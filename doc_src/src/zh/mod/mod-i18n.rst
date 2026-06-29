模组多语言说明
==============


语言设置
--------


在 ``cfg/language.txt`` 中写入语言代码（如 ``zh``、``fr``）。游戏会扫描已加载资源中的 ``ui-xx`` 文件夹并选择最佳匹配。

目录结构
--------


模组与 ``res`` 目录结构相同，常见布局：

.. code-block:: text

   mods/mymod/
     rules.txt
     mod.txt                 # 可选
     ui/style.txt
     ui/tts.txt
     ui-zh/tts.txt
     ui-fr/tts.txt
     single/                 # 可选：模组内战役
       my campaign/
         campaign.txt
         ui/tts.txt
         ui-zh/tts.txt


翻译游戏内文本
--------------


1. 在 ``ui/style.txt`` 为单位/建筑等设置 `title <数字ID>`。
2. 在 ``ui/tts.txt`` 写 ``7000 Pig Farm``。
3. 在 ``ui-zh/tts.txt`` 写 ``7000 猪圈`` （ID 必须一致）。

整句可用等号格式：``English phrase = 中文译文``。

tts.txt 编码（重要）
--------------------


请一律使用 UTF-8 保存。 未写 ``; coding:`` 时引擎默认按 UTF-8 读取；首行可加 ``; coding: utf-8`` （可选，便于部分编辑器识别）。

遗留 GBK 文件须在首行写 ``; coding: gbk``，否则解码会报错。

常见乱码原因：用 VS Code/Cursor 等以错误编码打开 ``tts.txt`` 后再保存，中文会变成 `` 并永久丢失。引擎加载时会检测 ``U+FFFD`` 并告警；解码失败时会报错而不是静默替换。

模组菜单显示名
--------------


选项 → 模组 列表默认朗读文件夹名。自 1.4.2.4 起可在 ``mod.txt`` 中设置：

.. code-block:: text

   title 7100


并在各语言 ``tts.txt`` 中定义 ``7100`` 的译文。机制与战役 ``campaign.txt`` 的 ``title`` 相同。

若不想改模组本身，可在 ``res/ui-zh/tts.txt`` 或翻译 mod 中添加：

.. code-block:: text

   文件夹名 = 中文显示名


限制
---


- ``rules.txt``、``ai.txt`` 只有一份，不按语言分文件。
- 地图/战役子目录中的 ``ui-xx/style.txt`` 可能不加载；``ui-xx/tts.txt`` 会加载。
- 音效包菜单仍使用文件夹名。

示例
---


- `mods/orc/`：七种语言的 ``ui-xx/tts.txt``
- `mods/prismalab/ui-fr/`：法语界面与快捷键

更多细节见 ``mod/modding.rst`` 中「模组多语言」一节。
