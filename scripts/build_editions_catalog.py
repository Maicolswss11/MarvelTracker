#!/usr/bin/env python3
"""Build the Italian collected-editions catalog and conservative route coverage.

Metadata is imported from ComicsBox series indexes. Route coverage is inferred only
when a collected edition points to a first Italian publication already present in
MarvelTracker AND the edition title/series identifies the same reading path.
Existing manually curated coverage always wins.
"""
from __future__ import annotations

import html
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
USER_AGENT = "MarvelTracker collected-editions maintenance/1.1"

SERIES = {
    "MVNWCOL_P": {"name": "Marvel Collection II", "publisher": "Panini Comics", "format": "Cartonato"},
    "MARVELMUST": {"name": "Marvel Must-Have", "publisher": "Panini Comics", "format": "Cartonato"},
    "MARVDELUXE": {"name": "Marvel Deluxe", "publisher": "Panini Comics", "format": "Cartonato"},
    "MAROMNIB": {"name": "Marvel Omnibus", "publisher": "Panini Comics", "format": "Omnibus cartonato"},
    "MCOLL_M": {"name": "Marvel Collection I", "publisher": "Panini Comics", "format": "Brossurato"},
    "MINTGRDDEV": {"name": "Marvel Integrale: Daredevil", "publisher": "Panini Comics", "format": "Integrale"},
    "MINTGRXMEN": {"name": "Marvel Integrale: Gli Incredibili X-Men", "publisher": "Panini Comics", "format": "Integrale"},
    "MISMJMDM": {"name": "Marvel Integrale: Spider-Man di J.M. DeMatteis", "publisher": "Panini Comics", "format": "Integrale"},
    "MARVINTSM": {"name": "Marvel Integrale: Spider-Man di Todd McFarlane", "publisher": "Panini Comics", "format": "Integrale"},
    "MARINTTH": {"name": "Marvel Integrale: Thor di Jason Aaron", "publisher": "Panini Comics", "format": "Integrale"},
    "DSTRANGEORO": {"name": "Doctor Strange (Serie Oro)", "publisher": "Panini Comics", "format": "Brossurato"},
    "ULF4D_M": {"name": "Ultimate Fantastic Four Deluxe", "publisher": "Marvel Italia", "format": "Brossurato"},
}

PATH_ALIASES = {
    "ironman": ["iron man"],
    "thor": ["thor"],
    "cap": ["capitan america", "captain america"],
    "hulk": ["hulk"],
    "spiderman": ["spider-man", "spider man", "uomo ragno", "amazing spider-man"],
    "avengers": ["avengers", "vendicatori"],
    "xmen": ["x-men", "x men"],
    "antman": ["ant-man", "ant man"],
    "wasp": ["wasp"],
    "scarletwitch": ["scarlet witch", "wanda maximoff"],
    "vision": ["visione", "vision"],
    "wonderman": ["wonder man"],
    "hawkeye": ["occhio di falco", "hawkeye"],
    "blackwidow": ["vedova nera", "black widow"],
    "blackpanther": ["pantera nera", "black panther"],
    "captainmarvel": ["captain marvel"],
    "shehulk": ["she-hulk", "she hulk"],
    "fantastic-four": ["fantastici quattro", "fantastic four"],
    "doctor-strange": ["doctor strange", "dottor strange", "dr. strange", "dr strange"],
    "house-of-m": ["house of m"],
    "civil-war": ["civil war"],
    "secret-invasion": ["secret invasion"],
    "siege": ["assedio", "siege"],
    "fear-itself": ["fear itself"],
    "avengers-vs-xmen": ["avengers vs x-men", "avengers vs. x-men", "avx"],
    "infinity": ["infinity"],
    "civil-war-ii": ["civil war ii", "civil war 2"],
    "secret-empire": ["secret empire"],
    "war-of-the-realms": ["war of the realms", "guerra dei regni"],
    "absolute-carnage": ["absolute carnage"],
    "empyre": ["empyre"],
    "king-in-black": ["king in black"],
    "blood-hunt": ["blood hunt"],
    "infinity-gauntlet": ["infinity gauntlet", "guanto dell\'infinito"],
    "judgment-day": ["a.x.e. judgment day", "a.x.e.", "judgment day"],
    "ultimate-spiderman-classic": ["ultimate spider-man", "ultimate spiderman"],
    "ultimate-xmen": ["ultimate x-men", "ultimate x men"],
    "ultimates": ["ultimates"],
    "ultimate-fantastic-four": ["ultimate fantastic four", "ultimate fantastici quattro"],
    "ultimate-ironman": ["ultimate iron man"],
    "ultimate-wolverine": ["ultimate wolverine"],
    "ultimate-new-spiderman": ["ultimate spider-man", "ultimate spiderman"],
    "ultimate-new-black-panther": ["ultimate black panther", "ultimate pantera nera"],
    "ultimate-new-xmen": ["ultimate x-men", "ultimate x men"],
    "ultimate-new-ultimates": ["ultimates"],
    "ultimate-new-wolverine": ["ultimate wolverine"],
    "hulk-classic-corno": ['hulk', 'incredible hulk'],
    "daredevil": ['daredevil', 'devil'],
    "wolverine-616": ['wolverine'],
    "venom": ['venom'],
    "doctor-doom": ['doctor doom', 'dottor destino', 'doom', 'destino'],
}

