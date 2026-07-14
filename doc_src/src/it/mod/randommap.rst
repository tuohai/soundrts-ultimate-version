.. raw:: html

   <script type="text/javascript" src="langdir.js"></script>

Guida alle mappe casuali
========================

.. contents::

Introduzione
------------

Da SoundRTS 1.4.3.4, il generatore procedurale di mappe casuali (RMG) costruisce mappe ``.txt`` standard dalle opzioni di menu. Le mappe generate usano la stessa pipeline di caricamento delle mappe fatte a mano e funzionano nello skirmish locale o nella creazione di stanze online.

1. Dove trovarlo
----------------

.. list-table::
   :header-rows: 1

   * - Modalità
     - Percorso
   * - Locale
     - Menu principale → Avvia una partita → Mappa casuale (prima voce)
   * - skirmish
     - 
   * - Host online
     - Collegati al server → Crea partita → scegli Mappa casuale → velocità →
   * - 
     - configura


Dopo la configurazione, il gioco locale continua con invita-IA / fazione / avvio; online viene inviato un comando ``create_random`` e l’host genera la mappa all’inizio della partita.

2. Flusso di configurazione
---------------------------

Il sottomenu procede così ( Esc torna indietro di un livello ):

1. Modello di mappa (o Importa codice di condivisione — sezione 4)
2. Dimensione: piccola / media / grande
3. Giocatori: 2 / 3 / 4
4. Modalità squadre (solo 4 giocatori): tutti contro tutti o 2v2 fisso
5. Forza mostri: debole / media / forte (guarnigione ostile al centro; attacca i giocatori — debole: 2 footmen / media: 4 footmen + 2 archers / forte: 6 footmen + 4 archers + 1 knight)
6. Disposizione risorse: bilanciata / raggruppata
7. Terreno (non per il modello lanes): casuale / erba, più ogni terreno ``rmg_terrain 1`` in ``rules.txt``
8. Acqua (non per lanes): nessuna / lago / fiume
9. Tesoro: nessuno / basso / alto (richiede tipi ``class item`` raccoglibili nelle regole)
10. Modalità vittoria: conquista / economica / esplorazione / sopravvivenza (predefinita conquista; vedi sezione 7)
11. Seed: casuale o numero personalizzato (0–99999)
12. Tregua: 0 / 5 / 10 / 15 / 20 minuti

Dopo la selezione del seed senti un’anteprima vocale delle impostazioni; dopo la conferma della tregua la mappa viene generata.

2.1 Modelli
^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Modello
     - Descrizione
   * - Standard
     - Griglia classica, partenze e ponti casuali
   * - Fast
     - Più risorse iniziali, partite più rapide
   * - Macro
     - Cap popolazione più alto e più prati, orientato all’economia
   * - Lanes
     - Layout a tre corsie (stile TD2); senza passi terreno/acqua


2.2 Squadre 2v2
^^^^^^^^^^^^^^^

Con 4 giocatori e 2v2, la mappa aggiunge trigger di alleanza: i giocatori 1+2 e 3+4 partono alleati.

3. Annuncio di generazione e F5/F6
----------------------------------

In modalità locale, quando la mappa è pronta il gioco annuncia:

- Mappa generata
- Seed (numero per riprodurre lo stesso layout)
- Codice di condivisione (stringa completa delle impostazioni)
- Premi F5 per ripetere (suggerimento cronologia)

Il menu invita-IA che segue non cancella questo: F5 ripete il messaggio precedente, F6 scorre la cronologia vocale così puoi riascoltare seed e codice di condivisione in qualsiasi momento.

I menu supportano le stesse chiavi di cronologia F5 / F6 che in partita.

4. Codici di condivisione
-------------------------

4.1 Formato
^^^^^^^^^^^

Esempio::

 RMG1:f:m:2:med:b:r:f:v:hi:c:4242

Dodici parti separate da due punti: prefisso ``RMG1`` + 11 campi (i codici legacy a 10 campi omettono la vittoria e usano conquista come predefinito):

.. list-table::
   :header-rows: 1

   * - Campo
     - Significato
     - Esempi
   * - Modello
     - standard / fast / macro / lanes
     - s / f / m / l
   * - Dimensione
     - small / medium / large
     - s / m / l
   * - Giocatori
     - 2–4
     - 2
   * - Mostri
     - weak / medium / strong
     - w / med / s
   * - Risorse
     - balanced / clustered
     - b / c
   * - Terreno
     - random / grass / marsh / mountain
     - r / g / a / t
   * - Squadre
     - ffa / teams_2v2
     - f / t
   * - Acqua
     - none / lake / river
     - n / l / v
   * - Tesoro
     - none / low / high
     - n / lo / hi
   * - Vittoria
     - conquest / economic /
     - c / e / x / s
   * - 
     - exploration / survival
     - 
   * - Seed
     - 0 = casuale; >0 fisso
     - 4242


Abbreviazioni vittoria: ``c`` conquista, ``e`` economica, ``x`` esplorazione, ``s`` sopravvivenza.

L’importazione accetta codici con o senza il prefisso ``RMG1:``; ``/`` funziona come separatore al posto di ``:``.

4.2 Importa codice di condivisione
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Nel sottomenu modello di mappa, scegli Importa codice di condivisione, digita o incolla il codice, Invio per confermare, Esc per annullare.

La casella di input supporta le scorciatoie di modifica standard (come altri campi di testo, ad esempio seed o login):

.. list-table::
   :header-rows: 1

   * - Scorciatoia
     - Azione
   * - Ctrl+A
     - Seleziona tutto
   * - Ctrl+C
     - Copia (tutto il testo se nulla è selezionato)
   * - Ctrl+X
     - Taglia
   * - Ctrl+V
     - Incolla (caratteri non validi filtrati)
   * - Backspace / Delete
     - Elimina selezione o carattere prima/dopo il cursore


