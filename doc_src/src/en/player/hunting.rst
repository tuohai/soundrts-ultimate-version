Hunting system
===============


SoundRTS supports Age of Empires–style hunting: workers attack wildlife, hunted animals leave gatherable food carcasses, and sheep can be herded.


----


1. Player flow
----------------


1. Backspace / default order or right-click an animal → ``go`` (approach / claim), including **owned** livestock; workers with ``can_herd`` still default to ``herd`` on ``herdable``. To **attack** (hunt / slaughter), use imperative (Ctrl+Backspace) or select ``go`` then Ctrl+Enter
2. On kill → a deposit named by the animal's ``food_deposit`` spawns (base game: ``food_carcass``; aoe2 sheep: ``food_livestock``); the attack order completes (**no** false ``order_impossible`` beep)
3. Auto-gather → workers may auto-queue gather on the carcass after the kill; with ``auto_gather`` they also collect and return food
4. Flee on hit → deer and sheep run away; boars counterattack and pursue across squares (``pursue_attacker``, can be lured to the town center; ``pursue_leash_range`` drops aggro if you open a large gap)
5. Claim (optional) → any non-neutral unit near a neutral ``claimable`` animal (AoE2-style sheep) takes ownership, with a confirmation sound and a short “sheep , claimed” style tip; ``can_herd`` is separate and still only follows
6. Herding (optional) → workers with ``can_herd 1`` can herd ``herdable`` animals (e.g. sheep)
7. Pasture (optional) → a building with ``spawns_unit`` / ``spawn_player_cap`` (aoe2 Mongol ``pasture``) periodically spawns owned livestock; ``spawn_immediate 1`` means **one** sheep on complete, then top up toward ``larva_cap`` on the interval. Mongol herdsmen build no mill/farm; pasture only needs a town center and can store food


Note: default order on **all** neutral units (wildlife, creep, NPCs) is ``go`` (move / approach). Offensive / defensive / chase AI will **not** auto-attack neutrals unless you issue an imperative attack.


----


2. Voice: "animal" label (not NPC)
------------------------------------


Hunt animals are placed with ``computer_only ... neutral`` but are not announced as "neutral NPC".


.. list-table::
   :header-rows: 1

   * - Situation
     - Example announcement
   * - Select a deer
     - deer , animal
   * - Square summary
     - , 2 deer , animal
   * - Ctrl+Shift+F4 to wildlife-only player
     - you are animal



Rules:

- Units with ``is_huntable 1`` or ``herdable 1`` → wildlife → announced as animal
- A comma separates the unit name and animal (same pattern as enemy/ally labels)
- Ctrl+Shift+F4 says you are animal only when every living unit on that player is wildlife; mixed ``quest_npc`` + deer still says you are neutral NPC

Story NPCs (``quest_npc``, etc.) keep neutral , NPC.


----


3. Map placement
------------------


.. code-block:: text

   computer_only 0 0 neutral b3 4 deer 2 sheep


Random maps also spawn orchards and wildlife near start positions.

3.1 Diplomacy: wildlife are not allies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Wildlife are spawned via ``computer_only``, but they do not join the default ``"ai"`` computer alliance and cannot ally with players or other factions.


.. list-table::
   :header-rows: 1

   * - Rule
     - Meaning
   * - Detection
     - The ``computer_only`` slot contains only units with ``is_huntable 1`` or ``herdable 1`` (deer, sheep, a custom tiger, etc.)
   * - Engine
     - That computer gets `alliance = None`; ``allied`` is only itself
   * - Multiple herds
     - Each ``computer_only`` line is a separate hunting spot; herds do not ally with each other
   * - Mixed slot
     - If the same line mixes animals and footmen, the whole slot stays a normal AI and joins `"ai"`
   * - Player diplomacy
     - Neutral players cannot F12-alliance; wildlife are never a diplomatic faction



Custom animal (isolated from ``"ai"``):

.. code-block:: text

   def tiger
   class soldier
   is_huntable 1
   ...
   
   computer_only 0 0 neutral 5,5 2 tiger


To make several wildlife groups act as one "nature faction", use trigger ``(alliance …)`` explicitly; that is not default hunting behavior.


----


