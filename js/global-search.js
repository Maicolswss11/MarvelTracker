(() => {
  const RESULT_LIMIT = 48;
  const RECENT_KEY = "marvel_archive_global_search_recent_v1";
  const SEARCH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>';

  let api = null;
  let manifest = null;
  let catalog = null;
  let searchItems = [];
  let pathById = new Map();
  let loadPromise = null;
  let activeFilter = "all";
  let initialized = false;
  let renderTimer = 0;

  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const normalize = value => String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("it-IT")
    .replace(/([a-z])([0-9])/g, "$1 $2")
    .replace(/([0-9])([a-z])/g, "$1 $2")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
  const compact = value => normalize(value).replace(/\s+/g, "");
  const fmt = number => new Intl.NumberFormat("it-IT").format(Number(number) || 0);
  const dialog = () => document.getElementById("globalSearchDialog");

  function contentText(content){
    if(typeof content === "string") return content;
    return [content?.id,content?.series,content?.number,content?.title].filter(Boolean).join(" ");
  }

  function itemSearchBlob(item){
    return normalize([
      item.id,
      item.name,
      item.series,
      item.number,
      item.n,
      item.title,
      item.date,
      ...(item.pathNames || []),
      ...(item.contents || []).map(contentText),
      ...(item.pathEntries || []).flatMap(entry => [entry.pathName,entry.era,entry.instruction,...(entry.contentIds || [])]),
    ].join(" "));
  }

  function normalizePathEntries(item){
    if(Array.isArray(item.pathEntries) && item.pathEntries.length) return item.pathEntries.map(entry => ({
      ...entry,
      pathName:entry.pathName || pathById.get(entry.pathId)?.name || entry.pathId,
      optional:!!entry.optional,
    }));
    return (item.paths || []).map((pathId,index) => ({
      pathId,
      pathName:item.pathNames?.[index] || pathById.get(pathId)?.name || pathId,
      token:String(item.n ?? ""),
      position:null,
      contentIds:(item.contents || []).map(content => content?.id).filter(Boolean),
      required:true,
      optional:false,
    }));
  }

  function buildIssueItem(item){
    const pathEntries = normalizePathEntries(item);
    const result = {
      ...item,
      kind:"issue",
      kindLabel:"Albo nel percorso",
      number:item.displayNumber ?? item.n,
      pathEntries,
      pathNames:pathEntries.map(entry => entry.pathName),
    };
    result.searchBlob = itemSearchBlob(result);
    result.searchCompact = result.searchBlob.replace(/\s+/g, "");
    return result;
  }

  function buildEditionPathEntries(edition,byIssue){
    const grouped = new Map();
    for(const coverage of edition.coverage || []){
      const pathId = coverage.path;
      if(!pathId) continue;
      const key = pathId;
      const current = grouped.get(key) || {
        pathId,
        pathName:pathById.get(pathId)?.name || pathId,
        token:"",
        position:null,
        issueIds:[],
        contentIds:[],
        labels:[],
      };
      if(coverage.label && !current.labels.includes(coverage.label)) current.labels.push(coverage.label);
      for(const issueId of coverage.issueIds || []){
        if(!current.issueIds.includes(issueId)) current.issueIds.push(issueId);
        const baseIssue = byIssue.get(issueId);
        const reference = baseIssue?.pathEntries?.find(entry => entry.pathId === pathId);
        if(reference && !current.token){
          current.token = reference.token || "";
          current.position = reference.position;
        }
        for(const contentId of reference?.contentIds || []) if(!current.contentIds.includes(contentId)) current.contentIds.push(contentId);
      }
      grouped.set(key,current);
    }
    return [...grouped.values()];
  }

  function buildEditionItem(edition,byIssue){
    const pathEntries = buildEditionPathEntries(edition,byIssue);
    const pathNames = pathEntries.map(entry => entry.pathName);
    const contents = (edition.contents || []).map(content => typeof content === "string" ? {title:content} : content);
    const result = {
      ...edition,
      kind:"edition",
      kindLabel:"Edizione alternativa",
      n:edition.number,
      number:edition.number,
      title:(edition.coverage || []).map(row => row.label).filter(Boolean).join(" · ") || contents.map(contentText).join(" · "),
      contents,
      paths:pathEntries.map(entry => entry.pathId),
      pathNames,
      pathEntries,
      isAlternativeEdition:true,
    };
    result.searchBlob = itemSearchBlob(result);
    result.searchCompact = result.searchBlob.replace(/\s+/g, "");
    return result;
  }

  async function loadIndex(){
    if(catalog) return catalog;
    if(loadPromise) return loadPromise;
    const version = manifest?.version || 1;
    loadPromise = fetch(`data/catalog.json?v=${encodeURIComponent(version)}`, {cache:"no-cache"})
      .then(response => {
        if(!response.ok) throw new Error(`Catalogo HTTP ${response.status}`);
        return response.json();
      })
      .then(data => {
        if(!Array.isArray(data.issues)) throw new Error("Catalogo globale non valido");
        catalog = data;
        const issues = data.issues.map(buildIssueItem);
        const byIssue = new Map(issues.map(item => [item.id,item]));
        const editions = (window.MarvelEditions?.all?.() || [])
          .filter(edition => (edition.coverage || []).some(row => row.path && row.issueIds?.length))
          .map(edition => buildEditionItem(edition,byIssue));
        searchItems = [...issues,...editions];
        return data;
      })
      .finally(() => { loadPromise = null; });
    return loadPromise;
  }

  function scoreItem(item,rawQuery){
    const query = normalize(rawQuery);
    const queryCompact = compact(rawQuery);
    const tokens = query.split(" ").filter(Boolean);
    if(!tokens.length) return -1;
    const matchesAll = tokens.every(token => item.searchBlob.includes(token) || item.searchCompact.includes(token));
    if(!matchesAll && !item.searchCompact.includes(queryCompact)) return -1;

    const name = normalize(item.name);
    const series = normalize(item.series);
    const identifier = normalize(item.id);
    const pathNames = normalize((item.pathNames || []).join(" "));
    const contents = normalize((item.contents || []).map(contentText).join(" "));
    let score = item.kind === "issue" ? 12 : 0;
    if(identifier === query || compact(item.id) === queryCompact) score += 420;
    if(name === query) score += 350;
    if(name.startsWith(query)) score += 230;
    else if(name.includes(query)) score += 180;
    if(series === query) score += 170;
    else if(series.startsWith(query)) score += 130;
    else if(series.includes(query)) score += 90;
    if(contents.includes(query) || compact(contents).includes(queryCompact)) score += 145;
    if(pathNames.includes(query)) score += 70;
    if(item.searchCompact.includes(queryCompact)) score += 60;
    score += Math.max(0,80 - name.length / 3);
    return score;
  }

  function filteredResults(query){
    return searchItems
      .filter(item => activeFilter === "all" || item.kind === activeFilter)
      .map(item => ({item,score:scoreItem(item,query)}))
      .filter(result => result.score >= 0)
      .sort((a,b) => b.score-a.score || String(a.item.name).localeCompare(String(b.item.name),"it"))
      .slice(0,RESULT_LIMIT)
      .map(result => result.item);
  }

  function statusFor(item){
    const state = api?.getState?.() || {};
    if(item.kind === "edition"){
      const physical = !!window.MarvelEditions?.isOwned?.(state,item.id);
      return {physical,digital:false,readCount:0,coveredCount:item.pathEntries.length};
    }
    const collection = state.collection?.[item.id] || {};
    const readCount = item.pathEntries.filter(entry => state.characters?.[entry.pathId]?.issues?.[item.id]?.read).length;
    const coveredCount = item.pathEntries.filter(entry => window.MarvelEditions?.coverageStatus?.(state,entry.pathId,item.id)?.owned?.length).length;
    return {physical:!!collection.physical,digital:!!collection.digital,readCount,coveredCount};
  }

  function coverMarkup(item){
    const label = item.series || "Marvel";
    const number = item.number ?? "";
    return `<div class="globalSearchCover"><span><small>${esc(label)}</small><b>${number!==""?`#${esc(number)}`:"MARVEL"}</b></span>${item.cover?`<img loading="lazy" src="${esc(item.cover)}" alt="${esc(item.name)}" referrerpolicy="no-referrer" onerror="this.remove()">`:""}</div>`;
  }

  function contentMarkup(item){
    const contents = (item.contents || []).map(contentText).filter(Boolean);
    if(!contents.length) return '<div class="globalSearchContents muted"><span>Contenuti USA</span><p>Mappatura non disponibile per questa edizione.</p></div>';
    const shown = contents.slice(0,3);
    return `<div class="globalSearchContents"><span>Contenuti USA</span><p>${shown.map(esc).join(" · ")}${contents.length>shown.length?` · +${contents.length-shown.length}`:""}</p></div>`;
  }

  function pathEntryMeta(entry,item){
    if(item.kind === "edition"){
      const count = entry.issueIds?.length || 0;
      return `${count} ${count===1?"tappa coperta":"tappe coperte"}`;
    }
    const position = entry.position;
    const contentCount = entry.contentIds?.length || 0;
    const pieces = [];
    if(position !== null && position !== undefined && position !== "") pieces.push(`Tappa ${position}`);
    if(contentCount) pieces.push(`${contentCount} ${contentCount===1?"contenuto":"contenuti"}`);
    if(entry.optional) pieces.push("Facoltativo");
    return pieces.join(" · ") || "Apri nel percorso";
  }

  function pathEntryContents(entry,item){
    if(item.kind === "edition") return (entry.labels || []).join(" · ");
    const byId = new Map((item.contents || []).filter(content => typeof content === "object").map(content => [content.id,content]));
    return (entry.contentIds || []).map(contentId => {
      const content = byId.get(contentId);
      return content ? `${content.series || "Marvel"}${content.number?` #${content.number}`:""}` : contentId;
    }).join(" · ");
  }

  function pathsMarkup(item){
    const entries = item.pathEntries || [];
    return `<div class="globalSearchPathBlock"><div class="globalSearchPathHead"><span>Presente in</span><b>${entries.length} ${entries.length===1?"percorso":"percorsi"}</b></div><div class="globalSearchPaths">${entries.map(entry => {const contents=pathEntryContents(entry,item);return `<button type="button" data-search-open-path="${esc(entry.pathId)}" data-search-token="${esc(entry.token || "")}" data-search-item="${esc(item.id)}" title="${esc(contents)}"><span><b>${esc(entry.pathName)}</b><small>${esc(pathEntryMeta(entry,item))}</small>${contents?`<em>${esc(contents)}</em>`:""}</span><i aria-hidden="true">→</i></button>`}).join("")}</div></div>`;
  }

  function resultMarkup(item){
    const status = statusFor(item);
    const badges = [
      `<span class="kind ${item.kind}">${esc(item.kindLabel)}</span>`,
      item.future?'<span class="future">Annunciato</span>':"",
      status.physical?'<span class="physical">Fisico</span>':"",
      status.digital?'<span class="digital">Digitale</span>':"",
      status.readCount?`<span class="read">Letto in ${status.readCount}</span>`:"",
      status.coveredCount&&!status.physical?`<span class="covered">Coperto in ${status.coveredCount}</span>`:"",
    ].join("");
    const publication = [item.series,item.number!==null&&item.number!==undefined&&item.number!==""?`#${item.number}`:"",item.date].filter(Boolean).join(" · ");
    return `<article class="globalSearchResult" data-search-result="${esc(item.id)}">
      ${coverMarkup(item)}
      <div class="globalSearchResultBody">
        <div class="globalSearchBadges">${badges}</div>
        <h3>${esc(item.name)}</h3>
        <p class="globalSearchPublication">${esc(publication)}</p>
        ${contentMarkup(item)}
        ${pathsMarkup(item)}
      </div>
      ${item.url?`<a class="globalSearchSource" href="${esc(item.url)}" target="_blank" rel="noopener" aria-label="Apri ${esc(item.name)} su ComicsBox">ComicsBox ↗</a>`:""}
    </article>`;
  }

  function recentQueries(){
    try{
      const values = JSON.parse(localStorage.getItem(RECENT_KEY));
      return Array.isArray(values) ? values.filter(Boolean).slice(0,5) : [];
    }catch{return []}
  }

  function rememberQuery(query){
    const value = String(query || "").trim();
    if(value.length < 2) return;
    const values = [value,...recentQueries().filter(item => normalize(item)!==normalize(value))].slice(0,5);
    localStorage.setItem(RECENT_KEY,JSON.stringify(values));
  }

  function emptyMarkup(){
    const recent = recentQueries();
    const examples = recent.length ? recent : ["X-Force #0","NM1 #98","House of M"];
    return `<div class="globalSearchWelcome"><span class="globalSearchWelcomeIcon">${SEARCH_ICON}</span><div><span>Ricerca globale</span><h2>Trova un albo in tutto l'archivio.</h2><p>Cerca una pubblicazione italiana, una testata, un numero o persino un capitolo USA. Vedrai ogni percorso in cui compare senza duplicare l'albo fisico.</p></div><div class="globalSearchSuggestions"><b>${recent.length?"Ricerche recenti":"Prova a cercare"}</b>${examples.map(value => `<button type="button" data-search-query="${esc(value)}">${esc(value)}</button>`).join("")}</div><div class="globalSearchIndexStats"><span><b>${fmt(catalog?.issues?.length)}</b> albi unici</span><span><b>${fmt(searchItems.filter(item=>item.kind==="edition").length)}</b> edizioni alternative collegate</span><span><b>${fmt(manifest?.characters?.length)}</b> percorsi</span></div></div>`;
  }

  function noResultsMarkup(query){
    return `<div class="globalSearchNoResults"><span>${SEARCH_ICON}</span><h2>Nessun albo trovato</h2><p>“${esc(query)}” non compare negli albi, nei contenuti USA o nei nomi dei percorsi indicizzati.</p><button type="button" data-search-clear>Azzera la ricerca</button></div>`;
  }

  function renderResults(){
    const root = dialog()?.querySelector("[data-global-search-results]");
    const input = dialog()?.querySelector("[data-global-search-input]");
    const summary = dialog()?.querySelector("[data-global-search-summary]");
    if(!root || !input || !catalog) return;
    const query = input.value.trim();
    if(!query){
      root.innerHTML = emptyMarkup();
      summary.textContent = "Catalogo pronto";
      return;
    }
    const results = filteredResults(query);
    summary.textContent = `${results.length}${results.length===RESULT_LIMIT?"+":""} risultati`;
    root.innerHTML = results.length ? `<div class="globalSearchResultList">${results.map(resultMarkup).join("")}</div>` : noResultsMarkup(query);
  }

  function scheduleRender(){
    clearTimeout(renderTimer);
    renderTimer = setTimeout(renderResults,70);
  }

  function ensureDialog(){
    if(dialog()) return dialog();
    const element = document.createElement("dialog");
    element.id = "globalSearchDialog";
    element.className = "globalSearchDialog";
    element.innerHTML = `<div class="globalSearchShell">
      <header class="globalSearchHeader"><div class="globalSearchTitle"><span>Marvel Archive</span><b>Ricerca globale</b></div><button type="button" class="globalSearchClose" data-global-search-close aria-label="Chiudi">×</button></header>
      <div class="globalSearchInputWrap">${SEARCH_ICON}<input type="search" data-global-search-input autocomplete="off" spellcheck="false" placeholder="Cerca albo, testata, numero o contenuto USA…" aria-label="Cerca in tutto Marvel Archive"><kbd>ESC</kbd></div>
      <div class="globalSearchToolbar"><div class="globalSearchFilters" role="group" aria-label="Tipo di risultato"><button type="button" class="active" data-search-filter="all">Tutto</button><button type="button" data-search-filter="issue">Albi nei percorsi</button><button type="button" data-search-filter="edition">Edizioni alternative</button></div><span data-global-search-summary>Preparazione catalogo…</span></div>
      <div class="globalSearchResults" data-global-search-results aria-live="polite"><div class="globalSearchLoading"><i></i><b>Indicizzazione dell'archivio…</b></div></div>
      <footer class="globalSearchFooter"><span><kbd>Ctrl</kbd><kbd>K</kbd> apri</span><span><kbd>Esc</kbd> chiudi</span><span>La ricerca non modifica l'ordine narrativo dei percorsi.</span></footer>
    </div>`;
    document.body.append(element);
    const input = element.querySelector("[data-global-search-input]");
    input.addEventListener("input",scheduleRender);
    element.querySelector("[data-global-search-close]").onclick = () => element.close();
    element.querySelectorAll("[data-search-filter]").forEach(button => button.onclick = () => {
      activeFilter = button.dataset.searchFilter;
      element.querySelectorAll("[data-search-filter]").forEach(item => item.classList.toggle("active",item===button));
      renderResults();
    });
    element.addEventListener("click",event => {
      if(event.target === element){ element.close(); return; }
      const suggestion = event.target.closest("[data-search-query]");
      if(suggestion){ input.value=suggestion.dataset.searchQuery; input.focus(); renderResults(); return; }
      if(event.target.closest("[data-search-clear]")){ input.value=""; input.focus(); renderResults(); return; }
      const pathButton = event.target.closest("[data-search-open-path]");
      if(pathButton){
        rememberQuery(input.value);
        const pathId = pathButton.dataset.searchOpenPath;
        const token = pathButton.dataset.searchToken || "";
        element.close();
        api?.openPath?.(pathId,token);
      }
    });
    element.addEventListener("close",() => document.body.classList.remove("globalSearchOpen"));
    return element;
  }

  async function open(initialQuery=""){
    if(!api) return;
    const element = ensureDialog();
    const input = element.querySelector("[data-global-search-input]");
    if(initialQuery) input.value = initialQuery;
    if(!element.open){
      if(typeof element.showModal === "function") element.showModal();
      else element.setAttribute("open","");
    }
    document.body.classList.add("globalSearchOpen");
    requestAnimationFrame(() => { input.focus(); input.select(); });
    const root = element.querySelector("[data-global-search-results]");
    if(!catalog) root.innerHTML = '<div class="globalSearchLoading"><i></i><b>Indicizzazione dell\'archivio…</b></div>';
    try{
      await loadIndex();
      renderResults();
    }catch(error){
      console.error("Ricerca globale non disponibile",error);
      root.innerHTML = `<div class="globalSearchNoResults"><span>!</span><h2>Catalogo non disponibile</h2><p>${esc(error.message)}</p></div>`;
    }
  }

  function refresh(){ if(dialog()?.open && catalog) renderResults(); }

  function init(nextApi){
    api = nextApi;
    manifest = nextApi?.manifest || null;
    pathById = new Map((manifest?.characters || []).map(path => [path.id,path]));
    if(initialized) return;
    initialized = true;
    ensureDialog();
    document.addEventListener("click",event => {
      if(event.target.closest("[data-global-search]")) open();
    });
    document.addEventListener("keydown",event => {
      const target = event.target;
      const editing = target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
      if((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k"){
        event.preventDefault();
        open();
      }else if(event.key === "/" && !editing && !event.ctrlKey && !event.metaKey && !event.altKey){
        event.preventDefault();
        open();
      }
    });
  }

  window.MarvelGlobalSearch = {init,open,refresh};
})();
