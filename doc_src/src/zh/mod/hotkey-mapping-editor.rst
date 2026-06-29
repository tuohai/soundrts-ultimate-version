按键映射编辑器（Hotkey Mapping Editor）
=======================================



玩家向说明（分层/经典热键总览）：`../player/分层热键方案说明.md <../player/分层热键方案说明.htm>`_

英文版：`../../en/mod/hotkey-mapping-editor.md <../../en/mod/hotkey-mapping-editor.htm>`_

主菜单 选项 → 按键映射 内的可视化（语音）热键编辑功能。Phase 1–5 已全部完成；本文供维护者了解架构与数据格式。

相关源码：``soundrts/hotkey_editor.py``、``soundrts/hotkey_catalogs.py``、``soundrts/hotkey_remapping_menu.py``、``soundrts/clientgame/interface_modes.py``。


----


1. 当前进度
-----------



.. list-table::
   :header-rows: 1

   * - 阶段
     - 状态
     - 内容
   * - Phase 1
     - ✅ 已完成
     - 解析器、``hotkey_overrides.json`` 存储、加载合并、全局层映射 UI
   * - Phase 2
     - ✅ 已完成
     - 单位/建筑/命令/技能/第一人称/帮助/地图/外交各界面层 catalog、加载挂钩、分层子菜单
   * - Phase 3
     - ✅ 已完成
     - 经典单文件方案（``legacy_bindings.txt`` / ``classic`` 层）映射 UI 与加载
   * - Phase 4
     - ✅ 已完成
     - 长列表搜索、高级变体子菜单、导入/导出（剪贴板）
   * - Phase 5
     - ✅ 已完成
     - 别名键独立映射（LCTRL/RCTRL、RETURN/KP_ENTER 等）



玩家可见行为（汇总）
~~~~~~~~~~~~~~~~~~~~


- 入口：选项 → 按键映射（与「热键方案」同级）
- 分层热键：再选界面层（全局 / 单位 / 建筑 / 命令 / 技能 / 第一人称 / 帮助 / 地图 / 外交）
- 经典热键：进入「按键映射」后直接列出全部经典绑定（无额外「经典热键」子层）；内含 第一人称界面 子菜单
- 每层列表顶部：搜索热键、高级变体（若有）、别名键（若有）；进入时提示可输入首字母跳转
- 映射入口顶部：导出热键配置 / 导入热键配置（剪贴板，合并或替换）
- 每项：功能名，当前热键 xxx，回车修改；Esc 取消；Backspace 清除自定义
- 键冲突：播报占用者，回车确认替换
- 按 当前 mod 读写 `user/hotkey_overrides/{mod_key}.json`；下次开始对局生效


----


2. 设计动机：为何不用纯 ``bindings.txt`` 追加
---------------------------------------------


旧机制：``cfg/bindings.txt`` 是 按键 → 命令 的追加覆盖，后加载覆盖同键。

