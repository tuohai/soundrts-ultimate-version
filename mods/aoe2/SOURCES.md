# AoE2 DE mod — data sources

## Primary (requested)

1. **Bilibili AoE2 DE Wiki** — https://wiki.biligame.com/aoe2de/首页  
   Used for: Chinese simplified names, civilization bonuses, unique unit/tech tables.

2. **aoetw** — http://aoetw.com/  
   Traditional-Chinese DE database (use **http**, HTTPS is broken).  
   Confirms armor icons and armor-class pages.

民兵→剑士→长剑士→双手剑士→冠军剑士；步弓手→弩手→劲弩手；
长矛兵→长枪兵→长戟兵；骑士→重装骑士→游侠；
轻型冲车；轻型/中型投石车；巨型投石机；
城镇中心、兵营、靶场、马厩、铁匠铺、攻城武器厂、织布机、采金法 等。

## Cross-check

3. **SiegeEngineers aoe2techtree** — https://github.com/SiegeEngineers/aoe2techtree  
   Used for: per-civ available Unit/Tech IDs (what each civ can research/train), unit HP/attack/range/cost numbers;
   **and** official DE UI strings under `data/locales/*` for mod translations.

4.**liquipedia** — https://liquipedia.net/ageofempires

## UI languages (`ui` / `ui-*`)

| Folder | Language | Source |
|--------|----------|--------|
| `ui` | English | hand-maintained |
| `ui-zh` | 简体中文 | biligame wiki |
| `ui-de` / `ui-es` / `ui-fr` / `ui-it` / `ui-pt-BR` / `ui-pl` / `ui-ru` / `ui-vi` | DE locales | aoe2techtree `strings.json` (regenerate: `_gen_aoe2_locales.py`) |
| `ui-be` | Беларуская | Russian DE names + hand blurbs |
| `ui-cs` / `ui-sk` | Čeština / Slovenčina | Polish DE names temporarily + hand blurbs (replace with proper CS/SK when available) |

Matches `res` language folders so the options menu language list stays complete when the aoe2 mod is enabled.
Custom attribute blurbs (`8510`–`8515`) and market verbs are hand-translated in the generator.

**William Wallace campaign** (`single/William Wallace/ui-*`): full mission titles / intros / objectives for the same language set; regenerate with `_gen_wallace_locales.py`.

## Civ pages used

| Civ | biligame |
|-----|----------|
| 不列颠 | https://wiki.biligame.com/aoe2de/不列颠 |
| 法兰克 | https://wiki.biligame.com/aoe2de/法兰克 |
| 中国 | https://wiki.biligame.com/aoe2de/中国 |
| 蒙古 | https://wiki.biligame.com/aoe2de/蒙古 |
| 拜占庭 | https://wiki.biligame.com/aoe2de/拜占庭 |
| 日本 | https://wiki.biligame.com/aoe2de/日本 |
| 条顿 | https://wiki.biligame.com/aoe2de/条顿 |
| 维京 | https://wiki.biligame.com/aoe2de/维京 |
| 越南 | https://wiki.biligame.com/aoe2de/越南 |
| 葡萄牙 | https://wiki.biligame.com/aoe2de/葡萄牙 |
| 阿兹特克 | https://wiki.biligame.com/aoe2de/阿兹特克 |
| 凯尔特 | https://wiki.biligame.com/aoe2de/凯尔特 |
| 马里 | https://wiki.biligame.com/aoe2de/马里 |

Unique units: 长弓兵 / 掷斧兵 / 诸葛弩 / 蒙古突骑 / 甲胄骑兵 / 武士 / 条顿骑士 / 狂战士 / 藤甲弓兵 / 风琴炮 / 美洲豹武士 / 靛蓝突袭者 / 女卫兵

## SoundRTS adaptations

