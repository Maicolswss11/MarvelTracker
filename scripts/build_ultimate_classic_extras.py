#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7500
MANIFEST_VERSION = 9

MONTHS = {
    "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
    "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
    "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12,
}

SPECIALS = [
    # Ultimate Marvel Team-Up — i 16 episodi USA sono raccolti in quattro Marvel Crossover italiani.
    {"id":"MCROS_M:32","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":32,"title":"Ultimate Spider-Man Special 1 — Ultimate Marvel Team-Up","date":"Aprile 2002","code":"MCROS_M_032","route":"ultimate-team-up","era":"Ultimate Marvel Team-Up","storyOrder":(2002,4,10)},
    {"id":"MCROS_M:33","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":33,"title":"Ultimate Spider-Man Special 2 — Ultimate Marvel Team-Up","date":"Luglio 2002","code":"MCROS_M_033","route":"ultimate-team-up","era":"Ultimate Marvel Team-Up","storyOrder":(2002,7,10)},
    {"id":"MCROS_M:34","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":34,"title":"Ultimate Spider-Man Special 3 — Ultimate Marvel Team-Up","date":"Settembre 2002","code":"MCROS_M_034","route":"ultimate-team-up","era":"Ultimate Marvel Team-Up","storyOrder":(2002,9,10)},
    {"id":"MCROS_M:35","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":35,"title":"Ultimate Spider-Man Special 4 — Ultimate Marvel Team-Up","date":"Dicembre 2002","code":"MCROS_M_035","route":"ultimate-team-up","era":"Ultimate Marvel Team-Up","storyOrder":(2002,12,10)},

    # Prime miniserie autonome fuori dalle quattro collane principali.
    {"id":"MCROS_M:37","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":37,"title":"Ultimate Daredevil and Elektra","date":"Giugno 2003","code":"MCROS_M_037","route":"ultimate-specials","era":"Devil, Elektra e gli altri eroi Ultimate","storyOrder":(2003,6,20)},
    {"id":"MCROS_M:38","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":38,"title":"Ultimate Adventures: Soldatino di Latta","date":"Maggio 2004","code":"MCROS_M_038","route":"ultimate-specials","era":"Devil, Elektra e gli altri eroi Ultimate","storyOrder":(2004,5,20)},
    {"id":"MCROS_M:39","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":39,"title":"Ultimate Elektra","date":"Maggio 2005","code":"MCROS_M_039","route":"ultimate-specials","era":"Devil, Elektra e gli altri eroi Ultimate","storyOrder":(2005,5,20)},

    # Tony Stark Ultimate — volumi italiani autonomi non presenti negli spillati Ultimates.
    {"id":"MCROS_M:43","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":43,"title":"Ultimate Iron-Man","date":"Luglio 2006","code":"MCROS_M_043","route":"ultimate-ironman","era":"Ultimate Iron Man — origini","storyOrder":(2006,7,30)},
    {"id":"MA_MEG:46","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":46,"title":"Ultimate Iron Man 2","date":"Ottobre 2008","code":"MA_MEG_046","route":"ultimate-ironman","era":"Ultimate Iron Man — origini","storyOrder":(2008,10,30)},
    {"id":"MA_MEG:59","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":59,"title":"Ultimate Comics Armor Wars","date":"Aprile 2010","code":"MA_MEG_059","route":"ultimate-ironman","era":"Ultimate Armor Wars","storyOrder":(2010,4,30)},
    {"id":"MA_MEG:82","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":82,"title":"Ultimate Comics Iron Man III — Il demone nell'armatura","date":"Aprile 2013","code":"MA_MEG_082","route":"ultimate-ironman","era":"Ultimate Comics Iron Man","storyOrder":(2013,4,30)},

    # Origini e annual immediatamente precedenti a Ultimatum.
    {"id":"MCROS_M:54","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":54,"title":"Ultimate Origins","date":"Marzo 2009","code":"MCROS_M_054","route":"ultimate-origins-annuals","era":"Origini dell'Universo Ultimate","storyOrder":(2009,3,40)},
    {"id":"MCROS_M:57","seriesId":"MCROS_M","series":"Marvel Crossover","publisher":"Marvel Italia","n":57,"title":"Ultimate Capitan America e Hulk","date":"Luglio 2009","code":"MCROS_M_057","route":"ultimate-origins-annuals","era":"Annual e preludio a Ultimatum","storyOrder":(2009,7,40)},

    # Wolverine/Hulk e il successivo speciale Wolverine.
    {"id":"MA_MEG:53","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":53,"title":"Ultimate Wolverine vs Hulk","date":"Ottobre 2009","code":"MA_MEG_053","route":"ultimate-wolverine","era":"Ultimate Wolverine vs Hulk","storyOrder":(2009,10,50)},
    {"id":"MA_MEG:85","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":85,"title":"Ultimate Comics Wolverine Special","date":"Dicembre 2013","code":"MA_MEG_085","route":"ultimate-wolverine","era":"Ultimate Comics Wolverine","storyOrder":(2013,12,50)},

    # Trilogia Enemy → Mystery → Doom, fondamentale per Reed Richards/Maker.
    {"id":"MA_MEG:66","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":66,"title":"Ultimate Comics Enemy","date":"Novembre 2010","code":"MA_MEG_066","route":"ultimate-doomsday","era":"Ultimate Doomsday — Enemy","storyOrder":(2010,11,60)},
    {"id":"MA_MEG:69","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":69,"title":"Ultimate Comics Mystery","date":"Aprile 2011","code":"MA_MEG_069","route":"ultimate-doomsday","era":"Ultimate Doomsday — Mystery","storyOrder":(2011,4,60)},
    {"id":"MA_MEG:72","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":72,"title":"Ultimate Comics Doom","date":"Settembre 2011","code":"MA_MEG_072","route":"ultimate-doomsday","era":"Ultimate Doomsday — Doom","storyOrder":(2011,9,60)},

    # Ultima fase dopo Cataclisma.
    {"id":"MA_MEG:91","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":91,"title":"All-New Ultimates 1","date":"Marzo 2015","code":"MA_MEG_091","route":"ultimate-post-cataclysm","era":"Dopo Cataclisma — nuova generazione","storyOrder":(2015,3,70)},
    {"id":"MA_MEG:92","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":92,"title":"Ultimate FF: Spacciati!","date":"Maggio 2015","code":"MA_MEG_092","route":"ultimate-post-cataclysm","era":"Dopo Cataclisma — Ultimate FF","storyOrder":(2015,5,70)},
    {"id":"MA_MEG:95","seriesId":"MA_MEG","series":"Marvel Mega","publisher":"Marvel Italia","n":95,"title":"All-New Ultimates 2","date":"Settembre 2015","code":"MA_MEG_095","route":"ultimate-post-cataclysm","era":"Dopo Cataclisma — nuova generazione","storyOrder":(2015,9,70)},
]

