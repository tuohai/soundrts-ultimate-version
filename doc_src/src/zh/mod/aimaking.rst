AI 制作教程
===========

.. contents::

1. 简介
-------

本教程介绍如何编写电脑 AI。
你需要编辑 ``ai.txt`` （脚本）以及 mod 的 ``rules.txt`` （各阵营难度映射）。
文件位于 SoundRTS 包的 ``res`` 文件夹中；mod、战役或地图也可以自带这些文件。

一个 AI 就是一段小脚本：电脑会从上到下逐条执行其中的命令，并不断循环。
不需要任何编程基础。

2. ``ai.txt``：AI 脚本
-----------------------------

在 ``ai.txt`` 里，每个 AI 以 ``def \<名称\>`` 开头，后面跟随它的命令::

    def tang_empire_easy
    research 1
    workers 12
    get 9 villager 5 footman
    attack
    goto -1

说明：

- 名称可以是任意标识符，例如 ``tang_empire_easy``、``my_mod_hard``。
  邀请菜单不会直接显示这些自定义名；玩家看到的是 ``rules.txt`` 里映射的
  难度档位（见下一节）。
- 若 mod 的 ``ai.txt`` 里写了 ``clear``，会清掉在此之前已加载的 AI 脚本
  （包括基础 ``res/ai.txt`` 里的五档）。这不影响邀请菜单显示几项，只影响
  内存里保留哪些 ``def``。对大多数 mod 而言 不必写 ``clear``。
- 同名 ``def`` 后写覆盖前写（mod 层覆盖基础层）。
- 若某个档位在运行时找不到对应脚本，``get_ai`` 会回退到最接近的已定义脚本
  （包括旧名 ``easy`` / ``aggressive`` 的别名链）。

3. 邀请电脑菜单与 ``rules.txt`` 映射
-------------------------------------

单机「开始游戏」与多人「邀请电脑」菜单中的选项，由当前 mod 的 ``rules.txt``
决定，而不是固定五个按钮，也不需要在 ``ai.txt`` 里写空的 ``def beginner``
占位。

无 mod 时
~~~~~~~~~

菜单固定为五档标准难度：

- ``beginner`` —— 初级
- ``intermediate`` —— 中级
- ``advanced`` —— 高级
- ``expert`` —— 专家
- ``nightmare`` —— 噩梦

加载 mod 时
~~~~~~~~~~~

引擎扫描各 阵营（faction） 在 ``rules.txt`` 中的难度映射行。只要映射指向的
脚本名在 ``ai.txt`` 里确有 ``def``，该档位就会出现在菜单中。

新写法（推荐） —— 在每个阵营块内写标准档位名::

    def tang_empire
    class race
    townhall county_government
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

上例会在菜单中显示 邀请初级 / 中级 / 高级 电脑（写几行映射就出现几档）。
玩家选「初级」、阵营为唐朝时，实际运行 ``tang_empire_easy`` 脚本。

旧 mod 写法 —— 仍使用 ``easy`` / ``aggressive``::

    def orc
    class race
    ...
    easy orc_defensive
    aggressive orc_aggressive

菜单显示 邀请防御型 / 攻击型 电脑（兼容老 mod）。运行时仍邀请 ``easy`` 或
``aggressive`` 档位，再经 ``rules.txt`` 找到各阵营的实际脚本。

要点
~~~~

- ``ai.txt`` 只负责写脚本；``rules.txt`` 负责「这一档叫什么、指向哪个脚本」。
- 各阵营可以指向不同的脚本（例如唐朝 ``beginner tang_empire_easy``、突厥
  ``beginner turkic_hanate_easy``），菜单只列档位名，不列阵营名。
- 若同一 mod 里既有 ``beginner`` 又有 ``easy`` 映射，菜单只保留 ``beginner``
  （避免重复）。
- 内部用脚本（如 ``timers``）不会出现在邀请菜单中。
- 多人联机主机发出 ``invite_ai \<档位名\>`` （例如 ``invite_ai beginner``）；
  旧的 ``invite_beginner`` 等命令仍可用。

