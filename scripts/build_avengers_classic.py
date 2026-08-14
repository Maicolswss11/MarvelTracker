#!/usr/bin/env python3
"""Build the audited classic Avengers team path.

The route follows the repository's three-level editorial model:

    Italian physical publication -> USA contents -> path readingStep

Avengers (1963) #1-298 come from the exhaustive ComicsBox crawl in
``avengers-classic-sources.json``. Annuals and chapters from other series are
kept in the smaller, reviewable ``avengers-classic-supplements.json`` file.
The already catalogued Italian physical ID is always reused; when one book is
visited more than once, ``physicalId`` shares ownership while the route ``id``
keeps the read state local to that chronological stop.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500
AUDIT_DATE = "2026-08-14"
AUDIT_SOURCE = "curated:avengers-classic"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def unpack(path_id: str) -> dict[str, Any]:
    stub = read_json(DATA / "characters" / f"{path_id}.json")
    if not isinstance(stub.get("issueSources"), list):
        return stub
    spec = read_json(DATA / "encoded" / f"{path_id}.json")
    encoded = "".join(
        (ROOT / source).read_text(encoding="ascii").strip()
        for source in spec["sources"]
    )
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def pack(character: dict[str, Any]) -> None:
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[index : index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    for old in (DATA / "b64").glob("avengers-*.b64"):
        old.unlink()
    sources: list[str] = []
    for index, part in enumerate(parts, 1):
        relative = f"data/b64/avengers-{index:02d}.b64"
        (ROOT / relative).write_text(part, encoding="ascii")
        sources.append(relative)
    write_json(DATA / "encoded" / "avengers.json", {"encoding": "gzip-base64-parts", "sources": sources})
    meta = {key: value for key, value in character.items() if key != "issues"}
    meta["issueSources"] = ["data/encoded/avengers.json"]
    write_json(DATA / "characters" / "avengers.json", meta)


def publication_id(code: str) -> str:
    match = re.match(r"^(.+)_([0-9]+)([A-Za-z]?)$", code)
    if not match:
        return code
    prefix, number, suffix = match.groups()
    return f"{prefix}:{int(number)}{suffix.upper()}"


def display_number(code: str) -> str:
    match = re.search(r"_([0-9]+)([A-Za-z]?)$", code)
    if not match:
        return code
    return f"{int(match.group(1))}{match.group(2).upper()}"


def classic_era(number: int) -> tuple[str, str]:
    if number <= 15:
        return "La nascita dei Vendicatori", "Loki riunisce Thor, Iron Man, Hulk, Ant-Man e Wasp; Capitan America ritorna"
    if number <= 59:
        return "Il quartetto di Cap", "Occhio di Falco, Scarlet Witch e Quicksilver costruiscono una nuova identità"
    if number <= 104:
        return "Visione, Ultron e Guerra Kree-Skrull", "La squadra diventa il centro dell'Universo Marvel"
    if number <= 150:
        return "Nuove formazioni e grandi saghe", "Vendicatori/Difensori, Mantis, Swordsman e la Madonna Celestiale"
    if number <= 200:
        return "Wonder Man, Korvac e Henry Pym", "La squadra entra nell'era moderna"
    if number <= 249:
        return "Monica Rambeau e una seconda costa", "La Visione espande i Vendicatori verso Ovest"
    return "Le due coste", "Vendicatori Est e Ovest, Sotto Assedio, Evolutionary War e Inferno"


def source_bucket(publication: dict[str, Any]) -> str:
    publisher = str(publication.get("publisher") or "").casefold()
    year_match = re.search(r"(19|20)\d{2}", str(publication.get("date") or ""))
    year = int(year_match.group(0)) if year_match else 9999
    if "corno" in publisher:
        return "AVCLASSIC_CORNO"
    if year <= 1994:
        return "AVCLASSIC_TRANSITION"
    return "AVCLASSIC_RECOVERED"


def source_series(name: str) -> str:
    return re.split(r"\s+(?:#|\|)\s*", name, maxsplit=1)[0].strip() or "Edizione italiana"


def first_publication_group(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every physical part of the first Italian publication."""
    explicit = row.get("primaryPublicationIds")
    if isinstance(explicit, list) and explicit:
        by_id = {publication["id"]: publication for publication in row["italianPublications"]}
        missing = [code for code in explicit if code not in by_id]
        if missing:
            raise RuntimeError(f"{row['id']}: primaryPublicationIds mancanti: {missing}")
        return [by_id[code] for code in explicit]

    group: list[dict[str, Any]] = []
    for publication in row["italianPublications"]:
        group.append(publication)
        if publication.get("publisher") or publication.get("date"):
            break
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for publication in group:
        if publication["id"] not in seen:
            seen.add(publication["id"])
            unique.append(publication)
    return unique


