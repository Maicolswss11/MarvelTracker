#!/usr/bin/env python3
"""Build the Hulk Corno, Daredevil, Wolverine, Venom and Doctor Doom paths.

This expansion introduces the first explicit three-level editorial mapping:

    physical Italian issue -> USA contents -> path reading step

The physical issue ID remains the global ownership key.  ``readingStep`` is
path-local and selects the stories that count when the same anthology is read
from a different character path.
"""

from __future__ import annotations

import argparse
import html
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

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "five-character-sources.json"
AUDIT_PATH = DATA / "five-character-audit.json"
MANIFEST_VERSION = 23


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


def attr_value(attributes: str, name: str) -> str:
    match = re.search(
        rf"\b{name}\s*=\s*(?:\"([^\"]*)\"|'([^']*)')",
        attributes,
        flags=re.I,
    )
    return html.unescape((match.group(1) or match.group(2)).strip()) if match else ""


def parse_album_contents(source: str) -> list[dict[str, Any]]:
    """Read only the original-album anchors introduced by ComicsBox's `da`."""

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r"<em[^>]*>\s*da\s*</em>\s*(?:<strong[^>]*>)?\s*<a\b([^>]*)>",
        flags=re.I,
    )
    for match in pattern.finditer(source):
        attributes = match.group(1)
        href = attr_value(attributes, "href")
        code = legacy.album_code(href)
        if not code or code in seen:
            continue
        seen.add(code)
        label = attr_value(attributes, "title") or code.replace("_", " ")
        label = " ".join(label.split())
        title_match = re.match(r"^(.*?)\s+#\s*(.+)$", label)
        series = title_match.group(1).strip() if title_match else code.rsplit("_", 1)[0]
        number = title_match.group(2).strip() if title_match else code.rsplit("_", 1)[-1].lstrip("0") or "0"
        results.append(
            {
                "id": code,
                "seriesId": code.rsplit("_", 1)[0],
                "series": series,
                "number": number,
                "title": label,
                "url": f"https://www.comicsbox.it/albo/{code}",
            }
        )
    return results


def load_italian_album(code: str) -> dict[str, Any]:
    metadata = legacy.load_italian_album(code)
    source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{code}")
    metadata["contents"] = parse_album_contents(source)
    metadata["contentsStatus"] = "complete" if metadata["contents"] else "unavailable"
    return metadata


def chapter_content(chapter: dict[str, Any]) -> dict[str, Any]:
    code = chapter["usaCode"]
    return {
        "id": code,
        "seriesId": chapter["sourceCode"],
        "series": chapter["sourceName"],
        "number": chapter["usaNumber"],
        "title": chapter["label"],
        "url": f"https://www.comicsbox.it/albo/{code}",
    }


