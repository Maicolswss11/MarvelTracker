#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise SystemExit(f"Anchor non trovato: {label}")
    return source.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Build a lightweight artwork index alongside the global issue catalog.
# ---------------------------------------------------------------------------
build_path = ROOT / "scripts" / "build_catalog.py"
build = build_path.read_text(encoding="utf-8")
if "def write_ui_art(" not in build:
    artwork_helpers = r'''

def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("–", "-").split())


def choose_path_cover(path_meta: dict[str, Any], issues: list[dict[str, Any]]) -> str | None:
    path_id = path_meta["id"]
    candidates = [
        row for row in issues
        if path_id in row.get("paths", []) and row.get("cover") and not row.get("future")
    ]
    if not candidates:
        return None

    start_name = _norm(str(path_meta.get("start", "")).split(" — ", 1)[0])
    if start_name:
        for row in candidates:
            issue_name = _norm(row.get("name", ""))
            if issue_name == start_name or start_name in issue_name or issue_name in start_name:
                return str(row["cover"])
    return str(candidates[0]["cover"])


def write_ui_art(manifest: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path_art: dict[str, str] = {}
    for path_meta in manifest.get("characters", []):
        cover = choose_path_cover(path_meta, issues)
        if cover:
            path_art[path_meta["id"]] = cover

    preferred_hub_paths = {
        "main": ["spiderman", "avengers", "xmen", "fantastic-four"],
        "ultimate-classic": ["ultimate-spiderman-classic", "ultimate-xmen", "ultimates", "ultimate-fantastic-four"],
        "ultimate-new": ["ultimate-new-spiderman", "ultimate-new-black-panther", "ultimate-new-xmen", "ultimate-new-ultimates", "ultimate-new-wolverine"],
        "avengers": ["ironman", "thor", "cap", "hulk"],
        "xmen": ["xmen"],
        "spider": ["spiderman"],
        "fantastic-four": ["fantastic-four"],
        "mystic": ["scarletwitch"],
    }

    hubs_manifest = read_json(DATA / "hubs.json")
    hub_art: dict[str, list[str]] = {}
    for hub in hubs_manifest.get("hubs", []):
        ids = list(preferred_hub_paths.get(hub["id"], []))
        if not ids:
            for group in hub.get("groups", []):
                ids.extend(group.get("paths", []))
            ids.extend(
                path_meta["id"]
                for path_meta in manifest.get("characters", [])
                if hub["id"] in path_meta.get("hubs", [])
            )
        covers: list[str] = []
        for path_id in ids:
            cover = path_art.get(path_id)
            if cover and cover not in covers:
                covers.append(cover)
            if len(covers) >= 4:
                break
        if covers:
            hub_art[hub["id"]] = covers

    payload = {
        "version": 1,
        "manifestVersion": manifest.get("version"),
        "paths": path_art,
        "hubs": hub_art,
    }
    (DATA / "ui-art.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
'''
    build = replace_once(build, "\ndef main() -> None:\n", artwork_helpers + "\n\ndef main() -> None:\n", "catalog artwork helpers")
    build = replace_once(
        build,
        '    print(f"Catalogo globale: {len(issues)} albi fisici unici")',
        '    write_ui_art(manifest, issues)\n    print(f"Catalogo globale: {len(issues)} albi fisici unici")',
        "catalog artwork output",
    )
    build_path.write_text(build, encoding="utf-8")


# ---------------------------------------------------------------------------
# Hub UI: real editorial artwork for paths and photographic hub cards.
# ---------------------------------------------------------------------------
hub_path = ROOT / "js" / "hub-ui.js"
hub = hub_path.read_text(encoding="utf-8")

