from math import cos, radians, sin
import time

import pygame

from .definitions import style
from .lib.nofloat import PRECISION, square_of_distance
from .lib.screen import draw_line, draw_rect, get_screen
from .worldentity import COLLISION_RADIUS

R = 3
R2 = 9

# 大地图不整图缩小：偏好格像素；装不下则延伸到屏外，用边缘滚屏（帝国式）移动镜头
_PREFERRED_CELL_PX = 48
_MIN_CELL_PX = 16
_MAX_CELL_PX = 160
_ZOOM_CELL_LEVELS = (16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160)
_EDGE_SCROLL_MARGIN_PX = 14
_EDGE_SCROLL_SPEED_PX = 700.0  # 像素/秒

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
        self._view_rect = (0, 0, 1, 1)  # 主地图可视区（不含底栏 HUD）
        self._viewport_panned = False  # True：地图大于视口，可边缘滚屏
        # 自由镜头（帝国式）：与 interface.place 解耦，避免鼠标划过就跳屏
        self._cam_cell = None  # 用户滚轮缩放后的格像素；None=自动
        self._cam_origin = None  # (ox, oy)；None=下次按当前格居中初始化
        self._cam_force_center = True

    def _main_view_rect(self):
        """主地图可用矩形（为底栏命令卡/属性板留空）。"""
        screen = get_screen()
        sw, sh = screen.get_width(), screen.get_height()
        left, top = 8, 8
        right = sw - 8
        bottom = sh - 140
        if bottom - top < 120:
            bottom = sh - 12
        return left, top, max(1, right - left), max(1, bottom - top)

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
        # Deleted / despawned world models: keep out of the map (and stop warning spam).
        if getattr(o, "place", None) is None and not getattr(o, "is_inside", False):
            return False

        if self.interface.zoom_mode:
            # 缩放模式：显示当前主方格内全部单位（子格网格可见，便于鼠标点选）
            place = self.interface.place
            if place is None:
                return False
            if hasattr(o, "is_in"):
                return o.is_in(place)
            o_place = getattr(o, "place", None)
            return o_place is place

        # 俯视图：大地图时只画屏上附近的单位（迷雾仍由 dobjets 过滤）
        try:
            x, y = self._object_coords(o)
        except Exception:
            return True
        screen = get_screen()
        if screen is None:
            return True
        margin = max(24, int(getattr(self, "square_view_width", 48) or 48))
        sw, sh = screen.get_width(), screen.get_height()
        return -margin <= x <= sw + margin and -margin <= y <= sh + margin

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
        """Map client-scale coords (raw_world / 1000) to screen pixels.

        Same contract as SoundRTS 1.3.8.1: ``EntityView.x`` / ``interface.x``
        are already divided by 1000. Raw millisecond coords must go through
        ``_xy_coords`` first.
        """
        try:
            ox = float(ox)
            oy = float(oy)
        except (TypeError, ValueError):
            return 0, 0
        if self.interface.zoom_mode and self.interface.place is not None:
            sq = self.interface.place
            left, top, w, h = self._zoom_view_rect()
            xmin = sq.xmin / 1000.0
            xmax = sq.xmax / 1000.0
            ymin = sq.ymin / 1000.0
            ymax = sq.ymax / 1000.0
            x = int(left + (ox - xmin) / max(xmax - xmin, 1e-9) * w)
            y = int(top + (ymax - oy) / max(ymax - ymin, 1e-9) * h)
            return x, y
        sw = float(self.interface.square_width) or 1.0
        x = int(self._map_origin[0] + ox / sw * self.square_view_width)
        y = int(
            self._map_origin[1]
            + self.ymax
            - oy / sw * self.square_view_height
        )
        return x, y

    def _object_coords(self, o):
        # EntityView.x / .y are already /1000 (1.3.8.1)
        return self._get_view_coords_from_world_coords(o.x, o.y)

    def _xy_coords(self, ox, oy):
        # Square / model raw milliseconds → client scale (1.3.8.1)
        return self._get_view_coords_from_world_coords(ox / 1000.0, oy / 1000.0)

    def _target_view_coords(self, target):
        """Screen coords for an EntityView (scaled) or world object (raw)."""
        if target is None:
            return None
        if getattr(target, "model", None) is not None and hasattr(target, "interface"):
            return self._object_coords(target)
        return self._xy_coords(target.x, target.y)

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

    def _object_type_name(self, o):
        model = getattr(o, "model", o)
        return (
            getattr(o, "type_name", None)
            or getattr(model, "type_name", None)
            or getattr(model, "type", None)
            or ""
        )

    def _try_blit_map_anim(self, screen, o, x, y, *, size, color, selected, pulse):
        """Optional ``ui/anims/<type>/`` pack; returns True if drawn."""
        if size < 10:
            return False
        try:
            from .clientgame.game_unit_anim import try_blit_unit_anim

            facing = float(getattr(o, "o", 0) or 0)
            ok = try_blit_unit_anim(screen, o, x, y, size, facing=facing)
        except Exception:
            return False
        if not ok:
            return False
        # team outline so anim packs stay readable vs fog
        half = size // 2
        pygame.draw.rect(
            screen,
            color,
            pygame.Rect(int(x) - half - 1, int(y) - half - 1, size + 2, size + 2),
            2,
            border_radius=3,
        )
        if selected and pulse is not None:
            pygame.draw.rect(
                screen,
                pulse,
                pygame.Rect(int(x) - half - 3, int(y) - half - 3, size + 6, size + 6),
                2,
                border_radius=4,
            )
        return True

    def _try_blit_map_icon(self, screen, o, x, y, *, size, color, selected, pulse):
        """若 ``ui/map/<type>.png`` 存在则画在地图上，返回 True（不读 icons）。"""
        if size < 10:
            return False
        try:
            from .clientgame.game_hud import get_map_sprite

            icon = get_map_sprite(self._object_type_name(o), size)
        except Exception:
            return False
        if icon is None:
            return False
        rect = icon.get_rect(center=(int(x), int(y)))
        # 半透明阵营底，图标叠上更易辨认敌我
        pad = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
        fill = (*color[:3], 90)
        pygame.draw.rect(pad, fill, pad.get_rect(), border_radius=4)
        screen.blit(pad, pad.get_rect(center=(int(x), int(y))))
        screen.blit(icon, rect)
        pygame.draw.rect(screen, color, rect.inflate(2, 2), 2, border_radius=3)
        if selected and pulse is not None:
            pygame.draw.rect(screen, pulse, rect.inflate(6, 6), 2, border_radius=4)
            pygame.draw.rect(screen, (255, 255, 220), rect.inflate(2, 2), 1, border_radius=3)
        return True

    def display_object(self, o):
        # 检查对象是否可见
        if not self._is_object_visible(o):
            return

        target_xy = self._object_coords(o)
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

        # 绘制优先级：动画包 → ui/map PNG → 几何示意；特效仍叠在上层
        # （命令卡 icons 不参与地图绘制）
        icon_size = max(radius * 2, 12)
        if self.square_view_width >= 28:
            icon_size = max(icon_size, min(40, self.square_view_width // 3))
        used_sprite = False
        if kind in ("unit", "building", "resource"):
            used_sprite = self._try_blit_map_anim(
                screen,
                o,
                x,
                y,
                size=icon_size,
                color=color,
                selected=selected,
                pulse=pulse,
            )
            if not used_sprite:
                used_sprite = self._try_blit_map_icon(
                    screen,
                    o,
                    x,
                    y,
                    size=icon_size,
                    color=color,
                    selected=selected,
                    pulse=pulse,
                )
            if used_sprite:
                radius = max(radius, icon_size // 2)

        if not used_sprite:
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
            else:
                pygame.draw.circle(screen, color, (x, y), radius, 0)
                pygame.draw.circle(screen, (15, 15, 15), (x, y), radius, 1)
                if selected:
                    pygame.draw.circle(screen, pulse, (x, y), radius + 4, 2)
                    pygame.draw.circle(screen, (255, 255, 220), (x, y), radius + 2, 1)

        if kind == "resource":
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

    def _clamp_cam_origin(self, ox, oy, left, top, vw, vh, map_w, map_h):
        if map_w > vw:
            ox = min(left, max(left + vw - map_w, ox))
        else:
            ox = left + (vw - map_w) // 2
        if map_h > vh:
            oy = min(top, max(top + vh - map_h, oy))
        else:
            oy = top + (vh - map_h) // 2
        return int(ox), int(oy)

    def _origin_centered_on_place(self, left, top, vw, vh, cell, map_h):
        fxc, fyc = 0, 0
        place = getattr(self.interface, "place", None)
        if place is not None and hasattr(place, "col"):
            fxc = int(place.col)
            fyc = int(place.row)
        view_cx = left + vw // 2
        view_cy = top + vh // 2
        ox = view_cx - fxc * cell - cell // 2
        oy = view_cy - (map_h - fyc * cell - cell // 2)
        return ox, oy

    def center_on_square(self, square=None):
        """键盘/小地图跳格：把镜头对准当前格（或调用方已设好的 place）。"""
        self._cam_force_center = True
        self._cam_origin = None
        self._update_coefs()

    def pan_camera(self, dx, dy):
        """平移自由镜头（dx/dy 为屏幕像素：正 dx 让地图内容右移）。"""
        self._update_coefs()
        if not self._viewport_panned:
            return False
        ox, oy = self._map_origin
        left, top, vw, vh = self._view_rect
        cols = self.interface.xcmax + 1
        rows = self.interface.ycmax + 1
        map_w = self.square_view_width * cols
        map_h = self.ymax
        new_ox, new_oy = self._clamp_cam_origin(
            ox + dx, oy + dy, left, top, vw, vh, map_w, map_h
        )
        if (new_ox, new_oy) == (ox, oy):
            return False
        self._cam_origin = (new_ox, new_oy)
        self._cam_force_center = False
        self._map_origin = self._cam_origin
        return True

    def update_edge_scroll(self, dt):
        """鼠标贴主视口边缘时滚动地图。返回是否发生了平移。"""
        if self.interface.zoom_mode:
            return False
        self._update_coefs()
        if not self._viewport_panned:
            return False
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            return False
        # 在 HUD / 小地图上不边缘滚，避免抢命令条
        try:
            from .clientgame.game_hud import hit_test_hud

            if hit_test_hud(self.interface, (mx, my)) is not None:
                return False
        except Exception:
            pass
        if self._minimap_hit:
            ml, mt, mw, mh = self._minimap_hit[:4]
            if ml <= mx < ml + mw and mt <= my < mt + mh:
                return False

        left, top, vw, vh = self._view_rect
        margin = _EDGE_SCROLL_MARGIN_PX
        dx = dy = 0.0
        if mx <= left + margin:
            dx = 1.0
        elif mx >= left + vw - margin:
            dx = -1.0
        if my <= top + margin:
            dy = 1.0
        elif my >= top + vh - margin:
            dy = -1.0
        if dx == 0.0 and dy == 0.0:
            return False
        # 对角滚屏时速度归一，手感接近帝国
        length = (dx * dx + dy * dy) ** 0.5
        speed = _EDGE_SCROLL_SPEED_PX * max(0.0, min(float(dt), 0.05))
        return self.pan_camera(dx / length * speed, dy / length * speed)

    def zoom_at_mouse(self, pos, zoom_in):
        """滚轮缩放：以鼠标下地图点为锚，放大/缩小格像素。"""
        if self.interface.zoom_mode:
            return False
        self._update_coefs()
        x, y = pos
        if not self._pos_in_main_view(pos):
            return False
        old_cell = max(1, self.square_view_width)
        ox, oy = self._map_origin
        mx = x - ox
        my = y - oy

        left, top, vw, vh = self._view_rect
        cols = max(1, self.interface.xcmax + 1)
        rows = max(1, self.interface.ycmax + 1)
        fit = max(1, min(vw // cols, vh // rows))
        levels = [lv for lv in _ZOOM_CELL_LEVELS if lv >= min(_MIN_CELL_PX, fit)]
        if fit not in levels:
            levels = sorted(set(levels + [fit]))
        idx = min(range(len(levels)), key=lambda i: abs(levels[i] - old_cell))
        new_idx = idx + (1 if zoom_in else -1)
        if new_idx < 0 or new_idx >= len(levels):
            return False
        new_cell = levels[new_idx]
        if new_cell == old_cell:
            return False

        # 缩到刚好整图可装下时恢复自动适配
        if not zoom_in and new_cell <= fit:
            self._cam_cell = None
            self._cam_origin = None
            self._cam_force_center = True
            self._update_coefs()
            return True

        self._cam_cell = new_cell
        scale = new_cell / float(old_cell)
        self._cam_origin = (int(x - mx * scale), int(y - my * scale))
        self._cam_force_center = False
        self._update_coefs()
        return True

    def _update_coefs(self):
        global R, R2
        if self.interface.zoom_mode and self.interface.place is not None:
            left, top, w, h = self._zoom_view_rect()
            self._view_rect = (left, top, w, h)
            self._map_origin = (left, top)
            self.ymax = h
            self.square_view_width = max(1, w)
            self.square_view_height = max(1, h)
            self._viewport_panned = False
            precision = 3
            zoom = getattr(self.interface, "zoom", None)
            if zoom is not None:
                precision = getattr(zoom, "precision", 3) or 3
            cell = min(w, h) / max(precision, 1)
            R = max(6, int(cell * 0.28))
            R2 = R * R
            return

        left, top, vw, vh = self._main_view_rect()
        self._view_rect = (left, top, vw, vh)
        cols = self.interface.xcmax + 1
        rows = self.interface.ycmax + 1
        fit = max(1, min(vw // max(cols, 1), vh // max(rows, 1)))
        preferred = _PREFERRED_CELL_PX

        if self._cam_cell is not None:
            cell = max(_MIN_CELL_PX, min(_MAX_CELL_PX, int(self._cam_cell)))
        elif fit >= preferred:
            cell = fit
        else:
            cell = preferred

        map_w = cell * cols
        map_h = cell * rows
        self.square_view_width = self.square_view_height = cell
        self.ymax = map_h
        needs_pan = map_w > vw or map_h > vh

        if not needs_pan:
            # 整图可装下：居中，关闭边缘滚屏
            self._map_origin = (left + (vw - map_w) // 2, top + (vh - map_h) // 2)
            self._viewport_panned = False
            self._cam_origin = None
        else:
            # 地图大于视口：自由镜头 + 边缘滚屏（不再每帧跟随 place）
            if self._cam_force_center or self._cam_origin is None:
                ox, oy = self._origin_centered_on_place(left, top, vw, vh, cell, map_h)
                self._cam_origin = self._clamp_cam_origin(
                    ox, oy, left, top, vw, vh, map_w, map_h
                )
                self._cam_force_center = False
            else:
                self._cam_origin = self._clamp_cam_origin(
                    self._cam_origin[0],
                    self._cam_origin[1],
                    left,
                    top,
                    vw,
                    vh,
                    map_w,
                    map_h,
                )
            self._map_origin = self._cam_origin
            self._viewport_panned = True

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
                        self._xy_coords(ox, oy),
                        0,
                        0,
                    )

    def _display_active_zone_border(self):
        screen = get_screen()
        if self.interface.zoom_mode:
            zoom = self.interface.zoom
            left, bottom = self._xy_coords(zoom.xmin, zoom.ymin)
            right, top = self._xy_coords(zoom.xmax, zoom.ymax)
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
                    x, y = self._target_view_coords(target)
                    draw_target_marker(screen, x, y, (120, 220, 255), max(8, R))
            except Exception:
                pass
        elif self.interface.zoom_mode and self.interface.zoom is not None:
            z = self.interface.zoom
            cx = (z.xmin + z.xmax) / 2.0
            cy = (z.ymin + z.ymax) / 2.0
            x, y = self._xy_coords(cx, cy)
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
                x0, y0 = self.fx.lerped_screen_pos(o.id, self._object_coords(o))
                x1, y1 = self._target_view_coords(dest)
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

        # 大地图：在小地图上标出当前主画面视口（帝国式相机）
        if getattr(self, "_viewport_panned", False) and cell > 0:
            vl, vt, vw, vh = self._view_rect
            ox, oy = self._map_origin
            main_cell = max(1, self.square_view_width)
            map_w = main_cell * cols
            map_h = self.ymax
            # 可视区相对整图的比例
            x0 = (vl - ox) / float(map_w)
            y0 = (vt - oy) / float(map_h)
            x1 = (vl + vw - ox) / float(map_w)
            y1 = (vt + vh - oy) / float(map_h)
            x0, x1 = max(0.0, min(1.0, x0)), max(0.0, min(1.0, x1))
            y0, y1 = max(0.0, min(1.0, y0)), max(0.0, min(1.0, y1))
            rx = left + int(x0 * w)
            rw = max(2, int((x1 - x0) * w))
            ry = top + int(y0 * h)
            rh = max(2, int((y1 - y0) * h))
            pygame.draw.rect(screen, (255, 255, 255), (rx, ry, rw, rh), 1)

    def minimap_square_from_mousepos(self, pos):
        from .clientgame.game_visual_fx import hit_test_minimap

        if not self._minimap_hit or self.interface.zoom_mode:
            return None
        hit = hit_test_minimap(pos, self._minimap_hit)
        if hit is None:
            return None
        return self.interface.server.player.world.grid.get(hit)

    def _pos_in_main_view(self, pos):
        x, y = pos
        left, top, vw, vh = self._view_rect
        return left <= x < left + vw and top <= y < top + vh

    def square_from_mousepos(self, pos):
        self._update_coefs()
        if self.interface.zoom_mode and self.interface.place is not None:
            if self.world_from_mousepos(pos) is not None:
                return self.interface.place
            return None
        if not self._pos_in_main_view(pos):
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
        if not self._pos_in_main_view(pos):
            return None
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
        model = getattr(a, "model", a)
        ranged = bool(getattr(model, "rdg", 0) or getattr(model, "rdg_projectile", 0))
        self.fx.note_attack(ax, ay, tx, ty, color, ranged=ranged)
        tid = getattr(target, "id", None)
        if tid is not None:
            self.fx.note_hurt(tid)

    def display_launch(self, attacker, event_name="launch_rdg"):
        """Attack wind-up / shot leave the barrel (visual only)."""
        if attacker is None or not self.interface.display_is_active:
            return
        model = getattr(attacker, "model", attacker)
        action = getattr(model, "action", None)
        target = getattr(action, "target", None) if action is not None else None
        if target is None or not hasattr(target, "x"):
            # fall back: current interface target if same fight
            target = getattr(self.interface, "target", None)
        if target is None or not hasattr(target, "x"):
            return
        self._update_coefs()
        try:
            ax, ay = self._object_coords(attacker)
            # world target may be raw model — use _target_view_coords when possible
            if getattr(target, "model", None) is not None or target in getattr(
                self.interface, "dobjets", {}
            ).values():
                tx, ty = self._object_coords(target)
            else:
                # raw world object
                view = None
                tid = getattr(target, "id", None)
                if tid is not None:
                    view = self.interface.dobjets.get(tid)
                if view is not None:
                    tx, ty = self._object_coords(view)
                else:
                    tx, ty = self._xy_coords(target.x, target.y)
        except Exception:
            return
        if self.interface.player.is_an_enemy(attacker):
            color = (255, 100, 70)
        else:
            color = (120, 255, 140)
        if event_name.startswith("launch_rdg"):
            self.fx.note_shot(ax, ay, tx, ty, color)
        else:
            self.fx.note_slash(ax, ay, tx, ty, color)

    def display_gather(self, worker, resource_type="0"):
        if worker is None or not self.interface.display_is_active:
            return
        model = getattr(worker, "model", worker)
        orders = getattr(model, "orders", None) or []
        deposit = None
        if orders:
            deposit = getattr(orders[0], "target", None)
        self._update_coefs()
        try:
            wx, wy = self._object_coords(worker)
            if deposit is not None and hasattr(deposit, "x"):
                did = getattr(deposit, "id", None)
                dview = self.interface.dobjets.get(did) if did is not None else None
                if dview is not None:
                    mx, my = self._object_coords(dview)
                else:
                    mx, my = self._xy_coords(deposit.x, deposit.y)
            else:
                mx, my = wx + 8, wy
        except Exception:
            return
        self.fx.note_gather(wx, wy, mx, my, resource_type)

    def display_store(self, storage, resource_type="0"):
        if storage is None or not self.interface.display_is_active:
            return
        self._update_coefs()
        try:
            sx, sy = self._object_coords(storage)
        except Exception:
            return
        # nearest worker of same player with cargo (optional)
        wx, wy = sx - 12, sy
        player = getattr(storage, "player", None)
        for o in self.interface.dobjets.values():
            if getattr(o, "player", None) is not player:
                continue
            cargo = getattr(getattr(o, "model", o), "cargo", None)
            if cargo:
                try:
                    wx, wy = self._object_coords(o)
                    break
                except Exception:
                    pass
        self.fx.note_store(wx, wy, sx, sy, resource_type)