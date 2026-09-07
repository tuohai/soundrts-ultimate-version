"""Campaign trigger script helpers: variables, loops, repeatable triggers.

Keeps integer-like values only (int, or int(float)) so clients stay deterministic.
"""

from __future__ import annotations

import re

from .lib.log import warning

DEFAULT_LOOP_LIMIT = 32
HARD_LOOP_CAP = 256
_VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OPS = ("==", "=", "!=", "<=", ">=", "<", ">")


def unpack_trigger(record):
    """Return (condition, action, meta_or_none) from a 2- or 3-item trigger record."""
    if not record:
        return None, None, None
    condition = record[0]
    action = record[1] if len(record) > 1 else None
    meta = record[2] if len(record) > 2 and isinstance(record[2], dict) else None
    return condition, action, meta


def parse_trigger_tree(tree):
    """Split a parsed trigger S-expression tree.

    ``trigger <owners> [repeat [seconds]] (condition) (action)``

    Returns (owners, condition, action, meta_or_none).
    ``meta`` is a new dict when ``repeat``/``every`` is present, else None.
    """
    if not isinstance(tree, list) or len(tree) < 3:
        raise ValueError("trigger needs owners, condition and action")
    action = tree[-1]
    condition = tree[-2]
    prefix = tree[:-2]
    if not prefix:
        raise ValueError("trigger missing owners")
    owners = prefix[0]
    meta = None
    i = 1
    while i < len(prefix):
        tok = prefix[i]
        if isinstance(tok, list):
            raise ValueError("unexpected nested list in trigger prefix")
        word = str(tok).lower()
        if word in ("repeat", "every"):
            if meta is None:
                meta = {
                    "repeat": True,
                    "cooldown": 0.0,
                    "was_true": False,
                    "next_ok": 0,
                }
            else:
                meta["repeat"] = True
            if i + 1 < len(prefix) and not isinstance(prefix[i + 1], list):
                nxt = str(prefix[i + 1])
                try:
                    meta["cooldown"] = float(nxt)
                    i += 2
                    continue
                except ValueError:
                    pass
            i += 1
            continue
        raise ValueError("unknown trigger modifier %s" % tok)
    return owners, condition, action, meta


def copy_trigger_record(condition, action, meta):
    if meta:
        return [condition, action, dict(meta)]
    return [condition, action]


def is_var_name(name) -> bool:
    return bool(name) and isinstance(name, str) and bool(_VAR_NAME.match(name))


def parse_script_number(token, default=0):
    if token is None:
        return default
    try:
        value = float(token)
    except (TypeError, ValueError):
        return default
    as_int = int(value)
    if as_int == value:
        return as_int
    return as_int


def compare_values(left, op, right) -> bool:
    if op in ("=", "=="):
        return left == right
    if op == "!=":
        return left != right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    return False


def loop_limit(world=None) -> int:
    n = DEFAULT_LOOP_LIMIT
    try:
        from .definitions import rules

        raw = rules.get("parameters", "trigger_loop_limit", DEFAULT_LOOP_LIMIT)
        if raw is not None:
            n = int(raw)
    except Exception:
        n = DEFAULT_LOOP_LIMIT
    if n < 1:
        n = 1
    if n > HARD_LOOP_CAP:
        n = HARD_LOOP_CAP
    return n


def _ensure_player_vars(player):
    bag = getattr(player, "_script_vars", None)
    if bag is None:
        bag = {}
        player._script_vars = bag
        _apply_parameter_defaults(bag, "trigger_var")
    return bag


def _ensure_world_vars(world):
    if world is None:
        return {}
    bag = getattr(world, "_script_globals", None)
    if bag is None:
        bag = {}
        world._script_globals = bag
        _apply_parameter_defaults(bag, "trigger_global")
    return bag


def _apply_parameter_defaults(bag, attr):
    try:
        from .definitions import rules

        raw = rules.get("parameters", attr, None)
    except Exception:
        return
    defaults = _as_name_value_map(raw)
    for name, value in defaults.items():
        bag.setdefault(name, value)


def _as_name_value_map(raw):
    out = {}
    if not raw:
        return out
    if isinstance(raw, dict):
        for key, value in raw.items():
            if is_var_name(str(key)):
                out[str(key)] = parse_script_number(value)
        return out
    if isinstance(raw, (list, tuple)):
        # "a 1 b 2" flattened, or [["a","1"], ...]
        if raw and isinstance(raw[0], (list, tuple)):
            for row in raw:
                if len(row) >= 2 and is_var_name(str(row[0])):
                    out[str(row[0])] = parse_script_number(row[1])
            return out
        i = 0
        while i + 1 < len(raw):
            name = str(raw[i])
            if is_var_name(name):
                out[name] = parse_script_number(raw[i + 1])
            i += 2
    return out


def get_var(player, name, default=0):
    if not is_var_name(name) or player is None:
        return default
    return _ensure_player_vars(player).get(name, default)


