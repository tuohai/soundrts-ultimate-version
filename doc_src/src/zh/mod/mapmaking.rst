地图制作指南
============

.. contents::

简介
----

最好的入门方式大概是制作一张多人地图，并用它来对抗电脑进行测试。

多人地图
--------

新多人地图存放在哪里
""""""""""""""""""""

如果你有权写入 SoundRTS\ （或 SoundRTS test）的安装文件夹，
那么你可以把第一张多人地图存放在 "multi" 文件夹中。

如果你以非管理员模式工作，无权写入 program files 文件夹，你可以把正在编辑的地图文件存放在
"C:\\Documents and Settings\\你的登录名\\Application Data\\SoundRTS" 下的 "multi" 文件夹中。该文件夹会在你第一次启动 SoundRTS 时创建，除非 soundrts.exe 旁边已存在 "user" 文件夹。
另一种方案是把 SoundRTS 安装到你有写入权限的文件夹，并在上一段提到的文件夹中工作。

如何编辑地图
""""""""""""

用文本编辑器打开文件。
请使用小写书写，尽管大小写大概率会被忽略。

如何测试地图
""""""""""""

要测试一张地图，启动 SoundRTS 并进入单人游戏菜单。你可以在多人地图上对抗电脑。
每次开始游戏时地图都会重新加载，因此你无需重启 SoundRTS 即可测试修改。
一个有用的组合键是 Control Shift F2：如果你是地图上唯一的人类玩家，你将能查看整张地图（没有战争迷雾）。

如何查找并排除错误
""""""""""""""""""

如果在启动地图时收到 "map error（地图错误）" 消息并被退回菜单，那么有时你可以在 "client.log" 或 "server.log" 中找到额外（但晦涩）的信息，通常位于 "user/tmp" 文件夹中。

如果你仍然不明白错误出在哪里，欢迎直接联系我或在 soundRTSChat 列表中联系我。

