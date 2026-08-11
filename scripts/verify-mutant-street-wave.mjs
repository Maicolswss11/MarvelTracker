import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const fail = (message) => { throw new Error(message); };

const expected = {
  elektra: { hubs: ['street'] },
  deadpool: { hubs: ['xmen', 'street'] },
  cable: { hubs: ['xmen'] },
  magik: { hubs: ['xmen', 'mystic'] },
};

const manifest = read('data/characters.json');
if (manifest.version < 27) fail(`manifest version ${manifest.version} < 27`);
const metaById = new Map(manifest.characters.map((item) => [item.id, item]));

for (const [id, rule] of Object.entries(expected)) {
  const meta = metaById.get(id);
  if (!meta) fail(`missing manifest path ${id}`);
  if (!meta.mainPath || meta.pathRole !== 'main') fail(`${id}: not a main path`);
  for (const hub of rule.hubs) {
    if (!meta.hubs?.includes(hub)) fail(`${id}: missing hub ${hub}`);
  }

  const character = read(`data/characters/${id}.json`);
  if (!Array.isArray(character.issues) || character.issues.length === 0) fail(`${id}: empty issue list`);
  if (character.totalRequired !== character.issues.filter((issue) => issue.required !== false && !issue.skip).length) {
    fail(`${id}: totalRequired mismatch`);
  }
  const seen = new Set();
  for (const issue of character.issues) {
    if (seen.has(issue.id)) fail(`${id}: duplicate physical issue id ${issue.id}`);
    seen.add(issue.id);
    if (!issue.readingStep || issue.readingStep.pathId !== id) fail(`${id}: invalid readingStep on ${issue.id}`);
    const contentIds = new Set((issue.contents || []).map((content) => content.id));
    if (!Array.isArray(issue.readingStep.contentIds) || issue.readingStep.contentIds.length === 0) {
      fail(`${id}: empty readingStep contents on ${issue.id}`);
    }
    for (const contentId of issue.readingStep.contentIds) {
      if (!contentIds.has(contentId)) fail(`${id}: readingStep content ${contentId} missing from physical issue ${issue.id}`);
    }
  }
}

const audit = read('data/mutant-street-wave-audit.json');
if (audit.manifestVersion !== 27) fail(`audit manifest version ${audit.manifestVersion} != 27`);
if (audit.summary.paths !== 4) fail(`audit path count ${audit.summary.paths} != 4`);
if (audit.summary.sourceErrors !== 0) fail(`source errors: ${audit.summary.sourceErrors}`);
if (audit.summary.filteredTeamStoryErrors !== 0) fail(`filtered team story errors: ${audit.summary.filteredTeamStoryErrors}`);
if (audit.summary.sharedUsStoryErrors !== 0) fail(`shared role scan errors: ${audit.summary.sharedUsStoryErrors}`);

const excluded = new Set(['ULT_DDE', 'ULT_ELK', 'DEPLMAX1', 'DEPLMAX2', 'DPKILMU', 'DPKILMUA', 'DPKMU1LT', 'DP_WWW', 'DPL_PULP', 'WATIFMAGIK']);
for (const row of audit.paths) {
  for (const source of row.sourceSeries || []) {
    if (excluded.has(source.code)) fail(`${row.id}: explicitly excluded source ${source.code} entered the build`);
  }
}

const hubs = read('data/hubs.json');
const hubById = new Map(hubs.hubs.map((hub) => [hub.id, hub]));
const pathsInHub = (hubId) => new Set((hubById.get(hubId)?.groups || []).flatMap((group) => group.paths || []));
if (!pathsInHub('street').has('elektra')) fail('Elektra missing from Street hub');
if (!pathsInHub('street').has('deadpool')) fail('Deadpool missing from Street hub');
if (!pathsInHub('xmen').has('deadpool') || !pathsInHub('xmen').has('cable') || !pathsInHub('xmen').has('magik')) fail('mutant-family hub links incomplete');
if (!pathsInHub('mystic').has('magik')) fail('Magik missing from Mystic hub');

console.log('Elektra/Deadpool/Cable/Magik wave verified.');
