#!/usr/bin/env python3
from __future__ import annotations

import base64, gzip, json, re, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
CHUNK_SIZE=7500
USER_AGENT="MarvelTracker data maintenance/5.0"
MANIFEST_VERSION = 9
MONTHS_IT={"Jan":"Gennaio","Feb":"Febbraio","Mar":"Marzo","Apr":"Aprile","May":"Maggio","Jun":"Giugno","Jul":"Luglio","Aug":"Agosto","Sep":"Settembre","Oct":"Ottobre","Nov":"Novembre","Dec":"Dicembre"}

class SeriesTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.rows=[]; self._in_row=False; self._in_cell=False; self._cells=[]; self._text=[]; self._href=""
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="tr": self._in_row=True; self._cells=[]; self._href=""
        elif tag=="td" and self._in_row: self._in_cell=True; self._text=[]
        elif tag=="a" and self._in_cell:
            href=d.get("href") or ""
            if "/albo/" in href and not self._href:self._href=href
    def handle_data(self,data):
        if self._in_cell:self._text.append(data)
    def handle_endtag(self,tag):
        if tag=="td" and self._in_cell:
            self._cells.append(" ".join("".join(self._text).split())); self._in_cell=False
        elif tag=="tr" and self._in_row:
            self._in_row=False
            if len(self._cells)>=4 and self._href:
                m=re.search(r"\d+",self._cells[0])
                if m:self.rows.append({"n":m.group(0),"name":self._cells[1].rstrip("* "),"title":self._cells[2],"date":self._cells[3],"href":self._href})

def fetch_url(url,attempts=5):
    last=None
    for attempt in range(1,attempts+1):
        try:
            req=Request(url,headers={"User-Agent":USER_AGENT})
            with urlopen(req,timeout=45) as response: source=response.read().decode("utf-8",errors="replace")
            if "Connessione MySQL fallita" in source: raise RuntimeError("ComicsBox database temporarily unavailable")
            return source
        except (HTTPError,URLError,TimeoutError,RuntimeError) as exc:
            last=exc
            if attempt<attempts: time.sleep(1.5*attempt)
    raise RuntimeError(f"Impossibile leggere {url}: {last}")

def fetch_all_series(code,max_pages=4):
    records={}
    for page in range(max_pages):
        parser=SeriesTableParser(); parser.feed(fetch_url(f"https://www.comicsbox.it/serie.php?limite={page*50}&serie={code}")); rows=parser.rows
        if not rows:break
        before=len(records)
        for row in rows:records[int(row["n"])]=row
        if len(records)==before or len(rows)<50:break
    if not records:raise RuntimeError(f"{code}: indice ComicsBox vuoto")
    return records

def italian_date(value):
    out=value
    for short,full in MONTHS_IT.items():out=re.sub(rf"\b{short}\b",full,out)
    return out

def era(series_id,n):
    if series_id=="ULSM_M":
        if n<=6:return "Origini — poteri e responsabilità","Peter Parker nasce come Spider-Man nell'Universo Ultimate"
        if n<=20:return "Primi anni — scuola, Goblin e Kingpin","Il mondo di Peter cresce attorno a scuola, amici e primi grandi nemici"
        if n<=40:return "Espansione dell'Universo Ultimate","Peter incontra sempre più eroi e minacce del nuovo universo Marvel"
        if n<=60:return "Clone Saga e maturazione","La vita di Peter diventa più complessa e la serie entra nella sua fase più ambiziosa"
        if n<=70:return "Ultimatum","Il disastro di Ultimatum travolge New York e chiude la prima grande era"
        return "Requiem","Epilogo della prima serie e passaggio al rilancio Ultimate Comics"
    if n<=10:return "Peter Parker — dopo Ultimatum","Il nuovo mondo di Peter Parker dopo la catastrofe"
    if n<=13:return "La morte di Spider-Man","L'ultimo arco di Peter Parker nell'Universo Ultimate"
    if n<=27:return "Miles Morales — il nuovo Spider-Man","Miles raccoglie l'eredità di Peter e costruisce una propria identità"
    if n<=29:return "Cataclisma","Galactus minaccia l'Universo Ultimate e Miles affronta una crisi cosmica"
    if n<=35:return "Miles Morales — verso la fine","Gli ultimi grandi archi di Miles prima di Secret Wars"
    return "Secret Wars / Ultimate End","La dissoluzione del vecchio Universo Ultimate e il ponte verso Battleworld"

