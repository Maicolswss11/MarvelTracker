(() => {
  "use strict";

  const CATEGORIES = [
    {id:"reading",label:"Lettura",eyebrow:"Cronologie",description:"Dalla prima pagina alla conoscenza completa dell’archivio.",accent:"#57c7ff",mark:"R",art:"read-1"},
    {id:"collection",label:"Collezione",eyebrow:"Archivio",description:"Copie recuperate, formati e copertura del catalogo globale.",accent:"#ffb637",mark:"C",art:"owned-1"},
    {id:"journeys",label:"Percorsi",eyebrow:"Esplorazione",description:"Universi, personaggi ed eventi iniziati e portati a termine.",accent:"#54dfa5",mark:"P",art:"started-1"},
    {id:"legends",label:"Leggende",eyebrow:"Sfide speciali",description:"Imprese dedicate agli eroi e alle grandi saghe Marvel.",accent:"#ef647f",mark:"L",art:"legend-big-three"},
    {id:"organizer",label:"Organizzazione",eyebrow:"Metodo",description:"Wishlist e liste personali per dominare anche l’arretrato.",accent:"#a98aff",mark:"O",art:"lists-1"},
    {id:"identity",label:"Identità",eyebrow:"Profilo",description:"Personalizzazione, cloud e anzianità nel Marvel Archive.",accent:"#f079d0",mark:"I",art:"identity-complete"},
  ];

  const RARITIES = {
    common:{label:"Comune",xp:40},
    rare:{label:"Raro",xp:90},
    epic:{label:"Epico",xp:170},
    legendary:{label:"Leggendario",xp:300},
    mythic:{label:"Mitico",xp:500},
  };

  const RANK_NAMES = [
    "Recluta dell’Archivio",
    "Lettore iniziato",
    "Custode delle storie",
    "Agente S.H.I.E.L.D.",
    "Collezionista esperto",
    "Vendicatore",
    "Archivista supremo",
    "Esploratore del Multiverso",
    "Leggenda Marvel",
    "Custode dell’Universo",
  ];

  const clamp = (value,min,max) => Math.max(min,Math.min(max,Number(value)||0));
  const asCount = value => Math.max(0,Math.floor(Number(value)||0));
  const rarityForStep = (index,total) => {
    const ratio=(index+1)/Math.max(1,total);
    if(ratio<=.34)return "common";
    if(ratio<=.62)return "rare";
    if(ratio<=.84)return "epic";
    if(ratio<1)return "legendary";
    return "mythic";
  };

  function makeAchievement({id,category,title,detail,icon,art=null,value=0,goal=1,unit="",rarity="common",xp=null,hidden=false,pathId=null,done=null}){
    const target=Math.max(1,Number(goal)||1);
    const current=Math.max(0,Number(value)||0);
    const unlocked=done===null ? current>=target : !!done;
    return {
      id,category,title,detail,icon,art:art||id,rarity,
      rarityLabel:RARITIES[rarity]?.label||RARITIES.common.label,
      xp:Number(xp)||RARITIES[rarity]?.xp||RARITIES.common.xp,
      hidden:!!hidden,pathId,
      value:current,goal:target,unit,done:unlocked,
      progress:unlocked?100:clamp(current/target*100,0,99.5),
      valueLabel:`${Math.min(current,target).toLocaleString("it-IT")}${unit} / ${target.toLocaleString("it-IT")}${unit}`,
    };
  }

  function addSeries(target,{category,prefix,icon,value,steps,unit=""}){
    steps.forEach((step,index)=>target.push(makeAchievement({
      id:`${prefix}-${step.goal}`,
      category,
      icon,
      art:step.art||`${prefix}-${step.goal}`,
      value,
      goal:step.goal,
      unit,
      title:step.title,
      detail:step.detail,
      rarity:step.rarity||rarityForStep(index,steps.length),
      xp:step.xp,
      hidden:step.hidden,
    })));
  }

  function build(snapshot={}){
    const achievements=[];
    const paths=Array.isArray(snapshot.paths)?snapshot.paths:[];
    const byPath=new Map(paths.map(path=>[path.id,path]));
    const completed=paths.filter(path=>path.done);
    const started=paths.filter(path=>path.started);
    const events=paths.filter(path=>path.type==="event");
    const characters=paths.filter(path=>path.type==="character"||path.type==="team");
    const universes=paths.filter(path=>path.type==="universe");
    const completedEvents=events.filter(path=>path.done);
    const completedCharacters=characters.filter(path=>path.done);
    const completedUniverses=universes.filter(path=>path.done);
    const availableTypes=new Set(paths.map(path=>path.type).filter(Boolean));
    const startedTypes=new Set(started.map(path=>path.type).filter(Boolean));

    addSeries(achievements,{category:"reading",prefix:"read",icon:"▤",value:asCount(snapshot.read),steps:[
      {goal:1,title:"Prima pagina",detail:"Segna il primo albo come letto."},
      {goal:10,title:"Dieci numeri dopo",detail:"Leggi 10 albi unici."},
      {goal:25,title:"Lettore in missione",detail:"Raggiungi 25 albi letti."},
      {goal:50,title:"Una pila rispettabile",detail:"Raggiungi 50 albi letti."},
      {goal:100,title:"Centenario",detail:"Leggi 100 albi unici."},
      {goal:250,title:"Divoratore di saghe",detail:"Supera 250 letture."},
      {goal:500,title:"Mezzo migliaio",detail:"Conquista 500 albi letti."},
      {goal:1000,title:"Mille mondi",detail:"Raggiungi 1.000 albi letti."},
      {goal:2500,title:"Memoria vivente",detail:"Leggi 2.500 albi unici.",hidden:true},
    ]});
    addSeries(achievements,{category:"reading",prefix:"reading-map",icon:"◫",value:asCount(snapshot.readingCoverage),unit:"%",steps:[
      {goal:10,title:"Prime coordinate",detail:"Completa il 10% delle tappe mappate."},
      {goal:25,title:"Un quarto dell’universo",detail:"Completa il 25% delle tappe mappate."},
      {goal:50,title:"A metà del viaggio",detail:"Completa metà delle tappe mappate."},
      {goal:100,title:"Tutto è storia",detail:"Completa ogni tappa mappata.",hidden:true},
    ]});

    addSeries(achievements,{category:"collection",prefix:"owned",icon:"▣",value:asCount(snapshot.owned),steps:[
      {goal:1,title:"Il primo recupero",detail:"Aggiungi la prima pubblicazione alla collezione."},
      {goal:10,title:"Scaffale inaugurato",detail:"Recupera 10 pubblicazioni."},
      {goal:25,title:"Collezionista",detail:"Recupera 25 pubblicazioni."},
      {goal:50,title:"Archivio in crescita",detail:"Recupera 50 pubblicazioni."},
      {goal:100,title:"Cento copertine",detail:"Recupera 100 pubblicazioni."},
      {goal:250,title:"Stanza delle meraviglie",detail:"Raggiungi 250 pubblicazioni."},
      {goal:500,title:"Archivio monumentale",detail:"Raggiungi 500 pubblicazioni."},
      {goal:1000,title:"Biblioteca Marvel",detail:"Raggiungi 1.000 pubblicazioni."},
    ]});
    addSeries(achievements,{category:"collection",prefix:"physical",icon:"■",value:asCount(snapshot.physical),steps:[
      {goal:1,title:"Carta e inchiostro",detail:"Registra la prima copia fisica."},
      {goal:25,title:"Scaffale reale",detail:"Possiedi 25 copie fisiche."},
      {goal:100,title:"Parete di volumi",detail:"Possiedi 100 copie fisiche."},
      {goal:250,title:"Sala dell’archivio",detail:"Possiedi 250 copie fisiche."},
    ]});
    addSeries(achievements,{category:"collection",prefix:"digital",icon:"◇",value:asCount(snapshot.digital),steps:[
      {goal:1,title:"Archivio digitale",detail:"Registra la prima copia digitale."},
      {goal:25,title:"Nuvola di storie",detail:"Possiedi 25 copie digitali."},
      {goal:100,title:"Biblioteca tascabile",detail:"Possiedi 100 copie digitali."},
      {goal:250,title:"Database vivente",detail:"Possiedi 250 copie digitali."},
    ]});
    addSeries(achievements,{category:"collection",prefix:"dual",icon:"◈",value:asCount(snapshot.both),steps:[
      {goal:1,title:"Doppia custodia",detail:"Possiedi lo stesso albo in fisico e digitale."},
      {goal:10,title:"Ridondanza strategica",detail:"Conserva 10 albi in entrambi i formati."},
      {goal:50,title:"Backup del Multiverso",detail:"Conserva 50 albi in entrambi i formati."},
      {goal:100,title:"Archivio indistruttibile",detail:"Conserva 100 albi in entrambi i formati."},
    ]});
    addSeries(achievements,{category:"collection",prefix:"catalog",icon:"▦",value:asCount(snapshot.collectionCoverage),unit:"%",steps:[
      {goal:10,title:"Catalogo sotto controllo",detail:"Recupera il 10% del catalogo globale."},
      {goal:25,title:"Un quarto in cassaforte",detail:"Recupera il 25% del catalogo globale."},
      {goal:50,title:"Metà dell’archivio",detail:"Recupera metà del catalogo globale."},
      {goal:100,title:"Collezione assoluta",detail:"Recupera l’intero catalogo globale.",hidden:true},
    ]});

    addSeries(achievements,{category:"journeys",prefix:"started",icon:"→",value:started.length,steps:[
      {goal:1,title:"Il viaggio comincia",detail:"Inizia il primo percorso."},
      {goal:5,title:"Bivi narrativi",detail:"Inizia 5 percorsi diversi."},
      {goal:10,title:"Cartografo",detail:"Inizia 10 percorsi diversi."},
      {goal:25,title:"Esploratore seriale",detail:"Inizia 25 percorsi diversi."},
      {goal:50,title:"Ovunque contemporaneamente",detail:"Inizia 50 percorsi diversi."},
    ]});
    addSeries(achievements,{category:"journeys",prefix:"completed",icon:"✓",value:completed.length,steps:[
      {goal:1,title:"Primo percorso chiuso",detail:"Completa il primo percorso."},
      {goal:3,title:"Tre finali",detail:"Completa 3 percorsi."},
      {goal:5,title:"Cinque su cinque",detail:"Completa 5 percorsi."},
      {goal:10,title:"Decatleta narrativo",detail:"Completa 10 percorsi."},
      {goal:25,title:"Veterano delle cronologie",detail:"Completa 25 percorsi."},
      {goal:Math.max(1,paths.length),title:"Nessuna storia lasciata indietro",detail:"Completa ogni percorso disponibile.",hidden:true,rarity:"mythic",art:"completed-all"},
    ]});
    addSeries(achievements,{category:"journeys",prefix:"events",icon:"⚡",value:completedEvents.length,steps:[
      {goal:1,title:"Testimone dell’evento",detail:"Completa il primo grande evento."},
      {goal:3,title:"Dopo la crisi",detail:"Completa 3 eventi."},
      {goal:5,title:"Epicentro",detail:"Completa 5 eventi."},
      {goal:10,title:"Cronista delle catastrofi",detail:"Completa 10 eventi."},
      {goal:Math.max(1,events.length),title:"La storia segreta degli eventi",detail:"Completa tutti gli eventi disponibili.",hidden:true,rarity:"mythic",art:"events-all"},
    ]});
    addSeries(achievements,{category:"journeys",prefix:"characters",icon:"◆",value:completedCharacters.length,steps:[
      {goal:1,title:"Biografo dell’eroe",detail:"Completa un percorso personaggio o squadra."},
      {goal:3,title:"Tre leggende",detail:"Completa 3 percorsi di eroi o squadre."},
      {goal:5,title:"Album degli eroi",detail:"Completa 5 percorsi di eroi o squadre."},
      {goal:10,title:"Enciclopedia vivente",detail:"Completa 10 percorsi di eroi o squadre."},
      {goal:Math.max(1,characters.length),title:"Ogni eroe, ogni storia",detail:"Completa tutti i percorsi di eroi e squadre.",hidden:true,rarity:"mythic",art:"characters-all"},
    ]});
    addSeries(achievements,{category:"journeys",prefix:"universes",icon:"∞",value:completedUniverses.length,steps:[
      {goal:1,title:"Un universo intero",detail:"Completa un percorso universo."},
      {goal:Math.max(1,universes.length),title:"Multiversale",detail:"Completa tutti i percorsi universo.",hidden:true,rarity:"mythic",art:"universes-all"},
    ]});
    achievements.push(makeAchievement({id:"journeys-every-kind",category:"journeys",title:"Ogni tipo di storia",detail:"Inizia almeno un percorso personaggio, squadra, evento e universo.",icon:"4",value:startedTypes.size,goal:Math.max(1,availableTypes.size),rarity:"legendary"}));

    const pathGoal=(id,title,detail,icon,rarity="legendary")=>{
      const path=byPath.get(id);
      if(!path)return;
      achievements.push(makeAchievement({id:`legend-${id}`,category:"legends",title,detail,icon,value:path.read,goal:path.total,done:path.done,rarity,pathId:id}));
    };
    pathGoal("ironman","Cuore d’acciaio","Completa l’intero percorso di Iron Man.","IM");
    pathGoal("thor","Degno di Mjolnir","Completa l’intero percorso di Thor.","TH");
    pathGoal("cap","Sentinella della libertà","Completa l’intero percorso di Capitan America.","CA");
    pathGoal("hulk","Il più forte che c’è","Completa l’intero percorso di Hulk.","HU");
    pathGoal("spiderman","Da grandi poteri","Completa l’intero percorso di Spider-Man.","SM","mythic");
    pathGoal("avengers","Vendicatori uniti","Completa l’intero percorso dei Vendicatori.","AV","mythic");
    pathGoal("xmen","Figli dell’atomo","Completa l’intero percorso degli X-Men.","XM","mythic");
    pathGoal("fantastic-four","La prima famiglia","Completa l’intero percorso dei Fantastici Quattro.","F4","mythic");
    pathGoal("doctor-strange","Maestro delle arti mistiche","Completa l’intero percorso di Doctor Strange.","DS","legendary");

    const groupGoal=(id,ids,title,detail,icon,{rarity="legendary",hidden=false}={})=>{
      const available=ids.map(pathId=>byPath.get(pathId)).filter(Boolean);
      if(!available.length)return;
      const done=available.filter(path=>path.done).length;
      achievements.push(makeAchievement({id,category:"legends",title,detail,icon,value:done,goal:available.length,rarity,hidden}));
    };
    groupGoal("legend-big-three",["ironman","thor","cap"],"I tre grandi","Completa Iron Man, Thor e Capitan America.","3",{rarity:"mythic"});
    groupGoal("legend-founders",["avengers","ironman","thor","cap","hulk","antman","wasp"],"Vendicatori: assemble","Completa la squadra e i percorsi dei membri fondatori.","A",{rarity:"mythic"});
    groupGoal("legend-mystic",["doctor-strange","scarletwitch"],"Arti mistiche","Completa Doctor Strange e Scarlet Witch.","M",{rarity:"legendary"});
    groupGoal("legend-crisis-era",["house-of-m","civil-war","secret-invasion","siege","fear-itself"],"L’era delle crisi","Attraversa House of M, Civil War, Secret Invasion, Assedio e Fear Itself.","X",{rarity:"mythic",hidden:true});
    groupGoal("legend-ultimate-dual",["ultimate-universe","ultimate-new-universe"],"Due universi Ultimate","Completa Terra-1610 e Terra-6160.","U",{rarity:"mythic",hidden:true});

    addSeries(achievements,{category:"organizer",prefix:"wishlist",icon:"☆",value:asCount(snapshot.wishlist),steps:[
      {goal:1,title:"Nel mirino",detail:"Aggiungi il primo albo alla wishlist."},
      {goal:10,title:"Lista della caccia",detail:"Raggiungi 10 albi in wishlist."},
      {goal:50,title:"Arretrato ambizioso",detail:"Raggiungi 50 albi in wishlist."},
      {goal:100,title:"Caccia infinita",detail:"Raggiungi 100 albi in wishlist."},
    ]});
    addSeries(achievements,{category:"organizer",prefix:"lists",icon:"☰",value:asCount(snapshot.lists),steps:[
      {goal:1,title:"Metodo personale",detail:"Crea la prima lista personale."},
      {goal:3,title:"Tre piani di lettura",detail:"Crea 3 liste personali."},
      {goal:5,title:"Stratega dell’arretrato",detail:"Crea 5 liste personali."},
    ]});
    achievements.push(makeAchievement({id:"organizer-curator",category:"organizer",title:"Curatore",detail:"Raccogli almeno 25 albi in una singola lista.",icon:"25",value:asCount(snapshot.maxListSize),goal:25,rarity:"legendary"}));

    achievements.push(makeAchievement({id:"identity-name",category:"identity",title:"Firma sull’archivio",detail:"Scegli un nome profilo personale.",icon:"ID",value:snapshot.hasDisplayName?1:0,goal:1,rarity:"common"}));
    achievements.push(makeAchievement({id:"identity-bio",category:"identity",title:"La tua origin story",detail:"Scrivi una bio nel profilo.",icon:"…",value:snapshot.hasBio?1:0,goal:1,rarity:"common"}));
    achievements.push(makeAchievement({id:"identity-favorite",category:"identity",title:"Fedeltà dichiarata",detail:"Scegli il tuo percorso preferito.",icon:"♥",value:snapshot.hasFavorite?1:0,goal:1,rarity:"rare"}));
    achievements.push(makeAchievement({id:"identity-avatar",category:"identity",title:"Volto dell’archivio",detail:"Scegli o carica un avatar personale.",icon:"◉",value:snapshot.hasAvatar?1:0,goal:1,rarity:"rare"}));
    achievements.push(makeAchievement({id:"identity-cloud",category:"identity",title:"Oltre il dispositivo",detail:"Collega il profilo al Marvel Archive Cloud.",icon:"☁",value:snapshot.cloudConnected?1:0,goal:1,rarity:"epic"}));
    const identityParts=[snapshot.hasDisplayName,snapshot.hasBio,snapshot.hasFavorite,snapshot.hasAvatar].filter(Boolean).length;
    achievements.push(makeAchievement({id:"identity-complete",category:"identity",title:"Identità completa",detail:"Completa nome, bio, preferito e avatar.",icon:"4",value:identityParts,goal:4,rarity:"legendary"}));
    achievements.push(makeAchievement({id:"identity-veteran",category:"identity",title:"Un anno nell’archivio",detail:"Raggiungi un anno di attività nel Marvel Archive.",icon:"365",value:asCount(snapshot.memberDays),goal:365,rarity:"mythic"}));

    const maxXp=achievements.reduce((sum,item)=>sum+item.xp,0);
    const xp=achievements.filter(item=>item.done).reduce((sum,item)=>sum+item.xp,0);
    const ranks=RANK_NAMES.map((name,index)=>({
      level:index+1,
      name,
      min:index===0?0:Math.round((maxXp*Math.pow(index/(RANK_NAMES.length-1),1.8))/10)*10,
    }));
    let rank=ranks[0];
    for(const candidate of ranks)if(xp>=candidate.min)rank=candidate;
    const nextRank=ranks.find(candidate=>candidate.level===rank.level+1)||null;
    const levelSpan=nextRank?Math.max(1,nextRank.min-rank.min):1;
    const levelProgress=nextRank?clamp((xp-rank.min)/levelSpan*100,0,100):100;
    const unlocked=achievements.filter(item=>item.done);
    const next=achievements.filter(item=>!item.done&&!item.hidden).sort((a,b)=>b.progress-a.progress||a.goal-a.value-(b.goal-b.value)||b.xp-a.xp).slice(0,4);
    const categoryStats=Object.fromEntries(CATEGORIES.map(category=>{
      const items=achievements.filter(item=>item.category===category.id);
      return [category.id,{total:items.length,unlocked:items.filter(item=>item.done).length}];
    }));

    return {
      achievements,
      categories:CATEGORIES,
      categoryStats,
      unlocked:unlocked.length,
      total:achievements.length,
      completion:Math.round(unlocked.length/Math.max(1,achievements.length)*100),
      xp,maxXp,rank,nextRank,levelProgress,next,
    };
  }

  globalThis.MarvelAchievements={build,CATEGORIES,RARITIES,RANK_NAMES};
})();
