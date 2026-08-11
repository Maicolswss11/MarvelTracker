#!/usr/bin/env python3
"""Build/upgrade the street-level character wave.

Wave: Black Widow, Hawkeye, Luke Cage, Iron Fist, Jessica Jones, Punisher,
Moon Knight.

The builder keeps MarvelTracker's editorial invariant:

    physical Italian issue -> USA contents -> path reading step

Dedicated series are sourced from ComicsBox and may use explicit issue selectors
for anthology/mantle-sharing titles. Shared history is imported only when the
target character is credited among the protagonists of the USA story; cameo-only
appearances are excluded.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_character_wave1 as wave1
import build_cosmic_supernatural_expansion as legacy
import build_five_character_expansion as five

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "street-wave-sources.json"
AUDIT_PATH = DATA / "street-wave-audit.json"
MANIFEST_VERSION = 26

SVG_MARKS = {
    "hawkeye": '<path d="M23 64h69" fill="none" stroke="currentColor" stroke-width="8"/><path d="m83 42 23 22-23 22" fill="none" stroke="currentColor" stroke-width="8"/><circle cx="42" cy="64" r="15" fill="none" stroke="currentColor" stroke-width="7"/>',
    "blackwidow": '<path d="m64 58-20-24h40Zm0 12-20 24h40Z"/><circle cx="64" cy="64" r="16" fill="none" stroke="currentColor" stroke-width="7"/>',
    "luke-cage": '<path d="M35 45h58v39H35Z" fill="none" stroke="currentColor" stroke-width="8"/><path d="M45 45V30h38v15M44 84v17m40-17v17" fill="none" stroke="currentColor" stroke-width="8"/>',
    "iron-fist": '<path d="M42 83V49c0-8 10-8 10 0V34c0-8 11-8 11 0v14-20c0-8 11-8 11 0v21-14c0-8 11-8 11 0v34c0 25-12 38-28 38S36 96 36 83Z" fill="none" stroke="currentColor" stroke-width="7"/>',
    "jessica-jones": '<path d="M35 28h58v72H35Z" fill="none" stroke="currentColor" stroke-width="7"/><path d="M46 44h36M46 60h27M46 76h31" fill="none" stroke="currentColor" stroke-width="6"/>',
    "punisher": '<path d="M64 24c23 0 38 13 38 34 0 17-9 28-21 34v18H70V96H58v14H47V92c-12-6-21-17-21-34 0-21 15-34 38-34Z"/><path d="M41 57h18v12H41Zm28 0h18v12H69Z" fill="#0b0f17"/><path d="M48 80h32" fill="none" stroke="#0b0f17" stroke-width="7"/>',
    "moon-knight": '<path d="M82 24c-25 5-41 23-41 43 0 19 13 34 32 40-30 4-53-13-53-40 0-29 26-50 62-43Z"/><path d="m82 43 8 17 19 2-14 13 4 19-17-9-17 9 4-19-14-13 19-2Z"/>',
}


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def source_spec(value: Any) -> dict[str, Any]:
    return {"code": value} if isinstance(value, str) else value


def load_config_sources(config: dict[str, Any], workers: int):
    specs = [source_spec(value) for path in config["paths"] for value in path.get("sources", [])]
    codes = sorted({spec["code"] for spec in specs})
    display_names: dict[str, str] = {}
    for spec in specs:
        display_name = spec.get("resolvedTitle") or spec.get("title") or spec.get("discoveredTitle")
        if display_name:
            current = display_names.get(spec["code"])
            if current and current != display_name:
                raise RuntimeError(
                    f"conflicting display names for {spec['code']}: {current!r} / {display_name!r}"
                )
            display_names[spec["code"]] = display_name
    loaded: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    log(f"Serie dedicate candidate: {len(codes)}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(legacy.load_foreign_series, code): code for code in codes}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                loaded[code] = future.result()
                if display_names.get(code):
                    loaded[code]["name"] = display_names[code]
            except Exception as error:
                errors[code] = str(error)
            if index % 10 == 0 or index == len(futures):
                log(f"Serie dedicate verificate: {index}/{len(futures)}")
    return loaded, errors


def dedicated_chapters(path: dict[str, Any], loaded: dict[str, dict[str, Any]], source_errors: dict[str, str]):
    chapters: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for source_index, raw_source in enumerate(path.get("sources", [])):
        source = source_spec(raw_source)
        code = source["code"]
        series = loaded.get(code)
        rows = [] if not series else [
            row for row in series.get("rows", [])
            if legacy.included(row.get("number", ""), source.get("include"))
        ]
        for row in rows:
            label = f"{series['name']} #{row['number']}"
            if row.get("title") and row["title"] != row["number"]:
                label += f" — {row['title']}"
            date = row.get("date", "")
            chapters.append({
                "kind": "chapter",
                "sourceCode": code,
                "sourceName": series["name"],
                "usaCode": row["code"],
                "usaNumber": row["number"],
                "usaTitle": row.get("title", ""),
                "usaDate": date,
                "authors": row.get("authors", ""),
                "label": label,
                "era": source.get("era") or wave1.era_for_date(date),
                "italianCode": row.get("italianCode", ""),
                "italianLabel": row.get("italianLabel", ""),
                "sort": legacy.original_date_key(date, source_index, row["number"]),
                "origin": "dedicated-series",
            })
        summaries.append({
            "code": code,
            "name": series.get("name", code) if series else code,
            "selectors": source.get("include", ["all"]),
            "chapters": len(rows),
            "mapped": sum(bool(row.get("italianCode")) for row in rows),
            "unmapped": sum(not bool(row.get("italianCode")) for row in rows),
            **({"error": source_errors[code]} if code in source_errors else {}),
        })
    return chapters, summaries


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {spec["id"] for spec in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "avengers": ["hawkeye", "blackwidow", "luke-cage", "jessica-jones", "moon-knight"],
        "cap": ["hawkeye", "blackwidow"],
        "winter-soldier": ["blackwidow"],
        "daredevil": ["blackwidow", "luke-cage", "iron-fist", "jessica-jones", "punisher", "moon-knight"],
        "spiderman": ["luke-cage", "punisher", "moon-knight"],
        "wolverine-616": ["punisher"],
        "war-machine": ["punisher"],
        "ghost-rider": ["moon-knight"],
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


def ensure_group(groups: list[dict[str, Any]], group_id: str, label: str) -> dict[str, Any]:
    group = next((item for item in groups if item.get("id") == group_id), None)
    if group is None:
        group = {"id": group_id, "label": label, "paths": []}
        groups.append(group)
    return group


def update_hubs(config: dict[str, Any]) -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    by_id = {hub["id"]: hub for hub in payload.get("hubs", [])}

    avengers = by_id.get("avengers")
    if avengers:
        members = ensure_group(avengers.setdefault("groups", []), "members", "Membri e percorsi collegati")
        for path_id in ["hawkeye", "blackwidow", "luke-cage", "jessica-jones", "moon-knight"]:
            if path_id not in members["paths"]:
                members["paths"].append(path_id)

    street = by_id.get("street")
    if street:
        groups = street.setdefault("groups", [])
        core = ensure_group(groups, "core", "Hell's Kitchen")
        if "daredevil" not in core["paths"]:
            core["paths"].append("daredevil")
        defenders = ensure_group(groups, "defenders", "Heroes for Hire e investigatori")
        for path_id in ["luke-cage", "iron-fist", "jessica-jones"]:
            if path_id not in defenders["paths"]:
                defenders["paths"].append(path_id)
        vigilantes = ensure_group(groups, "vigilantes", "Vigilanti urbani")
        for path_id in ["punisher", "moon-knight"]:
            if path_id not in vigilantes["paths"]:
                vigilantes["paths"].append(path_id)
        operatives = ensure_group(groups, "operatives", "Agenti e tiratori")
        for path_id in ["blackwidow", "hawkeye"]:
            if path_id not in operatives["paths"]:
                operatives["paths"].append(path_id)

    mystic = by_id.get("mystic")
    if mystic:
        supernatural = ensure_group(mystic.setdefault("groups", []), "supernatural", "Spiriti, vampiri e Figli della Mezzanotte")
        if "moon-knight" not in supernatural["paths"]:
            supernatural["paths"].append("moon-knight")

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
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "14")))
    args = parser.parse_args()
    workers = max(1, args.workers)
    config = read_json(CONFIG_PATH)
    manifest_before = read_json(DATA / "characters.json")
    catalog_before = read_json(DATA / "catalog.json")

    loaded, source_errors = load_config_sources(config, workers)
    per_base, _ = wave1.load_reuse_issues(config, manifest_before)
    reuse_contents, reuse_metadata, reuse_album_errors = wave1.enrich_reuse_contents(per_base, workers)
    role_map, role_errors = wave1.scan_content_roles(reuse_contents, config, workers)

    chapters_by_path: dict[str, list[dict[str, Any]]] = {}
    audits: list[dict[str, Any]] = []
    for spec in config["paths"]:
        dedicated, source_summary = dedicated_chapters(spec, loaded, source_errors)
        shared, shared_stats = wave1.shared_chapters(spec, per_base, reuse_contents, role_map)
        chapters = wave1.dedupe_chapters(dedicated + shared)
        chapters_by_path[spec["id"]] = chapters
        audits.append({
            "id": spec["id"], "name": spec["name"],
            "dedicatedChapters": len(dedicated), "sharedProtagonistChapters": len(shared),
            "deduplicatedChapters": len(chapters), "sourceSeries": source_summary,
            "sharedScan": shared_stats,
        })
        log(f"{spec['name']}: {len(dedicated)} dedicati + {len(shared)} condivisi = {len(chapters)} capitoli")

    physical, contents_by_album, content_status, album_errors = wave1.prepare_physical_maps(
        chapters_by_path, reuse_metadata, reuse_contents, workers
    )

    characters: dict[str, dict[str, Any]] = {}
    audit_by_id = {row["id"]: row for row in audits}
    for spec in config["paths"]:
        character, path_audit = five.build_character(
            spec, chapters_by_path[spec["id"]], physical, contents_by_album, content_status
        )
        character["readingOrderSource"] = "ComicsBox serie dedicate + selettori espliciti + riuso protagonista-only dai percorsi MarvelTracker esistenti"
        character["sharedHistoryPolicy"] = "protagonists-only; simple appearances excluded"
        if spec["id"] == "punisher":
            character["continuityPolicy"] = "Earth-616 only; MAX/Noir/alternate continuities excluded"
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
            "candidateDedicatedSeries": len({source_spec(value)["code"] for spec in config["paths"] for value in spec.get("sources", [])}),
            "validDedicatedSeries": len(loaded),
            "sourceErrors": len(source_errors),
            "sharedUsStoriesScanned": len(role_map),
            "sharedUsStoryErrors": len(role_errors),
            "uniqueItalianAlbums": len(all_albums),
            "reusedExistingAlbums": len(all_albums & set(existing_by_album)),
            "newItalianAlbums": len(all_albums - set(existing_by_album)),
        },
        "sourceErrors": source_errors,
        "reuseAlbumErrors": reuse_album_errors,
        "roleScanErrors": role_errors,
        "albumErrors": album_errors,
        "paths": audits,
    }
    write_json(AUDIT_PATH, audit_payload, pretty=True)
    log(f"Audit scritto: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
