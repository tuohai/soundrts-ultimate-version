import types

from soundrts.clientgameentity import combat as combat_module
from soundrts.clientgameentity.combat import EntityViewCombat


class _FakeStyle:
    def __init__(self, entries):
        self.entries = entries

    def get(self, obj, attr, warn_if_not_found=True):
        return self.entries.get((obj, attr), [])

    def has(self, obj, attr):
        return (obj, attr) in self.entries


class _View(EntityViewCombat):
    def __init__(self, buffs=()):
        self.type_name = "footman"
        self.expanded_is_a = set()
        self.model = types.SimpleNamespace(_buffs=list(buffs))
        self.interface = types.SimpleNamespace(dobjets={})


def test_mdg_hit_vs_matches_target_buff(monkeypatch):
    buff = types.SimpleNamespace(type_name="b_absolute_defense")
    monkeypatch.setattr(
        combat_module,
        "style",
        _FakeStyle(
            {
                ("swordsman", "mdg_hit_vs"): ["b_absolute_defense", "iron_clang"],
                ("swordsman", "mdg_hit"): ["flesh_hit"],
            }
        ),
    )

    assert _View([buff])._get_melee_hit_sound("swordsman") == "iron_clang"


def test_rdg_hit_vs_matches_tuple_buff(monkeypatch):
    monkeypatch.setattr(
        combat_module,
        "style",
        _FakeStyle(
            {
                ("archer", "rdg_hit_vs"): ["b_magic_shield", "shield_ping"],
                ("archer", "rdg_hit"): ["arrow_hit"],
            }
        ),
    )

    assert _View([("b_magic_shield", object())])._get_ranged_hit_sound("archer") == "shield_ping"


def test_hit_vs_still_matches_target_type(monkeypatch):
    monkeypatch.setattr(
        combat_module,
        "style",
        _FakeStyle({("swordsman", "mdg_hit_vs"): ["footman", "armor_hit"]}),
    )

    assert _View()._get_melee_hit_sound("swordsman") == "armor_hit"
