可配置方格地形与建造用地
==========================

.. epigraph:: 面向 **模组作者**：``class terrain`` 方格地貌、``class building_land`` 建造用地、``square_terrain`` 对象驱动动态地形，以及地图编辑器调色板。与 ``mapmaking.htm`` 地图语法、``modding.htm`` 规则关键字互补。


----

概述
----


所有地形都是同一种东西：``rules.txt`` 里 ``class terrain`` 声明属性，``style.txt`` 里同名 ``def`` 管语音/脚步/颜色。

**引擎不再自动赋默认地形。** 方格上的地形只来自：

1. 地图 ``terrain <名> <格>``（名与 rules 里 ``def`` 一致）
2. 对象 ``square_terrain``（树林、城镇、草地等）
3. ``high_grounds`` / ``is_high_ground`` 只额外播「高地」，不是地形名


定义与放置
----------


**rules.txt：**

.. code-block:: text

   def plain
   class terrain
   is_dynamic 1

   def lake
   class terrain
   is_water 1
   is_dynamic 0

   def hill
   class terrain
   is_high_ground 1

**style.txt：** 同名 ``def``（``lake``、``plain`` 等，配置 ``title``、``ground``、颜色）。单位上的 ``move_on_<键>`` / ``falling_on_<键>`` 可匹配地形类型名或 ``ground`` 类别，详见 ``modding.htm`` 战斗音效章节。

**地图：**

.. code-block:: text

   terrain plain a1
   terrain lake d1        ; 湖泊：自动标水域，地面单位不可进入
   terrain hill c1        ; 小山 + 高地
   high_grounds e1        ; 只播「高地」

- ``terrain lake d1`` **不必**再写 ``water d1``
- 旧地图的 ``water`` 关键字仍可用（可选）
- 未写 ``terrain`` 的空格：``type_name`` 为空，不播地形语音


建造用地（``class building_land``）
------------------------------------


草地（``meadow``）、空地（``build_site``）不再是引擎硬编码类型。在 ``rules.txt`` 里用 **`class building_land`** 声明，可任意扩展：

.. code-block:: text

   def parameters
   default_building_land meadow

   def meadow
   class building_land
   square_terrain meadows 40

   def build_site
   class building_land
   square_terrain build_sites 50

   ; 模组自定义示例
   def landing_pad
   class building_land
   square_terrain build_sites 45

.. list-table::
   :header-rows: 1

   * - 机制
     - 说明
   * - ``default_building_land``
     - 地图未写 ``building_land`` 时，规则层默认类型（可被地图覆盖）
   * - 地图 ``building_land <名>``
     - 整张图默认建造用地类型
   * - ``additional_meadows`` / ``additional_build_sites``
     - 兼容旧地图，分别刷 ``meadow`` / ``build_site``
   * - ``nb_<类型>_by_square <N>``
     - 每格自动刷 N 个该类型（须在 rules 里 ``class building_land``）
   * - ``nb_meadows_by_square <N>``
     - 遗留写法；类型由 ``building_land`` / 地图推断决定
   * - ``additional_building_land <名> <格…>``
     - 通用写法，刷任意已声明的建造用地
   * - ``terrain meadows a1``
     - 动态地貌反向关联，按 ``square_terrain`` 刷对应 ``class building_land`` 对象

起飞、部分升级在原地恢复建造用地时，优先使用**该建筑建造时保存的用地类型**；仅当建筑没有保存引用时，才用地图的 ``building_land`` 或 ``nb_<type>_by_square`` 推断出的默认类型。

每种建造用地可在 ``style.txt`` 配 ``title``、脚步声、颜色；用 ``square_terrain`` 关联想要的方格地貌（如 ``meadows``、``plain``、``build_sites``）。

地图关键字详见 ``mapmaking.htm`` 中 *Building_land* 与 *Nb_<type>_by_square* 两节。


``class terrain`` 常用属性
--------------------------


