#!/usr/bin/env python3
"""Build the Marvel Zombies alternate-realities hub from Italian editions.

The master route uses the two Panini Zomnibus volumes and the later Italian
collections. Child routes reuse the same physical IDs while exposing only the
US chapters that belong to a character, team or event continuity.
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
    "MAROMNIB", 188, "Marvel Omnibus", "Marvel Zombies: Marvel Zomnibus",
    "Settembre 2023", "MAROMNIB_188",
))
register(physical(
    "MAROMNIB", 235, "Marvel Omnibus", "Marvel Zombies: Marvel Zomnibus - Il Ritorno",
    "Settembre 2025", "MAROMNIB_235",
))
register(physical(
    "MARVGIANTS", 17, "Marvel Giants", "Marvel Zombies: Black, White and Blood",
    "Giugno 2024", "MARVGIANTS_017",
))
register(physical(
    "MVNWCOL_P", 647, "Marvel Collection (II)", "Marvel Zombies: Alba di Putrefazione",
    "Aprile 2025", "MVNWCOL_P_647",
))
register(physical(
    "MVNWCOL_P", 735, "Marvel Collection (II)", "Marvel Zombies - Red Band: Una storia di morte",
    "Maggio 2026", "MVNWCOL_P_735",
))


CONTENT_NAMES = {
    "MZDEADDAYS": "Marvel Zombies: Dead Days",
    "MZEVILEVOL": "Marvel Zombies: Evil Evolution",
    "ULTF4": "Ultimate Fantastic Four",
    "MZOMBIE1": "Marvel Zombies (2005)",
    "BLACKP4": "Black Panther (2005)",
    "MZOMBIE2": "Marvel Zombies 2",
    "MZRETURN": "Marvel Zombies Return",
    "MZOMBIE3": "Marvel Zombies 3",
    "MZOMBIE4": "Marvel Zombies 4",
    "MZOMBIE5": "Marvel Zombies 5",
    "MZSUPREME": "Marvel Zombies Supreme",
    "DPMWM": "Deadpool: Merc with a Mouth",
    "MZCHRISTMAS": "Zombies Christmas Carol",
    "MZDESTROY": "Marvel Zombies Destroy!",
    "MZHALLOWEEN": "Marvel Zombies Halloween",
    "MZ2015": "Marvel Zombies: Battleworld (2015)",
    "AOUVSMZ": "Age of Ultron vs. Marvel Zombies",
    "MARVELZOMBIE2018": "Marvel Zombie (2018)",
    "MZRES2019": "Marvel Zombies: Resurrection (2019)",
    "MZRES2020": "Marvel Zombies: Resurrection (2020)",
    "MZBWB": "Marvel Zombies: Black, White & Blood",
    "MZDAWN": "Marvel Zombies: Dawn of Decay",
    "MZREDBAND": "Marvel Zombies: Red Band",
}


def content_id(series_id: str, number: int | str) -> str:
    return f"{series_id}:{number}"


def run(series_id: str, numbers: Iterable[int | str]) -> list[str]:
    return [content_id(series_id, number) for number in numbers]


def content(value: str) -> dict[str, str]:
    series_id, number = value.split(":", 1)
    return {"id": value, "series": CONTENT_NAMES[series_id], "number": number}


ZOMNIBUS_CLASSIC = [
    *run("MZDEADDAYS", [1]),
    *run("MZEVILEVOL", [1]),
    *run("ULTF4", [21, 22, 23, 30, 31, 32]),
    *run("MZOMBIE1", range(1, 6)),
    *run("BLACKP4", range(28, 31)),
    *run("MZOMBIE2", range(1, 6)),
    *run("MZRETURN", range(1, 6)),
    *run("MZOMBIE3", range(1, 5)),
    *run("MZOMBIE4", range(1, 5)),
    *run("MZOMBIE5", range(1, 6)),
    *run("MZSUPREME", range(1, 6)),
]

ZOMNIBUS_RETURNS = [
    *run("DPMWM", range(1, 14)),
    *run("MZCHRISTMAS", range(1, 6)),
    *run("MZDESTROY", range(1, 6)),
    *run("MZHALLOWEEN", [1]),
    *run("MZ2015", range(1, 5)),
    *run("AOUVSMZ", range(1, 5)),
    *run("MARVELZOMBIE2018", [1]),
    *run("MZRES2019", [1]),
    *run("MZRES2020", range(1, 5)),
]

MASTER_CONTENTS: OrderedDict[str, list[str]] = OrderedDict([
    ("MAROMNIB:188", ZOMNIBUS_CLASSIC),
    ("MARVGIANTS:17", run("MZBWB", range(1, 5))),
    ("MVNWCOL_P:647", run("MZDAWN", range(1, 5))),
    ("MAROMNIB:235", ZOMNIBUS_RETURNS),
    ("MVNWCOL_P:735", run("MZREDBAND", range(1, 6))),
])

EARTH_2149_CORE = [
    *run("MZDEADDAYS", [1]),
    *run("ULTF4", [21, 22, 23, 30, 31, 32]),
    *run("MZOMBIE1", range(1, 6)),
    *run("BLACKP4", range(28, 31)),
    *run("MZOMBIE2", range(1, 6)),
    *run("MZRETURN", range(1, 6)),
]

ZOMBIE_SPIDER_MAN = [
    *run("ULTF4", [22, 23]),
    *run("MZDEADDAYS", [1]),
    *run("MZOMBIE1", range(1, 6)),
    *run("BLACKP4", range(28, 31)),
    *run("MZOMBIE2", range(1, 6)),
    *run("MZRETURN", [1, 3, 5]),
]


PATH_CONTENTS: dict[str, OrderedDict[str, list[str]]] = {
    "marvel-zombies": MASTER_CONTENTS,
    "zombie-spider-man": OrderedDict([("MAROMNIB:188", ZOMBIE_SPIDER_MAN)]),
    "marvel-zombies-2149": OrderedDict([("MAROMNIB:188", EARTH_2149_CORE)]),
    "marvel-zombies-battleworld": OrderedDict([(
        "MAROMNIB:235",
        [*run("MZ2015", range(1, 5)), *run("AOUVSMZ", range(1, 5))],
    )]),
    "marvel-zombies-resurrection": OrderedDict([(
        "MAROMNIB:235",
        [*run("MZRES2019", [1]), *run("MZRES2020", range(1, 5))],
    )]),
    "marvel-zombies-dawn-of-decay": OrderedDict([(
        "MVNWCOL_P:647", run("MZDAWN", range(1, 5)),
    )]),
    "marvel-zombies-red-band": OrderedDict([(
        "MVNWCOL_P:735", run("MZREDBAND", range(1, 6)),
    )]),
}


PATH_CONFIG: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("marvel-zombies", {
        "name": "Marvel Zombies",
        "subtitle": "Terra-2149 e le altre realtà contagiate",
        "type": "universe",
        "universe": "Multiverso Marvel",
        "accent": "#a7d95b",
        "start": "Marvel Omnibus #188 — Settembre 2023",
        "end": "Marvel Collection (II) #735 — Maggio 2026",
        "description": "Portale completo delle principali realtà Marvel Zombies disponibili in volume italiano. Il primo Zomnibus segue la saga classica di Terra-2149; il secondo raccoglie ritorni, Battleworld e Resurrection. Le tre tappe finali sono antologie o nuove epidemie autonome e non vengono confuse con la continuità originale.",
        "relatedPaths": [
            "marvel-zombies-2149", "zombie-spider-man", "marvel-zombies-battleworld",
            "marvel-zombies-resurrection", "marvel-zombies-dawn-of-decay", "marvel-zombies-red-band",
        ],
    }),
    ("zombie-spider-man", {
        "name": "Spider-Man Zombie",
        "subtitle": "Peter Parker · Terra-2149",
        "type": "character",
        "universe": "Terra-2149",
        "accent": "#e34c67",
        "start": "Marvel Omnibus #188 — Settembre 2023",
        "end": "Marvel Omnibus #188 — Settembre 2023",
        "description": "Il percorso personale di Peter Parker nella saga classica: dalla prima apparizione nell'universo zombie alla lotta contro la Fame e al ciclo Marvel Zombies Return. La singola tappa fisica indica esattamente quali capitoli leggere dentro il grande Zomnibus.",
        "relatedPaths": ["marvel-zombies", "marvel-zombies-2149", "spiderman"],
    }),
    ("marvel-zombies-2149", {
        "name": "Marvel Zombies di Terra-2149",
        "subtitle": "Gli eroi infetti della realtà originale",
        "type": "team",
        "universe": "Terra-2149",
        "accent": "#92c64a",
        "start": "Marvel Omnibus #188 — Settembre 2023",
        "end": "Marvel Omnibus #188 — Settembre 2023",
        "description": "La cronologia essenziale del gruppo originale: l'epidemia, il primo contatto con l'Universo Ultimate, la fame cosmica e il ritorno degli infetti. Sono esclusi Marvel Apes e le miniserie ambientate in realtà zombie successive.",
        "relatedPaths": ["marvel-zombies", "zombie-spider-man", "avengers"],
    }),
    ("marvel-zombies-battleworld", {
        "name": "Marvel Zombies: Battleworld",
        "subtitle": "Deadlands e Perfection · Secret Wars",
        "type": "event",
        "universe": "Battleworld",
        "accent": "#ff8c54",
        "start": "Marvel Omnibus #235 — Settembre 2025",
        "end": "Marvel Omnibus #235 — Settembre 2025",
        "description": "Le due miniserie zombie di Secret Wars 2015: Elsa Bloodstone attraversa le Deadlands mentre gli ultimi umani di Perfection combattono contemporaneamente non-morti e droni di Ultron. Un percorso autonomo rispetto a Terra-2149.",
        "relatedPaths": ["marvel-zombies", "secret-wars-2015"],
    }),
    ("marvel-zombies-resurrection", {
        "name": "Marvel Zombies: Resurrection",
        "subtitle": "Terra-19121 · i Respawned",
        "type": "event",
        "universe": "Terra-19121",
        "accent": "#9d7be8",
        "start": "Marvel Omnibus #235 — Settembre 2025",
        "end": "Marvel Omnibus #235 — Settembre 2025",
        "description": "Prologo 2019 e miniserie 2020 completi: il cadavere di Galactus porta sulla Terra un contagio parassitario diverso dalla Fame di Terra-2149. Spider-Man guida un gruppo di sopravvissuti in una realtà separata.",
        "relatedPaths": ["marvel-zombies", "spiderman", "fantastic-four"],
    }),
    ("marvel-zombies-dawn-of-decay", {
        "name": "Marvel Zombies: Alba di Putrefazione",
        "subtitle": "Terra-66804 · Groot e Hulk",
        "type": "event",
        "universe": "Terra-66804",
        "accent": "#73cf72",
        "start": "Marvel Collection (II) #647 — Aprile 2025",
        "end": "Marvel Collection (II) #647 — Aprile 2025",
        "description": "Miniserie completa in quattro capitoli. Un virus vegetale parte da Groot e trasforma gli eroi in creature fungine; Hulk e il giovane Groot diventano il centro di una storia autonoma, più avventurosa ma distinta da tutte le precedenti realtà zombie.",
        "relatedPaths": ["marvel-zombies", "hulk", "guardians-of-the-galaxy"],
    }),
    ("marvel-zombies-red-band", {
        "name": "Marvel Zombies: Red Band",
        "subtitle": "Una nuova storia della morte",
        "type": "event",
        "universe": "Realtà Red Band",
        "accent": "#f23f43",
        "start": "Marvel Collection (II) #735 — Maggio 2026",
        "end": "Marvel Collection (II) #735 — Maggio 2026",
        "description": "La miniserie 2025 completa riscrive l'inizio dell'era Marvel: il volo cosmico dei Fantastici Quattro genera subito il contagio e l'epidemia attraversa versioni deformate dei grandi momenti editoriali. È una continuità autonoma, non un seguito di Terra-2149.",
        "relatedPaths": ["marvel-zombies", "fantastic-four", "secret-wars-1984"],
    }),
])


INSTRUCTIONS = {
    ("marvel-zombies", "MAROMNIB:188"): "Leggi la saga classica di Terra-2149. I materiali Marvel Apes presenti nel volume sono extra e non fanno parte di questa tappa.",
    ("marvel-zombies", "MAROMNIB:235"): "Leggi le storie zombie raccolte nel secondo Zomnibus; i percorsi collegati separano Battleworld e Resurrection.",
    ("marvel-zombies", "MARVGIANTS:17"): "Antologia autonoma: dodici racconti brevi in bianco, nero e rosso, raccolti dai quattro numeri USA.",
    ("marvel-zombies", "MVNWCOL_P:647"): "Leggi Marvel Zombies: Dawn of Decay #1–4, realtà autonoma con Groot e Hulk.",
    ("marvel-zombies", "MVNWCOL_P:735"): "Leggi Marvel Zombies: Red Band #1–5, nuova cronologia completa.",
    ("zombie-spider-man", "MAROMNIB:188"): "Segui soltanto i capitoli mappati dell'arco di Peter Parker zombie, dall'esordio a Marvel Zombies Return.",
    ("marvel-zombies-2149", "MAROMNIB:188"): "Segui il nucleo di Terra-2149: origini, saga principale, Black Panther, Marvel Zombies 2 e Return.",
    ("marvel-zombies-battleworld", "MAROMNIB:235"): "Leggi Marvel Zombies: Battleworld #1–4 e Age of Ultron vs. Marvel Zombies #1–4.",
    ("marvel-zombies-resurrection", "MAROMNIB:235"): "Leggi il prologo del 2019 e Marvel Zombies: Resurrection (2020) #1–4.",
    ("marvel-zombies-dawn-of-decay", "MVNWCOL_P:647"): "Leggi Marvel Zombies: Dawn of Decay #1–4.",
    ("marvel-zombies-red-band", "MVNWCOL_P:735"): "Leggi Marvel Zombies: Red Band #1–5.",
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
    row["era"] = {
        "MAROMNIB:188": "Terra-2149 · saga classica",
        "MAROMNIB:235": "Ritorni e realtà successive",
        "MARVGIANTS:17": "Incubi antologici",
        "MVNWCOL_P:647": "Alba di Putrefazione",
        "MVNWCOL_P:735": "Red Band",
    }[issue_id]
    row["instruction"] = INSTRUCTIONS[(path_id, issue_id)]
    row["contents"] = [content(value) for value in content_ids]
    row["contentsStatus"] = "path-scoped"
    row["readingStep"] = {"position": seq, "contentIds": content_ids}
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
            "primaryHub": "marvel-zombies",
            "hubs": ["marvel-zombies"],
            "accent": payload["accent"],
            "logo": first_issue["cover"],
            "data": f"data/characters/{payload['id']}.json",
            "start": payload["start"],
            "end": payload["end"],
            "totalRequired": payload["totalRequired"],
            "relatedPaths": payload["relatedPaths"],
        })
    manifest["version"] = max(int(manifest.get("version", 0)), 31)
    dump(path, manifest, compact=True)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = max(int(payload.get("version", 0)), 3)
    payload["hubs"] = [hub for hub in payload["hubs"] if hub["id"] != "marvel-zombies"]
    alternate = next(hub for hub in payload["hubs"] if hub["id"] == "alternate")
    alternate.pop("status", None)
    alternate["subtitle"] = "Marvel 2099, Marvel Zombies e le grandi realtà parallele"
    realities = next((section for section in alternate.setdefault("sections", []) if section["id"] == "realities"), None)
    if realities is None:
        realities = {"id": "realities", "label": "Realtà alternative", "items": []}
        alternate["sections"].append(realities)
    if "marvel-2099" not in realities["items"]:
        realities["items"].append("marvel-2099")
    if "marvel-zombies" not in realities["items"]:
        realities["items"].append("marvel-zombies")

    child = {
        "id": "marvel-zombies",
        "name": "Marvel Zombies",
        "subtitle": "Terra-2149 e le altre realtà contagiate, separate per continuità",
        "type": "universe",
        "accent": "#a7d95b",
        "parent": "alternate",
        "groups": [
            {"id": "master", "label": "Segui tutte le realtà", "paths": ["marvel-zombies"]},
            {"id": "earth-2149", "label": "La realtà originale", "paths": ["marvel-zombies-2149", "zombie-spider-man"]},
            {"id": "battleworld", "label": "Secret Wars · Battleworld", "paths": ["marvel-zombies-battleworld"]},
            {"id": "new-outbreaks", "label": "Nuove epidemie", "paths": [
                "marvel-zombies-resurrection", "marvel-zombies-dawn-of-decay", "marvel-zombies-red-band",
            ]},
        ],
        "featuredPath": "marvel-zombies",
    }
    insert_at = next(
        (index + 1 for index, hub in enumerate(payload["hubs"]) if hub["id"] == "marvel-2099"),
        payload["hubs"].index(alternate) + 1,
    )
    payload["hubs"].insert(insert_at, child)
    dump(path, payload, compact=True)


CHARACTER_PROFILE = {
    "realName": "Peter Parker",
    "aliases": ["Spider-Man Zombie", "Il Ragno zombie", "Peter di Terra-2149"],
    "universe": "Terra-2149",
    "debut": "Ultimate Fantastic Four #22 (2005)",
    "creators": "Mark Millar e Greg Land, dalla creazione di Stan Lee e Steve Ditko",
    "affiliations": ["Marvel Zombies", "Galacti", "Sopravvissuti di Terra-91126"],
    "abilities": [
        "Poteri proporzionali di un ragno", "Senso di ragno", "Aderenza alle superfici",
        "Resistenza da non-morto e Fame sovrumana",
    ],
    "bio": "Il Peter Parker di Terra-2149 conserva memoria, intelligenza e poteri dopo il contagio, ma la Fame trasforma ogni impulso eroico in una minaccia. La tragedia del personaggio nasce dalla sua piena consapevolezza: a differenza di molti infetti, Spider-Man comprende il peso delle persone che ha divorato e non riesce a nascondersi dietro l'istinto. Attraversa così la conquista cosmica dei Marvel Zombies e il successivo passaggio in un'altra realtà cercando un modo per spezzare il ciclo. Il suo percorso deforma il principio della responsabilità senza cancellarlo: Peter rimane insieme colpevole, vittima e uno dei pochi zombie disposti a opporsi alla propria natura.",
}


EDITORIAL_PROFILES: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("marvel-zombies-2149", {
        "type": "team",
        "founded": "2005 (prima apparizione editoriale)",
        "universe": "Terra-2149",
        "debut": "Ultimate Fantastic Four #21–23 (2005)",
        "creators": "Mark Millar e Greg Land; sviluppati da Robert Kirkman e Sean Phillips",
        "founders": ["Fantastici Quattro zombie", "Avengers infetti", "Spider-Man zombie", "Hulk zombie"],
        "members": ["Giant-Man", "Wasp", "Iron Man", "Wolverine", "Luke Cage", "Scarlet Witch"],
        "bases": ["New York devastata di Terra-2149", "Asteroide M", "Spazio profondo"],
        "traits": ["Fame contagiosa", "Memorie e poteri originali", "Espansione cosmica", "Identità morale residua"],
        "bio": "I Marvel Zombies di Terra-2149 sono versioni degli eroi classici infettate da una piaga che conserva poteri, memoria e capacità di ragionare, ma impone una fame quasi irresistibile. Dopo aver distrutto la popolazione terrestre, gli infetti trasformano la loro stessa cooperazione eroica in una macchina di predazione e portano il contagio oltre il pianeta. Il gruppo non è una squadra stabile nel senso tradizionale: alleanze e rivalità cambiano secondo la disponibilità di cibo e i frammenti di coscienza che ciascuno riesce a conservare. Proprio questa tensione distingue la realtà originale dalle successive reinterpretazioni Marvel Zombies.",
    }),
    ("marvel-zombies-battleworld", {
        "type": "event",
        "period": "2015–2016 in Italia",
        "universe": "Battleworld · Deadlands e Perfection",
        "debut": "Marvel Zombies (2015) #1 e Age of Ultron vs. Marvel Zombies #1",
        "creators": "Si Spurrier e Kev Walker; James Robinson e Steve Pugh",
        "trigger": "Il collasso del Multiverso crea Battleworld e confina zombie e droni di Ultron oltre lo Scudo",
        "scope": "Due miniserie collegate a Secret Wars, complete in otto capitoli",
        "factions": ["Elsa Bloodstone e S.H.I.E.L.D.", "Orde delle Deadlands", "Droni di Ultron", "Resistenza di Perfection"],
        "consequences": ["Esplorazione delle Deadlands", "Guerra fra zombie e Ultron", "Collegamento diretto a Secret Wars 2015"],
        "bio": "Su Battleworld le Deadlands sono il dominio in cui vengono respinti i non-morti, separate dagli altri territori da un enorme Scudo. Elsa Bloodstone, in servizio lungo il confine, attraversa questa zona proibita mentre un secondo fronte mostra la guerra interminabile fra le orde zombie e la coscienza collettiva di Ultron nel dominio di Perfection. Le due miniserie condividono il contesto di Secret Wars ma raccontano missioni autonome. Il percorso le riunisce perché descrivono lo stesso sistema di contenimento costruito da Doom, senza presentarle come seguito della saga di Terra-2149.",
    }),
    ("marvel-zombies-resurrection", {
        "type": "event",
        "period": "2019–2021 in Italia",
        "universe": "Terra-19121",
        "debut": "Marvel Zombies: Resurrection #1 (2019)",
        "creators": "Phillip Kennedy Johnson e Leonard Kirk",
        "trigger": "Il cadavere di Galactus raggiunge il Sistema Solare trasportando un parassita cosmico",
        "scope": "Prologo e miniserie completa in cinque capitoli",
        "factions": ["Spider-Man e i sopravvissuti", "Fantastici Quattro", "Avengers e X-Men", "Respawned"],
        "consequences": ["Nascita dei Respawned", "Caduta dei principali gruppi eroici", "Nuova continuità zombie indipendente"],
        "bio": "Resurrection riparte da zero in Terra-19121. Quando il corpo di Galactus appare ai margini del Sistema Solare, Avengers, X-Men e Fantastici Quattro partono per indagare e incontrano un organismo capace di assorbire e riprodurre le persone infette. Anni dopo, Spider-Man protegge un gruppo fragile di superstiti e tenta di capire come fermare i Respawned. La serie sostituisce la Fame cosciente di Terra-2149 con un orrore parassitario e collettivo, costruendo una storia di sopravvivenza familiare che può essere letta senza conoscere i cicli precedenti.",
    }),
    ("marvel-zombies-dawn-of-decay", {
        "type": "event",
        "period": "2024–2025",
        "universe": "Terra-66804",
        "debut": "Marvel Zombies: Dawn of Decay #1 (2024)",
        "creators": "Thomas Krajewski e Jason Muhr",
        "trigger": "Un Groot malato diffonde accidentalmente un contagio vegetale con uno starnuto",
        "scope": "Miniserie autonoma completa in quattro capitoli",
        "factions": ["Groot", "Hulk", "Avengers infetti", "Superstiti di New York"],
        "consequences": ["Epidemia fungina su Terra-66804", "Alleanza fra Hulk e Groot", "Reinterpretazione accessibile del tema Marvel Zombies"],
        "bio": "Alba di Putrefazione immagina un contagio diverso da quello classico: Groot, ammalato, trasmette una piaga vegetale che attecchisce sugli eroi e si propaga rapidamente a New York. Hulk diventa il protettore riluttante del piccolo responsabile dell'epidemia e insieme i due cercano una cura mentre gli Avengers vengono trasformati in creature fungine. Il tono alterna horror, azione e commedia senza collegarsi a Terra-2149. La designazione Terra-66804 e il volume italiano unico rendono questa miniserie una diramazione netta e facilmente isolabile nella mappa.",
    }),
    ("marvel-zombies-red-band", {
        "type": "event",
        "period": "2025–2026",
        "universe": "Realtà Red Band",
        "debut": "Marvel Zombies: Red Band #1 (2025)",
        "creators": "Ethan S. Parker, Griffin Sheridan e Jan Bazaldua",
        "trigger": "I raggi cosmici trasformano il primo volo dei Fantastici Quattro nell'origine dell'epidemia",
        "scope": "Storia alternativa dell'Universo Marvel completa in cinque capitoli",
        "factions": ["Frightful Four infetti", "Primi Avengers", "X-Men", "Spider-Man e Jewel"],
        "consequences": ["Origini Marvel riscritte", "Eventi classici deformati dal contagio", "Continuità zombie autonoma"],
        "bio": "Red Band sposta l'apocalisse all'alba dell'Universo Marvel. Reed Richards, Sue Storm, Ben Grimm e Johnny Storm tornano dal loro volo con poteri straordinari e una fame incontrollabile, facendo del primo grande evento eroico l'inizio del disastro. La miniserie procede poi attraverso versioni accelerate e sanguinose di tappe storiche come la nascita degli Avengers, gli X-Men e le Guerre Segrete. Non continua nessuna precedente realtà zombie: usa l'intera storia editoriale Marvel come materia per una nuova cronologia compatta, pubblicata in Italia in un singolo volume Red Band.",
    }),
])


def update_profiles() -> None:
    character_path = DATA / "character-profiles.json"
    characters = json.loads(character_path.read_text(encoding="utf-8"))
    characters.setdefault("profiles", {}).pop("zombie-spider-man", None)
    characters["profiles"]["zombie-spider-man"] = CHARACTER_PROFILE
    characters["version"] = max(int(characters.get("version", 0)), 3)
    dump(character_path, characters)

    editorial_path = DATA / "editorial-profiles.json"
    editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
    for profile_id in EDITORIAL_PROFILES:
        editorial.setdefault("profiles", {}).pop(profile_id, None)
    editorial["profiles"].update(EDITORIAL_PROFILES)
    editorial["version"] = max(int(editorial.get("version", 0)), 2)
    dump(editorial_path, editorial)


def write_audit(paths: list[dict[str, Any]]) -> None:
    audit = {
        "version": 1,
        "scope": "Marvel Zombies nelle edizioni italiane Panini, separato per realtà narrativa",
        "publishedThrough": "Maggio 2026",
        "physicalIssues": len(PHYSICAL),
        "paths": {payload["id"]: payload["totalRequired"] for payload in paths},
        "continuities": {
            "marvel-zombies-2149": "Terra-2149 e il ciclo Return su Terra-91126",
            "marvel-zombies-battleworld": "Battleworld · Deadlands e Perfection",
            "marvel-zombies-resurrection": "Terra-19121",
            "marvel-zombies-dawn-of-decay": "Terra-66804",
            "marvel-zombies-red-band": "Realtà autonoma senza designazione ufficiale usata nel percorso",
        },
        "sharedPhysicalIssues": {
            "MAROMNIB:188": ["marvel-zombies", "zombie-spider-man", "marvel-zombies-2149"],
            "MAROMNIB:235": ["marvel-zombies", "marvel-zombies-battleworld", "marvel-zombies-resurrection"],
        },
        "scopingNotes": [
            "I materiali Marvel Apes del primo Zomnibus non sono inclusi nei contenuti del percorso.",
            "Black, White & Blood resta una tappa antologica del master e non viene presentato come singolo evento.",
            "Ogni percorso figlio riusa l'ID del volume fisico e limita la lettura ai contenuti USA indicati.",
        ],
        "imageRequests": {
            "universe": {"marvel-zombies": "marvel-zombies.jpg"},
            "characters": {"zombie-spider-man": "zombie-spider-man.jpg"},
            "teams": {"marvel-zombies-2149": "marvel-zombies-2149.jpg"},
            "events": {
                "marvel-zombies-battleworld": "marvel-zombies-battleworld.jpg",
                "marvel-zombies-resurrection": "marvel-zombies-resurrection.jpg",
                "marvel-zombies-dawn-of-decay": "marvel-zombies-dawn-of-decay.jpg",
                "marvel-zombies-red-band": "marvel-zombies-red-band.jpg",
            },
        },
        "sources": [
            "https://www.comicsbox.it/albo/MAROMNIB_188",
            "https://www.panini.it/shp_ita_it/marvel-zomnibus-momni032isbn-it08.html",
            "https://www.comicsbox.it/albo/MAROMNIB_235",
            "https://www.panini.it/shp_ita_it/marvel-zomnibus-il-ritorno-momni077isbn-it08.html",
            "https://www.comicsbox.it/albo/MARVGIANTS_017",
            "https://www.comicsbox.it/albo/MVNWCOL_P_647",
            "https://www.comicsbox.it/albo/MVNWCOL_P_735",
            "https://www.marvel.com/teams-and-groups/marvel-zombies-earth-2149",
            "https://www.marvel.com/comics/series/20318/marvel_zombies_battleworld_2015",
            "https://www.marvel.com/comics/series/28311/marvel_zombies_resurrection_2019",
        ],
    }
    dump(DATA / "marvel-zombies-audit.json", audit)


def main() -> None:
    paths = [build_path(path_id) for path_id in PATH_CONFIG]
    for payload in paths:
        dump(CHARACTERS / f"{payload['id']}.json", payload)
    update_manifest(paths)
    update_hubs()
    update_profiles()
    write_audit(paths)
    print("Marvel Zombies:", ", ".join(f"{row['id']}={row['totalRequired']}" for row in paths))


if __name__ == "__main__":
    main()
