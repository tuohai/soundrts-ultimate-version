"""追击模式：AttackAction 跨格连续跟随，不靠自动 go 命令跳格。"""
from __future__ import annotations

import types

from soundrts.worldaction import AttackAction


def test_attack_action_chase_moves_toward_exit_without_completing():
    enemy_place = types.SimpleNamespace(id="b", x=2000, y=0, objects=[])
    exit_other = types.SimpleNamespace(place=enemy_place)
    exit_obj = types.SimpleNamespace(
        place=None,  # filled below
        other_side=exit_other,
        x=1000,
        y=0,
    )
    my_place = types.SimpleNamespace(id="a", x=0, y=0, objects=[], neighbors=[enemy_place])
    exit_obj.place = my_place

    enemy = types.SimpleNamespace(
        id="e1",
        place=enemy_place,
        hp=50,
        x=2000,
        y=0,
        capture_hp_threshold=0,
        player=object(),
    )
    enemy_place.objects = [enemy]

    moves = []

    class _Unit:
        ai_mode = "chase"
        speed = 10
        place = my_place
        action = None
        walked = []
        orders = []

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return True

        def next_stage(self, target):
            assert target is enemy
            return exit_obj

        def go_to_xy(self, x, y):
            moves.append((x, y))

        def action_reach_and_aim(self):
            raise AssertionError("should not aim while target is out of square")

        def aim(self, _t):
            raise AssertionError("should not aim out of range")

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()

    assert unit.action is action
    assert not moves or moves == [(enemy_place.x, enemy_place.y)]
    assert moves == [(enemy_place.x, enemy_place.y)]


def test_attack_action_non_chase_completes_when_target_leaves_square():
    other = types.SimpleNamespace(id="b", objects=[])
    enemy = types.SimpleNamespace(
        id="e1",
        place=other,
        hp=50,
        capture_hp_threshold=0,
        player=object(),
    )
    my_place = types.SimpleNamespace(id="a", objects=[])

    class _Unit:
        ai_mode = "offensive"
        speed = 10
        place = my_place
        action = None
        walked = []
        orders = []

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return True

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()

    assert unit.action is None


def test_attack_action_chase_clears_hold_before_cross_square():
    """追击跨格前必须清 position_to_hold，否则 _must_hold 会把单位锁在原格。"""
    enemy_place = types.SimpleNamespace(id="b", x=2000, y=0, objects=[])
    exit_other = types.SimpleNamespace(place=enemy_place)
    my_place = types.SimpleNamespace(id="a", x=0, y=0, objects=[], neighbors=[enemy_place])

    class _HoldSquare:
        def contains(self, x, y):
            return True

    exit_obj = types.SimpleNamespace(
        place=my_place,
        other_side=exit_other,
        x=1000,
        y=0,
    )
    enemy = types.SimpleNamespace(
        id="e1",
        place=enemy_place,
        hp=50,
        x=2000,
        y=0,
        capture_hp_threshold=0,
        player=object(),
    )
    enemy_place.objects = [enemy]

    class _Unit:
        ai_mode = "chase"
        speed = 10
        place = my_place
        action = None
        walked = []
        orders = []
        position_to_hold = _HoldSquare()

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return True

        def next_stage(self, target):
            return exit_obj

        def go_to_xy(self, x, y):
            self.last_xy = (x, y)

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()

    assert unit.position_to_hold is None
    assert unit.last_xy == (enemy_place.x, enemy_place.y)
    assert unit.action is action


def test_must_hold_excludes_chase_mode():
    from soundrts.worldunit.world_movement import CreatureMovement

    class _Square:
        def contains(self, x, y):
            return True

    class _Unit:
        player = types.SimpleNamespace(smart_units=False)
        ai_mode = "chase"
        position_to_hold = _Square()
        x = y = 0
        _must_hold = CreatureMovement._must_hold

    assert _Unit()._must_hold() is False

    unit = _Unit()
    unit.ai_mode = "offensive"
    assert unit._must_hold() is True
    from pathlib import Path

    src = Path("soundrts/worldunit/world_ai_decision.py").read_text(encoding="utf-8")
    start = src.index('if self.ai_mode == "chase":')
    end = src.index('if self.ai_mode == "defensive":', start)
    block = src[start:end]
    assert 'take_order(["go"' not in block
    assert "_pick_chase_enemy" in block
    assert "self._attack(" in block


def test_pick_chase_enemy_ignores_can_attack_same_square_gate():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit import world_ai_decision as wad

    neighbor = types.SimpleNamespace(id="n", objects=[], neighbors=[])
    home = types.SimpleNamespace(id="h", objects=[], neighbors=[neighbor])

    enemy = types.SimpleNamespace(
        id="e1",
        player=object(),
        is_vulnerable=True,
        is_inside=False,
        hp=10,
        place=neighbor,
        x=5000,
        y=0,
    )
    neighbor.objects = [enemy]

    class _Player:
        def known_enemies(self, square):
            if square is neighbor:
                return [enemy]
            return []

        def enemy_menace(self, _p):
            return 0

    class _Unit:
        place = home
        x = 0
        y = 0
        player = _Player()
        ai_mode = "chase"
        speed = 10
        _is_chaseable_enemy = wad.CreatureAIDecision._is_chaseable_enemy
        _pick_chase_enemy = wad.CreatureAIDecision._pick_chase_enemy

        def is_an_enemy(self, _o):
            return True

        def _is_neutral_target(self, _o):
            return False

        def can_attack_if_in_range(self, _o):
            return True

        def can_attack(self, _o):
            return False  # 跨格近战：旧逻辑会过滤掉

    unit = _Unit()
    picked = unit._pick_chase_enemy()
    assert picked is enemy