4. rules.txt
--------------


Built-in units
~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Type
     - Notes
   * - ``deer``
     - 35 food, flees when hit; ``food_deposit food_carcass``
   * - ``sheep``
     - herdable, flees; base game ``food_carcass``, aoe2 ``food_livestock``
   * - ``boar``
     - 50 food, counterattacks and pursues across squares (``pursue_attacker``); ``food_deposit food_carcass``
   * - ``food_carcass``
     - hunt carcass deposit (``collision 0``)
   * - ``food_livestock``
     - aoe2 herdable carcass (shepherd bonuses target this)


Workers ``can_gather`` / ``can_gather_deposit`` should list every carcass type they may gather (e.g. ``food_carcass``, and in aoe2 also ``food_livestock``), plus ``orchard`` when used.

**Separate shepherd / hunter bonuses (rules-driven):** use different ``food_deposit`` types, then ``on_phase`` / tech ``gather_time_<deposit>`` (e.g. Britons ``gather_time_food_livestock``, Mongols ``gather_time_food_carcass``). The engine keys bonuses by deposit ``type_name``; AI hunting allows any deposit produced by ``is_huntable`` animals — no civ names in code.

Animal properties
~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Property
     - Meaning
   * - ``is_huntable 1``
     - huntable; right-click defaults to attack
   * - ``flee_on_hit 1``
     - run away from attacker
   * - ``pursue_attacker 1``
     - after counterattack, keep chasing across squares (boar lure to TC)
   * - ``pursue_leash_range``
     - max distance to the chase target in mm; beyond it, forget and return home (``0`` = no limit; boars use ``48000`` ≈ 4 squares)
   * - ``herdable 1``
     - can be herded by ``can_herd`` workers
   * - ``claimable 1``
     - while neutral, any nearby non-neutral unit claims ownership (AoE2 sheep); keeps ``can_herd`` as a separate follow mechanic
   * - ``claim_range``
     - claim distance in mm (``0`` = same square only; aoe2 sheep use ``12000``)
   * - ``food_deposit``
     - carcass deposit type on death
   * - ``food_deposit_qty``
     - carcass food amount
   * - ``no_number 1``
     - omit number when only one of that type



Worker: ``can_herd 1`` enables herding (default ``0``).

Pasture buildings (optional): ``spawns_unit sheep``, ``larva_spawn_time``, ``larva_cap`` (per-square max), ``spawn_player_cap`` (player-wide living count; aoe2 pasture uses ``30``), ``spawn_immediate 1`` (spawn **one** when the building is ready — not a full ``larva_cap`` dump; hatcheries without ``spawn_immediate`` still fill to cap).

Custom animal example
~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def wolf
   class soldier
   is_huntable 1
   flee_on_hit 1
   food_deposit food_carcass
   food_deposit_qty 40
   no_number 1
   ai_mode guard


Technology
~~~~~~~~~~~


``hunting_techniques``: faster orchard/carcass gathering, more yield, bonus carcass food on animals. Researched at town hall.


----


5. Wildlife vs story NPCs
---------------------------



.. list-table::
   :header-rows: 1

   * - 
     - Wildlife
     - Story NPC
   * - Examples
     - ``deer``, ``sheep``, ``boar``
     - ``quest_npc``, ``npc_knight``
   * - Detection
     - ``is_huntable`` / ``herdable``
     - (may have ``receive_items``)
   * - Voice
     - animal
     - neutral , NPC
   * - Player auto-attack
     - no (forced attack required)
     - no



See `unit-default-behavior <unit-default-behavior.htm>`_.


----


6. Code & tests
-----------------



.. list-table::
   :header-rows: 1

   * - Role
     - Path
   * - Hunting logic
     - ``soundrts/worldunit/worldcreature.py``, ``worldworker.py``
   * - Wildlife alliance isolation
     - ``soundrts/worldplayerbase/base.py``, ``world/world_objects.py``
   * - Animal voice
     - ``soundrts/clientgameentity/properties.py``
   * - Change-player voice
     - ``soundrts/clientgame/game_resources.py``
   * - RMG spawns
     - ``soundrts/randommap.py``
   * - Tests
     - ``soundrts/tests/test_hunting.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``

