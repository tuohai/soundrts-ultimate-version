"""战役触发器：alliance_request / alliance_with / transfer_units。"""
from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import patch

import pytest

import soundrts.worldunit  # noqa: F401

from soundrts.worldplayerbase.triggers import TriggersMixin

_CAMPAIGN_DIR = (
    Path(__file__).resolve().parents[2] / "res" / "single" / "The Legend of Raynor"
)


class _StubClient:
    def __init__(self, alliance=None):
        self.alliance = alliance


class _StubPlayer:
    is_human = False

    def __init__(self, *, is_human=False, player_id="c1", name=None):
        self.is_human = is_human
        self.id = player_id
        self.name = name or player_id
        self.neutral = False
        self.units = []
        self.allied = [self]
        self.allied_control = (self,)
        self.allied_control_units_set = set()
        self.client = _StubClient()
        self._ally_requests_from = set()
        self._alliance_declined_from = set()
        self.objectives = {}
        self._required_objective_numbers = set()
        self._completed_objective_numbers = set()
        self.upgrades = []
        self.has_victory = False
        self.voice = []

    def victory(self):
        self.has_victory = True

    def _all_required_objectives_done(self):
        from soundrts.worldplayerbase.base import Objective

        required = getattr(self, "_required_objective_numbers", set())
        completed = getattr(self, "_completed_objective_numbers", set())
        return required <= completed

    def _try_mission_victory(self):
        if self.has_victory or not self._all_required_objectives_done():
            return
        from soundrts import msgparts as mp

        self.send_voice_important(mp.MISSION_COMPLETE)
        self.has_victory = True

    def push(self, *args):
        pass

    def send_voice_important(self, msg):
        self.voice.append(msg)

    def unit_under_allied_control(self, unit):
        if unit.player in self.allied_control:
            return True
        return unit in self.allied_control_units_set

    @property
    def allied_control_units(self):
        result = []
        for p in self.allied_control:
            result.extend(p.units)
        for u in self.allied_control_units_set:
            if getattr(u, "presence", True) and u not in result:
                result.append(u)
        return result

    def update_alliance(self):
        from soundrts.worldplayerbase.base import alliance_ids_equal

        if self.client.alliance in (None, "None"):
            self.allied = [self]
        else:
            self.allied = [
                p
                for p in self.world.players
                if alliance_ids_equal(p.client.alliance, self.client.alliance)
            ]


class _StubAttackOrder:
    keyword = "attack"

    def __init__(self, target):
        self.target = target


class _StubUnit:
    def __init__(self, player, type_name="knight", unit_id="u1"):
        self.player = player
        self.type_name = type_name
        self.id = unit_id
        self.presence = True
        self.place = None
        self.inside = None
        self.orders = []
        player.units.append(self)

    def cancel_all_orders(self, unpay=False):
        self.orders = []

    def set_player(self, new_player):
        if self.player and self in self.player.units:
            self.player.units.remove(self)
        self.player = new_player
        if new_player is not None and self not in new_player.units:
            new_player.units.append(self)


class _StubVictim:
    def __init__(self, owner, type_name="traitor_guard", unit_id="v1"):
        self.player = owner
        self.type_name = type_name
        self.id = unit_id
        self.expanded_is_a = []

    def set_player(self, new_player):
        if self.player and self in self.player.units:
            self.player.units.remove(self)
        self.player = new_player
        if new_player is not None and self not in new_player.units:
            new_player.units.append(self)


class _StubWorld:
    def __init__(self, players):
        self.players = players
        self.ex_players = []
        self.grid = {}
        self.squares = []
        self.alliance_vision_managers = {}
        for p in players:
            p.world = self

    def update_alliances(self):
        for p in self.players:
            p.update_alliance()


class _TriggerOwner(TriggersMixin, _StubPlayer):
    pass


def _make_triggers(owner, world):
    owner.world = world
    owner.check_type = lambda o, name: getattr(o, "type_name", None) == name
    return owner


def _human_and_computer():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Knight Lord")
    world = _StubWorld([human, computer])
    world.update_alliances()
    return human, computer, world


def test_lang_has_detects_researched_upgrade(monkeypatch):
    _UpgradeStub = type("_UpgradeStub", (), {"upgrade_player": classmethod(lambda cls, p: None)})

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.unit_class",
        lambda name: _UpgradeStub if name == "u_psi_storm" else None,
    )
    assert t.lang_has(["u_psi_storm"]) is False
    human.upgrades.append("u_psi_storm")
    assert t.lang_has(["u_psi_storm"]) is True


def test_resolve_map_player_ref():
    human, computer, world = _human_and_computer()
    t = _make_triggers(human, world)
    assert t._resolve_map_player_ref("player1") is human
    assert t._resolve_map_player_ref("computer1") is computer
    assert t._resolve_map_player_ref("player2") is None


def test_alliance_request_adds_pending_and_notifies():
    human, computer, world = _human_and_computer()
    t = _make_triggers(human, world)
    t.lang_alliance_request(["computer1"])
    assert computer.id in human._ally_requests_from
    assert human.voice


