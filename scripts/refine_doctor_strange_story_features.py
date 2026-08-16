#!/usr/bin/env python3
"""Refine Doctor Strange from USA-issue identity to exact ComicsBox story-feature identity.

Doctor Strange is unusually sensitive to anthology/backup ambiguity:
- Strange Tales contains Human Torch/Nick Fury plus a Doctor Strange feature.
- Sorcerer Supreme can contain backups (for example Mordo stories) that may be
  reprinted independently from the main Doctor Strange story.

This pass gives each selected classic story a stable feature ID derived from the
source USA issue plus the ComicsBox story title, and rebuilds alternative-edition
coverage by parsing the actual Doctor Strange story blocks inside each Italian
edition.  Merely containing the same USA issue is therefore no longer sufficient.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

import build_cosmic_supernatural_expansion as legacy
import build_editions_catalog as edcat
import build_five_character_expansion as five

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "doctor-strange"
STORY_MODEL = "comicsbox-story-feature@1"
STORY_PREFIX = "doctor-strange-story:"

# Series not all present in the generic editions catalog, but known to contain
# Italian Doctor Strange collections/reprints worth auditing.
TARGET_SERIES: dict[str, dict[str, Any]] = {
    "DSTRANGEORO": {"name": "Doctor Strange (Serie Oro)", "publisher": "Panini Comics", "format": "Brossurato", "dedicated": True},
    "MMW_M": {"name": "Marvel Masterworks", "publisher": "Marvel Italia / Panini Comics", "format": "Cartonato"},
    "MAREPCOLL": {"name": "Marvel Epic Collection", "publisher": "Panini Comics", "format": "Raccolta"},
    "MARHIST_P": {"name": "Marvel History", "publisher": "Panini Comics", "format": "Cartonato"},
    "SUPEROICLA": {"name": "Super Eroi Classic", "publisher": "RCS Quotidiani", "format": "Brossurato"},
    "MARVELANT2": {"name": "Marvel Anthology (II)", "publisher": "Panini Comics", "format": "Cartonato"},
    "MAROMNIB": {"name": "Marvel Omnibus", "publisher": "Panini Comics", "format": "Omnibus cartonato"},
    "MARVELMUST": {"name": "Marvel Must-Have", "publisher": "Panini Comics", "format": "Cartonato"},
    "MVNWCOL_P": {"name": "Marvel Collection II", "publisher": "Panini Comics", "format": "Cartonato"},
    "MCOLL_M": {"name": "Marvel Collection I", "publisher": "Panini Comics", "format": "Brossurato"},
    "100M": {"name": "100% Marvel", "publisher": "Marvel Italia / Panini Comics", "format": "Brossurato"},
    "PSPP": {"name": "Play Special", "publisher": "Play Press", "format": "Brossurato"},
    "MARVELLC": {"name": "Marvel Legendary Collection", "publisher": "Hachette / Panini Comics", "format": "Cartonato"},
    "GEM_CA": {"name": "Grandi Eroi", "publisher": "Comic Art", "format": "Brossurato"},
    "MGNHCHT": {"name": "Marvel Graphic Novel", "publisher": "Hachette", "format": "Cartonato"},
    "GN_M": {"name": "Marvel Graphic Novels", "publisher": "Marvel Italia / Panini Comics", "format": "Cartonato"},
}

# This one story was split across two Italian physical issues.  The original
# builder can select only one first-publication anchor, so the second part is
# inserted here as an additional required physical reading step.
SPLIT_ITALIAN = {
    "ST2_007": ["WOL_PM_032", "WOL_PM_033"],
}

SOURCE_LABELS = {
    "ST1": "Strange Tales (1951)",
    "DS1": "Doctor Strange (1968)",
    "MFEAT1": "Marvel Feature (1971)",
    "MP1": "Marvel Premiere",
    "DS2": "Doctor Strange (1974)",
    "DSA": "Doctor Strange Annual",
    "ST2": "Strange Tales (1987)",
    "DS3": "Doctor Strange: Sorcerer Supreme",
    "MGN_STDO": "Doctor Strange & Doctor Doom: Triumph and Torment",
    "DS_DISTU": "Doctor Strange: What Is It That Disturbs You, Stephen?",
    "DS_TFOBO": "Doctor Strange: The Flight of Bones",
}

DA_PATTERN = re.compile(
    r"<em[^>]*>\s*da\s*</em>\s*(?:<strong[^>]*>\s*)?<a\b([^>]*)>",
    flags=re.I,
)


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def story_id(source_code: str, title: str) -> str:
    normalized = norm(title)
    if not normalized:
        raise RuntimeError(f"{source_code}: titolo feature Doctor Strange assente")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{STORY_PREFIX}{source_code}:{digest}"


def strip_lines(fragment: str) -> list[str]:
    text = re.sub(r"<(?:br|p|div|h[1-6]|li|tr|td|section|article)\b[^>]*>", "\n", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return [" ".join(line.split()) for line in text.splitlines() if " ".join(line.split())]


def feature_title(lines: list[str]) -> str:
    # ComicsBox renders: feature heading -> story title -> authors.  Work
    # backwards from the final script credit so compound headings such as
    # Doctor Strange/Doctor Doom are handled too.
    script_indexes = [index for index, line in enumerate(lines) if "(script)" in line.casefold()]
    if script_indexes:
        index = script_indexes[-1]
        if index > 0:
            return lines[index - 1]
    aliases = {"dr strange", "dr. strange", "doctor strange", "dottor strange", "dottor strange"}
    for index in range(len(lines) - 2, -1, -1):
        if norm(lines[index]) in {norm(alias) for alias in aliases}:
            return lines[index + 1]
    return ""


def is_doctor_strange_feature(lines: list[str]) -> bool:
    aliases = ("doctor strange", "dottor strange", "dr strange")
    for line in reversed(lines):
        lowered = norm(line)
        if lowered.startswith("protagonisti ") or lowered.startswith("protagonista "):
            return any(alias in lowered for alias in aliases)
    # Some entries omit protagonists; accept an explicit feature heading.
    exact_aliases = {"doctor strange", "dottor strange", "dr strange"}
    return any(norm(line) in exact_aliases for line in lines[-20:])


def parse_doctor_strange_features(source: str) -> list[dict[str, str]]:
    """Return exact Doctor Strange story blocks from one Italian edition page."""
    matches = list(DA_PATTERN.finditer(source))
    features: list[dict[str, str]] = []
    previous_end = 0
    seen: set[tuple[str, str]] = set()
    for match in matches:
        attributes = match.group(1)
        href = five.attr_value(attributes, "href")
        source_code = legacy.album_code(href)
        fragment = source[previous_end:match.start()]
        previous_end = match.end()
        if not source_code:
            continue
        lines = strip_lines(fragment)
        if not is_doctor_strange_feature(lines):
            continue
        title = feature_title(lines)
        if not title:
            raise RuntimeError(f"{source_code}: feature Doctor Strange trovata ma titolo non risolto")
        key = (source_code, norm(title))
        if key in seen:
            continue
        seen.add(key)
        features.append({
            "sourceCode": source_code,
            "title": title,
            "storyId": story_id(source_code, title),
        })
    return features


def source_label(source_code: str, title: str) -> str:
    prefix = source_code.rsplit("_", 1)[0]
    number = source_code.rsplit("_", 1)[-1].lstrip("0") or "0"
    base = SOURCE_LABELS.get(prefix, prefix)
    if prefix in {"MGN_STDO", "DS_DISTU"}:
        return f"{base} — {title}"
    return f"{base} #{number} — {title}"


def album_features(album_code: str) -> list[dict[str, str]]:
    source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{album_code}")
    return parse_doctor_strange_features(source)


def classic_source_codes(audit: dict[str, Any]) -> set[str]:
    return {row["usaCode"] for row in audit.get("mappings", []) if row.get("usaCode") and row.get("physicalId")}


def feature_for_source(features: list[dict[str, str]], source_code: str) -> dict[str, str]:
    matches = [feature for feature in features if feature["sourceCode"] == source_code]
    if not matches:
        raise RuntimeError(f"{source_code}: la pubblicazione italiana selezionata non espone la feature Doctor Strange")
    # Main feature is rendered first when an issue also has a Doctor Strange backup.
    return matches[0]


def physical_for_album(code: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metadata = five.load_italian_album(code)
    existing_by_album, existing_id_to_album = legacy.existing_physical_map()
    physical = legacy.assign_physical_ids({code: metadata}, existing_by_album, existing_id_to_album)[code]
    return physical, metadata.get("contents", [])


def transform_selected_contents(issue: dict[str, Any], selected: dict[str, dict[str, str]]) -> None:
    step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
    raw_ids = list(step.get("contentIds", []))
    if not raw_ids:
        return
    transformed: list[str] = []
    labels: list[str] = []
    for raw_id in raw_ids:
        feature = selected.get(raw_id)
        if not feature:
            transformed.append(raw_id)
            continue
        transformed.append(feature["storyId"])
        labels.append(source_label(raw_id, feature["title"]))
        for content in issue.get("contents", []):
            if content.get("id") != raw_id:
                continue
            content["sourceIssueId"] = raw_id
            content["id"] = feature["storyId"]
            content["feature"] = "Doctor Strange"
            content["storyTitle"] = feature["title"]
            content["title"] = source_label(raw_id, feature["title"])
            content["scope"] = "story-feature"
    step["contentIds"] = transformed
    if labels:
        issue["usaChapters"] = labels
        issue["title"] = five.concise(labels, 2)
        issue["instruction"] = "Leggi in questo albo: " + five.concise(labels, 3)
        issue["readingStep"]["scope"] = "doctor-strange-story-features"


def make_split_issue(
    album_code: str,
    source_code: str,
    canonical_feature: dict[str, str],
    position: int,
    era: str,
) -> dict[str, Any]:
    physical, contents = physical_for_album(album_code)
    features = album_features(album_code)
    present = [feature for feature in features if feature["sourceCode"] == source_code]
    if not present:
        raise RuntimeError(f"{album_code}: seconda parte di {source_code} non rilevata")
    label = source_label(source_code, canonical_feature["title"])
    transformed_contents = deepcopy(contents)
    found = False
    for content in transformed_contents:
        if content.get("id") != source_code:
            continue
        found = True
        content["sourceIssueId"] = source_code
        content["id"] = canonical_feature["storyId"]
        content["feature"] = "Doctor Strange"
        content["storyTitle"] = canonical_feature["title"]
        content["title"] = label
        content["scope"] = "story-feature"
    if not found:
        transformed_contents.append({
            "id": canonical_feature["storyId"],
            "sourceIssueId": source_code,
            "seriesId": source_code.rsplit("_", 1)[0],
            "series": SOURCE_LABELS.get(source_code.rsplit("_", 1)[0], source_code.rsplit("_", 1)[0]),
            "number": source_code.rsplit("_", 1)[-1].lstrip("0") or "0",
            "title": label,
            "feature": "Doctor Strange",
            "storyTitle": canonical_feature["title"],
            "scope": "story-feature",
            "url": f"https://www.comicsbox.it/albo/{source_code}",
        })
    physical = deepcopy(physical)
    physical.update({
        "seq": position,
        "required": True,
        "skip": False,
        "era": era,
        "eraSub": f"Continuazione italiana della stessa storia {source_code}.",
        "title": label,
        "instruction": f"Continua in questo albo: {label}",
        "usaChapters": [label],
        "sourceSeries": [source_code.rsplit("_", 1)[0]],
        "contents": transformed_contents,
        "contentsStatus": "complete",
        "readingStep": {
            "pathId": PATH_ID,
            "position": position,
            "contentIds": [canonical_feature["storyId"]],
            "scope": "doctor-strange-story-features",
        },
    })
    return physical


def refine_route(workers: int) -> None:
    character_path = DATA / "characters" / "doctor-strange.json"
    audit_path = DATA / "doctor-strange-audit.json"
    character = read_json(character_path)
    audit = read_json(audit_path)
    classic_codes = classic_source_codes(audit)

    issue_by_id = {issue["id"]: issue for issue in character.get("issues", [])}
    album_codes = {
        legacy.album_code(issue.get("url"))
        for issue in character.get("issues", [])
        if set(issue.get("readingStep", {}).get("contentIds", [])) & classic_codes
    }
    album_codes.discard("")
    features_by_album: dict[str, list[dict[str, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(album_features, code): code for code in sorted(album_codes)}
        for future in as_completed(futures):
            code = futures[future]
            try:
                features_by_album[code] = future.result()
            except Exception as error:
                errors[code] = str(error)
    if errors:
        raise RuntimeError("Feature delle pubblicazioni primarie non risolte: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    canonical: dict[str, dict[str, str]] = {}
    for mapping in audit.get("mappings", []):
        source_code = mapping.get("usaCode")
        physical_id = mapping.get("physicalId")
        if not source_code or not physical_id:
            continue
        issue = issue_by_id.get(physical_id)
        if not issue:
            raise RuntimeError(f"{source_code}: physicalId {physical_id} assente dal percorso")
        album_code = legacy.album_code(issue.get("url"))
        feature = feature_for_source(features_by_album.get(album_code, []), source_code)
        canonical[source_code] = feature

    for issue in character.get("issues", []):
        transform_selected_contents(issue, canonical)

    # Add the second physical half of Strange Tales (1987) #7.
    for source_code, albums in SPLIT_ITALIAN.items():
        feature = canonical.get(source_code)
        if not feature:
            raise RuntimeError(f"{source_code}: feature canonica assente per split italiano")
        existing_positions = [
            index for index, issue in enumerate(character["issues"])
            if feature["storyId"] in issue.get("readingStep", {}).get("contentIds", [])
        ]
        if not existing_positions:
            raise RuntimeError(f"{source_code}: prima parte non trovata nel percorso")
        insert_at = existing_positions[-1] + 1
        for album_code in albums[1:]:
            if any(legacy.album_code(issue.get("url")) == album_code for issue in character["issues"]):
                continue
            first = character["issues"][existing_positions[0]]
            character["issues"].insert(
                insert_at,
                make_split_issue(album_code, source_code, feature, insert_at + 1, first.get("era", "Strange Tales (1987)")),
            )
            insert_at += 1

    for index, issue in enumerate(character.get("issues", []), 1):
        issue["seq"] = index
        if isinstance(issue.get("readingStep"), dict):
            issue["readingStep"]["position"] = index

    required = sum(1 for issue in character["issues"] if issue.get("required") is not False and not issue.get("future"))
    character["totalRequired"] = required
    character["availableTotal"] = required
    character["storyIdentityModel"] = STORY_MODEL
    character["coverage"]["storyFeatureIds"] = len(canonical)
    character["coverage"]["physicalItalianIssues"] = len(character["issues"])
    character["coverage"]["completeContentAlbums"] = sum(issue.get("contentsStatus") == "complete" for issue in character["issues"])
    write_json(character_path, character)

    audit["storyIdentityModel"] = STORY_MODEL
    audit["classic"]["storyFeatures"] = len(canonical)
    audit["classic"]["physicalItalianIssues"] = len({issue["id"] for issue in character["issues"] if any(cid.startswith(STORY_PREFIX) for cid in issue.get("readingStep", {}).get("contentIds", []))})
    audit.setdefault("guardrails", {})["storyFeatureIdentity"] = (
        "Classic Doctor Strange reading steps use exact ComicsBox story-feature IDs. "
        "Same-USA-issue backups do not satisfy a main-story step unless their story title identity matches."
    )
    audit["guardrails"]["splitItalianStories"] = "ST2_007 requires both Wolverine #32 and #33 in the first Italian publication."
    for mapping in audit.get("mappings", []):
        source_code = mapping.get("usaCode")
        if source_code in canonical:
            mapping["storyId"] = canonical[source_code]["storyId"]
            mapping["storyTitle"] = canonical[source_code]["title"]
        if source_code in SPLIT_ITALIAN:
            physical_ids = []
            for album_code in SPLIT_ITALIAN[source_code]:
                issue = next((item for item in character["issues"] if legacy.album_code(item.get("url")) == album_code), None)
                if issue:
                    physical_ids.append(issue["id"])
            mapping["italianAlbums"] = SPLIT_ITALIAN[source_code]
            mapping["physicalIds"] = physical_ids
    write_json(audit_path, audit, pretty=True)
    log(f"Doctor Strange route refined: {len(canonical)} story features · {len(character['issues'])} physical steps")


def looks_like_strange(title: str, series_name: str = "") -> bool:
    text = norm(f"{series_name} {title}")
    return any(marker in text for marker in ("doctor strange", "dottor strange", "dr strange", "stregone supremo", "sorcerer supreme"))


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
            fresh = edition_from_row(meta, row)
            previous = existing.get(fresh["id"], {})
            candidates[fresh["id"]] = {**fresh, **previous, "sourceCode": fresh["sourceCode"], "source": "ComicsBox"}
            matched += 1
        log(f"{meta['name']}: {matched} candidate")
    return candidates


def load_candidate_features(candidates: dict[str, dict[str, Any]], workers: int) -> tuple[dict[str, list[dict[str, str]]], dict[str, str]]:
    result: dict[str, list[dict[str, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(album_features, item["sourceCode"]): eid for eid, item in candidates.items() if item.get("sourceCode")}
        for index, future in enumerate(as_completed(futures), 1):
            eid = futures[future]
            try:
                result[eid] = future.result()
            except Exception as error:
                errors[eid] = str(error)
            if index % 25 == 0 or index == len(futures):
                log(f"Feature alternative analizzate: {index}/{len(futures)}")
    return result, errors


def route_requirements(character: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str]]:
    required: dict[str, set[str]] = {}
    primary: dict[str, str] = {}
    for issue in character.get("issues", []):
        step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
        if step.get("pathId") != PATH_ID:
            continue
        ids = {str(code) for code in step.get("contentIds", []) if code}
        if not ids:
            raise RuntimeError(f"{issue.get('id')}: readingStep senza contentIds")
        required[issue["id"]] = ids
        primary[issue["id"]] = legacy.album_code(issue.get("url"))
    return required, primary


def refine_editions(workers: int) -> None:
    character = read_json(DATA / "characters" / "doctor-strange.json")
    required_by_issue, primary_by_issue = route_requirements(character)
    editions_path = DATA / "editions.json"
    payload = read_json(editions_path)
    existing = {item["id"]: deepcopy(item) for item in payload.get("editions", [])}

    # Any previous Doctor Strange coverage is deliberately discarded.  This pass
    # is the sole authoritative source and is based on actual story blocks.
    for item in existing.values():
        item["coverage"] = [row for row in item.get("coverage", []) if row.get("path") != PATH_ID]
        item.pop("doctorStrangeCoverage", None)

    candidates = discover_candidates(existing)
    parsed, errors = load_candidate_features(candidates, workers)
    if errors:
        raise RuntimeError("Feature alternative Doctor Strange non risolte: " + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items())))

    route_ids = set().union(*required_by_issue.values()) if required_by_issue else set()
    complete_links = 0
    partial_links = 0
    relevant_editions = 0
    exact_feature_count = 0

    for eid, candidate in candidates.items():
        features = parsed.get(eid, [])
        provided: set[str] = set()
        feature_labels: list[str] = []
        for feature in features:
            provided.add(feature["sourceCode"])  # modern dedicated series still use source-issue IDs
            provided.add(feature["storyId"])    # audited classic route uses exact feature IDs
            feature_labels.append(source_label(feature["sourceCode"], feature["title"]))
        overlap_route = provided & route_ids
        if not overlap_route:
            continue
        relevant_editions += 1
        exact_feature_count += len(features)
        candidate["contents"] = feature_labels
        candidate["contentIds"] = sorted(provided)
        rows = []
        for issue_id, required_ids in required_by_issue.items():
            overlap = sorted(required_ids & provided)
            if not overlap or primary_by_issue.get(issue_id) == candidate.get("sourceCode"):
                continue
            complete = required_ids.issubset(provided)
            rows.append({
                "path": PATH_ID,
                "issueIds": [issue_id],
                "label": candidate.get("name", eid),
                "contentIds": overlap,
                "requiredContentIds": sorted(required_ids),
                "complete": complete,
                "coverageLabel": "Completa" if complete else f"Parziale {len(overlap)}/{len(required_ids)}",
                "coverageModel": STORY_MODEL,
            })
            complete_links += int(complete)
            partial_links += int(not complete)
        if rows:
            candidate["coverage"] = [row for row in candidate.get("coverage", []) if row.get("path") != PATH_ID] + rows
            candidate["doctorStrangeCoverage"] = {
                "model": STORY_MODEL,
                "storyBlocks": len(features),
                "fullStepLinks": sum(1 for row in rows if row["complete"]),
                "partialStepLinks": sum(1 for row in rows if not row["complete"]),
            }
        existing[eid] = candidate

    editions = list(existing.values())
    editions.sort(key=lambda item: (norm(item.get("series", "")), edcat.natural_number(item.get("number")), norm(item.get("name", ""))))
    payload["version"] = max(int(payload.get("version", 2)), 4)
    payload["coverageModel"] = f"issue-links + doctor-strange/{STORY_MODEL}"
    payload["total"] = len(editions)
    payload["editions"] = editions
    write_json(editions_path, payload)

    audit = {
        "version": 2,
        "path": PATH_ID,
        "coverageModel": STORY_MODEL,
        "candidateEditions": len(candidates),
        "editionsWithRelevantContents": relevant_editions,
        "exactDoctorStrangeStoryBlocks": exact_feature_count,
        "completeStepLinks": complete_links,
        "partialStepLinks": partial_links,
        "rule": (
            "A Doctor Strange alternative is linked from the actual Doctor Strange story block in the Italian edition. "
            "Classic anthology/backup material uses source-issue + story-title identity; ownership is complete only when the union of owned editions covers every required story feature."
        ),
        "fanTranslations": "excluded from official-edition coverage",
        "auditedSeries": sorted(TARGET_SERIES),
    }
    write_json(DATA / "doctor-strange-alternatives-audit.json", audit, pretty=True)
    log(f"Doctor Strange alternatives refined: {relevant_editions} edizioni · {complete_links} completi · {partial_links} parziali")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("route", "editions", "all"), default="all")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(argv)
    workers = max(1, args.workers)
    if args.phase in {"route", "all"}:
        refine_route(workers)
    if args.phase in {"editions", "all"}:
        refine_editions(workers)


if __name__ == "__main__":
    main()
