#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";

const readJson = async file => JSON.parse(await readFile(file, "utf8"));
const manifest = await readJson("data/characters.json");
const spec = await readJson("data/encoded/avengers.json");
const encoded = (await Promise.all(spec.sources.map(file => readFile(file, "utf8")))).join("").replace(/\s+/g, "");
const path = JSON.parse(gunzipSync(Buffer.from(encoded, "base64")).toString("utf8"));
const source = await readJson("data/avengers-classic-sources.json");
const supplements = await readJson("data/avengers-classic-supplements.json");
const audit = await readJson("data/avengers-classic-audit.json");
const catalog = await readJson("data/catalog.json");
const editions = await readJson("data/curated-editions.json");
const app = await readFile("js/app.js", "utf8");
const editionsJs = await readFile("js/editions.js", "utf8");

assert.equal(source.issues.length, 298, "avengers: sorgente regolare USA #1-298 incompleta");
assert.ok(Object.keys(source.physicalPublications).length >= 270, "avengers: parti fisiche italiane regolari non tutte censite");
assert.equal(supplements.issues.length, 40, "avengers: Annual/crossover diretti incompleti");
assert.equal(supplements.editorialModel, "physical-issue/usa-contents/reading-step@1", "avengers: modello editoriale supplementi inatteso");

