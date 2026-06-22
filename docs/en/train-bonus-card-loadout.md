# Train Bonus Loadout Cards

Pre-mission cards can register a **train bonus**: the **first** time a building **finishes training** a unit type, spawn **n extra copies** (no population cost, no extra resource cost). **Once per unit type per game.**

Chinese: [../zh/train-bonus-card-loadout.md](../zh/train-bonus-card-loadout.md)

---

## cards.txt

```txt
def card_footman_train_bonus
title 5396
train_bonus footman 3
grant_charges 1
```

| Directive | Meaning |
|-----------|---------|
| `train_bonus <unit_type> <n>` | On **first** completed train of this type, spawn n extras (once per type per game) |

Unlike `spawn` (immediate or delayed batch at start), `train_bonus` fires **once** on the first **TrainOrder.complete** for that type.

Example: first footman trained with `train_bonus footman 3` → **4 footmen** total; later trains are normal.

Implementation: `player._loadout_train_bonuses`; hooked from `TrainOrder.complete`.
