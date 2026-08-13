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

    contents = issue.get("contents")
    if isinstance(contents, list):
        merged = {item.get("id"): item for item in target.get("contents", []) if item.get("id")}
        order = [item.get("id") for item in target.get("contents", []) if item.get("id")]
        for content in contents:
            content_id = content.get("id")
            if not content_id:
                continue
            if content_id not in merged:
                merged[content_id] = content
                order.append(content_id)
            else:
                current = merged[content_id]
                for key, value in content.items():
                    if current.get(key) in (None, "", []) and value not in (None, "", []):
                        current[key] = value
        target["contents"] = [merged[content_id] for content_id in order]
        rank = {"unavailable": 0, "path-scoped": 1, "complete": 2}
        incoming = issue.get("contentsStatus", "path-scoped")
        if rank.get(incoming, 0) > rank.get(target.get("contentsStatus", "unavailable"), 0):
            target["contentsStatus"] = incoming


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("–", "-").split())


def build_path_entry(
    path_meta: dict[str, Any],
    character: dict[str, Any],
    issue: dict[str, Any],
) -> dict[str, Any]:
    reading_step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
    sequence = issue.get("seq")
    number = issue.get("n")
    timeline_mode = bool(character.get("timelineMode"))
    if timeline_mode and isinstance(sequence, int) and not isinstance(sequence, bool):
        token = f"p{sequence}"
    else:
        token = str(number if number is not None else sequence if sequence is not None else "")

    content_ids = reading_step.get("contentIds")
    if not isinstance(content_ids, list):
        content_ids = [
            content.get("id")
            for content in issue.get("contents", [])
            if isinstance(content, dict) and content.get("id")
        ]

    entry = {
        "pathId": path_meta["id"],
        "token": token,
        "position": reading_step.get("position", sequence),
        "contentIds": content_ids,
    }
    if issue.get("era"):
        entry["era"] = issue["era"]
    if issue.get("skip"):
        entry["optional"] = True
    return entry


def choose_path_cover(path_meta: dict[str, Any], issues: list[dict[str, Any]]) -> str | None:
    editorial_cover = path_meta.get("editorialCover")
    if editorial_cover:
        return str(editorial_cover)

    path_id = path_meta["id"]
    candidates = [
        row for row in issues
        if path_id in row.get("paths", []) and row.get("cover") and not row.get("future")
    ]
    if not candidates:
        return None

    start_name = _norm(str(path_meta.get("start", "")).split(" — ", 1)[0])
    if start_name:
        for row in candidates:
            issue_name = _norm(row.get("name", ""))
            if issue_name == start_name or start_name in issue_name or issue_name in start_name:
                return str(row["cover"])
    return str(candidates[0]["cover"])


def choose_first_event_cover(path_meta: dict[str, Any]) -> str | None:
    character = unpack_character(path_meta["id"], path_meta["data"])
    for issue in character.get("issues", []):
        if issue.get("cover") and not issue.get("future") and issue.get("required") is not False:
            return str(issue["cover"])
    return None


def write_ui_art(manifest: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path_art: dict[str, str] = {}
    for path_meta in manifest.get("characters", []):
        cover = choose_first_event_cover(path_meta) if path_meta.get("type") == "event" else choose_path_cover(path_meta, issues)
        if cover:
            path_art[path_meta["id"]] = cover

    preferred_hub_paths = {
        "main": ["spiderman", "avengers", "xmen", "fantastic-four"],
        "ultimate-classic": ["ultimate-spiderman-classic", "ultimate-xmen", "ultimates", "ultimate-fantastic-four"],
        "ultimate-new": ["ultimate-new-spiderman", "ultimate-new-black-panther", "ultimate-new-xmen", "ultimate-new-ultimates", "ultimate-new-wolverine"],
        "alternate": ["marvel-2099", "marvel-zombies", "what-if", "age-of-apocalypse"],
        "marvel-2099": ["marvel-2099", "spiderman-2099", "xmen-2099", "doom-2099"],
        "marvel-zombies": ["marvel-zombies", "marvel-zombies-battleworld", "marvel-zombies-dawn-of-decay", "marvel-zombies-red-band"],
        "what-if": ["what-if", "what-if-classic", "what-if-miles-morales", "what-if-dark"],
        "age-of-apocalypse": ["age-of-apocalypse", "astonishing-xmen-aoa", "x-universe-aoa", "return-age-of-apocalypse"],
        "avengers": ["ironman", "thor", "cap", "hulk"],
        "xmen": ["xmen", "wolverine-616"],
        "spider": ["spiderman", "venom"],
        "fantastic-four": ["fantastic-four", "doctor-doom"],
        "street": ["daredevil"],
        "mystic": ["doctor-strange", "ghost-rider", "blade", "moon-knight"],
        "cosmic": ["silver-surfer", "guardians-of-the-galaxy", "nova", "thanos"],
    }

    hubs_manifest = read_json(DATA / "hubs.json")
    hub_art: dict[str, list[str]] = {}
    for hub in hubs_manifest.get("hubs", []):
        ids = list(preferred_hub_paths.get(hub["id"], []))
        if not ids:
            for group in hub.get("groups", []):
                ids.extend(group.get("paths", []))
            ids.extend(
                path_meta["id"]
                for path_meta in manifest.get("characters", [])
                if hub["id"] in path_meta.get("hubs", [])
            )
        covers: list[str] = []
        for path_id in ids:
            cover = path_art.get(path_id)
            if cover and cover not in covers:
                covers.append(cover)
            if len(covers) >= 4:
                break
        if covers:
            hub_art[hub["id"]] = covers

    payload = {
        "version": 1,
        "manifestVersion": manifest.get("version"),
        "paths": path_art,
        "hubs": hub_art,
    }
    (DATA / "ui-art.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


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
                    "pathEntries": [],
                },
            )
            fill_missing(row, issue)

            if path_id not in row["paths"]:
                row["paths"].append(path_id)
                row["pathNames"].append(path_meta.get("name", path_id))
            for hub in path_meta.get("hubs", []):
                if hub not in row["hubs"]:
                    row["hubs"].append(hub)

            path_entry = build_path_entry(path_meta, character, issue)
            duplicate = any(
                entry.get("pathId") == path_entry["pathId"]
                and entry.get("token") == path_entry["token"]
                for entry in row["pathEntries"]
            )
            if not duplicate:
                row["pathEntries"].append(path_entry)

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
    write_ui_art(manifest, issues)
    print(f"Catalogo globale: {len(issues)} albi fisici unici")


if __name__ == "__main__":
    main()
