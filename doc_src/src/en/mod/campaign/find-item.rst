# Find-item victory (``has_item`` trigger)

Design objectives where picking up an item completes the goal.

Core condition: :strong:```has_item`` — does the player hold the item in any living unit’s inventory?


----


1. Overview
-------------



.. list-table::
   :header-rows: 1

   * - Part
     - Name
     - Role
   * - Unit field
     - ``class item``
     - pickable item
   * - Default order
     - ``pickup``
     - right-click ground item
   * - Condition
     - ``has_item``
     - player holds item type



Flow: place item → pickup → ``(has_item …)`` → `` (objective_complete N)`` → victory when all objectives done.


Do not set ``consume_on_pickup 1`` (default 0). If consumed on pickup, ``has_item`` never becomes true.


----


2. ``has_item``
-------------------


.. code-block:: text

   (has_item <item_type> [count])


Counts items in all living player units’ inventories.

.. code-block:: text

   (has_item lost_amulet)
   (has_item lost_amulet 2)



.. list-table::
   :header-rows: 1

   * - Condition
     - Checks
   * - ``has``
     - unit count owned
   * - ``has_item``
     - items in inventory
   * - ``has_brought_item``
     - carried to square
   * - ``npc_has_item``
     - NPC received item
   * - ``find``
     - item on ground at square




----


3. Define quest item
----------------------


.. code-block:: text

   def lost_amulet
   class item


Picker needs ``inventory_capacity \> 0`` (peasant, footman, …).


----


4. Place on map
-----------------


.. code-block:: text

   lost_amulet c3
   lost_amulet 2 c3



----


5. Example (ch. 17)
---------------------


See `17.txt <../../../res/single/The Legend of Raynor/17.txt>`_:

.. code-block:: text

   trigger player1 (timer 0) (add_objective 1 "find the lost amulet")
   trigger player1 (has_item lost_amulet) (objective_complete 1)



----


6. Compound: ch. 20 (carry + use in inventory)
------------------------------------------------


`mystery_treasure <../../../res/single/The Legend of Raynor/20.txt>`_: pick up → ``has_brought_item b2`` → use at shrine (``use_square b2``) → gold reward.


----


7. Compound: ch. 22 (drop + collect coins)
--------------------------------------------


`sealed_treasure <../../../res/single/The Legend of Raynor/22.txt>`_: drop at b2 → ``find`` + ``remove_ground_item`` → spawn ``gold_coin`` → pick all up.


----


8. Compound: ch. 23 (drop = deliver)
--------------------------------------


`war_supplies <../../../res/single/The Legend of Raynor/23.txt>`_: ``has_item`` then ``find c3 war_supplies`` after drop.


.. list-table::
   :header-rows: 1

   * - Chapter
     - Item
     - Delivery
   * - 20
     - ``mystery_treasure``
     - carry + inventory use
   * - 22
     - ``sealed_treasure``
     - drop, open, collect coins
   * - 23
     - ``war_supplies``
     - drop at station




----


9. Ch. 24–27
--------------


Pick up ``secret_letter`` at ``b1`` (same as ``has_item`` flow), then give to leader (``npc_has_item``). See `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


----


10. Implementation
--------------------


- ``lang_has_item`` in ``soundrts/worldplayerbase/triggers.py``
- Example: `res/single/The Legend of Raynor/17.txt`, ``rules.txt`` (``lost_amulet``)
