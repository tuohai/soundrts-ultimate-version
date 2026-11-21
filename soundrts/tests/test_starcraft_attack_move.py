"""Attack-move (StarCraft 2 "A-move") regression tests."""

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.worldorders import ORDERS_DICT


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


def test_attack_move_order_is_registered():
    assert "attack_move" in ORDERS_DICT
    order_cls = ORDERS_DICT["attack_move"]
    assert order_cls.keyword == "attack_move"
    assert order_cls.nb_args == 1


def test_can_attack_move_is_a_known_rule_keyword():
    from soundrts.definitions import rules as global_rules

    assert "can_attack_move" in global_rules.int_properties


def test_can_attack_move_loads_from_rules():
    rules = Rules()
    rules.load(
        """
def marine
class soldier
can_attack_move 0

def firebat
class soldier
can_attack_move 1
"""
    )
    assert rules.unit_class("marine").can_attack_move == 0
    assert rules.unit_class("firebat").can_attack_move == 1


def test_soldier_defaults_to_allowing_attack_move():
    from soundrts.worldunit.worldsoldier import Soldier

    assert Soldier.can_attack_move == 1


def test_attack_move_is_in_the_order_menu():
    """The order needs a style entry with an index, else it never shows up."""
    from soundrts.definitions import style

    assert style.has("attack_move", "index")
    assert style.has("attack_move", "title")


def test_attack_move_uses_the_dedicated_tts_entry():
    """The style title must point at a real attack-move phrase in tts.txt."""
    from soundrts import msgparts as mp
    from soundrts.definitions import style

    title = style.get("attack_move", "title")
    assert [str(x) for x in title] == [str(x) for x in mp.ATTACK_MOVE]

    tts = Path("res/ui/tts.txt").read_text(encoding="utf-8")
    for msg_id in mp.ATTACK_MOVE:
        assert "\n%s\t" % msg_id in "\n" + tts
    assert "attack-move" in tts


def test_starcraft_mod_uses_attack_move():
    """The StarCraft mod's combat units must be able to A-move."""
    rules = Rules()
    rules.load(_starcraft_rules_text())
    for name in ("marine", "zealot", "zergling", "ghost"):
        unit = rules.unit_class(name)
        assert unit is not None, name
        assert int(getattr(unit, "can_attack_move", 0) or 0) == 1, name
    # Workers must not A-move into a fight.
    for name in ("scv", "probe", "drone"):
        unit = rules.unit_class(name)
        assert unit is not None, name
        assert int(getattr(unit, "can_attack_move", 0) or 0) == 0, name


def test_attack_move_menu_requires_both_skills():
    from soundrts.worldorders.movement import AttackMoveOrder

    class Unit:
        can_attack_move = 1
        basic_skills = {"go", "attack"}

    assert AttackMoveOrder.is_allowed(Unit()) is True

    class Worker(Unit):
        can_attack_move = 0

    assert AttackMoveOrder.is_allowed(Worker()) is False

    class NoAttack(Unit):
        basic_skills = {"go"}

    assert AttackMoveOrder.is_allowed(NoAttack()) is False


# ---------------------------------------------------------------------------
# Option A: an attack-moving unit never chases a fleeing enemy across squares
# ---------------------------------------------------------------------------


def _chase_unit():
    """A minimal unit stub that is in "chase" ai_mode."""

    class _Player:
        def updated_target(self, target):
            return target

        def player_is_an_enemy(self, other):
            return True

    class _Square:
        def __init__(self, name):
            self.id = name
            self.objects = []
            self.neighbors = []
            self.high_ground = False

    class _Unit:
        speed = 1
        ai_mode = "chase"
        can_attack_move = 1
        can_attack_move_chase = 0
        x = 0
        y = 0
        radius = 0
        action = None

        def __init__(self):
            self.chase_calls = []
            self.aim_calls = []
            self.notifications = []
            self.go_to_calls = []
            self.player = _Player()
            self.place = _Square("home")

        def is_an_enemy(self, other):
            return True

        def can_attack(self, target):
            return False

        def aim(self, target):
            self.aim_calls.append(target)

        def action_reach_and_aim(self):
            self.aim_calls.append(self.action_target)

        def go_to_xy(self, x, y):
            self.go_to_calls.append((x, y))

        def notify(self, msg, *args, **kwargs):
            self.notifications.append(msg)

    return _Unit()


