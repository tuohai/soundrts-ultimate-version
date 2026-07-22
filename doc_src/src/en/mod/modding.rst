
Modding guide
:::::::::::::

.. contents::

mods
-----

The rules of the game and the aspect of the game can be changed by mods.

A mod is a folder potentially containing rules.txt, ai.txt, ui (and their localized versions). The structure of the tree is the same as the "res" folder structure.

The mods are stored in the "mods" folder of the main folder or the "mods" folder of the user's folder. To be activated, a mod must be referenced in the "mods =" parameter in SoundRTS.ini.
For example: mods = soundpack,mymod,my_other_mod

The rules.txt file will patch the default file. For example, a rules.txt file containing these 2 lines: "def peasant" and "decay 20" will cause any peasant to disappear after 20 seconds.

Mod localization (ui-xx)
>>>>>>>>>>>>>>>>>>>>>>>>

Mod folders mirror the ``res`` tree. Add localized folders next to ``ui/`` (``ui-zh``, ``ui-fr``, ``ui-de``, etc.). The game loads the language from ``cfg/language.txt`` (or the system locale); missing entries fall back to ``ui/tts.txt``.

Recommended layout (``mods/mymod/``)::

    ui/style.txt          ; title 7000
    ui/tts.txt            ; 7000 Pig Farm
    ui-zh/tts.txt         ; 7000 猪圈
    ui-fr/tts.txt         ; 7000 Ferme à porcs
    mod.txt               ; optional: dependencies and menu title (below)

What you can translate (once the mod is active):

- Unit/building/faction names: ``title \<ID\>`` in ``style.txt`` + the same ID in each ``tts.txt``
- Unit intros: ``intro \<ID\>`` + ``tts.txt``
- Maps/campaigns inside the mod: map ``title``/``intro`` TTS IDs; campaign folders may use ``campaign.txt`` ``title`` (same as ``res/single`` campaigns)
- Full phrases: in ``tts.txt``, ``english phrase = translated phrase``

Mod menu display name (Options → Mods, since 1.4.2.4):

Add a ``title`` line to ``mod.txt``, same syntax as ``campaign.txt`` — TTS ID or space-separated words::

    title 7100

Define that ID in ``ui/tts.txt`` and each ``ui-xx/tts.txt`` (e.g. ``7100 Orc Faction Mod`` / ``7100 兽人模组``). Without ``title``, the folder name is spoken.

Alternatively, map folder names via phrase entries in global ``res/ui-zh/tts.txt`` or a small translation mod, e.g. ``crazyMod9beta10 = 疯狂模组``.

Notes: ``rules.txt`` / ``ai.txt`` are not localized. Localized ``ui-xx/style.txt`` inside map/campaign subfolders may not load, but ``ui-xx/tts.txt`` in those folders does. Soundpacks (mods without ``rules.txt``) also support ``mod.txt`` ``title`` and localized ``tts.txt`` in Options → Soundpacks.

Examples in this repo: ``mods/orc/``, ``mods/prismalab/ui-fr/``.

clear
>>>>>

To replace rules.txt or style.txt instead of patching it, use the "clear" command at the top of your file. This doesn't work with ai.txt,
and isn't needed anyway, because in ai.txt the def command rewrites the AI definition.

is_a
>>>>

While in style.txt "is_a" is a way to inherit all the properties of another definition,
in rules.txt, "is_a" is also used to make sure that a keep or a castle will allow what a town hall would allow.

Note: the inheritance trees in style.txt and in rules.txt don't need to match.

the rules
----------

Since SoundRTS 1.1, the rules of the game are stored in a file called rules.txt.

faction
>>>>>>>

Each faction is defined in rules.txt . For example::

	def orc_faction
	class faction

Note: the "orc_faction" name ends with "_faction" just to avoid name clashes. This "_faction" suffix is not mandatory as long as the name is unique.

unit
>>>>

Note: a unit can also be a building.

count_limit
============

New in SoundRTS 1.2 alpha 10.

`count_limit <value>`

The default value is 0 (no limit).
When the limit is active, a unit type which reaches the limit cannot be trained,
built, summoned, raised, resurrected, or added by a trigger (add_unit).
Conversion is unaffected though.

mdg_projectile / rdg_projectile
=================================

New in SoundRTS 1.3.8.2. Low-ground vs high-ground restriction added in 1.3.9.1.
Replaces the deprecated ``is_ballistic``.

``mdg_projectile 0|1``

``rdg_projectile 0|1``

The default value is 0. When set to 1, the corresponding attack type is treated as a
projectile:

- On high ground, the unit gains extra range when attacking targets at lower altitude
  (+1 square per height level)
- Non-projectile units cannot attack ground targets on high ground from below,
  regardless of range

Migration: mods that used ``is_ballistic 1`` should use ``rdg_projectile 1`` (ranged) or
``mdg_projectile 1`` (melee projectiles such as catapults); each attack type is configured
separately.

Ranged projectile example::

    def archer
    rdg 3
    rdg_range 4
    rdg_projectile 1

is_teleportable
================

New in SoundRTS 1.2 alpha 9.

``is_teleportable 1``

The unit (or building) is affected by the teleportation effect or the recall effect.

hp_regen
=========

New in SoundRTS 1.2 alpha 11

`hp_regen <hit points regeneration rate>`

For example, with "hp_regen 0.15", the unit regains 0.15 hit points per second.

mana_start
===========

New in SoundRTS 1.2 alpha 10.

``mana_start 50``

In the example, the unit will start with 50 mana instead of mana_max. The default value for mana_start is 0. If mana_start is 0 or negative, mana_max is used instead.

provides_survival
==================

New in SoundRTS 1.2 alpha 9.

``provides_survival 1``

Having at least one unit (or building) with "provides_survival" equal to 1 prevents a player from losing in a multiplayer game (not in a single player campaign). The affected trigger is "no_building_left". By default only the buildings have this property set to 1. Construction sites have this property set to 0 and it cannot be changed.

victory_time
=============

New in SoundRTS 1.4.5.8.

``victory_time <seconds>``

The default value is 0 (no victory timer). When greater than 0 on a **finished** building, a countdown starts as soon as that building exists. If the timer reaches zero while the building still stands, its owner (and allied victory camp) wins. Destroying the building cancels that countdown.

Applies to any ``class building`` type—not only the vanilla Wonder. Example (Age of Empires-style Wonder):

::

    def wonder
    class building
    cost 100 120
    time_cost 900
    hp_max 2500
    requirements imperial_age
    count_limit 1
    victory_time 300

Vanilla includes ``wonder`` with ``victory_time 300`` (5 minutes after completion). Voice messages: TTS 5720 (started), 5721 (cancelled), 5722 (remaining).

storage_bonus
==============

`storage_bonus <bonus for resource 0> <bonus for resource 1> ...`

For example, "storage_bonus 0 1" will cause a +1 bonus for wood (the second resource type).

The bonus goes to the owner of the unit.
The bonus doesn't stack: only the highest bonus will apply for each resource type.

damage_vs
==========

Note: since SoundRTS 1.4 the single ``damage`` / ``armor`` system was replaced by the
split melee/ranged system (``mdg`` / ``rdg`` / ``mdf`` / ``rdf`` ...). See `Combat system
(since 1.4)`_ below. The legacy ``damage_vs`` documentation is kept for older mods.

(damage versus specific units)

`damage_vs [<list of type names> <damage>] ...`

Defines a specific damage against some unit types.
The default value is defined in unit.damage.

Example of a type of pike man that would be more efficient against a knight
 and less efficient against a footman or a peasant:

`damage 2 ; default damage`

``damage_vs knight 7 footman peasant 1``

ability
>>>>>>>

Note: since SoundRTS 1.4, abilities are unified under ``class skill`` (see `Skills (class
skill)`_ below). The ``effect`` properties documented here still apply to skills and to
``class effect`` definitions.

effect
=======

`effect <effect type> [parameters]`

Default value: (none)

An effect is a property of an ability. When an ability is used by a unit, the effect will take place unless no effect type has been mentioned.