def make_issue(series_id,series_name,publisher,n,row,seq):
    e,sub=era(series_id,n); code=row["href"].split("/albo/")[-1].split("?")[0]
    instruction="Segui la pubblicazione italiana in ordine."
    if series_id=="ULSM_M" and n==71: instruction="REQU IEM: epilogo di Ultimatum. Dopo questo albo passa a Ultimate Comics Spider-Man #1."
    elif series_id=="ULTC_SM_M" and n==1: instruction="RIPARTENZA: continua direttamente da Ultimate Spider-Man (I) #71."
    elif series_id=="ULTC_SM_M" and n==14: instruction="CAMBIO DI PROTAGONISTA: inizia l'era di Miles Morales come nuovo Spider-Man Ultimate."
    elif series_id=="ULTC_SM_M" and n>=36: instruction="PONTE MULTIVERSALE: Ultimate End confluisce negli eventi di Secret Wars/Battleworld."
    return {"id":f"{series_id}:{n}","seq":seq,"seriesId":series_id,"series":series_name,"publisher":publisher,"n":n,"name":f"{series_name} #{n}","title":row["title"] or "Albo del percorso Ultimate Spider-Man","date":italian_date(row["date"]),"dateQuality":"indice","era":e,"eraSub":sub,"cover":f"https://www.comicsbox.it/cover/{code}.jpg","url":f"https://www.comicsbox.it/albo/{code}","required":True,"skip":False,"instruction":instruction,"coverSource":"ComicsBox"}

def pack(character):
    raw=json.dumps(character,ensure_ascii=False,separators=(",",":")).encode(); enc=base64.b64encode(gzip.compress(raw,compresslevel=9,mtime=0)).decode("ascii")
    for old in (DATA/"b64").glob("ultimate-spiderman-classic-*.b64"):old.unlink()
    parts=[enc[i:i+CHUNK_SIZE] for i in range(0,len(enc),CHUNK_SIZE)]; sources=[]
    for idx,part in enumerate(parts,1):
        rel=f"data/b64/ultimate-spiderman-classic-{idx:02d}.b64"; (ROOT/rel).write_text(part,encoding="ascii"); sources.append(rel)
    (DATA/"encoded"/"ultimate-spiderman-classic.json").write_text(json.dumps({"encoding":"gzip-base64-parts","sources":sources},separators=(",",":")),encoding="utf-8")
    print(f"Ultimate Spider-Man classico: {len(character['issues'])} albi, {len(raw):,} byte, {len(parts)} parti")

