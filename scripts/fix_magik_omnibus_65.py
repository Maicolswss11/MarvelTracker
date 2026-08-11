#!/usr/bin/env python3
"""Restore the verified Marvel Omnibus #65 alternative for Magik Play Book #3."""
import json
from pathlib import Path

path = Path("data/editions.json")
payload = json.loads(path.read_text(encoding="utf-8"))
editions = payload.setdefault("editions", [])

required = {
    "id": "MAROMNIB:65",
    "name": "Gli Incredibili X-Men, vol 3",
    "series": "Marvel Omnibus",
    "number": "65",
    "publisher": "Panini Comics",
    "format": "Omnibus cartonato",
    "date": "Ago 2018",
    "cover": "https://www.comicsbox.it/cover/MAROMNIB_065.jpg",
    "url": "https://www.comicsbox.it/albo/MAROMNIB_065",
    "contents": [],
    "coverage": [
        {
            "path": "magik",
            "issueIds": ["PB_PP:3"],
            "label": "Gli Incredibili X-Men, vol 3",
        }
    ],
    "coverageSource": "verified:comicsbox-content-route",
    "source": "ComicsBox",
    "sourceCode": "MAROMNIB_065",
}

item = next((entry for entry in editions if entry.get("id") == required["id"]), None)
if item is None:
    editions.append(required)
    item = required
else:
    for key, value in required.items():
        if key not in {"coverage", "coverageSource"}:
            item[key] = value
    by_path = {coverage.get("path"): coverage for coverage in item.get("coverage", []) if coverage.get("path")}
    magik = by_path.setdefault("magik", {"path": "magik", "issueIds": [], "label": required["name"]})
    magik["issueIds"] = list(dict.fromkeys([*magik.get("issueIds", []), "PB_PP:3"]))
    magik["label"] = required["name"]
    item["coverage"] = list(by_path.values())
    item["coverageSource"] = "verified:comicsbox-content-route"

# Keep deterministic ordering and metadata consistent with the catalog builder.
def natural_number(value):
    import re
    match = re.match(r"^(\d+)(.*)$", str(value or ""))
    return (int(match.group(1)), match.group(2)) if match else (10**9, str(value or ""))

editions.sort(key=lambda entry: (str(entry.get("series", "")).casefold(), natural_number(entry.get("number")), str(entry.get("name", "")).casefold()))
payload["total"] = len(editions)
path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("Verified alternative restored: MAROMNIB:65 -> magik/PB_PP:3")
