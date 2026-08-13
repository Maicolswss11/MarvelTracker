#!/usr/bin/env python3
"""Build the What If...? alternate-realities hub from Italian editions.

The master route follows six Panini collections. Child routes reuse the same
physical IDs and expose only the US stories relevant to a character, team,
event or editorial cycle.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHARACTERS = DATA / "characters"


def dump(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def physical(
    series_id: str,
    number: int,
    series: str,
    title: str,
    date: str,
    cover_code: str,
) -> dict[str, Any]:
    return {
        "id": f"{series_id}:{number}",
        "n": number,
        "name": f"{series} #{number}",
        "title": title,
        "date": date,
        "seriesId": series_id,
        "series": series,
        "publisher": "Panini Comics",
        "cover": f"https://www.comicsbox.it/cover/{cover_code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_code}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
    }


PHYSICAL: OrderedDict[str, dict[str, Any]] = OrderedDict()


def register(row: dict[str, Any]) -> None:
    PHYSICAL[row["id"]] = row


register(physical(
    "MARVGEEKS", 17, "Marvel Geeks", "What If? Classic 1",
    "Giugno 2021", "MARVGEEKS_017",
))
register(physical(
    "MARVGEEKS", 33, "Marvel Geeks", "What If? Classic 2",
    "Agosto 2022", "MARVGEEKS_033",
))
register(physical(
    "MVNWCOL_P", 436, "Marvel Collection (II)",
    "What If...? Miles Morales: Quanti Miles ci vogliono per...?",
    "Ottobre 2022", "MVNWCOL_P_436",
))
register(physical(
    "MARVGEEKS", 35, "Marvel Geeks", "What If? Classic 3",
    "Febbraio 2023", "MARVGEEKS_035",
))
register(physical(
    "MVNWCOL_P", 567, "Marvel Collection (II)",
    "What If...? Dark: Multiverso Oscuro",
    "Aprile 2024", "MVNWCOL_P_567",
))
register(physical(
    "MVNWCOL_P", 603, "Marvel Collection (II)",
    "What If...? Venom: Il Simbionte Supremo",
    "Ottobre 2024", "MVNWCOL_P_603",
))


CONTENT_NAMES = {
    "WHIF1": "What If? vol. 1",
    "WHATIFMM": "What If...? Miles Morales",
    "WIFDARKLOK": "What If...? Dark: Loki",
    "WIFDARKGWN": "What If...? Dark: Spider-Gwen",
    "WIFDARKVEN": "What If...? Dark: Venom",
    "WIFDARKMK": "What If...? Dark: Moon Knight",
    "WIFDARKCARN": "What If...? Dark: Carnage",
    "WIFDARKTOD": "What If...? Dark: Tomb of Dracula",
    "WIFVENOM": "What If...? Venom",
}


def content_id(series_id: str, number: int | str) -> str:
    return f"{series_id}:{number}"


def run(series_id: str, numbers: Iterable[int | str]) -> list[str]:
    return [content_id(series_id, number) for number in numbers]


def content(value: str) -> dict[str, str]:
    series_id, number = value.split(":", 1)
    series = CONTENT_NAMES[series_id]
    return {
        "id": value,
        "series": series,
        "number": number,
        "title": f"{series} #{number}",
    }


CLASSIC_ONE = run("WHIF1", range(1, 7))
CLASSIC_TWO = run("WHIF1", range(7, 13))
CLASSIC_THREE = run("WHIF1", [14, 15, 17, 18, 19, 20])
MILES = run("WHATIFMM", range(1, 6))
DARK = [
    "WIFDARKLOK:1",
    "WIFDARKGWN:1",
    "WIFDARKVEN:1",
    "WIFDARKMK:1",
    "WIFDARKCARN:1",
    "WIFDARKTOD:1",
]
VENOM = run("WIFVENOM", range(1, 6))


MASTER_CONTENTS: OrderedDict[str, list[str]] = OrderedDict([
    ("MARVGEEKS:17", CLASSIC_ONE),
    ("MARVGEEKS:33", CLASSIC_TWO),
    ("MVNWCOL_P:436", MILES),
    ("MARVGEEKS:35", CLASSIC_THREE),
    ("MVNWCOL_P:567", DARK),
    ("MVNWCOL_P:603", VENOM),
])


PATH_CONTENTS: dict[str, OrderedDict[str, list[str]]] = {
    "what-if": MASTER_CONTENTS,
    "what-if-classic": OrderedDict([
        ("MARVGEEKS:17", CLASSIC_ONE),
        ("MARVGEEKS:33", CLASSIC_TWO),
        ("MARVGEEKS:35", CLASSIC_THREE),
    ]),
    "what-if-miles-morales": OrderedDict([("MVNWCOL_P:436", MILES)]),
    "what-if-venom": OrderedDict([("MVNWCOL_P:603", VENOM)]),
    "what-if-dark": OrderedDict([("MVNWCOL_P:567", DARK)]),
    "avengers-1950s-what-if": OrderedDict([("MARVGEEKS:33", ["WHIF1:9"])]),
    "what-if-kree-skrull-war": OrderedDict([("MARVGEEKS:35", ["WHIF1:20"])]),
}


PATH_CONFIG: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("what-if", {
        "name": "What If...?",
        "subtitle": "Infinite possibilità · realtà indipendenti",
        "type": "universe",
        "universe": "Multiverso Marvel",
        "accent": "#45b8e8",
        "start": "Marvel Geeks #17 — Giugno 2021",
        "end": "Marvel Collection (II) #603 — Ottobre 2024",
        "description": "Portale italiano di What If...? costruito su sei raccolte Panini: i primi diciotto racconti classici disponibili nella collana Marvel Geeks e tre cicli moderni dedicati a Miles Morales, alle varianti Dark e al simbionte Venom. Ogni storia apre una realtà autonoma: il master ordina i volumi fisici, mentre i percorsi collegati isolano personaggi, squadre ed eventi senza duplicare la copia posseduta.",
        "relatedPaths": [
            "what-if-classic", "what-if-miles-morales", "what-if-venom",
            "what-if-dark", "avengers-1950s-what-if", "what-if-kree-skrull-war",
        ],
    }),
    ("what-if-classic", {
        "name": "What If? Classic",
        "subtitle": "La serie originale · 1977–1980",
        "type": "collection",
        "universe": "Multiverso Marvel",
        "accent": "#32a9dd",
        "start": "Marvel Geeks #17 — Giugno 2021",
        "end": "Marvel Geeks #35 — Febbraio 2023",
        "description": "I tre volumi Marvel Geeks raccolgono diciotto capitoli della prima serie What If?: numeri 1–12, 14–15 e 17–20. L'ordine segue i capitoli USA, saltando soltanto quelli non inclusi in queste edizioni italiane; ogni episodio è una deviazione indipendente e non forma una singola continuità.",
        "relatedPaths": ["what-if", "avengers-1950s-what-if", "what-if-kree-skrull-war"],
    }),
    ("what-if-miles-morales", {
        "name": "Miles Morales: What If...?",
        "subtitle": "Cinque Miles · cinque destini",
        "type": "character",
        "universe": "Multiverso What If",
        "accent": "#e44d64",
        "start": "Marvel Collection (II) #436 — Ottobre 2022",
        "end": "Marvel Collection (II) #436 — Ottobre 2022",
        "description": "Cinque variazioni complete su Miles Morales: Capitan America, Wolverine, Hulk, Thor e Spider-Man. Il volume termina facendo incontrare le diverse incarnazioni, ma ciascun capitolo nasce in una realtà distinta e il percorso non va confuso con la biografia del Miles dell'Universo Ultimate o di Terra-616.",
        "relatedPaths": ["what-if", "ultimate-spiderman-classic", "spiderman"],
    }),
    ("what-if-venom", {
        "name": "Venom: Il Simbionte Supremo",
        "subtitle": "She-Hulk · Wolverine · Strange · Loki · Moon Knight",
        "type": "character",
        "universe": "Multiverso What If",
        "accent": "#b7d2e7",
        "start": "Marvel Collection (II) #603 — Ottobre 2024",
        "end": "Marvel Collection (II) #603 — Ottobre 2024",
        "description": "La miniserie What If...? Venom completa immagina il simbionte legato a cinque ospiti diversi. I capitoli compongono un esperimento multiversale sul modo in cui Venom amplifica corpo, poteri e conflitti interiori di She-Hulk, Wolverine, Doctor Strange, Loki e Moon Knight.",
        "relatedPaths": ["what-if", "venom", "wolverine-616", "doctor-strange", "moon-knight"],
    }),
    ("what-if-dark", {
        "name": "What If...? Dark",
        "subtitle": "Multiverso Oscuro · sei one-shot",
        "type": "collection",
        "universe": "Multiverso What If",
        "accent": "#8b6fda",
        "start": "Marvel Collection (II) #567 — Aprile 2024",
        "end": "Marvel Collection (II) #567 — Aprile 2024",
        "description": "Sei one-shot completi che riscrivono celebri snodi Marvel in chiave più cupa: Loki e Mjolnir, la notte del ponte di Gwen Stacy, Ben Grimm e Venom, Moon Knight, Carnage e lo scontro fra Blade e Dracula. Non condividono una continuità e vengono riuniti soltanto dal marchio editoriale Dark.",
        "relatedPaths": ["what-if", "thor", "moon-knight", "blade", "venom"],
    }),
    ("avengers-1950s-what-if", {
        "name": "Avengers degli anni Cinquanta",
        "subtitle": "Jimmy Woo e gli eroi dell'era atomica",
        "type": "team",
        "universe": "Realtà alternativa del What If classico",
        "accent": "#e3b341",
        "start": "Marvel Geeks #33 — Agosto 2022",
        "end": "Marvel Geeks #33 — Agosto 2022",
        "description": "Il racconto di What If? #9 immagina una formazione degli Avengers attiva negli anni Cinquanta sotto la guida di Jimmy Woo. La tappa seleziona soltanto quel capitolo dal secondo volume Classic; le successive rielaborazioni degli Agents of Atlas nella continuità principale restano percorsi separati.",
        "relatedPaths": ["what-if", "what-if-classic", "avengers"],
    }),
    ("what-if-kree-skrull-war", {
        "name": "Guerra Kree-Skrull alternativa",
        "subtitle": "Senza Rick Jones · What If? #20",
        "type": "event",
        "universe": "Realtà alternativa del What If classico",
        "accent": "#ef725e",
        "start": "Marvel Geeks #35 — Febbraio 2023",
        "end": "Marvel Geeks #35 — Febbraio 2023",
        "description": "What If? #20 devia dalla Guerra Kree-Skrull chiedendo cosa sarebbe accaduto agli Avengers senza l'intervento decisivo di Rick Jones. È un singolo evento alternativo completo, estratto dal terzo volume Classic e mantenuto distinto dalla cronologia della guerra originale di Terra-616.",
        "relatedPaths": ["what-if", "what-if-classic", "avengers"],
    }),
])


INSTRUCTIONS = {
    ("what-if", "MARVGEEKS:17"): "Leggi What If? vol. 1 #1–6: il primo blocco delle realtà classiche.",
    ("what-if", "MARVGEEKS:33"): "Leggi What If? vol. 1 #7–12: Spider-Man, Avengers, Thor, Fantastici Quattro e Hulk.",
    ("what-if", "MVNWCOL_P:436"): "Leggi What If...? Miles Morales #1–5, miniserie completa.",
    ("what-if", "MARVGEEKS:35"): "Leggi What If? vol. 1 #14–15 e #17–20, come raccolti nel terzo Classic.",
    ("what-if", "MVNWCOL_P:567"): "Leggi i sei one-shot What If...? Dark raccolti nel volume.",
    ("what-if", "MVNWCOL_P:603"): "Leggi What If...? Venom #1–5, miniserie completa.",
    ("what-if-classic", "MARVGEEKS:17"): "Leggi What If? vol. 1 #1–6.",
    ("what-if-classic", "MARVGEEKS:33"): "Prosegui con What If? vol. 1 #7–12.",
    ("what-if-classic", "MARVGEEKS:35"): "Concludi questa selezione con What If? vol. 1 #14–15 e #17–20.",
    ("what-if-miles-morales", "MVNWCOL_P:436"): "Leggi tutti e cinque i capitoli: ogni numero presenta un Miles alternativo e il finale li riunisce.",
    ("what-if-venom", "MVNWCOL_P:603"): "Leggi What If...? Venom #1–5 seguendo i cinque diversi ospiti del simbionte.",
    ("what-if-dark", "MVNWCOL_P:567"): "Leggi i sei one-shot autonomi; non serve un ordine di continuità oltre a quello del volume.",
    ("avengers-1950s-what-if", "MARVGEEKS:33"): "Leggi soltanto What If? vol. 1 #9: gli Avengers formati durante gli anni Cinquanta.",
    ("what-if-kree-skrull-war", "MARVGEEKS:35"): "Leggi soltanto What If? vol. 1 #20: la Guerra Kree-Skrull senza Rick Jones.",
}


ERA_BY_ISSUE = {
    "MARVGEEKS:17": "What If? classico · volume 1",
    "MARVGEEKS:33": "What If? classico · volume 2",
    "MARVGEEKS:35": "What If? classico · volume 3",
    "MVNWCOL_P:436": "Miles Morales alternativi",
    "MVNWCOL_P:567": "Multiverso Oscuro",
    "MVNWCOL_P:603": "Il Simbionte Supremo",
}


def format_range(numbers: list[int]) -> str:
    if len(numbers) == 1:
        return f"#{numbers[0]}"
    if numbers == list(range(numbers[0], numbers[-1] + 1)):
        return f"#{numbers[0]}–{numbers[-1]}"
    return ", ".join(f"#{number}" for number in numbers)


def series_summary(issue_ids: Iterable[str]) -> list[dict[str, str]]:
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for issue_id in issue_ids:
        row = PHYSICAL[issue_id]
        current = grouped.setdefault(row["seriesId"], {
            "id": row["seriesId"],
            "name": row["series"],
            "publisher": row["publisher"],
            "numbers": [],
            "years": [],
        })
        current["numbers"].append(int(row["n"]))
        year = row["date"].split()[-1]
        if year not in current["years"]:
            current["years"].append(year)
    result = []
    for current in grouped.values():
        numbers = current.pop("numbers")
        years = current.pop("years")
        current["range"] = format_range(numbers)
        current["years"] = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"
        result.append(current)
    return result


def make_issue(path_id: str, issue_id: str, seq: int, content_ids: list[str]) -> dict[str, Any]:
    row = deepcopy(PHYSICAL[issue_id])
    row["seq"] = seq
    row["era"] = ERA_BY_ISSUE[issue_id]
    row["instruction"] = INSTRUCTIONS[(path_id, issue_id)]
    row["contents"] = [content(value) for value in content_ids]
    row["contentsStatus"] = "complete" if path_id in {"what-if", "what-if-classic", "what-if-miles-morales", "what-if-venom", "what-if-dark"} else "path-scoped"
    row["readingStep"] = {"position": seq, "contentIds": content_ids, "scope": "selected-contents"}
    return row


def build_path(path_id: str) -> dict[str, Any]:
    config = PATH_CONFIG[path_id]
    mapping = PATH_CONTENTS[path_id]
    issues = [
        make_issue(path_id, issue_id, seq, content_ids)
        for seq, (issue_id, content_ids) in enumerate(mapping.items(), 1)
    ]
    return {
        "id": path_id,
        "name": config["name"],
        "subtitle": config["subtitle"],
        "accent": config["accent"],
        "start": config["start"],
        "end": config["end"],
        "description": config["description"],
        "timelineMode": True,
        "series": series_summary(mapping),
        "archives": [],
        "relatedPaths": config["relatedPaths"],
        "totalRequired": len(issues),
        "issues": issues,
    }


def update_manifest(paths: list[dict[str, Any]]) -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    new_ids = set(PATH_CONFIG)
    manifest["characters"] = [row for row in manifest["characters"] if row["id"] not in new_ids]
    for payload in paths:
        config = PATH_CONFIG[payload["id"]]
        first_issue = payload["issues"][0]
        manifest["characters"].append({
            "id": payload["id"],
            "name": payload["name"],
            "subtitle": payload["subtitle"],
            "type": config["type"],
            "universe": config["universe"],
            "primaryHub": "what-if",
            "hubs": ["what-if"],
            "accent": payload["accent"],
            "logo": first_issue["cover"],
            "data": f"data/characters/{payload['id']}.json",
            "start": payload["start"],
            "end": payload["end"],
            "totalRequired": payload["totalRequired"],
            "relatedPaths": payload["relatedPaths"],
        })
    manifest["version"] = max(int(manifest.get("version", 0)), 32)
    dump(path, manifest, compact=True)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = max(int(payload.get("version", 0)), 4)
    payload["hubs"] = [hub for hub in payload["hubs"] if hub["id"] != "what-if"]
    alternate = next(hub for hub in payload["hubs"] if hub["id"] == "alternate")
    alternate.pop("status", None)
    alternate["subtitle"] = "Marvel 2099, Marvel Zombies, What If...? e le grandi realtà parallele"
    realities = next((section for section in alternate.setdefault("sections", []) if section["id"] == "realities"), None)
    if realities is None:
        realities = {"id": "realities", "label": "Realtà alternative", "items": []}
        alternate["sections"].append(realities)
    for hub_id in ("marvel-2099", "marvel-zombies", "what-if"):
        if hub_id not in realities["items"]:
            realities["items"].append(hub_id)

    child = {
        "id": "what-if",
        "name": "What If...?",
        "subtitle": "Storie classiche e moderne, separate per realtà e raccolta italiana",
        "type": "universe",
        "accent": "#45b8e8",
        "parent": "alternate",
        "groups": [
            {"id": "master", "label": "Segui tutto il portale", "paths": ["what-if"]},
            {"id": "classic", "label": "Le realtà classiche", "paths": [
                "what-if-classic", "avengers-1950s-what-if", "what-if-kree-skrull-war",
            ]},
            {"id": "heroes", "label": "Eroi reimmaginati", "paths": [
                "what-if-miles-morales", "what-if-venom",
            ]},
            {"id": "dark", "label": "Multiverso Oscuro", "paths": ["what-if-dark"]},
        ],
        "featuredPath": "what-if",
    }
    insert_at = next(
        (index + 1 for index, hub in enumerate(payload["hubs"]) if hub["id"] == "marvel-zombies"),
        payload["hubs"].index(alternate) + 1,
    )
    payload["hubs"].insert(insert_at, child)
    dump(path, payload, compact=True)


CHARACTER_PROFILES: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("what-if-miles-morales", {
        "realName": "Miles Morales · varianti multiversali",
        "aliases": ["Capitan America", "Wolverine", "Hulk", "Thor", "Spider-Man"],
        "universe": "Cinque realtà del Multiverso What If",
        "debut": "What If...? Miles Morales #1 (2022)",
        "creators": "Cody Ziglar, Paco Medina e i team creativi della miniserie del 2022",
        "affiliations": ["Avengers multiversali", "S.H.I.E.L.D. alternativo", "X-Men alternativi", "Asgard alternativo"],
        "abilities": [
            "Poteri variabili secondo la realtà", "Addestramento da supersoldato",
            "Fattore rigenerante e artigli", "Forza gamma", "Poteri asgardiani e Mjolnir",
        ],
        "bio": "Questa incarnazione editoriale di Miles Morales non è un singolo personaggio continuo, ma una costellazione di cinque possibilità. Ogni capitolo conserva il nucleo morale di Miles e cambia l'incontro che definisce la sua vita: il siero del supersoldato, il programma Weapon X, l'energia gamma, il potere di Thor o il morso del ragno. Le differenze mostrano quanto identità, famiglia e responsabilità contino più del costume. Nel finale le varianti entrano in contatto e trasformano l'antologia in una piccola squadra multiversale, distinta sia dal Miles dell'Universo Ultimate sia da quello trasferito su Terra-616.",
    }),
    ("what-if-venom", {
        "realName": "Simbionte Venom · varianti multiversali",
        "aliases": ["Il Simbionte Supremo", "She-Venom", "Venom-Wolverine", "Venom-Strange", "Venom-Moon Knight"],
        "universe": "Cinque realtà del Multiverso What If",
        "debut": "What If...? Venom #1 (2024)",
        "creators": "Jeremy Holt e i team artistici della miniserie What If...? Venom",
        "affiliations": ["She-Hulk", "Wolverine", "Doctor Strange", "Loki", "Moon Knight"],
        "abilities": [
            "Legame simbiotico", "Amplificazione dei poteri dell'ospite", "Mutaforma e mimetizzazione",
            "Memoria genetica", "Adattamento fisico e mistico",
        ],
        "bio": "Il Venom di questo percorso è il simbionte osservato attraverso cinque legami alternativi. Invece di definire la propria identità insieme a Eddie Brock, incontra She-Hulk, Wolverine, Doctor Strange, Loki e Moon Knight e assorbe ogni volta capacità, traumi e conflitti molto diversi. La miniserie usa così Venom come reagente narrativo: forza gamma, rigenerazione mutante, magia e identità frammentate cambiano anche il comportamento del Klyntar. I capitoli appartengono a possibilità separate e non sostituiscono la storia del simbionte di Terra-616; il profilo riassume ciò che rimane costante quando cambia l'ospite.",
    }),
])


EDITORIAL_PROFILES: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("avengers-1950s-what-if", {
        "type": "team",
        "founded": "Anni Cinquanta nella storia · 1978 editorialmente",
        "universe": "Realtà alternativa del What If classico",
        "debut": "What If? vol. 1 #9 (1978)",
        "creators": "Roy Thomas, Don Glut, Alan Kupperberg e Bill Black",
        "founders": ["Jimmy Woo", "3-D Man", "Gorilla-Man", "Human Robot", "Marvel Boy", "Venus"],
        "members": ["Jimmy Woo", "3-D Man", "Gorilla-Man", "Human Robot", "Marvel Boy", "Venus"],
        "bases": ["Strutture federali statunitensi", "Teatri operativi dell'era atomica"],
        "traits": ["Supergruppo pre-Avengers", "Eroi pulp e fantascientifici", "Missioni coordinate dall'FBI", "Prototipo degli Agents of Atlas"],
        "bio": "What If? #9 immagina che Jimmy Woo riunisca negli anni Cinquanta alcuni eroi dell'epoca Atlas per affrontare minacce che nessun agente potrebbe gestire da solo. 3-D Man, Gorilla-Man, Human Robot, Marvel Boy e Venus diventano così Avengers prima che il nome appartenga alla squadra di Thor, Iron Man, Hulk, Ant-Man e Wasp. Il racconto nacque come deviazione dalla storia nota e valorizza il patrimonio pulp, horror e fantascientifico della Marvel precedente al 1961. Idee e personaggi saranno poi rielaborati dagli Agents of Atlas nella continuità principale, ma questo percorso conserva il team esattamente nella cornice alternativa del capitolo originale.",
    }),
    ("what-if-kree-skrull-war", {
        "type": "event",
        "period": "1980 editorialmente · deviazione dalla Guerra Kree-Skrull",
        "universe": "Realtà alternativa del What If classico",
        "debut": "What If? vol. 1 #20 (1980)",
        "creators": "Tom DeFalco, Alan Kupperberg e Bruce Patterson",
        "trigger": "Rick Jones non interviene nel momento decisivo della Guerra Kree-Skrull",
        "scope": "Un capitolo autoconclusivo raccolto in What If? Classic 3",
        "factions": ["Avengers", "Impero Kree", "Impero Skrull", "Suprema Intelligenza"],
        "consequences": ["Esito alternativo del conflitto cosmico", "Nuove pressioni sugli Avengers", "Separazione netta dalla cronologia di Terra-616"],
        "bio": "La Guerra Kree-Skrull originale mette la Terra al centro dello scontro fra due imperi e assegna a Rick Jones un ruolo decisivo nel finale. What If? #20 rimuove proprio quella variabile e segue la reazione degli Avengers quando il conflitto non può essere risolto nello stesso modo. L'evento alternativo non è un seguito né una riscrittura retroattiva della saga di Terra-616: è un esperimento autoconclusivo sulle conseguenze di un'assenza. Il percorso seleziona soltanto questo capitolo dal terzo volume Classic, permettendo di possedere una sola copia fisica pur ritrovandola sia nell'antologia completa sia nella scheda dell'evento.",
    }),
])


def update_profiles() -> None:
    character_path = DATA / "character-profiles.json"
    characters = json.loads(character_path.read_text(encoding="utf-8"))
    profiles = characters.setdefault("profiles", {})
    for profile_id in CHARACTER_PROFILES:
        profiles.pop(profile_id, None)
    profiles.update(CHARACTER_PROFILES)
    characters["version"] = max(int(characters.get("version", 0)), 4)
    dump(character_path, characters)

    editorial_path = DATA / "editorial-profiles.json"
    editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
    profiles = editorial.setdefault("profiles", {})
    for profile_id in EDITORIAL_PROFILES:
        profiles.pop(profile_id, None)
    profiles.update(EDITORIAL_PROFILES)
    editorial["version"] = max(int(editorial.get("version", 0)), 3)
    dump(editorial_path, editorial)


def write_audit(paths: list[dict[str, Any]]) -> None:
    audit = {
        "version": 1,
        "scope": "What If...? nelle raccolte italiane Panini selezionate, con ogni realtà trattata come possibilità autonoma",
        "publishedThrough": "Ottobre 2024",
        "physicalIssues": len(PHYSICAL),
        "usaStories": sum(len(contents) for contents in MASTER_CONTENTS.values()),
        "paths": {payload["id"]: payload["totalRequired"] for payload in paths},
        "sharedPhysicalIssues": {
            "MARVGEEKS:33": ["what-if", "what-if-classic", "avengers-1950s-what-if"],
            "MARVGEEKS:35": ["what-if", "what-if-classic", "what-if-kree-skrull-war"],
            "MVNWCOL_P:436": ["what-if", "what-if-miles-morales"],
            "MVNWCOL_P:567": ["what-if", "what-if-dark"],
            "MVNWCOL_P:603": ["what-if", "what-if-venom"],
        },
        "scopingNotes": [
            "I tre Classic contengono i numeri USA #1–12, #14–15 e #17–20; i numeri assenti non vengono inventati come lacune fisiche.",
            "Miles Morales, What If...? Dark e What If...? Venom appartengono a raccolte autonome e non a una singola continuità condivisa.",
            "Ogni percorso figlio riusa l'ID del volume fisico e limita la lettura ai contenuti USA indicati.",
        ],
        "imageRequests": {
            "universe": {"what-if": "what-if.jpg"},
            "collections": {
                "what-if-classic": "what-if-classic.jpg",
                "what-if-dark": "what-if-dark.jpg",
            },
            "characters": {
                "what-if-miles-morales": "what-if-miles-morales.jpg",
                "what-if-venom": "what-if-venom.jpg",
            },
            "teams": {"avengers-1950s-what-if": "avengers-1950s-what-if.jpg"},
            "events": {"what-if-kree-skrull-war": "what-if-kree-skrull-war.jpg"},
        },
        "sources": [
            "https://www.comicsbox.it/albo/MARVGEEKS_017",
            "https://www.panini.it/shp_ita_it/what-if-classic-1-mgeek017isbn-it08.html",
            "https://www.comicsbox.it/albo/MARVGEEKS_033",
            "https://www.panini.it/shp_ita_it/what-if-classic-2-mgeek033isbn-it08.html",
            "https://www.comicsbox.it/albo/MARVGEEKS_035",
            "https://www.panini.it/shp_ita_it/what-if-classic-3-mgeek035isbn-it08.html",
            "https://www.comicsbox.it/albo/MVNWCOL_P_436",
            "https://www.panini.it/shp_ita_it/what-if-miles-morales-mnowi213isbn-it08.html",
            "https://www.comicsbox.it/albo/MVNWCOL_P_567",
            "https://www.panini.it/shp_ita_it/what-if-dark-multiverso-oscuro-mnowi286isbn-it08.html",
            "https://www.comicsbox.it/albo/MVNWCOL_P_603",
            "https://www.panini.it/shp_ita_it/what-if-venom-il-simbionte-supremo-mnowi320isbn-it08.html",
            "https://www.marvel.com/comics/series/34253/what_if_miles_morales_2022",
            "https://www.marvel.com/comics/series/38826/what_if_venom_2024",
            "https://www.marvel.com/articles/comics/what-if-dark-puts-a-dark-twist-on-classic-moments",
        ],
    }
    dump(DATA / "what-if-audit.json", audit)


def main() -> None:
    paths = [build_path(path_id) for path_id in PATH_CONFIG]
    for payload in paths:
        dump(CHARACTERS / f"{payload['id']}.json", payload)
    update_manifest(paths)
    update_hubs()
    update_profiles()
    write_audit(paths)
    print("What If...?:", ", ".join(f"{row['id']}={row['totalRequired']}" for row in paths))


if __name__ == "__main__":
    main()
