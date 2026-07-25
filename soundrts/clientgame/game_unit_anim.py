"""Optional map-unit animation packs with graceful fallback.

Lookup order (first hit wins):
1. ``ui/anims/<type>/`` Spine pack (optional runtime; see meta.json ``backend: spine``)
2. ``ui/anims/<type>/`` spritesheet / frame pack (``backend: spritesheet`` or default)
3. Caller falls back to ``ui/map/<type>.png`` then geometric shapes + FX

This module never requires Spine to be installed. Missing packs are silent.
"""

from __future__ import annotations

import io
import json
import os
import time
from typing import Dict, Optional, Tuple

import pygame

_pack_cache: Dict[str, Optional["AnimPack"]] = {}
_miss = set()
_frame_state: Dict[Tuple[str, str], float] = {}  # (oid, anim) -> t0


def _open_rel(rel: str):
    """Yield binary file handles for a resource-relative path."""
    try:
        from ..lib.resource import res

        for package, path in res.paths(rel, localize=False):
            try:
                if hasattr(package, "has_file") and not package.has_file(path):
                    if not (hasattr(package, "isfile") and package.isfile(path)):
                        continue
            except Exception:
                pass
            try:
                yield package.open_binary(path)
            except Exception:
                continue
    except Exception:
        pass
    local = os.path.join("res", rel.replace("/", os.sep))
    if os.path.isfile(local):
        yield open(local, "rb")


def _read_bytes(rel: str) -> Optional[bytes]:
    for fh in _open_rel(rel):
        try:
            with fh:
                return fh.read()
        except Exception:
            continue
    return None


def _load_surface(rel: str) -> Optional[pygame.Surface]:
    data = _read_bytes(rel)
    if not data:
        return None
    try:
        return pygame.image.load(io.BytesIO(data)).convert_alpha()
    except Exception:
        return None


def infer_anim_name(entity) -> str:
    """Pick a logical clip from unit orders / action."""
    model = getattr(entity, "model", entity)
    orders = getattr(model, "orders", None) or []
    if orders:
        kw = getattr(orders[0], "keyword", "") or ""
        if kw in ("gather", "exploit"):
            return "gather"
        if kw in ("attack", "patrol"):
            return "attack"
        if kw in ("build", "repair"):
            return "build"
    action = getattr(model, "action", None)
    if action is not None:
        an = type(action).__name__.lower()
        if "attack" in an:
            return "attack"
        if "mov" in an or "go" in an:
            return "walk"
    # crude motion hint
    try:
        if getattr(model, "speed", 0) and getattr(model, "is_idle", True) is False:
            return "walk"
    except Exception:
        pass
    return "idle"


