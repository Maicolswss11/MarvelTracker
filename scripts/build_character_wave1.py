#!/usr/bin/env python3
"""Build the first missing-character wave with protagonist-scoped shared-history reuse.

Wave: Black Cat, Quicksilver, Falcon, Winter Soldier, War Machine, Hercules,
Spider-Woman and Sentry.

The builder keeps the editorial invariant introduced by the five-character
expansion:

    physical Italian issue -> USA contents -> path reading step

Dedicated/co-billed series are read from ComicsBox series indexes.  Shared
history is reused from existing MarvelTracker paths only when ComicsBox credits
the target character among the *protagonisti* of the USA story.  Mere
``apparizioni`` are deliberately not imported.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import unicodedata
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
CONFIG_PATH = DATA / "character-wave1-sources.json"
AUDIT_PATH = DATA / "character-wave1-audit.json"
MANIFEST_VERSION = 25

MONTHS = {
    "jan": 1, "january": 1, "gen": 1, "gennaio": 1,
    "feb": 2, "february": 2, "febbraio": 2,
    "mar": 3, "march": 3, "marzo": 3,
    "apr": 4, "april": 4, "aprile": 4,
    "may": 5, "maggio": 5,
    "jun": 6, "june": 6, "giu": 6, "giugno": 6,
    "jul": 7, "july": 7, "lug": 7, "luglio": 7,
    "aug": 8, "august": 8, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "set": 9, "settembre": 9,
    "oct": 10, "october": 10, "ott": 10, "ottobre": 10,
    "nov": 11, "november": 11, "novembre": 11,
    "dec": 12, "december": 12, "dic": 12, "dicembre": 12,
}

SOURCE_MARKERS = {
    "black-cat": ["black cat", "felicia hardy", "iron cat", "mary jane & black cat", "spider-man/black cat", "spider-man presents: black cat"],
    "quicksilver": ["quicksilver", "son of m", "quick and the dead", "scarlet witch & quicksilver", "scarlet witch and quicksilver"],
    "falcon": ["falcon", "sam wilson", "all-new captain america", "symbol of truth"],
    "winter-soldier": ["winter soldier", "bucky barnes", "tales of suspense"],
    "war-machine": ["war machine", "iron man 2.0", "iron patriot"],
    "hercules": ["hercules", "incredible hercules", "herc"],
    "spider-woman": ["spider-woman", "spider woman"],
    "sentry": ["sentry"],
}

SVG_MARKS = {
    "black-cat": '<path d="M31 54 45 25l19 18 19-18 14 29-9 45-24 14-24-14Z"/><path d="M43 61h14v8H43Zm28 0h14v8H71ZM48 88c10 7 22 7 32 0" fill="none" stroke="currentColor" stroke-width="6"/>',
    "quicksilver": '<path d="M28 69 62 21 52 55h23L48 108l10-31H28Z"/>',
    "falcon": '<path d="M18 69c19-25 32-32 46-18 14-14 27-7 46 18-16-7-26-5-34 5-7 8-9 21-12 34-3-13-5-26-12-34-8-10-18-12-34-5Z"/>',
    "winter-soldier": '<path d="M39 24h36l16 18-8 68H45l-8-68Z"/><path d="M45 55h38M48 72h32" fill="none" stroke="#0b0f17" stroke-width="7"/><path d="m64 31 5 11 12 2-9 8 2 12-10-6-10 6 2-12-9-8 12-2Z" fill="#0b0f17"/>',
    "war-machine": '<path d="M42 25h44l14 24-10 57-26 12-26-12-10-57Z"/><path d="M48 54h32v20H48Z" fill="#0b0f17"/><path d="M52 86h24" fill="none" stroke="#0b0f17" stroke-width="7"/>',
    "hercules": '<path d="M27 92 45 28h38l18 64-19 22H46Z"/><path d="M45 54h38M41 76h46" fill="none" stroke="#0b0f17" stroke-width="7"/>',
    "spider-woman": '<path d="M64 22c18 0 32 15 32 34 0 24-15 48-32 61-17-13-32-37-32-61 0-19 14-34 32-34Z"/><path d="M37 55h54M42 77h44M64 30v77" fill="none" stroke="#0b0f17" stroke-width="6"/>',
    "sentry": '<path d="m64 18 12 29 31 2-24 20 8 30-27-16-27 16 8-30-24-20 31-2Z"/><circle cx="64" cy="65" r="15" fill="#0b0f17"/>',
}


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = html.unescape(value).casefold().replace("–", "-").replace("’", "'")
    return " ".join(value.split())


def visible_text(source: str) -> str:
    source = re.sub(r"<script\b.*?</script>", " ", source, flags=re.I | re.S)
    source = re.sub(r"<style\b.*?</style>", " ", source, flags=re.I | re.S)
    source = re.sub(r"<[^>]+>", " ", source)
    return " ".join(html.unescape(source).split())


def credited_as_protagonist(source: str, aliases: list[str]) -> bool:
    text = norm(visible_text(source))
    marker = text.find("protagonisti:")
    if marker < 0:
        return False
    end_candidates = [
        pos for needle in (" apparizioni:", " pubblicazione italiana:", " ristampa in originale:", " database italiano")
        if (pos := text.find(needle, marker + 1)) >= 0
    ]
    end = min(end_candidates) if end_candidates else min(len(text), marker + 1400)
    segment = text[marker:end]
    return any(norm(alias) in segment for alias in aliases)


def source_date(source: str, fallback: str = "") -> tuple[str, tuple[int, int]]:
    text = norm(visible_text(source)[:8000])
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else 9999
    month = 6
    if year_match:
        prefix = text[max(0, year_match.start() - 35):year_match.start()]
        for token, number in MONTHS.items():
            if re.search(rf"\b{re.escape(token)}\b", prefix):
                month = number
                break
    label = fallback or (f"{year:04d}-{month:02d}" if year < 9999 else "")
    return label, (year, month)


def source_valid_for_path(path_id: str, series_name: str) -> bool:
    text = norm(series_name)
    return any(norm(marker) in text for marker in SOURCE_MARKERS[path_id])


def load_config_sources(config: dict[str, Any], workers: int) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, list[str]]]:
    codes = sorted({code for path in config["paths"] for code in path.get("sources", [])})
    loaded: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    rejected: dict[str, list[str]] = defaultdict(list)
    log(f"Serie dedicate candidate: {len(codes)}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(legacy.load_foreign_series, code): code for code in codes}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                loaded[code] = future.result()
            except Exception as error:
                errors[code] = str(error)
            if index % 10 == 0 or index == len(futures):
                log(f"Serie dedicate verificate: {index}/{len(futures)}")
    for path in config["paths"]:
        for code in path.get("sources", []):
            item = loaded.get(code)
            reported_name = item.get("name", code) if item else code
            if item and reported_name != code and not source_valid_for_path(path["id"], reported_name):
                rejected[path["id"]].append(f"{code}: {reported_name}")
    return loaded, errors, rejected


def era_for_date(date: str) -> str:
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date or "")
    if not year_match:
        return "Storie dedicate"
    year = int(year_match.group())
    if year < 1980:
        return "Origini e anni classici"
    if year < 2000:
        return "Anni Ottanta e Novanta"
    if year < 2013:
        return "Era moderna"
    if year < 2020:
        return "Marvel NOW! e Legacy"
    return "Era contemporanea"


def dedicated_chapters(path: dict[str, Any], loaded: dict[str, dict[str, Any]], rejected: dict[str, list[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chapters: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    rejected_codes = {entry.split(":", 1)[0] for entry in rejected.get(path["id"], [])}
    for source_index, code in enumerate(path.get("sources", [])):
        series = loaded.get(code)
        if not series or code in rejected_codes:
            continue
        rows = series.get("rows", [])
        for row in rows:
            label = f"{series['name']} #{row['number']}"
            if row.get("title") and row["title"] != row["number"]:
                label += f" — {row['title']}"
            chapters.append({
                "kind": "chapter",
                "sourceCode": code,
                "sourceName": series["name"],
                "usaCode": row["code"],
                "usaNumber": row["number"],
                "usaTitle": row.get("title", ""),
                "usaDate": row.get("date", ""),
                "authors": row.get("authors", ""),
                "label": label,
                "era": era_for_date(row.get("date", "")),
                "italianCode": row.get("italianCode", ""),
                "italianLabel": row.get("italianLabel", ""),
                "sort": legacy.original_date_key(row.get("date", ""), source_index, row["number"]),
                "origin": "dedicated-series",
            })
        summaries.append({
            "code": code,
            "name": series["name"],
            "chapters": len(rows),
            "mapped": sum(bool(row.get("italianCode")) for row in rows),
            "unmapped": sum(not bool(row.get("italianCode")) for row in rows),
        })
    return chapters, summaries


def manifest_meta(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in manifest.get("characters", [])}


def load_reuse_issues(config: dict[str, Any], manifest: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    meta = manifest_meta(manifest)
    per_base: dict[str, list[dict[str, Any]]] = {}
    issue_by_album: dict[str, dict[str, Any]] = {}
    base_ids = sorted({base for path in config["paths"] for base in path.get("reusePaths", [])})
    for base_id in base_ids:
        base_meta = meta.get(base_id)
        if not base_meta:
            log(f"WARN percorso base assente: {base_id}")
            continue
        payload = legacy.unpack_character(base_id, base_meta["data"])
        rows = payload.get("issues", [])
        per_base[base_id] = rows
        for issue in rows:
            code = legacy.album_code(issue.get("url"))
            if code:
                issue_by_album.setdefault(code, issue)
        log(f"Base {base_id}: {len(rows)} albi")
    return per_base, issue_by_album


def enrich_reuse_contents(per_base: dict[str, list[dict[str, Any]]], workers: int) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, str]]:
    contents_by_album: dict[str, list[dict[str, Any]]] = {}
    metadata_by_album: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    need_fetch: set[str] = set()
    for issues in per_base.values():
        for issue in issues:
            code = legacy.album_code(issue.get("url"))
            if not code:
                continue
            existing = issue.get("contents") if isinstance(issue.get("contents"), list) else []
            if existing:
                contents_by_album[code] = deepcopy(existing)
            else:
                need_fetch.add(code)
    log(f"Albi condivisi senza mappa contenuti: {len(need_fetch)}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(five.load_italian_album, code): code for code in sorted(need_fetch)}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                metadata = future.result()
                metadata_by_album[code] = metadata
                contents_by_album[code] = metadata.get("contents", [])
            except Exception as error:
                errors[code] = str(error)
            if index % 75 == 0 or index == len(futures):
                log(f"Contenuti albi condivisi: {index}/{len(futures)}")
    return contents_by_album, metadata_by_album, errors


def scan_content_roles(contents_by_album: dict[str, list[dict[str, Any]]], config: dict[str, Any], workers: int) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    aliases_by_path = {path["id"]: path["aliases"] for path in config["paths"]}
    codes = sorted({content.get("id", "") for values in contents_by_album.values() for content in values if content.get("id")})
    result: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    log(f"Storie USA condivise da classificare: {len(codes)}")

    def inspect(code: str) -> tuple[str, dict[str, Any]]:
        source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{code}")
        date_label, date_key = source_date(source)
        protagonists = [path_id for path_id, aliases in aliases_by_path.items() if credited_as_protagonist(source, aliases)]
        return code, {"protagonistPaths": protagonists, "date": date_label, "dateKey": list(date_key)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(inspect, code): code for code in codes}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                key, info = future.result()
                result[key] = info
            except Exception as error:
                errors[code] = str(error)
            if index % 100 == 0 or index == len(futures):
                log(f"Storie USA classificate: {index}/{len(futures)}")
    return result, errors


def shared_chapters(path: dict[str, Any], per_base: dict[str, list[dict[str, Any]]], contents_by_album: dict[str, list[dict[str, Any]]], role_map: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    chapters: list[dict[str, Any]] = []
    scanned = 0
    included = 0
    no_contents = 0
    seen: set[str] = set()
    for reuse_index, base_id in enumerate(path.get("reusePaths", [])):
        for issue in per_base.get(base_id, []):
            album = legacy.album_code(issue.get("url"))
            if not album:
                continue
            contents = contents_by_album.get(album, [])
            if not contents:
                no_contents += 1
                continue
            for content in contents:
                code = content.get("id", "")
                if not code or code in seen:
                    continue
                scanned += 1
                info = role_map.get(code, {})
                if path["id"] not in info.get("protagonistPaths", []):
                    continue
                seen.add(code)
                included += 1
                year, month = (info.get("dateKey") or [9999, 6])[:2]
                number = str(content.get("number", ""))
                number_token = legacy.numeric_token(number) or 0
                label = content.get("title") or f"{content.get('series', base_id)} #{number}".strip()
                chapters.append({
                    "kind": "chapter",
                    "sourceCode": f"reuse:{base_id}",
                    "sourceName": content.get("series") or base_id,
                    "usaCode": code,
                    "usaNumber": number,
                    "usaTitle": content.get("title", ""),
                    "usaDate": info.get("date", ""),
                    "authors": "",
                    "label": label,
                    "era": era_for_date(info.get("date", "")),
                    "italianCode": album,
                    "italianLabel": issue.get("name", ""),
                    "sort": (int(year), int(month), 500 + reuse_index, number_token, code),
                    "origin": f"shared-protagonist:{base_id}",
                })
    return chapters, {"scannedContents": scanned, "includedProtagonistContents": included, "issuesWithoutContents": no_contents}


def dedupe_chapters(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(chapters, key=lambda item: (item["sort"], item.get("origin", "")))
    by_usa: dict[str, dict[str, Any]] = {}
    for chapter in ordered:
        code = chapter["usaCode"]
        current = by_usa.get(code)
        if current is None:
            by_usa[code] = chapter
            continue
        if current.get("origin", "").startswith("shared-") and chapter.get("origin") == "dedicated-series":
            by_usa[code] = chapter
    return sorted(by_usa.values(), key=lambda item: item["sort"])


def prepare_physical_maps(
    chapters_by_path: dict[str, list[dict[str, Any]]],
    reuse_metadata: dict[str, dict[str, Any]],
    reuse_contents: dict[str, list[dict[str, Any]]],
    workers: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, str], dict[str, str]]:
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    codes = {chapter.get("italianCode", "") for chapters in chapters_by_path.values() for chapter in chapters}
    codes.discard("")
    metadata: dict[str, dict[str, Any]] = {code: deepcopy(value) for code, value in reuse_metadata.items() if code in codes}
    contents_by_album: dict[str, list[dict[str, Any]]] = {code: deepcopy(values) for code, values in reuse_contents.items() if code in codes}
    errors: dict[str, str] = {}
    need_fetch = sorted(code for code in codes if code not in metadata and code not in existing_by_album)
    log(f"Nuovi albi italiani da risolvere: {len(need_fetch)}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(five.load_italian_album, code): code for code in need_fetch}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                item = future.result()
                metadata[code] = item
                contents_by_album[code] = item.get("contents", [])
            except Exception as error:
                errors[code] = str(error)
            if index % 50 == 0 or index == len(futures):
                log(f"Nuovi albi italiani risolti: {index}/{len(futures)}")
    for code in codes:
        if code in metadata:
            continue
        if code in existing_by_album:
            metadata[code] = deepcopy(existing_by_album[code])
            metadata[code]["albumCode"] = code
            if not contents_by_album.get(code) and isinstance(existing_by_album[code].get("contents"), list):
                contents_by_album[code] = deepcopy(existing_by_album[code]["contents"])
    known: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chapters in chapters_by_path.values():
        for chapter in chapters:
            code = chapter.get("italianCode", "")
            if code:
                known[code] = five.merge_contents(known[code], [five.chapter_content(chapter)])
    for code in codes:
        contents_by_album[code] = five.merge_contents(contents_by_album.get(code, []), known.get(code, []))
    physical = legacy.assign_physical_ids(metadata, existing_by_album, existing_id_to_album)
    statuses = {code: ("complete" if reuse_contents.get(code) or metadata.get(code, {}).get("contents") else "path-scoped") for code in codes}
    for code, issue in physical.items():
        issue["contents"] = contents_by_album.get(code, [])
        issue["contentsStatus"] = statuses.get(code, "path-scoped")
    return physical, contents_by_album, statuses, errors


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {spec["id"] for spec in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "spiderman": ["black-cat", "spider-woman"],
        "avengers": ["quicksilver", "falcon", "winter-soldier", "war-machine", "hercules", "spider-woman", "sentry"],
        "xmen": ["quicksilver"],
        "scarletwitch": ["quicksilver"],
        "cap": ["falcon", "winter-soldier"],
        "blackwidow": ["winter-soldier"],
        "ironman": ["war-machine"],
        "thor": ["hercules"],
        "hulk": ["hercules", "sentry"],
        "doctor-doom": ["black-cat"],
    }
    for item in items:
        for related in reciprocal.get(item["id"], []):
            item.setdefault("relatedPaths", [])
            if related not in item["relatedPaths"]:
                item["relatedPaths"].append(related)
    for spec in config["paths"]:
        character = characters[spec["id"]]
        meta = {
            "id": spec["id"], "name": spec["name"], "subtitle": spec["subtitle"],
            "type": spec["type"], "pathRole": "main", "mainPath": True,
            "primaryHub": spec["primaryHub"], "hubs": spec["hubs"], "accent": spec["accent"],
            "logo": f"assets/heroes/{spec['id']}.svg", "data": f"data/characters/{spec['id']}.json",
            "start": character["start"], "end": character["end"], "totalRequired": character["totalRequired"],
            "relatedPaths": spec.get("relatedPaths", []),
        }
        anchor = spec.get("insertAfter")
        index = next((i + 1 for i, item in enumerate(items) if item["id"] == anchor), len(items))
        items.insert(index, meta)
    manifest["version"] = MANIFEST_VERSION
    manifest["characters"] = items
    write_json(path, manifest)


def update_hubs(config: dict[str, Any]) -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    for hub in payload.get("hubs", []):
        groups = hub.setdefault("groups", [])
        if hub["id"] == "avengers":
            members = next((group for group in groups if group["id"] == "members"), None)
            if members is None:
                members = {"id": "members", "label": "Membri e percorsi collegati", "paths": []}
                groups.append(members)
            for path_id in ["quicksilver", "falcon", "winter-soldier", "war-machine", "hercules", "spider-woman", "sentry"]:
                if path_id not in members["paths"]:
                    members["paths"].append(path_id)
        elif hub["id"] == "spider":
            allies = next((group for group in groups if group["id"] == "allies"), None)
            if allies is None:
                allies = {"id": "allies", "label": "Alleati e Spider-family", "paths": []}
                groups.append(allies)
            for path_id in ["black-cat", "spider-woman"]:
                if path_id not in allies["paths"]:
                    allies["paths"].append(path_id)
        elif hub["id"] == "xmen":
            crossroads = next((group for group in groups if group["id"] == "crossroads"), None)
            if crossroads is None:
                crossroads = {"id": "crossroads", "label": "Mutanti tra più mondi", "paths": []}
                groups.append(crossroads)
            if "quicksilver" not in crossroads["paths"]:
                crossroads["paths"].append("quicksilver")
    write_json(path, payload)


def write_logos(config: dict[str, Any]) -> None:
    target = ROOT / "assets" / "heroes"
    target.mkdir(parents=True, exist_ok=True)
    for spec in config["paths"]:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" '
            f'style="color:{spec["accent"]}"><circle cx="64" cy="64" r="58" fill="#0b0f17" '
            'stroke="currentColor" stroke-width="5"/><g fill="currentColor" stroke-linecap="round" '
            f'stroke-linejoin="round">{SVG_MARKS[spec["id"]]}</g></svg>'
        )
        (target / f"{spec['id']}.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "12")))
    args = parser.parse_args()
    workers = max(1, args.workers)
    config = read_json(CONFIG_PATH)
    manifest_before = read_json(DATA / "characters.json")
    catalog_before = read_json(DATA / "catalog.json")

    loaded, source_errors, rejected_sources = load_config_sources(config, workers)
    per_base, _ = load_reuse_issues(config, manifest_before)
    reuse_contents, reuse_metadata, reuse_album_errors = enrich_reuse_contents(per_base, workers)
    role_map, role_errors = scan_content_roles(reuse_contents, config, workers)

    chapters_by_path: dict[str, list[dict[str, Any]]] = {}
    audits: list[dict[str, Any]] = []
    for spec in config["paths"]:
        dedicated, source_summary = dedicated_chapters(spec, loaded, rejected_sources)
        shared, shared_stats = shared_chapters(spec, per_base, reuse_contents, role_map)
        chapters = dedupe_chapters(dedicated + shared)
        chapters_by_path[spec["id"]] = chapters
        audits.append({
            "id": spec["id"], "name": spec["name"],
            "dedicatedChapters": len(dedicated), "sharedProtagonistChapters": len(shared),
            "deduplicatedChapters": len(chapters), "sourceSeries": source_summary,
            "sharedScan": shared_stats, "rejectedSources": rejected_sources.get(spec["id"], []),
        })
        log(f"{spec['name']}: {len(dedicated)} dedicati + {len(shared)} condivisi = {len(chapters)} capitoli")

    physical, contents_by_album, content_status, album_errors = prepare_physical_maps(
        chapters_by_path, reuse_metadata, reuse_contents, workers
    )

    characters: dict[str, dict[str, Any]] = {}
    audit_by_id = {row["id"]: row for row in audits}
    for spec in config["paths"]:
        character, path_audit = five.build_character(
            spec, chapters_by_path[spec["id"]], physical, contents_by_album, content_status
        )
        character["readingOrderSource"] = "ComicsBox serie dedicate + riuso protagonista-only dai percorsi MarvelTracker esistenti"
        character["sharedHistoryPolicy"] = "protagonists-only; simple appearances excluded"
        characters[spec["id"]] = character
        audit_by_id[spec["id"]].update({
            "mappedChapters": path_audit["mappedChapters"],
            "missingItalianPublications": path_audit["missingItalianPublications"],
            "physicalItalianIssues": path_audit["physicalItalianIssues"],
            "mappings": path_audit["mappings"],
        })
        write_json(DATA / "characters" / f"{spec['id']}.json", character)
        log(f"  -> {character['name']}: {len(character['issues'])} albi fisici, {path_audit['missingItalianPublications']} lacune")

    five.add_shared_labels(characters, manifest_before, catalog_before)
    for path_id, character in characters.items():
        write_json(DATA / "characters" / f"{path_id}.json", character)

    update_manifest(config, characters)
    update_hubs(config)
    write_logos(config)

    existing_by_album, _ = legacy.existing_physical_map()
    all_albums = {legacy.album_code(issue.get("url")) for character in characters.values() for issue in character["issues"]}
    all_albums.discard("")
    audit_payload = {
        "version": 1,
        "manifestVersion": MANIFEST_VERSION,
        "editorialModel": config["editorialModel"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": config["source"],
        "rules": config["rules"],
        "summary": {
            "paths": len(config["paths"]),
            "candidateDedicatedSeries": len({code for spec in config["paths"] for code in spec.get("sources", [])}),
            "validDedicatedSeries": len(loaded),
            "sourceErrors": len(source_errors),
            "rejectedWrongSeries": sum(len(values) for values in rejected_sources.values()),
            "sharedUsStoriesScanned": len(role_map),
            "sharedUsStoryErrors": len(role_errors),
            "uniqueItalianAlbums": len(all_albums),
            "reusedExistingAlbums": len(all_albums & set(existing_by_album)),
            "newItalianAlbums": len(all_albums - set(existing_by_album)),
        },
        "sourceErrors": source_errors,
        "rejectedSources": rejected_sources,
        "reuseAlbumErrors": reuse_album_errors,
        "roleScanErrors": role_errors,
        "albumErrors": album_errors,
        "paths": audits,
    }
    write_json(AUDIT_PATH, audit_payload, pretty=True)
    log(f"Audit scritto: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
