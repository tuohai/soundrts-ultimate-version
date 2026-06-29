# Layered Hotkey Scheme

This guide describes SoundRTS layered interface hotkeys: a global base layer plus a per-interface layer, so the same physical key can mean different things in different modes. Intended for players and mod authors customizing bindings.


----


1. Overview and motivation
----------------------------


Old scheme
~~~~~~~~~~~


All hotkeys lived in a single file ``res/ui/bindings.txt``. Keys became saturated; the same letter conflicted across unit selection, orders, and map browsing.

New scheme
~~~~~~~~~~~


- Global layer: resources, movement, square jumps, command confirmation — available in every mode.
- Interface layer: mode-specific bindings (unit, building, command, skill, map, etc.).
- Mode switching: F-keys toggle within groups; help / map / diplomacy are overlay modes that restore the previous mode on exit.

Implementation: ``soundrts/clientgame/interface_modes.py``.


----


2. Architecture and loading rules
-----------------------------------


.. code-block:: text

   flowchart TD
       global[global_bindings.txt]
       mode[current mode txt]
       custom[cfg/bindings.txt]
       mod[mod bindings.txt]
       global --> merge[merged load]
       mode --> merge
       custom --> merge
       mod --> merge
       merge --> active[active hotkeys]


Load order
~~~~~~~~~~~


