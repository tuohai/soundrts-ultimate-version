Configurazione del comportamento predefinito delle unità (``rules.txt``)
========================================================================


Gli autori di mappe e mod possono impostare il comportamento iniziale di ogni tipo di unità all’avvio della partita in ``rules.txt``:

- Modalità IA predefinita (``ai_mode``): offensive / defensive / guard / chase
- Raccolta automatica (``auto_gather``): i lavoratori iniziano a raccogliere automaticamente
- Riparazione automatica (``auto_repair``): i lavoratori iniziano a riparare automaticamente
- Esplorazione automatica (``auto_explore``): le unità mobili iniziano a esplorare automaticamente

I giocatori possono comunque modificare queste impostazioni in partita dopo la creazione.


----


1. Panoramica
-------------



.. list-table::
   :header-rows: 1

   * - Campo
     - Valori
     - Predefinito
     - Si applica a
     - Descrizione
   * - ``ai_mode``
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
     - soldati=``offensive``, lavoratori=``defensive``
     - unità da combattimento
     - modalità IA iniziale
   * - ``auto_gather``
     - ``1`` / `0`
     - lavoratori=`1`
     - lavoratori
     - raccolta automatica all’avvio
   * - ``auto_repair``
     - ``1`` / `0`
     - lavoratori=`1`
     - lavoratori
     - riparazione automatica all’avvio
   * - ``auto_explore``
     - ``1`` / `0`
     - ``0``
     - unità mobili
     - esplorazione automatica all’avvio
   * - ``can_auto_explore``
     - ``1`` / `0`
     - ``0``
     - unità mobili
     - mostra attiva/disattiva esplorazione automatica nel menu comandi




Scrivi questi campi nel blocco `def <name>` dell’unità. I campi omessi usano i valori predefiniti sopra.

Esempio di campagna (cap. 24–27): gli NPC chiave usano ``escort`` o ``ai_mode guard`` così non inseguono prima della consegna/duello. Dopo l’alleanza, i trigger cambiano modalità:

- `(set_ai_mode offensive c2 1 npc_count_roland …)` — Roland passa in offensiva dopo il gettone (cap. 25)
- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((go c1)))` — cap. 27 (``raynor7``): solo Marco passa in offensiva; le scorte si spostano in c1 per liberare l’arena
- `(allied_assist computer1)` — tutte le unità da combattimento alleate da guard → chase
- `(allied_assist computer1 c2 4 npc_archer_escort)` — solo gli arcieri di scorta → chase
- `(allied_control computer1 c2 4 npc_knight_escort)` — i cavalieri di scorta sotto il comando del giocatore (restano in guard); gli altri passano automaticamente → chase

Per i duelli con resa (``yield_on_defeat``), abilitali a runtime con `` (set_yield_on_defeat 1 …)`` invece che in ``rules.txt`` alla creazione, così gli NPC restano uccidibili prima della consegna del gettone. Vedi `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


``auto_explore`` rispetto a ``can_auto_explore``:

``auto_explore`` — se l’unità inizia con l’esplorazione automatica attiva.

``can_auto_explore`` — se il menu comandi offre attiva/disattiva esplorazione automatica.

Indipendenti: ad esempio solo i cavalieri hanno ``can_auto_explore 1``, oppure ``auto_explore 1`` per gli esploratori all’avvio.


----


2. Modalità IA (``ai_mode``)
----------------------------


2.1 Modalità
~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Valore
     - Nome
     - Comportamento
   * - ``offensive``
     - Offensiva
     - attacca le unità ostili nella casella corrente (predefinito comune)
   * - ``defensive``
     - Difensiva
     - si ritira dalle minacce ostili se in svantaggio; combatte se in vantaggio
   * - ``guard``
     - Guardia
     - mantiene la posizione; contrattacca solo se abilitato
   * - ``chase``
     - Inseguimento
     - mantiene un solo ``AttackAction`` sul nemico bloccato e segue tramite uscite tra caselle (senza ``go`` automatico) fino a portata


2.1.1 Punto di hold (``position_to_hold``) e uscita dalla casella
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Le unità nascono con la casella corrente come ``position_to_hold``. Dentro di quell’area,
``_must_hold`` blocca l’uscita:


.. list-table::
   :header-rows: 1

   * - Modalità IA
     - Limitata da ``position_to_hold``?
   * - ``offensive`` / ``guard``
     - Sì (non escono da sole senza un ordine che fa ``stop()``)
   * - ``defensive``
     - No (possono ritirarsi)
   * - ``chase``
     - No (l’hold si azzera quando l’inseguimento attraversa caselle)


Gli ordini ``go`` / ``attack`` del giocatore chiamano ``stop()`` al primo update e azzerano
``position_to_hold``.

La pattuglia è un comando con un percorso, non una modalità IA. Non puoi scrivere ``ai_mode patrol``. Usa ``guard`` o ``chase`` per effetti simili.

2.2 Esempi
~~~~~~~~~~


.. code-block:: text

   def knight
   class soldier
   ...
   ai_mode guard
   
   def footman
   class soldier
   ...
   ai_mode defensive


2.3 Unità neutrali
~~~~~~~~~~~~~~~~~~


Le unità del giocatore in modalità ``offensive``, ``defensive`` o ``chase``:

