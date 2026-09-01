
Release notes
==============

.. contents::


1.4.9.4
---------

**Fix: Options speed change did not apply until restart**

- **Issue**: ``Game.run(speed=config.speed)`` froze the value at import. Changing Options from custom 6 to 1 wrote ``SoundRTS.ini``, but solo/campaign ``run()`` still used 6 from process start.
- **Change**: Read ``current_game_speed()`` when the match starts.
- **Scope**: ``game.py`` ``run``; ``game_interface_base.py`` ``GameInterface``.

**Fix: joining after the host started only beeped**

- **Issue**: Opening a waiting room's action menu, waiting until the host started, then choosing Join still sent ``register`` from the stale snapshot. The server replied ``register_error``; the client only beeped.
- **Change**: If the match has already ``started``, the server sends ``game_already_started`` and the client says the game has already started. Spectate is unchanged.
- **Scope**: ``serverclient.py`` ``cmd_register``; ``clientservermenu.py`` ``srv_game_already_started``; ``GAME_ALREADY_STARTED`` (5834).

**Fix: room list warned on lobby maps / invitations**

- **Issue**: While in the room list (or its action submenu), host start still sent lobby ``maps``, ``invitations``, and ``update_menu``. The room list is not ``ServerMenu``, so the first two logged WARNING; ``update_menu`` rebuilt from the stale snapshot and still offered Join.
- **Change**: Nested menus ignore ``maps`` / ``invitations``; the room list requests ``list_rooms`` on ``update_menu``.
- **Scope**: ``clientservermenu.py`` ``_ServerMenu`` ``srv_maps`` / ``srv_invitations``; ``RoomListMenu.srv_update_menu``.

**Change: set default game speed from Options**

- **Issue**: Solo and campaign starts used ``SoundRTS.ini`` ``speed``, but Options could not change it, so it stayed at 1.
- **Change**: Options → **Default game speed**: 1, 1.5, 2, 2.5, 3, 3.5, 4, then **Custom** to type 0.1–10. Saved as ``speed``; solo/campaign use it. Multiplayer still picks speed when creating a room.
- **Scope**: ``config.py`` ``game_speed_type``; ``clientmain.py`` ``default_game_speed_menu``; ``DEFAULT_GAME_SPEED`` (5835–5837).

**Change: accessibility voice and display toggles in Options**

- **Issue**: Accessibility TTS was only in the game menu / menu F4, and the map display was only Ctrl+F2; Options had neither.
- **Change**: Options now has **Accessibility voice** and **Display**; Enter toggles them. Same config (``speech_enabled``, ``display_enabled``). Ctrl+F2 and menu F4 still work.
- **Scope**: ``clientmain.py`` ``options_menu``; ``DISPLAY_TOGGLE`` (5838).


1.4.9.3
---------

**Fix: multiplayer spectating stole entity ids**

- **Issue**: Creating the spectator player consumed ``world.get_next_id()``, so later trained or built units had ids one higher than the live match. Human orders select by id, so replayed ``all_orders`` hit the wrong targets; ``active_objects`` sort-by-id could also fork.
- **Change**: After creating the spectator, restore the numeric id sequence and tag the spectator ``pure_spectator``. Still consumes no ``world.random`` and takes no player slot.
- **Scope**: ``game.py`` ``_create_spectator_player``; headless ``test_multiplayer_spectate.py``.

**Fix: spectating kept saying "you are spectating", then stayed silent**

- **Issue**: Catch-up backlog oscillating around the threshold replayed ``YOU_ARE_SPECTATING``. Unmuting only at queue length 1 left live spectators muted (queue often sits at 2–3), so arrows/Tab/F10 seemed dead until leaving for the lobby.
- **Change**: Announce once and restore audio when backlog is within the catch-up threshold; silently drop a late lobby ``spectate_success``. In-game ``spectator_joined`` / ``spectator_left`` are spoken instead of a WARNING.
- **Scope**: ``game_interface_base.py``, ``worldclient.py``.

**Fix: spectator started with no square, so arrow keys did nothing**

- **Issue**: Pure spectators have no units, so ``interface.place`` stayed empty until PageUp / PageDown picked a square.
- **Change**: Open the camera on a real player's spawn square.
- **Scope**: ``game_navigation._initial_observer_place``.

**Change: one lobby room list, optional password for join and spectate**

- **Issue**: Public vs private was confusing, and spectating lived in a separate menu. "Public" used to mean auto-invite everyone; private rooms were invite-only.
- **Change**: Creating a game no longer asks public/private — after map/speed/treaty you set a password or skip. The lobby has a single **room list**: waiting rooms can be joined or spectated (spectators still wait for the host to start), started matches can be spectated. Password rooms stay on the list (announced as protected); join and spectate both require the password. Invited players skip it when joining. Hosts can still invite someone from the room menu.
- **Scope**: ``serverroom.py``, ``serverclient.py``, ``clientservermenu.py``, ``room_password.py``; headless ``test_open_rooms_lobby.py``.

**Fix: waiting-to-spectate screen had no quit, Esc did nothing**

- **Issue**: The wait-for-host spectator menu never applied ``make_menu()``, so choices were empty. Esc only confirms the last item, so there was no quit and Esc did nothing.
- **Change**: Apply the "quit / leave this game" row when entering the wait screen; Esc confirms it the same way as the guest wait menu.
- **Scope**: ``clientservermenu.py`` ``WaitingToSpectateMenu``.

**Fix: "you are spectating" was cut off by square/ops speech**

- **Issue**: Catch-up used ``voice.info()`` to queue ``YOU_ARE_SPECTATING``, then the next ``voice.item()`` (square or orders) preempted it.
- **Change**: Speak it with ``voice.alert()`` so it finishes before later items; still announced only once.
- **Scope**: ``game_interface_base.py`` ``_update_catch_up_audio``.


1.4.9.2
---------

**Change: rules-driven bounce (StarCraft Mutalisk glaive)**

- **Issue**: The engine had circular splash and line pierce, but no hop-to-nearby-enemies-with-decaying-damage keyword, so Mutalisks were single-target.
- **Change**: Added ``rdg_bounce`` / ``mdg_bounce`` (extra hops), ``*_bounce_range`` (0 = attack range), ``*_bounce_decay`` (percent kept per hop; 0 defaults to 33, i.e. 9→3→1). Bounce runs only after a primary hit; allies are skipped; a unit is not hit twice in the same chain; filters follow ``rdg_targets``.
- **Scope**: ``combat/bounce.py`` and combat resolution; StarCraft Mutalisk ``rdg_bounce 2``, range 3, decay 33.

**Change: StarCraft Lurker and Colossus line pierce**

- **Issue**: AoE2 scorpion-style ``rdg_pierce_line`` existed, but the StarCraft mod had no Lurker (spine line) or Colossus (thermal lances).
- **Change**: Zerg Lurker Den + Lurker / burrowed Lurker (width 0.5); Protoss Robotics Facility / Robotics Bay + Colossus (width 0.6). Hydralisks morph and larva can upgrade; expert / nightmare AI builds them.
- **Scope**: ``mods/starcraft/rules.txt``, UI, AI.

**Change: AoE2 scorpion extras deal 50% after armor**

- **Issue**: Pierce extras used full damage, unlike original (aimed unit full, others half after armor — same as a stray arrow).
- **Change**: ``rdg_pierce_decay`` / ``mdg_pierce_decay`` is the percent kept on extras after armor; 0 = 100%. Scorpion / Heavy Scorpion use 50. Lurker / Colossus omit it and stay full along the line.
- **Scope**: ``combat/pierce_line.py``, ``receive_hit`` ``hit_scale``; ``mods/aoe2/rules.txt``.

**Change: attributes screen shows line pierce, bounce, and pasture fields**

- **Issue**: Line pierce, bounce, and AoE2 pasture spawn only existed in rules; the attributes screen did not list them.
- **Change**: When the rules are set, the screen lists the fields (omits empty ones):

  - Pierce: ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``, ``*_pierce_decay`` (0 shows 100%)
  - Bounce: ``rdg_bounce`` / ``mdg_bounce``, ``*_bounce_range``, ``*_bounce_decay`` (0 shows 33%)
  - Pasture / spawn: ``spawns_unit``, ``larva_spawn_time``, ``larva_cap``, ``spawn_player_cap``, ``spawn_immediate``; storable ``storable_resource_types``; sheep ``claimable``; herders ``can_herd``

- **Scope**: attributes screen, ``msgparts`` 5800–5821.

**Change: line upgrades remap the production queue (AoE2 DE)**

- **Issue**: Researching Onager only morphed field Mangonels; units still queued at the Siege Workshop came out as Mangonels.
- **Change**: Completing the research rewrites same-line ``train`` orders to the new form; spawn also resolves to the highest unlocked tier. Cost and remaining time already paid stay unchanged.
- **Scope**: ``apply_unit_line_upgrade``, ``TrainOrder.complete``.

**Fix: Aztec Eagle Scouts did not become Eagle Warriors**

- **Issue**: The militia line had ``can_upgrade_to man_at_arms``; Eagle Scout's ``can_upgrade_to`` was empty. Researching Eagle Warrior unlocked the tech but left field ``aztec_eagle_scout`` unchanged.
- **Change**: ``eagle_scout`` → ``eagle_warrior`` → ``elite_eagle_warrior``; Jaguar Warrior → Elite. Dark Age Aztec eagles ``is_a eagle_scout`` and inherit the chain.
- **Scope**: ``mods/aoe2/rules.txt``.


1.4.9.1
---------

**Fix: CrazyMod pra1 computers froze on the hall opener**

- **Issue**: Lines like ``get chatelet 10 serf`` never finished: an owned hall was treated as a soldier held for later barracks, and workers who can make halls counted as an already-owned barracks, so AIs only printed ``vermine_nm_loop`` and built nothing.
- **Change**: Owned-building ``get`` lines complete; worker-made halls are not barracks; soldier-holds skip buildings. Skill summons (``can_use_skill`` → ``termitiere``) count as makers.
- **Scope**: Computer plan parsing and makers; CrazyMod zerg AI dropped extra ``get larve`` (hatchery spawns larvae).

**Fix: untargeted skills (larva) did nothing**

- **Issue**: Empty ``effect_target`` left ``UseOrder`` with no target, so CrazyMod ``a_larve`` and similar skills no-op'd.
- **Change**: Missing / ``self`` targets apply to the caster.
- **Scope**: ``worldorders/skills.py``.

**Change: CrazyMod ranged units get projectile speed**

- **Issue**: Long-range units/buildings lacked ``rdg_projectile_speed``, so shots hit instantly.
- **Change**: Added ``rdg_projectile`` / ``rdg_projectile_speed`` from range.
- **Scope**: ``mods/crazyMod9beta10/rules.txt``.

**Change: StarCraft AI uses this mod's unit names**

- **Issue**: ``ai.txt`` still asked for vanilla ``peasant`` / ``footman`` / ``townhall``, so computers never trained.
- **Change**: Terran/Protoss/Zerg scripts use SCV, probe, drone, marine, etc. Addon ``addon_grants_train`` counts as a maker so ``get tank`` builds a factory.
- **Scope**: ``mods/starcraft/ai.txt`` and maker lookup.

**Change: StarCraft maps use minerals/vespene; start peasants spawn**