ROUTES = {
    "ultimate-team-up": {
        "name":"Ultimate Marvel Team-Up","subtitle":"Gli incontri che costruiscono Terra-1610","type":"collection","accent":"#f0c14b",
        "description":"I quattro Marvel Crossover italiani che raccolgono i sedici numeri di Ultimate Marvel Team-Up: Spider-Man incontra Wolverine, Hulk, Iron Man, Punisher, Daredevil, Fantastic Four, X-Men, Doctor Strange, Black Widow e altri eroi della nuova continuità.",
    },
    "ultimate-specials": {
        "name":"Ultimate Speciali","subtitle":"Daredevil, Elektra e Adventures","type":"collection","accent":"#d7a86e",
        "description":"Prime miniserie autonome dell'Universo Ultimate pubblicate in Italia fuori dalle quattro testate principali: Daredevil & Elektra, Ultimate Adventures e Ultimate Elektra.",
    },
    "ultimate-ironman": {
        "name":"Ultimate Iron Man","subtitle":"Tony Stark di Terra-1610","type":"character","accent":"#d96a54",
        "description":"Percorso personale di Tony Stark Ultimate attraverso i volumi italiani autonomi: le due miniserie sulle origini, Armor Wars e Il demone nell'armatura.",
    },
    "ultimate-origins-annuals": {
        "name":"Ultimate Origins & Annuals","subtitle":"Le origini segrete prima di Ultimatum","type":"event","accent":"#e1c46b",
        "description":"Ultimate Origins e lo speciale italiano che raccoglie gli annual di Capitan America e Hulk: materiale di raccordo essenziale verso Ultimatum.",
    },
    "ultimate-wolverine": {
        "name":"Ultimate Wolverine","subtitle":"Wolverine, Hulk e il seguito post-Ultimatum","type":"character","accent":"#d7c65c",
        "description":"Le principali miniserie italiane autonome dedicate al Wolverine Ultimate: Wolverine vs Hulk e Ultimate Comics Wolverine.",
    },
    "ultimate-doomsday": {
        "name":"Ultimate Doomsday","subtitle":"Enemy → Mystery → Doom","type":"event","accent":"#79a0d8",
        "description":"La trilogia di Brian Michael Bendis che trasforma definitivamente Reed Richards e prepara la traiettoria del Maker: Enemy, Mystery e Doom.",
    },
    "ultimate-post-cataclysm": {
        "name":"Ultimate — Dopo Cataclisma","subtitle":"All-New Ultimates e Ultimate FF","type":"collection","accent":"#70b8c8",
        "description":"Le serie della fase finale di Terra-1610 dopo Cataclisma: All-New Ultimates e Ultimate FF, immediatamente prima del collasso dell'universo durante Secret Wars.",
    },
}


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