.. list-table::
   :header-rows: 1

   * - 属性
     - 含义
   * - ``is_dynamic``
     - ``0`` 静态；``1`` 动态（可被对象地形盖住）
   * - ``is_ground``
     - 地面单位能否站立
   * - ``is_air``
     - 空中单位能否飞越
   * - ``is_water``
     - 标为水域
   * - ``is_high_ground``
     - 标为高地 + 播「高地」
   * - ``passable_units``
     - 允许通行的单位类型白名单（支持 ``is_a`` 继承链）
   * - ``height``
     - 高度层级
   * - ``blocks_path``
     - 封住相邻方格之间的通道（如密林、高山）
   * - ``speed``
     - 可选。``speed <地面倍率> <空中倍率>``（如 ``speed .5 1`` → 地面 50%% 速）。地图 ``terrain <名>`` 时作为默认 ``terrain_speed``；地图 ``speed`` 行可覆盖单格

地图 ``terrain <名>`` 时，上述属性**一并写入方格**（可叠加）。例如 ``mountain``：``is_ground 0`` + ``is_air 0`` → 地面与空中均不可通行。

**移动速度**（与单位 ``speed_on_terrain`` 不同）按优先级生效：

1. 地图 ``speed <地面> <空中> <格>`` — 进游戏时的最终配置
2. ``rules.txt`` 里该 ``class terrain`` 的 ``speed`` — 仅有 ``terrain``、未写地图 ``speed`` 时
3. 默认 ``(100, 100)`` 全速

``editor_palette.txt`` 只在**地图编辑器**里决定「画地形时填什么」：未写 ``speed`` 的调色板项从 ``rules.txt`` 继承；保存地图时非默认速度会写成 ``speed`` 行。运行时**不读取**调色板。

浅滩示例：

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1

``is_ground 1`` 且 ``is_water 1`` 的浅滩/大桥与相邻陆地划入**同一地面区域**，分层寻路可正常穿过（例如雷诺传第二章 ``terrain ford a2`` → ``go a3``）。

**玩家逐格铺桥**（``wooden_bridge``、``is_buildable_on_water_only``、``bridge_terrain bridge_deck``）见 `水上铺桥 <water-bridge-building.htm>`_。地图自带 ``big_bridge`` 为固定栈桥；完工后的玩家桥段地形名为 ``bridge_deck``（桥面）。

单位在地形上的战斗修正（自 1.4.5.0 起）
----------------------------------------

除方格自带的 ``terrain_speed`` 外，可在**单位 def** 上按地形单独修正移动与战斗数值。格式与 ``speed_on_terrain`` 相同：

.. code-block:: text

   <地形名> <修正值> [<地形名> <修正值> ...]

**判定位置：** 攻击者/移动者**当前所在格**的地形名（``type_name``；子格地形时用 ``type_name_at``）。

**叠加规则：** 修正值为**加值**，与 ``mdg_vs``、``mdg_cd_vs`` 等叠加；负值表示削弱。数值写法与 ``mdg``、``mdg_cd`` 相同（支持小数，内部 ×1000）。

.. list-table::
   :header-rows: 1

   * - 属性
     - 含义
   * - ``speed_on_terrain``
     - 在该地形上的移动速度（绝对值或替换，见既有规则）
   * - ``mdg_on_terrain`` / ``rdg_on_terrain``
     - 近战 / 远程攻击力修正（加在 ``mdg``/``rdg`` 与 ``*_vs`` 结果之后）
   * - ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``
     - 攻击冷却修正（**正值 = 冷却更长、攻速更慢**）
   * - ``charge_mdg_terrain`` / ``charge_rdg_terrain``
     - 冲锋额外伤害修正（加在 ``charge_mdg``/``charge_rdg`` 与 ``charge_*_vs`` 之后）
   * - ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``
     - 冲锋冷却修正（正值 = 冲锋更久才能再用）

另有命中/闪避地形修正（作用于目标所在地形）：``mdg_cover_on_terrain``、``rdg_cover_on_terrain``、``mdg_dodge_on_terrain``、``rdg_dodge_on_terrain``。

**示例 — 骑士在沼泽中削弱：**

.. code-block:: text

   def knight
   speed 2.5
   mdg 6
   mdg_cd 1.5
   speed_on_terrain marsh 1.5 ford 1.5
   mdg_on_terrain marsh -2
   mdg_cd_on_terrain marsh 0.5

