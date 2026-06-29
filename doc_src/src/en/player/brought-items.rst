# Bring item to square & story hand-in (``has_brought_item`` + ``remove_item``)

Two triggers used together:

- ``has_brought_item`` (condition): player unit carries an item to a square
- ``remove_item`` (action): remove and destroy the item from inventory (story “hand-in”)

Typical: bring mana potion to shrine → cut scene → potion vanishes → objective complete.

Example: The Legend of Raynor ch. 18 (`18.txt <../../../res/single/The Legend of Raynor/18.txt>`_).


----


1. vs other item triggers
---------------------------



.. list-table::
   :header-rows: 1

   * - Trigger
     - Detects / effect
     - Item location
     - Use case
   * - ``has_item``
     - player holds item
     - any unit inventory
     - found / picked up
   * - ``has_brought_item``
     - carried item at square
     - units on that square
     - deliver by arriving (no drop)
   * - ``find``
     - object on ground
     - dropped on square
     - place item; syntax: square first ``(find c3 mana_potion)``
   * - ``npc_has_item``
     - NPC received item
     - NPC inventory / ``received_items``
     - give to NPC
   * - ``remove_item``
     - destroy from inventory
     - —
     - auto story hand-in




----


2. Condition: ``has_brought_item``
--------------------------------------


.. code-block:: text

   (has_brought_item <square> <item_type> [count])


- Square: e.g. ``c3``, `"3,3"`
- Item type: e.g. ``mana_potion``
- Count: optional, default `1`

True when at least one living player unit on that square holds enough of the item in inventory.

- Empty hands at square → false
- Item elsewhere, unit not at square → false
- Carried to square → true (no drop needed)


----


3. Action: ``remove_item``
------------------------------


.. code-block:: text

   (remove_item <item_type> [square] [count])


- No square: remove from all living player units
- With square: only units on that square
- Count: optional, default `1`

Item is destroyed (like consuming). Pair with ``cut_scene`` for narrative.


----


4. Full example (ch. 18)
--------------------------


.. code-block:: text

   trigger player1 (has_brought_item c3 mana_potion)
       (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))



Chain multiple actions with ``do``. Do not use ``if`` for three actions in a row.

Flow: pick up potion → walk to c3 shrine → condition true → cut scene → item removed → objective 1 done.


----


5. vs give-to-NPC
-------------------



.. list-table::
   :header-rows: 1

   * - Method
     - When
   * - ``npc_has_item`` + player ``give``
     - physical NPC receiver
   * - ``has_brought_item`` + ``remove_item``
     - arrive-and-hand-in, no NPC, auto story




----


6. Related files
------------------



.. list-table::
   :header-rows: 1

   * - Content
     - Path
   * - Implementation
     - ``soundrts/worldplayerbase/triggers.py``
   * - Example map
     - `res/single/The Legend of Raynor/18.txt`
   * - Find item
     - [find-item-objective.md](find-item-objective.htm)
   * - Give to NPC
     - [give-to-npc.md](give-to-npc.htm)

