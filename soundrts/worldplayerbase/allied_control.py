"""盟友指挥权查询 — 独立模块避免 worldcreature ↔ base 循环 import."""


def _world_has_allied_control(world):
    for player in world.players:
        if player.allied_control_units_set:
            return True
        if len(player.allied_control) > 1:
            return True
    return False


def mark_allied_control_changed(world):
    """触发器修改 allied_control 后调用; 使 per-unit 缓存失效."""
    world._allied_control_active = True
    world._allied_control_scanned = True
    world._allied_control_epoch = getattr(world, "_allied_control_epoch", 0) + 1


def allied_control_controller_for(unit):
    """返回正在指挥该单位的玩家（全盟友或选择性移交），无则 None。

    When no allied-control transfer is active, returns the unit's own player
    (legacy callers). Prefer checking ``world._allied_control_active`` first
    on hot paths that only need the inactive fast-path.
    """
    world = getattr(unit, "world", None)
    if world is None:
        return None
    if not getattr(world, "_allied_control_scanned", False):
        world._allied_control_active = _world_has_allied_control(world)
        world._allied_control_scanned = True
    if not world._allied_control_active:
        return getattr(unit, "player", None)
    epoch = getattr(world, "_allied_control_epoch", 0)
    cache = getattr(unit, "_allied_control_controller_cache", None)
    if cache is not None and cache[0] == epoch:
        return cache[1]
    result = None
    for player in world.players:
        if player.unit_under_allied_control(unit):
            result = player
            break
    unit._allied_control_controller_cache = (epoch, result)
    return result