在 ``marsh`` 上：移速 1.5、近战攻击 4、攻击冷却 2.0 秒。

**示例 — 带冲锋的单位：**

.. code-block:: text

   def raynor
   charge_mdg 4
   charge_mdg_cd 10
   charge_mdg_terrain marsh -1
   charge_mdg_cd_on_terrain marsh 2

在 ``marsh`` 上：冲锋额外伤害 −1，冲锋冷却 +2 秒。

实现：``soundrts/combat/damage_calculation.py``、``soundrts/combat/attack_action.py``；测试：``test_combat_terrain_modifiers.py``。

已写入 ``res/rules.txt`` 的地形：``plain``、``rocky_plain``、``plateau``、``hill``、``high_rocky_plain``、``mountain_pass``、``basin``、``lake``、``sea``、``ocean``、``river``、``creek``、``ford``、``big_bridge``、``bridge_deck``、``marsh``、``mountain``，以及对象地形 ``town``、``meadows``、``build_sites``、``forest``、``dense_forest``。

山地仅允许特定单位（继承链生效）：

.. code-block:: text

   def archers
   class soldier

   def archer
   class soldier
   is_a archers

   def mountain
   class terrain
   is_ground 0
   is_air 0
   blocks_path 1
   passable_units archers

上例中 ``archer`` 及其继承链上的单位可进入 ``mountain``，其他单位仍不可通行。


``square_terrain``：对象驱动的动态地形
--------------------------------------


``square_terrain`` 是本系统最独特的玩法层：**地形可以随地图上的对象出现、消失而实时改变**，不必改地图文件。

与地图 ``terrain`` 的区别：

.. list-table::
   :header-rows: 1

   * -
     - 地图 ``terrain``
     - 对象 ``square_terrain``
   * - 写在
     - 地图文件
     - ``rules.txt`` 的单位/建筑/矿床 ``def`` 上
   * - 方格锁定
     - 是（``fixed_terrain``）
     - 否
   * - 会随对象增减变化
     - 否
     - **是**
   * - 典型用途
     - 海洋、河流、平原底图
     - 树林、草地、城镇、工地

一句话：**地图 ``terrain`` 画底色；``square_terrain`` 让对象「长」出上层地貌。**


语法
~~~~


写在任意 ``def`` 上（单位、建筑、矿床、草地等均可）：

.. code-block:: text

   square_terrain <地形名> [priority] [min_count]

.. list-table::
   :header-rows: 1

   * - 参数
     - 默认
     - 含义
   * - ``<地形名>``
     - （必填）
     - ``rules.txt`` 里 ``class terrain`` 的地形名，须与 ``style.txt`` 同名 ``def`` 配套
   * - ``priority``
     - ``50``
     - 优先级，**数值越大越优先**
   * - ``min_count``
     - ``1``
     - 该 ``type_name`` 的对象在此方格至少要有几个，条目才生效

同一 ``def`` 可写多行，表示「数量少时一种地貌、数量多时另一种」：

.. code-block:: text

   def wood
   class deposit
   square_terrain forest 80
   square_terrain dense_forest 90 7

- 方格里有 **1～6 棵** ``wood`` → 满足 ``forest``（priority 80）
- 方格里有 **7 棵及以上** ``wood`` → ``dense_forest``（priority 90）同时满足，**90 > 80，密林胜出**

草地与工地：

.. code-block:: text

   def meadow
   square_terrain meadows 40

   def build_site
   square_terrain build_sites 50

城镇中心：

.. code-block:: text

   def townhall
   class building
   square_terrain town 60

``keep``、``castle`` 等写了 ``is_a townhall`` 的建筑，同样会触发 ``town`` 地貌（继承链对 ``square_terrain`` 源对象类型生效）。


如何选出当前地貌（``type_name``）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


每个游戏 tick，引擎对**未锁定**的方格调用 ``update_terrain()``，流程如下：

