import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const manifest = read("data/characters.json");
const hubs = read("data/hubs.json");
const profiles = read("data/character-profiles.json").profiles || {};
const expected = [
  "marvel-2099",
  "spiderman-2099",
  "doom-2099",
  "punisher-2099",
  "xmen-2099",
  "ghost-rider-2099",
];
const errors = [];
const manifestById = new Map(manifest.characters.map(row => [row.id, row]));
const paths = new Map();

for (const id of expected) {
  const meta = manifestById.get(id);
  if (!meta) {
    errors.push(`${id}: assente dal manifest`);
    continue;
  }
  const data = read(meta.data);
  paths.set(id, data);
  const required = data.issues.filter(issue => issue.required !== false && !issue.future).length;
  if (required !== data.totalRequired || required !== meta.totalRequired) {
    errors.push(`${id}: totale incoerente (${required}/${data.totalRequired}/${meta.totalRequired})`);
  }
  if (new Set(data.issues.map(issue => issue.id)).size !== data.issues.length) {
    errors.push(`${id}: albi fisici duplicati nel percorso`);
  }
  for (const issue of data.issues) {
    const available = new Set((issue.contents || []).map(content => content.id));
    for (const contentId of issue.readingStep?.contentIds || []) {
      if (!available.has(contentId)) errors.push(`${id}/${issue.id}: contenuto ${contentId} non dichiarato`);
    }
  }
}

const alternate = hubs.hubs.find(hub => hub.id === "alternate");
const universe = hubs.hubs.find(hub => hub.id === "marvel-2099");
if (!alternate?.sections?.some(section => section.items?.includes("marvel-2099"))) {
  errors.push("alternate: portale Marvel 2099 non collegato");
}
if (universe?.parent !== "alternate") errors.push("marvel-2099: gerarchia hub non valida");
const hubPathIds = new Set(universe?.groups?.flatMap(group => group.paths || []) || []);
for (const id of expected) if (!hubPathIds.has(id)) errors.push(`${id}: assente dai gruppi dell'hub`);

const master = paths.get("marvel-2099");
if (master) {
  const masterIds = new Set(master.issues.map(issue => issue.id));
  if (master.totalRequired !== 83 || master.issues.length !== 84) {
    errors.push(`marvel-2099: attesi 83 albi obbligatori + 1 ristampa, trovati ${master.totalRequired}/${master.issues.length}`);
  }
  const zero = master.issues.find(issue => issue.id === "2099SPEC_P:0");
  if (!zero || zero.required !== false || !zero.skip) errors.push("2099 Special #0: ristampa non facoltativa");
  for (const [id, data] of paths) {
    if (id === "marvel-2099") continue;
    for (const issue of data.issues) if (!masterIds.has(issue.id)) errors.push(`${id}/${issue.id}: albo assente dal master`);
  }
}

const requiredContents = {
  "spiderman-2099": ["SM2099:1", "SM2099:46"],
  "doom-2099": ["DOOM2099:1", "DOOM2099:44"],
  "punisher-2099": ["PUN2099:1", "PUN2099:28"],
  "xmen-2099": ["XMEN2099:1", "XMEN2099:35", "XM2099OASIS:1"],
  "ghost-rider-2099": ["GR2099:1", "GR2099:25"],
};
for (const [id, contentIds] of Object.entries(requiredContents)) {
  const actual = new Set(paths.get(id)?.issues.flatMap(issue => issue.contents || []).map(content => content.id) || []);
  for (const contentId of contentIds) if (!actual.has(contentId)) errors.push(`${id}: manca ${contentId}`);
}
const punisherContents = new Set(paths.get("punisher-2099")?.issues.flatMap(issue => issue.contents || []).map(content => content.id) || []);
if (punisherContents.has("PUN2099:29")) errors.push("punisher-2099: #29 non pubblicato incluso per errore");

for (const id of ["spiderman-2099", "doom-2099", "punisher-2099", "ghost-rider-2099"]) {
  if (!profiles[id]) errors.push(`${id}: biografia mancante`);
  else if ((profiles[id].bio || "").length < 300) errors.push(`${id}: biografia troppo breve`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("OK: Marvel 2099 — 1 master, 5 percorsi, 83 albi obbligatori e biografie validate.");