if "let uiArt =" not in hub:
    hub = replace_once(
        hub,
        "let hubManifest = null;\nlet pathManifest = null;\nlet activeHubId = null;",
        "let hubManifest = null;\nlet pathManifest = null;\nlet uiArt = {paths:{},hubs:{}};\nlet activeHubId = null;",
        "ui art state",
    )

    art_functions = r'''
function pathLogoUrl(path){
  const logo = path?.logo || "";
  if(!logo) return "";
  const separator = logo.includes("?") ? "&" : "?";
  return `${logo}${separator}v=${encodeURIComponent(pathManifest?.version||1)}`;
}
function pathArtworkMarkup(path){
  const cover = uiArt?.paths?.[path?.id] || "";
  const fallback = pathLogoUrl(path);
  return `${cover?`<img class="pathArtPrimary" loading="lazy" src="${esc(cover)}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">`:""}${fallback?`<img class="pathArtFallback" loading="lazy" src="${esc(fallback)}" alt="">`:""}`;
}
function hubArtworkUrls(hub){
  return [...new Set(uiArt?.hubs?.[hub?.id] || [])].filter(Boolean).slice(0,4);
}
function hubArtworkMarkup(hub){
  const covers = hubArtworkUrls(hub);
  if(!covers.length) return "";
  return `<span class="hubCardArt" aria-hidden="true">${covers.map(src=>`<img loading="lazy" src="${esc(src)}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">`).join("")}</span><span class="hubCardShade" aria-hidden="true"></span>`;
}
'''
    anchor = 'function pathHubIds(path){ return Array.isArray(path?.hubs) ? path.hubs : path?.primaryHub ? [path.primaryHub] : []; }\n'
    hub = replace_once(hub, anchor, anchor + art_functions, "artwork helpers")

    old_hub_card = '''function hubCard(hub,{compact=false}={}){
  const stats = hubStats(hub);
  const coming = hub.status === "coming";
  const label = hub.type === "universe" ? "Universo" : hub.type === "event-index" ? "Eventi" : "Famiglia";
  return `<button type="button" class="hubCard ${compact?"compact":""} ${coming?"coming":""}" style="--hub-accent:${esc(hub.accent||"#ed1d24")}" data-open-hub="${esc(hub.id)}">
    <span class="hubCardGlow"></span>
    <span class="hubCardTop"><span class="hubType">${esc(label)}</span>${coming?'<span class="hubStatus">In preparazione</span>':`<span class="hubStatus live">${stats.paths.length} percorsi</span>`}</span>
    <span class="hubCardBody"><b>${esc(hub.name)}</b><span>${esc(hub.subtitle)}</span></span>
    <span class="hubCardBottom">${coming?"Struttura pronta":`${stats.total.toLocaleString("it-IT")} tappe mappate`}<span aria-hidden="true">→</span></span>
  </button>`;
}'''
    new_hub_card = '''function hubCard(hub,{compact=false}={}){
  const stats = hubStats(hub);
  const coming = hub.status === "coming";
  const label = hub.type === "universe" ? "Universo" : hub.type === "event-index" ? "Eventi" : "Famiglia";
  const artwork = hubArtworkMarkup(hub);
  return `<button type="button" class="hubCard ${compact?"compact":""} ${coming?"coming":""} ${artwork?"withArt":""}" style="--hub-accent:${esc(hub.accent||"#ed1d24")}" data-open-hub="${esc(hub.id)}">
    ${artwork}<span class="hubCardGlow"></span>
    <span class="hubCardTop"><span class="hubType">${esc(label)}</span>${coming?'<span class="hubStatus">In preparazione</span>':`<span class="hubStatus live">${stats.paths.length} percorsi</span>`}</span>
    <span class="hubCardBody"><b>${esc(hub.name)}</b><span>${esc(hub.subtitle)}</span></span>
    <span class="hubCardBottom">${coming?"Struttura pronta":`${stats.total.toLocaleString("it-IT")} tappe mappate`}<span aria-hidden="true">→</span></span>
  </button>`;
}'''
    hub = replace_once(hub, old_hub_card, new_hub_card, "hub card artwork")

    hub = replace_once(
        hub,
        '<span class="hubPathLogo"><img src="${esc(path.logo)}?v=${encodeURIComponent(pathManifest.version||1)}" alt="" onerror="this.style.display=\'none\'"></span>',
        '<span class="hubPathLogo">${pathArtworkMarkup(path)}</span>',
        "path card artwork",
    )

    old_sidebar = 'function sidebarPathButton(path,currentId,hubId){\n  return `<button type="button" class="hubSidePath ${path.id===currentId?"active":""}" style="--path-accent:${esc(path.accent)}" data-side-path="${esc(path.id)}" data-side-hub="${esc(hubId)}"><img src="${esc(path.logo)}?v=${encodeURIComponent(pathManifest.version||1)}" alt="" onerror="this.style.visibility=\'hidden\'"><span><b>${esc(path.name)}</b><small>${esc(path.subtitle)}</small></span></button>`;\n}'
    new_sidebar = 'function sidebarPathButton(path,currentId,hubId){\n  return `<button type="button" class="hubSidePath ${path.id===currentId?"active":""}" style="--path-accent:${esc(path.accent)}" data-side-path="${esc(path.id)}" data-side-hub="${esc(hubId)}"><span class="hubSideArtwork">${pathArtworkMarkup(path)}</span><span><b>${esc(path.name)}</b><small>${esc(path.subtitle)}</small></span></button>`;\n}'
    hub = replace_once(hub, old_sidebar, new_sidebar, "sidebar artwork")

    old_init = '''    const [hubResponse,pathResponse] = await Promise.all([
      fetch("data/hubs.json",{cache:"no-cache"}),
      fetch("data/characters.json",{cache:"no-cache"})
    ]);
    if(!hubResponse.ok || !pathResponse.ok) throw new Error("Impossibile caricare la tassonomia Marvel");
    hubManifest = await hubResponse.json();
    pathManifest = await pathResponse.json();'''
    new_init = '''    const [hubResponse,pathResponse,artResponse] = await Promise.all([
      fetch("data/hubs.json",{cache:"no-cache"}),
      fetch("data/characters.json",{cache:"no-cache"}),
      fetch("data/ui-art.json",{cache:"no-cache"}).catch(()=>null)
    ]);
    if(!hubResponse.ok || !pathResponse.ok) throw new Error("Impossibile caricare la tassonomia Marvel");
    hubManifest = await hubResponse.json();
    pathManifest = await pathResponse.json();
    if(artResponse?.ok) uiArt = await artResponse.json();'''
    hub = replace_once(hub, old_init, new_init, "ui art fetch")
    hub_path.write_text(hub, encoding="utf-8")


