Guida alla creazione di mappe
=============================

.. contents::

Introduzione
------------

Il modo migliore per iniziare è probabilmente creare una mappa multigiocatore e testarla contro il computer.

Mappe multigiocatore
--------------------

Dove salvare una nuova mappa multigiocatore
"""""""""""""""""""""""""""""""""""""""""""

Se si dispone dei permessi di scrittura nella cartella in cui SoundRTS (o SoundRTS test) è installato,
si può salvare la prima mappa multigiocatore nella cartella "multi".

Se non si dispone dei permessi di scrittura nella cartella dei file di programma perché si lavora in modalità non amministratore, si può salvare il file di mappa di lavoro nella cartella "multi"
in "C:\\Documents and Settings\\VostroUtente\\Application Data\\SoundRTS". Questa cartella viene creata la prima volta che si avvia SoundRTS, a meno che non esista una cartella "user" vicino a soundrts.exe.
Un'altra soluzione è installare SoundRTS in una cartella in cui si dispone dei permessi di scrittura e lavorare nella cartella menzionata nel paragrafo precedente.

Come modificare una mappa
"""""""""""""""""""""""""

Aprire il file con un editor di testo.
Scrivere in minuscolo, anche se in ogni caso le maiuscole saranno probabilmente ignorate.

Come testare una mappa
"""""""""""""""""""""""

Per testare una mappa, avviare SoundRTS e andare al menu partita singola. Si può giocare contro il computer sulle mappe multigiocatore.
La mappa viene ricaricata ogni volta che si avvia una partita, quindi non è necessario riavviare SoundRTS per testare le modifiche.
Una combinazione di tasti utile è Control Shift F2: se si è l'unico umano sulla mappa, si potrà esaminare l'intera mappa (senza nebbia di guerra).

Come trovare e rimuovere un errore
""""""""""""""""""""""""""""""""""

Se, avviando la mappa, si ottiene un messaggio di "errore nella mappa" e si torna al menu, a volte si possono trovare informazioni aggiuntive (ma criptiche) in "client.log" o in "server.log", di solito nella cartella "user/tmp".

Se ancora non si capisce dove sia l'errore, non esitate a contattarmi, direttamente o tramite la mailing list soundRTSChat.

Commenti
""""""""

Le righe che iniziano con un punto e virgola sono commenti. I commenti vengono ignorati durante l'esecuzione.
Anche tutto ciò che segue un punto e virgola fino alla fine della riga è un commento.

