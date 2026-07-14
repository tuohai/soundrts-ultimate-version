单位默认模式与自动状态配置说明（rules.txt）
===========================================


本功能让地图/模组作者可以在 ``rules.txt`` 里按单位类型配置该单位开局时的默认行为状态，
包括：

- 默认 AI 模式（``ai_mode``）：进攻 / 防御 / 站岗 / 追击；
- 默认自动采集（``auto_gather``）：工人是否一开始就自动采集资源；
- 默认自动修理（``auto_repair``）：工人是否一开始就自动修理友方建筑/船只；
- 默认自动探索（``auto_explore``）：可移动单位是否一开始就自动四处探路。
- 默认占领命令（``can_capture``）：有攻击能力的单位对 ``capture_hp_threshold 100`` 目标是否默认占领。

这些配置决定了游戏开局时每个单位的初始状态，玩家之后仍可在游戏内手动切换。


----


1. 功能概述
-----------



.. list-table::
   :header-rows: 1

   * - 字段
     - 取值
     - 默认值
     - 作用对象
     - 说明
   * - ``ai_mode``
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
     - 兵种=``offensive``，工人=``defensive``
     - 所有作战单位
     - 开局默认 AI 模式
   * - ``auto_gather``
     - ``1`` / `0`
     - 工人=`1`
     - 工人（worker）
     - 开局是否自动采集资源
   * - ``auto_repair``
     - ``1`` / `0`
     - 工人=`1`
     - 工人（worker）
     - 开局是否自动修理
   * - ``auto_explore``
     - ``1`` / `0`
     - ``0`` （关闭）
     - 可移动单位
     - 开局是否自动探索（初始状态）
   * - ``can_auto_explore``
     - ``1`` / `0`
     - ``0`` （关闭）
     - 可移动单位
     - 该单位命令菜单里是否提供"启用/禁用自动探索"选项




这些字段都写在某个单位的 `def <单位名>` 定义块里。未写时使用上表的默认值。

战役示例：关键 NPC（第 24–27 章）通过 ``escort`` 基类或 ``ai_mode guard`` 配置站岗，
交付/比武前不主动远距追击。结盟后可用触发器切换模式：

