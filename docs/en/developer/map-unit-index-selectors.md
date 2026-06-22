# Map unit index selectors (`killed_target` / `npc_has_item` / `unit_lost` / `building_lost` / `key_unit_killed`)

When several **same-type** units share a square, use **`<square> <index> <type>`** to mean
“the Nth unit of that type at that square” — not “any one of them” or “kill N total”.

Same syntax as **`transfer_units`**, **`order`**, and **`add_units`**. Indices are assigned at
map load / trigger spawn per `(square, type)` and **stay stable after the unit moves**.

---

## 1. Triggers

| Condition | Index syntax | Use case |
| --- | --- | --- |
| `killed_target` | `(killed_target <index> <type> [enemy\|ally])` or square form | Must kill that specific unit |
| `npc_has_item` | `(npc_has_item <index> <type> <item>)` or square form | Must give the item to that specific NPC |
| `unit_lost` | `(unit_lost <index> <type>)` or `(unit_lost <square> <index> <type>)` | That spawned-index friendly unit is gone |
| `building_lost` | `(building_lost <index> <type>)` or `(building_lost <square> <index> <type>)` | That spawned-index building is destroyed |
| `key_unit_killed` | `(key_unit_killed <index> <type>)` or `(key_unit_killed <square> <index> <type>)` | That spawned-index friendly unit was killed |

Legacy forms still work:

- `(killed_target <unit_id>)` — global unit id
- `(killed_target <type> [enemy\|ally])` — any kill of that type
- `(npc_has_item <NPC_selector> <item> [square])` — type/id + optional current square

---

## 2. Kill a specific unit (`killed_target`)

### Complete objective only for the Nth unit

```txt
computer_only 0 0 c3 3 demo_marker_footman

trigger player1 (killed_target 3 demo_marker_footman enemy) (objective_complete 1)
```

Only killing the **3rd spawned** `demo_marker_footman` satisfies the condition (square-agnostic).
Square form: `(killed_target c3 3 demo_marker_footman enemy)`.

### Fail on wrong kill

```txt
trigger player1 (killed_target 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
trigger player1 (killed_target 2 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
trigger player1 (killed_target 3 demo_marker_footman enemy) (do (cut_scene 7603) (objective_complete 1))
```

Killing #1 or #2 → cut scene + `defeat`. Killing #3 → complete objective 1.

### vs `has_killed`

| Condition | Meaning |
| --- | --- |
| `(has_killed 3 footman enemy)` | **Three** enemy footmen killed in total |
| `(killed_target c3 3 footman enemy)` | The **3rd** footman **at C3** was killed |

---

## 3. Give to a specific NPC (`npc_has_item`)

```txt
computer_only 0 0 neutral b2 3 quest_npc
short_sword a1

trigger player1 (npc_has_item 3 quest_npc short_sword) (objective_complete 2)
```

Only the **3rd spawned** `quest_npc` counts (any square). Square form: `(npc_has_item b2 3 quest_npc short_sword)`.
See [give-to-npc.md](give-to-npc.md) for `give` / `receive_items`.

---

## 4. Protect a specific friendly unit or building (defeat)

### Only footman #3 may die

```txt
player ... a1 3 footman raynor

trigger player1 (unit_lost a1 3 footman) (defeat)
trigger player1 (key_unit_killed a1 3 footman) (defeat)
```

### Only the first town hall (global spawn index)

```txt
player ... b1 townhall raynor ...   ; chapter 2 base at B1 works too

trigger player1 (building_lost 1 townhall) (defeat)
```

**Global index** counts spawn order per player per type, regardless of square:
- 1st town hall spawned = town hall 1 (whether at A1 or B1)
- 2nd spawned = town hall 2; destroying #2 does **not** fail this trigger

For square-specific Nth unit, use `(building_lost a1 1 townhall)`.

### vs legacy forms

| Condition | Meaning |
| --- | --- |
| `(unit_lost footman)` | **All** player footmen are gone |
| `(unit_lost a1 3 footman)` | Only the **3rd** footman **at A1** is gone |
| `(building_lost townhall)` | **All** player town halls are destroyed |
| `(building_lost a1 1 townhall)` | Only the **1st** town hall **at A1** is destroyed |

---

## 5. Multiple objectives and cut scenes

Primary objectives may be finished **in any order**. Each `cut_scene` on `objective_complete`
should describe **that objective only** — do not say “all objectives complete” in one branch;
victory runs automatically when every primary objective is done.

Good:

```txt
trigger player1 (killed_target c3 3 demo_marker_footman enemy)
    (do (cut_scene 7603) (objective_complete 1))

trigger player1 (npc_has_item b2 3 quest_npc short_sword)
    (do (cut_scene 7604) (objective_complete 2))
```

Bad: cut scene 7604 text claiming both objectives are done when the player may still need to kill footman #3.

---

## 6. Demo: The Legend of Raynor chapter 28

File: `res/single/The Legend of Raynor/28.txt`

| Area | Content |
| --- | --- |
| A1 | footman + peasant, `short_sword` on ground |
| C3 | 3 enemy `demo_marker_footman` |
| B2 | 3 neutral `quest_npc` |

Objective 1: kill the 3rd footman at C3 (wrong kill → defeat).  
Objective 2: give `short_sword` to the 3rd NPC at B2.

---

## 7. Code & tests

| Role | Path |
| --- | --- |
| Assign index on spawn | `triggers.py` — `_assign_map_select_slot` |
| Kill tracking | `record_unit_killed` → `_killed_map_slots` / `_units_killed_by` |
| Conditions | `lang_killed_target`, `lang_npc_has_item`, `lang_unit_lost`, `lang_building_lost`, `lang_key_unit_killed` |
| Map test | `test_give_item_to_npc.py::test_chapter_28_map_select_index_triggers` |
| Loss tests | `test_map_select_loss_triggers.py` |

```
python -m pytest soundrts/tests/test_give_item_to_npc.py::test_chapter_28_map_select_index_triggers -q
python -m pytest soundrts/tests/test_map_select_loss_triggers.py -q
```