def publication_metadata(
    code: str,
    row: dict[str, Any],
    physical: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inline = next((item for item in row["italianPublications"] if item["id"] == code), {})
    canonical = physical.get(code, {})
    publication = {**inline, **canonical, "id": code}
    publication.setdefault("name", publication_id(code))
    publication.setdefault("publisher", "Editore italiano non indicato")
    publication.setdefault("date", "")
    publication.setdefault("cover", f"https://www.comicsbox.it/cover/{code}.jpg")
    publication.setdefault("url", f"https://www.comicsbox.it/albo/{code}")
    return publication


def build_timeline(source: dict[str, Any], supplements: dict[str, Any]) -> list[dict[str, Any]]:
    extras: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for supplement in supplements["issues"]:
        row = dict(supplement)
        row.setdefault("url", f"https://www.comicsbox.it/albo/{row['id']}")
        row.setdefault("cover", f"https://www.comicsbox.it/cover/{row['id']}.jpg")
        row["kind"] = "supplement"
        extras[row["after"]].append(row)
    for rows in extras.values():
        rows.sort(key=lambda item: (int(item.get("order", 0)), item["id"]))

    timeline: list[dict[str, Any]] = []
    known_main = {row["id"] for row in source["issues"]}
    unknown_anchors = sorted(set(extras) - known_main)
    if unknown_anchors:
        raise RuntimeError(f"Inserti con ancoraggi sconosciuti: {unknown_anchors}")

    for original in source["issues"]:
        row = dict(original)
        row["kind"] = "main"
        if row["number"] == 136:
            row.update({
                "required": False,
                "skip": True,
                "reprintOnly": True,
                "reason": "Numero composto dalla ristampa di Amazing Adventures #12: non aggiunge un capitolo nuovo dei Vendicatori.",
            })
        elif row["number"] == 150:
            row.update({
                "partialReprint": True,
                "reason": "Leggere soltanto le pagine di raccordo nuove; le sequenze ristampate sono già presenti nel percorso.",
            })
        timeline.append(row)
        timeline.extend(extras.get(row["id"], []))
    return timeline


def alternative_codes(row: dict[str, Any]) -> frozenset[str]:
    primary = {publication["id"] for publication in first_publication_group(row)}
    return frozenset(
        publication["id"]
        for publication in row["italianPublications"]
        if publication["id"] not in primary
    )


def physical_segments(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    units: list[dict[str, Any]] = []
    for row in rows:
        publications = first_publication_group(row)
        for part, publication in enumerate(publications, 1):
            units.append({
                "row": row,
                "code": publication["id"],
                "part": part,
                "parts": len(publications),
                "alternatives": alternative_codes(row),
                "required": row.get("required") is not False,
            })
    segments: list[list[dict[str, Any]]] = []
    for unit in units:
        previous = segments[-1][-1] if segments else None
        if (
            previous
            and previous["code"] == unit["code"]
            and previous["alternatives"] == unit["alternatives"]
            and previous["required"] == unit["required"]
        ):
            segments[-1].append(unit)
        else:
            segments.append([unit])
    return segments


def anchor_number(row: dict[str, Any]) -> int:
    if row.get("seriesId") == "AV1":
        return int(row["number"])
    match = re.match(r"AV1_(\d+)$", str(row.get("after") or ""))
    if not match:
        raise RuntimeError(f"{row['id']}: impossibile determinare l'era")
    return int(match.group(1))


def content_label(row: dict[str, Any]) -> str:
    return f"{row['series']} #{row['number']}"


def route_suffix(row: dict[str, Any]) -> str:
    if row.get("seriesId") == "AV1":
        return str(row["number"])
    return re.sub(r"[^A-Za-z0-9]+", "_", row["id"]).strip("_")


def build_classic(
    source: dict[str, Any],
    supplements: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], list[dict[str, Any]]]], list[dict[str, Any]]]:
    timeline = build_timeline(source, supplements)
    physical = source["physicalPublications"]
    segments = physical_segments(timeline)
    frequency = Counter(segment[0]["code"] for segment in segments)
    seen: Counter[str] = Counter()
    used_route_ids: set[str] = set()
    issues: list[dict[str, Any]] = []
    route_segments: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    for segment in segments:
        first_row = segment[0]["row"]
        code = segment[0]["code"]
        publication = publication_metadata(code, first_row, physical)
        physical_id = publication_id(code)
        seen[code] += 1
        route_id = physical_id if seen[code] == 1 else f"{physical_id}@av{route_suffix(first_row)}"
        collision = 2
        base_route_id = route_id
        while route_id in used_route_ids:
            route_id = f"{base_route_id}-{collision}"
            collision += 1
        used_route_ids.add(route_id)

        source_rows: list[dict[str, Any]] = []
        for unit in segment:
            if not any(row["id"] == unit["row"]["id"] for row in source_rows):
                source_rows.append(unit["row"])
        unit_by_id = {unit["row"]["id"]: unit for unit in segment}
        era, era_sub = classic_era(anchor_number(first_row))
        repeated = frequency[code] > 1

        selected: list[str] = []
        titles: list[str] = []
        contents: list[dict[str, Any]] = []
        for row in source_rows:
            unit = unit_by_id[row["id"]]
            part = f" — parte {unit['part']} di {unit['parts']}" if unit["parts"] > 1 else ""
            selected.append(f"{content_label(row)}{part}")
            titles.append(f"{content_label(row)}: {row['title']}{part}")
            contents.append({
                "id": row["id"],
                "seriesId": row["seriesId"],
                "series": row["series"],
                "number": row["number"],
                "title": f"{content_label(row)} — {row['title']}{part}",
                "url": row["url"],
            })

        required = any(row.get("required") is not False for row in source_rows)
        instruction = "In questo albo leggi: " + "; ".join(selected) + "."
        notes = [str(row["reason"]) for row in source_rows if row.get("reason")]
        if notes:
            instruction += " " + " ".join(notes)
        if repeated:
            instruction += " Lo stesso volume fisico ricompare in più punti: Fisico/Digitale resta condiviso, mentre Letto vale per questa tappa."

        issue = {
            "id": route_id,
            "physicalId": physical_id,
            "n": int(re.search(r"\d+", display_number(code)).group(0)),
            "displayNumber": display_number(code),
            "name": publication["name"],
            "title": " · ".join(titles),
            "date": publication["date"],
            "seriesId": source_bucket(publication),
            "series": source_series(publication["name"]),
            "publisher": publication["publisher"],
            "cover": publication["cover"],
            "url": publication["url"],
            "era": era,
            "eraSub": era_sub,
            "instruction": instruction,
            "required": required,
            "skip": not required,
            "future": False,
            "coverSource": "ComicsBox",
            "contents": contents,
            "contentsStatus": "path-scoped",
            "routeSegment": {"contentIds": [row["id"] for row in source_rows]},
            "auditCore": True,
            "auditStatus": "audited",
        }
        if all(row.get("reprintOnly") for row in source_rows):
            issue["reprintOnly"] = True
        if any(row.get("partialReprint") for row in source_rows):
            issue["partialReprint"] = True
        issues.append(issue)
        route_segments.append((issue, source_rows))

    return issues, route_segments, timeline


