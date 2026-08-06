# 通用技能系统（class skill）

面向 **模组作者**：在 `rules.txt` 中用 `class skill` 定义主动技能，无需 Python 源码。完整示例见官方 mod **`mods/wuxia/rules.txt`**（武侠技能演示）。

## 基本概念

用 `class skill` 定义技能，取代旧版 `class ability`：

```
def fireball
class skill
mana_cost 50
cost 10 0
time_cost 30
effect harm_target 60
effect_target ask
effect_range 12
cooldown 10
```

单位通过 `can_use_skill` 学会技能；升级仍用 `can_use_tech`。

### 统一技能系统（1.4.4.6 起）

同一 `class skill` 可同时配置 **手动释放** 与 **自动触发**。学会的技能统一写在单位的 `can_use_skill` 中。

| 属性 | 说明 |
|------|------|
| `manual_use 1` | 出现在命令菜单，玩家可按键释放（默认 `1`） |
| `auto_trigger 1` | 战斗中满足条件时自动触发（默认 `0`） |
| `trigger_timing` | 自动触发的时机（见下文） |

二者可并存：例如 `manual_use 1` + `auto_trigger 1` 表示既能手动放，也能在战斗中概率自动触发。

旧字段 `active_trigger_skills`、`attack_trigger_skills`、`attack_replace_skills`、`passive_trigger_skills`、`death_trigger_skills` 仍兼容；新 mod 建议只用 `can_use_skill` + 技能上的 `auto_trigger` / `trigger_timing`。

## 技能触发方式

### 自动触发时机（trigger_timing）

须同时设置 `auto_trigger 1` 与 `trigger_timing`。默认值为 `on_hit`。

| `trigger_timing` | 触发时机 | 旧单位列表（仍兼容） |
|----------------|----------|----------------------|
| `on_hit` | 攻击者 **命中敌人之后**（默认） | `active_trigger_skills` |
| `on_attack` | **发起攻击时**附加释放，**普攻照常进行** | `attack_trigger_skills` |
| `on_attack_replace` | **发起攻击时**释放，**替代本次普攻**（技能触发成功则跳过普攻） | `attack_replace_skills` |
| `on_damaged` | **被敌人命中时**（被动） | `passive_trigger_skills` |
| `on_death` | **单位/建筑死亡时**（摧毁前瞬间） | `death_trigger_skills` |

除 `on_death` 外，自动触发时会检查法力（`mana_cost`）、冷却（`cooldown`），并消耗法力、进入冷却（与手动释放相同）。若技能写了 `ready`，自动触发也会先进入前摇再生效。

**`on_death` 特例**：死亡时 HP 已为 0，因此**不检查、不消耗**法力与冷却，也**无前摇**，效果立即生效。爆炸中心默认取自身坐标；`effect_target ask` 时若有击杀者则以其为目标（范围伤害建议写 `effect_target self`）。连锁击杀会继续触发对方的 `on_death`。

同一技能可同时 `manual_use 1` + `trigger_timing on_death`（如 CrazyMod 炸药库手动引爆）。**手动成功释放后会记为已引爆**，随后因爆炸摧毁自身时**不会再触发一次** `on_death`；被敌人摧毁时仍会正常触发一次。

**注意**：`on_hit` 仅在攻击者对 **敌人** 造成伤害后触发；`on_damaged` 在 **被敌人攻击命中** 时由受击方触发。`on_death` 与攻击自爆 `mdg_explode`/`rdg_explode` 不同：后者仅在**主动攻击**时触发。

#### 示例 1：命中后附加伤害（on_hit）

对 **被命中的敌人** 触发时，``effect_target`` 不要写 ``self``（默认为自身）。实战写法：

```
def skill_poison_strike
class skill
auto_trigger 1
manual_use 0
trigger_timing on_hit
active_trigger_rate 30
effect debuffs b_poison
effect_target ask
```

自动触发时 ``ask`` 会解析为当前受击的敌人。测试见 ``test_wuxia_skills.py`` 的 ``skill_proc``。

#### 示例 2：出手附加 buff（on_attack）

