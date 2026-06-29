Score & Grading System
=======================



Player guide: `../player/score-and-grades.md <../player/score-and-grades.htm>`_

This document describes SoundRTS post-game multi-dimensional scoring, letter grades, and voice announcements.

Chinese version: `../../zh/mod/score-grading-system.htm <../../zh/mod/score-grading-system.htm>`_

For integration with achievements, see section 9 of `achievement-system <achievement-system.htm>`_. Achievements read ``score_breakdown()``; they do not reimplement scoring.


----


1. When scoring runs
----------------------



.. list-table::
   :header-rows: 1

   * - Scenario
     - Score announcement
     - History stats
   * - Custom / random map vs AI (TrainingGame)
     - ✅
     - ✅
   * - Multiplayer
     - ✅
     - ✅
   * - Campaign / co-op campaign
     - ❌
     - ❌
   * - Spectator
     - ❌ (“spectating finished”)
     - ❌



When ``game.is_campaign_session()`` is true, ``say_score()`` and ``\_record_stats()`` are skipped.

End-of-game order (``game.post_run()``): ``say_score()`` first, then ``\_say_achievements()``.


----


2. Score structure
--------------------


.. code-block:: text

   total = base_total + ai_defeat



.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``base_total``
     - Sum of seven base dimensions, cap 800
   * - ``ai_defeat``
     - Bonus for defeated enemy computers, not counted toward 800
   * - ``total``
     - `base_total + ai_defeat`; can exceed 800
   * - ``percent``
     - `base_total × 100 ÷ 800`, capped at 100%
   * - ``max``
     - Always 800 (denominator for percent; excludes ai_defeat)
   * - ``grade_total``
     - Score used for letter grade (defeat cap; see §5)



Seven base dimensions
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Dimension
     - Key
     - Range
     - Notes
   * - Outcome
     - ``outcome``
     - 0 or 200
     - Win 200, loss 0
   * - Mining
     - ``mining``
     - 0–100
     - vs map deposit capacity or reference
   * - Efficiency
     - ``efficiency``
     - 0–100
     - utilization or frugal (see §4)
   * - Survival
     - ``survival``
     - 0–100
     - friendly unit loss rate
   * - Building defense
     - ``building_defense``
     - 0–100
     - friendly building losses
   * - Combat
     - ``combat``
     - 0–100
     - kills vs enemy production
   * - Demolition
     - ``demolition``
     - 0–100
     - enemy buildings destroyed



Summary lines (for announcements)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Formula
   * - ``unit_line``
     - `survival + combat`
   * - ``building_line``
     - `building_defense + demolition`
   * - ``mining_by_resource[]``
     - per-resource mining score




----


3. Dimension formulas
-----------------------


All dimension scores use ``\_clamp_score()`` to 0–100 (outcome is 0 or 200). Internal amounts use fixed-point integers (``PRECISION``); announcements divide by ``PRECISION`` for display.

3.1 Outcome
~~~~~~~~~~~~


- Victory: `200`
- Defeat: `0`

Double weight vs other single dimensions.

3.2 Mining
~~~~~~~~~~~


Effective gathered = ``gathered[i] - starting_resources[i]`` (sum per resource, floored at 0). Starting stock does not count.

With map capacity (``sum(world.map_deposit_capacity) \> 0``):

.. code-block:: text

   mining = clamp(effective_gathered × 100 ÷ total_map_capacity)


Capacity is accumulated from each map ``Deposit`` at load time (``worldresource.py``).

Without map capacity:

- Campaign: win → 100; loss → 0
- Non-campaign: if effective gathered ≤ 0 → 0; else:

.. code-block:: text

     mining = clamp(effective_gathered × 100 ÷ 1000)

  (``MINING_REFERENCE_GATHER`` = 1000 in display units)

Per-resource scores follow the same rules in ``mining_by_resource[i]``.

3.3 Efficiency
~~~~~~~~~~~~~~~


.. code-block:: text

   utilization_percent = clamp(consumed ÷ gathered × 100)   // 0 if gathered is 0


- Default `efficiency_mode = "utilization"`: `efficiency = utilization_percent`
- Frugal `efficiency_mode = "frugal"` (win only, utilization < 50%):
  ``efficiency = clamp((1 - consumed/gathered) × 100)``  
  Announcement uses “frugal efficiency” (TTS 5251) instead of “resource utilization” (5227).

On defeat, frugal mode never applies.

3.4 Survival
~~~~~~~~~~~~~


.. code-block:: text

   if produced(unit) > 0:
       survival = clamp((produced - lost) × 100 ÷ produced)
   else:
       survival = 0


3.5 Building defense
~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   building_defense = max(0, 100 - lost(building) × 5)


5 points lost per friendly building.

3.6 Combat
~~~~~~~~~~~


