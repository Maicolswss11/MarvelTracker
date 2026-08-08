#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise SystemExit(f"Anchor non trovato: {label}")
    return source.replace(old, new, 1)


def patch_app() -> None:
    path = ROOT / "js" / "app.js"
    source = path.read_text(encoding="utf-8")

    source = replace_once(
        source,
        'x ??= {}; x.characters ??= {}; x.collection ??= {};',
        'x ??= {}; x.characters ??= {}; x.collection ??= {}; x.wishlist ??= {}; x.lists ??= {}; x.profileSchema ??= 1;',
        "profile state defaults",
    )
    source = replace_once(
        source,
        'function parseHash(){const p=location.hash.replace(/^#\\/?/,"").split("/").filter(Boolean);if(!p.length||p[0]==="home")return {view:"home",character:null,issue:null};return {view:"character",character:p[0],issue:p[1]||null}}',
        'function parseHash(){const p=location.hash.replace(/^#\\/?/,"").split("/").filter(Boolean);if(!p.length||p[0]==="home")return {view:"home",character:null,issue:null};if(p[0]==="profile")return {view:"profile",character:null,issue:null};return {view:"character",character:p[0],issue:p[1]||null}}',
        "profile hash",
    )
    source = replace_once(
        source,
        'document.body.classList.remove("homeActive");\n  els.homeView.hidden=true;',
        'document.body.classList.remove("homeActive","profileActive");\n  $("profileView") && ($("profileView").hidden=true);\n  els.homeView.hidden=true;',
        "hide profile on character",
    )
    source = replace_once(
        source,
        'function refreshCurrentView(){if(!manifest)return;if(document.body.classList.contains("homeActive")||!currentCharacter)showHome({updateHash:false});else if(currentCharacter.id!==activeCharacter)void switchCharacter(activeCharacter);else renderAll()}',
        'function refreshCurrentView(){if(!manifest)return;if(document.body.classList.contains("profileActive")){void window.MarvelProfile?.render();return}if(document.body.classList.contains("homeActive")||!currentCharacter)showHome({updateHash:false});else if(currentCharacter.id!==activeCharacter)void switchCharacter(activeCharacter);else renderAll()}',
        "refresh profile",
    )
    source = replace_once(
        source,
        'document.body.classList.add("homeActive");\n  document.documentElement.style.setProperty("--accent","#ed1d24");',
        'document.body.classList.remove("profileActive");\n  $("profileView") && ($("profileView").hidden=true);\n  document.body.classList.add("homeActive");\n  document.documentElement.style.setProperty("--accent","#ed1d24");',
        "hide profile on home",
    )
    source = replace_once(
        source,
        'window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.view==="home"){showHome({updateHash:false});return}if(els.trackerView.hidden||!currentCharacter||h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=resolveIssueToken(currentCharacter,h.issue);if(i)jumpToIssue(i)}});',
        'window.addEventListener("hashchange",async()=>{if(!manifest)return;const h=parseHash();if(h.view==="home"){showHome({updateHash:false});return}if(h.view==="profile"){await window.MarvelProfile?.show({updateHash:false});return}if(els.trackerView.hidden||!currentCharacter||h.character!==activeCharacter)await switchCharacter(h.character,{updateHash:false,issue:h.issue});else if(h.issue){const i=resolveIssueToken(currentCharacter,h.issue);if(i)jumpToIssue(i)}});',
        "profile hashchange",
    )
    source = replace_once(
        source,
        '(async()=>{try{await loadManifest();const h=parseHash();if(h.view==="home"){showHome({updateHash:false});if(!location.hash)history.replaceState(null,"","#/home")}else await switchCharacter(h.character,{updateHash:false,issue:h.issue});renderAccountUi();void initAccount(handleAccountChange)}catch(e){console.error(e);els.seriesBlocks.innerHTML=`<div class="loading error"><b>Errore di caricamento</b><br>${esc(e.message)}<br><br>Apri il sito tramite GitHub Pages o un server HTTP: i JSON non possono essere caricati correttamente con alcuni browser da file://.</div>`}})();',
        '(async()=>{try{await loadManifest();window.MarvelProfile?.init({getState:()=>state,getManifest:()=>manifest,saveState:()=>saveState(),showHome:()=>showHome(),openCharacter:id=>switchCharacter(id),openAccount:openAccountDialog});const h=parseHash();if(h.view==="home"){showHome({updateHash:false});if(!location.hash)history.replaceState(null,"","#/home")}else if(h.view==="profile")await window.MarvelProfile?.show({updateHash:false});else await switchCharacter(h.character,{updateHash:false,issue:h.issue});renderAccountUi();void initAccount(handleAccountChange)}catch(e){console.error(e);els.seriesBlocks.innerHTML=`<div class="loading error"><b>Errore di caricamento</b><br>${esc(e.message)}<br><br>Apri il sito tramite GitHub Pages o un server HTTP: i JSON non possono essere caricati correttamente con alcuni browser da file://.</div>`}})();',
        "profile bootstrap",
    )
    path.write_text(source, encoding="utf-8")