def test_pursue_attacker_crosses_square_without_chase_mode():
    """野猪等 pursue_attacker：guard 反击也能跨格追，便于诱到 TC。"""
    enemy_place = types.SimpleNamespace(id="b", x=2000, y=0, objects=[])
    exit_other = types.SimpleNamespace(place=enemy_place)
    exit_obj = types.SimpleNamespace(
        place=None,
        other_side=exit_other,
        x=1000,
        y=0,
    )
    my_place = types.SimpleNamespace(id="a", x=0, y=0, objects=[], neighbors=[enemy_place])
    exit_obj.place = my_place

    enemy = types.SimpleNamespace(
        id="e1",
        place=enemy_place,
        hp=50,
        x=2000,
        y=0,
        capture_hp_threshold=0,
        player=object(),
    )
    enemy_place.objects = [enemy]
    moves = []

    class _Unit:
        ai_mode = "guard"
        pursue_attacker = 1
        speed = 10
        place = my_place
        action = None
        walked = []
        orders = []
        position_to_hold = None

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return False  # 中立野生动物：外交上不是敌人

        def next_stage(self, target):
            assert target is enemy
            return exit_obj

        def go_to_xy(self, x, y):
            moves.append((x, y))

        def action_reach_and_aim(self):
            raise AssertionError("should not aim while target is out of square")

        def aim(self, _t):
            raise AssertionError("should not aim out of range")

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()

    assert unit.action is action
    assert moves == [(enemy_place.x, enemy_place.y)]


def test_guard_without_pursue_attacker_stops_when_target_leaves():
    other = types.SimpleNamespace(id="b", objects=[])
    enemy = types.SimpleNamespace(
        id="e1",
        place=other,
        hp=50,
        capture_hp_threshold=0,
        player=object(),
    )
    my_place = types.SimpleNamespace(id="a", objects=[])

    class _Unit:
        ai_mode = "guard"
        pursue_attacker = 0
        speed = 10
        place = my_place
        action = None
        walked = []
        orders = []

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return True

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()

    assert unit.action is None


def test_boar_rules_enable_pursue_attacker():
    from pathlib import Path

    for path in (
        Path("res/rules.txt"),
        Path("mods/aoe2/rules.txt"),
    ):
        if not path.is_file():
            continue
        block = path.read_text(encoding="utf-8").split("def boar", 1)[1].split("def ", 1)[0]
        assert "pursue_attacker 1" in block
        assert "pursue_leash_range 48000" in block
        assert "flee_on_hit 0" in block


def test_pursue_leash_clears_aggro_and_returns_home():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_ai_decision import CreatureAIDecision

    home = types.SimpleNamespace(id="home", x=0, y=0)
    far = types.SimpleNamespace(id="far", x=100000, y=0)
    orders = []

    class _Unit(CreatureAIDecision):
        pursue_attacker = 1
        pursue_leash_range = 48000
        speed = 10
        place = home
        x = 0
        y = 0
        action = None
        _wander_origin = (home, 0, 0)

        def take_order(self, cmd, imperative=False):
            orders.append((cmd, imperative))

    unit = object.__new__(_Unit)
    unit.last_attacker = types.SimpleNamespace(place=far, x=100000, y=0, hp=50)
    assert unit._pursue_target_too_far() is True
    assert unit._clear_pursue_aggro(return_home=True) is True
    assert unit.last_attacker is None
    assert orders == [(["go", "home"], True)]


def test_pursue_leash_unlimited_when_zero():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_ai_decision import CreatureAIDecision

    class _Unit(CreatureAIDecision):
        pursue_attacker = 1
        pursue_leash_range = 0
        place = types.SimpleNamespace(id="a")
        x = 0
        y = 0

    unit = object.__new__(_Unit)
    unit.last_attacker = types.SimpleNamespace(place=object(), x=999999, y=0)
    assert unit._pursue_target_too_far() is False


def test_attack_action_stops_when_pursue_leash_exceeded():
    enemy_place = types.SimpleNamespace(id="b", x=100000, y=0, objects=[])
    my_place = types.SimpleNamespace(id="a", x=0, y=0, objects=[])
    enemy = types.SimpleNamespace(
        id="e1",
        place=enemy_place,
        hp=50,
        x=100000,
        y=0,
        capture_hp_threshold=0,
        player=object(),
    )
    enemy_place.objects = [enemy]
    cleared = []

    class _Unit:
        ai_mode = "guard"
        pursue_attacker = 1
        pursue_leash_range = 48000
        speed = 10
        place = my_place
        x = 0
        y = 0
        action = None
        walked = []
        orders = []
        last_attacker = enemy

        def can_attack(self, _t):
            return False

        def is_an_enemy(self, _t):
            return False

        def _pursue_target_too_far(self, target=None):
            return True

        def _clear_pursue_aggro(self, return_home=True):
            cleared.append(return_home)
            self.last_attacker = None
            if self.action is not None:
                self.action.complete()

        def reset_charge_state(self, force=False):
            pass

        def switch_to_default_weapon(self):
            pass

    unit = _Unit()
    action = AttackAction(unit, enemy)
    unit.action = action
    action.update()
    assert cleared == [True]
    assert unit.action is None
    assert unit.last_attacker is None
