# SoundRTS 1.4.4.7 发行说明

**版本**：1.4.4.7  
**类型**：英雄经验门槛公式 + 升级后经验清零  
**适用**：在 `rules.txt` 中配置英雄等级与经验的地图/模组作者

---

## 本次更新一览

1. **`xp_threshold_growth`**：用公式自动生成经验门槛，不必手写大量 `xp_thresholds`
2. **`level_up_reset_xp`**：可选在每次升级后将当前经验清零

---

## 经验门槛公式（`xp_threshold_growth`）

高等级英雄可写 `max_level` + 曲线公式，加载 `rules.txt` 时自动展开为 `xp_thresholds`：

```text
def long_hero
class soldier
max_level 100
xp_threshold_growth linear 100 50
hp_max_per_level 30
mdg_per_level 2
```

| 类型 | 写法 | 含义 |
| --- | --- | --- |
| 线性 | `linear BASE STEP` | 门槛 = `BASE + STEP × i`（i 从 0 起，加载时展开为累计列表） |
| 二次 | `quadratic BASE A B` | `BASE + A×i + B×i²`（如雷纳曲线 `quadratic 40 40 10`） |
| 多项式 | `polynomial c0 c1 c2 …` | 任意次数多项式 |
| 几何 | `geometric FIRST RATIO` | `FIRST × RATIO^i`（如 `1.08`） |

- 与手写 `xp_thresholds` 兼容；两者都有时以手写列表为准。
- 子 def 可 `is_a` 继承 `xp_threshold_growth`，只改 `max_level`。

---

## 升级后经验清零（`level_up_reset_xp`）

```text
def my_hero
class soldier
xp_thresholds 40 50
level_up_reset_xp 1
hp_max_per_level 30
```

| 值 | 行为 |
| --- | --- |
| `0`（默认） | 保留累计经验 |
| `1` | 每次战斗升级后 `xp = 0` |

开启 `level_up_reset_xp 1` 时，建议把 `xp_thresholds` 写成**每级所需**经验（如 `40 50` 表示 2 级要 40、3 级要 50），而不是累计总值（如 `40 90`）。

示例：升到 2 级后 Tab 显示「经验 0/50」（若阈值为 `40 50`）。

---

## 相关文档

- 模组说明：`doc/zh/modding.htm` 英雄章节（源文件 `doc_src/src/zh/modding.rst`）
- 1.4.4.6 英雄开局等级、升级回满等：`docs/zh/player/release-1.4.4.6.md`
