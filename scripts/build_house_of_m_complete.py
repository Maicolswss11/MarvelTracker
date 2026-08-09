#!/usr/bin/env python3
"""Upgrade House of M to the complete official Marvel event reading order.

The canonical tracker route contains one node per mapped Italian physical
publication. The full 47-chapter US sequence stays in `readingOrder`; chapters
without a censused Italian edition are recorded explicitly in `italianGaps`
instead of being represented by fake physical issues.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_VERSION = 19

READING_ORDER = [
    "House of M (2005) #1",
    "House of M (2005) #2",
    "Fantastic Four: House of M (2005) #1",
    "Spider-Man: House of M (2005) #1",
    "Iron Man: House of M (2005) #1",
    "House of M (2005) #3",
    "Hulk (1999) #83",
    "Uncanny X-Men (1963) #462",
    "Mutopia X (2005) #1",
    "Spider-Man: House of M (2005) #2",
    "House of M (2005) #4",
    "Cable & Deadpool (2004) #17",
    "Hulk (1999) #84",
    "The Pulse (2004) #10",
    "New X-Men (2004) #16",
    "Fantastic Four: House of M (2005) #2",
    "Iron Man: House of M (2005) #2",
    "Uncanny X-Men (1963) #463",
    "House of M (2005) #5",
    "New Thunderbolts (2005) #11",
    "Hulk (1999) #85",
    "Mutopia X (2005) #2",
    "Spider-Man: House of M (2005) #3",
    "Black Panther (2005) #7",
    "New X-Men (2004) #17",
    "Fantastic Four: House of M (2005) #3",
    "Iron Man: House of M (2005) #3",
    "Exiles (2001) #69",
    "Hulk (1999) #86",
    "Uncanny X-Men (1963) #464",
    "Mutopia X (2005) #3",
    "Captain America (2004) #10",
    "Exiles (2001) #70",
    "Spider-Man: House of M (2005) #4",
    "New X-Men (2004) #18",
    "Wolverine (2003) #33",
    "Uncanny X-Men (1963) #465",
    "House of M (2005) #6",
    "Mutopia X (2005) #4",
    "House of M (2005) #7",
    "Wolverine (2003) #34",
    "Exiles (2001) #71",
    "New X-Men (2004) #19",
    "Wolverine (2003) #35",
    "Spider-Man: House of M (2005) #5",
    "House of M (2005) #8",
    "Decimation: House of M - The Day After (2005) #1",
]

CHAPTER_TO_ITALIAN = {
    "House of M (2005) #1": "MMMI:69",
    "House of M (2005) #2": "MMMI:69",
    "Fantastic Four: House of M (2005) #1": "SPEE_M:53",
    "Spider-Man: House of M (2005) #1": "MCROS_M:42",
    "Iron Man: House of M (2005) #1": "IM_VEN:85",
    "House of M (2005) #3": "MMMI:70",
    "Hulk (1999) #83": "DEH_M:119",
    "Uncanny X-Men (1963) #462": "XM_SM:190",
    "Spider-Man: House of M (2005) #2": "MCROS_M:42",
    "House of M (2005) #4": "MMMI:70",
    "Cable & Deadpool (2004) #17": "100M:172",
    "Hulk (1999) #84": "DEH_M:120",
    "The Pulse (2004) #10": "IM_VEN:85",
    "New X-Men (2004) #16": "MA_MEG:37",
    "Fantastic Four: House of M (2005) #2": "SPEE_M:53",
    "Iron Man: House of M (2005) #2": "IM_VEN:85",
    "Uncanny X-Men (1963) #463": "XM_SM:191",
    "House of M (2005) #5": "MMMI:71",
    "Hulk (1999) #85": "DEH_M:121",
    "Spider-Man: House of M (2005) #3": "MCROS_M:42",
    "Black Panther (2005) #7": "SPEE_M:53",
    "New X-Men (2004) #17": "MA_MEG:37",
    "Fantastic Four: House of M (2005) #3": "SPEE_M:53",
    "Iron Man: House of M (2005) #3": "IM_VEN:85",
    "Exiles (2001) #69": "XM_DX:140",
    "Hulk (1999) #86": "DEH_M:122",
    "Uncanny X-Men (1963) #464": "XM_SM:192",
    "Captain America (2004) #10": "THORVE_M:87",
    "Exiles (2001) #70": "XM_DX:141",
    "Spider-Man: House of M (2005) #4": "MCROS_M:42",
    "New X-Men (2004) #18": "MA_MEG:37",
    "Wolverine (2003) #33": "WOL_PM:198",
    "Uncanny X-Men (1963) #465": "XM_SM:193",
    "House of M (2005) #6": "MMMI:71",
    "House of M (2005) #7": "MMMI:72",
    "Wolverine (2003) #34": "WOL_PM:198",
    "Exiles (2001) #71": "XM_DX:141",
    "New X-Men (2004) #19": "MA_MEG:37",
    "Wolverine (2003) #35": "WOL_PM:198",
    "Spider-Man: House of M (2005) #5": "MCROS_M:42",
    "House of M (2005) #8": "MMMI:72",
    "Decimation: House of M - The Day After (2005) #1": "XM_SM:194",
}

ITALIAN_GAPS = [
    "Mutopia X (2005) #1",
    "New Thunderbolts (2005) #11",
    "Mutopia X (2005) #2",
    "Mutopia X (2005) #3",
    "Mutopia X (2005) #4",
]

SERIES_META = {
    "MMMI": ("Marvel Miniserie", "Marvel Italia / Panini Comics", "MMMI"),
    "SPEE_M": ("Special Events", "Marvel Italia / Panini Comics", "SPEE_M"),
    "MCROS_M": ("Marvel Crossover", "Marvel Italia / Panini Comics", "MCROS_M"),
    "IM_VEN": ("Iron Man e i Vendicatori", "Marvel Italia", "IM_VEN"),
    "DEH_M": ("Devil & Hulk", "Marvel Italia / Panini Comics", "DEH_M"),
    "XM_SM": ("Gli Incredibili X-Men", "Marvel Italia / Panini Comics", "XM_SM"),
    "100M": ("100% Marvel", "Marvel Italia / Panini Comics", "100M"),
    "MA_MEG": ("Marvel Mega", "Marvel Italia / Panini Comics", "MA_MEG"),
    "XM_DX": ("X-Men Deluxe", "Marvel Italia / Panini Comics", "XM_DX"),
    "THORVE_M": ("Thor", "Marvel Italia / Panini Comics", "THORVE_M"),
    "WOL_PM": ("Wolverine", "Marvel Italia / Panini Comics", "WOL_PM"),
}

FALLBACK_META = {
    "MMMI:69": ("Marvel Miniserie #69", "House of M, pt 1", "Aprile 2006"),
    "MMMI:70": ("Marvel Miniserie #70", "House of M, pt 2", "Maggio 2006"),
    "MMMI:71": ("Marvel Miniserie #71", "House of M, pt 3", "Giugno 2006"),
    "MMMI:72": ("Marvel Miniserie #72", "House of M, pt 4", "Luglio 2006"),
    "SPEE_M:53": ("Special Events #53", "Fantastici Quattro: House of M Special", "Giugno 2006"),
    "MCROS_M:42": ("Marvel Crossover #42", "L'Uomo Ragno - House of M Special", "Aprile 2006"),
    "IM_VEN:85": ("Iron Man e i Vendicatori #85", "Iron Man: House of M", "Giugno 2006"),
    "DEH_M:119": ("Devil & Hulk #119", "House of M — Hulk", "2006"),
    "DEH_M:120": ("Devil & Hulk #120", "House of M — Hulk", "2006"),
    "DEH_M:121": ("Devil & Hulk #121", "House of M — Hulk", "2006"),
    "DEH_M:122": ("Devil & Hulk #122", "House of M — Hulk", "2006"),
    "XM_SM:190": ("Gli Incredibili X-Men #190", "House of M", "2006"),
    "XM_SM:191": ("Gli Incredibili X-Men #191", "House of M", "2006"),
    "XM_SM:192": ("Gli Incredibili X-Men #192", "House of M", "2006"),
    "XM_SM:193": ("Gli Incredibili X-Men #193", "House of M", "2006"),
    "XM_SM:194": ("Gli Incredibili X-Men #194", "Decimation: House of M - The Day After", "2006"),
    "100M:172": ("100% Marvel #172", "Cable & Deadpool, vol 3: Pericolo pubblico", "Dicembre 2013"),
    "MA_MEG:37": ("Marvel Mega #37", "House of M Special: New X-Men", "Luglio 2006"),
    "XM_DX:140": ("X-Men Deluxe #140", "House of M — Exiles", "2006"),
    "XM_DX:141": ("X-Men Deluxe #141", "House of M — Exiles", "2006"),
    "THORVE_M:87": ("Thor #87", "House of M — Capitan America", "2006"),
    "WOL_PM:198": ("Wolverine #198", "House of M", "2006"),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


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
    prefix, n = prefix_and_number(issue_id)
    series, publisher, cover_prefix = SERIES_META[prefix]
    name, title, date = FALLBACK_META[issue_id]
    return {
        "id": issue_id,
        "n": n,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": cover_prefix,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{cover_prefix}_{n:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_prefix}_{n:03d}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
    }


def main() -> None:
    if len(READING_ORDER) != 47:
        raise RuntimeError(f"Reading order House of M inatteso: {len(READING_ORDER)}")
    if set(READING_ORDER) != set(CHAPTER_TO_ITALIAN) | set(ITALIAN_GAPS):
        missing = set(READING_ORDER) - set(CHAPTER_TO_ITALIAN) - set(ITALIAN_GAPS)
        extra = (set(CHAPTER_TO_ITALIAN) | set(ITALIAN_GAPS)) - set(READING_ORDER)
        raise RuntimeError(f"Audit incompleto. Missing={missing}; extra={extra}")
    if len(CHAPTER_TO_ITALIAN) != 42 or len(ITALIAN_GAPS) != 5:
        raise RuntimeError("Conteggio copertura italiana House of M inatteso")

    current = read_json(DATA / "characters" / "house-of-m.json")
    old_core = {row["id"]: row for row in current.get("issues", [])}
    if not all(f"MMMI:{n}" in old_core for n in range(69, 73)):
        raise RuntimeError("Core House of M #69–72 non trovato")

    catalog = read_json(DATA / "catalog.json")
    catalog_by_id = {row["id"]: row for row in catalog.get("issues", [])}

    physical_to_chapters: dict[str, list[str]] = {}
    physical_positions: dict[str, list[int]] = {}
    first_use: list[str] = []
    for position, chapter in enumerate(READING_ORDER, start=1):
        issue_id = CHAPTER_TO_ITALIAN.get(chapter)
        if issue_id is None:
            continue
        if issue_id not in physical_to_chapters:
            physical_to_chapters[issue_id] = []
            physical_positions[issue_id] = []
            first_use.append(issue_id)
        physical_to_chapters[issue_id].append(chapter)
        physical_positions[issue_id].append(position)

    if len(first_use) != 22:
        raise RuntimeError(f"Pubblicazioni italiane House of M inattese: {len(first_use)}")

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
        positions = physical_positions[issue_id]
        issue["era"] = "Epilogo / Decimation" if issue_id == "XM_SM:194" else "Evento completo"
        issue["readingOrderPositions"] = positions
        issue["instruction"] = (
            f"Nel reading order ufficiale usa questa pubblicazione ai passaggi {', '.join(map(str, positions))}: "
            f"{'; '.join(chapters)}. Se l'albo contiene altre storie, leggile soltanto quando richiesto dall'ordine."
        )
        issues.append(issue)

    payload = {
        "id": "house-of-m",
        "name": "House of M",
        "subtitle": "Avengers · X-Men · Scarlet Witch — evento completo 2005–2006",
        "accent": "#d84b74",
        "start": "Marvel Miniserie #69 — House of M #1–2",
        "end": "Gli Incredibili X-Men #194 — Decimation: The Day After",
        "description": (
            "Percorso completo di House of M secondo la reading list ufficiale Marvel. "
            "L'ordine comprende 47 capitoli USA: 42 sono ricondotti a 22 pubblicazioni fisiche italiane; "
            "Mutopia X #1–4 e New Thunderbolts #11 non hanno una pubblicazione italiana censita nell'audit e "
            "restano quindi buchi dichiarati, non albi fittizi. Omnibus, Deluxe e Must-Have rimangono edizioni "
            "alternative e coprono soltanto le pubblicazioni esplicitamente mappate."
        ),
        "timelineMode": True,
        "eventScope": "complete",
        "readingOrderSource": "Marvel official House of M: The Complete Event guide",
        "readingOrder": READING_ORDER,
        "italianCoverage": {
            "officialChapters": len(READING_ORDER),
            "mappedChapters": len(CHAPTER_TO_ITALIAN),
            "unmappedChapters": len(ITALIAN_GAPS),
            "physicalPublications": len(issues),
        },
        "italianGaps": [
            {"chapter": chapter, "reason": "Nessuna pubblicazione italiana censita nell'audit"}
            for chapter in ITALIAN_GAPS
        ],
        "series": [
            {"id": "HOM-CORE", "name": "House of M — serie principale", "publisher": "Marvel Italia / Panini Comics", "range": "House of M #1–8", "years": "2006"},
            {"id": "HOM-X", "name": "House of M — X-Men e mutanti", "publisher": "Marvel Italia / Panini Comics", "range": "Uncanny X-Men, New X-Men, Exiles, Wolverine, Decimation", "years": "2006"},
            {"id": "HOM-TIEINS", "name": "House of M — tie-in", "publisher": "Marvel Italia / Panini Comics", "range": "Spider-Man, Fantastic Four, Iron Man, Hulk, Capitan America, Cable & Deadpool, Black Panther", "years": "2006–2013"},
        ],
        "archives": [],
        "totalRequired": len(issues),
        "availableTotal": len(issues),
        "issues": issues,
    }
    write_json(DATA / "characters" / "house-of-m.json", payload)

    manifest = read_json(DATA / "characters.json")
    manifest["version"] = MANIFEST_VERSION
    meta = next(row for row in manifest["characters"] if row["id"] == "house-of-m")
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
            group["paths"] = [p for p in group.get("paths", []) if p != "house-of-m"]
    complete = [p for p in groups["complete"]["paths"] if p != "house-of-m"]
    complete.insert(0, "house-of-m")
    groups["complete"]["paths"] = complete
    write_json(DATA / "hubs.json", hubs)

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    old = 'assert.equal(manifest.version, 18, "Il manifest deve usare la versione cache v18");'
    new = 'assert.equal(manifest.version, 19, "Il manifest deve usare la versione cache v19");'
    if old not in verify and new not in verify:
        raise RuntimeError("Versione manifest attesa non trovata nel verifier")
    verify = verify.replace(old, new)
    verify_path.write_text(verify, encoding="utf-8")

    print(
        "House of M completo: "
        f"{len(READING_ORDER)} capitoli USA / {len(CHAPTER_TO_ITALIAN)} mappati / "
        f"{len(ITALIAN_GAPS)} gap / {len(issues)} pubblicazioni italiane"
    )


if __name__ == "__main__":
    main()
