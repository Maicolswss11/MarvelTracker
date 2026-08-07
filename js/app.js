const STORAGE_KEY = "marvel_archive_characters_v12";
const characterCache = new Map();
let manifest = null;
let currentMeta = null;
let currentCharacter = null;
let activeCharacter = "ironman";
let activeEra = "Tutte";
let activeSeries = "Tutte";
let optionalVisible = false;
let state = loadState();

const $ = (id) => document.getElementById(id);
const els = {
  charGrid: $("charGrid"), doneCount: $("doneCount"), totalCount: $("totalCount"), progressBar: $("progressBar"), ownedCount: $("ownedCount"), pct: $("pct"),
  seriesNav: $("seriesNav"), jumpNext: $("jumpNext"), showOptional: $("showOptional"), exportBtn: $("exportBtn"), importFile: $("importFile"), resetBtn: $("resetBtn"),
  footerNote: $("footerNote"), logoSub: $("logoSub"), topTitle: $("topTitle"), topSub: $("topSub"), search: $("search"), compactBtn: $("compactBtn"), heroLabel: $("heroLabel"), heroTitle: $("heroTitle"), heroDesc: $("heroDesc"), nextPanel: $("nextPanel"), route: $("route"), noticeWrap: $("noticeWrap"), filterBar: $("filterBar"), seriesBlocks: $("seriesBlocks")
};

function esc(x){return String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function normalizeState(x){
  x ??= {}; x.characters ??= {}; x.collection ??= {};
  if(manifest){ for(const c of manifest.characters){ x.characters[c.id] ??= {issues:{}}; x.characters[c.id].issues ??= {}; } }
  for(const c of Object.values(x.characters||{})){ for(const [id,v] of Object.entries(c.issues||{})){ if(v?.owned) x.collection[id]={...(x.collection[id]||{}),owned:true}; } }
  return x;
}
function loadState(){try{return normalizeState(JSON.parse(localStorage.getItem(STORAGE_KEY)))}catch{return normalizeState({characters:{},collection:{}})}}
function saveState(){state.activeCharacter=activeCharacter;localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}
function bucket(){state.characters[activeCharacter]??={issues:{}};state.characters[activeCharacter].issues??={};return state.characters[activeCharacter].issues}
function status(id){return {owned:!!state.collection?.[id]?.owned,read:!!bucket()[id]?.read}}
function setStatus(id,patch){state.collection??={};if(Object.hasOwn(patch,"owned"))state.collection[id]={...(state.collection[id]||{}),owned:!!patch.owned};if(Object.hasOwn(patch,"read"))bucket()[id]={...(bucket()[id]||{}),read:!!patch.read};saveState();renderAll()}
function requiredIssues(){return currentCharacter.issues.filter(i=>i.required!==false&&!i.future)}
function nextIssue(){return requiredIssues().find(i=>!status(i.id).read)||null}
function pad3(n){return String(n).padStart(3,"0")}
function coverPlaceholder(i){
  const accent=currentCharacter.accent||currentMeta.accent||"#43d7ff",safe=s=>String(s??"").replace(/[<>&]/g,m=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[m]));
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 600"><rect width="420" height="600" fill="#0b1118"/><rect x="18" y="18" width="384" height="564" rx="22" fill="none" stroke="${accent}" stroke-width="4" opacity=".6"/><text x="34" y="76" font-family="Arial" font-size="24" font-weight="700" fill="${accent}">${safe(i.series)}</text><text x="34" y="138" font-family="Arial" font-size="48" font-weight="900" fill="#fff">#${pad3(i.n)}</text><foreignObject x="34" y="175" width="352" height="270"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial;color:#d8e2eb;font-size:27px;font-weight:800;line-height:1.18">${safe(i.title)}</div></foreignObject><text x="34" y="548" font-family="Arial" font-size="17" fill="#8292a3">Copertina remota non disponibile</text></svg>`;
  return "data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);
}
window.coverFail = (img)=>{if(img.dataset.failed==="1"){img.style.display="none";return}img.dataset.failed="1";img.src=img.dataset.placeholder};
function coverImg(i,lazy=true){return `<img ${lazy?'loading="lazy" ':''}src="${esc(i.cover||coverPlaceholder(i))}" data-placeholder="${coverPlaceholder(i)}" alt="${esc(i.name)}" referrerpolicy="no-referrer" onerror="coverFail(this)">`}

