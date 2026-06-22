# 评分与评级系统（Score & Grading）

> **玩家向说明**：[../player/score-and-grades.md](../player/score-and-grades.md)

本文档说明 SoundRTS **对局结束后**的多维度评分、字母评级与语音播报规则。实现位于 `soundrts/worldplayerstats.py` 的 `Stats` 类。

英文版：[../../en/developer/score-grading-system.md](../../en/developer/score-grading-system.md)

与成就系统的关系见 [achievement-system.md](achievement-system.md) 第 9 节；玩家简述见 [../player/score-and-grades.md](../player/score-and-grades.md)。

---

## 1. 何时启用

| 场景 | 评分播报 | 历史统计写入 |
|------|----------|--------------|
| 自定义图 / 随机图 + 电脑（TrainingGame） | ✅ | ✅ |
| 联机对战 | ✅ | ✅ |
| 战役 / 合作战役 | ❌ | ❌ |
| 观战者 | ❌（播报「观战结束」） | ❌ |

判定：`game.is_campaign_session()` 为真时跳过 `say_score()` 与 `_record_stats()`。

结算顺序（`game.post_run()`）：先 `say_score()` 播报分数，再 `_say_achievements()` 播报成就。

---

## 2. 分数结构概览

```
总分 total = 基础分 base_total + 击败电脑奖励 ai_defeat
```

| 字段 | 含义 |
|------|------|
| `base_total` | 七项基础维度之和，**上限 800** |
| `ai_defeat` | 击败敌方电脑额外加分，**不计入 800 上限** |
| `total` | `base_total + ai_defeat`，可超过 800 |
| `percent` | `base_total × 100 ÷ 800`，上限 100% |
| `max` | 固定为 **800**（百分比分母，不含 ai_defeat） |
| `grade_total` | 用于字母评级的分数（败局有封顶，见 §5） |

### 七项基础维度

| 维度 | 键名 | 分值范围 | 说明 |
|------|------|----------|------|
| 胜负 | `outcome` | 0 或 **200** | 胜利 200，失败 0 |
| 采集 | `mining` | 0–100 | 相对地图资源储量或参照量 |
| 效率 | `efficiency` | 0–100 | 资源利用或节约（见 §4） |
| 存活 | `survival` | 0–100 | 己方单位损失率 |
| 建筑保全 | `building_defense` | 0–100 | 己方建筑损失惩罚 |
| 战斗 | `combat` | 0–100 | 相对敌方产量的击杀 |
| 拆迁 | `demolition` | 0–100 | 摧毁敌方建筑 |

### 汇总行（播报用）

| 键名 | 计算 |
|------|------|
| `unit_line` | `survival + combat` |
| `building_line` | `building_defense + demolition` |
| `mining_by_resource[]` | 每种资源单独的采集分（播报逐条显示） |

---

## 3. 各维度计算公式

所有维度分经 `_clamp_score()` 限制在 **0–100**（胜负除外，固定 0/200）。内部资源量使用定点整数（`PRECISION`），播报时除以 `PRECISION` 显示。

### 3.1 胜负（outcome）

- 胜利：`200`
- 失败：`0`

权重为其余单项的 **2 倍**，体现「赢没赢」的重要性。

### 3.2 采集（mining）

**有效采集量** = `gathered[i] - starting_resources[i]`（各资源求和，不低于 0）。开局自带资源不计入。

**有地图储量**（`world.map_deposit_capacity` 总和 > 0）：

```
mining = clamp(有效采集总量 × 100 ÷ 地图储量总和)
```

地图储量由地图上每个 `Deposit` 在加载时累加至 `map_deposit_capacity`（见 `worldresource.py`）。

**无地图储量**（开放图、无限矿等）：

- **战役局**：胜利 → 100；失败 → 0
- **非战役**：若有效采集 ≤ 0 → 0；否则按参照量比例：
  ```
  mining = clamp(有效采集总量 × 100 ÷ 1000)
  ```
  其中 `1000` 为内部定点常量 `MINING_REFERENCE_GATHER`（即游戏内显示为 1000 的资源单位）。

