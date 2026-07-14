
模组制作指南
::::::::::::

.. contents::

mods
-----

游戏的规则和表现可以通过模组来更改。

模组是一个文件夹，其中可能包含 rules.txt、ai.txt、ui（及其本地化版本）。其目录树结构与 "res" 文件夹的结构相同。

模组存放在主文件夹的 "mods" 文件夹中，或用户文件夹的 "mods" 文件夹中。要激活某个模组，必须在 SoundRTS.ini 的 "mods =" 参数中引用它。
例如：mods = soundpack,mymod,my_other_mod

rules.txt 文件会对默认文件打补丁。例如，一个含有这两行的 rules.txt 文件："def peasant" 和 "decay 20"，会使任何农民在 20 秒后消失。

模组多语言（ui-xx）
>>>>>>>>>>>>>>>>>>>

模组目录结构与 ``res`` 相同，可在 ``ui/`` 旁增加本地化文件夹（``ui-zh``、``ui-fr``、``ui-de`` 等）。游戏根据 ``cfg/language.txt`` （或系统语言）自动加载对应语言；未翻译的条目回退到 ``ui/tts.txt``。

推荐目录 （以 ``mods/mymod/`` 为例）::

    ui/style.txt          ; title 7000
    ui/tts.txt            ; 7000 Pig Farm
    ui-zh/tts.txt         ; 7000 猪圈
    ui-fr/tts.txt         ; 7000 Ferme à porcs
    mod.txt               ; 可选：依赖与菜单显示名（见下）

可翻译内容 （模组激活后生效）：

- 单位/建筑/派系名称：``style.txt`` 中的 ``title \<ID\>`` + 各语言 ``tts.txt`` 中同 ID 的文本
- 单位简介：``intro \<ID\>`` + ``tts.txt``
- 模组内地图/战役：地图 ``title``/``intro`` 用 TTS 编号；战役文件夹可用 ``campaign.txt`` 的 ``title`` （与 ``res/single`` 战役相同）
- 整句翻译：在 ``tts.txt`` 中用等号，例如 ``objective be to eliminate the enemy = 目标为消灭敌人``

模组菜单显示名 （选项 → 模组，自 1.4.2.4 起）：

在 ``mod.txt`` 中增加 ``title`` 行，写法与 ``campaign.txt`` 相同——可用 TTS 编号或空格分隔的文字::

    title 7100

在 ``ui/tts.txt`` 与各 ``ui-xx/tts.txt`` 中定义该编号，例如 ``7100 Orc Faction Mod`` / ``7100 兽人模组``。未设置 ``title`` 时仍朗读文件夹名。

若暂不改 ``mod.txt``，也可在全局 ``res/ui-zh/tts.txt`` （或专用翻译 mod 的 ``ui-zh/tts.txt``）用词组映射文件夹名，例如 ``crazyMod9beta10 = 疯狂模组``。

说明：``rules.txt`` / ``ai.txt`` 无多语言版本；地图/战役子目录内的 ``ui-xx/style.txt`` 可能不被加载，但同目录 ``ui-xx/tts.txt`` 会加载。音效包（无 ``rules.txt`` 的 mod）在 `` 选项 → 音效包`` 菜单中同样支持 ``mod.txt`` 的 ``title`` 与各语言 ``tts.txt``。

仓库示例：``mods/orc/`` （多语言 ``ui-xx/tts.txt``）、``mods/prismalab/ui-fr/`` （法语 ``style.txt`` + ``tts.txt``）。

clear
>>>>>

要替换 rules.txt 或 style.txt 而非对其打补丁，请在文件顶部使用 "clear" 命令。这对 ai.txt 无效，
而且本来也不需要，因为在 ai.txt 中 def 命令会重写该 AI 的定义。

is_a
>>>>

在 style.txt 中 "is_a" 是继承另一个定义全部属性的方式，
而在 rules.txt 中，"is_a" 还用于确保城堡或要塞能允许市政厅所允许的内容。

注意：style.txt 和 rules.txt 中的继承树无需一致。

the rules
----------

从 SoundRTS 1.1 起，游戏规则存储在一个名为 rules.txt 的文件中。

faction
>>>>>>>

每个阵营都在 rules.txt 中定义。例如::

	def orc_faction
	class faction

注意："orc_faction" 名称以 "_faction" 结尾只是为了避免名称冲突。只要名称唯一，这个 "_faction" 后缀并非强制。

unit
>>>>

注意：单位也可以是建筑。

count_limit
============

SoundRTS 1.2 alpha 10 新增。

`count_limit <值>`

默认值为 0（无限制）。
当限制生效时，达到上限的单位类型将无法被训练、建造、召唤、扶起、复活或由触发器（add_unit）添加。
不过转化（conversion）不受影响。

mdg_projectile / rdg_projectile
=================================

SoundRTS 1.3.8.2 新增。SoundRTS 1.3.9.1 补充低击高限制。取代已废弃的 ``is_ballistic``。

``mdg_projectile 0|1``

``rdg_projectile 0|1``

默认值为 0。设为 1 时，对应攻击类型视为投射物：

- 单位位于高地时，攻击海拔较低的目标可获得额外射程（每 1 级高度差 +1 格射程）
- 非投射物单位不能从低处攻击高地上的 ground 目标，无论射程多远

迁移说明：原先使用 ``is_ballistic 1`` 的 mod 应改为 ``rdg_projectile 1`` (远程) 或 ``mdg_projectile 1`` (近战投射物，如投石)；两种攻击可分别配置。

远程投射物示例::

    def archer
    rdg 3
    rdg_range 4
    rdg_projectile 1

is_teleportable
================

SoundRTS 1.2 alpha 9 新增。

``is_teleportable 1``

该单位（或建筑）会受到传送效果或召回效果的影响。

hp_regen
=========

SoundRTS 1.2 alpha 11 新增。

`hp_regen <生命值回复速率>`

例如，使用 "hp_regen 0.15" 时，该单位每秒回复 0.15 点生命值。

mana_start
===========

SoundRTS 1.2 alpha 10 新增。

``mana_start 50``

在此示例中，该单位将以 50 法力（而非 mana_max）开局。mana_start 的默认值为 0。如果 mana_start 为 0 或负数，则改用 mana_max。

provides_survival
==================

SoundRTS 1.2 alpha 9 新增。

``provides_survival 1``

只要拥有至少一个 "provides_survival" 等于 1 的单位（或建筑），就能防止玩家在多人游戏中落败（单人战役除外）。受影响的触发器是 "no_building_left"。默认情况下只有建筑将此属性设为 1。建筑工地的该属性被设为 0 且无法更改。

storage_bonus
==============

`storage_bonus <资源 0 的加成> <资源 1 的加成> ...`

例如，"storage_bonus 0 1" 会为木材（第二种资源类型）带来 +1 加成。

加成归该单位的拥有者所有。
加成不叠加：每种资源类型只会应用最高的那个加成。

damage_vs
==========

注意：自 SoundRTS 1.4 起，单一的 ``damage`` / ``armor`` 体系
已被拆分的近战/远程体系（``mdg`` / ``rdg`` / ``mdf`` / ``rdf`` ...）取代。
参见下文的 `Combat system (since 1.4)`_。保留旧的 ``damage_vs`` 文档仅供参考及旧模组使用。

（针对特定单位的伤害）

`damage_vs [<类型名列表> <伤害>] ...`

定义针对某些单位类型的特定伤害。
默认值在 unit.damage 中定义。

一种对骑士更高效、对步兵或农民效率更低的长枪兵示例：

`damage 2 ; 默认伤害`

``damage_vs knight 7 footman peasant 1``

ability
>>>>>>>

注意：自 SoundRTS 1.4 起，各种能力统一归于 ``class skill``\ `` （参见下文`` `Skills (class skill)``_``）`。这里记录的 ``effect`` 属性仍适用于技能以及 ``class effect`` 定义。

effect
=======

`effect <效果类型> [参数]`

默认值：（无）

效果是某项能力的属性。当某单位使用某项能力时，该效果会生效，除非未指定任何效果类型。

其他属性可以修改效果：effect_target_ 和 effect_range_。

apply_bonus
^^^^^^^^^^^^

`effect apply_bonus <属性名>`

提升受影响单位的某项属性。其数值定义在该单位名为 "<属性名>_bonus" 的属性中。
例如，"effect apply_bonus damage" 会在每个受影响单位的定义中查找名为 "damage_bonus" 的属性。
这样，享受相同升级的不同单位可以拥有不同的加成数值。

bonus
^^^^^^

`effect bonus <属性名> <值>`

将受影响单位的某项属性提升指定数值。

至少以下属性应当有效：damage、armor、range、heal_level、speed、hp_max（不过老单位的 hp 不会被更新到 hp_max）。
food_cost 和 food_provided 大概无法正常工作。

conversion
^^^^^^^^^^^

``effect conversion``\ （无参数）

将目标移入施法者的部队。

如果目标不是施法者的敌人，则什么都不会发生。

相关属性的允许取值：

* effect_target：ask
* effect_range：square、nearby、anywhere

TODO：添加一个 <limit>，以便选取目标格子中的单位（而不必瞄准某个单位）

raise_dead
^^^^^^^^^^^

`effect raise_dead <存活时长（秒）> <单位类型与数量>`

按单位列表的顺序，从目标格子里的尸体中在该格子创建所需单位。如果尸体不足，列表末尾的单位将不会被创建。除非 <存活时长> 设为 0，否则这些单位会在 <存活时长> 秒后消失。

如果目标格子里没有尸体，该命令将不会执行。

相关属性的允许取值：

