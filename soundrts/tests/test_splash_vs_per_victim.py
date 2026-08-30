"""mdg_splash_vs / decay_min_vs apply to the unit that is splashed, not the aim target."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from soundrts.combat.splash import SplashMixin, _type_map_bonus
from soundrts.worldunit import Creature


def test_type_map_bonus_prefers_type_name_then_is_a():
    archer = SimpleNamespace(type_name="aoe_archer", expanded_is_a=("archer_unit", "soldier"))
    knight = SimpleNamespace(type_name="aoe_knight", expanded_is_a=("cavalry",))
    vs = {"archer_unit": 30, "aoe_knight": 5}
    assert _type_map_bonus(archer, vs) == 30
    assert _type_map_bonus(knight, vs) == 5
    assert _type_map_bonus(SimpleNamespace(type_name="x", expanded_is_a=()), vs) == 0


def test_splash_vs_hits_nearby_archer_not_knight_when_aiming_at_knight():
    hits = {}

    def _hit(self, damage, attacker, notify=True):
        hits[self.type_name] = hits.get(self.type_name, 0) + damage

    knight = MagicMock(spec=Creature)
    knight.type_name = "aoe_knight"
    knight.expanded_is_a = ("cavalry",)
    knight.x = 0
    knight.y = 0
    knight.receive_hit.side_effect = lambda *a, **k: _hit(knight, a[0], a[1], **k)
    knight.notify = MagicMock()

    archer = MagicMock(spec=Creature)
    archer.type_name = "aoe_archer"
    archer.expanded_is_a = ("archer_unit",)
    archer.x = 0
    archer.y = 0
    archer.receive_hit.side_effect = lambda *a, **k: _hit(archer, a[0], a[1], **k)
    archer.notify = MagicMock()

    place = SimpleNamespace(objects=[knight, archer])
    knight.place = place
    archer.place = place

    class Dummy(SplashMixin):
        mdg_splash = 0
        mdg_radius = 1000
        mdg_radius_vs = {}
        mdg_splash_vs = {"archer_unit": 30}
        mdg_splash_decay_min = 1
        mdg_splash_decay_min_vs = {}
        mdg_explode = 0
        world = SimpleNamespace(random=SimpleNamespace(random=lambda: 1.0))

        def is_an_enemy(self, obj):
            return obj is not self

    attacker = Dummy()
    attacker.splash_aim(knight, is_melee=True)

    assert hits.get("aoe_archer") == 30
    assert "aoe_knight" not in hits
