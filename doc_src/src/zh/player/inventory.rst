背包与装备栏功能说明
====================


本文介绍 SoundRTS 中单位的背包（库存）、装备栏界面，以及 rules.txt 里同型物品模型（一个类型同时是可拾取物品 + 可装备武器/护甲）的配置方法。


----


1. 功能概述
-----------



.. list-table::
   :header-rows: 1

   * - 界面
     - 快捷键
     - 显示内容
   * - 属性界面
     - `Alt+V`
     - 单位全部属性（生命、攻击、科技等）
   * - 背包
     - `Shift+V`
     - 库存中的所有物品（药水、任务物品、武器、护甲等）
   * - 装备栏
     - `Ctrl+V`
     - 武器与护甲：背包中的可装备物品 + 仍为内置的武器/护甲



三个界面互斥，同一时间只能打开一个。均需单独选中一个己方单位。

背包 vs 装备栏
~~~~~~~~~~~~~~


- 背包：通用物品管理。可装备武器/护甲、使用消耗品、丢弃任意物品。
- 装备栏：专门浏览武器和护甲。出厂内置、尚未转为背包物品的装备会标为「内置武器 / 内置护甲」（只读，不能装备/卸下/丢弃）；已在背包中的武器/护甲物品可正常操作。

装备切换规则
~~~~~~~~~~~~


当单位同时配置了内置装备与 item 装备（例如 ``weapons bow sword``，弓为 ``class weapon``、剑为 ``class item``）时：


.. list-table::
   :header-rows: 1

   * - 规则
     - 说明
   * - 出厂优先级
     - 内置装备始终优先出厂装备；item 装备进入背包
   * - ``spawn_weapons_equipped 1`` （默认）
     - 仅 item 出厂武器不自动装备，留在背包，且无法手动装备
   * - ``spawn_weapons_equipped 0``
     - item 出厂武器留在背包，可手动装备
   * - 切换限制
     - 内置装备只能与内置装备切换；item 装备只能与 item 装备切换；内置与 item 不能互相切换
   * - 护甲
     - 逻辑相同：``spawn_armor_equipped`` 控制 item 护甲是否出厂穿戴；内置护甲已启用时无法穿戴 item 护甲