**按资源分项**（`mining_by_resource[i]`）：若该资源有对应 `map_deposit_capacity[i]`，按比例计；若无储量且地图总储量也为 0，则按同一参照量 `1000` 计；若地图有储量但该资源无对应矿点，则为 0。

### 3.3 效率（efficiency）

```
利用率 utilization_percent = clamp(消耗总量 ÷ 采集总量 × 100)   // 采集为 0 时为 0
```

- **默认模式** `efficiency_mode = "utilization"`：  
  `efficiency = utilization_percent`（消耗越多分越高）
- **节约模式** `efficiency_mode = "frugal"`（**仅胜利**且利用率 **< 50%**）：  
  `efficiency = clamp((1 - 消耗÷采集) × 100)`  
  播报标签为「节约效率」（TTS 5251），否则为「资源利用率」（TTS 5227）

失败局即使低消耗也走利用率模式，避免「故意不花钱刷节约分」。

### 3.4 存活（survival）

```
若 produced(unit) > 0:
    survival = clamp((produced - lost) × 100 ÷ produced)
否则:
    survival = 0
```

未生产任何单位时存活分为 **0**（避免「不造兵白拿分」）。

### 3.5 建筑保全（building_defense）

```
building_defense = max(0, 100 - lost(building) × 5)
```

每损失 1 座己方建筑扣 **5** 分。

### 3.6 战斗（combat）

统计所有**非己方、非同盟、非中立**玩家的 `produced(unit)` 之和为 `enemy_units`：

```
若 enemy_units > 0:
    combat = clamp(killed(unit) × 100 ÷ enemy_units)
否则:
    combat = clamp(killed(unit) × 5)    // 无产量参照时的兜底
```

### 3.7 拆迁（demolition）

```
demolition = clamp(killed(building) × 5)
```

每摧毁 1 座敌方建筑得 **5** 分，上限 100（即 20 座封顶）。

### 3.8 击败电脑奖励（ai_defeat）

对每名**已被击败**的敌方电脑，按其 AI 难度累加 `defeat_score`：

| 内置难度 | 默认 defeat_score |
|----------|-------------------|
| beginner / easy | 10 |
| intermediate / aggressive | 20 |
| advanced | 40 |
| expert | 80 |
| nightmare | 200 |

- 分值来自 `ai.txt` 中对应 `def` 块的 `defeat_score <n>`；未声明时查上表；自定义 AI 名无声明则为 **0**。
- **不计分**的情况：同盟电脑、未击败、AI 类型为 `timers` / `ai2` / 空串、`defeat_score 0`、非电脑玩家。
- 同难度多台电脑分别计分；播报按难度分组显示数量。
- 已退出玩家（`ex_players`）若满足条件仍计入。

---

## 4. 字母评级

基于 `grade_total` 查表（与 `score_grade_msg()` / `score_grade_letter()` 一致）：

| 字母 | 最低 grade_total |
|------|------------------|
| **S** | 720 |
| **A** | 640 |
| **B** | 560 |
| **C** | 480 |
| **D** | 400 |
| **E** | 0 |

### 败局评级封顶

失败时 `grade_total = min(total, 479)`（常量 `DEFEAT_GRADE_MAX_TOTAL`）。

- 即使 `total` 因战斗、拆迁等维度很高，**字母最高仍为 D**（C 门槛 480 达不到）。
- 胜利局无此限制，可拿 S/A/B/C 等。

示例：败局 raw `total = 600` → 评级 **D**；同分若胜利 → 评级 **B**。

---

## 5. 原始统计事件

`Stats.add(event, target, inc)` 在局内累积，`score_breakdown()` 据此计分：

| event | target | 触发场景（典型） |
|-------|--------|------------------|
| `gathered` | 资源索引 | 工人采矿、起始资源、卡牌发资源等 |
| `produced` | `unit` / `building` | 单位/建筑训练完成 |
| `lost` | `unit` / `building` | 己方单位/建筑被毁 |
| `killed` | `unit` / `building` | 击杀敌方单位/建筑 |

`consumed(i) = gathered(i) - player.resources[i]`（当前库存差额视为已消耗）。

局末 `stats.freeze()` 固定 `game_duration`（用于播报「在 X 分 Y 秒」）。