1. `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_ (global base)
2. Current mode file (see table below)
3. User overrides `cfg/bindings.txt <../../../soundrts/paths.py>`_ (``CUSTOM_BINDINGS_PATH``)
4. Non-stub mod ``bindings.txt`` (legacy append)

Later loads override earlier for the same key.

Sub-screens and RPG
~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Context
     - Behavior
   * - Inventory / equipment / attributes
     - Temporarily replaces ``\_bindings``; ``restore_active_bindings`` on exit
   * - RPG first-person
     - Additional [``res/ui/rpg_bindings.txt``](../../../res/ui/rpg_bindings.txt)
   * - Map editor
     - Independent [``res/ui/editor_bindings.txt``](../../../res/ui/editor_bindings.txt)



Mode files
~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Mode
     - File
   * - Global
     - ``global_bindings.txt``
   * - Unit selection
     - ``unit_bindings.txt``
   * - Building selection
     - ``building_bindings.txt``
   * - Commands
     - ``command_bindings.txt``
   * - Skills
     - ``skill_bindings.txt``
   * - First person (RPG)
     - ``rpg_bindings.txt``
   * - Help & query
     - ``help_bindings.txt``
   * - Map browse
     - ``map_bindings.txt``
   * - Diplomacy
     - ``diplomacy_bindings.txt``




----


3. Mode switching (F-keys and ESC)
------------------------------------



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - F1
     - Unit selection ↔ Building selection
   * - F2
     - Commands ↔ Skills
   * - F3
     - Inventory ↔ Equipment (single friendly unit required; see [inventory-and-equipment.md](inventory-and-equipment.htm))
   * - F4
     - Enter help & query (press again or Esc to exit)
   * - F12
     - Enter diplomacy (press again or Esc to exit)
   * - ESC
     - Cancel order / exit sub-screen; otherwise enter map browse



Switching to non-map modes announces the mode name (e.g. “unit selection”, “command mode”).

Special behavior when ESC enters map browse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Action
     - Voice
     - Internal state
   * - ESC → map
     - Always announces “map browse” + current square overview
     - If a deposit/meadow/passage was selected earlier, silently restores `interface.target`
   * - ``f`` / ``g`` / ``m`` / ``p`` in map
     - Announces the element as usual
     - Saves selection for restore after leaving map



Example: In map mode, ``f`` selects a gold mine → F1 to unit mode, select a peasant → ESC back to map → you hear “map browse, 8, 13, 1 town hall…” (square overview), not the mine again; focus remains on the mine, so you can press Enter to send the gather order immediately.

Leaving map mode saves the current map focus via ``save_map_browse_target``.


----


4. Global hotkeys
-------------------


Always active in every mode (``global_bindings.txt``).

Resources and population
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``z``
     - Resource 1 status
   * - ``x``
     - Resource 2 status
   * - ``SHIFT Z``
     - Resource 3 status
   * - ``c``
     - Population status



Quick entry (legacy)
~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``ALT V``
     - Attributes screen
   * - ``SHIFT V``
     - Inventory
   * - ``CTRL V``
     - Equipment



Target selection
~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``TAB`` / ``SHIFT TAB``
     - Next / previous target
   * - ``CTRL TAB`` / ``CTRL SHIFT TAB``
     - Next / previous useful target



Movement
~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - Arrow keys
     - Move 1 square
   * - ``SHIFT`` + arrows
     - Move 5 squares
   * - ``CTRL`` + arrows
     - Move 1 square (no collision)
   * - ``CTRL SHIFT`` + arrows
     - Move 5 squares (no collision)



Square jumps
~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``PAGE DOWN`` / ``PAGE UP``
     - Next / previous scouted square
   * - ``CTRL PAGE DOWN`` / ``CTRL PAGE UP``
     - Conflict squares
   * - ``ALT PAGE DOWN`` / ``ALT PAGE UP``
     - Unknown squares
   * - ``SHIFT PAGE DOWN`` / ``SHIFT PAGE UP``
     - Resource squares



Default command and confirmation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``BACKSPACE``
     - Default command
   * - ``SHIFT BACKSPACE``
     - Default command (queue)
   * - ``CTRL BACKSPACE``
     - Default command (imperative)
   * - ``RETURN`` / keypad ``ENTER``
     - Validate order
   * - With ``SHIFT`` / ``CTRL``
     - Queue / imperative variants



Observation and query
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``LCTRL`` / ``RCTRL``
     - Examine
   * - ``SPACE``
     - Unit status
   * - ``v``
     - Hit points
   * - ``F9`` / ``SHIFT F9``
     - Objectives
   * - ``F11``
     - Player list



System
~~~~~~~



.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``F5`` / ``F6``
     - History previous / next
   * - ``F10`` / ``CTRL C`` / ``ALT F4``
     - Game menu
   * - ``HOME`` / ``END`` etc.
     - Volume
   * - ``ALT SPACE`` / ``CTRL SPACE``
     - First-person mode
   * - ``CTRL F2``
     - Display toggle
   * - ``CTRL F3``
     - Talking clock toggle
   * - ``CTRL SHIFT F4``
     - Change player view
   * - ``ALT M`` etc.
     - Music volume




----


5. Per-interface hotkeys
--------------------------


5.1 Unit selection
~~~~~~~~~~~~~~~~~~~


File: ``unit_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Category
     - Keys
     - Notes
   * - Soldiers batch
     - ``a``
     - Local all; ``CTRL a`` map-wide
   * - Cycle unit
     - ``q`` / ``SHIFT q``
     - Local; ``CTRL q`` map-wide
   * - Order shortcut
     - ``b``
     - Uses ``shortcut`` from style.txt orders
   * - Filters
     - ``m`` / ``n``
     - Side / type when picking targets
   * - Workers
     - ``s`` batch / ``w`` cycle
     - Former ``d``/``e`` keys
   * - Soldiers 1–7
     - `d/e` … `;/p`
     - Same key region as buildings
   * - Groups
     - ``1``–`5` set, `6`–`9` recall
     - ``CTRL`` for map-wide groups



Unit mode can override ``BACKSPACE`` locally.

5.2 Building selection
~~~~~~~~~~~~~~~~~~~~~~~


File: ``building_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Key row
     - Maps to
   * - ``d f g h j k l ;``
     - building1 – building8
   * - ``e r t y u i o p``
     - building9 – building16



Per key: select local type; ``SHIFT`` + key cycles one; ``CTRL`` + key selects map-wide.

Mod config: set ``keyboard building1`` … ``keyboard building16`` in ``style.txt`` (alongside generic ``keyboard building``). Base campaign example: townhall→building1, house→building2.

5.3 Command mode
~~~~~~~~~~~~~~~~~


File: ``command_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Slot
     - Keys
   * - Browse
     - ``a`` / ``SHIFT a``
   * - 1–9
     - `s d f g h j k l ;`
   * - 10–18
     - ``w e r t y u i o p``
   * - 19–30
     - ``1``–`0` `-` `=`
   * - Repeat
     - ``ALT x`` / ``ALT z``



Slots follow the unit’s menu order; extra keys say “none” if fewer than 30 orders exist.

5.4 Skill mode
~~~~~~~~~~~~~~~


File: ``skill_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``a`` / ``SHIFT a``
     - Browse skill menu (next / previous)



5.5 First person (RPG) mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


When you enter first-person mode (global ``ALT SPACE``), ``rpg_bindings.txt`` is layered on top of the current interface bindings.


.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - `1`–`9`
     - Skills 1–9
   * - ``0``
     - Skill 10
   * - `-` / `=`
     - Skills 11 / 12
   * - ``ALT /``
     - Skill list
   * - ``CTRL A``
     - Auto attack
   * - ``CTRL F8`` / ``SHIFT F8`` / ``ALT F8``
     - Zoom precision up / down / query



Direction keys and ``SHIFT`` +direction keys move and turn in first person (see file comments).

5.6 Map browse
~~~~~~~~~~~~~~~


File: ``map_bindings.txt``

Movement and square jumps are global (section 4).

These keys cycle targets on the current square (no square change):


.. list-table::
   :header-rows: 1

   * - Key
     - Action
   * - ``f`` / ``r``
     - resource1 deposit (e.g. gold)
   * - ``g`` / ``t``
     - resource2 deposit (e.g. wood)
   * - ``y`` / ``h``
     - resource3 deposit (e.g. food)
   * - ``m`` / ``SHIFT m``
     - Meadow
   * - ``p`` / ``SHIFT p``
     - Passage / bridge
   * - ``F8`` series
     - Zoom



After selecting a deposit, use global ``BACKSPACE`` / ``RETURN`` to issue gather; meadow for build; passage for move/block.

5.7 Help and diplomacy
~~~~~~~~~~~~~~~~~~~~~~~


Help (`help_bindings.txt <../../../res/ui/help_bindings.txt>`_): ``1``/``2`` browse help, ``3`` say time, ``F7`` say, ``CTRL SHIFT F3`` toggle tick display.

Diplomacy (`diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_): ``1`` select candidate, ``q`` request, ``w`` accept, ``e`` decline/cancel.

