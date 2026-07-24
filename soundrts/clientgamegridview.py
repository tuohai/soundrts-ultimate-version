from math import cos, radians, sin
import time

import pygame

from .definitions import style
from .lib.log import warning
from .lib.nofloat import PRECISION, square_of_distance
from .lib.screen import draw_line, draw_rect, get_screen
from .worldentity import COLLISION_RADIUS

R = 3
R2 = 9

# style 未写 color 时的可读默认色（Ctrl+F2 俯视图）
_DEFAULT_TERRAIN_COLORS = {
    "plain": (48, 92, 48),
    "rocky_plain": (70, 85, 55),
    "high_rocky_plain": (90, 100, 70),
    "_high_ground": (85, 110, 55),
    "plateau": (95, 115, 60),
    "hill": (100, 105, 55),
    "meadows": (55, 120, 45),
    "build_sites": (70, 100, 50),
    "town": (90, 80, 55),
    "forest": (28, 70, 32),
    "dense_forest": (18, 50, 22),
    "river": (35, 75, 140),
    "creek": (40, 85, 145),
    "lake": (30, 70, 130),
    "sea": (25, 55, 120),
    "ocean": (20, 45, 110),
    "mountain": (95, 95, 100),
    "mountain_pass": (110, 110, 100),
    "ford": (50, 90, 100),
    "bridge": (120, 100, 70),
    "marsh": (55, 85, 50),
    "swamp": (45, 70, 45),
}


def _as_rgb(color):
    if isinstance(color, pygame.Color):
        return (color.r, color.g, color.b)
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    return None


def terrain_color(terrain: str):
    color = style.get(terrain, "color", warn_if_not_found=False)
    try:
        rgb = _as_rgb(pygame.Color(color[0]))
        if rgb is not None:
            return rgb
    except (IndexError, TypeError, ValueError):
        pass
    if terrain in _DEFAULT_TERRAIN_COLORS:
        return _DEFAULT_TERRAIN_COLORS[terrain]
    return (42, 78, 42)


def intensify(color):
    """高地：提亮并略偏暖，避免直接 ×2 过曝。"""
    r, g, b = color
    return (
        min(255, int(r * 1.35) + 18),
        min(255, int(g * 1.35) + 12),
        min(255, int(b * 1.25) + 8),
    )


def square_color(square):
    if getattr(square, "is_water", False) and not getattr(square, "is_ground", True):
        base = terrain_color(getattr(square, "type_name", "") or "lake")
        if not getattr(square, "type_name", None):
            base = (32, 68, 128)
    else:
        base = terrain_color(getattr(square, "type_name", "") or "")
    if square.high_ground:
        base = intensify(base)
    return base


