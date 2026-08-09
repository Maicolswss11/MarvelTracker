#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
USER_AGENT = "MarvelTracker mystic-cosmic expansion/1.0"
MANIFEST_VERSION = 13

MONTHS = {"Jan":"Gennaio","Feb":"Febbraio","Mar":"Marzo","Apr":"Aprile","May":"Maggio","Jun":"Giugno","Jul":"Luglio","Aug":"Agosto","Sep":"Settembre","Oct":"Ottobre","Nov":"Novembre","Dec":"Dicembre"}

class SeriesParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]; self.in_row=False; self.in_cell=False; self.cells=[]; self.text=[]; self.href=""
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=="tr": self.in_row=True; self.cells=[]; self.href=""
        elif tag=="td" and self.in_row: self.in_cell=True; self.text=[]
        elif tag=="a" and self.in_cell and not self.href:
            href=attrs.get("href") or ""
            if "/albo/" in href or "albo/" in href: self.href=href
    def handle_data(self,data):
        if self.in_cell: self.text.append(data)
    def handle_endtag(self,tag):
        if tag=="td" and self.in_cell:
            self.cells.append(" ".join("".join(self.text).split())); self.in_cell=False
        elif tag=="tr" and self.in_row:
            self.in_row=False
            if self.href and len(self.cells)>=4:
                self.rows.append({"number":self.cells[0].strip().rstrip("* "),"label":self.cells[1].strip().rstrip("* "),"title":self.cells[2].strip(),"date":self.cells[3].strip(),"href":self.href})

def norm(v):
    v=unicodedata.normalize("NFKD",v or ""); v="".join(c for c in v if not unicodedata.combining(c)); return " ".join(v.casefold().split())

def fetch(url,attempts=5):
    last=None
    for a in range(1,attempts+1):
        try:
            req=Request(url,headers={"User-Agent":USER_AGENT,"Accept-Language":"it-IT,it;q=0.9"})
            with urlopen(req,timeout=45) as r: source=r.read().decode("utf-8",errors="replace")
            if "Connessione MySQL fallita" in source: raise RuntimeError("ComicsBox DB unavailable")
            return source
        except Exception as e:
            last=e
            if a<attempts: time.sleep(a*1.5)
    raise RuntimeError(f"{url}: {last}")

def album_code(href):
    m=re.search(r"(?:^|/)albo/([^/?#]+)",href or ""); return unquote(m.group(1)) if m else ""

def load_series(code,max_pages=20,required=True):
    rows=[]; seen=set()
    try:
        for off in range(0,max_pages*50,50):
            p=SeriesParser(); p.feed(fetch(f"https://www.comicsbox.it/serie.php?limite={off}&serie={code}"))
            fresh=0
            for row in p.rows:
                ac=album_code(row["href"])
                if not ac or ac in seen: continue
                seen.add(ac); row["code"]=ac; rows.append(row); fresh+=1
            if fresh==0: break
    except Exception:
        if required: raise
    if required and not rows: raise RuntimeError(f"{code}: serie vuota")
    return rows

def intnum(v):
    m=re.search(r"\d+",str(v or "")); return int(m.group()) if m else None

def italian_date(v):
    for a,b in MONTHS.items(): v=re.sub(rf"\b{a}\b",b,v)
    return v

def rowmap(rows):
    return {intnum(r["number"]):r for r in rows if intnum(r["number"]) is not None}

def cover(row): return f"https://www.comicsbox.it/cover/{row['code']}.jpg"
def url(row): return f"https://www.comicsbox.it/albo/{row['code']}"

def issue(row,series_id,series_name,publisher,seq,era,instruction,required=True,skip=False,title=None):
    n=intnum(row["number"])
    return {"id":f"{series_id}:{n}","seq":seq,"seriesId":series_id,"series":series_name,"publisher":publisher,"n":n,"name":row.get("label") or f"{series_name} #{n}","title":title or row.get("title") or row.get("label") or series_name,"date":italian_date(row.get("date", "")),"dateQuality":"indice","era":era,"eraSub":instruction,"cover":cover(row),"url":url(row),"required":required,"skip":skip,"instruction":instruction,"coverSource":"ComicsBox"}