问题：若把「资源 1」从 ``z`` 改到 ``y``，只追加 ``y: resource_status resource1`` 时，``旧的 ``z`` 仍有效`，同一功能会有两个键。

新机制：以 功能 ID（binding_id） 为中心存储用户修改，加载时：

1. 移除该功能在默认文件中的主绑定键行
2. 写入新键行
3. 若新键与其他功能冲突，按 UI 确认后挤占（被挤占者失去该键，除非另有覆盖）

仍保留 ``cfg/bindings.txt`` 作为高级用户手写入口；映射 UI 按 当前 mod 读写 ``user/hotkey_overrides/{mod_key}.json``。


----


3. 文件与职责
-------------



.. list-table::
   :header-rows: 1

   * - 路径
     - 职责
   * - ``soundrts/hotkey_catalogs.py``
     - 各层 ``get_layer_catalog``、``keyboard_slot_label`` （通用 keyboard 槽位名）
   * - ``soundrts/hotkey_editor.py``
     - 解析、binding_id、JSON、``apply_overrides_to_bindings_text``、键捕获
   * - ``soundrts/hotkey_remapping_menu.py``
     - 菜单 UI：各界面层子菜单
   * - ``soundrts/clientmain.py``
     - ``options_menu`` 含「按键映射」
   * - ``soundrts/clientgame/interface_modes.py``
     - `_bindings_layer_with_overrides()`，合并前按层应用覆盖
   * - ``soundrts/lib/bindings.py``
     - 运行时按键解析（未改）
   * - ``soundrts/msgparts.py``
     - TTS 常量：菜单 5280–5399；catalog/键名 5500–5684
   * - ``res/ui/tts.txt``、``res/ui-zh/tts.txt``
     - 中英文语音文案
   * - ``user/hotkey_overrides/{mod_key}.json``
     - 各 mod 专属用户映射（与存档同规则：`current_mod_key()`）
   * - ``user/hotkey_overrides.json``
     - 旧版单文件（首次打开无 mod 映射时自动迁入 ``\_base.json``）
   * - ``cfg/bindings.txt``
     - 旧式手写覆盖（加载顺序在 JSON 之后）



测试：``soundrts/tests/test_hotkey_editor.py``、``test_hotkey_editor_phase2.py`` … ``test_hotkey_editor_phase5.py``、``test_hotkey_catalog_tts.py``


----


4. 数据模型
-----------


4.1 binding_id
~~~~~~~~~~~~~~~


规则：``{层}.{命令名}.{参数...}``，参数用 ``.`` 连接。

.. code-block:: text

   global.resource_status.resource1     ← z: resource_status resource1
   global.select_square.0.1           ← UP: select_square 0 1
   global.volume.-1                   ← END: volume -1
   unit.select_units.local.worker     ← （Phase 2）s: select_units local worker


生成函数：``hotkey_editor.make_binding_id(layer, command_name, args)``  
解析函数：``hotkey_editor.parse_bindings_text(text, layer)`` （展开 ``#define`` 宏）

4.2 按 mod 存储（`hotkey_overrides/{mod_key}.json`）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: json

   {
     "version": 1,
     "layered_hotkeys": 1,
     "overrides": {
       "global": {
         "global.resource_status.resource1": "y"
       },
       "unit": {
         "unit.select_units.local.worker": "d"
       }
     }
   }


- mod 标识与存档相同：无 mod → ``\_base.json``；单 mod → ``starcraft.json``；多 mod → `a+b.json`
- 各 mod 完全独立：热键方案（``layered_hotkeys``：`1` 分层 / `0` 经典）与按键映射均存于同一 JSON
- 进入「热键方案」「按键映射」均播报「当前模组热键配置，…」
- 无 mod 且 JSON 未写 ``layered_hotkeys`` 时，回退 ``user/SoundRTS.ini`` 的 ```[general] layered_hotkeys```` （兼容旧配置）
- 其它 mod 未写 ``layered_hotkeys`` 时默认分层（`1`）
- 旧版 ``user/hotkey_overrides.json`` 首次打开无 mod 配置时迁入 ``\_base.json``

4.3 主绑定目录（Catalog）
~~~~~~~~~~~~~~~~~~~~~~~~~


``GLOBAL_PRIMARY_CATALOG``：``List[Tuple[binding_id, label_msgs]]``

- 主 catalog 每项一个 binding_id（主键）；别名键见 Phase 5；Shift/Ctrl 修饰变体见 Phase 4「高级变体」


----


5. 加载流水线
-------------


.. code-block:: text

   flowchart TD
       A[global_bindings.txt] --> B[apply_overrides_to_bindings_text global]
       B --> C[合并 mode_bindings.txt]
       C --> D[mod bindings 追加]
       D --> E[cfg/bindings.txt 追加]
       E --> F[Bindings.load → 对局内生效]


``interface_modes.get_bindings_text(mode)`` 伪代码：

.. code-block:: python

   parts = [_global_bindings_with_overrides()]  # 非直接读 global txt
   if mode:
       parts.append(_read_bindings_layer(MODE_FILES[mode]))
   # + mod + custom suffix