* effect_target：self、ask、random
* effect_range：square、nearby、anywhere

recall
^^^^^^^

``effect recall``\ （无参数）

类似传送。把玩家位于目标格子的单位传送回施法者所在的格子。建筑不受影响。盟友单位也不受影响。

如果目标格子里没有单位，该命令将不会执行。

相关属性的允许取值：

* effect_target：ask、random
* effect_range：nearby、anywhere

resurrection
^^^^^^^^^^^^^

`effect resurrection <上限>`

复活躺在目标格子里、属于施法者部队的尸体，最多复活 <上限> 个单位。最旧的尸体最先被复活。生命值恢复到其最大值的三分之一。

如果目标格子里没有同一部队单位的尸体，该命令将不会执行。

相关属性的允许取值：

* effect_target：self、ask、random
* effect_range：square、nearby、anywhere

summon
^^^^^^^

`effect summon <存活时长（秒）> <单位类型与数量>`

在目标格子创建所需单位并将其加入施法者的部队。除非 <存活时长> 设为 0，否则被召唤的单位会在 <存活时长> 秒后消失。

可选技能属性（菌毯肿瘤示例）::

    summon_requires_build_field creep
    summon_requires_marked_field 1

``summon_requires_marked_field 1`` 要求目标格为已标记 建造场（仅实时供能不够）。女王生成肿瘤时不写此项。

deploy
^^^^^^^

``effect deploy \<存活时长（秒）\> [\<数量\>] \<效果类型\>``

在目标格子部署 ``class effect`` 实体（范围伤害、治疗区域、侦测等），持续指定秒数后消失。
与 ``effect summon`` 不同：仅用于 ``class effect``，属性界面显示伤害/治疗参数，而非「召唤」。

示例（核打击、灵能风暴）::

    effect deploy 5 sc_nuclear_blast
    effect deploy 3 sc_psi_storm_fx

可选数量（同一格多个效果实体）::

    effect deploy 5 2 greek_fire

同样支持 ``summon_requires_build_field`` / ``summon_requires_marked_field``。

相关属性的允许取值：

* effect_target：self、ask、random
* effect_range：square、nearby、anywhere

harm_target（since 1.4.4.6）
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

单体伤害。两种语法：

* **固定真实伤害**（绕过护甲）：``effect harm_target <数值>``
* **战斗管线伤害**（护甲、暴击、溅射等）：``effect harm_target mdg`` 或 ``effect harm_target rdg``

技能上的非零 ``mdg`` / ``rdg`` 等战斗属性会覆盖施法者。示例见 ``mods/wuxia/rules.txt`` 的 ``skill_lipi`` / ``skill_lipi_mdg``。

可用 ``harm_target_type`` 过滤目标（默认仅敌人）；详见 `技能专篇 <skills-and-effects.htm>`_。

harm_area（since 1.4.4.6）
^^^^^^^^^^^^^^^^^^^^^^^^^^^

范围伤害：

* **固定真实伤害**：``effect harm_area <伤害> <半径>``
* **战斗管线**：``effect harm_area mdg <半径>`` 或 ``effect harm_area rdg <半径>``

半径可省略，此时使用技能的 ``effect_radius``。示例：``skill_heng_sao``、``skill_heng_sao_mdg``（wuxia mod）。

burst（since 1.4.4.6）
^^^^^^^^^^^^^^^^^^^^^^^

技能连击（**不同于**单位 ``damage_seq`` 连发攻击，见 `burst-attacks.htm <../player/burst-attacks.htm>`_）::

    effect burst mdg <次数> (interval <秒>) (window <秒>)
    effect burst rdg <次数> (delays <t1> <t2> …)

伤害取自技能或施法者的 ``mdg`` / ``rdg``。示例：``skill_jifengci``（wuxia mod）。

push（since 1.4.4.6）
^^^^^^^^^^^^^^^^^^^^^

``effect push <距离>`` — 击退敌方目标并寻找可站立格。示例：``skill_moli_dan``（wuxia mod）。

buffs / debuffs（技能施加）
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``effect buffs <buff名> …`` / ``effect debuffs <debuff名> …``

对目标施加增益或减益（``debuffs`` 仅对敌人）。伤害反弹无独立 ``effect reflect``，须在 buff 上写 ``reflect_percent`` 再用 ``effect buffs`` 施加（wuxia ``b_douzhuan``）。

完整说明见 `技能专篇 <skills-and-effects.htm>`_。

teleportation
^^^^^^^^^^^^^^

``effect teleportation``\ （无参数）

把玩家位于施法者格子里的单位移动到目标格子。建筑不受影响。盟友单位也不受影响。

如果目的地与施法者所在格子相同，则什么都不会做。

相关属性的允许取值：

* effect_target：ask、random
* effect_range：nearby、anywhere

effect_target
==============

`effect_target <选择方式>`

决定如何选择目标。

默认值：self

可能取值：

* self：目标将是施法者（如果目标必须是一个地点，则为施法者所在位置）
* ask：用户界面会要求选择一个目标
* random：游戏会随机选择一个格子作为目标

effect_range
=============

`effect_range <距离>`

决定施法者与目标之间的距离。

默认值：6

特殊值：inf（无限）

如果当前距离大于所需距离，施法者会尝试移动到更近的位置，并从那里使用该能力。

effect_radius
==============

`effect_radius <距离>`

决定效果作用范围的半径。范围的中心是目标。

默认值：6

特殊值：inf（无限）

.. _combat-system-since-1-4:

Combat system (since 1.4)
--------------------------

自 1.4 起，最终伤害为叠加式：``final_mdg = mdg + mdg_vs`` （``rdg``、``mdf``、``rdf`` 同理）。当基础伤害为 0 且在 ``def parameters`` 中 ``minimal_damage`` 为 0 时，该单位将不会攻击。

主要近战/远程属性：

- ``mdg`` / ``rdg``：基础伤害
- ``mdg_vs`` / ``rdg_vs``：针对特定单位类型的加成
- ``mdf`` / ``rdf``：防御
- ``mdg_range`` / ``rdg_range``、``mdg_cd`` / ``rdg_cd``、``mdg_ready`` / ``rdg_ready``
- ``mdg_projectile`` / ``rdg_projectile``：投射物标志（高地射程加成、低击高规则）
- ``mdg_splash`` / ``rdg_splash``、``mdg_radius`` / ``rdg_radius``、``mdg_splash_decay``
- ``mdg_targets`` / ``rdg_targets``：``ground``、``air``、``unit``、``building`` 或类型名
- ``mdg_crit`` / ``rdg_crit``、``mdg_crit_rate`` / ``rdg_crit_rate``、``crit_vs``
- ``mdg_piercing`` / ``rdg_piercing``\ `` （无视护甲百分比）``、``piercing_vs``
- ``mdg_explode`` / ``rdg_explode``、``exp_dgf``、``exp_hp_cost``、``mdg_explode_vs``
- 单位**所在地形**上的修正（自 1.4.5.0，1.4.5.1 起百分比）：``mdg_on_terrain`` / ``rdg_on_terrain``、``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``、``charge_*_terrain`` 等使用小数百分比（``.33`` = ±33%%）；地形 ``class terrain`` 上可用 ``speed_vs`` / ``cover_vs`` / ``dodge_vs`` / ``mdg_vs`` 等按单位类型修正。详见 ``building-land-terrain.rst`` *单位在地形上的战斗修正*

自动威胁度 / 选敌优先级（自 1.4.5.2）
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

单位属性 ``menace`` 不再等于「伤害」。未在 rules 中写死绝对值时，引擎用**多维战斗评分**作为威胁度，用于：

- 单位自动选敌（按威胁从高到低；非 ``timers`` 电脑还可与 ``mdg_vs``/``rdg_vs`` + ``counter_skill`` 加权，见 ``aimaking.rst``）
- 格内敌方威胁求和等 AI 决策

**自动评分纳入的维度**（取主武器：``mdg``/``rdg`` 中伤害较高的一路）：

- 伤害、命中（``mdg_cover``/``rdg_cover``，0 视为 100%%）、冷却（``*_cd``）、前摇（``mdg_ready``/``rdg_ready``，不是弹道 ``*_delay``）
- 生命（当前 ``hp``，否则 ``hp_max``）、防御（``max(mdf, rdf)``）、闪避（``max(mdg_dodge, rdg_dodge)``）
- 射程、移速

大致：先算有效 DPS（伤害 × 命中 /（冷却+前摇）），再乘生存与射程/移速修正。

**rules 可选覆盖**（单位 def）：

======= ================== ==========================================================
字段      类型               含义
======= ================== ==========================================================
``menace`` 绝对值            固定威胁；**不**随升级/血量变化；盖掉自动多维
``menace_mult`` 权重（默认 1）  乘在自动多维底分上（随伤害升级等仍会变）
``menace_vs`` 绝对值 vs 类型   对该观察者类型（及 ``is_a``）的固定威胁；选敌时优先于下两项
``menace_mult_vs`` 权重 vs 类型 对该观察者：自动多维底分 × 权重
======= ================== ==========================================================

查有效威胁（``menace_versus``）顺序：``menace_vs`` → ``menace_mult_vs`` → 全局 ``menace``/``menace_mult``/自动分。

示例::

    def knight
    mdg 6
    menace_mult 1.5

    def archer
    rdg 5
    menace_vs knight 3
    menace_mult_vs mage 1.2

**parameters 可调权重**（只调「生存/机动」等项的比重；伤害+冷却+前摇+命中始终进入 DPS 核心，无单独旋钮）::

    def parameters
    menace_armor_weight 1
    menace_dodge_weight 1
    menace_range_weight 0.15
    menace_speed_weight 0.2
    menace_hp_ref 50

