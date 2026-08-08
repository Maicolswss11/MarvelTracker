#!/usr/bin/env python3
"""Rebuild the lazy-loaded character archives from ComicsBox indexes.

The public site only consumes the generated gzip/base64 chunks. This script is a
maintenance tool: it keeps the issue metadata reproducible and prevents manual
copy/paste from corrupting compressed streams.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500  # Multiple of four: every base64 part is independently safe to join.
USER_AGENT = "MarvelTracker data maintenance/2.0"

MONTHS = {
    "Jan": "Gennaio",
    "Feb": "Febbraio",
    "Mar": "Marzo",
    "Apr": "Aprile",
    "May": "Maggio",
    "Jun": "Giugno",
    "Jul": "Luglio",
    "Aug": "Agosto",
    "Sep": "Settembre",
    "Oct": "Ottobre",
    "Nov": "Novembre",
    "Dec": "Dicembre",
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
                number = re.search(r"\d+", self._cells[0])
                if number:
                    self.rows.append(
                        {
                            "n": number.group(0),
                            "name": self._cells[1].rstrip("* "),
                            "title": self._cells[2],
                            "date": self._cells[3],
                            "href": self._href,
                        }
                    )


def italian_date(value: str) -> str:
    for short, italian in MONTHS.items():
        value = re.sub(rf"\b{short}\b", italian, value)
    return value


def fetch_page(code: str, offset: int) -> list[dict[str, str]]:
    url = f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        source = response.read().decode("utf-8", errors="replace")
    parser = SeriesTableParser()
    parser.feed(source)
    return parser.rows


def fetch_series(code: str, first: int, last: int) -> dict[int, dict[str, str]]:
    offsets = list(range(0, last - first + 1, 50))
    records: dict[int, dict[str, str]] = {}
    for attempt in range(1, 4):
        with ThreadPoolExecutor(max_workers=min(4, len(offsets))) as pool:
            pages = pool.map(lambda offset: fetch_page(code, offset), offsets)
        for page in pages:
            for row in page:
                records[int(row["n"])] = row
        missing = [number for number in range(first, last + 1) if number not in records]
        if not missing:
            return records
        if attempt < 3:
            time.sleep(attempt * 2)
    raise RuntimeError(f"{code}: numeri mancanti nell'indice ComicsBox: {missing}")


def range_meta(number: int, ranges: list[tuple[int, str, str]]) -> tuple[str, str]:
    for maximum, era, subtitle in ranges:
        if number <= maximum:
            return era, subtitle
    raise ValueError(f"Nessuna era configurata per il numero {number}")


THOR_ERAS = [
    (38, "Heroes Return — Dan Jurgens", "Il rilancio moderno del 1998/1999"),
    (71, "Reigning / King Thor", "Il regno di Thor e la fase conclusiva di Dan Jurgens"),
    (77, "Ragnarok", "Vendicatori Divisi e fine di Thor vol. 2"),
    (109, "Intervallo antologico", "La testata ospita soprattutto Nuovi Vendicatori e Capitan America"),
    (136, "Rinascita / JMS / Dark Reign", "Thor torna; Asgard viene ricostruita sulla Terra"),
    (159, "Assedio / Heroic Age / Fear Itself", "Da Assedio alla frattura con Odino"),
    (170, "Tanarus / AvX / Fine dei Giorni", "Il ponte verso Thor: Dio del Tuono"),
    (193, "Thor: Dio del Tuono", "Jason Aaron, Gorr e le tre ere di Thor"),
    (201, "Thor / Jane Foster", "La nuova Dea del Tuono"),
    (205, "Secret Wars — Thors", "Il Corpo dei Thor nel Battleworld"),
    (233, "La Potente Thor", "Jane Foster, Mangog e la Guerra degli Asgardiani"),
    (253, "Thor rinato / Guerra dei Regni / King Thor", "Il ritorno di Thor e il finale di Jason Aaron"),
    (290, "Thor di Donny Cates", "Galactus, Dio dei Martelli e oltre"),
    (322, "Thor l'Immortale", "Al Ewing e il nuovo ciclo del Dio del Tuono"),
    (323, "Il Mortale Thor", "Il nuovo capitolo annunciato"),
]

HULK_DEH_ERAS = [
    (49, "Peter David / Hulk classico moderno", "Marvel Italia riprende Hulk dagli spillati Star Comics"),
    (83, "Fine anni '90 / Cavalieri Marvel", "Hulk e Devil condividono la testata antologica"),
    (123, "Bruce Jones / House of M", "La lunga fase precedente a Planet Hulk"),
    (134, "Planet Hulk", "Esilio, Sakaar e rivoluzione"),
    (140, "World War Hulk", "Il ritorno di Hulk sulla Terra"),
    (153, "Hulk Rosso / Secret Invasion", "Il mistero del nuovo Hulk rosso"),
    (169, "Dark Reign / Caduta degli Hulk", "La guerra della famiglia gamma"),
    (177, "World War Hulks / Shadowland", "Chiusura della storica testata antologica"),
]

HULK2_ERAS = [
    (13, "Jason Aaron — Separati", "Bruce Banner e Hulk su strade opposte"),
    (27, "Indistruttibile Hulk", "Mark Waid e lo S.H.I.E.L.D."),
    (38, "All-New Marvel NOW!", "La trasformazione di Doc Green"),
    (43, "Secret Wars — Planet Hulk", "Il mondo gamma del Battleworld"),
    (88, "L'Immortale Hulk", "Al Ewing e l'orrore della Porta Verde"),
    (103, "Hulk — Donny Cates", "L'astronave Hulk e Titan"),
    (139, "L'Incredibile Hulk", "Phillip Kennedy Johnson — horror gamma"),
]

SPIDER_SERIES = [
    (600, "UR_M", "L'Uomo Ragno"),
    (614, "SPIDER_SUP", "Superior Spider-Man"),
    (649, "ASM_IT_V1", "Amazing Spider-Man Vol.1"),
    (709, "ASM_IT_V2", "Amazing Spider-Man Vol.2"),
    (800, "ASM_IT_V3", "Amazing Spider-Man Vol.3"),
    (873, "ASM_IT_2022", "Amazing Spider-Man (2022)"),
    (899, "ASM_IT_2025", "Amazing Spider-Man (2025)"),
]

SPIDER_ERAS = [
    (140, "Star Comics", "Il nuovo corso italiano dal 1987"),
    (225, "Marvel Italia — anni '90", "La testata passa a Marvel Italia"),
    (488, "Marvel Italia / Panini", "La lunga fase classica della numerazione italiana"),
    (600, "Un nuovo giorno", "Il rilancio di Spider-Man e la strada verso Superior"),
    (614, "Superior Spider-Man", "Otto Octavius nei panni dell'Uomo Ragno"),
    (649, "Amazing Spider-Man Vol.1", "Il ritorno di Peter Parker"),
    (709, "Amazing Spider-Man Vol.2", "Worldwide, Clone Conspiracy e Legacy"),
    (800, "Amazing Spider-Man Vol.3", "Da Nick Spencer a Beyond"),
    (873, "Amazing Spider-Man (2022)", "Il ciclo di Zeb Wells"),
    (899, "Amazing Spider-Man (2025)", "Il nuovo ciclo di Joe Kelly"),
]


def read_meta(character_id: str) -> dict:
    result = json.loads((DATA / "characters" / f"{character_id}.json").read_text(encoding="utf-8"))
    result.pop("issueSources", None)
    return result


def build_thor(records: dict[int, dict[str, str]]) -> dict:
    character = read_meta("thor")
    issues = []
    for number in range(1, 324):
        row = records[number]
        era, era_sub = range_meta(number, THOR_ERAS)
        optional = 78 <= number <= 109
        future = number == 323
        sequence = None if optional else number if number <= 77 else number - 32
        if optional:
            instruction = "Facoltativo per il percorso Thor: in questa fase la testata ospita soprattutto Nuovi Vendicatori e Capitan America."
        elif number == 77:
            instruction = "Leggi l'albo completo. È l'ultimo capitolo di Ragnarok; poi salta direttamente al #110."
        elif number == 110:
            instruction = "Thor torna qui: riprendi la lettura dal #110."
        elif future:
            instruction = "Numero annunciato: non viene ancora conteggiato nel progresso leggibile."
        else:
            instruction = "Leggi l'albo completo e poi passa al successivo numero richiesto."
        issue = {
            "id": f"THORVE_M:{number}",
            "seq": sequence,
            "seriesId": "THORVE_M",
            "series": "Thor",
            "publisher": "Marvel Italia / Panini Comics",
            "n": number,
            "name": f"Thor #{number}",
            "title": row["title"] or ("Inizio del rilancio moderno di Thor" if number == 1 else "Albo regolare della testata"),
            "date": italian_date(row["date"]),
            "era": era,
            "eraSub": era_sub,
            "cover": f"https://www.comicsbox.it/cover/THORVE_M_{number:03d}.jpg",
            "url": f"https://www.comicsbox.it/albo/THORVE_M_{number:03d}",
            "required": not optional,
            "skip": optional,
            "instruction": instruction,
        }
        if future:
            issue["future"] = True
        issues.append(issue)
    character["issues"] = issues
    return character


def build_hulk(
    devil_hulk: dict[int, dict[str, str]],
    incredible_hulk: dict[int, dict[str, str]],
    hulk_defenders: dict[int, dict[str, str]],
) -> dict:
    character = read_meta("hulk")
    issues = []
    for number in range(1, 178):
        row = devil_hulk[number]
        era, era_sub = range_meta(number, HULK_DEH_ERAS)
        issues.append(
            {
                "id": f"DEH_M:{number}",
                "seq": number,
                "seriesId": "DEH_M",
                "series": "Devil & Hulk",
                "publisher": "Marvel Italia / Panini Comics",
                "n": number,
                "name": f"Devil & Hulk #{number}",
                "title": row["title"] or "Albo antologico — segmento Hulk",
                "date": italian_date(row["date"]),
                "era": era,
                "eraSub": era_sub,
                "cover": f"https://www.comicsbox.it/cover/DEH_M_{number:03d}.jpg",
                "url": f"https://www.comicsbox.it/albo/DEH_M_{number:03d}",
                "required": True,
                "skip": False,
                "sharedWith": ["Daredevil"],
                "instruction": (
                    "PARTI DA QUI. Devil & Hulk è antologico: leggi il segmento di Hulk; lo stesso albo fisico sarà condiviso con il percorso di Daredevil."
                    if number == 1
                    else "Albo antologico: per il percorso Hulk leggi il segmento di Hulk e poi passa al numero successivo."
                ),
            }
        )
    for number in range(178, 187):
        row = incredible_hulk[number]
        issues.append(
            {
                "id": f"HULK_M:{number}",
                "seq": number,
                "seriesId": "HULK_M",
                "series": "L'Incredibile Hulk",
                "publisher": "Panini Comics",
                "n": number,
                "name": f"L'Incredibile Hulk #{number}",
                "title": row["title"] or "Albo regolare della testata",
                "date": italian_date(row["date"]),
                "era": "L'Incredibile Hulk",
                "eraSub": "Chiusura della numerazione storica di Devil & Hulk",
                "cover": f"https://www.comicsbox.it/cover/HULK_M_{number:03d}.jpg",
                "url": f"https://www.comicsbox.it/albo/HULK_M_{number:03d}",
                "required": True,
                "skip": False,
                "instruction": "Leggi l'albo completo e poi passa al numero successivo.",
            }
        )
    for number in range(1, 140):
        row = hulk_defenders[number]
        era, era_sub = range_meta(number, HULK2_ERAS)
        issues.append(
            {
                "id": f"HULK2_M:{number}",
                "seq": 186 + number,
                "seriesId": "HULK2_M",
                "series": "Hulk e i Difensori",
                "publisher": "Panini Comics",
                "n": number,
                "name": f"Hulk e i Difensori #{number}",
                "title": row["title"] or "Albo regolare della testata",
                "date": italian_date(row["date"]),
                "era": era,
                "eraSub": era_sub,
                "cover": f"https://www.comicsbox.it/cover/HULK2_M_{number:03d}.jpg",
                "url": f"https://www.comicsbox.it/albo/HULK2_M_{number:03d}",
                "required": True,
                "skip": False,
                "instruction": "Leggi l'albo completo e poi passa al numero successivo.",
            }
        )
    character["issues"] = issues
    return character


def spider_series(number: int) -> tuple[str, str]:
    for maximum, series_id, name in SPIDER_SERIES:
        if number <= maximum:
            return series_id, name
    raise ValueError(number)


def build_spiderman(records: dict[int, dict[str, str]]) -> dict:
    character = read_meta("spiderman")
    character["mappedTotal"] = 899
    character["availableTotal"] = 895
    issues = []
    for number in range(1, 900):
        row = records[number]
        series_id, series_name = spider_series(number)
        era, era_sub = range_meta(number, SPIDER_ERAS)
        future = number > character["availableTotal"]
        issue = {
            "id": f"SPIDER_MAIN:{number}",
            "seq": number,
            "seriesId": series_id,
            "series": series_name,
            "publisher": "Star Comics / Marvel Italia / Panini Comics",
            "n": number,
            "name": f"{series_name} #{number}",
            "title": row["title"] or "Albo regolare della testata principale",
            "date": italian_date(row["date"]),
            "dateQuality": "indice",
            "era": era,
            "eraSub": era_sub,
            "cover": f"https://www.comicsbox.it/cover/UR_SM_{number:03d}.jpg",
            "url": f"https://www.comicsbox.it/albo/UR_SM_{number:03d}",
            "required": True,
            "skip": False,
            "instruction": (
                "PARTI DA QUI. È il #1 Star Comics del maggio 1987: l'edizione Corno è esclusa dal percorso."
                if number == 1
                else "Numero della sequenza italiana principale: leggi l'albo completo e poi passa al successivo."
            ),
            "coverSource": "ComicsBox",
        }
        if future:
            issue["future"] = True
            issue["instruction"] = "Numero annunciato: resta visibile ma non viene ancora conteggiato nel progresso leggibile."
        issues.append(issue)
    character["issues"] = issues
    return character


def unpack_character(character_id: str) -> dict:
    spec = json.loads((DATA / "encoded" / f"{character_id}.json").read_text(encoding="utf-8"))
    encoded = "".join((ROOT / source).read_text(encoding="ascii").strip() for source in spec["sources"])
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def pack_character(character: dict) -> None:
    character_id = character["id"]
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[index : index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    b64_dir = DATA / "b64"
    for old_part in b64_dir.glob(f"{character_id}-*.b64"):
        old_part.unlink()
    sources = []
    for index, part in enumerate(parts, start=1):
        relative = f"data/b64/{character_id}-{index:02d}.b64"
        (ROOT / relative).write_text(part, encoding="ascii")
        sources.append(relative)
    spec = {"encoding": "gzip-base64-parts", "sources": sources}
    (DATA / "encoded" / f"{character_id}.json").write_text(
        json.dumps(spec, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{character['name']}: {len(character['issues'])} albi, {len(raw):,} byte, {len(parts)} parti")


def update_manifests() -> None:
    manifest_path = DATA / "characters.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = 7
    for character in manifest["characters"]:
        if character["id"] == "cap":
            character["accent"] = "#3b6eea"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    cap_meta_path = DATA / "characters" / "cap.json"
    cap_meta = json.loads(cap_meta_path.read_text(encoding="utf-8"))
    cap_meta["accent"] = "#3b6eea"
    cap_meta_path.write_text(json.dumps(cap_meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    jobs = {
        "thor": ("THORVE_M", 1, 323),
        "devil_hulk": ("DEH_M", 1, 177),
        "incredible_hulk": ("HULK_M", 178, 186),
        "hulk_defenders": ("HULK2_M", 1, 139),
        "spiderman": ("UR_SM", 1, 899),
    }
    indexes = {
        name: fetch_series(code, first, last)
        for name, (code, first, last) in jobs.items()
    }

    cap = unpack_character("cap")
    cap["accent"] = "#3b6eea"
    pack_character(cap)
    pack_character(build_thor(indexes["thor"]))
    pack_character(
        build_hulk(indexes["devil_hulk"], indexes["incredible_hulk"], indexes["hulk_defenders"])
    )
    pack_character(build_spiderman(indexes["spiderman"]))
    update_manifests()


if __name__ == "__main__":
    main()
