"""武侠技能：burst / harm_area / harm_target / push / reflect 测试。"""
from __future__ import annotations

import types
from pathlib import Path

from soundrts.definitions import Rules, rules
from soundrts.lib.nofloat import PRECISION, to_int
from soundrts.skill_combat import SkillCombatProxy
from soundrts.worldskill import Skill

ROOT = Path(__file__).resolve().parents[2]

WUXIA_RULES = (ROOT / "mods/wuxia/rules.txt").read_text(encoding="utf-8")


def _load_wuxia_rules():
    rules.load(WUXIA_RULES)


class _StubPlayer:
    def __init__(self, pid="p1"):
        self.id = pid
        self.neutral = False
        self.is_human = True

    def observe(self, _unit):
        pass

    def player_is_an_enemy(self, other):
        return other is not None and other.id != self.id

    def player_is_a_hostile_enemy(self, other):
        return self.player_is_an_enemy(other)

    def on_unit_attacked(self, _unit, _attacker):
        pass


def _make_combat_unit(player, enemy_player=None, hp=100 * PRECISION, mdg=10 * PRECISION):
    from soundrts.combat.damage_effects import DamageEffectsMixin

    class _U(DamageEffectsMixin):
        def __init__(self):
            self.player = player
            self.hp = hp
            self.hp_max = hp
            self._buffs = []
            self.is_vulnerable = True
            self.type_name = "test_unit"
            self.expanded_is_a = set()
            self.id = id(self)
            self.place = None
            self.is_inside = None
            self.rdg_range = 0
            self.mdg = mdg
            self.rdg = 0
            self.mdg_vs = {}
            self.rdg_vs = {}
            self.mdf = 0
            self.rdf = 0
            self.mdf_vs = {}
            self.rdf_vs = {}
            self.minimal_damage = 0
            self.forced_damage = 0
            self.op_charge_mdg = 0
            self.op_charge_rdg = 0
            self.op_charge_mdg_cd = 0
            self.op_charge_rdg_cd = 0
            self.op_charge_mdg_dist = 0
            self.op_charge_rdg_dist = 0
            self.op_charge_mdg_ready = True
            self.op_charge_rdg_ready = True
            self.op_charge_mdg_vs = {}
            self.op_charge_rdg_vs = {}
            self.debuffs = []
            self.active_trigger_skills = ()
            self.passive_trigger_skills = ()
            self.attack_trigger_skills = ()
            self.attack_replace_skills = ()
            self.attack_trigger_buffs = ()
            self.attack_trigger_debuffs = ()
            self.attack_replace_buffs = ()
            self.attack_replace_debuffs = ()
            self.capture_hp_threshold = 0
            self._has_yielded = False
            self.world = types.SimpleNamespace(
                time=0,
                treaty_until_time=0,
                random=types.SimpleNamespace(randint=lambda a, b: 1),
                unit_class=lambda name: None,
            )
            self._enemy_player = enemy_player

        def is_an_enemy(self, other):
            if self._enemy_player is None:
                return False
            return getattr(other, "player", None) is self._enemy_player

        def notify(self, *_args, **_kwargs):
            pass

        def has_cooldown(self, _skill_cls):
            return False

        def add_cooldown(self, _skill_cls):
            pass

        def add_buff(self, name, author):
            self._buffs.append((name, author))

        def _trigger_attack_start_skill(self, target, skill_name, is_melee):
            from soundrts.combat.attack_action import AttackActionMixin

            return AttackActionMixin._trigger_attack_start_skill(self, target, skill_name, is_melee)

        def _trigger_attack_start_skills(self, target, is_melee, replace=False):
            from soundrts.combat.attack_action import AttackActionMixin

            return AttackActionMixin._trigger_attack_start_skills(self, target, is_melee, replace)

        def _trigger_attack_start_buff(self, target, buff_name, is_melee, apply_to_target=False):
            from soundrts.combat.attack_action import AttackActionMixin

            return AttackActionMixin._trigger_attack_start_buff(
                self, target, buff_name, is_melee, apply_to_target
            )

        def _trigger_attack_start_buffs(self, target, is_melee, replace=False):
            from soundrts.combat.attack_action import AttackActionMixin

            return AttackActionMixin._trigger_attack_start_buffs(self, target, is_melee, replace)

        def die(self, attacker=None):
            self.hp = 0

        def set_player(self, player):
            self.player = player

    return _U()


