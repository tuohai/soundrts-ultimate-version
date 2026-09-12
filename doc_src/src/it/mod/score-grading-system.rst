Sistema di punteggio e valutazione
==================================



Guida giocatore: `../player/score-and-grades.md <../player/score-and-grades.htm>`_

Questo documento descrive il punteggio multidimensionale di fine partita di SoundRTS, i voti in lettere e gli annunci vocali.

Per l’integrazione con gli achievement, vedi la sezione 9 di `Sistema achievement <achievement-system.htm>`_. Gli achievement leggono ``score_breakdown()``; non ricalcolano il punteggio.


----


1. Quando viene calcolato il punteggio
-------------------------------------



.. list-table::
   :header-rows: 1

   * - Scenario
     - Annuncio punteggio
     - Statistiche storiche
   * - Mappa personalizzata / casuale contro IA (TrainingGame)
     - ✅
     - ✅
   * - Multigiocatore
     - ✅
     - ✅
   * - Campagna / campagna coop
     - ❌
     - ❌
   * - Spettatore
     - ❌ (“spectating finished”)
     - ❌



Quando ``game.is_campaign_session()`` è vero, ``say_score()`` e ``\_record_stats()`` vengono saltati.

Ordine di fine partita (``game.post_run()``): prima ``say_score()``, poi ``\_say_achievements()``.


----


2. Struttura del punteggio
--------------------------


.. code-block:: text

   total = base_total + ai_defeat



.. list-table::
   :header-rows: 1

   * - Campo
     - Significato
   * - ``base_total``
     - Somma delle sette dimensioni base, tetto 800
   * - ``ai_defeat``
     - Bonus per computer nemici sconfitti, non conteggiato nel 800
   * - ``total``
     - `base_total + ai_defeat`; può superare 800
   * - ``percent``
     - `base_total × 100 ÷ 800`, limitato al 100%
   * - ``max``
     - Sempre 800 (denominatore della percentuale; esclude ai_defeat)
   * - ``grade_total``
     - Punteggio usato per il voto in lettere (tetto in sconfitta; vedi §5)



Sette dimensioni base
~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Dimensione
     - Chiave
     - Intervallo
     - Note
   * - Esito
     - ``outcome``
     - 0 o 200
     - Vittoria 200, sconfitta 0
   * - Estrazione
     - ``mining``
     - 0–100
     - rispetto alla capacità di depositi della mappa o al riferimento
   * - Efficienza
     - ``efficiency``
     - 0–100
     - utilizzo o parsimonia (vedi §4)
   * - Sopravvivenza
     - ``survival``
     - 0–100
     - tasso di perdite unità amiche
   * - Difesa edifici
     - ``building_defense``
     - 0–100
     - perdite di edifici amici
   * - Combattimento
     - ``combat``
     - 0–100
     - uccisioni rispetto alla produzione nemica
   * - Demolizione
     - ``demolition``
     - 0–100
     - edifici nemici distrutti



Righe di riepilogo (per gli annunci)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Chiave
     - Formula
   * - ``unit_line``
     - `survival + combat`
   * - ``building_line``
     - `building_defense + demolition`
   * - ``mining_by_resource[]``
     - punteggio estrazione per risorsa




----


3. Formule delle dimensioni
---------------------------


Tutti i punteggi dimensionali usano ``\_clamp_score()`` a 0–100 (l’esito è 0 o 200). Gli importi interni usano interi a virgola fissa (``PRECISION``); gli annunci dividono per ``PRECISION`` per la visualizzazione.

3.1 Esito
~~~~~~~~~


- Vittoria: `200`
- Sconfitta: `0`

Peso doppio rispetto alle altre singole dimensioni.

3.2 Estrazione
~~~~~~~~~~~~~~


Raccolto effettivo = ``gathered[i] - starting_resources[i]`` (somma per risorsa, minimo 0). Lo stock iniziale non conta.

