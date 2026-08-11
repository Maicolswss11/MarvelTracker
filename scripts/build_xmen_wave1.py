#!/usr/bin/env python3
"""Build the first expanded X-Men solo-character wave.

Wave: Cyclops, Jean Grey, Storm, Rogue and Gambit.

This wrapper deliberately reuses the hardened Elektra/Deadpool/Cable/Magik
builder so the editorial invariant stays identical:

    physical Italian issue -> USA contents -> path-local readingStep

The only extra layer is source resolution. Dedicated series are pinned in the
versioned config; curated team/co-billed titles are resolved from the USA
alphabetical index and then filtered by protagonist credits. ComicsBox's
``/personaggio`` endpoint is deliberately not used because it currently returns
the same global publication table for unrelated slugs.
"""
from __future__ import annotations

import html
import json
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import build_mutant_street_wave as base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "xmen-wave1-sources.json"
AUDIT_PATH = DATA / "xmen-wave1-audit.json"
RESOLVED_PATH = DATA / ".xmen-wave1-resolved.json"
MANIFEST_VERSION = 28
USER_AGENT = "Mozilla/5.0 (compatible; MarvelTracker/1.0; +https://github.com/Maicolswss11/MarvelTracker)"
MAX_SOURCE_SERIES_PER_PATH = 30
EXCLUDED_SOURCE_MARKERS = (
    "ultimate",
    "what if",
    "age of apocalypse",
    "x ternals",
)

SVG_MARKS = {
    "cyclops": '<path d="M28 49h72v29H28Z" fill="none" stroke="currentColor" stroke-width="8"/><path d="M37 63h54" fill="none" stroke="#0b0f17" stroke-width="8"/><path d="M64 31v18M64 78v19" fill="none" stroke="currentColor" stroke-width="7"/>',
    "jean-grey": '<path d="M64 20c12 18 26 28 39 31-12 5-21 13-27 24 7 6 12 15 14 27-11-8-20-11-26-11s-15 3-26 11c2-12 7-21 14-27-6-11-15-19-27-24 13-3 27-13 39-31Z"/><circle cx="64" cy="63" r="11" fill="#0b0f17"/>',
    "storm": '<path d="M24 52c10-17 25-26 40-26s30 9 40 26c-13-6-25-7-36-2 12 7 19 18 21 33-10-7-18-10-25-10s-15 3-25 10c2-15 9-26 21-33-11-5-23-4-36 2Z"/><path d="M55 83 45 106M73 83l10 23" fill="none" stroke="currentColor" stroke-width="7"/>',
    "rogue": '<path d="M31 33h66L85 57l12 38H31l12-38Z" fill="none" stroke="currentColor" stroke-width="8"/><path d="M64 34v61M43 57h42" fill="none" stroke="currentColor" stroke-width="7"/>',
    "gambit": '<path d="m64 22 35 21-14 43-21 20-21-20-14-43Z" fill="none" stroke="currentColor" stroke-width="7"/><path d="m64 42 13 22-13 22-13-22Z"/><path d="M25 101 103 27" fill="none" stroke="currentColor" stroke-width="6"/>',
}

SERIES_LINK_RE = re.compile(
    r'href=["\'](?:https?://(?:www\.)?comicsbox\.it)?/?serie/([^"\'/?#]+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
TRANSIENT_MARKERS = (
    "Connessione MySQL fallita",
    "Lost connection to MySQL server",
    "Too many connections",
    "Table 'comicsbox_it_db.",
)


def log(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"))
    path.write_text(text + ("\n" if pretty else ""), encoding="utf-8")


def fetch_html(url: str, attempts: int = 6) -> str:
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
    })
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=45) as response:
                source = response.read().decode("utf-8", errors="replace")
            folded = source.casefold()
            if any(marker.casefold() in folded for marker in TRANSIENT_MARKERS):
                raise RuntimeError(f"transient ComicsBox database response: {url}")
            return source
        except Exception as error:
            last_error = error
            if attempt == attempts:
                break
            time.sleep(min(4 * attempt, 20))
    raise RuntimeError(f"ComicsBox fetch failed after {attempts} attempts: {url}: {last_error}")