1. 扫描方格内所有对象的 ``type_name``
2. 读取各对象 ``def`` 上的 ``square_terrain`` 条目
3. 过滤：该类型对象数量 ≥ ``min_count`` 的条目进入候选
4. 在候选中取 **`priority` 最大** 的一条，其 ``<地形名>`` 写入方格的 ``type_name``
5. 若胜出地形有 ``blocks_path 1``（如 ``dense_forest``），自动封住与相邻方格之间的通道；对象移除后通道恢复

**建造用地（``building_land``）** 有单独一层语音逻辑：方格可同时播报「特征地貌 + 工地/草地」。例如同一格既有树林又有 ``build_site`` 时，可能听到森林 + 工地两层（``feature_voice`` 与 ``building_land_voice`` 分工，见下节）。


动态更新时机
~~~~~~~~~~~~


带 ``square_terrain`` 的对象**加入或离开**方格时，引擎会把该方格及其**四邻**标记为脏区，下一 tick 重算地貌：

- 砍光树木 → 森林语音消失，方格 ``type_name`` 变回 ``""``（若地图未写 ``terrain``）
- 树木攒够 7 棵 → 普通林变密林，相邻通路可能被 ``blocks_path`` 封死
- 城镇中心建成 → 方格播「城镇」；城镇被毁 → 城镇地貌消失
- ``meadow`` / ``build_site`` 放置或清除 → ``meadows`` / ``build_sites`` 随之切换

另每 2 秒全图兜底扫描一次，防止遗漏。


地图底色 vs 对象上层：谁会赢？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1

   * - 方格状态
     - 行为
   * - 地图**未写** ``terrain``
     - 完全由对象 ``square_terrain`` 决定 ``type_name``
   * - ``terrain plain a1`` 等（``is_dynamic 0``）
     - 方格 ``fixed_terrain`` 锁定，对象无法改变地貌
   * - ``terrain forest a1`` 等（``is_dynamic 1``）
     - 按 ``square_terrain`` **反向关联**生成对象，**不锁定**；对象消失后地貌可变

``is_dynamic 1`` 时，引擎扫描所有 ``def`` 的 ``square_terrain``：目的地形名与地图 ``terrain`` 一致则生成该对象，数量为 ``min_count``：

.. list-table::
   :header-rows: 1

   * - 地图
     - rules 关联
     - 自动生成
   * - ``terrain forest b1``
     - ``wood`` → ``square_terrain forest``
     - 1 棵 ``wood``
   * - ``terrain dense_forest b1``
     - ``wood`` → ``square_terrain dense_forest 90 7``
     - 7 棵 ``wood``
   * - ``terrain town a1``
     - ``townhall`` → ``square_terrain town``
     - 1 座 ``townhall``
   * - ``terrain meadows a1``
     - ``meadow`` → ``square_terrain meadows``
     - 1 块 ``meadow``

因此：

- 想做出「砍树变空地」：写 ``terrain forest``（动态，会刷树）或只靠 ``wood`` 的 ``square_terrain``
- 想做出「永远是平原，上面可以盖房子」：写 ``terrain plain``，平原底色锁定；对象地貌仅在不锁定的格子上动态变化

.. note::

   ``class terrain`` 上的 ``is_dynamic 1/0`` 表示设计意图（可覆盖 / 静态），**实际是否可覆盖由方格是否 ``fixed_terrain`` 决定**。


语音分层（听感）
~~~~~~~~~~~~~~~~


导航播报时，``resolve_square_layers()`` 按层叠加（``style.txt`` 的 ``title``）：

.. list-table::
   :header-rows: 1

   * - 层
     - 来源
     - 示例
   * - ``feature_voice``
     - 胜出的对象地貌 ``type_name``
     - ``forest``、``dense_forest``、``town``
   * - ``building_land_voice``
     - 建造用地对象的地貌，且与 ``feature_voice`` 不同时额外播
     - ``build_sites``、``meadows``
   * - ``high_ground_voice``
     - 方格或子格标了高地
     - ``_high_ground``（与地貌名无关）

举例：

