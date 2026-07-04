Configurable square terrain & building land
==============================================

.. epigraph:: For **mod authors**: ``class terrain``, ``class building_land``, object-driven ``square_terrain``, and the map editor palette. Complements ``mapmaking.htm`` and ``modding.htm``.


----

Overview
--------


All terrain is declared in ``rules.txt`` as ``class terrain``; ``style.txt`` uses the same ``def`` names for voice, footsteps, and colors.

**The engine no longer assigns a default terrain to every square.** A square’s terrain comes only from:

1. Map ``terrain <name> <squares>``
2. Object ``square_terrain`` (woods, towns, meadows, etc.)
3. ``high_grounds`` / ``is_high_ground`` — extra “high ground” voice only, not a terrain name


Definitions & placement
-----------------------


**rules.txt:**

.. code-block:: text

   def plain
   class terrain
   is_dynamic 1

   def lake
   class terrain
   is_water 1
   is_dynamic 0

**Map:**

.. code-block:: text

   terrain plain a1
   terrain lake d1
   terrain hill c1
   high_grounds e1

- ``terrain lake d1`` does **not** need a separate ``water d1`` line
- Legacy ``water`` keyword still works
- Squares without ``terrain``: empty ``type_name``, no terrain voice


Building land (``class building_land``)
---------------------------------------


``meadow``, ``build_site``, and custom types are no longer hard-coded. Declare them with **`class building_land`** in ``rules.txt``.

.. code-block:: text

   def meadow
   class building_land
   square_terrain meadows 40

   def build_site
   class building_land
   square_terrain build_sites 50

.. list-table::
   :header-rows: 1

   * - Mechanism
     - Role
   * - ``default_building_land``
     - Rules default when the map omits ``building_land``
   * - Map ``building_land <name>``
     - Whole-map default building-land type
   * - ``nb_<type>_by_square <N>``
     - Auto-fill every square with N objects of that ``class building_land`` type
   * - ``nb_meadows_by_square <N>``
     - Legacy; type from ``building_land`` / map inference
   * - ``additional_building_land <name> <squares…>``
     - Place any declared building-land type on listed squares

When lift-off or some upgrades restore building land in place, the engine uses **the type saved when the building was placed** first; only if missing, it falls back to the map’s ``building_land`` or a sole ``nb_<type>_by_square`` keyword.

See ``mapmaking.htm`` (*Building_land*, *Nb_<type>_by_square*).


``class terrain`` attributes
----------------------------


.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``is_dynamic``
     - ``0`` static; ``1`` can be overridden by object terrain
   * - ``is_ground`` / ``is_air`` / ``is_water``
     - Ground / air / water passability flags
   * - ``is_high_ground``
     - High ground + voice
   * - ``passable_units``
     - Whitelist (``is_a`` inheritance applies)
   * - ``blocks_path``
     - Blocks exits to neighbors (e.g. dense forest, mountain)
   * - ``speed``
     - Optional. ``speed <ground> <air>`` (e.g. ``speed .5 1`` → 50% ground speed). Applied when the map sets ``terrain <name>``; per-square map ``speed`` lines override

Map ``terrain <name>`` writes these flags onto the square. **Movement speed** on a square (not the same as unit ``speed_on_terrain``) resolves as:

1. Map ``speed <ground> <air> <squares>`` — authoritative at runtime
2. ``speed`` on the ``class terrain`` in ``rules.txt`` — when the map has ``terrain`` but no ``speed`` for that cell
3. Default ``(100, 100)``

``editor_palette.txt`` is editor-only: palette entries without ``speed`` inherit from ``rules.txt`` when the palette is loaded; saving the map writes ``speed`` lines. The game does **not** read the palette at runtime.

Ford example (shallow water, half ground speed):

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1

When ``is_ground 1`` is set on water terrain (``ford``, ``big_bridge``), pathfinding treats the tile as part of the **same ground region** as adjacent land, so units can route through fords without getting stuck at the shore.

**Player-built spans** (``wooden_bridge``, ``is_buildable_on_water_only``, ``bridge_terrain bridge_deck``): see `Building bridges on water <water-bridge-building.htm>`_ (`zh <../../zh/mod/water-bridge-building.htm>`_). Map ``big_bridge`` is fixed trestle terrain; finished player spans use ``bridge_deck``.

Unit combat modifiers on terrain (since 1.4.5.0)
------------------------------------------------

