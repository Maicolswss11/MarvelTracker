#!/usr/bin/env python3
"""Refine MarvelTracker's reading-order UI and Iron Man Extremis presentation.

This maintenance migration keeps the compressed dataset reproducible while
making the tracker read as a narrative sequence first and an editorial index
second. It is intentionally idempotent.
"""

from __future__ import annotations

import re
from pathlib import Path

from insert_ironman_extremis import SPECIAL_ID, pack_ironman, unpack_ironman

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "js" / "app.js"
CSS = ROOT / "css" / "app.css"

CSS_START = "/* Tracker readability redesign v1 */"
CSS_END = "/* /Tracker readability redesign v1 */"


def patch_ironman_data() -> None:
    character = unpack_ironman()
    special = next(issue for issue in character["issues"] if issue.get("id") == SPECIAL_ID)
    special.update(
        {
            "kind": "chronologyInsert",
            "editorialLabel": "100% Marvel #44",
            "era": "Extremis",
            "eraSub": "The Invincible Iron Man #1–6 · inserto narrativo prima di House of M",
            "instruction": (
                "Da leggere qui: l'intero volume raccoglie The Invincible Iron Man #1-6. "
                "È la tappa narrativa immediatamente successiva a Iron Man e i Vendicatori #84 "
                "e precede Iron Man e i Vendicatori #85 — House of M."
            ),
        }
    )
    pack_ironman(character)


