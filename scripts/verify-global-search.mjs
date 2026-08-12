import fs from "node:fs";

const read = path => JSON.parse(fs.readFileSync(path,"utf8"));
const manifest = read("data/characters.json");
const catalog = read("data/catalog.json");
const editions = read("data/editions.json");
const pathNames = new Map(manifest.characters.map(path => [path.id,path.name]));

const failures = [];
const fail = message => failures.push(message);

if(catalog.manifestVersion !== manifest.version) fail(`Catalog manifest ${catalog.manifestVersion} != ${manifest.version}`);
if(catalog.total !== catalog.issues.length) fail(`Catalog total ${catalog.total} != ${catalog.issues.length}`);
if(catalog.issues.length < 6000) fail(`Catalog unexpectedly small: ${catalog.issues.length}`);

for(const issue of catalog.issues){
  const paths = new Set(issue.paths || []);
  const entries = issue.pathEntries || [];
  const entryPaths = new Set(entries.map(entry => entry.pathId));
  if(!entries.length) fail(`${issue.id}: missing pathEntries`);
  if(paths.size !== entryPaths.size || [...paths].some(path => !entryPaths.has(path))){
    fail(`${issue.id}: paths/pathEntries mismatch`);
  }
  const contentIds = new Set((issue.contents || []).map(content => content.id).filter(Boolean));
  for(const entry of entries){
    if(!pathNames.has(entry.pathId)) fail(`${issue.id}: unknown path ${entry.pathId}`);
    if(entry.pathName && entry.pathName !== pathNames.get(entry.pathId)) fail(`${issue.id}: wrong name for ${entry.pathId}`);
    if(!String(entry.token || "").trim()) fail(`${issue.id}/${entry.pathId}: empty route token`);
    for(const contentId of entry.contentIds || []){
      if(!contentIds.has(contentId)) fail(`${issue.id}/${entry.pathId}: unknown content ${contentId}`);
    }
  }
}

const xforceZero = catalog.issues.find(issue => issue.id === "XFOR_M:0");
if(!xforceZero) fail("Canary XFOR_M:0 missing");
else{
  const expected = new Set(["new-mutants","x-force","deadpool"]);
  const actual = new Set(xforceZero.pathEntries.map(entry => entry.pathId));
  if([...expected].some(path => !actual.has(path))) fail("XFOR_M:0 does not expose every expected path");
  const deadpool = xforceZero.pathEntries.find(entry => entry.pathId === "deadpool");
  const xforce = xforceZero.pathEntries.find(entry => entry.pathId === "x-force");
  if(deadpool?.contentIds?.length !== 1 || xforce?.contentIds?.length !== 3){
    fail("XFOR_M:0 lost path-local USA content scopes");
  }
}

const coveredEditions = editions.editions.filter(edition => (edition.coverage || []).some(row => row.path && row.issueIds?.length));
if(coveredEditions.length < 100) fail(`Too few searchable alternative editions: ${coveredEditions.length}`);

const html = fs.readFileSync("index.html","utf8");
const triggerCount = (html.match(/data-global-search/g) || []).length;
if(triggerCount < 4) fail(`Only ${triggerCount} global-search entry points found`);
for(const asset of ["css/global-search.css","css/editorial-refresh.css","js/global-search.js"]){
  if(!html.includes(asset)) fail(`Missing ${asset} from index.html`);
}

if(failures.length){
  console.error(failures.slice(0,40).join("\n"));
  if(failures.length > 40) console.error(`…and ${failures.length-40} more`);
  process.exit(1);
}

console.log(`Global search verified: ${catalog.issues.length} physical issues, ${coveredEditions.length} linked alternatives, ${manifest.characters.length} paths.`);
