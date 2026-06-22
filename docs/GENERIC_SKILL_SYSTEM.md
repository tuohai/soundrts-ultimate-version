# 通用技能系统说明

本文面向 `rules.txt` / mod 作者，说明如何给单位配置主动技能，以及新技能效果如何走固定伤害或完整战斗系统。

## 基本结构

一个主动技能通常是 `class skill`：

```txt
def skill_example
class skill
effect harm_target mdg
mdg 6
effect_target ask
effect_range 2
time_cost 0
cooldown 8
mana_cost 0
```

把技能挂到单位上：

```txt
def hero
class soldier
can_use_skill skill_example
```

常用字段：

- `effect`：技能实际效果。
- `effect_target`：目标方式。`ask` 表示需要玩家选择目标；`self` 表示对自己释放。
- `effect_range`：施法距离，不是伤害半径，也不是攻击射程。
- `time_cost`：施法时间。
- `ready`：技能准备时间/前摇，准备结束后才执行效果。
- `cooldown`：技能冷却。
- `mana_cost`：法力消耗。
- `cost`：资源消耗。

技能名称不要依赖内部 id。应在 `ui/style.txt` 中写标题，并在对应 `ui/tts.txt` 中写文本：

```txt
; ui/style.txt
def skill_example
title 7752
alert 1328
triggered 1330

; ui-zh/tts.txt
7752 逐日剑法
```

这样命令菜单会读“逐日剑法”，不会读 `skill_example` 或 `effect` 的内部参数。
手动释放技能时播放 `alert`；自动触发时优先播放 `triggered`（未配置则回退 `alert`）。
自动触发可由技能上的 `auto_trigger` + `trigger_timing` 配置，或由单位上的旧列表字段
（`active_trigger_skills` 等）配置。

## 两类伤害技能

新技能系统支持两类伤害写法：固定 harm 和战斗系统 mdg/rdg。

### 固定 harm：绕过护甲

固定 harm 直接扣血，不走护甲、暴击、穿甲、溅射。

```txt
def skill_lipi
class skill
effect harm_target 60
effect_target ask
effect_range 2
```

```txt
def skill_heng_sao
class skill
effect harm_area 50 3
effect_target ask
effect_range 8
```

含义：

- `harm_target 60`：对单体造成 60 点固定伤害。
- `harm_area 50 3`：对目标点半径 3 内敌人造成 50 点固定伤害。

固定 harm 适合“真实伤害”“剧情伤害”“不受防御影响”的技能。

### 战斗系统：走 mdg/rdg 管线

战斗系统技能使用 `mdg` 或 `rdg` 作为伤害类型，伤害来自技能属性或施法者属性。

```txt
def skill_lipi_mdg
class skill
effect harm_target mdg
mdg 12
effect_target ask
effect_range 2
```

```txt
def skill_heng_sao_mdg
class skill
effect harm_area mdg 3
mdg 12
mdg_splash 6
mdg_radius 1.5
effect_target ask
effect_range 8
```

规则：

- `effect harm_target mdg`：对单体做一次近战伤害。
- `effect harm_area mdg 3`：目标点半径 3 内的敌人各吃一次近战伤害。
- `effect ... rdg`：改为远程伤害。
- 技能上写的非零战斗属性会覆盖施法者同名属性。
- 如果技能不写 `mdg` / `rdg`，就使用施法者自身的 `mdg` / `rdg`。

战斗系统会计算：

- 防御：`mdf` / `rdf`
- `*_vs`
- 暴击：`mdg_crit` / `rdg_crit`
- 穿甲：`mdg_piercing` / `rdg_piercing`
- 溅射：`mdg_splash` / `rdg_splash`
- debuffs
- 受击通知、反弹、击杀、经验等奖励逻辑

## burst：连击技能

`burst` 是单体连击，必须走 `mdg` 或 `rdg` 战斗系统。

```txt
effect burst mdg 5 (interval 0.2) (window 1)
```

这里的 `5` 是攻击次数，不是伤害。

伤害应写在独立属性里：

```txt
mdg 6
```

完整例子：

```txt
def skill_zhuiri_jianfa
class skill
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)
mdg 6
effect_target ask
effect_range 2
time_cost 0
cooldown 8
mana_cost 0
```

