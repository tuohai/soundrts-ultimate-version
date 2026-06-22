# Unit default behavior configuration (`rules.txt`)

Map and mod authors can set each unit type’s **initial behavior at game start** in `rules.txt`:

- **Default AI mode** (`ai_mode`): offensive / defensive / guard / chase
- **Auto-gather** (`auto_gather`): workers start gathering automatically
- **Auto-repair** (`auto_repair`): workers start repairing automatically
- **Auto-explore** (`auto_explore`): mobile units start exploring automatically

Players can still change these in-game after spawn.

---

## 1. Overview

| Field | Values | Default | Applies to | Description |
| --- | --- | --- | --- | --- |
| `ai_mode` | `offensive` / `defensive` / `guard` / `chase` | soldiers=`offensive`, workers=`defensive` | combat units | starting AI mode |
| `auto_gather` | `1` / `0` | workers=`1` | workers | auto-gather on start |
| `auto_repair` | `1` / `0` | workers=`1` | workers | auto-repair on start |
| `auto_explore` | `1` / `0` | `0` | mobile units | auto-explore on start |
| `can_auto_explore` | `1` / `0` | `0` | mobile units | show enable/disable auto-explore in command menu |

> Write these in the unit’s `def <name>` block. Omitted fields use the defaults above.

**Campaign example** (ch. 24–27): key NPCs use `escort` or `ai_mode guard` so they do not chase before delivery/duel. After alliance, triggers switch modes:

- `(set_ai_mode offensive c2 1 npc_count_roland …)` — Roland goes offensive after token (ch. 25)
- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((go c1)))` — ch. 27 (`raynor7`): **Marco only** goes offensive; escorts move to **c1** to clear the arena
- `(allied_assist computer1)` — all allied combat units on guard → chase
- `(allied_assist computer1 c2 4 npc_archer_escort)` — only escort archers → chase
- `(allied_control computer1 c2 4 npc_knight_escort)` — escort knights under player command (stay on guard); others auto → chase

For yield duels (`yield_on_defeat`), enable at runtime via `(set_yield_on_defeat 1 …)` rather than in `rules.txt` at spawn, so NPCs are killable before the token is delivered. See [campaign-secret-letter-alliance.md](campaign-secret-letter-alliance.md).

> **`auto_explore` vs `can_auto_explore`**:
> - `auto_explore` — whether the unit **starts** with auto-explore on.
> - `can_auto_explore` — whether the command menu offers **enable/disable auto-explore**.
> - Independent: e.g. only knights get `can_auto_explore 1`, or `auto_explore 1` for scouts at start.

---

## 2. AI mode (`ai_mode`)

### 2.1 Modes

| Value | Name | Behavior |
| --- | --- | --- |
| `offensive` | Offensive | attack **hostile** units in the current square (common default) |
| `defensive` | Defensive | retreat from **hostile** threats when unfavorable; engage when ahead |
| `guard` | Guard | hold position; counter-attack only if enabled |
| `chase` | Chase | pursue visible **hostile** units into range |

> **Patrol** is a **command with a route**, not an AI mode. You cannot write `ai_mode patrol`. Use `guard` or `chase` for similar effects.

### 2.2 Examples

```
def knight
class soldier
...
ai_mode guard

def footman
class soldier
...
ai_mode defensive
```

### 2.3 Neutral units

**Player units** in `offensive`, `defensive`, or `chase` mode:

- **do not auto-attack** neutral units (`computer_only ... neutral` creeps / NPCs / wildlife);
- **do not flee** because of neutrals (defensive mode only weighs real hostile threats);
- to fight a neutral, issue a **forced attack** (`imperative` — e.g. Ctrl+click on the unit;
  the engine converts imperative `go` into `attack`).

> **Voice**: hunt animals (`is_huntable` / `herdable`, e.g. deer, sheep) are announced as
> "deer , animal", **not** "neutral , NPC". Story NPCs (`quest_npc`, etc.) still say
> "neutral , NPC". See [hunting-system.md](hunting-system.md).

> `guard` mode is unchanged: no proactive attacks; counter-attack only if enabled and hit.
> Neutral computer creeps still use forced `guard` + counter-attack on their side.

### 2.4 Notes

- Invalid values are ignored (logged) and fall back to default.
- Neutral creeps (`computer_only ... neutral`) are still forced to `guard` + counter-attack regardless of `ai_mode`.

---

## 3. Auto-gather / auto-repair

For **workers** only:

- `auto_gather 1` — idle workers go gather when a deposit and warehouse exist nearby.
- `auto_repair 1` — idle workers repair damaged allies in the same square (needs `can_repair 1`).

Both default to **on**. Set `0` in the worker def to disable at start. Players can still toggle in-game.

**`can_repair`** — `1` or `0`. Default `1` on workers. When `0`, repair orders and auto-repair are disabled.

---

## 4. Default capture order (`can_capture`)

For units with **attack** skills, controls the default right-click order on enemies with
**`capture_hp_threshold 100`** (contact capture):

| Value | Behavior |
| --- | --- |
| `1` (default) | Default **capture** order; AI uses contact capture |
| `0` | Default **attack/move**; AI attacks normally |

Does **not** block capture at lower thresholds (e.g. `30`) via combat damage — only the
threshold-100 contact capture path and default right-click order.

```
def footman
class soldier
can_capture 1

def archer
class soldier
can_capture 0
```

See also random-map capturable barracks in `docs/zh/player/英雄无敌与文明5玩法说明.md`.

---

## 5. Auto-explore

For any unit with speed > 0. Controlled by `auto_explore` (initial state) and `can_auto_explore` (menu option).

- `can_auto_explore 1` — command menu shows enable/disable auto-explore (only on units that have it).
- `auto_explore 1` — starts exploring when idle; combat uses `ai_mode` when enemies appear.

**Runtime**: other orders pause explore; resumes when idle again. **Disable auto-explore** always available while exploring. **Enable** only if `can_auto_explore 1`. Computer AI exploration is separate.

---

## 6. Combined example

```
def peasant
class worker
auto_gather 1
auto_repair 0
ai_mode defensive

def knight
class soldier
auto_explore 1
can_auto_explore 1
ai_mode guard

def footman
class soldier
ai_mode defensive
```

---

## 7. FAQ

**Q: Why doesn’t `ai_mode patrol` work?**  
A: Patrol needs a path. Valid values: `offensive`, `defensive`, `guard`, `chase`.

**Q: `auto_explore` on a building?**  
A: Ignored (speed 0).

**Q: `auto_gather` on a soldier?**  
A: Only meaningful on workers.

**Q: Will offensive/chase units auto-attack neutral NPCs?**  
A: No. Offensive, defensive, and chase modes ignore neutrals for auto-attack and flee;
use a forced attack command to fight them.

**Q: Why do archers attack a barracks on right-click but footmen capture it?**  
A: Check `can_capture`. Default `1` → capture on `capture_hp_threshold 100` targets; `0` → normal attack.

---

## 8. Field reference

| Field | Type | Valid values |
| --- | --- | --- |
| `ai_mode` | string | `offensive` / `defensive` / `guard` / `chase` |
| `auto_gather` | int | `1` / `0` |
| `auto_repair` | int | `1` / `0` |
| `auto_explore` | int | `1` / `0` |
| `can_auto_explore` | int | `1` / `0` |
| `can_capture` | int | `1` / `0` |
