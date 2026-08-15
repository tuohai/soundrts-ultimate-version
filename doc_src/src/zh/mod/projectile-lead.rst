投射物预判（projectile_lead）与分路飞行速度
==========================================

面向 **模组作者**：近战/远程投射物各自配置**飞行速度**（格/秒）；非投射物攻击不受影响。

重要：字段是速度，不是时长
--------------------------

``rdg_projectile_speed`` / ``mdg_projectile_speed``（及已弃用的 ``projectile_speed``）表示**飞多快**（tiles per second），**不是**「飞了多少秒」。

- 写 ``7`` → 每秒飞 7 格（帝国2弓箭手量级）
- **不要**把「希望半秒命中」写成 ``0.57``——那会被当成每秒只飞 0.57 格，满射程会慢到数秒
- 实际从开火到命中要多久，由引擎按 **距离 ÷ 速度** 推算，距离越远时间越长

概述
----

.. list-table::
   :header-rows: 1

   * - 字段
     - 说明
   * - ``rdg_projectile`` + ``rdg_projectile_speed``
     - 远程投射物：**速度**（格/秒）
   * - ``mdg_projectile`` + ``mdg_projectile_speed``
     - 近战投射物：**速度**（格/秒，如投石车）
   * - ``projectile_lead``
     - 仅远程：按速度推算到达后，若目标已离开瞄准点则 miss
   * - ``projectile_speed``
     - **已弃用**共用名；加载时按投射物标志迁到上两路

速度为 0、或该路不是投射物 → 即时命中（无飞行）。

双持攻单位
----------

若单位同时有 ``mdg`` 与 ``rdg``（例如 range 都是 4）：

- 只写 ``rdg_projectile_speed`` → **只有远程**按该速度飞行；近战即时（除非另有 ``mdg_projectile``+速度）
- 只写 ``mdg_projectile_speed`` → **只有近战投射物**按该速度飞行
- 普通近战（无 ``mdg_projectile``）即使写了速度也**不会**飞

rules 示例
----------

::

    def aoe_archer
    rdg_projectile 1
    rdg_projectile_speed 7

    def mangonel
    mdg_projectile 1
    mdg_projectile_speed 3.5

    def ballistics
    class upgrade
    effect info 8510
    effect bonus projectile_lead 1
    effect_bonus_targets archer_unit -hand_cannoneer galley scouttower aoe_castle town_center townhall

aoe2 约略（均为**速度**）：箭/塔 ``7``，投石车 ``3.5``，投石机 ``1.6``。

已弃用
------

``mdg_delay`` / ``rdg_delay``（旧「延迟秒数」写法）与共用 ``projectile_speed``：战斗不直接读；加载时换算/迁到分路**速度**。新模组请直接写 ``*_projectile_speed``。

引擎
-----------

- ``attack_action._calc_projectile_flight_ms(target, is_melee=…)``（由速度推算到达毫秒）
- ``definitions._migrate_legacy_projectile_delay``

另见：`Mod 制作手册 <modding.htm>`_、`版本说明 <../relnotes.htm>`_（1.4.6.9）。
