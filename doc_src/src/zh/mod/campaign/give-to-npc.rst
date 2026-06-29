给 NPC 物品功能说明（give 指令 + npc_has_item 触发器）
======================================================


本功能让玩家可以把携带的物品交给另一个单位（尤其是中立/NPC 单位），并提供一个
触发器条件用来判断"某 NPC 是否已收到某物品"。配合战役/地图的目标系统，可以实现诸如
"把某件物品交给某 NPC 才能通关" 的关卡设计。


----


1. 功能概述
-----------


整套功能由这些部分组成：


.. list-table::
   :header-rows: 1

   * - 部分
     - 名称
     - 作用
   * - 指令
     - ``give``
     - 把携带的物品交给指定单位（含中立 NPC、盟友、敌人）
   * - 单位字段
     - ``receive_items``
     - 总开关：该单位是否接收别人交给的物品（1接收/0不接收，默认0）
   * - 单位字段
     - ``accepted_items``
     - 物品白名单：只接收这些物品类型（支持 is_a 继承）；空=接收任意
   * - 单位字段
     - ``accept_from``
     - 关系白名单：只接收来自这些关系的给予者（self/ally/neutral/enemy）；空=不限
   * - 触发器条件
     - ``npc_has_item``
     - 判断某个单位是否已经获得了指定物品



物品交付后：

- 物品从给予者的库存移除，放入目标单位的库存；
- 目标单位身上会记录一个 ``received_items`` 集合（已收到的物品类型），供触发器查询；
- 给予者和接收者都会播放对应音效/读屏提示。


前提：目标单位必须允许接收物品（``receive_items 1``）。默认情况下所有单位都

不接收（``receive_items 0``），所以要作为交付目标的 NPC 必须在 ``rules.txt`` 里显式

配置 ``receive_items 1``，否则交付会被拒绝。详见第 5 节。


----


2. 玩家操作方式
---------------


前提：单位要能携带物品（即该单位在 ``rules.txt`` 里有 ``inventory_capacity`` 且大于 0，
例如 ``peasant``、``footman`` 等），并且库存里确实有物品（先用 ``pickup`` 拾取）。

有三种触发"交给"的方式：

1. 右键默认操作：携带物品时，右键点击一个非敌对单位（中立 NPC、盟友单位），
   系统会自动选择"交给"，单位会走过去把（库存里的第一件）物品交给对方。
2. 指令菜单：在单位的指令列表中选择"交给"（标题：交给）。
3. 快捷键：``g`` （在 ``res/ui/style.txt`` 中配置）。


说明：右键默认操作只在"携带物品 + 目标是非敌对单位（且不是建筑）"时才会变成"交给"，

不会影响原有的运输（load/enter）、采集、修理、攻击等右键行为。


----


3. 地图作者：``give`` 指令语法
------------------------------


``give`` 也可以在触发器的 ``order`` 动作里发给单位（脚本化交付），语法：

.. code-block:: text

   give <目标单位id>            ; 把库存里的第一件物品交给目标
   give <目标单位id> <物品>     ; 把指定物品交给目标（<物品>可为物品 type_name 或物品 id）


- `<目标单位id>`：目标单位的引用。
- `<物品>`（可选）：当给予者携带多件物品时，用来指定交出哪一件；可写物品的
  ``type_name`` （如 ``health_potion``）或物品的 id。不写则默认交出库存第一件。


----


4. 触发器条件：``npc_has_item``
-------------------------------


用于在触发器的条件部分判断"某 NPC 是否已获得指定物品"：

.. code-block:: text

   (npc_has_item <NPC选择符> <物品type_name> [所在方格])
   (npc_has_item <方格> <序号> <单位类型> <物品type_name>)


