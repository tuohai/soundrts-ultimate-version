#!/usr/bin/env python3
"""Fix links and common RST issues in doc_src after MD migration."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "doc_src" / "src"

REPLACEMENTS = [
    (r"docs/zh/player/", "guides/player/"),
    (r"docs/zh/developer/", "guides/mod/"),
    (r"docs/en/player/", "guides/player/"),
    (r"docs/en/developer/", "guides/mod/"),
    (r"\.\./\.\./en/player/", "../../en/guides/player/"),
    (r"\.\./\.\./zh/player/", "../../zh/guides/player/"),
    (r"\.\./player/", "../player/"),
    (r"\]\(([^)]*?)\.md\)", r"](\1.htm)"),
    (r"``([^`]*?)\.md``", r"``\1.htm``"),
    (r"`([^`]*?)\.md`", r"`\1.htm`"),
]

MAPMAKING_DOC_LINKS = [
    ("docs/en/hunting-system.md", "guides/player/hunting-system.htm"),
    ("docs/en/map-unit-index-selectors.md", "guides/mod/map-unit-index-selectors.htm"),
    ("docs/en/campaign-secret-letter-alliance.md", "guides/player/campaign-secret-letter-alliance.htm"),
    ("docs/en/developer/coop-campaign.md", "guides/mod/coop-campaign.htm"),
    ("docs/en/player/campaign-and-co-op-improvements.md", "guides/player/campaign-and-co-op-improvements.htm"),
    ("docs/en/progressive-campaign-objectives.md", "guides/mod/progressive-campaign-objectives.htm"),
    ("docs/zh/狩猎系统说明.md", "guides/player/狩猎系统说明.htm"),
    ("docs/zh/指定序号目标说明.md", "guides/mod/指定序号目标说明.htm"),
    ("docs/zh/战役密信与结盟说明.md", "guides/player/战役密信与结盟说明.htm"),
    ("docs/zh/developer/coop-campaign.md", "guides/mod/coop-campaign.htm"),
    ("docs/zh/player/战役与合作战役改进说明.md", "guides/player/战役与合作战役改进说明.htm"),
    ("docs/zh/渐进式战役目标说明.md", "guides/mod/渐进式战役目标说明.htm"),
    ("docs/zh/狩猎系统说明.md", "guides/player/狩猎系统说明.htm"),
]


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    for pat, repl in REPLACEMENTS:
        text = re.sub(pat, repl, text)
    for old, new in MAPMAKING_DOC_LINKS:
        text = text.replace(old, new)
    # modding/manual legacy paths
    text = text.replace("../../../doc_src/src/zh/", "")
    text = text.replace("../../../doc_src/src/en/", "")
    text = re.sub(r"\[modding\.rst\]", "`modding.htm`", text)
    text = re.sub(r"\[mapmaking\.rst\]", "`mapmaking.htm`", text)
    text = re.sub(r"\[aimaking\.rst\]", "`aimaking.htm`", text)
    text = re.sub(r"\[randommap\.rst\]", "`randommap.htm`", text)
    text = re.sub(r"\[relnotes\.rst\]", "`relnotes.htm`", text)
    text = re.sub(r"\[manual\.rst\]", "`manual.htm`", text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def fix_randommap_player_zh(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    old = """7. 相关文件
-------


+----+----+
| 内容 | 路径 |
+:---+:---+
| 游戏内文档 | `doc/zh/randommap.htm`（主菜单 → 文档 → 随机地图指南） |
| 生成器 | `soundrts/randommap.py` |
| 菜单 | `soundrts/randommap_menu.py` |
| 测试 | `soundrts/tests/test_randommap.py` |
| 英文说明 | [../../en/player/random-map.md](../../en/player/random-map.md) |
| HoMM / Civ5 玩法详解 | [英雄无敌与文明5玩法说明.md](英雄无敌与文明5玩法说明.md) |
+:---+:---+"""
    new = """7. 相关文档
-------------

- `随机地图手册 <../../randommap.htm>`_（权威参数说明）
- `英文说明 <../../en/guides/player/random-map.htm>`_
- `HoMM / Civ5 式玩法 <英雄无敌与文明5玩法说明.htm>`_"""
    if old in text:
        path.write_text(text.replace(old, new), encoding="utf-8")


def fix_randommap_player_en(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    old = """+----+----+
| Item | Path |
+:---+:---+
| In-game doc | `doc/en/randommap.htm` |
| Generator | `soundrts/randommap.py` |
| Menus | `soundrts/randommap_menu.py` |
| Tests | `soundrts/tests/test_randommap.py` |
| Chinese guide | [../../zh/player/随机地图功能说明.md](../../zh/player/随机地图功能说明.md) |
+:---+:---+"""
    new = """- `Random map manual <../../randommap.htm>`_
- `Chinese guide <../../zh/guides/player/随机地图功能说明.htm>`_"""
    if "+:---+:---+" in text and "soundrts/randommap.py" in text:
        text = re.sub(
            r"\| Item \| Path \|.*?\+:---+:---\+",
            new.replace("\n", "\n"),
            text,
            count=1,
            flags=re.DOTALL,
        )
        path.write_text(text, encoding="utf-8")


def trim_mod_intro(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    # Remove source-code chapter and pytest learning path tail
    start = text.find("第七层：阅读源码")
    if start == -1:
        start = text.find("Level 7 — Source code")
    if start != -1:
        end_marker = "推荐学习路径"
        end = text.find(end_marker, start)
        if end != -1:
            text = text[:start] + text[end:]
    text = text.replace("实现入口：``soundrts/clientgame/interface_modes.py``\n\n", "")
    text = text.replace("Implementation: ``soundrts/clientgame/interface_modes.py``\n\n", "")
    text = text.replace("       E --> F[源码 + pytest]", "       E --> F[参考示例 mod]")
    text = text.replace("4. **引擎贡献者**：第七层 + 相关 `test_*.py`", "")
    text = text.replace("4. **Engine contributors**: Level 7 + `test_*.py`", "")
    text = text.replace("开发者 / 模组作者入门指南", "模组作者入门指南")
    text = text.replace("Developer / mod author guide", "Mod author guide")
    text = text.replace("开发者文档索引", "模组作者专题索引")
    text = text.replace("Developer doc index", "Mod author topic index")
    text = text.replace("返回开发者索引", "返回模组作者指南")
    text = text.replace("← Back to developer index", "← Back to mod author guide")
    text = text.replace("`开发者文档索引 <README.htm>`_", "`模组作者指南 <../../mod-author-guide.htm>`_")
    text = text.replace("``← 返回开发者索引 <README.htm>``_", "← 返回 `模组作者指南 <../../mod-author-guide.htm>`_")
    text = text.replace("| 系统 | 开发者文档 | 玩家简述 |", "| 系统 | 模组作者专题 | 玩家简述 |")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    n = 0
    for rst in SRC.rglob("*.rst"):
        if fix_file(rst):
            n += 1
    fix_randommap_player_zh(SRC / "zh/guides/player/随机地图功能说明.rst")
    fix_randommap_player_en(SRC / "en/guides/player/random-map.rst")
    trim_mod_intro(SRC / "zh/guides/mod/入门指南.rst")
    trim_mod_intro(SRC / "en/guides/mod/getting-started.rst")
    print(f"updated {n} rst files")