```
def skill_battle_cry
class skill
auto_trigger 1
manual_use 0
trigger_timing on_attack
active_trigger_rate 50
effect buffs b_battle_cry
effect_target self
```

发起攻击时 50% 概率对自身加 buff，**本次普攻仍会继续**。

#### 示例 3：替代普攻（on_attack_replace）

```
def skill_flame_strike
class skill
auto_trigger 1
manual_use 1
trigger_timing on_attack_replace
active_trigger_rate 100
effect harm_target mdg
effect_target ask
effect_range 1
mdg 15
cooldown 3
mana_cost 10
```

攻击开始时尝试释放；成功则 **本次不进行普通攻击**。可保留 `manual_use 1` 以便玩家也能从菜单手动施放。

#### 示例 4：受击反击（on_damaged）

```
def skill_thorns
class skill
auto_trigger 1
manual_use 0
trigger_timing on_damaged
passive_trigger_rate 30
effect harm_target 10
effect_target ask
```

被敌人命中时 30% 概率对 **攻击者** 造成 10 点固定伤害（``effect_target ask`` 在被动触发时解析为攻击者）。

#### 示例 5：死亡爆炸（on_death）

炸药库被摧毁时对周围造成范围伤害：

```
def skill_ammo_explode
class skill
auto_trigger 1
manual_use 0
trigger_timing on_death
effect harm_area 40 6
effect_target self

def ammo_depot
class building
hp_max 50
can_use_skill skill_ammo_explode
```

也可用 `effect deploy 1 fx_blast` 生成短暂 `class effect` 伤害区，或 `effect summon` 在死亡处生成单位。测试见 `test_death_skills.py`。

#### 示例 6：手动 + 自动并存

```
def skill_heal_proc
class skill
auto_trigger 1
manual_use 1
trigger_timing on_hit
active_trigger_rate 15
effect buffs b_small_heal
effect_target self
mana_cost 20
cooldown 8
```

玩家可按技能键手动治疗；战斗中命中敌人时另有 15% 概率自动触发（仍消耗法力并 respect 冷却）。

### 触发概率

| 属性 | 适用时机 | 说明 |
|------|----------|------|
| `active_trigger_rate` | `on_hit`、`on_attack`、`on_attack_replace` | 触发概率 1–100（默认 100） |
| `passive_trigger_rate` | `on_damaged`、`on_death` | 触发概率 1–100（默认 100） |
| `mdg_trigger_rate` | 上述主动类时机 | 若 > 0，**近战攻击时优先使用**，覆盖 `active_trigger_rate` |
| `rdg_trigger_rate` | 上述主动类时机 | 若 > 0，**远程攻击时优先使用**，覆盖 `active_trigger_rate` |

示例：近战 80%、远程 40% 的命中触发：

```
active_trigger_rate 100
mdg_trigger_rate 80
rdg_trigger_rate 40
trigger_timing on_hit
```

### 触发条件

| 属性 | 说明 |
|------|------|
| `trigger_condition` | 条件表达式，格式 `属性 运算符 值`（三词，空格分隔） |
| `hp_threshold` | 简写：生命百分比 ≤ 阈值时才触发（整数，如 `30` 表示 30% 以下） |

`trigger_condition` 语法与 buff 相同。`hp`、`mana` 在条件中按 **百分比** 比较：

```
trigger_condition hp < 30
```

等价于简写 `hp_threshold 30`（生命 ≤ 30% 时方可触发）。

**限制**：`trigger_condition` / `hp_threshold` 目前由 `on_hit` 与 `on_damaged` 路径检查；`on_attack` / `on_attack_replace` **不**检查这两项条件。

### 前摇（ready）

```
ready 2
```

自动触发与手动释放均会先等待 `ready` 秒再执行 `effect`；可在技能 `style.txt` 写 `ready <音效ID>` 在前摇开始时播放。

### 与 buff 攻击触发的区别

| 机制 | 配置位置 | 典型用途 |
|------|----------|----------|
| 技能 `auto_trigger` | `class skill` + `can_use_skill` | 释放完整技能 effect（harm、buff、deploy 等） |
| 攻击附带 buff | 单位 `attack_trigger_buffs` / `attack_replace_buffs` 等 | 仅施加 buff/debuff，无独立技能 def |
| buff `is_active` / `is_passive` | `class buff` | buff 自身在攻击/受击时叠加 |