Proprietà di base
"""""""""""""""""

Titolo
'''''

"title 4018 5000" significa: "il titolo della mappa è il suono 4018 seguito dal suono 5000".

Obiettivo
'''''''''

"objective 145 88" significa: "l'obiettivo della mappa è il suono 145 seguito dal suono 88".

Nb_players_min e nb_players_max
'''''''''''''''''''''''''''''''

"nb_players_min 2" significa: "sono necessari 2 giocatori per avviare la partita."
"nb_players_max 4" significa: "4 giocatori in questa mappa è il massimo."

Global_food_limit
'''''''''''''''''

Nuovo nella versione beta 9e.

Aggiornamento nella versione beta 10 o: questo limite di cibo non viene più diviso tra i giocatori.

"global_food_limit 200" significa: "nessun giocatore può avere più di 200 di cibo, anche se costruisce più fattorie."

Definire il terreno
"""""""""""""""""""

Coordinate (dalla 1.4.1.8)
'''''''''''''''''''''''''''

Il sistema di coordinate usa ``x,y`` (ad es. ``1,1`` per la vecchia ``a1``). In modalità zoom, le coordinate
vengono ancora annunciate con le lettere. La notazione legacy è accettata e convertita::

    west_east_paths 1,3 2,3
    south_north_paths 1,1 2,1 3,1

Usare la notazione x,y per definire più di 26 colonne.

Square_width
''''''''''''

"square_width 12" significa: "la larghezza della cella è di 12 metri".
Non si dovrebbe modificare questo parametro, poiché gli oggetti potrebbero risultare inudibili se troppo lontani.

Dal 1.4.5.8, ``square_width`` è anche la capacità **per alleanza** di ``space`` delle unità su ogni strato
aria/terra/acqua (stesse unità: ``space 1`` → al massimo 12 per lato se ``square_width`` è 12; conteggio per alleanza dal 1.4.5.9). Vedi
``mod/modding.rst`` (Occupazione della casella).

Nb_lines e nb_columns
'''''''''''''''''''''

"nb_lines 7" significa: "la griglia ha 7 righe".
"nb_columns 7" significa: "la griglia ha 7 colonne".
La notazione con le lettere limita le colonne a 26 (``z``); usare le coordinate x,y per più colonne. Non c'è
un limite rigido per le righe, ma le prestazioni impongono un limite pratico.
Attenzione: nb_rows è deprecato e ha lo stesso significato di nb_columns.

West_east_paths e south_north_paths
'''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" significa: "aggiungi un percorso da a1 a b1, da c1 a d1, da d1 a e1 e da f1 a g1".
È sufficiente indicare la cella più a ovest del percorso.
"south_north_paths a1 a3 a4 a6" significa: "aggiungi un percorso da a1 a a2, da a3 a a4, da a4 a a5 e da a6 a a7".
È sufficiente indicare la cella più a sud del percorso.

West_east_bridges e south_north_bridges
'''''''''''''''''''''''''''''''''''''''

I ponti funzionano esattamente come i percorsi.

Caso generale: west_east e south_north
'''''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" significa: "aggiungi un'uscita con stile 'road' da a1 a b1, da c1 a d1, da d1 a e1"

'road' deve essere definito in style.txt

Nota: "west_east_paths" è equivalente a "west_east path"

Nota: "south_north_bridges" è equivalente a "south_north bridge"

Miniere d'oro, boschi e altri giacimenti di risorse
'''''''''''''''''''''''''''''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" significa: "aggiungi miniere d'oro con 150 d'oro in a2, b7, g6 e f1".

"wood 150 a2 b7 g6 f1" significa: "aggiungi boschi con 150 di legna in a2, b7, g6 e f1".

"goldmine" e "wood" sono definiti in rules.txt come giacimenti di risorse ("class deposit").

Le vecchie parole chiave plurali ("goldmines" e "woods") funzionano ancora.

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" significa: "riempi automaticamente la mappa con 2 prati in ogni cella".

Additional_meadows
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" significa: "aggiungi 1 prato nelle celle a2, b7, g6 e f1".
"additional_meadows a2 a2 g6" significa: "aggiungi 2 prati in a2 e 1 prato in g6".

Remove_meadows
''''''''''''''

remove_meadows fa l'opposto di additional_meadows.

Building_land (tipo di slot di costruzione predefinito)
'''''''''''''''''''''''''''''''''''''''''''''''''''''''

Le mappe possono scegliere quale tipo di oggetto ``nb_meadows_by_square`` riempie automaticamente::

    building_land build_site
    nb_meadows_by_square 2

- ``building_land meadow`` (predefinito): riempie automaticamente gli slot **meadow** (prato).
- ``building_land build_site``: riempie automaticamente gli slot **build_site** (neutro rispetto al tema, ad es. mod spaziali).

``additional_meadows`` e ``additional_build_sites`` continuano a posizionare esplicitamente quei tipi;
``remove_meadows`` rimuove solo gli oggetti ``meadow``.

Nb_<tipo>_by_square (tipi di building_land da rules)
'''''''''''''''''''''''''''''''''''''''''''''''''''

Schema di parole chiave della mappa: ``nb_<type>_by_square <count>``, dove ``<type>`` è il nome ``def``
di qualsiasi oggetto con ``class building_land`` in ``rules.txt``::

    nb_build_site_by_square 1
    nb_meadow_by_square 2
    nb_volcanic_rock_by_square 1

- Riempie **ogni cella** con quel numero di oggetti del tipo indicato.
- I tipi provengono dalle regole (le mod possono aggiungere ``def volcanic_rock`` + ``class building_land`` e usare
  ``nb_volcanic_rock_by_square``; nomi Unicode come ``nb_火山岩石_by_square`` funzionano se definiti nelle regole).
- Indipendente dalla riga ``building_land`` della mappa.
- Può coesistere con ``nb_meadows_by_square``; di solito se ne usa uno o l'altro.

La vecchia ``nb_meadows_by_square`` resta: il nome è storico; il tipo effettivo è controllato
da ``building_land`` (predefinito ``meadow``), non analizzando ``meadow`` dalla parola chiave.

Se la mappa omette ``building_land`` e usa solo una parola chiave ``nb_<type>_by_square``, quel tipo diventa ``world.building_land`` per la partita.

Al decollo o quando alcuni potenziamenti ripristinano il terreno edificabile sul posto, il motore usa **il tipo salvato quando l'edificio è stato posizionato** la prima volta; solo se manca, ricade sul predefinito della mappa sopra indicato.

Additional_build_sites
''''''''''''''''''''''

::

    additional_build_sites a2 b7

aggiunge uno **build_site** per ogni cella elencata (indipendente da ``building_land``).

Vedere ``building-land-terrain.htm`` per terreno, terreno edificabile ed esempi correlati.

High_grounds
''''''''''''

Nuovo in SoundRTS 1.2 alpha 9.

"high_grounds a2 b7" significa: "a2 e b7 avranno un'altitudine superiore"

Terreno a livello di sottocella (dalla 1.4.4.8)
'''''''''''''''''''''''''''''''''''''''''''''''

Il terreno può anche essere sovrascritto all'interno di una cella. Aggiungere ``/x,y`` dopo la coordinata
della cella, dove ``x`` e ``y`` sono coordinate a partire da 1 all'interno della cella::

    high_grounds a1/1,1 a1/1,2
    terrain mountain a1/2,2
    ground a1/2,2
    no_air a1/2,2

La griglia di sottocelle è controllata da ``subcell_precision``. Il valore predefinito è ``3``,
quindi ``a1/1,1`` indica la sottocella a nord-ovest di una suddivisione 3x3. L'intervallo
accettato è da 2 a 20::

    subcell_precision 20
    high_grounds a1/10,10 a1/10,11
    terrain mountain a1/1,1 a1/2,2 a1/3,3

I seguenti comandi di terreno accettano coordinate di sottocella: ``terrain``,
``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` e ``no_air``.
Le sottocelle non menzionate ereditano il terreno della cella genitore.

In modalità zoom, il browser della mappa annuncia il terreno della sottocella corrente. Se
``a1/1,1`` è terreno elevato e il resto di ``a1`` è terreno basso, navigare quella
sottocella annuncerà altopiano, mentre le altre sottocelle no.

Square_name (dalla 1.4.1.8)
'''''''''''''''''''''''''''

Assegnare un nome a celle o regioni::

    square_name normandy 2,2 verdun 20,23
    square_name normandy 2,2 2,3 3,3

Dalla 1.4.1.9, sono supportati fino a tre livelli gerarchici (provincia, città, distretto). Il TTS
annuncia i nomi quando si entra da un'altra regione; i livelli interni vengono omessi durante la navigazione
all'interno della stessa regione. Tradurre i nomi in ``tts.txt``::

    normandy = Normandy

Musica e suoni della mappa (dalla 1.4.0.2)
'''''''''''''''''''''''''''''''''''''''''

Nel file di mappa::

    map_music <id>
    map_battle_music <id>
    map_victory_sound <id>
    map_defeat_sound <id>


Definire le risorse iniziali dei giocatori
"""""""""""""""""""""""""""""""""""""""""""

Nota (dalla 1.4.1.8): le unità iniziali di fazione e le risorse possono anche essere definite in
``rules.txt``. Le definizioni della mappa hanno la priorità quando sono impostate entrambe.

Caso 1: stesse risorse per tutti
''''''''''''''''''''''''''''''''

Usare in combinazione i seguenti comandi:

starting_resources
..................

"starting_resources 10 10" significa: "ogni giocatore inizia con 10 d'oro e 10 di legna."

starting_units
..............

"starting_units townhall farm peasant" significa: "ogni giocatore inizia con 1 municipio, 1 fattoria e 1 contadino."

"starting_units townhall 2 farm peasant" significa: "ogni giocatore inizia con 1 municipio, 2 fattorie e 1 contadino."

starting_population
...................

"starting_population 60" significa: "ogni giocatore ottiene 60 di capacità popolazione extra in aggiunta
a quella fornita dagli edifici iniziali." È un intero semplice (non moltiplicato come le
risorse). Le righe ``player`` / ``computer_only`` per singolo giocatore possono anche includere
``population 60`` tra i token di unità solo per quello slot. ``available_population``
rimane comunque limitato da ``global_population_limit``.

Da SoundRTS 1.1, starting_units può anche contenere:

- potenziamenti e ricerche: "starting_units u_teleportation" significa: "ogni giocatore ha già la telepatricerca completata."
- unità, edifici, abilità, potenziamenti/ricerche proibiti (non compariranno nel menu):

  - "starting_units -u_teleportation" significa: "ogni giocatore non può ricercare la telepatricerca."
  - "starting_units -a_teleportation" significa: "ogni giocatore non può usare la telepatricerca."

starting_squares
................

"starting_squares a2 b7 g6 f1" significa: "le celle di partenza dei giocatori sono a2, b7, g6 e f1."

Le unità e gli edifici iniziali verranno creati in queste celle.

``starting_squares`` fissa solo quali celle usa ogni slot di generazione; per impostazione predefinita non fissa quale umano che si unisce ottiene quale slot (vedere random_starts_ e player_start_).

.. _random_starts:

random_starts
.............

``random_starts 1`` (predefinito): gli slot di generazione vengono mescolati tra i client umani all'avvio della partita. Le posizioni delle unità all'interno di ogni slot restano le stesse, ma l'assegnazione degli slot è casuale.

``random_starts 0``: gli slot vengono assegnati in ordine ai client 0, 1, 2…; il primo che si unisce ottiene sempre il primo slot.

.. _player_start:

player_start (dalla 1.4.2.8)
............................

Fissa il giocatore N (basato su 1, come ``trigger playerN``) a uno slot/cella. I giocatori fissati non partecipano mai al mescolamento di ``random_starts``; gli altri seguono comunque ``random_starts``.

Forma semplice — cambia solo la cella, mantenendo le risorse e le unità esistenti di quello slot::

    starting_squares a1 c1 e1
    starting_units townhall peasant
    player_start 1 b1

Forma completa — equivalente a fissare una riga ``player`` completa al giocatore N::

    player_start 1 5 10 a1 townhall peasant

Sono supportate anche coordinate e alias::

    player_start 1 2,3
    player_start 2 5,1

.. _spawn_semantics:

Semantica di generazione: player vs player_start
'''''''''''''''''''''''''''''''''''''''''''''''''

Entrambi possono posizionare unità/edifici su celle specifiche (ad es. ``a1``), ma non indicano lo stesso tipo di "generazione fissa":

- ``player`` / ``starting_squares``: definiscono gli slot di generazione e i loro contenuti. Le coordinate delle celle sono fisse, ma con ``random_starts 1`` quale umano ottiene quale slot viene mescolato.
- ``player_start``: fissa il giocatore N allo slot N (e può cambiare la cella di quello slot), indipendentemente da ``random_starts``.

Pattern comuni:

Configurazioni diverse per giocatore, e il giocatore 1 deve sempre iniziare in basso a sinistra:

    random_starts 1
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant
    player_start 1 a1
    player_start 2 h1

Solo righe player, fissate in base all'ordine di inserzione (player_start non necessario):

    random_starts 0
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant

Configurazione di partenza condivisa, solo alcuni giocatori fissati:

    starting_squares a1 c1 e1 g1
    starting_units townhall peasant
    player_start 1 a1
    player_start 3 e1

Trappole comuni:

- In ``player 5 10 …``, i primi due numeri sono quantità di risorse (oro/legna), non un indice di giocatore o coordinate.
- Per fissare "quale chiave entra in quale angolo", usare ``player_start`` o ``random_starts 0``; ``starting_squares`` / ``player`` da soli non bastano.

Caso 2: risorse diverse a seconda del giocatore
'''''''''''''''''''''''''''''''''''''''''''''''

player
......

Il comando "player" definisce un punto di partenza che può essere usato da un giocatore umano o da un'IA del computer (nelle partite multigiocatore).

Questo comando può essere ripetuto più volte in una mappa multigiocatore.

"player 5 10 -townhall a1 townhall peasant c1 footman"
significa: "un giocatore inizierà con 5 d'oro, 10 di legna, non potrà costruire un municipio, avrà un municipio e un contadino in A1, un fante in C1."

Ogni riga ``player`` aggiunge uno slot di generazione nell'ordine della mappa; ``a1``, ``c1``, ecc. sono coordinate di cella. Per fissare uno slot al giocatore N, usare player_start_ o impostare random_starts 0 (vedere spawn_semantics_ sopra).


Elenco dei tipi
'''''''''''''''

Ecco alcuni nomi corretti di tipi usati in starting_units_, player_ e computer_only_.
Per un elenco completo, esaminare il file rules.txt: il nome si trova subito dopo l'istruzione "def".

- unità: peasant footman archer knight catapult dragon mage priest necromancer
- edifici: farm barracks lumbermill blacksmith townhall stables workshop dragonslair magestower
- abilità: a_teleportation
- potenziamento/ricerca: u_teleportation melee_weapon


Aggiungere mostri
"""""""""""""""""

