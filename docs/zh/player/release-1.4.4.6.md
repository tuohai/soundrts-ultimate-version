# SoundRTS 1.4.4.6 发行说明

**版本**：1.4.4.6  
**类型**：模组音效命名整理 + 统一技能系统 + 通用技能效果 + 技能目标类型与 -tag 排除 + 升级属性成长 + 升级解锁技能 + 战役跨章携带 + 背包物品使用音效 + 前摇自定义音效 + 背包/装备栏热键 + 英雄开局等级与 0 级经验显示  
**适用**：地图/模组作者；自定义 `ui/style.txt` 的玩家

---

## 本次更新一览

1.4.4.6 包含九块内容：

1. 攻击音效字段从 `matk` / `ratk` 统一为 `mdg` / `rdg`
2. 技能与普通攻击前摇可配置独立音效
3. **统一技能系统**：同一技能可同时手动释放与自动触发
4. **通用技能效果**：连击、击退、范围伤害、召唤、部署等 `effect` 类型
5. **升级属性成长**：更多属性支持 `*_per_level` 随等级提升
6. **升级解锁技能**：`level_skills` 升到指定等级自动学会技能
7. **战役跨章携带**：英雄等级、经验与背包可带到下一章
8. **背包物品使用音效**：与拾取/丢弃相同的三级查找
9. **背包/装备栏热键**：`Shift+V` 循环切换，移除 `Ctrl+V`
10. **技能书**：背包使用技能书永久学会（与第 6 项配合）
11. **目标类型过滤**：技能 `harm_target_type`；全局 `-tag` 排除语法
12. **英雄开局等级与状态显示**：`level` / `level 0` / `xp`；Tab 始终播报等级
13. **升级回满**：`level_up_heal_full 1` 每次升级后生命与法力回满

---

## 攻击音效字段改名

`ui/style.txt` 推荐使用新字段：

| 旧字段 | 新字段 |
| --- | --- |
| `launch_matk` / `launch_ratk` | `launch_mdg` / `launch_rdg` |
| `matk_hit` / `ratk_hit` | `mdg_hit` / `rdg_hit` |
| `matk_hit_vs` / `ratk_hit_vs` | `mdg_hit_vs` / `rdg_hit_vs` |
| `matk_hit_lv_1` / `ratk_hit_lv_1` | `mdg_hit_lv_1` / `rdg_hit_lv_1` |
| `matk_missed` / `ratk_missed` | `mdg_missed` / `rdg_missed` |
| `matk_dodge` / `ratk_dodge` | `mdg_dodge` / `rdg_dodge` |
| `launch_charge_matk` / `launch_charge_ratk` | `launch_charge_mdg` / `launch_charge_rdg` |
| `charge_matk_hit` / `charge_ratk_hit` | `charge_mdg_hit` / `charge_rdg_hit` |

仓库内置的 `style.txt` 已全部迁移到新字段。引擎仍兼容旧字段。

---

## 前摇自定义音效

技能 `ready` 可在 `ui/style.txt` 中配置同名技能的 `ready` 音效。手动释放与自动触发技能都会在前摇开始时播放。

```text
def skill_heavy_slash
ready heavy_slash_ready
```

普通攻击前摇也支持独立音效：

```text
def footman
mdg_ready sword_prepare

def archer
rdg_ready bow_prepare
```

---

## 统一技能系统

同一 `class skill` 可同时 **手动释放** 与 **自动触发**，不再拆成两套列表。

**技能字段**：

| 字段 | 说明 |
| --- | --- |
| `auto_trigger 1` | 允许自动触发 |
| `manual_use 1` | 允许手动释放（默认 1） |
| `trigger_timing` | 自动触发时机 |

**`trigger_timing` 取值**：

| 值 | 含义 | 对应旧写法 |
| --- | --- | --- |
| `on_hit` | 普攻命中后 | `active_trigger_skills` |
| `on_attack` | 出手附加，普攻继续 | `attack_trigger_skills` |
| `on_attack_replace` | 替代本次普攻 | `attack_replace_skills` |
| `on_damaged` | 受击时 | `passive_trigger_skills` |

学会的技能统一进入 `can_use_skill`；命令菜单仅显示 `manual_use 1` 的技能。旧字段 `active_trigger_skills` 等仍兼容。

示例（逐日剑法：手动 + 命中后自动触发）：

