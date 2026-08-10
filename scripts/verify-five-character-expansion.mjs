#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";

const readJson = async path => JSON.parse(await readFile(path,"utf8"));
const manifest = await readJson("data/characters.json");
const hubs = await readJson("data/hubs.json");
const audit = await readJson("data/five-character-audit.json");
const catalog = await readJson("data/catalog.json");
const expected = ["hulk-classic-corno","daredevil","wolverine-616","venom","doctor-doom"];

async function loadCharacter(id){
  const meta=manifest.characters.find(item=>item.id===id);
  assert.ok(meta,`${id}: percorso assente dal manifest`);
  const light=await readJson(meta.data);
  if(!Array.isArray(light.issueSources))return light;
  const spec=await readJson(`data/encoded/${id}.json`);
  const encoded=(await Promise.all(spec.sources.map(source=>readFile(source,"utf8"))))
    .join("").replace(/\s+/g,"");
  return JSON.parse(gunzipSync(Buffer.from(encoded,"base64")).toString("utf8"));
}

assert.equal(manifest.version,23,"versione manifest inattesa");
assert.equal(catalog.manifestVersion,23,"catalogo non rigenerato");
assert.equal(audit.manifestVersion,23,"versione audit inattesa");
assert.deepEqual(audit.pathOrder,expected,"ordine dei cinque percorsi inatteso");
assert.deepEqual(audit.sourceErrors,{},"restano codici-serie USA non validi");
assert.deepEqual(audit.albumErrors,{},"restano errori sui metadati italiani");

const characters={};
for(const id of [...expected,"hulk","spiderman","xmen","fantastic-four","absolute-carnage","king-in-black","secret-wars-1984","secret-wars-2015","ghost-rider"]){
  characters[id]=await loadCharacter(id);
}

for(const id of expected){
  const character=characters[id];
  const meta=manifest.characters.find(item=>item.id===id);
  assert.equal(character.editorialModel,"physical-issue/usa-contents/reading-step@1",`${id}: modello editoriale mancante`);
  assert.ok(character.issues.length>0,`${id}: nessun albo italiano`);
  assert.equal(meta.totalRequired,character.totalRequired,`${id}: totale manifest incoerente`);
  assert.ok(meta.hubs.includes(meta.primaryHub),`${id}: hub primario non dichiarato`);
  const seen=new Set();
  for(const issue of character.issues){
    assert.ok(!seen.has(issue.id),`${id}: albo fisico duplicato ${issue.id}`);
    seen.add(issue.id);
    assert.ok(Array.isArray(issue.contents)&&issue.contents.length>0,`${id}/${issue.id}: contenuti USA mancanti`);
    assert.equal(issue.readingStep.pathId,id,`${id}/${issue.id}: readingStep assegnata al percorso errato`);
    assert.ok(Number.isInteger(issue.readingStep.position),`${id}/${issue.id}: posizione di lettura mancante`);
    assert.ok(issue.readingStep.contentIds.length>0,`${id}/${issue.id}: selezione di lettura vuota`);
    const contentIds=new Set(issue.contents.map(content=>content.id));
    assert.ok(issue.readingStep.contentIds.every(contentId=>contentIds.has(contentId)),`${id}/${issue.id}: selezione fuori dai contenuti fisici`);
  }
}

const byUrl=(id,url)=>characters[id].issues.find(issue=>issue.url===url);
const hed44=byUrl("hulk-classic-corno","https://www.comicsbox.it/albo/HED_044");
assert.ok(hed44,"Hulk Corno: Hulk e i Difensori #44 mancante");
assert.equal(hed44.contentsStatus,"complete","HED #44 deve avere l'indice fisico completo");
const hedContents=new Set(hed44.contents.map(content=>content.id));
for(const id of ["IH2_174","DE1_029","JUWATLAS_056"]){
  assert.ok(hedContents.has(id),`HED #44: contenuto ${id} mancante`);
}
assert.deepEqual(hed44.readingStep.contentIds,["IH2_174"],"HED #44: la tappa Hulk deve selezionare soltanto Hulk #174");
const ur186=byUrl("hulk-classic-corno","https://www.comicsbox.it/albo/UR_C1_186");
assert.ok(ur186?.readingStep.contentIds.includes("IH2_175"),"Hulk #175 non prosegue su L'Uomo Ragno #186");
assert.equal(manifest.characters.find(item=>item.id==="hulk-classic-corno").mainPath,false,"Hulk Corno non deve alterare il percorso moderno");

const ids=id=>new Set(characters[id].issues.map(issue=>issue.id));
const overlap=(left,right)=>[...ids(left)].filter(id=>ids(right).has(id));
for(const [left,right,label] of [
  ["daredevil","hulk","Devil & Hulk"],
  ["venom","spiderman","Spider-Man"],
  ["venom","absolute-carnage","Absolute Carnage"],
  ["venom","king-in-black","King in Black"],
  ["doctor-doom","fantastic-four","Fantastici Quattro"],
  ["doctor-doom","secret-wars-1984","Secret Wars 1984"],
  ["doctor-doom","secret-wars-2015","Secret Wars 2015"],
  ["wolverine-616","ghost-rider","Weapons of Vengeance"],
]){
  assert.ok(overlap(left,right).length>0,`${left}/${right}: deduplica ${label} non rilevata`);
}

const pathsIn=hubId=>new Set((hubs.hubs.find(hub=>hub.id===hubId)?.groups||[]).flatMap(group=>group.paths));
for(const [hubId,pathIds] of [
  ["avengers",["hulk-classic-corno"]],
  ["street",["daredevil"]],
  ["xmen",["wolverine-616"]],
  ["spider",["venom"]],
  ["fantastic-four",["doctor-doom"]],
  ["mystic",["doctor-doom"]],
  ["cosmic",["doctor-doom"]],
]){
  for(const pathId of pathIds)assert.ok(pathsIn(hubId).has(pathId),`${pathId}: collegamento ${hubId} mancante`);
}

const idToUrl=new Map(),urlToId=new Map();
for(const meta of manifest.characters){
  const character=await loadCharacter(meta.id);
  for(const issue of character.issues){
    if(!issue.url?.includes("/albo/"))continue;
    if(idToUrl.has(issue.id))assert.equal(idToUrl.get(issue.id),issue.url,`${issue.id}: stesso ID con URL diversi`);
    if(urlToId.has(issue.url))assert.equal(urlToId.get(issue.url),issue.id,`${issue.url}: stesso albo con ID diversi`);
    idToUrl.set(issue.id,issue.url);urlToId.set(issue.url,issue.id);
  }
}

const app=await readFile("js/app.js","utf8");
assert.match(app,/state\.collection\[id\]/,"Fisico/Digitale non risultano globali per albo");
assert.match(app,/bucket\(\)\[id\]\?\.read/,"Letto non risulta specifico del percorso");
assert.match(app,/readingStep\?\.contentIds/,"la UI non mostra la selezione dei contenuti USA");

console.log(`Espansione personaggi: ${expected.length} percorsi, ${audit.summary.uniqueItalianAlbums} albi italiani, modello editoriale a tre livelli — OK`);
