# Developer & mod author guides (English)

For **mod/map/campaign authors** — `achievements.txt` syntax, scoring hooks, trigger keywords, source layout.

Players: [../player/README.md](../player/README.md).

---

## Achievements, scoring & cards

| Doc | Topic |
|-----|--------|
| [achievement-system.md](achievement-system.md) | Achievement system, file formats, code paths |
| [score-grading-system.md](score-grading-system.md) | Score dimensions & `score_breakdown()` |
| [delayed-card-loadout.md](delayed-card-loadout.md) | `delay` / `tech` on cards |

Player summaries: [../player/achievements.md](../player/achievements.md), [../player/score-and-grades.md](../player/score-and-grades.md), [../player/loadout-cards.md](../player/loadout-cards.md).

---

## Client UI & hotkeys

| Doc | Topic |
|-----|--------|
| [hotkey-mapping-editor.md](hotkey-mapping-editor.md) | Options menu key mapping editor (Phases 1–5 complete: layered/classic, search, variants, aliases, import/export) |

Player guide: [../player/layered-hotkeys.md](../player/layered-hotkeys.md).

---

## Campaign & map scripting

| Doc | Topic |
|-----|--------|
| [find-item-objective.md](find-item-objective.md) | `has_item`, `has_brought_item`, … |
| [give-to-npc.md](give-to-npc.md) | `give`, `npc_has_item` |
| [map-unit-index-selectors.md](map-unit-index-selectors.md) | `killed_target`, unit index syntax |
| [progressive-campaign-objectives.md](progressive-campaign-objectives.md) | `register_objective` |
| [coop-campaign.md](coop-campaign.md) | Co-op: `campaign.txt` flags + shared `N.txt` |
| [campaign-hero-carryover.md](campaign-hero-carryover.md) | `campaign_carryover`, stats/inventory split |

Chinese-only: [../../zh/developer/mod-i18n.md](../../zh/developer/mod-i18n.md) (mod i18n).

---

## Official manuals

| Path | Content |
|------|---------|
| `doc_src/src/en/modding.rst` | Rules & unit keywords |
| `doc_src/src/en/mapmaking.rst` | Maps & triggers |
| `doc_src/src/en/relnotes.rst` | Full version history |
| `doc_src/src/en/aimaking.rst` | AI scripts |

---

## 中文

[../../zh/developer/README.md](../../zh/developer/README.md)