def test_parse_burst_args():
    assert Skill.parse_burst_args(["burst", "mdg", "5", "(interval", "0.2)", "(window", "1)"]) == (
        "mdg",
        5,
        0.2,
        1.0,
        None,
    )
    assert Skill.parse_burst_args(["burst", "rdg", "3"]) == ("rdg", 3, 0.25, 0.5, None)
    assert Skill.parse_burst_args(
        ["burst", "mdg", "5", "(delays", "0", "0.55", "1.10", "1.40", "1.65)", "(window", "2)"]
    ) == ("mdg", 5, 0.25, 2.0, [0.0, 0.55, 1.1, 1.4, 1.65])


def test_burst_schedules_five_hits():
    scheduled = []

    class _World:
        def schedule_after(self, delay, fn):
            scheduled.append((delay, fn))

    caster = types.SimpleNamespace(
        world=_World(),
        player=_StubPlayer("hero"),
        hp=100,
        mdg=8 * PRECISION,
        mdg_vs={},
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        x=0,
        y=0,
        is_an_enemy=lambda t: True,
    )

    hits = []

    def receive_hit(damage, attacker, notify=True, is_melee=None, **kw):
        hits.append((damage, is_melee))

    target = types.SimpleNamespace(
        player=_StubPlayer("enemy"),
        hp=100,
        is_vulnerable=True,
        type_name="footman",
        expanded_is_a=set(),
        armor="",
        _armor_instance=None,
        receive_hit=receive_hit,
    )

    Skill.schedule_skill_burst(caster, target, "mdg", 5, 0.2, Skill)

    assert len(scheduled) == 4
    assert len(hits) == 1
    for _, fn in scheduled:
        fn()
    assert len(hits) == 5
    assert all(d == 8 * PRECISION for d, _ in hits)
    assert all(m is True for _, m in hits)


def test_burst_schedules_custom_rhythm():
    scheduled = []

    class _World:
        def schedule_after(self, delay, fn):
            scheduled.append((delay, fn))

    caster = types.SimpleNamespace(
        world=_World(),
        player=_StubPlayer("hero"),
        hp=100,
        mdg=6 * PRECISION,
        mdg_vs={},
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        x=0,
        y=0,
        is_an_enemy=lambda t: True,
    )

    hits = []
    target = types.SimpleNamespace(
        player=_StubPlayer("enemy"),
        hp=100,
        is_vulnerable=True,
        type_name="footman",
        expanded_is_a=set(),
        armor="",
        _armor_instance=None,
        receive_hit=lambda damage, attacker, notify=True, is_melee=None, **kw: hits.append((damage, is_melee)),
    )

    Skill.schedule_skill_burst(
        caster, target, "mdg", 5, 0.25, Skill, [0.0, 0.55, 1.10, 1.40, 1.65]
    )

    assert [delay for delay, _ in scheduled] == [550, 1100, 1400, 1650]
    assert len(hits) == 1
    for _, fn in scheduled:
        fn()
    assert hits == [(6 * PRECISION, True)] * 5


def test_burst_use_order_targets_unit():
    from soundrts.worldorders.skills import UseOrder

    order = UseOrder.__new__(UseOrder)
    order.type = types.SimpleNamespace(effect=["burst", "mdg", "5"], effect_target=["ask"])
    assert order.nb_args == 1
    assert order._target_type == "unit"


