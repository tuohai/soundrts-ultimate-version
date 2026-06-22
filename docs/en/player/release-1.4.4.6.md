# SoundRTS 1.4.4.6 Release Notes

**Version**: 1.4.4.6  
**Type**: mod sound naming cleanup + unified skill system + generic skill effects + skill target filters and -tag exclusions + level-up stat scaling + level skill unlocks + campaign hero carryover + backpack item use sounds + ready/prep sounds + backpack/equipment hotkey toggle + hero starting level and level-0 XP display  
**Audience**: map/mod authors; players customizing `ui/style.txt`

---

## Highlights

1.4.4.6 includes nine areas:

1. Attack sound keys renamed from `matk` / `ratk` to `mdg` / `rdg`
2. Custom sounds for skill prep and normal attack prep
3. **Unified skill system**: one skill can be both manual and auto-triggered
4. **Generic skill effects**: burst, push, AOE, summon, deploy, and other `effect` types
5. **Level-up stat scaling**: more attributes support `*_per_level` growth
6. **Level skill unlocks**: `level_skills` grants skills at set levels
7. **Campaign carryover**: hero level, XP, and backpack persist to the next chapter
8. **Backpack item use sounds**: same three-level lookup as pickup/drop
9. **Backpack/equipment hotkeys**: **Shift+V** cycles between screens; **Ctrl+V** removed
10. **Skill books**: permanent learning via backpack use (pairs with item 6)
11. **Target type filters**: skill `harm_target_type`; global `-tag` exclusions
12. **Hero starting level and status**: `level` / `level 0` / `xp`; Tab always announces level
13. **Full heal on level-up**: `level_up_heal_full 1` restores HP and mana on each level-up

---

## Attack sound key rename

Use these keys in `ui/style.txt`:

| Old key | New key |
| --- | --- |
| `launch_matk` / `launch_ratk` | `launch_mdg` / `launch_rdg` |
| `matk_hit` / `ratk_hit` | `mdg_hit` / `rdg_hit` |
| `matk_hit_vs` / `ratk_hit_vs` | `mdg_hit_vs` / `rdg_hit_vs` |
| `matk_hit_lv_1` / `ratk_hit_lv_1` | `mdg_hit_lv_1` / `rdg_hit_lv_1` |
| `matk_missed` / `ratk_missed` | `mdg_missed` / `rdg_missed` |
| `matk_dodge` / `ratk_dodge` | `mdg_dodge` / `rdg_dodge` |
| `launch_charge_matk` / `launch_charge_ratk` | `launch_charge_mdg` / `launch_charge_rdg` |
| `charge_matk_hit` / `charge_ratk_hit` | `charge_mdg_hit` / `charge_rdg_hit` |

Bundled `style.txt` files have been migrated. Old keys remain compatible as fallback.

---

## Custom ready sounds

Skills with `ready <seconds>` can define a `ready` style sound. Manual and automatic triggers play it when prep starts.

```text
def skill_heavy_slash
ready heavy_slash_ready
```

Normal attack prep also supports dedicated sounds:

```text
def footman
mdg_ready sword_prepare

def archer
rdg_ready bow_prepare
```

---

## Unified skill system

One `class skill` can be both **manually used** and **auto-triggered** — no separate twin lists required.

**Skill fields**:

| Field | Meaning |
| --- | --- |
| `auto_trigger 1` | Allow automatic triggering |
| `manual_use 1` | Allow manual use (default 1) |
| `trigger_timing` | When auto-trigger fires |

**`trigger_timing` values**:

| Value | Meaning | Legacy equivalent |
| --- | --- | --- |
| `on_hit` | After a normal attack hits | `active_trigger_skills` |
| `on_attack` | On attack start, normal attack continues | `attack_trigger_skills` |
| `on_attack_replace` | Replaces this normal attack | `attack_replace_skills` |
| `on_damaged` | When taking damage | `passive_trigger_skills` |

Learned skills live in `can_use_skill`; the command menu shows only `manual_use 1` skills. Legacy unit lists still work.

Example (manual + on-hit auto trigger):

```text
def skill_zhuiri_jianfa
class skill
auto_trigger 1
manual_use 1
trigger_timing on_hit
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)
mdg 6
effect_target ask
cooldown 8
mana_cost 20
```

---

## Generic skill effects

`define class skill` behavior via the `effect` field. Full guide: `GENERIC_SKILL_SYSTEM.md`.

### Damage

