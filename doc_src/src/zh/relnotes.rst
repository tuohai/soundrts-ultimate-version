版本说明
========

.. contents::


1.4.4.8
-------

面向地图作者与地图编辑器的子格地形：

**大格子内部的子格地形**

- 地形命令现在可以用 ``square/x,y`` 语法指定一个大格子内部的子区域，例如 ``high_grounds a1/1,1 a1/1,2``。
- ``subcell_precision N`` 控制子格划分；默认 ``3``，允许范围 ``2`` 到 ``20``。
- 支持的命令：``terrain``、``high_grounds``、``speed``、``cover``、``water``、``ground`` 和 ``no_air``。
- 战斗、移动、地形速度、掩护与高地判定可按单位实际所在子格计算。

**缩放浏览与编辑器行为**

- 缩放模式浏览地图时会播报当前子格地形，包括只覆盖局部的高地。
- 实验性地图编辑器中，开启缩放模式时按 Enter 会把选中的地形应用到当前子格。
- 保存地图时，子格覆盖会写回为 ``square/x,y`` 语法。

发行说明：``docs/zh/player/release-1.4.4.8.md``

1.4.4.7
-------

英雄经验门槛公式（``xp_threshold_growth``）与升级后经验清零（``level_up_reset_xp``）：

**英雄经验门槛公式（``xp_threshold_growth``）**

- 英雄 def 可写 ``max_level`` + ``xp_threshold_growth``，加载 ``rules.txt`` 时自动生成 ``xp_thresholds``，无需手写几十上百个累计经验数。
- 曲线类型：``linear``、``quadratic``、``polynomial``、``geometric``（见 ``modding.rst`` 英雄章节）。
- 与手写 ``xp_thresholds`` 兼容：两者同时存在时以手写列表为准；子 def 可 ``is_a`` 继承 ``xp_threshold_growth`` 并只改 ``max_level``。
- 实现：``soundrts/xp_threshold_growth.py``、``soundrts/definitions.py``；测试：``test_xp_threshold_growth.py``。

**升级后经验清零（``level_up_reset_xp``）**

- 英雄 def 可选 ``level_up_reset_xp 1``：战斗升级后当前经验归零；默认 ``0`` 保留累计经验。
- 开启时 ``xp_thresholds`` 宜写每级所需经验，而非累计总值。
- 实现：``soundrts/worldunit/world_status_update.py``；测试：``test_level_up_combat_stats.py``。

发行说明：``docs/zh/player/release-1.4.4.7.md``

1.4.4.6
-------

模组音效命名统一、统一技能系统、通用技能效果、技能目标类型与 -tag 排除、升级属性成长、升级解锁技能、战役跨章携带、背包物品使用音效、前摇自定义音效、背包/装备栏热键、英雄开局等级与 0 级经验显示：

**攻击音效字段改名**

- ``ui/style.txt`` 中攻击音效推荐使用 ``mdg`` / ``rdg`` 命名：
  ``launch_mdg`` / ``launch_rdg``、``mdg_hit`` / ``rdg_hit``、``mdg_hit_vs`` / ``rdg_hit_vs``、
  ``mdg_missed`` / ``rdg_missed``、``mdg_dodge`` / ``rdg_dodge``。
- 冲锋音效使用 ``launch_charge_mdg`` / ``launch_charge_rdg``、
  ``charge_mdg_hit`` / ``charge_rdg_hit``。
- 内置 ``style.txt`` 已迁移；旧 ``matk`` / ``ratk`` 字段仍作为兼容 fallback。

**前摇自定义音效**

- 技能 ``ready <秒>`` 可在技能 style 上配置 ``ready <sound>``；手动释放和自动触发技能都会在前摇开始时播放。
- 普通攻击 ``mdg_ready`` / ``rdg_ready`` 前摇开始时会播放单位 style 中同名音效。

**统一技能系统**

- 同一 ``class skill`` 可同时配置 **手动释放** 与 **自动触发**，不再拆成两套列表。
- 技能字段：``auto_trigger 1``、``manual_use 1``（默认 1）、``trigger_timing``。
- ``trigger_timing`` 取值：``on_hit``（命中后）、``on_attack``（出手附加，普攻继续）、
  ``on_attack_replace``（替代本次普攻）、``on_damaged``（受击时）。
- 学会的技能统一进入 ``can_use_skill``；菜单只显示 ``manual_use 1`` 的技能。
- **旧写法仍兼容**：``active_trigger_skills``、``attack_trigger_skills``、
  ``attack_replace_skills``、``passive_trigger_skills`` 继续有效，与新字段并存时以
  ``can_use_skill`` + 技能上的 ``auto_trigger`` / ``trigger_timing`` 为准。

**通用技能效果**

- 固定伤害 ``harm_target N`` / ``harm_area N R``；战斗伤害 ``harm_target mdg`` / ``harm_area mdg R``（完整战斗管线）。
- 连击 ``burst mdg N (interval X)`` 或 ``(delays …)``；击退 ``push``；``buffs`` / ``debuffs``；部署 ``deploy``；召唤 ``summon``。
- 旧效果 ``teleportation`` / ``recall`` / ``conversion`` / ``raise_dead`` / ``resurrection`` 仍可用。
- 触发率与条件、攻击发起 buff/debuff 列表仍兼容；详见 ``GENERIC_SKILL_SYSTEM.md``。

**目标类型过滤与排除语法（``-tag``）**

- ``class skill`` 支持 ``harm_target_type``（``burst`` / ``harm_target`` / ``harm_area`` / ``push``）；未配置时默认仅对敌人生效。
- 标签前加 ``-`` 表示排除，如 ``-building``；适用于 ``harm_target_type``、``heal_target_type``、``mdg_targets`` / ``rdg_targets``、buff/debuff ``target_type``。
- 外交标签支持 ``-enemy`` / ``-allied`` / ``-neutral``。
- 示例：``harm_target_type enemy unit -building``；``heal_target_type unit -undead``；``mdg_targets -building``。

**升级属性成长（``*_per_level``）**

- 单位可在 ``rules.txt`` 为绝大多数战斗、生命、法力、治疗/伤害、回复类属性配置 ``<属性>_per_level``，每次升级累加一档。
- 示例：``hp_max_per_level``、``mdg_per_level``、``charge_mdg_per_level``、``mdg_crit_rate_per_level``、``mana_max_per_level``、``heal_cd_per_level`` 等。
- 战役跨章恢复英雄时按存档等级补回累计成长。

**英雄开局等级与状态显示**

- ``level`` / ``xp``：在 ``rules.txt`` 英雄 def 上配置开局等级与累计经验（需 ``xp_thresholds``）；``level > 1`` 时生成单位逐级应用 ``*_per_level``。
- ``level 0``：从 0 级开局；Tab 状态显示「等级 0，经验 0/首个 xp_thresholds」。
- 定义了 ``xp_thresholds`` 的英雄在 Tab 状态中始终播报等级（含 1 级与 0 级）。

**升级回满（``level_up_heal_full``）**

- 英雄 def 可选 ``level_up_heal_full 1``：每次升级后生命与法力回满；默认 ``0`` 为仅加上限增量。

**升级解锁技能与技能书**

