技能、治疗、伤害与效果系统
==========================



面向 模组作者：在 ``rules.txt`` 里配置主动技能、单位自带治疗/伤害光环、以及战场区域效果（``class effect``）。由浅入深，建议按章阅读。


----


阅读顺序
--------


1. 主动技能（``class skill``）— 玩家按键或自动触发的招式
2. 单位治疗/伤害（`heal_*` / `harm_*`）— 牧师、毒云、生命/法力回复节奏
3. 战场效果（``class effect``）— 火墙、光环、带 debuff 的范围攻击
4. 进阶 — 连击 burst、自动触发、范围参数对照表

官方关键字大全另见 ``mod/modding.htm``。


本文档已迁入 :strong:```doc_src/src/zh/skills-and-effects.rst``，与「治疗/伤害自定义」「Effect buff 系统」合并为一篇模组作者指南。

- 编辑源文件：``doc_src/src/zh/skills-and-effects.rst`` （或由根目录三份 ``.md`` 运行 `python doc_src/tools/build_skills_doc.py` 重新生成）
- 阅读 HTML：运行 `python builddoc.py` 后打开 ``doc/zh/skills-and-effects.htm``

已并入 :strong:```doc_src/src/zh/skills-and-effects.rst`` （第二节：单位治疗/伤害）。

- 源文件：``doc_src/src/zh/skills-and-effects.rst``
- HTML：`python builddoc.py` → ``doc/zh/skills-and-effects.htm``

已并入 :strong:```doc_src/src/zh/skills-and-effects.rst`` （第三节：战场 ``class effect``）。

面向 模组作者：在 ``rules.txt`` 中用 ``class effect`` 配置，无需 Python 源码。

- 源文件：``doc_src/src/zh/skills-and-effects.rst``
- HTML：`python builddoc.py` → ``doc/zh/skills-and-effects.htm``
