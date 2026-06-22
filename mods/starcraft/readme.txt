StarCraft build mechanics demo mod

====================================



Activate: SoundRTS.ini → mods = starcraft



Multiplayer lobby factions

--------------------------

- Terran, Protoss, Zerg only (+ random). Base-game ``human_faction`` is hidden.

- Faction titles: style ``terran`` / ``protoss`` / ``zerg`` → TTS 7260–7262 (人族 / 神族 / 异虫).



Player guides (addons, lift-off, recombine)

-------------------------------------------

- Chinese: docs/zh/星际人族附属建筑与重组说明.md

- English: docs/en/starcraft-terran-addons.md

- Mod authors (build-field / addon keywords): doc_src/src/zh/modding.rst, doc_src/src/en/modding.rst



Resources (minerals + vespene)

--------------------------------

- ``mineral_field`` — map deposit (``mineral_field 1500 a1``); workers gather directly.

- ``geyser`` — vespene geyser (``geyser 1 e1``); build Assimilator / Extractor / Refinery on it.

- Gas buildings use ``requires_deposit geyser`` + ``is_gather`` / ``auto_production`` (``production_time`` = fill duration, ``production_qty`` = gas per cycle; engine keyword ``requires_deposit``). They **cannot** be built on meadows — only on a geyser square (Tab the geyser, then build).

- Map win example: ``(and (has assimilator) (has_resources resource2 8))`` — built gas structure **and** 8 vespene stored.

- Resource names: style ``resource1_title`` / ``resource2_title`` → minerals / vespene gas.

Test map: ``sc_resources_test`` (Protoss: build Assimilator on geyser).


Supply / population cap
-----------------------

Uses engine ``population_provided`` / ``population_cost`` (F1 资源面板显示已用/上限).

- **Command Center / Nexus / Hatchery** — **10** supply each (starting townhall)

- **Supply Depot** (Terran, SCV builds, ``B+D``) — **+8**

- **Pylon** (Protoss) — **+8** (also extends psi field)

- **Overlord** (Zerg, trained at Hatchery) — **+8** (does not consume supply)

Faction ``house`` in rules.txt tells the AI which type to build/train when supply is tight:

``terran`` → ``supply_depot``, ``protoss`` → ``pylon``, ``zerg`` → ``overlord``.

When supply is full, training is blocked and the client plays TTS **7399** (Not enough supply).

Test map: ``sc_supply_test`` — build a Supply Depot, then train **12** Marines (10 fit without depot).


Tech tree (units + vespene upgrades)

------------------------------------

Protoss psi field (meters, ``build_field_radius_m``)

- Nexus **18 m**; Pylon **12 m** (one map square ≈ 12 m — chain Pylons to extend)
- Zerg creep uses ``build_field_radius_m`` (Hatchery **12 m**); marks spread with ``build_field_spreads``
- **Queen** — Spawn creep tumor (25 mana, range 11; needs creep on target square)
- **Creep tumor** — invisible building, 4 m creep radius, spreads; **Extend creep tumor** (range 8; target must be a **marked** creep square)

Protoss buildings

- **Forge** (15 minerals, 1 gas) — Ground Weapons 1/2

- **Cybernetics Core** (15, 2) — Plasma Shields 1/2; unlocks **Dragoon** at Gateway

- **Stargate** (28, 4, requires Core) — **Observer**

- Dragoon (12, 2), Observer (15, 2)


Zerg

- **Spawning Pool** — Zergling + Melee/Carapace upgrades (tier 2 costs gas)

- **Queen** (from Hatchery) — Spawn Larva, Inject Larva, **Spawn creep tumor**

- **Creep tumor** — extends creep via **Extend creep tumor** (marked squares only)

- **Roach Warren** (15, 2, requires Pool) — **Roach** (10, 1)

- **Hydralisk Den** (15, 3, requires Pool) — **Hydralisk** (10, 2)


Terran

- **Engineering Bay** — Infantry Weapons/Armor 1/2 (tier 2 costs gas)

- **Armory** (requires Factory) — Vehicle Weapons/Armor 1/2 (gas)

- **Bunker** — defensive structure

- Tech Lab still unlocks Marauder / Tank / Medivac (gas unit costs unchanged)


Contents

--------

- rules.txt   — Protoss / Zerg / Terran units and build rules

- readme.txt  — this file (quick reference)

- docs/en/starcraft-zerg-creep.md (+ docs/zh/星际异虫菌毯说明.md) — creep radius, spread, Queen tumors

