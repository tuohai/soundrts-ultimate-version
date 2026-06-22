"""Tests for level_skills / learn_level_skills."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.worldunit.world_attributes import CreatureAttributes
from soundrts.worldunit.world_status_update import CreatureStatusUpdate


def _make_unit(**overrides):
    unit = SimpleNamespace(
        type_name="test_hero",
        id=42,
        level=1,
        max_level=20,
        xp=0,
        xp_thresholds=[100, 200, 300, 400, 500, 600, 700, 800, 900],
        xp_reward=0,
        xp_reward_per_xp=0,
        hp_max=100,
        hp=100,
        hp_max_per_level=0,
        hp_regen=0,
        hp_regen_per_level=0,
        mdg=0,
        rdg=0,
        mdf=0,
        rdf=0,
        mdg_per_level=0,
        rdg_per_level=0,
        mdf_per_level=0,
        rdf_per_level=0,
        revival_time=0,
        revival_time_per_level=0,
        can_use_skill=(),
        level_skills=(10, "skill_zhuiri_jianfa", 3, "skill_basic"),
        learn_level_skills=(10, "skill_zhuiri_jianfa"),
        active_trigger_skills=(),
        notifications=[],
    )
    for key, value in overrides.items():
        setattr(unit, key, value)
    unit.notify = lambda msg: unit.notifications.append(msg)
    for cls in (CreatureAttributes, CreatureStatusUpdate):
        for name in (
            "_parse_level_skill_pairs",
            "_get_level_skills_map",
            "_get_learn_level_skills_map",
            "_ensure_can_use_skill_list",
            "_unlock_level_skills",
            "_apply_level_skills_up_to",
            "_required_level_for_skill",
            "_try_learn_skill",
            "_known_skill_names",
            "iter_auto_trigger_skill_names",
            "iter_attack_trigger_skill_names",
            "iter_attack_replace_skill_names",
            "iter_passive_trigger_skill_names",
            "iter_skills_with_trigger_timing",
            "iter_manual_skill_names",
            "_skill_class",
            "increase_xp",
        ):
            if hasattr(cls, name):
                setattr(unit, name, getattr(cls, name).__get__(unit, cls))
    return unit


def test_level_skills_not_unlocked_at_level_one():
    unit = _make_unit()
    unit._apply_level_skills_up_to(notify=False)
    assert not unit.can_use_skill


def test_level_skills_unlock_on_level_up():
    unit = _make_unit()
    unit.increase_xp(100)
    assert unit.level == 2
    assert not unit.can_use_skill

    unit.increase_xp(200)
    assert unit.level == 3
    assert "skill_basic" in unit.can_use_skill


def test_level_skills_unlock_at_target_level():
    unit = _make_unit(level=10)
    unit._unlock_level_skills(10, notify=True)
    assert unit.can_use_skill == ["skill_zhuiri_jianfa"]
    assert any(n.startswith("skill_unlock,skill_zhuiri_jianfa,") for n in unit.notifications)


def test_apply_level_skills_up_to_restores_multiple():
    unit = _make_unit(level=10)
    unit._apply_level_skills_up_to(notify=False)
    assert unit.can_use_skill == ["skill_basic", "skill_zhuiri_jianfa"]


def test_try_learn_skill_requires_learn_level_skills():
    unit = _make_unit(level=5)
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", notify=False)
    assert not ok
    assert reason == "skill_level_too_low"
    assert not unit.can_use_skill


def test_try_learn_skill_at_required_level():
    unit = _make_unit(level=10)
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", notify=False)
    assert ok
    assert reason is None
    assert unit.can_use_skill == ["skill_zhuiri_jianfa"]


def test_try_learn_skill_already_known():
    unit = _make_unit(level=10, can_use_skill=["skill_zhuiri_jianfa"])
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", notify=False)
    assert not ok
    assert reason == "skill_already_known"


def test_level_skills_alone_does_not_gate_skill_book():
    """Only level_skills: auto-unlock at level, book usable at any level."""
    unit = _make_unit(
        level=1,
        level_skills=(10, "skill_zhuiri_jianfa"),
        learn_level_skills=(),
    )
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", notify=False)
    assert ok
    assert unit.can_use_skill == ["skill_zhuiri_jianfa"]


def test_learn_level_skills_alone_does_not_auto_unlock_on_level_up():
    """Only learn_level_skills: book needs level, no auto-unlock."""
    unit = _make_unit(
        level=11,
        level_skills=(),
        learn_level_skills=(10, "skill_zhuiri_jianfa"),
    )
    unit._apply_level_skills_up_to(notify=False)
    assert not unit.can_use_skill

    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", notify=False)
    assert ok
    assert unit.can_use_skill == ["skill_zhuiri_jianfa"]


def test_independent_unlock_and_learn_levels():
    """Auto-unlock and book requirement can use different levels."""
    unit = _make_unit(
        level=5,
        level_skills=(5, "skill_a"),
        learn_level_skills=(10, "skill_a"),
    )
    unit._apply_level_skills_up_to(notify=False)
    assert unit.can_use_skill == ["skill_a"]

    unit.can_use_skill = ()
    ok, reason = unit._try_learn_skill("skill_a", notify=False)
    assert not ok
    assert reason == "skill_level_too_low"

    unit.level = 10
    ok, reason = unit._try_learn_skill("skill_a", notify=False)
    assert ok


def test_unified_skill_auto_and_manual_from_can_use_skill():
    unit = _make_unit(level=10, can_use_skill=["skill_zhuiri_jianfa"])
    auto = list(unit.iter_auto_trigger_skill_names())
    manual = list(unit.iter_manual_skill_names())
    assert "skill_zhuiri_jianfa" not in auto  # stub has no skill class
    assert "skill_zhuiri_jianfa" in manual


def test_legacy_active_trigger_skills_still_auto_and_manual():
    unit = _make_unit(
        level=1,
        can_use_skill=(),
        active_trigger_skills=("skill_legacy",),
    )
    assert list(unit.iter_skills_with_trigger_timing("on_hit")) == ["skill_legacy"]
    assert list(unit.iter_auto_trigger_skill_names()) == ["skill_legacy"]
    assert list(unit.iter_manual_skill_names()) == ["skill_legacy"]


def test_trigger_timing_routes_can_use_skill():
    unit = _make_unit(level=10, can_use_skill=["skill_a", "skill_b", "skill_c"])

    class _ClsA:
        auto_trigger = 1
        trigger_timing = "on_attack"

    class _ClsB:
        auto_trigger = 1
        trigger_timing = "on_attack_replace"

    class _ClsC:
        auto_trigger = 1
        trigger_timing = "on_damaged"

    mapping = {
        "skill_a": _ClsA,
        "skill_b": _ClsB,
        "skill_c": _ClsC,
    }
    unit._skill_class = lambda name: mapping.get(name)

    assert list(unit.iter_attack_trigger_skill_names()) == ["skill_a"]
    assert list(unit.iter_attack_replace_skill_names()) == ["skill_b"]
    assert list(unit.iter_passive_trigger_skill_names()) == ["skill_c"]
    assert list(unit.iter_auto_trigger_skill_names()) == []


def test_item_learn_level_gates_skill_book():
    unit = _make_unit(level=5, learn_level_skills=())
    book = SimpleNamespace(
        learn_level=10,
        learn_level_skills=(),
        skills=("skill_zhuiri_jianfa",),
    )
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", item=book, notify=False)
    assert not ok
    assert reason == "skill_level_too_low"

    unit.level = 10
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", item=book, notify=False)
    assert ok


def test_item_and_unit_learn_level_use_strictest():
    unit = _make_unit(level=8, learn_level_skills=(5, "skill_zhuiri_jianfa"))
    book = SimpleNamespace(learn_level=10, learn_level_skills=(), skills=("skill_zhuiri_jianfa",))
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", item=book, notify=False)
    assert not ok  # item requires 10, unit only requires 5

    unit.level = 10
    ok, reason = unit._try_learn_skill("skill_zhuiri_jianfa", item=book, notify=False)
    assert ok


def test_use_item_order_consumes_skill_book():
    from soundrts.worldunit.world_order import CreatureOrders
    from soundrts.worldunit import worldbase

    book = SimpleNamespace(
        id=99,
        type_name="zhuiri_jianfa_book",
        learn_level=1,
        learn_level_skills=(),
        skills=("skill_zhuiri_jianfa",),
        buffs=(),
        use_effect=None,
        resource_rewards=(),
        use_square=None,
        is_weapon_item=False,
        is_armor_item=False,
        move_to=lambda *a: None,
        delete=lambda: None,
        unequip_calls=[],
    )
    book.unequip = lambda host, **kw: book.unequip_calls.append(kw)

    unit = _make_unit(level=1, can_use_skill=(), learn_level_skills=(), level_skills=())
    unit.inventory = [book]
    unit.world = SimpleNamespace(unit_class=lambda n: None, schedule_after=lambda d, f: None)
    unit.player = SimpleNamespace(_normalize_square_token=None, _unit_on_square=None)
    unit.use_consumable_item = worldbase.Unit.use_consumable_item.__get__(unit, type(unit))
    unit._find_inventory_item = CreatureOrders._find_inventory_item.__get__(unit, type(unit))

    CreatureOrders.use_item_order(unit, 99)
    assert "skill_zhuiri_jianfa" in unit.can_use_skill
    assert book not in unit.inventory
    assert book.unequip_calls == [{"strip_skills": False}]


def test_use_item_order_skill_already_known_keeps_book():
    from soundrts.worldunit.world_order import CreatureOrders
    from soundrts.worldunit import worldbase

    book = SimpleNamespace(
        id=99,
        type_name="zhuiri_jianfa_book",
        learn_level=1,
        learn_level_skills=(),
        skills=("skill_zhuiri_jianfa",),
        is_weapon_item=False,
        is_armor_item=False,
        use_square=None,
    )
    unit = _make_unit(level=1, can_use_skill=["skill_zhuiri_jianfa"], learn_level_skills=())
    unit.inventory = [book]
    unit.world = SimpleNamespace(unit_class=lambda n: None, schedule_after=lambda d, f: None)
    unit.player = SimpleNamespace(_normalize_square_token=None, _unit_on_square=None)
    unit.use_consumable_item = worldbase.Unit.use_consumable_item.__get__(unit, type(unit))
    unit._find_inventory_item = CreatureOrders._find_inventory_item.__get__(unit, type(unit))

    CreatureOrders.use_item_order(unit, 99)
    assert any(n == "order_impossible,skill_already_known" for n in unit.notifications)
    assert book in unit.inventory


def test_item_use_sound_config_wired():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    events = (root / "clientgameentity" / "events.py").read_text(encoding="utf-8")
    style = (root.parent / "res" / "ui" / "style.txt").read_text(encoding="utf-8")
    assert "_play_item_use_sound" in events
    assert "use_{type_name}" in events or "use_" in events
    assert "item_used" in style


def test_skill_message_tts_entries_present():
    """技能学习相关 messages 必须走 tts ID，否则非中文语言无法播报。"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    style = (root / "res" / "ui" / "style.txt").read_text(encoding="utf-8")
    for key, tid in (
        ("skill_level_too_low", 5686),
        ("skill_already_known", 5687),
        ("skill_learned", 5688),
        ("building_refund", 5689),
    ):
        assert f"{key} {tid}" in style, f"style.txt messages.{key} should use tts {tid}"
    for rel in (("res", "ui", "tts.txt"), ("res", "ui-zh", "tts.txt")):
        txt = (root / Path(*rel)).read_text(encoding="utf-8")
        for tid in (5686, 5687, 5688, 5689):
            assert f"\n{tid} " in ("\n" + txt), f"{rel} missing tts {tid}"
