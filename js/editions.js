(() => {
  let manifest = {version:1,editions:[]};
  let byId = new Map();
  let coverageIndex = new Map();
  let loadPromise = null;
  let lastState = null;
  const coverageSnapshot = new Map();

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
      if(value === true){
        state.editions[id] = {physical:true,digital:false,owned:true};
        continue;
      }
      if(!value || typeof value !== "object"){
        delete state.editions[id];
        continue;
      }
      const hasFormats = Object.hasOwn(value,"physical") || Object.hasOwn(value,"digital");
      const physical = hasFormats ? !!value.physical : !!value.owned;
      const digital = hasFormats ? !!value.digital : false;
      if(!physical && !digital){
        delete state.editions[id];
        continue;
      }
      state.editions[id] = {...value,physical,digital,owned:true};
    }
    state.editionSchema = 2;
    return state;
  }

  function all(){ return manifest.editions || []; }
  function get(id){ return byId.get(id) || null; }

  function formatsFor(state,id){
    const value = state?.editions?.[id];
    const collection = state?.collection?.[id] || {};
    if(value === true) return {physical:true,digital:false};
    const explicit = value && typeof value === "object";
    const hasFormats = explicit && (Object.hasOwn(value,"physical") || Object.hasOwn(value,"digital"));
    const physical = hasFormats ? !!value.physical : !!value?.owned;
    const digital = hasFormats ? !!value.digital : false;
    return {
      physical: physical || !!collection.physical,
      digital: digital || !!collection.digital,
    };
  }

  function isPhysical(state,id){ return formatsFor(state,id).physical; }
  function isDigital(state,id){ return formatsFor(state,id).digital; }
  function isOwned(state,id){
    if(state?.collection?.[id]?.physical || state?.collection?.[id]?.digital) return true;
    const formats = formatsFor(state,id);
    return formats.physical || formats.digital;
  }

  function setFormat(state,id,format,enabled){
    if(format !== "physical" && format !== "digital") return;
    state.editions ??= {};
    const previous = state.editions[id] && typeof state.editions[id] === "object" ? state.editions[id] : {};
    const current = formatsFor(state,id);
    const next = {
      ...previous,
      physical: format === "physical" ? !!enabled : current.physical,
      digital: format === "digital" ? !!enabled : current.digital,
    };
    next.owned = next.physical || next.digital;
    if(next.owned){
      next.addedAt = previous.addedAt || new Date().toISOString();
      state.editions[id] = next;
      if(state.wishlist?.[id]) delete state.wishlist[id];
    }else{
      delete state.editions[id];
    }
  }

  function setOwned(state,id,owned){
    if(!owned){
      if(state?.editions) delete state.editions[id];
      return;
    }
    if(isOwned(state,id)) return;
    setFormat(state,id,"physical",true);
  }

  function optionsFor(pathId,issueId){
    return coverageIndex.get(coverageKey(pathId,issueId)) || [];
  }

  function formatLabel(state,id){
    const formats = formatsFor(state,id);
    if(formats.physical && formats.digital) return "Fisico + Digitale";
    if(formats.digital) return "Digitale";
    if(formats.physical) return "Fisico";
    return "";
  }

  function coverageStatus(state,pathId,issueId){
    lastState = state;
    const options = optionsFor(pathId,issueId);
    const ownedOptions = options.filter(item => isOwned(state,item.id));
    const contentAware = options.filter(item => Array.isArray(item.coverage?.requiredContentIds) && item.coverage.requiredContentIds.length);

    const required = new Set();
    for(const item of contentAware) for(const id of item.coverage.requiredContentIds || []) required.add(id);

    const calculate = subset => {
      if(!contentAware.length) return {covered:new Set(),complete:subset.length>0};
      const covered = new Set();
      for(const item of subset) for(const id of item.coverage?.contentIds || []) covered.add(id);
      return {covered,complete:required.size > 0 && [...required].every(id => covered.has(id))};
    };

    const overall = calculate(ownedOptions);
    const physicalOptions = ownedOptions.filter(item => isPhysical(state,item.id));
    const digitalOptions = ownedOptions.filter(item => isDigital(state,item.id));
    const physical = calculate(physicalOptions);
    const digital = calculate(digitalOptions);

    const result = {
      options,
      owned: overall.complete ? ownedOptions : [],
      ownedOptions,
      complete: overall.complete,
      completePhysical: physical.complete,
      completeDigital: digital.complete,
      physicalOwnedOptions: physicalOptions,
      digitalOwnedOptions: digitalOptions,
      coveredContentIds:[...overall.covered],
      requiredContentIds:[...required],
    };
    coverageSnapshot.set(coverageKey(pathId,issueId),result);
    return result;
  }

  function physicalObjectCount(state){
    const ids = new Set();
    for(const [id,value] of Object.entries(state?.collection || {})) if(value?.physical) ids.add(id);
    for(const edition of all()) if(isPhysical(state,edition.id)) ids.add(edition.id);
    return ids.size;
  }

  function ownedPublicationCount(state){
    const ids = new Set();
    for(const [id,value] of Object.entries(state?.collection || {})) if(value?.physical || value?.digital) ids.add(id);
    for(const edition of all()) if(isOwned(state,edition.id)) ids.add(edition.id);
    return ids.size;
  }

  function digitalObjectCount(state){
    const ids = new Set();
    for(const [id,value] of Object.entries(state?.collection || {})) if(value?.digital) ids.add(id);
    for(const edition of all()) if(isDigital(state,edition.id)) ids.add(edition.id);
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
      ? `<div class="editionExactNote"><b>Copertura per storie USA</b><span>${status.complete?"Le edizioni alternative possedute coprono insieme tutte le storie richieste.":"Ogni edizione posseduta evidenzia subito le tappe che copre. Le coperture parziali possono essere combinate fino a completare tutte le storie richieste."}</span></div>`
      : `<div class="editionExactNote"><b>Edizione mostrata nel percorso</b><span>${esc(issue.name)} · scegli separatamente se possiedi la ristampa in formato fisico, digitale o entrambi.</span></div>`;

    body.innerHTML = `
      <header class="editionDialogHead">
        <span>Edizioni alternative</span>
        <h2>${esc(issue.name)}</h2>
        <p>Lo spillato e le raccolte sono pubblicazioni diverse. Per ogni ristampa indica il formato che possiedi: Fisico e Digitale restano distinti, mentre la copertura editoriale usa le storie realmente presenti.</p>
      </header>
      ${unionNote}
      <div class="editionChoices">${options.map(edition => {
        const physical = isPhysical(state,edition.id);
        const digital = isDigital(state,edition.id);
        const owned = physical || digital;
        const wishlisted = !!state?.wishlist?.[edition.id];
        const lists = Object.entries(state?.lists || {});
        const coverageClass = edition.coverage?.complete === false ? "partial" : "complete";
        const ownedFormat = formatLabel(state,edition.id);
        return `<article class="editionChoice ${owned?"owned":""} ${physical?"physicalOwned":""} ${digital?"digitalOwned":""} ${coverageClass}">
          <div class="editionChoiceCover">${edition.cover?`<img src="${esc(edition.cover)}" alt="${esc(edition.name)}" referrerpolicy="no-referrer">`:""}</div>
          <div class="editionChoiceInfo"><span>${esc(edition.format || "Edizione alternativa")}</span><h3>${esc(edition.name)}</h3><p>${esc(edition.series)}${edition.number?` #${esc(edition.number)}`:""} · ${esc(edition.publisher || "")}</p><small>${esc(coverageCopy(edition))}</small>${ownedFormat?`<em class="editionOwnedFormatSummary">${esc(ownedFormat)} posseduto</em>`:""}${edition.url?`<a href="${esc(edition.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}</div>
          <div class="editionChoiceActions">
            <button type="button" class="editionWishlistButton ${wishlisted?"active":""}" data-toggle-edition-wishlist="${esc(edition.id)}">${wishlisted?"★ In wishlist":"☆ Wishlist"}</button>
            ${lists.length?`<select class="editionListSelect" data-add-edition-list="${esc(edition.id)}" aria-label="Aggiungi ${esc(edition.name)} a una lista"><option value="">+ Lista…</option>${lists.map(([listId,list])=>`<option value="${esc(listId)}">${(list.issueIds||[]).includes(edition.id)?"✓ ":""}${esc(list.name)}</option>`).join("")}</select>`:""}
            <div class="editionFormatButtons" role="group" aria-label="Formato posseduto">
              <button type="button" class="editionFormatButton physical ${physical?"owned":""}" data-edition-format="physical" data-edition-id="${esc(edition.id)}">${physical?"✓ ":""}Fisico</button>
              <button type="button" class="editionFormatButton digital ${digital?"owned":""}" data-edition-format="digital" data-edition-id="${esc(edition.id)}">${digital?"✓ ":""}Digitale</button>
            </div>
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
    body.querySelectorAll("[data-edition-format]").forEach(button => button.onclick = () => {
      const id = button.dataset.editionId;
      const format = button.dataset.editionFormat;
      const enabled = format === "physical" ? !isPhysical(state,id) : !isDigital(state,id);
      setFormat(state,id,format,enabled);
      onToggle?.(id,isOwned(state,id));
      openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList});
    });
    if(!dialog.open){
      if(typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open","");
    }
  }

  function currentPathId(){
    const match = String(location.hash || "").match(/^#\/([^/?#]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function badgeCopy(state,status){
    const owned = status?.ownedOptions || [];
    if(!owned.length) return "";
    const labels = owned.map(item => `${item.name} · ${formatLabel(state,item.id)}`).join(" + ");
    if(status.complete) return `Coperto da ${labels}`;
    const covered = status.coveredContentIds?.length || 0;
    const required = status.requiredContentIds?.length || 0;
    return required ? `Copertura ${covered}/${required} · ${labels}` : `Coperto da ${labels}`;
  }

  function badgeTitle(state,status){
    return (status?.ownedOptions || []).map(item => {
      const coverage = item.coverage || {};
      const covered = coverage.contentIds?.length || 0;
      const required = coverage.requiredContentIds?.length || 0;
      const ratio = required ? ` · ${covered}/${required} storie` : "";
      return `${item.name} · ${formatLabel(state,item.id)}${ratio}`;
    }).join("\n");
  }

  function refreshCoverageBadges(){
    requestAnimationFrame(() => {
      const state = lastState;
      const pathId = currentPathId();
      if(!state || !pathId) return;
      document.querySelectorAll(".issue[data-issue-id]").forEach(article => {
        const issueId = article.dataset.issueId;
        const status = coverageSnapshot.get(coverageKey(pathId,issueId));
        const badges = article.querySelector(".issueBadges");
        if(!badges) return;
        let badge = badges.querySelector(".editionCoverageBadge");
        const hasOwnedAlternative = !!status?.ownedOptions?.length;
        if(hasOwnedAlternative){
          if(!badge){
            badge = document.createElement("span");
            badge.className = "editionCoverageBadge";
            badges.append(badge);
          }
          badge.textContent = badgeCopy(state,status);
          badge.title = badgeTitle(state,status);
          badge.classList.toggle("partial",!status.complete);
          badge.classList.toggle("complete",!!status.complete);
        }else if(badge){
          badge.remove();
        }

        const button = article.querySelector("[data-editions]");
        if(button){
          button.classList.toggle("on",hasOwnedAlternative);
          button.classList.toggle("partial",hasOwnedAlternative && !status?.complete);
          button.classList.toggle("complete",!!status?.complete);
          if(hasOwnedAlternative) button.title = badgeTitle(state,status);
          else button.removeAttribute("title");
        }
      });
    });
  }

  document.addEventListener("marvel:render",refreshCoverageBadges);
  window.addEventListener("hashchange",refreshCoverageBadges);

  window.MarvelEditions = {
    load,normalizeState,all,get,
    isOwned,isPhysical,isDigital,setOwned,setFormat,formatLabel,
    optionsFor,coverageStatus,
    physicalObjectCount,digitalObjectCount,ownedPublicationCount,
    catalogItems,openPicker
  };
})();