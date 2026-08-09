#!/usr/bin/env python3
"""Run the Avengers expansion builder with robust ComicsBox character matching."""

from __future__ import annotations

import re

import build_avengers_expansion as expansion


def scan_avengers_issue(issue: dict) -> tuple[str, set[str]]:
    parser = expansion.base.parse_issue(issue["url"])
    matched: set[str] = set()

    # ComicsBox often renders cast names as plain text rather than personaggio links.
    # Mirror the proven strategy used by build_avengers_characters.py: inspect both
    # normalized text tokens and explicit character links.
    normalized_tokens = {expansion.base.normalize(token) for token in parser.tokens}
    token_aliases = {
        "hawkeye": {
            "hawkeye", "occhio di falco", "clint barton", "barton clint",
            "hawkeye clint barton", "occhio di falco clint barton",
        },
        "blackwidow": {
            "black widow", "vedova nera", "natasha romanoff", "romanoff natasha",
            "black widow natasha romanoff", "vedova nera natasha romanoff",
        },
        "blackpanther": {
            "black panther", "pantera nera", "t challa", "tchalla",
            "black panther t challa", "pantera nera t challa",
        },
        "captainmarvel": {
            "captain marvel", "capitan marvel", "carol danvers", "danvers carol",
            "captain marvel carol danvers", "capitan marvel carol danvers",
        },
        "shehulk": {
            "she hulk", "jennifer walters", "walters jennifer",
            "she hulk jennifer walters",
        },
    }

    disqualifiers = {
        "hawkeye": ("kate bishop",),
        "blackwidow": ("yelena belova",),
        "blackpanther": ("black panther shuri", "pantera nera shuri"),
        "captainmarvel": ("monica rambeau", "mar vell", "genis vell"),
        "shehulk": (),
    }

    for route_id, aliases in token_aliases.items():
        for token in normalized_tokens:
            if any(bad in token for bad in disqualifiers[route_id]):
                continue
            if any(
                token == alias
                or re.search(rf"(^| ){re.escape(alias)}( |$)", token)
                for alias in aliases
            ):
                matched.add(route_id)
                break

    for href, text in parser.links:
        for route_id in expansion.ROUTES:
            if expansion.person_matches(route_id, href, text):
                matched.add(route_id)

    return issue["id"], matched


expansion.scan_avengers_issue = scan_avengers_issue

if __name__ == "__main__":
    expansion.main()
