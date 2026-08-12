"""AoE2 monastery techs: parse costs and rules-driven conversion flags."""

from soundrts.definitions import Rules, rules
from soundrts.worldskill import Skill


_MONASTERY_SNIPPET = """
def parameters
nb_of_resource_types 4

def castle_age
class phase
cost 0 0 0 0

def imperial_age
class phase
cost 0 0 0 0

def monastery
class building
requirements castle_age
can_research redemption atonement herbal_medicine heresy sanctity fervor faith illumination block_printing theocracy

def redemption
class upgrade
cost 475 0 0 0
time_cost 50
requirements monastery castle_age
conversion_allows_siege 1
conversion_allows_building 1

def atonement
class upgrade
cost 325 0 0 0
time_cost 40
requirements monastery castle_age
conversion_allows_monk 1

def herbal_medicine
class upgrade
cost 200 0 0 0
time_cost 35
requirements monastery castle_age
effect bonus heal_level 5

def heresy
class upgrade
cost 1000 0 0 0
time_cost 60
requirements monastery castle_age
conversion_victim_dies 1

def sanctity
class upgrade
cost 175 0 0 0
time_cost 60
requirements monastery castle_age
effect bonus hp 15

def fervor
class upgrade
cost 140 0 0 0
time_cost 50
requirements monastery castle_age
effect bonus speed 15%

def faith
class upgrade
cost 750 0 550 0
time_cost 60
requirements monastery imperial_age
conversion_channel_scale_num 5
conversion_channel_scale_den 3
conversion_channel_bonus_time 2

def illumination
class upgrade
cost 120 0 0 0
time_cost 65
requirements monastery imperial_age
effect bonus mana_regen 87.5%

def block_printing
class upgrade
cost 200 0 0 0
time_cost 55
requirements monastery imperial_age
effect bonus rdg_range 3

def theocracy
class upgrade
cost 200 0 0 0
time_cost 75
requirements monastery imperial_age
conversion_rest_only_success 1

def monk
class soldier
conversion_tech_gated 1
conversion_cleric 1
can_use_tech sanctity fervor illumination block_printing redemption atonement
"""


def _load_aoe2_snippet():
    r = Rules()
    r.load(_MONASTERY_SNIPPET)
    return r


def _install_global_monastery_rules():
    """Load snippet into the process-global ``rules`` used by world_conversion."""
    rules.load(_MONASTERY_SNIPPET)


def test_monastery_tech_costs_and_presence():
    r = _load_aoe2_snippet()
    assert list(r.unit_class("redemption").cost)[:4] == [475000, 0, 0, 0] or list(
        r._dict["redemption"]["cost"]
    )[:4] == [475, 0, 0, 0]
    faith_cost = r._dict["faith"]["cost"]
    assert int(faith_cost[0]) in (750, 750000)
    assert int(faith_cost[2]) in (550, 550000)
    for name in (
        "redemption",
        "atonement",
        "herbal_medicine",
        "heresy",
        "sanctity",
        "fervor",
        "faith",
        "illumination",
        "block_printing",
        "theocracy",
    ):
        assert name in r._dict


def test_conversion_blocks_monk_without_atonement():
    _install_global_monastery_rules()

    class P:
        upgrades = []

    class Caster:
        type_name = "monk"
        expanded_is_a = set()
        conversion_tech_gated = 1
        player = P()

        def is_an_enemy(self, _t):
            return True

    class Target:
        type_name = "monk"
        expanded_is_a = set()
        conversion_cleric = 1
        player = P()

        def set_player(self, _p):
            raise AssertionError("should not convert")

    assert Skill._conversion_target_allowed(Caster(), Target()) is False
    Caster.player.upgrades = ["atonement"]
    assert Skill._conversion_target_allowed(Caster(), Target()) is True


def test_heresy_kills_instead_of_converting():
    _install_global_monastery_rules()

    class P:
        upgrades = ["heresy"]

    class Caster:
        type_name = "monk"
        expanded_is_a = set()
        conversion_tech_gated = 1
        player = type("CP", (), {"upgrades": []})()

        def is_an_enemy(self, _t):
            return True

    died = []

    class Target:
        type_name = "peasant"
        expanded_is_a = set()
        player = P()

        def set_player(self, _p):
            raise AssertionError("heresy should not convert")

        def die(self, attacker=None):
            died.append(attacker)

    assert Skill._execute_conversion(Caster(), Target(), None) is True
    assert len(died) == 1


