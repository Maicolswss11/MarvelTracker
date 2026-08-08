import { fetchCloudState, flushCloudState, hasUnsyncedState, initAccount, queueCloudState, signIn, signOut, signUp } from "./account.js";

const STORAGE_KEY = "marvel_archive_characters_v12";
let activeStorageKey = STORAGE_KEY;
const characterCache = new Map();
let manifest = null;
let currentMeta = null;
let currentCharacter = null;
let activeCharacter = "ironman";
let activeEra = "Tutte";
let activeSeries = "Tutte";
let optionalVisible = false;
let characterSwitchRequest = 0;
let homeContinueRequest = 0;
let accountActivationRequest = 0;
let activatedAccountId = null;
let accountView = {configured:false,user:null,displayName:"Lettore Marvel",syncStatus:"local",phase:"loading"};
let authMode = "login";
let state = loadState();

const $ = (id) => document.getElementById(id);
const els = {
  charGrid: $("charGrid"), doneCount: $("doneCount"), totalCount: $("totalCount"), progressBar: $("progressBar"), ownedCount: $("ownedCount"), pct: $("pct"),
  seriesNav: $("seriesNav"), jumpNext: $("jumpNext"), showOptional: $("showOptional"), exportBtn: $("exportBtn"), importFile: $("importFile"), resetBtn: $("resetBtn"),
  footerNote: $("footerNote"), logoSub: $("logoSub"), topTitle: $("topTitle"), topSub: $("topSub"), search: $("search"), compactBtn: $("compactBtn"), heroLabel: $("heroLabel"), heroTitle: $("heroTitle"), heroDesc: $("heroDesc"), nextPanel: $("nextPanel"), route: $("route"), noticeWrap: $("noticeWrap"), filterBar: $("filterBar"), seriesBlocks: $("seriesBlocks"),
  homeView: $("homeView"), trackerView: $("trackerView"), homeBtn: $("homeBtn"), trackerHomeBtn: $("trackerHomeBtn"), trackerHomeIcon: $("trackerHomeIcon"), homeTopResume: $("homeTopResume"), homeResume: $("homeResume"), homeExplore: $("homeExplore"), homeHeroIcons: $("homeHeroIcons"), homeStats: $("homeStats"), homeCharacterGrid: $("homeCharacterGrid"), homeCharactersSection: $("homeCharactersSection"), homeContinue: $("homeContinue"), homeGreetingName: $("homeGreetingName"),
  homeAccountBtn: $("homeAccountBtn"), trackerAccountBtn: $("trackerAccountBtn"), accountDialog: $("accountDialog"), accountLoading: $("accountLoading"), accountSetup: $("accountSetup"), accountAuth: $("accountAuth"), accountSigned: $("accountSigned"), loginTab: $("loginTab"), registerTab: $("registerTab"), authForm: $("authForm"), displayNameField: $("displayNameField"), authDisplayName: $("authDisplayName"), authEmail: $("authEmail"), authPassword: $("authPassword"), authSubmit: $("authSubmit"), authMessage: $("authMessage"), accountProfileName: $("accountProfileName"), accountEmail: $("accountEmail"), accountSyncIcon: $("accountSyncIcon"), accountSyncTitle: $("accountSyncTitle"), accountSyncDetail: $("accountSyncDetail"), syncNowBtn: $("syncNowBtn"), signOutBtn: $("signOutBtn")
};

const ICONS = {
  archive: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 8v12h16V8"/><path d="M2.5 4h19v4h-19z"/><path d="M9 12h6"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.5 5.5A3.5 3.5 0 0 1 7 2h4v18H7a3.5 3.5 0 0 0-3.5 2z"/><path d="M20.5 5.5A3.5 3.5 0 0 0 17 2h-4v18h4a3.5 3.5 0 0 1 3.5 2z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="m8 12 2.7 2.7L16.5 9"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17.5 19H6a4 4 0 0 1-.4-8A6.5 6.5 0 0 1 18 9.5 4.8 4.8 0 0 1 17.5 19Z"/><path d="m9 14 2 2 4-4"/></svg>',
  sync: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M20 7h-5V2"/><path d="M20 7a8 8 0 0 0-14-2"/><path d="M4 17h5v5"/><path d="M4 17a8 8 0 0 0 14 2"/></svg>',
  offline: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m3 3 18 18"/><path d="M17.5 19H6a4 4 0 0 1-.4-8 6.5 6.5 0 0 1 .8-2.1"/><path d="M9.4 5.5A6.5 6.5 0 0 1 18 9.5 4.8 4.8 0 0 1 20 17"/></svg>',
  paths: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="6" cy="5" r="2"/><circle cx="18" cy="19" r="2"/><path d="M8 5h3a3 3 0 0 1 3 3v8a3 3 0 0 0 3 3h-1"/><path d="M14 9h3a3 3 0 0 0 3-3V5"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/></svg>'
};
function icon(name){return ICONS[name]||""}