- `(set_ai_mode offensive c2 1 npc_count_roland …)` — 交信物后罗兰切追击（第 25 章）
- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order (c2 4 npc_knight_escort) ((go c1)))` 等 — 第 27 章（``raynor7``）：仅马尔科切进攻；护卫前往 ``c1`` 让出阵前
- `(allied_assist computer1)` — 全盟友可战斗站岗单位切追击
- `(allied_assist computer1 c2 4 npc_archer_escort)` — 仅护卫射手切追击
- `(allied_control computer1 c2 4 npc_knight_escort)` — 护卫骑士交玩家指挥（保持站岗），其余自动切追击

比武认输（``yield_on_defeat``）建议用运行时 `` (set_yield_on_defeat 1 …)`` 开启，而非开局写在
``rules.txt``，这样交信物前 NPC 可被击杀（误杀判失败）。详见 `战役密信与结盟说明 <战役密信与结盟说明.htm>`_。


``auto_explore`` 与 ``can_auto_explore`` 的区别：

``auto_explore`` 决定单位开局是否处于自动探索状态（初始开/关）。

``can_auto_explore`` 决定玩家能否在该单位的命令菜单里看到"启用/禁用自动探索"选项，

即把自动探索作为该单位可手动开关的功能。

二者独立：可以只给 ``knight`` 配 ``can_auto_explore 1`` （让玩家手动开关），其它单位不配；

也可以用 ``auto_explore 1`` 让某单位开局就自动探索。


----


2. AI 模式（ai_mode）
---------------------


2.1 可用模式
~~~~~~~~~~~~


游戏里作战单位有 4 种可循环切换的 AI 模式，``ai_mode`` 只能取其中之一：


.. list-table::
   :header-rows: 1

   * - 取值
     - 名称
     - 行为
   * - ``offensive``
     - 进攻
     - 主动攻击当前格子里的敌对单位（最常见的默认）
   * - ``defensive``
     - 防御
     - 对敌对威胁战力不利时会撤退；占优时才主动交战
   * - ``guard``
     - 站岗
     - 不主动出击，原地驻守；仅在开启反击时才反击
   * - ``chase``
     - 追击
     - 锁定敌人后由同一个 ``AttackAction`` 经出口跨格持续跟随（不下自动 ``go``），直到进入射程交战


2.1.1 驻守点（``position_to_hold``）与离格
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


单位出生时会带上当前方格作为 ``position_to_hold``。在驻守范围内时，引擎的 ``_must_hold``
会阻止擅自走到格外坐标：


.. list-table::
   :header-rows: 1

   * - AI 模式
     - 受 ``position_to_hold`` 限制？
   * - ``offensive`` / ``guard``
     - 是（未接到会 ``stop()`` 的命令时，不宜自行跨格）
   * - ``defensive``
     - 否（便于受威胁时撤退）
   * - ``chase``
     - 否（跨格追击前会清 hold，才能真正跟随）


玩家下达普通 ``go`` / ``attack`` 等命令时，命令首次执行会 ``stop()``，从而清掉
``position_to_hold``，之后可正常跨格。

关于"巡逻"：游戏里的"巡逻"（patrol）是一条需要指定往返路线的命令，不是一种可作为

"开局默认状态"的 AI 模式，因此不能写成 ``ai_mode patrol``。想要"主动巡防"的效果，

可用 ``guard`` （原地驻守）或 ``chase`` （主动追击并跨格跟随敌人）。

2.2 配置示例
~~~~~~~~~~~~


.. code-block:: text

   def knight
   class soldier
   ...
   ai_mode guard      ; 骑士开局默认站岗
   
   def footman
   class soldier
   ...
   ai_mode defensive  ; 步兵开局默认防御


2.3 与中立单位的关系
~~~~~~~~~~~~~~~~~~~~


玩家单位在 ``offensive`` / ``defensive`` / ``chase`` 三种模式下：

- 不会主动攻击地图上的中立单位（`computer_only ... neutral` 刷出的中立 creep / NPC / 野生动物）；
- 不会因中立单位而撤退（防御模式仅根据真实敌对威胁评估战力，中立不计入威胁）；
- 对中立单位的默认 / 普通 ``go``（非强制）只移动，不挂攻击动作；
- 对可狩猎动物（``is_huntable``）的默认命令仍是 ``attack``，普通攻击可正常造成伤害；
- 若要让 AI 把中立 creep / NPC 当作自动交战目标，须下达强制攻击命令（``imperative``：
  例如对单位 Ctrl+点击 / 强制移动，引擎会转为 ``attack``）。


语音区分：狩猎动物（``is_huntable`` / ``herdable``，如鹿、羊）播报为「鹿 , 动物」，不是

「中立 , NPC」。剧情 NPC（``quest_npc`` 等）仍播报「中立 , NPC」。详见

`狩猎系统说明.md <狩猎系统说明.htm>`_。


站岗模式（``guard``）逻辑不变：仍不主动出击，仅在开启反击且遭受攻击时反击。

中立电脑自身的 ``guard`` + 被动反击行为也不受本节影响。

2.4 说明
~~~~~~~~


- 配置的取值会校验，非法取值（例如拼写错误）会被忽略并回退到默认模式，同时在日志里告警。
- 中立电脑（`computer_only ... neutral`）的单位仍会被引擎强制设为 ``guard`` + 开启反击
  （"被动反击型 creep"），这是刻意行为，不受 ``ai_mode`` 配置影响。


----


3. 自动采集 / 自动修理（auto_gather / auto_repair）
---------------------------------------------------


这两个状态作用于工人（worker），控制工人空闲时是否自动找活干。

- ``auto_gather 1``：工人空闲且附近有可采集资源点 + 对应仓库时，自动前往采集。
- ``auto_repair 1``：工人空闲且同格有受损的友方可修理单位时，自动修理（需要工人本身
  ``can_repair 1``）。

工人默认两者都为 开启。要按需关闭其一，在工人定义里写 ``0`` 即可。

配置示例
~~~~~~~~


.. code-block:: text

   def peasant
   class worker
   ...
   auto_gather 1      ; 开局自动采集（默认就是开，可省略）
   auto_repair 0      ; 开局禁用自动修理



这两个状态玩家在游戏内本来就能通过"启用/禁用自动采集"、"启用/禁用自动修理"命令切换；

本功能只是让你能设定开局时的初始值。


----


4. 自动探索（auto_explore）
---------------------------


``auto_explore`` 是新增的自动状态，作用于任何可移动单位（速度 > 0）。它由两个独立
字段控制：``auto_explore`` （初始状态）与 ``can_auto_explore`` （命令菜单是否提供该选项）。

4.1 把自动探索作为"可手动开关的功能"（can_auto_explore）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


如果你希望玩家能在某个单位的命令菜单里手动启用/禁用自动探索，给该单位配置
``can_auto_explore 1`` 即可。只配置了的单位才会出现这两个命令选项，其它单位看不到。

.. code-block:: text

   def knight
   class soldier
   ...
   can_auto_explore 1   ; 只有骑士的命令菜单里有"启用/禁用自动探索"选项
   
   def footman
   class soldier
   ...
                        ; 不配 can_auto_explore → 步兵命令里没有自动探索选项


这样玩家选中骑士时，命令列表里会多出"启用自动探索"（开启后变为"禁用自动探索"）；
选中步兵时则没有该选项。

4.2 让单位开局就自动探索（auto_explore）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def knight
   class soldier
   ...
   auto_explore 1       ; 骑士开局即自动探索（初始状态为开）
   can_auto_explore 1   ; 同时让玩家可在菜单里随时开关（推荐一起配）


- ``auto_explore 1``：该单位开局即自动探索——空闲时会自动走向未探明/需要侦察的区域，
  把地图探开；一旦发现敌人，单位的战斗逻辑会自动接管（按其 ``ai_mode`` 交战）。
- 默认值为 ``0`` （关闭）。


建议：想让单位"开局就探索且玩家能关掉"，把 ``auto_explore 1`` 和 ``can_auto_explore 1``

一起配。仅配 ``auto_explore 1`` 时玩家仍能"禁用"（见下方运行行为），但关掉后无法再通过

菜单重新启用（因为没有开放该选项）。

4.3 运行行为
~~~~~~~~~~~~


- 持续状态：开启后，单位每次变空闲都会重新开始探索。
- 被命令打断：玩家给它下达其它命令（移动、攻击等）会暂停探索；该命令完成、单位再次
  空闲时，会自动恢复探索。
- 彻底停止：使用 "禁用自动探索" 命令即可关闭。该命令只要单位当前正处于自动探索
  状态就会出现（即便没配 ``can_auto_explore``），避免"开着却关不掉"。
- 重新启用："启用自动探索"命令只对配置了 ``can_auto_explore 1`` 的单位出现。
- 计算机玩家的探索仍由其 AI 自行管理，不依赖这两个字段。


----


5. 默认占领命令（can_capture）
------------------------------


对有 攻击能力 的单位（士兵、工人等），可配置右键指向 :strong:```capture_hp_threshold 100`` 敌方目标时的默认命令：


