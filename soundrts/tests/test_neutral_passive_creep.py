"""验证 ``computer_only ... neutral`` 的中立电脑单位会被切到 guard 模式 +
counterattack_enabled=True（"被动反击型 creep"）。

引擎层修复点：``soundrts/worldplayerbase/base.py`` Player.add() 在
``unit.upgrade_to_player_level()`` 之后插入了 neutral 判定，把 Creature
子类单位的 ai_mode 覆盖为 "guard" 并打开反击。

测试设计：用 ``Player.__new__`` 跳过 Player.__init__（避免触发 World/Stats
等重依赖），手动注入 Player.add() 实际读到的字段；不实例化完整 Creature
（避免 place/world 依赖），用 ``Creature.__new__`` + 注入字段的方式。
"""
from __future__ import annotations

import pytest

# 解开 worldunit 包的循环导入（与 test_combat_fast_parity / test_combat_mixin_rewire 一致）
import soundrts.worldunit  # noqa: F401

from soundrts.worldplayerbase.base import Player
from soundrts.worldunit.worldcreature import Creature


class _StubWorld:
    """提供 ``world.time`` 给 ``Player.allied_vision`` property 用。"""
    time = 0


def _make_player(neutral: bool) -> Player:
    """构造一个最小化的 Player：跳过 __init__，仅注入 add() 实际访问的字段。

    ``allied_vision`` 是 property（不能直接赋值），它读 ``world.time``、
    ``_allied_vision_cache_time``、``_cached_allied_vision``，我们预先注入
    一个未过期的缓存，让 property 直接返回空列表，避开 perception 路径。
    """
    p = Player.__new__(Player)
    p.neutral = neutral
    p.units = []
    p.population = 0
    p.used_population = 0
    p.world = _StubWorld()
    p.allied = []
    p._cached_allied_vision = []
    p._allied_vision_cache_time = 0  # 未来 1 秒内 (cache_interval=1000) 都直接命中
    return p


def _make_creature_unit(player: Player, type_name: str = "test_creature") -> Creature:
    """构造一个最小化的 Creature：跳过 Creature.__init__，仅注入 Player.add() 路径所需字段。

    模拟 Creature.__init__ 设置的初始 ai_mode/counterattack_enabled 等。
    需要 ``unit.player`` 才能让 ``next_free_number()`` 工作（它读 ``self.player.units``）。
    """
    u = Creature.__new__(Creature)
    u.player = player
    u.type_name = type_name
    u.number = 0
    u.ai_mode = "offensive"
    u.counterattack_enabled = False
    u.last_attacker = None
    u.population_provided = 0
    u.population_cost = 0
    u.action_target = None
    return u


class _NonCreatureUnit:
    """非 Creature 单位（例如 Resource / Item）。Player.add() 应跳过 ai_mode 覆盖。"""

    population_provided = 0
    population_cost = 0
    action_target = None

    def __init__(self, player):
        self.player = player
        self.type_name = "non_creature"
        self.number = 0

    def next_free_number(self):
        return 1

    def upgrade_to_player_level(self):
        pass


def test_neutral_unit_becomes_guard_with_counterattack():
    """中立电脑的 Creature 单位：ai_mode 应被覆盖为 'guard'，counterattack_enabled 应为 True."""
    player = _make_player(neutral=True)
    unit = _make_creature_unit(player)

    player.add(unit)

    assert unit.ai_mode == "guard"
    assert unit.counterattack_enabled is True


def test_non_neutral_unit_keeps_offensive():
    """非中立玩家的 Creature 单位：ai_mode 保持 'offensive'，counterattack_enabled 保持 False."""
    player = _make_player(neutral=False)
    unit = _make_creature_unit(player)

    player.add(unit)

    assert unit.ai_mode == "offensive"
    assert unit.counterattack_enabled is False


def test_neutral_non_creature_skipped_no_error():
    """中立玩家添加非 Creature 对象时不应抛错（守卫 isinstance 检查）。

    Resource / Item 等没有 ai_mode 属性的对象，必须能安全通过 Player.add()。
    """
    player = _make_player(neutral=True)
    unit = _NonCreatureUnit(player)

    player.add(unit)

    assert not hasattr(unit, "ai_mode")
    assert not hasattr(unit, "counterattack_enabled")