Besides per-square ``terrain_speed``, unit defs can override movement and combat stats **by the terrain the unit stands on**. Syntax matches ``speed_on_terrain``:

.. code-block:: text

   <terrain_name> <modifier> [<terrain_name> <modifier> ...]

**Which tile counts:** the **attacker/mover's current square** ``type_name`` (or ``type_name_at`` for sub-cell terrain).

**Stacking:** modifiers are **additive** (negative = penalty), applied after ``mdg_vs`` / ``mdg_cd_vs`` etc. Values use the same units as ``mdg`` / ``mdg_cd`` (decimals allowed; stored ×1000 internally).

.. list-table::
   :header-rows: 1

   * - Property
     - Effect
   * - ``speed_on_terrain``
     - Movement speed on that terrain (existing behaviour)
   * - ``mdg_on_terrain`` / ``rdg_on_terrain``
     - Melee / ranged damage bonus (after base + ``*_vs``)
   * - ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``
     - Attack cooldown bonus (**positive = slower attacks**)
   * - ``charge_mdg_terrain`` / ``charge_rdg_terrain``
     - Extra charge damage bonus (after ``charge_mdg`` + ``charge_*_vs``)
   * - ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``
     - Charge cooldown bonus (positive = longer charge cooldown)

Hit/dodge on **target** terrain (existing): ``mdg_cover_on_terrain``, ``rdg_cover_on_terrain``, ``mdg_dodge_on_terrain``, ``rdg_dodge_on_terrain``.

**Example — knight weakened in marsh:**

.. code-block:: text

   def knight
   speed 2.5
   mdg 6
   mdg_cd 1.5
   speed_on_terrain marsh 1.5 ford 1.5
   mdg_on_terrain marsh -2
   mdg_cd_on_terrain marsh 0.5

On ``marsh``: speed 1.5, melee damage 4, attack cooldown 2.0 s.

**Example — unit with charge:**

.. code-block:: text

   def raynor
   charge_mdg 4
   charge_mdg_cd 10
   charge_mdg_terrain marsh -1
   charge_mdg_cd_on_terrain marsh 2

On ``marsh``: charge bonus −1, charge cooldown +2 s.

Implementation: ``soundrts/combat/damage_calculation.py``, ``soundrts/combat/attack_action.py``; tests: ``test_combat_terrain_modifiers.py``.

Types in ``res/rules.txt`` include ``plain``, ``lake``, ``marsh``, ``mountain``, ``forest``, ``dense_forest``, ``meadows``, ``build_sites``, ``town``, ``ford``, etc.


``square_terrain``: object-driven terrain
------------------------------------------


**Map ``terrain`` paints the base layer; ``square_terrain`` lets objects grow the upper layer** that can appear and disappear at runtime.

Syntax on any ``def``:

.. code-block:: text

   square_terrain <terrain_name> [priority] [min_count]

- ``priority`` (default 50): higher wins
- ``min_count`` (default 1): minimum objects of that ``type_name`` on the square

Example — forest vs dense forest:

.. code-block:: text

   def wood
   class deposit
   square_terrain forest 80
   square_terrain dense_forest 90 7

Each tick, ``update_terrain()`` picks the highest-priority eligible entry and sets the square’s ``type_name``. Building land has a separate voice layer (``building_land_voice`` vs ``feature_voice``).

Dynamic ``terrain forest`` on the map spawns matching objects via reverse ``square_terrain`` links (see Chinese doc for full tables).


Voice layers
~~~~~~~~~~~~


``resolve_square_layers()`` may stack:

- ``feature_voice`` — winning object terrain (``forest``, ``town``, …)
- ``building_land_voice`` — ``meadows`` / ``build_sites`` when different from feature
- ``high_ground_voice`` — high ground marker


Map editor palette
------------------


Console ``edit``; bindings in ``res/ui/editor_bindings.txt``. Logic in ``soundrts/lib/editor_palette.py``.

- Static terrains (``lake``, ``mountain``, …): ``fixed_terrain``, saved as ``terrain <name>``
- Dynamic terrains (``forest``, ``meadows``, …): spawn objects, not locked
- Palette names aligned with ``res/ui/editor_palette.txt`` (``forest`` not legacy ``woods``)


Tests
-----


.. code-block:: bash

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py -q

Full tables and Chinese prose: ``../../zh/mod/building-land-terrain.htm``.