- 4 resources (gold / wood / food / stone) in SoundRTS order as resource1–4.
- Maps omit starting_resources / starting_units (race defaults in rules.txt). Starting squares (TC) get stone_mines + orchard only; neutral wildlife (sheep → food_livestock; deer / boar → food_carcass) is ~3–4 squares away (never on/adjacent to TC). Villagers can_herd + gather orchard/carcass/livestock/stone/farm.
- **Monastery relics (rules-driven):** monks ``inventory_capacity 1`` pick up ``relic``. Monastery: ``inventory_capacity 10``, ``receive_items 1``, ``accepted_items relic``, ``accept_from self``, ``accept_givers monk``, ``apply_inventory_production 1``. Relic: ``inventory_production_rates 0.5 0 0 0`` + ``inventory_victory 1``. Parameters: ``inventory_victory_time 1000`` (≈ DE 200 years). Engine: ``apply_inventory_production`` / ``inventory_production_rates`` / ``team_inventory_production_bonus_pct`` / hold-all timer in ``world_inventory_victory.py`` — no type-name hardcoding.
- **Aztecs:** ``team_inventory_production_bonus_pct 33``; +50 start gold; villager ``carry_capacity 13``; military ``time_cost -13%``; ``research_stack_hp_bonus 5 monk`` (each monastery tech has ``research_stack_hp 1``); no stables/cavalry/stone walls/Thumb Ring/Ring Archer Armor/Keep/Galleon/Heated Shot; Dark Age ``aztec_eagle_scout``; ``jaguar_warrior`` + ``atlatl`` / ``garland_wars``.
- **Celts:** infantry +15% speed from Feudal; lumberjacks +15%; siege fire 25% faster; workshop train −17%; ``woad_raider`` + ``stronghold`` / ``furor_celtica``. No 2HS/Champion, Arbalester, Thumb Ring, CA, Bloodlines, Hussar, Paladin, Bracer, Plate Barding, Architecture, Bombard Tower, Crop Rotation, Cannon Galleon. William Wallace campaign: player ``celts``, English ``faction britons``.
- **Malians:** buildings wood −15% except farms; barracks units +1/+2/+3 pierce armor Feudal/Castle/Imperial (``militia spearman``, not Gbeto); villagers ``gather_qty_goldmine 10%`` (DE drop-off +10% gold); ``gbeto`` + ``tigui`` (``base_shots 8``) / ``farimba`` (cavalry +5 mdg). Team: university techs ``time_cost -44%`` (80% faster). No Gambesons, Halberdier, Blast Furnace, Bracer, Plate Barding, Arbalester, Heavy CA, Hand Cannoneer, Paladin, Hussar, Architecture, Siege Engineers, Bombard Tower, Siege Ram, Galleon, Elite Cannon Galleon, Illumination.
- **Farm mill techs (DE):** Horse Collar / Heavy Plow / Crop Rotation (farm_food_bonus 75/125/175). Base farm food 175; new farms only get the bonus (via finalize_new_building). Heavy Plow also carry_capacity +1 on villagers. Reseed production_cost = 60 wood. **Mongols (AoE4-like):** ``mongol_herdsman`` builds ``pasture`` (not farm), cannot build mill, no farm mill techs; pasture needs ``town_center`` only and stores food (``resource3``). Market remapped to ``mongol_market`` (``town_center`` + Feudal, no mill).
- **Market (rules-driven, 1.4.6.9):** Engine API in `worldmarket.py` / `worldorders/market.py` — no hardcoded wood/food/stone or gold-only trade.
  - **parameters:** `market_currency resource1`; `market_commodities resource2 100 resource3 100 resource4 100`; `market_menu_labels` use `resourceN` (not deposit type `wood`, which is the grove titled 树林); tax 300‰ / Guilds 150‰; `tribute_resources` all four; `trade_tile_scale` / `trade_shrink` / `trade_reward_cap`.
  - **market:** `is_market 1`, trains `trade_cart`, researches Caravan / Guilds / Coinage / Banking.
  - **trade_cart:** `trade_hubs market`, `trade_rewards resource1` (gold). **trade_cog:** `trade_hubs is_dock shipyard`, same gold reward.
  - **Docs:** `doc_src/src/zh/mod/market-system.rst` (en twin), `doc_src/src/zh/player/market-and-trade.rst`, release notes §1.4.6.9.