- docs/en/progressive-campaign-objectives.md (+ docs/zh/渐进式战役目标说明.md) — register_objective for chained campaign goals

- doc_src/src/en/modding.rst (+ zh) — full `build_field_radius` / `build_field_radius_m` modder reference

- ui/style.txt + ui/tts.txt (+ ui-zh/tts.txt) — names and speech

  Build field labels: style.txt `def build_field_<name>` + `title <tts_id>` (e.g. psi → 7240)

  Voice: moving onto a visible square with your field announces the label; building

  without the required field plays "cannot build there" + the field label.

  Ambient sound: optional `noise repeat <seconds> <sound>` or `noise loop <sound>`

  on the same `build_field_<name>` block (like townhall). Place `<sound>.ogg` in

  mod `ui/effects/` (e.g. `build_field_psi.ogg`, `build_field_creep.ogg`).



Test maps (multiplayer menu, with mod active)

---------------------------------------------

- sc_ai_multi_test  — 2–4 players; pick terran/protoss/zerg; invite easy/aggressive AI

- sc_resources_test — minerals + vespene geyser; build Assimilator on geyser

- sc_tech_test      — Protoss: Cybernetics Core + train Dragoon

- sc_supply_test    — Terran: Supply Depot + train 12 Marines

- protoss_psi_test   — chain at least 4 Pylons (12 m each), Gateway in f1

- zerg_creep_test    — creep spread + on-square build; then destroy Hatchery and build on lingering creep

- zerg_creep_tumor_test — Queen spawn/extend creep tumors to reach distant build site

- terran_addon_test  — attach Tech Lab to Barracks

- terran_recombine_test — lift Barracks (orphan Tech Lab), lift Factory, Tab Tech Lab + go + land to recombine, train Tank



AI scripts (mods/starcraft/ai.txt)

----------------------------------

- sc_terran_easy / sc_terran_aggressive — SCV economy, supply depots, barracks, factory + tech_lab, tanks

- sc_protoss_easy / sc_protoss_aggressive — probes, pylons, gateway, cyber core, dragoons

- sc_zerg_easy / sc_zerg_aggressive — drones, overlords, pool, roach warren / hydra den, gas

Faction defs map lobby ``easy`` / ``aggressive`` to the matching ``sc_*`` script.



Campaign (single player, with mod active)

-----------------------------------------

- sc_campaign — merged tutorial (8 missions: build ch.1–5, late game ch.6–8)



Hotkeys (same as base game)

---------------------------

- W / Shift+W — cycle buildings (Nexus, Pylon, …)

- E / Shift+E — cycle workers (Probe, Drone, SCV)

- R — cycle soldiers (Zealot, Zergling, Marine)

- B then shortcut — build menu: e.g. B+P = Pylon, B+G = Gateway (see style.txt shortcuts)

- Tab / Shift+Tab — cycle targets on square (meadows, addons, units, …)

- Backspace — default order (go to target; flying factory + Tech Lab → flies to landing slot)



Terran addons & recombine (summary)

-----------------------------------

Hosts: Barracks / Factory / Starport (`can_have_addon`).

Addons: Tech Lab / Reactor (`is_addon 1`), built on host side slot, not on a separate meadow.



Build addon: select host → build Tech Lab or Reactor (self_constructs).



Lift-off: `can_change_to flying_*` — addon stays on ground (detached); meadow appears under host.



Land on own lift-off meadow: Tab meadow → Backspace go → change_to ground.

  Normal landing only; does NOT reattach orphan addons.



Recombine: Tab orphaned Tech Lab → Backspace go (redirects to slot west of lab) → change_to.

  Factory placed at slot; nearest meadow consumed; addon reattaches if slot aligned (~2.5 tiles).

  Wrong meadow / no slot alignment → voice hint (7350): go to Tech Lab first.



Tech Lab: `addon_grants_train_<host>` / `addon_grants_research`.

Reactor: `addon_train_multiplier 2`.



See docs/zh/星际人族附属建筑与重组说明.md for meadow vs slot, FAQ, and rules keywords.



Quick checks (other races)

--------------------------

Protoss: Probe places Pylon/Gateway and leaves; buildings self-construct.

         Psi = live radius from Nexus/Pylon; buildings power down if psi is lost.

Zerg:    Drone is consumed when building; creep = persistent ground marks that spread.

         Zerg buildings must be on a creep-marked square (not just near Hatchery).

         Creep spread: `build_field_spread_squares N` on the provider (default 1 per game second).

         Queen **Spawn creep tumor** works on live or marked creep; tumor **Extend** requires marked creep only.


