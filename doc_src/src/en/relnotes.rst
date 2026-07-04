
Release notes
==============

.. contents::


1.4.5.0
--------

Configurable terrain, transport containers, ``attack_inside_chance``, and random maps:

**Configurable square terrain**

- Terrain is ``class terrain`` in ``rules.txt`` plus matching ``style.txt`` defs; no engine-wide default terrain on every cell.
- Map ``terrain <name>`` applies passability, water, speed, and high ground from rules; ``class building_land`` extends meadows and build sites.
- Map editor and sub-cell ``square/x,y`` syntax: ``mod/building-land-terrain.rst``.

**Transport containers**

- ``passenger_attack_types``: unit types that may attack outside targets while inside the container.
- ``load_bonus``: per loaded unit, add stats to the container.
- ``passenger_bonus``: stats added to the passenger while inside; removed on unload. Same syntax as ``load_bonus``; can be combined with ``load_bonus``.

**``attack_inside_chance``**

- Open-container property: outside attacks hit passengers inside at this percent (e.g. wall ``attack_inside_chance 40``).

**Random map generator**

- Built-in templates list every ``rmg_terrain 1`` terrain from rules; placement uses rules properties.
- Custom ``random_map_template`` files in ``cfg/randommap/`` or ``mods/.../randommap/``.
- Share codes: ``RMG1`` (built-in abbreviations) / ``RMG2`` (full custom names).

See ``mod/building-land-terrain.rst``, ``mod/randommap.rst``, ``mod/modding.rst`` (Transport containers); tests ``test_transport_bonus.py``, ``test_attack_inside_chance.py``, ``test_randommap.py``.

**Building bridges on water**

- Workers can lay ``wooden_bridge`` spans tile-by-tile on rivers, lakes, and oceans (``is_buildable_on_water_only`` + ``bridge_terrain bridge_deck``).
- Scaffold phase: walk-on build, no passage until complete; finished spans link to shore / other decks; neutral for all players.
- Site TTS matches other ``buildingsite`` entries; footsteps use ``bridge_deck`` / ``big_bridge`` ``ground wood``.
- Docs: ``mod/water-bridge-building.rst``; tests: ``test_bridge_terrain.py``.

**Unit combat modifiers on terrain**

- ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``: per-terrain attack, cooldown, and charge bonuses for the **attacker's current square** (same ``terrain value …`` list syntax as ``speed_on_terrain``).
- Negative damage modifiers weaken attacks; positive ``*_cd_on_terrain`` lengthens cooldown.
- Docs: ``mod/building-land-terrain.rst``; tests: ``test_combat_terrain_modifiers.py``.

1.4.4.9
--------

Fixed a bug where the minimum effective charge distance was not working.

Updated the documentation.

1.4.4.8
--------

Sub-cell terrain for map authors and the map editor:

Sub-cell terrain inside a square

