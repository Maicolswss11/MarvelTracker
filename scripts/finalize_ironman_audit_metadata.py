#!/usr/bin/env python3
"""Recalculate Iron Man summary counters after path-local segmentation.

The base builder cannot know how many reading steps/physical books will remain
after exact story-feature refinement splits collected volumes.  This finalizer
runs after refinement so summary metadata always describes the emitted route.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, payload, *, pretty: bool = False):
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def main() -> None:
    character_path = DATA / "characters" / "ironman.json"
    audit_path = DATA / "ironman-audit.json"
    manifest_path = DATA / "characters.json"

    character = load(character_path)
    audit = load(audit_path)
    manifest = load(manifest_path)

    issues = character.get("issues", [])
    reading_steps = len(issues)
    physical_ids = {
        str(issue.get("physicalId") or issue.get("id"))
        for issue in issues
        if issue.get("physicalId") or issue.get("id")
    }
    required = sum(
        1 for issue in issues
        if issue.get("required") is not False and not issue.get("future")
    )

    coverage = character.setdefault("coverage", {})
    coverage["readingSteps"] = reading_steps
    coverage["physicalItalianIssues"] = len(physical_ids)
    character["totalRequired"] = required
    character["availableTotal"] = required

    audit["totalReadingSteps"] = reading_steps
    audit["uniquePhysicalItalianIssues"] = len(physical_ids)
    audit["totalRequired"] = required

    entry = next((row for row in manifest.get("characters", []) if row.get("id") == "ironman"), None)
    if entry is None:
        raise RuntimeError("ironman assente dal manifest")
    entry["totalRequired"] = required
    entry["start"] = character["start"]
    entry["end"] = character["end"]

    save(character_path, character)
    save(audit_path, audit, pretty=True)
    save(manifest_path, manifest)
    print(
        f"Iron Man final metadata: {reading_steps} reading steps · "
        f"{len(physical_ids)} physical books · {required} required"
    )


if __name__ == "__main__":
    main()
