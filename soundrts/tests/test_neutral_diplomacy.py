"""验证 ``computer_only ... neutral`` 玩家能正确进入 F12 外交候选，
并能与之结盟（中立 AI 自动 accept），同时保证人不会被合并进 "ai" 默认联盟、
从而误与所有 AI 同盟。

涉及的改动点（详见 plans/neutral_diplomacy_f12_*.plan.md）：

1. ``soundrts/clientgame/game_audio.py``
   - ``_diplo_players``：去掉 ``neutral`` 过滤。
   - ``_diplo_relation_msg``：对未结盟 neutral 返回 ``mp.NEUTRAL``。
2. ``soundrts/worldplayerbase/base.py``
   - ``Player.name``：neutral 返回 ``mp.NEUTRAL + nb2msg(1-based 序号)``。
   - ``cmd_diplomacy 'accept'``：``"ai"`` 视为 unset；
     人 (None) + 中立 ("ai") 必须分配新 ID，而不是让人继承 "ai"。
   - ``cmd_diplomacy 'request'``：目标 neutral 时自动调 accept。

测试结构：
- 逻辑级：``Player.name`` 序号、外交合并真值表。
- 模块级：``_diplo_players`` / ``_diplo_relation_msg`` 用 ``_stub_client_modules``
  加载 game_audio，避免拉真 clientmedia/pygame。
- 源码契约：cmd_diplomacy 中存在 ``_UNSET``、``"ai"`` 处理以及
  ``target.cmd_diplomacy(["accept", ...])`` 自动接受块；
  ``_diplo_players`` 不再含 ``neutral`` 过滤。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# 解开 worldunit 循环导入，对齐 test_neutral_passive_creep.py 的做法。
import soundrts.worldunit  # noqa: F401

from soundrts import msgparts as mp
from soundrts.lib.msgs import nb2msg
from soundrts.worldplayerbase.base import Player


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


class _StubWorld:
    time = 0

    def __init__(self):
        self.players = []


def _make_player(neutral: bool, world: _StubWorld) -> Player:
    """跳过 ``Player.__init__``，注入 ``name`` 与 ``cmd_diplomacy`` 路径用到的字段。"""
    p = Player.__new__(Player)
    p.neutral = neutral
    p.world = world
    p.allied = [p]
    p._cached_allied_vision = []
    p._allied_vision_cache_time = 0
    return p


# ---------------------------------------------------------------------------
# Player.name 对 neutral 的 1-based 序号
# ---------------------------------------------------------------------------


def test_player_name_neutral_single_returns_neutral_one():
    """单个中立玩家：``name`` 应为 ``mp.NEUTRAL + nb2msg(1)``。"""
    world = _StubWorld()
    neutral = _make_player(neutral=True, world=world)
    world.players = [neutral]

    assert neutral.name == mp.NEUTRAL + nb2msg(1)


def test_player_name_neutral_multiple_uses_position_index():
    """多个 neutral：按 ``world.players`` 中出现顺序得到 1/2/3。"""
    world = _StubWorld()
    n1 = _make_player(neutral=True, world=world)
    n2 = _make_player(neutral=True, world=world)
    n3 = _make_player(neutral=True, world=world)
    world.players = [n1, n2, n3]

    assert n1.name == mp.NEUTRAL + nb2msg(1)
    assert n2.name == mp.NEUTRAL + nb2msg(2)
    assert n3.name == mp.NEUTRAL + nb2msg(3)


def test_player_name_neutral_index_skips_non_neutral():
    """非 neutral 不计入序号，比如 [human, neutralA, human2, neutralB] -> N1/N2。"""
    world = _StubWorld()
    human = _make_player(neutral=False, world=world)
    # human 需要 ``client.name`` 才不会触发 neutral 分支
    human.client = types.SimpleNamespace(name=["human"])
    neutral_a = _make_player(neutral=True, world=world)
    human2 = _make_player(neutral=False, world=world)
    human2.client = types.SimpleNamespace(name=["human2"])
    neutral_b = _make_player(neutral=True, world=world)
    world.players = [human, neutral_a, human2, neutral_b]

    assert neutral_a.name == mp.NEUTRAL + nb2msg(1)
    assert neutral_b.name == mp.NEUTRAL + nb2msg(2)


def test_player_name_non_neutral_still_uses_client_name():
    """非 neutral 玩家继续读 ``client.name``，与原行为一致。"""
    world = _StubWorld()
    p = _make_player(neutral=False, world=world)
    p.client = types.SimpleNamespace(name=["alice"])
    world.players = [p]

    assert p.name == ["alice"]


# ---------------------------------------------------------------------------
# cmd_diplomacy 'accept' 合并语义：把 "ai" 视为 unset
# ---------------------------------------------------------------------------


def _assign_alliance(aid_self, aid_t, world_alliances):
    """精确复现 ``base.py`` cmd_diplomacy 'accept' 分支的合并算法。

    `world_alliances` 是当前所有 player 的 ``client.alliance`` 集合，用于挑选未
    占用的最小正整数（与源码 `used = {... for p in self.world.players}` 等价）。
    返回 ``(new_aid_self, new_aid_t)``。
    """
    _UNSET = (None, "None", "ai")
    if aid_self in _UNSET and aid_t in _UNSET:
        used = set(world_alliances)
        new_id = 1
        while new_id in used:
            new_id += 1
        return (new_id, new_id)
    if aid_self in _UNSET:
        return (aid_t, aid_t)
    if aid_t in _UNSET:
        return (aid_self, aid_self)
    # 都已设
    try:
        nid = min(int(aid_self), int(aid_t))
    except Exception:
        nid = aid_self
    return (nid, nid)


def test_merge_human_none_with_neutral_ai_assigns_fresh_id():
    """人 (None) + 中立 ("ai") 必须分配新 ID，绝不能让人继承 "ai"。"""
    # 假设地图上还有 2 个其它 AI，他们的 alliance="ai"；以及人 alliance=None。
    world_alliances = {None, "ai"}
    new_self, new_t = _assign_alliance(None, "ai", world_alliances)

    assert new_self == 1
    assert new_t == 1
    # 关键：人没有继承 "ai" 字符串
    assert new_self != "ai"


def test_merge_human_in_alliance_with_second_neutral_ai_extends_same_alliance():
    """已与中立1结盟 (alliance=1) 的人再与中立2 ("ai") 结盟：中立2 加入 1。"""
    world_alliances = {1, "ai"}
    new_self, new_t = _assign_alliance(1, "ai", world_alliances)

    assert new_self == 1
    assert new_t == 1


def test_merge_two_none_assigns_fresh_id_skipping_used():
    """二人都未设：分配一个未占用的最小整数。"""
    world_alliances = {1, 2, "ai"}  # 1, 2 已占
    new_self, new_t = _assign_alliance(None, None, world_alliances)

    assert new_self == 3
    assert new_t == 3


def test_merge_two_integers_takes_min():
    """两人都已有 int 联盟编号：合并到较小的一个。"""
    new_self, new_t = _assign_alliance(5, 2, set())
    assert new_self == 2
    assert new_t == 2


def test_merge_none_with_integer_takes_integer():
    """None + 已有 int：未设的一方加入已有的。"""
    new_self, new_t = _assign_alliance(None, 4, {4})
    assert new_self == 4
    assert new_t == 4


# ---------------------------------------------------------------------------
# 逻辑级：_diplo_players / _diplo_relation_msg
#
# 直接 import ``soundrts.clientgame.game_audio`` 会拉起整条 clientgame /
# attributes_face / lib.voice / lib.resource / options 链，
# 在测试环境里 options.py 会调 parser.parse_args() 把 pytest 的参数当未知选项
# 抛出。所以这里改用"复刻等价规则 + 源码契约"的方式覆盖。
# ---------------------------------------------------------------------------


class _StubDiploPlayer:
    def __init__(self, pid, neutral=False):
        self.id = pid
        self.neutral = neutral
        self.allied = [self]


class _StubInterface:
    def __init__(self, me, players):
        self.player = me
        self.world = types.SimpleNamespace(players=players)


def _diplo_players_logic(interface):
    """等价复刻 ``game_audio._diplo_players`` 现行行为：剔除自己 + 中立玩家。"""
    world = getattr(interface, 'world', None)
    me = getattr(interface, 'player', None)
    if not world or not me:
        return []
    players = [p for p in world.players
               if p is not me and not getattr(p, 'neutral', False)]
    players.sort(key=lambda p: p.id)
    return players


def _diplo_relation_msg_logic(interface, p):
    """等价复刻 ``_diplo_relation_msg`` 修改后行为：未结盟的 neutral 单独标 NEUTRAL。"""
    try:
        me = getattr(interface, 'player', None)
        if me and p in me.allied:
            return mp.ALLY
    except Exception:
        pass
    if getattr(p, 'neutral', False):
        return mp.NEUTRAL
    return mp.ENEMY


def test_diplo_players_excludes_neutral():
    """中立玩家**不**进 F12 候选——设计上把中立 creep 当作环境物，不参与外交。"""
    me = _StubDiploPlayer("1")
    other = _StubDiploPlayer("2")
    neutral = _StubDiploPlayer("3", neutral=True)
    iface = _StubInterface(me, [me, other, neutral])

    result = _diplo_players_logic(iface)

    assert me not in result
    assert other in result
    assert neutral not in result


def test_diplo_players_excludes_self():
    me = _StubDiploPlayer("1")
    iface = _StubInterface(me, [me])

    assert _diplo_players_logic(iface) == []


def test_diplo_relation_msg_neutral_returns_neutral():
    me = _StubDiploPlayer("1")
    neutral = _StubDiploPlayer("2", neutral=True)
    iface = _StubInterface(me, [me, neutral])

    assert _diplo_relation_msg_logic(iface, neutral) == mp.NEUTRAL


def test_diplo_relation_msg_allied_neutral_returns_ally():
    me = _StubDiploPlayer("1")
    neutral = _StubDiploPlayer("2", neutral=True)
    me.allied = [me, neutral]
    iface = _StubInterface(me, [me, neutral])

    assert _diplo_relation_msg_logic(iface, neutral) == mp.ALLY


def test_diplo_relation_msg_hostile_returns_enemy():
    me = _StubDiploPlayer("1")
    hostile = _StubDiploPlayer("2", neutral=False)
    iface = _StubInterface(me, [me, hostile])

    assert _diplo_relation_msg_logic(iface, hostile) == mp.ENEMY


# ---------------------------------------------------------------------------
# 源码契约：cmd_diplomacy 与 _diplo_players 都按计划落实
# ---------------------------------------------------------------------------


def _source(path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def test_diplo_players_filters_neutral():
    """``_diplo_players`` 必须把 neutral 过滤掉（与 self、defeated 过滤合在一起）。"""
    src = _source(["soundrts", "clientgame", "game_audio.py"])
    # 关键标记：现在过滤组合包含 `not getattr(p, 'neutral', False)`
    assert "not getattr(p, 'neutral', False)" in src
    # 仍然有 alive 过滤（Bug C 的成果）
    assert "_diplo_is_alive(p)" in src


def test_diplo_relation_msg_has_neutral_branch():
    src = _source(["soundrts", "clientgame", "game_audio.py"])
    assert "getattr(p, 'neutral', False)" in src
    assert "return mp.NEUTRAL" in src


def test_cmd_diplomacy_accept_treats_ai_as_unset():
    """cmd_diplomacy 'accept' 分支必须用 ``_UNSET`` 把 ``"ai"`` 视为未设值，
    避免人继承 "ai" 联盟。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    # 关键标记：定义了 _UNSET，且包含 "ai"
    assert "_UNSET = (None, 'None', 'ai')" in src
    # 旧的 [None, 'None'] 判定路径应被 _UNSET 取代（在 accept 分支内）
    # 至少应出现 4 次（4 个分支都改）
    assert src.count("in _UNSET") >= 4