def main():
    first=fetch_all_series("ULSM_M",3); second=fetch_all_series("ULTC_SM_M",2)
    if max(first)!=71:raise RuntimeError(f"Ultimate Spider-Man (I): attesi 71 numeri, trovati {max(first)}")
    if max(second)!=37:raise RuntimeError(f"Ultimate Comics Spider-Man: attesi 37 numeri, trovati {max(second)}")
    for expected,rows,name in [(71,first,"Ultimate Spider-Man (I)"),(37,second,"Ultimate Comics Spider-Man")]:
        missing=[n for n in range(1,expected+1) if n not in rows]
        if missing:raise RuntimeError(f"{name}: numeri mancanti {missing}")
    issues=[]; seq=1
    for n in range(1,72):issues.append(make_issue("ULSM_M","Ultimate Spider-Man (I)","Panini Comics",n,first[n],seq));seq+=1
    for n in range(1,38):issues.append(make_issue("ULTC_SM_M","Ultimate Comics Spider-Man","Panini Comics",n,second[n],seq));seq+=1
    character={"id":"ultimate-spiderman-classic","name":"Ultimate Spider-Man","subtitle":"Peter Parker → Miles Morales · Terra-1610","accent":"#f0c14b","start":"Ultimate Spider-Man (I) #1 — Maggio 2001","end":f"Ultimate Comics Spider-Man #37 — {italian_date(second[37]['date'])}","description":"Percorso completo della linea italiana di Ultimate Spider-Man del vecchio Universo Ultimate (Terra-1610): dalle origini di Peter Parker alla sua morte, dal passaggio del testimone a Miles Morales fino a Ultimate End e Secret Wars. Il nuovo Ultimate di Terra-6160 resta un universo separato.","timelineMode":True,"series":[{"id":"ULSM_M","name":"Ultimate Spider-Man (I)","publisher":"Panini Comics","range":"#1–71","years":"2001–2010"},{"id":"ULTC_SM_M","name":"Ultimate Comics Spider-Man","publisher":"Panini Comics","range":"#1–37","years":"2010–2016"}],"archives":[],"totalRequired":len(issues),"availableTotal":len(issues),"issues":issues}
    pack(character)
    stub={k:v for k,v in character.items() if k not in {"issues","availableTotal"}};stub["issueSources"]=["data/encoded/ultimate-spiderman-classic.json"]
    (DATA/"characters"/"ultimate-spiderman-classic.json").write_text(json.dumps(stub,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    manifest_path=DATA/"characters.json";manifest=json.loads(manifest_path.read_text(encoding="utf-8"));manifest["version"]=MANIFEST_VERSION
    meta={"id":"ultimate-spiderman-classic","name":"Ultimate Spider-Man","subtitle":"Peter Parker → Miles Morales · Terra-1610","type":"character","primaryHub":"ultimate-classic","hubs":["ultimate-classic"],"accent":"#f0c14b","logo":"assets/heroes/ultimate-spiderman.svg","data":"data/characters/ultimate-spiderman-classic.json","start":character["start"],"end":character["end"],"totalRequired":character["totalRequired"]}
    chars=[c for c in manifest["characters"] if c["id"]!="ultimate-spiderman-classic"];chars.append(meta);manifest["characters"]=chars
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    hubs_path=DATA/"hubs.json";hubs=json.loads(hubs_path.read_text(encoding="utf-8"));hub=next(h for h in hubs["hubs"] if h["id"]=="ultimate-classic");hub.pop("status",None);hub["featuredPath"]="ultimate-spiderman-classic";hub["groups"]=[{"id":"core","label":"Percorsi principali","paths":["ultimate-spiderman-classic"]},{"id":"future","label":"Altre linee Ultimate","paths":[]}];hubs_path.write_text(json.dumps(hubs,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (ROOT/"assets"/"heroes"/"ultimate-spiderman.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="Ultimate Spider-Man"><rect width="128" height="128" rx="26" fill="#0b0c11"/><circle cx="64" cy="64" r="47" fill="none" stroke="#f0c14b" stroke-width="6"/><path d="M64 29c-18 0-31 14-31 33 0 21 13 37 31 37s31-16 31-37c0-19-13-33-31-33Z" fill="#a81924"/><path d="M48 55 35 47m45 8 13-8M47 72 35 81m46-9 12 9M64 31v67M35 63h58" stroke="#111827" stroke-width="3"/><path d="M43 55c7-7 13-8 18-4-2 11-7 17-18 18-3-5-3-9 0-14Zm42 0c-7-7-13-8-18-4 2 11 7 17 18 18 3-5 3-9 0-14Z" fill="#f5f7fb"/></svg>',encoding="utf-8")
    print(f"Percorso Ultimate Spider-Man classico generato: {len(issues)} tappe")

if __name__=="__main__":main()
