技能、治疗、伤害与效果系统
=============


.. epigraph:: 面向 **模组作者**：在 `rules.txt` 里配置主动技能、单位自带治疗/伤害光环、以及战场区域效果（`class effect`）。由浅入深，建议按章阅读。



----


阅读顺序
----


1. **主动技能**（`class skill`）— 玩家按键或自动触发的招式
2. **单位治疗/伤害**（`heal_*` / `harm_*`）— 牧师、毒云、生命/法力回复节奏
3. **战场效果**（`class effect`）— 火墙、光环、带 debuff 的范围攻击
4. **进阶** — 连击 burst、自动触发、范围参数对照表

官方关键字大全另见 ``modding.htm``。


面向 **模组作者**：在 ``rules.txt`` 中用 ``class skill`` 定义主动技能，无需 Python 源码。完整示例见官方 mod **``mods/wuxia/rules.txt``**（武侠技能演示）。

基本概念
----


用 ``class skill`` 定义技能，取代旧版 ``class ability``：

.. code-block:: text

   def fireball
   class skill
   mana_cost 50
   cost 10 0
   time_cost 30
   effect harm_target 60
   effect_target ask
   effect_range 12
   cooldown 10


单位通过 ``can_use_skill`` 学会技能；升级仍用 ``can_use_tech``。

统一技能系统（1.4.4.6 起）
~~~~~~~~~~~~~~~~~


同一 ``class skill`` 可同时配置 **手动释放** 与 **自动触发**。学会的技能统一写在单位的 ``can_use_skill`` 中。


+----+----+
| 属性 | 说明 |
+====+====+
| `manual_use 1` | 出现在命令菜单，玩家可按键释放（默认 `1`） |
+----+----+
| `auto_trigger 1` | 战斗中满足条件时自动触发（默认 `0`） |
+----+----+
| `trigger_timing` | 自动触发的时机（见下文） |
+----+----+


二者可并存：例如 ``manual_use 1`` + ``auto_trigger 1`` 表示既能手动放，也能在战斗中概率自动触发。

旧字段 ``active_trigger_skills``、``attack_trigger_skills``、``attack_replace_skills``、``passive_trigger_skills`` 仍兼容；新 mod 建议只用 ``can_use_skill`` + 技能上的 ``auto_trigger`` / ``trigger_timing``。

技能触发方式
------


四种自动触发时机（trigger_timing）
~~~~~~~~~~~~~~~~~~~~~~~~


须同时设置 ``auto_trigger 1`` 与 ``trigger_timing``。默认值为 ``on_hit``。


+------------------+------+------------+
| `trigger_timing` | 触发时机 | 旧单位列表（仍兼容） |
+==================+======+============+
| `on_hit` | 攻击者 **命中敌人之后**（默认） | `active_trigger_skills` |
+------------------+------+------------+
| `on_attack` | **发起攻击时**附加释放，**普攻照常进行** | `attack_trigger_skills` |
+------------------+------+------------+
| `on_attack_replace` | **发起攻击时**释放，**替代本次普攻**（技能触发成功则跳过普攻） | `attack_replace_skills` |
+------------------+------+------------+
| `on_damaged` | **被敌人命中时**（被动） | `passive_trigger_skills` |
+------------------+------+------------+


自动触发时会检查法力（``mana_cost``）、冷却（``cooldown``），并消耗法力、进入冷却（与手动释放相同）。若技能写了 ``ready``，自动触发也会先进入前摇再生效。

**注意**：``on_hit`` 仅在攻击者对 **敌人** 造成伤害后触发；``on_damaged`` 在 **被敌人攻击命中** 时由受击方触发。

示例 1：命中后附加伤害（on_hit）
^^^^^^^^^^^^^^^^^^^^


对 **被命中的敌人** 触发时，```effect_target```` 不要写 ````self```（默认为自身）。实战写法：

.. code-block:: text

   def skill_poison_strike
   class skill
   auto_trigger 1
   manual_use 0
   trigger_timing on_hit
   active_trigger_rate 30
   effect debuffs b_poison
   effect_target ask


自动触发时 ```ask```` 会解析为当前受击的敌人。测试见 ````test_wuxia_skills.py```` 的 ````skill_proc```。

示例 2：出手附加 buff（on_attack）
^^^^^^^^^^^^^^^^^^^^^^^^^