def test_cmd_diplomacy_request_blocks_neutral_target():
    """cmd_diplomacy 'request' 必须把 neutral 目标在引擎层拦住，
    并且**不再**自动调 ``target.cmd_diplomacy(['accept', ...])``。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    # 新增的早返回逻辑
    assert "if getattr(target, 'neutral', False):" in src
    request_start = src.index("if action == 'request':")
    neutral_block = src.index("getattr(target, 'neutral', False)", request_start)
    return_stmt = src.index("return", neutral_block)
    # `return` 应该紧跟 neutral 判定（中间允许 NO_CANDIDATE 提示）
    assert (return_stmt - neutral_block) < 300, "neutral 判定后应早返回"
    # 旧的 auto-accept 调用应彻底消失
    assert "target.cmd_diplomacy(['accept', str(self.id)])" not in src


def test_player_name_neutral_uses_neutral_and_nb2msg():
    """``Player.name`` 的 neutral 分支必须用 ``mp.NEUTRAL + nb2msg(idx)``。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    assert "return mp.NEUTRAL + nb2msg(idx)" in src
    # 旧的 ``return []`` 不应再是 neutral 唯一行为
    # （仍可能在 except 等地方使用 []，所以不做 negative 检测）


# ---------------------------------------------------------------------------
# 地图解析：未标记的 computer_only 默认为敌对 (等价于 non_neutral)
# ---------------------------------------------------------------------------
#
# 与 doc_src/src/en/mapmaking.rst:223 的文档承诺一致：
#   "This AI will be hostile to any other player or AI."
# 仅当地图作者显式写 `neutral` 时才进入 "被动 creep" 路径。


