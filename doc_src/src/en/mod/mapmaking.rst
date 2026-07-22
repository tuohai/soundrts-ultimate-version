Map making guide
=================

.. contents::

Introduction
-------------

The best way to start is probably to make a multiplayer map and test it against the computer.

Multiplayer maps
-----------------

Where to store a new multiplayer map
"""""""""""""""""""""""""""""""""""""

If you are allowed to write in the folder where SoundRTS (or SoundRTS test) is installed,
then you can store your first multiplayer map in the "multi" folder.

If you are not allowed to write in the program files folder because you work in non-admin mode, you can store your working map file in the "multi"
folder in "C:\\Documents and Settings\\Your Login\\Application Data\\SoundRTS". This folder is created the first time you start SoundRTS, unless a "user" folder exists near soundrts.exe.
Another solution is to install SoundRTS in a folder where you are allowed to write, and to work in the folder mentioned in the previous paragraph.

How to edit a map
""""""""""""""""""

Open the file with a text editor.
Write in lower case, even if case will be probably ignored anyway.

How to test a map
""""""""""""""""""

To test a map, start SoundRTS and go to the single player menu. You can play against the computer on multiplayer maps.
The map is reloaded each time you start a game, so you don't need to restart SoundRTS to test the modifications.
A useful key combination is Control Shift F2: if you are the only human on the map, you will be able to examine the whole map (no fog of war).

How to find and remove an error
""""""""""""""""""""""""""""""""

If, when you start the map, you get a "map error" message and go back to the menu, then you may sometimes find additional (but cryptic) information in "client.log" or in "server.log", usually in the "user/tmp" folder.

If you still don't understand where the error is, feel free to contact me, directly or at the soundRTSChat list.

Comments
"""""""""

The lines that start with a semicolon are comments. Comments are ignored at runtime.
Everything after a semicolon until the end of the line is a comment too.

Basic properties
"""""""""""""""""

Title
'''''

"title 4018 5000" means: "the title of the map is the sound 4018 followed by the sound 5000".

Objective
'''''''''

"objective 145 88" means: "the objective of the map is the sound 145 followed by the sound 88".

Nb_players_min and nb_players_max
'''''''''''''''''''''''''''''''''

"nb_players_min 2" means: "2 players are needed to start the game."
"nb_players_max 4" means: "4 players in this map is a maximum."

Global_food_limit
'''''''''''''''''

New in version beta 9e.

Update in version beta 10 o: this food limit is not divided among the players anymore.

"global_food_limit 200" means: "Every player cannot have more than 200 food, even if he builds more farms."

