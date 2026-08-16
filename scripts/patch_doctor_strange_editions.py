#!/usr/bin/env python3
"""Compatibility entry point for the Doctor Strange alternative-edition audit.

The original issue-level implementation was superseded by exact ComicsBox
story-feature identity.  Keep this filename for manual workflows while routing
all work through the authoritative refiner.
"""
from __future__ import annotations

import sys

from refine_doctor_strange_story_features import main


if __name__ == "__main__":
    main(["--phase", "editions", *sys.argv[1:]])
