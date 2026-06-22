# 成就系统（Achievement System）

> **玩家向说明**（菜单、进度、战役是否计入）：[../player/achievements.md](../player/achievements.md)

本文档描述 SoundRTS **成就系统**的实现与后续路线，便于在新会话中继续开发。

英文版：[../../en/developer/achievement-system.md](../../en/developer/achievement-system.md)

---

## 1. 目标

| 阶段 | 状态 | 说明 |
|------|------|------|
| 第一期 | ✅ | 模组 `achievements.txt`、按 mod 存档、结算判定、语音播报、成就列表 |
| 第二期 | ✅ | 奖章 / 卡牌 / **军衔与荣誉头衔**、`cards.txt`、`titles.txt`、军械库 |
| 第三期 | ✅ | 战前选卡（TrainingMenu / 对战电脑）、进局生效、消耗充能 |
| 方案 D | ✅ | 按阵营独立存档（`achievements_per_faction`）、菜单选分支 |
| 元进度 | ✅ | 跨阵营 `_meta.json`、聚合条件、`scope meta` 成就与荣誉 |

---

## 2. 相关文件

| 路径 | 作用 |
|------|------|
| `soundrts/achievements.py` | 加载定义、判定、存档、奖励、播报消息 |
| `soundrts/faction_progress.py` | 按阵营存档路径、阵营匹配、菜单选分支 |
| `soundrts/meta_progress.py` | 跨阵营元进度（`_meta.json`、分支快照聚合） |
| `soundrts/cards.py` | 卡牌定义加载 |
| `soundrts/worldplayerstats.py` | 结算维度、`score_grade_letter()` |
| `soundrts/achievements_menu.py` | 主菜单：成就列表 + 军械库 |
| `soundrts/game.py` | `_say_achievements()` 在 `post_run` 调用 |
| `soundrts/lib/resource.py` | `load_rules_and_ai()` 内加载 achievements + cards + titles |
| `res/achievements.txt` | 基础版成就定义（含 `reward` 行） |
| `soundrts/titles.py` | 军衔阶梯 + 荣誉头衔定义 |
| `res/titles.txt` | 基础版头衔（列兵→元帅 + 成就荣誉） |
| `mods/<mod>/achievements.txt` | 模组追加/覆盖 |
| `mods/<mod>/cards.txt` | 模组追加/覆盖 |
| `mods/<mod>/titles.txt` | 模组自定义军衔/荣誉名称与阶梯 |
| `user/achievements/<mod_key>.json` | 解锁 + 奖章 + 卡牌 + 荣誉头衔（单存档模式） |
| `user/achievements/<mod_key>/<faction>.json` | 按阵营分支存档（`achievements_per_faction 1`） |
| `user/achievements/<mod_key>/_meta.json` | 跨阵营元成就与元荣誉（`achievements_per_faction 1`） |

**mod key** 与存档目录规则相同，见 `soundrts/paths.py` → `current_mod_key()`。

**按阵营进度（方案 D）**：模组 `rules.txt` 设 `achievements_per_faction 1` 后，各分支存档为 `user/achievements/<mod_key>/<faction>.json`；成就/军衔/荣誉定义须加 `faction <race_id>` 才会在该分支判定与显示。主菜单「成就」与战前选卡会先选阵营；随机阵营时会提示选定分支并写入本局阵营。从分支子菜单（成就列表 / 军械库）返回会回到**阵营选择**，取消则回主菜单。

**跨阵营元进度**：同一 mod 下另存 `user/achievements/<mod_key>/_meta.json`。元成就在 `achievements.txt` 中写 `scope meta`（无 `faction`），条件读取**所有分支存档**的聚合数据；奖励以元荣誉头衔为主，少量奖章记入 `_meta.json`（不计入单分支军衔）。主菜单「成就」在有多分支时出现 **「跨阵营进度」** 入口。

**战役与统计**：战役局（`game.is_campaign_session()`）**不计入**成就、奖章、军衔晋升与结算分数播报/统计存档。**联机对战**（`game_type_name == "multiplayer"`）仍播报结算分数并写入历史统计，但**不计入**成就、奖章、军衔与卡牌进度。

---

## 3. achievements.txt 格式

与 `ai.txt` 类似：每个成就一个 `def` 块；模组可用 `clear` 清空后重写。

```txt
def grade_s
title 5300
condition grade S
once_per map_ai
reward medal 50
reward card card_mixed_army
```

### 指令

