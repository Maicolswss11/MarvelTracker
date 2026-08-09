(() => {
  let api = null;
  let catalog = null;
  let catalogPromise = null;
  let activeTab = "overview";
  let activeListId = null;
  let pageLimit = 120;
  let searchTerm = "";
  let formatFilter = "all";

  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const fmt = value => new Intl.NumberFormat("it-IT").format(value || 0);

  function state(){
    const s = api.getState();
    s.collection ??= {};
    s.editions ??= {};
    window.MarvelEditions?.normalizeState(s);
    s.wishlist ??= {};
    s.lists ??= {};
    return s;
  }

  function manifest(){ return api.getManifest(); }

  function readIds(){
    const ids = new Set();
    for(const character of Object.values(state().characters || {})){
      for(const [id, value] of Object.entries(character?.issues || {})) if(value?.read) ids.add(id);
    }
    return ids;
  }

  function readPathsFor(id){
    const paths = [];
    const byId = new Map((manifest()?.characters || []).map(p => [p.id, p.name]));
    for(const [pathId, character] of Object.entries(state().characters || {})){
      if(character?.issues?.[id]?.read) paths.push({id:pathId,name:byId.get(pathId) || pathId});
    }
    return paths;
  }

  function itemStatus(id){
    const s = state();
    const entry = s.collection?.[id] || {};
    const editionPhysical = !!window.MarvelEditions?.get(id) && !!window.MarvelEditions?.isOwned(s,id);
    const physical = !!entry.physical || editionPhysical;
    const digital = !!entry.digital;
    return {physical,digital,owned:physical||digital,wishlist:!!s.wishlist?.[id],read:readIds().has(id),editionPhysical};
  }

  function save(){
    state().profileSchema = 1;
    api.saveState();
    decorateTrackerWishlist();
  }

  async function loadCatalog(){
    if(catalog) return catalog;
    if(catalogPromise) return catalogPromise;
    const version = manifest()?.version || 1;
    catalogPromise = fetch(`data/catalog.json?v=${encodeURIComponent(version)}`, {cache:"no-cache"})
      .then(response => {
        if(!response.ok) throw new Error(`Catalogo HTTP ${response.status}`);
        return response.json();
      })
      .then(data => {
        if(!Array.isArray(data.issues)) throw new Error("Catalogo globale non valido");
        catalog = data;
        return data;
      })
      .finally(() => { catalogPromise = null; });
    return catalogPromise;
  }

  function allCatalogItems(){
    const merged = new Map((catalog?.issues || []).map(item => [item.id,{...item}]));
    for(const edition of window.MarvelEditions?.catalogItems(manifest()) || []) merged.set(edition.id,{...(merged.get(edition.id)||{}),...edition});
    return [...merged.values()];
  }

  function collectionStats(){
    const s = state();
    const values = Object.values(s.collection || {});
    const directPhysical = values.filter(x => x?.physical).length;
    const physical = window.MarvelEditions?.physicalObjectCount(s) ?? directPhysical;
    const digital = values.filter(x => x?.digital).length;
    const both = values.filter(x => x?.physical && x?.digital).length;
    const owned = window.MarvelEditions?.ownedPublicationCount(s) ?? values.filter(x => x?.physical || x?.digital).length;
    const read = readIds().size;
    const wishlist = Object.keys(state().wishlist || {}).length;
    const lists = Object.keys(state().lists || {}).length;
    return {physical,digital,both,owned,read,wishlist,lists};
  }

  function toggleEdition(id){
    const s = state();
    window.MarvelEditions?.setOwned(s,id,!window.MarvelEditions?.isOwned(s,id));
    save();
    void render();
  }

  function toggleFormat(id, key){
    const s = state();
    const entry = s.collection[id] = {...(s.collection[id] || {})};
    entry[key] = !entry[key];
    entry.physical = !!entry.physical;
    entry.digital = !!entry.digital;
    entry.owned = entry.physical || entry.digital;
    save();
    void render();
  }

  function toggleWishlist(id){
    const s = state();
    if(s.wishlist[id]) delete s.wishlist[id];
    else s.wishlist[id] = {addedAt:new Date().toISOString()};
    save();
    void render();
  }

  function createList(){
    const name = prompt("Nome della nuova lista:", "Da leggere");
    if(!name?.trim()) return;
    const id = globalThis.crypto?.randomUUID?.() || `list-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    state().lists[id] = {name:name.trim(), issueIds:[], createdAt:new Date().toISOString()};
    activeListId = id;
    save();
    void render();
  }

  function renameList(id){
    const list = state().lists?.[id];
    if(!list) return;
    const name = prompt("Nuovo nome della lista:", list.name);
    if(!name?.trim()) return;
    list.name = name.trim();
    save();
    void render();
  }

  function deleteList(id){
    const list = state().lists?.[id];
    if(!list || !confirm(`Eliminare la lista “${list.name}”?\nGli albi non verranno rimossi dalla collezione.`)) return;
    delete state().lists[id];
    if(activeListId === id) activeListId = Object.keys(state().lists)[0] || null;
    save();
    void render();
  }

  function addToList(issueId, listId){
    if(!listId) return;
    const list = state().lists?.[listId];
    if(!list) return;
    list.issueIds ??= [];
    if(!list.issueIds.includes(issueId)) list.issueIds.push(issueId);
    save();
    void render();
  }

  function removeFromList(issueId, listId){
    const list = state().lists?.[listId];
    if(!list) return;
    list.issueIds = (list.issueIds || []).filter(id => id !== issueId);
    save();
    void render();
  }

  function tabButton(id,label,count=null){
    return `<button type="button" class="profileTab ${activeTab===id?"active":""}" data-profile-tab="${id}">${esc(label)}${count===null?"":`<span>${fmt(count)}</span>`}</button>`;
  }

  function renderStats(){
    const s = collectionStats();
    $("profileStats").innerHTML = `
      <article><span>Collezione</span><b>${fmt(s.owned)}</b><small>albi unici recuperati</small></article>
      <article><span>Fisici</span><b>${fmt(s.physical)}</b><small>${fmt(s.both)} anche digitali</small></article>
      <article><span>Digitali</span><b>${fmt(s.digital)}</b><small>${fmt(s.both)} anche fisici</small></article>
      <article><span>Letti</span><b>${fmt(s.read)}</b><small>albi unici letti</small></article>
      <article><span>Wishlist</span><b>${fmt(s.wishlist)}</b><small>da recuperare</small></article>
      <article><span>Liste</span><b>${fmt(s.lists)}</b><small>liste personali</small></article>`;
  }

  function renderTabs(){
    const s = collectionStats();
    $("profileTabs").innerHTML = [
      tabButton("overview","Dashboard"),
      tabButton("collection","Collezione",s.owned),
      tabButton("read","Letti",s.read),
      tabButton("wishlist","Wishlist",s.wishlist),
      tabButton("lists","Liste",s.lists),
      tabButton("catalog","Catalogo",allCatalogItems().length),
    ].join("");
    $("profileTabs").querySelectorAll("[data-profile-tab]").forEach(button => button.onclick = () => {
      activeTab = button.dataset.profileTab;
      pageLimit = 120;
      searchTerm = "";
      formatFilter = "all";
      void render();
    });
  }

  function progressRows(){
    const rows = (manifest()?.characters || []).map(path => {
      const total = path.totalRequired || 0;
      const read = Object.values(state().characters?.[path.id]?.issues || {}).filter(x => x?.read).length;
      return {...path,total,read,pct:Math.min(100,Math.round(read/(total || 1)*100))};
    }).filter(x => x.read > 0).sort((a,b) => b.pct-a.pct || b.read-a.read).slice(0,10);
    if(!rows.length) return `<div class="profileEmpty"><b>Nessun percorso iniziato</b><span>Quando segni i primi albi come letti, qui vedrai l’avanzamento per percorso.</span></div>`;
    return rows.map(row => `<button type="button" class="profileProgressRow" data-open-path="${esc(row.id)}"><span><b>${esc(row.name)}</b><small>${row.read}/${row.total} letti</small></span><span class="profileProgressTrack"><i style="width:${row.pct}%"></i></span><strong>${row.pct}%</strong></button>`).join("");
  }

  function renderOverview(){
    const stats = collectionStats();
    const total = allCatalogItems().length;
    const missing = Math.max(0,total-stats.owned);
    $("profileToolbar").innerHTML = "";
    $("profileBody").innerHTML = `
      <section class="profileOverviewGrid">
        <article class="profileOverviewCard profileOverviewWide"><div class="profileCardHead"><div><span>Progressi</span><h2>I percorsi che stai seguendo</h2></div></div><div class="profileProgressRows">${progressRows()}</div></article>
        <article class="profileOverviewCard"><span>Catalogo globale</span><b class="profileMegaNumber">${fmt(total)}</b><p>albi fisici unici mappati, deduplicati tra tutti i percorsi.</p></article>
        <article class="profileOverviewCard"><span>Ancora da recuperare</span><b class="profileMegaNumber">${fmt(missing)}</b><p>albi del catalogo che non risultano né fisici né digitali.</p></article>
        <article class="profileOverviewCard"><span>Copertura collezione</span><b class="profileMegaNumber">${total?Math.round(stats.owned/total*100):0}%</b><p>${fmt(stats.owned)} posseduti su ${fmt(total)} albi unici mappati.</p></article>
        <article class="profileOverviewCard"><span>Wishlist</span><b class="profileMegaNumber">${fmt(stats.wishlist)}</b><p>titoli che hai segnato da recuperare.</p><button type="button" data-overview-open="wishlist">Apri wishlist →</button></article>
      </section>`;
    $("profileBody").querySelectorAll("[data-open-path]").forEach(button => button.onclick = () => api.openCharacter(button.dataset.openPath));
    $("profileBody").querySelectorAll("[data-overview-open]").forEach(button => button.onclick = () => {activeTab=button.dataset.overviewOpen;void render()});
  }

  function filterItems(items){
    const q = searchTerm.trim().toLowerCase();
    return items.filter(item => {
      if(q && ![item.name,item.series,item.title,item.date,item.n,...(item.pathNames || [])].join(" ").toLowerCase().includes(q)) return false;
      const st = itemStatus(item.id);
      if(formatFilter === "physical" && !st.physical) return false;
      if(formatFilter === "digital" && !st.digital) return false;
      if(formatFilter === "both" && !(st.physical && st.digital)) return false;
      if(formatFilter === "missing" && st.owned) return false;
      return true;
    });
  }

  function itemPool(){
    const all = allCatalogItems();
    const s = state();
    const reads = readIds();
    if(activeTab === "collection") return all.filter(item => itemStatus(item.id).owned);
    if(activeTab === "read") return all.filter(item => reads.has(item.id));
    if(activeTab === "wishlist") return all.filter(item => s.wishlist?.[item.id]);
    if(activeTab === "catalog") return all;
    return [];
  }

  function listOptions(issueId){
    const lists = Object.entries(state().lists || {});
    if(!lists.length) return "";
    return `<select class="profileListSelect" data-add-list="${esc(issueId)}" aria-label="Aggiungi a una lista"><option value="">+ Lista…</option>${lists.map(([id,list])=>`<option value="${esc(id)}">${(list.issueIds||[]).includes(issueId)?"✓ ":""}${esc(list.name)}</option>`).join("")}</select>`;
  }

  function issueCard(item,{listId=null}={}){
    const st = itemStatus(item.id);
    const isAlternative = !!item.isAlternativeEdition;
    const readPaths = st.read ? readPathsFor(item.id) : [];
    const pathButtons = (item.paths || []).slice(0,3).map((id,index)=>`<button type="button" data-open-path="${esc(id)}">${esc(item.pathNames?.[index] || id)}</button>`).join("");
    const morePaths = (item.paths?.length || 0) > 3 ? `<span>+${item.paths.length-3}</span>` : "";
    return `<article class="profileIssueCard ${isAlternative?"editionCard":""}" data-profile-issue="${esc(item.id)}">
      <div class="profileIssueCover">${item.cover?`<img loading="lazy" src="${esc(item.cover)}" alt="${esc(item.name)}" referrerpolicy="no-referrer">`:`<div>${esc(item.series || "Marvel")}<b>#${esc(item.displayNumber ?? item.n ?? "")}</b></div>`}</div>
      <div class="profileIssueInfo">
        <div class="profileIssueBadges">${isAlternative?'<span class="editionAlternative">Edizione alternativa</span>':""}${st.physical?'<span class="physical">Fisico</span>':""}${st.digital?'<span class="digital">Digitale</span>':""}${st.read?'<span class="read">Letto</span>':""}${st.wishlist?'<span class="wishlist">Wishlist</span>':""}</div>
        <h3>${esc(item.name)}</h3>
        <p>${esc(item.title || "")}</p>
        <small>${esc(item.date || "")}${item.future?" · Annunciato":""}</small>
        ${st.read&&readPaths.length?`<div class="profileReadPaths">Letto in ${readPaths.slice(0,2).map(x=>esc(x.name)).join(" · ")}${readPaths.length>2?` · +${readPaths.length-2}`:""}</div>`:""}
        <div class="profileIssuePaths">${pathButtons}${morePaths}</div>
      </div>
      <div class="profileIssueActions">
        ${isAlternative?`<button type="button" class="${st.physical?"on physical":""}" data-profile-edition="${esc(item.id)}">${st.physical?"✓ ":""}Fisico</button>`:`<button type="button" class="${st.physical?"on physical":""}" data-profile-physical="${esc(item.id)}">Fisico</button><button type="button" class="${st.digital?"on digital":""}" data-profile-digital="${esc(item.id)}">Digitale</button>`}
        <button type="button" class="${st.wishlist?"on wishlist":""}" data-profile-wishlist="${esc(item.id)}">★ Wishlist</button>
        ${listOptions(item.id)}
        ${listId?`<button type="button" class="removeListIssue" data-remove-list-issue="${esc(item.id)}" data-list-id="${esc(listId)}">Rimuovi dalla lista</button>`:""}
      </div>
    </article>`;
  }

  function bindIssueCards(root=$("profileBody")){
    root.querySelectorAll("[data-profile-physical]").forEach(button => button.onclick = () => toggleFormat(button.dataset.profilePhysical,"physical"));
    root.querySelectorAll("[data-profile-edition]").forEach(button => button.onclick = () => toggleEdition(button.dataset.profileEdition));
    root.querySelectorAll("[data-profile-digital]").forEach(button => button.onclick = () => toggleFormat(button.dataset.profileDigital,"digital"));
    root.querySelectorAll("[data-profile-wishlist]").forEach(button => button.onclick = () => toggleWishlist(button.dataset.profileWishlist));
    root.querySelectorAll("[data-open-path]").forEach(button => button.onclick = () => api.openCharacter(button.dataset.openPath));
    root.querySelectorAll("[data-add-list]").forEach(select => select.onchange = () => {const listId=select.value;select.value="";if(listId)addToList(select.dataset.addList,listId)});
    root.querySelectorAll("[data-remove-list-issue]").forEach(button => button.onclick = () => removeFromList(button.dataset.removeListIssue,button.dataset.listId));
  }

  function renderItemTab(){
    const raw = itemPool();
    const filtered = filterItems(raw);
    const shown = filtered.slice(0,pageLimit);
    const labels = {collection:"La mia collezione",read:"Albi letti",wishlist:"Wishlist",catalog:"Catalogo globale"};
    $("profileToolbar").innerHTML = `<div class="profileSearch"><input id="profileSearchInput" type="search" value="${esc(searchTerm)}" placeholder="Cerca titolo, testata, numero, percorso…"></div><div class="profileFormatFilters"><button data-profile-format="all" class="${formatFilter==="all"?"active":""}">Tutti</button><button data-profile-format="physical" class="${formatFilter==="physical"?"active":""}">Fisici</button><button data-profile-format="digital" class="${formatFilter==="digital"?"active":""}">Digitali</button><button data-profile-format="both" class="${formatFilter==="both"?"active":""}">Entrambi</button><button data-profile-format="missing" class="${formatFilter==="missing"?"active":""}">Mancanti</button></div>`;
    $("profileBody").innerHTML = `<section class="profileCatalogSection"><div class="profileCatalogHead"><div><span>${esc(labels[activeTab])}</span><h2>${fmt(filtered.length)} albi</h2></div>${activeTab==="wishlist"?'<button type="button" data-create-list>+ Nuova lista</button>':""}</div><div class="profileIssueGrid">${shown.map(item=>issueCard(item)).join("") || '<div class="profileEmpty"><b>Nessun albo trovato</b><span>Modifica i filtri o aggiungi nuovi albi alla collezione.</span></div>'}</div>${shown.length<filtered.length?`<button type="button" class="profileLoadMore" id="profileLoadMore">Mostra altri ${Math.min(120,filtered.length-shown.length)}</button>`:""}</section>`;
    const search = $("profileSearchInput");
    search.oninput = () => {searchTerm=search.value;pageLimit=120;renderItemTab()};
    $("profileToolbar").querySelectorAll("[data-profile-format]").forEach(button => button.onclick=()=>{formatFilter=button.dataset.profileFormat;pageLimit=120;renderItemTab()});
    $("profileLoadMore")?.addEventListener("click",()=>{pageLimit+=120;renderItemTab()});
    $("profileBody").querySelector("[data-create-list]")?.addEventListener("click",createList);
    bindIssueCards();
  }

  function renderLists(){
    const lists = Object.entries(state().lists || {});
    if(!activeListId || !state().lists?.[activeListId]) activeListId = lists[0]?.[0] || null;
    $("profileToolbar").innerHTML = `<button type="button" class="profileNewList" id="profileNewList">+ Nuova lista</button>`;
    $("profileNewList").onclick = createList;
    if(!lists.length){
      $("profileBody").innerHTML = `<div class="profileEmpty profileEmptyLarge"><b>Non hai ancora liste</b><span>Crea liste come “Da leggere”, “Da comprare”, “Hickman”, “Ultimate preferiti” o qualsiasi raccolta personale.</span><button type="button" id="profileEmptyNewList">Crea la prima lista</button></div>`;
      $("profileEmptyNewList").onclick = createList;
      return;
    }
    const selected = state().lists[activeListId];
    const byId = new Map((catalog?.issues || []).map(item => [item.id,item]));
    const items = (selected.issueIds || []).map(id=>byId.get(id)).filter(Boolean);
    $("profileBody").innerHTML = `<section class="profileListsLayout"><aside class="profileListsNav">${lists.map(([id,list])=>`<button type="button" class="${id===activeListId?"active":""}" data-profile-list="${esc(id)}"><b>${esc(list.name)}</b><span>${fmt((list.issueIds||[]).length)} albi</span></button>`).join("")}</aside><div class="profileListContent"><div class="profileListHead"><div><span>Lista personale</span><h2>${esc(selected.name)}</h2><p>${fmt(items.length)} albi</p></div><div><button type="button" data-rename-list="${esc(activeListId)}">Rinomina</button><button type="button" class="danger" data-delete-list="${esc(activeListId)}">Elimina</button></div></div><div class="profileIssueGrid">${items.map(item=>issueCard(item,{listId:activeListId})).join("") || '<div class="profileEmpty"><b>Lista vuota</b><span>Usa “+ Lista…” nelle schede della Collezione, Wishlist o Catalogo per aggiungere albi.</span></div>'}</div></div></section>`;
    $("profileBody").querySelectorAll("[data-profile-list]").forEach(button=>button.onclick=()=>{activeListId=button.dataset.profileList;void render()});
    $("profileBody").querySelector("[data-rename-list]")?.addEventListener("click",()=>renameList(activeListId));
    $("profileBody").querySelector("[data-delete-list]")?.addEventListener("click",()=>deleteList(activeListId));
    bindIssueCards();
  }

  async function render(){
    if(!api || $("profileView")?.hidden) return;
    renderStats();
    renderTabs();
    if(activeTab === "overview") renderOverview();
    else if(activeTab === "lists") renderLists();
    else renderItemTab();
  }

  function decorateTrackerWishlist(){
    if(!api) return;
    document.querySelectorAll("#seriesBlocks .issue[data-issue-id]").forEach(card => {
      const id = card.dataset.issueId;
      const status = card.querySelector(".status");
      if(!status || !id) return;
      let button = status.querySelector("[data-route-wishlist]");
      if(!button){
        button = document.createElement("button");
        button.type = "button";
        button.dataset.routeWishlist = id;
        button.innerHTML = "<span>★</span><span>Wishlist</span>";
        button.onclick = () => toggleWishlist(id);
        status.append(button);
      }
      const on = !!state().wishlist?.[id];
      button.classList.toggle("on",on);
      button.classList.toggle("wishlist",on);
      button.setAttribute("aria-pressed",String(on));
    });
  }

  async function show({updateHash=true}={}){
    if(!api) return;
    document.body.classList.remove("homeActive","bulkSelectMode");
    document.body.classList.add("profileActive");
    $("homeView").hidden = true;
    $("trackerView").hidden = true;
    $("profileView").hidden = false;
    if(updateHash) history.replaceState(null,"","#/profile");
    $("profileBody").innerHTML = '<div class="profileLoading">Preparazione del catalogo personale…</div>';
    try{
      await loadCatalog();
      await render();
    }catch(error){
      console.error(error);
      $("profileBody").innerHTML = `<div class="profileEmpty profileEmptyLarge"><b>Catalogo non disponibile</b><span>${esc(error.message)}</span></div>`;
    }
  }

  function init(nextApi){
    api = nextApi;
    const s = state();
    s.wishlist ??= {};
    s.lists ??= {};
    s.profileSchema = 1;

    $("profileHomeBtn").onclick = () => api.showHome();
    $("profileAccountBtn").onclick = () => api.openAccount();
    $("homeProfileBtn").onclick = () => void show();
    $("trackerProfileBtn").onclick = () => void show();

    const observer = new MutationObserver(decorateTrackerWishlist);
    observer.observe($("seriesBlocks"),{childList:true,subtree:true});
    decorateTrackerWishlist();
  }

  window.MarvelProfile = {init,show,render,decorateTrackerWishlist};
})();
