Dare oggetti ai PNG (``give`` + ``npc_has_item``)
=====================================================


Permette ai giocatori di consegnare oggetti trasportati a un'altra unità (PNG neutrale, alleato, nemico) e di verificare la consegna con :strong:```npc_has_item``.


----


1. Panoramica
---------------



.. list-table::
   :header-rows: 1

   * - Parte
     - Nome
     - Ruolo
   * - Ordine
     - ``give``
     - trasferisce l'oggetto dal portatore al bersaglio
   * - Campo
     - ``receive_items``
     - interruttore principale (default 0)
   * - Campo
     - ``accepted_items``
     - whitelist oggetti; vuoto = qualsiasi
   * - Campo
     - ``accept_from``
     - relazione del donatore: ``self``/``ally``/``neutral``/``enemy``; vuoto = qualsiasi
   * - Campo
     - ``accept_givers``
     - tipi unità donatori; vuoto = qualsiasi
   * - Condizione
     - ``npc_has_item``
     - il bersaglio ha ricevuto / possiede l'oggetto
   * - Condizione
     - ``npc_has_items``
     - il bersaglio ha ricevuto / possiede una *quantità* di oggetti (obiettivi di raccolta)



In caso di successo: l'oggetto passa all'inventario del bersaglio; ``received_items`` registra il tipo; feedback audio/UI.


I bersagli devono avere ``receive_items 1`` in ``rules.txt``, altrimenti la consegna è rifiutata.


----


2. Uso da parte del giocatore
-------------------------------


Il portatore deve avere ``inventory_capacity \> 0`` e l'oggetto (via ``pickup``).

1. Clic destro su un'unità non nemica mentre si trasporta → give predefinito (primo oggetto accettabile).
2. Menu comandi: «Give».
3. Tasto rapido: ``g`` (``style.txt``).

Il give con clic destro solo se si trasporta + il bersaglio non è nemico né edificio.


----


3. Script: ``give`` nei trigger
-----------------------------------


.. code-block:: text

   give <target_unit_id>
   give <target_unit_id> <item>    ; type_name or item id



----


4. ``npc_has_item``
-----------------------


.. code-block:: text

   (npc_has_item <NPC_selector> <item_type> [square])
   (npc_has_item <index> <unit_type> <item_type>)
   (npc_has_item <square> <index> <unit_type> <item_type>)


- Classico: selettore = ``type_name`` o id unità; casella opzionale = PNG attualmente in quella casella.
- Indice globale: `(npc_has_item 3 quest_npc short_sword)` — 3° ``<unit_type>`` spawnato per quel proprietario (qualsiasi casella).
- Indice casella: N-esimo in ``<square>`` (stabile dopo lo spostamento). Vedi `map-unit-index-selectors.md <map-unit-index-selectors.htm>`_. Il capitolo 28 usa la forma globale.

Vero se ``received_items`` contiene il tipo o l'inventario lo detiene ancora.

Confronta con `find-item-objective <find-item-objective.htm>`_. Per arrivare e far sparire senza PNG, usa `brought-item-delivery <brought-item-delivery.htm>`_.


----

4b. ``npc_has_items`` (variante con contatore)
-------------------------------------------------

.. code-block:: text

   (npc_has_items <NPC_selector> <item_type> <count> [square])
   (npc_has_items <index> <unit_type> <item_type> <count>)
   (npc_has_items <square> <index> <unit_type> <item_type> <count>)


Gli stessi selettori di ``npc_has_item``, più un ``<count>`` obbligatorio: la
condizione è vera solo quando l'unità possiede **almeno quel numero** di
oggetti di quel tipo.

``npc_has_item`` chiede soltanto se l'unità ha il *tipo* di oggetto
(``received_items`` è un insieme), quindi basta consegnare un oggetto per
soddisfarla. Usa ``npc_has_items`` per obiettivi di raccolta che richiedono più
copie — ad es. il capitolo 4 di Joan of Arc richiede tutte e tre le reliquie
nella cattedrale di Reims:

.. code-block:: text

   trigger player1 (npc_has_items npc_reims_cathedral relic 3 c5) (do (objective_complete 1) (cut_scene 8837))


Il conteggio è il maggiore tra (a) quanti oggetti sono stati consegnati con
``give`` e (b) quanti si trovano ora nell'inventario dell'unità — così sopravvive
all'uscita dell'oggetto dall'inventario e conta anche gli oggetti con cui il PNG
inizia. Lo stesso oggetto non viene mai contato due volte.

