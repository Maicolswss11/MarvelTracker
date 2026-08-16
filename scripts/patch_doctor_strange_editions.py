#!/usr/bin/env python3
"""Audit Doctor Strange alternative editions by selected USA contents.

Unlike the legacy issue-level link, this pass records partial coverage and only lets the
UI consider a step satisfied when the union of owned alternatives covers every contentId
required by that Doctor Strange reading step.
"""
from __future__ import annotations

import argparse
import json
import os
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

import build_editions_catalog as edcat
import build_five_character_expansion as five
import build_cosmic_supernatural_expansion as legacy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "doctor-strange"

TARGET_SERIES = {
    "DSTRANGEORO": {"name": "Doctor Strange (Serie Oro)", "publisher": "Panini Comics", "format": "Brossurato", "dedicated": True},
    "MMW_M": {"name": "Marvel Masterworks", "publisher": "Panini Comics", "format": "Cartonato", "dedicated": False},
    "MAREPCOLL": {"name": "Marvel Epic Collection", "publisher": "Panini Comics", "format": "Raccolta", "dedicated": False},
    "MARHIST_P": {"name": "Marvel History", "publisher": "Panini Comics", "format": "Raccolta", "dedicated": False},
    "SUPEROICLA": {"name": "Super Eroi Classic", "publisher": "Panini Comics", "format": "Brossurato", "dedicated": False},
    "MARVELANT2": {"name": "Marvel Anthology (II)", "publisher": "Panini Comics", "format": "Cartonato", "dedicated": False},
    "MAROMNIB": {"name": "Marvel Omnibus", "publisher": "Panini Comics", "format": "Omnibus cartonato", "dedicated": False},
    "MARVELMUST": {"name": "Marvel Must-Have", "publisher": "Panini Comics", "format": "Cartonato", "dedicated": False},
    "MVNWCOL_P": {"name": "Marvel Collection II", "publisher": "Panini Comics", "format": "Cartonato", "dedicated": False},
    "100M": {"name": "100% Marvel", "publisher": "Marvel Italia / Panini Comics", "format": "Brossurato", "dedicated": False},
    "PSPP": {"name": "Play Special", "publisher": "Play Press", "format": "Brossurato", "dedicated": False},
}


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("’", "'")
    return " ".join(value.split())


def looks_like_strange(title: str, series_name: str = "") -> bool:
    text = norm(f"{series_name} {title}")
    return any(marker in text for marker in (
        "doctor strange", "dottor strange", "dr. strange", "dr strange",
        "stregone supremo", "sorcerer supreme",
    ))


def route_requirements(character: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str]]:
    required: dict[str, set[str]] = {}
    primary_album: dict[str, str] = {}
    for issue in character.get("issues", []):
        step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
        if step.get("pathId") != PATH_ID:
            continue
        ids = {str(code) for code in step.get("contentIds", []) if code}
        if not ids:
            raise RuntimeError(f"{issue.get('id')}: readingStep senza contentIds")
        required[issue["id"]] = ids
        primary_album[issue["id"]] = legacy.album_code(issue.get("url"))
    return required, primary_album