- ``menace_armor_weight`` / ``menace_dodge_weight``：防御、闪避在生存项中的权重（默认 1）
- ``menace_range_weight`` / ``menace_speed_weight``：每单位射程、移速的加成系数（默认 0.15 / 0.2）
- ``menace_hp_ref``：血量归一参考（默认 50），用于把综合分压到与旧「伤害威胁」相近的量级

建议：会随科研成长的战斗单位优先用 ``menace_mult`` / ``menace_mult_vs``；仅当刻意固定优先级时才写绝对 ``menace`` / ``menace_vs``。

冲锋与反冲锋（自 1.4.0.1 起）

冲锋：配置了冲锋属性的单位在有效距离内接敌时，可发动一次高伤害冲锋攻击。冲锋完成后进入
冷却，期间只造成普通 ``mdg`` / ``rdg`` 伤害；冷却结束后须将单位拉开至超过冲锋有效距离，
才能对同一目标再次冲锋。

冲锋伤害（加法，非倍率）::

    冲锋伤害 = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)

例如 ``mdg 6, charge_mdg 2`` 时基础部分为 ``6 + 2 = 8``，再按与目标距离在
``charge_mdg_dist`` 内做衰减（近处约 50%，远处接近 100%）。远程同理，将 ``mdg`` 换为
``rdg``、``charge_mdg`` 换为 ``charge_rdg``。

冲锋属性（近战 / 远程各有一套，远程将 ``mdg`` 换为 ``rdg``）：

- ``charge_mdg`` / ``charge_rdg`` — 冲锋额外伤害加值
- ``charge_mdg_vs`` / ``charge_rdg_vs`` — 对特定单位类型的冲锋加值
- ``charge_mdg_cd`` / ``charge_rdg_cd`` — 冲锋冷却（毫秒）
- ``charge_mdg_dist`` / ``charge_rdg_dist`` — 冲锋有效距离上限
- ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` — 冲锋最小触发距离（0 表示不限）
- ``charge_mdg_splash`` / ``charge_rdg_splash`` — 冲锋溅射伤害
- ``charge_mdg_radius`` / ``charge_rdg_radius`` — 冲锋溅射半径
- ``charge_mdg_splash_decay_min`` / ``charge_rdg_splash_decay_min`` — 溅射最小衰减（0.0–1.0）

示例（战役骑士）::

    def knight
    mdg 3
    charge_mdg 2
    charge_mdg_cd 10
    charge_mdg_dist 15
    charge_mdg_min_dist 3
    charge_mdg_splash 1
    charge_mdg_radius 1
    charge_mdg_splash_decay_min 0.5

反冲锋：专门克制冲锋。当具有反冲锋的单位在有效距离内拦截 正在冲锋的敌人时，会打断对方
冲锋（对方本次按普通攻击结算），并对攻击者造成反冲锋伤害。

反冲锋伤害（加法）::

    反冲锋伤害 = 对方 (mdg/rdg + mdg_vs/rdg_vs) + 对方 (charge_mdg/charge_rdg + charge_mdg_vs/charge_rdg_vs)
               + 自身 (op_charge_mdg/op_charge_rdg + op_charge_mdg_vs/op_charge_rdg_vs)

反冲锋属性：

- ``op_charge_mdg`` / ``op_charge_rdg`` — 反冲锋额外伤害加值
- ``op_charge_mdg_vs`` / ``op_charge_rdg_vs`` — 对特定攻击者类型的加值
- ``op_charge_mdg_cd`` / ``op_charge_rdg_cd`` — 反冲锋冷却
- ``op_charge_mdg_dist`` / ``op_charge_rdg_dist`` — 反冲锋有效距离（0 表示不限）

``音效（``style.txt``）`：``charge_success``、``charge_failed``、``op_charge``。战斗相关还有
``critical_hit``、``piercing_triggered``。

注意：自伤不会触发冲锋；地面冲锋溅射不影响空中单位。

连发 / 序列攻击（``damage_seq``，自 1.3.8.2 起，1.4.3.6 增强）
----------------------------------------------------------------

一次攻击可在冷却周期内快速连击多次 （类似帝国时代诸葛弩）。须先定义 ``mdg`` / ``rdg``，再写
``damage_seq``：

``damage_seq mdg|rdg \<次数\> [(damage d1 d2 ...)] [(interval 秒)]``

- 手动分段：``(damage 6 3 3)`` — 各段为整数，总和须等于 ``mdg`` / ``rdg`` 基础值
- 自动均分 （1.4.3.6 起）：省略 ``(damage ...)`` 时按次数均分基础伤害（支持小数，如
  ``rdg 7.5`` 配 3 次 → 每发 2.5）
- 间隔：``(interval 0.25)`` 为每发之间的秒数；多段且未写 interval 或为 0 时默认 0.25 秒
- 上限：单次攻击最多 6 段
- 判定：每段独立计算命中、暴击、debuff
- 冷却：``mdg_cd`` / ``rdg_cd`` 在`` 整轮连发结束后``才开始
- 音效：每发触发 ``launch_mdg`` / ``launch_rdg``；可在 ``style.txt`` 写多个音效 ID
  （如 ``launch_rdg 1042 1042 1042``）

远程连发示例（内置 ``repeating_crossbowman`` 诸葛弩手）::

    def repeating_crossbowman
    rdg 6
    rdg_cd 2.5
    rdg_range 4
    rdg_projectile 1
    damage_seq rdg 3 (interval 0.25)

近战手动分段示例::

    def footman
    mdg 12
    mdg_cd 1.5
    mdg_range 6
    damage_seq mdg 3 (damage 6 3 3) (interval 0.2)

详见 ``../player/burst-attacks.htm``。

Weapons and armor (since 1.4.1.3)
----------------------------------

武器（``class weapon``）和护甲（``class armor``）承载战斗数值。单位引用它们::

    def footman
    class soldier
    weapons sword bow     ; 第一件武器为默认/主武器
    auto_weapon_switch 1  ; 1 = 战斗中按射程自动换武器
    armor light_armor

玩家用 A / Shift+A 或 B 然后 X 切换武器。手动切换优先于自动切换。
单位与已装备物品上的数值相加。武器像单位一样支持继承。

Buffs and debuffs (since 1.3.9.8, extended in 1.4.1.7)
-------------------------------------------------------

通过 ``buffs`` / ``debuffs`` 附加到攻击上，或通过技能的 ``effect buffs`` / ``effect debuffs`` 附加。

``reflect_percent``（整数百分比）可在 buff 上配置伤害反弹，由技能 ``effect buffs`` 施加；无独立 ``effect reflect``。示例：``mods/wuxia/rules.txt`` 的 ``b_douzhuan``。

多属性增益示例::

    def HealEnhancementBuff
    class buff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1

触发模式：

1. 默认 — 攻击命中后触发
2. ``is_active 1`` — 发起攻击时触发（主动型）
3. ``is_passive 1`` — 遭受攻击时触发（被动型），配合 ``trigger_condition``\ `` （例如`` ``hp \< 20``\ `）` 和 ``passive_trigger_rate``

触发几率（百分比，默认沿用普通攻击率）：

- ``mdg_trigger_rate`` / ``rdg_trigger_rate`` — 普通伤害触发
- ``charge_mdg_trigger_rate`` / ``charge_rdg_trigger_rate`` — 冲锋伤害触发
- ``op_charge_mdg_trigger_rate`` / ``op_charge_rdg_trigger_rate`` — 反冲锋触发

.. _skills-class-skill:

Skills (class skill)
---------------------

用 ``class skill`` 定义技能，取代 ``class ability``::

    def fireball
    class skill
    mana_cost 50
    cost 10 0
    time_cost 30
    effect harm_target 60
    effect_target ask
    effect_range 12
    cooldown 10

``can_use_tech`` 用于升级；``can_use_skill`` 用于技能。

1.4.4.6 起支持 ``harm_target``、``harm_area``、``burst``、``push``、``effect buffs`` / ``debuffs`` 等通用效果；官方演示见 ``mods/wuxia/rules.txt``。详见 `技能 / 治疗 / 效果 <skills-and-effects.htm>`_。

**技能触发方式（since 1.4.4.6）**

学会的技能写在 ``can_use_skill``。手动与自动可并存：

+------------------+--------------------------------------------------+
| ``manual_use 1`` | 出现在命令菜单（默认 1）                         |
+------------------+--------------------------------------------------+
| ``auto_trigger 1`` | 战斗中自动触发                               |
+------------------+--------------------------------------------------+
| ``trigger_timing`` | 见下表                                       |
+------------------+--------------------------------------------------+

+-----------------------+----------------------------------------------+---------------------------+
| ``trigger_timing``    | 时机                                         | 旧列表（兼容）            |
+=======================+==============================================+===========================+
| ``on_hit`` （默认）   | 命中敌人后                                   | ``active_trigger_skills`` |
+-----------------------+----------------------------------------------+---------------------------+
| ``on_attack``         | 发起攻击时附加，普攻继续                     | ``attack_trigger_skills`` |
+-----------------------+----------------------------------------------+---------------------------+
| ``on_attack_replace`` | 发起攻击时释放，替代本次普攻                 | ``attack_replace_skills`` |
+-----------------------+----------------------------------------------+---------------------------+
| ``on_damaged``        | 被敌人命中时（被动）                         | ``passive_trigger_skills``|
+-----------------------+----------------------------------------------+---------------------------+

