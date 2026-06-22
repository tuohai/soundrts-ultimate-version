# Campaign & co-op campaign improvements (1.4.3.9)

This guide describes SoundRTS **Age of Empires Definitive Edition–style** single-player and cooperative campaigns: mission browser, five difficulty tiers, story-mission co-op, enemy scaling, and lockstep-safe sync. For players, campaign authors, and modders.

Chinese version: [../../zh/player/战役与合作战役改进说明.md](../../zh/player/战役与合作战役改进说明.md).

---

## 1. Overview

### Before

- **Single-player**: chapter list only; no difficulty, synopsis, or retry on defeat.
- **Co-op** (since 1.4.2.2): multiple humans on one campaign map, but closer to a skirmish than AoE DE co-op (no difficulty tiers, player slots, allied AI partners, or shared story semantics).

### After (1.4.3.9)

| Area | Single-player | Co-op |
| --- | --- | --- |
| Menu | Mission browser: synopsis, difficulty, completed/locked | Server: campaign → chapter → **difficulty** → speed |
| Difficulty | Five tiers, saved in `user/campaigns.ini` | Same + extra scaling by **human player count** |
| Enemy scaling | Enemy HP / outgoing damage by % | Server computes once, broadcast to all clients / replays |
| Story | `intro`, objective-driven win/loss | Shared `intro`, cutscenes, F9 objectives; not “destroy all enemies” |
| Slots | One human | One slot per human; empty slots filled by **allied AI** |

Core code: [`soundrts/coop_difficulty.py`](../../../soundrts/coop_difficulty.py), [`soundrts/campaign.py`](../../../soundrts/campaign.py), [`soundrts/clientservermenu.py`](../../../soundrts/clientservermenu.py), [`soundrts/serverroom.py`](../../../soundrts/serverroom.py).

---

## 2. Single-player campaign

### 2.1 Mission browser

After picking a campaign from the main menu:

1. **Campaign synopsis** (optional) — only if `campaign.txt` defines `synopsis`; plays TTS then returns to the list.
2. **Difficulty: …** — current tier; submenu to pick Easy / Standard / Moderate / Hard / Extreme.
3. **Continue** — shortcut to the latest unlocked chapter when applicable.
4. **Chapter list** with status:
   - **Completed** — replayable, full title shown.
   - **Current** — playable, full title.
   **Locked** — number + “locked” only; **not selectable** (no title spoiler).
5. **Back**.

Progress is stored in [`user/campaigns.ini`](../../../soundrts/paths.py) (`chapter` + `difficulty` per campaign id).

### 2.1.1 Hero growth and cross-mission carryover (rules-driven)

Configure any hero in **`rules.txt`** with **`campaign_carryover 1`** (not Raynor-specific).

| Field | Default | Effect |
| --- | --- | --- |
| `campaign_carryover_id` | def name | Save keys `hero_<id>_xp`, etc. |
| `campaign_carryover_stats` | `1` | Level + XP |
| `campaign_carryover_inventory` | `1` | Backpack |

- Saved on **victory** only; next chapter restores. **`hero_min_level`** in `campaign.txt` optional.
- **Co-op** does not persist heroes.
- Split: `campaign_carryover_inventory 0` (stats only) or `campaign_carryover_stats 0` (inventory only).

Author guide: [../developer/campaign-hero-carryover.md](../developer/campaign-hero-carryover.md).

### 2.2 Synopsis in `campaign.txt`

```txt
title 7747
synopsis 7751
```

`7751` is a voice id in `ui/tts.txt` / `ui-zh/tts.txt`. Omit `synopsis` to hide the menu entry.

Example: [`res/single/The Legend of Raynor/campaign.txt`](../../../res/single/The Legend of Raynor/campaign.txt).

### 2.3 Difficulty and enemy scaling

- Difficulty persists in `campaigns.ini`; default **Standard**.
- `MissionChapter.run` sets `enemy_hp_factor` / `enemy_damage_factor` on the session.
- Only **enemy** (non-human, non-neutral) units: **HP** at spawn, **outgoing damage** on hit.
- **Standard + solo** = 100% / 100% (unchanged baseline).
- Solo never applies the player-count multiplier (always counts as 1 human).

Base tiers (HP / damage):

| Tier | Enemy HP | Enemy damage |
| --- | --- | --- |
| Easy | 70% | 70% |
| Standard | 100% | 100% |
| Moderate | 120% | 115% |
| Hard | 145% | 135% |
| Extreme | 180% | 165% |

### 2.4 Victory and defeat

- **Win**: voice **Next mission unlocked**; menu **Continue** (next chapter) or **Quit**; bookmark advances.
- **Loss**: menu **Retry this mission** or **Quit**.

---

## 3. Cooperative campaign

### 3.1 Player flow

1. Server lobby → **Co-op campaign** → campaign (only if `coop_campaign 1` in `campaign.txt`) → chapter → **difficulty** → **speed** → create room.
2. **No treaty step** (`treaty` fixed to 0).
3. Others join; host starts.
4. Everyone gets the chapter **intro**, then map **triggers** drive win/loss.
5. Any human completing primary objectives wins for the team; host bookmark advances when the host wins and bookmark equals the current chapter.

### 3.2 Campaign table and mission maps

- **Co-op menu**: driven by `coop_campaign` / `coop_intro` / `coop_missions` in each campaign’s `campaign.txt` (no hard-coded campaign names in the engine).
- **Map load**: co-op and single-player share `N.txt`; the server loads via `ensure_chapter_map` — no `N.coop.txt`.
- Authoring: [coop-campaign.md](../developer/coop-campaign.md) and §4 below.

### 3.3 Story mission, not skirmish

