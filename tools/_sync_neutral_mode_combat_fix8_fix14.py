# -*- coding: utf-8 -*-
"""Incremental sync: mode→hostile + hit→hostile → 修复8 & 修复14."""
from __future__ import annotations

from pathlib import Path

MAIN = Path(r"C:\Users\Administrator\Desktop\soundrts1.3.8.1项目\soundrts-1.4.5.1")
TARGETS = [Path(r"E:\代码\修复8"), Path(r"E:\代码\修复14")]
LOG: list[str] = []

ON_MODE = '''
    def on_unit_ai_mode_changed(self, mode):
        """中立与站岗绑定：离开站岗进入主动 AI 时解除中立。

        ``computer_only ... neutral`` 开局为 guard + 反击的被动 creep。
        一旦切到 ``offensive`` / ``defensive`` / ``chase``（UI 或
        ``set_ai_mode``），清掉 ``neutral`` 变为正式敌对，避免「会打你
        但仍显示中立、己方不自动交战」。纯野生动物电脑保持中立。
        """
        if mode not in ("offensive", "defensive", "chase"):
            return
        if not getattr(self, "neutral", False):
            return
        if player_is_wildlife_only(self):
            return
        self.set_neutral(False)

    def note_combat_with(self, other_player):
        """本方单位遭到非中立势力攻击时，解除中立。

        与切 AI 模式解中立互补：站岗中立 creep 被打后应变为正式敌对，
        以便对方自动交战与「中立」标注一致。主动出手不改中立。
        纯野生动物电脑保持中立。
        """
        if other_player is None or other_player is self:
            return
        if not getattr(self, "neutral", False):
            return
        if getattr(other_player, "neutral", False):
            return
        if player_is_wildlife_only(self):
            return
        self.set_neutral(False)

'''


def patch(root: Path, rel: str, old: str, new: str, name: str) -> None:
    p = root / rel
    if not p.exists():
        LOG.append(f"FAIL missing-file {root.name}:{name}")
        return
    t = p.read_text(encoding="utf-8")
    if old not in t:
        if new and (new in t or new.strip()[:60] in t):
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


