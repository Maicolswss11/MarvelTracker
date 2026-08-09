#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


editions = {
    "version": 1,
    "editions": [
        {
            "id": "MVNWCOL_P:12",
            "name": "Iron Man: Credere",
            "series": "Marvel Collection II",
            "number": 12,
            "publisher": "Panini Comics",
            "format": "Cartonato",
            "cover": "https://www.comicsbox.it/cover/MVNWCOL_P_012.jpg",
            "url": "https://www.comicsbox.it/albo/MVNWCOL_P_012",
            "contents": ["Iron Man (2012) #1–5"],
            "coverage": [
                {
                    "path": "ironman",
                    "issueIds": ["IRONM3_P:1", "IRONM3_P:2", "IRONM3_P:3"],
                    "label": "Credere — Iron Man (2012) #1–5"
                }
            ]
        }
    ]
}
(ROOT / "data" / "editions.json").write_text(
    json.dumps(editions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

editions_js = r'''(() => {
  let manifest = {version:1,editions:[]};
  let byId = new Map();
  let loadPromise = null;

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

  async function load(version=1){
    if(loadPromise) return loadPromise;
    loadPromise = fetch(`data/editions.json?v=${encodeURIComponent(version)}`, {cache:"no-cache"})
      .then(response => {
        if(!response.ok) throw new Error(`Edizioni alternative HTTP ${response.status}`);
        return response.json();
      })
      .then(data => {
        if(!Array.isArray(data.editions)) throw new Error("Manifest edizioni alternative non valido");
        manifest = data;
        byId = new Map(data.editions.map(item => [item.id,item]));
        return manifest;
      })
      .catch(error => {
        console.error("Edizioni alternative non disponibili", error);
        manifest = {version:1,editions:[]};
        byId = new Map();
        return manifest;
      })
      .finally(() => { loadPromise = null; });
    return loadPromise;
  }

  function normalizeState(state){
    state ??= {};
    state.editions ??= {};
    for(const [id,value] of Object.entries(state.editions)){
      if(value === true) state.editions[id] = {owned:true};
      else if(!value || typeof value !== "object") delete state.editions[id];
      else state.editions[id] = {...value,owned:!!value.owned};
    }
    state.editionSchema = 1;
    return state;
  }

  function all(){ return manifest.editions || []; }
  function get(id){ return byId.get(id) || null; }
  function isOwned(state,id){
    const value = state?.editions?.[id];
    return value === true || !!value?.owned;
  }
  function setOwned(state,id,owned){
    state.editions ??= {};
    if(owned){
      const previous = state.editions[id];
      state.editions[id] = {
        ...(previous && typeof previous === "object" ? previous : {}),
        owned:true,
        addedAt: previous?.addedAt || new Date().toISOString(),
      };
    }else delete state.editions[id];
  }

  function optionsFor(pathId,issueId){
    const result = [];
    for(const edition of all()){
      for(const coverage of edition.coverage || []){
        if(coverage.path === pathId && (coverage.issueIds || []).includes(issueId)){
          result.push({...edition,coverage});
          break;
        }
      }
    }
    return result;
  }

  function coverageStatus(state,pathId,issueId){
    const options = optionsFor(pathId,issueId);
    return {options,owned:options.filter(item => isOwned(state,item.id))};
  }

  function physicalObjectCount(state){
    const ids = new Set();
    for(const [id,value] of Object.entries(state?.collection || {})) if(value?.physical) ids.add(id);
    for(const edition of all()) if(isOwned(state,edition.id)) ids.add(edition.id);
    return ids.size;
  }

  function ownedPublicationCount(state){
    const ids = new Set();
    for(const [id,value] of Object.entries(state?.collection || {})) if(value?.physical || value?.digital) ids.add(id);
    for(const edition of all()) if(isOwned(state,edition.id)) ids.add(edition.id);
    return ids.size;
  }

  function catalogItems(pathManifest){
    const pathNames = new Map((pathManifest?.characters || []).map(item => [item.id,item.name]));
    return all().map(edition => {
      const paths = [...new Set((edition.coverage || []).map(item => item.path))];
      const coverage = (edition.coverage || []).map(item => item.label).filter(Boolean).join(" · ");
      return {
        id: edition.id,
        name: edition.name,
        series: edition.series,
        n: edition.number,
        displayNumber: edition.number,
        publisher: edition.publisher,
        title: coverage || (edition.contents || []).join(" · "),
        date: edition.date || "",
        cover: edition.cover,
        url: edition.url,
        paths,
        pathNames: paths.map(id => pathNames.get(id) || id),
        isAlternativeEdition: true,
        editionFormat: edition.format,
        editionContents: edition.contents || [],
      };
    });
  }

  function ensureDialog(){
    let dialog = document.getElementById("editionDialog");
    if(dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.id = "editionDialog";
    dialog.className = "editionDialog";
    dialog.innerHTML = '<div class="editionDialogShell"><button type="button" class="editionDialogClose" aria-label="Chiudi">×</button><div class="editionDialogBody"></div></div>';
    document.body.append(dialog);
    dialog.querySelector(".editionDialogClose").onclick = () => dialog.close();
    dialog.addEventListener("click", event => { if(event.target === dialog) dialog.close(); });
    return dialog;
  }

  function openPicker({state,pathId,issue,onToggle}){
    const options = optionsFor(pathId,issue?.id);
    if(!options.length) return;
    const dialog = ensureDialog();
    const body = dialog.querySelector(".editionDialogBody");
    body.innerHTML = `
      <header class="editionDialogHead">
        <span>Edizioni alternative</span>
        <h2>${esc(issue.name)}</h2>
        <p>Lo spillato e le raccolte sono pubblicazioni diverse. Segna qui la ristampa che possiedi: il tracker coprirà questa tappa senza dichiarare posseduto lo spillato.</p>
      </header>
      <div class="editionExactNote"><b>Edizione mostrata nel percorso</b><span>${esc(issue.name)} · usa “Fisico” sulla scheda solo se possiedi davvero questo albo.</span></div>
      <div class="editionChoices">${options.map(edition => {
        const owned = isOwned(state,edition.id);
        const contents = (edition.contents || []).join(" · ");
        return `<article class="editionChoice ${owned?"owned":""}">
          <div class="editionChoiceCover">${edition.cover?`<img src="${esc(edition.cover)}" alt="${esc(edition.name)}" referrerpolicy="no-referrer">`:""}</div>
          <div class="editionChoiceInfo"><span>${esc(edition.format || "Edizione alternativa")}</span><h3>${esc(edition.name)}</h3><p>${esc(edition.series)}${edition.number?` #${esc(edition.number)}`:""} · ${esc(edition.publisher || "")}</p><small>${esc(edition.coverage?.label || contents)}</small>${edition.url?`<a href="${esc(edition.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}</div>
          <button type="button" class="editionOwnButton ${owned?"owned":""}" data-toggle-edition="${esc(edition.id)}">${owned?"✓ Posseduto":"Segna posseduto"}</button>
        </article>`;
      }).join("")}</div>`;
    body.querySelectorAll("[data-toggle-edition]").forEach(button => button.onclick = () => {
      const id = button.dataset.toggleEdition;
      onToggle?.(id,!isOwned(state,id));
      openPicker({state,pathId,issue,onToggle});
    });
    if(typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open","");
  }

  window.MarvelEditions = {load,normalizeState,all,get,isOwned,setOwned,optionsFor,coverageStatus,physicalObjectCount,ownedPublicationCount,catalogItems,openPicker};
})();
'''
(ROOT / "js" / "editions.js").write_text(editions_js, encoding="utf-8")

editions_css = r'''
.editionCoverageBadge{display:inline-flex;align-items:center;gap:5px;margin-left:7px;padding:3px 7px;border:1px solid rgba(78,224,160,.35);border-radius:999px;background:rgba(78,224,160,.1);color:#82edba;font-size:10px;font-weight:800;vertical-align:middle}.collectionFormats button.edition{border-color:rgba(78,224,160,.45);color:#82edba;background:rgba(78,224,160,.09)}.collectionFormats button.edition.on{background:rgba(78,224,160,.16)}
.editionDialog{width:min(780px,calc(100vw - 24px));max-height:min(760px,calc(100vh - 24px));padding:0;border:1px solid #273545;border-radius:22px;background:#0a1017;color:#eef5fb;box-shadow:0 28px 90px rgba(0,0,0,.65)}.editionDialog::backdrop{background:rgba(0,0,0,.72);backdrop-filter:blur(5px)}.editionDialogShell{position:relative;padding:26px}.editionDialogClose{position:absolute;right:14px;top:14px;width:38px;height:38px;border:1px solid #2b3948;border-radius:50%;background:#101923;color:#d9e6ef;font-size:24px;cursor:pointer}.editionDialogHead{padding-right:48px}.editionDialogHead>span{display:block;color:#82edba;text-transform:uppercase;letter-spacing:.12em;font-size:10px;font-weight:900}.editionDialogHead h2{margin:7px 0 9px;font-size:27px}.editionDialogHead p{margin:0;color:#91a2b2;line-height:1.55}.editionExactNote{display:grid;gap:4px;margin:20px 0;padding:13px 15px;border:1px solid #253343;border-radius:13px;background:#0d151e}.editionExactNote b{font-size:12px}.editionExactNote span{color:#8496a8;font-size:11px}.editionChoices{display:grid;gap:12px}.editionChoice{display:grid;grid-template-columns:78px 1fr auto;gap:15px;align-items:center;padding:13px;border:1px solid #263544;border-radius:16px;background:#0c141d}.editionChoice.owned{border-color:rgba(78,224,160,.45);box-shadow:inset 0 0 0 1px rgba(78,224,160,.08)}.editionChoiceCover{width:78px;aspect-ratio:2/3;border-radius:8px;overflow:hidden;background:#111b25}.editionChoiceCover img{width:100%;height:100%;object-fit:cover}.editionChoiceInfo>span{color:#82edba;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.1em}.editionChoiceInfo h3{margin:4px 0;font-size:16px}.editionChoiceInfo p{margin:0 0 5px;color:#94a6b7;font-size:11px}.editionChoiceInfo small{display:block;color:#c7d4df;font-size:10px;line-height:1.4}.editionChoiceInfo a{display:inline-block;margin-top:7px;color:#74b9ff;font-size:10px}.editionOwnButton{min-width:120px;padding:10px 12px;border:1px solid #34485a;border-radius:10px;background:#111c27;color:#dce8f1;font-weight:800;cursor:pointer}.editionOwnButton.owned{border-color:rgba(78,224,160,.5);background:rgba(78,224,160,.14);color:#8ff0c1}.profileIssueBadges .editionAlternative{background:rgba(78,224,160,.12);border-color:rgba(78,224,160,.35);color:#82edba}.profileIssueCard.editionCard{border-color:rgba(78,224,160,.25)}
@media(max-width:650px){.editionDialogShell{padding:20px 14px}.editionChoice{grid-template-columns:62px 1fr;align-items:start}.editionChoiceCover{width:62px}.editionOwnButton{grid-column:1/-1;width:100%}.editionDialogHead h2{font-size:23px}}
'''
(ROOT / "css" / "editions.css").write_text(editions_css.strip() + "\n", encoding="utf-8")

# Patch main tracker.
app_path = ROOT / "js" / "app.js"
app = app_path.read_text(encoding="utf-8")
app = replace_once(
    app,
    '  x ??= {}; x.characters ??= {}; x.collection ??= {}; x.wishlist ??= {}; x.lists ??= {}; x.profileSchema ??= 1;',
    '  x ??= {}; x.characters ??= {}; x.collection ??= {}; x.wishlist ??= {}; x.lists ??= {}; x.editions ??= {}; x.profileSchema ??= 1; x=window.MarvelEditions?.normalizeState(x)||x;',
    "normalize state editions",
)
app = replace_once(
    app,
    '''function status(id){\n  const item=state.collection?.[id]||{},physical=!!item.physical,digital=!!item.digital;\n  return {physical,digital,owned:physical||digital,read:!!bucket()[id]?.read};\n}\n''',
    '''function status(id){\n  const item=state.collection?.[id]||{},physical=!!item.physical,digital=!!item.digital;\n  const coverage=window.MarvelEditions?.coverageStatus(state,activeCharacter,id)||{options:[],owned:[]};\n  const alternativePhysical=coverage.owned.length>0,physicalCovered=physical||alternativePhysical;\n  return {physical,digital,physicalCovered,alternativePhysical,owned:physicalCovered||digital,read:!!bucket()[id]?.read,editionOptions:coverage.options,ownedEditions:coverage.owned};\n}\n''',
    "route status with edition coverage",
)
app = replace_once(
    app,
    'function setStatus(id,patch){setStatuses([id],patch)}\n',
    '''function setStatus(id,patch){setStatuses([id],patch)}\nfunction setEditionOwned(id,owned){\n  window.MarvelEditions?.setOwned(state,id,owned);\n  saveState();\n  renderAll();\n  void window.MarvelProfile?.render();\n}\nfunction openEditionPicker(issueId){\n  const issue=currentCharacter?.issues?.find(item=>item.id===issueId);\n  if(!issue)return;\n  window.MarvelEditions?.openPicker({state,pathId:activeCharacter,issue,onToggle:setEditionOwned});\n}\n''',
    "edition actions",
)
app = replace_once(
    app,
    '''async function loadManifest(){\n  const r=await fetch("data/characters.json",{cache:"no-cache"}); if(!r.ok)throw new Error(`Manifest HTTP ${r.status}`); manifest=await r.json(); state=normalizeState(state);\n}\n''',
    '''async function loadManifest(){\n  const r=await fetch("data/characters.json",{cache:"no-cache"}); if(!r.ok)throw new Error(`Manifest HTTP ${r.status}`); manifest=await r.json(); await window.MarvelEditions?.load(manifest.version); state=normalizeState(state);\n}\n''',
    "load editions manifest",
)
app = replace_once(
    app,
    'const collectionValues=Object.values(state.collection||{}),physicalTotal=collectionValues.filter(x=>x?.physical).length,digitalTotal=collectionValues.filter(x=>x?.digital).length,ownedTotal=collectionValues.filter(x=>x?.physical||x?.digital).length;',
    'const collectionValues=Object.values(state.collection||{}),directPhysicalTotal=collectionValues.filter(x=>x?.physical).length,digitalTotal=collectionValues.filter(x=>x?.digital).length,physicalTotal=window.MarvelEditions?.physicalObjectCount(state)??directPhysicalTotal,ownedTotal=window.MarvelEditions?.ownedPublicationCount(state)??collectionValues.filter(x=>x?.physical||x?.digital).length;',
    "home collection stats",
)
app = replace_once(
    app,
    'function renderStats(){const req=requiredIssues(),r=req.filter(i=>status(i.id).read).length,o=req.filter(i=>status(i.id).owned).length,ph=req.filter(i=>status(i.id).physical).length,dg=req.filter(i=>status(i.id).digital).length,p=Math.round(r/(req.length||1)*100);',
    'function renderStats(){const req=requiredIssues(),r=req.filter(i=>status(i.id).read).length,o=req.filter(i=>status(i.id).owned).length,ph=req.filter(i=>status(i.id).physicalCovered).length,dg=req.filter(i=>status(i.id).digital).length,p=Math.round(r/(req.length||1)*100);',
    "route physical coverage stat",
)
app = replace_once(
    app,
    '  const publicationBadge=currentCharacter.timelineMode?`<span class="publicationBadge">${esc(i.series)}</span>`:"";\n  return `<article',
    '  const publicationBadge=currentCharacter.timelineMode?`<span class="publicationBadge">${esc(i.series)}</span>`:"";\n  const editionBadge=st.ownedEditions?.length?`<span class="editionCoverageBadge">Coperto da ${esc(st.ownedEditions.map(item=>item.name).join(", "))}</span>`:"";\n  const editionButton=st.editionOptions?.length?`<button type="button" class="${st.alternativePhysical?"on edition":"edition"}" data-editions="${esc(i.id)}">${icon(st.alternativePhysical?"check":"archive")}<span>${st.alternativePhysical?"Edizione":"Edizioni"}</span></button>`:"";\n  return `<article',
    "issue edition metadata",
)
app = replace_once(
    app,
    '<div class="issueBadges">${publicationBadge}${insertBadge}</div>',
    '<div class="issueBadges">${publicationBadge}${insertBadge}${editionBadge}</div>',
    "edition coverage badge",
)
app = replace_once(
    app,
    '<button type="button" class="${st.physical?"on physical":""}" data-physical="${esc(i.id)}">${icon(st.physical?"check":"archive")}<span>Fisico</span></button><button type="button" class="${st.digital?"on digital":""}"',
    '<button type="button" class="${st.physical?"on physical":""}" data-physical="${esc(i.id)}">${icon(st.physical?"check":"archive")}<span>Fisico</span></button>${editionButton}<button type="button" class="${st.digital?"on digital":""}"',
    "edition button in issue status",
)
app = replace_once(
    app,
    '  document.querySelectorAll("[data-digital]").forEach(b=>b.onclick=()=>setStatus(b.dataset.digital,{digital:!status(b.dataset.digital).digital}));\n',
    '  document.querySelectorAll("[data-digital]").forEach(b=>b.onclick=()=>setStatus(b.dataset.digital,{digital:!status(b.dataset.digital).digital}));\n  document.querySelectorAll("[data-editions]").forEach(b=>b.onclick=()=>openEditionPicker(b.dataset.editions));\n',
    "bind edition buttons",
)
app = replace_once(
    app,
    'if(id==="ironman")ns.push(["Ordine narrativo","Il numero grande indica la posizione nel percorso di lettura; il titolo conserva il numero dell’edizione italiana. Gli inserti cronologici obbligatori sono evidenziati."]);',
    'if(id==="ironman")ns.push(["Ordine narrativo","Il numero grande indica la posizione nel percorso di lettura; il titolo conserva il numero dell’edizione italiana. Gli inserti cronologici obbligatori sono evidenziati."],["Edizioni alternative","Quando una raccolta copre le storie di uno o più spillati, usa il pulsante Edizioni: la tappa risulterà recuperata senza segnare come posseduto uno spillato che non hai."]);',
    "Iron Man editions notice",
)
app_path.write_text(app, encoding="utf-8")

# Patch profile / global collection.
profile_path = ROOT / "js" / "profile-ui.js"
profile = profile_path.read_text(encoding="utf-8")
profile = replace_once(
    profile,
    '    s.collection ??= {};\n    s.wishlist ??= {};',
    '    s.collection ??= {};\n    s.editions ??= {};\n    window.MarvelEditions?.normalizeState(s);\n    s.wishlist ??= {};',
    "profile state editions",
)
profile = replace_once(
    profile,
    '''  function itemStatus(id){\n    const entry = state().collection?.[id] || {};\n    return {\n      physical: !!entry.physical,\n      digital: !!entry.digital,\n      owned: !!entry.physical || !!entry.digital,\n      wishlist: !!state().wishlist?.[id],\n      read: readIds().has(id),\n    };\n  }\n''',
    '''  function itemStatus(id){\n    const s = state();\n    const entry = s.collection?.[id] || {};\n    const editionPhysical = !!window.MarvelEditions?.get(id) && !!window.MarvelEditions?.isOwned(s,id);\n    const physical = !!entry.physical || editionPhysical;\n    const digital = !!entry.digital;\n    return {physical,digital,owned:physical||digital,wishlist:!!s.wishlist?.[id],read:readIds().has(id),editionPhysical};\n  }\n''',
    "profile item status",
)
profile = replace_once(
    profile,
    '''  function collectionStats(){\n    const values = Object.values(state().collection || {});\n    const physical = values.filter(x => x?.physical).length;\n    const digital = values.filter(x => x?.digital).length;\n    const both = values.filter(x => x?.physical && x?.digital).length;\n    const owned = values.filter(x => x?.physical || x?.digital).length;\n''',
    '''  function collectionStats(){\n    const s = state();\n    const values = Object.values(s.collection || {});\n    const directPhysical = values.filter(x => x?.physical).length;\n    const physical = window.MarvelEditions?.physicalObjectCount(s) ?? directPhysical;\n    const digital = values.filter(x => x?.digital).length;\n    const both = values.filter(x => x?.physical && x?.digital).length;\n    const owned = window.MarvelEditions?.ownedPublicationCount(s) ?? values.filter(x => x?.physical || x?.digital).length;\n''',
    "profile collection stats",
)
profile = replace_once(
    profile,
    '''  function toggleFormat(id, key){\n''',
    '''  function toggleEdition(id){\n    const s = state();\n    window.MarvelEditions?.setOwned(s,id,!window.MarvelEditions?.isOwned(s,id));\n    save();\n    void render();\n  }\n\n  function toggleFormat(id, key){\n''',
    "profile edition toggle",
)
profile = replace_once(
    profile,
    '''  function collectionStats(){''',
    '''  function allCatalogItems(){\n    const merged = new Map((catalog?.issues || []).map(item => [item.id,{...item}]));\n    for(const edition of window.MarvelEditions?.catalogItems(manifest()) || []) merged.set(edition.id,{...(merged.get(edition.id)||{}),...edition});\n    return [...merged.values()];\n  }\n\n  function collectionStats(){''',
    "profile alternative catalog",
)
profile = replace_once(
    profile,
    '      tabButton("catalog","Catalogo",catalog?.total || 0),',
    '      tabButton("catalog","Catalogo",allCatalogItems().length),',
    "catalog tab count",
)
profile = replace_once(
    profile,
    '    const total = catalog?.total || 0;',
    '    const total = allCatalogItems().length;',
    "overview catalog total",
)
profile = replace_once(
    profile,
    '''  function itemPool(){\n    const all = catalog?.issues || [];\n    const s = state();\n    const reads = readIds();\n    if(activeTab === "collection") return all.filter(item => s.collection?.[item.id]?.physical || s.collection?.[item.id]?.digital);\n''',
    '''  function itemPool(){\n    const all = allCatalogItems();\n    const s = state();\n    const reads = readIds();\n    if(activeTab === "collection") return all.filter(item => itemStatus(item.id).owned);\n''',
    "collection includes alternative editions",
)
profile = replace_once(
    profile,
    '''  function issueCard(item,{listId=null}={}){\n    const st = itemStatus(item.id);\n''',
    '''  function issueCard(item,{listId=null}={}){\n    const st = itemStatus(item.id);\n    const isAlternative = !!item.isAlternativeEdition;\n''',
    "edition card flag",
)
profile = replace_once(
    profile,
    '<div class="profileIssueBadges">${st.physical?',
    '<div class="profileIssueBadges">${isAlternative?\'<span class="editionAlternative">Edizione alternativa</span>\':""}${st.physical?',
    "profile edition badge",
)
profile = replace_once(
    profile,
    '<article class="profileIssueCard" data-profile-issue="${esc(item.id)}">',
    '<article class="profileIssueCard ${isAlternative?"editionCard":""}" data-profile-issue="${esc(item.id)}">',
    "profile edition card class",
)
profile = replace_once(
    profile,
    '''        <button type="button" class="${st.physical?"on physical":""}" data-profile-physical="${esc(item.id)}">Fisico</button>\n        <button type="button" class="${st.digital?"on digital":""}" data-profile-digital="${esc(item.id)}">Digitale</button>''',
    '''        ${isAlternative?`<button type="button" class="${st.physical?"on physical":""}" data-profile-edition="${esc(item.id)}">${st.physical?"✓ ":""}Fisico</button>`:`<button type="button" class="${st.physical?"on physical":""}" data-profile-physical="${esc(item.id)}">Fisico</button><button type="button" class="${st.digital?"on digital":""}" data-profile-digital="${esc(item.id)}">Digitale</button>`}''',
    "profile edition physical action",
)
profile = replace_once(
    profile,
    '    root.querySelectorAll("[data-profile-physical]").forEach(button => button.onclick = () => toggleFormat(button.dataset.profilePhysical,"physical"));\n',
    '    root.querySelectorAll("[data-profile-physical]").forEach(button => button.onclick = () => toggleFormat(button.dataset.profilePhysical,"physical"));\n    root.querySelectorAll("[data-profile-edition]").forEach(button => button.onclick = () => toggleEdition(button.dataset.profileEdition));\n',
    "bind profile edition",
)
profile_path.write_text(profile, encoding="utf-8")

# Patch index/cache and load order.
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
index = replace_once(index, '<link rel="stylesheet" href="css/profile.css?v=1">', '<link rel="stylesheet" href="css/profile.css?v=1">\n  <link rel="stylesheet" href="css/editions.css?v=1">', "editions stylesheet")
index = replace_once(index, '<script src="js/profile-ui.js?v=1"></script>\n<script type="module" src="js/app.js?v=11"></script>', '<script src="js/editions.js?v=1"></script>\n<script src="js/profile-ui.js?v=2"></script>\n<script type="module" src="js/app.js?v=12"></script>', "editions scripts")
index_path.write_text(index, encoding="utf-8")

print("Alternative editions installed: Iron Man Credere -> IRONM3_P:1,2,3")
