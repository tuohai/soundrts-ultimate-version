"""帝国时代决定版风格合作战役：难度系统的唯一数据源。

设计目标
========
把"合作战役"改造成《帝国时代2/3 决定版》那样的多人战役体验，难度是其
核心一环：

* 玩家在创建合作战役时可选 5 档难度（简单 / 标准 / 中等 / 困难 / 极难），
  与决定版一致：越难，敌人越强。
* 与决定版相同，敌人强度还会**随参战玩家人数增加而提升**（人多 → 敌人更猛），
  这样 3、4 个人一起打不会被原本为 1 人设计的关卡碾过去。

确定性约束（非常重要）
======================
本引擎是 lockstep 同步：多人对局、旁观、回放都靠"相同 seed + 相同世界设置 +
相同 orders"在各端各自重建出完全一致的世界。因此难度系数必须：

* 全程使用**整数百分比**与整数运算（``x * pct // 100``），不引入浮点，
  避免各平台浮点误差导致的不同步；
* 由服务器在开局时**一次性算定**最终百分比（已包含玩家人数缩放），再分发给
  所有客户端 / 旁观者，并写入回放头，保证唯一数据源、各端一致。

百分比含义
==========
``enemy_hp`` / ``enemy_damage`` 是"敌方（非人类且非中立）单位"的生命与输出
伤害相对标准值的百分比。100 表示原版强度（标准难度、单人）。
"""
from __future__ import annotations

from typing import Tuple

# 难度等级标识（内部 key，跨网络传输用 ASCII，避免编码问题）。
EASY = "easy"
STANDARD = "standard"
MODERATE = "moderate"
HARD = "hard"
EXTREME = "extreme"

# 菜单展示顺序。
LEVELS = (EASY, STANDARD, MODERATE, HARD, EXTREME)

# 默认难度：标准（与不传难度时的行为一致，敌人 100%）。
DEFAULT_LEVEL = STANDARD

# 每档难度的基础敌人强度百分比 (enemy_hp_percent, enemy_damage_percent)。
# 标准 = 100/100（不改变原版关卡平衡）。
_BASE: dict[str, Tuple[int, int]] = {
    EASY: (70, 70),
    STANDARD: (100, 100),
    MODERATE: (120, 115),
    HARD: (145, 135),
    EXTREME: (180, 165),
}

# 每多一名人类玩家，敌人额外增强的百分点（与决定版"敌人随人数变强"一致）。
PER_EXTRA_PLAYER_BONUS = 20


def normalize_level(level) -> str:
    """把任意输入规整为合法难度 key；无法识别时回退到标准。"""
    if isinstance(level, str):
        key = level.strip().lower()
        if key in _BASE:
            return key
    return DEFAULT_LEVEL


def player_count_multiplier(nb_human_players: int) -> int:
    """返回随人数缩放的整数百分比乘子（单人=100）。"""
    try:
        n = int(nb_human_players)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    return 100 + (n - 1) * PER_EXTRA_PLAYER_BONUS


def factors(level, nb_human_players: int = 1) -> Tuple[int, int]:
    """计算最终敌人 (hp_percent, damage_percent)，已含玩家人数缩放。

    全整数运算，确定性安全。标准难度 + 单人 → (100, 100)。
    """
    base_hp, base_dmg = _BASE[normalize_level(level)]
    mult = player_count_multiplier(nb_human_players)
    hp = max(1, base_hp * mult // 100)
    dmg = max(1, base_dmg * mult // 100)
    return hp, dmg


def label(level):
    """返回该难度在菜单里使用的语音消息常量（msgparts 列表）。"""
    from . import msgparts as mp

    return {
        EASY: mp.DIFFICULTY_EASY,
        STANDARD: mp.DIFFICULTY_STANDARD,
        MODERATE: mp.DIFFICULTY_MODERATE,
        HARD: mp.DIFFICULTY_HARD,
        EXTREME: mp.DIFFICULTY_EXTREME,
    }[normalize_level(level)]