def test_alliance_request_skips_if_already_allied():
    human, computer, world = _human_and_computer()
    human.client.alliance = 1
    computer.client.alliance = 1
    world.update_alliances()
    t = _make_triggers(human, world)
    t.lang_alliance_request(["computer1"])
    assert computer.id not in human._ally_requests_from


def test_lang_alliance_sets_multiple_players():
    human, computer, world = _human_and_computer()
    human.client.alliance = "ai"
    computer.client.alliance = "ai"
    t = _make_triggers(human, world)
    t.lang_alliance(["1", "player1", "computer1"])
    assert human.client.alliance == 1
    assert computer.client.alliance == 1
    assert computer in human.allied


def test_alliance_ids_equal_across_int_and_string():
    from soundrts.worldplayerbase.base import alliance_ids_equal, normalize_alliance_id

    assert normalize_alliance_id("1") == 1
    assert alliance_ids_equal(1, "1")
    assert alliance_ids_equal("1", 1)


def test_lang_alliance_ceasefire_between_new_allies():
    human, computer, world = _human_and_computer()
    human.client.alliance = "ai"
    computer.client.alliance = "ai"
    knight = _StubUnit(human, type_name="knight", unit_id="k1")
    marco = _StubUnit(computer, type_name="npc_marco_ironhand", unit_id="m1")
    knight.action_target = marco
    marco.action_target = knight
    t = _make_triggers(human, world)
    t.lang_alliance(["1", "player1", "computer1"])
    assert knight.action_target is None
    assert marco.action_target is None


def test_lang_alliance_ceasefire_clears_attack_orders():
    human, computer, world = _human_and_computer()
    human.client.alliance = "ai"
    computer.client.alliance = "ai"
    knight = _StubUnit(human, type_name="knight", unit_id="k1")
    marco = _StubUnit(computer, type_name="npc_marco_ironhand", unit_id="m1")
    knight.orders = [_StubAttackOrder(marco)]
    t = _make_triggers(human, world)
    t.lang_alliance(["1", "player1", "computer1"])
    assert knight.orders == []


def test_alliance_with_true_after_shared_alliance():
    human, computer, world = _human_and_computer()
    human.client.alliance = 2
    computer.client.alliance = 2
    world.update_alliances()
    t = _make_triggers(human, world)
    assert t.lang_alliance_with(["computer1"]) is True


def test_alliance_request_pending():
    human, computer, world = _human_and_computer()
    human._ally_requests_from.add(computer.id)
    t = _make_triggers(human, world)
    assert t.lang_alliance_request_pending(["computer1"]) is True
    assert t.lang_alliance_request_pending(["player1"]) is False


def test_alliance_declined_with_after_decline():
    human, computer, world = _human_and_computer()
    human._alliance_declined_from.add(computer.id)
    t = _make_triggers(human, world)
    assert t.lang_alliance_declined_with(["computer1"]) is True
    assert t.lang_alliance_declined_with(["player1"]) is False
    assert t.lang_alliance_with(["computer1"]) is False


def test_cmd_diplomacy_decline_records_alliance_declined_from():
    from soundrts.worldplayerbase import Player

    computer = _StubPlayer(is_human=False, player_id="ai1")
    computer.name = ["Knight Lord"]
    computer.send_voice_important = lambda msg: None
    world = _StubWorld([computer])
    human = Player.__new__(Player)
    human.id = "h1"
    human.is_human = True
    human.neutral = False
    human.world = world
    human.client = types.SimpleNamespace(name=["Player 1"], alliance=None)
    human._ally_requests_from = {computer.id}
    human._alliance_declined_from = set()
    human.voice = []
    human.send_voice_important = lambda msg: human.voice.append(msg)
    human.broadcast_to_others_only = lambda *a, **k: None
    human.is_local_human = lambda: True
    world.players = [human, computer]

    human._resolve_player_by_id = lambda pid: computer if pid == computer.id else None
    human.cmd_diplomacy(["decline_or_cancel", computer.id])

    assert computer.id not in human._ally_requests_from
    assert computer.id in human._alliance_declined_from


def test_transfer_units_changes_owner():
    human, computer, world = _human_and_computer()
    square = types.SimpleNamespace(objects=[], name="1,1")
    knight = _StubUnit(computer, type_name="knight", unit_id="k1")
    square.objects = [knight]
    world.grid = {"1,1": square}
    world.squares = [square]

    t = _make_triggers(human, world)
    t.lang_transfer_units(["computer1", "player1", "b2", "knight"])

    assert knight.player is human
    assert knight in human.units
    assert knight not in computer.units


def test_transfer_units_all_when_no_selector():
    human, computer, world = _human_and_computer()
    u1 = _StubUnit(computer, type_name="knight", unit_id="k1")
    u2 = _StubUnit(computer, type_name="archer", unit_id="a1")
    t = _make_triggers(human, world)
    t.lang_transfer_units(["computer1", "player1"])
    assert u1.player is human
    assert u2.player is human
    assert computer.units == []


