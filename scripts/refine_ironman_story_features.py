#!/usr/bin/env python3
"""Refine audited classic Iron Man to exact story-feature IDs.

The route keeps the physical Italian publication as the ownership key, while
path-local reading steps may segment one collected volume when another physical
publication interrupts its internal USA-story chronology. This is required for
Iron Man (1968) #178: its two features have different first official Italian
publications.
"""
from __future__ import annotations

import argparse
import json
import re
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
CLASSIC_END = 306
STORY_PREFIX = "ironman-story:"
STORY_MODEL = "comicsbox-story-feature@2"

# A source issue can contain multiple story features whose first official
# Italian publications differ.  The normal ComicsBox series table exposes only
# one primary anchor reliably in these cases, so the missing feature is resolved
# from the actual later physical page and inserted at the exact narrative point.
SPLIT_PRIMARY_FEATURES = {
    "IM1_178": ["SUPEROICLA_475"],
}


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def norm(value: str) -> str:
    return feature_base.norm(value)


def source_number(source_code: str) -> int | None:
    match = re.fullmatch(r"IM1_(\d+)", str(source_code or ""))
    return int(match.group(1)) if match else None


def is_classic_source(source_code: str) -> bool:
    number = source_number(source_code)
    return number is not None and 1 <= number <= CLASSIC_END


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
    return any(
        is_classic_source(str(cid))
        for cid in issue.get("readingStep", {}).get("contentIds", [])
    )


def story_content(feature: dict[str, str], raw: dict[str, Any] | None = None) -> dict[str, Any]:
    source_code = feature["sourceCode"]
    content = deepcopy(raw or {})
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
    return content


def refresh_issue_copy(issue: dict[str, Any]) -> None:
    selected_ids = list(issue.get("readingStep", {}).get("contentIds", []))
    by_id = {row.get("id"): row for row in issue.get("contents", []) if row.get("id")}
    labels = [by_id[cid].get("title", cid) for cid in selected_ids if cid in by_id]
    if labels:
        issue["usaChapters"] = labels
        issue["title"] = five.concise(labels, 2)
        issue["instruction"] = "Leggi in questo albo: " + five.concise(labels, 3)


def transform_issue(issue: dict[str, Any], features: list[dict[str, str]]) -> list[dict[str, str]]:
    by_source: dict[str, list[dict[str, str]]] = {}
    for feature in features:
        by_source.setdefault(feature["sourceCode"], []).append(feature)

    step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
    raw_ids = [str(cid) for cid in step.get("contentIds", [])]
    selected: list[dict[str, str]] = []
    for raw_id in raw_ids:
        if not is_classic_source(raw_id):
            continue
        matches = by_source.get(raw_id, [])
        if not matches:
            raise RuntimeError(f"{issue.get('id')}: {raw_id} non espone una feature Iron Man nella pubblicazione primaria")
        selected.extend(matches)

    story_ids = list(dict.fromkeys(row["storyId"] for row in selected))
    if not story_ids:
        return []

    raw_set = {cid for cid in raw_ids if is_classic_source(cid)}
    step["contentIds"] = story_ids + [cid for cid in raw_ids if cid not in raw_set]
    step["scope"] = "ironman-story-features"
    issue["readingStep"] = step

    contents = [deepcopy(row) for row in issue.get("contents", []) if row.get("id") not in raw_set]
    for feature in selected:
        raw = next((row for row in issue.get("contents", []) if row.get("id") == feature["sourceCode"]), {})
        contents.append(story_content(feature, raw))
    issue["contents"] = five.merge_contents(contents)
    refresh_issue_copy(issue)
    issue.pop("storyRows", None)
    return selected