4. 设置项（在 "def" 顶部写一次即可）
------------------------------------

这些用于调节 AI 的整体行为。请把它们写在 ``def`` 的靠前位置，使其在循环
之前执行。难度越高，通常意味着更大的经济、开启科技、更多基地，以及更愿意
主动进攻。

- ``constant_attacks 0/1`` —— 为 ``1`` 时，AI 会持续进攻并探索地图，而不是
  龟缩在家里。
- ``research 0/1`` —— 为 ``1`` 时，AI 在资源足够时研究武器、护甲、技能升级。
- ``workers \<n\>`` —— AI 试图维持的工人（农民）数量。工人越多经济越强。
  默认值为 ``10`` 。
- ``expand \<n\>`` —— 维持的主基地（town hall）总数。初始基地也算在内，所以
  ``expand 2`` 表示 AI 会再造一个分基地。默认值为 ``0`` （不额外扩张）。
- ``attack_ratio \<百分比\>`` —— AI 的部队需要达到目标区域内敌方实力的多少
  百分比才会进攻。``180`` （默认）表示「拥有 80% 优势才进攻」（谨慎）。数值
  越低越早投入战斗；低于 ``100`` 时，即使略弱也会进攻（持续施压）。
- ``counter_skill \<0-100\>`` —— AI 单位利用 ``mdg_vs`` / ``rdg_vs`` 克制加成
  选择目标与派兵的程度。``0`` 完全忽略克制，只按 ``menace`` （威胁值）选目标；
  ``100`` 始终优先打克制关系最好的敌人，并识别 ``is_a`` 继承（例如
  ``mdg_vs cavalry`` 也会克制 ``is_a 骑兵`` 的骆驼兵）。中间值在克制加成与
  ``menace`` 之间加权。未写时默认 ``100``。

  原版 ``res/ai.txt`` 五档默认：初级 ``25``、中级 ``50``、高级 ``75``、
  专家 ``90``、噩梦 ``100``。
- ``starting_resources \<数量...\>`` —— 在地图（或阵营）开局资源之上额外增加
  的资源，顺序与地图 ``starting_resources`` 相同，数值含义也相同（如
  ``10 10`` = 10 金 10 木；内部与地图一样按 ``× 1000`` 存储）。不写则
  无加成。
- ``starting_units \<单位\>...`` —— 在正常开局之后，于 AI 出生方格额外生成
  单位或建筑。语法与地图 ``starting_units`` 相同（数量写在类型名前，如
  ``5 footman 2 archer``）。会走阵营 ``equivalent`` 映射。**占用人口**
  （与地图开局单位相同；可用 ``starting_population`` 提高上限）。不写则无额外单位。
- ``starting_population \<n\>`` —— 在农舍等 ``population_provided`` 单位提供的
  人口上限之上，额外增加人口上限。普通整数（不像资源那样 ``× 1000``）。
  实际可用人口仍受地图 ``global_population_limit`` 限制。
- ``train_time \<pct\>`` —— 训练时长百分比（``100`` = 正常，``50`` = 时间减半 /
  训练更快）。仅影响 ``train`` 与按训练计时的变形。不写则 ``100``。
- ``research_time \<pct\>`` —— 科技研究 / 时代推进时长百分比（``100`` = 正常，
  ``80`` = 快 20%）。仅影响 ``research`` / ``advance``。不写则 ``100``。
- ``unit_hp \<pct\>`` —— 该电脑所有单位血量百分比（``100`` = 正常，``120`` =
  +20% HP）。在合作战役 ``enemy_hp_factor`` 之后再乘。不写则 ``100``。

  以上指令仅在游戏开始时生效一次，不会进入脚本循环（与 ``get`` /
  ``attack`` 不同）。

  原版 ``res/ai.txt`` 额外加成（叠在每张地图的正常开局之上）：

  - 中级：``starting_resources 50 50``、``starting_population 10``
  - 高级：``100 100`` + ``2 footman 2 archer``、``starting_population 20``、
    ``train_time 50``、``research_time 80``
  - 专家：``200 200`` + ``5 footman 4 archer 2 knight``、``starting_population 40``、
    ``train_time 50``、``research_time 70``、``unit_hp 120``
  - 噩梦：``400 400`` + ``8 footman 6 archer 4 knight``、``starting_population 60``、
    ``train_time 40``、``research_time 60``、``unit_hp 140``