- Terrain commands can target an area inside a square with ``square/x,y`` syntax, for example ``high_grounds a1/1,1 a1/1,2``.
- ``subcell_precision N`` controls the subdivision. It defaults to ``3`` and accepts values from ``2`` to ``20``.
- Supported commands: ``terrain``, ``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` and ``no_air``.
- Combat, movement, terrain speed, cover and high-ground checks can use the unit's actual sub-cell.

Zoom browsing and editor behavior

- Zoom-mode map browsing announces the current sub-cell terrain, including partial high ground.
- In the experimental map editor, Enter applies the selected terrain to the current sub-cell while zoom mode is enabled.
- Saved maps write sub-cell overrides with ``square/x,y`` syntax.

1.4.4.7
--------

Hero XP threshold formulas (``xp_threshold_growth``) and post-level-up XP reset (``level_up_reset_xp``):

``Hero XP threshold formulas (``xp_threshold_growth``)``

- Hero defs can set ``max_level`` + ``xp_threshold_growth``; ``rules.txt`` load auto-fills ``xp_thresholds`` so modders need not list dozens or hundreds of cumulative XP values by hand.
- Curve types: ``linear``, ``quadratic``, ``polynomial``, ``geometric`` (see Heroes in ``modding.rst``).
- Backward compatible with explicit ``xp_thresholds`` (explicit list wins). Child defs can ``is_a`` inherit ``xp_threshold_growth`` and override only ``max_level``.
- Implementation: ``soundrts/xp_threshold_growth.py``, ``soundrts/definitions.py``; tests: ``test_xp_threshold_growth.py``.

``Post-level-up XP reset (``level_up_reset_xp``)``

- Optional ``level_up_reset_xp 1`` on hero defs: current XP becomes 0 after each combat level-up; default ``0`` keeps cumulative XP.
- When ``1``, prefer per-level ``xp_thresholds``, not cumulative totals.
- Implementation: ``soundrts/worldunit/world_status_update.py``; tests: ``test_level_up_combat_stats.py``.

1.4.4.6
--------

Mod sound naming cleanup, unified skill system, generic skill effects, skill target filters and -tag exclusions, level-up stat scaling, level skill unlocks, campaign hero carryover, backpack item use sounds, custom ready/prep sounds, backpack/equipment hotkey toggle, hero starting level and level-0 XP display:

Attack sound key rename

- ``ui/style.txt`` attack sounds now prefer ``mdg`` / ``rdg`` keys:
  ``launch_mdg`` / ``launch_rdg``, ``mdg_hit`` / ``rdg_hit``,
  ``mdg_hit_vs`` / ``rdg_hit_vs``, ``mdg_missed`` / ``rdg_missed``,
  and ``mdg_dodge`` / ``rdg_dodge``.
- Charge sounds use ``launch_charge_mdg`` / ``launch_charge_rdg`` and
  ``charge_mdg_hit`` / ``charge_rdg_hit``.
- Bundled ``style.txt`` files have been migrated; old ``matk`` / ``ratk`` keys remain compatible as fallback.

Custom ready sounds

- Skills with ``ready \<seconds\>`` can define ``ready \<sound\>`` on the skill style; manual and automatic triggers play it when prep starts.
- Normal attack prep can play unit style ``mdg_ready`` / ``rdg_ready`` sounds.

Unified skill system

- One ``class skill`` can be both manually used and auto-triggered; no separate twin lists required.
- Skill fields: ``auto_trigger 1``, ``manual_use 1`` (default 1), ``trigger_timing``.
- ``trigger_timing``: ``on_hit`` | ``on_attack`` | ``on_attack_replace`` | ``on_damaged``.
- Learned skills live in ``can_use_skill``; the command menu shows only ``manual_use 1`` skills.
- Legacy lists still work: ``active_trigger_skills``, ``attack_trigger_skills``,
  ``attack_replace_skills``,   ``passive_trigger_skills`` remain compatible alongside the new fields.

Generic skill effects

- Fixed damage ``harm_target N`` / ``harm_area N R``; combat damage ``harm_target mdg`` / ``harm_area mdg R`` (full pipeline).
- Combos ``burst mdg N (interval X)`` or `` (delays …)``; knockback ``push``; ``buffs`` / ``debuffs``; ``deploy``; ``summon``.
- Legacy ``teleportation`` / ``recall`` / ``conversion`` / ``raise_dead`` / ``resurrection`` still work.
- Trigger rates, HP conditions, attack-start buff/debuff lists remain compatible; see ``mod/skills-and-effects.htm``.

``Target type filters and exclusions (``-tag``)``

- ``class skill`` supports ``harm_target_type`` on ``burst`` / ``harm_target`` / ``harm_area`` / ``push``; default enemies only when unset.
- Prefix ``-`` excludes a tag (e.g. ``-building``). Applies to ``harm_target_type``, ``heal_target_type``, ``mdg_targets`` / ``rdg_targets``, buff/debuff ``target_type``.
- Diplomacy exclusions: ``-enemy``, ``-allied``, ``-neutral``.
- Examples: ``harm_target_type enemy unit -building``; ``heal_target_type unit -undead``; ``mdg_targets -building``.

**Level-up stat bonuses (``*_per_level``)**

- Units can set ``\<stat\>\_per_level`` in ``rules.txt`` for most combat, life, mana, heal/harm, and regen stats; each level up adds one step.
- Examples: ``hp_max_per_level``, ``mdg_per_level``, ``charge_mdg_per_level``, ``mdg_crit_rate_per_level``, ``mana_max_per_level``, ``heal_cd_per_level``, etc.
- Campaign hero restore reapplies cumulative bonuses up to the saved level.

Hero starting level and status display

- ``level`` / ``xp`` on hero defs in ``rules.txt`` (requires ``xp_thresholds``); ``level \> 1`` applies cumulative ``*_per_level`` on spawn.
- ``level 0``: start below level 1; Tab status shows level 0 and XP toward ``xp_thresholds[0]``.
- Heroes with ``xp_thresholds`` always announce level in Tab status (including 0 and 1).

``Full heal on level up (``level_up_heal_full``)``

- Optional ``level_up_heal_full 1`` on hero defs: restore full HP and mana on each level up; default ``0`` keeps incremental HP/mana gain only.

Level skill unlocks and skill books

- Unit ``level_skills \<level\> \<skill\> …``: auto-add to ``can_use_skill`` when that level is reached (with voice notify).
- Unit ``learn_level_skills``: extra book-learning level gate (strictest with item ``learn_level``).
- Skill books: permanent learn via backpack ``use_item``; pickup does not grant when gated.
- Do not duplicate the same skill on ``level_skills`` and a book.

Campaign hero carryover

- Hero defs: ``campaign_carryover 1`` (optional ``campaign_carryover_stats``, ``campaign_carryover_inventory``, ``campaign_carryover_id``).
- On victory, level/XP and backpack saved to ``user/campaigns.ini``; next chapter restores; co-op does not persist.
- Optional ``hero_min_level 13:2 …`` in ``campaign.txt`` for per-chapter level floors.

Backpack item use sounds (style.txt)

- Same three-level lookup as pickup/drop: item ``use`` / ``on_use`` → unit ``use_\<item type\>`` → global ``item_used`` (``def thing``).
- Sounds play only after server-confirmed success; no optimistic "used" voice on Enter.
- Skill books: use sound + skill title + ``skill_learned``; other consumables: item title + "used".
- Consumables are removed from inventory on success; skill-book ``unequip`` no longer strips permanently learned skills.

Backpack / equipment hotkeys

- Shift+V cycles between backpack and equipment (classic and layered); Ctrl+V removed; layered F3 still works.

Docs: ``mod/modding.rst``, ``mod/modding.rst``, ``mod/skills-and-effects.htm``, ``mod/campaign-hero-carryover.htm``
Tests: ``test_level_skills.py``, ``test_level_up_combat_stats.py``, ``test_campaign_hero.py``, ``test_wuxia_skills.py``, ``test_worldskill_deploy.py``, ``test_target_type_exclusions.py``, ``test_hit_vs_buff_sounds.py``, ``test_damage_seq_burst.py``,
``test_changelog_138x.py``, ``test_skill_trigger_sounds.py``, ``test_inventory_backpack.py``


1.4.4.5
--------

Random map HoMM/Civ5-style gameplay, default capture order, AI amphibious ops, Ctrl+Shift+F4 scoring fix, hotkey mapping editor:

Random map: HoMM / Civ5-inspired

- victory mode menu: conquest / economic / exploration / survival (TTS 5425–5430)
- map POI: ancient ruins, capturable barracks, central creeps, optional treasure
- share codes: 11th victory field; ``res/rules.txt``: ``ancient_ruin``, ``captured_barracks``
- docs: ``player/英雄无敌与文明5玩法说明.htm``; ``randommap.rst``
- tests: ``test_randommap.py``

Default capture order (can_capture)

- ``capture_hp_threshold 100``: ``can_capture 1`` → default occupy; ``can_capture 0`` → attack/move only
- thresholds below 100 still require combat to capture threshold
- docs: ``mod/modding.rst``; players ``player/unit-default-behavior.htm`` §4
- tests: ``test_capture_default_order.py``

AI cross-water operations

- amphibious gathering, transport assaults, naval upkeep on water maps
- tests: ``test_worldplayercomputer_water.py``, ``test_ai_naval_m3.py``

Train: scale batch to remaining population

- insufficient pop headroom when batch training → train as many as fit (e.g. 5 requested, 3 pop → 3 trained); zero headroom still fails
- ``worldorders/production.py`` (``TrainOrder._max_train_count_for_population``)
- tests: ``test_train_population.py``

Fix: Ctrl+Shift+F4 view switch vs scoring

- pin scoring human; no AI/passive victory rewards after switch; baseline of defeated scoring enemies at first switch
- tests: ``test_change_player_scoring.py``

Hotkey mapping editor

- Options → Key mapping (sibling of Hotkey scheme); ``hotkey_remapping_menu.py``, ``hotkey_editor.py``, ``hotkey_catalogs.py``
- layered 8 layers + classic ~179 bindings; per-mod ``user/hotkey_overrides/{mod_key}.json``; effective next game start
- search, advanced variants, alias keys (``binding_id@default_key``), clipboard import/export
- catalog TTS 5500–5684; classic advanced variants complete; control-group label fixes
- labels: Alt+Space → first-person mode; Ctrl+F2 → display toggle
- docs: ``mod/hotkey-mapping-editor.htm``, ``player/layered-hotkeys.htm``
- tests: ``test_hotkey_editor*.py``, ``test_hotkey_catalog_tts.py``, ``test_hotkey_editor_mod_isolation.py``

1.4.4.4
--------

Delayed loadout cards, scoring & grades, per-faction achievements, meta progress, CrazyMod, UX fixes:

Delayed pre-mission cards

- ``cards.txt``: ``delay \<seconds\>``, ``delay_minutes \<n\>`` — schedule effects after in-game time (``world.schedule_after``, respects ``timer_coefficient``)
- ``tech \<upgrade_id\>`` on cards; combinable with ``spawn`` / ``resource`` under one shared delay
- voice at apply: effects after N minutes/seconds; at fire: loadout card effect triggered (TTS 5387–5393)
- vanilla: ``card_reinforcements_delayed`` (3 footman after 10 min), ``card_delayed_melee_weapon`` (``melee_weapon`` after 8 min)
- achievements: ``reinforcement_contract`` → delayed reinforcements; ``defeat_expert`` → delayed melee weapon card
- docs: ``mod/delayed-card-loadout.htm`` (players: ``player/loadout-cards.htm``)
- tests: ``test_cards.py``, ``test_card_loadout.py`` (``-k delay`` / ``-k delayed``)

Post-game score & letter grades

- docs: ``mod/score-grading-system.htm`` (players: ``player/score-and-grades.htm``)
- base seven dimensions cap at 800; AI defeat bonus is extra and excluded from the percent denominator
- defeat grade capped at D (``grade_total`` max 479)
- win + utilization < 50%: frugal efficiency dimension (TTS 5251)
- mining on maps without deposit capacity: proportional to reference gather (1000 = 100 pts); campaign no-deposit maps unchanged
- survival 0 if no units produced; building loss/demolition 5 pts per building (was 10)
- removed unused legacy score helpers from ``worldplayerbase/resources.py``
- tests: ``test_score_breakdown.py``

Achievements & rank data

- Lieutenant (``rank_lieutenant``): 200 medals, 1 loadout slot
- ``defeat_beginner`` repeat medal 8; ``perfect_survival`` requires survival ≥90 and building defense ≥90

Fixes

- worker ``can_gather all``: attribute UI no longer duplicates “all” when deposit and building lists are both ``all``
- tests: ``conftest`` restores ``res.mods`` after mod-switching tests
- loadout / random-faction UX; NPC defeat broadcast gated by ``broadcasts_defeat_and_quit``

Per-faction & meta progress

- ``achievements_per_faction 1``, ``\_meta.json``, ``scope meta``; campaign excluded

CrazyMod 9

- per-faction milestones, meta tiers, balance tweaks

Documentation (player / developer)

- Index: ``help-index.htm``, ``player/README.htm``, ``mod/README.htm``

Campaign hero carryover (rules-driven)

- ``rules.txt``: ``campaign_carryover 1`` (optional ``campaign_carryover_id``, ``campaign_carryover_stats``, ``campaign_carryover_inventory``)
- ``campaign.txt``: ``hero_min_level 13:2 …`` for chapter floor levels
- saved on victory to ``user/campaigns.ini`` (``hero_\<id\>\_xp`` / ``\_level`` / ``\_inventory``); restored next chapter; co-op does not persist
- independent of ``campaign_flag`` / ``add_inventory_item``; see ``modding.rst``, ``mapmaking.rst``, ``mod/campaign-hero-carryover.htm``
- implementation: ``soundrts/campaign_hero.py``; tests: ``test_campaign_hero.py``

Fixes & voice

- lanes maps: ``has_entered`` with 1-based coords (e.g. ``8,2``) no longer collides with 0-based grid keys; ruin triggers work
- text inputs (share code, seed, etc.): Ctrl+V paste via pygame-ce clipboard API
- HoMM/Civ5 and campaign side-quest TTS moved from 5107–5123 to 5425–5441 to avoid ID conflicts

1.4.4.3
--------

Achievements and armory (phases 2–3: medals, ranks, cards, pre-mission loadout):

- new main-menu Achievements entry: achievement list + armory (rank, honors, medal total, card charges)
- after skirmish / random-map vs computer, ``achievements.txt`` unlocks are evaluated; voice for unlocks, medals, cards, rank promotion, and extra loadout slots
- progress is saved per mod: ``user/achievements/\<mod\>.json``
- pre-mission card loadout: Single player → Start on map → Start, then pick up to N cards by rank (Lieutenant = 1 slot, Captain = 2, … in ``titles.txt``); TrainingGame only (custom or random map vs AI — not campaign or multiplayer)
- effects apply at game start: bonus resources and/or units near your start; one charge spent per card used
- card spawns do not use population; random faction spawns use faction equivalents
- fix: loadout cards were not applied because the local player was only detected after ``GameInterface`` existed; now applied after map load, before the interface opens
- armory: browsing a card speaks its effect (start bonus, spawns, required rank if locked)
- repeat completion: meeting an already-unlocked achievement again grants ``repeat_medal \<n\>`` medals only (no card, honor, or unlock voice); medals still advance rank
- mod opt-out: ``achievements_enabled 0`` in ``rules.txt`` hides the menu entry and skips loadout / post-game processing
- ``AI ``starting_units`` bonuses in ``ai.txt`` do not consume population`` (map starts still do); ``starting_population`` is unchanged
- data: ``res/achievements.txt``, ``res/cards.txt``, ``res/titles.txt``; TTS ids 5244–5367, etc.
- docs: ``achievement-system.htm`` (``achievement-system.htm``)
- tests: ``test_achievements.py``, ``test_cards.py``, ``test_titles.py``, ``test_card_loadout.py``

1.4.4.2
--------

AI counter targeting (``counter_skill`` in ``ai.txt``):

- computer units use ``mdg_vs`` / ``rdg_vs`` (and ``is_a`` inheritance) when picking targets and sending attacks
- new ``counter_skill \<0-100\>`` script command: ``0`` = ignore counters (``menace`` only), ``100`` = always pick the best counter; values in between blend both
- vanilla tiers in ``res/ai.txt``: beginner ``25``, intermediate ``50``, advanced ``75``, expert ``90``, nightmare ``100``; omitted in a mod script defaults to ``100``
- new ``starting_resources`` / ``starting_units`` in ``ai.txt``: bonus resources and units added on top of the map start for invited computers (same syntax as map commands; applied once at game start, not in the script loop)
- new ``starting_population`` in ``ai.txt`` and maps: bonus population cap (plain integer, not ×1000) added on top of houses/units; still capped by ``global_population_limit``
- vanilla bonus starts: intermediate +50/+50 resources; advanced +100/+100 and 2 footman 2 archer; expert +200/+200 and 5/4/2 army; nightmare +400/+400 and 8/6/4 army
- docs: ``doc_src/src/en/aimaking.rst``, ``doc_src/src/zh/aimaking.rst``
- tests: ``test_ai_counter_targeting.py``, ``test_ai_loader_and_menu.py``, ``test_ai_start_settings.py``

1.4.3.9
--------

Layered interface hotkeys (global base + per-mode layer):

- single ``bindings.txt`` split into ``global_bindings.txt`` and seven mode files (unit/building/command/skill/help/map/diplomacy); load order: global → current mode → ``cfg/bindings.txt`` → mod append
- F-key switching: F1 unit↔building, F2 command↔skill, F3 inventory↔equipment, F4 help & query, F12 diplomacy, ESC enter/exit map browse; mode name announced on switch
- global layer keeps resources (z/x/SHIFT z/c), movement, square jumps, command confirm, F9/F11, etc.; former F1/F4 help and direct F12 diplomacy now enter dedicated overlay modes
- unit mode: workers ``s``/``w`` (was ``d``/``e``); soldiers 1–7 on ``d/e``…``;``/``p``; building mode slots ``building1``–``building16`` (``d/f/g/h/j/k/l/;`` + ``e/r/t/y/u/i/o/p``)
- command mode 30-slot index hotkeys; map mode ``f/g/m/p`` cycles deposits/meadows/passages on current square (no square jumps); ESC to map announces square summary and silently restores last map target
- mod ``style.txt``: ``keyboard worker``, ``keyboard soldier1``–``7``, ``keyboard building1``–``16``; ``bindings.txt`` body is now a compatibility stub
- inventory/equipment/attributes sub-screens call ``restore_active_bindings`` on exit; editor bindings unchanged
- classic single-file hotkeys: `````[general] layered_hotkeys = 0``` in ``user/SoundRTS.ini`` (default ``1`` = layered); or main menu Options → Hotkey scheme — Layered hotkeys / Classic hotkeys (effective next game); classic loads ``legacy_bindings.txt``, no F-key mode layers, ESC does not enter map browse
- mods may customize each scheme: layered via ``ui/*_bindings.txt`` or append ``ui/bindings.txt``; classic via ``ui/legacy_bindings.txt`` or append ``ui/bindings.txt``
- docs: ``../player/layered-hotkeys.htm``, ``../player/layered-hotkeys.htm``
- tests: ``test_layered_bindings.py``, ``test_map_browse_target_persist.py``

Age of Empires DE-style campaigns (single-player + co-op):

- single-player: mission browser (``synopsis``, five difficulty tiers persisted, completed/locked chapters, retry); enemy HP/damage scale by tier (Standard + solo = 100%)
- co-op: story-mission multiplayer (player slots + allied AI partners, shared intro/cutscenes/objectives, no treaty); difficulty and human count scale enemies; campaign TTS auto-loaded for localized place names
- see ``../player/campaign-menu.htm`` (``../player/campaign-menu.htm``)
- tests: ``test_changelog_1429_coop_campaign_difficulty.py``, ``test_changelog_1429b_campaign_browser_difficulty.py``, ``test_changelog_1429c_coop_story_mission.py``, ``test_changelog_1429d_coop_player_slots.py``, ``test_coop_campaign_place_names.py``

1.4.3.8
--------

Build fields, progressive objectives, and Zerg creep tumors:

- ``build_field_radius`` (tile BFS) vs ``build_field_radius_m`` (meters from `` (x,y)``); meter providers paint marks when ``build_field_persists`` / ``build_field_spreads`` — fixes Hatchery-only meter creep build checks
- Trigger ``register_objective`` registers primary numbers for victory without F9/voice; victory uses ``\_required_objective_numbers`` vs ``\_completed_objective_numbers`` (no premature win when goals are revealed one-by-one)
- F9 / ``add_objective``: "Primary objective N:" when multiple goals; colon after number; single goal omits number
- StarCraft mod: Queen Spawn creep tumor / tumor Extend creep tumor; skill attrs ``summon_requires_build_field``, ``summon_requires_marked_field``
- docs: ``campaign/progressive-objectives.htm``, ``../player/starcraft-zerg-creep.htm``; ``modding.rst``, ``mapmaking.rst``
- tests: ``test_build_rules.py`` (creep tumor), ``test_campaign_alliance_transfer_triggers.py`` (register_objective), ``test_objective_announce.py``

1.4.3.7
--------

Hunting system and wildlife voice labels:

- Age of Empires–style hunting: ``is_huntable`` animals leave ``food_carcass`` deposits; workers gather them; deer/sheep flee; sheep can be herded (``can_herd`` / ``herdable``)
- Wildlife announced as "animal" (e.g. "deer , animal"), not "neutral , NPC"; square summaries use a separate animal bucket
- Wildlife-only ``computer_only`` slots do not join the ``"ai"`` alliance (not with players, hostile creep, or other herds; mixed slots unchanged)
- Ctrl+Shift+F4 to a wildlife-only player says "you are animal"; mixed NPC + wildlife players still say "you are neutral NPC"
- Random maps spawn wildlife and orchards near starts; ``hunting_techniques`` improves carcass gathering
- docs: ``../player/hunting.htm``; ``modding.rst`` hunting section
- tests: ``soundrts/tests/test_hunting.py``, ``test_hunting_herd.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``

1.4.3.6
--------

Burst / sequence attacks (``damage_seq``):

- fixed burst interval: rules ``(interval …)`` is now respected (was hard-coded to 0.4 s)
- omit ``(damage …)`` to auto-split base ``mdg`` / ``rdg`` evenly (supports fractional damage)
- each shot in a burst triggers ``launch_mdg`` / ``launch_rdg``; list multiple sound IDs in ``style.txt``
- base rules: new ``repeating_crossbowman`` (upgrade from archer; Age of Empires Chu Ko Nu style)
- tests: ``soundrts/tests/test_damage_seq_burst.py``
- docs: ``../player/burst-attacks.htm``; ``modding.rst`` Combat system section

1.4.3.5
--------

Combat AI vs neutral units:

- player units in ``offensive``, ``defensive``, or ``chase`` mode do not auto-attack neutral
  units (``computer_only ... neutral``)
- defensive mode does not flee when only neutrals are present
- forced attack (``imperative`` go/attack, e.g. Ctrl+click on the unit) still works
- neutral creeps remain guard + counter-attack on their side; see ``../player/unit-default-behavior.htm``

1.4.3.4
--------

Procedural random map generator (RMG):

- Entry: main menu Start a game → Random map; or Random map in the online create-game map list
- Options: template (standard/fast/macro/lanes), size, player count, 2v2 teams, monsters, resources, terrain, water, treasure, seed, treaty
- After generation, seed and share code are announced; F5/F6 replay them from voice history (still available in the invite-AI menu)
- Import share code skips step-by-step menus; format ``RMG1:…`` — see `Random map guide <randommap.htm>`_
- Menu text inputs (share code, seed, login, etc.) support Ctrl+A/C/V/X select all, copy, paste, cut
- Code: ``soundrts/randommap.py``, ``soundrts/randommap_menu.py``; tests ``soundrts/tests/test_randommap.py``

1.4.3.3
--------

Indexed conditions (``killed_target`` / ``npc_has_item`` / ``unit_lost`` / ``building_lost`` / ``key_unit_killed``):

- Global spawn index (any square): ``(killed_target \<index\> \<type\> [enemy|ally])``, `` (npc_has_item \<index\> \<type\> \<item\>)``, `` (unit_lost \<index\> \<type\>)``, `` (building_lost \<index\> \<type\>)``, `` (key_unit_killed \<index\> \<type\>)``
- Square index: ``(killed_target \<square\> \<index\> \<type\>)``, `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``, etc.
- Same index rules as ``killed_target`` / ``npc_has_item``; only the Nth spawned unit/building at that square
- Example: ``(building_lost 1 townhall) (defeat)`` fails only if the 1st spawned town hall is destroyed (any square); `` (building_lost a1 1 townhall)`` is square-specific; `` (unit_lost 3 footman) (defeat)`` fails only if footman #3 dies
- Demo: The Legend of Raynor chapter 1; see ``campaign/unit-index.htm``
- Tests: ``soundrts/tests/test_map_select_loss_triggers.py``

