# Burst attacks (`damage_seq`) and repeating crossbow

Since SoundRTS 1.3.8.2 (enhanced in **1.4.3.6**), units can perform **burst / sequence attacks**: one attack cycle fires several hits in quick succession, similar to the Chu Ko Nu (repeating crossbow) in *Age of Empires*. Each shot rolls hit, crit, and debuff separately.

Official reference: `doc_src/src/en/modding.rst` (Combat system → `damage_seq`).

---

## 1. Overview

| Aspect | Behavior |
| --- | --- |
| Total damage per cycle | Still equals base `mdg` / `rdg` (split across shots) |
| Shots per cycle | Up to **6** (`damage_seq … <times>`) |
| Hit rolls | **Independent** per shot |
| Cooldown | `mdg_cd` / `rdg_cd` starts after the **full burst** ends |
| Launch sounds | One `launch_mdg` / `launch_rdg` **per shot** |

---

## 2. rules.txt configuration

### 2.1 Syntax

```text
damage_seq mdg|rdg <times> [(damage d1 d2 ...)] [(interval seconds)]
```

Define base `mdg` or `rdg` **before** `damage_seq`.

### 2.2 Auto split (since 1.4.3.6)

Omit `(damage …)` to divide base damage evenly:

```text
rdg 6
damage_seq rdg 3 (interval 0.25)
```

→ three shots of 2 damage each. Works with fractional base damage (e.g. `rdg 7.5` with 3 shots → 2.5 each).

### 2.3 Manual split

Integer segment values must sum to the base damage (same units as in rules):

```text
mdg 12
damage_seq mdg 3 (damage 6 3 3) (interval 0.2)
```

Manual `(damage …)` uses **integer** values only; fractional base damage (e.g. `rdg 2.5`) cannot be expressed this way — use auto split instead.

### 2.4 Interval

- `(interval 0.25)` — seconds between shots
- If `times > 1` and interval is omitted or `0`, default **0.25** s

### 2.5 Ranged burst tips

- Set `rdg_projectile 1` for projectile behavior (high-ground rules, etc.)
- Use a longer `rdg_cd` than a single-shot archer: burst DPS is higher but each **cycle** still respects total `rdg`

Example (built-in unit):

```text
def repeating_crossbowman
class soldier
rdg 6
rdg_cd 2.5
rdg_range 4
rdg_projectile 1
damage_seq rdg 3 (interval 0.25)
```

---

## 3. Sounds (`style.txt`)

Each shot triggers `launch_rdg` or `launch_mdg`. List multiple sound IDs so shots can vary:

```text
def repeating_crossbowman
is_a archer
launch_rdg 1042 1042 1042
```

Hit / miss sounds (`rdg_hit`, `rdg_missed`, …) still play per successful hit roll as usual.

---

## 4. Built-in example: `repeating_crossbowman`

| Item | Value |
| --- | --- |
| Location | `res/rules.txt` |
| Upgrade | `archer` → `repeating_crossbowman` (`can_upgrade_to`) |
| Voice (ZH) | 诸葛弩手 (`tts.txt` id 5082) |
| Stats | 3×2 ranged damage per cycle, 2.5 s reload, range 4 |

---

## 5. Common mistakes

| Problem | Cause / fix |
| --- | --- |
| `damage_seq` ignored | Base `mdg` / `rdg` not defined, or segment sum ≠ base (manual split) |
| Wrong interval | Before 1.4.3.6, interval was ignored (fixed); check game version |
| Fractional damage + manual `(damage …)` | Use auto split instead |
| More than 6 shots | Engine caps at 6 per attack |
| Only one launch sound | Expected for non-burst units; burst units need per-shot handling (1.4.3.6+) |

---

## 6. Related files and tests

| File | Role |
| --- | --- |
| `soundrts/definitions.py` | Parses `damage_seq` in rules |
| `soundrts/combat/damage_effects.py` | Schedules burst hits and launch sounds |
| `soundrts/combat/attack_action.py` | Attack prep / cooldown |
| `soundrts/tests/test_damage_seq_burst.py` | Parsing and regression tests |

Run tests:

```bash
python -m pytest soundrts/tests/test_damage_seq_burst.py -q
```
