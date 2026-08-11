#!/usr/bin/env python3
from pathlib import Path

path = Path("scripts/build_editions_catalog.py")
text = path.read_text(encoding="utf-8")

aliases = {
    "elektra": ["elektra", "elektra natchios"],
    "deadpool": ["deadpool", "wade wilson"],
    "cable": ["cable", "nathan summers"],
    "magik": ["magik", "illyana rasputin", "illyana"],
}
start = text.index("PATH_ALIASES = {")
end = text.index("\n}\n\nDETAIL_HINTS", start)
block = text[start:end]
additions = []
for path_id, values in aliases.items():
    if f'"{path_id}":' not in block:
        additions.append(f'    "{path_id}": [{", ".join(repr(v) for v in values)}],')
if additions:
    text = text[:end] + "\n" + "\n".join(additions) + text[end:]

old = '''            auto_generated = old.get("coverageSource") == "auto:first-italian-publication"
            preserved_coverage = [] if auto_generated else old.get("coverage", [])
            preserved_source = "" if auto_generated else old.get("coverageSource", "")
'''
new = '''            auto_generated = old.get("coverageSource") == "auto:first-italian-publication"
            # Preserve verified automatic coverage as a monotonic baseline.
            preserved_coverage = old.get("coverage", [])
            preserved_source = old.get("coverageSource", "")
'''
if old in text:
    text = text.replace(old, new, 1)

old = '''    to_scan = [
        item for item in imported
        if not item.get("coverage") and should_fetch_detail(f"{item['series']} {item['name']}")
    ]
'''
new = '''    to_scan = [
        item for item in imported
        if (not item.get("coverage") or item.get("coverageSource") == "auto:first-italian-publication")
        and should_fetch_detail(f"{item['series']} {item['name']}")
    ]
'''
if old in text:
    text = text.replace(old, new, 1)

old = '''    for item in imported:
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
'''
new = '''    for item in imported:
        is_auto = item.get("coverageSource") == "auto:first-italian-publication"
        if item.get("coverage") and not is_auto:
            continue
        baseline = item.get("coverage", []) if is_auto else []
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
        for coverage in baseline:
            path_id = coverage.get("path")
            if path_id and coverage.get("issueIds"):
                by_path.setdefault(path_id, []).extend(coverage["issueIds"])
        for issue in matched:
            for path_id in issue.get("paths", []):
                if path_id in candidates:
                    by_path.setdefault(path_id, []).append(issue["id"])

        merged_coverage = [
            {"path": path_id, "issueIds": list(dict.fromkeys(ids)), "label": item["name"]}
            for path_id, ids in sorted(by_path.items()) if ids
        ]
        if merged_coverage:
            item["coverage"] = merged_coverage
            item["coverageSource"] = "auto:first-italian-publication"
'''
if old in text:
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Alternative-edition matcher prepared with monotonic coverage.")