.. list-table::
   :header-rows: 1

   * - 方格内容
     - 听到的大致顺序
   * - 7+ 棵 ``wood``
     - 密林
   * - 3 棵 ``wood``
     - 森林
   * - ``wood`` + ``build_site``
     - 森林 + 工地
   * - 只有 ``meadow``
     - 草地
   * - ``meadow`` + ``build_site``
     - 工地（``build_site`` priority 50 > ``meadow`` 40）
   * - 有 ``townhall``
     - 城镇
   * - 地图 ``terrain hill`` + 高地标记
     - 小山 + 高地（地图锁定，不受树林影响）
   * - 什么都没有
     - 静音（无地貌 ``title``）


通行与寻路
~~~~~~~~~~


对象动态地貌的 ``type_name`` 同样参与通行判定：

- 未写 ``passable_units`` → 用该地形 ``class terrain`` 的 ``is_ground`` / ``is_air`` / ``is_water``
- 写了 ``passable_units`` → 白名单优先

``blocks_path 1`` 的地形（``dense_forest``、``mountain``）在成为当前 ``type_name`` 后，会影响**相邻方格之间的 exit**，不只是格内站立。仅当**相邻两格均为** ``blocks_path`` 地形时才封住二者之间的通道（密林 ↔ 密林）；密林 ↔ 普通陆地之间的南北向通道不封。

``go`` / ``patrol`` 命令与语音提示
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

对目标方格做与移动相同的通行判定（``Square.is_passable_for``）。不可通行时命令在**入队阶段**失败（``order_impossible`` 音效），不进入移动。

**按地形属性（未配置 ``passable_units``）**

.. list-table::
   :header-rows: 1

   * - 条件
     - 消息键（``style.txt`` ``messages``）
     - 中文播报示例
   * - 地面单位 → 纯水路（``is_water`` 且非 ``is_ground``）
     - ``water_impassable``
     - 水路无法通行
   * - 水上单位 → 陆地
     - ``land_impassable``
     - 陆地无法通行
   * - 地面单位 → ``is_ground 0``
     - ``ground_impassable``
     - 地面无法通行
   * - 空中单位 → ``is_air 0``
     - ``air_impassable``
     - 空中无法通行
   * - 未完工桥梁脚手架
     - ``scaffold_impassable``
     - 未完工，无法通行

**``passable_units`` 白名单**

地形写了 ``passable_units`` 时，白名单**优先于** ``is_ground`` / ``is_air`` / ``is_water`` 分类判定。不在名单内的单位 ``go`` 失败，播报该单位 ``style.txt`` ``title`` + 「无法通行」（消息键 ``passable_units_denied``，TTS 5701）。名单条目支持 ``is_a`` 继承（例如 ``passable_units archers`` 允许所有 ``is_a archers`` 的单位）。

示例：

.. code-block:: text

   def mountain
   class terrain
   is_ground 0
   is_air 0
   passable_units archers

- ``archer``（``is_a archers``）→ 可 ``go`` 进山
- ``footman``、``knight`` → ``go`` 失败，播报「步兵，无法通行」「骑士，无法通行」

``patrol`` 与 ``move_to_or_fail``（含智能单位编队移动）使用同一套 ``_terrain_impassable_reason`` 检查。
~~~~~~~~~~~~~~~~~~~~~~~~


**第一步 — ``rules.txt`` 声明地貌属性：**

.. code-block:: text

   def my_swamp_patch
   class terrain
   is_ground 1
   is_water 1
   passable_units boat

**第二步 — ``style.txt`` 配语音/脚步：**

.. code-block:: text

   def my_swamp_patch
   title 4310

**第三步 — 挂在对象上：**

.. code-block:: text

   def my_puddle
   class deposit
   square_terrain my_swamp_patch 70 3

方格内每有 3 个 ``my_puddle``，就动态变成 ``my_swamp_patch``，只有 ``boat`` 能进。

同一对象也可挂多种地貌，用 ``priority`` / ``min_count`` 做阈值阶梯（参考 ``wood`` → ``forest`` / ``dense_forest``）。