触发概率：``active_trigger_rate`` / ``passive_trigger_rate`` （1–100）；近战/远程可分别写 ``mdg_trigger_rate`` / ``rdg_trigger_rate`` （>0 时覆盖 active 率）。

触发条件：``trigger_condition hp < 30`` （``hp``/``mana`` 按百分比比较）；或简写 ``hp_threshold 30``。**仅** ``on_hit`` / ``on_damaged`` 检查条件；``on_attack`` / ``on_attack_replace`` 不检查。

自动触发同样消耗法力、进入冷却；``ready`` 前摇与手动释放一致。

示例（受击被动）::

    def skill_thorns
    class skill
    auto_trigger 1
    manual_use 0
    trigger_timing on_damaged
    passive_trigger_rate 30
    effect harm_target 10
    effect_target ask

示例（替代普攻）::

    def skill_flame_strike
    class skill
    auto_trigger 1
    trigger_timing on_attack_replace
    active_trigger_rate 100
    effect harm_target mdg
    effect_target ask
    effect_range 1
    mdg 15
    mana_cost 10
    cooldown 3

完整说明与四种 timing 的更多示例见 `技能专篇 <skills-and-effects.htm>`_ 的「技能触发方式」一节。

Effects (class effect, since 1.4.1.7)
--------------------------------------

伤害与治疗拆分为详细参数::

    def exorcism
    class effect
    harm_level 2
    harm_cd 7.5
    harm_radius 6
    harm_target_type undead
    debuffs b_slow

同理：``heal_level``、``heal_cd``、``heal_radius``、``heal_target_type``；
``hp_regen_cd``、``mana_regen_ready`` 等。

Phase system (since 1.4.2.4)
-----------------------------

``class phase`` 在不升级基地的情况下推进游戏时代::

    def dark_age
    class phase
    cost 0 0
    time_cost 0

    def feudal_age
    class phase
    cost 10 15
    time_cost 130
    phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
    units_auto_upgrade 0
    phase_targets soldier

``phase_targets`` 可选，控制哪些单位获得 ``phase bonus`` 中的非成本项加成（成本类加成始终作用于玩家全局）。留空表示所有单位受益。可写类别名（``soldier``\ 、``worker``\ 、``building``\ 、``unit`` 等）、具体单位名（``footman knight``），或 ``is_a`` 继承链中的类型名；任一正向项命中即匹配。前缀 ``-`` 表示排除，例如 ``phase_targets -building`` 表示除建筑外的所有单位；可与正向项混用，例如 ``phase_targets soldier -footman``。

在建筑上::

    can_advance feudal_age

阶段使用 ``can_advance``\ `` （而非`` ``can_research``\ `）`。在建筑上按 V 查看当前阶段。

在 ``def parameters`` 中设置 ``hide_locked_commands 1`` 可隐藏尚未满足要求的命令。

Economy (since 1.4.0.x)
------------------------

``population_cost`` 取代了 ``food_cost``。建筑可以生产或存放资源::

    auto_production 1       ; 自动生产（气矿等）；资源未满即可重启
    manual_production 1     ; 手动开始生产
    auto_cultivate 1        ; 自动耕种（农田）；储量抽空后才重启
    is_gather 1             ; 产出进入建筑储量，由工人运回基地
    resource_volume_max 8
    resource_volume_start 0
    production_type resource2
    production_time 18      ; 攒满一批资源所需秒数
    production_qty 8        ; 每轮产出数量（存入建筑储量）
    extraction_time 2       ; 工人从建筑开采耗时（秒）
    extraction_qty 8        ; 工人单次运载量

无 ``is_gather`` 时，无论自动还是手动生产，``production_type`` 每轮产出都会直接进入玩家资源库存 （如 ``gold_house``）::

    auto_production 1
    manual_production 1
    production_type resource1
    production_time 100
    production_qty 200

需要产出可拾取物品时，使用 ``production_item`` （与 ``production_type`` 二选一）::

    production_item gold_pile
    production_qty 1

| 属性 | 说明 |
| --- | --- |
| ``production_type`` | 生产的资源类型（与 ``production_time``\ 、``production_qty`` 共同定义生产能力） |
| ``production_time`` | 完成一轮生产所需时间（秒） |
| ``production_qty`` | 每轮产出量；无 ``is_gather`` 时入库玩家资源；有 ``is_gather`` 时写入建筑 ``resource_qty`` |
| ``auto_production`` | 为 ``1`` 时显示自动生产 命令；完成后自动开始下一轮；气矿 用此项（非 ``auto_cultivate``） |
| ``manual_production`` | 为 ``1`` 时显示手动生产 命令；每轮完成后需再次点击；与 ``auto_production`` 独立，须分别开启 |
| ``auto_cultivate`` | 农田等 ``is_gather`` 建筑的自动耕种；与 ``auto_production`` 对应 |
| ``manual_cultivate`` | 农田等的手动耕种；与 ``manual_production`` 对应，须单独设为 ``1`` |
| ``production_item`` | 生产的物品类型名；完成后在建筑旁生成可 ``pickup`` 的物品 |
| ``is_gather`` | 产出不进玩家库存，先存入建筑；工人 ``can_gather_building`` 该建筑类型后运回仓库 |
| ``resource_volume_max`` | 建筑内最大储量（如气矿 8） |
| ``resource_volume_start`` | 建成时初始储量（``0`` 表示空） |
| ``extraction_time`` / ``extraction_qty`` | 工人从建筑（或矿床）开采的耗时与单次数量 |

.. note::

   ``auto_production`` 与 ``manual_production`` 为两个独立开关，可同时为 ``1`` （如 ``gold_house``）。``auto_production`` 未写或为 ``0`` `` 不会``自动视为手动生产；需要手动命令时必须写 ``manual_production 1``。农田侧同理：``auto_cultivate`` / ``manual_cultivate`` 独立配置。

.. note::

   ``is_create`` 已废弃：不再生成地面 ``class resource`` 堆。请用 ``production_type`` （直接入库）、``is_gather`` （存入建筑）或 ``production_item`` （生成物品）。

``class resource`` 与 ``class deposit`` 相互独立。地图矿床::

    mineral_field 1500 a1    ; 矿物矿床，1500 储量
    geyser 1 e1              ; 瓦斯气泉（建造气矿后移除）

气矿建筑须建在指定矿床上::

    requires_deposit geyser
    is_buildable_anywhere 0

完整示例见 ``mods/starcraft/rules.txt`` 中的 ``sc_gas_building`` / ``assimilator``；玩家说明见 ``../player/starcraft-resources.htm``。属性界面（V）新增 需要矿床 （``requires_deposit``）；生产时间/数量等沿用既有生产属性显示。

Heroes (since 1.4)
-------------------

任意 :strong:```rules.txt`` 均可定义英雄单位（基础规则、模组、战役包、联机地图包等）。在对战电脑、随机图、联机、战役等模式中均生效：杀敌获经验、按 ``xp_thresholds`` 升级、``is_revivable`` 复活、背包装备等。跨章存档（下一节 ``campaign_carryover``）才是仅单人战役的附加功能。

联机示例：``res/multi/td2/rules.txt`` 中的 ``hero`` / ``hero_knight`` 等。

::

    def hero
    class soldier
    global_count_limit 1
    is_revivable 1
    revival_time 10
    xp_thresholds 200 500 900
    hp_max_per_level 1000
    mdg_per_level 100
    resource_rewards 300
    xp_reward 100

``等级与经验（``level`` / ``xp`` / ``xp_thresholds`` / ``xp_threshold_growth``）``

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| ``xp_thresholds`` | （空） | 升级所需累计经验列表。第 1 个值为升到 2 级（或从 0 级升到 1 级）的门槛；其后依次为 3 级、4 级…… |
| ``max_level`` | （无） | 英雄等级上限。与 ``xp_threshold_growth`` 配合时，加载规则时自动生成 ``max_level - 1`` 个门槛 |
| ``xp_threshold_growth`` | （无） | 按公式自动生成 ``xp_thresholds`` （见下表）。须同时写 ``max_level``；与手写 ``xp_thresholds`` 二选一（手写优先） |
| ``level`` | ``1`` | 开局等级。``\> 1`` 时按 ``*_per_level`` 逐级补全属性并解锁 ``level_skills`` |
| ``xp`` | ``0`` | 开局累计经验（可选） |
| ``level_up_heal_full`` | ``0`` | ``1`` = 每次升级后生命与法力回满；``0`` = 仅把 ``hp_max_per_level`` / ``mana_max_per_level`` 增量加到当前值（默认） |
| ``level_up_reset_xp`` | ``0`` | ``1`` = 每次升级后当前经验清零；``0`` = 保留累计经验（默认）。开启时 ``xp_thresholds`` 宜写每级所需经验，而非累计值 |

- 最高等级 = ``len(xp_thresholds) + 1`` （例如 9 个阈值 → 最高 10 级）。
- 选中单位时（Tab 状态）：定义了 ``xp_thresholds`` 的英雄始终播报等级（含 1 级、0 级）；经验显示为 ``当前经验/下一级门槛`` （0 级时下一级门槛为 ``xp_thresholds`` 第 1 项）。
- 仅写 ``xp_thresholds`` （或 ``xp_threshold_growth`` 展开后）且不写 ``level`` → 默认 1 级 开局；写 ``level 0`` 可从 0 级成长。

:strong:```xp_threshold_growth`` 曲线类型`` （第 ``i`` 个门槛，``i`` 从 0 起，对应升到 2 级、3 级……）