同一单位可同时使用技能自动触发与攻击附带 buff；二者独立判定概率与冷却。

### 目标与范围

| 属性 | 说明 |
|------|------|
| `effect_target` | `self`（自身）、`ask`（玩家选目标）、`random`（随机格） |
| `effect_range` | 施法距离（格）；`inf` 为无限 |
| `effect_radius` | 效果中心半径（部分 legacy 效果使用） |

### 消耗与冷却

`mana_cost`、`cost`（资源）、`time_cost`（吟唱秒数）、`cooldown`（冷却秒数）、`ready`（前摇秒数；可在技能 `style.txt` 定义 `ready <sound>` 播放音效）。

## 通用技能效果（effect）

语法：`effect <类型> [参数…]`

每个技能通常只写一行 `effect`。引擎支持以下可执行类型（legacy 与 1.4.4.6 通用效果）：

### harm_target — 单体伤害

**固定真实伤害**（绕过护甲）：

```
effect harm_target 60
```

**战斗管线伤害**（护甲、暴击、溅射等完整流程；技能上的非零战斗属性覆盖施法者）：

```
effect harm_target mdg
effect harm_target rdg
```

wuxia 示例：`skill_lipi`（固定 60）、`skill_lipi_mdg`（战斗 mdg）。

### harm_area — 范围伤害

**固定真实伤害**：

```
effect harm_area <伤害> <半径>
```

示例（wuxia `skill_heng_sao`）：`effect harm_area 50 3`（固定 50 真实伤害，半径 3）。

**战斗管线范围伤害**：

```
effect harm_area mdg <半径>
effect harm_area rdg <半径>
```

半径可省略，此时使用技能的 `effect_radius`（默认 6）。技能可覆写战斗属性：

```
def skill_heng_sao_mdg
class skill
effect harm_area mdg 3
mdg 12
mdg_splash 6
mdg_radius 1.5
mdg_splash_decay_min 0.5
effect_target ask
effect_range 8
```

### burst — 连击（技能）

```
effect burst mdg <次数> (interval <秒>) (window <秒>)
effect burst rdg <次数> (interval <秒>) (window <秒>)
```

或使用逐发延迟：

```
effect burst mdg 3 (delays 0 0.2 0.5)
```

- `interval`：相邻两击间隔（秒）
- `window`：连击总时间窗口（秒）
- `delays`：每击的绝对延迟列表，长度须等于次数

伤害取自技能或施法者的 `mdg` / `rdg` 及完整战斗属性。wuxia 示例：`skill_jifengci`、`skill_jifengci_rdg`。

> **注意：技能 `effect burst` ≠ 单位 `damage_seq` 连发攻击。** 详见本文「进阶」一节及 `player/burst-attacks.htm`。

### push — 击退

```
effect push <距离>
```

将敌方目标向远离施法者方向推开，自动寻找可站立格。wuxia 示例：`skill_moli_dan`（`effect push 5`）。

### buffs / debuffs — 施加增益或减益

```
effect buffs <buff名> [<buff名2> …]
effect debuffs <debuff名>
```

- `effect_target self`：对自身施放
- `effect_target ask` + `effect_range`：对选中目标施放

`debuffs` 仅对敌人生效。wuxia 示例：`skill_douzhuan` → `effect buffs b_douzhuan`。

**伤害反弹**：没有独立的 `effect reflect`。须在 buff 定义上使用 `reflect_percent`（百分比），再由技能 `effect buffs` 施加。wuxia 示例：`b_douzhuan` 的 `reflect_percent 100`。

### deploy — 部署战场效果

```
effect deploy <存活秒数> [<数量>] <class effect 类型名>
```

在目标格放置 `class effect` 实体（火墙、治疗区等）。详见第三节「战场效果」。

### summon — 召唤单位

```
effect summon <存活秒数> [<数量>] <单位类型> …
```

可选：`summon_requires_build_field`、`summon_requires_marked_field`。

### 旧版效果（仍可用）

