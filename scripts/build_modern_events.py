#!/usr/bin/env python3
"""Build the first curated Terra-616 modern-event spine.

The canonical route uses first Italian Marvel Miniserie publications. Collected
editions remain separate physical objects and cover the same route through
curated edition mappings.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_VERSION = 15

MONTHS = {
    "Jan": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
    "May": "Maggio", "Jun": "Giugno", "Jul": "Luglio", "Aug": "Agosto",
    "Sep": "Settembre", "Oct": "Ottobre", "Nov": "Novembre", "Dec": "Dicembre",
}


def it_date(value: str) -> str:
    for en, it in MONTHS.items():
        value = value.replace(en, it)
    return value


def issue(n: int, title: str, date: str, era: str, instruction: str, *, required: bool = True):
    return {
        "id": f"MMMI:{n}",
        "n": n,
        "name": f"Marvel Miniserie #{n}",
        "title": title,
        "date": it_date(date),
        "seriesId": "MMMI",
        "series": "Marvel Miniserie",
        "publisher": "Marvel Italia / Panini Comics",
        "cover": f"https://www.comicsbox.it/cover/MMMI_{n:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/MMMI_{n:03d}",
        "era": era,
        "instruction": instruction,
        "required": required,
        "skip": not required,
        "future": False,
        "coverSource": "ComicsBox",
    }


EVENTS = [
    {
        "id": "house-of-m",
        "name": "House of M",
        "subtitle": "Avengers · X-Men · Scarlet Witch — core 2005",
        "accent": "#d84b74",
        "description": "Percorso core di House of M sulla prima edizione italiana Marvel Miniserie. Copre la miniserie principale USA #1–8. I numerosi tie-in restano fuori dal conteggio obbligatorio finché non vengono auditati uno per uno; Omnibus, Deluxe e Must-Have sono gestiti come edizioni fisiche alternative, non come possesso degli spillati.",
        "readingOrder": [f"House of M (2005) #{n}" for n in range(1, 9)],
        "issues": [
            issue(69, "House of M, pt 1", "Apr 2006", "Evento principale", "House of M #1–2."),
            issue(70, "House of M, pt 2", "May 2006", "Evento principale", "House of M #3–4."),
            issue(71, "House of M, pt 3", "Jun 2006", "Evento principale", "House of M #5–6."),
            issue(72, "House of M, pt 4", "Jul 2006", "Evento principale", "House of M #7–8 e conclusione del core."),
        ],
    },
    {
        "id": "civil-war",
        "name": "Civil War",
        "subtitle": "Iron Man · Capitan America — core 2006–2007",
        "accent": "#bf4d45",
        "description": "Percorso core di Civil War sulla prima edizione italiana Marvel Miniserie. La sequenza #76–82 contiene i sette capitoli della miniserie principale, affiancati nell'edizione italiana da materiale Front Line. I tie-in delle singole testate saranno espansi separatamente; le raccolte moderne coprono il core senza segnare gli spillati come posseduti.",
        "readingOrder": [f"Civil War (2006) #{n}" for n in range(1, 8)],
        "issues": [
            issue(n, f"Civil War, pt {n-75}", f"{['Mar','Apr','May','Jun','Jul','Aug','Sep'][n-76]} 2007", "Evento principale", f"Leggi Civil War #{n-75}; nell'albo italiano è presente anche materiale Front Line collegato all'evento.")
            for n in range(76, 83)
        ],
    },
    {
        "id": "secret-invasion",
        "name": "Secret Invasion",
        "subtitle": "Skrull · Avengers — core 2008–2009",
        "accent": "#6cad6f",
        "description": "Percorso core di Secret Invasion sulla prima edizione italiana Marvel Miniserie #93–100. Copre la miniserie principale USA #1–8 e il prologo presente nell'apertura italiana. New Avengers, Mighty Avengers e gli altri tie-in verranno aggiunti in un'espansione completa successiva.",
        "readingOrder": [f"Secret Invasion (2008) #{n}" for n in range(1, 9)],
        "issues": [
            issue(n, f"Secret Invasion, pt {n-92}", f"{['Feb','Feb','Apr','May','Jun','Jul','Aug','Sep'][n-93]} 2009", "Evento principale", f"Leggi Secret Invasion #{n-92}; segui l'albo italiano in ordine numerico.")
            for n in range(93, 101)
        ],
    },
    {
        "id": "siege",
        "name": "Assedio",
        "subtitle": "Dark Reign · Asgard — core 2010",
        "accent": "#7786b8",
        "description": "Percorso core di Siege/Assedio: La Cabala e Origins of Siege come prologo, quindi Siege #1–4. È la chiusura del Dark Reign. I tie-in di Dark Avengers, New Avengers, Thor e Initiative saranno trattati come espansione dell'evento, non sono necessari per completare questo core.",
        "readingOrder": ["Origins of Siege", "Siege: The Cabal", *[f"Siege (2010) #{n}" for n in range(1, 5)]],
        "issues": [
            issue(107, "Assedio 0: La Cabala", "Sep 2010", "Prologo", "Leggi Origins of Siege e Siege: The Cabal."),
            issue(108, "Assedio, pt 1", "Oct 2010", "Evento principale", "Siege #1."),
            issue(109, "Assedio, pt 2", "Nov 2010", "Evento principale", "Siege #2."),
            issue(110, "Assedio, pt 3", "Dec 2010", "Evento principale", "Siege #3."),
            issue(111, "Assedio, pt 4", "Jan 2011", "Evento principale", "Siege #4 e conclusione del core."),
        ],
    },
    {
        "id": "fear-itself",
        "name": "Fear Itself",
        "subtitle": "Il Serpente · Thor · Avengers — core 2011",
        "accent": "#8d684c",
        "description": "Percorso core di Fear Itself: Book of the Skull come prologo e Fear Itself #1–7. I tie-in di Avengers, Iron Man, Thor, Spider-Man, X-Force e Home Front non sono ancora obbligatori; gli Omnibus possono coprire il core come edizioni alternative.",
        "readingOrder": ["Fear Itself: Book of the Skull #1", *[f"Fear Itself (2011) #{n}" for n in range(1, 8)]],
        "issues": [
            issue(118, "Fear Itself: Il libro del teschio", "Oct 2011", "Prologo", "Fear Itself: Book of the Skull #1."),
            *[
                issue(n, f"Fear Itself, pt {n-118}", f"{['Nov','Dec','Jan','Feb','Mar','Apr','May'][n-119]} {2011 if n <= 120 else 2012}", "Evento principale", f"Fear Itself #{n-118}.")
                for n in range(119, 126)
            ],
        ],
    },
    {
        "id": "avengers-vs-xmen",
        "name": "Avengers vs. X-Men",
        "subtitle": "AvX · Fenice — core 2012",
        "accent": "#d55d48",
        "description": "Percorso core di Avengers vs. X-Men: prologo AVX #0 e i dodici round della miniserie principale, raccolti in sette Marvel Miniserie italiani. AvX: VS e i tie-in delle testate sono fuori dal conteggio obbligatorio; i due volumi Conseguenze sono presenti come epilogo facoltativo.",
        "readingOrder": ["Avengers vs. X-Men #0", *[f"Avengers vs. X-Men #{n}" for n in range(1, 13)]],
        "issues": [
            issue(128, "AVX 0", "Oct 2012", "Prologo", "Point One + Avengers vs. X-Men #0: prepara Hope, Scarlet e la Fenice."),
            issue(129, "AVX 1", "Nov 2012", "Evento principale", "Avengers vs. X-Men #1–2."),
            issue(130, "AVX 2", "Dec 2012", "Evento principale", "Avengers vs. X-Men #3–4."),
            issue(131, "AVX 3", "Jan 2013", "Evento principale", "Avengers vs. X-Men #5–6."),
            issue(132, "AVX 4", "Feb 2013", "Evento principale", "Avengers vs. X-Men #7–8."),
            issue(133, "AVX 5", "Mar 2013", "Evento principale", "Avengers vs. X-Men #9–10."),
            issue(134, "AVX 6", "Apr 2013", "Evento principale", "Avengers vs. X-Men #11–12 e conclusione."),
            issue(135, "AvX Conseguenze, vol 1", "May 2013", "Epilogo facoltativo", "AvX: Consequences — prima parte. Leggilo se vuoi seguire le conseguenze immediate.", required=False),
            issue(136, "AvX Conseguenze, vol 2", "Jun 2013", "Epilogo facoltativo", "AvX: Consequences — conclusione. Facoltativo rispetto al core.", required=False),
        ],
    },
]


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build_routes() -> None:
    for event in EVENTS:
        required = sum(1 for row in event["issues"] if row.get("required") is not False)
        payload = {
            "id": event["id"],
            "name": event["name"],
            "subtitle": event["subtitle"],
            "accent": event["accent"],
            "start": f"{event['issues'][0]['name']} — {event['issues'][0]['date']}",
            "end": f"{event['issues'][-1 if event['issues'][-1].get('required') is not False else -3]['name']} — {event['issues'][-1 if event['issues'][-1].get('required') is not False else -3]['date']}",
            "description": event["description"],
            "timelineMode": True,
            "eventScope": "core",
            "readingOrderSource": "Marvel official event reading list — core/main event",
            "readingOrder": event["readingOrder"],
            "series": [{"id": "MMMI", "name": "Marvel Miniserie", "publisher": "Marvel Italia / Panini Comics", "range": f"#{event['issues'][0]['n']}–#{event['issues'][-1]['n']}"}],
            "archives": [],
            "totalRequired": required,
            "availableTotal": required,
            "issues": event["issues"],
        }
        write_json(DATA / "characters" / f"{event['id']}.json", payload)


def write_logos() -> None:
    marks = {
        "house-of-m": "M",
        "civil-war": "CW",
        "secret-invasion": "SI",
        "siege": "S",
        "fear-itself": "FI",
        "avengers-vs-xmen": "AvX",
    }
    for event in EVENTS:
        mark = marks[event["id"]]
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect x="12" y="12" width="104" height="104" rx="24" fill="#111720" stroke="{event['accent']}" stroke-width="6"/><text x="64" y="73" text-anchor="middle" font-family="Arial,sans-serif" font-size="32" font-weight="800" fill="{event['accent']}">{mark}</text></svg>'''
        (ROOT / "assets" / "heroes" / f"{event['id']}.svg").write_text(svg, encoding="utf-8")


def update_manifest() -> None:
    path = DATA / "characters.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = MANIFEST_VERSION
    event_ids = {event["id"] for event in EVENTS}
    rows = [row for row in manifest.get("characters", []) if row.get("id") not in event_ids]
    insert_at = next((i for i, row in enumerate(rows) if str(row.get("id", "")).startswith("ultimate-")), len(rows))
    entries = []
    for event in EVENTS:
        required = sum(1 for row in event["issues"] if row.get("required") is not False)
        required_rows = [row for row in event["issues"] if row.get("required") is not False]
        entries.append({
            "id": event["id"],
            "name": event["name"],
            "subtitle": event["subtitle"],
            "type": "event",
            "universe": "Terra-616",
            "primaryHub": "events",
            "hubs": ["events"],
            "accent": event["accent"],
            "logo": f"assets/heroes/{event['id']}.svg",
            "data": f"data/characters/{event['id']}.json",
            "start": f"{required_rows[0]['name']} — {required_rows[0]['date']}",
            "end": f"{required_rows[-1]['name']} — {required_rows[-1]['date']}",
            "totalRequired": required,
        })
    rows[insert_at:insert_at] = entries
    manifest["characters"] = rows
    write_json(path, manifest)


def update_hubs() -> None:
    path = DATA / "hubs.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for hub in payload.get("hubs", []):
        if hub.get("id") != "events":
            continue
        hub.pop("status", None)
        hub["groups"] = [
            {"id": "modern-core", "label": "Grandi eventi moderni — core", "paths": [event["id"] for event in EVENTS]},
            {"id": "complete", "label": "Eventi completi", "paths": ["judgment-day"]},
        ]
        hub["featuredPath"] = "civil-war"
    write_json(path, payload)


def update_curated_editions() -> None:
    path = DATA / "curated-editions.json"
    curated = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "editions": []}
    generated = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    generated_by_id = {row["id"]: row for row in generated.get("editions", [])}
    existing = {row["id"]: row for row in curated.get("editions", [])}

    mappings = {
        "MARVELMUST:26": ("house-of-m", list(range(69, 73)), "House of M — miniserie principale #1–8"),
        "MAROMNIB:7": ("house-of-m", list(range(69, 73)), "House of M — miniserie principale #1–8"),
        "MARVDELUXE:1": ("house-of-m", list(range(69, 73)), "House of M — miniserie principale #1–8"),
        "MARVELMUST:1": ("civil-war", list(range(76, 83)), "Civil War — miniserie principale #1–7"),
        "MAROMNIB:2": ("civil-war", list(range(76, 83)), "Civil War — miniserie principale #1–7"),
        "MAROMNIB:53": ("civil-war", list(range(76, 83)), "Civil War — miniserie principale #1–7"),
        "MARVELMUST:42": ("secret-invasion", list(range(93, 101)), "Secret Invasion — miniserie principale #1–8"),
        "MAROMNIB:15": ("secret-invasion", list(range(93, 101)), "Secret Invasion — miniserie principale #1–8"),
        "MARVELMUST:37": ("siege", list(range(107, 112)), "Assedio — prologo + Siege #1–4"),
        "MAROMNIB:21": ("siege", list(range(107, 112)), "Assedio — prologo + Siege #1–4"),
        "MARVELMUST:48": ("fear-itself", list(range(118, 126)), "Fear Itself — Book of the Skull + #1–7"),
        "MAROMNIB:27": ("fear-itself", list(range(118, 126)), "Fear Itself — core principale"),
        "MAROMNIB:31": ("avengers-vs-xmen", list(range(128, 135)), "Avengers vs. X-Men — #0 + round 1–12"),
    }

    for edition_id, (route, nums, label) in mappings.items():
        base = dict(generated_by_id.get(edition_id, {}))
        base.update(existing.get(edition_id, {}))
        if not base:
            raise RuntimeError(f"Edizione raccolta non trovata: {edition_id}")
        previous_cov = list(base.get("coverage", []))
        previous_cov = [c for c in previous_cov if c.get("path") != route]
        previous_cov.append({"path": route, "issueIds": [f"MMMI:{n}" for n in nums], "label": label})
        base["coverage"] = previous_cov
        base["coverageSource"] = "curated:event-core"
        existing[edition_id] = base

    curated["version"] = max(2, int(curated.get("version", 1)) + 1)
    curated["editions"] = sorted(existing.values(), key=lambda row: row.get("id", ""))
    write_json(path, curated)


def patch_edition_builder() -> None:
    path = ROOT / "scripts" / "build_editions_catalog.py"
    text = path.read_text(encoding="utf-8")
    anchor = '    "doctor-strange": ["doctor strange", "dottor strange", "dr. strange", "dr strange"],\n'
    additions = (
        '    "house-of-m": ["house of m"],\n'
        '    "civil-war": ["civil war"],\n'
        '    "secret-invasion": ["secret invasion"],\n'
        '    "siege": ["assedio", "siege"],\n'
        '    "fear-itself": ["fear itself"],\n'
        '    "avengers-vs-xmen": ["avengers vs x-men", "avengers vs. x-men", "avx"],\n'
    )
    if '"house-of-m": ["house of m"]' not in text:
        if anchor not in text:
            raise RuntimeError("Anchor PATH_ALIASES non trovato")
        text = text.replace(anchor, anchor + additions)
    if '"avx",' not in text:
        hint_anchor = '    "extremis", "ragnarok", "spider-verse", "absolute carnage", "king in black",\n'
        if hint_anchor in text:
            text = text.replace(hint_anchor, '    "extremis", "ragnarok", "spider-verse", "absolute carnage", "king in black", "avx",\n')
    old = '    candidates = {path for path, aliases in PATH_ALIASES.items() if any(alias in text for alias in aliases)}\n'
    new = old + '    if "civil war ii" in text or "civil war 2" in text:\n        candidates.discard("civil-war")\n'
    if 'candidates.discard("civil-war")' not in text:
        if old not in text:
            raise RuntimeError("Anchor candidates_for_title non trovato")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def patch_verifier() -> None:
    path = ROOT / "scripts" / "verify-data.mjs"
    text = path.read_text(encoding="utf-8")
    text = text.replace("assert.equal(manifest.version, 14, \"Il manifest deve usare la versione cache v14\");", "assert.equal(manifest.version, 15, \"Il manifest deve usare la versione cache v15\");")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    build_routes()
    write_logos()
    update_manifest()
    update_hubs()
    update_curated_editions()
    patch_edition_builder()
    patch_verifier()
    print("Modern events:", ", ".join(event["name"] for event in EVENTS))
    print("Manifest version:", MANIFEST_VERSION)


if __name__ == "__main__":
    main()
