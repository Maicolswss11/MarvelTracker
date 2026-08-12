#!/usr/bin/env python3
"""Build New Mutants, X-Factor and X-Force as physical Italian paths.

Editorial invariant:
    physical Italian issue -> complete USA contents -> path-local readingStep

Only explicitly curated Earth-616 team series enter the build. Existing physical
album IDs are reused globally and albums lacking a complete content map are
re-enriched from ComicsBox before the path is written.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_character_wave1 as matrix
import build_cosmic_supernatural_expansion as legacy
import build_five_character_expansion as five
import build_mutant_street_wave as solo_base
import build_street_wave as street
import build_xmen_wave1 as source_resolver

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "mutant-teams-wave1-sources.json"
AUDIT_PATH = DATA / "mutant-teams-wave1-audit.json"
RESOLVED_PATH = DATA / ".mutant-teams-wave1-resolved.json"
MANIFEST_VERSION = 29

SVG_MARKS = {
    "new-mutants": '<path d="M32 94V34l32 36 32-36v60" fill="none" stroke="currentColor" stroke-width="9"/><path d="M64 25v80" fill="none" stroke="currentColor" stroke-width="6"/>',
    "x-factor": '<path d="m35 31 58 66M93 31 35 97" fill="none" stroke="currentColor" stroke-width="12"/><circle cx="64" cy="64" r="38" fill="none" stroke="currentColor" stroke-width="6"/>',
    "x-force": '<path d="m30 29 68 70M98 29 30 99" fill="none" stroke="currentColor" stroke-width="13"/><circle cx="64" cy="64" r="15" fill="#0b0f17"/><path d="M64 17v17M64 94v17M17 64h17M94 64h17" fill="none" stroke="currentColor" stroke-width="6"/>',
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


def source_display_names(config: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for path in config["paths"]:
        for raw in path.get("sources", []):
            source = street.source_spec(raw)
            name = source.get("resolvedTitle") or source.get("title") or source["code"]
            names[source["code"]] = name
    return names


def load_sources(config: dict[str, Any], workers: int) -> dict[str, dict[str, Any]]:
    loaded, errors = street.load_config_sources(config, min(workers, 8))
    names = source_display_names(config)
    retry_delays = (5, 15, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not errors:
            break
        failed_codes = sorted(errors)
        log(f"Retry sorgenti {retry}/{len(retry_delays)} tra {delay}s: {', '.join(failed_codes)}")
        time.sleep(delay)
        for code in failed_codes:
            try:
                loaded[code] = legacy.load_foreign_series(code)
                loaded[code]["name"] = names[code]
                errors.pop(code, None)
            except Exception as error:
                errors[code] = str(error)
    if errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(errors.items()))
        raise RuntimeError(f"ComicsBox source load failed after retries: {details}")
    return loaded


def existing_content_seed(
    chapters_by_path: dict[str, list[dict[str, Any]]], workers: int
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, str]]:
    existing_by_album, _ = legacy.existing_physical_map()
    mapped_codes = {
        chapter.get("italianCode", "")
        for chapters in chapters_by_path.values()
        for chapter in chapters
        if chapter.get("italianCode")
    }
    metadata: dict[str, dict[str, Any]] = {}
    contents: dict[str, list[dict[str, Any]]] = {}
    to_fetch: list[str] = []
    for code in sorted(mapped_codes & set(existing_by_album)):
        issue = existing_by_album[code]
        issue_contents = issue.get("contents") if isinstance(issue.get("contents"), list) else []
        if issue.get("contentsStatus") == "complete" and issue_contents:
            metadata[code] = deepcopy(issue)
            metadata[code]["albumCode"] = code
            contents[code] = deepcopy(issue_contents)
        else:
            to_fetch.append(code)

    log(f"Albi esistenti da arricchire: {len(to_fetch)}")
    errors: dict[str, str] = {}

    def fetch_all(codes: list[str]) -> None:
        with ThreadPoolExecutor(max_workers=min(workers, 16)) as pool:
            futures = {pool.submit(five.load_italian_album, code): code for code in codes}
            for index, future in enumerate(as_completed(futures), 1):
                code = futures[future]
                try:
                    item = future.result()
                    metadata[code] = item
                    contents[code] = item.get("contents", [])
                    errors.pop(code, None)
                except Exception as error:
                    errors[code] = str(error)
                if index % 50 == 0 or index == len(futures):
                    log(f"Albi esistenti arricchiti: {index}/{len(futures)}")

    fetch_all(to_fetch)
    retry_delays = (5, 15, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not errors:
            break
        failed_codes = sorted(errors)
        log(f"Retry albi esistenti {retry}/{len(retry_delays)} tra {delay}s: {', '.join(failed_codes)}")
        time.sleep(delay)
        fetch_all(failed_codes)
    if errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(errors.items()))
        raise RuntimeError(f"ComicsBox existing-album enrichment failed after retries: {details}")
    return metadata, contents, errors


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {spec["id"] for spec in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "xmen": ["new-mutants", "x-factor", "x-force"],
        "magik": ["new-mutants"],
        "cable": ["new-mutants", "x-force"],
        "cyclops": ["x-factor"],
        "jean-grey": ["x-factor"],
        "quicksilver": ["x-factor"],
        "deadpool": ["x-force"],
        "wolverine-616": ["x-force"],
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


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    xmen = next((hub for hub in payload.get("hubs", []) if hub.get("id") == "xmen"), None)
    if xmen:
        groups = xmen.setdefault("groups", [])
        teams = next((group for group in groups if group.get("id") == "teams"), None)
        if teams is None:
            teams = {"id": "teams", "label": "Squadre mutanti", "paths": []}
            core_index = next((index for index, group in enumerate(groups) if group.get("id") == "core"), -1)
            groups.insert(core_index + 1, teams)
        for path_id in ("new-mutants", "x-factor", "x-force"):
            if path_id not in teams["paths"]:
                teams["paths"].append(path_id)
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
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "16")))
    args = parser.parse_args()
    workers = max(1, args.workers)

    config = read_json(CONFIG_PATH)
    resolved, resolution = source_resolver.resolve_config(config)
    write_json(RESOLVED_PATH, resolved, pretty=True)
    manifest_before = read_json(DATA / "characters.json")
    catalog_before = read_json(DATA / "catalog.json")

    try:
        loaded = load_sources(resolved, workers)
        log(f"Sorgenti ComicsBox complete: {len(loaded)}")

        chapters_by_path: dict[str, list[dict[str, Any]]] = {}
        audits: list[dict[str, Any]] = []
        for spec in resolved["paths"]:
            dedicated, source_summary = solo_base.dedicated_chapters(spec, loaded, {}, {})
            chapters = matrix.dedupe_chapters(dedicated)
            chapters_by_path[spec["id"]] = chapters
            audits.append({
                "id": spec["id"],
                "name": spec["name"],
                "deduplicatedChapters": len(chapters),
                "sourceSeries": source_summary,
            })
            log(f"{spec['name']}: {len(chapters)} capitoli curati")

        reuse_metadata, reuse_contents, enrichment_errors = existing_content_seed(chapters_by_path, workers)
        physical, contents_by_album, content_status, album_errors = matrix.prepare_physical_maps(
            chapters_by_path, reuse_metadata, reuse_contents, workers
        )
        if album_errors:
            details = "; ".join(f"{code}: {error}" for code, error in sorted(album_errors.items()))
            raise RuntimeError(f"ComicsBox physical-album resolution failed: {details}")

        characters: dict[str, dict[str, Any]] = {}
        audit_by_id = {row["id"]: row for row in audits}
        for spec in resolved["paths"]:
            character, path_audit = five.build_character(
                spec, chapters_by_path[spec["id"]], physical, contents_by_album, content_status
            )
            character["readingOrderSource"] = "ComicsBox team series → prima pubblicazione italiana; selezione curatoriale MarvelTracker"
            character["classification"] = "mutant-team"
            characters[spec["id"]] = character
            audit_by_id[spec["id"]].update(path_audit)
            write_json(DATA / "characters" / f"{spec['id']}.json", character)
            log(
                f"  -> {character['name']}: {len(character['issues'])} albi fisici, "
                f"{path_audit['missingItalianPublications']} lacune"
            )

        five.add_shared_labels(characters, manifest_before, catalog_before)
        for path_id, character in characters.items():
            write_json(DATA / "characters" / f"{path_id}.json", character)

        update_manifest(resolved, characters)
        update_hubs()
        write_logos(resolved)

        existing_by_album, _ = legacy.existing_physical_map()
        all_albums = {
            legacy.album_code(issue.get("url"))
            for character in characters.values()
            for issue in character["issues"]
        }
        all_albums.discard("")
        audit_payload = {
            "version": 1,
            "manifestVersion": MANIFEST_VERSION,
            "editorialModel": config["editorialModel"],
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": config["source"],
            "rules": config["rules"],
            "summary": {
                "paths": len(resolved["paths"]),
                "candidateSeries": len({
                    street.source_spec(value)["code"]
                    for spec in resolved["paths"]
                    for value in spec.get("sources", [])
                }),
                "validSeries": len(loaded),
                "sourceErrors": 0,
                "contentEnrichmentErrors": len(enrichment_errors),
                "albumErrors": len(album_errors),
                "uniqueItalianAlbums": len(all_albums),
                "reusedExistingAlbums": len(all_albums & set(existing_by_album)),
                "newItalianAlbums": len(all_albums - set(existing_by_album)),
            },
            "sourceResolution": resolution,
            "contentEnrichmentErrors": enrichment_errors,
            "albumErrors": album_errors,
            "paths": audits,
        }
        write_json(AUDIT_PATH, audit_payload, pretty=True)
        log(f"Audit scritto: {AUDIT_PATH.relative_to(ROOT)}")
    finally:
        RESOLVED_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