| effect | 说明 |
|--------|------|
| `teleportation` | 传送友方单位至目标格 |
| `recall` | 召回目标格友方单位至施法者处 |
| `conversion` | 转化敌方单位 |
| `raise_dead <秒> <单位…>` | 从尸体复活 |
| `resurrection <上限>` | 复活友方尸体 |
| `harm <等级>` | 旧式：在目标格生成临时 harm 效果（建议改用 `harm_target` / `harm_area`） |

### 不可执行（仅 UI 显示）

`effect heal`、`effect damage` 仅在属性界面格式化显示，**不会**在释放时执行治疗或伤害。治疗请用单位 `heal_*` 属性、`class effect` 或 `effect buffs` 增强治疗属性。

## 目标类型过滤（harm_target_type）

对 `burst`、`harm_target`、`harm_area`、`push` 生效。未配置时 **默认仅对敌人** 生效（1.4.4.6 起）。

```
harm_target_type enemy ground unit -building
```

- 标签前加 `-` 表示排除，如 `-building`、`-undead`、`-enemy`
- `harm_target_type` 与 buff `target_type`：正向标签为 **AND**（须全部满足）
- `heal_target_type` 与 `mdg_targets` / `rdg_targets`：正向标签为 **OR**

示例：

```
harm_target_type enemy unit -building
heal_target_type unit -undead
mdg_targets ground air -building
```

## 参考 mod：wuxia 逐技能对照

官方演示 mod：`mods/wuxia/rules.txt`。测试地图：`mods/wuxia/multi/skills_test.txt`。

| 技能 | effect 类型 | 要点 |
|------|-------------|------|
| `skill_jifengci` | `burst mdg` | 5 连击，间隔 0.2s，窗口 1s，近战范围 2 |
| `skill_jifengci_rdg` | `burst rdg` | 同上，远程范围 6 |
| `skill_heng_sao` | `harm_area 50 3` | 固定 50 真实伤害，半径 3 |
| `skill_heng_sao_mdg` | `harm_area mdg 3` | 战斗管线 + 技能覆写 mdg/splash |
| `skill_lipi` | `harm_target 60` | 固定 60 真实伤害 |
| `skill_lipi_mdg` | `harm_target mdg` | 战斗管线单体伤害 |
| `skill_douzhuan` | `buffs b_douzhuan` | 自身增益；反弹见 buff `reflect_percent` |
| `skill_moli_dan` | `push 5` | 击退 5 格 |

载体单位 `wuxia_hero` 通过 `can_use_skill` 学会全部 8 个技能。

## 进阶

### 技能 burst 与单位 damage_seq 的区别

| 项目 | 技能 `effect burst` | 单位 `damage_seq` |
|------|----------------------|-------------------|
| 配置位置 | `class skill` 的 `effect` 行 | 单位 def 上的 `damage_seq` |
| 触发方式 | 手动或自动释放技能 | 普通攻击 / 远程攻击 |
| 伤害来源 | 技能或施法者 `mdg`/`rdg` + 战斗属性 | 单位 `mdg`/`rdg` 拆成多段 |
| 段数语法 | `burst mdg N (interval X)` | `damage_seq mdg N [(damage …)]` |
| 文档 | 本文 + `modding.htm` | `player/burst-attacks.htm` |

两者均走战斗管线，但配置入口与触发时机完全不同，请勿混用语法。

### 技能书与升级解锁

- `level_skills <等级> <技能> …`：升级自动学会
- 物品 `skills` + `learn_level`：背包使用技能书学会
- 详见 `modding.htm` 与 `relnotes.htm` §1.4.4.6

### 音效

技能 `style.txt`：`alert`（选中）、`ready`（前摇）、`triggered`（生效）。攻击触发 buff 见 buff 的 `triggered` / `noise loop`。

## 相关文档

- 单位自带治疗/伤害：`HEAL_HARM_自定义功能说明.md`（本文第二节）
- 战场 `class effect` 与 deploy：`EFFECT_BUFF_SYSTEM_说明.md`（本文第三节）
- 关键字大全：`modding.htm`
- 发布说明摘要：`relnotes.htm` §1.4.4.6
