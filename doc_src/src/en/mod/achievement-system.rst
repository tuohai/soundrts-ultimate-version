Achievement System
===================



Player guide (menus, progress, what counts): `../player/achievements.htm <../player/achievements.htm>`_

Implementation reference. Chinese version: `../../zh/mod/achievement-system <../../zh/mod/achievement-system.htm>`_.

Status
-------



.. list-table::
   :header-rows: 1

   * - Phase
     - Status
     - Summary
   * - 1
     - Done
     - Definitions, per-mod save, post-game unlock, achievement list
   * - 2
     - Done
     - Medals, cards, ranks & honor titles, armory
   * - 3
     - Done
     - Pre-mission loadout in TrainingGame, apply effects, consume charges
   * - Scheme D
     - Done
     - Per-faction saves (``achievements_per_faction``), faction picker in menus
   * - Meta progress
     - Done
     - Cross-faction ``\_meta.json``, aggregate conditions, ``scope meta``



Key code
---------



.. list-table::
   :header-rows: 1

   * - File
     - Role
   * - ``soundrts/achievements.py``
     - Load, evaluate, rewards, persist, announce
   * - ``soundrts/faction_progress.py``
     - Per-faction paths, faction matching, menu picker
   * - ``soundrts/meta_progress.py``
     - Cross-faction meta save (``\_meta.json``), snapshot aggregation
   * - ``soundrts/cards.py``
     - Card definitions
   * - ``soundrts/titles.py``
     - Rank ladder + honor titles
   * - ``soundrts/achievements_menu.py``
     - Hub: faction picker, achievement list, armory, meta progress
   * - ``soundrts/game.py``
     - `_say_achievements()` after `say_score()` (skipped in campaign)
   * - ``soundrts/lib/resource.py``
     - Loads achievements + cards + titles with rules
   * - ``res/achievements.txt``
     - Base achievements
   * - ``mods/\<mod\>/achievements.txt``
     - Mod append / override



Save paths
-----------



.. list-table::
   :header-rows: 1

   * - Path
     - When
   * - ``user/achievements/\<mod_key\>.json``
     - Default (single save per mod)
   * - ``user/achievements/\<mod_key\>/\<faction\>.json``
     - ``achievements_per_faction 1``
   * - ``user/achievements/\<mod_key\>/\_meta.json``
     - Cross-faction meta (``achievements_per_faction 1``)



Enable per-faction mode in mod ``rules.txt``:

.. code-block:: text

   def parameters
   achievements_enabled 1
   achievements_per_faction 1


- Faction-tagged defs use `faction <race_id>`; omit ``faction`` on global cards (shared across branches).
- Main menu Achievements picks a faction first (multi-faction mods); back from list/armory returns to faction picker.
- Cross-faction progress entry opens meta achievement list + meta armory (active branches, map milestones, meta honors).

Campaign: ``game.is_campaign_session()`` skips score, achievements, medals, rank promotion, and stats recording.

Multiplayer: ``game_type_name == "multiplayer"`` skips achievements, medals, rank promotion, and card progress; score voice and play-time stats still run (see `score-grading-system.htm <score-grading-system.htm>`_).

Definition snippet
-------------------


.. code-block:: text

   def grade_s
   title 5300
   condition grade S
   once_per map_ai
   reward medal 50
   reward card card_mixed_army


Meta achievement (``scope meta``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def meta_three_branches
   scope meta
   title 79950
   condition factions_unlocked_at_least 3 1
   once
   reward title honor_meta_novice


Aggregate conditions (read all faction saves):


.. list-table::
   :header-rows: 1

   * - Condition
     - Meaning
   * - ``factions_unlocked_at_least N M``
     - At least N branches each unlocked ≥M achievements
   * - ``factions_medals_at_least N M``
     - At least N branches with ≥M medals
   * - ``factions_honors_at_least N M``
     - At least N branches each with ≥M honor titles
   * - ``factions_achievement_id_contains_at_least N \<substr\>``
     - At least N branches unlocked an achievement whose id contains `<substr>` (e.g. ``\_map_``)



Meta rewards are stored in ``\_meta.json``. Meta medals do not count toward per-faction ranks. Meta honor titles have no ``faction`` field.

See the zh doc for the full directive list (``condition``, ``reward``, ``repeat_medal``, ``cards.txt``, ``titles.txt``).

Repeat completion: if the same ``once`` key was already awarded, ``repeat_medal \<n\>`` grants medals only (no card/honor/unlock voice).

AI difficulty normalization: custom faction AI script names map to canonical tiers for cumulative defeat counters; legacy save keys migrate on load.

Runtime flow
-------------


.. code-block:: text

   Main menu → Achievements
     ├─ (multi-faction) pick faction → list / armory → back → pick faction again
     └─ (multi-faction) cross-faction progress → meta list / meta armory
   
   game.post_run()
     → say_score()              # skipped in campaign
     → _say_achievements()      # faction unlocks, then meta unlocks, rewards, rank-up
                                # skipped in campaign and multiplayer


Save format (faction or single-mod)
------------------------------------


.. code-block:: json

   {
     "unlocked": { "grade_s": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "grade_s|map:jl1|ai:beginner": true },
     "medals": 50,
     "honors": ["honor_nightmare_slayer"],
     "ai_defeats": { "beginner": 5 },
     "map_ai_defeats": { "pra1": { "beginner": 3 } },
     "cards": { "card_infantry": { "charges": 1, "total_earned": 1 } }
   }


Meta save (``\_meta.json``) — no ``cards`` / ``ai_defeats`` / ``map_ai_defeats``:

.. code-block:: json

   {
     "unlocked": { "meta_three_branches": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "meta_three_branches": true },
     "medals": 25,
     "honors": ["honor_meta_novice"]
   }


Legacy saves missing fields are normalized on load.

Phase 3 (done)
---------------


- After Single player → Start on map → Start, pick up to N cards (N = rank ``loadout_slots``)
- Effects apply after map populate (immediate or after ``delay`` / ``delay_minutes``); one charge consumed per card at game start
- Card fields: ``spawn``, ``resource``, ``tech``; combo cards supported; delayed cards documented in `delayed-card-loadout.htm <delayed-card-loadout.htm>`_
- Card spawns consume population
- TrainingGame only (skirmish vs AI); not campaign or multiplayer
- Cards may require ``min_rank`` in ``cards.txt``

Mod opt-out
------------


.. code-block:: text

   def parameters
   achievements_enabled 0


Hides the main-menu Achievements entry, skips post-game unlocks, loadout, and in-game card apply; does not load ``achievements.txt`` / ``cards.txt`` / ``titles.txt``. Save files are kept if you re-enable later.

CrazyMod example
-----------------


``mods/crazyMod9beta10`` uses scheme D + four meta tiers (``meta_three_branches`` … ``meta_ten_masters``) and per-faction map milestones (``trad_map_pra1`` … ``delf_map_pra10``).

Tests
------


.. code-block:: bash

   python -m pytest soundrts/tests/test_achievements.py -v
   python -m pytest soundrts/tests/test_faction_progress.py -v
   python -m pytest soundrts/tests/test_meta_progress.py -v
   python -m pytest soundrts/tests/test_achievements_menu_navigation.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
   python -m pytest soundrts/tests/test_card_loadout.py -v
