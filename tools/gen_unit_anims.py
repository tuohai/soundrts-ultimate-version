"""Generate starter unit animation packs (ui/anims/) — geometric spritesheets.

Run: python tools/gen_unit_anims.py

Each pack: meta.json + sheet.png (4 directions × idle/walk/attack/gather).
Original flat silhouettes (same style as tools/gen_hud_icons.py).
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FRAME_W = 32
FRAME_H = 32
FPS = 8
DIRS = 4

# idle, walk, attack, gather/build — row bases (each anim uses 4 consecutive rows)
ANIM_ROWS = {
    "idle": 0,
    "walk": 4,
    "attack": 8,
    "gather": 12,
    "build": 12,
}
ANIM_FRAMES = {
    "idle": 4,
    "walk": 6,
    "attack": 4,
    "gather": 4,
    "build": 4,
}

BASE_MOBILE = (
    "peasant",
    "footman",
    "archer",
    "knight",
    "catapult",
    "mage",
    "priest",
    "dragon",
    "flyingmachine",
    "boat",
    "destroyer",
    "battleship",
)

AOE2_MOBILE = ("peasant", "militia", "archer", "knight", "scout")


def _bob(anim: str, frame: int) -> int:
    if anim == "idle":
        return (frame % 2) * 1
    if anim == "walk":
        return (frame % 3) - 1
    if anim == "attack":
        return -1 if frame % 2 else 0
    if anim in ("gather", "build"):
        return (frame % 2) * 1
    return 0


def _swing(anim: str, frame: int) -> int:
    if anim == "attack":
        return frame * 3
    if anim in ("gather", "build"):
        return frame * 2
    if anim == "walk":
        return frame * 2
    return 0


def _draw_humanoid(d: ImageDraw.ImageDraw, *, body, trim, phase: int, anim: str):
    y = 8 + _bob(anim, phase)
    d.ellipse((11, y, 21, y + 10), fill=(220, 180, 140))
    d.polygon(
        [(8, y + 10), (24, y + 10), (26, y + 26), (6, y + 26)],
        fill=body,
    )
    if anim == "attack":
        sx = 22 + _swing(anim, phase)
        d.line([(sx, y + 12), (sx + 8, y + 6)], fill=(200, 200, 210), width=2)
    elif anim in ("gather", "build"):
        gx = 20 + _swing(anim, phase)
        d.line([(gx, y + 14), (gx + 6, y + 8)], fill=trim, width=2)
    elif anim == "walk":
        leg = phase % 2
        d.line([(12, y + 26), (10 - leg, 30)], fill=(60, 40, 30), width=2)
        d.line([(20, y + 26), (22 + leg, 30)], fill=(60, 40, 30), width=2)


def _draw_archer(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 8 + _bob(anim, phase)
    d.ellipse((12, y, 20, y + 8), fill=(210, 175, 140))
    d.polygon([(10, y + 8), (22, y + 8), (24, y + 24), (8, y + 24)], fill=(40, 90, 50))
    d.arc((4, y + 4, 18, y + 22), start=270, end=90, fill=(160, 120, 70), width=2)
    if anim == "attack":
        d.line([(18, y + 10), (26 + phase, y + 6)], fill=(200, 190, 160), width=2)


def _draw_knight(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 10 + _bob(anim, phase)
    d.ellipse((6, y + 8, 26, y + 22), fill=(90, 70, 50))
    d.rectangle((18, y + 4, 26, y + 14), fill=(90, 70, 50))
    d.rectangle((12, y, 20, y + 10), fill=(160, 160, 175))
    if anim == "attack":
        d.line([(20, y + 6), (28 + phase * 2, y + 2)], fill=(200, 200, 210), width=2)
    if anim == "walk":
        d.line([(10, y + 20), (8 - phase % 2, 28)], fill=(60, 50, 40), width=2)


def _draw_ship(d: ImageDraw.ImageDraw, phase: int, anim: str, large: bool = False):
    y = 12 + _bob(anim, phase)
    w = 22 if large else 18
    d.polygon([(16 - w // 2, y + 10), (16 + w // 2, y + 10), (16 + w // 4, y + 22), (16 - w // 4, y + 22)], fill=(100, 80, 60))
    d.rectangle((14, y, 18, y + 12), fill=(180, 180, 190))
    if anim == "walk":
        d.line([(16 - w // 2, y + 14), (16 - w // 2 - 2 - phase % 2, y + 18)], fill=(120, 200, 255), width=1)


def _draw_dragon(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 10 + _bob(anim, phase)
    d.ellipse((8, y + 6, 24, y + 22), fill=(200, 70, 50))
    d.polygon([(20, y + 8), (28, y + 12), (22, y + 16)], fill=(200, 70, 50))
    d.polygon([(10, y + 4), (22, y + 2), (16, y + 10)], fill=(180, 50, 40))
    if anim == "attack":
        d.ellipse((26 + phase, y + 10, 30 + phase, y + 14), fill=(255, 180, 60))


def _draw_catapult(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 14 + _bob(anim, phase)
    d.rectangle((6, y + 10, 26, y + 18), fill=(120, 90, 50))
    d.line([(10, y + 10), (22, y + 4 - (phase if anim == "attack" else 0))], fill=(140, 110, 70), width=3)


def _draw_flyer(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 12 + _bob(anim, phase)
    d.ellipse((10, y + 8, 22, y + 18), fill=(140, 140, 160))
    wing = 4 + (phase % 2) * 2
    d.polygon([(16, y + 6), (6, y + wing), (16, y + 12)], fill=(120, 130, 180))
    d.polygon([(16, y + 6), (26, y + wing), (16, y + 12)], fill=(120, 130, 180))


def _draw_militia(d: ImageDraw.ImageDraw, phase: int, anim: str):
    _draw_humanoid(d, body=(100, 100, 120), trim=(180, 160, 90), phase=phase, anim=anim)


def _draw_scout(d: ImageDraw.ImageDraw, phase: int, anim: str):
    y = 8 + _bob(anim, phase)
    d.ellipse((12, y, 20, y + 8), fill=(210, 175, 140))
    d.polygon([(10, y + 8), (22, y + 8), (24, y + 24), (8, y + 24)], fill=(120, 90, 60))
    if anim == "walk":
        d.line([(12, y + 24), (10 - phase % 2, 28)], fill=(60, 40, 30), width=2)


def _draw_frame(type_name: str, anim: str, direction: int, frame: int) -> Image.Image:
    im = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    phase = frame

    if type_name == "peasant":
        _draw_humanoid(d, body=(120, 78, 42), trim=(140, 140, 150), phase=phase, anim=anim)
    elif type_name == "footman":
        _draw_humanoid(d, body=(70, 90, 130), trim=(200, 200, 210), phase=phase, anim=anim)
    elif type_name in ("archer",):
        _draw_archer(d, phase, anim)
    elif type_name == "knight":
        _draw_knight(d, phase, anim)
    elif type_name == "militia":
        _draw_militia(d, phase, anim)
    elif type_name == "scout":
        _draw_scout(d, phase, anim)
    elif type_name == "catapult":
        _draw_catapult(d, phase, anim)
    elif type_name == "dragon":
        _draw_dragon(d, phase, anim)
    elif type_name == "flyingmachine":
        _draw_flyer(d, phase, anim)
    elif type_name in ("boat",):
        _draw_ship(d, phase, anim, large=False)
    elif type_name in ("destroyer", "battleship"):
        _draw_ship(d, phase, anim, large=True)
    elif type_name == "mage":
        _draw_humanoid(d, body=(70, 50, 120), trim=(120, 200, 255), phase=phase, anim=anim)
    elif type_name == "priest":
        _draw_humanoid(d, body=(230, 230, 235), trim=(200, 170, 60), phase=phase, anim=anim)
    else:
        _draw_humanoid(d, body=(100, 100, 110), trim=(180, 180, 190), phase=phase, anim=anim)

    # Direction: 0=E, 1=N, 2=W, 3=S — rotate/flip east-facing art
    if direction == 1:
        im = im.transpose(Image.ROTATE_90)
    elif direction == 2:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction == 3:
        im = im.transpose(Image.ROTATE_270)
    return im


def _sheet_size() -> tuple[int, int]:
    max_frames = max(ANIM_FRAMES[a] for a in ("idle", "walk", "attack", "gather"))
    rows = max(ANIM_ROWS[a] for a in ANIM_ROWS) + DIRS
    return max_frames * FRAME_W, rows * FRAME_H


def _build_sheet(type_name: str) -> Image.Image:
    w, h = _sheet_size()
    sheet = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for anim, base_row in ANIM_ROWS.items():
        if anim == "build":
            continue
        n = ANIM_FRAMES[anim]
        for direction in range(DIRS):
            row = base_row + direction
            for frame in range(n):
                fr = _draw_frame(type_name, anim, direction, frame)
                x = frame * FRAME_W
                y = row * FRAME_H
                sheet.paste(fr, (x, y), fr)
    return sheet


def _meta_json() -> dict:
    anims = {}
    for name, row in ANIM_ROWS.items():
        anims[name] = {"row": row, "frames": ANIM_FRAMES[name]}
    return {
        "backend": "spritesheet",
        "sheet": "sheet.png",
        "frame_w": FRAME_W,
        "frame_h": FRAME_H,
        "fps": FPS,
        "dirs": DIRS,
        "animations": anims,
    }


def _write_pack(out_root: Path, type_name: str):
    pack_dir = out_root / type_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    sheet = _build_sheet(type_name)
    sheet_path = pack_dir / "sheet.png"
    sheet.save(sheet_path)
    meta_path = pack_dir / "meta.json"
    meta_path.write_text(json.dumps(_meta_json(), indent=2) + "\n", encoding="utf-8")
    print("wrote", sheet_path.relative_to(ROOT))
    print("wrote", meta_path.relative_to(ROOT))


def main():
    base = ROOT / "res" / "ui" / "anims"
    for t in BASE_MOBILE:
        _write_pack(base, t)
    aoe2 = ROOT / "mods" / "aoe2" / "ui" / "anims"
    for t in AOE2_MOBILE:
        _write_pack(aoe2, t)
    print("done")


if __name__ == "__main__":
    main()
