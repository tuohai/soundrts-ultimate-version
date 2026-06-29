地图制作指南（入门与进阶）
==========================


先做一张能打的图，再加触发器与高级地形。语法大全见 `地图制作手册 <mapmaking.htm>`_ （同目录）。
.. contents::

----

入门：放哪里、怎么测
--------------------

.. list-table::
   :header-rows: 1

   * - 位置
     - 说明
   * - ``user/multi/``
     - 私人地图（推荐）
   * - 游戏目录 ``multi/``
     - 随游戏分发
   * - ``user/single/…/N.txt``
     - 战役章节（见 `战役制作指南 <campaign-guide.htm>`_）

测试：主菜单 → 单人 → 选你的图 → 对战电脑。每次开局重载地图，无需重启。  
排错：报 map error 时看 ``user/tmp/client.log``。  
开全图（仅单人、唯一人类玩家）：Control+Shift+F2。

入门：最小多人图
----------------

.. code-block:: text

   title 4018 5000
   objective 145 88
   nb_players_min 2
   nb_players_max 2
   squares 3 3
   goldmines 1 1 5000
   woods 2 2 5000
   players 1 1 1

保存为 ``user/multi/my_map.txt``，按上一节测试。

进阶：触发器
------------

在地图里用 ``trigger`` / ``if`` 控制刷兵、对话、胜利。  
完整关键字与示例 → `地图制作手册 <mapmaking.htm>`_ 触发器章节；战役专用动作 → `战役制作指南 <campaign-guide.htm>`_。

进阶：子格地形（1.4.4.8+）
--------------------------

同一大格内可定义局部高地、水域等：

.. code-block:: text

   subcell_precision 20
   high_grounds a1/10,10
   terrain mountain a1/1,1

缩放模式下浏览会按子格播报地形；编辑器在缩放模式按 Enter 写入当前子格。  
详见 `版本说明 <../relnotes.htm>`_ 1.4.4.8 节与 `地图制作手册 <mapmaking.htm>`_。

随机地图（RMG）
---------------

作者参数 → `随机地图手册 <randommap.htm>`_  
玩家菜单与分享码 → `随机地图（玩家向） <../player/random-map-play.htm>`_

HoMM / 文明5 式 POI
-------------------

玩家向玩法 → `英雄无敌 / 文明5 式地图 <../player/homm-civ5-play.htm>`_
