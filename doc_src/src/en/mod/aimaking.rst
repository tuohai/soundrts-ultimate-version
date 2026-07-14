Making AIs Tutorial
====================

.. contents::

1. Introduction
-----------------

This tutorial explains how to write computer AIs.
You edit ``ai.txt`` (scripts) and, for mods, ``rules.txt`` (per-faction difficulty
mappings). These files live in the ``res`` folder of the SoundRTS package; a mod,
campaign or map can ship its own copies too.

An AI is a small script: a list of commands the computer runs from top to
bottom, looping forever. No programming knowledge is required.

2. ``ai.txt``: AI scripts
-----------------------------------

In ``ai.txt``, each AI starts with ``def \<name\>`` followed by its commands::

    def tang_empire_easy
    research 1
    workers 12
    get 9 villager 5 footman
    attack
    goto -1

Notes:

- Names can be any identifier, e.g. ``tang_empire_easy`` or ``my_mod_hard``.
  Custom names are not shown in the invite menu; players see the difficulty
  tier mapped in ``rules.txt`` (next section).
- If a mod's ``ai.txt`` contains ``clear``, every AI script loaded so far
  (including the base five tiers from ``res/ai.txt``) is discarded. This
  does not change how many invite buttons appear; it only affects which
  ``def`` entries remain loaded. Most mods do not need ``clear``.
- Same-named ``def`` lines in a later layer override earlier ones.
- If no script exists for a requested tier at runtime, ``get_ai`` falls back to
  the closest defined script (including the legacy ``easy`` / ``aggressive``
  alias chain).

3. Invite menu and ``rules.txt`` mappings
---------------------------------------------------

The single-player and multiplayer invite computer menus are driven by the
``current mod's ``rules.txt``, not by a fixed list of five buttons. You do
not need empty placeholder lines like ``def beginner`` in ``ai.txt``.

Without a mod
~~~~~~~~~~~~~~

The menu always offers the five standard tiers:

- ``beginner`` -- Beginner (初级)
- ``intermediate`` -- Intermediate (中级)
- ``advanced`` -- Advanced (高级)
- ``expert`` -- Expert (专家)
- ``nightmare`` -- Nightmare (噩梦)

With a mod loaded
~~~~~~~~~~~~~~~~~~

The engine scans faction blocks in ``rules.txt`` for difficulty mapping lines.
Each tier appears in the menu when at least one faction maps that tier to a
script name that exists as a ``def`` in ``ai.txt``.

Recommended (new mods) -- standard tier names inside each faction block::

    def tang_empire
    class race
    townhall county_government
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

This yields Invite beginner / intermediate / advanced computer (as many
buttons as you map). If the player picks "beginner" with the Tang faction, the
``tang_empire_easy`` script runs.

Legacy mods -- still using ``easy`` / ``aggressive``::

    def orc
    class race
    ...
    easy orc_defensive
    aggressive orc_aggressive

The menu shows Invite quiet / aggressive computer (defensive / aggressive
labels in Chinese UI). The host still invites tier ``easy`` or ``aggressive``;
``rules.txt`` resolves the actual script per faction.

Summary
~~~~~~~~

- ``ai.txt`` holds scripts; ``rules.txt`` maps tiers to scripts per faction.
- Different factions can map the same tier to different scripts; the menu lists
  tier names only, not faction-specific script names.
- If both ``beginner`` and ``easy`` are mapped, only ``beginner`` is listed.
- Internal scripts such as ``timers`` never appear in the invite menu.
- Multiplayer hosts send ``invite_ai \<tier\>`` (e.g. ``invite_ai beginner``).
  Legacy commands ``invite_beginner``, etc. still work.

4. Settings (written once, near the top of a "def")
-----------------------------------------------------

These tune the AI's overall behaviour. Put them near the top of a ``def`` so
they run before the loop. A higher difficulty usually means a bigger economy,
research turned on, more bases and more willingness to attack.

- ``constant_attacks 0/1`` -- when ``1`` the AI keeps attacking and exploring
  the map instead of turtling at home.
- ``research 0/1`` -- when ``1`` the AI researches weapon/armor/ability
  upgrades whenever it can afford them.
- ``workers \<n\>`` -- the number of workers (peasants) the AI tries to keep.
  More workers means a stronger economy. Default: ``10``.
- ``expand \<n\>`` -- the total number of town halls (bases) to maintain. The
  starting base counts, so ``expand 2`` makes the AI build one extra base.
  Default: ``0`` (no extra expansion).
- ``attack_ratio \<percent\>`` -- how strong the AI's army must be, compared to
  the enemy in the target area, before it attacks. ``180`` (the default) means
  "attack only with an 80% advantage" (cautious). Lower values make the AI
  commit sooner; below ``100`` it attacks even when slightly weaker
  (relentless pressure).