注释
""""

以分号开头的行是注释。注释在运行时会被忽略。
分号之后直到行尾的所有内容也都是注释。

基本属性
""""""""

Title（标题）
'''''''''''''

"title 4018 5000" 表示："地图的标题是声音 4018 后接声音 5000"。

Objective（目标）
'''''''''''''''''

"objective 145 88" 表示："地图的目标是声音 145 后接声音 88"。

Nb_players_min 和 nb_players_max
'''''''''''''''''''''''''''''''''

"nb_players_min 2" 表示："需要 2 名玩家才能开始游戏。"
"nb_players_max 4" 表示："这张地图最多 4 名玩家。"

Global_food_limit
'''''''''''''''''

beta 9e 版新增。

beta 10 o 版更新：此食物上限不再在玩家之间均分。

"global_food_limit 200" 表示："每位玩家的食物不能超过 200，即使他建造更多农场也是如此。"

定义地形
""""""""

坐标（自 1.4.1.8 起）
'''''''''''''''''''''''

坐标系统使用 ``x,y``\ （例如 ``1,1`` 对应旧的 ``a1``）。在缩放模式下，坐标
仍用字母播报。传统记法会被接受并转换::

    west_east_paths 1,3 2,3
    south_north_paths 1,1 2,1 3,1

使用 x,y 记法可定义超过 26 列。

Square_width
''''''''''''

"square_width 12" 表示："格子宽度为 12 米"。
你不应修改此参数，因为如果对象太远可能会听不到。

Nb_lines 和 nb_columns
''''''''''''''''''''''

"nb_lines 7" 表示："网格有 7 行"。
"nb_columns 7" 表示："网格有 7 列"。
字母记法将列数限制为 26（``z``）；超过 26 列请使用 x,y 坐标。行数没有硬性上限，但性能会带来实际限制。
警告：nb_rows 已弃用，其含义与 nb_columns 相同。

West_east_paths 和 south_north_paths
'''''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" 表示："添加从 a1 到 b1、从 c1 到 d1、从 d1 到 e1、从 f1 到 g1 的通路"。
你只需给出通路最西端的格子。
"south_north_paths a1 a3 a4 a6" 表示："添加从 a1 到 a2、从 a3 到 a4、从 a4 到 a5、从 a6 到 a7 的通路"。
你只需给出通路最南端的格子。

West_east_bridges 和 south_north_bridges
'''''''''''''''''''''''''''''''''''''''''

桥的工作方式与通路完全相同。

通用情形：west_east 和 south_north
'''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" 表示："添加从 a1 到 b1、从 c1 到 d1、从 d1 到 e1、采用 'road' 样式的出口"。

'road' 必须在 style.txt 中定义。

注意："west_east_paths" 等同于 "west_east path"。

注意："south_north_bridges" 等同于 "south_north bridge"。

金矿、森林及其他资源矿床
''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" 表示："在 a2、b7、g6 和 f1 添加含 150 黄金的金矿"。

"wood 150 a2 b7 g6 f1" 表示："在 a2、b7、g6 和 f1 添加含 150 木材的森林"。

"goldmine" 和 "wood" 在 rules.txt 中被定义为资源矿床（"class deposit"）。

旧的复数关键词（"goldmines" 和 "woods"）仍然有效。

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" 表示："自动在每个格子里填充 2 块草地"。

Additional_meadows
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" 表示："在格子 a2、b7、g6 和 f1 各添加 1 块草地"。
"additional_meadows a2 a2 g6" 表示："在 a2 添加 2 块草地、在 g6 添加 1 块草地"。

Remove_meadows
''''''''''''''

remove_meadows 的作用与 additional_meadows 相反。

High_grounds
''''''''''''

SoundRTS 1.2 alpha 9 新增。

"high_grounds a2 b7" 表示："a2 和 b7 将拥有更高的海拔"。

子格地形（自 1.4.4.8 起）
''''''''''''''''''''''''''''''

也可以只覆盖一个大格子内部的某些子格。在格子坐标后加 ``/x,y``，
其中 ``x`` 和 ``y`` 是该大格子内部的 1 基子格坐标::

    high_grounds a1/1,1 a1/1,2
    terrain mountain a1/2,2
    ground a1/2,2
    no_air a1/2,2

子格网格由 ``subcell_precision`` 控制。默认值为 ``3``，因此
``a1/1,1`` 表示 3x3 划分中的左上子格。允许范围是 2 到 20::

    subcell_precision 20
    high_grounds a1/10,10 a1/10,11
    terrain mountain a1/1,1 a1/2,2 a1/3,3

以下地形命令支持子格坐标：``terrain``、``high_grounds``、``speed``、
``cover``、``water``、``ground`` 和 ``no_air``。没有单独指定的子格会继承
父大格子的地形。

在缩放模式下，地图浏览会播报当前子格的地形。比如 ``a1/1,1`` 是高地、
``a1`` 其他位置是低地时，浏览到该子格会播报高地，浏览其他子格则不会。

Square_name（自 1.4.1.8 起）
'''''''''''''''''''''''''''''

为格子或区域命名::

    square_name normandy 2,2 verdun 20,23
    square_name normandy 2,2 2,3 3,3

自 1.4.1.9 起，最多支持三级层级（省、市、区）。TTS
在进入另一区域时播报名称；在同一区域内浏览时会省略内层名称。在 ``tts.txt`` 中翻译名称::

    normandy = Normandy

地图音乐及音效（自 1.4.0.2 起）
''''''''''''''''''''''''''''''''

在地图文件中::

    map_music <id>
    map_battle_music <id>
    map_victory_sound <id>
    map_defeat_sound <id>


定义玩家的初始资源
""""""""""""""""""

注意（自 1.4.1.8 起）：阵营的初始单位和资源也可以在
``rules.txt`` 中定义。若两处都有定义，则以地图中的定义为准。

情形 1：所有人资源相同
''''''''''''''''''''''

组合使用以下命令：

starting_resources
..................

"starting_resources 10 10" 表示："每位玩家以 10 黄金和 10 木材开局。"

starting_units
..............

"starting_units townhall farm peasant" 表示："每位玩家以 1 座市政厅、1 座农场和 1 个农民开局。"

"starting_units townhall 2 farm peasant" 表示："每位玩家以 1 座市政厅、2 座农场和 1 个农民开局。"

starting_population
...................

"starting_population 60" 表示："每位玩家在农舍等 ``population_provided`` 建筑
提供的人口上限之上，再额外获得 60 人口上限。" 这是普通整数（不像资源那样
``× 1000``）。``player`` / ``computer_only`` 行里也可写 ``population 60`` 只
作用于该槽位。实际可用人口仍受 ``global_population_limit`` 限制。

从 SoundRTS 1.1 起，starting_units 还可以包含：

- 升级与研究："starting_units u_teleportation" 表示："每位玩家已研究好传送。"
- 被禁止的单位、建筑、技能、升级/研究（它们不会出现在菜单中）：

  - "starting_units -u_teleportation" 表示："每位玩家不能研究传送。"
  - "starting_units -a_teleportation" 表示："每位玩家不能使用传送。"

starting_squares
................

"starting_squares a2 b7 g6 f1" 表示："玩家的出生格子是 a2、b7、g6 和 f1。"

初始单位和建筑将在这些格子中创建。

``starting_squares`` 只固定每个出生槽位里的单位落在哪些格子；默认情况下并不固定“第几个加入的真人玩家拿哪个槽位”（见 random_starts_ 与 player_start_）。

.. _random_starts:

random_starts
.............

random_starts 1（默认）表示：开局时多个出生槽位会在真人玩家之间随机洗牌；槽位里的单位位置不变，但哪个玩家拿到哪个槽位不固定。

random_starts 0 表示：按槽位顺序分配给第 1、2、3… 个加入的 client，第 1 个加入的人固定拿第 1 个槽位。

.. _player_start:

player_start（自 1.4.2.8 起）
.............................

将第 N 个玩家（与 ``trigger playerN`` 一致，1-based）固定到指定槽位/格子；被钉的玩家不论 ``random_starts`` 是否开启都不参与洗牌，未指定的玩家仍按 ``random_starts`` 规则分配。

简单式：只改格子，保留该槽位已有的资源与单位列表。

::

    starting_squares a1 c1 e1
    starting_units townhall peasant
    player_start 1 b1

完整式：等价于把一条 player 行固定给玩家 N。

::

    player_start 1 5 10 a1 townhall peasant

也支持坐标形式与别名。

::

    player_start 1 2,3
    player_start 2 5,1

.. _spawn_semantics:

player 与 player_start 的出生点语义
''''''''''''''''''''''''''''''''''''''''

两者都能把单位/建筑生成在指定格子（如 ``a1``），但“固定”的含义不同：

- ``player`` / ``starting_squares``：定义出生槽位及其内容；单位坐标固定，但哪个真人玩家拿哪个槽位在 ``random_starts 1`` 时会被随机分配。
- ``player_start``：把第 N 个玩家钉到第 N 个槽位（并可改该槽位的格子），无视 ``random_starts`` 洗牌。

常见写法：

多人地图，每人不同资源，且要固定“玩家 1 在左下角” :

    random_starts 1
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant
    player_start 1 a1
    player_start 2 h1

第二套写法：只用 player 行，按加入顺序固定槽位（无需 player_start）。

::

    random_starts 0
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant

统一开局，只固定部分玩家位置 :

    starting_squares a1 c1 e1 g1
    starting_units townhall peasant
    player_start 1 a1
    player_start 3 e1

易混淆点：

- ``player 5 10`` 开头两个数字是资源数量（金/木），不是玩家编号，也不是坐标。
- 要钉“第几个玩家拿哪个角”，需 ``player_start`` 或 ``random_starts 0``；仅写 ``starting_squares`` / ``player`` 不够。

情形 2：不同玩家拥有不同资源
''''''''''''''''''''''''''''

player
......

"player" 命令定义一个出生点，它可能由人类玩家或电脑 AI 使用（在多人游戏中）。

此命令在一张多人地图中可重复使用多次。

"player 5 10 -townhall a1 townhall peasant c1 footman"
表示："某玩家以 5 黄金、10 木材开局，不允许建造市政厅，在 A1 有一座市政厅和一个农民、在 C1 有一个步兵。"

每条 ``player`` 行按出现顺序追加为一个出生槽位；``a1``、``c1`` 等才是方格坐标。若需把某个槽位固定给“第 N 个玩家”，请配合 player_start_ 或设置 random_starts 0（见上文 spawn_semantics_）。


类型列表
''''''''

这里给出一些可用于 starting_units_、player_ 和 computer_only_ 的正确类型名称。
完整列表请查看 rules.txt 文件：名称就在 "def" 语句之后。

- 单位：peasant footman archer knight catapult dragon mage priest necromancer
- 建筑：farm barracks lumbermill blacksmith townhall stables workshop dragonslair magestower
- 技能：a_teleportation
- 升级/研究：u_teleportation melee_weapon


添加怪物
""""""""

添加一个 computer_only 出生点
'''''''''''''''''''''''''''''

.. _computer_only:

"computer_only" 命令定义一个始终由电脑 AI 操控的出生点。该 AI 会对任何其他玩家或 AI 怀有敌意。

此命令可重复使用多次，但要当心：AI 过多会拖慢游戏。
因此，如果这些单位本不应彼此交战（例如散布全图的若干巨龙），请只用一个 AI。

computer_only 0 0 a3 dragon b1 dragon
表示："添加一个 0 黄金、0 木材的电脑 AI，在 A3 有一条巨龙、在 B1 有一条巨龙。"

中立电脑（自 1.4.2.8 起）
...........................

在 ``computer_only`` 行上加上 ``neutral`` 关键词，可使该 AI 成为中立：除非先被攻击，否则不会攻击任何人::

    computer_only 0 0 neutral a3 peasant b1 footman

不加 ``neutral`` 时，电脑对所有人怀有敌意。

玩家单位在进攻、防御、追击模式下不会主动攻击这些中立者，防御模式也不会仅因中立者而撤退；
只有对该单位下达强制攻击（``imperative``\ ）才会开战。

狩猎动物槽位（自 1.4.3.7 起）
..............................

若一行 ``computer_only`` 只 放置配置了 ``is_huntable`` / ``herdable`` 的动物（如 ``deer``\ 、``sheep``\ 、自定义 ``tiger``\ ），该槽位在引擎里不加入 默认 ``ai`` 联盟，也不与其它动物群、玩家或敌对 creep 结盟。每一行 ``computer_only`` 表示一个独立狩猎点。

若同一行混有动物与步兵等单位，整槽仍按普通电脑处理。详见 ``../player/hunting.htm`` §3.1。


添加触发器让怪物移动
''''''''''''''''''''

重要：添加默认的多人触发器
..........................

如果一张多人地图定义了至少一个触发器，默认的多人触发器就会被忽略。其目的是允许自定义胜利条件。

为保留默认胜利条件，必须把以下触发器显式添加到地图中（否则游戏不会自动结束）::

    trigger players (no_enemy_player_left) (victory)
    trigger players (no_building_left) (defeat)
    trigger computers (no_unit_left) (defeat)

注意：第三个触发器其实不是必需的。

胜利与失败条件（自 1.4.0.1 起）
................................

额外的触发器条件::

    trigger all (unit_lost knight) (defeat)
    trigger player1 (unit_lost a1 3 footman) (defeat)
    trigger player1 (building_lost 1 townhall) (defeat)
    trigger player1 (key_unit_killed a1 3 footman) (defeat)
    trigger all (key_unit_killed hero) (defeat)
    trigger all (key_units_killed 5 knight) (defeat)
    trigger all (units_lost 3 knight) (defeat)
    trigger all (building_lost townhall) (defeat)
    trigger all (buildings_lost 1 townhall 2 barracks) (defeat)
    trigger players (killed_target dragon) (victory)
    trigger players (killed_target dragon enemy) (victory)
    trigger player1 (has_killed 5 footman enemy) (objective_complete 1)
    trigger player1 (has_killed 1 footman 3 knight enemy) (objective_complete 2)

``killed_target`` 和 ``has_killed`` 可接受可选的 ``enemy`` 或 ``ally``，以只统计
对应关系的单位击杀。

指定序号单位 （自 1.4.3.1 起，The Legend of Raynor 第 28 章演示）— 语法与 ``transfer_units`` 相同，
按方格刷出顺序指定第 N 个 同类型单位（移动后序号不变）::

    trigger player1 (killed_target c3 3 demo_marker_footman enemy) (objective_complete 1)
    trigger player1 (killed_target c3 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

``killed_target`` 序号：`` (killed_target \<方格\> \<序号\> \<类型\> [enemy|ally])``。
``npc_has_item`` 序号：`` (npc_has_item \<方格\> \<序号\> \<类型\> \<物品\>)``。
``unit_lost`` / ``building_lost`` / ``key_unit_killed`` 序号：`` (\<方格\> \<序号\> \<类型\>)`` — 仅当该刷出序号单位/建筑丢失时成立（如保护初始 townhall、指定步兵）。
与 ``has_killed 3 footman`` （合计数量）不同。多目标可任意顺序完成；各 ``cut_scene`` 只描述该目标。
详见 ``campaign/unit-index.htm``；示例 ``res/single/The Legend of Raynor/28.txt``、``1.txt`` （初始基地）。

物品任务触发器（自 1.4.3.1 起）
................................

has_item — 玩家拾取了任务物品（检查所有存活单位的库存）::

    trigger player1 (has_item lost_amulet) (objective_complete 1)
    trigger player1 (has_item health_potion 2) (objective_complete 2)

用法：``(has_item \<物品type_name\> [数量])``

- ``\<物品type_name\>``：物品类型（如 ``lost_amulet``）。
- `````[数量]```：可选，需要持有的数量，默认 ``1``。

判定方式：统计当前玩家所有存活单位库存中该类型物品的数量，达到所需数量即成立。

物品必须是 ``class item``，且 ``consume_on_pickup`` 不能设为 1（默认 0），这样拾取后
物品才会留在库存中。在地图上像放置单位一样放置物品::

    lost_amulet c3
    health_potion 2 a2

在 ``rules.txt`` 中定义任务物品::

    def lost_amulet
    class item

确保用来拾取的单位有 ``inventory_capacity \> 0`` （如 ``peasant``、``footman`` 等）。

与相关条件的区别：

- ``has``：检测玩家拥有的单位 数量（``self.units``）；用于 "造出/拥有 N 个某单位"
- ``has_item``：检测玩家单位库存里的物品；用于 "找到/拾取了某物品"
- ``npc_has_item``：检测某个 NPC 库存或已收到记录里的物品；用于 "把物品交给某 NPC"（支持序号格式 ``\<方格\> \<序号\> \<类型\> \<物品\>``，见第 28 章）
- ``find``：检测某方格上地面存在 的物体（任意所属）；用于 "某处出现某物体"（物品被拾走后即不再满足）
- ``has_brought_item``：检测玩家单位是否携带 指定物品到达 某方格（物品在库存中即可，无需丢弃）
- ``remove_ground_item``：触发器动作，删除某方格 地面上的指定物品
- ``do``：触发器动作，按顺序执行多个子动作
- ``and``：触发器条件，所有子条件均成立时返回真

has_brought_item — 携带物品到达指定方格（物品在单位库存中，无需丢弃到地面）::

    trigger player1 (has_brought_item c3 mana_potion) (objective_complete 1)

用法：``(has_brought_item \<方格\> \<物品type_name\> [数量])``

- ``\<方格\>``：目标方格（如 ``c3``、``"3,3"``）。
- ``\<物品type_name\>``：物品类型（如 ``mana_potion``）。
- `````[数量]```：可选，需要在场单位身上合计持有的数量，默认 ``1``。

判定方式：在目标方格上查找该玩家的存活单位，统计这些单位库存中的指定物品；
达到所需数量即成立。空手进入方格不会完成目标。

remove_item — 触发器动作：从玩家单位库存中移除并销毁指定物品（剧情“上交”）::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

用法：``(remove_item \<物品type_name\> [方格] [数量])``

- 未写方格时，从该玩家所有存活单位的库存中移除；
- 写了方格（如 ``c3``）时，只从该方格上的玩家单位库存中移除；
- `````[数量]``` 可选，默认 ``1``。

典型流程：``has_brought_item`` 成立 → 播放过场 → ``remove_item`` 让物品从背包消失 →
``objective_complete``。示例：The Legend of Raynor 第 18 章。

do — 触发器动作：按顺序执行多个子动作::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

用法：``(do \<动作1\> \<动作2\> ...)``

``if`` 只有 if/else 两个分支，不能串联三个以上动作；需要多步剧情（过场 + 删物品 +
完成目标等）时必须用 ``do``。

remove_ground_item — 触发器动作：删除某方格地面上的指定类型物品::

    trigger player1 (find b2 mystery_treasure)
        (do (cut_scene 7546) (remove_ground_item b2 mystery_treasure)
            (add_units b2 10 gold_coin) (objective_complete 2))

用法：``(remove_ground_item \<方格\> \<物品type_name\> [数量])``

- ``remove_item`` 删的是玩家库存 里的物品；
- ``remove_ground_item`` 删的是方格地面 上的物品（例如玩家丢弃后触发开箱剧情）。

and — 触发器条件：所有子条件均成立时返回真::

    trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin)))
        (objective_complete 3)

用法：``(and \<条件1\> \<条件2\> ...)``

一行触发器只能写一个条件表达式；多个条件须包在 ``and`` 里，不能写成
``(条件1) (条件2) (动作)`` （后者会把第二个 S 表达式当成动作）。

``find`` 的参数顺序始终是方格在前、类型在后，包括嵌套在 ``not`` 里的子条件。
错误写法 ``(not (find gold_coin b2))`` 会先在默认方格查类型，几乎恒为真；
正确写法：``(not (find b2 gold_coin))``。丢弃开箱拾金币完整示例：The Legend of Raynor 第 22 章；背包使用见第 20 章。

npc_has_item — 某个 NPC 收到了指定物品（库存或 ``received_items`` 记录）::

    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

用法（二选一）：

- 经典：``(npc_has_item \<NPC选择符\> \<物品type_name\> [所在方格])``
- 序号：``(npc_has_item \<方格\> \<序号\> \<单位类型\> \<物品type_name\>)`` — 与 ``transfer_units`` 相同，
  指定该格第 N 个单位（按刷出顺序；移动后仍有效）。示例：The Legend of Raynor 第 28 章。

经典写法参数：

- ``\<NPC选择符\>``：目标单位的 ``type_name`` （如 ``footman``、``quest_npc``）或 单位 id。
- ``\<物品type_name\>``：物品类型，如 ``health_potion``。
- `````[所在方格]```\ （可选）：限定 NPC 当前所在 方格（如 ``c3``），用于多个同名 NPC 时区分。

序号写法按刷出序号识别目标，不依赖 NPC 当前是否仍在该格。

判定逻辑：遍历世界中所有玩家（含已出局玩家）的单位，找到匹配 ``\<NPC选择符\>`` 的单位，
若其 ``received_items`` 含有该物品类型，或其当前库存里仍持有该类型物品，则条件成立。

目标 NPC 必须在 ``rules.txt`` 中配置 ``receive_items 1`` （默认 ``0``，不接收物品）。
仓库内置示例接收型 NPC：``quest_npc`` （``res/rules.txt``，``receive_items 1`` +
``inventory_capacity 5``，未限制物品/关系）。

give — 触发器 order 中的脚本化交付::

    trigger player1 (timer 5) (order (a1 1 peasant) ((give c3 health_potion)))

语法：``give \<目标单位id\> [\<物品\>]``

- ``\<目标单位id\>``：目标单位的引用。
- ``\<物品\>``\ （可选）：当给予者携带多件物品时，用来指定交出哪一件；可写物品的
  ``type_name`` （如 ``health_potion``）或物品的 id。不写则默认交出库存第一件。

寻找物品示例地图（The Legend of Raynor 第 17 章）::

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
随后自动判定胜利、解锁下一章节。

交给 NPC 示例地图（``res/multi/give_demo.txt``）::

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

- ``computer_only 0 0 neutral c3 quest_npc``：在 c3 放一个中立 且可接收物品 的 NPC。
- ``add_objective 1 "..."``：添加 1 号目标，描述可用引号包裹的文本，也可用 tts 声音 ID。
- ``npc_has_item quest_npc health_potion``：NPC 收到 ``health_potion`` 时条件成立。
- 当所有主要 目标都 ``objective_complete`` 后，引擎会自动判定 ``victory()`` 通关。
  可选目标用 ``add_secondary_objective`` 添加（编号与主要目标独立，均可从 1 起），可不完成即通关；拒绝分支可用 ``objective_abandon`` 移除；完成可选目标用 ``secondary_objective_complete``。

如果地图上有多个同名 NPC，用第三个参数区分，例如只认 c3 上的那个::

    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)

战役示例（``The Legend of Raynor``）：第 14 章交给盟友农民镐头、第 15 章交给中立骑士骑士枪、
第 16 章交给敌方法师魔杖（``ally``/``neutral``/``enemy`` 关系）。
见 ``res/single/The Legend of Raynor/14.txt``、``15.txt``、``16.txt``。
联机通用演示仍见 ``res/multi/give_demo.txt``。

战役结盟与部队归属（自 1.4.3.1 起）
........................................

战役中 F12 动态外交无效；``alliance_request`` 发出申请后，人类玩家用 Ctrl+F4 同意、
Shift+F4 拒绝（无需 F12 选目标）。完整剧情示例见仓库 ``../player/campaign-northern-arc.htm``。

alliance_request — 触发器动作：某方向另一方发起结盟申请::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (cut_scene 7585) (alliance_request computer1) (objective_complete 1))

用法：``(alliance_request \<发起方\> [接收方])``；省略接收方时，向触发器所属玩家申请。

alliance_with — 触发器条件：是否与指定玩家已结盟::

    trigger player1 (alliance_with computer1) (objective_complete 2)

alliance_declined_with — 触发器条件：是否已拒绝来自指定玩家的结盟申请（战役内 Shift+F4）::

    trigger player1 (alliance_declined_with computer1)
        (do (cut_scene 7598) (add_units c3 3 knight) (objective_abandon 1))

add_secondary_objective — 触发器动作：添加可选目标（播报「可选目标」前缀）。编号与主要目标 独立 （均可从 1 起）::

    trigger player1 (timer 0) (add_objective 1 7583)
    trigger player1 (timer 0) (add_objective 2 7584)
    trigger player1 (timer 0) (add_secondary_objective 1 7599)

secondary_objective_complete — 触发器动作：完成可选目标 N（不影响主要目标 N）::

    trigger player1 (alliance_with computer1)
        (do (cut_scene 7586) (allied_assist computer1) (secondary_objective_complete 1))

objective_abandon — 触发器动作：放弃可选目标 N（如拒绝结盟）；仅对 ``add_secondary_objective`` 有效。

alliance_request_pending — 触发器条件：是否收到来自指定玩家的待处理结盟申请。

transfer_units / convert_units / change_owner — 触发器动作：把某玩家的单位
改归属给另一玩家（非 ``add_units`` 刷兵）::

    trigger player1 (alliance_with computer1)
        (do (transfer_units computer1 player1) (add_objective 2 7584))

未写单位选择符时转移原属方全部存活单位。选择符语法与 ``order``/``add_units`` 相同：
``\<方格\> \<数量\> \<类型\>``。

allied_assist — 触发器动作：让盟友部队自主参战（站岗→追击），不授予玩家指挥权::

    trigger player1 (alliance_with computer1)
        (do (allied_assist computer1))

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (allied_assist computer1 c2 4 npc_archer_escort))

用法：

- 全盟友：``(allied_assist \<盟友\>)``
- 选择性切追击：``(allied_assist \<盟友\> \<方格\> \<数量\> \<类型\> ...)``

单位选择符语法与 ``transfer_units`` / ``add_units`` 相同。未写选择符时该盟友全部可战斗站岗单位
切为追击；写了选择符时仅匹配单位切为追击，其余不变。

allied_control — 触发器动作：让玩家直接指挥盟友玩家的部队（选中、移动、攻击）::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (alliance 1) (allied_control computer1 c2 4 npc_knight_escort))

用法：

- 全盟友：``(allied_control \<盟友\> [指挥者])``
- 选择性移交：``(allied_control \<盟友\> [\<指挥者\>] \<方格\> \<数量\> \<类型\> ...)``

未写选择符时移交该盟友全部单位并全部切追击。写了选择符时仅匹配单位交给玩家指挥（保持站岗）；
未匹配 的可战斗站岗单位自动切为追击。

add_inventory_item — 触发器动作：把物品放入单位背包（剧情奖励、跨章补发）::

    trigger player1 (has_killed 3 traitor_guard)
        (do (cut_scene 7580) (add_inventory_item garrek_token 1 raynor) (set_campaign_flag ch24_garrek_token))

用法：``(add_inventory_item \<物品type_name\> [\<数量\>] [\<单位type_name\>])``；省略单位时，放入触发方首个有 ``inventory_capacity`` 的单位（雷诺战役默认找 ``raynor`` 系）。

跨章进度（三种机制）
....................

| 机制 | 配置 | 携带内容 |
| --- | --- | --- |
| ``campaign_carryover`` | ``rules.txt`` 单位字段 | 等级+经验、背包（可拆分，见 ``modding.rst``） |
| ``campaign_flag`` / ``set_campaign_flag`` | 地图触发器 | 剧情布尔状态（结盟、支线） |
| ``add_inventory_item`` | 地图触发器 | 指定物品进背包 |

``campaign_flag`` 写入 ``campaigns.ini`` 的 ``flags``\ ，跨章保留；``map_flag`` / ``set_map_flag`` 仅当前地图。

下一关可按标记补发物品::

    trigger player1 (timer 0) (if (campaign_flag ch24_garrek_token) (do (add_inventory_item garrek_token 1 raynor)))

unset_campaign_flag 可清除误持久化的战役标记。

set_ai_mode — 触发器动作：切换触发器所属方单位的 AI 模式（站岗↔追击等）::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard))

用法：``(set_ai_mode \<offensive|defensive|guard|chase\> [\<方格\> \<数量\> \<类型\> ...])``；未写选择符时作用于所属方全部单位。

set_yield_on_defeat — 触发器动作：开关实例级「认输」（HP 归零时不死亡、短暂无敌）::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

用法：``(set_yield_on_defeat \<0|1\> [\<方格\> \<数量\> \<类型\> ...])``。也可在 ``rules.txt`` 写 ``yield_on_defeat 1``。

units_yielded — 触发器条件：敌方认输单位计数（配合 ``yield_on_defeat``）::

    trigger player1 (units_yielded 1 npc_marco_ironhand) (objective_complete 1)

units_yielded_by — 触发器条件：指定攻击者令敌方认输（支持 ``is_a``）::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy) (objective_complete 1)

has_entered — 触发器条件：触发方单位进入指定方格（可用地名别名；可选单位类型）::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

map_flag / set_map_flag — 局内标记（仅当前地图，不写入战役存档）::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

stop_all_units / release_yielded_units — 停火与结束认输无敌::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy)
        (do (cut_scene 7710) (alliance 1 player1 computer1) (stop_all_units) (release_yielded_units computer1))

``stop_all_units`` 可写 ``computer1`` 等限定停火范围。``cut_scene`` 须挂在 ``player1`` 触发器上，否则人类客户端听不到语音。

The Legend of Raynor 北方战役（``24.txt``–``27.txt``）为连贯剧情线；各章共享歼灭 ``traitor_guard`` 副目标，``campaign_flag`` 跨章保留奖励。详见 ``../player/campaign-northern-arc.htm``：

- 第 24 章（密信给加雷克）：``allied_control``；杀手全灭后 ``add_inventory_item garrek_token``
- 第 25 章（信物给罗兰）：交信物前可击杀（误杀失败）；交后 ``set_ai_mode`` + ``set_yield_on_defeat``；``alliance_request``
- 第 26 章（王旗给薇拉）：``transfer_units`` 改归属
- 第 27 章（比武马尔科）：``has_entered c2 raynor7`` 播 7718；仅马尔科 ``set_ai_mode offensive``；护卫 ``order`` 前往 ``c1`` 让出场地；``units_yielded_by raynor7``；``stop_all_units`` + ``allied_control`` 仅 4 护卫骑士

第 25 章须开局注册 三个主要目标 （交信物、击败罗兰、歼灭杀手）与  一个可选目标 （结盟）；编号各自独立。按 F9 可同时播报主要与可选目标。
脚本电脑对外名称统一为 ``NPC`` （``Player.name`` 对 ``is_script_npc`` 读 ``ai_timers`` 的 title）。

关键 NPC（罗兰 ``npc_count_roland``、亲卫 ``npc_roland_guard`` 等）建议开局 ``ai_mode guard``；比武认输用运行时 ``set_yield_on_defeat`` 而非开局写在 rules 里，避免交信物前打不死。


巡逻
....

要命令最多 10 条来自 d1 的巨龙在 d1 和 d9 之间巡逻::

    trigger computer1 (timer 0) (order (d1 10 dragon) ((patrol d9)))


在特定时刻发动进攻
..................

要命令最多 10 条来自 e3 的巨龙在 20 分钟后（正常速度）进攻 b2::

    timer_coefficient 60
    trigger computer1 (timer 20) (order (e3 10 dragon) ((go b2)))


切换到另一个 AI
.................

computer_only 的默认 AI 是一个仅靠触发器、什么都不做的 AI。要切换到 "easy"（也称 "quiet computer"）::

    trigger computer1 (timer 0) (ai easy)


添加单位
..........

要在 A1 添加 10 条巨龙::

    trigger computer1 (timer 0) (add_units a1 10 dragon)


#random_choice、#end_choice 和 #end_random_choice
"""""""""""""""""""""""""""""""""""""""""""""""""

（beta 9g 新增）
这条预处理指令会在由 #random_choice、#end_choice 分隔（最后一个选项由 #end_random_choice 结束）的 2 个或更多选项之间随机选择。
每个选项由零行或多行组成。
一个地图文件中可以使用多个 #random_choice 指令，但它们不能嵌套。

例如，这可用于放置随机资源::

 #random_choice
 goldmines 500 e2 c6 b3 f5
 #end_choice
 goldmines 500 d2 d6 b4 f4
 #end_choice
 goldmines 500 c2 e6 b5 f3
 #end_random_choice

上面这些行表示："在 e2、c6、b3 和 f5 添加金矿，或在 d2、d6、b4 和 f4，或在 c2、e6、b5 和 f3"。这样资源就能保持平衡（当然，如果我没算错的话）。这只是一个示例。

地图标题和玩家数量不能用这种方式更改，因为预处理器是在地图加载时运行的（也就是说：远在单人游戏菜单加载之后）。

高级多人地图：如何更改游戏规则与表现
------------------------------------

地图结构
""""""""

高级地图是一个文件夹，其中包含一个名为 "map.txt" 的文件（内容是一张普通地图），以及大部分你在 "res" 文件夹中能找到的文件和文件夹：
rules.txt、ai.txt、ui 文件夹及其内容。

注意：目前在地图或战役文件夹中，本地化版本的 style.txt（例如：ui-fr/style.txt）不会被加载。
不过本地化的声音会被加载。

单人战役
--------

新单人战役存放在哪里
""""""""""""""""""""

如果你有权写入 SoundRTS\ （或 SoundRTS test）的安装文件夹，那么你可以把第一个战役存放在 "single" 文件夹中。

如果你以非管理员模式工作，无权写入 program files 文件夹，你可以把正在编辑的地图文件存放在
"C:\\Documents and Settings\\你的登录名\\Application Data\\SoundRTS" 下的 "single" 文件夹中。该文件夹会在你第一次启动 SoundRTS 时创建。
另一种方案是把 SoundRTS 安装到你有写入权限的文件夹，并在上一段提到的文件夹中工作。

战役文件夹的结构
""""""""""""""""

