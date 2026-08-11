#!/usr/bin/env python3
"""Exact regression checks for Magik Play Book #3 alternative editions."""
import json
from pathlib import Path

payload = json.loads(Path("data/editions.json").read_text(encoding="utf-8"))
by_id = {item.get("id"): item for item in payload.get("editions", [])}

required = ("PUNX_M:20", "MAROMNIB:65")
for edition_id in required:
    item = by_id.get(edition_id)
    if not item:
        raise SystemExit(f"missing required Magik alternative: {edition_id}")
    issue_ids = {
        issue_id
        for coverage in item.get("coverage", [])
        if coverage.get("path") == "magik"
        for issue_id in coverage.get("issueIds", [])
    }
    if "PB_PP:3" not in issue_ids:
        raise SystemExit(f"{edition_id} must cover magik/PB_PP:3; got {sorted(issue_ids)}")
    print(f"OK {edition_id} -> magik/PB_PP:3")

print("Magik Play Book #3 alternatives verified: Integrale #20 + Marvel Omnibus #65.")
