#!/usr/bin/env python3
"""Compatibility refinements for exact Doctor Strange story-feature parsing.

Doctor Strange needs story-level identity because anthology issues and
Sorcerer Supreme backups cannot be treated as equivalent to an entire USA
issue.  At the same time, Italian reprints often retitle the same USA story.
This layer therefore identifies a story by source USA issue plus a stable
fingerprint of its story body/metadata, not by the translated title.

It also handles ComicsBox markup exceptions such as Triumph and Torment and
keeps Wolverine #32/33 as one double-numbered Italian physical issue.
"""
from __future__ import annotations

import hashlib
import sys

import refine_doctor_strange_story_features as base

STORY_MODEL = "comicsbox-story-feature@2"


def is_doctor_strange_feature(lines: list[str]) -> bool:
    aliases = ("doctor strange", "dottor strange", "dr strange")
    for line in reversed(lines):
        lowered = base.norm(line)
        if lowered.startswith("protagonisti ") or lowered.startswith("protagonista "):
            return any(alias in lowered for alias in aliases)

    # ComicsBox occasionally omits protagonist metadata for graphic novels or
    # joint features. Accept only a genuine feature heading: an alias by itself
    # or an explicit joint heading such as "Dr. Strange and Dr. Doom".
    # Do NOT accept arbitrary strings beginning with the alias, because the raw
    # fragment can still contain the previous source-link text.
    for line in lines[-20:]:
        lowered = base.norm(line)
        for alias in aliases:
            if lowered == alias or lowered.startswith(alias + " and "):
                return True
    return False


def story_fingerprint(lines: list[str]) -> tuple[str, str]:
    """Return a title-independent fingerprint and the normalized evidence used.

    ComicsBox can use different Italian titles for the same source story in
    different reprints. The synopsis/notes/page-count block, however, is tied
    to the underlying story and also distinguishes separate features/backups
    coming from the same USA issue.
    """
    script_indexes = [index for index, line in enumerate(lines) if "(script)" in line.casefold()]
    start = script_indexes[-1] + 1 if script_indexes else 0

    evidence: list[str] = []
    for line in lines[start:]:
        normalized = base.norm(line)
        if not normalized:
            continue
        if normalized.startswith("protagonisti ") or normalized.startswith("protagonista "):
            break
        evidence.append(normalized)

    # Rare entries can have almost no synopsis. Fall back to stable credit/page/
    # protagonist metadata rather than the translated title.
    joined = " | ".join(evidence).strip()
    if len(joined) < 20:
        fallback: list[str] = []
        for line in lines:
            normalized = base.norm(line)
            if not normalized:
                continue
            if "(script)" in line.casefold() or "(art)" in line.casefold() or "(inks)" in line.casefold():
                fallback.append(normalized)
            elif normalized.startswith("protagonisti ") or normalized.startswith("protagonista "):
                fallback.append(normalized)
            elif " pagin" in normalized or normalized.endswith(" pagina"):
                fallback.append(normalized)
        joined = " | ".join(fallback).strip()

    if not joined:
        raise RuntimeError("feature Doctor Strange priva di evidenza stabile per il fingerprint")
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    return digest, joined


def parse_doctor_strange_features(source: str) -> list[dict[str, str]]:
    """Return exact Doctor Strange story blocks with title-independent IDs."""
    matches = list(base.DA_PATTERN.finditer(source))
    features: list[dict[str, str]] = []
    previous_end = 0
    seen: set[tuple[str, str]] = set()

    for match in matches:
        attributes = match.group(1)
        href = base.five.attr_value(attributes, "href")
        source_code = base.legacy.album_code(href)
        fragment = source[previous_end:match.start()]
        previous_end = match.end()
        if not source_code:
            continue

        lines = base.strip_lines(fragment)
        if not is_doctor_strange_feature(lines):
            continue
        title = base.feature_title(lines)
        if not title:
            raise RuntimeError(f"{source_code}: feature Doctor Strange trovata ma titolo non risolto")

        fingerprint, _evidence = story_fingerprint(lines)
        stable_id = f"{base.STORY_PREFIX}{source_code}:{fingerprint}"
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


def phase_from_argv(argv: list[str] | None) -> str:
    phase = "all"
    if argv and "--phase" in argv:
        try:
            phase = argv[argv.index("--phase") + 1]
        except (IndexError, ValueError):
            phase = "all"
    return phase


def clean_route_audit() -> None:
    audit_path = base.DATA / "doctor-strange-audit.json"
    audit = base.read_json(audit_path)
    audit.setdefault("guardrails", {})["storyFeatureIdentity"] = (
        "Classic Doctor Strange reading steps use source-USA-issue plus a title-independent "
        "ComicsBox story fingerprint. Retitled Italian reprints of the same story match, while "
        "different features/backups from the same USA issue remain distinct."
    )
    audit["guardrails"]["splitItalianStories"] = (
        "Strange Tales (1987) #7 is published in the single double-numbered Italian physical issue "
        "Wolverine #32/33 (WOL_PM_032); it must create one physical reading step, not two."
    )
    # The first-pass series parser can label anthology rows with the first feature
    # in the USA issue (e.g. Human Torch). Once the exact Doctor Strange story is
    # resolved, the audit row must expose that selected feature instead.
    for mapping in audit.get("mappings", []):
        source_code = mapping.get("usaCode")
        story_title = mapping.get("storyTitle")
        if source_code and story_title:
            mapping["usa"] = base.source_label(source_code, story_title)
    base.write_json(audit_path, audit, pretty=True)


def clean_alternatives_audit() -> None:
    audit_path = base.DATA / "doctor-strange-alternatives-audit.json"
    audit = base.read_json(audit_path)
    audit["coverageModel"] = STORY_MODEL
    audit["rule"] = (
        "A Doctor Strange alternative is linked from the actual Doctor Strange story block in the Italian edition. "
        "Classic anthology/backup material uses source-USA-issue plus a title-independent story fingerprint; "
        "ownership is complete only when the union of owned editions covers every required story feature."
    )
    base.write_json(audit_path, audit, pretty=True)


def main(argv: list[str] | None = None) -> None:
    base.STORY_MODEL = STORY_MODEL
    base.is_doctor_strange_feature = is_doctor_strange_feature
    base.parse_doctor_strange_features = parse_doctor_strange_features

    # ComicsBox's Italian series index identifies this as one physical double
    # issue: "Wolverine #32/33" with source code WOL_PM_032. The base refiner's
    # earlier two-object assumption is intentionally disabled.
    base.SPLIT_ITALIAN = {}
    base.main(argv)

    phase = phase_from_argv(argv)
    if phase in {"route", "all"}:
        clean_route_audit()
    if phase in {"editions", "all"}:
        clean_alternatives_audit()


if __name__ == "__main__":
    main(sys.argv[1:])