若单位仅有 item 装备（如 footman 的 ``sword``），无内置武器/护甲，则 ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` 仍控制是否出厂静默装备（默认装备）。


----


2. 玩家操作
-----------


2.1 打开条件
~~~~~~~~~~~~


- 选中恰好 1 个己方单位。
- 背包：库存不为空；否则播报「背包为空」。
- 装备栏：至少有一件武器或护甲（内置或背包中）；否则播报「装备栏为空」。

2.2 界面内按键（背包与装备栏相同）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - 方向键
     - 上一件 / 下一件
   * - ``g``
     - 朗读当前物品简介（``style.txt`` 中的 ``intro``）
   * - ``Enter``
     - 装备武器 / 穿戴护甲 / 使用消耗品（背包）
   * - ``Shift+Enter``
     - 卸下已装备的武器或护甲
   * - ``Delete``
     - 丢弃：先确认，再按 ``Enter`` 执行
   * - ``Shift+Delete``
     - 直接丢弃，不询问
   * - ``Esc``
     - 退出；若在丢弃确认中则取消丢弃



2.3 游戏内拾取与给予
~~~~~~~~~~~~~~~~~~~~


- 拾取：携带空间足够的单位对地面物品使用 ``pickup`` （默认右键或指令菜单）。
- 丢弃：指令 ``drop``，或在背包/装备栏中用 ``Delete``。
- 交给：指令 ``give``，详见 `给 NPC 物品功能说明.md <给NPC物品功能说明.htm>`_。


----


3. 两套装备系统
---------------


3.1 内置武器 / 内置护甲（传统）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


在 rules.txt 为单位配置：

.. code-block:: text

   def footman
   weapons sword          ; class weapon 类型（如 bow、short_sword）
   armor footman_armor    ; class armor 类型


- 武器走 ``class weapon`` 系统，护甲走 ``class armor`` 系统。
- 不会自动出现在背包里。
- 在装备栏中显示为「内置武器 / 内置护甲」，不能通过界面装备、卸下或丢弃。

3.2 背包物品装备（同型模型）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


同一 ``type_name`` 可定义为 ``class item``，并加上：

.. code-block:: text

   equippable_as_weapon 1   ; 可作为武器装备
   equippable_as_armor 1    ; 可作为护甲穿戴


物品进入单位 ``inventory`` 后，可通过背包或装备栏装备；数值（``mdg``、``mdf`` 等）在装备时套用到单位身上，卸下后还原。

示例（res/rules.txt 中的剑）：

.. code-block:: text

   def sword
   is_a melee
   class item
   equippable_as_weapon 1
   mdg 3.5
   mdg_bonus 2.5
   mdg_cd 1.5
   mdg_range 1
   transport_volume 1
   can_use_tech melee_weapon


示例（步兵鳞甲）：

.. code-block:: text

   def footman_armor
   is_a light_armor
   class item
   equippable_as_armor 1
   mdf 0.5
   mdf_bonus 1
   rdf_bonus 1
   can_use_tech melee_armor



----


4. 出厂装备自动入背包
---------------------


单位生成时，引擎会检查 rules 中的出厂配置：

- `weapons <名称>`：若同名类型为 ``class item`` 且 ``equippable_as_weapon 1``，则创建物品实例 → 放入背包；若无内置武器且 ``spawn_weapons_equipped 1`` （默认），则静默装备。
- `armor <名称>`：若同名类型为 ``class item`` 且 ``equippable_as_armor 1``，同理；若无内置护甲且 ``spawn_armor_equipped 1`` （默认），则静默穿戴。

因此 footman 的配置：

.. code-block:: text

   def footman
   weapons sword
   armor footman_armor
   inventory_capacity 2


在 ``sword`` 与 ``footman_armor`` 均定义为可装备 item 时，训练出的步兵会：

1. 背包中有剑和鳞甲各一件；
2. 出厂即已装备（默认 ``spawn_weapons_equipped 1``、``spawn_armor_equipped 1``）；
3. `Shift+V` 能看到全部物品；
4. `Ctrl+V` 显示「剑，已装备」「步兵鳞甲，已装备」，且可用 `Shift+Enter` 卸下、``Delete`` 丢弃。

出厂是否静默装备（仅背包 item）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   spawn_weapons_equipped 0/1   ; 无内置武器时：控制 class item 出厂武器是否静默装备（默认 1）
                                ; 有内置武器时：1=item 武器留背包且不装备，0=允许手动装备
   spawn_armor_equipped 0/1     ; 无内置护甲时：控制 class item 出厂护甲是否静默穿戴（默认 1）
                                ; 有内置护甲时：1=item 护甲留背包且不穿戴，0=允许手动穿戴
   ; 内置 class weapon / class armor 不受上述 flag 影响，始终出厂生效


混合配置（弓箭手）
~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def archer
   weapons bow sword


- ``bow`` 为 ``class weapon`` → 内置武器，不入背包，始终出厂装备。
- ``sword`` 为 ``class item`` + ``equippable_as_weapon 1`` → 入背包。
- 默认 ``spawn_weapons_equipped 1`` 时：弓已装备，剑留在背包且无法装备；只能在弓等内置武器之间切换，不能与剑切换。
- 装备栏会同时列出内置的弓与背包中的剑。

若希望弓为主武器、剑作备用且允许玩家手动装备：

.. code-block:: text

   def archer
   weapons bow sword
   spawn_weapons_equipped 0
   inventory_capacity 3


此时 bow 仍会自动装备，sword 在背包中待玩家手动装备；装备剑后只能在 item 武器之间切换，仍不能与弓直接切换（需先卸下剑）。

前提条件
~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 字段
     - 说明
   * - ``inventory_capacity``
     - 必须 > 0，否则无法持有物品，出厂转背包也不会执行
   * - ``transport_volume``
     - 物品在库存中占用的格数（默认 1）；当前容量按物品件数计算，与 ``transport_volume`` 无关
   * - 背包空间
     - 出厂武器、护甲各占一件；``inventory_capacity`` 需足够（如 footman 为 2）




----


5. 地图作者：rules.txt 配置清单
-------------------------------


5.1 仅内置装备（不可卸下）
~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def my_unit
   weapons short_sword
   armor light_armor
   ; 不设置 inventory_capacity，或设为 0


``short_sword``、``light_armor`` 使用 ``class weapon`` / ``class armor`` 即可。

5.2 可拾取、可装备、可卸下的装备
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. 定义 item，并写上战斗数值与标志位：

.. code-block:: text

   def my_sword
   class item
   equippable_as_weapon 1
   mdg 3
   mdg_range 1
   transport_volume 1


2. 单位开启库存并声明出厂武器：

.. code-block:: text

   def my_soldier
   inventory_capacity 2
   weapons my_sword


3. 在 ``res/ui/style.txt`` 中配置 ``title``、``intro``，供读屏使用。

5.3 地面放置物品
~~~~~~~~~~~~~~~~


地图中放置 ``class item`` 类型，格式见各战役 ``rules.txt`` 注释；单位靠近后 ``pickup`` 拾取。

5.4 消耗品
~~~~~~~~~~


.. code-block:: text

   def health_potion
   class item
   buffs heal


在背包中按 ``Enter`` 使用（走 ``use_item`` 指令），不能在装备栏中当作武器/护甲装备。


----


6. 服务端指令（脚本 / 调试用）
------------------------------


以下指令由客户端背包/装备栏发送，也可在触发器 ``order`` 中直接使用：


.. list-table::
   :header-rows: 1

   * - 指令
     - 参数
     - 说明
   * - ``equip_weapon``
     - 物品 id
     - 装备库存中的武器物品
   * - ``unequip_weapon``
     - 物品 id
     - 卸下
   * - ``equip_armor``
     - 物品 id
     - 穿戴库存中的护甲物品
   * - ``unequip_armor``
     - 物品 id
     - 脱下
   * - ``use_item``
     - 物品 id
     - 使用消耗品
   * - ``drop``
     - 物品 id
     - 丢弃到脚下



单位升级/变形时，库存会通过 ``transfer_inventory_to`` 转移到新单位（见 ``world_order.py``）。


----


7. 常见问题
-----------


Q：为什么以前 footman 按 Shift+V 显示「背包为空」？

出厂的 ``weapons sword`` 走的是内置武器系统，不会自动进背包。只有把 ``sword`` 定义为 ``class item`` 并启用出厂转背包逻辑后，剑才会出现在库存里。

Q：装备栏里显示「内置护甲」且不能操作？

说明该护甲仍是 ``class armor``，未配置为 ``equippable_as_armor 1`` 的 item。按第 5.2 节为 ``footman_armor`` 等类型增加 ``class item`` 与 ``equippable_as_armor 1`` 即可。

Q：背包和装备栏能同时开吗？

不能。打开其中一个时，需先 ``Esc`` 退出再开另一个。

``Q：``class item`` 和 ``class weapon`` 能用同一个名字吗？``

可以（同型模型）。例如 ``sword`` 同时 ``is_a melee``、``class item``、``equippable_as_weapon 1``：出厂时入背包；地图上也可作为物品放置和拾取。纯 ``class weapon`` 的 ``bow`` 则只作内置武器。

Q：为什么弓箭手有弓和剑，却不能在装备栏里装备剑？

若同时配置了内置武器与 item 武器，且 ``spawn_weapons_equipped 1`` （默认），内置武器优先，item 武器留在背包且无法装备。只有 ``spawn_weapons_equipped 0`` 时才允许手动装备 item 武器。无论哪种设置，内置与 item 装备都不能互相切换，只能各自在同类之间切换。


----


8. 相关文件
-----------



.. list-table::
   :header-rows: 1

   * - 文件
     - 内容
   * - ``res/ui/bindings.txt``
     - `Shift+V` 背包、`Ctrl+V` 装备栏热键
   * - ``soundrts/attributes/inventory_screen.py``
     - 背包界面逻辑
   * - ``soundrts/attributes/equipment_screen.py``
     - 装备栏界面逻辑
   * - ``soundrts/worldunit/worldbase.py``
     - 出厂装备入背包、物品装备/卸下
   * - ``soundrts/worlditem.py``
     - 物品基类与 `equippable_as_*` 属性
   * - ``res/rules.txt``
     - ``sword``、``footman_armor`` 等示例定义



更多物品交互（交给 NPC、触发器）见 `给NPC物品功能说明 <给NPC物品功能说明.htm>`_、`寻找物品通关说明 <寻找物品通关说明.htm>`_。
