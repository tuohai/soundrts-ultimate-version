"""Room password tokens for the multiplayer protocol.

Passwords are optional. An empty password means the room is open: anyone
compatible can join (if a slot is free) or spectate (if the match started).
The password itself is never sent in lobby listings — only a yes/no flag.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

MAX_ROOM_PASSWORD_LEN = 20


def sanitize_room_password(raw) -> str:
    if not raw:
        return ""
    return "".join(c for c in str(raw) if c.isalnum())[:MAX_ROOM_PASSWORD_LEN]


def extract_password_token(tokens: Sequence[str]) -> Tuple[str, List[str]]:
    password = ""
    kept: List[str] = []
    for t in tokens:
        s = str(t)
        if s.startswith("password="):
            password = sanitize_room_password(s.split("=", 1)[1])
        else:
            kept.append(s)
    return password, kept


def password_arg(password: str) -> str:
    cleaned = sanitize_room_password(password)
    if not cleaned:
        return ""
    return f"password={cleaned}"
