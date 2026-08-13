import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const manifest = read("data/characters.json");
const hubs = read("data/hubs.json");
const catalog = read("data/catalog.json");
const characterProfiles = read("data/character-profiles.json").profiles || {};
const editorialProfiles = read("data/editorial-profiles.json").profiles || {};
const audit = read("data/what-if-audit.json");

const expected = [
  "what-if",
  "what-if-classic",
  "what-if-miles-morales",
  "what-if-venom",
  "what-if-dark",
  "avengers-1950s-what-if",
  "what-if-kree-skrull-war",
];
const expectedTypes = {
  "what-if": "universe",
  "what-if-classic": "collection",
  "what-if-miles-morales": "character",
  "what-if-venom": "character",
  "what-if-dark": "collection",
  "avengers-1950s-what-if": "team",
  "what-if-kree-skrull-war": "event",
};
const expectedTotals = {
  "what-if": 6,
  "what-if-classic": 3,
  "what-if-miles-morales": 1,
  "what-if-venom": 1,
  "what-if-dark": 1,
  "avengers-1950s-what-if": 1,
  "what-if-kree-skrull-war": 1,
};

const errors = [];
const manifestById = new Map(manifest.characters.map(row => [row.id, row]));
const paths = new Map();

for (const id of expected) {
  const meta = manifestById.get(id);
  if (!meta) {
    errors.push(`${id}: assente dal manifest`);
    continue;
  }
  if (meta.type !== expectedTypes[id]) errors.push(`${id}: tipo ${meta.type}, atteso ${expectedTypes[id]}`);
  if (meta.primaryHub !== "what-if" || !meta.hubs?.includes("what-if")) errors.push(`${id}: hub What If non assegnato`);
  const data = read(meta.data);
  paths.set(id, data);
  const required = data.issues.filter(issue => issue.required !== false && !issue.future).length;
  if (required !== expectedTotals[id] || required !== data.totalRequired || required !== meta.totalRequired) {
    errors.push(`${id}: totale incoerente (${required}/${data.totalRequired}/${meta.totalRequired})`);
  }
  if (new Set(data.issues.map(issue => issue.id)).size !== data.issues.length) {
    errors.push(`${id}: volume fisico duplicato nel percorso`);
  }
  for (const issue of data.issues) {
    const available = new Set((issue.contents || []).map(item => item.id));
    for (const contentId of issue.readingStep?.contentIds || []) {
      if (!available.has(contentId)) errors.push(`${id}/${issue.id}: contenuto ${contentId} non dichiarato`);
    }
  }
}

const alternate = hubs.hubs.find(hub => hub.id === "alternate");
const universe = hubs.hubs.find(hub => hub.id === "what-if");
if (!alternate?.sections?.some(section => section.items?.includes("what-if"))) {
  errors.push("alternate: portale What If non collegato");
}
if (universe?.parent !== "alternate") errors.push("what-if: gerarchia hub non valida");
const hubPathIds = new Set(universe?.groups?.flatMap(group => group.paths || []) || []);
for (const id of expected) if (!hubPathIds.has(id)) errors.push(`${id}: assente dai gruppi dell'hub`);

const master = paths.get("what-if");
const expectedPhysical = [
  "MARVGEEKS:17",
  "MARVGEEKS:33",
  "MVNWCOL_P:436",
  "MARVGEEKS:35",
  "MVNWCOL_P:567",
  "MVNWCOL_P:603",
];
if (master) {
  const physical = new Set(master.issues.map(issue => issue.id));
  for (const id of expectedPhysical) if (!physical.has(id)) errors.push(`what-if: manca ${id}`);
  for (const [id, data] of paths) {
    if (id === "what-if") continue;
    for (const issue of data.issues) if (!physical.has(issue.id)) errors.push(`${id}/${issue.id}: volume assente dal master`);
  }

  const masterContents = new Map(master.issues.map(issue => [issue.id, new Set(issue.contents.map(item => item.id))]));
  for (const [id, data] of paths) {
    if (id === "what-if") continue;
    for (const issue of data.issues) {
      const available = masterContents.get(issue.id) || new Set();
      for (const item of issue.contents) {
        if (!available.has(item.id)) errors.push(`${id}/${issue.id}: ${item.id} non appartiene al master`);
      }
    }
  }
}

const requiredContents = {
  "what-if-classic": ["WHIF1:1", "WHIF1:12", "WHIF1:14", "WHIF1:20"],
  "what-if-miles-morales": ["WHATIFMM:1", "WHATIFMM:5"],
  "what-if-venom": ["WIFVENOM:1", "WIFVENOM:5"],
  "what-if-dark": ["WIFDARKLOK:1", "WIFDARKTOD:1"],
  "avengers-1950s-what-if": ["WHIF1:9"],
  "what-if-kree-skrull-war": ["WHIF1:20"],
};
for (const [id, contentIds] of Object.entries(requiredContents)) {
  const actual = new Set(paths.get(id)?.issues.flatMap(issue => issue.contents || []).map(item => item.id) || []);
  for (const contentId of contentIds) if (!actual.has(contentId)) errors.push(`${id}: manca ${contentId}`);
}

for (const id of ["what-if-miles-morales", "what-if-venom"]) {
  const profile = characterProfiles[id];
  if (!profile || (profile.bio || "").length < 300) errors.push(`${id}: biografia mancante o troppo breve`);
}
for (const id of ["avengers-1950s-what-if", "what-if-kree-skrull-war"]) {
  const profile = editorialProfiles[id];
  if (!profile || profile.type !== expectedTypes[id] || (profile.bio || "").length < 300) {
    errors.push(`${id}: dossier mancante, errato o troppo breve`);
  }
}

const catalogById = new Map(catalog.issues.map(issue => [issue.id, issue]));
for (const id of expectedPhysical) {
  const issue = catalogById.get(id);
  if (!issue) errors.push(`${id}: assente dal catalogo globale`);
}
const sharedExpectations = {
  "MARVGEEKS:33": ["what-if", "what-if-classic", "avengers-1950s-what-if"],
  "MARVGEEKS:35": ["what-if", "what-if-classic", "what-if-kree-skrull-war"],
  "MVNWCOL_P:436": ["what-if", "what-if-miles-morales"],
  "MVNWCOL_P:567": ["what-if", "what-if-dark"],
  "MVNWCOL_P:603": ["what-if", "what-if-venom"],
};
for (const [issueId, pathIds] of Object.entries(sharedExpectations)) {
  const catalogPaths = new Set(catalogById.get(issueId)?.paths || []);
  for (const pathId of pathIds) if (!catalogPaths.has(pathId)) errors.push(`${issueId}: manca il riuso in ${pathId}`);
}

if (audit.physicalIssues !== 6 || audit.usaStories !== 34) {
  errors.push(`audit: conteggi inattesi (${audit.physicalIssues} volumi, ${audit.usaStories} storie)`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("OK: What If...? — 1 portale, 2 personaggi, 1 squadra, 1 evento, 2 raccolte e 6 volumi italiani condivisi senza duplicati.");
