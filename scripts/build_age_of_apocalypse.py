#!/usr/bin/env python3
"""Build the Earth-295 / Age of Apocalypse family from Italian editions.

The seven Panini ``L'era di Apocalisse Collection`` books are the physical
source of truth. Child paths reuse those IDs and select only the US chapters
for a team, character or event, so collection ownership is never duplicated.
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
    text = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    path.write_text(text, encoding="utf-8")


def physical(number: int, title: str, date: str) -> dict[str, Any]:
    code = f"ERAPOCOL_P_{number:03d}"
    return {
        "id": f"ERAPOCOL_P:{number}",
        "n": number,
        "name": f"L'era di Apocalisse Collection #{number}",
        "title": title,
        "date": date,
        "seriesId": "ERAPOCOL_P",
        "series": "L'era di Apocalisse Collection",
        "publisher": "Panini Comics",
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
        "dateQuality": "ComicsBox",
    }


PHYSICAL: OrderedDict[str, dict[str, Any]] = OrderedDict(
    (row["id"], row)
    for row in (
        physical(1, "Il sogno muore", "Gennaio 2014"),
        physical(2, "Agnelli sacrificali", "Marzo 2014"),
        physical(3, "Fuoco nel cielo", "Maggio 2014"),
        physical(4, "Ferite aperte", "Luglio 2014"),
        physical(5, "L'arte della guerra", "Settembre 2014"),
        physical(6, "Su terra consacrata", "Novembre 2014"),
        physical(7, "Ritorno all'Era di Apocalisse", "Gennaio 2015"),
    )
)


CONTENT_SERIES = {
    "XM1": "Uncanny X-Men vol. 1",
    "XM2": "X-Men vol. 2",
    "CAB2": "Cable vol. 1",
    "XM_ALPH": "X-Men: Alpha",
    "XM_ASTO": "Astonishing X-Men",
    "XM_AMAZ": "Amazing X-Men",
    "GAMXTE": "Gambit and the X-Ternals",
    "GENEXT": "Generation Next",
    "WEAPX1": "Weapon X",
    "XCALIBR": "X-Calibre",
    "FACTX": "Factor X",
    "XMAN": "X-Man",
    "XUNIVER": "X-Universe",
    "XM_CHRO": "X-Men Chronicles",
    "XM_OMEG": "X-Men: Omega",
    "XM_AGAPO": "X-Men: Age of Apocalypse One Shot",
    "XM_AGAP": "X-Men: Age of Apocalypse",
}


def run(series_id: str, numbers: Iterable[int]) -> list[str]:
    return [f"{series_id}_{number:03d}" for number in numbers]


VOLUME_CONTENTS: OrderedDict[str, list[str]] = OrderedDict([
    ("ERAPOCOL_P:1", [
        "XM1_320", "XM2_040", "CAB2_020", "XM2_041", "XM_ALPH_001", "XM1_321",
    ]),
    ("ERAPOCOL_P:2", [
        "XM_ASTO_001", "XM_AMAZ_001", "GAMXTE_001", "GENEXT_001",
        "WEAPX1_001", "XCALIBR_001", "FACTX_001", "XMAN_001",
    ]),
    ("ERAPOCOL_P:3", [
        "XM_ASTO_002", "XM_AMAZ_002", "GAMXTE_002", "GENEXT_002",
        "WEAPX1_002", "XCALIBR_002", "FACTX_002", "XMAN_002",
    ]),
    ("ERAPOCOL_P:4", [
        "XM_ASTO_003", "XM_AMAZ_003", "GAMXTE_003", "GENEXT_003",
        "WEAPX1_003", "XCALIBR_003", "FACTX_003", "XMAN_003",
    ]),
    ("ERAPOCOL_P:5", [
        "XM_ASTO_004", "XM_AMAZ_004", "GAMXTE_004", "GENEXT_004",
        "WEAPX1_004", "XCALIBR_004", "FACTX_004", "XMAN_004",
    ]),
    ("ERAPOCOL_P:6", [
        "XUNIVER_001", "XUNIVER_002", "XM_CHRO_001", "XM_CHRO_002", "XM_OMEG_001",
    ]),
    ("ERAPOCOL_P:7", ["XM_AGAPO_001", *run("XM_AGAP", range(1, 7))]),
])


def four_part(series_id: str) -> OrderedDict[str, list[str]]:
    return OrderedDict(
        (f"ERAPOCOL_P:{volume}", [f"{series_id}_{chapter:03d}"])
        for volume, chapter in zip(range(2, 6), range(1, 5))
    )


PATH_CONTENTS: dict[str, OrderedDict[str, list[str]]] = {
    "age-of-apocalypse": VOLUME_CONTENTS,
    "age-of-apocalypse-event": OrderedDict(list(VOLUME_CONTENTS.items())[:6]),
    "astonishing-xmen-aoa": four_part("XM_ASTO"),
    "amazing-xmen-aoa": four_part("XM_AMAZ"),
    "gambit-xternals-aoa": four_part("GAMXTE"),
    "generation-next-aoa": four_part("GENEXT"),
    "weapon-x-aoa": four_part("WEAPX1"),
    "x-calibre-aoa": four_part("XCALIBR"),
    "factor-x-aoa": four_part("FACTX"),
    "x-man-aoa": four_part("XMAN"),
    "x-universe-aoa": OrderedDict([("ERAPOCOL_P:6", VOLUME_CONTENTS["ERAPOCOL_P:6"])]),
    "return-age-of-apocalypse": OrderedDict([("ERAPOCOL_P:7", VOLUME_CONTENTS["ERAPOCOL_P:7"])]),
}


PATH_CONFIG: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("age-of-apocalypse", {
        "name": "Era di Apocalisse",
        "subtitle": "Terra-295 · saga originale e ritorno del 2005",
        "type": "universe",
        "universe": "Terra-295",
        "accent": "#e3973f",
        "start": "L'era di Apocalisse Collection #1 — Gennaio 2014",
        "end": "L'era di Apocalisse Collection #7 — Gennaio 2015",
        "description": "Percorso master di Terra-295 costruito sui sette volumi Panini della L'era di Apocalisse Collection. I primi sei raccolgono il passaggio dalla linea temporale originaria al crossover del 1995 e la guerra contro Apocalisse; il settimo riunisce il one-shot celebrativo e la miniserie del 2005. I percorsi collegati riusano gli stessi volumi fisici e isolano una squadra, un protagonista o una fase narrativa.",
        "relatedPaths": [
            "age-of-apocalypse-event", "amazing-xmen-aoa", "astonishing-xmen-aoa",
            "gambit-xternals-aoa", "generation-next-aoa", "weapon-x-aoa",
            "x-calibre-aoa", "factor-x-aoa", "x-man-aoa",
            "x-universe-aoa", "return-age-of-apocalypse",
        ],
    }),
    ("age-of-apocalypse-event", {
        "name": "Era di Apocalisse: saga originale",
        "subtitle": "Il crossover mutante del 1995",
        "type": "event",
        "universe": "Terra-295 e linea temporale originaria",
        "accent": "#e1513d",
        "start": "L'era di Apocalisse Collection #1 — Gennaio 2014",
        "end": "L'era di Apocalisse Collection #6 — Novembre 2014",
        "description": "Il nucleo del crossover del 1995, dal crollo della storia conosciuta a X-Men: Alpha, attraverso gli otto fronti paralleli, fino alle cronache di Terra-295, X-Universe e X-Men: Omega. Il percorso segue l'ordine dei sei volumi italiani selezionati e non include il ritorno celebrativo del 2005.",
        "relatedPaths": ["age-of-apocalypse", "xmen", "return-age-of-apocalypse"],
    }),
    ("astonishing-xmen-aoa", {
        "name": "Astonishing X-Men",
        "subtitle": "Rogue contro Olocausto",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#d85b71",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "I quattro capitoli completi della squadra guidata da Rogue. Sabretooth, Blink, Wild Child, Morph e Sunfire affrontano le fabbriche di Infinites e le selezioni di Olocausto, mentre la resistenza tenta di proteggere i superstiti umani.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "xmen", "rogue"],
    }),
    ("amazing-xmen-aoa", {
        "name": "Amazing X-Men",
        "subtitle": "Quicksilver guida l'evacuazione",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#5da9e9",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "La missione completa degli X-Men guidati da Quicksilver. Storm, Dazzler, Banshee, Iceman ed Exodus devono sostenere l'evacuazione degli umani verso l'Europa e contrastare la Fratellanza del Caos e il Cavaliere Abyss.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "xmen", "quicksilver", "storm"],
    }),
    ("gambit-xternals-aoa", {
        "name": "Gambit e gli X-Ternals",
        "subtitle": "La missione del Cristallo M'Kraan",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#a779d9",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "Gambit conduce Jubilee, Strong Guy, Sunspot e Lila Cheney nello spazio Shi'ar per recuperare un frammento del Cristallo M'Kraan. La missione collega direttamente la resistenza di Magneto al tentativo di Bishop di ripristinare la realtà perduta.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "gambit", "x-force"],
    }),
    ("generation-next-aoa", {
        "name": "Generation Next",
        "subtitle": "La nuova generazione nel Core di Seattle",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#d9a33d",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "Colosso e Shadowcat guidano Chamber, Husk, Mondo, Skin e Vincente nella missione per liberare Illyana Rasputin dal Core di Seattle. I quattro capitoli mostrano il costo più duro della resistenza giovanile contro Sugar Man.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "new-mutants", "xmen"],
    }),
    ("weapon-x-aoa", {
        "name": "Weapon X (Terra-295)",
        "subtitle": "Logan e Jean Grey contro il regime",
        "type": "character",
        "universe": "Terra-295",
        "accent": "#d36c42",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "La miniserie completa di Logan nella realtà dominata da Apocalisse. Weapon X e Jean Grey operano fra Europa e America mentre il piano nucleare del Consiglio Umano mette in conflitto la salvezza dei superstiti e il destino del continente occupato.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "wolverine-616", "jean-grey"],
    }),
    ("x-calibre-aoa", {
        "name": "X-Calibre",
        "subtitle": "Nightcrawler sulla rotta di Avalon",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#6f77d9",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "Nightcrawler attraversa le rotte dei profughi per raggiungere Avalon e trovare Destiny, l'unica mutante capace di verificare il racconto di Bishop. Mystica, Switchback e Damask trasformano la missione in una piccola squadra nata lungo il viaggio.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "xmen", "deadpool"],
    }),
    ("factor-x-aoa", {
        "name": "Factor X",
        "subtitle": "L'élite mutante di Apocalisse",
        "type": "team",
        "universe": "Terra-295",
        "accent": "#6db9a5",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "Il fronte interno del regime visto attraverso Cyclops, Havok e l'Elite Mutant Force. I laboratori di Bestia Nera e i recinti di Sinistro incrinano la fedeltà dei due fratelli e mostrano il sistema di controllo costruito da Apocalisse dall'interno.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "x-factor", "cyclops"],
    }),
    ("x-man-aoa", {
        "name": "X-Man (Nate Grey)",
        "subtitle": "L'arma vivente di Sinistro",
        "type": "character",
        "universe": "Terra-295",
        "accent": "#4ec8d5",
        "start": "L'era di Apocalisse Collection #2 — Marzo 2014",
        "end": "L'era di Apocalisse Collection #5 — Settembre 2014",
        "description": "I primi quattro capitoli di Nate Grey, giovane psionico creato da Sinistro usando il patrimonio genetico di Scott Summers e Jean Grey. Cresciuto fra gli Outcasts di Forge, Nate scopre gradualmente la propria origine e il motivo per cui Apocalisse lo considera una minaccia.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "cyclops", "jean-grey", "cable"],
    }),
    ("x-universe-aoa", {
        "name": "X-Universe e Cronache",
        "subtitle": "Le origini di Terra-295 e l'ultima frontiera",
        "type": "collection",
        "universe": "Terra-295",
        "accent": "#cf8752",
        "start": "L'era di Apocalisse Collection #6 — Novembre 2014",
        "end": "L'era di Apocalisse Collection #6 — Novembre 2014",
        "description": "Un percorso concentrato sul sesto volume: X-Universe segue gli eroi non mutanti sopravvissuti, X-Men Chronicles ricostruisce due momenti anteriori al crossover e X-Men: Omega chiude il conflitto principale. È il complemento corale agli otto titoli paralleli.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "xmen"],
    }),
    ("return-age-of-apocalypse", {
        "name": "Ritorno all'Era di Apocalisse",
        "subtitle": "Il decennale del 2005",
        "type": "event",
        "universe": "Terra-295",
        "accent": "#b94e46",
        "start": "L'era di Apocalisse Collection #7 — Gennaio 2015",
        "end": "L'era di Apocalisse Collection #7 — Gennaio 2015",
        "description": "Il one-shot celebrativo e la miniserie X-Men: Age of Apocalypse #1–6 pubblicati per il decennale. Le storie brevi colmano passaggi precedenti, mentre la miniserie torna su Terra-295 dopo X-Men: Omega e mostra una realtà sopravvissuta ma ancora segnata dal regime.",
        "relatedPaths": ["age-of-apocalypse", "age-of-apocalypse-event", "xmen"],
    }),
])


ERA_BY_ISSUE = {
    "ERAPOCOL_P:1": "Prologo e X-Men: Alpha",
    "ERAPOCOL_P:2": "Fronti di guerra · atto I",
    "ERAPOCOL_P:3": "Fronti di guerra · atto II",
    "ERAPOCOL_P:4": "Fronti di guerra · atto III",
    "ERAPOCOL_P:5": "Fronti di guerra · atto IV",
    "ERAPOCOL_P:6": "Cronache, X-Universe e Omega",
    "ERAPOCOL_P:7": "Ritorno su Terra-295",
}


def content(content_id: str) -> dict[str, Any]:
    series_id, number = content_id.rsplit("_", 1)
    series = CONTENT_SERIES[series_id]
    display_number = int(number)
    return {
        "id": content_id,
        "seriesId": series_id,
        "series": series,
        "number": display_number,
        "title": f"{series} #{display_number}",
        "url": f"https://www.comicsbox.it/albo/{content_id}",
    }


def selected_summary(content_ids: list[str]) -> str:
    rows = [content(value) for value in content_ids]
    if len(rows) == 1:
        return rows[0]["title"]
    labels = [row["title"] for row in rows[:3]]
    suffix = f" e altri {len(rows) - 3} capitoli" if len(rows) > 3 else ""
    return ", ".join(labels) + suffix


def instruction(path_id: str, issue_id: str, content_ids: list[str]) -> str:
    if path_id == "age-of-apocalypse":
        return f"Leggi il volume completo: {selected_summary(content_ids)}."
    if path_id == "age-of-apocalypse-event":
        return f"Prosegui la saga originale con tutto il volume: {selected_summary(content_ids)}."
    if path_id == "x-universe-aoa":
        return "Leggi X-Universe #1–2, X-Men Chronicles #1–2 e X-Men: Omega."
    if path_id == "return-age-of-apocalypse":
        return "Leggi il one-shot celebrativo e X-Men: Age of Apocalypse #1–6."
    return f"In questo volume leggi soltanto {selected_summary(content_ids)}."


def format_range(numbers: list[int]) -> str:
    if len(numbers) == 1:
        return f"#{numbers[0]}"
    if numbers == list(range(numbers[0], numbers[-1] + 1)):
        return f"#{numbers[0]}–{numbers[-1]}"
    return ", ".join(f"#{number}" for number in numbers)


def series_summary(issue_ids: Iterable[str]) -> list[dict[str, str]]:
    numbers = [int(PHYSICAL[issue_id]["n"]) for issue_id in issue_ids]
    years = [PHYSICAL[issue_id]["date"].split()[-1] for issue_id in issue_ids]
    return [{
        "id": "ERAPOCOL_P",
        "name": "L'era di Apocalisse Collection",
        "publisher": "Panini Comics",
        "range": format_range(numbers),
        "years": years[0] if len(set(years)) == 1 else f"{years[0]}–{years[-1]}",
    }]


def make_issue(path_id: str, issue_id: str, seq: int, content_ids: list[str]) -> dict[str, Any]:
    row = deepcopy(PHYSICAL[issue_id])
    row["seq"] = seq
    row["era"] = ERA_BY_ISSUE[issue_id]
    row["instruction"] = instruction(path_id, issue_id, content_ids)
    row["contents"] = [content(value) for value in content_ids]
    row["contentsStatus"] = "complete" if path_id in {
        "age-of-apocalypse", "age-of-apocalypse-event", "x-universe-aoa", "return-age-of-apocalypse",
    } else "path-scoped"
    row["readingStep"] = {
        "pathId": path_id,
        "position": seq,
        "contentIds": content_ids,
        "scope": "selected-contents",
    }
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
        "editorialModel": "physical-issue/usa-contents/reading-step@1",
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
        manifest["characters"].append({
            "id": payload["id"],
            "name": payload["name"],
            "subtitle": payload["subtitle"],
            "type": config["type"],
            "universe": config["universe"],
            "primaryHub": "age-of-apocalypse",
            "hubs": ["age-of-apocalypse"],
            "accent": payload["accent"],
            "logo": payload["issues"][0]["cover"],
            "data": f"data/characters/{payload['id']}.json",
            "start": payload["start"],
            "end": payload["end"],
            "totalRequired": payload["totalRequired"],
            "relatedPaths": payload["relatedPaths"],
        })
    manifest["version"] = max(int(manifest.get("version", 0)), 33)
    dump(path, manifest, compact=True)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = max(int(payload.get("version", 0)), 5)
    payload["hubs"] = [hub for hub in payload["hubs"] if hub["id"] != "age-of-apocalypse"]
    alternate = next(hub for hub in payload["hubs"] if hub["id"] == "alternate")
    alternate.pop("status", None)
    alternate["subtitle"] = "Marvel 2099, Marvel Zombies, What If...?, Era di Apocalisse e le grandi realtà parallele"
    realities = next(section for section in alternate["sections"] if section["id"] == "realities")
    if "age-of-apocalypse" not in realities["items"]:
        realities["items"].append("age-of-apocalypse")

    child = {
        "id": "age-of-apocalypse",
        "name": "Era di Apocalisse",
        "subtitle": "Terra-295: saga originale, fronti paralleli e ritorno del 2005",
        "type": "universe",
        "accent": "#e3973f",
        "parent": "alternate",
        "groups": [
            {"id": "master", "label": "Segui tutta Terra-295", "paths": ["age-of-apocalypse"]},
            {"id": "event", "label": "La saga", "paths": [
                "age-of-apocalypse-event", "x-universe-aoa", "return-age-of-apocalypse",
            ]},
            {"id": "xmen", "label": "Le squadre degli X-Men", "paths": [
                "amazing-xmen-aoa", "astonishing-xmen-aoa", "generation-next-aoa", "x-calibre-aoa",
            ]},
            {"id": "resistance", "label": "Missioni della resistenza", "paths": [
                "weapon-x-aoa", "x-man-aoa", "gambit-xternals-aoa",
            ]},
            {"id": "regime", "label": "Dentro il regime", "paths": ["factor-x-aoa"]},
        ],
        "featuredPath": "age-of-apocalypse",
    }
    insert_at = next(
        (index + 1 for index, hub in enumerate(payload["hubs"]) if hub["id"] == "what-if"),
        payload["hubs"].index(alternate) + 1,
    )
    payload["hubs"].insert(insert_at, child)
    dump(path, payload, compact=True)


CHARACTER_PROFILES: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("weapon-x-aoa", {
        "realName": "James “Logan” Howlett",
        "aliases": ["Weapon X", "Logan", "Wolverine di Terra-295"],
        "universe": "Terra-295",
        "debut": "X-Men: Alpha #1 (1995); Weapon X #1 (1995)",
        "creators": "Versione di Scott Lobdell, Mark Waid e Roger Cruz; serie di Larry Hama e Adam Kubert",
        "affiliations": ["X-Men di Magneto", "Resistenza europea", "Jean Grey", "Consiglio Umano"],
        "abilities": [
            "Fattore rigenerante", "Scheletro e artigli di adamantio", "Sensi sovrumani",
            "Esperienza militare e clandestina", "Resistenza fisica eccezionale",
        ],
        "bio": "Il Logan di Terra-295 conserva l'indole feroce e il fattore rigenerante della sua controparte principale, ma è stato plasmato da una guerra già perduta. Conosciuto come Weapon X e privo di una mano dopo uno scontro con Cyclops, opera al fianco di Jean Grey nelle zone europee controllate dalla resistenza umana. La loro relazione è insieme sentimentale e politica: Logan appoggia il piano estremo del Consiglio Umano, mentre Jean teme il prezzo imposto ai civili e ai mutanti rimasti in America. I quattro capitoli seguono questo conflitto fino alla fase conclusiva della guerra contro Apocalisse, mantenendo separata la sua biografia da Wolverine di Terra-616.",
    }),
    ("x-man-aoa", {
        "realName": "Nathaniel “Nate” Grey",
        "aliases": ["X-Man", "Nate Grey", "Il figlio genetico di Scott e Jean"],
        "universe": "Terra-295",
        "debut": "X-Man #1 (1995)",
        "creators": "Jeph Loeb e Steve Skroce",
        "affiliations": ["Outcasts di Forge", "Sonique", "Toad", "Mastermind", "Resistenza di Terra-295"],
        "abilities": [
            "Telepatia di livello omega", "Telecinesi", "Proiezione e manipolazione psionica",
            "Volo telecinetico", "Percezione delle energie e delle realtà",
        ],
        "bio": "Nate Grey nasce nei laboratori di Mister Sinister dall'unione artificiale del patrimonio genetico di Scott Summers e Jean Grey. Sinistro vuole creare un'arma psionica abbastanza potente da distruggere Apocalisse, ma Nate cresce lontano dal suo controllo insieme agli Outcasts guidati da Forge. È un adolescente dotato di poteri enormi, poca esperienza e un corpo incapace di contenere senza conseguenze tutta la propria energia. Nei primi quattro numeri scopre frammenti della propria origine, affronta i cacciatori del regime e comprende che sia Sinistro sia Apocalisse vedono in lui uno strumento. Questo profilo riguarda Nate di Terra-295 prima del suo successivo passaggio nella continuità principale.",
    }),
])


EDITORIAL_PROFILES: OrderedDict[str, dict[str, Any]] = OrderedDict([
    ("age-of-apocalypse-event", {
        "type": "event",
        "period": "1995 editorialmente",
        "universe": "Terra-295 e linea temporale originaria",
        "debut": "X-Men: Alpha #1 e le testate mutanti Marvel del 1995",
        "creators": "Scott Lobdell, Mark Waid, Fabian Nicieza, Jeph Loeb, Larry Hama, Warren Ellis e i team creativi mutanti",
        "trigger": "Legion viaggia nel passato per uccidere Magneto ma colpisce Charles Xavier, cancellando la storia conosciuta",
        "scope": "Sei volumi italiani, otto miniserie parallele, prologo, cronache e finale",
        "factions": ["X-Men di Magneto", "Impero di Apocalisse", "Consiglio Umano", "Bishop", "Sinistro e i suoi agenti"],
        "consequences": ["Nascita di Terra-295", "Dominio anticipato di Apocalisse", "Nuove versioni degli eroi mutanti", "Personaggi trasferiti nella continuità principale"],
        "bio": "Era di Apocalisse nasce quando il viaggio temporale di Legion priva il mondo di Charles Xavier prima della fondazione degli X-Men. Apocalisse comincia così la propria conquista con anni di anticipo, mentre Magneto raccoglie l'eredità dell'amico e organizza una resistenza mutante. Nel 1995 Marvel sospese temporaneamente le normali testate X e le sostituì con otto serie ambientate nella nuova realtà, racchiuse fra X-Men: Alpha e X-Men: Omega. Ogni fronte segue una missione diversa ma contribuisce allo stesso piano: verificare il ricordo di Bishop, proteggere i superstiti e trovare un modo per correggere la storia. Il percorso italiano conserva questa struttura corale senza fondere Terra-295 con le biografie di Terra-616.",
    }),
    ("astonishing-xmen-aoa", {
        "type": "team",
        "founded": "Durante il dominio di Apocalisse",
        "universe": "Terra-295",
        "debut": "Astonishing X-Men #1 (1995)",
        "creators": "Scott Lobdell e Joe Madureira",
        "founders": ["Rogue", "Sabretooth", "Blink", "Wild Child", "Morph", "Sunfire"],
        "members": ["Rogue", "Sabretooth", "Blink", "Wild Child", "Morph", "Sunfire", "Iceman"],
        "bases": ["Villa di Xavier", "Fronte occidentale degli Stati Uniti"],
        "traits": ["Squadra di evacuazione", "Contrasto alle selezioni", "Guerra contro Olocausto", "Distruzione delle fabbriche di Infinites"],
        "bio": "Rogue guida la formazione degli Astonishing X-Men incaricata di fermare le selezioni con cui Olocausto elimina umani e mutanti considerati inadatti. Sabretooth e Wild Child costituiscono il nucleo d'assalto, Blink garantisce spostamenti istantanei, Morph e Sunfire portano versatilità e potenza. La squadra opera lontano dalla base di Magneto e deve conciliare il salvataggio dei prigionieri con la distruzione delle fabbriche di Infinites. Il rapporto protettivo fra Sabretooth e Blink dà alla missione il suo centro emotivo, mentre Rogue affronta anche il peso di essere comandante, compagna di Magneto e madre del giovane Charles.",
    }),
    ("amazing-xmen-aoa", {
        "type": "team",
        "founded": "Durante il dominio di Apocalisse",
        "universe": "Terra-295",
        "debut": "Amazing X-Men #1 (1995)",
        "creators": "Fabian Nicieza e Andy Kubert",
        "founders": ["Quicksilver", "Storm", "Dazzler", "Banshee", "Iceman", "Exodus"],
        "members": ["Quicksilver", "Storm", "Dazzler", "Banshee", "Iceman", "Exodus"],
        "bases": ["Villa di Xavier", "Corridoio di evacuazione del Maine"],
        "traits": ["Evacuazione degli umani", "Intervento rapido", "Scontro con Abyss", "Supporto alle altre squadre X"],
        "bio": "Gli Amazing X-Men sono la formazione mobile guidata da Quicksilver, figlio di Magneto e comandante cresciuto sotto l'ombra della guerra. Storm, Dazzler, Banshee, Iceman ed Exodus lo accompagnano nel Maine per rendere possibile l'evacuazione degli umani verso l'Europa. La squadra affronta la Fratellanza del Caos e Abyss, uno dei Cavalieri di Apocalisse, mentre la situazione alla Villa di Xavier precipita. La velocità di Pietro non è soltanto un potere ma il principio operativo del gruppo: completare la missione, dividersi e raggiungere in tempo gli altri fronti della resistenza.",
    }),
    ("gambit-xternals-aoa", {
        "type": "team",
        "founded": "Prima dell'offensiva finale contro Apocalisse",
        "universe": "Terra-295",
        "debut": "Gambit and the X-Ternals #1 (1995)",
        "creators": "Fabian Nicieza, Tony Daniel e Salvador Larroca",
        "founders": ["Gambit", "Jubilee", "Strong Guy", "Sunspot", "Lila Cheney"],
        "members": ["Gambit", "Jubilee", "Strong Guy", "Sunspot", "Lila Cheney"],
        "bases": ["Resistenza di Magneto", "Rotte interstellari di Lila Cheney"],
        "traits": ["Missioni clandestine", "Teletrasporto interstellare", "Recupero del Cristallo M'Kraan", "Legame con l'Impero Shi'ar"],
        "bio": "Gli X-Ternals sono il gruppo clandestino di Gambit, formato da Jubilee, Strong Guy, Sunspot e dalla teleporta Lila Cheney. Magneto affida loro la missione più lontana dalla guerra terrestre: raggiungere lo spazio Shi'ar e recuperare un frammento del Cristallo M'Kraan, necessario per dimostrare che i ricordi di Bishop appartengono a una realtà cancellata. L'operazione combina infiltrazione, pirateria cosmica e rapporti personali già incrinati. La squadra rappresenta la versione di Terra-295 della tradizione di X-Force, ma mantiene un'identità autonoma legata alla leadership irregolare di Gambit.",
    }),
    ("generation-next-aoa", {
        "type": "team",
        "founded": "Durante la guerra di resistenza",
        "universe": "Terra-295",
        "debut": "Generation Next #1 (1995)",
        "creators": "Scott Lobdell e Chris Bachalo",
        "founders": ["Colossus", "Shadowcat", "Chamber", "Husk", "Mondo", "Skin", "Vincente"],
        "members": ["Colossus", "Shadowcat", "Chamber", "Husk", "Mondo", "Skin", "Vincente"],
        "bases": ["Strutture di addestramento della resistenza", "Core di Seattle"],
        "traits": ["Giovani mutanti addestrati alla guerra", "Missione di salvataggio", "Infiltrazione nel Core", "Conflitto con Sugar Man"],
        "bio": "Generation Next è la classe di giovani mutanti addestrata da Colosso e Shadowcat in un mondo che non concede loro il tempo di diventare adulti. Chamber, Husk, Mondo, Skin e Vincente vengono inviati nel Core di Seattle, complesso industriale e campo di prigionia governato da Sugar Man, per liberare Illyana Rasputin. La missione sfrutta le capacità complementari dei ragazzi e la conoscenza personale che Colosso ha della prigioniera, ma mette in luce anche l'ossessione del comandante per sua sorella. La miniserie è una delle storie più dure dell'evento e definisce quanto la guerra deformi perfino gli ideali degli X-Men.",
    }),
    ("x-calibre-aoa", {
        "type": "team",
        "founded": "Durante il viaggio verso Avalon",
        "universe": "Terra-295",
        "debut": "X-Calibre #1 (1995)",
        "creators": "Warren Ellis e Ken Lashley",
        "founders": ["Nightcrawler", "Mystica", "Switchback"],
        "members": ["Nightcrawler", "Mystica", "Switchback", "Damask"],
        "bases": ["Rotte dei profughi", "Avalon"],
        "traits": ["Ricerca di Destiny", "Protezione dei rifugiati", "Teletrasporto", "Opposizione ai Pale Riders"],
        "bio": "X-Calibre nasce più come alleanza di viaggio che come squadra pianificata. Magneto invia Nightcrawler alla ricerca di Destiny, la precognitiva che può confermare se Bishop ricorda davvero una linea temporale diversa. Il percorso conduce Kurt attraverso le rotte dei rifugiati e il santuario di Avalon, dove si riunisce con Mystica e incontra Switchback; Damask, inizialmente legata ai servitori di Apocalisse, completa poi il gruppo. La missione oppone la possibilità di una comunità pacifica alla brutalità dei Pale Riders e dà a Nightcrawler un ruolo centrale nella salvezza dell'intera realtà.",
    }),
    ("factor-x-aoa", {
        "type": "team",
        "founded": "Durante il consolidamento del regime di Apocalisse",
        "universe": "Terra-295",
        "debut": "Factor X #1 (1995)",
        "creators": "John Francis Moore, Steve Epting e Terry Dodson",
        "founders": ["Cyclops", "Havok", "Bestia Nera", "Northstar", "Aurora", "Cannonball"],
        "members": ["Cyclops", "Havok", "Bestia Nera", "Northstar", "Aurora", "Cannonball", "Amazon", "Bedlam Brothers"],
        "bases": ["Recinti di Sinistro", "Laboratori di Bestia Nera"],
        "traits": ["Elite Mutant Force", "Controllo dei prigionieri", "Servizio al regime", "Conflitto fra Cyclops e Havok"],
        "bio": "Factor X racconta l'Elite Mutant Force dall'interno del sistema di Apocalisse. Cyclops e Havok sono ufficiali cresciuti sotto Mister Sinister, affiancati da Bestia Nera e da reparti come Northstar, Aurora e Cannonball. Il loro compito è controllare i recinti e soffocare ogni ribellione, ma Scott comincia a mettere in discussione ciò che vede nei laboratori e a favorire segretamente alcune fughe. La rivalità con Havok trasforma la crisi morale in uno scontro familiare. Il gruppo non è una versione eroica di X-Factor: è l'apparato del regime, osservato nel momento in cui le sue lealtà iniziano a spezzarsi.",
    }),
    ("return-age-of-apocalypse", {
        "type": "event",
        "period": "2005 editorialmente",
        "universe": "Terra-295",
        "debut": "X-Men: Age of Apocalypse One Shot e X-Men: Age of Apocalypse #1 (2005)",
        "creators": "Akira Yoshida, Chris Bachalo e i team creativi del one-shot celebrativo",
        "trigger": "Il decennale dell'evento riapre Terra-295 dopo gli eventi di X-Men: Omega",
        "scope": "Un one-shot con quattro storie e una miniserie di sei numeri, raccolti in un volume italiano",
        "factions": ["X-Men di Magneto", "Superstiti umani e mutanti", "Mister Sinister", "Forze residue del vecchio regime"],
        "consequences": ["Conferma della sopravvivenza di Terra-295", "Nuovi personaggi nella realtà alternativa", "Ricostruzione incompleta dopo Apocalisse", "Ponte verso successive visite multiversali"],
        "bio": "Nel 2005 Marvel tornò nell'Era di Apocalisse per il decimo anniversario. Il one-shot contiene quattro episodi ambientati in momenti diversi della storia e amplia origini, incontri e sopravvivenze lasciati fuori dal crossover originale. La miniserie successiva riparte invece dopo X-Men: Omega e mostra Terra-295 come una realtà ancora esistente, impegnata a ricostruirsi sulle rovine del regime. Magneto e i suoi X-Men devono affrontare le conseguenze politiche e biologiche della guerra, insieme a minacce rimaste nascoste. Il percorso resta distinto sia dalla saga del 1995 sia dalle successive incursioni di personaggi di Terra-295 in altre continuità.",
    }),
])


def update_profiles() -> None:
    character_path = DATA / "character-profiles.json"
    characters = json.loads(character_path.read_text(encoding="utf-8"))
    profiles = characters.setdefault("profiles", {})
    for profile_id in CHARACTER_PROFILES:
        profiles.pop(profile_id, None)
    profiles.update(CHARACTER_PROFILES)
    characters["version"] = max(int(characters.get("version", 0)), 5)
    dump(character_path, characters)

    editorial_path = DATA / "editorial-profiles.json"
    editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
    profiles = editorial.setdefault("profiles", {})
    for profile_id in EDITORIAL_PROFILES:
        profiles.pop(profile_id, None)
    profiles.update(EDITORIAL_PROFILES)
    editorial["version"] = max(int(editorial.get("version", 0)), 4)
    dump(editorial_path, editorial)


def write_audit(paths: list[dict[str, Any]]) -> None:
    audit = {
        "version": 1,
        "scope": "Terra-295 nella L'era di Apocalisse Collection Panini #1–7",
        "publishedThrough": "Gennaio 2015 per l'edizione fisica selezionata",
        "physicalIssues": len(PHYSICAL),
        "usaIssues": sum(len(set(contents)) for contents in VOLUME_CONTENTS.values()),
        "usaStories": 53,
        "paths": {payload["id"]: payload["totalRequired"] for payload in paths},
        "sharedPhysicalModel": "Ogni percorso figlio riusa ERAPOCOL_P:1–7 e limita readingStep ai contenuti USA pertinenti.",
        "scopingNotes": [
            "I volumi #1–6 raccolgono il nucleo della saga originale; il #7 raccoglie il one-shot e la miniserie del 2005.",
            "Il primo volume include la transizione finale dalla linea temporale originaria e X-Men: Alpha, ma non viene presentato come raccolta integrale di Legion Quest.",
            "X-Man, Weapon X e le sei squadre seguono soltanto le rispettive miniserie in quattro parti, senza trasformare semplici apparizioni in tappe.",
            "Il one-shot del 2005 contiene quattro storie ma conserva un solo ID di albo USA nel modello dei contenuti.",
        ],
        "imageRequests": {
            "characters": {
                "weapon-x-aoa": "weapon-x-aoa.jpg",
                "x-man-aoa": "x-man-aoa.jpg",
            },
            "teams": {
                "amazing-xmen-aoa": "amazing-xmen-aoa.jpg",
                "astonishing-xmen-aoa": "astonishing-xmen-aoa.jpg",
                "gambit-xternals-aoa": "gambit-xternals-aoa.jpg",
                "generation-next-aoa": "generation-next-aoa.jpg",
                "x-calibre-aoa": "x-calibre-aoa.jpg",
                "factor-x-aoa": "factor-x-aoa.jpg",
            },
            "optional": {
                "age-of-apocalypse": "age-of-apocalypse.jpg",
                "x-universe-aoa": "x-universe-aoa.jpg",
            },
            "events": "Le schede evento usano automaticamente la copertina del primo volume del percorso.",
        },
        "sources": [
            "https://www.comicsbox.it/serie/ERAPOCOL_P",
            *[f"https://www.comicsbox.it/albo/ERAPOCOL_P_{number:03d}" for number in range(1, 8)],
            "https://www.marvel.com/comics/guides/84/age-of-apocalypse-the-complete-event",
            "https://www.marvel.com/teams-and-groups/x-men-age-of-apocalypse",
        ],
    }
    dump(DATA / "age-of-apocalypse-audit.json", audit)


def main() -> None:
    paths = [build_path(path_id) for path_id in PATH_CONFIG]
    for payload in paths:
        dump(CHARACTERS / f"{payload['id']}.json", payload)
    update_manifest(paths)
    update_hubs()
    update_profiles()
    write_audit(paths)
    print("Era di Apocalisse:", ", ".join(f"{row['id']}={row['totalRequired']}" for row in paths))


if __name__ == "__main__":
    main()
