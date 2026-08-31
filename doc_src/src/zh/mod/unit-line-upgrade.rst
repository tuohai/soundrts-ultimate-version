单位线升级与最高阶训练（line_upgrade）
====================================

面向 **模组作者**：在 ``rules.txt`` 中配置“研究单位形态 → 解锁训练最高阶 → 场上同线变形”，无需在引擎里写死单位名。帝国时代 2 DE 的兵营剑线等即按此模式工作。

概述
----

.. list-table::
   :header-rows: 1

   * - 能力
     - 说明
   * - 最高阶训练
     - 建筑 ``can_train`` 写线根（如 ``militia``），实际训练当前已解锁的最高形态
   * - 可研究线升级
     - 形态标 ``line_upgrade 1``，并写入建筑 ``can_research``；研究后记入 ``player.upgrades``
   * - 场上变形
     - 研究完成时，把 ``can_upgrade_to`` 含该形态的场上单位瞬时升到该阶
   * - 训练队列
     - 研究完成时，同线已排队 / 正在训练的命令改成新形态（帝国 2 DE：队列里的轻型投石车造出来是中型）。已付训练费与剩余时间不变
   * - 训练费用
     - 默认按**线根**的 ``cost`` / ``time_cost`` 收费（可用 ``train_cost`` / ``train_time`` 覆盖）

引擎**不硬编码**任何文明或单位 id，只认规则字段与 ``can_upgrade_to`` 链。

rules 写法
----------

1. 单位线（``can_upgrade_to``）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def militia
    class soldier
    cost 20 0 50 0
    time_cost 21
    can_upgrade_to man_at_arms

    def man_at_arms
    is_a militia
    cost 40 0 100 0
    time_cost 40
    requirements feudal_age
    line_upgrade 1
    can_upgrade_to long_swordsman

- 中阶/高阶的 ``cost`` / ``time_cost`` 通常表示**研究**价格（与 DE 一致）。
- 训练仍走线根费用，除非写了 ``train_cost`` / ``train_time``。

2. 建筑：训练槽 + 研究槽
~~~~~~~~~~~~~~~~~~~~~~~~

::

    def barracks
    class building
    can_train militia spearman
    can_research tracking squires man_at_arms long_swordsman …

- ``can_train`` 只列线根；菜单会映射到已解锁的最高阶。
- ``can_research`` 列入带 ``line_upgrade 1`` 的形态后，即可当科技研究。

3. 可选：科技 effect
~~~~~~~~~~~~~~~~~~~~

若用 ``class upgrade`` 包一层，可写::

    effect unit_line_upgrade man_at_arms

效果与直接研究该单位形态相同（写入 upgrades + 变形）。同一目标对同一玩家只生效一次。

与时代自动变形的关系
--------------------

.. list-table::
   :header-rows: 1

   * - 标记
     - 行为
   * - （无特殊标记）
     - 若 phase 开了 ``units_auto_upgrade 1``，且目标 ``requirements`` 含该时代名，可随时代自动变形
   * - ``line_upgrade 1``
     - **不**随时代自动变形；须研究解锁；训练解析也要求该名已在 ``player.upgrades``
   * - ``no_auto_upgrade 1``
     - 跳过时代自动变形；训练解析同样要求已研究（与 ``line_upgrade`` 相同门槛）

AoE2 DE 军事线推荐统一用 ``line_upgrade 1``（研究解锁），不要只靠 ``units_auto_upgrade``。

选中单位菜单上的 ``upgrade_to`` **不会**再出现指向 ``line_upgrade`` 形态的选项（避免按差价单兵付费，与帝国2不符）；请在建筑 ``can_research`` 里研究。

建筑线（箭塔、垛墙）同样：``can_build`` 写线根，研究后菜单映射到最高阶；建造费按线根（可用 ``train_cost``）。一研多项可用 ``line_upgrade_also``（如垛墙顺带解锁强化城门）。

引擎入口（查阅用）
------------------

.. list-table::
   :header-rows: 1

   * - 符号
     - 位置
   * - ``resolve_trainable_unit_type``
     - ``soundrts/world_build_rules.py``
   * - ``effective_can_train`` / ``unit_train_cost`` / ``unit_train_time``
     - 同上
   * - ``apply_unit_line_upgrade``
     - 同上
   * - ``remap_queued_train_orders_for_line_upgrade`` / ``resolved_train_type_class``
     - 同上
   * - ``ResearchOrder.complete``
     - ``soundrts/worldorders/production.py``
   * - ``effect_unit_line_upgrade``
     - ``soundrts/worldupgrade/attribute_effects.py``
   * - 时代跳过
     - ``soundrts/worldphase.py`` → ``_auto_upgrade_units``
   * - 单位默认属性
     - ``Creature.line_upgrade``（``worldcreature.py``）
   * - 规则 int 属性
     - ``definitions.py`` → ``line_upgrade``

测试
----

``soundrts/tests/test_train_line_resolve.py``：时代 alone 不解锁；写入 upgrades / ``apply_unit_line_upgrade`` 后才训练最高阶并变形；研究完成会改写同线训练队列。

aoe2 模组
---------

``mods/aoe2/rules.txt`` 已为剑线、矛、弓、马、攻城等升级形态加 ``line_upgrade 1``，并挂到兵营/靶场/马厩/车间及文明变体的 ``can_research``。数据出处见 ``mods/aoe2/SOURCES.md``。

另见：`Mod 制作手册 <modding.htm>`_。