.. code-block:: text

   def skill_battle_cry
   class skill
   auto_trigger 1
   manual_use 0
   trigger_timing on_attack
   active_trigger_rate 50
   effect buffs b_battle_cry
   effect_target self


发起攻击时 50% 概率对自身加 buff，**本次普攻仍会继续**。

示例 3：替代普攻（on_attack_replace）
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code-block:: text

   def skill_flame_strike
   class skill
   auto_trigger 1
   manual_use 1
   trigger_timing on_attack_replace
   active_trigger_rate 100
   effect harm_target mdg
   effect_target ask
   effect_range 1
   mdg 15
   cooldown 3
   mana_cost 10


攻击开始时尝试释放；成功则 **本次不进行普通攻击**。可保留 ``manual_use 1`` 以便玩家也能从菜单手动施放。

示例 4：受击反击（on_damaged）
^^^^^^^^^^^^^^^^^^^^^


.. code-block:: text

   def skill_thorns
   class skill
   auto_trigger 1
   manual_use 0
   trigger_timing on_damaged
   passive_trigger_rate 30
   effect harm_target 10
   effect_target ask


被敌人命中时 30% 概率对 **攻击者** 造成 10 点固定伤害（```effect_target ask``` 在被动触发时解析为攻击者）。

示例 5：手动 + 自动并存
^^^^^^^^^^^^^^


.. code-block:: text

   def skill_heal_proc
   class skill
   auto_trigger 1
   manual_use 1
   trigger_timing on_hit
   active_trigger_rate 15
   effect buffs b_small_heal
   effect_target self
   mana_cost 20
   cooldown 8


玩家可按技能键手动治疗；战斗中命中敌人时另有 15% 概率自动触发（仍消耗法力并 respect 冷却）。

触发概率
~~~~



+----+------+----+
| 属性 | 适用时机 | 说明 |
+====+======+====+
| `active_trigger_rate` | `on_hit`、`on_attack`、`on_attack_replace` | 触发概率 1–100（默认 100） |
+----+------+----+
| `passive_trigger_rate` | `on_damaged` | 触发概率 1–100（默认 100） |
+----+------+----+
| `mdg_trigger_rate` | 上述主动类时机 | 若 > 0，**近战攻击时优先使用**，覆盖 `active_trigger_rate` |
+----+------+----+
| `rdg_trigger_rate` | 上述主动类时机 | 若 > 0，**远程攻击时优先使用**，覆盖 `active_trigger_rate` |
+----+------+----+


示例：近战 80%、远程 40% 的命中触发：

.. code-block:: text

   active_trigger_rate 100
   mdg_trigger_rate 80
   rdg_trigger_rate 40
   trigger_timing on_hit


触发条件
~~~~



+----+----+
| 属性 | 说明 |
+====+====+
| `trigger_condition` | 条件表达式，格式 `属性 运算符 值`（三词，空格分隔） |
+----+----+
| `hp_threshold` | 简写：生命百分比 ≤ 阈值时才触发（整数，如 `30` 表示 30% 以下） |
+----+----+


``trigger_condition`` 语法与 buff 相同。``hp``、``mana`` 在条件中按 **百分比** 比较：

.. code-block:: text

   trigger_condition hp < 30


等价于简写 ``hp_threshold 30``（生命 ≤ 30% 时方可触发）。

**限制**：``trigger_condition`` / ``hp_threshold`` 目前由 ``on_hit`` 与 ``on_damaged`` 路径检查；``on_attack`` / ``on_attack_replace`` **不**检查这两项条件。

前摇（ready）
~~~~~~~~~


.. code-block:: text

   ready 2


自动触发与手动释放均会先等待 ``ready`` 秒再执行 ``effect``；可在技能 ``style.txt`` 写 ``ready <音效ID>`` 在前摇开始时播放。

与 buff 攻击触发的区别
~~~~~~~~~~~~~~



+----+------+------+
| 机制 | 配置位置 | 典型用途 |
+====+======+======+
| 技能 `auto_trigger` | `class skill` + `can_use_skill` | 释放完整技能 effect（harm、buff、deploy 等） |
+----+------+------+
| 攻击附带 buff | 单位 `attack_trigger_buffs` / `attack_replace_buffs` 等 | 仅施加 buff/debuff，无独立技能 def |
+----+------+------+
| buff `is_active` / `is_passive` | `class buff` | buff 自身在攻击/受击时叠加 |
+----+------+------+