function esc(x){return String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function normalizeState(x){
  x ??= {}; x.characters ??= {}; x.collection ??= {};
  if(manifest){ for(const c of manifest.characters){ x.characters[c.id] ??= {issues:{}}; x.characters[c.id].issues ??= {}; } }
  for(const c of Object.values(x.characters||{})){ for(const [id,v] of Object.entries(c.issues||{})){ if(v?.owned) x.collection[id]={...(x.collection[id]||{}),owned:true}; } }
  return x;
}
function loadState(key=activeStorageKey){try{return normalizeState(JSON.parse(localStorage.getItem(key)))}catch{return normalizeState({characters:{},collection:{}})}}
function saveState({sync=true}={}){state.activeCharacter=activeCharacter;localStorage.setItem(activeStorageKey,JSON.stringify(state));if(sync&&accountView.user)queueCloudState(state)}
function bucket(){state.characters[activeCharacter]??={issues:{}};state.characters[activeCharacter].issues??={};return state.characters[activeCharacter].issues}
function status(id){return {owned:!!state.collection?.[id]?.owned,read:!!bucket()[id]?.read}}
function setStatus(id,patch){state.collection??={};if(Object.hasOwn(patch,"owned"))state.collection[id]={...(state.collection[id]||{}),owned:!!patch.owned};if(Object.hasOwn(patch,"read"))bucket()[id]={...(bucket()[id]||{}),read:!!patch.read};saveState();renderAll()}
function requiredIssues(){return currentCharacter.issues.filter(i=>i.required!==false&&!i.future)}
function nextIssue(){return requiredIssues().find(i=>!status(i.id).read)||null}
function pad3(n){return String(n).padStart(3,"0")}
function versioned(path){
  const separator=path.includes("?")?"&":"?";
  return `${path}${separator}v=${encodeURIComponent(manifest?.version||1)}`;
}
function coverPlaceholder(i,accentOverride=null){
  const accent=accentOverride||currentCharacter?.accent||currentMeta?.accent||"#43d7ff",safe=s=>String(s??"").replace(/[<>&]/g,m=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[m]));
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 600"><rect width="420" height="600" fill="#0b1118"/><rect x="18" y="18" width="384" height="564" rx="22" fill="none" stroke="${accent}" stroke-width="4" opacity=".6"/><text x="34" y="76" font-family="Arial" font-size="24" font-weight="700" fill="${accent}">${safe(i.series)}</text><text x="34" y="138" font-family="Arial" font-size="48" font-weight="900" fill="#fff">#${pad3(i.n)}</text><foreignObject x="34" y="175" width="352" height="270"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial;color:#d8e2eb;font-size:27px;font-weight:800;line-height:1.18">${safe(i.title)}</div></foreignObject><text x="34" y="548" font-family="Arial" font-size="17" fill="#8292a3">Copertina remota non disponibile</text></svg>`;
  return "data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);
}
window.coverFail = (img)=>{if(img.dataset.failed==="1"){img.style.display="none";return}img.dataset.failed="1";img.src=img.dataset.placeholder};
function coverImg(i,lazy=true,accent=null){return `<img ${lazy?'loading="lazy" ':''}src="${esc(i.cover||coverPlaceholder(i,accent))}" data-placeholder="${coverPlaceholder(i,accent)}" alt="${esc(i.name)}" referrerpolicy="no-referrer" onerror="coverFail(this)">`}