| 类型 | 写法 | 公式 |
| --- | --- | --- |
| 线性 | ``linear BASE STEP`` | ``BASE + STEP × i`` |
| 二次 | ``quadratic BASE A B`` | ``BASE + A×i + B×i²`` |
| 多项式 | ``polynomial c0 c1 c2 …`` | ``c0 + c1×i + c2×i² + …`` |
| 几何 | ``geometric FIRST RATIO`` | ``FIRST × RATIO^i`` （``RATIO`` 可写小数，如 ``1.08``） |

示例（100 级英雄，线性累计经验）::

    def long_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50
    hp_max_per_level 30
    mdg_per_level 2

示例（雷纳式二次曲线，等价于 ``40 90 160 250 …``）::

    def raynor_curve
    class soldier
    max_level 10
    xp_threshold_growth quadratic 40 40 10
    hp_max_per_level 30

示例子类型只改等级上限（继承父 def 的 ``xp_threshold_growth``）::

    def base_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50

    def short_campaign_hero
    is_a base_hero
    max_level 20

示例（0 级开局、手写多级阈值）::

    def raynor
    is_a footman
    xp_thresholds 40 90 160 250 360 490 640 810 1000
    hp_max_per_level 30
    mdg_per_level 2
    level 0

示例（升级回满生命/法力）::

    def raynor
    is_a footman
    xp_thresholds 40 90 160
    hp_max_per_level 30
    level_up_heal_full 1

示例（3 级开局，带初始经验）::

    def veteran_hero
    is_a knight
    xp_thresholds 200 500 900
    hp_max_per_level 20
    level 3
    xp 500

战役跨章英雄携带（规则驱动）
--------------------------------

在上一节已定义的英雄 def 上再加 ``campaign_carryover 1``\ 。仅 单人战役在通关时把进度写入 ``user/campaigns.ini``\ ，下一关开局自动恢复（失败重打不覆盖）。合作战役不支持。

::

    def my_hero
    is_a knight
    campaign_carryover 1
    campaign_carryover_id my_hero
    campaign_carryover_stats 1
    campaign_carryover_inventory 1
    inventory_capacity 8

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| ``campaign_carryover`` | ``0`` | ``1`` = 启用跨章存档 |
| ``campaign_carryover_id`` | def 名 | 存档键 ``hero_\<id\>\_xp`` / ``\_level`` / ``\_inventory`` |
| ``campaign_carryover_stats`` | ``1`` | 等级与经验 |
| ``campaign_carryover_inventory`` | ``1`` | 背包物品 |

子版本（``raynor7 is_a … raynor``）共用父类型存档键。只带经验：``campaign_carryover_inventory 0``\ ；只带背包：``campaign_carryover_stats 0``\ ；完全不跨章：不写 ``campaign_carryover 1``\ 。

``campaign.txt`` 可选 ``hero_min_level 13:2 16:3 …`` 指定进入某章后的最低等级。

与 ``campaign_flag`` / ``add_inventory_item`` 独立：剧情信物、结盟等仍用地图触发器。详见 ``mod/战役跨章英雄携带说明.htm``\ 。

运输容器（自 1.4.4.9 起字段重命名；旧名仍兼容）
------------------------------------------------

带 ``transport_capacity`` 的单位/建筑可作为运输容器。相关属性：

| 字段 | 作用 | 示例 |
| --- | --- | --- |
| ``passenger_attack_types`` | 容器内可攻击外部目标的单位类型 | ``passenger_attack_types archer knight`` 或 ``all`` |
| ``load_bonus`` | 每装载 1 名单位 → **容器**获得属性 | ``load_bonus speed 0.5 mdg 2`` |
| ``passenger_bonus`` | 进入容器后 → **乘客**获得属性（卸载回滚） | ``passenger_bonus rdg_range 1 mdg 2`` |

完整示例::

    def flyingmachine
    class soldier
    transport_capacity 8
    passenger_attack_types knight archer
    load_bonus speed 0.5
    passenger_bonus rdg_range 1

    def wall
    class building
    transport_capacity 4
    passenger_attack_types archer catapult
    passenger_bonus mdg 2

- 未写 ``passenger_attack_types`` 时，容器内单位默认不能攻击外部目标。
- ``load_bonus`` 与 ``passenger_bonus`` 可叠加使用。

Items (since 1.4.1.3)
----------------------

::

    def magic_sword
    class item
    consume_on_pickup 0
    buffs power_buff
    resource_rewards resource1 50

``is_loot 1`` 在携带者死亡时掉落该物品。

``物品音效（``style.txt``，自 1.4.4.6 起支持使用音效）``

| 时机 | 物品 ``style.txt`` | 单位 ``style.txt`` | 全局默认（``def thing``） |
| 拾取 | ``on_pickup`` | ``pickup_\<物品type\>`` | ``pickup`` |
| 丢弃 | ``on_drop`` | ``drop_\<物品type\>`` | ``drop`` |
| 使用 | ``use`` / ``on_use`` | ``use_\<物品type\>`` | ``item_used`` |

物品上（``use`` 与 ``on_use`` 等价；多个 ID 随机播放）::

    def zhuiri_jianfa_book
    title 7754
    pickup 1506
    use 1506

单位上::

    def raynor
    use_zhuiri_jianfa_book 1506

全局默认::

    def thing
    item_used 1194 1195 1196

继承链（``is_a``）与 ``on_pickup`` / ``on_drop`` 相同：子类型可覆盖父类型音效。

背包与可装备物品（自 1.4.3.1 起）
----------------------------------

单位需要 ``inventory_capacity``\ > 0 才能持有物品。每件物品占一格（``transport_volume``\ 已定义，但当前容量按物品件数 计算，与 ``transport_volume``\ 无关）。

两套装备系统

内置武器 / 内置护甲（传统）：

::

    def footman
    weapons sword          ; class weapon 类型
    armor footman_armor    ; class armor 类型

- 武器走 ``class weapon``\ 系统，护甲走 ``class armor``\ 系统。
- 不会自动出现在背包里。
- 在装备栏中显示为「内置武器 / 内置护甲」，不能通过界面装备、卸下或丢弃。

背包物品装备（同型模型）：同一 ``type_name``\ 可定义为 ``class item``\ ，并加上：

::

    def sword
    class item
    equippable_as_weapon 1
    mdg 3.5
    mdg_bonus 2.5
    mdg_cd 1.5
    mdg_range 1
    transport_volume 1
    can_use_tech melee_weapon

    def footman_armor
    class item
    equippable_as_armor 1
    mdf 0.5
    mdf_bonus 1
    rdf_bonus 1
    can_use_tech melee_armor

物品进入单位 ``inventory``\ 后，可通过背包或装备栏装备；数值（``mdg``\ 、``mdf``\ 等）在装备时套用到单位身上，卸下后还原。

装备切换规则

当单位同时配置了内置装备与 item 装备 时：

- 内置装备始终优先出厂装备；item 装备进入背包。
- ``spawn_weapons_equipped 1``\ （默认）时：item 出厂武器留在背包且无法手动装备；``spawn_weapons_equipped 0``\ 时允许手动装备。
- 内置装备只能与内置装备切换；item 装备只能与 item 装备切换；二者 不能互相切换。
- 护甲逻辑相同，由 ``spawn_armor_equipped``\ 控制 item 护甲是否出厂穿戴；内置护甲已启用时无法穿戴 item 护甲。

若单位仅有 item 装备 （无内置武器/护甲），则 ``spawn_weapons_equipped``\ / ``spawn_armor_equipped``\ 仍控制是否出厂静默装备（默认装备）。

出厂装备自动入背包

单位生成时，引擎会检查 rules 中的出厂配置：

- ``weapons \<名称\>``\ ：若同名类型为 ``class item``\ 且 ``equippable_as_weapon 1``\ ，则创建物品实例 → 放入背包；若无内置武器且 ``spawn_weapons_equipped 1``\ ，则静默装备。
- ``armor \<名称\>``\ ：若同名类型为 ``class item``\ 且 ``equippable_as_armor 1``\ ，同理；若无内置护甲且 ``spawn_armor_equipped 1``\ ，则静默穿戴。

::

    def footman
    weapons sword
    armor footman_armor
    inventory_capacity 2

在 ``sword``\ 与 ``footman_armor``\ 均定义为可装备 item 时，训练出的步兵会背包中有剑和鳞甲各一件，且出厂即已装备（默认 ``spawn_weapons_equipped 1``\ 、``spawn_armor_equipped 1``\ ）。

出厂是否静默装备（仅背包 item）：

::

    spawn_weapons_equipped 0/1   ; 无内置武器时：控制 class item 出厂武器是否静默装备（默认 1）
                                 ; 有内置武器时：1=item 武器留背包且不装备，0=允许手动装备 item 武器
    spawn_armor_equipped 0/1     ; 无内置护甲时：控制 class item 出厂护甲是否静默穿戴（默认 1）
                                 ; 有内置护甲时：1=item 护甲留背包且不穿戴，0=允许手动穿戴 item 护甲
    ; 内置 class weapon / class armor 不受上述 flag 影响，始终出厂生效

混合配置（弓箭手）：

::

    def archer
    weapons bow sword

- ``bow``\ 为 ``class weapon``\ → 内置武器，不入背包，始终出厂装备。
- ``sword``\ 为 ``class item``\ + ``equippable_as_weapon 1``\ → 入背包。
- 默认 ``spawn_weapons_equipped 1``\ 时：弓已装备，剑留在背包且无法装备；只能在内置武器之间切换。
- 仅当 ``spawn_weapons_equipped 0``\ 时，剑可手动装备；装备后只能在 item 武器之间切换，不能与弓直接切换。

若希望弓为主武器、剑作备用且允许玩家手动装备：

