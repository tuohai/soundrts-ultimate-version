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
        self.select_pulse_t0 = time.time()

    def clear(self):
        self.lerp_pos.clear()
        self.vis_hp.clear()
        self.hurt_until.clear()
        self.particles.clear()
        self.attack_beams.clear()

    def note_hurt(self, oid, duration=0.28):
        self.hurt_until[oid] = time.time() + duration

    def note_attack(self, ax, ay, tx, ty, color, duration=0.22):
        now = time.time()
        self.attack_beams.append(
            {
                "a": (ax, ay),
                "b": (tx, ty),
                "color": color,
                "until": now + duration,
            }
        )
        # hit spark
        for i in range(6):
            ang = (i / 6.0) * math.tau
            self.particles.append(
                {
                    "x": float(tx),
                    "y": float(ty),
                    "vx": math.cos(ang) * 40,
                    "vy": math.sin(ang) * 40,
                    "until": now + 0.35,
                    "color": color,
                    "r": 2,
                }
            )

    def update_and_draw_overlays(self, screen, dt=0.05):
        now = time.time()
        # beams
        keep_beams = []
        for b in self.attack_beams:
            if b["until"] <= now:
                continue
            keep_beams.append(b)
            alpha_t = max(0.0, (b["until"] - now) / 0.22)
            col = b["color"]
            pygame.draw.line(screen, col, b["a"], b["b"], max(1, int(3 * alpha_t)))
        self.attack_beams = keep_beams

        # particles
        keep_p = []
        for p in self.particles:
            if p["until"] <= now:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.88
            p["vy"] *= 0.88
            keep_p.append(p)
            life = max(0.0, (p["until"] - now) / 0.35)
            r = max(1, int(p["r"] * (0.5 + life)))
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