- 单位 ``level_skills <等级> <技能> …``：升到对应等级自动加入 ``can_use_skill``（带语音提示）。
- 单位 ``learn_level_skills``：技能书学习的额外等级门槛（与物品 ``learn_level`` 取较高）。
- 技能书：背包 Enter 使用（``use_item``）永久学会；有 ``learn_level`` 时拾取不自动学会。
- 同一技能勿在 ``level_skills`` 与技能书上重复配置。

**战役跨章英雄携带**

- 英雄 def：``campaign_carryover 1``（可选 ``campaign_carryover_stats``、``campaign_carryover_inventory``、``campaign_carryover_id``）。
- **通关**写入 ``user/campaigns.ini``（``hero_<id>_xp`` / ``_level`` / ``_inventory``）；下一关恢复；**合作战役**不持久化。
- ``campaign.txt`` 可选 ``hero_min_level 13:2 …`` 章节最低等级。

**背包物品使用音效（style.txt）**

- 与拾取/丢弃相同的三级查找：物品 ``use`` / ``on_use`` → 单位 ``use_<物品type>`` → 全局 ``item_used``（``def thing``）。
- 服务端确认使用成功后才播放；不再在按 Enter 时乐观朗读「已使用」。
- 技能书成功：使用音效 + 「技能名，已学会」（``skill_learned``）；普通消耗品：「物品名，已使用」。
- 成功使用后消耗品从背包移除；技能书 ``unequip`` 不再撤销已永久学会的技能。

**背包与装备栏热键**

- **Shift+V** 在背包与装备栏之间循环切换（经典与分层方案）；**Ctrl+V** 已移除；分层 **F3** 仍可用。

文档：``doc_src/src/zh/modding.rst``、``doc_src/src/en/modding.rst``、``GENERIC_SKILL_SYSTEM.md``、``docs/zh/developer/战役跨章英雄携带说明.md``
测试：``test_level_skills.py``、``test_level_up_combat_stats.py``、``test_campaign_hero.py``、``test_wuxia_skills.py``、``test_worldskill_deploy.py``、``test_target_type_exclusions.py``、``test_hit_vs_buff_sounds.py``、``test_damage_seq_burst.py``、
``test_changelog_138x.py``、``test_skill_trigger_sounds.py``、``test_inventory_backpack.py``

发行说明：``docs/zh/player/release-1.4.4.6.md``


1.4.4.5
-------

**随机地图：英雄无敌 / 文明 5 风格**

- 胜利模式：征服 / 经济 / 探索 / 生存（TTS 5425–5430）
- 地图兴趣点：**古代遗迹**、**可占领兵营**、中央野怪、可选宝箱
- 分享码第 11 段胜利字段；``res/rules.txt`` 新增 ``ancient_ruin``、``captured_barracks``
- 文档：``docs/zh/player/英雄无敌与文明5玩法说明.md``；``randommap.rst``
- 测试：``test_randommap.py``

**默认占领命令（can_capture）**

