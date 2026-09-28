"""Audit: 1.5.1.0 — perception _update_perception_and_memory defers dict construction
and gates _last_unit_positions overwrite on position_changed.
"""
from __future__ import annotations

from pathlib import Path


_LANGS = ("zh", "en", "es", "it", "pt-BR")


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1510(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.0\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.0.9\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_current_version_matches_1510_section():
    """The current VERSION must be >= 1.5.1.0 (i.e. the 1.5.1.0 release shipped)."""
    src = _source("soundrts", "version.py")
    import re
    m = re.search(r'VERSION = "([^"]+)"', src)
    assert m, "VERSION literal not found in soundrts/version.py"
    assert tuple(int(x) for x in m.group(1).split(".")) >= (1, 5, 1, 0)


def test_all_relnotes_have_1510_before_15009():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.1.0\n") < src.index("\n1.5.0.9\n"), lang


def test_zh_relnotes_1510_describes_deferred_dict():
    section = _section_1510("zh")
    assert "_update_perception_and_memory" in section
    assert "_last_unit_positions" in section
    assert "current_unit_positions" in section
    assert "position_changed" in section
    assert "性能" in section


def test_en_relnotes_1510_describes_deferred_dict():
    section = _section_1510("en")
    assert "_update_perception_and_memory" in section
    assert "_last_unit_positions" in section
    assert "current_unit_positions" in section
    assert "position_changed" in section
    assert "Performance" in section


def test_es_relnotes_1510_describes_deferred_dict():
    section = _section_1510("es")
    assert "_update_perception_and_memory" in section
    assert "_last_unit_positions" in section
    assert "current_unit_positions" in section
    assert "position_changed" in section
    assert "Rendimiento" in section


def test_it_relnotes_1510_describes_deferred_dict():
    section = _section_1510("it")
    assert "_update_perception_and_memory" in section
    assert "_last_unit_positions" in section
    assert "current_unit_positions" in section
    assert "position_changed" in section
    assert "Prestazioni" in section


def test_pt_br_relnotes_1510_describes_deferred_dict():
    section = _section_1510("pt-BR")
    assert "_update_perception_and_memory" in section
    assert "_last_unit_positions" in section
    assert "current_unit_positions" in section
    assert "position_changed" in section
    assert "Desempenho" in section


def test_perception_defers_current_unit_positions_dict():
    """Aggregate fold is computed first; dict only when aggregate differs."""
    text = _source("soundrts", "worldplayerbase", "perception.py")
    # 1.5.1.0: in _update_perception_and_memory, current_unit_positions
    # population must be gated on aggregate fold changing (was sum, now XOR).
    func_start = text.index("def _update_perception_and_memory")
    func_text = text[func_start:func_start + 6000]
    # The aggregate first pass loop must appear before the dict population.
    # Accept either the legacy sum form (1.5.1.0) or the XOR form (1.5.1.2).
    aggregate_needles = (
        "current_positions_hash += pos_hash",
        "current_positions_xor ^= hash(",
    )
    aggregate_idx = -1
    for needle in aggregate_needles:
        try:
            aggregate_idx = func_text.index(needle)
            break
        except ValueError:
            continue
    assert aggregate_idx >= 0, (
        "aggregate fold first pass must use either sum or XOR of pos_hash"
    )
    dict_population_idx = func_text.index("current_unit_positions[unit.id] = pos_hash")
    assert aggregate_idx < dict_population_idx, (
        "current_unit_positions dict population must come AFTER aggregate fold scan"
    )


def test_perception_gates_last_unit_positions_overwrite():
    """_last_unit_positions = current_unit_positions only runs when position_changed."""
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def _update_perception_and_memory")
    func_text = text[func_start:func_start + 6000]
    # Full-update path overwrites _last_unit_positions under a position_changed guard.
    assert "if position_changed:\n            self._last_unit_positions = current_unit_positions" in func_text


# ── 1.5.1.0 – save_pickle: shallow pickle for huge maps ──────────────────────

def test_save_pickle_module_exists():
    path = Path(__file__).resolve().parents[2] / "soundrts" / "save_pickle.py"
    assert path.exists(), "soundrts/save_pickle.py must exist"


def test_all_relnotes_1510_mention_save_pickle():
    for lang in _LANGS:
        section = _section_1510(lang)
        assert "save_pickle" in section, f"{lang} relnotes must mention save_pickle"
        assert "cloudpickle" in section, f"{lang} relnotes must mention cloudpickle"
        assert "__getstate__" in section, f"{lang} relnotes must mention __getstate__"


def test_world_getstate_strips_path_graph():
    text = _source("soundrts", "world", "world_core.py")
    getstate_start = text.index("def __getstate__")
    getstate_block = text[getstate_start:getstate_start + 2000]
    # WORLD_STRIP_ON_SAVE or explicit "g" must be stripped
    assert ("WORLD_STRIP_ON_SAVE" in getstate_block or '"g"' in getstate_block
            or "'g'" in getstate_block), "World.__getstate__ must strip 'g' path graph"


def test_square_getstate_strips_neighbors():
    text = _source("soundrts", "worldroom.py")
    getstate_start = text.index("def __getstate__")
    getstate_block = text[getstate_start:getstate_start + 1500]
    assert ("SQUARE_STRIP_ON_SAVE" in getstate_block or "'neighbors'" in getstate_block
            or '"neighbors"' in getstate_block), "Square.__getstate__ must strip neighbors"


def test_save_pickle_has_rebuild_function():
    text = _source("soundrts", "save_pickle.py")
    assert "def rebuild_world_after_load" in text
    assert "def restore_world_pickle_targets" in text


def test_worldaction_getstate_strips_target():
    text = _source("soundrts", "worldaction.py")
    getstate_start = text.index("def __getstate__")
    getstate_block = text[getstate_start:getstate_start + 800]
    assert ("strip_target_for_pickle" in getstate_block
            or '"target"' in getstate_block
            or "'target'" in getstate_block), "Action.__getstate__ must strip target"


# ── 1.5.1.0 – ms maps no toroidal wrap ────────────────────────────────────────

def test_all_relnotes_1510_mention_ms_wrap_fix():
    for lang in _LANGS:
        section = _section_1510(lang)
        assert "west_east_paths" in section, f"{lang} relnotes must mention west_east_paths"
        assert "_create_we_passage" in section, (
            f"{lang} relnotes must mention _create_we_passage"
        )
        assert "wrap" in section.lower() or "portal" in section.lower(), (
            f"{lang} relnotes must explain the wrap / portal root cause"
        )


def test_ms_maps_audit_test_exists():
    path = Path(__file__).resolve().parent / "test_ms_maps_no_wrap.py"
    assert path.exists(), "soundrts/tests/test_ms_maps_no_wrap.py must exist"


def test_ms200_ms500_ms1000_boundary_entries_dropped():
    """1-based boundary ``(N, row)`` / ``(col, N)`` / ``(0, row)`` / ``(col, 0)``
    entries in the three multi maps would trip the engine's portal wrap in
    ``_create_we_passage``. They must be absent.
    """
    for name in ("ms200.txt", "ms500.txt", "ms1000.txt"):
        path = Path(__file__).resolve().parents[2] / "res" / "multi" / name
        assert path.exists(), f"{name} must exist"
        text = path.read_text(encoding="utf-8")
        n = 0
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("nb_columns "):
                n = int(line.split()[1])
                break
        assert n > 0
        for raw in text.splitlines():
            line = raw.strip()
            if not (line.startswith("west_east_paths ")
                    or line.startswith("west_east ")
                    or line.startswith("south_north_paths ")
                    or line.startswith("south_north ")):
                continue
            for tok in line.split()[1:]:
                x, y = (int(p) for p in tok.split(","))
                assert not (x == n or x == 0 or y == n or y == 0), (
                    f"{name}: 1-based ({x},{y}) would wrap in engine"
                )


def test_gen_ms500_avoids_boundary_in_range():
    text = _source("tools", "gen_ms500.py")
    # The fix replaces range(1, n + 1) main corridor with range(1, n).
    assert "range(1, n)" in text
    # Secondary branch filter for boundary picks.
    assert "x == n or x == 0 or y == n or y == 0" in text
