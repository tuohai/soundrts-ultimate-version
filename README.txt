SoundRTS is a real-time strategy audio game.

Feel free to experiment on the code base, but don't feel obliged to contribute back.

The license for the Python source code is a BSD 3-clause license (LICENSE.txt).
The license for the rest is unclear at the moment.

Tested with Python 3.11.

To install the requirements:
pip install -r requirements.txt -U

Running server.py doesn't require any package.

The optional upnpclient package can help for the configuration of your router.

Running soundrts.py requires:
* pygame
* accessible_output2

Building a package requires also:
* docutils
* cx_Freeze

Testing requires:
* pytest

Building Cython extensions (optional, for full performance):
* Python 3.11 (tested); on Windows you also need MSVC Build Tools
* pip install -r requirements-build.txt
* python setup_cython.py build_ext --inplace
* verify: python -m pytest soundrts/tests/test_combat_fast_parity.py -q
Without compiled extensions the game still runs (Python fallback) but large
maps with many AIs will be noticeably slower.

Official SoundRTS web site: http://jlpo.free.fr/soundrts
