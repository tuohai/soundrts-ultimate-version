# Heal和Harm自定义功能说明

## 概述
本次更新为SoundRTS游戏添加了heal和harm技能的自定义范围和时间控制功能，让玩家可以更精确地配置治疗和伤害技能的行为。

## 新增属性

### 治疗相关属性
- **heal_radius**: 治疗半径，在半径内的友军单位会被治疗，通常用于群体治疗
  - 默认值: 0 (不使用范围治疗)
  - 示例: `heal_radius 3` (3格范围) 或 `heal_radius 4.5` (4.5格范围)

- **heal_range**: 治疗射程，处于射程内的单位会被治疗，通常用于单体治疗，受伤单位必须被瞄准才能治疗
  - 默认值: 0 (不使用单体瞄准)
  - 示例: `heal_range 2.5` (2.5格射程的单体治疗) 或 `heal_range 1.8` (1.8格射程)

- **heal_cd**: 治疗冷却时间，控制治疗的频率
  - 默认值: 7.5 (秒)
  - 示例: `heal_cd 3.0` (每3秒治疗一次) 或 `heal_cd 1.5` (每1.5秒治疗一次)

- **heal_ready**: 治疗前摇时间，治疗开始前的准备时间
  - 默认值: 0 (无前摇)
  - 示例: `heal_ready 1.0` (1秒前摇时间) 或 `heal_ready 0.5` (0.5秒前摇时间)

### 伤害相关属性
- **harm_radius**: 伤害半径，在半径内的单位会被伤害，通常用于群体伤害
  - 默认值: 0 (不使用范围伤害)
  - 示例: `harm_radius 4` (4格范围) 或 `harm_radius 3.5` (3.5格范围)

- **harm_range**: 伤害射程，处于射程内的单位会被伤害，通常用于单体伤害，目标必须被瞄准才能伤害
  - 默认值: 0 (不使用单体瞄准)
  - 示例: `harm_range 2.5` (2.5格射程的单体伤害) 或 `harm_range 3.2` (3.2格射程)

- **harm_cd**: 伤害冷却时间，控制伤害的频率（类似攻击冷却）
  - 默认值: 0 (无冷却，持续伤害)
  - 示例: `harm_cd 2.0` (每2秒伤害一次) 或 `harm_cd 1.5` (每1.5秒伤害一次)

- **harm_ready**: 伤害前摇时间，伤害开始前的准备时间
  - 默认值: 0 (无前摇)
  - 示例: `harm_ready 0.5` (0.5秒前摇时间) 或 `harm_ready 1.2` (1.2秒前摇时间)

### 目标类型控制

- **heal_target_type**: 可治疗的目标类型，控制治疗技能能够治疗哪些单位类型
  - 默认值: () (空，可治疗任何友军单位，但不包括建筑)
  - 支持的类型: `unit`(单位), `ground`(地面单位), `air`(空中单位), `water`(水上单位), `healable`(可治疗单位), `undead`(不死单位), 具体单位类型名称
  - 注意: 不支持 `enemy`, `allied` 和 `building`，治疗只能针对友军单位，建筑需要repair修理
  - 示例: `heal_target_type ground` (只治疗地面单位) 或 `heal_target_type undead` (只治疗不死友军) 或 `heal_target_type footman archer` (只治疗步兵和弓箭手)

- **harm_target_type**: 可伤害的目标类型，控制伤害技能能够伤害哪些单位类型
  - 默认值: () (空，可伤害任何单位)
  - 支持的类型: `enemy`(敌人), `allied`(友军), `building`(建筑), `unit`(单位), `ground`(地面单位), `air`(空中单位), `water`(水上单位), `healable`(可治疗单位), `undead`(不死单位), 具体单位类型名称
  - 示例: `harm_target_type enemy` (只伤害敌人) 或 `harm_target_type undead` (只伤害不死单位) 或 `harm_target_type healable` (只伤害可治疗单位)

## 工作原理

### 治疗模式
1. **范围治疗模式**: 当`heal_range`为0时，使用`heal_radius`进行范围治疗，治疗半径内所有受伤的友军单位
2. **单体瞄准模式**: 当`heal_range`大于0时，自动寻找射程内最近的受伤友军单位进行单体治疗

### 伤害模式
1. **范围伤害模式**: 当`harm_range`为0时，使用`harm_radius`进行范围伤害，伤害半径内所有符合条件的单位
2. **单体瞄准模式**: 当`harm_range`大于0时，自动寻找射程内最近的敌方单位进行单体伤害

### 冷却和前摇机制
- **冷却时间**: 技能执行后需要等待冷却时间才能再次使用
- **前摇时间**: 技能开始前需要准备时间，可以模拟施法时间

## 使用示例

### 牧师（范围治疗）
```
def priest
    heal_level 5         ; 治疗强度
    heal_radius 3        ; 3格治疗半径
    heal_cd 3.0          ; 3秒冷却
    heal_ready 1.0       ; 1秒施法时间
```

