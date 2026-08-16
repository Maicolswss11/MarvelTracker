#!/usr/bin/env python3
"""Rebuild Doctor Strange with explicit Italian physical issue -> USA contents -> reading step mapping.

The audited pre-2005 spine deliberately distinguishes published Italian material from gaps.
Unlicensed/fan translations are never treated as official ownership alternatives.
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
AUDIT_PATH = DATA / "doctor-strange-audit.json"
AUDIT_DATE = "2026-08-16"

MASTERWORK_CODES = [
    "MMW_M_067", "MMW_M_083", "MMW_M_097", "MMW_M_114", "MMW_M_135",
    "MMW_M_150", "MMW_M_169", "MMW_M_186", "MMW_M_203",
]

DS3_GAP_NUMBERS = set(range(14, 19)) | set(range(20, 28)) | set(range(29, 42)) | set(range(54, 57)) | set(range(62, 76))
ST2_GAP_NUMBERS = set(range(1, 7)) | set(range(8, 20))

SOURCE_SPECS = [
    {"code": "ST1", "era": "Origini — Strange Tales", "include": lambda n: 110 <= n <= 168 and n not in {112, 113}},
    {"code": "DS1", "era": "Doctor Strange classico", "include": lambda n: 169 <= n <= 183 and n != 179},
    {"code": "MFEAT1", "era": "Verso i Difensori", "include": lambda n: n == 1},
    {"code": "MP1", "era": "Marvel Premiere — ritorno di Strange", "include": lambda n: 3 <= n <= 14},
    {"code": "DS2", "era": "Doctor Strange (1974)", "include": lambda n: 1 <= n <= 81},
    {"code": "DSA", "era": "Annual e speciali", "include": lambda n: n in {1, 2, 4}},
    {"code": "ST2", "era": "Strange Tales (1987) — transizione", "include": lambda n: 1 <= n <= 19},
    {"code": "DS3", "era": "Sorcerer Supreme", "include": lambda n: 1 <= n <= 90},
    {"code": "MGN_STDO", "era": "Sorcerer Supreme — Trionfo e Tormento", "include": lambda n: n == 1},
    {"code": "DS_DISTU", "era": "Fine anni Novanta", "include": lambda n: n == 1},
    {"code": "DS_TFOBO", "era": "Marvel Knights — Il volo delle ossa", "include": lambda n: 1 <= n <= 4},
]

# Main-story publication overrides where a ComicsBox issue page also exposes separately published backups.
# The route follows Stephen Strange's principal story, not an unrelated backup from the same US issue.
FORCED_ITALIAN = {
    "ST2_007": "WOL_PM_032",
    "MGN_STDO_001": "PSPP_006",
}


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


def norm(value: str) -> str:
    value = str(value or "").casefold().replace("’", "'")
    return " ".join(value.split())


def content_url(code: str) -> str:
    return f"https://www.comicsbox.it/albo/{code}"


def load_album(code: str) -> dict[str, Any]:
    return five.load_italian_album(code)


def load_albums(codes: set[str], workers: int, seed: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    result = {key: deepcopy(value) for key, value in (seed or {}).items() if key in codes}
    errors: dict[str, str] = {}
    pending = sorted(codes - set(result))
    if not pending:
        return result, errors
    log(f"Albi italiani da leggere: {len(pending)}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(load_album, code): code for code in pending}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                result[code] = future.result()
            except Exception as error:
                errors[code] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Albi italiani letti: {index}/{len(futures)}")
    return result, errors


def masterwork_content_map(workers: int) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    albums, errors = load_albums(set(MASTERWORK_CODES), workers)
    if errors:
        raise RuntimeError("Masterworks Doctor Strange non risolti: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))
    mapping: dict[str, str] = {}
    for album_code in MASTERWORK_CODES:
        album = albums[album_code]
        for content in album.get("contents", []):
            content_id = content.get("id")
            if content_id:
                mapping.setdefault(content_id, album_code)
    log(f"Masterworks: {len(mapping)} contenuti USA indicizzati in {len(albums)} volumi")
    return mapping, albums


def forced_publication(usa_code: str, row_italian: str, mmw_map: dict[str, str]) -> str:
    if usa_code in mmw_map:
        return mmw_map[usa_code]
    if usa_code in FORCED_ITALIAN:
        return FORCED_ITALIAN[usa_code]
    match = re.fullmatch(r"ST2_0*(\d+)", usa_code)
    if match:
        number = int(match.group(1))
        return "" if number in ST2_GAP_NUMBERS else row_italian
    match = re.fullmatch(r"DS3_0*(\d+)", usa_code)
    if match:
        number = int(match.group(1))
        return "" if number in DS3_GAP_NUMBERS else row_italian
    match = re.fullmatch(r"DSA_0*(\d+)", usa_code)
    if match and int(match.group(1)) == 4:
        return ""
    return row_italian


def load_classic_chapters(workers: int) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    mmw_map, mmw_albums = masterwork_content_map(workers)
    loaded: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(SOURCE_SPECS))) as pool:
        futures = {pool.submit(legacy.load_foreign_series, spec["code"]): spec for spec in SOURCE_SPECS}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                loaded[spec["code"]] = future.result()
            except Exception as error:
                errors[spec["code"]] = str(error)
    if errors:
        raise RuntimeError("Serie USA Doctor Strange non risolte: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    chapters: list[dict[str, Any]] = []
    source_summary: list[dict[str, Any]] = []
    for source_index, spec in enumerate(SOURCE_SPECS):
        series = loaded[spec["code"]]
        chosen = []
        for row in series.get("rows", []):
            number = number_token(row.get("number", ""))
            if number is None or not spec["include"](number):
                continue
            usa_code = row["code"]
            italian_code = forced_publication(usa_code, row.get("italianCode", ""), mmw_map)
            title = row.get("title", "")
            label = f"{series['name']} #{row['number']}"
            if title and title != row.get("number"):
                label += f" — {title}"
            chapters.append({
                "kind": "chapter",
                "sourceCode": spec["code"],
                "sourceName": series["name"],
                "usaCode": usa_code,
                "usaNumber": row.get("number", ""),
                "usaTitle": title,
                "usaDate": row.get("date", ""),
                "authors": row.get("authors", ""),
                "label": label,
                "era": spec["era"],
                "italianCode": italian_code,
                "italianLabel": row.get("italianLabel", ""),
                "sort": legacy.original_date_key(row.get("date", ""), source_index, row.get("number", "")),
            })
            chosen.append((usa_code, italian_code))
        source_summary.append({
            "code": spec["code"],
            "name": series["name"],
            "chapters": len(chosen),
            "mapped": sum(bool(italian) for _, italian in chosen),
            "unmapped": sum(not bool(italian) for _, italian in chosen),
        })
    chapters.sort(key=lambda item: item["sort"])
    log(f"Spina classica: {len(chapters)} capitoli; {sum(bool(c['italianCode']) for c in chapters)} con pubblicazione italiana")
    return chapters, {"sources": source_summary, "masterworkContents": len(mmw_map)}, mmw_albums


def prepare_classic_physical(chapters: list[dict[str, Any]], workers: int, mmw_albums: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, str], dict[str, str]]:
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    codes = {chapter.get("italianCode", "") for chapter in chapters if chapter.get("italianCode")}
    metadata, errors = load_albums(codes, workers, seed=mmw_albums)

    for code in codes:
        if code not in metadata and code in existing_by_album:
            metadata[code] = deepcopy(existing_by_album[code])
            metadata[code]["albumCode"] = code
            metadata[code].setdefault("contents", deepcopy(existing_by_album[code].get("contents", [])))

    missing_metadata = sorted(codes - set(metadata))
    if missing_metadata:
        raise RuntimeError("Metadati italiani mancanti: " + ", ".join(missing_metadata))

    contents_by_album: dict[str, list[dict[str, Any]]] = {}
    for code in codes:
        contents_by_album[code] = deepcopy(metadata[code].get("contents", []))

    # Ensure every selected USA issue is represented even if the source page's HTML omitted an anchor.
    for chapter in chapters:
        code = chapter.get("italianCode", "")
        if not code:
            continue
        content = {
            "id": chapter["usaCode"],
            "seriesId": chapter["sourceCode"],
            "series": chapter["sourceName"],
            "number": chapter["usaNumber"],
            "title": chapter["label"],
            "url": content_url(chapter["usaCode"]),
        }
        contents_by_album[code] = five.merge_contents(contents_by_album.get(code, []), [content])
        metadata[code]["contents"] = contents_by_album[code]
        metadata[code]["contentsStatus"] = "complete"

    physical = legacy.assign_physical_ids(metadata, existing_by_album, existing_id_to_album)
    for code, issue in physical.items():
        issue["contents"] = contents_by_album.get(code, [])
        issue["contentsStatus"] = "complete"
    statuses = {code: "complete" for code in codes}
    return physical, contents_by_album, statuses, errors


def choose_tail_contents(contents: list[dict[str, Any]], issue: dict[str, Any]) -> list[str]:
    selected: list[str] = []
    for content in contents:
        text = norm(" ".join(str(content.get(key, "")) for key in ("series", "title", "seriesId")))
        if any(marker in text for marker in ("doctor strange", "dr. strange", "dr strange", "dottor strange", "sorcerer supreme", "strange", "stregone supremo")):
            selected.append(content["id"])
    if selected:
        return list(dict.fromkeys(selected))
    # Existing tail was already manually curated. For a dedicated one-volume miniseries, keeping all
    # contents is safer than producing an empty reading step; the audit records this fallback.
    return [content["id"] for content in contents if content.get("id")]


def enrich_tail(existing: dict[str, Any], start_position: int, workers: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tail_start = next((index for index, issue in enumerate(existing.get("issues", [])) if issue.get("id") == "100M:31"), None)
    if tail_start is None:
        raise RuntimeError("Doctor Strange tail anchor 100M:31 non trovato")
    original_tail = deepcopy(existing["issues"][tail_start:])
    codes = {legacy.album_code(issue.get("url")) for issue in original_tail}
    codes.discard("")
    metadata, errors = load_albums(codes, workers)
    if errors:
        raise RuntimeError("Tail Doctor Strange non risolta: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    enriched: list[dict[str, Any]] = []
    fallback_ids: list[str] = []
    position = start_position
    for issue in original_tail:
        code = legacy.album_code(issue.get("url"))
        album = metadata.get(code, {})
        contents = deepcopy(album.get("contents", []))
        if not contents:
            raise RuntimeError(f"{issue.get('id')}: nessun contenuto USA rilevato")
        selected = choose_tail_contents(contents, issue)
        if len(selected) == len(contents) and len(contents) > 1:
            fallback_ids.append(issue.get("id", code))
        issue["seq"] = position
        issue["contents"] = contents
        issue["contentsStatus"] = "complete"
        issue["usaChapters"] = [content.get("title") or f"{content.get('series')} #{content.get('number')}" for content in contents if content.get("id") in selected]
        issue["sourceSeries"] = list(dict.fromkeys(content.get("seriesId") for content in contents if content.get("id") in selected and content.get("seriesId")))
        issue["readingStep"] = {
            "pathId": "doctor-strange",
            "position": position,
            "contentIds": selected,
            "scope": "selected-contents",
        }
        enriched.append(issue)
        position += 1
    return enriched, {"tailIssues": len(enriched), "fallbackWholeAlbumSelection": fallback_ids}


def series_index(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for issue in issues:
        series_id = issue.get("seriesId") or issue.get("id", "").split(":", 1)[0]
        rows.setdefault(series_id, {
            "id": series_id,
            "name": issue.get("series") or series_id,
            "publisher": issue.get("publisher") or "Editore italiano non indicato",
            "range": "pubblicazioni italiane censite",
        })
    return list(rows.values())


def update_manifest(character: dict[str, Any]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    found = False
    for item in manifest.get("characters", []):
        if item.get("id") != "doctor-strange":
            continue
        item["start"] = character["start"]
        item["end"] = character["end"]
        item["totalRequired"] = character["totalRequired"]
        item["pathRole"] = "main"
        item["mainPath"] = True
        item["auditStatus"] = "audited"
        item["auditKind"] = "path/character"
        item["auditDate"] = AUDIT_DATE
        found = True
        break
    if not found:
        raise RuntimeError("doctor-strange assente dal manifest")
    # Never regress the global manifest version from newer builders.
    manifest["version"] = max(int(manifest.get("version", 1)), 36)
    write_json(path, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "16")))
    args = parser.parse_args()
    workers = max(1, args.workers)

    existing_path = DATA / "characters" / "doctor-strange.json"
    existing = read_json(existing_path)
    chapters, source_audit, mmw_albums = load_classic_chapters(workers)
    physical, contents_by_album, statuses, album_errors = prepare_classic_physical(chapters, workers, mmw_albums)

    path_spec = {
        "id": "doctor-strange",
        "name": "Doctor Strange",
        "subtitle": "Stephen Strange · Stregone Supremo",
        "accent": "#8d66d9",
        "description": "Percorso narrativo di Stephen Strange auditato per contenuto USA e pubblicazione italiana ufficiale.",
        "pathRole": "main",
        "mainPath": True,
        "relatedPaths": existing.get("relatedPaths", ["doctor-doom", "scarletwitch"]),
    }
    classic_character, classic_audit = five.build_character(path_spec, chapters, physical, contents_by_album, statuses)
    classic_issues = classic_character["issues"]
    tail, tail_audit = enrich_tail(existing, len(classic_issues) + 1, workers)
    issues = classic_issues + tail

    required_count = sum(1 for issue in issues if issue.get("required") is not False and not issue.get("future"))
    all_content_ids = [content_id for issue in issues for content_id in issue.get("readingStep", {}).get("contentIds", [])]
    classic_missing = [mapping for mapping in classic_audit["mappings"] if not mapping.get("physicalId")]
    character = {
        "id": "doctor-strange",
        "name": "Doctor Strange",
        "subtitle": "Stephen Strange · Stregone Supremo",
        "accent": "#8d66d9",
        "start": f"{issues[0]['name']} — {issues[0]['date']}",
        "end": f"{issues[-1]['name']} — {issues[-1]['date']}",
        "description": (
            "Percorso di Stephen Strange ricostruito con il modello albo fisico italiano → contenuti USA → readingStep. "
            "La fase classica, Strange Tales e Sorcerer Supreme dichiarano esplicitamente le storie prive di edizione italiana ufficiale; "
            "traduzioni amatoriali non vengono conteggiate come pubblicazioni o alternative ufficiali."
        ),
        "timelineMode": True,
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
        "pathRole": "main",
        "mainPath": True,
        "readingOrderSource": "ComicsBox USA → pubblicazioni italiane; audit MarvelTracker 2026-08-16",
        "coverage": {
            "auditedClassicChapters": classic_audit["originalChapters"],
            "auditedClassicMappedChapters": classic_audit["mappedChapters"],
            "missingItalianPublications": len(classic_missing),
            "routeSelectedContents": len(all_content_ids),
            "physicalItalianIssues": len(issues),
            "completeContentAlbums": sum(issue.get("contentsStatus") == "complete" for issue in issues),
        },
        "series": series_index(issues),
        "archives": existing.get("archives", []),
        "relatedPaths": existing.get("relatedPaths", ["doctor-doom", "scarletwitch"]),
        "totalRequired": required_count,
        "availableTotal": required_count,
        "issues": issues,
    }
    write_json(existing_path, character)
    update_manifest(character)

    mapping_by_code = {row["usaCode"]: row for row in classic_audit["mappings"]}
    audit = {
        "version": 1,
        "status": "audited",
        "auditKind": "path/character",
        "auditDate": AUDIT_DATE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "editorialModel": character["editorialModel"],
        "scope": "Stephen Strange main reading spine from Strange Tales (1963) through the current route, with explicit pre-2005 Italian publication gaps",
        "sourceSummary": source_audit,
        "classic": {
            "chapters": classic_audit["originalChapters"],
            "mapped": classic_audit["mappedChapters"],
            "unpublishedInItaly": len(classic_missing),
            "physicalItalianIssues": classic_audit["physicalItalianIssues"],
        },
        "knownGaps": {
            "strangeTalesVol2DoctorStrange": [f"ST2_{n:03d}" for n in sorted(ST2_GAP_NUMBERS)],
            "sorcererSupremeMainStories": [f"DS3_{n:03d}" for n in sorted(DS3_GAP_NUMBERS)],
            "doctorStrangeAnnual4": ["DSA_004"],
        },
        "guardrails": {
            "dstrM2M3": "Dottor Strange #2-3 are not sequential Sorcerer Supreme issues and are excluded from that spine; their Secret Defenders / Annual material must be routed by selected USA content only.",
            "fanTranslations": "Unofficial/fan Italian translations may be noted externally by the reader but never satisfy official-edition ownership or availability in MarvelTracker.",
            "alternatives": "An alternative edition must expose the same selected USA content IDs; partial alternatives are recorded as partial and do not individually satisfy a route step.",
        },
        "tail": tail_audit,
        "albumFetchWarnings": album_errors,
        "mappings": classic_audit["mappings"],
        "checks": {
            "DS3_001": mapping_by_code.get("DS3_001"),
            "DS3_019": mapping_by_code.get("DS3_019"),
            "DS3_042": mapping_by_code.get("DS3_042"),
            "DS3_048": mapping_by_code.get("DS3_048"),
            "DS3_057": mapping_by_code.get("DS3_057"),
            "DS3_076": mapping_by_code.get("DS3_076"),
            "DS3_090": mapping_by_code.get("DS3_090"),
            "ST2_007": mapping_by_code.get("ST2_007"),
            "MGN_STDO_001": mapping_by_code.get("MGN_STDO_001"),
        },
    }
    write_json(AUDIT_PATH, audit, pretty=True)
    log(f"Doctor Strange: {len(issues)} tappe fisiche · {required_count} richieste · {len(classic_missing)} lacune classiche dichiarate")


if __name__ == "__main__":
    main()
