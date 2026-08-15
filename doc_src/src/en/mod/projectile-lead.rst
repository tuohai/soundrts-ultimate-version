Projectile lead (projectile_lead) and per-lane flight speed
===========================================================

For **mod authors**: melee and ranged projectiles each get a **flight speed** (tiles/s); non-projectile attacks are unaffected.

Important: speed, not duration
------------------------------

``rdg_projectile_speed`` / ``mdg_projectile_speed`` (and deprecated ``projectile_speed``) mean **how fast** the projectile travels (tiles per second), **not** “how many seconds until impact”.

- ``7`` → seven tiles per second (AoE2 archer scale)
- Do **not** write ``0.57`` because you want a ~0.57 s hit — that is read as 0.57 tiles/s and feels extremely slow
- Time-to-hit is **derived**: distance ÷ speed (farther = longer)

Overview
--------

.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``rdg_projectile`` + ``rdg_projectile_speed``
     - Ranged projectile **speed** (tiles/s)
   * - ``mdg_projectile`` + ``mdg_projectile_speed``
     - Melee-projectile **speed** (tiles/s, e.g. mangonel)
   * - ``projectile_lead``
     - Ranged only: after travel at that speed, miss if the target left the aim point
   * - ``projectile_speed``
     - **Deprecated** shared name; migrated to the matching lane on load

Speed 0, or that lane is not a projectile → instant hit (no flight).

Dual-attack units
-----------------

If a unit has both ``mdg`` and ``rdg`` (e.g. both ranges 4):

- Only ``rdg_projectile_speed`` → **only ranged** flies at that speed; melee is instant (unless ``mdg_projectile`` + speed too)
- Only ``mdg_projectile_speed`` → **only melee-projectile** flies at that speed
- Normal melee (no ``mdg_projectile``) never flies, even if a speed is written

rules examples
--------------

::

    def aoe_archer
    rdg_projectile 1
    rdg_projectile_speed 7

    def mangonel
    mdg_projectile 1
    mdg_projectile_speed 3.5

    def ballistics
    class upgrade
    effect info 8510
    effect bonus projectile_lead 1
    effect_bonus_targets archer_unit -hand_cannoneer galley scouttower aoe_castle town_center townhall

aoe2 (DE-ish, all **speeds**): arrows/towers ``7``, mangonel ``3.5``, trebuchet ``1.6``.

Deprecated
----------

``mdg_delay`` / ``rdg_delay`` (old “seconds of delay”) and shared ``projectile_speed``: not read in combat; converted/migrated to per-lane **speeds** on load. New mods should set ``*_projectile_speed`` directly.

Engine
-------------

- ``attack_action._calc_projectile_flight_ms(target, is_melee=…)`` (derives arrival ms from speed)
- ``definitions._migrate_legacy_projectile_delay``

See also: `Modding manual <modding.htm>`_, `Release notes <../relnotes.htm>`_ (1.4.6.9).
