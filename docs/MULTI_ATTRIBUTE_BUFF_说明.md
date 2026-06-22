# 多属性Buff系统说明

## 概述

增强了 `worldbuff.py`，现在支持一个buff同时影响多个属性，同时保持向后兼容性。

## 新功能特性

### 1. 多属性支持
- `stat` 参数现在可以接受多个属性
- `v`、`dv`、`percentage` 参数可以为每个属性设置不同的值

### 2. 智能值匹配
- 如果属性数量多于值的数量，最后一个值会被重复使用
- 如果只有一个值，它会应用到所有属性上
- 如果值的数量多于属性数量，多余的值会被忽略

### 3. 全面直观数值设置 ⭐ **重大更新**
- **大部分属性现在都支持1=1的直观数值设置！**
- **设置v为1就是真正的1点，不再是1000！**
- **支持20+个常用属性的直观设置**
- 告别复杂的精度转换，全面1=1的直观体验

### 4. 向后兼容
- 原有的单属性buff写法完全保持不变
- 现有的buff定义无需修改

## 使用方法

### 规则文件中的定义格式

#### 基本语法
```
BuffName 1
    stat 属性1 属性2 属性3
    v 值1 值2 值3
    duration 持续时间
    temporary 1
```

#### 示例1：治疗增强buff（直观数值设置）⭐
```
HealEnhancementBuff 1
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1
```
效果：
- `heal_level` 增加 1 点治疗量（真正的1点，不是1000！）
- `heal_cd` 设置为 1.5秒冷却时间（1500毫秒）
- `heal_radius` 增加 6 点治疗范围

#### 示例2：使用相同值
```
AllRoundBuff 1
    stat hp_max mana_max speed
    v 100
    duration 600
    temporary 1
```
效果：所有三个属性都增加100点

#### 示例3：混合百分比和固定值
```
MixedBuff 1
    stat hp mana
    percentage 50 0
    v 0 100
    duration 300
    temporary 1
```
效果：
- `hp` 增加当前值的50%
- `mana` 增加固定100点

#### 示例4：持续效果
```
RegenerationBuff 1
    stat hp mana
    dv 10 5
    dt 1
    duration 600
    temporary 0
```
效果：
- 每秒恢复10点hp
- 每秒恢复5点mana

#### 示例5：向后兼容（原有格式）
```
OldStyleBuff 1
    stat hp
    v 200
    duration 300
    temporary 1
```
效果：hp增加200点（原有功能保持不变）

## 高级功能

### 1. 直观数值设置 ⭐ **重点推荐**

现在 `heal_level` 和 `harm_level` 支持1=1的直观设置！

#### 治疗buff示例
```
def SimpleHealBuff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    temporary 1
    duration 10
```
- ✅ `heal_level` 设置1 = 真正的1点治疗量
- ✅ `heal_cd` 设置1500 = 1.5秒冷却时间
- ✅ `heal_radius` 设置6 = 6点治疗范围

#### 伤害buff示例
```
SimpleHarmBuff 1
    stat harm_level harm_cd harm_radius
    v 2 -1000 4
    temporary 1
    duration 15
```
- ✅ `harm_level` 设置2 = 真正的2点伤害量
- ✅ `harm_cd` 设置-1000 = 减少1秒冷却时间
- ✅ `harm_radius` 设置4 = 4点伤害范围

#### 支持直观数值的属性列表（20+个）

##### 基础属性
- `hp`, `hp_max`, `mana`, `mana_max`, `speed`

##### 攻击防御属性  
- `mdg`, `rdg`, `mdf`, `rdf`

##### 治疗伤害等级
- `heal_level`, `harm_level`

##### 范围和射程属性
- `heal_radius`, `harm_radius`, `mdg_radius`, `rdg_radius`
- `heal_range`, `harm_range`, `mdg_range`, `rdg_range`

##### 攻击目标和其他属性
- `minimal_mdg`, `minimal_rdg`, `buff_radius`

##### 溅射相关属性
- `mdg_splash`, `rdg_splash`, `mdg_splash_decay_min`, `rdg_splash_decay_min`

#### 保持精度系统的属性（主要是时间类）
- **时间类**：`heal_cd`, `harm_cd`, `mdg_cd`, `rdg_cd`, `heal_ready`, `harm_ready`, `mdg_ready`, `rdg_ready`
- **回复类**：`hp_regen`, `mana_regen`
- **百分比类**：`mdg_cover`, `rdg_cover`, `mdg_dodge`, `rdg_dodge`
- **精度范围**：`mdg_minimal_range`, `rdg_minimal_range`

### 2. 触发式多属性buff
```
CombatStanceBuff 1
    stat mdg rdg mdg_cd rdg_cd
    v 30 25 -20 -15
    duration 100
    temporary 1
    is_active 1
    mdg_trigger_rate 80
    rdg_trigger_rate 70
```

### 3. Buff/Debuff 音效配置

触发瞬间音效和持续状态音效写在对应 buff/debuff 的 `ui/style.txt` 定义里：

```
def CombatStanceBuff
triggered stance_proc
noise loop stance_hum
```

