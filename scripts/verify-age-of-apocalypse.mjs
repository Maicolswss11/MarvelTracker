import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const manifest = read("data/characters.json");
const hubs = read("data/hubs.json");
const catalog = read("data/catalog.json");
const art = read("data/ui-art.json");
const characterProfiles = read("data/character-profiles.json").profiles || {};
const editorialProfiles = read("data/editorial-profiles.json").profiles || {};
const audit = read("data/age-of-apocalypse-audit.json");

const expected = [
  "age-of-apocalypse",
  "age-of-apocalypse-event",
  "astonishing-xmen-aoa",
  "amazing-xmen-aoa",
  "gambit-xternals-aoa",
  "generation-next-aoa",
  "weapon-x-aoa",
  "x-calibre-aoa",
  "factor-x-aoa",
  "x-man-aoa",
  "x-universe-aoa",
  "return-age-of-apocalypse",
];
const types = {
  "age-of-apocalypse": "universe",
  "age-of-apocalypse-event": "event",
  "astonishing-xmen-aoa": "team",
  "amazing-xmen-aoa": "team",
  "gambit-xternals-aoa": "team",
  "generation-next-aoa": "team",
  "weapon-x-aoa": "character",
  "x-calibre-aoa": "team",
  "factor-x-aoa": "team",
  "x-man-aoa": "character",
  "x-universe-aoa": "collection",
  "return-age-of-apocalypse": "event",
};
const totals = Object.fromEntries(expected.map(id => [id, 4]));
Object.assign(totals, {
  "age-of-apocalypse": 7,
  "age-of-apocalypse-event": 6,
  "x-universe-aoa": 1,
  "return-age-of-apocalypse": 1,
});

const errors = [];
const manifestById = new Map(manifest.characters.map(row => [row.id, row]));
const paths = new Map();

for (const id of expected) {
  const meta = manifestById.get(id);
  if (!meta) {
    errors.push(`${id}: assente dal manifest`);
    continue;
  }
  if (meta.type !== types[id]) errors.push(`${id}: tipo ${meta.type}, atteso ${types[id]}`);
  if (meta.primaryHub !== "age-of-apocalypse" || !meta.hubs?.includes("age-of-apocalypse")) {
    errors.push(`${id}: hub Terra-295 non assegnato`);
  }
  const data = read(meta.data);
  paths.set(id, data);
  const required = data.issues.filter(issue => issue.required !== false && !issue.future).length;
  if (required !== totals[id] || required !== data.totalRequired || required !== meta.totalRequired) {
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
const universe = hubs.hubs.find(hub => hub.id === "age-of-apocalypse");
if (!alternate?.sections?.some(section => section.items?.includes("age-of-apocalypse"))) {
  errors.push("alternate: portale Era di Apocalisse non collegato");
}
if (universe?.parent !== "alternate") errors.push("age-of-apocalypse: gerarchia hub non valida");
const hubPathIds = new Set(universe?.groups?.flatMap(group => group.paths || []) || []);
for (const id of expected) if (!hubPathIds.has(id)) errors.push(`${id}: assente dai gruppi dell'hub`);

const physicalIds = Array.from({length: 7}, (_, index) => `ERAPOCOL_P:${index + 1}`);
const master = paths.get("age-of-apocalypse");
if (master) {
  const physical = new Set(master.issues.map(issue => issue.id));
  for (const id of physicalIds) if (!physical.has(id)) errors.push(`age-of-apocalypse: manca ${id}`);
  const masterContents = new Map(master.issues.map(issue => [issue.id, new Set(issue.contents.map(item => item.id))]));
  for (const [pathId, data] of paths) {
    if (pathId === "age-of-apocalypse") continue;
    for (const issue of data.issues) {
      if (!physical.has(issue.id)) errors.push(`${pathId}/${issue.id}: volume assente dal master`);
      const available = masterContents.get(issue.id) || new Set();
      for (const item of issue.contents) {
        if (!available.has(item.id)) errors.push(`${pathId}/${issue.id}: ${item.id} non appartiene al master`);
      }
    }
  }
}

const requiredContents = {
  "age-of-apocalypse-event": ["XM_ALPH_001", "XM_ASTO_001", "XM_OMEG_001"],
  "astonishing-xmen-aoa": ["XM_ASTO_001", "XM_ASTO_004"],
  "amazing-xmen-aoa": ["XM_AMAZ_001", "XM_AMAZ_004"],
  "gambit-xternals-aoa": ["GAMXTE_001", "GAMXTE_004"],
  "generation-next-aoa": ["GENEXT_001", "GENEXT_004"],
  "weapon-x-aoa": ["WEAPX1_001", "WEAPX1_004"],
  "x-calibre-aoa": ["XCALIBR_001", "XCALIBR_004"],
  "factor-x-aoa": ["FACTX_001", "FACTX_004"],
  "x-man-aoa": ["XMAN_001", "XMAN_004"],
  "x-universe-aoa": ["XUNIVER_001", "XM_CHRO_001", "XM_OMEG_001"],
  "return-age-of-apocalypse": ["XM_AGAPO_001", "XM_AGAP_001", "XM_AGAP_006"],
};
for (const [id, contentIds] of Object.entries(requiredContents)) {
  const actual = new Set(paths.get(id)?.issues.flatMap(issue => issue.contents || []).map(item => item.id) || []);
  for (const contentId of contentIds) if (!actual.has(contentId)) errors.push(`${id}: manca ${contentId}`);
}

for (const id of ["weapon-x-aoa", "x-man-aoa"]) {
  const profile = characterProfiles[id];
  if (!profile || (profile.bio || "").length < 400) errors.push(`${id}: biografia mancante o troppo breve`);
}
for (const id of expected.filter(id => ["team", "event"].includes(types[id]))) {
  const profile = editorialProfiles[id];
  if (!profile || profile.type !== types[id] || (profile.bio || "").length < 400) {
    errors.push(`${id}: dossier mancante, errato o troppo breve`);
  }
}

const catalogById = new Map(catalog.issues.map(issue => [issue.id, issue]));
for (const id of physicalIds) {
  const issue = catalogById.get(id);
  if (!issue) errors.push(`${id}: assente dal catalogo globale`);
  if (!issue?.paths?.includes("age-of-apocalypse")) errors.push(`${id}: master non registrato nel catalogo`);
}
for (const id of expected) {
  if (!art.paths?.[id]) errors.push(`${id}: artwork editoriale non generato`);
}
if ((art.hubs?.["age-of-apocalypse"] || []).length < 4) {
  errors.push("age-of-apocalypse: mosaico hub incompleto");
}

if (audit.physicalIssues !== 7 || audit.usaIssues !== 50 || audit.usaStories !== 53) {
  errors.push(`audit: conteggi inattesi (${audit.physicalIssues} volumi, ${audit.usaIssues} albi USA, ${audit.usaStories} storie)`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("OK: Era di Apocalisse — 1 universo, 2 eventi, 2 personaggi, 6 squadre, 1 raccolta e 7 volumi italiani condivisi senza duplicati.");
