import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const fail = (message) => { throw new Error(message); };
const norm = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const expected = {
  cyclops: { hubs: ['xmen'], requiredSource: 'cyclops vol 4' },
  'jean-grey': { hubs: ['xmen'], requiredSource: 'phoenix' },
  storm: { hubs: ['xmen'], requiredSource: 'storm earth s mightiest mutant' },
  rogue: { hubs: ['xmen'], requiredSource: 'rogue the savage land' },
  gambit: { hubs: ['xmen'], requiredSource: 'gambit vol 6' },
};

const manifest = read('data/characters.json');
if (manifest.version < 28) fail(`manifest version ${manifest.version} < 28`);
const metaById = new Map(manifest.characters.map((item) => [item.id, item]));

for (const [id, rule] of Object.entries(expected)) {
  const meta = metaById.get(id);
  if (!meta) fail(`missing manifest path ${id}`);
  if (!meta.mainPath || meta.pathRole !== 'main') fail(`${id}: not a main path`);
  if (meta.primaryHub !== 'xmen') fail(`${id}: primary hub is ${meta.primaryHub}, expected xmen`);
  for (const hub of rule.hubs) {
    if (!meta.hubs?.includes(hub)) fail(`${id}: missing hub ${hub}`);
  }

  const character = read(`data/characters/${id}.json`);
  if (!Array.isArray(character.issues) || character.issues.length === 0) fail(`${id}: empty issue list`);
  const expectedRequired = character.issues.filter((issue) => issue.required !== false && !issue.skip).length;
  if (character.totalRequired !== expectedRequired) fail(`${id}: totalRequired mismatch`);

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
      if (!contentIds.has(contentId)) fail(`${id}: readingStep content ${contentId} missing from ${issue.id}`);
    }
  }
}

const audit = read('data/xmen-wave1-audit.json');
if (audit.manifestVersion !== 28) fail(`audit manifest version ${audit.manifestVersion} != 28`);
if (audit.summary.paths !== 5) fail(`audit path count ${audit.summary.paths} != 5`);
if (audit.summary.sourceErrors !== 0) fail(`source errors: ${audit.summary.sourceErrors}`);
if (audit.summary.filteredTeamStoryErrors !== 0) fail(`filtered team story errors: ${audit.summary.filteredTeamStoryErrors}`);
if (audit.summary.sharedUsStoryErrors !== 0) fail(`shared role scan errors: ${audit.summary.sharedUsStoryErrors}`);
if (!audit.sourceResolution || audit.sourceResolution.paths?.length !== 5) fail('source resolution audit missing');

const auditById = new Map(audit.paths.map((row) => [row.id, row]));
for (const [id, rule] of Object.entries(expected)) {
  const row = auditById.get(id);
  if (!row) fail(`${id}: missing audit row`);
  const names = (row.sourceSeries || []).map((source) => norm(source.name));
  if (!names.some((name) => name.includes('uncanny x men vol 1'))) {
    fail(`${id}: Uncanny X-Men vol 1 protagonist history missing`);
  }
  if (!names.some((name) => name.includes(rule.requiredSource))) {
    fail(`${id}: current/dedicated source missing (${rule.requiredSource})`);
  }
  for (const source of row.sourceSeries || []) {
    const name = norm(source.name);
    const code = String(source.code || '').toUpperCase();
    if (code.startsWith('ULT') || name.includes('what if') || name.includes('age of apocalypse')) {
      fail(`${id}: alternate-continuity source entered build: ${source.name} (${source.code})`);
    }
  }
}

const hubs = read('data/hubs.json');
const xmenHub = hubs.hubs.find((hub) => hub.id === 'xmen');
const xmenPaths = new Set((xmenHub?.groups || []).flatMap((group) => group.paths || []));
for (const id of Object.keys(expected)) {
  if (!xmenPaths.has(id)) fail(`${id}: missing from X-Men hub`);
}

console.log('Cyclops/Jean Grey/Storm/Rogue/Gambit wave verified.');
