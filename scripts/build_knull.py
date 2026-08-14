#!/usr/bin/env python3
"""Build Knull's complete core saga from existing Italian physical issues."""

from __future__ import annotations

import base64
import copy
import gzip
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    if path.name == "character-profiles.json":
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(serialized, encoding="utf-8")


def unpack(path_id: str) -> dict[str, Any]:
    stub = read_json(DATA / "characters" / f"{path_id}.json")
    if not isinstance(stub.get("issueSources"), list):
        return stub
    spec = read_json(DATA / "encoded" / f"{path_id}.json")
    encoded = "".join((ROOT / source).read_text(encoding="ascii").strip() for source in spec["sources"])
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def content(code: str, series: str, number: int, title: str | None = None) -> dict[str, Any]:
    series_id = code.rsplit("_", 1)[0]
    return {
        "id": code,
        "seriesId": series_id,
        "series": series,
        "number": number,
        "title": title or f"{series} #{number}",
        "url": f"https://www.comicsbox.it/albo/{code}",
    }


def manual_issue(
    issue_id: str,
    number: int,
    name: str,
    title: str,
    date: str,
    series_id: str,
    series: str,
    code: str,
    contents: list[dict[str, Any]],
    era: str,
    instruction: str,
    publisher: str = "Panini Comics",
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "n": number,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": series_id,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "era": era,
        "eraSub": "La storia di Knull in ordine di rivelazione",
        "instruction": instruction,
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
        "contents": contents,
        "contentsStatus": "path-scoped",
    }


def clone_selected(
    source: dict[str, Any],
    content_ids: list[str],
    era: str,
    note: str = "",
) -> dict[str, Any]:
    issue = copy.deepcopy(source)
    available = {row.get("id"): row for row in issue.get("contents", []) if row.get("id")}
    missing = [code for code in content_ids if code not in available]
    if missing:
        raise RuntimeError(f"{issue['id']}: contenuti mancanti {missing}")
    issue["contents"] = [available[code] for code in content_ids]
    issue["contentsStatus"] = "path-scoped"
    issue["era"] = era
    issue["eraSub"] = "La storia di Knull in ordine di rivelazione"
    issue["publisher"] = "Panini Comics"
    labels = [available[code].get("title") or code for code in content_ids]
    issue["title"] = " · ".join(labels)
    issue["instruction"] = "Leggi in questo albo: " + "; ".join(labels) + "."
    if note:
        issue["instruction"] += " " + note
    issue["required"] = True
    issue["skip"] = False
    issue["future"] = False
    issue["sharedWith"] = sorted(set(issue.get("sharedWith", [])) | {"Venom"})
    return issue


