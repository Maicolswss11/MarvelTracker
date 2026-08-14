#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";

const readJson = async path => JSON.parse(await readFile(path, "utf8"));
const manifest = await readJson("data/characters.json");
const spec = await readJson("data/encoded/avengers.json");
const encoded = (await Promise.all(spec.sources.map(source => readFile(source, "utf8")))).join("").replace(/\s+/g, "");
const path = JSON.parse(gunzipSync(Buffer.from(encoded, "base64")).toString("utf8"));
const source = await readJson("data/avengers-classic-sources.json");
const audit = await readJson("data/avengers-classic-audit.json");
const catalog = await readJson("data/catalog.json");
const editions = await readJson("data/curated-editions.json");
const app = await readFile("js/app.js", "utf8");

assert.equal(source.issues.length, 298, "avengers: audit USA #1-298 incompleto");
assert.ok(Object.keys(source.physicalPublications).length >= 270, "avengers: parti fisiche italiane non tutte censite");
assert.equal(path.issues[0].physicalId, "THOR_C1:5", "avengers: il percorso non parte da Il mitico Thor #5");
assert.deepEqual(path.issues[0].readingStep.contentIds, ["AV1_001"], "avengers: Avengers #1 non è la prima lettura");
assert.match(path.start, /Il mitico Thor #5/, "avengers: metadato iniziale obsoleto");

const byContent = new Map();
for (const issue of path.issues) {
  for (const contentId of issue.readingStep?.contentIds || []) {
    const rows = byContent.get(contentId) || [];
    rows.push(issue);
    byContent.set(contentId, rows);
  }
}
for (let number = 1; number <= 298; number += 1) {
  const contentId = `AV1_${String(number).padStart(3, "0")}`;
  assert.ok(byContent.has(contentId), `avengers: ${contentId} mancante`);
}

function firstPublicationCodes(row) {
  const codes = [];
  for (const publication of row.italianPublications) {
    if (!codes.includes(publication.id)) codes.push(publication.id);
    if (publication.publisher || publication.date) break;
  }
  return codes;
}
function physicalId(code) {
  const match = code.match(/^(.+)_([0-9]+)([A-Za-z]?)$/);
  return match ? `${match[1]}:${Number(match[2])}${match[3].toUpperCase()}` : code;
}
for (const row of source.issues) {
  const contentId = row.id;
  const routes = byContent.get(contentId) || [];
  for (const code of firstPublicationCodes(row)) {
    assert.ok(routes.some(issue => issue.physicalId === physicalId(code)), `${contentId}: parte italiana ${code} mancante`);
  }
}

const wca = path.issues.find(issue => issue.id === "SPE_VCO_S:1");
const av250 = byContent.get("AV1_250")[0];
assert.ok(wca && wca.seq < av250.seq, "avengers: origine della Costa Ovest non inserita prima di Avengers #250");
assert.deepEqual(wca.readingStep.contentIds, ["WCA1_001", "WCA1_002", "WCA1_003", "WCA1_004"], "avengers: miniserie Costa Ovest incompleta");

const v1 = path.issues.find(issue => issue.id === "VEN_M:1");
const v0 = path.issues.find(issue => issue.id === "VEN_M:0");
assert.ok(v1.seq < v0.seq, "avengers: Vendicatori #0 precede ancora Avengers #299-300");
assert.deepEqual(v1.readingStep.contentIds, ["AV1_299", "AV1_300"], "avengers: passaggio al #299 non mappato");
assert.ok(!v0.readingStep.contentIds.includes("AV1_300"), "avengers: il riassunto duplicato di Avengers #300 è ancora obbligatorio");
assert.match(v0.instruction, /Quasar è Wendell Vaughn/, "avengers: contesto di Quasar mancante");

const routeIds = path.issues.map(issue => issue.id);
assert.equal(new Set(routeIds).size, routeIds.length, "avengers: id di tappa duplicati");
assert.equal(path.totalRequired, path.issues.filter(issue => issue.required !== false && !issue.future).length, "avengers: totale incoerente");
assert.equal(manifest.characters.find(item => item.id === "avengers").totalRequired, path.totalRequired, "avengers: manifest incoerente");
assert.equal(audit.totalRouteSegments, path.issues.length, "avengers: audit non aggiornato");

const repeated = path.issues.filter(issue => issue.physicalId && issue.id !== issue.physicalId);
assert.ok(repeated.length > 0, "avengers: nessun segmento fisico condiviso rilevato");
for (const issue of repeated) {
  assert.ok(catalog.issues.some(item => item.id === issue.physicalId), `${issue.id}: albo fisico assente dal catalogo`);
  assert.ok(!catalog.issues.some(item => item.id === issue.id), `${issue.id}: segmento contato come secondo albo fisico`);
}
assert.match(app, /function physicalIssueId\(/, "avengers: UI senza condivisione dello stato fisico");

const masterworks = editions.editions.find(item => item.id === "MMW_M:3");
assert.ok(masterworks?.coverage?.some(item => item.path === "avengers" && item.issueIds.includes(path.issues[0].id)), "avengers: ristampa Marvel Masterworks vol. 1 non collegata");

console.log(`Vendicatori: ${audit.usaMainIssues} capitoli classici, ${audit.classicPhysicalPublications} albi fisici, ${path.issues.length} tappe totali — OK`);