- non attaccano automaticamente le unità neutrali (creep / NPC / fauna `computer_only ... neutral`);
- non fuggono a causa dei neutrali (la modalità difensiva valuta solo le vere minacce ostili);
- ``go`` predefinito / normale su un neutrale (non imperativo) si limita a muovere, senza AttackAction;
- l’ordine predefinito su ``is_huntable`` resta ``attack`` e infligge danno;
- per far trattare dalla IA un creep / NPC neutrale come bersaglio automatico, dai un attacco forzato (``imperative`` — ad es. Ctrl+clic sull’unità;
  il motore converte l’``go`` imperativo in ``attack``).


Voce: gli animali da caccia (``is_huntable`` / ``herdable``, ad es. cervi, pecore) vengono annunciati come

"deer , animal", non "neutral , NPC". Gli NPC di trama (``quest_npc``, ecc.) dicono ancora

"neutral , NPC". Vedi `hunting.htm <hunting-system.htm>`_.


La modalità ``guard`` non cambia: nessun attacco proattivo; contrattacco solo se abilitato e colpiti.

I creep del computer neutrali usano comunque ``guard`` forzato + contrattacco dal loro lato.

2.4 Note
~~~~~~~~


- I valori non validi vengono ignorati (registrati nel log) e si torna al predefinito.
- I creep neutrali (`computer_only ... neutral`) restano forzati a ``guard`` + contrattacco indipendentemente da ``ai_mode``.


----


3. Raccolta / riparazione automatica
------------------------------------


Solo per i lavoratori:

- ``auto_gather 1`` — i lavoratori inattivi vanno a raccogliere se esistono un deposito e un magazzino nelle vicinanze.
- ``auto_repair 1`` — i lavoratori inattivi riparano gli alleati danneggiati nella stessa casella (serve ``can_repair 1``).

Entrambi sono attivi per impostazione predefinita. Imposta ``0`` nella def del lavoratore per disattivarli all’avvio. I giocatori possono comunque attivarli/disattivarli in partita.

:strong:```can_repair`` — ``1`` o ``0``. Predefinito ``1`` sui lavoratori. Con ``0``, gli ordini di riparazione e la riparazione automatica sono disabilitati.


----


4. Ordine di cattura predefinito (``can_capture``)
--------------------------------------------------


Per le unità con abilità di attacco, controlla l’ordine predefinito del clic destro sui nemici con
:strong:```capture_hp_threshold 100`` (cattura a contatto):


.. list-table::
   :header-rows: 1

   * - Valore
     - Comportamento
   * - `1` (predefinito)
     - Ordine di cattura predefinito; l’IA usa la cattura a contatto
   * - ``0``
     - Attacco/movimento predefinito; l’IA attacca normalmente



Non blocca la cattura a soglie inferiori (ad es. ``30``) tramite danni da combattimento — solo il
percorso di cattura a contatto con soglia 100 e l’ordine predefinito del clic destro.

.. code-block:: text

   def footman
   class soldier
   can_capture 1
   
   def archer
   class soldier
   can_capture 0


Vedi anche le caserme catturabili delle mappe casuali in ``player/英雄无敌与文明5玩法说明.htm``.


----


5. Esplorazione automatica
--------------------------


Per qualsiasi unità con velocità > 0. Controllata da ``auto_explore`` (stato iniziale) e ``can_auto_explore`` (opzione di menu).

- ``can_auto_explore 1`` — il menu comandi mostra attiva/disattiva esplorazione automatica (solo sulle unità che ce l’hanno).
- ``auto_explore 1`` — inizia a esplorare quando è inattivo; in combattimento usa ``ai_mode`` quando compaiono nemici.

A runtime: altri ordini mettono in pausa l’esplorazione; riprende quando torna inattivo. Disattiva esplorazione automatica è sempre disponibile mentre esplora. Attiva solo se ``can_auto_explore 1``. L’esplorazione dell’IA del computer è separata.


----


6. Esempio combinato
--------------------


.. code-block:: text

   def peasant
   class worker
   auto_gather 1
   auto_repair 0
   ai_mode defensive
   
   def knight
   class soldier
   auto_explore 1
   can_auto_explore 1
   ai_mode guard
   
   def footman
   class soldier
   ai_mode defensive



----


7. Domande frequenti
--------------------


``Q: Perché ``ai_mode patrol`` non funziona?``  
A: La pattuglia richiede un percorso. Valori validi: ``offensive``, ``defensive``, ``guard``, ``chase``.

``Q: ``auto_explore`` su un edificio?``  
A: Ignorato (velocità 0).

``Q: ``auto_gather`` su un soldato?``  
A: Ha senso solo sui lavoratori.

Q: In che modo chase differisce dal vecchio salto con ``go`` automatico?  
A: Ora mantiene l’attacco e segue tra caselle; non è limitato da ``position_to_hold``.
Offensiva / guardia sì, a meno che il giocatore non ordini di muoversi.

Q: Le unità in offensiva/inseguimento attaccheranno automaticamente gli NPC neutrali?  
A: No. Le modalità offensive, defensive e chase ignorano i neutrali per attacco automatico e fuga;
usa un comando di attacco forzato per combatterli.

Q: Perché gli arcieri attaccano una caserma con il clic destro mentre i fanti la catturano?  
A: Controlla ``can_capture``. Predefinito ``1`` → cattura sui bersagli con ``capture_hp_threshold 100``; ``0`` → attacco normale.


----


8. Riferimento dei campi
------------------------



.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Valori validi
   * - ``ai_mode``
     - string
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
   * - ``auto_gather``
     - int
     - ``1`` / `0`
   * - ``auto_repair``
     - int
     - ``1`` / `0`
   * - ``auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_capture``
     - int
     - ``1`` / `0`
