#!/usr/bin/env python3
"""Prepend the complete classic Avengers spine to the existing modern route.

The source audit maps Avengers vol. 1 #1-298 to the first Italian physical
publication of each chapter. A physical book may reappear as multiple reading
segments when its contents are not consecutive; ``physicalId`` keeps collection
ownership shared while ``id`` keeps reading progress narrative and independent.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def unpack(path_id: str) -> dict[str, Any]:
    stub = read_json(DATA / "characters" / f"{path_id}.json")
    if not isinstance(stub.get("issueSources"), list):
        return stub
    spec = read_json(DATA / "encoded" / f"{path_id}.json")
    encoded = "".join((ROOT / source).read_text(encoding="ascii").strip() for source in spec["sources"])
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def pack(character: dict[str, Any]) -> None:
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
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
    match = re.search(r"_([0-9]+[A-Za-z]?)$", code)
    return str(int(re.match(r"\d+", match.group(1)).group(0))) + match.group(1)[len(re.match(r"\d+", match.group(1)).group(0)):] if match else code


def classic_era(number: int) -> tuple[str, str]:
    if number <= 15:
        return "La nascita dei Vendicatori", "Loki riunisce la squadra; Hulk lascia e Capitan America ritorna"
    if number <= 59:
        return "Il quartetto di Cap", "Occhio di Falco, Scarlet Witch e Quicksilver costruiscono una nuova identità"
    if number <= 104:
        return "Visione, Ultron e Guerra Kree-Skrull", "La squadra diventa il centro dell'Universo Marvel"
    if number <= 150:
        return "Nuove formazioni e grandi saghe", "Mantis, Swordsman, Kang e la Corona del Serpente"
    if number <= 200:
        return "Korvac, Pym e il destino di Ms. Marvel", "La squadra entra nell'era moderna"
    if number <= 249:
        return "Monica Rambeau e una seconda costa", "La Visione espande i Vendicatori verso Ovest"
    return "Le due coste", "Vendicatori Est e Ovest, Sotto Assedio e Inferno"


def source_bucket(publication: dict[str, str]) -> str:
    publisher = publication.get("publisher", "").casefold()
    year_match = re.search(r"(19|20)\d{2}", publication.get("date", ""))
    year = int(year_match.group(0)) if year_match else 9999
    if "corno" in publisher:
        return "AVCLASSIC_CORNO"
    if year <= 1994:
        return "AVCLASSIC_TRANSITION"
    return "AVCLASSIC_RECOVERED"


def source_series(name: str) -> str:
    return re.split(r"\s+#\s+", name, maxsplit=1)[0].strip() or "Edizione italiana"


def first_publication_group(row: dict[str, Any]) -> list[dict[str, str]]:
    """Return every physical part used by the first Italian publication.

    ComicsBox lists split stories as ``issue A, issue B, Publisher (date/date)``.
    The crawler therefore sees metadata only on the final link. Accumulating up
    to that first metadata-bearing record preserves both halves instead of
    silently treating the opening half as the complete chapter.
    """
    group: list[dict[str, str]] = []
    for publication in row["italianPublications"]:
        group.append(publication)
        if publication.get("publisher") or publication.get("date"):
            break
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for publication in group:
        if publication["id"] not in seen:
            seen.add(publication["id"])
            unique.append(publication)
    return unique


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
            })
    segments: list[list[dict[str, Any]]] = []
    for unit in units:
        if segments and segments[-1][-1]["code"] == unit["code"]:
            segments[-1].append(unit)
        else:
            segments.append([unit])
    return segments


def number_label(numbers: list[int]) -> str:
    return f"#{numbers[0]}" if len(numbers) == 1 else f"#{numbers[0]}–{numbers[-1]}"


def build_classic(source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], list[dict[str, Any]]]]]:
    rows = source["issues"]
    physical = source["physicalPublications"]
    segments = physical_segments(rows)
    frequency = Counter(segment[0]["code"] for segment in segments)
    seen: Counter[str] = Counter()
    issues: list[dict[str, Any]] = []
    route_segments: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    wca_inserted = False

    for segment in segments:
        start = segment[0]["row"]["number"]
        if start == 250 and not wca_inserted:
            wca = {
                "id": "SPE_VCO_S:1",
                "physicalId": "SPE_VCO_S:1",
                "n": 1,
                "displayNumber": "1",
                "name": "Speciale Vendicatori Costa Ovest — Vendicatori Uniti!",
                "title": "West Coast Avengers vol. 1 #1–4",
                "date": "Febbraio 1991",
                "seriesId": "AVCLASSIC_TRANSITION",
                "series": "Speciale Vendicatori Costa Ovest",
                "publisher": "Star Comics",
                "cover": "https://www.comicsbox.it/cover/SPE_VCO_S_001.jpg",
                "url": "https://www.comicsbox.it/albo/SPE_VCO_S_001",
                "era": "Nascono i Vendicatori della Costa Ovest",
                "eraSub": "La miniserie fondativa prima dell'incontro fra le due squadre",
                "instruction": "Leggi West Coast Avengers vol. 1 #1–4. Qui Visione affida a Occhio di Falco la formazione della squadra di Los Angeles: da questo momento i Vendicatori Est e Ovest possono già conoscersi e punzecchiarsi.",
                "required": True,
                "skip": False,
                "future": False,
                "coverSource": "ComicsBox",
                "contents": [
                    {"id": f"WCA1_{number:03d}", "seriesId": "WCA1", "series": "West Coast Avengers vol. 1", "number": number, "title": f"West Coast Avengers vol. 1 #{number}", "url": f"https://www.comicsbox.it/albo/WCA1_{number:03d}"}
                    for number in range(1, 5)
                ],
                "contentsStatus": "path-scoped",
            }
            issues.append(wca)
            route_segments.append((wca, []))
            wca_inserted = True

        code = segment[0]["code"]
        publication = physical[code]
        physical_id = publication_id(code)
        seen[code] += 1
        route_id = physical_id if seen[code] == 1 else f"{physical_id}@av{start}"
        source_rows = list({unit["row"]["number"]: unit["row"] for unit in segment}.values())
        unit_by_number = {unit["row"]["number"]: unit for unit in segment}
        numbers = [row["number"] for row in source_rows]
        labels = [
            f"Avengers #{unit['row']['number']}: {unit['row']['title']}"
            + (f" — parte {unit['part']} di {unit['parts']}" if unit["parts"] > 1 else "")
            for unit in segment
        ]
        era, era_sub = classic_era(start)
        repeated = frequency[code] > 1
        instruction = "In questo albo leggi: " + "; ".join(
            f"Avengers vol. 1 #{unit['row']['number']}"
            + (f" parte {unit['part']} di {unit['parts']}" if unit["parts"] > 1 else " completo")
            for unit in segment
        ) + "."
        if repeated:
            instruction += " Lo stesso volume fisico ricompare in più punti della cronologia: Fisico/Digitale resta condiviso, mentre Letto vale soltanto per questa tappa."
        issue = {
            "id": route_id,
            "physicalId": physical_id,
            "n": int(re.search(r"\d+", display_number(code)).group(0)),
            "displayNumber": display_number(code),
            "name": publication["name"],
            "title": " · ".join(labels),
            "date": publication["date"],
            "seriesId": source_bucket(publication),
            "series": source_series(publication["name"]),
            "publisher": publication["publisher"],
            "cover": publication["cover"],
            "url": publication["url"],
            "era": era,
            "eraSub": era_sub,
            "instruction": instruction,
            "required": True,
            "skip": False,
            "future": False,
            "coverSource": "ComicsBox",
            "contents": [
                {
                    "id": row["id"],
                    "seriesId": "AV1",
                    "series": "Avengers vol. 1",
                    "number": row["number"],
                    "title": f"Avengers vol. 1 #{row['number']} — {row['title']}"
                    + (
                        f" (parte {unit_by_number[row['number']]['part']} di {unit_by_number[row['number']]['parts']})"
                        if unit_by_number[row["number"]]["parts"] > 1 else ""
                    ),
                    "url": row["url"],
                }
                for row in source_rows
            ],
            "contentsStatus": "path-scoped",
            "routeSegment": {"series": "Avengers vol. 1", "from": numbers[0], "to": numbers[-1]},
        }
        issues.append(issue)
        route_segments.append((issue, source_rows))
    return issues, route_segments


def patch_modern(modern: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in modern}
    one = by_id["VEN_M:1"]
    one.update({
        "title": "Avengers vol. 1 #299–300 — Inferno e la nuova formazione",
        "instruction": "Leggi Avengers vol. 1 #299–300. È la continuazione diretta del percorso classico.",
        "contents": [
            {"id": f"AV1_{number:03d}", "seriesId": "AV1", "series": "Avengers vol. 1", "number": number, "title": f"Avengers vol. 1 #{number}", "url": f"https://www.comicsbox.it/albo/AV1_{number:03d}"}
            for number in (299, 300)
        ],
        "contentsStatus": "path-scoped",
        "era": "Inferno e una nuova formazione",
        "eraSub": "Avengers #299–300 prima degli annual del 1989",
    })
    zero = by_id["VEN_M:0"]
    zero.update({
        "title": "Quasar entra nei Vendicatori · racconti di Cavaliere Nero, Visione e Thor",
        "instruction": "Albo antologico: salta il riassunto di Avengers #300, già letto. Leggi i due segmenti di Avengers Annual #18 sull'ingresso di Quasar, poi i racconti indicati di Cavaliere Nero, Visione e Thor. Quasar è Wendell Vaughn, eroe cosmico attivo dal 1978: questa è la sua ammissione nella squadra, non la sua origine.",
        "contents": [
            {"id": "AVANN1_018", "seriesId": "AVANN1", "series": "Avengers Annual vol. 1", "number": 18, "title": "Avengers Annual vol. 1 #18 — L'iniziazione di Quasar / Cap valuta i Vendicatori", "url": "https://www.comicsbox.it/albo/AVANN1_018"},
            {"id": "MARVSHERO2_004", "seriesId": "MARVSHERO2", "series": "Marvel Super-Heroes vol. 2", "number": 4, "title": "Marvel Super-Heroes vol. 2 #4 — Cavaliere Nero", "url": "https://www.comicsbox.it/albo/MARVSHERO2_004"},
            {"id": "AVANN1_020", "seriesId": "AVANN1", "series": "Avengers Annual vol. 1", "number": 20, "title": "Avengers Annual vol. 1 #20 — Visione / Thor", "url": "https://www.comicsbox.it/albo/AVANN1_020"},
        ],
        "contentsStatus": "path-scoped",
        "era": "Annual e nuovi membri",
        "eraSub": "Quasar arriva dopo la formazione dei Vendicatori della Costa Ovest",
    })
    ordered = [one, zero]
    ordered.extend(row for row in modern if row["id"] not in {"VEN_M:0", "VEN_M:1"})
    return ordered


def add_alternatives(route_segments: list[tuple[dict[str, Any], list[dict[str, Any]]]]) -> int:
    path = DATA / "curated-editions.json"
    payload = read_json(path)
    by_id = {row["id"]: row for row in payload.get("editions", [])}
    managed_route_ids = {route["id"] for route, _ in route_segments}

    for route, source_rows in route_segments:
        candidates: set[str]
        metadata: dict[str, dict[str, str]] = {}
        if source_rows:
            sets: list[set[str]] = []
            for row in source_rows:
                primary_codes = {pub["id"] for pub in first_publication_group(row)}
                editions = {pub["id"] for pub in row["italianPublications"] if pub["id"] not in primary_codes}
                sets.append(editions)
                for pub in row["italianPublications"]:
                    metadata.setdefault(pub["id"], pub)
            candidates = set.intersection(*sets) if sets else set()
        else:
            candidates = {"AVENSORO_012"}
            metadata = {"AVENSORO_012": {"id": "AVENSORO_012", "name": "Avengers (Serie Oro) #12 — I Vendicatori della Costa Ovest", "publisher": "Panini Comics", "date": "Lug 2015"}}

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
                "coverageSource": "curated:avengers-classic",
            })
            coverage = next((item for item in edition.setdefault("coverage", []) if item.get("path") == "avengers"), None)
            if not coverage:
                coverage = {"path": "avengers", "issueIds": [], "label": edition["name"]}
                edition["coverage"].append(coverage)
            if route["id"] not in coverage["issueIds"]:
                coverage["issueIds"].append(route["id"])

    payload["version"] = max(int(payload.get("version", 1)), 4)
    payload["editions"] = sorted(by_id.values(), key=lambda row: (row.get("series", "").casefold(), str(row.get("number", ""))))
    write_json(path, payload)
    return sum(
        len(managed_route_ids.intersection(coverage.get("issueIds", [])))
        for edition in payload["editions"]
        for coverage in edition.get("coverage", [])
        if coverage.get("path") == "avengers"
    )


def main() -> None:
    source = read_json(DATA / "avengers-classic-sources.json")
    if len(source.get("issues", [])) != 298 or len(source.get("physicalPublications", {})) != 270:
        raise RuntimeError("Audit classico Vendicatori incompleto")

    current = unpack("avengers")
    classic, route_segments = build_classic(source)
    modern_seed = [
        row for row in current["issues"]
        if not row.get("routeSegment")
        and row.get("id") != "SPE_VCO_S:1"
        and not str(row.get("seriesId", "")).startswith("AVCLASSIC_")
    ]
    modern = patch_modern(modern_seed)
    modern_series = [row for row in current.get("series", []) if not str(row.get("id", "")).startswith("AVCLASSIC_")]
    issues = classic + modern
    for seq, issue in enumerate(issues, 1):
        issue["seq"] = seq
        if issue.get("contents") and not isinstance(issue.get("readingStep"), dict):
            issue["readingStep"] = {
                "pathId": "avengers",
                "position": seq,
                "contentIds": [row["id"] for row in issue["contents"]],
                "scope": "selected-contents",
            }
        elif isinstance(issue.get("readingStep"), dict):
            issue["readingStep"]["pathId"] = "avengers"
            issue["readingStep"]["position"] = seq

    current.update({
        "start": "Il mitico Thor #5 — Giugno 1971",
        "description": "Percorso completo dei Vendicatori dall'Avengers #1 del 1963: ogni capitolo classico è collegato alla sua prima edizione fisica italiana, con la fondazione dei Vendicatori della Costa Ovest inserita prima che le due squadre inizino a interagire. Dal #299 il percorso prosegue nelle testate Marvel Italia e Panini già mappate.",
        "timelineMode": True,
        "series": [
            {"id": "AVCLASSIC_CORNO", "name": "Classici Editoriale Corno", "publisher": "Editoriale Corno", "range": "prime edizioni italiane", "years": "1971–1982"},
            {"id": "AVCLASSIC_TRANSITION", "name": "Transizione e Costa Ovest", "publisher": "Comic Art / Star Comics / altri", "range": "prime edizioni italiane", "years": "1983–1994"},
            {"id": "AVCLASSIC_RECOVERED", "name": "Inediti classici recuperati", "publisher": "Marvel Italia / Panini Comics", "range": "prime edizioni italiane tardive", "years": "1997–2024"},
            *modern_series,
        ],
        "archives": [
            {"name": "Avengers vol. 1", "range": "#1–300", "publisher": "Marvel Comics", "years": "1963–1989", "status": "mappatura completa sulle prime edizioni italiane"},
            {"name": "West Coast Avengers vol. 1", "range": "#1–4", "publisher": "Marvel Comics", "years": "1984", "status": "origine della squadra inserita nella timeline"},
        ],
        "totalRequired": len(issues),
        "availableTotal": len([row for row in issues if row.get("required") is not False and not row.get("future")]),
        "issues": issues,
    })
    pack(current)

    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    manifest["version"] = max(int(manifest.get("version", 1)), 35)
    meta = next(row for row in manifest["characters"] if row["id"] == "avengers")
    meta.update({"start": current["start"], "end": current["end"], "totalRequired": current["totalRequired"]})
    write_json(manifest_path, manifest)

    alternatives = add_alternatives(route_segments)
    repeated = len(classic) - len({row.get("physicalId", row["id"]) for row in classic})
    audit = {
        "version": 1,
        "source": "ComicsBox USA issue pages and Italian publication records",
        "usaMainIssues": 298,
        "westCoastOriginIssues": 4,
        "classicReadingSegments": len(classic),
        "classicPhysicalPublications": len({row.get("physicalId", row["id"]) for row in classic}),
        "repeatedPhysicalSegments": repeated,
        "alternativeCoverageLinks": alternatives,
        "modernSegments": len(modern),
        "totalRouteSegments": len(issues),
        "transition": ["AV1_299", "AV1_300", "AVANN1_018"],
    }
    write_json(DATA / "avengers-classic-audit.json", audit)
    print(f"Vendicatori: {len(classic)} tappe classiche + {len(modern)} moderne = {len(issues)}")
    print(f"Albi fisici classici: {audit['classicPhysicalPublications']} · collegamenti ristampe: {alternatives}")


if __name__ == "__main__":
    main()
