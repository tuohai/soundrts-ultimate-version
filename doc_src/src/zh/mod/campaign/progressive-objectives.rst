渐进式战役目标（``register_objective``）
========================================


适用于单人地图：逐条显示主要目标（完成 1 后再播报 2），且不能提前通关。

官方触发器说明：``mod/mapmaking.rst`` （Register_objective 一节）。


----


1. 问题
-------


每次 ``add_objective`` 会做两件事：

1. 在 F9 显示目标并播报「新目标」语音。
2. 把该编号加入通关所需集合。

若开局只 ``add_objective 1``，完成目标 1 后再 ``add_objective 2``，可能在目标 2 尚未显示时就误判胜利（旧逻辑按「当前可见目标全部完成」判定）。


----


2. 做法：``register_objective``
--------------------------------


开局登记全部主要编号，不显示、不播报：

.. code-block:: text

   trigger player1 (timer 0) (do (register_objective 1 2 3) (add_objective 1 7001))
   trigger player1 (has barracks) (do (objective_complete 1) (add_objective 2 7002))
   trigger player1 (has 10 footman) (objective_complete 2)
   trigger player1 (has townhall) (objective_complete 3)



.. list-table::
   :header-rows: 1

   * - 动作
     - F9 / 语音
     - 胜利集合
   * - ``register_objective 1 2 3``
     - 否
     - 写入 ``\_required_objective_numbers``
   * - ``add_objective 1 …``
     - 是
     - 若未登记也会加入 1
   * - ``objective_complete 1``
     - 从 F9 移除目标 1
     - 写入 ``\_completed_objective_numbers``



当 ``\_required_objective_numbers`` 中每个编号都在 ``\_completed_objective_numbers`` 里时触发 ``victory()`` （``soundrts/worldplayerbase/base.py`` — ``\_all_required_objectives_done``）。


----


3. F9 与语音序号
----------------


多个主要目标（已登记或已显示）时：

- F9 与 ``add_objective`` 播报 「主要目标 N：」 再读描述（序号后带冒号）。
- 仅一个主要目标时不读序号。

地图加载时会扫描全部触发器（``soundrts/objective_announce.py`` — ``collect_planned_objective_numbers``），因此 ``add_objective`` 分散在不同 ``timer 0`` 触发器里也能正确决定是否读序号。

可选目标（``add_secondary_objective``）编号独立，规则相同。


----


4. 仓库示例
-----------



.. list-table::
   :header-rows: 1

   * - 地图
     - 说明
   * - ``mods/starcraft/single/sc_build_tests/1.txt``
     - 2 个链式神族目标
   * - ``mods/starcraft/single/sc_late_game/1.txt``
     - 6 个链式后期目标




----


5. 测试
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_campaign_alliance_transfer_triggers.py -k register_objective -q
   python -m pytest soundrts/tests/test_objective_announce.py -q
   python -m pytest soundrts/tests/test_cmd_objectives.py -q
