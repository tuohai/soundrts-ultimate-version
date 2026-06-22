# Give items to NPCs (`give` + `npc_has_item`)

Let players **hand carried items to another unit** (neutral NPC, ally, enemy) and test delivery with **`npc_has_item`**.

---

## 1. Overview

| Part | Name | Role |
| --- | --- | --- |
| Order | `give` | transfer item from carrier to target |
| Field | `receive_items` | master switch (default **0**) |
| Field | `accepted_items` | item whitelist; empty = any |
| Field | `accept_from` | giver relation: `self`/`ally`/`neutral`/`enemy`; empty = any |
| Field | `accept_givers` | giver unit types; empty = any |
| Condition | `npc_has_item` | target received / holds item |

On success: item moves to target inventory; `received_items` records type; audio/UI feedback.

> Targets need **`receive_items 1`** in `rules.txt` or delivery is rejected.

---

## 2. Player usage

Carrier needs `inventory_capacity > 0` and the item (via `pickup`).

1. **Right-click** non-enemy unit while carrying → default **give** (first acceptable item).
2. **Command menu**: “Give”.
3. **Hotkey**: `g` (`style.txt`).

Right-click give only when carrying + target is non-enemy non-building.

---

## 3. Script: `give` in triggers

```
give <target_unit_id>
give <target_unit_id> <item>    ; type_name or item id
```

---

## 4. `npc_has_item`

```
(npc_has_item <NPC_selector> <item_type> [square])
(npc_has_item <index> <unit_type> <item_type>)
(npc_has_item <square> <index> <unit_type> <item_type>)
```

- **Classic**: selector = `type_name` or unit id; optional square = NPC **currently** at that square.
- **Global index**: `(npc_has_item 3 quest_npc short_sword)` — 3rd spawned `<unit_type>` for that owner (any square).
- **Square index**: Nth at `<square>` (stable after move). See [map-unit-index-selectors.md](map-unit-index-selectors.md). Chapter 28 uses global form.

True if `received_items` contains the type or inventory still holds it.

Compare with [find-item-objective.md](find-item-objective.md). For arrive-and-vanish without NPC, use [brought-item-delivery.md](brought-item-delivery.md).

---

## 5. Receive rules

All must pass:

| Field | Values | |
| --- | --- | --- |
| `receive_items` | `1` / `0` | default 0 |
| `accepted_items` | type list | empty = any; `is_a` works |
| `accept_from` | relations | empty = any |
| `accept_givers` | unit types | empty = any |

**Relations** (receiver vs giver): `self` > `ally` > `neutral` > `enemy`.

With `accept_from enemy`, right-click that enemy with the right item becomes **give** instead of attack (for that item + unit type only).

### Examples

**Ally knight accepts lance only:**

```
def knight
receive_items 1
accepted_items knight_lance
accept_from ally
```

**Enemy leader accepts letter from peasant only:**

```
def npc_knight_leader
receive_items 1
accepted_items secret_letter
accept_from enemy
accept_givers peasant
ai_mode guard
```

Campaign ch. 24–27: [campaign-secret-letter-alliance.md](campaign-secret-letter-alliance.md).

---

## 6. Demo map

`res/multi/give_demo.txt`:

```
health_potion a1
computer_only 0 0 neutral c3 quest_npc
trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
```

Campaign examples (`The Legend of Raynor`): ch. 14 deliver `pickaxe` to allied `npc_peasant`; ch. 15
deliver `knight_lance` to neutral `npc_knight`; ch. 16 deliver `wand` to enemy `npc_mage`.
See `res/single/The Legend of Raynor/14.txt`, `15.txt`, `16.txt`. Multiplayer: `res/multi/give_demo.txt`.

---

## 7. Implementation files

| Role | Path |
| --- | --- |
| `GiveOrder` | `soundrts/worldorders/skills.py` |
| Transfer | `soundrts/worldunit/world_order.py` |
| `accepts_item` | `soundrts/worldunit/worldcreature.py` |
| Trigger | `soundrts/worldplayerbase/triggers.py` |
| Tests | `soundrts/tests/test_give_item_to_npc.py` |

---

## 8. Edge cases

- Triple check: `receive_items`, `accepted_items`, `accept_from` (+ `accept_givers` if set).
- Target must be a unit with `player`.
- Item must be in giver inventory.
- Delivery **ignores target `inventory_capacity`** (story transfer); overflow drops on ground.
- `equip` runs on receiver like `pickup` (buffs/skills apply).

---

## 9. Tests

```
python -m pytest soundrts/tests/test_give_item_to_npc.py -q
```

Also: `test_campaign_alliance_transfer_triggers.py` for alliance / transfer triggers.

---

## 10. Campaign ch. 24–27

| Ch. | Item | Receiver |
| --- | --- | --- |
| 24 | `secret_letter` | `npc_knight_leader` (Garrek) |
| 25 | `garrek_token` | `npc_count_roland` (Roland) |
| 26 | `war_banner` | `npc_general_vera` (Vera) |
| 27 | — | duel with `npc_marco_ironhand` |

After ch. 24 traitors die, `(add_inventory_item garrek_token 1 raynor)` puts the token in Raynor's inventory for ch. 25. Run `cut_scene` on **player1** triggers after `npc_has_item` so the human hears voice. Full walkthrough: [campaign-secret-letter-alliance.md](campaign-secret-letter-alliance.md).

---

## 11. Campaign ch. 28 (indexed delivery)

```
trigger player1 (npc_has_item 3 quest_npc short_sword) (objective_complete 2)
```

Only the **3rd** `quest_npc` at B2 counts. Same chapter demos indexed `killed_target` and wrong-kill defeat: [map-unit-index-selectors.md](map-unit-index-selectors.md).