| Syntax | Meaning |
| --- | --- |
| `effect harm_target 60` | Single-target fixed 60 true damage (bypasses armor) |
| `effect harm_area 50 3` | Fixed 50 damage in radius 3 around target point |
| `effect harm_target mdg` + `mdg 12` | Single-target melee via full combat pipeline |
| `effect harm_area mdg 3` + `mdg 12` | Area melee damage; supports splash params |

Combat damage applies defense, `*_vs`, crit, piercing, splash, debuffs, XP, etc. Non-zero skill stats override the caster.

### Burst combos

```text
effect burst mdg 5 (interval 0.2) (window 1)   ; evenly spaced 5-hit combo
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)   ; custom rhythm
mdg 6
```

The number after `burst` is **hit count**, not damage; put damage in `mdg` / `rdg`.

### Control and other effects

| `effect` | Example | Meaning |
| --- | --- | --- |
| `push` | `effect push 5` | Knock enemy back |
| `buffs` | `effect buffs b_power` | Apply buff to target or self |
| `debuffs` | `effect debuffs b_poison` | Apply debuff to enemy |
| `deploy` | `effect deploy 10 fire_zone` | Place `class effect` zone on square |
| `summon` | `effect summon 30 2 footman` | Summon 2 footmen for 30 seconds |

Legacy effects still work: `teleportation`, `recall`, `conversion`, `raise_dead`, `resurrection`.

Buffs support `reflect_percent` to reflect a portion of damage taken (no reflect chains).

### Range and triggers

- `effect_range`: cast distance
- `effect harm_area mdg 3` — `3` is primary hit radius
- `mdg_range` / `rdg_range`: combat reach cap
- `mdg_splash` + `mdg_radius`: secondary splash after primary hit

Auto-triggers support `active_trigger_rate`, `passive_trigger_rate`, `mdg_trigger_rate` / `rdg_trigger_rate`, and conditions like `trigger_condition hp < 30`. Legacy unit lists (`attack_trigger_buffs`, `attack_replace_debuffs`, etc.) remain compatible.

### Target type filters and `-tag` exclusions

`class skill` can set `harm_target_type` for `burst`, `harm_target`, `harm_area`, and `push`. When omitted, skills default to **enemies only**.

Prefix `-` on a tag to exclude it, e.g. `-building` = everything except buildings. Also applies to:

| Field | Inclusion logic |
| --- | --- |
| `harm_target_type` | AND |
| `heal_target_type` | OR |
| `mdg_targets` / `rdg_targets` | OR |
| buff/debuff `target_type` | AND |

Diplomacy exclusions work too: `harm_target_type -enemy`, etc.

```text
def skill_heng_sao
class skill
effect harm_area 50 3
harm_target_type enemy ground unit -building

def priest
heal_target_type unit -undead

def archer
mdg_targets ground air -building

def b_holy
class buff
target_type unit -undead
```

---

## Level-up stat scaling (`*_per_level`)

In `rules.txt`, set `<stat>_per_level` on a unit to grow that stat each level. Beyond HP, mana, and revival time, most combat stats are supported: melee/ranged damage and armor, range, cooldowns, splash, charge attacks, crit rates, heal/harm auras, regen timing, and more.

```text
def raynor
is_a footman
xp_thresholds 100 250 500 900
hp_max_per_level 30
mdg_per_level 2
mdf_per_level 1
charge_mdg_per_level 2
mdg_crit_rate_per_level 1
mana_max_per_level 10
```

- Applied automatically on level up; default ``level_up_heal_full 0`` adds only the ``hp_max_per_level`` / ``mana_max_per_level`` increment to current HP/mana; ``level_up_heal_full 1`` restores **full** HP and mana on each level up.
- Campaign hero restore reapplies cumulative bonuses up to the saved level.

### Starting level and status display

Optional starting level/XP on the hero def (requires `xp_thresholds`):

```text
def raynor
xp_thresholds 40 90 160 250 360 490 640 810 1000
hp_max_per_level 30
level 0          ; start at level 0 (default is 1 if omitted)
xp 0             ; optional starting cumulative XP
level 3          ; or: spawn at level 3 (applies cumulative *_per_level)
```

| Field | Meaning |
| --- | --- |
| `level` | Starting level (default `1`); values `> 1` apply cumulative growth on spawn |
| `xp` | Optional starting cumulative XP |
| `level 0` | Start below level 1; Tab status shows level 0 and XP toward `xp_thresholds[0]` |

Heroes with `xp_thresholds` **always announce level** in Tab status (including 0 and 1); XP is shown as current / next gate.