def merge_contents(*collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    positions: dict[str, int] = {}
    for collection in collections:
        for content in collection or []:
            content_id = str(content.get("id") or "")
            if not content_id:
                continue
            if content_id not in positions:
                positions[content_id] = len(merged)
                merged.append(deepcopy(content))
                continue
            target = merged[positions[content_id]]
            for key, value in content.items():
                if target.get(key) in (None, "", []) and value not in (None, "", []):
                    target[key] = deepcopy(value)
    return merged


def concise(values: list[str], limit: int = 3) -> str:
    if len(values) <= limit:
        return "; ".join(values)
    return "; ".join(values[:limit]) + f"; + altri {len(values) - limit} capitoli"


def build_character(
    path: dict[str, Any],
    chapters: list[dict[str, Any]],
    physical_by_album: dict[str, dict[str, Any]],
    contents_by_album: dict[str, list[dict[str, Any]]],
    content_status_by_album: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    mappings: list[dict[str, Any]] = []

    for chapter in sorted(chapters, key=lambda item: item["sort"]):
        italian_code = chapter.get("italianCode", "")
        physical = physical_by_album.get(italian_code)
        mapping = {
            "kind": chapter["kind"],
            "sourceCode": chapter["sourceCode"],
            "usaCode": chapter["usaCode"],
            "usa": chapter["label"],
            "usaDate": chapter["usaDate"],
            "italianAlbum": italian_code or None,
            "physicalId": physical.get("id") if physical else None,
        }
        mappings.append(mapping)
        if not physical:
            continue

        issue_id = physical["id"]
        group = groups.setdefault(
            issue_id,
            {
                "physical": physical,
                "albumCode": italian_code,
                "sort": chapter["sort"],
                "labels": [],
                "eras": [],
                "sources": [],
                "contentIds": [],
                "hasReuse": False,
            },
        )
        if chapter["sort"] < group["sort"]:
            group["sort"] = chapter["sort"]
        for key, value in (("labels", chapter["label"]), ("eras", chapter["era"]), ("sources", chapter["sourceCode"])):
            if value not in group[key]:
                group[key].append(value)
        if chapter["kind"] == "chapter":
            if chapter["usaCode"] not in group["contentIds"]:
                group["contentIds"].append(chapter["usaCode"])
        else:
            group["hasReuse"] = True

    issues: list[dict[str, Any]] = []
    ordered = sorted(groups.values(), key=lambda item: item["sort"])
    for sequence, group in enumerate(ordered, 1):
        physical = group["physical"]
        album_code = group["albumCode"]
        contents = deepcopy(contents_by_album.get(album_code, []))
        available_ids = [content["id"] for content in contents]
        selected = [content_id for content_id in group["contentIds"] if content_id in available_ids]
        if group["hasReuse"]:
            selected.extend(content_id for content_id in available_ids if content_id not in selected)
        if not selected:
            selected = available_ids[:]

        issue = {
            "id": physical["id"],
            "seq": sequence,
            "n": int(physical.get("n") or 0),
            "name": physical.get("name") or physical["id"],
            "title": concise(group["labels"], 2),
            "date": physical.get("date") or "Data italiana non disponibile",
            "seriesId": physical.get("seriesId") or physical["id"].split(":", 1)[0],
            "series": physical.get("series") or "Marvel",
            "publisher": physical.get("publisher") or "Editore italiano non indicato",
            "cover": physical.get("cover"),
            "url": physical.get("url"),
            "future": bool(physical.get("future", False)),
            "required": True,
            "skip": False,
            "coverSource": physical.get("coverSource", "ComicsBox"),
            "era": group["eras"][0],
            "eraSub": " · ".join(group["eras"][:3]),
            "instruction": "Leggi in questo albo: " + concise(group["labels"]),
            "usaChapters": group["labels"],
            "sourceSeries": group["sources"],
            "contents": contents,
            "contentsStatus": content_status_by_album.get(album_code, "path-scoped"),
            "readingStep": {
                "pathId": path["id"],
                "position": sequence,
                "contentIds": selected,
                "scope": "selected-contents",
            },
        }
        if physical.get("displayNumber"):
            issue["displayNumber"] = physical["displayNumber"]
        if physical.get("dateQuality"):
            issue["dateQuality"] = physical["dateQuality"]
        issues.append(issue)

    if not issues:
        raise RuntimeError(f"{path['id']}: nessuna pubblicazione italiana risolta")

    mapped = sum(1 for mapping in mappings if mapping["physicalId"])
    missing = [mapping for mapping in mappings if not mapping["physicalId"]]
    available = sum(1 for issue in issues if not issue["future"])
    series_rows: dict[str, dict[str, Any]] = {}
    for issue in issues:
        series_rows.setdefault(
            issue["seriesId"],
            {
                "id": issue["seriesId"],
                "name": issue["series"],
                "publisher": issue["publisher"],
                "range": "prime pubblicazioni italiane censite",
            },
        )

    character: dict[str, Any] = {
        "id": path["id"],
        "name": path["name"],
        "subtitle": path["subtitle"],
        "accent": path["accent"],
        "start": f"{issues[0]['name']} — {issues[0]['date']}",
        "end": f"{issues[-1]['name']} — {issues[-1]['date']}",
        "description": (
            path["description"]
            + f" La matrice collega {mapped} di {len(mappings)} capitoli a {len(issues)} albi fisici italiani; "
            + f"{len(missing)} lacune restano dichiarate nell'audit."
        ),
        "timelineMode": True,
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
        "pathRole": path.get("pathRole", "main"),
        "mainPath": path.get("mainPath", True),
        "readingOrderSource": "ComicsBox USA → prima pubblicazione italiana; selezione curatoriale MarvelTracker",
        "coverage": {
            "originalChapters": len(mappings),
            "mappedChapters": mapped,
            "missingItalianPublications": len(missing),
            "physicalItalianIssues": len(issues),
            "completeContentAlbums": sum(issue["contentsStatus"] == "complete" for issue in issues),
        },
        "series": list(series_rows.values()),
        "archives": [],
        "relatedPaths": path.get("relatedPaths", []),
        "branches": path.get("branches", []),
        "totalRequired": available,
        "availableTotal": available,
        "issues": issues,
    }
    if path.get("canonicalCharacter"):
        character["canonicalCharacter"] = path["canonicalCharacter"]

    audit = {
        "id": path["id"],
        "name": path["name"],
        "originalChapters": len(mappings),
        "mappedChapters": mapped,
        "missingItalianPublications": len(missing),
        "physicalItalianIssues": len(issues),
        "completeContentAlbums": character["coverage"]["completeContentAlbums"],
        "mappings": mappings,
    }
    return character, audit


def add_shared_labels(
    characters: dict[str, dict[str, Any]],
    manifest_before: dict[str, Any],
    existing_catalog: dict[str, Any],
) -> None:
    names = {item["id"]: item["name"] for item in manifest_before["characters"]}
    names.update({path_id: character["name"] for path_id, character in characters.items()})
    paths_by_issue: dict[str, set[str]] = defaultdict(set)
    for row in existing_catalog.get("issues", []):
        paths_by_issue[row["id"]].update(row.get("paths", []))
    for path_id, character in characters.items():
        for issue in character["issues"]:
            paths_by_issue[issue["id"]].add(path_id)
    for path_id, character in characters.items():
        for issue in character["issues"]:
            others = sorted(paths_by_issue[issue["id"]] - {path_id})
            if others:
                issue["sharedWith"] = [names.get(other, other) for other in others]


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {item["id"] for item in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "hulk": ["hulk-classic-corno", "daredevil"],
        "spiderman": ["venom"],
        "xmen": ["wolverine-616"],
        "fantastic-four": ["doctor-doom"],
        "doctor-strange": ["doctor-doom"],
    }
    for item in items:
        for related_id in reciprocal.get(item["id"], []):
            item.setdefault("relatedPaths", [])
            if related_id not in item["relatedPaths"]:
                item["relatedPaths"].append(related_id)

    for spec in config["paths"]:
        character = characters[spec["id"]]
        meta: dict[str, Any] = {
            "id": spec["id"],
            "name": spec["name"],
            "subtitle": spec["subtitle"],
            "type": spec["type"],
            "pathRole": spec.get("pathRole", "main"),
            "mainPath": spec.get("mainPath", True),
            "primaryHub": spec["primaryHub"],
            "hubs": spec["hubs"],
            "accent": spec["accent"],
            "logo": f"assets/heroes/{spec['id']}.svg",
            "data": f"data/characters/{spec['id']}.json",
            "start": character["start"],
            "end": character["end"],
            "totalRequired": character["totalRequired"],
            "relatedPaths": spec.get("relatedPaths", []),
        }
        if spec.get("canonicalCharacter"):
            meta["canonicalCharacter"] = spec["canonicalCharacter"]
        anchor = spec.get("insertAfter")
        index = next((i + 1 for i, item in enumerate(items) if item["id"] == anchor), len(items))
        items.insert(index, meta)

    manifest["version"] = MANIFEST_VERSION
    manifest["characters"] = items
    write_json(path, manifest)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    for hub in payload.get("hubs", []):
        if hub["id"] == "avengers":
            hub["groups"] = [
                {"id": "core", "label": "Percorso principale", "paths": ["avengers"]},
                {"id": "foundations", "label": "Membri principali", "paths": ["ironman", "thor", "cap", "hulk"]},
                {"id": "history", "label": "Archivio storico", "paths": ["hulk-classic-corno"]},
                {"id": "members", "label": "Membri e percorsi collegati", "paths": ["antman", "wasp", "scarletwitch", "vision", "wonderman", "hawkeye", "blackwidow", "blackpanther", "captainmarvel", "shehulk"]},
            ]
        elif hub["id"] == "street":
            hub.pop("status", None)
            hub["groups"] = [{"id": "core", "label": "Hell's Kitchen", "paths": ["daredevil"]}]
            hub["featuredPath"] = "daredevil"
        elif hub["id"] == "xmen":
            hub["groups"] = [
                {"id": "core", "label": "Percorso principale", "paths": ["xmen"]},
                {"id": "solo", "label": "Percorsi personali", "paths": ["wolverine-616"]},
            ]
        elif hub["id"] == "spider":
            hub["groups"] = [
                {"id": "core", "label": "Percorso principale", "paths": ["spiderman"]},
                {"id": "symbiotes", "label": "Simbionti", "paths": ["venom"]},
            ]
        elif hub["id"] == "fantastic-four":
            hub["groups"] = [
                {"id": "core", "label": "Percorso principale", "paths": ["fantastic-four"]},
                {"id": "latveria", "label": "Latveria", "paths": ["doctor-doom"]},
            ]
        elif hub["id"] == "mystic":
            groups = [group for group in hub.get("groups", []) if group["id"] != "crossroads"]
            groups.append({"id": "crossroads", "label": "Magia, scienza e potere", "paths": ["doctor-doom"]})
            hub["groups"] = groups
        elif hub["id"] == "cosmic":
            groups = [group for group in hub.get("groups", []) if group["id"] != "crossroads"]
            groups.append({"id": "crossroads", "label": "Imperi e potere assoluto", "paths": ["doctor-doom"]})
            hub["groups"] = groups
    write_json(path, payload)


def update_hulk_archive_link() -> None:
    path = DATA / "characters" / "hulk.json"
    payload = read_json(path)
    for archive in payload.get("archives", []):
        if archive.get("publisher") == "Editoriale Corno":
            archive["status"] = "Disponibile come percorso storico separato; non altera il progresso moderno"
            archive["pathId"] = "hulk-classic-corno"
    payload.setdefault("relatedPaths", [])
    for related_id in ("hulk-classic-corno", "daredevil"):
        if related_id not in payload["relatedPaths"]:
            payload["relatedPaths"].append(related_id)
    write_json(path, payload)


SVG_MARKS = {
    "hulk-classic-corno": '<path d="M36 35h15l5 24h16l5-24h15l-8 58H44Z"/><path d="M45 73h38v16H45Z" fill="#0b0f17"/>',
    "daredevil": '<path d="M35 31h18v24h9c23 0 36 10 36 29 0 20-14 31-39 31H35Zm18 42v24h8c12 0 19-4 19-13 0-8-6-11-19-11Z"/><path d="M64 22h17v74H64Z" opacity=".72"/>',
    "wolverine-616": '<path d="m23 36 20 15 21-32 21 32 20-15-9 70-32 10-32-10Z"/><path d="M43 66h42L78 96H50Z" fill="#0b0f17"/><path d="m49 75 10 8-12 8m32-16-10 8 12 8" fill="none" stroke="currentColor" stroke-width="6"/>',
    "venom": '<path d="M21 43c17-20 34-20 43 2 9-22 26-22 43-2-4 38-20 65-43 73-23-8-39-35-43-73Z"/><path d="M38 53c8-9 15-8 22 4-10-2-16 1-22 8Zm52 0c-8-9-15-8-22 4 10-2 16 1 22 8ZM43 77c15 10 27 10 42 0-4 22-14 31-21 31s-17-9-21-31Z" fill="#0b0f17"/>',
    "doctor-doom": '<path d="M35 24h58l10 30-10 47-29 15-29-15-10-47Z"/><path d="M43 42h42l7 16-9 34-19 10-19-10-9-34Z" fill="#0b0f17"/><path d="M48 60h12v9H48Zm20 0h12v9H68ZM50 82h28" fill="none" stroke="currentColor" stroke-width="6"/>',
}


def write_logos(config: dict[str, Any]) -> None:
    target = ROOT / "assets" / "heroes"
    target.mkdir(parents=True, exist_ok=True)
    for spec in config["paths"]:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" '
            f'style="color:{spec["accent"]}"><circle cx="64" cy="64" r="58" '
            'fill="#0b0f17" stroke="currentColor" stroke-width="5"/>'
            f'<g fill="currentColor" stroke-linecap="round" stroke-linejoin="round">{SVG_MARKS[spec["id"]]}</g></svg>'
        )
        (target / f"{spec['id']}.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use only the shared ComicsBox cache")
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "8")))
    args = parser.parse_args()
    legacy.OFFLINE = args.offline

    config = read_json(CONFIG_PATH)
    expected = ["hulk-classic-corno", "daredevil", "wolverine-616", "venom", "doctor-doom"]
    if [path["id"] for path in config.get("paths", [])] != expected:
        raise RuntimeError("ordine dei cinque percorsi non valido")

    manifest_before = read_json(DATA / "characters.json")
    existing_catalog = read_json(DATA / "catalog.json")
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    expansion_ids = {path["id"] for path in config["paths"]}
    pre_expansion_album_codes = {
        legacy.album_code(issue.get("url"))
        for issue in existing_catalog.get("issues", [])
        if any(path_id not in expansion_ids for path_id in issue.get("paths", []))
    }
    pre_expansion_album_codes.discard("")
    unique_codes = sorted({source["code"] for path in config["paths"] for source in path["sources"]})
    log(f"Serie USA da verificare: {len(unique_codes)}")

    series_results: dict[str, dict[str, Any]] = {}
    source_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(legacy.load_foreign_series, code): code for code in unique_codes}
        for completed, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                series_results[code] = future.result()
            except Exception as error:
                source_errors[code] = str(error)
                log(f"  ! {code}: {error}")
            if completed % 15 == 0 or completed == len(futures):
                log(f"Serie USA: {completed}/{len(futures)}")

    path_chapters: dict[str, list[dict[str, Any]]] = {}
    source_summaries: dict[str, list[dict[str, Any]]] = {}
    all_italian_codes: set[str] = set()
    force_content_codes: set[str] = set()
    known_contents: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in config["paths"]:
        chapters, summaries = legacy.source_chapters(path, series_results, source_errors)
        chapters.extend(legacy.reused_chapters(path, manifest_before))
        path_chapters[path["id"]] = chapters
        source_summaries[path["id"]] = summaries
        for chapter in chapters:
            italian_code = chapter.get("italianCode", "")
            if not italian_code:
                continue
            all_italian_codes.add(italian_code)
            if chapter["kind"] == "chapter":
                known_contents[italian_code] = merge_contents(known_contents[italian_code], [chapter_content(chapter)])
            if (
                path["id"] == "hulk-classic-corno"
                or chapter["kind"] == "reuse"
                or (path["id"] == "daredevil" and italian_code.startswith("DEH_M_"))
            ):
                force_content_codes.add(italian_code)

    metadata_by_album: dict[str, dict[str, Any]] = {}
    album_errors: dict[str, str] = {}
    content_warnings: dict[str, str] = {}
    fetch_codes = sorted((all_italian_codes - set(existing_by_album)) | force_content_codes)
    for code in all_italian_codes - set(fetch_codes):
        metadata_by_album[code] = deepcopy(existing_by_album[code])
        metadata_by_album[code]["albumCode"] = code

    log(
        f"Albi italiani unici: {len(all_italian_codes)} "
        f"({len(fetch_codes)} da arricchire, inclusi gli antologici condivisi)"
    )
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(load_italian_album, code): code for code in fetch_codes}
        for completed, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                metadata_by_album[code] = future.result()
            except Exception as error:
                if code in existing_by_album:
                    content_warnings[code] = str(error)
                    metadata_by_album[code] = deepcopy(existing_by_album[code])
                    metadata_by_album[code]["albumCode"] = code
                else:
                    album_errors[code] = str(error)
                log(f"  ! albo {code}: {error}")
            if completed % 40 == 0 or completed == len(futures):
                log(f"Albi italiani: {completed}/{len(futures)}")

    physical_by_album = legacy.assign_physical_ids(metadata_by_album, existing_by_album, existing_id_to_album)
    contents_by_album: dict[str, list[dict[str, Any]]] = {}
    content_status_by_album: dict[str, str] = {}
    for code, physical in physical_by_album.items():
        metadata = metadata_by_album.get(code, {})
        for key in ("publisher", "dateQuality", "coverSource"):
            if physical.get(key) in (None, "", []) and metadata.get(key) not in (None, "", []):
                physical[key] = metadata[key]
        parsed = metadata.get("contents", [])
        contents = merge_contents(parsed, known_contents.get(code, []))
        contents_by_album[code] = contents
        content_status_by_album[code] = "complete" if parsed else "path-scoped"
        physical["contents"] = contents
        physical["contentsStatus"] = content_status_by_album[code]

    characters: dict[str, dict[str, Any]] = {}
    audits: list[dict[str, Any]] = []
    for path in config["paths"]:
        character, audit = build_character(
            path,
            path_chapters[path["id"]],
            physical_by_album,
            contents_by_album,
            content_status_by_album,
        )
        audit["sources"] = source_summaries[path["id"]]
        characters[path["id"]] = character
        audits.append(audit)
        log(
            f"{path['name']}: {character['coverage']['mappedChapters']}/"
            f"{character['coverage']['originalChapters']} capitoli, {len(character['issues'])} albi"
        )

    add_shared_labels(characters, manifest_before, existing_catalog)
    for path_id, character in characters.items():
        write_json(DATA / "characters" / f"{path_id}.json", character)

    physical_paths: dict[str, list[str]] = defaultdict(list)
    for path_id, character in characters.items():
        for issue in character["issues"]:
            physical_paths[issue["id"]].append(path_id)
    overlaps = {
        issue_id: sorted(set(paths))
        for issue_id, paths in physical_paths.items()
        if len(set(paths)) > 1
    }

    audit_payload = {
        "version": 1,
        "manifestVersion": MANIFEST_VERSION,
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": config["source"],
        "rules": config["rules"],
        "pathOrder": expected,
        "summary": {
            "paths": len(expected),
            "uniqueUsSeries": len(unique_codes),
            "validUsSeries": len(series_results),
            "invalidUsSeries": len(source_errors),
            "uniqueItalianAlbums": len(physical_by_album),
            "reusedExistingAlbums": len(set(physical_by_album) & pre_expansion_album_codes),
            "newItalianAlbums": len(set(physical_by_album) - pre_expansion_album_codes),
            "completeContentAlbums": sum(status == "complete" for status in content_status_by_album.values()),
            "pathScopedContentAlbums": sum(status == "path-scoped" for status in content_status_by_album.values()),
            "crossPathPhysicalOverlaps": len(overlaps),
        },
        "sourceErrors": source_errors,
        "albumErrors": album_errors,
        "contentWarnings": content_warnings,
        "crossPathPhysicalOverlaps": overlaps,
        "paths": audits,
    }
    write_json(AUDIT_PATH, audit_payload, pretty=True)
    update_manifest(config, characters)
    update_hubs()
    update_hulk_archive_link()
    write_logos(config)
    log(f"Audit: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
