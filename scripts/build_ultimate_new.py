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
USER_AGENT = "MarvelTracker Ultimate 6160 maintenance/1.0"
MANIFEST_VERSION = 11

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
MONTHS_IT = {
    "Jan": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
    "May": "Maggio", "Jun": "Giugno", "Jul": "Luglio", "Aug": "Agosto",
    "Sep": "Settembre", "Oct": "Ottobre", "Nov": "Novembre", "Dec": "Dicembre",
}

# Edizioni italiane Panini. I conteggi rappresentano gli albi fisici effettivamente
# catalogati/pubblicati in Italia alla data del builder.
SERIES = {
    "ULTIMATIN": ("Ultimate Invasion", "Panini Comics", 4),
    "ULTIMATEUN": ("Ultimate Universe", "Panini Comics", 2),
    "ULT_SM3": ("Ultimate Spider-Man (II)", "Panini Comics", 24),
    "ULTBLCKPIT": ("Ultimate Black Panther", "Panini Comics", 24),
    "ULT_XMEN3": ("Ultimate X-Men (II)", "Panini Comics", 24),
    "ULTIMATESP": ("Ultimates (II)", "Panini Comics", 24),
    "ULTMTWOLVP": ("Ultimate Wolverine", "Panini Comics", 16),
    "USMINCRSN": ("Ultimate Spider-Man: Incursion", "Panini Comics", 5),
    "ULTMTENDG": ("Ultimate Endgame", "Panini Comics", 3),
}

