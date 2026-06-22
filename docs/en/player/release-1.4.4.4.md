# SoundRTS 1.4.4.4 Release Notes

**Version**: 1.4.4.4  
**Type**: Features + CrazyMod content + balance & fixes  
**Audience**: Skirmish / random map vs AI, achievements & loadout; multi-faction mod players

---

## Highlights

Builds on 1.4.4.3 with **delayed loadout cards**, **post-game scoring & grading**, **per-faction achievements**, **cross-faction meta progress** (e.g. CrazyMod), and clearer pre-game flow when you have no cards yet.

---

## New features

### Delayed pre-mission cards

Loadout cards can fire **after in-game time** instead of only at start:

- Voice at game start: effects after N minutes/seconds.
- When the timer fires: “loadout card effect triggered” — units spawn near your start (no population cost) and/or tech is granted.
- **Charge is spent at game start**, same as instant cards.

**Vanilla cards**

| Card | Effect | How to unlock |
|------|--------|---------------|
| Delayed infantry reinforcement | 3 footman after 10 min | Achievement *Reinforcement contract* |
| Delayed melee weapon | `melee_weapon` tech after 8 min | *Defeat expert* reward |

Requires minimum rank (`min_rank`) to select in loadout.

### Post-game scoring

Non-campaign games announce multi-dimensional scores and **letter grades S–E**:

- Seven base dimensions sum to **800**; defeating stronger AI adds bonus points.
- **Defeat caps letter grade at D** (grade_total max 479).
- **Wins with low resource spending** use the “frugal efficiency” dimension.

See [score-and-grades.md](score-and-grades.md).

### Per-faction achievements (CrazyMod, etc.)

- Each faction has its **own medals, ranks, achievements, and armory**.
- Main menu → **Achievements** → pick faction → list or armory; **Back** returns to faction picker.
- Saves under `user/achievements/<mod_key>/<faction>.json`.
- **Campaign** excluded from achievements, medals, ranks, and post-game score.

### Cross-faction meta progress

- Main menu → **Achievements** → **Cross-faction progress**: meta list + meta armory.
- Meta tiers (e.g. *Three realms touched*, *Tenfold mastery*) unlock across multiple factions.
- Meta honors are extra titles; meta medals do not count toward branch ranks.

### Map & cumulative achievements (CrazyMod)

- Map milestones are **per faction**; cumulative AI defeats per branch; legacy save keys migrate on load.

---

## Balance & data

- **Lieutenant** rank: **200** medals, 1 loadout slot.
- **Perfect survival**: survival ≥90 **and** building defense ≥90 (victory required).
- **Defeat beginner** repeat: **8** medals per repeat.
- Building loss/demolition scoring: **5** points per building (was 10).
- CrazyMod: small balance tweaks in `rules.txt` / `ai.txt` (vermin buildings still 0 gold).

---

## Fixes & UX

- Worker `can_gather all`: attribute UI no longer announces “all” twice.
- **Pre-game**: no loadout card voice when you have no slots or no cards; random faction uses **select your faction for this game** (not loadout captions).
- Hunting / timer NPC defeats: broadcast only when `broadcasts_defeat_and_quit` is true.
- Test suite: restores `res.mods` after mod-switching tests.

---

## For mod authors

- `cards.txt`: `delay`, `delay_minutes`, `tech` — [delayed-card-loadout.md](delayed-card-loadout.md).
- `achievements_per_faction 1`, `faction`, `scope meta`, `factions_*` — [achievement-system.md](achievement-system.md).
- `ai.txt`: `defeat_score` still controls post-game defeat bonus.

---

## Upgrade notes

- Overwrite install; `user/achievements/` saves preserved; legacy defeat counters migrate automatically.
- Campaign, co-op campaign, multiplayer: still **no** achievements, loadout, or score announcements.
- `achievements_enabled 0` keeps the whole system off.

---

## Docs

| Doc | Topic |
|-----|--------|
| [achievements.md](achievements.md) | Achievements (players) |
| [score-and-grades.md](score-and-grades.md) | Scoring (players) |
| [loadout-cards.md](loadout-cards.md) | Loadout (players) |
| [../developer/achievement-system.md](../developer/achievement-system.md) | Achievement system (dev) |
| [../developer/delayed-card-loadout.md](../developer/delayed-card-loadout.md) | Delayed cards (dev) |
| [../developer/score-grading-system.md](../developer/score-grading-system.md) | Scoring implementation (dev) |
| `doc_src/src/en/relnotes.rst` | Full version history |

---

## Quick test

```bash
python -m pytest soundrts/tests/test_card_loadout.py soundrts/tests/test_score_breakdown.py soundrts/tests/test_meta_progress.py soundrts/tests/test_faction_progress.py -q
```