assert.equal(path.issues[0].physicalId, "THOR_C1:5", "avengers: il percorso non parte da Il mitico Thor #5");
assert.deepEqual(path.issues[0].readingStep.contentIds, ["AV1_001"], "avengers: Avengers #1 non è la prima lettura");
assert.match(path.start, /Avengers \(1963\) #1/, "avengers: metadato iniziale obsoleto");
assert.match(path.description, /formazione causata da Loki/, "avengers: fondazione originale non documentata");
assert.equal(path.auditStatus, "audited", "avengers: percorso non marcato auditato");
assert.equal(path.auditKind, "path/team", "avengers: audit di team confuso con un evento completo");

const routeById = new Map(path.issues.map(issue => [issue.id, issue]));
assert.equal(routeById.size, path.issues.length, "avengers: id di tappa duplicati");
for (const issue of path.issues) {
  assert.equal(issue.seq, issue.readingStep?.position ?? issue.seq, `${issue.id}: readingStep.position incoerente`);
  if (issue.contents?.length) {
    assert.equal(issue.readingStep?.pathId, "avengers", `${issue.id}: readingStep.pathId mancante`);
    assert.deepEqual(issue.readingStep.contentIds, issue.contents.map(content => content.id), `${issue.id}: readingStep non corrisponde ai contenuti selezionati`);
  }
}

const byContent = new Map();
for (const issue of path.issues) {
  for (const contentId of issue.readingStep?.contentIds || []) {
    const rows = byContent.get(contentId) || [];
    rows.push(issue);
    byContent.set(contentId, rows);
  }
}

function firstPublicationCodes(row) {
  if (row.primaryPublicationIds?.length) return row.primaryPublicationIds;
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

function assertPrimaryMapping(row) {
  const routes = byContent.get(row.id) || [];
  assert.ok(routes.length, `avengers: ${row.id} mancante dal percorso`);
  for (const code of firstPublicationCodes(row)) {
    assert.ok(routes.some(issue => issue.physicalId === physicalId(code)), `${row.id}: parte italiana primaria ${code} mancante`);
  }
}

for (const row of source.issues) assertPrimaryMapping(row);
for (const row of supplements.issues) assertPrimaryMapping(row);
for (let number = 1; number <= 300; number += 1) {
  assert.ok(byContent.has(`AV1_${String(number).padStart(3, "0")}`), `avengers: AV1_${String(number).padStart(3, "0")} mancante`);
}

// Compare the complete logical sequence, collapsing only repeated physical
// halves of the same USA chapter.
const extrasByAnchor = new Map();
for (const row of supplements.issues) {
  const rows = extrasByAnchor.get(row.after) || [];
  rows.push(row);
  extrasByAnchor.set(row.after, rows);
}
for (const rows of extrasByAnchor.values()) rows.sort((a, b) => (a.order || 0) - (b.order || 0) || a.id.localeCompare(b.id));
const expectedOrder = [];
for (const row of source.issues) {
  expectedOrder.push(row.id);
  expectedOrder.push(...(extrasByAnchor.get(row.id) || []).map(extra => extra.id));
}
expectedOrder.push("AV1_299", "AV1_300");
const expectedSet = new Set(expectedOrder);
const actualOrder = [];
for (const issue of path.issues) {
  if (issue.id === "VEN_M:0") break;
  for (const contentId of issue.readingStep?.contentIds || []) {
    if (!expectedSet.has(contentId)) continue;
    if (actualOrder.at(-1) !== contentId) actualOrder.push(contentId);
  }
}
assert.deepEqual(actualOrder, expectedOrder, "avengers: ordine cronologico completo USA errato");
assert.equal(expectedOrder.length, 340, "avengers: perimetro USA classico inatteso");

const reprint136 = byContent.get("AV1_136")[0];
assert.equal(reprint136.required, false, "avengers: #136 reprint-only ancora obbligatorio");
assert.equal(reprint136.skip, true, "avengers: #136 non marcato facoltativo");
assert.equal(reprint136.reprintOnly, true, "avengers: natura di ristampa del #136 non dichiarata");
const issue150 = byContent.get("AV1_150")[0];
assert.equal(issue150.partialReprint, true, "avengers: materiale ristampato del #150 non segnalato");
assert.match(issue150.instruction, /pagine di raccordo nuove/, "avengers: istruzione di lettura selettiva del #150 mancante");

const wcaOrder = ["AV1_248", "WCA1_001", "IMA_007", "WCA1_002", "AV1_249", "WCA1_003", "WCA1_004", "AV1_250"];
const wcaPositions = wcaOrder.map(id => expectedOrder.indexOf(id));
assert.ok(wcaPositions.every((value, index) => index === 0 || value > wcaPositions[index - 1]), "avengers: fondazione West Coast non nella sequenza narrativa verificata");
assert.equal(new Set(["WCA1_001", "WCA1_002", "WCA1_003", "WCA1_004"].flatMap(id => byContent.get(id).map(issue => issue.physicalId))).size, 1, "avengers: miniserie West Coast non riusa un solo ID fisico");

const bronzeTransition = ["AV1_125", "CM1_033", "AV1_126", "GSA_001", "AV1_127", "F41_150", "AV1_128", "AV1_129", "GSA_002"];
const bronzePositions = bronzeTransition.map(id => expectedOrder.indexOf(id));
assert.ok(bronzePositions.every((value, index) => index === 0 || value > bronzePositions[index - 1]), "avengers: transizione Thanos / Giant-Size / nozze Inumane fuori ordine");

const v1 = routeById.get("VEN_M:1");
const v0 = routeById.get("VEN_M:0");
assert.ok(v1.seq < v0.seq, "avengers: Vendicatori #0 precede ancora Avengers #299-300");
assert.deepEqual(v1.readingStep.contentIds, ["AV1_299", "AV1_300"], "avengers: passaggio al #299-300 non mappato");
assert.equal(v0.required, false, "avengers: Annual #18 legacy altera ancora il progresso obbligatorio");
assert.equal(v0.legacyPostCore, true, "avengers: Annual #18 non distinto dal nucleo auditato");
assert.ok(v0.readingStep.contentIds.includes("AV1A_018"), "avengers: ID bibliografico di Annual #18 errato");
assert.ok(!v0.readingStep.contentIds.includes("AV1_300"), "avengers: riassunto duplicato di Avengers #300 ancora selezionato");

assert.equal(path.totalRequired, path.issues.filter(issue => issue.required !== false && !issue.future).length, "avengers: totale richiesto incoerente");
const manifestEntry = manifest.characters.find(item => item.id === "avengers");
assert.equal(manifestEntry.totalRequired, path.totalRequired, "avengers: manifest incoerente");
assert.equal(manifestEntry.auditStatus, "audited", "avengers: manifest non marcato auditato");
assert.equal(manifestEntry.auditKind, "path/team", "avengers: tipo audit manifest errato");

assert.equal(audit.version, 2, "avengers: audit legacy non aggiornato");
assert.equal(audit.status, "audited", "avengers: audit non concluso");
assert.equal(audit.auditKind, "path/team", "avengers: audit di percorso non distinto dagli eventi");
assert.equal(audit.editorialModel, "physical-issue/usa-contents/reading-step@1", "avengers: modello editoriale audit errato");
assert.deepEqual(audit.mainSeriesRange, { series: "Avengers vol. 1", from: 1, to: 300, mapped: 300 }, "avengers: intervallo regolare audit errato");
assert.equal(audit.mainSeriesNarrativeRequired, 299, "avengers: #136 non escluso dal conteggio narrativo");
assert.equal(audit.supplementalUsIssues, 40, "avengers: conteggio supplementi errato");
assert.equal(audit.requiredUsChapters, 339, "avengers: conteggio capitoli USA richiesti errato");
assert.deepEqual(audit.remainingCoreGaps, [], "avengers: restano buchi nel nucleo dichiarato auditato");
assert.equal(audit.totalRouteSegments, path.issues.length, "avengers: audit non sincronizzato con il percorso");
assert.equal(audit.legacyPostCore.routeId, "VEN_M:0", "avengers: confine post-classico non documentato");
assert.ok(audit.sourceConflicts.some(item => /Masterworks/.test(item.subject)), "avengers: conflitto Masterworks/Panini non documentato");

const catalogIds = catalog.issues.map(issue => issue.id);
assert.equal(new Set(catalogIds).size, catalogIds.length, "avengers: ID fisici duplicati nel catalogo globale");
const catalogSet = new Set(catalogIds);
for (const issue of path.issues.filter(issue => issue.auditCore)) {
  assert.ok(catalogSet.has(issue.physicalId), `${issue.id}: albo fisico assente dal catalogo`);
  if (issue.id !== issue.physicalId) assert.ok(!catalogSet.has(issue.id), `${issue.id}: segmento cronologico contato come secondo albo fisico`);
}
assert.match(app, /function physicalIssueId\(/, "avengers: UI senza condivisione dello stato fisico");
assert.match(app, /routeBucket\[id\].*read/, "avengers: Letto non resta specifico della tappa");
assert.match(editionsJs, /state\?\.collection\?\.\[id\]\?\.physical/, "avengers: un ID fisico già posseduto non viene riconosciuto come edizione");
assert.match(app, /coverage\.owned\.length>0/, "avengers: Recuperato non riconosce le edizioni alternative");

const editionIds = editions.editions.map(edition => edition.id);
assert.equal(new Set(editionIds).size, editionIds.length, "avengers: ID di edizione alternativa duplicati");
const allRouteIds = new Set(path.issues.map(issue => issue.id));
for (const edition of editions.editions) {
  for (const coverage of edition.coverage || []) {
    if (coverage.path !== "avengers") continue;
    assert.equal(new Set(coverage.issueIds).size, coverage.issueIds.length, `${edition.id}: coverage Avengers duplicata`);
    for (const routeId of coverage.issueIds) assert.ok(allRouteIds.has(routeId), `${edition.id}: coverage obsoleta ${routeId}`);
  }
}

function edition(id) {
  const result = editions.editions.find(item => item.id === id);
  assert.ok(result, `avengers: edizione ${id} assente`);
  return result;
}

function coverageIds(id) {
  return new Set((edition(id).coverage || []).find(item => item.path === "avengers")?.issueIds || []);
}

function assertEditionCoversContents(id, contentIds) {
  const coverage = coverageIds(id);
  for (const contentId of contentIds) {
    for (const route of byContent.get(contentId) || []) {
      if (!route.auditCore) continue;
      assert.ok(coverage.has(route.id), `${id}: non copre ${contentId} nella tappa ${route.id}`);
    }
  }
}

assertEditionCoversContents("MMW_M:3", Array.from({ length: 11 }, (_, index) => `AV1_${String(index + 1).padStart(3, "0")}`));
assert.ok(!coverageIds("MMW_M:3").has(byContent.get("AV1_012")[0].id), "avengers: MMW_M:3 attribuisce erroneamente Avengers #12");
assertEditionCoversContents("MMW_M:6", Array.from({ length: 13 }, (_, index) => `AV1_${String(index + 12).padStart(3, "0")}`));
assert.ok(!coverageIds("MMW_M:6").has(byContent.get("AV1_011").at(-1).id), "avengers: MMW_M:6 attribuisce erroneamente Avengers #11");

assertEditionCoversContents("MAROMNIB:191", Array.from({ length: 30 }, (_, index) => `AV1_${String(index + 1).padStart(3, "0")}`));
assertEditionCoversContents("MAROMNIB:192", [
  ...Array.from({ length: 28 }, (_, index) => `AV1_${String(index + 31).padStart(3, "0")}`),
  "AV1A_001", "XM1_045", "AV1A_002",
]);
assertEditionCoversContents("MAROMNIB:193", [
  ...Array.from({ length: 30 }, (_, index) => `AV1_${String(index + 59).padStart(3, "0")}`),
  "IH2_140",
]);
assertEditionCoversContents("MARVELMUST:103", ["DE1_008", "DE1_009", "DE1_010", "DE1_011"]);
assertEditionCoversContents("AVENSORO:12", ["WCA1_001", "WCA1_002", "WCA1_003", "WCA1_004"]);
assert.equal(byContent.get("IMA_007")[0].physicalId, "AVENSORO:12", "avengers: Iron Man Annual #7 non riusa l'ID fisico dell'edizione Serie Oro");
assertEditionCoversContents("MAROMNIB:97", ["AV1A_014", "APF1_039", "AV1A_015", "WCAA_001"]);
assert.ok(!coverageIds("MAROMNIB:97").has(byContent.get("APF1_040")[0].id), "avengers: Omnibus Sotto Assedio attribuisce erroneamente Alpha Flight #40");
assertEditionCoversContents("MAROMNIB:115", ["WCAA_002", "AV1A_016", "AV1A_017"]);

console.log(`Vendicatori: Avengers #1-300 + ${audit.supplementalUsIssues} capitoli diretti, ${audit.classicPhysicalPublications} albi fisici classici, ${path.issues.length} tappe totali — OK`);
