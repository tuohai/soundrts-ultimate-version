Upgrade di linea unità e addestramento di livello massimo (line_upgrade)
========================================================================

Per **autori di mod**: configurare in ``rules.txt`` “ricerca una forma → sblocca l’addestramento di livello massimo → trasforma le unità sul campo”, senza nomi unità hardcoded nel motore. Le linee della caserma di Age of Empires II DE funzionano così.

Panoramica
----------

.. list-table::
   :header-rows: 1

   * - Funzione
     - Descrizione
   * - Addestramento di livello massimo
     - Il ``can_train`` dell’edificio elenca la radice (es. ``militia``); si addestra la forma più alta sbloccata
   * - Upgrade di linea ricercabile
     - Segnare la forma con ``line_upgrade 1`` e metterla in ``can_research``; al completamento va in ``player.upgrades``
   * - Trasformazione sul campo
     - Al completamento della ricerca, le unità il cui ``can_upgrade_to`` include quella forma si trasformano all’istante
   * - Coda di produzione
     - Gli ordini ``train`` in coda o in corso sulla stessa linea diventano la nuova forma (AoE2 DE: i mangonelli in coda escono come onagri). Costo e tempo restante già pagati restano
   * - Costo di addestramento
     - Di default si addebita ``cost`` / ``time_cost`` della **radice** (override con ``train_cost`` / ``train_time``)

Il motore **non** hardcoda civiltà o id unità: solo campi di rules e catene ``can_upgrade_to``.

Sintassi rules
--------------

1. Linea unità (``can_upgrade_to``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def militia
    class soldier
    cost 20 0 50 0
    time_cost 21
    can_upgrade_to man_at_arms

    def man_at_arms
    is_a militia
    cost 40 0 100 0
    time_cost 40
    requirements feudal_age
    line_upgrade 1
    can_upgrade_to long_swordsman

- ``cost`` / ``time_cost`` dei livelli medi/alti di solito sono il prezzo di **ricerca** (come in DE).
- L’addestramento usa ancora il costo della radice salvo ``train_cost`` / ``train_time``.

2. Edificio: slot addestramento + ricerca
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def barracks
    class building
    can_train militia spearman
    can_research tracking squires man_at_arms long_swordsman …

- Elencare solo radici in ``can_train``; il menu mappa al livello più alto sbloccato.
- Dopo aver messo una forma ``line_upgrade 1`` in ``can_research``, si ricerca come una tecnologia.

3. Effect tecnologia opzionale
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Con ``class upgrade`` si può scrivere::

    effect unit_line_upgrade man_at_arms

Stesso risultato della ricerca diretta della forma (upgrades + morph). Ogni obiettivo vale una volta per giocatore.

Rapporto con la morph automatica per età
----------------------------------------

.. list-table::
   :header-rows: 1

   * - Flag
     - Comportamento
   * - (nessuno)
     - Se la phase ha ``units_auto_upgrade 1`` e il target ha quel nome età in ``requirements``, può morfarsi con l’età
   * - ``line_upgrade 1``
     - **Non** si morfosa con l’età; va ricercata; l’addestramento richiede il nome in ``player.upgrades``
   * - ``no_auto_upgrade 1``
     - Salta la morph per età; l’addestramento richiede comunque la ricerca (stessa soglia di ``line_upgrade``)

Per linee militari stile AoE2 DE usare ``line_upgrade 1``, non solo ``units_auto_upgrade``.

Il menu unità ``upgrade_to`` **non** offre più forme ``line_upgrade`` (evita pagare la differenza per unità, a differenza di AoE2). Ricercarle in ``can_research`` dell’edificio.

Anche le linee di edifici (torri, mura): ``can_build`` elenca la radice; dopo la ricerca il menu mappa al livello massimo; il costo di costruzione usa la radice (override con ``train_cost``). ``line_upgrade_also`` sblocca più forme in una ricerca.

Punti di ingresso del motore (riferimento)
------------------------------------------

.. list-table::
   :header-rows: 1

   * - Simbolo
     - Posizione
   * - ``resolve_trainable_unit_type``
     - ``soundrts/world_build_rules.py``
   * - ``effective_can_train`` / ``unit_train_cost`` / ``unit_train_time``
     - idem
   * - ``apply_unit_line_upgrade``
     - idem
   * - ``remap_queued_train_orders_for_line_upgrade`` / ``resolved_train_type_class``
     - idem
   * - ``ResearchOrder.complete``
     - ``soundrts/worldorders/production.py``
   * - ``effect_unit_line_upgrade``
     - ``soundrts/worldupgrade/attribute_effects.py``
   * - Skip età
     - ``soundrts/worldphase.py`` → ``_auto_upgrade_units``
   * - Attributo predefinito
     - ``Creature.line_upgrade`` (``worldcreature.py``)
   * - Attributo int rules
     - ``definitions.py`` → ``line_upgrade``

Test
----

``soundrts/tests/test_train_line_resolve.py``: l’età da sola non sblocca; dopo upgrades / ``apply_unit_line_upgrade`` funzionano addestramento di livello massimo e morph; completare la ricerca riassegna la coda sulla stessa linea.

Mod aoe2
--------

``mods/aoe2/rules.txt`` marca forme di spada, lancia, arco, cavalleria e assedio con ``line_upgrade 1`` e le collega a ``can_research`` di caserma / arco / scuderia / officina (e varianti civ). Fonti: ``mods/aoe2/SOURCES.md``.

Vedi anche: `Manuale di modding <modding.htm>`_.
