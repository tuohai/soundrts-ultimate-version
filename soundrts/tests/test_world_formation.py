"""Rule-driven AoE2 DE spatial formations."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from soundrts.world_formation import (
    FormationRules,
    _bind_formation_slots,
    _layout_kind,
    _point_blocks_segment,
    after_group_order,
    apply_idle_rearrange,
    apply_slots_to_go_orders,
    assign_formation_slots,
    break_formation_hold,
    compute_slot_offsets,
    cycle_next_formation,
    formation_blocker,
    formation_hold_xy,
    formation_stand_ground,
    offsets_for_units,
    unit_can_form,
    unit_formation_rank,
)
from soundrts.worldorders import ORDERS_DICT
from soundrts.worldorders.immediate import CycleFormationOrder, SetFormationOrder


ROOT = Path(__file__).resolve().parents[2]


def _spec(**kwargs):
    spec = {
        "name": "formation_line",
        "shape": "line",
        "spacing": 1500,
        "rank_gap": 1800,
        "flank_gap": 6000,
        "max_front": 8,
        "ranks": ("melee", "ranged", "siege"),
        "keep_pace": True,
        "radius": 0,
        "rings": 0,
        "ring_gap": 0,
        "arc_span": 0,
        "arc_start": None,
        "ring_rank": "in",
    }
    spec.update(kwargs)
    return spec


def _unit(uid, rank, x=0, y=0, **extra):
    data = dict(
        id=uid,
        x=x,
        y=y,
        o=90,
        hp=40,
        speed=1000,
        radius=200,
        is_inside=False,
        use_formation=1,
        formation_rank=rank,
        type_name=uid,
        expanded_is_a=(uid, rank),
        rdg_range=0,
        mdg_range=1000,
        airground_type="ground",
        formation="",
        place=None,
    )
    data.update(extra)
    return SimpleNamespace(**data)


def test_line_slots_are_centered_and_evenly_spaced():
    slots = compute_slot_offsets(3, _spec(), margin=500)
    along = [a for a, _b in slots]
    assert along == [-1500, 0, 1500]
    assert all(b == 0 for _a, b in slots)


def test_line_wraps_to_a_second_rank():
    slots = compute_slot_offsets(5, _spec(max_front=3))
    assert [b for _a, b in slots] == [0, 0, 0, 1800, 1800]


def test_staggered_offsets_odd_columns():
    slots = compute_slot_offsets(3, _spec(shape="staggered", max_front=8))
    backs = [b for _a, b in slots]
    assert backs[0] == 0
    assert backs[1] == 900
    assert backs[2] == 0


def test_box_is_compact_square():
    slots = compute_slot_offsets(4, _spec(shape="box", spacing=1200))
    assert len(slots) == 4
    along = sorted(a for a, _b in slots)
    back = sorted(b for _a, b in slots)
    assert along[0] < 0 < along[-1]
    assert back[0] < 0 < back[-1]


def test_flank_splits_left_and_right():
    slots = compute_slot_offsets(4, _spec(shape="flank", max_front=8, flank_gap=6000))
    along = [a for a, _b in slots]
    assert min(along) < -2000
    assert max(along) > 2000


def test_circle_alias_places_units_around_center():
    slots = compute_slot_offsets(8, _spec(shape="circle", radius=4000))
    assert len(slots) == 8
    sq = [a * a + b * b for a, b in slots]
    assert min(sq) > 0
    assert max(sq) - min(sq) < 20000
    alongs = [a for a, _b in slots]
    backs = [b for _a, b in slots]
    assert min(alongs) < 0 < max(alongs)
    assert min(backs) < 0 < max(backs)


def test_wedge_arc_span_stays_in_front():
    slots = compute_slot_offsets(5, _spec(shape="wedge", radius=4000, arc_span=90))
    assert all(b <= 0 for _a, b in slots)
    alongs = [a for a, _b in slots]
    assert min(alongs) < 0 < max(alongs)


def test_unknown_shape_with_radius_uses_ring():
    polar = compute_slot_offsets(6, _spec(shape="blob", radius=4000))
    line = compute_slot_offsets(6, _spec(shape="line", radius=4000))
    assert polar != line
    assert any(b != 0 for _a, b in polar)
    assert _layout_kind(_spec(shape="blob", radius=4000)) == "ring"


def test_unknown_shape_without_polar_knobs_stays_line():
    assert compute_slot_offsets(3, _spec(shape="blob")) == compute_slot_offsets(
        3, _spec(shape="line")
    )


def test_circle_ranks_put_melee_inner():
    melee = [_unit("m1", "melee", x=0)]
    ranged = [_unit("a1", "ranged", x=1000)]
    packed = offsets_for_units(
        melee + ranged, _spec(shape="circle", radius=3000, rank_gap=1800)
    )
    by_id = {u.id: along * along + back * back for u, (along, back) in packed}
    assert by_id["m1"] < by_id["a1"]
    packed_out = offsets_for_units(
        melee + ranged,
        _spec(shape="circle", radius=3000, rank_gap=1800, ring_rank="out"),
    )
    by_out = {u.id: along * along + back * back for u, (along, back) in packed_out}
    assert by_out["m1"] > by_out["a1"]


def test_rings_split_same_rank_circle():
    units = [_unit(f"m{i}", "melee", x=i * 100) for i in range(6)]
    packed = offsets_for_units(
        units, _spec(shape="ring", radius=2000, rings=2, ring_gap=1500)
    )
    sq = sorted(along * along + back * back for _u, (along, back) in packed)
    assert sq[0] < sq[-1]


def test_line_puts_melee_in_front_of_ranged():
    melee = [_unit("m1", "melee", x=0), _unit("m2", "melee", x=1000)]
    ranged = [_unit("a1", "ranged", x=2000)]
    packed = offsets_for_units(melee + ranged, _spec(max_front=8))
    by_id = {u.id: back for u, (_along, back) in packed}
    assert by_id["m1"] == 0
    assert by_id["m2"] == 0
    assert by_id["a1"] == 1800


def test_flank_keeps_melee_on_both_wings():
    units = [
        _unit("m1", "melee", x=0),
        _unit("m2", "melee", x=1000),
        _unit("a1", "ranged", x=2000),
        _unit("a2", "ranged", x=3000),
    ]
    packed = offsets_for_units(units, _spec(shape="flank", max_front=8, flank_gap=6000))
    melee_along = [along for u, (along, _b) in packed if u.formation_rank == "melee"]
    ranged_back = [back for u, (_a, back) in packed if u.formation_rank == "ranged"]
    assert min(melee_along) < 0 < max(melee_along)
    assert all(b >= 1800 for b in ranged_back)


def test_assign_slots_face_the_move_direction():
    units = [_unit("m1", "melee", x=0, y=0), _unit("m2", "melee", x=0, y=1000)]
    target = SimpleNamespace(x=0, y=12000, xmin=-6000, xmax=6000, ymin=6000, ymax=18000)
    slots = assign_formation_slots(units, target, _spec(max_front=8), facing=90)
    xs = sorted(x for _u, _p, x, _y in slots)
    assert xs[0] < xs[1]
    ys = [y for _u, _p, _x, y in slots]
    assert all(y == ys[0] for y in ys)


def test_unit_formation_rank_uses_explicit_then_range():
    assert unit_formation_rank(_unit("m", "melee")) == "melee"
    archer = _unit("a", "", rdg_range=4000, mdg_range=0, formation_rank="")
    assert unit_formation_rank(archer) == "ranged"


def test_unit_can_form_requires_flag(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: False)
    assert not unit_can_form(_unit("m1", "melee"))


def test_unit_can_form_use_formation(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    assert unit_can_form(_unit("m1", "melee", use_formation=1))
    dead = _unit("m2", "melee", hp=0)
    assert not unit_can_form(dead)
    inside = _unit("m3", "melee", is_inside=True)
    assert not unit_can_form(inside)
    stopped = _unit("m4", "melee", speed=0, use_formation=1)
    assert not unit_can_form(stopped)


def test_cycle_order_matches_rules_order(monkeypatch):
    names = ["formation_line", "formation_box", "formation_staggered", "formation_flank"]
    monkeypatch.setattr("soundrts.world_formation.formation_type_names", lambda: names)
    monkeypatch.setattr(
        "soundrts.world_formation.default_formation_name", lambda: "formation_line"
    )
    assert cycle_next_formation("formation_line") == "formation_box"
    assert cycle_next_formation("formation_flank") == "formation_line"


def test_keep_pace_caps_to_slowest_unit():
    slow = _unit("s", "melee", speed=400)
    fast = _unit("f", "melee", speed=1200, x=1500)
    place = SimpleNamespace(
        id="a1",
        x=6000,
        y=6000,
        xmin=0,
        xmax=12000,
        ymin=0,
        ymax=12000,
        title=[],
    )
    t = SimpleNamespace(id="a1", place=place, x=6000, y=6000, player=None)
    orders = [
        SimpleNamespace(keyword="go", target=t, _creation_time=1, _formation_anchor_id=None),
        SimpleNamespace(keyword="go", target=t, _creation_time=1, _formation_anchor_id=None),
    ]
    slow.orders = [orders[0]]
    fast.orders = [orders[1]]
    apply_slots_to_go_orders([(slow, orders[0]), (fast, orders[1])], _spec())
    assert slow._formation_speed_cap == 400
    assert fast._formation_speed_cap == 400
    assert orders[0].target is not t
    assert orders[0]._formation_anchor is t


def test_combat_slots_put_melee_in_front_of_ranged():
    from soundrts.world_formation import assign_formation_slots, _combat_anchor

    place = SimpleNamespace(
        id="a1",
        x=6000,
        y=6000,
        xmin=0,
        xmax=12000,
        ymin=0,
        ymax=12000,
        title=[],
        objects=[],
    )
    threat = SimpleNamespace(id="e1", x=1500, y=6000, place=place, hp=40, player="p2")
    melee = [_unit("m1", "melee", x=7000, y=5800), _unit("m2", "melee", x=7000, y=6200)]
    ranged = [_unit("r1", "ranged", x=8500, y=6000, rdg_range=4000, mdg_range=0)]
    units = melee + ranged
    for u in units:
        u.place = place
        u.player = "p1"
        u.is_an_enemy = lambda o, t=threat: o is t
    dummy, facing = _combat_anchor(units, threat)
    assert dummy is not None
    slots = assign_formation_slots(units, dummy, _spec(), facing=facing)
    by_id = {id(u): (x, y) for u, _p, x, y in slots}
    melee_x = sum(by_id[id(u)][0] for u in melee) / len(melee)
    ranged_x = by_id[id(ranged[0])][0]
    assert melee_x < ranged_x
    assert melee_x < 7000


def test_go_to_enemy_breaks_formation():
    place = SimpleNamespace(
        id="a1",
        x=6000,
        y=6000,
        xmin=0,
        xmax=12000,
        ymin=0,
        ymax=12000,
        title=[],
        objects=[],
    )
    enemy = SimpleNamespace(id="e1", x=2000, y=6000, place=place, hp=40, player="p2")
    a = _unit("m1", "melee", x=8000, y=5800)
    b = _unit("m2", "melee", x=8000, y=6200)
    for u in (a, b):
        u.place = place
        u.player = "p1"
        u.is_an_enemy = lambda o, e=enemy: o is e
        u.world = SimpleNamespace(time=1)
        u._formation_slot = (place, 8000, 6000)
    orders = [
        SimpleNamespace(
            keyword="go",
            target=enemy,
            _creation_time=1,
            _formation_anchor=None,
            _formation_anchor_id=None,
        ),
        SimpleNamespace(
            keyword="go",
            target=enemy,
            _creation_time=1,
            _formation_anchor=None,
            _formation_anchor_id=None,
        ),
    ]
    a.orders = [orders[0]]
    b.orders = [orders[1]]
    apply_slots_to_go_orders([(a, orders[0]), (b, orders[1])], _spec())
    assert getattr(a, "_formation_slot", None) is None
    assert getattr(b, "_formation_slot", None) is None
    assert getattr(a, "_formation_focus_fire", 0)
    assert orders[0].target is enemy


def test_after_group_attack_breaks_slots():
    a = _unit("m1", "melee")
    b = _unit("m2", "melee")
    a._formation_slot = (None, 1, 2)
    b._formation_slot = (None, 3, 4)
    after_group_order([a, b], "attack")
    assert a._formation_slot is None
    assert b._formation_slot is None
    assert a._formation_focus_fire == 1


def test_formation_hold_xy_skips_focus_fire():
    u = _unit("m", "melee", x=0, y=0)
    u._formation_slot = (None, 100, 200)
    assert formation_hold_xy(u) == (100, 200)
    u._formation_focus_fire = 1
    assert formation_hold_xy(u) is None


def test_formation_stand_ground_only_when_enabled(monkeypatch):
    u = _unit("m", "melee")
    u.ai_mode = "guard"
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: False)
    assert not formation_stand_ground(u)
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    assert formation_stand_ground(u)
    u.ai_mode = "offensive"
    assert not formation_stand_ground(u)


def test_point_blocks_segment_midpoint_not_endpoints():
    assert _point_blocks_segment(0, 0, 10000, 0, 5000, 0, 400)
    assert not _point_blocks_segment(0, 0, 10000, 0, 5000, 1000, 400)
    assert not _point_blocks_segment(0, 0, 10000, 0, 0, 0, 400)
    assert not _point_blocks_segment(0, 0, 10000, 0, 10000, 0, 400)


def test_formation_blocker_front_rank_not_holders():
    place = SimpleNamespace(id="a1", objects=[])
    walker = _unit("w", "melee", x=0, y=0)
    walker.place = place
    walker.player = "p1"
    walker.radius = 200
    walker.is_an_enemy = lambda o: getattr(o, "player", None) == "p2"
    target = _unit("t", "ranged", x=8000, y=0)
    target.place = place
    target.player = "p2"
    wall = _unit("wall", "melee", x=4000, y=0)
    wall.place = place
    wall.player = "p2"
    wall.radius = 200
    wall._formation_slot = (place, 4000, 0)
    place.objects = [walker, wall, target]
    assert formation_blocker(walker, target) is wall
    walker._formation_slot = (place, 0, 0)
    assert formation_blocker(walker, target) is None


def test_idle_rearrange_keeps_each_square(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    monkeypatch.setattr(
        "soundrts.world_formation.formation_type_names",
        lambda: ["formation_line"],
    )
    monkeypatch.setattr(
        "soundrts.world_formation.default_formation_name",
        lambda: "formation_line",
    )
    monkeypatch.setattr("soundrts.world_formation._spec", lambda name=None: _spec())
    west = SimpleNamespace(
        id="a1",
        x=6000,
        y=6000,
        xmin=0,
        xmax=12000,
        ymin=0,
        ymax=12000,
        title=[],
        objects=[],
    )
    east = SimpleNamespace(
        id="c3",
        x=30000,
        y=30000,
        xmin=24000,
        xmax=36000,
        ymin=24000,
        ymax=36000,
        title=[],
        objects=[],
    )
    west_units = [
        _unit("w1", "melee", x=5000, y=5800),
        _unit("w2", "melee", x=7000, y=6200),
    ]
    east_units = [
        _unit("e1", "melee", x=29000, y=29800),
        _unit("e2", "melee", x=31000, y=30200),
    ]
    for u, place in ((west_units[0], west), (west_units[1], west),
                     (east_units[0], east), (east_units[1], east)):
        u.place = place
        u.formation = "formation_line"
        u.orders = []
        u.world = SimpleNamespace(time=1)

        def _take(args, forget_previous=True, self=u):
            self.orders = [
                SimpleNamespace(
                    keyword="go",
                    target=SimpleNamespace(id=args[1]),
                    _formation_anchor=None,
                    _formation_anchor_id=None,
                )
            ]

        u.take_order = _take
    apply_idle_rearrange(west_units + east_units)
    for u in west_units:
        slot = getattr(u, "_formation_slot", None)
        assert slot is not None, u.id
        assert slot[0] is west
        assert west.xmin <= slot[1] < west.xmax
        assert west.ymin <= slot[2] < west.ymax
    for u in east_units:
        slot = getattr(u, "_formation_slot", None)
        assert slot is not None, u.id
        assert slot[0] is east
        assert east.xmin <= slot[1] < east.xmax
        assert east.ymin <= slot[2] < east.ymax


def test_orders_are_registered():
    assert ORDERS_DICT["set_formation"] is SetFormationOrder
    assert ORDERS_DICT["cycle_formation"] is CycleFormationOrder
    assert SetFormationOrder.nb_args == 0
    assert CycleFormationOrder.nb_args == 0


def test_res_rules_define_formations_but_leave_them_off():
    text = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    assert "class formation" in text
    assert "def formation_line" in text
    assert "def formation_flank" in text
    assert not any(line.strip() == "formations 1" for line in text.splitlines())


def test_aoe2_rules_enable_and_name_the_four_shapes():
    from soundrts.definitions import Rules
    from soundrts.lib.nofloat import PRECISION as P

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    assert r.get("parameters", "formations") == 1
    assert r.get("parameters", "default_formation") == "formation_line"
    names = [
        name
        for name, cls in r.classes.items()
        if getattr(cls, "cls", None) is FormationRules
    ]
    assert names == [
        "formation_line",
        "formation_box",
        "formation_staggered",
        "formation_flank",
    ]
    line = r.unit_class("formation_line")
    assert line.shape == "line"
    assert line.spacing == int(1.5 * P)
    box = r.unit_class("formation_box")
    assert box.shape == "box"
    flank = r.unit_class("formation_flank")
    assert flank.shape == "flank"
    assert flank.flank_gap == 6 * P
    assert getattr(line, "mdg", 0) == 0
    assert getattr(line, "rdf", 0) == 0
    assert getattr(line, "speed", 0) == 0
    assert not getattr(line, "mdg_vs", None)
    assert "infantry" in list(r.get("parameters", "formation_units"))
    assert "monk" in list(r.get("parameters", "formation_rank_siege"))


def test_style_and_tts_wire_formation_commands():
    style = (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8")
    tts = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    assert "def cycle_formation" in style
    assert "def set_formation" in style
    cycle_block = style.split("def cycle_formation", 1)[1].split("\ndef ", 1)[0]
    set_block = style.split("def set_formation", 1)[1].split("\ndef ", 1)[0]
    assert "index" not in cycle_block
    assert "index" in set_block
    assert "5845" in tts and "line formation" in tts
    assert "5849" in zh and "切换阵型" in zh
    aoe2_style = (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8")
    assert "formation_change" in aoe2_style


def test_cycle_formation_hotkey_is_bindable():
    from soundrts.hotkey_catalogs import _build_classic_catalog, _build_command_catalog, _build_unit_catalog
    from soundrts.hotkey_editor import get_default_key
    from soundrts import msgparts as mp

    unit_ids = [bid for bid, _ in _build_unit_catalog()]
    command_ids = [bid for bid, _ in _build_command_catalog()]
    classic_ids = [bid for bid, _ in _build_classic_catalog()]
    assert "unit.cycle_formation" in unit_ids
    assert "command.cycle_formation" in command_ids
    assert "classic.cycle_formation" in classic_ids
    assert mp.HOTKEY_CYCLE_FORMATION == [5849]
    assert get_default_key("unit.cycle_formation", "unit") == "CTRL SHIFT f"
    assert get_default_key("classic.cycle_formation", "classic") == "CTRL SHIFT f"
    orders = (ROOT / "soundrts" / "clientgame" / "game_orders.py").read_text(encoding="utf-8")
    assert "def cmd_cycle_formation" in orders
    assert "require_menu=False" in orders
    for rel in (
        ("res", "ui", "unit_bindings.txt"),
        ("res", "ui", "command_bindings.txt"),
        ("res", "ui", "legacy_bindings.txt"),
        ("mods", "aoe2", "ui", "legacy_bindings.txt"),
    ):
        text = ROOT.joinpath(*rel).read_text(encoding="utf-8")
        assert "CTRL SHIFT f: cycle_formation" in text


def test_formation_class_parses_combat_stats():
    from soundrts.definitions import Rules
    from soundrts.lib.nofloat import PRECISION as P

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def formation_wedge
class formation
shape flank
mdg 2
rdf -3
speed -1.5
mdg_vs cavalry 1
"""
    )
    cls = r.unit_class("formation_wedge")
    assert cls.mdg == 2 * P
    assert cls.rdf == -3 * P
    assert cls.mdg_vs == {"cavalry": P}
    assert cls.rdg == 0
    assert cls.mdf == 0
    assert cls.speed == -int(1.5 * P)