同一单位可同时使用技能自动触发与攻击附带 buff；二者独立判定概率与冷却。

目标与范围
~~~~~



+----+----+
| 属性 | 说明 |
+====+====+
| `effect_target` | `self`（自身）、`ask`（玩家选目标）、`random`（随机格） |
+----+----+
| `effect_range` | 施法距离（格）；`inf` 为无限 |
+----+----+
| `effect_radius` | 效果中心半径（部分 legacy 效果使用） |
+----+----+


消耗与冷却
~~~~~


``mana_cost``、``cost``（资源）、``time_cost``（吟唱秒数）、``cooldown``（冷却秒数）、``ready``（前摇秒数；可在技能 ``style.txt`` 定义 ``ready <sound>`` 播放音效）。

通用技能效果（effect）
--------------


语法：``effect <类型> [参数…]``

每个技能通常只写一行 ``effect``。引擎支持以下可执行类型（legacy 与 1.4.4.6 通用效果）：

harm_target — 单体伤害
~~~~~~~~~~~~~~~~~~


**固定真实伤害**（绕过护甲）：

.. code-block:: text

   effect harm_target 60


**战斗管线伤害**（护甲、暴击、溅射等完整流程；技能上的非零战斗属性覆盖施法者）：

.. code-block:: text

   effect harm_target mdg
   effect harm_target rdg


wuxia 示例：``skill_lipi``（固定 60）、``skill_lipi_mdg``（战斗 mdg）。

harm_area — 范围伤害
~~~~~~~~~~~~~~~~


**固定真实伤害**：

.. code-block:: text

   effect harm_area <伤害> <半径>


示例（wuxia ``skill_heng_sao``）：``effect harm_area 50 3``（固定 50 真实伤害，半径 3）。

**战斗管线范围伤害**：

.. code-block:: text

   effect harm_area mdg <半径>
   effect harm_area rdg <半径>


半径可省略，此时使用技能的 ``effect_radius``（默认 6）。技能可覆写战斗属性：

.. code-block:: text

   def skill_heng_sao_mdg
   class skill
   effect harm_area mdg 3
   mdg 12
   mdg_splash 6
   mdg_radius 1.5
   mdg_splash_decay_min 0.5
   effect_target ask
   effect_range 8


burst — 连击（技能）
~~~~~~~~~~~~~~


.. code-block:: text

   effect burst mdg <次数> (interval <秒>) (window <秒>)
   effect burst rdg <次数> (interval <秒>) (window <秒>)


或使用逐发延迟：

.. code-block:: text

   effect burst mdg 3 (delays 0 0.2 0.5)


- `interval`：相邻两击间隔（秒）
- `window`：连击总时间窗口（秒）
- `delays`：每击的绝对延迟列表，长度须等于次数

伤害取自技能或施法者的 ``mdg`` / ``rdg`` 及完整战斗属性。wuxia 示例：``skill_jifengci``、``skill_jifengci_rdg``。

.. epigraph:: **注意：技能 `effect burst` ≠ 单位 `damage_seq` 连发攻击。** 详见本文「进阶」一节及 `player/burst-attacks.htm`。


push — 击退
~~~~~~~~~


.. code-block:: text

   effect push <距离>


将敌方目标向远离施法者方向推开，自动寻找可站立格。wuxia 示例：``skill_moli_dan``（``effect push 5``）。

buffs / debuffs — 施加增益或减益
~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   effect buffs <buff名> [<buff名2> …]
   effect debuffs <debuff名>


- `effect_target self`：对自身施放
- `effect_target ask` + `effect_range`：对选中目标施放

``debuffs`` 仅对敌人生效。wuxia 示例：``skill_douzhuan`` → ``effect buffs b_douzhuan``。

**伤害反弹**：没有独立的 ``effect reflect``。须在 buff 定义上使用 ``reflect_percent``（百分比），再由技能 ``effect buffs`` 施加。wuxia 示例：``b_douzhuan`` 的 ``reflect_percent 100``。

deploy — 部署战场效果
~~~~~~~~~~~~~~~


.. code-block:: text

   effect deploy <存活秒数> [<数量>] <class effect 类型名>


