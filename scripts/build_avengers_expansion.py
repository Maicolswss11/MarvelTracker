#!/usr/bin/env python3
"""Build the second Avengers character expansion for MarvelTracker.

Routes:
- Hawkeye (Clint Barton)
- Black Widow (Natasha Romanoff)
- Black Panther (T'Challa)
- Captain Marvel (Carol Danvers)
- She-Hulk (Jennifer Walters)

The Avengers timeline remains the narrative backbone. Shared physical issues reuse
exactly the same issue IDs as the Avengers route. Dedicated Italian volumes are
selected from Marvel Collection II and positioned by the earliest US story date
found on the ComicsBox issue page, rather than by the later Italian collection date.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import build_avengers_characters as base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ROUTES = {
    "hawkeye": {
        "name": "Occhio di Falco",
        "subtitle": "Clint Barton",
        "accent": "#a875d6",
        "logo": "assets/heroes/hawkeye.svg",
        "description": "Percorso italiano di Clint Barton: apparizioni nei Vendicatori e principali cicli solisti di Occhio di Falco.",
        "label": ("HF", "HAWKEYE"),
    },
    "blackwidow": {
        "name": "Vedova Nera",
        "subtitle": "Natasha Romanoff",
        "accent": "#d95058",
        "logo": "assets/heroes/black-widow.svg",
        "description": "Percorso italiano di Natasha Romanoff: spy story personali, missioni in solitaria e apparizioni nei Vendicatori.",
        "label": ("BW", "NATASHA"),
    },
    "blackpanther": {
        "name": "Pantera Nera",
        "subtitle": "T'Challa",
        "accent": "#8f79c9",
        "logo": "assets/heroes/black-panther.svg",
        "description": "Percorso italiano di T'Challa: Wakanda, cicli personali di Pantera Nera e apparizioni nei Vendicatori.",
        "label": ("BP", "T'CHALLA"),
    },
    "captainmarvel": {
        "name": "Captain Marvel",
        "subtitle": "Carol Danvers",
        "accent": "#e9b84a",
        "logo": "assets/heroes/captain-marvel.svg",
        "description": "Percorso italiano di Carol Danvers: l'era di Captain Marvel, avventure cosmiche e apparizioni nei Vendicatori.",
        "label": ("CM", "CAROL"),
    },
    "shehulk": {
        "name": "She-Hulk",
        "subtitle": "Jennifer Walters",
        "accent": "#73c66a",
        "logo": "assets/heroes/she-hulk.svg",
        "description": "Percorso italiano di Jennifer Walters: serie personali di She-Hulk e tappe condivise con i Vendicatori.",
        "label": ("SH", "JEN"),
    },
}

MONTHS = {
    "jan": 1, "gen": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5, "mag": 5,
    "jun": 6, "giu": 6,
    "jul": 7, "lug": 7,
    "aug": 8, "ago": 8,
    "sep": 9, "set": 9,
    "oct": 10, "ott": 10,
    "nov": 11,
    "dec": 12, "dic": 12,
}


def person_matches(route_id: str, href: str, text: str) -> bool:
    if "personaggio/" not in href:
        return False
    h = base.normalize(href)
    t = base.normalize(text)
    hay = f"{h} {t}"

    if route_id == "hawkeye":
        if "kate bishop" in hay:
            return False
        return (
            "clint barton" in hay
            or "barton clint" in hay
            or t in {"hawkeye", "occhio di falco"}
            or h.endswith("personaggio hawkeye")
        )
    if route_id == "blackwidow":
        if "yelena" in hay:
            return False
        return (
            "natasha romanoff" in hay
            or "romanoff natasha" in hay
            or t in {"black widow", "vedova nera"}
            or h.endswith("personaggio blackwidow")
        )
    if route_id == "blackpanther":
        if "shuri" in hay:
            return False
        return (
            "t challa" in hay
            or "tchalla" in hay
            or t in {"black panther", "pantera nera"}
            or h.endswith("personaggio blackpanther")
        )
    if route_id == "captainmarvel":
        if any(alias in hay for alias in ("monica rambeau", "mar vell", "genis vell", "photon", "spectrum")):
            return False
        return (
            "carol danvers" in hay
            or "danvers carol" in hay
            or t in {"captain marvel", "capitan marvel"}
            or h.endswith("personaggio captainmarvel")
        )
    if route_id == "shehulk":
        return (
            "jennifer walters" in hay
            or "walters jennifer" in hay
            or t in {"she hulk", "she-hulk"}
            or h.endswith("personaggio shehulk")
        )
    return False


def scan_avengers_issue(issue: dict) -> tuple[str, set[str]]:
    parser = base.parse_issue(issue["url"])
    matched: set[str] = set()
    for href, text in parser.links:
        for route_id in ROUTES:
            if person_matches(route_id, href, text):
                matched.add(route_id)
    return issue["id"], matched


def dedicated_match(route_id: str, title: str) -> bool:
    value = base.normalize(title)
    if route_id == "hawkeye":
        return (
            ("occhio di falco" in value or re.search(r"\bhawkeye\b", value))
            and "kate bishop" not in value
            and "vecchio occhio" not in value
            and "old man" not in value
        )
    if route_id == "blackwidow":
        return ("vedova nera" in value or "black widow" in value) and "vedova bianca" not in value
    if route_id == "blackpanther":
        return ("pantera nera" in value or "black panther" in value) and "ultimate" not in value
    if route_id == "captainmarvel":
        return ("captain marvel" in value or "capitan marvel" in value) and "ultimate" not in value
    if route_id == "shehulk":
        return (
            ("she hulk" in value or "she-hulk" in title.lower())
            and not value.startswith("avengers")
            and "world war she hulk" not in value
        )
    return False


def earliest_us_story_sort(url: str, fallback_date: str) -> tuple[int, int]:
    source = base.fetch_url(url)
    candidates: list[tuple[int, int]] = []
    # ComicsBox localizes month abbreviations inconsistently; accept both IT and EN.
    for month_token, year_text in re.findall(
        r"Marvel Comics\s*-\s*USA\s*\(\s*([A-Za-zÀ-ÿ]{3,10})\s+((?:19|20)\d{2})\s*\)",
        source,
        flags=re.I,
    ):
        month = MONTHS.get(base.normalize(month_token)[:3], 6)
        candidates.append((int(year_text), month))
    if candidates:
        return min(candidates)
    return base.date_parts(base.italian_date(fallback_date))


def dedicated_volume(route_id: str, row: dict[str, str], number: int) -> dict:
    url = urljoin("https://www.comicsbox.it", row["href"])
    story_year, story_month = earliest_us_story_sort(url, row["date"])
    title = row["title"] or ROUTES[route_id]["name"]
    issue = base.row_issue(
        "MVNWCOL_P",
        "Marvel Collection II",
        "Panini Comics",
        row,
        number,
        sort_year=story_year,
        sort_month=story_month,
        era=f"{ROUTES[route_id]['name']} — percorso personale",
        era_sub=title,
        instruction="Leggi il volume completo in questa posizione narrativa; l'ordine segue le storie USA contenute, non la data della ristampa italiana.",
        chronology_insert=True,
    )
    issue["storyOrder"] = f"{story_year:04d}-{story_month:02d}"
    return issue


def build_dedicated_volumes() -> dict[str, list[dict]]:
    rows = base.fetch_all_series("MVNWCOL_P", 20)
    selected: dict[str, list[tuple[int, dict[str, str]]]] = {route_id: [] for route_id in ROUTES}
    for number, row in rows.items():
        for route_id in ROUTES:
            if dedicated_match(route_id, row.get("title", "")):
                selected[route_id].append((number, row))

    result: dict[str, list[dict]] = {route_id: [] for route_id in ROUTES}
    for route_id, items in selected.items():
        print(f"{ROUTES[route_id]['name']}: {len(items)} volumi Marvel Collection II candidati")
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(dedicated_volume, route_id, row, number): number
                for number, row in items
            }
            for future in as_completed(futures):
                result[route_id].append(future.result())
    return result


def make_character(route_id: str, issues: list[dict], avengers: dict) -> dict:
    cfg = ROUTES[route_id]
    issues = base.dedupe_and_sequence(issues)
    if not issues:
        raise RuntimeError(f"{route_id}: nessuna tappa generata")
    avengers_series_meta = {item["id"]: item for item in avengers.get("series", [])}
    first, last = issues[0], issues[-1]
    return {
        "id": route_id,
        "name": cfg["name"],
        "subtitle": cfg["subtitle"],
        "accent": cfg["accent"],
        "start": f"{first['era']} — {first['title']}",
        "end": f"{last['name']} — {last['date']}",
        "description": cfg["description"],
        "timelineMode": True,
        "series": base.series_summary(issues, avengers_series_meta),
        "archives": [],
        "totalRequired": len(issues),
        "issues": issues,
    }


def write_stub(character: dict) -> None:
    stub = {key: value for key, value in character.items() if key != "issues"}
    stub["issueSources"] = [f"data/encoded/{character['id']}.json"]
    (DATA / "characters" / f"{character['id']}.json").write_text(
        json.dumps(stub, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def update_manifest(characters: dict[str, dict]) -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = 12
    existing = {item["id"]: item for item in manifest["characters"]}

    for route_id, character in characters.items():
        cfg = ROUTES[route_id]
        existing[route_id] = {
            "id": route_id,
            "name": cfg["name"],
            "subtitle": cfg["subtitle"],
            "type": "character",
            "primaryHub": "avengers",
            "hubs": ["avengers"],
            "accent": cfg["accent"],
            "logo": cfg["logo"],
            "data": f"data/characters/{route_id}.json",
            "start": character["start"],
            "end": character["end"],
            "totalRequired": character["totalRequired"],
        }

    expansion = list(ROUTES)
    order = [item["id"] for item in manifest["characters"] if item["id"] not in expansion]
    anchor = order.index("wonderman") + 1 if "wonderman" in order else len(order)
    order[anchor:anchor] = expansion
    manifest["characters"] = [existing[item_id] for item_id in order]
    path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update_hubs() -> None:
    path = DATA / "hubs.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    avengers = next(hub for hub in doc["hubs"] if hub["id"] == "avengers")
    members = next(group for group in avengers["groups"] if group["id"] == "members")
    for route_id in ROUTES:
        if route_id not in members["paths"]:
            members["paths"].append(route_id)
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update_ui_art(dedicated: dict[str, list[dict]], characters: dict[str, dict]) -> None:
    path = DATA / "ui-art.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["manifestVersion"] = 12
    path_map = doc.setdefault("paths", {})
    for route_id in ROUTES:
        candidates = sorted(dedicated[route_id], key=lambda issue: issue.get("storyOrder", "9999-99"))
        if candidates:
            path_map[route_id] = candidates[0]["cover"]
        else:
            path_map[route_id] = characters[route_id]["issues"][0]["cover"]
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def write_icons() -> None:
    assets = ROOT / "assets" / "heroes"
    assets.mkdir(parents=True, exist_ok=True)
    for route_id, cfg in ROUTES.items():
        label, subtitle = cfg["label"]
        filename = Path(cfg["logo"]).name
        (assets / filename).write_text(base.icon_svg(label, subtitle, cfg["accent"]), encoding="utf-8")


def main() -> None:
    avengers = base.unpack_character("avengers")
    avengers_issues = [issue for issue in avengers["issues"] if not issue.get("future")]
    print(f"Analizzo {len(avengers_issues)} tappe Vendicatori per la seconda espansione…")

    matches: dict[str, set[str]] = {route_id: set() for route_id in ROUTES}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(scan_avengers_issue, issue) for issue in avengers_issues]
        for future in as_completed(futures):
            issue_id, route_ids = future.result()
            for route_id in route_ids:
                matches[route_id].add(issue_id)

    route_issues: dict[str, list[dict]] = {route_id: [] for route_id in ROUTES}
    for route_id, cfg in ROUTES.items():
        for issue in avengers_issues:
            if issue["id"] in matches[route_id]:
                route_issues[route_id].append(base.copy_shared_issue(issue, cfg["name"]))
        print(f"{cfg['name']}: {len(route_issues[route_id])} albi condivisi con Vendicatori")

    dedicated = build_dedicated_volumes()
    for route_id in ROUTES:
        route_issues[route_id].extend(dedicated[route_id])

    characters: dict[str, dict] = {}
    for route_id in ROUTES:
        character = make_character(route_id, route_issues[route_id], avengers)
        write_stub(character)
        base.pack_character(character)
        characters[route_id] = character

    update_manifest(characters)
    update_hubs()
    update_ui_art(dedicated, characters)
    write_icons()

    print("\nRiepilogo:")
    for route_id, character in characters.items():
        shared = sum(1 for issue in character["issues"] if "Vendicatori" in issue.get("sharedWith", []))
        dedicated_count = len(character["issues"]) - shared
        print(f"- {character['name']}: {character['totalRequired']} tappe ({shared} Avengers + {dedicated_count} volumi personali)")


if __name__ == "__main__":
    main()
