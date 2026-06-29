Achievements, ranks & armory (players)
=======================================


How to use the main-menu Achievements hub — no ``achievements.txt`` syntax.

Mod authors: `../mod/achievement-system <../mod/achievement-system.htm>`_.


----


Where to find it
-----------------


Main menu → Achievements:

1. Achievement list — locked / unlocked; locked entries speak requirement summaries
2. Armory — current rank, honor titles, medal total, card charges

Multi-faction mods (e.g. CrazyMod) ask you to pick a faction first; Back from a sub-menu returns to faction selection.

Cross-faction progress (multi-faction mods only): meta achievements, branch summary, meta honors.


----


What counts?
-------------



.. list-table::
   :header-rows: 1

   * - Game type
     - Achievements / medals / ranks
     - Score voice
   * - Custom or random map vs computer
     - ✅
     - ✅
   * - Campaign, co-op campaign
     - ❌
     - ❌
   * - Multiplayer
     - ❌
     - ✅




----


After a match (non-campaign)
-----------------------------


Vs computer (skirmish), voice usually announces:

1. Score breakdown & letter grade (S–E) — `score-and-grades.md <score-and-grades.htm>`_
2. New achievements, medals, card charges, honor titles
3. Rank promotion, extra loadout slots if applicable

Multiplayer announces item 1 only — no achievements, medals, ranks, or card progress.

Repeat completions may grant medals only (no card/honor/unlock voice again).


----


Per-faction progress (CrazyMod, etc.)
--------------------------------------


- Each faction has its own medals, ranks, and achievement list.
- Saves live under `user/achievements/<mod>/<faction>.json` (normally automatic).
- Random faction: Start may ask you to select your faction for this game.
- Pick a concrete faction in the skirmish setup to skip that step.


----


Cross-faction meta
-------------------


Progress across branches unlocks meta achievements and meta honor titles (e.g. three realms / tenfold mastery). View them under Cross-faction progress. Meta medals do not count toward a single faction’s rank.


----


Pre-mission cards
------------------


See `loadout-cards <loadout-cards.htm>`_.


----


See also
---------


- `Release notes <../../relnotes.htm>`_
- `../mod/achievement-system.md <../mod/achievement-system.htm>`_