Con capacità della mappa (``sum(world.map_deposit_capacity) \> 0``):

.. code-block:: text

   mining = clamp(effective_gathered × 100 ÷ total_map_capacity)


La capacità è accumulata da ogni ``Deposit`` della mappa al caricamento (``worldresource.py``).

Senza capacità della mappa:

- Campagna: vittoria → 100; sconfitta → 0
- Non campagna: se il raccolto effettivo ≤ 0 → 0; altrimenti:

.. code-block:: text

     mining = clamp(effective_gathered × 100 ÷ 1000)

  (``MINING_REFERENCE_GATHER`` = 1000 in unità di visualizzazione)

I punteggi per risorsa seguono le stesse regole in ``mining_by_resource[i]``.

3.3 Efficienza
~~~~~~~~~~~~~~


.. code-block:: text

   utilization_percent = clamp(consumed ÷ gathered × 100)   // 0 if gathered is 0


- Predefinito `efficiency_mode = "utilization"`: `efficiency = utilization_percent`
- Parsimonia `efficiency_mode = "frugal"` (solo in vittoria, utilizzo < 50%):
  ``efficiency = clamp((1 - consumed/gathered) × 100)``  
  L’annuncio usa “efficienza parsimoniosa” (TTS 5251) invece di “utilizzo risorse” (5227).

In sconfitta, la modalità frugal non si applica mai.

3.4 Sopravvivenza
~~~~~~~~~~~~~~~~~


.. code-block:: text

   if produced(unit) > 0:
       survival = clamp((produced - lost) × 100 ÷ produced)
   else:
       survival = 0


3.5 Difesa edifici
~~~~~~~~~~~~~~~~~~


.. code-block:: text

   building_defense = max(0, 100 - lost(building) × 5)


5 punti persi per ogni edificio amico.

3.6 Combattimento
~~~~~~~~~~~~~~~~~


Somma ``produced(unit)`` sui nemici non alleati e non neutrali come ``enemy_units``:

.. code-block:: text

   if enemy_units > 0:
       combat = clamp(killed(unit) × 100 ÷ enemy_units)
   else:
       combat = clamp(killed(unit) × 5)


3.7 Demolizione
~~~~~~~~~~~~~~~


.. code-block:: text

   demolition = clamp(killed(building) × 5)


5 punti per edificio nemico (tetto 100 a 20 edifici).

