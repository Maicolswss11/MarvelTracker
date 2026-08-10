#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
payload = json.loads((ROOT / "data" / "editions.json").read_text(encoding="utf-8"))
editions = payload.get("editions", [])

required = {
    "daredevil": "Daredevil",
    "wolverine-616": "Wolverine 616",
}

failures = []
for path_id, label in required.items():
    matches = []
    covered_issue_ids = set()
    for edition in editions:
        if edition.get("source") != "ComicsBox":
            continue
        path_coverages = [
            coverage for coverage in edition.get("coverage", [])
            if coverage.get("path") == path_id and coverage.get("issueIds")
        ]
        if not path_coverages:
            continue
        matches.append(edition)
        for coverage in path_coverages:
            covered_issue_ids.update(coverage.get("issueIds", []))

    if not matches or not covered_issue_ids:
        failures.append(f"{label}: zero alternative ComicsBox coverage")
    else:
        print(f"{label}: {len(matches)} alternative editions, {len(covered_issue_ids)} covered physical issues")

if failures:
    raise SystemExit("Alternative-edition coverage regression: " + "; ".join(failures))