.. list-table::
   :header-rows: 1

   * - 值
     - 行为
   * - ``1`` （默认）
     - 默认 占领（``capture`` 命令）；AI 对该目标也走接触即占领
   * - ``0``
     - 默认 攻击/移动；AI 正常攻击，不自动占领



不影响：较低夺取阈值（如 ``capture_hp_threshold 30``）仍通过战斗伤害触发夺取；``can_capture`` 主要控制 阈值 100 的接触即占领 与默认右键命令。

配置示例
~~~~~~~~


.. code-block:: text

   def footman
   class soldier
   can_capture 1      ; 可占领兵营（默认，可省略）
   
   def archer
   class soldier
   can_capture 0      ; 只能打兵营，不会默认占领


目标建筑示例（写在 ``rules.txt`` 或 mod 中）：

.. code-block:: text

   def captured_barracks
   class building
   capture_hp_threshold 100
   can_train footman 5 archer 3


详见 `英雄无敌与文明5玩法说明 <英雄无敌与文明5玩法说明.htm>`_ 中的可占领兵营 POI。


----


6. 综合示例
-----------


.. code-block:: text

   ; 工人：开局自动采集、不自动修理、AI 防御
   def peasant
   class worker
   cost 50 0
   auto_gather 1
   auto_repair 0
   ai_mode defensive
   
   ; 骑士：开局自动探索、命令里提供自动探索开关、站岗模式
   def knight
   class soldier
   cost 60 20
   auto_explore 1
   can_auto_explore 1
   ai_mode guard
   
   ; 步兵：开局防御模式（不探索）
   def footman
   class soldier
   cost 60 0
   ai_mode defensive



