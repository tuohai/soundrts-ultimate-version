"""Re-tint the AoE2 DE art per architecture set.

The 1.4.9.7 high-res art pass installed the *same* trial sprite into every
``ui/map/<set>/`` and ``ui/icons/<set>/`` directory, so all eight DE
architecture sets rendered identically and the ``ui/architecture.txt``
palettes had no visible effect.

This tool re-grades the installed art per set: it rotates the hue of the
opaque pixels toward the set's accent colour (and nudges saturation), so
each civ reads as its own colour scheme while keeping the real AoE2
artwork's shading and detail.

Usage::

    python tools/tint_aoe2_arch_sets.py [--dry-run]
"""

from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ARCH_FILE = ROOT / "mods" / "aoe2" / "ui" / "architecture.txt"

sys.path.insert(0, str(ROOT))
from soundrts.lib.arch_set import parse_architecture  # noqa: E402

TARGETS = ("ui/map", "ui/icons")

# How strongly the set accent pulls the art's hue (0 = keep, 1 = fully accent).
HUE_STRENGTH = 0.75
# Saturation multiplier applied after the hue rotation.
SAT_BOOST = 1.12

# The DE palettes share hues (western / east / central_asian are all
# red-tabbed), so the palette hue alone cannot tell two sets apart.  Each
# architecture *kit* is a distinct silhouette recipe, so every kit gets its
# own target hue.  The eight targets are spread around the wheel and keep
# all sets visually separable.
KIT_TARGET_HUE = {
    "western": 0.03,
    "central": 0.58,
    "med": 0.11,
    "east": 0.00,
    "yurt": 0.09,
    "sea": 0.40,
    "meso": 0.47,
    "african": 0.14,
}


def _palette_hue(style: dict) -> float:
    """Saturation-weighted circular mean hue of the set's palette."""
    total = 0.0
    total_w = 0.0
    for key in ("rim", "armor", "tunic", "horse", "wood", "roof", "stone", "tab"):
        rgb = style.get(key)
        if not rgb:
            continue
        h, s, _v = colorsys.rgb_to_hsv(*(v / 255.0 for v in rgb))
        w = s
        if w <= 0.01:
            continue
        ang = h * 2 * np.pi
        total += np.sin(ang) * w
        total_w += np.cos(ang) * w
    if abs(total_w) < 1e-6 and total_w == 0.0:
        return 0.0
    return (np.arctan2(total, total_w) / (2 * np.pi)) % 1.0


def _accent(style: dict) -> tuple:
    """Pick the set's most distinctive colour as the accent."""
    for key in ("tab", "tunic", "roof", "rim", "armor"):
        rgb = style.get(key)
        if rgb:
            return tuple(v / 255.0 for v in rgb)
    return (0.6, 0.2, 0.2)


def tint(im: Image.Image, style: dict) -> Image.Image:
    """Re-grade ``im`` toward the architecture set's accent colour."""
    rgba = np.array(im.convert("RGBA"), dtype=np.float32)
    alpha = rgba[:, :, 3]
    opaque = alpha > 8
    if not opaque.any():
        return im

    rgb = rgba[:, :, :3] / 255.0
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    diff = mx - mn
    v = mx
    s = np.zeros_like(mx)
    h = np.zeros_like(mx)
    nonzero = diff > 1e-6
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    idx = nonzero & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / diff[idx]) % 6
    idx = nonzero & (mx == g)
    h[idx] = ((b[idx] - r[idx]) / diff[idx]) + 2
    idx = nonzero & (mx == b)
    h[idx] = ((r[idx] - g[idx]) / diff[idx]) + 4
    h = h / 6.0
    s = np.where(mx > 1e-6, diff / np.maximum(mx, 1e-6), 0.0)

    # Dominant hue of the artwork = circular mean over opaque pixels,
    # weighted by saturation so grey background pixels barely count.
    weights = s * (alpha / 255.0)
    if weights.sum() > 1e-6:
        ang = h * 2 * np.pi
        mean_ang = np.arctan2((np.sin(ang) * weights).sum(), (np.cos(ang) * weights).sum())
        art_hue = (mean_ang / (2 * np.pi)) % 1.0
    else:
        art_hue = 0.0

    accent = _accent(style)
    accent_h, _accent_s, _accent_v = colorsys.rgb_to_hsv(*accent)
    # The kit defines the set's colour identity; the palette only nudges it.
    kit = style.get("kit", "western")
    target_h = KIT_TARGET_HUE.get(kit, _palette_hue(style))
    accent_h = 0.35 * accent_h + 0.65 * target_h

    # Rotate every opaque pixel's hue so the artwork's dominant hue lands
    # on the accent hue (partially -- the art keeps some of its own colour).
    delta = (accent_h - art_hue + 0.5) % 1.0 - 0.5
    h_new = (h + delta * HUE_STRENGTH) % 1.0
    s_new = np.clip(s * SAT_BOOST, 0.0, 1.0)

    # Back to RGB.
    i = np.floor(h_new * 6.0).astype(np.int32) % 6
    f = h_new * 6.0 - np.floor(h_new * 6.0)
    p = v * (1 - s_new)
    q = v * (1 - f * s_new)
    t = v * (1 - (1 - f) * s_new)
    out = np.zeros_like(rgb)
    out[:, :, 0] = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    out[:, :, 1] = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    out[:, :, 2] = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])

    rgba[:, :, :3] = np.where(opaque[:, :, None], out * 255.0, rgba[:, :, :3])
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _mapping, sets, _neutral = parse_architecture(
        ARCH_FILE.read_text(encoding="utf-8")
    )
    for name, spec in sets.items():
        style = dict(spec)
        for folder in TARGETS:
            set_dir = ROOT / "mods" / "aoe2" / folder / name
            if not set_dir.is_dir():
                continue
            n = 0
            for png in sorted(set_dir.glob("*.png")):
                if args.dry_run:
                    print("would tint", png.relative_to(ROOT))
                    n += 1
                    continue
                tinted = tint(Image.open(png), style)
                tmp = png.with_suffix(".png.tmp")
                tinted.save(tmp, "PNG")
                tmp.replace(png)
                n += 1
            print(f"{name}/{folder}: {n} png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