def test_neutral_unit_in_units_list_with_population():
    """sanity check: Player.add() 的其余逻辑仍正常工作（unit 进 units 列表、人口累加）。"""
    player = _make_player(neutral=True)
    unit = _make_creature_unit(player)
    unit.population_provided = 5
    unit.population_cost = 2
    unit.effective_population_cost = 2

    player.add(unit)

    assert unit in player.units
    assert player.population == 5
    assert player.used_population == 2
    assert unit.ai_mode == "guard"


# --- Tab 浏览/选择时的标注: neutral 玩家应标为"中立"而非"敌人" -------------
#
# 直接测 EntityViewProperties.title 需要 import soundrts.clientgameentity，
# 那条链会拉起 clientmedia → resource → pygame/locale，触发 locale
# DeprecationWarning（被 pytest.ini 的 `filterwarnings = error` 拦截）。
# 改为在 import 前预填 sys.modules 桩，跳过 client-side 重依赖。

import sys
import types
from soundrts import msgparts as mp


def _stub_client_modules():
    """预填 sys.modules 桩，避免 import properties 时拉起 pygame/locale 链。"""
    if "soundrts.clientmedia" not in sys.modules:
        stub = types.ModuleType("soundrts.clientmedia")
        stub.sounds = None
        stub.voice = None
        sys.modules["soundrts.clientmedia"] = stub
    if "soundrts.clientmenu" not in sys.modules:
        sys.modules["soundrts.clientmenu"] = types.ModuleType("soundrts.clientmenu")
    if "soundrts.animation" not in sys.modules:
        ani = types.ModuleType("soundrts.animation")
        ani.noise = lambda *a, **kw: None
        sys.modules["soundrts.animation"] = ani
    if "soundrts.clientgamenews" not in sys.modules:
        news = types.ModuleType("soundrts.clientgamenews")
        news.must_be_said = lambda *a, **kw: False
        sys.modules["soundrts.clientgamenews"] = news
    if "soundrts.clientgameorder" not in sys.modules:
        co = types.ModuleType("soundrts.clientgameorder")
        co.get_orders_list = lambda: []
        co.substitute_args = lambda *a, **kw: None
        sys.modules["soundrts.clientgameorder"] = co
    if "soundrts.lib.sound" not in sys.modules:
        s = types.ModuleType("soundrts.lib.sound")
        s.distance = lambda *a, **kw: 0
        s.psounds = None
        s.angle = lambda *a, **kw: 0
        sys.modules["soundrts.lib.sound"] = s


def _import_entity_view_properties():
    """安全加载 EntityViewProperties，跳过桩掉的依赖。"""
    _stub_client_modules()
    try:
        from soundrts.clientgameentity.properties import EntityViewProperties
        return EntityViewProperties
    except Exception:
        return None


_EVP = _import_entity_view_properties()


class _StubModel:
    """模拟 EntityView.model 的最小对象。"""

    def __init__(self, player, number=1):
        self.player = player
        self.number = number
        self.type_name = "footman"


class _StubInterfacePlayer:
    """human 玩家：拥有 allied 列表，不是 neutral。"""

    neutral = False

    def __init__(self):
        self.allied = [self]


class _StubInterface:
    def __init__(self, player):
        self.player = player


class _StubPlayer:
    """target 单位所属玩家。"""

    def __init__(self, neutral, name=None):
        self.neutral = neutral
        # neutral player 的 name 在 base.py:270 是空列表，对齐之
        self.name = name if name is not None else ([] if neutral else ["enemy_name"])


def _make_view(target_is_neutral, target_is_allied=False):
    if _EVP is None:
        pytest.skip("EntityViewProperties 无法在测试环境加载（client-side 依赖）")

    class _StubEntityView(_EVP):
        is_memory = False
        speed = 0

        def __init__(self, interface, model):
            self.interface = interface
            self.model = model
            self.player = model.player
            self.number = model.number
            self.type_name = model.type_name

        @property
        def short_title(self):
            return ["footman_title"]

    human = _StubInterfacePlayer()
    target_player = _StubPlayer(neutral=target_is_neutral)
    if target_is_allied:
        human.allied.append(target_player)
    interface = _StubInterface(human)
    model = _StubModel(player=target_player)
    return _StubEntityView(interface, model)


def test_title_neutral_says_neutral_not_enemy():
    """neutral 玩家的单位 Tab 标题包含 NEUTRAL，不包含 ENEMY。"""
    view = _make_view(target_is_neutral=True)
    title = view.title
    assert mp.NEUTRAL[0] in title
    assert mp.ENEMY[0] not in title
    assert mp.ALLY[0] not in title


