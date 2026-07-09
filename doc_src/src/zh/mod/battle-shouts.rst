战斗喊杀音效（分层播放）
==========================

接战时的喊杀声分为**战场背景**、**单位音色**、**事件高光**三层，按交战规模与冷却错开播放。本仓库为**原版单体作战**（无军团编队玩法）。

.. contents::

概述
----

| 层级 | 作用 | 典型条数 |
|------|------|----------|
| 战场背景（``shout_bg``） | 这片格子在打仗的氛围 | 1–2 |
| 单位音色（``shout_unit``） | 人数占优一方的兵种喊杀 | 1–2 |
| 事件高光（``shout_event``） | 首次接战、冲锋、暴击 | 1–2 |

实现模块：

- ``soundrts/clientgameentity/battle_shout_audio.py``
- ``soundrts/clientgameentity/combat.py``
- ``soundrts/clientgameentity/formation_sound_queue.py``

测试：``python -m pytest soundrts/tests/test_battle_shout_audio.py -q``


触发条件
--------

- 交战格内**任一方**战斗单位（``menace > 0``）≥ **5** 时，可能播放背景层与单位层。
- 单位层只播**同格人数更多一方**的 ``shouts``，避免小规模混战叠音。

冷却（硬编码）：

- 全局 10 秒；同格 6 秒（背景 + 单位）
- 冲锋/暴击事件喊杀：同格 4 秒短冷却


style.txt 配置
--------------

在 ``ui/style.txt`` 写 ``shouts``（一个或多个音效 ID）::

  def walking_unit
  is_a unit
  move 1053 1054
  shouts 1854

**推荐**写在 ``def walking_unit`` 上，使 ``footman``、``archer`` 等继承。内置 ``res/ui/style.txt`` 已包含此行。

单独兵种也可覆盖::

  def knight
  shouts 1854


播放行为
--------

- **背景层**：``walking_unit`` 的 ``shouts``，音量略低。
- **单位层**：优势方单位的 ``shouts``。
- **事件层**：该格超过 15 秒未喊杀后再接战 +2 条；冲锋命中、暴击各 +1 条。

与 ``mdg_hit`` / ``launch_rdg`` 等命中音效独立播放。


玩家与模组
----------

- 玩家：仅能通过 ``audio.main_volume`` 或音效包替换素材。
- 模组：改 ``shouts`` 音效 ID 即可换音色；密度与三层开关尚未暴露为配置项。

详见 :doc:`modding` 中 Combat sound system 章节。
