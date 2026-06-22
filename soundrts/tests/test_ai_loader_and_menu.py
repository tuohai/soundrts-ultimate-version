"""``ai.txt`` 加载器 + "邀请电脑"菜单回归测试。

游戏提供五档默认难度，但邀请菜单会根据已加载的 ``ai.txt`` 动态列出可邀请的
电脑 AI。本文件覆盖以下契约：

1. ``_read_ai_to_dict`` 必须识别 ``clear`` 指令（mod 的覆盖入口）。
2. ``load_ai`` 在分层输入（基础 + mod）下行为正确，``clear`` 影响仅及
   出现位置之前的内容。
3. ``get_ai`` 在请求的难度缺失时，按 ``_AI_FALLBACKS`` 回退到最接近的
   已定义难度（包括 ``easy`` / ``aggressive`` 旧名）。
4. ``get_menu_ai_difficulties``：无 mod 时五档；有 mod 时按 ``rules.txt`` 映射列档位。
   ``beginner`` … → 初级 …；旧 mod 的 ``easy`` / ``aggressive`` → 防御型 / 攻击型。
5. ``TrainingMenu._add_ai_invite_menu`` / ``GameAdminMenu.make_menu`` 使用
   ``get_menu_ai_difficulties()`` 动态生成按钮。
6. ``clientservermenu.name(login)`` 识别标准 ``ai_<难度>`` login（外加
   旧的 ``ai_easy`` / ``ai_aggressive``），自定义 AI 使用可读标签。
"""
from __future__ import annotations

import os
import sys
import textwrap
import warnings as _warnings

# pytest.ini 把所有 warning 升级成 error。``soundrts.lib.resource`` 在
# import 阶段调用已弃用的 ``locale.getdefaultlocale`` (Python 3.12+)。
# 在第一次 import 之前先屏蔽这两类问题，避免 collect 阶段就挂掉。
_warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*getdefaultlocale.*",
)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        from soundrts import clientservermenu as _preload_csm  # noqa: F401
    finally:
        sys.argv = _saved_argv

import pytest

