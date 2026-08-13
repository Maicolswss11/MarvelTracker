import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const manifest = read("data/characters.json");
const hubs = read("data/hubs.json");
const characterProfiles = read("data/character-profiles.json").profiles || {};
const editorialProfiles = read("data/editorial-profiles.json").profiles || {};
const expected = [
  "marvel-zombies",
  "zombie-spider-man",
  "marvel-zombies-2149",
  "marvel-zombies-battleworld",
  "marvel-zombies-resurrection",
  "marvel-zombies-dawn-of-decay",
  "marvel-zombies-red-band",
];
const expectedTypes = {
  "marvel-zombies": "universe",
  "zombie-spider-man": "character",
  "marvel-zombies-2149": "team",
  "marvel-zombies-battleworld": "event",
  "marvel-zombies-resurrection": "event",
  "marvel-zombies-dawn-of-decay": "event",
  "marvel-zombies-red-band": "event",
};
const expectedTotals = {
  "marvel-zombies": 5,
  "zombie-spider-man": 1,
  "marvel-zombies-2149": 1,
  "marvel-zombies-battleworld": 1,
  "marvel-zombies-resurrection": 1,
  "marvel-zombies-dawn-of-decay": 1,
  "marvel-zombies-red-band": 1,
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
const universe = hubs.hubs.find(hub => hub.id === "marvel-zombies");
if (!alternate?.sections?.some(section => section.items?.includes("marvel-zombies"))) {
  errors.push("alternate: portale Marvel Zombies non collegato");
}
if (universe?.parent !== "alternate") errors.push("marvel-zombies: gerarchia hub non valida");
const hubPathIds = new Set(universe?.groups?.flatMap(group => group.paths || []) || []);
for (const id of expected) if (!hubPathIds.has(id)) errors.push(`${id}: assente dai gruppi dell'hub`);

const master = paths.get("marvel-zombies");
if (master) {
  const expectedPhysical = ["MAROMNIB:188", "MAROMNIB:235", "MARVGIANTS:17", "MVNWCOL_P:647", "MVNWCOL_P:735"];
  const physical = new Set(master.issues.map(issue => issue.id));
  for (const id of expectedPhysical) if (!physical.has(id)) errors.push(`marvel-zombies: manca ${id}`);
  for (const [id, data] of paths) {
    if (id === "marvel-zombies") continue;
    for (const issue of data.issues) if (!physical.has(issue.id)) errors.push(`${id}/${issue.id}: volume assente dal master`);
  }
}

const requiredContents = {
  "zombie-spider-man": ["ULTF4:22", "MZOMBIE1:1", "MZRETURN:5"],
  "marvel-zombies-2149": ["MZDEADDAYS:1", "MZOMBIE2:5", "MZRETURN:5"],
  "marvel-zombies-battleworld": ["MZ2015:1", "MZ2015:4", "AOUVSMZ:1", "AOUVSMZ:4"],
  "marvel-zombies-resurrection": ["MZRES2019:1", "MZRES2020:4"],
  "marvel-zombies-dawn-of-decay": ["MZDAWN:1", "MZDAWN:4"],
  "marvel-zombies-red-band": ["MZREDBAND:1", "MZREDBAND:5"],
};
for (const [id, contentIds] of Object.entries(requiredContents)) {
  const actual = new Set(paths.get(id)?.issues.flatMap(issue => issue.contents || []).map(item => item.id) || []);
  for (const contentId of contentIds) if (!actual.has(contentId)) errors.push(`${id}: manca ${contentId}`);
}

const originalReality = new Set(paths.get("marvel-zombies-2149")?.issues.flatMap(issue => issue.contents || []).map(item => item.id) || []);
if ([...originalReality].some(id => id.startsWith("MZRES") || id.startsWith("MZ2015") || id.startsWith("MZDAWN") || id.startsWith("MZREDBAND"))) {
  errors.push("marvel-zombies-2149: contiene per errore una realtà successiva");
}

const spiderProfile = characterProfiles["zombie-spider-man"];
if (!spiderProfile || (spiderProfile.bio || "").length < 300) errors.push("zombie-spider-man: biografia mancante o troppo breve");
for (const id of expected.filter(item => ["team", "event"].includes(expectedTypes[item]))) {
  const profile = editorialProfiles[id];
  if (!profile || profile.type !== expectedTypes[id] || (profile.bio || "").length < 300) {
    errors.push(`${id}: dossier mancante, errato o troppo breve`);
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("OK: Marvel Zombies — 1 portale, 1 personaggio, 1 squadra, 4 eventi e 5 volumi italiani separati per continuità.");
