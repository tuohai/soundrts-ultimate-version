# Achievements, ranks & armory (players)

How to use the main-menu **Achievements** hub — no `achievements.txt` syntax.

Mod authors: [../developer/achievement-system.md](../developer/achievement-system.md).

---

## Where to find it

Main menu → **Achievements**:

1. **Achievement list** — locked / unlocked; locked entries speak requirement summaries  
2. **Armory** — current rank, honor titles, medal total, card charges  

Multi-faction mods (e.g. CrazyMod) ask you to **pick a faction** first; **Back** from a sub-menu returns to faction selection.

**Cross-faction progress** (multi-faction mods only): meta achievements, branch summary, meta honors.

---

## What counts?

| Game type | Achievements / medals / ranks | Score voice |
|-----------|------------------------------|-------------|
| Custom or random map **vs computer** | ✅ | ✅ |
| **Campaign**, co-op campaign | ❌ | ❌ |
| Multiplayer | ❌ | ✅ |

---

## After a match (non-campaign)

**Vs computer** (skirmish), voice usually announces:

1. **Score breakdown & letter grade** (S–E) — [score-and-grades.md](score-and-grades.md)  
2. **New achievements**, medals, card charges, honor titles  
3. **Rank promotion**, extra loadout slots if applicable  

**Multiplayer** announces item 1 only — no achievements, medals, ranks, or card progress.

**Repeat completions** may grant medals only (no card/honor/unlock voice again).

---

## Per-faction progress (CrazyMod, etc.)

- Each faction has **its own** medals, ranks, and achievement list.  
- Saves live under `user/achievements/<mod>/<faction>.json` (normally automatic).  
- **Random faction**: **Start** may ask you to **select your faction for this game**.  
- Pick a concrete faction in the skirmish setup to skip that step.

---

## Cross-faction meta

Progress across branches unlocks **meta achievements** and **meta honor** titles (e.g. three realms / tenfold mastery). View them under **Cross-faction progress**. Meta medals do **not** count toward a single faction’s rank.

---

## Pre-mission cards

See [loadout-cards.md](loadout-cards.md).

---

## See also

- [release-1.4.4.4.md](release-1.4.4.4.md)  
- [../developer/achievement-system.md](../developer/achievement-system.md)