Aggiungere un punto di partenza computer_only
'''''''''''''''''''''''''''''''''''''''''''''

.. _computer_only:

Il comando "computer_only" definisce un punto di partenza che sarà sempre giocato da un'IA del computer. Questa IA sarà ostile a qualsiasi altro giocatore o IA.

Questo comando può essere ripetuto più volte ma attenzione: troppe IA possono rallentare la partita.
Quindi usare una sola IA se queste unità non dovrebbero combattere tra loro (diversi draghi sparsi per la mappa ad esempio).

computer_only 0 0 a3 dragon b1 dragon
significa: "aggiungi un'IA del computer con 0 oro, 0 legna, un drago in A3 e un drago in B1."

Computer neutrali (dalla 1.4.2.8)
..................................

Aggiungere la parola chiave ``neutral`` in modo che l'IA non attacchi finché non viene attaccata per prima::

    computer_only 0 0 neutral a3 peasant b1 footman

Senza ``neutral``, il computer è ostile verso tutti.

Le unità del giocatore in modalità offensiva, difensiva o di inseguimento non attaccheranno automaticamente
questi neutrali e non fuggiranno da loro in modalità difensiva; solo un attacco forzato (imperativo) avvia il combattimento.

Slot solo fauna (dalla 1.4.3.7)
...............................

Se una riga ``computer_only`` contiene solo animali con ``is_huntable`` / ``herdable`` (ad es. ``deer``, ``sheep``, ``tiger`` personalizzato), quello slot non si unisce all'alleanza predefinita ``"ai"`` e non si allea con altri branchi, giocatori o creep ostili. Ogni riga ``computer_only`` è un punto di caccia indipendente.

Se la stessa riga mescola animali e fanti, l'intero slot resta una IA normale. Vedere ``../player/hunting.htm`` §3.1.


Aggiungere trigger per far muovere i mostri
'''''''''''''''''''''''''''''''''''''''''''

Importante: aggiungere i trigger multigiocatore predefiniti
...........................................................

Se una mappa multigiocatore definisce almeno un trigger, i trigger multigiocatore predefiniti vengono ignorati. Lo scopo è consentire condizioni di vittoria personalizzate.

Per mantenere le condizioni di vittoria predefinite, i seguenti trigger devono essere aggiunti esplicitamente alla mappa (altrimenti la partita non si fermerà automaticamente)::

    trigger players (no_enemy_player_left) (victory)
    trigger players (no_building_left) (defeat)
    trigger computers (no_unit_left) (defeat)

Nota: il terzo trigger non è strettamente necessario.

Condizioni di vittoria e sconfitta (dalla 1.4.0.1)
..................................................

Condizioni di trigger aggiuntive::

    trigger all (unit_lost knight) (defeat)
    trigger player1 (unit_lost a1 3 footman) (defeat)
    trigger player1 (building_lost 1 townhall) (defeat)
    trigger player1 (key_unit_killed a1 3 footman) (defeat)
    trigger all (key_unit_killed hero) (defeat)
    trigger all (key_units_killed 5 knight) (defeat)
    trigger all (units_lost 3 knight) (defeat)
    trigger all (building_lost townhall) (defeat)
    trigger all (buildings_lost 1 townhall 2 barracks) (defeat)
    trigger players (killed_target dragon) (victory)
    trigger players (killed_target dragon enemy) (victory)
    trigger player1 (has_killed 5 footman enemy) (objective_complete 1)
    trigger player1 (has_killed 1 footman 3 knight enemy) (objective_complete 2)

``killed_target`` e ``has_killed`` accettano ``enemy`` o ``ally`` opzionale per contare solo
quelle unità.

Selettori di indice unità (dalla 1.4.3.1, demo: The Legend of Raynor capitolo 28) — stessa
sintassi ``\<square\> \<index\> \<type\>`` di ``transfer_units``; identifica l'N-esima unità di
quel tipo generata nella cella (stabile dopo il movimento)::

    trigger player1 (killed_target c3 3 demo_marker_footman enemy) (objective_complete 1)
    trigger player1 (killed_target c3 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Indice ``killed_target``: `` (killed_target \<square\> \<index\> \<type\> [enemy|ally])``.
Indice ``npc_has_item``: `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``.
Indice ``unit_lost`` / ``building_lost`` / ``key_unit_killed``: `` (\<square\> \<index\> \<type\>)`` — solo quella unità/edificio generato (ad es. proteggere il municipio iniziale).
Non equivale a ``has_killed 3 footman`` (conteggio totale). Il ``cut_scene`` di ciascun obiettivo dovrebbe
descrivere solo quell'obiettivo. Vedere ``campaign/unit-index.htm``; esempi
``res/single/The Legend of Raynor/28.txt``, ``1.txt``.

Trigger di missioni con oggetti (dalla 1.4.3.1)
..............................................

has_item — il giocatore ha raccolto un oggetto missione (controlla gli inventari di tutte le unità viventi)::

    trigger player1 (has_item lost_amulet) (objective_complete 1)
    trigger player1 (has_item health_potion 2) (objective_complete 2)

L'oggetto deve essere ``class item`` con ``consume_on_pickup`` non impostato a 1 (predefinito 0), così
resta nell'inventario dopo la raccolta. Posizionare gli oggetti sulla mappa come le unità::

    lost_amulet c3
    health_potion 2 a2

Differenze tra condizioni correlate:

- ``has``: conteggi unità del giocatore (``self.units``)
- ``has_item``: oggetti negli inventari delle unità del giocatore (trovati/raccolti ovunque)
- ``npc_has_item``: un NPC ha ricevuto un oggetto (inventario o ``received_items``); forma con indice ``\<square\> \<index\> \<type\> \<item\>`` (capitolo 28)
- ``find``: un oggetto esiste a terra in una cella (cella prima del tipo, ad es. ``c3 mana_potion``); l'oggetto deve di solito essere lasciato cadere
- ``has_brought_item``: un'unità del giocatore che trasporta un oggetto è arrivata in una cella (l'oggetto resta nell'inventario)
- ``remove_item``: azione di trigger che elimina un oggetto dagli inventari del giocatore (consegna narrativa)
- ``remove_ground_item``: azione di trigger che elimina oggetti a terra in una cella
- ``do``: azione di trigger che esegue più sotto-azioni in ordine
- ``and``: condizione di trigger vera solo quando ogni sotto-condizione è vera

has_brought_item — trasportare un oggetto missione in una cella (conta l'inventario; non richiede di lasciar cadere)::

    trigger player1 (has_brought_item c3 mana_potion) (objective_complete 1)

Sintassi: ``(has_brought_item \<square\> \<item_type_name\> [count])``

remove_item — rimuovere e distruggere oggetti dagli inventari del giocatore (consegna narrativa)::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintassi: ``(remove_item \<item_type_name\> [square] [count])``

Flusso tipico: ``has_brought_item`` → ``cut_scene`` → ``remove_item`` → ``objective_complete``.
Esempio: The Legend of Raynor capitolo 18.

do — eseguire più azioni di trigger in ordine::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintassi: ``(do \<action1\> \<action2\> ...)``

``if`` ha solo due rami (if/else). Usare ``do`` quando servono tre o più azioni
(cutscene, rimuovere oggetto, completare obiettivo, ecc.).

remove_ground_item — eliminare oggetti a terra in una cella::

    trigger player1 (find b2 mystery_treasure)
        (do (cut_scene 7546) (remove_ground_item b2 mystery_treasure)
            (add_units b2 10 gold_coin) (objective_complete 2))

Sintassi: ``(remove_ground_item \<square\> \<item_type_name\> [count])``

``remove_item`` rimuove dagli inventari del giocatore; ``remove_ground_item`` rimuove
dal suolo in una cella (ad es. dopo che il giocatore lascia cadere un oggetto missione per aprire un forziere).

and — tutte le sotto-condizioni devono essere vere::

    trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin)))
        (objective_complete 3)

Sintassi: ``(and \<condition1\> \<condition2\> ...)``

Una riga di trigger ha un'espressione di condizione. Racchiudere più condizioni in ``and``; non
scrivere ``(cond1) (cond2) (action)`` (la seconda S-expression diventa l'azione).

Per ``find``, mettere sempre la cella prima del tipo, anche dentro ``not``.
Sbagliato: ``(not (find gold_coin b2))`` (controlla prima la cella predefinita, quasi sempre vero).
Corretto: ``(not (find b2 gold_coin))``. Esempio di lascia-e-apri: The Legend of Raynor capitolo 22; uso dell'inventario: capitolo 20.

npc_has_item — un NPC ha ricevuto un oggetto specifico (inventario o record ``received_items``)::

    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Sintassi (entrambe le forme):

- Classica: ``(npc_has_item \<NPC_selector\> \<item_type_name\> [square])``
- Con indice: ``(npc_has_item \<square\> \<index\> \<unit_type\> \<item_type_name\>)`` — come
  ``transfer_units``; l'N-esima unità in quella cella per ordine di generazione. Esempio: capitolo 28.

Forma classica:

- ``\<NPC_selector\>``: ``type_name`` della unità o id della unità.
- ``\<item_type_name\>``: ad es. ``health_potion``.
- `````[square]``` opzionale: limita agli NPC attualmente in quella cella.

La forma con indice corrisponde per indice di generazione; l'unità può essersi allontanata da quella cella.

give negli ordini di trigger (consegna scriptata)::

    trigger player1 (timer 5) (order (a1 1 peasant) ((give c3 health_potion)))

Esempio di mappa trova-oggetto (The Legend of Raynor capitolo 17)::

    title Find the lost amulet
    lost_amulet c3
    starting_squares a1
    starting_units peasant
    trigger player1 (timer 0) (add_objective 1 "find the lost amulet")
    trigger player1 (has_item lost_amulet) (objective_complete 1)

Esempio di mappa consegna-a-NPC (``res/multi/give_demo.txt``)::

    health_potion a1
    computer_only 0 0 neutral c3 quest_npc
    trigger player1 (timer 0) (add_objective 1 "deliver the potion to the quest npc")
    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)

Esempi della campagna (``The Legend of Raynor``): cap. 14 consegna ``pickaxe`` all'alleato ``npc_peasant``;
cap. 15 consegna ``knight_lance`` al neutrale ``npc_knight``; cap. 16 consegna ``wand`` al nemico
``npc_mage`` (relazioni ``ally``/``neutral``/``enemy``). Vedere ``res/single/The Legend of Raynor/14.txt``,
``15.txt``, ``16.txt``. Demo multigiocatore: ``res/multi/give_demo.txt``.

Alleanze di campagna e trasferimento di unità (dalla 1.4.3.1)
............................................................

La diplomazia dinamica con F12 non funziona nelle campagne. Dopo ``alliance_request``, l'umano
accetta con Ctrl+F4 e rifiuta con Shift+F4 (nessuna selezione del bersaglio con F12). Vedere
``../player/campaign-northern-arc.htm`` per l'intero arco settentrionale (cap. 24–27).

alliance_request — azione di trigger: un giocatore richiede alleanza con un altro::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (cut_scene 7585) (alliance_request computer1) (objective_complete 1))

Sintassi: ``(alliance_request \<from\> [to])``; se ``to`` è omesso, la richiesta va al
proprietario del trigger.

alliance_with — condizione: il proprietario del trigger è alleato con il giocatore indicato::

    trigger player1 (alliance_with computer1) (objective_complete 2)

alliance_declined_with — condizione: richiesta di alleanza rifiutata dal giocatore indicato (campagna Shift+F4)::

    trigger player1 (alliance_declined_with computer1)
        (do (cut_scene 7598) (add_units c3 3 knight) (objective_abandon 1))

add_secondary_objective — azione di trigger: aggiunge un obiettivo opzionale (annunciato con il
prefisso "obiettivo opzionale"). La numerazione è indipendente dagli obiettivi primari (entrambi
iniziano da 1)::

    trigger player1 (timer 0) (add_objective 1 7583)
    trigger player1 (timer 0) (add_objective 2 7584)
    trigger player1 (timer 0) (add_secondary_objective 1 7599)

secondary_objective_complete — azione di trigger: completa l'obiettivo opzionale N (non
influenza l'obiettivo primario N)::

    trigger player1 (alliance_with computer1)
        (do (cut_scene 7586) (allied_assist computer1) (secondary_objective_complete 1))

objective_abandon — azione di trigger: abbandona l'obiettivo opzionale N (ad es. rifiuto alleanza);
si applica solo a ``add_secondary_objective``.

alliance_request_pending — condizione: una richiesta di alleanza in sospeso dal giocatore indicato.

transfer_units / convert_units / change_owner — azione di trigger: cambia la proprietà
delle unità da un giocatore a un altro (non genera unità come ``add_units``)::

    trigger player1 (alliance_with computer1)
        (do (transfer_units computer1 player1) (add_objective 2 7584))

Senza selettore di unità, tutte le unità viventi del giocatore sorgente vengono trasferite.
La sintassi del selettore corrisponde a ``order`` / ``add_units``: ``\<square\> \<count\> \<type\>``.

allied_assist — azione di trigger: lascia che le unità dell'alleato combattano per conto proprio
(guardia→inseguimento); non concede il comando al giocatore::

    trigger player1 (alliance_with computer1)
        (do (allied_assist computer1))

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (allied_assist computer1 c2 4 npc_archer_escort))

Sintassi:

- Intero alleato: ``(allied_assist \<ally\>)``
- Solo unità selezionate: ``(allied_assist \<ally\> \<square\> \<count\> \<type\> ...)``

La sintassi del selettore di unità corrisponde a ``transfer_units`` / ``add_units``. Senza selettore, tutte
le unità da combattimento in guardia passano a inseguimento; con un selettore, solo le unità corrispondenti
cambiano; le altre restano invariate.

allied_control — azione di trigger: consente a un giocatore di comandare direttamente le unità di un
alleato (selezionare, muovere, attaccare)::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (alliance 1) (allied_control computer1 c2 4 npc_knight_escort))

Sintassi:

- Intero alleato: ``(allied_control \<ally\> [controller])``
- Solo unità selezionate: ``(allied_control \<ally\> [\<controller\>] \<square\> \<count\> \<type\> ...)``

Senza selettore, tutte le unità viventi dell'alleato vengono concesse e passano a inseguimento. Con un
selettore, solo le unità corrispondenti vengono concesse (restano in guardia finché il giocatore non ordina);
le unità da combattimento non corrispondenti in guardia passano a inseguimento automaticamente.

add_inventory_item — inserisce un oggetto nell'inventario di una unità (ricompensa missione,
riconcessione tra capitoli)::

    trigger player1 (has_killed 3 traitor_guard)
        (do (cut_scene 7580) (add_inventory_item garrek_token 1 raynor) (set_campaign_flag ch24_garrek_token))

Sintassi: ``(add_inventory_item \<item_type\> [\<count\>] [\<unit_type\>])``; se l'unità è omessa, la
prima unità amica con ``inventory_capacity`` (la campagna di Raynor usa i tipi ``raynor`` come predefinito).

Avanzamento tra capitoli (tre meccanismi)
.........................................

.. list-table::
   :header-rows: 1

   * - Meccanismo
     - Configurazione
     - Trasporta
   * - ``campaign_carryover``
     - campi unità in ``rules.txt``
     - Livello+XP, inventario
   * - 
     - 
     - (split; vedere modding.rst)
   * - ``campaign_flag`` /
     - trigger di mappa
     - booleani narrativi
   * - ``set_campaign_flag``
     - 
     - 
   * - ``add_inventory_item``
     - trigger di mappa
     - oggetti specifici


``campaign_flag`` persiste in ``campaigns.ini`` ``flags``; ``map_flag`` è solo per mappa.

Riconcessione all'avvio del capitolo::

    trigger player1 (timer 0) (if (campaign_flag ch24_garrek_token) (do (add_inventory_item garrek_token 1 raynor)))

unset_campaign_flag cancella i flag persistiti per errore.

set_ai_mode — cambia la modalità IA sulle unità del proprietario del trigger::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Sintassi: ``(set_ai_mode \<offensive|defensive|guard|chase\> [\<square\> \<count\> \<type\> ...])``.

set_yield_on_defeat — attiva/disattiva la resa per unità (HP a zero → si arrende invece di morire)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Sintassi: ``(set_yield_on_defeat \<0|1\> [\<square\> \<count\> \<type\> ...])``. Si può anche impostare ``yield_on_defeat 1`` in ``rules.txt``.

units_yielded — conteggio di unità nemiche arrese::

    trigger player1 (units_yielded 1 npc_marco_ironhand) (objective_complete 1)

units_yielded_by — resa forzata da un attaccante specifico (supporta ``is_a``)::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy) (objective_complete 1)

has_entered — unità del proprietario del trigger sono entrate in una cella (griglia o alias di toponimo;
tipo unità opzionale)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

map_flag / set_map_flag — flag per sessione di mappa (non salvati nella configurazione campagna)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

stop_all_units / release_yielded_units — cessate il fuoco e fine dell'invulnerabilità da resa::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy)
        (do (cut_scene 7710) (alliance 1 player1 computer1) (stop_all_units) (release_yielded_units computer1))

Eseguire ``cut_scene`` sui trigger di player1 in modo che il client umano ascolti la voce. Le modalità IA /
i toggle di resa possono girare su computer1 (proprietario delle unità).

L'arco settentrionale di The Legend of Raynor (cap. 24–27): storia continua con obiettivo condiviso
``traitor_guard`` e propagazione tramite ``campaign_flag``. Vedere ``../player/campaign-northern-arc.htm``:

- cap. 24 (lettera a Garrek): ``allied_control``; ``add_inventory_item garrek_token`` dopo la morte dei traditori
- cap. 25 (token a Roland): uccidibile prima della consegna; poi ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``
- cap. 26 (stendardo a Vera): ``transfer_units``
- cap. 27 (duello con Marco): ``has_entered c2 raynor7`` + cutscene 7718; solo Marco ``set_ai_mode offensive``;
  scorte in ``order`` verso ``c1`` per liberare l'arena; ``units_yielded_by raynor7``; ``stop_all_units`` +
  ``allied_control`` selettivo (4 cavalieri di scorta)

Il capitolo 25 deve registrare tre obiettivi primari (consegnare token, sconfiggere Roland, uccidere
traditori) più l'obiettivo opzionale 1 (alleanza) all'inizio. Premere F9 per gli obiettivi primari e
opzionali. I computer script si mostrano come NPC (``Player.name`` + ``is_script_npc``).

Gli NPC chiave (``npc_count_roland``, ``npc_roland_guard``, ecc.) dovrebbero iniziare con ``ai_mode guard``.
Attivare ``yield_on_defeat`` a runtime tramite ``set_yield_on_defeat``, non nelle regole alla generazione,
così Roland è uccidibile prima della consegna del token.


Pattuglia
........

Per ordinare a fino a 10 draghi da d1 di pattugliare tra d1 e d9::

    trigger computer1 (timer 0) (order (d1 10 dragon) ((patrol d9)))


Attacco a un momento specifico
..............................

Per ordinare a fino a 10 draghi da e3 di attaccare b2 dopo 20 minuti (velocità normale)::

    timer_coefficient 60
    trigger computer1 (timer 20) (order (e3 10 dragon) ((go b2)))


Passare a un'altra IA
.....................

L'IA predefinita per computer_only è un'IA solo trigger, che non fa nulla. Per passare a "easy"
(anche nota come "computer silenzioso")::

    trigger computer1 (timer 0) (ai easy)


Aggiungere unità
...............

Per aggiungere 10 draghi in A1::

    trigger computer1 (timer 0) (add_units a1 10 dragon)


#random_choice, #end_choice e #end_random_choice
"""""""""""""""""""""""""""""""""""""""""""""""
(nuovo in beta 9g)
Questa direttiva del preprocessore sceglie casualmente tra 2 o più alternative delimitate da #random_choice,
#end_choice e da #end_random_choice per l'ultima scelta.
Ogni scelta consiste in zero o più righe.
Più direttive #random_choice possono essere usate in un file di mappa, ma non possono essere annidate.

Questo può essere usato ad esempio per posizionare risorse casuali. Ad esempio::

 #random_choice
 goldmines 500 e2 c6 b3 f5
 #end_choice
 goldmines 500 d2 d6 b4 f4
 #end_choice
 goldmines 500 c2 e6 b5 f3
 #end_random_choice

Le righe precedenti significano: "aggiungi una miniera d'oro in e2, c6, b3 e f5, oppure in d2, d6, b4 e f4, oppure in c2, e6, b5 e f3". In questo modo le risorse sono bilanciate (se non ho fatto un errore, ovviamente). È solo un esempio.

Il titolo della mappa e il numero di giocatori non possono essere cambiati in questo modo perché il preprocessore viene eseguito quando la mappa viene caricata (cioè molto tempo dopo che il menu partita singola è stato caricato).

Mappe multigiocatore avanzate: come cambiare le regole e l'aspetto del gioco
----------------------------------------------------------------------------

Struttura della mappa
"""""""""""""""""""""

La mappa avanzata è una cartella contenente un file chiamato "map.txt" con il contenuto di una mappa usuale, e la maggior parte dei file e cartelle che si trovano nella cartella "res":
rules.txt, ai.txt, le cartelle ui e il loro contenuto.

Nota: al momento, in una cartella di mappa o di campagna, la versione localizzata di style.txt (ad esempio: ui-fr/style.txt) non viene caricata.
I suoni localizzati vengono però caricati.

Campagne partita singola
------------------------

Dove salvare una nuova campagna partita singola
"""""""""""""""""""""""""""""""""""""""""""""""

Se si dispone dei permessi di scrittura nella cartella in cui SoundRTS (o SoundRTS test) è installato, si può salvare la prima campagna nella cartella "single".

Se non si dispone dei permessi di scrittura nella cartella dei file di programma perché si lavora in modalità non amministratore, si può salvare il file di mappa di lavoro nella cartella "single"
in "C:\\Documents and Settings\\VostroUtente\\Application Data\\SoundRTS". Questa cartella viene creata la prima volta che si avvia SoundRTS.
Un'altra soluzione è installare SoundRTS in una cartella in cui si dispone dei permessi di scrittura e lavorare nella cartella menzionata nel paragrafo precedente.

Struttura della cartella della campagna
"""""""""""""""""""""""""""""""""""""""

Il nome della cartella della campagna sarà usato dal menu partita singola. Le campagne ufficiali avranno il proprio titolo nella cartella "ui".
La cartella contiene i file dei capitoli. Contiene anche file e cartelle che imitano la struttura della cartella "res": rules.txt, ai.txt, ui...

File delle mod richieste
'''''''''''''''''''''''