def fade(color):
    """迷雾记忆：压暗但保留一点色相，避免糊成一团灰。"""
    r, g, b = color
    return (r * 35 // 100 + 12, g * 35 // 100 + 12, b * 35 // 100 + 14)


def _blend(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _square_coord_label(col, row):
    """0-based col/row → 游戏内数字坐标（1 基，如 2,7）。"""
    return "%d,%d" % (col + 1, row + 1)


def _resolve_place_label(key):
    """地图别名 / tts 键 → 尽量可读的短文本。"""
    if key is None:
        return None
    if isinstance(key, int):
        key = str(key)
    text = str(key).strip()
    if not text:
        return None
    try:
        from .lib.msgs import localize_voice_msg

        resolved = localize_voice_msg([text])
        if resolved:
            part = resolved[0]
            if isinstance(part, str) and part.strip():
                text = part.strip()
    except Exception:
        pass
    # 过长地名截断，避免糊满一格
    if len(text) > 14:
        text = text[:13] + "…"
    return text


def _square_place_name(square, world):
    std = "%d,%d" % (square.col, square.row)
    for mapping_name in (
        "square_districts",
        "square_cities",
        "square_names",
        "square_provinces",
    ):
        mapping = getattr(world, mapping_name, None) or {}
        if std in mapping:
            return _resolve_place_label(mapping[std])
    return None


def _resource_qty_label(o):
    model = getattr(o, "model", o)
    qty = getattr(o, "qty", None)
    if qty is None:
        qty = getattr(model, "qty", None)
    if qty is None:
        qty = getattr(model, "resource_qty", None)
    if qty is None:
        return None
    try:
        n = int(qty)
    except (TypeError, ValueError):
        return None
    if n >= PRECISION:
        n = n // PRECISION
    if n <= 0:
        return None
    return str(n)


def _voice_to_text(parts):
    """语音消息片段 → 面板用短文本。"""
    if not parts:
        return ""
    try:
        from .lib.pygame_ui import msgparts_to_text

        return (msgparts_to_text(parts) or "").strip()
    except Exception:
        try:
            return " ".join(str(p) for p in parts).strip()
        except Exception:
            return str(parts)


def _terrain_type_label(square, x=None, y=None, detailed=False):
    """当前格地形类型短名（可读标题优先）。"""
    if detailed:
        try:
            from .clientgame.game_navigation import _square_terrain

            voice = _square_terrain(square, x, y)
            if voice:
                text = _voice_to_text(voice)
                if text:
                    # 语音常带逗号前缀/分隔，压成一行短标签
                    text = text.replace(",", " ").replace("，", " ")
                    return " ".join(text.split())
        except Exception:
            pass
    tn = getattr(square, "type_name", None) or ""
    if tn:
        title = style.get(tn, "title", warn_if_not_found=False)
        if title:
            return _voice_to_text(title) or tn
        return tn
    if getattr(square, "is_water", False) and not getattr(square, "is_ground", True):
        return "water"
    return None


class GridView:
    def __init__(self, interface):
        self.interface = interface
        self._object_cache = {}  # 对象渲染缓存
        self._last_cache_update = 0
        self._cache_update_interval = 100  # 缓存更新间隔(ms)
        self._visible_objects = set()  # 当前可见的对象
        self._map_origin = (0, 0)  # 地图在屏幕上的偏移（居中）
        self._font_coord = None
        self._font_name = None
        self._font_qty = None
        self._font_panel = None
        self._font_panel_title = None
        self._font_size_key = None
        from .clientgame.game_visual_fx import VisualFxState

        self.fx = VisualFxState()
        self._minimap_hit = None  # (left, top, w, h, cell, cols, rows)

    def _ensure_fonts(self):
        size = max(10, min(16, self.square_view_width // 4))
        key = (size, self.square_view_width)
        if key == self._font_size_key and self._font_coord is not None:
            return
        self._font_size_key = key
        self._font_coord = pygame.font.SysFont("consolas", max(9, size - 1), bold=True)
        if self._font_coord is None or self._font_coord.get_height() == 0:
            self._font_coord = pygame.font.SysFont("arial", max(9, size - 1), bold=True)
        self._font_name = pygame.font.SysFont("arial", max(9, size - 2), bold=False)
        self._font_qty = pygame.font.SysFont("consolas", max(9, size), bold=True)
        if self._font_qty.get_height() == 0:
            self._font_qty = pygame.font.SysFont("arial", max(9, size), bold=True)
        self._font_panel = pygame.font.SysFont("arial", 13, bold=False)
        self._font_panel_title = pygame.font.SysFont("arial", 14, bold=True)

    @staticmethod
    def _blit_label(screen, font, text, pos, color, shadow=True):
        if not text or font is None:
            return
        x, y = pos
        if shadow:
            sh = font.render(text, True, (0, 0, 0))
            screen.blit(sh, (x + 1, y + 1))
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))

    def _update_object_cache(self):
        current_time = pygame.time.get_ticks()
        if current_time - self._last_cache_update < self._cache_update_interval:
            return

        # 清理过期的缓存
        self._object_cache.clear()
        self._last_cache_update = current_time

    def _is_object_visible(self, o):
        """判断对象是否在视野内"""
        if not hasattr(o, "x") or not hasattr(o, "y"):
            return False

        if not self.interface.zoom_mode:
            # 全图显示模式：dobjets 已由战争迷雾过滤，无需再按当前方格裁剪
            return True

        # 缩放模式：显示当前主方格内全部单位（子格网格可见，便于鼠标点选）
        place = self.interface.place
        if place is None:
            return False
        if hasattr(o, "is_in"):
            return o.is_in(place)
        o_place = getattr(o, "place", None)
        return o_place is place

    def _zoom_view_rect(self):
        """Screen rect mapping to the current main square in zoom mode (leave HUD/info)."""
        screen = get_screen()
        sw, sh = screen.get_width(), screen.get_height()
        # 底留命令卡，左留信息板
        left = 200
        top = 12
        right = sw - 12
        bottom = sh - 130
        if right - left < 120:
            left = 12
        if bottom - top < 120:
            bottom = sh - 12
        return left, top, max(1, right - left), max(1, bottom - top)

    def _get_rect_from_map_coords(self, xc, yc):
        width, height = self.square_view_width, self.square_view_height
        ox, oy = self._map_origin
        left, top = ox + xc * width, oy + self.ymax - (yc + 1) * height
        return left, top, width, height

    def _display(self):
        if self.interface.zoom_mode and self.interface.place is not None:
            self._display_zoom_square()
            return

        screen = get_screen()
        cols = self.interface.xcmax + 1
        rows = self.interface.ycmax + 1
        map_w = self.square_view_width * cols
        map_h = self.square_view_height * rows

        # 未探索底色
        draw_rect((18, 18, 22), (self._map_origin[0], self._map_origin[1], map_w, map_h))

        # backgrounds
        squares_to_view = []
        player = self.interface.player
        for xc in range(0, cols):
            for yc in range(0, rows):
                sq = player.world.grid[(xc, yc)]
                if sq in player.observed_squares or sq in player.observed_before_squares:
                    color = square_color(sq)
                    if sq not in player.observed_squares:
                        from .clientgame.game_visual_fx import fog_edge_strength, soft_fog_color

                        color = soft_fog_color(color, fog_edge_strength(sq, player))
                    rect = self._get_rect_from_map_coords(xc, yc)
                    draw_rect(color, rect)
                    squares_to_view.append((sq, rect))

        # 迷雾交界柔边：已探明格与迷雾记忆格相邻时画半透明过渡带
        self._draw_fog_fringes(squares_to_view, player)

        # 细格线（可读分区，不抢出口）
        if self.square_view_width >= 8:
            grid_c = (0, 0, 0)
            for xc in range(cols + 1):
                x = self._map_origin[0] + xc * self.square_view_width
                pygame.draw.line(
                    screen,
                    grid_c,
                    (x, self._map_origin[1]),
                    (x, self._map_origin[1] + map_h),
                    1,
                )
            for yc in range(rows + 1):
                y = self._map_origin[1] + yc * self.square_view_height
                pygame.draw.line(
                    screen,
                    grid_c,
                    (self._map_origin[0], y),
                    (self._map_origin[0] + map_w, y),
                    1,
                )

        # 墙 = 无出口边；通路边略提亮缺口感
        for sq, rect in squares_to_view:
            exits = {e.o for e in sq.exits if not e.is_blocked()}
            walls = {-90, 90, 180, 0} - exits
            x, y = self._xy_coords(sq.x, sq.y)
            half_w = self.square_view_width / 2
            half_h = self.square_view_height / 2
            for o in walls:
                dx = cos(radians(o)) * half_w
                dy = -sin(radians(o)) * half_h
                # 用格宽方向边长，避免非正方形格时歪斜
                if o in (0, 180):  # 东/西：竖边
                    x1, y1 = x + dx, y - half_h + 1
                    x2, y2 = x + dx, y + half_h - 1
                else:  # 北/南：横边
                    x1, y1 = x - half_w + 1, y + dy
                    x2, y2 = x + half_w - 1, y + dy
                pygame.draw.line(screen, (8, 8, 10), (x1, y1), (x2, y2), 3)

            # 未阻塞出口：短划线提示可通
            for e in sq.exits:
                if e.is_blocked():
                    continue
                o = e.o
                dx = cos(radians(o)) * half_w * 0.92
                dy = -sin(radians(o)) * half_h * 0.92
                if o in (0, 180):
                    pygame.draw.line(
                        screen,
                        (200, 200, 160),
                        (x + dx, y - 3),
                        (x + dx, y + 3),
                        2,
                    )
                else:
                    pygame.draw.line(
                        screen,
                        (200, 200, 160),
                        (x - 3, y + dy),
                        (x + 3, y + dy),
                        2,
                    )

        # 地图外框
        draw_rect(
            (160, 160, 170),
            (self._map_origin[0], self._map_origin[1], map_w, map_h),
            2,
        )

        # 坐标 / 地名（格够大才画，避免糊成一团）
        self._draw_square_labels(squares_to_view, player.world)

    def _draw_fog_fringes(self, squares_to_view, player):
        """Soft edge between live vision and fog-of-war memory."""
        screen = get_screen()
        by_sq = {sq: rect for sq, rect in squares_to_view}
        fringe = pygame.Surface((max(2, self.square_view_width), 4), pygame.SRCALPHA)
        fringe.fill((0, 0, 0, 70))
        fringe_v = pygame.Surface((4, max(2, self.square_view_height)), pygame.SRCALPHA)
        fringe_v.fill((0, 0, 0, 70))
        for sq, rect in squares_to_view:
            if sq not in player.observed_squares:
                continue
            left, top, width, height = rect
            # neighbors: E W N S in grid
            for dc, dr, side in ((1, 0, "e"), (-1, 0, "w"), (0, 1, "n"), (0, -1, "s")):
                nb = player.world.grid.get((sq.col + dc, sq.row + dr))
                if nb is None:
                    continue
                if nb in player.observed_squares:
                    continue
                if nb not in player.observed_before_squares:
                    continue
                if side == "e":
                    screen.blit(fringe_v, (left + width - 4, top))
                elif side == "w":
                    screen.blit(fringe_v, (left, top))
                elif side == "n":
                    screen.blit(fringe, (left, top))
                else:
                    screen.blit(fringe, (left, top + height - 4))

    def _draw_square_labels(self, squares_to_view, world):
        if self.square_view_width < 22:
            return
        self._ensure_fonts()
        screen = get_screen()
        show_name = self.square_view_width >= 36
        show_terrain = self.square_view_width >= 44
        for sq, rect in squares_to_view:
            left, top, width, height = rect
            coord = _square_coord_label(sq.col, sq.row)
            self._blit_label(
                screen,
                self._font_coord,
                coord,
                (left + 2, top + 1),
                (230, 230, 235),
            )
            y = top + 2 + self._font_coord.get_height()
            if show_name:
                place_name = _square_place_name(sq, world)
                if place_name and place_name != coord:
                    if y + self._font_name.get_height() <= top + height - 2:
                        self._blit_label(
                            screen,
                            self._font_name,
                            place_name,
                            (left + 2, y),
                            (255, 230, 150),
                        )
                        y += self._font_name.get_height()
            if show_terrain:
                terrain = _terrain_type_label(sq)
                if terrain and y + self._font_name.get_height() <= top + height - 2:
                    if len(terrain) > 16:
                        terrain = terrain[:15] + "…"
                    self._blit_label(
                        screen,
                        self._font_name,
                        terrain,
                        (left + 2, y),
                        (180, 210, 255),
                    )

    def _display_zoom_square(self):
        """F8 zoom + Ctrl+F2: enlarge current square with N×N sub-cell grid."""
        screen = get_screen()
        sq = self.interface.place
        zoom = self.interface.zoom
        left, top, w, h = self._zoom_view_rect()
        self._map_origin = (left, top)
        self.ymax = h
        self.square_view_width = max(1, w)
        self.square_view_height = max(1, h)

        player = self.interface.player
        known = sq in player.observed_squares or sq in player.observed_before_squares
        if known:
            color = square_color(sq)
            if sq not in player.observed_squares:
                from .clientgame.game_visual_fx import fog_edge_strength, soft_fog_color

                color = soft_fog_color(color, fog_edge_strength(sq, player))
        else:
            color = (18, 18, 22)
        draw_rect(color, (left, top, w, h))
        draw_rect((160, 160, 170), (left, top, w, h), 2)

        precision = getattr(zoom, "precision", 3) or 3
        for i in range(1, precision):
            x = left + int(i * w / precision)
            y = top + int(i * h / precision)
            pygame.draw.line(screen, (0, 0, 0), (x, top), (x, top + h), 1)
            pygame.draw.line(screen, (0, 0, 0), (left, y), (left + w, y), 1)

        if known:
            exits = {e.o for e in sq.exits if not e.is_blocked()}
            walls = {-90, 90, 180, 0} - exits
            cx, cy = self._xy_coords(sq.x, sq.y)
            half_w = w / 2
            half_h = h / 2
            for o in walls:
                dx = cos(radians(o)) * half_w
                dy = -sin(radians(o)) * half_h
                if o in (0, 180):
                    pygame.draw.line(
                        screen,
                        (8, 8, 10),
                        (cx + dx, cy - half_h + 2),
                        (cx + dx, cy + half_h - 2),
                        4,
                    )
                else:
                    pygame.draw.line(
                        screen,
                        (8, 8, 10),
                        (cx - half_w + 2, cy + dy),
                        (cx + half_w - 2, cy + dy),
                        4,
                    )
            for e in sq.exits:
                if e.is_blocked():
                    continue
                o = e.o
                dx = cos(radians(o)) * half_w * 0.92
                dy = -sin(radians(o)) * half_h * 0.92
                if o in (0, 180):
                    pygame.draw.line(
                        screen,
                        (200, 200, 160),
                        (cx + dx, cy - 6),
                        (cx + dx, cy + 6),
                        3,
                    )
                else:
                    pygame.draw.line(
                        screen,
                        (200, 200, 160),
                        (cx - 6, cy + dy),
                        (cx + 6, cy + dy),
                        3,
                    )

        self._ensure_fonts()
        world = getattr(player, "world", None)
        coord = _square_coord_label(sq.col, sq.row)
        place_name = _square_place_name(sq, world) if world is not None else None
        head = ("%s  %s" % (coord, place_name)).strip() if place_name else coord
        font = self._font_panel_title or self._font_coord
        self._blit_label(screen, font, head, (left + 6, top + 4), (255, 235, 160))

    def _get_view_coords_from_world_coords(self, ox, oy):
        if self.interface.zoom_mode and self.interface.place is not None:
            sq = self.interface.place
            left, top, w, h = self._zoom_view_rect()
            x = int(left + (ox - sq.xmin) / max(sq.xmax - sq.xmin, 1e-9) * w)
            # world Y up → screen Y down
            y = int(top + (sq.ymax - oy) / max(sq.ymax - sq.ymin, 1e-9) * h)
            return x, y
        sw = self.interface.world.square_width
        x = int(self._map_origin[0] + ox / sw * self.square_view_width)
        y = int(self._map_origin[1] + oy / sw * self.square_view_height)
        return x, y

    def _object_coords(self, o):
        return self._get_view_coords_from_world_coords(o.x, o.y)

    def _xy_coords(self, ox, oy):
        return self._get_view_coords_from_world_coords(ox, oy)

    def _object_color(self, o):
        if getattr(o.model, "player", None) is not None:
            if o.id in self.interface.group:
                return (80, 255, 120)  # 选中：亮绿
            if o.player is self.interface.player:
                return (70, 210, 90)
            if o.player in self.interface.player.allied:
                return (70, 140, 255)
            if o.player.player_is_an_enemy(self.interface.player):
                return (230, 70, 60)
            return (180, 180, 80)
        # 中立：资源偏金，其它偏灰
        if getattr(o.model, "resource_type", None) is not None or getattr(
            o, "resource_type", None
        ):
            return (240, 200, 60)
        if getattr(o.model, "is_a_building_land", False):
            return (90, 140, 70)
        return (150, 150, 155)

    def _object_kind(self, o):
        model = getattr(o, "model", o)
        if getattr(model, "resource_type", None) is not None:
            return "resource"
        if getattr(model, "is_a_building", False):
            return "building"
        if getattr(model, "is_a_building_land", False):
            return "land"
        return "unit"

    def display_object(self, o):
        # 检查对象是否可见
        if not self._is_object_visible(o):
            return

        target_xy = self._get_view_coords_from_world_coords(o.x, o.y)
        x, y = self.fx.lerped_screen_pos(o.id, target_xy)
        color = self._object_color(o)

        screen = get_screen()
        kind = self._object_kind(o)
        selected = o.id in self.interface.group
        radius = max(3, R // 2)
        if kind == "building":
            radius = max(4, int(R * 0.85))
        elif kind == "resource":
            radius = max(3, int(R * 0.7))

        hurt = time.time() < self.fx.hurt_until.get(o.id, 0)
        if hurt:
            color = _blend(color, (255, 255, 255), 0.55)

        pulse = self.fx.selection_pulse_color() if selected else None

        if kind == "building":
            s = radius * 2
            rect = pygame.Rect(x - s // 2, y - s // 2, s, s)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (20, 20, 20), rect, 1)
            if selected:
                pygame.draw.rect(screen, pulse, rect.inflate(6, 6), 2)
                pygame.draw.rect(screen, (255, 255, 220), rect.inflate(2, 2), 1)
        elif kind == "resource":
            pts = (
                (x, y - radius),
                (x + radius, y),
                (x, y + radius),
                (x - radius, y),
            )
            pygame.draw.polygon(screen, color, pts)
            pygame.draw.polygon(screen, (40, 30, 10), pts, 1)
            qty_text = _resource_qty_label(o)
            if qty_text and self.square_view_width >= 20:
                self._ensure_fonts()
                self._blit_label(
                    screen,
                    self._font_qty,
                    qty_text,
                    (x + radius + 1, y - self._font_qty.get_height() // 2),
                    (255, 240, 120),
                )
        else:
            pygame.draw.circle(screen, color, (x, y), radius, 0)
            pygame.draw.circle(screen, (15, 15, 15), (x, y), radius, 1)
            if selected:
                pygame.draw.circle(screen, pulse, (x, y), radius + 4, 2)
                pygame.draw.circle(screen, (255, 255, 220), (x, y), radius + 2, 1)

        # 空气单位：细白圈
        if getattr(getattr(o, "model", o), "airground_type", None) == "air":
            pygame.draw.circle(screen, (220, 220, 255), (x, y), radius + 1, 1)

        # 渲染血条
        hp = getattr(o, "hp", None)
        hp_max = getattr(o, "hp_max", None)
        self.fx.check_hp_flash(o.id, hp)
        if hp is not None and hp_max and hp != hp_max and hp_max > 0:
            hp_prop = max(0, min(100, 100 * hp // hp_max))
            if hp_prop > 60:
                bar_color = (60, 220, 80)
            elif hp_prop > 30:
                bar_color = (230, 190, 40)
            else:
                bar_color = (240, 50, 50)
            W = max(4, radius)
            bar_y = y - radius - 3
            pygame.draw.line(
                screen,
                (30, 30, 30),
                (x - W, bar_y),
                (x + W, bar_y),
                2,
            )
            pygame.draw.line(
                screen,
                bar_color,
                (x - W, bar_y),
                (x - W + hp_prop * (2 * W) // 100, bar_y),
                2,
            )

        # 建造 / 训练进度环（仅画面，不影响语音）
        self._draw_order_progress(screen, o, x, y, radius)

    def _draw_order_progress(self, screen, o, x, y, radius):
        from .clientgame.game_visual_fx import draw_progress_ring

        model = getattr(o, "model", o)
        orders = getattr(model, "orders", None) or getattr(o, "orders", None) or []
        if not orders:
            return
        wo = orders[0]
        time_cost = getattr(wo, "time_cost", 0) or 0
        time_left = getattr(wo, "time", None)
        if not time_cost or time_left is None:
            return
        try:
            ratio = 1.0 - float(time_left) / float(time_cost)
        except (TypeError, ValueError, ZeroDivisionError):
            return
        kw = getattr(wo, "keyword", "") or ""
        if kw in ("build", "train", "research", "upgrade_to", "advance", "repair"):
            color = (90, 200, 255)
        else:
            color = (180, 180, 100)
        draw_progress_ring(screen, x, y, max(radius + 5, 8), ratio, color)

    def display_objects(self):
        # 更新对象缓存
        self._update_object_cache()

        visible_objects = [
            o for o in self.interface.dobjets.values() if self._is_object_visible(o)
        ]

        # 底层资源/空地 → 建筑 → 单位 → 选中置顶
        def _sort_key(o):
            kind = self._object_kind(o)
            layer = {"land": 0, "resource": 1, "building": 2, "unit": 3}.get(kind, 3)
            selected = 1 if o.id in self.interface.group else 0
            return (layer, selected)

        for o in sorted(visible_objects, key=_sort_key):
            self.display_object(o)
            if (
                o.place is None
                and not o.is_inside
                and not (
                    self.interface.already_asked_to_quit or self.interface.end_loop
                )
            ):
                warning("%s.place is None", o.type_name)
                if o.is_memory:
                    warning("(memory)")

    def _update_coefs(self):
        global R, R2
        screen = get_screen()
        sw, sh = screen.get_width(), screen.get_height()
        if self.interface.zoom_mode and self.interface.place is not None:
            left, top, w, h = self._zoom_view_rect()
            self._map_origin = (left, top)
            self.ymax = h
            self.square_view_width = max(1, w)
            self.square_view_height = max(1, h)
            precision = 3
            zoom = getattr(self.interface, "zoom", None)
            if zoom is not None:
                precision = getattr(zoom, "precision", 3) or 3
            cell = min(w, h) / max(precision, 1)
            R = max(6, int(cell * 0.28))
            R2 = R * R
            return
        cols = self.interface.xcmax + 1
        rows = self.interface.ycmax + 1
        self.square_view_width = self.square_view_height = max(
            1, min(sw // cols, sh // rows)
        )
        map_w = self.square_view_width * cols
        map_h = self.square_view_height * rows
        self.ymax = map_h
        # 地图居中，四周留黑边
        self._map_origin = ((sw - map_w) // 2, (sh - map_h) // 2)
        R = max(
            3,
            int(
                COLLISION_RADIUS
                / PRECISION
                / max(self.interface.square_width, 0.001)
                * self.square_view_width
            ),
        )
        R2 = R * R

    def _collision_display(self):
        for t, c in (("ground", (0, 0, 255)), ("air", (255, 0, 0))):
            for ox, oy in self.interface.collision_debug[t].xy_set():
                if self._is_object_visible({"x": ox, "y": oy}):
                    pygame.draw.circle(
                        get_screen(),
                        c,
                        self._get_view_coords_from_world_coords(ox, oy),
                        0,
                        0,
                    )

    def _display_active_zone_border(self):
        screen = get_screen()
        if self.interface.zoom_mode:
            zoom = self.interface.zoom
            left, bottom = self._get_view_coords_from_world_coords(zoom.xmin, zoom.ymin)
            right, top = self._get_view_coords_from_world_coords(zoom.xmax, zoom.ymax)
            rect = left, top, right - left, bottom - top
        else:
            xc, yc = self.interface.coords_in_map(self.interface.place)
            if xc < 0 or yc < 0:
                return
            rect = list(self._get_rect_from_map_coords(xc, yc))

        if self.interface.target is None:
            color = (255, 245, 180)
        else:
            color = (200, 200, 210)
        # 双线高亮当前格
        draw_rect(color, rect, 2)
        inset = [rect[0] + 2, rect[1] + 2, max(0, rect[2] - 4), max(0, rect[3] - 4)]
        draw_rect(_blend(color, (40, 40, 40), 0.35), inset, 1)

        # 观察者位置
        observer_coordinates = self._get_view_coords_from_world_coords(
            self.interface.x,
            self.interface.y,
        )
        ox, oy = observer_coordinates
        pygame.draw.circle(screen, color, (ox, oy), 4, 1)
        pygame.draw.line(screen, color, (ox - 6, oy), (ox + 6, oy), 1)
        pygame.draw.line(screen, color, (ox, oy - 6), (ox, oy + 6), 1)

    def _place_is_known(self, place):
        if place is None:
            return False
        if getattr(self.interface, "cheatmode", False):
            return True
        player = self.interface.player
        return place in player.observed_squares or place in player.observed_before_squares

    def _place_info_lines(self, place):
        from . import msgparts as mp

        lines = []
        if place is None:
            return lines
        coord = _square_coord_label(place.col, place.row)
        title = _voice_to_text(getattr(place, "title", None) or [])
        head = title or coord
        if title and coord not in title:
            head = "%s  (%s)" % (title, coord)
        lines.append(("title", head))

        if not self._place_is_known(place):
            lines.append(("dim", _voice_to_text(mp.UNKNOWN) or "unknown"))
            return lines

        x = getattr(self.interface, "x", None)
        y = getattr(self.interface, "y", None)
        terrain = _terrain_type_label(place, x, y, detailed=True)
        if terrain:
            label = _voice_to_text(mp.RMG_TERRAIN) or "terrain"
            lines.append(("", "%s: %s" % (label, terrain)))

        if x is not None and y is not None and hasattr(place, "high_ground_at"):
            height = 1 if place.high_ground_at(x, y) else 0
        else:
            height = int(getattr(place, "height", 0) or 0)
        h_label = _voice_to_text(mp.HEIGHT) or "height"
        lines.append(("", "%s: %d" % (h_label, height)))

        width_m = max(0, (place.xmax - place.xmin) // PRECISION)
        w_label = _voice_to_text(mp.SQUARE_WIDTH) or "width"
        meters = _voice_to_text(mp.METERS) or "m"
        lines.append(("", "%s: %d%s" % (w_label, width_m, meters)))

        if hasattr(place, "terrain_speed_at") and x is not None:
            speed = place.terrain_speed_at(x, y)
        else:
            speed = getattr(place, "terrain_speed", (100, 100))
        if speed and speed != (100, 100):
            s_label = _voice_to_text(mp.SPEED) or "speed"
            lines.append(("", "%s: %s%% / %s%%" % (s_label, speed[0], speed[1])))

        if hasattr(place, "terrain_cover_at") and x is not None:
            cover = place.terrain_cover_at(x, y)
        else:
            cover = getattr(place, "terrain_cover", (0, 0))
        if cover and cover != (0, 0):
            c_label = _voice_to_text(mp.TERRAIN_COVER) or "cover"
            lines.append(("", "%s: %s%% / %s%%" % (c_label, cover[0], cover[1])))

        flags = []
        if getattr(place, "is_water", False):
            flags.append("water")
        if getattr(place, "high_ground", False):
            flags.append("high")
        if flags:
            lines.append(("dim", " · ".join(flags)))
        return lines

    def _target_info_lines(self, target):
        lines = []
        if target is None:
            return lines
        model = getattr(target, "model", target)
        title = _voice_to_text(getattr(target, "title", None) or [])
        if not title:
            tn = getattr(target, "type_name", None) or getattr(model, "type_name", "?")
            title = _voice_to_text(style.get(tn, "title", warn_if_not_found=False) or []) or str(tn)
        kind = self._object_kind(target)
        lines.append(("title", title))
        lines.append(("dim", kind))

        hp = getattr(target, "hp", None)
        hp_max = getattr(target, "hp_max", None)
        if hp is None:
            hp = getattr(model, "hp", None)
        if hp_max is None:
            hp_max = getattr(model, "hp_max", None)
        if hp is not None and hp_max:
            lines.append(("", "HP: %s / %s" % (int(hp), int(hp_max))))
        elif hp is not None:
            lines.append(("", "HP: %s" % int(hp)))

        mana = getattr(target, "mana", None)
        mana_max = getattr(target, "mana_max", None) or 0
        if mana is not None and mana_max:
            lines.append(("", "MP: %s / %s" % (int(mana), int(mana_max))))

        mdg = getattr(target, "mdg", None)
        if mdg is None:
            mdg = getattr(model, "mdg", 0)
        rdg = getattr(target, "rdg", None)
        if rdg is None:
            rdg = getattr(model, "rdg", 0)
        if mdg:
            lines.append(("", "MDG: %s" % int(mdg)))
        if rdg:
            lines.append(("", "RDG: %s" % int(rdg)))

        mdf = getattr(target, "mdf", None)
        if mdf is None:
            mdf = getattr(model, "mdf", 0)
        rdf = getattr(target, "rdf", None)
        if rdf is None:
            rdf = getattr(model, "rdf", 0)
        if mdf:
            lines.append(("", "MDF: %s" % int(mdf)))
        if rdf:
            lines.append(("", "RDF: %s" % int(rdf)))

        armor = getattr(target, "armor", None) or getattr(model, "armor", None)
        if armor:
            armor_title = _voice_to_text(style.get(armor, "title", warn_if_not_found=False) or []) or str(armor)
            lines.append(("", "Armor: %s" % armor_title))

        ag = getattr(model, "airground_type", None) or getattr(target, "airground_type", None)
        if ag and ag != "ground":
            lines.append(("dim", str(ag)))

        qty = _resource_qty_label(target)
        if qty:
            lines.append(("", "Qty: %s" % qty))

        level = getattr(target, "level", None) or getattr(model, "level", None)
        if level:
            lines.append(("", "Lv: %s" % int(level)))
        return lines

    def _draw_info_panel(self):
        """Ctrl+F2：左侧信息板 — 当前格地形 + 指向单位/建筑。"""
        self._ensure_fonts()
        screen = get_screen()
        place = getattr(self.interface, "place", None)
        target = getattr(self.interface, "target", None)

        sections = []
        place_lines = self._place_info_lines(place)
        if place_lines:
            sections.append(place_lines)
        target_lines = self._target_info_lines(target)
        if target_lines:
            sections.append(target_lines)
        if not sections:
            return

        pad = 8
        line_gap = 2
        section_gap = 10
        title_font = self._font_panel_title
        body_font = self._font_panel
        max_w = 0
        total_h = pad * 2
        for si, lines in enumerate(sections):
            if si:
                total_h += section_gap
            for kind, text in lines:
                font = title_font if kind == "title" else body_font
                max_w = max(max_w, font.size(text)[0])
                total_h += font.get_height() + line_gap

        panel_w = min(screen.get_width() // 3, max(160, max_w + pad * 2))
        # 优先放在地图左侧黑边；不够则贴屏幕左上角半透明叠层
        ox = self._map_origin[0]
        if ox >= panel_w + 12:
            px = max(4, (ox - panel_w) // 2)
        else:
            px = 6
        py = max(6, self._map_origin[1])

        bg = pygame.Surface((panel_w, total_h), pygame.SRCALPHA)
        bg.fill((12, 14, 20, 200))
        screen.blit(bg, (px, py))
        pygame.draw.rect(screen, (120, 130, 150), (px, py, panel_w, total_h), 1)

        y = py + pad
        colors = {
            "title": (255, 235, 160),
            "dim": (160, 170, 185),
            "": (220, 225, 235),
        }
        for si, lines in enumerate(sections):
            if si:
                y += section_gap - line_gap
                pygame.draw.line(
                    screen,
                    (70, 75, 90),
                    (px + pad, y - section_gap // 2),
                    (px + panel_w - pad, y - section_gap // 2),
                    1,
                )
            for kind, text in lines:
                font = title_font if kind == "title" else body_font
                color = colors.get(kind, colors[""])
                # 过长截断
                draw = text
                while font.size(draw)[0] > panel_w - pad * 2 and len(draw) > 4:
                    draw = draw[:-2] + "…"
                self._blit_label(screen, font, draw, (px + pad, y), color, shadow=False)
                y += font.get_height() + line_gap

    def display(self):
        self._update_coefs()
        self._display()
        self.display_objects()
        self._display_active_zone_border()
        self._draw_move_target_marker()
        self._draw_info_panel()
        if not self.interface.zoom_mode:
            self._draw_minimap()
        try:
            from .clientgame.game_hud import draw_hud

            draw_hud(self.interface)
        except Exception:
            pass
        self.fx.update_and_draw_overlays(get_screen())
        if self.interface.collision_debug:
            self._collision_display()

    def _draw_move_target_marker(self):
        from .clientgame.game_visual_fx import draw_target_marker

        screen = get_screen()
        target = getattr(self.interface, "target", None)
        if target is not None and hasattr(target, "x") and hasattr(target, "y"):
            try:
                if (not self.interface.zoom_mode) or self._is_object_visible(target):
                    x, y = self._get_view_coords_from_world_coords(target.x, target.y)
                    draw_target_marker(screen, x, y, (120, 220, 255), max(8, R))
            except Exception:
                pass
        elif self.interface.zoom_mode and self.interface.zoom is not None:
            z = self.interface.zoom
            cx = (z.xmin + z.xmax) / 2.0
            cy = (z.ymin + z.ymax) / 2.0
            x, y = self._get_view_coords_from_world_coords(cx, cy)
            draw_target_marker(screen, x, y, (255, 210, 90), max(8, R))

        for uid in getattr(self.interface, "group", ()) or ():
            o = self.interface.dobjets.get(uid)
            if o is None or not self._is_object_visible(o):
                continue
            model = getattr(o, "model", o)
            orders = getattr(model, "orders", None) or []
            if not orders:
                continue
            dest = getattr(orders[0], "target", None)
            if dest is None or not hasattr(dest, "x"):
                continue
            try:
                x0, y0 = self.fx.lerped_screen_pos(
                    o.id, self._get_view_coords_from_world_coords(o.x, o.y)
                )
                x1, y1 = self._get_view_coords_from_world_coords(dest.x, dest.y)
                pygame.draw.line(screen, (100, 180, 220), (x0, y0), (x1, y1), 1)
                draw_target_marker(screen, x1, y1, (80, 200, 255), 6)
            except Exception:
                pass

    def _draw_minimap(self):
        from .clientgame.game_visual_fx import minimap_rect, soft_fog_color

        screen = get_screen()
        sw, sh = screen.get_width(), screen.get_height()
        cols = self.interface.xcmax + 1
        rows = self.interface.ycmax + 1
        left, top, w, h, cell = minimap_rect(sw, sh, cols, rows)
        self._minimap_hit = (left, top, w, h, cell, cols, rows)

        player = self.interface.player
        bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        bg.fill((8, 10, 16, 210))
        screen.blit(bg, (left - 2, top - 2))
        pygame.draw.rect(screen, (160, 170, 190), (left - 2, top - 2, w + 4, h + 4), 1)

        for xc in range(cols):
            for yc in range(rows):
                sq = player.world.grid.get((xc, yc))
                if sq is None:
                    continue
                px = left + xc * cell
                py = top + (rows - 1 - yc) * cell
                if sq in player.observed_squares:
                    col = square_color(sq)
                elif sq in player.observed_before_squares:
                    col = soft_fog_color(square_color(sq), 0.35)
                else:
                    col = (22, 24, 28)
                pygame.draw.rect(screen, col, (px, py, cell, cell))

        for o in self.interface.dobjets.values():
            place = getattr(o, "place", None)
            if place is None or not hasattr(place, "col"):
                continue
            if (
                place not in player.observed_squares
                and place not in player.observed_before_squares
            ):
                continue
            px = left + place.col * cell + cell // 2
            py = top + (rows - 1 - place.row) * cell + cell // 2
            pygame.draw.circle(
                screen, self._object_color(o), (px, py), max(1, cell // 4)
            )

        place = self.interface.place
        if place is not None and hasattr(place, "col"):
            px = left + place.col * cell
            py = top + (rows - 1 - place.row) * cell
            pygame.draw.rect(
                screen, (255, 230, 120), (px, py, cell, cell), max(1, cell // 6)
            )

    def minimap_square_from_mousepos(self, pos):
        from .clientgame.game_visual_fx import hit_test_minimap

        if not self._minimap_hit or self.interface.zoom_mode:
            return None
        hit = hit_test_minimap(pos, self._minimap_hit)
        if hit is None:
            return None
        return self.interface.server.player.world.grid.get(hit)

    def square_from_mousepos(self, pos):
        self._update_coefs()
        if self.interface.zoom_mode and self.interface.place is not None:
            if self.world_from_mousepos(pos) is not None:
                return self.interface.place
            return None
        x, y = pos
        ox, oy = self._map_origin
        if self.square_view_width <= 0 or self.square_view_height <= 0:
            return None
        xc = (x - ox) // self.square_view_width
        yc = (self.ymax - (y - oy)) // self.square_view_height
        if 0 <= xc <= self.interface.xcmax and 0 <= yc <= self.interface.ycmax:
            return self.interface.server.player.world.grid[(xc, yc)]

    def world_from_mousepos(self, pos):
        """Return world (x, y) under mouse, or None if outside the active view."""
        self._update_coefs()
        x, y = pos
        if self.interface.zoom_mode and self.interface.place is not None:
            sq = self.interface.place
            left, top, w, h = self._zoom_view_rect()
            if not (left <= x < left + w and top <= y < top + h):
                return None
            wx = sq.xmin + (x - left) / w * (sq.xmax - sq.xmin)
            wy = sq.ymax - (y - top) / h * (sq.ymax - sq.ymin)
            return wx, wy
        ox, oy = self._map_origin
        if self.square_view_width <= 0 or self.square_view_height <= 0:
            return None
        if not (
            ox <= x < ox + self.square_view_width * (self.interface.xcmax + 1)
            and oy <= y < oy + self.ymax
        ):
            return None
        sw = self.interface.world.square_width
        wx = (x - ox) / self.square_view_width * sw
        wy = (self.ymax - (y - oy)) / self.square_view_height * sw
        return wx, wy

    def move_zoom_to_mousepos(self, pos):
        """Move F8 zoom focus to the sub-cell under the mouse. Returns True if changed."""
        if not self.interface.zoom_mode or self.interface.zoom is None:
            return False
        world = self.world_from_mousepos(pos)
        if world is None:
            return False
        return self.interface.zoom.move_to_world(world[0], world[1])

    def object_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        best = None
        best_d = None
        for o in list(self.interface.dobjets.values()):
            if not self._is_object_visible(o):
                continue
            xo, yo = self._object_coords(o)
            d = square_of_distance(x, y, xo, yo)
            if d <= R2 + 1:  # is + 1 necessary?
                if best is None or d < best_d:
                    best = o
                    best_d = d
        return best

    def units_from_mouserect(self, pos, pos2):
        result = []
        self._update_coefs()
        x, y = pos
        x2, y2 = pos2
        if x > x2:
            x, x2 = x2, x
        if y > y2:
            y, y2 = y2, y
        for o in self.interface.units():
            if not self._is_object_visible(o):
                continue
            xo, yo = self._object_coords(o)
            if x < xo < x2 and y < yo < y2:
                result.append(o.id)
        return result

    def display_attack(self, attacker_id, target):
        a = self.interface.dobjets.get(attacker_id)
        if a is None or target is None:
            return
        self._update_coefs()
        if self.interface.player.is_an_enemy(a):
            color = (255, 80, 60)
        else:
            color = (80, 255, 120)
        ax, ay = self._object_coords(a)
        tx, ty = self._object_coords(target)
        self.fx.note_attack(ax, ay, tx, ty, color)
        tid = getattr(target, "id", None)
        if tid is not None:
            self.fx.note_hurt(tid)
        screen = get_screen()
        r1 = pygame.draw.line(screen, color, (tx, ty), (ax, ay), 2)
        r2 = pygame.draw.circle(
            screen, (220, 220, 220), (tx, ty), max(4, R * 3 // 2), 0
        )
        pygame.display.update(r1.union(r2))