### 军医（只治疗地面单位）
```
def medic
    heal_level 3         ; 治疗强度
    heal_radius 2        ; 2格治疗半径
    heal_cd 2.0          ; 2秒冷却
    heal_target_type ground ; 只能治疗地面单位（不能治疗空中的dragon）
```

### 死灵法师（单体伤害）
```
def necromancer
    harm_level 3         ; 伤害强度
    harm_range 2.5       ; 2.5格射程单体伤害
    harm_cd 2.0          ; 2秒冷却
    harm_ready 0.5       ; 0.5秒施法时间
    harm_target_type enemy ; 只伤害敌人
```

### 毒云（持续范围伤害）
```
def poison_cloud
    harm_level 4         ; 持续伤害
    harm_radius 4.0      ; 4格毒云范围
    harm_cd 1.0          ; 每秒伤害一次
```

### 防空塔（只伤害空中单位）
```
def antiair_tower
    harm_level 6         ; 对空伤害
    harm_radius 5        ; 5格射程
    harm_cd 1.5          ; 1.5秒冷却
    harm_target_type air ; 只伤害空中单位
```

### 地面医疗兵（只治疗地面单位）
```
def ground_medic
    heal_level 3         ; 治疗强度
    heal_radius 3        ; 3格治疗半径
    heal_cd 2.0          ; 2秒冷却
    heal_target_type ground ; 只治疗地面单位
```

### 不死族治疗师（只治疗不死友军）
```
def undead_healer
    heal_level 4         ; 治疗强度
    heal_radius 2.5      ; 2.5格治疗半径
    heal_cd 1.8          ; 1.8秒冷却
    heal_target_type undead ; 只治疗友方的zombie、skeleton等不死单位
```

### 驱邪师（只伤害不死单位）
```
def exorcist
    harm_level 10        ; 对不死单位高伤害
    harm_radius 4        ; 4格驱邪范围
    harm_cd 2.5          ; 2.5秒冷却
    harm_ready 1.0       ; 1秒施法时间
    harm_target_type undead ; 只伤害zombie、skeleton等不死单位
```

### 毒素发生器（只伤害可治疗单位）
```
def poison_generator
    harm_level 2         ; 毒素伤害
    harm_radius 3.5      ; 3.5格毒云范围
    harm_cd 1.0          ; 持续每秒伤害
    harm_target_type healable ; 只伤害可治疗单位（不伤害机械catapult等）
```

## 属性显示
在游戏的单位属性界面中，这些新属性会自动显示：
- 治疗半径、治疗射程、治疗冷却、治疗前摇
- 伤害半径、伤害射程、伤害冷却、伤害前摇

## 生命和法力回复冷却控制

除了治疗和伤害技能，现在还可以为生命回复（`hp_regen`）和法力回复（`mana_regen`）设置冷却时间和前摇时间：

### 生命回复相关属性
- **hp_regen_cd**: 生命回复冷却时间，控制生命回复的频率
  - 默认值: 0 (无冷却，持续回复)
  - 示例: `hp_regen_cd 2.0` (每2秒回复一次)

- **hp_regen_ready**: 生命回复前摇时间，回复开始前的准备时间
  - 默认值: 0 (无前摇)
  - 示例: `hp_regen_ready 0.5` (0.5秒前摇时间)

### 法力回复相关属性
- **mana_regen_cd**: 法力回复冷却时间，控制法力回复的频率
  - 默认值: 0 (无冷却，持续回复)
  - 示例: `mana_regen_cd 3.0` (每3秒回复一次)

- **mana_regen_ready**: 法力回复前摇时间，回复开始前的准备时间
  - 默认值: 0 (无前摇)
  - 示例: `mana_regen_ready 1.0` (1秒前摇时间)

### 使用示例

```
def battle_mage
    hp_max 500
    mana_max 300
    hp_regen 10         ; 每次回复10点生命
    hp_regen_cd 5.0     ; 每5秒回复一次
    hp_regen_ready 1.0  ; 1秒前摇
    mana_regen 20       ; 每次回复20点法力
    mana_regen_cd 3.0   ; 每3秒回复一次
```

## 兼容性
- 现有的`heal_level`和`harm_level`属性保持不变
- 如果不设置新属性，将使用默认值，保持向后兼容
- 现有的`harm_target_type`属性继续正常工作
- 原有的`hp_regen`和`mana_regen`行为不变（不设置冷却时持续回复）

## 技术细节
- **距离单位**: 使用格子数，支持小数（如 `2.5` 表示2.5格）
- **时间单位**: 使用秒，支持小数（如 `1.5` 表示1.5秒）
- 冷却时间和前摇时间独立跟踪
- 单体瞄准模式会自动选择最近的有效目标
- 内部自动转换：距离转为毫米，时间转为毫秒进行处理 