def test_use_order_effect_range_includes_unit_radii():
    from soundrts.worldorders.skills import UseOrder

    order = UseOrder.__new__(UseOrder)
    order.type = types.SimpleNamespace(effect_range=PRECISION)
    order.unit = types.SimpleNamespace(radius=100)
    order.target = types.SimpleNamespace(radius=200)

    assert order._effect_range_to_target() == PRECISION + 300

    order.target = types.SimpleNamespace()
    assert order._effect_range_to_target() == PRECISION


def test_burst_execute_returns_false_for_square_target():
    class _BurstSkill(Skill):
        type_name = "burst_test"
        effect = ["burst", "mdg", "5"]

    caster = types.SimpleNamespace(is_an_enemy=lambda target: False)
    square = types.SimpleNamespace(x=0, y=0)
    assert _BurstSkill.execute_skill(caster, square, None) is False


def test_parse_harm_area_and_target_args():
    assert Skill.parse_harm_area_args(["harm_area", "50", "3"]) == ("fixed", 50, 3 * PRECISION)
    assert Skill.parse_harm_area_args(["harm_area", "mdg", "3"]) == ("mdg", 3 * PRECISION)
    assert Skill.parse_harm_target_args(["harm_target", "60"]) == ("fixed", 60)
    assert Skill.parse_harm_target_args(["harm_target", "rdg"]) == ("rdg", None)


def test_harm_target_mdg_uses_combat_pipeline():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    hits = []

    rules.load(
        "def skill_sweep\nclass skill\nmdg 12\n"
        "def footman\nclass soldier\n"
    )
    skill_cls = rules.unit_class("skill_sweep")

    caster = types.SimpleNamespace(
        player=hero_p,
        world=types.SimpleNamespace(time=0, treaty_until_time=0),
        mdg=3 * PRECISION,
        mdg_vs={},
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        x=0,
        y=0,
        is_an_enemy=lambda u: u.player is enemy_p,
    )
    target = types.SimpleNamespace(
        player=enemy_p,
        hp=100 * PRECISION,
        is_vulnerable=True,
        place=None,
        type_name="footman",
        expanded_is_a=set(),
        armor="",
        _armor_instance=None,
    )

    def receive_hit(damage, attacker, notify=True, is_melee=None, **kw):
        hits.append((damage, is_melee))

    target.receive_hit = receive_hit

    assert Skill._skill_combat_harm(caster, target, "mdg", skill_cls) is True
    assert hits == [(12 * PRECISION, True)]


def test_skill_combat_proxy_merges_skill_stats():
    from soundrts.skill_combat import SkillCombatProxy

    rules.load(
        "def skill_sweep\nclass skill\n"
        "mdg 12\n"
        "mdg_splash 6\n"
        "mdg_radius 1.5\n"
        "mdg_range 8\n"
        "def footman\nclass soldier\n"
    )
    skill_cls = rules.unit_class("skill_sweep")
    caster = types.SimpleNamespace(
        mdg=3 * PRECISION,
        rdg=0,
        mdg_vs={},
        rdg_vs={},
        mdg_splash=0,
        rdg_splash=0,
        mdg_radius=0,
        rdg_radius=0,
        mdg_range=0,
        rdg_range=0,
        player=_StubPlayer("hero"),
        world=types.SimpleNamespace(time=0),
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        x=0,
        y=0,
        is_an_enemy=lambda u: True,
    )
    proxy = SkillCombatProxy(caster, skill_cls)
    assert proxy.mdg == 12 * PRECISION
    assert proxy.mdg_splash == 6 * PRECISION
    assert proxy.mdg_radius == to_int("1.5")
    assert proxy.mdg_range == 8 * PRECISION


