#!/usr/bin/env python3
"""Build the deduplicated physical-issue catalog used by the profile page."""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unpack_character(path_id: str, meta_path: str) -> dict[str, Any]:
    light = read_json(ROOT / meta_path)
    if not isinstance(light.get("issueSources"), list):
        return light

    spec = read_json(DATA / "encoded" / f"{path_id}.json")
    if spec.get("encoding") != "gzip-base64-parts":
        raise RuntimeError(f"{path_id}: formato encoded non supportato")

    encoded = "".join(
        (ROOT / source).read_text(encoding="ascii").strip()
        for source in spec.get("sources", [])
    )
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def fill_missing(target: dict[str, Any], issue: dict[str, Any]) -> None:
    for key in (
        "name",
        "series",
        "seriesId",
        "n",
        "displayNumber",
        "title",
        "date",
        "dateQuality",
        "cover",
        "url",
        "future",
    ):
        value = issue.get(key)
        if target.get(key) in (None, "", []) and value not in (None, "", []):
            target[key] = value


def main() -> None:
    manifest = read_json(DATA / "characters.json")
    catalog: dict[str, dict[str, Any]] = {}

    for path_meta in manifest.get("characters", []):
        path_id = path_meta["id"]
        character = unpack_character(path_id, path_meta["data"])
        for issue in character.get("issues", []):
            issue_id = issue.get("id")
            if not issue_id:
                continue

            row = catalog.setdefault(
                issue_id,
                {
                    "id": issue_id,
                    "paths": [],
                    "pathNames": [],
                    "hubs": [],
                },
            )
            fill_missing(row, issue)

            if path_id not in row["paths"]:
                row["paths"].append(path_id)
                row["pathNames"].append(path_meta.get("name", path_id))
            for hub in path_meta.get("hubs", []):
                if hub not in row["hubs"]:
                    row["hubs"].append(hub)

    issues = list(catalog.values())
    for row in issues:
        row.setdefault("name", row["id"])
        row.setdefault("series", row.get("seriesId", "Marvel"))
        row.setdefault("title", "")
        row.setdefault("date", "")
        row.setdefault("n", 0)
        row.setdefault("future", False)

    issues.sort(
        key=lambda row: (
            str(row.get("series", "")).casefold(),
            int(row.get("n") or 0),
            str(row.get("name", "")).casefold(),
        )
    )

    output = {
        "version": 1,
        "manifestVersion": manifest.get("version"),
        "total": len(issues),
        "issues": issues,
    }
    target = DATA / "catalog.json"
    target.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Catalogo globale: {len(issues)} albi fisici unici")


if __name__ == "__main__":
    main()
