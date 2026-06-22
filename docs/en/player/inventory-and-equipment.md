# Inventory & equipment UI

How units use **inventory (backpack)**, the **equipment screen**, and the **same-type item model** in `rules.txt` (one type can be both a pickable item and equippable weapon/armor).

---

## 1. Overview

| Screen | Hotkey | Shows |
| --- | --- | --- |
| Attributes | `Alt+V` | all stats |
| **Backpack** | `Shift+V` | **all** inventory items |
| **Equipment** | `Ctrl+V` | **weapons & armor** (inventory gear + built-in) |

Only one screen at a time. Select **exactly one** friendly unit.

### Backpack vs equipment

- **Backpack**: equip/use/drop any item.
- **Equipment**: weapons and armor only. Built-in gear labeled “built-in weapon / built-in armor” (read-only).

### Mixed built-in + item gear

When a unit has **both** `class weapon`/`class armor` and `class item` gear (e.g. `weapons bow sword`):

| Rule | Meaning |
| --- | --- |
| Spawn priority | **Built-in always equipped first**; item gear goes to backpack |
| `spawn_weapons_equipped 1` (default) | Item weapons stay in backpack and **cannot** be equipped manually |
| `spawn_weapons_equipped 0` | Item weapons in backpack **can** be equipped |
| Switching | Built-in ↔ built-in only; item ↔ item only; **no cross-switch** |
| Armor | Same with `spawn_armor_equipped` |

If the unit has **only** item gear, spawn flags control silent equip at creation (default on).

---

## 2. Player controls

### Open

- Exactly **1** friendly unit selected.
- Backpack: non-empty inventory.
- Equipment: at least one weapon or armor (built-in or inventory).

### In backpack / equipment

| Key | Action |
| --- | --- |
| Arrows | previous / next item |
| `g` | read item intro (from `style.txt`) |
| `Enter` | equip weapon / wear armor / use consumable |
| `Shift+Enter` | unequip weapon or armor |
| `Delete` | drop (confirm, then Enter) |
| `Shift+Delete` | drop without confirm |
| `Esc` | close / cancel drop |

### World

- **Pickup**: `pickup` (default right-click).
- **Drop**: `drop` or Delete in UI.
- **Give**: `give` — see [give-to-npc.md](give-to-npc.md).

---

## 3. Two equipment systems

### 3.1 Built-in weapon / armor (classic)

```
def footman
weapons sword          ; class weapon
armor footman_armor    ; class armor
```

Not in backpack. Equipment screen shows as built-in; cannot unequip or drop via UI.

### 3.2 Backpack item equipment (same-type model)

```
def sword
class item
equippable_as_weapon 1
mdg 3.5
...
```

Stats apply while equipped; removed on unequip. See `res/rules.txt` for `sword`, `footman_armor` examples.

---

## 4. Spawn gear into backpack

On spawn:

- `weapons <name>`: if type is `class item` + `equippable_as_weapon 1` → instance in backpack; silent equip if no built-in weapon and `spawn_weapons_equipped 1`.
- `armor <name>`: same for armor.

Example footman with item sword + item armor: both in backpack, both equipped by default, visible in Shift+V and Ctrl+V.

```
spawn_weapons_equipped 0/1   ; default 1
spawn_armor_equipped 0/1     ; default 1
```

### Mixed archer

```
def archer
weapons bow sword
```

- `bow` = `class weapon` → built-in, always equipped.
- `sword` = `class item` → backpack; with default spawn flag, sword cannot be equipped while bow is built-in.

Set `spawn_weapons_equipped 0` to allow manual sword equip (still no bow↔sword direct switch).

### Requirements

| Field | Note |
| --- | --- |
| `inventory_capacity` | must be > 0 |
| `transport_volume` | space per item (default 1); capacity counts **items**, not volume |

---

## 5. Author checklist

### Built-in only

```
def my_unit
weapons short_sword
armor light_armor
```

### Pickable, equippable, removable

1. Define item with `equippable_as_weapon 1` or `equippable_as_armor 1`.
2. Unit: `inventory_capacity` + `weapons my_sword`.
3. `style.txt`: `title`, `intro`.

### Consumables

```
def health_potion
class item
buffs heal
```

Use with Enter in backpack (`use_item`), not in equipment screen.

---

## 6. Server orders

| Order | Args | |
| --- | --- | --- |
| `equip_weapon` | item id | |
| `unequip_weapon` | item id | |
| `equip_armor` | item id | |
| `unequip_armor` | item id | |
| `use_item` | item id | |
| `drop` | item id | |

Inventory transfers on upgrade/morph via `transfer_inventory_to`.

---

## 7. FAQ

**Q: Backpack empty on footman?**  
Built-in `class weapon` does not enter backpack until the type is `class item` with spawn-to-inventory logic.

**Q: “Built-in armor” and can’t unequip?**  
Still `class armor`; add `class item` + `equippable_as_armor 1`.

**Q: Same name for item and weapon?**  
Yes (same-type model): e.g. `sword` as item for backpack/spawn; `bow` stays pure `class weapon`.

---

## 8. Related files

| File | |
| --- | --- |
| `res/ui/bindings.txt` | Shift+V, Ctrl+V |
| `soundrts/attributes/inventory_screen.py` | backpack UI |
| `soundrts/attributes/equipment_screen.py` | equipment UI |
| `soundrts/worldunit/worldbase.py` | spawn / equip logic |
| `res/rules.txt` | examples |

See also [give-to-npc.md](give-to-npc.md), [find-item-objective.md](find-item-objective.md).