经典方案通过 ``\_legacy_bindings_with_overrides()`` 对 ``classic`` 层应用 JSON 覆盖（Phase 3）。

``apply_overrides_to_bindings_text(text, layer)`` 逻辑摘要：

1. ``parse_bindings_text`` 得到全部行
2. 建立 `binding_id → command_string`
3. 删除：被覆盖的主键或别名键默认行；以及「新键已被占用且自身无 override」的行
4. 追加 override 的新键行（含 `{binding_id}@{别名默认键}` 格式）


----


6. 菜单与改键 UI
----------------


.. code-block:: text

   options_menu
     ├── 热键方案
     ├── 按键映射                    # 导出/导入 + 各层子菜单
     │     ├── [分层] 全局 / 单位 / 建筑 / …
     │     │     ├── 搜索热键
     │     │     ├── 高级变体（若有）
     │     │     ├── 别名键（若有）
     │     │     ├── [主 catalog 项…]
     │     │     ├── 恢复本层默认
     │     │     └── 返回
     │     └── [经典] 经典热键（同上结构）
     └── …


改键流程：``\_remap_binding`` / ``\_remap_alias_binding`` → ``capture_binding_key()`` → ``set_layer_override()`` 或 ``set_layer_alias_override()``。


----


7. TTS 消息 ID
--------------


7.1 菜单框架（5280–5399）
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - ID
     - 中文
     - 常量
   * - 5280
     - 按键映射
     - `mp.HOTKEY_MAPPING`
   * - 5281
     - 全局热键
     - `mp.GLOBAL_HOTKEYS_LAYER`
   * - 5282
     - 当前热键
     - `mp.HOTKEY_CURRENT_KEY`
   * - …
     - …
     - 见 ``msgparts.py`` 热键区块
   * - 5397
     - 当前模组热键配置，
     - `mp.HOTKEY_OVERRIDES_FOR_MOD`
   * - 5398
     - 无模组
     - `mp.HOTKEY_MOD_NONE`
   * - 5399
     - 已恢复经典热键默认
     - `mp.HOTKEY_CLASSIC_RESET`



7.2 Catalog 与 Phase 4/5 文案（5500–5684）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- 5500–5670：各层 catalog 功能名、物理键名、classic 高级变体标签等
- 5671–5684：搜索、导入导出、别名键等 Phase 4/5 菜单文案
- 带序号的项（士兵3、命令5、技能2）使用 ``HOTKEY_SLOT_SOLDIER`` / ``HOTKEY_ORDER_LABEL`` / ``HOTKEY_SKILL_LABEL`` + `nb2msg(n)`
- 定义位置：`soundrts/msgparts.py <soundrts/msgparts.py>`_；译文：`res/ui/tts.txt <res/ui/tts.txt>`_ （英）、`res/ui-zh/tts.txt <res/ui-zh/tts.txt>`_ （中）
- 覆盖测试：`soundrts/tests/test_hotkey_catalog_tts.py <soundrts/tests/test_hotkey_catalog_tts.py>`_

classic 层 catalog 构成（``hotkey_catalogs._build_classic_catalog()``）：

1. 基础项（移动、资源、编组、外交等）
2. `_classic_supplement_catalog()` — 第一批补项（objectives.-1、cheat、zoom、music volume 等）
3. `_classic_advanced_catalog()` — 第二批高级变体（12 项五格/无视碰撞移动 + 34 项单位切换/空闲/全图变体）

``test_classic_catalog_covers_all_legacy_primary_bindings`` 断言 catalog 与 ``legacy_bindings.txt`` 解析出的全部 ``binding_id`` 一一对应（missing = 0）。

新增 UI 文案请延续未占用 ID，并同步 ``tts.txt`` / ``ui-zh/tts.txt``。不得在 catalog 中直接写自然语言字符串。


----


8. Phase 4 功能（已完成）
-------------------------


8.1 搜索与首字母跳转
~~~~~~~~~~~~~~~~~~~~


