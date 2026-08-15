"""AoE2: Britons shepherd vs Mongols hunter use separate deposit gather_time keys."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import soundrts.worldunit  # noqa: F401

from soundrts.worldresource import Deposit
from soundrts.worldunit.worldworker import Worker


ROOT = Path(__file__).resolve().parents[2]
AOE2_RULES = ROOT / "mods" / "aoe2" / "rules.txt"


def test_aoe2_rules_split_livestock_and_hunt_deposits():
    if not AOE2_RULES.is_file():
        return
    text = AOE2_RULES.read_text(encoding="utf-8")
    assert "def food_livestock" in text
    sheep = text.split("def sheep", 1)[1].split("def ", 1)[0]
    deer = text.split("def deer", 1)[1].split("def ", 1)[0]
    boar = text.split("def boar", 1)[1].split("def ", 1)[0]
    assert "food_deposit food_livestock" in sheep
    assert "food_deposit food_carcass" in deer
    assert "food_deposit food_carcass" in boar
    assert "food_livestock" in text.split("def peasant", 1)[1].split("def chinese_villager", 1)[0]
    brit = text.split("def britons", 1)[1].split("def franks", 1)[0]
    mong = text.split("def mongols", 1)[1].split("def ", 1)[0]
    assert "gather_time_food_livestock -20%" in brit
    assert "gather_time_food_carcass" not in brit
    assert "gather_time_food_carcass -29%" in mong
    assert "gather_time_food_livestock" not in mong


def test_gather_time_bonus_keys_by_deposit_type_not_civ_name():
    """Engine matches player.gather_time_bonus[deposit.type_name]; no civ hardcoding."""

    class Mini:
        gather_time = 10
        player = SimpleNamespace(
            gather_time_bonus={
                "food_livestock": "-20%",
                "food_carcass": "-29%",
            },
            ai_gather_time_percent=100,
        )

        def _single_gather_permission(self):
            return False

    mini = Mini()
    live = Deposit.__new__(Deposit)
    live.type_name = "food_livestock"
    live.extraction_time = 0
    hunt = Deposit.__new__(Deposit)
    hunt.type_name = "food_carcass"
    hunt.extraction_time = 0
    t_live = Worker.get_gather_time(mini, "resource3", live)
    t_hunt = Worker.get_gather_time(mini, "resource3", hunt)
    assert abs(t_live - 8.0) < 0.01  # 10 * 0.8
    assert abs(t_hunt - 7.1) < 0.01  # 10 * 0.71


def test_worker_can_hunt_uses_rules_food_deposit_types():
    from soundrts.worldplayercomputer import Computer

    player = Computer.__new__(Computer)
    player._cached_huntable_food_deposits = frozenset(
        {"food_carcass", "food_livestock"}
    )
    worker = SimpleNamespace(
        basic_skills={"attack", "gather"},
        can_gather_deposit=["goldmine", "food_livestock"],
    )
    assert player._worker_can_hunt(worker) is True
    worker.can_gather_deposit = ["goldmine"]
    assert player._worker_can_hunt(worker) is False


def test_carcass_short_title_any_deposit_with_carcass_of(monkeypatch):
    from soundrts.clientgameentity import properties as props

    monkeypatch.setattr(props, "compute_title", lambda name: [f"t:{name}"])
    monkeypatch.setattr(props.mp, "CORPSE", ["CORPSE"])
    titled = props.carcass_short_title(
        SimpleNamespace(type_name="food_livestock", carcass_of="sheep")
    )
    assert titled == ["t:sheep", "CORPSE"]
    plain = props.carcass_short_title(SimpleNamespace(type_name="food_livestock"))
    assert plain == ["t:food_livestock"]