::

    def archer
    weapons bow sword
    spawn_weapons_equipped 0
    inventory_capacity 3

此时 bow 仍会自动装备，sword 在背包中待玩家手动装备。

前提：``inventory_capacity``\ 必须 > 0；出厂武器、护甲各占一件，容量需足够。

地图作者配置清单

仅内置装备（不可卸下）：

::

    def my_unit
    weapons short_sword
    armor light_armor
    ; 不设置 inventory_capacity，或设为 0

可拾取、可装备、可卸下的装备：

1. 定义 item 并写上战斗数值与标志位。
2. 单位开启库存并声明出厂武器：``inventory_capacity 2``\ 、``weapons my_sword``\ 。
3. 在 ``res/ui/style.txt``\ 中配置 ``title``\ 、``intro``\ ，供读屏使用。

地面放置物品：地图中放置 ``class item``\ 类型；单位靠近后 ``pickup``\ 拾取。

消耗品：

::

    def health_potion
    class item
    buffs heal

在背包中按 Enter 使用（``use_item``\ ），不能在装备栏中当作武器/护甲装备。使用成功后才播放 ``use`` / ``on_use`` 音效；普通消耗品朗读「物品名，已使用」。

技能书（永久学会技能，使用后消耗）::

    def zhuiri_jianfa_book
    class item
    skills skill_zhuiri_jianfa
    learn_level 10
    transport_volume 1

- ``learn_level`` / ``learn_level_skills``：从背包使用时的最低等级（与单位 ``learn_level_skills`` 取较高门槛）。
- 单位 ``level_skills``：升级时自动学会（与技能书独立；勿与同一技能重复配置，否则使用时会提示 ``skill_already_known`` 且不消耗书籍）。
- 拾取时若设置了 ``learn_level``\ / ``learn_level_skills``\ ，不会自动学会，须进背包后按 Enter 使用。
- 成功：播放使用音效 + 朗读「技能名，已学会」（``messages`` → ``skill_learned``）；失败：``order_impossible`` + ``skill_level_too_low`` / ``skill_already_known`` 等消息。

带使用地点的宝箱（``use_square`` + ``resource_rewards``\ ）::

    def mystery_treasure
    class item
    use_square b2
    resource_rewards resource1 150

须站在指定方格（地图 ``square_name`` 别名）上，在背包中使用后才发放资源。

服务端指令（也可在触发器 ``order`` 动作中使用）：``equip_weapon``\ 、``unequip_weapon``\ 、``equip_armor``\ 、``unequip_armor``\ 、``use_item``\ 、``drop``\ 。

单位默认行为（自 1.4.3.1 起）
------------------------------

地图/模组作者可在 ``rules.txt``\ 中按单位类型配置开局时的默认行为状态：

- ``ai_mode``\ ：``offensive`` / ``defensive`` / ``guard`` / ``chase``\ 。默认：兵种 ``offensive``\ ，工人 ``defensive``\ 。作用于作战单位。``chase`` 锁定敌人后保持 ``AttackAction`` 跨格跟随（不下自动 ``go``）；``offensive`` / ``guard`` 仍受出生 ``position_to_hold`` 限制，直到命令 ``stop()``；``defensive`` / ``chase`` 不受限。
- ``auto_gather``\ ：``1`` / ``0``\ 。默认 ``1``\ 。仅工人。
- ``auto_repair``\ ：``1`` / ``0``\ 。默认 ``1``\ 。仅工人。
- ``auto_explore``\ ：``1`` / ``0``\ 。默认 ``0``\ 。可移动单位。
- ``can_auto_explore``\ ：``1`` / ``0``\ 。默认 ``0``\ 。命令菜单是否提供自动探索开关。
- ``no_number``\ （自 1.4.3.2 起）：``1`` / ``0``\ 。默认 ``0``\ （始终报序号，如「农民1在 a1」）。设为 ``1`` 时：同类型仅 1 个存活不报序号（「关羽在 a1」），2 个及以上才报「关羽1」「关羽2」；编组摘要亦同（「你控制了关羽和2护卫骑士」）。适合英雄、将领等特殊单位。

``auto_explore``\ 与 ``can_auto_explore``\ 的区别：

- ``auto_explore``\ 决定单位开局是否处于自动探索状态。
- ``can_auto_explore``\ 决定玩家能否在该单位的命令菜单里看到「启用/禁用自动探索」选项。

AI 模式（``ai_mode``\ ）

| 取值 | 名称 | 行为 |
| offensive | 进攻 | 主动攻击当前格子里的敌人 |
| defensive | 防御 | 战力不利时撤退；占优时才交战 |
| guard | 站岗 | 不主动出击，原地驻守 |
| chase | 追击 | 保持攻击动作跨格跟随敌人（不下自动 ``go``）；不受 ``position_to_hold`` 限制 |

``ai_mode patrol``\ 无效——巡逻（patrol）是需要路线目标的命令，不是一种 AI 模式。中立电脑（``computer_only ... neutral``\ ）的单位仍会被引擎强制设为 guard + 反击。

玩家单位在 ``offensive``\ / ``defensive``\ / ``chase``\ 模式下不会主动攻击 中立单位，防御模式也不会因中立者而撤退；对中立普通 ``go`` 只移动；对 ``is_huntable`` 默认仍可 ``attack`` 并造成伤害；若要 AI 把中立 creep/NPC 当自动目标，须下达 强制攻击命令 （``imperative``\ ，例如 Ctrl+点击）。

自动采集 / 自动修理

- ``auto_gather 1``\ ：工人空闲且附近有可采集资源点 + 对应仓库时，自动前往采集。
- ``auto_repair 1``\ ：工人空闲且同格有受损友方可修理单位时，自动修理（需 ``can_repair 1``\ ）。
- ``can_herd 1``\ ：工人可驱赶 ``herdable`` 动物（如羊）；默认 ``0``\ ，须在单位定义中显式开启。
- ``can_capture``\ ：``1`` / ``0``\ 。默认 ``1``\ 。有 ``attack`` 技能的单位；控制右键 ``capture_hp_threshold 100`` 敌方目标时是否默认 占领 （``capture`` 命令）。``0`` 时改为普通攻击/移动，AI 也不会对该目标走接触即占领逻辑。详见下文「占领与默认占领命令」。

狩猎系统（帝国时代式）

详见 ``../player/hunting.htm``\ 。概要：

- 村民退格/右键 ``is_huntable`` 动物默认攻击（普通攻击即造成伤害）；击杀后生成 ``food_deposit``（如 ``food_carcass``\ ），攻击命令完成且不误播 ``order_impossible``\ 。
- 动物属性：``is_huntable``\ 、``flee_on_hit``\ 、``herdable``\ 、``food_deposit``\ 、``food_deposit_qty``\ 、``no_number``\ 。
- 地图放置：``computer_only 0 0 neutral \<方格\> \<数量\> deer``\ ；随机地图会自动生成野生动物。
- 语音标识：配置了 ``is_huntable`` / ``herdable`` 的单位播报为「鹿 , 动物」，`` 不是`` 「中立 , NPC」。Ctrl+Shift+F4 切到仅含野生动物的玩家时播报「你是动物」。剧情 NPC（``quest_npc`` 等）仍播报「中立 , NPC」。
- 外交隔离：仅含野生动物的 ``computer_only`` 槽位（如 ``deer`` / ``sheep`` / 自定义 ``tiger``）不进 ``ai`` 联盟，不与玩家、敌对 creep、其它动物群结盟；混编槽位除外。详见 ``../player/hunting.htm`` §3.1。
- 科技 ``hunting_techniques``\ ：提升尸体与浆果采集效率。

自动探索

- ``can_auto_explore 1``\ ：该单位命令菜单里提供「启用/禁用自动探索」选项；只配置了的单位才会出现。
- ``auto_explore 1``\ ：该单位开局即自动探索——空闲时自动走向未探明区域；发现敌人后按 ``ai_mode``\ 交战。
- 玩家下达其他命令会暂停探索；命令完成、单位再次空闲时自动恢复探索。
- 「禁用自动探索」在单位当前正处于自动探索状态时就会出现（即便没配 ``can_auto_explore``\ ）。

综合示例::

    def peasant
    class worker
    auto_gather 1
    auto_repair 0
    ai_mode defensive

    def knight
    class soldier
    auto_explore 1
    can_auto_explore 1
    ai_mode guard

狩猎动物示例::

    def deer
    class soldier
    is_huntable 1
    flee_on_hit 1
    food_deposit food_carcass
    food_deposit_qty 35
    no_number 1
    ai_mode guard

给 NPC 物品（自 1.4.3.1 起）
------------------------------

give 指令——将背包中的物品交给另一单位：

::

    give <目标单位id>            ; 交出库存第一件
    give <目标单位id> <物品>     ; 指定 type_name 或物品 id

npc_has_item 触发器条件：

::

    (npc_has_item <NPC选择符> <物品type_name> [所在方格])

判定：目标单位的 ``received_items``\ 含有该物品类型，或其当前库存里仍持有该类型物品。可选方格参数用于区分多个同名 NPC。

目标字段（须全部通过）：

- ``receive_items``\ ：``1`` / ``0``\ 。总开关；默认 ``0``\ （不接收）。
- ``accepted_items``\ ：物品 type_name 列表。白名单；留空 = 接收任意物品。
- ``accept_from``\ ：``self``/``ally``/``neutral``/``enemy``\ 列表。留空 = 不限关系。

关系（``accept_from``\ ）按 self > ally > neutral > enemy 优先级实时计算。

