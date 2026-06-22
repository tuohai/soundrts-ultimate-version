"""验证 rules.txt 可为不同单位设置开局默认 AI 模式（ai_mode）。

需求：在 rules.txt 中给单位写 ``ai_mode guard`` / ``ai_mode patrol`` 等，
决定该类型单位开局时使用的默认模式（offensive/defensive/guard/chase）。

实现要点：
* ``soundrts/definitions.py``：``ai_mode`` 注册为 string_properties，使
  ``ai_mode guard`` 被解析为字符串并成为生成单位类的类属性。
* ``soundrts/worldunit/worldcreature.py``：``Creature.__init__`` 不再硬编码
  ``offensive``，而是经 ``_resolve_default_ai_mode`` 读取类属性（即 rules
  里定义的值），非法值回退默认并告警。
* ``soundrts/worldunit/worldworker.py``：同样尊重 rules 定义，缺省回退
  ``defensive``。
"""
from __future__ import annotations

import soundrts.worldunit  # noqa: F401  解开 worldunit 包循环导入

from soundrts.definitions import Rules
from soundrts.worldunit.worldcreature import Creature, VALID_AI_MODES
from soundrts.worldunit.worldworker import Worker


def test_ai_mode_registered_as_string_property():
    assert "ai_mode" in Rules.string_properties


def test_rules_parse_ai_mode_value():
    r = Rules()
    r.read(
        """
def knight
class soldier
ai_mode guard
"""
    )
    assert r.get("knight", "ai_mode") == "guard"


def _load_rules(extra):
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def soldier
class soldier
"""
        + extra
    )
    return r


def test_generated_class_carries_rules_ai_mode():
    """rules 里 ``ai_mode guard`` 应成为生成单位类的类属性。"""
    r = _load_rules(
        """
def knight
class soldier
ai_mode guard
"""
    )
    knight = r.unit_class("knight")
    assert knight is not None
    assert knight.ai_mode == "guard"


def test_resolve_default_ai_mode_uses_class_value():
    """实例化路径上的 _resolve_default_ai_mode 应返回 rules 定义的合法模式。"""
    u = Creature.__new__(Creature)
    type(u).ai_mode  # sanity: 类有该属性

    class _Knight(Creature):
        ai_mode = "guard"

    k = _Knight.__new__(_Knight)
    assert k._resolve_default_ai_mode("offensive") == "guard"


def test_resolve_default_ai_mode_invalid_falls_back():
    class _Weird(Creature):
        ai_mode = "patrolling_nonsense"

    w = _Weird.__new__(_Weird)
    assert w._resolve_default_ai_mode("offensive") == "offensive"


def test_resolve_default_ai_mode_none_falls_back():
    class _Bare(Creature):
        ai_mode = None

    b = _Bare.__new__(_Bare)
    assert b._resolve_default_ai_mode("offensive") == "offensive"


def test_all_valid_modes_accepted():
    for mode in VALID_AI_MODES:
        class _U(Creature):
            pass
        _U.ai_mode = mode
        u = _U.__new__(_U)
        assert u._resolve_default_ai_mode("offensive") == mode


def test_worker_respects_rules_ai_mode():
    """工人若在 rules 定义了合法 ai_mode，则尊重之；否则回退 defensive。"""
    class _Peasant(Worker):
        ai_mode = "guard"

    p = _Peasant.__new__(_Peasant)
    assert p._resolve_default_ai_mode("defensive") == "guard"

    class _DefaultWorker(Worker):
        pass

    dw = _DefaultWorker.__new__(_DefaultWorker)
    # Worker 类默认 ai_mode = "defensive"
    assert dw._resolve_default_ai_mode("defensive") == "defensive"