```text
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

---

## 通用技能效果

`class skill` 通过 `effect` 字段定义技能行为。完整说明见 `GENERIC_SKILL_SYSTEM.md`。

### 伤害类

| 写法 | 说明 |
| --- | --- |
| `effect harm_target 60` | 单体固定 60 点真实伤害（绕过护甲） |
| `effect harm_area 50 3` | 目标点半径 3 内固定 50 点伤害 |
| `effect harm_target mdg` + `mdg 12` | 单体近战伤害，走完整战斗系统 |
| `effect harm_area mdg 3` + `mdg 12` | 范围近战伤害，支持溅射参数 |

战斗伤害会计算防御、`*_vs`、暴击、穿甲、溅射、debuff、经验等；技能上的 `mdg`/`rdg`/`mdg_crit` 等非零属性覆盖施法者。

### 连击（burst）

```text
effect burst mdg 5 (interval 0.2) (window 1)   ; 等间隔五连击
effect burst mdg 5 (delays 0 0.55 1.10 1.40 1.65) (window 2)   ; 自定义节奏
mdg 6
```

`burst` 后的数字是**命中次数**，不是伤害；伤害写在 `mdg` / `rdg`。

### 控制与其它效果

| `effect` | 示例 | 说明 |
| --- | --- | --- |
| `push` | `effect push 5` | 击退敌方单位 |
| `buffs` | `effect buffs b_power` | 给目标或自己加 buff |
| `debuffs` | `effect debuffs b_poison` | 给敌人加减益 |
| `deploy` | `effect deploy 10 fire_zone` | 在目标格部署 `class effect` 区域 |
| `summon` | `effect summon 30 2 footman` | 召唤 2 个步兵，持续 30 秒 |

旧内置效果仍可用：`teleportation`、`recall`、`conversion`、`raise_dead`、`resurrection`。

buff 可配置 `reflect_percent` 按比例反弹实际伤害（不触发反弹链）。

### 范围与触发

- `effect_range`：施法距离（能点多远）
- `effect harm_area mdg 3` 中的 `3`：主命中半径
- `mdg_range` / `rdg_range`：战斗系统攻击距离上限
- `mdg_splash` + `mdg_radius`：主命中后的二次溅射

自动触发除 `trigger_timing` 外，还支持 `active_trigger_rate`、`passive_trigger_rate`、`mdg_trigger_rate` / `rdg_trigger_rate`，以及 `trigger_condition hp < 30` 等血量条件。单位上的 `attack_trigger_buffs`、`attack_replace_debuffs` 等旧列表仍兼容。

### 目标类型过滤与 `-tag` 排除

`class skill` 可写 `harm_target_type`，作用于 `burst`、`harm_target`、`harm_area`、`push`。未配置时默认**仅对敌人**生效。

排除写法：标签前加 `-`，例如 `-building` 表示除建筑外均可。同样适用于：

| 字段 | 正向匹配 |
| --- | --- |
| `harm_target_type` | AND |
| `heal_target_type` | OR |
| `mdg_targets` / `rdg_targets` | OR |
| buff/debuff `target_type` | AND |

外交标签也支持排除：`harm_target_type -enemy` 等。

```text
def skill_heng_sao
class skill
effect harm_area 50 3
harm_target_type enemy ground unit -building

def priest
heal_target_type unit -undead

def archer
mdg_targets ground air -building

