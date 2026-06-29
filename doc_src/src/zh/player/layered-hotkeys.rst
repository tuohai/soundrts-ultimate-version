# 分层热键方案说明

本文介绍 SoundRTS 的分层界面热键系统：全局底座 + 当前界面层，同一物理键在不同界面可有不同语义。适用于玩家日常操作与 Mod 作者自定义热键。


----


1. 概述与设计动机
-----------------


旧方案的问题
~~~~~~~~~~~~


原先所有热键集中在单一文件 ``res/ui/bindings.txt`` 中，键位逐渐饱和，同一字母在不同场景（选单位、选命令、浏览地图）含义冲突，难以扩展。

新方案
~~~~~~~~


- 全局层：资源、方向移动、方格跳转、确认命令等，任何界面均可用。
- 界面层：按当前模式加载专属热键（单位、建筑、命令、技能、地图等）。
- 界面切换：F 键在模式组内切换；帮助 / 地图 / 外交为覆盖式界面，退出后恢复先前模式。

实现入口：``soundrts/clientgame/interface_modes.py``。


----


2. 架构与加载规则
-----------------


.. code-block:: text

   flowchart TD
       global[global_bindings.txt]
       mode[当前界面txt]
       custom[cfg/bindings.txt]
       mod[mod bindings.txt]
       global --> merge[合并加载]
       mode --> merge
       custom --> merge
       mod --> merge
       merge --> active[当前生效热键]


加载顺序
~~~~~~~~


