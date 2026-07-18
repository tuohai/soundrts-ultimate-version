"""Scan ``user/voices/*/voice.ini`` packs (friendly titles → SAPI names).

These packs do **not** install a TTS engine. The ``sapi`` field must match a
voice already registered with Windows SAPI5 (substring match allowed).
"""

from __future__ import annotations

import configparser
import os
from typing import Dict, List, Optional, Tuple

from .log import exception, warning

PREFIX = "pack:"


def _voices_root() -> str:
    try:
        from ..paths import VOICES_PATH

        return VOICES_PATH
    except Exception:
        return os.path.join("user", "voices")


def is_pack_voice(voice_id: str) -> bool:
    return (voice_id or "").strip().lower().startswith(PREFIX)


def pack_folder_name(voice_id: str) -> str:
    s = (voice_id or "").strip()
    if s.lower().startswith(PREFIX):
        return s[len(PREFIX) :].strip()
    return s


def _read_ini(path: str) -> Optional[dict]:
    try:
        cp = configparser.ConfigParser()
        # UTF-8 with BOM / plain UTF-8
        try:
            cp.read(path, encoding="utf-8-sig")
        except Exception:
            cp.read(path, encoding="utf-8")
        if not cp.has_section("voice"):
            return None
        title = (cp.get("voice", "title", fallback="") or "").strip()
        sapi = (cp.get("voice", "sapi", fallback="") or "").strip()
        if not sapi:
            return None
        rate_s = (cp.get("voice", "rate", fallback="0") or "0").strip()
        try:
            rate = max(-10, min(10, int(rate_s)))
        except Exception:
            rate = 0
        return {"title": title or sapi, "sapi": sapi, "rate": rate}
    except Exception:
        exception("failed to read voice pack %r", path)
        return None


def scan_packs() -> List[dict]:
    """Return packs: ``{id, folder, title, sapi, rate, path}``."""
    root = _voices_root()
    out: List[dict] = []
    if not os.path.isdir(root):
        return out
    try:
        names = sorted(os.listdir(root), key=lambda s: s.lower())
    except Exception:
        return out
    for name in names:
        if name.startswith(".") or name.lower() == "nuance":
            continue
        folder = os.path.join(root, name)
        if not os.path.isdir(folder):
            continue
        ini = os.path.join(folder, "voice.ini")
        if not os.path.isfile(ini):
            continue
        meta = _read_ini(ini)
        if not meta:
            warning("ignore voice pack without sapi: %s", folder)
            continue
        out.append(
            {
                "id": PREFIX + name,
                "folder": name,
                "title": meta["title"],
                "sapi": meta["sapi"],
                "rate": meta["rate"],
                "path": folder,
            }
        )
    return out


def packs_by_id() -> Dict[str, dict]:
    return {p["id"]: p for p in scan_packs()}


def packs_by_sapi() -> Dict[str, dict]:
    """Lowercased sapi description → pack (first wins)."""
    out: Dict[str, dict] = {}
    for p in scan_packs():
        key = p["sapi"].lower()
        out.setdefault(key, p)
    return out


def resolve_sapi(voice_id: str) -> Tuple[str, Optional[dict]]:
    """Map ``pack:folder`` / pack title / raw SAPI id → (sapi_name, pack_or_None)."""
    v = (voice_id or "").strip()
    if not v:
        return v, None
    if is_pack_voice(v):
        p = packs_by_id().get(v)
        if p:
            return p["sapi"], p
        return "", None
    # Exact / case-insensitive match on title or sapi from packs
    for p in scan_packs():
        if v == p["title"] or v.lower() == p["title"].lower():
            return p["sapi"], p
        if v == p["sapi"] or v.lower() == p["sapi"].lower():
            return p["sapi"], p
    return v, packs_by_sapi().get(v.lower())


def display_name(voice_id: str) -> str:
    v = (voice_id or "").strip()
    if not v:
        return v
    if is_pack_voice(v):
        p = packs_by_id().get(v)
        return p["title"] if p else pack_folder_name(v)
    p = packs_by_sapi().get(v.lower())
    if p:
        return p["title"]
    for pack in scan_packs():
        if v == pack["title"] or v.lower() == pack["title"].lower():
            return pack["title"]
    return v


def list_selectable_ids(*, installed_sapi: Optional[List[str]] = None) -> List[str]:
    """Return ``pack:…`` ids.

    When ``installed_sapi`` is provided, only packs whose ``sapi`` matches an
    installed voice (exact or substring, case-insensitive) are returned.
    """
    packs = scan_packs()
    if installed_sapi is None:
        return [p["id"] for p in packs]
    installed_low = [s.lower() for s in installed_sapi if s]
    out = []
    for p in packs:
        needle = p["sapi"].lower()
        ok = any(
            needle == s or needle in s or s in needle for s in installed_low
        )
        if ok:
            out.append(p["id"])
    return out


def pack_installed(pack: dict, installed_sapi: List[str]) -> bool:
    needle = (pack.get("sapi") or "").lower()
    if not needle:
        return False
    for s in installed_sapi or []:
        low = (s or "").lower()
        if needle == low or needle in low or low in needle:
            return True
    return False
