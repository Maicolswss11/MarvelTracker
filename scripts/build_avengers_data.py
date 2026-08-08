#!/usr/bin/env python3
"""Build the modern Italian Avengers reading path (Marvel Italia/Panini era).

The route starts with Marvel Italia's Vendicatori (1994), follows Avengers
material when it moves through anthology titles already tracked by the site,
and then continues on the dedicated Panini Avengers monthly.

Physical issue ids are intentionally reused (IM_VEN:*, THORVE_M:*, IM_VEN2:*)
so the global "Recuperato" collection state is shared with character paths.
"""

from __future__ import annotations

import base64
import copy
import gzip
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500
USER_AGENT = "MarvelTracker data maintenance/3.0"

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
SERIES_PRIORITY = {"VEN_M": 0, "IM_VEN": 1, "THORVE_M": 2, "IM_VEN2": 3, "AVENGERS_M": 4}


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


class IssueContentParser(HTMLParser):
    """Collect short visible labels and link text from an Italian issue page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if len(text) <= 100:
            self.tokens.append(text)
        if self._href is not None:
            self._link_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = " ".join(" ".join(self._link_text).split())
            if text:
                self.links.append((self._href, text))
            self._href = None
            self._link_text = []


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
    source = fetch_url(f"https://www.comicsbox.it/serie.php?limite={offset}&serie={code}")
    parser = SeriesTableParser()
    parser.feed(source)
    return parser.rows


def fetch_all_series(code: str, max_pages: int = 8) -> dict[int, dict[str, str]]:
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


def date_key(value: str) -> tuple[int, int]:
    text = value.lower()
    year_match = re.search(r"(19|20)\d{2}", text)
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
    print(f"Vendicatori: {len(character['issues'])} albi, {len(raw):,} byte, {len(parts)} parti")


def scan_avengers_content(issue: dict) -> tuple[bool, list[str]]:
    source = fetch_url(issue["url"])
    parser = IssueContentParser()
    parser.feed(source)

    # Story labels on ComicsBox are short tokens such as "Avengers", "New Avengers",
    # "Mighty Avengers". The Italian anthology title itself uses "Vendicatori", so it
    # cannot create an English-label false positive here.
    has_team_label = any("avengers" in token.lower() and len(token) <= 70 for token in parser.tokens)
    source_issues: list[str] = []
    for href, text in parser.links:
        if "/albo/" not in href:
            continue
        if "avengers" not in text.lower():
            continue
        cleaned = " ".join(text.split())
        if cleaned not in source_issues:
            source_issues.append(cleaned)
    return has_team_label, source_issues[:8]


def anthology_issue(base: dict, sources: list[str], shared_with: str) -> dict:
    issue = copy.deepcopy(base)
    issue["required"] = True
    issue["skip"] = False
    issue.pop("future", None)
    issue.pop("displayNumber", None)
    issue.pop("kind", None)
    issue["sharedWith"] = [shared_with]
    issue["sourceIssues"] = sources
    issue["title"] = " · ".join(sources[:4]) if sources else "Segmento Avengers dell'albo"
    issue["instruction"] = (
        "Albo antologico: per il percorso Vendicatori leggi i segmenti Avengers indicati, "
        "poi prosegui con la tappa successiva."
    )
    return issue


def avengers_era(issue: dict) -> tuple[str, str]:
    sid, n = issue["seriesId"], issue["n"]
    if sid == "VEN_M":
        return "Vendicatori — Marvel Italia", "Il rilancio italiano moderno dal 1994"
    if sid == "IM_VEN":
        if n < 32:
            return "Onslaught / Heroes Reborn", "Dagli ultimi Vendicatori classici al rilancio post-Onslaught"
        return "Heroes Return", "Busiek, Pérez e il ritorno degli Eroi più potenti della Terra"
    if sid == "THORVE_M":
        if n <= 73:
            return "Avengers — Geoff Johns / Austen", "La testata Thor ospita la serie Avengers"
        if n <= 77:
            return "Vendicatori Divisi", "La caduta della squadra storica"
        if n <= 142:
            return "Nuovi Vendicatori", "L'era di Brian Michael Bendis dopo Avengers Disassembled"
        return "Heroic Age — Nuovi Vendicatori", "La ricostruzione dopo Assedio"
    if sid == "IM_VEN2":
        if n <= 34:
            return "Potenti / Oscuri Vendicatori", "Da Civil War a Secret Invasion, Dark Reign e Assedio"
        return "Heroic Age — Avengers", "Il ritorno di una squadra ufficiale dei Vendicatori"
    if sid == "AVENGERS_M":
        if n <= 15:
            return "Bendis / Avengers vs X-Men", "La chiusura dell'era Bendis"
        if n <= 49:
            return "Marvel NOW! — Hickman", "Avengers, New Avengers, Infinity e Secret Wars"
        if n <= 100:
            return "All-New, All-Different / Legacy", "Le nuove formazioni dopo Secret Wars"
        if n <= 150:
            return "Fresh Start", "Il ciclo moderno degli Avengers"
        return "Avengers — era contemporanea", "Le più recenti incarnazioni degli Eroi più potenti della Terra"
    return "Vendicatori", "Percorso moderno italiano"


def build_dedicated_issue(series_id: str, series_name: str, publisher: str, row: dict[str, str], number: int) -> dict:
    issue = {
        "id": f"{series_id}:{number}",
        "seq": 0,
        "seriesId": series_id,
        "series": series_name,
        "publisher": publisher,
        "n": number,
        "name": f"{series_name} #{number}",
        "title": row["title"] or "Albo dedicato ai Vendicatori",
        "date": italian_date(row["date"]),
        "era": "",
        "eraSub": "",
        "cover": f"https://www.comicsbox.it/cover/{series_id}_{number:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{series_id}_{number:03d}",
        "required": True,
        "skip": False,
        "instruction": "Leggi l'albo completo e poi prosegui con la tappa successiva del percorso Vendicatori.",
    }
    issue["era"], issue["eraSub"] = avengers_era(issue)
    return issue


def patch_ui() -> None:
    app_path = ROOT / "js" / "app.js"
    app = app_path.read_text(encoding="utf-8")

    old_parse = 'function parseHash(){const p=location.hash.replace(/^#\\/?/,"").split("/").filter(Boolean);if(!p.length||p[0]==="home")return {view:"home",character:null,issue:null};return {view:"character",character:p[0],issue:p[1]?Number(p[1]):null}}'
    new_parse = 'function parseHash(){const p=location.hash.replace(/^#\\/?/,"").split("/").filter(Boolean);if(!p.length||p[0]==="home")return {view:"home",character:null,issue:null};return {view:"character",character:p[0],issue:p[1]||null}}\nfunction routeIssueToken(i){return currentCharacter?.timelineMode&&Number.isInteger(i.seq)?`p${i.seq}`:String(i.n)}\nfunction resolveIssueToken(character,token){if(!character||token===null||token===undefined||token==="")return null;const value=String(token);if(value.startsWith("p")){const seq=Number(value.slice(1));return character.issues.find(i=>i.seq===seq)||null}const n=Number(value);return Number.isFinite(n)?character.issues.find(i=>i.n===n)||null:null}'
    if old_parse in app:
        app = app.replace(old_parse, new_parse, 1)
    elif "function routeIssueToken" not in app:
        raise RuntimeError("parseHash non riconosciuto in js/app.js")

    old_switch = '  if(updateHash)history.replaceState(null,"",`#/${meta.id}${issue?`/${issue}`:""}`);\n  if(issue)requestAnimationFrame(()=>$( `issue-${currentCharacter.issues.find(i=>i.n===issue)?.seriesId}-${issue}` )?.scrollIntoView({behavior:"smooth",block:"center"}));'
    new_switch = '  const routeTarget=issue?resolveIssueToken(currentCharacter,issue):null;\n  if(updateHash)history.replaceState(null,"",`#/${meta.id}${routeTarget?`/${routeIssueToken(routeTarget)}`:""}`);\n  if(routeTarget)requestAnimationFrame(()=>$( `issue-${routeTarget.seriesId}-${routeTarget.n}` )?.scrollIntoView({behavior:"smooth",block:"center"}));'
    if old_switch in app:
        app = app.replace(old_switch, new_switch, 1)
    elif "const routeTarget=issue?resolveIssueToken" not in app:
        raise RuntimeError("switchCharacter non riconosciuto in js/app.js")

    old_nav_start = 'function renderSeriesNav(){els.seriesNav.innerHTML=(currentCharacter.series||[]).map(s=>{const xs=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=xs.filter(i=>status(i.id).read).length;return `<button data-jump="${esc(s.id)}"><b>${esc(s.name)}</b><span>${r}/${xs.length} letti · ${esc(s.years)}</span></button>`}).join("");els.seriesNav.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>$("series-"+b.dataset.jump)?.scrollIntoView({behavior:"smooth",block:"start"}))}'
    new_nav = 'function renderSeriesNav(){els.seriesNav.innerHTML=(currentCharacter.series||[]).map(s=>{const xs=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=xs.filter(i=>status(i.id).read).length;return `<button data-jump="${esc(s.id)}"><b>${esc(s.name)}</b><span>${r}/${xs.length} letti · ${esc(s.years)}</span></button>`}).join("");els.seriesNav.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>{if(currentCharacter.timelineMode){const i=currentCharacter.issues.find(i=>i.seriesId===b.dataset.jump&&i.required!==false&&!i.future);if(i)jumpToIssue(i)}else $("series-"+b.dataset.jump)?.scrollIntoView({behavior:"smooth",block:"start"})})}'
    if old_nav_start in app:
        app = app.replace(old_nav_start, new_nav, 1)
    elif "if(currentCharacter.timelineMode){const i=currentCharacter.issues.find" not in app:
        raise RuntimeError("renderSeriesNav non riconosciuto in js/app.js")

    old_issue_marker = '  const insertBadge=isInsert?\'<span class="chronologyBadge">Inserto cronologico</span>\':"";'
    new_issue_marker = '  const insertBadge=isInsert?\'<span class="chronologyBadge">Inserto cronologico</span>\':"";\n  const publicationBadge=currentCharacter.timelineMode?`<span class="publicationBadge">${esc(i.series)}</span>`:"";'
    if old_issue_marker in app:
        app = app.replace(old_issue_marker, new_issue_marker, 1)
    elif "const publicationBadge=currentCharacter.timelineMode" not in app:
        raise RuntimeError("issueHtml marker non riconosciuto")
    app = app.replace('<div class="issueBadges">${insertBadge}</div>', '<div class="issueBadges">${publicationBadge}${insertBadge}</div>', 1)

    start = app.find("function renderBlocks(){")
    end = app.find("function bindIssueActions(){", start)
    if start < 0 or end < 0:
        raise RuntimeError("renderBlocks non trovato")
    normal_body = 'const vis=visibleIssues(),order=(currentCharacter.series||[]).filter(s=>activeSeries==="Tutte"||s.id===activeSeries);els.seriesBlocks.innerHTML=order.map(s=>{const xs=vis.filter(i=>i.seriesId===s.id);if(!xs.length)return"";const all=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=all.filter(i=>status(i.id).read).length,eras=[];for(const i of xs){let g=eras.find(x=>x.era===i.era);if(!g){g={era:i.era,sub:i.eraSub,items:[]};eras.push(g)}g.items.push(i)}return `<section class="seriesBlock" id="series-${esc(s.id)}"><div class="seriesHead"><div><div class="label">${esc(s.publisher)} · ${esc(s.years)}</div><h2>${esc(s.name)} ${esc(s.range)}</h2><p>${all.length} albi richiesti nel percorso</p></div><div class="seriesPct">${r}/${all.length} letti<br>${Math.round(r/(all.length||1)*100)}%</div></div>${eras.map(eraHtml).join("")}</section>`}).join("")||\'<div class="loading">Nessun albo trovato.</div>\';bindIssueActions()'
    new_blocks = 'function renderBlocks(){const vis=visibleIssues();if(currentCharacter.timelineMode){const xs=[...vis].sort((a,b)=>(a.seq??Number.MAX_SAFE_INTEGER)-(b.seq??Number.MAX_SAFE_INTEGER));const all=currentCharacter.issues.filter(i=>i.required!==false&&!i.future),r=all.filter(i=>status(i.id).read).length,eras=[];for(const i of xs){let g=eras.find(x=>x.era===i.era);if(!g){g={era:i.era,sub:i.eraSub,items:[]};eras.push(g)}g.items.push(i)}els.seriesBlocks.innerHTML=xs.length?`<section class="seriesBlock timelineBlock" id="series-timeline"><div class="seriesHead"><div><div class="label">Timeline di lettura · più testate italiane</div><h2>${esc(currentCharacter.name)} — percorso narrativo</h2><p>${all.length} albi fisici ordinati come un unico percorso; usa i filtri per isolare una testata.</p></div><div class="seriesPct">${r}/${all.length} letti<br>${Math.round(r/(all.length||1)*100)}%</div></div>${eras.map(eraHtml).join("")}</section>`:\'<div class="loading">Nessun albo trovato.</div>\';bindIssueActions();return}' + normal_body + '}'
    app = app[:start] + new_blocks + app[end:]

    old_jump = 'function jumpToIssue(i){history.replaceState(null,"",`#/${activeCharacter}/${i.n}`);$( `issue-${i.seriesId}-${i.n}` )?.scrollIntoView({behavior:"smooth",block:"center"})}'
    new_jump = 'function jumpToIssue(i){history.replaceState(null,"",`#/${activeCharacter}/${routeIssueToken(i)}`);$( `issue-${i.seriesId}-${i.n}` )?.scrollIntoView({behavior:"smooth",block:"center"})}'
    if old_jump in app:
        app = app.replace(old_jump, new_jump, 1)
    elif "routeIssueToken(i)" not in app:
        raise RuntimeError("jumpToIssue non riconosciuto")

    old_hash = 'window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.view==="home"){showHome({updateHash:false});return}if(els.trackerView.hidden||!currentCharacter||h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=currentCharacter.issues.find(x=>x.n===h.issue);if(i)jumpToIssue(i)}});'
    new_hash = 'window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.view==="home"){showHome({updateHash:false});return}if(els.trackerView.hidden||!currentCharacter||h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=resolveIssueToken(currentCharacter,h.issue);if(i)jumpToIssue(i)}});'
    if old_hash in app:
        app = app.replace(old_hash, new_hash, 1)
    elif "const i=resolveIssueToken(currentCharacter,h.issue)" not in app:
        raise RuntimeError("hashchange non riconosciuto")

    notice_old = 'function renderNotices(){const id=activeCharacter,ns=[];if(id==="ironman")'
    notice_new = 'function renderNotices(){const id=activeCharacter,ns=[];if(id==="avengers")ns.push(["Timeline Vendicatori","Il percorso attraversa più testate italiane. Il numero grande è sempre la tappa narrativa; il titolo della card identifica l’albo fisico da recuperare."],["Percorso moderno dal 1994","Sono escluse le edizioni Corno e Star Comics: si parte dal rilancio Marvel Italia e si seguono le pubblicazioni italiane moderne."]);if(id==="ironman")'
    if notice_old in app:
        app = app.replace(notice_old, notice_new, 1)
    elif 'id==="avengers"' not in app:
        raise RuntimeError("renderNotices non riconosciuto")

    app_path.write_text(app, encoding="utf-8")

    css_path = ROOT / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    marker = "/* Avengers timeline support */"
    if marker not in css:
        css += '\n' + marker + '\n.timelineBlock>.seriesHead{padding:0 3px 5px}.issueBadges{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:5px}.publicationBadge{display:inline-flex;padding:3px 7px;border-radius:999px;border:1px solid var(--line2);background:#0a1118;color:var(--muted);font-size:7px;font-weight:900;letter-spacing:.04em;text-transform:uppercase}.timelineBlock .era{scroll-margin-top:92px}@media(min-width:1121px){.publicationBadge{font-size:8px;padding:4px 8px}.timelineBlock>.seriesHead h2{font-size:30px}}\n/* /Avengers timeline support */\n'
        css_path.write_text(css, encoding="utf-8")

    index_path = ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = index.replace('<div class="label" style="margin-bottom:7px">Personaggi</div>', '<div class="label" style="margin-bottom:7px">Percorsi</div>')
    index = index.replace('Scegli il prossimo eroe', 'Scegli il prossimo percorso')
    index = index.replace('css/app.css?v=5', 'css/app.css?v=6').replace('js/app.js?v=5', 'js/app.js?v=6')
    index_path.write_text(index, encoding="utf-8")

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    verify = verify.replace('assert.equal(manifest.version, 2, "Il manifest deve usare la versione cache v2");', 'assert.equal(manifest.version, 3, "Il manifest deve usare la versione cache v3");')
    verify_path.write_text(verify, encoding="utf-8")

    rebuild_path = ROOT / "scripts" / "rebuild_character_data.py"
    rebuild = rebuild_path.read_text(encoding="utf-8").replace('manifest["version"] = 2', 'manifest["version"] = 3')
    rebuild_path.write_text(rebuild, encoding="utf-8")


def write_logo_placeholder() -> None:
    logo = ROOT / "assets" / "heroes" / "avengers.svg"
    logo.parent.mkdir(parents=True, exist_ok=True)
    logo.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="Placeholder Vendicatori">
<rect width="128" height="128" rx="26" fill="#080d13"/>
<circle cx="64" cy="64" r="48" fill="none" stroke="#6fa8ff" stroke-width="6"/>
<path d="M43 92 61 34h13l17 58H78l-4-16H56l-4 16H43Zm16-27h12l-6-23-6 23Z" fill="#eef4f8"/>
<path d="M81 36h17v12H84" fill="#6fa8ff"/>
</svg>''', encoding="utf-8")


def main() -> None:
    ironman = unpack_character("ironman")
    thor = unpack_character("thor")
    lookup = {issue["id"]: issue for issue in ironman["issues"] + thor["issues"]}

    vendicatori = fetch_all_series("VEN_M", max_pages=2)
    avengers_monthly = fetch_all_series("AVENGERS_M", max_pages=8)

    issues: list[dict] = []
    for number in sorted(vendicatori):
        issues.append(build_dedicated_issue("VEN_M", "Vendicatori", "Marvel Italia", vendicatori[number], number))

    candidates: list[tuple[dict, str]] = []
    for sid, first, last, shared in (
        ("IM_VEN", 1, 89, "Iron Man"),
        ("THORVE_M", 1, 170, "Thor"),
        ("IM_VEN2", 1, 62, "Iron Man"),
    ):
        for number in range(first, last + 1):
            physical = lookup.get(f"{sid}:{number}")
            if physical:
                candidates.append((physical, shared))

    print(f"Analizzo {len(candidates)} albi antologici per individuare il materiale Avengers…")
    selected: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(scan_avengers_content, physical): (physical, shared) for physical, shared in candidates}
        for future in as_completed(futures):
            physical, shared = futures[future]
            include, sources = future.result()
            if not include:
                continue
            issue = anthology_issue(physical, sources, shared)
            issue["era"], issue["eraSub"] = avengers_era(issue)
            selected.append(issue)
    issues.extend(selected)

    for number in sorted(avengers_monthly):
        issues.append(build_dedicated_issue("AVENGERS_M", "Avengers", "Panini Comics", avengers_monthly[number], number))

    # One global timeline: publication date is the primary bridge between parallel
    # Italian anthology titles; series priority gives deterministic ordering when
    # two issues share the same month.
    issues.sort(key=lambda i: (*date_key(i["date"]), SERIES_PRIORITY.get(i["seriesId"], 99), i["n"]))
    for seq, issue in enumerate(issues, 1):
        issue["seq"] = seq

    if not issues:
        raise RuntimeError("Percorso Vendicatori vuoto")

    latest = max(avengers_monthly)
    end_date = italian_date(avengers_monthly[latest]["date"])
    character = {
        "id": "avengers",
        "name": "Vendicatori",
        "subtitle": "Gli Eroi più potenti della Terra",
        "accent": "#6fa8ff",
        "start": "Vendicatori #0 — Aprile 1994",
        "end": f"Avengers #{latest} — {end_date}",
        "description": "Percorso moderno italiano dei Vendicatori: una timeline unica che attraversa le diverse testate Marvel Italia e Panini seguendo solo gli albi con materiale Avengers.",
        "timelineMode": True,
        "series": [
            {"id": "VEN_M", "name": "Vendicatori", "publisher": "Marvel Italia", "range": "#0–23", "years": "1994–1996"},
            {"id": "IM_VEN", "name": "Iron Man e i Vendicatori", "publisher": "Marvel Italia", "range": "solo albi con storie Avengers", "years": "1996–2008"},
            {"id": "THORVE_M", "name": "Thor / Nuovi Vendicatori", "publisher": "Marvel Italia", "range": "solo albi con storie Avengers", "years": "1999–2013"},
            {"id": "IM_VEN2", "name": "Iron Man e i potenti Vendicatori", "publisher": "Marvel Italia", "range": "solo albi con storie Avengers", "years": "2008–2013"},
            {"id": "AVENGERS_M", "name": "Avengers", "publisher": "Panini Comics", "range": f"#1–{latest}", "years": "2012–2026"},
        ],
        "archives": [],
        "totalRequired": len(issues),
        "issues": issues,
    }

    pack_character(character)

    meta = {key: value for key, value in character.items() if key != "issues"}
    meta["issueSources"] = ["data/encoded/avengers.json"]
    (DATA / "characters" / "avengers.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    manifest_path = DATA / "characters.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = 3
    entry = {
        "id": "avengers",
        "name": "Vendicatori",
        "subtitle": "Gli Eroi più potenti della Terra",
        "accent": "#6fa8ff",
        "logo": "assets/heroes/avengers.svg",
        "data": "data/characters/avengers.json",
        "start": character["start"],
        "end": character["end"],
        "totalRequired": character["totalRequired"],
    }
    existing = next((item for item in manifest["characters"] if item["id"] == "avengers"), None)
    if existing:
        existing.update(entry)
    else:
        manifest["characters"].append(entry)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    write_logo_placeholder()
    patch_ui()

    by_series: dict[str, int] = {}
    for issue in issues:
        by_series[issue["seriesId"]] = by_series.get(issue["seriesId"], 0) + 1
    print("Percorso Vendicatori generato:", ", ".join(f"{sid}={count}" for sid, count in by_series.items()))
    print(f"Totale tappe narrative: {len(issues)}")


if __name__ == "__main__":
    main()
