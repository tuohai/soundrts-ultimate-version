Sistema di caccia
==================


SoundRTS supporta la caccia in stile Age of Empires: i lavoratori attaccano la fauna selvatica, gli animali cacciati lasciano carcasse di cibo raccoglibili e le pecore possono essere guidate.


----


1. Flusso del giocatore
------------------------


1. Backspace / ordine predefinito o clic destro su un animale → ``attack`` su ``is_huntable`` (l’attacco normale infligge danno; non serve imperative)
2. Alla morte → nasce ``food_carcass``; l’ordine di attacco si completa (**nessun** beep falso ``order_impossible``)
3. Raccolta automatica → dopo l’uccisione il lavoratore può accodare la raccolta; con ``auto_gather`` raccoglie e riporta il cibo
4. Fuga al colpo → cervi e pecore scappano; i cinghiali contrattaccano
5. Pastorizia (opzionale) → i lavoratori con ``can_herd 1`` possono guidare animali ``herdable`` (es. pecore)


Nota: l’ordine predefinito su creep / NPC neutrali comuni è ``go`` (solo movimento); sugli animali cacciabili resta ``attack``.
Le modalità offensive / defensive / chase **non** attaccano automaticamente gli animali neutrali senza attacco imperativo.


----


2. Voce: etichetta «animal» (non NPC)
--------------------------------------


Gli animali da caccia sono piazzati con ``computer_only ... neutral`` ma non vengono annunciati come «NPC neutrale».


.. list-table::
   :header-rows: 1

   * - Situazione
     - Annuncio di esempio
   * - Seleziona un cervo
     - deer , animal
   * - Riepilogo della casella
     - , 2 deer , animal
   * - Ctrl+Shift+F4 sul giocatore solo-fauna
     - you are animal



Regole:

- Unità con ``is_huntable 1`` o ``herdable 1`` → fauna selvatica → annunciate come animal
- Una virgola separa il nome dell'unità e animal (stesso schema delle etichette nemico/alleato)
- Ctrl+Shift+F4 dice you are animal solo quando ogni unità viva di quel giocatore è fauna; un mix di ``quest_npc`` + cervo dice ancora you are neutral NPC

Gli NPC di storia (``quest_npc``, ecc.) restano neutral , NPC.


----


3. Piazzamento sulla mappa
---------------------------


.. code-block:: text

   computer_only 0 0 neutral b3 4 deer 2 sheep


Anche le mappe casuali generano frutteti e fauna vicino alle posizioni di partenza.

3.1 Diplomazia: la fauna non è alleata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


La fauna nasce tramite ``computer_only``, ma non entra nell'alleanza computer predefinita ``"ai"`` e non può allearsi con giocatori o altre fazioni.


.. list-table::
   :header-rows: 1

   * - Regola
     - Significato
   * - Rilevamento
     - Lo slot ``computer_only`` contiene solo unità con ``is_huntable 1`` o ``herdable 1`` (cervo, pecora, una tigre personalizzata, ecc.)
   * - Motore
     - Quel computer ottiene `alliance = None`; ``allied`` è solo se stesso
   * - Più branchi
     - Ogni riga ``computer_only`` è un punto di caccia separato; i branchi non si alleano tra loro
   * - Slot misto
     - Se la stessa riga mescola animali e fanti, l'intero slot resta un'IA normale e entra in `"ai"`
   * - Diplomazia del giocatore
     - I giocatori neutrali non possono allearsi con F12; la fauna non è mai una fazione diplomatica



Animale personalizzato (isolato da ``"ai"``):

.. code-block:: text

   def tiger
   class soldier
   is_huntable 1
   ...
   
   computer_only 0 0 neutral 5,5 2 tiger


Per far agire più gruppi di fauna come una sola «fazione natura», usa esplicitamente il trigger ``(alliance …)``; non è il comportamento predefinito della caccia.


----


4. rules.txt
--------------


Unità integrate
~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tipo
     - Note
   * - ``deer``
     - 35 cibo, fugge quando colpito
   * - ``sheep``
     - 25 cibo, guidibile, fugge
   * - ``boar``
     - 50 cibo, contrattacca
   * - ``food_carcass``
     - carcassa raccoglibile (``collision 0``)



Il ``can_gather`` dei lavoratori include ``food_carcass`` e ``orchard``.

Proprietà degli animali
~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Proprietà
     - Significato
   * - ``is_huntable 1``
     - cacciabile; il clic destro predefinito è attacco
   * - ``flee_on_hit 1``
     - scappa dall'attaccante
   * - ``herdable 1``
     - può essere guidato da lavoratori ``can_herd``
   * - ``food_deposit``
     - tipo di deposito carcassa alla morte
   * - ``food_deposit_qty``
     - quantità di cibo della carcassa
   * - ``no_number 1``
     - omette il numero quando ce n'è uno solo di quel tipo



Lavoratore: ``can_herd 1`` abilita la pastorizia (predefinito ``0``).

Esempio di animale personalizzato
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def wolf
   class soldier
   is_huntable 1
   flee_on_hit 1
   food_deposit food_carcass
   food_deposit_qty 40
   no_number 1
   ai_mode guard


Tecnologia
~~~~~~~~~~~


``hunting_techniques``: raccolta più rapida di frutteti/carcasse, più rendimento, cibo bonus sulle carcasse degli animali. Si ricerca al municipio.


----


5. Fauna vs NPC di storia
--------------------------



.. list-table::
   :header-rows: 1

   * - 
     - Fauna
     - NPC di storia
   * - Esempi
     - ``deer``, ``sheep``, ``boar``
     - ``quest_npc``, ``npc_knight``
   * - Rilevamento
     - ``is_huntable`` / ``herdable``
     - (può avere ``receive_items``)
   * - Voce
     - animal
     - neutral , NPC
   * - Auto-attacco del giocatore
     - no (serve attacco forzato)
     - no



Vedi `unit-default-behavior <unit-default-behavior.htm>`_.


----


6. Codice e test
-----------------



.. list-table::
   :header-rows: 1

   * - Ruolo
     - Percorso
   * - Logica di caccia
     - ``soundrts/worldunit/worldcreature.py``, ``worldworker.py``
   * - Isolamento alleanza fauna
     - ``soundrts/worldplayerbase/base.py``, ``world/world_objects.py``
   * - Voce animali
     - ``soundrts/clientgameentity/properties.py``
   * - Voce cambio giocatore
     - ``soundrts/clientgame/game_resources.py``
   * - Spawn RMG
     - ``soundrts/randommap.py``
   * - Test
     - ``soundrts/tests/test_hunting.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``