def patch_modern(modern: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in modern}
    if "VEN_M:1" not in by_id or "VEN_M:0" not in by_id:
        raise RuntimeError("Transizione Vendicatori #0/#1 assente dal percorso esistente")

    one = by_id["VEN_M:1"]
    one.update({
        "title": "Avengers vol. 1 #299–300 — Inferno e la nuova formazione",
        "instruction": "Leggi Avengers vol. 1 #299–300: conclusione del nucleo classico auditato.",
        "contents": [
            {"id": f"AV1_{number:03d}", "seriesId": "AV1", "series": "Avengers vol. 1", "number": number, "title": f"Avengers vol. 1 #{number}", "url": f"https://www.comicsbox.it/albo/AV1_{number:03d}"}
            for number in (299, 300)
        ],
        "contentsStatus": "path-scoped",
        "era": "Inferno e una nuova formazione",
        "eraSub": "Avengers #299–300 chiude il perimetro classico auditato",
        "required": True,
        "skip": False,
        "coreTransition": True,
        "auditStatus": "audited",
    })

    zero = by_id["VEN_M:0"]
    zero.update({
        "title": "Archivio post-classico — Quasar, Cavaliere Nero, Visione e Thor",
        "instruction": "Tappa antologica legacy, fuori dal nucleo #1–300: salta il riassunto di Avengers #300. I racconti di Avengers Annual #18 non sono contigui al #300 (Quasar è successivo al #303; Atlantis Attacks al #310), quindi questa card resta facoltativa finché il tratto #301–310 non sarà auditato allo stesso livello.",
        "contents": [
            {"id": "AV1A_018", "seriesId": "AV1A", "series": "Avengers Annual vol. 1", "number": 18, "title": "Avengers Annual vol. 1 #18 — racconti selezionati", "url": "https://www.comicsbox.it/albo/AV1A_018"},
            {"id": "MARVSHERO2_004", "seriesId": "MARVSHERO2", "series": "Marvel Super-Heroes vol. 2", "number": 4, "title": "Marvel Super-Heroes vol. 2 #4 — Cavaliere Nero", "url": "https://www.comicsbox.it/albo/MARVSHERO2_004"},
            {"id": "AV1A_020", "seriesId": "AV1A", "series": "Avengers Annual vol. 1", "number": 20, "title": "Avengers Annual vol. 1 #20 — Visione / Thor", "url": "https://www.comicsbox.it/albo/AV1A_020"}
        ],
        "contentsStatus": "path-scoped",
        "era": "Archivio post-classico",
        "eraSub": "Materiale conservato, ma non dichiarato cronologicamente auditato",
        "required": False,
        "skip": True,
        "legacyPostCore": True,
        "auditStatus": "deferred",
    })

    ordered = [one, zero]
    ordered.extend(row for row in modern if row["id"] not in {"VEN_M:0", "VEN_M:1"})
    return ordered