在目标格放置 ``class effect`` 实体（火墙、治疗区等）。详见第三节「战场效果」。

summon — 召唤单位
~~~~~~~~~~~~~


.. code-block:: text

   effect summon <存活秒数> [<数量>] <单位类型> …


可选：``summon_requires_build_field``、``summon_requires_marked_field``。

旧版效果（仍可用）
~~~~~~~~~



+--------+----+
| effect | 说明 |
+========+====+
| `teleportation` | 传送友方单位至目标格 |
+--------+----+
| `recall` | 召回目标格友方单位至施法者处 |
+--------+----+
| `conversion` | 转化敌方单位 |
+--------+----+
| `raise_dead <秒> <单位…>` | 从尸体复活 |
+--------+----+
| `resurrection <上限>` | 复活友方尸体 |
+--------+----+
| `harm <等级>` | 旧式：在目标格生成临时 harm 效果（建议改用 `harm_target` / `harm_area`） |
+--------+----+


不可执行（仅 UI 显示）
~~~~~~~~~~~~~


``effect heal``、``effect damage`` 仅在属性界面格式化显示，**不会**在释放时执行治疗或伤害。治疗请用单位 ``heal_*`` 属性、``class effect`` 或 ``effect buffs`` 增强治疗属性。

目标类型过滤（harm_target_type）
------------------------


对 ``burst``、``harm_target``、``harm_area``、``push`` 生效。未配置时 **默认仅对敌人** 生效（1.4.4.6 起）。

.. code-block:: text

   harm_target_type enemy ground unit -building


- 标签前加 `-` 表示排除，如 `-building`、`-undead`、`-enemy`
- `harm_target_type` 与 buff `target_type`：正向标签为 **AND**（须全部满足）
- `heal_target_type` 与 `mdg_targets` / `rdg_targets`：正向标签为 **OR**

示例：

.. code-block:: text

   harm_target_type enemy unit -building
   heal_target_type unit -undead
   mdg_targets ground air -building


参考 mod：wuxia 逐技能对照
------------------


官方演示 mod：``mods/wuxia/rules.txt``。测试地图：``mods/wuxia/multi/skills_test.txt``。


+----+-----------+----+
| 技能 | effect 类型 | 要点 |
+====+===========+====+
| `skill_jifengci` | `burst mdg` | 5 连击，间隔 0.2s，窗口 1s，近战范围 2 |
+----+-----------+----+
| `skill_jifengci_rdg` | `burst rdg` | 同上，远程范围 6 |
+----+-----------+----+
| `skill_heng_sao` | `harm_area 50 3` | 固定 50 真实伤害，半径 3 |
+----+-----------+----+
| `skill_heng_sao_mdg` | `harm_area mdg 3` | 战斗管线 + 技能覆写 mdg/splash |
+----+-----------+----+
| `skill_lipi` | `harm_target 60` | 固定 60 真实伤害 |
+----+-----------+----+
| `skill_lipi_mdg` | `harm_target mdg` | 战斗管线单体伤害 |
+----+-----------+----+
| `skill_douzhuan` | `buffs b_douzhuan` | 自身增益；反弹见 buff `reflect_percent` |
+----+-----------+----+
| `skill_moli_dan` | `push 5` | 击退 5 格 |
+----+-----------+----+


载体单位 ``wuxia_hero`` 通过 ``can_use_skill`` 学会全部 8 个技能。

进阶
--


技能 burst 与单位 damage_seq 的区别
~~~~~~~~~~~~~~~~~~~~~~~~~~~



+----+-------------------+-----------------+
| 项目 | 技能 `effect burst` | 单位 `damage_seq` |
+====+===================+=================+
| 配置位置 | `class skill` 的 `effect` 行 | 单位 def 上的 `damage_seq` |
+----+-------------------+-----------------+
| 触发方式 | 手动或自动释放技能 | 普通攻击 / 远程攻击 |
+----+-------------------+-----------------+
| 伤害来源 | 技能或施法者 `mdg`/`rdg` + 战斗属性 | 单位 `mdg`/`rdg` 拆成多段 |
+----+-------------------+-----------------+
| 段数语法 | `burst mdg N (interval X)` | `damage_seq mdg N [(damage …)]` |
+----+-------------------+-----------------+
| 文档 | 本文 + `modding.htm` | `player/burst-attacks.htm` |
+----+-------------------+-----------------+