``ESC`` in overlay modes calls ``exit_overlay_mode``.


----


6. Typical workflows
----------------------


Gathering
~~~~~~~~~~


1. Unit mode: ``s`` select peasant
2. ``F2`` command mode, ``s`` pick gather (or ``b`` + letter shortcut)
3. ``ESC`` map browse
4. ``f`` select gold mine (announced)
5. ``RETURN`` to confirm

If you already selected a mine and left map: ``ESC`` back announces square overview; focus stays on the mine — press ``RETURN`` directly.

Building
~~~~~~~~~


1. ``ESC`` map → ``m`` select meadow
2. ``F2`` pick build slot
3. ``RETURN`` confirm

Diplomacy
~~~~~~~~~~


1. ``F12`` diplomacy
2. `1` select candidate
3. ``q`` alliance request

.. code-block:: text

   sequenceDiagram
       participant U as UnitMode
       participant C as CommandMode
       participant M as MapMode
       U->>U: s select peasant
       U->>C: F2
       C->>C: s order slot 1
       C->>M: ESC
       M->>M: f select mine
       M->>C: RETURN validate



----


7. Customization for mods
---------------------------


Which file to edit
~~~~~~~~~~~~~~~~~~~


- Global behavior: ``global_bindings.txt``
- One interface: the matching `*_bindings.txt`
- Do not edit ``bindings.txt`` body (stub only) unless you understand legacy mod append behavior

