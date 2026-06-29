Delayed Loadout Cards
======================



Player guide: `../player/loadout-cards.md <../player/loadout-cards.htm>`_

Pre-mission cards can take effect after :strong:```delay`` / ``delay_minutes`` instead of at game start.

Chinese version: `../../zh/mod/delayed-card-loadout.htm <../../zh/mod/delayed-card-loadout.htm>`_

See also: `achievement-system <achievement-system.htm>`_, `score-grading-system.htm <score-grading-system.htm>`_.


----


1. Scope
----------


- TrainingGame only (custom / random map vs AI), same as instant cards; not campaign or multiplayer.
- Card selection and charge deduction happen at game start; effects fire after in-game time elapses.
- Delayed cards use loadout slots and cost one charge like instant cards; ``min_rank`` / ``faction`` unchanged.


----


2. cards.txt syntax
---------------------



.. list-table::
   :header-rows: 1

   * - Directive
     - Meaning
   * - ``delay \<seconds\>``
     - Wait seconds of game time
   * - ``delay_minutes \<n\>``
     - Same as `delay (n×60)`
   * - ``tech \<upgrade_id\> [...]``
     - Grant upgrade(s) when the delay expires



Combine with ``spawn`` and ``resource`` on one card; one shared delay, all effects applied together.

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


- Omit ``delay`` or use `0` for immediate effect (legacy behavior).


----


3. Runtime
------------


At loadout apply time, ``delay \> 0`` registers ``world.schedule_after(delay_ms, callback)``.  
``delay_ms = delay_seconds × 1000 × world.timer_coefficient``.

When the timer fires: apply resources → spawns near start (no population cost) → techs; local human gets LOADOUT_CARD_TRIGGERED voice.

Charge is consumed when the card is scheduled successfully at game start, not when effects fire.


----


4. Voice (TTS)
----------------



.. list-table::
   :header-rows: 1

   * - ID
     - English
     - Use
   * - 5387
     - (effects in)
     - Applied / armory
   * - 5392
     - (after delay)
     - suffix
   * - 5388
     - loadout card effect triggered
     - On fire
   * - 5389–5393
     - spawn / resource / tech hints
     - Armory



Whole minutes announced as “N minutes”; otherwise seconds.


----


5. Vanilla examples
---------------------



.. list-table::
   :header-rows: 1

   * - Card
     - Effect
     - Achievement
   * - ``card_reinforcements_delayed``
     - 3 footman after 10 min
     - ``reinforcement_contract``
   * - ``card_delayed_melee_weapon``
     - ``melee_weapon`` after 8 min
     - ``defeat_expert``




----


6. Tests
----------


.. code-block:: bash

   python -m pytest soundrts/tests/test_cards.py -k delay -v
   python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
