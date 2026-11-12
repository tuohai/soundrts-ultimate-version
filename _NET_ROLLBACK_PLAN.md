# 联机架构改造：锁步 → 主机权威 + 快照回滚

## 目标

把 SoundRTS 的多人联机从 **确定性锁步（lockstep）** 改为 **主机权威 + 客户端预测 + 快照回滚**，
解决"高延迟拖慢全体 / 一方不同步则整局崩"这两个硬伤。

## 现状（读码结论）

### 锁步数据流

```
客户端 Coordinator._dispatch_orders()          # worldclient.py
  ├─ com_turn 时把自己的 orders + digest + ping 上报服务器
  └─ 收 "all_orders" (fpct, all_orders) 后 _give_all_orders() 下发给自己

服务器 Game._dispatch_orders_if_needed()       # serverroom.py:438
  ├─ Orders.are_ready()  ← 所有人类玩家都上报了才继续
  ├─ _check_synchronization(check_strings)     # 比对 md5 digest
  └─ notify("all_orders", fpct, all_orders)    # 广播给所有玩家 + 旁观者

世界推进                                              # world/world_game.py:300
  └─ world.update() 每 VIRTUAL_TIME_INTERVAL=300ms 一次
```

**关键特性**：服务器**不模拟世界**。每个客户端各自跑完整模拟，靠"同一批 orders + 同一 seed"
保证结果一致，用 md5 digest 定期校验。

### 服务器权威的部分

- `seed`（开局随机种子）→ `serverroom.py:_start`
- `_initial_players_pack`（开局名册，含 alliance/faction）
- `fpct`（每通信回合的模拟帧数，按 ping 自适应）
- 合作战役难度百分比 `_coop_enemy_hp` / `_coop_enemy_damage`
- 订单的**聚合与广播顺序**

### 客户端权威的部分

- 全部世界模拟（`world.update()`）
- 单位位置/血量/AI 决策
- 全部 RNG 消耗（`world.random`）

---

## 实测数据（cw1-mm 100×100 = 131835 objects，148 单位，293 active）

### 帧成本

| 项目 | 数值 |
|---|---|
| `world.update()` 一帧 | **2.39 ms** |
| `world.update()` + 全量指纹扫描 | 2.83 ms |

### 快照成本（决定回滚是否可行）

| 策略 | cw1 | cw1-mm | 评价 |
|---|---|---|---|
| `cloudpickle.dumps(world)` | 29.7 ms | **492 ms** | 太慢 |
| `cloudpickle` 整个 game | 31 ms | 492 ms | 同上 |
| `cloudpickle` 热集（带 Player） | 28.7 ms | — | **失败**：Player 反向引用拖入整个 World |
| `copy.deepcopy(world)` | **失败** | **失败** | `World` 无 `players` 属性 → deepcopy 走不通 |
| `copy.deepcopy(world.objects)` | **失败** | **失败** | 同上 |
| `copy.deepcopy(active)`（不 pin memo） | **失败** | **失败** | 同上 |
| `copy.deepcopy(active)` + **pin back-refs** | **0.75 ms** | **15.2 ms** | 可行，但 cw1-mm 偏慢 |
| `dict(o.__dict__)` 浅拷贝 × 293 active | 0.20 ms | **0.40 ms** | 最快 |
| 全量 131835 对象 `dict(__dict__)` | — | **124 ms** | 太慢 |
| `world.random.getstate()` | 0.0096 ms | 同 | 忽略不计 |
| 2 个 Player 的 `dict(__dict__)` | 0.000 ms | 同 | 忽略不计 |

### 关键洞察：只 0.12% 的对象会变

```
30 帧内变化过的对象: 153 / 131835 (0.12%)
每帧变化对象数: 平均 120.8，最大 150
变化的对象类型: house(52) peasant(20) footman(10) knight(10) archer(10)
                catapult(10) dragon(10) mage(10) Square(3~5) 其他建筑各 2
```

**131835 个对象里 120156 个是 `meadow`（building land），永远不变。**
→ 快照只需覆盖 ~293 个热对象。

