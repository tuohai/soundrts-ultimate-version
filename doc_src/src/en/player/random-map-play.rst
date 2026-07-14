Random map generator
=====================


Since SoundRTS 1.4.3.4, the procedural random map generator (RMG) builds standard ``.txt`` maps from menu options. Generated maps use the same load pipeline as hand-made maps and work in local skirmish or online room creation.


----


1. Where to find it
---------------------



.. list-table::
   :header-rows: 1

   * - Mode
     - Path
   * - Local skirmish
     - Main menu → Start a game → Random map (first item)
   * - Online host
     - Connect to server → Create game → pick Random map → speed → configure



After configuration, local play continues to invite-AI / faction / start; online play sends a ``create_random`` command and the host generates the map at game start.


----


2. Configuration flow
-----------------------


The submenu walks through ( Esc goes back one level ):

1. Map template (or Import share code — section 4)
2. Size: small / medium / large
3. Players: 2 / 3 / 4
4. Team mode (4 players only): free-for-all or fixed 2v2
5. Monster strength: weak / medium / strong (hostile center garrison; attacks players — weak: 2 footmen / medium: 4 footmen + 2 archers / strong: 6 footmen + 4 archers + 1 knight)
6. Resource layout: balanced / clustered
7. Terrain (not for lanes template): random / grass / marsh / mountain
8. Water (not for lanes): none / lake / river
9. Treasure: none / low / high (requires pickable ``class item`` types in rules)
10. Victory mode: conquest / economic / exploration / survival
11. Seed: random or custom number (0–99999)
12. Treaty: 0 / 5 / 10 / 15 / 20 minutes

After seed selection you hear a voice preview of the settings; after treaty confirmation the map is generated.

2.1 Templates
~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Template
     - Description
   * - Standard
     - Classic grid, random starts and bridges
   * - Fast
     - Higher starting resources, quicker games
   * - Macro
     - Higher pop cap and more meadows, economy-focused
   * - Lanes
     - Three-lane layout (TD2-style); no terrain/water steps



2.2 Teams 2v2
~~~~~~~~~~~~~~


With 4 players and 2v2, the map adds alliance triggers: players 1+2 and 3+4 start allied.

2.3 Victory modes
~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Mode
     - Win condition
     - Start objective (voice)
     - Notes
   * - Conquest
     - Eliminate all enemy players
     - Eliminate all enemy players
     - Default; no need to clear center creeps or barracks guards
   * - Economic
     - Total gold gathered reaches goal (excludes starting stock)
     - Gather N gold total
     - Spending gathered gold still counts; preview announces N; checked about every 60s
   * - Exploration
     - Your camp discovers all ancient ruins
     - Discover all ruins with your forces
     - 2v2 ally finds count; FFA enemy finds do not; reward still goes to first visitor
   * - Survival
     - Hold until timer with town hall intact
     - Hold N minutes while keeping town hall
     - 10 min fast, 15 min otherwise; lose base first = defeat; multiple winners allowed



Economic gold goals (``resource1`` only):


.. list-table::
   :header-rows: 1

   * - Template
     - Goal
   * - Fast
     - 2000
   * - Standard
     - 3000
   * - Macro
     - 5000
   * - Lanes
     - 2500



Losing all ``provides_survival`` buildings still means defeat. In exploration/economic/survival modes, wiping all enemies does not auto-win; you may still attack.

All modes also spawn ancient ruins (one-time resource reward on first visit) and capturable barracks (clear guards, capture, then train units).


----


3. Generation announcement and F5/F6
--------------------------------------


In local mode, when the map is ready the game announces:

- Map generated
- Seed (number for reproducing the same layout)
- Share code (full settings string)
- Press F5 to repeat (history hint)

The invite-AI menu that follows does not erase this: F5 repeats the previous message, F6 steps through voice history so you can review seed and share code anytime.

Menus support the same F5 / F6 history keys as in-game.


----


4. Share codes
----------------


4.1 Format
~~~~~~~~~~~


Example:

.. code-block:: text

   RMG1:f:m:2:med:b:r:f:v:hi:4242


Eleven colon-separated parts: ``RMG1`` prefix + 10 fields:


.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
     - Examples
   * - Template
     - standard / fast / macro / lanes
     - ``s`` / ``f`` / ``m`` / ``l``
   * - Size
     - small / medium / large
     - ``s`` / ``m`` / ``l``
   * - Players
     - 2–4
     - `2`
   * - Monsters
     - weak / medium / strong
     - ``w`` / ``med`` / ``s``
   * - Resources
     - balanced / clustered
     - ``b`` / ``c``
   * - Terrain
     - random / grass / marsh / mountain
     - ``r`` / ``g`` / ``a`` / ``t``
   * - Teams
     - ffa / teams_2v2
     - ``f`` / ``t``
   * - Water
     - none / lake / river
     - ``n`` / ``l`` / ``v``
   * - Treasure
     - none / low / high
     - ``n`` / ``lo`` / ``hi``
   * - Seed
     - 0 = random; >0 fixed
     - `4242`



Import accepts codes with or without the ``RMG1:`` prefix; ``/`` works as a separator instead of ``:``.

4.2 Import share code
~~~~~~~~~~~~~~~~~~~~~~


On the map template submenu, choose Import share code, type or paste the code, Enter to confirm, Esc to cancel.

The input box supports standard editing shortcuts (same as other ``input_string`` fields such as seed or login):


.. list-table::
   :header-rows: 1

   * - Shortcut
     - Action
   * - Ctrl+A
     - Select all
   * - Ctrl+C
     - Copy (all text if nothing selected)
   * - Ctrl+X
     - Cut
   * - Ctrl+V
     - Paste (invalid characters filtered out)
   * - Backspace / Delete
     - Delete selection or character before/after cursor



Max length 80; allowed characters: letters, digits, ``:``, ``/``, ``.``, ``-``.

On success you hear a preview and go straight to Treaty (skipping intermediate steps). Invalid codes show Invalid share code and return to the template menu.


----


5. Multiplayer notes
----------------------


- The host’s `create_random …` command is applied when the game starts; all clients get the same deterministic map from seed + settings.
- Clients do not hear the local “map generated + share code” announcement; share the code before hosting or have guests import the same code when creating a room.
- Public games and treaty minutes follow the usual speed / visibility submenus.


----


6. vs. `#random_choice` in map files
------------------------------------------


``#random_choice`` / ``#end_random_choice`` in a map file are preprocessor picks among fixed alternatives (e.g. random gold placement). That is not RMG.

RMG generates the whole map from parameters, with seeds and share codes for reproduction.


----


7. Source
-----------



.. list-table::
   :header-rows: 1

   * - Item
     - Path
   * - In-game docs
     - ``doc/en/randommap.htm`` (main menu → Documentation → Random map guide)
   * - Generator
     - ``soundrts/randommap.py``
   * - Menus
     - ``soundrts/randommap_menu.py``
   * - Tests
     - ``soundrts/tests/test_randommap.py``
   * - Chinese guide
     - [../../zh/player/随机地图功能说明.md](../../zh/player/随机地图功能说明.htm)