SERIES_PRIORITY = {
    "ULTIMATIN": 5,
    "ULTIMATEUN": 10,
    "ULT_SM3": 20,
    "ULTBLCKPIT": 30,
    "ULT_XMEN3": 40,
    "ULTIMATESP": 50,
    "ULTMTWOLVP": 60,
    "USMINCRSN": 70,
    "ULTMTENDG": 80,
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


def era_for(series_id: str, n: int) -> tuple[str, str]:
    if series_id == "ULTIMATIN":
        return "La nascita di Terra-6160", "Il Creatore riscrive la storia e nasce il nuovo Universo Ultimate"
    if series_id == "ULTIMATEUN" and n == 1:
        return "La nascita di Terra-6160", "Dopo Ultimate Invasion, Tony Stark prepara il ritorno degli eroi"
    if series_id == "ULTIMATEUN" and n == 2:
        return "Un anno dopo", "Il Consiglio del Creatore reagisce mentre il conto alla rovescia continua"
    if series_id in {"ULT_SM3", "ULTBLCKPIT", "ULT_XMEN3", "ULTIMATESP"}:
        if n <= 6:
            return "Anno Uno — il mondo si risveglia", "I nuovi eroi emergono in un mondo costruito dal Creatore"
        if n <= 12:
            return "Anno Uno — resistenza", "Le linee si espandono e il Consiglio del Creatore entra sempre più in gioco"
        if n <= 18:
            return "Anno Due — conto alla rovescia", "Manca sempre meno al ritorno del Creatore"
        return "Anno Due — verso Endgame", "Le ultime mosse prima del ritorno del Creatore"
    if series_id == "ULTMTWOLVP":
        if n <= 6:
            return "Anno Due — il Soldato d'Inverno", "La Repubblica Eurasiatica scatena la sua arma mutante"
        if n <= 12:
            return "Anno Due — liberare Wolverine", "La resistenza mutante tenta di spezzare il condizionamento"
        return "Anno Due — verso Endgame", "La guerra con i Rasputin conduce direttamente alla resa dei conti"
    if series_id == "USMINCRSN":
        return "Incursion", "Miles Morales di Terra-616 attraversa Terra-6160 e incontra le sue linee principali"
    if series_id == "ULTMTENDG":
        return "Ultimate Endgame", "Il Creatore ritorna: tutte le linee convergono nella battaglia finale"
    return "Nuovo Ultimate", "Terra-6160"


def instruction_for(series_id: str, n: int) -> str:
    if series_id == "ULTIMATIN":
        return "FONDAZIONE: leggi prima di qualunque altra serie di Terra-6160."
    if series_id == "ULTIMATEUN" and n == 1:
        return "EPILOGO DI ULTIMATE INVASION: introduce la nuova linea Ultimate e prepara Spider-Man, Black Panther, X-Men e Ultimates."
    if series_id == "ULTIMATEUN" and n == 2:
        return "ONE YEAR IN: speciale centrale tra il primo e il secondo anno; include anche il prologo di Ultimate Wolverine."
    if series_id == "USMINCRSN" and n == 1:
        return "INCURSION: include il preludio FCBD e apre il crossover di Miles Morales attraverso Terra-6160."
    if series_id == "ULTMTENDG":
        return "ENDGAME: evento conclusivo. Nel percorso master è intrecciato con la fase finale delle serie regolari."
    return "Leggi l'albo completo e prosegui con la tappa successiva."


def make_issue(series_id: str, n: int, row: dict[str, str]) -> dict:
    series_name, publisher, _ = SERIES[series_id]
    code = row["href"].split("/albo/")[-1].split("?")[0]
    era, era_sub = era_for(series_id, n)
    return {
        "id": f"{series_id}:{n}",
        "seq": 0,
        "seriesId": series_id,
        "series": series_name,
        "publisher": publisher,
        "n": n,
        "name": f"{series_name} #{n}",
        "title": row["title"] or "Albo del nuovo Universo Ultimate",
        "date": italian_date(row["date"]),
        "dateQuality": "indice",
        "era": era,
        "eraSub": era_sub,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "required": True,
        "skip": False,
        "instruction": instruction_for(series_id, n),
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


def publication_order(issues: list[dict]) -> list[dict]:
    unique = {issue["id"]: issue for issue in issues}
    return sorted(unique.values(), key=lambda i: (i["_sortDate"], i["_sortPriority"], i["n"]))


def build_character(path_id: str, name: str, subtitle: str, accent: str, description: str, issues: list[dict], series_ids: list[str]) -> dict:
    issues = ordered(issues)
    series = []
    for sid in series_ids:
        sname, publisher, expected = SERIES[sid]
        series.append({"id": sid, "name": sname, "publisher": publisher, "range": f"#1–{expected}"})
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


def write_logo(filename: str, accent: str, text: str) -> None:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
<rect width="128" height="128" rx="26" fill="#090b11"/>
<circle cx="64" cy="64" r="48" fill="none" stroke="{accent}" stroke-width="6"/>
<text x="64" y="73" text-anchor="middle" font-family="Arial,sans-serif" font-size="27" font-weight="900" fill="#f7f7f7">{text}</text>
</svg>'''
    (ROOT / "assets" / "heroes" / filename).write_text(svg, encoding="utf-8")


def main() -> None:
    indexes = {sid: fetch_series(sid, spec[2]) for sid, spec in SERIES.items()}
    issue_maps = {
        sid: {n: make_issue(sid, n, row) for n, row in rows.items()}
        for sid, rows in indexes.items()
    }

    invasion = [issue_maps["ULTIMATIN"][n] for n in range(1, 5)]
    universe_specials = [issue_maps["ULTIMATEUN"][n] for n in range(1, 3)]
    spider = [issue_maps["ULT_SM3"][n] for n in range(1, 25)]
    black_panther = [issue_maps["ULTBLCKPIT"][n] for n in range(1, 25)]
    xmen = [issue_maps["ULT_XMEN3"][n] for n in range(1, 25)]
    ultimates = [issue_maps["ULTIMATESP"][n] for n in range(1, 25)]
    wolverine = [issue_maps["ULTMTWOLVP"][n] for n in range(1, 17)]
    incursion = [issue_maps["USMINCRSN"][n] for n in range(1, 6)]
    endgame = [issue_maps["ULTMTENDG"][n] for n in range(1, 4)]

    # Master: fondazione esplicita, poi pubblicazione italiana mensile stabile.
    # Ultimate Universe #1 è l'epilogo di Invasion e viene quindi forzato prima delle ongoing.
    master = invasion + [universe_specials[0]]
    remaining = spider + black_panther + xmen + ultimates + wolverine + incursion + endgame + [universe_specials[1]]
    master += publication_order(remaining)

    # Correzioni narrative minime: One Year In deve precedere l'avvio di Wolverine;
    # Endgame resta nella cronologia editoriale perché procede in parallelo agli ultimi numeri.
    one_year = issue_maps["ULTIMATEUN"][2]
    w1_id = issue_maps["ULTMTWOLVP"][1]["id"]
    master = [i for i in master if i["id"] != one_year["id"]]
    w1_index = next((idx for idx, i in enumerate(master) if i["id"] == w1_id), len(master))
    master.insert(w1_index, one_year)

    characters = [
        build_character(
            "ultimate-new-universe", "Ultimate Universe", "Terra-6160 · saga completa", "#ff6a4d",
            "Percorso master del nuovo Universo Ultimate. Parte da Ultimate Invasion, attraversa tutte le linee principali di Terra-6160, gli speciali annuali, Ultimate Spider-Man: Incursion e la fase Ultimate Endgame. Gli albi fisici sono condivisi con i percorsi singoli, quindi Recuperato resta globale mentre Letto resta specifico del percorso.",
            master, list(SERIES),
        ),
        build_character("ultimate-invasion", "Ultimate Invasion", "La nascita di Terra-6160", "#ff765e", "La miniserie di Jonathan Hickman e Bryan Hitch che crea Terra-6160 e dà origine alla nuova linea Ultimate.", invasion, ["ULTIMATIN"]),
        build_character("ultimate-new-spiderman", "Ultimate Spider-Man", "Peter Parker · Terra-6160", "#e85b5b", "Il percorso completo di Ultimate Spider-Man di Jonathan Hickman, dal ritorno di Peter Parker come eroe alla conclusione della serie.", spider, ["ULT_SM3"]),
        build_character("ultimate-new-black-panther", "Ultimate Black Panther", "T'Challa · Terra-6160", "#9c7cff", "Il percorso completo del Wakanda di Terra-6160 e della guerra contro Moon Knight.", black_panther, ["ULTBLCKPIT"]),
        build_character("ultimate-new-xmen", "Ultimate X-Men", "Mutanti di Hi no Kuni · Terra-6160", "#e9c45f", "La serie completa di Peach Momoko con Armor, Maystorm e i mutanti di Hi no Kuni.", xmen, ["ULT_XMEN3"]),
        build_character("ultimate-new-ultimates", "Ultimates", "La resistenza di Terra-6160", "#6fa8ff", "La serie completa di Deniz Camp che segue Iron Lad, Capitan America, Thor e la rete di eroi contro il Consiglio del Creatore.", ultimates, ["ULTIMATESP"]),
        build_character("ultimate-new-wolverine", "Ultimate Wolverine", "Il Soldato d'Inverno · Terra-6160", "#d8c55b", "La serie completa di Chris Condon e Alessandro Cappuccio: Wolverine come arma della Repubblica Eurasiatica e il tentativo di liberarlo dal condizionamento.", wolverine, ["ULTMTWOLVP"]),
        build_character("ultimate-new-specials", "Ultimate Universe", "Speciali · apertura e One Year In", "#ff9b6e", "I due speciali italiani che aprono la linea dopo Ultimate Invasion e segnano il passaggio dal primo al secondo anno.", universe_specials, ["ULTIMATEUN"]),
        build_character("ultimate-incursion", "Ultimate Spider-Man: Incursion", "Miles Morales entra in Terra-6160", "#df6dff", "Il primo crossover limitato della linea: Miles Morales di Terra-616 attraversa il nuovo Universo Ultimate e incontra le sue principali linee narrative.", incursion, ["USMINCRSN"]),
        build_character("ultimate-endgame", "Ultimate Endgame", "Il ritorno del Creatore", "#ff4d4d", "L'evento conclusivo di Terra-6160. Il percorso include gli albi italiani fisicamente pubblicati e catalogati; verrà esteso automaticamente nelle manutenzioni quando Panini pubblicherà gli ultimi capitoli.", endgame, ["ULTMTENDG"]),
    ]

    for character in characters:
        pack(character)

    manifest_path = DATA / "characters.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    replacement_ids = {c["id"] for c in characters}
    entries = [e for e in manifest["characters"] if e["id"] not in replacement_ids]
    meta = {
        "ultimate-new-universe": ("Ultimate Universe", "Terra-6160 · saga completa", "universe", "#ff6a4d", "ultimate-new-universe.svg"),
        "ultimate-invasion": ("Ultimate Invasion", "La nascita di Terra-6160", "event", "#ff765e", "ultimate-invasion.svg"),
        "ultimate-new-spiderman": ("Ultimate Spider-Man", "Peter Parker · Terra-6160", "character", "#e85b5b", "ultimate-new-spiderman.svg"),
        "ultimate-new-black-panther": ("Ultimate Black Panther", "T'Challa · Terra-6160", "character", "#9c7cff", "ultimate-new-black-panther.svg"),
        "ultimate-new-xmen": ("Ultimate X-Men", "Mutanti di Hi no Kuni · Terra-6160", "team", "#e9c45f", "ultimate-new-xmen.svg"),
        "ultimate-new-ultimates": ("Ultimates", "La resistenza di Terra-6160", "team", "#6fa8ff", "ultimate-new-ultimates.svg"),
        "ultimate-new-wolverine": ("Ultimate Wolverine", "Il Soldato d'Inverno · Terra-6160", "character", "#d8c55b", "ultimate-new-wolverine.svg"),
        "ultimate-new-specials": ("Ultimate Universe", "Speciali · apertura e One Year In", "collection", "#ff9b6e", "ultimate-new-specials.svg"),
        "ultimate-incursion": ("Ultimate Spider-Man: Incursion", "Miles Morales entra in Terra-6160", "event", "#df6dff", "ultimate-incursion.svg"),
        "ultimate-endgame": ("Ultimate Endgame", "Il ritorno del Creatore", "event", "#ff4d4d", "ultimate-endgame.svg"),
    }
    for character in characters:
        name, subtitle, type_, accent, logo = meta[character["id"]]
        entries.append({
            "id": character["id"], "name": name, "subtitle": subtitle, "type": type_,
            "primaryHub": "ultimate-new", "hubs": ["ultimate-new"], "accent": accent,
            "logo": f"assets/heroes/{logo}", "data": f"data/characters/{character['id']}.json",
            "start": character["start"], "end": character["end"], "totalRequired": character["totalRequired"],
        })
    manifest["characters"] = entries
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    hubs_path = DATA / "hubs.json"
    hubs = json.loads(hubs_path.read_text(encoding="utf-8"))
    hub = next(item for item in hubs["hubs"] if item["id"] == "ultimate-new")
    hub.pop("status", None)
    hub["subtitle"] = "Terra-6160 · due anni, un'unica saga completa"
    hub["featuredPath"] = "ultimate-new-universe"
    hub["groups"] = [
        {"id": "master", "label": "Segui tutto l'universo", "paths": ["ultimate-new-universe"]},
        {"id": "foundation", "label": "Fondazione", "paths": ["ultimate-invasion", "ultimate-new-specials"]},
        {"id": "core", "label": "Linee principali", "paths": ["ultimate-new-spiderman", "ultimate-new-black-panther", "ultimate-new-xmen", "ultimate-new-ultimates", "ultimate-new-wolverine"]},
        {"id": "events", "label": "Eventi", "paths": ["ultimate-incursion", "ultimate-endgame"]},
    ]
    hubs_path.write_text(json.dumps(hubs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    logos = {
        "ultimate-new-universe.svg": ("#ff6a4d", "6160"),
        "ultimate-invasion.svg": ("#ff765e", "INV"),
        "ultimate-new-spiderman.svg": ("#e85b5b", "USM"),
        "ultimate-new-black-panther.svg": ("#9c7cff", "BP"),
        "ultimate-new-xmen.svg": ("#e9c45f", "X"),
        "ultimate-new-ultimates.svg": ("#6fa8ff", "U"),
        "ultimate-new-wolverine.svg": ("#d8c55b", "W"),
        "ultimate-new-specials.svg": ("#ff9b6e", "UU"),
        "ultimate-incursion.svg": ("#df6dff", "INC"),
        "ultimate-endgame.svg": ("#ff4d4d", "END"),
    }
    for filename, (accent, text) in logos.items():
        write_logo(filename, accent, text)

    audit = {
        "version": 1,
        "universe": "Earth-6160",
        "masterTotal": len(master),
        "series": {sid: expected for sid, (_, _, expected) in SERIES.items()},
        "ordering": "Fondazione esplicita; poi pubblicazione italiana con priorità stabili; One Year In forzato prima di Ultimate Wolverine.",
        "note": "Ultimate Endgame include solo gli albi italiani fisicamente pubblicati/catalogati al momento del build; il finale USA non viene contato come albo italiano finché non esiste l'edizione Panini.",
    }
    (DATA / "ultimate-new-audit.json").write_text(json.dumps(audit, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("Nuovo Ultimate / Terra-6160 generato:")
    for character in characters:
        print(f"- {character['name']}: {character['totalRequired']} tappe")


if __name__ == "__main__":
    main()