Defining the terrain
"""""""""""""""""""""

Coordinates (since 1.4.1.8)
'''''''''''''''''''''''''''''

The coordinate system uses ``x,y`` (e.g. ``1,1`` for the old ``a1``). In zoom mode, coordinates
are still announced with letters. Legacy notation is accepted and converted::

    west_east_paths 1,3 2,3
    south_north_paths 1,1 2,1 3,1

Use x,y notation to define more than 26 columns.

Square_width
''''''''''''

"square_width 12" means: "the square width is 12 meters".
You shouldn't modify this parameter, since objects may be inaudible if they are too far.

Since 1.4.5.8, ``square_width`` is also the capacity for unit ``space`` on each air/ground/water
layer (same units: ``space 1`` → at most 12 units when ``square_width`` is 12). See
``mod/modding.rst`` (Square occupancy).

Nb_lines and nb_columns
'''''''''''''''''''''''

"nb_lines 7" mean: "the grid has 7 lines".
"nb_columns 7" mean: "the grid has 7 columns".
Letter notation limits columns to 26 (``z``); use x,y coordinates for more columns. There is
no hard limit for lines, but performance sets a practical limit.
Warning: nb_rows is deprecated and has the same meaning as nb_columns.

West_east_paths and south_north_paths
'''''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" means: "add a path from a1 to b1, from c1 to d1, from d1 to e1, and from f1 to g1".
You only need to give the west-most square of the path.
"south_north_paths a1 a3 a4 a6" means:  "add a path from a1 to a2, from a3 to a4, from a4 to a5, and from a6 to a7".
You only need to give the south-most square of the path.

West_east_bridges and south_north_bridges
'''''''''''''''''''''''''''''''''''''''''

Bridges work exactly like paths.

General case: west_east and south_north
'''''''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" means: "add an exit with the 'road' style from a1 to b1, from c1 to d1, from d1 to e1"

'road' must be defined in style.txt

Note: "west_east_paths" is the same as "west_east path"

Note: "south_north_bridges" is the same as "south_north bridge"

Goldmines, woods, and other resource deposits
'''''''''''''''''''''''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" means: "add goldmines with 150 gold at a2, b7, g6 and f1".

"wood 150 a2 b7 g6 f1" means: "add woods with 150 wood at a2, b7, g6 and f1".

"goldmine" and "wood" are defined in rules.txt as resource deposits ("class deposit").

The old plural keywords ("goldmines" and "woods") are still working.

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" means: "auto fill the map with 2 meadows in each square".

Additional_meadows
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" means: "add 1 meadow in the squares a2, b7, g6 and f1".
"additional_meadows a2 a2 g6" means: "add 2 meadows in a2 and 1 meadow in g6".

Remove_meadows
''''''''''''''

remove_meadows do the opposite of additional_meadows.

Building_land (default build slot type)
'''''''''''''''''''''''''''''''''''''

Maps can choose which object type ``nb_meadows_by_square`` auto-fills::

    building_land build_site
    nb_meadows_by_square 2

- ``building_land meadow`` (default): auto-fill **meadow** slots.
- ``building_land build_site``: auto-fill **build_site** slots (theme-neutral, e.g. space mods).

``additional_meadows`` and ``additional_build_sites`` still place those types explicitly;
``remove_meadows`` only removes ``meadow`` objects.

Nb_<type>_by_square (building_land types from rules)
'''''''''''''''''''''''''''''''''''''''''''''''''''''

Map keyword pattern: ``nb_<type>_by_square <count>``, where ``<type>`` is the ``def`` name
of any object with ``class building_land`` in ``rules.txt``::

    nb_build_site_by_square 1
    nb_meadow_by_square 2
    nb_volcanic_rock_by_square 1

- Fills **every square** with that many objects of the given type.
- Types come from rules (mods can add ``def volcanic_rock`` + ``class building_land`` and use
  ``nb_volcanic_rock_by_square``; Unicode names such as ``nb_火山岩石_by_square`` work if defined in rules).
- Independent of the map ``building_land`` line.
- Can coexist with ``nb_meadows_by_square``; usually use one or the other.

Legacy ``nb_meadows_by_square`` remains: the name is historical; the actual type is controlled
by ``building_land`` (default ``meadow``), not by parsing ``meadow`` from the keyword.

If the map omits ``building_land`` and uses only one ``nb_<type>_by_square`` keyword, that type becomes ``world.building_land`` for the match.

When lift-off or some upgrades restore building land in place, the engine uses **the type saved when the building was placed** first; only if missing, it falls back to the map default above.

Additional_build_sites
''''''''''''''''''''''

::

    additional_build_sites a2 b7

adds one **build_site** per listed square (independent of ``building_land``).

See ``building-land-terrain.htm`` for terrain, building land, and related examples.

High_grounds
''''''''''''

New in SoundRTS 1.2 alpha 9.

"high_grounds a2 b7" means: "a2 and b7 will have a higher altitude"

Sub-cell terrain (since 1.4.4.8)
'''''''''''''''''''''''''''''''''

Terrain can also be overridden inside a square. Add ``/x,y`` after the square
coordinate, where ``x`` and ``y`` are 1-based coordinates inside the square::

    high_grounds a1/1,1 a1/1,2
    terrain mountain a1/2,2
    ground a1/2,2
    no_air a1/2,2

The sub-cell grid is controlled by ``subcell_precision``. It defaults to ``3``,
so ``a1/1,1`` means the north-west sub-cell of a 3x3 subdivision. The accepted
range is 2 to 20::

    subcell_precision 20
    high_grounds a1/10,10 a1/10,11
    terrain mountain a1/1,1 a1/2,2 a1/3,3

The following terrain commands accept sub-cell coordinates: ``terrain``,
``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` and ``no_air``.
Sub-cells not mentioned inherit the terrain of their parent square.

In zoom mode, the map browser announces the terrain of the current sub-cell. If
``a1/1,1`` is high ground and the rest of ``a1`` is low ground, browsing that
sub-cell will announce plateau, while the other sub-cells will not.

Square_name (since 1.4.1.8)
'''''''''''''''''''''''''''''

Name squares or regions::

    square_name normandy 2,2 verdun 20,23
    square_name normandy 2,2 2,3 3,3

Since 1.4.1.9, up to three hierarchy levels are supported (province, city, district). TTS
announces names when entering from another region; inner levels are omitted while browsing
inside the same region. Translate names in ``tts.txt``::

    normandy = Normandy

Map music and sounds (since 1.4.0.2)
''''''''''''''''''''''''''''''''''''''

In the map file::

    map_music <id>
    map_battle_music <id>
    map_victory_sound <id>
    map_defeat_sound <id>


Defining the starting resources of the players
"""""""""""""""""""""""""""""""""""""""""""""""

Note (since 1.4.1.8): faction starting units and resources can also be defined in
``rules.txt``. Map definitions take priority when both are set.

Case 1: same resources for everybody
''''''''''''''''''''''''''''''''''''

Use the following commands in combination:

starting_resources
..................

"starting_resources 10 10" means: "each player starts with 10 gold and 10 wood."

starting_units
..............

"starting_units townhall farm peasant" means: "each player starts with 1 townhall, 1 farm and 1 peasant."

"starting_units townhall 2 farm peasant" means: "each player starts with 1 townhall, 2 farms and 1 peasant."

starting_population
...................

"starting_population 60" means: "each player gets 60 extra population cap on top of
what their starting buildings provide." This is a plain integer (not multiplied like
resources). Per-player ``player`` / ``computer_only`` lines can also include
``population 60`` among the unit tokens for that slot only. ``available_population``
is still limited by ``global_population_limit``.

Since SoundRTS 1.1, starting_units can also contain:

