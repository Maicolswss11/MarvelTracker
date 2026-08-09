# MarvelTracker

Marvel Archive è un tracker web delle edizioni italiane Marvel.

La home `#/home` riunisce il prossimo albo, il riepilogo globale e un explorer gerarchico per universi, famiglie ed eventi. Le pagine `#/{percorso}` aprono il tracker narrativo completo del percorso selezionato; `#/profile` raccoglie collezione, letture, wishlist e liste personali.

## Architettura

- `index.html` — shell leggera
- `css/app.css` — stile
- `css/cinematic.css` — sistema visivo, layout responsive e motion design
- `js/app.js` — logica dell'app
- `js/hub-ui.js` — navigazione per universi, famiglie ed eventi
- `js/motion.js` — transizioni, reveal, micro-interazioni e menu mobile
- `data/characters.json` — manifest dei personaggi
- `data/characters/*.json` — metadati leggeri per personaggio
- `data/encoded/*.json` — manifest dei dataset compressi
- `data/b64/*.b64` — blocchi gzip/base64 lazy-loaded
- `assets/heroes/` — loghi PNG personalizzati

La vecchia `const DATA` monolitica non esiste più nell'HTML. I dati vengono caricati e decompressi solo quando selezioni il personaggio.

## Percorsi attuali

Il manifest comprende personaggi, squadre, universi completi ed eventi. La tassonomia in `data/hubs.json` organizza i percorsi tra Terra-616, Ultimate classico, Nuovo Ultimate, famiglie narrative ed eventi senza duplicare la collezione globale.

## Interfaccia

Il sistema visivo include una sequenza di apertura, transizioni tra viste, entrate progressive, contatori animati, illuminazione reattiva e feedback sui comandi. Su mobile la navigazione dei percorsi usa un pannello laterale dedicato. `prefers-reduced-motion` disattiva le animazioni non essenziali e mantiene immediatamente visibili tutti i contenuti.

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

Il repository include emblemi locali per personaggi, squadre, universi ed eventi, oltre al wordmark Marvel dell'intestazione.

## Verifica dati

Eseguire `node scripts/verify-data.mjs` per controllare integrità gzip, schema, duplicati e conteggi di tutti gli archivi. `scripts/rebuild_character_data.py` ricostruisce gli indici danneggiati dai dati pubblici ComicsBox.
