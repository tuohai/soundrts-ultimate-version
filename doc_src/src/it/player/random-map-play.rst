Generatore di mappe casuali
============================


Da SoundRTS 1.4.3.4, il generatore procedurale di mappe casuali (RMG) costruisce mappe ``.txt`` standard dalle opzioni del menu. Le mappe generate usano la stessa pipeline di caricamento delle mappe fatte a mano e funzionano nello skirmish locale o nella creazione di stanze online.


----


1. Dove trovarlo
-----------------



.. list-table::
   :header-rows: 1

   * - Modalità
     - Percorso
   * - Skirmish locale
     - Menu principale → Inizia una partita → Mappa casuale (prima voce)
   * - Host online
     - Connettiti al server → Crea partita → scegli Mappa casuale → velocità → configura



Dopo la configurazione, il gioco locale continua con invita-IA / fazione / inizio; online viene inviato un comando ``create_random`` e l'host genera la mappa all'inizio della partita.


----


2. Flusso di configurazione
-----------------------------


Il sottomenu procede così ( Esc torna indietro di un livello ):

1. Modello di mappa (o Importa codice di condivisione — sezione 4)
2. Dimensione: piccola / media / grande
3. Giocatori: 2 / 3 / 4
4. Modalità squadre (solo 4 giocatori): tutti contro tutti o 2v2 fisse
5. Forza dei mostri: debole / media / forte (guarnigione ostile al centro; attacca i giocatori — debole: 2 fanti / media: 4 fanti + 2 arcieri / forte: 6 fanti + 4 arcieri + 1 cavaliere)
6. Disposizione delle risorse: bilanciata / raggruppata
7. Terreno (non per il modello lanes): casuale / erba / palude / montagna
8. Acqua (non per lanes): nessuna / lago / fiume
9. Tesoro: nessuno / basso / alto (richiede tipi ``class item`` raccoglibili nelle regole)
10. Modalità di vittoria: conquista / economica / esplorazione / sopravvivenza
11. Seed: casuale o numero personalizzato (0–99999)
12. Tregua: 0 / 5 / 10 / 15 / 20 minuti

Dopo la selezione del seed senti un'anteprima vocale delle impostazioni; dopo la conferma della tregua la mappa viene generata.

2.1 Modelli
~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modello
     - Descrizione
   * - Standard
     - Griglia classica, partenze e ponti casuali
   * - Fast
     - Più risorse iniziali, partite più rapide
   * - Macro
     - Limite di popolazione più alto e più prati, incentrato sull'economia
   * - Lanes
     - Layout a tre corsie (stile TD2); senza passi terreno/acqua



2.2 Squadre 2v2
~~~~~~~~~~~~~~~~


Con 4 giocatori e 2v2, la mappa aggiunge trigger di alleanza: i giocatori 1+2 e 3+4 partono alleati.

2.3 Modalità di vittoria
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modalità
     - Condizione di vittoria
     - Obiettivo iniziale (voce)
     - Note
   * - Conquista
     - Elimina tutti i giocatori nemici
     - Elimina tutti i giocatori nemici
     - Predefinita; non serve ripulire i creep del centro o le guardie delle caserme
   * - Economica
     - L'oro totale raccolto raggiunge l'obiettivo (esclude lo stock iniziale)
     - Raccogli N oro in totale
     - Spendere l'oro raccolto conta comunque; l'anteprima annuncia N; controllo circa ogni 60 s
   * - Esplorazione
     - Il tuo campo scopre tutte le rovine antiche
     - Scopri tutte le rovine con le tue forze
     - In 2v2 contano i ritrovamenti degli alleati; in FFA quelli dei nemici no; la ricompensa va comunque al primo visitatore
   * - Sopravvivenza
     - Resisti fino al timer con il municipio intatto
     - Resisti N minuti mantenendo il municipio
     - 10 min fast, 15 min altrimenti; perdere la base per primi = sconfitta; più vincitori ammessi



Obiettivi d'oro economici (solo ``resource1``):


.. list-table::
   :header-rows: 1

   * - Modello
     - Obiettivo
   * - Fast
     - 2000
   * - Standard
     - 3000
   * - Macro
     - 5000
   * - Lanes
     - 2500



Perdere tutti gli edifici ``provides_survival`` significa comunque sconfitta. Nelle modalità esplorazione/economica/sopravvivenza, eliminare tutti i nemici non fa vincere automaticamente; puoi comunque attaccare.

Tutte le modalità generano anche rovine antiche (ricompensa di risorse una tantum alla prima visita) e caserme catturabili (elimina le guardie, cattura, poi addestra unità).