现有 ``square_terrain`` 一览（``res/rules.txt``）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1

   * - 对象 ``def``
     - ``square_terrain``
     - priority
     - min_count
     - 胜出地貌
     - 备注
   * - ``wood``
     - ``forest``
     - 80
     - 1
     - 森林
     - 有树即有林
   * - ``wood``
     - ``dense_forest``
     - 90
     - 7
     - 密林
     - 7+ 棵树；``blocks_path 1``
   * - ``meadow``
     - ``meadows``
     - 40
     - 1
     - 草地
     - 建造用地
   * - ``build_site``
     - ``build_sites``
     - 50
     - 1
     - 工地
     - 优先级高于草地
   * - ``townhall``
     - ``town``
     - 60
     - 1
     - 城镇
     - ``keep``/``castle`` 继承生效

对应 ``style.txt``：``def forest``、``def dense_forest``、``def meadows``、``def build_sites``、``def town``。


语音举例（地图 + 对象）
-----------------------


.. list-table::
   :header-rows: 1

   * - 情况
     - 播报
     - ``type_name``
   * - 未写 terrain
     - （无）
     - ``""``
   * - ``terrain plain a1``
     - 平原
     - ``plain``
   * - ``terrain lake d1``
     - 湖泊
     - ``lake``
   * - ``terrain hill c1``
     - 小山 + 高地
     - ``hill``
   * - 有树林
     - 森林
     - ``forest``
   * - 树林 ≥7
     - 密林
     - ``dense_forest``
   * - 有城镇中心
     - 城镇
     - ``town``
   * - 有草地
     - 草地
     - ``meadows``
   * - 有工地
     - 工地
     - ``build_sites``


地图编辑器调色板
----------------


实验性编辑器通过控制台 ``edit`` 进入，绑定见 ``res/ui/editor_bindings.txt``：

.. list-table::
   :header-rows: 1

   * - 操作
     - 按键
   * - 切换调色板项
     - PageUp / PageDown
   * - 应用到当前格
     - Enter
   * - 子格编辑（F8 缩放模式）
     - Enter 只改当前子格
   * - 保存地图
     - Ctrl+S

应用逻辑在 ``soundrts/lib/editor_palette.py``（``apply_palette_to_square``），与上文地形规则一致。调色板项若**未写** ``speed``，加载时从 ``rules.txt`` 同名 ``class terrain`` 继承默认速度；保存地图时写入 ``speed`` 行（见上文优先级）。

.. list-table::
   :header-rows: 1

   * - 调色板 ``style``（``class terrain`` 名）
     - ``is_dynamic``
     - 编辑器行为
   * - ``lake``、``mountain``、``hill`` 等
     - ``0`` 静态
     - ``fixed_terrain = True``，写入 ``type_name``，应用 ``class terrain`` 标志；保存为 ``terrain <名>``
   * - ``forest``、``dense_forest``、``meadows`` 等
     - ``1`` 动态
     - 按项内 ``woods`` / ``meadows`` / ``goldmines`` 刷对象，**不锁定**；``update_terrain()`` 解析为对应对象地貌
   * - ``rocky_plain``、``plain`` 等（动态但无对象）
     - ``1``
     - 刷对象后若仍无对象地貌，则锁定 ``type_name`` 以便保存

调色板项与地貌名（与 ``rules.txt`` / ``style.txt`` 对齐）：

.. list-table::
   :header-rows: 1

   * - 调色板 ``def`` 名
     - ``style``
     - 效果摘要
   * - ``forest``
     - ``forest``
     - 1 草地 + 3 棵 ``wood`` → 森林
   * - ``dense_forest``
     - ``dense_forest``
     - 7 棵 ``wood`` → 密林
   * - ``meadows``
     - ``meadows``
     - 3 块 ``meadow`` → 草地
   * - ``goldmine``
     - ``meadows``
     - 草地 + 树 + 金矿
   * - ``lake`` / ``river`` / ``sea`` / ``ocean``
     - 同名
     - 静态水域
   * - ``mountain``
     - ``mountain``
     - 静态不可通行
   * - ``rocky_plain`` / ``high_rocky_plain``
     - 同名
     - 可保存的平原变体

.. note::

   旧名 ``woods``、``dense_woods``、``meadow`` 已从调色板移除；地图里手写资源仍可用 ``wood`` / ``woods`` 关键字。


测试
----


.. code-block:: bash

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py soundrts/tests/test_water_impassable_order.py -q