战役文件夹的名称将被单人游戏菜单使用。官方战役会在 "ui" 文件夹中拥有各自的标题。
该文件夹包含若干章节文件。它还包含模仿 "res" 文件夹结构的文件和文件夹：rules.txt、ai.txt、ui……

必需模组文件
''''''''''''

SoundRTS 1.2 alpha 10 新增。

战役可以定义它所需要的模组。所需模组将被自动加载。

所需模组定义在战役文件夹中一个名为 "mods.txt" 的文件里：

- 该文件是以逗号分隔的模组名称列表；
- 如果该文件不存在，则保留当前模组；
- 如果该文件为空，则加载 "原版" 游戏。

章节文件
''''''''

章节文件是名为 "0.txt"、"1.txt"、"2.txt" 等的文本文件。当某战役首次启动时，只有第 0 章可用。当一章完成后，下一章便可运行。已可用的最高章节号会自动存储在玩家的配置文件 campaigns.ini 中。

一个章节文件描述一个任务章节或一个过场动画章节。

至少要有一个章节文件，名为 "0.txt"。

章节文件的语法
""""""""""""""

一章是一个任务或一段过场动画。

任务章节文件的语法
''''''''''''''''''

任务文件与多人地图差别不大。
也允许使用高级地图结构：那种情况下，文件夹名即为章节号。

