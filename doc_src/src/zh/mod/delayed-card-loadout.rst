延迟卡牌（Delayed Loadout Cards）
=================================



玩家向说明：`../player/loadout-cards.md <../player/loadout-cards.htm>`_

战前携带卡可在 :strong:```delay`` / ``delay_minutes`` 之后再生效，用于「开局预约、稍后增援/发科技」类效果。实现见 ``soundrts/cards.py``、``soundrts/card_loadout.py``。

英文版：`../../en/mod/delayed-card-loadout.htm <../../en/mod/delayed-card-loadout.htm>`_

相关：`achievement-system <achievement-system.htm>`_ （卡牌与战前携带总览）、`score-grading-system.htm <score-grading-system.htm>`_ （结算评分）。


----


1. 适用场景
-----------


- 仅 单机自定义图 / 随机图 + 邀请电脑（TrainingGame），与即时卡牌相同；战役、联机不适用。
- 选卡、扣充能在进局时完成；效果在游戏时间到达延迟后触发。
- 延迟卡与即时卡一样占用战前栏位、消耗 1 点充能；``min_rank``、``faction`` 规则不变。


----


2. cards.txt 语法
-----------------


在现有 ``def`` 块中增加：


.. list-table::
   :header-rows: 1

   * - 指令
     - 说明
   * - ``delay \<seconds\>``
     - 效果延迟 秒（游戏内时间，非真实时间）
   * - ``delay_minutes \<n\>``
     - 等价于 `delay (n×60)`
   * - ``tech \<upgrade_id\> [...]``
     - 到达延迟后授予科技（等同建筑研究完成）



可与 ``spawn``、``resource`` 组合在同一张卡上；共用同一延迟，到点一次性执行全部效果。

.. code-block:: text

   def card_reinforcements_delayed
   title 5333
   tags infantry
   spawn footman 3
   delay_minutes 10
   grant_charges 1
   min_rank rank_sergeant
   
   def card_delayed_melee_weapon
   title 5334
   tech melee_weapon
   delay_minutes 8
   grant_charges 1
   min_rank rank_lieutenant


- ``delay`` 省略或为 0：开局立即生效（原版行为）。
- 多条 ``spawn`` / 多条 ``tech``：到点后按定义顺序全部应用。
- ``tech`` 需为有效升级 ID；已研究过的科技会跳过。


----


3. 运行时行为
-------------


.. code-block:: text

   战前选卡 → 进局 populate_map 后 apply_loadout_to_player
     → delay > 0：world.schedule_after(delay_ms, 回调)
     → delay = 0：立即 _apply_card_effects


到点回调（``\_schedule_card_effects``）：

1. 按 `player.id` 找回本地人类玩家（玩家已退出则放弃并写 warning）
2. 依次应用：资源 → 生成单位（起始格附近，不占人口）→ 科技
3. 对本地玩家推送 ``LOADOUT_CARD_TRIGGERED`` 语音（「携带卡牌效果生效：…」）

游戏速度：``delay_ms = delay_seconds × 1000 × world.timer_coefficient`` （加速/减速局内一致）。

充能：调度成功即视为「已使用」，进局时扣 1 点充能，与是否已到延迟无关。


----


4. 语音与 UI
------------



.. list-table::
   :header-rows: 1

   * - TTS ID
     - 中文（ui-zh）
     - 用途
   * - 5387
     - 效果将在
     - 进局应用延迟卡 / 军械库说明
   * - 5392
     - 后生效
     - 接在时长之后
   * - 5388
     - 携带卡牌效果生效
     - 延迟到点触发
   * - 5389
     - 在起始位置附近生成
     - 军械库：延迟生成单位
   * - 5390
     - 额外获得
     - 军械库：延迟资源
   * - 5393
     - 获得科技
     - 军械库：科技效果



进局播报示例（``loadout_applied_msgs``）：  
「已应用延迟步兵增援卡，效果将在 10 分钟后生效。」

军械库说明（``card_armory_explanation``）：在普通卡说明前加「效果将在 N 分钟/秒后生效」，资源/生成项使用延迟专用措辞。

时长播报：整分钟用「N 分钟」，否则「N 秒」。


----


5. 基础版示例卡与成就
---------------------



.. list-table::
   :header-rows: 1

   * - 卡牌 ID
     - 效果
     - 成就来源
   * - ``card_reinforcements_delayed``
     - 10 分钟后 3 步兵
     - ``reinforcement_contract`` （5309 援军合约）
   * - ``card_delayed_melee_weapon``
     - 8 分钟后 ``melee_weapon``
     - ``defeat_expert`` （击败专家电脑）



成就仍走 ``achievements.txt`` 的 ``reward card \<id\>``；解锁后充能进入军械库，与即时卡相同。


----


6. 模组作者注意
---------------


- 延迟卡至少需一种效果（``resource`` / ``spawn`` / ``tech``），否则调度失败。
- 需要 `world.schedule_after`（正常对局均有）；无 world 或玩家无 ``id`` 时无法调度。
- 极长延迟在加速局仍按 ``timer_coefficient`` 缩短；设计关卡节奏时请考虑游戏速度选项。
- 与 ``achievements_enabled 0`` 互斥：关闭成就系统时不加载 ``cards.txt``、不显示战前选卡。


----


7. 测试
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_cards.py -k delay -v
   python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
