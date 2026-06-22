"""vs_handler must display negative *_vs penalties (SC2 armor matrix)."""

import warnings
from types import SimpleNamespace

warnings.filterwarnings("ignore", category=DeprecationWarning)

from soundrts import msgparts as mp
from soundrts.attributes.vs_handler import VsHandler
from soundrts.lib.nofloat import PRECISION


def test_add_vs_attribute_includes_negative_values():
    handler = VsHandler(SimpleNamespace())
    attrs = []
    vs_dict = {"sc_massive": -4 * PRECISION}

    handler._add_vs_attribute(attrs, vs_dict, "mdg", precision_divide=True)

    assert len(attrs) == 1
    assert attrs[0][1] == mp.MDG_VS
    assert mp.VERSUS[0] in attrs[0][2]
    assert any("-4" in str(part) for part in attrs[0][2])