两者均走战斗管线，但配置入口与触发时机完全不同，请勿混用语法。

技能书与升级解锁
~~~~~~~~


- `level_skills <等级> <技能> …`：升级自动学会
- 物品 `skills` + `learn_level`：背包使用技能书学会
- 详见 `modding.htm` 与 `relnotes.htm` §1.4.4.6

音效
~~


技能 ``style.txt``：``alert``（选中）、``ready``（前摇）、``triggered``（生效）。攻击触发 buff 见 buff 的 ``triggered`` / ``noise loop``。

相关文档
----


- 单位自带治疗/伤害：`HEAL_HARM_自定义功能说明.md`（本文第二节）
- 战场 `class effect` 与 deploy：`EFFECT_BUFF_SYSTEM_说明.md`（本文第三节）
- 关键字大全：`modding.htm`
- 发布说明摘要：`relnotes.htm` §1.4.4.6

面向 **模组作者**：在 ``rules.txt`` 中为单位配置自带治疗光环、伤害光环、生命/法力回复节奏，无需 Python 源码。与主动技能（``class skill``）和战场区域（``class effect``）配合使用。

概述
--


自 1.4.1.7 起，单位的伤害与治疗拆分为细粒度参数，可写在 **单位 def** 或 **``class effect``** 上。单位上的参数表示该单位持续或周期性地对周围（或自身）产生治疗/伤害效果。

伤害参数（harm_*）
------------



+----+----+
| 属性 | 说明 |
+====+====+
| `harm_level` | 每次伤害量（直观数值，1 = 1 点） |
+----+----+
| `harm_cd` | 伤害间隔（秒）；内部以毫秒存储，如 7.5 秒写 `7.5` |
+----+----+
| `harm_ready` | 首次伤害前延迟（秒） |
+----+----+
| `harm_range` | 作用距离（从单位到目标） |
+----+----+
| `harm_radius` | 以目标为中心的作用半径 |
+----+----+
| `harm_target_type` | 目标筛选标签 |
+----+----+


示例（单位自带毒云）：

.. code-block:: text

   def poison_aura_unit
   class soldier
   harm_level 2
   harm_cd 3
   harm_radius 4
   harm_target_type enemy unit -building


harm_target_type 行为说明
~~~~~~~~~~~~~~~~~~~~~


- **1.4.4.6 起**：技能上的 `harm_target_type` 未配置时默认 **仅对敌人** 生效。
- 可写 `enemy`、`allied`、`ground`、`air`、`unit`、`building` 等；前缀 `-` 排除，如 `-building`、`-undead`。
- 正向标签为 **AND**（须全部满足）。
- 若未写 `enemy` / `allied` 等外交标签，旧版单位 harm 光环可能不分敌友；新 mod 建议显式写 `harm_target_type enemy …`。

治疗参数（heal_*）
------------



+----+----+
| 属性 | 说明 |
+====+====+
| `heal_level` | 每次治疗量 |
+----+----+
| `heal_cd` | 治疗间隔（秒） |
+----+----+
| `heal_ready` | 首次治疗前延迟 |
+----+----+
| `heal_range` | 作用距离 |
+----+----+
| `heal_radius` | 作用半径 |
+----+----+
| `heal_target_type` | 目标筛选；正向标签为 **OR** |
+----+----+


示例（牧师式治疗光环）：

.. code-block:: text

   def priest
   class soldier
   heal_level 3
   heal_cd 2
   heal_radius 5
   heal_target_type allied unit -undead


生命与法力回复（regen）
--------------



+----+----+
| 属性 | 说明 |
+====+====+
| `hp_regen` | 每秒生命回复 |
+----+----+
| `hp_regen_cd` | 回复 tick 间隔 |
+----+----+
| `hp_regen_ready` | 首次回复延迟 |
+----+----+
| `mana_regen` | 每秒法力回复 |
+----+----+
| `mana_regen_cd` | 法力回复间隔 |
+----+----+
| `mana_regen_ready` | 首次法力回复延迟 |
+----+----+


通过 buff 增强治疗/伤害
---------------


可在 buff 中修改 ``heal_level``、``heal_cd``、``heal_radius`` 或 ``harm_level`` 等（多属性 buff）。示例：