def main() -> None:
    venom = unpack("venom")
    thor = unpack("thor")
    absolute = unpack("absolute-carnage")
    king = unpack("king-in-black")
    venom_by_id = {row["id"]: row for row in venom["issues"]}
    thor_by_id = {row["id"]: row for row in thor["issues"]}
    absolute_by_id = {row["id"]: row for row in absolute["issues"]}
    king_by_id = {row["id"]: row for row in king["issues"]}

    issues: list[dict[str, Any]] = []

    thor_seed = copy.deepcopy(thor_by_id["THORVE_M:176"])
    thor_seed.update({
        "era": "Il primo seme",
        "eraSub": "All-Black e il futuro Macellatore di Dei",
        "title": "Thor: God of Thunder #6 — Le origini di Gorr",
        "instruction": "Leggi Thor: God of Thunder #6: è la prima apparizione canonica, ancora senza nome, di Knull e di All-Black.",
        "publisher": "Marvel Italia / Panini Comics",
        "required": True,
        "skip": False,
        "future": False,
        "contents": [content("THORGOT_006", "Thor: God of Thunder", 6, "Thor: God of Thunder #6")],
        "contentsStatus": "path-scoped",
        "sharedWith": sorted(set(thor_seed.get("sharedWith", [])) | {"Thor"}),
    })
    issues.append(thor_seed)

    issues.append(manual_issue(
        "GUARDGAL_P:24", 24,
        "Guardiani della Galassia #24", "Chi sono i Klyntar?", "Agosto 2015",
        "GUARDGAL_P", "Guardiani della Galassia", "GUARDGAL_P_024",
        [content("GUGX3_023", "Guardians of the Galaxy vol. 3", 23)],
        "Il mito di Klyntar",
        "Leggi solo Guardians of the Galaxy vol. 3 #23: introduce il pianeta-prigione Klyntar e la versione della storia conosciuta dai simbionti.",
    ))

    for issue_id, ids in [
        ("VENOMP:18", ["VENOM5_001", "VENOM5_002"]),
        ("VENOMP:19", ["VENOM5_003"]),
        ("VENOMP:20", ["VENOM5_004"]),
        ("VENOMP:21", ["VENOM5_005"]),
        ("VENOMP:22", ["VENOM5_006"]),
    ]:
        issues.append(clone_selected(venom_by_id[issue_id], ids, "Rex — il Dio dei Simbionti", "Qui avvengono l'incontro con Knull e la rivelazione delle sue origini."))

    issues.append(clone_selected(
        venom_by_id["VENOMP:23"], ["WOVVENAM_001"], "Grendel sulla Terra",
        "È il flashback sui simbionti-soldato del Vietnam; salta Venom: First Host #5 in questa tappa.",
    ))

    for issue_id, ids in [
        ("VENOMP:24", ["VENOM5_007"]),
        ("VENOMP:25", ["VENOM5_008"]),
        ("VENOMP:26", ["WEOVECRBRN_001", "VENOM5_009"]),
        ("VENOMP:27", ["VENOM5_010"]),
        ("VENOMP:28", ["VENOM5_011"]),
        ("VENOMP:29", ["VENOM5_012"]),
    ]:
        issues.append(clone_selected(venom_by_id[issue_id], ids, "Codici e figli dell'alveare"))

    issues.append(manual_issue(
        "SILVERBLAC:1", 1,
        "Silver Surfer: Nero", "Silver Surfer: Black #1–5", "Gennaio 2020",
        "SILVERBLAC", "Silver Surfer: Nero", "SILVERBLAC_001",
        [content(f"SILSURBLAK_{number:03d}", "Silver Surfer: Black", number) for number in range(1, 6)],
        "Lo scontro fuori dal tempo",
        "Leggi l'intero volume: Silver Surfer: Black #1–5. Il viaggio nel passato mostra lo scontro più antico fra un eroe Marvel e Knull.",
    ))

    issues.append(clone_selected(venom_by_id["VENOMP:30"], ["WEOVECTCG_001"], "Verso Absolute Carnage"))
    issues.append(clone_selected(
        venom_by_id["VENOMP:34"], ["VENOM5_016"], "Verso Absolute Carnage",
        "I capitoli #13–15 legati alla Guerra dei Regni restano nel percorso Venom e non sono obbligatori qui.",
    ))

    for issue_id, codes, era, instruction in [
        ("MMMI:227", ["ABSCARNAGE_001"], "Absolute Carnage", "Absolute Carnage #1."),
        ("MMMI:228", ["ABSCARNAGE_002", "ABSCARNAGE_003"], "Absolute Carnage", "Absolute Carnage #2–3."),
        ("MMMI:229", ["ABSCARNAGE_004", "ABSCARNAGE_005"], "Absolute Carnage", "Absolute Carnage #4–5: la scelta di Eddie libera Knull."),
    ]:
        source = copy.deepcopy(absolute_by_id[issue_id])
        source["era"] = era
        source["eraSub"] = "I codici aprono la prigione di Klyntar"
        source["contents"] = [content(code, "Absolute Carnage", int(code[-3:])) for code in codes]
        source["contentsStatus"] = "path-scoped"
        source["instruction"] = instruction
        source["sharedWith"] = ["Absolute Carnage"]
        issues.append(source)

    for issue_id, ids in [
        ("VENOMP:36", ["VENOM5_017"]),
        ("VENOMP:37", ["VENOM5_018", "VENOM5_019"]),
        ("VENOMP:38", ["VENOM5_020"]),
    ]:
        issues.append(clone_selected(venom_by_id[issue_id], ids, "Absolute Carnage — il fronte di Venom"))

    for issue_id, ids in [
        ("VENOMP:39", ["VENOM5_021"]),
        ("VENOMP:40", ["VENOM5_022"]),
        ("VENOMP:41", ["VENOM5_023"]),
        ("VENOMP:43", ["VENOM5_024"]),
        ("VENOMP:44", ["VENOM5_025"]),
        ("VENOMP:45", ["VENOM5_026"]),
        ("VENOMP:46", ["VENOM5_027"]),
        ("VENOMP:47", ["VENOM5_028"]),
        ("VENOMP:48", ["WEBWRAITH_001", "VENOM5_029"]),
        ("VENOMP:49", ["WOVEMPEND_001", "VENOM5_030"]),
    ]:
        issues.append(clone_selected(venom_by_id[issue_id], ids, "La marcia del Re in Nero"))

    for issue_id, codes, instruction in [
        ("MMMI:244", ["KINGBLACK_001"], "King in Black #1."),
        ("MMMI:245", ["KINGBLACK_002", "KINGBLACK_003"], "King in Black #2–3."),
        ("MMMI:246", ["KINGBLACK_004", "KINGBLACK_005"], "King in Black #4–5: conclusione dell'invasione."),
    ]:
        source = copy.deepcopy(king_by_id[issue_id])
        source["era"] = "King in Black"
        source["eraSub"] = "Knull invade la Terra"
        source["contents"] = [content(code, "King in Black", int(code[-3:])) for code in codes]
        source["contentsStatus"] = "path-scoped"
        source["instruction"] = instruction
        source["sharedWith"] = ["King in Black"]
        issues.append(source)

    for issue_id, ids in [
        ("VENOMP:50", ["VENOM5_031"]),
        ("VENOMP:51", ["VENOM5_032", "VENOM5_033"]),
        ("VENOMP:52", ["VENOM5_034"]),
        ("VENOMP:53", ["VENOM5_035"]),
    ]:
        issues.append(clone_selected(venom_by_id[issue_id], ids, "King in Black — il fronte di Venom"))

    issues.append(clone_selected(
        venom_by_id["VENOMP:105"], ["VNM6_250"], "Il ritorno di Knull",
        "È il nuovo punto di ripartenza del 2026; il percorso verrà esteso con i capitoli successivi pertinenti.",
    ))

    for position, issue in enumerate(issues, 1):
        issue["seq"] = position
        issue["readingStep"] = {
            "pathId": "knull",
            "position": position,
            "contentIds": [row["id"] for row in issue.get("contents", [])],
            "scope": "selected-contents",
        }

    character = {
        "id": "knull",
        "name": "Knull",
        "subtitle": "Il Dio dei Simbionti",
        "accent": "#c44b62",
        "start": "Thor #176 — Novembre 2013",
        "end": "Venom #105 — Febbraio 2026",
        "description": "Percorso essenziale completo di Knull, dalla prima ombra senza nome in Thor: God of Thunder #6 alla rivelazione in Venom, attraverso Absolute Carnage e King in Black, fino al ritorno del 2026. Ogni tappa indica soltanto i capitoli USA pertinenti quando l'albo italiano contiene materiale aggiuntivo.",
        "timelineMode": True,
        "readingOrderSource": "Marvel Knull / Road to King in Black guides; ComicsBox first Italian publication audit",
        "series": [
            {"id": "THORVE_M", "name": "Thor", "publisher": "Marvel Italia / Panini Comics", "range": "prima apparizione"},
            {"id": "GUARDGAL_P", "name": "Guardiani della Galassia", "publisher": "Panini Comics", "range": "mitologia Klyntar"},
            {"id": "VENOMP", "name": "Venom", "publisher": "Panini Comics", "range": "saga principale"},
            {"id": "SILVERBLAC", "name": "Silver Surfer: Nero", "publisher": "Panini Comics", "range": "miniserie completa"},
            {"id": "MMMI", "name": "Marvel Miniserie", "publisher": "Panini Comics", "range": "Absolute Carnage / King in Black"},
        ],
        "archives": [],
        "totalRequired": len(issues),
        "availableTotal": len(issues),
        "issues": issues,
    }
    write_json(DATA / "characters" / "knull.json", character)

    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    manifest["version"] = max(int(manifest.get("version", 1)), 34)
    entry = {
        "id": "knull",
        "name": "Knull",
        "subtitle": "Il Dio dei Simbionti",
        "type": "character",
        "universe": "Terra-616",
        "pathRole": "main",
        "primaryHub": "spider",
        "hubs": ["spider", "cosmic"],
        "accent": "#c44b62",
        "logo": "assets/path-icons/KinginBlack.webp",
        "editorialCover": "https://www.comicsbox.it/cover/VENOMP_020.jpg",
        "data": "data/characters/knull.json",
        "start": character["start"],
        "end": character["end"],
        "totalRequired": character["totalRequired"],
        "relatedPaths": ["venom", "silver-surfer", "thor", "absolute-carnage", "king-in-black"],
    }
    existing = next((row for row in manifest["characters"] if row["id"] == "knull"), None)
    if existing:
        existing.update(entry)
    else:
        venom_index = next(i for i, row in enumerate(manifest["characters"]) if row["id"] == "venom")
        manifest["characters"].insert(venom_index + 1, entry)
    for path_id in ("venom", "absolute-carnage", "king-in-black"):
        row = next(item for item in manifest["characters"] if item["id"] == path_id)
        related = row.setdefault("relatedPaths", [])
        if "knull" not in related:
            related.append("knull")
    write_json(manifest_path, manifest)

    hubs_path = DATA / "hubs.json"
    hubs = read_json(hubs_path)
    for hub_id, group_id in (("spider", "symbiotes"), ("cosmic", "powers")):
        hub = next(row for row in hubs["hubs"] if row["id"] == hub_id)
        group = next(row for row in hub["groups"] if row["id"] == group_id)
        if "knull" not in group["paths"]:
            group["paths"].append("knull")
    write_json(hubs_path, hubs)

    profiles_path = DATA / "character-profiles.json"
    profiles = read_json(profiles_path)
    profiles["version"] = max(int(profiles.get("version", 1)), 6)
    profiles.setdefault("profiles", {})["knull"] = {
        "realName": "Knull",
        "aliases": ["Dio dei Simbionti", "Re in Nero", "Signore dell'Abisso"],
        "universe": "Terra-616",
        "debut": "Venom (2018) #3; apparizione senza nome in Thor: God of Thunder #6",
        "creators": "Donny Cates e Ryan Stegman",
        "affiliations": ["Alveare dei simbionti", "Draghi simbionti", "Chiesa della Nuova Oscurità"],
        "abilities": ["Controllo dell'alveare", "Creazione di simbionti", "Manipolazione dell'oscurità vivente", "Forza e longevità cosmiche"],
        "bio": "Knull è un'entità primordiale che sostiene di esistere da prima che la luce riempisse il cosmo. Quando i Celestiali sconvolgono il suo abisso, forgia dalla propria oscurità All-Black, la Necrospada, e con essa uccide un Celestiale. Perduta la lama che finirà nelle mani di Gorr, Knull crea i simbionti e li governa attraverso una mente alveare. Un colpo di Thor spezza però quel legame: le creature scoprono la possibilità della simbiosi, si ribellano e trasformano i propri corpi nel pianeta-prigione Klyntar. Millenni dopo il drago Grendel, i codici lasciati negli ospiti e il culto di Carnage preparano il suo risveglio. Liberato durante Absolute Carnage, Knull marcia sulla Terra in King in Black, dove Eddie Brock e l'Enigma Force pongono fine al suo regno. La sua ombra resta tuttavia legata alla mitologia dei simbionti e torna a farsi sentire nelle storie di Venom del 2026."
    }
    write_json(profiles_path, profiles)

    print(f"Knull: {len(issues)} albi fisici, biografia e collegamenti aggiornati")


if __name__ == "__main__":
    main()
