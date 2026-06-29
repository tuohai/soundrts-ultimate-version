Mod 入门制作指南
================


第一次改规则、第一次看到效果——不涉及地图触发器与完整战役。下一步：`Mod 制作进阶指南 <advanced.htm>`_。
------------------------------------------------------------------------------------------------------

你会改什么？
------------

SoundRTS 的 mod 是文本文件夹：改完保存，重开地图或重启游戏即可试验。

.. list-table::
   :header-rows: 1

   * - 文件
     - 作用
   * - ``rules.txt``
     - 单位数值、科技、技能（本指南重点）
   * - ``style.txt`` + ``ui/tts.txt``
     - 名称、简介、音效 ID
   * - ``ai.txt``
     - 电脑怎么造兵（进阶时再学）

语法大全 → `Mod 制作手册 <modding.htm>`_ （查关键字时用）。

----

第一步：工作目录与激活
----------------------

.. list-table::
   :header-rows: 1

   * - 路径
     - 说明
   * - ``user/mods/你的mod名/``
     - 推荐：私人 mod
   * - 游戏目录 ``mods/``
     - 随游戏分发、给他人用

在选项菜单可打开 user 文件夹。便携版：在游戏根目录建 ``user/`` 即可。

激活 — 编辑 ``user/SoundRTS.ini``：

.. code-block:: ini

   mods = mymod

多个 mod 用逗号分隔；后面的覆盖前面的同名定义。  
开发时可命令行：``python soundrts.py --mods=mymod``

验证是否加载：见下一节「两行补丁」。

----

第二步：两行补丁（第一个 mod）
------------------------------

在 ``user/mods/mymod/rules.txt`` 写入：

.. code-block:: text

   def peasant
   decay 20

重启游戏或重开地图。任意农民约 20 秒后消失——说明 mod 已生效。

零代码 mod：只改音效/文案时，复制 ``mods/soundpack/``，不动 ``rules.txt``；或在选项 → 音效包 勾选。

----

第三步：rules.txt 怎么读
------------------------

一条定义 = ``def 名字`` + 若干行属性 + （可选）``class``：

.. code-block:: text

   def my_soldier
   class soldier
   is_a footman
   hp 120
   mdg 8
   cost 50 0
   time_cost 12

.. list-table::
   :header-rows: 1

   * - 概念
     - 含义
   * - ``def``
     - 开始一条定义
   * - ``class``
     - 类型：``soldier``、``building``、``skill``…
   * - ``is_a``
     - 继承另一条定义的全部属性，再覆盖
   * - ``clear`` （文件首行）
     - 整文件替换默认规则，而非补丁

阵营：``def orc_faction`` + ``class faction`` （名称须唯一）。

----

第四步：让游戏「读对人话」
--------------------------

内部 id（``my_soldier``）不要指望玩家听见。在 mod 的 ``ui/`` 里：

.. code-block:: text

   ; style.txt
   def my_soldier
   title 7801

   ; ui-zh/tts.txt
   7801 重装步兵

命令菜单、选中单位时会朗读 7801 对应文本。  
多语言目录 ``ui-fr/``、``ui-de/`` 等 → `模组多语言 <mod-i18n.htm>`_。

----

第五步：怎么测
--------------

1. 主菜单 → 单人 → 选小图 → 对战电脑
2. 训练/修改后的单位，看数值与名称是否符合预期
3. 单人且只有你一名人类玩家时：Ctrl+Shift+F2 开全图（调试用）
4. 报错时看 ``user/tmp/client.log``

想理解玩家侧背包、默认行为字段含义，可对照：

- `背包与装备栏 <../player/inventory.htm>`_
- `单位默认行为 <../player/unit-default-behavior.htm>`_

----

本指南之后读什么？
------------------

.. list-table::
   :header-rows: 1

   * - 你想做
     - 下一步
   * - 完整单位、技能、阵营
     - `Mod 制作进阶 <advanced.htm>`_ → `Mod 手册 <modding.htm>`_
   * - 一张可玩的地图
     - `地图入门 <map-guide.htm>`_
   * - 多章战役
     - `战役指南 <campaign-guide.htm>`_
   * - 只查版本更新
     - `版本说明 <../relnotes.htm>`_

返回 `模组文档索引 <index.htm>`_ · 玩家向 `玩家入门 <../player/getting-started.htm>`_