Nuovo in SoundRTS 1.2 alpha 10.

Una campagna può definire quali mod richiede. Le mod richieste saranno caricate automaticamente.

Le mod richieste sono definite in un file chiamato "mods.txt", nella cartella della campagna:

- il file è un elenco separato da virgole di nomi di mod;
- se il file non esiste, verranno mantenute le mod correnti;
- se il file è vuoto, verrà caricato il gioco "vanilla".

File dei capitoli
'''''''''''''''''

I file dei capitoli sono file di testo chiamati "0.txt", "1.txt", "2.txt", ecc. Quando una campagna viene avviata per la prima volta, è disponibile solo il capitolo 0. Quando un capitolo è terminato, si può eseguire il capitolo successivo. Il numero del capitolo più alto disponibile viene automaticamente memorizzato nel file di configurazione del giocatore chiamato campaigns.ini.

Un file di capitolo descrive un capitolo missione o un capitolo cutscene.

Deve esistere almeno un file di capitolo, chiamato "0.txt".

Sintassi di un file di capitolo
"""""""""""""""""""""""""""""""

Un capitolo è una missione o una cutscene.

Sintassi di un file di capitolo missione
'''''''''''''''''''''''''''''''''''''''''
Un file missione non è molto diverso da una mappa multigiocatore.
È ammessa anche la struttura di mappa avanzata: in quel caso, il nome della cartella è il numero del capitolo.