- `triggered`：当该 buff 或 debuff 通过 `attack_trigger_buffs`、`attack_replace_buffs`、`attack_trigger_debuffs` 等触发应用时，额外播放一次。
- `noise loop <sound>`：buff/debuff 持续期间循环播放状态音效，持续时间结束并移除后自动停止。
- `noise repeat <interval> <sound...>`：buff/debuff 持续期间按间隔重复播放状态音效。
- `noise <sound>`：保持原有解析行为，不会自动当作循环音效。

命中音效可以在攻击者的 `ui/style.txt` 上用 `mdg_hit_vs` / `rdg_hit_vs` 针对目标身上的
buff/debuff 类型配置：

```
def swordsman
mdg_hit_vs b_absolute_defense iron_clang
```

这样攻击命中带有 `b_absolute_defense` 的目标时，会播放 `iron_clang`。这与针对单位类型的
`mdg_hit_vs footman ...` 使用同一套机制。

## 技术细节

### 值的匹配规则
1. **完全匹配**：属性数量 = 值数量，一一对应
2. **值不足**：用最后一个值填充缺失的位置
3. **单个值**：复制给所有属性
4. **值过多**：截断多余的值

### 示例
```python
# 情况1：完全匹配
stat = ["hp", "mana", "speed"]
v = [100, 50, 20]
# 结果：hp+100, mana+50, speed+20

# 情况2：值不足
stat = ["hp", "mana", "speed"]
v = [100, 50]
# 结果：hp+100, mana+50, speed+50 (用最后的50填充)

# 情况3：单个值
stat = ["hp", "mana", "speed"]
v = [100]
# 结果：hp+100, mana+100, speed+100 (单个值应用到所有)

# 情况4：值过多
stat = ["hp", "mana"]
v = [100, 50, 20, 30]
# 结果：hp+100, mana+50 (忽略多余的20和30)
```

### 特殊处理
- `drain_to` 功能只在第一个属性上生效，避免重复消耗
- 临时buff移除时，会正确恢复所有影响的属性
- 通知消息会显示所有受影响的属性和对应的变化值

## 注意事项

1. **属性验证**：所有stat中的属性都会被验证是否在允许列表中
2. **性能优化**：多属性处理进行了优化，不会显著影响性能
3. **错误处理**：对于无效的属性或值，会给出警告信息
4. **兼容性**：完全向后兼容，现有的单属性buff无需修改

## 实际应用场景

### 1. 职业技能
- 法师的元素掌握：同时提升多种魔法伤害
- 战士的战斗专精：同时提升攻击力和防御力
- 治疗师的医术精通：同时提升治疗效果、范围和速度

### 2. 装备效果
- 全属性装备：同时提升多个基础属性
- 专业装备：只提升特定领域的相关属性

### 3. 环境效果
- 祝福区域：提升多种正面属性
- 诅咒区域：降低多种属性

## 快速参考

### 🎯 用户最常用的配置

#### 治疗buff（直观设置）
```
def heal
class buff
stack 1
stat heal_level heal_cd heal_radius
v 1 1500 6          ← 1点治疗，1.5秒冷却，6点范围
temporary 1
duration 10
target_type self
```

#### 伤害buff（直观设置）
```
def harm
class buff  
stack 1
stat harm_level harm_cd harm_radius
v 2 -1000 4         ← 2点伤害，减少1秒冷却，4点范围
temporary 1
duration 15
target_type self
```

#### 混合属性buff（全直观数值）
```
def mixed
class buff
stack 1
stat hp mdg heal_level heal_radius speed
v 100 20 1 6 5      ← 全部直观：100血, 20攻击, 1治疗, 6半径, 5速度
temporary 1
duration 20
target_type self
```

#### 全能超级buff
```
def ultimate  
class buff
stack 1
stat hp hp_max mana mdg rdg mdf rdf speed heal_level harm_level
v 200 1000 100 30 35 20 25 15 3 4
temporary 1
duration 60
target_type self
```

### 📋 属性对照表

| 属性类型 | 示例属性 | 设置方式 | 说明 |
|---------|---------|---------|------|
| **直观数值** ⭐ | `hp`, `mdg`, `heal_level`, `heal_radius` | `v 100` = 100点 | 1=1的直观设置 |
| **时间类** | `heal_cd`, `harm_cd`, `mdg_cd` | `v 1500` = 1.5秒 | 以毫秒为单位 |
| **回复类** | `hp_regen`, `mana_regen` | `v 5` = 5点/秒 | 精度系统 |
| **百分比类** | `mdg_cover`, `rdg_dodge` | `v 50` = 50% | 精度系统 |

## 测试建议

建议使用以下示例来测试各种功能：
- `examples/all_direct_values_example.py` - **全属性直观数值设置** ⭐ **最新推荐**
- `examples/multi_attribute_buff_example.py` - 多属性基础功能
- `examples/direct_value_buff_example.py` - 治疗伤害直观数值设置
- `examples/heal_buff_example.py` - 治疗buff专项
- `examples/harm_buff_example.py` - 伤害buff专项 