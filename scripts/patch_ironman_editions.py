#!/usr/bin/env python3
"""Build exact Iron Man alternative-edition coverage from story features."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

import build_cosmic_supernatural_expansion as legacy
import build_editions_catalog as edcat
import refine_ironman_story_features as iron

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TARGET_SERIES: dict[str, dict[str, str]] = {
    "MMW_M": {"name": "Marvel Masterworks", "publisher": "Marvel Italia / Panini Comics", "format": "Cartonato"},
    "SUPEROICLA": {"name": "Super Eroi Classic", "publisher": "RCS Quotidiani", "format": "Brossurato"},
    "MCOLL_M": {"name": "Marvel Collection (I)", "publisher": "Panini Comics", "format": "Brossurato"},
    "MARVELREP": {"name": "Marvel Replica Edition", "publisher": "Panini Comics", "format": "Spillato"},
    "MAR_GOLD": {"name": "Marvel Gold", "publisher": "Panini Comics", "format": "Brossurato"},
    "MARVGEEKS": {"name": "Marvel Geeks", "publisher": "Panini Comics", "format": "Cartonato"},
    "MAREPCOLL": {"name": "Marvel Epic Collection", "publisher": "Panini Comics", "format": "Brossurato"},
    "MARHIST_P": {"name": "Marvel History", "publisher": "Panini Comics", "format": "Cartonato"},
    "MARVELLC": {"name": "Marvel Legendary Collection", "publisher": "Panini Comics", "format": "Cartonato"},
    "MARVELMUST": {"name": "Marvel Must-Have", "publisher": "Panini Comics", "format": "Cartonato"},
    "SUPER_LG": {"name": "Supereroi: Le Leggende Marvel", "publisher": "RCS Quotidiani", "format": "Brossurato"},
    "MAROMNIB": {"name": "Marvel Omnibus", "publisher": "Panini Comics", "format": "Omnibus cartonato"},
    "MARVELANT2": {"name": "Marvel Anthology (II)", "publisher": "Panini Comics", "format": "Cartonato"},
    "MVNWCOL_P": {"name": "Marvel Collection (II)", "publisher": "Panini Comics", "format": "Cartonato"},
}


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def looks_like_ironman(title: str, series_name: str = "") -> bool:
    text = iron.norm(f"{series_name} {title}")
    return any(marker in text for marker in (
        "iron man", "ironman", "tony stark",
        "guerra delle armature", "demone nella bottiglia", "demonio nella bottiglia",
    ))


def edition_from_row(meta: dict[str, str], row: dict[str, str]) -> dict[str, Any]:
    code = row["code"]
    return {
        "id": edcat.edition_id(code),
        "name": row.get("title") or row.get("label") or f"{meta['name']} #{row.get('number', '')}",
        "series": meta["name"],
        "number": row.get("number", ""),
        "publisher": meta["publisher"],
        "format": meta["format"],
        "date": row.get("date", ""),
        "cover": edcat.cover_url(code),
        "url": f"https://www.comicsbox.it/albo/{code}",
        "contents": [],
        "coverage": [],
        "source": "ComicsBox",
        "sourceCode": code,
    }


def discover(existing: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for eid, item in existing.items():
        if item.get("sourceCode") and looks_like_ironman(item.get("name", ""), item.get("series", "")):
            candidates[eid] = deepcopy(item)

    for series_code, meta in TARGET_SERIES.items():
        matched = 0
        for row in edcat.load_series(series_code):
            if not looks_like_ironman(row.get("title", ""), row.get("label", "")):
                continue
            fresh = edition_from_row(meta, row)
            previous = existing.get(fresh["id"], {})
            candidates[fresh["id"]] = {**fresh, **previous, "sourceCode": fresh["sourceCode"], "source": "ComicsBox"}
            matched += 1
        log(f"{meta['name']}: {matched} candidate")
    return candidates


def parse_candidates(candidates: dict[str, dict[str, Any]], workers: int) -> tuple[dict[str, list[dict[str, str]]], dict[str, str]]:
    parsed: dict[str, list[dict[str, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(iron.album_features, item["sourceCode"]): eid
            for eid, item in candidates.items() if item.get("sourceCode")
        }
        for index, future in enumerate(as_completed(futures), 1):
            eid = futures[future]
            try:
                parsed[eid] = future.result()
            except Exception as error:
                errors[eid] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Alternative analizzate: {index}/{len(futures)}")
    return parsed, errors


def requirements(character: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str]]:
    required: dict[str, set[str]] = {}
    primary: dict[str, str] = {}
    for issue in character.get("issues", []):
        step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
        if step.get("pathId") != iron.PATH_ID:
            continue
        ids = {str(cid) for cid in step.get("contentIds", []) if cid}
        if not ids:
            continue
        required[issue["id"]] = ids
        primary[issue["id"]] = legacy.album_code(issue.get("url"))
    return required, primary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(argv)
    workers = max(1, args.workers)

    character = read_json(DATA / "characters" / "ironman.json")
    required_by_issue, primary_by_issue = requirements(character)
    editions_path = DATA / "editions.json"
    payload = read_json(editions_path)
    existing = {item["id"]: deepcopy(item) for item in payload.get("editions", [])}

    for item in existing.values():
        item["coverage"] = [row for row in item.get("coverage", []) if row.get("path") != iron.PATH_ID]
        item.pop("ironManCoverage", None)

    candidates = discover(existing)
    parsed, errors = parse_candidates(candidates, workers)
    if errors:
        raise RuntimeError("Alternative Iron Man non risolte: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    route_ids = set().union(*required_by_issue.values()) if required_by_issue else set()
    complete_links = 0
    partial_links = 0
    relevant = 0
    story_blocks = 0

    for eid, candidate in candidates.items():
        features = parsed.get(eid, [])
        provided: set[str] = set()
        labels: list[str] = []
        for feature in features:
            provided.add(feature["sourceCode"])
            provided.add(feature["storyId"])
            if feature["sourceCode"].startswith(iron.CLASSIC_PREFIX):
                labels.append(iron.source_label(feature["sourceCode"], feature["title"]))
            else:
                labels.append(f"{feature['sourceCode']} — {feature['title']}")
        if not (provided & route_ids):
            continue
        relevant += 1
        story_blocks += len(features)
        candidate["contents"] = labels
        candidate["contentIds"] = sorted(provided)
        rows: list[dict[str, Any]] = []
        for issue_id, required_ids in required_by_issue.items():
            overlap = sorted(required_ids & provided)
            if not overlap or primary_by_issue.get(issue_id) == candidate.get("sourceCode"):
                continue
            complete = required_ids.issubset(provided)
            rows.append({
                "path": iron.PATH_ID,
                "issueIds": [issue_id],
                "label": candidate.get("name", eid),
                "contentIds": overlap,
                "requiredContentIds": sorted(required_ids),
                "complete": complete,
                "coverageLabel": "Completa" if complete else f"Parziale {len(overlap)}/{len(required_ids)}",
                "coverageModel": iron.STORY_MODEL,
            })
            complete_links += int(complete)
            partial_links += int(not complete)
        if rows:
            candidate["coverage"] = [row for row in candidate.get("coverage", []) if row.get("path") != iron.PATH_ID] + rows
            candidate["ironManCoverage"] = {
                "model": iron.STORY_MODEL,
                "storyBlocks": len(features),
                "fullStepLinks": sum(1 for row in rows if row["complete"]),
                "partialStepLinks": sum(1 for row in rows if not row["complete"]),
            }
        existing[eid] = candidate

    editions = list(existing.values())
    editions.sort(key=lambda item: (iron.norm(item.get("series", "")), edcat.natural_number(item.get("number")), iron.norm(item.get("name", ""))))
    payload["version"] = max(int(payload.get("version", 2)), 5)
    payload["coverageModel"] = "issue-links + exact-story-feature coverage"
    payload["total"] = len(editions)
    payload["editions"] = editions
    write_json(editions_path, payload)

    audit = {
        "version": 1,
        "path": iron.PATH_ID,
        "coverageModel": iron.STORY_MODEL,
        "candidateEditions": len(candidates),
        "editionsWithRelevantContents": relevant,
        "exactIronManStoryBlocks": story_blocks,
        "completeStepLinks": complete_links,
        "partialStepLinks": partial_links,
        "auditedSeries": sorted(TARGET_SERIES),
        "rule": (
            "An alternative is linked only from actual Iron Man story blocks. "
            "A route step is complete only when the union of owned editions covers every required content ID."
        ),
    }
    write_json(DATA / "ironman-alternatives-audit.json", audit, pretty=True)
    log(f"Iron Man alternatives: {relevant} relevant · {complete_links} complete · {partial_links} partial")


if __name__ == "__main__":
    main()