Campagna cooperativa (dalla 1.4.2.2; stile AoE DE dalla 1.4.4.4+): dichiarare
``coop_campaign`` / ``coop_intro`` / ``coop_missions`` in ``campaign.txt``;
opzionale ``hero_min_level 13:2 16:3 …`` (livelli minimi del eroe tra capitoli; vedere ``modding.rst``);
partita singola e cooperativa caricano la stessa mappa missione ``N.txt`` (non spedire
``N.coop.txt``). Vedere ``mod/coop-campaign.htm`` e
``player/campaign-and-co-op-improvements.htm``.

Le missioni co-op impostano ``nb_players_min`` / ``nb_players_max`` e più blocchi ``player``
in ``N.txt``; su un server, qualsiasi giocatore che completa obiettivi contribuisce
alla squadra. La partita singola registra comunque un umano e usa solo la prima generazione.

Nelle campagne, F12 (alleanza dinamica) non seleziona alcun bersaglio. I computer con script trigger
vengono annunciati come "NPC" invece dei nomi interni come ``ai_timers``.

Intro
.....

Nota: un numero può rappresentare un messaggio di testo definito in tts.txt (nuovo in SoundRTS 1.2 alpha 9).

Esempio: "intro 7500 7501 7502" significa: "prima che la partita inizi, riproduci 7500.ogg, 7501.ogg e 7502.ogg (o testo se definito in tts.txt)".
Il comando intro definisce una sequenza di suoni e testi che verrà riprodotta prima dell'inizio della partita. Quando il giocatore preme un tasto, viene riprodotto l'elemento successivo della sequenza. Un intro può essere ad esempio un titolo con musica, poi una scena con una discussione tra personaggi, poi un briefing. Dopo l'intro, il gioco comunicherà gli obiettivi della missione.

