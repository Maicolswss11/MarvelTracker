import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "data/characters.json"), "utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(root, "data/character-profiles.json"), "utf8"));
const characterIds = manifest.characters.filter(path => path.type === "character").map(path => path.id);
const profileIds = Object.keys(catalog.profiles || {});
const requiredStrings = ["realName", "universe", "debut", "creators", "bio"];
const requiredLists = ["aliases", "affiliations", "abilities"];
const errors = [];

for (const id of characterIds) {
  const profile = catalog.profiles?.[id];
  if (!profile) {
    errors.push(`${id}: profilo mancante`);
    continue;
  }
  for (const field of requiredStrings) {
    if (typeof profile[field] !== "string" || !profile[field].trim()) errors.push(`${id}: ${field} non valido`);
  }
  for (const field of requiredLists) {
    if (!Array.isArray(profile[field]) || !profile[field].length || profile[field].some(value => typeof value !== "string" || !value.trim())) {
      errors.push(`${id}: ${field} non valido`);
    }
  }
  if (typeof profile.bio === "string" && profile.bio.length < 300) errors.push(`${id}: biografia troppo breve`);
}

for (const id of profileIds) {
  if (!characterIds.includes(id)) errors.push(`${id}: profilo senza percorso personaggio`);
}

if (new Set(characterIds).size !== characterIds.length) errors.push("ID personaggio duplicati nel manifest");
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`OK: ${profileIds.length}/${characterIds.length} profili personaggio completi e validi.`);