3.8 Bonus sconfitta IA (``ai_defeat``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Per ogni computer nemico sconfitto, aggiungi ``defeat_score`` in base alla difficoltà:


.. list-table::
   :header-rows: 1

   * - Livello integrato
     - defeat_score predefinito
   * - beginner / easy
     - 10
   * - intermediate / aggressive
     - 20
   * - advanced
     - 40
   * - expert
     - 80
   * - nightmare
     - 200



Da ``defeat_score \<n\>`` nel blocco ``ai.txt`` dell’IA; i nomi IA personalizzati senza di esso valgono 0.

Esclusi: computer alleati, non sconfitti, tipi IA ``timers`` / ``ai2`` / vuoto, ``defeat_score 0``, giocatori non computer. I giocatori sconfitti in ``ex_players`` contano comunque.


----


4. Voti in lettere
------------------


Da ``grade_total`` (``score_grade_msg()`` / ``score_grade_letter()``):


.. list-table::
   :header-rows: 1

   * - Voto
     - grade_total minimo
   * - S
     - 720
   * - A
     - 640
   * - B
     - 560
   * - C
     - 480
   * - D
     - 400
   * - E
     - 0



Tetto del voto in sconfitta
~~~~~~~~~~~~~~~~~~~~~~~~~~~


In sconfitta: ``grade_total = min(total, 479)`` (``DEFEAT_GRADE_MAX_TOTAL``). Il voto in lettere non può superare D in sconfitta anche se combattimento/demolizione gonfiano ``total``.


----


5. Eventi statistici grezzi
---------------------------


``Stats.add(event, target, inc)`` durante la partita:


.. list-table::
   :header-rows: 1

   * - event
     - target
     - Trigger tipico
   * - ``gathered``
     - indice risorsa
     - estrazione, risorse iniziali, concessioni carte
   * - ``produced``
     - ``unit`` / ``building``
     - addestramento completato
   * - ``lost``
     - ``unit`` / ``building``
     - amico distrutto
   * - ``killed``
     - ``unit`` / ``building``
     - nemico distrutto

Lo scadere di ``time_limit`` con ``on_disappear`` (incluse le invocazioni di ``lang_add_units``) non aggiunge ``lost``; ``uncount_expired_unit_produced`` storna ``produced``. La morte in combattimento conta ancora ``lost`` / ``killed``.



``consumed(i) = gathered(i) - player.resources[i]``.

``stats.freeze()`` a fine partita fissa ``game_duration`` per l’annuncio del tempo.


----


6. Annunci vocali (``score_msgs``)
----------------------------------


Ordine:

1. Vittoria/sconfitta + durata + punti esito
2. Unità: prodotte / perse / uccise + ``unit_line``
3. Edifici: prodotti / persi / uccisi + ``building_line``
4. Ogni risorsa: raccolta / consumata + punteggio estrazione per risorsa
5. Riga efficienza (etichetta frugal o utilization)
6. Ogni livello IA sconfitto [× conteggio] + bonus
7. Totale / 800 / percent%
8. Voto in lettere + spiegazione storica

ID TTS: ``soundrts/msgparts.py`` (5225–5243, 5251) e ``res/ui/tts.txt``.


----


7. Integrazione achievement
---------------------------


``achievements.build_context()`` legge da ``score_breakdown()``:


.. list-table::
   :header-rows: 1

   * - Condizione
     - Fonte
   * - ``condition grade S`` ecc.
     - `score_grade_letter(total)`
   * - ``condition victory``
     - `player.has_victory`
   * - ``condition utilization_below N``
     - ``utilization_percent`` (vittoria richiesta)
   * - ``condition survival_at_least N``
     - ``survival``
   * - ``condition building_defense_at_least N``
     - ``building_defense``
   * - ``condition defeated_ai expert`` ecc.
     - ``ai_defeat_entries``




----


8. Personalizzazione nella mod
------------------------------


ai.txt — bonus sconfitta
~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def my_custom_ai
   defeat_score 55


``defeat_score 0`` disabilita il bonus per quell’IA.


----


9. File correlati
-----------------



.. list-table::
   :header-rows: 1

   * - Percorso
     - Ruolo
   * - ``soundrts/worldplayerstats.py``
     - Punteggio, voti, messaggi
   * - ``soundrts/definitions.py``
     - ``DEFAULT_AI_DEFEAT_SCORE``, `get_ai_defeat_score()`
   * - ``soundrts/worldresource.py``
     - ``map_deposit_capacity``
   * - ``soundrts/game.py``
     - `say_score()`, `post_run()`
   * - ``soundrts/achievements.py``
     - Legge il breakdown per gli sblocchi




----


10. Test
--------


.. code-block:: bash

   python -m pytest soundrts/tests/test_score_breakdown.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v



----


11. Costanti di progetto
------------------------



.. list-table::
   :header-rows: 1

   * - Costante
     - Valore
     - Ruolo
   * - ``SCORE_BASE_MAX``
     - 800
     - Massimo base
   * - ``OUTCOME_MAX``
     - 200
     - Peso dell’esito
   * - ``DEFEAT_GRADE_MAX_TOTAL``
     - 479
     - Tetto voto in sconfitta (D)
   * - ``MINING_REFERENCE_GATHER``
     - 1000
     - Riferimento senza depositi



Non valutati oggi: durata partita, progresso tecnologico. ``game_duration`` è solo per l’annuncio.

La percentuale riflette solo le sette dimensioni base, non il bonus sconfitta IA.
