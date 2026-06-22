# SoundRTS 1.4.4.5 发行说明

**版本**：1.4.4.5  
**类型**：随机地图玩法 + 占领规则 + AI 水域 + 结算修复 + 热键映射  
**适用**：随机地图与对战电脑玩家；地图/模组作者；使用作弊视角切换的测试者；需要自定义热键的玩家

---

## 本次更新一览

1.4.4.5 在随机地图上引入受 **《英雄无敌》** 与 **《文明 5》** 启发的兴趣点与多种胜利模式；完善 **夺取阈值为 100 时的默认占领命令**；电脑 AI 在含水地图上可 **跨水域采集与登陆作战**；**批量训练** 在人口不足时会按剩余人口自动训满；修复 **Ctrl+Shift+F4 切换视角** 导致的结算与成就漏洞；并新增完整的 **按键映射编辑器**（分层/经典方案、搜索、变体、别名键、导入导出）。

---

## 随机地图：英雄无敌与文明 5 风格玩法

经典 RTS 操作不变，新增的是 **地图目标、兴趣点（POI）与胜利条件**（非回合制或完整科技树）。

| 灵感 | 在 SoundRTS 中 |
| --- | --- |
| 英雄无敌：探索遗迹 | 单位进入方格 → **遗迹已发现** → 获得资源（`ancient_ruin`） |
| 英雄无敌：可占领据点 | 清守卫 → 占领 **可夺取兵营**，持续产兵（`captured_barracks`） |
| 英雄无敌：地图中央守军 | 菜单 **野怪强度** 控制中央敌对守军规模 |
| 文明 5：多种胜利 | **征服 / 经济 / 探索 / 生存** 四种 RMG 胜利模式 |
| 文明 5：全图探索 / 资源胜利 | 探索模式须发现全部遗迹；经济模式须累计采集达目标 |
| 文明 5：生存与时间 | 生存模式坚守至倒计时并保留主基地 |
| 文明 5：地图宝箱 | 可选 **宝箱** 菜单：对称额外矿点或可拾取物品 |

**如何开始**：主菜单 → 开始游戏 → **随机地图** → 配置模板与 **胜利模式** → 生成地图。联机需交换分享码（含胜利模式字段）。

完整说明见 [英雄无敌与文明5玩法说明.md](英雄无敌与文明5玩法说明.md) 与 [随机地图功能说明.md](随机地图功能说明.md)。

---

## 默认占领命令（`can_capture`）

当敌方单位或建筑的 **`capture_hp_threshold` 为 100** 时，表示 **接触即占领**（不造成伤害）。此时：

- 拥有 **`can_capture 1`**（默认）且具备攻击技能的单位，对这类目标 **默认下达占领命令**；到位即可占领成功。
- **`can_capture 0`** 的单位只会普通攻击/移动，不会默认走占领。
- **阈值低于 100**（如 30）时，仍须通过战斗将目标 HP 打到夺取阈值才能占领；**不适用**上述「默认占领」逻辑。

模组示例 — 步兵占领、弓箭手只打：

```
def footman
class soldier
can_capture 1

def archer
class soldier
can_capture 0
```

详见 [单位默认模式与自动状态配置说明.md](单位默认模式与自动状态配置说明.md) §5。

---

## AI 跨水域作战

含水地图上，电脑 AI 不再把对岸资源与敌人视为不可达：

- **两栖采集**：对岸仅有水上矿床时，用运输船摆渡工人采集。
- **两栖登陆**：调度运输船（及必要时空中运输）将地面部队送往对岸目标，参与进攻与扩张。
- **海军维护**：维持船坞与少量战舰，配合巡逻与渡河作战。

---

## 训练：人口不足时按剩余人口训满

一次训练多个单位时，若 **剩余人口** 不够训满整批，命令 **不会整单取消**，而是按当前可用人口 **尽可能多训**：

- 例：训练 5 个步兵，人口只剩 3 → 兵营 **只训练 3 个步兵**。
- 人口为 0 时仍会提示人口不足，与以前一致。
- 资源消耗与训练时间按 **实际训练数量** 计算。

---

## 修复：切换视角（Ctrl+Shift+F4）与结算

单人/训练等 **允许作弊模式** 的对局中，`Ctrl+Shift+F4` 可切换观察视角。此前存在漏洞：快输时切到 AI，AI 获胜后仍按 AI 的胜负发放 **分数、成就、奖章与卡牌**；或切到 AI 后由 NPC 打掉 AI，玩家被动成为最后存活者仍算胜利。

**现行为**：

- 局初 **固定计分玩家** 为开局真人；切换视角只改变观察与操作绑定，不改变计分归属。
- 切视角后，**首次** 被击败的计分对手（如 NPC 刚消灭你正在观察的 AI）**不计入** 你的胜利与击败分。
- 你在切视角 **之前** 已亲手击败的计分对手，切到 AI 旁观后 **仍算你的胜利**（正常结算）。
- 切视角后 AI 获胜、或被动「捡漏」胜利 → 按 **你的失败** 结算，不发胜利成就/奖章/卡牌。

