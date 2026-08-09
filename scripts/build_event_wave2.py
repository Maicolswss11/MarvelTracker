#!/usr/bin/env python3
"""Build the second curated Terra-616 event wave plus two classic events."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_VERSION = 16


def row(issue_id: str, n: int, name: str, title: str, date: str, series_id: str, series: str,
        publisher: str, cover_code: str, era: str, instruction: str, *, required: bool = True,
        display_number: str | None = None):
    out = {
        "id": issue_id,
        "n": n,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": series_id,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{cover_code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_code}",
        "era": era,
        "instruction": instruction,
        "required": required,
        "skip": not required,
        "future": False,
        "coverSource": "ComicsBox",
    }
    if display_number is not None:
        out["displayNumber"] = display_number
    return out


def mmmi(n: int, title: str, date: str, era: str, instruction: str, *, required: bool = True):
    return row(f"MMMI:{n}", n, f"Marvel Miniserie #{n}", title, date, "MMMI", "Marvel Miniserie",
               "Marvel Italia / Panini Comics", f"MMMI_{n:03d}", era, instruction, required=required)


def spee(n: int, title: str, date: str, instruction: str):
    return row(f"SPEE_M:{n}", n, f"Special Events #{n}", title, date, "SPEE_M", "Special Events",
               "Marvel Italia / Panini Comics", f"SPEE_M_{n:03d}", "Evento principale", instruction)


def secret_wars_classic_issue(n: int, title: str, date: str, chapters: str):
    return row(f"SPE_GS1:{n}", n, f"Speciale Guerre Segrete #{n}", title, date, "SPE_GS1",
               "Speciale Guerre Segrete", "Star Comics", f"SPE_GS1_{n:03d}", "Evento classico",
               f"Marvel Super-Heroes Secret Wars {chapters}.")


def gauntlet_issue(issue_id: str, n: int, name: str, title: str, date: str, chapters: str, code: str,
                   display_number: str | None = None):
    return row(issue_id, n, name, title, date, "MCP_M", "Marvel Comics Presenta", "Play Press",
               code, "Evento classico", f"The Infinity Gauntlet {chapters}.", display_number=display_number)


EVENTS = [
    {
        "id": "secret-wars-1984", "name": "Secret Wars", "subtitle": "Marvel Super Heroes Secret Wars · 1984",
        "accent": "#df4b55", "group": "classic", "scope": "core",
        "description": "Il primo grande crossover Marvel. Percorso sulla prima edizione italiana completa Star Comics del 1990: tre speciali raccolgono tutti i dodici capitoli USA di Marvel Super-Heroes Secret Wars.",
        "readingOrder": [f"Marvel Super-Heroes Secret Wars (1984) #{n}" for n in range(1, 13)],
        "issues": [
            secret_wars_classic_issue(1, "Inizia la guerra", "Marzo 1990", "#1–4"),
            secret_wars_classic_issue(2, "Invasione", "Maggio 1990", "#5–8"),
            secret_wars_classic_issue(3, "E polvere ritornerai", "Luglio 1990", "#9–12"),
        ],
    },
    {
        "id": "infinity-gauntlet", "name": "Il Guanto dell'Infinito", "subtitle": "Thanos · Infinity Gauntlet · 1991",
        "accent": "#a87be8", "group": "classic", "scope": "core",
        "description": "Percorso sulla prima pubblicazione italiana Play Press del 1993. I sei capitoli USA di The Infinity Gauntlet occupano cinque pubblicazioni fisiche perché Marvel Comics Presenta #4/5 uscì come albo doppio unico.",
        "readingOrder": [f"The Infinity Gauntlet (1991) #{n}" for n in range(1, 7)],
        "issues": [
            gauntlet_issue("MCP_M:1", 1, "Marvel Comics Presenta #1", "La Fine comincia qui", "Aprile 1993", "#1", "MCP_M_001"),
            gauntlet_issue("MCP_M:2", 2, "Marvel Comics Presenta #2", "La morte di un Mondo... la fine degli Eroi...", "Maggio 1993", "#2", "MCP_M_002"),
            gauntlet_issue("MCP_M:3", 3, "Marvel Comics Presenta #3", "Scoppia la guerra!", "Giugno 1993", "#3", "MCP_M_003"),
            gauntlet_issue("MCP_M:4/5", 4, "Marvel Comics Presenta #4/5", "Marvel Comics Presenta #4/5", "Luglio 1993", "#4–5", "MCP_M_004", "4/5"),
            gauntlet_issue("MCP_M:6", 6, "Marvel Comics Presenta #6", "Scontro finale!", "Settembre 1993", "#6", "MCP_M_006"),
        ],
    },
    {
        "id": "infinity", "name": "Infinity", "subtitle": "Jonathan Hickman · Thanos · 2013",
        "accent": "#7358c7", "group": "modern2", "scope": "core",
        "description": "Core di Infinity sulla prima edizione italiana Marvel Miniserie #145–150. Copre la miniserie Infinity #1–6; Avengers e New Avengers che si intrecciano all'evento saranno gestiti come espansione/tie-in.",
        "readingOrder": [f"Infinity (2013) #{n}" for n in range(1, 7)],
        "issues": [mmmi(n, f"Infinity, pt {n-144}", ["Marzo 2014","Aprile 2014","Maggio 2014","Giugno 2014","Luglio 2014","Agosto 2014"][n-145], "Evento principale", f"Infinity #{n-144}.") for n in range(145,151)],
    },
    {
        "id": "secret-wars-2015", "name": "Secret Wars", "subtitle": "Jonathan Hickman · Battleworld · 2015",
        "accent": "#d94e4e", "group": "modern2", "scope": "core",
        "description": "Core di Secret Wars 2015: i nove capitoli della miniserie principale nella prima edizione italiana Marvel Miniserie #164–172. Le numerose miniserie di Battleworld restano tie-in separati.",
        "readingOrder": [f"Secret Wars (2015) #{n}" for n in range(1, 10)],
        "issues": [mmmi(n, f"Secret Wars {n-163}", ["Dicembre 2015","Dicembre 2015","Gennaio 2016","Gennaio 2016","Febbraio 2016","Marzo 2016","Aprile 2016","Aprile 2016","Maggio 2016"][n-164], "Evento principale", f"Secret Wars (2015) #{n-163}.") for n in range(164,173)],
    },
    {
        "id": "civil-war-ii", "name": "Civil War II", "subtitle": "Captain Marvel · Iron Man · 2016",
        "accent": "#5580be", "group": "modern2", "scope": "core",
        "description": "Core di Civil War II: numero zero e miniserie principale #1–8, pubblicati in Marvel Miniserie #175–183. I tie-in delle singole testate restano fuori dal conteggio obbligatorio.",
        "readingOrder": ["Civil War II #0", *[f"Civil War II #{n}" for n in range(1,9)]],
        "issues": [mmmi(n, f"Civil War II {n-175}", ["Dicembre 2016","Gennaio 2017","Gennaio 2017","Febbraio 2017","Febbraio 2017","Marzo 2017","Aprile 2017","Aprile 2017","Maggio 2017"][n-175], "Evento principale", f"Civil War II #{n-175}.") for n in range(175,184)],
    },
    {
        "id": "secret-empire", "name": "Secret Empire", "subtitle": "Hydra · Steve Rogers · 2017",
        "accent": "#5e9a68", "group": "modern2", "scope": "core",
        "description": "Core di Secret Empire dal #0 al #10. Secret Empire Omega è mantenuto subito dopo come epilogo facoltativo: utile per chiudere le conseguenze, ma non necessario al 100% del core.",
        "readingOrder": ["Secret Empire #0", *[f"Secret Empire #{n}" for n in range(1,11)], "Secret Empire Omega #1"],
        "issues": [
            *[mmmi(n, f"Secret Empire {n-188}", ["Novembre 2017","Novembre 2017","Dicembre 2017","Dicembre 2017","Gennaio 2018","Gennaio 2018","Febbraio 2018","Febbraio 2018","Marzo 2018","Marzo 2018","Aprile 2018"][n-188], "Evento principale", f"Secret Empire #{n-188}.") for n in range(188,199)],
            mmmi(199, "Secret Empire Omega", "Aprile 2018", "Epilogo facoltativo", "Secret Empire Omega #1: epilogo immediato dell'evento.", required=False),
        ],
    },
    {
        "id": "war-of-the-realms", "name": "La Guerra dei Regni", "subtitle": "Thor · Malekith · 2019",
        "accent": "#d8873f", "group": "modern2", "scope": "core",
        "description": "Core di War of the Realms #1–6 nei quattro Marvel Miniserie italiani #222–225. Il #226, che contiene War of the Realms Omega, è presente come epilogo facoltativo.",
        "readingOrder": [*[f"War of the Realms #{n}" for n in range(1,7)], "War of the Realms Omega #1"],
        "issues": [
            mmmi(222, "La Guerra dei Regni 1", "Settembre 2019", "Evento principale", "War of the Realms #1."),
            mmmi(223, "La Guerra dei Regni 2", "Settembre 2019", "Evento principale", "War of the Realms #2–3."),
            mmmi(224, "La Guerra dei Regni 3: La battaglia del Bifrost Nero", "Ottobre 2019", "Evento principale", "War of the Realms #4–5."),
            mmmi(225, "La Guerra dei Regni 4", "Novembre 2019", "Evento principale", "War of the Realms #6 e conclusione del core."),
            mmmi(226, "La Guerra dei Regni 5", "Dicembre 2019", "Epilogo facoltativo", "War of the Realms Omega #1.", required=False),
        ],
    },
    {
        "id": "absolute-carnage", "name": "Absolute Carnage", "subtitle": "Carnage · Venom · 2019",
        "accent": "#b42735", "group": "modern2", "scope": "core",
        "description": "Core di Absolute Carnage #1–5 nei tre Marvel Miniserie italiani #227–229. I tie-in di Venom, Spider-Man e delle altre testate saranno collegati separatamente.",
        "readingOrder": [f"Absolute Carnage #{n}" for n in range(1,6)],
        "issues": [
            mmmi(227, "Absolute Carnage 1: Il re insanguinato", "Gennaio 2020", "Evento principale", "Absolute Carnage #1."),
            mmmi(228, "Absolute Carnage 2: Il macabro imperatore", "Febbraio 2020", "Evento principale", "Absolute Carnage #2–3."),
            mmmi(229, "Absolute Carnage 3: Fino alla morte!", "Marzo 2020", "Evento principale", "Absolute Carnage #4–5."),
        ],
    },
    {
        "id": "empyre", "name": "Empyre", "subtitle": "Avengers · Fantastici Quattro · Kree/Skrull",
        "accent": "#4aa7a3", "group": "modern2", "scope": "core-plus",
        "description": "Empyre con prologo e conseguenze visibili ma facoltativi. Il core obbligatorio è Empyre #1–6, distribuito nei Marvel Miniserie #236–239; #235 prepara la Guerra Kree/Skrull e #240 raccoglie gli aftermath.",
        "readingOrder": ["Road to Empyre: The Kree/Skrull War #1", *[f"Empyre #{n}" for n in range(1,7)], "Empyre: Aftermath Avengers #1", "Empyre: Fallout Fantastic Four #1"],
        "issues": [
            mmmi(235, "La Strada verso Empyre: La guerra Kree/Skrull", "Settembre 2020", "Prologo facoltativo", "Road to Empyre: The Kree/Skrull War #1.", required=False),
            mmmi(236, "Empyre 1: Invasione!", "Ottobre 2020", "Evento principale", "Empyre #1."),
            mmmi(237, "Empyre 2: L'ascesa del Messia Celestiale", "Ottobre 2020", "Evento principale", "Empyre #2–3."),
            mmmi(238, "Empyre 3: Tradimento a corte", "Novembre 2020", "Evento principale", "Empyre #4–5."),
            mmmi(239, "Empyre 4: Conflitto finale", "Dicembre 2020", "Evento principale", "Empyre #6 e conclusione del core."),
            mmmi(240, "Empyre 5: Conseguenze", "Dicembre 2020", "Epilogo facoltativo", "Empyre: Aftermath Avengers + Empyre: Fallout Fantastic Four.", required=False),
        ],
    },
    {
        "id": "king-in-black", "name": "King in Black", "subtitle": "Knull · Venom · 2020–2021",
        "accent": "#575061", "group": "modern2", "scope": "core",
        "description": "Core di King in Black #1–5 nei tre Marvel Miniserie italiani #244–246. I tie-in restano fuori dal conteggio obbligatorio.",
        "readingOrder": [f"King in Black #{n}" for n in range(1,6)],
        "issues": [
            mmmi(244, "King In Black 1: Regna l'oscurità", "Aprile 2021", "Evento principale", "King in Black #1."),
            mmmi(245, "King in Black 2: Acclamate il re!", "Maggio 2021", "Evento principale", "King in Black #2–3."),
            mmmi(246, "King In Black 3: Il gran finale", "Giugno 2021", "Evento principale", "King in Black #4–5."),
        ],
    },
    {
        "id": "blood-hunt", "name": "Blood Hunt", "subtitle": "Vampiri · Avengers · Doctor Strange · 2024",
        "accent": "#a53545", "group": "modern2", "scope": "core",
        "description": "Core di Blood Hunt nella prima edizione italiana Special Events #109–111. Comprende il prologo FCBD e Blood Hunt #1–5; i tie-in delle singole testate restano percorsi satelliti.",
        "readingOrder": ["Free Comic Book Day 2024: Blood Hunt", *[f"Blood Hunt #{n}" for n in range(1,6)]],
        "issues": [
            spee(109, "Blood Hunt 1", "Ottobre 2024", "FCBD 2024: Blood Hunt + Blood Hunt #1."),
            spee(110, "Blood Hunt 2", "Novembre 2024", "Blood Hunt #2–3."),
            spee(111, "Blood Hunt 3", "Dicembre 2024", "Blood Hunt #4–5 e conclusione."),
        ],
    },
]


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def required_rows(event):
    return [x for x in event["issues"] if x.get("required") is not False]


def build_routes() -> None:
    for event in EVENTS:
        req = required_rows(event)
        series = []
        seen = set()
        for issue in event["issues"]:
            sid = issue["seriesId"]
            if sid in seen: continue
            seen.add(sid)
            series.append({"id": sid, "name": issue["series"], "publisher": issue["publisher"], "range": "edizione italiana di riferimento"})
        payload = {
            "id": event["id"], "name": event["name"], "subtitle": event["subtitle"], "accent": event["accent"],
            "start": f"{req[0]['name']} — {req[0]['date']}", "end": f"{req[-1]['name']} — {req[-1]['date']}",
            "description": event["description"], "timelineMode": True, "eventScope": event["scope"],
            "readingOrderSource": "Marvel event main series / Italian first-publication audit",
            "readingOrder": event["readingOrder"], "series": series, "archives": [],
            "totalRequired": len(req), "availableTotal": len(req), "issues": event["issues"],
        }
        write_json(DATA / "characters" / f"{event['id']}.json", payload)


def write_logos() -> None:
    marks = {"secret-wars-1984":"SW84","infinity-gauntlet":"IG","infinity":"∞","secret-wars-2015":"SW",
             "civil-war-ii":"CW2","secret-empire":"SE","war-of-the-realms":"WotR","absolute-carnage":"AC",
             "empyre":"E","king-in-black":"KiB","blood-hunt":"BH"}
    out = ROOT / "assets" / "heroes"
    for event in EVENTS:
        mark = marks[event["id"]]
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect x="12" y="12" width="104" height="104" rx="24" fill="#111720" stroke="{event["accent"]}" stroke-width="6"/><text x="64" y="73" text-anchor="middle" font-family="Arial,sans-serif" font-size="26" font-weight="800" fill="{event["accent"]}">{mark}</text></svg>'
        (out / f"{event['id']}.svg").write_text(svg, encoding="utf-8")


def update_manifest() -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    ids = {e["id"] for e in EVENTS}
    rows = [x for x in manifest.get("characters", []) if x.get("id") not in ids]
    insert_at = next((i for i,x in enumerate(rows) if str(x.get("id","")).startswith("ultimate-")), len(rows))
    entries=[]
    for event in EVENTS:
        req=required_rows(event)
        entries.append({"id":event["id"],"name":event["name"],"subtitle":event["subtitle"],"type":"event","universe":"Terra-616",
                        "primaryHub":"events","hubs":["events"],"accent":event["accent"],"logo":f"assets/heroes/{event['id']}.svg",
                        "data":f"data/characters/{event['id']}.json","start":f"{req[0]['name']} — {req[0]['date']}",
                        "end":f"{req[-1]['name']} — {req[-1]['date']}","totalRequired":len(req)})
    rows[insert_at:insert_at]=entries
    manifest["characters"]=rows
    write_json(path,manifest)


def update_hubs() -> None:
    path=DATA/"hubs.json"
    payload=json.loads(path.read_text(encoding="utf-8"))
    for hub in payload.get("hubs",[]):
        if hub.get("id")!="events": continue
        hub.pop("status",None)
        hub["groups"]=[
            {"id":"classic","label":"Eventi classici","paths":["secret-wars-1984","infinity-gauntlet"]},
            {"id":"modern-core-1","label":"Era moderna — 2005–2012","paths":["house-of-m","civil-war","secret-invasion","siege","fear-itself","avengers-vs-xmen"]},
            {"id":"modern-core-2","label":"Era moderna — 2013–2024","paths":["infinity","secret-wars-2015","civil-war-ii","secret-empire","war-of-the-realms","absolute-carnage","empyre","king-in-black","blood-hunt"]},
            {"id":"complete","label":"Eventi completi auditati","paths":["judgment-day"]},
        ]
        hub["featuredPath"]="civil-war"
    write_json(path,payload)


def update_curated_editions() -> None:
    path=DATA/"curated-editions.json"
    curated=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version":1,"editions":[]}
    generated=json.loads((DATA/"editions.json").read_text(encoding="utf-8"))
    g={x["id"]:x for x in generated.get("editions",[])}
    existing={x["id"]:x for x in curated.get("editions",[])}
    mappings={
        "MAROMNIB:46":("secret-wars-1984",["SPE_GS1:1","SPE_GS1:2","SPE_GS1:3"],"Marvel Super Heroes Secret Wars #1–12"),
        "MARVELMUST:72":("secret-wars-1984",["SPE_GS1:1","SPE_GS1:2","SPE_GS1:3"],"Marvel Super Heroes Secret Wars #1–12"),
        "MAROMNIB:71":("infinity-gauntlet",["MCP_M:1","MCP_M:2","MCP_M:3","MCP_M:4/5","MCP_M:6"],"The Infinity Gauntlet #1–6"),
        "MARVELMUST:12":("infinity-gauntlet",["MCP_M:1","MCP_M:2","MCP_M:3","MCP_M:4/5","MCP_M:6"],"The Infinity Gauntlet #1–6"),
        "MAROMNIB:45":("infinity",[f"MMMI:{n}" for n in range(145,151)],"Infinity #1–6"),
        "MVNWCOL_P:31":("infinity",[f"MMMI:{n}" for n in range(145,151)],"Infinity #1–6"),
        "MAROMNIB:69":("secret-wars-2015",[f"MMMI:{n}" for n in range(164,173)],"Secret Wars (2015) #1–9"),
        "MVNWCOL_P:133":("secret-wars-2015",[f"MMMI:{n}" for n in range(164,173)],"Secret Wars (2015) #1–9"),
        "MARVELMUST:64":("secret-wars-2015",[f"MMMI:{n}" for n in range(164,173)],"Secret Wars (2015) #1–9"),
        "MAROMNIB:80":("civil-war-ii",[f"MMMI:{n}" for n in range(175,184)],"Civil War II #0–8"),
        "MARVELMUST:90":("civil-war-ii",[f"MMMI:{n}" for n in range(175,184)],"Civil War II #0–8"),
        "MAROMNIB:98":("secret-empire",[f"MMMI:{n}" for n in range(188,200)],"Secret Empire #0–10 + Omega"),
        "MVNWCOL_P:408":("war-of-the-realms",[f"MMMI:{n}" for n in range(222,226)],"War of the Realms #1–6"),
        "MVNWCOL_P:336":("absolute-carnage",[f"MMMI:{n}" for n in range(227,230)],"Absolute Carnage #1–5"),
        "MAROMNIB:168":("empyre",[f"MMMI:{n}" for n in range(235,241)],"Road to Empyre + Empyre #1–6 + aftermath"),
        "MVNWCOL_P:458":("empyre",[f"MMMI:{n}" for n in range(236,241)],"Empyre #1–6 + aftermath"),
        "MVNWCOL_P:394":("king-in-black",[f"MMMI:{n}" for n in range(244,247)],"King in Black #1–5"),
        "MVNWCOL_P:740":("blood-hunt",[f"SPEE_M:{n}" for n in range(109,112)],"FCBD 2024 + Blood Hunt #1–5"),
    }
    for eid,(route,ids,label) in mappings.items():
        base=dict(g.get(eid,{})); base.update(existing.get(eid,{}))
        if not base: raise RuntimeError(f"Edizione raccolta non trovata: {eid}")
        cov=[c for c in base.get("coverage",[]) if c.get("path")!=route]
        cov.append({"path":route,"issueIds":ids,"label":label})
        base["coverage"]=cov; base["coverageSource"]="curated:event-core"
        existing[eid]=base
    curated["version"]=max(3,int(curated.get("version",1))+1)
    curated["editions"]=sorted(existing.values(),key=lambda x:x.get("id",""))
    write_json(path,curated)


def patch_edition_builder() -> None:
    path=ROOT/"scripts"/"build_editions_catalog.py"
    text=path.read_text(encoding="utf-8")
    anchor='    "avengers-vs-xmen": ["avengers vs x-men", "avengers vs. x-men", "avx"],\n'
    additions=(
        '    "infinity": ["infinity"],\n'
        '    "civil-war-ii": ["civil war ii", "civil war 2"],\n'
        '    "secret-empire": ["secret empire"],\n'
        '    "war-of-the-realms": ["war of the realms", "guerra dei regni"],\n'
        '    "absolute-carnage": ["absolute carnage"],\n'
        '    "empyre": ["empyre"],\n'
        '    "king-in-black": ["king in black"],\n'
        '    "blood-hunt": ["blood hunt"],\n'
        '    "infinity-gauntlet": ["infinity gauntlet", "guanto dell\\\'infinito"],\n'
    )
    if '"empyre": ["empyre"]' not in text:
        if anchor not in text: raise RuntimeError("Anchor PATH_ALIASES non trovato")
        text=text.replace(anchor,anchor+additions)
    old='    if "civil war ii" in text or "civil war 2" in text:\n        candidates.discard("civil-war")\n'
    new=old+'    if any(x in text for x in ("infinity gauntlet", "guanto dell\\\'infinito", "infinity wars", "infinity countdown")):\n        candidates.discard("infinity")\n'
    if 'candidates.discard("infinity")' not in text:
        if old not in text: raise RuntimeError("Anchor collision rules non trovato")
        text=text.replace(old,new)
    path.write_text(text,encoding="utf-8")


def patch_verifier() -> None:
    path=ROOT/"scripts"/"verify-data.mjs"
    text=path.read_text(encoding="utf-8")
    text=text.replace('assert.equal(manifest.version, 15, "Il manifest deve usare la versione cache v15");',
                      'assert.equal(manifest.version, 16, "Il manifest deve usare la versione cache v16");')
    path.write_text(text,encoding="utf-8")


def main() -> None:
    build_routes(); write_logos(); update_manifest(); update_hubs(); update_curated_editions(); patch_edition_builder(); patch_verifier()
    print("Second event wave:", ", ".join(e["name"] for e in EVENTS))
    print("Manifest version:",MANIFEST_VERSION)
    empyre=next(e for e in EVENTS if e["id"]=="empyre")
    print("Empyre:",len(empyre["issues"]),"pubblicazioni visibili,",len(required_rows(empyre)),"core obbligatorie")


if __name__ == "__main__":
    main()
