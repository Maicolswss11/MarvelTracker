#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500
USER_AGENT = "MarvelTracker data maintenance/4.0"
MANIFEST_VERSION = 10

MONTHS_IT = {
    "Jan": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
    "May": "Maggio", "Jun": "Giugno", "Jul": "Luglio", "Aug": "Agosto",
    "Sep": "Settembre", "Oct": "Ottobre", "Nov": "Novembre", "Dec": "Dicembre",
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
                    self.rows.append({
                        "n": number.group(0),
                        "name": self._cells[1].rstrip("* "),
                        "title": self._cells[2],
                        "date": self._cells[3],
                        "href": self._href,
                    })


def fetch_url(url: str, attempts: int = 5) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=45) as response:
                source = response.read().decode("utf-8", errors="replace")
            if "Connessione MySQL fallita" in source:
                raise RuntimeError("ComicsBox database temporarily unavailable")
            return source
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Impossibile leggere {url}: {last_error}")


def fetch_series_page(code: str, offset: int) -> list[dict[str, str]]:
    parser = SeriesTableParser()
    parser.feed(fetch_url(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}"))
    return parser.rows


def fetch_all_series(code: str, max_pages: int = 12) -> dict[int, dict[str, str]]:
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


def date_year(value: str) -> str:
    match = re.search(r"(?:19|20)\d{2}", value)
    return match.group(0) if match else "oggi"


def xmen_era(series_id: str, number: int) -> tuple[str, str]:
    if series_id == "MINTGRXMEN":
        if number <= 18:
            return "Seconda Genesi / Fenice", "Dalla nuova squadra di Giant-Size X-Men al primo grande ciclo di Claremont"
        if number <= 38:
            return "Claremont — espansione del mondo mutante", "La squadra cresce e il mondo degli X-Men diventa una mitologia condivisa"
        if number <= 58:
            return "Claremont — crisi e crossover mutanti", "Il periodo dei grandi conflitti che ridefiniscono il destino dei mutanti"
        return "Claremont / Jim Lee — Squadre Blu e Oro", "Verso X-Men vol.2 e la configurazione iconica dei primi anni Novanta"
    if number <= 99:
        return "Anni Novanta — Blue/Gold e grandi crisi", "La continuità successiva a X-Men vol.2 #1-3"
    if number <= 149:
        return "Fine anni Novanta / inizio Duemila", "Dalla ricostruzione post-Onslaught verso la rivoluzione moderna della linea mutante"
    if number <= 199:
        return "Morrison / Reload / House of M", "Gli X-Men entrano nell'era moderna e il mondo mutante cambia radicalmente"
    if number <= 249:
        return "Decimation / Messiah era", "Dopo House of M, la sopravvivenza della specie mutante diventa il centro della saga"
    if number <= 279:
        return "Secondo Avvento / Scisma / Avengers vs X-Men", "La frattura interna degli X-Men conduce allo scontro con i Vendicatori"
    if number <= 320:
        return "Marvel NOW! — era Bendis", "La rivoluzione mutante di Ciclope e le nuove generazioni di X-Men"
    if number <= 360:
        return "ResurrXion / X-Men Divisi", "La linea mutante si ricompone prima del successivo cambio di paradigma"
    if number <= 418:
        return "Krakoa", "L'era della nazione mutante, da House of X / Powers of X alla caduta di Krakoa"
    return "Dalle ceneri — era contemporanea", "Il nuovo assetto degli X-Men dopo Krakoa"


def make_issue(series_id: str, series_name: str, publisher: str, number: int, row: dict[str, str], seq: int, instruction: str) -> dict:
    era, era_sub = xmen_era(series_id, number)
    code = f"{series_id}_{number:03d}"
    return {
        "id": f"{series_id}:{number}", "seq": seq, "seriesId": series_id, "series": series_name,
        "publisher": publisher, "n": number, "name": f"{series_name} #{number}",
        "title": row["title"] or "Albo del percorso principale X-Men", "date": italian_date(row["date"]),
        "dateQuality": "indice", "era": era, "eraSub": era_sub,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg", "url": f"https://www.comicsbox.it/albo/{code}",
        "required": True, "skip": False, "instruction": instruction, "coverSource": "ComicsBox",
    }


def pack_character(character: dict) -> None:
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[i:i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]
    for old in (DATA / "b64").glob("xmen-*.b64"):
        old.unlink()
    sources: list[str] = []
    for index, part in enumerate(parts, 1):
        rel = f"data/b64/xmen-{index:02d}.b64"
        (ROOT / rel).write_text(part, encoding="ascii")
        sources.append(rel)
    (DATA / "encoded" / "xmen.json").write_text(json.dumps({"encoding": "gzip-base64-parts", "sources": sources}, separators=(",", ":")), encoding="utf-8")
    print(f"X-Men: {len(character['issues'])} albi, {len(raw):,} byte, {len(parts)} parti")


def build_path() -> tuple[dict, int]:
    integrale = fetch_all_series("MINTGRXMEN", 3)
    mainline = fetch_all_series("XM_SM", 12)
    missing = [n for n in range(1, 77) if n not in integrale]
    if missing:
        raise RuntimeError(f"Marvel Integrale incompleto: {missing}")
    if 51 not in mainline:
        raise RuntimeError("Gli Incredibili X-Men #51 non trovato")
    current_main = max(n for n in mainline if n >= 51)
    if current_main < 419:
        raise RuntimeError(f"Indice X-Men inatteso: ultimo numero {current_main}")

    issues: list[dict] = []
    seq = 1
    for number in range(1, 77):
        instruction = "PARTI DA QUI. Il volume apre la fondazione moderna con Giant-Size X-Men #1 e l'inizio del ciclo di Chris Claremont." if number == 1 else "Fondazione Claremont in ordine narrativo: leggi il volume completo e prosegui."
        issues.append(make_issue("MINTGRXMEN", "Marvel Integrale: Gli Incredibili X-Men", "Panini Comics", number, integrale[number], seq, instruction))
        seq += 1
    for number in range(51, current_main + 1):
        if number not in mainline:
            raise RuntimeError(f"Gli Incredibili X-Men #{number} mancante nell'indice ComicsBox")
        instruction = "Marvel Integrale #76 contiene già X-Men vol.2 #1-3, pubblicati nell'originale italiano #50: il percorso riprende dal #51 per evitare duplicati." if number == 51 else "Segui la testata italiana principale; crossover e satelliti vengono collegati da percorsi evento separati quando necessari."
        issues.append(make_issue("XM_SM", "Gli Incredibili X-Men", "Star Comics / Marvel Italia / Panini Comics", number, mainline[number], seq, instruction))
        seq += 1

    character = {
        "id": "xmen", "name": "X-Men", "subtitle": "La saga mutante", "accent": "#e7c04a",
        "start": "Marvel Integrale: Gli Incredibili X-Men #1 — Gennaio 2019 · storie dal 1975",
        "end": f"Gli Incredibili X-Men #{current_main} — {italian_date(mainline[current_main]['date'])}",
        "description": "Spina dorsale narrativa degli X-Men in edizione italiana. Marvel Integrale #1–76 copre in ordine la fondazione da Giant-Size X-Men #1 fino a X-Men vol.2 #1–3; la timeline prosegue poi da Gli Incredibili X-Men #51 fino alla pubblicazione corrente. X-Force, X-Factor, New Mutants e i completamenti dei grandi crossover restano percorsi trasversali separati, così il percorso principale rimane leggibile.",
        "timelineMode": True,
        "series": [
            {"id": "MINTGRXMEN", "name": "Marvel Integrale: Gli Incredibili X-Men", "publisher": "Panini Comics", "range": "#1–76", "years": "2019–2025 · storie 1975–1991"},
            {"id": "XM_SM", "name": "Gli Incredibili X-Men", "publisher": "Star Comics / Marvel Italia / Panini Comics", "range": f"#51–{current_main}", "years": f"1994–{date_year(mainline[current_main]['date'])}"},
        ],
        "archives": [], "totalRequired": len(issues), "availableTotal": len(issues), "issues": issues,
    }
    return character, current_main


def write_stub(character: dict) -> None:
    stub = {k: v for k, v in character.items() if k not in {"issues", "availableTotal"}}
    stub["issueSources"] = ["data/encoded/xmen.json"]
    (DATA / "characters" / "xmen.json").write_text(json.dumps(stub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update_manifest(character: dict) -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    meta = {
        "id": "xmen", "name": "X-Men", "subtitle": "La saga mutante", "type": "team",
        "primaryHub": "xmen", "hubs": ["xmen"], "accent": "#e7c04a", "logo": "assets/heroes/xmen.svg",
        "data": "data/characters/xmen.json", "start": character["start"], "end": character["end"], "totalRequired": character["totalRequired"],
    }
    chars = [c for c in manifest["characters"] if c["id"] != "xmen"]
    pos = next((i + 1 for i, c in enumerate(chars) if c["id"] == "avengers"), len(chars))
    chars.insert(pos, meta)
    manifest["characters"] = chars
    path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    hub = next((h for h in payload["hubs"] if h["id"] == "xmen"), None)
    if not hub:
        raise RuntimeError("Hub X-Men non trovato")
    hub.pop("status", None)
    hub["featuredPath"] = "xmen"
    hub["groups"] = [{"id": "core", "label": "Percorso principale", "paths": ["xmen"]}]
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def write_logo() -> None:
    (ROOT / "assets" / "heroes" / "xmen.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="X-Men"><rect width="128" height="128" rx="26" fill="#080d13"/><circle cx="64" cy="64" r="47" fill="none" stroke="#e7c04a" stroke-width="6"/><path d="M38 35h16l11 18 11-18h16L73 64l20 30H77L65 74 52 94H36l21-30-19-29Z" fill="#eef4f8"/><path d="M64 17v20M64 91v20" stroke="#e7c04a" stroke-width="5" stroke-linecap="round"/></svg>''', encoding="utf-8")


def update_version_guards() -> None:
    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    verify = re.sub(r'assert\.equal\(manifest\.version,\s*\d+,\s*"Il manifest deve usare la versione cache v\d+"\);', f'assert.equal(manifest.version, {MANIFEST_VERSION}, "Il manifest deve usare la versione cache v{MANIFEST_VERSION}");', verify)
    verify_path.write_text(verify, encoding="utf-8")
    for filename in ("rebuild_character_data.py", "build_avengers_data.py", "build_avengers_characters.py"):
        target = ROOT / "scripts" / filename
        if target.exists():
            source = target.read_text(encoding="utf-8")
            source = re.sub(r'manifest\["version"\]\s*=\s*\d+', f'manifest["version"] = {MANIFEST_VERSION}', source)
            target.write_text(source, encoding="utf-8")


def main() -> None:
    character, current_main = build_path()
    write_stub(character)
    pack_character(character)
    update_manifest(character)
    update_hubs()
    write_logo()
    update_version_guards()
    print(f"X-Men pronto: {character['totalRequired']} tappe. Marvel Integrale #1–76 → Gli Incredibili X-Men #51–{current_main}.")


if __name__ == "__main__":
    main()
