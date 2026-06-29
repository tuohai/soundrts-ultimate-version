帝国时代式合作战役
==================



完整指南（1.4.3.9+）： `../player/战役与合作战役改进说明.md <../player/战役与合作战役改进说明.htm>`_ — 任务浏览器、五档难度、AI 队友、确定性、地图作者要点。

English: `../../en/mod/coop-campaign.md <../../en/mod/coop-campaign.htm>`_

引擎以帝国时代 II/III 决定版的方式运行战役合作：多名玩家进入同一剧情任务，各自指挥独立玩家位（基地/部队），同队共享目标与过场，敌人强度随难度与人类玩家数缩放。空位由同盟 AI 队友接管，单人也可开合作关。

玩家流程
--------


1. 服务器大厅 → 合作战役 → 选战役 → 选章节 → 选难度 → 选速度（无条约步骤）。
2. 其他玩家加入；房主开始。
3. 全员播放关卡 intro，随后由地图触发器判定胜负（非「杀光所有敌人」）。
4. 通关后推进房主的合作进度书签（``coop_chapter``，与单人 ``chapter`` 独立）。

战役作者：``campaign.txt``
--------------------------


与帝国时代战役表一样，在 :strong:```campaign.txt`` 中声明合作（与 ``title`` / ``synopsis`` 同级）。不要再维护平行的 ``N.coop.txt``；单人与合作加载同一份 ``N.txt``。

.. code-block:: text

   title 7747
   synopsis 7751
   coop_campaign 1
   coop_intro 0
   coop_missions 1-29



.. list-table::
   :header-rows: 1

   * - 字段
     - 含义
   * - ``coop_campaign``
     - ``1`` — 出现在服务器「合作战役」菜单
   * - ``coop_intro``
     - 合作流程中的过场章节号（可多个或 `1-29` 范围）
   * - ``coop_missions``
     - 可合作的任务章节号



解析与菜单逻辑见 `soundrts/campaign.py <../../../soundrts/campaign.py>`_ （``supports_coop``、``coop_menu_chapters``、``coop_mission_chapters``）。合作对局通过 ``ensure_chapter_map`` 加载章节地图。

引擎不写死任何战役名；Mod 作者只需在自己的战役目录填写上述字段。

地图作者：``N.txt`` 合作槽位
----------------------------


任务章节即战役地图。要支持合作，在同一张 ``N.txt`` 中声明多个人类玩家位（同队）：

.. code-block:: text

   nb_players_min 1
   nb_players_max 2
   player_start 1 a1 raynor footman footman
   player_start 2 h8 raynor2 footman archer
   computer_only e5 ...


要点：

- ``nb_players_max`` = 合作槽位数；每位人类（及 AI 队友）从地图出生点获得独立基地/部队。
- ``nb_players_min 1`` 允许单人开房；空位由 `Game._fill_coop_ai_partners <../../../soundrts/serverroom.py>`_ 用同盟 AI 补满。
- 人类 + AI 队友开局 alliance 1；``computer_only`` 敌人归入 `"ai"` 同盟。
- 触发器中的 ``player1``、``player2`` 按人类加入顺序映射；AI 队友位通常不参与剧情触发器。

单人战役（``MissionGame``）仍只注册 1 名玩家，仅占用第一个出生点。

难度与人数缩放
--------------


敌方生命与输出伤害按难度与人类数确定性缩放（整数运算）。见 ``soundrts/coop_difficulty.py``。

确定性说明
----------


- 难度系数在服务器算定并广播，旁观/回放一致。
- 合作对局不挂载本地 `world.campaign`，跨章 ``campaign_flag`` 为确定性 no-op；关内 ``set_map_flag`` / ``map_flag`` 正常。

维护工具（可选）
----------------


`tools/generate_raynor_coop_maps.py <../../../tools/generate_raynor_coop_maps.py>`_ 仅用于 The Legend of Raynor：把合作布局（加宽、对称第二玩家等）写入 ``N.txt``。其它战役请直接在 ``campaign.txt`` + ``N.txt`` 中手工或通过 Mod 工具维护。

测试
---


.. code-block:: bash

   python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
   python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
   python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
