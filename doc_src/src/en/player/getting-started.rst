SoundRTS Player Guide — Start Here
===================================



A progressive reading path: basics → core RTS → modern features → multiplayer → mods.

Mod authors: `Developer Getting Started <../mod/getting-started.htm>`_.


----


What is SoundRTS?
------------------


An audio real-time strategy game inspired by Warcraft and StarCraft, designed for blind players and anyone who enjoys commanding by ear. Two views:


.. list-table::
   :header-rows: 1

   * - Mode
     - Enter
     - Best for
   * - Map mode (default)
     - at launch
     - Macro: select units, issue orders, check resources
   * - First-person (RPG) mode
     - Alt+Space / Ctrl+Space
     - Micro: walk, aim skills




----


Level 1 — Ten-minute start
---------------------------


Goal: select a peasant, mine gold, build a farm and a house.


.. list-table::
   :header-rows: 1

   * - Action
     - Key
   * - Next friendly unit
     - Q
   * - Next building
     - W
   * - Next / previous command
     - A / Shift+A
   * - Next / previous target
     - Tab / Shift+Tab
   * - Confirm
     - Enter
   * - Default command on target
     - Backspace



Resources: Z gold · X wood · Shift+Z food · C population.

Movement: arrow keys, Page Up/Down between interesting squares, Space to follow selection.

Full command list: `manual.rst <../../../player/manual.rst>`_ §3, or F10 in-game menu.


----


Level 2 — Core RTS loop
------------------------


- Economy: peasants → houses (population cap) and farms (food) → buildings → army
- Rally point: select town hall → Tab to gold mine → Backspace
- Groups: Shift+6–9 to save, 6–9 to recall
- Scouting: defense mode flees from stronger enemies
- Forced move/attack: Ctrl+Backspace
- Zoom: F8 (sub-squares for precise placement)

Tips: `unit-default-behavior <unit-default-behavior.htm>`_


----


Level 3 — Modern features (1.4+)
---------------------------------



.. list-table::
   :header-rows: 1

   * - Topic
     - Doc
   * - Attributes / inventory / equipment
     - [inventory-and-equipment.md](inventory-and-equipment.htm)
   * - Achievements, ranks, armory
     - [achievements.htm](achievements.htm)
   * - Post-game score (S–E)
     - [score-and-grades.md](score-and-grades.htm)
   * - Pre-mission cards
     - [loadout-cards.md](loadout-cards.htm)
   * - Campaigns & co-op
     - [campaign-and-co-op-improvements.md](campaign-and-co-op-improvements.htm)
   * - Random maps (seed / share code)
     - [random-map.md](random-map.htm)
   * - Layered hotkeys
     - [layered-hotkeys.md](layered-hotkeys.htm)
   * - Primary & secondary voice libraries
     - [voice-libraries.md](voice-libraries.htm)
   * - Bring items to a square
     - [brought-item-delivery.md](brought-item-delivery.htm)




----


Level 4 — Multiplayer
----------------------


Main menu → multiplayer → pick server → create/join room → F7 chat. Teams fixed before start; dynamic alliances F12 / F4 / Ctrl+F4 when allowed. Default port 2500.


----


Level 5 — Mods & themed docs
-----------------------------


Enable in ``user/SoundRTS.ini``: ``mods = soundpack,starcraft`` or ``--mods=...``


.. list-table::
   :header-rows: 1

   * - Topic
     - Doc
   * - Hunting / herding
     - [hunting.htm](hunting-system.htm)
   * - Burst attacks
     - [burst-attack-damage-seq.md](burst-attack-damage-seq.htm)
   * - StarCraft resources
     - [starcraft-resources.htm](starcraft-resources-vespene.htm)
   * - Terran add-ons
     - [starcraft-terran.htm](starcraft-terran-addons.htm)
   * - Zerg creep
     - [starcraft-zerg-creep.md](starcraft-zerg-creep.htm)


If in-match SFX stutter or cut out, raise ``mixer_buffer`` under ``[audio]`` in
``SoundRTS.ini`` (default ``2048``; try ``4096``), and optionally
``[general] num_channels`` (try ``32``). Restart after editing. Details:
:doc:`../mod/audio-management`.


Release notes: `Release notes <../../relnotes.htm>`_ — full version history.


----


Next steps
-----------


- Play through the tutorial → Level 3 docs as needed
- Modding: `Developer Getting Started <../mod/getting-started.htm>`_
- Index: `README.md <README.htm>`_
