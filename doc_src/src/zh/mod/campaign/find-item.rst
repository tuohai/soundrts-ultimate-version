# 找到物品即通关功能说明（has_item 触发器）

本功能让地图/战役作者可以设置一个目标：让玩家找到（拾取）某件物品，
一旦玩家持有该物品，目标即完成，从而实现 "找到某物品即通关" 的关卡设计。

核心是一个新的触发器条件 ``has_item``，用来判断当前玩家是否已把某类物品收入囊中。


----


1. 功能概述
-----------



.. list-table::
   :header-rows: 1

   * - 部分
     - 名称
     - 作用
   * - 单位字段
     - ``class item``
     - 把某个类型定义为"物品"，可被拥有 ``inventory_capacity`` 的单位拾取
   * - 默认指令
     - ``pickup``
     - 玩家右键地上的物品即可拾取，物品进入单位库存(inventory)
   * - 触发器条件
     - ``has_item``
     - 判断玩家是否已经持有指定物品（在任意存活单位的库存中）



判定流程：

.. code-block:: text

   地图上放置物品 (class item)
     -> 玩家移动单位过去，右键拾取 (pickup)
     -> 物品进入 unit.inventory
     -> 触发器条件 (has_item <类型>) 成立
     -> (objective_complete N) 完成目标
     -> 所有目标完成后自动 victory()（通关）



前提：物品不能设置 ``consume_on_pickup`` （拾取即消耗）。 默认值为 0（不消耗），

这样拾取后物品才会进入库存并被 ``has_item`` 检测到。若设为 1，物品在拾取时会被删除，

条件将永远无法成立。


----


2. 触发器条件 ``has_item``
--------------------------


用法：

.. code-block:: text

   (has_item <物品type_name> [数量])


