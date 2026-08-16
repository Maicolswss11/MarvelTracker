#!/usr/bin/env python3
"""Resilient Iron Man audit wrapper.

Keeps the v2 reprint-aware narrative model and retries only Italian album pages
that fail after the parallel fetch pass. ComicsBox sometimes answers HTTP 200
with a temporary database-error page; one such response must not invalidate a
full #1-306 audit, but unresolved metadata still hard-fails downstream.
"""
from __future__ import annotations

import time

import build_five_character_expansion as five
import build_ironman_audit as base
import build_ironman_audit_v2 as v2

_original_load_albums = base.load_albums


def load_albums(codes: set[str], workers: int):
    result, errors = _original_load_albums(codes, workers)
    pending = set(errors)
    for attempt in range(1, 4):
        if not pending:
            break
        base.log(f"Retry seriale ComicsBox {attempt}/3: {len(pending)} albi")
        next_pending: set[str] = set()
        for code in sorted(pending):
            try:
                result[code] = five.load_italian_album(code)
                errors.pop(code, None)
            except Exception as error:
                errors[code] = str(error)
                next_pending.add(code)
        pending = next_pending
        if pending and attempt < 3:
            time.sleep(attempt * 2)
    return result, errors


def main() -> None:
    base.load_albums = load_albums
    v2.main()


if __name__ == "__main__":
    main()
