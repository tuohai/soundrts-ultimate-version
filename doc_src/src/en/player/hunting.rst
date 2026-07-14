Hunting system
===============


SoundRTS supports Age of Empires–style hunting: workers attack wildlife, hunted animals leave gatherable food carcasses, and sheep can be herded.


----


1. Player flow
----------------


1. Backspace / default order or right-click an animal → ``attack`` on ``is_huntable`` (plain attack deals damage; imperative not required)
2. On kill → ``food_carcass`` deposit spawns; the attack order completes (**no** false ``order_impossible`` beep)
3. Auto-gather → workers may auto-queue gather on the carcass after the kill; with ``auto_gather`` they also collect and return food
4. Flee on hit → deer and sheep run away; boars fight back
5. Herding (optional) → workers with ``can_herd 1`` can herd ``herdable`` animals (e.g. sheep)


Note: default order on ordinary neutral creeps / NPCs is ``go`` (move only); on huntable animals it remains ``attack``.
Offensive / defensive / chase AI will **not** auto-attack neutral animals unless you issue an imperative attack.


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
     - 35 food, flees when hit
   * - ``sheep``
     - 25 food, herdable, flees
   * - ``boar``
     - 50 food, counter-attacks
   * - ``food_carcass``
     - gatherable carcass (``collision 0``)



Workers ``can_gather`` includes ``food_carcass`` and ``orchard``.

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
   * - ``herdable 1``
     - can be herded by ``can_herd`` workers
   * - ``food_deposit``
     - carcass deposit type on death
   * - ``food_deposit_qty``
     - carcass food amount
   * - ``no_number 1``
     - omit number when only one of that type



Worker: ``can_herd 1`` enables herding (default ``0``).

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

