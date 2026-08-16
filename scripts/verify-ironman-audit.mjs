#!/usr/bin/env node
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const readJson = async path => JSON.parse(await readFile(path, "utf8"));
const character = await readJson("data/characters/ironman.json");
const audit = await readJson("data/ironman-audit.json");
const alternatives = await readJson("data/ironman-alternatives-audit.json");
const editions = await readJson("data/editions.json");

assert.equal(character.id, "ironman");
assert.equal(character.editorialModel, "physical-issue/usa-contents/reading-step@1");
assert.equal(character.storyIdentityModel, "comicsbox-story-feature@2");
assert.equal(audit.status, "audited");
assert.equal(audit.storyIdentityModel, "comicsbox-story-feature@2");
assert.equal(alternatives.coverageModel, "comicsbox-story-feature@2");

const first = character.issues[0];
assert.ok(first, "ironman: percorso vuoto");
assert.match(first.url || "", /\/ID1_086$/, "ironman: la prima tappa non è L'Incredibile Devil #86");
assert.ok(!first.id.startsWith("IM_VEN:"), "ironman: il percorso parte ancora da Iron Man e i Vendicatori");
const firstIds = first.readingStep?.contentIds || [];
assert.ok(firstIds.length >= 2, "ironman: Iron Man #1 non espone entrambe le feature pubblicate in ID1 #86");
assert.ok(firstIds.every(id => id.startsWith("ironman-story:IM1_001:")), "ironman: la prima tappa contiene materiale non appartenente a Iron Man #1");

const mappings = audit.mappings || [];
const gaps = mappings.filter(row => !row.physicalId);
const actualGapCodes = [...new Set(gaps.map(row => row.usaCode))].sort();
const expectedGapCodes = [
  ...Array.from({length: 10}, (_, index) => `IM1_${String(183 + index).padStart(3, "0")}`),
  ...Array.from({length: 14}, (_, index) => `IM1_${String(201 + index).padStart(3, "0")}`),
  "IM1_255",
  "IM1_257",
].sort();
assert.deepEqual(actualGapCodes, expectedGapCodes, "ironman: elenco attuale delle lacune italiane inatteso");

const issue183 = mappings.find(row => row.usaCode === "IM1_183");
assert.ok(issue183, "ironman: Iron Man #183 non censito");
assert.equal(issue183.italianAlbum, null, "ironman: Iron Man #183 ha ancora una falsa pubblicazione italiana");
assert.equal(issue183.physicalId, null, "ironman: Iron Man #183 non deve creare un albo fisico");
assert.ok(
  character.coverage?.sourceMappingOverrides?.some(row => row.usaIssue === 183 && row.discardedItalianAlbum === "SUPEROICLA_488"),
  "ironman: correzione del boundary #183/SEC #488 non documentata",
);

const issue178Rows = mappings.filter(row => row.usaCode === "IM1_178");
assert.equal(issue178Rows.length, 2, "ironman: Iron Man #178 non conserva esattamente le due story feature");
assert.ok(issue178Rows.some(row => row.italianAlbum === "MARVGEEKS_019"), "ironman: storia principale #178 non usa Marvel Geeks #19");
assert.ok(issue178Rows.some(row => row.italianAlbum === "SUPEROICLA_475"), "ironman: Struggle! non usa Super Eroi Classic #475");
assert.ok(issue178Rows.every(row => row.physicalId), "ironman: una feature di #178 viene ancora trattata come inedita");

const routeStories = [];
for (const issue of character.issues) {
  const byId = new Map((issue.contents || []).map(content => [content.id, content]));
  for (const id of issue.readingStep?.contentIds || []) {
    if (!String(id).startsWith("ironman-story:")) continue;
    const content = byId.get(id);
    if (!content?.sourceIssueId) continue;
    routeStories.push({
      id,
      sourceIssueId: content.sourceIssueId,
      title: content.storyTitle || content.title,
      routeId: issue.id,
      physicalId: issue.physicalId || issue.id,
    });
  }
}
const positions178 = routeStories.map((row, index) => row.sourceIssueId === "IM1_178" ? index : -1).filter(index => index >= 0);
assert.equal(positions178.length, 2, "ironman: #178 non produce due feature nel reading order");
assert.equal(positions178[1], positions178[0] + 1, "ironman: le due feature di #178 non sono consecutive");
assert.equal(routeStories[positions178[0] - 1]?.sourceIssueId, "IM1_177", "ironman: #178 non segue #177");
assert.equal(routeStories[positions178[1] + 1]?.sourceIssueId, "IM1_179", "ironman: #179 non segue entrambe le feature di #178");
const two178 = positions178.map(index => routeStories[index]);
assert.equal(new Set(two178.map(row => row.physicalId)).size, 2, "ironman: le due feature di #178 non usano due pubblicazioni fisiche distinte");
assert.ok(two178.some(row => row.physicalId === "SUPEROICLA:475"), "ironman: SEC #475 non compare nel punto narrativo di #178");
const main178 = two178.find(row => row.physicalId !== "SUPEROICLA:475");
const story179 = routeStories[positions178[1] + 1];
assert.equal(main178?.physicalId, story179?.physicalId, "ironman: il volume Marvel Geeks non riusa lo stesso physicalId dopo l'inserto #178");
assert.notEqual(main178?.routeId, story179?.routeId, "ironman: il volume Marvel Geeks non è segmentato path-local attorno a Struggle!");

