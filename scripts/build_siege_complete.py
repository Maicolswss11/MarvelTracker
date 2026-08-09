#!/usr/bin/env python3
"""Upgrade Assedio/Siege to the complete audited Italian physical route.

The saved reading order contains the narrative US chapters.  The checklist
contains one node per distinct first Italian physical publication; collected
editions remain alternatives and never replace a mixed Italian issue unless
they cover every Siege chapter assigned to that issue.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "siege"
MANIFEST_VERSION = 20


READING_ORDER = [
    "Dark Avengers (2009) #1",
    "Dark Reign: The Cabal (2009) #1",
    "Thor (2007) #600",
    "Dark Reign: The List - Avengers (2009) #1",
    "New Avengers Annual (2009) #3",
    "Siege: The Cabal (2010) #1",
    "Avengers: The Initiative (2007) #31",
    "Origins of Siege (2010) #1",
    "Siege (2010) #1",
    "Avengers: The Initiative (2007) #32",
    "Dark Avengers (2009) #13",
    "Dark Wolverine (2009) #82",
    "New Avengers (2004) #61",
    "Siege: Embedded (2010) #1",
    "Siege (2010) #2",
    "Avengers: The Initiative (2007) #33",
    "Dark Avengers (2009) #14",
    "Dark Wolverine (2009) #83",
    "New Avengers (2004) #62",
    "Siege: Embedded (2010) #2",
    "Thor (2007) #607",
    "Thunderbolts (2006) #141",
    "Siege (2010) #3",
    "Avengers: The Initiative (2007) #34",
    "Dark Avengers (2009) #15",
    "Dark Wolverine (2009) #84",
    "The Mighty Avengers (2007) #35",
    "New Avengers (2004) #63",
    "Siege: Loki (2010) #1",
    "New Mutants (2009) #11",
    "Siege: Embedded (2010) #3",
    "Thor (2007) #608",
    "Thunderbolts (2006) #142",
    "Siege: Secret Warriors (2010) #1",
    "Siege: Spider-Man (2010) #1",
    "Siege: Young Avengers (2010) #1",
    "Siege: Captain America (2010) #1",
    "Thor (2007) #609",
    "The Mighty Avengers (2007) #36",
    "Siege (2010) #4",
    "Avengers: The Initiative (2007) #35",
    "Dark Avengers (2009) #16",
    "New Avengers (2004) #64",
    "Siege: Embedded (2010) #4",
    "Thor (2007) #610",
    "Thunderbolts (2006) #143",
    "New Avengers Finale (2010) #1",
    "Sentry: Fallen Sun (2010) #1",
]


CHAPTER_TO_ITALIAN: dict[str, str] = {
    "Dark Avengers (2009) #1": "IM_VEN2:20",
    "Dark Reign: The Cabal (2009) #1": "MMMI:102",
    "Thor (2007) #600": "THORVE_M:128",
    "Dark Reign: The List - Avengers (2009) #1": "MMMI:106",
    "New Avengers Annual (2009) #3": "THORVE_M:138",
    "Siege: The Cabal (2010) #1": "MMMI:107",
    "Avengers: The Initiative (2007) #31": "MAR_MIX:88",
    "Origins of Siege (2010) #1": "MMMI:107",
    "Siege (2010) #1": "MMMI:108",
    "Avengers: The Initiative (2007) #32": "MAR_MIX:88",
    "Dark Avengers (2009) #13": "IM_VEN2:31",
    "Dark Wolverine (2009) #82": "WOL_PM:250",
    "New Avengers (2004) #61": "THORVE_M:139",
    "Siege: Embedded (2010) #1": "MMMI:108",
    "Siege (2010) #2": "MMMI:109",
    "Avengers: The Initiative (2007) #33": "MAR_MIX:88",
    "Dark Avengers (2009) #14": "IM_VEN2:32",
    "Dark Wolverine (2009) #83": "WOL_PM:251",
    "New Avengers (2004) #62": "THORVE_M:140",
    "Siege: Embedded (2010) #2": "MMMI:109",
    "Thor (2007) #607": "THORVE_M:140",
    "Thunderbolts (2006) #141": "MAR_MIX:89",
    "Siege (2010) #3": "MMMI:110",
    "Avengers: The Initiative (2007) #34": "MAR_MIX:88",
    "Dark Avengers (2009) #15": "IM_VEN2:33",
    "Dark Wolverine (2009) #84": "WOL_PM:252",
    "The Mighty Avengers (2007) #35": "IM_VEN2:33",
    "New Avengers (2004) #63": "THORVE_M:141",
    "Siege: Loki (2010) #1": "MRVUN_M:2",
    "New Mutants (2009) #11": "XM_DX:190",
    "Siege: Embedded (2010) #3": "MMMI:110",
    "Thor (2007) #608": "THORVE_M:141",
    "Thunderbolts (2006) #142": "MAR_MIX:89",
    "Siege: Secret Warriors (2010) #1": "MRVUN_M:2",
    "Siege: Spider-Man (2010) #1": "MRVUN_M:2",
    "Siege: Young Avengers (2010) #1": "MRVUN_M:2",
    "Siege: Captain America (2010) #1": "MRVUN_M:2",
    "Thor (2007) #609": "THORVE_M:141",
    "The Mighty Avengers (2007) #36": "IM_VEN2:33",
    "Siege (2010) #4": "MMMI:111",
    "Avengers: The Initiative (2007) #35": "MAR_MIX:88",
    "Dark Avengers (2009) #16": "IM_VEN2:34",
    "New Avengers (2004) #64": "THORVE_M:142",
    "Siege: Embedded (2010) #4": "MMMI:111",
    "Thor (2007) #610": "THORVE_M:142",
    "Thunderbolts (2006) #143": "MAR_MIX:89",
    "New Avengers Finale (2010) #1": "THORVE_M:143",
    "Sentry: Fallen Sun (2010) #1": "IM_VEN2:34",
}


FALLBACK_META = {
    "MMMI:102": ("Marvel Miniserie #102", "Dark Reign Zero b", "Novembre 2009"),
    "MMMI:106": ("Marvel Miniserie #106", "Dark Reign — La Lista 4", "Agosto 2010"),
    "MAR_MIX:88": ("Marvel Mix #88", "Vendicatori l'Iniziativa — Assedio: La caduta!", "Gennaio 2011"),
    "MAR_MIX:89": ("Marvel Mix #89", "Thunderbolts 4: Assedio", "Febbraio 2011"),
    "WOL_PM:250": ("Wolverine #250", "Assedio", "Ottobre 2010"),
    "WOL_PM:251": ("Wolverine #251", "Assedio", "Novembre 2010"),
    "WOL_PM:252": ("Wolverine #252", "Assedio", "Dicembre 2010"),
    "XM_DX:190": ("X-Men Deluxe #190", "X-Necrosha parte 6", "Gennaio 2011"),
    "MRVUN_M:2": ("Marvel Universe #2", "Speciale Assedio", "Gennaio 2011"),
}


SERIES_META = {
    "IM_VEN2": ("Iron Man e i potenti Vendicatori", "Marvel Italia / Panini Comics", "IM_VEN2"),
    "MMMI": ("Marvel Miniserie", "Marvel Italia / Panini Comics", "MMMI"),
    "THORVE_M": ("Thor", "Marvel Italia / Panini Comics", "THORVE_M"),
    "MAR_MIX": ("Marvel Mix", "Marvel Italia / Panini Comics", "MAR_MIX"),
    "WOL_PM": ("Wolverine", "Panini Comics", "WOL_PM"),
    "XM_DX": ("X-Men Deluxe", "Marvel Italia / Panini Comics", "XM_DX"),
    "MRVUN_M": ("Marvel Universe", "Panini Comics", "MRVUN_M"),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def prefix_and_number(issue_id: str) -> tuple[str, int]:
    prefix, raw = issue_id.split(":", 1)
    match = re.match(r"\d+", raw)
    if not match:
        raise RuntimeError(f"Numero non ricavabile da {issue_id}")
    return prefix, int(match.group())


def clean_catalog_issue(row: dict) -> dict:
    issue = {key: value for key, value in row.items() if key not in {"paths", "pathNames", "hubs"}}
    issue["required"] = True
    issue["skip"] = False
    issue["future"] = False
    issue["coverSource"] = issue.get("coverSource") or "ComicsBox"
    return issue


def fallback_issue(issue_id: str) -> dict:
    prefix, number = prefix_and_number(issue_id)
    series, publisher, cover_prefix = SERIES_META[prefix]
    try:
        name, title, date = FALLBACK_META[issue_id]
    except KeyError as exc:
        raise RuntimeError(f"Metadati italiani mancanti per {issue_id}") from exc
    return {
        "id": issue_id,
        "n": number,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": prefix,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{cover_prefix}_{number:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_prefix}_{number:03d}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
    }


def set_edition_coverage(payload: dict, edition_id: str, issue_ids: list[str], label: str) -> None:
    edition = next((row for row in payload.get("editions", []) if row.get("id") == edition_id), None)
    if edition is None:
        raise RuntimeError(f"Edizione alternativa {edition_id} non trovata")
    coverage = [row for row in edition.get("coverage", []) if row.get("path") != PATH_ID]
    coverage.append({"path": PATH_ID, "issueIds": issue_ids, "label": label})
    edition["coverage"] = coverage
    edition["coverageSource"] = "curated:siege-complete"


def main() -> None:
    current = read_json(DATA / "characters" / "siege.json")
    old_core = {row["id"]: row for row in current.get("issues", [])}
    if not all(f"MMMI:{number}" in old_core for number in range(107, 112)):
        raise RuntimeError("Core Assedio #107–111 non trovato")

    catalog = read_json(DATA / "catalog.json")
    catalog_by_id = {row["id"]: row for row in catalog.get("issues", [])}

    physical_to_chapters: dict[str, list[str]] = {}
    first_use: list[str] = []
    for chapter in READING_ORDER:
        issue_id = CHAPTER_TO_ITALIAN.get(chapter)
        if issue_id is None:
            raise RuntimeError(f"Capitolo senza mapping italiano: {chapter}")
        if issue_id not in physical_to_chapters:
            physical_to_chapters[issue_id] = []
            first_use.append(issue_id)
        physical_to_chapters[issue_id].append(chapter)

    if len(READING_ORDER) != 48 or len(first_use) != 26:
        raise RuntimeError(f"Conteggi inattesi: {len(READING_ORDER)} / {len(first_use)}")

    prelude_ids = {"IM_VEN2:20", "MMMI:102", "THORVE_M:128", "MMMI:106", "THORVE_M:138", "MMMI:107"}
    epilogue_ids = {"IM_VEN2:34", "THORVE_M:142", "THORVE_M:143"}
    issues = []
    for issue_id in first_use:
        if issue_id in old_core:
            issue = dict(old_core[issue_id])
            issue.update({"required": True, "skip": False, "future": False})
        elif issue_id in catalog_by_id:
            issue = clean_catalog_issue(catalog_by_id[issue_id])
        else:
            issue = fallback_issue(issue_id)

        chapters = physical_to_chapters[issue_id]
        issue["era"] = (
            "Prologo — Dark Reign" if issue_id in prelude_ids
            else "Epilogo — Età degli Eroi" if issue_id in epilogue_ids
            else "Assedio di Asgard"
        )
        displayed_chapters = [
            "Thor (2007) #600 — storia principale Victory/Vittoria"
            if chapter == "Thor (2007) #600"
            else chapter
            for chapter in chapters
        ]
        issue["instruction"] = (
            "Nel reading order completo usa questa pubblicazione per: "
            + "; ".join(displayed_chapters)
            + ". Se contiene altre storie, leggile soltanto quando ricompaiono nell'ordine salvato."
        )
        issues.append(issue)

    payload = {
        "id": PATH_ID,
        "name": "Assedio",
        "subtitle": "Dark Reign · Asgard — evento completo 2009–2011",
        "accent": "#7786b8",
        "start": "Iron Man e i potenti Vendicatori #20 — Dark Avengers #1",
        "end": "Thor #143 — New Avengers Finale · Sentry: Fallen Sun in Iron Man #34",
        "description": (
            "Percorso narrativo completo di Siege/Assedio: 48 capitoli USA ricondotti a 26 prime "
            "pubblicazioni fisiche italiane, dal preludio del Dark Reign agli epiloghi che aprono "
            "l'Età degli Eroi. Sono inclusi Embedded, tutti e cinque gli speciali Battlefield, le "
            "serie Avengers, Thor, Thunderbolts, Dark Wolverine, New Mutants, New Avengers Finale e "
            "Sentry: Fallen Sun. Siege: Storming Asgard — Heroes & Villains è escluso esplicitamente "
            "perché è un handbook enciclopedico, non un capitolo narrativo."
        ),
        "timelineMode": True,
        "eventScope": "complete",
        "readingOrderSource": (
            "Marvel Discover: Siege; bibliography completa dell'evento; cronologia narrativa "
            "verificata sulle prime pubblicazioni italiane ComicsBox"
        ),
        "readingOrder": READING_ORDER,
        "series": [
            {"id": "SIEGE-PRELUDE", "name": "Assedio — preludio Dark Reign", "publisher": "Panini Comics", "range": "Dark Avengers, Cabala, Thor e New Avengers", "years": "2009–2010"},
            {"id": "SIEGE-CORE", "name": "Assedio — evento e Embedded", "publisher": "Panini Comics", "range": "Siege #1–4 + Embedded #1–4", "years": "2010–2011"},
            {"id": "SIEGE-TIEINS", "name": "Assedio — tie-in ed epiloghi", "publisher": "Panini Comics", "range": "Avengers, Thor, X-Men, Thunderbolts e Battlefield", "years": "2010–2011"},
        ],
        "archives": [],
        "totalRequired": len(issues),
        "availableTotal": len(issues),
        "issues": issues,
    }
    write_json(DATA / "characters" / "siege.json", payload)

    manifest = read_json(DATA / "characters.json")
    manifest["version"] = MANIFEST_VERSION
    meta = next(row for row in manifest["characters"] if row["id"] == PATH_ID)
    meta.update({
        "subtitle": payload["subtitle"],
        "start": payload["start"],
        "end": payload["end"],
        "totalRequired": len(issues),
        "eventScope": "complete",
    })
    write_json(DATA / "characters.json", manifest)

    hubs = read_json(DATA / "hubs.json")
    event_hub = next(row for row in hubs["hubs"] if row["id"] == "events")
    groups = {row["id"]: row for row in event_hub["groups"]}
    for group_id, group in groups.items():
        if group_id != "complete":
            group["paths"] = [path for path in group.get("paths", []) if path != PATH_ID]
    complete = [path for path in groups["complete"]["paths"] if path != PATH_ID]
    insert_at = complete.index("secret-invasion") + 1 if "secret-invasion" in complete else len(complete)
    complete.insert(insert_at, PATH_ID)
    groups["complete"]["paths"] = complete
    write_json(DATA / "hubs.json", hubs)

    # These alternatives fully replace MMMI #107.  The Omnibus also replaces
    # Marvel Universe #2.  Their copies of Siege #1–4 and Fallen Sun are not
    # mapped onto mixed Italian issues, because those also contain Embedded or
    # Dark Avengers #16 and therefore are not complete one-for-one substitutes.
    for editions_path in (DATA / "editions.json", DATA / "curated-editions.json"):
        editions = read_json(editions_path)
        set_edition_coverage(
            editions,
            "MAROMNIB:21",
            ["MMMI:107", "MRVUN_M:2"],
            "Cabal/Origins + cinque speciali Battlefield; include anche Siege #1–4 e Fallen Sun, ma non sostituisce gli albi misti con Embedded o Dark Avengers #16",
        )
        set_edition_coverage(
            editions,
            "MARVELMUST:37",
            ["MMMI:107"],
            "Cabal/Origins; include anche Siege #1–4, ma non sostituisce gli albi misti #108–111 che contengono Embedded",
        )
        write_json(editions_path, editions)

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    old = 'assert.equal(manifest.version, 19, "Il manifest deve usare la versione cache v19");'
    new = 'assert.equal(manifest.version, 20, "Il manifest deve usare la versione cache v20");'
    if old not in verify and new not in verify:
        raise RuntimeError("Versione manifest attesa non trovata nel verifier")
    verify_path.write_text(verify.replace(old, new), encoding="utf-8")

    print(f"Assedio completo: {len(READING_ORDER)} capitoli USA -> {len(issues)} pubblicazioni italiane")


if __name__ == "__main__":
    main()
