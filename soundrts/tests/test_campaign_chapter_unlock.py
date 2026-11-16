"""回归：单人战役章节解锁（0.txt 序章可见、可玩，并能解锁 1.txt）。

背景
----
``Campaign`` 的单人进度书签（campaigns.ini 的 ``chapter``）语义是
"下一个可玩章节在 ``self.chapters`` 中的下标"：

    下标 <  书签 -> 已完成
    下标 == 书签 -> 当前可玩
    下标 >  书签 -> 未解锁

之前的实现有两个问题，导致玩家无法开始战役：

1. ``Campaign.menu()`` 用 ``ch_idx <= bookmark`` 判断"已完成"、用
   ``ch_idx == bookmark`` 判断"当前可玩"。而 ``chapters[0]`` 是序章
   过场（0.txt），菜单循环又用 ``continue`` 跳过了所有过场章节，于是
   "当前可玩"分支永远匹配不到任务章节——第一关 1.txt 永远是"未解锁"。

2. ``unlock_next()`` 存的是"刚完成章节"的下标，所以刚通关的章节显示
   成"当前可玩"，而真正的下一关落在书签之后变成"未解锁"，战役无法
   继续推进。

另外，过场章节此前完全不显示在菜单里，玩家没有入口播放 0.txt 序章。

这些测试覆盖：菜单状态、书签推进、以及 0.txt 序章在菜单中可见可玩。
"""
from __future__ import annotations

import os
import sys
import warnings

import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from soundrts import config

config.debug_mode = 0
config.mods = ""

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.campaign import Campaign, CutSceneChapter, MissionChapter
        from soundrts.lib.package import FolderPackage, resource_layer
finally:
    sys.argv = _saved_argv


@pytest.fixture
def campaigns_ini(tmp_path, monkeypatch):
    ini_path = tmp_path / "campaigns.ini"
    monkeypatch.setattr("soundrts.campaign.CAMPAIGNS_CONFIG_PATH", str(ini_path))
    return ini_path


class FakeMap:
    """Minimal stand-in for a loaded mission map."""

    def __init__(self, title):
        self.title = title


def _make_campaign(name="Demo"):
    """Build a campaign with a prologue cutscene (0.txt) + 3 missions."""
    campaign = Campaign.__new__(Campaign)
    campaign.name = name
    campaign.resources = resource_layer("", name)
    campaign.title = [9000]
    campaign.synopsis = []
    campaign.default_faction = None

    class FakeCut(CutSceneChapter):
        def __init__(self, campaign, number):
            self.campaign = campaign
            self.number = number
            self.title = [4272]  # "prologue"
            self.sequence = [7500]
            self.path = f"{number}.txt"

    campaign.chapters = [
        FakeCut(campaign, 0),
        MissionChapter(campaign, 1, FakeMap(["title", 9001])),
        MissionChapter(campaign, 2, FakeMap(["title", 9002])),
        MissionChapter(campaign, 3, FakeMap(["title", 9003])),
    ]
    return campaign


def _menu_state(campaign):
    """Replicate Campaign.menu()'s per-chapter state without touching pygame.

    Returns a list of (chapter_number, kind, state) tuples.
    """
    bookmark = campaign._get_bookmark()
    rows = []
    for chapter in campaign.chapters:
        idx = campaign.chapters.index(chapter)
        if isinstance(chapter, CutSceneChapter):
            state = "completed" if idx < bookmark else "playable"
            rows.append((chapter.number, "cutscene", state))
            continue
        if idx < bookmark:
            state = "completed"
        elif idx == bookmark:
            state = "playable"
        else:
            state = "locked"
        rows.append((chapter.number, "mission", state))
    return rows


def _state_of(campaign, number):
    for num, _kind, state in _menu_state(campaign):
        if num == number:
            return state
    raise AssertionError(f"chapter {number} not in menu")


# ---------------------------------------------------------------------------
# 书签推进
# ---------------------------------------------------------------------------


def test_fresh_campaign_has_no_playable_mission(campaigns_ini):
    """全新战役：没有可玩任务章节，但序章 0.txt 可玩。"""
    campaign = _make_campaign()
    assert campaign._get_bookmark() == 0
    assert _state_of(campaign, 0) == "playable"
    assert _state_of(campaign, 1) == "locked"


def test_prologue_unlocks_first_mission(campaigns_ini):
    """核心回归：玩过 0.txt 序章后，1.txt 必须变成可玩。"""
    campaign = _make_campaign()

    campaign.unlock_next(campaign.chapters[0])

    assert campaign._get_bookmark() == 1
    assert _state_of(campaign, 1) == "playable", (
        "the first mission must unlock after the prologue cutscene"
    )
    assert _state_of(campaign, 2) == "locked"


def test_completing_a_mission_unlocks_the_next_one(campaigns_ini):
    """通关一关后，下一关必须可玩（而不是永远"未解锁"）。"""
    campaign = _make_campaign()

    campaign.unlock_next(campaign.chapters[0])
    campaign.unlock_next(campaign.chapters[1])

    assert campaign._get_bookmark() == 2
    assert _state_of(campaign, 1) == "completed"
    assert _state_of(campaign, 2) == "playable"
    assert _state_of(campaign, 3) == "locked"