1.4.3.2
--------

Unnumbered units (rules.txt, ``no_number 1``):

- Applies only to unit types with ``no_number 1``; default units (e.g. peasants) always keep serial numbers ("peasant 1 at a1")
- With ``no_number 1`` and only one living unit of that type: no serial number ("Guan Yu at a1", "knight leader at a1")
- With ``no_number 1`` and two or more of that type: serial numbers ("Guan Yu 1", "Guan Yu 2")
- Group, square, and battle summaries follow the same rule (e.g. "you control Guan Yu and 2 escort knights")
- See ``modding.rst``; campaign examples ``raynor``, ``npc_knight_leader`` in ``The Legend of Raynor/rules.txt``

1.4.3.1
--------

Inventory and equipment:

- Shift+V: backpack (all items in inventory); Ctrl+V: equipment (weapons and armor)
- mutually exclusive with Alt+V properties screen; requires exactly one friendly unit selected
- in-screen keys: arrows browse, Enter equip/use, Shift+Enter unequip, Delete/Shift+Delete drop, g reads intro
- unified item model: ``class item`` with ``equippable_as_weapon 1`` / ``equippable_as_armor 1``; stats apply on equip
- starting ``weapons`` / ``armor`` that are equippable items auto-enter inventory; silently equipped when no built-in gear of that kind and ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` is 1 (default; needs ``inventory_capacity`` > 0)
- legacy ``class weapon`` / ``class armor`` remain built-in (read-only in equipment screen)
- mixed built-in + item gear: built-in equipped at spawn; with ``spawn_weapons_equipped 1``, item weapons stay in backpack and cannot be equipped; built-in switches only with built-in, item only with item, no cross-switching (same for armor)

Unit default behavior (rules.txt):

- ``ai_mode``: starting AI mode — ``offensive``, ``defensive``, ``guard``, or ``chase`` (not ``patrol``)
- ``auto_gather`` / ``auto_repair``: worker auto-gather and auto-repair at game start (default 1)
- ``auto_explore``: mobile units start with auto-explore on (default 0)
- ``can_auto_explore 1``: unit menu offers enable/disable auto-explore commands

Giving items to NPCs:

- ``give`` order: right-click a non-hostile unit, command menu, or shortcut ``g``
- target needs ``receive_items 1``; optional ``accepted_items`` whitelist and ``accept_from`` relation filter
- trigger condition ``npc_has_item``; multiplayer demo ``res/multi/give_demo.txt``; campaign ch. 14–16 (``The Legend of Raynor/14.txt``\ –``16.txt``) for ally/neutral/enemy delivery
- ``npc_has_item`` / ``killed_target`` unit index syntax (``\<square\> \<index\> \<type\>``); demo The Legend of Raynor chapter 28; see ``campaign/unit-index.htm``

Find-item victory:

- trigger condition ``has_item`` checks player inventory for a given item type (optional count)
- item must stay in inventory (``consume_on_pickup`` must not be 1)
- example: The Legend of Raynor chapter 17 (``lost_amulet``)

Carry-to-square and story hand-over:

- trigger condition ``has_brought_item``: player unit arrives at a square while carrying an item (no drop)
- trigger action ``remove_item``: remove and destroy items from player inventories; use with ``cut_scene`` for narrative delivery
- trigger action ``do``: run multiple sub-actions in order (``if`` cannot replace this)
- example: The Legend of Raynor chapter 18 (``mana_potion`` at shrine c3)

Ground items and compound conditions:

- trigger action ``remove_ground_item``: delete items on the ground at a square (e.g. remove treasure after opening)
- trigger condition ``and``: true only when every sub-condition is true
- ``find`` syntax: square before type, including inside ``not``; wrong order makes conditions almost always true
- example: The Legend of Raynor chapter 20 (drop treasure, then pick up all gold coins)

Campaign diplomacy and unit transfer triggers:

- trigger action ``alliance_request``: one player requests alliance; in campaigns the human accepts with Ctrl+F4 (no F12 target selection)
- trigger conditions ``alliance_with`` / ``alliance_request_pending``
- trigger action ``transfer_units`` (aliases ``convert_units``, ``change_owner``): change unit ownership between players
- trigger action ``allied_assist``: ally units fight on their own (guard→chase); optional unit selector for partial switch
- trigger action ``allied_control``: grant direct command over an ally's army (whole ally or selected units); unmatched units switch to chase
- trigger action ``add_inventory_item``: put items into unit inventory (cross-chapter carry, quest rewards)
- trigger actions ``set_ai_mode`` / ``set_yield_on_defeat``: runtime AI mode and yield-duel toggles
- conditions ``units_yielded`` / ``units_yielded_by``, ``has_entered``; actions ``stop_all_units`` / ``release_yielded_units``: yield counts (filter by attacker), square entry, ceasefire, restore combat
- The Legend of Raynor chapters 24–27 (northern alliance arc); see ``../player/campaign-northern-arc.htm``

``phase_targets`` exclusion syntax:

- a leading ``-`` excludes a match (e.g. ``phase_targets -building`` = all units except buildings)
- includes and excludes can be mixed (e.g. ``phase_targets soldier -footman``)

``is_a`` exclusion inheritance ``-`` prefix:

- e.g. ``is_a footman(-hp_max)`` is equivalent to ``is_a footman(apart hp_max)``
- multiple exclusions: ``is_a footman(-hp_max -mdg)``

Bugs fixed:

- fixed unit selection being lost after a ``can_upgrade_to`` upgrade or ``can_change_to`` morph: for example, an archer selected with g stays selected after upgrading to a dark archer, without reselecting


1.4.3.0
--------

Bugs fixed:

- fixed a serious campaign victory bug: when a campaign map had two or more enemy computers, completing the objectives would not end the game; the root cause was mutating the player list while iterating during victory settlement
- fixed units and objects disappearing from a square for 4–5 seconds after a unit left
- in campaigns, F12 (dynamic alliance) no longer selects any target; trigger-script computers are not real opponent players
- trigger computers promoted by ``(ai easy)`` and similar triggers are announced as "NPC" instead of the internal name ``ai_timers``; their defeat is no longer announced in campaigns
- Ctrl+Shift+F4 now announces trigger computers as "NPC"


1.4.2.9
--------

- maps downloaded from a server keep their original name
- maps with the same content as a local map are not downloaded again
- multiplayer replays are stored as ``replay1``, ``replay2``, ``replay3``, etc.


1.4.2.8
--------

- small performance boost from Cython optimizations
- neutral computers: add the ``neutral`` keyword to a ``computer_only`` line; neutral AIs do not attack unless attacked first
- ``player_start \<N\> \<square\>`` fixes the spawn square for player N (see the map making guide)


1.4.2.7
--------

- saves and replays can be renamed (any language/characters): edit files in ``user/saves`` or ``user/replays``, or press Shift+Enter on a file in the restore/replay menu
- Delete asks for confirmation; Shift+Delete deletes immediately


1.4.2.6
--------

- up to 10 save slots per mod; each mod has its own saves, memory points, and replays
- cancelling a game creates a memory point; "continue unfinished game" appears on the main menu
- replay files are also mod-specific


1.4.2.5
--------

- ``can_advance`` for phase upgrades (distinct from ``can_research``); shown in the properties interface
- default starting phase is displayed at game start when a building has ``can_advance``
- ``hide_locked_commands`` in ``def parameters`` hides commands whose requirements are not met


1.4.2.4
--------

- new ``class phase`` (age-style progression): ``phase_targets``, ``phase bonus``, ``units_auto_upgrade``
- dynamic alliance: each alliance request now has its own cooldown


1.4.2.3
--------

- dynamic alliance during a game (F12 / Shift+F12 select target; F4 request; Ctrl+F4 accept; Shift+F4 cancel/reject/leave); pre-game alliances cannot be changed in-game
- cooperative campaign bug fixes


1.4.2.2
--------

- treaty mode: peace for a chosen duration (up to 20 minutes), then war
- cooperative campaign on servers: any player completing objectives contributes to the team


1.4.2.1
--------

Bugs fixed:

- passage sounds no longer delay place-name and coordinate announcements
- units no longer gain speed bonus on every revival
- upgrade changes to cost, time_cost, and population_cost now persist after research
- heal and harm upgrades no longer apply to every unit type
- air unit altitude restored to 1.3.8.1 behavior


1.4.2.0
--------

Bugs fixed:

- revived units can receive orders again
- self-attacks no longer trigger charge damage
- discount upgrades no longer affect units without the discount tech
- ground charge splash no longer hits air units
- transports with capacity ≥ 99 no longer load themselves


1.4.1.9
--------

- ``square_name`` hierarchy up to 3 levels (province / city / district); TTS announces names when entering from another region
- further performance optimizations


1.4.1.8
--------

- map coordinates use ``x,y`` (e.g. ``1,1``) instead of letter+number; legacy notation still accepted
- ``square_name`` for naming squares; translations in ``tts.txt``
- faction starting units and resources can be defined in ``rules.txt`` (map definitions take priority)


1.4.1.7
--------

- unified skill system (``class skill``) with ``effect_target`` and ``effect_range``
- multi-stat buffs, aura buffs (``buff_radius``), expanded harm/heal/regen parameters


1.4.1.6
--------

- debuffs can be defined on weapons
- fixed save-game load failure


1.4.1.5
--------

- ``intro`` keyword in ``style.txt`` for unit descriptions
- diagonal perception restored
- fixed production UI on non-producing buildings


1.4.1.4
--------

- 1.3.5.2 triggers migrated; td1–td3 maps playable


1.4.1.3
--------

- weapons and armor system; manual weapon switch (A / Shift+A / B+X); ``auto_weapon_switch``
- item system migrated from 1.3.5.2
- walls and gates buildable again


1.4.1.2
--------

- ``can_repair`` on workers; improved water-unit pathfinding and shore mining
- more attributes in the properties interface


1.4.1.1
--------

- enhanced properties interface with interactive browsing (can_train, skills, research, can_build)
- ``can_repair_ships`` for workers and buildings; shore ship repair (distance 6) and building auto-repair (distance 8)


1.4.1
------

- first-person RPG view is 360°; improved movement precision


1.4.0.9
--------

- first-person RPG mode guide; F8 dynamic zoom 3×3 to 15×15; path-aware browsing


1.4.0.8
--------

- ``minimal_mdg`` / ``minimal_rdg`` renamed back to ``minimal_damage``
- RPG skill hotkeys (1–0) in first-person mode


1.4.0.7
--------

- critical hit rates fixed; crazy-Mod playable


1.4.0.6
--------

- spectator mode on servers; victory/defeat sounds in multiplayer fixed


1.4.0.5
--------

- ``food`` keywords replaced with ``population`` (e.g. ``population_cost``)
- richer economy: resource buildings, auto/manual cultivation and production
- ``rpg_bindings.txt`` reserved for future RPG hotkey customization


1.4.0.4
--------

- ``auto_production`` / ``manual_production``; ``is_gather`` / ``is_create``; ``class resource`` separate from ``class deposit``


1.4.0.3
--------

- faction background and battle music (``\<faction\>\_music``, ``\<faction\>\_battle_music``)


1.4.0.2
--------

- menu select/confirm/return sounds; per-menu background music and battle music


1.4.0.1
--------

- charge and counter-charge mechanics; expanded buff trigger rates
- new defeat conditions: ``unit_lost``, ``key_unit_killed``, ``key_units_killed``, ``units_lost``, ``buildings_lost``, ``has_killed``; ``killed_target`` and ``has_killed`` support ``enemy`` / ``ally``


1.4
----

- combat rework: ``mdg`` + ``mdg_vs`` (additive), crit, piercing, explode
- hero and XP system from 1.3.5.2 integrated
- ``title`` / campaign / map parameters accept quoted strings; ``tts.txt`` translation format
- unpacked advanced maps in ``multi/`` supported
- fixed sounds playing when typing matching names in input boxes


1.3.9.8
--------

- buff/debuff system from 1.3.5.2 integrated
- enemies appear immediately when entering their square


1.3.9.7
--------

- ``can_train`` with quantities; ``can_change_to``; ``can_use_tech`` / ``can_use_skill`` menu fix


1.3.9.6
--------

- percentage cost/time_cost/population_cost on upgrades; decimal resource display


1.3.9.5
--------

- object filters (M / N keys); ``cfg/language.txt`` language selection


1.3.9.3
--------

- terrain cover/dodge fixes; research applies to future units; splash hit sounds temporarily removed


1.3.9.2
--------

- upgrade effects on cost/time/population; splash hit sounds; float attributes in properties UI


1.3.9.1
--------

- splash ``\_vs`` properties; delayed ``falling`` sound; projectile height attack rule


1.3.9.0
--------

- ``extraction_time`` / ``extraction_qty`` restored; Alt+V properties interface with ``attributes_bindings.txt``


1.3.8.8
--------

- ``can_gather`` / ``gather_time`` / ``gather_qty`` on workers; ``is_rewards`` / ``rewards_resource``


1.3.8.7
--------

- kill/destroy resource rewards; refund on self-demolish


1.3.8.5
--------

- mod-specific maps via ``mods/\<mod\>/multi/``


1.3.8.4
--------

- building resource production (``is_production``, ``production_type``, etc.)


1.3.8.3
--------

- flexible ``is_a`` inheritance (selective, exclusion, multi-parent)


1.3.8.2
--------

- capture ownership; ``mdg_projectile`` / terrain cover/dodge; improved exit containers
- major combat rework: ``mdg``/``rdg``/``mdf``/``rdf`` system; damage sequences; ``class skill``; guard/chase modes; sound system refactor


1.3.8.1
--------

For multiplayer games, this version requires:

- client: 1.3.8 or later
- server: 1.2-c12 or later

Main changes from 1.3.8:

Bugs fixed:

- in a restored game, the R key would select any soldier (thanks to Marco Oros for reporting the bug)
- when building a menu takes too much time, repeated keys would accumulate
- hopefully avoid any volume glitch when a sound source is created
- custom maps will appear after official maps
- running server.py doesn't require any package


1.3.8
------

For multiplayer games, this version requires:

- client: 1.3.8 or later
- server: 1.2-c12 or later

Main changes from 1.3.7:

- added tts_digit_coefficient in cfg/parameters.toml

Bugs fixed:

- paths between ground and water will be kept if both squares are ground
- units will flee to the previous square more often
- properly handle replay files that are not timestamps (thanks to dnl-nash)
- send bug reports only if the client is an executable

Translations:

- added Belarusian translation (thanks to Uladzimir)
- updated Slovak translation (thanks to Marco Oros)


1.3.7
------

For multiplayer games, this version requires:

- client: 1.3.7 or later
- server: 1.2-c12 or later

Changes from 1.3.6:

Now units can attack from inside vehicles or buildings:

- ranged units can attack as usual
- melee units can attack only from ground and without any additional range
- melee units cannot attack from air vehicles
- in the default game: units can enter in walls, gates and towers

Fixed issues with counterattacks to a nearby square:

- units who cannot counterattack will stay silent
- defensive units won't counterattack

Other:

- restored the "attack!" notification
- bugfix: a unit would not enter a building if the order was given from another square
- fixed: restore game
- inter-square attacks might work better

Modding:

- added armor_vs
- now "damage_vs" works with "is_a" (including several levels of "inheritance" and multiple "inheritance")

Map making:

- official "multi" maps moved to res/multi
- multiplayer "folder maps" must be zipped to be played online
- removed the "maperror.txt" file (the information is already in the in-game error message).

Changes to campaign format:

- mods.txt replaced with "mods" keyword in campaign.txt
- "title" keyword in campaign.txt
- new constraint: a complex mission map must be stored as a zip file


1.3.6
------

For multiplayer games, this version requires:

- client: 1.3.6 or later
- server: 1.2-c12 or later

Changes from 1.3.5:

Unit behavior:

- bug fixed: nearby offensive units will automatically counterattack again (they will move to the attacker's square and then return to their starting positions)
- bug fixed: defensive units will flee again

Interface:

- the description of controlled units will be less confusing
- improved group following (space key): the interface will usually follow the front of the group
- bug fixed: in style.txt, noise_if_very_damaged would never play
- bug fixed: SAPI wouldn't work

Water:

- from now on, the game won't create amphibious paths (solves the following problem: if the shortest path to destination included a water square, land units would walk into water and die)
- issue fixed: a mage could recall water units to non-water squares (Now a mage will recall water units to the nearest adjacent water square.)

Multiplayer:

- starting a non-private server will auto-configure the router (works only if UPnP is activated on the router; the configuration is automatically removed by the router after 20 minutes of inactivity)
- easier configuration of the standalone server
- local server auto-discovery by UDP broadcast (The local server will appear in the "choose a server in a list" menu.)
- bug fixed: in multiplayer games, a non-admin player could set a slower speed

Translations:

- updated Brazilian Portuguese, Chinese, Czech, Italian and Slovak translations

Map making:

- when possible, issue a warning instead of a map error
- bug fixed: in some cases, a trigger selected more units than specified. For example, if there are 3 dragons and many footmen in a1, (a1 10 dragon footman) would select 3 dragons and 7 footmen.


1.3.5
------

For multiplayer games, this version requires:

- client: 1.3.5 or later
- server: 1.2-c12 or later

Changes from 1.3.4:

- bug fixed: couldn't save a game with terrain
- fixed: the hit sound wasn't emitted if it killed the target
- fixed: the game would freeze if there wasn't enough space in a square to create a unit

Internationalization:

- converted all the tts.txt files to UTF-8 with BOM signature. The encoding is still explicitly defined in the first line as UTF-8. The BOM signature might help some text editors to select UTF-8 automatically.
- will always use UTF-8 (or ASCII) for text files other than tts.txt (rules.txt, style.txt, etc)
- updated Spanish translation (thanks to Oscar Corona)


1.3.4
------

For multiplayer games, this version requires:

- client: 1.3.4 or later
- server: 1.2-c12 or later

Changes from 1.3.3:

- probably fixed speech in a few more cases (please report if you still cannot start the client)
- restored save and restore (it seems to be working, but please be careful)
- restored infinite resources and tech for "aggressive computer 2" (more interesting)

Multiplayer:

- the client will remember the previously downloaded list of servers and use it if the metaserver is temporarily down
- in "enter the IP address of the server", entering an empty IP address will select your computer (no need to type: "localhost")
- standalone server: removed pygame dependency

Interface:

- console command: "a u_recall" will add the recall upgrade to the current player
- minor bug fixed: the interface wouldn't follow a unit inside a transport (if the unit was in follow mode before being transported)

Internationalization:

- updated Italian translation (thanks to Luigi Russo)

Main campaign:

- added chapter 12, a tiny map to show how dense forests work (the rule is: "any path between two dense forests is blocked")

Tip: to quickly check for improvements in a specific chapter of a campaign you have already played:

- press the "console" key under Escape and press "v" and Enter for an instant victory
- or edit user/campaigns.ini: in [single_campaign] "chapter = 12" for example


1.3.3
------

For multiplayer games, this version requires:

- client: 1.3.3 or later (if compatible)
- server: 1.2-c12, 1.3.0, 1.3.1, 1.3.2, 1.3.3 or later (if compatible)

Changes from 1.3.2:

- bug fixed: a unit wouldn't stop after using an ability requiring to get closer (deadly fog, exorcism...) and would move to the enemy...
- bug fixed: the game would require a target for an ability centered on the caster (for example: raise dead)
- bug fixed: water couldn't be seen from low ground (for example in map jl7)

The map interface should feel more natural:

- moving in the map won't cause collisions if you control a flying unit
- moving in the map won't cause collisions if you are defining the target of a recall order (for example)
- removed collisions between water and low ground

Dense forests:

- bug fixed: dense forests would create paths when cleared (even if there wasn't any paths before)
- now forests are dense if they have at least 7 woods (instead of 3)
- multiplayer map 8: updated (7 woods) and improved (faster economy)
- editor: updated terrain palette (dense forest if at least 7 woods)

Internationalization:

- bug fixed: maps with non US-ASCII characters could not be read on platforms using GBK or UTF-8 by default (now maps are always read as UTF-8 and errors are replaced with "?")
- converted the following maps to UTF-8: bs2, can1, qc1, qc2 and qc3
- updated Polish translation (thanks to Patryk Mojsiewicz)

Tiny changes in the main campaign:

- chapter 9: with the "deadly fog" bug fixed, necromancers should be easier to manage
- slightly improved chapters 5 and 10

Tip: to quickly check for improvements in a specific chapter of a campaign you have already played:

- press the "console" key under Escape and press "v" and Enter for an instant victory
- or edit user/campaigns.ini: in [single_campaign] "chapter = 11" for example


1.3.2
------

Changes from 1.3.1:

Main changes:

- the "choose a server" menu will include any server with a compatible server version (not only the same version) so the servers won't have to be updated as often
- compatible clients with different versions will be allowed to play together
- the "nearest" servers will appear first in the "choose a server" menu (servers with the smallest delay of response)
- the time taken to check if a server is available will be mentioned (expressed in milliseconds) in the "choose a server" menu for comparison
- the unavailable servers won't appear in the "choose a server" menu

Minor changes:

- slightly decreased the verbosity of server.log
- improved the standalone server guide (still not perfect though)
- added "release notes" to the documentation

1.3.1
------

Changes from 1.3.0:

- probably fixed: the game wouldn't start on Windows 7 (ImportError: DLL load failed while importing _socket)
- fixed: sometimes the game wouldn't start until the folder "gen_py" in "appdata\local\Temp" is deleted (AttributeError: module 'win32com.gen_py...' has no attribute 'CLSIDToClassMap')
- fixed: vcruntime140.dll could be missing
- fixed: couldn't get the list of servers
- fixed: pressing A will behave like before and pressing Control+A will only select inactive orders

1.3.0
------

Changes from 1.2-c12:

Main changes:

- only walls and gates can be built on exits (or any building "buildable on exits only")
- now a tower can be built only at the center of a sub-square, and only one tower per sub-square. The location of a tower can be selected in several ways:

  - in zoom mode: selects the current sub-square (must be free)
  - in square mode: selects any free sub-square, starting with the central one
  - if any object is selected: selects the enclosing sub-square (must be free)

- now the screen reader is the default TTS

Technical changes:

- migrated to Python 3
- replaced all TTS with accessible_output2 (patched to support Linux)

Bugs fixed:

- couldn't control a resurrected unit which was in a group
- a worker who postponed building or gathering to eliminate an intruder wouldn't move back to its task and would complete it in place
- a unit could see a plateau from below
- a unit couldn't see diagonally
- couldn't select a square as a target for building a gate (a free exit will be selected)

Interface improvements:

- zoom mode: validating a build order of a wall (or a gate) without selecting a specific target will automatically select the local exit (if it isn't blocked)
- tab will select any enemy first
- pressing escape when a target is selected will select the current square
- bug fixed: now entering or exiting zoom mode will select the mini-square or square as a target (instead of keeping the selected target)
- added commas in some messages (for clarity)
- shorter enemy summary
- bug fixed: would say "building site" and not the type of building
- bug fixed: in zoom mode, a default order for a building didn't set the rallying point to the sub-square but to the square
- bug fixed: a paused game wouldn't quit
- bug fixed: pressing Space will tell the exact orders even when some units have different orders (This is very useful to check how many workers are gathering gold, wood, etc (by pressing D). This could be useful to know how many units in a group are moving and how many have arrived. Pressing Control + Shift + S will give a complete summary of the orders of soldiers and workers.)
- in building mode, tab will select meadows before exits
- the description of a patrol order will recapitulate all the waypoints
- bug fixed: pressing Tab would select blocked exits
- bug fixed: it is no longer possible to build another wall on the same exit
- zoom mode: if no building land is found while a build order has been validated on a sub-square, an error will be raised (instead of searching for a building land in the enclosing square
