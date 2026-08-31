"""AoE2-style trainable line resolution + researchable line_upgrade."""

from soundrts.world_build_rules import (
    apply_unit_line_upgrade,
    line_train_root_type_name,
    remap_queued_train_orders_for_line_upgrade,
    resolve_trainable_unit_type,
    resolved_train_type_class,
    unit_train_cost,
    unit_train_time,
)


class _FakePlayer:
    def __init__(self, upgrades=None, ok_reqs=None, units=None):
        self.upgrades = list(upgrades or [])
        self._ok = set(ok_reqs or [])
        self.units = list(units or [])

    def has_all(self, reqs):
        reqs = reqs or ()
        if not reqs:
            return True
        return all(r in self._ok or r in self.upgrades for r in reqs)


_LINE_RULES = """
def parameters
nb_of_resource_types 4

def feudal_age
class phase

def castle_age
class phase

def militia
class soldier
cost 20 0 50 0
time_cost 21
can_upgrade_to man_at_arms

def man_at_arms
is_a militia
cost 40 0 100 0
time_cost 40
requirements feudal_age
line_upgrade 1
can_upgrade_to long_swordsman

def long_swordsman
is_a man_at_arms
cost 65 0 150 0
time_cost 40
requirements castle_age
line_upgrade 1
can_upgrade_to champion

def champion
is_a long_swordsman
cost 350 0 650 0
time_cost 70
requirements castle_age
line_upgrade 1
can_upgrade_to
"""


def test_resolve_requires_line_upgrade_research():
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        dark = _FakePlayer(ok_reqs=[])
        assert resolve_trainable_unit_type(dark, "militia") == "militia"

        # Age alone does not unlock line forms marked line_upgrade.
        feudal = _FakePlayer(ok_reqs=["feudal_age"], upgrades=["feudal_age"])
        assert resolve_trainable_unit_type(feudal, "militia") == "militia"

        feudal_researched = _FakePlayer(
            ok_reqs=["feudal_age"],
            upgrades=["feudal_age", "man_at_arms"],
        )
        assert (
            resolve_trainable_unit_type(feudal_researched, "militia") == "man_at_arms"
        )

        castle = _FakePlayer(
            ok_reqs=["feudal_age", "castle_age"],
            upgrades=["feudal_age", "castle_age", "man_at_arms"],
        )
        assert resolve_trainable_unit_type(castle, "militia") == "man_at_arms"

        castle_ls = _FakePlayer(
            ok_reqs=["feudal_age", "castle_age"],
            upgrades=["feudal_age", "castle_age", "man_at_arms", "long_swordsman"],
        )
        assert resolve_trainable_unit_type(castle_ls, "militia") == "long_swordsman"

        unlocked = _FakePlayer(
            ok_reqs=["feudal_age", "castle_age"],
            upgrades=[
                "feudal_age",
                "castle_age",
                "man_at_arms",
                "long_swordsman",
                "champion",
            ],
        )
        assert resolve_trainable_unit_type(unlocked, "militia") == "champion"

        assert line_train_root_type_name("champion") == "militia"
        assert list(unit_train_cost("champion")) == list(r.unit_class("militia").cost)
        assert unit_train_time("champion") == r.unit_class("militia").time_cost
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_effective_can_train_remaps_after_research():
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4

def feudal_age
class phase

def militia
class soldier
cost 20 0 50 0
time_cost 21
can_upgrade_to man_at_arms

def man_at_arms
is_a militia
cost 40 0 100 0
time_cost 40
requirements feudal_age
line_upgrade 1
can_upgrade_to