- 敌方 ``capture_hp_threshold`` 为 **100** 时：`can_capture 1``（默认）单位默认 **占领**；``can_capture 0`` 默认攻击/移动
- **低于 100** 的阈值仍须战斗打到夺取线，不走默认占领
- 文档：``doc_src/src/zh/modding.rst``；玩家 ``docs/zh/player/单位默认模式与自动状态配置说明.md`` §5
- 测试：``test_capture_default_order.py``

**AI 跨水域作战**

- 对岸矿床两栖采集、运输船/空中运输登陆、船坞与战舰维护
- ``worldplayercomputer_water.py``、``_try_transport_assaults`` / ``_try_amphibious_landings``
- 测试：``test_worldplayercomputer_water.py``、``test_ai_naval_m3.py`` 等

**训练：人口不足时按剩余人口训满**

- 批量训练时剩余人口不足：按可用人口 **尽可能多训**（例：训 5 步兵只剩 3 人口 → 训 3）；人口为 0 仍失败
- ``worldorders/production.py``（``TrainOrder._max_train_count_for_population``）
- 测试：``test_train_population.py``

**修复：Ctrl+Shift+F4 切换视角与结算**

- 局初固定计分真人；切视角不再把 AI 胜负/奖章/卡牌/成就算到玩家头上
- 首次切视角之后新倒下的计分对手（如 NPC 打掉所观察 AI）不计入胜利与击败分；切视角前已击败的对手仍算
- ``scoring_player`` / ``scoring_victory``；首次切换时记录已击败计分对手基线
- 测试：``test_change_player_scoring.py``

**按键映射编辑器**

- 主菜单 **选项 → 按键映射**（与热键方案同级）；``hotkey_remapping_menu.py``、``hotkey_editor.py``、``hotkey_catalogs.py``
- 分层 8 层 + 经典约 179 项；按 mod 存 ``user/hotkey_overrides/{mod_key}.json``；下次开局生效
- 搜索、高级变体、别名键（``binding_id@默认键``）、剪贴板导入导出
- Catalog TTS 5500–5684；classic 高级变体全覆盖；编组语义修正
- 标签：Alt+Space → **第一人称模式**；Ctrl+F2 → **画面开关**
- 文档：``docs/zh/developer/hotkey-mapping-editor.md``、``docs/zh/player/分层热键方案说明.md``
- 测试：``test_hotkey_editor*.py``、``test_hotkey_catalog_tts.py``、``test_hotkey_editor_mod_isolation.py``

发行说明：``docs/zh/player/release-1.4.4.5.md``

1.4.4.4
-------

延迟卡牌、结算评分与评级、按阵营成就与元进度、CrazyMod 内容与体验修复：

**延迟战前卡牌**

- ``cards.txt`` 新增 ``delay <秒>``、``delay_minutes <分>``：进局预约效果，到点再生效（``world.schedule_after``，受 ``timer_coefficient`` 影响）
- 新增 ``tech <upgrade_id>``：卡牌可授予科技；可与 ``spawn`` / ``resource`` 组合，共用同一延迟
- 进局播报「效果将在 N 分钟/秒后生效」；到点播报「携带卡牌效果生效」（TTS 5387–5393）
- 基础版示例：``card_reinforcements_delayed``（10 分钟后 3 步兵）、``card_delayed_melee_weapon``（8 分钟后近战武器科技）
- 成就：``reinforcement_contract``（5309 援军合约）→ 延迟增援卡；``defeat_expert`` → 延迟近战武器卡
- 文档：``docs/zh/developer/delayed-card-loadout.md`` （玩家：``docs/zh/player/loadout-cards.md``）
- 测试：``test_cards.py``、``test_card_loadout.py`` （``-k delay`` / ``-k delayed``）

**结算评分与字母评级**

- 多维度评分文档：``docs/zh/developer/score-grading-system.md`` （玩家：``docs/zh/player/score-and-grades.md``）
- 基础七项满分 800；击败电脑奖励另计，**不计入**百分比分母
- **败局字母评级最高 D**（``grade_total`` 封顶 479，无法评 C 及以上）
- 胜利且资源利用率 < 50% 时，效率维度改为 **节约效率**（TTS 5251），按低消耗计分
- 无地图矿储量时，采集分按参照采集量（1000 单位 = 100 分）比例计算；战役无矿图仍按胜/败给满/零
- 未生产单位时存活分为 0；建筑损失/拆迁各 **5 分/座**（原 10）
- 移除 ``worldplayerbase/resources.py`` 中未使用的旧版结算分接口
- 测试：``test_score_breakdown.py``

**成就与军衔数据**

- 少尉（``rank_lieutenant``）门槛调整为 **200** 奖章、1 个战前栏位
- ``defeat_beginner`` 重复完成奖章 **8**；``perfect_survival`` 条件为存活 ≥90 且建筑保全 ≥90

**修复**

- 工人 ``can_gather all`` 在矿床与建筑均为 ``all`` 时，属性界面不再重复播报两个「全部」
- 测试：切换 crazyMod 后自动恢复 ``res.mods``，避免污染基础 ``titles.txt`` 测试
- 随机阵营开局与战前选卡体验；狩猎等 NPC 击败播报受 ``broadcasts_defeat_and_quit`` 控制

**按阵营成就（方案 D）**

- ``achievements_per_faction 1``、``faction_progress.py``；战役不计成就与结算分数

**跨阵营元进度**

- ``_meta.json``、``scope meta``、``meta_progress.py``；主菜单「跨阵营进度」

**CrazyMod 9**

- 分阵营地图里程碑、四档元成就、``rules.txt`` / ``ai.txt`` 平衡微调

**文档（玩家 / 开发者两套）**

- 索引：``docs/README.md``、``docs/zh/player/README.md``、``docs/zh/developer/README.md``

**战役跨章英雄携带（规则驱动）**

- ``rules.txt``：``campaign_carryover 1``（可选 ``campaign_carryover_id``、``campaign_carryover_stats``、``campaign_carryover_inventory``）
- ``campaign.txt``：``hero_min_level 13:2 …`` 指定进入某章后的最低等级
- **通关**写入 ``user/campaigns.ini``（``hero_<id>_xp`` / ``_level`` / ``_inventory``）；下一关恢复；**合作战役**不持久化
- 与 ``campaign_flag`` / ``add_inventory_item`` 独立；详见 ``modding.rst``、``mapmaking.rst``、``docs/zh/developer/战役跨章英雄携带说明.md``
- 实现：``soundrts/campaign_hero.py``；测试：``test_campaign_hero.py``

**修复与语音**

- 通道图 ``has_entered`` 使用 1 基坐标（如 ``8,2``）时不再与 0 基 grid 键冲突，遗迹触发正常
- 分享码/种子等文本输入框 **Ctrl+V** 粘贴（pygame-ce 剪贴板 API）
- HoMM/Civ5 与战役支线 TTS 从 5107–5123 迁至 **5425–5441**，避免与既有条目冲突

发行说明：``docs/zh/player/release-1.4.4.4.md``

1.4.4.3
-------

成就与军械库（第二、三期：奖章、军衔、卡牌、战前携带）：

- 主菜单新增 **成就**：成就列表 + **军械库**（当前军衔、荣誉、奖章总数、卡牌充能）
- 单机对战电脑或随机地图结算后，按 ``achievements.txt`` 判定解锁；语音播报成就、奖章、卡牌、军衔晋升、战前携带栏位增加
- 进度按 **当前模组** 分别存档：``user/achievements/<模组>.json``
- **战前携带卡**：主菜单 → 单人游戏 → 在地图上开始 → 点「开始」后，按军衔选择最多 N 张卡（少尉 1 栏、上尉 2 栏…，见 ``titles.txt``）；**仅** 自定义图 / 随机图 + 邀请电脑（**不含** 战役、联机）
- 进局后立即生效：额外资源或在起始位置附近生成单位；每张使用的卡消耗 1 点充能
- **卡牌生成的单位不占人口**；随机阵营会按阵营等价表生成对应单位
- **修复**：此前战前携带的卡在进局时未生效（界面创建前无法识别本地玩家）；已改为开局加载地图后、进入界面前正确应用
- 军械库浏览卡牌时会朗读效果说明（开局加成、生成单位、所需军衔等）
- **重复完成**：同一地图 / 难度再次达成已解锁成就时，若配置了 ``repeat_medal <n>``，仅再获得少量奖章（不再发卡、荣誉或「成就解锁」）；奖章仍计入军衔
- **模组可关闭整套系统**：``rules.txt`` 中 ``achievements_enabled 0`` —— 隐藏主菜单入口，跳过结算与战前选卡
- **电脑 ``ai.txt`` 的 ``starting_units`` 加成单位不占人口**（地图开局单位仍占人口）；``starting_population`` 仍为额外人口上限
- 数据文件：``res/achievements.txt``、``res/cards.txt``、``res/titles.txt``；语音 ID 5244–5367 等
- 文档：``docs/zh/achievement-system.md`` （英文：``docs/en/achievement-system.md``）
- 测试：``test_achievements.py``、``test_cards.py``、``test_titles.py``、``test_card_loadout.py``

1.4.4.2
-------

AI 单位克制（``ai.txt`` 中的 ``counter_skill``）：

- 电脑单位选目标与派兵时会参考 ``mdg_vs`` / ``rdg_vs`` 及 ``is_a`` 继承
- 新增脚本命令 ``counter_skill <0-100>``：``0`` 忽略克制（只看 ``menace``），``100`` 始终选最佳克制；中间值为两者加权
- 原版 ``res/ai.txt`` 五档：初级 ``25``、中级 ``50``、高级 ``75``、专家 ``90``、噩梦 ``100``；mod 脚本未写则默认 ``100``
- 新增 ``starting_resources`` / ``starting_units``：邀请的电脑在地图正常开局之上额外获得资源与单位（语法同地图；仅开局生效，不参与脚本循环）
- 新增 ``starting_population``（``ai.txt`` 与地图）：在农舍等单位提供的人口上限之上额外增加人口上限（普通整数，非 ×1000）；仍受 ``global_population_limit`` 限制
- 原版额外开局：中级 +50/+50；高级 +100/+100 与 2 步兵 2 弓；专家 +200/+200 与 5/4/2；噩梦 +400/+400 与 8/6/4
- 文档：``doc_src/src/en/aimaking.rst``、``doc_src/src/zh/aimaking.rst``
- 测试：``test_ai_counter_targeting.py``、``test_ai_loader_and_menu.py``、``test_ai_start_settings.py``

1.4.3.9
-------

分层界面热键（全局层 + 界面层）：

- 原单一 ``bindings.txt`` 拆分为 ``global_bindings.txt`` 与 7 个界面文件（单位/建筑/命令/技能/帮助/地图/外交）；加载顺序：全局 → 当前界面 → ``cfg/bindings.txt`` → Mod 追加
- F 键切换：F1 单位↔建筑、F2 命令↔技能、F3 背包↔装备栏、F4 帮助与查询、F12 外交、ESC 进入/退出地图浏览；切换时播报界面名称
- 全局层保留资源（z/x/SHIFT z/c）、方向移动、方格跳转、确认命令、F9/F11 等；原 F1/F4 帮助、F12 直接外交改为进入对应界面后再操作
- 单位界面：农民 ``s``/``w``（原 ``d``/``e``）；士兵 1–7 映射 ``d/e``…``;``/``p``；建筑界面 16 槽 ``building1``–``building16``（``d/f/g/h/j/k/l/;`` + ``e/r/t/y/u/i/o/p``）
- 命令界面 30 槽序号热键；地图界面 ``f/g/m/p`` 在当前方格内循环矿点/草地/通道（不再跳格）；ESC 回地图播报方格概况并静默恢复上次地图焦点
- Mod ``style.txt`` 支持 ``keyboard worker``、``keyboard soldier1``–``7``、``keyboard building1``–``16``；``bindings.txt`` 正文改为兼容说明 stub
- 背包/装备/属性子界面退出时 ``restore_active_bindings`` 恢复分层绑定；编辑器热键不受影响
- **切回经典单文件热键**：配置文件 ``user/SoundRTS.ini`` 中 ``layered_hotkeys``：``0`` = 经典单文件（默认 ``1`` = 分层）；亦可在主菜单「选项 → 热键方案」切换（下次开始对局生效）。经典模式加载 ``legacy_bindings.txt``，无 F 键界面层，ESC 不进入地图浏览
- Mod 可分别定制：分层用 ``ui/*_bindings.txt`` 或追加 ``ui/bindings.txt``；经典用 ``ui/legacy_bindings.txt`` 或追加 ``ui/bindings.txt``
- 文档：``docs/zh/分层热键方案说明.md``、``docs/en/layered-hotkeys.md``
- 测试：``test_layered_bindings.py``、``test_map_browse_target_persist.py``

帝国时代决定版风格战役（单机 + 合作）：

- 单机：任务浏览器（``synopsis`` 简介、五档难度持久化、已完成/未解锁、重试本关）；敌方 hp/伤害按难度缩放（标准+单人=100%）
- 合作：剧情关卡式多人战役（玩家位 + 同盟 AI 补位、共享 intro/过场/目标、无条约）；难度与参战人数控敌强度；合作地图自动加载战役 TTS 本地化地名
- 详见 ``docs/zh/战役与合作战役改进说明.md`` （``docs/en/campaign-and-co-op-improvements.md``）
- 测试：``test_changelog_1429_coop_campaign_difficulty.py``、``test_changelog_1429b_campaign_browser_difficulty.py``、``test_changelog_1429c_coop_story_mission.py``、``test_changelog_1429d_coop_player_slots.py``、``test_coop_campaign_place_names.py``

1.4.3.8
-------

建造场、渐进式目标与异虫菌毯肿瘤：

- ``build_field_radius`` （格 BFS）与 ``build_field_radius_m`` （从 ``(x,y)`` 计米）；米制提供者在 ``build_field_persists`` / ``build_field_spreads`` 时也会绘制格标记——修复主巢仅写米制半径时的建造判定
- 触发器 ``register_objective``：登记通关所需主要编号但不显示/不播报；胜利判定改为 ``_required_objective_numbers`` 与 ``_completed_objective_numbers`` 比较，避免分步 ``add_objective`` 提前胜利
- F9 / ``add_objective``：多个主要目标时播报「主要目标 N：」（序号后带冒号）；仅一个目标时不读序号
- 星际 mod：女王 **生成菌毯肿瘤**/ 肿瘤 ** 延伸菌毯肿瘤**；技能属性 ``summon_requires_build_field``、``summon_requires_marked_field``
- 文档：``docs/zh/渐进式战役目标说明.md``、``docs/zh/星际异虫菌毯说明.md``；``modding.rst``、``mapmaking.rst``
- 测试：``test_build_rules.py`` （菌毯肿瘤）、``test_campaign_alliance_transfer_triggers.py`` （register_objective）、``test_objective_announce.py``

1.4.3.7
-------

狩猎系统与动物播报：

- 帝国时代式狩猎：击杀 ``is_huntable`` 动物后生成 ``food_carcass`` 尸体矿床；村民可采集；鹿/羊受击逃跑；羊可驱赶（``can_herd`` / ``herdable``\ ）
- 野生动物语音标识为「动物」（如「鹿 , 动物」），不再播报「中立 , NPC」；方格摘要单独归类为动物
- 仅含野生动物的 ``computer_only`` 槽位不进 ``ai`` 联盟，不与玩家、敌对 creep、其它动物群结盟（混编槽位除外）
- Ctrl+Shift+F4 切到仅含野生动物的玩家时播报「你是动物」；混合 NPC 与动物的玩家仍播报「你是中立 NPC」
- 随机地图出生点附近生成野生动物与浆果丛；科技 ``hunting_techniques`` 提升尸体采集
- 文档：``docs/zh/狩猎系统说明.md``\ ；``modding.rst`` 狩猎系统一节
- 测试：``soundrts/tests/test_hunting.py``\ 、``test_hunting_herd.py``\ 、``test_wildlife_identification.py``\ 、``test_wildlife_alliance.py``

1.4.3.6
-------

连发 / 序列攻击（``damage_seq``）：

- 修复连发间隔：rules 中的 ``(interval …)`` 现已生效（此前被硬编码为 0.4 秒）
- 省略 ``(damage …)`` 时可自动均分 ``mdg`` / ``rdg`` 基础伤害（支持小数伤害）
- 连发每一发都会触发 ``launch_mdg`` / ``launch_rdg``\ ；可在 ``style.txt`` 配置多个音效 ID
- 基础规则新增 ``repeating_crossbowman`` （诸葛弩手，由弓箭手升级；帝国时代诸葛弩式连发）
- 测试：``soundrts/tests/test_damage_seq_burst.py``
- 文档：``docs/zh/连发攻击与诸葛弩说明.md``\ ；``modding.rst`` 战斗系统一节

1.4.3.5
-------

战斗 AI 与中立单位：

- 玩家单位在 ``offensive``\ / ``defensive``\ / ``chase``\ 模式下不会主动攻击中立单位（``computer_only ... neutral``\ ）
- 防御模式仅因中立者存在不会触发撤退
- 强制攻击（``imperative``\ 的 go/attack，如 Ctrl+点击单位）仍可开战
- 中立 creep 自身仍为 guard + 被动反击；详见 ``docs/zh/单位默认模式与自动状态配置说明.md``

1.4.3.4
-------

新增程序化随机地图（RMG）：

- 入口：主菜单「开始游戏」→「随机地图」；联机建房地图列表中的「随机地图」
- 可配置：模板（标准/快速/宏观/通道）、尺寸、人数、2v2 组队、野怪、资源布局、地形、水域、宝箱、种子、停火条约
- 生成后播报种子与分享码；可用 **F5/F6** 在历史中回听（进入邀请电脑菜单后仍有效）
- **导入分享码** 可跳过逐步菜单；分享码格式 ``RMG1:…``\ ，详见 `随机地图指南 <randommap.htm>`_
- 菜单文本输入框（分享码、种子、登录名等）支持 **Ctrl+A/C/V/X** 全选、复制、粘贴、剪切
- 实现：``soundrts/randommap.py``\ 、``soundrts/randommap_menu.py``\ ；测试 ``soundrts/tests/test_randommap.py``

1.4.3.3
-------

序号条件扩展（``killed_target`` / ``npc_has_item`` / ``unit_lost`` / ``building_lost`` / ``key_unit_killed``）：

- 全局序号（不限方格）：``(killed_target <序号> <类型> [enemy|ally])``\ 、``(npc_has_item <序号> <类型> <物品>)``\ 、``(unit_lost <序号> <类型>)``\ 、``(building_lost <序号> <类型>)``\ 、``(key_unit_killed <序号> <类型>)``
- 方格序号：``(killed_target <方格> <序号> <类型>)``\ 、``(npc_has_item <方格> <序号> <类型> <物品>)``\ 等
- 与 ``killed_target`` / ``npc_has_item`` 序号规则一致；仅指定刷出序号单位/建筑丢失时成立
- 示例：``(building_lost 1 townhall) (defeat)`` 仅第 1 个刷出的市政厅被毁失败（不限方格）；``(building_lost a1 1 townhall)`` 限定 a1 格；``(unit_lost 3 footman) (defeat)`` 仅第 3 个步兵阵亡失败
- The Legend of Raynor 第 1 章演示初始 townhall 保护；详见 ``docs/zh/指定序号目标说明.md``
- 测试：``soundrts/tests/test_map_select_loss_triggers.py``

1.4.3.2
-------

新增无序号单位（rules.txt，``no_number 1``）：

- 仅对配置了 ``no_number 1`` 的单位类型生效；默认单位（如农民）仍始终报序号（「农民1在 a1」）
- ``no_number 1`` 且同类型仅 1 个存活：不报序号（「关羽在 a1」「骑士首领在 a1」）
- ``no_number 1`` 且同类型有 2 个及以上：播报序号（「关羽1」「关羽2」）
- 编组、方格、战报摘要同样遵循上述规则（如「你控制了关羽和2护卫骑士」）
- 配置说明见 ``modding.rst``；战役示例 ``raynor``、``npc_knight_leader`` （``The Legend of Raynor/rules.txt``）

1.4.3.1
-------

新增背包与装备栏系统：

- Shift+V 打开背包，Ctrl+V 打开装备栏，与 Alt+V 属性界面互斥，需单独选中一个己方单位
- 背包管理全部库存物品；装备栏专门浏览武器与护甲（含内置武器/护甲与背包中的可装备物品）
- 界面内：方向键浏览，Enter 装备/使用，Shift+Enter 卸下，Delete/Shift+Delete 丢弃，g 朗读简介
- 支持同型物品模型：同一 type_name 可定义为 ``class item``\ 并设置 ``equippable_as_weapon 1``\ / ``equippable_as_armor 1``\ ，数值在装备时套用、卸下后还原
- 出厂 ``weapons``\ / ``armor``\ 若对应类型为可装备 item，则自动创建物品实例放入背包；若无同类型内置装备且 ``spawn_weapons_equipped``\ / ``spawn_armor_equipped``\ 为 1（默认），则静默装备（需 ``inventory_capacity``\ > 0）
- 传统 ``class weapon``\ / ``class armor``\ 仍为内置装备，在装备栏显示为「内置武器/内置护甲」，不可卸下或丢弃
- 混合内置与背包装备时：内置优先出厂装备；``spawn_weapons_equipped 1``\ 时 item 武器留在背包且无法装备；内置装备只能与内置装备切换，item 装备只能与 item 装备切换，二者不可互相切换（护甲同理）

新增单位默认模式与自动状态配置（rules.txt）：

- ``ai_mode``\ ：开局默认 AI 模式，取值 ``offensive``\ / ``defensive``\ / ``guard``\ / ``chase``
- ``auto_gather``\ 、``auto_repair``\ ：工人开局是否自动采集、自动修理（默认均为 1）
- ``auto_explore``\ ：可移动单位开局是否自动探索（默认 0）
- ``can_auto_explore 1``\ ：该单位命令菜单提供「启用/禁用自动探索」选项

新增给 NPC 物品功能：

- ``give``\ 指令：携带物品时右键非敌对单位、命令菜单或快捷键 g，将物品交给目标
- 目标须 ``receive_items 1``\ （默认 0）；可用 ``accepted_items``\ 限制物品白名单，``accept_from``\ 限制给予者关系（self/ally/neutral/enemy）
- ``npc_has_item`` 触发器：判断某 NPC 是否已收到指定物品，支持方格参数区分同名 NPC
- ``npc_has_item`` / ``killed_target`` 序号格式（``<方格> <序号> <类型>``）；The Legend of Raynor 第 28 章演示；详见 ``docs/zh/指定序号目标说明.md``
- 示例：联机 ``res/multi/give_demo.txt``\ ；战役 ``The Legend of Raynor`` 第 14–16 章（``14.txt``\ / ``15.txt``\ / ``16.txt``\ ）演示 ally/neutral/enemy 三种交付关系

新增寻找物品通关功能：

- ``has_item``\ 触发器：判断当前玩家是否在任意存活单位库存中持有指定物品（可选数量参数）
- 物品须为 ``class item``\ 且 ``consume_on_pickup``\ 不为 1，拾取后进入 inventory 方可检测
- The Legend of Raynor 第 17 章（17.txt）为示例：找到 ``lost_amulet``\ 即完成目标并通关

新增携带物品到达与剧情交付：

- ``has_brought_item``\ 触发器：玩家单位携带指定物品到达某方格即成立（无需丢弃）
- ``remove_item``\ 触发器动作：从玩家库存移除并销毁物品，配合 ``cut_scene``\ 实现剧情上交
- ``do``\ 触发器动作：按顺序执行多个子动作（``if``\ 不能代替）
- The Legend of Raynor 第 18 章（18.txt）为示例：携带 ``mana_potion``\ 到 c3 祭坛，过场后物品消失

新增地面物品与复合条件：

- ``remove_ground_item``\ 触发器动作：删除某方格地面上的指定物品（如开箱后移除秘宝）
- ``and``\ 触发器条件：所有子条件均成立时返回真
- ``find``\ 须方格在前、类型在后（``not``\ 内嵌套亦然）；错误顺序会导致条件恒真
- The Legend of Raynor 第 20 章（20.txt）为示例：丢弃秘宝开箱 → 拾取全部金币

战役外交与单位归属触发器：

- ``alliance_request``\ 触发器动作：某方向玩家发起结盟申请；战役中玩家用 **Ctrl+F4** 同意（无需 F12 选目标）
- ``alliance_with``\ / ``alliance_request_pending``\ 触发器条件：检测是否已结盟 / 是否有待处理申请
- ``transfer_units``\ （别名 ``convert_units``\ 、``change_owner``\ ）：把某玩家的单位改归属给另一玩家
- ``allied_assist``\ 触发器动作：让盟友自主参战（站岗→追击）；支持单位选择符仅让部分单位切追击
- ``allied_control``\ 触发器动作：让玩家直接指挥盟友部队（可全盟友或按单位选择符仅移交部分单位）；未移交单位自动切追击
- ``add_inventory_item``\ 触发器动作：把物品放入单位背包（跨章携带、剧情奖励）
- ``set_ai_mode``\ / ``set_yield_on_defeat``\ 触发器动作：运行时切换 AI 模式与比武认输
- ``units_yielded``\ / ``units_yielded_by``\ 条件、``has_entered``\ 条件、``stop_all_units``\ / ``release_yielded_units``\ 动作：认输计数（可按攻击者筛选）、进入方格、停火与恢复可战
- The Legend of Raynor 第 24–27 章（北方联军线：密信/信物/王旗/比武）；说明见 ``docs/zh/战役密信与结盟说明.md``

``phase_targets``\ 排除写法：

- 前缀 ``-``\ 表示排除，例如 ``phase_targets -building``\ 表示除建筑外的所有单位
- 可与正向项混用，例如 ``phase_targets soldier -footman``

``is_a``\ 排除继承 ``-``\ 前缀：

- 例如 ``is_a footman(-hp_max)``\ 与 ``is_a footman(apart hp_max)``\ 等价
- 可写多个排除项，例如 ``is_a footman(-hp_max -mdg)``

修复的 bug：

- 修复单位升级（``can_upgrade_to``\ ）或切换形态（``can_change_to``\ ）后丢失选中状态的问题：例如用 g 选中弓箭手后升级为暗黑弓箭手，升级完成后仍保持选中，无需重新选中。


1.4.3.0
-------

修复的 bug：

- 修复战役胜负判定的一个严重 bug：当一张战役地图里有两个（及以上）敌方电脑时，完成任务目标后游戏不会结束，必须再手动消灭剩下的电脑才会宣布胜利。根源是胜利结算时一边遍历玩家列表一边删除被击败的玩家，导致紧随其后的那个电脑被跳过。现已修正，完成任务目标即可正常胜利。
- 修复了当单位离开当前 square 后，该 square 的对象会消失 4–5 秒钟才会重新出现的 bug
- 修复战役里 F12（动态结盟）会误切到电脑的问题：战役里没有真正的对手玩家，电脑只是触发器脚本，F12 不应能切到任何目标；此前被 ``(ai ...)``\ 触发器升格的电脑会漏进候选并被读成内部名 ``ai_timers``\ 。现在战役内 F12 不再选中任何目标。
- 战役里被 ``(ai easy)``\ 等触发器升格的电脑同样视为无身份的 NPC：其单位归属、切换玩家等播报统一为「NPC」，而不再读出内部名 ``ai_timers``\ ；并且不再播报任何战役电脑「被击败/退出了游戏」（含被升格的电脑）。
- Ctrl+Shift+F4 现在会将触发器电脑播报为「NPC」。


1.4.2.9
-------

- 从服务器下载的地图将保留原始名称
- 与本地地图内容相同的地图不会再次下载
- 多人录像以 ``replay1``\ 、``replay2``\ 、``replay3``\ 等名称存储


1.4.2.8
-------

- 用 Cython 优化了引擎的部分模块，带来小幅性能提升
- 新增中立电脑。中立电脑除非先被攻击，否则不会攻击任何人。要让某个 ``computer_only``\ AI 中立，在其所在行加上 ``neutral``\ 关键词，例如：``computer_only 0 0 neutral <单位与建筑>``\ 。不加 ``neutral``\ 关键词时，电脑保持敌对
- 新增为特定玩家定义固定出生格子的功能（``player_start <N> <square>``\ ）。详见地图制作指南


1.4.2.7
-------

- 你现在可以重命名存档和录像文件（支持英文、中文或任何其他字符）。方法：在 ``user/saves``\ 或 ``user/replays``\ 文件夹中重命名；或在游戏内的读取/录像菜单中选中文件，按 Shift+Enter 输入新名称
- 按 Delete 删除存档或录像（带确认）；按 Shift+Delete 立即删除


1.4.2.6
-------

- 每个模组最多 10 个存档槽位；各模组的存档、记忆点和录像相互独立
- 取消一局游戏会创建记忆点；主菜单出现「继续未完成的游戏」
- 录像文件同样按模组区分


1.4.2.5
-------

- 新增 ``can_advance``\ 用于阶段升级（与 ``can_research``\ 区分）；在属性界面中显示
- 游戏开始时显示建筑的默认起始阶段（当建筑具有 ``can_advance``\ 时）
- ``def parameters``\ 中的 ``hide_locked_commands``\ 可隐藏未满足要求的命令


1.4.2.4
-------

- 新增 ``class phase``\ （年代式进度）：``phase_targets``\ 、``phase bonus``\ 、``units_auto_upgrade``
- 动态结盟：每个结盟请求现在有各自独立的冷却时间


1.4.2.3
-------

- 游戏过程中动态结盟（F12 / Shift+F12 选择目标；F4 发送请求；Ctrl+F4 接受；Shift+F4 取消/拒绝/离开）；游戏开始前已固定的联盟无法在游戏中更改
- 合作战役 bug 修复


1.4.2.2
-------

- 条约模式：在选定持续时间内（最长 20 分钟）保持和平，之后进入战争
- 服务器上的合作战役：任何玩家完成目标都会为队伍做出贡献


1.4.2.1
-------

修复的 bug：

- 通行音效不再延迟地名和坐标的播报
- 单位每次复活不再获得速度加成
- 升级对 ``cost``\ 、``time_cost``\ 、``population_cost``\ 的更改现在会持久保存
- heal 和 harm 升级不再应用到任意单位类型
- 空中单位海拔恢复为 1.3.8.1 的行为


1.4.2.0
-------

修复的 bug：

- 复活的单位可以再次接收命令
- 自攻击不再触发冲锋伤害
- 折扣升级不再影响没有该折扣科技的单位
- 地面冲锋溅射不再击中空中单位
- 运载量 ≥ 99 的运输工具不再装载自己


1.4.1.9
-------

- ``square_name``\ 层级最多 3 级（省 / 市 / 区）；从其他区域进入时 TTS 播报名称
- 进一步的性能优化


1.4.1.8
-------

- 地图坐标使用 ``x,y``\ （例如 ``1,1``\ ）代替字母+数字；旧记法仍被接受
- ``square_name``\ 用于命名方格；翻译在 ``tts.txt``\ 中
- 阵营起始单位和资源可在 ``rules.txt``\ 中定义（地图定义优先）


1.4.1.7
-------

- 统一技能系统（``class skill``\ ）及 ``effect_target``\ 、``effect_range``
- 多属性增益、光环增益（``buff_radius``\ ）、扩展的 harm/heal/regen 参数


1.4.1.6
-------

- 武器上可定义 debuff
- 修复存档加载失败


1.4.1.5
-------

- ``style.txt``\ 中的 ``intro``\ 关键词用于单位描述
- 恢复对角感知
- 修复非生产建筑上的生产界面


1.4.1.4
-------

- 1.3.5.2 触发器已迁移；td1–td3 地图可玩


1.4.1.3
-------

- 武器与护甲系统；手动换武器（A / Shift+A / B+X）；``auto_weapon_switch``
- 物品系统从 1.3.5.2 迁移
- 墙和大门可再次建造


1.4.1.2
-------

- 工人上的 ``can_repair``\ ；改进水上单位寻路和岸边采矿
- 属性界面中更多属性


1.4.1.1
-------

- 增强的属性界面，支持交互式浏览（``can_train``\ 、技能、研究、``can_build``\ ）
- 工人的 ``can_repair_ships``\ ；岸边修船（距离 6）和建筑自动修船（距离 8）


1.4.1
-----

- 第一人称 RPG 视角为 360°；改进移动精度


1.4.0.9
-------

- 第一人称 RPG 模式指南；F8 动态缩放 3×3 至 15×15；路径感知浏览


1.4.0.8
-------

- ``minimal_mdg``\ / ``minimal_rdg``\ 改回 ``minimal_damage``
- 第一人称模式中的 RPG 技能热键（1–0）


1.4.0.7
-------

- 修复暴击率
- crazy-Mod 可玩


1.4.0.6
-------

- 服务器观战模式；修复多人胜/负音效


1.4.0.5
-------

- ``food``\ 关键词替换为 ``population``\ （例如 ``population_cost``\ ）
- 更丰富的经济：资源建筑、自动/手动耕种与生产
- ``rpg_bindings.txt``\ 预留给未来 RPG 热键自定义


1.4.0.4
-------

- ``auto_production``\ / ``manual_production``\ ；``is_gather``\ / ``is_create``\ ；``class resource``\ 与 ``class deposit``\ 分离


1.4.0.3
-------

- 阵营背景和战斗音乐（``<faction>_music``\ 、``<faction>_battle_music``\ ）


1.4.0.2
-------

- 菜单选择/确认/返回音效；各菜单背景音乐和战斗音乐


1.4.0.1
-------

- 冲锋与反冲锋机制；扩展增益触发率
- 新失败条件：``unit_lost``\ 、``key_unit_killed``\ 、``key_units_killed``\ 、``units_lost``\ 、``buildings_lost``\ 、``has_killed``\ ；``killed_target``\ 和 ``has_killed``\ 支持 ``enemy``\ / ``ally``


1.4
---

- 战斗重做：``mdg``\ + ``mdg_vs``\ （加法）、暴击、破甲、爆炸
- 整合 1.3.5.2 的英雄与 XP 系统
- ``title``\ / 战役 / 地图参数接受引号字符串；``tts.txt``\ 翻译格式
- 支持 ``multi/``\ 中未压缩的高级地图
- 修复在输入框中输入匹配名称时播放音效


1.3.9.8
-------

- 整合 1.3.5.2 的增益/减益系统
- 进入敌方所在方格时敌人立即出现


1.3.9.7
-------

- 带数量的 ``can_train``\ ；``can_change_to``\ ；``can_use_tech``\ / ``can_use_skill``\ 菜单修复


1.3.9.6
-------

- 升级上的百分比 ``cost``\ / ``time_cost``\ / ``population_cost``\ ；小数资源显示


1.3.9.5
-------

- 对象筛选（M / N 键）；``cfg/language.txt``\ 语言选择


1.3.9.3
-------

- 地形掩护/闪避修复；研究应用于未来单位；暂时移除溅射命中音效


1.3.9.2
-------

- 升级对 cost/time/population 的效果；溅射命中音效；属性界面中的浮点属性


1.3.9.1
-------

- 溅射 ``_vs``\ 属性；延迟 ``falling``\ 音效；抛射物高度攻击规则


1.3.9.0
-------

- 恢复 ``extraction_time``\ / ``extraction_qty``\ ；Alt+V 属性界面及 ``attributes_bindings.txt``


1.3.8.8
-------

- 工人上的 ``can_gather``\ / ``gather_time``\ / ``gather_qty``\ ；``is_rewards``\ / ``rewards_resource``


1.3.8.7
-------

- 击杀/摧毁资源奖励；自拆返还


1.3.8.5
-------

- 通过 ``mods/<mod>/multi/``\ 实现模组专属地图


1.3.8.4
-------

- 建筑资源生产（``is_production``\ 、``production_type``\ 等）


1.3.8.3
-------

- 灵活的 ``is_a``\ 继承（选择性、排除、多父级）


1.3.8.2
-------

- 夺取归属；``mdg_projectile``\ / 地形掩护/闪避；改进离开容器
- 重大战斗重做：``mdg``\ /``rdg``\ /``mdf``\ /``rdf``\ 系统；伤害序列；``class skill``\ ；guard/chase 模式；音效系统重构


1.3.8.1
-------

对于多人游戏，本版本需要：

- 客户端：1.3.8 或更高
- 服务器：1.2-c12 或更高

相对 1.3.8 的主要变化：

修复的 bug：

- 在已读取的游戏中，R 键会选中任意士兵（感谢 Marco Oros 报告该 bug）
- 当构建菜单耗时过长时，重复的按键会累积
- 希望能避免创建声源时出现的任何音量故障
- 自定义地图会出现在官方地图之后
- 运行 server.py 不再需要任何包


1.3.8
-----

对于多人游戏，本版本需要：

- 客户端：1.3.8 或更高
- 服务器：1.2-c12 或更高

相对 1.3.7 的主要变化：

- 在 cfg/parameters.toml 中新增了 tts_digit_coefficient

修复的 bug：

- 如果地面与水域两个格子都是地面，则它们之间的通路会被保留
- 单位更经常地逃回上一个格子
- 正确处理并非时间戳的录像文件（感谢 dnl-nash）
- 仅当客户端为可执行文件时才发送 bug 报告

翻译：

- 新增白俄罗斯语翻译（感谢 Uladzimir）
- 更新斯洛伐克语翻译（感谢 Marco Oros）


1.3.7
-----

对于多人游戏，本版本需要：

- 客户端：1.3.7 或更高
- 服务器：1.2-c12 或更高

相对 1.3.6 的变化：

现在单位可以从载具或建筑内部发动攻击：

- 远程单位可以照常攻击
- 近战单位只能从地面攻击，且没有任何额外射程
- 近战单位无法从空中载具攻击
- 在默认游戏中：单位可以进入墙、大门和塔楼

修复了对相邻格子进行反击时的问题：

- 无法反击的单位将保持沉默
- 防御性单位不会反击

其他：

- 恢复了「进攻！」提示
- bug 修复：如果命令是从另一个格子下达的，单位将不会进入建筑
- 修复：读取游戏
- 跨格攻击可能更好用了

模组制作：

- 新增了 armor_vs
- 现在 ``damage_vs``\ 可与 ``is_a``\ 配合（包括多级继承和多重继承）

地图制作：

- 官方 ``multi``\ 地图移至 res/multi
- 多人「文件夹地图」必须打包压缩才能在线游玩
- 移除了 ``maperror.txt``\ 文件（相关信息已包含在游戏内的错误消息中）

战役格式的变化：

- mods.txt 被 campaign.txt 中的 ``mods``\ 关键词取代
- campaign.txt 中的 ``title``\ 关键词
- 新约束：复杂的任务地图必须以 zip 文件形式存储


1.3.6
-----

对于多人游戏，本版本需要：

- 客户端：1.3.6 或更高
- 服务器：1.2-c12 或更高

相对 1.3.5 的变化：

单位行为：

- bug 修复：附近的攻击性单位会再次自动反击（它们会移动到攻击者的格子，然后返回起始位置）
- bug 修复：防御性单位会再次逃跑

界面：

- 被控单位的描述将不那么令人困惑
- 改进了编组跟随（空格键）：界面通常会跟随编组的前部
- bug 修复：在 style.txt 中，noise_if_very_damaged 从不播放
- bug 修复：SAPI 无法工作

水域：

- 从现在起，游戏不会创建两栖通路（解决了以下问题：如果到目的地的最短路径包含一个水域格子，陆地单位会走进水里并死亡）
- 问题修复：法师可以把水上单位召回到非水域格子（现在法师会把水上单位召回到最近的相邻水域格子）

多人游戏：

- 启动非私人服务器会自动配置路由器（仅当路由器启用 UPnP 时有效；该配置会在路由器闲置 20 分钟后被自动移除）
- 更简便的独立服务器配置
- 通过 UDP 广播自动发现本地服务器（本地服务器会出现在「从列表中选择服务器」菜单中）
- bug 修复：在多人游戏中，非管理员玩家可以设置更慢的速度

翻译：

- 更新了巴西葡萄牙语、中文、捷克语、意大利语和斯洛伐克语翻译

地图制作：

- 在可能的情况下，发出警告而非地图错误
- bug 修复：在某些情况下，触发器选中的单位多于指定数量。例如，如果 a1 中有 3 条巨龙和许多步兵，``(a1 10 dragon footman)``\ 会选中 3 条巨龙和 7 个步兵。


1.3.5
-----

对于多人游戏，本版本需要：

- 客户端：1.3.5 或更高
- 服务器：1.2-c12 或更高

相对 1.3.4 的变化：

- bug 修复：无法保存带地形的游戏
- 修复：如果命中击杀了目标，则命中音效不会播放
- 修复：如果格子中没有足够空间创建单位，游戏会卡死

国际化：

- 将所有 tts.txt 文件转换为带 BOM 签名的 UTF-8。编码仍在第一行显式定义为 UTF-8。BOM 签名可能有助于某些文本编辑器自动选择 UTF-8。
- 对于 tts.txt 以外的文本文件（rules.txt、style.txt 等）将始终使用 UTF-8（或 ASCII）
- 更新了西班牙语翻译（感谢 Oscar Corona）


1.3.4
-----

对于多人游戏，本版本需要：

- 客户端：1.3.4 或更高
- 服务器：1.2-c12 或更高

相对 1.3.3 的变化：

- 可能修复了更多情况下的语音问题（如果你仍无法启动客户端，请报告）
- 恢复了存档与读档（似乎可以工作，但请务必小心）
- 为「aggressive computer 2」恢复了无限资源和科技（更有趣）

多人游戏：

- 客户端会记住此前下载的服务器列表，并在元服务器暂时宕机时使用它
- 在「输入服务器的 IP 地址」中，输入空 IP 地址会选择你自己的电脑（无需输入「localhost」）
- 独立服务器：移除了 pygame 依赖

界面：

- 控制台命令：「a u_recall」会为当前玩家添加召回升级
- 小 bug 修复：界面不会跟随运输工具内的单位（如果该单位在被运输前处于跟随模式）

国际化：

- 更新了意大利语翻译（感谢 Luigi Russo）

主线战役：

- 新增了第 12 章，一张展示密林如何运作的小地图（规则是：「两片密林之间的任何通路都被封锁」）

提示：要快速检查你已经玩过的战役中某一章的改进：

- 按 Escape 下方的「控制台」键，再按「v」和 Enter 立即取胜
- 或编辑 user/campaigns.ini：例如在 [single_campaign] 中写「chapter = 12」


1.3.3
-----

对于多人游戏，本版本需要：

- 客户端：1.3.3 或更高（如果兼容）
- 服务器：1.2-c12、1.3.0、1.3.1、1.3.2、1.3.3 或更高（如果兼容）

相对 1.3.2 的变化：

- bug 修复：单位在使用需要靠近的能力（致命迷雾、驱魔……）后不会停下，会继续移向敌人……
- bug 修复：游戏会为以施法者为中心的能力（例如：扶起亡灵）要求一个目标
- bug 修复：无法从低地看到水（例如在地图 jl7 中）

地图界面应该感觉更自然：

- 如果你控制的是飞行单位，在地图上移动不会引发碰撞
- 如果你正在定义召回（例如）命令的目标，在地图上移动不会引发碰撞
- 移除了水域与低地之间的碰撞

密林：

- bug 修复：密林被清除时会创建通路（即使之前并没有任何通路）
- 现在森林只要拥有至少 7 棵树木就算密林（原为 3 棵）
- 多人地图 8：更新（7 棵树木）并改进（更快的经济）
- 编辑器：更新了地形调色板（至少 7 棵树木即为密林）

国际化：

- bug 修复：含非 US-ASCII 字符的地图在默认使用 GBK 或 UTF-8 的平台上无法读取（现在地图始终按 UTF-8 读取，错误以「?」替换）
- 将以下地图转换为 UTF-8：bs2、can1、qc1、qc2 和 qc3
- 更新了波兰语翻译（感谢 Patryk Mojsiewicz）

主线战役中的微小变化：

- 第 9 章：随着「致命迷雾」bug 的修复，死灵法师应该更容易应付了
- 略微改进了第 5 章和第 10 章

提示：要快速检查你已经玩过的战役中某一章的改进：

- 按 Escape 下方的「控制台」键，再按「v」和 Enter 立即取胜
- 或编辑 user/campaigns.ini：例如在 [single_campaign] 中写「chapter = 11」


1.3.2
-----

相对 1.3.1 的变化：

主要变化：

- 「选择服务器」菜单将包含任何具有兼容服务器版本的服务器（不仅是相同版本），这样服务器就不必那么频繁地更新
- 允许版本不同但兼容的客户端一起游玩
- 「最近的」服务器会在「选择服务器」菜单中优先显示（响应延迟最小的服务器）
- 检查服务器是否可用所花的时间会在「选择服务器」菜单中标明（以毫秒表示）以便比较
- 不可用的服务器不会出现在「选择服务器」菜单中

次要变化：

- 略微降低了 server.log 的冗长程度
- 改进了独立服务器指南（不过仍不完美）
- 在文档中加入了「版本说明」


1.3.1
-----

相对 1.3.0 的变化：

- 可能已修复：游戏在 Windows 7 上无法启动（ImportError: DLL load failed while importing _socket）
- 修复：有时在删除「appdata\\local\\Temp」中的「gen_py」文件夹之前游戏无法启动（AttributeError: module 'win32com.gen_py...' has no attribute 'CLSIDToClassMap'）
- 修复：vcruntime140.dll 可能缺失
- 修复：无法获取服务器列表
- 修复：按 A 会像以前一样工作，按 Control+A 则只选择未激活的命令


1.3.0
-----

相对 1.2-c12 的变化：

主要变化：

- 只有墙和大门可以建在出口上（或任何「仅可建在出口上」的建筑）
- 现在塔楼只能建在子格子的中心，且每个子格子只能有一座塔楼。塔楼的位置可以通过几种方式选择：

  - 在缩放模式下：选择当前子格子（必须空闲）
  - 在格子模式下：选择任意空闲子格子，从中央那个开始
  - 如果选中了任何对象：选择其所在的子格子（必须空闲）

- 现在屏幕阅读器是默认的 TTS

技术变化：

- 迁移到 Python 3
- 用 accessible_output2 替换了所有 TTS（已打补丁以支持 Linux）

修复的 bug：

- 无法控制编组中被复活的单位
- 一个为消灭入侵者而推迟建造或采集的工人不会回到其任务，而是就地完成
- 单位能从下方看到高台
- 单位无法对角看到
- 无法选择一个格子作为建造大门的目标（会改选一个空闲出口）

界面改进：

- 缩放模式：在未选择特定目标的情况下确认建墙（或建门）命令，会自动选择本地出口（如果它未被封锁）
- Tab 会优先选择任意敌人
- 在选中目标时按 Escape 会选择当前格子
- bug 修复：现在进入或退出缩放模式会把子格子或格子选为目标（而非保留已选目标）
- 在一些消息中加入了逗号（以提高清晰度）
- 更简短的敌情摘要
- bug 修复：会说「建筑工地」而不说建筑类型
- bug 修复：在缩放模式下，建筑的默认命令没有把集结点设到子格子，而是设到了格子
- bug 修复：暂停的游戏无法退出
- bug 修复：按空格键会告知确切的命令，即使一些单位有不同的命令（这对于检查有多少工人在采集黄金、木材等非常有用（按 D）。也可用于了解编组中有多少单位在移动、有多少已到达。按 Control + Shift + S 会给出士兵和工人命令的完整摘要。）
- 在建造模式下，Tab 会在出口之前先选择草地
- 巡逻命令的描述会概述所有途经点
- bug 修复：按 Tab 会选中被封锁的出口
- bug 修复：不再可能在同一出口上建造另一堵墙
- 缩放模式：如果在某个子格子上确认了建造命令却找不到可建造的土地，将抛出错误（而不是去其所在格子中搜索可建造的土地）