def add_alternatives(route_segments: list[tuple[dict[str, Any], list[dict[str, Any]]]]) -> int:
    path = DATA / "curated-editions.json"
    payload = read_json(path)
    editions = payload.get("editions", [])

    for edition in editions:
        edition["coverage"] = [
            coverage
            for coverage in edition.get("coverage", [])
            if not (
                coverage.get("path") == "avengers"
                and (
                    edition.get("coverageSource") == AUDIT_SOURCE
                    or coverage.get("coverageSource") == AUDIT_SOURCE
                )
            )
        ]
    editions = [edition for edition in editions if edition.get("coverage") or edition.get("coverageSource") != AUDIT_SOURCE]
    by_id = {row["id"]: row for row in editions}

    links = 0
    for route, source_rows in route_segments:
        sets: list[set[str]] = []
        metadata: dict[str, dict[str, Any]] = {}
        for row in source_rows:
            primary_codes = {publication["id"] for publication in first_publication_group(row)}
            alternatives = {publication["id"] for publication in row["italianPublications"] if publication["id"] not in primary_codes}
            sets.append(alternatives)
            for publication in row["italianPublications"]:
                metadata.setdefault(publication["id"], publication)
        candidates = set.intersection(*sets) if sets else set()

        for code in sorted(candidates):
            pub = metadata[code]
            edition_id = publication_id(code)
            edition = by_id.setdefault(edition_id, {
                "id": edition_id,
                "name": pub.get("name") or edition_id,
                "series": source_series(pub.get("name") or edition_id),
                "number": display_number(code),
                "publisher": pub.get("publisher") or "Editore italiano non indicato",
                "format": "Ristampa / raccolta",
                "date": pub.get("date", ""),
                "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
                "url": f"https://www.comicsbox.it/albo/{code}",
                "contents": [],
                "coverage": [],
                "source": "ComicsBox",
                "sourceCode": code,
                "coverageSource": AUDIT_SOURCE,
            })
            coverage = next((item for item in edition.setdefault("coverage", []) if item.get("path") == "avengers"), None)
            if not coverage:
                coverage = {"path": "avengers", "issueIds": [], "label": edition["name"], "coverageSource": AUDIT_SOURCE}
                edition["coverage"].append(coverage)
            if route["id"] not in coverage["issueIds"]:
                coverage["issueIds"].append(route["id"])
                links += 1

    payload["version"] = max(int(payload.get("version", 1)), 5)
    payload["editions"] = sorted(by_id.values(), key=lambda row: (row.get("series", "").casefold(), str(row.get("number", ""))))
    write_json(path, payload)
    return links


