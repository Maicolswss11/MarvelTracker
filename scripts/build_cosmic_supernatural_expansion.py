#!/usr/bin/env python3
"""Build the twelve intertwined cosmic and supernatural reading paths.

The source of truth is ``data/cosmic-supernatural-sources.json``.  For every
configured US series, ComicsBox exposes the first Italian publication next to
each original issue.  This builder follows those links, resolves the physical
Italian album, reuses existing MarvelTracker IDs by album URL, and records every
unmapped chapter as an explicit audit gap.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "cosmic-supernatural-sources.json"
AUDIT_PATH = DATA / "cosmic-supernatural-audit.json"
CACHE_ROOT = ROOT / ".cache" / "comicsbox-expansion"
MANIFEST_VERSION = 22
USER_AGENT = "MarvelTracker cosmic-supernatural expansion/2.0"

MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

ITALIAN_MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

OFFLINE = False
PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")


def cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_ROOT / f"{digest}.html"


def fetch_text(url: str, *, attempts: int = 5) -> str:
    cached = cache_path(url)
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    if OFFLINE:
        raise RuntimeError(f"cache assente in modalità offline: {url}")

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.6",
                },
            )
            with urlopen(request, timeout=50) as response:
                source = response.read().decode("utf-8", errors="replace")
            if not source.strip() or "Connessione MySQL fallita" in source:
                raise RuntimeError("risposta ComicsBox temporaneamente non disponibile")
            temporary = cached.with_suffix(".tmp")
            temporary.write_text(source, encoding="utf-8")
            temporary.replace(cached)
            return source
        except Exception as error:  # network failures are retried and then audited
            last_error = error
            if attempt < attempts:
                time.sleep(min(8.0, attempt * 1.4))
    raise RuntimeError(f"{url}: {last_error}")


def album_code(href: str | None) -> str:
    href = href or ""
    parsed = urlparse(href)
    marker = "/albo/"
    if marker in parsed.path:
        return unquote(parsed.path.split(marker, 1)[1].strip("/"))
    query = parse_qs(parsed.query)
    if query.get("albo"):
        return unquote(query["albo"][0])
    return ""


def series_code(href: str | None) -> str:
    href = href or ""
    match = re.search(r"(?:^|/)serie/([^/?#]+)", href)
    if match:
        return unquote(match.group(1))
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if query.get("serie"):
        return unquote(query["serie"][0])
    return ""


class ForeignSeriesParser(HTMLParser):
    """Parse the ComicsBox original-series table without third-party packages."""

    def __init__(self, code: str) -> None:
        super().__init__(convert_charrefs=True)
        self.code = code
        self.in_target_table = False
        self.table_depth = 0
        self.current: dict[str, Any] | None = None
        self.tr_depth = 0
        self.outer_cell = -1
        self.anchor: dict[str, Any] | None = None
        self.in_authors = 0
        self.in_h1 = 0
        self.h1_text: list[str] = []
        self.name = ""
        self.rows: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "h1" and not self.name:
            self.in_h1 += 1
            self.h1_text = []

        if tag == "table":
            if not self.in_target_table and attr.get("id") == "lista-table":
                self.in_target_table = True
                self.table_depth = 1
            elif self.in_target_table:
                self.table_depth += 1
            return
        if not self.in_target_table:
            return

        if tag == "tr":
            if self.current is None and self.table_depth == 1:
                self.current = {"cells": [], "anchors": [], "authors": []}
                self.tr_depth = 1
                self.outer_cell = -1
            elif self.current is not None:
                self.tr_depth += 1
        elif tag == "td" and self.current is not None and self.tr_depth == 1:
            self.current["cells"].append([])
            self.outer_cell = len(self.current["cells"]) - 1
        elif tag == "a" and self.current is not None:
            self.anchor = {"href": attr.get("href") or "", "text": []}
        elif tag == "span" and self.current is not None:
            classes = set((attr.get("class") or "").split())
            if "autori" in classes:
                self.in_authors += 1

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            self.h1_text.append(data)
        if self.current is None:
            return
        if self.outer_cell >= 0:
            self.current["cells"][self.outer_cell].append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)
        if self.in_authors:
            self.current["authors"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.in_h1:
            self.in_h1 -= 1
            if not self.in_h1:
                self.name = " ".join("".join(self.h1_text).split())

        if not self.in_target_table:
            return
        if tag == "a" and self.anchor is not None:
            self.anchor["text"] = " ".join("".join(self.anchor["text"]).split())
            if self.current is not None:
                self.current["anchors"].append(self.anchor)
            self.anchor = None
        elif tag == "span" and self.in_authors:
            self.in_authors -= 1
        elif tag == "td" and self.current is not None and self.tr_depth == 1:
            self.outer_cell = -1
        elif tag == "tr" and self.current is not None:
            self.tr_depth -= 1
            if self.tr_depth == 0:
                self._finish_row(self.current)
                self.current = None
                self.outer_cell = -1
        elif tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_target_table = False

    def _finish_row(self, row: dict[str, Any]) -> None:
        anchors = [item for item in row["anchors"] if album_code(item["href"])]
        if not anchors:
            return
        original = anchors[0]
        original_code = album_code(original["href"])
        if not original_code:
            return
        number = original["text"].strip().rstrip("* ")
        title = ""
        for item in anchors[1:]:
            if album_code(item["href"]) == original_code and item["text"] != number:
                title = item["text"]
                break
        italian = next(
            (item for item in anchors if album_code(item["href"]) != original_code),
            None,
        )
        cells = [" ".join("".join(parts).split()) for parts in row["cells"]]
        self.rows.append(
            {
                "code": original_code,
                "number": number,
                "date": cells[1] if len(cells) > 1 else "",
                "title": title or number,
                "authors": " ".join("".join(row["authors"]).split()),
                "italianCode": album_code(italian["href"]) if italian else "",
                "italianLabel": italian["text"] if italian else "",
            }
        )


class ItalianAlbumParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.capture: str | None = None
        self.buffer: list[str] = []
        self.name = ""
        self.publisher = ""
        self.date = ""
        self.series = ""
        self.series_id = ""
        self.cover = ""
        self.anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "h1" and not self.name:
            self.capture = "name"
            self.buffer = []
        elif tag == "span" and attr.get("id") == "editore_issue":
            self.capture = "publisher"
            self.buffer = []
        elif tag == "span" and attr.get("id") == "data_issue":
            self.capture = "date"
            self.buffer = []
        elif tag == "a":
            code = series_code(attr.get("href"))
            if code:
                self.anchor = {"code": code, "text": []}
        elif tag == "img" and not self.cover:
            source = attr.get("src") or ""
            if "/cover/" in source:
                self.cover = source

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "span"} and self.capture:
            value = " ".join("".join(self.buffer).split())
            setattr(self, self.capture, value)
            self.capture = None
            self.buffer = []
        elif tag == "a" and self.anchor is not None:
            text = " ".join("".join(self.anchor["text"]).split())
            if text.casefold().startswith("lista completa di ") and not self.series_id:
                self.series_id = self.anchor["code"]
                self.series = text[len("Lista completa di "):].strip()
            self.anchor = None


def load_foreign_series(code: str, max_pages: int = 10) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    name = ""
    for offset in range(0, max_pages * 50, 50):
        url = f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}"
        parser = ForeignSeriesParser(code)
        parser.feed(fetch_text(url))
        if parser.name and not name:
            name = parser.name
        fresh = 0
        for row in parser.rows:
            if row["code"] in seen:
                continue
            seen.add(row["code"])
            rows.append(row)
            fresh += 1
        if fresh == 0 or fresh < 50:
            break
    if not rows:
        raise RuntimeError(f"{code}: serie vuota o codice non valido")
    return {"code": code, "name": name or code, "rows": rows}


def load_italian_album(code: str) -> dict[str, Any]:
    parser = ItalianAlbumParser()
    parser.feed(fetch_text(f"https://www.comicsbox.it/albo/{code}"))
    if not parser.name or not parser.date:
        raise RuntimeError(f"{code}: metadati italiani incompleti")
    series_id = parser.series_id or re.sub(r"_[^_]+$", "", code)
    series = parser.series or re.sub(r"\s*#.*$", "", parser.name).strip() or series_id
    return {
        "albumCode": code,
        "name": parser.name,
        "series": series,
        "seriesId": series_id,
        "publisher": parser.publisher or "Editore italiano non indicato",
        "date": parser.date,
        "dateQuality": "ComicsBox",
        "cover": (
            f"https://www.comicsbox.it{parser.cover}"
            if parser.cover.startswith("/")
            else parser.cover or f"https://www.comicsbox.it/cover/{code}.jpg"
        ),
        "url": f"https://www.comicsbox.it/albo/{code}",
        "future": False,
        "coverSource": "ComicsBox",
    }


def numeric_token(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value or "")
    return float(match.group()) if match else None


def included(number: str, selectors: list[str] | None) -> bool:
    if not selectors:
        return True
    token = numeric_token(number)
    if token is None:
        return False
    for selector in selectors:
        selector = str(selector).strip()
        range_match = re.fullmatch(r"(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)", selector)
        if range_match:
            low, high = map(float, range_match.groups())
            if low <= token <= high:
                return True
        else:
            exact = numeric_token(selector)
            if exact is not None and token == exact:
                return True
    return False


def original_date_key(value: str, source_index: int, number: str) -> tuple[Any, ...]:
    value = " ".join((value or "").split())
    year_match = re.search(r"\b(19|20)\d{2}\b", value)
    year = int(year_match.group()) if year_match else 9999
    month = 6
    for label, month_number in MONTH_NUMBERS.items():
        if re.search(rf"\b{label}\b", value, re.I):
            month = month_number
            break
    return (year, month, source_index, numeric_token(number) or 0, number)


def italian_number(metadata: dict[str, Any]) -> tuple[int, str]:
    name = metadata.get("name", "")
    code = metadata.get("albumCode", "")
    match = re.search(r"#\s*([0-9]+(?:/[0-9]+)?)", name)
    display = match.group(1) if match else ""
    if not display:
        match = re.search(r"_0*([0-9]+)(?:[A-Za-z]*)$", code)
        display = match.group(1) if match else "1"
    number_match = re.search(r"\d+", display)
    return (int(number_match.group()) if number_match else 1, display)


def unpack_character(path_id: str, meta_path: str) -> dict[str, Any]:
    light = read_json(ROOT / meta_path)
    if not isinstance(light.get("issueSources"), list):
        return light
    spec = read_json(DATA / "encoded" / f"{path_id}.json")
    encoded = "".join(
        (ROOT / source).read_text(encoding="ascii").strip()
        for source in spec.get("sources", [])
    )
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def existing_physical_map() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    catalog = read_json(DATA / "catalog.json")
    by_album: dict[str, dict[str, Any]] = {}
    id_to_album: dict[str, str] = {}
    for issue in catalog.get("issues", []):
        code = album_code(issue.get("url"))
        if not code:
            continue
        by_album[code] = deepcopy(issue)
        id_to_album[issue["id"]] = code
    return by_album, id_to_album


def assign_physical_ids(
    metadata_by_album: dict[str, dict[str, Any]],
    existing_by_album: dict[str, dict[str, Any]],
    existing_id_to_album: dict[str, str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    used = dict(existing_id_to_album)
    for code in sorted(metadata_by_album):
        if code in existing_by_album:
            issue = deepcopy(existing_by_album[code])
            issue["albumCode"] = code
            result[code] = issue
            continue
        issue = deepcopy(metadata_by_album[code])
        n, display = italian_number(issue)
        base_id = f"{issue['seriesId']}:{display}"
        issue_id = base_id
        if issue_id in used and used[issue_id] != code:
            issue_id = f"{base_id}@{code}"
        used[issue_id] = code
        issue["id"] = issue_id
        issue["n"] = n
        if display != str(n):
            issue["displayNumber"] = display
        result[code] = issue
    return result


def source_chapters(
    path: dict[str, Any],
    series_results: dict[str, dict[str, Any]],
    source_errors: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chapters: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for source_index, source in enumerate(path.get("sources", [])):
        code = source["code"]
        loaded = series_results.get(code)
        selected: list[dict[str, Any]] = []
        if loaded:
            selected = [
                row for row in loaded["rows"]
                if included(row["number"], source.get("include"))
            ]
        for row in selected:
            series_name = loaded["name"] if loaded else code
            label = f"{series_name} #{row['number']}"
            if row.get("title") and row["title"] != row["number"]:
                label += f" — {row['title']}"
            chapters.append(
                {
                    "kind": "chapter",
                    "sourceCode": code,
                    "sourceName": series_name,
                    "usaCode": row["code"],
                    "usaNumber": row["number"],
                    "usaTitle": row.get("title", ""),
                    "usaDate": row.get("date", ""),
                    "authors": row.get("authors", ""),
                    "label": label,
                    "era": source["era"],
                    "italianCode": row.get("italianCode", ""),
                    "italianLabel": row.get("italianLabel", ""),
                    "sort": original_date_key(row.get("date", ""), source_index, row["number"]),
                }
            )
        summaries.append(
            {
                "code": code,
                "name": loaded["name"] if loaded else code,
                "era": source["era"],
                "selectors": source.get("include", ["all"]),
                "chapters": len(selected),
                "mapped": sum(1 for row in selected if row.get("italianCode")),
                "unmapped": sum(1 for row in selected if not row.get("italianCode")),
                **({"error": source_errors[code]} if code in source_errors else {}),
            }
        )
    return chapters, summaries


def reused_chapters(path: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = {item["id"]: item for item in manifest["characters"]}
    chapters: list[dict[str, Any]] = []
    start_index = len(path.get("sources", [])) + 100
    for reuse_index, reuse in enumerate(path.get("reusePaths", [])):
        meta = metadata.get(reuse["id"])
        if not meta:
            raise RuntimeError(f"{path['id']}: percorso riusato inesistente {reuse['id']}")
        character = unpack_character(meta["id"], meta["data"])
        for issue_index, issue in enumerate(character.get("issues", [])):
            code = album_code(issue.get("url"))
            if not code:
                continue
            chapters.append(
                {
                    "kind": "reuse",
                    "sourceCode": f"@{reuse['id']}",
                    "sourceName": meta["name"],
                    "usaCode": f"{reuse['id']}:{issue_index + 1}",
                    "usaNumber": str(issue_index + 1),
                    "usaTitle": issue.get("title", ""),
                    "usaDate": str(reuse["year"]),
                    "authors": "",
                    "label": f"{meta['name']} — {issue.get('instruction') or issue.get('name')}",
                    "era": reuse["era"],
                    "italianCode": code,
                    "italianLabel": issue.get("name", ""),
                    "sort": (reuse["year"], 6, start_index + reuse_index, issue_index, ""),
                }
            )
    return chapters


def concise_labels(labels: list[str], limit: int = 4) -> str:
    if len(labels) <= limit:
        return "; ".join(labels)
    return "; ".join(labels[:limit]) + f"; + altri {len(labels) - limit} capitoli"


def build_character(
    path: dict[str, Any],
    chapters: list[dict[str, Any]],
    physical_by_album: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    mappings: list[dict[str, Any]] = []
    for chapter in sorted(chapters, key=lambda item: item["sort"]):
        italian_code = chapter.get("italianCode", "")
        physical = physical_by_album.get(italian_code)
        mapping = {
            "kind": chapter["kind"],
            "sourceCode": chapter["sourceCode"],
            "usaCode": chapter["usaCode"],
            "usa": chapter["label"],
            "usaDate": chapter["usaDate"],
            "italianAlbum": italian_code or None,
            "physicalId": physical.get("id") if physical else None,
        }
        mappings.append(mapping)
        if not physical:
            continue
        issue_id = physical["id"]
        group = groups.setdefault(
            issue_id,
            {
                "physical": physical,
                "sort": chapter["sort"],
                "labels": [],
                "eras": [],
                "sources": [],
            },
        )
        if chapter["sort"] < group["sort"]:
            group["sort"] = chapter["sort"]
        if chapter["label"] not in group["labels"]:
            group["labels"].append(chapter["label"])
        if chapter["era"] not in group["eras"]:
            group["eras"].append(chapter["era"])
        if chapter["sourceCode"] not in group["sources"]:
            group["sources"].append(chapter["sourceCode"])

    issues: list[dict[str, Any]] = []
    for sequence, group in enumerate(sorted(groups.values(), key=lambda item: item["sort"]), 1):
        physical = deepcopy(group["physical"])
        issue = {
            "id": physical["id"],
            "seq": sequence,
            "n": int(physical.get("n") or 0),
            "name": physical.get("name") or physical["id"],
            "title": physical.get("title") or group["labels"][0],
            "date": physical.get("date") or "Data italiana non disponibile",
            "seriesId": physical.get("seriesId") or physical["id"].split(":", 1)[0],
            "series": physical.get("series") or "Marvel",
            "publisher": physical.get("publisher") or "Editore italiano non indicato",
            "cover": physical.get("cover"),
            "url": physical.get("url"),
            "future": bool(physical.get("future", False)),
            "required": True,
            "skip": False,
            "coverSource": physical.get("coverSource", "ComicsBox"),
            "era": group["eras"][0],
            "eraSub": " · ".join(group["eras"][:3]),
            "instruction": "Prima pubblicazione italiana per: " + concise_labels(group["labels"]),
            "usaChapters": group["labels"],
            "sourceSeries": group["sources"],
        }
        if physical.get("displayNumber"):
            issue["displayNumber"] = physical["displayNumber"]
        if physical.get("dateQuality"):
            issue["dateQuality"] = physical["dateQuality"]
        issues.append(issue)

    if not issues:
        raise RuntimeError(f"{path['id']}: nessuna pubblicazione italiana risolta")
    mapped_chapters = sum(1 for mapping in mappings if mapping["physicalId"])
    missing = [mapping for mapping in mappings if not mapping["physicalId"]]
    required_count = sum(1 for issue in issues if not issue["future"])
    series_rows: dict[str, dict[str, Any]] = {}
    for issue in issues:
        row = series_rows.setdefault(
            issue["seriesId"],
            {
                "id": issue["seriesId"],
                "name": issue["series"],
                "publisher": issue["publisher"],
                "range": "prime pubblicazioni italiane censite",
            },
        )
        if row["publisher"] == "Editore italiano non indicato" and issue["publisher"]:
            row["publisher"] = issue["publisher"]

    coverage_sentence = (
        f" La matrice collega {mapped_chapters} di {len(mappings)} capitoli censiti a "
        f"{len(issues)} pubblicazioni fisiche italiane; {len(missing)} lacune restano dichiarate nell'audit."
    )
    character = {
        "id": path["id"],
        "name": path["name"],
        "subtitle": path["subtitle"],
        "accent": path["accent"],
        "start": f"{issues[0]['name']} — {issues[0]['date']}",
        "end": f"{issues[-1]['name']} — {issues[-1]['date']}",
        "description": path["description"] + coverage_sentence,
        "timelineMode": True,
        "readingOrderSource": "ComicsBox USA → prima pubblicazione italiana; configurazione editoriale MarvelTracker",
        "coverage": {
            "originalChapters": len(mappings),
            "mappedChapters": mapped_chapters,
            "missingItalianPublications": len(missing),
            "physicalItalianIssues": len(issues),
        },
        "series": list(series_rows.values()),
        "archives": [],
        "totalRequired": required_count,
        "availableTotal": required_count,
        "issues": issues,
    }
    audit = {
        "id": path["id"],
        "name": path["name"],
        "originalChapters": len(mappings),
        "mappedChapters": mapped_chapters,
        "missingItalianPublications": len(missing),
        "physicalItalianIssues": len(issues),
        "mappings": mappings,
    }
    return character, audit


def update_manifest(config: dict[str, Any], characters: dict[str, dict[str, Any]]) -> None:
    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    new_ids = {path["id"] for path in config["paths"]}
    old = [item for item in manifest["characters"] if item["id"] not in new_ids]
    insert_at = next(
        (index + 1 for index, item in enumerate(old) if item["id"] == "ultimates-616"),
        len(old),
    )
    metadata: list[dict[str, Any]] = []
    for path in config["paths"]:
        character = characters[path["id"]]
        metadata.append(
            {
                "id": path["id"],
                "name": path["name"],
                "subtitle": path["subtitle"],
                "type": path["type"],
                "primaryHub": path["primaryHub"],
                "hubs": path["hubs"],
                "accent": path["accent"],
                "logo": f"assets/heroes/{path['id']}.svg",
                "data": f"data/characters/{path['id']}.json",
                "start": character["start"],
                "end": character["end"],
                "totalRequired": character["totalRequired"],
            }
        )
    manifest["version"] = MANIFEST_VERSION
    manifest["characters"] = old[:insert_at] + metadata + old[insert_at:]
    write_json(manifest_path, manifest)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = read_json(path)
    for hub in payload.get("hubs", []):
        if hub["id"] == "mystic":
            hub.pop("status", None)
            hub["groups"] = [
                {"id": "core", "label": "Magia e realtà occulta", "paths": ["doctor-strange", "scarletwitch"]},
                {"id": "supernatural", "label": "Spiriti, vampiri e Figli della Mezzanotte", "paths": ["ghost-rider", "blade", "moon-knight", "midnight-sons", "morbius"]},
                {"id": "hybrid", "label": "Tra Inferno e cosmo", "paths": ["cosmic-ghost-rider"]},
            ]
            hub["featuredPath"] = "ghost-rider"
        elif hub["id"] == "cosmic":
            hub.pop("status", None)
            hub["groups"] = [
                {"id": "explorers", "label": "Esploratori e squadre cosmiche", "paths": ["ultimates-616", "silver-surfer", "nova", "guardians-of-the-galaxy"]},
                {"id": "powers", "label": "Potenze cosmiche", "paths": ["adam-warlock", "thanos", "galactus-heralds"]},
                {"id": "hybrid", "label": "Spirito di Vendetta cosmico", "paths": ["cosmic-ghost-rider"]},
            ]
            hub["featuredPath"] = "silver-surfer"
    write_json(path, payload)


SVG_MARKS = {
    "ghost-rider": '<path d="M64 18c15 17 7 26 21 36 10 7 13 17 8 29-6 15-18 24-29 24S40 98 35 84c-4-12 1-23 12-32 9-8 10-18 17-34Z"/><path d="M47 70h34v21l-9 9H56l-9-9Z" fill="#0b0f17"/><circle cx="56" cy="80" r="4" fill="currentColor"/><circle cx="72" cy="80" r="4" fill="currentColor"/>',
    "blade": '<path d="m34 99 54-70 7 7-54 70Z"/><path d="m31 31 66 66-7 7-66-66Z"/><path d="m80 25 23 23-8 8-23-23Z" fill="#0b0f17"/>',
    "moon-knight": '<path d="M87 25a43 43 0 1 0 0 78A34 34 0 1 1 87 25Z"/>',
    "midnight-sons": '<path d="M87 25a43 43 0 1 0 0 78A34 34 0 1 1 87 25Z"/><path d="M72 54c16 15 4 21 13 31-6 13-14 18-22 18-11 0-20-10-18-22 2-10 12-15 14-29 6 6 8 13 13 2Z"/>',
    "morbius": '<path d="M18 48c15-4 25 1 35 14L64 45l11 17c10-13 20-18 35-14-5 29-18 48-46 59-28-11-41-30-46-59Z"/><path d="M52 72h24L64 96Z" fill="#0b0f17"/>',
    "silver-surfer": '<path d="M18 86c28 16 68 13 94-9-18 33-65 45-94 9Z"/><circle cx="64" cy="37" r="11"/><path d="M61 47 48 72l11 5 9-17 13 13 8-8-17-18Z"/>',
    "nova": '<path d="m64 14 11 34 36 1-29 21 10 34-28-20-28 20 10-34-29-21 36-1Z"/><path d="M46 56h36v23L64 94 46 79Z" fill="#0b0f17"/>',
    "guardians-of-the-galaxy": '<circle cx="64" cy="64" r="39" fill="none" stroke="currentColor" stroke-width="10"/><path d="m64 20 9 28 30 1-24 17 9 29-24-17-24 17 9-29-24-17 30-1Z"/>',
    "adam-warlock": '<path d="M64 14 98 42 88 98 64 114 40 98 30 42Z" fill="none" stroke="currentColor" stroke-width="9"/><path d="m64 35 12 21-12 22-12-22Z"/><circle cx="64" cy="56" r="6" fill="#0b0f17"/>',
    "thanos": '<path d="M35 28h58l10 29-10 43-29 14-29-14-10-43Z"/><path d="M43 42h42l8 18-10 31-19 10-19-10-10-31Z" fill="#0b0f17"/><path d="M49 60h30M52 78h24" fill="none" stroke="currentColor" stroke-width="7"/>',
    "galactus-heralds": '<path d="M32 18h18v21h28V18h18v31l13 12-12 43-33 12-33-12-12-43 13-12Z"/><path d="M43 50h42l7 15-10 28-18 9-18-9-10-28Z" fill="#0b0f17"/><circle cx="64" cy="69" r="6"/>',
    "cosmic-ghost-rider": '<path d="M64 15c14 16 8 24 20 34 14 11 15 29 4 43-7 9-15 14-24 14-18 0-31-16-27-34 2-10 12-17 15-31 7 7 8 14 12-26Z"/><path d="m64 48 7 15h17L75 74l5 17-16-10-16 10 5-17-13-11h17Z" fill="#0b0f17"/>',
}


def write_logos(config: dict[str, Any]) -> None:
    target = ROOT / "assets" / "heroes"
    target.mkdir(parents=True, exist_ok=True)
    for path in config["paths"]:
        mark = SVG_MARKS[path["id"]]
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" '
            f'style="color:{path["accent"]}"><circle cx="64" cy="64" r="58" '
            'fill="#0b0f17" stroke="currentColor" stroke-width="5"/>'
            f'<g fill="currentColor" stroke-linecap="round" stroke-linejoin="round">{mark}</g></svg>'
        )
        (target / f"{path['id']}.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    global OFFLINE
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use only the local HTML cache")
    parser.add_argument("--workers", type=int, default=int(os.environ.get("MARVELTRACKER_WORKERS", "8")))
    args = parser.parse_args()
    OFFLINE = args.offline

    config = read_json(CONFIG_PATH)
    if len(config.get("paths", [])) != 12 or config["paths"][-1]["id"] != "cosmic-ghost-rider":
        raise RuntimeError("la configurazione deve contenere 12 percorsi e terminare con Cosmic Ghost Rider")

    manifest_before = read_json(DATA / "characters.json")
    existing_by_album, existing_id_to_album = existing_physical_map()
    unique_codes = sorted({source["code"] for path in config["paths"] for source in path["sources"]})
    log(f"Serie USA da verificare: {len(unique_codes)}")

    series_results: dict[str, dict[str, Any]] = {}
    source_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(load_foreign_series, code): code for code in unique_codes}
        for completed, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                series_results[code] = future.result()
            except Exception as error:
                source_errors[code] = str(error)
                log(f"  ! {code}: {error}")
            if completed % 20 == 0 or completed == len(futures):
                log(f"Serie USA: {completed}/{len(futures)}")

    path_chapters: dict[str, list[dict[str, Any]]] = {}
    path_source_summaries: dict[str, list[dict[str, Any]]] = {}
    all_italian_codes: set[str] = set()
    for path in config["paths"]:
        chapters, summaries = source_chapters(path, series_results, source_errors)
        chapters.extend(reused_chapters(path, manifest_before))
        path_chapters[path["id"]] = chapters
        path_source_summaries[path["id"]] = summaries
        all_italian_codes.update(chapter["italianCode"] for chapter in chapters if chapter.get("italianCode"))

    metadata_by_album: dict[str, dict[str, Any]] = {}
    album_errors: dict[str, str] = {}
    for code in all_italian_codes:
        if code in existing_by_album:
            metadata_by_album[code] = deepcopy(existing_by_album[code])
            metadata_by_album[code]["albumCode"] = code
    missing_metadata = sorted(all_italian_codes - set(metadata_by_album))
    log(f"Albi italiani unici: {len(all_italian_codes)} ({len(missing_metadata)} nuovi da arricchire)")
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(load_italian_album, code): code for code in missing_metadata}
        for completed, future in enumerate(as_completed(futures), 1):
            code = futures[future]
            try:
                metadata_by_album[code] = future.result()
            except Exception as error:
                album_errors[code] = str(error)
                log(f"  ! albo {code}: {error}")
            if completed % 25 == 0 or completed == len(futures):
                log(f"Albi italiani: {completed}/{len(futures)}")

    physical_by_album = assign_physical_ids(
        metadata_by_album,
        existing_by_album,
        existing_id_to_album,
    )

    characters: dict[str, dict[str, Any]] = {}
    audits: list[dict[str, Any]] = []
    for path in config["paths"]:  # Cosmic Ghost Rider is intentionally last.
        character, audit = build_character(path, path_chapters[path["id"]], physical_by_album)
        audit["sources"] = path_source_summaries[path["id"]]
        characters[path["id"]] = character
        audits.append(audit)
        write_json(DATA / "characters" / f"{path['id']}.json", character)
        log(
            f"{path['name']}: {character['coverage']['mappedChapters']}/"
            f"{character['coverage']['originalChapters']} capitoli, "
            f"{len(character['issues'])} albi italiani"
        )

    new_ids = {path["id"] for path in config["paths"]}
    overlap: dict[str, list[str]] = {}
    physical_paths: dict[str, list[str]] = {}
    for path_id, character in characters.items():
        for issue in character["issues"]:
            physical_paths.setdefault(issue["id"], []).append(path_id)
    for issue_id, paths in physical_paths.items():
        unique = sorted(set(paths))
        if len(unique) > 1:
            overlap[issue_id] = unique

    audit_payload = {
        "version": 1,
        "manifestVersion": MANIFEST_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": config["source"],
        "rules": config["rules"],
        "pathOrder": [path["id"] for path in config["paths"]],
        "summary": {
            "paths": len(config["paths"]),
            "uniqueUsSeries": len(unique_codes),
            "validUsSeries": len(series_results),
            "invalidUsSeries": len(source_errors),
            "uniqueItalianAlbums": len(physical_by_album),
            "reusedExistingAlbums": len(set(physical_by_album) & set(existing_by_album)),
            "newItalianAlbums": len(set(physical_by_album) - set(existing_by_album)),
            "crossPathPhysicalOverlaps": len(overlap),
        },
        "sourceErrors": source_errors,
        "albumErrors": album_errors,
        "overlaps": overlap,
        "paths": audits,
    }
    write_json(AUDIT_PATH, audit_payload, pretty=True)
    update_manifest(config, characters)
    update_hubs()
    write_logos(config)
    log(f"Audit scritto in {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
