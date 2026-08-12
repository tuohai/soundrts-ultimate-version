"""Rules-driven research_stack_hp (Aztec monk HP per monastery tech)."""

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.world_research_stack import (
    apply_research_stack_hp_on_complete,
    parse_research_stack_hp_bonus,
    upgrade_has_research_stack_hp,
)
from soundrts.worldupgrade.base import Upgrade


def test_aoe2_monastery_techs_flag_research_stack_hp():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for tech in (
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
        # Each monastery tech block should include the flag near its def
        idx = text.find(f"def {tech}\n")
        assert idx >= 0, tech
        chunk = text[idx : idx + 350]
        assert "research_stack_hp 1" in chunk, tech
    assert "research_stack_hp_bonus 5 monk" in text
    assert "def aztec_eagle_scout" in text
    assert "can_research crossbowman arbalester elite_skirmisher" in text
    assert "thumb_ring" not in text.split("def aztec_archery", 1)[1].split("def aztec_blacksmith", 1)[0]
    assert "keeptower" not in text.split("def aztec_university", 1)[1].split("def aztec_workshop", 1)[0]
    assert "galleon" not in text.split("def aztec_shipyard", 1)[1].split("def aztec_castle", 1)[0]


def test_parse_research_stack_hp_bonus(monkeypatch):
    monkeypatch.setattr(
        "soundrts.definitions.rules.get",
        lambda faction, key, *a, **k: ["5", "monk"]
        if key == "research_stack_hp_bonus"
        else None,
    )
    delta, types = parse_research_stack_hp_bonus("aztecs")
    assert delta == 5 * PRECISION
    assert types == ("monk",)


def test_apply_research_stack_hp_on_complete(monkeypatch):
    monkeypatch.setattr(
        "soundrts.world_research_stack.parse_research_stack_hp_bonus",
        lambda faction: (5 * PRECISION, ("monk",)),
    )
    applied = []

    class _Upg:
        type_name = "sanctity"
        research_stack_hp = 1

    class _Monk:
        type_name = "monk"
        expanded_is_a = ()
        hp_max = 30 * PRECISION
        hp = 30 * PRECISION

    monk = _Monk()
    player = types.SimpleNamespace(faction="aztecs", units=[monk], _phase_bonus_pool=None)

    def _fake_bonus(cls, unit, start_level, *args):
        applied.append((unit, args))
        # mimic hp grow
        unit.hp_max += args[1]
        unit.hp += args[1]

    monkeypatch.setattr(Upgrade, "effect_bonus", classmethod(_fake_bonus))
    assert upgrade_has_research_stack_hp(_Upg)
    apply_research_stack_hp_on_complete(player, _Upg)
    assert applied and applied[0][0] is monk
    assert applied[0][1] == ("hp", 5 * PRECISION)
    assert player._phase_bonus_pool == [(["hp", 5 * PRECISION], ["monk"])]
    assert monk.hp_max == 35 * PRECISION


def test_upgrade_default_research_stack_hp_off():
    assert Upgrade.research_stack_hp == 0
