"""Generate AoE2 mod HUD icons (ui/icons/) and map sprites (ui/map/).

Original geometric silhouettes (not copied from any commercial game).
Run: python tools/gen_aoe2_hud_icons.py

- Order keywords are copied from res/ui/icons/ (train, attack, …)
- Unit / building / resource / wildlife types → both ui/icons and ui/map
- DE architecture sets (ui/architecture.txt): shared unit/building art per set
  under ui/icons/<set>/ and ui/map/<set>/
- Civ aliases (is_a parent) reuse the parent PNG
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mods" / "aoe2" / "ui" / "icons"
OUT_MAP = ROOT / "mods" / "aoe2" / "ui" / "map"
RULES = ROOT / "mods" / "aoe2" / "rules.txt"
RES_ICONS = ROOT / "res" / "ui" / "icons"
SIZE = 96

BG = (22, 26, 36, 255)
RIM = (196, 168, 84, 255)
RIM_INNER = (60, 68, 88, 255)

NEUTRAL_TYPES = set()

DEFAULT_STYLE = {
    "kit": "western",
    "rim": RIM[:3],
    "armor": (70, 90, 130),
    "tunic": (120, 78, 42),
    "horse": (90, 70, 50),
    "wood": (140, 110, 70),
    "roof": (160, 60, 50),
    "stone": (110, 110, 120),
    "tab": (160, 40, 40),
}

ARCH_FILE = ROOT / "mods" / "aoe2" / "ui" / "architecture.txt"

_STYLE = dict(DEFAULT_STYLE)

VISUAL_CLASSES = {
    "worker",
    "soldier",
    "building",
    "deposit",
    "item",
    "building_land",
}
ABSTRACT_PARENTS = {
    "infantry",
    "cavalry",
    "archer_unit",
    "siege_unit",
    "unique_unit",
    "building",
    "ship",
}

ORDER_KEYWORDS = (
    "train",
    "build",
    "research",
    "attack",
    "stop",
    "patrol",
    "repair",
    "gather",
    "rallying_point",
    "cancel_training",
    "cancel_upgrading",
    "cancel_changing",
    "cancel_building",
    "advance",
    "upgrade_to",
)

_written: dict[str, Image.Image] = {}


def new_canvas():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rim = tuple(_STYLE.get("rim", RIM[:3])) + (255,)
    d.rounded_rectangle((2, 2, SIZE - 3, SIZE - 3), radius=10, fill=BG)
    d.rounded_rectangle((2, 2, SIZE - 3, SIZE - 3), radius=10, outline=rim, width=3)
    d.rounded_rectangle((6, 6, SIZE - 7, SIZE - 7), radius=8, outline=RIM_INNER, width=1)
    tab = _STYLE.get("tab")
    if tab:
        d.rectangle((8, 18, 14, 78), fill=tuple(tab))
    return im, d


def mark_rank(d: ImageDraw.ImageDraw, rank: int):
    if rank <= 0:
        return
    for i in range(min(rank, 4)):
        x = 12 + i * 9
        d.polygon([(x, 16), (x + 5, 8), (x + 10, 16)], fill=(220, 180, 50))


def save(name: str, im: Image.Image, *, map_too: bool = True, icons_dir=None, map_dir=None, written=None):
    icons_dir = icons_dir or OUT
    map_dir = map_dir or OUT_MAP
    written = written if written is not None else _written
    icons_dir.mkdir(parents=True, exist_ok=True)
    im.save(icons_dir / f"{name}.png")
    written[name] = im
    if map_too:
        map_dir.mkdir(parents=True, exist_ok=True)
        im.save(map_dir / f"{name}.png")


def copy_as(src_name: str, dest_name: str, *, map_too: bool = True, icons_dir=None, map_dir=None, written=None):
    written = written if written is not None else _written
    im = written.get(src_name)
    if im is None:
        return False
    save(
        dest_name,
        im.copy(),
        map_too=map_too,
        icons_dir=icons_dir,
        map_dir=map_dir,
        written=written,
    )
    return True


# --- shared body parts ---


def _head(d, x=38, y=16, w=20, h=20, skin=(210, 175, 140)):
    d.ellipse((x, y, x + w, y + h), fill=skin)


def _tunic(d, color, top=36):
    d.polygon([(30, top), (66, top), (72, 78), (24, 78)], fill=color)


# --- units ---


def villager(rank=0, accent=None):
    im, d = new_canvas()
    _head(d)
    _tunic(d, accent or _STYLE["tunic"])
    d.line([(58, 48), (78, 28)], fill=(160, 160, 170), width=4)
    d.rectangle((72, 20, 84, 30), fill=(140, 140, 150))
    mark_rank(d, rank)
    return im


def infantry_sword(rank=0, armor=None):
    im, d = new_canvas()
    armor = armor or _STYLE["armor"]
    _head(d, y=14)
    d.rectangle((34, 34, 62, 74), fill=armor)
    if _STYLE.get("kit") == "meso":
        d.line([(58, 42), (80, 24)], fill=(200, 180, 80), width=5)
        d.polygon([(76, 18), (88, 28), (74, 32)], fill=(200, 180, 80))
    else:
        d.ellipse((16, 40, 42, 70), fill=(armor[0] + 20, armor[1] + 20, armor[2] + 20))
        d.line([(62, 40), (80, 24)], fill=(200, 200, 210), width=4)
        d.polygon([(78, 18), (86, 24), (78, 30)], fill=(200, 200, 210))
    mark_rank(d, rank)
    return im


def spear_line(rank=0):
    im, d = new_canvas()
    _head(d, y=18)
    _tunic(d, (80, 90, 70), top=38)
    d.line([(52, 78), (78, 16)], fill=(180, 160, 90), width=3)
    d.polygon([(74, 12), (86, 18), (76, 24)], fill=(180, 180, 190))
    if rank >= 1:
        d.polygon([(70, 20), (86, 22), (72, 30)], fill=(160, 160, 170))
    if rank >= 2:
        d.polygon([(48, 44), (70, 36), (52, 56)], fill=(90, 100, 80))
    mark_rank(d, rank)
    return im


def archer_line(rank=0, tunic=(40, 90, 50)):
    im, d = new_canvas()
    _head(d, x=40, y=16, w=18, h=18)
    d.polygon([(36, 34), (62, 34), (66, 74), (32, 74)], fill=tunic)
    d.arc((16, 26, 48, 78), start=270, end=90, fill=(160, 120, 70), width=4)
    d.line([(32, 28), (32, 76)], fill=(200, 190, 160), width=2)
    if rank >= 1:
        d.rectangle((44, 48, 58, 56), fill=(90, 70, 40))
    if rank >= 2:
        d.line([(20, 40), (44, 48)], fill=(180, 180, 190), width=2)
    mark_rank(d, rank)
    return im


def skirm_line(rank=0):
    im, d = new_canvas()
    _head(d, x=40, y=16, w=18, h=18)
    d.polygon([(34, 34), (64, 34), (70, 76), (28, 76)], fill=(140, 110, 60))
    d.line([(22, 30), (40, 70)], fill=(160, 120, 70), width=3)
    d.ellipse((18, 24, 28, 34), fill=(180, 140, 80))
    mark_rank(d, rank)
    return im


def horse_body(d, color=None):
    color = color or _STYLE["horse"]
    d.ellipse((16, 48, 70, 78), fill=color)
    d.rectangle((62, 40, 78, 60), fill=color)
    d.ellipse((72, 32, 88, 48), fill=color)


def rider_horse(rank=0, horse=(90, 70, 50), rider=(160, 160, 175), bow=False):
    im, d = new_canvas()
    horse_body(d, horse)
    d.rectangle((36, 26, 54, 54), fill=rider)
    _head(d, x=38, y=14, w=14, h=14, skin=rider if rider[0] > 140 else (210, 175, 140))
    if bow:
        d.arc((52, 20, 82, 56), start=200, end=40, fill=(160, 120, 70), width=3)
    else:
        d.line([(54, 34), (78, 16)], fill=(200, 200, 210), width=3)
    mark_rank(d, rank)
    return im


def camel_line(rank=0):
    im, d = new_canvas()
    d.ellipse((18, 50, 68, 78), fill=(180, 140, 80))
    d.rectangle((58, 34, 72, 56), fill=(180, 140, 80))
    d.ellipse((66, 22, 86, 42), fill=(180, 140, 80))
    d.rectangle((36, 28, 52, 54), fill=(80, 90, 70))
    _head(d, x=38, y=16, w=14, h=14)
    d.line([(52, 36), (74, 18)], fill=(200, 200, 210), width=3)
    mark_rank(d, rank)
    return im


def elephant_line(rank=0, armor=False, howdah=(140, 90, 50)):
    im, d = new_canvas()
    body = (110, 110, 100) if armor else (130, 130, 120)
    d.ellipse((12, 40, 78, 80), fill=body)
    d.ellipse((64, 28, 88, 56), fill=body)
    d.polygon([(78, 48), (90, 70), (72, 62)], fill=body)
    d.rectangle((30, 28, 56, 48), fill=howdah)
    _head(d, x=36, y=16, w=14, h=14)
    mark_rank(d, rank)
    return im


def eagle_line(rank=0):
    im, d = new_canvas()
    _head(d, y=18)
    _tunic(d, (70, 50, 40), top=38)
    d.polygon([(18, 50), (48, 28), (78, 50), (70, 44), (48, 34), (26, 44)], fill=(200, 190, 170))
    d.line([(60, 48), (80, 28)], fill=(160, 140, 80), width=3)
    mark_rank(d, rank)
    return im


def jaguar_line(rank=0):
    im, d = new_canvas()
    _head(d, y=16)
    _tunic(d, (180, 120, 40), top=36)
    d.ellipse((28, 48, 44, 64), fill=(40, 30, 20))
    d.ellipse((52, 48, 68, 64), fill=(40, 30, 20))
    d.line([(62, 42), (80, 24)], fill=(180, 160, 90), width=4)
    mark_rank(d, rank)
    return im


def monk_line(rank=0, missionary=False):
    im, d = new_canvas()
    _head(d)
    robe = (70, 80, 160) if missionary else (230, 230, 235)
    d.polygon([(28, 40), (68, 40), (74, 82), (22, 82)], fill=robe)
    d.rectangle((44, 48, 52, 72), fill=(200, 170, 60))
    d.rectangle((36, 54, 60, 62), fill=(200, 170, 60))
    if missionary:
        d.ellipse((18, 50, 42, 74), fill=(160, 140, 70))
    mark_rank(d, rank)
    return im


def unique_melee(rank=0, tunic=(90, 70, 50), extra="axe"):
    im, d = new_canvas()
    _head(d)
    _tunic(d, tunic)
    if extra == "axe":
        d.line([(58, 50), (78, 24)], fill=(140, 120, 80), width=4)
        d.polygon([(72, 16), (88, 22), (74, 32)], fill=(160, 160, 170))
    elif extra == "katana":
        d.line([(58, 48), (82, 18)], fill=(200, 200, 210), width=3)
        d.rectangle((34, 36, 62, 48), fill=(180, 40, 40))
    elif extra == "club":
        d.line([(56, 50), (80, 26)], fill=(120, 80, 40), width=6)
    elif extra == "throw":
        d.ellipse((68, 20, 84, 36), fill=(180, 160, 70))
        d.line([(58, 48), (72, 30)], fill=(140, 110, 60), width=3)
    mark_rank(d, rank)
    return im


def teuton_line(rank=0):
    im, d = new_canvas()
    _head(d, skin=(180, 180, 190))
    d.rectangle((32, 34, 64, 76), fill=(70, 70, 80))
    d.polygon([(28, 34), (48, 18), (68, 34)], fill=(70, 70, 80))
    d.line([(64, 44), (82, 22)], fill=(200, 200, 210), width=5)
    mark_rank(d, rank)
    return im


def cataphract_line(rank=0):
    return rider_horse(rank, horse=(90, 90, 80), rider=(160, 160, 140))


def rattan_line(rank=0):
    return archer_line(rank, tunic=(60, 120, 70))


def chukonu_line(rank=0):
    im, d = new_canvas()
    _head(d, x=40, y=16, w=18, h=18)
    d.polygon([(36, 34), (62, 34), (66, 74), (32, 74)], fill=(140, 50, 50))
    d.rectangle((18, 40, 48, 50), fill=(90, 70, 40))
    d.line([(18, 36), (18, 54)], fill=(160, 140, 90), width=3)
    mark_rank(d, rank)
    return im


def organ_line(rank=0):
    im, d = new_canvas()
    d.rectangle((18, 54, 78, 74), fill=(120, 90, 50))
    d.ellipse((20, 68, 36, 84), fill=(60, 50, 40))
    d.ellipse((60, 68, 76, 84), fill=(60, 50, 40))
    for i in range(5):
        x = 28 + i * 8
        d.rectangle((x, 28, x + 5, 56), fill=(70, 70, 80))
    mark_rank(d, rank)
    return im


def ram_line(rank=0):
    im, d = new_canvas()
    d.rectangle((16, 44, 80, 70), fill=(120, 90, 50))
    d.polygon([(70, 44), (88, 56), (70, 68)], fill=(90, 70, 40))
    d.ellipse((20, 64, 38, 82), fill=(60, 50, 40))
    d.ellipse((58, 64, 76, 82), fill=(60, 50, 40))
    if rank >= 1:
        d.rectangle((22, 36, 74, 46), fill=(90, 90, 95))
    mark_rank(d, rank)
    return im


def mangonel_line(rank=0):
    im, d = new_canvas()
    d.rectangle((20, 58, 76, 72), fill=(120, 90, 50))
    d.ellipse((22, 68, 40, 84), fill=(60, 50, 40))
    d.ellipse((56, 68, 74, 84), fill=(60, 50, 40))
    d.line([(30, 58), (70, 26)], fill=(140, 110, 70), width=5)
    ball = (90, 90, 100) if rank < 2 else (50, 50, 55)
    d.ellipse((64, 16, 82, 34), fill=ball)
    mark_rank(d, rank)
    return im


def scorpion_line(rank=0):
    im, d = new_canvas()
    d.rectangle((22, 50, 74, 70), fill=(120, 95, 55))
    d.rectangle((48, 28, 82, 42), fill=(80, 70, 50))
    d.polygon([(78, 24), (90, 34), (78, 44)], fill=(180, 180, 190))
    mark_rank(d, rank)
    return im


def bombard_line(rank=0):
    im, d = new_canvas()
    d.rectangle((18, 52, 70, 74), fill=(70, 70, 80))
    d.ellipse((16, 64, 34, 82), fill=(50, 50, 55))
    d.ellipse((52, 64, 70, 82), fill=(50, 50, 55))
    d.rectangle((50, 40, 88, 54), fill=(50, 50, 55))
    mark_rank(d, rank)
    return im


def siege_tower_icon():
    im, d = new_canvas()
    d.rectangle((28, 22, 68, 78), fill=(120, 100, 60))
    d.rectangle((22, 16, 74, 28), fill=(100, 80, 50))
    d.rectangle((36, 32, 60, 48), fill=(40, 40, 45))
    d.rectangle((40, 56, 56, 78), fill=(50, 40, 30))
    return im


def trebuchet_icon():
    im, d = new_canvas()
    d.polygon([(20, 78), (48, 70), (76, 78), (70, 84), (26, 84)], fill=(110, 80, 45))
    d.line([(48, 72), (72, 22)], fill=(140, 110, 70), width=5)
    d.ellipse((68, 12, 86, 30), fill=(80, 80, 90))
    d.line([(48, 72), (30, 40)], fill=(140, 110, 70), width=3)
    return im


def petard_icon():
    im, d = new_canvas()
    _head(d)
    _tunic(d, (80, 70, 50))
    d.ellipse((58, 40, 82, 66), fill=(70, 70, 75))
    d.line([(70, 40), (78, 24)], fill=(180, 160, 80), width=2)
    return im


def hand_cannon_icon(rank=0):
    im, d = new_canvas()
    _head(d)
    _tunic(d, (70, 80, 70))
    d.rectangle((56, 44, 86, 54), fill=(50, 50, 55))
    d.ellipse((50, 42, 62, 56), fill=(90, 70, 40))
    mark_rank(d, rank)
    return im


def condottiero_icon():
    im, d = new_canvas()
    _head(d)
    d.rectangle((34, 36, 62, 74), fill=(90, 90, 100))
    d.polygon([(30, 36), (48, 22), (66, 36)], fill=(90, 90, 100))
    d.line([(62, 42), (80, 24)], fill=(200, 200, 210), width=4)
    return im


def fishing_ship_icon():
    im, d = new_canvas()
    d.polygon([(16, 58), (80, 58), (72, 76), (24, 76)], fill=(110, 80, 50))
    d.line([(48, 58), (48, 24)], fill=(160, 140, 90), width=3)
    d.polygon([(48, 24), (70, 48), (48, 52)], fill=(220, 220, 230))
    d.ellipse((28, 66, 44, 78), fill=(40, 90, 150))
    return im


def ship_line(rank=0, kind="galley"):
    im, d = new_canvas()
    hull = (70, 80, 95)
    if kind == "fire":
        hull = (160, 70, 40)
    elif kind == "demo":
        hull = (80, 60, 50)
    elif kind == "cannon":
        hull = (60, 70, 85)
    elif kind == "turtle":
        hull = (70, 90, 70)
    elif kind == "longboat":
        hull = (110, 80, 50)
    elif kind == "caravel":
        hull = (90, 90, 100)
    elif kind == "dromon":
        hull = (80, 70, 55)
    elif kind == "transport":
        hull = (100, 85, 60)
    d.polygon([(10, 56), (86, 56), (76, 78), (20, 78)], fill=hull)
    if kind in ("galley", "caravel", "longboat", "transport"):
        d.line([(48, 56), (48, 22)], fill=(160, 140, 90), width=3)
        d.polygon([(48, 22), (70, 46), (48, 50)], fill=(220, 220, 230))
    if kind == "fire":
        d.polygon([(40, 28), (56, 44), (32, 44)], fill=(255, 140, 40))
    if kind == "cannon":
        d.rectangle((54, 40, 82, 50), fill=(50, 50, 55))
    if kind == "turtle":
        d.ellipse((28, 36, 68, 62), fill=(50, 80, 55))
    if kind == "dromon":
        d.ellipse((60, 36, 78, 50), fill=(255, 160, 50))
    if kind == "demo":
        d.ellipse((40, 38, 58, 54), fill=(70, 70, 75))
    mark_rank(d, rank)
    return im


def trade_cart_icon():
    im, d = new_canvas()
    horse_body(d, (90, 70, 50))
    d.rectangle((18, 40, 50, 70), fill=(140, 110, 70))
    d.rectangle((22, 44, 46, 58), fill=(180, 150, 90))
    return im


# --- buildings / resources ---


def town_center_icon():
    im, d = new_canvas()
    kit = _STYLE.get("kit", "western")
    wood, roof, stone = _STYLE["wood"], _STYLE["roof"], _STYLE["stone"]
    if kit == "meso":
        d.polygon([(14, 80), (48, 16), (82, 80)], fill=stone)
        d.polygon([(24, 80), (48, 36), (72, 80)], fill=(stone[0] - 20, stone[1] - 20, stone[2] - 20))
        d.rectangle((40, 56, 56, 80), fill=(40, 30, 20))
    elif kit == "east":
        d.rectangle((26, 48, 70, 78), fill=wood)
        d.polygon([(14, 50), (48, 18), (82, 50)], fill=roof)
        d.polygon([(20, 50), (48, 28), (76, 50)], fill=(roof[0] + 20, roof[1] + 10, roof[2] + 10))
        d.rectangle((42, 56, 54, 78), fill=(50, 30, 25))
    elif kit == "yurt":
        d.ellipse((18, 28, 78, 80), fill=wood)
        d.polygon([(48, 16), (70, 40), (26, 40)], fill=roof)
        d.rectangle((42, 52, 54, 78), fill=(50, 30, 20))
    elif kit == "med":
        d.rectangle((22, 48, 74, 78), fill=stone)
        d.ellipse((28, 18, 68, 58), fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(80, 50, 40))
        d.rectangle((28, 52, 38, 62), fill=(180, 200, 220))
        d.rectangle((58, 52, 68, 62), fill=(180, 200, 220))
    elif kit == "african":
        d.ellipse((20, 36, 76, 80), fill=stone)
        d.polygon([(24, 48), (48, 18), (72, 48)], fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(70, 50, 30))
    elif kit == "sea":
        d.rectangle((24, 48, 72, 78), fill=wood)
        d.polygon([(18, 50), (48, 10), (78, 50)], fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(50, 35, 25))
    elif kit == "central":
        d.rectangle((22, 38, 74, 78), fill=stone)
        d.polygon([(18, 40), (48, 14), (78, 40)], fill=roof)
        d.rectangle((40, 52, 56, 78), fill=(40, 35, 30))
        for x in (22, 34, 58, 70):
            d.rectangle((x, 30, x + 8, 40), fill=stone)
    else:
        d.rectangle((20, 40, 76, 78), fill=wood)
        d.polygon([(16, 42), (48, 14), (80, 42)], fill=roof)
        d.rectangle((40, 52, 56, 78), fill=(60, 45, 30))
        d.rectangle((26, 48, 36, 58), fill=(180, 200, 220))
        d.rectangle((60, 48, 70, 58), fill=(180, 200, 220))
    return im


def house_icon():
    im, d = new_canvas()
    kit = _STYLE.get("kit", "western")
    wood, roof, stone = _STYLE["wood"], _STYLE["roof"], _STYLE["stone"]
    if kit == "meso":
        d.rectangle((24, 44, 72, 78), fill=stone)
        d.polygon([(20, 46), (48, 22), (76, 46)], fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(40, 30, 20))
    elif kit == "yurt":
        d.ellipse((22, 32, 74, 80), fill=wood)
        d.ellipse((36, 28, 60, 48), fill=roof)
    elif kit == "east":
        d.rectangle((26, 50, 70, 78), fill=wood)
        d.polygon([(16, 52), (48, 20), (80, 52)], fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(50, 30, 25))
    elif kit == "african":
        d.ellipse((22, 40, 74, 80), fill=stone)
        d.polygon([(28, 48), (48, 22), (68, 48)], fill=roof)
        d.rectangle((42, 58, 54, 78), fill=(70, 50, 30))
    elif kit == "med":
        d.rectangle((24, 48, 72, 78), fill=stone)
        d.rectangle((20, 42, 76, 52), fill=roof)
        d.rectangle((42, 56, 54, 78), fill=(80, 50, 40))
    elif kit == "sea":
        d.rectangle((26, 52, 70, 78), fill=wood)
        d.polygon([(18, 54), (48, 16), (78, 54)], fill=roof)
        d.rectangle((42, 58, 54, 78), fill=(50, 35, 25))
    else:
        d.polygon([(18, 50), (48, 22), (78, 50)], fill=roof)
        d.rectangle((24, 50, 72, 78), fill=wood)
        d.rectangle((42, 56, 54, 78), fill=(90, 60, 40))
    return im


def farm_icon():
    im, d = new_canvas()
    d.rectangle((16, 40, 80, 78), fill=(90, 140, 50))
    for y in (48, 58, 68):
        d.line([(20, y), (76, y)], fill=(70, 110, 40), width=3)
    d.polygon([(50, 28), (78, 50), (54, 50)], fill=(160, 70, 50))
    return im


def pasture_icon():
    im, d = new_canvas()
    d.rectangle((16, 48, 80, 78), fill=(80, 130, 55))
    d.ellipse((30, 36, 66, 62), fill=(220, 220, 210))
    d.ellipse((54, 32, 70, 48), fill=(220, 220, 210))
    return im


def mill_icon():
    im, d = new_canvas()
    d.rectangle((36, 40, 60, 78), fill=(150, 130, 80))
    d.ellipse((22, 18, 74, 70), fill=(200, 190, 160))
    d.polygon([(48, 20), (70, 44), (48, 48), (26, 44)], fill=(180, 170, 140))
    d.polygon([(48, 68), (70, 44), (48, 48), (26, 44)], fill=(160, 150, 120))
    return im


def lumbermill_icon():
    im, d = new_canvas()
    d.rectangle((20, 44, 70, 76), fill=(130, 100, 60))
    d.polygon([(16, 46), (46, 24), (74, 46)], fill=(90, 70, 40))
    d.ellipse((22, 70, 48, 86), fill=(100, 70, 40))
    d.ellipse((40, 70, 66, 86), fill=(110, 80, 45))
    d.ellipse((58, 36, 82, 60), fill=(160, 160, 170))
    return im


def mining_camp_icon():
    im, d = new_canvas()
    d.polygon([(16, 70), (30, 34), (48, 48), (66, 28), (80, 70)], fill=(90, 90, 95))
    d.rectangle((28, 48, 68, 78), fill=(120, 100, 70))
    d.ellipse((44, 36, 56, 48), fill=(220, 180, 40))
    return im


def market_icon():
    im, d = new_canvas()
    d.rectangle((20, 48, 76, 78), fill=(160, 130, 70))
    d.polygon([(16, 50), (48, 22), (80, 50)], fill=(180, 60, 50))
    d.rectangle((40, 56, 56, 78), fill=(80, 50, 30))
    d.ellipse((28, 54, 40, 66), fill=(220, 180, 40))
    return im


def feitoria_icon():
    im, d = new_canvas()
    d.rectangle((18, 40, 78, 78), fill=(110, 100, 80))
    d.rectangle((18, 22, 34, 78), fill=(90, 80, 65))
    d.rectangle((62, 22, 78, 78), fill=(90, 80, 65))
    d.polygon([(20, 70), (76, 70), (70, 84), (26, 84)], fill=(40, 90, 150))
    return im


def barracks_icon():
    im, d = new_canvas()
    wood, roof = _STYLE["wood"], _STYLE["roof"]
    d.rectangle((18, 36, 78, 78), fill=wood)
    d.rectangle((18, 28, 78, 40), fill=(wood[0] - 20, wood[1] - 10, wood[2] - 5))
    d.rectangle((40, 50, 56, 78), fill=(50, 40, 30))
    d.line([(30, 20), (30, 36)], fill=(180, 180, 180), width=2)
    d.polygon([(30, 20), (48, 26), (30, 32)], fill=roof)
    return im


def archery_range_icon():
    im, d = new_canvas()
    d.rectangle((18, 48, 78, 78), fill=(70, 100, 55))
    d.arc((20, 24, 56, 76), start=270, end=90, fill=(160, 120, 70), width=5)
    d.line([(38, 28), (70, 36)], fill=(200, 190, 160), width=2)
    return im


def blacksmith_icon():
    im, d = new_canvas()
    d.rectangle((24, 48, 72, 78), fill=(90, 70, 50))
    d.polygon([(20, 50), (48, 28), (76, 50)], fill=(70, 60, 50))
    d.rectangle((32, 58, 64, 70), fill=(70, 70, 80))
    d.rectangle((40, 50, 56, 58), fill=(70, 70, 80))
    d.ellipse((58, 40, 68, 50), fill=(255, 180, 60))
    return im


def stables_icon():
    im, d = new_canvas()
    d.rectangle((18, 44, 78, 78), fill=(120, 95, 60))
    d.polygon([(14, 46), (48, 22), (82, 46)], fill=(100, 75, 45))
    d.ellipse((30, 52, 66, 74), fill=(90, 70, 50))
    d.ellipse((58, 48, 72, 62), fill=(90, 70, 50))
    return im


def workshop_icon():
    im, d = new_canvas()
    d.rectangle((20, 40, 76, 78), fill=(110, 100, 70))
    d.rectangle((20, 32, 76, 44), fill=(80, 80, 70))
    d.ellipse((36, 48, 60, 72), fill=(160, 160, 100))
    d.ellipse((42, 54, 54, 66), fill=(110, 100, 70))
    return im


def shipyard_icon():
    im, d = new_canvas()
    d.polygon([(18, 58), (48, 40), (78, 58), (70, 78), (26, 78)], fill=(100, 80, 55))
    d.rectangle((40, 28, 56, 58), fill=(140, 120, 80))
    d.polygon([(20, 70), (76, 70), (70, 84), (26, 84)], fill=(40, 90, 150))
    return im


def fish_trap_icon():
    im, d = new_canvas()
    d.ellipse((18, 28, 78, 78), fill=(40, 90, 140))
    d.arc((26, 36, 70, 70), start=0, end=360, fill=(180, 160, 90), width=3)
    d.line([(48, 36), (48, 70)], fill=(180, 160, 90), width=2)
    d.line([(30, 52), (66, 52)], fill=(180, 160, 90), width=2)
    return im


def wall_icon(fortified=False, palisade=False):
    im, d = new_canvas()
    if palisade:
        for x in (20, 34, 48, 62, 76):
            d.rectangle((x - 6, 28, x + 6, 78), fill=(120, 90, 50))
            d.polygon([(x - 6, 28), (x, 16), (x + 6, 28)], fill=(100, 75, 40))
    else:
        color = (80, 80, 90) if fortified else (110, 110, 120)
        d.rectangle((14, 40, 82, 78), fill=color)
        for x in (18, 34, 50, 66):
            d.rectangle((x, 28, x + 12, 42), fill=color)
    return im


def gate_icon(fortified=False, palisade=False):
    im, d = new_canvas()
    color = (120, 90, 50) if palisade else ((70, 70, 80) if fortified else (100, 100, 110))
    d.rectangle((18, 28, 78, 78), fill=color)
    d.polygon([(30, 78), (48, 44), (66, 78)], fill=(40, 30, 25))
    return im


def outpost_icon():
    im, d = new_canvas()
    d.polygon([(32, 78), (48, 18), (64, 78)], fill=(120, 110, 90))
    d.rectangle((42, 28, 54, 42), fill=(160, 200, 220))
    return im


def tower_icon(kind="scout"):
    im, d = new_canvas()
    if kind == "scout":
        d.polygon([(30, 78), (48, 18), (66, 78)], fill=(120, 110, 90))
        d.rectangle((40, 34, 56, 50), fill=(160, 200, 220))
        d.rectangle((36, 18, 60, 28), fill=(140, 60, 50))
    elif kind == "cannon":
        d.rectangle((30, 36, 66, 78), fill=(90, 90, 95))
        d.rectangle((26, 28, 70, 40), fill=(80, 80, 85))
        d.rectangle((48, 34, 82, 46), fill=(50, 50, 55))
    else:
        d.rectangle((32, 28, 64, 78), fill=(100, 100, 110))
        d.rectangle((28, 20, 68, 32), fill=(90, 90, 100))
        d.rectangle((38, 36, 58, 52), fill=(50, 50, 55))
        d.rectangle((42, 60, 54, 78), fill=(50, 40, 35))
        if kind == "keep":
            d.rectangle((36, 12, 44, 22), fill=(90, 90, 100))
            d.rectangle((52, 12, 60, 22), fill=(90, 90, 100))
    return im


def university_icon():
    im, d = new_canvas()
    d.rectangle((22, 48, 74, 78), fill=(200, 200, 210))
    d.polygon([(18, 50), (48, 18), (78, 50)], fill=(160, 80, 50))
    d.rectangle((42, 56, 54, 78), fill=(90, 70, 40))
    d.ellipse((40, 28, 56, 44), fill=(120, 200, 255))
    return im


def monastery_icon():
    im, d = new_canvas()
    d.rectangle((24, 48, 72, 78), fill=(220, 220, 225))
    d.polygon([(20, 50), (48, 22), (76, 50)], fill=(200, 180, 80))
    d.rectangle((44, 28, 52, 42), fill=(200, 180, 80))
    d.rectangle((40, 56, 56, 78), fill=(120, 100, 60))
    return im


def castle_icon():
    im, d = new_canvas()
    kit = _STYLE.get("kit", "western")
    stone, roof, wood = _STYLE["stone"], _STYLE["roof"], _STYLE["wood"]
    if kit == "meso":
        d.polygon([(12, 80), (48, 14), (84, 80)], fill=stone)
        d.polygon([(26, 80), (48, 40), (70, 80)], fill=(stone[0] - 25, stone[1] - 25, stone[2] - 20))
        d.rectangle((40, 58, 56, 80), fill=(40, 28, 18))
    elif kit == "east":
        d.rectangle((28, 44, 68, 78), fill=wood)
        d.polygon([(16, 46), (48, 16), (80, 46)], fill=roof)
        d.polygon([(22, 46), (48, 26), (74, 46)], fill=(min(255, roof[0] + 25), roof[1], roof[2]))
        d.rectangle((42, 56, 54, 78), fill=(50, 30, 25))
    elif kit == "yurt":
        d.ellipse((14, 36, 82, 82), fill=wood)
        d.polygon([(48, 14), (78, 44), (18, 44)], fill=roof)
        d.rectangle((40, 56, 56, 78), fill=(50, 30, 20))
    elif kit == "african":
        d.rectangle((20, 48, 76, 78), fill=stone)
        d.polygon([(16, 50), (48, 18), (80, 50)], fill=roof)
        d.rectangle((18, 22, 32, 78), fill=stone)
        d.rectangle((64, 22, 78, 78), fill=stone)
    elif kit == "sea":
        d.rectangle((20, 44, 76, 78), fill=wood)
        d.polygon([(14, 46), (48, 12), (82, 46)], fill=roof)
        d.rectangle((18, 28, 32, 78), fill=wood)
        d.rectangle((64, 28, 78, 78), fill=wood)
    else:
        d.rectangle((18, 40, 78, 78), fill=stone)
        d.rectangle((18, 18, 34, 78), fill=(stone[0] - 10, stone[1] - 10, stone[2] - 10))
        d.rectangle((62, 18, 78, 78), fill=(stone[0] - 10, stone[1] - 10, stone[2] - 10))
        for x in (18, 26, 62, 70):
            d.rectangle((x, 12, x + 6, 20), fill=stone)
        d.rectangle((38, 52, 58, 78), fill=(50, 40, 35))
    return im


def goldmine_icon():
    im, d = new_canvas()
    d.polygon([(16, 70), (30, 30), (48, 44), (66, 26), (80, 70)], fill=(90, 90, 95))
    d.ellipse((34, 48, 62, 76), fill=(30, 28, 28))
    d.ellipse((44, 40, 56, 52), fill=(220, 180, 40))
    return im


def wood_icon():
    im, d = new_canvas()
    d.rectangle((42, 48, 54, 80), fill=(110, 80, 45))
    d.ellipse((24, 18, 72, 58), fill=(40, 110, 50))
    d.ellipse((18, 32, 50, 62), fill=(36, 100, 46))
    return im


def stone_mine_icon():
    im, d = new_canvas()
    d.polygon([(14, 74), (28, 34), (48, 50), (70, 28), (84, 74)], fill=(130, 130, 135))
    d.polygon([(32, 52), (48, 36), (62, 56)], fill=(160, 160, 165))
    return im


def orchard_icon():
    im, d = new_canvas()
    d.ellipse((20, 22, 76, 70), fill=(50, 120, 55))
    d.ellipse((36, 36, 48, 48), fill=(200, 60, 50))
    d.ellipse((52, 40, 64, 52), fill=(200, 60, 50))
    d.rectangle((42, 64, 54, 80), fill=(110, 80, 45))
    return im


def fish_icon(deep=False):
    im, d = new_canvas()
    water = (30, 70, 130) if deep else (50, 110, 160)
    d.ellipse((14, 22, 82, 78), fill=water)
    d.polygon([(24, 48), (58, 32), (58, 64)], fill=(220, 180, 80))
    d.polygon([(58, 40), (78, 32), (78, 56), (58, 48)], fill=(200, 160, 70))
    return im


def carcass_icon():
    im, d = new_canvas()
    d.ellipse((20, 40, 76, 74), fill=(140, 90, 60))
    d.ellipse((62, 32, 82, 52), fill=(140, 90, 60))
    d.polygon([(24, 36), (40, 22), (44, 40)], fill=(160, 110, 70))
    return im


def livestock_icon():
    im, d = new_canvas()
    d.ellipse((22, 40, 74, 76), fill=(230, 230, 220))
    d.ellipse((58, 28, 78, 48), fill=(230, 230, 220))
    d.ellipse((28, 56, 40, 68), fill=(40, 40, 40))
    return im


def relic_icon():
    im, d = new_canvas()
    d.ellipse((28, 22, 68, 78), fill=(180, 150, 50))
    d.ellipse((36, 30, 60, 70), fill=(40, 40, 50))
    d.rectangle((44, 38, 52, 62), fill=(220, 190, 80))
    return im


def deer_icon():
    im, d = new_canvas()
    d.ellipse((18, 48, 70, 76), fill=(140, 100, 55))
    d.ellipse((62, 32, 82, 52), fill=(140, 100, 55))
    d.line([(70, 32), (64, 16)], fill=(160, 130, 80), width=2)
    d.line([(74, 32), (84, 16)], fill=(160, 130, 80), width=2)
    return im


def sheep_icon():
    return livestock_icon()


def boar_icon():
    im, d = new_canvas()
    d.ellipse((16, 44, 74, 78), fill=(90, 70, 50))
    d.ellipse((64, 36, 88, 60), fill=(90, 70, 50))
    d.polygon([(80, 48), (92, 44), (82, 56)], fill=(220, 220, 210))
    return im


def meadow_icon():
    im, d = new_canvas()
    d.rectangle((14, 40, 82, 78), fill=(70, 140, 60))
    d.line([(20, 52), (40, 44)], fill=(50, 110, 45), width=3)
    d.line([(36, 66), (60, 50)], fill=(50, 110, 45), width=3)
    return im


def keep_icon():
    im, d = new_canvas()
    d.rectangle((28, 30, 68, 78), fill=(120, 120, 130))
    for x in (28, 40, 52, 64):
        d.rectangle((x, 22, x + 8, 32), fill=(120, 120, 130))
    d.rectangle((40, 50, 56, 78), fill=(50, 45, 40))
    return im


def generic_icon(kind: str, name: str):
    im, d = new_canvas()
    colors = {
        "worker": (120, 78, 42),
        "soldier": (70, 90, 130),
        "building": (140, 110, 70),
        "deposit": (90, 90, 95),
        "item": (180, 150, 50),
        "building_land": (70, 140, 60),
    }
    c = colors.get(kind, (55, 60, 72))
    d.rounded_rectangle((18, 18, 78, 78), radius=8, fill=c)
    letter = next((ch.upper() for ch in name if ch.isalnum()), "?")
    d.text((42, 38), letter, fill=(245, 248, 255))
    return im


CANONICAL = {
    "peasant": lambda: villager(),
    "militia": lambda: infantry_sword(0, (90, 90, 100)),
    "man_at_arms": lambda: infantry_sword(1, (80, 90, 120)),
    "long_swordsman": lambda: infantry_sword(2, (70, 90, 130)),
    "two_handed_swordsman": lambda: infantry_sword(3, (60, 80, 120)),
    "champion": lambda: infantry_sword(4, (50, 70, 110)),
    "spearman": lambda: spear_line(0),
    "pikeman": lambda: spear_line(1),
    "halberdier": lambda: spear_line(2),
    "aoe_archer": lambda: archer_line(0),
    "crossbowman": lambda: archer_line(1),
    "arbalester": lambda: archer_line(2),
    "skirmisher": lambda: skirm_line(0),
    "elite_skirmisher": lambda: skirm_line(1),
    "imperial_skirmisher": lambda: skirm_line(2),
    "cavalry_archer": lambda: rider_horse(0, bow=True),
    "heavy_cavalry_archer": lambda: rider_horse(1, bow=True),
    "mongol_cavalry_archer": lambda: rider_horse(0, horse=(70, 55, 40), bow=True),
    "scout_cavalry": lambda: rider_horse(0, rider=(120, 90, 50)),
    "light_cavalry": lambda: rider_horse(1, rider=(120, 90, 50)),
    "hussar": lambda: rider_horse(2, rider=(140, 100, 50)),
    "aoe_knight": lambda: rider_horse(0),
    "cavalier": lambda: rider_horse(1),
    "paladin": lambda: rider_horse(2, rider=(180, 180, 190)),
    "camel_rider": lambda: camel_line(0),
    "heavy_camel_rider": lambda: camel_line(1),
    "imperial_camel_rider": lambda: camel_line(2),
    "battle_elephant": lambda: elephant_line(0),
    "elite_battle_elephant": lambda: elephant_line(1),
    "war_elephant": lambda: elephant_line(0, howdah=(160, 60, 50)),
    "elite_war_elephant": lambda: elephant_line(1, howdah=(160, 60, 50)),
    "armored_elephant": lambda: elephant_line(0, armor=True),
    "elite_armored_elephant": lambda: elephant_line(1, armor=True),
    "elephant_archer": lambda: elephant_line(0, howdah=(40, 90, 50)),
    "elite_elephant_archer": lambda: elephant_line(1, howdah=(40, 90, 50)),
    "steppe_lancer": lambda: rider_horse(0, horse=(100, 80, 50), rider=(80, 90, 70)),
    "elite_steppe_lancer": lambda: rider_horse(1, horse=(100, 80, 50), rider=(80, 90, 70)),
    "eagle_scout": lambda: eagle_line(0),
    "eagle_warrior": lambda: eagle_line(1),
    "elite_eagle_warrior": lambda: eagle_line(2),
    "jaguar_warrior": lambda: jaguar_line(0),
    "elite_jaguar_warrior": lambda: jaguar_line(1),
    "condottiero": condottiero_icon,
    "hand_cannoneer": hand_cannon_icon,
    "petard": petard_icon,
    "monk": monk_line,
    "missionary": lambda: monk_line(0, missionary=True),
    "longbowman": lambda: archer_line(0, tunic=(40, 70, 90)),
    "elite_longbowman": lambda: archer_line(1, tunic=(40, 70, 90)),
    "throwing_axeman": lambda: unique_melee(0, (90, 50, 40), "axe"),
    "elite_throwing_axeman": lambda: unique_melee(1, (90, 50, 40), "axe"),
    "chu_ko_nu": chukonu_line,
    "elite_chu_ko_nu": lambda: chukonu_line(1),
    "mangudai": lambda: rider_horse(0, horse=(70, 50, 35), bow=True),
    "elite_mangudai": lambda: rider_horse(1, horse=(70, 50, 35), bow=True),
    "cataphract": cataphract_line,
    "elite_cataphract": lambda: cataphract_line(1),
    "samurai": lambda: unique_melee(0, (50, 50, 60), "katana"),
    "elite_samurai": lambda: unique_melee(1, (50, 50, 60), "katana"),
    "teutonic_knight": teuton_line,
    "elite_teutonic_knight": lambda: teuton_line(1),
    "berserk": lambda: unique_melee(0, (80, 50, 40), "axe"),
    "elite_berserk": lambda: unique_melee(1, (80, 50, 40), "axe"),
    "woad_raider": lambda: unique_melee(0, (50, 90, 70), "club"),
    "elite_woad_raider": lambda: unique_melee(1, (50, 90, 70), "club"),
    "gbeto": lambda: unique_melee(0, (180, 140, 60), "throw"),
    "elite_gbeto": lambda: unique_melee(1, (180, 140, 60), "throw"),
    "rattan_archer": rattan_line,
    "elite_rattan_archer": lambda: rattan_line(1),
    "organ_gun": organ_line,
    "elite_organ_gun": lambda: organ_line(1),
    "battering_ram": lambda: ram_line(0),
    "capped_ram": lambda: ram_line(1),
    "siege_ram": lambda: ram_line(2),
    "mangonel": lambda: mangonel_line(0),
    "onager": lambda: mangonel_line(1),
    "siege_onager": lambda: mangonel_line(2),
    "scorpion": lambda: scorpion_line(0),
    "heavy_scorpion": lambda: scorpion_line(1),
    "bombard_cannon": bombard_line,
    "siege_tower": siege_tower_icon,
    "trebuchet": trebuchet_icon,
    "fishing_ship": fishing_ship_icon,
    "transport_ship": lambda: ship_line(0, "transport"),
    "galley": lambda: ship_line(0, "galley"),
    "war_galley": lambda: ship_line(1, "galley"),
    "galleon": lambda: ship_line(2, "galley"),
    "fire_galley": lambda: ship_line(0, "fire"),
    "fire_ship": lambda: ship_line(1, "fire"),
    "fast_fire_ship": lambda: ship_line(2, "fire"),
    "demolition_raft": lambda: ship_line(0, "demo"),
    "demolition_ship": lambda: ship_line(1, "demo"),
    "heavy_demolition_ship": lambda: ship_line(2, "demo"),
    "cannon_galleon": lambda: ship_line(0, "cannon"),
    "elite_cannon_galleon": lambda: ship_line(1, "cannon"),
    "turtle_ship": lambda: ship_line(0, "turtle"),
    "elite_turtle_ship": lambda: ship_line(1, "turtle"),
    "longboat": lambda: ship_line(0, "longboat"),
    "elite_longboat": lambda: ship_line(1, "longboat"),
    "caravel": lambda: ship_line(0, "caravel"),
    "elite_caravel": lambda: ship_line(1, "caravel"),
    "dromon": lambda: ship_line(0, "dromon"),
    "trade_cog": lambda: ship_line(0, "transport"),
    "trade_cart": trade_cart_icon,
    "town_center": town_center_icon,
    "townhall": town_center_icon,
    "house": house_icon,
    "farm": farm_icon,
    "pasture": pasture_icon,
    "mill": mill_icon,
    "lumbermill": lumbermill_icon,
    "mining_camp": mining_camp_icon,
    "market": market_icon,
    "feitoria": feitoria_icon,
    "barracks": barracks_icon,
    "archery_range": archery_range_icon,
    "blacksmith": blacksmith_icon,
    "stables": stables_icon,
    "workshop": workshop_icon,
    "shipyard": shipyard_icon,
    "fish_trap": fish_trap_icon,
    "wall": lambda: wall_icon(),
    "fortified_wall": lambda: wall_icon(fortified=True),
    "palisade_wall": lambda: wall_icon(palisade=True),
    "gate": lambda: gate_icon(),
    "fortified_gate": lambda: gate_icon(fortified=True),
    "palisade_gate": lambda: gate_icon(palisade=True),
    "outpost": outpost_icon,
    "scouttower": lambda: tower_icon("scout"),
    "guardtower": lambda: tower_icon("guard"),
    "keeptower": lambda: tower_icon("keep"),
    "cannontower": lambda: tower_icon("cannon"),
    "university": university_icon,
    "monastery": monastery_icon,
    "aoe_castle": castle_icon,
    "keep": keep_icon,
    "goldmine": goldmine_icon,
    "wood": wood_icon,
    "stone_mine": stone_mine_icon,
    "orchard": orchard_icon,
    "shore_fish": lambda: fish_icon(False),
    "deep_fish": lambda: fish_icon(True),
    "food_carcass": carcass_icon,
    "food_livestock": livestock_icon,
    "relic": relic_icon,
    "deer": deer_icon,
    "sheep": sheep_icon,
    "boar": boar_icon,
    "meadow": meadow_icon,
    "build_site": meadow_icon,
    "footman": lambda: infantry_sword(0),
    "archer": lambda: archer_line(0),
    "darkarcher": lambda: archer_line(0, tunic=(40, 50, 40)),
    "knight": lambda: rider_horse(0),
    "catapult": lambda: mangonel_line(0),
    "dragon": lambda: elephant_line(0, howdah=(180, 50, 40)),
    "mage": lambda: monk_line(),
    "skeleton": lambda: infantry_sword(0, (180, 180, 185)),
    "zombie": lambda: infantry_sword(0, (70, 90, 50)),
    "dragonslair": castle_icon,
    "magestower": university_icon,
}


def parse_rules(text: str):
    types: dict[str, dict] = {}
    current = None
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("def "):
            current = line.split()[1]
            types[current] = {"cls": None, "is_a": []}
            continue
        if current is None:
            continue
        if line.startswith("class "):
            types[current]["cls"] = line.split()[1]
        elif line.startswith("is_a "):
            types[current]["is_a"].extend(line.split()[1:])
    return types


def resolved_class(name: str, types: dict, seen=None) -> str | None:
    seen = seen if seen is not None else set()
    if name in seen or name not in types:
        return None
    seen.add(name)
    cls = types[name].get("cls")
    if cls:
        return cls
    for parent in types[name].get("is_a") or []:
        found = resolved_class(parent, types, seen)
        if found:
            return found
    return None


def find_drawn_parent(name: str, types: dict, written: dict | None = None) -> str | None:
    written = written if written is not None else _written
    seen = set()
    queue = list(types.get(name, {}).get("is_a") or [])
    while queue:
        parent = queue.pop(0)
        if parent in seen:
            continue
        seen.add(parent)
        if parent in ABSTRACT_PARENTS:
            if parent in types:
                queue.extend(types[parent]["is_a"])
            continue
        if parent in written:
            return parent
        if parent in types:
            queue.extend(types[parent]["is_a"])
    return None


def generate_pack(types: dict, icons_dir: Path, map_dir: Path, *, include_neutral: bool):
    written: dict[str, Image.Image] = {}
    for name, fn in CANONICAL.items():
        if not include_neutral and name in NEUTRAL_TYPES:
            continue
        save(name, fn(), icons_dir=icons_dir, map_dir=map_dir, written=written)
    for name in types:
        if name in written or name in ABSTRACT_PARENTS:
            continue
        if not include_neutral and name in NEUTRAL_TYPES:
            continue
        cls = resolved_class(name, types)
        if cls not in VISUAL_CLASSES:
            continue
        if not include_neutral and cls in ("deposit", "item", "building_land"):
            continue
        parent = find_drawn_parent(name, types, written)
        if parent and copy_as(
            parent, name, icons_dir=icons_dir, map_dir=map_dir, written=written
        ):
            continue
        if include_neutral:
            save(
                name,
                generic_icon(cls or "soldier", name),
                icons_dir=icons_dir,
                map_dir=map_dir,
                written=written,
            )
    return written


def copy_order_keywords():
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in ORDER_KEYWORDS:
        src = RES_ICONS / f"{name}.png"
        if src.is_file():
            shutil.copyfile(src, OUT / f"{name}.png")
            n += 1
    return n


def load_arch_packs():
    """Read set palettes and neutral types from ui/architecture.txt."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from soundrts.lib.arch_set import COLOR_KEYS, parse_architecture

    _mapping, sets, neutral = parse_architecture(
        ARCH_FILE.read_text(encoding="utf-8")
    )
    styles = {}
    for name, spec in sets.items():
        style = dict(DEFAULT_STYLE)
        if spec.get("kit"):
            style["kit"] = spec["kit"]
        for key in COLOR_KEYS:
            if key in spec:
                style[key] = spec[key]
        styles[name] = style
    return styles, set(neutral)


def main():
    global _STYLE, NEUTRAL_TYPES
    types = parse_rules(RULES.read_text(encoding="utf-8"))
    arch_styles, NEUTRAL_TYPES = load_arch_packs()
    _STYLE = dict(DEFAULT_STYLE)
    generate_pack(types, OUT, OUT_MAP, include_neutral=True)
    n_kw = copy_order_keywords()
    for arch, style in arch_styles.items():
        _STYLE = dict(style)
        generate_pack(types, OUT / arch, OUT_MAP / arch, include_neutral=False)
        print("arch", arch)
    _STYLE = dict(DEFAULT_STYLE)
    print(f"done: {len(list(OUT.glob('*.png')))} png in {OUT.relative_to(ROOT)}")
    print(f"done: {len(list(OUT.rglob('*.png')))} png under icons (incl. sets)")
    print(f"done: {len(list(OUT_MAP.rglob('*.png')))} png under map (incl. sets)")
    print(f"copied {n_kw} order keywords from res/ui/icons")


if __name__ == "__main__":
    main()