---

## 6. 结算语音播报（score_msgs）

播报顺序（`Stats.score_msgs()`）：

1. **胜/败** + 对局时长 + 胜负分（+200 / +0）
2. **单位行**：生产数、损失数、歼灭数 + `unit_line` 分
3. **建筑行**：生产数、损失数、歼灭数 + `building_line` 分
4. **各资源行**：采集量、消耗量 + 该资源采集分
5. **效率行**：利用率百分比 + 效率分（节约/利用标签）
6. **击败电脑行**（每条）：难度名称 [×数量] + 奖励分
7. **总分行**：`total` / `max`(800) / `percent`%
8. **评级行**：字母等级 + 「历史记录说明」提示

TTS 编号见 `soundrts/msgparts.py`（5225–5243、5251）与 `res/ui/tts.txt`。

---

## 7. 与成就系统的接口

`achievements.build_context()` 从 `score_breakdown()` 提取：

| 成就条件 | 来源字段 |
|----------|----------|
| `condition grade S` 等 | `score_grade_letter(total)` |
| `condition victory` | `player.has_victory` |
| `condition utilization_below N` | `utilization_percent`（须胜利） |
| `condition survival_at_least N` | `survival` |
| `condition building_defense_at_least N` | `building_defense` |
| `condition defeated_ai expert` 等 | `ai_defeat_entries` |

联机对战仍执行 `say_score()`，但 `process_game_end_achievements()` 在 `game_type_name == "multiplayer"` 时直接返回，不读取上述字段写入存档。

---

## 8. 模组定制

### ai.txt — 击败奖励分

```txt
def my_custom_ai
defeat_score 55
...
```

`defeat_score 0` 表示该 AI 被击败不计奖励分。

### 关闭整套评分相关系统

`rules.txt` 设 `achievements_enabled 0` 时，不加载 achievements/cards/titles；评分播报仍可在非战役局执行（与成就独立），但通常一并关闭成就菜单。

---

## 9. 相关文件

| 路径 | 作用 |
|------|------|
| `soundrts/worldplayerstats.py` | 计分、评级、播报消息 |
| `soundrts/definitions.py` | `DEFAULT_AI_DEFEAT_SCORE`、`get_ai_defeat_score()` |
| `soundrts/worldresource.py` | 地图 `map_deposit_capacity` 登记 |
| `soundrts/worldunit/worldcreature.py` | `lost` / `killed` 统计 |
| `soundrts/worldunit/world_attributes.py` | `produced` 统计 |
| `soundrts/game.py` | `say_score()`、`post_run()` |
| `soundrts/achievements.py` | 读取 breakdown 判定成就 |
| `soundrts/msgparts.py` | 播报常量 |
| `res/ui/tts.txt`、`res/ui-zh/tts.txt` | 语音文案 |

---

## 10. 测试

```bash
python -m pytest soundrts/tests/test_score_breakdown.py -v
python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
python -m pytest soundrts/tests/test_ai_start_settings.py -k defeat_score -v
```

`test_score_breakdown.py` 覆盖：各维度公式、败局 D 封顶、节约效率模式、百分比不含 ai_defeat、击败电脑分组等。

---

## 11. 设计说明（调参参考）

| 常量 | 值 | 含义 |
|------|-----|------|
| `SCORE_BASE_MAX` | 800 | 基础满分 |
| `OUTCOME_MAX` | 200 | 胜负权重 |
| `DEFEAT_GRADE_MAX_TOTAL` | 479 | 败局评级上限对应 D |
| `MINING_REFERENCE_GATHER` | 1000（定点） | 无矿储量地图的采集参照 |
| 建筑损失惩罚 | 5 分/座 | `building_defense` |
| 拆迁奖励 | 5 分/座 | `demolition` |

**未纳入评分的维度**（当前版本）：对局时长、科技进度。二者在代码中暂无对应分项；`game_duration` 仅用于播报时长。

**百分比含义**：表示「基础七项完成度」，不含击败电脑奖励。因此总分 900（800 基础 + 100 击败）仍可能显示 100%，评级 S 需 `grade_total ≥ 720`（胜利时等于 `total`）。