---

## Level unlocks and skill books

**Auto unlock on level up** (unit `rules.txt`):

```text
level_skills 10 skill_zhuiri_jianfa
learn_level_skills 10 skill_zhuiri_jianfa   ; extra gate for book learning
```

**Skill book** (backpack Enter, permanent learn):

```text
def zhuiri_jianfa_book
class item
skills skill_zhuiri_jianfa
learn_level 10
```

- With `learn_level`, pickup does not grant the skill; use from backpack.
- Successful use removes the book; learned skills are not stripped on unequip.
- Already known or level too low: `order_impossible` message; book kept.
- Do **not** put the same skill on both `level_skills` and a book, or use returns `skill_already_known` without consuming the book.
- Reaching a `level_skills` threshold announces the newly learned skill.

---

## Campaign hero carryover

Enable cross-chapter save on a hero def in `rules.txt`. On **victory**, level, XP, and backpack carry to the next chapter (single-player campaigns only):

```text
def raynor
campaign_carryover 1
campaign_carryover_id raynor
campaign_carryover_stats 1
campaign_carryover_inventory 1
inventory_capacity 8
```

| Field | Meaning |
| --- | --- |
| `campaign_carryover` | `1` = enable cross-chapter save |
| `campaign_carryover_stats` | `1` = save/restore level + XP (default on) |
| `campaign_carryover_inventory` | `1` = save/restore backpack (default on) |

- Progress is written to `user/campaigns.ini` on **victory only**; defeat retries do not overwrite.
- Optional `hero_min_level 13:2 16:3 …` in `campaign.txt` sets a per-chapter level floor.
- Stats only: `campaign_carryover_inventory 0`. Inventory only: `campaign_carryover_stats 0`.
- **Co-op** does not persist heroes; story tokens still use `campaign_flag` / `add_inventory_item`.

---

## Backpack item use sounds

Same three-level lookup as pickup/drop:

| When | Item `style.txt` | Unit `style.txt` | Global default |
| --- | --- | --- | --- |
| Use | `use` / `on_use` | `use_<item type>` | `item_used` |

```text
def zhuiri_jianfa_book
use 1506

def raynor
use_zhuiri_jianfa_book 1506

def thing
item_used 1194 1195 1196
```

- Sounds play only after server-confirmed success; no optimistic "used" voice on Enter.
- Skill books: use sound + skill title + "learned"; other consumables: item title + "used".

---

## Backpack and equipment hotkeys

Classic and layered schemes now match:

| Key | Action |
| --- | --- |
| `Shift+V` | Cycle between backpack and equipment |
| `F3` | Same as Shift+V in layered scheme (still available) |
| ~~`Ctrl+V`~~ | Removed |

- First press opens the backpack when inventory is non-empty; further presses toggle while a sub-screen is open.
- Requires exactly one friendly unit selected; mutually exclusive with the `Alt+V` attributes screen.
- Custom overrides: hotkey editor entry **Toggle backpack and equipment**.

---

## Upgrade notes

- New content should use `mdg` / `rdg` style keys instead of `matk` / `ratk`.
- Prefer `auto_trigger` / `manual_use` / `trigger_timing` for new skills; legacy lists still work.
- Learn skills from books via backpack `use_item`; avoid duplicating the same skill on `level_skills` and a book.

---

## Documentation

| Doc | Topic |
| --- | --- |
| `doc_src/src/en/modding.rst` | item sounds, skill books, unified skills, campaign carryover |
| [campaign-hero-carryover.md](../developer/campaign-hero-carryover.md) | full `campaign_carryover` guide |
| [inventory-and-equipment.md](inventory-and-equipment.md) | UI controls and Shift+V toggle |
| `GENERIC_SKILL_SYSTEM.md` | full skill guide (burst, push, AOE, triggers) |
| [burst-attack-damage-seq.md](burst-attack-damage-seq.md) | `damage_seq` launch sounds |

---

## Quick test

```bash
python -m pytest soundrts/tests/test_level_skills.py soundrts/tests/test_level_up_combat_stats.py soundrts/tests/test_campaign_hero.py soundrts/tests/test_wuxia_skills.py soundrts/tests/test_worldskill_deploy.py soundrts/tests/test_hit_vs_buff_sounds.py soundrts/tests/test_damage_seq_burst.py soundrts/tests/test_changelog_138x.py soundrts/tests/test_skill_trigger_sounds.py soundrts/tests/test_inventory_backpack.py -q
```