from soundrts import definitions
from soundrts.definitions import (
    AI_DIFFICULTIES,
    _read_ai_to_dict,
    ai_invite_label,
    ai_player_label,
    get_ai,
    get_ai_names,
    get_menu_ai_difficulties,
    load_ai,
    rules,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_ai(monkeypatch):
    """在测试期间替换 ``definitions._ai`` 为一个新字典，避免污染全局。"""
    fresh = {}
    monkeypatch.setattr(definitions, "_ai", fresh)
    return fresh


def _ai(text):
    """去掉左缩进，让测试用的 triple-quoted 字符串和真实 ai.txt 一样从第 0 列开始。"""
    return textwrap.dedent(text).strip("\n")


# ---------------------------------------------------------------------------
# 1. _read_ai_to_dict: clear directive
# ---------------------------------------------------------------------------

class TestReadAiToDictClear:
    """``clear`` 指令在 AI loader 里的语义。"""

    def test_clear_wipes_previous_defs(self):
        d = {}
        _read_ai_to_dict(_ai("""
            def easy
            get 5 peasant
            def aggressive
            get 10 peasant
            clear
            def c_traditionnel
            get 5 serf
        """), d)
        assert "easy" not in d
        assert "aggressive" not in d
        assert "c_traditionnel" in d
        assert "get 5 serf" in d["c_traditionnel"]

    def test_clear_resets_open_def_context(self):
        """``clear`` 不应让"前一个 def 的开放上下文"漏到后面去。"""
        d = {}
        _read_ai_to_dict(_ai("""
            def easy
            get 5 peasant
            clear
            def c_orc
            get 10 peon
        """), d)
        assert "easy" not in d
        assert d["c_orc"] == ["get 10 peon"]

    def test_no_clear_keeps_legacy_behaviour(self):
        """没有 ``clear`` 时，``load_ai`` 是单纯的累加。"""
        d = {}
        _read_ai_to_dict(_ai("""
            def easy
            get 5 peasant
            def aggressive
            get 10 peasant
        """), d)
        _read_ai_to_dict(_ai("""
            def my_mod_ai
            get 7 elf
        """), d)
        assert set(d.keys()) == {"easy", "aggressive", "my_mod_ai"}


# ---------------------------------------------------------------------------
# 2. load_ai: 分层拼接 + clear 交互
# ---------------------------------------------------------------------------

class TestLoadAiLayering:
    """``load_ai`` 模拟实际加载流程（基础层 + mod 层）。"""

    def test_layered_with_clear_replaces_base(self, isolated_ai):
        """mod 里写 ``clear`` 时基础那些 def 必须被丢掉。"""
        base = _ai("""
            def easy
            get 5 peasant
            def aggressive
            get 8 peasant
        """)
        mod = _ai("""
            clear
            def c_traditionnel
            get 5 serf
            def traditionnel
            get 10 serf
        """)
        load_ai(base, mod)
        names = set(get_ai_names())
        assert "easy" not in names
        assert "aggressive" not in names
        assert names == {"c_traditionnel", "traditionnel"}

    def test_layered_without_clear_merges(self, isolated_ai):
        """没有 ``clear`` 时，mod 的 def 直接堆在基础之上。同名后写覆盖前写。"""
        base = _ai("""
            def easy
            get 5 peasant
            def aggressive
            get 10 peasant
        """)
        mod = _ai("""
            def aggressive
            get 99 ultra_unit
            def my_extra
            get 1 elf
        """)
        load_ai(base, mod)
        names = set(get_ai_names())
        assert names == {"easy", "aggressive", "my_extra"}
        assert definitions._ai["aggressive"] == ["get 99 ultra_unit"]

    def test_vanilla_ai_txt_defines_all_difficulties(self, isolated_ai):
        """vanilla ``res/ai.txt`` 必须为五个难度都写有非空 ``def``。"""
        import pathlib
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        base = (repo_root / "res" / "ai.txt").read_text(
            encoding="utf-8", errors="replace"
        )
        load_ai(base)
        names = set(get_ai_names())
        for difficulty in AI_DIFFICULTIES:
            assert difficulty in names, f"vanilla ai.txt 缺少 def {difficulty}"
            assert definitions._ai[difficulty], f"vanilla def {difficulty} 不能为空"


# ---------------------------------------------------------------------------
# 2b. get_ai: 难度回退（缺失时退到最接近的已定义难度 / 旧名别名）
# ---------------------------------------------------------------------------

class TestGetAiFallback:
    def test_missing_difficulty_falls_back_to_closest(self, isolated_ai):
        """只定义 intermediate 时，请求更高难度回退到 intermediate。"""
        load_ai(_ai("""
            def intermediate
            get 10 peasant
        """))
        assert get_ai("nightmare") == ["get 10 peasant"]
        assert get_ai("expert") == ["get 10 peasant"]
        assert get_ai("advanced") == ["get 10 peasant"]
        assert get_ai("intermediate") == ["get 10 peasant"]

    def test_legacy_easy_aggressive_aliases(self, isolated_ai):
        """旧 mod 只写 def easy / def aggressive 时，新难度名仍能解析。"""
        load_ai(_ai("""
            def easy
            get 5 peasant
            def aggressive
            get 8 peasant
        """))
        assert get_ai("beginner") == ["get 5 peasant"]
        assert get_ai("intermediate") == ["get 8 peasant"]
        # 新名字优先于旧别名
        assert get_ai("easy") == ["get 5 peasant"]

    def test_unknown_name_does_not_crash(self, isolated_ai):
        """完全没有匹配时返回一个已加载难度（绝不抛 KeyError）。"""
        load_ai(_ai("""
            def beginner
            get 3 peasant
        """))
        assert get_ai("totally_unknown") == ["get 3 peasant"]


# ---------------------------------------------------------------------------
# 2c. get_menu_ai_difficulties: 邀请菜单动态列表
# ---------------------------------------------------------------------------

class TestGetMenuAiDifficulties:
    def test_vanilla_offers_five_standard_difficulties(self, isolated_ai):
        load_ai(_ai("""
            def beginner
            get 1 peasant
            def intermediate
            get 2 peasant
            def advanced
            get 3 peasant
            def expert
            get 4 peasant
            def nightmare
            get 5 peasant
        """))
        assert get_menu_ai_difficulties() == list(AI_DIFFICULTIES)

    def test_mod_menu_from_rules_legacy_easy_aggressive(self, isolated_ai):
        rules.load(_ai("""
            def parameters
            nb_of_resource_types 2
            def orc
            class race
            easy tang_easy
            aggressive tang_hard
        """))
        load_ai(_ai("def beginner\nget 1 a\n"), _ai("""
            def tang_easy
            get 5 villager
            def tang_hard
            get 10 villager
        """))
        assert get_menu_ai_difficulties() == ["easy", "aggressive"]

    def test_legacy_easy_shows_defensive_label(self, isolated_ai):
        from soundrts import msgparts as mp
        assert ai_player_label("easy") == list(mp.QUIET_COMPUTER)
        assert ai_player_label("aggressive") == list(mp.AGGRESSIVE_COMPUTER)
        assert ai_player_label("beginner") == list(mp.BEGINNER_COMPUTER)

    def test_mod_menu_from_rules_three_tiers(self, isolated_ai):
        rules.load(_ai("""
            def parameters
            nb_of_resource_types 2
            def tang_empire
            class race
            beginner tang_empire_easy
            intermediate tang_empire_hard
            advanced tang_empire_hard
        """))
        load_ai(_ai("def beginner\nget 1 a\n"), _ai("""
            def tang_empire_easy
            get 5 villager
            def tang_empire_hard
            get 10 villager
        """))
        assert get_menu_ai_difficulties() == [
            "beginner",
            "intermediate",
            "advanced",
        ]

    def test_mod_fallback_when_no_rules_mapping(self, isolated_ai):
        rules.load(_ai("""
            def parameters
            nb_of_resource_types 2
            def orc
            class race
            townhall great_hall
        """))
        load_ai(_ai("""
            def beginner
            get 1 peasant
            def intermediate
            get 2 peasant
        """), _ai("""
            def beginner
            get 5 villager
            def intermediate
            get 8 villager
        """))
        assert get_menu_ai_difficulties() == ["beginner", "intermediate"]


# ---------------------------------------------------------------------------
# 3. clientservermenu.name(): 多人大厅 AI 登录名显示（SoundRTS 1.x 风格）
# ---------------------------------------------------------------------------

class TestClientServerMenuName:
    """``name(login)`` 识别 5 个难度 login（外加旧别名），其余按字面返回。"""

    def test_human_login_unchanged(self):
        from soundrts.clientservermenu import name
        assert name("alice") == ["alice"]

    def test_difficulty_logins_read_labels(self):
        from soundrts.clientservermenu import name
        from soundrts import msgparts as mp
        assert name("ai_beginner") == list(mp.BEGINNER_COMPUTER)
        assert name("ai_intermediate") == list(mp.INTERMEDIATE_COMPUTER)
        assert name("ai_advanced") == list(mp.ADVANCED_COMPUTER)
        assert name("ai_expert") == list(mp.EXPERT_COMPUTER)
        assert name("ai_nightmare") == list(mp.NIGHTMARE_COMPUTER)

    def test_legacy_logins_still_labelled(self):
        from soundrts.clientservermenu import name
        from soundrts import msgparts as mp
        assert name("ai_easy") == list(mp.QUIET_COMPUTER)
        assert name("ai_aggressive") == list(mp.AGGRESSIVE_COMPUTER)

    def test_ai_ai2_falls_back_to_humanized_name(self):
        from soundrts.clientservermenu import name
        assert name("ai_ai2") == ["ai2"]

    def test_custom_ai_uses_humanized_name(self):
        from soundrts.clientservermenu import name
        assert name("ai_c_traditionnel") == ["c traditionnel"]


# ---------------------------------------------------------------------------
# 4. 邀请菜单：clientmain + clientservermenu 跟随 get_menu_ai_difficulties
# ---------------------------------------------------------------------------

class TestAiInviteMenuDynamic:
    VANILLA_TYPES = ["beginner", "intermediate", "advanced", "expert", "nightmare"]

    def _load_vanilla_ai(self):
        load_ai(_ai("""
            def beginner
            get 1 peasant
            def intermediate
            get 2 peasant
            def advanced
            get 3 peasant
            def expert
            get 4 peasant
            def nightmare
            get 5 peasant
        """))

    def test_single_player_menu_follows_menu_difficulties(self, isolated_ai):
        self._load_vanilla_ai()
        from soundrts.clientmain import TrainingMenu

        tm = TrainingMenu.__new__(TrainingMenu)
        captured = []

        class FakeMenu:
            def append(self, label, callback):
                captured.append((list(label), callback))

        tm._add_ai = lambda ai_type: ai_type
        tm._add_ai_invite_menu(FakeMenu())

        ai_types_called = [callback[1] for _label, callback in captured]
        assert ai_types_called == self.VANILLA_TYPES
        assert [c[0] for c in captured] == [
            ai_invite_label(name) for name in self.VANILLA_TYPES
        ]

    def test_multiplayer_menu_uses_invite_ai_command(self, isolated_ai):
        self._load_vanilla_ai()
        from soundrts.clientservermenu import GameAdminMenu

        menu_obj = GameAdminMenu.__new__(GameAdminMenu)

        class FakeMap:
            title = ["t"]
            nb_players_min = 1
            nb_players_max = 8

        class FakeServer:
            def __init__(self):
                self.lines_written = []

            def write_line(self, line):
                self.lines_written.append(line)

        menu_obj.map = FakeMap()
        menu_obj.registered_players = []
        menu_obj.available_players = []
        menu_obj.server = FakeServer()

        result = menu_obj.make_menu()

        invite_actions = []
        for entry in getattr(result, "choices", []):
            label, action = entry[0], entry[1]
            if isinstance(action, tuple) and len(action) >= 2:
                fn = action[0]
                arg = action[1]
                if (
                    getattr(fn, "__self__", None) is menu_obj.server
                    and getattr(fn, "__name__", "") == "write_line"
                    and isinstance(arg, str)
                    and arg.startswith("invite_ai ")
                ):
                    invite_actions.append((label, arg))

        cmds = [arg for _label, arg in invite_actions]
        assert cmds == [f"invite_ai {name}" for name in self.VANILLA_TYPES]
        assert [label for label, _arg in invite_actions] == [
            ai_invite_label(name) for name in self.VANILLA_TYPES
        ]


# ---------------------------------------------------------------------------
# 5. ai.txt 脚本新参数：workers / expand / attack_ratio / wait
# ---------------------------------------------------------------------------

class _FakeWorld:
    time = 0


def _make_computer(plan):
    """构造一个跳过 __init__ 的 Computer，仅装上 _follow_plan 需要的状态。"""
    from soundrts.worldplayercomputer import Computer

    c = Computer.__new__(Computer)
    c.world = _FakeWorld()
    c._plan = plan
    c.watchdog = 0
    c._previous_linechange = 0
    c._wait_deadline = None
    c._line_nb = 0
    # tunable defaults (mirrors set_ai)
    c.nb_workers_to_get = Computer.nb_workers_to_get
    c._target_townhalls = Computer._target_townhalls
    c._attack_ratio = Computer._attack_ratio
    c.counter_skill = Computer.counter_skill
    return c


class TestFollowPlanTunables:
    """``_follow_plan`` 对新参数命令的解析。"""

    def test_workers_expand_attack_ratio_are_applied(self):
        c = _make_computer(["workers 25", "expand 3", "attack_ratio 120", "goto -1"])
        c._follow_plan()
        assert c.nb_workers_to_get == 25
        c._follow_plan()
        assert c._target_townhalls == 3
        c._follow_plan()
        assert c._attack_ratio == 120

    def test_attack_ratio_is_floored_at_one(self):
        c = _make_computer(["attack_ratio 0", "goto -1"])
        c._follow_plan()
        assert c._attack_ratio == 1

    def test_counter_skill_is_clamped_to_0_100(self):
        c = _make_computer(["counter_skill 150", "goto -1"])
        c._follow_plan()
        assert c.counter_skill == 100
        c._line_nb = 0
        c = _make_computer(["counter_skill 25", "goto -1"])
        c._follow_plan()
        assert c.counter_skill == 25

    def test_counter_skill_zero_disables_counter_utilization(self):
        c = _make_computer(["counter_skill 0", "goto -1"])
        c.AI_type = "beginner"
        c._follow_plan()
        assert c.counter_skill == 0
        assert c._counter_skill_level() == 0

    def test_non_numeric_argument_is_ignored_and_advances(self):
        c = _make_computer(["workers abc", "goto -1"])
        c._follow_plan()
        # 非法参数：保持默认值并前进到下一行
        assert c.nb_workers_to_get == type(c).nb_workers_to_get
        assert c._line_nb == 1

    def test_wait_stalls_until_deadline_then_advances(self):
        c = _make_computer(["wait 5", "goto -1"])
        c.world.time = 0
        c._follow_plan()
        assert c._line_nb == 0  # still waiting
        assert c._wait_deadline == 5000
        c.world.time = 5000
        c._follow_plan()
        assert c._wait_deadline is None
        assert c._line_nb == 1  # delay elapsed, moved on
