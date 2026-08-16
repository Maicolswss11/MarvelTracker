import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const read = rel => JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"));
const fail = message => { throw new Error(message); };
const assert = (condition, message) => { if(!condition) fail(message); };
const STORY_MODEL = "comicsbox-story-feature@2";
const STORY_PREFIX = "doctor-strange-story:";

const character = read("data/characters/doctor-strange.json");
const audit = read("data/doctor-strange-audit.json");

assert(character.editorialModel === "physical-issue/usa-contents/reading-step@1", "Doctor Strange editorial model missing");
assert(character.storyIdentityModel === STORY_MODEL, "Doctor Strange story-feature model missing");
assert(audit.status === "audited", "Doctor Strange audit is not marked audited");
assert(audit.storyIdentityModel === STORY_MODEL, "Audit story-feature model missing");
assert(character.issues.length > 100, `Doctor Strange route unexpectedly short: ${character.issues.length}`);
assert(!character.issues.some(issue => issue.id === "DSTR_M:2" || issue.id === "DSTR_M:3"), "DSTR_M #2-3 must not masquerade as sequential Sorcerer Supreme steps");

for(const [index, issue] of character.issues.entries()){
  const step = issue.readingStep;
  assert(step?.pathId === "doctor-strange", `${issue.id}: invalid readingStep path`);
  assert(step.position === index + 1, `${issue.id}: readingStep position ${step.position} != ${index + 1}`);
  assert(Array.isArray(step.contentIds) && step.contentIds.length > 0, `${issue.id}: empty contentIds`);
  assert(Array.isArray(issue.contents) && issue.contents.length > 0, `${issue.id}: contents missing`);
  const available = new Set(issue.contents.map(content => content.id));
  for(const contentId of step.contentIds) assert(available.has(contentId), `${issue.id}: selected ${contentId} absent from contents`);
}

const mapping = new Map(audit.mappings.map(row => [row.usaCode, row]));
const expectAlbum = (usaCode, albumCode) => {
  const row = mapping.get(usaCode);
  assert(row, `${usaCode}: mapping missing`);
  assert(row.italianAlbum === albumCode, `${usaCode}: expected ${albumCode}, got ${row.italianAlbum}`);
  assert(row.physicalId, `${usaCode}: no physicalId`);
  assert(row.storyId?.startsWith(STORY_PREFIX), `${usaCode}: exact storyId missing`);
  assert(row.storyTitle, `${usaCode}: exact story title missing`);
};
expectAlbum("ST2_007", "WOL_PM_032");
expectAlbum("MGN_STDO_001", "PSPP_006");
expectAlbum("DS3_001", "MAREPCOLL_003");
expectAlbum("DS3_006", "MAREPCOLL_003");
expectAlbum("DS3_019", "MAR_MAG_008");
expectAlbum("DS3_042", "MCP_M_018");
expectAlbum("DS3_048", "DSTR_M_000");
expectAlbum("DS3_057", "DSTR_M_004");
assert(mapping.get("DS3_076")?.storyId?.startsWith(STORY_PREFIX), "DS3 #76 should have an audited story feature");
assert(mapping.get("DS3_090")?.storyId?.startsWith(STORY_PREFIX), "DS3 #90 should have an audited story feature");

// ComicsBox catalogs Wolverine #32/33 as one double-numbered physical issue.
const st2 = mapping.get("ST2_007");
const st2Steps = character.issues.filter(issue => issue.readingStep.contentIds.includes(st2.storyId));
assert(st2Steps.length === 1, `ST2 #7 should require one double-numbered physical step, got ${st2Steps.length}`);
assert(st2Steps[0].id === "WOL_PM:32/33", `ST2 #7 should map to WOL_PM:32/33, got ${st2Steps[0].id}`);
assert(!character.issues.some(issue => issue.id === "WOL_PM:33"), "Wolverine #33 must not be invented as a separate physical issue");
assert(/single double-numbered Italian physical issue/i.test(audit.guardrails?.splitItalianStories || ""), "ST2 #7 double-number guardrail missing");

// The first Masterworks must select only the Doctor Strange feature of each
// anthology issue; Human Torch/Nick Fury labels were the semantic bug that
// triggered this second audit pass.
const mmw1 = character.issues.find(issue => issue.id === "MMW_M:67");
assert(mmw1, "Marvel Masterworks #67 missing");
assert(mmw1.readingStep.contentIds.every(id => id.startsWith(STORY_PREFIX)), "MMW #67 still uses raw anthology issue IDs");
const selectedMmw1 = new Set(mmw1.readingStep.contentIds);
const selectedMmw1Contents = mmw1.contents.filter(content => selectedMmw1.has(content.id));
assert(selectedMmw1Contents.length === selectedMmw1.size, "MMW #67 selected feature metadata incomplete");
for(const content of selectedMmw1Contents){
  assert(content.feature === "Doctor Strange", `${content.id}: not tagged as Doctor Strange feature`);
  assert(content.sourceIssueId?.startsWith("ST1_"), `${content.id}: source anthology issue missing`);
  assert(!/human torch|nick fury/i.test(content.title || ""), `${content.id}: wrong anthology feature label: ${content.title}`);
}

