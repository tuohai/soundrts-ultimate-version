星际 mod：异虫菌毯与女王肿瘤
============================


在 ``SoundRTS.ini`` 中启用 ``mods = starcraft``。

规则关键字：``mod/modding.rst`` （建造场一节）。人族/神族说明见 `星际人族附属建筑与重组说明 <星际人族附属建筑与重组说明.htm>`_、`星际资源与气矿说明 <星际资源与气矿说明.htm>`_。


----


1. 两种半径属性
---------------


每个菌毯/灵能提供者只设一种，另一种保持 0。


.. list-table::
   :header-rows: 1

   * - 属性
     - 范围
     - 说明
   * - ``build_field_radius``
     - 从建筑所在格 BFS 的格数
     - 离散铺格，旧式写法
   * - ``build_field_radius_m``
     - 从建筑 ``(x,y)`` 的米制距离
     - 与攻击距离同尺度；一格约 12 米



星际 mod 默认值：


.. list-table::
   :header-rows: 1

   * - 建筑
     - 半径
   * - 主巢 Hatchery
     - ``build_field_radius_m 12``
   * - 菌毯肿瘤
     - ``build_field_radius_m 4``
   * - 主基地 Nexus
     - 18 m
   * - 水晶塔 Pylon
     - 12 m




----


2. 实时菌毯 vs 格标记
---------------------



.. list-table::
   :header-rows: 1

   * - 类型
     - 含义
   * - 实时（live）
     - 主巢/肿瘤仍在时当前覆盖的范围（移动时可听到菌毯）
   * - 标记（marked）
     - 持久格标记 + 每秒蔓延（``build_field_persists``、``build_field_spreads``）



- 异虫建筑必须在已标记的格上建造（``requires_build_field_on_square 1``）。
- 主巢被毁后标记菌毯仍在，可在残留菌毯上建造。
- 仅写米制半径的主巢在开启 ``build_field_persists`` / ``build_field_spreads`` 时也会绘制标记，否则会出现「听得见菌毯但提示此处没有菌毯」。


----


3. 蔓延
-------


``build_field_spreads 1`` — 每秒向相邻格蔓延一层标记；``build_field_spread_squares N`` 可加快。

测试图：``mods/starcraft/multi/zerg_creep_test.txt``。


----


4. 女王菌毯肿瘤（类似 SC2）
---------------------------


在女王巢穴（需孵化池）训练 女王。


.. list-table::
   :header-rows: 1

   * - 技能
     - 消耗
     - 射程
     - 目标要求
   * - 生成菌毯肿瘤
     - 25 法力，施法 20 秒
     - 11
     - 格上有实时或标记菌毯
   * - 延伸菌毯肿瘤（肿瘤自带）
     - 施法 12 秒
     - 8
     - 格上须为已标记菌毯



- 生成在目标格召唤隐形 ``creep_tumor`` 建筑。
- 肿瘤提供 4 m 菌毯并像主巢一样蔓延。
- 延伸用于向远处链式铺菌毯；不能铺在仅有实时范围、尚未标记的边缘格上。

测试图：``mods/starcraft/multi/zerg_creep_tumor_test.txt``。

模组技能属性示例：

.. code-block:: text

   summon_requires_build_field creep
   summon_requires_marked_field 1    ; 仅延伸技能



----


5. 操作要点
-----------


1. 主巢铺菌毯 → 等待蔓延，或用女王肿瘤铺到远处。
2. 异虫建筑只能建在已标记菌毯格上。
3. 主巢被毁后在残留菌毯上建造 — 见 ``zerg_creep_test`` 第二阶段。
