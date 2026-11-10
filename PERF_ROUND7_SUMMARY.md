# 性能优化进展 — cw1 地图 / 15 个初级电脑

## 基准命令（老规矩）

```
python bench_headless.py --display --game-minutes 40 --wall-seconds 0 \
    --all-ai --nb-ai 15 --ai beginner --seed 42 \
    --report bench_headless_40min_round7_final.txt
```

## 40 分钟完整验证结果（最终）

| 阶段 | 墙钟 | 倍速 | World.update/tick | display drain/tick | 函数调用数 |
|---|---|---|---|---|---|
| 优化前（aura 之前） | 8768.7 s | 0.27x | 949.9 ms | — | — |
| aura 后基线 | 3075.3 s | 0.78x | 236.4 ms | 118.5 ms | 5,393,841,222 |
| Round 3 中途 | 2767.1 s | 0.87x | 241.7 ms | 81.2 ms | 5,753,990,012 |
| **Round 7 最终** | **2329.0 s** | **1.03x** | **193.0 ms** | **75.1 ms** | **4,367,899,841** |

**总加速：3075.3 s → 2329.0 s = 1.32x（相对 aura 后基线）**
**函数调用数：5.39B → 4.37B = −19%**

10 分钟快速迭代（seed 42，同一负载）：

| Round | 墙钟 | 倍速 | 函数调用数 |
|---|---|---|---|
| Round 2 | 310.6 s | 1.93x | 662.5 M |
| Round 3 | 305.0 s | 1.97x | 615.8 M |
| Round 4 | 289.3 s | 2.07x | 578.0 M |
| Round 5 | 286.4 s | 2.10x | 567.9 M |
| Round 6 | 283.2 s | 2.12x | 561.6 M |
| Round 7 | 283.4 s | 2.12x | 555.4 M |

## 本轮（Round 4–7）改动

### A* 寻路（`soundrts/worldroom.py`）
- **内联 blocked 检查**：原来是一个闭包 `_exit_blocked(node)`，40 分钟 profile 里
  **2.4 亿次调用 + 2.4 亿次 `getattr`**（19.9 s + 19.9 s 纯开销）。
  现在在 `_shortest_path_to` 的两个使用点直接内联：
  - 出口两侧都没有 blocker → 未被阻挡（地图上 ~5 万个出口，墙/门是极少数）
  - 否则回退到带缓存的完整 `is_blocked`
- **修正了一个语义 bug**：第一版内联时把"自己这一侧没有 blocker"直接当成
  "没被阻挡"，忽略了**对侧**有 blocker 的情况。这会让 AI 穿过被墙/门挡住
  的出口 —— `test_ai_res_jl1_attack_timing` 直接失败（"AI never reached the
  human base"）。已改为两侧都检查。
- `_ground_astar_exits_only` 的 `_blocked()` 同样加了"无 blocker → 直接返回
  False"的快路径。

### Entity 类级默认值（`soundrts/worldentity.py`）
新增类属性，让热路径可以用普通属性读取代 `getattr(obj, name, default)`：
- `resource_type = None`（Deposit / 资源 Creature 已有）
- `_formation_combat_spec = None`
- `expanded_is_a = ()`

对应改了这些热点的 `getattr`：
- `soundrts/clientgamegridview.py::_kind_from_model`（5.4M getattr）
- `soundrts/clientgamegridview.py::_color_from_model`
- `soundrts/worldunit/world_attributes.py::_speed_with_formation_cap`
- `soundrts/combat/damage_calculation.py::_with_formation_combat`
- `soundrts/world_formation.py::formation_combat_stats`
- `soundrts/worldplayerbase/base.py::check_type`
- `soundrts/worldunit/worldcreature.py::is_an_enemy`（`_allied_control_scanned`）
- `soundrts/worldplayerbase/base.py::__setattr__`（元组成员判断 → 直接字符串比较）

### 显示路径（`soundrts/clientgamegridview.py`）
- `map_icon_size_for`：记忆化从 3 层嵌套压成 2 层
  （`cell_px * 4 + kind_index -> crowd -> size`），省一次 dict 查找。
- `_paint_object`：内联 `_map_icon_size()` 这一层只有一行的包装函数
  （40 分钟 profile 里 4900 万次调用）。
- `display_objects`：内联 `_model_unplaced()`（570 万次调用）和
  `_kind_from_model()`（490 万次调用）。

## 踩过的坑（都是 duck-typed 测试桩暴露的）

1. **`orders[0].is_imperative` 直接属性读** — `test_world_hotpath_opt.py`
   的桩里 `orders = [object()]`，没有该属性。改成 `try/except AttributeError`，
   零成本 happy path。
2. **A* 内联漏了对侧 blocker** — 见上，语义 bug，被 AI 行为测试抓到。
3. **`_formation_combat_spec` 直接读** — `SkillCombatProxy` 通过 `__getattr__`
   代理到 `SimpleNamespace` 桩，没有该属性。改成 `try/except`。
4. **`world._allied_control_scanned` 直接读** — `_StubWorld` 没有该属性。
   改成 `try/except`。
5. **`o.type_name` / `o.expanded_is_a` 直接读** — `check_type` 会被鸭子类型的
   对象调用。改成 `try/except` + getattr 兜底。
6. **`getattr(p, "neutral", False)` 源码标记测试** —
   `test_joan_cathedral_visible.py` 断言源码里必须出现这个字符串，且必须
   在 `player_is_an_enemy(me)` 之前。恢复成原写法（这条路径每帧只跑
   15 次左右，冷路径，不值得优化）。

## 回归测试

`python -m pytest soundrts/tests/ -q` → **全绿**（12 skipped，0 failed）。

## 剩下的热点（40 分钟最终 profile）

```
425729  193.6s  worldroom.py:400(_shortest_path_to)      40.9M 次
40895859 111.5s  clientgamegridview.py:1114(_paint_object)
  7950  110.8s  clientgamegridview.py:1335(display_objects)
  73166   54.5s  worldroom.py:639(_ground_astar_exits_only)
  7950   47.8s  game_navigation.py:1214(update_fog_of_war)
84649187 42.9s  pygame.draw.circle
```

下一步的方向：
1. `_shortest_path_to` 本体（193 s tottime）是第一大项 —— A* 内层循环
   本身（`heappop`/`g_score.get`/`closed` 集合），需要考虑把整个 A* 搬到
   Cython（`worldroom_fast.pyx`）或 Numba。
2. `_paint_object` + `display_objects`（222 s）已经接近 pygame 原语的下限，
   剩下的是 Python 循环本身 —— 可以考虑在 Cython 里批处理。
3. `update_fog_of_war`（47.8 s）每 tick 重建 dobjets，是显示链的入口。
