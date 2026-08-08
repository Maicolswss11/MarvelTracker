const HUB_SESSION_KEY = "marvel_archive_last_hub";

let hubManifest = null;
let pathManifest = null;
let activeHubId = null;
let progressSnapshot = new Map();

const byId = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

function hubById(id){ return hubManifest?.hubs?.find(hub => hub.id === id) || null; }
function pathById(id){ return pathManifest?.characters?.find(path => path.id === id) || null; }
function pathTypeLabel(path){ return path?.type === "team" ? "Squadra" : "Personaggio"; }
function pathHubIds(path){ return Array.isArray(path?.hubs) ? path.hubs : path?.primaryHub ? [path.primaryHub] : []; }

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

function hubStats(hub){
  const paths = hubPaths(hub);
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

function returnHomeThen(callback){
  if(location.hash !== "#/home") location.hash = "#/home";
  requestAnimationFrame(()=>requestAnimationFrame(callback));
}

function hubCard(hub,{compact=false}={}){
  const stats = hubStats(hub);
  const coming = hub.status === "coming";
  const label = hub.type === "universe" ? "Universo" : hub.type === "event-index" ? "Eventi" : "Famiglia";
  return `<button type="button" class="hubCard ${compact?"compact":""} ${coming?"coming":""}" style="--hub-accent:${esc(hub.accent||"#ed1d24")}" data-open-hub="${esc(hub.id)}">
    <span class="hubCardGlow"></span>
    <span class="hubCardTop"><span class="hubType">${esc(label)}</span>${coming?'<span class="hubStatus">In preparazione</span>':`<span class="hubStatus live">${stats.paths.length} percorsi</span>`}</span>
    <span class="hubCardBody"><b>${esc(hub.name)}</b><span>${esc(hub.subtitle)}</span></span>
    <span class="hubCardBottom">${coming?"Struttura pronta":`${stats.total.toLocaleString("it-IT")} tappe mappate`}<span aria-hidden="true">→</span></span>
  </button>`;
}

function pathCard(path,hubId){
  const progress = progressSnapshot.get(path.id);
  return `<button type="button" class="hubPathCard" style="--path-accent:${esc(path.accent||"#ed1d24")}" data-hub-path="${esc(path.id)}" data-from-hub="${esc(hubId)}">
    <span class="hubPathLogo"><img src="${esc(path.logo)}?v=${encodeURIComponent(pathManifest.version||1)}" alt="" onerror="this.style.display='none'"></span>
    <span class="hubPathMain"><small>${esc(pathTypeLabel(path))}</small><b>${esc(path.name)}</b><span>${esc(path.subtitle)}</span></span>
    <span class="hubPathProgress">${progress?`<b>${esc(progress.pct)}</b><small>${esc(progress.count)}</small>`:`<b>${Number(path.totalRequired||0).toLocaleString("it-IT")}</b><small>tappe</small>`}</span>
    <span class="hubPathArrow" aria-hidden="true">→</span>
  </button>`;
}

function breadcrumbHtml(hub){
  const parent = hub?.parent ? hubById(hub.parent) : null;
  return `<nav class="hubBreadcrumb" aria-label="Percorso di navigazione">
    <button type="button" data-hub-home>Marvel Archive</button>
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
  root.innerHTML = `${breadcrumbHtml(hub)}<section class="hubDetailHero" style="--hub-accent:${esc(hub.accent)}"><span class="hubEyebrow">Universo</span><h2>${esc(hub.name)}</h2><p>${esc(hub.subtitle)}</p></section>
    <section class="hubShelf"><div class="hubShelfHead"><div><span>Terra-616</span><h3>Famiglie narrative</h3></div><small>Apri una famiglia per vedere squadre, personaggi e percorsi collegati.</small></div><div class="hubGrid familyGrid">${families.map(h=>hubCard(h,{compact:true})).join("")}</div></section>`;
  bindHubControls(root);
}

function renderHubDetail(root,hub){
  collectProgress();
  const groups = hub.groups || [];
  const stats = hubStats(hub);
  const coming = hub.status === "coming" && !groups.length;
  root.innerHTML = `${breadcrumbHtml(hub)}
    <section class="hubDetailHero" style="--hub-accent:${esc(hub.accent)}"><div><span class="hubEyebrow">${hub.type === "event-index" ? "Indice eventi" : hub.type === "universe" ? "Universo" : "Famiglia Marvel"}</span><h2>${esc(hub.name)}</h2><p>${esc(hub.subtitle)}</p></div><div class="hubDetailStats"><b>${stats.paths.length}</b><span>percorsi</span><b>${stats.total.toLocaleString("it-IT")}</b><span>tappe</span></div></section>
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

function openHub(id){
  const root = byId("hubExplorer");
  if(!root) return;
  activeHubId = id || null;
  if(!id){ renderRootExplorer(root); return; }
  const hub = hubById(id);
  if(!hub){ renderRootExplorer(root); return; }
  setLastHub(id);
  if(id === "main") renderMainUniverse(root,hub); else renderHubDetail(root,hub);
  root.scrollIntoView({behavior:"smooth",block:"start"});
}

function ensureHomeExplorer(){
  const section = byId("homeCharactersSection");
  const legacyGrid = byId("homeCharacterGrid");
  if(!section || !legacyGrid) return;
  document.body.classList.add("hubUiEnabled");
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
  return `<button type="button" class="hubSidePath ${path.id===currentId?"active":""}" style="--path-accent:${esc(path.accent)}" data-side-path="${esc(path.id)}" data-side-hub="${esc(hubId)}"><img src="${esc(path.logo)}?v=${encodeURIComponent(pathManifest.version||1)}" alt="" onerror="this.style.visibility='hidden'"><span><b>${esc(path.name)}</b><small>${esc(path.subtitle)}</small></span></button>`;
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
  breadcrumb.innerHTML = `<button type="button" data-tracker-home>Marvel Archive</button><span>›</span>${parent?`<button type="button" data-tracker-parent="${esc(parent.id)}">${esc(parent.name)}</button><span>›</span>`:""}<button type="button" data-tracker-hub="${esc(hub.id)}">${esc(hub.name)}</button><span>›</span><b>${esc(path.name)}</b>`;
  breadcrumb.querySelector("[data-tracker-home]").onclick=()=>returnHomeThen(()=>openHub(null));
  breadcrumb.querySelector("[data-tracker-parent]")?.addEventListener("click",event=>returnHomeThen(()=>openHub(event.currentTarget.dataset.trackerParent)));
  breadcrumb.querySelector("[data-tracker-hub]").onclick=()=>returnHomeThen(()=>openHub(hub.id));

  const legacy = byId("charGrid");
  if(!legacy) return;
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
  nav.querySelector("[data-side-back]").onclick=()=>returnHomeThen(()=>openHub(hub.id));
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
    if(activeHubId && byId("hubExplorer")) openHub(activeHubId);
  } else renderTrackerContext();
}

async function initHubUi(){
  try{
    const [hubResponse,pathResponse] = await Promise.all([
      fetch("data/hubs.json",{cache:"no-cache"}),
      fetch("data/characters.json",{cache:"no-cache"})
    ]);
    if(!hubResponse.ok || !pathResponse.ok) throw new Error("Impossibile caricare la tassonomia Marvel");
    hubManifest = await hubResponse.json();
    pathManifest = await pathResponse.json();
    ensureHomeExplorer();
    refresh();

    const legacyGrid=byId("homeCharacterGrid");
    if(legacyGrid){
      new MutationObserver(()=>{
        collectProgress();
        if(location.hash === "#/home" && byId("hubExplorer")) openHub(activeHubId);
      }).observe(legacyGrid,{childList:true,subtree:true,characterData:true});
    }
    window.addEventListener("hashchange",()=>setTimeout(refresh,0));
    new MutationObserver(()=>refresh()).observe(document.body,{attributes:true,attributeFilter:["class"]});
  }catch(error){
    console.error("Hub UI non disponibile",error);
  }
}

initHubUi();
