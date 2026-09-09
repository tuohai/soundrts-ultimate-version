"""Treaty duration choices, aligned with Age of Empires II Definitive Edition."""

# AoE2 DE lobby: 5-minute steps from 5 to 60, plus 90.
TREATY_MINUTE_CHOICES = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 90)
MIN_CUSTOM_TREATY_MINUTES = 5
MAX_TREATY_MINUTES = 90


def clamp_treaty_minutes(value) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 0
    if minutes <= 0:
        return 0
    if minutes > MAX_TREATY_MINUTES:
        return MAX_TREATY_MINUTES
    return minutes


def parse_custom_treaty_minutes(value):
    """Return an int in 5–90, or None if empty / not an int / out of range."""
    try:
        minutes = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if minutes < MIN_CUSTOM_TREATY_MINUTES or minutes > MAX_TREATY_MINUTES:
        return None
    return minutes


def prompt_custom_treaty_minutes():
    """Ask for a custom duration. None means cancel or invalid input."""
    from . import msgparts as mp
    from .clientmedia import voice
    from .clientmenu import input_string

    raw = input_string(
        list(mp.ENTER_TREATY_MINUTES),
        pattern=r"^[0-9]$",
        default="",
        spell=True,
        max_length=2,
    )
    if raw is None:
        return None
    minutes = parse_custom_treaty_minutes(raw)
    if minutes is None:
        voice.info(mp.BEEP)
        return None
    return minutes
