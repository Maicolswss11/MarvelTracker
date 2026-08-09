import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require=createRequire(import.meta.url);
require("../js/achievements.js");
const manifest=require("../data/characters.json");

const paths=manifest.characters.map(path=>({
  id:path.id,
  name:path.name,
  type:path.type,
  read:0,
  total:path.totalRequired,
  started:false,
  done:false,
}));
const emptySnapshot={
  read:0,owned:0,physical:0,digital:0,both:0,wishlist:0,lists:0,
  readingCoverage:0,collectionCoverage:0,maxListSize:0,memberDays:0,
  hasDisplayName:false,hasBio:false,hasFavorite:false,hasAvatar:false,cloudConnected:false,
  paths,
};

const empty=globalThis.MarvelAchievements.build(emptySnapshot);
assert.equal(empty.total,90,"Il catalogo deve contenere 90 traguardi");
assert.equal(empty.categories.length,6,"Il catalogo deve contenere 6 categorie");
assert.equal(new Set(empty.achievements.map(item=>item.id)).size,empty.total,"Ogni traguardo deve avere un id univoco");
assert.equal(empty.unlocked,0,"Un profilo vuoto non deve avere traguardi sbloccati");

const firstRead=globalThis.MarvelAchievements.build({...emptySnapshot,read:1});
assert.equal(firstRead.achievements.find(item=>item.id==="read-1")?.done,true,"La prima lettura deve sbloccare Prima pagina");
assert.equal(firstRead.achievements.find(item=>item.id==="read-10")?.done,false,"Una lettura non deve sbloccare il traguardo da 10");

const completePaths=paths.map(path=>({...path,read:path.total,started:true,done:true}));
const complete=globalThis.MarvelAchievements.build({
  ...emptySnapshot,
  read:4000,owned:4000,physical:1000,digital:1000,both:200,wishlist:100,lists:5,
  readingCoverage:100,collectionCoverage:100,maxListSize:30,memberDays:365,
  hasDisplayName:true,hasBio:true,hasFavorite:true,hasAvatar:true,cloudConnected:true,
  paths:completePaths,
});
assert.equal(complete.unlocked,complete.total,"Il profilo completo deve sbloccare l’intero catalogo");
assert.equal(complete.rank.level,10,"Il completamento totale deve raggiungere il livello massimo");

console.log(`Achievement catalog verified: ${complete.total} traguardi, ${complete.categories.length} categorie, ${complete.maxXp} XP massimi.`);
