# SoundRTS 1.4.4.5 Release Notes

**Version**: 1.4.4.5  
**Type**: Random-map gameplay + capture rules + AI amphibious ops + scoring fix + hotkey remapping  
**Audience**: Random-map and vs-AI players; map/mod authors; anyone testing Ctrl+Shift+F4 view switch; players customizing hotkeys

---

## Highlights

1.4.4.5 adds **Heroes of Might and Magic (HoMM)** and **Civilization V (Civ5)**-inspired POIs and victory modes on **random maps (RMG)**; clarifies **default capture (occupy) orders** when `capture_hp_threshold` is **100**; gives computer AI **cross-water gathering and amphibious assault** on naval maps; **batch training** scales to **remaining population** when headroom is low; fixes **Ctrl+Shift+F4** exploits around post-game score, achievements, medals, and cards; and ships a full **key mapping editor** (layered/classic schemes, search, variants, alias keys, import/export).

---

## Random map: HoMM / Civ5-inspired gameplay

Core RTS controls are unchanged. New content is **map objectives, points of interest (POI), and victory conditions** — not turn-based play or full tech trees.

| Inspiration | In SoundRTS |
| --- | --- |
| HoMM: explore ruins | Enter square → **ruin discovered** → resources (`ancient_ruin`) |
| HoMM: capturable sites | Clear guards → capture **barracks**, train units (`captured_barracks`) |
| HoMM: central creeps | **Creep strength** menu scales central hostile stacks |
| Civ5: multiple victories | RMG modes: **conquest / economic / exploration / survival** |
| Civ5: explore / gold win | Exploration: discover all ruins; economic: total gather target |
| Civ5: survival timer | Survive until countdown with main base intact |
| Civ5: map goodies | Optional **treasure** menu: extra mines or pick-up items |

**How to start**: Main menu → Start → **Random map** → pick template and **victory mode** → generate. Multiplayer needs the same share code (includes victory field).

Full player guide (Chinese): `docs/zh/player/英雄无敌与文明5玩法说明.md`. RMG menus and share codes: random-map player docs / `doc_src/.../randommap.rst`.

---

## Default capture order (`can_capture`)

When an enemy unit or building has **`capture_hp_threshold 100`**, capture is **contact-only** (no damage on occupy):

- Units with **`can_capture 1`** (default) and an `attack` skill use the **default capture order** on such targets; standing on target captures immediately.
- **`can_capture 0`** units default to attack/move, not capture.
- **Threshold below 100** (e.g. 30) still requires fighting down to the capture threshold — **not** covered by this default-order path.

Mod example — footmen capture, archers only attack:

```
def footman
class soldier
can_capture 1

def archer
class soldier
can_capture 0
```

See [unit-default-behavior.md](unit-default-behavior.md) §4.

---

## AI cross-water operations

On maps with water, computer players can reach opposite shores:

- **Amphibious gathering**: ferry workers by transport when deposits are only reachable across water.
- **Amphibious landings**: schedule boat (and when cheaper, air) transport to move ground armies for attacks and expansions.
- **Naval upkeep**: maintain dock and warships; patrol and support river/lake fights.

---

## Train: scale batch to remaining population

When you train **multiple units** in one order and **population headroom** is too low for the full batch, the order **no longer fails entirely**. The building trains **as many as fit**:

- Example: queue **5 footmen** with only **3** pop left → the barracks trains **3 footmen**.
- **Zero** headroom still reports not enough population (unchanged).
- Resource cost and train time match the **actual count** trained.

---

## Fix: Ctrl+Shift+F4 view switch and scoring

In single-player / training (cheat mode allowed), **Ctrl+Shift+F4** switches the observed player. Previously:

- Switching to the AI before a loss could grant **your** score, achievements, medals, and cards when the **AI** won.
- Switching to the AI and letting an **NPC** defeat the AI could leave you last standing and still grant a full **victory** payout.

**Now**:

- The **human who started the match** is pinned for scoring; view switch only changes observation/control binding.
- After the **first** view switch, scoring opponents defeated **for the first time** (e.g. NPC kills the AI you are watching) **do not** count as your win or AI-defeat bonus.
- Opponents you already defeated **before** switching still count — legitimate wins while briefly observing another player still pay out.
- AI wins or passive “last player standing” wins after switching → scored as **your defeat**; no victory achievements/medals/cards.

