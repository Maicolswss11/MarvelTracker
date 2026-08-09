#!/usr/bin/env python3
"""Upgrade the Civil War event route to the complete official reading order.

The route stores one node per Italian physical publication, while `readingOrder`
keeps Marvel's complete US chapter sequence. Collected editions can therefore be
reused several times without pretending that the reader owns the original
single issues they replace.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_VERSION = 17


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def row(issue_id: str, n: int, name: str, title: str, date: str, series_id: str,
        series: str, publisher: str, cover_code: str, era: str, instruction: str):
    return {
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
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
    }


READING_ORDER = [
    "Amazing Spider-Man (1999) #529",
    "Amazing Spider-Man (1999) #530",
    "Amazing Spider-Man (1999) #531",
    "Fantastic Four (1998) #536",
    "Fantastic Four (1998) #537",
    "New Avengers: Illuminati (2006) #1",
    "Civil War (2006) #1",
    "She-Hulk (2005) #8",
    "Wolverine (2003) #42",
    "Amazing Spider-Man (1999) #532",
    "Civil War: Front Line (2006) #1",
    "Civil War (2006) #2",
    "Thunderbolts (2006) #103",
    "Civil War: Front Line (2006) #2",
    "X-Factor (2006) #8",
    "New Avengers (2004) #21",
    "Wolverine (2003) #43",
    "Amazing Spider-Man (1999) #533",
    "Fantastic Four (1998) #538",
    "Civil War: Front Line (2006) #3",
    "Thunderbolts (2006) #104",
    "Civil War: X-Men (2006) #1",
    "Civil War (2006) #3",
    "Cable & Deadpool (2004) #30",
    "Civil War: Young Avengers & Runaways (2006) #1",
    "Civil War: Front Line (2006) #4",
    "X-Factor (2006) #9",
    "New Avengers (2004) #22",
    "Wolverine (2003) #44",
    "Amazing Spider-Man (1999) #534",
    "Fantastic Four (1998) #539",
    "Civil War: Front Line (2006) #5",
    "Ms. Marvel (2006) #6",
    "Civil War: X-Men (2006) #2",
    "Heroes for Hire (2006) #1",
    "New Avengers (2004) #23",
    "Wolverine (2003) #45",
    "Civil War: Young Avengers & Runaways (2006) #2",
    "Cable & Deadpool (2004) #31",
    "Ms. Marvel (2006) #7",
    "Civil War: X-Men (2006) #3",
    "Civil War (2006) #4",
    "Wolverine (2003) #46",
    "Heroes for Hire (2006) #2",
    "Civil War: Young Avengers & Runaways (2006) #3",
    "Civil War: Front Line (2006) #6",
    "Captain America (2004) #22",
    "Cable & Deadpool (2004) #32",
    "Amazing Spider-Man (1999) #535",
    "Civil War: Choosing Sides (2006) #1",
    "Fantastic Four (1998) #540",
    "Civil War: Front Line (2006) #7",
    "Civil War: X-Men (2006) #4",
    "Ms. Marvel (2006) #8",
    "Wolverine (2003) #47",
    "Heroes for Hire (2006) #3",
    "Captain America (2004) #23",
    "New Avengers (2004) #24",
    "Civil War (2006) #5",
    "Civil War: Young Avengers & Runaways (2006) #4",
    "Invincible Iron Man (2005) #13",
    "New Avengers (2004) #25",
    "Punisher War Journal (2006) #1",
    "Civil War: Front Line (2006) #8",
    "Amazing Spider-Man (1999) #536",
    "Black Panther (2005) #22",
    "Captain America (2004) #24",
    "Civil War: War Crimes (2007) #1",
    "Civil War: Front Line (2006) #9",
    "Invincible Iron Man (2005) #14",
    "Fantastic Four (1998) #541",
    "Black Panther (2005) #23",
    "Punisher War Journal (2006) #2",
    "Civil War (2006) #6",
    "Iron Man/Captain America: Casualties of War (2007) #1",
    "Civil War: Front Line (2006) #10",
    "Amazing Spider-Man (1999) #537",
    "Fantastic Four (1998) #542",
    "Civil War: The Return (2007) #1",
    "Punisher War Journal (2006) #3",
    "Black Panther (2005) #24",
    "Civil War (2006) #7",
    "Amazing Spider-Man (1999) #538",
    "Civil War: Front Line (2006) #11",
    "Black Panther (2005) #25",
    "Civil War: The Initiative (2007) #1",
    "Invincible Iron Man (2005) #15",
    "Mighty Avengers (2007) #1",
    "Captain America (2004) #25",
    "Civil War: The Confession (2007) #1",
    "Fallen Son: The Death of Captain America (2007) #1",
    "Fallen Son: The Death of Captain America (2007) #2",
    "Fallen Son: The Death of Captain America (2007) #3",
    "Fallen Son: The Death of Captain America (2007) #4",
    "Fallen Son: The Death of Captain America (2007) #5",
    "Fantastic Four (1998) #543",
    "Fantastic Four (1998) #544",
    "Avengers: The Initiative (2007) #1",
]


def main():
    civil_path = DATA / "characters" / "civil-war.json"
    current = read_json(civil_path)
    core = {issue["id"]: issue for issue in current["issues"]}
    expected_core = [f"MMMI:{n}" for n in range(76, 83)]
    if not all(issue_id in core for issue_id in expected_core):
        raise RuntimeError("Civil War core #76–82 non trovato")

    def core_issue(n: int, instruction: str):
        issue = dict(core[f"MMMI:{n}"])
        issue["instruction"] = instruction
        issue["era"] = "Evento principale"
        issue["required"] = True
        issue["skip"] = False
        issue["future"] = False
        return issue

    issues = [
        row("MAROMNIB:56", 56, "Marvel Omnibus #56", "Civil War - Spider-Man", "Aprile 2016",
            "MAROMNIB", "Marvel Omnibus", "Panini Comics", "MAROMNIB_056", "Preludio / Spider-Man",
            "Volume da riaprire più volte. Comincia con Amazing Spider-Man #529–531; poi inserisci #532–538 esattamente nei punti indicati dal reading order. Non leggerlo tutto in blocco."),
        row("MAROMNIB:57", 57, "Marvel Omnibus #57", "Civil War - Le conseguenze", "Aprile 2016",
            "MAROMNIB", "Marvel Omnibus", "Panini Comics", "MAROMNIB_057", "Preludio e conseguenze",
            "All'inizio leggi Fantastic Four #536–537 e New Avengers: Illuminati. Torna al volume dopo il core per The Return, Iron Man #15, Captain America #25, The Confession, The Initiative e Fallen Son #1–5. Segui il reading order, non l'ordine del volume."),
        core_issue(76, "Leggi Civil War #1. Il materiale Front Line presente nell'albo va seguito secondo il reading order completo e non anticipato."),
        row("F4_SM:270", 270, "Fantastici Quattro #270", "She-Hulk #8 — Civil War", "Aprile 2007",
            "F4_SM", "Fantastici Quattro", "Panini Comics", "F4_SM_270", "Tie-in",
            "Per Civil War leggi She-Hulk (2005) #8, subito dopo Civil War #1."),
        row("MAROMNIB:55", 55, "Marvel Omnibus #55", "Civil War - Universo Marvel", "Aprile 2016",
            "MAROMNIB", "Marvel Omnibus", "Panini Comics", "MAROMNIB_055", "Tie-in",
            "Volume da riaprire in molti punti: Wolverine #42–48, X-Factor #8–9, Civil War: X-Men #1–4, Fantastic Four #538–543 e Punisher War Journal #1–3. Leggi ogni capitolo solo quando compare nel reading order."),
        row("MAR_MIX:66", 66, "Marvel Mix #66", "Civil War Special 1: Prima pagina", "Giugno 2007",
            "MAR_MIX", "Marvel Mix", "Panini Comics", "MAR_MIX_066", "Front Line / speciali",
            "Prima parte italiana del materiale Civil War: Front Line. Usa il volume per i capitoli Front Line iniziali nei rispettivi punti del reading order; non leggere in anticipo le sezioni successive."),
        core_issue(77, "Leggi Civil War #2; poi continua con i tie-in nell'ordine ufficiale prima di passare al #3."),
        row("MARMONED:9", 9, "Marvel Monster Edition #9", "Civil War: Disobbedienza civile", "Ottobre 2007",
            "MARMONED", "Marvel Monster Edition", "Panini Comics", "MARMONED_009", "Tie-in",
            "Usalo in più punti per Thunderbolts #103–104, Cable & Deadpool #30–32 e Heroes for Hire #1–3. Gli altri contenuti del volume non vanno letti fuori ordine."),
        row("MAROMNIB:54", 54, "Marvel Omnibus #54", "Civil War - Avengers", "Aprile 2016",
            "MAROMNIB", "Marvel Omnibus", "Panini Comics", "MAROMNIB_054", "Tie-in Avengers",
            "Volume da riaprire più volte: New Avengers #21–25, Captain America #22–24, Young Avengers & Runaways #1–4, Black Panther #22–25, Iron Man #13–14 e Casualties of War. Segui sempre il reading order completo."),
        row("THORVE_M:99", 99, "Thor #99", "Ms. Marvel — Civil War", "Giugno 2007",
            "THORVE_M", "Thor / Nuovi Vendicatori", "Panini Comics", "THORVE_M_099", "Tie-in Ms. Marvel",
            "Per il percorso Civil War usa il materiale di Ms. Marvel collegato all'evento secondo il reading order. Le storie Avengers eventualmente presenti possono duplicare il volume Civil War - Avengers."),
        core_issue(78, "Leggi Civil War #3; poi prosegui con Cable & Deadpool, Young Avengers/Runaways, Front Line e gli altri tie-in prima del #4."),
        row("THORVE_M:100", 100, "Thor #100", "Ms. Marvel — Civil War", "Luglio 2007",
            "THORVE_M", "Thor / Nuovi Vendicatori", "Panini Comics", "THORVE_M_100", "Tie-in Ms. Marvel",
            "Continua il blocco Ms. Marvel #6–8 soltanto nel punto indicato dal reading order. Ignora le eventuali storie già coperte dal Civil War - Avengers."),
        core_issue(79, "Leggi Civil War #4 e poi completa i tie-in intermedi prima di arrivare al quinto capitolo."),
        row("MAR_MIX:67", 67, "Marvel Mix #67", "Civil War Special 2: Fronti di guerra", "Agosto 2007",
            "MAR_MIX", "Marvel Mix", "Panini Comics", "MAR_MIX_067", "Front Line / speciali",
            "Secondo blocco Front Line. Insieme a Marvel Mix #68 copre anche la pubblicazione italiana suddivisa del materiale Civil War: Choosing Sides: leggi le singole storie solo quando richieste dal reading order."),
        row("THORVE_M:101", 101, "Thor #101", "Ms. Marvel — Civil War", "Agosto 2007",
            "THORVE_M", "Thor / Nuovi Vendicatori", "Panini Comics", "THORVE_M_101", "Tie-in Ms. Marvel",
            "Concludi il materiale Ms. Marvel #6–8 nel punto previsto dal reading order. Le storie duplicate di altre testate vanno saltate."),
        row("IM_VEN:88", 88, "Iron Man e i Vendicatori #88", "Civil War: War Crimes", "Settembre 2007",
            "IM_VEN", "Iron Man e i Vendicatori", "Panini Comics", "IM_VEN_088", "Tie-in Iron Man",
            "Per questo percorso leggi Civil War: War Crimes #1. Casualties of War è già coperto dal volume Civil War - Avengers e non va riletto."),
        core_issue(80, "Leggi Civil War #5; poi continua con Young Avengers/Runaways, Iron Man, New Avengers, Punisher, Front Line e gli altri tie-in."),
        row("MAR_MIX:68", 68, "Marvel Mix #68", "Civil War Special 3: La confessione", "Novembre 2007",
            "MAR_MIX", "Marvel Mix", "Panini Comics", "MAR_MIX_068", "Front Line / speciali",
            "Chiude il blocco Front Line e completa le parti italiane di Choosing Sides insieme al #67. Segui il reading order: non anticipare The Confession, che viene dopo Captain America #25."),
        core_issue(81, "Leggi Civil War #6, quindi Casualties of War, Front Line #10, Spider-Man, Fantastic Four, The Return, Punisher e Black Panther prima del finale."),
        core_issue(82, "Leggi Civil War #7. Dopo il finale continua: Spider-Man #538, Front Line #11, Black Panther #25 e tutte le conseguenze fino ad Avengers: The Initiative #1."),
        row("IM_VEN2:1", 1, "Iron Man e i potenti Vendicatori #1", "Mighty Avengers #1", "Aprile 2008",
            "IM_VEN2", "Iron Man e i potenti Vendicatori", "Panini Comics", "IM_VEN2_001", "Conseguenze",
            "Dopo Civil War: The Initiative e Iron Man #15, leggi Mighty Avengers #1 nel punto indicato dal reading order."),
        row("F4_SM:280", 280, "Fantastici Quattro #280", "Fantastic Four #544 — conseguenze", "Febbraio 2008",
            "F4_SM", "Fantastici Quattro", "Panini Comics", "F4_SM_280", "Conseguenze",
            "Dopo Fallen Son e Fantastic Four #543, leggi Fantastic Four #544."),
        row("MA_MEG:44", 44, "Marvel Mega #44", "Avengers: The Initiative #1", "Maggio 2008",
            "MA_MEG", "Marvel Mega", "Panini Comics", "MA_MEG_044", "Conseguenze",
            "Ultima tappa della reading list ufficiale: Avengers: The Initiative #1."),
    ]

    if len(READING_ORDER) != 98:
        raise RuntimeError(f"Reading order Civil War inatteso: {len(READING_ORDER)}")
    if len(issues) != 23 or len({issue['id'] for issue in issues}) != 23:
        raise RuntimeError("Checklist fisica Civil War deve avere 23 pubblicazioni uniche")

    upgraded = {
        "id": "civil-war",
        "name": "Civil War",
        "subtitle": "Iron Man · Capitan America — evento completo 2006–2008",
        "accent": "#bf4d45",
        "start": "Preludio Civil War — Amazing Spider-Man #529",
        "end": "Avengers: The Initiative #1 — conseguenze",
        "description": "Percorso completo di Civil War secondo la reading list ufficiale Marvel. I 98 capitoli USA sono ricondotti a 23 pubblicazioni fisiche italiane, privilegiando raccolte che accorpano molti tie-in e riusando gli stessi volumi in più punti. Le istruzioni indicano quando tornare in un Omnibus o speciale: non leggere automaticamente un volume intero in blocco.",
        "timelineMode": True,
        "eventScope": "complete",
        "readingOrderSource": "Marvel official Civil War complete event suggested reading order",
        "readingOrder": READING_ORDER,
        "series": [
            {"id": "CW-CORE", "name": "Civil War — serie principale", "publisher": "Marvel Italia / Panini Comics", "range": "Civil War #1–7", "years": "2007"},
            {"id": "CW-FRONTLINE", "name": "Civil War — Front Line e speciali", "publisher": "Marvel Italia / Panini Comics", "range": "Front Line #1–11, Choosing Sides, War Crimes", "years": "2007"},
            {"id": "CW-TIEINS", "name": "Civil War — tie-in", "publisher": "Panini Comics", "range": "Avengers, Spider-Man, X-Men, Fantastic Four e altri", "years": "2007–2016"},
            {"id": "CW-AFTERMATH", "name": "Civil War — conseguenze", "publisher": "Panini Comics", "range": "The Return, Initiative, Fallen Son e nuovi team", "years": "2007–2008"},
        ],
        "archives": [],
        "totalRequired": 23,
        "availableTotal": 23,
        "issues": issues,
    }
    write_json(civil_path, upgraded)

    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    manifest["version"] = MANIFEST_VERSION
    civil_meta = next(item for item in manifest["characters"] if item["id"] == "civil-war")
    civil_meta.update({
        "subtitle": upgraded["subtitle"],
        "start": upgraded["start"],
        "end": upgraded["end"],
        "totalRequired": upgraded["totalRequired"],
    })
    write_json(manifest_path, manifest)

    hubs_path = DATA / "hubs.json"
    hubs = read_json(hubs_path)
    event_hub = next(item for item in hubs["hubs"] if item["id"] == "events")
    modern = next(group for group in event_hub["groups"] if group["id"] == "modern-core-1")
    modern["paths"] = [path for path in modern["paths"] if path != "civil-war"]
    complete = next(group for group in event_hub["groups"] if group["id"] == "complete")
    complete["paths"] = [path for path in complete["paths"] if path != "civil-war"]
    complete["paths"].insert(0, "civil-war")
    write_json(hubs_path, hubs)

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    verify = verify.replace(
        'assert.equal(manifest.version, 16, "Il manifest deve usare la versione cache v16");',
        'assert.equal(manifest.version, 17, "Il manifest deve usare la versione cache v17");',
    )
    verify_path.write_text(verify, encoding="utf-8")

    app_path = ROOT / "js" / "app.js"
    app = app_path.read_text(encoding="utf-8")
    old = '  const item=state.collection?.[id]||{},physical=!!item.physical,digital=!!item.digital;'
    new = '  const item=state.collection?.[id]||{};\n  const editionPhysical=!!window.MarvelEditions?.get(id)&&!!window.MarvelEditions?.isOwned(state,id);\n  const physical=!!item.physical||editionPhysical,digital=!!item.digital;'
    if old in app:
        app = app.replace(old, new, 1)
    elif 'const editionPhysical=!!window.MarvelEditions?.get(id)' not in app:
        raise RuntimeError("Target status() app.js non trovato")
    app_path.write_text(app, encoding="utf-8")

    index_path = ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    if 'js/app.js?v=14' in index:
        index = index.replace('js/app.js?v=14', 'js/app.js?v=15', 1)
    elif 'js/app.js?v=15' not in index:
        raise RuntimeError("Versione cache app.js inattesa")
    index_path.write_text(index, encoding="utf-8")

    print(f"Civil War completo: {len(READING_ORDER)} capitoli USA -> {len(issues)} pubblicazioni italiane")


if __name__ == "__main__":
    main()
