#!/usr/bin/env python3
"""Find minimum underline length docutils accepts for a title."""
import io
from docutils.core import publish_string


def min_ul(title: str, char: str = "-") -> int:
    for n in range(len(title), len(title) + 30):
        err = io.StringIO()
        publish_string(
            f"{title}\n{char * n}\n\nbody\n",
            writer_name="html",
            settings_overrides={"warning_stream": err, "report_level": 2},
        )
        if "Title underline too short" not in err.getvalue():
            return n
    return len(title) + 30


samples = [
    "1. 目标",
    "2. 触发器条件 `has_item`",
    "成就系统（Achievement System）",
    "4.2 按 mod 存储（`hotkey_overrides/{mod_key}.json`）",
    "指定序号目标（killed_target / npc_has_item / unit_lost / building_lost / key_unit_killed）",
]
for s in samples:
    print(len(s), min_ul(s), repr(s[:50]))