| 指令 | 说明 |
|------|------|
| `title <tts_id>` | 成就名称 |
| `condition grade S` | 结算评级为 S（A/B/C/D/E 同理） |
| `condition victory` | 本局胜利 |
| `condition utilization_below 30` | 资源利用率 **严格小于** 30，且胜利 |
| `condition defeated_ai nightmare` | 击败了列表中**任一**敌方电脑难度（同一条可写多个，OR） |
| `condition map jl9 z5` | 在指定地图对局（同一条可写多个地图名，OR）；常与 `victory`、`defeated_ai` 合用 |
| `condition defeated_ai_total_at_least 5 beginner` | 累计击败初级电脑 ≥5 次（`easy` 计入 `beginner`） |
| `condition defeated_ai_map_at_least pra1 3 beginner` | 在地图 `pra1` 累计击败初级电脑 ≥3 次 |
| `condition survival_at_least 100` | 单位存活维度分 ≥ 100 |
| `condition building_defense_at_least 100` | 建筑保全维度分 ≥ 100 |
| `once` | 全局只解锁一次（默认） |
| `once_per map` | 每个地图名各解锁一次 |
| `once_per map_ai` | 每个「地图 + 本局最强敌方 AI 难度」各解锁一次 |
| `reward medal <n>` | 解锁时获得 n 枚奖章 |
| `reward card <card_id> [<times>]` | 解锁时获得卡牌充能（次数 × 卡定义的 `grant_charges`） |
| `reward title <title_id>` | 解锁时获得荣誉头衔（`titles.txt` 中 `kind honor`） |
| `faction <race_id>` | 仅在该阵营游玩时判定/显示（需 `achievements_per_faction 1`）；省略且 `scope` 为默认时**不会**进入分支成就列表 |
| `scope meta` | 跨阵营元成就：写入 `_meta.json`，在分支结算保存后聚合判定（需 `achievements_per_faction 1`） |
| `repeat_medal <n>` | **重复完成**（同一 `once` 键已解锁后再达成）仅再获得 n 枚奖章；**不再**发卡牌/荣誉/「成就解锁」播报 |

### 跨阵营聚合条件（`scope meta`）

| 指令 | 说明 |
|------|------|
| `condition factions_unlocked_at_least <N> <M>` | 至少 N 个分支各已解锁 ≥M 项成就 |
| `condition factions_medals_at_least <N> <M>` | 至少 N 个分支奖章累计 ≥M |
| `condition factions_honors_at_least <N> <M>` | 至少 N 个分支各有 ≥M 个荣誉头衔 |
| `condition factions_achievement_id_contains_at_least <N> <子串>` | 至少 N 个分支已解锁 id 含该子串的成就（如 `_map_` 表示地图里程碑） |

元成就示例：

```txt
def meta_three_branches
scope meta
title 79950
condition factions_unlocked_at_least 3 1
once
reward title honor_meta_novice
```

**电脑难度归一化**：阵营自定义 AI 脚本名（如 `traditionnel_exp`）在累计击败计数时会映射到标准难度（`expert` 等），旧存档读取时自动迁移 `ai_defeats` / `map_ai_defeats` 键名。

同一 `def` 内多条 `condition` 为 **与（AND）** 关系。

**重复完成**：例如同一张图、同一电脑难度再次打出 S 级，不会再解锁成就或给卡，但若配置了 `repeat_medal 8`，结算会播报「重复完成，完美作战，获得 8 奖章」。奖章仍计入军衔。设为 `0` 或省略则重复完成无奖励。

**奖章 → 军衔**：奖章只增不减；当前军衔 = 已达成 `medals` 阈值的最高一档。跨档时结算播报「军衔晋升：少尉」。

**荣誉头衔**：仅当与成就名称**不同**时使用（如成就「噩梦猎手」+ 荣誉「噩梦克星」）。同名时只播「成就解锁」，军械库荣誉栏不重复显示。

---

## 4. titles.txt 格式

```txt
def rank_lieutenant
kind rank
title 5404
medals 140

def honor_nightmare_slayer
kind honor
title 5422
```

| 指令 | 说明 |
|------|------|
| `title <tts_id>` | 头衔名称 |
| `kind rank` | 军衔（需 `medals`） |
| `kind honor` | 荣誉（由成就 `reward title` 授予） |
| `medals <n>` | 累计 n 枚奖章达到该军衔 |
| `faction <race_id>` | 该军衔/荣誉仅属于此阵营（需 `achievements_per_faction 1`）；省略且用于元荣誉时不带 `faction` |

模组可用 `clear` 重写整套阶梯（例如改为星际/武侠称谓）。多分支模组（如 CrazyMod）可为每个 `class race` 写一套带 `faction` 的阶梯。元荣誉（如 `honor_meta_novice`）无 `faction`，只在「跨阵营进度」军械库显示。

---

## 5. cards.txt 格式

