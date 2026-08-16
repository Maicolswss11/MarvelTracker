#!/usr/bin/env python3
"""Compatibility refinements for exact Doctor Strange story-feature parsing.

Some ComicsBox entries, notably Triumph and Torment, omit a protagonists line
and identify the feature only with a joint heading such as
``Dr. Strange and Dr. Doom``.  Wolverine #32/33 is also one double-numbered
Italian physical issue, not two separate objects.
"""
from __future__ import annotations

import sys

import refine_doctor_strange_story_features as base


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
    # HTML fragment can still contain the previous source-link text such as
    # "Doctor Strange vol 1 #183, Marvel Comics - USA".
    for line in lines[-20:]:
        lowered = base.norm(line)
        for alias in aliases:
            if lowered == alias or lowered.startswith(alias + " and "):
                return True
    return False


def main(argv: list[str] | None = None) -> None:
    base.is_doctor_strange_feature = is_doctor_strange_feature

    # ComicsBox's Italian series index identifies this as one physical double
    # issue: "Wolverine #32/33" with source code WOL_PM_032.  The base refiner's
    # earlier two-object assumption is intentionally disabled.
    base.SPLIT_ITALIAN = {}
    base.main(argv)

    phase = "all"
    if argv and "--phase" in argv:
        try:
            phase = argv[argv.index("--phase") + 1]
        except (IndexError, ValueError):
            phase = "all"
    if phase in {"route", "all"}:
        audit_path = base.DATA / "doctor-strange-audit.json"
        audit = base.read_json(audit_path)
        audit.setdefault("guardrails", {})["splitItalianStories"] = (
            "Strange Tales (1987) #7 is published in the single double-numbered Italian physical issue "
            "Wolverine #32/33 (WOL_PM_032); it must create one physical reading step, not two."
        )
        base.write_json(audit_path, audit, pretty=True)


if __name__ == "__main__":
    main(sys.argv[1:])