``<count>`` deve essere un intero positivo; ``0``, un numero negativo o un token
non numerico rendono la condizione falsa.

----


5. Regole di ricezione
-----------------------


Tutte devono passare:


.. list-table::
   :header-rows: 1

   * - Campo
     - Valori
     - 
   * - ``receive_items``
     - ``1`` / `0`
     - default 0
   * - ``accepted_items``
     - elenco tipi
     - vuoto = qualsiasi; ``is_a`` funziona
   * - ``accept_from``
     - relazioni
     - vuoto = qualsiasi
   * - ``accept_givers``
     - tipi unità
     - vuoto = qualsiasi



Relazioni (ricevente vs donatore): ``self`` > ``ally`` > ``neutral`` > ``enemy``.

Con ``accept_from enemy``, il clic destro su quel nemico con l'oggetto giusto diventa give invece di attacco (solo per quell'oggetto + tipo unità).

Esempi
~~~~~~


Cavaliere alleato accetta solo la lancia:

.. code-block:: text

   def knight
   receive_items 1
   accepted_items knight_lance
   accept_from ally


Leader nemico accetta la lettera solo dal contadino:

.. code-block:: text

   def npc_knight_leader
   receive_items 1
   accepted_items secret_letter
   accept_from enemy
   accept_givers peasant
   ai_mode guard


Campagna cap. 24–27: `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


----


6. Mappa demo
---------------


``res/multi/give_demo.txt``:

.. code-block:: text

   health_potion a1
   computer_only 0 0 neutral c3 quest_npc
   trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)


Esempi di campagna (``The Legend of Raynor``): cap. 14 consegna ``pickaxe`` all'alleato ``npc_peasant``; cap. 15
consegna ``knight_lance`` al neutrale ``npc_knight``; cap. 16 consegna ``wand`` al nemico ``npc_mage``.
Vedi ``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``. Multigiocatore: ``res/multi/give_demo.txt``.


----


7. File di implementazione
----------------------------



.. list-table::
   :header-rows: 1

   * - Ruolo
     - Percorso
   * - ``GiveOrder``
     - ``soundrts/worldorders/skills.py``
   * - Trasferimento
     - ``soundrts/worldunit/world_order.py``
   * - ``accepts_item``
     - ``soundrts/worldunit/worldcreature.py``
   * - Trigger
     - ``soundrts/worldplayerbase/triggers.py``
   * - Test
     - ``soundrts/tests/test_give_item_to_npc.py``



----


8. Casi limite
----------------


- Controllo triplo: ``receive_items``, ``accepted_items``, ``accept_from`` (+ ``accept_givers`` se impostato).
- Il bersaglio deve essere un'unità con ``player``.
- L'oggetto deve essere nell'inventario del donatore.
- La consegna ignora ``inventory_capacity`` del bersaglio (trasferimento narrativo); l'overflow cade a terra.
- ``equip`` sul ricevente come ``pickup`` (buff/skill si applicano).


----


9. Test
---------


.. code-block:: text

   python -m pytest soundrts/tests/test_give_item_to_npc.py -q


Anche: ``test_campaign_alliance_transfer_triggers.py`` per trigger di alleanza / trasferimento.


----


10. Campagna cap. 24–27
-------------------------



.. list-table::
   :header-rows: 1

   * - Cap.
     - Oggetto
     - Ricevente
   * - 24
     - ``secret_letter``
     - ``npc_knight_leader`` (Garrek)
   * - 25
     - ``garrek_token``
     - ``npc_count_roland`` (Roland)
   * - 26
     - ``war_banner``
     - ``npc_general_vera`` (Vera)
   * - 27
     - —
     - duello con ``npc_marco_ironhand``



Dopo la morte dei traditori al cap. 24, ``(add_inventory_item garrek_token 1 raynor)`` mette il gettone nell'inventario di Raynor per il cap. 25. Esegui ``cut_scene`` sui trigger di player1 dopo ``npc_has_item`` così il giocatore umano sente la voce. Guida completa: `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


----


11. Campagna cap. 28 (consegna indicizzata)
---------------------------------------------


.. code-block:: text

   trigger player1 (npc_has_item 3 quest_npc short_sword) (objective_complete 2)


Solo il 3° ``quest_npc`` in B2 conta. Lo stesso capitolo dimostra ``killed_target`` indicizzato e sconfitta per uccisione sbagliata: `map-unit-index-selectors <map-unit-index-selectors.htm>`_.
