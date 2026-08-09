#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "js" / "hub-ui.js"
CSS = ROOT / "css" / "hub-ui.css"

js = JS.read_text(encoding="utf-8")
old_breadcrumb = '<button type="button" data-hub-home>Marvel Archive</button>'
new_breadcrumb = '<button type="button" class="hubHomeLevelsBtn" data-hub-home aria-label="Torna alla home dei livelli">← Home livelli</button>'
if old_breadcrumb not in js and new_breadcrumb not in js:
    raise RuntimeError("Breadcrumb target non trovato in js/hub-ui.js")
js = js.replace(old_breadcrumb, new_breadcrumb)

old_tracker_home = '<button type="button" data-tracker-home>Marvel Archive</button>'
new_tracker_home = '<button type="button" class="hubHomeLevelsBtn" data-tracker-home aria-label="Torna alla home dei livelli">← Home livelli</button>'
if old_tracker_home not in js and new_tracker_home not in js:
    raise RuntimeError("Tracker breadcrumb target non trovato in js/hub-ui.js")
js = js.replace(old_tracker_home, new_tracker_home)

old_explore = 'if(exploreButton) exploreButton.onclick=()=>goToExplorer(null);'
new_explore = 'if(exploreButton) exploreButton.addEventListener("click",()=>goToExplorer(null));'
if old_explore not in js and new_explore not in js:
    raise RuntimeError("homeExplore binding target non trovato in js/hub-ui.js")
js = js.replace(old_explore, new_explore)

JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
marker = "/* Explicit return to the level-based explorer root. */"
block = '''\n\n/* Explicit return to the level-based explorer root. */\n.hubBreadcrumb .hubHomeLevelsBtn,\n.trackerHubBreadcrumb .hubHomeLevelsBtn{\n  display:inline-flex;align-items:center;justify-content:center;gap:6px;\n  min-height:36px;padding:7px 12px;border:1px solid #d8d8e6;border-radius:999px;\n  background:#fff;color:#17182a;font-weight:900;line-height:1;cursor:pointer;\n  box-shadow:0 3px 12px rgba(20,22,42,.08);\n}\n.hubBreadcrumb .hubHomeLevelsBtn:hover,\n.trackerHubBreadcrumb .hubHomeLevelsBtn:hover{\n  color:#d3152e;border-color:#d3152e;background:#fff7f8;\n}\n.hubBreadcrumb .hubHomeLevelsBtn:focus-visible,\n.trackerHubBreadcrumb .hubHomeLevelsBtn:focus-visible{\n  outline:3px solid rgba(211,21,46,.22);outline-offset:2px;\n}\n@media (max-width:640px){\n  .hubBreadcrumb .hubHomeLevelsBtn,\n  .trackerHubBreadcrumb .hubHomeLevelsBtn{min-height:40px;padding:9px 13px;font-size:.86rem;}\n}\n'''
if marker not in css:
    css += block
CSS.write_text(css, encoding="utf-8")

print("Hub navigation: explicit Home livelli buttons + resilient Tutti i percorsi binding — OK")