----


7. 常见问题
-----------


``Q：``ai_mode patrol`` 为什么不生效？``
A：patrol（巡逻）是需要路线目标的命令，不是 AI 模式。合法取值只有
``offensive`` / ``defensive`` / ``guard`` / ``chase``。

``Q：给建筑写 ``auto_explore 1`` 会怎样？``
A：建筑不能移动（速度为 0），该配置对其无效，会被忽略。

``Q：``auto_gather`` / ``auto_repair`` 写在兵种（soldier）上有用吗？``
A：这两个状态只对工人有意义。写在不具备采集/修理能力的单位上不会生效。

``Q：开了 ``auto_explore`` 的单位老是自己跑掉，怎么让它停下？``
A：游戏内用"禁用自动探索"命令关闭；或者它本来就是"空闲即探索"的设计，给它下个驻守/移动
命令也能临时停住。

Q：我只想让某些单位（如骑士）有"启用/禁用自动探索"的命令选项，怎么做？
A：只给这些单位配 ``can_auto_explore 1``，不配的单位命令菜单里不会出现自动探索选项。

``Q：``auto_explore`` 和 ``can_auto_explore`` 有什么区别？``
A：``auto_explore`` 是开局初始状态（开/关）；``can_auto_explore`` 是命令菜单是否提供
开关选项。想要"开局就探索且能手动关"，两个都配 ``1``。

Q：追击模式和以前「自动 go 跳格」有什么区别？
A：现在锁定敌人后保持攻击动作跨格跟随，不再靠自动 ``go``；且追击不受
``position_to_hold`` 限制。进攻 / 站岗仍受驻守限制，除非玩家下令移动。

Q：进攻/追击模式下，单位会自动打地图上的中立 NPC 吗？
A：不会。三种主动交战模式（进攻、防御、追击）都不会把中立单位当作自动攻击目标；
只有对该单位使用强制攻击命令才会开战。防御模式下也不会因路过中立者而逃跑。

Q：为什么弓箭手右键兵营是攻击，步兵是占领？
A：检查单位是否写了 ``can_capture 0``。默认 ``can_capture 1`` 时，对 ``capture_hp_threshold 100``
的目标会默认占领；设为 ``0`` 则改为普通攻击。


----


8. 涉及的字段一览
-----------------



.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 合法值
   * - ``ai_mode``
     - 字符串
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
   * - ``auto_gather``
     - 整数
     - ``1`` （开）/ ``0`` （关）
   * - ``auto_repair``
     - 整数
     - ``1`` （开）/ ``0`` （关）
   * - ``auto_explore``
     - 整数
     - ``1`` （开局开启）/ ``0`` （关）
   * - ``can_auto_explore``
     - 整数
     - ``1`` （菜单提供开关选项）/ ``0`` （不提供）
   * - ``can_capture``
     - 整数
     - ``1`` （默认占领）/ ``0`` （普通攻击）