def test_chapter_24_uses_workaround_triggers():
    text = (_CAMPAIGN_DIR / "24.txt").read_text(encoding="utf-8")
    assert "secret_letter h1" in text
    assert "(alliance 1)" in text
    assert "(allied_control computer1)" in text
    assert "(add_units o8 6 knight)" in text
    assert "(set_campaign_flag ch24_garrek)" in text
    assert "(add_inventory_item garrek_token 1 raynor)" in text
    assert "(set_campaign_flag ch24_garrek_token)" in text
    assert "(alliance_request" not in text
    assert "(transfer_units" not in text
    assert "(has_killed 6 traitor_guard enemy)" in text


def test_lang_add_inventory_item_puts_item_in_unit_bag(monkeypatch):
    created = []

    class _Token:
        def __init__(self, place, x, y):
            self.type_name = "garrek_token"
            self.place = place
            created.append(self)

        def move_to(self, *a, **k):
            pass

        def equip(self, unit):
            pass

    human, _, world = _human_and_computer()
    raynor = _StubUnit(human, type_name="raynor", unit_id="r1")
    raynor.inventory = []
    raynor.inventory_capacity = 3
    t = _make_triggers(human, world)
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.unit_class",
        lambda name: _Token if name == "garrek_token" else None,
    )
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.get",
        lambda name, key: ["item"] if name == "garrek_token" and key == "class" else None,
    )
    t.lang_add_inventory_item(["garrek_token", "1", "raynor"])
    assert len(raynor.inventory) == 1
    assert len(created) == 1


def test_lang_add_inventory_item_matches_raynor_stage_via_is_a(monkeypatch):
    """战役各章雷诺阶段名不同；add_inventory_item 用基类 raynor 应能命中。"""
    created = []

    class _Token:
        def __init__(self, place, x, y):
            self.type_name = "garrek_token"
            self.place = place
            created.append(self)

        def move_to(self, *a, **k):
            pass

        def equip(self, unit):
            pass

    human, _, world = _human_and_computer()
    raynor = _StubUnit(human, type_name="raynor6", unit_id="r1")
    raynor.expanded_is_a = {"raynor", "raynor5", "raynor6"}
    raynor.inventory = []
    raynor.inventory_capacity = 3
    t = _make_triggers(human, world)
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.unit_class",
        lambda name: _Token if name == "garrek_token" else None,
    )
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.get",
        lambda name, key: ["item"] if name == "garrek_token" and key == "class" else None,
    )
    t.lang_add_inventory_item(["garrek_token", "1", "raynor"])
    assert len(raynor.inventory) == 1
    assert len(created) == 1


def test_lang_set_ai_mode_on_selected_units():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    world = _StubWorld([human, computer])
    world.update_alliances()
    roland = _StubUnit(computer, type_name="npc_count_roland", unit_id="r1")
    brother = _StubUnit(computer, type_name="npc_roland_guard", unit_id="b1")
    roland.ai_mode = "guard"
    brother.ai_mode = "guard"
    t = _make_triggers(computer, world)
    t.lang_set_ai_mode(["offensive"])
    assert roland.ai_mode == "offensive"
    assert brother.ai_mode == "offensive"


def test_lang_set_yield_on_defeat_on_selected_units():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    world = _StubWorld([human, computer])
    world.update_alliances()
    roland = _StubUnit(computer, type_name="npc_count_roland", unit_id="r1")
    brother = _StubUnit(computer, type_name="npc_roland_guard", unit_id="b1")
    roland.yield_on_defeat = 0
    brother.yield_on_defeat = 0
    t = _make_triggers(computer, world)
    t.lang_set_yield_on_defeat(["1"])
    assert roland.yield_on_defeat == 1
    assert brother.yield_on_defeat == 1


def test_chapter_25_roland_rules_no_spawn_yield():
    rules = (_CAMPAIGN_DIR / "rules.txt").read_text(encoding="utf-8")
    roland_block = rules.split("def npc_count_roland")[1].split("def npc_roland_guard")[0]
    brother_block = rules.split("def npc_roland_guard")[1].split("def npc_general_vera")[0]
    assert "yield_on_defeat" not in roland_block
    assert "yield_on_defeat" not in brother_block