def barracks
class building
can_train militia
"""
    )
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:

        class B:
            type_name = "barracks"
            can_train = ("militia",)
            place = None

        B.player = _FakePlayer(ok_reqs=["feudal_age"], upgrades=["feudal_age"])
        assert effective_can_train(B()) == ("militia",)

        B.player = _FakePlayer(
            ok_reqs=["feudal_age"], upgrades=["feudal_age", "man_at_arms"]
        )
        assert effective_can_train(B()) == ("man_at_arms",)
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_apply_unit_line_upgrade_unlocks_and_morphs():
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:

        class U:
            type_name = "militia"
            can_upgrade_to = ("man_at_arms",)

        player = _FakePlayer(
            ok_reqs=["feudal_age"], upgrades=["feudal_age"], units=[U()]
        )

        morphs = []

        def fake_morph(unit, target_cls):
            morphs.append((unit.type_name, getattr(target_cls, "type_name", None)))
            unit.type_name = getattr(target_cls, "type_name", "man_at_arms")

        import soundrts.worldphase as worldphase

        saved_morph = worldphase.Phase._instant_morph
        worldphase.Phase._instant_morph = staticmethod(fake_morph)
        try:
            apply_unit_line_upgrade(player, "man_at_arms")
            assert "man_at_arms" in player.upgrades
            assert resolve_trainable_unit_type(player, "militia") == "man_at_arms"
            assert morphs == [("militia", "man_at_arms")]
        finally:
            worldphase.Phase._instant_morph = saved_morph
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def _type_name(cls):
    return getattr(cls, "type_name", None) or getattr(cls, "__name__", None)


def test_apply_unit_line_upgrade_remaps_queued_trains():
    """AoE2 DE: queued previous-tier trains become the researched form."""
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        militia_cls = r.unit_class("militia")
        maa_cls = r.unit_class("man_at_arms")

        class LineTrain:
            keyword = "train"
            is_complete = False
            is_impossible = False
            type = militia_cls

        class OtherTrain:
            keyword = "train"
            is_complete = False
            is_impossible = False

            class _Spear:
                type_name = "spearman"
                __name__ = "spearman"

            type = _Spear

        class Research:
            keyword = "research"
            is_complete = False
            is_impossible = False
            type = maa_cls

        class Barracks:
            type_name = "barracks"
            can_upgrade_to = ()
            orders = [LineTrain(), OtherTrain(), Research()]

        player = _FakePlayer(
            ok_reqs=["feudal_age"], upgrades=["feudal_age"], units=[Barracks()]
        )

        import soundrts.worldphase as worldphase

        saved_morph = worldphase.Phase._instant_morph
        worldphase.Phase._instant_morph = staticmethod(lambda *a, **k: None)
        try:
            apply_unit_line_upgrade(player, "man_at_arms")
        finally:
            worldphase.Phase._instant_morph = saved_morph

        assert _type_name(Barracks.orders[0].type) == "man_at_arms"
        assert Barracks.orders[0].type is maa_cls or _type_name(maa_cls) == "man_at_arms"
        assert _type_name(Barracks.orders[1].type) == "spearman"
        assert Barracks.orders[2].keyword == "research"
        assert Barracks.orders[2].type is maa_cls
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_queued_militia_skips_to_long_swordsman_when_that_research_completes():
    """Already-queued militia jump to the newly unlocked highest form."""
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        class LineTrain:
            keyword = "train"
            is_complete = False
            is_impossible = False
            type = r.unit_class("militia")

        class Barracks:
            type_name = "barracks"
            can_upgrade_to = ()
            orders = [LineTrain()]

        player = _FakePlayer(
            ok_reqs=["feudal_age", "castle_age"],
            upgrades=["feudal_age", "castle_age", "man_at_arms"],
            units=[Barracks()],
        )
        remap_queued_train_orders_for_line_upgrade(player, "long_swordsman")
        # man_at_arms already unlocked → queued militia become that form first
        assert _type_name(Barracks.orders[0].type) == "man_at_arms"

        player.upgrades.append("long_swordsman")
        remap_queued_train_orders_for_line_upgrade(player, "long_swordsman")
        assert _type_name(Barracks.orders[0].type) == "long_swordsman"
        spawn = resolved_train_type_class(player, r.unit_class("militia"))
        assert _type_name(spawn) == "long_swordsman"
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_upgrade_to_hidden_for_line_upgrade_targets():
    """Per-unit upgrade_to must not offer line_upgrade forms (DE: research only)."""
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules
    from soundrts.worldorders.production import UpgradeToOrder

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:

        class U:
            orders = []

        assert UpgradeToOrder.additional_condition(U(), "man_at_arms") is False
        assert UpgradeToOrder.additional_condition(U(), "champion") is False
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_allied_upgrades_shares_line_upgrade_without_upgrade_player():
    """Allied sync must not call upgrade_player on soldier line forms."""
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules
    from soundrts.worldplayerbase.resources import ResourcesMixin

    r = Rules()
    r.load(_LINE_RULES)
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:

        class P(ResourcesMixin):
            def __init__(self, upgrades=None):
                self.upgrades = list(upgrades or [])
                self.allied = []
                self.units = []

            def level(self, type_name):
                return self.upgrades.count(type_name)

        maa = global_rules.unit_class("man_at_arms")
        assert maa is not None
        assert not hasattr(maa, "upgrade_player")

        ally = P(upgrades=["man_at_arms"])
        me = P()
        me.allied = [ally]
        me._update_allied_upgrades()
        assert "man_at_arms" in me.upgrades

        leftover = P(upgrades=["militia"])
        other = P()
        other.allied = [leftover]
        other._update_allied_upgrades()
        assert other.upgrades == []
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_morph_upgrade_does_not_replace_train_slot():
    """Vanilla archer→darkarcher is a unit morph, not an AoE2 train line."""
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4

def magestower
class building

def archer
class soldier
can_upgrade_to darkarcher

def darkarcher
class soldier
requirements magestower

def barracks
class building
can_train footman archer knight
"""
    )
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        player = _FakePlayer(ok_reqs=["magestower"], upgrades=["magestower"])

        class B:
            type_name = "barracks"
            can_train = ("footman", "archer", "knight")
            place = None

        B.player = player
        assert resolve_trainable_unit_type(player, "archer") == "archer"
        assert effective_can_train(B()) == ("footman", "archer", "knight")
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c
