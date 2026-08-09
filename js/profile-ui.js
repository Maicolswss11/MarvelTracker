(() => {
  let api = null;
  let catalog = null;
  let catalogPromise = null;
  let activeTab = "overview";
  let activeListId = null;
  let pageLimit = 120;
  let searchTerm = "";
  let formatFilter = "all";
  let authMode = "login";
  let accountMessage = "";
  let accountMessageTone = "";
  let avatarMessage = "";

  const AVATARS = [
    {id:"iron-man",name:"Iron Man",src:"assets/heroes/ironman.png",accent:"#ed1d24"},
    {id:"spider-man",name:"Spider-Man",src:"assets/heroes/spiderman.png",accent:"#f0444b"},
    {id:"captain-america",name:"Capitan America",src:"assets/heroes/capitan-america.png",accent:"#4f9ee8"},
    {id:"thor",name:"Thor",src:"assets/heroes/thor.png",accent:"#75b7ff"},
    {id:"hulk",name:"Hulk",src:"assets/heroes/hulk.png",accent:"#70c74e"},
    {id:"black-panther",name:"Black Panther",src:"assets/heroes/black-panther.svg",accent:"#a88cff"},
    {id:"scarlet-witch",name:"Scarlet Witch",src:"assets/heroes/scarlet-witch.svg",accent:"#ee4779"},
    {id:"doctor-strange",name:"Doctor Strange",src:"assets/heroes/doctor-strange.svg",accent:"#e66a55"},
    {id:"captain-marvel",name:"Captain Marvel",src:"assets/heroes/captain-marvel.svg",accent:"#ffb51b"},
    {id:"black-widow",name:"Black Widow",src:"assets/heroes/black-widow.svg",accent:"#d94d56"},
    {id:"x-men",name:"X-Men",src:"assets/heroes/xmen.svg",accent:"#f3ca44"},
    {id:"fantastic-four",name:"Fantastici Quattro",src:"assets/heroes/fantastic-four.svg",accent:"#63aaf5"},
  ];
  const AVATAR_BY_ID = new Map(AVATARS.map(item => [item.id,item]));

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
    s.userProfile = typeof s.userProfile === "object" && s.userProfile ? s.userProfile : {};
    s.userProfile.displayName = String(s.userProfile.displayName || "").trim().slice(0,40);
    s.userProfile.bio = String(s.userProfile.bio || "").trim().slice(0,180);
    s.userProfile.favoritePath = String(s.userProfile.favoritePath || "").slice(0,80);
    s.userProfile.avatar = typeof s.userProfile.avatar === "object" && s.userProfile.avatar ? s.userProfile.avatar : {kind:"initial"};
    s.userProfile.createdAt ||= new Date().toISOString();
    return s;
  }

  function manifest(){ return api.getManifest(); }

  function avatarDescriptor(avatar,name="Marvel"){
    const initial=(String(name||"M").trim().charAt(0)||"M").toUpperCase();
    if(avatar?.kind==="preset"){
      const preset=AVATAR_BY_ID.get(avatar.id);
      if(preset)return {...preset,kind:"preset",initial};
    }
    if(avatar?.kind==="custom"&&/^data:image\/(?:png|jpe?g|webp);base64,/i.test(String(avatar.dataUrl||"")))return {kind:"custom",name:"Immagine personalizzata",src:avatar.dataUrl,accent:avatar.accent||"#ed1d24",initial};
    return {kind:"initial",name:"Iniziale",src:"",accent:avatar?.accent||"#ed1d24",initial};
  }

  function applyAvatar(element,{name,avatar}={}){
    if(!element)return false;
    const descriptor=avatarDescriptor(avatar,name);
    element.replaceChildren();
    element.style.setProperty("--avatar-accent",descriptor.accent);
    element.dataset.avatarKind=descriptor.kind;
    if(descriptor.src){
      const image=document.createElement("img");
      image.src=descriptor.src;
      image.alt="";
      image.decoding="async";
      image.draggable=false;
      element.append(image);
    }else element.textContent=descriptor.initial;
    return true;
  }

  function account(){ return api.getAccount?.() || {configured:false,user:null,displayName:"Lettore Marvel",syncStatus:"local",phase:"loading"}; }

  function profileName(){
    const local=state().userProfile.displayName.trim();
    const cloud=account();
    return local || (cloud.user ? cloud.displayName : "Profilo locale");
  }

  function favoritePath(){ return (manifest()?.characters || []).find(item => item.id === state().userProfile.favoritePath) || null; }

  function syncCopy(value=account()){
    if(!value.configured)return {title:"Profilo locale",detail:"I dati restano al sicuro su questo dispositivo",tone:"local"};
    if(!value.user)return {title:"Cloud non collegato",detail:"Accedi per sincronizzare su tutti i dispositivi",tone:"local"};
    return {
      synced:{title:"Tutto sincronizzato",detail:"Le ultime modifiche sono già nel cloud",tone:"good"},
      syncing:{title:"Sincronizzazione in corso",detail:"Stiamo salvando le ultime modifiche",tone:"busy"},
      offline:{title:"Modalità offline",detail:"Salveremo le modifiche appena torni online",tone:"warn"},
      error:{title:"Sincronizzazione sospesa",detail:"Riprova manualmente quando vuoi",tone:"bad"},
      ready:{title:"Cloud collegato",detail:"Il profilo è pronto per la sincronizzazione",tone:"good"},
    }[value.syncStatus] || {title:"Cloud collegato",detail:"I progressi sono protetti dal tuo account",tone:"good"};
  }

  function renderHero(){
    if(!api)return;
    const profile=state().userProfile;
    const name=profileName();
    const descriptor=avatarDescriptor(profile.avatar,name);
    const favorite=favoritePath();
    const cloud=syncCopy();
    $("profileView")?.style.setProperty("--profile-accent",descriptor.accent);
    if($("profileHeroName"))$("profileHeroName").textContent=name;
    if($("profileHeroBio"))$("profileHeroBio").textContent=profile.bio || "Costruisci la tua identità Marvel e porta collezione, letture e wishlist sempre con te.";
    if($("profileHeroEyebrow"))$("profileHeroEyebrow").textContent=account().user ? "Archivio personale sincronizzato" : "Il tuo archivio personale";
    if($("profileHeroCloud"))$("profileHeroCloud").textContent=cloud.title;
    if($("profileHeroFavorite"))$("profileHeroFavorite").textContent=favorite ? `Preferito · ${favorite.name}` : "Nessun percorso preferito";
    applyAvatar($("profileHeroAvatarVisual"),{name,avatar:profile.avatar});
  }

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
    state().profileSchema = 2;
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
      tabButton("account","Profilo"),
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
      history.replaceState(null,"",`#/profile/${activeTab}`);
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

  function formatMemberDate(value){
    const date=new Date(value);
    return Number.isNaN(date.getTime()) ? "Da oggi" : `Dal ${new Intl.DateTimeFormat("it-IT",{month:"long",year:"numeric"}).format(date)}`;
  }

  function achievementData(){
    const stats=collectionStats();
    const started=(manifest()?.characters || []).filter(path => Object.values(state().characters?.[path.id]?.issues || {}).some(item => item?.read)).length;
    return [
      {code:"01",title:"Prima pagina",detail:"Segna il primo albo come letto",done:stats.read>=1,value:Math.min(stats.read,1),goal:1},
      {code:"25",title:"Collezionista",detail:"Recupera 25 pubblicazioni",done:stats.owned>=25,value:Math.min(stats.owned,25),goal:25},
      {code:"05",title:"Multiversale",detail:"Inizia 5 percorsi diversi",done:started>=5,value:Math.min(started,5),goal:5},
      {code:"100",title:"Archivista",detail:"Leggi 100 albi unici",done:stats.read>=100,value:Math.min(stats.read,100),goal:100},
    ];
  }

  function accountCloudHtml(){
    const cloud=account();
    const copy=syncCopy(cloud);
    if(cloud.phase==="loading")return `<article class="profileAccountPanel profileCloudPanel"><div class="profilePanelEyebrow">Marvel Archive Cloud</div><div class="profileAccountLoading"><i></i><span>Caricamento del profilo…</span></div></article>`;
    if(!cloud.configured)return `<article class="profileAccountPanel profileCloudPanel"><div class="profilePanelEyebrow">Marvel Archive Cloud</div><div class="profileCloudState local"><span class="profileCloudOrb">L</span><div><h3>Profilo locale attivo</h3><p>I progressi sono salvati sul dispositivo. Il collegamento cloud può essere attivato dalla configurazione del progetto.</p></div></div></article>`;
    if(cloud.user)return `<article class="profileAccountPanel profileCloudPanel">
      <div class="profilePanelHead"><div><div class="profilePanelEyebrow">Marvel Archive Cloud</div><h2>Account collegato</h2></div><span class="profileConnectionPill ${esc(copy.tone)}"><i></i>${esc(copy.title)}</span></div>
      <div class="profileCloudIdentity"><div><b>${esc(profileName())}</b><span>${esc(cloud.user.email || "")}</span></div><small>${formatMemberDate(cloud.user.created_at || state().userProfile.createdAt)}</small></div>
      <div class="profileCloudDescription ${esc(copy.tone)}"><i></i><div><b>${esc(copy.title)}</b><span>${esc(copy.detail)}</span></div></div>
      <div class="profileCloudActions"><button type="button" data-profile-sync>Sincronizza ora</button><button type="button" class="danger" data-profile-signout>Esci dall’account</button></div>
      <p class="profileInlineMessage ${accountMessageTone}" role="status">${esc(accountMessage)}</p>
    </article>`;
    const register=authMode==="register";
    const busy=cloud.phase==="authenticating";
    return `<article class="profileAccountPanel profileCloudPanel profileAuthPanel">
      <div class="profilePanelEyebrow">Marvel Archive Cloud</div><h2>${register?"Crea il tuo account":"Porta l’archivio con te"}</h2><p class="profilePanelIntro">${register?"Crea un profilo per ritrovare avatar, collezione e letture su ogni dispositivo.":"Accedi per sincronizzare automaticamente ogni modifica, anche dopo una sessione offline."}</p>
      <div class="profileAuthTabs" role="tablist"><button type="button" class="${register?"":"active"}" data-auth-mode="login" role="tab" aria-selected="${!register}">Accedi</button><button type="button" class="${register?"active":""}" data-auth-mode="register" role="tab" aria-selected="${register}">Crea account</button></div>
      <form class="profileAuthForm" id="profileAuthForm">
        ${register?'<label>Nome profilo<input name="displayName" autocomplete="name" maxlength="40" required placeholder="Come vuoi essere chiamato"></label>':""}
        <label>Email<input name="email" type="email" autocomplete="email" required placeholder="nome@email.it"></label>
        <label>Password<input name="password" type="password" autocomplete="${register?"new-password":"current-password"}" minlength="8" required placeholder="Almeno 8 caratteri"></label>
        <button type="submit" ${busy?"disabled":""}>${busy?"Connessione in corso…":register?"Crea account":"Accedi e sincronizza"}</button>
        <p class="profileInlineMessage ${accountMessageTone}" role="status">${esc(accountMessage || (cloud.phase==="error"?`Connessione non riuscita: ${cloud.error || "riprova più tardi"}`:""))}</p>
      </form>
    </article>`;
  }

  function accountAchievementsHtml(){
    return achievementData().map(item => `<article class="profileAchievement ${item.done?"unlocked":""}"><span>${item.done?"✓":item.code}</span><div><b>${esc(item.title)}</b><small>${esc(item.detail)}</small><i><em style="width:${Math.round(item.value/item.goal*100)}%"></em></i></div></article>`).join("");
  }

  async function imageToAvatar(file){
    if(!/^image\/(?:png|jpe?g|webp)$/i.test(file?.type || ""))throw new Error("Scegli un’immagine PNG, JPG o WebP.");
    if(file.size>12*1024*1024)throw new Error("L’immagine supera 12 MB. Scegline una più leggera.");
    const url=URL.createObjectURL(file);
    try{
      const image=await new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error("Immagine non leggibile."));img.src=url});
      const size=320;
      const canvas=document.createElement("canvas");
      canvas.width=size;canvas.height=size;
      const context=canvas.getContext("2d",{alpha:false});
      if(!context)throw new Error("Il browser non riesce a elaborare l’immagine.");
      context.fillStyle="#0b1118";context.fillRect(0,0,size,size);
      const scale=Math.max(size/image.naturalWidth,size/image.naturalHeight);
      const width=image.naturalWidth*scale,height=image.naturalHeight*scale;
      context.drawImage(image,(size-width)/2,(size-height)/2,width,height);
      const dataUrl=canvas.toDataURL("image/jpeg",.84);
      if(dataUrl.length>520000)throw new Error("L’immagine elaborata è ancora troppo pesante.");
      return dataUrl;
    }finally{URL.revokeObjectURL(url)}
  }

  function setAvatar(avatar,message){
    const profile=state().userProfile;
    profile.avatar=avatar;
    profile.updatedAt=new Date().toISOString();
    avatarMessage=message;
    save();
    renderHero();
    api.refreshAccountUi?.();
    const descriptor=avatarDescriptor(avatar,profileName());
    if(account().user)void api.updateCloudProfile?.({displayName:profileName(),avatarColor:descriptor.accent}).catch(()=>{});
    void renderAccount();
  }

  function chooseCustomAvatar(){
    const input=document.createElement("input");
    input.type="file";
    input.accept="image/png,image/jpeg,image/webp";
    input.addEventListener("change",async()=>{
      const file=input.files?.[0];
      if(!file)return;
      avatarMessage="Preparazione dell’immagine…";
      void renderAccount();
      try{
        const dataUrl=await imageToAvatar(file);
        setAvatar({kind:"custom",dataUrl,accent:"#ed1d24"},"Immagine personalizzata salvata.");
      }catch(error){avatarMessage=error.message;void renderAccount()}
    },{once:true});
    input.click();
  }

  function chooseBackup(){
    const input=document.createElement("input");
    input.type="file";
    input.accept="application/json,.json";
    input.addEventListener("change",async()=>{
      const file=input.files?.[0];
      if(!file)return;
      try{await api.importState(file);accountMessage="Backup importato correttamente.";accountMessageTone="success";await render()}
      catch(error){accountMessage=error.message;accountMessageTone="error";void renderAccount()}
    },{once:true});
    input.click();
  }

  async function saveIdentity(form){
    const data=new FormData(form);
    const displayName=String(data.get("displayName")||"").trim().slice(0,40);
    const bio=String(data.get("bio")||"").trim().slice(0,180);
    const favorite=String(data.get("favoritePath")||"");
    if(displayName.length<2){accountMessage="Il nome deve contenere almeno 2 caratteri.";accountMessageTone="error";void renderAccount();return}
    const profile=state().userProfile;
    profile.displayName=displayName;
    profile.bio=bio;
    profile.favoritePath=(manifest()?.characters || []).some(item=>item.id===favorite)?favorite:"";
    profile.updatedAt=new Date().toISOString();
    save();
    renderHero();
    accountMessage="Profilo aggiornato.";accountMessageTone="success";
    try{
      if(account().user){
        const descriptor=avatarDescriptor(profile.avatar,displayName);
        await api.updateCloudProfile?.({displayName,avatarColor:descriptor.accent});
      }
    }catch(error){accountMessage=`Salvato in locale. Cloud: ${error.message}`;accountMessageTone="error"}
    api.refreshAccountUi?.();
    void renderAccount();
  }

  async function renderAccount(){
    if(!api||$("profileView")?.hidden||activeTab!=="account")return;
    const profile=state().userProfile;
    const name=profileName();
    const descriptor=avatarDescriptor(profile.avatar,name);
    const stats=collectionStats();
    const readPaths=(manifest()?.characters || []).filter(path => Object.values(state().characters?.[path.id]?.issues || {}).some(item=>item?.read)).length;
    $("profileToolbar").innerHTML="";
    $("profileBody").innerHTML=`<section class="profileAccountPage">
      <div class="profileAccountMain">
        <article class="profileAccountPanel profileAvatarStudio">
          <div class="profilePanelHead"><div><div class="profilePanelEyebrow">Identità visiva</div><h2>Scegli il tuo eroe</h2></div><span class="profilePanelStep">01</span></div>
          <div class="profileAvatarLead"><span class="profileAvatarPreview" id="profileAvatarPreview">${esc(descriptor.initial)}</span><div><b>${esc(descriptor.name)}</b><span>Il tuo avatar compare nella home, nei percorsi e nel profilo.</span></div></div>
          <div class="profileAvatarGrid" aria-label="Avatar Marvel predefiniti">${AVATARS.map(item=>`<button type="button" class="profileAvatarPreset ${profile.avatar?.kind==="preset"&&profile.avatar.id===item.id?"selected":""}" style="--avatar-accent:${item.accent}" data-avatar-id="${esc(item.id)}" aria-pressed="${profile.avatar?.kind==="preset"&&profile.avatar.id===item.id}"><span><img src="${esc(item.src)}" alt=""></span><small>${esc(item.name)}</small><i>✓</i></button>`).join("")}</div>
          <div class="profileAvatarActions"><button type="button" class="primary" data-custom-avatar>Carica una tua immagine</button><button type="button" data-reset-avatar>Usa l’iniziale</button><span>PNG, JPG o WebP · ritaglio automatico</span></div>
          <p class="profileInlineMessage ${avatarMessage&&/troppo|non |impossibile/i.test(avatarMessage)?"error":"success"}" role="status">${esc(avatarMessage)}</p>
        </article>

        <article class="profileAccountPanel profileIdentityEditor">
          <div class="profilePanelHead"><div><div class="profilePanelEyebrow">Scheda lettore</div><h2>Racconta chi sei</h2></div><span class="profilePanelStep">02</span></div>
          <form id="profileIdentityForm" class="profileIdentityForm">
            <label><span>Nome profilo <small>visibile solo nel tuo archivio</small></span><input name="displayName" value="${esc(name)}" minlength="2" maxlength="40" required></label>
            <label><span>Bio <small><b id="profileBioCount">${profile.bio.length}</b>/180</small></span><textarea name="bio" maxlength="180" rows="4" placeholder="Per esempio: lettore Marvel dal 1998, team X-Men…">${esc(profile.bio)}</textarea></label>
            <label><span>Percorso preferito <small>apparirà in evidenza nel profilo</small></span><select name="favoritePath"><option value="">Nessun preferito</option>${(manifest()?.characters || []).map(path=>`<option value="${esc(path.id)}" ${profile.favoritePath===path.id?"selected":""}>${esc(path.name)}</option>`).join("")}</select></label>
            <div class="profileIdentityFooter"><span>Le modifiche sono salvate subito sul dispositivo${account().user?" e sincronizzate nel cloud":""}.</span><button type="submit">Salva profilo</button></div>
          </form>
        </article>
      </div>

      <aside class="profileAccountSide">
        <article class="profileAccountPanel profileReaderCard">
          <div class="profileReaderTop"><span class="profileReaderAvatar" id="profileReaderAvatar">${esc(descriptor.initial)}</span><div><small>Marvel Archive Reader</small><h2>${esc(name)}</h2><p>${formatMemberDate(account().user?.created_at || profile.createdAt)}</p></div></div>
          <div class="profileReaderNumbers"><span><b>${fmt(stats.read)}</b><small>Letti</small></span><span><b>${fmt(stats.owned)}</b><small>Recuperati</small></span><span><b>${fmt(readPaths)}</b><small>Percorsi</small></span></div>
        </article>
        ${accountCloudHtml()}
        <article class="profileAccountPanel profileAchievements"><div class="profilePanelEyebrow">Traguardi</div><h2>La tua carriera Marvel</h2><div class="profileAchievementGrid">${accountAchievementsHtml()}</div></article>
        <article class="profileAccountPanel profileBackupPanel"><div class="profilePanelEyebrow">Dati & backup</div><h2>Il tuo archivio, sempre tuo</h2><p>Scarica una copia completa o ripristina un backup precedente. Avatar personalizzato e preferenze sono inclusi.</p><div><button type="button" data-export-profile>Esporta backup</button><button type="button" data-import-profile>Importa backup</button></div></article>
      </aside>
    </section>`;

    applyAvatar($("profileAvatarPreview"),{name,avatar:profile.avatar});
    applyAvatar($("profileReaderAvatar"),{name,avatar:profile.avatar});
    $("profileBody").querySelectorAll("[data-avatar-id]").forEach(button=>button.onclick=()=>{const item=AVATAR_BY_ID.get(button.dataset.avatarId);if(item)setAvatar({kind:"preset",id:item.id},`${item.name} è ora il tuo avatar.`)});
    $("profileBody").querySelector("[data-custom-avatar]").onclick=chooseCustomAvatar;
    $("profileBody").querySelector("[data-reset-avatar]").onclick=()=>setAvatar({kind:"initial",accent:"#ed1d24"},"Avatar ripristinato all’iniziale.");
    const identityForm=$("profileIdentityForm");
    identityForm.onsubmit=event=>{event.preventDefault();void saveIdentity(identityForm)};
    const bio=identityForm.elements.bio;
    bio.oninput=()=>{$("profileBioCount").textContent=String(bio.value.length)};
    $("profileBody").querySelectorAll("[data-auth-mode]").forEach(button=>button.onclick=()=>{authMode=button.dataset.authMode;accountMessage="";accountMessageTone="";void renderAccount()});
    const authForm=$("profileAuthForm");
    if(authForm)authForm.onsubmit=async event=>{
      event.preventDefault();
      const data=new FormData(authForm);
      accountMessage="";accountMessageTone="";
      try{
        const result=await api.authenticate({mode:authMode,email:String(data.get("email")||"").trim(),password:String(data.get("password")||""),displayName:String(data.get("displayName")||"").trim()});
        if(result?.confirmationRequired){accountMessage="Account creato. Controlla l’email per confermare l’accesso.";accountMessageTone="success";void renderAccount()}
      }catch(error){accountMessage=error.message;accountMessageTone="error";void renderAccount()}
    };
    $("profileBody").querySelector("[data-profile-sync]")?.addEventListener("click",async event=>{event.currentTarget.disabled=true;accountMessage="Sincronizzazione in corso…";accountMessageTone="";try{await api.syncNow();accountMessage="Sincronizzazione completata.";accountMessageTone="success"}catch(error){accountMessage=error.message;accountMessageTone="error"}void renderAccount()});
    $("profileBody").querySelector("[data-profile-signout]")?.addEventListener("click",async()=>{accountMessage="";try{await api.signOut()}catch(error){accountMessage=error.message;accountMessageTone="error";void renderAccount()}});
    $("profileBody").querySelector("[data-export-profile]").onclick=()=>api.exportState();
    $("profileBody").querySelector("[data-import-profile]").onclick=chooseBackup;
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
    renderHero();
    renderStats();
    renderTabs();
    if(activeTab === "account") await renderAccount();
    else if(activeTab === "overview") renderOverview();
    else if(activeTab === "lists") renderLists();
    else renderItemTab();
    document.dispatchEvent(new CustomEvent("marvel:render",{detail:{view:"profile"}}));
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

  async function show({updateHash=true,animate=true,tab=null}={}){
    if(animate&&window.MarvelMotion?.transition)return window.MarvelMotion.transition(()=>show({updateHash,animate:false,tab}));
    if(!api) return;
    const validTabs=new Set(["account","overview","collection","read","wishlist","lists","catalog"]);
    if(tab&&validTabs.has(tab))activeTab=tab;
    document.body.classList.remove("homeActive","bulkSelectMode");
    document.body.classList.add("profileActive");
    $("homeView").hidden = true;
    $("trackerView").hidden = true;
    $("profileView").hidden = false;
    if(updateHash) history.replaceState(null,"",`#/profile/${activeTab}`);
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
    s.userProfile ??= {avatar:{kind:"initial"},displayName:"",bio:"",favoritePath:"",createdAt:new Date().toISOString()};
    s.profileSchema = 2;

    $("profileHomeBtn").onclick = () => api.showHome();
    $("profileAccountBtn").onclick = () => void show({tab:"account"});
    $("profileHeroAvatarButton").onclick = () => void show({tab:"account"});
    $("profileHeroEdit").onclick = () => void show({tab:"account"});
    $("homeProfileBtn").onclick = () => void show({tab:"overview"});
    $("trackerProfileBtn").onclick = () => void show({tab:"overview"});

    const observer = new MutationObserver(decorateTrackerWishlist);
    observer.observe($("seriesBlocks"),{childList:true,subtree:true});
    decorateTrackerWishlist();
  }

  function accountChanged(){
    if(!api)return;
    renderHero();
    if(document.body.classList.contains("profileActive")&&activeTab==="account")void renderAccount();
  }

  window.MarvelProfile = {init,show,render,decorateTrackerWishlist,accountChanged,applyAvatar,avatarDescriptor};
})();