for(const code of audit.knownGaps.strangeTalesVol2DoctorStrange){
  const row = mapping.get(code);
  assert(row && !row.physicalId && !row.italianAlbum && !row.storyId, `${code}: must remain an explicit Italian-publication gap`);
}
for(const code of audit.knownGaps.sorcererSupremeMainStories){
  const row = mapping.get(code);
  assert(row && !row.physicalId && !row.italianAlbum && !row.storyId, `${code}: main story must remain an explicit Italian-publication gap`);
}
assert(mapping.get("DSA_004") && !mapping.get("DSA_004").physicalId, "Doctor Strange Annual #4 must remain an Italian-publication gap");
assert(audit.classic.unpublishedInItaly === 62, `Expected 62 declared classic gaps, got ${audit.classic.unpublishedInItaly}`);

const tailIds = new Set(character.issues.map(issue => issue.id));
for(const id of ["100M:31", "100M:65", "100M:174", "DSTRANGE_P:1", "UMSDSTRIMP:5"]){
  assert(tailIds.has(id), `Modern route regression: ${id} missing`);
}
const expectedRequired = character.issues.filter(issue => issue.required !== false && !issue.future).length;
assert(character.totalRequired === expectedRequired, `totalRequired mismatch: ${character.totalRequired}/${expectedRequired}`);

const editions = read("data/editions.json");
const altAudit = read("data/doctor-strange-alternatives-audit.json");
assert(editions.coverageModel?.includes(`doctor-strange/${STORY_MODEL}`), "Doctor Strange exact story-feature coverage model missing");
assert(altAudit.coverageModel === STORY_MODEL, "Alternative audit is not story-feature scoped");
assert(altAudit.editionsWithRelevantContents >= 20, `Too few Doctor Strange alternatives: ${altAudit.editionsWithRelevantContents}`);
assert(altAudit.exactDoctorStrangeStoryBlocks > 100, `Too few exact story blocks: ${altAudit.exactDoctorStrangeStoryBlocks}`);
const requirements = new Map(character.issues.map(issue => [issue.id, new Set(issue.readingStep.contentIds)]));
let doctorCoverage = 0;
for(const edition of editions.editions){
  for(const row of edition.coverage || []){
    if(row.path !== "doctor-strange") continue;
    doctorCoverage++;
    assert(row.coverageModel === STORY_MODEL, `${edition.id}: stale Doctor Strange coverage model`);
    assert(Array.isArray(row.contentIds) && row.contentIds.length > 0, `${edition.id}: Doctor Strange coverage lacks contentIds`);
    assert(Array.isArray(row.requiredContentIds) && row.requiredContentIds.length > 0, `${edition.id}: Doctor Strange coverage lacks requiredContentIds`);
    assert((row.issueIds || []).length === 1, `${edition.id}: audited Doctor Strange coverage must be one step per row`);
    const issueId = row.issueIds[0];
    const required = requirements.get(issueId);
    assert(required, `${edition.id}: unknown Doctor Strange issue ${issueId}`);
    const declaredRequired = new Set(row.requiredContentIds);
    assert(required.size === declaredRequired.size && [...required].every(id => declaredRequired.has(id)), `${edition.id}: requiredContentIds mismatch for ${issueId}`);
    const covered = new Set(row.contentIds);
    assert([...covered].every(id => required.has(id)), `${edition.id}: coverage contains non-required IDs for ${issueId}`);
    const complete = [...required].every(id => covered.has(id));
    assert(Boolean(row.complete) === complete, `${edition.id}: complete flag wrong for ${issueId}`);
  }
}
assert(doctorCoverage >= 20, `Doctor Strange alternative coverage too small: ${doctorCoverage}`);

const edition = id => editions.editions.find(item => item.id === id);
const rowFor = (editionId, issueId) => (edition(editionId)?.coverage || []).find(row => row.path === "doctor-strange" && row.issueIds?.includes(issueId));

// Cross-volume boundaries are now real: the 2026 Ditko omnibus fully replaces
// MMW #67 despite retitled Italian story headings, while a broad anthology
// containing only selected early stories remains partial.
assert(edition("MAROMNIB:252"), "2026 Ditko Doctor Strange omnibus missing");
assert(rowFor("MAROMNIB:252", "MMW_M:67")?.complete === true, "Ditko Omnibus #252 should completely cover MMW #67 selected stories");
assert(edition("MARVELANT2:21"), "Io sono Doctor Strange anthology missing");
assert(rowFor("MARVELANT2:21", "MMW_M:67")?.complete === false, "Marvel Anthology #21 should be partial for MMW #67, not a false full equivalent");

for(const id of ["GEM_CA:113", "MARVELLC:8", "SUPEROICLA:201", "DSTRANGEORO:23"]){
  const item = edition(id);
  assert(item, `${id}: expected audited Doctor Strange edition missing`);
  assert((item.coverage || []).some(row => row.path === "doctor-strange"), `${id}: no exact Doctor Strange coverage`);
}

console.log(`Doctor Strange story-feature audit OK: ${character.issues.length} physical steps, ${audit.classic.unpublishedInItaly} declared classic gaps, ${altAudit.editionsWithRelevantContents} relevant alternatives.`);