def edition_from_row(meta: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    source_code = row["code"]
    return {
        "id": edcat.edition_id(source_code),
        "name": row.get("title") or row.get("label") or f"{meta['name']} #{row.get('number', '')}",
        "series": meta["name"],
        "number": row.get("number", ""),
        "publisher": meta["publisher"],
        "format": meta["format"],
        "date": row.get("date", ""),
        "cover": edcat.cover_url(source_code),
        "url": f"https://www.comicsbox.it/albo/{source_code}",
        "contents": [],
        "coverage": [],
        "source": "ComicsBox",
        "sourceCode": source_code,
    }


def discover_candidates(existing: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for eid, item in existing.items():
        if item.get("sourceCode") and (str(item.get("sourceCode", "")).startswith("DSTRANGEORO_") or looks_like_strange(item.get("name", ""), item.get("series", ""))):
            candidates[eid] = deepcopy(item)

    for series_code, meta in TARGET_SERIES.items():
        rows = edcat.load_series(series_code)
        matched = 0
        for row in rows:
            if not meta.get("dedicated") and not looks_like_strange(row.get("title", ""), row.get("label", "")):
                continue
            item = edition_from_row(meta, row)
            eid = item["id"]
            previous = existing.get(eid, {})
            merged = {**item, **previous}
            merged["sourceCode"] = item["sourceCode"]
            merged["source"] = "ComicsBox"
            candidates[eid] = merged
            matched += 1
        log(f"{meta['name']}: {matched} candidate Doctor Strange")
    return candidates


def load_candidate_contents(candidates: dict[str, dict[str, Any]], workers: int) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    contents: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(five.load_italian_album, item["sourceCode"]): eid
            for eid, item in candidates.items() if item.get("sourceCode")
        }
        for index, future in enumerate(as_completed(futures), 1):
            eid = futures[future]
            try:
                contents[eid] = future.result()
            except Exception as error:
                errors[eid] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Alternative analizzate: {index}/{len(futures)}")
    return contents, errors


def display_content(content: dict[str, Any]) -> str:
    title = content.get("title") or ""
    if title:
        return title
    series = content.get("series") or content.get("seriesId") or "Marvel"
    number = content.get("number") or ""
    return f"{series} #{number}".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "12")))
    args = parser.parse_args()
    workers = max(1, args.workers)

    character = read_json(DATA / "characters" / "doctor-strange.json")
    required_by_issue, primary_by_issue = route_requirements(character)
    editions_path = DATA / "editions.json"
    payload = read_json(editions_path)
    existing = {item["id"]: deepcopy(item) for item in payload.get("editions", [])}

    # Remove old Doctor Strange issue-level guesses. They will be rebuilt below from content IDs.
    for item in existing.values():
        item["coverage"] = [row for row in item.get("coverage", []) if row.get("path") != PATH_ID]
        item.pop("doctorStrangeCoverage", None)

    candidates = discover_candidates(existing)
    album_data, errors = load_candidate_contents(candidates, workers)
    if errors:
        raise RuntimeError("Alternative Doctor Strange non leggibili: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    route_contents = set().union(*required_by_issue.values()) if required_by_issue else set()
    full_links = 0
    partial_links = 0
    candidates_with_overlap = 0
    for eid, candidate in candidates.items():
        album = album_data[eid]
        raw_contents = album.get("contents", [])
        content_ids = {content.get("id") for content in raw_contents if content.get("id")}
        relevant = content_ids & route_contents
        if not relevant:
            continue
        candidates_with_overlap += 1
        candidate["contents"] = [display_content(content) for content in raw_contents]
        candidate["contentIds"] = sorted(content_ids)
        candidate["coverage"] = [row for row in candidate.get("coverage", []) if row.get("path") != PATH_ID]
        rows = []
        source_code = candidate.get("sourceCode", "")
        for issue_id, required_ids in required_by_issue.items():
            overlap = sorted(required_ids & content_ids)
            if not overlap or primary_by_issue.get(issue_id) == source_code:
                continue
            complete = required_ids.issubset(content_ids)
            rows.append({
                "path": PATH_ID,
                "issueIds": [issue_id],
                "label": candidate.get("name", eid),
                "contentIds": overlap,
                "requiredContentIds": sorted(required_ids),
                "complete": complete,
                "coverageLabel": "Completa" if complete else f"Parziale {len(overlap)}/{len(required_ids)}",
            })
            full_links += int(complete)
            partial_links += int(not complete)
        if rows:
            candidate["coverage"].extend(rows)
            candidate["doctorStrangeCoverage"] = {
                "model": "content-union@1",
                "matchedContentIds": sorted(relevant),
                "fullStepLinks": sum(1 for row in rows if row["complete"]),
                "partialStepLinks": sum(1 for row in rows if not row["complete"]),
            }
        existing[eid] = candidate

    editions = list(existing.values())
    editions.sort(key=lambda item: (norm(item.get("series", "")), edcat.natural_number(item.get("number")), norm(item.get("name", ""))))
    payload["version"] = max(int(payload.get("version", 2)), 3)
    payload["coverageModel"] = "issue-links + doctor-strange/content-union@1"
    payload["total"] = len(editions)
    payload["editions"] = editions
    write_json(editions_path, payload)

    audit_path = DATA / "doctor-strange-alternatives-audit.json"
    audit = {
        "version": 1,
        "path": PATH_ID,
        "coverageModel": "content-union@1",
        "candidateEditions": len(candidates),
        "editionsWithRelevantContents": candidates_with_overlap,
        "completeStepLinks": full_links,
        "partialStepLinks": partial_links,
        "rule": "A route step is covered by alternatives only when the union of owned edition contentIds contains every requiredContentId for that step.",
        "fanTranslations": "excluded from official-edition coverage",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Doctor Strange alternatives: {candidates_with_overlap} edizioni · {full_links} link completi · {partial_links} link parziali")


if __name__ == "__main__":
    main()