---

## Key mapping editor

Main menu **Options → Key mapping** (sibling of Hotkey scheme) — voice-driven remapping without editing text files.

### Entry and storage

| Item | Detail |
| --- | --- |
| Schemes | **Layered hotkeys** (8 interface layers) or **Classic hotkeys** (~179 primary bindings, full legacy coverage) |
| Storage | Per **current mod**: `user/hotkey_overrides/{mod_key}.json` |
| When active | **Next game start**; replaces by binding ID so old keys do not linger (unlike append-only `bindings.txt`) |
| Scheme flag | Same JSON: `layered_hotkeys` `1` = layered, `0` = classic |

### Features

- **Primary catalog**: list current key per action; Enter to remap; conflict announce + confirm replace
- **Search hotkeys**: filter by keyword (EN/ZH) — especially useful on the classic list
- **Advanced variants**: Shift/Ctrl modifier commands, five-square movement, etc.
- **Alias keys**: remap secondary keys independently (e.g. LCTRL/RCTRL, RETURN/KP_ENTER)
- **Import/export**: JSON to clipboard; merge or replace
- **Localized labels**: catalog TTS IDs 5500–5684; group 1–5 = selection ratio, 6–9 = control groups

### Label fixes

| Default key | Action | Menu label |
| --- | --- | --- |
| Alt+Space | First-person (`immersion`) | **First-person mode** |
| Ctrl+F2 | Display toggle (`fullscreen`) | **Display toggle** |

Player guide: [layered-hotkeys.md](layered-hotkeys.md). Developer doc: [hotkey-mapping-editor.md](../developer/hotkey-mapping-editor.md).

---

## For mod / map authors

| Topic | Reference |
| --- | --- |
| RMG modes & POI | `soundrts/randommap.py`, `res/rules.txt` (`ancient_ruin`, `captured_barracks`) |
| `can_capture` / `capture_hp_threshold` | `doc_src/src/en/modding.rst` (Capture / default occupy order) |
| AI water | `soundrts/worldplayercomputer_water.py`, `worldplayercomputer.py` |

---

## Upgrade notes

- Overwrite install; no save migration.
- Mods unchanged in `rules.txt`: `can_capture` defaults to `1`.
- Campaign, co-op campaign, and multi-human multiplayer still exclude achievements/loadout scoring (same as 1.4.4.4); view switch is disabled in multi-human games anyway.

---

## Documentation

| Doc | Topic |
| --- | --- |
| `docs/zh/player/英雄无敌与文明5玩法说明.md` | HoMM/Civ5 RMG guide (zh) |
| [unit-default-behavior.md](unit-default-behavior.md) | `can_capture` |
| [achievements.md](achievements.md) | Achievements & armory (from 1.4.4.4) |
| [layered-hotkeys.md](layered-hotkeys.md) | Layered/classic hotkeys & in-game mapping |
| [hotkey-mapping-editor.md](../developer/hotkey-mapping-editor.md) | Key mapping editor (developer) |
| `doc_src/src/en/relnotes.rst` | Full version history |

---

## Quick test

```bash
python -m pytest soundrts/tests/test_randommap.py soundrts/tests/test_capture_default_order.py soundrts/tests/test_change_player_scoring.py soundrts/tests/test_train_population.py soundrts/tests/test_worldplayercomputer_water.py soundrts/tests/test_ai_naval_m3.py soundrts/tests/test_hotkey_editor.py soundrts/tests/test_hotkey_editor_phase2.py soundrts/tests/test_hotkey_editor_phase3.py soundrts/tests/test_hotkey_editor_phase4.py soundrts/tests/test_hotkey_editor_phase5.py soundrts/tests/test_hotkey_catalog_tts.py -q
```

1. RMG: try all four **victory modes**; enter ruins; capture barracks.  
2. Water map vs AI: watch for ferrying workers or amphibious attacks.  
3. Threshold-100 targets: footman defaults to capture; archer (`can_capture 0`) defaults to attack.  
4. Batch train near pop cap: confirm only the affordable count is queued.  
5. Training: Ctrl+Shift+F4 to AI — confirm no victory rewards from AI/NPC outcomes.  
6. **Options → Key mapping**: try search, primary remap, alias keys (e.g. KP_ENTER), import/export JSON.