Lunghezza massima 80; caratteri ammessi: lettere, cifre, ``:``, ``/``, ``.``, ``-``.

In caso di successo senti un’anteprima e vai direttamente a Tregua (saltando i passi intermedi). I codici non validi mostrano Codice di condivisione non valido e tornano al menu modello.

5. Note multigiocatore
----------------------

- Il comando ``create_random …`` dell’host viene applicato all’avvio della partita; tutti i client ottengono la stessa mappa deterministica da seed + impostazioni.
- I client non sentono l’annuncio locale “mappa generata + codice di condivisione”; condividi il codice prima di ospitare oppure fai importare lo stesso codice agli ospiti quando creano una stanza.
- Le partite pubbliche e i minuti di tregua seguono i soliti sottomenu velocità / visibilità.

6. Confronto con ``#random_choice`` nei file mappa
-------------------------------------------------

``#random_choice`` / ``#end_random_choice`` in un file mappa sono scelte del preprocessore tra alternative fisse (es. posizionamento casuale dell’oro). Non è RMG.

RMG genera l’intera mappa dai parametri, con seed e codici di condivisione per la riproduzione.

7. Gameplay ispirato a HoMM / Civ5
----------------------------------

Funzionalità RMG ispirate a Heroes of Might and Magic e Civilization V (obiettivi di mappa e POI, non turni completi né alberi tecnologici):

7.1 Modalità di vittoria
^^^^^^^^^^^^^^^^^^^^^^^^

Conquista
    Elimina tutti i giocatori nemici (predefinita; ripulire i creep del centro è opzionale).

Economica
    L’oro totale raccolto raggiunge l’obiettivo (esclude lo stock iniziale; la spesa conta comunque; controllo circa ogni 60 s).
    Fast 2000 / standard 3000 / macro 5000 / lanes 2500.

Esplorazione
    Il tuo campo scopre ogni rovina antica (FFA: contano solo le tue scoperte; 2v2: contano anche quelle degli alleati).

Sopravvivenza
    Resisti fino alla fine del timer con il municipio intatto (10 min fast / 15 min altrimenti).

Perdere tutti gli edifici ``provides_survival`` significa comunque sconfitta. Nelle modalità esplorazione/economica/sopravvivenza, eliminare tutti i nemici non dà vittoria automatica; puoi comunque attaccare. I controlli di vittoria girano circa ogni 30 s (esplorazione) o 60 s (economica) dopo che le condizioni sono soddisfatte.

7.2 POI della mappa
^^^^^^^^^^^^^^^^^^^

Ogni mappa RMG (quando i tipi esistono in ``rules.txt``) può includere:

- Rovine antiche (``ancient_ruin``): la tua unità entra nella casella per risorse (fast: 300 oro + 150 legno; altre: 500 + 250); l’esplorazione richiede che il tuo campo trovi ogni rovina; ricompensa solo al primo visitatore; l’edificio resta dopo la scoperta
- Caserma catturabile (``captured_barracks``): 2 footmen + 1 archer di guardia; elimina le guardie, attacca per catturare, poi addestra footmen/archers; le caserme non rinforzate generano footmen extra ogni ~5–10 minuti
- Guarnigione centrale: menu Forza mostri (debole 2 footmen / media 4+2 / forte 6+4+1 knight)

7.3 Letture ulteriori
^^^^^^^^^^^^^^^^^^^^^

Confronto completo, ID vocali ed estensione mod: ``player/英雄无敌与文明5玩法说明.htm`` (cinese; dettagli RMG in inglese in ``player/random-map.htm``).

8. Modelli di mappa casuale personalizzati
------------------------------------------

Giocatori e autori di mod possono aggiungere file di testo ``random_map_template`` per estendere i modelli RMG e allineare le scelte di terreno a ``rules.txt``.

8.1 Dove mettere i file
^^^^^^^^^^^^^^^^^^^^^^^

- ``cfg/randommap/*.txt`` — modelli locali del giocatore (consigliato)
- ``mods/<modname>/randommap/*.txt`` — distribuiti con una mod
- Riferimento sintassi: ``res/randommap/example.txt``

8.2 Formato file
^^^^^^^^^^^^^^^^

::

 random_map_template
 name my_macro
 extends macro
 title My macro map
 terrain_modes random grass marsh rocky_plain
 water_terrain lake
 monster_medium 4 footman 2 archer

- ``extends`` eredita da ``standard``, ``fast``, ``macro``, ``lanes`` o da un altro modello personalizzato
- I modelli integrati omettono ``terrain_modes`` per elencare automaticamente ``random``, ``grass`` e tutti i terreni ``rmg_terrain 1`` dalle regole
- ``terrain_modes`` limita opzionalmente il menu (ogni nome deve essere ``class terrain`` in ``rules.txt``)
- Codici di condivisione: i modelli integrati usano ancora le abbreviazioni ``RMG1:``; modelli personalizzati o nomi di terreno personalizzati usano ``RMG2:`` (nomi completi, senza abbreviazioni)

8.3 Flag di terreno in rules.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Flag opzionali su ``class terrain``:

- ``rmg_terrain 1`` — terreno di terra che RMG può posizionare
- ``rmg_border 1`` — posiziona lungo i bordi della mappa (es. montagne)
- ``rmg_water 1`` — nome terreno usato per le caselle d’acqua lago/fiume
- ``rmg_ford 1`` — nome terreno usato per i guadi delle mappe a corsie

Quando RMG posiziona il terreno, legge ``speed``, ``is_water``, ``blocks_path`` e proprietà correlate dalle regole invece di valori cablati ``marsh`` / ``mountain``.
