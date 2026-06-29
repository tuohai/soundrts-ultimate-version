#!/usr/bin/env python3
"""Build skills-and-effects.rst from the three legacy markdown guides."""
from pathlib import Path

from md2rst import convert_md_to_rst, _underline

ROOT = Path(__file__).resolve().parents[2]

INTRO = """\
# 技能、治疗、伤害与效果系统

> 面向 **模组作者**：在 `rules.txt` 里配置主动技能、单位自带治疗/伤害光环、以及战场区域效果（`class effect`）。\
由浅入深，建议按章阅读。

---

## 阅读顺序

1. **主动技能**（`class skill`）— 玩家按键或自动触发的招式
2. **单位治疗/伤害**（`heal_*` / `harm_*`）— 牧师、毒云、生命/法力回复节奏
3. **战场效果**（`class effect`）— 火墙、光环、带 debuff 的范围攻击
4. **进阶** — 连击 burst、自动触发、范围参数对照表

官方关键字大全另见 `modding.htm`。
"""


def _strip_python_blocks(md: str) -> str:
    """Mod authors use rules.txt; drop Python examples from legacy effect doc."""
    out: list[str] = []
    skip = False
    for line in md.splitlines():
        if line.strip().startswith("```python"):
            skip = True
            continue
        if skip:
            if line.strip().startswith("```"):
                skip = False
            continue
        if line.strip().startswith("class ") and "Effect" in line:
            skip = True
            continue
        out.append(line)
    return "\n".join(out)


def main() -> None:
    parts = [INTRO]
    for name in (
        "GENERIC_SKILL_SYSTEM.md",
        "HEAL_HARM_自定义功能说明.md",
        "EFFECT_BUFF_SYSTEM_说明.md",
    ):
        path = ROOT / name
        if path.is_file():
            body = path.read_text(encoding="utf-8")
            if "EFFECT_BUFF" in name:
                body = _strip_python_blocks(body)
            lines = body.splitlines()
            if lines and lines[0].startswith("# "):
                lines = lines[1:]
            parts.append("\n".join(lines))

    merged = "\n".join(parts)
    rst = convert_md_to_rst(merged)
    # fix title underline length for Chinese title
    title = "技能、治疗、伤害与效果系统"
    rst = _underline(title, "=") + rst.split("\n", 2)[-1] if title not in rst[:40] else rst

    out = ROOT / "doc_src" / "src" / "zh" / "mod" / "skills-and-effects.rst"
    out.write_text(rst, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