DETAIL_HINTS = tuple(sorted({alias for values in PATH_ALIASES.values() for alias in values} | {
    "house of m", "civil war", "secret invasion", "assedio", "siege", "fear itself",
    "avengers vs x-men", "infinity", "secret wars", "world war hulk", "planet hulk",
    "extremis", "ragnarok", "spider-verse", "absolute carnage", "king in black", "a.x.e.", "judgment day",
}, key=len, reverse=True))

class SeriesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self.in_row = False
        self.in_cell = False
        self.cells: list[str] = []
        self.text: list[str] = []
        self.href = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.cells = []
            self.href = ""
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.text = []
        elif tag == "a" and self.in_cell and not self.href:
            href = attrs.get("href") or ""
            if "/albo/" in href or "albo/" in href:
                self.href = href

    def handle_data(self, data):
        if self.in_cell:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.cells.append(" ".join("".join(self.text).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.href and len(self.cells) >= 4:
                self.rows.append({
                    "number": self.cells[0].strip().rstrip("* "),
                    "label": self.cells[1].strip().rstrip("* "),
                    "title": self.cells[2].strip(),
                    "date": self.cells[3].strip(),
                    "href": self.href,
                })


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("–", "-").replace("’", "'")
    return " ".join(value.split())


def fetch(url: str, attempts: int = 4) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt * 1.5)
    raise RuntimeError(url)


def album_code(href: str) -> str:
    match = re.search(r"(?:^|/)albo/([^/?#]+)", href)
    return unquote(match.group(1)) if match else ""


def edition_id(code: str) -> str:
    match = re.match(r"^(.+)_([0-9]+[A-Za-z]?)$", code)
    if not match:
        return code
    prefix, suffix = match.groups()
    num = re.match(r"^(\d+)([A-Za-z]?)$", suffix)
    assert num
    return f"{prefix}:{int(num.group(1))}{num.group(2).upper()}"


def cover_url(code: str) -> str:
    return f"https://www.comicsbox.it/cover/{code}.jpg"


def load_series(code: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for offset in range(0, 1000, 50):
        source = fetch(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}")
        parser = SeriesParser()
        parser.feed(source)
        fresh = 0
        for row in parser.rows:
            acode = album_code(row["href"])
            if not acode or acode in seen:
                continue
            seen.add(acode)
            row["code"] = acode
            rows.append(row)
            fresh += 1
        if fresh == 0:
            break
    return rows


def first_italian_codes(source: str) -> list[str]:
    result: list[str] = []
    for marker in re.finditer(r"Prima\s+pubblicazione\s+in\s+Italia", source, flags=re.I):
        snippet = source[marker.start(): marker.start() + 1800]
        match = re.search(r"href=[\"'][^\"']*?(?:/|^)albo/([^\"'?#/]+)", snippet, flags=re.I)
        if not match:
            match = re.search(r"href=[\"'](?:https?://[^\"']+)?/?albo/([^\"'?#/]+)", snippet, flags=re.I)
        if match:
            code = unquote(html.unescape(match.group(1)))
            if code not in result:
                result.append(code)
    return result


def candidates_for_title(title: str) -> set[str]:
    text = norm(title)
    candidates = {path for path, aliases in PATH_ALIASES.items() if any(alias in text for alias in aliases)}
    if "civil war ii" in text or "civil war 2" in text:
        candidates.discard("civil-war")
    if any(x in text for x in ("infinity gauntlet", "guanto dell\'infinito", "infinity wars", "infinity countdown")):
        candidates.discard("infinity")
    if "ultimate" in text:
        candidates = {path for path in candidates if path.startswith("ultimate") or path == "ultimates"}
    else:
        candidates = {path for path in candidates if not path.startswith("ultimate") and path != "ultimates"}
    return candidates


def should_fetch_detail(title: str) -> bool:
    text = norm(title)
    return any(hint in text for hint in DETAIL_HINTS)


def natural_number(value: object) -> tuple[int, str]:
    match = re.match(r"^(\d+)(.*)$", str(value or ""))
    return (int(match.group(1)), match.group(2)) if match else (10**9, str(value or ""))


def main() -> None:
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    existing_payload = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    existing = {item["id"]: item for item in existing_payload.get("editions", [])}

    code_to_issue: dict[str, dict] = {}
    for issue in catalog.get("issues", []):
        code = album_code(issue.get("url", ""))
        if code:
            code_to_issue[code] = issue

    imported: list[dict] = []
    for series_code, meta in SERIES.items():
        rows = load_series(series_code)
        print(f"{meta['name']}: {len(rows)} volumi")
        for row in rows:
            eid = edition_id(row["code"])
            old = existing.get(eid, {})
            imported.append({
                "id": eid,
                "name": row["title"] or row["label"] or f"{meta['name']} #{row['number']}",
                "series": meta["name"],
                "number": row["number"],
                "publisher": meta["publisher"],
                "format": meta["format"],
                "date": row["date"],
                "cover": cover_url(row["code"]),
                "url": f"https://www.comicsbox.it/albo/{row['code']}",
                "contents": old.get("contents", []),
                "coverage": old.get("coverage", []),
                **({"coverageSource": old["coverageSource"]} if old.get("coverageSource") else {}),
                "source": "ComicsBox",
                "sourceCode": row["code"],
            })

    to_scan = [
        item for item in imported
        if not item.get("coverage") and should_fetch_detail(f"{item['series']} {item['name']}")
    ]
    print(f"Schede da analizzare per copertura: {len(to_scan)}")

    def scan(item: dict) -> tuple[str, list[str]]:
        source = fetch(item["url"])
        return item["id"], first_italian_codes(source)

    scanned: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(scan, item): item["id"] for item in to_scan}
        for index, future in enumerate(as_completed(futures), 1):
            eid = futures[future]
            try:
                key, codes = future.result()
                scanned[key] = codes
            except Exception as error:
                print(f"WARN {eid}: {error}")
            if index % 50 == 0:
                print(f"Analizzate {index}/{len(to_scan)} schede")

    for item in imported:
        if item.get("coverage"):
            continue
        codes = scanned.get(item["id"], [])
        if not codes:
            continue
        identity = f"{item['series']} {item['name']}"
        candidates = candidates_for_title(identity)
        matched = [code_to_issue[code] for code in codes if code in code_to_issue]
        if not matched:
            continue

        route_union = {path for issue in matched for path in issue.get("paths", [])}
        if not candidates and len(route_union) == 1:
            candidates = set(route_union)

        by_path: dict[str, list[str]] = {}
        for issue in matched:
            for path in issue.get("paths", []):
                if path in candidates:
                    by_path.setdefault(path, []).append(issue["id"])

        item["coverage"] = [
            {"path": path, "issueIds": list(dict.fromkeys(ids)), "label": item["name"]}
            for path, ids in sorted(by_path.items()) if ids
        ]
        if item["coverage"]:
            item["coverageSource"] = "auto:first-italian-publication"

    imported_ids = {item["id"] for item in imported}
    for eid, item in existing.items():
        if eid not in imported_ids:
            imported.append(item)

    imported.sort(key=lambda item: (norm(item.get("series", "")), natural_number(item.get("number")), norm(item.get("name", ""))))
    auto_covered = sum(1 for item in imported if item.get("coverageSource") == "auto:first-italian-publication")
    payload = {
        "version": 2,
        "generatedFrom": "ComicsBox collected-edition indexes",
        "series": list(SERIES.keys()),
        "total": len(imported),
        "autoCovered": auto_covered,
        "editions": imported,
    }
    (DATA / "editions.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Edizioni: {len(imported)} · coperture automatiche: {auto_covered}")


if __name__ == "__main__":
    main()
