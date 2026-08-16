import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const read = rel => JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"));
const fail = message => { throw new Error(message); };
const assert = (condition, message) => { if(!condition) fail(message); };

const character = read("data/characters/doctor-strange.json");
const audit = read("data/doctor-strange-audit.json");

assert(character.editorialModel === "physical-issue/usa-contents/reading-step@1", "Doctor Strange editorial model missing");
assert(audit.status === "audited", "Doctor Strange audit is not marked audited");
assert(character.issues.length > 90, `Doctor Strange route unexpectedly short: ${character.issues.length}`);
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
};
expectAlbum("ST2_007", "WOL_PM_032");
expectAlbum("MGN_STDO_001", "PSPP_006");
expectAlbum("DS3_001", "MAREPCOLL_003");
expectAlbum("DS3_019", "MAR_MAG_008");
expectAlbum("DS3_042", "MCP_M_018");
expectAlbum("DS3_048", "DSTR_M_000");
expectAlbum("DS3_057", "DSTR_M_004");
assert(mapping.get("DS3_076")?.physicalId, "DS3 #76 should have an official Italian publication");
assert(mapping.get("DS3_090")?.physicalId, "DS3 #90 should have an official Italian publication");

for(const code of audit.knownGaps.strangeTalesVol2DoctorStrange){
  const row = mapping.get(code);
  assert(row && !row.physicalId && !row.italianAlbum, `${code}: must remain an explicit Italian-publication gap`);
}
for(const code of audit.knownGaps.sorcererSupremeMainStories){
  const row = mapping.get(code);
  assert(row && !row.physicalId && !row.italianAlbum, `${code}: main story must remain an explicit Italian-publication gap`);
}
assert(mapping.get("DSA_004") && !mapping.get("DSA_004").physicalId, "Doctor Strange Annual #4 must remain an Italian-publication gap");

const tailIds = new Set(character.issues.map(issue => issue.id));
for(const id of ["100M:31", "100M:65", "100M:174", "DSTRANGE_P:1", "UMSDSTRIMP:5"]){
  assert(tailIds.has(id), `Modern route regression: ${id} missing`);
}
const expectedRequired = character.issues.filter(issue => issue.required !== false && !issue.future).length;
assert(character.totalRequired === expectedRequired, `totalRequired mismatch: ${character.totalRequired}/${expectedRequired}`);

if(fs.existsSync(path.join(root, "data/doctor-strange-alternatives-audit.json"))){
  const editions = read("data/editions.json");
  const altAudit = read("data/doctor-strange-alternatives-audit.json");
  assert(editions.coverageModel?.includes("doctor-strange/content-union@1"), "Doctor Strange content-union coverage model missing");
  assert(altAudit.editionsWithRelevantContents >= 5, `Too few Doctor Strange alternatives: ${altAudit.editionsWithRelevantContents}`);
  const requirements = new Map(character.issues.map(issue => [issue.id, new Set(issue.readingStep.contentIds)]));
  let doctorCoverage = 0;
  for(const edition of editions.editions){
    for(const row of edition.coverage || []){
      if(row.path !== "doctor-strange") continue;
      doctorCoverage++;
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
  assert(doctorCoverage >= 5, `Doctor Strange alternative coverage too small: ${doctorCoverage}`);
  for(const id of ["DSTRANGEORO:2", "DSTRANGEORO:11", "DSTRANGEORO:15", "DSTRANGEORO:17", "DSTRANGEORO:25"]){
    const edition = editions.editions.find(item => item.id === id);
    assert(edition, `${id}: expected Doctor Strange Serie Oro volume missing`);
    assert((edition.coverage || []).some(row => row.path === "doctor-strange"), `${id}: no audited Doctor Strange overlap`);
  }
}

console.log(`Doctor Strange audit OK: ${character.issues.length} physical steps, ${audit.classic.unpublishedInItaly} declared classic gaps.`);
