Carte di loadout ritardate
==========================



Guida giocatore: `../player/loadout-cards.md <../player/loadout-cards.htm>`_

Le carte pre-missione possono attivarsi dopo :strong:```delay`` / ``delay_minutes`` invece che all’inizio della partita.

Vedi anche: `Sistema achievement <achievement-system.htm>`_, `Sistema di valutazione punteggio <score-grading-system.htm>`_.


----


1. Ambito
---------


- Solo TrainingGame (mappa personalizzata / casuale contro IA), come le carte istantanee; non campagna né multigiocatore.
- Selezione della carta e consumo della carica avvengono all’inizio della partita; gli effetti scattano dopo il tempo di gioco trascorso.
- Le carte ritardate usano gli slot di loadout e costano una carica come le carte istantanee; ``min_rank`` / ``faction`` restano invariati.


----


2. Sintassi di cards.txt
------------------------



.. list-table::
   :header-rows: 1

   * - Direttiva
     - Significato
   * - ``delay \<seconds\>``
     - Attende secondi di tempo di gioco
   * - ``delay_minutes \<n\>``
     - Equivale a `delay (n×60)`
   * - ``tech \<upgrade_id\> [...]``
     - Concede l’upgrade (o gli upgrade) allo scadere del ritardo



Combinabile con ``spawn`` e ``resource`` sulla stessa carta; un solo ritardo condiviso, tutti gli effetti applicati insieme.

.. code-block:: text

   def card_reinforcements_delayed
   title 5333
   spawn footman 3
   delay_minutes 10
   grant_charges 1
   
   def card_delayed_melee_weapon
   title 5334
   tech melee_weapon
   delay_minutes 8
   grant_charges 1


- Ometti ``delay`` oppure usa `0` per effetto immediato (comportamento legacy).


----


3. Runtime
----------


Al momento dell’applicazione del loadout, ``delay \> 0`` registra ``world.schedule_after(delay_ms, callback)``.  
``delay_ms = delay_seconds × 1000 × world.timer_coefficient``.

Quando scatta il timer: applica risorse → spawn vicino all’inizio (consumano popolazione) → tech; l’umano locale riceve la voce LOADOUT_CARD_TRIGGERED.

La carica viene consumata quando la carta è programmata con successo all’inizio della partita, non quando gli effetti scattano.


----


4. Voce (TTS)
-------------



.. list-table::
   :header-rows: 1

   * - ID
     - Inglese
     - Uso
   * - 5387
     - (effects in)
     - Applicata / armeria
   * - 5392
     - (after delay)
     - suffisso
   * - 5388
     - loadout card effect triggered
     - Allo scatto
   * - 5389–5393
     - spawn / resource / tech hints
     - Armeria



I minuti interi sono annunciati come “N minuti”; altrimenti in secondi.


----


5. Esempi vanilla
-----------------



.. list-table::
   :header-rows: 1

   * - Carta
     - Effetto
     - Achievement
   * - ``card_reinforcements_delayed``
     - 3 footman dopo 10 min
     - ``reinforcement_contract``
   * - ``card_delayed_melee_weapon``
     - ``melee_weapon`` dopo 8 min
     - ``defeat_expert``




----


6. Test
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_cards.py -k delay -v
   python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
