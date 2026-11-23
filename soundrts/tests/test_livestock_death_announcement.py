"""牲口死亡的播报措辞：不该说成「阵亡 / 被消灭」。

背景：
  玩家用 ``claim`` 把中立羊收归自己后，敌方斥候骑兵杀死这只羊，客户端
  原本会播报两条军事化提示：

      羊 被消灭 在 2 , 1
      羊 阵亡 在 2 , 1

  一只羊既不是「被消灭的敌人」，也不是「阵亡的军事单位」。现在它走独立的
  ``slaughtered_units`` 队列，用专门的「被宰杀」措辞播报：

      羊 被宰杀 在 2 , 1
"""

from __future__ import annotations

import types
from pathlib import Path

from soundrts import msgparts as mp

ROOT = Path(__file__).resolve().parents[2]


class _FakePlace:
    def __init__(self, title=None):
        # 真实 Place.title 是 TTS 消息 id 列表（例如 [51, 55, 62]）。
        self.title = title if title is not None else [51, 55, 62]


class _FakeEntityView:
    """最小化的 EntityView，用于直接调用 ``on_death_by``。"""

    def __init__(self, model, interface, player=None, place=None, short_title=None):
        self.model = model
        self.interface = interface
        self.player = player
        self.place = place or _FakePlace()
        self.short_title = short_title or ["sheep_title"]
        self.id = 1
        self.menace = False

    # ``on_death_by`` 结尾会统计「还有没有友军」，这里没有友军即可。
    @property
    def units(self):
        return []

    # 最后一个单位倒下时会触发战斗结束播报，这里只需要它不炸。
    def on_lose_fight(self):
        pass

    def _check_battle_status_for_music(self):
        pass


def _make_player():
    """一个玩家。``units`` 为空，所以死亡时没有友军需要播报。"""
    return types.SimpleNamespace(units=[])


def _make_interface():
    return types.SimpleNamespace(
        player=_make_player(),
        lost_units=[],
        neutralized_units=[],
        slaughtered_units=[],
        new_enemy_units=[],
        dobjets={},
    )


def _make_attacker(player, attacker_id):
    """攻击者视图（需要 ``on_win_fight``，因为最后一只羊倒下时会调用它）。"""
    return types.SimpleNamespace(
        player=player,
        id=attacker_id,
        on_win_fight=lambda: None,
    )


def _sheep_model():
    """一只羊的模型（herdable + claimable，跟 mods/aoe2/rules.txt 一致）。"""
    return types.SimpleNamespace(
        type_name="sheep",
        herdable=1,
        claimable=1,
        is_huntable=1,
        player=None,
    )


def _knight_model():
    return types.SimpleNamespace(
        type_name="scout_cavalry",
        herdable=0,
        claimable=0,
        is_huntable=0,
        player=None,
    )


def test_msgpart_slaughtered_defined():
    assert mp.SLAUGHTERED == [7810]


def test_slaughtered_phrase_present_in_every_language():
    """每个语言的 tts.txt 都要有 7810，否则会读不出声音。"""
    for folder in (
        "ui",
        "ui-be",
        "ui-cs",
        "ui-de",
        "ui-es",
        "ui-fr",
        "ui-it",
        "ui-pl",
        "ui-pt-BR",
        "ui-ru",
        "ui-sk",
        "ui-vi",
        "ui-zh",
    ):
        path = ROOT / "res" / folder / "tts.txt"
        text = path.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.startswith("7810\t")]
        assert lines, f"{folder}/tts.txt is missing id 7810"
        assert lines[0].split("\t", 1)[1].strip(), f"{folder}/tts.txt 7810 is empty"


def test_sheep_death_is_announced_as_slaughtered_not_lost_or_neutralized():
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    enemy = _make_player()

    sheep = _sheep_model()
    sheep.player = local
    view = _FakeEntityView(sheep, interface, player=local)

    # 敌方斥候骑兵杀掉了我的羊。
    attacker = _make_attacker(enemy, 42)
    interface.dobjets[42] = attacker

    EntityViewEvents.on_death_by(view, 42)

    assert len(interface.slaughtered_units) == 1
    assert interface.lost_units == [], "a dead sheep is not a lost military unit"
    assert interface.neutralized_units == [], "a dead sheep is not a neutralized enemy"


def test_killing_an_animal_is_not_announced_as_neutralized():
    """我方单位杀了一只中立羊 —— 也不算「消灭了敌人」。"""
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    neutral = _make_player()

    sheep = _sheep_model()
    sheep.player = neutral
    view = _FakeEntityView(sheep, interface, player=neutral)

    attacker = _make_attacker(local, 7)
    interface.dobjets[7] = attacker

    EntityViewEvents.on_death_by(view, 7)

    assert len(interface.slaughtered_units) == 1
    assert interface.neutralized_units == []
    assert interface.lost_units == []