def test_skill_combat_proxy_exposes_entity_visibility_state():
    from soundrts.skill_combat import SkillCombatProxy

    caster = types.SimpleNamespace(
        mdg=3 * PRECISION,
        mdg_vs={},
        player=_StubPlayer("hero"),
        world=types.SimpleNamespace(time=0),
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        x=0,
        y=0,
        place="p",
        time_limit=None,
        harm_level=0,
        menace=7,
        is_invisible=True,
        is_cloaked=True,
        airground_type="ground",
        custom_flag="delegated",
        is_an_enemy=lambda u: True,
    )

    proxy = SkillCombatProxy(caster, Skill)
    assert proxy.is_invisible is True
    assert proxy.is_cloaked is True
    assert proxy.place == "p"
    assert proxy.time_limit is None
    assert proxy.harm_level == 0
    assert proxy.menace == 7
    assert proxy.airground_type == "ground"
    assert proxy.custom_flag == "delegated"


def test_skill_combat_attrs_on_skill_rules():
    r = Rules()
    r.load(
        "def sweep\nclass skill\n"
        "effect harm_area mdg 3\n"
        "mdg 12\n"
        "mdg_splash 6\n"
        "mdg_radius 1.5\n"
        "mdg_range 8\n"
        "def footman\nclass soldier\n"
    )
    sweep = r.unit_class("sweep")
    assert sweep.mdg == 12 * PRECISION
    assert sweep.mdg_splash == 6 * PRECISION
    assert sweep.mdg_radius == to_int("1.5")
    assert sweep.mdg_range == 8 * PRECISION


def test_harm_area_mdg_hits_via_combat_pipeline():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    hits = []

    near = types.SimpleNamespace(
        player=enemy_p,
        hp=100 * PRECISION,
        is_vulnerable=True,
        x=0,
        y=0,
        type_name="footman",
        expanded_is_a=set(),
        armor="",
        _armor_instance=None,
    )

    def receive_hit(damage, attacker, notify=True, is_melee=None, **kw):
        hits.append((damage, is_melee))

    near.receive_hit = receive_hit

    from soundrts.lib.nofloat import int_distance

    world = types.SimpleNamespace(
        time=0,
        treaty_until_time=0,
        get_objects2=lambda x, y, r, filter=None, skip_cache=False: [
            u for u in [near] if int_distance(x, y, u.x, u.y) <= r and filter(u)
        ],
    )
    caster = types.SimpleNamespace(
        player=hero_p,
        world=world,
        x=0,
        y=0,
        mdg=9 * PRECISION,
        mdg_vs={},
        type_name="hero",
        expanded_is_a=set(),
        id="h1",
        is_an_enemy=lambda u: u.player is enemy_p,
    )

    rules.load(
        "def skill_aoe_mdg\nclass skill\neffect harm_area mdg 3\n"
        "def footman\nclass soldier\n"
    )
    skill_cls = rules.unit_class("skill_aoe_mdg")
    target = types.SimpleNamespace(x=0, y=0)

    assert skill_cls._execute_harm_area(caster, target, world) is True
    assert hits == [(9 * PRECISION, True)]


def test_harm_target_single_enemy():
    _load_wuxia_rules()
    skill_cls = rules.unit_class("skill_lipi")
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")

    caster = types.SimpleNamespace(
        player=hero_p,
        world=types.SimpleNamespace(time=0, treaty_until_time=0),
        is_an_enemy=lambda u: u.player is enemy_p,
    )
    target = types.SimpleNamespace(
        player=enemy_p,
        hp=80 * PRECISION,
        is_vulnerable=True,
        place=None,
    )
    target.die = lambda _a=None: setattr(target, "hp", 0)

    assert skill_cls._execute_harm_target(caster, target, None) is True
    assert target.hp == (80 - 60) * PRECISION