1. `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_ （全局底座）
2. 当前模式文件（见下表）
3. 用户自定义 `cfg/bindings.txt <../../../soundrts/paths.py>`_ （``CUSTOM_BINDINGS_PATH``）
4. 非 stub 的 Mod ``bindings.txt`` （兼容旧 Mod 追加覆盖）

后加载覆盖先加载的同名按键。

子界面与 RPG
~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 场景
     - 行为
   * - 背包 / 装备 / 属性
     - 临时替换 ``\_bindings``；退出时 ``restore_active_bindings`` 恢复分层绑定
   * - RPG 第一人称
     - 额外叠加 [``res/ui/rpg_bindings.txt``](../../../res/ui/rpg_bindings.txt)
   * - 地图编辑器
     - 独立 [``res/ui/editor_bindings.txt``](../../../res/ui/editor_bindings.txt)，不受分层系统影响



模式文件一览
~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 模式
     - 文件
   * - 全局
     - ``global_bindings.txt``
   * - 单位选择
     - ``unit_bindings.txt``
   * - 建筑选择
     - ``building_bindings.txt``
   * - 命令
     - ``command_bindings.txt``
   * - 技能
     - ``skill_bindings.txt``
   * - 第一人称（RPG）
     - ``rpg_bindings.txt``
   * - 帮助与查询
     - ``help_bindings.txt``
   * - 地图浏览
     - ``map_bindings.txt``
   * - 外交
     - ``diplomacy_bindings.txt``




----


3. 界面切换（F 键与 ESC）
-------------------------



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - F1
     - 单位选择 ↔ 建筑选择
   * - F2
     - 命令 ↔ 技能
   * - F3
     - 背包 ↔ 装备栏（需先选中单个单位；见 [背包与装备栏功能说明.md](背包与装备栏功能说明.htm)）
   * - F4
     - 进入帮助与查询（再按 F4 或 Esc 退出）
   * - F12
     - 进入外交（再按 F12 或 Esc 退出）
   * - ESC
     - 取消命令 / 退出子界面；无上述状态时进入地图浏览



切换非地图界面时，会播报对应界面名（如「单位选择界面」「命令界面」）。

ESC 进入地图浏览的特殊行为
~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 动作
     - 语音播报
     - 内部状态
   * - ESC 进入地图
     - 始终播报「地图浏览界面」+ 当前方格整体概况
     - 若此前在地图内选过矿点/草地/通道，静默恢复 `interface.target`
   * - 地图内按 ``f`` / ``g`` / ``m`` / ``p`` 等
     - 照常播报该元素名称
     - 同时记住选中目标，供离开地图后恢复



示例：地图模式 ``f`` 选金矿 → F1 切单位界面选农民 → ESC 回地图 → 听到「地图浏览界面，8，13，1 市政厅…」等方格概况，不会重复播报金矿；但焦点仍在金矿上，可直接按回车让农民开采。

离开地图界面（切到单位/建筑/命令等）时，系统自动 ``save_map_browse_target`` 保存当前地图焦点。


----


4. 全局热键
-----------


以下热键在任何界面均生效（``global_bindings.txt``）。

资源与人口
~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``z``
     - 资源 1 状态
   * - ``x``
     - 资源 2 状态
   * - ``SHIFT Z``
     - 资源 3 状态
   * - ``c``
     - 人口状态



快捷入口（兼容旧键位）
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``ALT V``
     - 属性界面
   * - ``SHIFT V``
     - 背包
   * - ``CTRL V``
     - 装备栏



目标选择
~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``TAB`` / ``SHIFT TAB``
     - 下一个 / 上一个目标
   * - ``CTRL TAB`` / ``CTRL SHIFT TAB``
     - 下一个 / 上一个有用目标



方向移动
~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - 方向键
     - 移动 1 格
   * - ``SHIFT`` + 方向键
     - 移动 5 格
   * - ``CTRL`` + 方向键
     - 移动 1 格（无碰撞检测）
   * - ``CTRL SHIFT`` + 方向键
     - 移动 5 格（无碰撞检测）



方格跳转
~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``PAGE DOWN`` / ``PAGE UP``
     - 下一个 / 上一个已侦察方格
   * - ``CTRL PAGE DOWN`` / ``CTRL PAGE UP``
     - 冲突方格
   * - ``ALT PAGE DOWN`` / ``ALT PAGE UP``
     - 未知方格
   * - ``SHIFT PAGE DOWN`` / ``SHIFT PAGE UP``
     - 资源方格



默认命令与确认
~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``BACKSPACE``
     - 默认命令
   * - ``SHIFT BACKSPACE``
     - 默认命令（排队）
   * - ``CTRL BACKSPACE``
     - 默认命令（强制）
   * - ``RETURN`` / 小键盘 ``ENTER``
     - 确认命令
   * - 配合 ``SHIFT`` / ``CTRL``
     - 排队 / 强制等变体



观察与查询
~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``LCTRL`` / ``RCTRL``
     - 观察（examine）
   * - ``SPACE``
     - 单位状态
   * - ``v``
     - 生命值
   * - ``F9`` / ``SHIFT F9``
     - 任务目标
   * - ``F11``
     - 玩家列表



系统功能
~~~~~~~~



.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``F5`` / ``F6``
     - 历史回放上一条 / 下一条
   * - ``F10`` / ``CTRL C`` / ``ALT F4``
     - 游戏菜单
   * - ``HOME`` / ``END`` 等
     - 音量
   * - ``ALT SPACE`` / ``CTRL SPACE``
     - 第一人称模式
   * - ``CTRL F2``
     - 画面开关
   * - ``CTRL F3``
     - 报时开关
   * - ``CTRL SHIFT F4``
     - 切换视角玩家
   * - ``ALT M`` 等
     - 音乐音量




----


5. 各单位界面热键
-----------------


5.1 单位选择界面
~~~~~~~~~~~~~~~~


文件：``unit_bindings.txt``


.. list-table::
   :header-rows: 1

   * - 类别
     - 按键
     - 说明
   * - 士兵批量
     - ``a``
     - 本地全部士兵；``CTRL a`` 全图
   * - 逐个切换
     - ``q`` / ``SHIFT q``
     - 本地；``CTRL q`` 全图
   * - 命令字母
     - ``b``
     - 按 style.txt 中 order 的 ``shortcut`` 选命令
   * - 过滤器
     - ``m`` / ``n``
     - 阵营 / 类型过滤（选目标时）
   * - 农民
     - ``s`` 批量 / ``w`` 逐个
     - 原 ``d``/``e`` 键位
   * - 士兵 1–7
     - `d/e` … `;/p`
     - 两行键区，与建筑界面同区
   * - 编组
     - ``1``–`5` 设组，`6`–`9` 召回
     - ``CTRL`` 设全图组



单位界面可单独覆盖 ``BACKSPACE`` 默认命令（仅单位界面生效）。

5.2 建筑选择界面
~~~~~~~~~~~~~~~~


文件：``building_bindings.txt``


.. list-table::
   :header-rows: 1

   * - 键区
     - 映射
   * - ``d f g h j k l ;``
     - building1 – building8
   * - ``e r t y u i o p``
     - building9 – building16



每键：本键选本地同类建筑；``SHIFT`` + 本键逐个切换；``CTRL`` + 本键选全图同类。

Mod 配置：在 ``style.txt`` 为单位设置 ``keyboard building1`` … ``keyboard building16`` （与通用 ``keyboard building`` 并存）。基地战役示例：townhall→building1，house→building2 等。

5.3 命令界面
~~~~~~~~~~~~


文件：``command_bindings.txt``


.. list-table::
   :header-rows: 1

   * - 序号
     - 按键
   * - 浏览
     - ``a`` / ``SHIFT a``
   * - 1–9
     - `s d f g h j k l ;`
   * - 10–18
     - ``w e r t y u i o p``
   * - 19–30
     - ``1``–`0` `-` `=`
   * - 重复
     - ``ALT x`` / ``ALT z``



命令按当前单位菜单排序后的序号选取；不足 30 条时多余键播报「无」。

5.4 技能界面
~~~~~~~~~~~~


文件：``skill_bindings.txt``


.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``a`` / ``SHIFT a``
     - 浏览技能菜单（下一项 / 上一项）



5.5 第一人称（RPG）界面
~~~~~~~~~~~~~~~~~~~~~~~


进入第一人称模式（全局 ``ALT SPACE``）时，在当前界面热键之上叠加 ``rpg_bindings.txt``。


.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - `1`–`9`
     - 技能 1–9
   * - ``0``
     - 技能 10
   * - `-` / `=`
     - 技能 11 / 12
   * - ``ALT /``
     - 技能列表
   * - ``CTRL A``
     - 自动攻击
   * - ``CTRL F8`` / ``SHIFT F8`` / ``ALT F8``
     - 缩放精细度增减 / 查询



方向键与 ``SHIFT`` +方向键在第一人称下为前进、后退、平移与转向（见该文件注释）。

5.6 地图浏览界面
~~~~~~~~~~~~~~~~


文件：``map_bindings.txt``

方向移动与方格跳转见第 4 节（全局可用）。

以下键在当前方格内循环选择目标（不切换方格）：


.. list-table::
   :header-rows: 1

   * - 按键
     - 作用
   * - ``f`` / ``r``
     - resource1 矿点（如金矿）
   * - ``g`` / ``t``
     - resource2 矿点（如树林）
   * - ``y`` / ``h``
     - resource3 矿点（如果园）
   * - ``m`` / ``SHIFT m``
     - 草地
   * - ``p`` / ``SHIFT p``
     - 通道 / 桥梁
   * - ``F8`` 系列
     - 缩放



选矿后可用全局 ``BACKSPACE`` / ``RETURN`` 让农民开采；选草地后可建造；选通道后可移动或阻塞。

5.7 帮助与外交
~~~~~~~~~~~~~~


帮助（`help_bindings.txt <../../../res/ui/help_bindings.txt>`_）：``1``/``2`` 浏览帮助，``3`` 报时，``F7`` 发言，``CTRL SHIFT F3`` 切换 tick 显示。

外交（`diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_）：``1`` 选结盟候选，``q`` 请求，``w`` 接受，``e`` 拒绝或取消。