---

## 按键映射编辑器

主菜单 **选项 → 按键映射**（与「热键方案」同级），语音驱动改键，无需编辑文本文件。

### 入口与存储

| 项目 | 说明 |
| --- | --- |
| 热键方案 | **分层热键**（8 个界面层）或 **经典热键**（约 179 项，覆盖全部 legacy 主绑定） |
| 保存位置 | 按 **当前 mod** 独立保存：`user/hotkey_overrides/{mod_key}.json` |
| 生效时机 | **下次开局**；按功能 ID 替换旧键，避免手写 `bindings.txt` 时旧键仍有效 |
| 方案开关 | 同一 JSON 内 `layered_hotkeys`：`1` 分层 / `0` 经典 |

### 功能一览

- **主 catalog**：逐项查看当前键、回车改键；冲突时播报占用者并确认替换
- **搜索热键**：中英文关键词过滤（classic 长列表尤其有用）
- **高级变体**：Shift/Ctrl 修饰命令、五格移动等不在主列表中的 binding
- **别名键**：同一功能的备用键独立映射（如 LCTRL/RCTRL、RETURN/KP_ENTER）
- **导出/导入**：JSON 写入剪贴板；支持合并或整包替换
- **多语言标签**：catalog 功能名走 TTS（5500–5684）；编组 1–5 为选中比例，6–9 为控制编组

### 标签修正

| 默认键 | 功能 | 映射菜单播报 |
| --- | --- | --- |
| Alt+Space | 第一人称（`immersion`） | **第一人称模式** |
| Ctrl+F2 | 画面开关（`fullscreen`） | **画面开关** |

说明见 [分层热键方案说明.md](分层热键方案说明.md)；开发者架构见 [hotkey-mapping-editor.md](../developer/hotkey-mapping-editor.md)。

---

## 模组与地图作者

| 主题 | 参考 |
| --- | --- |
| RMG 胜利模式与 POI | `soundrts/randommap.py`、`res/rules.txt`（`ancient_ruin`、`captured_barracks`） |
| `can_capture` / `capture_hp_threshold` | `doc_src/src/zh/modding.rst`（占领与默认占领命令） |
| AI 水域 | `soundrts/worldplayercomputer_water.py`、`worldplayercomputer.py` |

---

## 升级说明

- 覆盖安装即可，无需存档迁移。
- 未修改 `rules.txt` 的模组：`can_capture` 默认为 `1`，行为与以前一致。
- 战役、合作战役、多真人对战：**仍不参与** 成就/奖章/卡牌与结算评分（与 1.4.4.4 相同）；切换视角在多真人对战中本即不可用。

---

## 相关文档

| 文档 | 内容 |
| --- | --- |
| [英雄无敌与文明5玩法说明.md](英雄无敌与文明5玩法说明.md) | RMG 四种胜利、遗迹/兵营/野怪/宝箱（玩家） |
| [随机地图功能说明.md](随机地图功能说明.md) | 菜单、种子、分享码 |
| [单位默认模式与自动状态配置说明.md](单位默认模式与自动状态配置说明.md) | `can_capture` |
| [achievements.md](achievements.md) | 成就与军械库（1.4.4.4 起） |
| [分层热键方案说明.md](分层热键方案说明.md) | 分层/经典热键与游戏内映射 |
| [hotkey-mapping-editor.md](../developer/hotkey-mapping-editor.md) | 按键映射编辑器（开发者） |
| `doc_src/src/zh/relnotes.rst` | 完整版本历史 |

---

## 测试建议

```bash
python -m pytest soundrts/tests/test_randommap.py soundrts/tests/test_capture_default_order.py soundrts/tests/test_change_player_scoring.py soundrts/tests/test_train_population.py soundrts/tests/test_worldplayercomputer_water.py soundrts/tests/test_ai_naval_m3.py soundrts/tests/test_hotkey_editor.py soundrts/tests/test_hotkey_editor_phase2.py soundrts/tests/test_hotkey_editor_phase3.py soundrts/tests/test_hotkey_editor_phase4.py soundrts/tests/test_hotkey_editor_phase5.py soundrts/tests/test_hotkey_catalog_tts.py -q
```

1. 随机地图：分别试 **征服 / 经济 / 探索 / 生存**，进入遗迹格、占领兵营。
2. 含水地图对战电脑：观察 AI 是否摆渡工人或登陆进攻。
3. `capture_hp_threshold 100` 目标：步兵默认占领，弓箭手（`can_capture 0`）默认攻击。
4. 人口将满时批量训练：确认只训剩余人口能容纳的数量。
5. 训练局：`Ctrl+Shift+F4` 切 AI 后确认不能蹭 AI/NPC 结果的胜利奖励。
6. **选项 → 按键映射**：试搜索、改主键、改别名键（如 KP_ENTER）、导出/导入 JSON。