def test_harm_area_hits_enemies_in_radius():
    _load_wuxia_rules()
    skill_cls = rules.unit_class("skill_heng_sao")
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")

    near1 = types.SimpleNamespace(
        player=enemy_p, hp=100 * PRECISION, is_vulnerable=True, x=0, y=0
    )
    near2 = types.SimpleNamespace(
        player=enemy_p, hp=100 * PRECISION, is_vulnerable=True, x=500, y=0
    )
    far = types.SimpleNamespace(
        player=enemy_p, hp=100 * PRECISION, is_vulnerable=True, x=5000, y=0
    )
    for u in (near1, near2, far):
        u.die = lambda _a=None, u=u: setattr(u, "hp", 0)

    from soundrts.lib.nofloat import int_distance

    def get_objects2(x, y, r, filter=None, skip_cache=False):
        return [
            u
            for u in (near1, near2, far)
            if int_distance(x, y, u.x, u.y) <= r and filter(u)
        ]

    world = types.SimpleNamespace(
        time=0,
        treaty_until_time=0,
        get_objects2=get_objects2,
    )
    caster = types.SimpleNamespace(
        player=hero_p,
        world=world,
        is_an_enemy=lambda u: u.player is enemy_p,
    )
    target = types.SimpleNamespace(x=0, y=0)

    assert skill_cls._execute_harm_area(caster, target, world) is True
    assert near1.hp == 50 * PRECISION
    assert near2.hp == 50 * PRECISION
    assert far.hp == 100 * PRECISION


def test_reflect_returns_damage():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    defender = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION)
    attacker = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION, mdg=10 * PRECISION)

    class _ReflectBuff:
        reflect_percent = 100

    defender._buffs = [_ReflectBuff()]
    defender.receive_hit(10 * PRECISION, attacker, notify=False, is_melee=True)
    assert defender.hp == 90 * PRECISION
    assert attacker.hp == 90 * PRECISION


def test_reflect_no_infinite_loop():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    defender = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION)
    attacker = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION, mdg=10 * PRECISION)

    class _ReflectBuff:
        reflect_percent = 100

    defender._buffs = [_ReflectBuff()]
    attacker._buffs = [_ReflectBuff()]
    defender.receive_hit(10 * PRECISION, attacker, notify=False, is_melee=True)
    assert defender.hp == 90 * PRECISION
    assert attacker.hp == 90 * PRECISION


def test_active_trigger_skill_fires_after_attack():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    attacker = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION)
    attacker.active_trigger_skills = ("skill_proc",)

    class _ProcSkill(Skill):
        type_name = "skill_proc"
        effect = ["harm_target", "5"]
        effect_target = ["ask"]
        active_trigger_rate = 100

    attacker.world.unit_class = lambda name: _ProcSkill if name == "skill_proc" else None
    defender.world = attacker.world

    defender.receive_hit(10 * PRECISION, attacker, notify=False, is_melee=True)
    assert defender.hp == 85 * PRECISION


def test_passive_trigger_skill_fires_after_damage():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    defender = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION)
    attacker = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender.passive_trigger_skills = ("skill_counter",)

    class _CounterSkill(Skill):
        type_name = "skill_counter"
        effect = ["harm_target", "5"]
        effect_target = ["ask"]
        passive_trigger_rate = 100

    defender.world.unit_class = lambda name: _CounterSkill if name == "skill_counter" else None
    attacker.world = defender.world

    defender.receive_hit(10 * PRECISION, attacker, notify=False, is_melee=True)
    assert defender.hp == 90 * PRECISION
    assert attacker.hp == 95 * PRECISION


def test_attack_start_trigger_skill_fires_before_hit():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    attacker = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION)
    attacker.attack_trigger_skills = ("skill_start",)

    class _StartSkill(Skill):
        type_name = "skill_start"
        effect = ["harm_target", "5"]
        effect_target = ["ask"]
        active_trigger_rate = 100

    attacker.world.unit_class = lambda name: _StartSkill if name == "skill_start" else None
    defender.world = attacker.world

    assert attacker._trigger_attack_start_skills(defender, is_melee=True, replace=False) is True
    assert defender.hp == 95 * PRECISION


def test_attack_replace_skill_skips_normal_attack_when_triggered():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    attacker = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION)
    attacker.attack_replace_skills = ("skill_replace",)

    class _ReplaceSkill(Skill):
        type_name = "skill_replace"
        effect = ["harm_target", "7"]
        effect_target = ["ask"]
        active_trigger_rate = 100

    attacker.world.unit_class = lambda name: _ReplaceSkill if name == "skill_replace" else None
    defender.world = attacker.world

    assert attacker._trigger_attack_start_skills(defender, is_melee=True, replace=True) is True
    assert defender.hp == 93 * PRECISION