def test_military_unit_death_still_uses_lost_and_neutralized():
    """普通军事单位死亡仍旧走「阵亡 / 被消灭」，不能被这次改动波及。"""
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player

    knight = _knight_model()
    knight.player = local
    view = _FakeEntityView(knight, interface, player=local)

    attacker = _make_attacker(_make_player(), 9)
    interface.dobjets[9] = attacker

    EntityViewEvents.on_death_by(view, 9)

    assert interface.slaughtered_units == []
    assert len(interface.lost_units) == 1
    assert interface.neutralized_units == []


def _capture_spoken(monkeypatch, game_unit_control):
    spoken = []

    def fake_info(msg, *args, **kwargs):
        spoken.append(list(msg))

    monkeypatch.setattr(game_unit_control.voice, "info", fake_info)
    return spoken


def test_units_alert_speaks_slaughtered_with_its_own_phrase(monkeypatch):
    """播报队列里，动物用 SLAUGHTERED，军事单位用 LOST / NEUTRALIZED。"""
    from soundrts.clientgame import game_unit_control

    spoken = _capture_spoken(monkeypatch, game_unit_control)

    interface = _make_interface()
    interface.player.is_an_enemy = lambda other: False
    interface.slaughtered_units = [[["sheep_title"], _FakePlace(), False]]
    interface.lost_units = [[["knight_title"], _FakePlace(), False]]
    interface.neutralized_units = [[["scout_title"], _FakePlace(), False]]
    interface.previous_units_alert = None

    game_unit_control.units_alert_if_needed(interface)

    slaughter_lines = [m for m in spoken if mp.SLAUGHTERED[0] in m]
    lost_lines = [m for m in spoken if mp.LOST[0] in m]
    neutralized_lines = [m for m in spoken if mp.NEUTRALIZED[0] in m]

    assert len(slaughter_lines) == 1, "the sheep must be announced once"
    assert mp.LOST[0] not in slaughter_lines[0]
    assert mp.NEUTRALIZED[0] not in slaughter_lines[0]
    assert len(lost_lines) == 1
    assert len(neutralized_lines) == 1
    # 播报后队列被清空。
    assert interface.slaughtered_units == []
    assert interface.lost_units == []
    assert interface.neutralized_units == []


def test_units_alert_if_needed_triggers_on_slaughtered_alone(monkeypatch):
    """只有动物死亡时也要触发播报（不能因为 lost/neutralized 为空而跳过）。"""
    from soundrts.clientgame import game_unit_control

    spoken = _capture_spoken(monkeypatch, game_unit_control)

    interface = _make_interface()
    interface.player.is_an_enemy = lambda other: False
    interface.slaughtered_units = [[["sheep_title"], _FakePlace(), False]]
    interface.previous_units_alert = None

    game_unit_control.units_alert_if_needed(interface)
    assert len(spoken) == 1
    assert mp.SLAUGHTERED[0] in spoken[0]


# ---------------------------------------------------------------------------
# 数量：「1 羊 被宰杀」/「2 羊 被宰杀」/「20 羊 被宰杀」
# ---------------------------------------------------------------------------
def _slaughtered_line(monkeypatch, count):
    """把 ``count`` 只羊放进播报队列，返回实际播出的那一行。"""
    from soundrts.clientgame import game_unit_control
    from soundrts.lib.msgs import nb2msg

    spoken = _capture_spoken(monkeypatch, game_unit_control)

    interface = _make_interface()
    interface.player.is_an_enemy = lambda other: False
    # 同一个 place、同一个标题实例：这样 ``units_alert`` 才会把它们合成一组，
    # 读成「3 羊 被宰杀」而不是三个「1 羊 被宰杀」。
    place = _FakePlace()
    title = ["sheep_title"]
    interface.slaughtered_units = [
        [title, place, False] for _ in range(count)
    ]
    interface.previous_units_alert = None

    game_unit_control.units_alert_if_needed(interface)

    assert len(spoken) == 1, spoken
    return spoken[0]


def test_slaughtered_announcement_spells_out_the_count(monkeypatch):
    """数量必须读出来，和「xx 敌人被消灭」一致。"""
    from soundrts.lib.msgs import nb2msg

    line = _slaughtered_line(monkeypatch, 1)
    assert nb2msg(1)[0] in line, "「1 羊 被宰杀」必须读出数量"
    assert mp.SLAUGHTERED[0] in line

    line = _slaughtered_line(monkeypatch, 2)
    assert nb2msg(2)[0] in line, "「2 羊 被宰杀」必须读出数量"

    line = _slaughtered_line(monkeypatch, 20)
    assert nb2msg(20)[0] in line, "「20 羊 被宰杀」必须读出数量"