Add_objective
.............

"add_objective player1 1 7000" significa: "aggiungi l'obiettivo primario numero 1 con il suono 7000.ogg"

"add_secondary_objective player1 1 7599" significa: "aggiungi l'obiettivo opzionale numero 1" (la missione
si può vincere senza completarlo). Obiettivi primari e opzionali usano numerazioni indipendenti
(entrambi possono iniziare da 1; primario 1 e opzionale 1 possono coesistere).

Tutti gli obiettivi primari devono essere completati per vincere. Usare ``secondary_objective_complete`` per
segnare un obiettivo opzionale come completato, o ``objective_abandon`` per abbandonarlo. Se un obiettivo
primario fallisce (ad es. muore un personaggio importante), la missione è persa.

Register_objective (azione in un trigger)
.........................................

``register_objective`` registra i numeri degli obiettivi primari necessari per la vittoria senza
mostrarli nell'elenco F9 né riprodurre la voce "nuovo obiettivo".

Sintassi (dentro un'azione di trigger)::

    register_objective 1 2 3

Perché usarlo: se si concatenano ``add_objective`` su più trigger (rivela l'obiettivo 2 solo
dopo il completamento dell'obiettivo 1), ogni ``add_objective`` aggiunge anche quel numero all'insieme di vittoria.
Completare l'obiettivo 1 potrebbe altrimenti innescare una vittoria prematura quando gli obiettivi 2–N
non sono ancora stati aggiunti.

Pattern di rivelazione progressiva — a ``timer 0``, registrare tutti i numeri, poi mostrare solo il primo
obiettivo; a ogni completamento, ``objective_complete`` + ``add_objective`` per il successivo::

    trigger player1 (timer 0) (do (register_objective 1 2) (add_objective 1 7510))
    trigger player1 (has 4 pylon) (do (objective_complete 1) (add_objective 2 7511))
    trigger player1 (has_entered f1 gateway) (objective_complete 2)

Logica di vittoria: il motore mantiene ``\_required_objective_numbers`` (da ``register_objective``
e ``add_objective``) e ``\_completed_objective_numbers`` (da ``objective_complete``).
La vittoria della missione scatta quando ogni numero richiesto è completato — indipendentemente dal fatto
che un obiettivo sia ancora visibile in F9.

Numerazione F9 / voce: quando esistono più obiettivi primari (registrati o già mostrati),
F9 e ``add_objective`` annunciano "Obiettivo primario N:" prima della descrizione; con un
singolo obiettivo primario il numero viene omesso. Vedere ``soundrts/objective_announce.py``.

Esempi: ``mods/starcraft/single/sc_build_tests/1.txt`` (2 obiettivi); ``sc_late_game/1.txt`` (6
obiettivi concatenati). Guida: ``campaign/progressive-objectives.htm``.

Objective_complete (azione in un trigger)
.........................................

Questa azione può essere inclusa solo nella parte azione di un trigger.

"objective_complete 1" significa: "l'obiettivo primario 1 è ora completato".

Secondary_objective_complete (azione in un trigger)
..................................................

``objective_complete 1`` influisce solo sugli obiettivi primari. Per completare un obiettivo opzionale, usare::

    secondary_objective_complete 1

che significa: "l'obiettivo opzionale 1 è ora completato".

Esempio di trigger:

"trigger player1 (has barracks) (objective_complete 2)" significa: "aggiungi il seguente trigger per player1: se possiede almeno 1 caserma allora l'obiettivo 2 è completato"

Coefficiente timer
..................

Un coefficiente timer può essere usato per misurare il tempo dei trigger in un dato blocco.

Ad esempio, se si sa che si vogliono far accadere tutti i trigger in blocchi di mezzo minuto, si può impostare il coefficiente timer a 30 in questo modo.

"timer_coefficient 30"

Ogni volta che questa quantità di tempo trascorre, il contatore timer viene incrementato (aumenta di 1). Si possono poi collegare i trigger al raggiungimento di un dato numero da parte del timer. Ad esempio, se si vogliono far apparire rinforzi sulla mappa dopo 90 secondi (3 incrementi di 30 secondi), si procede come segue.

"trigger player1 (timer 3) (add_units a1 10 footman)" ; dopo tre scatti del timer, dai al giocatore 10 fanti in a1

Cut_scene (azione in un trigger)
................................

Nota: la distinzione tra suoni in streaming e suoni precaricati è stata rimossa in SoundRTS 1.2. Tutti i suoni vengono precaricati.

Nota: un numero può rappresentare un messaggio di testo definito in tts.txt (nuovo in SoundRTS 1.2 alpha 9).

Una cutscene può essere innescata a metà partita: quando si scopre qualcosa, quando arrivano rinforzi, ecc.

"cut_scene 7500 7501" significa: riproduci la cutscene composta dai suoni 7500 e 7501.

Esempio di trigger:

"trigger player1 (has_entered d5) (cut_scene 7500)" significa: "aggiungi il seguente trigger per player1: se è entrato nella cella d5, riproduci la cutscene composta dal suono 7500.ogg"

Timer e timer_coefficient (condizione in un trigger)

"timer_coefficient 60"

'trigger player1 (timer 2) (cut_scene 7500)" significa: "dopo 2 minuti (2 x 60 secondi) riproduci il file sonoro 7500.ogg."

Ordini all'IA
.............

È possibile controllare le azioni del computer in una missione, per aggiungere sfida. Bisogna far sì che le sue unità prendano ordini a determinati trigger.

Ad esempio, possiamo far muovere le forze IA in A1 verso la posizione nota del giocatore in A3, che ingaggerà le forze del giocatore quando le incontrerà. Qui lanceremo un attacco con 10 fanti contro il giocatore.

"timer_coefficient 60"

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1)))"

