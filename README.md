# MarvelTracker

Marvel Archive è un tracker web delle edizioni italiane Marvel.

La home `#/home` riunisce il prossimo albo, il riepilogo globale, il pulsante per riprendere l'ultimo percorso e le schede dei cinque personaggi. Le pagine `#/{personaggio}` aprono il tracker completo del singolo eroe e includono un tasto Home esplicito.

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

## Profili e sincronizzazione

Il frontend supporta account Supabase con email/password e una strategia local-first: le modifiche vengono salvate subito sul dispositivo e sincronizzate nel record cloud dell'utente. Il vecchio stato locale viene migrato automaticamente al primo accesso quando il profilo non contiene ancora progressi.

Per attivare il cloud:

1. eseguire `supabase/schema.sql` nel SQL Editor del progetto;
2. inserire Project URL e Publishable key in `js/supabase-config.js`;
3. configurare l'URL pubblico di MarvelTracker tra i Redirect URLs di Supabase Auth.

La Publishable key può essere esposta nel browser; la protezione dei dati dipende dalle policy RLS incluse nello schema. Non inserire mai una `service_role` key nel repository.

## GitHub Pages

Il workflow `.github/workflows/pages.yml` pubblica automaticamente `main` su GitHub Pages.

## Copertine

Le copertine sono remote. Per Spider-Man vengono usati URL puntuali ComicsBox `UR_SM_###.jpg`; se una cover non è disponibile viene mostrato un fallback generato dal tracker.

## Loghi

Il repository include cinque emblemi PNG locali per il selettore dei personaggi e il wordmark Marvel dell'intestazione. Gli asset possono essere rigenerati con `python scripts/generate_logos.py`.

## Verifica dati

Eseguire `node scripts/verify-data.mjs` per controllare integrità gzip, schema, duplicati e conteggi di tutti gli archivi. `scripts/rebuild_character_data.py` ricostruisce gli indici danneggiati dai dati pubblici ComicsBox.
