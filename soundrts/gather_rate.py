# -*- coding: utf-8 -*-
"""Shared helpers for computing a worker's *effective* gathering numbers.

The live simulation (``soundrts.worldunit.worldworker.Worker``) and the
attributes screen must agree on what "0.38 gold per second" means: after
the player researches Gold Mining the number has to change, otherwise the
attribute screen lies about the unit's real speed.

Both sides therefore resolve the bonuses through the helpers in this module
instead of duplicating the lookup order.  The rules store their bonuses in
``player.gather_time_bonus`` / ``player.gather_qty_bonus``, keyed by
whatever suffix the rules row used:

* the **resource slot** — ``resource1``, ``resource2``, … (a bonus for
  every deposit that yields that resource), or
* the **deposit type** — ``goldmine``, ``wood``, ``stone_mine`` (a bonus
  for one specific deposit, which is how the AoE2 mining / lumber techs
  and the shepherd / hunter bonuses are written), or
* the **resource name** — ``gold``, ``wood``, ``stone``, as declared by
  the rules (``parameters resource_names``; the engine hardcodes no
  resource name), or
* ``all`` — a blanket bonus.

``Worker.get_gather_time`` and the continuous rate path used to resolve
those keys in *different* orders (slot first vs. deposit first), so a
resource-wide bonus could shadow a deposit-specific tech in one path and
not in the other — the attribute screen then disagreed with the live
simulation.  Both now share the single order implemented by
:func:`bonus_keys`: *deposit type* → *resource slot* → *resource name* →
``all``.
"""

from __future__ import annotations


def resource_name_aliases(resource_type):
    """The resource *name* spellings that may key a gather bonus.

    ``resource_type`` is the engine's canonical slot id (``"resource1"``),
    but rules rows may name the resource instead — the AoE2 civ phase
    bonuses use ``gold`` / ``wood`` / ``food`` / ``stone`` (e.g. the
    Ethiopians' ``on_phase castle_age gather_time -50% gold``).  Those rows
    must reach the worker, so every spelling of the slot is tried.

    The spellings come from the rules (``parameters resource_names``), so
    the engine hardcodes no resource name; the deposit types that yield
    the slot are accepted as well.

    Returns the aliases in order (most specific first).  An unknown slot
    yields an empty tuple.
    """
    if not resource_type:
        return ()
    try:
        from .worldmarket import parse_resource_index

        index = parse_resource_index(resource_type)
    except Exception:
        index = None
    if index is None:
        return ()
    names = []
    try:
        from .worldmarket import resource_name_aliases as _aliases

        names.extend(_aliases(index))
    except Exception:
        pass
    return tuple(names)


def _percent_value(value):
    """Return *value* as a percentage number, or ``None`` if it is not one."""
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            try:
                return float(text[:-1])
            except ValueError:
                return None
    return None


def _lookup_bonus(bonus, keys):
    """First non-``None`` bonus value for *keys* (in order) in *bonus*.

    *bonus* may be a dict (the normal case), a plain scalar (applies to
    everything), a :class:`_MergedBonus` (the technology bonuses combined
    with the civilization phase bonuses) or ``None``.
    """
    if not bonus:
        return None
    if isinstance(bonus, _MergedBonus):
        return bonus.lookup(keys)
    if isinstance(bonus, dict):
        for key in keys:
            if not key:
                continue
            if key in bonus:
                return bonus[key]
        return None
    # Legacy scalar form: the same bonus for every resource.
    return bonus


def combine_bonus_values(old, new):
    """Combine two gather bonus values into one.

    Two **percent** bonuses multiply (two "-13%" rows mean 26% less time,
    not 13%); two **flat** bonuses add.  A percent and a flat value cannot
    be combined, so the percent wins (the flat value is a number of
    seconds, which is a different unit).
    """
    if old is None:
        return new
    if new is None:
        return old
    old_pct = isinstance(old, str) and str(old).endswith("%")
    new_pct = isinstance(new, str) and str(new).endswith("%")
    if old_pct and new_pct:
        factor = (1 + float(str(old)[:-1]) / 100.0) * (
            1 + float(str(new)[:-1]) / 100.0
        )
        return f"{(factor - 1) * 100.0:.6f}%"
    if not old_pct and not new_pct:
        try:
            return int(float(old)) + int(float(new))
        except (TypeError, ValueError):
            return new
    # Mixed units — the percent wins.
    return old if old_pct else new


def player_gather_bonus(player, kind):
    """The gather bonuses of *kind* (``"time"`` / ``"qty"``) of *player*.

    Two sources are combined:

    * ``player.gather_time_bonus`` / ``player.gather_qty_bonus`` — the
      bonuses granted by **technologies**;
    * ``player.phase_gather_time_bonus`` / ``player.phase_gather_qty_bonus``
      — the bonuses granted by **civilization phase bonuses**
      (``on_phase … gather_time_…``).

    They are stored apart on purpose: both may use the same key (the
    mining-camp tech and the Romans' civ bonus are both written for
    ``resource1``), and a single shared dict would make one of them
    silently overwrite the other.

    The two are resolved *independently* — each namespace picks its own
    most specific key — and only then combined.  Merging the dicts first
    would let a narrow key in one namespace hide a broad key in the other
    (the Mayans' ``goldmine`` bonus would hide the Romans' ``resource1``
    one, and the mining tech would be lost).
    """
    if player is None:
        return None
    attr = "gather_time_bonus" if kind == "time" else "gather_qty_bonus"
    phase_attr = (
        "phase_gather_time_bonus" if kind == "time"
        else "phase_gather_qty_bonus"
    )
    tech = getattr(player, attr, None)
    phase = getattr(player, phase_attr, None)
    if not tech and not phase:
        return None
    return _MergedBonus(tech, phase)


