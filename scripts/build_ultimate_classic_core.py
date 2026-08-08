#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
import re
import time
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7500
USER_AGENT = "MarvelTracker Ultimate classic maintenance/1.0"
MANIFEST_VERSION = 10

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
MONTHS_IT = {
    "Jan": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
    "May": "Maggio", "Jun": "Giugno", "Jul": "Luglio", "Aug": "Agosto",
    "Sep": "Settembre", "Oct": "Ottobre", "Nov": "Novembre", "Dec": "Dicembre",
}

SERIES = {
    "ULSM_M": ("Ultimate Spider-Man (I)", "Panini Comics", 71),
    "ULTC_SM_M": ("Ultimate Comics Spider-Man", "Panini Comics", 37),
    "ULXM_M": ("Ultimate X-Men", "Panini Comics", 53),
    "ULTS_M": ("Ultimates (I)", "Marvel Italia", 43),
    "ULF4_M": ("Ultimate Fantastic Four", "Marvel Italia", 32),
    "ULTCM_M": ("Ultimate Comics", "Panini Comics", 28),
    "UCAV_M": ("Ultimate Comics Avengers", "Panini Comics", 28),
}

SERIES_PRIORITY = {
    "ULSM_M": 10,
    "ULXM_M": 20,
    "ULTS_M": 30,
    "ULF4_M": 40,
    "ULTC_SM_M": 50,
    "UCAV_M": 60,
    "ULTCM_M": 70,
}


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
        elif tag == "a" and self.in_cell:
            href = attrs.get("href") or ""
            if "/albo/" in href and not self.href:
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
            if len(self.cells) >= 4 and self.href:
                match = re.search(r"\d+", self.cells[0])
                if match:
                    self.rows.append({
                        "n": match.group(0),
                        "name": self.cells[1].rstrip("* "),
                        "title": self.cells[2],
                        "date": self.cells[3],
                        "href": self.href,
                    })


def fetch_url(url: str, attempts: int = 5) -> str:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as response:
                source = response.read().decode("utf-8", errors="replace")
            if "Connessione MySQL fallita" in source:
                raise RuntimeError("ComicsBox database temporarily unavailable")
            return source
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Impossibile leggere {url}: {last}")


