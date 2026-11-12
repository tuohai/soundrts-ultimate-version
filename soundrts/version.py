from hashlib import md5

from . import config
from .lib.resource import res

VERSION = "1.5.1.8"
IS_DEV_VERSION = config.debug_mode
CLIENT_COMPATIBILITY = "15"
SERVER_COMPATIBILITY = "0"


def server_is_compatible(version):
    if version in ["1.2-c12", "1.3.0", "1.3.1"]:
        version = "0"
    return version == SERVER_COMPATIBILITY


# The netcode protocol a client speaks.
#
# ``lockstep`` is the legacy protocol: the server waits for every player
# before it broadcasts a turn.  It is what every client used before the
# rollback work.
#
# ``rollback`` is the new protocol: the server stamps and broadcasts every
# input as it arrives, and the client predicts and rolls back.  It removes
# the "wait for the slowest player" barrier.
#
# The two coexist: a game is played with the rollback protocol only when
# *every* player speaks it.  Otherwise the game falls back to lockstep, so
# an old client can still play against a new server.
LOCKSTEP_PROTOCOL = "lockstep"
ROLLBACK_PROTOCOL = "rollback"
SUPPORTED_PROTOCOLS = (LOCKSTEP_PROTOCOL, ROLLBACK_PROTOCOL)
# The protocol a client uses when it does not say otherwise.
DEFAULT_PROTOCOL = LOCKSTEP_PROTOCOL


def client_protocol():
    """The protocol this client speaks.

    The rollback protocol is opt-in for now: it is a big change to the
    netcode, and a mismatch between the clients of a match would break it.
    Until it is proven in real matches, the default stays the legacy
    lockstep, and the user can switch it on in the configuration file.
    """
    try:
        enabled = int(getattr(config, "use_rollback_netcode", 0))
    except (AttributeError, TypeError, ValueError):
        enabled = 0
    if enabled:
        return ROLLBACK_PROTOCOL
    return DEFAULT_PROTOCOL


def negotiate_protocol(client_protocols):
    """The protocol a game uses, given the protocols its clients speak.

    The rollback protocol only works when *every* player understands it:
    the clients have to agree on which inputs are authoritative, and that
    is only possible if they all speak the same protocol.

    So the answer is the rollback protocol only when everybody asked for
    it; otherwise the game falls back to lockstep, which every client
    understands.
    """
    if not client_protocols:
        return DEFAULT_PROTOCOL
    if all(p == ROLLBACK_PROTOCOL for p in client_protocols):
        return ROLLBACK_PROTOCOL
    return LOCKSTEP_PROTOCOL


def compatibility_version():
    # Includes a hash of rules.txt.
    # (about the choice of MD5, check the comments in mapfile.py, line 45)
    # Don't check *.pyc (or library.zip, soundrts.exe and server.exe)
    # because it would require to add an internal version for every file.
    # (a bit complicated for the moment, and not as useful as checking rules.txt)
    return CLIENT_COMPATIBILITY + "-" + rules_hash()


def rules_hash():
    rules_and_ai = res.text("rules", append=True) + res.text("ai", append=True)
    return md5(rules_and_ai.encode()).hexdigest()


# VERSION_FOR_BUG_REPORTS helps ignoring automatic bug reports related to
# modified code.
try:
    with open("lib/full_version.txt") as t:
        VERSION_FOR_BUG_REPORTS = t.read()
except OSError:
    VERSION_FOR_BUG_REPORTS = VERSION