for (let n = 154; n <= 157; n += 1) {
  const code = `IM1_${String(n).padStart(3, "0")}`;
  const rows = mappings.filter(row => row.usaCode === code);
  assert.ok(rows.some(row => row.italianAlbum === "MMW_M_176"), `ironman: #${n} non mappato a Marvel Masterworks #176`);
}

assert.ok(!character.issues.some(issue =>
  (issue.contents || []).some(content => content.sourceIssueId === "IM1_076") ||
  (issue.readingStep?.contentIds || []).some(id => String(id).startsWith("ironman-story:IM1_076:"))
), "ironman: Iron Man #76 reprint-only crea ancora una tappa narrativa");
assert.deepEqual(character.coverage?.reprintOnlyIssuesExcluded, [76], "ironman: #76 non documentato come reprint-only escluso");

const tail = character.issues.find(issue => issue.id === "IM_VEN:1");
assert.ok(tail, "ironman: coda moderna Iron Man e i Vendicatori #1 assente");
assert.ok(tail.seq > first.seq, "ironman: coda moderna collocata prima del classico");
assert.ok((tail.readingStep?.contentIds || []).includes("IM1_307"), "ironman: Iron Man e i Vendicatori #1 non aggancia Iron Man vol.1 #307");

const classic306 = character.issues.find(issue =>
  (issue.contents || []).some(content => content.sourceIssueId === "IM1_306") ||
  (issue.readingStep?.contentIds || []).some(id => String(id).startsWith("ironman-story:IM1_306:"))
);
assert.ok(classic306, "ironman: Iron Man vol.1 #306 assente");
assert.ok(classic306.seq < tail.seq, "ironman: giunzione #306 → #307 fuori ordine");

for (const issue of character.issues) {
  const step = issue.readingStep;
  if (!step?.contentIds?.length) continue;
  assert.equal(step.pathId, "ironman", `${issue.id}: readingStep.pathId errato`);
  assert.equal(step.position, issue.seq, `${issue.id}: readingStep.position errato`);
  const contentIds = new Set((issue.contents || []).map(row => row.id));
  for (const id of step.contentIds) {
    assert.ok(contentIds.has(id), `${issue.id}: contentId ${id} non presente nei contents`);
  }
}

function edition(id) {
  const item = editions.editions.find(row => row.id === id);
  assert.ok(item, `ironman: edizione ${id} assente`);
  return item;
}
function coverage(id, issueId) {
  return (edition(id).coverage || []).find(row => row.path === "ironman" && (row.issueIds || []).includes(issueId));
}

const mmw20 = coverage("MMW_M:20", first.id);
assert.ok(mmw20, "ironman: Marvel Masterworks #20 non collegato alla prima tappa");
assert.equal(mmw20.complete, true, "ironman: Marvel Masterworks #20 deve coprire tutto Iron Man #1");
assert.deepEqual(new Set(mmw20.contentIds), new Set(firstIds), "ironman: MMW #20 non copre entrambe le story feature di #1");

const collection17 = coverage("MCOLL_M:17", first.id);
assert.ok(collection17, "ironman: Marvel Collection #17 non collegato alla prima tappa");
assert.equal(collection17.complete, false, "ironman: Marvel Collection #17 non deve essere equivalente completa a Iron Man #1");
assert.ok(collection17.contentIds.length < firstIds.length, "ironman: Marvel Collection #17 non risulta realmente parziale");

const replica14 = coverage("MARVELREP:14", first.id);
assert.ok(replica14, "ironman: Marvel Replica Edition #14 non collegata alla prima tappa");
assert.equal(replica14.complete, false, "ironman: Replica #14 non deve coprire la feature Origini se ComicsBox non la censisce");

assert.ok(alternatives.editionsWithRelevantContents >= 10, "ironman: troppo poche alternative rilevanti");
assert.ok(alternatives.completeStepLinks > 20, "ironman: coperture alternative complete troppo poche");
assert.ok(alternatives.partialStepLinks > 0, "ironman: nessuna copertura parziale rilevata");

console.log(
  `OK: Iron Man audit — ${character.issues.length} reading steps, ` +
  `${audit.classic.stories} story feature classiche, ${actualGapCodes.length} lacune correnti, ` +
  `${alternatives.editionsWithRelevantContents} edizioni alternative rilevanti.`
);