def fetch_series(code: str, expected: int) -> dict[int, dict[str, str]]:
    records: dict[int, dict[str, str]] = {}
    # Finestre sovrapposte: alcune serie ComicsBox contengono speciali/asterischi
    # che possono spostare una riga tra due pagine.
    for offset in range(0, expected + 90, 45):
        parser = SeriesParser()
        parser.feed(fetch_url(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}"))
        if not parser.rows:
            if offset == 0:
                raise RuntimeError(f"{code}: indice vuoto")
            break
        before = len(records)
        for row in parser.rows:
            n = int(row["n"])
            if 1 <= n <= expected:
                records[n] = row
        if len(records) >= expected:
            break
        if len(records) == before and offset > expected:
            break
    missing = [n for n in range(1, expected + 1) if n not in records]
    if missing:
        raise RuntimeError(f"{code}: numeri mancanti {missing}")
    return records


def italian_date(value: str) -> str:
    result = value
    for short, full in MONTHS_IT.items():
        result = re.sub(rf"\b{short}\b", full, result)
    return result


def date_key(value: str) -> tuple[int, int, int]:
    month_match = re.search(r"\b(" + "|".join(MONTHS) + r")\b", value)
    year_match = re.search(r"(?:19|20)\d{2}", value)
    day_match = re.match(r"\s*(\d{1,2})\b", value)
    year = int(year_match.group(0)) if year_match else 9999
    month = MONTHS.get(month_match.group(1), 12) if month_match else 12
    day = int(day_match.group(1)) if day_match else 15
    return year, month, day


def ultimate_era(date: str) -> tuple[str, str]:
    year, month, _ = date_key(date)
    if year <= 2002:
        return "Nascita dell'Universo Ultimate", "Spider-Man e X-Men fondano la nuova continuità Terra-1610"
    if year <= 2004:
        return "Espansione — Ultimates e Fantastic Four", "L'universo si allarga e le linee iniziano a incrociarsi"
    if year <= 2008:
        return "Universo condiviso — grandi crossover", "Ultimate War, Ultimate Six, Galactus e le grandi saghe del periodo classico"
    if year == 2009:
        return "Ultimatum", "La catastrofe che chiude la prima grande era della Terra-1610"
    if year <= 2011:
        return "Ultimate Comics — ricostruzione", "Dopo Ultimatum l'universo cambia volto e prepara una nuova generazione"
    if year <= 2013:
        return "Miles / Divisi cadiamo / Uniti vinciamo", "Miles Morales e la terza era dell'Universo Ultimate"
    if year == 2014:
        return "Cataclisma", "Galactus minaccia la Terra-1610 e ridefinisce ancora una volta il suo status quo"
    return "Verso Secret Wars / Ultimate End", "Gli ultimi anni della Terra-1610 prima dell'incursione e di Battleworld"


def path_era(path_id: str, series_id: str, n: int, date: str) -> tuple[str, str]:
    if path_id == "ultimate-universe":
        return ultimate_era(date)
    if path_id == "ultimate-spiderman-classic":
        if series_id == "ULSM_M":
            if n <= 20: return "Peter Parker — origini", "Poteri, responsabilità e primi grandi nemici"
            if n <= 45: return "Peter Parker — mondo in espansione", "La serie entra pienamente nell'Universo Ultimate condiviso"
            if n <= 60: return "Clone Saga e maturazione", "La fase più ambiziosa della prima serie"
            if n <= 70: return "Ultimatum", "La catastrofe travolge New York"
            return "Requiem", "Epilogo della prima serie e dei suoi sopravvissuti"
        if series_id == "ULTCM_M": return "Ultimate Fallout", "Il lutto per Peter e la nascita del nuovo Spider-Man"
        if n <= 13: return "Peter Parker — ultima fase", "Il rilancio Ultimate Comics conduce alla morte di Peter"
        if n <= 29: return "Miles Morales", "Miles raccoglie l'eredità di Spider-Man"
        if n <= 35: return "Miles Morales — verso Secret Wars", "Gli ultimi archi della Terra-1610"
        return "Ultimate End", "Il ponte diretto verso Secret Wars e Battleworld"
    if path_id == "ultimate-xmen":
        if series_id == "ULXM_M" and n <= 17: return "Millar / Tomorrow People", "La fondazione degli X-Men Ultimate"
        if series_id == "ULXM_M" and n <= 35: return "Weapon X / Return of the King", "Il mondo mutante si espande e si radicalizza"
        if series_id == "ULXM_M" and n <= 51: return "Vaughan / Kirkman / Coleite", "La lunga fase centrale della prima serie"
        if series_id in {"ULXM_M", "ULSM_M"}: return "Ultimatum / Requiem", "La fine della prima generazione mutante"
        if series_id == "ULTCM_M" and n <= 9: return "Ultimate X", "I superstiti mutanti dopo Ultimatum"
        return "Ultimate Comics X-Men", "Kitty Pryde, Riserva X e la nuova nazione mutante"
    if path_id == "ultimates":
        if series_id == "ULTS_M" and n <= 14: return "Millar / Hitch — nascita degli Ultimates", "La squadra governativa che ridefinisce i Vendicatori"
        if series_id == "ULTS_M" and n <= 25: return "Ultimate Six / Galactus", "La squadra diventa il centro dell'universo condiviso"
        if series_id == "ULTS_M" and n <= 40: return "Ultimates 2 / 3 e grandi crisi", "Tradimenti, guerra e disgregazione"
        if series_id == "ULTS_M": return "Ultimatum", "La fine della prima era degli Ultimates"
        if series_id == "UCAV_M" and n <= 12: return "Ultimate Avengers", "Le squadre di Fury e lo scontro con i New Ultimates"
        if series_id == "ULTCM_M": return "Thor / Cap / New Ultimates", "Miniserie di ricostruzione post-Ultimatum"
        return "Hickman / Ultimate Comics The Ultimates", "La Repubblica sta bruciando, Divided We Fall e Cataclysm"
    if path_id == "ultimate-fantastic-four":
        if series_id == "ULSM_M": return "Requiem", "Epilogo dei Fantastic Four dopo Ultimatum"
        if n <= 9: return "Origini / Doom / Zona N", "La nascita della versione Ultimate della Prima Famiglia"
        if n <= 18: return "Crossover / Namor / Presidente Thor", "La squadra entra nel cuore dell'Universo Ultimate"
        if n <= 26: return "God War / Silver Surfer", "La fase cosmica della serie"
        return "Thanos / Salem / Ultimatum", "Gli ultimi archi prima della dissoluzione della squadra"
    return ultimate_era(date)


def make_issue(series_id: str, n: int, row: dict[str, str], path_id: str) -> dict:
    series_name, publisher, _ = SERIES[series_id]
    code = row["href"].split("/albo/")[-1].split("?")[0]
    era, era_sub = path_era(path_id, series_id, n, row["date"])
    instruction = "Leggi l'albo completo e prosegui con la tappa successiva del percorso."
    if series_id == "ULSM_M" and n == 71:
        instruction = "REQU IEM CONDIVISO: questo albo contiene gli epiloghi di Spider-Man, X-Men e Fantastic Four dopo Ultimatum."
    elif series_id == "ULTCM_M" and n in {10, 11}:
        instruction = "ULTIMATE FALLOUT: leggi prima di iniziare stabilmente l'era di Miles Morales."
    elif series_id == "ULTC_SM_M" and n == 14:
        instruction = "CAMBIO DI PROTAGONISTA: da qui Miles Morales diventa il nuovo Spider-Man Ultimate."
    elif series_id == "ULTC_SM_M" and n >= 36:
        instruction = "ULTIMATE END: ponte diretto con Secret Wars/Battleworld."
    elif series_id == "ULTS_M" and n >= 41:
        instruction = "ULTIMATUM: albo evento centrale. Segui la sequenza del percorso master se stai leggendo tutto l'universo."
    return {
        "id": f"{series_id}:{n}",
        "seq": 0,
        "seriesId": series_id,
        "series": series_name,
        "publisher": publisher,
        "n": n,
        "name": f"{series_name} #{n}",
        "title": row["title"] or "Albo dell'Universo Ultimate",
        "date": italian_date(row["date"]),
        "dateQuality": "indice",
        "era": era,
        "eraSub": era_sub,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "required": True,
        "skip": False,
        "instruction": instruction,
        "coverSource": "ComicsBox",
        "_sortDate": date_key(row["date"]),
        "_sortPriority": SERIES_PRIORITY[series_id],
    }


def ordered(issues: list[dict]) -> list[dict]:
    result = []
    for seq, issue in enumerate(issues, 1):
        issue = deepcopy(issue)
        issue["seq"] = seq
        issue.pop("_sortDate", None)
        issue.pop("_sortPriority", None)
        result.append(issue)
    return result


def by_publication(issues: list[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for issue in issues:
        unique[issue["id"]] = issue
    sorted_issues = sorted(unique.values(), key=lambda issue: (issue["_sortDate"], issue["_sortPriority"], issue["n"]))
    return ordered(sorted_issues)


def build_character(path_id: str, name: str, subtitle: str, accent: str, description: str, issues: list[dict], series: list[dict]) -> dict:
    issues = ordered(issues)
    return {
        "id": path_id,
        "name": name,
        "subtitle": subtitle,
        "accent": accent,
        "start": f"{issues[0]['name']} — {issues[0]['date']}",
        "end": f"{issues[-1]['name']} — {issues[-1]['date']}",
        "description": description,
        "timelineMode": True,
        "series": series,
        "archives": [],
        "totalRequired": len(issues),
        "availableTotal": len(issues),
        "issues": issues,
    }


def pack(character: dict) -> None:
    cid = character["id"]
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    for old in (DATA / "b64").glob(f"{cid}-*.b64"):
        old.unlink()
    parts = [encoded[i:i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]
    sources = []
    for index, part in enumerate(parts, 1):
        rel = f"data/b64/{cid}-{index:02d}.b64"
        (ROOT / rel).write_text(part, encoding="ascii")
        sources.append(rel)
    (DATA / "encoded" / f"{cid}.json").write_text(
        json.dumps({"encoding": "gzip-base64-parts", "sources": sources}, separators=(",", ":")), encoding="utf-8"
    )
    stub = {k: v for k, v in character.items() if k not in {"issues", "availableTotal"}}
    stub["issueSources"] = [f"data/encoded/{cid}.json"]
    (DATA / "characters" / f"{cid}.json").write_text(json.dumps(stub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{character['name']}: {len(character['issues'])} albi, {len(parts)} parti")


def series_meta(ids: list[str], ranges: dict[str, str]) -> list[dict]:
    result = []
    for sid in ids:
        name, publisher, expected = SERIES[sid]
        result.append({"id": sid, "name": name, "publisher": publisher, "range": ranges.get(sid, f"#1–{expected}")})
    return result


def write_logos() -> None:
    logos = {
        "ultimate-universe.svg": ('#f0c14b', '<path d="M32 39h16v31c0 12 6 18 16 18s16-6 16-18V39h16v32c0 22-12 34-32 34S32 93 32 71V39Z" fill="#f7f7f7"/>'),
        "ultimate-xmen.svg": ('#d9d9e8', '<path d="M36 34h17l12 19 12-19h17L74 64l21 31H78L65 75 51 95H34l22-31-20-30Z" fill="#f4f4f8"/>'),
        "ultimates.svg": ('#7cb7ff', '<path d="M64 27 96 98H80l-7-17H52l-7 17H29l31-71h4Zm1 26-8 17h16l-8-17Z" fill="#f4f8ff"/>'),
        "ultimate-fantastic-four.svg": ('#66b8ff', '<path d="M71 28 37 70v14h31v15h15V84h12V69H83V28H71Zm-3 41H54l14-18v18Z" fill="#f4f9ff"/>'),
    }
    for filename, (accent, mark) in logos.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" rx="26" fill="#090b11"/><circle cx="64" cy="64" r="48" fill="none" stroke="{accent}" stroke-width="6"/>{mark}</svg>'
        (ROOT / "assets" / "heroes" / filename).write_text(svg, encoding="utf-8")


def main() -> None:
    indexes = {sid: fetch_series(sid, meta[2]) for sid, meta in SERIES.items()}
    base = {
        sid: {n: make_issue(sid, n, row, "ultimate-universe") for n, row in rows.items()}
        for sid, rows in indexes.items()
    }

    # Spider-Man: correggiamo il vecchio percorso inserendo Ultimate Fallout.
    spider = []
    spider += [make_issue("ULSM_M", n, indexes["ULSM_M"][n], "ultimate-spiderman-classic") for n in range(1, 72)]
    spider += [make_issue("ULTC_SM_M", n, indexes["ULTC_SM_M"][n], "ultimate-spiderman-classic") for n in range(1, 14)]
    spider += [make_issue("ULTCM_M", n, indexes["ULTCM_M"][n], "ultimate-spiderman-classic") for n in (10, 11)]
    spider += [make_issue("ULTC_SM_M", n, indexes["ULTC_SM_M"][n], "ultimate-spiderman-classic") for n in range(14, 38)]

    xmen = [make_issue("ULXM_M", n, indexes["ULXM_M"][n], "ultimate-xmen") for n in range(1, 54)]
    xmen.append(make_issue("ULSM_M", 71, indexes["ULSM_M"][71], "ultimate-xmen"))
    xmen += [make_issue("ULTCM_M", n, indexes["ULTCM_M"][n], "ultimate-xmen") for n in range(7, 10)]
    xmen += [make_issue("ULTCM_M", n, indexes["ULTCM_M"][n], "ultimate-xmen") for n in range(12, 29)]

    ultimates = [make_issue("ULTS_M", n, indexes["ULTS_M"][n], "ultimates") for n in range(1, 44)]
    bridge = [make_issue("ULTCM_M", n, indexes["ULTCM_M"][n], "ultimates") for n in range(1, 8)]
    bridge += [make_issue("UCAV_M", n, indexes["UCAV_M"][n], "ultimates") for n in range(1, 29)]
    # Dopo Ultimatum l'ordine delle due collane va seguito per data di uscita italiana.
    bridge = sorted(bridge, key=lambda issue: (issue["_sortDate"], issue["_sortPriority"], issue["n"]))
    ultimates += bridge

    uff = [make_issue("ULF4_M", n, indexes["ULF4_M"][n], "ultimate-fantastic-four") for n in range(1, 33)]
    uff.append(make_issue("ULSM_M", 71, indexes["ULSM_M"][71], "ultimate-fantastic-four"))

    master_raw = []
    for sid, (_, _, expected) in SERIES.items():
        master_raw += [base[sid][n] for n in range(1, expected + 1)]
    master = by_publication(master_raw)
    # by_publication ha già assegnato seq; build_character lo riassegna in modo stabile.

    characters = [
        build_character(
            "ultimate-universe", "Ultimate Universe", "Terra-1610 · percorso completo delle linee principali", "#f0c14b",
            "Percorso master del vecchio Universo Ultimate: unisce le principali pubblicazioni italiane di Spider-Man, X-Men, Ultimates e Fantastic Four, più le collane Ultimate Comics che tengono insieme la continuità dopo Ultimatum. L'ordine segue la pubblicazione italiana con priorità narrative stabili nei mesi condivisi, così puoi leggere Terra-1610 dall'inizio a Ultimate End senza saltare manualmente tra le testate.",
            master,
            series_meta(list(SERIES), {}),
        ),
        build_character(
            "ultimate-spiderman-classic", "Ultimate Spider-Man", "Peter Parker → Miles Morales · Terra-1610", "#f0c14b",
            "Percorso completo della linea italiana di Ultimate Spider-Man. Include ora Ultimate Fallout tra la morte di Peter Parker e l'affermazione di Miles Morales, quindi prosegue fino a Ultimate End/Secret Wars.",
            spider,
            series_meta(["ULSM_M", "ULTC_SM_M", "ULTCM_M"], {"ULTCM_M": "#10–11 (Ultimate Fallout)"}),
        ),
        build_character(
            "ultimate-xmen", "Ultimate X-Men", "Mutanti di Terra-1610", "#d9d9e8",
            "Percorso degli X-Men del vecchio Universo Ultimate: la serie italiana originale, il Requiem condiviso post-Ultimatum e il rilancio Ultimate Comics fino a Cataclisma.",
            xmen,
            series_meta(["ULXM_M", "ULSM_M", "ULTCM_M"], {"ULSM_M": "#71 (Requiem)", "ULTCM_M": "#7–9, #12–28"}),
        ),
        build_character(
            "ultimates", "Ultimates", "Vendicatori di Terra-1610", "#7cb7ff",
            "Percorso degli Ultimates dalla serie classica di Millar/Hitch a Ultimatum, poi Ultimate Avengers, Thor/Cap/New Ultimates e la fase Hickman fino a Cataclisma.",
            ultimates,
            series_meta(["ULTS_M", "UCAV_M", "ULTCM_M"], {"ULTCM_M": "#1–7"}),
        ),
        build_character(
            "ultimate-fantastic-four", "Ultimate Fantastic Four", "La Prima Famiglia di Terra-1610", "#66b8ff",
            "Percorso della linea italiana Ultimate Fantastic Four dalle origini al collasso della squadra durante Ultimatum, con il Requiem conclusivo condiviso nell'albo Ultimate Spider-Man #71.",
            uff,
            series_meta(["ULF4_M", "ULSM_M"], {"ULSM_M": "#71 (Fantastic Four Requiem)"}),
        ),
    ]

    for character in characters:
        pack(character)

    manifest_path = DATA / "characters.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    replacement_ids = {character["id"] for character in characters}
    existing = [entry for entry in manifest["characters"] if entry["id"] not in replacement_ids]
    meta_by_id = {
        "ultimate-universe": ("Ultimate Universe", "Terra-1610 · percorso completo", "universe", "#f0c14b", "assets/heroes/ultimate-universe.svg"),
        "ultimate-spiderman-classic": ("Ultimate Spider-Man", "Peter Parker → Miles Morales · Terra-1610", "character", "#f0c14b", "assets/heroes/ultimate-spiderman.svg"),
        "ultimate-xmen": ("Ultimate X-Men", "Mutanti di Terra-1610", "team", "#d9d9e8", "assets/heroes/ultimate-xmen.svg"),
        "ultimates": ("Ultimates", "Vendicatori di Terra-1610", "team", "#7cb7ff", "assets/heroes/ultimates.svg"),
        "ultimate-fantastic-four": ("Ultimate Fantastic Four", "La Prima Famiglia di Terra-1610", "team", "#66b8ff", "assets/heroes/ultimate-fantastic-four.svg"),
    }
    for character in characters:
        name, subtitle, type_, accent, logo = meta_by_id[character["id"]]
        existing.append({
            "id": character["id"], "name": name, "subtitle": subtitle, "type": type_,
            "primaryHub": "ultimate-classic", "hubs": ["ultimate-classic"], "accent": accent, "logo": logo,
            "data": f"data/characters/{character['id']}.json", "start": character["start"], "end": character["end"],
            "totalRequired": character["totalRequired"],
        })
    manifest["characters"] = existing
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    hubs_path = DATA / "hubs.json"
    hubs = json.loads(hubs_path.read_text(encoding="utf-8"))
    hub = next(item for item in hubs["hubs"] if item["id"] == "ultimate-classic")
    hub.pop("status", None)
    hub["subtitle"] = "Terra-1610 · un universo completo e finito da seguire"
    hub["featuredPath"] = "ultimate-universe"
    hub["groups"] = [
        {"id": "master", "label": "Segui tutto l'universo", "paths": ["ultimate-universe"]},
        {"id": "core", "label": "Linee principali", "paths": ["ultimate-spiderman-classic", "ultimate-xmen", "ultimates", "ultimate-fantastic-four"]},
        {"id": "future", "label": "Eventi e miniserie", "paths": []},
    ]
    hubs_path.write_text(json.dumps(hubs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_logos()

    print("Ultimate classico core generato:")
    for character in characters:
        print(f"- {character['name']}: {character['totalRequired']} tappe")


if __name__ == "__main__":
    main()