示例——只有盟友骑士接收 ``knight_lance``::

    def knight
    receive_items 1
    accepted_items knight_lance
    accept_from ally

示例——只有中立农民接收 ``pickaxe``::

    def quest_peasant
    receive_items 1
    accepted_items pickaxe
    accept_from neutral

内置示例 NPC：``quest_npc``\ （``res/rules.txt``\ ，``receive_items 1``\ + ``inventory_capacity 5``\ ）。

交付会在目标上记录 ``received_items``\ ，供触发器检查。物品在接收时像 ``pickup``\ 一样应用 ``skills`` / ``buffs``\ 。脚本交付不受目标 ``inventory_capacity``\ 限制。联机示例：``res/multi/give_demo.txt``\ ；战役关系示例见 ``The Legend of Raynor`` 第 14–16 章（``res/single/The Legend of Raynor/14.txt``\ 、``15.txt``\ 、``16.txt``\ ）。

建造场、附属建筑与起飞重组（星际争霸式，``mods/starcraft``）
--------------------------------------------------------------

引擎自 1.4.x 起支持 建造场（build field）、 工人施工模式、 人族附属与 起飞重组。
完整示例见 ``mods/starcraft/rules.txt``\ ；玩家向说明：

- 人族附属：``../player/starcraft-terran.htm``
- 异虫菌毯与女王肿瘤：``../player/starcraft-zerg-creep.htm``

建造场（神族灵能场 / 异虫菌毯等）
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| 属性 | 说明 |
| --- | --- |
| ``provides_build_field \<名称\>`` | 该单位/建筑为周围格提供建造场标记（如 ``psi``\ 、``creep``\ ） |
| ``requires_build_field \<名称\>`` | 需要指定建造场才能放置/施工；``0`` 表示 该建筑豁免（如主基地、光子炮） |
| ``build_field_radius \<格数\>`` | 提供建造场的半径（沿主方格 BFS 计格；与 ``build_field_radius_m`` 二选一） |
| ``build_field_radius_m \<米\>`` | 供能半径（米，与 ``rdg_range`` 同尺度）；按提供者 `` (x,y)`` 到目标点的距离判定 |
| ``build_field_persists 1`` | 提供者被毁后，已标记的格子仍保留建造场（异虫菌毯） |
| ``build_field_spreads 1`` | 每秒向相邻格蔓延一层建造场标记 |
| ``build_field_spread_squares N`` | 每次 tick 蔓延的层数（默认随 ``build_field_spreads`` 为 1） |
| ``requires_build_field_on_square 1`` | 目标整格 须带建造场标记（异虫）；否则只需格内有实时供能即可（神族） |
| ``loses_power_without_field 1`` | 失去实时建造场时断电：停工、停训练、停供能（神族建筑） |