def test_slaughtered_announcement_does_not_double_the_count(monkeypatch):
    """数量只能出现一次（标题里已经带序号时不能再加一遍）。"""
    from soundrts.lib.msgs import nb2msg

    line = _slaughtered_line(monkeypatch, 3)
    encoded = nb2msg(3)[0]
    assert line.count(encoded) == 1, line


def test_slaughtered_death_ignores_the_no_number_rule_flag():
    """``no_number 1``（同类型只有一只时不报序号）不能压掉死亡播报的数量。

    帝国 2 的羊 / 鹿 / 野猪都带 ``no_number 1``；死亡播报必须照样读数量。
    """
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player

    sheep = _sheep_model()
    sheep.player = local
    sheep.no_number = 1  # 规则里的 no_number 1
    view = _FakeEntityView(sheep, interface, player=local)

    attacker = _make_attacker(_make_player(), 11)
    interface.dobjets[11] = attacker

    EntityViewEvents.on_death_by(view, 11)

    assert len(interface.slaughtered_units) == 1
    title, place, omit_single_count = interface.slaughtered_units[0]
    assert omit_single_count is False, "死亡播报必须始终读出数量"


# ---------------------------------------------------------------------------
# 自己人打自己的羊：不播报
# ---------------------------------------------------------------------------
def test_own_unit_killing_own_sheep_is_not_announced():
    """自己攻击自己的羊不播报「羊 被宰杀」。

    玩家是自己动手的，不需要被告知自己宰掉了自己的羊。
    """
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    local.allied = [local]

    sheep = _sheep_model()
    sheep.player = local
    view = _FakeEntityView(sheep, interface, player=local)

    # 攻击者是自己的单位
    attacker = _make_attacker(local, 21)
    interface.dobjets[21] = attacker

    EntityViewEvents.on_death_by(view, 21)

    assert interface.slaughtered_units == [], "自己打自己的羊不该播报"
    assert interface.lost_units == []
    assert interface.neutralized_units == []


def test_ally_unit_killing_my_sheep_is_not_announced():
    """盟友打死我的羊也不播报（盟友是友方）。"""
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    ally = _make_player()
    local.allied = [local, ally]

    sheep = _sheep_model()
    sheep.player = local
    view = _FakeEntityView(sheep, interface, player=local)

    attacker = _make_attacker(ally, 22)
    interface.dobjets[22] = attacker

    EntityViewEvents.on_death_by(view, 22)

    assert interface.slaughtered_units == [], "盟友打死我的羊不该播报"


def test_hunting_a_neutral_sheep_with_my_own_unit_is_announced():
    """打中立（还没归属）的羊是正常狩猎 —— 仍然要播报。

    友好误伤的豁免只针对「我名下」的羊；狩猎中立羊是主动行为，
    玩家需要知道自己的羊群/猎获情况。
    """
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    local.allied = [local]
    neutral = _make_player()

    sheep = _sheep_model()
    sheep.player = neutral
    view = _FakeEntityView(sheep, interface, player=neutral)

    attacker = _make_attacker(local, 24)
    interface.dobjets[24] = attacker

    EntityViewEvents.on_death_by(view, 24)

    assert len(interface.slaughtered_units) == 1, "狩猎中立羊必须播报"


def test_enemy_killing_my_sheep_is_still_announced():
    """敌人打死我的羊仍然要播报（不能被友好误伤判断误伤）。"""
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    local.allied = [local]

    sheep = _sheep_model()
    sheep.player = local
    view = _FakeEntityView(sheep, interface, player=local)

    enemy = _make_player()
    attacker = _make_attacker(enemy, 23)
    interface.dobjects = interface.dobjets
    interface.dobjets[23] = attacker

    EntityViewEvents.on_death_by(view, 23)

    assert len(interface.slaughtered_units) == 1, "敌人打死我的羊必须播报"


def test_no_announcement_when_announcer_without_player():
    """没有攻击者信息（attacker 为 None）时按「不是自己人」处理，仍然播报。"""
    from soundrts.clientgameentity.events import EntityViewEvents

    interface = _make_interface()
    local = interface.player
    local.allied = [local]

    sheep = _sheep_model()
    sheep.player = local
    view = _FakeEntityView(sheep, interface, player=local)

    EntityViewEvents.on_death_by(view, 999)  # 没有这个 id -> attacker 为 None

    assert len(interface.slaughtered_units) == 1