def test_attack_start_buff_applies_to_self_before_hit():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    attacker = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION)
    attacker.attack_trigger_buffs = ("b_before",)

    class _Buff:
        mdg_trigger_rate = 100
        rdg_trigger_rate = 0

    attacker.world.unit_class = lambda name: _Buff if name == "b_before" else None
    defender.world = attacker.world

    assert attacker._trigger_attack_start_buffs(defender, is_melee=True, replace=False) is True
    assert attacker._buffs == [("b_before", attacker)]
    assert defender._buffs == []


def test_attack_replace_debuff_applies_to_target_and_replaces_attack():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    attacker = _make_combat_unit(hero_p, enemy_player=enemy_p, hp=100 * PRECISION, mdg=10 * PRECISION)
    defender = _make_combat_unit(enemy_p, enemy_player=hero_p, hp=100 * PRECISION)
    attacker.attack_replace_debuffs = ("b_mark",)

    class _Debuff:
        mdg_trigger_rate = 100
        rdg_trigger_rate = 0

    attacker.world.unit_class = lambda name: _Debuff if name == "b_mark" else None
    defender.world = attacker.world

    assert attacker._trigger_attack_start_buffs(defender, is_melee=True, replace=True) is True
    assert defender._buffs == [("b_mark", attacker)]
    assert attacker._buffs == []


def test_push_moves_target():
    _load_wuxia_rules()
    skill_cls = rules.unit_class("skill_moli_dan")
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")

    moved = {}

    def move_to(place, x, y, o=None):
        moved["x"] = x
        moved["y"] = y

    place = types.SimpleNamespace(
        find_free_space_for=lambda o, x, y: (x, y),
    )
    target = types.SimpleNamespace(
        player=enemy_p,
        hp=100,
        is_vulnerable=True,
        x=5 * PRECISION,
        y=0,
        place=place,
        move_to=move_to,
    )
    caster = types.SimpleNamespace(
        player=hero_p,
        x=0,
        y=0,
        o=90,
        is_an_enemy=lambda u: u.player is enemy_p,
    )

    assert skill_cls._execute_push(caster, target, None) is True
    assert moved["x"] == 10 * PRECISION
    assert moved["y"] == 0


def test_triggered_push_effect_range_includes_unit_radii():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    moved = []

    class _PushSkill(Skill):
        effect = ["push", "1"]
        effect_range = PRECISION

    place = types.SimpleNamespace(find_free_space_for=lambda o, x, y: (x, y))
    caster = types.SimpleNamespace(
        player=hero_p,
        x=0,
        y=0,
        o=90,
        radius=100,
        is_an_enemy=lambda u: u.player is enemy_p,
    )
    target = types.SimpleNamespace(
        player=enemy_p,
        hp=100,
        is_vulnerable=True,
        x=1209,
        y=0,
        radius=200,
        place=place,
        move_to=lambda place, x, y, o=None: moved.append((x, y)),
    )

    assert _PushSkill._execute_push(caster, target, None) is True
    assert moved

    target.x = 1301
    moved.clear()
    assert _PushSkill._execute_push(caster, target, None) is False
    assert moved == []


def test_wuxia_rules_parse():
    r = Rules()
    r.load(WUXIA_RULES)
    assert r.unit_class("skill_jifengci") is not None
    assert r.unit_class("b_douzhuan").reflect_percent == 100
    assert r.unit_class("wuxia_hero") is not None
    burst = r.get("skill_jifengci", "effect")
    assert burst[0] == "burst"
    assert burst[1] == "mdg"