Il posizionamento delle parentesi qui è importante, per incapsulare i comandi giusti nelle parti giuste di questo trigger. Se per qualche motivo il trigger non sembra funzionare, provare a ricontrollare le parentesi.

È anche possibile accodare ordini perché le unità indicate li seguano. In questo scenario, immaginiamo che il giocatore abbia la base distribuita su a1 e b1. Dobbiamo quindi dire ai fanti di andare a b1 una volta finito con a1. Lo faremo così.

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1)))"

Infine, se si vuole che le unità IA entrino in modalità "auto_attack", dove daranno la caccia a ogni unità superstite del giocatore dopo aver ripulito la base, si può fare anche questo.

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1) (auto_attack)))"

Si possono usare gli ordini per far addestrare al computer anche le proprie unità, che possono poi diventare oggetto di ordini successivi. Qui diremo alle caserme del computer di addestrare immediatamente altri 10 fanti per rimpiazzare quelli che stiamo per mandare ad attaccare il giocatore.

trigger computer1 (timer 0) (order (a1 barracks) ((train footman) (train footman) (train footman))) ; e così via finché non si hanno 10 ordini train footman

Notare che ogni ordine di addestramento deve essere separato, non si può fare quanto segue: (train 10 footman)

Questo non è l'unico modo per aumentare le unità a disposizione del giocatore computer, si può anche usare l'ordine add_units come mostrato qui.

