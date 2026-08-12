Unit-line upgrades and top-tier training (line_upgrade)
=======================================================

For **mod authors**: configure “research a unit form → unlock top-tier training → morph field units on the line” in ``rules.txt``, without hardcoding unit names in the engine. Age of Empires II DE barrack sword lines work this way.

Overview
--------

.. list-table::
   :header-rows: 1

   * - Feature
     - Meaning
   * - Top-tier training
     - Building ``can_train`` lists the line root (e.g. ``militia``); training resolves to the highest unlocked form
   * - Researchable line upgrade
     - Mark the form with ``line_upgrade 1`` and put it on a building ``can_research``; on complete it is stored in ``player.upgrades``
   * - Field morph
     - When research completes, field units whose ``can_upgrade_to`` includes that form morph to it instantly
   * - Training cost
     - Default charge is the **line root** ``cost`` / ``time_cost`` (override with ``train_cost`` / ``train_time``)

The engine does **not** hardcode any civilization or unit id — only rule fields and ``can_upgrade_to`` chains.

rules syntax
------------

1. Unit line (``can_upgrade_to``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def militia
    class soldier
    cost 20 0 50 0
    time_cost 21
    can_upgrade_to man_at_arms

    def man_at_arms
    is_a militia
    cost 40 0 100 0
    time_cost 40
    requirements feudal_age
    line_upgrade 1
    can_upgrade_to long_swordsman

- Mid/high-tier ``cost`` / ``time_cost`` usually mean the **research** price (as in DE).
- Training still uses the line-root cost unless ``train_cost`` / ``train_time`` are set.

2. Building: train slots + research slots
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def barracks
    class building
    can_train militia spearman
    can_research tracking squires man_at_arms long_swordsman …

- List only line roots in ``can_train``; the menu maps to the highest unlocked tier.
- After a ``line_upgrade 1`` form is listed in ``can_research``, it can be researched like a tech.

3. Optional tech effect
~~~~~~~~~~~~~~~~~~~~~~~

If you wrap it in ``class upgrade``, you may write::

    effect unit_line_upgrade man_at_arms

Same result as researching that unit form directly (upgrades + morph). Each target applies once per player.

Relation to age auto-morph
--------------------------

.. list-table::
   :header-rows: 1

   * - Flag
     - Behavior
   * - (none)
     - If the phase has ``units_auto_upgrade 1`` and the target ``requirements`` include that age name, units may morph with the age
   * - ``line_upgrade 1``
     - Does **not** auto-morph with age; must be researched; training also requires the name in ``player.upgrades``
   * - ``no_auto_upgrade 1``
     - Skips age auto-morph; training still requires research (same gate as ``line_upgrade``)

For AoE2 DE military lines, prefer ``line_upgrade 1`` (research unlock), not ``units_auto_upgrade`` alone.

The selected-unit menu ``upgrade_to`` no longer offers ``line_upgrade`` forms (avoids per-unit price-diff upgrades, unlike AoE2). Research them on the building ``can_research`` list instead.

Building lines (towers, walls) work the same: ``can_build`` lists the line root; after research the menu maps to the top tier; build cost uses the root (override with ``train_cost``). Use ``line_upgrade_also`` to unlock several forms in one research (e.g. wall upgrade also unlocks fortified gate).

Engine entry points (reference)
-------------------------------

.. list-table::
   :header-rows: 1

   * - Symbol
     - Location
   * - ``resolve_trainable_unit_type``
     - ``soundrts/world_build_rules.py``
   * - ``effective_can_train`` / ``unit_train_cost`` / ``unit_train_time``
     - same
   * - ``apply_unit_line_upgrade``
     - same
   * - ``ResearchOrder.complete``
     - ``soundrts/worldorders/production.py``
   * - ``effect_unit_line_upgrade``
     - ``soundrts/worldupgrade/attribute_effects.py``
   * - Age skip
     - ``soundrts/worldphase.py`` → ``_auto_upgrade_units``
   * - Unit default
     - ``Creature.line_upgrade`` (``worldcreature.py``)
   * - Rules int attr
     - ``definitions.py`` → ``line_upgrade``

Tests
-----

``soundrts/tests/test_train_line_resolve.py``: age alone does not unlock; after upgrades / ``apply_unit_line_upgrade``, top-tier training and morph work.

aoe2 mod
--------

``mods/aoe2/rules.txt`` marks sword, spear, archer, cavalry, siege upgrade forms with ``line_upgrade 1`` and hooks them into barracks / archery range / stable / siege workshop (and civ variants) ``can_research``. Sources: ``mods/aoe2/SOURCES.md``.

See also: `Modding manual <modding.htm>`_.
