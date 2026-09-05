SoundRTS 游戏语音安装说明（类似迷雾世界 vl 语音库）
================================================

游戏旁白使用 Windows SAPI 系统语音 / Nuance 苹果音库。

一、安装系统语音
1. 安装任意 SAPI5 语音包（如 Microsoft Huihui、VocalWare VW Julie）。
2. 在 sapi.cpl 里能看到即可。
3. 注意：部分第三方音库（如 VW Julie）只注册了 32 位 SAPI。
   64 位游戏会通过内置的 tools/sapi32 助手调用它们，菜单里应能选到「朱莉」。

二、可选：语音包清单（友好中文名）
在本目录下新建子文件夹，例如 user/voices/juli/，放入 voice.ini：

[voice]
title = 朱莉
sapi = VW Julie
rate = 0

title：菜单显示名；sapi：须与系统语音名一致（或子串）。

三、苹果音库（Nuance）
选项 → 导入苹果音库到本游戏 → voices/nuance/
