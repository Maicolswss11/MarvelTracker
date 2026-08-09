#!/usr/bin/env python3
"""Upgrade Secret Invasion to the complete official Marvel reading order.

The path stores one node per first Italian physical publication. The full US
chapter sequence lives in `readingOrder`; collected editions remain alternative
physical editions whose coverage is mapped onto those Italian publications.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_VERSION = 18

READING_ORDER = [
    "New Avengers (2004) #31",
    "The Mighty Avengers (2007) #7",
    "New Avengers (2004) #34",
    "New Avengers: Illuminati (2006) #5",
    "Secret Invasion (2008) #1",
    "The Mighty Avengers (2007) #12",
    "New Avengers (2004) #40",
    "Secret Invasion (2008) #2",
    "The Mighty Avengers (2007) #13",
    "Captain Britain and MI:13 (2008) #1",
    "Secret Invasion: Fantastic Four (2008) #1",
    "The Mighty Avengers (2007) #14",
    "Incredible Hercules (2008) #117",
    "New Avengers (2004) #41",
    "Secret Invasion (2008) #3",
    "Secret Invasion: Who Do You Trust? (2008) #1",
    "Captain Britain and MI:13 (2008) #2",
    "Secret Invasion: Fantastic Four (2008) #2",
    "Incredible Hercules (2008) #118",
    "Secret Invasion: Runaways/Young Avengers (2008) #1",
    "Avengers: The Initiative (2007) #14",
    "The Mighty Avengers (2007) #15",
    "Ms. Marvel (2006) #28",
    "New Avengers (2004) #42",
    "Secret Invasion: Front Line (2008) #1",
    "Captain Britain and MI:13 (2008) #3",
    "Secret Invasion (2008) #4",
    "The Mighty Avengers (2007) #16",
    "X-Factor (2005) #33",
    "Incredible Hercules (2008) #119",
    "New Warriors (2007) #14",
    "Avengers: The Initiative (2007) #15",
    "She-Hulk (2005) #31",
    "New Avengers (2004) #43",
    "Thunderbolts (2006) #122",
    "Secret Invasion: Fantastic Four (2008) #3",
    "Ms. Marvel (2006) #29",
    "Black Panther (2005) #39",
    "Secret Invasion: Front Line (2008) #2",
    "Secret Invasion: X-Men (2008) #1",
    "Secret Invasion: Inhumans (2008) #1",
    "Secret Invasion: Thor (2008) #1",
    "Secret Invasion: Runaways/Young Avengers (2008) #2",
    "Captain Britain and MI:13 (2008) #4",
    "Secret Invasion (2008) #5",
    "Guardians of the Galaxy (2008) #4",
    "X-Factor (2005) #34",
    "Incredible Hercules (2008) #120",
    "Secret Invasion: The Amazing Spider-Man (2008) #1",
    "New Warriors (2007) #15",
    "Nova (2007) #16",
    "Avengers: The Initiative (2007) #16",
    "The Mighty Avengers (2007) #17",
    "She-Hulk (2005) #32",
    "Black Panther (2005) #40",
    "New Avengers (2004) #44",
    "Thunderbolts (2006) #123",
    "Secret Invasion: Front Line (2008) #3",
    "Deadpool (2008) #1",
    "Secret Invasion: Inhumans (2008) #2",
    "Secret Invasion: Runaways/Young Avengers (2008) #3",
    "Secret Invasion (2008) #6",
    "Ms. Marvel (2006) #30",
    "Secret Invasion: Thor (2008) #2",
    "Guardians of the Galaxy (2008) #5",
    "The Mighty Avengers (2007) #18",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #33",
    "Deadpool (2008) #2",
    "Secret Invasion: The Amazing Spider-Man (2008) #2",
    "Nova (2007) #17",
    "Avengers: The Initiative (2007) #17",
    "She-Hulk (2005) #33",
    "Black Panther (2005) #41",
    "New Avengers (2004) #45",
    "Thunderbolts (2006) #124",
    "Deadpool (2008) #3",
    "Secret Invasion: Inhumans (2008) #3",
    "Secret Invasion: Front Line (2008) #4",
    "Guardians of the Galaxy (2008) #6",
    "The Mighty Avengers (2007) #19",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #34",
    "Secret Invasion: The Amazing Spider-Man (2008) #3",
    "Secret Invasion (2008) #7",
    "New Avengers (2004) #46",
    "Thunderbolts (2006) #125",
    "Secret Invasion: X-Men (2008) #3",
    "Secret Invasion: Thor (2008) #3",
    "Nova (2007) #18",
    "Avengers: The Initiative (2007) #18",
    "Punisher War Journal (2006) #25",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #35",
    "Secret Invasion: X-Men (2008) #4",
    "Secret Invasion: Inhumans (2008) #4",
    "Secret Invasion: Front Line (2008) #5",
    "Secret Invasion (2008) #8",
    "New Avengers (2004) #47",
    "Secret Invasion: Dark Reign (2008) #1",
    "Avengers: The Initiative (2007) #19",
]

CHAPTER_TO_ITALIAN: dict[str, str | list[str]] = {
    "New Avengers (2004) #31": "THORVE_M:109",
    "The Mighty Avengers (2007) #7": "IM_VEN2:4",
    "New Avengers (2004) #34": "THORVE_M:112",
    "New Avengers: Illuminati (2006) #5": "THORVE_M:112",
    "Secret Invasion (2008) #1": "MMMI:93",
    "The Mighty Avengers (2007) #12": "IM_VEN2:11",
    "New Avengers (2004) #40": "THORVE_M:119",
    "Secret Invasion (2008) #2": "MMMI:94",
    "The Mighty Avengers (2007) #13": "IM_VEN2:12",
    "Captain Britain and MI:13 (2008) #1": "WOL_PM:231",
    "Secret Invasion: Fantastic Four (2008) #1": "F4_SM:294",
    "The Mighty Avengers (2007) #14": "IM_VEN2:13",
    "Incredible Hercules (2008) #117": "DEH_M:147",
    "New Avengers (2004) #41": "THORVE_M:120",
    "Secret Invasion (2008) #3": "MMMI:95",
    "Secret Invasion: Who Do You Trust? (2008) #1": ["MMMI:94", "MMMI:95"],
    "Captain Britain and MI:13 (2008) #2": "WOL_PM:232",
    "Secret Invasion: Fantastic Four (2008) #2": "F4_SM:295",
    "Incredible Hercules (2008) #118": "DEH_M:148",
    "Secret Invasion: Runaways/Young Avengers (2008) #1": "MCROS_M:58",
    "Avengers: The Initiative (2007) #14": "MA_MEG:49",
    "The Mighty Avengers (2007) #15": "IM_VEN2:14",
    "Ms. Marvel (2006) #28": "MARMONED:12",
    "New Avengers (2004) #42": "THORVE_M:121",
    "Secret Invasion: Front Line (2008) #1": "MMMI:96",
    "Captain Britain and MI:13 (2008) #3": "WOL_PM:233",
    "Secret Invasion (2008) #4": "MMMI:96",
    "The Mighty Avengers (2007) #16": "IM_VEN2:15",
    "X-Factor (2005) #33": "XM_DX:170",
    "Incredible Hercules (2008) #119": "DEH_M:149",
    "New Warriors (2007) #14": "MARMONED:12",
    "Avengers: The Initiative (2007) #15": "MA_MEG:49",
    "She-Hulk (2005) #31": "F4_SM:297",
    "New Avengers (2004) #43": "THORVE_M:122",
    "Thunderbolts (2006) #122": "SPIDER_MAIN:507",
    "Secret Invasion: Fantastic Four (2008) #3": "F4_SM:296",
    "Ms. Marvel (2006) #29": "MARMONED:12",
    "Black Panther (2005) #39": "MARMONED:12",
    "Secret Invasion: Front Line (2008) #2": "MMMI:97",
    "Secret Invasion: X-Men (2008) #1": "XM_SM:228",
    "Secret Invasion: Inhumans (2008) #1": "MA_MEG:51",
    "Secret Invasion: Thor (2008) #1": "MCROS_M:58",
    "Secret Invasion: Runaways/Young Avengers (2008) #2": "MCROS_M:58",
    "Captain Britain and MI:13 (2008) #4": "WOL_PM:234",
    "Secret Invasion (2008) #5": "MMMI:97",
    "Guardians of the Galaxy (2008) #4": "MCROS_M:56",
    "X-Factor (2005) #34": "XM_DX:171",
    "Incredible Hercules (2008) #120": "DEH_M:150",
    "Secret Invasion: The Amazing Spider-Man (2008) #1": "SPIDER_MAIN:506",
    "New Warriors (2007) #15": "MARMONED:12",
    "Nova (2007) #16": "MCROS_M:55",
    "Avengers: The Initiative (2007) #16": "MA_MEG:49",
    "The Mighty Avengers (2007) #17": "IM_VEN2:16",
    "She-Hulk (2005) #32": "F4_SM:298",
    "Black Panther (2005) #40": "MARMONED:12",
    "New Avengers (2004) #44": "THORVE_M:123",
    "Thunderbolts (2006) #123": "SPIDER_MAIN:508",
    "Secret Invasion: Front Line (2008) #3": "MMMI:98",
    "Deadpool (2008) #1": "WOL_PM:234",
    "Secret Invasion: Inhumans (2008) #2": "MA_MEG:51",
    "Secret Invasion: Runaways/Young Avengers (2008) #3": "MCROS_M:58",
    "Secret Invasion (2008) #6": "MMMI:98",
    "Ms. Marvel (2006) #30": "MARMONED:12",
    "Secret Invasion: Thor (2008) #2": "MCROS_M:58",
    "Guardians of the Galaxy (2008) #5": "MCROS_M:56",
    "The Mighty Avengers (2007) #18": "IM_VEN2:17",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #33": "IM_VEN2:13",
    "Deadpool (2008) #2": "WOL_PM:235",
    "Secret Invasion: The Amazing Spider-Man (2008) #2": "SPIDER_MAIN:506",
    "Nova (2007) #17": "MCROS_M:56",
    "Avengers: The Initiative (2007) #17": "MA_MEG:52",
    "She-Hulk (2005) #33": "F4_SM:299",
    "Black Panther (2005) #41": "MARMONED:12",
    "New Avengers (2004) #45": "THORVE_M:124",
    "Thunderbolts (2006) #124": "SPIDER_MAIN:509",
    "Deadpool (2008) #3": "WOL_PM:236",
    "Secret Invasion: Inhumans (2008) #3": "MA_MEG:51",
    "Secret Invasion: Front Line (2008) #4": "MMMI:99",
    "Guardians of the Galaxy (2008) #6": "MCROS_M:56",
    "The Mighty Avengers (2007) #19": "IM_VEN2:18",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #34": "IM_VEN2:14",
    "Secret Invasion: The Amazing Spider-Man (2008) #3": "SPIDER_MAIN:506",
    "Secret Invasion (2008) #7": "MMMI:99",
    "New Avengers (2004) #46": "THORVE_M:125",
    "Thunderbolts (2006) #125": "SPIDER_MAIN:510",
    "Secret Invasion: X-Men (2008) #3": "XM_SM:230",
    "Secret Invasion: Thor (2008) #3": "MCROS_M:58",
    "Nova (2007) #18": "MCROS_M:56",
    "Avengers: The Initiative (2007) #18": "MA_MEG:52",
    "Punisher War Journal (2006) #25": "MA_MEG:50",
    "Iron Man: Director of S.H.I.E.L.D. (2008) #35": "IM_VEN2:15",
    "Secret Invasion: X-Men (2008) #4": "XM_SM:231",
    "Secret Invasion: Inhumans (2008) #4": "MA_MEG:51",
    "Secret Invasion: Front Line (2008) #5": "MMMI:100",
    "Secret Invasion (2008) #8": "MMMI:100",
    "New Avengers (2004) #47": "THORVE_M:126",
    "Secret Invasion: Dark Reign (2008) #1": "MMMI:101",
    "Avengers: The Initiative (2007) #19": "MA_MEG:52",
}

FALLBACK_META = {
    "MCROS_M:55": ("Marvel Crossover #55", "Secret Invasion: Nova e i Guardiani della Galassia", "Aprile 2009"),
    "MCROS_M:56": ("Marvel Crossover #56", "Secret Invasion: Nova e i Guardiani della Galassia 2", "Giugno 2009"),
    "MCROS_M:58": ("Marvel Crossover #58", "Secret Invasion: Thor / Giovani Vendicatori / Runaways", "Agosto 2009"),
    "MA_MEG:49": ("Marvel Mega #49", "Avengers: The Initiative — Secret Invasion", "Aprile 2009"),
    "MA_MEG:50": ("Marvel Mega #50", "Punisher War Journal — Secret Invasion", "2009"),
    "MA_MEG:51": ("Marvel Mega #51", "Secret Invasion: Inumani", "2009"),
    "MA_MEG:52": ("Marvel Mega #52", "Avengers: The Initiative — Secret Invasion 2", "Settembre 2009"),
    "MARMONED:12": ("Marvel Monster Edition #12", "Secret Invasion", "Maggio 2009"),
    "XM_DX:170": ("X-Men Deluxe #170", "X-Factor — Secret Invasion", "Maggio 2009"),
    "XM_DX:171": ("X-Men Deluxe #171", "X-Factor — Secret Invasion", "Giugno 2009"),
    "MMMI:101": ("Marvel Miniserie #101", "Dark Reign Zero a", "Ottobre 2009"),
}

SERIES_META = {
    "THORVE_M": ("Thor / Nuovi Vendicatori", "Panini Comics", "THORVE_M"),
    "IM_VEN2": ("Iron Man e i potenti Vendicatori", "Panini Comics", "IM_VEN2"),
    "MMMI": ("Marvel Miniserie", "Marvel Italia / Panini Comics", "MMMI"),
    "WOL_PM": ("Wolverine", "Panini Comics", "WOL_PM"),
    "F4_SM": ("Fantastici Quattro", "Panini Comics", "F4_SM"),
    "DEH_M": ("Devil & Hulk", "Panini Comics", "DEH_M"),
    "MCROS_M": ("Marvel Crossover", "Panini Comics", "MCROS_M"),
    "MA_MEG": ("Marvel Mega", "Panini Comics", "MA_MEG"),
    "MARMONED": ("Marvel Monster Edition", "Panini Comics", "MARMONED"),
    "XM_DX": ("X-Men Deluxe", "Panini Comics", "XM_DX"),
    "XM_SM": ("Gli Incredibili X-Men", "Panini Comics", "XM_SM"),
    "SPIDER_MAIN": ("L'Uomo Ragno/Spider-Man", "Panini Comics", "UR_SM"),
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
    if issue_id in FALLBACK_META:
        name, title, date = FALLBACK_META[issue_id]
    else:
        name = f"{series} #{n}"
        title = "Secret Invasion — tie-in"
        date = "2009"
    return {
        "id": issue_id, "n": n, "name": name, "title": title, "date": date,
        "seriesId": cover_prefix, "series": series, "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{cover_prefix}_{n:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_prefix}_{n:03d}",
        "required": True, "skip": False, "future": False, "coverSource": "ComicsBox",
    }

def set_edition_coverage(editions: dict, edition_id: str, issue_ids: list[str], label: str) -> None:
    item = next((row for row in editions.get("editions", []) if row.get("id") == edition_id), None)
    if item is None:
        raise RuntimeError(f"Edizione {edition_id} non trovata")
    coverage = [row for row in item.get("coverage", []) if row.get("path") != "secret-invasion"]
    coverage.append({"path": "secret-invasion", "issueIds": issue_ids, "label": label})
    item["coverage"] = coverage
    item["coverageSource"] = "curated:secret-invasion-complete"

def main() -> None:
    current = read_json(DATA / "characters" / "secret-invasion.json")
    old_core = {row["id"]: row for row in current.get("issues", [])}
    if not all(f"MMMI:{n}" in old_core for n in range(93, 101)):
        raise RuntimeError("Core Secret Invasion #93–100 non trovato")

    catalog = read_json(DATA / "catalog.json")
    catalog_by_id = {row["id"]: row for row in catalog.get("issues", [])}

    physical_to_chapters: dict[str, list[str]] = {}
    first_use: list[str] = []
    for chapter in READING_ORDER:
        mapped = CHAPTER_TO_ITALIAN.get(chapter)
        if mapped is None:
            raise RuntimeError(f"Capitolo senza mapping italiano: {chapter}")
        ids = mapped if isinstance(mapped, list) else [mapped]
        for issue_id in ids:
            if issue_id not in physical_to_chapters:
                physical_to_chapters[issue_id] = []
                first_use.append(issue_id)
            physical_to_chapters[issue_id].append(chapter)

    if len(READING_ORDER) != 98 or len(first_use) != 62:
        raise RuntimeError(f"Conteggi inattesi: {len(READING_ORDER)} / {len(first_use)}")

    issues = []
    for issue_id in first_use:
        if issue_id in old_core:
            issue = dict(old_core[issue_id])
            issue["required"] = True
            issue["skip"] = False
            issue["future"] = False
        elif issue_id in catalog_by_id:
            issue = clean_catalog_issue(catalog_by_id[issue_id])
        else:
            issue = fallback_issue(issue_id)

        chapters = physical_to_chapters[issue_id]
        preview = "; ".join(chapters)
        issue["era"] = (
            "Prologo / infiltrazione" if issue_id in {"THORVE_M:109", "IM_VEN2:4", "THORVE_M:112"}
            else "Epilogo / Dark Reign" if issue_id in {"MMMI:101", "MA_MEG:52", "THORVE_M:126"}
            else "Evento completo"
        )
        issue["instruction"] = (
            f"Nel reading order ufficiale usa questa pubblicazione per: {preview}. "
            "Se contiene altre storie, leggile soltanto quando ricompaiono nell'ordine salvato."
        )
        issues.append(issue)

    payload = {
        "id": "secret-invasion", "name": "Secret Invasion",
        "subtitle": "Skrull · Avengers — evento completo 2008–2009", "accent": "#6cad6f",
        "start": "Thor / Nuovi Vendicatori #109 — New Avengers #31",
        "end": "Avengers: The Initiative #19 — epilogo Dark Reign",
        "description": "Percorso completo di Secret Invasion secondo la reading list ufficiale Marvel. I 98 capitoli USA sono ricondotti a 62 prime pubblicazioni fisiche italiane. Gli Omnibus e i cartonati restano edizioni alternative: possederli copre gli albi equivalenti senza trasformarli in spillati posseduti.",
        "timelineMode": True, "eventScope": "complete",
        "readingOrderSource": "Marvel official Secret Invasion: The Complete Event guide",
        "readingOrder": READING_ORDER,
        "series": [
            {"id": "SI-CORE", "name": "Secret Invasion — serie principale e Front Line", "publisher": "Panini Comics", "range": "core, Front Line, Dark Reign", "years": "2008–2009"},
            {"id": "SI-AVENGERS", "name": "Secret Invasion — Avengers", "publisher": "Panini Comics", "range": "New Avengers, Mighty Avengers, Initiative", "years": "2008–2009"},
            {"id": "SI-TIEINS", "name": "Secret Invasion — tie-in", "publisher": "Panini Comics", "range": "X-Men, FF, Thor, Spider-Man, cosmico e altri", "years": "2008–2009"},
        ],
        "archives": [], "totalRequired": len(issues), "availableTotal": len(issues), "issues": issues,
    }
    write_json(DATA / "characters" / "secret-invasion.json", payload)

    manifest = read_json(DATA / "characters.json")
    manifest["version"] = MANIFEST_VERSION
    meta = next(row for row in manifest["characters"] if row["id"] == "secret-invasion")
    meta.update({"subtitle": payload["subtitle"], "start": payload["start"], "end": payload["end"], "totalRequired": len(issues)})
    write_json(DATA / "characters.json", manifest)

    hubs = read_json(DATA / "hubs.json")
    event_hub = next(row for row in hubs["hubs"] if row["id"] == "events")
    groups = {row["id"]: row for row in event_hub["groups"]}
    groups["modern-core-1"]["paths"] = [p for p in groups["modern-core-1"]["paths"] if p != "secret-invasion"]
    complete = [p for p in groups["complete"]["paths"] if p != "secret-invasion"]
    insert_at = complete.index("civil-war") + 1 if "civil-war" in complete else 0
    complete.insert(insert_at, "secret-invasion")
    groups["complete"]["paths"] = complete
    write_json(DATA / "hubs.json", hubs)

    editions = read_json(DATA / "editions.json")
    core_ids = [f"MMMI:{n}" for n in range(93, 101)]
    set_edition_coverage(editions, "MAROMNIB:15", core_ids + ["THORVE_M:119"], "Secret Invasion #1–8 + New Avengers #40")
    set_edition_coverage(editions, "MAROMNIB:208", ["THORVE_M:112", *[f"THORVE_M:{n}" for n in range(119, 127)], "MMMI:101"], "New Avengers — Secret Invasion / Dark Reign")
    write_json(DATA / "editions.json", editions)

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    verify = verify.replace('assert.equal(manifest.version, 17, "Il manifest deve usare la versione cache v17");', 'assert.equal(manifest.version, 18, "Il manifest deve usare la versione cache v18");')
    verify_path.write_text(verify, encoding="utf-8")

    print(f"Secret Invasion completo: {len(READING_ORDER)} capitoli USA -> {len(issues)} pubblicazioni italiane")

if __name__ == "__main__":
    main()