- **Dock navy economy (DE):** shipyard (Dark Age, like DE Dock) trains fishing_ship + trade_cog; researches gillnets / shipwright. **Natural fish (rules-driven):** ``shore_fish`` (200 food, ``gather_from_shore 1`` — villagers from adjacent land, fishing ships on water) and ``deep_fish`` (225 food, ships only) placed on water squares. fishing_ship ``can_gather_deposit shore_fish deep_fish`` (rates 0.28 / 0.41) plus fish_trap (养鱼场, Dark Age, 100W, 715 food) on water. Villager shore rate 0.23. Gillnets: gather_time on fish_trap / shore_fish / deep_fish −20%. Japanese age work-rate applies to all three. Shipwright: ships wood −20% and time_cost −35% (~+54% create). trade_cog uses trade order between docks (same gold loop as carts). Transport / galley / trade cog stay Feudal.
- **Castle Imperial techs (DE):** Conscription (time_cost -33% on infantry/archer/cavalry/UU + castle petard/trebuchet); Hoardings (+1000 castle HP); Sappers (villager mdg_vs building/stone +15); Spies (reveal_enemies, gold = 200 × enemy workers).
- **Gather (AoE2 DE wiki style):** gather_mode continuous, carry_capacity 10 (hunt carcass 35). Villager gather_rate in resources/sec: wood 0.39, gold 0.38, stone 0.36, forage 0.31, hunt 0.41, farm 0.32. Deposits use extraction_* 0 (rate is on the villager). Lumber/mining techs: cumulative % gather_time cuts (wood −17/−31/−37; gold&stone −13/−24). Civ dark-age: Britons food_livestock −20% (shepherds), Franks orchard −13%, Mongols food_carcass −29% (hunters). Wheelbarrow/Hand Cart: carry_capacity +3 / +7.
- Costs and research/train times are **exact AoE2 DE** values from SiegeEngineers aoe2techtree (data.json); unit-line upgrades use DE upgrade-research costs.
- Ages are class phase with DE costs/times. Cleared res demo universal phase bonus (no free mdg/hp for every civ). Civ age rewards use race on_phase, research_cost_discount, and advance_cost_discount. Military lines use line_upgrade 1 + building can_research (not age-only morph).
- Combat stats are **exact AoE2 DE** from the same data; bonus damage vs armor classes mapped to SoundRTS mdg_vs/rdg_vs.
- **Attack wind-up (DE Attack Delay):** ranged use ``rdg_ready``, melee-projectiles use ``mdg_ready`` (seconds). Values from the AoE2 wiki Attack delay tables (DE / LotW). Ships and defensive buildings stay ``0`` (instant release). ``*_cd`` is set to DE Rate of Fire minus Attack Delay so continuous shot interval stays ≈ RoF (SoundRTS applies ready every shot).
- **Accuracy (DE Accuracy Percent):** ``rdg_cover`` / ``mdg_cover`` as 0–100 (omit or 0 = 100%%). Examples: archer 80, crossbow 85, arbalester 90, skirmisher 90, cavalry archer 50, hand cannoneer 65, longbowman 70 / elite 80, chu ko nu 85, mangudai 95, trebuchet 80 (+``rdg_cover_vs building 20``), bombard cannon 92, cannon galleon 50. Thumb Ring: ``effect bonus rdg_cover 100`` on ``archer_unit -hand_cannoneer`` (clamped to 100%%).
- **Chu Ko Nu (DE multi-projectile):** ``damage_seq rdg 3|5 (secondary 3 0) (interval 0.23)`` — first arrow = live pierce (+0 melee); extras = fixed 3 pierce + 0 melee (not upgraded). Elite = 5 arrows. Volley CD after last arrow so practical RoF ≈ 3+(n−1)×0.23.
- **Bonus damage / tech filters:** category roots via is_a — infantry, cavalry, archer_unit, siege_unit, building. effect_bonus_targets should list these roots (plus -exclude).
- Skirmisher line includes Imperial Skirmisher (wired for Vietnamese) and camel line Imperial Camel Rider (ready for Hindustanis).
- Tower line: scouttower → research guardtower → keeptower; cannontower separate (Chemistry). Fortified wall/gate via university line_upgrade.
- University extras: Murder Holes, Masonry, Architecture, Heated Shot, Treadmill Crane.
- **Unique techs (full DE, not stand-ins):** Yasama ``rdg_seq_*`` (+2 arrows); Kataparuto fire rate + ``unpack_time -75%`` (pack/unpack transition); Crenellations range + ``passenger_attack_types infantry``; Chieftains cavalry/camel bonus + ``kill_resource_vs``; Paper Money ``gather_byproduct wood 0.014``; Circumnavigation ``reveal_map`` + ships ``time_cost -33%``; Arquebus ``projectile_lead`` + proj speed +0.5/+0.2.
- **Trebuchet pack/unpack (DE, rules-driven):** ``packable 1``, ``unpack_time`` / ``pack_time``, optional ``packed_mdf`` / ``packed_rdf``, ``spawn_packed``. Spawn packed; move auto-packs; attack auto-unpacks; stop cancels transition. Progress via ``completeness`` → ``proportion_*``. Menu: ``pack`` / ``unpack`` (Chinese UI **打包** / **拆包**).