def test_skill_range_includes_unit_radii():
    caster = types.SimpleNamespace(
        player=_StubPlayer("hero"),
        world=types.SimpleNamespace(),
        id="h1",
        type_name="hero",
        expanded_is_a=set(),
        x=0,
        y=0,
        radius=100,
    )
    skill_cls = types.SimpleNamespace(mdg_range=PRECISION, rdg_range=0)
    proxy = SkillCombatProxy(caster, skill_cls)

    target = types.SimpleNamespace(x=1209, y=0, radius=200)
    assert proxy.in_skill_range(target, "mdg") is True

    target.x = 1301
    assert proxy.in_skill_range(target, "mdg") is False


def test_skill_can_harm_defaults_to_enemy_only():
    from soundrts.worldunit.world_public_method import skill_can_harm

    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    ally_p = _StubPlayer("ally")

    class _Skill(Skill):
        type_name = "test_skill"

    caster = types.SimpleNamespace(player=hero_p, is_an_enemy=lambda u: u.player is enemy_p)
    enemy = types.SimpleNamespace(
        player=enemy_p, hp=100, is_vulnerable=True, type_name="footman"
    )
    ally = types.SimpleNamespace(
        player=ally_p, hp=100, is_vulnerable=True, type_name="footman"
    )

    assert skill_can_harm(caster, _Skill, enemy) is True
    assert skill_can_harm(caster, _Skill, ally) is False


def test_harm_area_respects_harm_target_type_ground():
    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")

    class _AoeSkill(Skill):
        type_name = "aoe_ground"
        effect = ["harm_area", "50", "3"]
        harm_target_type = ["enemy", "ground", "unit"]

    ground = types.SimpleNamespace(
        player=enemy_p,
        hp=100 * PRECISION,
        is_vulnerable=True,
        is_a_unit=True,
        airground_type="ground",
        type_name="footman",
        x=0,
        y=0,
    )
    air = types.SimpleNamespace(
        player=enemy_p,
        hp=100 * PRECISION,
        is_vulnerable=True,
        is_a_unit=True,
        airground_type="air",
        type_name="dragon",
        x=100,
        y=0,
    )
    for u in (ground, air):
        u.die = lambda _a=None, u=u: setattr(u, "hp", 0)

    from soundrts.lib.nofloat import int_distance

    def get_objects2(x, y, r, filter=None, skip_cache=False):
        return [
            u
            for u in (ground, air)
            if int_distance(x, y, u.x, u.y) <= r and filter(u)
        ]

    world = types.SimpleNamespace(time=0, treaty_until_time=0, get_objects2=get_objects2)
    caster = types.SimpleNamespace(
        player=hero_p,
        world=world,
        is_an_enemy=lambda u: u.player is enemy_p,
    )
    target = types.SimpleNamespace(x=0, y=0)

    assert _AoeSkill._execute_harm_area(caster, target, world) is True
    assert ground.hp == 50 * PRECISION
    assert air.hp == 100 * PRECISION


def test_burst_respects_harm_target_type_on_each_hit():
    class _BurstSkill(Skill):
        type_name = "burst_ground"
        effect = ["burst", "mdg", "3"]
        harm_target_type = ["enemy", "ground", "unit"]

    hero_p = _StubPlayer("hero")
    enemy_p = _StubPlayer("enemy")
    caster = types.SimpleNamespace(
        player=hero_p,
        is_an_enemy=lambda t: t.player is enemy_p,
    )

    air_target = types.SimpleNamespace(
        player=enemy_p,
        hp=100,
        is_vulnerable=True,
        is_a_unit=True,
        airground_type="air",
        type_name="dragon",
    )
    ground_target = types.SimpleNamespace(
        player=enemy_p,
        hp=100,
        is_vulnerable=True,
        is_a_unit=True,
        airground_type="ground",
        type_name="footman",
    )

    assert _BurstSkill._is_burst_necessary(caster, air_target) is False
    assert _BurstSkill._is_burst_necessary(caster, ground_target) is True
    assert _BurstSkill._execute_burst(caster, air_target, None) is False