def set_var(player, name, value):
    if not is_var_name(name) or player is None:
        return
    _ensure_player_vars(player)[name] = parse_script_number(value)


def add_var(player, name, delta):
    if not is_var_name(name) or player is None:
        return
    bag = _ensure_player_vars(player)
    bag[name] = parse_script_number(bag.get(name, 0)) + parse_script_number(delta)


def get_global(world, name, default=0):
    if not is_var_name(name) or world is None:
        return default
    return _ensure_world_vars(world).get(name, default)


def set_global(world, name, value):
    if not is_var_name(name) or world is None:
        return
    _ensure_world_vars(world)[name] = parse_script_number(value)


def add_global(world, name, delta):
    if not is_var_name(name) or world is None:
        return
    bag = _ensure_world_vars(world)
    bag[name] = parse_script_number(bag.get(name, 0)) + parse_script_number(delta)


def eval_var_condition(player, world, args, is_global=False):
    """``(var name)`` nonzero, or ``(var name op number|var other)``."""
    if not args:
        return False
    name = str(args[0])
    current = get_global(world, name) if is_global else get_var(player, name)
    if len(args) == 1:
        return current != 0
    if len(args) < 3:
        return False
    op = str(args[1])
    if op not in _OPS:
        return False
    rhs_tok = args[2]
    if str(rhs_tok) == "var" and len(args) >= 4:
        other = str(args[3])
        right = get_global(world, other) if is_global else get_var(player, other)
    elif is_var_name(str(rhs_tok)) and not _looks_like_number(rhs_tok):
        right = get_global(world, str(rhs_tok)) if is_global else get_var(player, str(rhs_tok))
    else:
        right = parse_script_number(rhs_tok)
    return compare_values(current, op, right)


def _looks_like_number(token) -> bool:
    try:
        float(token)
        return True
    except (TypeError, ValueError):
        return False


def apply_var_effect(caster, world, op, name, value):
    """Skill / death-script bridge: set_var, add_var, set_global, add_global."""
    player = getattr(caster, "player", None) if caster is not None else None
    if op == "set_var":
        set_var(player, name, value)
        return True
    if op == "add_var":
        add_var(player, name, value)
        return True
    if op == "set_global":
        set_global(world, name, value)
        return True
    if op == "add_global":
        add_global(world, name, value)
        return True
    return False


def apply_on_death_script(unit, attacker=None):
    """Apply ``on_death_*_var`` / ``on_death_*_global`` from the unit type."""
    rows = getattr(unit, "on_death_script", None)
    if not rows:
        type_obj = getattr(unit, "type", None)
        rows = getattr(type_obj, "on_death_script", None) if type_obj is not None else None
    if not rows:
        return
    world = getattr(unit, "world", None)
    if world is None and attacker is not None:
        world = getattr(attacker, "world", None)
    var_player = None
    if attacker is not None:
        var_player = getattr(attacker, "player", None)
    if var_player is None:
        var_player = getattr(unit, "player", None)
    for row in rows:
        if not row or len(row) < 2:
            continue
        op = str(row[0])
        name = str(row[1])
        value = row[2] if len(row) > 2 else 1
        if op == "set_var":
            set_var(var_player, name, value)
        elif op == "add_var":
            add_var(var_player, name, value)
        elif op == "set_global":
            set_global(world, name, value)
        elif op == "add_global":
            add_global(world, name, value)


def should_fire_repeat(meta, cond_now, now_ms):
    """Update *meta* in place. True if the repeatable trigger should run now.

    No cooldown: rising edge (true after false).
    Cooldown > 0: fire while true, then wait ``cooldown`` seconds.
    """
    if not meta or not meta.get("repeat"):
        return False
    cooldown_ms = int(float(meta.get("cooldown") or 0) * 1000)
    next_ok = int(meta.get("next_ok") or 0)
    was_true = bool(meta.get("was_true"))
    if not cond_now:
        meta["was_true"] = False
        return False
    if now_ms < next_ok:
        return False
    if cooldown_ms > 0:
        meta["was_true"] = True
        meta["next_ok"] = now_ms + cooldown_ms
        return True
    if was_true:
        return False
    meta["was_true"] = True
    return True


def append_on_death_row(dest, kind, words):
    """Parse ``on_death_add_var name n`` into dest['on_death_script']."""
    if len(words) < 2:
        warning("%s needs a variable name", kind)
        return
    name = str(words[1])
    if not is_var_name(name):
        warning("invalid script variable name: %s", name)
        return
    value = parse_script_number(words[2], 1) if len(words) >= 3 else 1
    op = {
        "on_death_add_var": "add_var",
        "on_death_set_var": "set_var",
        "on_death_add_global": "add_global",
        "on_death_set_global": "set_global",
    }.get(kind)
    if not op:
        return
    dest.setdefault("on_death_script", []).append([op, name, value])