- 各层热键列表首项 搜索热键：输入关键词（支持中英文），匹配 catalog 标签或 binding_id
- 进入任一层列表时会播报 输入首字母可快速跳转（沿用 ``Menu`` 内置首字母循环）

8.2 高级变体子菜单
~~~~~~~~~~~~~~~~~~


- 当 bindings 文件中存在不在主 catalog 的 binding（如 `Shift+回车 排队确认`、五格移动、反向切换等），层菜单显示 高级变体 入口
- classic 层已全部纳入主 catalog，通常无此项；global / unit / building 等层有变体
- 变体标签由 `variant_label_for_binding_id()` 自动生成（复用 msgparts 片段）

8.3 导入 / 导出
~~~~~~~~~~~~~~~


- 按键映射入口顶部：导出热键配置 → JSON 写入剪贴板
- 导入热键配置 → 子菜单选 合并导入 或 替换导入，粘贴 JSON（支持 Ctrl+V）
- 作用于当前 mod 的 `user/hotkey_overrides/{mod_key}.json`

8.4 Phase 5：别名键（已完成）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


同一 ``binding_id`` 在 bindings 文件中可有多个等效按键（如 ``LCTRL`` / ``RCTRL`` 查看、``RETURN`` / ``KP_ENTER`` 确认）。主 catalog 只显示主键；层菜单 别名键 列出其余默认按键，可单独改映射。

- 存储格式：`{binding_id}@{默认别名键}`，空格写作 `+`（例：`global.examine@RCTRL`、`global.validate.imperative@CTRL+KP_ENTER`）
- 主键与别名互不影响：改主键不会自动改别名，反之亦然
- 导出/导入 JSON 时别名 override 与主 override 一并读写


----


9. 与分层热键系统的关系
-----------------------



.. list-table::
   :header-rows: 1

   * - 概念
     - 文档 / 代码
   * - 分层加载顺序
     - [../player/分层热键方案说明.md](../player/分层热键方案说明.htm)
   * - ``layered_hotkeys`` 配置
     - 按 mod 存于 `hotkey_overrides/{mod_key}.json`；`interface_modes.layered_hotkeys_enabled()` → `hotkey_editor.get_layered_hotkeys_scheme()`；无 mod 未写入时回退 ``config.py`` / ini
   * - 模式文件表
     - `interface_modes.MODE_FILES`
   * - 运行时切换界面
     - `apply_active_mode_bindings()`



映射编辑器不修改 ``res/ui/*_bindings.txt`` 默认文件，只写用户 JSON。


----


10. 常见问题（维护）
--------------------


Q：改了键进游戏没生效？  
A：需新开一局；映射在 ``init_interface_modes`` → ``get_bindings_text`` 路径加载。

``Q：与手写 ``bindings.txt`` 冲突？``  
A：``bindings.txt`` 在合并链最后追加，同键会覆盖 JSON 生成的行；建议 UI 用户只用 JSON。

Q：RETURN 与 KP_ENTER 双绑定？  
A：主 catalog 只显示 RETURN；KP_ENTER 等在 别名键 子菜单中可单独改映射（Phase 5）。未改时两者均按默认 bindings 生效。

Q：Azerty 反引号键？  
A：运行时 ``Bindings`` 与 ``key_event_to_binding_string`` 均支持 BACKQUOTE/QUOTE scancode；若某布局捕获异常请提 issue。


----


11. 相关测试命令
----------------


.. code-block:: bash

   pytest soundrts/tests/test_hotkey_editor.py -q
   pytest soundrts/tests/test_hotkey_editor_phase2.py -q
   pytest soundrts/tests/test_hotkey_editor_phase3.py -q
   pytest soundrts/tests/test_hotkey_editor_phase4.py -q
   pytest soundrts/tests/test_hotkey_editor_phase5.py -q
   pytest soundrts/tests/test_hotkey_catalog_tts.py -q
   pytest soundrts/tests/test_layered_bindings.py -q


关键用例：各层 catalog、classic 全覆盖、搜索/变体/别名 override、``apply_overrides`` 主键与别名独立、导入导出、mod 隔离。