覆盖式界面内按 ``ESC`` 调用 ``exit_overlay_mode`` 返回先前模式。


----


6. 典型操作流程
---------------


开采资源
~~~~~~~~


1. 单位界面 ``s`` 选农民
2. ``F2`` 进入命令界面，``s`` 选开采命令（或 ``b`` + 字母快捷）
3. ``ESC`` 进入地图浏览
4. ``f`` 选金矿（听到金矿播报）
5. ``RETURN`` 确认，农民前往开采

若已选过金矿再离开地图：按 ``ESC`` 回地图时听方格概况，焦点仍在金矿，可直接 ``RETURN``。

建造建筑
~~~~~~~~


1. ``ESC`` 地图 → ``m`` 选草地
2. ``F2`` 命令界面选建造槽位
3. ``RETURN`` 确认

外交
~~~


1. ``F12`` 进入外交
2. `1` 选候选玩家
3. ``q`` 发送结盟请求

.. code-block:: text

   sequenceDiagram
       participant U as UnitMode
       participant C as CommandMode
       participant M as MapMode
       U->>U: s选农民
       U->>C: F2
       C->>C: s选命令1
       C->>M: ESC
       M->>M: f选金矿
       M->>C: RETURN确认



----


7. 自定义与 Mod 说明
--------------------


