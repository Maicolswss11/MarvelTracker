#!/usr/bin/env python3
"""Build the classic Marvel 2099 universe from Italian physical editions.

The universe path tracks first-print Italian anthologies. Character paths reuse
the same physical IDs and scope each step to the relevant US contents.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHARACTERS = DATA / "characters"

MONTHS = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]


def dump(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def monthly(start_year: int, start_month: int, count: int) -> list[tuple[int, int]]:
    result = []
    year, month = start_year, start_month
    for _ in range(count):
        result.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def issue(
    series_id: str,
    number: int,
    series: str,
    title: str,
    year: int,
    month: int,
    publisher: str,
    *,
    display_number: str | None = None,
) -> dict[str, Any]:
    code = f"{series_id}_{number:03d}"
    name = series if series_id == "2099SPE" else f"{series} #{display_number or number}"
    return {
        "id": f"{series_id}:{number}",
        "n": number,
        **({"displayNumber": display_number} if display_number is not None else {}),
        "name": name,
        "title": title,
        "date": f"{MONTHS[month - 1]} {year}",
        "seriesId": series_id,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
        "_date": date(year, month, 1).isoformat(),
    }


PHYSICAL: OrderedDict[str, dict[str, Any]] = OrderedDict()


def register(row: dict[str, Any]) -> None:
    PHYSICAL[row["id"]] = row


register(issue(
    "2099SPE", 0, "Marvel 2099 Speciale", "2099 Speciale ZERO",
    1993, 4, "Star Comics", display_number="0",
))

UR_TITLES = [
    "Il ragno del futuro", "Battesimo del fuoco", "Lo Specialista",
    "Giuramento di sangue", "Downtown", "Le ali della speranza",
    "Castelli in aria", "Casa dolce casa", "Dietro la maschera",
    "Sotto assedio", "Thanatos", "Profani e profeti", "Punto di ebollizione",
    "Nulla si trasforma", "Comando a distanza", "Si alza il martello",
    "Cade il Martello", "Bloodsword contro l'Uomo Ragno 2099", "2099",
    "Ah, sì?", "Errore di sistema", "Ecco! Sono io l'Uomo Ragno 2099",
    "Pericolo! Non toccatelo!", "Vecchi amici... nuovi nemici!",
    "È il momento della verità...", "The Web of Life", "Welcome to Nightshade",
    "Travesty", "Svendita totale", "Bugaboo / Route 666",
]
for number, ((year, month), title) in enumerate(zip(monthly(1993, 6, 30), UR_TITLES), 1):
    register(issue(
        "UR2099", number, "L'Uomo Ragno 2099", title, year, month,
        "Star Comics" if number <= 11 else "Marvel Italia",
    ))

XM_TITLES = [
    "Il Raduno", "Synge City Blues", "Viva Las Vegas!", "La stanza oscura",
    "Cade il Martello", "Arrivano... i Freakshow!", "Skullfire!",
    "Venti spettrali!", "Il segreto di Xi'An", "Il ritorno di... la Lunatica!",
    "Il mistero di Driver!", "Benvenuto al Teatro del Dolore!", "Metalhead",
    "La prossima fase di Metalhead", "Halloween Jack", "Strani giorni",
    "Ecco a voi i Free Radical Chic", "Battaglia a Las Vegas",
]
for number, ((year, month), title) in enumerate(zip(monthly(1994, 6, 18), XM_TITLES), 1):
    register(issue("XM2099", number, "X-Men 2099", title, year, month, "Marvel Italia"))

SPECIAL_MONTHS = [(1994, 11), (1994, 11)] + monthly(1995, 2, 16)
SPECIAL_TITLES = {
    0: "L'Uomo Ragno 2099 ZERO",
    1: "Nuove storie dal futuro",
    2: "Ghost Rider 2099",
    8: "Arriva... Infarto!",
    14: "E la città sarà sommersa dal sangue!",
    15: "È sempre più buio... prima dell'alba",
    17: "La fine del viaggio!",
}
for number, (year, month) in zip(range(0, 18), SPECIAL_MONTHS):
    register(issue(
        "2099SPEC_P", number, "2099 Special", SPECIAL_TITLES.get(number, "Universo Marvel 2099"),
        year, month, "Marvel Italia", display_number=str(number),
    ))

AD_TITLES = [
    "Una nazione sotto Doom", "La nuova era", "Mr. O'Hara va a Washington",
    "L'Uomo Ragno contro Venom", "Venom 2099", "L'ultimo sipario",
    "Io odio l'Uomo Ragno 2099", "La città dei morti", "Shockriding",
    "Goblin 2099", "Goblin ti tiene in pugno!", "Le profezie di Doom",
    "X-Men 2099 Special",
]
for number, ((year, month), title) in enumerate(zip(monthly(1995, 12, 13), AD_TITLES), 1):
    register(issue("2099AD", number, "2099 AD", title, year, month, "Marvel Italia"))

register(issue("MCROS_M", 10, "Marvel Crossover", "2099 AD 0", 1995, 12, "Marvel Italia"))
register(issue("MCROS_M", 13, "Marvel Crossover", "2099 Apocalypse", 1996, 7, "Marvel Italia"))
register(issue("MAROMNIB", 219, "Marvel Omnibus", "X-Men 2099", 2025, 3, "Panini Comics"))
register(issue("MAROMNIB", 233, "Marvel Omnibus", "Fantastici Quattro/Destino 2099", 2025, 9, "Panini Comics"))


CONTENT_META = {
    "SM2099": "Spider-Man 2099",
    "SM2099ANN": "Spider-Man 2099 Annual",
    "DOOM2099": "Doom 2099",
    "PUN2099": "Punisher 2099",
    "XMEN2099": "X-Men 2099",
    "XM2099SP": "X-Men 2099 Special",
    "XM2099OASIS": "X-Men 2099: Oasis",
    "GR2099": "Ghost Rider 2099",
    "2099ADUS": "2099 A.D.",
    "2099UNLIM": "2099 Unlimited",
    "2099APOC": "2099 Apocalypse",
}


def content(content_id: str) -> dict[str, Any]:
    series_id, number = content_id.split(":", 1)
    return {
        "id": content_id,
        "series": CONTENT_META[series_id],
        "number": number,
    }


PATH_CONTENTS: dict[str, OrderedDict[str, list[str]]] = {
    path_id: OrderedDict()
    for path_id in ("spiderman-2099", "doom-2099", "punisher-2099", "xmen-2099", "ghost-rider-2099")
}


def map_content(path_id: str, physical_id: str, *content_ids: str) -> None:
    bucket = PATH_CONTENTS[path_id].setdefault(physical_id, [])
    for content_id in content_ids:
        if content_id not in bucket:
            bucket.append(content_id)


# Spider-Man 2099 #1–46, Annual #1 and the short chapters split by Marvel Italia.
map_content("spiderman-2099", "2099SPE:0", "SM2099:1")
for us_number, italian_number in zip(range(2, 15), range(1, 14)):
    map_content("spiderman-2099", f"UR2099:{italian_number}", f"SM2099:{us_number}")
for us_number, italian_number in [
    (15, 16), (16, 17), (17, 18), (18, 19), (19, 20), (20, 21),
    (21, 23), (22, 22), (23, 24), (24, 25), (25, 25), (26, 26),
    (27, 27), (28, 28), (29, 29), (30, 30), (31, 30),
]:
    map_content("spiderman-2099", f"UR2099:{italian_number}", f"SM2099:{us_number}")
map_content("spiderman-2099", "UR2099:21", "SM2099ANN:1")
map_content("spiderman-2099", "XM2099:13", "SM2099:25")
map_content("spiderman-2099", "2099SPEC_P:4", "SM2099:25")
for physical_id, content_ids in [
    ("2099AD:1", ["SM2099:32"]),
    ("2099AD:2", ["SM2099:32", "SM2099:33"]),
    ("2099AD:3", ["SM2099:34"]),
    ("2099AD:4", ["SM2099:35"]),
    ("2099AD:5", ["SM2099:36", "SM2099:37"]),
    ("2099AD:7", ["SM2099:38"]),
    ("2099AD:8", ["SM2099:39"]),
    ("2099AD:10", ["SM2099:40"]),
    ("2099AD:11", ["SM2099:41"]),
    ("2099AD:12", ["SM2099:42"]),
    ("2099AD:13", ["SM2099:43", "SM2099:44"]),
    ("2099SPEC_P:14", ["SM2099:45"]),
    ("2099SPEC_P:16", ["SM2099:46"]),
]:
    map_content("spiderman-2099", physical_id, *content_ids)

# Doom 2099 #1–44. The 2025 omnibus is scoped only to the chapters never printed
# in the classic Italian magazines, avoiding a forced reread of #1–39.
map_content("doom-2099", "2099SPE:0", "DOOM2099:1")
for us_number, italian_number in [
    (2, 1), (3, 3), (4, 4), (5, 6), (6, 7), (7, 8), (8, 9), (9, 11), (10, 10),
]:
    map_content("doom-2099", f"UR2099:{italian_number}", f"DOOM2099:{us_number}")
for us_number, italian_number in [
    (11, 2), (12, 3), (13, 4), (14, 5), (15, 6), (16, 12), (17, 7),
    (18, 8), (19, 9), (20, 10), (21, 11), (22, 12), (23, 13), (24, 14),
    (25, 15), (26, 16), (27, 17), (28, 18),
]:
    map_content("doom-2099", f"XM2099:{italian_number}", f"DOOM2099:{us_number}")
map_content("doom-2099", "2099SPEC_P:5", "DOOM2099:25-extra")
map_content("doom-2099", "MCROS_M:10", "2099ADUS:0")
for us_number, italian_number in [
    (29, 1), (30, 2), (31, 3), (32, 4), (33, 5), (34, 6), (35, 7),
    (36, 8), (37, 9), (38, 11), (39, 12),
]:
    map_content("doom-2099", f"2099AD:{italian_number}", f"DOOM2099:{us_number}")
map_content(
    "doom-2099", "MAROMNIB:233", "DOOM2099:39-extra", "DOOM2099:40",
    "DOOM2099:41", "DOOM2099:42", "DOOM2099:43", "DOOM2099:44",
)

# Punisher 2099 #1–28: #29–34 remain unavailable in an Italian edition.
map_content("punisher-2099", "2099SPE:0", "PUN2099:1")
for us_number, italian_number in [
    (2, 2), (3, 5), (4, 8), (5, 9), (6, 10), (7, 11), (8, 12), (9, 13),
    (10, 14), (11, 15), (12, 17), (14, 18), (15, 19), (16, 20),
    (17, 21), (18, 22), (19, 23), (20, 24), (21, 25), (22, 26),
    (23, 27), (24, 28), (25, 29), (26, 30),
]:
    map_content("punisher-2099", f"UR2099:{italian_number}", f"PUN2099:{us_number}")
map_content("punisher-2099", "XM2099:5", "PUN2099:13")
map_content("punisher-2099", "2099SPEC_P:5", "PUN2099:25-extra")
map_content("punisher-2099", "2099SPEC_P:7", "PUN2099:27", "PUN2099:28")

# X-Men 2099 #1–35 plus the Special and Oasis. The 2025 omnibus contributes
# only the two previously unavailable stories to the physical reading route.
for us_number, italian_number in [
    (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8),
    (9, 9), (10, 10), (11, 11), (12, 11), (13, 12), (14, 13), (15, 14),
    (16, 15), (17, 16), (18, 17), (19, 18), (20, 18),
]:
    map_content("xmen-2099", f"XM2099:{italian_number}", f"XMEN2099:{us_number}")
for us_number, italian_number in [
    (21, 1), (22, 2), (23, 3), (24, 4), (25, 6), (26, 7), (27, 8),
    (28, 10), (29, 11), (30, 12),
]:
    map_content("xmen-2099", f"2099AD:{italian_number}", f"XMEN2099:{us_number}")
for us_number, italian_number in [(31, 13), (32, 15), (33, 16), (34, 17), (35, 17)]:
    map_content("xmen-2099", f"2099SPEC_P:{italian_number}", f"XMEN2099:{us_number}")
map_content("xmen-2099", "2099AD:13", "XM2099SP:main")
map_content("xmen-2099", "MCROS_M:13", "XM2099SP:halloween")
map_content("xmen-2099", "MAROMNIB:219", "XM2099SP:shakti", "XM2099OASIS:1")

# Ghost Rider 2099 #1–25, completely published across 2099 Special.
for physical_number, numbers in [
    (2, range(1, 5)), (3, range(5, 8)), (4, range(8, 10)),
    (5, range(10, 12)), (6, range(12, 13)), (7, range(13, 15)),
    (8, range(15, 17)), (9, range(17, 19)), (10, range(19, 21)),
    (12, range(21, 23)), (13, range(23, 24)), (14, range(24, 25)),
    (15, range(25, 26)),
]:
    map_content(
        "ghost-rider-2099", f"2099SPEC_P:{physical_number}",
        *(f"GR2099:{number}" for number in numbers),
    )


def all_contents_by_issue() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {issue_id: [] for issue_id in PHYSICAL}
    for mapping in PATH_CONTENTS.values():
        for issue_id, content_ids in mapping.items():
            for content_id in content_ids:
                if content_id not in result[issue_id]:
                    result[issue_id].append(content_id)
    result["MCROS_M:10"].append("2099UNLIM:9-spider")
    result["MCROS_M:13"].extend(["2099APOC:1", "2099UNLIM:10-chameleon"])
    return result


ALL_CONTENTS = all_contents_by_issue()


def era_for(row: dict[str, Any]) -> str:
    issue_id = row["id"]
    if issue_id.startswith("MAROMNIB"):
        return "Recuperi moderni degli inediti"
    if issue_id in {"MCROS_M:10", "MCROS_M:13"}:
        return "Eventi e crossover 2099"
    if issue_id in {"UR2099:16", "UR2099:17", "UR2099:18", "XM2099:5"}:
        return "Cade il Martello"
    if issue_id.startswith("2099AD"):
        return "One Nation Under Doom"
    if issue_id.startswith("2099SPEC_P") and row["n"] >= 13:
        return "La fine del mondo 2099"
    if row["_date"] < "1994-06-01":
        return "La nascita del 2099"
    return "L'universo si espande"


def instruction_for(content_ids: list[str], *, master: bool = False) -> str:
    if not content_ids:
        return "Leggi l'intero albo antologico del 2099."
    labels = [f"{content(value)['series']} #{content(value)['number']}" for value in content_ids]
    prefix = "Contenuti mappati" if master else "Leggi"
    return f"{prefix}: " + " · ".join(labels) + "."


def make_issue(row: dict[str, Any], seq: int, content_ids: list[str], *, master: bool = False) -> dict[str, Any]:
    result = {key: deepcopy(value) for key, value in row.items() if not key.startswith("_")}
    result["seq"] = seq
    result["era"] = era_for(row)
    result["instruction"] = instruction_for(content_ids, master=master)
    if content_ids:
        result["contents"] = [content(value) for value in content_ids]
        result["contentsStatus"] = "path-scoped"
        result["readingStep"] = {"position": seq, "contentIds": content_ids}
    return result


MASTER_SERIES_ORDER = {
    "2099SPE": 0, "UR2099": 1, "XM2099": 2, "2099SPEC_P": 3,
    "MCROS_M": 4, "2099AD": 5, "MAROMNIB": 6,
}


def master_rows() -> list[dict[str, Any]]:
    ordered = sorted(
        PHYSICAL.values(),
        key=lambda row: (row["_date"], MASTER_SERIES_ORDER[row["seriesId"]], row["n"]),
    )
    output = []
    position = 0
    for row in ordered:
        is_optional_reprint = row["id"] == "2099SPEC_P:0"
        if not is_optional_reprint:
            position += 1
        built = make_issue(row, position if not is_optional_reprint else 0, ALL_CONTENTS[row["id"]], master=True)
        if is_optional_reprint:
            built["required"] = False
            built["skip"] = True
            built["instruction"] = "Ristampa facoltativa del Marvel 2099 Speciale ZERO del 1993."
        output.append(built)
    return output


PATH_CONFIG = {
    "spiderman-2099": {
        "name": "Spider-Man 2099",
        "subtitle": "Miguel O'Hara · Terra-928",
        "accent": "#e43f68",
        "start": "Marvel 2099 Speciale — Aprile 1993",
        "end": "2099 Special #16 — Giugno 1997",
        "description": "La serie classica completa di Miguel O'Hara nelle prime edizioni italiane: Spider-Man 2099 #1–46, l'Annual e i capitoli brevi distribuiti nelle collane antologiche. Ogni card indica soltanto le storie di Miguel da leggere dentro l'albo fisico.",
        "relatedPaths": ["marvel-2099", "xmen-2099", "doom-2099"],
    },
    "doom-2099": {
        "name": "Doom 2099",
        "subtitle": "Victor von Doom · Terra-928",
        "accent": "#69d28b",
        "start": "Marvel 2099 Speciale — Aprile 1993",
        "end": "Marvel Omnibus #233 — Settembre 2025",
        "description": "Doom 2099 #1–44 in ordine narrativo. Le edizioni Marvel Italia coprono #1–39; l'ultima tappa usa l'Omnibus Fantastici Quattro/Destino 2099 soltanto per il capitolo breve di #39 e per #40–44, allora inediti in Italia.",
        "relatedPaths": ["marvel-2099", "spiderman-2099", "doctor-doom"],
    },
    "punisher-2099": {
        "name": "Punisher 2099",
        "subtitle": "Jake Gallows · Terra-928",
        "accent": "#ff8b5c",
        "start": "Marvel 2099 Speciale — Aprile 1993",
        "end": "2099 Special #7 — Dicembre 1995",
        "description": "Il percorso italiano disponibile di Jake Gallows: Punisher 2099 #1–28, compresi i capitoli brevi, ricostruiti nelle antologie Star Comics e Marvel Italia. I numeri USA #29–34 sono esclusi perché non risultano pubblicati in italiano.",
        "relatedPaths": ["marvel-2099", "punisher", "doom-2099"],
    },
    "xmen-2099": {
        "name": "X-Men 2099",
        "subtitle": "Xi'an Chi Xan e i mutanti di Halo City",
        "accent": "#f0cb55",
        "start": "X-Men 2099 #1 — Giugno 1994",
        "end": "Marvel Omnibus #219 — Marzo 2025",
        "description": "X-Men 2099 #1–35 nelle edizioni Marvel Italia, più lo Special e Oasis. L'Omnibus 2025 è usato soltanto per i racconti che non avevano avuto una precedente edizione italiana, senza duplicare la lettura dei diciotto spillati originali.",
        "relatedPaths": ["marvel-2099", "spiderman-2099", "xmen"],
    },
    "ghost-rider-2099": {
        "name": "Ghost Rider 2099",
        "subtitle": "Kenshiro “Zero” Cochrane · Terra-928",
        "accent": "#ff6a32",
        "start": "2099 Special #2 — Febbraio 1995",
        "end": "2099 Special #15 — Aprile 1997",
        "description": "La serie completa Ghost Rider 2099 #1–25 di Len Kaminski, pubblicata integralmente in Italia dentro 2099 Special. Le card raggruppano i capitoli USA contenuti in ogni volume fisico.",
        "relatedPaths": ["marvel-2099", "ghost-rider", "doom-2099"],
    },
}


def series_summary(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        current = grouped.setdefault(row["seriesId"], {
            "id": row["seriesId"], "name": row["series"], "publisher": row["publisher"], "numbers": [],
        })
        current["numbers"].append(int(row["n"]))
    result = []
    for current in grouped.values():
        numbers = current.pop("numbers")
        low, high = min(numbers), max(numbers)
        current["range"] = f"#{low}" if low == high else f"#{low}–{high}"
        result.append(current)
    return result


def build_path(path_id: str) -> dict[str, Any]:
    config = PATH_CONFIG[path_id]
    mapping = PATH_CONTENTS[path_id]
    rows = [PHYSICAL[issue_id] for issue_id in mapping]
    issues = [make_issue(row, seq, mapping[row["id"]]) for seq, row in enumerate(rows, 1)]
    return {
        "id": path_id,
        "name": config["name"],
        "subtitle": config["subtitle"],
        "accent": config["accent"],
        "start": config["start"],
        "end": config["end"],
        "description": config["description"],
        "timelineMode": True,
        "series": series_summary(rows),
        "archives": [],
        "relatedPaths": config["relatedPaths"],
        "totalRequired": len(issues),
        "issues": issues,
    }


def build_master() -> dict[str, Any]:
    issues = master_rows()
    required = [row for row in issues if row.get("required") is not False]
    return {
        "id": "marvel-2099",
        "name": "Marvel 2099",
        "subtitle": "Terra-928 · percorso classico italiano",
        "accent": "#55dff6",
        "start": "Marvel 2099 Speciale — Aprile 1993",
        "end": "Marvel Omnibus #233 — Settembre 2025",
        "description": "Percorso master dell'universo Marvel 2099 classico nelle edizioni italiane. Segue 83 albi necessari fra antologie, crossover e recuperi moderni degli inediti; 2099 Special #0 resta visibile come ristampa facoltativa. Lo stato Fisico/Digitale è condiviso con tutti i percorsi personali.",
        "timelineMode": True,
        "series": series_summary([PHYSICAL[row["id"]] for row in issues]),
        "archives": [],
        "relatedPaths": list(PATH_CONFIG),
        "totalRequired": len(required),
        "issues": issues,
    }


def update_manifest(paths: list[dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    new_ids = {row["id"] for row in paths}
    manifest["characters"] = [row for row in manifest["characters"] if row["id"] not in new_ids]
    types = {
        "marvel-2099": "universe",
        "spiderman-2099": "character",
        "doom-2099": "character",
        "punisher-2099": "character",
        "xmen-2099": "team",
        "ghost-rider-2099": "character",
    }
    logos = {
        path_id: f"assets/heroes/{path_id}.svg"
        for path_id in new_ids
    }
    for data in paths:
        manifest["characters"].append({
            "id": data["id"],
            "name": data["name"],
            "subtitle": data["subtitle"],
            "type": types[data["id"]],
            "universe": "Terra-928",
            "primaryHub": "marvel-2099",
            "hubs": ["marvel-2099"],
            "accent": data["accent"],
            "logo": logos[data["id"]],
            "data": f"data/characters/{data['id']}.json",
            "start": data["start"],
            "end": data["end"],
            "totalRequired": data["totalRequired"],
            "relatedPaths": data["relatedPaths"],
        })
    manifest["version"] = max(int(manifest.get("version", 0)), 30)
    dump(path, manifest, compact=True)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = max(int(payload.get("version", 0)), 2)
    payload["hubs"] = [hub for hub in payload["hubs"] if hub["id"] != "marvel-2099"]
    alternate = next(hub for hub in payload["hubs"] if hub["id"] == "alternate")
    alternate.pop("status", None)
    alternate["subtitle"] = "Marvel 2099 e le grandi realtà parallele"
    alternate["sections"] = [{
        "id": "realities",
        "label": "Realtà alternative",
        "items": ["marvel-2099"],
    }]
    alternate["groups"] = []
    child = {
        "id": "marvel-2099",
        "name": "Marvel 2099",
        "subtitle": "Terra-928 · il futuro distopico Marvel nelle edizioni italiane",
        "type": "universe",
        "accent": "#55dff6",
        "parent": "alternate",
        "groups": [
            {"id": "master", "label": "Segui tutto l'universo", "paths": ["marvel-2099"]},
            {"id": "icons", "label": "Icone del 2099", "paths": ["spiderman-2099", "doom-2099", "punisher-2099", "ghost-rider-2099"]},
            {"id": "mutants", "label": "Mutanti del futuro", "paths": ["xmen-2099"]},
        ],
        "featuredPath": "marvel-2099",
    }
    alternate_index = payload["hubs"].index(alternate)
    payload["hubs"].insert(alternate_index + 1, child)
    dump(path, payload, compact=True)


def write_audit(paths: list[dict[str, Any]]) -> None:
    audit = {
        "version": 1,
        "scope": "Marvel 2099 classico nelle edizioni italiane",
        "physicalIssues": len(PHYSICAL),
        "requiredMasterIssues": next(row["totalRequired"] for row in paths if row["id"] == "marvel-2099"),
        "optionalReprints": ["2099SPEC_P:0"],
        "paths": {row["id"]: row["totalRequired"] for row in paths},
        "knownItalianGaps": {
            "punisher-2099": ["Punisher 2099 #29–34"],
        },
        "scopedModernRecoveries": {
            "MAROMNIB:219": ["X-Men 2099 Special: Shakti", "X-Men 2099: Oasis #1"],
            "MAROMNIB:233": ["Doom 2099 #39 (storia breve)", "Doom 2099 #40–44"],
        },
        "sources": [
            "https://www.comicsbox.it/serie/UR2099",
            "https://www.comicsbox.it/serie/XM2099",
            "https://www.comicsbox.it/serie/2099SPEC_P",
            "https://www.comicsbox.it/serie/2099AD",
            "https://www.comicsbox.it/serie/MCROS_M",
            "https://www.comicsbox.it/serie/SM12099",
            "https://www.comicsbox.it/serie/DOOM2099",
            "https://www.comicsbox.it/serie/PUN2099",
            "https://www.comicsbox.it/serie/XMEN2099",
            "https://www.comicsbox.it/serie/GR2099",
        ],
    }
    dump(DATA / "marvel-2099-audit.json", audit)


def main() -> None:
    paths = [build_master(), *(build_path(path_id) for path_id in PATH_CONFIG)]
    for payload in paths:
        dump(CHARACTERS / f"{payload['id']}.json", payload)
    update_manifest(paths)
    update_hubs()
    write_audit(paths)
    print("Marvel 2099:", ", ".join(f"{row['id']}={row['totalRequired']}" for row in paths))


if __name__ == "__main__":
    main()
