战役制作指南
============


从 ``campaign.txt`` 到触发器脚本——入门讲结构，进阶讲物品、目标与合作。语法细节另见 `地图制作手册 <mapmaking.htm>`_。
.. contents::

----

入门：战役文件夹
----------------

典型结构（放在 ``user/single/我的战役/`` 或 mod 的 ``single/`` 下）：

.. code-block:: text

   my_campaign/
     campaign.txt
     0.txt
     1.txt
     rules.txt       ; 可选

``campaign.txt`` 常用字段：``title``、``chapters``、``difficulty``、合作相关标志。  
每章 ``N.txt`` 的写法与多人地图相同。

建议：先用 `地图入门 <map-guide.htm>`_ 做一张能单机测的多人图，再拆成战役第一章。

入门：第一张战役章
------------------

1. 复制一张已通过测试的 ``multi/*.txt`` 为 ``0.txt``
2. 在 ``campaign.txt`` 里登记章节
3. 主菜单 → 单人 → 战役 → 选你的战役 → 打第一章

每改 ``0.txt`` 后重开该章即可，不必重启游戏。

----

进阶专题（详细语法）
--------------------

下列专题为独立页面，按需在浏览器中打开：

- `渐进式目标 register_objective <campaign/progressive-objectives.htm>`_
- `寻找物品 has_item <campaign/find-item.htm>`_
- `交给 NPC <campaign/give-to-npc.htm>`_
- `指定序号目标 <campaign/unit-index.htm>`_
- `英雄跨章携带 <campaign/hero-carryover.htm>`_
- `合作战役 <campaign/coop.htm>`_

玩家向说明
----------

- `战役菜单与合作 <../player/campaign-menu.htm>`_
- `北方战役 24–27 章 <../player/campaign-northern-arc.htm>`_
- `携带物品（玩家） <../player/brought-items.htm>`_
