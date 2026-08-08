#!/usr/bin/env python3
"""Build personal Italian reading paths for Avengers-centric characters.

The builder uses the existing Avengers timeline as the backbone. It scans each
physical Avengers issue on ComicsBox, keeps only issues where the requested
character is actually listed, reuses the same physical issue id so ownership is
shared globally, and then merges character-specific Italian volumes in narrative
order.

Routes generated:
- Ant-Man (Hank Pym / Scott Lang)
- Wasp (Janet Van Dyne / Nadia Van Dyne)
- Scarlet Witch (Wanda Maximoff)
- Visione
- Wonder Man (Simon Williams)
"""

from __future__ import annotations

import base64
import copy
import gzip
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500
USER_AGENT = "MarvelTracker data maintenance/4.0"

MONTHS_IT = {
    "Jan": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
    "May": "Maggio", "Jun": "Giugno", "Jul": "Luglio", "Aug": "Agosto",
    "Sep": "Settembre", "Oct": "Ottobre", "Nov": "Novembre", "Dec": "Dicembre",
}
MONTH_ORDER = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

ROUTES = {
    "antman": {
        "name": "Ant-Man",
        "subtitle": "Hank Pym / Scott Lang",
        "accent": "#e45b5f",
        "logo": "assets/heroes/antman.svg",
        "description": "Percorso italiano di Ant-Man: origini classiche, apparizioni nei Vendicatori e serie moderne di Hank Pym e Scott Lang.",
        "notice": "Il percorso segue il mantello di Ant-Man attraverso Hank Pym e Scott Lang. Gli albi condivisi con i Vendicatori mantengono lo stesso stato Recuperato.",
    },
    "wasp": {
        "name": "Wasp",
        "subtitle": "Janet Van Dyne / Nadia Van Dyne",
        "accent": "#f3c64f",
        "logo": "assets/heroes/wasp.svg",
        "description": "Percorso italiano di Wasp: dalle origini di Janet Van Dyne alle incarnazioni moderne e alle storie condivise con i Vendicatori.",
        "notice": "Le fondamenta classiche seguono Janet Van Dyne; il percorso moderno include anche Nadia Van Dyne quando presente nelle pubblicazioni italiane selezionate.",
    },
    "scarletwitch": {
        "name": "Scarlet Witch",
        "subtitle": "Wanda Maximoff",
        "accent": "#e34366",
        "logo": "assets/heroes/scarlet-witch.svg",
        "description": "Percorso italiano di Wanda Maximoff: Visione e Scarlet Witch, apparizioni nei Vendicatori e serie soliste moderne.",
        "notice": "La timeline integra le storie personali di Wanda con gli albi dei Vendicatori in cui è effettivamente presente, evitando di duplicare l'albo fisico.",
    },
    "vision": {
        "name": "Visione",
        "subtitle": "Vision",
        "accent": "#7ccf8a",
        "logo": "assets/heroes/vision.svg",
        "description": "Percorso italiano di Visione: storie con Scarlet Witch, apparizioni nei Vendicatori e la serie di Tom King.",
        "notice": "Gli albi Visione & Scarlet Witch sono condivisi con il percorso di Wanda; Recuperato è globale, mentre Letto resta indipendente per percorso.",
    },
    "wonderman": {
        "name": "Wonder Man",
        "subtitle": "Simon Williams",
        "accent": "#b979e8",
        "logo": "assets/heroes/wonder-man.svg",
        "description": "Percorso italiano di Wonder Man: fondamenti classici, apparizioni nei Vendicatori e miniserie personali di Simon Williams.",
        "notice": "Alcune storie personali di Wonder Man sono arrivate in volume italiano molti anni dopo l'uscita USA: qui sono collocate nella posizione narrativa, non in quella di pubblicazione italiana.",
    },
}

SERIES_META = {
    "MMW_M": ("Marvel Masterworks", "Marvel Italia / Panini Comics"),
    "MRVHEROS": ("Marvel Heroes", "Panini Comics"),
    "MVNWCOL_P": ("Marvel Collection II", "Panini Comics"),
    "DSTRANGE_P": ("Doctor Strange", "Panini Comics"),
    "VSWPC": ("Avengers - Visione & Scarlet Witch", "Panini Comics"),
    "MARVGEEKS": ("Marvel Geeks", "Panini Comics"),
    "MARVELVERSE": ("Marvel-Verse", "Panini Comics"),
}


class SeriesTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._in_row = False
        self._in_cell = False
        self._cells: list[str] = []
        self._text: list[str] = []
        self._href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr":
            self._in_row = True
            self._in_cell = False
            self._cells = []
            self._href = ""
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._text = []
        elif tag == "a" and self._in_cell:
            href = attrs_dict.get("href") or ""
            if "/albo/" in href and not self._href:
                self._href = href

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._cells.append(" ".join("".join(self._text).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if len(self._cells) >= 4 and self._href:
                match = re.search(r"\d+", self._cells[0])
                if match:
                    self.rows.append({
                        "n": match.group(0),
                        "name": self._cells[1].rstrip("* "),
                        "title": self._cells[2],
                        "date": self._cells[3],
                        "href": self._href,
                    })


class IssuePageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.tokens: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and len(text) <= 120:
            self.tokens.append(text)
        if self._href is not None and text:
            self._link_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = " ".join(" ".join(self._link_text).split())
            if text:
                self.links.append((self._href, text))
            self._href = None
            self._link_text = []


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def fetch_url(url: str, attempts: int = 5) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as response:
                source = response.read().decode("utf-8", errors="replace")
            if "Connessione MySQL fallita" in source:
                raise RuntimeError("ComicsBox database temporarily unavailable")
            return source
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(1.25 * attempt)
    raise RuntimeError(f"Impossibile leggere {url}: {last_error}")


def parse_issue(url: str) -> IssuePageParser:
    parser = IssuePageParser()
    parser.feed(fetch_url(url))
    return parser


def fetch_series_page(code: str, offset: int) -> list[dict[str, str]]:
    source = fetch_url(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}")
    parser = SeriesTableParser()
    parser.feed(source)
    return parser.rows


def fetch_all_series(code: str, max_pages: int = 20) -> dict[int, dict[str, str]]:
    records: dict[int, dict[str, str]] = {}
    for page in range(max_pages):
        rows = fetch_series_page(code, page * 50)
        if not rows:
            break
        before = len(records)
        for row in rows:
            records[int(row["n"])] = row
        if len(records) == before or len(rows) < 50:
            break
    if not records:
        raise RuntimeError(f"{code}: indice ComicsBox vuoto")
    return records


def italian_date(value: str) -> str:
    result = value
    for short, full in MONTHS_IT.items():
        result = re.sub(rf"\b{short}\b", full, result)
    return result


def date_parts(value: str) -> tuple[int, int]:
    text = normalize(value)
    year_match = re.search(r"(?:19|20)\d{2}", text)
    year = int(year_match.group(0)) if year_match else 9999
    month = next((number for name, number in MONTH_ORDER.items() if name in text), 12)
    return year, month


def unpack_character(character_id: str) -> dict:
    spec = json.loads((DATA / "encoded" / f"{character_id}.json").read_text(encoding="utf-8"))
    encoded = "".join((ROOT / source).read_text(encoding="ascii").strip() for source in spec["sources"])
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def pack_character(character: dict) -> None:
    character_id = character["id"]
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    b64_dir = DATA / "b64"
    b64_dir.mkdir(parents=True, exist_ok=True)
    for old_part in b64_dir.glob(f"{character_id}-*.b64"):
        old_part.unlink()
    sources: list[str] = []
    for index, part in enumerate(parts, 1):
        relative = f"data/b64/{character_id}-{index:02d}.b64"
        (ROOT / relative).write_text(part, encoding="ascii")
        sources.append(relative)
    (DATA / "encoded" / f"{character_id}.json").write_text(
        json.dumps({"encoding": "gzip-base64-parts", "sources": sources}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"{character['name']}: {len(character['issues'])} tappe, {len(raw):,} byte, {len(parts)} parti")


def person_matches(route_id: str, href: str, text: str) -> bool:
    if "personaggio/" not in href:
        return False
    h = normalize(href)
    t = normalize(text)
    hay = f"{h} {t}"

    if route_id == "antman":
        keys = ("ant man", "hank pym", "henry pym", "scott lang", "pym henry", "lang scott", "yellowjacket")
        return any(key in hay for key in keys)
    if route_id == "wasp":
        keys = ("wasp", "janet van dyne", "nadia van dyne", "nadia pym", "van dyne janet", "van dyne nadia")
        return any(key in hay for key in keys)
    if route_id == "scarletwitch":
        return any(key in hay for key in ("scarlet witch", "wanda maximoff", "maximoff wanda"))
    if route_id == "vision":
        # Deliberately avoid Viv Vision / Virginia Vision and unrelated uses of the word.
        return t in {"vision", "visione"} or h.endswith("personaggio vision") or h.endswith("personaggio visione")
    if route_id == "wonderman":
        return any(key in hay for key in ("wonder man", "wonderman", "simon williams", "williams simon"))
    return False


def scan_avengers_issue(issue: dict) -> tuple[str, set[str]]:
    parser = parse_issue(issue["url"])
    matched: set[str] = set()
    for href, text in parser.links:
        for route_id in ROUTES:
            if person_matches(route_id, href, text):
                matched.add(route_id)
    return issue["id"], matched


def copy_shared_issue(base: dict, route_name: str) -> dict:
    issue = copy.deepcopy(base)
    issue["required"] = True
    issue["skip"] = False
    issue.pop("future", None)
    issue.pop("kind", None)
    issue.pop("displayNumber", None)
    issue["sharedWith"] = ["Vendicatori"]
    issue["instruction"] = (
        f"Albo condiviso con il percorso Vendicatori: per {route_name} leggi le storie in cui il personaggio è coinvolto, "
        "poi prosegui con la tappa successiva."
    )
    year, month = date_parts(issue["date"])
    issue["_sort"] = (year, month, 40, int(base.get("seq") or 9999))
    return issue


def row_issue(
    series_id: str,
    series_name: str,
    publisher: str,
    row: dict[str, str],
    number: int,
    *,
    sort_year: int | None = None,
    sort_month: int | None = None,
    era: str,
    era_sub: str,
    instruction: str,
    shared_with: list[str] | None = None,
    chronology_insert: bool = False,
) -> dict:
    date = italian_date(row["date"])
    real_year, real_month = date_parts(date)
    issue = {
        "id": f"{series_id}:{number}",
        "seq": 0,
        "seriesId": series_id,
        "series": series_name,
        "publisher": publisher,
        "n": number,
        "name": f"{series_name} #{number}",
        "title": row["title"] or "Volume dedicato al personaggio",
        "date": date,
        "era": era,
        "eraSub": era_sub,
        "cover": f"https://www.comicsbox.it/cover/{series_id}_{number:03d}.jpg",
        "url": urljoin("https://www.comicsbox.it", row["href"]),
        "required": True,
        "skip": False,
        "instruction": instruction,
        "_sort": (sort_year or real_year, sort_month or real_month, 20, number),
    }
    if shared_with:
        issue["sharedWith"] = shared_with
    if chronology_insert:
        issue["kind"] = "chronologyInsert"
        issue["editorialLabel"] = f"{series_name} #{number}"
    return issue


def synthetic_issue(
    series_id: str,
    series_name: str,
    publisher: str,
    number: int,
    title: str,
    date: str,
    *,
    sort_year: int,
    sort_month: int,
    era: str,
    era_sub: str,
    instruction: str,
    shared_with: list[str] | None = None,
    chronology_insert: bool = False,
) -> dict:
    issue = {
        "id": f"{series_id}:{number}",
        "seq": 0,
        "seriesId": series_id,
        "series": series_name,
        "publisher": publisher,
        "n": number,
        "name": f"{series_name} #{number}",
        "title": title,
        "date": date,
        "era": era,
        "eraSub": era_sub,
        "cover": f"https://www.comicsbox.it/cover/{series_id}_{number:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{series_id}_{number:03d}",
        "required": True,
        "skip": False,
        "instruction": instruction,
        "_sort": (sort_year, sort_month, 10, number),
    }
    if shared_with:
        issue["sharedWith"] = shared_with
    if chronology_insert:
        issue["kind"] = "chronologyInsert"
        issue["editorialLabel"] = f"{series_name} #{number}"
    return issue


def contains_source_story(parser: IssuePageParser, phrase: str) -> bool:
    target = normalize(phrase)
    for href, text in parser.links:
        if "/albo/" in href and target in normalize(text):
            return True
    return False


def selected_doctor_strange_wanda(rows: dict[int, dict[str, str]]) -> list[dict]:
    selected: list[dict] = []
    numbers = sorted(rows)
    print(f"Analizzo {len(numbers)} numeri di Doctor Strange per la serie solista di Scarlet Witch…")

    def inspect(number: int) -> tuple[int, bool]:
        url = urljoin("https://www.comicsbox.it", rows[number]["href"])
        parser = parse_issue(url)
        return number, contains_source_story(parser, "Scarlet Witch")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(inspect, number) for number in numbers]
        for future in as_completed(futures):
            number, matched = future.result()
            if matched:
                row = rows[number]
                selected.append(row_issue(
                    "DSTRANGE_P", "Doctor Strange", "Panini Comics", row, number,
                    era="Scarlet Witch — James Robinson",
                    era_sub="La serie solista di Wanda pubblicata nell'antologico Doctor Strange",
                    instruction="Albo antologico: leggi il segmento di Scarlet Witch e poi prosegui con la tappa successiva.",
                ))
    return selected


def series_summary(issues: list[dict], avengers_series_meta: dict[str, dict]) -> list[dict]:
    ordered_ids: list[str] = []
    for issue in issues:
        if issue["seriesId"] not in ordered_ids:
            ordered_ids.append(issue["seriesId"])
    result: list[dict] = []
    for sid in ordered_ids:
        xs = [issue for issue in issues if issue["seriesId"] == sid]
        existing = avengers_series_meta.get(sid)
        name = existing["name"] if existing else SERIES_META.get(sid, (xs[0]["series"], xs[0]["publisher"]))[0]
        publisher = existing["publisher"] if existing else SERIES_META.get(sid, (xs[0]["series"], xs[0]["publisher"]))[1]
        numbers = sorted({issue["n"] for issue in xs})
        if len(numbers) == 1:
            range_text = f"#{numbers[0]}"
        elif numbers == list(range(numbers[0], numbers[-1] + 1)):
            range_text = f"#{numbers[0]}–{numbers[-1]}"
        else:
            range_text = f"{len(numbers)} albi selezionati"
        years = sorted({date_parts(issue["date"])[0] for issue in xs if date_parts(issue["date"])[0] < 9999})
        years_text = str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}" if years else ""
        result.append({"id": sid, "name": name, "publisher": publisher, "range": range_text, "years": years_text})
    return result


def icon_svg(label: str, subtitle: str, accent: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
<rect width="128" height="128" rx="28" fill="#080d13"/>
<rect x="6" y="6" width="116" height="116" rx="24" fill="none" stroke="{accent}" stroke-width="4"/>
<text x="64" y="69" text-anchor="middle" font-family="Arial,sans-serif" font-size="38" font-weight="900" fill="{accent}">{label}</text>
<text x="64" y="94" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" font-weight="700" fill="#dbe5ed">{subtitle}</text>
</svg>'''


def write_icons() -> None:
    assets = ROOT / "assets" / "heroes"
    assets.mkdir(parents=True, exist_ok=True)
    icons = {
        "antman.svg": ("AM", "ANT-MAN", ROUTES["antman"]["accent"]),
        "wasp.svg": ("W", "WASP", ROUTES["wasp"]["accent"]),
        "scarlet-witch.svg": ("SW", "WANDA", ROUTES["scarletwitch"]["accent"]),
        "vision.svg": ("V", "VISION", ROUTES["vision"]["accent"]),
        "wonder-man.svg": ("WM", "SIMON", ROUTES["wonderman"]["accent"]),
    }
    for filename, args in icons.items():
        (assets / filename).write_text(icon_svg(*args), encoding="utf-8")


def add_special_material(route_issues: dict[str, list[dict]]) -> None:
    print("Carico gli indici delle collane dedicate…")
    mmw = fetch_all_series("MMW_M", 6)
    heroes = fetch_all_series("MRVHEROS", 2)
    collections = fetch_all_series("MVNWCOL_P", 20)
    doctor_strange = fetch_all_series("DSTRANGE_P", 3)

    # ANT-MAN / WASP — classic foundations.
    for route_id in ("antman", "wasp"):
        route_name = ROUTES[route_id]["name"]
        route_issues[route_id].append(row_issue(
            "MMW_M", "Marvel Masterworks", "Marvel Italia", mmw[42], 42,
            sort_year=1962, sort_month=1,
            era="Origini classiche — Tales to Astonish",
            era_sub="Hank Pym, Ant-Man e la nascita del sodalizio con Wasp",
            instruction=f"Fondamenta classiche del percorso {route_name}: leggi il volume completo prima di entrare nella cronologia moderna.",
            shared_with=["Ant-Man", "Wasp"] if route_id in {"antman", "wasp"} else None,
            chronology_insert=True,
        ))
        route_issues[route_id].append(row_issue(
            "MMW_M", "Marvel Masterworks", "Marvel Italia", mmw[79], 79,
            sort_year=1964, sort_month=3,
            era="Origini classiche — Giant-Man & Wasp",
            era_sub="Giant-Man e le prime storie in solitaria di Wasp",
            instruction=f"Prosegui le fondamenta classiche di {route_name}; il volume precede le apparizioni moderne dei Vendicatori.",
            shared_with=["Ant-Man", "Wasp"],
            chronology_insert=True,
        ))

    # ANT-MAN — Nick Spencer and later minis.
    for number in sorted(n for n in heroes if 1 <= n <= 11):
        route_issues["antman"].append(row_issue(
            "MRVHEROS", "Marvel Heroes", "Panini Comics", heroes[number], number,
            era="Ant-Man — Nick Spencer",
            era_sub="Scott Lang tra Ant-Man e Astonishing Ant-Man",
            instruction="Leggi l'albo completo: fa parte del ciclo moderno di Scott Lang.",
        ))
    for number, story_year, era in (
        (320, 2020, "Ant-Man — Mondo Alveare"),
        (456, 2022, "Ant-Man — Ant-niversario"),
    ):
        if number in collections:
            route_issues["antman"].append(row_issue(
                "MVNWCOL_P", "Marvel Collection II", "Panini Comics", collections[number], number,
                sort_year=story_year,
                era=era,
                era_sub="Miniserie moderna di Ant-Man",
                instruction="Leggi il volume completo e poi rientra nella timeline condivisa con i Vendicatori.",
            ))

    # WASP — 2023 solo miniseries.
    if 496 in collections:
        route_issues["wasp"].append(row_issue(
            "MVNWCOL_P", "Marvel Collection II", "Panini Comics", collections[496], 496,
            sort_year=2023, sort_month=1,
            era="Wasp — Piccoli Mondi",
            era_sub="La miniserie moderna dedicata a Janet Van Dyne",
            instruction="Leggi il volume completo e poi prosegui con le successive apparizioni della timeline.",
        ))

    # WANDA + VISION — classic relationship blocks, represented with modern Italian editions.
    pair_classics = [
        synthetic_issue(
            "VSWPC", "Avengers - Visione & Scarlet Witch", "Panini Comics", 1,
            "Visione & Scarlet Witch", "Novembre 2020",
            sort_year=1982, sort_month=11,
            era="Visione & Scarlet Witch — origini della coppia",
            era_sub="Dalla storia del matrimonio alla prima miniserie Vision and the Scarlet Witch",
            instruction="Blocco classico della coppia: leggilo qui prima delle fasi moderne dei Vendicatori.",
            shared_with=["Scarlet Witch", "Visione"], chronology_insert=True,
        ),
        synthetic_issue(
            "MARVGEEKS", "Marvel Geeks", "Panini Comics", 16,
            "Visione e Scarlet: Un Anno nella Vita", "Maggio 2021",
            sort_year=1985, sort_month=10,
            era="Visione & Scarlet Witch — Un anno nella vita",
            era_sub="La seconda miniserie e i capitoli collegati dei Vendicatori della Costa Ovest",
            instruction="Leggi il volume come continuazione del blocco classico Visione/Scarlet Witch.",
            shared_with=["Scarlet Witch", "Visione"], chronology_insert=True,
        ),
    ]
    for route_id in ("scarletwitch", "vision"):
        route_issues[route_id].extend(copy.deepcopy(pair_classics))

    # WANDA — Scarlet Witch solo material in Doctor Strange plus modern collections.
    route_issues["scarletwitch"].extend(selected_doctor_strange_wanda(doctor_strange))
    wanda_collections = [
        (506, 2023, 1, "Scarlet Witch — L'Ultima Porta"),
        (566, 2023, 7, "Scarlet Witch — Magnum Opus"),
        (598, 2024, 2, "Scarlet Witch & Quicksilver"),
        (636, 2024, 6, "Scarlet Witch — Regina del Caos"),
        (673, 2025, 1, "Scarlet Witch — L'Ascesa di Amaranth"),
        (703, 2025, 5, "Visione & Scarlet Witch — nuova serie"),
    ]
    for number, year, month, era in wanda_collections:
        if number not in collections:
            continue
        route_issues["scarletwitch"].append(row_issue(
            "MVNWCOL_P", "Marvel Collection II", "Panini Comics", collections[number], number,
            sort_year=year, sort_month=month,
            era=era,
            era_sub="Fase contemporanea di Wanda Maximoff",
            instruction="Leggi il volume completo nella posizione narrativa indicata.",
            shared_with=["Visione"] if number == 703 else None,
        ))

    # VISION — Tom King and contemporary reunion with Wanda.
    for number, year, month, era in (
        (56, 2016, 1, "Visione — Tom King, parte 1"),
        (81, 2016, 7, "Visione — Tom King, parte 2"),
        (703, 2025, 5, "Visione & Scarlet Witch — nuova serie"),
    ):
        if number not in collections:
            continue
        route_issues["vision"].append(row_issue(
            "MVNWCOL_P", "Marvel Collection II", "Panini Comics", collections[number], number,
            sort_year=year, sort_month=month,
            era=era,
            era_sub="Percorso personale di Visione" if number != 703 else "Il ritorno della coppia Visione e Scarlet Witch",
            instruction="Leggi il volume completo nella posizione narrativa indicata.",
            shared_with=["Scarlet Witch"] if number == 703 else None,
        ))

    # WONDER MAN — a compact classic foundation plus the late Italian edition of his 2007 mini.
    route_issues["wonderman"].append(synthetic_issue(
        "MARVELVERSE", "Marvel-Verse", "Panini Comics", 45,
        "Wonder Man", "Novembre 2025",
        sort_year=1986, sort_month=3,
        era="Wonder Man — fondamenta classiche",
        era_sub="Selezione di storie classiche di Simon Williams",
        instruction="Volume di raccordo classico: leggilo qui per avere le fondamenta del personaggio prima della timeline moderna.",
        chronology_insert=True,
    ))
    if 693 in collections:
        route_issues["wonderman"].append(row_issue(
            "MVNWCOL_P", "Marvel Collection II", "Panini Comics", collections[693], 693,
            sort_year=2007, sort_month=2,
            era="Wonder Man — My Fair Super-Hero",
            era_sub="La miniserie del 2007, pubblicata in volume italiano successivamente",
            instruction="INSERTO CRONOLOGICO: l'edizione italiana è recente, ma le storie sono del 2007; leggila qui.",
            chronology_insert=True,
        ))


def dedupe_and_sequence(issues: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for issue in issues:
        existing = by_id.get(issue["id"])
        if existing is None:
            by_id[issue["id"]] = issue
            continue
        # Prefer dedicated metadata over a generic shared timeline copy if ever duplicated.
        if issue.get("kind") == "chronologyInsert" or issue["seriesId"] not in {"VEN_M", "IM_VEN", "THORVE_M", "IM_VEN2", "AVENGERS_M"}:
            by_id[issue["id"]] = issue
    result = sorted(by_id.values(), key=lambda issue: issue.get("_sort", (9999, 12, 99, 9999)))
    for seq, issue in enumerate(result, 1):
        issue["seq"] = seq
        issue.pop("_sort", None)
    return result


def make_character(route_id: str, issues: list[dict], avengers: dict) -> dict:
    cfg = ROUTES[route_id]
    issues = dedupe_and_sequence(issues)
    if not issues:
        raise RuntimeError(f"{route_id}: nessuna tappa generata")
    avengers_series_meta = {item["id"]: item for item in avengers.get("series", [])}
    first, last = issues[0], issues[-1]
    character = {
        "id": route_id,
        "name": cfg["name"],
        "subtitle": cfg["subtitle"],
        "accent": cfg["accent"],
        "start": f"{first['era']} — {first['title']}",
        "end": f"{last['name']} — {last['date']}",
        "description": cfg["description"],
        "timelineMode": True,
        "series": series_summary(issues, avengers_series_meta),
        "archives": [],
        "totalRequired": len(issues),
        "issues": issues,
    }
    return character


def write_stub(character: dict) -> None:
    stub = {key: value for key, value in character.items() if key != "issues"}
    stub["issueSources"] = [f"data/encoded/{character['id']}.json"]
    (DATA / "characters" / f"{character['id']}.json").write_text(
        json.dumps(stub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def update_manifest(characters: dict[str, dict]) -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = 4
    existing = {item["id"]: item for item in manifest["characters"]}
    for route_id, character in characters.items():
        cfg = ROUTES[route_id]
        entry = {
            "id": route_id,
            "name": cfg["name"],
            "subtitle": cfg["subtitle"],
            "accent": cfg["accent"],
            "logo": cfg["logo"],
            "data": f"data/characters/{route_id}.json",
            "start": character["start"],
            "end": character["end"],
            "totalRequired": character["totalRequired"],
        }
        existing[route_id] = entry
    canonical = ["ironman", "thor", "cap", "hulk", "spiderman", "avengers", "antman", "wasp", "scarletwitch", "vision", "wonderman"]
    manifest["characters"] = [existing[item_id] for item_id in canonical if item_id in existing]
    path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def patch_project_files() -> None:
    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    verify = verify.replace('assert.equal(manifest.version, 3, "Il manifest deve usare la versione cache v3");',
                            'assert.equal(manifest.version, 4, "Il manifest deve usare la versione cache v4");')
    verify_path.write_text(verify, encoding="utf-8")

    index_path = ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = index.replace("css/app.css?v=7", "css/app.css?v=8")
    index = index.replace("js/app.js?v=7", "js/app.js?v=8")
    index = index.replace("Reset personaggio", "Reset percorso")
    index_path.write_text(index, encoding="utf-8")

    css_path = ROOT / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    marker = "/* Avengers character paths v1 */"
    if marker not in css:
        css += "\n" + marker + "\n.homeHeroIcons{flex-wrap:wrap;row-gap:8px}.homeIntro .homeHeroIcons{max-width:620px}.homeCharacterGrid{grid-template-columns:repeat(auto-fit,minmax(185px,1fr))}\n"
    css_path.write_text(css, encoding="utf-8")

    app_path = ROOT / "js" / "app.js"
    app = app_path.read_text(encoding="utf-8")
    anchor = 'function renderNotices(){const id=activeCharacter,ns=[];'
    addition = 'function renderNotices(){const id=activeCharacter,ns=[];if(["antman","wasp","scarletwitch","vision","wonderman"].includes(id))ns.push(["Percorso personale + Vendicatori","Le tappe condivise riutilizzano lo stesso albo fisico del percorso Vendicatori: Recuperato è globale, mentre Letto rimane indipendente per questo percorso."]);'
    if anchor in app:
        app = app.replace(anchor, addition, 1)
    app_path.write_text(app, encoding="utf-8")

    rebuild_path = ROOT / "scripts" / "rebuild_character_data.py"
    rebuild = rebuild_path.read_text(encoding="utf-8")
    rebuild = rebuild.replace('manifest["version"] = 2', 'manifest["version"] = 4')
    rebuild_path.write_text(rebuild, encoding="utf-8")


def main() -> None:
    avengers = unpack_character("avengers")
    avengers_issues = [issue for issue in avengers["issues"] if not issue.get("future")]
    print(f"Analizzo {len(avengers_issues)} albi della timeline Vendicatori per i cinque personaggi…")

    matches: dict[str, set[str]] = {route_id: set() for route_id in ROUTES}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(scan_avengers_issue, issue) for issue in avengers_issues]
        for future in as_completed(futures):
            issue_id, route_ids = future.result()
            for route_id in route_ids:
                matches[route_id].add(issue_id)

    route_issues: dict[str, list[dict]] = {route_id: [] for route_id in ROUTES}
    for route_id, cfg in ROUTES.items():
        for issue in avengers_issues:
            if issue["id"] in matches[route_id]:
                route_issues[route_id].append(copy_shared_issue(issue, cfg["name"]))
        print(f"{cfg['name']}: {len(route_issues[route_id])} albi condivisi trovati nella timeline Vendicatori")

    add_special_material(route_issues)

    characters: dict[str, dict] = {}
    for route_id in ROUTES:
        character = make_character(route_id, route_issues[route_id], avengers)
        write_stub(character)
        pack_character(character)
        characters[route_id] = character

    update_manifest(characters)
    write_icons()
    patch_project_files()

    print("\nRiepilogo percorsi generati:")
    for route_id, character in characters.items():
        shared = sum(1 for issue in character["issues"] if "Vendicatori" in issue.get("sharedWith", []))
        print(f"- {character['name']}: {character['totalRequired']} tappe ({shared} condivise con Vendicatori)")


if __name__ == "__main__":
    main()