### interval 与 delays

`interval` 表示等间隔：

```txt
effect burst mdg 5 (interval 0.2) (window 1)
```

命中时间：

```txt
0.00, 0.20, 0.40, 0.60, 0.80
```

`delays` 表示每一击从技能开始算起的时间点：

```txt
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)
```

命中时间：

```txt
0.00, 0.55, 1.10, 1.40, 1.65
```

区别：

- `interval`：固定节拍，适合普通连击。
- `delays`：自定义节奏，适合招式感强的技能。
- `delays` 数量必须等于连击次数，且必须从小到大。
- `window` 是说明/技能窗口；不写时，`delays` 技能默认用最后一个 delay，`interval` 技能默认用 `(次数 - 1) * interval`。

## 范围参数不要混用

常见范围字段：

- `effect_range`：玩家能点多远，也就是施法距离。
- `effect_radius`：某些范围效果省略半径时的默认半径。
- `effect harm_area mdg 3` 里的 `3`：目标点周围的主命中半径。
- `mdg_range` / `rdg_range`：战斗系统攻击距离。技能上写时，会限制候选目标距离施法者的最大距离。
- `mdg_radius` / `rdg_radius`：溅射半径。

例子：

```txt
def skill_sweep
class skill
effect harm_area mdg 3
mdg 12
mdg_range 8
mdg_splash 6
mdg_radius 1.5
effect_range 8
```

含义：

- `effect_range 8`：施法者最多点 8 格远。
- `harm_area mdg 3`：目标点半径 3 内敌人吃主伤害。
- `mdg_range 8`：每个主伤害目标还必须离施法者不超过 8 格。
- `mdg_splash 6` + `mdg_radius 1.5`：主命中后，再按普通攻击溅射逻辑造成二次范围伤害。

## 内置效果

### buffs

给目标或自己加 buff：

```txt
def skill_douzhuan
class skill
effect buffs b_douzhuan
effect_target self
cooldown 20
mana_cost 40
```

### debuffs

给敌人加负面 buff：

```txt
def skill_poison
class skill
effect debuffs b_poison
effect_target ask
effect_range 6
```

### push

击退敌方单位：

```txt
def skill_moli_dan
class skill
effect push 5
effect_target ask
effect_range 6
cooldown 6
mana_cost 15
```

`push 5` 表示把目标从施法者方向推出 5 格左右，实际落点会找可站立位置。

### deploy

在目标格部署 `class effect`：

```txt
def skill_fire_zone
class skill
effect deploy 10 fire_zone
effect_target ask
effect_range 8
```

`deploy` 用于放置战场区域效果。被部署对象应该是 `class effect`，不要用 `summon` 的单位写法混用。

### summon

召唤单位：

```txt
def skill_summon_guard
class skill
effect summon 30 2 footman
effect_target ask
effect_range 6
```

含义：召唤 2 个 `footman`，持续 30 秒。

### 旧内置技能

这些旧效果仍可用：

- `teleportation`
- `recall`
- `conversion`
- `raise_dead`
- `resurrection`

## 反弹 buff

`reflect_percent` 写在 `class buff` 上，表示受伤后把实际伤害按比例反弹给攻击者。

```txt
def b_douzhuan
class buff
duration 8
temporary 1
reflect_percent 100
```

注意：

- `reflect_percent 100` 表示反弹 100% 实际伤害。
- 反弹伤害不会继续触发反弹链。
- 技能通常通过 `effect buffs b_douzhuan` 施加该 buff。

## 统一技能配置（1.4.4.6+）

推荐在 **技能本身** 上配置手动/自动行为，单位只需把技能放进 `can_use_skill`（或通过
`level_skills` / 技能书学会）：

```txt
def skill_zhuiri_jianfa
class skill
auto_trigger 1
manual_use 1
trigger_timing on_hit
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)
mdg 6
effect_target ask
cooldown 8
mana_cost 20
```

| 字段 | 说明 |
| --- | --- |
| `auto_trigger 1` | 允许自动触发 |
| `manual_use 1` | 允许手动释放（默认 1；设为 0 则仅自动触发） |
| `trigger_timing` | 自动触发时机，见下表 |