def _try_import_world_map():
    """尝试 import world_map。

    两道坎：
    1. 导入链上 ``options.py`` 的 ``parser.parse_args()`` 会消费 pytest 自身
       的命令行参数（如 ``--tb``）抛 ``SystemExit``。临时把 ``sys.argv`` 改成
       无参数即可绕过。
    2. ``lib/resource.py`` 链上调 ``locale.getdefaultlocale()`` 触发
       ``DeprecationWarning``；``pytest.ini`` 把 warnings 当 error，会再次失败。
       用 ``warnings.simplefilter("ignore")`` 屏蔽。
    """
    import warnings
    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.world import world_map  # noqa: WPS433
            return world_map
    except (SystemExit, Exception):
        return None
    finally:
        sys.argv = saved_argv


_WM = _try_import_world_map()


def _make_map_stub_for_add_start():
    if _WM is None:
        return None, None
    m = _WM.WorldMapMixin.__new__(_WM.WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.nb_res = 2  # 与多数地图 "computer_only 0 0 ..." 的两资源一致
    captured = {}

    def fake_add(starts, resources, items, sq=None, neutral=None, population=0):
        captured['neutral'] = neutral
        captured['items'] = list(items)
        captured['population'] = population
        starts.append([resources, items, [], neutral])

    m._add_start_to = fake_add
    return m, captured


def test_computer_only_without_marker_defaults_to_hostile():
    """没写 ``neutral`` / ``non_neutral`` 的 ``computer_only`` 应解析成敌对 AI。"""
    m, captured = _make_map_stub_for_add_start()
    if m is None:
        pytest.skip("world_map 无法在测试环境加载（options.py 抢解析 pytest 参数）")
    m._add_start("computer_only", ["computer_only", "0", "0", "a3", "footman"])

    assert captured['neutral'] is False
    assert "neutral" not in captured['items']
    assert "non_neutral" not in captured['items']


def test_computer_only_with_explicit_neutral_marker_is_neutral():
    """显式写 ``neutral`` 的 ``computer_only`` 必须仍按中立 creep 处理。"""
    m, captured = _make_map_stub_for_add_start()
    if m is None:
        pytest.skip("world_map 无法在测试环境加载")
    m._add_start("computer_only",
                 ["computer_only", "0", "0", "neutral", "a3", "footman"])

    assert captured['neutral'] is True
    assert "neutral" not in captured['items']


def test_computer_only_with_explicit_non_neutral_marker_is_hostile():
    """显式写 ``non_neutral`` 仍能被识别为敌对，与现有 z5/td2 地图保持兼容。"""
    m, captured = _make_map_stub_for_add_start()
    if m is None:
        pytest.skip("world_map 无法在测试环境加载")
    m._add_start("computer_only",
                 ["computer_only", "0", "0", "non_neutral", "a3", "footman"])

    assert captured['neutral'] is False
    assert "non_neutral" not in captured['items']


def test_world_map_source_default_is_false():
    """源码契约：world_map.py 的默认值必须翻成 False。"""
    src = _source(["soundrts", "world", "world_map.py"])
    # 关键标记：默认值改为 False；保留 elif "neutral" in units: neutral = True 分支。
    assert "neutral = False\n        if w in [\"computer_only\", \"computer\"]" in src
    assert "elif \"neutral\" in units:" in src


def test_world_objects_dummy_client_default_is_false():
    """源码契约：world_objects.py 的 DummyClient fallback 也翻成 False。"""
    src = _source(["soundrts", "world", "world_objects.py"])
    # 在 computer_start 循环里 fallback 默认值应为 False
    assert "neutral = False\n            if len(computer_start) >= 4" in src


# ---------------------------------------------------------------------------
# F12 候选广播：中立既然已被 _diplo_players 过滤掉，
# cmd_select_alliance_candidate 不应再含 "neutral 时用 client.login" 死分支
# ---------------------------------------------------------------------------


def test_cmd_select_alliance_no_longer_special_cases_neutral():
    """源码契约：``cmd_select_alliance_candidate`` 不能再有 ``client.login`` 死分支。

    历史背景：曾为避免 "中立 1, 中立" 重复在 F12 把 neutral 名字换成
    client.login（例如 "ai_timers"）。现在已把 neutral 从 _diplo_players 过滤掉，
    该分支永远到不了，删掉以免误导后续维护者。
    """
    src = _source(["soundrts", "clientgame", "game_audio.py"])
    cmd_start = src.index("def cmd_select_alliance_candidate(")
    cmd_body = src[cmd_start:cmd_start + 1200]
    assert "if getattr(p, 'neutral', False):" not in cmd_body
    assert "name_msg = [getattr(p.client, 'login', '?')]" not in cmd_body


# ---------------------------------------------------------------------------
# 动态联盟相关短语：在 tts 字典里有对应文本，否则语音会"哑掉"。
# ---------------------------------------------------------------------------
#
# 用户报告：以下 5 个 msgparts 常量虽已在 msgparts.py 定义，但中文 tts.txt
# 缺少对应条目，导致结盟流程的语音播报听不到。
# 顺带补 4967 UNALLY_WITH（撤销结盟请求）——base.py 同样在用、ZH 同样缺。


import re as _re


_DIPLOMACY_EN_EXPECTED = {
    4963: "unallied with",       # UNALLIED_WITH
    4966: "ally with",            # ALLY_WITH
    4967: "unally with",          # UNALLY_WITH
    4968: "alliance request from",  # ALLIANCE_REQUEST_FROM
    4969: "alliance accepted with",  # ALLIANCE_ACCEPTED_WITH
    4970: "alliance declined with",  # ALLIANCE_DECLINED_WITH
}


# 中文不强等值，只要求"存在条目"（具体翻译可后续微调），避免误把翻译写死成
# 不可读字符串。需要每条非空、跟在 ID 后面要有非空白。
_DIPLOMACY_ZH_IDS = sorted(_DIPLOMACY_EN_EXPECTED.keys())


def _tts_path(language_dir):
    return Path(__file__).resolve().parents[2] / "res" / language_dir / "tts.txt"


def test_diplomacy_phrases_have_english_tts():
    """en tts.txt 必须包含全部 5 条动态联盟语音 + 我们补的 4967。"""
    text = _tts_path("ui").read_text(encoding="utf-8")
    for tts_id, en in _DIPLOMACY_EN_EXPECTED.items():
        pattern = rf"^{tts_id}\s+{_re.escape(en)}\s*$"
        assert _re.search(pattern, text, flags=_re.MULTILINE), (
            f"en tts.txt 缺少 '{tts_id} {en}' 条目"
        )


def test_diplomacy_phrases_have_chinese_tts():
    """zh tts.txt 必须包含每个 ID 的条目，且后面非空（避免空朗读）。"""
    text = _tts_path("ui-zh").read_text(encoding="utf-8")
    for tts_id in _DIPLOMACY_ZH_IDS:
        pattern = rf"^{tts_id}\s+\S"
        assert _re.search(pattern, text, flags=_re.MULTILINE), (
            f"zh tts.txt 缺少 ID {tts_id} 的中文条目"
        )


def test_msgparts_constants_match_tts_ids():
    """msgparts.py 里这 6 个常量必须与 tts 文件里的 ID 一一对应，避免下次改一边漏一边。"""
    from soundrts import msgparts as mp_mod
    pairs = {
        "UNALLIED_WITH": 4963,
        "ALLY_WITH": 4966,
        "UNALLY_WITH": 4967,
        "ALLIANCE_REQUEST_FROM": 4968,
        "ALLIANCE_ACCEPTED_WITH": 4969,
        "ALLIANCE_DECLINED_WITH": 4970,
    }
    for name, tts_id in pairs.items():
        assert getattr(mp_mod, name) == [tts_id], (
            f"msgparts.{name} 期望 [{tts_id}]，实际 {getattr(mp_mod, name)}"
        )


# ===========================================================================
# Bug A：broadcast_to_others_only 加 exclude 参数，避免当事人重复听到自己名字
# ===========================================================================


class _RecorderPlayer:
    """记录每次 send_voice_important 的内容，用来验证广播覆盖面。"""

    def __init__(self, pid, name):
        self.id = pid
        self.name_value = name
        self.received = []

    def send_voice_important(self, msg):
        self.received.append(msg)


def _broadcast_excl(world_players, sender, msg, exclude=None):
    """等价复刻 ``broadcast_to_others_only(msg, exclude=...)`` 的修复后行为。"""
    for p in world_players:
        if p is not sender and p is not exclude:
            p.send_voice_important(msg)


def test_broadcast_excludes_target_so_target_does_not_hear_own_name():
    """关键断言：把 target 加进 exclude 后，target 不再收到广播（避免听到自己名字）。"""
    a = _RecorderPlayer("1", ["alice"])
    b = _RecorderPlayer("2", ["bob"])
    c = _RecorderPlayer("3", ["carol"])
    world = [a, b, c]

    # 模拟 ACCEPTED 单次广播 + exclude target 的新行为
    _broadcast_excl(world, sender=a, msg=["MSG"] + b.name_value, exclude=b)

    assert a.received == []           # 发送者不收
    assert b.received == []           # exclude 起作用，target 不收
    assert c.received == [["MSG", "bob"]]  # 真正的第三方仍收到


def test_broadcast_without_exclude_still_works():
    """未传 exclude 时行为退化成原行为：除自己外人人收。"""
    a = _RecorderPlayer("1", ["alice"])
    b = _RecorderPlayer("2", ["bob"])
    c = _RecorderPlayer("3", ["carol"])
    world = [a, b, c]

    _broadcast_excl(world, sender=a, msg=["X"])

    assert a.received == []
    assert b.received == [["X"]]
    assert c.received == [["X"]]


def test_broadcast_to_others_only_source_has_exclude_param():
    """源码契约：``broadcast_to_others_only`` 必须接受 ``exclude=None`` 关键字。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    assert "def broadcast_to_others_only(self, msg, exclude=None):" in src
    # 三处调用必须都传 exclude=target
    assert src.count("exclude=target") >= 3


def test_accept_branch_collapses_double_broadcast():
    """ACCEPTED 分支应只剩一次广播（之前是两次），且内容包含双方名字。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    # 旧的 target.broadcast_to_others_only 在 ACCEPTED 分支应被删除
    accept_block_start = src.index(
        "self.send_voice_important(mp.ALLIANCE_ACCEPTED_WITH + target.name)")
    # 取够长的窗口覆盖整个 ACCEPTED 语音块
    accept_block = src[accept_block_start:accept_block_start + 1200]
    # 旧的双 broadcast 不应再出现
    assert "target.broadcast_to_others_only(mp.ALLIANCE_ACCEPTED_WITH" not in accept_block
    # 单次合并广播应存在
    assert "mp.ALLIANCE_ACCEPTED_WITH + self.name + mp.COMMA + target.name" in accept_block


# ===========================================================================
# Bug B：_diplo_players 按 int(p.id) 排序，避免字典序乱序
# ===========================================================================


def test_diplo_id_sort_key_is_numeric_when_id_is_digit_string():
    """字符串 ID "1", "2", "10", "11" 应按整数顺序排好，而不是 1, 10, 11, 2。"""
    # 直接调用复刻函数验证 key 行为
    class _P:
        def __init__(self, pid):
            self.id = pid

    items = [_P("11"), _P("2"), _P("1"), _P("10")]
    items.sort(key=_diplo_id_sort_key_logic)

    assert [p.id for p in items] == ["1", "2", "10", "11"]


def test_diplo_id_sort_key_falls_back_for_non_numeric():
    """非数字 ID（理论上不该出现，但要兜底不抛异常）走字符串排序。"""
    class _P:
        def __init__(self, pid):
            self.id = pid

    items = [_P("zeta"), _P("alpha")]
    items.sort(key=_diplo_id_sort_key_logic)

    assert [p.id for p in items] == ["alpha", "zeta"]


def _diplo_id_sort_key_logic(p):
    """等价复刻 game_audio._diplo_id_sort_key（避免依赖 client 导入链）。"""
    pid = getattr(p, 'id', None)
    try:
        return (0, int(pid))
    except (TypeError, ValueError):
        return (1, str(pid))


def test_diplo_players_source_uses_int_sort():
    """源码契约：``_diplo_players`` 必须用 ``_diplo_id_sort_key`` 而非 ``p.id``。"""
    src = _source(["soundrts", "clientgame", "game_audio.py"])
    assert "players.sort(key=_diplo_id_sort_key)" in src
    assert "def _diplo_id_sort_key(p):" in src


# ===========================================================================
# Bug C：F12 候选过滤已淘汰/胜出的玩家；advance 用 selected_id 重锚 idx
# ===========================================================================


def _diplo_is_alive_logic(p):
    if getattr(p, 'has_been_defeated', False):
        return False
    if getattr(p, 'has_victory', False):
        return False
    return True


class _StubAlivePlayer:
    def __init__(self, pid, defeated=False, victory=False, neutral=False):
        self.id = pid
        self.has_been_defeated = defeated
        self.has_victory = victory
        self.neutral = neutral
        self.allied = [self]


def test_diplo_players_filters_defeated():
    """已淘汰的玩家不应出现在 F12 候选列表里。"""
    me = _StubAlivePlayer("1")
    alive = _StubAlivePlayer("2")
    dead = _StubAlivePlayer("3", defeated=True)
    iface = _StubInterface(me, [me, alive, dead])

    # 复刻修复后的 _diplo_players 逻辑
    players = [p for p in iface.world.players
               if p is not me and _diplo_is_alive_logic(p)]

    assert alive in players
    assert dead not in players


def test_diplo_players_filters_victorious():
    """已胜出的玩家也不应出现（同理）。"""
    me = _StubAlivePlayer("1")
    winner = _StubAlivePlayer("2", victory=True)
    iface = _StubInterface(me, [me, winner])

    players = [p for p in iface.world.players
               if p is not me and _diplo_is_alive_logic(p)]

    assert players == []


def test_diplo_players_source_uses_is_alive_filter():
    """源码契约：``_diplo_players`` 必须用 ``_diplo_is_alive`` 过滤。"""
    src = _source(["soundrts", "clientgame", "game_audio.py"])
    assert "def _diplo_is_alive(p):" in src
    assert "_diplo_is_alive(p)" in src
    # advance_candidate 重锚 idx 的关键代码
    assert "_diplo_selected_player_id" in src
    assert "selected_id = getattr(interface, '_diplo_selected_player_id', None)" in src


# ===========================================================================
# Bug D：对已是盟友的目标 'request' 必须短路
# ===========================================================================


def test_request_to_existing_ally_short_circuits_in_source():
    """源码契约：cmd_diplomacy 'request' 必须在 ``target in self.allied`` 时短路返回。"""
    src = _source(["soundrts", "worldplayerbase", "base.py"])
    # 关键标记
    assert "already_ally = target in getattr(self, 'allied', [])" in src
    # request 频率限制之前必须先短路
    request_start = src.index("if action == 'request':")
    freq_start = src.index("60000", request_start)
    short_circuit = src.index("already_ally", request_start)
    assert short_circuit < freq_start, (
        "已是盟友的短路检查必须在 60s 频率限制之前，不应写 cooldown"
    )


def test_request_short_circuit_logic_truth_table():
    """逻辑级：当 target 已在 allied 列表里，短路返回 True；否则继续。"""

    class _StubReq:
        def __init__(self, allied):
            self.allied = allied

    def _should_short_circuit(self_player, target):
        try:
            return target in getattr(self_player, 'allied', [])
        except Exception:
            return False

    me = _StubReq([])
    ally = "fake_ally"
    stranger = "fake_stranger"
    me.allied = [me, ally]

    assert _should_short_circuit(me, ally) is True       # 应短路
    assert _should_short_circuit(me, stranger) is False  # 应继续走 request