- ``counter_skill \<0-100\>`` -- how well the AI's units use ``mdg_vs`` /
  ``rdg_vs`` counter bonuses when choosing targets and sending attacks.
  ``0`` ignores counters (pure ``menace`` priority). ``100`` always picks the
  best counter match, including inherited types via ``is_a`` (for example,
  ``mdg_vs cavalry`` also counters a camel with ``is_a cavalry``). Values in
  between blend counter bonus and ``menace``. Default if omitted: ``100``.

  Vanilla ``res/ai.txt`` sets: beginner ``25``, intermediate ``50``,
  advanced ``75``, expert ``90``, nightmare ``100``.
- ``starting_resources \<amounts...\>`` -- bonus resources added on top of
  the map (or faction) start. Same order and same units as map
  ``starting_resources`` (e.g. ``10 10`` = 10 gold and 10 wood; internally
  stored as ``× 1000`` like map starts). Omitted = no bonus.
- ``starting_units \<unit\>...`` -- bonus units or buildings spawned at the
  AI's start square after the normal start. Uses the same flat syntax as map
  ``starting_units`` (put a count before a type name to spawn several:
  ``5 footman 2 archer``). Respects faction ``equivalent`` names. Do not
  consume population (unlike map starting units). Omitted = no bonus units.
- ``starting_population \<n\>`` -- bonus population cap added on top of
  houses and other ``population_provided`` units. Plain integer (not ``× 1000``).
  ``available_population`` is still capped by the map's ``global_population_limit``.

  These lines are applied once at game start; they are not part of the
  script loop (unlike ``get`` / ``attack``).

  Vanilla ``res/ai.txt`` bonuses (on top of every map start):

  - intermediate: ``starting_resources 50 50``, ``starting_population 10``
  - advanced: ``100 100`` + ``2 footman 2 archer``, ``starting_population 20``
  - expert: ``200 200`` + ``5 footman 4 archer 2 knight``, ``starting_population 40``
  - nightmare: ``400 400`` + ``8 footman 6 archer 4 knight``, ``starting_population 60``
- ``watchdog \<seconds\>`` -- a safety net: if the AI is stuck on the same line
  for this long, it moves on to the next line. ``0`` disables it.

Counter targeting (``counter_skill``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``counter_skill`` is above ``0``, computer units prefer enemies they
counter according to ``rules.txt`` damage bonuses:

- A knight with ``mdg_vs archer 12`` focuses archers over higher-``menace`` units.
- An archer with ``rdg_vs footman 7`` focuses footmen.
- Type names in ``mdg_vs`` / ``rdg_vs`` match the target's ``type_name`` or any
  name in its ``is_a`` inheritance chain.

At low ``counter_skill``, high-``menace`` targets can still win; at ``100``,
the best counter match wins unless only one enemy is in range.

Since 1.4.5.2, default ``menace`` is a **multi-dimensional combat score**
(damage, hit cover, cooldown, ready/wind-up, HP, armor, dodge, range, speed),
optionally overridden with ``menace_mult`` / ``menace_vs`` — see ``modding.rst``
*Auto menace / targeting priority*.

This affects both micro (which enemy each unit attacks) and macro
(which area to push and which units to send first), as long as the army still
meets ``attack_ratio``.

5. Action commands
--------------------

- ``get \<n\> \<unit\>...`` -- recruit or build until the AI owns ``\<n\>`` of each
  listed unit/building. You can list several pairs at once. See ``rules.txt``
  for the exact unit type names.
  Example: ``get 10 footman 20 archer 10 knight``
- ``attack`` -- from this point on, attack whenever strong enough (it also
  turns on ``constant_attacks``).
- ``wait \<seconds\>`` -- stay on this line for ``\<seconds\>`` before continuing.
  Useful for pacing (an easy AI can ``wait`` between waves). Note: a non-zero
  ``watchdog`` can still pull the AI off the line early.

6. Flow control
-----------------

- ``label \<name\>`` -- marks a position you can jump to.
- ``goto \<name\>`` -- jump to a label. ``goto`` also accepts a relative line
  offset such as ``goto -1`` (go back one line).
- ``goto_random \<name1\> \<name2\> ...`` -- jump to one of the listed labels,
  chosen at random. Great for making the AI unpredictable.

7. Mod example (three tiers, per-faction scripts)
---------------------------------------------------

``ai.txt`` excerpt::

    def tang_empire_easy
    constant_attacks 0
    get 9 villager 5 footman
    attack
    goto -1

    def tang_empire_hard
    constant_attacks 1
    get 9 villager 10 footman
    attack
    goto -1

``rules.txt`` excerpt for the Tang faction::

    def tang_empire
    class race
    peasant villagers
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

The menu shows three tiers; Tang + "intermediate" runs ``tang_empire_hard``.

8. Complete example (one vanilla tier)
----------------------------------------

::

    def advanced

    counter_skill 75
    watchdog 480
    constant_attacks 1
    research 1
    workers 18
    expand 2          ; second base for a stronger economy
    attack_ratio 150  ; pushes with a smaller advantage

    label open
    get 9 peasant 6 footman 4 archer
    attack
    goto_random knights mixed

    label knights
    get 9 peasant 16 knight 10 archer 3 catapult
    attack
    goto open

    label mixed
    get 9 peasant 20 archer 12 knight 5 priest 4 catapult
    attack
    goto open

Everything after a ``;`` on a line is a comment and is ignored.