- ``watchdog \<秒\>`` —— 安全机制：若 AI 在同一行卡住超过这么久，就跳到下一行。
  ``0`` 表示关闭。

单位克制（counter_skill）
------------------------------

当 ``counter_skill`` 大于 ``0`` 时，电脑单位会按 ``rules.txt`` 中的 vs 加成
优先选敌：

- 骑士 ``mdg_vs archer 12`` 会优先打弓箭手，而不是威胁更高的单位。
- 弓箭手 ``rdg_vs footman 7`` 会优先打步兵。
- ``mdg_vs`` / ``rdg_vs`` 里的类型名会匹配目标的 ``type_name``，或 ``is_a``
  继承链上的任意父类型。

``counter_skill`` 较低时，高 ``menace`` 目标仍可能「打错人」；为 ``100`` 时，
在射程内会稳定选克制最好的敌人。

自 1.4.5.2 起，默认 ``menace`` 为**多维战斗评分**（伤害、命中、冷却、前摇、HP、
防御、闪避、射程、移速等），可用 ``menace_mult`` / ``menace_vs`` 等覆盖；详见
``modding.rst`` *自动威胁度 / 选敌优先级*。

这同时影响「微观」（每个单位打谁）和「宏观」（优先进攻哪片区域、先派哪类
兵），但仍须满足 ``attack_ratio`` 兵力门槛。

5. 行动命令
-----------

- ``get \<n\> \<单位\>...`` —— 招募或建造，直到 AI 拥有列出的每种单位或建筑各
  ``\<n\>`` 个。可一次列出多组。确切的单位类型名称见 ``rules.txt`` 。
  示例： ``get 10 footman 20 archer 10 knight``
- ``attack`` —— 从此刻起，只要实力足够就发动进攻（同时会打开
  ``constant_attacks`` ）。
- ``wait \<秒\>`` —— 在当前行停留若干秒后再继续。用于控制节奏（简单 AI 可在
  每波之间使用 ``wait`` ）。注意：非零的 ``watchdog`` 仍可能提前把 AI 拉走。

6. 流程控制
-----------

- ``label \<名称\>`` —— 标记一个可跳转到的位置。
- ``goto \<名称\>`` —— 跳转到某个标签。``goto`` 也接受相对行偏移，例如
  ``goto -1`` （回退一行）。
- ``goto_random \<名称1\> \<名称2\> ...`` —— 在列出的标签中随机选一个跳转。
  非常适合让 AI 变得难以预测。

7. mod 示例（三档 + 分阵营脚本）
--------------------------------

以下是 ``ai.txt`` 节选::

    def tang_empire_easy
    constant_attacks 0
    get 9 villager 5 footman
    attack
    goto -1

    def tang_empire_hard
    constant_attacks 1
    get 9 villager 10 footman
    attack
    goto -1

以下是 ``rules.txt`` 中唐朝阵营的节选::

    def tang_empire
    class race
    peasant villagers
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

菜单显示三档；选唐朝 + 「中级」时运行 ``tang_empire_hard``。

8. 完整示例（原版五档之一）
---------------------------

::

    def advanced

    counter_skill 75
    watchdog 480
    constant_attacks 1
    research 1
    workers 18
    expand 2          ; 第二个基地，经济更强
    attack_ratio 150  ; 优势更小就敢推进

    label open
    get 9 peasant 6 footman 4 archer
    attack
    goto_random knights mixed

    label knights
    get 9 peasant 16 knight 10 archer 3 catapult
    attack
    goto open

    label mixed
    get 9 peasant 20 archer 12 knight 5 priest 4 catapult
    attack
    goto open

一行中 ``;`` 之后的内容都是注释，会被忽略。
