(() => {
  let manifest = {version:1,editions:[]};
  let byId = new Map();
  let coverageIndex = new Map();
  let loadPromise = null;

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const coverageKey = (pathId,issueId) => `${pathId}\u0000${issueId}`;

  function rebuildIndexes(){
    byId = new Map((manifest.editions || []).map(item => [item.id,item]));
    coverageIndex = new Map();
    for(const edition of manifest.editions || []){
      for(const coverage of edition.coverage || []){
        for(const issueId of coverage.issueIds || []){
          const key = coverageKey(coverage.path,issueId);
          const entries = coverageIndex.get(key) || [];
          entries.push({...edition,coverage});
          coverageIndex.set(key,entries);
        }
      }
    }
  }

  async function load(version=1){
    if(loadPromise) return loadPromise;
    const token = encodeURIComponent(version);
    loadPromise = Promise.all([
      fetch(`data/editions.json?v=${token}`, {cache:"no-cache"}).then(response => {
        if(!response.ok) throw new Error(`Edizioni alternative HTTP ${response.status}`);
        return response.json();
      }),
      fetch(`data/curated-editions.json?v=${token}`, {cache:"no-cache"})
        .then(response => response.ok ? response.json() : {version:1,editions:[]})
        .catch(() => ({version:1,editions:[]})),
    ])
      .then(([data,curated]) => {
        if(!Array.isArray(data.editions)) throw new Error("Manifest edizioni alternative non valido");
        const merged = new Map(data.editions.map(item => [item.id,item]));
        for(const item of curated.editions || []){
          const previous = merged.get(item.id) || {};
          merged.set(item.id,{...previous,...item});
        }
        manifest = {...data,curatedVersion:curated.version || 1,editions:[...merged.values()]};
        rebuildIndexes();
        return manifest;
      })
      .catch(error => {
        console.error("Edizioni alternative non disponibili", error);
        manifest = {version:1,editions:[]};
        rebuildIndexes();
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
    return value === true || !!value?.owned || !!state?.collection?.[id]?.physical;
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
      if(state.wishlist?.[id]) delete state.wishlist[id];
    }else delete state.editions[id];
  }

  function optionsFor(pathId,issueId){
    return coverageIndex.get(coverageKey(pathId,issueId)) || [];
  }

  // Content-aware alternatives can split one route step across several differently-collected volumes.
  // A step becomes physically covered only when the UNION of owned alternatives contains every
  // requiredContentId. Legacy paths without content metadata keep the original any-owned behavior.
  function coverageStatus(state,pathId,issueId){
    const options = optionsFor(pathId,issueId);
    const ownedOptions = options.filter(item => isOwned(state,item.id));
    const contentAware = options.filter(item => Array.isArray(item.coverage?.requiredContentIds) && item.coverage.requiredContentIds.length);
    if(!contentAware.length) return {options,owned:ownedOptions,ownedOptions,complete:ownedOptions.length>0};

    const required = new Set();
    for(const item of contentAware) for(const id of item.coverage.requiredContentIds || []) required.add(id);
    const covered = new Set();
    for(const item of ownedOptions) for(const id of item.coverage?.contentIds || []) covered.add(id);
    const complete = required.size > 0 && [...required].every(id => covered.has(id));
    return {options,owned:complete?ownedOptions:[],ownedOptions,complete,coveredContentIds:[...covered],requiredContentIds:[...required]};
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

  function coverageCopy(edition){
    const coverage = edition.coverage || {};
    if(Array.isArray(coverage.requiredContentIds) && coverage.requiredContentIds.length){
      const covered = coverage.contentIds?.length || 0;
      const required = coverage.requiredContentIds.length;
      return coverage.complete ? `Copertura completa · ${covered}/${required} storie` : `Copertura parziale · ${covered}/${required} storie`;
    }
    return coverage.label || (edition.contents || []).join(" · ");
  }

  function openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList}){
    const options = optionsFor(pathId,issue?.id);
    if(!options.length) return;
    const status = coverageStatus(state,pathId,issue?.id);
    const dialog = ensureDialog();
    const body = dialog.querySelector(".editionDialogBody");
    const contentAware = options.some(item => item.coverage?.requiredContentIds?.length);
    const unionNote = contentAware
      ? `<div class="editionExactNote"><b>Copertura per storie USA</b><span>${status.complete?"Le edizioni alternative possedute coprono insieme tutte le storie richieste.":"Le edizioni parziali possono essere combinate: la tappa conta solo quando, insieme, coprono tutte le storie richieste."}</span></div>`
      : `<div class="editionExactNote"><b>Edizione mostrata nel percorso</b><span>${esc(issue.name)} · usa “Fisico” sulla scheda solo se possiedi davvero questo albo.</span></div>`;
    body.innerHTML = `
      <header class="editionDialogHead">
        <span>Edizioni alternative</span>
        <h2>${esc(issue.name)}</h2>
        <p>Lo spillato e le raccolte sono pubblicazioni diverse. Segna qui la ristampa che possiedi: il tracker userà solo la copertura editoriale realmente verificata.</p>
      </header>
      ${unionNote}
      <div class="editionChoices">${options.map(edition => {
        const owned = isOwned(state,edition.id);
        const wishlisted = !!state?.wishlist?.[edition.id];
        const lists = Object.entries(state?.lists || {});
        const coverageClass = edition.coverage?.complete === false ? "partial" : "complete";
        return `<article class="editionChoice ${owned?"owned":""} ${coverageClass}">
          <div class="editionChoiceCover">${edition.cover?`<img src="${esc(edition.cover)}" alt="${esc(edition.name)}" referrerpolicy="no-referrer">`:""}</div>
          <div class="editionChoiceInfo"><span>${esc(edition.format || "Edizione alternativa")}</span><h3>${esc(edition.name)}</h3><p>${esc(edition.series)}${edition.number?` #${esc(edition.number)}`:""} · ${esc(edition.publisher || "")}</p><small>${esc(coverageCopy(edition))}</small>${edition.url?`<a href="${esc(edition.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}</div>
          <div class="editionChoiceActions">
            <button type="button" class="editionWishlistButton ${wishlisted?"active":""}" data-toggle-edition-wishlist="${esc(edition.id)}">${wishlisted?"★ In wishlist":"☆ Wishlist"}</button>
            ${lists.length?`<select class="editionListSelect" data-add-edition-list="${esc(edition.id)}" aria-label="Aggiungi ${esc(edition.name)} a una lista"><option value="">+ Lista…</option>${lists.map(([listId,list])=>`<option value="${esc(listId)}">${(list.issueIds||[]).includes(edition.id)?"✓ ":""}${esc(list.name)}</option>`).join("")}</select>`:""}
            <button type="button" class="editionOwnButton ${owned?"owned":""}" data-toggle-edition="${esc(edition.id)}">${owned?"✓ Posseduto":"Segna posseduto"}</button>
          </div>
        </article>`;
      }).join("")}</div>`;
    body.querySelectorAll("[data-toggle-edition-wishlist]").forEach(button => button.onclick = () => {
      const id = button.dataset.toggleEditionWishlist;
      onToggleWishlist?.(id,!state?.wishlist?.[id]);
      openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList});
    });
    body.querySelectorAll("[data-add-edition-list]").forEach(select => select.onchange = () => {
      const listId = select.value;
      select.value = "";
      if(listId) onAddToList?.(select.dataset.addEditionList,listId);
      openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList});
    });
    body.querySelectorAll("[data-toggle-edition]").forEach(button => button.onclick = () => {
      const id = button.dataset.toggleEdition;
      onToggle?.(id,!isOwned(state,id));
      openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList});
    });
    if(!dialog.open){
      if(typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open","");
    }
  }

  window.MarvelEditions = {load,normalizeState,all,get,isOwned,setOwned,optionsFor,coverageStatus,physicalObjectCount,ownedPublicationCount,catalogItems,openPicker};
})();
