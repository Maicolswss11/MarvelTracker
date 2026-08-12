import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const fail = (message) => { throw new Error(message); };
const norm = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const expected = {
  'new-mutants': {
    requiredSources: ['the new mutants vol 1', 'new mutants vol 4'],
    minChapters: 220,
    maxChapters: 230,
    maxGaps: 5,
  },
  'x-factor': {
    requiredSources: ['x factor vol 1', 'all new x factor'],
    minChapters: 320,
    maxChapters: 335,
    maxGaps: 12,
  },
  'x-force': {
    requiredSources: ['x force vol 1', 'uncanny x force vol 1'],
    minChapters: 340,
    maxChapters: 370,
    maxGaps: 25,
  },
};

const manifest = read('data/characters.json');
if (manifest.version < 29) fail(`manifest version ${manifest.version} < 29`);
const metaById = new Map(manifest.characters.map((item) => [item.id, item]));

for (const id of Object.keys(expected)) {
  const meta = metaById.get(id);
  if (!meta) fail(`missing manifest path ${id}`);
  if (!meta.mainPath || meta.pathRole !== 'main') fail(`${id}: not a main path`);
  if (meta.type !== 'team') fail(`${id}: expected team type, got ${meta.type}`);
  if (meta.primaryHub !== 'xmen' || !meta.hubs?.includes('xmen')) fail(`${id}: missing X-Men hub`);

  const character = read(`data/characters/${id}.json`);
  if (!Array.isArray(character.issues) || character.issues.length === 0) fail(`${id}: empty issue list`);
  const expectedRequired = character.issues.filter((issue) => issue.required !== false && !issue.skip && !issue.future).length;
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

const audit = read('data/mutant-teams-wave1-audit.json');
if (audit.manifestVersion !== 29) fail(`audit manifest version ${audit.manifestVersion} != 29`);
if (audit.summary.paths !== 3) fail(`audit path count ${audit.summary.paths} != 3`);
if (audit.summary.sourceErrors !== 0) fail(`source errors: ${audit.summary.sourceErrors}`);
if (audit.summary.contentEnrichmentErrors !== 0) fail(`content enrichment errors: ${audit.summary.contentEnrichmentErrors}`);
if (audit.summary.albumErrors !== 0) fail(`album errors: ${audit.summary.albumErrors}`);
if (audit.summary.candidateSeries > 60) fail(`source explosion: ${audit.summary.candidateSeries} candidate series`);
if (audit.sourceResolution?.strategy !== 'curated-explicit') fail('unsafe source resolution strategy');

const auditById = new Map(audit.paths.map((row) => [row.id, row]));
for (const [id, rule] of Object.entries(expected)) {
  const row = auditById.get(id);
  if (!row) fail(`${id}: missing audit row`);
  if (row.originalChapters < rule.minChapters || row.originalChapters > rule.maxChapters) {
    fail(`${id}: chapter count ${row.originalChapters} outside ${rule.minChapters}-${rule.maxChapters}`);
  }
  if (row.missingItalianPublications > rule.maxGaps) {
    fail(`${id}: ${row.missingItalianPublications} gaps exceed ${rule.maxGaps}`);
  }
  if (row.physicalItalianIssues < 50 || row.physicalItalianIssues > 350) {
    fail(`${id}: implausible physical issue count ${row.physicalItalianIssues}`);
  }
  const names = (row.sourceSeries || []).map((source) => norm(source.name));
  for (const requiredSource of rule.requiredSources) {
    if (!names.some((name) => name.includes(requiredSource))) {
      fail(`${id}: required source missing (${requiredSource})`);
    }
  }
  for (const source of row.sourceSeries || []) {
    const name = norm(source.name);
    if (name.includes('forever') || name.includes('age of apocalypse') || name.includes('youngblood')) {
      fail(`${id}: alternate/cross-company source entered build: ${source.name}`);
    }
  }
}

const hubs = read('data/hubs.json');
const xmenHub = hubs.hubs.find((hub) => hub.id === 'xmen');
const teams = xmenHub?.groups?.find((group) => group.id === 'teams');
for (const id of Object.keys(expected)) {
  if (!teams?.paths?.includes(id)) fail(`${id}: missing from X-Men teams group`);
}

console.log('New Mutants/X-Factor/X-Force wave verified.');
