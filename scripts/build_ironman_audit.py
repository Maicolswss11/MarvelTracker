#!/usr/bin/env python3
"""Rebuild Iron Man from Iron Man (1968) #1 through the existing modern Italian route.

Editorial model:
    Italian physical issue -> USA story/issue contents -> path-local readingStep

The classic spine begins with Iron Man vol.1 #1, not Tales of Suspense #39.
ComicsBox first-Italian-publication links define the primary physical edition;
later Masterworks/collections are handled by the dedicated alternatives audit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_cosmic_supernatural_expansion as legacy
import build_five_character_expansion as five

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "ironman"
AUDIT_PATH = DATA / "ironman-audit.json"
AUDIT_DATE = "2026-08-16"
CLASSIC_SERIES = "IM1"
CLASSIC_END = 306
TAIL_ANCHOR = "IM_VEN:1"


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def number_token(value: str) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def era_for(number: int) -> tuple[str, str]:
    ranges = [
        (24, "Origini della testata", "Archie Goodwin e il primo ciclo della serie autonoma"),
        (82, "Età classica", "Dalla fase Goodwin/Tuska alla prima maturità della testata"),
        (128, "Demon in a Bottle e Michelinie/Layton", "Justin Hammer, alcolismo e consolidamento di Tony Stark"),
        (157, "Stark International", "La fase successiva a Demon in a Bottle"),
        (200, "Obadiah Stane / Iron Monger", "La caduta e la ricostruzione di Tony Stark"),
        (232, "Armor Wars", "Michelinie/Layton e la Guerra delle Armature"),
        (266, "Verso Armor Wars II", "Dalla fine degli anni Ottanta alla seconda Guerra delle Armature"),
        (306, "Anni Novanta / War Machine", "Len Kaminski, War Machine e il ponte verso Marvel Italia"),
    ]
    for maximum, era, subtitle in ranges:
        if number <= maximum:
            return era, subtitle
    return "Iron Man classico", "Iron Man vol.1"


def load_all_story_rows() -> tuple[str, list[dict[str, Any]]]:
    """Read every ComicsBox story row, keeping same-issue backups instead of deduping by issue."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    name = ""
    empty_pages = 0
    for offset in range(0, 600, 50):
        parser = legacy.ForeignSeriesParser(CLASSIC_SERIES)
        parser.feed(legacy.fetch_text(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={CLASSIC_SERIES}"))
        if parser.name and not name:
            name = parser.name
        fresh = 0
        for row in parser.rows:
            number = number_token(row.get("number", ""))
            if number is None or number < 1 or number > CLASSIC_END:
                continue
            key = (
                row.get("code", ""),
                row.get("title", ""),
                row.get("italianCode", ""),
                row.get("authors", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            item = deepcopy(row)
            item["numberInt"] = number
            rows.append(item)
            fresh += 1
        if not parser.rows:
            empty_pages += 1
            if empty_pages >= 1:
                break
        else:
            empty_pages = 0
    if not rows:
        raise RuntimeError("IM1: nessuna storia letta da ComicsBox")
    present_numbers = {row["numberInt"] for row in rows}
    missing_numbers = [number for number in range(1, CLASSIC_END + 1) if number not in present_numbers]
    if missing_numbers:
        raise RuntimeError("IM1: numeri USA assenti dall'indice: " + ", ".join(map(str, missing_numbers)))
    rows.sort(key=lambda row: (
        legacy.original_date_key(row.get("date", ""), 0, row.get("number", "")),
        row.get("code", ""),
        row.get("title", ""),
    ))
    return name or "Iron Man Vol 1", rows


def story_chapters() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    series_name, rows = load_all_story_rows()
    per_issue_ordinal: dict[str, int] = defaultdict(int)
    chapters: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        number = row["numberInt"]
        source_code = row["code"]
        per_issue_ordinal[source_code] += 1
        ordinal = per_issue_ordinal[source_code]
        era, era_sub = era_for(number)
        title = row.get("title", "") or f"storia {ordinal}"
        chapters.append({
            "kind": "story",
            "sourceCode": CLASSIC_SERIES,
            "sourceName": series_name,
            "usaCode": source_code,
            "usaNumber": row.get("number", str(number)),
            "usaNumberInt": number,
            "usaTitle": title,
            "usaDate": row.get("date", ""),
            "authors": row.get("authors", ""),
            "storyOrdinal": ordinal,
            "label": f"{series_name} #{row.get('number', number)} — {title}",
            "era": era,
            "eraSub": era_sub,
            "italianCode": row.get("italianCode", ""),
            "italianLabel": row.get("italianLabel", ""),
            "sort": (*legacy.original_date_key(row.get("date", ""), 0, row.get("number", "")), ordinal, row_index),
        })
    mapped = [chapter for chapter in chapters if chapter["italianCode"]]
    gaps = [chapter for chapter in chapters if not chapter["italianCode"]]
    log(f"Iron Man classico: {len(chapters)} storie in {CLASSIC_END} numeri USA; {len(mapped)} mappate, {len(gaps)} senza edizione italiana")
    return chapters, {
        "series": series_name,
        "stories": len(chapters),
        "issues": CLASSIC_END,
        "mappedStories": len(mapped),
        "unmappedStories": len(gaps),
    }


def load_albums(codes: set[str], workers: int) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    result: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    if not codes:
        return result, errors
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(five.load_italian_album, code): code for code in sorted(codes)}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                result[code] = future.result()
            except Exception as error:
                errors[code] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Pubblicazioni italiane lette: {index}/{len(futures)}")
    return result, errors


def prepare_physical(chapters: list[dict[str, Any]], workers: int) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, str]]:
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    codes = {chapter["italianCode"] for chapter in chapters if chapter.get("italianCode")}
    metadata, errors = load_albums(codes, workers)

    for code in codes:
        if code not in metadata and code in existing_by_album:
            metadata[code] = deepcopy(existing_by_album[code])
            metadata[code]["albumCode"] = code
            metadata[code].setdefault("contents", deepcopy(existing_by_album[code].get("contents", [])))

    missing = sorted(codes - set(metadata))
    if missing:
        details = "; ".join(f"{code}: {errors.get(code, 'non risolto')}" for code in missing)
        raise RuntimeError("Metadati italiani mancanti: " + details)

    contents_by_album: dict[str, list[dict[str, Any]]] = {
        code: deepcopy(metadata[code].get("contents", [])) for code in codes
    }

    for chapter in chapters:
        code = chapter.get("italianCode", "")
        if not code:
            continue
        raw = {
            "id": chapter["usaCode"],
            "seriesId": CLASSIC_SERIES,
            "series": chapter["sourceName"],
            "number": chapter["usaNumber"],
            "title": f"{chapter['sourceName']} #{chapter['usaNumber']}",
            "url": f"https://www.comicsbox.it/albo/{chapter['usaCode']}",
        }
        contents_by_album[code] = five.merge_contents(contents_by_album.get(code, []), [raw])
        metadata[code]["contents"] = contents_by_album[code]
        metadata[code]["contentsStatus"] = "complete"

    physical = legacy.assign_physical_ids(metadata, existing_by_album, existing_id_to_album)
    for code, issue in physical.items():
        issue["contents"] = contents_by_album.get(code, [])
        issue["contentsStatus"] = "complete"
    return physical, contents_by_album, errors


def build_classic(
    chapters: list[dict[str, Any]],
    physical_by_album: dict[str, dict[str, Any]],
    contents_by_album: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, dict[str, Any]] = {}
    mappings: list[dict[str, Any]] = []

    for chapter in chapters:
        album_code = chapter.get("italianCode", "")
        physical = physical_by_album.get(album_code)
        mapping = {
            "sourceCode": chapter["sourceCode"],
            "usaCode": chapter["usaCode"],
            "usaNumber": chapter["usaNumber"],
            "usaTitle": chapter["usaTitle"],
            "usa": chapter["label"],
            "usaDate": chapter["usaDate"],
            "storyOrdinal": chapter["storyOrdinal"],
            "italianAlbum": album_code or None,
            "italianLabel": chapter.get("italianLabel") or None,
            "physicalId": physical.get("id") if physical else None,
        }
        mappings.append(mapping)
        if not physical:
            continue

        issue_id = physical["id"]
        group = groups.setdefault(issue_id, {
            "physical": physical,
            "albumCode": album_code,
            "sort": chapter["sort"],
            "labels": [],
            "eras": [],
            "eraSubs": [],
            "sourceIds": [],
            "storyRows": [],
        })
        group["sort"] = min(group["sort"], chapter["sort"])
        if chapter["label"] not in group["labels"]:
            group["labels"].append(chapter["label"])
        if chapter["era"] not in group["eras"]:
            group["eras"].append(chapter["era"])
        if chapter["eraSub"] not in group["eraSubs"]:
            group["eraSubs"].append(chapter["eraSub"])
        if chapter["usaCode"] not in group["sourceIds"]:
            group["sourceIds"].append(chapter["usaCode"])
        group["storyRows"].append({
            "sourceIssueId": chapter["usaCode"],
            "storyOrdinal": chapter["storyOrdinal"],
            "sourceTitle": chapter["usaTitle"],
        })

    issues: list[dict[str, Any]] = []
    for position, group in enumerate(sorted(groups.values(), key=lambda item: item["sort"]), 1):
        physical = deepcopy(group["physical"])
        album_code = group["albumCode"]
        contents = deepcopy(contents_by_album.get(album_code, []))
        selected = list(group["sourceIds"])
        issue = {
            "id": physical["id"],
            "seq": position,
            "n": int(physical.get("n") or 0),
            "name": physical.get("name") or physical["id"],
            "title": five.concise(group["labels"], 2),
            "date": physical.get("date") or "Data italiana non disponibile",
            "seriesId": physical.get("seriesId") or physical["id"].split(":", 1)[0],
            "series": physical.get("series") or "Marvel",
            "publisher": physical.get("publisher") or "Editore italiano non indicato",
            "cover": physical.get("cover"),
            "url": physical.get("url"),
            "required": True,
            "skip": False,
            "future": bool(physical.get("future", False)),
            "coverSource": physical.get("coverSource", "ComicsBox"),
            "era": group["eras"][0],
            "eraSub": " · ".join(group["eraSubs"][:2]),
            "instruction": "Leggi in questo albo: " + five.concise(group["labels"], 3),
            "usaChapters": group["labels"],
            "sourceSeries": [CLASSIC_SERIES],
            "storyRows": group["storyRows"],
            "contents": contents,
            "contentsStatus": "complete",
            "readingStep": {
                "pathId": PATH_ID,
                "position": position,
                "contentIds": selected,
                "scope": "selected-usa-issues-pending-story-refinement",
            },
        }
        if physical.get("displayNumber"):
            issue["displayNumber"] = physical["displayNumber"]
        if physical.get("dateQuality"):
            issue["dateQuality"] = physical["dateQuality"]
        issues.append(issue)
    return issues, mappings


def choose_tail_contents(contents: list[dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    markers = (
        "iron man", "invincible iron man", "superior iron man", "tony stark",
        "infamous iron man", "international iron man",
    )
    for content in contents:
        text = " ".join(str(content.get(key, "")) for key in ("series", "seriesId", "title")).casefold()
        if any(marker in text for marker in markers):
            cid = content.get("id")
            if cid:
                selected.append(cid)
    return list(dict.fromkeys(selected))


def enrich_tail(existing: dict[str, Any], start_position: int, workers: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor = next((index for index, issue in enumerate(existing.get("issues", [])) if issue.get("id") == TAIL_ANCHOR), None)
    if anchor is None:
        raise RuntimeError(f"Anchor moderno {TAIL_ANCHOR} non trovato")
    tail = deepcopy(existing["issues"][anchor:])
    codes = {legacy.album_code(issue.get("url")) for issue in tail}
    codes.discard("")
    metadata, errors = load_albums(codes, workers)
    fallback: list[str] = []
    position = start_position
    for issue in tail:
        code = legacy.album_code(issue.get("url"))
        album = metadata.get(code)
        if album and album.get("contents"):
            contents = deepcopy(album["contents"])
            selected = choose_tail_contents(contents)
            if not selected:
                selected = [content["id"] for content in contents if content.get("id")]
                fallback.append(issue.get("id", code))
            issue["contents"] = contents
            issue["contentsStatus"] = "complete"
            issue["readingStep"] = {
                "pathId": PATH_ID,
                "position": position,
                "contentIds": selected,
                "scope": "selected-contents",
            }
        else:
            step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
            step["pathId"] = PATH_ID
            step["position"] = position
            issue["readingStep"] = step
        issue["seq"] = position
        position += 1
    return tail, {
        "issues": len(tail),
        "albumFetchErrors": errors,
        "fallbackWholeAlbumSelection": fallback,
    }


def series_index(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for issue in issues:
        sid = issue.get("seriesId") or issue.get("id", "").split(":", 1)[0]
        row = result.setdefault(sid, {
            "id": sid,
            "name": issue.get("series") or sid,
            "publisher": issue.get("publisher") or "Editore italiano non indicato",
            "range": "pubblicazioni italiane censite",
        })
        if sid == "ID1":
            row["years"] = "Editoriale Corno"
    return list(result.values())


def update_manifest(character: dict[str, Any]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    item = next((row for row in manifest.get("characters", []) if row.get("id") == PATH_ID), None)
    if not item:
        raise RuntimeError("ironman assente dal manifest")
    for key in ("start", "end", "totalRequired"):
        item[key] = character[key]
    item["pathRole"] = "main"
    item["mainPath"] = True
    item["auditStatus"] = "audited"
    item["auditKind"] = "path/character"
    item["auditDate"] = AUDIT_DATE
    manifest["version"] = max(int(manifest.get("version", 1)), 37)
    write_json(path, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "20")))
    args = parser.parse_args()
    workers = max(1, args.workers)

    existing = legacy.unpack_character(PATH_ID, "data/characters/ironman.json")
    chapters, source_summary = story_chapters()
    physical, contents_by_album, album_errors = prepare_physical(chapters, workers)
    classic_issues, mappings = build_classic(chapters, physical, contents_by_album)
    tail, tail_audit = enrich_tail(existing, len(classic_issues) + 1, workers)

    issues = classic_issues + tail
    for position, issue in enumerate(issues, 1):
        issue["seq"] = position
        if isinstance(issue.get("readingStep"), dict):
            issue["readingStep"]["position"] = position

    required = sum(1 for issue in issues if issue.get("required") is not False and not issue.get("future"))
    gaps = [mapping for mapping in mappings if not mapping.get("physicalId")]
    gap_issue_numbers = sorted({int(mapping["usaNumber"]) for mapping in gaps})
    first = issues[0]
    last = issues[-1]

    character = {
        "id": PATH_ID,
        "name": "Iron Man",
        "subtitle": "Tony Stark",
        "accent": "#ffb000",
        "start": f"{first['name']} — {first['date']}",
        "end": f"{last['name']} — {last['date']}",
        "description": (
            "Percorso di Tony Stark ricostruito da Iron Man (1968) #1 con il modello "
            "albo fisico italiano → storie USA → readingStep. Le lacune editoriali italiane "
            "restano dichiarate nell'audit; le ristampe vengono trattate come edizioni alternative "
            "solo per le storie che contengono realmente."
        ),
        "timelineMode": True,
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
        "pathRole": "main",
        "mainPath": True,
        "readingOrderSource": "ComicsBox Iron Man vol.1 → prime pubblicazioni italiane; audit MarvelTracker 2026-08-16",
        "coverage": {
            "classicUsIssues": CLASSIC_END,
            "classicStoryRows": len(chapters),
            "classicMappedStories": len(chapters) - len(gaps),
            "missingItalianStories": len(gaps),
            "classicPhysicalItalianIssues": len(classic_issues),
            "physicalItalianIssues": len(issues),
        },
        "series": series_index(issues),
        "archives": existing.get("archives", []),
        "relatedPaths": existing.get("relatedPaths", ["avengers", "war-machine"]),
        "totalRequired": required,
        "availableTotal": required,
        "issues": issues,
    }
    write_json(DATA / "characters" / "ironman.json", character)
    update_manifest(character)

    audit = {
        "version": 1,
        "status": "audited",
        "auditKind": "path/character",
        "auditDate": AUDIT_DATE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "editorialModel": character["editorialModel"],
        "scope": "Tony Stark main path from Iron Man (1968) #1 through the existing modern Italian route; Tales of Suspense remains pre-series context.",
        "classic": {
            **source_summary,
            "physicalItalianIssues": len(classic_issues),
            "gapIssueNumbers": gap_issue_numbers,
        },
        "guardrails": {
            "start": "Mandatory route begins with Iron Man (1968) #1. Tales of Suspense #39 and Iron Man & Sub-Mariner #1 are pre-series context, not mandatory step 1.",
            "firstPublication": "Primary physical steps use ComicsBox first official Italian publication; later collections are alternatives.",
            "storyLevel": "Same-USA-issue backups are audited independently. A later reprint may cover only part of a physical reading step.",
            "join": "Classic audit stops at Iron Man vol.1 #306; the preserved Marvel Italia tail begins with Iron Man vol.1 #307 in Iron Man e i Vendicatori #1.",
        },
        "tail": tail_audit,
        "albumFetchWarnings": album_errors,
        "mappings": mappings,
    }
    write_json(AUDIT_PATH, audit, pretty=True)
    log(f"Iron Man: {len(classic_issues)} tappe classiche + {len(tail)} moderne = {len(issues)}; {len(gaps)} storie senza edizione italiana")


if __name__ == "__main__":
    main()