| `trigger_timing` | 含义 |
| --- | --- |
| `on_hit` | 普攻命中后附加 |
| `on_attack` | 出手时附加，普攻继续 |
| `on_attack_replace` | 替代本次普攻 |
| `on_damaged` | 受击时 |

学会的技能统一进入 `can_use_skill`；命令菜单只显示 `manual_use 1` 的技能。
仅自动触发、不需手动命令的技能可设 `manual_use 0`，仍须通过 `can_use_skill`、
`level_skills` 或技能书学会后才会参与自动触发。

## 自动触发技能（旧写法仍兼容）

以下单位列表字段仍有效，可与上面的 `auto_trigger` / `trigger_timing` 并存：

- `attack_trigger_skills`：发起普通攻击时触发，触发后普通攻击仍会继续。
- `attack_replace_skills`：发起普通攻击时触发，触发成功后跳过这次普通攻击。
- `active_trigger_skills`：普通攻击命中敌人后触发。
- `passive_trigger_skills`：被敌人打中后触发。

如果你要“命中后附加技能”，用 `trigger_timing on_hit` 或 `active_trigger_skills`。
如果你要“挥刀/开火前先触发技能”，用 `trigger_timing on_attack` 或 `attack_trigger_skills`。
如果你要“这次攻击直接变成技能攻击”，用 `trigger_timing on_attack_replace` 或 `attack_replace_skills`。

buff / debuff 也有同样的攻击发起触发点：

- `attack_trigger_buffs`：发起攻击时给自己加 buff，普通攻击继续。
- `attack_trigger_debuffs`：发起攻击时给目标加 debuff，普通攻击继续。
- `attack_replace_buffs`：发起攻击时给自己加 buff，触发成功后跳过这次普通攻击。
- `attack_replace_debuffs`：发起攻击时给目标加 debuff，触发成功后跳过这次普通攻击。

### 主动触发技能

命中后主动触发写在单位上：

```txt
def hero
class soldier
active_trigger_skills skill_flame_proc
```

技能仍然是普通 `class skill`：

```txt
def skill_flame_proc
class skill
effect harm_target mdg
mdg 4
effect_target ask
active_trigger_rate 30
cooldown 3
```

含义：

- `hero` 普通攻击命中敌方单位后，有 30% 几率触发 `skill_flame_proc`。
- 触发目标是刚被命中的敌人。
- 技能走已有 `execute_skill()`，因此可以使用 `harm_target`、`burst`、`buffs`、`push` 等效果。
- 如果技能在冷却或法力不足，则不会触发。

也可以按攻击类型分别设置：

```txt
mdg_trigger_rate 30
rdg_trigger_rate 10
```

若设置了 `mdg_trigger_rate` / `rdg_trigger_rate`，对应攻击类型优先使用它；否则使用 `active_trigger_rate`。

### 攻击发起时触发

攻击发起时触发，但普通攻击继续：

```txt
def hero
class soldier
attack_trigger_skills skill_before_hit

def skill_before_hit
class skill
effect buffs b_self_power
effect_target self
active_trigger_rate 100
cooldown 5
```

这适合“攻击前给自己加一层状态，然后这次普通攻击继续打出去”。

### 替代本次普通攻击

攻击发起时触发，技能触发成功后跳过这次普通攻击：

```txt
def hero
class soldier
attack_replace_skills skill_second_slash

def skill_second_slash
class skill
effect harm_target mdg
mdg 12
effect_target ask
active_trigger_rate 50
cooldown 2
```

这适合“本次攻击变成技能攻击，没有普通攻击”。如果要“第 2 下必定触发”，目前可以用冷却/触发率近似；若需要严格每第 N 下触发，需要另加攻击计数规则。

buff / debuff 版本：

```txt
def hero
class soldier
attack_trigger_buffs b_self_power
attack_trigger_debuffs b_mark
attack_replace_debuffs b_stun

def b_self_power
class buff
duration 3
temporary 1
stat mdg
v 2
mdg_trigger_rate 100

def b_mark
class buff
duration 5
temporary 1
negative 1
stat mdf
v 2
mdg_trigger_rate 30
```

说明：

