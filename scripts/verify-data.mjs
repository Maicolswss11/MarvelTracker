#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));
const manifest = await readJson("data/characters.json");

assert.equal(manifest.version, 5, "Il manifest deve usare la versione cache v5");
assert.ok(Array.isArray(manifest.characters) && manifest.characters.length > 0, "Manifest personaggi vuoto");

for (const meta of manifest.characters) {
  const stub = await readJson(meta.data);
  let character = stub;
  if (Array.isArray(stub.issueSources)) {
    const spec = await readJson(`data/encoded/${meta.id}.json`);
    assert.equal(spec.encoding, "gzip-base64-parts", `${meta.id}: encoding non valido`);
    assert.ok(Array.isArray(spec.sources) && spec.sources.length > 0, `${meta.id}: parti mancanti`);
    const encoded = (
      await Promise.all(spec.sources.map((source) => readFile(source, "utf8")))
    ).join("").replace(/\s+/g, "");
    character = JSON.parse(gunzipSync(Buffer.from(encoded, "base64")).toString("utf8"));
  }

  assert.equal(character.id, meta.id, `${meta.id}: id archivio errato`);
  assert.ok(Array.isArray(character.issues), `${meta.id}: lista albi mancante`);
  assert.ok(character.issues.length > 0, `${meta.id}: lista albi vuota`);

  const ids = new Set();
  for (const issue of character.issues) {
    assert.equal(typeof issue.id, "string", `${meta.id}: albo senza id`);
    assert.ok(!ids.has(issue.id), `${meta.id}: id duplicato ${issue.id}`);
    ids.add(issue.id);
    assert.ok(Number.isInteger(issue.n) && issue.n >= 0, `${issue.id}: numero non valido`);
    assert.equal(typeof issue.title, "string", `${issue.id}: titolo mancante`);
    assert.equal(typeof issue.date, "string", `${issue.id}: data mancante`);
    assert.match(issue.cover, /^https:\/\/\S+$/, `${issue.id}: cover non valida`);
    assert.match(issue.url, /^https:\/\/\S+$/, `${issue.id}: URL non valido`);
  }

  const available = character.issues.filter((issue) => issue.required !== false && !issue.future).length;
  assert.equal(
    available,
    character.availableTotal ?? character.totalRequired,
    `${meta.id}: totale disponibile incoerente`,
  );
  assert.equal(meta.totalRequired, character.totalRequired, `${meta.id}: totale manifest incoerente`);
  console.log(`${meta.name}: ${character.issues.length} albi, ${available} conteggiati — OK`);
}

console.log("Tutti gli archivi compressi sono integri.");
