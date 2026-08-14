#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const readJson = async path => JSON.parse(await readFile(path, "utf8"));
const manifest = await readJson("data/characters.json");
const path = await readJson("data/characters/knull.json");
const profiles = await readJson("data/character-profiles.json");
const hubs = await readJson("data/hubs.json");

const meta = manifest.characters.find(item => item.id === "knull");
assert.ok(meta, "knull: voce manifest mancante");
assert.equal(meta.type, "character", "knull: deve aprire la biografia personaggio");
assert.deepEqual(meta.hubs, ["spider", "cosmic"], "knull: hub incompleti");
assert.equal(meta.totalRequired, path.issues.length, "knull: totale manifest incoerente");
assert.equal(path.totalRequired, 41, "knull: numero di albi fisici inatteso");

assert.equal(path.issues[0].id, "THORVE_M:176", "knull: il percorso non parte dalla prima apparizione canonica");
assert.deepEqual(path.issues[0].readingStep.contentIds, ["THORGOT_006"], "knull: Thor #6 non instradato");
assert.ok(path.issues.some(item => item.id === "SILVERBLAC:1"), "knull: Silver Surfer: Nero mancante");
assert.ok(path.issues.some(item => item.id === "GUARDGAL_P:24"), "knull: mitologia Klyntar mancante");
assert.ok(path.issues.some(item => item.id === "MMMI:229"), "knull: conclusione Absolute Carnage mancante");
assert.ok(path.issues.some(item => item.id === "MMMI:246"), "knull: conclusione King in Black mancante");
assert.equal(path.issues.at(-1).id, "VENOMP:105", "knull: ritorno del 2026 mancante");

const ids = path.issues.map(item => item.id);
assert.equal(new Set(ids).size, ids.length, "knull: albo fisico duplicato");
for (const [index, issue] of path.issues.entries()) {
  assert.equal(issue.seq, index + 1, `${issue.id}: sequenza non continua`);
  assert.equal(issue.readingStep.pathId, "knull", `${issue.id}: readingStep su percorso errato`);
  assert.ok(issue.readingStep.contentIds.length > 0, `${issue.id}: contenuti USA non selezionati`);
}

const profile = profiles.profiles.knull;
assert.ok(profile && profile.bio.length >= 500, "knull: biografia completa mancante");
for (const [hubId, groupId] of [["spider", "symbiotes"], ["cosmic", "powers"]]) {
  const hub = hubs.hubs.find(item => item.id === hubId);
  const group = hub?.groups.find(item => item.id === groupId);
  assert.ok(group?.paths.includes("knull"), `knull: assente da ${hubId}/${groupId}`);
}

console.log("Knull: 41 albi, biografia, due hub e collegamenti evento — OK");
