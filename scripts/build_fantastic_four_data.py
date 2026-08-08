#!/usr/bin/env python3
from __future__ import annotations

import base64, gzip, json, re, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7500
USER_AGENT = "MarvelTracker data maintenance/5.0"
MANIFEST_VERSION = 10
MONTHS_IT = {"Jan":"Gennaio","Feb":"Febbraio","Mar":"Marzo","Apr":"Aprile","May":"Maggio","Jun":"Giugno","Jul":"Luglio","Aug":"Agosto","Sep":"Settembre","Oct":"Ottobre","Nov":"Novembre","Dec":"Dicembre"}

class SeriesTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.rows=[]; self._in_row=False; self._in_cell=False; self._cells=[]; self._text=[]; self._href=""
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="tr": self._in_row=True; self._cells=[]; self._href=""
        elif tag=="td" and self._in_row: self._in_cell=True; self._text=[]
        elif tag=="a" and self._in_cell:
            href=d.get("href") or ""
            if "/albo/" in href and not self._href: self._href=href
    def handle_data(self,data):
        if self._in_cell: self._text.append(data)
    def handle_endtag(self,tag):
        if tag=="td" and self._in_cell:
            self._cells.append(" ".join("".join(self._text).split())); self._in_cell=False
        elif tag=="tr" and self._in_row:
            self._in_row=False
            if len(self._cells)>=4 and self._href:
                m=re.search(r"\d+",self._cells[0])
                if m:self.rows.append({"n":m.group(0),"name":self._cells[1].rstrip("* "),"title":self._cells[2],"date":self._cells[3],"href":self._href})

def fetch_url(url, attempts=5):
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

def fetch_all_series(code,max_pages=12):
    records={}
    for page in range(max_pages):
        parser=SeriesTableParser(); parser.feed(fetch_url(f"https://www.comicsbox.it/serie.php?limite={page*45}&serie={code}")); rows=parser.rows
        if not rows: break
        before=len(records)
        for row in rows: records[int(row["n"])]=row
        if len(records)==before or len(rows)<50: break
    if not records: raise RuntimeError(f"{code}: indice ComicsBox vuoto")
    return records

def italian_date(value):
    out=value
    for short,full in MONTHS_IT.items(): out=re.sub(rf"\b{short}\b",full,out)
    return out

def ff_era(n):
    if n<=4: return "Verso l'era Byrne","La testata italiana riparte da Fantastic Four #229 e accompagna il gruppo verso il grande ciclo di John Byrne"
    if n<=69: return "John Byrne e gli anni Ottanta","La Prima Famiglia entra nel suo grande rilancio moderno"
    if n<=114: return "Fine Star Comics / DeFalco","Dalla fase post-Byrne alla lunga gestione anni Novanta"
    if n<=149: return "Marvel Italia — anni Novanta","La testata passa a Marvel Italia e consolida la nuova continuità editoriale"
    if n<=199: return "Heroes Reborn / Heroes Return","Crisi, rinascita e ritorno degli eroi nel Marvel Universe"
    if n<=249: return "Waid / Wieringo","Fantascienza, famiglia e avventura nel ciclo moderno di Mark Waid e Mike Wieringo"
    if n<=299: return "Civil War / Millar-Hitch","La famiglia attraversa Civil War e il rilancio spettacolare di Millar e Hitch"
    if n<=349: return "Hickman / Future Foundation","Il grande progetto di Jonathan Hickman, dal Consiglio dei Reed alla Future Foundation"
    if n<=399: return "Marvel NOW! / Secret Wars","Dalla fase Fraction al collasso del multiverso e al ritorno della famiglia"
    if n<=449: return "Slott / Reckoning War","Il ritorno dei Fantastici Quattro e la lunga gestione moderna"
    return "Ryan North — era contemporanea","La fase contemporanea della Prima Famiglia Marvel"

def make_issue(n,row,seq):
    era,sub=ff_era(n); code=f"F4_SM_{n:03d}"
    return {"id":f"F4_SM:{n}","seq":seq,"seriesId":"F4_SM","series":"Fantastici Quattro","publisher":"Star Comics / Marvel Italia / Panini Comics","n":n,"name":f"Fantastici Quattro #{n}","title":row["title"] or "Albo del percorso Fantastici Quattro","date":italian_date(row["date"]),"dateQuality":"indice","era":era,"eraSub":sub,"cover":f"https://www.comicsbox.it/cover/{code}.jpg","url":f"https://www.comicsbox.it/albo/{code}","required":True,"skip":False,"instruction":"Segui la testata italiana principale; eventi e serie satellite verranno collegati come percorsi trasversali quando necessari.","coverSource":"ComicsBox"}