Sum ``produced(unit)`` over non-allied, non-neutral enemies as ``enemy_units``:

.. code-block:: text

   if enemy_units > 0:
       combat = clamp(killed(unit) × 100 ÷ enemy_units)
   else:
       combat = clamp(killed(unit) × 5)


3.7 Demolition
~~~~~~~~~~~~~~~


.. code-block:: text

   demolition = clamp(killed(building) × 5)


5 points per enemy building (cap 100 at 20 buildings).

3.8 AI defeat bonus (``ai_defeat``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


For each defeated enemy computer, add ``defeat_score`` by difficulty:


.. list-table::
   :header-rows: 1

   * - Built-in tier
     - Default defeat_score
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



From ``defeat_score \<n\>`` in the AI’s ``ai.txt`` block; custom AI names without it score 0.

Excluded: allied computers, not defeated, AI types ``timers`` / ``ai2`` / empty, ``defeat_score 0``, non-computer players. Defeated players in ``ex_players`` still count.


----


4. Letter grades
------------------


From ``grade_total`` (``score_grade_msg()`` / ``score_grade_letter()``):


.. list-table::
   :header-rows: 1

   * - Grade
     - Minimum grade_total
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



Defeat grade cap
~~~~~~~~~~~~~~~~~


On loss: ``grade_total = min(total, 479)`` (``DEFEAT_GRADE_MAX_TOTAL``). Letter grade cannot exceed D on defeat even if combat/demolition inflate ``total``.


----


5. Raw stat events
--------------------


``Stats.add(event, target, inc)`` during the match:


.. list-table::
   :header-rows: 1

   * - event
     - target
     - Typical trigger
   * - ``gathered``
     - resource index
     - mining, starting resources, card grants
   * - ``produced``
     - ``unit`` / ``building``
     - training complete
   * - ``lost``
     - ``unit`` / ``building``
     - friendly destroyed
   * - ``killed``
     - ``unit`` / ``building``
     - enemy destroyed



``consumed(i) = gathered(i) - player.resources[i]``.

``stats.freeze()`` at game end fixes ``game_duration`` for the time announcement.


----


6. Voice announcements (``score_msgs``)
-------------------------------------------


Order:

1. Win/loss + duration + outcome points
2. Units: produced / lost / killed + ``unit_line``
3. Buildings: produced / lost / killed + ``building_line``
4. Each resource: gathered / consumed + per-resource mining score
5. Efficiency line (frugal or utilization label)
6. Each defeated AI tier [× count] + bonus
7. Total / 800 / percent%
8. Letter grade + history explanation

TTS IDs: ``soundrts/msgparts.py`` (5225–5243, 5251) and ``res/ui/tts.txt``.


----


7. Achievement integration
----------------------------


``achievements.build_context()`` reads from ``score_breakdown()``:


.. list-table::
   :header-rows: 1

   * - Condition
     - Source
   * - ``condition grade S`` etc.
     - `score_grade_letter(total)`
   * - ``condition victory``
     - `player.has_victory`
   * - ``condition utilization_below N``
     - ``utilization_percent`` (win required)
   * - ``condition survival_at_least N``
     - ``survival``
   * - ``condition building_defense_at_least N``
     - ``building_defense``
   * - ``condition defeated_ai expert`` etc.
     - ``ai_defeat_entries``




----


8. Mod customization
----------------------


ai.txt — defeat bonus
~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def my_custom_ai
   defeat_score 55


``defeat_score 0`` disables bonus for that AI.


----


9. Related files
------------------



.. list-table::
   :header-rows: 1

   * - Path
     - Role
   * - ``soundrts/worldplayerstats.py``
     - Scoring, grades, messages
   * - ``soundrts/definitions.py``
     - ``DEFAULT_AI_DEFEAT_SCORE``, `get_ai_defeat_score()`
   * - ``soundrts/worldresource.py``
     - ``map_deposit_capacity``
   * - ``soundrts/game.py``
     - `say_score()`, `post_run()`
   * - ``soundrts/achievements.py``
     - Reads breakdown for unlocks




----


10. Tests
-----------


.. code-block:: bash

   python -m pytest soundrts/tests/test_score_breakdown.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v



----


11. Design constants
----------------------



.. list-table::
   :header-rows: 1

   * - Constant
     - Value
     - Role
   * - ``SCORE_BASE_MAX``
     - 800
     - Base maximum
   * - ``OUTCOME_MAX``
     - 200
     - Outcome weight
   * - ``DEFEAT_GRADE_MAX_TOTAL``
     - 479
     - Defeat grade cap (D)
   * - ``MINING_REFERENCE_GATHER``
     - 1000
     - Reference when no deposits



Not scored today: game duration, tech progress. ``game_duration`` is announcement-only.

Percent reflects base seven dimensions only, not AI defeat bonus.
