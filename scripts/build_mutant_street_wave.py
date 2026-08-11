#!/usr/bin/env python3
"""Build Elektra, Deadpool, Cable and Magik reading paths.

Editorial invariant:
    physical Italian issue -> USA contents -> path-local readingStep

Dedicated series are imported from ComicsBox. Team/co-billed sources flagged
``protagonistOnly`` are filtered story-by-story through ComicsBox protagonist
credits. Existing MarvelTracker paths are reused with the same protagonist-only
policy, so ownership stays attached to one physical Italian issue while reading
progress remains local to each character path.
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
import build_street_wave as street

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "mutant-street-wave-sources.json"
AUDIT_PATH = DATA / "mutant-street-wave-audit.json"
MANIFEST_VERSION = 27

SVG_MARKS = {
    "elektra": '<path d="M31 91 91 31M37 35l56 56M25 71l20 20M71 25l20 20" fill="none" stroke="currentColor" stroke-width="8"/><circle cx="64" cy="64" r="12"/>',
    "deadpool": '<path d="M64 23c23 0 38 17 38 41s-15 41-38 41S26 88 26 64s15-41 38-41Z"/><path d="M64 23v82" fill="none" stroke="#0b0f17" stroke-width="6"/><path d="M39 55c9-7 17-7 24 0-3 13-10 20-21 18Zm50 0c-9-7-17-7-24 0 3 13 10 20 21 18Z" fill="#0b0f17"/>',
    "cable": '<path d="M35 27h58l11 35-18 43H42L24 62Z"/><path d="M62 29v76M37 57h20M71 57h21" fill="none" stroke="#0b0f17" stroke-width="7"/><circle cx="81" cy="61" r="8" fill="#0b0f17"/>',
    "magik": '<path d="m71 18 13 10-8 20 28 43-13 10-27-42-18 47-14-6 22-58Z"/><path d="m35 26 8 17 19 2-14 13 4 19-17-9-17 9 4-19-14-13 19-2Z"/>',
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


def filtered_source_roles(config: dict[str, Any], loaded: dict[str, dict[str, Any]], workers: int):
    interested: dict[str, set[str]] = defaultdict(set)
    for path in config["paths"]:
        for raw_source in path.get("sources", []):
            source = street.source_spec(raw_source)
            if not source.get("protagonistOnly"):
                continue
            series = loaded.get(source["code"])
            if not series:
                continue
            for row in series.get("rows", []):
                if legacy.included(row.get("number", ""), source.get("include")):
                    interested[row["code"]].add(path["id"])

    aliases = {path["id"]: path["aliases"] for path in config["paths"]}
    result: dict[str, list[str]] = {}
    errors: dict[str, str] = {}
    codes = sorted(interested)
    log(f"Storie USA di squadra da filtrare: {len(codes)}")

    def inspect(code: str):
        source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{code}")
        paths = [path_id for path_id in interested[code]
                 if wave1.credited_as_protagonist(source, aliases[path_id])]
        return code, paths

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(inspect, code): code for code in codes}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                key, paths = future.result()
                result[key] = paths
            except Exception as error:
                errors[code] = str(error)
            if index % 100 == 0 or index == len(futures):
                log(f"Storie USA di squadra filtrate: {index}/{len(futures)}")

    retry_delays = (3, 10, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not errors:
            break
        failed_codes = sorted(errors)
        log(
            f"Retry storie team {retry}/{len(retry_delays)} tra {delay}s: "
            + ", ".join(failed_codes)
        )
        __import__("time").sleep(delay)
        for code in failed_codes:
            try:
                key, paths = inspect(code)
                result[key] = paths
                errors.pop(code, None)
            except Exception as error:
                errors[code] = str(error)
    if errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(errors.items()))
        raise RuntimeError(f"ComicsBox filtered team scan failed after retries: {details}")
    return result, errors


def dedicated_chapters(path: dict[str, Any], loaded: dict[str, dict[str, Any]], filtered_roles: dict[str, list[str]], source_errors: dict[str, str]):
    chapters: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for source_index, raw_source in enumerate(path.get("sources", [])):
        source = street.source_spec(raw_source)
        code = source["code"]
        series = loaded.get(code)
        rows = [] if not series else [
            row for row in series.get("rows", [])
            if legacy.included(row.get("number", ""), source.get("include"))
        ]
        selected = []
        for row in rows:
            if source.get("protagonistOnly") and path["id"] not in filtered_roles.get(row["code"], []):
                continue
            selected.append(row)
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
                "origin": "dedicated-series" if not source.get("protagonistOnly") else "filtered-team-series",
            })
        summaries.append({
            "code": code,
            "name": series.get("name", code) if series else code,
            "selectors": source.get("include", ["all"]),
            "protagonistOnly": bool(source.get("protagonistOnly")),
            "candidateChapters": len(rows),
            "chapters": len(selected),
            "mapped": sum(bool(row.get("italianCode")) for row in selected),
            "unmapped": sum(not bool(row.get("italianCode")) for row in selected),
            **({"error": source_errors[code]} if code in source_errors else {}),
        })
    return chapters, summaries


def ensure_group(groups: list[dict[str, Any]], group_id: str, label: str) -> dict[str, Any]:
    group = next((item for item in groups if item.get("id") == group_id), None)
    if group is None:
        group = {"id": group_id, "label": label, "paths": []}
        groups.append(group)
    return group


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {spec["id"] for spec in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "daredevil": ["elektra"],
        "punisher": ["elektra", "deadpool"],
        "wolverine-616": ["elektra", "deadpool", "cable"],
        "spiderman": ["deadpool"],
        "xmen": ["deadpool", "cable", "magik"],
        "doctor-strange": ["magik"],
        "scarletwitch": ["magik"],
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
    by_id = {hub["id"]: hub for hub in payload.get("hubs", [])}

    street_hub = by_id.get("street")
    if street_hub:
        groups = street_hub.setdefault("groups", [])
        core = ensure_group(groups, "core", "Hell's Kitchen")
        if "elektra" not in core["paths"]:
            core["paths"].append("elektra")
        vigilantes = ensure_group(groups, "vigilantes", "Vigilanti urbani")
        if "deadpool" not in vigilantes["paths"]:
            vigilantes["paths"].append("deadpool")

    xmen = by_id.get("xmen")
    if xmen:
        groups = xmen.setdefault("groups", [])
        solo = ensure_group(groups, "solo", "Percorsi personali")
        for path_id in ["cable", "magik"]:
            if path_id not in solo["paths"]:
                solo["paths"].append(path_id)
        crossroads = ensure_group(groups, "crossroads", "Mutanti tra più mondi")
        if "deadpool" not in crossroads["paths"]:
            crossroads["paths"].append("deadpool")

    mystic = by_id.get("mystic")
    if mystic:
        core = ensure_group(mystic.setdefault("groups", []), "core", "Magia e realtà occulta")
        if "magik" not in core["paths"]:
            core["paths"].append("magik")

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

    # Keep source-index traffic conservative: ComicsBox throttles large bursts.
    source_workers = min(workers, 8)
    loaded, source_errors = street.load_config_sources(config, source_workers)
    retry_delays = (5, 15, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not source_errors:
            break
        failed_codes = ", ".join(sorted(source_errors))
        log(f"Retry sorgenti ComicsBox {retry}/{len(retry_delays)} tra {delay}s: {failed_codes}")
        __import__("time").sleep(delay)
        for code in list(source_errors):
            try:
                loaded[code] = legacy.load_foreign_series(code)
                source_errors.pop(code, None)
            except Exception as error:
                source_errors[code] = str(error)
    if source_errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(source_errors.items()))
        raise RuntimeError(f"ComicsBox source load failed after retries: {details}")
    log(f"Sorgenti ComicsBox complete: {len(loaded)}/77")
    filtered_roles, filtered_role_errors = filtered_source_roles(config, loaded, min(workers, 16))

    per_base, _ = wave1.load_reuse_issues(config, manifest_before)
    reuse_contents, reuse_metadata, reuse_album_errors = wave1.enrich_reuse_contents(per_base, workers)
    role_map, role_errors = wave1.scan_content_roles(reuse_contents, config, workers)
    aliases_by_path = {path["id"]: path["aliases"] for path in config["paths"]}
    retry_delays = (3, 10, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not role_errors:
            break
        failed_codes = sorted(role_errors)
        log(
            f"Retry storie condivise {retry}/{len(retry_delays)} tra {delay}s: "
            + ", ".join(failed_codes)
        )
        __import__("time").sleep(delay)
        for code in failed_codes:
            try:
                source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{code}")
                date_label, date_key = wave1.source_date(source)
                protagonists = [
                    path_id
                    for path_id, aliases in aliases_by_path.items()
                    if wave1.credited_as_protagonist(source, aliases)
                ]
                role_map[code] = {
                    "protagonistPaths": protagonists,
                    "date": date_label,
                    "dateKey": list(date_key),
                }
                role_errors.pop(code, None)
            except Exception as error:
                role_errors[code] = str(error)
    if role_errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(role_errors.items()))
        raise RuntimeError(f"ComicsBox shared story scan failed after retries: {details}")

    chapters_by_path: dict[str, list[dict[str, Any]]] = {}
    audits: list[dict[str, Any]] = []
    for spec in config["paths"]:
        dedicated, source_summary = dedicated_chapters(spec, loaded, filtered_roles, source_errors)
        shared, shared_stats = wave1.shared_chapters(spec, per_base, reuse_contents, role_map)
        chapters = wave1.dedupe_chapters(dedicated + shared)
        chapters_by_path[spec["id"]] = chapters
        audits.append({
            "id": spec["id"], "name": spec["name"],
            "dedicatedAndFilteredChapters": len(dedicated),
            "sharedProtagonistChapters": len(shared),
            "deduplicatedChapters": len(chapters),
            "sourceSeries": source_summary,
            "sharedScan": shared_stats,
        })
        log(f"{spec['name']}: {len(dedicated)} dedicati/filtrati + {len(shared)} condivisi = {len(chapters)} capitoli")

    physical, contents_by_album, content_status, album_errors = wave1.prepare_physical_maps(
        chapters_by_path, reuse_metadata, reuse_contents, workers
    )

    characters: dict[str, dict[str, Any]] = {}
    audit_by_id = {row["id"]: row for row in audits}
    for spec in config["paths"]:
        character, path_audit = five.build_character(
            spec, chapters_by_path[spec["id"]], physical, contents_by_album, content_status
        )
        character["readingOrderSource"] = "ComicsBox serie dedicate + team filtrati per protagonisti + riuso protagonista-only MarvelTracker"
        character["sharedHistoryPolicy"] = "protagonists-only; simple appearances excluded except explicitly selected historical anchors"
        if spec["id"] == "deadpool":
            character["continuityPolicy"] = "Earth-616 focused; MAX, Kills-universe, Pulp, What If and explicit alternates excluded"
        elif spec["id"] == "elektra":
            character["continuityPolicy"] = "Mainline focused; Ultimate and explicit cross-company continuities excluded"
        elif spec["id"] == "magik":
            character["classification"] = "mutant-mystic hybrid"
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
            "candidateDedicatedSeries": len({street.source_spec(value)["code"] for spec in config["paths"] for value in spec.get("sources", [])}),
            "validDedicatedSeries": len(loaded),
            "sourceErrors": len(source_errors),
            "filteredTeamStoriesScanned": len(filtered_roles) + len(filtered_role_errors),
            "filteredTeamStoryErrors": len(filtered_role_errors),
            "sharedUsStoriesScanned": len(role_map),
            "sharedUsStoryErrors": len(role_errors),
            "uniqueItalianAlbums": len(all_albums),
            "reusedExistingAlbums": len(all_albums & set(existing_by_album)),
            "newItalianAlbums": len(all_albums - set(existing_by_album)),
        },
        "sourceErrors": source_errors,
        "filteredTeamRoleErrors": filtered_role_errors,
        "reuseAlbumErrors": reuse_album_errors,
        "roleScanErrors": role_errors,
        "albumErrors": album_errors,
        "paths": audits,
    }
    write_json(AUDIT_PATH, audit_payload, pretty=True)
    log(f"Audit scritto: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
