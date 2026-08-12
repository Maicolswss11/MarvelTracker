const HUB_SESSION_KEY = "marvel_archive_last_hub";

let hubManifest = null;
let pathManifest = null;
let uiArt = {paths:{},hubs:{}};
let pathIconCatalog = {version:1,paths:{}};
let activeHubId = null;
let progressSnapshot = new Map();

const byId = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

function hubById(id){ return hubManifest?.hubs?.find(hub => hub.id === id) || null; }
function pathById(id){ return pathManifest?.characters?.find(path => path.id === id) || null; }
function pathTypeLabel(path){
  const labels={team:"Squadra",character:"Personaggio",universe:"Percorso universo",event:"Evento",collection:"Percorso",archive:"Archivio storico"};
  return labels[path?.type] || "Percorso";
}
function pathHubIds(path){ return Array.isArray(path?.hubs) ? path.hubs : path?.primaryHub ? [path.primaryHub] : []; }

function pathLogoSource(path){
  const override = pathIconCatalog?.paths?.[path?.id] || "";
  return {logo:override || path?.logo || "",override:!!override};
}
function pathLogoUrl(path){
  const {logo,override} = pathLogoSource(path);
  if(!logo) return "";
  const separator = logo.includes("?") ? "&" : "?";
  const version = override ? pathIconCatalog.version : pathManifest?.version;
  return `${logo}${separator}v=${encodeURIComponent(version||1)}`;
}
function pathArtworkMarkup(path){
  const fallback = pathLogoUrl(path);
  const raster = /\.(?:png|jpe?g|webp)(?:[?#]|$)/i.test(pathLogoSource(path).logo);
  if(path?.type === "character" && fallback){
    return `<img class="pathArtPrimary pathCharacterPortrait pathIconImage ${raster?"pathIconRaster":"pathIconVector"}" loading="lazy" src="${esc(fallback)}" alt="" data-path-icon-id="${esc(path.id)}" onerror="this.remove()">`;
  }
  const cover = uiArt?.paths?.[path?.id] || "";
  return `${cover?`<img class="pathArtPrimary" loading="lazy" src="${esc(cover)}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">`:""}${fallback?`<img class="pathArtFallback pathIconImage ${raster?"pathIconRaster":"pathIconVector"}" loading="lazy" src="${esc(fallback)}" alt="" data-path-icon-id="${esc(path?.id||"")}">`:""}`;
}
function hubArtworkUrls(hub){
  return [...new Set(uiArt?.hubs?.[hub?.id] || [])].filter(Boolean).slice(0,4);
}
function hubArtworkMarkup(hub){
  const covers = hubArtworkUrls(hub);
  if(!covers.length) return "";
  return `<span class="hubCardArt" aria-hidden="true">${covers.map(src=>`<img loading="lazy" src="${esc(src)}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">`).join("")}</span><span class="hubCardShade" aria-hidden="true"></span>`;
}
function hubDetailArtworkMarkup(hub){
  const covers = hubArtworkUrls(hub);
  if(!covers.length) return `<div class="hubDetailMonogram" aria-hidden="true">${esc((hub?.name || "M").charAt(0))}</div>`;
  return `<div class="hubDetailArtwork" aria-hidden="true">${covers.map(src=>`<span><img loading="lazy" src="${esc(src)}" alt="" referrerpolicy="no-referrer" onerror="this.parentElement.remove()"></span>`).join("")}</div>`;
}

function collectProgress(){
  const grid = byId("homeCharacterGrid");
  if(!grid) return;
  const next = new Map();
  grid.querySelectorAll("[data-home-char]").forEach(card => {
    const id = card.dataset.homeChar;
    const pct = card.querySelector(".homeCharPercent")?.textContent?.trim() || "0%";
    const count = card.querySelector(".homeCharProgressTop b")?.textContent?.trim() || "";
    next.set(id,{pct,count});
  });
  if(next.size) progressSnapshot = next;
}

function hubPaths(hub){
  const ids = new Set();
  for(const group of hub?.groups || []) for(const id of group.paths || []) ids.add(id);
  for(const path of pathManifest?.characters || []) if(pathHubIds(path).includes(hub?.id)) ids.add(path.id);
  return [...ids].map(pathById).filter(Boolean);
}

function hubStats(hub,visited=new Set()){
  if(!hub || visited.has(hub.id)) return {paths:[],total:0};
  visited.add(hub.id);
  const unique = new Map(hubPaths(hub).map(path=>[path.id,path]));
  const childIds = new Set([
    ...(hub.sections?.flatMap(section=>section.items||[]) || []),
    ...(hubManifest?.hubs||[]).filter(child=>child.parent===hub.id).map(child=>child.id)
  ]);
  for(const childId of childIds){
    const child = hubById(childId);
    const nested = hubStats(child,new Set(visited));
    for(const path of nested.paths) unique.set(path.id,path);
  }
  const paths = [...unique.values()];
  const total = paths.reduce((sum,path)=>sum+(Number(path.totalRequired)||0),0);
  return {paths,total};
}

function setLastHub(id){
  if(id) sessionStorage.setItem(HUB_SESSION_KEY,id);
}

function rememberedHubForPath(path){
  const remembered = sessionStorage.getItem(HUB_SESSION_KEY);
  if(remembered && pathHubIds(path).includes(remembered)) return hubById(remembered);
  return hubById(path?.primaryHub) || hubById(pathHubIds(path)[0]) || null;
}

function openPath(pathId, hubId = null){
  if(hubId) setLastHub(hubId);
  location.hash = `#/${pathId}`;
}

let internalHomeNavigation = false;
function goToExplorer(hubId=null){
  internalHomeNavigation = true;
  if(!document.body.classList.contains("homeActive")){
    const homeControl = byId("trackerHomeBtn") || byId("homeBtn");
    if(homeControl) homeControl.click();
    else location.hash = "#/home";
  }
  internalHomeNavigation = false;
  activeHubId = hubId || null;
  ensureHomeExplorer();
  openHub(activeHubId);
  byId("hubExplorer")?.scrollIntoView({behavior:"smooth",block:"start"});
}

function hubCard(hub,{compact=false}={}){
  const stats = hubStats(hub);
  const coming = hub.status === "coming";
  const label = hub.type === "universe" ? "Universo" : hub.type === "event-index" ? "Eventi" : "Famiglia";
  const artwork = hubArtworkMarkup(hub);
  return `<button type="button" class="hubCard ${compact?"compact":""} ${coming?"coming":""} ${artwork?"withArt":""}" style="--hub-accent:${esc(hub.accent||"#ed1d24")}" data-open-hub="${esc(hub.id)}">
    ${artwork}<span class="hubCardGlow"></span>
    <span class="hubCardTop"><span class="hubType">${esc(label)}</span>${coming?'<span class="hubStatus">In preparazione</span>':`<span class="hubStatus live">${stats.paths.length} percorsi</span>`}</span>
    <span class="hubCardBody"><b>${esc(hub.name)}</b><span>${esc(hub.subtitle)}</span></span>
    <span class="hubCardBottom">${coming?"Struttura pronta":`${stats.total.toLocaleString("it-IT")} tappe mappate`}<span aria-hidden="true">→</span></span>
  </button>`;
}

function pathCard(path,hubId){
  const progress = progressSnapshot.get(path.id);
  const percentage = Math.max(0,Math.min(100,Number.parseFloat(progress?.pct) || 0));
  const progressLabel = progress?.count ? `${progress.count} letti` : `${Number(path.totalRequired||0).toLocaleString("it-IT")} tappe mappate`;
  return `<button type="button" class="hubPathCard" style="--path-accent:${esc(path.accent||"#ed1d24")}" data-hub-path="${esc(path.id)}" data-from-hub="${esc(hubId)}">
    <span class="hubPathLogo">${pathArtworkMarkup(path)}</span>
    <span class="hubPathMain"><small>${esc(pathTypeLabel(path))}</small><b>${esc(path.name)}</b><span>${esc(path.subtitle)}</span><em>${esc(String(path.start||"").split(" — ")[0])}</em></span>
    <span class="hubPathProgress"><span class="hubPathProgressValue"><b>${progress?esc(progress.pct):"0%"}</b><small>${esc(progressLabel)}</small></span><span class="hubPathTrack"><i style="width:${percentage}%"></i></span></span>
    <span class="hubPathArrow" aria-hidden="true">→</span>
  </button>`;
}

function breadcrumbHtml(hub){
  const parent = hub?.parent ? hubById(hub.parent) : null;
  return `<nav class="hubBreadcrumb" aria-label="Percorso di navigazione">
    <button type="button" class="hubHomeLevelsBtn" data-hub-home aria-label="Torna alla home dei livelli">← Home livelli</button>
    ${parent?`<span>›</span><button type="button" data-open-hub="${esc(parent.id)}">${esc(parent.name)}</button>`:""}
    ${hub?`<span>›</span><b>${esc(hub.name)}</b>`:""}
  </nav>`;
}

function renderRootExplorer(root){
  collectProgress();
  const topIds = ["main","ultimate-classic","ultimate-new","alternate","events"];
  const familyIds = ["avengers","xmen","spider","fantastic-four","mystic","street","cosmic"];
  root.innerHTML = `<div class="hubExplorerRoot">
    <div class="hubExplorerHeading"><div><span class="hubEyebrow">Esplora l'archivio</span><h2>Universi, famiglie ed eventi</h2><p>I percorsi non sono più una lista piatta: ogni storia può appartenere a più sezioni senza duplicare la tua collezione.</p></div></div>
    <section class="hubShelf"><div class="hubShelfHead"><div><span>Livello 1</span><h3>Universi e realtà</h3></div><small>La struttura è pronta anche per Ultimate, What If e crossover multiversali.</small></div><div class="hubGrid universeGrid">${topIds.map(id=>hubById(id)).filter(Boolean).map(h=>hubCard(h)).join("")}</div></section>
    <section class="hubShelf"><div class="hubShelfHead"><div><span>Terra-616</span><h3>Famiglie principali</h3></div><small>Un personaggio può comparire in più famiglie: Wanda, per esempio, è già collegata a Vendicatori e Mistico.</small></div><div class="hubGrid familyGrid">${familyIds.map(id=>hubById(id)).filter(Boolean).map(h=>hubCard(h,{compact:true})).join("")}</div></section>
  </div>`;
  bindHubControls(root);
}

function renderMainUniverse(root,hub){
  const families = (hub.sections?.flatMap(section=>section.items||[]) || []).map(hubById).filter(Boolean);
  const stats = hubStats(hub);
  root.innerHTML = `${breadcrumbHtml(hub)}<section class="hubDetailHero" style="--hub-accent:${esc(hub.accent)}"><div class="hubDetailCopy"><span class="hubEyebrow">Universo</span><h2>${esc(hub.name)}</h2><p>${esc(hub.subtitle)}</p></div><div class="hubDetailAside">${hubDetailArtworkMarkup(hub)}<div class="hubDetailStats"><b>${stats.paths.length}</b><span>percorsi</span><b>${stats.total.toLocaleString("it-IT")}</b><span>tappe</span></div></div></section>
    <section class="hubShelf"><div class="hubShelfHead"><div><span>Terra-616</span><h3>Famiglie narrative</h3></div><small>Apri una famiglia per vedere squadre, personaggi e percorsi collegati.</small></div><div class="hubGrid familyGrid">${families.map(h=>hubCard(h,{compact:true})).join("")}</div></section>`;
  bindHubControls(root);
}

function renderHubDetail(root,hub){
  collectProgress();
  const groups = hub.groups || [];
  const stats = hubStats(hub);
  const coming = hub.status === "coming" && !groups.length;
  root.innerHTML = `${breadcrumbHtml(hub)}
    <section class="hubDetailHero" style="--hub-accent:${esc(hub.accent)}"><div class="hubDetailCopy"><span class="hubEyebrow">${hub.type === "event-index" ? "Indice eventi" : hub.type === "universe" ? "Universo" : "Famiglia Marvel"}</span><h2>${esc(hub.name)}</h2><p>${esc(hub.subtitle)}</p></div><div class="hubDetailAside">${hubDetailArtworkMarkup(hub)}<div class="hubDetailStats"><b>${stats.paths.length}</b><span>percorsi</span><b>${stats.total.toLocaleString("it-IT")}</b><span>tappe</span></div></div></section>
    ${coming?`<section class="hubEmpty"><span>Struttura pronta</span><h3>${esc(hub.name)} sarà costruito qui.</h3><p>Il contenitore è già parte della nuova architettura. Quando aggiungeremo i dati, non serviranno altre modifiche alla navigazione.</p></section>`:
      groups.map(group=>`<section class="hubShelf pathShelf"><div class="hubShelfHead"><div><span>${esc(hub.name)}</span><h3>${esc(group.label)}</h3></div><small>${(group.paths||[]).length} percorsi</small></div><div class="hubPathGrid">${(group.paths||[]).map(pathById).filter(Boolean).map(path=>pathCard(path,hub.id)).join("")}</div></section>`).join("")}
  `;
  bindHubControls(root);
}

function bindHubControls(root){
  root.querySelectorAll("[data-open-hub]").forEach(button=>button.onclick=()=>openHub(button.dataset.openHub));
  root.querySelectorAll("[data-hub-home]").forEach(button=>button.onclick=()=>openHub(null));
  root.querySelectorAll("[data-hub-path]").forEach(button=>button.onclick=()=>openPath(button.dataset.hubPath,button.dataset.fromHub));
}

function openHub(id,{animate=true,scroll=true}={}){
  const root = byId("hubExplorer");
  if(!root) return;
  if(animate&&window.MarvelMotion?.sectionTransition)return window.MarvelMotion.sectionTransition(root,()=>openHub(id,{animate:false,scroll}));
  activeHubId = id || null;
  if(!id){ renderRootExplorer(root); document.dispatchEvent(new CustomEvent("marvel:render",{detail:{view:"hub"}})); return; }
  const hub = hubById(id);
  if(!hub){ renderRootExplorer(root); document.dispatchEvent(new CustomEvent("marvel:render",{detail:{view:"hub"}})); return; }
  setLastHub(id);
  if(id === "main") renderMainUniverse(root,hub); else renderHubDetail(root,hub);
  if(scroll)root.scrollIntoView({behavior:"smooth",block:"start"});
  document.dispatchEvent(new CustomEvent("marvel:render",{detail:{view:"hub"}}));
}

function ensureHomeExplorer(){
  const section = byId("homeCharactersSection");
  const legacyGrid = byId("homeCharacterGrid");
  if(!section || !legacyGrid) return;
  if(!document.body.classList.contains("hubUiEnabled")) document.body.classList.add("hubUiEnabled");
  legacyGrid.classList.add("hubLegacyGrid");
  let root = byId("hubExplorer");
  if(!root){
    root = document.createElement("div");
    root.id = "hubExplorer";
    root.className = "hubExplorer";
    legacyGrid.before(root);
  }
  if(!root.dataset.ready){ root.dataset.ready="1"; renderRootExplorer(root); }
}

function sidebarPathButton(path,currentId,hubId){
  return `<button type="button" class="hubSidePath ${path.id===currentId?"active":""}" style="--path-accent:${esc(path.accent)}" data-side-path="${esc(path.id)}" data-side-hub="${esc(hubId)}"><span class="hubSideArtwork">${pathArtworkMarkup(path)}</span><span><b>${esc(path.name)}</b><small>${esc(path.subtitle)}</small></span></button>`;
}

function renderTrackerContext(){
  const tracker = byId("trackerView");
  if(!tracker || tracker.hidden || !pathManifest || !hubManifest) return;
  const parts = location.hash.replace(/^#\/?/,"").split("/").filter(Boolean);
  const path = pathById(parts[0]);
  if(!path) return;
  const hub = rememberedHubForPath(path);
  if(!hub) return;

  let breadcrumb = byId("trackerHubBreadcrumb");
  if(!breadcrumb){
    breadcrumb = document.createElement("div");
    breadcrumb.id = "trackerHubBreadcrumb";
    breadcrumb.className = "trackerHubBreadcrumb";
    tracker.prepend(breadcrumb);
  }
  const parent = hub.parent ? hubById(hub.parent) : null;
  breadcrumb.innerHTML = `<button type="button" class="hubHomeLevelsBtn" data-tracker-home aria-label="Torna alla home dei livelli">← Home livelli</button><span>›</span>${parent?`<button type="button" data-tracker-parent="${esc(parent.id)}">${esc(parent.name)}</button><span>›</span>`:""}<button type="button" data-tracker-hub="${esc(hub.id)}">${esc(hub.name)}</button><span>›</span><b>${esc(path.name)}</b>`;
  breadcrumb.querySelector("[data-tracker-home]").onclick=()=>goToExplorer(null);
  breadcrumb.querySelector("[data-tracker-parent]")?.addEventListener("click",event=>goToExplorer(event.currentTarget.dataset.trackerParent));
  breadcrumb.querySelector("[data-tracker-hub]").onclick=()=>goToExplorer(hub.id);

  const legacy = byId("charGrid");
  if(!legacy) return;
  const sidebarLabel = legacy.previousElementSibling;
  if(sidebarLabel?.classList.contains("label")) sidebarLabel.textContent = "Sezione";
  legacy.classList.add("hubLegacySidebar");
  let nav = byId("hubSidebarNav");
  if(!nav){
    nav=document.createElement("div");
    nav.id="hubSidebarNav";
    nav.className="hubSidebarNav";
    legacy.before(nav);
  }
  const groups = hub.groups || [];
  nav.innerHTML = `<div class="hubSideHead" style="--hub-accent:${esc(hub.accent)}"><button type="button" data-side-back>←</button><span><small>Sezione</small><b>${esc(hub.name)}</b></span></div>${groups.map(group=>`<div class="hubSideGroup"><div class="hubSideLabel">${esc(group.label)}</div>${(group.paths||[]).map(pathById).filter(Boolean).map(item=>sidebarPathButton(item,path.id,hub.id)).join("")}</div>`).join("")}`;
  nav.querySelector("[data-side-back]").onclick=()=>goToExplorer(hub.id);
  nav.querySelectorAll("[data-side-path]").forEach(button=>button.onclick=()=>openPath(button.dataset.sidePath,button.dataset.sideHub));
}

function hideTrackerContextOnHome(){
  const breadcrumb=byId("trackerHubBreadcrumb");
  if(breadcrumb) breadcrumb.remove();
}

function refresh(){
  ensureHomeExplorer();
  collectProgress();
  if(location.hash === "#/home" || !location.hash){
    hideTrackerContextOnHome();
    if(activeHubId && byId("hubExplorer")) openHub(activeHubId,{animate:false,scroll:false});
  } else renderTrackerContext();
}

async function initHubUi(){
  try{
    const [hubResponse,pathResponse,artResponse,iconResponse] = await Promise.all([
      fetch("data/hubs.json",{cache:"no-cache"}),
      fetch("data/characters.json",{cache:"no-cache"}),
      fetch("data/ui-art.json",{cache:"no-cache"}).catch(()=>null),
      fetch("data/path-icons.json",{cache:"no-cache"}).catch(()=>null)
    ]);
    if(!hubResponse.ok || !pathResponse.ok) throw new Error("Impossibile caricare la tassonomia Marvel");
    hubManifest = await hubResponse.json();
    pathManifest = await pathResponse.json();
    if(artResponse?.ok) uiArt = await artResponse.json();
    if(iconResponse?.ok) pathIconCatalog = await iconResponse.json();
    ensureHomeExplorer();
    refresh();
    ["homeBtn","trackerHomeBtn"].forEach(id=>byId(id)?.addEventListener("click",()=>{
    if(internalHomeNavigation) return;
    activeHubId=null;
    requestAnimationFrame(()=>{
      ensureHomeExplorer();
      openHub(null);
    });
  },{capture:true}));
  const exploreButton=byId("homeExplore");
  if(exploreButton) exploreButton.addEventListener("click",()=>goToExplorer(null));

    const legacyGrid=byId("homeCharacterGrid");
    if(legacyGrid){
      new MutationObserver(()=>{
        collectProgress();
        if(location.hash === "#/home" && byId("hubExplorer")) openHub(activeHubId,{animate:false,scroll:false});
      }).observe(legacyGrid,{childList:true,subtree:true,characterData:true});
    }
    window.addEventListener("hashchange",()=>setTimeout(refresh,0));
    let lastHomeActive = document.body.classList.contains("homeActive");
    new MutationObserver(()=>{
      const homeActive = document.body.classList.contains("homeActive");
      if(homeActive === lastHomeActive) return;
      lastHomeActive = homeActive;
      setTimeout(refresh,0);
    }).observe(document.body,{attributes:true,attributeFilter:["class"]});
  }catch(error){
    console.error("Hub UI non disponibile",error);
  }
}

initHubUi();