```txt
def card_infantry
title 5322
tags infantry
spawn footman 3
grant_charges 1
```

| 指令 | 说明 |
|------|------|
| `title <tts_id>` | 卡牌名称 |
| `tags ...` | 标签（第三期与 mod 单位 tags 配合） |
| `spawn <unit_type> <n>` | 使用卡时生成单位（第三期生效） |
| `resource resource1 <n>` | 使用卡时给予起始资源（第三期） |
| `tech <upgrade_id> [...]` | 授予科技（等同研究完成；可与 spawn 组合） |
| `train_bonus <unit_type> <n>` | 训练加成：**首次**从建筑完成训练该单位时额外生成 n 个（整局每种仅一次） |
| `delay <seconds>` | 效果延迟秒数（游戏时间）；0 或未写 = 开局立即 |
| `delay_minutes <n>` | 同上，单位为分钟 |
| `grant_charges <n>` | 每次奖励增加的充能数（默认 1） |
| `min_rank <rank_id>` | 战前携带所需最低军衔 |
| `faction <race_id>` | 仅该阵营军械库/战前可选（需 `achievements_per_faction 1`）；省略则为全阵营通用（如资源卡） |

多条 `spawn` 表示组合卡。`spawn` + `tech` + 共用 `delay` 可在到点后同时发兵与发科技。

**延迟卡牌**（1.4.4.4+）：进局时扣充能并预约效果，到点语音「携带卡牌效果生效」。详见 **[delayed-card-loadout.md](../delayed-card-loadout.md)**。

**训练加成卡**：`train_bonus` 在本局注册被动——**第一次**训练完成该单位时额外再生成 n 个，之后不再触发。详见 **[train-bonus-card-loadout.md](../train-bonus-card-loadout.md)**。

---

## 6. 运行时流程

```
主菜单 → 成就
  ├─（多分支）选阵营 → 成就列表 / 军械库 → 返回 → 再选阵营
  └─（多分支）跨阵营进度 → 元成就列表 / 元军械库

game.post_run()
  → say_score()            # 战役局跳过
  → _say_achievements()    # 分支解锁 + 元成就 + 奖励 + 军衔晋升
```

**结算顺序（非战役）**：本局分支成就判定并保存 → 聚合各分支存档 → 元成就判定并保存 `_meta.json` → 合并播报。

**不参与判定**：观战者、无 `player.stats`、战役局、**联机对战**（`game_type_name == "multiplayer"`；仍可有结算分数播报，见 [score-grading-system.md](score-grading-system.md)）。

**多人地图 NPC**：仅 `broadcasts_defeat_and_quit` 为真的玩家（如狩猎动物、定时器 AI）击败时才播报并退出；普通地图 NPC 击败不触发成就向播报。

---

## 7. 存档 JSON 结构

### 单 mod 存档

路径：`user/achievements/<mod_key>.json`

### 按阵营存档

路径：`user/achievements/<mod_key>/<faction>.json`（`faction` 为 sanitized 的 `race_id`，如 `traditionnel`）

### 元进度存档

路径：`user/achievements/<mod_key>/_meta.json`

字段与分支存档类似，但**不含** `cards`、`ai_defeats`、`map_ai_defeats`；元奖章不计入分支军衔。

```json
{
  "unlocked": {
    "meta_three_branches": {
      "count": 1,
      "first_at": 1718280000,
      "last_at": 1718280000
    }
  },
  "once_keys": {
    "meta_three_branches": true
  },
  "medals": 25,
  "honors": ["honor_meta_novice"]
}
```

### 分支存档示例

```json
{
  "unlocked": {
    "grade_s": {
      "count": 1,
      "first_at": 1718280000,
      "last_at": 1718280000
    }
  },
  "once_keys": {
    "grade_s|map:jl1|ai:beginner": true
  },
  "medals": 50,
  "honors": ["honor_nightmare_slayer"],
  "ai_defeats": {
    "beginner": 5,
    "nightmare": 1
  },
  "map_ai_defeats": {
    "pra1": {"beginner": 3},
    "pra11": {"nightmare": 1}
  },
  "cards": {
    "card_infantry": {
      "charges": 2,
      "total_earned": 3
    }
  }
}
```

旧存档缺少 `medals` / `cards` / `honors` 时会在读取时自动补全。

---

## 8. 语音 ID