def test_formation_class_parses_circle_shape():
    from soundrts.definitions import Rules
    from soundrts.lib.nofloat import PRECISION as P

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def formation_circle
class formation
shape circle
spacing 1.5
radius 4
mdg 20%
speed -30%
"""
    )
    cls = r.unit_class("formation_circle")
    assert cls.shape == "circle"
    assert cls.radius == 4 * P
    assert cls.spacing == int(1.5 * P)
    assert _layout_kind(
        {
            "shape": cls.shape,
            "radius": cls.radius,
            "arc_span": getattr(cls, "arc_span", 0) or 0,
            "rings": getattr(cls, "rings", 0) or 0,
        }
    ) == "ring"


def test_formation_class_parses_percent_stats():
    from soundrts.definitions import Rules
    from soundrts.world_formation import _parse_bonus

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def formation_circle
class formation
shape box
mdg 20%
speed -30%
mdg_vs cavalry 50%
"""
    )
    cls = r.unit_class("formation_circle")
    assert _parse_bonus(cls.mdg) == ("pct", 20)
    assert _parse_bonus(cls.speed) == ("pct", -30)
    assert cls.mdg_vs == {"cavalry": ("pct", 50)}


def _combat_unit(**extra):
    import soundrts.worldunit  # noqa: F401
    from soundrts.combat.damage_calculation import DamageCalculationMixin
    from soundrts.lib.nofloat import PRECISION as P

    class U(DamageCalculationMixin):
        mdg = 5 * P
        mdg_vs = {}
        rdg = 4 * P
        rdg_vs = {}
        mdf = 3 * P
        mdf_vs = {}
        rdf = 6 * P
        rdf_vs = {}
        mdg_on_terrain = ()
        rdg_on_terrain = ()
        ai_mode = "offensive"
        type_name = "u"
        expanded_is_a = ()
        hp = 10
        place = None
        _formation_focus_fire = 0
        _formation_combat_spec = None
        _formation_slot = None

    u = U()
    for key, val in extra.items():
        setattr(u, key, val)
    return u