trigger computer1 (timer 0) (add_units a1 10 footman)

Tuttavia, questo è immediato e non offre al giocatore alcun modo di influenzare l'evento. Nell'altro scenario, il giocatore può impedire al computer di avere il prossimo gruppo di fanti distruggendo le caserme usate per addestrarli. In questo modo, invece, questi fanti appariranno a prescindere.

Sintassi di un file di capitolo cutscene
'''''''''''''''''''''''''''''''''''''''''

Nota: la distinzione tra suoni in streaming e suoni precaricati è stata rimossa in SoundRTS 1.2. Tutti i suoni vengono precaricati.

Nota: un numero può rappresentare un messaggio di testo definito in tts.txt (nuovo in SoundRTS 1.2 alpha 9).

Un capitolo cutscene è una sequenza di suoni interrompibile. Quando il capitolo cutscene è stato riprodotto, il capitolo successivo viene sbloccato.
Non confondere con le cutscene più brevi eseguite da un trigger durante una missione quando si verifica una condizione (scoperta di una cella ad esempio), o con l'introduzione (o briefing) della missione.

I capitoli cutscene hanno solo 3 righe. Ad esempio:
cut_scene_chapter
title 7000
sequence 7500 7501 7502

La prima riga è una parola chiave usata per comunicare al gioco che questo capitolo è una cutscene e non una missione.
La riga title è usata nel menu della campagna.
La riga sequence significa: "riproduci il suono 7500.ogg seguito da 7501 e 7502; se il giocatore preme un tasto, salta il suono corrente e riproduci il successivo."

Editor di mappe (sperimentale)
------------------------------

Il client include un editor di mappe sperimentale per le mappe multigiocatore. Funziona solo per il terreno, quindi si deve ancora modificare manualmente la mappa per le unità.

Avviare l'editor
""""""""""""""""

Avviare una partita su una mappa. Questa mappa sarà il punto di partenza. Entrare nella console (premere il tasto sotto escape) e inserire il comando: "edit". Premere Invio. Le associazioni di tasti dell'editor verranno caricate da res/ui/editor_bindings.txt.

Selezionare un terreno dalla tavolozza
""""""""""""""""""""""""""""""""""""""

Premere PagSu o PagGiù per selezionare un terreno. Il significato di ciascun terreno è memorizzato in ``res/ui/editor_palette.txt``.

Il campo ``style`` di ogni voce della tavolozza deve corrispondere a un nome ``class terrain`` in ``rules.txt``
(ad es. ``forest``, ``dense_forest``, ``meadows``, ``lake``). Quando applicato:

- **Terreno statico** (``is_dynamic 0``, ad es. lago, montagna): blocca ``type_name`` sulla cella; salvato come ``terrain <name>``.
- **Terreno dinamico** (``is_dynamic 1``, ad es. foresta, foresta fitta, prati): posiziona giacimenti ``wood`` / ``meadow`` sulla cella; la voce del terreno proviene da ``square_terrain`` e può cambiare quando gli oggetti vengono rimossi.

Applicare un terreno a una cella
"""""""""""""""""""""""""""""""

Premere Invio per applicare il terreno alla cella corrente. Le celle adiacenti con le stesse caratteristiche (terreno e stessa altezza) saranno collegate automaticamente da un percorso. Le celle diverse avranno il percorso rimosso.

Se la modalità zoom è attiva, Invio applica il terreno selezionato solo alla sottocella
corrente. La mappa salvata userà la sintassi ``square/x,y`` descritta in
`Terreno a livello di sottocella (dalla 1.4.4.8)`_.

Attiva/disattiva percorso verso un vicino
"""""""""""""""""""""""""""""""""""""""""

Premere Control + Shift + freccia per aggiungere o rimuovere il percorso nella direzione corrispondente.

Salva mappa
"""""""""""

Premere Control + s per salvare la mappa. Il file non sovrascriverà mai un altro file. Il nome del file sarà user/multi/editor0.txt, editor1.txt, editor2.txt, ecc.

Esci dall'editor
""""""""""""""""

Premere F10 e uscire dal gioco per lasciare l'editor. Verrà fatto un salvataggio automatico della mappa per sicurezza (ma non contarci troppo). Il nome è user/multi/editor_autosave.txt

Aggiungere unità
""""""""""""""""

Aprire il file in un editor di testo. Usare i comandi menzionati in `Definire le risorse iniziali dei giocatori`.
