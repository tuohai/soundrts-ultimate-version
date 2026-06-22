# Pre-mission card loadout (players)

When and how to **carry cards** before start — and when you **won’t** hear card prompts.

File format: [../developer/delayed-card-loadout.md](../developer/delayed-card-loadout.md).

---

## Requirements

All of:

1. **Single player → Start on map → invite computer → Start** (custom or random map)  
2. Mod has achievements enabled (`achievements_enabled` not 0)  
3. Your **rank** grants **loadout slots** (e.g. Lieutenant = 1, Captain = 2, …)  
4. **Armory** has cards with charges left and you meet each card’s **min rank**  

**No loadout** in campaign or multiplayer.

---

## Flow

1. Set up map and AI, press **Start**.  
2. **Random faction** (multi-faction mods): voice **select your faction for this game**.  
3. **No slots or no usable cards**: match starts **immediately** — no “select loadout card” voice.  
4. Otherwise: pick a card per slot, **skip slot**, or **start now**.  
5. Effects apply in-game (instant or delayed); **one charge** per card used.  

---

## Typical effects

- **Resource cards** — bonus at start  
- **Reinforcement cards** — units near your start (**no population cost**)  
- **Delayed cards** — charge spent at start; units or tech arrive after in-game time  

The armory speaks each card’s effect when you browse it.

---

## Common confusion

| Situation | What happens |
|-----------|----------------|
| New player, no cards yet | **Straight into the match** — no card menu |
| Random faction | May only hear **faction** selection, not cards |
| Rank too low | Cards stay in armory but can’t be selected |

---

## See also

- [achievements.md](achievements.md)  
- [release-1.4.4.4.md](release-1.4.4.4.md)