- **Issue**: Maps still listed ``goldmines`` / ``woods``; start ``peasant`` is undefined in this mod (``couldn't create an initial unit``).
- **Change**: Multi maps use ``mineral_field`` / ``geyser``; the faction table maps map ``peasant`` to SCV / probe / drone even when peasant has no class.
- **Scope**: StarCraft multi maps, ``equivalent_type``, start parsing.

**Change: StarCraft times and gather match SC2 Faster**

- **Issue**: Train, upgrade, research times and gather yields were still closer to SC1.
- **Change**: Align with SC2 Faster (5 minerals, 4 gas / 2 depleted, geyser 2250); ranged units get ``rdg_projectile_speed``.
- **Scope**: ``mods/starcraft/rules.txt``.

**Fix: jl1 beginner computers ping-ponged gold and wood**

- **Issue**: When feudal needed both gold and wood, every AI turn stole the same peasants from gold to wood and back, so trips never finished and beginners idled.
- **Change**: Do not steal a worker from another missing resource that is still at or under its cap.
- **Scope**: Computer ``_send_workers_toward_resources``.

**Fix: feudal ``time_cost -5`` skipped proportion 2 and 8**

- **Issue**: Phase ``time_cost -5`` applied on the player and again from ``_phase_bonus_pool``, so a 12s footman became 2s; 300ms ticks skipped 2/5/8 on the bar.
- **Change**: The pool keeps combat stats only; train duration is snapshotted and skipped ``completeness`` 0–10 values are filled.
- **Scope**: Phase pool and ``ProductionOrder`` progress.

**Fix: first achievement unlock also announced a repeat**

- **Issue**: ``evaluate_new_unlocks`` wrote ``once_keys`` before ``evaluate_repeat_completions``, so a first unlock was also treated as a recompletion.
- **Change**: Evaluate repeats first, then new unlocks. Private still has 0 loadout slots (lieutenant gets 1); that is by design.
- **Scope**: ``process_game_end_achievements``.

**Fix: console terrain palette painting**

- **Issue**: Forest lacked ``is_dynamic 1``, so painting locked the square and chopping trees did not revert. The goldmine brush dropped the wood after the mine took the free tile. Painting forest after a lake still searched for space as water, so trees never spawned.
- **Change**: Forest is dynamic; the palette sets land/water before placing resources; mines and trees use collision-off arrange.
- **Scope**: Palette apply, ``ensure_resources``; ``forest`` in base / AoE2 / StarCraft / CrazyMod.


1.4.9.0
---------

**Change: splash ``*_vs`` applies to the unit that is hit**

- **Issue**: ``mdg_splash_vs`` / ``mdg_splash_decay_min_vs`` used the aimed unit to resize the whole splash pool, so a knight next to an aimed archer shared the archer bonus.
- **Change**: Base ``mdg_splash`` / ``rdg_splash`` is still randomly split; ``*_splash_vs`` and ``*_splash_decay_min_vs`` apply to **each splashed unit**. Charge splash matches.
- **Scope**: ``combat/splash.py`` and charge splash.

**Balance: restore DE mangonel-line damage**

- **Issue**: 1.4.8.7 cut ~25% assuming no friendly fire plus full per-target splash; splash is a shared pool, so the extra cut stacked.
- **Change**: Mangonel / Onager / Siege Onager back to 40 / 50 / 75; ``mdg_splash`` matches melee.
- **Scope**: ``mods/aoe2/rules.txt`` mangonel line.

**Balance: AoE2 splash pools match main attack**

- **Issue**: Mangonel already used ``mdg_splash`` = melee; bombard cannon, cannon galleons, dromon, turtle ships, Warwolf, elephant/ram trample, and bombard towers still had splash ``1`` as a flag, so the shared pool was empty.
- **Change**: Splash pool equals main ``mdg`` / ``rdg``; Logistica trample 9/12; bombard tower gets 120 splash and 0.5 radius. Petards and demolition ships were already correct.
- **Scope**: ``mods/aoe2/rules.txt``.


1.4.8.9
--------

**Fix: computer crash requisitioning fishing ships for land scaffolds (``KeyError: deep_fish()``)**

- **Issue**: Forgotten-site repair requisitioned any ``Worker``, including fishing ships on ``deep_fish``. ``_gathered_deposits`` only counts land peasants, so decrementing crashed.
- **Change**: Water workers are not pulled onto land scaffolds; gather counts decrement only after the new order is allowed and only if the deposit was tracked.
- **Scope**: Computer ``order()`` repair requisition.

**Fix: scorpion pierce rules dropped on load**

- **Issue**: ``rdg_pierce_line`` / ``rdg_pierce_width`` were in rules and the parser tables, but ``Soldier``/``Creature`` lacked class attributes, so load warned and stripped them; pierce never applied.
- **Change**: Pierce fields exist on ``Creature`` and are copied onto instances; aoe2 scorpion / heavy scorpion keep the flags.
- **Scope**: Unit attributes and aoe2 scorpions.

**Fix: gathering fog-memory shore fish warned about moving the real object**

- **Issue**: When the water square was out of vision, gather targeted a ``shore_fish`` memory copy; emptying it ``delete()``'d the copy and logged ``Will move the real object instead of its memorized version``.
- **Change**: ``extract_resource`` on a memory copy debits the live deposit.
- **Scope**: Deposit gathering (shore fish, etc.).

**Fix: unit menu crash when ``player`` is None (mage, etc.)**

- **Issue**: ``EnableAutoExplore.is_allowed`` read ``unit.player.is_human``; fog memory, corpses, and unowned units have ``player is None`` and raised ``AttributeError``. ``_menu`` aborted the whole loop, dropping later commands.
- **Change**: Treat a missing ``player`` as non-human and return False; same guard on disable auto-explore and computer auto-explore.
- **Scope**: Unit command menu.

**Fix: command menu crash on EnableAutoExplore when ``player`` is None (mage)**

- **Issue**: ``EnableAutoExplore.is_allowed`` read ``unit.player.is_human``; fog memory, corpses, and unowned units have ``player is None`` and raised ``AttributeError``. ``_menu`` caught the whole loop, so later commands were dropped.
- **Change**: Return False when ``player`` is None or not human; same guard on disable auto-explore and computer auto-explore.
- **Scope**: Command menu (auto-explore toggle).


1.4.8.8
--------

**Change: revert “0 melee attack vs negative armor”**

- **Issue**: Allowing ``mdg 0`` to melee negative ``mdf`` made “0 attack” feel wrong.
- **Change**: ``mdg == 0`` (non-explode) cannot start melee again; ``max(1, attack−armor)`` stays for real hits. aoe2 archers no longer get a free melee ``mdg_range``.
- **Scope**: Attack gates / AI attack-capability cache / aoe2 archers. Scorpion pierce and mangonel nerf from 1.4.8.7 remain.

**Improvement: attribute “usable techs” filtered to civ-researchable**

- **Issue**: Unit ``can_use_tech`` lists often include foreign unique techs for effect targeting, so attributes read out rocketry etc. for the wrong civ.
- **Change**: The list shows only techs this civ can research (plus ally ``team_share_research`` and already researched). Actual upgrade application and allied ``_update_allied_upgrades`` sharing are unchanged. Base / crazyMod archer techs on the shared lumber mill still appear.
- **Scope**: Attribute list and left/right navigation indexes.


1.4.8.7
--------

**Improvement: rules-driven projectile line pierce (scorpion)**

- **Issue**: AoE2 scorpions should pierce units along the shot line; the engine only had circular splash.
- **Change**: Added ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``. Projectiles deal extra hits along the aim segment (excluding the primary target; pierce still applies if the primary misses). aoe2 scorpion / heavy scorpion enable ``rdg_pierce_line 1``.
- **Scope**: Combat resolution and aoe2 scorpions; splash remains enemies-only.

**Balance: mangonel line damage nerf (no friendly splash)**

- **Issue**: Splash already skips allies; keeping DE-level base damage made mangonels too strong.
- **Change**: Mangonel / Onager / Siege Onager melee damage cut ~25% (40→30, 50→38, 75→56).
- **Scope**: ``mods/aoe2/rules.txt`` mangonel line.

**Improvement: 0 melee attack can hit negative-armor targets (rams)**

- **Issue**: ``mdg 0`` was gated out before armor, so rams with ``mdf -3`` never took ``max(1, 0−(−3))=3``.
- **Change**: Units with ``mdg_range`` (or explode) may melee when post-armor damage would be > 0; units without melee range (e.g. monks) stay blocked. Archers / skirmishers / cavalry archers gain ``mdg_range 1``. 0 attack vs 0 armor still floors at 1 (AoE2-like).
- **Scope**: Attack gates / melee range / aoe2 archers and rams.


1.4.8.6
--------

**Fix: aoe2 Hand Cannoneer trainable at the Archery Range**

- **Issue**: Hand Cannoneers did not appear in the Archery Range train list; some civs listed them under ``can_research``, and the unit only required Imperial Age (not Chemistry).
- **Change**: ``hand_cannoneer`` requires ``imperial_age chemistry``; generic Archery Range and civ shells that have the unit list it under ``can_train`` (Byzantines, Japanese, Franks, Teutons, Portuguese, Malians, …). Britons, Chinese, Mongols, Vikings, Vietnamese, Aztecs, and Celts still lack them (DE tech tree).
- **Scope**: ``mods/aoe2/rules.txt`` Archery Range and Hand Cannoneer definitions.

**Fix: villager “can build” detail resolves civ building shells**

- **Issue**: The build menu keeps semantic names (e.g. ``aoe_castle``). Drilling into details used the generic shell, so a Briton castle preview showed only the Trebuchet until the real castle was built (Longbowman).
- **Change**: ``_show_unit_detail`` uses ``resolve_buildable_type`` for the current faction shell (``aoe_castle`` → ``briton_castle``, etc.) so train/research lists match the built building.
- **Scope**: Attribute-screen type details opened from can-build / can-train entries.

**Fix: unit type details stack age / civ bonuses**

- **Issue**: Opening Militia, Archer, etc. from a can-train list showed rules base stats only, missing Malian pierce armor, Briton archer range, and other ``on_phase`` / research-stack bonuses.
- **Change**: Detail proxies reuse ``Player._phase_bonus_pool`` via the same ``Phase.apply_pool_*`` path as ``Player.add``, so preview stats match trained units.
- **Scope**: Attribute type details (not tech/skill entries).


1.4.8.5
--------

**Improvement: box-select prefers military; crowded map sprites shrink**

- **Issue**: A drag box selected workers, soldiers, and buildings together, unlike Age of Empires II Definitive Edition. ``ui/map`` sprites are larger than the collision dot, so stacked units in one square covered each other.
- **Change**: Box-select follows DE: if the box has military (``class soldier``), keep only military; else if it has workers (``class worker``, including fishing ships), keep only workers; else buildings. Click-select is unchanged. Map sprites shrink when many units share a square, with a team-color pip at the true position.
- **Scope**: Ctrl+F2 / F8 mouse box-select and map painting. Keyboard selection and TTS unchanged.

**Improvement: starter unit spritesheet anims (optional Spine)**

- **Issue**: ``ui/anims/`` had only docs, so Ctrl+F2 kept using static ``ui/map`` PNGs; ``go`` orders did not switch to ``walk``.
- **Change**: ``python tools/gen_unit_anims.py`` writes 4-direction sheets (idle/walk/attack/gather) for base and aoe2 mobile types. ``go``/``use`` → ``walk``; ``meta.json`` supports ``dirs: 4``; ``backend: spine`` silently falls back to a spritesheet in the same folder when no runtime is installed.
- **Scope**: ``game_unit_anim.py``, ``res/ui/anims/``, ``mods/aoe2/ui/anims/``. TTS / blind play unchanged; missing packs still fall back to map PNG / shapes.

**Fix: farm auto-replant no longer shows redundant “start auto cultivate”**

- **Issue**: While a farm was already in auto-cultivate mode (including between auto-replant cycles), the command card showed both “start auto cultivate” and “stop cultivate”.
- **Change**: When ``current_production_mode`` is already ``auto``, hide the start-auto command and keep only stop. Same for manual ``auto_produce`` / ``manual_produce`` menus.
- **Scope**: ``AutoCultivateOrder`` / ``StopCultivateOrder`` and matching production menus.

**Fix: worker default order on farms is gather, not go**

- **Issue**: With a worker selected, right-clicking a farm issued ``go`` instead of ``gather``.
- **Change**: ``Worker.get_default_order`` checks gatherable deposits/buildings (including ``can_gather_building`` farms) before the generic living-unit ``go`` fallback.
- **Scope**: Worker default right-click; depleted or forbidden targets still use ``go``.

**Fix: aoe2 Frank free farm-tech aliases did not satisfy parent requirements**

- **Issue**: After researching ``frank_horse_collar`` (``is_a horse_collar``, free), Heavy Plow / Crop Rotation still required ``horse_collar`` / ``heavy_plow``. Other civs that research the parent names worked.
- **Change**: ``player.has()`` treats researched upgrades’ ``is_a`` / ``expanded_is_a`` as satisfying the parent. Free farm techs (Frank civ bonus) unchanged.
- **Scope**: Tech requirement checks (civ tech aliases).


1.4.8.4
--------

**Performance: Ctrl+F2 map view and world simulation**

- **Issue**: With Ctrl+F2 on and many computers, map painting and world updates could not keep real time. The hot path repeatedly used EntityView ``__getattr__``, rebuilt fog every tick, and reclassified every object and sprite. Unit ``decide`` and square occupancy ran too often.
- **Change**: The map view reads kind and coordinates from the world model (``stamp_map_view_cache``, ``_map_kind``). ``display_objects`` paints in layer buckets; resources skip unit animation and hit-point bars. Fog skips unchanged objects and caches ``is_memory``, sprites, and labels. ``memory_for_display`` is cached per tick. Idle units delay ``decide`` (``_next_decide_time``). Squares cache ``used_square_space``. Combat-idle status updates take a cheap path. Viewport cell clipping (``visible_cell_range``) was tried; the object loop got slower, so it was not kept.
- **Scope**: Ctrl+F2 map view, client fog, computer updates. TTS and rules gameplay unchanged.


1.4.8.3
--------

**aoe2: HUD / map art and DE architecture sets**

- **Issue**: The Age of Empires II DE mod had no command-card or map PNGs of its own, so Ctrl+F2 fell back to the base peasant/footman art. Civilizations share type names such as ``militia``; making a unique militia per civ would not match DE (DE uses regional architecture sets, not per-civ unit IDs).
- **Change**: Later resource layers overlay same-named PNGs from the base pack. aoe2 ships ``mods/aoe2/ui/icons`` (command card / queue) and ``ui/map`` (top-down). Starter geometry: ``python tools/gen_aoe2_hud_icons.py``; custom PNGs do not need that script. ``ui/architecture.txt`` groups civs into sets such as ``western_european`` / ``east_asian``; lookup tries ``ui/map/<set>/<type>.png`` first. Civs in the same set share art (Britons and Franks use the same militia). Neutral deposits and wildlife stay at the top level. ``rim`` and other RGB values affect the generator only. StarCraft-style mods already use distinct type names per race (``marine`` / ``zergling`` / ``zealot``), so one PNG per type is enough — no architecture subfolders.
- **Scope**: Engine HUD/map PNG loading; aoe2 art and ``architecture.txt``. TTS / blind play unchanged.


1.4.8.2
--------

**aoe2: rules-driven fishing (shore fish / deep sea fish)**

- **Issue**: The DE mod only had fishing-ship fish traps. There were no shore or deep-sea fish deposits, fishing ships could not gather natural fish, and villagers could not fish from the shore. The dock and fish trap were Feudal, so Dark Age fishing was impossible unlike DE.
- **Change**: Deposits with ``gather_from_shore 1`` can be gathered by ground workers on an adjacent land square (generic engine flag). aoe2: ``shore_fish`` (200 food, villagers + ships) and ``deep_fish`` (225 food, ships only). Gillnets and the Japanese fishing-ship work-rate cover all three sources. Water maps and random lakes/rivers place fish. Dock and fish trap are Dark Age (transport / galley / trade cog stay Feudal). Computers request a dock on water maps, then train water gatherers.
- **Scope**: Engine gather/AI/random maps; aoe2 rules and water multiplayer maps.

**Fix: gather / build / repair / store sounds play at the target, not the worker**

- **Issue**: Mining, woodcutting, shore fishing, building, and repair loops were attached to the worker, so stereo played at the villager. Shore fishing sounded on land; repair hammers sat on the peasant instead of the building.
- **Change**: Gather / build / repair activity noise can still be defined on the worker (``noise_when_exploiting_*`` / ``noise_when_building``, optional ``noise_when_repairing``), but stereo coordinates come from the deposit or building. A construction site with workers no longer stacks its own hammer loop (self-constructing sites still play on the site). Store cues ``store_resource1`` … may be on the villager / fishing ship **or** the warehouse; if both are set, the worker wins. Stereo still plays at the warehouse. ``store_resource_0`` is obsolete.
- **Scope**: Gather / build / repair loops and store one-shots in all mods.

**Fix: maps with only starting_squares always used a fixed spawn**

- **Issue**: AoE2 DE multiplayer maps list ``starting_squares`` and omit ``starting_units`` (race defaults). Empty slots dropped the square, so faction town centers / villagers always used ``starting_squares[player_index]``. ``random_starts 1`` did not shuffle.
- **Change**: Each spawn slot remembers its square. Default random starts shuffle those squares, then race defaults land on the drawn one. ``random_starts 0`` still uses list order.
- **Scope**: All maps that use ``starting_squares`` without per-slot units (including aoe2).


1.4.8.1
--------

**Improvement: sheep claim range matches AoE2 DE (4 m + collision radii)**

- **Issue**: Sheep used ``claim_range 12000`` (a full 12 m square), far beyond DE’s ~4-tile search radius. The 12 m square is a navigation cell for blind play; coordinates stay continuous at about 1 m per tile. Claims compared centers only, with no collision radii.
- **Change**: Sheep use ``claim_range 4000`` (~4 m). Claim/steal is edge-to-edge: center distance ≤ ``claim_range`` + both ``radius`` values (175 mm each when collision is on).
- **Scope**: Base rules and aoe2 sheep; all ``claimable`` livestock that set ``claim_range``.

**Fix: numeric save/replay names were spoken as tts.txt IDs**

- **Issue**: Renaming a save to ``1`` said “you are” (tts.txt id 1) instead of the number 1. Replays had the same bug.
- **Change**: Player-chosen save and replay names (including delete confirm) use ``literal_text_msg``. Auto ``replayN_timestamp`` names and old long timestamp-only files still speak the time and index.
- **Scope**: Load-game and replay menus.


1.4.8.0
--------

**Fix: pickup buff TTS used millihitpoints as the spoken number**

- **Issue**: On td2, picking up a sword said melee damage +7000000. Rules ``stat mdg`` / ``v 7000`` store 7_000_000 millihp; the announcement treated that internal value as the display amount.
- **Change**: Temporary buffs divide precision stats (hp, mdg, and so on) by ``PRECISION`` before TTS. Production accumulators stay in display units.
- **Scope**: Buff-gained TTS in all mods.

**Computer: lure retaliating huntables to a food drop-off before the kill**

- **Issue**: Idle workers attacked ``is_huntable`` animals in place. Boars with ``pursue_attacker`` fight back in the field. There was no hit-once-and-drag-home behaviour.
- **Change**: A huntable that is not ``herdable`` / ``claimable`` and has ``pursue_attacker`` (aoe2 boars) is hit once, then the villager runs to a building that stores resource 3 (town center, mill, and so on) and kills it there. Non-retaliating huntables (deer) are still killed in the field. Sheep are still herded to the drop-off. No type-name checks. The runner does not turn around to fight on the way home.
- **Scope**: Computer players; mods that use those rule flags (including aoe2).

**Hotkey map: resource 4 status**

- **Issue**: aoe2 already bound stone to Shift+X, but the remap catalog only listed resources 1–3.
- **Change**: Global and classic catalogs include resource 4 status. aoe2 default remains Shift+X.
- **Scope**: Hotkey remapping; TTS id 5508.

**Classic bindings: Right Shift+C / B copy the secondary voice**

- **Issue**: Layered hotkeys could copy secondary speech to the clipboard; classic ``legacy_bindings.txt`` had no matching keys.
- **Change**: ``res/ui`` and ``mods/aoe2/ui`` ``legacy_bindings.txt`` add Right Shift+C copy and Right Shift+B append-copy of the secondary voice.
- **Scope**: Classic hotkey scheme.


1.4.7.9
--------

**Improvement: sheep claim/steal names the taker's civilization and relation**

- **Issue**: Claiming or stealing a sheep always said “sheep , claimed”, so you could not tell which civilization took it.
- **Change**: Own claims stay short. An enemy take (if you can see the claimer) says “sheep claimed Byzantines , enemy”; an ally take names the civ and “ally”. Single-faction mods omit the civ name but still say enemy/ally. No announcement in fog if you cannot see the claimer.
- **Scope**: Client TTS; all mods with ``claimable`` livestock (including aoe2 sheep).

**Improvement: capturing buildings speaks the name and count (same as death alerts)**

- **Issue**: Capture only played a sound, with no TTS for which building was taken.
- **Change**: Losing your own: “1 town hall occupied”. Taking an enemy’s: “1 town center captured”. Several of the same type in one burst: “2 barracks occupied / captured”. Count rules match death: numbered types include the count; ``no_number`` uniques omit “1”. Watching others capture still only plays the sound.
- **Scope**: Client TTS; all capturable buildings (including aoe2 walls, gates, town centers).


1.4.7.8
--------

**Fix: server still listed a match as in progress after it ended**

- **Issue**: After a multiplayer match, the client sometimes never sent ``quit_game`` (score TTS error, map load failure, or the command ran only after the recap). If anyone was still in the lobby, the room stayed on the in-progress / spectate list.
- **Change**: Unregister the room before score TTS; send ``quit_game`` again when leaving the match UI if it was not sent. Lobby commands and a server sweep close rooms with no one still playing. A duplicate ``quit_game`` from the lobby is ignored (no warning).
- **Scope**: Multiplayer server and client.

**Packaging: Windows install no longer duplicates Tcl/Tk**

- **Issue**: ``tcl8`` / ``tcl8.6`` / ``tk8.6`` existed both at the install root and under ``share/``, identical copies, about 5 MB extra.
- **Change**: Keep only the cx_Freeze copy under ``share/``; the update window prefers ``share/``.
- **Scope**: Windows package.


1.4.7.7
--------

**Engine: building garrison volley (rules-driven, weapon-agnostic)**

- **Issue**: aoe2 empty Town Centers still fired (building pierce damage), unlike DE. Teuton empty-TC +5 shots and Malian Tigui +8 could not be expressed in rules. A field named arrows would not fit a cannon building.
- **Change**: With ``garrison_shots 1``, shots = ``base_shots`` + firing garrison units, capped by ``max_garrison_shots`` (default 10). Empty buildings with ``base_shots 0`` do not fire; Teutons use ``base_shots 5``; Tigui uses existing ``effect bonus base_shots 8``. Damage type is still the building’s ``rdg`` (arrow, cannon, or other ranged). The volley is the building’s, not passenger shots. The engine does not test civilization names.
- **Scope**: All mods; aoe2 Town Centers enable it. Castles and towers still fire when empty.

**aoe2: Malians**

- **Issue**: The mod had no Malians civilization.
- **Change**: Thirteenth civ. Buildings −15% wood except farms; barracks militia/spearman lines +1/+2/+3 pierce armor Feudal/Castle/Imperial (not Gbeto); villagers drop off +10% gold; team university research 80% faster (``team_on_phase`` + ``time_cost -44%``). Unique unit Gbeto; Castle tech Tigui (200 food 300 wood, Town Center ``base_shots`` +8); Imperial tech Farimba (cavalry melee +5). Faction intro ``8532``.
- **Scope**: aoe2 mod.

**aoe2: civ building shells had no style titles**

- **Issue**: Rule shells such as ``malian_barracks`` did not inherit titles, so finished buildings were nameless. Teuton farms/Town Centers and the Byzantine monastery also lacked ``style.txt`` ``is_a``.
- **Change**: Give those shells ``is_a`` pointing at the generic building; a test requires later civ shells to have titles.
- **Scope**: aoe2 UI style.


1.4.7.6
--------

**aoe2: twelve civilization bonuses aligned to current Definitive Edition**

- **Issue**: Civ bonuses still matched a ~2022 snapshot (for example Chinese techs 10/15/20%, Town Centers 10 population), not current DE. The engine also could not express team-shared research, stealing guarded flock, or pooled age cost discounts.
- **Change**: All twelve civs (Britons, Franks, Chinese, Mongols, Byzantines, Japanese, Teutons, Vikings, Vietnamese, Portuguese, Aztecs, Celts) now use current DE bonuses and team bonuses. Where rules were not enough, the engine gained rules-driven fields with no civ type-name checks: ``team_on_phase``, ``grant_tech_on_phase``, ``team_share_research`` (tech plus optional host buildings, e.g. Vietnamese Imperial Skirmisher for allies), ``team_farm_food_pct``, ``reveal_enemy_town_centers``, ``research_cost_zero_slot`` / ``research_time_percent``, gather ``gather_byproduct``, team conversion resist, and so on.
- **Scope**: aoe2 mod; the new race fields are available to other mods.

**Engine: claim / steal herdables (rules-driven)**

- **Issue**: ``claimable`` proximity ownership was not wired into the unit loop. AoE2 “cannot steal a guarded flock / can steal an unprotected flock through guards” had no rules knobs.
- **Change**: Neutral ``claimable`` animals join a nearby non-neutral player. Owned flock can be stolen: anyone if unguarded; blocked if a living owner unit stands by; race ``herdable_steal_ignore_guards 1`` ignores that guard; ``herdable_steal_protected 1`` (default 0) blocks the ignore-guards bonus on your own animals. The engine does not test civilization names.
- **Scope**: All mods; aoe2 Celts enable both flags.

**aoe2: Dark Age start matches AoE2 (including Chinese)**

- **Issue**: Default start was 1 villager, a house, and no scout. Chinese used 4 villagers ( +3 vs a 1-vil baseline), not DE’s 6 villagers plus scout.
- **Change**: Standard civs: Town Center + 3 villagers + scout cavalry. Chinese: 6 villagers + scout (−50 wood, −200 food, TC 15 population). Aztecs: 3 villagers + eagle scout, +50 gold. No starting house (population from the Town Center). Campaign map scripts and AI difficulty extra villagers are unchanged.
- **Scope**: aoe2 race default ``starting_units`` / ``starting_resources``.

**aoe2: faction-picker intros in every locale pack**

- **Issue**: Civilization G-key blurbs existed only in English and Chinese.
- **Change**: Ids ``8520``–``8531`` are in every aoe2 UI pack (en, zh, de, fr, es, it, ru, be, pl, cs, sk, pt-BR, vi).


1.4.7.5
--------

**Fix: worker default order on a damaged building was not repair**

- **Issue**: The hunting change made any living owned target default to ``go``. Damaged friendly buildings (and unfinished sites) hit that branch, so a worker walked there instead of repairing.
- **Change**: Resolve default repair first for building sites and ``is_repairable`` targets with ``hp < hp_max`` (still requires ``can_repair`` / ``can_build``; enemies excluded). Intact buildings, wildlife, and enemies still default to ``go``.
- **Scope**: Worker default orders in all mods.


1.4.7.4
--------

**Performance: opening F-key speed (client loop)**

- **Issue**: Early-game crowds plus first-time OGG decode of footsteps/ambient could stall the client for a long frame, delaying the next world ask and dropping F-key relative speed.
- **Change**: Drain server notifies on a short time budget (leave ``voila`` for the next frame); spread unit animation across frames; decode footstep/ambient SFX (priority ≤ −10) on a background thread and never steal mixer channels for them.
- **Scope**: Local client in all mods.

**SFX rate limits: fire/hit, order ack, footsteps, looping noise**

- **Issue**: Dense combat or many units on one square still ran every notify / animate for sounds the mixer cannot stack.
- **Change**: Fire/hit at most 16 per tick (8 per square); ``order_ok`` / ``order_impossible`` 2 per tick; footsteps 8 per animation wave (4 per square); looping noise at most 3 per unit/building type (types do not share a cap; no global type ceiling). Death, falling, HP proportion, and own-unit-attacked alerts are not capped.
- **Scope**: Local client in all mods.

**Fix: hit, HP proportion, and death SFX sometimes silent**

- **Issue**: Skipping on-thread OGG decode for combat SFX avoided hitches but returned silence when the sound was not cached yet.
- **Change**: The play path never decodes on the client loop. Combat styles (hit / ``proportion_*`` / death, and so on) are prefetched in the background when a type appears; a miss is retried from a short pending queue. Event bursting is kept.

**Fix: no opening square coords or summary after the objective**

- **Issue**: The first camera refresh skipped speech to avoid TTS decode hitching animation, queued the line, and never spoke it.
- **Change**: After draining server events, speak the opening square once (coords, terrain, peasants / houses / town hall / gold mine, and so on).

**Fix: default barracks menu trained dark archers instead of archers**

- **Issue**: AoE2-style train-line resolution treated any ``can_upgrade_to`` as the next form the building should train. Vanilla archer→darkarcher (mage tower morph) was remapped onto barracks.
- **Change**: Only forms with ``line_upgrade`` / ``no_auto_upgrade`` replace the train slot (AoE2 militia→man-at-arms lives in that mod’s rules). Default barracks still train archers; dark archers remain an upgrade of existing archers. Mod features must not rewrite the base game or other mods’ menus.

**Fix: Options → secondary voice library spoke 5762 and 5778**

- **Issue**: Opening the secondary voice editor from Options read TTS ids ``5762`` / ``5778`` as literal digits instead of “secondary voice library” and the control hint.
- **Change**: Resolve msgparts before speaking. The editor is a normal submenu list; feedback uses the menu voice so a muted secondary channel does not feel like an empty screen.


1.4.7.3
--------

**Performance: computer AI turn counts and plan memo**

- **Issue**: With many computers in one game, ``Computer.play`` repeatedly full-scanned ``nb`` / ``future_nb`` and recomputed get-line building / wood-reserve helpers many times per turn, so wall time barely kept up with game time.
- **Change**: Build a per-AI-turn unit type index; drop expensive class checks in ``check_type``; memoize plan helpers (pending makers, wood reserve, and so on) for the turn and invalidate them after train/build orders. Combat throttle and perception semantics are unchanged.
- **Scope**: Computer players in all mods.

**aoe2: computer AI staged by age — trains and attacks**

- **Issue**: ``mods/aoe2/ai.txt`` still mixed multi-age army tokens on one get line (res-style). Food banking deferred the current wave’s soldiers, then watchdog skipped unfinished gets, so computers barely trained or attacked.
- **Change**: Stage aoe2 scripts by Dark / Feudal / Castle get waves; do not let watchdog skip dark-age eco banking early; keep feudal army on the current line from being held for later castle needs; after castle, bank wood for the siege workshop without freezing farms or age-appropriate troops. Civ scripts and difficulty knobs updated accordingly.
- **Note**: Age-up can share engine helpers with other mods, but aoe2’s banking / wave staging follows its own ruleset — other age-based mods need not behave the same way.

**Fix: default res computers built barracks but never trained**

- **Issue**: AoE2 “unpaid maker” wood banking treated unit→unit makers (``darkarcher`` ← ``archer``) and land-map shipyards as buildings to save for, so footmen/archers stayed deferred after barracks finished.
- **Change**: Unpaid makers must be real buildings; on land-only maps, skip water units / docks. Default res trains and attacks once barracks are up; AoE2 post-castle workshop wood banking is unchanged.

**Fix: computers stuck on feudal army get — never reach castle / rams**

- **Issue**: Plans intentionally keep the current feudal army wave from clicking Castle Age. When soldiers die at the enemy base, the get count never completes. Meanwhile ``_watchdog_should_wait`` treated later-wave workshop wood and ongoing trainer food/wood as “still progressing,” constantly resetting the stuck-line timer, so watchdog never skipped the feudal get and the later castle wave (blacksmith, Castle Age, workshop, rams) never started.
- **Change**: When the current get line no longer needs an age but a later plan wave still needs Castle, pause the timer only for unpaid current-line production buildings (barracks / range, and so on)—not for later workshop wood or trainer food/wood. Siege get lines still pause correctly while an owned workshop waits on ram wood.
- **Scope**: Computer players in all mods (not one aoe2 civ). Any aoe2 script shaped “feudal army → castle troops / siege” benefits.

**Fix: computers never walk owned sheep to the town center before slaughter**

- **Issue**: Many mods (including aoe2) leave villagers at ``can_herd 0`` and rely on ``claimable`` proximity ownership. Computers neither ordered owned sheep as controllable units to a food drop-off, nor kept them out of ``auto_explore`` / attack waves, so livestock wandered or were killed in the field instead of leaving ``food_livestock`` at the town center for gathering.
- **Change**: Owned livestock (``herdable`` / ``claimable``) ``go`` themselves to a food-storing building (town center, and so on); villagers slaughter only there, then gather. Neutral claimable sheep are approached with ``go`` to claim first. Livestock are excluded from explorers and idle fighters. Does not require ``can_herd``; the existing herd-follow path remains.
- **Scope**: Computer players in all mods; aoe2 sheep and Mongol pasture spawns benefit.


1.4.7.2
--------

**aoe2 / engine: trebuchet pack / unpack (rules-driven) + proportion progress**

- **Issue**: Packable siege units only delayed the first shot after moving; there was no real packed/unpacked state, no menu wording aligned with AoE2, and no ``proportion_*`` progress during the transition.
- **Change**: Rules ``packable``, ``unpack_time`` / ``pack_time``, optional ``packed_mdf`` / ``packed_rdf``, ``spawn_packed``. Packed = move only; unpacked = attack only; move auto-packs, attack auto-unpacks; stop cancels. Progress via ``completeness`` → ``proportion_*``. UI: pack / unpack (Chinese **打包** / **拆包**).
- **Docs**: ``mod/modding.htm`` (all locales with a modding chapter).

**aoe2: Mongols lose the mill (AoE4-like pastoral food)**

- **Issue**: Mongol herdsmen still built mills and listed farm mill techs, while pastures already replaced farms.
- **Change**: ``mongol_herdsman`` cannot build ``mill`` or research Horse Collar / Heavy Plow / Crop Rotation. ``pasture`` requires ``town_center`` only and stores food (``resource3``).
- **Docs**: ``player/hunting.htm``, ``mods/aoe2/SOURCES.md``.

**aoe2 fix: duplicate Horse Collar / Heavy Plow / Crop Rotation on villagers**

- **Issue**: Peasant ``can_use_tech`` listed both the generic mill farm techs and the Frank 0-cost aliases (``frank_horse_collar`` and so on). The aliases share titles with the generic techs, so the attributes screen spoke each name twice.
- **Change**: Non-Frank villagers keep only ``horse_collar`` / ``heavy_plow`` / ``crop_rotation``. Franks use ``frank_villager``, whose farm techs are the free aliases only.

**Fix: ``gather_byproduct`` (e.g. Paper Money) missing from the attributes screen**

- **Issue**: The effect is a triple (deposit, rate). The UI parsed it as a pair, treated the deposit name as the value, dropped the rate, and hid the row.
- **Change**: The screen shows deposit name, byproduct resource, and rate per second (Paper Money: wood deposit, gold, +0.014/s). Rules still name the deposit type (e.g. ``wood``).

**New: hear civilization bonuses while picking a faction**

- Arrow keys speak only the faction name. With an ``intro``, press **G** for a submenu and use up/down to hear one sentence at a time (Enter repeats the line; Esc returns). Mods without ``intro`` are unchanged.
- aoe2: all twelve civs have English and Chinese blurbs. Indented continuation lines in ``tts.txt`` are one menu line each.

**aoe2: shepherds vs hunters use separate carcass deposits (rules-driven)**

- **Issue**: Sheep and deer/boar both used ``food_carcass``, so Britons' shepherd bonus and Mongols' hunter bonus each sped up both jobs.
- **Change**: Herdables drop ``food_livestock``; huntables keep ``food_carcass``. Britons: ``gather_time_food_livestock -20%``. Mongols: ``gather_time_food_carcass -29%``. Engine matches ``gather_time_<deposit>`` and AI hunt ability from rules (``food_deposit`` / ``is_huntable``) — no civ-name hardcoding.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm`` (hunting summary).

**New: ``pursue_attacker`` — boar lure across squares (AoE2-style)**

- **Issue**: Boars counterattacked in ``guard`` mode but ``AttackAction`` only chased across squares in ``chase`` mode, so a villager leaving the tile dropped the chase and TC lure failed.
- **Change**: Rules flag ``pursue_attacker 1`` keeps the attack action following across squares (no diplomatic enmity required). Boars in base and aoe2 rules enable it; deer/sheep still ``flee_on_hit``.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**New: ``pursue_leash_range`` — deaggro when outrunning the boar**

- **Issue**: With ``pursue_attacker`` alone, chase stuck via ``last_attacker`` even after opening a large gap (not AoE2-like LOS deaggro).
- **Change**: Rules int ``pursue_leash_range`` (mm; ``0`` = unlimited). Beyond it, forget the attacker, stop the attack, and walk home. Boars use ``48000`` (~4 squares).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**New: ``claimable`` + pasture spawn (AoE2 claim / AoE4 pasture, rules-driven)**

- **Issue**: Herding only followed without changing ownership, so AoE2-style sheep claim and AoE4-style breeding pastures were not available as optional mod rules.
- **Change**: Neutral ``claimable`` animals join any nearby non-neutral player's units (``claim_range``; keeps ``can_herd`` separate). Buildings may use ``spawns_unit`` with ``spawn_player_cap`` / ``spawn_immediate`` (aoe2: sheep ``claimable``; Mongol ``pasture``).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.


1.4.7.1
--------

**Fix: unfinished buildings could train units**

- **Issue**: A construction site (``BuildingSite``) exposed the target building's train/research menu, so barracks could train before they finished.
- **Change**: Unfinished sites have empty train/research lists and cannot run production.
- **Scope**: All mods (including aoe2).
- **Code / tests**: ``world_build_rules.py`` (``is_unfinished_building``, ``effective_can_train`` / ``effective_can_research`` / ``building_can_operate``); ``test_can_train_upgrade.py``.

**Fix: completed buildings spawned below civ/age bonus HP**

- **Issue**: Completion wrote current HP from the rules class ``hp_max`` (e.g. barracks 1200), while instance ``hp_max`` already included bonuses (Byzantine Dark Age +10% → 1320). Villagers then auto-repaired the gap.
- **Change**: On complete, current HP uses instance ``hp_max`` (minus damage taken during construction). Matches AoE2: finish at full bonus HP, not repair up to it.
- **Scope**: All mods.
- **Code / tests**: ``worldcreature.py`` (``BuildingSite._complete_construction``); ``test_z5_byzantine_barracks_hp.py``.

**aoe2: Celts civilization; William Wallace campaign plays as Celts**

- Celts: UU Woad Raider; UTs Stronghold / Furor Celtica; infantry speed, lumberjack, and siege-fire bonuses.
- Wallace campaign: player ``default_faction celts``; English computers ``faction britons`` (no longer playing England as the Scots).
- Maps: ``computer_only … faction <name> …`` assigns a civilization per computer. See ``mod/mapmaking``.


1.4.7.0
--------

**Improvement: map-browse path SFX overlaps coordinate speech**

- **Issue**: When arrow-key browsing the map, terrain pass (e.g. bridge) or block cues were queued on the voice channel and finished before square coordinates / place names, so feedback felt laggy.
- **Change**: Pass/block cues play immediately on the SFX mixer; coordinates and names still use the voice queue, so both start together instead of waiting in line.
- **Scope**: Normal map browse, zoom square crossing, first-person block feedback.
- **Code**: ``clientgame/game_navigation.py`` (``_play_movement_sfx``), ``clientgamefocus.py``, ``clientgame/game_audio.py``.


**New: rules-driven kill resource reward ``kill_resource_vs`` (not gold-hardcoded)**

- **Use**: when the killer slays a matching unit type, grant a **chosen resource slot** (e.g. Chieftains gold on villager kills) — the engine does **not** hardcode “gold” or ``resource1``.
- **Syntax**: ``effect bonus kill_resource_vs <unit_type> <resource> <amount>``, e.g. ``kill_resource_vs peasant resource1 5``. Resource may be ``resourceN`` or aliases ``gold`` / ``wood`` / ``food`` / ``stone`` (normalized to ``resourceN``). Types match via ``type_name`` / ``is_a``.
- **Storage**: ``victim_type → { resourceN: display_amount }``; on kill, ``store`` that resource and fire ``resourceN_reward``.
- **aoe2**: Chieftains uses ``kill_resource_vs … resource1 5`` (villager / trade cart / trade cog / monk).
- **TTS / UI**: “resource on kill bonus vs” (no raw ``kill_gold`` key); tech detail includes target type and resource title.
- **Docs**: ``mod/modding`` (all languages).
- **Code / tests**: ``worldmarket.canonical_resource_name``, ``effect_bonus_parse``, ``attribute_effects``, ``worldcreature``; ``test_aoe2_full_unique_techs.py``, ``test_stat_tts_names.py``.


1.4.6.9
--------

**New: rules-driven garrison heal ``heal_garrisoned``**

- **Use**: TC / castle / towers heal only units inside (AoE2-style); monks keep area auras — **no** building-name hardcoding in the engine.
- **Flag**: ``heal_garrisoned 1`` → ``heal_nearby_units`` heals ``self.inside`` passengers only; default ``0`` keeps ``heal_range`` / ``heal_radius`` behavior.
- **aoe2 rates (DE)**: TC/towers ``heal_level 1`` + ``heal_cd 10`` → 0.1 HP/s; castle ``heal_level 1`` + ``heal_cd 5`` → 0.2 HP/s; Herbal Medicine ``heal_level +5`` (×6) → 0.6 / 1.2 HP/s; targets include ``keeptower``.
- **Docs**: Chinese `skills / heal / effects <../zh/mod/skills-and-effects.htm>`_; ``mod/modding``.
- **Tests**: ``test_heal_garrisoned.py``.

**New: rules-driven projectile lead and per-lane flight speed**

- **Flight**: ``rdg_projectile_speed`` / ``mdg_projectile_speed`` are **speeds** (tiles/s), not “seconds of flight”; only when the matching ``*_projectile`` flag is set. Time-to-hit = distance ÷ speed. Shared ``projectile_speed`` and legacy ``*_delay`` are deprecated (migrated on load).
- **Lead**: ``projectile_lead 0|1`` (ranged projectiles only). No hardcoded ``ballistics``.
- **Tech / UI**: ``effect bonus projectile_lead 1``; ``effect info``.
- **Docs**: `Projectile lead & flight speed <mod/projectile-lead.htm>`_; ``mod/modding``.
- **Tests**: ``test_projectile_speed.py``.

**New: rules-driven market (buy/sell, tribute, route trade)**

- **Use**: mods choose commodities, currency, tax, tribute list, and which resources/hubs trade units use — **no** engine hardcoding of wood/food/stone or gold-only payouts.
- **Parameters** (``def parameters``): ``market_currency``, ``market_commodities``, ``market_menu_labels``, batch/tax/tribute keys, ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``, etc.
- **Unit attrs**: ``is_market``, ``is_trade_unit``, ``trade_hubs``, ``trade_rewards`` (several → pick trade type in the menu); techs ``market_tax_guilds``, ``tribute_fee_permille``.
- **Orders**: ``market_buy`` / ``market_sell`` / ``tribute`` / ``trade``; payout uses **square hops** (very short routes may pay 0).
- **aoe2**: gold currency + wood/food/stone goods; carts trade between markets for gold, cogs between docks.
- **Docs**: ``mod/market-system`` (zh/en), ``mod/modding``, ``player/market-and-trade`` (zh); ``mods/aoe2/SOURCES.md``.
- **Code / tests**: ``worldmarket.py``, ``worldorders/market.py``; ``test_aoe2_market.py``, ``test_aoe2_dock_economy.py``.

**Improvement: rename bonus filter fields to ``phase_bonus_targets`` / ``effect_bonus_targets``**

- **Primary names**: pair with ``phase bonus`` / ``effect bonus``.
- **Aliases still work**: ``phase_targets``, ``tech_effect_targets``, ``effect_targets``.
- **Docs**: ``mod/modding`` (zh/en).
- **Tests**: ``test_phase_bonus_groups.py``, ``test_effect_bonus_unit_filter.py``.

**New: dual gather modes ``gather_mode trip|continuous``**

- Default ``trip``: one ``gather_qty`` pulse then drop-off (previous behaviour).
- ``continuous``: fill ``carry_capacity`` at a per-second rate, then drop-off (AoE II/IV style).
- Rules: ``gather_mode``, ``carry_capacity``, ``carry_capacity_<type>``, ``gather_rate`` — see modding docs.
- ``mods/aoe2`` enables continuous (carry 10, hunt carcass 35).

**New: faction age rewards ``on_phase`` and ``research_cost_discount`` / ``advance_cost_discount``**

- **Use**: civ-specific age rewards on ``class race`` / ``class faction`` — **no civ names in engine code**. Shared ``phase bonus`` can stay empty.
- **``on_phase``**: when that phase is in ``player.upgrades``, apply ``effect bonus``-style stats to matching units (start + after advance; ``_phase_bonus_pool``).
- **``research_cost_discount``**: replaces research-cost % for highest matching age; ``ResearchOrder`` / ``UpgradeToOrder`` only.
- **``advance_cost_discount``**: by purchased age; ``AdvanceOrder`` only.
- **Helpers**: bare ``phase bonus`` / ``phase bonus clear``; ``no_auto_upgrade 1``.
- **Code / tests**: ``worldphase.py``, orders, ``definitions.py``; ``test_faction_age_cost_discounts.py``, etc.

**Improvement: announce the resolved faction after a random civ roll**

- **Issue**: with Random, shared names like town center / villager do not reveal the civ (sighted AoE2 uses flags).
- **Change**: speak “you are” plus the civ title only when the lobby pick was Random **and** the mod has more than one faction (after the opening objective, so scrolling does not cut it off). Manual picks and single-faction mods (e.g. base ``res``) stay silent. ``Alt+C`` (``faction_status``) uses the same rule.
- **Code**: ``faction_announce.py``, ``worldplayerbase/base.py`` (``faction_was_random``), ``clientgame/game_resources.py``, ``game_interface_base.py``; ``global_bindings.txt`` (base + aoe2).
- **Tests**: ``test_faction_status_announce.py``.

**Improvement: hear enemy civilization in multi-civ mods**

- **Issue**: shared unit names (militia, etc.) do not reveal which civ an opponent is playing.
- **Change**: with more than one faction, enemy/ally unit titles include the civ; ``F11`` player roster and diplomacy candidate selection also speak the civ after the player name (e.g. “Takumi, Britons”). Unchanged for single-faction mods.
- **Code**: ``faction_announce.py``, ``clientgameentity/properties.py``, ``clientgame/game_audio.py``.
- **Tests**: ``test_faction_status_announce.py``.

**New: abstract faction templates and ``is_a`` inheritance for starting units/resources**

- **Use**: define default ``starting_resources`` / ``starting_units`` on an abstract parent (e.g. ``Civilization``); each civ ``is_a`` that parent. Child overrides win; omitted fields inherit. Maps without starting units still get race defaults so games do not end immediately.
- **``abstract 1``**: inheritance-only template — **hidden from the faction picker**; ``abstract`` is not copied to children.
- **Inheritance**: ``class race`` equals ``class faction``; ``is_a`` chains work. Explicit map ``starting_units`` / ``starting_resources`` still take priority.
- **Code**: ``definitions.py`` (skip ``abstract`` in ``apply_inheritance``; filter abstract in ``factions``).
- **Tests**: ``test_faction_starting_inheritance.py``.

**Improvement: isolate maps and campaigns when a mod is active (no ``res`` fallback)**

- **Issue**: if a mod had no own ``multi/`` maps or ``single/`` campaigns, menus still listed base ``res`` content.
- **Change**: with any mod enabled, only ``mods/<mod>/multi`` and ``mods/<mod>/single`` are listed; if the mod has none, the lists are empty — **no** fallback to ``res/multi``, ``res/single``, or downloads. Unchanged with no mod.
- **Code**: ``lib/resource.py`` (``_get_multi_maps`` / ``_add_custom_multi`` / ``_campaigns``); spectator default avoids empty-list index (``game.py``).
- **Tests**: ``test_mod_map_campaign_isolation.py``.

**Fix: race ``starting_resources`` ignored when the map omits them (start at 0)**

- **Issue**: factions set ``starting_resources`` in rules (e.g. ``100 200 200 200``), but maps without that line still started at 0.
- **Cause**: ``_parse_map`` pre-filled ``[0, 0, …]``; ``populate_map`` only falls back to race defaults when the resource list is empty — all zeros are not empty.
- **Fix**: leave an empty list ``[]`` until the map defines ``starting_resources``, then apply race/faction defaults; an explicit map line (including intentional ``0``) still wins.
- **Code**: ``world/world_map.py``.
- **Tests**: ``test_race_starting_resources.py``.

**Fix: commenting out ``LSHIFT C`` / ``LSHIFT B`` still copied speech in-game**

- **Issue**: ``global_bindings.txt`` comments out Left Shift+C/B (primary voice-library copy / append) by default, but the keys still worked in a match.
- **Cause**: ``game_input_handler`` called ``voice_libs.handle_hotkey`` before bindings, bypassing the hotkey table.
- **Fix**: in-game Shift+C/B follow **bindings only** — a leading ``;`` disables them. Menus keep the hardcoded Left/Right Shift+C/B. Right Shift+C/B (secondary library) stay enabled by default.
- **Code**: ``clientgame/game_input_handler.py``; menus via ``clientmenu.py`` / ``voice_libs.handle_hotkey``.
- **Tests**: ``test_lshift_rshift_bindings.py``.

**Improvement: StarCraft gas aligned with Brood War (worker trips + ``gather_slots``)**

- **Mechanism**: gas buildings no longer fill via ``auto_production``; workers trip-gather from the structure (default ``extraction_qty`` 8, depleted ``2``), debiting ``source_qty``.
- **``gather_slots 3``**: at most 3 workers extract at once (extras wait); more workers still produce gas via rotation, but throughput ≈ 3. **Tip: put 3 workers on each gas.**
- **Build fields**: Pylon / Assimilator ``requires_build_field 0``; Photon Cannons need psi and do not attack while unpowered.
- **Docs**: ``player/starcraft-resources`` (zh/en/es/it/pt-BR), ``mod/modding`` (Deposits & gas), ``mods/starcraft/readme.txt``.
- **Code**: ``world_extractor.py``, ``worldorders/gathering.py``, ``definitions.py``, ``worldplayercomputer.py``, ``mods/starcraft/rules.txt``.

**Improvement: AoE2 monastery conversion techs are rules-driven (no tech-name hardcoding)**

- **Issue**: Redemption / Atonement / Heresy / Faith / Theocracy checked string names like ``"redemption"`` in the engine.
- **Change**: generic attrs (``conversion_allows_*``, ``conversion_victim_dies``, ``conversion_channel_*``, ``conversion_rest_only_success``, ``conversion_tech_gated``, ``conversion_cleric``, ``conversion_immune``); engine reads attrs only.
- **aoe2**: those techs and monk / immune buildings are wired; attributes UI still uses ``effect info``.
- **Code**: ``world_conversion.py``, ``worldskill.py``, ``definitions.py``, ``mods/aoe2/rules.txt``.
- **Tests**: ``test_aoe2_monastery_techs.py``.


1.4.6.8
--------

**New: auto-cast skills on death/destruction (``trigger_timing on_death``)**

- **Use**: units or buildings can trigger extra effects when they die — e.g. an ammo depot exploding for area damage; also death summons, short ``class effect`` deploy, etc.
- **Setup**: on a ``class skill``, set ``auto_trigger 1``, ``manual_use 0``, ``trigger_timing on_death``, then attach it with ``can_use_skill`` (or legacy ``death_trigger_skills``). Example: ``effect harm_area 40 6`` (flat damage 40, radius 6); ``effect deploy`` / ``summon`` / ``buffs`` and other existing effect types also work.
- **Behavior**: fires in ``die()`` before the entity is deleted; allows HP already at 0; **skips mana and cooldown** (no wind-up); centers on self (prefer ``effect_target self`` for AoE); chain kills can fire further ``on_death`` skills. Different from attack suicide ``mdg_explode`` / ``rdg_explode`` (those only fire when the unit attacks). The same skill may be ``manual_use 1`` + ``on_death`` (e.g. ammo depot self-detonate): a successful manual cast is recorded so the ensuing self-kill does **not** explode again; enemy destruction still fires once.
- **Code**: ``worldunit/world_attributes.py``, ``worldunit/worldcreature.py``, ``worldskill.py``.
- **Docs / tests**: ``GENERIC_SKILL_SYSTEM.md``; ``test_death_skills.py``, ``test_level_skills.py``.


1.4.6.7
--------

**Fix: attacking a neutral story NPC did not make them hostile (army would not auto-attack)**

- **Issue**: e.g. Raynor campaign ch. 25 — royal guards fought back after being hit, but ``neutral`` stayed set, so offensive/chase units still treated them as passive creeps and would not auto-engage.
- **Cause**: duel start only ran ``set_ai_mode offensive`` and never cleared ``Player.neutral``; combat AI intentionally skips neutrals via ``player_is_a_hostile_enemy`` / ``can_attack``.
- **Fix**: new trigger ``(set_neutral 0|1 [player])``; neutrality is tied to guard — switching to offensive/defensive/chase (UI or ``set_ai_mode``) clears ``neutral``; being hit by a non-neutral side also clears it; ch. 25 sets ``set_neutral 0`` at duel start and ``set_neutral 1 computer1`` after declining an alliance (restore guard).
- **Code**: ``worldplayerbase/base.py``, ``triggers.py``, ``worldorders/immediate.py``, ``combat/damage_effects.py``, ``res/single/The Legend of Raynor/25.txt``.
- **Tests**: ``test_campaign_alliance_transfer_triggers.py``, ``test_neutral_no_auto_attack.py``.

**Fix: Marco’s escorts attacked Raynor during the ch. 27 duel**

- **Issue**: escorts were supposed to leave the arena, but ``_notify_guard_units`` pulled them into counterattacks; leave orders only targeted 8 of 12 escorts.
- **Fix**: new ``(set_counterattack 0|1 …)``; on duel start disable counterattack for all 12 escorts (clear ``last_attacker``), set Marco offensive, then ``imperative go`` to o1.
- **Code**: ``worldplayerbase/triggers.py``, ``res/single/The Legend of Raynor/27.txt``.
- **Tests**: ``test_campaign_alliance_transfer_triggers.py``.

**Fix: with cheat mode on, one arrow key press browsed several squares**

- **Issue**: on large maps (e.g. ch. 28) with cheatmode, Right once went a1→b1→c1→d1 instead of one step.
- **Cause**: full-map perception made ``select_square`` slow; pygame key-repeat queued multiple KEYDOWNs while the handler ran; the game loop (unlike menus) did not collapse/clear repeats.
- **Fix**: keep only the first KEYDOWN per key in a batch; ``pygame.event.clear([KEYDOWN])`` after handling.
- **Code**: ``clientgame/game_input_handler.py``.
- **Tests**: ``test_game_keydown_repeat_collapse.py``.


1.4.6.6
--------

**Fix: startup “check for updates” could miss a newer release (only Options → Check now worked)**

- **Issue**: with check-on-start enabled, a newer GitHub release sometimes produced no prompt after launch, while Options → Check for updates now found it.
- **Cause**: the HTTP request may take up to about 20 seconds, but the main thread only waited about 8 seconds; a timeout was treated as “up to date”, and a late background result was never offered.
- **Fix**: start the background check earlier (overlap media init); wait until the check actually finishes (~30s); if still unfinished, fall back to the same synchronous check as the Options menu.
- **Code**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``.
- **Tests**: ``test_auto_update.py`` (timeout / sync-fallback cases).

**Improvement: visible update prompts for sighted players**

- **Issue**: update prompts were voice-only; the game window showed no text or buttons.
- **Change**: confirmation dialogs show on-screen text plus Yes/No buttons (mouse-clickable); changelog text is shown while spoken; status banners for checking / up to date; try to raise the game window to the foreground.
- **Code**: ``pygame_ui.py`` (``show_confirm`` / ``draw_confirm``), ``clientmenu.py`` (``confirm_yes_no``), ``clientversion.py``.

**Fix: choosing “read the update notes” after an update prompt did not speak the release notes**

- **Issue**: after a newer release was found and confirmed, answering yes to the changelog prompt produced no notes (or they were cut off at once by “press Enter to continue updating”), even though the GitHub Release body was fetched correctly.
- **Cause**: ``literal_text_msg`` already returns a list and was wrapped again, so TTS could not parse it; non-blocking ``voice.item`` was immediately preempted by the continue prompt.
- **Fix**: speak the notes with blocking ``voice.menu(literal_text_msg(...))`` (finish or skip with a key), then ask to continue updating.
- **Code**: ``clientversion.py``.
- **Tests**: ``test_auto_update.py`` (``test_offer_update_speaks_changelog_body``).

**Fix: translation shift in multilingual TTS (key ``5750``)**

- **Issue**: in German / Spanish / French / Italian / Brazilian Portuguese UI strings, key ``5750`` (language) was wrongly set to “one vs many”-style text after a line shift.
- **Fix**: correct ``tts.txt`` under ``res/ui-de``, ``ui-es``, ``ui-fr``, ``ui-it``, and ``ui-pt-BR`` so ``5750`` reads as language (Sprache / idioma / langue / lingua / linguagem).

**Fix: multilingual TTS audit (missing ids and clear mistranslations)**

- **Issue**: several UI languages lagged behind English ``tts.txt`` (about 27 newer ids such as impassable ground/air, threat attributes, victory countdown, accessibility voice, system default language), and some entries were wrong or conflated (e.g. Italian footman as farmhand, stealth as invisible, rally as reorganize; Spanish/Portuguese stealth as “stolen”; German rally as “you command”; population vs food sharing one word; speech rate colliding with unit speed; long voice-library help left in English).
- **Fix**: fill missing ids for ``ui-it``, ``ui-fr``, ``ui-es``, ``ui-de``, ``ui-pt-BR``, ``ui-ru``, ``ui-pl``, ``ui-cs``, ``ui-sk``, ``ui-be``, ``ui-vi`` (Chinese was already complete); correct clear mistranslations across those packs; translate leftover English voice-library / update help strings where they were still untranslated.
- **i18n sync**: ran ``python tools/i18n/extract_pot.py`` so ``i18n/tts.pot`` and each ``i18n/tts-*.po`` match ``res/ui-*/tts.txt``; running ``build_tts.py`` afterwards will not wipe these updates.
- **Files**: ``res/ui-*/tts.txt``, ``i18n/tts.pot``, ``i18n/tts-*.po``.


1.4.6.5
--------

**Fix / new: StarCraft gas depletes (generic extractor buildings)**

- **Issue**: Assimilator / Extractor / Refinery produced unlimited vespene at ``production_qty`` (default 8) after building on a geyser — unlike StarCraft.
- **Rules**: geysers have a reserve (default ``deposit_volume 5000``; map ``geyser 1`` is a build marker that uses that default, or write ``geyser 5000``); each production cycle debits the reserve; when empty, yield drops to ``depleted_production_qty`` (default 2).
- **Generic keywords** (reusable for other mods, e.g. gold-vein extractors):
  - ``is_an_extractor 1`` — on completion, take over deposit reserve and debit on production
  - ``deposit_volume N`` — default deposit reserve
  - ``depleted_production_qty N`` — per-cycle yield after empty (``0`` = stop)
  - Still uses existing ``requires_deposit``, ``production_type`` / ``resource_type``, ``is_gather``, ``auto_production``
- **Code**: ``world_extractor.py``, ``worldcreature.py``, ``world_status_update.py``, ``worldorders/production.py``, ``definitions.py``, ``randommap.py``, ``mods/starcraft/rules.txt``.
- **Tests**: ``test_extractor_depletion.py``, ``test_build_rules.py``.
- **Docs**: player StarCraft resources guide, modding (Deposits & gas), ``mods/starcraft/readme.txt``, release notes.

**Improvement: larva/hatchery spawning is now generic ``spawns_unit`` (no hardcoded type names)**

- **Issue**: the engine keyed off ``type_name == "hatchery"`` / ``"larva"`` for auto-spawn and inject morph speed — other mods could not reuse it.
- **Approach**: buildings use ``spawns_unit \<type\>`` + ``larva_cap`` + ``larva_spawn_time``; inject-style buffs apply to the same-square host that spawns the morphing unit. StarCraft ``hatchery`` sets ``spawns_unit larva``. ``larva_cap`` alone still defaults to spawning ``larva`` (compat).
- **Code**: ``world_build_rules.py``, ``worldorders/production.py``, ``world/world_game.py``, ``worldplayerbase/base.py``, ``mods/starcraft/rules.txt``.
- **Tests**: ``test_starcraft_larva.py``, ``test_build_rules.py``.
- **Docs**: modding (Unit spawn hosts), release notes.

**Fix: Ctrl+F2 top-down view spamming ``X.place is None``**

- **Cause**: after a building site finishes, a geyser is consumed, or a unit is deleted, the entity briefly stayed in perception/memory and the map warned every frame.
- **Fix**: purge placeless models during fog sync; do not draw/warn about ``place is None`` objects on the map.
- **Code**: ``clientgame/game_navigation.py``, ``clientgamegridview.py``.
- **Tests**: ``test_purge_placeless_fow.py``.


1.4.6.4
--------

**New: Options → Check for updates now**

- If startup update checks are turned off, you can still check GitHub manually from Options; a newer release uses the same confirm flow as the startup prompt.
- Announces when you are already up to date, or if the check fails.

**Improvement / fix: Windows packaged builds use a standalone update window (with progress)**

- **Issues**: downloading inside the game UI caused “Not Responding”; an early external updater that imported full ``auto_update`` (and thus ``config`` / ``resource``) could hang on “Loading updater…”; ``tasklist | find "pid"`` in the apply script could be hijacked by Git’s GNU ``find``, spamming ``find "xxxxx"`` and stalling install.
- **Approach**: after confirm, the game exits and ``soundrts.exe --soundrts-update`` opens a standalone **SoundRTS Update** window for download/extract with a progress bar. Download/apply helpers live in stdlib-only ``update_core.py`` (no game config/resource imports). ``apply.bat`` waits via ``tasklist`` only (**no** ``find``), then ``robocopy`` overwrites the install (skipping ``user``) and relaunches. Staging remains under ``user/tmp/`` (or ``%APPDATA%\\SoundRTS\\tmp/``).
- **Code**: ``update_window.py``, ``update_core.py``, ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``soundrts.py``, ``msgparts.py``, per-language ``tts.txt`` (``5794``–``5798``).
- **Tests**: ``test_auto_update.py``.
- **Docs**: player manuals, getting started, release notes.

**Fix: lag when browsing the Voice libraries menu with arrow keys**

- **Symptom**: Options → Voice libraries felt sluggish on up/down even when a short row was selected, as long as a long help line stayed visible.
- **Cause**: every redraw truncated long visible lines with a linear ``font.size`` loop; a ~hundreds-of-characters help line was expensive.
- **Fix**: menu text fitting now uses binary search plus a cache, so arrow navigation stays responsive.
- **Code**: ``lib/pygame_ui.py`` (``_fit_menu_text``).
- **Tests**: ``test_voice_libs_menu_arrow_profile.py``.

**Improvement: voice-library / update-check copy moved to multilingual TTS ids**

- Some strings lived only as Chinese literals in ``msgparts.py`` (e.g. “voice libraries”, primary/secondary labels, secondary toggle, help text, “check for updates when starting the game”), so they did not follow the UI language via ``tts.txt``.
- They are now numeric ids (about ``5760``–``5793``) in ``res/ui`` and each ``ui-*`` ``tts.txt`` (full zh/en; other languages translate short labels, with English fallback for long help where needed).
- **Code**: ``msgparts.py``, per-language ``tts.txt``.


1.4.6.3
--------

**New: check GitHub for updates at startup and one-click install (Windows packaged builds)**

- On launch, the game queries the GitHub Release for ``tuohai/soundrts-ultimate-version``. If the online version is newer, you are prompted: **Enter** to update, **Esc** to cancel.
- Optionally hear the Release notes before downloading.
- **Windows packaged build**: downloads and extracts under the config ``tmp`` folder (portable ``user/tmp/``, installed ``%APPDATA%\\SoundRTS\\tmp/``), then a short script overwrites the install folder and relaunches after exit. The ``user`` folder is **skipped** so local saves/settings are kept. Temp update files under ``tmp`` are removed after a successful apply.
- **Source / development runs**: opens the Release download page only (does not overwrite the project tree).
- Options menu: **Check for updates when starting the game** (on by default; Enter toggles). Stored as ``check_updates_on_start`` in ``SoundRTS.ini``.
- **Code**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``config.py``.
- **Tests**: ``test_auto_update.py``.
- **Docs**: player manuals, getting started, release notes.

**Improvement: Ctrl+F2 large-map edge scroll and mouse-wheel zoom (Age of Empires-style)**

- **Issue**: on large maps (e.g. cw1), moving the mouse across squares jumped the camera with every hover—hard to play visually.
- **Edge scroll**: the view pans only when the pointer is at the **main map viewport edge** (Age of Empires-style). Hovering still selects squares / targets but **does not jump the camera**.
- **Mouse-wheel zoom**: scroll up to zoom in, down to zoom out (anchored under the cursor); zooming out until the whole map fits recenters it.
- **Jump-to-center**: minimap clicks and keyboard square jumps still center the view; edge scroll is disabled over the command HUD / minimap.
- **Code**: ``clientgamegridview.py``, ``clientgame/game_input_handler.py``, ``clientgame/game_navigation.py``.
- **Tests**: ``test_gridview_viewport.py``, ``test_zoom_mouse.py``.
- **Docs**: player manuals, release notes.


1.4.6.2
--------

**New: switch UI language from the options menu**

- Main menu → **Options** → **Language**: pick a language or **System default** without editing install-folder files.
- Preference is saved to the user ``language.txt`` (portable ``user/language.txt``, or ``%APPDATA%\\SoundRTS\\language.txt`` on Windows installs). Install ``cfg/language.txt`` remains a read-only fallback.
- The user file overrides ``cfg/language.txt``. Choosing **System default** writes an empty user file and ignores a forced language in ``cfg``.
- **Code**: ``clientmain.py``, ``lib/resource.py``, ``paths.py``.
- **Docs**: player manuals, getting started, mod i18n guides, release notes.

**Improvement: Ctrl+F2 selection stats / backpack & gear / large-map viewport**

- **Selection stats panel**: bottom-left portrait + HP/attack/defense/range/speed (Age of Empires / StarCraft-style; full Alt+V list remains TTS).
- **Backpack / equipment visuals**: with Ctrl+F2, open via buttons beside the selection panel; clickable item grid + Use/Unequip/Drop (Shift+V / Ctrl+V keyboard still work).
- **Large-map viewport**: big maps (e.g. cw1) no longer shrink-to-fit; cells stay near the size used on small maps, the rest extends off-screen, and the view follows the focused square (Age of Empires-style).
- The top-right minimap still shows the whole map and outlines the current viewport; left-click jumps square, right-click jumps and issues default order. Small maps still fit centered.
- **Code**: ``clientgame/game_hud.py``, ``clientgame/game_gear_hud.py``, ``clientgamegridview.py``, ``clientgame/game_input_handler.py``.
- **Docs**: player manuals, release notes.

**Fix: auto resume save failed when quitting large maps mid-game**

- **Symptom**: quitting a large map such as ``cw1-mm`` (100×100) logged ``auto save resume skipped: world too large (10000 squares)``, so “continue unfinished game” was unavailable.
- **Cause**: the save path pickled ``local_client.interface`` (pygame fonts, locks, etc.); any dump failure was then mislabeled as “world too large.”
- **Fix**: client ``__getstate__`` omits ``interface`` (UI rebuilt on load); only ``RecursionError`` / ``MemoryError`` are reported as “world too large.”
- **Code**: ``worldclient.py``, ``game.py``, ``clientgame/game_resources.py``.
- **Tests**: ``test_save_resume_pickle.py`` (including cw1-mm round-trip with a fake UI attached).


1.4.6.1
--------

**Fix / improvement: Ctrl+F2 map unit placement and art layers**

- **Fix**: main-map units/buildings were almost stuck at the top edge due to wrong world→screen conversion (minimap dots still showed); Y axis now matches square layout.
- **Mouse (display on only)**: click select; double-click same type; Shift+click add/remove; Shift+box append; empty click jumps square and clears; right-click default orders unchanged.
- **Command-card HUD**: 5×3 icon grid (bottom-right); production queue; optional ``res/ui/icons/<type_or_order>.png``.
- **Map sprites**: top-down map uses ``res/ui/map/<type>.png`` (separate from HUD icons); else colored shapes.
- **Optional unit animation**: ``res/ui/anims/<type>/`` spritesheets or optional Spine; fallback: anim → ``ui/map`` → shapes (``clientgame/game_unit_anim.py``).
- **Starter packs**: flat geometric PNGs in ``res/ui/icons/`` and ``res/ui/map/``; replace same filename to customize; regenerate via ``python tools/gen_hud_icons.py``.
- **F8 zoom + display**: current square fills the view with a sub-cell grid; mouse moves focus, selects units, box-selects, right-clicks orders onto a sub-cell.
- **Code**: ``clientgamegridview.py``, ``clientgame/game_visual_fx.py``, ``clientgame/game_input_handler.py``, ``clientgame/game_unit_control.py``, ``clientgame/game_hud.py``, ``clientgame/game_unit_anim.py``.
- **Docs**: player manuals, modding guides, layered-hotkeys.


1.4.6.0
--------

**New / improved: Ctrl+F2 visual quality (sighted top-down view)**

Compared with the old debug-style map (flat blocks, black walls, tiny dots), this release raises readability and information density:

- **Terrain and mood**: readable default colors when style has no ``color`` (plains/forest/water/mountains, etc.); high ground brightened with a slight warm bias (no harsh ×2 blowout); fog-of-war memory darkened but keeps hue; map centered with margins.
- **Structure cues**: grid lines; walls (no-exit edges) vs exits/passages drawn differently.
- **Units and resources**: distinct shapes for units/buildings/resources; team colors; selection highlight; HP bars; air markers.
- **Labels and info panel**: 1-based numeric coords (e.g. 2,7), place names and resource amounts when cells are large enough; left hover panel for terrain and unit/building basics (HP, attack/defense, etc.).
- **Readability extras**: soft fog fringes; pulsing selection; target cross + march lines; hurt/attack flashes and short particles; build/train progress rings; movement lerp (visual only).
- **Combat / gather FX**: ranged projectile dots, melee slash arcs; mining chips and store-into-building cargo flight.
- **Minimap**: top-right global overview (hidden in F8 zoom); left-click jumps square, right-click jumps and issues default order.
- **Objectives button**: top-left; left-click next, Shift+click previous (same as objectives hotkey); Esc dismisses caption.
- **Code**: ``clientgamegridview.py``, ``clientgame/game_visual_fx.py``, ``clientgame/game_display.py``.
- **Docs**: player manuals and layered-hotkeys.

**New: F4 accessibility voice toggle in menus**

- In **any menu** (including the in-game pause menu), press **F4**, or use “toggle accessibility voice” in the game menu, to turn all TTS off/on.
- **Off**: no speech; SFX and music still work—handy with Ctrl+F2 for sighted play.
- **Default on** (blind-friendly); saved in ``SoundRTS.ini`` (``speech_enabled``).
- **In-match F4 unchanged** (layered hotkeys: still Help & Query); this toggle is menu-only.
- **Code**: ``config.py``, ``lib/voice.py``, ``lib/voice_libs.py`` / ``lib/speech_accessibility.py``, ``clientmenu.py``, ``clientgame/game_resources.py``, ``msgparts.py``; TTS 5740–5743.
- **Docs**: ``player/voice-libraries.rst``, player manuals.

**New: pygame menu visuals and mouse (no wxPython)**

- Main / sub / pause menus draw a selectable list in the SDL window (default about 960×640).
- **Mouse**: hover highlight; click to select and announce; click again or double-click to confirm. Keyboard behavior unchanged.
- Blind play remains TTS + keyboard; on-screen text is pixel-drawn and **usually not available to screen readers / braille displays** (same class of limit as the in-match map view).
- **Code**: ``lib/pygame_ui.py``, ``clientmenu.py``, ``lib/screen.py``.

**New: on-screen cut-scenes / campaign synopsis / objectives**

- Campaign ``synopsis``, cut-scene ``sequence``, map ``intro``, opening objectives, and in-match objective browse (hotkey or top-left Objectives button) show text on screen.
- **Opening objectives**: always **scroll** (auto-continue; any key skips); re-check in-match via Objectives button / hotkey.
- **Cut-scenes / synopsis / intro**: local / training / vs computers only still **Enter** / **Esc**; online with two or more humans scrolls so one player cannot stall everyone.
- **Code**: ``lib/voice.py`` (``play_cutscene_line`` / ``play_scrolling_line`` / ``play_narrative_line``), ``clientmedia.play_sequence``, ``campaign.py``, ``game_interface_base.py``, ``game_resources.py``, ``game_display.py``.

**Improvement: Ctrl+F2 display toggle persisted**

- Saved as ``display_enabled`` under ``[general]`` in ``SoundRTS.ini``; restored on next launch.
- **Code**: ``config.py``, ``clientmedia.py``.

**Fix: letter-jump lag in long map lists**

- **Symptom**: After “start a game”, jumping to a map by first letter lagged ~0.8 s.
- **Cause**: Menu redraw ran a global campaign TTS scan per map name.
- **Fix**: Local fast labels + cache; drop redundant redraw after every key.
- **Code**: ``lib/pygame_ui.py``, ``clientmenu.py``.


1.4.5.9
--------

**Improvement: square ``space`` counted per alliance**

- **Before**: Capacity was shared by all sides; enemy siege filling a square blocked friendly melee/cavalry from entering.
- **Now**: Each alliance has its own budget up to ``square_width``; enemy occupancy does not use your budget. E.g. with ``square_width 12``, each side may field twelve ``space 1`` units. Allies share one budget.
- **Code**: ``worldroom.py`` (``used_square_space`` / ``have_enough_square_space``); train/spawn call sites pass the player.
- **Docs**: ``res/rules.txt``, ``mod/modding.rst``, player manuals, release notes.
- **Tests**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Fix: gathered resources stored without a warehouse**

- **Symptom**: After gathering, workers could add resources to the stockpile even with no town hall / lumber mill / other storage building present.
- **Cause**: Land ``bring_back`` still called ``_store_cargo()`` when ``nearest_warehouse`` returned none. In 1.3.8.1 cargo was cleared and the order failed; a later rewrite incorrectly stored instead.
- **Fix**: Without a warehouse, do not store; keep cargo, notify ``order_impossible`` once, and stop. Delivery resumes after a warehouse is built.
- **Code**: ``worldorders/gathering.py``.
- **Tests**: ``test_gather_requires_warehouse.py``.


1.4.5.8
--------

**New: abstract square occupancy (``space``)**

- Unit property ``space`` (precision; decimals allowed) uses the **same units as map ``square_width``**. ``square_width 12`` means each square (e.g. a1) has size 12; ``space 1`` occupies 1 of that 12 (at most 12); ``space 0.5`` → at most 24. **Abstract capacity only**; it does not change physical collision size.
- Default ``space 0`` = unlimited abstract capacity (legacy). Capacity is per alliance (see 1.4.5.9); when your side is full, you cannot enter or train there. Voice: ``not_enough_space`` (TTS 5338); attribute label TTS 5733.
- Vanilla examples: peasant/footman ``space 0.25``; catapult ``space 1``.
- **Code**: ``definitions.py``, ``worldentity.py``, ``worldroom.py``, ``worldunit/world_movement.py``, ``worldorders/production.py``, ``worldplayercomputer_water.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui*/tts.txt``.
- **Docs**: ``mod/modding.rst``, ``mod/mapmaking.rst``, player manuals (all languages).
- **Tests**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**New: building victory countdown (``victory_time``) and Wonder**

- Any finished building with ``victory_time N`` (seconds) starts a countdown. If the timer ends while that building still stands, its owner (and allied victory camp) wins. Destroying the building cancels the countdown and announces it.
- Vanilla ``wonder`` (Imperial Age): expensive late building; ``victory_time 300`` (5 minutes). Shortcut ``o``.
- Voice IDs 5720–5722 (timer started / cancelled / remaining); remaining cues at 120/60/30/10 s and 5…1.
- **Code**: ``building_victory.py``, ``worldunit/worldcreature.py``, ``world/world_core.py``, ``world/world_game.py``, ``definitions.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (``victory_time``), player manuals.
- **Tests**: ``test_building_victory.py``.

**New: ``any_buildings`` requirement groups**

- ``requirements`` may use ``any_buildings <n> <group>_buildings``: the player must own any ``<n>`` distinct buildings of that group (AND with other plain names on the same line).
- Group membership: buildings whose simple ``requirements`` list ``<key>`` (after stripping the ``_buildings`` suffix). Example: ``requirements castle_age`` joins ``castle_age_buildings``.
- Vanilla: ``imperial_age`` and ``castle`` (keep→castle) both use ``any_buildings 2 castle_age_buildings``.
- Voice: style ``parameters.any`` / ``parameters.buildings_of`` (TTS 5730–5731); attributes “belongs to age” (TTS 5732) inferred from phase names in simple ``requirements``.
- **Code**: ``worldrequirements.py``, ``worldplayerbase/base.py``, ``worldphase.py``, ``worldplayercomputer.py``, ``clientgameorder.py``, ``attributes/display_interface.py``, ``attributes/basic_attributes.py``, ``definitions.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (all languages).
- **Tests**: ``test_any_buildings_requirements.py``, ``test_tech_detail_attributes.py``.


1.4.5.7
--------

**Fix: units stuck attacking non-threatening buildings instead of enemy combatants**

- **Symptom**: While units smash a farm, town hall, or similar building, enemy combatants can walk up and kill them; the attackers keep hitting the building instead of switching.
- **Cause**: 1.4 skipped target re-scan while already engaged (performance). Buildings count as living enemies, so engagement stuck on farms. 1.3.8.1 only stuck on targets with ``menace > 0`` and re-chose when the current target had no threat.
- **Fix**: Restore 1.3.8.1 behavior—sticky engage and decision cache only for ``menace > 0``; zero-menace buildings may be re-scanned so combat units are preferred. Fighting threatening units still early-returns (hot path unchanged).
- **Code**: ``worldunit/world_ai_decision.py``.
- **Tests**: ``test_retarget_zero_menace.py``.

**Improvement: bindings distinguish Left/Right Shift (``LSHIFT`` / ``RSHIFT``)**

- Binding files may use ``LSHIFT`` or ``RSHIFT`` as modifiers in addition to generic ``SHIFT`` (do not mix ``SHIFT`` with ``LSHIFT``/``RSHIFT`` on the same line).
- Lookup prefers side-specific bindings, then falls back to generic ``SHIFT`` (e.g. ``SHIFT F9`` for the secondary voice library still works with either Shift).
- Enabled by default: ``RSHIFT C`` / ``RSHIFT B`` (copy/append **secondary** last utterance).
- ``LSHIFT C`` / ``LSHIFT B`` (primary) are **commented out** in ``res/ui/global_bindings.txt``; remove the leading ``;`` to enable them.
- **Tip:** Prefer a screen reader as the primary voice (it takes over primary duties) so ``F9``–``F12`` need not adjust the primary library. Hotkeys are nearly saturated—save keys when you can. See ``player/voice-libraries.rst``.
- **Code**: ``lib/bindings.py``, ``res/ui/global_bindings.txt``, ``hotkey_editor.py``.
- **Tests**: ``test_lshift_rshift_bindings.py``.

**Improvement: volume floor for distant square speech pan**

- **Symptom**: Square-linked passive speech (secondary library, etc.) attenuated too much for far squares and was hard to hear while playing.
- **Change**: Distance attenuation for spoken directional cues is capped near one-square loudness (slightly quieter allowed); there is always that floor no matter how far. Left/right and rear attenuation remain. Minimap alert SFX still use full distance falloff.
- **Code**: ``lib/sound.py`` (``distance_cap``), ``clientgame/game_resources.py``, ``clientgame/game_unit_control.py``.
- **Docs**: ``player/voice-libraries.rst``.
- **Tests**: ``test_spatial_voice_alerts.py``.

**Improvement: ``ai.txt`` ``build_time`` multiplier**

- New one-shot directive ``build_time <pct>`` (applied at game start, not in the script loop): percent of normal building-construction duration (``100`` = normal, ``50`` = twice as fast). Alongside ``train_time`` / ``research_time``.
- Vanilla examples: advanced/expert ``build_time 50``; nightmare ``build_time 40``.
- **Code**: ``definitions.py``, ``worldplayercomputer.py``, ``worldorders/base.py``, ``worldunit/worldcreature.py``; ``res/ai.txt``.
- **Docs**: ``mod/aimaking.rst``.
- **Tests**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.

**Improvement: ``ai.txt`` ``gather_time`` multiplier**

- New one-shot directive ``gather_time <pct>``: percent of normal resource-gathering duration for computer workers (``100`` = normal, ``50`` = twice as fast). Applied in ``Worker.get_gather_time`` (distinct from the worker ``gather_time`` field in ``rules.txt``).
- Vanilla examples: advanced/expert ``gather_time 50``; nightmare ``gather_time 40``.
- **Code**: ``definitions.py``, ``worldplayercomputer.py``, ``worldunit/worldworker.py``; ``res/ai.txt``.
- **Docs**: ``mod/aimaking.rst``.
- **Tests**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.6
--------

**Fix: Alt+Z could only queue one extra train**

- **Symptom**: After confirming train peasant on a town hall, Alt+Z (``do_again now``) could add only one more to the queue; further presses did not grow the queue (they replaced the single queued follow-up).
- **Cause**: 1.4 limited “only one normal order behind an imperative head” to protect ``auto_explore``. Production orders (train/research) are also marked ``is_imperative``, so they were hit by mistake. 1.3.8.1 had no such limit and stacked trains correctly.
- **Fix**: ``never_forget_previous`` production orders may stack freely; the single follow-up slot still applies to normal orders behind true imperative heads (e.g. explore).
- **Code**: ``worldunit/world_order.py``.
- **Tests**: ``test_train_queue_repeat.py``.

**Fix: first Alt+Z (and similar) hitch ~0.6–1s**

- **Symptom**: After starting a match, the first Alt+Z to repeat train (etc.) freezes the game for about half a second to one second; later presses are usually fine. 1.3.8.1 Alt+G (same feature) did not hitch.
- **Cause**: Alt+Z / Alt+G both deliver a lone ``LALT`` key first (``history_stop_primary`` → ``game_tts.stop``). ``stop`` called ``needs_sapi32`` for the primary voice; with Nuance that still probed the 32-bit SAPI helper (cold-start PowerShell) ~1s on the UI thread.
- **Fix**: Nuance voices skip sapi32 probing; cache ``needs_sapi32`` results; ``stop`` skips the probe for Nuance.
- **Code**: ``lib/game_tts.py``.
- **Tests**: ``test_nuance_skip_sapi32_probe.py``.


1.4.5.5
--------

**Improvement: directional square alerts (stereo pan follows the view)**

- Square-linked passive lines (enemy spotted, casualties, scout info, combat-square alerts) pan left/right relative to the current view square (same math as minimap alert SFX).
- **Pan updates mid-utterance** when you change squares (e.g. hear “enemy at a1” from the left on b1, then move to a1 → voice centers before the next message).
- Nuance: PCM stereo gains plus live ``set_pan``; SAPI: render to a buffer and pan on the pygame voice channel.
- Nuance helper must be built as **Java 7** bytecode (runtime ``user/voices/nuance/jre``); see ``tools/nuance_ve/README.md``.
- **Code**: ``lib/voicechannel.py``, ``lib/message.py``, ``lib/game_tts.py``, ``lib/nuance_tts.py``, ``clientgame/game_unit_control.py``, ``clientgame/game_navigation.py``, ``tools/nuance_ve``, ``tools/sapi32``.
- **Docs**: ``player/voice-libraries.rst``.
- **Tests**: ``test_spatial_voice_alerts.py``.

**Improvement: narrower secondary voice duties (economy / production → primary)**

- Unit/building complete, research complete, age upgrade complete, resource stock changes, and “menu changed” now use the **primary** library.
- Secondary focuses on battlefield passives (enemies spotted, casualties, scout, combat alerts, …).
- **Code**: ``lib/message.py`` (``tts_channel``), ``lib/voice.py``, ``clientgameentity/events.py``, ``clientgame/game_resources.py``, ``clientgame/game_unit_control.py``.
- **Docs**: ``player/voice-libraries.rst``.
- **Tests**: ``test_primary_economy_voice.py``.

**Improvement: Left Alt / Right Alt filter primary vs secondary**

- **Left Alt** skips/stops the primary library; **Right Alt** skips/stops the secondary (no longer one shared Alt).
- **With secondary disabled**: both Left and Right Alt skip the current line (everything is on primary).
- Bindings: ``LALT: history_stop_primary``, ``RALT: history_stop_secondary``.
- **Code**: ``lib/voice.py``, ``clientgame/game_audio.py``, ``clientmenu.py``, ``res/ui/*_bindings.txt``.
- **Docs**: ``player/voice-libraries.rst``.
- **Tests**: ``test_secondary_alt_interrupt.py``.

**Improvement: configurable mixer buffer and sample rate (less in-match SFX stutter)**

- ``SoundRTS.ini`` ``[audio]`` adds ``mixer_buffer`` (default ``2048``) and ``mixer_frequency`` (default ``44100``), applied at startup via ``pygame.mixer.pre_init``.
- Larger buffer = stabler audio, slightly more latency: ``1024``≈23ms (prone to underruns), ``2048``≈46ms (default), ``4096``≈93ms (try if still stuttering). Invalid values snap to the nearest of ``512/1024/2048/4096/8192``.
- SFX channel count remains ``[general] num_channels`` (default ``16``; try ``32`` in very busy matches).
- **Restart the game** after changing these. Older ini files missing the keys get defaults on the next launch.
- **Code**: ``config.py``, ``lib/sound.py``, ``clientmedia.py``.
- **Docs**: ``mod/audio-management.rst``, ``player/getting-started.rst``.


1.4.5.4
--------

**Improvement: primary / secondary voice libraries and toggle**

- In-match: player ops use the **primary** library; passive events (casualties, discoveries, …) use the **secondary** library (can overlap; only Alt interrupts secondary).
- Options → Voice library settings: edit volume / pitch / rate / voice / device per library; enable or disable secondary.
- **F3 in menus** toggles secondary on/off (not in-match); when off, primary speaks everything.
- Install SAPI voices or ``voice.ini`` packs under ``user/voices``; a detected screen reader may take over primary duties.
- **Code**: ``lib/voice.py``, ``lib/voicechannel.py``, ``lib/game_tts.py``, ``lib/voice_libs.py``, ``lib/voice_packs.py``, ``clientmenu.py``, ``clientmain.py``, ``config.py``.
- **Docs**: ``player/voice-libraries.rst``.
- **Tests**: ``test_secondary_voice_toggle.py``, ``test_secondary_alt_interrupt.py``.

**Improvement: card reinforcements and AI ``starting_units`` consume population**

- Pre-mission card ``spawn`` / ``train_bonus`` units use normal ``population_cost`` (no longer free of population).
- ``ai.txt`` ``starting_units`` bonuses also consume population (same as map starting units); raise the cap with ``starting_population`` if needed.
- **Code**: ``card_loadout.py``, ``worldplayercomputer.py``.
- **Docs**: ``player/loadout-cards.rst``, ``mod/aimaking.rst``, ``mod/delayed-card-loadout.rst``, ``mod/achievement-system.rst``.
- **Tests**: ``test_card_loadout.py``, ``test_ai_start_settings.py``.

**Improvement: ``ai.txt`` train time, research time, and unit HP multipliers**

- New one-shot directives (applied at game start, not in the script loop):
  - ``train_time <pct>`` — percent of normal training duration (``100`` = normal, ``50`` = half time)
  - ``research_time <pct>`` — percent of normal research/advance duration (``80`` = 20% faster)
  - ``unit_hp <pct>`` — percent of normal HP for this computer's units (``120`` = +20% HP)
- Vanilla ``res/ai.txt`` examples: advanced ``train_time 50`` / ``research_time 80``; expert also ``unit_hp 120``; nightmare ``train_time 40`` / ``research_time 60`` / ``unit_hp 140``.
- **Code**: ``definitions.py``, ``worldplayercomputer.py``, ``worldorders/base.py``, ``worldorders/production.py``, ``worldunit/worldcreature.py``; ``res/ai.txt``.
- **Docs**: ``mod/aimaking.rst``.
- **Tests**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.3
--------

**Fix: intermediate computer soldiers stuck on auto-explore delaying attacks**

- **Symptom**: On small melee maps (e.g. ``jl1``), inviting an intermediate computer while the human idles produced highly unstable first-attack timing — sometimes ~6 minutes, sometimes 16–22 minutes. In 1.3.8.1 the aggressive computer reliably attacked around 7–9 minutes in the same setup.
- **Cause**: Since 1.4, ``take_order`` protects an imperative head order (``auto_explore`` is imperative): a plain ``go`` only queues and cannot displace explore. AI ``_send_explorer`` still recalled the old explorer with ``go``, failed, then kept assigning new explorers until nearly all soldiers were on ``auto_explore``, so ``constant_attacks`` had no idle fighters.
- **Fix**: ``_send_explorer`` issues ``stop`` before recall and clears surplus explorers so normally only one unit explores.
- **Code**: ``worldplayercomputer.py`` (``_send_explorer``).
- **Verification**: Headless multi-seed comparison vs 1.3.8.1; after the fix, jl1 intermediate first damage is about 5–7 minutes with ~1.5 minutes span (no more 10+ minute stalls).

**Fix: menu first-letter map jump skipped the first match and lagged when changing letters**

- **Symptom**: In Single player → Start a game on (map list), one press of a letter often landed on the second match (e.g. ``m`` → ``m2`` instead of ``m1``, ``p`` → ``pm2`` instead of ``pm1``); pressing another letter then paused about 0.7–1 second before jumping.
- **Cause**: Title speech with ``keep_key`` re-queued every auto-repeat ``KEYDOWN``, so one physical press was handled twice; remembering the last map inserted a duplicate at the front of the list, which won when it shared the typed letter. ``_first_letter`` called ``translate_sound_number`` → ``_global_lookup_text`` on map filenames, costing ~1 second to scan a hundred-entry list.
- **Fix**: Keep only the first ``KEYDOWN`` when interrupting speech and clear repeats after letter jumps; from a fresh selection, find the first match from the start of the list; remember via ``default_choice_index`` instead of a duplicate; take the first character of map names directly and look up numeric TTS ids in the local layer only.
- **Code**: ``clientmenu.py``, ``lib/voice.py``.
- **Tests**: ``test_menu_first_letter_jump.py``.


1.4.5.2
--------

**Improvement: multi-dimensional auto menace and optional rules overrides**

- Default ``menace`` is no longer raw damage: it scores damage, hit cover, cooldown, wind-up (``*_ready``), HP, armor, dodge, range, and speed for auto-targeting and square threat sums.
- Optional unit fields: ``menace`` / ``menace_vs`` (absolute fixed), ``menace_mult`` / ``menace_mult_vs`` (multiply the auto multi-dim base; still scales with upgrades).
- Tunable in ``def parameters``: ``menace_armor_weight``, ``menace_dodge_weight``, ``menace_range_weight``, ``menace_speed_weight``, ``menace_hp_ref``.
- **Code**: ``worldunit/world_attributes.py``, ``combat/targeting.py``, ``definitions.py``; ``res/rules.txt`` parameters; ``res/ui/rules_doc.txt``.
- **Docs**: ``mod/modding.rst``, ``mod/aimaking.rst``.
- **Tests**: ``test_rules_menace_targeting.py``, ``test_ai_counter_targeting.py``.

**Improvement: continuous cross-square chase (true pursuit)**

- **Before**: In chase mode, when an enemy left the square the AI issued automatic ``go`` orders to hop into adjacent squares and then attack again — still order-driven, and units could stay “attacking” without leaving the square.
- **Now**: ``chase`` keeps a single ``AttackAction`` on the locked enemy and paths through exits across squares; no automatic ``go`` spam.
- **Hold**: Spawn ``position_to_hold`` still blocks leaving the hold area for offensive / guard. Defensive / chase are exempt (chase clears hold when crossing squares). Normal ``go`` / ``attack`` still call ``stop()`` first and clear hold.
- **Code**: ``worldaction.py`` (``AttackAction._chase_toward``), ``worldunit/world_ai_decision.py``, ``worldunit/world_movement.py`` (``_must_hold``).
- **Docs**: ``player/unit-default-behavior.rst``.
- **Tests**: ``test_chase_continuous_pursuit.py``.

**Improvement: attributes screen shows live terrain-adjusted stats**

- Alt+V shows unit ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` and charge terrain modifiers.
- Current-square terrain ``mdg_vs`` / ``rdg_vs`` / etc. plus ``*_on_terrain`` feed the damage, cooldown, and speed readings on the attributes screen (terrain ``*_vs`` = decimal percent, e.g. ``.25`` = +25%%; unit ``speed_on_terrain`` remains absolute speed).
- **Code**: ``attributes/terrain_effective.py``, ``attributes/combat_attributes.py``, ``attributes/basic_attributes.py``, ``attributes/bonus_handler.py``.
- **Tests**: ``test_terrain_attributes_ui.py``, ``test_terrain_effective_attributes.py``.

**Fix: Tab no longer finds exits on never-scouted squares**

- **Symptom**: On squares never visited (static fog, no scout record), Tab cycling could still announce far-side exits / paths.
- **Cause**: Fog logic remembered opposite-side exits before the square was actually entered.
- **Fix**: If a square is in neither ``scouted_squares`` nor ``scouted_before_squares``, visibility / place summary stay blank; visited-then-left static fog still allows Tab.
- **Code**: ``clientgame/game_unit_control.py``.
- **Tests**: ``test_unknown_square_tab_blank.py``.

**Fix: ``order_impossible`` beep after Backspace-killing a hunt animal**

- **Symptom**: After a default attack killed a huntable animal, ``order_impossible`` played.
- **Cause**: ``AttackOrder`` treated a vanished target as failure.
- **Fix**: Mark the order complete when the target is gone or ``hp <= 0``.
- **Code**: ``worldorders/movement.py``.
- **Tests**: ``test_hunting.py`` (``test_attack_order_completes_when_huntable_target_gone``).

**Fix: neutral default order and hunt damage**

- Default order on **all** neutrals (wildlife / creep / NPC, including ``is_huntable``) is ``go`` — approach / claim; no AttackAction.
- Attack neutrals with imperative (Ctrl+Backspace, or ``go`` then Ctrl+Enter). Owned ``is_huntable`` still defaults to ``attack`` (slaughter); plain attack deals damage.
- Only imperative attack lets AI treat neutrals as auto-engage targets.
- **Code**: ``worldunit/world_ai_decision.py``, ``worldunit/worldcreature.py``, ``worldunit/worldworker.py``, ``worldunit/world_order.py``.
- **Docs**: ``player/hunting.rst``, ``player/unit-default-behavior.rst``.
- **Tests**: ``test_neutral_no_auto_attack.py``, ``test_neutral_go_and_hunt_attack.py``, ``test_claimable_pasture.py``, ``test_hunting.py``.

**Fix: Computer player perception update crash (missing ``_buckets``)**

- **Symptom**: Mid-game (especially with ``computer_only`` map AI, allied AI teammates, or after loading a save) could crash in the main-loop perception stage with ``AttributeError: 'Computer' object has no attribute '_buckets'``.
- **Cause**: The player spatial-grid index ``_buckets`` was initialized only in the wrapper ``Player.__init__``; save/load strips that cache field; allied-vision bulk visibility checks (``bulk_visibility_check``) call allies' ``_potential_neighbors``, which raised if a ``Computer`` did not yet hold ``_buckets``.
- **Fix**: Pre-initialize ``_buckets`` in ``BasePlayer.__init__`` with the other perception caches; ``_potential_neighbors`` falls back to an empty dict when missing; ``update_alliance`` clears the ``allied_vision`` instance cache so alliance changes do not keep stale ally lists.
- **Code**: ``worldplayerbase/base.py``, ``worldplayerbase/perception.py``, ``worldplayerbase/__init__.py``.
- **Tests**: ``test_meteors_computer_only.py``, ``test_phase3_parity.py``, ``test_neutral_passive_creep.py``.


1.4.5.1
--------

**Improvement: terrain cover, per-unit modifiers, and percent notation**

- ``rules.txt`` ``class terrain`` now supports ``cover <ground> <air>``, same as ``speed``: a map line ``terrain marsh h8`` inherits default cover; per-square map ``cover`` lines still override.
- Terrain can modify **unit types** via ``speed_vs``, ``cover_vs``, ``dodge_vs``, ``mdg_vs``, ``rdg_vs``, ``mdg_cd_vs``, ``rdg_cd_vs`` (e.g. ``speed_vs knight .25 archer .5``). You may use ``*_vs`` alone without a global ``speed``/``cover``.
- Those ``*_vs`` fields and unit ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` (and ``charge_*_terrain``) now use **0–1 decimal percents** (``.5`` = ±50%%, ``.1`` = ±10%%) relative to the unit's current base damage or cooldown.
- ``speed_on_terrain`` remains an **absolute speed** override (unlike percent ``speed_vs``).
- Map ``speed`` / ``cover`` still apply to **all** units on a square; per-unit differences belong in terrain or unit defs in ``rules.txt``.
- **Code**: ``worldterrain.py``, ``lib/square_terrain_rules.py``, ``world/world_map.py``, ``combat/hit_miss.py``, ``combat/damage_calculation.py``, ``combat/attack_action.py``, ``worldunit/world_movement.py``; random maps emit ``cover`` lines (``rmg_templates.terrain_cover_line``).
- **Docs**: ``mod/building-land-terrain.rst``; ``res/ui/editor_palette.txt`` comments.
- **Tests**: ``test_terrain_cover_defaults.py``, ``test_terrain_unit_vs.py``, ``test_unit_on_terrain_percent.py``; ``test_combat_terrain_modifiers.py`` updated to percent cases.

Bug fixes and voice/audio UX improvements:

**Fix: melee/ranged attack cooldown (``mdg_cd`` / ``rdg_cd``) slower than rules specify**

- **Symptom**: With 1 second cooldown in rules (e.g. peasant ``mdg_cd 1``), actual attack interval was noticeably longer than in 1.3.8.1 (~1.5 s vs ~1.2 s; the latter is only 300 ms tick quantization).
- **Cause**: (1) When ``mdg_ready`` / ``rdg_ready`` is 0, the prep branch still consumed an extra tick before striking; (2) instant hits (``mdg_delay`` / ``rdg_delay`` 0) were forced through a 100 ms minimum delay in ``_schedule_ballistic_hit``; (3) ``attack_action.aim()`` and ``damage_effects._schedule_ballistic_hit`` both set cooldown, with the second write after the delay extending ``next_attack_time`` further.
- **Fix**: Skip prep when ``ready=0`` and attack immediately; no 100 ms floor for instant hits; set cooldown only once in ``attack_action.aim()`` when the attack starts.
- **Note**: ``charge_mdg_cd`` / ``charge_rdg_cd`` use a separate path (immediate ``receive_hit``, no prep/ballistic scheduling) and were not affected by these three issues; mixed charge + normal-attack pacing improves indirectly via the normal-attack CD fix.
- **Code**: ``combat/attack_action.py``, ``combat/damage_effects.py``.
- **Tests**: ``test_attack_cooldown_timing.py``.

**Improvement: go-order rejection and voice feedback on impassable terrain**

- When a ground unit orders ``go`` / ``patrol`` to a square with ``is_ground 0``, or an air unit to ``is_air 0``, the order is rejected at queue time with "ground is impassable" or "air is impassable" (``order_impossible`` + ``ground_impassable`` / ``air_impassable``).
- Terrain with a ``passable_units`` whitelist: units not on the list are rejected on ``go`` with "\<unit type\>, cannot pass" (e.g. "footman, cannot pass", "knight, cannot pass"); whitelisted types (including via ``is_a``) still work.
- Existing checks unchanged: pure water for ground units, land for water units, unfinished bridge scaffold, etc.
- **Code**: ``worldorders/base.py`` (``_ground_air_impassable_reason``, ``_terrain_impassable_reason``); ``lib/square_terrain_rules.py`` (``terrain_name_at_square``, ``passable_units_denied_reason``); ``clientgameentity/events.py`` (unit title + "cannot pass" in ``on_order_impossible``).
- **Voice**: ``res/ui/style.txt`` ``messages`` — ``ground_impassable`` 4979, ``air_impassable`` 5700, ``passable_units_denied`` 5701; EN/ZH ``tts.txt`` entries included.
- **Docs**: ``mod/building-land-terrain.rst`` passability section.
- **Tests**: ``test_water_impassable_order.py``.

**Fix: nameless fog ghost after unit suicide**

- **Symptom**: After a unit suicides, Tab-cycling targets in the same square could still select an object with no readable name.
- **Cause**: After death ``place is None``, fog-of-war memory was not cleared in time; memory objects could have a ``title`` (fog suffix) but an empty ``short_title``, yet Tab still treated them as selectable.
- **Fix**: ``perception.py`` forgets memory when ``initial_model.place is None``; units leaving perception are not memorized when ``place is None`` or when they are the player's own dead units; ``game_unit_control.py`` ``is_visible`` requires a non-empty ``short_title``.
- **Tests**: ``test_suicide_fog_ghost.py`` (corpse fog memory and ambient audio paths preserved).

**Fix: wall HP flickering up and down while attacking**

- **Symptom**: Attacking ``wall`` and other ``is_repairable`` buildings could make HP or life-change sounds rise and fall intermittently.
- **Cause**: Walls inherit ``is_repairable=True`` from buildings, so attack / repair / capture-threshold logic could interact; fog HP sync (``_sync_memory_hp_from_live``) without carrying ``previous_hp`` across perception/memory view swaps caused false life-change feedback.
- **Fix**: ``world_order.py`` / ``worldcreature.py`` / ``worldworker.py`` — enemy repairable buildings default to ``go``, imperative default to ``attack``; repair paths guarded with ``not is_an_enemy(target)``; ``game_navigation.py`` preserves HP tracking on fog updates (``_take_hp_tracking`` / ``_apply_hp_tracking``).
- **Tests**: ``test_imperative_attack.py`` (imperative attack on walls).

**Fix: normal go order incorrectly interrupting imperative attack**

- **Symptom**: While a unit is force-attacking a target (e.g. town hall), issuing a normal ``go`` stopped the attack, yet group select (e.g. F) still announced "attacking the town hall, go to \<square\>" — behavior and voice were inconsistent.
- **Cause**: ``take_order`` with ``forget_previous=True`` called ``cancel_all_orders()``, removing the imperative attack and queuing ``go``, while ``AttackAction`` could remain on the unit.
- **Fix**: While an imperative order is active, normal commands (except ``stop``) are auto-queued (``forget_previous=False``) without replacing the imperative head; the unit finishes the forced attack before executing the follow-up. Only **one** queued command is allowed after an imperative order; a new normal command **replaces** the existing queued one (same as 1.3.8.1).
- **Code**: ``worldunit/world_order.py`` ``take_order``.
- **Tests**: ``test_imperative_attack.py`` (``test_normal_go_queues_behind_imperative_attack``, ``test_only_one_queued_order_behind_imperative_attack``, etc.).

**Improvement: unit behavior voice descriptions**

- After Tab-selecting a target, Ctrl+Backspace or go + Ctrl+Enter confirms "attack \<target\>" instead of "go" for enemy units/buildings.
- Hotkey group select (e.g. F for footmen): "You control N footmen attacking the town hall"; if moving while fighting, appends "go to c6".
- **Code**: ``clientgameentity/base.py`` ``_attack_action_title_msg``; ``properties.py`` ``orders_txt``; ``game_orders.py`` ``_say_validate_confirmation`` / ``_say_default_confirmation``; ``game_unit_control.py`` ``say_group``.
- **Tests**: ``test_attack_orders_txt.py``, ``test_imperative_attack.py``.

**Improvement: layered battle shouts**

- Three layers: ``shout_bg`` (battlefield background), ``shout_unit`` (unit voice), ``shout_event`` (first clash / charge / crit highlights); global and per-square cooldowns; ``formation_sound_queue`` staggers bursts so shouts do not stack with hit sounds in the same frame.
- **Code**: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``.
- **Docs**: ``mod/battle-shouts.rst``.
- **Tests**: ``test_battle_shout_audio.py``.

**Improvement: P0–P2 audio engine refactor**

- **Correction**: early drafts wrongly described P0–P2 as ambient/combat/alert *priority tiers*; they are **three refactor phases** for the audio engine, separate from layered battle shouts above and from ``psounds.play(..., priority=…)`` preemption. See ``mod/audio-management.rst``.
- **P0 structure**: ``lib/music_resolver.py`` centralizes menu/game/battle/victory/defeat lookup; ``sound_cache.clear_decoded()`` on mod/map switches; instance-state fixes for ``SoundSource`` / ``SoundManager``.
- **P1 UX**: separate ``audio/sfx_volume`` from voice ``main_volume``; non-blocking voice wait (event pump); unified menu-music fallback.
- **P2 polish**: ambient LFO smoothing; ``lib/battle_music.py`` state machine; ``music_resolver`` cleanup; game SFX under ``ui/`` supports ``.ogg`` / ``.wav`` / ``.mp3`` (``.ogg`` preferred) plus hot preload (``preload_sounds`` / ``tick_preload``).
- **Hotkeys**: Home/End for game SFX; Alt+Home/Alt+End for music.
- **Tests**: ``test_music_resolver.py``, ``test_audio_settings.py``, ``test_voice_pump.py``, ``test_ambient_stereo_volume.py``, ``test_battle_music.py``, ``test_sfx_formats.py``.

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

**Terrain footsteps and falling sounds**

- ``move_on_<key>`` / ``falling_on_<key>`` now accept **terrain type names** (e.g. ``ocean``) and ``style.txt`` ``ground`` categories (e.g. ``water``, ``grass``); the type name is tried first.
- Fix: on terrains without ``ground`` (e.g. ``ocean``), ``falling_on_ocean`` previously never matched and only the generic ``falling`` played.
- Docs: ``mod/modding.rst`` (Combat sound system); tests: ``test_falling_terrain_sound.py``.

**Battle shouts (layered playback)**

- Three layers on combat: battlefield background, unit voice, event highlights; global/per-square cooldowns.
- ``ui/style.txt``: ``shouts`` on ``def walking_unit``; triggers when either side has ≥5 fighting units in the square.
- Code: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``; tests: ``test_battle_shout_audio.py``.
- Docs: ``mod/battle-shouts.rst``.

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