:strong:```build_field_radius`` 与 ``build_field_radius_m``

每个提供者只应设置一种 半径，另一种保持 0 （默认）。

| 属性 | 范围计算方式 | 典型用途 |
| --- | --- | --- |
| ``build_field_radius`` | 从提供者主方格 出发的 BFS 格数（离散铺格） | 旧式按格菌毯 |
| ``build_field_radius_m`` | 从提供者 (x, y) 的欧氏距离（米） | 神族灵能链（类似 SC2）；星际 mod 主巢/菌毯肿瘤 |

一格地图宽度约 12 米 （``square_width 12``）。星际 mod 示例：主基地 18 m、水晶塔 12 m、主巢 12 m、菌毯肿瘤 4 m。

实时供能 vs 格标记

- 实时供能（live） — 当前仍存在的提供者正在覆盖的范围（米制：点落在圆内；格制：从 ``place`` BFS）。
- 格标记（marked） — 注册时绘制、或每秒蔓延写入的持久方格集合。

``has_build_field_on_square`` 接受 实时或标记 任一满足即可。异虫 ``requires_build_field_on_square 1`` 只认`` 标记格`` （主巢旁实时菌毯尚未蔓延标记时不能建造）。

当 ``build_field_persists 1`` 或 ``build_field_spreads 1`` 时，米制半径 提供者也会绘制格标记 （主巢仅写 ``build_field_radius_m`` 时仍能供异虫判定建造）。

女王菌毯肿瘤 （``mods/starcraft``）：召唤类技能在目标格放置 ``creep_tumor`` 建筑。技能属性：

| 属性 | 说明 |
| --- | --- |
| ``summon_requires_build_field \<名称\>`` | 目标格须有此建造场（实时或标记均可） |
| ``summon_requires_marked_field 1`` | 目标格须为已标记 菌毯（肿瘤 延伸；女王  生成 不写此项） |

测试图：``mods/starcraft/multi/zerg_creep_tumor_test.txt``。玩家说明：``../player/starcraft-zerg-creep.htm``。

神族示例 （``protoss_building``\ ）::

    requires_build_field psi
    is_buildable_anywhere 1
    self_constructs 1
    loses_power_without_field 1

主基地 ``requires_build_field 0`` + ``provides_build_field psi``\ ；水晶塔/传送门依赖灵能场。
星际模组示例：``build_field_radius_m 18`` （主基地）、``12`` （水晶塔）；一格地图宽度约 12 米。

异虫示例 （``zerg_building``\ ）::

    requires_build_field creep
    requires_build_field_on_square 1
    is_buildable_anywhere 1
    self_constructs 1

主巢 ``provides_build_field creep`` + ``build_field_radius_m 12`` + ``build_field_persists 1`` + ``build_field_spreads 1``\ ；女王 生成菌毯肿瘤/ 肿瘤  延伸 见 ``../player/starcraft-zerg-creep.htm``\ 。

UI 语音：在 ``ui/style.txt`` 定义 ``def build_field_\<名称\>`` + ``title \<TTS编号\>``\ ；可选 ``noise repeat N \<音效\>``\ 。进入可见格时会播报场类型；无法建造时播报「不能建在那里」+ 场名。

矿床与气矿（``requires_deposit``）
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| 属性 | 说明 |
| --- | --- |
| ``requires_deposit \<类型\>`` | 只能建在地图矿床对象上（如 ``geyser``）；完工后移除该矿床 |
| ``is_buildable_anywhere 0`` | 与 ``requires_deposit`` 配合，禁止建在建造用地上 |

气矿模板 ``sc_gas_building`` 使用 ``auto_production`` + ``is_gather`` + ``production_time`` / ``production_qty``\ 。工人 ``can_gather`` 须包含气矿建筑类型名（如 ``assimilator``），而非 ``geyser`` 矿床本身。

工人施工模式
>>>>>>>>>>>>

| ``build_mode`` | 行为 |
| --- | --- |
| ``assisted`` | 默认：工人协助施工直至完工（人族 SCV） |
| ``place_and_leave`` | 放置工地后离开，建筑 ``self_constructs 1`` 自行完工（神族探机） |
| ``sacrifice`` | 工人被消耗，建筑立即开始施工（异虫工蜂） |

相关属性：

- ``self_constructs 1`` — 无需工人持续建造（可与 ``place_and_leave`` 配合）
- ``build_sacrifices_worker 1`` — 强制消耗工人（等价于 sacrifice 模式）
- ``is_buildable_anywhere 1`` — 可在任意已满足建造场条件的格内选点，不单独占用 ``class building_land`` 对象（神族/异虫/飞行人族）

人族附属建筑（addon）
>>>>>>>>>>>>>>>>>>>>>

| 属性 | 说明 |
| --- | --- |
| ``can_have_addon \<类型列表\>`` | 宿主（兵营/工厂/星港）可挂的附件 |
| ``addon_max N`` | 宿主最多挂载数量（默认 1） |
| ``is_addon 1`` | 标记附属建筑（Tech Lab、Reactor） |
| ``addon_host_types \<宿主列表\>`` | 附件可挂在哪些宿主上 |
| ``addon_grants_train_\<宿主\> \<单位\>`` | 挂接后为该宿主增加训练项（如 ``addon_grants_train_factory tank``\ ） |
| ``addon_grants_research \<科技\>`` | 挂接后增加研究项 |
| ``addon_grants_train \<单位\>`` | 为任意兼容宿主增加训练（通用写法） |
| ``addon_train_multiplier N`` | Reactor：训练数量倍率（2 = 双产） |
| ``addon_offset_x \<值\>`` | 附件相对宿主东侧偏移（默认 3.5 格 = 3500 内部单位） |

附件在宿主侧面插槽自行建造（``self_constructs 1``\ ），不单独占用建造用地。建造时选中已有宿主，不要点空地。

起飞与重组（lift-off / recombine）
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| 属性 | 说明 |
| --- | --- |
| ``can_change_to \<飞行形态\>`` | 地面宿主可变形起飞 |
| ``ground_form \<地面形态\>`` | 飞行形态的落地目标（如 ``flying_factory`` → ``factory``\ ） |
| ``change_time \<秒\>`` | 变形耗时（``change_to`` 专用，不耗资源/人口） |

星际 mod 地图默认刷 **空地**（``build_site``），见 ``nb_build_site_by_square`` / ``building_land build_site`` （``mod/mapmaking.rst``\ ）。

起飞：地面人族建筑 → 飞行形态；附件 detach 留在原格；原位置恢复**该建筑建造时占用的建造用地类型**（星际为 ``build_site``）。仅当建筑未保存用地引用时，才用地图 ``building_land`` 或 ``nb_<type>_by_square`` 推断的类型。

降落：飞行形态 ``change_to`` 回地面；须消耗同格一块 ``class building_land`` 对象（引擎内部仍称 meadow，见 ``find_meadow_near_xy``\ ）。

重组 （接管孤立 Tech Lab）：

1. Tab 科技实验室→ 退格 go（目标改飞向宿主降落插槽，实验室西侧约 3.5 格）
2. 变形落地 → 插槽对齐时 ``try_reattach_orphan_addons`` 自动挂接

建造用地 vs 插槽 （两套独立判定）：

- 建造用地：降落许可；``find_meadow_near_xy`` 选最近 ``class building_land`` 消耗
- 插槽：``tech_lab.x ≈ factory.x + addon_offset_x`` （曼哈顿距离 ≤ 约 2.5 格）才对接

落在自己起飞用地 仅普通降落，不对接；落错格且同格仍有可对接附件时会播报 TTS ``addon_reattach_failed`` （7350）。

操作速查

| 目的 | Tab 目标 |
| --- | --- |
| 落回起飞点 | 该建筑起飞留下的建造用地（星际为空地） |
| 接管孤立 Tech Lab | 科技实验室 （非建造用地） |

测试地图：``terran_addon_test``\ 、``terran_recombine_test``\ ；战役 ``sc_build_tests`` 第 3–4 章。

占领与默认占领命令
------------------

目标侧 — ``capture_hp_threshold`` （写在可被夺取的建筑/单位上）：

| 值 | 含义 |
| --- | --- |
| ``0`` （默认） | 不可通过血量阈值夺取 |
| ``100`` | 接触即占领：单位到位后直接转变阵营，不造成伤害；右键默认命令为占领（见 ``can_capture``\ ） |
| ``30`` 等 | 战斗中血量 ≤ 该百分比时可夺取（走正常伤害与 ``damage_effects`` 逻辑） |

攻击方 — ``can_capture`` （写在士兵/工人等有攻击能力的单位上）：

| 值 | 含义 |
| --- | --- |
| ``1`` （默认） | 右键 ``capture_hp_threshold 100`` 的敌方目标 → 默认 占领 ；AI 对该目标也走接触即占领 |
| ``0`` | 同上目标 → 默认 攻击/移动 ；AI 正常攻击，不自动占领 |

前提：本单位有 ``attack`` 技能，目标为存活、可受伤的敌方单位/建筑。

示例 — 只有步兵能占领兵营，弓箭手只能打::

    def captured_barracks
    class building
    capture_hp_threshold 100
    ...

    def footman
    class soldier
    can_capture 1
    ...

    def archer
    class soldier
    can_capture 0
    ...

随机地图 POI ``captured_barracks`` 与 HoMM 式玩法见 ``player/英雄无敌与文明5玩法说明.htm``\ 。

Ship repair (since 1.4.1.1)
----------------------------

工人或建筑上设置 ``can_repair_ships 1``。工人修理相邻岸边的舰船（6 格）；建筑自动修理邻近水域中的舰船（8 格）。

水上铺桥（逐格桥段）
--------------------

工人可在纯水路方格上建造 ``is_buildable_on_water_only 1`` 的桥段；完工后应用 ``bridge_terrain``（如 ``bridge_deck``）。脚手架阶段播报与其它 ``buildingsite`` 相同（「木桥桥段 在建筑」），脚步声读 ``bridge_terrain`` 的 ``ground``。详见 `水上铺桥 <water-bridge-building.htm>`_。

Inheritance (since 1.3.8.3)
-----------------------------

::

    is_a footman                    ; 全部属性
    is_a footman(hp_max mdg)        ; 选择性继承
    is_a footman(apart hp_max)      ; 排除继承（apart 写法）
    is_a footman(-hp_max)           ; 排除继承（- 前缀，与 apart 等价）
    is_a footman(-hp_max -mdg)      ; 排除多个属性
    is_a footman(mdg) knight(hp_max) ; 多父级

style
------

样式定义在 "ui/style.txt" 以及 "style.txt" 的本地化版本中。

shortcut
>>>>>>>>

如果定义了快捷键，简单命令、建造命令、训练命令以及使用能力的命令都可以用快捷键下达。

要定义快捷键，定义一个 "shortcut" 属性，后接对应的字母。该字母必须是小写。

如果命令是简单命令，则快捷键必须由该命令定义（例如：patrol）。
如果命令是复合命令（训练、建造、使用能力），则快捷键必须由命令的第二部分定义。
例如，为流星术能力定义一个 "m" 快捷键，这样法师就会有施放流星的 "m" 快捷键。

intro (since 1.4.1.5)
>>>>>>>>>>>>>>>>>>>>>>

在 ``title`` 下添加单位描述::

    def footman
    title 87
    intro 1001

文本须存在于 ``tts.txt`` 中。

Combat sound system (since 1.3.8.2; 1.4.4.6 renamed matk/ratk to mdg/rdg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

取代旧的攻击音效::

    launch_mdg / launch_rdg
    mdg_hit / rdg_hit / mdg_hit_vs / rdg_hit_vs
    mdg_missed / rdg_missed
    mdg_dodge / rdg_dodge
    launch_charge_mdg / launch_charge_rdg
    charge_mdg_hit / charge_rdg_hit
    casting
    disappear
    weapon_switched
    death / falling / falling_delay / falling_on_<terrain>
    move / move_on_<terrain>

**战斗喊杀（自 1.4.5.0 起分层播放；详见 :doc:`battle-shouts`）**

- ``shouts`` — 接战喊杀音池；建议在 ``def walking_unit`` 定义，供步兵/弓手等继承

**脚步声与倒地音效（自 1.3.9.1 起；1.4.5.0 起 ``move_on_`` / ``falling_on_`` 支持地形类型名）**

在 ``def unit``（或具体单位）的 ``style.txt`` 中可写：

- ``move`` — 默认脚步声
- ``move_on_<键>`` — 按地形变化的脚步声
- ``falling`` — 死亡后的倒地音效（通用）
- ``falling_delay <秒>`` — 先播 ``death``，延迟后再播 ``falling``；省略或为 0 则立即播放
- ``falling_on_<键>`` — 按地形变化的倒地音效

``<键>`` 的匹配顺序（``move_on_`` 与 ``falling_on_`` 相同）：

1. **地形类型名** — 单位所在格的 ``rules.txt`` / ``style.txt`` 定义名（如 ``ocean``、``plain``、``mountain``）。若地图启用子格地形，使用单位坐标处的子格类型。
2. **ground 类别** — 该地形在 ``style.txt`` 上的 ``ground`` 值（如 ``creek`` 的 ``ground water`` → 匹配 ``move_on_water`` / ``falling_on_water``）。

地形类型名优先于 ``ground``。例如 ``ocean`` 没有 ``ground`` 时仍可用 ``falling_on_ocean``；``creek`` 上若同时写了 ``falling_on_creek`` 与 ``falling_on_water``，优先播放前者。

示例::

    def unit
    move 1052 1053
    move_on_ocean 1088 1348
    move_on_water 1088 1348
    move_on_grass 1053 1054
    falling 80051
    falling_delay 1
    falling_on_ocean fallwater
    falling_on_water splash

仅 **地面单位** 使用所在格的地形脚步声；无匹配时回退到 ``move``。若格内静止物体（建筑、树木等）更近，也会尝试 ``move_on_<物体类型名>``，再尝试其 ``ground`` 类别。

配置了 ``damage_seq`` 连发的单位，每一发都会触发 ``launch_mdg`` / ``launch_rdg``。可在同一行
写多个音效 ID，使各发从中选取。

``mdg_hit_vs`` / ``rdg_hit_vs`` 可以按目标类型播放不同命中音效。目标匹配范围包括：
单位类型、单位继承类型，以及目标当前身上的 buff/debuff 类型。例如::

    def swordsman
    mdg_hit_vs b_absolute_defense iron_clang

当 ``swordsman`` 打中带有 ``b_absolute_defense`` 的目标时，会播放 ``iron_clang``。

1.4.4.6 起，文档与内置资源统一使用 ``mdg`` / ``rdg`` 命名。旧 ``matk`` / ``ratk``
字段仍作为兼容 fallback，可供旧 mod 继续工作。

技能、buff 和 debuff 还可以定义触发音效::

    def skill_counter
    alert counter_alert
    ready counter_ready
    triggered counter_proc

    def b_absolute_defense
    triggered shield_on
    noise loop shield_hum

技能手动释放时播放 ``alert``；如果技能规则含 ``ready \<秒\>``，可在技能 style 中写
``ready \<sound\>``，手动释放与自动触发技能都会在前摇开始时播放。通过 ``active_trigger_skills``、``passive_trigger_skills``、
``attack_trigger_skills`` 或 ``attack_replace_skills`` 自动触发时，优先播放 ``triggered``，
未配置则回退到 ``alert``。buff/debuff 通过触发字段应用时，如果配置了 ``triggered``，
会额外播放一次。buff/debuff 的持续状态音效必须显式写成 ``noise loop \<sound\>`` 或
``noise repeat \<interval\> \<sound...\>``；只写 ``noise \<sound\>`` 不会自动当作循环音效。

Menu and game music (since 1.4.0.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

在 ``def parameters`` 中::

    menu_music <id>
    campaign_music <id>
    game_creation_music <id>
    server_lobby_music <id>
    game_music <id>
    battle_music <id>
    victory_sound <id>
    defeat_sound <id>
    main_menu_select_sound <id>
    main_menu_confirm_sound <id>

阵营音乐（自 1.4.0.3 起）::

    china_music china
    china_battle_music china_battle

地图覆盖：``map_music``、``map_battle_music``、``map_victory_sound``、``map_defeat_sound``。
音乐文件：``ui/music/\<id\>.mp3`` 或 ``mods/\<mod\>/ui/music/\<id\>.mp3``。