def date_key(value: str) -> tuple[int,int,int]:
    year_match = re.search(r"(?:19|20)\d{2}", value)
    month = next((num for name,num in MONTHS.items() if name in value), 12)
    return (int(year_match.group()) if year_match else 9999, month, 15)


def era_for_date(value: str) -> tuple[str,str]:
    year, _, _ = date_key(value)
    if year <= 2002:
        return "Nascita dell'Universo Ultimate", "Spider-Man, X-Men e i primi incontri costruiscono Terra-1610"
    if year <= 2006:
        return "Espansione dell'Universo Ultimate", "Nuovi eroi, Fantastic Four, Ultimates e miniserie autonome"
    if year <= 2008:
        return "Universo condiviso — grandi crossover", "Galactus, Ultimate Power e l'espansione delle linee principali"
    if year == 2009:
        return "Verso Ultimatum", "Origini, annual e ultime storie prima e durante la grande catastrofe"
    if year <= 2011:
        return "Ultimate Comics — ricostruzione", "Dopo Ultimatum nascono nuove squadre, nuovi nemici e il futuro Maker"
    if year <= 2013:
        return "Miles e la terza era Ultimate", "Nuove generazioni e nuovi equilibri di Terra-1610"
    return "Dopo Cataclisma / verso Secret Wars", "La fase finale dell'Universo Ultimate prima dell'incursione"


def issue_from_spec(spec: dict, route_name: str) -> dict:
    era, era_sub = era_for_date(spec["date"])
    if route_name != "Ultimate Universe":
        era = spec["era"]
        era_sub = ROUTES[spec["route"]]["subtitle"]
    return {
        "id": spec["id"], "seq": 0, "seriesId": spec["seriesId"], "series": spec["series"],
        "publisher": spec["publisher"], "n": spec["n"], "name": f"{spec['series']} #{spec['n']}",
        "title": spec["title"], "date": spec["date"], "dateQuality":"curata", "era":era, "eraSub":era_sub,
        "cover": f"https://www.comicsbox.it/cover/{spec['code']}.jpg", "url": f"https://www.comicsbox.it/albo/{spec['code']}",
        "required": True, "skip": False, "coverSource":"ComicsBox", "sharedWith":["Ultimate Universe", route_name],
        "instruction": "Albo fisico condiviso con il percorso master Ultimate Universe. Leggi il volume completo e prosegui con la tappa successiva.",
        "_storyOrder": spec["storyOrder"],
    }


def resequence(issues: list[dict]) -> list[dict]:
    result=[]
    for seq, issue in enumerate(issues,1):
        item=deepcopy(issue)
        item["seq"]=seq
        item.pop("_storyOrder",None)
        result.append(item)
    return result


def make_route(cid: str, specs: list[dict]) -> dict:
    meta=ROUTES[cid]
    issues=resequence([issue_from_spec(spec, meta["name"]) for spec in specs])
    unique_series=[]
    seen=set()
    for issue in issues:
        if issue["seriesId"] in seen: continue
        seen.add(issue["seriesId"])
        unique_series.append({"id":issue["seriesId"],"name":issue["series"],"publisher":issue["publisher"],"range":"selezione Ultimate"})
    return {
        "id":cid,"name":meta["name"],"subtitle":meta["subtitle"],"accent":meta["accent"],
        "start":f"{issues[0]['name']} — {issues[0]['date']}","end":f"{issues[-1]['name']} — {issues[-1]['date']}",
        "description":meta["description"],"timelineMode":True,"series":unique_series,"archives":[],
        "totalRequired":len(issues),"availableTotal":len(issues),"issues":issues,
    }