- upgrades and research: "starting_units u_teleportation" means: "each player has teleportation already researched."
- forbidden units, buildings, abilities, upgrades/research (they won't appear on the menu):

  - "starting_units -u_teleportation" means: "each player cannot research teleportation."
  - "starting_units -a_teleportation" means: "each player cannot use teleportation."

starting_squares
................

"starting_squares a2 b7 g6 f1" means: "the starting squares of the players are a2, b7, g6 and f1."

The starting units and buildings will be created in these squares.

``starting_squares`` only fixes which squares each spawn slot uses; by default it does not fix which joining human gets which slot (see random_starts_ and player_start_).

.. _random_starts:

random_starts
.............

``random_starts 1`` (default): spawn slots are shuffled among human clients at game start. Unit positions inside each slot stay the same, but slot assignment is random.

``random_starts 0``: slots are assigned in order to clients 0, 1, 2…; the first joiner always gets the first slot.

.. _player_start:

player_start (since 1.4.2.8)
............................

Pin player N (1-based, same as ``trigger playerN``) to a slot/square. Pinned players never participate in ``random_starts`` shuffling; others still follow ``random_starts``.

Simple form — change the square only, keep that slot's existing resources and units::

    starting_squares a1 c1 e1
    starting_units townhall peasant
    player_start 1 b1

Full form — equivalent to pinning a full ``player`` line to player N::

    player_start 1 5 10 a1 townhall peasant

Coordinates and aliases are also supported::

    player_start 1 2,3
    player_start 2 5,1

.. _spawn_semantics:

Spawn semantics: player vs player_start
'''''''''''''''''''''''''''''''''''''''''

Both can place units/buildings on specific squares (e.g. ``a1``), but they do not mean the same kind of "fixed spawn":

- ``player`` / ``starting_squares``: define spawn slots and their contents. Square coordinates are fixed, but with ``random_starts 1`` which human gets which slot is shuffled.
- ``player_start``: pins player N to slot N (and can change that slot's square), regardless of ``random_starts``.

Common patterns:

Different per-player setups, and player 1 must always start bottom-left :

    random_starts 1
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant
    player_start 1 a1
    player_start 2 h1

player lines only, fixed by join order (no player_start needed) :

    random_starts 0
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant

Shared starting setup, only some players pinned :

    starting_squares a1 c1 e1 g1
    starting_units townhall peasant
    player_start 1 a1
    player_start 3 e1

Common pitfalls:

- In ``player 5 10 …``, the first two numbers are resource amounts (gold/wood), not a player index or coordinates.
- To pin "which joiner gets which corner", use ``player_start`` or ``random_starts 0``; ``starting_squares`` / ``player`` alone is not enough.

Case 2: different resources depending on the player
'''''''''''''''''''''''''''''''''''''''''''''''''''

player
......

The "player" command defines a starting point that might be used by a human player or by a computer AI (in multiplayer games).

This command can be repeated several times in a multiplayer map.

"player 5 10 -townhall a1 townhall peasant c1 footman"
means: "a player will start with 5 gold, 10 wood, won't be allowed to build a town hall, will have a townhall and a peasant at A1, a footman at C1.

Each ``player`` line appends one spawn slot in map order; ``a1``, ``c1``, etc. are square coordinates. To pin a slot to player N, use player_start_ or set random_starts 0 (see spawn_semantics_ above).


Types list
''''''''''

Here are some correct names for types used in starting_units_, player_ and computer_only_ .
For a full list, examine the rules.txt file: the name is just after the "def" statement.

- units: peasant footman archer knight catapult dragon mage priest necromancer
- buildings: farm barracks lumbermill blacksmith townhall stables workshop dragonslair magestower
- abilities: a_teleportation
- upgrade/research: u_teleportation melee_weapon


Adding monsters
""""""""""""""""

Add a computer_only starting point
''''''''''''''''''''''''''''''''''

.. _computer_only:

The "computer_only" command defines a starting point that will always be played by a computer AI. This AI will be hostile to any other player or AI.

This command can be repeated several times but be careful: too many AI can slow the game.
So use one AI if these units are not supposed to fight each other (several dragons all over the map for example).

computer_only 0 0 a3 dragon b1 dragon
means: "add a computer AI with 0 gold, 0 wood, a dragon at A3 and a dragon at B1."

Neutral computers (since 1.4.2.8)
..................................

Add the ``neutral`` keyword so the AI does not attack unless attacked first::

    computer_only 0 0 neutral a3 peasant b1 footman

Without ``neutral``, the computer is hostile to everyone.

Player units in offensive, defensive, or chase mode will not auto-attack these neutrals and
will not flee from them in defensive mode; only a forced attack (imperative) starts combat.

Wildlife-only slots (since 1.4.3.7)
.....................................

If a ``computer_only`` line contains only animals with ``is_huntable`` / ``herdable`` (e.g. ``deer``, ``sheep``, custom ``tiger``), that slot does not join the default ``"ai"`` alliance and does not ally with other herds, players, or hostile creep. Each ``computer_only`` line is one independent hunting spot.

If the same line mixes animals and footmen, the whole slot stays a normal AI. See ``../player/hunting.htm`` §3.1.


Add triggers to make the monsters move
''''''''''''''''''''''''''''''''''''''

Important: add the default multiplayer triggers
...............................................

If a multiplayer map defines at least one trigger, the default multiplayer triggers are ignored. The goal is to allow custom victory conditions.

To keep the default victory conditions, the following triggers must be explicitly added to the map (or the game won't stop automatically)::

    trigger players (no_enemy_player_left) (victory)
    trigger players (no_building_left) (defeat)
    trigger computers (no_unit_left) (defeat)

Note: the third trigger is not really needed.

Victory and defeat conditions (since 1.4.0.1)
.............................................

Additional trigger conditions::

    trigger all (unit_lost knight) (defeat)
    trigger player1 (unit_lost a1 3 footman) (defeat)
    trigger player1 (building_lost 1 townhall) (defeat)
    trigger player1 (key_unit_killed a1 3 footman) (defeat)
    trigger all (key_unit_killed hero) (defeat)
    trigger all (key_units_killed 5 knight) (defeat)
    trigger all (units_lost 3 knight) (defeat)
    trigger all (building_lost townhall) (defeat)
    trigger all (buildings_lost 1 townhall 2 barracks) (defeat)
    trigger players (killed_target dragon) (victory)
    trigger players (killed_target dragon enemy) (victory)
    trigger player1 (has_killed 5 footman enemy) (objective_complete 1)
    trigger player1 (has_killed 1 footman 3 knight enemy) (objective_complete 2)

``killed_target`` and ``has_killed`` accept optional ``enemy`` or ``ally`` to count only
those units.

Unit index selectors (since 1.4.3.1, demo: The Legend of Raynor chapter 28) — same
``\<square\> \<index\> \<type\>`` syntax as ``transfer_units``; identifies the Nth unit of
that type spawned at the square (stable after movement)::

    trigger player1 (killed_target c3 3 demo_marker_footman enemy) (objective_complete 1)
    trigger player1 (killed_target c3 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

``killed_target`` index: `` (killed_target \<square\> \<index\> \<type\> [enemy|ally])``.
``npc_has_item`` index: `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``.
``unit_lost`` / ``building_lost`` / ``key_unit_killed`` index: `` (\<square\> \<index\> \<type\>)`` — only that spawned unit/building (e.g. protect starting town hall).
Not the same as ``has_killed 3 footman`` (total count). Each objective's ``cut_scene`` should
describe that objective only. See ``campaign/unit-index.htm``; examples
``res/single/The Legend of Raynor/28.txt``, ``1.txt``.

Item quest triggers (since 1.4.3.1)
.....................................

has_item — player picked up a quest item (checks all living units' inventories)::

    trigger player1 (has_item lost_amulet) (objective_complete 1)
    trigger player1 (has_item health_potion 2) (objective_complete 2)

The item must be ``class item`` with ``consume_on_pickup`` not set to 1 (default 0), so it
stays in inventory after pickup. Place items on the map like units::

    lost_amulet c3
    health_potion 2 a2

Differences between related conditions:

- ``has``: player unit counts (``self.units``)
- ``has_item``: items in player units' inventories (found/picked up anywhere)
- ``npc_has_item``: an NPC received an item (inventory or ``received_items``); index form ``\<square\> \<index\> \<type\> \<item\>`` (chapter 28)
- ``find``: object exists on the ground at a square (square before type, e.g. ``c3 mana_potion``); item must usually be dropped
- ``has_brought_item``: player unit carrying an item arrived at a square (item stays in inventory)
- ``remove_item``: trigger action that deletes an item from player inventories (story hand-over)
- ``remove_ground_item``: trigger action that deletes items on the ground at a square
- ``do``: trigger action that runs multiple sub-actions in order
- ``and``: trigger condition that is true only when every sub-condition is true

has_brought_item — carry a quest item to a square (inventory counts; no drop required)::

    trigger player1 (has_brought_item c3 mana_potion) (objective_complete 1)

Syntax: ``(has_brought_item \<square\> \<item_type_name\> [count])``

remove_item — remove and destroy items from player inventories (story delivery)::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Syntax: ``(remove_item \<item_type_name\> [square] [count])``

Typical flow: ``has_brought_item`` → ``cut_scene`` → ``remove_item`` → ``objective_complete``.
Example: The Legend of Raynor chapter 18.

do — run multiple trigger actions in order::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Syntax: ``(do \<action1\> \<action2\> ...)``

``if`` has only two branches (if/else). Use ``do`` when you need three or more actions
(cut scene, remove item, complete objective, etc.).

remove_ground_item — delete items on the ground at a square::

    trigger player1 (find b2 mystery_treasure)
        (do (cut_scene 7546) (remove_ground_item b2 mystery_treasure)
            (add_units b2 10 gold_coin) (objective_complete 2))

Syntax: ``(remove_ground_item \<square\> \<item_type_name\> [count])``

``remove_item`` removes from player inventories; ``remove_ground_item`` removes from
the ground at a square (e.g. after the player drops a quest item to open a chest).

and — all sub-conditions must be true::

    trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin)))
        (objective_complete 3)

Syntax: ``(and \<condition1\> \<condition2\> ...)``

A trigger line has one condition expression. Wrap multiple conditions in ``and``; do not
write ``(cond1) (cond2) (action)`` (the second S-expression becomes the action).

For ``find``, always put the square before the type, including inside ``not``.
Wrong: ``(not (find gold_coin b2))`` (checks the default square first, almost always true).
Right: ``(not (find b2 gold_coin))``. Drop-to-open example: The Legend of Raynor chapter 22; inventory use: chapter 20.

npc_has_item — an NPC received a specific item (inventory or ``received_items`` record)::

    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Syntax (either form):

- Classic: ``(npc_has_item \<NPC_selector\> \<item_type_name\> [square])``
- Index: ``(npc_has_item \<square\> \<index\> \<unit_type\> \<item_type_name\>)`` — same as
  ``transfer_units``; the Nth unit at that square by spawn order. Example: chapter 28.

Classic form:

- ``\<NPC_selector\>``: unit ``type_name`` or unit id.
- ``\<item_type_name\>``: e.g. ``health_potion``.
- Optional `````[square]```: limits to NPCs currently at that square.

Index form matches by spawn index; the unit may have moved away from that square.

give in trigger orders (scripted delivery)::

    trigger player1 (timer 5) (order (a1 1 peasant) ((give c3 health_potion)))

Example find-item map (The Legend of Raynor chapter 17)::

    title Find the lost amulet
    lost_amulet c3
    starting_squares a1
    starting_units peasant
    trigger player1 (timer 0) (add_objective 1 "find the lost amulet")
    trigger player1 (has_item lost_amulet) (objective_complete 1)

Example give-to-NPC map (``res/multi/give_demo.txt``)::

    health_potion a1
    computer_only 0 0 neutral c3 quest_npc
    trigger player1 (timer 0) (add_objective 1 "deliver the potion to the quest npc")
    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)

Campaign examples (``The Legend of Raynor``): ch. 14 deliver ``pickaxe`` to allied ``npc_peasant``;
ch. 15 deliver ``knight_lance`` to neutral ``npc_knight``; ch. 16 deliver ``wand`` to enemy
``npc_mage`` (``ally``/``neutral``/``enemy`` relations). See ``res/single/The Legend of Raynor/14.txt``,
``15.txt``, ``16.txt``. Multiplayer demo: ``res/multi/give_demo.txt``.

Campaign alliance and unit transfer (since 1.4.3.1)
.....................................................

F12 dynamic diplomacy does not work in campaigns. After ``alliance_request``, the human
accepts with Ctrl+F4 and declines with Shift+F4 (no F12 target selection). See
``../player/campaign-northern-arc.htm`` for the full northern arc (ch. 24–27).

alliance_request — trigger action: one player requests alliance with another::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (cut_scene 7585) (alliance_request computer1) (objective_complete 1))

Syntax: ``(alliance_request \<from\> [to])``; if ``to`` is omitted, the request goes to the
trigger owner.

alliance_with — condition: trigger owner is allied with the given player::

    trigger player1 (alliance_with computer1) (objective_complete 2)

alliance_declined_with — condition: declined alliance request from the given player (campaign Shift+F4)::

    trigger player1 (alliance_declined_with computer1)
        (do (cut_scene 7598) (add_units c3 3 knight) (objective_abandon 1))

add_secondary_objective — trigger action: add an optional objective (announced with the
"optional objective" prefix). Numbering is independent from primary objectives (both start at 1)::

    trigger player1 (timer 0) (add_objective 1 7583)
    trigger player1 (timer 0) (add_objective 2 7584)
    trigger player1 (timer 0) (add_secondary_objective 1 7599)

secondary_objective_complete — trigger action: complete optional objective N (does not
affect primary objective N)::

    trigger player1 (alliance_with computer1)
        (do (cut_scene 7586) (allied_assist computer1) (secondary_objective_complete 1))

objective_abandon — trigger action: abandon optional objective N (e.g. decline alliance);
only applies to ``add_secondary_objective``.

alliance_request_pending — condition: a pending alliance request from the given player.

transfer_units / convert_units / change_owner — trigger action: change unit
ownership from one player to another (not ``add_units`` spawning)::

    trigger player1 (alliance_with computer1)
        (do (transfer_units computer1 player1) (add_objective 2 7584))

With no unit selector, all living units of the source player are transferred.
Selector syntax matches ``order`` / ``add_units``: ``\<square\> \<count\> \<type\>``.

allied_assist — trigger action: let ally units fight on their own (guard→chase); does not
grant player command::

    trigger player1 (alliance_with computer1)
        (do (allied_assist computer1))

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (allied_assist computer1 c2 4 npc_archer_escort))

Syntax:

- Whole ally: ``(allied_assist \<ally\>)``
- Selected units only: ``(allied_assist \<ally\> \<square\> \<count\> \<type\> ...)``

Unit selector syntax matches ``transfer_units`` / ``add_units``. With no selector, all combat
units on guard switch to chase; with a selector, only matching units switch; the rest are
unchanged.

allied_control — trigger action: let a player directly command an ally's units
(select, move, attack)::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (alliance 1) (allied_control computer1 c2 4 npc_knight_escort))

Syntax:

- Whole ally: ``(allied_control \<ally\> [controller])``
- Selected units only: ``(allied_control \<ally\> [\<controller\>] \<square\> \<count\> \<type\> ...)``

With no selector, all living units of the ally are granted and switch to chase. With a selector,
only matching units are granted (they stay on guard until the player orders); unmatched combat
units on guard switch to chase automatically.

add_inventory_item — put an item into a unit's inventory (quest reward, cross-chapter re-grant)::

    trigger player1 (has_killed 3 traitor_guard)
        (do (cut_scene 7580) (add_inventory_item garrek_token 1 raynor) (set_campaign_flag ch24_garrek_token))

Syntax: ``(add_inventory_item \<item_type\> [\<count\>] [\<unit_type\>])``; if unit omitted, first friendly unit with ``inventory_capacity`` (Raynor campaign defaults to ``raynor`` types).

Cross-chapter progress (three mechanisms)
.........................................

.. list-table::
   :header-rows: 1

   * - Mechanism
     - Config
     - Carries
   * - ``campaign_carryover``
     - ``rules.txt`` unit fields
     - Level+XP, inventory
   * - 
     - 
     - (split; see modding.rst)
   * - ``campaign_flag`` /
     - map triggers
     - story booleans
   * - ``set_campaign_flag``
     - 
     - 
   * - ``add_inventory_item``
     - map triggers
     - specific items


``campaign_flag`` persists in ``campaigns.ini`` ``flags``; ``map_flag`` is per map only.

Re-grant at chapter start::

    trigger player1 (timer 0) (if (campaign_flag ch24_garrek_token) (do (add_inventory_item garrek_token 1 raynor)))

unset_campaign_flag clears mistakenly persisted flags.

set_ai_mode — change AI mode on the trigger owner's units::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Syntax: ``(set_ai_mode \<offensive|defensive|guard|chase\> [\<square\> \<count\> \<type\> ...])``.

set_yield_on_defeat — toggle per-unit yield (zero HP → yield instead of die)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Syntax: ``(set_yield_on_defeat \<0|1\> [\<square\> \<count\> \<type\> ...])``. Can also set ``yield_on_defeat 1`` in ``rules.txt``.

units_yielded — count of yielded enemy units::

    trigger player1 (units_yielded 1 npc_marco_ironhand) (objective_complete 1)

units_yielded_by — yield forced by a specific attacker (supports ``is_a``)::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy) (objective_complete 1)

has_entered — trigger owner's units entered a square (grid or place-name alias; optional unit type)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

map_flag / set_map_flag — per-map session flags (not saved in campaign config)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

stop_all_units / release_yielded_units — cease fire and end yield invulnerability::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy)
        (do (cut_scene 7710) (alliance 1 player1 computer1) (stop_all_units) (release_yielded_units computer1))

Run ``cut_scene`` on player1 triggers so the human client hears voice. AI mode / yield toggles may run on computer1 (unit owner).

The Legend of Raynor northern arc (ch. 24–27): continuous storyline with shared ``traitor_guard`` objective and ``campaign_flag`` carryover. See ``../player/campaign-northern-arc.htm``:

- ch. 24 (letter to Garrek): ``allied_control``; ``add_inventory_item garrek_token`` after traitors die
- ch. 25 (token to Roland): killable before delivery; then ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``
- ch. 26 (banner to Vera): ``transfer_units``
- ch. 27 (duel with Marco): ``has_entered c2 raynor7`` + cutscene 7718; Marco-only ``set_ai_mode offensive``; escorts ``order`` to ``c1`` to clear the arena; ``units_yielded_by raynor7``; ``stop_all_units`` + selective ``allied_control`` (4 escort knights)

Chapter 25 must register three primary objectives (deliver token, defeat Roland, kill traitors) plus optional objective 1 (alliance) at start. Press F9 for primary and optional objectives. Script computers display as NPC (``Player.name`` + ``is_script_npc``).

Key NPCs (``npc_count_roland``, ``npc_roland_guard``, etc.) should start on ``ai_mode guard``. Enable ``yield_on_defeat`` at runtime via ``set_yield_on_defeat``, not in rules at spawn, so Roland is killable before the token is delivered.


Patrol
......

To order up to 10 dragons from d1 to patrol between d1 and d9::

    trigger computer1 (timer 0) (order (d1 10 dragon) ((patrol d9)))


Attack at a specific moment
...........................

To order up to 10 dragons from e3 to attack b2 after 20 minutes (normal speed)::

    timer_coefficient 60
    trigger computer1 (timer 20) (order (e3 10 dragon) ((go b2)))


Switch to another AI
....................

The default AI for computer_only is a trigger-only, do-nothing AI. To switch to "easy" (also known as "quiet computer")::

    trigger computer1 (timer 0) (ai easy)


Add units
.........

To add 10 dragons at A1::

    trigger computer1 (timer 0) (add_units a1 10 dragon)


#random_choice,  #end_choice and #end_random_choice
""""""""""""""""""""""""""""""""""""""""""""""""""""
(new in beta 9g)
This preprocessor directive chooses randomly between 2 or more choices delimited by #random_choice,  #end_choice and by #end_random_choice for the last choice.
Each choice consists in zero or more lines.
More than one #random_choice directives can be used in a map file, but they cannot be nested.

This can be used for example to place random resources. For example::

 #random_choice
 goldmines 500 e2 c6 b3 f5
 #end_choice
 goldmines 500 d2 d6 b4 f4
 #end_choice
 goldmines 500 c2 e6 b5 f3
 #end_random_choice

The preceding lines mean: "add a goldmine at e2, c6, b3 and f5, or at d2, d6, b4 and f4, or at c2, e6, b5 and f3". This way, the resources are balanced (if I didn't make a mistake of course). This is only an example.

The title of the map and the number of players cannot be changed this way because the preprocessor is run when the map is loaded (that is to say: long after the single player menu is loaded).

Advanced multiplayer maps: how to change the rules and the aspect of the game
------------------------------------------------------------------------------

Map structure
""""""""""""""

The advanced map is a folder containing a file called "map.txt" with the content of a usual map, and most files and folders that you find in the "res" folder:
rules.txt, ai.txt, the ui folders and their content.

Note: at the moment, in a map or a campaign folder, the localized version of style.txt (for example: ui-fr/style.txt) isn't loaded.
Localized sounds are loaded though.

Single player campaigns
------------------------

Where to store a new single player campaign
""""""""""""""""""""""""""""""""""""""""""""

If you are allowed to write in the folder where SoundRTS (or SoundRTS test) is installed, then you can store your first campaign in the "single" folder.

If you are not allowed to write in the program files folder because you work in non-admin mode, you can store your working map file in the "single"
folder in "C:\\Documents and Settings\\Your Login\\Application Data\\SoundRTS". This folder is created the first time you start SoundRTS.
Another solution is to install SoundRTS in a folder where you are allowed to write, and to work in the folder mentioned in the previous paragraph.

Structure of the campaign folder
"""""""""""""""""""""""""""""""""

The name of the campaign folder will be used by the single player menu. Official campaigns will have their own title in the "ui" folder.
The folder contains chapter files. It also contains files and folders imitating the structure of the "res" folder: rules.txt, ai.txt, ui...

Required mods file
''''''''''''''''''

New in SoundRTS 1.2 alpha 10.

A campaign can define which mods it requires. The required mods will be automatically loaded.

The required mods are defined in a file called "mods.txt", in the campaign folder:

- the file is a comma-separated list of mod names;
- if the file doesn't exist, the current mods will be kept;
- if the file is empty, the "vanilla" game will be loaded.

Chapter files
'''''''''''''

Chapter files are text files called "0.txt", "1.txt", "2.txt", etc. When a campaign is started for the first time, only the chapter 0 is available. When a chapter is finished, the next chapter can be run. The number of the higher chapter available is automatically stored in the player's configuration file called campaigns.ini.

A chapter file describes a mission chapter or a cut scene chapter.

There must be at least one chapter file, called "0.txt".

Syntax of a chapter file
"""""""""""""""""""""""""

A chapter is a mission or a cut scene.

Syntax of a mission chapter file
''''''''''''''''''''''''''''''''
A mission file is not very different from a multiplayer map.
The advanced map structure is also allowed: in that case, the folder name is the number of the chapter.

Cooperative campaign (since 1.4.2.2; AoE DE-style since 1.4.4.4+): declare
``coop_campaign`` / ``coop_intro`` / ``coop_missions`` in ``campaign.txt``;
optional ``hero_min_level 13:2 16:3 …`` (cross-chapter hero floor levels; see ``modding.rst``);
single-player and co-op load the same ``N.txt`` mission map (do not ship
``N.coop.txt``). See ``mod/coop-campaign.htm`` and
``player/campaign-and-co-op-improvements.htm``.

Co-op missions set ``nb_players_min`` / ``nb_players_max`` and multiple ``player``
blocks in ``N.txt``; on a server, any player completing objectives contributes
to the team. Single-player still registers one human and uses only the first spawn.

In campaigns, F12 (dynamic alliance) does not select any target. Trigger-script computers are
announced as "NPC" instead of internal names like ``ai_timers``.

Intro
.....

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

Example: "intro 7500 7501 7502" means: "before the game starts, play 7500.ogg, 7501.ogg and 7502.ogg (or text if defined in tts.txt)".
The intro command defines a sequence of sounds and texts that will be played before the game starts. When the player presses a key, the next element in the sequence is played. An intro can be for example a title with music, then a scene with a discussion between characters, then a briefing. After the intro, the game will tell the objectives of the mission.

Add_objective
.............

"add_objective player1 1 7000" means: "add primary objective number 1 with the sound 7000.ogg"

"add_secondary_objective player1 1 7599" means: "add optional objective number 1" (mission
can be won without completing it). Primary and optional objectives use independent numbering
(both can start at 1; primary 1 and optional 1 can coexist).

All primary objectives must be completed to win. Use ``secondary_objective_complete`` to
mark an optional objective done, or ``objective_abandon`` to drop it. If a primary objective
fails (e.g. an important character dies), the mission is lost.

Register_objective (action in a trigger)
........................................

``register_objective`` registers primary objective numbers required for victory without
showing them in the F9 list or playing the "new objective" voice.

Syntax (inside a trigger action)::

    register_objective 1 2 3

Why use it: if you chain ``add_objective`` across several triggers (reveal goal 2 only
after goal 1 completes), each ``add_objective`` also adds that number to the victory set.
Completing objective 1 could otherwise trigger premature victory when goals 2–N are not
added yet.

Progressive reveal pattern — at ``timer 0``, register all numbers, then show only the first
objective; on each completion, ``objective_complete`` + ``add_objective`` for the next::

    trigger player1 (timer 0) (do (register_objective 1 2) (add_objective 1 7510))
    trigger player1 (has 4 pylon) (do (objective_complete 1) (add_objective 2 7511))
    trigger player1 (has_entered f1 gateway) (objective_complete 2)

Victory logic: the engine keeps ``\_required_objective_numbers`` (from ``register_objective``
and ``add_objective``) and ``\_completed_objective_numbers`` (from ``objective_complete``).
Mission victory runs when every required number is completed — independent of whether a goal
is still visible in F9.

F9 / voice numbering: when several primary objectives exist (registered or already shown),
F9 and ``add_objective`` announce "Primary objective N:" before the description; with a
single primary objective the number is omitted. See ``soundrts/objective_announce.py``.

Examples: ``mods/starcraft/single/sc_build_tests/1.txt`` (2 goals); ``sc_late_game/1.txt`` (6
chained goals). Guide: ``campaign/progressive-objectives.htm``.

Objective_complete (action in a trigger)
........................................

This action can only be included in the action part of a trigger.

"objective_complete 1" means: "primary objective 1 is now complete".

Secondary_objective_complete (action in a trigger)
..................................................

``objective_complete 1`` only affects primary objectives. To complete an optional objective, use::

    secondary_objective_complete 1

which means: "optional objective 1 is now complete".

Trigger example:

"trigger player1 (has barracks) (objective_complete 2)" means: "add the following trigger for player1: if he has at least 1 barracks then the objective 2 is completed"

Timer coefficiency
..................

A timer coefficient can be used to measure time for triggers in a given block. 

For example, if you know that you want all of your triggers to happen in given half a minute blocks, you could set your timer coefficient to 30 like so.

"timer_coefficient 30"

Whenever this amount of time elapses, the timer counter will increment (increase by 1). You can then bind triggers to the timer reaching a given number. For example, if you wanted to make reinforcements appear on the map after 90 seconds (3 increments of 30 seconds), you would do the following. 

"trigger player1 (timer 3) (add_units a1 10 footman)" ; after three timer ticks, give the player 10 footman at a1

Cut_scene (action in a trigger)
...............................

Note: the distinction between streaming sounds and preloaded sounds have been removed in SoundRTS 1.2. All the sounds are loaded in advance.

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

A cut scene can be triggered in the middle of a game: when something is discovered, when reinforcements arrive, etc.

"cut_scene 7500 7501" means: play the cut scene made up of the sounds 7500 and 7501.

Trigger example:

"trigger player1 (has_entered d5) (cut_scene 7500)" means: "add the following trigger for player1: if he has entered the square d5, then play the cut scene made up of the sound 7500.ogg"

Timer and timer_coefficient (condition in a trigger)

"timer_coefficient 60"

'trigger player1 (timer 2) (cut_scene 7500)" means: "after 2 minutes (2 x 60 seconds) play the 7500.ogg sound file."

AI orders
..........

It is possible to control the computer's actions in a mission, to add some challenge. You will have to do this by directly making their units take orders at given triggers. 

For example, we can make the AI forces at A1 move to the known player location at A3, who will engage player forces as they encounter them. Here, we will launch an attack with 10 footman on the player.

"timer_coefficient 60"

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1)))"

The placement of brackets is important here, to encapsulate the right commands in the right parts of this trigger. If for some reason your trigger isn't seeming to work, try double checking your brackets.

It is also possible to queue up orders for the given units to follow. In this next scenario, lets imagine the player has their base spread over a1 and b1. We would then need to tell the footmen to go to b1 once they've finished with a1. We would do that like so. 

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1)))"

Finally, if you want the AI units to go into "auto_attack" mode, where they will hunt down any surviving player units after mopping up their base, you can do this as well. 

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1) (auto_attack)))"

You can use orders to make the computer train up its own units, too, which you can then make the subject of later orders. Here, we will tell the computer barracks to immediately train up another 10 footmen to replace the ones we're about to send to attack the player. 

trigger computer1 (timer 0) (order (a1 barracks) ((train footman) (train footman) (train footman))) ; and so on and so on until you have 10 train footman orders

Note that each training order has to be separate, you cannot do the following: (train 10 footman)

This is not the only way to increase the amount of units the computer player has at its disposal, you could also use the add_units order as shown here.

trigger computer1 (timer 0) (add_units a1 10 footman)

However, this is immediate and doesn't offer the player any way to influence this event. In the other scenario, the player can stop the computer having its next batch of footmen by destroying the barracks used to train them. This way, these footmen will appear regardless.

Syntax of a cut scene chapter file
''''''''''''''''''''''''''''''''''

Note: the distinction between streaming sounds and preloaded sounds have been removed in SoundRTS 1.2. All the sounds are loaded in advance.

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

A cut scene chapter is an interruptible sequence of sounds. When the cut scene chapter has been played, the next chapter is unlocked.
Do not confuse with shorter cut scenes run by a trigger during a mission when a condition is met (discovery of a square for example), or with the mission's introduction (or briefing).

The cut scene chapters have only 3 lines. For example:
cut_scene_chapter
title 7000
sequence 7500 7501 7502

The first line is a keyword used to tell the game that this chapter is a cut scene and not a mission.
The title line is used in the campaign menu.
The sequence line means: "play the sound 7500.ogg followed by 7501 and 7502; if the player presses a key, skip the current sound and play the next one." 

Map editor (experimental)
--------------------------

The client includes an experimental map editor for multiplayer maps. It only works for the terrain, so you still have to edit manually the map for the units.

Launch the editor
""""""""""""""""""

Start a game on a map. This map will be the starting point. Enter the console (press the key under escape) and enter the command: "edit". Press Enter. The editor keyboard bindings will be loaded from res/ui/editor_bindings.txt.

Select a terrain from the palette
""""""""""""""""""""""""""""""""""

Press PageUp or PageDown to select a terrain. The meaning of each terrain is stored in ``res/ui/editor_palette.txt``.

Each palette entry's ``style`` must match a ``class terrain`` name in ``rules.txt`` (e.g. ``forest``, ``dense_forest``, ``meadows``, ``lake``). When applied:

- **Static terrain** (``is_dynamic 0``, e.g. lake, mountain): locks ``type_name`` on the square; saved as ``terrain <name>``.
- **Dynamic terrain** (``is_dynamic 1``, e.g. forest, dense forest, meadows): places ``wood`` / ``meadow`` deposits on the square; terrain voice comes from ``square_terrain`` and can change when objects are removed.

Apply a terrain to a square
""""""""""""""""""""""""""""

Press Enter to apply the terrain to the current square. Neighboring squares with the same characteristics (ground and same height) will be linked automatically by a path. Different squares will have their path removed.

If zoom mode is enabled, Enter applies the selected terrain only to the current
sub-cell. The saved map will use the ``square/x,y`` syntax described in
`Sub-cell terrain (since 1.4.4.8)`_.

Toggle path to a neighbor
""""""""""""""""""""""""""

Press Control + Shift + arrow to add or remove the path in the corresponding direction.

Save map
"""""""""

Press Control + s to save the map. The file will never overwrite another file. The name of the file will be user/multi/editor0.txt, editor1.txt, editor2.txt, etc.

Quit editor
""""""""""""

Press F10 and quit the game to leave the editor. An autosave of the map will be done just in case (but don't count on it too much). Its name is user/multi/editor_autosave.txt

Add units
""""""""""

Open the file in a text editor. Use commands mentioned in ``Defining the starting resources of the players``.
