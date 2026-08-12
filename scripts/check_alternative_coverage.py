#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
payload = json.loads((ROOT / "data" / "editions.json").read_text(encoding="utf-8"))
editions = payload.get("editions", [])

required = {
    "daredevil": ("Daredevil", 63, 340),
    "wolverine-616": ("Wolverine 616", 34, 153),
    "cyclops": ("Cyclops", 25, 58),
    "jean-grey": ("Jean Grey", 14, 14),
    "storm": ("Storm", 39, 42),
    "rogue": ("Rogue", 27, 21),
    "gambit": ("Gambit", 4, 2),
    "new-mutants": ("New Mutants", 25, 43),
    "x-factor": ("X-Factor", 23, 103),
    "x-force": ("X-Force", 17, 95),
}

failures = []
for path_id, (label, min_editions, min_issues) in required.items():
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

    print(f"{label}: {len(matches)} alternative editions, {len(covered_issue_ids)} covered physical issues")
    if len(matches) < min_editions or len(covered_issue_ids) < min_issues:
        failures.append(
            f"{label}: {len(matches)}/{len(covered_issue_ids)} below "
            f"{min_editions}/{min_issues}"
        )

if failures:
    raise SystemExit("Alternative-edition coverage regression: " + "; ".join(failures))
