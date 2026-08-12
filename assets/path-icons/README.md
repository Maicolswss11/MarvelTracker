# Path icons

Questa cartella contiene esclusivamente le immagini raster usate come identità visiva dei percorsi (quelle mostrate, per esempio, in "Continua a leggere").

Le immagini profilo sono un inventario separato: restano in `assets/heroes/` e vengono configurate in `js/profile-ui.js`. Non vanno copiate qui né registrate automaticamente come icone percorso.

- Usa immagini quadrate o quasi quadrate, preferibilmente almeno 500×500 px.
- JPG, PNG e WebP sono supportati. I file JFIF vanno rinominati in `.jpg`: sono già immagini JPEG e non richiedono ricompressione.
- Mantieni un file per percorso e registralo in `data/path-icons.json`.
- Il nome definitivo deve coincidere con l'ID del percorso, per esempio `hulk.jpg`, `doctor-strange.jpg` o `ultimate-ironman.png`. I prefissi usati durante il caricamento, come `pers_`, vengono rimossi quando l'immagine viene collegata.
- I builder dei dati non modificano questa cartella né la mappa degli override.

La pagina `icon-gallery.html` mostra l'inventario completo, il nome esatto di ogni percorso e quali immagini devono ancora essere sostituite.
