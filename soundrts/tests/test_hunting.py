"""帝国时代式狩猎：可狩猎动物、尸体采集、受击逃跑。"""
from __future__ import annotations

import types
from pathlib import Path

import soundrts.worldunit  # noqa: F401 — 解开循环导入

from soundrts.worldunit import world_ai_decision as wad
from soundrts.worldunit.worldworker import Worker


class _HuntableTarget:
    is_huntable = 1
    hp = 5

    def __init__(self):
        self.player = types.SimpleNamespace(neutral=True)


def test_attack_order_completes_when_huntable_target_gone():
    """击杀动物后目标消失：应 complete，不要 order_impossible 滴声。"""
    from soundrts.worldorders.movement import AttackOrder

    class _Player:
        def updated_target(self, target):
            return None  # 目标已删除

    class _Unit:
        notifications = []
        orders = []
        is_idle = True
        action = None
        distance_to_goal = 0

        def __init__(self):
            self.player = _Player()
            self.notifications = []

        def notify(self, msg, *_a, **_k):
            self.notifications.append(msg)

        def is_an_enemy(self, _t):
            return True

        def _near_enough_to_aim(self, _t):
            return True

    unit = _Unit()
    order = AttackOrder(unit, ["deer1"])
    order.target = types.SimpleNamespace(id="deer1", hp=0, is_vulnerable=True)
    unit.orders = [order]
    order.execute()

    assert order.is_complete
    assert not getattr(order, "is_impossible", False)
    assert "order_impossible" not in unit.notifications
    worker = Worker.__new__(Worker)
    worker._basic_skills = {"go", "attack", "gather", "repair", "block", "join_group", "pickup", "drop"}
    worker.orders = []
    worker.player = types.SimpleNamespace(get_object_by_id=lambda _id: _HuntableTarget())

    assert worker.get_default_order(99) == "go"


def test_is_an_enemy_honors_imperative_attack_order():
    src = Path("soundrts/worldunit/worldcreature.py").read_text(encoding="utf-8")
    assert "_player_ordered_attack_on(c)" in src
    assert 'kw == "attack"' in src or 'keyword == "attack"' in src


def test_flee_from_attacker_moves_away():
    sq_far = types.SimpleNamespace(id="far", x=5000, y=0)
    sq_near = types.SimpleNamespace(id="near", x=100, y=0)
    exit_far = types.SimpleNamespace(other_side=types.SimpleNamespace(place=sq_far))
    exit_near = types.SimpleNamespace(other_side=types.SimpleNamespace(place=sq_near))

    class _Animal:
        speed = 2
        place = types.SimpleNamespace(exits=[exit_near, exit_far])
        last_attacker = types.SimpleNamespace(place=sq_near, x=0, y=0)
        orders_taken = []

        def take_order(self, cmd, imperative=False):
            self.orders_taken.append((cmd, imperative))

        def notify(self, *_args, **_kwargs):
            pass

    animal = _Animal()
    assert wad.CreatureAIDecision._flee_from_attacker(animal) is True
    assert animal.orders_taken[0][0] == ["go", "far"]
    assert animal.orders_taken[0][1] is True
    assert animal.last_attacker is None


def test_flee_on_hit_clears_attacker_so_no_perpetual_flee():
    """One hit → one flee; sticky last_attacker must not re-flee every decide."""
    src = Path("soundrts/worldunit/world_ai_decision.py").read_text(encoding="utf-8")
    assert "self.last_attacker = None" in src
    block = src[src.find("def _flee_from_attacker") : src.find("def _is_wildlife_unit")]
    assert "last_attacker = None" in block


def test_rules_define_hunting_units():
    text = Path("res/rules.txt").read_text(encoding="utf-8")
    for name in ("def deer", "def sheep", "def boar", "def food_carcass"):
        assert name in text
    assert "is_huntable 1" in text
    assert "agro_on_sight 0" in text
    assert "food_deposit food_carcass" in text
    assert "can_gather_deposit goldmine wood orchard food_carcass" in text
    assert "can_gather_building farm" in text


def test_hunting_animals_wander_range_loaded():
    from soundrts.definitions import Rules, _get_base_classes

    r = Rules()
    r.load(Path("res/rules.txt").read_text(encoding="utf-8"), base_classes=_get_base_classes())
    for animal in ("deer", "sheep", "boar"):
        cls = r.unit_class(animal)
        assert cls.wander_range == 12000
        assert int(cls.agro_on_sight) == 0


