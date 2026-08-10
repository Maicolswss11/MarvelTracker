import fs from 'node:fs';

const root = new URL('../', import.meta.url);
const read = (path) => JSON.parse(fs.readFileSync(new URL(path, root), 'utf8'));
const ids = ['hawkeye','blackwidow','luke-cage','iron-fist','jessica-jones','punisher','moon-knight'];
const manifest = read('data/characters.json');
const audit = read('data/street-wave-audit.json');
const hubs = read('data/hubs.json');

if (manifest.version < 26) throw new Error(`manifest version ${manifest.version}, expected >=26`);
const manifestIds = new Set(manifest.characters.map((item) => item.id));
for (const id of ids) {
  if (!manifestIds.has(id)) throw new Error(`missing manifest path ${id}`);
  const data = read(`data/characters/${id}.json`);
  if (!Array.isArray(data.issues) || data.issues.length === 0) throw new Error(`${id}: no physical issues`);
  if (data.totalRequired !== data.issues.filter((issue) => issue.required !== false).length) {
    throw new Error(`${id}: totalRequired mismatch`);
  }
  const seen = new Set();
  for (const issue of data.issues) {
    if (seen.has(issue.id)) throw new Error(`${id}: duplicate physical issue ${issue.id}`);
    seen.add(issue.id);
    if (!issue.url?.includes('comicsbox.it')) throw new Error(`${id}: issue without ComicsBox URL ${issue.id}`);
    const step = issue.readingStep;
    if (!step || step.pathId !== id || !Array.isArray(step.contentIds) || step.contentIds.length === 0) {
      throw new Error(`${id}: invalid readingStep for ${issue.id}`);
    }
    if (!Array.isArray(issue.contents) || issue.contents.length === 0) throw new Error(`${id}: missing USA contents for ${issue.id}`);
    const contentIds = new Set(issue.contents.map((content) => content.id));
    for (const contentId of step.contentIds) {
      if (!contentIds.has(contentId)) throw new Error(`${id}: readingStep selects unknown content ${contentId}`);
    }
  }
}

if (audit.manifestVersion !== 26 || audit.editorialModel !== 'physical-issue/usa-contents/reading-step@1') {
  throw new Error('street wave audit does not declare the expected editorial model/version');
}
for (const id of ids) {
  const row = audit.paths.find((item) => item.id === id);
  if (!row) throw new Error(`audit missing ${id}`);
  if (!Number.isInteger(row.mappedChapters) || row.mappedChapters <= 0) throw new Error(`${id}: no mapped chapters`);
}

const byHub = new Map(hubs.hubs.map((hub) => [hub.id, hub]));
const pathsInHub = (hubId) => new Set((byHub.get(hubId)?.groups || []).flatMap((group) => group.paths || []));
for (const id of ids) {
  if (!pathsInHub('street').has(id)) throw new Error(`street hub missing ${id}`);
}
for (const id of ['hawkeye','blackwidow','luke-cage','jessica-jones','moon-knight']) {
  if (!pathsInHub('avengers').has(id)) throw new Error(`avengers hub missing ${id}`);
}
if (!pathsInHub('mystic').has('moon-knight')) throw new Error('mystic hub missing moon-knight');

const punisher = read('data/characters/punisher.json');
if (!punisher.continuityPolicy?.includes('Earth-616')) throw new Error('punisher continuity policy missing');

console.log(`Street wave OK: ${ids.length} paths, ${ids.reduce((sum,id) => sum + read(`data/characters/${id}.json`).issues.length, 0)} physical-path entries`);
