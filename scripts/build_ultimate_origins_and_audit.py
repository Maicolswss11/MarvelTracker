#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7500
MANIFEST_VERSION = 11


def unpack(cid: str) -> dict:
    spec = json.loads((DATA / "encoded" / f"{cid}.json").read_text(encoding="utf-8"))
    encoded = "".join((ROOT / source).read_text(encoding="ascii").strip() for source in spec["sources"])
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


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
        json.dumps({"encoding":"gzip-base64-parts","sources":sources}, separators=(",", ":")), encoding="utf-8"
    )
    stub = {k:v for k,v in character.items() if k not in {"issues","availableTotal"}}
    stub["issueSources"] = [f"data/encoded/{cid}.json"]
    (DATA / "characters" / f"{cid}.json").write_text(json.dumps(stub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{character['name']}: {len(character['issues'])} albi")


def resequence(issues: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for issue in issues:
        if issue["id"] in seen:
            continue
        seen.add(issue["id"])
        item = deepcopy(issue)
        item["seq"] = len(result) + 1
        result.append(item)
    return result


def themed(source: dict, *, era: str, era_sub: str, instruction: str | None = None) -> dict:
    item = deepcopy(source)
    item["era"] = era
    item["eraSub"] = era_sub
    if instruction:
        item["instruction"] = instruction
    item["required"] = True
    item["skip"] = False
    item.pop("future", None)
    return item


def make_world_issue(n: int, title: str, date: str, era: str, instruction: str) -> dict:
    return {
        "id": f"MWORLD_M:{n}",
        "seq": 0,
        "seriesId": "MWORLD_M",
        "series": "Marvel World",
        "publisher": "Panini Comics",
        "n": n,
        "name": f"Marvel World #{n}",
        "title": title,
        "date": date,
        "dateQuality": "curata",
        "era": era,
        "eraSub": "Galactus arriva dalla Terra-616 e trascina Terra-1610 verso Cataclisma",
        "cover": f"https://www.comicsbox.it/cover/MWORLD_M_{n:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/MWORLD_M_{n:03d}",
        "required": True,
        "skip": False,
        "instruction": instruction,
        "coverSource": "ComicsBox",
    }


def build_route(cid: str, name: str, subtitle: str, accent: str, description: str, issues: list[dict], series: list[dict]) -> dict:
    issues = resequence(issues)
    return {
        "id": cid,
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


def annotate_crossovers(master: list[dict]) -> None:
    blocks = {
        "Ultimate War": {"ULTS_M:5", "ULTS_M:6"},
        "Ultimate Six": {"ULTS_M:10", "ULTS_M:11", "ULTS_M:12", "ULTS_M:13"},
        "Ultimate Nightmare": {"ULTS_M:13", "ULTS_M:14", "ULTS_M:15"},
        "Ultimate Secret": {"ULTS_M:17", "ULTS_M:18", "ULTS_M:19", "ULTS_M:20"},
        "Ultimate Extinction": {"ULTS_M:23", "ULTS_M:24", "ULTS_M:25", "ULTS_M:26", "ULTS_M:27"},
        "Ultimate Power / Vision": {"ULTS_M:30", "ULTS_M:31", "ULTS_M:32", "ULTS_M:33", "ULTS_M:34", "ULTS_M:35", "ULTS_M:36"},
        "Ultimate Origins": {"MCROS_M:54"},
        "Ultimatum": {"ULTS_M:41", "ULTS_M:42", "ULTS_M:43", "ULSM_M:68", "ULSM_M:69", "ULSM_M:70", "ULSM_M:71", "ULXM_M:52", "ULXM_M:53"},
        "Cataclisma": {"MWORLD_M:23", "MWORLD_M:24", "MWORLD_M:25", "MWORLD_M:26", "ULTC_SM_M:28", "ULTCM_M:28", "UCAV_M:28"},
        "Ultimate End / Secret Wars": {"ULTC_SM_M:36", "ULTC_SM_M:37"},
    }
    for issue in master:
        tags = [name for name, ids in blocks.items() if issue["id"] in ids]
        if not tags:
            continue
        issue["crossover"] = tags
        if issue["id"] == "ULTS_M:13":
            issue["instruction"] = "PONTE EVENTO: chiude Ultimate Six e apre Ultimate Nightmare. Leggi l'albo intero prima di proseguire."
        elif "Cataclisma" in tags:
            issue["instruction"] = "CATACLISMA: segui la sequenza curata del percorso master; Hunger e Last Stand incorniciano i tie-in delle tre testate Ultimate."
        elif "Ultimatum" in tags:
            issue["instruction"] = "ULTIMATUM: mantieni l'ordine del percorso master; gli spillati italiani mescolano evento principale e tie-in delle singole testate."
        elif "Ultimate End / Secret Wars" in tags:
            issue["instruction"] = "ULTIMATE END: conclusione di Terra-1610 su Battleworld, da leggere nel contesto di Secret Wars."
        else:
            issue["instruction"] = f"CROSSOVER: {', '.join(tags)}. Segui questa tappa nell'ordine curato del percorso master."


def main() -> None:
    master = unpack("ultimate-universe")
    issues = [deepcopy(issue) for issue in master["issues"] if not issue["id"].startswith("MWORLD_M:")]

    world23 = make_world_issue(23, "Hunger: La furia di Galactus, pt 1", "Maggio 2014", "Hunger — prologo a Cataclisma", "PROLOGO: Galactus della Terra-616 entra nell'Universo Ultimate. Leggi prima di Cataclisma.")
    world24 = make_world_issue(24, "Hunger: La furia di Galactus, pt 2", "Luglio 2014", "Hunger — prologo a Cataclisma", "PROLOGO: conclude Hunger e porta direttamente a Cataclisma.")
    world25 = make_world_issue(25, "Cataclisma: L'ultima battaglia degli Ultimates 1", "Agosto 2014", "Cataclisma", "EVENTO PRINCIPALE: prologo Vision + prime due parti di The Ultimates' Last Stand.")
    world26 = make_world_issue(26, "Cataclisma: L'ultima battaglia degli Ultimates 2", "Ottobre 2014", "Cataclisma", "EVENTO PRINCIPALE: conclude The Ultimates' Last Stand dopo i tie-in Spider-Man, X-Men e Ultimates.")

    tie_order = ["ULTC_SM_M:28", "ULTCM_M:28", "UCAV_M:28"]
    tie_ids = set(tie_order)
    first_tie = next((idx for idx, issue in enumerate(issues) if issue["id"] in tie_ids), None)
    if first_tie is None:
        raise RuntimeError("Cataclisma: tie-in principali non trovati nel master")
    tie_map = {issue["id"]: deepcopy(issue) for issue in issues if issue["id"] in tie_ids}
    missing_ties = [issue_id for issue_id in tie_order if issue_id not in tie_map]
    if missing_ties:
        raise RuntimeError(f"Cataclisma: tie-in mancanti {missing_ties}")
    issues = [issue for issue in issues if issue["id"] not in tie_ids]
    block = [world23, world24, world25] + [tie_map[issue_id] for issue_id in tie_order] + [world26]
    issues[first_tie:first_tie] = block
    issues = resequence(issues)
    annotate_crossovers(issues)

    master["issues"] = issues
    master["totalRequired"] = len(issues)
    master["availableTotal"] = len(issues)
    master["subtitle"] = "Terra-1610 · percorso completo e auditato"
    master["description"] = (
        "Percorso master curato del vecchio Universo Ultimate. Integra le linee principali, le miniserie autonome, "
        "Ultimate Origins, Hunger e Cataclisma, con annotazioni esplicite sui crossover. Gli stessi ID fisici sono "
        "riutilizzati nei percorsi tematici: Recuperato resta condiviso, mentre Letto rimane specifico del percorso."
    )
    if not any(item.get("id") == "MWORLD_M" for item in master.get("series", [])):
        master.setdefault("series", []).append({"id":"MWORLD_M","name":"Marvel World","publisher":"Panini Comics","range":"#23–26 (Hunger / Cataclisma)"})
    pack(master)
    source = {issue["id"]: issue for issue in issues}

    origins = build_route(
        "ultimate-origins", "Ultimate Origins", "Le origini segrete di Terra-1610", "#e1c46b",
        "La miniserie Ultimate Origins #1-5 raccolta integralmente nell'edizione italiana Marvel Crossover #54: Weapon X/Wolverine, Nick Fury, Capitan America, Hulk, Fantastic Four e il retroscena sulla nascita dei mutanti Ultimate.",
        [themed(source["MCROS_M:54"], era="Ultimate Origins", era_sub="Le origini segrete dell'Universo Ultimate", instruction="VOLUME UNICO: contiene tutti e cinque i capitoli USA di Ultimate Origins.")],
        [{"id":"MCROS_M","name":"Marvel Crossover","publisher":"Marvel Italia","range":"#54"}],
    )
    thor = build_route(
        "ultimate-thor", "Ultimate Thor", "Le origini del Dio del Tuono · Terra-1610", "#75b9ff",
        "La miniserie Ultimate Thor di Jonathan Hickman e Carlos Pacheco, pubblicata in Italia in due albi di Ultimate Comics: ricostruisce Asgard, Loki e il passato di Thor prima della fase moderna degli Ultimates.",
        [
            themed(source["ULTCM_M:1"], era="Ultimate Thor — origini", era_sub="Asgard, Loki e la nascita del Thor Ultimate", instruction="ORIGINI DI THOR: parte 1 della miniserie Ultimate Thor."),
            themed(source["ULTCM_M:2"], era="Ultimate Thor — origini", era_sub="Asgard, Loki e la nascita del Thor Ultimate", instruction="ORIGINI DI THOR: conclusione della miniserie Ultimate Thor."),
        ],
        [{"id":"ULTCM_M","name":"Ultimate Comics","publisher":"Panini Comics","range":"#1–2"}],
    )
    cap = build_route(
        "ultimate-cap", "Ultimate Capitan America", "Steve Rogers · Terra-1610", "#6e9cff",
        "Percorso compatto di Steve Rogers Ultimate: l'origine bellica e il risveglio in Ultimates, l'annual italiano con Capitan America e Hulk e la miniserie Ultimate Captain America di Jason Aaron.",
        [
            themed(source["ULTS_M:1"], era="Capitan America — origine e risveglio", era_sub="1945, sacrificio e ritorno nel presente", instruction="ORIGINE: apre con la missione del 1945 e introduce il Capitan America Ultimate."),
            themed(source["MCROS_M:57"], era="Annual e retroscena", era_sub="Capitan America, Hulk e l'origine di Pantera Nera", instruction="ANNUAL: materiale di raccordo su Capitan America/Hulk e l'origine di Pantera Nera Ultimate."),
            themed(source["ULTCM_M:3"], era="Ultimate Captain America", era_sub="Non più solo", instruction="MINISERIE: Ultimate Captain America, prima metà."),
            themed(source["ULTCM_M:4"], era="Ultimate Captain America", era_sub="Non più solo", instruction="MINISERIE: Ultimate Captain America, conclusione."),
        ],
        [
            {"id":"ULTS_M","name":"Ultimates (I)","publisher":"Marvel Italia","range":"#1"},
            {"id":"MCROS_M","name":"Marvel Crossover","publisher":"Marvel Italia","range":"#57"},
            {"id":"ULTCM_M","name":"Ultimate Comics","publisher":"Panini Comics","range":"#3–4"},
        ],
    )
    cataclysm = build_route(
        "ultimate-cataclysm", "Cataclisma", "Hunger → Ultima battaglia degli Ultimates", "#9b7cff",
        "Percorso evento curato: Hunger porta Galactus della Terra-616 nella Terra-1610, poi The Ultimates' Last Stand incornicia i tie-in di Spider-Man, X-Men e Ultimates.",
        [
            themed(world23, era="Hunger", era_sub="Galactus entra nella Terra-1610"),
            themed(world24, era="Hunger", era_sub="Galactus entra nella Terra-1610"),
            themed(world25, era="Cataclisma — evento principale", era_sub="The Ultimates' Last Stand, apertura"),
            themed(source["ULTC_SM_M:28"], era="Cataclisma — tie-in", era_sub="Spider-Man", instruction="TIE-IN: Cataclysm: Ultimate Comics Spider-Man."),
            themed(source["ULTCM_M:28"], era="Cataclisma — tie-in", era_sub="X-Men", instruction="TIE-IN: Cataclysm: Ultimate Comics X-Men."),
            themed(source["UCAV_M:28"], era="Cataclisma — tie-in", era_sub="Ultimates", instruction="TIE-IN: Cataclysm: Ultimate Comics The Ultimates."),
            themed(world26, era="Cataclisma — evento principale", era_sub="The Ultimates' Last Stand, conclusione"),
        ],
        [
            {"id":"MWORLD_M","name":"Marvel World","publisher":"Panini Comics","range":"#23–26"},
            {"id":"ULTC_SM_M","name":"Ultimate Comics Spider-Man","publisher":"Panini Comics","range":"#28"},
            {"id":"ULTCM_M","name":"Ultimate Comics","publisher":"Panini Comics","range":"#28"},
            {"id":"UCAV_M","name":"Ultimate Comics Avengers","publisher":"Panini Comics","range":"#28"},
        ],
    )
    for route in (origins, thor, cap, cataclysm):
        pack(route)

    manifest_path = DATA / "characters.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    replace_ids = {"ultimate-universe", "ultimate-origins", "ultimate-thor", "ultimate-cap", "ultimate-cataclysm", "ultimate-origins-annuals"}
    entries = [entry for entry in manifest["characters"] if entry["id"] not in replace_ids]

    def meta(route: dict, type_: str, logo: str) -> dict:
        return {
            "id":route["id"], "name":route["name"], "subtitle":route["subtitle"], "type":type_,
            "primaryHub":"ultimate-classic", "hubs":["ultimate-classic"], "accent":route["accent"], "logo":logo,
            "data":f"data/characters/{route['id']}.json", "start":route["start"], "end":route["end"], "totalRequired":route["totalRequired"],
        }

    entries += [
        meta(master, "universe", "assets/heroes/ultimate-universe.svg"),
        meta(origins, "event", "assets/heroes/ultimate-origins.svg"),
        meta(thor, "character", "assets/heroes/ultimate-thor.svg"),
        meta(cap, "character", "assets/heroes/ultimate-cap.svg"),
        meta(cataclysm, "event", "assets/heroes/ultimate-cataclysm.svg"),
    ]
    manifest["characters"] = entries
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    hubs_path = DATA / "hubs.json"
    hubs = json.loads(hubs_path.read_text(encoding="utf-8"))
    hub = next(item for item in hubs["hubs"] if item["id"] == "ultimate-classic")
    hub["subtitle"] = "Terra-1610 · universo compatto, completo e curato"
    hub["featuredPath"] = "ultimate-universe"
    hub["groups"] = [
        {"id":"master","label":"Segui tutto l'universo","paths":["ultimate-universe"]},
        {"id":"core","label":"Linee principali","paths":["ultimate-spiderman-classic","ultimate-xmen","ultimates","ultimate-fantastic-four"]},
        {"id":"origins","label":"Origini e personaggi","paths":["ultimate-origins","ultimate-ironman","ultimate-thor","ultimate-cap"]},
        {"id":"events","label":"Eventi e miniserie","paths":["ultimate-team-up","ultimate-specials","ultimate-wolverine","ultimate-doomsday","ultimate-cataclysm","ultimate-post-cataclysm"]},
    ]
    hubs_path.write_text(json.dumps(hubs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    logos = {
        "ultimate-origins.svg": ("#e1c46b", "O"),
        "ultimate-thor.svg": ("#75b9ff", "T"),
        "ultimate-cap.svg": ("#6e9cff", "A"),
        "ultimate-cataclysm.svg": ("#9b7cff", "C"),
    }
    for filename, (accent, letter) in logos.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" rx="26" fill="#090b11"/><circle cx="64" cy="64" r="48" fill="none" stroke="{accent}" stroke-width="6"/><text x="64" y="82" text-anchor="middle" font-family="Arial" font-size="54" font-weight="900" fill="#f7f7fb">{letter}</text></svg>'
        (ROOT / "assets" / "heroes" / filename).write_text(svg, encoding="utf-8")

    audit = {
        "version": 1,
        "masterTotal": len(master["issues"]),
        "addedPhysicalIssues": ["MWORLD_M:23", "MWORLD_M:24", "MWORLD_M:25", "MWORLD_M:26"],
        "verifiedBlocks": ["Ultimate War", "Ultimate Six", "Ultimate Nightmare", "Ultimate Secret", "Ultimate Extinction", "Ultimate Power / Vision", "Ultimate Origins", "Ultimatum", "Cataclisma", "Ultimate End / Secret Wars"],
        "notes": "L'ordine master conserva la sequenza editoriale italiana generale, ma Cataclisma è stato curato esplicitamente come Hunger -> Last Stand apertura -> tie-in -> Last Stand conclusione.",
    }
    (DATA / "ultimate-audit.json").write_text(json.dumps(audit, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("Ultimate origins + audit completati")
    print(f"- master: {len(master['issues'])} tappe")
    print("- Ultimate Origins: 1 albo italiano / 5 capitoli USA")
    print("- Ultimate Thor: 2 albi")
    print("- Ultimate Capitan America: 4 albi")
    print("- Cataclisma: 7 albi")


if __name__ == "__main__":
    main()
