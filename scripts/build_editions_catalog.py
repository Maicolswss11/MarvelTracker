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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

import build_cosmic_supernatural_expansion as legacy

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
    "black-cat": ['black cat', 'gatta nera', 'felicia hardy'],
    "quicksilver": ['quicksilver', 'pietro maximoff'],
    "falcon": ['falcon', 'sam wilson'],
    "winter-soldier": ['winter soldier', "soldato d'inverno", 'bucky barnes'],
    "war-machine": ['war machine', 'macchina da guerra', 'james rhodes', 'rhodey'],
    "hercules": ['hercules', 'ercole'],
    "spider-woman": ['spider-woman', 'spider woman', 'donna ragno', 'jessica drew'],
    "sentry": ['sentry', 'robert reynolds'],
    "luke-cage": ['luke cage', 'power man'],
    "iron-fist": ['iron fist', "pugno d'acciaio"],
    "jessica-jones": ['jessica jones', 'alias'],
    "punisher": ['punisher', 'punitore', 'frank castle'],
    "moon-knight": ['moon knight', 'cavaliere della luna', 'marc spector'],
    "elektra": ['elektra', 'elektra natchios'],
    "deadpool": ['deadpool', 'wade wilson'],
    "cable": ['cable', 'nathan summers'],
    "magik": ['magik', 'illyana rasputin', 'illyana'],
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


def _linked_album_codes(fragment: str) -> list[str]:
    result: list[str] = []
    for match in re.finditer(
        r'href=["\'][^"\']*?(?:/|^)albo/([^"\'?#/]+)',
        fragment,
        flags=re.I,
    ):
        code = unquote(html.unescape(match.group(1)))
        if code not in result:
            result.append(code)
    return result


def first_italian_pairs(source: str) -> list[tuple[str, str]]:
    """Return (USA story code, first Italian physical issue code) pairs.

    ComicsBox collection pages place the source-USA issue immediately before
    each ``Prima pubblicazione in Italia`` marker.  Keeping that identity is
    essential: one Italian physical issue can contain several USA stories that
    belong to different MarvelTracker reading paths.
    """
    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for marker in re.finditer(r"Prima\s+pubblicazione\s+in\s+Italia", source, flags=re.I):
        before = source[max(0, marker.start() - 5000):marker.start()]
        after = source[marker.start(): marker.start() + 1800]
        before_codes = _linked_album_codes(before)
        after_codes = _linked_album_codes(after)
        if not after_codes:
            continue
        usa_code = before_codes[-1] if before_codes else ""
        italian_code = after_codes[0]
        pair = (usa_code, italian_code)
        if pair not in seen:
            seen.add(pair)
            result.append(pair)
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


def exact_reading_routes() -> tuple[dict[tuple[str, str], set[tuple[str, str]]], set[str]]:
    """Index (USA content, Italian album) -> (path, physical issue id).

    This mirrors MarvelTracker's editorial invariant:
        physical Italian issue -> USA contents -> path-local readingStep
    """
    manifest = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    routes: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    exact_paths: set[str] = set()
    for meta in manifest.get("characters", []):
        path_id = meta.get("id", "")
        data_path = meta.get("data", "")
        if not path_id or not data_path:
            continue
        try:
            character = legacy.unpack_character(path_id, data_path)
        except Exception as error:
            print(f"WARN reading-route {path_id}: {error}")
            continue
        for issue in character.get("issues", []):
            step = issue.get("readingStep") if isinstance(issue.get("readingStep"), dict) else {}
            if step.get("pathId") != path_id:
                continue
            physical_code = album_code(issue.get("url", ""))
            content_ids = [code for code in step.get("contentIds", []) if code]
            issue_id = issue.get("id", "")
            if not physical_code or not content_ids or not issue_id:
                continue
            exact_paths.add(path_id)
            for content_id in content_ids:
                routes[(content_id, physical_code)].add((path_id, issue_id))
    print(f"Routing esatto: {len(routes)} coppie contenuto/albo · {len(exact_paths)} percorsi")
    return routes, exact_paths


def main() -> None:
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    existing_payload = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    existing = {item["id"]: item for item in existing_payload.get("editions", [])}

    code_to_issue: dict[str, dict] = {}
    for issue in catalog.get("issues", []):
        code = album_code(issue.get("url", ""))
        if code:
            code_to_issue[code] = issue

    exact_routes, exact_paths = exact_reading_routes()

    imported: list[dict] = []
    for series_code, meta in SERIES.items():
        rows = load_series(series_code)
        print(f"{meta['name']}: {len(rows)} volumi")
        for row in rows:
            eid = edition_id(row["code"])
            old = existing.get(eid, {})
            auto_generated = old.get("coverageSource") == "auto:first-italian-publication"
            # Preserve verified automatic coverage as a monotonic baseline.
            preserved_coverage = old.get("coverage", [])
            preserved_source = old.get("coverageSource", "")
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
                "coverage": preserved_coverage,
                **({"coverageSource": preserved_source} if preserved_source else {}),
                "source": "ComicsBox",
                "sourceCode": row["code"],
            })

    # Content-level routing cannot depend on a collection title naming the
    # character. Scan every non-manual imported edition; e.g. an X-Men omnibus
    # may be a valid Magik/Cable/Wolverine alternative without saying so in its title.
    to_scan = [
        item for item in imported
        if not item.get("coverage") or item.get("coverageSource") == "auto:first-italian-publication"
    ]
    print(f"Schede da analizzare per copertura: {len(to_scan)}")

    def scan(item: dict) -> tuple[str, list[tuple[str, str]]]:
        source = fetch(item["url"])
        return item["id"], first_italian_pairs(source)

    scanned: dict[str, list[tuple[str, str]]] = {}
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
        is_auto = item.get("coverageSource") == "auto:first-italian-publication"
        if item.get("coverage") and not is_auto:
            continue
        baseline = item.get("coverage", []) if is_auto else []
        pairs = scanned.get(item["id"], [])
        if not pairs:
            continue
        codes = list(dict.fromkeys(italian_code for _, italian_code in pairs if italian_code))
        identity = f"{item['series']} {item['name']}"
        candidates = candidates_for_title(identity)
        matched = [code_to_issue[code] for code in codes if code in code_to_issue]

        by_path: dict[str, list[str]] = {}
        for coverage in baseline:
            path_id = coverage.get("path")
            if path_id and coverage.get("issueIds"):
                by_path.setdefault(path_id, []).extend(coverage["issueIds"])

        # Exact route: the collected edition must contain the same USA story
        # selected by that path's readingStep on the cited Italian physical issue.
        for usa_code, italian_code in pairs:
            if not usa_code or not italian_code:
                continue
            for path_id, issue_id in exact_routes.get((usa_code, italian_code), set()):
                by_path.setdefault(path_id, []).append(issue_id)

        # Backward-compatible fallback only for legacy paths that do not expose
        # readingStep/contentIds yet. Never override exact paths with title inference.
        if matched:
            route_union = {
                path_id
                for issue in matched
                for path_id in issue.get("paths", [])
                if path_id not in exact_paths
            }
            if not candidates and len(route_union) == 1:
                candidates = set(route_union)
            for issue in matched:
                for path_id in issue.get("paths", []):
                    if path_id in exact_paths:
                        continue
                    if path_id in candidates:
                        by_path.setdefault(path_id, []).append(issue["id"])

        merged_coverage = [
            {"path": path_id, "issueIds": list(dict.fromkeys(ids)), "label": item["name"]}
            for path_id, ids in sorted(by_path.items()) if ids
        ]
        if merged_coverage:
            item["coverage"] = merged_coverage
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
