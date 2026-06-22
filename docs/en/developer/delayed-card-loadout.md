# Delayed Loadout Cards

> **Player guide**: [../player/loadout-cards.md](../player/loadout-cards.md)

Pre-mission cards can take effect after **`delay` / `delay_minutes`** instead of at game start.

Chinese version: [../../zh/developer/delayed-card-loadout.md](../../zh/developer/delayed-card-loadout.md)

See also: [achievement-system.md](achievement-system.md), [score-grading-system.md](score-grading-system.md).

---

## 1. Scope

- **TrainingGame only** (custom / random map vs AI), same as instant cards; not campaign or multiplayer.
- Card selection and charge deduction happen **at game start**; effects fire after **in-game time** elapses.
- Delayed cards use loadout slots and cost one charge like instant cards; `min_rank` / `faction` unchanged.

---

## 2. cards.txt syntax

| Directive | Meaning |
|-----------|---------|
| `delay <seconds>` | Wait **seconds** of game time |
| `delay_minutes <n>` | Same as `delay (n×60)` |
| `tech <upgrade_id> [...]` | Grant upgrade(s) when the delay expires |

Combine with `spawn` and `resource` on one card; **one shared delay**, all effects applied together.

```txt
def card_reinforcements_delayed
title 5333
spawn footman 3
delay_minutes 10
grant_charges 1

def card_delayed_melee_weapon
title 5334
tech melee_weapon
delay_minutes 8
grant_charges 1
```

- Omit `delay` or use `0` for immediate effect (legacy behavior).

---

## 3. Runtime

At loadout apply time, `delay > 0` registers `world.schedule_after(delay_ms, callback)`.  
`delay_ms = delay_seconds × 1000 × world.timer_coefficient`.

When the timer fires: apply resources → spawns near start (no population cost) → techs; local human gets **LOADOUT_CARD_TRIGGERED** voice.

Charge is consumed when the card is scheduled successfully at game start, not when effects fire.

---

## 4. Voice (TTS)

| ID | English | Use |
|----|---------|-----|
| 5387 | (effects in) | Applied / armory |
| 5392 | (after delay) | suffix |
| 5388 | loadout card effect triggered | On fire |
| 5389–5393 | spawn / resource / tech hints | Armory |

Whole minutes announced as “N minutes”; otherwise seconds.

---

## 5. Vanilla examples

| Card | Effect | Achievement |
|------|--------|-------------|
| `card_reinforcements_delayed` | 3 footman after 10 min | `reinforcement_contract` |
| `card_delayed_melee_weapon` | `melee_weapon` after 8 min | `defeat_expert` |

---

## 6. Tests

```bash
python -m pytest soundrts/tests/test_cards.py -k delay -v
python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
```