def write_json(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

def build_doctor_strange():
    mmw=load_series("MMW_M",6)
    dstr=load_series("DSTR_M",3,required=False)
    epic=rowmap(load_series("MAREPCOLL",2))
    hundred=rowmap(load_series("100M",5))
    modern=rowmap(load_series("DSTRANGE_P",3))
    collection=rowmap(load_series("MVNWCOL_P",20))
    doom=rowmap(load_series("UMSDSTRIMP",2))

    master=[]
    for r in mmw:
        m=re.search(r"Doctor Strange,\s*vol\s*(\d+)",r.get("title", ""),re.I)
        if m: master.append((int(m.group(1)),r))
    master.sort()
    if len(master)<8: raise RuntimeError(f"Doctor Strange Masterworks inattesi: {len(master)}")
    for n in range(1,65):
        if n not in modern: raise RuntimeError(f"Doctor Strange #{n} mancante")
    for n in (3,):
        if n not in epic: raise RuntimeError("Marvel Epic Collection #3 mancante")
    for n in (31,65,174):
        if n not in hundred: raise RuntimeError(f"100% Marvel #{n} mancante")
    for n in (310,391,399,443,487,528,568,640):
        if n not in collection: raise RuntimeError(f"Marvel Collection II #{n} mancante")
    for n in range(1,6):
        if n not in doom: raise RuntimeError(f"Storie Imperiali #{n} mancante")

    issues=[]; seq=1
    for vol,r in master:
        issues.append(issue(r,"MMW_M","Marvel Masterworks","Marvel Italia / Panini Comics",seq,"Classici — Strange Tales e serie originali",f"Volume {vol} della ristampa cronologica classica di Doctor Strange. Leggi il volume completo e prosegui.")); seq+=1
    issues.append(issue(epic[3],"MAREPCOLL","Marvel Epic Collection","Panini Comics",seq,"Sorcerer Supreme — fine anni Ottanta","Prosegue nell'era Doctor Strange: Sorcerer Supreme e include Trionfo e Tormento.",title="Doctor Strange: Trionfo e Tormento")); seq+=1
    for n,r in sorted(((intnum(x["number"]),x) for x in dstr if intnum(x["number"]) is not None),key=lambda x:x[0]):
        issues.append(issue(r,"DSTR_M","Dottor Strange","Marvel Italia",seq,"Anni Novanta — Sorcerer Supreme","Edizione italiana Marvel Italia degli anni Novanta: prosegui in ordine di numero.")); seq+=1
    issues.append(issue(hundred[31],"100M","100% Marvel","Marvel Italia",seq,"Anni Duemila — ritorno alle origini","Miniserie Principio e fine: rilettura moderna delle origini, utile ma non indispensabile alla continuità principale.",required=False,skip=True)); seq+=1
    issues.append(issue(hundred[65],"100M","100% Marvel","Marvel Italia",seq,"Anni Duemila — Il giuramento","Il giuramento di Brian K. Vaughan: arco autonomo ma centrale per Stephen Strange.")); seq+=1
    issues.append(issue(hundred[174],"100M","100% Marvel","Marvel Italia",seq,"Verso l'era moderna","Il Dottore è fuori: Stephen opera dopo aver perso il ruolo di Stregone Supremo.")); seq+=1
    for n in range(1,65):
        r=modern[n]
        if n<=25: era="Jason Aaron — Gli ultimi giorni della magia"
        elif n<=37: era="Secret Empire / Rinascita"
        else: era="Donny Cates e Mark Waid — era moderna"
        issues.append(issue(r,"DSTRANGE_P","Doctor Strange","Panini Comics",seq,era,"Segui la testata italiana Doctor Strange in ordine di numero; contiene la spina dorsale moderna di Stephen Strange.")); seq+=1

    post=[
        (310,"Chirurgo Supremo","Sotto i ferri: Stephen torna anche alla chirurgia.",True),
        (391,"La morte di Doctor Strange","Miniserie principale La Morte di Doctor Strange.",True),
        (399,"La morte di Doctor Strange — tie-in","Un mondo senza Strange: storie collaterali dell'evento. Facoltativo.",False),
        (443,"Clea — Strega Suprema","Strange 1: Io appartengo alla Morte. Clea raccoglie l'eredità di Stephen.",True),
        (487,"Clea — Strega Suprema","Strange 2: Il Dr. Strange della Morte. Conclusione dell'era di Clea.",True),
        (528,"Il ritorno di Stephen","Doctor Strange 1: La vita di Doctor Strange.",True),
        (568,"Il ritorno di Stephen","Doctor Strange 2: Strange vs. Strange.",True),
        (640,"Blood Hunt","Doctor Strange 3: Blood Hunt; conduce al cambio di Stregone Supremo.",True),
    ]
    for n,era,instr,req in post:
        issues.append(issue(collection[n],"MVNWCOL_P","Marvel Collection II","Panini Comics",seq,era,instr,required=req,skip=not req)); seq+=1
    for n in range(1,6):
        issues.append(issue(doom[n],"UMSDSTRIMP","Un Mondo Sotto Destino: Storie Imperiali","Panini Comics",seq,"Doctor Strange of Asgard","La parte di Doctor Strange of Asgard è serializzata in questa antologia italiana; leggi il segmento di Strange.")); seq+=1

    required_count=sum(1 for x in issues if x.get("required") is not False and not x.get("future"))
    character={"id":"doctor-strange","name":"Doctor Strange","subtitle":"Stephen Strange · Stregone Supremo","accent":"#8d66d9","start":issues[0]["name"]+" — "+issues[0]["date"],"end":issues[-1]["name"]+" — "+issues[-1]["date"],"description":"Percorso narrativo di Stephen Strange in edizione italiana: fondazione classica in Marvel Masterworks, passaggio attraverso Sorcerer Supreme e le miniserie chiave, testata Panini 2016–2020, Chirurgo Supremo, Morte di Doctor Strange, era di Clea, ritorno di Stephen, Blood Hunt e Doctor Strange of Asgard. Le raccolte alternative vengono collegate al medesimo contenuto senza fingere il possesso degli spillati.","timelineMode":True,"series":[],"archives":[],"totalRequired":required_count,"availableTotal":required_count,"issues":issues}
    write_json(DATA/"characters"/"doctor-strange.json",character)
    return character

def build_ultimates_616():
    deluxe=rowmap(load_series("MARVDELUXE",4))
    for n in (2,10):
        if n not in deluxe: raise RuntimeError(f"Marvel Deluxe #{n} mancante")
    rows=[deluxe[2],deluxe[10]]
    issues=[]
    labels=[("Omniversale","Ultimates (2015) #1–12 + Avengers #0: la prima metà della saga cosmica di Al Ewing."),("Guerra in Paradiso","Ultimates² (2016) #1–9 + #100: conclusione della saga cosmica di Al Ewing.")]
    for i,(r,(era,instr)) in enumerate(zip(rows,labels),1):
        issues.append(issue(r,"MARVDELUXE","Marvel Deluxe","Panini Comics",i,era,instr,title=r.get("title")))
    return {"id":"ultimates-616","name":"Ultimates","subtitle":"Al Ewing · Terra-616","accent":"#55d6d0","start":issues[0]["name"]+" — "+issues[0]["date"],"end":issues[-1]["name"]+" — "+issues[-1]["date"],"description":"Saga completa degli Ultimates cosmici di Al Ewing su Terra-616: Captain Marvel, Pantera Nera, Spectrum, Blue Marvel e America Chavez affrontano problemi su scala cosmica e omniversale. Non va confusa con gli Ultimates degli universi Ultimate 1610 o 6160.","timelineMode":True,"series":[{"id":"MARVDELUXE","name":"Marvel Deluxe — The Ultimates di Al Ewing","publisher":"Panini Comics","range":"Omniversale → Guerra in Paradiso"}],"archives":[],"totalRequired":2,"availableTotal":2,"issues":issues}

def update_manifest(ds,ult):
    p=DATA/"characters.json"; m=json.loads(p.read_text(encoding="utf-8")); m["version"]=MANIFEST_VERSION
    chars=[c for c in m["characters"] if c["id"] not in {"doctor-strange","ultimates-616"}]
    dsmeta={"id":"doctor-strange","name":"Doctor Strange","subtitle":"Stephen Strange · Stregone Supremo","type":"character","primaryHub":"mystic","hubs":["mystic"],"accent":"#8d66d9","logo":"assets/heroes/doctor-strange.svg","data":"data/characters/doctor-strange.json","start":ds["start"],"end":ds["end"],"totalRequired":ds["totalRequired"]}
    ultmeta={"id":"ultimates-616","name":"Ultimates","subtitle":"Al Ewing · Terra-616","type":"team","primaryHub":"cosmic","hubs":["cosmic"],"accent":"#55d6d0","logo":"assets/heroes/ultimates-616.svg","data":"data/characters/ultimates-616.json","start":ult["start"],"end":ult["end"],"totalRequired":2}
    insert=next((i+1 for i,c in enumerate(chars) if c["id"]=="fantastic-four"),len(chars)); chars[insert:insert]=[dsmeta,ultmeta]; m["characters"]=chars; write_json(p,m)

def update_hubs():
    p=DATA/"hubs.json"; d=json.loads(p.read_text(encoding="utf-8"))
    for h in d["hubs"]:
        if h["id"]=="mystic":
            h.pop("status",None); h["groups"]=[{"id":"current","label":"Percorsi disponibili","paths":["doctor-strange","scarletwitch"]}]; h["featuredPath"]="doctor-strange"
        elif h["id"]=="cosmic":
            h.pop("status",None); h["groups"]=[{"id":"core","label":"Percorsi disponibili","paths":["ultimates-616"]}]; h["featuredPath"]="ultimates-616"
    write_json(p,d)

def write_logos():
    (ROOT/"assets/heroes/doctor-strange.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><circle cx="64" cy="64" r="54" fill="none" stroke="#8d66d9" stroke-width="8"/><path d="M64 18 75 48l31 1-25 18 9 30-26-18-26 18 9-30-25-18 31-1z" fill="none" stroke="#8d66d9" stroke-width="7" stroke-linejoin="round"/></svg>''',encoding="utf-8")
    (ROOT/"assets/heroes/ultimates-616.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><circle cx="64" cy="64" r="50" fill="none" stroke="#55d6d0" stroke-width="8"/><path d="M39 31v38c0 20 10 29 25 29s25-9 25-29V31" fill="none" stroke="#55d6d0" stroke-width="11" stroke-linecap="round"/><circle cx="64" cy="64" r="7" fill="#55d6d0"/></svg>''',encoding="utf-8")

def patch_support_files():
    verify=ROOT/"scripts/verify-data.mjs"; s=verify.read_text(encoding="utf-8"); s=s.replace("manifest.version, 12","manifest.version, 13").replace("versione cache v12","versione cache v13"); verify.write_text(s,encoding="utf-8")
    editions=ROOT/"scripts/build_editions_catalog.py"; s=editions.read_text(encoding="utf-8")
    if '"DSTRANGEORO"' not in s:
        s=s.replace('    "MARINTTH": {"name": "Marvel Integrale: Thor di Jason Aaron", "publisher": "Panini Comics", "format": "Integrale"},', '    "MARINTTH": {"name": "Marvel Integrale: Thor di Jason Aaron", "publisher": "Panini Comics", "format": "Integrale"},\n    "DSTRANGEORO": {"name": "Doctor Strange (Serie Oro)", "publisher": "Panini Comics", "format": "Brossurato"},\n    "ULF4D_M": {"name": "Ultimate Fantastic Four Deluxe", "publisher": "Marvel Italia", "format": "Brossurato"},')
    if '"doctor-strange"' not in s:
        s=s.replace('    "fantastic-four": ["fantastici quattro", "fantastic four"],', '    "fantastic-four": ["fantastici quattro", "fantastic four"],\n    "doctor-strange": ["doctor strange", "dottor strange", "dr. strange", "dr strange"],')
    editions.write_text(s,encoding="utf-8")
    js=ROOT/"js/editions.js"; s=js.read_text(encoding="utf-8")
    old='''  function isOwned(state,id){\n    const value = state?.editions?.[id];\n    return value === true || !!value?.owned;\n  }'''
    new='''  function isOwned(state,id){\n    const value = state?.editions?.[id];\n    return value === true || !!value?.owned || !!state?.collection?.[id]?.physical;\n  }'''
    if old in s: s=s.replace(old,new)
    js.write_text(s,encoding="utf-8")

def main():
    ds=build_doctor_strange(); ult=build_ultimates_616(); write_json(DATA/"characters"/"ultimates-616.json",ult); update_manifest(ds,ult); update_hubs(); write_logos(); patch_support_files()
    print(f"Doctor Strange: {len(ds['issues'])} tappe, {ds['totalRequired']} richieste")
    print("Ultimates 616: 2 volumi — Omniversale → Guerra in Paradiso")

if __name__=="__main__": main()