def test_title_hostile_still_says_enemy():
    """非 neutral 且非盟友的玩家：仍然是 ENEMY。"""
    view = _make_view(target_is_neutral=False)
    title = view.title
    assert mp.ENEMY[0] in title
    assert mp.NEUTRAL[0] not in title


def test_title_allied_still_says_ally():
    """同盟玩家：仍然是 ALLY，与 neutral 改动无关。"""
    view = _make_view(target_is_neutral=False, target_is_allied=True)
    title = view.title
    assert mp.ALLY[0] in title
    assert mp.NEUTRAL[0] not in title
    assert mp.ENEMY[0] not in title


def test_neutral_constant_distinct_from_enemy():
    """NEUTRAL 与 ENEMY / ALLY 是不同的 TTS ID，避免被误显示成"敌人"。"""
    assert mp.NEUTRAL != mp.ENEMY
    assert mp.NEUTRAL != mp.ALLY
    assert mp.NEUTRAL == [5027]


def test_tts_files_have_neutral_entry():
    """en / zh 的 tts.txt 都应有 5027 条目，让 voice 能正确播报"中立"。"""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "res"
    for path in (root / "ui" / "tts.txt", root / "ui-zh" / "tts.txt"):
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^5027[\t ]+\S", text, flags=re.MULTILINE), (
            f"{path} 缺少 5027 条目（NEUTRAL 的文案）"
        )


# --- 中立单位不触发战斗音乐 / 新敌人提示 -------------------------------------
#
# 5 个改动点（game_navigation.py / perception.py / combat.py (×2) /
# game_display.py / events.py (×2)）都注入了同样的过滤模式：
#     is_an_enemy(X) and not getattr(X.player, "neutral", False)
# 直接运行这些 client-side 模块的真实代码会拉起 pygame/locale 链路（已在前面
# 用 sys.modules 桩规避了 properties.py，但战斗音乐路径涉及 sound/pygame 太多，
# 不适合在测试里整模块加载）。所以这里同时做两件事：
#   1. 逻辑等价测试：模拟过滤式的真值表，对 4 种 player 组合验证结果正确；
#   2. 源码契约测试：确认 5 个修复点的源文件确实包含 `neutral` 检查。


def _hostile_for_alert(viewer_player, target_unit):
    """模拟改动后所有"是否触发新敌人提示/战斗音乐"使用的同一判定。"""
    p = getattr(target_unit, "player", None)
    if p is None:
        return False
    is_enemy = p not in viewer_player.allied
    return is_enemy and not getattr(p, "neutral", False)


class _UnitWithPlayer:
    def __init__(self, player):
        self.player = player


def test_alert_filter_truth_table():
    """neutral 玩家的单位永远不触发提示；hostile 仍然触发；ally 永远不触发。"""
    human = _StubInterfacePlayer()
    neutral = _StubPlayer(neutral=True)
    hostile = _StubPlayer(neutral=False)
    ally = _StubPlayer(neutral=False)
    human.allied.append(ally)

    # 触发表
    assert _hostile_for_alert(human, _UnitWithPlayer(neutral)) is False  # 关键
    assert _hostile_for_alert(human, _UnitWithPlayer(hostile)) is True
    assert _hostile_for_alert(human, _UnitWithPlayer(ally)) is False
    assert _hostile_for_alert(human, _UnitWithPlayer(human)) is False  # 自己
    assert _hostile_for_alert(human, _UnitWithPlayer(None)) is False  # 无主对象


def test_alert_filter_missing_neutral_attribute_defaults_false():
    """player 上没有 neutral 属性时按 False 处理（行为不变）。"""
    class _OldStylePlayer:
        pass  # 没有 neutral 字段
    human = _StubInterfacePlayer()
    old = _OldStylePlayer()
    # 不在 allied 中 → is_an_enemy=True；neutral 字段缺失 → False → 仍触发
    assert _hostile_for_alert(human, _UnitWithPlayer(old)) is True


# --- 源码契约测试：确保 5 个修复点都引入了 `neutral` 过滤 ---------------------