def b_holy
class buff
target_type unit -undead
```

---

## 升级属性成长（`*_per_level`）

在 `rules.txt` 中为单位配置 `<属性>_per_level`，每次升级累加对应数值。除生命、法力、复活时间外，还支持近战/远程伤害与护甲、射程、冷却、溅射、冲锋攻击、暴击率、治疗/伤害光环等大量战斗属性。

```text
def raynor
is_a footman
xp_thresholds 100 250 500 900
hp_max_per_level 30
mdg_per_level 2
mdf_per_level 1
charge_mdg_per_level 2
mdg_crit_rate_per_level 1
mana_max_per_level 10
```

- 升级时自动应用；默认 ``level_up_heal_full 0`` 时仅把 ``hp_max_per_level`` / ``mana_max_per_level`` 增量加到当前生命/法力；``level_up_heal_full 1`` 时每次升级**回满**生命与法力。
- 战役跨章恢复英雄时，会按存档等级补回全部累计成长。

### 开局等级与状态显示

在英雄 def 上可配置开局等级与经验（需同时定义 `xp_thresholds`）：

```text
def raynor
xp_thresholds 40 90 160 250 360 490 640 810 1000
hp_max_per_level 30
level 0          ; 从 0 级开始（默认不写 level 则为 1 级）
xp 0             ; 可选：开局累计经验
level 3          ; 或：直接 3 级开局（自动逐级应用 *_per_level）
```

| 字段 | 说明 |
| --- | --- |
| `level` | 开局等级，默认 `1`；`> 1` 时生成时补全累计成长 |
| `xp` | 开局累计经验（可选） |
| `level 0` | 从 0 级成长；Tab 状态显示「等级 0，经验 0/首个阈值」 |

定义了 `xp_thresholds` 的英雄在 Tab 状态中**始终播报等级**（含 1 级与 0 级），经验为「当前/下一级门槛」。

---

## 升级解锁与技能书

**升级自动解锁**（单位 `rules.txt`）：

```text
level_skills 10 skill_zhuiri_jianfa
learn_level_skills 10 skill_zhuiri_jianfa   ; 技能书学习的额外等级门槛
```

**技能书**（背包 Enter 使用，永久学会）：

```text
def zhuiri_jianfa_book
class item
skills skill_zhuiri_jianfa
learn_level 10
```

- 有 `learn_level` 时，拾取不会自动学会，必须背包使用。
- 成功使用后书籍从背包移除；已学技能不会被撤销。
- 已学会或等级不足：播放 `order_impossible` 对应消息，书籍保留。
- **勿**在同一技能上同时配置 `level_skills` 与技能书，否则使用时会 `skill_already_known` 且不消耗书籍。
- 升到 `level_skills` 指定等级时会语音提示新技能已学会。

---

## 战役跨章英雄携带

在英雄单位的 `rules.txt` 中启用跨章存档，通关后等级、经验与背包可带到下一章（仅单人战役）：

```text
def raynor
campaign_carryover 1
campaign_carryover_id raynor
campaign_carryover_stats 1
campaign_carryover_inventory 1
inventory_capacity 8
```

| 字段 | 说明 |
| --- | --- |
| `campaign_carryover` | `1` = 启用跨章存档 |
| `campaign_carryover_stats` | `1` = 保存/恢复等级与经验（默认开启） |
| `campaign_carryover_inventory` | `1` = 保存/恢复背包（默认开启） |

- 进度写入 `user/campaigns.ini`，**仅胜利**时更新；失败重打不覆盖。
- `campaign.txt` 可写 `hero_min_level 13:2 16:3 …` 设定进入某章后的最低等级。
- 只带等级：`campaign_carryover_inventory 0`；只带背包：`campaign_carryover_stats 0`。
- **合作战役**不持久化英雄；剧情信物仍用 `campaign_flag` / `add_inventory_item`。

---

## 背包物品使用音效

与拾取/丢弃相同的三级查找：

| 时机 | 物品 `style.txt` | 单位 `style.txt` | 全局默认 |
| --- | --- | --- | --- |
| 使用 | `use` / `on_use` | `use_<物品type>` | `item_used` |

```text
def zhuiri_jianfa_book
use 1506

def raynor
use_zhuiri_jianfa_book 1506

def thing
item_used 1194 1195 1196
```

- 服务端确认使用成功后才播放；不再在按 Enter 时提前朗读「已使用」。
- 技能书：使用音效 + 「技能名，已学会」；普通消耗品：「物品名，已使用」。

---

## 背包与装备栏热键

经典热键与分层热键均已统一：

| 按键 | 作用 |
| --- | --- |
| `Shift+V` | 在背包与装备栏之间循环切换 |
| `F3` | 分层方案下同 `Shift+V`（仍可用） |
| ~~`Ctrl+V`~~ | 已移除 |

- 首次按下：若背包非空则打开背包；在已打开的界面内再按可在两界面间切换。
- 须单独选中一个己方单位；与 `Alt+V` 属性界面互斥。
- 自定义热键覆盖见热键映射编辑器中的「切换背包与装备栏」。

---

## 升级说明

- 推荐把自定义 `style.txt` 中的 `matk` / `ratk` 改为 `mdg` / `rdg`。
- 新技能优先使用 `auto_trigger` / `manual_use` / `trigger_timing`；旧列表字段仍可工作。
- 技能书通过背包 `use_item` 学会，不要与 `level_skills` 重复配置同一技能。

---

## 相关文档

| 文档 | 内容 |
| --- | --- |
| `doc_src/src/zh/modding.rst` | 物品音效、技能书、统一技能、战役携带 |
| [战役跨章英雄携带说明.md](../developer/战役跨章英雄携带说明.md) | `campaign_carryover` 完整配置 |
| [背包与装备栏功能说明.md](背包与装备栏功能说明.md) | 界面操作与 `Shift+V` 切换 |
| `GENERIC_SKILL_SYSTEM.md` | 通用技能完整配置指南（burst/push/AOE/触发等） |
| [连发攻击与诸葛弩说明.md](连发攻击与诸葛弩说明.md) | `damage_seq` 每发 `launch_mdg` / `launch_rdg` |

---

## 测试建议

```bash
python -m pytest soundrts/tests/test_level_skills.py soundrts/tests/test_level_up_combat_stats.py soundrts/tests/test_campaign_hero.py soundrts/tests/test_wuxia_skills.py soundrts/tests/test_worldskill_deploy.py soundrts/tests/test_hit_vs_buff_sounds.py soundrts/tests/test_damage_seq_burst.py soundrts/tests/test_changelog_138x.py soundrts/tests/test_skill_trigger_sounds.py soundrts/tests/test_inventory_backpack.py -q
```