- `<物品type_name>`：物品类型（如 ``lost_amulet``）。
- ````[数量]```：可选，需要持有的数量，默认 `1`。

判定方式：统计当前玩家所有存活单位库存中该类型物品的数量，达到所需数量即成立。

示例：

.. code-block:: text

   (has_item lost_amulet)      ; 玩家任意单位身上有至少 1 件 lost_amulet
   (has_item lost_amulet 2)    ; 需要持有至少 2 件


与相关条件的区别：


.. list-table::
   :header-rows: 1

   * - 条件
     - 检测对象
     - 用途
   * - ``has``
     - 玩家拥有的单位数量（`self.units`）
     - "造出/拥有 N 个某单位"
   * - ``has_item``
     - 玩家单位库存里的物品
     - "找到/拾取了某物品"
   * - ``has_brought_item``
     - 玩家单位携带物品到达某方格
     - "运送到达"（无需丢弃）
   * - ``npc_has_item``
     - 某个 NPC 库存或已收到记录里的物品
     - "把物品交给某 NPC"（可指定序号：``(npc_has_item b2 3 quest_npc item)``，见 [指定序号目标说明.md](指定序号目标说明.htm)）
   * - ``find``
     - 某方格上地面存在的物体（任意所属）
     - "某处出现某物体"；须丢弃；语法方格在前 ``(find c3 item)``
   * - ``remove_item``
     - 触发器动作：从库存销毁物品
     - 剧情自动上交（见 [携带物品与剧情交付说明.md](携带物品与剧情交付说明.htm)）




----


3. 定义任务物品
---------------


在 ``rules.txt`` （全局 ``res/rules.txt`` 或战役本地 ``res/single/\<战役\>/rules.txt``）中定义：

.. code-block:: text

   def lost_amulet
   class item


``class item`` + 默认设置即可被拾取、不阻挡移动、可长期存在于库存中。
本示例中已在 `res/single/The Legend of Raynor/rules.txt <../../../res/single/The Legend of Raynor/rules.txt>`_ 定义了 ``lost_amulet``。

确保用来拾取的单位有 ``inventory_capacity \> 0`` （如 ``peasant``、``footman`` 等自带库存容量）。


----


4. 在地图上放置物品
-------------------


物品的放置语法与其它地图物体一致：

.. code-block:: text

   lost_amulet c3          ; 在方格 c3 放 1 件
   lost_amulet 2 c3        ; 在 c3 放 2 件（数量在前）



----


5. 完整示例地图（The Legend of Raynor / 17.txt）
------------------------------------------------


示例地图见 `res/single/The Legend of Raynor/17.txt <../../../res/single/The Legend of Raynor/17.txt>`_，关键内容：

.. code-block:: text

   title 找到物品通关示例
   
   square_width 12
   nb_columns 3
   nb_lines 3
   
   west_east_paths a1 b1 a2 b2 a3 b3
   south_north_paths a1 a2 b1 b2 c1 c2
   
   nb_meadows_by_square 4
   nb_players_min 1
   nb_players_max 1
   
   ; 待寻找的任务物品，放在远离出生点的 c3
   lost_amulet c3
   
   ; 玩家起始：一个能携带物品的农民
   starting_squares a1
   starting_units peasant
   starting_resources 100 100
   
   ; 目标与触发器
   timer_coefficient 1
   trigger player1 (timer 0) (add_objective 1 "找到失落的护符")
   trigger player1 (has_item lost_amulet) (objective_complete 1)
   trigger all (no_unit_left) (defeat)


玩法：游戏开始时收到目标"找到失落的护符"；玩家操控农民从 ``a1`` 走到 ``c3``，
右键地上的护符将其拾取；护符进入库存后 ``(has_item lost_amulet)`` 成立，目标完成，
随后自动判定胜利、解锁下一章节（通关）。


该地图是 ``The Legend of Raynor`` 的第 17 章（``17.txt``），在战役菜单里需要先通关前面的章节

才会解锁；用于测试时可直接顺序游玩到此章。


----


6. 复合示例：第 20 关（携带 + 背包使用）
----------------------------------------


`res/single/The Legend of Raynor/20.txt <../../../res/single/The Legend of Raynor/20.txt>`_ 分三步：拾取秘宝 → 携带到 B2 祭坛 → 在背包中使用秘宝领取金币。

``mystery_treasure`` 在 ``rules.txt`` 中配置 ``use_square b2`` 与 ``resource_rewards 150 0``，
只能在 B2 祭坛从背包使用（回车），使用后消耗并发放金币。

关键触发器：

.. code-block:: text

   ; 目标2：携带秘宝到达 b2（无需丢弃）
   trigger player1 (has_brought_item b2 mystery_treasure)
       (do (cut_scene 7546) (add_units b2 1 treasure_opened_mark) (objective_complete 2))
   
   ; 目标3：已在祭坛、秘宝已从背包使用（不在身上且不在 b2 地面）
   trigger player1 (and (find b2 treasure_opened_mark) (not (has_item mystery_treasure))
       (not (find b2 mystery_treasure))) (objective_complete 3)



``find`` 一律方格在前、类型在后，嵌套在 ``not`` 里亦然：`(not (find b2 mystery_treasure))`。


----


7. 复合示例：第 22 关（丢弃 + 拾取金币）
----------------------------------------


`res/single/The Legend of Raynor/22.txt <../../../res/single/The Legend of Raynor/22.txt>`_ 分三步：拾取封印宝藏 → 在 B2 祭坛丢弃开箱 → 拾取地上全部金币。

任务物品为 ``sealed_treasure`` （无 ``use_square``、无 ``resource_rewards``），须丢弃到地面后由触发器处理。

关键触发器（每条 trigger 须写在一行内）：

.. code-block:: text

   ; 目标1
   trigger player1 (has_item sealed_treasure) (objective_complete 1)
   
   ; 目标2：在 b2 丢弃后开箱并生成金币
   trigger player1 (find b2 sealed_treasure) (do (cut_scene 7567) (remove_ground_item b2 sealed_treasure) (add_units b2 1 treasure_opened_mark) (add_units b2 10 gold_coin) (objective_complete 2))
   
   ; 目标3：b2 上金币已全部捡走
   trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin))) (objective_complete 3)


8. 复合示例：第 23 关（丢弃即交付）
-----------------------------------


`res/single/The Legend of Raynor/23.txt <../../../res/single/The Legend of Raynor/23.txt>`_ 演示最简 「带到某格丢弃 → 完成目标」 流程（无开箱、无捡金币）：

1. 拾取 ``war_supplies`` → 目标 1（``has_item``）
2. 在 c3 补给站方格上 丢弃 → 目标 2（``find c3 war_supplies``）

.. code-block:: text

   trigger player1 (has_item war_supplies) (objective_complete 1)
   trigger player1 (find c3 war_supplies) (do (cut_scene 7573) (remove_ground_item c3 war_supplies) (objective_complete 2))


与 ``has_brought_item`` （携带到达、无需丢弃）的区别：本关必须让物品出现在目标方格的地面上，因此用 ``find`` 检测丢弃后的状态。

第 20、22、23 关对比
~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 关卡
     - 任务物品
     - 到达方式
     - 完成条件
   * - 20
     - ``mystery_treasure``
     - 携带到 B2（``has_brought_item``）
     - 背包 ``use_square`` 使用，金币入账
   * - 22
     - ``sealed_treasure``
     - 携带到 B2 后丢弃
     - 开箱 + 拾取全部 ``gold_coin``
   * - 23
     - ``war_supplies``
     - 携带到 C3 后丢弃
     - ``find`` + ``remove_ground_item`` 即交付




----


9. 涉及的代码改动
-----------------


- 新增触发器条件 ``lang_has_item``，见
  `soundrts/worldplayerbase/triggers.py <../../../soundrts/worldplayerbase/triggers.py>`_ （位于 ``lang_npc_has_item`` 之后）。
  触发器关键字采用动态分发（``my_eval`` -> ``lang_\<关键字\>``），且地图解析阶段会自动接受
  任何已存在的 ``lang_*`` 方法，因此无需改动解析器即可使用 ``has_item``。
- 新增任务物品 ``lost_amulet``，见
  `res/single/The Legend of Raynor/rules.txt <../../../res/single/The Legend of Raynor/rules.txt>`_。
- 新增示例地图 `res/single/The Legend of Raynor/17.txt <../../../res/single/The Legend of Raynor/17.txt>`_。


----


10. 相关战役：第 24–25 章（拾取密信 + 交给首领）
------------------------------------------------


第 24、25 章需先从 ``b1`` 拾取 ``secret_letter`` （玩法同本章 ``has_item`` 拾取流程），再
到 加雷克营地（``c2``）交给 加雷克爵士（``npc_has_item``）。结盟与打内奸部分见
`战役密信与结盟说明 <战役密信与结盟说明.htm>`_。