改哪个文件
~~~~~~~~~~


- 调整全局行为：改 ``global_bindings.txt``
- 调整某一界面：改对应的 `*_bindings.txt`
- 不要直接改 ``bindings.txt`` 正文（仅为 stub 说明）；除非知悉其作为 Mod 追加层的兼容行为

用户覆盖
~~~~~~~~


游戏内映射（推荐）： 主菜单 → 选项 → 按键映射。映射按当前加载的 mod 分别保存到 ``user/hotkey_overrides/{mod_key}.json`` （规则与存档一致），下次开始对局生效。详见 `开发者文档：按键映射编辑器 <../../mod/hotkey-mapping-editor.htm>`_。

注意事项
~~~~~~~~


- 命令槽位 ``select_order_index`` 依赖菜单排序，Mod 增删命令后序号会变
- 建筑槽位 ``buildingN`` 依赖 ``style.txt`` 中 ``keyboard buildingN`` 映射
- 单位界面 ``b`` （``order_shortcut``）依赖 style 里各 order 的 ``shortcut`` 字段


----


8. 切回经典单文件热键
---------------------


若更习惯 1.4.3 之前的整套键位（F4 直接外交请求、F12 切换结盟对象、ESC 不进入地图浏览层等），可在用户配置中关闭分层模式：

方式一（推荐）：主菜单 → 选项 → 热键方案，选择「分层热键」或「经典热键」。方案按当前加载的 mod 分别保存（与按键映射相同），下次开始对局生效。

方式二（手动编辑，仅无 mod 时的兼容回退）：

1. 打开 :strong:```user/SoundRTS.ini`` （Windows 上通常在 `%APPDATA%\SoundRTS\SoundRTS.ini`）。
2. 在 `````[general]``` 段加入或修改：

.. code-block:: ini

      layered_hotkeys = 0


3. 重启游戏（须在对局开始前生效）。

关闭后：

- 仅加载 `res/ui/legacy_bindings.txt <../../../res/ui/legacy_bindings.txt>`_，不再叠加 ``global_bindings.txt`` 与各界面层。
- 仍追加 Mod 的非 stub ``bindings.txt`` 与 ``user/bindings.txt`` （个人覆盖最后生效）。
- F1/F2/F3/F4/F12/ESC 的「界面切换」命令无效（会蜂鸣）；ESC 恢复为取消命令 / 退出子界面 / 退出沉浸或缩放，不会进入地图浏览层。
- 背包（``i``）、装备（``u``）、属性（Alt+V）等子界面热键仍按 ``legacy_bindings.txt`` 中的定义工作。

恢复分层模式：设 ``layered_hotkeys = 1`` （或删除该行，默认即为 1）并重启。


----


9. 与旧版差异 / 迁移提示
------------------------



.. list-table::
   :header-rows: 1

   * - 旧行为
     - 新行为
   * - F1 / F4 直接帮助
     - F4 进入帮助界面；F9/F11 已全局化
   * - F12 直接外交操作
     - F12 进入外交界面再操作
   * - 农民 ``d``/``e``
     - 单位界面 ``s``/``w``
   * - 士兵键位
     - 重新映射到 `d/e`…`;`/p`
   * - 地图 ``f`` 跳方格
     - ``f`` 在当前格内循环矿点
   * - ESC 回地图播报上次目标
     - ESC 回地图播报方格概况，焦点静默恢复



属性界面、编辑器热键不受影响。


----


相关源文件
----------


- `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_
- `res/ui/unit_bindings.txt <../../../res/ui/unit_bindings.txt>`_
- `res/ui/building_bindings.txt <../../../res/ui/building_bindings.txt>`_
- `res/ui/command_bindings.txt <../../../res/ui/command_bindings.txt>`_
- `res/ui/skill_bindings.txt <../../../res/ui/skill_bindings.txt>`_
- `res/ui/map_bindings.txt <../../../res/ui/map_bindings.txt>`_
- `res/ui/help_bindings.txt <../../../res/ui/help_bindings.txt>`_
- `res/ui/diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_
- `soundrts/clientgame/interface_modes.py <../../../soundrts/clientgame/interface_modes.py>`_