def test_chapter_27_uses_selective_allied_control():
    text = (_CAMPAIGN_DIR / "27.txt").read_text(encoding="utf-8")
    assert "npc_marco_ironhand" in text
    assert "(units_yielded_by raynor 1 npc_marco_ironhand enemy)" in text
    assert "(not (units_yielded_by raynor 1 npc_marco_ironhand enemy))" in text
    assert "(alliance 1 player1 computer1)" in text
    assert "(stop_all_units)" in text
    assert "(stop_all_units computer1)" in text
    assert "(stop_all_units computer3)" in text
    assert "(stop_all_units computer4)" in text
    assert "(allied_control computer1 o8 8 npc_knight_escort)" in text
    assert "(release_yielded_units computer1)" in text
    assert "(set_campaign_flag ch27_marco)" in text
    assert "npc_footman_escort" in text
    assert "npc_archer_escort" in text
    assert "(campaign_flag ch24_garrek)" in text
    assert "(campaign_flag ch26_vera)" in text
    assert "(has_killed 6 traitor_guard enemy)" in text
    assert "(cut_scene 7719)" in text
    assert "7580" not in text
    assert "(has_entered o8 raynor)" in text
    assert "starting_units raynor7" in text
    assert "raynor77" not in text
    assert "(set_map_flag ch27_duel_started)" in text
    assert "(map_flag ch27_duel_started)" in text
    assert "(unset_campaign_flag ch27_duel_started)" in text
    assert "(cut_scene 7718)" in text
    assert "(set_ai_mode offensive o8 1 npc_marco_ironhand)" in text
    assert "(order (o8 8 npc_knight_escort) ((go o1)))" in text
    assert "(order (o8 8 npc_footman_escort) ((go o1)))" in text
    assert "(order (o8 8 npc_archer_escort) ((go o1)))" in text
    assert "(set_map_flag ch27_escorts_return)" in text
    assert "(order (o1 8 npc_knight_escort) ((go o8)))" in text
    assert "(order (o1 8 npc_footman_escort) ((go o8)))" in text
    assert "(order (o1 8 npc_archer_escort) ((go o8)))" in text


def test_script_npc_name_is_npc_not_ai_timers_login():
    """结盟请求等语音应播报 NPC，而非内部 login ai_timers。"""
    from soundrts.worldplayerbase import Player

    world = _StubWorld([])
    world.is_campaign = True
    computer = Player.__new__(Player)
    computer.world = world
    computer.AI_type = "timers"
    computer.neutral = False
    object.__setattr__(computer, "is_human", False)
    computer.client = type("C", (), {"login": "ai_timers"})()

    name = computer.name
    assert name != ["ai_timers"]
    flat = "".join(str(x) for x in name)
    assert "NPC" in flat


def test_allied_assist_switches_chase_without_control():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Lord")
    escort = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e1")
    escort.ai_mode = "guard"
    escort.mdg = 3
    world = _StubWorld([human, computer])
    t = _make_triggers(human, world)
    t.lang_allied_assist(["computer1"])
    assert computer not in human.allied_control
    assert escort.ai_mode == "chase"


def test_allied_assist_switches_offensive_units_to_chase():
    """第25章罗兰比武后为 offensive，结盟后 allied_assist 应切追击。"""
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Count Roland")
    count = _StubUnit(computer, type_name="npc_count_roland", unit_id="r1")
    brother = _StubUnit(computer, type_name="npc_roland_guard", unit_id="r2")
    for u in (count, brother):
        u.ai_mode = "offensive"
        u.mdg = 10
    world = _StubWorld([human, computer])
    t = _make_triggers(human, world)
    t.lang_allied_assist(["computer1"])
    assert count.ai_mode == "chase"
    assert brother.ai_mode == "chase"


def test_allied_assist_selective_units_only():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Lord")
    square = types.SimpleNamespace(objects=[], name="1,1")
    archer = _StubUnit(computer, type_name="npc_archer_escort", unit_id="a1")
    footman = _StubUnit(computer, type_name="npc_footman_escort", unit_id="f1")
    escort = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e1")
    for u in (archer, footman, escort):
        u.ai_mode = "guard"
        u.mdg = 3
    square.objects = [archer, footman, escort]
    world = _StubWorld([human, computer])
    world.grid = {"1,1": square}
    world.squares = [square]

    t = _make_triggers(human, world)
    t.lang_allied_assist(["computer1", "b2", "1", "npc_archer_escort"])

    assert computer not in human.allied_control
    assert archer.ai_mode == "chase"
    assert footman.ai_mode == "guard"
    assert escort.ai_mode == "guard"


def test_allied_control_finds_units_by_map_select_after_move():
    """第27章：骑士离开 c2 后仍应按刷出序号移交指挥权。"""
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    human.client = type("C", (), {"alliance": 1})()
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Marco")
    computer.client = type("C", (), {"alliance": "ai"})()
    spawn_sq = types.SimpleNamespace(objects=[], name="1,1")
    fight_sq = types.SimpleNamespace(objects=[], name="2,2")
    escorts = []
    for i in range(1, 5):
        u = _StubUnit(computer, type_name="npc_knight_escort", unit_id=f"e{i}")
        u.ai_mode = "guard"
        u.mdg = 3
        u.map_select_square = "1,1"
        u.map_select_type = "npc_knight_escort"
        u.map_select_index = i
        u.place = fight_sq
        escorts.append(u)
    footman = _StubUnit(computer, type_name="npc_footman_escort", unit_id="f1")
    footman.mdg = 3
    footman.map_select_square = "1,1"
    footman.map_select_type = "npc_footman_escort"
    footman.map_select_index = 1
    footman.place = fight_sq
    spawn_sq.objects = escorts + [footman]
    fight_sq.objects = escorts + [footman]
    world = _StubWorld([human, computer])
    world.grid = {"1,1": spawn_sq, "2,2": fight_sq}
    world.squares = [spawn_sq, fight_sq]

    t = _make_triggers(human, world)
    t.lang_allied_control(["computer1", "b2", "4", "npc_knight_escort"])

    for u in escorts:
        assert u in human.allied_control_units_set
    assert footman not in human.allied_control_units_set