def test_randommap_includes_hunting_spawns(monkeypatch):
    # Hunting spawns only exist when the active rules define huntable animals.
    # Force base-game rules (no mod) so the assertion is environment-independent.
    from soundrts import config

    monkeypatch.setattr(config, "mods", "", raising=False)

    from soundrts.randommap import RandomMapConfig, generate_definition

    text, _ = generate_definition(RandomMapConfig(seed=42))
    assert "computer_only 0 0 neutral" in text
    assert any(animal in text for animal in ("deer", "sheep", "boar"))


def test_wildlife_wander_moves_within_leash():
    sq_a = types.SimpleNamespace(id="a", x=0, y=0)
    sq_b = types.SimpleNamespace(id="b", x=5000, y=0)
    exit_b = types.SimpleNamespace(other_side=types.SimpleNamespace(place=sq_b))

    class _Deer:
        is_huntable = 1
        herdable = 0
        wander_range = 12000
        speed = 2
        orders = []
        last_attacker = None
        _herd_leader = None
        x = 0
        y = 0
        place = types.SimpleNamespace(exits=[exit_b])
        orders_taken = []

        def take_order(self, cmd, imperative=False):
            self.orders_taken.append((cmd, imperative))

    deer = _Deer()
    deer.world = types.SimpleNamespace(
        random=types.SimpleNamespace(
            randint=lambda a, b: 0,
            choice=lambda items: items[0],
        )
    )
    assert wad.CreatureAIDecision._wildlife_wander(deer) is True
    assert deer.orders_taken[0][0] == ["go", "b"]
    assert deer.orders_taken[0][1] is True


def test_wildlife_does_not_wander_while_aggroed():
    deer = types.SimpleNamespace(
        is_huntable=1,
        herdable=0,
        last_attacker=object(),
        player=types.SimpleNamespace(neutral=True),
        speed=2,
        place=types.SimpleNamespace(exits=[]),
        orders=[],
        _herd_leader=None,
    )
    assert wad.CreatureAIDecision._wildlife_wander(deer) is False


def _guard_decide_stub(*, agro_on_sight, last_attacker=None):
    class _Guard:
        _last_decide_time = 0
        _next_decide_time = 0
        _decision_cache = {}
        _decision_cache_bucket = -1
        _cached_has_attack = True
        _has_yielded = False
        herdable = 0
        is_huntable = 1
        last_attacker = None
        orders = []
        ai_mode = "guard"
        counterattack_enabled = True
        speed = 10
        auto_explore = False
        is_inside = False
        agro_on_sight = 1

        decide = wad.CreatureAIDecision.decide
        _flee_on_hit_enabled = lambda self: False
        _has_pursue_attacker = lambda self: False
        _wildlife_wander = lambda self: False
        _must_hold = lambda self: False

        def __init__(self):
            self.world = types.SimpleNamespace(time=10_000)
            self.id = id(self)
            self.place = types.SimpleNamespace(
                objects=[], neighbors=[], strict_neighbors=[], exits=[]
            )
            self.action = None
            self.attacks = []
            self.stand_ground_calls = 0
            self.player = types.SimpleNamespace(
                smart_units=False,
                enemy_menace=lambda _p: 0,
                balance=lambda *a, **k: 10,
            )

        def _attack(self, target):
            self.attacks.append(target)

        def _stand_ground_target(self):
            self.stand_ground_calls += 1
            return types.SimpleNamespace(id="nearby")

    u = _Guard()
    u.agro_on_sight = agro_on_sight
    u.last_attacker = last_attacker
    return u