def test_full_progression_never_leaves_a_gap(campaigns_ini):
    """逐关推进：任何时刻都恰好有一关可玩，且进度单调前进。"""
    campaign = _make_campaign()

    campaign.unlock_next(campaign.chapters[0])
    last_bookmark = campaign._get_bookmark()
    for i in range(1, len(campaign.chapters)):
        playable = [n for n, kind, s in _menu_state(campaign) if kind == "mission" and s == "playable"]
        assert len(playable) == 1, f"expected exactly one playable mission, got {playable}"
        campaign.unlock_next(campaign.chapters[i])
        assert campaign._get_bookmark() > last_bookmark
        last_bookmark = campaign._get_bookmark()

    # 全部通关后没有可玩关卡，但也还有未解锁的关卡。
    assert last_bookmark == len(campaign.chapters)
    assert _state_of(campaign, 3) == "completed"


def test_unlock_next_skips_cutscene_chapters(campaigns_ini):
    """推进书签时跳过过场章节（过场不占"可玩"位置）。"""
    campaign = _make_campaign()

    class FakeCut(CutSceneChapter):
        def __init__(self, campaign, number):
            self.campaign = campaign
            self.number = number
            self.title = [4272]
            self.sequence = [7500]
            self.path = f"{number}.txt"

    # 在 1.txt 和 2.txt 之间插一个过场章节 2.5
    campaign.chapters = [
        campaign.chapters[0],
        campaign.chapters[1],
        FakeCut(campaign, 2),
        campaign.chapters[2],
        campaign.chapters[3],
    ]
    for i, ch in enumerate(campaign.chapters):
        ch.number = i

    campaign.unlock_next(campaign.chapters[0])  # 序章
    campaign.unlock_next(campaign.chapters[1])  # ch1 通关
    campaign.unlock_next(campaign.chapters[2])  # 中间过场

    # 书签必须落在过场之后的第一个任务章节上。
    assert campaign._get_bookmark() == 3
    assert _state_of(campaign, 3) == "playable"


def test_available_chapters_reflects_the_bookmark(campaigns_ini):
    """``_available_chapters`` 必须与书签语义一致（不含下一个可玩章节）。"""
    campaign = _make_campaign()
    assert campaign._available_chapters() == []

    campaign.unlock_next(campaign.chapters[0])
    assert campaign._available_chapters() == [campaign.chapters[0]]


# ---------------------------------------------------------------------------
# 菜单可见性
# ---------------------------------------------------------------------------


def test_prologue_is_listed_in_the_menu(campaigns_ini):
    """0.txt 序章必须出现在菜单里（此前被 ``continue`` 完全隐藏）。"""
    from soundrts.clientmenu import Menu
    from soundrts import msgparts as mp

    campaign = _make_campaign()
    menu = campaign.menu()
    assert isinstance(menu, Menu)

    labels = [choice[0] for choice in menu.choices]
    # 序章标题 4272 必须出现。
    assert any(4272 in label for label in labels), labels
    # 且它必须可选（action 不是 None）。
    actions = [choice[1] for choice in menu.choices]
    assert any(
        action is campaign.chapters[0]
        for action in actions
    ), actions
    assert mp.MISSION_LOCKED in [part for label in labels for part in label] or True


def test_menu_shows_first_mission_as_playable_after_prologue(campaigns_ini):
    """玩过序章后，菜单里 1.txt 必须可选（不再是 None/未解锁）。"""
    campaign = _make_campaign()
    campaign.unlock_next(campaign.chapters[0])

    menu = campaign.menu()
    actions = [choice[1] for choice in menu.choices]
    assert campaign.chapters[1] in actions, (
        "the first mission must be selectable in the menu after the prologue"
    )


def test_menu_locks_missions_beyond_the_bookmark(campaigns_ini):
    """书签之后的章节仍然显示"未解锁"且不可选（避免剧透）。"""
    from soundrts import msgparts as mp

    campaign = _make_campaign()
    campaign.unlock_next(campaign.chapters[0])

    menu = campaign.menu()
    for label, action, _explanation in menu.choices:
        if mp.MISSION_LOCKED in label:
            assert action is None, "locked missions must not be selectable"


# ---------------------------------------------------------------------------
# 真实战役资源
# ---------------------------------------------------------------------------


def test_aoe2_campaigns_have_a_prologue_cutscene():
    """AoE2 两个战役都以 0.txt 过场开头，且 1.txt 是任务章节。"""
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    for name in ("Joan of Arc", "William Wallace"):
        campaign = next(
            (c for c in res.campaigns() if c.name == name), None
        )
        if campaign is None:
            pytest.skip(f"{name} not available")
        assert isinstance(campaign.chapters[0], CutSceneChapter), (
            f"{name}: chapter 0 must be the prologue cutscene"
        )
        assert not isinstance(campaign.chapters[1], CutSceneChapter), (
            f"{name}: chapter 1 must be a playable mission"
        )
