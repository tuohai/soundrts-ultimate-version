"""Voice and ambient sound helpers for build fields (psi, creep, etc.)."""

from .. import msgparts as mp
from ..animation import noise
from ..clientgameentity import SquareView
from ..clientmedia import voice
from ..definitions import style


def build_field_style_name(field_type):
    return f"build_field_{field_type}"


def build_field_noise_style(field_type):
    """style.txt ``noise repeat`` / ``noise loop`` on ``build_field_<type>``."""
    return style.get(
        build_field_style_name(field_type), "noise", warn_if_not_found=False
    )


def build_field_title_msg(field_type):
    """TTS fragments for style.txt ``build_field_<type>`` title."""
    title = style.get(
        f"build_field_{field_type}", "title", warn_if_not_found=False
    )
    if not title:
        return [str(field_type)]
    if isinstance(title, list):
        return list(title)
    return [str(title)]


def square_build_field_msgs(interface, place):
    """Build field labels for a visible square (movement announcement)."""
    if place not in interface.scouted_squares:
        return []
    player = interface.player
    if player is None:
        return []
    world = getattr(player, "world", None)
    if world is None:
        return []
    from ..world_build_rules import build_field_types_on_square

    result = []
    for field_type in build_field_types_on_square(world, place, player):
        result.extend(build_field_title_msg(field_type))
        result.extend(mp.COMMA)
    if result and result[-1] in mp.COMMA:
        result = result[:-1]
    return result


def voice_missing_build_field(reason):
    """Play one voice line when build fails for missing build field."""
    if not reason or not str(reason).startswith("missing_build_field."):
        return False
    field_type = str(reason).split(".", 1)[1]
    msg = style.get(
        "messages", f"missing_build_field_{field_type}", warn_if_not_found=False
    )
    if not msg:
        msg = style.get("messages", "missing_build_field", warn_if_not_found=False)
    if not msg:
        msg = style.get("messages", "cannot_build_here", warn_if_not_found=False)
    if msg:
        voice.info(msg)
    return True


def voice_missing_deposit(reason):
    """Play generic + deposit-type voice when build fails for missing deposit."""
    if not reason or not str(reason).startswith("missing_deposit."):
        return False
    deposit_type = str(reason).split(".", 1)[1]
    msg = style.get("messages", "missing_deposit", warn_if_not_found=False)
    if not msg:
        msg = style.get("messages", "cannot_build_here", warn_if_not_found=False)
    if msg:
        voice.info(msg)
    title = style.get(deposit_type, "title", warn_if_not_found=False)
    if title:
        if isinstance(title, list):
            voice.info(list(title))
        else:
            voice.info([str(title)])
    return True


def stop_build_field_noises(interface):
    build_field_noises = getattr(interface, "_build_field_noises", [])
    for n in build_field_noises[:]:
        n.stop()
    interface._build_field_noises = []


def animate_build_field_noises(interface):
    """Ambient build-field sounds while the focused square has active fields."""
    if not interface.place:
        stop_build_field_noises(interface)
        return
    if interface.place not in interface.scouted_squares:
        stop_build_field_noises(interface)
        return
    player = interface.player
    if player is None:
        stop_build_field_noises(interface)
        return
    world = getattr(player, "world", None)
    if world is None:
        stop_build_field_noises(interface)
        return
    from ..world_build_rules import build_field_types_on_square

    place = interface.place
    active = set()
    for field_type in build_field_types_on_square(world, place, player):
        if build_field_noise_style(field_type):
            active.add((place, field_type))

    build_field_noises = getattr(interface, "_build_field_noises", [])
    for n in build_field_noises[:]:
        key = getattr(n, "_build_field_key", None)
        if key not in active:
            n.stop()
            build_field_noises.remove(n)
        else:
            n.update()

    existing = {getattr(n, "_build_field_key", None) for n in build_field_noises}
    for key in active:
        if key in existing:
            continue
        sq, field_type = key
        st = build_field_noise_style(field_type)
        n = noise(SquareView(interface, sq), st)
        if n:
            n._build_field_key = key
            build_field_noises.append(n)

    interface._build_field_noises = build_field_noises
