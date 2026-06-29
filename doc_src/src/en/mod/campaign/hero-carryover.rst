Campaign hero carryover (rules-driven)
=======================================


Single-player campaigns can persist a designated hero across chapters. Everything is configured in :strong:```rules.txt`` / ``campaign.txt`` — no hard-coded unit names. Co-op does not persist heroes (network sync).

Player overview: `../player/campaign-and-co-op-improvements <../player/campaign-and-co-op-improvements.htm>`_ §2.1.1.

Chinese: `../../zh/mod/战役跨章英雄携带说明 <../../zh/mod/战役跨章英雄携带说明.htm>`_.


----


1. Three cross-chapter mechanisms
-----------------------------------



.. list-table::
   :header-rows: 1

   * - Mechanism
     - Where
     - Carries
     - Typical use
   * - ``campaign_carryover``
     - ``rules.txt`` unit fields
     - Level+XP, inventory (optional split)
     - RPG hero growth
   * - ``campaign_flag``
     - Map triggers
     - Story booleans
     - Alliances, side quests
   * - ``add_inventory_item``
     - Map triggers
     - Specific items
     - Tokens, keys




----


2. ``rules.txt`` fields
---------------------------


Set on the root hero def (variants via ``is_a`` inherit).


.. list-table::
   :header-rows: 1

   * - Field
     - Default
     - Meaning
   * - ``campaign_carryover``
     - ``0``
     - ``1`` = enable cross-chapter save
   * - ``campaign_carryover_id``
     - def name
     - ``campaigns.ini`` prefix `hero_<id>_`
   * - ``campaign_carryover_stats``
     - ``1`` when carryover on
     - Level + XP
   * - ``campaign_carryover_inventory``
     - ``1`` when carryover on
     - Backpack items



Examples
~~~~~~~~~


Full carryover (default):

.. code-block:: text

   def my_hero
   is_a knight
   campaign_carryover 1
   inventory_capacity 8
   max_level 20
   xp_threshold_growth linear 100 50
   hp_max_per_level 20


(Explicit ``xp_thresholds 200 500 1000`` still works.)

``Starting level / XP (``level`` / ``xp``):``

Same as the Heroes section in ``mod/modding.rst`` (including ``xp_threshold_growth`` since 1.4.4.7):


.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``level``
     - Starting level (default `1`). Values `> 1` apply cumulative `*_per_level` and ``level_skills`` on spawn.
   * - ``xp``
     - Optional starting cumulative XP.
   * - ``level 0``
     - Start below level 1; status shows level 0 and XP toward `xp_thresholds[0]`.



Cross-chapter restore overrides map defaults; saved level is combined with ``hero_min_level``, then cumulative bonuses are reapplied.

Stats only (no inventory):

.. code-block:: text

   campaign_carryover 1
   campaign_carryover_inventory 0


Inventory only (no stats):

.. code-block:: text

   campaign_carryover 1
   campaign_carryover_stats 0


No carryover: omit ``campaign_carryover 1``.


----


3. ``campaign.txt``: minimum level
--------------------------------------


.. code-block:: text

   hero_min_level 13:2 16:3 19:4


Chapter:level pairs; restored level is ``max(saved, minimum)``.


----


4. Save file (``user/campaigns.ini``)
-----------------------------------------


.. code-block:: ini

   hero_raynor_xp = 1200
   hero_raynor_level = 3
   hero_raynor_inventory = sword,health_potion
   flags = ch24_garrek_token


Updated only on victory; retry after defeat does not overwrite.


----


5. Code
---------


- `soundrts/campaign_hero.py <../../../soundrts/campaign_hero.py>`_
- `soundrts/tests/test_campaign_hero.py <../../../soundrts/tests/test_campaign_hero.py>`_


----


6. Co-op
----------


No hero restore/save; ``campaign_flag`` is also a deterministic no-op in co-op.
