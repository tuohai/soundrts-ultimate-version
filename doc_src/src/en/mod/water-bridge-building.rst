Building bridges on water (tile-by-tile spans)
================================================

.. epigraph:: For **mod authors** and mappers: workers can lay **walkable bridge spans** one water square at a time on rivers, lakes, and oceans. Complements ``modding.htm`` (construction sites) and ``building-land-terrain.htm`` (``big_bridge``, ``ford``).


----

Design
------

- **One map square = one bridge span**, not a single “whole bridge” object covering a wide river.
- **Construction** uses a ``BuildingSite`` (scaffold): ground units can walk onto that square to build, but **unfinished scaffolds do not grant passage** (no scaffold-only shortcuts across water).
- **When complete**, the square gets the ``bridge_terrain`` def (default ``bridge_deck``), links to adjacent land / completed spans, and is **neutral** — all ground players may use it.

Built-in example: ``wooden_bridge`` (requires ``lumbermill``, 5 gold / 10 wood).

Rule attributes
---------------

On a ``class building`` in ``rules.txt``:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``is_buildable_on_water_only 1``
     - Only on **pure water** squares (``is_water`` without map ``is_ground`` — rivers, lakes, oceans; not map ``ford`` / ``big_bridge``)
   * - ``bridge_terrain <name>``
     - When the building **finishes**, apply this ``class terrain`` to the square (e.g. ``bridge_deck``)

Finished terrain example::

    def bridge_deck
    class terrain
    is_water 1
    is_ground 1
    is_dynamic 0

Buildable span example::

    def wooden_bridge
    class building
    cost 5 10
    hp_max 400
    time_cost 60
    is_buildable_on_water_only 1
    bridge_terrain bridge_deck
    requirements lumbermill

In-game flow
------------

1. Select a worker; from **adjacent land**, order ``wooden_bridge`` on a water square.
2. A ``BuildingSite`` is placed; the cell temporarily becomes ``is_ground`` so the worker can path **onto the scaffold** (ocean tiles with ground speed 0 regain normal speed while scaffolded).
3. The worker builds on that square — same TTS as any site: **“bridge span, under construction”** (building type title + ``buildingsite`` title).
4. On completion the ``wooden_bridge`` building remains and ``bridge_terrain`` is applied; the tile becomes passable and connects to shore / other finished spans.

Scaffold restrictions
---------------------

- Only one temporary exit to the **shore square where the order was given**; **no** direct scaffold-to-scaffold steps.
- Passage sync runs only for **finished`` ``bridge_terrain``**, not for bare scaffolds.
- Water ``BuildingSite`` units are **not** drowned (``is_a_building`` exempt).
- Hammer sounds play on the **site** (``buildingsite`` ``noise_when_building``), not on the worker.

Voice & footsteps (``style.txt`` / ``tts.txt``)
------------------------------------------------

Same as other construction: **no** separate “scaffold” style def; sites use ``buildingsite`` ``title 107 128`` (“under construction”).

| TTS ID | Text (zh) | Use |
|--------|-----------|-----|
| 153 | bridge (generic) | Exit type ``bridge`` |
| 4348 | trestle | Map terrain ``big_bridge`` |
| 5108 | wooden bridge span | Unit ``wooden_bridge``, site name |
| 5109 | bridge deck | Finished terrain ``bridge_deck`` |

**Footsteps:** During scaffold and after completion, audio uses the ``ground`` of ``bridge_terrain`` (default ``bridge_deck`` ``is_a big_bridge`` → ``ground wood``).

**Square voice:** While building, the cell still reports the underlying water; **“bridge deck”** is announced only after completion.

UI: Tab & passages
------------------

- ``wooden_bridge`` is **not** an exit; **Tab** at the center of a deck square can select the span building.
- On bridge/scaffold squares, maps with ``select_target no_exit`` (e.g. td2) still cycle **passage exits** via Tab.
- Dedicated passage cycling: ``select_passage`` when bound.

Custom spans (e.g. iron bridge)
-------------------------------

Define the **building** + **finished terrain** only — no ``bridge_scaffold`` style:

**rules.txt** — ``iron_bridge`` with ``bridge_terrain iron_bridge_deck``; **style.txt** — titles and ``iron_bridge_deck is_a big_bridge`` (or custom ``ground``). Scaffold footsteps follow ``bridge_terrain``; site TTS stays “iron bridge span, under construction”.

vs. map ``big_bridge``
----------------------

Player-built spans use ``bridge_deck`` when done, leave a destructible ``wooden_bridge`` entity, and revert to impassable water when destroyed. Map-placed ``big_bridge`` is fixed at load time with no building entity.

Implementation & tests
----------------------

``soundrts/world_build_rules.py``, ``worldorders/movement.py``, ``clientgameentity/properties.py``, ``audio.py``; tests in ``soundrts/tests/test_bridge_terrain.py``.

See also ``building-land-terrain.htm``, ``modding.htm``.