### 状态面

| 项 | 数值 |
|---|---|
| 单位的 `__dict__` attr 数 | 182 ~ 200 |
| 其中纯标量（int/float/bool/str/None） | **132 ~ 133（72~73%）** |
| 单位的非标量 attr | 50 个（`orders` / `action` / `place` / `player` / `inventory` / `_buffs` / 各种 `*_vs` dict / `neighbors` / `objects` …） |
| 热集内容器嵌套深度 | depth 0: 6300 attr，depth 1: 287 attr，**depth 2: 51 attr**（全是 `_obs_cache`） |
| Player 内容器嵌套深度 | depth 0: 89，depth 1: 95，depth 2: 13，**depth 3: 6** |

### 已验证的正确性基线

**现有存档/读档路径是逐位确定的**：

```
cw1:      dump 31ms / load 27ms → digest MATCH = True
cw1-mm:   dump 492ms / load 515ms → digest MATCH = True
读档后再跑 20 帧: digest 仍然相同 → DIVERGED = False
```

这证明：**引擎的模拟本身是确定性的，快照/恢复只要保真就能回滚。**
（现有 `world.get_digest()` 只覆盖 `random.getstate()`，不够用——
需要一个覆盖位置/血量/资源的强摘要用于回滚校验。）

### 已排除的方案

| 方案 | 为什么排除 |
|---|---|
| 服务器跑完整世界 + 客户端只渲染 | `clientgamegridview.py` 95KB 直接遍历 `world.squares` / `player.units`，纯状态同步要重写整个客户端层 |
| 每帧 pickle 快照 | 492 ms，远超 100 ms 卡顿预算 |
| 每帧全量 `dict(__dict__)` | 124 ms |
| `deepcopy(world)` | 直接失败 |

---

## 设计

### 架构：服务器权威 input stream + 客户端预测 + 回滚

```
   客户端 A                    服务器（权威仲裁，不模拟世界）
   ┌──────────┐               ┌────────────────────────────────────┐
   │ 预测帧    │  input(带seq) │ · authoritative frame counter        │
   │          │──────────────►│ · 按到达顺序编号 → frame N          │
   │          │               │ · 广播 confirmed input stream         │
   │ 收到权威  │◄──────────────│ · 检测落后客户端 → 要求其回滚        │
   │ input     │               └────────────────────────────────────┘
   │          │
   │ 若与预测不符 → 回滚到最近快照 → 重放
   └──────────┘
```

**服务器不模拟世界，但决定输入的权威顺序和帧号。**
客户端立即应用自己的输入（预测），收到权威输入后校正；不符则回滚重放。

### 快照设计（Phase 0，地基）

**分层快照**，而不是全量 pickle：

| 层 | 内容 | 成本 |
|---|---|---|
| L0 | `world.time` / `_next_id` / `random.getstate()` | 0.01 ms |
| L1 | Player 可变状态（资源/人口/升级/tech/flags…），排除可重算缓存 | ~0 ms |
| L2 | 热对象（units + active objects）的 `__dict__`，**其中容器做 1~2 层拷贝** | 0.4 ms |
| L3 | 结构变更记录：新建/删除的对象 id、`Square.objects` 成员变化、`_scheduled_events` | 视情况 |

**容器拷贝深度**需要 ≥3（Player 有 depth 3），但 depth ≥2 的只有 6 个 attr，
可以用"按需深拷贝"策略：浅拷贝所有容器，遇到 depth≥2 的再深拷贝。

**`_scheduled_events` 存的是闭包**（`world.schedule_after(delay, lambda: ...)`），
不可 pickle → 必须用**可序列化的替代表示**（记录 `(exec_time, callback_id)`，
或直接记录"重放该事件的效果"）。这是 Phase 0 的一个必须解决的问题。

### 组件