- 经典写法
- `<NPC选择符>`：目标单位的 ``type_name`` （如 ``footman``、``oldman``）或单位 id。
- `<物品type_name>`：物品类型，如 ``health_potion``。
- ````[所在方格]``` （可选）：限定 NPC 当前所在方格（如 ``c3``、`"5,7"`），用于多个同名 NPC 时区分。
- 序号写法（与 ``transfer_units`` 相同）：指定该格刷出的第 N 个 `<单位类型>`；按刷出顺序编号，移动后仍有效。详见 `指定序号目标说明.md <指定序号目标说明.htm>`_。示例：The Legend of Raynor 第 28 章 `(npc_has_item b2 3 quest_npc short_sword)`。

判定逻辑：遍历世界中所有玩家（含已出局玩家）的单位，找到匹配目标的单位，
若其 ``received_items`` 含有该物品类型，或其当前库存里仍持有该类型物品，则条件成立。

与其它物品任务触发器的区别见 `寻找物品通关说明 <寻找物品通关说明.htm>`_ 对比表。
若需「携带到达某格 + 过场后物品自动消失」（无需实体 NPC），请用 ``has_brought_item`` +
``remove_item``，详见 `携带物品与剧情交付说明 <携带物品与剧情交付说明.htm>`_。


----


5. 单位字段：精细控制谁接收什么物品
-----------------------------------


在 ``rules.txt`` 的单位定义里，用以下三个字段精确控制"接收"行为。判定时三者依次校验，
全部通过才接收：


.. list-table::
   :header-rows: 1

   * - 字段
     - 取值
     - 说明
   * - ``receive_items``
     - ``1`` / `0`
     - 总开关；默认 ``0`` （不接收）
   * - ``accepted_items``
     - 物品 type_name 列表
     - 物品白名单；留空 = 接收任意物品；支持 ``is_a`` 继承
   * - ``accept_from``
     - ``self``/``ally``/``neutral``/``enemy`` 列表
     - 给予者关系白名单；留空 = 不限关系
   * - ``accept_givers``
     - 单位 type_name 列表
     - 给予者单位类型白名单；留空 = 不限单位；支持 ``is_a`` 继承



关系（``accept_from``）的判定
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


关系是"接收者相对于给予者"的关系，交付时实时计算，优先级 self > ally > neutral > enemy：

- ``self``：给予者和接收者属于同一玩家；
- ``ally``：接收者在给予者的盟友列表中（已结盟的中立按盟友处理）；
- ``neutral``：接收者属于中立玩家（`computer_only ... neutral`）且未与给予者结盟；
- ``enemy``：其余情况（非中立、未结盟的敌对方）。


注意：配置了 ``accept_from enemy`` 后，玩家携带对应物品右键敌方该单位会变成"交给"

而非"攻击"（仅对该物品 + 该单位类型生效，不影响其他战斗单位的正常攻击）。

三个示例
~~~~~~~~


1) 只有盟友的骑士接收骑士枪，其他物品都不接收：

.. code-block:: text

   def knight
   ...
   receive_items 1
   accepted_items knight_lance
   accept_from ally


2) 只有中立 NPC 的农民接收镐头，其他物品都不接收：

.. code-block:: text

   def quest_peasant
   class worker
   ...
   inventory_capacity 3
   receive_items 1
   accepted_items pickaxe
   accept_from neutral


3) 只有敌对（非中立）首领接收密信，且只收农民交来的信：

仓库内实际类型名为 ``npc_knight_leader`` （见 ``res/single/The Legend of Raynor/rules.txt``）：

.. code-block:: text

   def npc_knight_leader
   class soldier
   ...
   receive_items 1
   accepted_items secret_letter
   accept_from enemy
   accept_givers peasant
   ai_mode guard


骑士背着密信右键首领会显示「命令不可能」；须用农民（或 ``accept_givers`` 里列出的类型）交付。


第 24–25 章完整流程（交信 → 结盟 → 打内奸）见 `战役密信与结盟说明.md <战役密信与结盟说明.htm>`_。

组合规则速查
~~~~~~~~~~~~


- ``receive_items 1``，不写 ``accepted_items`` / ``accept_from``：接收任意人交来的任意物品。
- ``accepted_items potion`` （不写 ``accept_from``）：接收任意人交来的所有"药水类"物品（is_a potion）。
- ``accept_from ally neutral``：可写多个关系，任一匹配即可。
- ``accept_givers footman knight``：只接收这两种单位（及 ``is_a`` 它们的子类型）交来的物品。
- ``receive_items 0`` （或不写）：该单位完全拒绝接收，右键它也不会出现"交给"。


仓库内置示例接收型 NPC：``quest_npc`` （``res/rules.txt``，``receive_items 1`` +

``inventory_capacity 5``，未限制物品/关系），可直接用作"接收任意物品"的交付目标。

这样地图/Mod 作者可以精确控制：哪种单位（放在哪个单位定义上）、对哪种关系的给予者、
接收哪些物品，从而实现"只有盟友的骑士收骑士枪""只有敌方首领收密信"等剧情设定。


----


6. 完整示例
-----------


下面是一张可直接试玩的示例地图（已随仓库提供：``res/multi/give_demo.txt``）：

.. code-block:: text

   ; 玩法：用农民拾取 a1 的生命药水，走到 c3 的中立 quest_npc 旁右键它即可"交给"，
   ;       NPC 一旦收到药水即完成目标、获得胜利。
   
   title 交给NPC物品示例
   
   square_width 12
   nb_columns 3
   nb_lines 3
   
   west_east_paths a1 b1 a2 b2 a3 b3
   south_north_paths a1 a2 b1 b2 c1 c2
   
   nb_meadows_by_square 4
   nb_players_min 1
   nb_players_max 1
   
   ; 一件可被拾取的物品
   health_potion a1
   
   ; 玩家起始：一个能携带物品的农民
   starting_squares a1
   starting_units peasant
   starting_resources 100 100
   
   ; 中立NPC（quest_npc 已配置 receive_items 1），作为交付目标
   computer_only 0 0 neutral c3 quest_npc
   
   ; 目标与触发器
   timer_coefficient 1
   trigger player1 (timer 0) (add_objective 1 "deliver the health potion to the quest npc")
   trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)


要点：

- ``computer_only 0 0 neutral c3 quest_npc``：在 c3 放一个中立且可接收物品的 NPC。
- `add_objective 1 "..."`：添加 1 号目标，描述可用引号包裹的文本，也可用 tts 声音 ID。
- ``npc_has_item quest_npc health_potion``：NPC 收到 ``health_potion`` 时条件成立。
- 当所有目标都 ``objective_complete`` 后，引擎会自动判定 `victory()` 通关。

如果地图上有多个同名 NPC，用第三个参数区分，例如只认 c3 上的那个：

.. code-block:: text

   trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)


战役示例：三种关系（The Legend of Raynor 第 14–16 章）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


内置战役 ``The Legend of Raynor`` 第 14–16 章分别演示 ``ally`` / ``neutral`` / ``enemy`` 三种交付关系：


.. list-table::
   :header-rows: 1

   * - 章节
     - 场景
     - NPC 类型
     - 物品
     - 关系
   * - 第 14 章（``14.txt``）
     - 给盟友农民镐头
     - ``npc_peasant``
     - ``pickaxe``
     - ``ally`` （开局 ``alliance`` 触发器结盟）
   * - 第 15 章（``15.txt``）
     - 给中立骑士骑士枪
     - ``npc_knight``
     - ``knight_lance``
     - ``neutral``
   * - 第 16 章（``16.txt``）
     - 给敌方法师魔杖
     - ``npc_mage``
     - ``wand``
     - ``enemy``



地图文件见 ``res/single/The Legend of Raynor/14.txt``、``15.txt``、``16.txt``。联机通用演示仍见 ``res/multi/give_demo.txt``。

每章玩法相同：用出生点的农民拾取物品 → 走到 NPC 旁右键"交给" → 目标完成获胜。
这三个 ``npc_*`` 单位类型与三件物品（``knight_lance``/``pickaxe``/``wand``）已在 ``res/rules.txt``
中定义，标题在 ``res/ui/style.txt`` 中。


----


7. 实现涉及的文件（维护参考）
-----------------------------



.. list-table::
   :header-rows: 1

   * - 用途
     - 文件
     - 说明
   * - 新指令 ``GiveOrder``
     - ``soundrts/worldorders/skills.py``
     - `keyword = "give"`；选择目标"愿意接收"的物品并校验 ``accepts_item``
   * - 注册指令关键字
     - ``soundrts/worldorders/_\_init__.py``
     - 导出 ``GiveOrder`` → 进入 `ORDERS_DICT["give"]`
   * - 物品转移逻辑
     - ``soundrts/worldunit/world_order.py``
     - `CreatureOrders.give(item, target)`，调用 ``accepts_item`` 校验、记录 ``received_items``
   * - 接收判定
     - ``soundrts/worldunit/worldcreature.py``
     - 默认值 `receive_items=0`/`accepted_items=()`/`accept_from=()`；``can_receive_items``、``relation_to``、``accepts_item``
   * - 解析字段
     - ``soundrts/definitions.py``
     - ``receive_items`` 入 ``int_properties``；``accepted_items``/``accept_from`` 入 ``string_list_properties``
   * - 右键默认操作
     - ``soundrts/worldunit/worldcreature.py``、``worldworker.py``
     - ``get_default_order`` 新增 "give" 分支（要求目标可接收）
   * - 触发器条件
     - ``soundrts/worldplayerbase/triggers.py``
     - ``lang_npc_has_item`` （及辅助方法）
   * - 客户端音效
     - ``soundrts/clientgameentity/events.py``
     - ``on_give`` / ``on_received``
   * - 指令菜单/快捷键
     - ``res/ui/style.txt``
     - ``def give`` （title=交给，shortcut=g，index=3.7）
   * - 示例 NPC 类型
     - ``res/rules.txt``
     - ``def quest_npc`` （``receive_items 1``）
   * - 示例地图
     - ``res/multi/give_demo.txt``
     - 联机通用可玩示例
   * - 战役关系示例
     - `res/single/The Legend of Raynor/14.txt`–``16.txt``
     - 第 14 章盟友农民收镐头；第 15 章中立骑士收骑士枪；第 16 章敌方法师收魔杖
   * - 战役示例
     - `res/single/The Legend of Raynor/24.txt`–``27.txt``
     - 24 交密信；25 交加雷克信物；26 交王旗；27 比武（见 [战役密信与结盟说明.md](战役密信与结盟说明.htm)）
   * - 序号目标示例
     - `res/single/The Legend of Raynor/28.txt`
     - 击杀/交物指定序号单位；见 [指定序号目标说明.md](指定序号目标说明.htm)
   * - 单元测试
     - ``soundrts/tests/test_give_item_to_npc.py``
     - 覆盖指令注册、转移、``receive_items`` 门控、触发器命中/区分




----


8. 注意事项与边界情况
---------------------


- 三重校验：目标须 ``receive_items 1``、物品在 ``accepted_items`` 白名单内（若配置）、
  给予者关系在 ``accept_from`` 白名单内（若配置），三者全过才接收，否则拒绝
  （``order_impossible``），右键也不会出现"交给"。默认所有单位都不接收（0）。
- 目标必须是"单位"：必须拥有 ``player`` （属于某个玩家），不能是物品本身或地形。
- 库存校验：要交出的物品必须确实在给予者库存中，否则拒绝执行。
- 物品自动选择：右键/不带物品参数时，会自动从携带物品里挑一件"目标愿意接收"的交出；
  也可用 ``give \<目标\> \<物品\>`` 显式指定。
- NPC 库存容量：交付是"脚本/剧情"性质的转移，会直接放入目标库存，不受目标的
  ``inventory_capacity`` 限制；目标若是无法持有物品的对象，则物品会掉落在其所在位置。
- 装备效果：交付时会对接收者执行 ``equip`` （即如果物品带 ``skills``/``buffs``，会作用到
  接收者身上），与 ``pickup`` 行为保持一致。若不希望 NPC 获得物品的增益，请使用不带
  ``skills``/``buffs`` 的纯剧情物品。
- 敌人也可作为接收者：配置 ``accept_from enemy`` 时，携带对应物品右键敌方该单位会
  变成"交给"而非"攻击"（仅对该物品+该单位类型生效）。
- 剧情奖励进背包：杀手全灭后可用 `(add_inventory_item garrek_token 1 raynor)` 把信物
  放入雷诺背包，下一章 ``campaign_flag`` 携带（The Legend of Raynor 第 24→25 章）。
- 过场语音归属：``npc_has_item`` 成立后的 ``cut_scene`` 须写在 ``player1`` 触发器上；
  写在 ``computer1`` 上人类玩家听不到（第 25 章交信物过场 7701）。


----


9. 测试
-------


运行本功能的单元测试：

.. code-block:: text

   python -m pytest soundrts/tests/test_give_item_to_npc.py -q


覆盖范围：指令注册、``is_allowed``/菜单、物品选择、物品转移与 ``received_items`` 记录、
``receive_items`` 门控、``relation_to`` （self/ally/neutral/enemy）、三个关系场景
（盟友农民收镐头 / 中立骑士收骑士枪 / 敌方法师收魔杖）、``accepted_items`` 的 is_a 继承、
``accept_from`` 关系门控，以及 ``npc_has_item`` 的命中/未命中/同名 NPC 方格区分。

结盟与部队归属相关测试见 ``soundrts/tests/test_campaign_alliance_transfer_triggers.py``。


----


10. 战役示例：第 24–25 章（密信 + 结盟）
----------------------------------------


两章共用交付条件：

.. code-block:: text

   trigger player1 (npc_has_item npc_knight_leader secret_letter c2) ...


- 玩家从 ``b1`` 拾取 ``secret_letter``，到 ``c2`` 右键首领 交给。
- 首领与护卫开局为 ``ai_mode guard``，避免交信前与内奸误战。

结盟与协同的差异见 `战役密信与结盟说明 <战役密信与结盟说明.htm>`_ （含 ``alliance_request``、
``transfer_units``、``allied_assist``、``allied_control`` 与第 24–27 章对比表）。


----


11. 战役示例：第 28 章（指定序号交物）
--------------------------------------


.. code-block:: text

   trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)


必须与 B2 上第 3 个 ``quest_npc`` 交物；交给第 1、2 个无效。同章还演示 ``killed_target`` 序号击杀与误杀失败，见 `指定序号目标说明 <指定序号目标说明.htm>`_。
