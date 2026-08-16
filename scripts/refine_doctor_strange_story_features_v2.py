#!/usr/bin/env python3
"""Compatibility refinements for exact Doctor Strange story-feature parsing.

Some ComicsBox entries, notably Triumph and Torment, omit a protagonists line
and identify the feature only with a joint heading such as
``Dr. Strange and Dr. Doom``.  This remains an exact Doctor Strange story block
and is accepted without relaxing source-issue + story-title identity.
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
    # joint features.  Accept an explicit feature heading that starts with a
    # Doctor Strange alias (e.g. "Dr. Strange and Dr. Doom"), but never a mere
    # mention in synopsis/credits.
    for line in lines[-20:]:
        lowered = base.norm(line)
        if any(lowered == alias or lowered.startswith(alias + " ") for alias in aliases):
            return True
    return False


def main(argv: list[str] | None = None) -> None:
    base.is_doctor_strange_feature = is_doctor_strange_feature
    base.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
