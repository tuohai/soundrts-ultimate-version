# 开发者 / 模组作者指南（中文）

面向 **写模组、地图、战役脚本** 的读者：`achievements.txt` 语法、`rules.txt` 字段、触发器关键字、源码入口等。

纯玩家请阅 [../player/README.md](../player/README.md)。

---

## 成就、评分与卡牌

| 文档 | 说明 |
|------|------|
| [achievement-system.md](achievement-system.md) | 成就系统实现、`achievements.txt` / `titles.txt` / `cards.txt` |
| [score-grading-system.md](score-grading-system.md) | 结算评分维度与 `score_breakdown()` |
| [delayed-card-loadout.md](delayed-card-loadout.md) | 延迟卡牌 `delay` / `tech` 字段 |

玩家向简述见 [../player/achievements.md](../player/achievements.md)、[../player/score-and-grades.md](../player/score-and-grades.md)、[../player/loadout-cards.md](../player/loadout-cards.md)。

---

## 客户端 UI 与热键

| 文档 | 说明 |
|------|------|
| [hotkey-mapping-editor.md](hotkey-mapping-editor.md) | 选项菜单「按键映射」编辑器（Phase 1–5 已完成：分层/经典、搜索、变体、别名、导入导出） |

玩家向分层热键说明见 [../player/分层热键方案说明.md](../player/分层热键方案说明.md)。

---

## 战役与地图脚本

| 文档 | 说明 |
|------|------|
| [寻找物品通关说明.md](寻找物品通关说明.md) | `has_item`、`has_brought_item` 等 |
| [给NPC物品功能说明.md](给NPC物品功能说明.md) | `give`、`npc_has_item` |
| [指定序号目标说明.md](指定序号目标说明.md) | `killed_target`、地图单位序号 |
| [渐进式战役目标说明.md](渐进式战役目标说明.md) | `register_objective` |
| [coop-campaign.md](coop-campaign.md) | 合作战役（``campaign.txt`` + ``N.txt``） |
| [战役跨章英雄携带说明.md](战役跨章英雄携带说明.md) | ``campaign_carryover``、stats/inventory 拆分 |
| [mod-i18n.md](mod-i18n.md) | 模组多语言 `ui-xx`、`mod.txt` |

玩家向 HoMM / Civ5 式 RMG 说明见 [../player/英雄无敌与文明5玩法说明.md](../player/英雄无敌与文明5玩法说明.md)。

---

## 官方手册

| 路径 | 内容 |
|------|------|
| `doc_src/src/zh/modding.rst` | 单位、规则、战斗关键字 |
| `doc_src/src/zh/mapmaking.rst` | 地图与触发器 |
| `doc_src/src/zh/relnotes.rst` | 完整版本历史 |
| `doc_src/src/zh/aimaking.rst` | 电脑 AI 脚本 |

---

## English

[../../en/developer/README.md](../../en/developer/README.md)