def _combat_spec(**kwargs):
    spec = {
        "name": "formation_wedge",
        "shape": "flank",
        "spacing": 1500,
        "rank_gap": 1800,
        "flank_gap": 6000,
        "max_front": 0,
        "ranks": ("melee", "ranged", "siege"),
        "keep_pace": True,
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
    spec.update(kwargs)
    return spec


def test_formation_combat_bonus_only_while_holding_ranks():
    from soundrts.lib.nofloat import PRECISION as P

    place = SimpleNamespace()
    u = _combat_unit(place=place)
    target = SimpleNamespace(
        type_name="t", expanded_is_a=(), armor=None, _armor_instance=None
    )
    cavalry = SimpleNamespace(
        type_name="cavalry",
        expanded_is_a=("cavalry",),
        armor=None,
        _armor_instance=None,
    )
    attacker = SimpleNamespace(type_name="archer", expanded_is_a=("archer",))
    spec = _combat_spec(mdg=2 * P, rdf=-3 * P, mdg_vs={"cavalry": P})
    _bind_formation_slots([(u, place, 100, 200)], spec=spec)
    assert formation_hold_xy(u) == (100, 200)
    assert u._get_melee_damage_vs(target) == 7 * P
    assert u._get_melee_damage_vs(cavalry) == 8 * P
    assert u._get_ranged_defense_vs(attacker) == 3 * P
    assert getattr(u, "mdg") == 5 * P
    u.ai_mode = "chase"
    assert u._get_melee_damage_vs(target) == 5 * P
    u.ai_mode = "offensive"
    u._formation_focus_fire = 1
    assert u._get_melee_damage_vs(target) == 5 * P
    u._formation_focus_fire = 0
    break_formation_hold(u)
    assert getattr(u, "_formation_combat_spec", None) is None
    assert u._get_melee_damage_vs(target) == 5 * P
    assert u._get_ranged_defense_vs(attacker) == 6 * P


def test_aoe2_line_spec_has_no_combat_bonus():
    from soundrts.lib.nofloat import PRECISION as P

    place = SimpleNamespace()
    u = _combat_unit(place=place)
    target = SimpleNamespace(
        type_name="t", expanded_is_a=(), armor=None, _armor_instance=None
    )
    _bind_formation_slots([(u, place, 0, 0)], spec=_spec())
    assert getattr(u, "_formation_combat_spec", None) is None
    assert u._get_melee_damage_vs(target) == 5 * P
    assert formation_hold_xy(u) == (0, 0)


def test_formation_speed_applies_after_keep_pace():
    from soundrts.lib.nofloat import PRECISION as P
    from soundrts.worldunit.world_attributes import CreatureAttributes

    place = SimpleNamespace()
    u = _unit("s", "melee", speed=2 * P)
    u.place = place
    u.VERY_SLOW = 1
    u.ai_mode = "offensive"
    u._formation_focus_fire = 0
    spec = _combat_spec(mdg=2 * P, speed=-100)
    _bind_formation_slots([(u, place, 0, 0)], spec=spec)
    u._formation_speed_cap = 400
    assert CreatureAttributes._speed_with_formation_cap(u, 2 * P) == 300
    u.ai_mode = "chase"
    assert CreatureAttributes._speed_with_formation_cap(u, 2 * P) == 400
    u.ai_mode = "offensive"
    break_formation_hold(u)
    assert CreatureAttributes._speed_with_formation_cap(u, 2 * P) == 2 * P
    assert getattr(u, "_formation_combat_spec", None) is None


def test_formation_percent_scales_with_unit_stats():
    from soundrts.lib.nofloat import PRECISION as P
    from soundrts.worldunit.world_attributes import CreatureAttributes

    place = SimpleNamespace()
    u = _combat_unit(place=place, mdg=5 * P)
    target = SimpleNamespace(
        type_name="t", expanded_is_a=(), armor=None, _armor_instance=None
    )
    cavalry = SimpleNamespace(
        type_name="cavalry",
        expanded_is_a=("cavalry",),
        armor=None,
        _armor_instance=None,
    )
    spec = _combat_spec(mdg=("pct", 20), speed=("pct", -50), mdg_vs={"cavalry": ("pct", 40)})
    _bind_formation_slots([(u, place, 0, 0)], spec=spec)
    assert u._get_melee_damage_vs(target) == 6 * P
    assert u._get_melee_damage_vs(cavalry) == 8 * P
    u._formation_speed_cap = 400
    assert CreatureAttributes._speed_with_formation_cap(u, 2 * P) == 200
    break_formation_hold(u)
    assert u._get_melee_damage_vs(target) == 5 * P
    assert CreatureAttributes._speed_with_formation_cap(u, 2 * P) == 2 * P
