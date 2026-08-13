import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const manifest = read("data/characters.json");
const characterCatalog = read("data/character-profiles.json");
const editorialCatalog = read("data/editorial-profiles.json");
const iconCatalog = read("data/path-icons.json");
const artCatalog = read("data/ui-art.json");
const pathsById = new Map(manifest.characters.map(item => [item.id, item]));
const errors = [];

function requireString(id, profile, field) {
  if (typeof profile?.[field] !== "string" || !profile[field].trim()) errors.push(`${id}: ${field} non valido`);
}

function requireList(id, profile, field) {
  const value = profile?.[field];
  if (!Array.isArray(value) || !value.length || value.some(item => typeof item !== "string" || !item.trim())) {
    errors.push(`${id}: ${field} non valido`);
  }
}

const schemas = {
  team: {
    strings: ["founded", "universe", "debut", "creators", "bio"],
    lists: ["founders", "members", "bases", "traits"]
  },
  event: {
    strings: ["period", "universe", "debut", "creators", "trigger", "scope", "bio"],
    lists: ["factions", "consequences"]
  }
};

for (const type of Object.keys(schemas)) {
  const expected = manifest.characters.filter(item => item.type === type);
  for (const pathMeta of expected) {
    const profile = editorialCatalog.profiles?.[pathMeta.id];
    if (!profile) {
      errors.push(`${pathMeta.id}: dossier ${type} mancante`);
      continue;
    }
    if (profile.type !== type) errors.push(`${pathMeta.id}: tipo profilo ${profile.type || "mancante"}, atteso ${type}`);
    for (const field of schemas[type].strings) requireString(pathMeta.id, profile, field);
    for (const field of schemas[type].lists) requireList(pathMeta.id, profile, field);
    if (typeof profile.bio === "string" && profile.bio.length < 300) errors.push(`${pathMeta.id}: biografia troppo breve`);
    if (!iconCatalog.paths?.[pathMeta.id] && !artCatalog.paths?.[pathMeta.id]) errors.push(`${pathMeta.id}: artwork dedicato mancante`);
  }
}

for (const [id, profile] of Object.entries(editorialCatalog.profiles || {})) {
  const pathMeta = pathsById.get(id);
  if (!pathMeta) errors.push(`${id}: dossier senza percorso`);
  else if (!schemas[pathMeta.type]) errors.push(`${id}: dossier editoriale assegnato a ${pathMeta.type}`);
  if (characterCatalog.profiles?.[id]) errors.push(`${id}: profilo duplicato nei due cataloghi`);
  if (!schemas[profile.type]) errors.push(`${id}: tipo dossier sconosciuto`);
}

const expectedEditorialCount = manifest.characters.filter(item => schemas[item.type]).length;
const actualEditorialCount = Object.keys(editorialCatalog.profiles || {}).length;
if (actualEditorialCount !== expectedEditorialCount) errors.push(`totale dossier ${actualEditorialCount}, attesi ${expectedEditorialCount}`);

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

const characterCount = Object.keys(characterCatalog.profiles || {}).length;
console.log(`OK: ${actualEditorialCount}/${expectedEditorialCount} dossier squadre/eventi validi; ${characterCount + actualEditorialCount} profili totali con artwork.`);
