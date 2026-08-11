#!/usr/bin/env python3
"""Harden collected-edition fetching against transient HTTP-200 database errors."""
from pathlib import Path

path = Path("scripts/build_editions_catalog.py")
text = path.read_text(encoding="utf-8")

old = '''def fetch(url: str, attempts: int = 4) -> str:
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
'''

new = '''def fetch(url: str, attempts: int = 6) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})
    transient_markers = (
        "Connessione MySQL fallita",
        "Lost connection to MySQL server",
        "Too many connections",
    )
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=45) as response:
                source = response.read().decode("utf-8", errors="replace")
            # ComicsBox can answer HTTP 200 with a database-error page.  Treat
            # that as a failed request; otherwise load_series() sees zero rows
            # and incorrectly concludes that pagination has ended.
            if any(marker.casefold() in source.casefold() for marker in transient_markers):
                raise RuntimeError(f"transient ComicsBox database response: {url}")
            return source
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt * 1.5)
    raise RuntimeError(url)
'''

if old in text:
    text = text.replace(old, new, 1)
elif "transient ComicsBox database response" not in text:
    raise SystemExit("fetch() anchor not found")

path.write_text(text, encoding="utf-8")
print("ComicsBox transient HTTP-200 database responses now retry instead of ending pagination.")
