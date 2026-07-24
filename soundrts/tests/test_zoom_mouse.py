"""Zoom mouse helpers: move_to_world sub-cell math."""

from types import SimpleNamespace

from soundrts.clientgamefocus import Zoom


class _Place:
    def __init__(self):
        self.xmin = 0
        self.xmax = 120
        self.ymin = 0
        self.ymax = 120
        self.col = 0
        self.row = 0
        self.id = "a1"
        self.exits = []
        self.objects = []
        self.world = SimpleNamespace(subcell_precision=3, nb_columns=1, nb_lines=1, grid={(0, 0): self})


class _Iface:
    def __init__(self):
        self.place = _Place()
        self._zoom_precision = 3
        self.follow_mode = False
        self.target = None
        self.world = self.place.world

    def set_obs_pos(self):
        pass


def test_move_to_world_center():
    iface = _Iface()
    z = Zoom(iface)
    z.move_to_world(60, 60)
    assert z.sub_x == 0
    assert z.sub_y == 0


def test_move_to_world_corners_3x3():
    iface = _Iface()
    z = Zoom(iface)
    # southwest-ish
    z.move_to_world(10, 10)
    assert z.sub_x == -1
    assert z.sub_y == -1
    # northeast-ish
    z.move_to_world(110, 110)
    assert z.sub_x == 1
    assert z.sub_y == 1


def test_move_to_world_reports_change():
    iface = _Iface()
    z = Zoom(iface)
    z.sub_x = 0
    z.sub_y = 0
    z.update_coords()
    assert z.move_to_world(10, 10) is True
    assert z.move_to_world(10, 10) is False


def test_zoom_mouse_handlers_wired():
    from pathlib import Path

    text = Path("soundrts/clientgame/game_input_handler.py").read_text(encoding="utf-8")
    assert "def _process_zoom_mode_mouse_event" in text
    assert "move_zoom_to_mousepos" in text
    gv = Path("soundrts/clientgamegridview.py").read_text(encoding="utf-8")
    assert "def _display_zoom_square" in text or "def _display_zoom_square" in gv
    assert "def world_from_mousepos" in gv
    assert "def move_zoom_to_mousepos" in gv
