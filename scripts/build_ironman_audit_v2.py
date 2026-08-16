#!/usr/bin/env python3
"""Compatibility layer for the audited Iron Man classic route.

Iron Man (1968) #76 is a reprint-only issue of Iron Man #9 and therefore does
not create a second narrative reading step. The base builder still audits the
full #1-306 publication range, while this layer removes #76 from the mandatory
story spine and records that decision explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path

import build_ironman_audit as base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPRINT_ONLY = {76}

_original_story_chapters = base.story_chapters


def story_chapters():
    chapters, summary = _original_story_chapters()
    filtered = [chapter for chapter in chapters if int(chapter.get("usaNumberInt") or 0) not in REPRINT_ONLY]
    removed = len(chapters) - len(filtered)
    summary = dict(summary)
    summary["seriesRangeIssues"] = summary.get("issues", base.CLASSIC_END)
    summary["issues"] = base.CLASSIC_END - len(REPRINT_ONLY)
    summary["stories"] = len(filtered)
    summary["mappedStories"] = sum(bool(chapter.get("italianCode")) for chapter in filtered)
    summary["unmappedStories"] = sum(not bool(chapter.get("italianCode")) for chapter in filtered)
    summary["reprintOnlyIssues"] = sorted(REPRINT_ONLY)
    base.log(f"Reprint-only esclusi dalla spina narrativa: {sorted(REPRINT_ONLY)} ({removed} story row)")
    return filtered, summary


def postprocess() -> None:
    character_path = DATA / "characters" / "ironman.json"
    audit_path = DATA / "ironman-audit.json"
    character = json.loads(character_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    character.setdefault("coverage", {})["classicUsPublicationRange"] = "Iron Man (1968) #1-306"
    character["coverage"]["classicNarrativeIssues"] = base.CLASSIC_END - len(REPRINT_ONLY)
    character["coverage"]["reprintOnlyIssuesExcluded"] = sorted(REPRINT_ONLY)
    character_path.write_text(json.dumps(character, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    audit.setdefault("guardrails", {})["reprintOnly"] = (
        "Iron Man (1968) #76 is a reprint of Iron Man #9 and is excluded from the mandatory narrative spine; "
        "it must not create a second reading requirement for the same story."
    )
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    base.story_chapters = story_chapters
    base.main()
    postprocess()


if __name__ == "__main__":
    main()