# ---------------------------------------------------------------------------
# Visual CSS overrides.
# ---------------------------------------------------------------------------
hub_css_path = ROOT / "css" / "hub-ui.css"
hub_css = hub_css_path.read_text(encoding="utf-8")
if "Editorial artwork v1" not in hub_css:
    hub_css += r'''

/* Editorial artwork v1 */
.hubCard.withArt{background:#080d13;isolation:isolate}
.hubCardArt{position:absolute;inset:0;z-index:0;display:flex;overflow:hidden;opacity:.50;pointer-events:none}
.hubCardArt img{min-width:0;flex:1 1 0;width:0;height:100%;object-fit:cover;object-position:center 18%;filter:saturate(.92) contrast(1.08)}
.hubCardShade{position:absolute;inset:0;z-index:1;pointer-events:none;background:linear-gradient(90deg,rgba(5,9,14,.94) 0%,rgba(5,9,14,.72) 48%,rgba(5,9,14,.48) 100%),linear-gradient(180deg,rgba(4,8,12,.12),rgba(4,8,12,.82))}
.hubCard.withArt .hubCardGlow{z-index:2;opacity:.18}
.hubCard.withArt .hubCardTop,.hubCard.withArt .hubCardBody,.hubCard.withArt .hubCardBottom{z-index:3}
.hubCard.withArt .hubCardBody b{color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.82)}
.hubCard.withArt .hubCardBody span{color:#b7c2ce;text-shadow:0 2px 12px rgba(0,0,0,.88)}
.hubCard.withArt .hubCardBottom{color:#aeb9c5;border-top-color:rgba(255,255,255,.18);text-shadow:0 1px 8px rgba(0,0,0,.9)}
.hubCard.withArt .hubType{color:#c2ccd6;text-shadow:0 1px 8px rgba(0,0,0,.9)}
.hubCard.withArt .hubStatus{backdrop-filter:blur(7px);background:rgba(7,12,18,.58)}

.hubPathLogo{position:relative;isolation:isolate}
.hubPathLogo img{position:absolute;inset:0;width:100%;height:100%;max-width:none;max-height:none}
.hubPathLogo .pathArtFallback{z-index:1;object-fit:contain;padding:6px;background:#080d13}
.hubPathLogo .pathArtPrimary{z-index:2;object-fit:cover;padding:0;background:#080d13}
.hubPathCard:has(.pathArtPrimary) .hubPathLogo{box-shadow:0 8px 18px rgba(0,0,0,.28)}

.hubSidePath{grid-template-columns:34px minmax(0,1fr)}
.hubSideArtwork{position:relative;width:34px;height:34px;border-radius:9px;overflow:hidden;border:1px solid color-mix(in srgb,var(--path-accent) 32%,#263443);background:#080d13;isolation:isolate}
.hubSideArtwork img{position:absolute;inset:0;width:100%;height:100%}
.hubSideArtwork .pathArtFallback{z-index:1;object-fit:contain;padding:4px;background:#080d13}
.hubSideArtwork .pathArtPrimary{z-index:2;object-fit:cover;padding:0}
@media(max-width:520px){.hubCardArt{opacity:.46}.hubCardShade{background:linear-gradient(90deg,rgba(5,9,14,.95),rgba(5,9,14,.63)),linear-gradient(180deg,rgba(4,8,12,.15),rgba(4,8,12,.84))}}
'''
    hub_css_path.write_text(hub_css, encoding="utf-8")