- `attack_trigger_buffs` / `attack_replace_buffs` 作用于攻击者自己。
- `attack_trigger_debuffs` / `attack_replace_debuffs` 作用于当前攻击目标。
- 触发率使用 buff 上的 `mdg_trigger_rate` / `rdg_trigger_rate`。
- 如果没写触发率，显式列在这些字段里的 buff/debuff 默认按 100% 触发。

### 被动触发技能

被动触发技能写在单位上：

```txt
def hero
class soldier
passive_trigger_skills skill_counter
```

技能定义：

```txt
def skill_counter
class skill
effect harm_target mdg
mdg 5
effect_target ask
passive_trigger_rate 25
cooldown 4
```

含义：

- `hero` 被敌人打中且仍存活时，有 25% 几率触发 `skill_counter`。
- 默认目标是攻击者。
- 技能在冷却或法力不足时不会触发。

### 触发条件

自动触发技能支持血量条件：

```txt
trigger_condition hp < 30
passive_trigger_rate 100
```

或旧式阈值：

```txt
hp_threshold 30
```

这些条件以触发者自身为判断对象：

- 主动触发：判断攻击者。
- 被动触发：判断受击者。

### 注意

- 统一模型下，自动触发技能也须进入 `can_use_skill`（或通过 `level_skills` / 技能书学会）；
  `manual_use 0` 时不会出现在手动命令菜单，但仍可自动触发。
- 旧写法（单位列表字段）下，列表中的技能不必同时在 `can_use_skill` 中。
- 自动触发技能造成的伤害不会继续触发新的自动技能，避免递归连锁。
- 自动触发技能成功后会进入自身 `cooldown`，并扣除 `mana_cost`。
- 自动触发技能的音效优先使用技能自身 `triggered`；未配置时回退到 `alert`。
- 如果技能 `effect_target self`，触发目标会改成触发者自身，适合自动给自己加 buff。
- `attack_replace_skills` 只有技能执行成功时才替代普攻；若几率失败、冷却中或法力不足，普通攻击照常发出。
- 击杀当前攻击目标后，若攻击命令未取消，会自动选取当前格及相邻格内最近的下一个可攻击敌人继续攻击（与手动持续攻击行为一致）；附近无敌人时攻击命令正常结束。

## ready：技能准备时间

`ready` 是技能前摇，表示技能触发后等待一段时间再真正执行效果。

```txt
def skill_heavy_slash
class skill
effect harm_target mdg
mdg 20
effect_target ask
ready 0.5
cooldown 8
```

含义：技能开始后等待 0.5 秒，再造成伤害。

可在 `ui/style.txt` 为技能配置前摇开始音效：

```txt
def skill_heavy_slash
ready heavy_slash_ready
```

手动释放技能和自动触发技能都会在 `ready` 前摇开始时播放该音效；前摇结束后再执行技能效果。

`ready` 和其它时间字段的区别：

- `ready`：执行效果前的准备时间/前摇。
- `time_cost`：手动施法的施法时间，会走现有施法进度逻辑。
- `cooldown`：技能释放成功后的冷却。

自动触发技能也支持 `ready`：

```txt
def skill_auto_counter
class skill
effect harm_target mdg
mdg 8
effect_target ask
passive_trigger_rate 100
trigger_condition hp < 30
ready 0.3
cooldown 5
```

含义：被打后如果血量低于 30%，先等待 0.3 秒，再反击攻击者。

## 技能战斗参数

`class skill` 支持写单位战斗系统中的核心参数。释放 `burst` / `harm_target mdg` / `harm_area rdg` 等战斗技能时，技能上的非零/非空属性会覆盖施法者。

常用参数：

- `mdg` / `rdg`
- `mdg_vs` / `rdg_vs`
- `mdf` / `rdf`
- `mdg_range` / `rdg_range`
- `mdg_minimal_range` / `rdg_minimal_range`
- `mdg_splash` / `rdg_splash`
- `mdg_radius` / `rdg_radius`
- `mdg_splash_decay_min` / `rdg_splash_decay_min`
- `mdg_crit` / `rdg_crit`
- `mdg_crit_rate` / `rdg_crit_rate`
- `mdg_piercing` / `rdg_piercing`
- `mdg_piercing_rate` / `rdg_piercing_rate`
- `mdg_explode` / `rdg_explode`
- `debuffs`

示例：