def physical_for_album(album_code: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metadata = five.load_italian_album(album_code)
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    physical = legacy.assign_physical_ids({album_code: metadata}, existing_by_album, existing_id_to_album)[album_code]
    return physical, deepcopy(metadata.get("contents", []))


def exact_contents(raw_contents: list[dict[str, Any]], features: list[dict[str, str]]) -> list[dict[str, Any]]:
    source_codes = {feature["sourceCode"] for feature in features}
    result = [deepcopy(row) for row in raw_contents if row.get("id") not in source_codes]
    for feature in features:
        raw = next((row for row in raw_contents if row.get("id") == feature["sourceCode"]), {})
        result.append(story_content(feature, raw))
    return five.merge_contents(result)


def selected_source(issue: dict[str, Any], content_id: str) -> str:
    row = next((item for item in issue.get("contents", []) if item.get("id") == content_id), None)
    return str(row.get("sourceIssueId") or row.get("id") or "") if row else ""


def make_segment(issue: dict[str, Any], content_ids: list[str], suffix: str, *, keep_id: bool) -> dict[str, Any]:
    segment = deepcopy(issue)
    physical_id = issue.get("physicalId") or issue["id"]
    segment["physicalId"] = physical_id
    if not keep_id:
        segment["id"] = f"{physical_id}@ironman-{suffix}"
    segment["readingStep"] = deepcopy(issue.get("readingStep", {}))
    segment["readingStep"]["contentIds"] = list(content_ids)
    segment["readingStep"]["scope"] = "ironman-story-features"
    refresh_issue_copy(segment)
    return segment


def make_split_publication_issue(
    album_code: str,
    selected_features: list[dict[str, str]],
    era: str,
    era_sub: str,
) -> dict[str, Any]:
    physical, raw_contents = physical_for_album(album_code)
    all_features = album_features(album_code)
    contents = exact_contents(raw_contents, all_features)
    labels = [source_label(feature["sourceCode"], feature["title"]) for feature in selected_features]
    issue = deepcopy(physical)
    issue.update({
        "id": physical["id"],
        "physicalId": physical["id"],
        "required": True,
        "skip": False,
        "future": bool(physical.get("future", False)),
        "era": era,
        "eraSub": era_sub,
        "title": five.concise(labels, 2),
        "instruction": "Leggi in questo albo: " + five.concise(labels, 3),
        "usaChapters": labels,
        "sourceSeries": ["IM1"],
        "contents": contents,
        "contentsStatus": "complete",
        "readingStep": {
            "pathId": PATH_ID,
            "position": 0,
            "contentIds": [feature["storyId"] for feature in selected_features],
            "scope": "ironman-story-features",
        },
    })
    return issue


def insert_split_primary_features(
    character: dict[str, Any],
    audit: dict[str, Any],
) -> list[dict[str, Any]]:
    inserted: list[dict[str, Any]] = []
    for source_code, album_codes in SPLIT_PRIMARY_FEATURES.items():
        selected_rows: list[tuple[int, dict[str, Any], str]] = []
        for issue_index, issue in enumerate(character.get("issues", [])):
            for content_id in issue.get("readingStep", {}).get("contentIds", []):
                if selected_source(issue, str(content_id)) == source_code:
                    selected_rows.append((issue_index, issue, str(content_id)))
        if not selected_rows:
            raise RuntimeError(f"{source_code}: feature primaria non trovata nel percorso")

        primary_index = selected_rows[0][0]
        primary_issue = character["issues"][primary_index]
        existing_story_ids = {
            content_id for _index, _issue, content_id in selected_rows
            if str(content_id).startswith(STORY_PREFIX)
        }

        candidates: list[tuple[str, dict[str, str]]] = []
        for album_code in album_codes:
            for feature in album_features(album_code):
                if feature["sourceCode"] == source_code and feature["storyId"] not in existing_story_ids:
                    candidates.append((album_code, feature))
        if not candidates:
            raise RuntimeError(f"{source_code}: nessuna feature supplementare trovata nelle pubblicazioni split")

        # Split the original physical reading step exactly after the already
        # selected source feature.  If the same collected volume continues with
        # #179+ afterwards, it reappears as a second path-local segment sharing
        # the same physicalId, so ownership is still counted only once.
        original_ids = list(primary_issue.get("readingStep", {}).get("contentIds", []))
        source_positions = [
            index for index, content_id in enumerate(original_ids)
            if selected_source(primary_issue, str(content_id)) == source_code
        ]
        if not source_positions:
            raise RuntimeError(f"{source_code}: posizione narrativa non risolta nella pubblicazione primaria")
        cut = max(source_positions) + 1
        before_ids = original_ids[:cut]
        after_ids = original_ids[cut:]
        first_segment = make_segment(primary_issue, before_ids, f"through-{source_code.lower()}", keep_id=True)
        first_segment["eraSub"] = primary_issue.get("eraSub", "")

        split_issues: list[dict[str, Any]] = []
        for album_code in album_codes:
            features = [feature for code, feature in candidates if code == album_code]
            if not features:
                continue
            split_issue = make_split_publication_issue(
                album_code,
                features,
                primary_issue.get("era", "Iron Man classico"),
                f"Story-feature di {source_code} con prima pubblicazione italiana distinta.",
            )
            split_issues.append(split_issue)
            physical_id = split_issue["physicalId"]
            base_date = next((row.get("usaDate") for row in audit.get("mappings", []) if row.get("usaCode") == source_code), "")
            existing_ordinals = [int(row.get("storyOrdinal") or 0) for row in audit.get("mappings", []) if row.get("usaCode") == source_code]
            ordinal = max(existing_ordinals or [0])
            for feature in features:
                ordinal += 1
                audit.setdefault("mappings", []).append({
                    "sourceCode": "IM1",
                    "usaCode": source_code,
                    "usaNumber": str(source_number(source_code) or ""),
                    "usaTitle": feature["title"],
                    "usa": source_label(source_code, feature["title"]),
                    "usaDate": base_date,
                    "storyOrdinal": ordinal,
                    "italianAlbum": album_code,
                    "italianLabel": split_issue.get("name"),
                    "physicalId": physical_id,
                    "storyIdsInPhysical": [feature["storyId"]],
                    "splitPrimary": True,
                })
                inserted.append(feature)

        replacement = [first_segment, *split_issues]
        if after_ids:
            replacement.append(
                make_segment(
                    primary_issue,
                    after_ids,
                    f"after-{source_code.lower()}",
                    keep_id=False,
                )
            )
        character["issues"][primary_index:primary_index + 1] = replacement

    return inserted


def update_manifest(character: dict[str, Any]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    item = next((row for row in manifest.get("characters", []) if row.get("id") == PATH_ID), None)
    if not item:
        raise RuntimeError("ironman assente dal manifest")
    item["start"] = character["start"]
    item["end"] = character["end"]
    item["totalRequired"] = character["totalRequired"]
    item["auditStatus"] = "audited"
    item["auditKind"] = "path/character"
    item["auditDate"] = "2026-08-16"
    write_json(path, manifest)


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

    source_album_features: dict[tuple[str, str], list[str]] = {}
    for issue in classic:
        album_code = legacy.album_code(issue.get("url"))
        selected = transform_issue(issue, parsed.get(album_code, []))
        for feature in selected:
            source_album_features.setdefault((feature["sourceCode"], album_code), []).append(feature["storyId"])

    for mapping in audit.get("mappings", []):
        key = (mapping.get("usaCode"), mapping.get("italianAlbum"))
        ids = source_album_features.get(key, [])
        if ids:
            mapping["storyIdsInPhysical"] = list(dict.fromkeys(ids))

    inserted = insert_split_primary_features(character, audit)

    for position, issue in enumerate(character.get("issues", []), 1):
        issue["seq"] = position
        if isinstance(issue.get("readingStep"), dict):
            issue["readingStep"]["position"] = position

    classic_story_ids: set[str] = set()
    classic_physical_ids: set[str] = set()
    classic_steps = 0
    for issue in character.get("issues", []):
        ids = issue.get("readingStep", {}).get("contentIds", [])
        exact_classic = [
            str(cid) for cid in ids
            if str(cid).startswith(STORY_PREFIX)
            and is_classic_source(selected_source(issue, str(cid)))
        ]
        if not exact_classic:
            continue
        classic_steps += 1
        classic_story_ids.update(exact_classic)
        classic_physical_ids.add(str(issue.get("physicalId") or issue.get("id")))

    current_gap_rows = [row for row in audit.get("mappings", []) if not row.get("physicalId")]
    required = sum(1 for issue in character["issues"] if issue.get("required") is not False and not issue.get("future"))
    character["totalRequired"] = required
    character["availableTotal"] = required
    character["storyIdentityModel"] = STORY_MODEL
    character.setdefault("coverage", {})["classicStoryFeatureIds"] = len(classic_story_ids)
    character["coverage"]["classicMappedStoryFeatures"] = len(classic_story_ids)
    character["coverage"]["missingItalianStories"] = len(current_gap_rows)
    character["coverage"]["classicPhysicalItalianIssues"] = len(classic_physical_ids)
    character["coverage"]["classicReadingSteps"] = classic_steps
    character["coverage"]["splitPrimaryStoryFeatures"] = len(inserted)
    write_json(character_path, character)
    update_manifest(character)

    audit["storyIdentityModel"] = STORY_MODEL
    audit.setdefault("classic", {})["storyFeatureIds"] = len(classic_story_ids)
    audit["classic"]["mappedStoryFeatures"] = len(classic_story_ids)
    audit["classic"]["unmappedStories"] = len(current_gap_rows)
    audit["classic"]["stories"] = len(classic_story_ids) + len(current_gap_rows)
    audit["classic"]["physicalItalianIssues"] = len(classic_physical_ids)
    audit["classic"]["readingSteps"] = classic_steps
    audit.setdefault("guardrails", {})["storyFeatureIdentity"] = (
        "Classic Iron Man coverage uses source-USA-issue plus a title-independent ComicsBox story fingerprint. "
        "Retitled reprints match; separate backups/features from the same USA issue remain distinct."
    )
    audit["guardrails"]["splitPrimaryFeatures"] = (
        "Iron Man (1968) #178 contains two story features with different first official Italian publications. "
        "The route segments the surrounding collected volume path-locally and inserts Super Eroi Classic #475 "
        "for the missing feature while reusing physicalId for repeated segments of the same owned book."
    )
    write_json(audit_path, audit, pretty=True)
    log(
        f"Iron Man route refined: {len(classic_story_ids)} exact classic story features · "
        f"{len(classic_physical_ids)} physical books · {classic_steps} reading steps"
    )


if __name__ == "__main__":
    main()