async function loadManifest(){
  const r=await fetch("data/characters.json",{cache:"no-cache"}); if(!r.ok)throw new Error(`Manifest HTTP ${r.status}`); manifest=await r.json(); state=normalizeState(state);
}
async function loadCharacter(id){
  if(characterCache.has(id))return characterCache.get(id);
  const meta=manifest.characters.find(c=>c.id===id); if(!meta)throw new Error(`Personaggio sconosciuto: ${id}`);
  const r=await fetch(meta.data); if(!r.ok)throw new Error(`${meta.name}: HTTP ${r.status}`); const c=await r.json();
  if(Array.isArray(c.issueSources)){
    const parts=await Promise.all(c.issueSources.map(async src=>{const rr=await fetch(src);if(!rr.ok)throw new Error(`${meta.name}: ${src} HTTP ${rr.status}`);return rr.json()}));
    c.issues=parts.flatMap(p=>p.issues||[]).sort((a,b)=>(a.seq??Number.MAX_SAFE_INTEGER)-(b.seq??Number.MAX_SAFE_INTEGER)||a.n-b.n);
  }
  c.issues??=[]; characterCache.set(id,c); return c;
}
function parseHash(){const p=location.hash.replace(/^#\/?/,"").split("/").filter(Boolean);return {character:p[0]||state.activeCharacter||manifest.defaultCharacter,issue:p[1]?Number(p[1]):null}}
async function switchCharacter(id,{updateHash=true,issue=null}={}){
  const meta=manifest.characters.find(c=>c.id===id)||manifest.characters[0]; activeCharacter=meta.id; currentMeta=meta;
  els.seriesBlocks.innerHTML='<div class="loading">Caricamento dati…</div>';
  currentCharacter=await loadCharacter(meta.id); activeEra="Tutte";activeSeries="Tutte";optionalVisible=false;saveState();renderAll();
  if(updateHash)history.replaceState(null,"",`#/${meta.id}${issue?`/${issue}`:""}`);
  if(issue)requestAnimationFrame(()=>$( `issue-${currentCharacter.issues.find(i=>i.n===issue)?.seriesId}-${issue}` )?.scrollIntoView({behavior:"smooth",block:"center"}));
}
function visibleIssues(){const q=els.search.value.trim().toLowerCase();return currentCharacter.issues.filter(i=>(optionalVisible||!i.skip)&&(activeSeries==="Tutte"||i.seriesId===activeSeries)&&(activeEra==="Tutte"||i.era===activeEra)&&(!q||[i.n,i.name,i.title,i.date,i.era,i.eraSub,i.series].join(" ").toLowerCase().includes(q)))}
function renderCharacters(){els.charGrid.innerHTML=manifest.characters.map(c=>`<button class="charBtn ${c.id===activeCharacter?"active":""}" data-char="${esc(c.id)}"><div class="charIcon"><span class="logoFallback">LOGO</span><img src="${esc(c.logo)}" alt="Logo ${esc(c.name)}" onerror="this.style.display='none'"></div><b>${esc(c.name)}</b><span>${esc(c.subtitle)}</span></button>`).join("");els.charGrid.querySelectorAll("[data-char]").forEach(b=>b.onclick=()=>switchCharacter(b.dataset.char))}
function renderStats(){const req=requiredIssues(),r=req.filter(i=>status(i.id).read).length,o=req.filter(i=>status(i.id).owned).length,p=Math.round(r/(req.length||1)*100);els.doneCount.textContent=r;els.totalCount.textContent=req.length;els.ownedCount.textContent=o;els.pct.textContent=p+"%";els.progressBar.style.width=p+"%"}
function renderHero(){document.documentElement.style.setProperty("--accent",currentCharacter.accent||currentMeta.accent);els.logoSub.textContent=currentCharacter.subtitle||currentMeta.subtitle;els.heroLabel.textContent="Percorso attivo";els.heroTitle.innerHTML=`${esc(currentCharacter.name)}<br><span>${esc(currentCharacter.start)}</span>`;els.heroDesc.textContent=currentCharacter.description;els.topTitle.textContent=`${currentCharacter.name} Reading System`;els.topSub.textContent=`${currentCharacter.start} → ${currentCharacter.end}`;els.footerNote.innerHTML=`<b>${esc(currentCharacter.name)}</b><br>${esc(currentCharacter.start)}<br>→ ${esc(currentCharacter.end)}`}
function renderNext(){const i=nextIssue();if(!i){els.nextPanel.innerHTML=`<div class="nextMeta" style="grid-column:1/-1"><div class="label">Percorso completato</div><h2>Sei in pari con ${esc(currentCharacter.name)}.</h2><p>${esc(currentCharacter.end)}</p></div>`;return}const st=status(i.id);els.nextPanel.innerHTML=`<div class="nextCover"><div class="fallback">${esc(i.name)}</div>${coverImg(i,false)}</div><div class="nextMeta"><div class="label">Leggi adesso · ${i.seq}/${currentCharacter.totalRequired}</div><h2>${esc(i.name)}</h2><p>${esc(i.date)} · ${esc(i.era)}<br>${esc(i.title)}</p><div class="nextBtns"><button class="btn ${st.owned?"primary":""}" id="nextOwned">${st.owned?"✓ Recuperato":"Segna recuperato"}</button><button class="btn done" id="nextRead">Segna letto</button><button class="btn" id="nextJump">Mostra</button></div></div>`;$("nextOwned").onclick=()=>setStatus(i.id,{owned:!st.owned});$("nextRead").onclick=()=>setStatus(i.id,{read:true,owned:true});$("nextJump").onclick=()=>jumpToIssue(i)}
function renderRoute(){let h=(currentCharacter.series||[]).map((s,k)=>`<div class="routeCard"><b>${k+1} · ${esc(s.name)} ${esc(s.range)}</b><span>${esc(s.publisher)} · ${esc(s.years)}</span></div>`).join("");for(const a of currentCharacter.archives||[])h+=`<div class="routeCard archive"><b>${esc(a.name)} ${esc(a.range)}</b><span>${esc(a.publisher)} · ${esc(a.years)}<br>${esc(a.status)}${a.url?` · <a href="${esc(a.url)}" target="_blank" rel="noopener">Apri ↗</a>`:""}</span></div>`;els.route.innerHTML=h;renderNotices()}
function renderNotices(){const id=activeCharacter,ns=[];if(id==="spiderman")ns.push(["🕷️ Editoriale Corno esclusa","Il percorso parte da L'Uomo Ragno #1 — Star Comics, maggio 1987. Le cover puntano direttamente alle schede italiane ComicsBox."],["Numerazione fino al #899","Gli albi futuri annunciati restano visibili ma non vengono conteggiati nel progresso leggibile."]);if(id==="hulk")ns.push(["💥 Devil & Hulk","Hulk e Daredevil condividono la stessa testata italiana. Recuperato è globale per albo fisico; Letto resta separato per personaggio."]);if(id==="thor")ns.push(["⚡ Salto intenzionale #78–109","Nel percorso personale di Thor questi numeri sono facoltativi; la testata ospita soprattutto Nuovi Vendicatori/Capitan America."]);if(id==="cap")ns.push(["🛡️ Ingresso moderno","Il percorso parte dal blocco antologico italiano legato alla gestione moderna e poi passa alla testata Capitan America."]);els.noticeWrap.innerHTML=ns.map(([b,p])=>`<div class="notice"><b>${b}</b><p>${p}</p></div>`).join("")}
function renderSeriesNav(){els.seriesNav.innerHTML=(currentCharacter.series||[]).map(s=>{const xs=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=xs.filter(i=>status(i.id).read).length;return `<button data-jump="${esc(s.id)}"><b>${esc(s.name)}</b><span>${r}/${xs.length} letti · ${esc(s.years)}</span></button>`}).join("");els.seriesNav.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>$("series-"+b.dataset.jump)?.scrollIntoView({behavior:"smooth",block:"start"}))}
function renderFilters(){const source=visibleIssues(),eras=["Tutte",...new Set(source.map(i=>i.era))];els.filterBar.innerHTML=`<button class="chip ${activeSeries==="Tutte"?"active":""}" data-series="Tutte">Tutte le testate</button>`+(currentCharacter.series||[]).map(s=>`<button class="chip ${activeSeries===s.id?"active":""}" data-series="${esc(s.id)}">${esc(s.name)}</button>`).join("")+`<span style="width:1px;height:22px;background:var(--line)"></span>`+eras.map(e=>`<button class="chip ${activeEra===e?"active":""}" data-era="${esc(e)}">${esc(e)}</button>`).join("");els.filterBar.querySelectorAll("[data-series]").forEach(b=>b.onclick=()=>{activeSeries=b.dataset.series;activeEra="Tutte";renderAll()});els.filterBar.querySelectorAll("[data-era]").forEach(b=>b.onclick=()=>{activeEra=b.dataset.era;renderAll()})}
function issueHtml(i){const st=status(i.id);return `<article class="issue ${st.read?"read":""} ${i.skip?"optional":""} ${i.future?"future":""}" id="issue-${esc(i.seriesId)}-${i.n}"><div class="num">#<b>${String(i.n).padStart(2,"0")}</b></div><div class="cover"><div class="fallback">${esc(i.name)}</div>${coverImg(i)}</div><div class="meta"><h4>${esc(i.name)} ${i.url?`<a href="${esc(i.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}${i.sharedWith?.length?`<span class="sharedBadge">condiviso con ${esc(i.sharedWith.join(", "))}</span>`:""}${i.future?'<span class="futureBadge">ANNUNCIATO</span>':""}</h4><div class="title">${esc(i.title)}</div><div class="instruction">${esc(i.instruction)}</div></div><div class="date">${esc(i.date)}${i.dateQuality==="ricostruita"?' <span title="Data ricostruita" style="color:#718196;font-size:7px">≈</span>':""}<br><span style="color:var(--cyan);font-size:8px">${esc(i.era)}</span><span class="seq">${i.required!==false?(i.future?"ANNUNCIATO":"percorso #"+i.seq):"FACOLTATIVO / SALTA"}</span></div><div class="status"><button class="${st.owned?"on owned":""}" data-owned="${esc(i.id)}">${st.owned?"✓ Recuperato":"□ Recuperato"}</button><button class="${st.read?"on read":""}" data-read="${esc(i.id)}">${st.read?"✓ Letto":"□ Letto"}</button></div></article>`}
function eraHtml(g){const req=g.items.filter(i=>i.required!==false&&!i.future);return `<section class="era"><div class="eraHead"><div><h3>${esc(g.era)}</h3><p>${esc(g.sub)}</p></div><div class="count">${req.filter(i=>status(i.id).read).length}/${req.length} richiesti letti</div></div><div class="issueList">${g.items.map(issueHtml).join("")}</div></section>`}
function renderBlocks(){const vis=visibleIssues(),order=(currentCharacter.series||[]).filter(s=>activeSeries==="Tutte"||s.id===activeSeries);els.seriesBlocks.innerHTML=order.map(s=>{const xs=vis.filter(i=>i.seriesId===s.id);if(!xs.length)return"";const all=currentCharacter.issues.filter(i=>i.seriesId===s.id&&i.required!==false&&!i.future),r=all.filter(i=>status(i.id).read).length,eras=[];for(const i of xs){let g=eras.find(x=>x.era===i.era);if(!g){g={era:i.era,sub:i.eraSub,items:[]};eras.push(g)}g.items.push(i)}return `<section class="seriesBlock" id="series-${esc(s.id)}"><div class="seriesHead"><div><div class="label">${esc(s.publisher)} · ${esc(s.years)}</div><h2>${esc(s.name)} ${esc(s.range)}</h2><p>${all.length} albi richiesti nel percorso</p></div><div class="seriesPct">${r}/${all.length} letti<br>${Math.round(r/(all.length||1)*100)}%</div></div>${eras.map(eraHtml).join("")}</section>`}).join("")||'<div class="loading">Nessun albo trovato.</div>';bindIssueActions()}
function bindIssueActions(){document.querySelectorAll("[data-owned]").forEach(b=>b.onclick=()=>setStatus(b.dataset.owned,{owned:!status(b.dataset.owned).owned}));document.querySelectorAll("[data-read]").forEach(b=>b.onclick=()=>{const s=status(b.dataset.read),v=!s.read;setStatus(b.dataset.read,{read:v,owned:v?true:s.owned})})}
function jumpToIssue(i){history.replaceState(null,"",`#/${activeCharacter}/${i.n}`);$( `issue-${i.seriesId}-${i.n}` )?.scrollIntoView({behavior:"smooth",block:"center"})}
function renderAll(){if(!currentCharacter)return;renderCharacters();renderHero();renderStats();renderNext();renderRoute();renderSeriesNav();renderFilters();renderBlocks();els.showOptional.style.display=currentCharacter.issues.some(i=>i.skip)?"block":"none";els.showOptional.textContent=optionalVisible?"− Nascondi numeri facoltativi":"+ Mostra numeri facoltativi"}

els.search.addEventListener("input",()=>renderAll());
els.jumpNext.onclick=()=>{const i=nextIssue();if(i)jumpToIssue(i)};
els.showOptional.onclick=()=>{optionalVisible=!optionalVisible;renderAll()};
els.compactBtn.onclick=()=>{document.body.classList.toggle("compact");els.compactBtn.textContent=document.body.classList.contains("compact")?"Vista completa":"Vista compatta"};
els.resetBtn.onclick=()=>{if(confirm(`Azzerare solo lo stato LETTO di ${currentCharacter.name}? Gli albi recuperati resteranno nella collezione globale.`)){state.characters[activeCharacter]={issues:{}};saveState();renderAll()}};
els.exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="marvel_archive_progressi.json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),600)};
els.importFile.onchange=e=>{const f=e.target.files?.[0];if(!f)return;const r=new FileReader();r.onload=()=>{try{state=normalizeState(JSON.parse(r.result));saveState();renderAll()}catch{alert("Backup non valido.")}};r.readAsText(f);e.target.value=""};
window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=currentCharacter.issues.find(x=>x.n===h.issue);if(i)jumpToIssue(i)}});

(async()=>{try{await loadManifest();renderCharacters();const h=parseHash();await switchCharacter(h.character,{updateHash:false,issue:h.issue});if(!location.hash)history.replaceState(null,"",`#/${activeCharacter}`)}catch(e){console.error(e);els.seriesBlocks.innerHTML=`<div class="loading error"><b>Errore di caricamento</b><br>${esc(e.message)}<br><br>Apri il sito tramite GitHub Pages o un server HTTP: i JSON non possono essere caricati correttamente con alcuni browser da file://.</div>`}})();