def test_allied_control_units_not_attackable_by_controller():
    from soundrts.tests.test_yield_on_defeat_and_campaign_flags import (
        _StubPlayer as _CombatStubPlayer,
        _StubWorld as _CombatStubWorld,
        _YieldUnit,
    )

    human = _CombatStubPlayer()
    human.id = "h1"
    human.allied = [human]
    computer = _CombatStubPlayer()
    computer.id = "ai1"
    world = _CombatStubWorld([human, computer])
    human.world = world
    escort = _YieldUnit()
    escort.id = "e1"
    escort.type_name = "npc_knight_escort"
    escort.player = computer
    escort.world = world
    escort.yield_on_defeat = 0
    computer.units = [escort]
    knight = _YieldUnit()
    knight.id = "k1"
    knight.type_name = "knight"
    knight.player = human
    knight.world = world
    knight.yield_on_defeat = 0
    knight.orders = []
    knight.action_target = escort
    human.units = [knight]

    assert knight.is_an_enemy(escort) is True

    from soundrts.worldplayerbase.allied_control import mark_allied_control_changed
    human.allied_control_units_set = {escort}
    mark_allied_control_changed(world)
    TriggersMixin._ceasefire_for_allied_control_units(human, human, [escort])

    assert knight.is_an_enemy(escort) is False
    assert knight.action_target is None
    assert human.is_an_enemy(escort) is False


def test_allied_control_grants_command_and_switches_chase():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Lord")
    escort = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e1")
    escort.ai_mode = "guard"
    escort.mdg = 3
    world = _StubWorld([human, computer])
    t = _make_triggers(human, world)
    t.lang_allied_control(["computer1"])
    assert computer in human.allied_control
    assert escort.ai_mode == "chase"


def test_allied_control_selective_units_only():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _StubPlayer(is_human=False, player_id="ai1", name="Lord")
    square = types.SimpleNamespace(objects=[], name="1,1")
    escort1 = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e1")
    escort2 = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e2")
    archer = _StubUnit(computer, type_name="archer", unit_id="a1")
    leader = _StubUnit(computer, type_name="npc_knight_leader", unit_id="l1")
    for u in (escort1, escort2, archer, leader):
        u.ai_mode = "guard"
        u.mdg = 3
    square.objects = [escort1, escort2, archer, leader]
    world = _StubWorld([human, computer])
    world.grid = {"1,1": square}
    world.squares = [square]

    t = _make_triggers(human, world)
    t.lang_allied_control(["computer1", "b2", "2", "npc_knight_escort"])

    assert computer not in human.allied_control
    assert escort1 in human.allied_control_units_set
    assert escort2 in human.allied_control_units_set
    assert archer not in human.allied_control_units_set
    assert leader not in human.allied_control_units_set
    assert human.unit_under_allied_control(escort1)
    assert not human.unit_under_allied_control(archer)
    assert escort1.ai_mode == "guard"
    assert archer.ai_mode == "chase"
    assert leader.ai_mode == "chase"
    assert escort1 in human.allied_control_units
    assert archer not in human.allied_control_units