def test_agro_on_sight_zero_skips_stand_ground_until_hit(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    u = _guard_decide_stub(agro_on_sight=0)
    wad.CreatureAIDecision.decide(u)
    assert u.stand_ground_calls == 0
    assert u.attacks == []


def test_agro_on_sight_zero_counterattacks_last_attacker(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    foe = types.SimpleNamespace(id="hitter", place=object(), hp=10)
    u = _guard_decide_stub(agro_on_sight=0, last_attacker=foe)
    wad.CreatureAIDecision.decide(u)
    assert u.stand_ground_calls == 0
    assert u.attacks == [foe]


def test_agro_on_sight_one_uses_stand_ground_when_formations_on(monkeypatch):
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    u = _guard_decide_stub(agro_on_sight=1)
    wad.CreatureAIDecision.decide(u)
    assert u.stand_ground_calls == 1
    assert len(u.attacks) == 1


def test_agro_on_sight_zero_is_not_pack_notified():
    from soundrts.worldunit.worldcreature import Creature

    attacker = object()
    player = object()
    place = types.SimpleNamespace(objects=[])
    hit = Creature.__new__(Creature)
    hit.player = player
    other = Creature.__new__(Creature)
    other.player = player
    other.ai_mode = "guard"
    other.counterattack_enabled = True
    other.agro_on_sight = 0
    other.last_attacker = None
    ally = Creature.__new__(Creature)
    ally.player = player
    ally.ai_mode = "guard"
    ally.counterattack_enabled = True
    ally.agro_on_sight = 1
    ally.last_attacker = None
    place.objects = [hit, other, ally]
    Creature._notify_units_in_place(hit, place, attacker)
    assert other.last_attacker is None
    assert ally.last_attacker is attacker


def test_wildlife_wander_returns_toward_origin_when_too_far():
    origin = types.SimpleNamespace(id="home", x=0, y=0)
    sq_far = types.SimpleNamespace(id="far", x=20000, y=0)

    class _Deer:
        is_huntable = 1
        herdable = 0
        wander_range = 12000
        speed = 2
        orders = []
        last_attacker = None
        _herd_leader = None
        _wander_origin = (origin, 0, 0)
        x = 20000
        y = 0
        place = types.SimpleNamespace(exits=[])
        orders_taken = []

        def take_order(self, cmd, imperative=False):
            self.orders_taken.append((cmd, imperative))

    deer = _Deer()
    deer.world = types.SimpleNamespace(
        random=types.SimpleNamespace(
            randint=lambda a, b: 0,
            choice=lambda items: items[0],
        )
    )
    assert wad.CreatureAIDecision._wildlife_wander(deer) is True
    assert deer.orders_taken[0][0] == ["go", "home"]


def test_computer_ai_hunts_when_no_gather_target():
    src = Path("soundrts/worldplayercomputer.py").read_text(encoding="utf-8")
    assert "def _worker_can_hunt" in src
    assert "def _huntable_food_deposit_types" in src
    assert "def _choose_hunt_target" in src
    assert "hunt_target = self._choose_hunt_target(u)" in src
    assert 'u.take_order(["attack", hunt_target.id], imperative=True)' in src
    assert "def _try_start_boar_lure" in src
    assert "def _maintain_boar_lure" in src
    assert "self._ensure_boar_lure()" in src
    assert '"food_carcass" in deposits' not in src


def test_computer_ai_herding_helpers():
    src = Path("soundrts/worldplayercomputer.py").read_text(encoding="utf-8")
    assert "def _worker_can_herd" in src
    assert "def _choose_herd_target" in src
    assert "def _maintain_worker_herding" in src
    assert "def _herded_animals" in src
    assert "herd_target = self._choose_herd_target(u)" in src
    assert 'u.take_order(["herd", herd_target.id], imperative=True)' in src
    assert "getattr(o, \"herdable\", 0)" in src
    assert "_worker_can_herd(worker)" in src


def test_attack_order_completes_when_huntable_target_gone():
    """击杀动物后目标消失：应 complete，不要 order_impossible 滴声。"""
    from soundrts.worldorders.movement import AttackOrder

    class _Player:
        def updated_target(self, target):
            return None  # 目标已删除

    class _Unit:
        is_idle = True
        action = None
        distance_to_goal = 0

        def __init__(self):
            self.player = _Player()
            self.notifications = []
            self.orders = []

        def notify(self, msg, *_a, **_k):
            self.notifications.append(msg)

        def is_an_enemy(self, _t):
            return True

        def _near_enough_to_aim(self, _t):
            return True

    unit = _Unit()
    order = AttackOrder(unit, ["deer1"])
    order.target = types.SimpleNamespace(id="deer1", hp=0, is_vulnerable=True)
    unit.orders = [order]
    order.execute()

    assert order.is_complete
    assert not getattr(order, "is_impossible", False)
    assert "order_impossible" not in unit.notifications