合作战役（自 1.4.2.2 起，1.4.4.4+ 帝国时代决定版式）：在 :strong:```campaign.txt``
中声明 ``coop_campaign`` / ``coop_intro`` / ``coop_missions``；可选 ``hero_min_level 13:2 16:3 …``
（跨章英雄最低等级，见 ``modding.rst``）；单人与合作共用同一份
``N.txt`` 任务地图（不要再维护 ``N.coop.txt``）。详见
``mod/coop-campaign.htm`` 与 ``player/战役与合作战役改进说明.htm``。

合作任务在 ``N.txt`` 中声明 ``nb_players_min`` / ``nb_players_max`` 与多个 ``player``
出生块；服务器上任意玩家完成目标都会为团队做出贡献。单人战役仍只注册 1 名玩家，
仅占用第一个出生点。

在战役中，F12（动态结盟）不会选择任何目标。由触发器脚本控制的电脑会
播报为 "NPC"，而不是 ``ai_timers`` 等内部名称。

Intro（开场）
..............

注意：一个数字可以代表 tts.txt 中定义的一段文本消息（SoundRTS 1.2 alpha 9 新增）。

示例："intro 7500 7501 7502" 表示："在游戏开始前，播放 7500.ogg、7501.ogg 和 7502.ogg（如果在 tts.txt 中有定义则播放文本）"。
intro 命令定义一段在游戏开始前播放的声音和文本序列。当玩家按下某个键时，播放序列中的下一个元素。开场可以是例如带音乐的标题，然后是角色之间对话的场景，再然后是任务简报。开场之后，游戏会告知任务目标。

Add_objective
..............

"add_objective player1 1 7000" 表示："添加编号为 1、声音为 7000.ogg 的主要 目标"。

"add_secondary_objective player1 1 7599" 表示："添加编号为 1 的可选 目标"（可不完成即通关）。主要目标与可选目标各自独立编号，均可从 1 起，例如可同时存在主要目标 1 与可选目标 1。

必须完成所有主要 目标才能赢得任务。可选目标用 ``secondary_objective_complete`` 完成，或用 ``objective_abandon`` 放弃。如果某个主要目标失败（例如某个重要角色死亡），任务即告失败。

Register_objective（触发器中的动作）
....................................

``register_objective`` 登记 通关所需的主要目标编号，但 不写入 F9 列表、 不播报「新目标」语音。

语法（写在触发器动作里）::

    register_objective 1 2 3

用途： 若多个 ``add_objective`` 分散在不同触发器里（完成目标 1 后再显示目标 2），每次 ``add_objective`` 也会把该编号加入胜利集合；只完成目标 1 时可能因其余编号尚未 ``add`` 而`` 提前胜利``。开局用 ``register_objective`` 登记全部编号可避免此问题。

渐进显示写法 — ``timer 0`` 登记全部编号并只 ``add_objective`` 第一条；每完成一条再 ``objective_complete`` + ``add_objective`` 下一条::

    trigger player1 (timer 0) (do (register_objective 1 2) (add_objective 1 7510))
    trigger player1 (has 4 pylon) (do (objective_complete 1) (add_objective 2 7511))
    trigger player1 (has_entered f1 gateway) (objective_complete 2)

胜利判定： 引擎维护 ``\_required_objective_numbers`` （来自 ``register_objective`` / ``add_objective``）与 ``\_completed_objective_numbers`` （来自 ``objective_complete``）。当`` 已登记`` 的每个主要编号都完成时调用 ``victory()``，与 F9 上是否仍显示该目标无关。

F9 / 语音序号： 存在多个主要目标（已登记或已显示）时，F9 与 ``add_objective`` 会播报「主要目标 N：」再读描述；仅一个主要目标时不读序号。实现见 ``soundrts/objective_announce.py``。

示例：``mods/starcraft/single/sc_build_tests/1.txt`` （2 个目标）；``sc_late_game/1.txt`` （6 个链式目标）。说明见 ``campaign/progressive-objectives.htm``。

Objective_complete（触发器中的动作）
....................................

此动作只能放在触发器的动作部分。

"objective_complete 1" 表示："现在主要 目标 1 已完成"。

Secondary_objective_complete（触发器中的动作）
..............................................

"objective_complete 1" 只作用于主要目标。完成可选目标请用::

    secondary_objective_complete 1

表示："现在可选 目标 1 已完成"。

触发器示例：

"trigger player1 (has barracks) (objective_complete 2)" 表示："为 player1 添加以下触发器：如果他拥有至少 1 座兵营，则目标 2 完成"。

计时系数
........

可以使用计时系数来度量某个区块中触发器的时间。

例如，如果你希望所有触发器都在给定的半分钟区块内发生，你可以像这样把计时系数设为 30。

"timer_coefficient 30"

每当经过这段时间，计时计数器就会递增（加 1）。然后你可以把触发器绑定到计时器达到某个数值上。例如，如果你想让援军在 90 秒后（30 秒的 3 次递增）出现在地图上，你可以这样做。

"trigger player1 (timer 3) (add_units a1 10 footman)" ; 三次计时滴答后，在 a1 给玩家 10 个步兵

Cut_scene（触发器中的动作）
...........................

注意：流式声音与预加载声音之间的区别已在 SoundRTS 1.2 中取消。所有声音都会被提前加载。

注意：一个数字可以代表 tts.txt 中定义的一段文本消息（SoundRTS 1.2 alpha 9 新增）。

过场动画可以在游戏中途被触发：当某物被发现、当援军到达等等。

"cut_scene 7500 7501" 表示：播放由声音 7500 和 7501 组成的过场动画。

触发器示例：

"trigger player1 (has_entered d5) (cut_scene 7500)" 表示："为 player1 添加以下触发器：如果他进入了格子 d5，则播放由声音 7500.ogg 组成的过场动画"。

Timer 与 timer_coefficient（触发器中的条件）

"timer_coefficient 60"

"trigger player1 (timer 2) (cut_scene 7500)" 表示："2 分钟后（2 x 60 秒）播放 7500.ogg 声音文件。"

AI 命令
.......

可以在任务中控制电脑的行动，以增加挑战。你需要通过在给定触发器上直接让它们的单位接受命令来实现。

例如，我们可以让位于 A1 的 AI 部队移动到玩家已知所在的 A3，在那里它们会与遇到的玩家部队交战。这里，我们将用 10 个步兵向玩家发动进攻。

"timer_coefficient 60"

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1)))"

这里括号的位置很重要，要把正确的命令封装在该触发器的正确部分中。如果你的触发器因某种原因似乎不起作用，试着仔细检查你的括号。

也可以为给定单位排队多条命令以依次执行。在下面这个场景中，假设玩家的基地散布在 a1 和 b1。那我们就需要告诉步兵在搞定 a1 后再前往 b1。我们可以这样做。

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1)))"

最后，如果你想让 AI 单位进入 "auto_attack（自动攻击）" 模式——在清扫完玩家基地后追猎任何幸存的玩家单位——你也可以这样做。

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1) (auto_attack)))"

你也可以用命令让电脑训练自己的单位，然后再让这些单位成为后续命令的对象。这里，我们将让电脑的兵营立即训练另外 10 个步兵，以替换我们即将派去进攻玩家的那些。

trigger computer1 (timer 0) (order (a1 barracks) ((train footman) (train footman) (train footman))) ; 以此类推，直到你有 10 条训练步兵的命令

注意每条训练命令都必须分开写，你不能这样写：(train 10 footman)

这并不是增加电脑玩家可用单位数量的唯一方式，你也可以使用如下所示的 add_units 命令。

trigger computer1 (timer 0) (add_units a1 10 footman)

然而，这是立即生效的，不给玩家任何影响该事件的机会。在另一个场景中，玩家可以通过摧毁用于训练的兵营来阻止电脑获得下一批步兵。而用这种方式，这些步兵无论如何都会出现。

过场动画章节文件的语法
''''''''''''''''''''''

注意：流式声音与预加载声音之间的区别已在 SoundRTS 1.2 中取消。所有声音都会被提前加载。

注意：一个数字可以代表 tts.txt 中定义的一段文本消息（SoundRTS 1.2 alpha 9 新增）。

过场动画章节是一段可被打断的声音序列。当过场动画章节播放完毕后，下一章便会解锁。
不要与任务中由触发器在满足某条件时（例如发现某个格子）运行的较短过场动画混淆，也不要与任务的开场（或简报）混淆。

过场动画章节只有 3 行。例如：
cut_scene_chapter
title 7000
sequence 7500 7501 7502

第一行是一个关键词，用于告诉游戏该章节是过场动画而非任务。
title 行用于战役菜单。
sequence 行表示："播放声音 7500.ogg，后接 7501 和 7502；如果玩家按下某个键，则跳过当前声音并播放下一个"。

地图编辑器（实验性）
--------------------

客户端内置了一个用于多人地图的实验性地图编辑器。它只对地形有效，因此你仍需手动编辑地图来放置单位。

启动编辑器
""""""""""

在某张地图上开始一局游戏。这张地图将作为起点。进入控制台（按 Escape 下方的那个键）并输入命令："edit"。按 Enter。编辑器的键盘绑定将从 res/ui/editor_bindings.txt 加载。

从调色板中选择一种地形
""""""""""""""""""""""

按 PageUp 或 PageDown 选择一种地形。每种地形的含义存储在 res/ui/editor_palette.txt 中。

将地形应用到格子
""""""""""""""""

按 Enter 将地形应用到当前格子。具有相同特性（地面与相同高度）的相邻格子将自动用通路连接。不同的格子则会移除其通路。

如果已开启缩放模式，Enter 只会把选中的地形应用到当前子格。保存后的地图会使用
`子格地形（自 1.4.4.8 起）`_ 中说明的 ``square/x,y`` 语法。

切换到相邻格子的通路
""""""""""""""""""""

按 Control + Shift + 方向键可在对应方向上添加或移除通路。

保存地图
""""""""

按 Control + s 保存地图。该文件永远不会覆盖另一个文件。文件名将是 user/multi/editor0.txt、editor1.txt、editor2.txt 等等。

退出编辑器
""""""""""

按 F10 并退出游戏即可离开编辑器。届时会对地图做一次自动保存以防万一（但不要太指望它）。它的名称是 user/multi/editor_autosave.txt。

添加单位（文本编辑器）
""""""""""""""""""""""

用文本编辑器打开文件。使用 `定义玩家的初始资源`_ 中提到的命令。