async function loadManifest(){
  const r=await fetch("data/characters.json",{cache:"no-cache"}); if(!r.ok)throw new Error(`Manifest HTTP ${r.status}`); manifest=await r.json(); state=normalizeState(state);
}
async function loadEncodedCharacter(id, meta){
  if(typeof DecompressionStream!=="function") throw new Error("Il browser non supporta la decompressione gzip richiesta dal tracker. Aggiorna il browser e riprova.");
  const specResponse=await fetch(versioned(`data/encoded/${id}.json`),{cache:"no-cache"});
  if(!specResponse.ok) throw new Error(`${meta.name}: manifest dati compressi HTTP ${specResponse.status}`);
  const spec=await specResponse.json();
  if(spec.encoding!=="gzip-base64-parts"||!Array.isArray(spec.sources)) throw new Error(`${meta.name}: formato dati compressi non riconosciuto`);
  const chunks=await Promise.all(spec.sources.map(async src=>{
    const response=await fetch(versioned(src),{cache:"no-cache"});
    if(!response.ok) throw new Error(`${meta.name}: ${src} HTTP ${response.status}`);
    return (await response.text()).replace(/\s+/g,"");
  }));
  const binary=atob(chunks.join(""));
  const bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++) bytes[i]=binary.charCodeAt(i);
  const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  const character=JSON.parse(await new Response(stream).text());
  if(character.id!==id||!Array.isArray(character.issues)) throw new Error(`${meta.name}: archivio dati incompleto`);
  return character;
}
async function loadCharacter(id){
  if(characterCache.has(id))return characterCache.get(id);
  const meta=manifest.characters.find(c=>c.id===id); if(!meta)throw new Error(`Personaggio sconosciuto: ${id}`);
  const r=await fetch(versioned(meta.data),{cache:"no-cache"}); if(!r.ok)throw new Error(`${meta.name}: HTTP ${r.status}`); let c=await r.json();
  if(Array.isArray(c.issueSources)) c=await loadEncodedCharacter(id,meta);
  c.issues??=[];
  c.issues.sort((a,b)=>(a.seq??Number.MAX_SAFE_INTEGER)-(b.seq??Number.MAX_SAFE_INTEGER)||a.n-b.n);
  characterCache.set(id,c); return c;
}
function parseHash(){const p=location.hash.replace(/^#\/?/,"").split("/").filter(Boolean);if(!p.length||p[0]==="home")return {view:"home",character:null,issue:null};return {view:"character",character:p[0],issue:p[1]?Number(p[1]):null}}
async function switchCharacter(id,{updateHash=true,issue=null}={}){
  const requestId=++characterSwitchRequest;
  const meta=manifest.characters.find(c=>c.id===id)||manifest.characters[0]; activeCharacter=meta.id; currentMeta=meta;
  document.body.classList.remove("homeActive");
  els.homeView.hidden=true;
  els.trackerView.hidden=false;
  document.documentElement.style.setProperty("--accent",meta.accent);
  renderCharacters();
  els.seriesBlocks.innerHTML='<div class="loading">Caricamento dati…</div>';
  let character;
  try{character=await loadCharacter(meta.id)}catch(error){
    if(requestId!==characterSwitchRequest)return false;
    console.error(error);
    els.topTitle.textContent=`${meta.name} Reading System`;
    els.topSub.textContent="Archivio non disponibile";
    els.seriesBlocks.innerHTML=`<div class="loading error"><b>Impossibile caricare ${esc(meta.name)}</b><br>${esc(error.message)}<br><br>Riprova selezionando nuovamente il personaggio.</div>`;
    return false;
  }
  if(requestId!==characterSwitchRequest)return false;
  currentCharacter=character; activeEra="Tutte";activeSeries="Tutte";optionalVisible=false;saveState();renderAll();
  if(updateHash)history.replaceState(null,"",`#/${meta.id}${issue?`/${issue}`:""}`);
  if(issue)requestAnimationFrame(()=>$( `issue-${currentCharacter.issues.find(i=>i.n===issue)?.seriesId}-${issue}` )?.scrollIntoView({behavior:"smooth",block:"center"}));
  return true;
}
function visibleIssues(){const q=els.search.value.trim().toLowerCase();return currentCharacter.issues.filter(i=>(optionalVisible||!i.skip)&&(activeSeries==="Tutte"||i.seriesId===activeSeries)&&(activeEra==="Tutte"||i.era===activeEra)&&(!q||[i.n,i.name,i.title,i.date,i.era,i.eraSub,i.series].join(" ").toLowerCase().includes(q)))}
function renderCharacters(){const home=document.body.classList.contains("homeActive");els.charGrid.innerHTML=manifest.characters.map(c=>`<button type="button" class="charBtn ${!home&&c.id===activeCharacter?"active":""}" data-char="${esc(c.id)}" aria-pressed="${!home&&c.id===activeCharacter}"><div class="charIcon"><span class="logoFallback">LOGO</span><img src="${esc(versioned(c.logo))}" alt="Logo ${esc(c.name)}" onerror="this.style.display='none'"></div><b>${esc(c.name)}</b><span>${esc(c.subtitle)}</span></button>`).join("");els.charGrid.querySelectorAll("[data-char]").forEach(b=>b.onclick=()=>void switchCharacter(b.dataset.char))}
function readCountFor(id){return Object.values(state.characters?.[id]?.issues||{}).filter(x=>x?.read).length}
function accountStorageKey(id){return `${STORAGE_KEY}:user:${id}`}
function refreshCurrentView(){if(!manifest)return;if(document.body.classList.contains("homeActive")||!currentCharacter)showHome({updateHash:false});else if(currentCharacter.id!==activeCharacter)void switchCharacter(activeCharacter);else renderAll()}
function renderAccountUi(){
  const signed=!!accountView.user,name=signed?accountView.displayName:"Profilo locale",initial=(name||"M").trim().charAt(0).toUpperCase()||"M";
  const statusText=signed?({synced:"Sincronizzato",syncing:"Sincronizzazione…",offline:"Offline · copia locale",error:"Sync da riprovare",ready:"Cloud collegato"}[accountView.syncStatus]||"Cloud collegato"):(accountView.configured?"Accedi per sincronizzare":"Cloud da collegare");
  document.querySelectorAll("[data-account-avatar]").forEach(x=>x.textContent=initial);
  document.querySelectorAll("[data-account-name]").forEach(x=>x.textContent=name);
  document.querySelectorAll("[data-account-status]").forEach(x=>x.textContent=statusText);
  if(els.homeGreetingName)els.homeGreetingName.textContent=signed?`${accountView.displayName}.`:"lettore.";
  els.accountLoading.hidden=accountView.phase!=="loading";
  els.accountSetup.hidden=accountView.configured||accountView.phase==="loading";
  els.accountAuth.hidden=!accountView.configured||signed||accountView.phase==="loading";
  els.accountSigned.hidden=!signed;
  if(signed){
    const copy={synced:["Sincronizzato","Progressi salvati nel cloud","cloud"],syncing:["Sincronizzazione…","Stiamo salvando le ultime modifiche","sync"],offline:["Modalità offline","Le modifiche saranno inviate alla riconnessione","offline"],error:["Sincronizzazione sospesa","Premi “Sincronizza ora” per riprovare","offline"],ready:["Cloud collegato","I progressi sono pronti per la sincronizzazione","cloud"]}[accountView.syncStatus]||["Cloud collegato","Progressi protetti dal tuo profilo","cloud"];
    els.accountProfileName.textContent=accountView.displayName;
    els.accountEmail.textContent=accountView.user.email||"";
    els.accountSyncTitle.textContent=copy[0];els.accountSyncDetail.textContent=copy[1];els.accountSyncIcon.innerHTML=icon(copy[2]);
  }
  const busy=accountView.phase==="authenticating";
  els.authSubmit.disabled=busy;
  if(busy)els.authSubmit.textContent="Accesso in corso…";else els.authSubmit.textContent=authMode==="register"?"Crea account":"Accedi e sincronizza";
  if(accountView.phase==="error"&&accountView.error&&!els.authMessage.textContent)els.authMessage.textContent=`Connessione al profilo non riuscita: ${accountView.error}`;
}
async function handleAccountChange(next){
  accountView=next;renderAccountUi();
  const nextId=next.user?.id||null;
  if(nextId&&(nextId!==activatedAccountId||next.reconnected)){
    const request=++accountActivationRequest,guestState=state,cachedRaw=localStorage.getItem(accountStorageKey(nextId));
    activatedAccountId=nextId;activeStorageKey=accountStorageKey(nextId);
    let remote=null,remoteLoaded=false;
    try{remote=await fetchCloudState();remoteLoaded=true}catch(error){console.error("Stato cloud non disponibile",error)}
    if(request!==accountActivationRequest)return;
    if(remote?.state&&!hasUnsyncedState())state=normalizeState(remote.state);
    else if(cachedRaw)state=loadState(activeStorageKey);
    else state=normalizeState(guestState);
    activeCharacter=manifest?.characters.some(c=>c.id===state.activeCharacter)?state.activeCharacter:(manifest?.defaultCharacter||activeCharacter);
    saveState({sync:false});
    if(remoteLoaded&&(!remote||hasUnsyncedState()))await flushCloudState(state).catch(error=>console.error("Prima sincronizzazione non riuscita",error));
    refreshCurrentView();
  }else if(!nextId&&activatedAccountId){
    accountActivationRequest++;activatedAccountId=null;activeStorageKey=STORAGE_KEY;state=loadState();
    activeCharacter=manifest?.characters.some(c=>c.id===state.activeCharacter)?state.activeCharacter:(manifest?.defaultCharacter||activeCharacter);
    refreshCurrentView();
  }
}
async function renderHomeContinue(meta){
  const request=++homeContinueRequest;
  els.homeContinue.innerHTML='<div class="homeContinueLoading"><span></span><div><b>Prepariamo il prossimo albo…</b><small>Caricamento del percorso</small></div></div>';
  try{
    const character=await loadCharacter(meta.id);if(request!==homeContinueRequest||els.homeView.hidden)return;
    const progress=state.characters?.[meta.id]?.issues||{},required=character.issues.filter(i=>i.required!==false&&!i.future),next=required.find(i=>!progress[i.id]?.read);
    if(!next){els.homeContinue.innerHTML=`<div class="homeContinueComplete"><img src="${esc(versioned(meta.logo))}" alt=""><span>${icon("check")}</span><div><div class="homeEyebrow">Percorso completato</div><h2>Sei in pari con ${esc(meta.name)}</h2><p>${esc(character.end)}</p></div><button type="button" data-continue-char="${esc(meta.id)}">Rivedi il percorso ${icon("arrow")}</button></div>`}
    else els.homeContinue.innerHTML=`<div class="homeContinueHead"><span>Continua a leggere</span><span class="homeContinueCloud">${icon(accountView.user?"cloud":"book")}${accountView.user?"Sincronizzato":"Salvato in locale"}</span></div><div class="homeContinueBody"><div class="homeContinueCover"><div class="fallback">${esc(next.name)}</div>${coverImg(next,false,meta.accent)}</div><div class="homeContinueMeta"><div class="homeContinueHero"><img src="${esc(versioned(meta.logo))}" alt=""><span><b>${esc(meta.name)}</b><small>Albo ${next.seq} di ${required.length}</small></span></div><h2>${esc(next.name)}</h2><p>${esc(next.title)}<br><span>${esc(next.date)} · ${esc(next.era)}</span></p><button type="button" data-continue-char="${esc(meta.id)}">Apri il percorso ${icon("arrow")}</button></div></div>`;
    els.homeContinue.querySelector("[data-continue-char]").onclick=()=>void switchCharacter(meta.id);
  }catch(error){
    if(request!==homeContinueRequest)return;
    els.homeContinue.innerHTML=`<div class="homeContinueError"><span>${icon("offline")}</span><div><b>Anteprima non disponibile</b><small>${esc(error.message)}</small></div><button type="button" data-continue-char="${esc(meta.id)}">Apri comunque</button></div>`;
    els.homeContinue.querySelector("[data-continue-char]").onclick=()=>void switchCharacter(meta.id);
  }
}
function renderHome(){
  const resume=manifest.characters.find(c=>c.id===(state.activeCharacter||activeCharacter))||manifest.characters.find(c=>c.id===manifest.defaultCharacter)||manifest.characters[0];
  const totalMapped=manifest.characters.reduce((sum,c)=>sum+(c.totalRequired||0),0);
  const readTotal=manifest.characters.reduce((sum,c)=>sum+readCountFor(c.id),0);
  const ownedTotal=Object.values(state.collection||{}).filter(x=>x?.owned).length;
  const completed=manifest.characters.filter(c=>readCountFor(c.id)>=(c.totalRequired||0)).length;
  const globalPct=Math.min(100,Math.round(readTotal/(totalMapped||1)*100));
  const fmt=n=>new Intl.NumberFormat("it-IT").format(n);
  els.homeGreetingName.textContent=accountView.user?`${accountView.displayName}.`:"lettore.";
  els.homeHeroIcons.innerHTML=manifest.characters.map(c=>`<button type="button" class="homeHeroIcon" style="--hero-accent:${esc(c.accent)}" title="Apri ${esc(c.name)}" data-hero-shortcut="${esc(c.id)}"><img src="${esc(versioned(c.logo))}" alt="${esc(c.name)}" onerror="this.parentElement.style.display='none'"></button>`).join("");
  els.homeHeroIcons.querySelectorAll("[data-hero-shortcut]").forEach(b=>b.onclick=()=>void switchCharacter(b.dataset.heroShortcut));
  els.homeStats.innerHTML=`<article class="homeStat" style="--stat-color:#ed1d24"><div class="homeStatLabel">${icon("paths")}<span>Percorsi</span></div><b>${manifest.characters.length}</b><small>${completed} completati</small></article><article class="homeStat" style="--stat-color:#64b9ff"><div class="homeStatLabel">${icon("book")}<span>Albi mappati</span></div><b>${fmt(totalMapped)}</b><small>Edizioni italiane in ordine di lettura</small></article><article class="homeStat" style="--stat-color:#ffb000"><div class="homeStatLabel">${icon("archive")}<span>Recuperati</span></div><b>${fmt(ownedTotal)}</b><small>Nella collezione globale</small></article><article class="homeStat" style="--stat-color:#4fe0a0"><div class="homeStatLabel">${icon("chart")}<span>Avanzamento</span></div><b>${globalPct}%</b><small>${fmt(readTotal)} albi letti in tutti i percorsi</small></article>`;
  els.homeCharacterGrid.innerHTML=manifest.characters.map(c=>{const read=readCountFor(c.id),total=c.totalRequired||0,pct=Math.min(100,Math.round(read/(total||1)*100));return `<button type="button" class="homeCharCard" style="--hero-accent:${esc(c.accent)}" data-home-char="${esc(c.id)}" aria-label="Apri il percorso di ${esc(c.name)}, ${read} albi letti su ${total}"><span class="homeCharTop"><img class="homeCharLogo" src="${esc(versioned(c.logo))}" alt="Logo ${esc(c.name)}" onerror="this.style.visibility='hidden'"><span class="homeCharPercent">${pct}%</span></span><span class="homeCharMeta"><b>${esc(c.name)}</b><span>${esc(c.subtitle)}</span><small>${esc(c.start.split(" — ")[0])}</small></span><span class="homeCharProgress"><span class="homeCharProgressTop"><span>Albi letti</span><b>${read}/${total}</b></span><span class="homeCharTrack"><span style="width:${pct}%"></span></span><span class="homeCharOpen">Apri percorso ${icon("arrow")}</span></span></button>`}).join("");
  els.homeCharacterGrid.querySelectorAll("[data-home-char]").forEach(b=>b.onclick=()=>void switchCharacter(b.dataset.homeChar));
  els.homeResume.innerHTML=`Riprendi ${esc(resume.name)} ${icon("arrow")}`;
  els.homeTopResume.innerHTML=`Riprendi ${icon("arrow")}`;
  els.homeResume.onclick=els.homeTopResume.onclick=()=>void switchCharacter(resume.id);
  els.homeExplore.onclick=()=>els.homeCharactersSection.scrollIntoView({behavior:"smooth",block:"start"});
  void renderHomeContinue(resume);
}
function showHome({updateHash=true}={}){
  characterSwitchRequest++;
  document.body.classList.add("homeActive");
  document.documentElement.style.setProperty("--accent","#ed1d24");
  els.homeView.hidden=false;
  els.trackerView.hidden=true;
  els.logoSub.textContent="Il tuo archivio personale";
  renderCharacters();
  renderHome();
  if(updateHash)history.replaceState(null,"","#/home");
}
function setAuthMode(mode){
  authMode=mode;const register=mode==="register";
  els.loginTab.classList.toggle("active",!register);els.loginTab.setAttribute("aria-selected",String(!register));
  els.registerTab.classList.toggle("active",register);els.registerTab.setAttribute("aria-selected",String(register));
  els.displayNameField.hidden=!register;els.authDisplayName.required=register;
  els.authPassword.autocomplete=register?"new-password":"current-password";
  els.authMessage.textContent="";renderAccountUi();
}
function openAccountDialog(){
  renderAccountUi();
  if(typeof els.accountDialog.showModal==="function")els.accountDialog.showModal();else els.accountDialog.setAttribute("open","");
}
function friendlyAuthError(error){const message=String(error?.message||error||"Operazione non riuscita.");if(/invalid login credentials/i.test(message))return"Email o password non corretti.";if(/already registered/i.test(message))return"Esiste già un account con questa email.";if(/password/i.test(message)&&/least/i.test(message))return"La password deve contenere almeno 8 caratteri.";return message}
function renderStats(){const req=requiredIssues(),r=req.filter(i=>status(i.id).read).length,o=req.filter(i=>status(i.id).owned).length,p=Math.round(r/(req.length||1)*100);els.doneCount.textContent=r;els.totalCount.textContent=req.length;els.ownedCount.textContent=o;els.pct.textContent=p+"%";els.progressBar.style.width=p+"%"}
function renderHero(){document.documentElement.style.setProperty("--accent",currentCharacter.accent||currentMeta.accent);els.logoSub.textContent=currentCharacter.subtitle||currentMeta.subtitle;els.heroLabel.textContent="Percorso attivo";els.heroTitle.innerHTML=`${esc(currentCharacter.name)}<br><span>${esc(currentCharacter.start)}</span>`;els.heroDesc.textContent=currentCharacter.description;els.topTitle.textContent=`${currentCharacter.name} Reading System`;els.topSub.textContent=`${currentCharacter.start} → ${currentCharacter.end}`;els.footerNote.innerHTML=`<b>${esc(currentCharacter.name)}</b><br>${esc(currentCharacter.start)}<br>→ ${esc(currentCharacter.end)}`}
function renderNext(){const i=nextIssue();if(!i){els.nextPanel.innerHTML=`<div class="nextMeta" style="grid-column:1/-1"><div class="label">Percorso completato</div><h2>Sei in pari con ${esc(currentCharacter.name)}.</h2><p>${esc(currentCharacter.end)}</p></div>`;return}const st=status(i.id);els.nextPanel.innerHTML=`<div class="nextCover"><div class="fallback">${esc(i.name)}</div>${coverImg(i,false)}</div><div class="nextMeta"><div class="label">Leggi adesso · ${i.seq}/${currentCharacter.totalRequired}</div><h2>${esc(i.name)}</h2><p>${esc(i.date)} · ${esc(i.era)}<br>${esc(i.title)}</p><div class="nextBtns"><button type="button" class="btn ${st.owned?"primary":""}" id="nextOwned">${icon(st.owned?"check":"archive")}<span>${st.owned?"Recuperato":"Segna recuperato"}</span></button><button type="button" class="btn done" id="nextRead">${icon("book")}<span>Segna letto</span></button><button type="button" class="btn" id="nextJump"><span>Mostra</span>${icon("arrow")}</button></div></div>`;$("nextOwned").onclick=()=>setStatus(i.id,{owned:!st.owned});$("nextRead").onclick=()=>setStatus(i.id,{read:true,owned:true});$("nextJump").onclick=()=>jumpToIssue(i)}
function renderRoute(){let h=(currentCharacter.series||[]).map((s,k)=>`<div class="routeCard"><b>${k+1} · ${esc(s.name)} ${esc(s.range)}</b><span>${esc(s.publisher)} · ${esc(s.years)}</span></div>`).join("");for(const a of currentCharacter.archives||[])h+=`<div class="routeCard archive"><b>${esc(a.name)} ${esc(a.range)}</b><span>${esc(a.publisher)} · ${esc(a.years)}<br>${esc(a.status)}${a.url?` · <a href="${esc(a.url)}" target="_blank" rel="noopener">Apri ↗</a>`:""}</span></div>`;els.route.innerHTML=h;renderNotices()}
function renderNotices(){const id=activeCharacter,ns=[];if(id==="spiderman")ns.push(["🕷️ Editoriale Corno esclusa","Il percorso parte da L'Uomo Ragno #1 — Star Comics, maggio 1987. Le cover puntano direttamente alle schede italiane ComicsBox."],["Numerazione fino al #899","Gli albi futuri annunciati restano visibili ma non vengono conteggiati nel progresso leggibile."]);if(id==="hulk")ns.push(["💥 Devil & Hulk","Hulk e Daredevil condividono la stessa testata italiana. Recuperato è globale per albo fisico; Letto resta separato per personaggio."]);if(id==="thor")ns.push(["⚡ Salto intenzionale #78–109","Nel percorso personale di Thor questi numeri sono facoltativi; la testata ospita soprattutto Nuovi Vendicatori/Capitan America."]);if(id==="cap")ns.push(["🛡️ Ingresso moderno","Il percorso parte dal blocco antologico italiano legato alla gestione moderna e poi passa alla testata Capitan America."]);els.noticeWrap.innerHTML=ns.map(([b,p])=>`<div class="notice"><b>${b}</b><p>${p}</p></div>`).join("")}
function renderSeriesNav(){els.seriesNav.innerHTML=(currentCharacter.series||[]).map(s=>{const xs=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=xs.filter(i=>status(i.id).read).length;return `<button data-jump="${esc(s.id)}"><b>${esc(s.name)}</b><span>${r}/${xs.length} letti · ${esc(s.years)}</span></button>`}).join("");els.seriesNav.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>$("series-"+b.dataset.jump)?.scrollIntoView({behavior:"smooth",block:"start"}))}
function renderFilters(){const source=visibleIssues(),eras=["Tutte",...new Set(source.map(i=>i.era))];els.filterBar.innerHTML=`<button class="chip ${activeSeries==="Tutte"?"active":""}" data-series="Tutte">Tutte le testate</button>`+(currentCharacter.series||[]).map(s=>`<button class="chip ${activeSeries===s.id?"active":""}" data-series="${esc(s.id)}">${esc(s.name)}</button>`).join("")+`<span style="width:1px;height:22px;background:var(--line)"></span>`+eras.map(e=>`<button class="chip ${activeEra===e?"active":""}" data-era="${esc(e)}">${esc(e)}</button>`).join("");els.filterBar.querySelectorAll("[data-series]").forEach(b=>b.onclick=()=>{activeSeries=b.dataset.series;activeEra="Tutte";renderAll()});els.filterBar.querySelectorAll("[data-era]").forEach(b=>b.onclick=()=>{activeEra=b.dataset.era;renderAll()})}
function issueHtml(i){const st=status(i.id);return `<article class="issue ${st.read?"read":""} ${i.skip?"optional":""} ${i.future?"future":""}" id="issue-${esc(i.seriesId)}-${i.n}"><div class="num">#<b>${esc(i.displayNumber??String(i.n).padStart(2,"0"))}</b></div><div class="cover"><div class="fallback">${esc(i.name)}</div>${coverImg(i)}</div><div class="meta"><h4>${esc(i.name)} ${i.url?`<a href="${esc(i.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}${i.sharedWith?.length?`<span class="sharedBadge">condiviso con ${esc(i.sharedWith.join(", "))}</span>`:""}${i.future?'<span class="futureBadge">ANNUNCIATO</span>':""}</h4><div class="title">${esc(i.title)}</div><div class="instruction">${esc(i.instruction)}</div></div><div class="date">${esc(i.date)}${i.dateQuality==="ricostruita"?' <span title="Data ricostruita" style="color:#718196;font-size:7px">≈</span>':""}<br><span style="color:var(--cyan);font-size:8px">${esc(i.era)}</span><span class="seq">${i.required!==false?(i.future?"ANNUNCIATO":"percorso #"+i.seq):"FACOLTATIVO / SALTA"}</span></div><div class="status"><button type="button" class="${st.owned?"on owned":""}" data-owned="${esc(i.id)}">${icon(st.owned?"check":"archive")}<span>Recuperato</span></button><button type="button" class="${st.read?"on read":""}" data-read="${esc(i.id)}">${icon(st.read?"check":"book")}<span>Letto</span></button></div></article>`}
function eraHtml(g){const req=g.items.filter(i=>i.required!==false&&!i.future);return `<section class="era"><div class="eraHead"><div><h3>${esc(g.era)}</h3><p>${esc(g.sub)}</p></div><div class="count">${req.filter(i=>status(i.id).read).length}/${req.length} richiesti letti</div></div><div class="issueList">${g.items.map(issueHtml).join("")}</div></section>`}
function renderBlocks(){const vis=visibleIssues(),order=(currentCharacter.series||[]).filter(s=>activeSeries==="Tutte"||s.id===activeSeries);els.seriesBlocks.innerHTML=order.map(s=>{const xs=vis.filter(i=>i.seriesId===s.id);if(!xs.length)return"";const all=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=all.filter(i=>status(i.id).read).length,eras=[];for(const i of xs){let g=eras.find(x=>x.era===i.era);if(!g){g={era:i.era,sub:i.eraSub,items:[]};eras.push(g)}g.items.push(i)}return `<section class="seriesBlock" id="series-${esc(s.id)}"><div class="seriesHead"><div><div class="label">${esc(s.publisher)} · ${esc(s.years)}</div><h2>${esc(s.name)} ${esc(s.range)}</h2><p>${all.length} albi richiesti nel percorso</p></div><div class="seriesPct">${r}/${all.length} letti<br>${Math.round(r/(all.length||1)*100)}%</div></div>${eras.map(eraHtml).join("")}</section>`}).join("")||'<div class="loading">Nessun albo trovato.</div>';bindIssueActions()}
function bindIssueActions(){document.querySelectorAll("[data-owned]").forEach(b=>b.onclick=()=>setStatus(b.dataset.owned,{owned:!status(b.dataset.owned).owned}));document.querySelectorAll("[data-read]").forEach(b=>b.onclick=()=>{const s=status(b.dataset.read),v=!s.read;setStatus(b.dataset.read,{read:v,owned:v?true:s.owned})})}
function jumpToIssue(i){history.replaceState(null,"",`#/${activeCharacter}/${i.n}`);$( `issue-${i.seriesId}-${i.n}` )?.scrollIntoView({behavior:"smooth",block:"center"})}
function renderAll(){if(!currentCharacter)return;renderCharacters();renderHero();renderStats();renderNext();renderRoute();renderSeriesNav();renderFilters();renderBlocks();els.showOptional.style.display=currentCharacter.issues.some(i=>i.skip)?"block":"none";els.showOptional.textContent=optionalVisible?"− Nascondi numeri facoltativi":"+ Mostra numeri facoltativi"}

els.search.addEventListener("input",()=>renderAll());
els.homeBtn.onclick=()=>{if(manifest)showHome()};
els.trackerHomeIcon.innerHTML=icon("home");
els.trackerHomeBtn.onclick=()=>{if(manifest)showHome()};
els.homeAccountBtn.onclick=els.trackerAccountBtn.onclick=openAccountDialog;
els.loginTab.onclick=()=>setAuthMode("login");
els.registerTab.onclick=()=>setAuthMode("register");
els.accountDialog.addEventListener("click",event=>{if(event.target===els.accountDialog)els.accountDialog.close()});
els.authForm.onsubmit=async event=>{
  event.preventDefault();els.authMessage.textContent="";
  try{
    if(authMode==="register"){
      const result=await signUp(els.authEmail.value.trim(),els.authPassword.value,els.authDisplayName.value.trim());
      if(result.confirmationRequired)els.authMessage.textContent="Account creato. Controlla l'email per confermare l'accesso.";
    }else await signIn(els.authEmail.value.trim(),els.authPassword.value);
  }catch(error){els.authMessage.textContent=friendlyAuthError(error)}
};
els.syncNowBtn.onclick=async()=>{try{await flushCloudState(state)}catch(error){console.error(error)}};
els.signOutBtn.onclick=async()=>{try{await signOut();els.accountDialog.close()}catch(error){els.accountSyncDetail.textContent=friendlyAuthError(error)}};
els.jumpNext.onclick=()=>{const i=nextIssue();if(i)jumpToIssue(i)};
els.showOptional.onclick=()=>{optionalVisible=!optionalVisible;renderAll()};
els.compactBtn.onclick=()=>{document.body.classList.toggle("compact");els.compactBtn.textContent=document.body.classList.contains("compact")?"Vista completa":"Vista compatta"};
els.resetBtn.onclick=()=>{if(confirm(`Azzerare solo lo stato LETTO di ${currentCharacter.name}? Gli albi recuperati resteranno nella collezione globale.`)){state.characters[activeCharacter]={issues:{}};saveState();renderAll()}};
els.exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="marvel_archive_progressi.json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),600)};
els.importFile.onchange=e=>{const f=e.target.files?.[0];if(!f)return;const r=new FileReader();r.onload=()=>{try{state=normalizeState(JSON.parse(r.result));saveState();document.body.classList.contains("homeActive")?renderHome():renderAll()}catch{alert("Backup non valido.")}};r.readAsText(f);e.target.value=""};
window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.view==="home"){showHome({updateHash:false});return}if(els.trackerView.hidden||!currentCharacter||h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=currentCharacter.issues.find(x=>x.n===h.issue);if(i)jumpToIssue(i)}});

(async()=>{try{await loadManifest();const h=parseHash();if(h.view==="home"){showHome({updateHash:false});if(!location.hash)history.replaceState(null,"","#/home")}else await switchCharacter(h.character,{updateHash:false,issue:h.issue});renderAccountUi();void initAccount(handleAccountChange)}catch(e){console.error(e);els.seriesBlocks.innerHTML=`<div class="loading error"><b>Errore di caricamento</b><br>${esc(e.message)}<br><br>Apri il sito tramite GitHub Pages o un server HTTP: i JSON non possono essere caricati correttamente con alcuni browser da file://.</div>`}})();