def test_theocracy_only_one_monk_rests():
    _install_global_monastery_rules()

    class Player:
        upgrades = ["theocracy"]
        units = []

    player = Player()

    class Order:
        keyword = "use"
        type = type("T", (), {"effect": ["conversion"]})()
        target = None

    class Monk:
        def __init__(self, mana=100):
            self.type_name = "monk"
            self.expanded_is_a = set()
            self.conversion_tech_gated = 1
            self.player = player
            self.mana = mana
            self.orders = []
            self.id = id(self)

    target = type("Target", (), {"id": 99})()
    a = Monk(100)
    b = Monk(100)
    a.orders = [Order()]
    b.orders = [Order()]
    a.orders[0].target = target
    b.orders[0].target = target
    player.units = [a, b]

    Skill.apply_conversion_mana_costs(a, target, 100)
    assert a.mana == 0
    assert b.mana == 100


def test_without_theocracy_all_converting_monks_rest():
    _install_global_monastery_rules()

    class Player:
        upgrades = []
        units = []

    player = Player()

    class Order:
        keyword = "use"
        type = type("T", (), {"effect": ["conversion"]})()
        target = None

    class Monk:
        def __init__(self):
            self.type_name = "monk"
            self.expanded_is_a = set()
            self.conversion_tech_gated = 1
            self.player = player
            self.mana = 100
            self.orders = []
            self.id = id(self)

    target = type("Target", (), {"id": 42})()
    a = Monk()
    b = Monk()
    c = Monk()  # not converting this target
    a.orders = [Order()]
    b.orders = [Order()]
    a.orders[0].target = target
    b.orders[0].target = target
    player.units = [a, b, c]

    Skill.apply_conversion_mana_costs(a, target, 100)
    assert a.mana == 0
    assert b.mana == 0
    assert c.mana == 100


def test_faith_lengthens_conversion_channel():
    from soundrts.lib.nofloat import PRECISION

    _install_global_monastery_rules()

    class SkillType:
        time_cost = 6 * PRECISION

    class Target:
        type_name = "peasant"
        expanded_is_a = set()
        player = type("P", (), {"upgrades": []})()

    base = Skill.conversion_channel_time(None, Target(), SkillType)
    Target.player = type("P", (), {"upgrades": ["faith"]})()
    resisted = Skill.conversion_channel_time(None, Target(), SkillType)
    assert base == 6 * PRECISION
    assert resisted > base
    # ~6 * 5/3 + 2 ≈ 12s
    assert resisted == 6 * PRECISION * 5 // 3 + 2 * PRECISION


def test_illumination_shortens_faith_recovery_to_about_33s():
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldupgrade import Upgrade

    u = type("u", (), {})()
    u.type_name = "monk"
    u.expanded_is_a = set()
    u.can_use_tech = ["illumination"]
    u.mana_max = 100 * PRECISION
    u.mana_regen = int(1.6 * PRECISION)  # 1600 /s
    u.mana_regen_cd = 1 * PRECISION
    Upgrade.effect_bonus(u, 0, "mana_regen", "87.5%")
    # 1600 * 1.875 = 3000 → 100000/3000 ≈ 33.3s
    assert int(u.mana_regen) == 3000
    seconds = (100 * PRECISION) / float(u.mana_regen)
    assert 32.0 <= seconds <= 34.0


def test_heresy_kills_building_too():
    _install_global_monastery_rules()

    class P:
        upgrades = ["heresy"]

    class Caster:
        type_name = "monk"
        expanded_is_a = set()
        conversion_tech_gated = 1
        player = type("CP", (), {"upgrades": ["redemption"]})()

        def is_an_enemy(self, _t):
            return True

    died = []

    class Target:
        type_name = "barracks"
        expanded_is_a = {"building"}
        player = P()

        def set_player(self, _p):
            raise AssertionError("heresy should not convert")

        def die(self, attacker=None):
            died.append(True)

    assert Skill._execute_conversion(Caster(), Target(), None) is True
    assert died == [True]


def test_upgrade_flags_are_data_driven_not_name_checks():
    """Renaming the upgrade still works if attrs are kept."""
    _install_global_monastery_rules()
    # Inject a renamed clone with the same flags
    rules.load(
        _MONASTERY_SNIPPET
        + """
def my_heresy
class upgrade
conversion_victim_dies 1
"""
    )

    class P:
        upgrades = ["my_heresy"]

    class Caster:
        type_name = "monk"
        conversion_tech_gated = 1
        expanded_is_a = set()
        player = type("CP", (), {"upgrades": []})()

        def is_an_enemy(self, _t):
            return True

    died = []

    class Target:
        type_name = "peasant"
        expanded_is_a = set()
        player = P()

        def set_player(self, _p):
            raise AssertionError("should die")

        def die(self, attacker=None):
            died.append(True)

    assert Skill._execute_conversion(Caster(), Target(), None) is True
    assert died == [True]
