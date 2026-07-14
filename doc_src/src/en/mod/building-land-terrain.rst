Configurable square terrain & building land
==============================================

.. epigraph:: For **mod authors**: ``class terrain``, ``class building_land``, object-driven ``square_terrain``, and the map editor palette. Complements ``mapmaking.htm`` and ``modding.htm``.


----

Overview
--------


All terrain is declared in ``rules.txt`` as ``class terrain``; ``style.txt`` uses the same ``def`` names for voice, ``ground``, and colors. Unit ``move_on_<key>`` / ``falling_on_<key>`` match terrain type names or ``ground`` categories — see ``modding.htm`` (Combat sound system).

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
   * - ``cover``
     - Optional. ``cover <ground> <air>`` (e.g. ``cover .5 0`` → 50% ranged cover for ground units). Affects **ranged** hit chance only. Same inheritance/priority as ``speed``
   * - ``speed_vs`` / ``cover_vs`` / ``dodge_vs`` / ``mdg_vs`` / ``rdg_vs`` / ``mdg_cd_vs`` / ``rdg_cd_vs``
     - Optional per-**unit-type** modifiers on this terrain (e.g. ``speed_vs knight .25 archer .5``). ``*_vs`` alone is enough; default ``speed``/``cover`` is optional

Map ``terrain <name>`` writes these flags onto the square. **Movement speed** resolves as:

1. Map ``speed <ground> <air> <squares>`` — all units on that cell
2. Matching ``speed_vs`` for the current unit (``is_a`` inheritance)
3. ``speed`` on ``class terrain`` in ``rules.txt``
4. Default ``(100, 100)``

**Ranged cover** resolves as:

1. Map ``cover`` line — all units
2. Matching ``cover_vs`` for the **target** unit
3. ``cover`` on ``class terrain``
4. Default ``(0, 0)``

Maps do **not** support per-unit ``speed_vs``/``cover_vs`` on individual squares; use map ``speed``/``cover`` or terrain defs in ``rules.txt``.

``editor_palette.txt`` is editor-only: entries without ``speed``/``cover`` inherit from ``rules.txt``; saving writes ``speed``/``cover`` lines. The game does **not** read the palette at runtime.

Ford example (shallow water, half ground speed):

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1

When ``is_ground 1`` is set on water terrain (``ford``, ``big_bridge``), pathfinding treats the tile as part of the **same ground region** as adjacent land, so units can route through fords without getting stuck at the shore.

**Player-built spans** (``wooden_bridge``, ``is_buildable_on_water_only``, ``bridge_terrain bridge_deck``): see `Building bridges on water <water-bridge-building.htm>`_ (`zh <../../zh/mod/water-bridge-building.htm>`_). Map ``big_bridge`` is fixed trestle terrain; finished player spans use ``bridge_deck``.

Unit combat modifiers on terrain (since 1.4.5.0; percent decimals since 1.4.5.1)
---------------------------------------------------------------------------------

Besides per-square ``terrain_speed`` / ``terrain_cover``, use **terrain** ``*_vs`` (by unit type) in ``rules.txt``, or **unit** ``*_on_terrain`` (by terrain name).

**Percent decimals (recommended since 1.4.5.1):** ``.1`` = ±10%, ``.5`` = ±50%, relative to the unit’s current base stat (``mdg``, ``mdg_cd``, ``charge_mdg``, etc.). Examples: ``mdg_on_terrain marsh -.33``, ``speed_vs knight .25``, ``mdg_cd_vs knight .5``.

**Terrain-side** (``class terrain``): ``speed_vs``, ``cover_vs``, ``dodge_vs``, ``mdg_vs``, ``rdg_vs``, ``mdg_cd_vs``, ``rdg_cd_vs`` — multiple pairs per line allowed.

**Unit-side:** ``mdg_on_terrain``, ``rdg_on_terrain``, ``mdg_cd_on_terrain``, ``rdg_cd_on_terrain``, ``charge_*_terrain`` — same percent rules. ``speed_on_terrain`` remains an **absolute** speed override.

**Attributes screen (Alt+V):** lists unit ``*_on_terrain`` / charge terrain lines, and the live damage / cooldown / speed readings include current-square terrain ``*_vs`` plus unit ``*_on_terrain`` (terrain ``*_vs`` = decimal percent; ``speed_on_terrain`` stays absolute).

**Which tile counts:** attacker/mover’s current square ``type_name`` (or ``type_name_at`` for sub-cells). ``cover_vs`` applies to the **target** unit when attacked at range.

Maps: ``speed``/``cover`` lines affect **all** units on a cell; per-unit rules belong in ``rules.txt``.

**Example — marsh slows knights only; forest covers archers only:**

.. code-block:: text

   def marsh
   class terrain
   speed_vs knight .25

   def forest
   class terrain
   cover_vs archer .25

**Example — knight weakened in marsh (unit-side):**

.. code-block:: text

   def knight
   mdg 6
   mdg_cd 1.5
   mdg_on_terrain marsh -.33
   mdg_cd_on_terrain marsh .33

Tests: ``test_combat_terrain_modifiers.py``, ``test_terrain_cover_defaults.py``, ``test_terrain_unit_vs.py``, ``test_unit_on_terrain_percent.py``.

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


Passability, ``go`` orders, and voice feedback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Target squares use the same check as movement (``Square.is_passable_for``). Impassable ``go`` / ``patrol`` orders fail at **queue time** (``order_impossible`` sound).

Without ``passable_units``: ground units blocked by pure water → ``water_impassable``; water units on land → ``land_impassable``; ``is_ground 0`` → ``ground_impassable``; ``is_air 0`` → ``air_impassable``; unfinished bridge scaffold → ``scaffold_impassable``. Message IDs in ``res/ui/style.txt`` ``messages`` (4976–4979, 4978, 5700).

With ``passable_units``: whitelist wins over category flags. Denied units hear their unit ``title`` from ``style.txt`` plus "cannot pass" (``passable_units_denied``, TTS 5701). ``is_a`` inheritance applies (e.g. ``passable_units archers`` allows ``is_a archers``).

``patrol`` and ``move_to_or_fail`` use the same ``_terrain_impassable_reason`` path. Full tables and Chinese prose: ``../../zh/mod/building-land-terrain.htm``.


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

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py soundrts/tests/test_water_impassable_order.py -q

Full tables and Chinese prose: ``../../zh/mod/building-land-terrain.htm``.