Additional properties can modify an effect: effect_target_ and effect_range_.

apply_bonus
^^^^^^^^^^^^

`effect apply_bonus <property name>`

Increases the property of the affected units. The value is defined in the property of the unit called "<property name>_bonus".
For example, "effect apply_bonus damage" will look for a property called "damage_bonus" in the definition of each affected unit.
This way, units benefiting from the same upgrade can have different bonus values.

bonus
^^^^^^

`effect bonus <property name> <value>`

Increases by the indicated value the property of the affected units.

At least the following properties should work: damage, armor, range, heal_level, speed, hp_max (old units won't have their hp updated to hp_max though).
food_cost and food_provided probably don't work correctly.

conversion
^^^^^^^^^^^

``effect conversion`` (no parameter)

Moves the target to the caster's army.

If the target isn't an enemy of the caster, nothing will happen.

Allowed values for the related properties:

* effect_target: ask
* effect_range: square, nearby, anywhere

TODO: add a <limit> so units in a targeted square are chosen (instead of having to target a unit)

raise_dead
^^^^^^^^^^^

`effect raise_dead <life span (in seconds)> <unit types and numbers>`

Creates the required units in the targeted square from the corpses in the square, in the order of the units list. If there are not enough corpses, the end of the list will not be created. The units will disappear after <life span> seconds, unless <life span> is set to 0.

If no corpse is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

recall
^^^^^^^

``effect recall`` (no parameter)

Similar to teleportation. Teleports the player's units from the targeted square back to the caster's square. Buildings are unaffected. Allied units are unaffected too.

If no unit is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: ask, random
* effect_range: nearby, anywhere

resurrection
^^^^^^^^^^^^^

`effect resurrection <limit>`

Resurrects the corpses of the caster's army lying in the targeted square, with a maximum of <limit> resurrected units. The oldest corpses are resurrected first. The hit points are restored to one third of their maximum.

If no corpse of a unit in the same army is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

summon
^^^^^^^

`effect summon <life span (in seconds)> <unit types and numbers>`

Creates the required units in the targeted square and adds them to the caster's army. The summoned units will disappear after <life span> seconds, unless <life span> is set to 0.

Optional skill attributes for placement checks (StarCraft creep tumor example)::

    summon_requires_build_field creep
    summon_requires_marked_field 1

``summon_requires_marked_field 1`` requires a marked build-field square (not live-only). Omit it when live field is enough (Queen spawn tumor).

deploy
^^^^^^^

``effect deploy \<life span (seconds)\> [\<count\>] \<effect type\>``

Places a ``class effect`` entity at the target square (area harm, heal zone, detector, etc.). It vanishes after the given duration. Unlike ``effect summon``, this is only for ``class effect`` definitions; the attributes UI shows harm/heal stats instead of "summon".

Examples::

    effect deploy 5 sc_nuclear_blast
    effect deploy 3 sc_psi_storm_fx

Optional count (multiple effect entities on the same square)::

    effect deploy 5 2 greek_fire

Also supports ``summon_requires_build_field`` / ``summon_requires_marked_field``.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

harm_target (since 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Single-target damage. Two forms:

* **Fixed true damage** (bypasses armor): ``effect harm_target <value>``
* **Combat pipeline** (armor, crit, splash, etc.): ``effect harm_target mdg`` or ``effect harm_target rdg``

Non-zero combat stats on the skill override the caster. See ``skill_lipi`` / ``skill_lipi_mdg`` in ``mods/wuxia/rules.txt``.

Use ``harm_target_type`` to filter targets (enemies only by default). See `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

harm_area (since 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Area damage:

* **Fixed true damage**: ``effect harm_area <damage> <radius>``
* **Combat pipeline**: ``effect harm_area mdg <radius>`` or ``effect harm_area rdg <radius>``

Radius may be omitted (uses the skill's ``effect_radius``). Examples: ``skill_heng_sao``, ``skill_heng_sao_mdg`` (wuxia mod).

burst (since 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^

Skill combo hits (**not** the same as unit ``damage_seq`` burst attacks; see `burst-attacks.htm <../player/burst-attacks.htm>`_)::

    effect burst mdg <count> (interval <sec>) (window <sec>)
    effect burst rdg <count> (delays <t1> <t2> …)

Damage uses the skill or caster ``mdg`` / ``rdg``. Example: ``skill_jifengci`` (wuxia mod).

push (since 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^

``effect push <distance>`` — knocks an enemy back and finds a walkable square. Example: ``skill_moli_dan`` (wuxia mod).

buffs / debuffs (via skills)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``effect buffs <buff> …`` / ``effect debuffs <debuff> …``

Applies buffs or debuffs to the target (``debuffs`` only on enemies). There is no ``effect reflect``; use ``reflect_percent`` on the buff and apply with ``effect buffs`` (wuxia ``b_douzhuan``).

Full reference: `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

teleportation
^^^^^^^^^^^^^^

``effect teleportation`` (no parameter)

Moves the player's units in the caster's square to the target square. Buildings are unaffected. Allied units are unaffected too.
   
If the destination is the same as the caster's square, nothing will be done.

Allowed values for the related properties:

* effect_target: ask, random
* effect_range: nearby, anywhere

effect_target
==============

`effect_target <selection method>`

Determines how the target will be selected.

Default value: self

Possible values:

* self: the target will be the caster (or the location of the caster if the target must be a place)
* ask: the user interface will ask for a target
* random: the game will choose a random square as a target

effect_range
=============

`effect_range <distance>`

Determines the distance between the caster and the target.

Default value: 6

Special value: inf (infinite)

If the current distance is greater than the required distance, the caster will try to move to a closer place and use the ability from there.

effect_radius
==============

`effect_radius <distance>`

Determines the radius of the area of effect. The center of the area is the target.

Default value: 6

Special value: inf (infinite)

Combat system (since 1.4)
--------------------------

Since 1.4, final damage is additive: ``final_mdg = mdg + mdg_vs`` (and the same for
``rdg``, ``mdf``, ``rdf``). When base damage is 0 and ``minimal_damage`` is 0 in
``def parameters``, the unit will not attack.

Main melee/ranged properties:

- ``mdg`` / ``rdg``: base damage
- ``mdg_vs`` / ``rdg_vs``: bonus vs specific unit types
- ``mdf`` / ``rdf``: defense
- ``mdg_range`` / ``rdg_range``, ``mdg_cd`` / ``rdg_cd``, ``mdg_ready`` / ``rdg_ready``
- ``mdg_projectile`` / ``rdg_projectile``: projectile flag (high-ground range bonus, low vs high ground rules)
- ``mdg_splash`` / ``rdg_splash``, ``mdg_radius`` / ``rdg_radius``, ``mdg_splash_decay``
- ``mdg_targets`` / ``rdg_targets``: ``ground``, ``air``, ``unit``, ``building``, or a type name
- ``mdg_crit`` / ``rdg_crit``, ``mdg_crit_rate`` / ``rdg_crit_rate``, ``crit_vs``
- ``mdg_piercing`` / ``rdg_piercing`` (percent armor ignored), ``piercing_vs``
- ``mdg_explode`` / ``rdg_explode``, ``exp_dgf``, ``exp_hp_cost``, ``mdg_explode_vs``
- Per-**attacker terrain** modifiers (since 1.4.5.0): ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``; same syntax as ``speed_on_terrain`` — see ``building-land-terrain.rst`` *Unit combat modifiers on terrain*

Auto menace / targeting priority (since 1.4.5.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Unit ``menace`` is no longer just damage. When rules do not set a fixed absolute
value, the engine builds a **multi-dimensional combat score** used for:

- Auto target choice (highest threat first; non-``timers`` computer players can
  also blend ``mdg_vs``/``rdg_vs`` via ``counter_skill`` — see ``aimaking.rst``)
- Square enemy-threat sums and related AI checks

**Dimensions** (primary weapon = higher of ``mdg`` / ``rdg``):

- Damage, hit chance (``mdg_cover``/``rdg_cover``, 0 means 100%%), cooldown
  (``*_cd``), wind-up (``mdg_ready``/``rdg_ready`` — not ballistic ``*_delay``)
- HP (current ``hp``, else ``hp_max``), armor (``max(mdf, rdf)``), dodge
  (``max(mdg_dodge, rdg_dodge)``)
- Attack range, move speed

Roughly: effective DPS (damage × hit / (cd + ready)), then survivability and
range/speed factors.

**Optional rules overrides** (unit defs):

======= ================= ============================================================
Field     Kind              Meaning
======= ================= ============================================================
``menace`` absolute         Fixed threat; does **not** track upgrades; replaces auto
``menace_mult`` weight (1)  Multiplies the auto multi-dim base (still scales with stats)
``menace_vs`` absolute vs   Fixed threat toward that observer type / ``is_a``
``menace_mult_vs`` weight vs Auto multi-dim base × weight toward that observer
======= ================= ============================================================

Lookup order (``menace_versus``): ``menace_vs`` → ``menace_mult_vs`` → global
``menace`` / ``menace_mult`` / auto score.

Example::

    def knight
    mdg 6
    menace_mult 1.5

    def archer
    rdg 5
    menace_vs knight 3
    menace_mult_vs mage 1.2

**Tunable weights** in ``def parameters`` (armor/dodge/range/speed importance and
HP normalization; damage+cd+ready+cover always feed the DPS core)::

    def parameters
    menace_armor_weight 1
    menace_dodge_weight 1
    menace_range_weight 0.15
    menace_speed_weight 0.2
    menace_hp_ref 50

Prefer ``menace_mult`` / ``menace_mult_vs`` for combat units that research upgrades;
use absolute ``menace`` / ``menace_vs`` only when you want a fixed priority.

Charge and counter-charge (since 1.4.0.1)

Charge: units with charge stats can perform a high-damage charge attack when engaging an
enemy within range. After charging they enter cooldown and deal normal ``mdg`` / ``rdg`` only
until cooldown ends. To charge the same target again, pull the unit beyond
``charge_mdg_dist`` / ``charge_rdg_dist`` after cooldown expires.

Charge damage (additive, not a multiplier)::

    charge_damage = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)

Example: ``mdg 6, charge_mdg 2`` → base ``6 + 2 = 8``, then scaled by distance within
``charge_mdg_dist`` (about 50% at point-blank, up to ~100% at max range). Ranged uses ``rdg`` /
``charge_rdg`` the same way.

Charge properties (melee / ranged pairs; swap ``mdg`` ↔ ``rdg`` for ranged):

- ``charge_mdg`` / ``charge_rdg`` — extra charge damage (added)
- ``charge_mdg_vs`` / ``charge_rdg_vs`` — bonus vs specific unit types
- ``charge_mdg_cd`` / ``charge_rdg_cd`` — cooldown (ms)
- ``charge_mdg_dist`` / ``charge_rdg_dist`` — max charge range
- ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` — min range to trigger (0 = no limit)
- ``charge_mdg_splash`` / ``charge_rdg_splash`` — splash damage
- ``charge_mdg_radius`` / ``charge_rdg_radius`` — splash radius
- ``charge_mdg_splash_decay_min`` / ``charge_rdg_splash_decay_min`` — min splash falloff (0.0–1.0)

Example (campaign knight)::

    def knight
    mdg 3
    charge_mdg 2
    charge_mdg_cd 10
    charge_mdg_dist 15
    charge_mdg_min_dist 3
    charge_mdg_splash 1
    charge_mdg_radius 1
    charge_mdg_splash_decay_min 0.5

Counter-charge: counters an incoming charge. When a counter-charge unit blocks a charging
attacker within range, the attacker's charge is interrupted (that hit resolves as a normal
attack) and the attacker takes counter-charge damage.

Counter-charge damage (additive)::

    counter = attacker (mdg/rdg + mdg_vs/rdg_vs) + attacker (charge_mdg/charge_rdg + charge_mdg_vs/charge_rdg_vs)
            + self (op_charge_mdg/op_charge_rdg + op_charge_mdg_vs/op_charge_rdg_vs)

Counter-charge properties:

- ``op_charge_mdg`` / ``op_charge_rdg`` — extra counter damage (added)
- ``op_charge_mdg_vs`` / ``op_charge_rdg_vs`` — bonus vs attacker types
- ``op_charge_mdg_cd`` / ``op_charge_rdg_cd`` — cooldown
- ``op_charge_mdg_dist`` / ``op_charge_rdg_dist`` — effective range (0 = unlimited)

``Sounds (``style.txt``)`: ``charge_success``, ``charge_failed``, ``op_charge``. Also
``critical_hit``, ``piercing_triggered`` for combat feedback.

Notes: self-attacks do not trigger charge; ground charge splash does not hit air units.

Burst / sequence attacks (``damage_seq``, since 1.3.8.2, enhanced in 1.4.3.6)
-------------------------------------------------------------------------------------

One attack cycle can fire multiple hits in quick succession (Age of Empires Chu Ko Nu
style). Define base ``mdg`` / ``rdg`` first, then ``damage_seq``:

``damage_seq mdg|rdg \<times\> [(damage d1 d2 ...)] [(interval seconds)]``

- Explicit split: ``(damage 6 3 3)`` — integer segment values must sum to the base
  damage (same units as ``mdg`` / ``rdg`` in rules.txt)
- Auto split (since 1.4.3.6): omit ``(damage ...)`` to divide base damage evenly across
  ``times`` (works with fractional damage, e.g. ``rdg 7.5`` with ``times 3`` → 2.5 per shot)
- Interval: ``(interval 0.25)`` seconds between shots; if omitted or 0 with ``times \> 1``,
  default 0.25 s
- Limit: at most 6 shots per attack
- Hit rolls: each segment rolls hit, crit, and debuff separately
- Cooldown: ``mdg_cd`` / ``rdg_cd`` starts after the full burst finishes
- Sounds: each shot triggers ``launch_mdg`` / ``launch_rdg``; list multiple sound IDs
  in ``style.txt`` (e.g. ``launch_rdg 1042 1042 1042``)

Ranged burst example (built-in ``repeating_crossbowman``)::

    def repeating_crossbowman
    rdg 6
    rdg_cd 2.5
    rdg_range 4
    rdg_projectile 1
    damage_seq rdg 3 (interval 0.25)

Melee example with explicit damage split::

    def footman
    mdg 12
    mdg_cd 1.5
    mdg_range 6
    damage_seq mdg 3 (damage 6 3 3) (interval 0.2)

See also ``../player/burst-attacks.htm``.

Weapons and armor (since 1.4.1.3)
----------------------------------

Weapons (``class weapon``) and armor (``class armor``) hold combat stats. Units reference
them::

    def footman
    class soldier
    weapons sword bow     ; first weapon is default / main weapon
    auto_weapon_switch 1  ; 1 = auto-switch by range in combat
    armor light_armor

Players switch weapons with A / Shift+A or B then X. Manual switch overrides auto switch.
Stats on the unit and on equipped gear add together. Weapons support inheritance like
units.

Buffs and debuffs (since 1.3.9.8, extended in 1.4.1.7)
-------------------------------------------------------

Attach to attacks with ``buffs`` / ``debuffs``, or via skills with ``effect buffs`` /
``effect debuffs``.

``reflect_percent`` (integer percent) on a buff enables damage reflection; apply with
``effect buffs``. There is no ``effect reflect``. Example: ``b_douzhuan`` in ``mods/wuxia/rules.txt``.

Multi-stat buff example::

    def HealEnhancementBuff
    class buff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1

Trigger modes:

1. Default — on hit
2. :strong:```is_active 1`` — when starting an attack (active)
3. :strong:```is_passive 1`` — when taking damage (passive), with ``trigger_condition`` (e.g.
   ``hp \< 20``) and ``passive_trigger_rate``

Trigger rates (percent; default falls back to normal attack rates):

- ``mdg_trigger_rate`` / ``rdg_trigger_rate`` — normal damage
- ``charge_mdg_trigger_rate`` / ``charge_rdg_trigger_rate`` — charge damage
- ``op_charge_mdg_trigger_rate`` / ``op_charge_rdg_trigger_rate`` — counter-charge

Skills (class skill)
---------------------

Define skills with ``class skill`` instead of ``class ability``::

    def fireball
    class skill
    mana_cost 50
    cost 10 0
    time_cost 30
    effect harm_target 60
    effect_target ask
    effect_range 12
    cooldown 10

``can_use_tech`` applies to upgrades; ``can_use_skill`` applies to skills.

Since 1.4.4.6: ``harm_target``, ``harm_area``, ``burst``, ``push``, ``effect buffs`` / ``debuffs``, etc. Demo mod: ``mods/wuxia/rules.txt``. See `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

**Skill triggers (since 1.4.4.6)**

Learned skills go in ``can_use_skill``. Manual and auto can coexist (``manual_use 1`` + ``auto_trigger 1``).

+--------------------+------------------------------------------------+
| ``manual_use 1``   | Show in command menu (default 1)               |
+--------------------+------------------------------------------------+
| ``auto_trigger 1`` | Fire automatically in combat                   |
+--------------------+------------------------------------------------+
| ``trigger_timing`` | When to auto-fire (see table)                  |
+--------------------+------------------------------------------------+

+-------------------------+----------------------------------------------+---------------------------+
| ``trigger_timing``      | When                                         | Legacy list               |
+=========================+==============================================+===========================+
| ``on_hit`` (default)    | After hitting an enemy                       | ``active_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack``           | At attack start; normal attack continues     | ``attack_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack_replace``   | At attack start; replaces this attack        | ``attack_replace_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_damaged``          | When hit by an enemy (passive)               | ``passive_trigger_skills``|
+-------------------------+----------------------------------------------+---------------------------+

Rates: ``active_trigger_rate`` / ``passive_trigger_rate`` (1–100); optional ``mdg_trigger_rate`` / ``rdg_trigger_rate`` override the active rate for melee/ranged.

Conditions: ``trigger_condition hp < 30`` (``hp``/``mana`` compared as percent) or ``hp_threshold 30``. Checked only for ``on_hit`` and ``on_damaged``, not for ``on_attack`` / ``on_attack_replace``.

Auto triggers consume mana and respect cooldown; ``ready`` wind-up applies like manual casts.

Example (passive on hit taken)::

    def skill_thorns
    class skill
    auto_trigger 1
    manual_use 0
    trigger_timing on_damaged
    passive_trigger_rate 30
    effect harm_target 10
    effect_target ask

Full reference: `Skills guide <../../zh/mod/skills-and-effects.htm>`_ (section on trigger modes).

Effects (class effect, since 1.4.1.7)
--------------------------------------

Harm and heal are split into detailed parameters::

    def exorcism
    class effect
    harm_level 2
    harm_cd 7.5
    harm_radius 6
    harm_target_type undead
    debuffs b_slow

Similarly: ``heal_level``, ``heal_cd``, ``heal_radius``, ``heal_target_type``;
``hp_regen_cd``, ``mana_regen_ready``, etc.

Phase system (since 1.4.2.4)
-----------------------------

``class phase`` advances game eras without upgrading the base::

    def dark_age
    class phase
    cost 0 0
    time_cost 0

    def feudal_age
    class phase
    cost 10 15
    time_cost 130
    phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
    units_auto_upgrade 0
    phase_targets soldier

Optional ``phase_targets`` limits which units receive non-cost entries from ``phase bonus`` (cost-type bonuses always apply at player level). Leave empty for all units. Use category names (``soldier``, ``worker``, ``building``, ``unit``, etc.), specific unit names (``footman knight``), or any name in the ``is_a`` chain; any positive match counts. A leading ``-`` excludes a match — e.g. ``phase_targets -building`` means every unit except buildings; you can mix includes and excludes, e.g. ``phase_targets soldier -footman``.

On a building::

    can_advance feudal_age

Use ``can_advance`` (not ``can_research``) for phases. Press V on the building to view the
current phase.

``hide_locked_commands 1`` in ``def parameters`` hides commands whose requirements are not
yet met.

Besides plain type names (all must be owned — AND), ``requirements`` can ask for any N
buildings of a named group (since 1.4.5.8)::

    ; buildings with requirements castle_age join castle_age_buildings
    def stables
    class building
    requirements castle_age

    ; age advance and HQ upgrades can share the same group
    def imperial_age
    class phase
    requirements castle_age any_buildings 2 castle_age_buildings

    def castle
    class building
    requirements any_buildings 2 castle_age_buildings

``any_buildings <n> <group>_buildings`` strips ``_buildings`` to get the key, then
collects every building whose simple ``requirements`` list that key. Example:
``castle_age_buildings`` collects buildings with ``requirements castle_age``.
For an HQ stage, members use ``requirements keep`` and the gate uses
``any_buildings 2 keep_buildings``.

Use names like ``castle_age_buildings``, not bare phase names.
The group token does not trigger ``units_auto_upgrade``.

The attributes screen shows “belongs to age” from phase names in the building’s
simple ``requirements`` (e.g. barracks with ``requirements feudal_age`` → Feudal Age).
Buildings without a phase requirement omit this row.

Economy (since 1.4.0.x)
------------------------

``population_cost`` replaced ``food_cost``. Buildings can produce or hold resources::

    auto_production 1       ; auto produce (gas, etc.); restarts while not full
    manual_production 1     ; player-started production
    auto_cultivate 1        ; farms; restarts only when storage is empty
    is_gather 1             ; output goes to building storage; workers haul to base
    resource_volume_max 8
    resource_volume_start 0
    production_type resource2
    production_time 18      ; seconds to fill one batch
    production_qty 8        ; amount per production cycle (into building storage)
    extraction_time 2       ; worker harvest time from building (seconds)
    extraction_qty 8        ; worker carry size per trip

Without ``is_gather``, both auto and manual production credit ``production_type`` output straight into the player's stockpile (e.g. ``gold_house``)::

    auto_production 1
    manual_production 1
    production_type resource1
    production_time 100
    production_qty 200

For pickable loot instead, use ``production_item`` (instead of ``production_type``)::

    production_item gold_pile
    production_qty 1

| Attribute | Role |
| --- | --- |
| ``production_type`` | Resource produced (with ``production_time`` and ``production_qty`` defines production capability) |
| ``production_time`` | Seconds per production cycle |
| ``production_qty`` | Output per cycle; without ``is_gather``, added to player resources; with ``is_gather``, to building ``resource_qty`` |
| ``auto_production`` | When ``1``, shows auto produce; loops after each cycle; use for gas (not ``auto_cultivate``) |
| ``manual_production`` | When ``1``, shows manual produce; one cycle per click; independent from ``auto_production`` |
| ``auto_cultivate`` | Auto cultivation on ``is_gather`` buildings (e.g. farms); parallels ``auto_production`` |
| ``manual_cultivate`` | Manual cultivation; parallels ``manual_production``; set ``1`` explicitly when needed |
| ``production_item`` | Item type name; spawns pickable items beside the building on completion |
| ``is_gather`` | Output stays in the building until a worker with ``can_gather_building`` hauls it to a warehouse |
| ``resource_volume_max`` | Max stored in building (e.g. 8 vespene) |
| ``resource_volume_start`` | Initial stored amount when built (``0`` = empty) |
| ``extraction_time`` / ``extraction_qty`` | Worker harvest time and per-trip amount from building or deposit |

.. note::

   ``auto_production`` and ``manual_production`` are separate flags and may both be ``1`` (e.g. ``gold_house``). ``auto_production`` absent or ``0`` does not imply manual mode; set ``manual_production 1`` for the manual command. Same for ``auto_cultivate`` / ``manual_cultivate`` on farms.

.. note::

   ``is_create`` is deprecated: ground ``class resource`` piles are no longer spawned. Use ``production_type`` (direct stockpile), ``is_gather`` (building storage), or ``production_item`` (spawn items).

``class resource`` is separate from ``class deposit``. Map deposits::

    mineral_field 1500 a1
    geyser 1 e1

Gas structures must sit on the matching deposit::

    requires_deposit geyser
    is_buildable_anywhere 0

See ``sc_gas_building`` / ``assimilator`` in ``mods/starcraft/rules.txt``. Player guide:
``../player/starcraft-resources.htm``. The attributes screen (V) adds requires deposit;
production time/qty use the existing production attribute entries.

Heroes (since 1.4)
-------------------

Define hero units in any ``rules.txt`` (base rules, mods, campaign packs, multiplayer map packs). They work in skirmish, random maps, multiplayer, and campaigns: kill XP, ``xp_thresholds`` leveling, ``is_revivable`` revival, inventory, etc. Cross-chapter save (``campaign_carryover`` in the next section) is an extra feature for single-player campaigns only.

Multiplayer example: ``hero`` / ``hero_knight`` in ``res/multi/td2/rules.txt``.

::

    def hero
    class soldier
    global_count_limit 1
    is_revivable 1
    revival_time 10
    xp_thresholds 200 500 900
    hp_max_per_level 1000
    mdg_per_level 100
    resource_rewards 300
    xp_reward 100

``Level and XP (``level`` / ``xp`` / ``xp_thresholds`` / ``xp_threshold_growth``)``

| Field | Default | Meaning |
| --- | --- | --- |
| ``xp_thresholds`` | (empty) | Cumulative XP gates. The first value is the total XP for level 2 (or level 1 when starting at level 0); each following value is the next level. |
| ``max_level`` | (none) | Hero level cap. With ``xp_threshold_growth``, rules load generates ``max_level - 1`` thresholds automatically |
| ``xp_threshold_growth`` | (none) | Auto-generate ``xp_thresholds`` from a formula (table below). Requires ``max_level``; use either this or an explicit ``xp_thresholds`` list (explicit list wins) |
| ``level`` | ``1`` | Starting level. When ``\> 1`` with ``xp_thresholds``, cumulative ``*_per_level`` bonuses and ``level_skills`` are applied on spawn. |
| ``xp`` | ``0`` | Optional starting cumulative XP. |
| ``level_up_heal_full`` | ``0`` | ``1`` = restore full HP and mana on each level up; ``0`` = add only the ``hp_max_per_level`` / ``mana_max_per_level`` increment to current values (default). |
| ``level_up_reset_xp`` | ``0`` | ``1`` = reset current XP to 0 after each level up; ``0`` = keep cumulative XP (default). When ``1``, prefer per-level ``xp_thresholds`` (XP since last level-up), not cumulative totals. |

- Max level = ``len(xp_thresholds) + 1`` (e.g. nine thresholds → level 10 cap).
- Unit status (Tab): heroes with ``xp_thresholds`` always announce level (including 0 and 1). XP is shown as ``current / next gate`` (at level 0 the next gate is ``xp_thresholds[0]``).
- ``xp_thresholds`` (or ``xp_threshold_growth`` after expansion) alone → default level 1 at game start; ``level 0`` starts below level 1.

:strong:```xp_threshold_growth`` curve types`` (threshold index ``i`` starts at 0 for level 2, 3, …)

| Type | Syntax | Formula |
| --- | --- | --- |
| linear | ``linear BASE STEP`` | ``BASE + STEP × i`` |
| quadratic | ``quadratic BASE A B`` | ``BASE + A×i + B×i²`` |
| polynomial | ``polynomial c0 c1 c2 …`` | ``c0 + c1×i + c2×i² + …`` |
| geometric | ``geometric FIRST RATIO`` | ``FIRST × RATIO^i`` (``RATIO`` may be fractional, e.g. ``1.08``) |

Example (100-level hero, linear cumulative XP)::

    def long_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50
    hp_max_per_level 30
    mdg_per_level 2

Example (Raynor-style quadratic curve, same as ``40 90 160 250 …``)::

    def raynor_curve
    class soldier
    max_level 10
    xp_threshold_growth quadratic 40 40 10
    hp_max_per_level 30

Example (child def overrides only the level cap; inherits parent ``xp_threshold_growth``)::

    def base_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50

    def short_campaign_hero
    is_a base_hero
    max_level 20

Example (level 0 start, explicit threshold list)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160 250 360 490 640 810 1000
    hp_max_per_level 30
    mdg_per_level 2
    level 0

Example (full heal on level up)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160
    hp_max_per_level 30
    level_up_heal_full 1

Example (level 3 start with initial XP)::

    def veteran_hero
    is_a knight
    xp_thresholds 200 500 900
    hp_max_per_level 20
    level 3
    xp 500

Campaign hero carryover (rules-driven)
---------------------------------------

Add ``campaign_carryover 1`` on a hero def from the previous section. Only single-player campaigns: on victory, progress is saved to ``user/campaigns.ini`` and restored on the next chapter (defeat retry does not overwrite). Co-op does not persist heroes.

::

    def my_hero
    is_a knight
    campaign_carryover 1
    campaign_carryover_stats 1
    campaign_carryover_inventory 1
    inventory_capacity 8

| Field | Default | Meaning |
| --- | --- | --- |
| ``campaign_carryover`` | ``0`` | ``1`` = enable cross-chapter save |
| ``campaign_carryover_id`` | def name | Keys ``hero_\<id\>\_xp``, ``\_level``, ``\_inventory`` |
| ``campaign_carryover_stats`` | ``1`` | Level + XP |
| ``campaign_carryover_inventory`` | ``1`` | Backpack items |

Stats only: ``campaign_carryover_inventory 0``. Inventory only: ``campaign_carryover_stats 0``. No carryover: omit ``campaign_carryover 1``.

Optional in ``campaign.txt``: ``hero_min_level 13:2 16:3 …`` for chapter floor levels.

Separate from ``campaign_flag`` / ``add_inventory_item`` (story tokens, alliances). See ``mod/campaign-hero-carryover.htm``.

Transport containers (field rename since 1.4.4.9; legacy names still accepted)
-------------------------------------------------------------------------------

Units or buildings with ``transport_capacity`` act as transport containers. Related properties:

| Property | Effect | Example |
| --- | --- | --- |
| ``passenger_attack_types`` | Unit types that may attack outside while inside | ``passenger_attack_types archer knight`` or ``all`` |
| ``load_bonus`` | Per loaded unit → stats added to the **container** | ``load_bonus speed 0.5 mdg 2`` |
| ``passenger_bonus`` | Stats added to the **passenger** while inside (rolled back on unload) | ``passenger_bonus rdg_range 1 mdg 2`` |

Example::

    def flyingmachine
    class soldier
    transport_capacity 8
    passenger_attack_types knight archer
    load_bonus speed 0.5
    passenger_bonus rdg_range 1

    def wall
    class building
    transport_capacity 4
    passenger_attack_types archer catapult
    passenger_bonus mdg 2

- Without ``passenger_attack_types``, passengers cannot attack outside targets by default.
- ``load_bonus`` and ``passenger_bonus`` can be combined on the same container.

Square occupancy (``space``, since 1.4.5.8)
---------------------------------------------

``space`` is a precision property (decimals allowed). It is how much of a map square
the unit occupies on its air/ground/water layer. Capacity equals map ``square_width``
in the same units.

| Setting | Effect |
| --- | --- |
| ``space 0`` (default) | Does not consume capacity (legacy unlimited) |
| ``space 1`` on ``square_width 12`` | At most 12 such units on that layer |
| ``space 0.5`` on ``square_width 12`` | At most 24 |
| ``space`` > ``square_width`` | Unit cannot enter that square |

Capacity is shared by all sides. When the square is full, movement into it and training
that would spawn there are refused (voice ``not_enough_space``). Layers are separate:
ground occupancy does not block air units.

Example::

    def peasant
    class worker
    space 1

    def siege_engine
    class soldier
    space 4

See also map ``square_width`` in ``mod/mapmaking.rst``.

Items (since 1.4.1.3)
----------------------

::

    def magic_sword
    class item
    consume_on_pickup 0
    buffs power_buff
    resource_rewards resource1 50

``is_loot 1`` drops the item when the carrier dies.

``Item sounds (``style.txt``; use sounds since 1.4.4.6)``

| When | Item ``style.txt`` | Unit ``style.txt`` | Global default (``def thing``) |
| Pickup | ``on_pickup`` | ``pickup_\<item type\>`` | ``pickup`` |
| Drop | ``on_drop`` | ``drop_\<item type\>`` | ``drop`` |
| Use | ``use`` / ``on_use`` | ``use_\<item type\>`` | ``item_used`` |

On the item (``use`` and ``on_use`` are equivalent; multiple IDs are chosen at random)::

    def zhuiri_jianfa_book
    title 7754
    pickup 1506
    use 1506

On the unit::

    def raynor
    use_zhuiri_jianfa_book 1506

Global fallback::

    def thing
    item_used 1194 1195 1196

Inheritance (``is_a``) works like ``on_pickup`` / ``on_drop``: derived types override parents.

Inventory and equippable items (since 1.4.3.1)
------------------------------------------------

Units need ``inventory_capacity`` > 0 to hold items. Each item uses one slot (``transport_volume``
is defined but capacity currently counts items, not volume).

Built-in gear (traditional)::

    def footman
    weapons sword          ; class weapon — built-in, not in backpack
    armor footman_armor    ; class armor — built-in

Equippable items (unified model): the same type name can be ``class item``::

    def sword
    class item
    equippable_as_weapon 1
    mdg 3.5
    mdg_range 1
    transport_volume 1

    def footman_armor
    class item
    equippable_as_armor 1
    mdf 0.5

When ``weapons`` / ``armor`` on a unit point to equippable items, the engine creates item
instances at spawn and puts them in inventory. If the unit has no built-in gear of that
kind and ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` is ``1`` (default), they are
silently equipped::

    def footman
    inventory_capacity 2
    weapons sword
    armor footman_armor

Gear switching rules when a unit has both built-in and item gear (e.g.
``weapons bow sword`` with ``bow`` as ``class weapon`` and ``sword`` as equippable item):

- Built-in gear is always equipped at spawn; item gear goes to the backpack.
- With ``spawn_weapons_equipped 1`` (default), item weapons stay in the backpack and cannot
  be equipped; with ``spawn_weapons_equipped 0``, the player may equip them manually.
- Built-in gear can only switch with built-in gear; item gear only with item gear;
  no cross-switching between the two kinds. Same rules apply to armor
  (``spawn_armor_equipped``).

Mixed archer example::

    def archer
    weapons bow sword
    spawn_weapons_equipped 1   ; bow equipped, sword in backpack, sword not equippable
    inventory_capacity 3

    def archer
    weapons bow sword
    spawn_weapons_equipped 0   ; bow equipped, sword in backpack, player may equip sword
    inventory_capacity 3

Consumables (``buffs`` only, no ``equippable_as_*``) are used from the backpack with Enter,
not from the equipment screen. On success, ``use`` / ``on_use`` sounds play; normal consumables
announce the item title plus "used".

Skill books (permanently learn a skill; consumed on successful use)::

    def zhuiri_jianfa_book
    class item
    skills skill_zhuiri_jianfa
    learn_level 10
    transport_volume 1

- ``learn_level`` / ``learn_level_skills``: minimum level to learn from the book (strictest of
  unit ``learn_level_skills`` and item rules).
- Unit ``level_skills``: auto-unlock on level up (separate from books; do not duplicate the same
  skill or use returns ``skill_already_known`` and keeps the book).
- With ``learn_level`` / ``learn_level_skills`` on the item, pickup does not grant the skill;
  the player must use the book from the backpack.
- Success: use sound + TTS skill title + ``skill_learned`` message; failure: ``order_impossible``
  with ``skill_level_too_low`` / ``skill_already_known`` etc.

``Treasure with ``use_square`` (rewards only when used in backpack at a named square)::

    def mystery_treasure
    class item
    use_square b2
    resource_rewards resource1 150

Server orders (also usable in trigger ``order`` actions): ``equip_weapon``, ``unequip_weapon``,
``equip_armor``, ``unequip_armor``, ``use_item``, ``drop``.

Unit default behavior (since 1.4.3.1)
--------------------------------------

Per-unit starting behavior in ``rules.txt``:

- ``ai_mode``: ``offensive``, ``defensive``, ``guard``, or ``chase``. Default: ``offensive``
  for soldiers, ``defensive`` for workers. Applies to combat units.
  ``chase`` keeps one ``AttackAction`` and follows across squares (no auto ``go``);
  ``offensive`` / ``guard`` still respect spawn ``position_to_hold`` until an order ``stop()``\ s;
  ``defensive`` / ``chase`` do not.
- ``auto_gather``: ``1`` or ``0``. Default ``1``. Workers only.
- ``auto_repair``: ``1`` or ``0``. Default ``1``. Workers only.
- ``auto_explore``: ``1`` or ``0``. Default ``0``. Mobile units (speed > 0).
- ``can_auto_explore``: ``1`` or ``0``. Default ``0``. Adds enable/disable auto-explore to
  the unit's command menu.
- ``no_number`` (since 1.4.3.2): ``1`` or ``0``. Default ``0`` (always speak serial numbers,
  e.g. "peasant 1 at a1"). When ``1``: omit the number while only one living unit of that
  type exists ("Guan Yu at a1"); with two or more, use numbers ("Guan Yu 1", "Guan Yu 2").
  Group summaries follow the same rule. For unique heroes or leaders.

``ai_mode patrol`` is invalid — patrol requires a route command. Neutral computer units are
still forced to guard + counterattack regardless of ``ai_mode``.

Player units in ``offensive``, ``defensive``, or ``chase`` mode do not auto-attack neutral
units (``computer_only ... neutral``) and defensive mode does not flee from neutrals alone.
Plain ``go`` on a neutral only moves; plain ``attack`` on ``is_huntable`` deals damage.
Use an imperative attack (e.g. Ctrl+click on the unit) to make the AI treat a neutral creep/NPC as an auto-engage target.

Example::

    def knight
    class soldier
    ai_mode guard
    auto_explore 1
    can_auto_explore 1

    def peasant
    class worker
    auto_gather 1
    auto_repair 0
    ai_mode defensive

Capture / default occupy order
-------------------------------

Target — ``capture_hp_threshold`` (on capturable buildings/units):

| Value | Meaning |
| --- | --- |
| ``0`` (default) | Not capturable via HP threshold |
| ``100`` | Contact capture: convert owner on arrival, no damage; default right-click order is capture (see ``can_capture``) |
| ``30`` etc. | Capturable when HP ≤ that percentage during normal combat |

Attacker — ``can_capture`` (on soldiers/workers with attack):

| Value | Meaning |
| --- | --- |
| ``1`` (default) | Right-click enemy with ``capture_hp_threshold 100`` → default capture; AI uses contact capture |
| ``0`` | Same target → default attack/move; AI attacks normally |

Requires ``attack`` in the unit's skills; target must be a living, vulnerable enemy.

Example — only footmen capture barracks; archers attack::

    def captured_barracks
    class building
    capture_hp_threshold 100
    ...

    def footman
    class soldier
    can_capture 1
    ...

    def archer
    class soldier
    can_capture 0
    ...

Random-map POI ``captured_barracks`` and HoMM-style play: ``player/英雄无敌与文明5玩法说明.htm``.

Ship repair (since 1.4.1.1)
------------------------------------

give order — transfer an inventory item to another unit::

    give <target unit id>
    give <target unit id> <item type or id>

Target fields (all must pass):

- ``receive_items 1`` (default 0 — NPCs must opt in)
- ``accepted_items`` — optional whitelist of item types (``is_a`` inheritance supported); empty = any
- ``accept_from`` — optional list: ``self``, ``ally``, ``neutral``, ``enemy``; empty = any

Example NPC that accepts any item from anyone::

    def quest_npc
    receive_items 1
    inventory_capacity 5

Example: allied knights accept only ``knight_lance`` from allies::

    def knight
    receive_items 1
    accepted_items knight_lance
    accept_from ally

Delivery records ``received_items`` on the target for trigger checks. Items apply ``skills`` /
``buffs`` on receipt like ``pickup``. Script delivery ignores target ``inventory_capacity``.
Multiplayer demo: ``res/multi/give_demo.txt``. Campaign relation demos: ``The Legend of Raynor`` ch. 14–16
(``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``).

Build fields, addons & lift-off (StarCraft-style, ``mods/starcraft``)
-----------------------------------------------------------------------------

The engine supports build fields, worker build modes, Terran addons, and
lift-off recombine. Reference implementation: ``mods/starcraft/rules.txt``. Player guides:

- Terran addons: ``../player/starcraft-terran.htm``
- Zerg creep & Queen tumors: ``../player/starcraft-zerg-creep.htm``

Build fields (Protoss psi / Zerg creep)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Attribute | Role |
| --- | --- |
| ``provides_build_field \<name\>`` | Marks nearby squares (e.g. ``psi``, ``creep``) |
| ``requires_build_field \<name\>`` | Requires that field to place/build; ``0`` exempts the type (Nexus, Photon Cannon) |
| ``build_field_radius \<tiles\>`` | Provider radius (main-square BFS steps; use this or ``build_field_radius_m``) |
| ``build_field_radius_m \<meters\>`` | Provider radius in meters (same scale as ``rdg_range``); Euclidean distance from provider `` (x,y)`` |
| ``build_field_persists 1`` | Marks remain after provider is destroyed (Zerg creep) |
| ``build_field_spreads 1`` | Spread marks to adjacent squares each second |
| ``build_field_spread_squares N`` | Layers per tick (default 1 when ``build_field_spreads``) |
| ``requires_build_field_on_square 1`` | Entire square must be marked (Zerg); else live field anywhere on square suffices (Protoss) |
| ``loses_power_without_field 1`` | Power down without live field: halt build/train/power (Protoss) |

:strong:```build_field_radius`` vs ``build_field_radius_m``

Use one radius property per provider; leave the other at 0 (default).

| Property | How range is measured | Typical use |
| --- | --- | --- |
| ``build_field_radius`` | BFS steps from the provider's main square (discrete tiles) | Legacy tile-based creep |
| ``build_field_radius_m`` | Euclidean distance from the provider's (x, y) in meters | Protoss psi chains (SC2-like); Zerg Hatchery / creep tumor in ``mods/starcraft`` |

One map square is about 12 m wide (``square_width 12``). Examples in the StarCraft mod:
Nexus 18 m, Pylon 12 m, Hatchery 12 m, creep tumor 4 m.

Live vs marked field

- Live field — currently provided by standing buildings/units (meter: point-in-circle; tiles: BFS from ``place``).
- Marked field — persistent square marks painted on registration and/or spread each second.

``has_build_field_on_square`` accepts live OR marked. Zerg ``requires_build_field_on_square 1`` checks marked squares only (you cannot build on live creep that has not spread/marked yet).

When ``build_field_persists 1`` or ``build_field_spreads 1`` is set, meter-radius providers also paint marks in range (needed so Hatchery-only ``build_field_radius_m`` still allows Zerg building).

Queen creep tumor (``mods/starcraft``): summon skills place ``creep_tumor`` buildings on targeted squares. Skill attributes:

| Attribute | Role |
| --- | --- |
| ``summon_requires_build_field \<name\>`` | Target square must have that field (live or marked) |
| ``summon_requires_marked_field 1`` | Target must be marked (tumor Extend; Queen Spawn omits this) |

Player guide: ``../player/starcraft-zerg-creep.htm``. Mod readme: ``mods/starcraft/readme.txt``.

Protoss (``protoss_building``)::

    requires_build_field psi
    is_buildable_anywhere 1
    self_constructs 1
    loses_power_without_field 1

Zerg (``zerg_building``)::

    requires_build_field creep
    requires_build_field_on_square 1
    is_buildable_anywhere 1
    self_constructs 1

Hatchery: ``provides_build_field creep`` + ``build_field_radius_m 12`` + ``build_field_persists 1`` +
``build_field_spreads 1``. Queen Spawn creep tumor / tumor Extend — see ``../player/starcraft-zerg-creep.htm``.

UI: ``def build_field_\<name\>`` + ``title \<tts_id\>`` in ``ui/style.txt``; optional ambient ``noise``.

Deposits & gas (``requires_deposit``)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Attribute | Role |
| --- | --- |
| ``requires_deposit \<type\>`` | Must build on a map deposit (e.g. ``geyser``); deposit is removed on completion |
| ``is_buildable_anywhere 0`` | With ``requires_deposit``, blocks building on building land |

Gas template ``sc_gas_building`` uses ``auto_production`` + ``is_gather`` + ``production_time`` / ``production_qty``.
Workers need ``can_gather assimilator`` (building type), not ``geyser`` (deposit).

Worker build modes
>>>>>>>>>>>>>>>>>>

| ``build_mode`` | Behavior |
| --- | --- |
| ``assisted`` | Worker stays until done (Terran SCV, default) |
| ``place_and_leave`` | Worker places site and leaves; ``self_constructs 1`` finishes building (Probe) |
| ``sacrifice`` | Worker is consumed (Drone) |

Also: ``self_constructs 1``, ``build_sacrifices_worker 1``, ``is_buildable_anywhere 1`` (no separate ``class building_land`` slot on Protoss/Zerg/flying Terran).

Terran addons
>>>>>>>>>>>>>

| Attribute | Role |
| --- | --- |
| ``can_have_addon \<types\>`` | Host types (Barracks / Factory / Starport) |
| ``addon_max N`` | Max attached addons (default 1) |
| ``is_addon 1`` | Addon building (Tech Lab, Reactor) |
| ``addon_host_types \<hosts\>`` | Which hosts accept this addon |
| ``addon_grants_train_\<host\> \<unit\>`` | Extra train option when attached |
| ``addon_grants_research \<tech\>`` | Extra research when attached |
| ``addon_train_multiplier N`` | Reactor double production |
| ``addon_offset_x \<value\>`` | Side slot offset east of host (default 3.5 tiles) |

Build addon on an existing host, not bare ground.

Lift-off & recombine
>>>>>>>>>>>>>>>>>>>>

| Attribute | Role |
| --- | --- |
| ``can_change_to \<flying\>`` | Ground host can lift |
| ``ground_form \<ground\>`` | Flying form lands as this type |
| ``change_time \<sec\>`` | Morph time for ``change_to`` (no resource/pop cost) |

Lift: addons detach on ground; building land is restored under the host (**same type the building consumed when built**; StarCraft maps use ``build_site``). If the unit has no saved reference, the map’s ``building_land`` or a sole ``nb_<type>_by_square`` keyword is used.

Land: consumes nearest ``class building_land`` object on the square (API names like ``find_meadow_near_xy`` are historical).

Recombine: Tab Tech Lab → Backspace go (flies to landing slot west of lab) → ``change_to`` ground.

Building land vs slot: building land = land permission; reattach needs slot alignment
(``tech_lab.x ≈ factory.x + addon_offset_x``, within ~2.5 tiles Manhattan).

Landing on own lift-off patch does not reattach. Wrong land with orphan addon → TTS ``addon_reattach_failed`` (7350).

Test maps: ``terran_addon_test``, ``terran_recombine_test``; campaign ``sc_build_tests`` ch. 3–4.

Ship repair (since 1.4.1.1)
----------------------------

``can_repair_ships 1`` on workers or buildings. Workers repair adjacent shore ships (6
squares); buildings auto-repair ships in neighboring water (8 squares).

Building bridges on water (tile spans)
---------------------------------------

Workers can build ``is_buildable_on_water_only 1`` spans on pure water; on completion
``bridge_terrain`` (e.g. ``bridge_deck``) is applied. Scaffold sites use normal
``buildingsite`` TTS; footsteps use the finished terrain ``ground``. See
`water-bridge-building.htm <water-bridge-building.htm>`_ (`zh <../../zh/mod/water-bridge-building.htm>`_).

Herding (workers)
------------------

``can_herd 1`` lets a worker herd animals with ``herdable 1`` (for example sheep). The
default is ``0``; enable herding explicitly per worker type in ``rules.txt``.

:strong:```can_capture`` — ``1`` or ``0``. Default ``1``. On units with ``attack`` skills: when
``0``, right-click on enemies with ``capture_hp_threshold 100`` uses normal attack/move instead
of the default capture order; AI contact-capture is disabled too. See Capture / default occupy
order above.

Hunting system (Age of Empires style)

See ``../player/hunting.htm``. Summary:

- Workers Backspace/right-click ``is_huntable`` animals to attack (plain attack deals damage); kills spawn a ``food_deposit`` carcass (e.g. ``food_carcass``) and complete the attack order without a false ``order_impossible`` beep.
- Animal attrs: ``is_huntable``, ``flee_on_hit``, ``herdable``, ``food_deposit``, ``food_deposit_qty``, ``no_number``.
- Map spawn: ``computer_only 0 0 neutral \<square\> \<count\> deer``; random maps add wildlife near starts.
- Voice: units with ``is_huntable`` / ``herdable`` are announced as "deer , animal", not "neutral , NPC". Ctrl+Shift+F4 to a wildlife-only player says "you are animal". Story NPCs (``quest_npc``, etc.) still say "neutral , NPC".
- Diplomacy: a ``computer_only`` slot with only wildlife (``deer`` / ``sheep`` / custom ``tiger``, etc.) does not join the ``"ai"`` alliance and does not ally with players, hostile creep, or other wildlife herds; mixed slots are unchanged. See ``../player/hunting.htm`` §3.1.
- Tech ``hunting_techniques``: faster orchard/carcass gathering.

Example animal::

    def deer
    class soldier
    is_huntable 1
    flee_on_hit 1
    food_deposit food_carcass
    food_deposit_qty 35
    no_number 1
    ai_mode guard

Inheritance (since 1.3.8.3)
-----------------------------

::

    is_a footman                    ; all attributes
    is_a footman(hp_max mdg)        ; selective
    is_a footman(apart hp_max)      ; exclusion inheritance (apart form)
    is_a footman(-hp_max)           ; exclusion inheritance (- prefix, same as apart)
    is_a footman(-hp_max -mdg)      ; exclude multiple attributes
    is_a footman(mdg) knight(hp_max) ; multiple parents

style
------

The style is defined in "ui/style.txt" and in the localized version of "style.txt".

shortcut
>>>>>>>>

Simple orders, building orders, training orders, orders using an ability can be given with a shortcut, if a shortcut is defined.

To define a shortcut, define a "shortcut" property followed by the corresponding letter. The letter must be in lowercase.

If the order is a simple order, the shortcut must be defined by the order (ex: patrol).
If the order is a complex order (train, build, use an ability), the shortcut must be defined by the second part of the order.
For example, define an "m" shortcut for the meteor ability so the mage will have the "m" shortcut to cast meteors.

intro (since 1.4.1.5)
>>>>>>>>>>>>>>>>>>>>>

Add a unit description below ``title``::

    def footman
    title 87
    intro 1001

The text must exist in ``tts.txt``.

Combat sound system (since 1.3.8.2; 1.4.4.6 renamed matk/ratk to mdg/rdg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Replaces the old attack sounds::

    launch_mdg / launch_rdg
    mdg_hit / rdg_hit / mdg_hit_vs / rdg_hit_vs
    mdg_missed / rdg_missed
    mdg_dodge / rdg_dodge
    launch_charge_mdg / launch_charge_rdg
    charge_mdg_hit / charge_rdg_hit
    casting
    disappear
    weapon_switched
    death / falling / falling_delay / falling_on_<terrain>
    move / move_on_<terrain>

**Battle shouts (layered playback since 1.4.5.0; see :doc:`battle-shouts`)**

- ``shouts`` — combat shout pool; define on ``def walking_unit`` so infantry and archers inherit

**Terrain footsteps and falling sounds (since 1.3.9.1; terrain type names since 1.4.5.0)**

In ``def unit`` (or a specific unit) in ``style.txt``:

- ``move`` — default footstep sounds
- ``move_on_<key>`` — footsteps that depend on terrain
- ``falling`` — generic body-fall sound after death
- ``falling_delay <seconds>`` — wait after ``death`` before ``falling``; omit or ``0`` for immediate play
- ``falling_on_<key>`` — terrain-specific fall sound

``<key>`` resolution (same for ``move_on_`` and ``falling_on_``):

1. **Terrain type name** — the ``rules.txt`` / ``style.txt`` def on the unit's square (e.g. ``ocean``, ``plain``, ``mountain``). With sub-cell terrain, the type at the unit's coordinates is used.
2. **``ground`` category** — the ``ground`` value on that terrain's ``style.txt`` def (e.g. ``creek`` with ``ground water`` matches ``move_on_water`` / ``falling_on_water``).

The terrain type name is tried before ``ground``. ``falling_on_ocean`` works on ``ocean`` even when that def has no ``ground`` line; on ``creek``, ``falling_on_creek`` wins over ``falling_on_water`` when both exist.

Example::

    def unit
    move 1052 1053
    move_on_ocean 1088 1348
    move_on_water 1088 1348
    move_on_grass 1053 1054
    falling 80051
    falling_delay 1
    falling_on_ocean fallwater
    falling_on_water splash

Only **ground** units use square terrain for ``move_on_``; otherwise ``move`` is used. Nearby immobile objects (buildings, trees, etc.) can also supply ``move_on_<object type>`` or ``move_on_<ground>`` when closer.

Burst units fire ``launch_mdg`` / ``launch_rdg`` once per shot in a ``damage_seq``
burst. You can list several sound IDs on the same line so each shot picks from them.

``mdg_hit_vs`` / ``rdg_hit_vs`` can play different hit sounds by target type. The target
match set includes the unit type, inherited unit types, and the buff/debuff types currently
active on the target. Example::

    def swordsman
    mdg_hit_vs b_absolute_defense iron_clang

When ``swordsman`` hits a target that currently has ``b_absolute_defense``, ``iron_clang``
is played.

Since 1.4.4.6, docs and bundled resources use the ``mdg`` / ``rdg`` names. Old
``matk`` / ``ratk`` keys remain available as a compatibility fallback for existing mods.

Skills, buffs, and debuffs can also define trigger sounds::

    def skill_counter
    alert counter_alert
    ready counter_ready
    triggered counter_proc

    def b_absolute_defense
    triggered shield_on
    noise loop shield_hum

Manually used skills play ``alert``. If a skill rule has ``ready \<seconds\>``, the skill
style can define ``ready \<sound\>``; manual and automatic triggers play it when prep starts.
Skills triggered by ``active_trigger_skills``,
``passive_trigger_skills``, ``attack_trigger_skills``, or ``attack_replace_skills`` prefer
``triggered`` and fall back to ``alert`` when ``triggered`` is not configured. Buffs and
debuffs applied through trigger fields play their own ``triggered`` sound when configured.
Persistent buff/debuff status sounds must be written explicitly as ``noise loop \<sound\>`` or
``noise repeat \<interval\> \<sound...\>``; ``noise \<sound\>`` keeps its existing parsing behavior
and is not treated as a loop automatically.

Menu and game music (since 1.4.0.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

In ``def parameters``::

    menu_music <id>
    campaign_music <id>
    game_creation_music <id>
    server_lobby_music <id>
    game_music <id>
    battle_music <id>
    victory_sound <id>
    defeat_sound <id>
    main_menu_select_sound <id>
    main_menu_confirm_sound <id>

Faction music (since 1.4.0.3)::

    china_music china
    china_battle_music china_battle

Map overrides: ``map_music``, ``map_battle_music``, ``map_victory_sound``, ``map_defeat_sound``.
Music files: ``ui/music/\<id\>.mp3`` or ``mods/\<mod\>/ui/music/\<id\>.mp3``.
