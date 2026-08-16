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
const gapCodes = new Set(gaps.map(row => row.usaCode));
const map183 = mappings.filter(row => row.usaCode === "IM1_183");
console.log("Iron Man gap IDs:", [...gapCodes].join(", "));
console.log("IM1_183 mapping:", JSON.stringify(map183));
for (let n = 183; n <= 192; n += 1) {
  const code = `IM1_${String(n).padStart(3, "0")}`;
  assert.ok(gapCodes.has(code), `ironman: Iron Man #${n} non risulta tra le lacune italiane; mapping183=${JSON.stringify(map183)}`);
}
assert.ok(gapCodes.has("IM1_255"), "ironman: Iron Man #255 non risulta inedito");
assert.ok(gapCodes.has("IM1_257"), "ironman: Iron Man #257 non risulta inedito");

const struggle = mappings.find(row => row.usaCode === "IM1_178" && /struggle/i.test(row.usaTitle || ""));
assert.ok(struggle, "ironman: backup Struggle! di Iron Man #178 non censito");
assert.equal(struggle.italianAlbum, "SUPEROICLA_475", "ironman: Struggle! non usa la pubblicazione italiana Super Eroi Classic #475");
assert.ok(struggle.physicalId, "ironman: Struggle! viene ancora trattato come inedito");

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
  `OK: Iron Man audit — ${character.issues.length} tappe fisiche, ` +
  `${audit.classic.stories} story rows classiche, ${audit.classic.unmappedStories} lacune, ` +
  `${alternatives.editionsWithRelevantContents} edizioni alternative rilevanti.`
);