class AnimPack:
    def __init__(self, type_name: str, meta: dict, base_rel: str):
        self.type_name = type_name
        self.meta = meta
        self.base_rel = base_rel.rstrip("/")
        self.backend = (meta.get("backend") or "spritesheet").lower()
        self._sheet = None
        self._frames: Dict[str, list] = {}
        self._spine = None  # optional runtime object
        self._spine_failed = False

    def _ensure_spritesheet(self):
        if self._sheet is not None or self._frames:
            return
        sheet_name = self.meta.get("sheet") or self.meta.get("spritesheet") or "sheet.png"
        surf = _load_surface("%s/%s" % (self.base_rel, sheet_name))
        if surf is None:
            # sequence: frame_0.png, frame_1.png under idle/ etc. handled per-anim
            return
        self._sheet = surf
        fw = int(self.meta.get("frame_w") or self.meta.get("frame_width") or 0)
        fh = int(self.meta.get("frame_h") or self.meta.get("frame_height") or 0)
        anims = self.meta.get("animations") or {}
        if not fw or not fh:
            # whole sheet = one idle frame
            self._frames["idle"] = [surf]
            return
        cols = max(1, surf.get_width() // fw)
        for name, spec in anims.items():
            if isinstance(spec, dict):
                row = int(spec.get("row", 0))
                n = int(spec.get("frames", cols))
                frames = []
                for i in range(n):
                    x = (i % cols) * fw
                    y = row * fh
                    if x + fw > surf.get_width() or y + fh > surf.get_height():
                        break
                    frames.append(surf.subsurface(pygame.Rect(x, y, fw, fh)).copy())
                if frames:
                    self._frames[name] = frames
            elif isinstance(spec, list):
                # list of file names relative to pack
                frames = []
                for fn in spec:
                    fr = _load_surface("%s/%s" % (self.base_rel, fn))
                    if fr is not None:
                        frames.append(fr)
                if frames:
                    self._frames[name] = frames
        if "idle" not in self._frames and self._frames:
            self._frames["idle"] = next(iter(self._frames.values()))

    def _ensure_spine(self) -> bool:
        if self._spine is not None:
            return True
        if self._spine_failed:
            return False
        # Optional dependency — never required to run the game.
        try:
            # Prefer a pygame-oriented binding if present; otherwise mark unavailable.
            import importlib

            spine_mod = None
            for name in ("spine_pygame", "spine", "spinemodule"):
                try:
                    spine_mod = importlib.import_module(name)
                    break
                except ImportError:
                    continue
            if spine_mod is None:
                self._spine_failed = True
                return False
            spine_meta = self.meta.get("spine") or {}
            skel = spine_meta.get("skeleton") or spine_meta.get("json") or "skeleton.json"
            atlas = spine_meta.get("atlas") or "skeleton.atlas"
            # APIs differ across bindings; keep best-effort and fail soft.
            loader = getattr(spine_mod, "load_skeleton", None) or getattr(
                spine_mod, "Skeleton", None
            )
            if loader is None:
                self._spine_failed = True
                return False
            skel_path = "res/%s/%s" % (self.base_rel, skel)
            atlas_path = "res/%s/%s" % (self.base_rel, atlas)
            if callable(loader) and loader is not getattr(spine_mod, "Skeleton", None):
                self._spine = loader(skel_path, atlas_path)
            else:
                self._spine_failed = True
                return False
            return self._spine is not None
        except Exception:
            self._spine_failed = True
            return False

    def blit(
        self,
        screen,
        oid: str,
        anim: str,
        x: int,
        y: int,
        size: int,
        facing: float = 0.0,
    ) -> bool:
        if self.backend == "spine":
            if self._ensure_spine():
                try:
                    draw = getattr(self._spine, "draw", None) or getattr(
                        self._spine, "blit", None
                    )
                    set_anim = getattr(self._spine, "set_animation", None) or getattr(
                        self._spine, "setAnimation", None
                    )
                    if set_anim:
                        set_anim(anim or "idle")
                    if draw:
                        draw(screen, x, y, size)
                        return True
                except Exception:
                    self._spine_failed = True
            # Spine missing → try spritesheet in same pack, else fail
            self.backend = "spritesheet"

        self._ensure_spritesheet()
        frames = self._frames.get(anim) or self._frames.get("idle")
        if not frames:
            # try folder of loose frames: anim/0.png
            loose = []
            for i in range(32):
                fr = _load_surface("%s/%s/%d.png" % (self.base_rel, anim, i))
                if fr is None:
                    fr = _load_surface("%s/%s_%d.png" % (self.base_rel, anim, i))
                if fr is None:
                    break
                loose.append(fr)
            if loose:
                self._frames[anim] = loose
                frames = loose
        if not frames:
            return False

        fps = float(self.meta.get("fps") or 8)
        key = (str(oid), anim)
        t0 = _frame_state.get(key)
        now = time.time()
        if t0 is None:
            _frame_state[key] = now
            t0 = now
        idx = int((now - t0) * fps) % len(frames)
        frame = frames[idx]
        if frame.get_width() != size or frame.get_height() != size:
            frame = pygame.transform.smoothscale(frame, (size, size))
        # facing: flip when facing left (west)
        ang = facing % 360.0
        if 90.0 < ang < 270.0:
            frame = pygame.transform.flip(frame, True, False)
        screen.blit(frame, frame.get_rect(center=(int(x), int(y))))
        return True


def _load_meta(type_name: str) -> Optional[Tuple[dict, str]]:
    base = "ui/anims/%s" % type_name
    for name in ("meta.json", "anim.json", "pack.json"):
        raw = _read_bytes("%s/%s" % (base, name))
        if not raw:
            continue
        try:
            meta = json.loads(raw.decode("utf-8"))
            if isinstance(meta, dict):
                return meta, base
        except Exception:
            continue
    # Implicit spritesheet pack: sheet.png present without meta
    if _read_bytes("%s/sheet.png" % base):
        return {"backend": "spritesheet", "sheet": "sheet.png", "fps": 8}, base
    return None


def get_anim_pack(type_name: str) -> Optional[AnimPack]:
    type_name = (type_name or "").strip()
    if not type_name or type_name in _miss:
        return None
    if type_name in _pack_cache:
        return _pack_cache[type_name]
    loaded = _load_meta(type_name)
    if loaded is None:
        _miss.add(type_name)
        _pack_cache[type_name] = None
        return None
    meta, base = loaded
    pack = AnimPack(type_name, meta, base)
    _pack_cache[type_name] = pack
    return pack


def try_blit_unit_anim(screen, entity, x, y, size, *, facing: float = 0.0) -> bool:
    """Draw animated unit if a pack exists. Returns False → caller uses icon/shapes."""
    if size < 10:
        return False
    type_name = (
        getattr(entity, "type_name", None)
        or getattr(getattr(entity, "model", None), "type_name", None)
        or ""
    )
    pack = get_anim_pack(str(type_name))
    if pack is None:
        return False
    oid = str(getattr(entity, "id", type_name))
    anim = infer_anim_name(entity)
    try:
        return pack.blit(screen, oid, anim, int(x), int(y), int(size), facing=facing)
    except Exception:
        return False


def clear_anim_caches():
    _pack_cache.clear()
    _miss.clear()
    _frame_state.clear()
