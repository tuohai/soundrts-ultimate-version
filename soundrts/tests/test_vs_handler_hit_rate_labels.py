"""属性界面的 ``*_vs`` 标签必须说明“加的是什么”，不能一律当成伤害加成。

回归用例：巨型投石机（trebuchet）的 ``rdg_hit_rate_vs building 65`` 在属性
界面里曾被念成“远程伤害加成 对抗 建筑 65”——把命中率错说成伤害。
正确说法应为“远程命中加成 对抗 建筑 65”。
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.vs_handler import VsHandler

ROOT = Path(__file__).resolve().parents[2]


class _Parent:
    pass


def _read_tts(path):
    table = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        table[parts[0]] = parts[1]
    return table


def _speak(parts, table):
    out = []
    for p in parts:
        if isinstance(p, int):
            out.append(table.get(str(p), str(p)))
        else:
            text = str(p)
            # At runtime a numeric string is a TTS key too (e.g. style title "4812").
            out.append(table.get(text, text) if text.isdigit() else text)
    return "".join(out)


def _vs_label(attr_name, value=65):
    """Render one *_vs row the way the attributes screen does."""
    attrs = []
    VsHandler(_Parent())._add_vs_attribute(
        attrs, {"building": value}, attr_name, precision_divide=True
    )
    assert attrs, attr_name
    _, name, val = attrs[0]
    if isinstance(val, tuple):
        val = val[1][0]
    return name, val


def test_hit_rate_vs_is_not_labelled_as_damage_bonus():
    """rdg_hit_rate must not fall back to the ranged *damage* label."""
    name, _ = _vs_label("rdg_hit_rate")
    assert name == list(mp.RDG_COVER_VS)
    assert name != list(mp.RDG_VS)

    name, _ = _vs_label("mdg_hit_rate")
    assert name == list(mp.MDG_COVER_VS)
    assert name != list(mp.MDG_VS)


def test_dodge_rate_vs_is_not_labelled_as_damage_bonus():
    name, _ = _vs_label("rdg_dodge_rate")
    assert name == list(mp.RDG_DODGE_VS)
    assert name != list(mp.RDG_VS)


def test_plain_damage_vs_labels_unchanged():
    """Plain damage/defence bonuses keep their original labels."""
    assert _vs_label("rdg")[0] == list(mp.RDG_VS)
    assert _vs_label("mdg")[0] == list(mp.MDG_VS)
    assert _vs_label("mdf")[0] == list(mp.MDF_VS)
    assert _vs_label("rdf")[0] == list(mp.RDF_VS)


def test_bonus_hit_rate_keeps_bonus_word():
    name, _ = _vs_label("rdg_hit_rate_bonus")
    assert name[: len(mp.RDG_COVER_VS)] == list(mp.RDG_COVER_VS)
    assert mp.BONUS[0] in name


def test_chinese_trebuchet_hit_rate_vs_reads_as_hit_not_damage():
    """The Chinese attributes screen must say 远程命中…, not 远程伤害…."""
    zh = _read_tts(ROOT / "res" / "ui-zh" / "tts.txt")
    name, value = _vs_label("rdg_hit_rate")
    spoken = _speak(name, zh) + " " + _speak(value, zh)
    assert "远程命中" in spoken
    assert "远程伤害" not in spoken
    assert "建筑" in spoken
