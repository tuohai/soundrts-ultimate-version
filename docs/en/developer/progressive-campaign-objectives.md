# Progressive campaign objectives (`register_objective`)

For single-player maps that reveal goals one at a time (complete goal 1, then hear goal 2).

Official trigger reference: `doc_src/src/en/mapmaking.rst` (Register_objective).

---

## 1. Problem

Each `add_objective` does two things:

1. Shows the goal in **F9** and plays the "new objective" voice.
2. Adds that number to the **victory requirement set**.

If a map only calls `add_objective 1` at start and `add_objective 2` after goal 1 completes, completing goal 1 used to win the mission immediately — because no goal 2 existed yet in the requirement set, or the old logic treated "all visible objectives done" as victory.

---

## 2. Solution: `register_objective`

**Register** all primary numbers up front **without** displaying them:

```txt
trigger player1 (timer 0) (do (register_objective 1 2 3) (add_objective 1 7001))
trigger player1 (has barracks) (do (objective_complete 1) (add_objective 2 7002))
trigger player1 (has 10 footman) (objective_complete 2)
trigger player1 (has townhall) (objective_complete 3)
```

| Action | F9 / voice | Victory set |
| --- | --- | --- |
| `register_objective 1 2 3` | No | Adds 1, 2, 3 to `_required_objective_numbers` |
| `add_objective 1 …` | Yes | Also adds 1 (if not already registered) |
| `objective_complete 1` | Removes goal 1 from F9 | Adds 1 to `_completed_objective_numbers` |

Victory runs when `_required_objective_numbers` ⊆ `_completed_objective_numbers` (`soundrts/worldplayerbase/base.py` — `_all_required_objectives_done`).

---

## 3. F9 and voice numbering

When **more than one** primary objective is registered or visible:

- F9 shows **"Primary objective N:"** then the description (colon after the number).
- With **only one** primary objective, the number is omitted.

The engine scans map triggers at load time (`collect_planned_objective_numbers` in `soundrts/objective_announce.py`) so numbers are correct even when `add_objective` calls live in separate `timer 0` triggers.

Optional objectives (`add_secondary_objective`) use independent numbering with the same rules.

---

## 4. Examples in this repo

| Map | Pattern |
| --- | --- |
| `mods/starcraft/single/sc_build_tests/1.txt` | 2 chained Protoss goals |
| `mods/starcraft/single/sc_late_game/1.txt` | 6 chained late-game goals |

---

## 5. Tests

```bash
python -m pytest soundrts/tests/test_campaign_alliance_transfer_triggers.py -k register_objective -q
python -m pytest soundrts/tests/test_objective_announce.py -q
python -m pytest soundrts/tests/test_cmd_objectives.py -q
```
