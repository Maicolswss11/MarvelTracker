#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";

const readJson = async path => JSON.parse(await readFile(path,"utf8"));
const manifest = await readJson("data/characters.json");
const hubs = await readJson("data/hubs.json");
const audit = await readJson("data/cosmic-supernatural-audit.json");

const expected = [
  "ghost-rider",
  "blade",
  "moon-knight",
  "midnight-sons",
  "morbius",
  "silver-surfer",
  "nova",
  "guardians-of-the-galaxy",
  "adam-warlock",
  "thanos",
  "galactus-heralds",
  "cosmic-ghost-rider",
];

async function loadCharacter(id){
  const meta=manifest.characters.find(item=>item.id===id);
  assert.ok(meta,`${id}: percorso assente dal manifest`);
  const light=await readJson(meta.data);
  if(!Array.isArray(light.issueSources)) return light;
  const spec=await readJson(`data/encoded/${id}.json`);
  const encoded=(await Promise.all(spec.sources.map(source=>readFile(source,"utf8"))))
    .join("").replace(/\s+/g,"");
  return JSON.parse(gunzipSync(Buffer.from(encoded,"base64")).toString("utf8"));
}

assert.equal(manifest.version,22,"versione manifest inattesa");
assert.equal(audit.manifestVersion,22,"versione audit inattesa");
assert.deepEqual(audit.pathOrder,expected,"Cosmic Ghost Rider deve essere costruito per ultimo");
assert.deepEqual(Object.keys(audit.albumErrors),[],"restano errori sui metadati italiani");
assert.deepEqual(Object.keys(audit.sourceErrors),["SS_MO"],"le sorgenti non valide devono limitarsi al record vuoto Silver Surfer Minus One");

const manifestOrder=manifest.characters.map(item=>item.id);
const positions=expected.map(id=>manifestOrder.indexOf(id));
assert.ok(positions.every(index=>index>=0),"uno o più percorsi non sono nel manifest");
assert.deepEqual([...positions].sort((a,b)=>a-b),positions,"ordine dei nuovi percorsi incoerente");

const characters={};
for(const id of [...expected,"fear-itself","infinity-gauntlet"]){
  characters[id]=await loadCharacter(id);
}

const auditById=new Map(audit.paths.map(path=>[path.id,path]));
for(const id of expected){
  const character=characters[id];
  const meta=manifest.characters.find(item=>item.id===id);
  const pathAudit=auditById.get(id);
  assert.ok(character.issues.length>0,`${id}: nessun albo italiano`);
  assert.equal(character.coverage.physicalItalianIssues,character.issues.length,`${id}: conteggio fisico incoerente`);
  assert.equal(character.coverage.mappedChapters,pathAudit.mappedChapters,`${id}: capitoli mappati incoerenti`);
  assert.equal(character.coverage.missingItalianPublications,pathAudit.missingItalianPublications,`${id}: lacune incoerenti`);
  assert.equal(meta.totalRequired,character.totalRequired,`${id}: totale manifest incoerente`);
  assert.ok(meta.hubs.includes(meta.primaryHub),`${id}: hub primario non dichiarato`);
  assert.ok(character.issues.every(issue=>issue.url.includes("/albo/")),`${id}: URL fisico ComicsBox non puntuale`);
}

const ids = id => new Set(characters[id].issues.map(issue=>issue.id));
const overlap = (left,right) => [...ids(left)].filter(id=>ids(right).has(id));
for(const [left,right] of [
  ["ghost-rider","fear-itself"],
  ["silver-surfer","infinity-gauntlet"],
  ["blade","midnight-sons"],
  ["morbius","midnight-sons"],
  ["midnight-sons","ghost-rider"],
  ["adam-warlock","infinity-gauntlet"],
  ["thanos","infinity-gauntlet"],
  ["galactus-heralds","silver-surfer"],
  ["nova","guardians-of-the-galaxy"],
  ["cosmic-ghost-rider","thanos"],
]){
  assert.ok(overlap(left,right).length>0,`${left}/${right}: deduplica fisica non rilevata`);
}

const idToUrl=new Map();
const urlToId=new Map();
for(const meta of manifest.characters){
  const character=await loadCharacter(meta.id);
  for(const issue of character.issues){
    if(!issue.url.includes("/albo/")) continue;
    const previousUrl=idToUrl.get(issue.id);
    if(previousUrl) assert.equal(previousUrl,issue.url,`${issue.id}: stesso ID con URL diversi`);
    idToUrl.set(issue.id,issue.url);
    const previousId=urlToId.get(issue.url);
    if(previousId) assert.equal(previousId,issue.id,`${issue.url}: stesso albo fisico con ID diversi`);
    urlToId.set(issue.url,issue.id);
  }
}

const mystic=hubs.hubs.find(hub=>hub.id==="mystic");
const cosmic=hubs.hubs.find(hub=>hub.id==="cosmic");
const pathsIn = hub => new Set(hub.groups.flatMap(group=>group.paths));
for(const id of ["ghost-rider","blade","moon-knight","midnight-sons","morbius","cosmic-ghost-rider"]){
  assert.ok(pathsIn(mystic).has(id),`${id}: collegamento Mistico mancante`);
}
for(const id of ["silver-surfer","nova","guardians-of-the-galaxy","adam-warlock","thanos","galactus-heralds","cosmic-ghost-rider"]){
  assert.ok(pathsIn(cosmic).has(id),`${id}: collegamento Cosmico mancante`);
}

console.log(`Espansione cosmica/soprannaturale: ${expected.length} percorsi, ${audit.summary.uniqueItalianAlbums} albi italiani, ${audit.summary.crossPathPhysicalOverlaps} overlap — OK`);