- Victory/defeat from `add_objective`, `objective_complete`, `defeat`, etc. — not wiping all AI players.
- `world.is_campaign = True`: campaign music, trigger computers announced as “NPC”, no “player defeated/quit” for script AIs.
- `cut_scene` and objectives broadcast to the trigger owner **and all allies**.
- `MultiplayerGame.pre_run` plays `world.intro` for co-op.

### 3.4 Player slots and allied AI partners

Example map: [`res/single/The Legend of Raynor/1.txt`](../../../res/single/The Legend of Raynor/1.txt).

```txt
nb_players_min 1
nb_players_max 2
player_start 1 a1 raynor footman footman
player_start 2 h8 raynor2 footman archer
computer_only e5 ...
```

| Field | Meaning |
| --- | --- |
| `nb_players_max` | Co-op slot count |
| `nb_players_min 1` | Solo + AI partners allowed |
| `player_start N …` | Spawn square and units for slot N |
| `computer_only` | Mission enemies (`"ai"` alliance vs humans on alliance 1) |

[`Game._fill_coop_ai_partners`](../../../soundrts/serverroom.py) fills empty slots with **aggressive** allied AI; all humans + partners start on **alliance 1**.  
`player1`, `player2`, … in triggers map to humans in join order; AI-only slots are usually not targeted by story triggers.

### 3.5 Difficulty and player count

On top of the base tier:

```
count multiplier = 100 + (humans - 1) × 20   (solo = 100%)
final hp%        = base hp% × multiplier // 100
final damage%    = base damage% × multiplier // 100
```

Example: **Hard** + **3 humans** → base 145/135, multiplier 140 → ~**203% HP / 189% damage**.

Server sends `coop_difficulty` before `start_game`; integer math only. Replay seed line may append `hp% damage%` (old replays default to 100).

### 3.6 Place names and campaign resources

Logical map name `CampaignName/chapter` triggers [`apply_campaign_from_map_name`](../../../soundrts/lib/resource.py) so `rules.txt` and campaign `tts.txt` load on clients; square names like `loc_ch02_*` resolve through TTS instead of reading raw keys.

### 3.7 Cross-chapter `campaign_flag`

Co-op does **not** set `world.campaign`, so `campaign_flag` with no local campaign object returns **False** (deterministic no-op). In-mission `set_map_flag` / `map_flag` still work on synced world state.

---

## 4. Map authoring

### 4.1 Campaign table (`campaign.txt`)

Declare co-op like Age of Empires in **`campaign.txt`**. Do **not** ship parallel `N.coop.txt`
files; single-player and co-op load the same `N.txt` mission map.

```txt
title 7747
synopsis 7751
coop_campaign 1
coop_intro 0
coop_missions 1-29
```

| Field | Meaning |
| --- | --- |
| `coop_campaign` | `1` — show in server **Co-op campaign** menu |
| `coop_intro` | Cutscene chapter numbers in the co-op flow (e.g. prologue `0`) |
| `coop_missions` | Mission chapters playable in co-op (`1-29`, space lists, etc.) |

### 4.2 Co-op map fields (`N.txt`)

1. `nb_players_min 1` / `nb_players_max 2` and multiple `player` blocks (or `player_start`).
2. Duplicate key triggers per co-op player where needed (`add_objective`, `objective_complete`), or drive globally via `player1` if shared.
3. Optional `(alliance 1)` for co-op humans; enemies via `computer_only`.
4. Optional `intro` / `cut_scene`; balance via engine difficulty — no manual stat hacks required.

Single-player still registers one human and uses only the first spawn; empty co-op slots are not filled by AI in solo.

### 4.3 Related fixes (1.4.3.0)

- Multi-computer maps: completing objectives wins without having to kill every script AI (`Player.victory` iterates a snapshot).
- **F12** selects no target in campaigns; trigger computers announced as “NPC”.

---

## 5. Migration summary

| Old | New |
| --- | --- |
| Chapter list only | Synopsis + difficulty + completed/locked + retry |
| Co-op without difficulty / treaty step | Five tiers + count scaling; no treaty |
| Co-op as skirmish | Shared intro/cutscenes/objectives; AI partners |
| `N.coop.txt` or file-based co-op detection | `campaign.txt` flags + shared `N.txt` |
| Raw `loc_*` keys in co-op | Campaign TTS layer, localized names |
| Standard = baseline | Still 100%/100%; other tiers per table |

---

## 6. Tests

```bash
python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
python -m pytest soundrts/tests/test_changelog_1429b_campaign_browser_difficulty.py -q
python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
python -m pytest soundrts/tests/test_coop_campaign_place_names.py -q
python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
python -m pytest soundrts/tests/test_changelog_1428_campaign_victory_f12.py -q
```

---

## 7. See also

| Doc | Topic |
| --- | --- |
| [progressive-campaign-objectives.md](progressive-campaign-objectives.md) | `register_objective` |
| [campaign-secret-letter-alliance.md](campaign-secret-letter-alliance.md) | The Legend of Raynor ch. 24–27 |
| [coop-campaign.md](coop-campaign.md) | Short co-op reference |
| `doc_src/src/en/mapmaking.rst` | Mission syntax |

| Source | Role |
| --- | --- |
| `soundrts/campaign.py` | SP browser, co-op metadata (`coop_*`), bookmarks, difficulty |
| `soundrts/coop_difficulty.py` | Tier table and count multiplier |
| `soundrts/clientservermenu.py` | Co-op menu, `srv_coop_difficulty` |
| `soundrts/serverroom.py` | AI partners, difficulty broadcast |
| `soundrts/game.py` | `is_coop_campaign`, intro, bookmark update |
| `soundrts/worldunit/worldcreature.py` | Enemy HP scale |
| `soundrts/combat/damage_effects.py` | Enemy damage scale |
| `soundrts/lib/resource.py` | Campaign resource stack, place TTS |
