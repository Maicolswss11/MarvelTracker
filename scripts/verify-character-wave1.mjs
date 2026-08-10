import fs from 'node:fs';

const root = new URL('../', import.meta.url);
const read = (path) => JSON.parse(fs.readFileSync(new URL(path, root), 'utf8'));
const ids = ['black-cat','quicksilver','falcon','winter-soldier','war-machine','hercules','spider-woman','sentry'];
const manifest = read('data/characters.json');
const audit = read('data/character-wave1-audit.json');
const hubs = read('data/hubs.json');

if (manifest.version < 25) throw new Error(`manifest version ${manifest.version}, expected >=25`);
const manifestIds = new Set(manifest.characters.map((item) => item.id));
for (const id of ids) {
  if (!manifestIds.has(id)) throw new Error(`missing manifest path ${id}`);
  const data = read(`data/characters/${id}.json`);
  if (!Array.isArray(data.issues) || data.issues.length === 0) throw new Error(`${id}: no physical issues`);
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

if (audit.manifestVersion !== 25 || audit.editorialModel !== 'physical-issue/usa-contents/reading-step@1') {
  throw new Error('wave audit does not declare the expected editorial model/version');
}
for (const id of ids) {
  const row = audit.paths.find((item) => item.id === id);
  if (!row) throw new Error(`audit missing ${id}`);
  if (!Number.isInteger(row.mappedChapters) || row.mappedChapters <= 0) throw new Error(`${id}: no mapped chapters`);
}

const byHub = new Map(hubs.hubs.map((hub) => [hub.id, hub]));
const pathsInHub = (hubId) => new Set((byHub.get(hubId)?.groups || []).flatMap((group) => group.paths || []));
for (const id of ['quicksilver','falcon','winter-soldier','war-machine','hercules','spider-woman','sentry']) {
  if (!pathsInHub('avengers').has(id)) throw new Error(`avengers hub missing ${id}`);
}
for (const id of ['black-cat','spider-woman']) {
  if (!pathsInHub('spider').has(id)) throw new Error(`spider hub missing ${id}`);
}
if (!pathsInHub('xmen').has('quicksilver')) throw new Error('xmen hub missing quicksilver');

console.log(`Character wave 1 OK: ${ids.length} paths, ${ids.reduce((sum,id) => sum + read(`data/characters/${id}.json`).issues.length, 0)} physical-path entries`);
