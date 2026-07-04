# StarCraft mod: Terran addons & recombine

Mod: enable ``mods = starcraft`` in ``SoundRTS.ini``.

This guide covers Tech Lab / Reactor addons: build, lift-off detach, flying recombine, and the difference between **building land** (build permission) and slot alignment (reattach).

StarCraft maps use **build sites** (``build_site``, square terrain ``build_sites``) rather than classic **meadows**. Below, “building land” means any ``class building_land`` object; in this mod that is usually ``build_site``.


----


1. Concepts
-------------



.. list-table::
   :header-rows: 1

   * - Term
     - Meaning
   * - Host
     - Barracks, Factory, or Starport (``can_have_addon``)
   * - Addon
     - Tech Lab or Reactor (``is_addon 1``), built on the host’s side slot
   * - Slot
     - About 3.5 tiles east of the host (``addon_offset_x``, default 3500 internal units)
   * - Building land
     - A ``class building_land`` object on the square (``build_site`` in this mod); ground Terran buildings must consume one to land
   * - Recombine
     - After lift-off the addon stays on the ground; another host lands with the slot aligned and auto-reattaches the orphan addon



Tech Lab grants per host, e.g.:

- Barracks + Tech Lab → Marauder
- Factory + Tech Lab → Siege Tank
- Starport + Tech Lab → Medivac

Reactor uses ``addon_train_multiplier 2``.


----


2. Building an addon
----------------------


1. Select an existing host (e.g. Barracks), not bare ground.
2. Build Tech Lab or Reactor from the menu.
3. The addon self-constructs on the host’s side (``self_constructs 1``); it does not use its own building-land slot.

Test map: ``terran_addon_test``.


----


3. Lift-off
-------------


Barracks / Factory / Starport can change to flying form (``can_change_to flying_*``):

1. Select the ground building → change_to → flying variant.
2. The host leaves the ground; the addon stays and is detached.
3. Building land is restored where the host stood: **the same type the building consumed when built** (``build_site`` in this mod). If the map only spawns build sites (``nb_build_site_by_square``, ``building_land build_site``, etc.), lift-off leaves a build site — you do **not** need ``default_building_land build_site`` in mod rules for that.

One square may have several patches (e.g. Barracks and Factory each lift once → two build sites). On starts with only one map patch, the Factory may start without building land; patches appear at each building’s lift position.


----


4. Normal land vs recombine land
----------------------------------


4.1 Two separate checks
~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Step
     - Decides
     - Does not decide
   * - Landing
     - Which building-land object is consumed; host (x, y)
     - Reattach
   * - Reattach
     - Orphan Tech Lab attaches to host
     - Which patch was used



Building land = permission to land (any ``class building_land`` on the square; API names like ``find_meadow_near_xy`` are historical).  
Slot = geometry: addon at ``(host.x + 3500, host.y)``; reattach requires slot alignment within ~2.5 tiles Manhattan distance.

You may see the Factory on a “center patch” while Tank training works: slot is aligned, not because the building sits on grass under the lab.

4.2 Normal land (own lift-off patch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. Tab the building land left when that building lifted (build site in this mod).
2. Backspace (default ``go``), wait until arrival.
3. change_to ground form.

The building lands there and does not take over an orphan Tech Lab. If a compatible orphan addon remains on the square, you hear: *Go to the Tech Lab first, then land to reattach the addon* (TTS 7350).

4.3 Recombine land (take orphan Tech Lab)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. Build Tech Lab on Barracks, lift Barracks (lab stays).
2. Lift Factory, fly to that square.
3. Tab the Tech Lab (not a building-land patch).
4. Backspace go — target becomes the landing slot (~3.5 tiles west of the lab), not the lab’s center.
5. change_to Factory.

Result:

- Factory spawns at slot coordinates;
- The nearest building-land object on the square is consumed (often a center patch);
- Slot aligns with the lab → auto-reattach → Tank (etc.) available.

Test map: ``terran_recombine_test``; campaign ``sc_build_tests`` chapter 4.


----


5. Quick reference
--------------------



.. list-table::
   :header-rows: 1

   * - Goal
     - Tab
     - After go
     - change_to result
   * - Land on lift spot
     - Lift-off build site
     - Backspace
     - No reattach, no Tank
   * - Take orphan Tech Lab
     - Tech Lab
     - Backspace (flies to slot)
     - Reattach, Tank available



With multiple patches, Tab voice may say “build site” for all — use direction; for recombine, Tab the lab.


----


6. FAQ
--------


Why can I train Tank when the lab has no patch nearby, only center patches?

Going to the Tech Lab flies you to the slot. Landing places the Factory at slot (x,y) but deletes the nearest building-land object (often a center one). Reattach checks distance from the lab to ``factory.x + 3500``, not which patch was used.

Why did center landing used to reattach?

Older logic snapped landing anywhere on the square within ~5.5 m of the lab. Now: go to your own lift-off patch → land in place; recombine requires go to the Tech Lab.

Slot aligned but looks far from the lab?

The lab is on the host’s side (~3.5 tiles offset), not under the host center — SC2-style layout.


----


7. Mod authors (rules.txt)
----------------------------



.. list-table::
   :header-rows: 1

   * - Keyword
     - Role
   * - ``can_have_addon``
     - Allowed addon types on host
   * - ``is_addon 1``
     - Addon building
   * - ``addon_host_types``
     - Which hosts accept this addon
   * - ``addon_grants_train_\<host\>``
     - Extra train options when attached
   * - ``addon_grants_research``
     - Extra research when attached
   * - ``addon_train_multiplier``
     - Reactor multiplier
   * - ``can_change_to`` / ``ground_form``
     - Lift / land forms
   * - ``change_time``
     - Morph time
   * - ``nb_build_site_by_square``
     - Auto-fill each square with ``build_site``; see ``mod/mapmaking.rst`` and ``mod/building-land-terrain.htm``



See also ``mods/starcraft/readme.txt``.  
Author reference: ``mod/modding.rst`` section *Build fields, addons & lift-off*.
