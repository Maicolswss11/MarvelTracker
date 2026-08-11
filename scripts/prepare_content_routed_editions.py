#!/usr/bin/env python3
"""Upgrade alternative-edition matching from title-level to USA-content-level routing."""
from pathlib import Path

path = Path("scripts/build_editions_catalog.py")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"anchor not found: {label}")
    text = text.replace(old, new, 1)


replace_once(
    "import unicodedata\nfrom concurrent.futures import ThreadPoolExecutor, as_completed\n",
    "import unicodedata\nfrom collections import defaultdict\nfrom concurrent.futures import ThreadPoolExecutor, as_completed\n",
    "defaultdict import",
)
replace_once(
    "from urllib.request import Request, urlopen\n\nROOT = Path(__file__).resolve().parents[1]\n",
    "from urllib.request import Request, urlopen\n\nimport build_cosmic_supernatural_expansion as legacy\n\nROOT = Path(__file__).resolve().parents[1]\n",
    "legacy import",
)

old_parser = '''def first_italian_codes(source: str) -> list[str]:
    result: list[str] = []
    for marker in re.finditer(r"Prima\\s+pubblicazione\\s+in\\s+Italia", source, flags=re.I):
        snippet = source[marker.start(): marker.start() + 1800]
        match = re.search(r"href=[\\\"'][^\\\"']*?(?:/|^)albo/([^\\\"'?#/]+)", snippet, flags=re.I)
        if not match:
            match = re.search(r"href=[\\\"'](?:https?://[^\\\"']+)?/?albo/([^\\\"'?#/]+)", snippet, flags=re.I)
        if match:
            code = unquote(html.unescape(match.group(1)))
            if code not in result:
                result.append(code)
    return result
'''
new_parser = '''def _linked_album_codes(fragment: str) -> list[str]:
    result: list[str] = []
    for match in re.finditer(
        r'href=["\\\'][^"\\\']*?(?:/|^)albo/([^"\\\'?#/]+)',
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
    for marker in re.finditer(r"Prima\\s+pubblicazione\\s+in\\s+Italia", source, flags=re.I):
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
'''
replace_once(old_parser, new_parser, "first Italian parser")

old_natural = '''def natural_number(value: object) -> tuple[int, str]:
    match = re.match(r"^(\\d+)(.*)$", str(value or ""))
    return (int(match.group(1)), match.group(2)) if match else (10**9, str(value or ""))


def main() -> None:
'''
new_natural = '''def natural_number(value: object) -> tuple[int, str]:
    match = re.match(r"^(\\d+)(.*)$", str(value or ""))
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
'''
replace_once(old_natural, new_natural, "exact reading routes")

replace_once(
    '''    imported: list[dict] = []
''',
    '''    exact_routes, exact_paths = exact_reading_routes()

    imported: list[dict] = []
''',
    "route initialization",
)

old_scan_filter = '''    to_scan = [
        item for item in imported
        if (not item.get("coverage") or item.get("coverageSource") == "auto:first-italian-publication")
        and should_fetch_detail(f"{item['series']} {item['name']}")
    ]
'''
new_scan_filter = '''    # Content-level routing cannot depend on a collection title naming the
    # character. Scan every non-manual imported edition; e.g. an X-Men omnibus
    # may be a valid Magik/Cable/Wolverine alternative without saying so in its title.
    to_scan = [
        item for item in imported
        if not item.get("coverage") or item.get("coverageSource") == "auto:first-italian-publication"
    ]
'''
replace_once(old_scan_filter, new_scan_filter, "scan all non-manual editions")

old_scan = '''    def scan(item: dict) -> tuple[str, list[str]]:
        source = fetch(item["url"])
        return item["id"], first_italian_codes(source)

    scanned: dict[str, list[str]] = {}
'''
new_scan = '''    def scan(item: dict) -> tuple[str, list[tuple[str, str]]]:
        source = fetch(item["url"])
        return item["id"], first_italian_pairs(source)

    scanned: dict[str, list[tuple[str, str]]] = {}
'''
replace_once(old_scan, new_scan, "pair scan")

old_mapping = '''        codes = scanned.get(item["id"], [])
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
        for coverage in baseline:
            path_id = coverage.get("path")
            if path_id and coverage.get("issueIds"):
                by_path.setdefault(path_id, []).extend(coverage["issueIds"])
        for issue in matched:
            for path_id in issue.get("paths", []):
                if path_id in candidates:
                    by_path.setdefault(path_id, []).append(issue["id"])
'''
new_mapping = '''        pairs = scanned.get(item["id"], [])
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
'''
replace_once(old_mapping, new_mapping, "content-routed coverage")

path.write_text(text, encoding="utf-8")
print("Alternative-edition matcher upgraded to USA-content-level routing.")
