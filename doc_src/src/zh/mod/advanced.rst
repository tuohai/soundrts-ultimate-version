Mod 制作进阶指南
================


在单位补丁之上，做完整 mod：技能、阵营、元进度、AI。地图与战役有专门指南。前置：`Mod 入门 <getting-started.htm>`_。
.. contents::

----

一、Mod 组成一览
----------------

一个可发布的 mod 文件夹通常包含：

.. code-block:: text

   mymod/
     rules.txt       ; 规则（核心）
     style.txt       ; 可选，ui/style 补丁
     ai.txt          ; 可选，电脑策略
     ui/
       tts.txt
       bindings.txt  ; 可选，热键
     ui-zh/          ; 可选，中文

加载顺序：``SoundRTS.ini`` 里 ``mods = A,B,mymod`` — 越靠后越优先。

参考完整示例：``mods/orc/``、``mods/starcraft/``、``mods/crazyMod9beta10/`` （先复制到 ``user/mods/`` 再改）。

----

二、规则进阶：单位与战斗
------------------------

继承链：用 ``is_a`` 叠层，避免复制整段属性。

.. code-block:: text

   def elite_footman
   is_a footman
   hp 80
   mdg 7
   cost 60 0

阵营与生产：在 ``def xxx_faction`` 里声明 ``can_train`` / ``can_build`` 列表；建筑用 ``can_train peasant footman`` 等形式。

战斗相关（节选）— 完整见 `Mod 制作手册 <modding.htm>`_：

.. list-table::
   :header-rows: 1

   * - 字段
     - 用途
   * - ``mdg`` / ``rdg`` / ``mdf`` / ``rdf``
     - 近战/远程伤害与防御
   * - ``mdg_range`` / ``rdg_range``
     - 攻击距离
   * - ``speed`` / ``sight_range``
     - 移动与视野
   * - ``can_use_skill``
     - 挂载主动技能

技能：不要只在单位上堆数值——见 `技能 / 治疗 / 效果 <skills-and-effects.htm>`_ （``class skill``、``effect``、heal/harm、战场 effect）。

连发与 burst — 玩家向见 `连发攻击 <../player/burst-attacks.htm>`_；语法见 skills 文档与 `Mod 制作手册 <modding.htm>`_ 战斗节。

----

三、界面、热键与多语言
----------------------

- 文案：``style.txt`` 的 ``title`` / ``intro`` + 各语言 ``tts.txt``
- 热键：mod 可带 ``ui/bindings.txt`` 覆盖按键；选项内编辑器 → `热键映射编辑器 <hotkey-mapping-editor.htm>`_
- 文件结构（分层热键）：`分层热键 <../player/layered-hotkeys.htm>`_
- 多语言目录：`模组多语言 <mod-i18n.htm>`_

----

四、电脑 AI（ai.txt）
---------------------

让电脑会造你的新单位、走新科技树。  
教程 → `AI 制作 <aimaking.htm>`_；简单 mod 可先沿用默认 AI，只改 ``rules.txt``。

----

五、元进度：成就、评分、卡牌
----------------------------

对战电脑（非战役）可挂钩：

.. list-table::
   :header-rows: 1

   * - 系统
     - 文档
     - 玩家侧
   * - ``achievements.txt`` 等
     - `成就系统 <achievement-system.htm>`_
     - `成就 <../player/achievements.htm>`_
   * - 结算维度
     - `结算评分 <score-grading-system.htm>`_
     - `评分与等级 <../player/score-and-grades.htm>`_
   * - 战前卡牌
     - `延迟卡牌 <delayed-card-loadout.htm>`_
     - `战前卡牌 <../player/loadout-cards.htm>`_

----

六、地图与战役（另册）
----------------------

本指南不展开触发器语法，请按任务选读：

.. list-table::
   :header-rows: 1

   * - 任务
     - 指南
   * - 第一张多人图、触发器、子格地形
     - `地图入门与进阶 <map-guide.htm>`_ → `地图手册 <mapmaking.htm>`_
   * - 多章、物品、NPC、合作、跨章英雄
     - `战役指南 <campaign-guide.htm>`_ （含 ``campaign/`` 专题）
   * - 随机地图参数
     - `随机地图手册 <randommap.htm>`_
   * - HoMM / Civ5 式 POI（玩家向）
     - `英雄无敌 / 文明5 式地图 <../player/homm-civ5-play.htm>`_

----

七、发布与协作建议
------------------

1. 小步提交：一个 ``rules.txt`` 改动 + 一张测试图
2. 命名：``def`` 名唯一；``title`` 用 TTS ID，避免硬编码中文进 rules
3. 文档：在 mod 的 ``readme.txt`` 写激活方式与 ``mods = ...`` 顺序
4. 版本：大改规则时提醒玩家删旧存档或开新图测试

----

查阅索引
--------

- `Mod 制作手册 <modding.htm>`_ — 关键字权威
- `版本说明 <../relnotes.htm>`_ — 新字段从哪版开始
- `模组文档索引 <index.htm>`_

返回 `Mod 入门 <getting-started.htm>`_
