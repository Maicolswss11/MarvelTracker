#!/usr/bin/env python3
"""Build the curated Italian physical checklist for A.X.E.: Judgment Day."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "judgment-day"
MANIFEST_VERSION = 14


def issue(issue_id, n, name, title, date, series_id, series, code, era, instruction):
    return {
        "id": issue_id,
        "n": n,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": series_id,
        "series": series,
        "cover": f"https://www.comicsbox.it/cover/{code}.jpg",
        "url": f"https://www.comicsbox.it/albo/{code}",
        "era": era,
        "instruction": instruction,
        "required": True,
        "future": False,
    }


ISSUES = [
    issue("MMMI:262", 262, "Marvel Miniserie #262", "A.X.E. - Judgment Day 1", "Novembre 2022", "MMMI", "Marvel Miniserie", "MMMI_262", "Prologo", "Leggi FCBD 2022: Avengers/X-Men e A.X.E.: Eve of Judgment. Il FCBD è ristampato anche nel cartonato principale: qui va letto una sola volta."),
    issue("MVNWCOL_P:572", 572, "Marvel Collection (II) #572", "A.X.E. Judgment Day", "Maggio 2024", "MVNWCOL_P", "Marvel Collection II", "MVNWCOL_P_572", "Evento principale", "Cartonato di riferimento. Usalo più volte seguendo l'ordine USA salvato nel percorso: Judgment Day #1-3; poi #4-5; A.X.E.: Avengers; A.X.E.: X-Men; A.X.E.: Eternals; infine Judgment Day #6. Salta il FCBD, già letto nel #262."),
    issue("AXEMOMUTA:1", 1, "A.X.E. Judgment Day: Morte ai Mutanti", "Morte ai Mutanti", "Marzo 2023", "AXEMOMUTA", "A.X.E. Judgment Day: Morte ai Mutanti", "AXEMOMUTA_001", "Companion essenziali", "Usalo in più punti: Death to the Mutants #1, poi #2, poi #3; quindi A.X.E.: Iron Fist e A.X.E.: Starfox. A.X.E.: Avengers/X-Men/Eternals sono duplicati del cartonato #572 e non vanno riletti."),
    issue("IMMXMENITA:6", 6, "Immortal X-Men #6", "A.X.E. Judgment Day", "Dicembre 2022", "IMMXMENITA", "Immortal X-Men", "IMMXMENITA_006", "Krakoa e Arakko", "Contiene Immortal X-Men #5 e X-Men Red #5. Leggi Immortal #5 dopo Death to the Mutants #1; torna a X-Men Red #5 dopo X-Men #14."),
    issue("WOL_PM:431", 431, "Wolverine #431", "Wolverine 27 (A.X.E. Judgment Day)", "Dicembre 2022", "WOL_PM", "Wolverine", "WOL_PM_431", "Giudizi personali", "Contiene Wolverine (2020) #24. Leggilo dopo Immortal X-Men #5."),
    issue("XFORCEIT:32", 32, "X-Force #32", "X-Force 28 (A.X.E. Judgment Day)", "Dicembre 2022", "XFORCEIT", "X-Force", "XFORCEIT_032", "Krakoa e Arakko", "Contiene X-Force (2020) #30. Leggilo dopo Wolverine #24."),
    issue("XFORCEIT:33", 33, "X-Force #33", "X-Force 29 (A.X.E. Judgment Day)", "Gennaio 2023", "XFORCEIT", "X-Force", "XFORCEIT_033", "Krakoa e Arakko", "Contiene X-Force (2020) #31. Prosegui subito dopo X-Force #30."),
    issue("XM_SM:396", 396, "Gli Incredibili X-Men #396", "X-Men 15 (A.X.E. Judgment Day)", "Dicembre 2022", "XM_SM", "Gli Incredibili X-Men", "XM_SM_396", "Krakoa e Arakko", "Albo già condiviso con il percorso X-Men. Contiene X-Men (2021) #13; leggilo dopo X-Force #31."),
    issue("XM_SM:397", 397, "Gli Incredibili X-Men #397", "X-Men 16 (A.X.E. Judgment Day)", "Gennaio 2023", "XM_SM", "Gli Incredibili X-Men", "XM_SM_397", "Krakoa e Arakko", "Albo già condiviso con il percorso X-Men. Contiene X-Men (2021) #14; leggilo dopo X-Men #13."),
    issue("IMMXMENITA:7", 7, "Immortal X-Men #7", "A.X.E. Judgment Day", "Gennaio 2023", "IMMXMENITA", "Immortal X-Men", "IMMXMENITA_007", "Krakoa e Arakko", "Contiene Immortal X-Men #6 e X-Men Red #6. Nell'ordine completo vengono dopo Fantastic Four #47: Immortal #6, poi X-Men Red #6."),
    issue("MVNWCOL_P:491", 491, "Marvel Collection (II) #491", "Captain Marvel 9: La Vendetta della Covata", "Luglio 2023", "MVNWCOL_P", "Marvel Collection II", "MVNWCOL_P_491", "Giudizi personali", "Volume già condivisibile con Captain Marvel. Per A.X.E. leggi soltanto Captain Marvel (2019) #42; gli altri capitoli del volume appartengono alla saga della Covata."),
    issue("F4_SM:433", 433, "Fantastici Quattro #433", "Fantastici Quattro 48: Assalto al Baxter Building", "Dicembre 2022", "F4_SM", "Fantastici Quattro", "F4_SM_433", "Giudizi personali", "Albo già condiviso con i Fantastici Quattro. Contiene Fantastic Four (2018) #47, tie-in A.X.E."),
    issue("WOL_PM:432", 432, "Wolverine #432", "Wolverine 28 (A.X.E. Judgment Day)", "Gennaio 2023", "WOL_PM", "Wolverine", "WOL_PM_432", "Giudizi personali", "Contiene Wolverine (2020) #25, seconda parte del tie-in personale di Logan."),
    issue("MARAUDIIIT:2", 2, "Marauders (II) #2", "Spettri del Passato", "Giugno 2023", "MARAUDIIIT", "Marauders (II)", "MARAUDIIIT_002", "Krakoa e Arakko", "Per A.X.E. leggi Marauders (2022) #6, il primo capitolo USA contenuto in questo volume. I successivi #7-12 proseguono Marauders fuori dall'evento."),
    issue("AVENGERS_M:154", 154, "Avengers #154", "Avengers 50: Nel cuore di Occhio di Falco! (A.X.E. Judgment Day)", "Dicembre 2022", "AVENGERS_M", "Avengers", "AVENGERS_M_154", "Giudizi personali", "Albo già condiviso con il percorso Vendicatori. Per A.X.E. leggi Avengers (2018) #60; l'altro materiale dell'albo resta nella serie Avengers."),
    issue("XFORCEIT:34", 34, "X-Force #34", "X-Force 30 (A.X.E. Judgment Day)", "Febbraio 2023", "XFORCEIT", "X-Force", "XFORCEIT_034", "Krakoa e Arakko", "Contiene X-Force (2020) #32. Leggilo dopo Avengers #60."),
    issue("SPIDER_MAIN:809", 809, "Amazing Spider-Man (2022) #809", "Amazing Spider-Man 9: Thwip+Snikt! (A.X.E. Judgment Day)", "Dicembre 2022", "ASM_IT_2022", "Amazing Spider-Man (2022)", "UR_SM_809", "Giudizi personali", "Albo già condiviso con Spider-Man. Contiene sia Amazing Spider-Man (2022) #9 (Gala Infernale) sia #10: per A.X.E. leggi soltanto il #10, Il giorno in cui tornò Gwen Stacy."),
    issue("F4_SM:434", 434, "Fantastici Quattro #434", "Fantastici Quattro 49: Donne invisibili", "Gennaio 2023", "F4_SM", "Fantastici Quattro", "F4_SM_434", "Giudizi personali", "Albo già condiviso con i Fantastici Quattro. Contiene Fantastic Four (2018) #48, seconda e ultima parte del tie-in A.X.E."),
    issue("IMMXMENITA:8", 8, "Immortal X-Men #8", "A.X.E. Judgment Day", "Febbraio 2023", "IMMXMENITA", "Immortal X-Men", "IMMXMENITA_008", "Krakoa e Arakko", "Contiene Immortal X-Men #7 e X-Men Red #7. Nell'ordine ufficiale: Immortal #7, poi X-Force #33, poi X-Men Red #7."),
    issue("XFORCEIT:35", 35, "X-Force #35", "X-Force 31 (A.X.E. Judgment Day)", "Marzo 2023", "XFORCEIT", "X-Force", "XFORCEIT_035", "Krakoa e Arakko", "Contiene X-Force (2020) #33. Leggilo tra Immortal X-Men #7 e X-Men Red #7."),
    issue("LEGXITA:2", 2, "Legion of X #2", "Legami di Famiglia", "Maggio 2023", "LEGXITA", "Legion of X", "LEGXITA_002", "Krakoa e Arakko", "Per A.X.E. leggi Legion of X #6, il primo capitolo USA contenuto nel volume. Va letto dopo A.X.E.: Eternals e prima di Judgment Day #6."),
    issue("MMMI:266", 266, "Marvel Miniserie #266", "A.X.E. - Judgment Day 5", "Marzo 2023", "MMMI", "Marvel Miniserie", "MMMI_266", "Epilogo", "Se usi il cartonato #572, Judgment Day #6 è già coperto: in questo albo leggi solo A.X.E.: Judgment Day Omega, epilogo finale dell'evento."),
]

READING_ORDER = [
    "Free Comic Book Day 2022: Avengers/X-Men #1",
    "A.X.E.: Eve of Judgment #1",
    "A.X.E.: Judgment Day #1",
    "A.X.E.: Judgment Day #2",
    "A.X.E.: Judgment Day #3",
    "A.X.E.: Death to the Mutants #1",
    "Immortal X-Men #5",
    "Wolverine #24",
    "X-Force #30",
    "X-Force #31",
    "X-Men #13",
    "X-Men #14",
    "X-Men Red #5",
    "A.X.E.: Judgment Day #4",
    "A.X.E.: Judgment Day #5",
    "A.X.E.: Death to the Mutants #2",
    "A.X.E.: Avengers #1",
    "Captain Marvel #42",
    "Fantastic Four #47",
    "Immortal X-Men #6",
    "X-Men Red #6",
    "Wolverine #25",
    "Marauders #6",
    "Avengers #60",
    "X-Force #32",
    "Amazing Spider-Man #10",
    "A.X.E.: Death to the Mutants #3",
    "A.X.E.: X-Men #1",
    "A.X.E.: Iron Fist #1",
    "A.X.E.: Starfox #1",
    "Fantastic Four #48",
    "Immortal X-Men #7",
    "X-Force #33",
    "X-Men Red #7",
    "A.X.E.: Eternals #1",
    "Legion of X #6",
    "A.X.E.: Judgment Day #6",
    "A.X.E.: Judgment Day Omega #1",
]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build_route() -> None:
    payload = {
        "id": PATH_ID,
        "name": "A.X.E.: Judgment Day",
        "subtitle": "Avengers · X-Men · Eterni — evento completo",
        "accent": "#f59b45",
        "start": "Marvel Miniserie #262 — Novembre 2022 · FCBD + Eve of Judgment",
        "end": "Marvel Miniserie #266 — Marzo 2023 · Judgment Day Omega",
        "description": "Checklist fisica italiana completa dell'evento A.X.E.: Judgment Day. La selezione privilegia il cartonato Marvel Collection #572 per la miniserie principale e usa Morte ai Mutanti per i companion esclusivi, evitando di richiedere le vecchie uscite Marvel Miniserie #263-265 già ristampate. I tie-in sono mappati sulle prime edizioni italiane o su raccolte che li contengono. Alcuni volumi accorpano più capitoli USA: segui le istruzioni e l'ordine narrativo ufficiale salvato nel percorso.",
        "timelineMode": True,
        "readingOrderSource": "Marvel official A.X.E.: Judgment Day suggested reading order",
        "readingOrder": READING_ORDER,
        "series": [
            {"id": "AXE-CORE", "name": "A.X.E.: Judgment Day — core", "publisher": "Panini Comics", "range": "prologo, main event, companion, Omega", "years": "2022–2024"},
            {"id": "AXE-TIEINS", "name": "A.X.E.: Judgment Day — tie-in", "publisher": "Panini Comics", "range": "X-Men, X-Force, Wolverine, Avengers, Spider-Man, Fantastic Four e altri", "years": "2022–2023"},
        ],
        "archives": [],
        "totalRequired": len(ISSUES),
        "availableTotal": len(ISSUES),
        "issues": ISSUES,
    }
    write_json(DATA / "characters" / f"{PATH_ID}.json", payload)


def update_manifest() -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    entry = {
        "id": PATH_ID,
        "name": "A.X.E.: Judgment Day",
        "subtitle": "Avengers · X-Men · Eterni — evento completo",
        "type": "event",
        "universe": "Terra-616",
        "primaryHub": "events",
        "hubs": ["events"],
        "accent": "#f59b45",
        "logo": "assets/heroes/judgment-day.svg",
        "data": "data/characters/judgment-day.json",
        "start": "Marvel Miniserie #262 — Novembre 2022 · FCBD + Eve of Judgment",
        "end": "Marvel Miniserie #266 — Marzo 2023 · Judgment Day Omega",
        "totalRequired": len(ISSUES),
    }
    rows = [row for row in manifest.get("characters", []) if row.get("id") != PATH_ID]
    insert_at = next((i for i, row in enumerate(rows) if str(row.get("universe", "")).startswith("Ultimate")), len(rows))
    rows.insert(insert_at, entry)
    manifest["characters"] = rows
    write_json(path, manifest)


def update_hub() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for hub in payload.get("hubs", []):
        if hub.get("id") != "events":
            continue
        hub.pop("status", None)
        hub["featuredPath"] = PATH_ID
        groups = hub.setdefault("groups", [])
        group = next((g for g in groups if g.get("id") == "events-main"), None)
        if group is None:
            group = {"id": "events-main", "label": "Eventi completi", "paths": []}
            groups.insert(0, group)
        if PATH_ID not in group["paths"]:
            group["paths"].insert(0, PATH_ID)
        break
    write_json(path, payload)


def write_logo() -> None:
    target = ROOT / "assets" / "heroes" / "judgment-day.svg"
    target.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 280"><rect width="640" height="280" rx="34" fill="#111319"/><path d="M54 222 160 50h72l104 172h-78l-16-31H148l-17 31H54Zm122-90h39l-19-40-20 40Z" fill="#f59b45"/><text x="355" y="130" text-anchor="middle" fill="#fff" font-family="Arial,Helvetica,sans-serif" font-size="64" font-weight="900">A.X.E.</text><text x="390" y="192" text-anchor="middle" fill="#f59b45" font-family="Arial,Helvetica,sans-serif" font-size="34" font-weight="800">JUDGMENT DAY</text></svg>''', encoding="utf-8")


def patch_maintenance() -> None:
    verify = ROOT / "scripts" / "verify-data.mjs"
    text = verify.read_text(encoding="utf-8")
    text = text.replace("manifest.version, 13", f"manifest.version, {MANIFEST_VERSION}").replace("cache v13", f"cache v{MANIFEST_VERSION}")
    verify.write_text(text, encoding="utf-8")

    editions = ROOT / "scripts" / "build_editions_catalog.py"
    text = editions.read_text(encoding="utf-8")
    marker = '    "doctor-strange": ["doctor strange", "dottor strange", "dr. strange", "dr strange"],\n'
    addition = marker + '    "judgment-day": ["a.x.e. judgment day", "a.x.e.", "judgment day"],\n'
    if '"judgment-day":' not in text and marker in text:
        text = text.replace(marker, addition)
    old = '    "extremis", "ragnarok", "spider-verse", "absolute carnage", "king in black",\n'
    new = '    "extremis", "ragnarok", "spider-verse", "absolute carnage", "king in black", "a.x.e.", "judgment day",\n'
    if old in text:
        text = text.replace(old, new)
    editions.write_text(text, encoding="utf-8")


def main() -> None:
    build_route()
    update_manifest()
    update_hub()
    write_logo()
    patch_maintenance()
    print(f"A.X.E.: Judgment Day: {len(ISSUES)} copie fisiche italiane, {len(READING_ORDER)} capitoli in ordine narrativo")


if __name__ == "__main__":
    main()
