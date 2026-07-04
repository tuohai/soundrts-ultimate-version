水上铺桥（逐格桥段）
=====================

.. epigraph:: 面向 **mod 作者** 与地图设计者：工人可在河流 / 湖泊 / 海洋上**逐格**铺设可通行桥段。机制与 ``modding.htm`` 中的建筑工地、``building-land-terrain.htm`` 中的 ``big_bridge`` / ``ford`` 地形互补。

----

设计思路
--------

- **一格 = 一段桥段**，不是整张大地图只放「一座桥」；大片水域需要多格连续铺设。
- **施工阶段**有脚手架（``BuildingSite``）：工人可走上该格继续建造，但**未完工前不能当作桥梁偷渡**（不能搭脚手架就过河）。
- **完工后**该格应用 ``bridge_terrain`` 指定的地形（默认 ``bridge_deck``），与相邻陆地 / 已完工桥段连通，**所有玩家**的地面单位均可通行（中立地形，无阵营限制）。

内置示例：``wooden_bridge``（木桥桥段），需 ``lumbermill``，成本 5 金 10 木。

规则属性
--------

在 ``rules.txt`` 中为 ``class building`` 定义：

.. list-table::
   :header-rows: 1

   * - 属性
     - 说明
   * - ``is_buildable_on_water_only 1``
     - 只能建在**纯水路方格**（``is_water`` 且地图未赋 ``is_ground`` 的河流 / 湖 / 海等；不含地图自带的 ``ford`` / ``big_bridge``）
   * - ``bridge_terrain <地形名>``
     - 桥梁**完工后**将水格应用为该 ``class terrain``（须已在 rules 中定义，如 ``bridge_deck``）

完工地形 ``bridge_deck`` 示例（``res/rules.txt``）::

    def bridge_deck
    class terrain
    is_water 1
    is_ground 1
    is_dynamic 0

可建造桥段示例::

    def wooden_bridge
    class building
    cost 5 10
    hp_max 400
    time_cost 60
    is_buildable_on_water_only 1
    bridge_terrain bridge_deck
    requirements lumbermill

游戏内流程
----------

1. 选中工人，在**相邻陆地**对着目标水格下达建造（``wooden_bridge``）。
2. 脚手架放置于水格中心；该格临时 ``is_ground 1``，工人可寻路**走上脚手架**（海洋等 ``speed 0`` 水域在脚手架期间会恢复可移动速度）。
3. 工人在脚手架格内施工（与普通 ``buildingsite`` 相同，播报 **「木桥桥段 在建筑」**）。
4. 进度完成后格子上留下 ``wooden_bridge`` 建筑，并刷新 ``bridge_terrain``；该格变为可通行桥面，与对岸 / 相邻已完工桥段相连。

脚手架阶段的限制
----------------

- 仅与**放置时下令的那一侧岸格**有一条临时出口；**不能**脚手架格 ↔ 脚手架格直接互走（防止未完工偷渡）。
- 脚手架存在期间**不**开放全图桥梁通行；只有**完工**的 ``bridge_terrain`` 才同步 land↔water / 桥↔桥 出口。
- 水上 ``BuildingSite`` **不会**被淹死判定销毁（``is_a_building`` 豁免）。
- 施工锤声在**工地**播放（``buildingsite`` 的 ``noise_when_building``），不在工人身上。

播报与音效（``style.txt`` / ``tts.txt``）
------------------------------------------

与其它建筑工地一致：**不需要**在 ``style.txt`` 里单独定义「脚手架」样式；工地用 ``buildingsite`` 的 ``title 107 128``（「在建筑」）。

| TTS ID | 中文 | 用途 |
|--------|------|------|
| 153 | 桥梁 | 通用出口 ``bridge`` 等 |
| 4348 | 栈桥 | 地图编辑器 / 地图地形 ``big_bridge`` |
| 5108 | 木桥桥段 | 可建造单位 ``wooden_bridge``、施工工地名 |
| 5109 | 桥面 | 完工后格地形 ``bridge_deck``（进入已scout格时） |

**脚步声：** 脚手架阶段与完工后均使用 ``bridge_terrain`` 对应样式上的 ``ground``。默认 ``bridge_deck`` 继承 ``big_bridge`` 的 ``ground wood``，工人走上去为木地板脚步声。

**进入方格播报：** 施工中的水格仍报原水域（河 / 海）；**完工后**才额外报「桥面」。

界面：Tab 与通道
----------------

- ``wooden_bridge`` **不是**出口对象；在桥面格心按 **Tab** 可选中「木桥桥段」。
- 使用 ``select_target no_exit`` 的地图（如 td2）在**桥面 / 脚手架格**上仍可用 Tab 循环**通道出口**（东 / 西向桥连接）。
- 通道专用浏览见 ``select_passage``（若地图绑定了该键）。

Mod 作者：自定义铁桥等
----------------------

只需定义**桥段建筑** + **完工地形**，无需 ``bridge_scaffold`` 之类脚手架样式：

**rules.txt**::

    def iron_bridge_deck
    class terrain
    is_water 1
    is_ground 1

    def iron_bridge
    class building
    cost 8 15
    hp_max 600
    time_cost 90
    is_buildable_on_water_only 1
    bridge_terrain iron_bridge_deck
    requirements blacksmith

**style.txt**::

    def iron_bridge
    is_a building
    title 5xxx          ; 例如「铁桥桥段」，并在 tts.txt 登记

    def iron_bridge_deck
    is_a big_bridge     ; 继承通行音；或自行写 ground / noise
    title 5xxx          ; 例如「铁桥面」

脚手架脚步声会自动读 ``bridge_terrain``（``iron_bridge_deck``）的 ``ground``，工地播报仍为「铁桥桥段 在建筑」。

与地图自带 ``big_bridge`` 的区别
---------------------------------

| | 地图 ``terrain big_bridge`` | 玩家建造的 ``wooden_bridge`` |
|--|------------------------------|------------------------------|
| 放置 | 地图加载时固定 | 工人逐格施工 |
| 地形名 | ``big_bridge``（栈桥） | 完工后为 ``bridge_deck``（桥面） |
| 建筑 | 无 | 格上有 ``wooden_bridge`` 实体，可被打掉 |
| 打掉后 | — | 恢复纯水、移除动态出口 |

实现与测试
----------

- 核心逻辑：``soundrts/world_build_rules.py``（``refresh_scaffold_passage``、``refresh_bridge_terrain``、``finalize_new_building``）
- 施工订单：``soundrts/worldorders/movement.py``（水上同格建造、``BuildPhaseTwoOrder``）
- 客户端标题 / 脚步：``soundrts/clientgameentity/properties.py``、``audio.py``
- 测试：``soundrts/tests/test_bridge_terrain.py``

相关文档：``building-land-terrain.htm``（``ford`` / ``big_bridge`` 通行）、``modding.htm``（``buildingsite``、``can_repair`` 岸建）。