def plain_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def norm_title(value: str) -> str:
    value = html.unescape(value).casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def series_links(source: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for code, raw_title in SERIES_LINK_RE.findall(source):
        code = html.unescape(code).strip()
        title = plain_label(raw_title)
        if not code or not title or code in seen:
            continue
        seen.add(code)
        rows.append({"code": code, "title": title})
    return rows


_letter_cache: dict[str, list[dict[str, str]]] = {}


def title_index(title: str) -> list[dict[str, str]]:
    normalized = norm_title(title)
    first = next((char.upper() for char in normalized if char.isalnum()), "")
    if not first:
        raise ValueError(f"cannot resolve empty series title: {title!r}")
    if first not in _letter_cache:
        source = fetch_html(f"https://www.comicsbox.it/comicsusa?l={quote(first)}")
        _letter_cache[first] = series_links(source)
    return _letter_cache[first]


def resolve_title(title: str) -> dict[str, str]:
    wanted = norm_title(title)
    rows = title_index(title)
    exact = [row for row in rows if norm_title(row["title"]) == wanted]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        codes = ", ".join(row["code"] for row in exact)
        raise RuntimeError(f"ambiguous ComicsBox series title {title!r}: {codes}")
    nearby = [row["title"] for row in rows
              if wanted in norm_title(row["title"]) or norm_title(row["title"]) in wanted]
    hint = f"; nearby: {', '.join(nearby[:8])}" if nearby else ""
    raise RuntimeError(f"ComicsBox series title not found: {title!r}{hint}")


def resolve_config(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = deepcopy(config)
    resolution: dict[str, Any] = {
        "strategy": "curated-explicit",
        "paths": [],
    }
    for path in resolved["paths"]:
        merged: list[dict[str, Any]] = []
        index_by_code: dict[str, int] = {}
        explicit_rows: list[dict[str, Any]] = []
        for raw in path.get("sources", []):
            spec = {"code": raw} if isinstance(raw, str) else deepcopy(raw)
            if not spec.get("code") and not spec.get("title"):
                raise ValueError(f"{path['id']}: source without code or title: {raw!r}")
            if not spec.get("code"):
                match = resolve_title(spec["title"])
                spec["code"] = match["code"]
                spec["resolvedTitle"] = match["title"]
            elif spec.get("title"):
                spec["resolvedTitle"] = spec["title"]

            code = spec["code"]
            display_title = spec.get("resolvedTitle", "")
            normalized_title = norm_title(display_title)
            if any(marker in normalized_title for marker in EXCLUDED_SOURCE_MARKERS):
                raise RuntimeError(
                    f"{path['id']}: excluded alternate-continuity source configured: "
                    f"{display_title} ({code})"
                )
            explicit_rows.append({
                "requested": raw,
                "resolvedCode": code,
                "resolvedTitle": display_title,
            })
            if code in index_by_code:
                merged[index_by_code[code]].update(spec)
            else:
                index_by_code[code] = len(merged)
                merged.append(spec)

        if len(merged) > MAX_SOURCE_SERIES_PER_PATH:
            raise RuntimeError(
                f"{path['id']}: {len(merged)} source series exceed the guarded maximum "
                f"of {MAX_SOURCE_SERIES_PER_PATH}"
            )
        path["sources"] = merged
        resolution["paths"].append({
            "id": path["id"],
            "strategy": "curated-explicit",
            "curatedSources": explicit_rows,
            "resolvedSeriesCount": len(merged),
        })
    return resolved, resolution


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = read_json(path)
    new_ids = {spec["id"] for spec in config["paths"]}
    items = [item for item in manifest["characters"] if item["id"] not in new_ids]
    reciprocal = {
        "xmen": ["cyclops", "jean-grey", "storm", "rogue", "gambit"],
        "wolverine-616": ["cyclops", "jean-grey", "storm", "rogue", "gambit"],
        "cable": ["cyclops", "jean-grey"],
        "blackpanther": ["storm"],
        "captainmarvel": ["rogue"],
    }
    for item in items:
        for related in reciprocal.get(item["id"], []):
            item.setdefault("relatedPaths", [])
            if related not in item["relatedPaths"]:
                item["relatedPaths"].append(related)

    for spec in config["paths"]:
        character = characters[spec["id"]]
        meta = {
            "id": spec["id"], "name": spec["name"], "subtitle": spec["subtitle"],
            "type": spec["type"], "pathRole": "main", "mainPath": True,
            "primaryHub": spec["primaryHub"], "hubs": spec["hubs"], "accent": spec["accent"],
            "logo": f"assets/heroes/{spec['id']}.svg", "data": f"data/characters/{spec['id']}.json",
            "start": character["start"], "end": character["end"], "totalRequired": character["totalRequired"],
            "relatedPaths": spec.get("relatedPaths", []),
        }
        anchor = spec.get("insertAfter")
        index = next((i + 1 for i, item in enumerate(items) if item["id"] == anchor), len(items))
        items.insert(index, meta)

    manifest["version"] = MANIFEST_VERSION
    manifest["characters"] = items
    write_json(path, manifest)


def update_hubs(config: dict[str, Any]) -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    by_id = {hub["id"]: hub for hub in payload.get("hubs", [])}
    xmen = by_id.get("xmen")
    if xmen:
        solo = base.ensure_group(xmen.setdefault("groups", []), "solo", "Percorsi personali")
        for path_id in ["cyclops", "jean-grey", "storm", "rogue", "gambit"]:
            if path_id not in solo["paths"]:
                solo["paths"].append(path_id)
    write_json(path, payload)


def main() -> None:
    config = read_json(CONFIG_PATH)
    resolved, resolution = resolve_config(config)
    write_json(RESOLVED_PATH, resolved, pretty=True)

    base.CONFIG_PATH = RESOLVED_PATH
    base.AUDIT_PATH = AUDIT_PATH
    base.MANIFEST_VERSION = MANIFEST_VERSION
    base.SVG_MARKS = SVG_MARKS
    base.update_manifest = update_manifest
    base.update_hubs = update_hubs

    try:
        base.main()
        audit = read_json(AUDIT_PATH)
        audit["sourceResolution"] = resolution
        write_json(AUDIT_PATH, audit, pretty=True)
    finally:
        RESOLVED_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
