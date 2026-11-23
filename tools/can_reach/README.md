# can_reach verification tools

These scripts back the claims made in the **1.5.2.5** release notes about
the AI reachability optimisation (`Square.can_reach`).

They build a headless cw1 world directly and do not depend on the ad-hoc
`bench_headless.py` scratch script.

| Script | What it does |
|---|---|
| `diff_test.py` | Differential test: compares `Square.can_reach` against the old `shortest_path_to(places=True)` on every call the AI actually makes during a live match. |
| `exhaustive_test.py` | Exhaustive differential test: walks a grid of *square pairs* on the live world (for several players) and compares the two answers. |
| `deterministic_ab.py` | Per-query A/B: replays **both** implementations over the *same* frozen world and the *same* query list, at several checkpoints of one match. |
| `memo_probe.py` | Counts the 1500 ms reachability memo's hit rate in a live match. |
| `perception_probe.py` | Times the `perception` / `memory` set walks and the cost of the old `union()` allocation. |
| `ab_probe.py` | Total-CPU A/B over two separate runs. Kept for reference, but see the caveat below. |
| `cost_probe.py` | Per-call cost of each implementation in two separate runs. Same caveat as `ab_probe.py`. |
| `common.py` | Shared world-building helpers. |

## Usage

```sh
cd tools/can_reach

# 10-minute live differential test (release notes quote 230,162 calls, 0 mismatches)
python diff_test.py 10

# exhaustive square-pair test (release notes quote 142,191 pairs, 0 mismatches)
python exhaustive_test.py

# deterministic per-query A/B (release notes quote 1.6%..7.4% less per query)
python deterministic_ab.py 20

# memo hit rate
python memo_probe.py 20

# perception / memory set-walk cost
python perception_probe.py 20
```

`diff_test.py` and `exhaustive_test.py` exit with code 0 when the two
implementations agree everywhere, and 1 on any mismatch.

## Why the A/B needs a deterministic probe

The engine is inherently nondeterministic: some code iterates over
`id()`-keyed dictionaries, so ASLR changes the iteration order and two
identical runs diverge at tick 42.  Two separate runs therefore play
different games — they issue different numbers of reachability queries
against different worlds — so their *total* pathfinding CPU is not
comparable.

Measured that way (`ab_probe.py`), the same code pair has produced
**-19.2%**, **-4.5%** and **+9.7%** on repeated runs.  Those numbers
are not reproducible and are not quoted in the release notes.

`deterministic_ab.py` sidesteps this by freezing one world, freezing a
query list, and replaying **both** implementations over the same frozen
inputs.  Same world, same squares, same player, same questions — so the
numbers measure the algorithms, not two different games.  That is the
measurement the release notes quote.

The legacy path is selected with the `SOUNDRTS_LEGACY_CAN_REACH=1`
environment variable; the probes set and clear it for each arm and
reimport the engine.
