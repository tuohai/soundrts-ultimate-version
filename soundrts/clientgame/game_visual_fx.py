"""Ctrl+F2 sighted polish: fog soft edges, flashes, particles, lerp, minimap helpers.

Visual-only — no TTS, no gameplay/network side effects.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

import pygame

from ..lib.screen import get_screen

Vec2 = Tuple[float, float]
RGB = Tuple[int, int, int]


def blend(a: RGB, b: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def soft_fog_color(base: RGB, edge_strength: float) -> RGB:
    """edge_strength 0 = deep fog, 1 = near visible (softer)."""
    deep = (
        base[0] * 32 // 100 + 10,
        base[1] * 32 // 100 + 10,
        base[2] * 32 // 100 + 12,
    )
    mid = (
        base[0] * 55 // 100 + 14,
        base[1] * 55 // 100 + 14,
        base[2] * 55 // 100 + 16,
    )
    return blend(deep, mid, max(0.0, min(1.0, edge_strength)))


def fog_edge_strength(square, player) -> float:
    """How close a fog square is to live vision (0–1)."""
    if square in player.observed_squares:
        return 1.0
    if square not in player.observed_before_squares:
        return 0.0
    n = 0
    for nb in getattr(square, "neighbors", ()) or ():
        if nb in player.observed_squares:
            n += 1
    return min(1.0, 0.25 + 0.25 * n)


class VisualFxState:
    """Per-GridView transient visual state."""

    def __init__(self):
        self.lerp_pos = {}  # id -> (sx, sy) float
        self.vis_hp = {}  # id -> last hp for flash detect
        self.hurt_until = {}  # id -> time
        self.particles: List[dict] = []
        self.attack_beams: List[dict] = []  # lingering attack lines
        self.projectiles: List[dict] = []  # flying shots
        self.slashes: List[dict] = []  # melee arcs
        self.select_pulse_t0 = time.time()

    def clear(self):
        self.lerp_pos.clear()
        self.vis_hp.clear()
        self.hurt_until.clear()
        self.particles.clear()
        self.attack_beams.clear()
        self.projectiles.clear()
        self.slashes.clear()

    def note_hurt(self, oid, duration=0.28):
        self.hurt_until[oid] = time.time() + duration

    def _burst(self, x, y, color, n=8, speed=55, life=0.4, r=2):
        now = time.time()
        for i in range(n):
            ang = (i / float(n)) * math.tau + (now % 1) * 0.7
            sp = speed * (0.55 + 0.45 * ((i * 37) % 10) / 10.0)
            self.particles.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "vx": math.cos(ang) * sp,
                    "vy": math.sin(ang) * sp,
                    "until": now + life,
                    "life0": life,
                    "color": color,
                    "r": r,
                    "kind": "spark",
                }
            )

    def note_attack(self, ax, ay, tx, ty, color, *, ranged=False, duration=0.22):
        """Hit feedback. Prefer note_shot/note_slash at launch; this covers wound."""
        now = time.time()
        if ranged:
            self.attack_beams.append(
                {
                    "a": (ax, ay),
                    "b": (tx, ty),
                    "color": color,
                    "until": now + duration,
                    "w0": 2,
                }
            )
        else:
            self.slashes.append(
                {
                    "cx": float(tx),
                    "cy": float(ty),
                    "ax": float(ax),
                    "ay": float(ay),
                    "color": color,
                    "until": now + 0.18,
                }
            )
        self._burst(tx, ty, color, n=10 if ranged else 7, speed=70 if ranged else 45)

    def note_shot(self, ax, ay, tx, ty, color, flight=0.28):
        """Ranged projectile from attacker to target (launch time)."""
        now = time.time()
        self.projectiles.append(
            {
                "x0": float(ax),
                "y0": float(ay),
                "x1": float(tx),
                "y1": float(ty),
                "t0": now,
                "t1": now + flight,
                "color": color,
                "r": 3,
            }
        )
        # muzzle puff
        self._burst(ax, ay, color, n=4, speed=30, life=0.2, r=2)

    def note_slash(self, ax, ay, tx, ty, color):
        now = time.time()
        self.slashes.append(
            {
                "cx": float(tx),
                "cy": float(ty),
                "ax": float(ax),
                "ay": float(ay),
                "color": color,
                "until": now + 0.2,
            }
        )
        self.attack_beams.append(
            {
                "a": (ax, ay),
                "b": (tx, ty),
                "color": color,
                "until": now + 0.12,
                "w0": 3,
            }
        )

    def note_gather(self, wx, wy, mx, my, resource_type="0"):
        """Worker gathers at mine/wood: chips fly from deposit to worker."""
        now = time.time()
        if str(resource_type) in ("1", "resource1", "gold", "0"):
            color = (255, 210, 60)
        else:
            color = (140, 190, 80)
        # sparkles on deposit
        self._burst(mx, my, color, n=6, speed=35, life=0.35, r=2)
        # chips toward worker
        for i in range(5):
            t = 0.12 + i * 0.04
            self.projectiles.append(
                {
                    "x0": float(mx),
                    "y0": float(my),
                    "x1": float(wx),
                    "y1": float(wy),
                    "t0": now + i * 0.03,
                    "t1": now + t,
                    "color": color,
                    "r": 2,
                }
            )

    def note_store(self, wx, wy, sx, sy, resource_type="0"):
        """Cargo delivered into townhall/lumbermill."""
        now = time.time()
        if str(resource_type) in ("1", "resource1", "gold", "0"):
            color = (255, 220, 70)
        else:
            color = (150, 200, 90)
        self.projectiles.append(
            {
                "x0": float(wx),
                "y0": float(wy),
                "x1": float(sx),
                "y1": float(sy),
                "t0": now,
                "t1": now + 0.35,
                "color": color,
                "r": 3,
            }
        )
        self._burst(sx, sy, color, n=8, speed=40, life=0.4, r=2)

    def update_and_draw_overlays(self, screen, dt=0.05):
        now = time.time()
        # projectiles (fly along segment)
        keep_proj = []
        for p in self.projectiles:
            if now < p["t0"]:
                keep_proj.append(p)
                continue
            if now >= p["t1"]:
                # impact spark at end
                self._burst(p["x1"], p["y1"], p["color"], n=5, speed=50, life=0.25, r=2)
                continue
            u = (now - p["t0"]) / max(1e-6, p["t1"] - p["t0"])
            # slight arc
            x = p["x0"] + (p["x1"] - p["x0"]) * u
            y = p["y0"] + (p["y1"] - p["y0"]) * u - math.sin(u * math.pi) * 10
            keep_proj.append(p)
            pygame.draw.circle(screen, p["color"], (int(x), int(y)), p["r"])
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), max(1, p["r"] - 1), 1)
        self.projectiles = keep_proj

        # melee slashes
        keep_s = []
        for s in self.slashes:
            if s["until"] <= now:
                continue
            keep_s.append(s)
            life = max(0.0, (s["until"] - now) / 0.2)
            # arc around target facing attacker
            ang0 = math.atan2(s["ay"] - s["cy"], s["ax"] - s["cx"])
            radius = 14
            pts = []
            for i in range(7):
                a = ang0 - 0.9 + 1.8 * (i / 6.0)
                pts.append(
                    (
                        s["cx"] + math.cos(a) * radius * (0.7 + 0.3 * life),
                        s["cy"] + math.sin(a) * radius * (0.7 + 0.3 * life),
                    )
                )
            if len(pts) >= 2:
                pygame.draw.lines(screen, s["color"], False, pts, max(1, int(3 * life)))
        self.slashes = keep_s

        # beams
        keep_beams = []
        for b in self.attack_beams:
            if b["until"] <= now:
                continue
            keep_beams.append(b)
            span = 0.22
            alpha_t = max(0.0, (b["until"] - now) / span)
            col = b["color"]
            w0 = int(b.get("w0", 3))
            pygame.draw.line(screen, col, b["a"], b["b"], max(1, int(w0 * alpha_t)))
        self.attack_beams = keep_beams

        # particles
        keep_p = []
        for p in self.particles:
            if p["until"] <= now:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.88
            p["vy"] *= 0.88 + (0.02 if p.get("kind") == "spark" else 0)
            p["vy"] += 25 * dt  # light gravity
            keep_p.append(p)
            life0 = float(p.get("life0", 0.35))
            life = max(0.0, (p["until"] - now) / max(life0, 1e-6))
            r = max(1, int(p["r"] * (0.4 + 0.6 * life)))
            pygame.draw.circle(screen, p["color"], (int(p["x"]), int(p["y"])), r)
        self.particles = keep_p

        # prune hurt
        self.hurt_until = {k: v for k, v in self.hurt_until.items() if v > now}

    def lerped_screen_pos(self, oid, target_xy: Vec2, snap_dist=80.0) -> Tuple[int, int]:
        tx, ty = float(target_xy[0]), float(target_xy[1])
        prev = self.lerp_pos.get(oid)
        if prev is None:
            self.lerp_pos[oid] = (tx, ty)
            return int(tx), int(ty)
        px, py = prev
        dx, dy = tx - px, ty - py
        if dx * dx + dy * dy > snap_dist * snap_dist:
            self.lerp_pos[oid] = (tx, ty)
            return int(tx), int(ty)
        # ease toward target
        nx = px + dx * 0.38
        ny = py + dy * 0.38
        self.lerp_pos[oid] = (nx, ny)
        return int(nx), int(ny)

    def selection_pulse_color(self) -> RGB:
        t = 0.5 + 0.5 * math.sin(time.time() * 7.0)
        return blend((255, 255, 170), (255, 170, 60), t)

    def check_hp_flash(self, oid, hp) -> bool:
        if hp is None:
            return False
        prev = self.vis_hp.get(oid)
        self.vis_hp[oid] = hp
        if prev is not None and hp < prev:
            self.note_hurt(oid)
            return True
        return False


def draw_progress_ring(screen, cx, cy, radius, ratio, color=(90, 200, 255)):
    ratio = max(0.0, min(1.0, float(ratio)))
    if ratio <= 0.01:
        return
    rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
    # background ring
    pygame.draw.circle(screen, (30, 35, 45), (cx, cy), radius, 2)
    if ratio >= 0.999:
        pygame.draw.circle(screen, color, (cx, cy), radius, 2)
        return
    # approximate arc with short segments
    start = -math.pi / 2
    end = start + math.tau * ratio
    steps = max(4, int(24 * ratio))
    pts = []
    for i in range(steps + 1):
        a = start + (end - start) * (i / steps)
        pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
    if len(pts) >= 2:
        pygame.draw.lines(screen, color, False, pts, 2)


def draw_target_marker(screen, x, y, color=(120, 220, 255), size=10):
    pygame.draw.line(screen, color, (x - size, y), (x + size, y), 2)
    pygame.draw.line(screen, color, (x, y - size), (x, y + size), 2)
    pygame.draw.circle(screen, color, (x, y), size // 2 + 2, 1)


def minimap_rect(screen_w, screen_h, cols, rows, max_side=150, margin=10):
    """Top-right minimap rect."""
    cell = max(2, min(max_side // max(cols, 1), max_side // max(rows, 1)))
    w = cell * cols
    h = cell * rows
    left = screen_w - w - margin
    top = margin
    return left, top, w, h, cell


def hit_test_minimap(pos, rect_cell) -> Optional[Tuple[int, int]]:
    """Return (col, row) or None. rect_cell = (left, top, w, h, cell, cols, rows)."""
    left, top, w, h, cell, cols, rows = rect_cell
    x, y = pos
    if not (left <= x < left + w and top <= y < top + h):
        return None
    # screen y down; row 0 at bottom of world map in gridview — match main map:
    # yc = (ymax - (y-oy)) // height → row 0 at bottom of rect visually if we flip
    xc = int((x - left) // cell)
    # Flip Y so top of minimap = high row numbers? Main map: row increases north = up on screen
    # In _get_rect: top = oy + ymax - (yc+1)*height → high yc near top of map origin area
    # So yc=0 is at bottom of the drawn map. Minimap: top of rect = high row.
    yc = rows - 1 - int((y - top) // cell)
    if 0 <= xc < cols and 0 <= yc < rows:
        return xc, yc
    return None