def patch_index() -> None:
    path = ROOT / "index.html"
    source = path.read_text(encoding="utf-8")

    if 'css/profile.css' not in source:
        source = replace_once(
            source,
            '  <link rel="stylesheet" href="css/collection-formats.css?v=1">',
            '  <link rel="stylesheet" href="css/collection-formats.css?v=1">\n  <link rel="stylesheet" href="css/profile.css?v=1">',
            "profile css",
        )

    if 'id="homeProfileBtn"' not in source:
        source = replace_once(
            source,
            '<div class="homeTopActions"><button type="button" class="homeTopAction" id="homeTopResume">Riprendi percorso</button><button type="button" class="accountButton" id="homeAccountBtn"',
            '<div class="homeTopActions"><button type="button" class="homeTopAction" id="homeTopResume">Riprendi percorso</button><button type="button" class="homeTopAction" id="homeProfileBtn">Collezione</button><button type="button" class="accountButton" id="homeAccountBtn"',
            "home profile button",
        )

    if 'id="trackerProfileBtn"' not in source:
        source = replace_once(
            source,
            '<div class="trackerTopActions"><button class="compactBtn" id="compactBtn">Vista compatta</button><button type="button" class="trackerAccountBtn"',
            '<div class="trackerTopActions"><button class="compactBtn" id="trackerProfileBtn">Collezione</button><button class="compactBtn" id="compactBtn">Vista compatta</button><button type="button" class="trackerAccountBtn"',
            "tracker profile button",
        )

    if 'id="profileView"' not in source:
        profile = '''    <section class="profileView" id="profileView" hidden>
      <header class="profileTopbar">
        <div class="profileTopbarLeft"><button type="button" class="profileHomeButton" id="profileHomeBtn">← Home</button><div class="profileBrand"><b>MARVEL ARCHIVE</b><span>Profilo · Collezione globale</span></div></div>
        <div class="profileTopbarRight"><button type="button" class="profileAccountButton" id="profileAccountBtn"><span class="accountAvatar" data-account-avatar>M</span><span data-account-name>Profilo locale</span></button></div>
      </header>
      <div class="profileContent">
        <section class="profileHero"><div><div class="eyebrow">Il tuo archivio personale</div><h1>Profilo & Collezione</h1><p>Un catalogo unico per copie fisiche, digitali, letture, wishlist e liste personali. Lo stesso albo compare una sola volta anche quando appartiene a più percorsi.</p></div><div class="profileHeroMark">M</div></section>
        <section class="profileStats" id="profileStats"></section>
        <nav class="profileTabs" id="profileTabs" aria-label="Sezioni profilo"></nav>
        <div class="profileToolbar" id="profileToolbar"></div>
        <div id="profileBody"><div class="profileLoading">Preparazione del catalogo personale…</div></div>
      </div>
    </section>
    <div id="trackerView">'''
        source = replace_once(source, '    <div id="trackerView">', profile, "profile view")

    if 'js/profile-ui.js' not in source:
        source = replace_once(
            source,
            '<script type="module" src="js/app.js?v=10"></script>',
            '<script src="js/profile-ui.js?v=1"></script>\n<script type="module" src="js/app.js?v=11"></script>',
            "profile script",
        )
    else:
        source = source.replace('js/app.js?v=10', 'js/app.js?v=11')

    path.write_text(source, encoding="utf-8")


def main() -> None:
    patch_app()
    patch_index()
    print("Integrazione Profilo applicata")


if __name__ == "__main__":
    main()