----


3. Annuncio di generazione e F5/F6
------------------------------------


In modalità locale, quando la mappa è pronta il gioco annuncia:

- Mappa generata
- Seed (numero per riprodurre lo stesso layout)
- Codice di condivisione (stringa completa delle impostazioni)
- Premi F5 per ripetere (suggerimento della cronologia)

Il menu invita-IA che segue non cancella questo: F5 ripete il messaggio precedente, F6 scorre la cronologia vocale così puoi rivedere seed e codice di condivisione in qualsiasi momento.

I menu supportano le stesse scorciatoie di cronologia F5 / F6 della partita.


----


4. Codici di condivisione
--------------------------


4.1 Formato
~~~~~~~~~~~~


Esempio:

.. code-block:: text

   RMG1:f:m:2:med:b:r:f:v:hi:4242


Undici parti separate da due punti: prefisso ``RMG1`` + 10 campi:


.. list-table::
   :header-rows: 1

   * - Campo
     - Significato
     - Esempi
   * - Modello
     - standard / fast / macro / lanes
     - ``s`` / ``f`` / ``m`` / ``l``
   * - Dimensione
     - piccola / media / grande
     - ``s`` / ``m`` / ``l``
   * - Giocatori
     - 2–4
     - `2`
   * - Mostri
     - debole / media / forte
     - ``w`` / ``med`` / ``s``
   * - Risorse
     - bilanciata / raggruppata
     - ``b`` / ``c``
   * - Terreno
     - casuale / erba / palude / montagna
     - ``r`` / ``g`` / ``a`` / ``t``
   * - Squadre
     - ffa / teams_2v2
     - ``f`` / ``t``
   * - Acqua
     - nessuna / lago / fiume
     - ``n`` / ``l`` / ``v``
   * - Tesoro
     - nessuno / basso / alto
     - ``n`` / ``lo`` / ``hi``
   * - Seed
     - 0 = casuale; >0 fisso
     - `4242`



L'importazione accetta codici con o senza il prefisso ``RMG1:``; ``/`` funziona come separatore al posto di ``:``.

4.2 Importa codice di condivisione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Nel sottomenu del modello di mappa, scegli Importa codice di condivisione, digita o incolla il codice, Enter per confermare, Esc per annullare.

La casella di input supporta le scorciatoie di modifica standard (come altri campi ``input_string`` quali seed o login):


.. list-table::
   :header-rows: 1

   * - Scorciatoia
     - Azione
   * - Ctrl+A
     - Seleziona tutto
   * - Ctrl+C
     - Copia (tutto il testo se non c'è selezione)
   * - Ctrl+X
     - Taglia
   * - Ctrl+V
     - Incolla (caratteri non validi filtrati)
   * - Backspace / Delete
     - Elimina la selezione o il carattere prima/dopo il cursore



Lunghezza massima 80; caratteri consentiti: lettere, cifre, ``:``, ``/``, ``.``, ``-``.

In caso di successo senti un'anteprima e vai direttamente a Tregua (saltando i passi intermedi). I codici non validi mostrano Invalid share code e tornano al menu del modello.


----


5. Note sul multigiocatore
---------------------------


- Il comando `create_random …` dell'host viene applicato all'inizio della partita; tutti i client ottengono la stessa mappa deterministica da seed + impostazioni.
- I client non sentono l'annuncio locale «mappa generata + codice di condivisione»; condividi il codice prima di ospitare o fai importare lo stesso codice agli ospiti quando creano una stanza.
- Le partite pubbliche e i minuti di tregua seguono i soliti sottomenu di velocità / visibilità.


----


6. Confronto con `#random_choice` nei file mappa
-----------------------------------------------------


``#random_choice`` / ``#end_random_choice`` in un file mappa sono scelte del preprocessore tra alternative fisse (es. piazzamento casuale dell'oro). Non è l'RMG.

L'RMG genera l'intera mappa dai parametri, con seed e codici di condivisione per la riproduzione.


----


7. Sorgente
------------



.. list-table::
   :header-rows: 1

   * - Voce
     - Percorso
   * - Documentazione in gioco
     - ``doc/en/randommap.htm`` (menu principale → Documentazione → Guida alle mappe casuali)
   * - Generatore
     - ``soundrts/randommap.py``
   * - Menu
     - ``soundrts/randommap_menu.py``
   * - Test
     - ``soundrts/tests/test_randommap.py``
   * - Guida in cinese
     - [../../zh/player/随机地图功能说明.md](../../zh/player/随机地图功能说明.htm)
