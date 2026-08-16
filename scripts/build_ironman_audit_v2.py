#!/usr/bin/env python3
"""Compatibility layer for the audited Iron Man classic route.

Corrections applied on top of the generic ComicsBox series-table parser:
- Iron Man (1968) #76 is reprint-only material from Iron Man #9 and does not
  create a second mandatory narrative step.
- the generic nested-table parser can carry the final Italian link from the
  #179-182 block into #183; the dedicated #183 page and current author index
  still expose no Italian publication, so that false SUPEROICLA_488 mapping is
  cleared explicitly and documented in the audit.
"""
from __future__ import annotations

import json
from pathlib import Path

import build_ironman_audit as base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPRINT_ONLY = {76}
FALSE_PRIMARY_OVERRIDES = {
    183: "SUPEROICLA_488",
}

_original_story_chapters = base.story_chapters


def story_chapters():
    chapters, summary = _original_story_chapters()
    filtered = [chapter for chapter in chapters if int(chapter.get("usaNumberInt") or 0) not in REPRINT_ONLY]
    removed = len(chapters) - len(filtered)
    corrected: list[dict[str, object]] = []
    for chapter in filtered:
        number = int(chapter.get("usaNumberInt") or 0)
        false_album = FALSE_PRIMARY_OVERRIDES.get(number)
        if false_album and chapter.get("italianCode") == false_album:
            corrected.append({
                "usaCode": chapter.get("usaCode"),
                "number": number,
                "discardedItalianAlbum": false_album,
            })
            chapter["italianCode"] = ""
            chapter["italianLabel"] = ""

    summary = dict(summary)
    summary["seriesRangeIssues"] = summary.get("issues", base.CLASSIC_END)
    summary["issues"] = base.CLASSIC_END - len(REPRINT_ONLY)
    summary["stories"] = len(filtered)
    summary["mappedStories"] = sum(bool(chapter.get("italianCode")) for chapter in filtered)
    summary["unmappedStories"] = sum(not bool(chapter.get("italianCode")) for chapter in filtered)
    summary["reprintOnlyIssues"] = sorted(REPRINT_ONLY)
    summary["correctedSeriesTableMappings"] = corrected
    base.log(f"Reprint-only esclusi dalla spina narrativa: {sorted(REPRINT_ONLY)} ({removed} story row)")
    if corrected:
        base.log("Mapping tabella serie corretti: " + ", ".join(
            f"#{row['number']} non è {row['discardedItalianAlbum']}" for row in corrected
        ))
    return filtered, summary


def postprocess() -> None:
    character_path = DATA / "characters" / "ironman.json"
    audit_path = DATA / "ironman-audit.json"
    character = json.loads(character_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    character.setdefault("coverage", {})["classicUsPublicationRange"] = "Iron Man (1968) #1-306"
    character["coverage"]["classicNarrativeIssues"] = base.CLASSIC_END - len(REPRINT_ONLY)
    character["coverage"]["reprintOnlyIssuesExcluded"] = sorted(REPRINT_ONLY)
    character["coverage"]["sourceMappingOverrides"] = [
        {"usaIssue": number, "discardedItalianAlbum": album, "status": "unpublished-in-italy"}
        for number, album in sorted(FALSE_PRIMARY_OVERRIDES.items())
    ]
    character_path.write_text(json.dumps(character, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    audit.setdefault("guardrails", {})["reprintOnly"] = (
        "Iron Man (1968) #76 is a reprint of Iron Man #9 and is excluded from the mandatory narrative spine; "
        "it must not create a second reading requirement for the same story."
    )
    audit["guardrails"]["seriesTableBoundaryOverride"] = (
        "Iron Man (1968) #183 remains without an official Italian publication in the audited source. "
        "SUPEROICLA_488 contains #179-182; a nested-table boundary artifact must not carry that link into #183."
    )
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    base.story_chapters = story_chapters
    base.main()
    postprocess()


if __name__ == "__main__":
    main()
