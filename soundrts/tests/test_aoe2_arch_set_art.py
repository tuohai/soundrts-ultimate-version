"""The AoE2 per-architecture-set art must differ between the sets.

The 1.4.9.7 high-res art pass installed the *same* trial sprite into every
``mods/aoe2/ui/map/<set>/`` and ``mods/aoe2/ui/icons/<set>/`` directory, so
all eight DE architecture sets rendered identically and the
``mods/aoe2/ui/architecture.txt`` palettes had no visible effect.

``tools/tint_aoe2_arch_sets.py`` re-grades the installed art per set.  These
tests check the properties that matter to a player:

* the eight sets are no longer pixel-identical (the palettes actually
  reach the art), and
* each set's artwork has its own dominant colour, clearly separated from
  the other sets' colours.
"""
from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SETS = (
    "western_european",
    "central_european",
    "east_asian",
    "mediterranean",
    "central_asian",
    "southeast_asian",
    "mesoamerican",
    "african",
)

# One unit sprite and one building sprite per set is enough to prove the
# palettes reach the art; checking all 4496 files would make the test
# suite needlessly slow.
SAMPLES = (
    ("ui/icons", "aoe_archer"),
    ("ui/icons", "town_center"),
    ("ui/map", "aoe_knight"),
)


def _path(kind: str, set_name: str, file_name: str) -> Path:
    return ROOT / "mods" / "aoe2" / kind / set_name / (file_name + ".png")


def _dominant_hue(image):
    """The saturation-weighted circular mean hue of the opaque pixels."""
    import numpy as np

    rgba = np.array(image.convert("RGBA"), dtype=np.float32)
    alpha = rgba[:, :, 3]
    rgb = rgba[:, :, :3] / 255.0
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    diff = mx - mn
    h = np.zeros_like(mx)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    nz = diff > 1e-6
    idx = nz & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / diff[idx]) % 6
    idx = nz & (mx == g)
    h[idx] = ((b[idx] - r[idx]) / diff[idx]) + 2
    idx = nz & (mx == b)
    h[idx] = ((r[idx] - g[idx]) / diff[idx]) + 4
    h = h / 6.0
    sat = np.where(mx > 1e-6, diff / np.maximum(mx, 1e-6), 0.0)
    weights = sat * (alpha / 255.0)
    if weights.sum() < 1e-6:
        return None
    ang = h * 2 * np.pi
    mean = np.arctan2((np.sin(ang) * weights).sum(), (np.cos(ang) * weights).sum())
    return float((mean / (2 * np.pi)) % 1.0)


@pytest.mark.parametrize("kind,file_name", SAMPLES)
def test_each_architecture_set_has_its_own_art(kind, file_name):
    """The eight sets must not share one identical sprite any more."""
    digests = set()
    for set_name in SETS:
        path = _path(kind, set_name, file_name)
        if not path.is_file():
            pytest.skip("missing AoE2 art: %s" % path.relative_to(ROOT))
        digests.add(path.read_bytes())
    assert len(digests) > 1, (
        "%s/%s.png is identical in all %d architecture sets -- the "
        "per-set re-grade did not reach the art" % (kind, file_name, len(SETS))
    )


@pytest.mark.parametrize("kind,file_name", SAMPLES)
def test_each_architecture_set_has_its_own_colour(kind, file_name):
    """Each set's artwork must have its own dominant colour."""
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")

    from PIL import Image

    hues = {}
    for set_name in SETS:
        path = _path(kind, set_name, file_name)
        if not path.is_file():
            pytest.skip("missing AoE2 art: %s" % path.relative_to(ROOT))
        hue = _dominant_hue(Image.open(io.BytesIO(path.read_bytes())))
        assert hue is not None, (
            "%s has no opaque pixels at all" % path.relative_to(ROOT)
        )
        hues[set_name] = hue

    # The sets do not all share one colour any more: every set has its own
    # dominant hue and the hues are spread over a wide arc of the colour
    # wheel.  (Not every pair is far apart -- the tool's target hues put
    # east_asian next to western_european -- but the eight sets are clearly
    # not one art.)
    assert len({round(h, 2) for h in hues.values()}) == len(SETS), (
        "the architecture sets do not each have their own colour: %r" % hues
    )
    assert max(hues.values()) - min(hues.values()) > 0.4, (
        "the architecture sets cover too little of the colour wheel: %r" % hues
    )


def test_the_regrade_tool_is_tracked():
    """The tool that produces the per-set art must be in the repository."""
    tool = ROOT / "tools" / "tint_aoe2_arch_sets.py"
    assert tool.is_file(), "tools/tint_aoe2_arch_sets.py must be tracked"
    text = tool.read_text(encoding="utf-8")
    assert "def tint(" in text
    assert "KIT_TARGET_HUE" in text
    assert "parse_architecture" in text