app_css_path = ROOT / "css" / "app.css"
app_css = app_css_path.read_text(encoding="utf-8")
if "Mobile collection control fix v1" not in app_css:
    app_css += r'''

/* Mobile collection control fix v1 */
#homeProfileBtn{display:inline-flex;align-items:center;justify-content:center;gap:7px}
#homeProfileBtn .homeTopActionIcon{width:15px;height:15px;flex:none}
@media(max-width:720px){
  #homeProfileBtn{width:42px;height:42px;padding:0;border-radius:12px}
  #homeProfileBtn .homeTopActionLabel{display:none}
  #homeProfileBtn .homeTopActionIcon{width:18px;height:18px}
}
'''
    app_css_path.write_text(app_css, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML: visible collection glyph on mobile + cache bumps for changed assets.
# ---------------------------------------------------------------------------
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
old_profile = '<button type="button" class="homeTopAction" id="homeProfileBtn">Collezione</button>'
new_profile = '<button type="button" class="homeTopAction" id="homeProfileBtn" aria-label="Apri la collezione"><svg class="homeTopActionIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8v12h16V8"/><path d="M2.5 4h19v4h-19z"/><path d="M9 12h6"/></svg><span class="homeTopActionLabel">Collezione</span></button>'
if old_profile in index:
    index = index.replace(old_profile, new_profile, 1)
elif 'id="homeProfileBtn"' not in index:
    raise SystemExit("homeProfileBtn non trovato")

index = index.replace('css/app.css?v=8', 'css/app.css?v=9')
index = index.replace('css/hub-ui.css?v=6', 'css/hub-ui.css?v=7')
index = index.replace('js/hub-ui.js?v=6', 'js/hub-ui.js?v=7')
index = index.replace('assets/brand/marvel.png?v=2', 'assets/brand/marvel.png?v=3')
index_path.write_text(index, encoding="utf-8")

print("Visual artwork integration applied")