def build_master() -> dict:
    master=unpack("ultimate-universe")
    base=[]
    for issue in master["issues"]:
        item=deepcopy(issue)
        item["_storyOrder"] = (*date_key(issue["date"]), 10, issue.get("n",0))
        base.append(item)
    extras=[]
    for spec in SPECIALS:
        item=issue_from_spec(spec,"Ultimate Universe")
        y,m,p=spec["storyOrder"]
        item["_storyOrder"]=(y,m,15,p,spec["n"])
        extras.append(item)
    unique={item["id"]:item for item in base+extras}
    ordered=sorted(unique.values(), key=lambda item:item["_storyOrder"])
    master["issues"]=resequence(ordered)
    master["totalRequired"]=len(master["issues"])
    master["availableTotal"]=len(master["issues"])
    master["subtitle"]="Terra-1610 · percorso completo con eventi e miniserie"
    master["description"]="Percorso master del vecchio Universo Ultimate: intreccia le quattro linee principali e le pubblicazioni italiane autonome realmente necessarie per seguire Terra-1610 senza dover ricostruire a mano Team-Up, Origins, Doomsday, Iron Man e la fase post-Cataclisma. Gli stessi ID fisici sono riutilizzati nei percorsi tematici, quindi Recuperato resta condiviso."
    known={item.get("id") for item in master.get("series",[])}
    if "MCROS_M" not in known:
        master["series"].append({"id":"MCROS_M","name":"Marvel Crossover","publisher":"Marvel Italia","range":"speciali Ultimate selezionati"})
    if "MA_MEG" not in known:
        master["series"].append({"id":"MA_MEG","name":"Marvel Mega","publisher":"Marvel Italia","range":"miniserie Ultimate selezionate"})
    return master


def update_manifest(master: dict, route_characters: list[dict]) -> None:
    path=DATA/"characters.json"
    manifest=json.loads(path.read_text(encoding="utf-8"))
    manifest["version"]=MANIFEST_VERSION
    new_ids={"ultimate-universe", *ROUTES.keys()}
    chars=[item for item in manifest["characters"] if item["id"] not in new_ids]
    master_meta=next((item for item in manifest["characters"] if item["id"]=="ultimate-universe"), None)
    if not master_meta: raise RuntimeError("ultimate-universe assente dal manifest")
    master_meta=dict(master_meta)
    master_meta.update({"subtitle":"Terra-1610 · percorso completo","totalRequired":master["totalRequired"],"start":master["start"],"end":master["end"]})
    insert_at=len(chars)
    chars.insert(insert_at,master_meta)
    for character in route_characters:
        meta=ROUTES[character["id"]]
        chars.append({
            "id":character["id"],"name":character["name"],"subtitle":character["subtitle"],"type":meta["type"],
            "primaryHub":"ultimate-classic","hubs":["ultimate-classic"],"accent":character["accent"],
            "logo":"assets/heroes/ultimate-universe.svg","data":f"data/characters/{character['id']}.json",
            "start":character["start"],"end":character["end"],"totalRequired":character["totalRequired"],
        })
    manifest["characters"]=chars
    path.write_text(json.dumps(manifest,ensure_ascii=False,separators=(",", ":")),encoding="utf-8")


def update_hub() -> None:
    path=DATA/"hubs.json"
    payload=json.loads(path.read_text(encoding="utf-8"))
    hub=next(item for item in payload["hubs"] if item["id"]=="ultimate-classic")
    hub["subtitle"]="Terra-1610 · un universo completo e finito da seguire"
    hub["featuredPath"]="ultimate-universe"
    hub["groups"]=[
        {"id":"master","label":"Segui tutto l'universo","paths":["ultimate-universe"]},
        {"id":"core","label":"Linee principali","paths":["ultimate-spiderman-classic","ultimate-xmen","ultimates","ultimate-fantastic-four"]},
        {"id":"events","label":"Eventi e miniserie","paths":["ultimate-team-up","ultimate-origins-annuals","ultimate-doomsday","ultimate-ironman","ultimate-wolverine","ultimate-specials","ultimate-post-cataclysm"]},
    ]
    path.write_text(json.dumps(payload,ensure_ascii=False,separators=(",", ":")),encoding="utf-8")


def main() -> None:
    master=build_master()
    route_characters=[]
    for cid in ROUTES:
        specs=[spec for spec in SPECIALS if spec["route"]==cid]
        route_characters.append(make_route(cid,specs))
    pack(master)
    for character in route_characters: pack(character)
    update_manifest(master,route_characters)
    update_hub()
    print(f"Ultimate Universe completo: {master['totalRequired']} tappe ({len(SPECIALS)} extra fisici aggiunti)")
    for character in route_characters:
        print(f"- {character['name']}: {character['totalRequired']}")

if __name__=="__main__":
    main()
