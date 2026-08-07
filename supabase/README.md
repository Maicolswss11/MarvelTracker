# Configurazione Supabase

MarvelTracker usa Supabase Auth per gli account e Postgres per sincronizzare lo stato del tracker.

## 1. Crea il database

Apri **SQL Editor** nel progetto Supabase ed esegui integralmente `schema.sql`. Lo script crea:

- `profiles`, con nome e colore avatar;
- `tracker_states`, con un documento JSON per utente;
- trigger per creare il profilo alla registrazione e aggiornare i timestamp;
- policy RLS che limitano lettura e scrittura al proprietario autenticato.

## 2. Collega il frontend

In **Project Settings → API** copia:

- Project URL;
- Publishable key.

Inseriscili in `js/supabase-config.js`. Questi valori sono destinati al frontend e non sono segreti. Non usare la chiave `service_role`.

## 3. Configura Auth

In **Authentication → URL Configuration** imposta come Site URL:

`https://maicolswss11.github.io/MarvelTracker/`

Aggiungi lo stesso indirizzo ai Redirect URLs. Il flusso iniziale usa email e password; se la conferma email è attiva, l'utente dovrà aprire il link ricevuto prima del primo accesso.

## Strategia di sincronizzazione

- senza account, MarvelTracker continua a usare il profilo locale esistente;
- al primo accesso, uno stato cloud già presente ha priorità;
- se il cloud è vuoto, vengono caricati i progressi locali;
- durante un'interruzione di rete, le modifiche restano locali e vengono reinviate quando la connessione torna disponibile;
- la sincronizzazione usa last-write-wins sull'intero stato del tracker.