def _source(path_parts):
    """读取 soundrts 源文件全文（基于 tests 文件相对路径定位）。"""
    from pathlib import Path
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def test_game_navigation_filters_neutral_for_new_enemy():
    src = _source(["soundrts", "clientgame", "game_navigation.py"])
    # 在 update_fog_of_war 的 perception 循环中应有 neutral 过滤
    assert "is_an_enemy(m)" in src
    assert 'getattr(\n                getattr(m, "player", None), "neutral", False\n            )' in src \
        or 'getattr(getattr(m, "player", None), "neutral", False)' in src


def test_perception_filters_neutral_for_new_enemy():
    src = _source(["soundrts", "worldplayerbase", "perception.py"])
    assert 'getattr(\n                    getattr(o, "player", None), "neutral", False\n                )' in src \
        or 'getattr(getattr(o, "player", None), "neutral", False)' in src


def test_combat_check_battle_status_filters_neutral():
    src = _source(["soundrts", "clientgameentity", "combat.py"])
    # _set_battle_mode 和 _check_battle_status_for_music 中各有一处
    assert src.count("getattr(obj.player, 'neutral', False)") >= 2


def test_game_display_check_battle_status_filters_neutral():
    src = _source(["soundrts", "clientgame", "game_display.py"])
    assert "getattr(obj.player, 'neutral', False)" in src


def test_events_attack_wounded_skip_neutral_combat_music():
    src = _source(["soundrts", "clientgameentity", "events.py"])
    # on_attack 和 on_wounded 各有 is_neutral_involved 分支
    assert src.count("is_neutral_involved") >= 2


# --- place_summary 应把中立单位单独归为"中立"而非"敌人" ----------------------
#
# 直接 import game_unit_control 会拉起 clientgame/__init__.py 整个链路（含
# pygame、locale、style.load → 加载真实资源文件），在测试中极难桩干净。
# 改用源码契约 + 通过模块 spec 隔离加载的方式来验证修复点存在。


def test_game_unit_control_place_summary_classifies_neutrals_separately():
    """place_summary 必须为 neutral 单位维护单独的列表，并用 mp.NEUTRAL 输出。"""
    src = _source(["soundrts", "clientgame", "game_unit_control.py"])
    # 必须存在 neutrals 列表
    assert "neutrals = []" in src
    # neutral 归类已集中到 _unit_bucket：对 neutral 玩家的单位返回 neutrals，
    # 并在"容器内"与"普通单位"两条路径上都经由 _unit_bucket(obj.model) 归类。
    assert "return neutrals" in src
    assert src.count("_unit_bucket(obj.model)") >= 2
    # 结果构建段必须有 NEUTRAL 标注分支
    assert "mp.NEUTRAL" in src
    assert "if neutrals:" in src


def test_game_unit_control_tell_enemies_splits_neutral():
    """tell_enemies_in_square 必须把 neutral 与 enemy 分两条 voice.info 播报。"""
    src = _source(["soundrts", "clientgame", "game_unit_control.py"])
    # 函数体应同时收集 enemies / neutrals
    func_idx = src.index("def tell_enemies_in_square")
    body = src[func_idx:func_idx + 1500]
    assert "neutrals = []" in body
    assert "neutrals.append" in body
    assert "mp.NEUTRAL" in body
    assert "mp.ENEMY" in body


def test_place_summary_logic_classification():
    """逻辑级测试: 用同等的"分类规则"小函数验证 enemy / neutral / ally / 自己 的
    分类正确性, 不依赖 client-side 模块。规则与 game_unit_control.place_summary
    完全等价: 先看 is_an_enemy, 再细分 neutral; 否则按盟友/自己/资源归类。"""

    def classify(obj_player, interface_player, interface_allied):
        # 模拟 is_an_enemy: non-allied 视为敌人
        if obj_player is None:
            return "resource"
        is_enemy = obj_player not in interface_allied
        if is_enemy:
            if getattr(obj_player, "neutral", False):
                return "neutral"
            return "enemy"
        if obj_player in interface_allied and obj_player is not interface_player:
            return "ally"
        if obj_player is interface_player:
            return "self"
        return "resource"

    human = _StubInterfacePlayer()
    neutral = _StubPlayer(neutral=True)
    hostile = _StubPlayer(neutral=False)
    ally = _StubPlayer(neutral=False)
    human.allied.append(ally)

    assert classify(neutral, human, human.allied) == "neutral"  # 关键: 不再归为 enemy
    assert classify(hostile, human, human.allied) == "enemy"
    assert classify(ally, human, human.allied) == "ally"
    assert classify(human, human, human.allied) == "self"
    assert classify(None, human, human.allied) == "resource"