User overrides
~~~~~~~~~~~~~~~


In-game mapping (recommended): Main menu → Options → Key mapping (sibling of Hotkey scheme). Supports layered and classic schemes, all layers, search, variants, alias keys, and clipboard import/export. Settings are stored per mod in ``user/hotkey_overrides/{mod_key}.json`` and apply at the next game. See `developer: hotkey mapping editor <../../mod/hotkey-mapping-editor.htm>`_.

Hotkey scheme: Options → Hotkey scheme switches layered/classic; moving the selection announces active or inactive for the current scheme.

Manual file: Append or override keys in ``cfg/bindings.txt``; loaded last (still appended after JSON-based overrides).

Notes
~~~~~~


- ``select_order_index`` slots depend on menu order
- ``buildingN`` slots need ``keyboard buildingN`` in ``style.txt``
- Unit ``b`` (``order_shortcut``) uses each order’s ``shortcut`` in style


----


8. Classic single-file hotkeys
--------------------------------


To restore the pre-1.4.3 binding set (F4 alliance request, F12 alliance candidate, ESC without map browse mode, etc.):

Option A (recommended): Main menu → Options → Hotkey scheme, then choose Layered hotkeys or Classic hotkeys.

Option B (edit ini manually):

1. Open :strong:```user/SoundRTS.ini`` (often `%APPDATA%\SoundRTS\SoundRTS.ini` on Windows).
2. Under `````[general]```, add or set:

.. code-block:: ini

      layered_hotkeys = 0


3. Restart the game (must be set before a match starts).

When disabled:

- Only `res/ui/legacy_bindings.txt <../../../res/ui/legacy_bindings.txt>`_ is loaded — no ``global_bindings.txt`` or per-mode layers.
- Mod non-stub ``bindings.txt`` and ``user/bindings.txt`` are still appended (user overrides win).
- F1/F2/F3/F4/F12/ESC mode-switch commands beep; ESC cancels orders / exits sub-screens / exits immersion or zoom, and does not enter map browse mode.
- Inventory (``i``), equipment (``u``), attributes (Alt+V), etc. follow ``legacy_bindings.txt``.

To re-enable layered mode: set ``layered_hotkeys = 1`` (or remove the line; default is 1) and restart.


----


9. Differences from the old scheme
------------------------------------



.. list-table::
   :header-rows: 1

   * - Old
     - New
   * - F1/F4 direct help
     - F4 enters help mode; F9/F11 globalized
   * - F12 direct diplomacy
     - F12 enters diplomacy mode first
   * - Worker ``d``/``e``
     - Unit mode ``s``/``w``
   * - Soldier keys
     - Remapped to `d/e`…`;`/p`
   * - Map ``f`` jumped squares
     - ``f`` cycles deposits on current square
   * - ESC to map announced last target
     - ESC announces square overview; focus restored silently



Attributes and editor bindings are unchanged.


----


Related source files
---------------------


- `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_
- `res/ui/unit_bindings.txt <../../../res/ui/unit_bindings.txt>`_
- `res/ui/building_bindings.txt <../../../res/ui/building_bindings.txt>`_
- `res/ui/command_bindings.txt <../../../res/ui/command_bindings.txt>`_
- `res/ui/skill_bindings.txt <../../../res/ui/skill_bindings.txt>`_
- `res/ui/map_bindings.txt <../../../res/ui/map_bindings.txt>`_
- `res/ui/help_bindings.txt <../../../res/ui/help_bindings.txt>`_
- `res/ui/diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_
- `soundrts/clientgame/interface_modes.py <../../../soundrts/clientgame/interface_modes.py>`_
