"""Persist the player's view focus (the square the camera is on) across
save / load.

Before this module the interface was stripped from the pickle
(``_Savable.__getstate__`` pops ``interface``), so the focused square was
never written to disk.  On load, ``set_obs_pos()`` fell back to
``_initial_observer_place()`` -- the spawn square of the first
controllable unit -- so the camera always jumped back to the town centre
instead of returning to the square the player was looking at when they
saved.

The focus is stored as plain data (square ``id`` + the zoom sub-cell
coordinates) so it survives pickling without dragging the whole
interface (and its pygame/thread state) into the save file.
"""

from __future__ import annotations


def capture_focus(interface) -> dict | None:
    """Snapshot the interface's current focus as plain picklable data.

    Returns ``None`` when there is nothing worth restoring (no interface,
    no focused square, or the square is not part of the world).
    """
    if interface is None:
        return None
    place = getattr(interface, "place", None)
    if place is None:
        return None
    square_id = getattr(place, "id", None)
    if square_id is None:
        return None
    data = {"square_id": square_id}
    zoom = getattr(interface, "zoom", None)
    if zoom is not None:
        sub_x = getattr(zoom, "sub_x", None)
        sub_y = getattr(zoom, "sub_y", None)
        precision = getattr(zoom, "precision", None)
        if sub_x is not None and sub_y is not None:
            data["zoom_sub_x"] = int(sub_x)
            data["zoom_sub_y"] = int(sub_y)
        if precision is not None:
            data["zoom_precision"] = int(precision)
    return data


def fog_state_ready(interface) -> bool:
    """True once the server has sent the fog-of-war data for this game.

    The server pushes a ``voila`` event every world tick carrying
    ``scouted_squares`` / ``scouted_before_squares``.  Until the first one
    arrives the interface has empty fog sets, so announcing a square would
    wrongly say "unknown" ("未知").
    """
    if interface is None:
        return False
    synced = getattr(interface, "_fog_synced", None)
    if synced is not None:
        return bool(synced)
    # Fallback for interfaces that do not track the flag (e.g. tests):
    # the fog sets must be non-empty.
    scouted = getattr(interface, "scouted_squares", None)
    before = getattr(interface, "scouted_before_squares", None)
    if scouted is None or before is None:
        return False
    return bool(scouted or before)


def announce_restored_focus(interface, place) -> None:
    """Announce the restored square, once the fog state is known.

    The announcement is queued rather than spoken immediately: right after
    a load the client has not received a ``voila`` yet, so the square would
    be announced as "unknown".  ``flush_pending_square_announce`` (called
    every frame by the client loop) speaks it as soon as the fog data has
    arrived.
    """
    if interface is None or place is None:
        return
    try:
        interface._pending_square_announce = {
            "place": place,
            "prefix": [],
            "require_fog": True,
        }
    except Exception:
        pass


def restore_focus(interface, data) -> bool:
    """Restore a focus snapshot taken by :func:`capture_focus`.

    Returns ``True`` when the focus was restored.  A snapshot that no
    longer matches the loaded world (square gone, id reused) is ignored
    so a stale save can never crash the client.
    """
    if interface is None or not data:
        return False
    try:
        square_id = data.get("square_id")
        if square_id is None:
            return False
        world = getattr(interface, "world", None)
        if world is None:
            return False
        place = None
        for sq in getattr(world, "squares", ()) or ():
            if getattr(sq, "id", None) == square_id:
                place = sq
                break
        if place is None:
            return False
        interface.place = place
        interface.target = None
        interface.follow_mode = False
        # Restore the zoom sub-cell when the snapshot had one.
        sub_x = data.get("zoom_sub_x")
        sub_y = data.get("zoom_sub_y")
        if sub_x is not None and sub_y is not None:
            try:
                from .clientgamefocus import Zoom

                zoom = Zoom(interface)
                zoom.sub_x = int(sub_x)
                zoom.sub_y = int(sub_y)
                zoom.update_coords()
                interface.zoom = zoom
                interface.zoom_mode = True
            except Exception:
                pass
        # Re-centre the free camera on the restored square.
        grid_view = getattr(interface, "grid_view", None)
        if grid_view is not None:
            try:
                grid_view._cam_force_center = True
                grid_view._cam_origin = None
            except Exception:
                pass
        return True
    except Exception:
        return False
