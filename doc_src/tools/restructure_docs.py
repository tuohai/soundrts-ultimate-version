#!/usr/bin/env python3
"""One-time restructure: doc_src/src/{lang}/player/ and mod/."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "doc_src" / "src"

# (old relative to lang, new relative to lang)
ZH_PLAYER_MOVES = {
    "guides/player/入门指南.rst": "player/getting-started.rst",
    "guides/player/分层热键方案说明.rst": "player/layered-hotkeys.rst",
    "guides/player/单位默认模式与自动状态配置说明.rst": "player/unit-default-behavior.rst",
    "guides/player/achievements.rst": "player/achievements.rst",
    "guides/player/score-and-grades.rst": "player/score-and-grades.rst",
    "guides/player/loadout-cards.rst": "player/loadout-cards.rst",
    "guides/player/战役与合作战役改进说明.rst": "player/campaign-menu.rst",
    "guides/player/战役密信与结盟说明.rst": "player/campaign-northern-arc.rst",
    "guides/player/随机地图功能说明.rst": "player/random-map-play.rst",
    "guides/player/背包与装备栏功能说明.rst": "player/inventory.rst",
    "guides/player/狩猎系统说明.rst": "player/hunting.rst",
    "guides/player/连发攻击与诸葛弩说明.rst": "player/burst-attacks.rst",
    "guides/player/携带物品与剧情交付说明.rst": "player/brought-items.rst",
    "guides/player/英雄无敌与文明5玩法说明.rst": "player/homm-civ5-play.rst",
    "guides/player/星际资源与气矿说明.rst": "player/starcraft-resources.rst",
    "guides/player/星际人族附属建筑与重组说明.rst": "player/starcraft-terran.rst",
    "guides/player/星际异虫菌毯说明.rst": "player/starcraft-zerg-creep.rst",
    "manual.rst": "player/manual.rst",
}

ZH_MOD_MOVES = {
    "guides/mod/入门指南.rst": "mod/getting-started.rst",
    "modding.rst": "mod/modding.rst",
    "mapmaking.rst": "mod/mapmaking.rst",
    "aimaking.rst": "mod/aimaking.rst",
    "randommap.rst": "mod/randommap.rst",
    "server.rst": "mod/server.rst",
    "skills-and-effects.rst": "mod/skills-and-effects.rst",
    "guides/mod/mod-i18n.rst": "mod/mod-i18n.rst",
    "guides/mod/hotkey-mapping-editor.rst": "mod/hotkey-mapping-editor.rst",
    "guides/mod/achievement-system.rst": "mod/achievement-system.rst",
    "guides/mod/score-grading-system.rst": "mod/score-grading-system.rst",
    "guides/mod/delayed-card-loadout.rst": "mod/delayed-card-loadout.rst",
    "guides/mod/寻找物品通关说明.rst": "mod/campaign/find-item.rst",
    "guides/mod/给NPC物品功能说明.rst": "mod/campaign/give-to-npc.rst",
    "guides/mod/指定序号目标说明.rst": "mod/campaign/unit-index.rst",
    "guides/mod/渐进式战役目标说明.rst": "mod/campaign/progressive-objectives.rst",
    "guides/mod/战役跨章英雄携带说明.rst": "mod/campaign/hero-carryover.rst",
    "guides/mod/coop-campaign.rst": "mod/campaign/coop.rst",
}

EN_PLAYER_MOVES = {
    "guides/player/getting-started.rst": "player/getting-started.rst",
    "guides/player/layered-hotkeys.rst": "player/layered-hotkeys.rst",
    "guides/player/unit-default-behavior.rst": "player/unit-default-behavior.rst",
    "guides/player/achievements.rst": "player/achievements.rst",
    "guides/player/score-and-grades.rst": "player/score-and-grades.rst",
    "guides/player/loadout-cards.rst": "player/loadout-cards.rst",
    "guides/player/campaign-and-co-op-improvements.rst": "player/campaign-menu.rst",
    "guides/player/campaign-secret-letter-alliance.rst": "player/campaign-northern-arc.rst",
    "guides/player/random-map.rst": "player/random-map-play.rst",
    "guides/player/inventory-and-equipment.rst": "player/inventory.rst",
    "guides/player/hunting-system.rst": "player/hunting.rst",
    "guides/player/burst-attack-damage-seq.rst": "player/burst-attacks.rst",
    "guides/player/brought-item-delivery.rst": "player/brought-items.rst",
    "guides/player/starcraft-resources-vespene.rst": "player/starcraft-resources.rst",
    "guides/player/starcraft-terran-addons.rst": "player/starcraft-terran.rst",
    "guides/player/starcraft-zerg-creep.rst": "player/starcraft-zerg-creep.rst",
    "manual.rst": "player/manual.rst",
}

EN_MOD_MOVES = {
    "guides/mod/getting-started.rst": "mod/getting-started.rst",
    "modding.rst": "mod/modding.rst",
    "mapmaking.rst": "mod/mapmaking.rst",
    "aimaking.rst": "mod/aimaking.rst",
    "randommap.rst": "mod/randommap.rst",
    "server.rst": "mod/server.rst",
    "guides/mod/find-item-objective.rst": "mod/campaign/find-item.rst",
    "guides/mod/give-to-npc.rst": "mod/campaign/give-to-npc.rst",
    "guides/mod/map-unit-index-selectors.rst": "mod/campaign/unit-index.rst",
    "guides/mod/progressive-campaign-objectives.rst": "mod/campaign/progressive-objectives.rst",
    "guides/mod/campaign-hero-carryover.rst": "mod/campaign/hero-carryover.rst",
    "guides/mod/coop-campaign.rst": "mod/campaign/coop.rst",
    "guides/mod/hotkey-mapping-editor.rst": "mod/hotkey-mapping-editor.rst",
    "guides/mod/achievement-system.rst": "mod/achievement-system.rst",
    "guides/mod/score-grading-system.rst": "mod/score-grading-system.rst",
    "guides/mod/delayed-card-loadout.rst": "mod/delayed-card-loadout.rst",
}


def move_map(lang: str, moves: dict[str, str]) -> None:
    base = SRC / lang
    for old, new in moves.items():
        src = base / old
        dst = base / new
        if not src.is_file():
            print("skip missing", src)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))
        print(f"{lang}: {old} -> {new}")


def cleanup(lang: str) -> None:
    base = SRC / lang
    for name in ("player-guide.rst", "mod-author-guide.rst"):
        p = base / name
        if p.is_file():
            p.unlink()
            print("removed", p)
    guides = base / "guides"
    if guides.is_dir():
        shutil.rmtree(guides)
        print("removed", guides)


def main() -> None:
    move_map("zh", {**ZH_PLAYER_MOVES, **ZH_MOD_MOVES})
    move_map("en", {**EN_PLAYER_MOVES, **EN_MOD_MOVES})
    cleanup("zh")
    cleanup("en")
    print("done")


if __name__ == "__main__":
    main()
