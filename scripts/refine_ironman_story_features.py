#!/usr/bin/env python3
"""Refine the audited classic Iron Man route to exact story-feature IDs."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

import build_cosmic_supernatural_expansion as legacy
import build_five_character_expansion as five
import refine_doctor_strange_story_features as feature_base
import refine_doctor_strange_story_features_v2 as feature_v2

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "ironman"
CLASSIC_PREFIX = "IM1_"
STORY_PREFIX = "ironman-story:"
STORY_MODEL = "comicsbox-story-feature@2"


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def norm(value: str) -> str:
    return feature_base.norm(value)


def is_ironman_feature(lines: list[str]) -> bool:
    aliases = ("iron man", "ironman", "tony stark")
    for line in reversed(lines):
        lowered = norm(line)
        if lowered.startswith("protagonisti ") or lowered.startswith("protagonista "):
            return any(alias in lowered for alias in aliases)
    for line in lines[-20:]:
        lowered = norm(line)
        if lowered in {"iron man", "ironman"} or lowered.startswith("iron man and "):
            return True
    return False


def parse_ironman_features(source: str) -> list[dict[str, str]]:
    matches = list(feature_base.DA_PATTERN.finditer(source))
    features: list[dict[str, str]] = []
    previous_end = 0
    seen: set[tuple[str, str]] = set()
    for match in matches:
        href = five.attr_value(match.group(1), "href")
        source_code = legacy.album_code(href)
        fragment = source[previous_end:match.start()]
        previous_end = match.end()
        if not source_code:
            continue
        lines = feature_base.strip_lines(fragment)
        if not is_ironman_feature(lines):
            continue
        title = feature_base.feature_title(lines)
        if not title:
            raise RuntimeError(f"{source_code}: feature Iron Man trovata ma titolo non risolto")
        fingerprint, _ = feature_v2.story_fingerprint(lines)
        stable_id = f"{STORY_PREFIX}{source_code}:{fingerprint}"
        key = (source_code, stable_id)
        if key in seen:
            continue
        seen.add(key)
        features.append({
            "sourceCode": source_code,
            "title": title,
            "storyId": stable_id,
            "storyFingerprint": fingerprint,
        })
    return features


def album_features(album_code: str) -> list[dict[str, str]]:
    return parse_ironman_features(legacy.fetch_text(f"https://www.comicsbox.it/albo/{album_code}"))


def source_label(source_code: str, title: str) -> str:
    number = source_code.rsplit("_", 1)[-1].lstrip("0") or "0"
    return f"Iron Man (1968) #{number} — {title}"


def is_classic_raw(issue: dict[str, Any]) -> bool:
    return any(str(cid).startswith(CLASSIC_PREFIX) for cid in issue.get("readingStep", {}).get("contentIds", []))


def transform_issue(issue: dict[str, Any], features: list[dict[str, str]]) -> list[dict[str, str]]:
    by_source: dict[str, list[dict[str, str]]] = {}
    for feature in features:
        by_source.setdefault(feature["sourceCode"], []).append(feature)

    step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
    raw_ids = [str(cid) for cid in step.get("contentIds", [])]
    selected: list[dict[str, str]] = []
    for raw_id in raw_ids:
        if not raw_id.startswith(CLASSIC_PREFIX):
            continue
        matches = by_source.get(raw_id, [])
        if not matches:
            raise RuntimeError(f"{issue.get('id')}: {raw_id} non espone una feature Iron Man nella pubblicazione primaria")
        selected.extend(matches)

    story_ids = list(dict.fromkeys(row["storyId"] for row in selected))
    if not story_ids:
        return []

    raw_set = {cid for cid in raw_ids if cid.startswith(CLASSIC_PREFIX)}
    step["contentIds"] = story_ids + [cid for cid in raw_ids if cid not in raw_set]
    step["scope"] = "ironman-story-features"
    issue["readingStep"] = step

    contents = [deepcopy(row) for row in issue.get("contents", []) if row.get("id") not in raw_set]
    for feature in selected:
        source_code = feature["sourceCode"]
        raw = next((row for row in issue.get("contents", []) if row.get("id") == source_code), {})
        content = deepcopy(raw)
        content.update({
            "id": feature["storyId"],
            "sourceIssueId": source_code,
            "seriesId": "IM1",
            "series": "Iron Man Vol 1",
            "number": source_code.rsplit("_", 1)[-1].lstrip("0") or "0",
            "feature": "Iron Man",
            "storyTitle": feature["title"],
            "title": source_label(source_code, feature["title"]),
            "scope": "story-feature",
            "url": f"https://www.comicsbox.it/albo/{source_code}",
        })
        contents.append(content)
    issue["contents"] = five.merge_contents(contents)
    labels = [source_label(row["sourceCode"], row["title"]) for row in selected]
    issue["usaChapters"] = labels
    issue["title"] = five.concise(labels, 2)
    issue["instruction"] = "Leggi in questo albo: " + five.concise(labels, 3)
    issue.pop("storyRows", None)
    return selected


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args(argv)
    workers = max(1, args.workers)

    character_path = DATA / "characters" / "ironman.json"
    audit_path = DATA / "ironman-audit.json"
    character = read_json(character_path)
    audit = read_json(audit_path)
    classic = [issue for issue in character.get("issues", []) if is_classic_raw(issue)]
    if not classic:
        raise RuntimeError("Iron Man: nessuna tappa classica grezza")

    album_codes = {legacy.album_code(issue.get("url")) for issue in classic}
    album_codes.discard("")
    parsed: dict[str, list[dict[str, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(album_features, code): code for code in sorted(album_codes)}
        for index, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                parsed[code] = future.result()
            except Exception as error:
                errors[code] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Feature primarie Iron Man: {index}/{len(futures)}")
    if errors:
        raise RuntimeError("Feature primarie non risolte: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    story_ids: set[str] = set()
    source_album_features: dict[tuple[str, str], list[str]] = {}
    for issue in classic:
        album_code = legacy.album_code(issue.get("url"))
        selected = transform_issue(issue, parsed.get(album_code, []))
        for feature in selected:
            story_ids.add(feature["storyId"])
            source_album_features.setdefault((feature["sourceCode"], album_code), []).append(feature["storyId"])

    for mapping in audit.get("mappings", []):
        key = (mapping.get("usaCode"), mapping.get("italianAlbum"))
        ids = source_album_features.get(key, [])
        if ids:
            mapping["storyIdsInPhysical"] = list(dict.fromkeys(ids))

    character["storyIdentityModel"] = STORY_MODEL
    character["coverage"]["classicStoryFeatureIds"] = len(story_ids)
    character["coverage"]["classicPhysicalItalianIssues"] = len(classic)
    write_json(character_path, character)

    audit["storyIdentityModel"] = STORY_MODEL
    audit["classic"]["storyFeatureIds"] = len(story_ids)
    audit.setdefault("guardrails", {})["storyFeatureIdentity"] = (
        "Classic Iron Man coverage uses source-USA-issue plus a title-independent ComicsBox story fingerprint. "
        "Retitled reprints match; separate backups/features from the same USA issue remain distinct."
    )
    write_json(audit_path, audit, pretty=True)
    log(f"Iron Man route refined: {len(story_ids)} exact story features · {len(classic)} physical steps")


if __name__ == "__main__":
    main()