class _MergedBonus:
    """The bonuses of two namespaces, resolved independently.

    ``lookup`` picks the most specific key of *each* namespace on its own
    and combines the two results.  This keeps a deposit-scoped bonus from
    hiding a resource-wide one that lives in the other namespace.
    """

    def __init__(self, tech, phase):
        self.tech = tech if isinstance(tech, dict) else None
        self.phase = phase if isinstance(phase, dict) else None
        self._tech_scalar = None if self.tech is not None else tech
        self._phase_scalar = None if self.phase is not None else phase

    def _one(self, bonus, scalar, keys):
        if bonus is not None:
            return _lookup_bonus(bonus, keys)
        if scalar:
            return scalar
        return None

    def lookup(self, keys):
        tech_value = self._one(self.tech, self._tech_scalar, keys)
        phase_value = self._one(self.phase, self._phase_scalar, keys)
        if tech_value is None:
            return phase_value
        if phase_value is None:
            return tech_value
        return combine_bonus_values(tech_value, phase_value)

    def __bool__(self):
        return bool(self.tech or self.phase
                    or self._tech_scalar or self._phase_scalar)

    def get(self, key, default=None):
        value = self.lookup((key,))
        return default if value is None else value

    def keys(self):
        keys = []
        for d in (self.tech, self.phase):
            if d:
                for key in d:
                    if key not in keys:
                        keys.append(key)
        return keys

    def __iter__(self):
        return iter(self.keys())

    def items(self):
        return [(key, self.lookup((key,))) for key in self.keys()]

    def __contains__(self, key):
        return key in self.keys()

    def __getitem__(self, key):
        value = self.lookup((key,))
        if value is None:
            raise KeyError(key)
        return value


def bonus_keys(deposit_type, resource_type, order=None):
    """The bonus keys to try, in lookup order.

    A gather bonus may be written with either of two kinds of key:

    * the **resource slot** — ``gather_time_resource1`` (every deposit that
      yields that resource is affected);
    * the **deposit type** — ``gather_time_goldmine`` (only that deposit is
      affected, which is how the AoE2 shepherd / hunter bonuses stay
      separate).

    The single, shared order is:

    1. the **deposit type** — the most specific key, so a mining / lumber
       tech always wins over a civ-wide bonus for the same resource;
    2. the **resource slot** — ``resource1`` / ``resource2`` / …;
    3. the **resource name** — the aliases declared by
       ``parameters resource_names`` (``gold`` / ``wood`` / …), so rules
       rows may name the resource instead of numbering it;
    4. ``all`` — the blanket bonus.

    *order* is accepted for backwards compatibility only; every caller
    now uses the same order so the attribute screen and the live
    simulation can never disagree about which bonus applies.
    """
    aliases = resource_name_aliases(resource_type)
    keys = [deposit_type, resource_type]
    if resource_type:
        keys.extend(aliases)
    keys.append("all")
    # Keep the first occurrence of each key.
    seen = set()
    unique = []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return tuple(unique)


def lookup_bonus(bonus, keys):
    """First non-``None`` bonus value for *keys* (in order) in *bonus*.

    *bonus* may be a dict (the normal case), a plain scalar (applies to
    everything) or ``None``.
    """
    return _lookup_bonus(bonus, keys)


def time_bonus_factor(bonus, deposit_type, resource_type):
    """Multiplier applied to the *time* by ``player.gather_time_bonus``.

    A ``-13%`` bonus means "13% less time", so the factor is ``0.87``.
    Flat bonuses (seconds) cannot be turned into a multiplier here — they
    are handled by ``Worker.get_gather_time`` itself.
    """
    value = _lookup_bonus(bonus, bonus_keys(deposit_type, resource_type))
    pct = _percent_value(value)
    if pct is None:
        return None
    return 1.0 + pct / 100.0

def rate_bonus_factor(bonus, deposit_type, resource_type):
    """Multiplier applied to the *rate* by ``player.gather_time_bonus``.

    A ``-13%`` time bonus makes the worker 1/0.87 ≈ 1.15 times faster, so
    the rate factor is ``1 / factor``.  Returns ``None`` when the bonus is
    flat (seconds) rather than a percentage.
    """
    factor = time_bonus_factor(bonus, deposit_type, resource_type)
    if factor is None or factor <= 0.01:
        return None
    return 1.0 / factor


def qty_bonus_factor(bonus, deposit_type, resource_type):
    """Multiplier applied to the *quantity* by ``player.gather_qty_bonus``.

    ``+25%`` → ``1.25``.  Flat bonuses (extra units per trip) return
    ``None`` because they are not expressible as a multiplier.
    """
    value = _lookup_bonus(bonus, bonus_keys(deposit_type, resource_type))
    pct = _percent_value(value)
    if pct is None:
        return None
    return 1.0 + pct / 100.0


def base_gather_rate(unit, deposit_type):
    """The unit's *unmodified* per-second rate for *deposit_type*.

    Mirrors ``Worker.get_gather_rate``'s lookup order:

    1. ``gather_rate_<deposit_type>``
    2. the ``gather_rate`` dict (keyed by deposit type) or a scalar

    Returns ``None`` when the unit has no explicit rate for that deposit.
    """
    if deposit_type:
        attr = f"gather_rate_{deposit_type}"
        if hasattr(unit, attr):
            try:
                value = float(getattr(unit, attr))
            except (TypeError, ValueError):
                value = None
            if value:
                return value
    raw = getattr(unit, "gather_rate", None)
    if isinstance(raw, dict):
        if deposit_type and deposit_type in raw:
            try:
                value = float(raw[deposit_type])
            except (TypeError, ValueError):
                return None
            return value or None
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) or None
    return None
