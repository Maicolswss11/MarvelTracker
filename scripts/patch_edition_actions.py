from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Patch target not found: {label}")
    return text.replace(old, new, 1)


editions = Path("js/editions.js")
text = editions.read_text(encoding="utf-8")
text = replace_once(text, '''    if(owned){
      const previous = state.editions[id];
      state.editions[id] = {
        ...(previous && typeof previous === "object" ? previous : {}),
        owned:true,
        addedAt: previous?.addedAt || new Date().toISOString(),
      };
    }else delete state.editions[id];''', '''    if(owned){
      const previous = state.editions[id];
      state.editions[id] = {
        ...(previous && typeof previous === "object" ? previous : {}),
        owned:true,
        addedAt: previous?.addedAt || new Date().toISOString(),
      };
      if(state.wishlist?.[id]) delete state.wishlist[id];
    }else delete state.editions[id];''', "auto-remove wishlist when owned")

text = replace_once(text,
    "function openPicker({state,pathId,issue,onToggle}){",
    "function openPicker({state,pathId,issue,onToggle,onToggleWishlist,onAddToList}){",
    "picker callback signature",
)

old_picker = '''      <div class="editionChoices">${options.map(edition => {
        const owned = isOwned(state,edition.id);
        const contents = (edition.contents || []).join(" · ");
        return `<article class="editionChoice ${owned?"owned":""}">
          <div class="editionChoiceCover">${edition.cover?`<img src="${esc(edition.cover)}" alt="${esc(edition.name)}" referrerpolicy="no-referrer">`:""}</div>
          <div class="editionChoiceInfo"><span>${esc(edition.format || "Edizione alternativa")}</span><h3>${esc(edition.name)}</h3><p>${esc(edition.series)}${edition.number?` #${esc(edition.number)}`:""} · ${esc(edition.publisher || "")}</p><small>${esc(edition.coverage?.label || contents)}</small>${edition.url?`<a href="${esc(edition.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}</div>
          <button type="button" class="editionOwnButton ${owned?"owned":""}" data-toggle-edition="${esc(edition.id)}">${owned?"✓ Posseduto":"Segna posseduto"}</button>
        </article>`;
      }).join("")}</div>`;
    body.querySelectorAll("[data-toggle-edition]").forEach(button => button.onclick = () => {
      const id = button.dataset.toggleEdition;
      onToggle?.(id,!isOwned(state,id));
      openPicker({state,pathId,issue,onToggle});
    });
    if(typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open","");'''

new_picker = '''      <div class="editionChoices">${options.map(edition => {
        const owned = isOwned(state,edition.id);
        const wishlisted = !!state?.wishlist?.[edition.id];
        const lists = Object.entries(state?.lists || {});
        const contents = (edition.contents || []).join(" · ");
        return `<article class="editionChoice ${owned?"owned":""}">
          <div class="editionChoiceCover">${edition.cover?`<img src="${esc(edition.cover)}" alt="${esc(edition.name)}" referrerpolicy="no-referrer">`:""}</div>
          <div class="editionChoiceInfo"><span>${esc(edition.format || "Edizione alternativa")}</span><h3>${esc(edition.name)}</h3><p>${esc(edition.series)}${edition.number?` #${esc(edition.number)}`:""} · ${esc(edition.publisher || "")}</p><small>${esc(edition.coverage?.label || contents)}</small>${edition.url?`<a href="${esc(edition.url)}" target="_blank" rel="noopener">ComicsBox ↗</a>`:""}</div>
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
    }'''
text = replace_once(text, old_picker, new_picker, "edition picker controls")
editions.write_text(text, encoding="utf-8")

app = Path("js/app.js")
text = app.read_text(encoding="utf-8")
old_app = '''function setEditionOwned(id,owned){
  window.MarvelEditions?.setOwned(state,id,owned);
  saveState();
  renderAll();
  void window.MarvelProfile?.render();
}
function openEditionPicker(issueId){
  const issue=currentCharacter?.issues?.find(item=>item.id===issueId);
  if(!issue)return;
  window.MarvelEditions?.openPicker({state,pathId:activeCharacter,issue,onToggle:setEditionOwned});
}'''
new_app = '''function setEditionOwned(id,owned){
  window.MarvelEditions?.setOwned(state,id,owned);
  saveState();
  renderAll();
  void window.MarvelProfile?.render();
}
function setEditionWishlist(id,wishlisted){
  state.wishlist??={};
  if(wishlisted) state.wishlist[id]={addedAt:new Date().toISOString()};
  else delete state.wishlist[id];
  saveState();
  renderAll();
  void window.MarvelProfile?.render();
}
function addEditionToList(id,listId){
  const list=state.lists?.[listId];
  if(!list)return;
  list.issueIds??=[];
  if(!list.issueIds.includes(id))list.issueIds.push(id);
  saveState();
  renderAll();
  void window.MarvelProfile?.render();
}
function openEditionPicker(issueId){
  const issue=currentCharacter?.issues?.find(item=>item.id===issueId);
  if(!issue)return;
  window.MarvelEditions?.openPicker({state,pathId:activeCharacter,issue,onToggle:setEditionOwned,onToggleWishlist:setEditionWishlist,onAddToList:addEditionToList});
}'''
text = replace_once(text, old_app, new_app, "app edition callbacks")
app.write_text(text, encoding="utf-8")

css = Path("css/editions.css")
text = css.read_text(encoding="utf-8")
marker = "@media(max-width:650px)"
extra = ".editionChoiceActions{display:flex;min-width:148px;flex-direction:column;gap:8px}.editionWishlistButton,.editionListSelect{width:100%;min-height:38px;padding:9px 11px;border:1px solid #34485a;border-radius:10px;background:#111c27;color:#dce8f1;font:inherit;font-size:11px;font-weight:800;cursor:pointer}.editionWishlistButton.active{border-color:rgba(244,190,65,.55);background:rgba(244,190,65,.12);color:#ffd66e}.editionListSelect{appearance:auto;font-weight:700}.editionChoiceActions .editionOwnButton{width:100%}"
if marker not in text:
    raise RuntimeError("CSS media marker not found")
text = text.replace(marker, extra + "\n" + marker, 1)
text = replace_once(text,
    "@media(max-width:650px){.editionDialogShell{padding:20px 14px}.editionChoice{grid-template-columns:62px 1fr;align-items:start}.editionChoiceCover{width:62px}.editionOwnButton{grid-column:1/-1;width:100%}",
    "@media(max-width:650px){.editionDialogShell{padding:20px 14px}.editionChoice{grid-template-columns:62px 1fr;align-items:start}.editionChoiceCover{width:62px}.editionChoiceActions{grid-column:1/-1;width:100%;display:grid;grid-template-columns:1fr 1fr}.editionChoiceActions .editionOwnButton{grid-column:1/-1}.editionOwnButton{width:100%}",
    "mobile edition actions",
)
css.write_text(text, encoding="utf-8")

index = Path("index.html")
text = index.read_text(encoding="utf-8")
for old, new in (
    ("css/editions.css?v=2", "css/editions.css?v=3"),
    ("js/editions.js?v=5", "js/editions.js?v=6"),
    ("js/app.js?v=13", "js/app.js?v=14"),
):
    text = replace_once(text, old, new, f"cache bump {old}")
index.write_text(text, encoding="utf-8")

print("Alternative edition wishlist/list actions patched")