.. code-block:: text

   def HealEnhancementBuff
   class buff
   stat heal_level heal_cd heal_radius
   v 1 1500 6
   duration 300
   temporary 1


- `heal_level` 的 `v 1` = 真正 +1 点治疗
- `heal_cd` 的 `v 1500` = 1.5 秒冷却（毫秒）
- `heal_radius` 的 `v 6` = +6 范围

技能施加：``effect buffs HealEnhancementBuff``。

与 class effect 的关系
------------------


``class effect`` 实体使用相同的 ``harm_*`` / ``heal_*`` 参数，由技能 ``effect deploy`` 放置到战场。详见 ``EFFECT_BUFF_SYSTEM_说明.md``。

与技能 effect 的区别
--------------



+----+----+
| 方式 | 用途 |
+====+====+
| 单位 `harm_*` / `heal_*` | 单位常驻或周期光环 |
+----+----+
| `class effect` + `deploy` | 临时战场区域（火墙、圣光等） |
+----+----+
| `effect harm_target` / `harm_area` | 主动技能一次性/连击伤害 |
+----+----+
| `effect buffs` | 通过 buff 间接改 heal/harm 属性 |
+----+----+


**不存在** ``effect heal`` 的可执行技能效果；治疗请用上述三种方式之一。

升级成长
----


单位可配置 ``heal_cd_per_level``、``harm_radius_per_level`` 等 ``*_per_level`` 属性，升级时累加。详见 ``relnotes.htm`` §1.4.4.6。

参数对照速查
------



+----+----+----+
| 伤害 | 治疗 | 含义 |
+====+====+====+
| `harm_level` | `heal_level` | 每次数值 |
+----+----+----+
| `harm_cd` | `heal_cd` | 间隔 |
+----+----+----+
| `harm_ready` | `heal_ready` | 首次延迟 |
+----+----+----+
| `harm_range` | `heal_range` | 距离 |
+----+----+----+
| `harm_radius` | `heal_radius` | 半径 |
+----+----+----+
| `harm_target_type` | `heal_target_type` | 目标过滤 |
+----+----+----+


面向 **模组作者**：在 ``rules.txt`` 中用 ``class effect`` 配置战场区域效果，用 ``class buff`` / ``class debuff`` 配置增益减益；通过技能 ``effect deploy`` 或 ``effect buffs`` / ``debuffs`` 施加。无需 Python 源码。

战场效果（class effect）
------------------


自 1.4.1.7 起，``class effect`` 实体可在地图上持续造成范围伤害、治疗或携带 debuff。

伤害区域示例
~~~~~~


.. code-block:: text

   def exorcism
   class effect
   harm_level 2
   harm_cd 7.5
   harm_radius 6
   harm_target_type undead
   debuffs b_slow


治疗区域示例
~~~~~~


.. code-block:: text

   def holy_ground
   class effect
   heal_level 5
   heal_cd 3
   heal_radius 4
   heal_target_type allied unit


参数说明
~~~~


伤害与治疗参数与单位上的 ``harm_*`` / ``heal_*`` 相同（见第二节「单位治疗/伤害」）。``class effect`` 还可写 ``decay``（存活秒数，deploy 时也可由技能指定）。

通过技能部署
~~~~~~


.. code-block:: text

   def skill_blizzard
   class skill
   effect deploy 8 blizzard_fx
   effect_target ask
   effect_range 10


语法：``effect deploy <秒> [<数量>] <effect类型名>``

与 ``effect summon`` 不同：deploy 只生成 ``class effect``，不生成单位。可选 ``summon_requires_build_field`` / ``summon_requires_marked_field``（如菌毯肿瘤）。

内置示例见 ``res/rules.txt``（牧师 ``effect deploy`` + 驱魔 ``class effect``）。

Buff 与 Debuff（class buff / class debuff）
----------------------------------------


基本语法
~~~~


.. code-block:: text

   def b_slow
   class debuff
   stat speed
   v -2
   duration 10
   temporary 1
   stack 1



+----+----+
| 属性 | 说明 |
+====+====+
| `stat` | 影响的属性（可多个） |
+----+----+
| `v` | 固定加值 |
+----+----+
| `dv` | 每秒变化量（配合 `dt`） |
+----+----+
| `percentage` | 百分比加成 |
+----+----+
| `duration` | 持续时间（秒） |
+----+----+
| `temporary` | `1` = 死亡时移除 |
+----+----+
| `stack` | 叠加层数 |
+----+----+
| `target_type` | 可作为 buff 目标的条件（AND 逻辑） |
+----+----+
| `buff_radius` | 光环半径（光环型 buff） |
+----+----+