| 文件 | 职责 |
|---|---|
| `soundrts/net/__init__.py` | 包 |
| `soundrts/net/snapshot.py` | 分层快照 capture/restore + 强摘要 |
| `soundrts/net/rollback.py` | 快照环形缓冲 + 回滚 + 重放 |
| `soundrts/net/input_stream.py` | 权威 input stream：帧编号、去重、缺口检测 |
| `soundrts/serverroom.py` | 服务器侧：改用 input stream 广播 |
| `soundrts/worldclient.py` | 客户端侧：预测 + 校正 |

### 兼容策略

当前 `CLIENT_COMPATIBILITY = "15"`，服务器按 `client.version` 判兼容。
改造后需要新版本号；服务器要能同时服务新旧客户端——老客户端走锁步，
新客户端走回滚，**按版本分流到两种 Game 流程**。

---

## 阶段划分

### Phase 0：快照与回滚基础设施（纯本地，不动网络）★ 已完成

1. `snapshot.py`：分层快照 capture/restore + 强摘要 `strong_digest`
2. `rollback.py`：环形缓冲 + 回滚重放
3. 单元测试：**快照 → 继续模拟 N 帧 → 与不快照的分支逐位一致**

**这是整个改造的地基，也是最大的风险点。** 如果快照不保真，后面全白做。

已验证的失败模式：
- `copy.deepcopy` 浅层 restore **不精确**（RESTORE EXACT = False）——
  因为 `dict.update` 只恢复了 attr 值，没恢复被 mutate 的**容器内容**和结构变更
  （对象增删、`_next_id`、RNG 消耗）。

### Phase 1：服务器权威 input stream
4. 服务器改为广播"权威编号的 input"，而非"等所有人齐了再广播"
5. 客户端预测自己的 input

### Phase 2：客户端回滚校正
6. 检测预测错误 → 回滚 → 重放

### Phase 3：兼容性
7. 协议版本分离，新旧客户端各自走各自流程

### Phase 4：旁观者（spectator）
8. 服务器保存整局权威 input 历史，旁观者加入时一次性下发
9. 旁观者用 `SpectatorSession` 逐帧重放，**不做预测、不做回滚**
10. 追帧快进：`pending_frames() > catch_up_buffer` 时跳过实时节流

### Phase 5：健壮性（已完成的修补）
11. 会话**提前创建**（`Game._start_rollback_session`）：会话需要世界与玩家，
    二者在开局前都不存在；晚建会话会丢掉开局第一批 input。
12. 开局前的 input **缓冲**在 `Coordinator._pending_rollback_inputs`，不丢弃。
13. 玩家中途退出：该玩家未回答的帧由服务器**补空**并广播，
    否则整局会卡在那一帧（帧只有"人人回答"才算完整）。
14. 旁观者也接收**实时 input**：否则旁观者会停在它追上的那一帧。
15. 本地指令**竞态**：帧号在读取 input 与写入本地指令之间不能移动，
    否则本地指令会落到已模拟完的帧上被**静默丢弃**（`RLock` + 提前推进帧号）。

---

## 风险清单

| 风险 | 严重度 | 应对 |
|---|---|---|
| `_scheduled_events` 是闭包，不可序列化 | **高** | 改为可序列化事件表示，或回滚时按"取消并重放"处理 |
| 对象增删（建造/死亡/采石）改变 `world.objects` 与 `_next_id` | **高** | 快照 L3 层记录结构变更 |
| `meadow` 被消耗/重建（`recreate_building_land`）改 `Square.objects` | 中 | L3 层覆盖 |
| `Player` 的缓存字段（`_buckets` 等）被快照进去 | 中 | 排除 `PLAYER_CACHE_KEYS`（现成） |
| `hash(self.id)` 依赖 `PYTHONHASHSEED` | 中 | 回滚不改变 hash 行为，但要在测试中固定种子 |
| 回滚后 UI 仍持有旧对象引用 | 中 | 已验证：UI 用 **unit id** 索引（`interface.dobjets` / `interface.group` 存 id），不是对象引用 → 安全 |
| `Action.target` / `Order.target` 是对象引用 | 中 | 恢复时按 id 重新链接（现成 `restore_world_pickle_targets`） |