```txt
def skill_armor_break
class skill
effect harm_target mdg
mdg 8
mdg_piercing 5
mdg_piercing_rate 100
effect_target ask
effect_range 2
```

## 目标类型与命令

技能作为命令显示时，通常写：

```txt
can_use_skill skill_name
```

`UseOrder` 会把技能作为 `use skill_name` 命令展示和执行。

目标规则：

- `effect_target self`：不需要目标。
- `effect_target ask`：需要目标。
- `burst` / `harm_target` / `push`：目标必须是单位。
- `harm_area` / `deploy` / `summon`：目标通常是格子或可定位对象。

如果技能需要读出友好的名称，必须配 `style.txt` 和 `tts.txt`。否则 UI 可能读内部 id 或效果参数。

## 示例：逐日剑法

雷诺传中的逐日剑法（手动 + 自动触发统一为同一技能）：

**单位（升级自动学会，可选）**::

```txt
def raynor
is_a knight
level_skills 10 skill_zhuiri_jianfa    ; 10 级自动解锁（可选）
learn_level_skills 10 skill_zhuiri_jianfa   ; 技能书学习门槛（可选，与物品 learn_level 取较高）
```

**技能**::

```txt
def skill_zhuiri_jianfa
class skill
auto_trigger 1
manual_use 1
trigger_timing on_hit          ; on_hit | on_attack | on_attack_replace | on_damaged
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)
mdg 6
effect_target ask
effect_range 2
time_cost 0
cooldown 8
mana_cost 20
```

**技能书（背包中使用）**::

```txt
def zhuiri_jianfa_book
class item
skills skill_zhuiri_jianfa
learn_level 10
transport_volume 1
```

地图触发器发放：``(add_inventory_item zhuiri_jianfa_book 1 raynor)``

**UI 与音效**::

```txt
; ui/style.txt
def skill_zhuiri_jianfa
title 7752
alert roar

def zhuiri_jianfa_book
title 7754
pickup 1506
use 1506          ; 背包中使用时的音效

; messages（style.txt 顶层）
skill_learned 已学会
skill_level_too_low 等级不足，无法学习该技能
skill_already_known 已经学会该技能

; ui-zh/tts.txt
7752 逐日剑法
7754 逐日剑法秘籍
```

注意：同一技能不要同时在 ``level_skills`` 与技能书上重复配置为同一等级自动获得，否则使用技能书时会提示已学会且不消耗书籍。

## 常见错误

### 把 burst 的次数当成伤害

错误理解：

```txt
effect burst mdg 6
```

这里的 `6` 是连击次数，不是伤害。

正确写法：

```txt
effect burst mdg 5
mdg 6
```

### 把 delays 当成间隔

`delays` 是每一击的绝对时间点，不是两击之间的间隔。

```txt
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65)
```

表示第 1 击在 0 秒，第 2 击在 0.55 秒，第 3 击在 1.10 秒。

### 没配 title

没有 `ui/style.txt` 标题时，命令菜单可能读内部 id 或效果细节。

### 混淆固定伤害与战斗伤害

固定伤害：

```txt
effect harm_target 60
```

战斗伤害：

```txt
effect harm_target mdg
mdg 60
```

前者绕过护甲，后者走完整战斗系统。

## 扩展开发接口

如果需要新增引擎级效果，可在 `Skill` 上添加：

```python
@classmethod
def _is_my_effect_necessary(cls, caster, target):
    return True

@classmethod
def _execute_my_effect(cls, caster, target, world):
    return True
```

然后在 rules 中使用：

```txt
effect my_effect ...
```

执行约定：

- 返回 `True` 表示技能成功，扣资源/法力并进入冷却。
- 返回 `False` 表示技能失败，命令会失败，不应进入冷却。
- 抛异常会记录 warning，并视为失败。

## 建议

- 普通招式优先使用 `burst` / `harm_target mdg` / `harm_area mdg`。
- 需要真实伤害时才用固定 `harm_target N` / `harm_area N R`。
- 有节奏的连击用 `delays`；普通连击用 `interval`。
- 技能伤害写在 `mdg` / `rdg` 属性里，不要塞进 `effect` 参数。
- 每个可见技能都配 `style.txt` 标题和对应语言 `tts.txt`。