技能施加 buff
~~~~~~~~~


.. code-block:: text

   def skill_douzhuan
   class skill
   effect buffs b_douzhuan
   effect_target self


.. code-block:: text

   def skill_curse
   class skill
   effect debuffs b_slow
   effect_target ask
   effect_range 8


攻击也可附带：``buffs`` / ``debuffs`` 写在单位 def 上，或通过 ``attack_trigger_buffs`` 等触发。

伤害反弹（reflect_percent）
~~~~~~~~~~~~~~~~~~~~~


**没有** ``effect reflect`` 关键字。反弹须在 buff 上配置：

.. code-block:: text

   def b_douzhuan
   class buff
   duration 8
   temporary 1
   reflect_percent 100


再由技能 ``effect buffs b_douzhuan`` 施加。wuxia mod 的「斗转星移」即此模式。

``reflect_percent`` 为整数百分比（100 = 全额反弹）。

多属性 buff
~~~~~~~~


一个 buff 可同时影响多个属性：

.. code-block:: text

   def HealEnhancementBuff
   class buff
   stat heal_level heal_cd heal_radius
   v 1 1500 6
   duration 300
   temporary 1


值匹配规则：

- 属性数 = 值数：一一对应
- 值不足：用最后一个值填充
- 单个值：应用到所有属性

直观数值属性（``v 1`` = 1 点）：``hp``、``mdg``、``rdg``、``heal_level``、``harm_level``、``heal_radius``、``harm_radius``、``speed`` 等 20+ 项。

时间类（毫秒）：``heal_cd``、``harm_cd``、``mdg_cd``、``rdg_cd`` 等。

触发式 buff
~~~~~~~~


.. code-block:: text

   def CombatStanceBuff
   class buff
   stat mdg rdg
   v 30 25
   duration 100
   temporary 1
   is_active 1
   mdg_trigger_rate 80



+----+----+
| 模式 | 属性 |
+====+====+
| 攻击命中后 | 默认 |
+----+----+
| 发起攻击时 | `is_active 1` |
+----+----+
| 遭受攻击时 | `is_passive 1` + `trigger_condition` + `passive_trigger_rate` |
+----+----+


Buff 音效（style.txt）
~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def b_douzhuan
   triggered douzhuan_proc
   noise loop douzhuan_hum


- `triggered`：施加瞬间播放
- `noise loop`：持续期间循环
- `noise repeat <间隔> <音效…>`：按间隔重复

目标类型过滤（target_type）
-------------------


buff / debuff 的 ``target_type`` 语法与 ``harm_target_type`` 一致，多条件 **AND**。支持 ``-tag`` 排除：

.. code-block:: text

   target_type unit -undead -building


与技能系统的关系
--------



+-----------+----+
| 技能 effect | 作用 |
+===========+====+
| `effect deploy` | 放置 `class effect` |
+-----------+----+
| `effect buffs` / `debuffs` | 对目标施加 buff |
+-----------+----+
| `effect harm_target` / `harm_area` | 直接伤害（不经过 effect 实体） |
+-----------+----+


完整技能关键字见 ``GENERIC_SKILL_SYSTEM.md``（第一节）。

快速参考
----


治疗增强 buff
~~~~~~~~~


.. code-block:: text

   def heal_aura_buff
   class buff
   stack 1
   stat heal_level heal_cd heal_radius
   v 1 1500 6
   temporary 1
   duration 10
   target_type self


伤害增强 buff
~~~~~~~~~


.. code-block:: text

   def harm_aura_buff
   class buff
   stack 1
   stat harm_level harm_cd harm_radius
   v 2 -1000 4
   temporary 1
   duration 15
   target_type self


在 ``MULTI_ATTRIBUTE_BUFF_说明.md <MULTI_ATTRIBUTE_BUFF_说明.htm>``_ 中有更完整的多属性 buff 示例。伤害反弹使用 buff 属性 ``reflect_percent``（整数百分比，100 = 全额反弹），由技能 ``effect buffs`` 施加；无独立 ``effect reflect``。wuxia 示例见 ``b_douzhuan``。
