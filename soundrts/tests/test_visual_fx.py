"""Visual polish helpers for Ctrl+F2 (fog, minimap, fx)."""

from soundrts.clientgame.game_visual_fx import (
    VisualFxState,
    fog_edge_strength,
    hit_test_minimap,
    minimap_rect,
    soft_fog_color,
)


def test_soft_fog_blends():
    deep = soft_fog_color((100, 150, 80), 0.0)
    soft = soft_fog_color((100, 150, 80), 1.0)
    assert soft[1] >= deep[1]


def test_minimap_hit_flip_y():
    # 4x4 map, cell 10 → rect 40x40 at (0,0)
    hit = (0, 0, 40, 40, 10, 4, 4)
    assert hit_test_minimap((5, 5), hit) == (0, 3)  # top-left screen → high row
    assert hit_test_minimap((35, 35), hit) == (3, 0)
    assert hit_test_minimap((100, 100), hit) is None


def test_visual_fx_attack_spawns_particles():
    fx = VisualFxState()
    fx.note_attack(0, 0, 20, 20, (255, 0, 0))
    assert fx.particles
    assert fx.attack_beams


def test_lerp_snaps_on_teleport():
    fx = VisualFxState()
    assert fx.lerped_screen_pos("u1", (10, 10)) == (10, 10)
    x, y = fx.lerped_screen_pos("u1", (12, 12))
    assert abs(x - 10) <= 3
    # large jump snaps
    assert fx.lerped_screen_pos("u1", (500, 500)) == (500, 500)


def test_gridview_wires_minimap_and_fx():
    from pathlib import Path

    text = Path("soundrts/clientgamegridview.py").read_text(encoding="utf-8")
    assert "_draw_minimap" in text
    assert "soft_fog_color" in text
    assert "lerped_screen_pos" in text
    assert "_draw_order_progress" in text
    assert "note_attack" in text
    inp = Path("soundrts/clientgame/game_input_handler.py").read_text(encoding="utf-8")
    assert "minimap_square_from_mousepos" in inp