| ID | 用途 |
|----|------|
| 5244 | 成就解锁 |
| 5245–5248 | 获得奖章 / 获得卡牌 / 剩余充能 |
| 5249–5250 | 军衔晋升 / 获得荣誉称号 |
| 5300–5308 | 成就名称 |
| 5310–5319 | 菜单 |
| 5320–5332 | 卡牌名称 |
| 5340 | 军械库为空 |
| 5366 | 卡牌效果：起始位置附近生成 |
| 5367 | 重复完成（再达成已解锁成就） |
| 5370–5378 | 成就条件描述（要求 / 至少 / 在地图 / 累计…） |
| 5379–5385 | 跨阵营进度菜单与元条件描述 |
| 5400–5411 | 军衔（列兵→元帅） |
| 5420–5424 | 荣誉头衔（基础版） |
| 79600+ / 79850+ / 79900+ | CrazyMod 分阵营军衔、荣誉、累计与地图里程碑 |
| 79860–79863 | CrazyMod 元荣誉头衔 |
| 79950–79953 | CrazyMod 元成就名称 |

模组请使用 **7100+** 等同 mod 约定区间，避免与基础版冲突。CrazyMod 使用 79500+ 区间。

---

## 9. 与结算评分的关系

成就 **读取** `player.stats.score_breakdown()`，不重复实现计分逻辑。

完整计分规则见 **[score-grading-system.md](score-grading-system.md)**（七项维度、击败电脑奖励、败局 D 封顶、节约效率等）。

评级阈值与 `worldplayerstats._GRADE_TABLE` 一致（720/640/560/480/400）。

---

## 10. 第三期：战前携带卡

**入口：** 主菜单 → 单人游戏 → 在地图上开始 → 点「开始」后。

**流程：**
1. 按当前军衔决定 **栏位数**（少尉 1、上尉 2、上校 3、上将 4…，见 `titles.txt` 的 `loadout_slots`）
2. 逐栏选择要携带的卡（可「本栏不携带」或「直接开始游戏」）
3. 进局后在 `populate_map` 之后生效：发资源 / 在起始格附近生成单位 / 授予 `tech`；可选 **`delay` / `delay_minutes` 延迟到点再生效**（进局即扣充能，到点语音播报）
4. **消耗 1 点充能**（写入 `user/achievements/<mod>.json`）

**限制：**
- 仅 `TrainingGame`（自定义图 / 随机图 + 邀请电脑），**不含战役、联机**
- 卡须 `min_rank` 满足当前军衔（军械库中已有提示）
- 进局后卡牌 `spawn` 在起始位置附近立即生成单位；**不占人口**
- 充能不足或栏位已满时不可重复选择

**模组：** `cards.txt` 的 `min_rank`；`titles.txt` 的 `loadout_slots` 与军衔阶梯。

---

## 11. 模组关闭整套系统

在模组 `rules.txt` 的 `def parameters` 中设置：

```txt
def parameters
achievements_enabled 0
```

多分支模组另可设：

```txt
def parameters
achievements_enabled 1
achievements_per_faction 1
```

效果（当前 mod 生效时）：

| 项目 | 行为 |
|------|------|
| 主菜单「成就」 | **不显示** |
| 结算成就 / 奖章 / 晋升 | **不判定、不播报** |
| 战前携带卡 | **不出现** |
| 进局卡牌效果 | **不应用** |
| `achievements.txt` / `cards.txt` / `titles.txt` | **不加载**（省解析） |

基础版默认 `achievements_enabled 1`。设为 `0` 后该 mod 的 `user/achievements/<mod_key>.json` 仍保留，重新启用后可继续用。

若只想自定义内容、不要基础版成就，仍用各文件的 `clear`；与 `achievements_enabled 0` 可二选一或组合（完全关闭用 `0` 即可）。

---

## 12. 测试

```bash
python -m pytest soundrts/tests/test_card_loadout.py -v
python -m pytest soundrts/tests/test_achievements.py -v
python -m pytest soundrts/tests/test_cards.py -v
python -m pytest soundrts/tests/test_titles.py -v
python -m pytest soundrts/tests/test_faction_progress.py -v
python -m pytest soundrts/tests/test_meta_progress.py -v
python -m pytest soundrts/tests/test_achievements_menu_navigation.py -v
python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
```

---

## 13. CrazyMod 示例（方案 D + 元进度）

`mods/crazyMod9beta10/rules.txt`：

```txt
achievements_enabled 1
achievements_per_faction 1
```

- 10 个分支各有独立军衔阶梯、成就与地图里程碑（如 `trad_map_pra1` … `delf_map_pra10`）
- 元成就四档：`meta_three_branches` / `meta_five_sergeant` / `meta_eight_maps` / `meta_ten_masters`
- 元荣誉：`honor_meta_novice` … `honor_meta_conqueror`

---

## 14. 开发备忘

- 打包发布需包含 `res/achievements.txt`、`res/cards.txt`、`res/titles.txt` 与 tts 新 ID
