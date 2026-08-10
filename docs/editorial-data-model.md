# Modello editoriale MarvelTracker

Il Reading Path è una vista curatoriale sopra le edizioni italiane: non coincide con la struttura editoriale delle testate.

## Identità e stato

- L'ID dell'albo italiano è globale e identifica la copia fisica o digitale (`HED:44`, `DEH_M:170`, ecc.).
- `state.collection[issueId]` conserva `physical` e `digital` una sola volta per albo.
- `state.characters[pathId].issues[issueId].read` conserva la lettura separatamente per percorso.
- Il titolo di una testata da solo non è un'identità. Gli ID di serie distinguono editore e incarnazione editoriale (`HED` Corno e `HULK2_M` Panini).

## Relazione a tre livelli

```json
{
  "id": "HED:44",
  "name": "Hulk e i Difensori #44",
  "contents": [
    {"id": "IH2_174", "series": "The Incredible Hulk Vol 2", "number": "174"},
    {"id": "DE1_029", "series": "Defenders vol 1", "number": "29"},
    {"id": "JUWATLAS_056", "series": "Journey into Unknown Worlds", "number": "56"}
  ],
  "readingStep": {
    "pathId": "hulk-classic-corno",
    "position": 44,
    "contentIds": ["IH2_174"],
    "scope": "selected-contents"
  }
}
```

`contents` descrive ciò che è stampato nell'albo. `readingStep.contentIds` seleziona ciò che va letto nel percorso attivo. Due percorsi possono quindi riutilizzare lo stesso `id` fisico e selezionare storie diverse.

`contentsStatus` vale:

- `complete`: tutti i contenuti sono stati letti dalla scheda dell'albo italiano;
- `path-scoped`: sono noti almeno i contenuti necessari ai percorsi costruiti, ma l'indice completo non è ancora stato migrato;
- `unavailable`: la fonte non ha restituito un indice utilizzabile.

## Percorsi, archivi e rami

- `pathRole: main` indica una progressione principale.
- `pathRole: historical-archive` indica un archivio consultabile che non altera la progressione moderna.
- `canonicalCharacter` collega un archivio al personaggio principale senza fondere i progressi.
- `relatedPaths` dichiara collegamenti navigabili.
- `branches` descrive eventi, spin-off e percorsi paralleli; gli albi restano deduplicati tramite il loro ID globale.

Il modello è incrementale: gli archivi preesistenti senza `contents` continuano a funzionare e possono essere migrati un albo alla volta.