@patch("soundrts.lib.sound.pause_music")
def test_register_objective_no_premature_victory(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_register_objective(["1", "2"])
    t.lang_add_objective(["1", "7583"])
    assert len(human.objectives) == 1
    assert human._required_objective_numbers == {"1", "2"}
    t.lang_objective_complete(["1"])
    assert human.has_victory is False
    assert "1" in human._completed_objective_numbers
    assert Objective.storage_key("2", optional=False) not in human.objectives


@patch("soundrts.lib.sound.pause_music")
def test_register_objective_progressive_reveal(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_register_objective(["1", "2"])
    t.lang_add_objective(["1", "7583"])
    assert list(human.objectives.keys()) == [Objective.storage_key("1", optional=False)]
    t.lang_objective_complete(["1"])
    t.lang_add_objective(["2", "7584"])
    assert list(human.objectives.keys()) == [Objective.storage_key("2", optional=False)]
    t.lang_objective_complete(["2"])
    assert human.has_victory is True


@patch("soundrts.lib.sound.pause_music")
def test_add_objective_announces_number_for_raynor_style_timer_triggers(_pause_music):
    from soundrts import msgparts as mp
    from soundrts.lib.msgs import nb2msg

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    human.triggers = [
        (["timer", "0"], ["add_objective", "1", "4660"]),
        (["timer", "0"], ["add_objective", "2", "99"]),
    ]
    human._planned_primary_objective_numbers = {"1", "2"}
    human._planned_secondary_objective_numbers = set()
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_objective(["1", "4660"])
    assert human.voice[0] == mp.PRIMARY_OBJECTIVE + nb2msg(1) + mp.COLON + ["4660"]


@patch("soundrts.lib.sound.pause_music")
def test_add_objective_announces_number_when_multiple_registered(_pause_music):
    from soundrts import msgparts as mp
    from soundrts.lib.msgs import nb2msg

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_register_objective(["1", "2"])
    t.lang_add_objective(["1", "7583"])
    assert human.voice[0] == mp.PRIMARY_OBJECTIVE + nb2msg(1) + mp.COLON + ["7583"]


@patch("soundrts.lib.sound.pause_music")
def test_add_objective_announces_primary_and_secondary_prefix(_pause_music):
    from soundrts import msgparts as mp
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_objective(["1", "7583"])
    t.lang_add_secondary_objective(["1", "7599"])
    assert human.voice[0] == mp.PRIMARY_OBJECTIVE + mp.COLON + ["7583"]
    assert human.voice[1] == mp.SECONDARY_OBJECTIVE + mp.COLON + ["7599"]
    assert Objective.storage_key("1", optional=False) in human.objectives
    assert Objective.storage_key("1", optional=True) in human.objectives


@patch("soundrts.lib.sound.pause_music")
def test_primary_and_secondary_objectives_use_independent_numbers(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_objective(["1", "7583"])
    t.lang_add_secondary_objective(["1", "7599"])
    assert Objective.storage_key("1", optional=False) in human.objectives
    assert Objective.storage_key("1", optional=True) in human.objectives


@patch("soundrts.lib.sound.pause_music")
def test_secondary_objective_not_required_for_victory(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_objective(["1", "7583"])
    t.lang_add_objective(["2", "7584"])
    t.lang_objective_complete(["1"])
    assert human.has_victory is False
    t.lang_add_secondary_objective(["1", "7599"])
    assert Objective.storage_key("1", optional=True) in human.objectives
    assert len(human._required_objective_numbers) == 2
    t.lang_objective_complete(["2"])
    assert human.has_victory is True
    assert Objective.storage_key("1", optional=True) in human.objectives


@patch("soundrts.lib.sound.pause_music")
def test_objective_abandon_removes_secondary_only(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_secondary_objective(["1", "7599"])
    t.lang_objective_abandon(["1"])
    assert Objective.storage_key("1", optional=True) not in human.objectives
    t.lang_add_objective(["1", "7583"])
    t.lang_objective_abandon(["1"])
    assert Objective.storage_key("1", optional=False) in human.objectives


@patch("soundrts.lib.sound.pause_music")
def test_secondary_objective_complete_only_affects_secondary(_pause_music):
    from soundrts.worldplayerbase.base import Objective

    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    world = _StubWorld([human])
    t = _make_triggers(human, world)
    t.lang_add_objective(["1", "7583"])
    t.lang_add_secondary_objective(["1", "7599"])
    t.lang_secondary_objective_complete(["1"])
    assert Objective.storage_key("1", optional=True) not in human.objectives
    assert Objective.storage_key("1", optional=False) in human.objectives


def test_chapter_25_uses_duel_and_optional_alliance():
    text = (_CAMPAIGN_DIR / "25.txt").read_text(encoding="utf-8")
    assert "npc_count_roland" in text
    assert "garrek_token" in text
    assert "(npc_has_item npc_count_roland garrek_token o8)" in text
    assert "(set_ai_mode offensive o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_yield_on_defeat 1 o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_campaign_flag ch25_duel_started)" in text
    assert "trigger players (npc_has_item npc_count_roland garrek_token o8) (do (cut_scene 7701)" in text
    assert "(set_campaign_flag ch25_duel_started))" in text.split("(cut_scene 7701)")[1].split("trigger computer1")[0]
    assert "trigger computer1 (npc_has_item npc_count_roland garrek_token o8) (do (set_ai_mode offensive" in text
    assert "(campaign_flag ch25_duel_started)" in text
    assert "(key_unit_killed npc_count_roland npc_roland_guard)" in text
    assert "trigger players (and (not (campaign_flag ch25_duel_started)) (key_unit_killed npc_count_roland npc_roland_guard)) (defeat)" in text
    assert "(campaign_flag ch24_garrek_token)" in text
    assert "(add_inventory_item garrek_token 1 raynor)" in text
    assert "(add_objective 1 7717)" in text
    assert "intro 7728 7729 7700" in text
    assert "7701" not in text.split("intro")[1].split("\n")[0]
    assert "(units_yielded 1 npc_count_roland 6 npc_roland_guard enemy)" in text
    assert "(alliance_request computer1)" in text
    assert "(allied_assist computer1)" in text
    assert "(alliance_with computer1)" in text
    assert "(alliance_declined_with computer1)" in text
    assert "(add_units h8 6 knight)" in text
    assert "(set_campaign_flag ch25_roland_allied)" in text
    assert "(set_campaign_flag ch25_roland_knights)" in text
    assert "(campaign_flag ch24_garrek)" in text
    assert "(add_secondary_objective 1 7599)" in text
    assert "(stop_all_units)" in text
    assert "(stop_all_units computer1)" in text
    assert "(release_yielded_units computer1)" in text
    assert "trigger players (no_unit_left) (defeat)" in text
    assert "trigger all (no_unit_left)" not in text
    assert "(transfer_units" not in text
    assert "secret_letter" not in text


def test_chapter_26_uses_banner_transfer_units():
    text = (_CAMPAIGN_DIR / "26.txt").read_text(encoding="utf-8")
    assert "war_banner h1" in text
    assert "npc_general_vera" in text
    assert "(transfer_units computer1 player1)" in text
    assert "(npc_has_item npc_general_vera war_banner o8)" in text
    assert "(set_campaign_flag ch26_vera)" in text
    assert "(has_killed 6 traitor_guard enemy)" in text
    assert "(campaign_flag ch25_roland_allied)" in text


def test_convert_units_and_change_owner_are_aliases():
    human, computer, world = _human_and_computer()
    knight = _StubUnit(computer, type_name="knight", unit_id="k1")
    t = _make_triggers(human, world)
    t.lang_convert_units(["computer1", "player1"])
    assert knight.player is human
    knight.player = computer
    computer.units = [knight]
    human.units = []
    t.lang_change_owner(["computer1", "player1"])
    assert knight.player is human


def test_has_killed_counts_own_enemy_kills():
    human, computer, world = _human_and_computer()
    traitor_owner = _StubPlayer(is_human=False, player_id="ai2", name="Traitors")
    world.players.append(traitor_owner)
    t = _make_triggers(human, world)
    for i in range(3):
        human.record_unit_killed(_StubVictim(traitor_owner, unit_id=f"v{i}"))
    assert t.lang_has_killed(["3", "traitor_guard", "enemy"]) is True


def test_has_killed_counts_allied_and_controlled_kills():
    """ch24/25：盟友或 allied_control 击杀应计入玩家 has_killed 目标。"""
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    traitor_owner = _StubPlayer(is_human=False, player_id="ai2", name="Traitors")
    world = _StubWorld([human, computer, traitor_owner])
    human.allied = [human, computer]
    human.allied_control = (human, computer)
    t = _make_triggers(human, world)
    for i in range(3):
        computer.record_unit_killed(_StubVictim(traitor_owner, unit_id=f"v{i}"))
    assert getattr(human, "_killed_enemy_unit_counts", {}).get("traitor_guard", 0) == 0
    assert t.lang_has_killed(["3", "traitor_guard", "enemy"]) is True


def test_has_killed_counts_coop_human_ally_kills():
    """合作战役：另一名人类盟友的击杀计入团队 has_killed。"""
    human1 = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    human2 = _TriggerOwner(is_human=True, player_id="h2", name="Player 2")
    traitor_owner = _StubPlayer(is_human=False, player_id="ai2", name="Traitors")
    world = _StubWorld([human1, human2, traitor_owner])
    human1.allied = [human1, human2]
    human2.allied = [human1, human2]
    t = _make_triggers(human1, world)
    for i in range(3):
        human2.record_unit_killed(_StubVictim(traitor_owner, unit_id=f"v{i}"))
    assert t.lang_has_killed(["3", "traitor_guard", "enemy"]) is True


def test_has_killed_does_not_count_non_allied_kills():
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    traitor_owner = _StubPlayer(is_human=False, player_id="ai2", name="Traitors")
    world = _StubWorld([human, computer, traitor_owner])
    t = _make_triggers(human, world)
    for i in range(3):
        computer.record_unit_killed(_StubVictim(traitor_owner, unit_id=f"v{i}"))
    assert t.lang_has_killed(["3", "traitor_guard", "enemy"]) is False


def test_chapters_traitor_guard_spawn_line_matches_has_killed():
    """24–27 关均刷 12 个 traitor_guard，与 has_killed 6 一致（需清剿半数刺客）。"""
    for chapter in ("24", "25", "26", "27"):
        text = (_CAMPAIGN_DIR / f"{chapter}.txt").read_text(encoding="utf-8")
        assert "(has_killed 6 traitor_guard enemy)" in text
        if chapter == "24":
            assert "h15 4 traitor_guard 4 traitor_guard" in text
            assert "o15 4 traitor_guard" in text
        else:
            assert "h15 6 traitor_guard o15 6 traitor_guard" in text


def test_chapter_27_carryover_slots_separate_from_traitors():
    """第27章：computer3/4 为继承占位，不得与宰相杀手混在同一玩家槽。"""
    text = (_CAMPAIGN_DIR / "27.txt").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("computer_only")]
    assert "traitor_guard" in lines[1]
    assert lines[2] == "computer_only 0 0 non_neutral a2"
    assert lines[3] == "computer_only 0 0 non_neutral a3"
    assert "traitor_guard" not in lines[2]
    assert "traitor_guard" not in lines[3]
    assert (
        "trigger computer3 (timer 0) (if (campaign_flag ch24_garrek) "
        "(do (add_units a2 1 npc_knight_leader"
    ) in text
    assert "(allied_control computer3)" in text


def test_chapter_28_carryover_computer5_slot_exists():
    """第28章：computer5 为马尔科继承占位，触发器须能解析到该槽。"""
    text = (_CAMPAIGN_DIR / "28.txt").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("computer_only")]
    assert lines[4] == "computer_only 0 0 non_neutral b30"
    assert "trigger computer5 (timer 0) (if (campaign_flag ch27_marco)" in text
    assert "(allied_control computer5)" in text


def test_killed_target_map_select_index_only_specific_unit():
    """序号格式：仅击杀指定序号的单位时成立。"""
    human, computer, world = _human_and_computer()
    t = _make_triggers(human, world)

    v1 = _StubVictim(computer, type_name="footman", unit_id="f1")
    v1.map_select_square = "1,1"
    v1.map_select_type = "footman"
    v1.map_select_index = 1
    v3 = _StubVictim(computer, type_name="footman", unit_id="f3")
    v3.map_select_square = "1,1"
    v3.map_select_type = "footman"
    v3.map_select_index = 3

    t.record_unit_killed(v1)
    assert t.lang_killed_target(["1,1", "1", "footman", "enemy"]) is True
    assert t.lang_killed_target(["1,1", "3", "footman", "enemy"]) is False

    t.record_unit_killed(v3)
    assert t.lang_killed_target(["1,1", "3", "footman", "enemy"]) is True


def test_killed_target_global_index_only_specific_unit():
    """全局序号：仅击杀该类型第 N 个刷出单位时成立（与方格无关）。"""
    human, computer, world = _human_and_computer()
    t = _make_triggers(human, world)

    v1 = _StubVictim(computer, type_name="footman", unit_id="f1")
    v1.map_select_global_index = 1
    v3 = _StubVictim(computer, type_name="footman", unit_id="f3")
    v3.map_select_global_index = 3

    t.record_unit_killed(v1)
    assert t.lang_killed_target(["1", "footman", "enemy"]) is True
    assert t.lang_killed_target(["3", "footman", "enemy"]) is False

    t.record_unit_killed(v3)
    assert t.lang_killed_target(["3", "footman", "enemy"]) is True


def test_killed_target_map_select_index_team_kills():
    """合作/盟友补刀计入序号击杀目标。"""
    human, computer, world = _human_and_computer()
    human2 = _TriggerOwner(is_human=True, player_id="h2", name="Player 2")
    human2.allied = [human, human2]
    human.allied = [human, human2]
    world.players.append(human2)
    human2.world = world

    t = _make_triggers(human, world)
    v3 = _StubVictim(computer, type_name="footman", unit_id="f3")
    v3.map_select_square = "2,2"
    v3.map_select_type = "footman"
    v3.map_select_index = 3
    human2.record_unit_killed(v3)
    assert t.lang_killed_target(["2,2", "3", "footman", "enemy"]) is True


def test_assign_map_select_slot_increments_per_square_and_type():
    human, computer, world = _human_and_computer()
    square = types.SimpleNamespace(objects=[], name="1,1")
    world.grid = {"1,1": square}
    t = _make_triggers(human, world)

    u1 = types.SimpleNamespace(type_name="footman")
    u2 = types.SimpleNamespace(type_name="footman")
    u3 = types.SimpleNamespace(type_name="archer")
    t._assign_map_select_slot(u1, square)
    t._assign_map_select_slot(u2, square)
    t._assign_map_select_slot(u3, square)

    assert u1.map_select_index == 1
    assert u2.map_select_index == 2
    assert u3.map_select_index == 1
    assert u1.map_select_square == "1,1"
    assert u3.map_select_type == "archer"


def test_used_skill_records_and_matches_basic_usage():
    human, _computer, world = _human_and_computer()
    t = _make_triggers(human, world)
    caster = types.SimpleNamespace(type_name="marine")
    assert t.lang_used_skill(["sc_stim_pack"]) is False
    t.record_skill_used("sc_stim_pack", caster=caster)
    assert t.lang_used_skill(["sc_stim_pack"]) is True
    assert t.lang_used_skill(["sc_stim_pack", "marauder"]) is False
    assert t.lang_used_skill(["sc_stim_pack", "marine"]) is True


def test_used_skill_matches_caster_and_target_filters():
    human, _computer, world = _human_and_computer()
    t = _make_triggers(human, world)
    queen = types.SimpleNamespace(type_name="queen")
    hatchery = types.SimpleNamespace(type_name="hatchery")
    t.record_skill_used("sc_spawn_larva", caster=queen, target=hatchery)
    assert t.lang_used_skill(["sc_spawn_larva", "queen", "hatchery"]) is True
    assert t.lang_used_skill(["sc_spawn_larva", "queen", "nexus"]) is False
    assert t.lang_used_skill(["2", "sc_spawn_larva"]) is False
    t.record_skill_used("sc_spawn_larva", caster=queen, target=hatchery)
    assert t.lang_used_skill(["2", "sc_spawn_larva"]) is True
