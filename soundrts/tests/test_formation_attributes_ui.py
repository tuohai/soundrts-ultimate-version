"""属性界面：当前阵型、可用阵型左右导航、回车查看形状与效果。"""
from pathlib import Path
from types import SimpleNamespace

from soundrts import msgparts as mp
from soundrts.attributes.formation_detail import (
    add_formation_attributes,
    build_formation_detail_attrs,
    format_formation_bonus,
)
from soundrts.attributes.utils import NAVIGABLE_ITEM_TYPES
from soundrts.lib.nofloat import PRECISION

ROOT = Path(__file__).resolve().parents[2]


def _tts_map(rel):
    ids = {}
    for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            ids[int(parts[0])] = parts[1]
    return ids


def _labels(attrs):
    return [name for _key, name, _value in attrs]


def _value(attrs, label):
    for _key, name, value in attrs:
        if name == label:
            return value
    raise AssertionError("missing %r" % (label,))


def test_navigable_types_include_formations():
    assert "AVAILABLE_FORMATIONS_ITEMS" in NAVIGABLE_ITEM_TYPES


def test_format_formation_bonus_percent_and_absolute():
    assert format_formation_bonus(("pct", 20)) == ["+20%"]
    assert format_formation_bonus(("pct", -30)) == ["-30%"]
    spoken = "".join(str(p) for p in format_formation_bonus(2 * PRECISION))
    assert "2" in spoken
    assert format_formation_bonus(0) is None


def test_add_formation_attributes_lists_types(monkeypatch):
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formations_enabled", lambda: True
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.unit_can_form", lambda _u: True
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formation_type_names",
        lambda: ["formation_line", "formation_box"],
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.unit_formation_name",
        lambda _u: "formation_line",
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.unit_formation_rank",
        lambda _u: "melee",
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.style.get",
        lambda name, _key: {
            "formation_line": "line formation",
            "formation_box": "box formation",
        }.get(name),
    )
    attrs = []
    add_formation_attributes(SimpleNamespace(), attrs)
    assert mp.CURRENT_FORMATION in _labels(attrs)
    assert mp.AVAILABLE_FORMATIONS in _labels(attrs)
    assert mp.FORMATION_RANK in _labels(attrs)
    assert _value(attrs, mp.CURRENT_FORMATION) == ["line formation"]
    kind, items = _value(attrs, mp.AVAILABLE_FORMATIONS)
    assert kind == "AVAILABLE_FORMATIONS_ITEMS"
    assert items == [["line formation"], ["box formation"]]
    assert _value(attrs, mp.FORMATION_RANK) == list(mp.FORMATION_RANK_MELEE)


def test_add_formation_attributes_hidden_when_off(monkeypatch):
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formations_enabled", lambda: False
    )
    attrs = []
    add_formation_attributes(SimpleNamespace(), attrs)
    assert attrs == []


def test_add_formation_attributes_hidden_when_unit_cannot_form(monkeypatch):
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formations_enabled", lambda: True
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.unit_can_form", lambda _u: False
    )
    attrs = []
    add_formation_attributes(SimpleNamespace(), attrs)
    assert attrs == []


def test_circle_detail_shows_shape_and_percent_effects(monkeypatch):
    spec = {
        "name": "formation_circle",
        "shape": "circle",
        "spacing": 1500,
        "rank_gap": 1800,
        "flank_gap": 0,
        "max_front": 0,
        "ranks": ("melee", "ranged"),
        "keep_pace": True,
        "radius": 4000,
        "rings": 0,
        "ring_gap": 0,
        "arc_span": 0,
        "arc_start": None,
        "ring_rank": "in",
        "mdg": ("pct", 20),
        "rdg": 0,
        "mdf": 0,
        "rdf": 0,
        "mdg_vs": {"cavalry": ("pct", 50)},
        "rdg_vs": {},
        "mdf_vs": {},
        "rdf_vs": {},
        "speed": ("pct", -30),
    }
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formation_spec", lambda _n: spec
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.style.get",
        lambda name, key: {
            ("formation_circle", "title"): "circle",
            ("cavalry", "title"): "cavalry",
        }.get((name, key)),
    )
    attrs = build_formation_detail_attrs("formation_circle")
    labels = _labels(attrs)
    assert mp.FORMATION_SHAPE in labels
    assert _value(attrs, mp.FORMATION_SHAPE) == list(mp.FORMATION_SHAPE_RING)
    assert mp.FORMATION_RADIUS in labels
    assert mp.MELEE_DAMAGE in labels
    assert _value(attrs, mp.MELEE_DAMAGE) == ["+20%"]
    assert _value(attrs, mp.SPEED) == ["-30%"]
    assert mp.MDG_VS in labels
    vs = "".join(str(p) for p in _value(attrs, mp.MDG_VS))
    assert "50%" in vs or "+50%" in vs
    assert mp.FORMATION_KEEP_PACE in labels
    assert _value(attrs, mp.FORMATION_KEEP_PACE) == list(mp.YES)


def test_line_detail_shows_cartesian_shape_and_spacing(monkeypatch):
    spec = {
        "name": "formation_line",
        "shape": "line",
        "spacing": 1500,
        "rank_gap": 1800,
        "flank_gap": 0,
        "max_front": 0,
        "ranks": ("melee", "ranged"),
        "keep_pace": True,
        "radius": 0,
        "rings": 0,
        "ring_gap": 0,
        "arc_span": 0,
        "arc_start": None,
        "ring_rank": "in",
        "mdg": 0,
        "rdg": 0,
        "mdf": 0,
        "rdf": 0,
        "mdg_vs": {},
        "rdg_vs": {},
        "mdf_vs": {},
        "rdf_vs": {},
        "speed": 0,
    }
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.formation_spec", lambda _n: spec
    )
    monkeypatch.setattr(
        "soundrts.attributes.formation_detail.style.get",
        lambda name, _key: "line formation" if name == "formation_line" else None,
    )
    attrs = build_formation_detail_attrs("formation_line")
    labels = _labels(attrs)
    assert _value(attrs, mp.FORMATION_SHAPE) == [5845]
    assert mp.FORMATION_SPACING in labels
    assert mp.FORMATION_RANK_GAP in labels
    assert _value(attrs, mp.FORMATION_KEEP_PACE) == list(mp.YES)
    assert mp.FORMATION_RADIUS not in labels
    assert mp.FORMATION_RINGS not in labels
    assert mp.FORMATION_ARC_SPAN not in labels
    assert mp.MELEE_DAMAGE not in labels


def test_tts_wires_formation_attribute_ids():
    en = _tts_map("res/ui/tts.txt")
    zh = _tts_map("res/ui-zh/tts.txt")
    assert en[5850] == "available formations"
    assert zh[5850] == "可用阵型"
    assert en[5851] == "formation rank"
    assert zh[5867] == "圆环"
    assert en[5868] == "arc"
    for tid in range(5850, 5869):
        assert tid in en and en[tid].strip(), tid
        assert tid in zh and zh[tid].strip(), tid
    for lang_dir in (
        "ui-es",
        "ui-it",
        "ui-pt-BR",
        "ui-fr",
        "ui-de",
        "ui-ru",
        "ui-pl",
        "ui-cs",
        "ui-sk",
        "ui-vi",
    ):
        ids = _tts_map(f"res/{lang_dir}/tts.txt")
        if 5849 not in ids:
            continue
        for tid in range(5850, 5869):
            assert tid in ids and ids[tid].strip(), (lang_dir, tid)