def pack(character):
    raw=json.dumps(character,ensure_ascii=False,separators=(",",":")).encode(); enc=base64.b64encode(gzip.compress(raw,compresslevel=9,mtime=0)).decode("ascii")
    for old in (DATA/"b64").glob("fantastic-four-*.b64"): old.unlink()
    parts=[enc[i:i+CHUNK_SIZE] for i in range(0,len(enc),CHUNK_SIZE)]; sources=[]
    for idx,part in enumerate(parts,1):
        rel=f"data/b64/fantastic-four-{idx:02d}.b64"; (ROOT/rel).write_text(part,encoding="ascii"); sources.append(rel)
    (DATA/"encoded"/"fantastic-four.json").write_text(json.dumps({"encoding":"gzip-base64-parts","sources":sources},separators=(",",":")),encoding="utf-8")
    print(f"Fantastici Quattro: {len(character['issues'])} albi, {len(raw):,} byte, {len(parts)} parti")

def main():
    rows=fetch_all_series("F4_SM",12); current=max(rows)
    if current<475: raise RuntimeError(f"Indice Fantastici Quattro inatteso: ultimo numero {current}")
    missing=[n for n in range(1,current+1) if n not in rows]
    if missing: raise RuntimeError(f"Fantastici Quattro: numeri mancanti {missing[:20]}")
    issues=[make_issue(n,rows[n],n) for n in range(1,current+1)]
    character={"id":"fantastic-four","name":"Fantastici Quattro","subtitle":"La Prima Famiglia Marvel","accent":"#4ca9ff","start":"Fantastici Quattro #1 — Ottobre 1988 · storie dal 1981","end":f"Fantastici Quattro #{current} — {italian_date(rows[current]['date'])}","description":"Percorso italiano principale dei Fantastici Quattro dalla seconda serie Star Comics del 1988 fino alla pubblicazione corrente. Parte da Fantastic Four vol.1 #229; la fondazione classica Lee/Kirby verrà collegata come blocco storico separato, evitando di mescolare ristampe e albo fisico moderno.","timelineMode":True,"series":[{"id":"F4_SM","name":"Fantastici Quattro","publisher":"Star Comics / Marvel Italia / Panini Comics","range":f"#1–{current}","years":f"1988–{re.search(r'(?:19|20)\d{2}',rows[current]['date']).group(0)}"}],"archives":[],"totalRequired":len(issues),"availableTotal":len(issues),"issues":issues}
    pack(character)
    stub={k:v for k,v in character.items() if k not in {"issues","availableTotal"}}; stub["issueSources"]=["data/encoded/fantastic-four.json"]
    (DATA/"characters"/"fantastic-four.json").write_text(json.dumps(stub,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    manifest_path=DATA/"characters.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8")); manifest["version"]=MANIFEST_VERSION
    meta={"id":"fantastic-four","name":"Fantastici Quattro","subtitle":"La Prima Famiglia Marvel","type":"team","primaryHub":"fantastic-four","hubs":["fantastic-four"],"accent":"#4ca9ff","logo":"assets/heroes/fantastic-four.svg","data":"data/characters/fantastic-four.json","start":character["start"],"end":character["end"],"totalRequired":character["totalRequired"]}
    chars=[c for c in manifest["characters"] if c["id"]!="fantastic-four"]; chars.append(meta); manifest["characters"]=chars
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    hubs_path=DATA/"hubs.json"; hubs=json.loads(hubs_path.read_text(encoding="utf-8")); hub=next(h for h in hubs["hubs"] if h["id"]=="fantastic-four"); hub.pop("status",None); hub["featuredPath"]="fantastic-four"; hub["groups"]=[{"id":"core","label":"Percorso principale","paths":["fantastic-four"]}]; hubs_path.write_text(json.dumps(hubs,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (ROOT/"assets"/"heroes"/"fantastic-four.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="Fantastici Quattro"><rect width="128" height="128" rx="26" fill="#07121f"/><circle cx="64" cy="64" r="47" fill="none" stroke="#4ca9ff" stroke-width="7"/><path d="M71 29 37 71v13h31v15h15V84h12V69H83V29H71Zm-3 40H54l14-18v18Z" fill="#eef7ff"/></svg>',encoding="utf-8")
    print(f"Percorso Fantastici Quattro generato: {len(issues)} tappe")

if __name__=="__main__": main()