def main() -> None:
    source = read_json(DATA / "avengers-classic-sources.json")
    supplements = read_json(DATA / "avengers-classic-supplements.json")
    if len(source.get("issues", [])) != 298 or len(source.get("physicalPublications", {})) < 270:
        raise RuntimeError("Audit regolare Vendicatori #1-298 incompleto")
    if len(supplements.get("issues", [])) != 40:
        raise RuntimeError("Audit dei supplementi classici incompleto")

    current = unpack("avengers")
    classic, route_segments, timeline = build_classic(source, supplements)
    modern_seed = [
        row
        for row in current["issues"]
        if not row.get("routeSegment")
        and row.get("id") != "SPE_VCO_S:1"
        and not str(row.get("seriesId", "")).startswith("AVCLASSIC_")
    ]
    modern = patch_modern(modern_seed)
    modern_series = [row for row in current.get("series", []) if not str(row.get("id", "")).startswith("AVCLASSIC_")]
    issues = classic + modern
    for seq, issue in enumerate(issues, 1):
        issue["seq"] = seq
        if issue.get("contents"):
            issue["readingStep"] = {
                "pathId": "avengers",
                "position": seq,
                "contentIds": [row["id"] for row in issue["contents"]],
                "scope": "selected-contents",
            }

    required_total = sum(issue.get("required") is not False and not issue.get("future") for issue in issues)
    current.update({
        "start": "Il mitico Thor #5 — Avengers (1963) #1 — Giugno 1971",
        "subtitle": "Terra-616 · percorso della squadra classica auditato",
        "description": "Percorso narrativo dei Vendicatori dalla formazione causata da Loki in Avengers (1963) #1. La serie regolare, gli Annual e i crossover che proseguono direttamente la storia della squadra sono mappati sulle edizioni fisiche italiane; la fondazione della Costa Ovest è collocata capitolo per capitolo prima di Avengers #250.",
        "timelineMode": True,
        "auditStatus": "audited",
        "auditKind": "path/team",
        "auditScope": "Avengers (1963) #1–300 e capitoli USA direttamente necessari",
        "auditDate": AUDIT_DATE,
        "series": [
            {"id": "AVCLASSIC_CORNO", "name": "Classici Editoriale Corno", "publisher": "Editoriale Corno", "range": "prime edizioni italiane", "years": "1971–1982"},
            {"id": "AVCLASSIC_TRANSITION", "name": "Transizione e Costa Ovest", "publisher": "Comic Art / Star Comics / altri", "range": "prime edizioni italiane", "years": "1983–1994"},
            {"id": "AVCLASSIC_RECOVERED", "name": "Inediti classici recuperati", "publisher": "Marvel Italia / Panini Comics", "range": "prime edizioni italiane tardive", "years": "1997–2024"},
            *modern_series,
        ],
        "archives": [
            {"name": "Avengers vol. 1", "range": "#1–300", "publisher": "Marvel Comics", "years": "1963–1989", "status": "nucleo della squadra auditato; #136 è una ristampa facoltativa"},
            {"name": "Annual e crossover diretti", "range": "40 capitoli USA", "publisher": "Marvel Comics", "years": "1967–1988", "status": "inseriti nella posizione narrativa verificata"},
            {"name": "West Coast Avengers vol. 1", "range": "#1–4 + Iron Man Annual #7", "publisher": "Marvel Comics", "years": "1984", "status": "fondazione inserita capitolo per capitolo"},
        ],
        "totalRequired": required_total,
        "availableTotal": required_total,
        "issues": issues,
    })
    pack(current)

    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    manifest["version"] = max(int(manifest.get("version", 1)), 36)
    meta = next(row for row in manifest["characters"] if row["id"] == "avengers")
    meta.update({
        "start": current["start"],
        "end": current["end"],
        "totalRequired": current["totalRequired"],
        "auditStatus": "audited",
        "auditKind": "path/team",
        "auditDate": AUDIT_DATE,
    })
    write_json(manifest_path, manifest)

    alternative_links = add_alternatives(route_segments)
    repeated = len(classic) - len({row.get("physicalId", row["id"]) for row in classic})
    required_core_ids = {row["id"] for row in timeline if row.get("required") is not False} | {"AV1_299", "AV1_300"}
    audit = {
        "version": 2,
        "status": "audited",
        "auditKind": "path/team",
        "auditDate": AUDIT_DATE,
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
        "scope": "Avengers (1963) #1–300 e soli capitoli USA che continuano direttamente la storia della squadra",
        "mainSeriesRange": {"series": "Avengers vol. 1", "from": 1, "to": 300, "mapped": 300},
        "mainSeriesNarrativeRequired": 299,
        "optionalReprintMainIssues": ["AV1_136"],
        "supplementalUsIssues": len(supplements["issues"]),
        "requiredUsChapters": len(required_core_ids),
        "classicReadingSegments": len(classic) + 1,
        "classicPhysicalPublications": len({row.get("physicalId", row["id"]) for row in classic} | {"VEN_M:1"}),
        "repeatedPhysicalSegments": repeated,
        "alternativeCoverageLinks": alternative_links,
        "modernSegments": len(modern),
        "totalRouteSegments": len(issues),
        "remainingCoreGaps": [],
        "transition": ["AV1A_017", "AV1_299", "AV1_300"],
        "legacyPostCore": {
            "routeId": "VEN_M:0",
            "status": "deferred",
            "required": False,
            "reason": "Avengers Annual #18 è posteriore ad Avengers #303/#310 e non può essere collocato subito dopo #300 senza auditare il tratto intermedio."
        },
        "excludedReprints": supplements["excludedReprints"],
        "scopeExclusions": supplements["scopeExclusions"],
        "sources": supplements["sources"],
        "sourceConflicts": supplements["sourceConflicts"],
        "sourcePolicy": "ComicsBox per albo USA e pubblicazioni italiane; Marvel/GCD per controllo; ordine verificato su rimandi interni e raccolte Marvel. In caso di ristampe con ISBN o contenuti diversi, gli ID fisici restano distinti."
    }
    write_json(DATA / "avengers-classic-audit.json", audit)
    print(f"Vendicatori: {len(classic)} tappe classiche + {len(modern)} moderne = {len(issues)}")
    print(f"Nucleo USA richiesto: {audit['requiredUsChapters']} capitoli · albi fisici classici: {audit['classicPhysicalPublications']}")
    print(f"Collegamenti a edizioni alternative: {alternative_links}")


if __name__ == "__main__":
    main()