def patch_app_renderer() -> None:
    source = APP.read_text(encoding="utf-8")

    issue_html = r'''function issueHtml(i){
  const st=status(i.id);
  const narrative=i.required!==false&&!i.future&&Number.isInteger(i.seq)?i.seq:null;
  const editorial=String(i.displayNumber??String(i.n).padStart(2,"0"));
  const isInsert=i.kind==="chronologyInsert"||/^100% Marvel #44/.test(i.name||"")||/INSERTO CRONOLOGICO/.test(i.instruction||"");
  const editorialNumeric=Number(editorial);
  const differs=narrative!==null&&(isInsert||(Number.isFinite(editorialNumeric)&&editorialNumeric!==narrative));
  const editorialLabel=i.editorialLabel||(isInsert?`100% Marvel #${editorial}`:`Albo editoriale #${editorial}`);
  const numberHtml=narrative!==null
    ?`<div class="num narrativeNum"><span>Percorso</span><b>#${esc(narrative)}</b>${differs?`<small>${esc(editorialLabel)}</small>`:""}</div>`
    :`<div class="num narrativeNum"><span>${i.future?"Annunciato":"Albo"}</span><b>#${esc(editorial)}</b>${i.required===false?"<small>Facoltativo</small>":""}</div>`;
  const insertBadge=isInsert?'<span class="chronologyBadge">Inserto cronologico</span>':"";
  return `<article class="issue ${st.read?"read":""} ${i.skip?"optional":""} ${i.future?"future":""} ${isInsert?"chronologyInsert":""}" id="issue-${esc(i.seriesId)}-${i.n}">${numberHtml}<div class="cover"><div class="fallback">${esc(i.name)}</div>${coverImg(i)}</div><div class="meta"><div class="issueBadges">${insertBadge}</div><h4>${esc(i.name)} ${i.url?`<a href="${esc(i.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}${i.sharedWith?.length?`<span class="sharedBadge">condiviso con ${esc(i.sharedWith.join(", "))}</span>`:""}${i.future?'<span class="futureBadge">ANNUNCIATO</span>':""}</h4><div class="title">${esc(i.title)}</div><div class="instruction">${esc(i.instruction)}</div></div><div class="date">${esc(i.date)}${i.dateQuality==="ricostruita"?' <span title="Data ricostruita" style="color:#718196;font-size:7px">≈</span>':""}<br><span class="eraName">${esc(i.era)}</span><span class="seq">${i.required!==false?(i.future?"ANNUNCIATO":"Tappa obbligatoria"):"FACOLTATIVO / SALTA"}</span></div><div class="status"><button type="button" class="${st.owned?"on owned":""}" data-owned="${esc(i.id)}">${icon(st.owned?"check":"archive")}<span>Recuperato</span></button><button type="button" class="${st.read?"on read":""}" data-read="${esc(i.id)}">${icon(st.read?"check":"book")}<span>Letto</span></button></div></article>`}
'''
    source, count = re.subn(
        r"function issueHtml\(i\)\{.*?\}\n(?=function eraHtml\(g\))",
        issue_html,
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Impossibile sostituire issueHtml in js/app.js")

    render_filters = r'''function renderFilters(){
  const q=els.search.value.trim().toLowerCase();
  const source=currentCharacter.issues.filter(i=>(optionalVisible||!i.skip)&&(activeSeries==="Tutte"||i.seriesId===activeSeries)&&(!q||[i.n,i.name,i.title,i.date,i.era,i.eraSub,i.series].join(" ").toLowerCase().includes(q)));
  const eras=["Tutte",...new Set(source.map(i=>i.era))];
  els.filterBar.innerHTML=`<span class="filterLabel">Testata</span><button class="chip ${activeSeries==="Tutte"?"active":""}" data-series="Tutte">Tutte</button>`+(currentCharacter.series||[]).map(s=>`<button class="chip ${activeSeries===s.id?"active":""}" data-series="${esc(s.id)}">${esc(s.name)}</button>`).join("")+`<span class="filterDivider"></span><span class="filterLabel">Era</span>`+eras.map(e=>`<button class="chip ${activeEra===e?"active":""}" data-era="${esc(e)}">${esc(e)}</button>`).join("");
  els.filterBar.querySelectorAll("[data-series]").forEach(b=>b.onclick=()=>{activeSeries=b.dataset.series;activeEra="Tutte";renderAll()});
  els.filterBar.querySelectorAll("[data-era]").forEach(b=>b.onclick=()=>{activeEra=b.dataset.era;renderAll()})}
'''
    source, count = re.subn(
        r"function renderFilters\(\)\{.*?\}\n(?=function issueHtml\(i\))",
        render_filters,
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Impossibile sostituire renderFilters in js/app.js")

    notice_start = 'function renderNotices(){const id=activeCharacter,ns=[];'
    iron_notice = (
        'function renderNotices(){const id=activeCharacter,ns=[];'
        'if(id==="ironman")ns.push(["Ordine narrativo",'
        '"Il numero grande indica la posizione nel percorso di lettura; il titolo conserva il numero dell’edizione italiana. Gli inserti cronologici obbligatori sono evidenziati."]);'
    )
    if 'if(id==="ironman")ns.push(["Ordine narrativo"' not in source:
        if notice_start not in source:
            raise RuntimeError("Impossibile trovare renderNotices in js/app.js")
        source = source.replace(notice_start, iron_notice, 1)

    APP.write_text(source, encoding="utf-8")


def patch_css() -> None:
    source = CSS.read_text(encoding="utf-8")
    block = r'''
/* Tracker readability redesign v1 */
#trackerView{font-size:16px}
.filterLabel{font-size:9px;letter-spacing:.13em;text-transform:uppercase;color:#718196;font-weight:900;margin:0 2px}.filterDivider{width:1px;height:26px;background:var(--line);margin:0 3px}.eraName{color:var(--cyan);font-size:10px}.issueBadges{min-height:0;margin-bottom:5px}.chronologyBadge{display:inline-flex;align-items:center;padding:4px 7px;border:1px solid color-mix(in srgb,var(--accent) 70%,var(--line));border-radius:999px;background:color-mix(in srgb,var(--accent) 10%,#0b1118);color:var(--accent);font-size:8px;line-height:1;text-transform:uppercase;letter-spacing:.09em;font-weight:950}.issue.chronologyInsert{border-color:color-mix(in srgb,var(--accent) 65%,var(--line));background:linear-gradient(105deg,color-mix(in srgb,var(--accent) 8%,#101821),#0d141c 38%,#0b1118);box-shadow:inset 4px 0 0 var(--accent),0 14px 34px rgba(0,0,0,.16)}.issue.chronologyInsert:hover{border-color:var(--accent)}.issue.chronologyInsert .narrativeNum b{color:var(--accent)}
.narrativeNum{display:flex;min-width:0;flex-direction:column;align-items:flex-start;justify-content:center;line-height:1}.narrativeNum>span{color:#718196;font-size:8px;font-weight:950;letter-spacing:.13em;text-transform:uppercase}.narrativeNum>b{display:block;margin-top:6px;color:var(--text);font-size:24px;font-weight:900;letter-spacing:-.04em}.narrativeNum>small{display:block;margin-top:8px;max-width:92px;color:#8696a6;font-size:8px;line-height:1.3;font-weight:750}
@media(min-width:1121px){
  .app{grid-template-columns:340px minmax(0,1fr)}.sidebar{padding:24px 20px;gap:18px}.trackerSidebar{gap:16px}.charGrid{gap:10px}.charBtn{padding:14px 12px;border-radius:15px}.charIcon{width:58px;height:58px;margin-bottom:10px}.charBtn b{font-size:13px}.charBtn span{font-size:9px}.label{font-size:10px}.card{padding:17px}.bigNum{font-size:44px;margin:10px 0}.stat{padding:11px}.stat b{font-size:19px}.stat span{font-size:9px}.seriesNav,.sideActions{gap:9px}.seriesNav button,.sideActions button,.sideActions label{padding:11px 12px;border-radius:12px}.seriesNav b{font-size:11px}.seriesNav span{font-size:9px}.sideActions button,.sideActions label{font-size:11px}.footerNote{font-size:10px;line-height:1.6}
  .topbar{min-height:66px;padding:12px 28px;grid-template-columns:auto auto minmax(320px,720px) auto;gap:16px}.topbarTitle strong{font-size:13px}.topbarTitle span{font-size:10px}.search input{padding:12px 15px;font-size:12px}.compactBtn{padding:10px 12px;font-size:10px}.content{max-width:1720px;padding:31px 36px 78px}.hero{gap:18px;margin-bottom:20px}.heroPanel{padding:30px}.hero h1{font-size:clamp(40px,3.2vw,62px);line-height:.96}.hero p{font-size:14px;line-height:1.65}.nextPanel{grid-template-columns:124px 1fr;gap:18px;padding:20px}.nextCover{width:124px;height:178px}.nextMeta h2{font-size:22px}.nextMeta p{font-size:11px;line-height:1.55}.btn{padding:9px 11px;font-size:10px}.route{gap:11px;margin-bottom:19px}.routeCard{padding:14px;border-radius:15px}.routeCard b{font-size:12px}.routeCard span{font-size:10px;line-height:1.45}.notice{padding:14px 16px;margin-bottom:18px}.notice b{font-size:13px}.notice p{font-size:10.5px;line-height:1.6}.filterBar{padding:13px 14px;gap:8px;margin-bottom:22px}.chip{padding:9px 11px;font-size:10px}.seriesBlock{margin:30px 0 46px}.seriesHead,.eraHead{margin-bottom:13px}.seriesHead h2{font-size:27px;letter-spacing:-.025em}.seriesHead p,.eraHead p{font-size:10.5px;line-height:1.45}.seriesPct,.count{font-size:10px}.era{margin:20px 0 30px}.eraHead h3{font-size:19px}.issueList{gap:12px}.issue{min-height:148px;grid-template-columns:96px 96px minmax(360px,1fr) 150px 205px;gap:18px;padding:14px 17px;border-radius:16px}.cover{width:86px;height:124px;border-radius:10px}.meta h4{font-size:14px;line-height:1.35}.meta .title{font-size:11px;margin-top:6px;line-height:1.45}.meta .instruction{margin-top:8px;font-size:10.5px;line-height:1.55}.meta a{font-size:9px;margin-left:8px}.sharedBadge,.futureBadge{font-size:8px}.date{font-size:10.5px;line-height:1.6}.eraName{font-size:10px}.seq{font-size:9px;margin-top:6px;letter-spacing:.02em}.status{gap:7px}.status button{padding:9px 10px;border-radius:9px;font-size:10px;gap:6px}.status button svg{width:15px;height:15px}
  body.compact .issue{min-height:86px;grid-template-columns:82px minmax(340px,1fr) 140px 190px;padding:11px 14px}body.compact .issue .cover{display:none}body.compact .meta h4{font-size:12px}body.compact .meta .instruction{font-size:9.5px}.compact .narrativeNum>b{font-size:20px}
}
@media(min-width:1121px) and (max-width:1450px){.app{grid-template-columns:310px minmax(0,1fr)}.content{padding-left:25px;padding-right:25px}.issue{grid-template-columns:82px 84px minmax(300px,1fr) 132px 184px;gap:13px;padding:12px 13px}.cover{width:74px;height:107px}.meta h4{font-size:13px}.meta .instruction{font-size:9.5px}.narrativeNum>b{font-size:21px}.narrativeNum>small{font-size:7.5px}.status button{font-size:9px;padding:8px}.routeCard b{font-size:11px}}
@media(max-width:1120px){.content{padding:22px 18px 54px}.issue{grid-template-columns:76px 82px minmax(0,1fr) 128px;gap:13px;padding:12px;border-radius:15px}.cover{width:72px;height:104px}.meta h4{font-size:12.5px}.meta .title{font-size:10px}.meta .instruction{font-size:9px}.date{font-size:9.5px}.status{grid-column:3/-1}.narrativeNum>b{font-size:21px}.narrativeNum>small{font-size:7.5px}.chip{font-size:9px;padding:8px 10px}}
@media(max-width:720px){.filterDivider{display:none}.filterLabel{width:100%;margin-top:4px}.issue{grid-template-columns:64px 68px minmax(0,1fr);gap:10px;padding:11px 9px}.cover{width:62px;height:90px}.narrativeNum>b{font-size:18px}.narrativeNum>small{max-width:62px;font-size:6.8px}.meta h4{font-size:11.5px}.meta .title{font-size:9px}.meta .instruction{font-size:8.5px;line-height:1.45}.date,.status{grid-column:3}.status{justify-content:flex-start}.status button{font-size:8.5px;padding:7px 8px}.chronologyBadge{font-size:7px}.seriesHead h2{font-size:20px}.eraHead h3{font-size:16px}}
/* /Tracker readability redesign v1 */
'''

    pattern = re.compile(re.escape(CSS_START) + r".*?" + re.escape(CSS_END), re.S)
    if pattern.search(source):
        source = pattern.sub(block.strip(), source, count=1)
    else:
        source = source.rstrip() + "\n\n" + block.strip() + "\n"
    CSS.write_text(source, encoding="utf-8")


def main() -> None:
    patch_ironman_data()
    patch_app_renderer()
    patch_css()
    print("Tracker UI: ordine narrativo prioritario, Extremis separato e leggibilità desktop aumentata.")


if __name__ == "__main__":
    main()
