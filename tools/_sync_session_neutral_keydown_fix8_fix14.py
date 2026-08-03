# -*- coding: utf-8 -*-
"""Incremental sync: neutral hostility / ch25-27 / KEYDOWN collapse → 修复8 & 修复14."""
from __future__ import annotations

from pathlib import Path

MAIN = Path(r"C:\Users\Administrator\Desktop\soundrts1.3.8.1项目\soundrts-1.4.5.1")
TARGETS = [Path(r"E:\代码\修复8"), Path(r"E:\代码\修复14")]
LOG: list[str] = []


def patch(root: Path, rel: str, old: str, new: str, name: str) -> None:
    p = root / rel
    if not p.exists():
        LOG.append(f"FAIL missing-file {root.name}:{name}")
        return
    t = p.read_text(encoding="utf-8")
    if old not in t:
        if new[:80] in t or (new and new in t):
            LOG.append(f"SKIP already {root.name}:{name}")
            return
        LOG.append(f"FAIL missing-anchor {root.name}:{name}")
        return
    c = t.count(old)
    if c != 1:
        LOG.append(f"FAIL count={c} {root.name}:{name}")
        return
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    LOG.append(f"OK {root.name}:{name}")


def ensure_new(root: Path, rel: str) -> None:
    src = MAIN / rel
    dst = root / rel
    if dst.exists():
        LOG.append(f"SKIP exists {root.name}:{rel}")
        return
    if not src.exists():
        LOG.append(f"FAIL no-src {rel}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    LOG.append(f"NEW {root.name}:{rel}")


def patch_docs_fix8_only() -> None:
    root = Path(r"E:\代码\修复8")
    if not (root / "doc_src").exists():
        LOG.append("SKIP docs (no doc_src)")
        return

    patch(
        root,
        "doc_src/src/en/mod/mapmaking.rst",
        """set_ai_mode — change AI mode on the trigger owner's units::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Syntax: ``(set_ai_mode \\<offensive|defensive|guard|chase\\> [\\<square\\> \\<count\\> \\<type\\> ...])``.

set_yield_on_defeat — toggle per-unit yield (zero HP → yield instead of die)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Syntax: ``(set_yield_on_defeat \\<0|1\\> [\\<square\\> \\<count\\> \\<type\\> ...])``. Can also set ``yield_on_defeat 1`` in ``rules.txt``.

units_yielded — count of yielded enemy units::
""",
        """set_ai_mode — change AI mode on the trigger owner's units::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_neutral 0) (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Syntax: ``(set_ai_mode \\<offensive|defensive|guard|chase\\> [\\<square\\> \\<count\\> \\<type\\> ...])``.
Setting ``offensive`` on a non-wildlife neutral computer also clears ``neutral`` automatically
(so player units start auto-attacking them). Prefer an explicit ``(set_neutral 0)`` for clarity.

set_neutral — toggle a player's ``neutral`` flag::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2) (set_neutral 0)
    trigger player1 (alliance_declined_with computer1) (set_neutral 1 computer1)

Syntax: ``(set_neutral \\<0|1> [\\<player1|computer1|...>])``.
Use ``0`` when a story NPC leaves passive-creep status and enters a real fight;
use ``1`` (optionally with a player ref) to restore neutrality after declining an alliance.
Setting ``1`` also restores units to ``guard`` + counterattack. Keep wildlife-only slots neutral.

set_yield_on_defeat — toggle per-unit yield (zero HP → yield instead of die)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Syntax: ``(set_yield_on_defeat \\<0|1\\> [\\<square\\> \\<count\\> \\<type\\> ...])``. Can also set ``yield_on_defeat 1`` in ``rules.txt``.

set_counterattack — toggle per-unit guard counterattack::

    trigger computer1 (map_flag ch27_duel_started)
        (set_counterattack 0 c2 12 npc_knight_escort c2 12 npc_footman_escort c2 12 npc_archer_escort)

Syntax: ``(set_counterattack \\<0|1\\> [\\<square\\> \\<count\\> \\<type\\> ...])``.
Use ``0`` so story escorts leave a duel arena without joining when the boss is hit
(``_notify_guard_units`` only wakes units with counterattack enabled).

units_yielded — count of yielded enemy units::
""",
        "docs-en-mapmaking-triggers",
    )

    patch(
        root,
        "doc_src/src/en/mod/mapmaking.rst",
        "- ch. 25 (token to Roland): killable before delivery; then ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``\n"
        "- ch. 26 (banner to Vera): ``transfer_units``\n"
        "- ch. 27 (duel with Marco): ``has_entered c2 raynor7`` + cutscene 7718; Marco-only ``set_ai_mode offensive``; escorts ``order`` to ``c1`` to clear the arena; ``units_yielded_by raynor7``; ``stop_all_units`` + selective ``allied_control`` (4 escort knights)\n",
        "- ch. 25 (token to Roland): killable before delivery; then ``set_neutral 0`` + ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``\n"
        "- ch. 26 (banner to Vera): ``transfer_units``\n"
        "- ch. 27 (duel with Marco): ``has_entered c2 raynor7`` + cutscene 7718; Marco-only ``set_ai_mode offensive``; escorts ``set_counterattack 0`` then ``imperative go`` to ``c1`` to clear the arena; ``units_yielded_by raynor7``; ``stop_all_units`` + selective ``allied_control`` (8 escort knights)\n",
        "docs-en-mapmaking-northern-arc",
    )

    patch(
        root,
        "doc_src/src/en/player/campaign-northern-arc.rst",
        "2. computer1 (flag set): Marco only `(set_ai_mode offensive c2 1 npc_marco_ironhand)`; escorts `(order … ((go c1)))` to c1 to clear the arena.\n",
        "2. computer1 (flag set): escorts `(set_counterattack 0)` then `(imperative go c1)` to clear the arena; Marco only `(set_ai_mode offensive c2 1 npc_marco_ironhand)`.\n",
        "docs-en-northern-arc-ch27",
    )

    patch(
        root,
        "doc_src/src/zh/player/campaign-northern-arc.rst",
        "2. ``computer1`` （同标记已设）：仅马尔科 `(set_ai_mode offensive c2 1 npc_marco_ironhand)`；其余护卫 `(order … ((go c1)))` 前往 ``c1`` 让出阵前。\n",
        "2. ``computer1`` （同标记已设）：护卫先 `(set_counterattack 0)` 再 `(imperative go c1)` 让出阵前；仅马尔科 `(set_ai_mode offensive c2 1 npc_marco_ironhand)`。\n",
        "docs-zh-northern-arc-ch27",
    )

    patch(
        root,
        "doc_src/src/en/player/unit-default-behavior.rst",
        "- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((go c1)))` — ch. 27 (``raynor7``): Marco only goes offensive; escorts move to c1 to clear the arena\n",
        "- `(set_counterattack 0 …)` + `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((imperative go c1)))` — ch. 27 (``raynor7``): escorts stand down and leave; Marco only goes offensive\n",
        "docs-en-unit-behavior-ch27",
    )

    patch(
        root,
        "doc_src/src/zh/player/unit-default-behavior.rst",
        "- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order (c2 4 npc_knight_escort) ((go c1)))` 等 — 第 27 章（``raynor7``）：仅马尔科切进攻；护卫前往 ``c1`` 让出阵前\n",
        "- `(set_counterattack 0 …)` + `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((imperative go c1)))` — 第 27 章（``raynor7``）：护卫关闭反击并离场；仅马尔科切进攻\n",
        "docs-zh-unit-behavior-ch27",
    )


SET_NEUTRAL_METHOD = r'''
    def set_neutral(self, value):
        """设置/清除中立标记，并立刻失效各玩家的敌对目标缓存。

        ``computer_only ... neutral`` 开局的中立电脑在进入正式交战
        （例如决斗触发 ``set_ai_mode offensive`` / ``set_neutral 0``）后
        必须清掉 ``neutral``，否则玩家单位的自动攻击会继续忽略他们
        （``player_is_a_hostile_enemy`` / ``can_attack`` 排除中立）。

        重新标为中立（``set_neutral 1``，例如拒绝结盟后）会把存活单位
        恢复为 guard + 反击，避免仍以 offensive 主动追杀玩家。
        狩猎动物槽位应保持中立，不要对 wildlife-only 玩家调用本方法清中立。
        """
        value = bool(value)
        prev = bool(getattr(self, "neutral", False))
        self.neutral = value
        if value:
            for u in list(getattr(self, "units", []) or ()):
                if not getattr(u, "presence", True):
                    continue
                if hasattr(u, "ai_mode"):
                    u.ai_mode = "guard"
                if hasattr(u, "counterattack_enabled"):
                    u.counterattack_enabled = True
        if prev == value:
            return
        world = getattr(self, "world", None)
        if world is None:
            return
        for p in getattr(world, "players", []) or ():
            if hasattr(p, "_enemy_players_cache_time"):
                p._enemy_players_cache_time = -1
            if hasattr(p, "_enemy_units_cache_time"):
                p._enemy_units_cache_time = -1
            if hasattr(p, "_enemy_units_set_time"):
                p._enemy_units_set_time = -1
            if hasattr(p, "_perception_set_time"):
                p._perception_set_time = -1
            if hasattr(p, "_enemy_menace_cache_time"):
                p._enemy_menace_cache_time = -1
            if hasattr(p, "_known_enemies"):
                try:
                    p._known_enemies.clear()
                except Exception:
                    p._known_enemies = {}
            if hasattr(p, "_known_enemies_time"):
                try:
                    p._known_enemies_time.clear()
                except Exception:
                    p._known_enemies_time = {}
            hit = getattr(p, "_known_enemies_hit", None)
            if isinstance(hit, list) and len(hit) >= 3:
                hit[0] = None
                hit[1] = -1
                hit[2] = ()
            if hasattr(p, "_enemy_player_cache"):
                p._enemy_player_cache = {}
                p._enemy_player_timestamp = 0

    def set_ai(self, ai_type):
        pass
'''

LANG_SET_AI_OLD = r'''    def lang_set_ai_mode(self, args):
        """设置触发器所属玩家单位的 AI 模式。

        用法：``(set_ai_mode <offensive|defensive|guard|chase> [<方格> <数量> <类型> ...])``

        带单位选择符时仅作用于匹配单位；省略时作用于该玩家全部存活单位。
        """
        if not args:
            return
        mode = str(args[0])
        if mode not in ("offensive", "defensive", "guard", "chase"):
            warning("set_ai_mode: unknown mode %s", mode)
            return
        if len(args) == 1:
            targets = [
                u for u in self.units if getattr(u, "presence", True)
            ]
        else:
            targets = self._units(args[1:])
        for u in targets:
            u.ai_mode = mode

    def lang_set_yield_on_defeat(self, args):
'''

LANG_SET_AI_NEW = r'''    def lang_set_ai_mode(self, args):
        """设置触发器所属玩家单位的 AI 模式。

        用法：``(set_ai_mode <offensive|defensive|guard|chase> [<方格> <数量> <类型> ...])``

        带单位选择符时仅作用于匹配单位；省略时作用于该玩家全部存活单位。

        当模式为 ``offensive`` 且本玩家仍是中立非野生动物电脑时，会自动
        ``set_neutral 0``：否则单位虽会主动进攻，玩家侧自动攻击仍会忽略他们。
        """
        if not args:
            return
        mode = str(args[0])
        if mode not in ("offensive", "defensive", "guard", "chase"):
            warning("set_ai_mode: unknown mode %s", mode)
            return
        if len(args) == 1:
            targets = [
                u for u in self.units if getattr(u, "presence", True)
            ]
        else:
            targets = self._units(args[1:])
        for u in targets:
            u.ai_mode = mode
        if mode == "offensive" and getattr(self, "neutral", False):
            from .base import player_is_wildlife_only

            if not player_is_wildlife_only(self):
                self.lang_set_neutral([0])

    def lang_set_neutral(self, args):
        """设置玩家的中立标记。

        用法：
            ``(set_neutral <0|1>)`` — 作用于触发器所属玩家
            ``(set_neutral <0|1> <player1|computer1|...>)`` — 作用于指定玩家

        ``0`` 清除中立（成为可被自动攻击的敌对电脑）；``1`` 重新标为中立
        （并恢复 guard + 反击）。战役决斗开局用 ``(set_neutral 0)``；
        拒绝结盟后可用 ``(set_neutral 1 computer1)`` 恢复中立关系。
        ``set_ai_mode offensive`` 本身也会自动对非野生动物电脑清中立。
        """
        if not args:
            return
        try:
            value = int(args[0])
        except (TypeError, ValueError):
            warning("set_neutral: invalid value %s", args[0])
            return
        if value not in (0, 1):
            warning("set_neutral: expected 0 or 1, got %s", args[0])
            return
        if len(args) == 1:
            targets = [self]
        else:
            targets = []
            for ref in args[1:]:
                player = self._resolve_map_player_ref(ref)
                if player is None:
                    warning("set_neutral: unknown player %s", ref)
                    continue
                targets.append(player)
        flag = bool(value)
        for player in targets:
            if hasattr(player, "set_neutral"):
                player.set_neutral(flag)
            else:
                player.neutral = flag
                if flag:
                    for u in list(getattr(player, "units", []) or ()):
                        if not getattr(u, "presence", True):
                            continue
                        if hasattr(u, "ai_mode"):
                            u.ai_mode = "guard"
                        if hasattr(u, "counterattack_enabled"):
                            u.counterattack_enabled = True

    def lang_set_yield_on_defeat(self, args):
'''

LANG_COUNTER_INSERT_AFTER = r'''        for u in targets:
            u.yield_on_defeat = value

    def lang_release_yielded_units(self, args):
'''

LANG_COUNTER_BLOCK = r'''        for u in targets:
            u.yield_on_defeat = value

    def lang_set_counterattack(self, args):
        """设置触发器所属玩家单位的反击开关。

        用法：``(set_counterattack <0|1> [<方格> <数量> <类型> ...])``

        带单位选择符时仅作用于匹配单位；省略时作用于该玩家全部存活单位。
        ``0`` 会同时清空 ``last_attacker`` 并中止当前攻击目标，避免护卫
        在比武开场时因 ``_notify_guard_units`` 被拉进决斗。
        """
        if not args:
            return
        try:
            value = int(args[0])
        except (TypeError, ValueError):
            warning("set_counterattack: invalid value %s", args[0])
            return
        if value not in (0, 1):
            warning("set_counterattack: expected 0 or 1, got %s", args[0])
            return
        if len(args) == 1:
            targets = [
                u for u in self.units if getattr(u, "presence", True)
            ]
        else:
            targets = self._units(args[1:])
        enabled = bool(value)
        for u in targets:
            if hasattr(u, "counterattack_enabled"):
                u.counterattack_enabled = enabled
            if not enabled:
                if hasattr(u, "last_attacker"):
                    u.last_attacker = None
                if getattr(u, "action_target", None) is not None:
                    u.action_target = None

    def lang_release_yielded_units(self, args):
'''

COLLAPSE_HELPER = r'''
def _collapse_keydown_repeats(events):
    """同一批次里同键的重复 KEYDOWN 只保留第一次。

    作弊模式 / 大地图下 ``select_square`` 很重时，pygame key-repeat 会在
    一次物理按键期间往队列塞入多个 KEYDOWN；若本帧 ``event.get()`` 一次
    取到整串，就会连续跳多格（a1→b1→c1→d1）。菜单侧用
    ``pygame.event.clear([KEYDOWN])`` 解决；游戏循环还需折叠已取出的批次。
    """
    seen_keys = set()
    out = []
    for e in events:
        if getattr(e, "type", None) == KEYDOWN:
            key = getattr(e, "key", None)
            if key in seen_keys:
                continue
            seen_keys.add(key)
        out.append(e)
    return out


'''

PROCESS_EVENTS_OLD = r'''    for e in pygame.event.get():
        if e.type == USEREVENT:
            voice.update()
        elif e.type == USEREVENT + 1:
            psounds.update()
        # 处理倒地音效定时器事件
        elif e.type in interface._falling_callbacks:
            falling_data = interface._falling_callbacks.pop(e.type)
            falling_data['obj'].launch_event(falling_data['sound'])
            pygame.time.set_timer(e.type, 0)  # 停止定时器
        elif e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            # F9 目标字幕：Esc 关闭（开场目标播完后本就不该残留）
            if e.key == K_ESCAPE:
                try:
                    from ..lib import pygame_ui

                    if pygame_ui.narrative_is_active():
                        pygame_ui.end_narrative()
                        from .game_display import display

                        display(interface)
                        continue
                except Exception:
                    pass
            # 首先检查是否在缩放输入模式
            if interface._zoom_input_mode:
                if _handle_zoom_input(interface, e):
                    continue  # 输入已处理，跳过其他处理
            
            # 然后尝试属性界面的键盘处理
            if hasattr(interface, "_process_keyboard_event") and interface._process_keyboard_event(e):
                continue
                
            if interface.shortcut_mode:
                _execute_order_shortcut(interface, e)
                interface.shortcut_mode = False
            else:
                # L/R Shift+C copy; L/R Shift+B append (primary / secondary)
                try:
                    from pygame.locals import K_b, K_c
                    from ..lib import voice_libs

                    key = e.key
                    if key in (ord("C"), ord("B")):
                        key = ord(chr(key).lower())
                    if (
                        (e.mod & KMOD_SHIFT)
                        and not (e.mod & KMOD_CTRL)
                        and key in (K_b, K_c)
                        and voice_libs.handle_hotkey(key, e.mod)
                    ):
                        continue
                except Exception:
                    pass
                try:
                    interface._bindings.process_keydown_event(e)
                except KeyError:
                    voice.item(mp.BEEP)
        elif interface.display_is_active:
            _process_fullscreen_mode_mouse_event(interface, e)
'''

PROCESS_EVENTS_NEW = r'''    for e in _collapse_keydown_repeats(pygame.event.get()):
        if e.type == USEREVENT:
            voice.update()
        elif e.type == USEREVENT + 1:
            psounds.update()
        # 处理倒地音效定时器事件
        elif e.type in interface._falling_callbacks:
            falling_data = interface._falling_callbacks.pop(e.type)
            falling_data['obj'].launch_event(falling_data['sound'])
            pygame.time.set_timer(e.type, 0)  # 停止定时器
        elif e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            # F9 目标字幕：Esc 关闭（开场目标播完后本就不该残留）
            if e.key == K_ESCAPE:
                try:
                    from ..lib import pygame_ui

                    if pygame_ui.narrative_is_active():
                        pygame_ui.end_narrative()
                        from .game_display import display

                        display(interface)
                        pygame.event.clear([KEYDOWN])
                        continue
                except Exception:
                    pass
            # 首先检查是否在缩放输入模式
            if interface._zoom_input_mode:
                if _handle_zoom_input(interface, e):
                    pygame.event.clear([KEYDOWN])
                    continue  # 输入已处理，跳过其他处理
            
            # 然后尝试属性界面的键盘处理
            if hasattr(interface, "_process_keyboard_event") and interface._process_keyboard_event(e):
                pygame.event.clear([KEYDOWN])
                continue
                
            if interface.shortcut_mode:
                _execute_order_shortcut(interface, e)
                interface.shortcut_mode = False
            else:
                # L/R Shift+C copy; L/R Shift+B append (primary / secondary)
                try:
                    from pygame.locals import K_b, K_c
                    from ..lib import voice_libs

                    key = e.key
                    if key in (ord("C"), ord("B")):
                        key = ord(chr(key).lower())
                    if (
                        (e.mod & KMOD_SHIFT)
                        and not (e.mod & KMOD_CTRL)
                        and key in (K_b, K_c)
                        and voice_libs.handle_hotkey(key, e.mod)
                    ):
                        pygame.event.clear([KEYDOWN])
                        continue
                except Exception:
                    pass
                try:
                    interface._bindings.process_keydown_event(e)
                except KeyError:
                    voice.item(mp.BEEP)
            # 处理可能很慢（作弊全图 + 大地图 select_square / TTS）。
            # 清掉处理期间 key-repeat 再塞进队列的 KEYDOWN，否则下一帧
            # 会连续跳多格。与 Menu._process_keydown 同模式。
            pygame.event.clear([KEYDOWN])
        elif interface.display_is_active:
            _process_fullscreen_mode_mouse_event(interface, e)
'''


def sync_one(root: Path) -> None:
    # --- base.py: insert set_neutral before set_ai ---
    patch(
        root,
        "soundrts/worldplayerbase/base.py",
        "    def set_ai(self, ai_type):\n        pass\n",
        SET_NEUTRAL_METHOD.lstrip("\n"),
        "base-set_neutral",
    )

    # --- triggers.py ---
    patch(
        root,
        "soundrts/worldplayerbase/triggers.py",
        LANG_SET_AI_OLD,
        LANG_SET_AI_NEW,
        "triggers-set_ai_mode+set_neutral",
    )
    patch(
        root,
        "soundrts/worldplayerbase/triggers.py",
        LANG_COUNTER_INSERT_AFTER,
        LANG_COUNTER_BLOCK,
        "triggers-set_counterattack",
    )

    # --- game_input_handler.py ---
    patch(
        root,
        "soundrts/clientgame/game_input_handler.py",
        "_MOUSE_CLICK_TOLERANCE_PX = 5\n\n\ndef _mouse_is_click(",
        "_MOUSE_CLICK_TOLERANCE_PX = 5\n\n" + COLLAPSE_HELPER + "def _mouse_is_click(",
        "input-collapse-helper",
    )
    patch(
        root,
        "soundrts/clientgame/game_input_handler.py",
        PROCESS_EVENTS_OLD,
        PROCESS_EVENTS_NEW,
        "input-process-events-clear",
    )
    patch(
        root,
        "soundrts/clientgame/game_input_handler.py",
        "__all__ = [\n    '_process_events',",
        "__all__ = [\n    '_collapse_keydown_repeats',\n    '_process_events',",
        "input-__all__",
    )

    # --- tests ---
    patch(
        root,
        "soundrts/tests/test_campaign_alliance_transfer_triggers.py",
        '''def test_lang_set_ai_mode_on_selected_units():
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
''',
        '''def test_lang_set_ai_mode_on_selected_units():
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


def test_lang_set_ai_mode_offensive_clears_neutral():
    """决斗开局：set_ai_mode offensive 必须解除中立，否则玩家不会自动攻击。"""
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    computer.neutral = True
    world = _StubWorld([human, computer])
    world.update_alliances()
    roland = _StubUnit(computer, type_name="npc_count_roland", unit_id="r1")
    roland.ai_mode = "guard"
    t = _make_triggers(computer, world)
    t.lang_set_ai_mode(["offensive"])
    assert roland.ai_mode == "offensive"
    assert computer.neutral is False


def test_lang_set_neutral_toggles_flag():
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    computer.neutral = True
    world = _StubWorld([computer])
    t = _make_triggers(computer, world)
    t.lang_set_neutral([0])
    assert computer.neutral is False
    t.lang_set_neutral([1])
    assert computer.neutral is True


def test_lang_set_neutral_on_other_player_restores_guard():
    """拒绝结盟后：玩家触发器可对 computer1 执行 set_neutral 1，并恢复 guard。"""
    human = _TriggerOwner(is_human=True, player_id="h1", name="Player 1")
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Knight Lord")
    computer.neutral = False
    world = _StubWorld([human, computer])
    roland = _StubUnit(computer, type_name="npc_count_roland", unit_id="r1")
    brother = _StubUnit(computer, type_name="npc_roland_guard", unit_id="b1")
    roland.ai_mode = "offensive"
    brother.ai_mode = "offensive"
    roland.counterattack_enabled = False
    brother.counterattack_enabled = False
    t = _make_triggers(human, world)
    t.lang_set_neutral([1, "computer1"])
    assert computer.neutral is True
    assert human.neutral is False
    assert roland.ai_mode == "guard"
    assert brother.ai_mode == "guard"
    assert roland.counterattack_enabled is True
    assert brother.counterattack_enabled is True


def test_lang_set_yield_on_defeat_on_selected_units():
''',
        "tests-set_neutral-helpers",
    )

    patch(
        root,
        "soundrts/tests/test_campaign_alliance_transfer_triggers.py",
        '''    assert "(set_ai_mode offensive o8 1 npc_marco_ironhand)" in text
    assert "(order (o8 8 npc_knight_escort) ((go o1)))" in text
    assert "(order (o8 8 npc_footman_escort) ((go o1)))" in text
    assert "(order (o8 8 npc_archer_escort) ((go o1)))" in text
    assert "(set_map_flag ch27_escorts_return)" in text
    assert "(order (o1 8 npc_knight_escort) ((go o8)))" in text
    assert "(order (o1 8 npc_footman_escort) ((go o8)))" in text
    assert "(order (o1 8 npc_archer_escort) ((go o8)))" in text


def test_script_npc_name_is_npc_not_ai_timers_login():
''',
        '''    assert "(set_ai_mode offensive o8 1 npc_marco_ironhand)" in text
    assert "(set_counterattack 0 o8 12 npc_knight_escort o8 12 npc_footman_escort o8 12 npc_archer_escort)" in text
    assert "(order (o8 12 npc_knight_escort) ((imperative go o1)))" in text
    assert "(order (o8 12 npc_footman_escort) ((imperative go o1)))" in text
    assert "(order (o8 12 npc_archer_escort) ((imperative go o1)))" in text
    assert "(set_map_flag ch27_escorts_return)" in text
    assert "(order (o1 12 npc_knight_escort) ((go o8)))" in text
    assert "(order (o1 12 npc_footman_escort) ((go o8)))" in text
    assert "(order (o1 12 npc_archer_escort) ((go o8)))" in text
    duel = [
        line
        for line in text.splitlines()
        if "set_ai_mode offensive o8 1 npc_marco_ironhand" in line
    ][0]
    assert duel.index("set_counterattack 0") < duel.index("set_ai_mode offensive")
    assert duel.index("set_counterattack 0") < duel.index("imperative go o1")


def test_lang_set_counterattack_disables_and_clears_attacker():
    computer = _TriggerOwner(is_human=False, player_id="ai1", name="Marco")
    world = _StubWorld([computer])
    escort = _StubUnit(computer, type_name="npc_knight_escort", unit_id="e1")
    escort.counterattack_enabled = True
    escort.last_attacker = object()
    escort.action_target = object()
    t = _make_triggers(computer, world)
    t.lang_set_counterattack(["0"])
    assert escort.counterattack_enabled is False
    assert escort.last_attacker is None
    assert escort.action_target is None
    t.lang_set_counterattack(["1"])
    assert escort.counterattack_enabled is True


def test_script_npc_name_is_npc_not_ai_timers_login():
''',
        "tests-ch27-counterattack",
    )

    patch(
        root,
        "soundrts/tests/test_campaign_alliance_transfer_triggers.py",
        '''    assert "(npc_has_item npc_count_roland garrek_token o8)" in text
    assert "(set_ai_mode offensive o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_yield_on_defeat 1 o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_campaign_flag ch25_duel_started)" in text
    assert "trigger players (npc_has_item npc_count_roland garrek_token o8) (do (cut_scene 7701)" in text
    assert "(set_campaign_flag ch25_duel_started))" in text.split("(cut_scene 7701)")[1].split("trigger computer1")[0]
    assert "trigger computer1 (npc_has_item npc_count_roland garrek_token o8) (do (set_ai_mode offensive" in text
''',
        '''    assert "(npc_has_item npc_count_roland garrek_token o8)" in text
    assert "(set_neutral 0)" in text
    assert "(set_ai_mode offensive o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_yield_on_defeat 1 o8 1 npc_count_roland 6 npc_roland_guard)" in text
    assert "(set_campaign_flag ch25_duel_started)" in text
    assert "trigger players (npc_has_item npc_count_roland garrek_token o8) (do (cut_scene 7701)" in text
    assert "(set_campaign_flag ch25_duel_started))" in text.split("(cut_scene 7701)")[1].split("trigger computer1")[0]
    assert "trigger computer1 (npc_has_item npc_count_roland garrek_token o8) (do (set_neutral 0) (set_ai_mode offensive" in text
''',
        "tests-ch25-set_neutral-0",
    )

    patch(
        root,
        "soundrts/tests/test_campaign_alliance_transfer_triggers.py",
        '''    assert "(alliance_declined_with computer1)" in text
    assert "(add_units h8 6 knight)" in text
    assert "(set_campaign_flag ch25_roland_allied)" in text
    assert "(set_campaign_flag ch25_roland_knights)" in text
    assert "(campaign_flag ch24_garrek)" in text
''',
        '''    assert "(alliance_declined_with computer1)" in text
    assert "(set_neutral 1 computer1)" in text
    assert "(add_units h8 6 knight)" in text
    assert "(set_campaign_flag ch25_roland_allied)" in text
    assert "(set_campaign_flag ch25_roland_knights)" in text
    declined = text.split("alliance_declined_with computer1")[1].split("trigger")[0]
    assert "(set_neutral 1 computer1)" in declined
    assert "(stop_all_units)" in declined
    assert "(stop_all_units computer1)" in declined
    assert "(campaign_flag ch24_garrek)" in text
''',
        "tests-ch25-decline-neutral",
    )

    patch(
        root,
        "soundrts/tests/test_neutral_no_auto_attack.py",
        '''def test_player_is_a_hostile_enemy_excludes_neutral():
    human = _CombatPlayer(neutral=False)
    neutral = _CombatPlayer(neutral=True)
    human.allied = [human]

    assert human.player_is_an_enemy(neutral) is True
    assert human.player_is_a_hostile_enemy(neutral) is False
    assert human.player_is_a_hostile_enemy(human) is False


def test_can_attack_refuses_neutral_without_imperative_order():
''',
        '''def test_player_is_a_hostile_enemy_excludes_neutral():
    human = _CombatPlayer(neutral=False)
    neutral = _CombatPlayer(neutral=True)
    human.allied = [human]

    assert human.player_is_an_enemy(neutral) is True
    assert human.player_is_a_hostile_enemy(neutral) is False
    assert human.player_is_a_hostile_enemy(human) is False


def test_clearing_neutral_makes_hostile_enemy():
    """决斗开局清掉 neutral 后，玩家战斗 AI 应把对方当作可自动攻击的敌对目标。"""
    human = _CombatPlayer(neutral=False)
    duel_npc = _CombatPlayer(neutral=True)
    human.allied = [human]
    duel_npc.id = "ai1"

    assert human.player_is_a_hostile_enemy(duel_npc) is False
    duel_npc.neutral = False
    assert human.player_is_a_hostile_enemy(duel_npc) is True


def test_can_attack_refuses_neutral_without_imperative_order():
''',
        "tests-clearing-neutral-hostile",
    )

    patch(
        root,
        "soundrts/tests/test_yield_on_defeat_and_campaign_flags.py",
        '    assert "set_ai_mode offensive" in ch25\n    assert "set_yield_on_defeat 1" in ch25\n',
        '    assert "set_neutral 0" in ch25\n    assert "set_ai_mode offensive" in ch25\n    assert "set_yield_on_defeat 1" in ch25\n',
        "tests-yield-ch25-set_neutral",
    )

    ensure_new(root, "soundrts/tests/test_game_keydown_repeat_collapse.py")
    ensure_new(root, "res/single/The Legend of Raynor/25.txt")
    ensure_new(root, "res/single/The Legend of Raynor/27.txt")


def main() -> None:
    for root in TARGETS:
        sync_one(root)
    patch_docs_fix8_only()
    out = MAIN / "tools" / "_sync_session_neutral_keydown_fix8_fix14_log.txt"
    out.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("\n".join(LOG))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