def sync_one(root: Path) -> None:
    # --- base.py: insert methods before set_neutral + refresh docstring ---
    patch(
        root,
        "soundrts/worldplayerbase/base.py",
        "    def set_neutral(self, value):\n"
        '        """设置/清除中立标记，并立刻失效各玩家的敌对目标缓存。\n\n'
        "        ``computer_only ... neutral`` 开局的中立电脑在进入正式交战\n"
        "        （例如决斗触发 ``set_ai_mode offensive`` / ``set_neutral 0``）后\n"
        "        必须清掉 ``neutral``，否则玩家单位的自动攻击会继续忽略他们\n"
        "        （``player_is_a_hostile_enemy`` / ``can_attack`` 排除中立）。\n",
        ON_MODE
        + "    def set_neutral(self, value):\n"
        '        """设置/清除中立标记，并立刻失效各玩家的敌对目标缓存。\n\n'
        "        ``computer_only ... neutral`` 开局的中立电脑在进入正式交战\n"
        "        （挨打 ``note_combat_with``、切非站岗模式、或地图 ``set_neutral 0``）后\n"
        "        必须清掉 ``neutral``，否则玩家单位的自动攻击会继续忽略他们\n"
        "        （``player_is_a_hostile_enemy`` / ``can_attack`` 排除中立）。\n",
        "base-on_mode+note_combat",
    )

    # --- triggers: lang_set_ai_mode uses on_unit_ai_mode_changed ---
    patch(
        root,
        "soundrts/worldplayerbase/triggers.py",
        "        当模式为 ``offensive`` 且本玩家仍是中立非野生动物电脑时，会自动\n"
        "        ``set_neutral 0``：否则单位虽会主动进攻，玩家侧自动攻击仍会忽略他们。\n"
        '        """\n'
        "        if not args:\n"
        "            return\n"
        "        mode = str(args[0])\n"
        '        if mode not in ("offensive", "defensive", "guard", "chase"):\n'
        '            warning("set_ai_mode: unknown mode %s", mode)\n'
        "            return\n"
        "        if len(args) == 1:\n"
        "            targets = [\n"
        '                u for u in self.units if getattr(u, "presence", True)\n'
        "            ]\n"
        "        else:\n"
        "            targets = self._units(args[1:])\n"
        "        for u in targets:\n"
        "            u.ai_mode = mode\n"
        '        if mode == "offensive" and getattr(self, "neutral", False):\n'
        "            from .base import player_is_wildlife_only\n\n"
        "            if not player_is_wildlife_only(self):\n"
        "                self.lang_set_neutral([0])\n",
        "        当模式为 ``offensive`` / ``defensive`` / ``chase`` 且本玩家仍是\n"
        "        中立非野生动物电脑时，会自动 ``set_neutral 0``：否则单位虽会主动\n"
        "        出击，玩家侧仍显示中立且自动攻击会忽略他们。\n"
        '        """\n'
        "        if not args:\n"
        "            return\n"
        "        mode = str(args[0])\n"
        '        if mode not in ("offensive", "defensive", "guard", "chase"):\n'
        '            warning("set_ai_mode: unknown mode %s", mode)\n'
        "            return\n"
        "        if len(args) == 1:\n"
        "            targets = [\n"
        '                u for u in self.units if getattr(u, "presence", True)\n'
        "            ]\n"
        "        else:\n"
        "            targets = self._units(args[1:])\n"
        "        for u in targets:\n"
        "            u.ai_mode = mode\n"
        '        if targets and hasattr(self, "on_unit_ai_mode_changed"):\n'
        "            self.on_unit_ai_mode_changed(mode)\n",
        "triggers-set_ai_mode-on_unit_ai_mode_changed",
    )

    patch(
        root,
        "soundrts/worldplayerbase/triggers.py",
        "        ``set_ai_mode offensive`` 本身也会自动对非野生动物电脑清中立。\n"
        '        """\n',
        "        ``set_ai_mode`` 切到非站岗模式、以及中立单位遭到非中立攻击时，\n"
        "        也会自动对非野生动物电脑清中立。\n"
        '        """\n',
        "triggers-set_neutral-doc",
    )

    # --- immediate.py: _apply_unit_ai_mode + Mode* ---
    patch(
        root,
        "soundrts/worldorders/immediate.py",
        'class ModeOffensive(ImmediateOrder):\n'
        '    keyword = "mode_offensive"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "chase")\n\n'
        "    def immediate_action(self):\n"
        '        self.unit.ai_mode = "offensive"\n'
        '        self.unit.notify("order_ok")\n\n\n'
        "class ModeDefensive(ImmediateOrder):\n"
        '    keyword = "mode_defensive"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "offensive")\n\n'
        "    def immediate_action(self):\n"
        '        self.unit.ai_mode = "defensive"\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeGuard(ImmediateOrder):\n"
        '    keyword = "mode_guard"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "defensive")\n'
        "        \n"
        "    def immediate_action(self):\n"
        '        self.unit.ai_mode = "guard"\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeChase(ImmediateOrder):\n"
        '    keyword = "mode_chase"\n'
        "    \n"
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "guard")\n'
        "        \n"
        "    def immediate_action(self):\n"
        '        self.unit.ai_mode = "chase"\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeToggle(ImmediateOrder):\n"
        '    """切换 AI 模式的命令"""\n'
        '    keyword = "toggle_ai_mode"\n'
        "    nb_args = 0\n"
        "    population_cost = 0\n\n"
        "    @classmethod\n"
        "    def menu(cls, unit, strict=False):\n"
        "        if cls.is_allowed(unit):\n"
        "            next_mode = {\n"
        '                "offensive": "defensive",\n'
        '                "defensive": "guard",\n'
        '                "guard": "chase",\n'
        '                "chase": "offensive"\n'
        "            }[unit.ai_mode]\n"
        '            return [f"mode_{next_mode}"]\n'
        "        return []\n\n"
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        "        return unit.can_switch_ai_mode\n\n"
        "    def immediate_action(self):\n"
        "        next_mode = {\n"
        '            "offensive": "defensive",\n'
        '            "defensive": "guard",\n'
        '            "guard": "chase",\n'
        '            "chase": "offensive"\n'
        "        }[self.unit.ai_mode]\n"
        "        self.unit.ai_mode = next_mode\n"
        '        self.unit.notify("order_ok")\n',
        'def _apply_unit_ai_mode(unit, mode):\n'
        '    """设置单位 AI 模式；离开站岗时中立非野生电脑解除中立。"""\n'
        "    unit.ai_mode = mode\n"
        '    player = getattr(unit, "player", None)\n'
        '    if player is not None and hasattr(player, "on_unit_ai_mode_changed"):\n'
        "        player.on_unit_ai_mode_changed(mode)\n\n\n"
        "class ModeOffensive(ImmediateOrder):\n"
        '    keyword = "mode_offensive"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "chase")\n\n'
        "    def immediate_action(self):\n"
        '        _apply_unit_ai_mode(self.unit, "offensive")\n'
        '        self.unit.notify("order_ok")\n\n\n'
        "class ModeDefensive(ImmediateOrder):\n"
        '    keyword = "mode_defensive"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "offensive")\n\n'
        "    def immediate_action(self):\n"
        '        _apply_unit_ai_mode(self.unit, "defensive")\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeGuard(ImmediateOrder):\n"
        '    keyword = "mode_guard"\n\n'
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "defensive")\n'
        "        \n"
        "    def immediate_action(self):\n"
        '        _apply_unit_ai_mode(self.unit, "guard")\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeChase(ImmediateOrder):\n"
        '    keyword = "mode_chase"\n'
        "    \n"
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        '        return unit.can_switch_ai_mode and (unit.ai_mode == "guard")\n'
        "        \n"
        "    def immediate_action(self):\n"
        '        _apply_unit_ai_mode(self.unit, "chase")\n'
        '        self.unit.notify("order_ok")\n\n'
        "class ModeToggle(ImmediateOrder):\n"
        '    """切换 AI 模式的命令"""\n'
        '    keyword = "toggle_ai_mode"\n'
        "    nb_args = 0\n"
        "    population_cost = 0\n\n"
        "    @classmethod\n"
        "    def menu(cls, unit, strict=False):\n"
        "        if cls.is_allowed(unit):\n"
        "            next_mode = {\n"
        '                "offensive": "defensive",\n'
        '                "defensive": "guard",\n'
        '                "guard": "chase",\n'
        '                "chase": "offensive"\n'
        "            }[unit.ai_mode]\n"
        '            return [f"mode_{next_mode}"]\n'
        "        return []\n\n"
        "    @classmethod\n"
        "    def is_allowed(cls, unit, *unused_args):\n"
        "        return unit.can_switch_ai_mode\n\n"
        "    def immediate_action(self):\n"
        "        next_mode = {\n"
        '            "offensive": "defensive",\n'
        '            "defensive": "guard",\n'
        '            "guard": "chase",\n'
        '            "chase": "offensive"\n'
        "        }[self.unit.ai_mode]\n"
        "        _apply_unit_ai_mode(self.unit, next_mode)\n"
        '        self.unit.notify("order_ok")\n',
        "immediate-apply_unit_ai_mode",
    )

    # --- world_ai_decision toggle ---
    patch(
        root,
        "soundrts/worldunit/world_ai_decision.py",
        "        modes = [\"offensive\", \"defensive\", \"guard\", \"chase\"]\n"
        "        current_index = modes.index(self.ai_mode)\n"
        "        next_index = (current_index + 1) % len(modes)\n"
        "        self.ai_mode = modes[next_index]\n"
        '        self.notify("order_ok")\n',
        "        modes = [\"offensive\", \"defensive\", \"guard\", \"chase\"]\n"
        "        current_index = modes.index(self.ai_mode)\n"
        "        next_index = (current_index + 1) % len(modes)\n"
        "        next_mode = modes[next_index]\n"
        "        self.ai_mode = next_mode\n"
        '        player = getattr(self, "player", None)\n'
        '        if player is not None and hasattr(player, "on_unit_ai_mode_changed"):\n'
        "            player.on_unit_ai_mode_changed(next_mode)\n"
        '        self.notify("order_ok")\n',
        "ai-toggle-on_unit_ai_mode_changed",
    )

    # --- damage_effects ---
    patch(
        root,
        "soundrts/combat/damage_effects.py",
        "            self.last_attacker = attacker\n\n"
        "            # 通知友军单位（仅当攻击者存在时）\n"
        "            if self.place:\n"
        "                self._notify_guard_units(attacker)\n",
        "            self.last_attacker = attacker\n\n"
        "            # 中立 creep 遭到非中立攻击 → 解除中立（野生动物除外）\n"
        '            attacker_player = getattr(attacker, "player", None)\n'
        "            victim_player = self.player\n"
        '            if hasattr(victim_player, "note_combat_with"):\n'
        "                victim_player.note_combat_with(attacker_player)\n\n"
        "            # 通知友军单位（仅当攻击者存在时）\n"
        "            if self.place:\n"
        "                self._notify_guard_units(attacker)\n",
        "damage-note_combat_with",
    )

    # --- worldskill ---
    patch(
        root,
        "soundrts/worldskill.py",
        "        if victim.player:\n"
        "            victim.player.observe(caster)\n"
        "            victim.last_attacker = caster\n"
        "        victim.hp -= hp\n",
        "        if victim.player:\n"
        "            victim.player.observe(caster)\n"
        "            victim.last_attacker = caster\n"
        '            attacker_player = getattr(caster, "player", None)\n'
        '            if hasattr(victim.player, "note_combat_with"):\n'
        "                victim.player.note_combat_with(attacker_player)\n"
        "        victim.hp -= hp\n",
        "skill-note_combat_with",
    )

    # --- tests: stub helpers + new cases (copy whole test file sections from MAIN if present) ---
    test_rel = "soundrts/tests/test_campaign_alliance_transfer_triggers.py"
    main_test = (MAIN / test_rel).read_text(encoding="utf-8")
    dst = root / test_rel
    if dst.exists():
        # Prefer copying the MAIN test file for this module — it is the source of truth
        # for mode/combat neutral coverage and already includes prior alliance tests.
        # Only if sizes are wildly different would we worry; both trees got the prior sync.
        dst.write_text(main_test, encoding="utf-8")
        LOG.append(f"COPY {root.name}:{test_rel}")
    else:
        LOG.append(f"FAIL missing-file {root.name}:{test_rel}")

    # docs: fix8 only
    if root.name == "修复8" and (root / "doc_src").exists():
        for rel in (
            "doc_src/src/zh/player/unit-default-behavior.rst",
            "doc_src/src/en/player/unit-default-behavior.rst",
            "doc_src/src/zh/relnotes.rst",
            "doc_src/src/en/relnotes.rst",
        ):
            src = MAIN / rel
            dstp = root / rel
            if src.exists() and dstp.exists():
                dstp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                LOG.append(f"COPY {root.name}:{rel}")
            elif src.exists():
                dstp.parent.mkdir(parents=True, exist_ok=True)
                dstp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                LOG.append(f"NEW {root.name}:{rel}")
            else:
                LOG.append(f"SKIP no-src {rel}")


def main() -> None:
    for root in TARGETS:
        if not root.exists():
            LOG.append(f"FAIL missing-root {root}")
            continue
        sync_one(root)
    out = MAIN / "tools" / "_sync_neutral_mode_combat_fix8_fix14.log"
    text = "\n".join(LOG) + "\n"
    out.write_text(text, encoding="utf-8")
    print(text)
    bad = [x for x in LOG if x.startswith("FAIL")]
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
