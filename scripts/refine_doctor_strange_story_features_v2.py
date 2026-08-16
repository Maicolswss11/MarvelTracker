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
    base.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
