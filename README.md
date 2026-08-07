# MarvelTracker

Marvel Archive è un tracker web delle edizioni italiane Marvel.

## Architettura

- `index.html` — shell leggera
- `css/app.css` — stile
- `js/app.js` — logica dell'app
- `data/characters.json` — manifest dei personaggi
- `data/characters/*.json` — metadati leggeri per personaggio
- `data/encoded/*.json` — manifest dei dataset compressi
- `data/b64/*.b64` — blocchi gzip/base64 lazy-loaded
- `assets/heroes/` — loghi PNG personalizzati

La vecchia `const DATA` monolitica non esiste più nell'HTML. I dati vengono caricati e decompressi solo quando selezioni il personaggio.

## Personaggi attuali

- Iron Man
- Thor
- Capitan America
- Hulk
- Spider-Man

## Progressi

I progressi restano nel `localStorage` del browser. `Recuperato` è globale per albo fisico; `Letto` è separato per personaggio. Export/import JSON inclusi.

## GitHub Pages

Il workflow `.github/workflows/pages.yml` pubblica automaticamente `main` su GitHub Pages.

## Copertine

Le copertine sono remote. Per Spider-Man vengono usati URL puntuali ComicsBox `UR_SM_###.jpg`; se una cover non è disponibile viene mostrato un fallback generato dal tracker.

## Loghi

I loghi non sono inclusi nel repository: inserire i PNG personalizzati in `assets/heroes/` mantenendo i nomi documentati nel relativo README.