class _FakeStage:
    """A stand-in for the exit/stage returned by ``unit.next_stage``."""

    def __init__(self):
        self.x = 500
        self.y = 500
        self.place = None
        self.other_side = None


class _FakeTarget:
    def __init__(self, x=0, y=0):
        self.id = "enemy1"
        self.x = x
        self.y = y
        self.hp = 100
        self.is_vulnerable = True
        self.radius = 0
        # The target sits in another square, so the unit has to walk to it.
        self.place = type("_Square", (), {"id": "far", "objects": [], "neighbors": []})()


def test_attack_move_action_forbids_cross_square_pursuit_by_default():
    """The attack-move order must mark its AttackAction as no-chase."""
    from soundrts.worldaction import AttackAction
    from soundrts.worldorders.movement import AttackMoveOrder

    unit = _chase_unit()
    enemy = _FakeTarget()
    unit.action_target = enemy

    order = AttackMoveOrder.__new__(AttackMoveOrder)
    order.unit = unit
    order.target = enemy
    order.is_imperative = True
    order._pick_enemy_on_the_way = lambda: enemy

    order.execute()

    assert isinstance(unit.action, AttackAction)
    assert unit.action.no_cross_square_pursuit is True


def test_attack_move_does_not_chase_across_squares_even_in_chase_mode():
    """A chaser that is A-moving must not follow a target out of its square."""
    from soundrts.worldaction import AttackAction

    unit = _chase_unit()
    enemy = _FakeTarget()
    unit.action = AttackAction(unit, enemy)
    unit.action.no_cross_square_pursuit = True
    unit.action_target = enemy

    # The target is out of reach and not attackable: the action must give
    # up instead of walking towards it.
    chased = []
    unit.next_stage = lambda target: chased.append(target) or _FakeStage()

    unit.action.update()

    assert chased == [], "A-move unit must not pursue the target across squares"
    # The action is over, so the order queue takes over again and the unit
    # resumes advancing towards its destination.
    assert unit.action is None


def test_regular_attack_action_still_chases_across_squares():
    """Without the A-move flag the chase behaviour is unchanged."""
    from soundrts.worldaction import AttackAction

    unit = _chase_unit()
    enemy = _FakeTarget()
    unit.action = AttackAction(unit, enemy)
    unit.action_target = enemy

    chased = []
    unit.next_stage = lambda target: chased.append(target) or _FakeStage()

    unit.action.update()

    assert chased == [enemy], "a plain chase-mode attack must still pursue"
    assert unit.action is not None, "the chase must not end the action"


def test_can_attack_move_chase_opt_in_re_enables_cross_square_pursuit():
    """``can_attack_move_chase 1`` lets a mod opt a unit type back in."""
    from soundrts.worldaction import AttackAction
    from soundrts.worldorders.movement import AttackMoveOrder

    unit = _chase_unit()
    unit.can_attack_move_chase = 1
    enemy = _FakeTarget()
    unit.action_target = enemy

    order = AttackMoveOrder.__new__(AttackMoveOrder)
    order.unit = unit
    order.target = enemy
    order.is_imperative = True
    order._pick_enemy_on_the_way = lambda: enemy

    order.execute()

    assert isinstance(unit.action, AttackAction)
    assert unit.action.no_cross_square_pursuit is False


def test_can_attack_move_chase_is_a_known_rule_keyword():
    from soundrts.definitions import rules as global_rules

    assert "can_attack_move_chase" in global_rules.int_properties


def test_can_attack_move_chase_loads_from_rules():
    rules = Rules()
    rules.load(
        """
def marine
class soldier
can_attack_move_chase 0

def firebat
class soldier
can_attack_move_chase 1
"""
    )
    assert rules.unit_class("marine").can_attack_move_chase == 0
    assert rules.unit_class("firebat").can_attack_move_chase == 1


def test_units_do_not_chase_across_squares_while_attack_moving_by_default():
    """The default is "no cross-square chase" for every unit type."""
    from soundrts.worldunit.worldbase import Unit

    assert Unit.can_attack_move_chase == 0
