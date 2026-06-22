# SoundRTS 1.4.4.7 Release Notes

**Version**: 1.4.4.7  
**Type**: hero XP threshold formulas + post-level-up XP reset  
**Audience**: map/mod authors configuring hero leveling in `rules.txt`

---

## Highlights

1. **`xp_threshold_growth`**: auto-generate `xp_thresholds` from a formula instead of listing dozens of values by hand
2. **`level_up_reset_xp`**: optional reset of current XP to 0 after each combat level-up

---

## XP threshold formulas (`xp_threshold_growth`)

For high level caps, set `max_level` + a growth curve; rules load expands it into `xp_thresholds`:

```text
def long_hero
class soldier
max_level 100
xp_threshold_growth linear 100 50
hp_max_per_level 30
mdg_per_level 2
```

| Type | Syntax | Meaning |
| --- | --- | --- |
| linear | `linear BASE STEP` | gate = `BASE + STEP × i` (i from 0; expanded to cumulative list at load) |
| quadratic | `quadratic BASE A B` | `BASE + A×i + B×i²` (e.g. Raynor curve `quadratic 40 40 10`) |
| polynomial | `polynomial c0 c1 c2 …` | general polynomial |
| geometric | `geometric FIRST RATIO` | `FIRST × RATIO^i` (e.g. `1.08`) |

- Explicit `xp_thresholds` still works and wins when both are set.
- Child defs can `is_a` inherit `xp_threshold_growth` and override only `max_level`.

---

## Post-level-up XP reset (`level_up_reset_xp`)

```text
def my_hero
class soldier
xp_thresholds 40 50
level_up_reset_xp 1
hp_max_per_level 30
```

| Value | Behavior |
| --- | --- |
| `0` (default) | keep cumulative XP |
| `1` | set `xp = 0` after each combat level-up |

When `level_up_reset_xp 1`, prefer **per-level** `xp_thresholds` (e.g. `40 50` = 40 XP for level 2, 50 for level 3), not cumulative totals (e.g. `40 90`).

Example: after reaching level 2, Tab status shows XP **0/50** when thresholds are `40 50`.

---

## See also

- Modder guide: `doc/en/modding.htm` (Heroes); source `doc_src/src/en/modding.rst`
- Hero starting level, full heal on level-up, etc. (1.4.4.6): `docs/en/player/release-1.4.4.6.md`
