"""worldskill：effect deploy 仅在目标格部署 class effect。"""

import types

from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION
from soundrts.worldskill import Skill


_MINI_RULES = """
def sc_blast
class effect
harm_level 50
harm_radius 8

def sc_nuke_test
class skill
effect deploy 5 sc_blast

def footman
class soldier
"""


def test_parse_deploy_args_with_optional_count():
    assert Skill.parse_deploy_args(["5", "sc_blast"]) == (5 * PRECISION, 1, "sc_blast")
    assert Skill.parse_deploy_args(["5", "2", "greek_fire"]) == (
        5 * PRECISION,
        2,
        "greek_fire",
    )


def test_get_deploy_effect_class_rejects_soldiers():
    rules.load(_MINI_RULES)
    assert Skill._get_deploy_effect_class("sc_blast") is not None
    rules.load(_MINI_RULES + "\ndef grunt\nclass soldier\n")
    assert Skill._get_deploy_effect_class("grunt") is None


def test_execute_deploy_calls_lang_add_units():
    rules.load(_MINI_RULES)
    skill_cls = rules.unit_class("sc_nuke_test")
    calls = []

    player = types.SimpleNamespace(
        lang_add_units=lambda items, target=None, decay=0, **kw: calls.append(
            (list(items), decay, target)
        )
    )
    caster = types.SimpleNamespace(player=player)
    target = types.SimpleNamespace(x=0, y=0, place=None)
    world = types.SimpleNamespace()

    assert skill_cls._execute_deploy(caster, target, world) is True
    assert calls == [(["sc_blast"], 5 * PRECISION, target)]


def test_execute_deploy_rejects_non_effect_type():
    rules.load(
        _MINI_RULES
        + """
def bad_skill
class skill
effect deploy 5 footman
"""
    )
    skill_cls = rules.unit_class("bad_skill")
    player = types.SimpleNamespace(lang_add_units=lambda *a, **k: None)
    caster = types.SimpleNamespace(player=player)
    target = types.SimpleNamespace(x=0, y=0)

    assert skill_cls._execute_deploy(caster, target, None) is False


def test_execute_raise_dead_returns_true_on_success():
    from soundrts.worldresource import Corpse

    rules.load(
        """
def a_raise_dead
class skill
effect raise_dead 600 zombie
"""
    )
    skill_cls = rules.unit_class("a_raise_dead")
    corpse = Corpse.__new__(Corpse)
    corpse.x = 1
    corpse.y = 1
    calls = []

    world = types.SimpleNamespace(
        get_objects=lambda x, y, r, filter: [c for c in [corpse] if filter(c)]
    )
    player = types.SimpleNamespace(
        lang_add_units=lambda *a, **kw: calls.append((a, kw))
    )
    caster = types.SimpleNamespace(player=player, x=0, y=0)
    target = types.SimpleNamespace(x=0, y=0)

    assert skill_cls.execute_skill(caster, target, world) is True
    assert calls


def test_execute_recall_returns_true_on_success():
    rules.load(
        """
def a_recall
class skill
effect recall
effect_radius 6
"""
    )
    skill_cls = rules.unit_class("a_recall")
    moved = []

    class _Unit:
        airground_type = "ground"
        is_teleportable = True

        def move_to(self, place, x, y):
            moved.append((place, x, y))

    unit = _Unit()
    caster_place = types.SimpleNamespace(is_water=False, can_receive=lambda t: True)
    caster = types.SimpleNamespace(
        player=types.SimpleNamespace(id="p1"),
        place=caster_place,
        x=0,
        y=0,
        nearest_water=lambda: None,
    )
    unit.player = caster.player
    target = types.SimpleNamespace(x=10, y=10)
    world = types.SimpleNamespace(
        get_objects=lambda x, y, r, filter: [u for u in [unit] if filter(u)]
    )

    assert skill_cls.execute_skill(caster, target, world) is True
    assert moved == [(caster_place, None, None)]
