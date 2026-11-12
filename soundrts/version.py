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


# The revision of each protocol.
#
# A *protocol* says which netcode is used (lockstep or rollback); a
# *revision* says which version of that netcode's wire format and
# semantics the speaker implements.  They are separate numbers because
# the two protocols evolve independently: a bug fix in the rollback netcode
# does not change the lockstep wire format, and vice versa.
#
# Compatibility rules
# -------------------
#
# * A client announces ``<protocol>/<revision>`` at login time (the
#   ``login`` line).  An old client announces nothing but the protocol
#   name, which is understood as revision 1.
# * Two peers are compatible for a given protocol when they announce the
#   *same* revision of it.  A different revision means the wire format or
#   the frame semantics changed, so mixing them would silently corrupt the
#   match: the client and the server would disagree on what a frame is,
#   or on the order in which inputs are applied.
# * The rollback protocol is only used when **every** player speaks it
#   *and* all of them speak the same revision of it.  Otherwise the game
#   falls back to lockstep, which every client understands.
#
# Bumping a revision
# ------------------
#
# Bump ``PROTOCOL_REVISIONS[protocol]`` whenever the wire format or the
# frame semantics of that protocol change in a way that an older peer
# could not understand.  The bump is what makes the two sides fall back
# to a protocol they both speak, instead of corrupting the match.
PROTOCOL_REVISIONS = {
    LOCKSTEP_PROTOCOL: 1,
    ROLLBACK_PROTOCOL: 1,
}

# The revision this build speaks for each protocol it supports.  It is the
# same table for the client and the server: both are the same codebase.
CURRENT_PROTOCOL_REVISIONS = dict(PROTOCOL_REVISIONS)


def protocol_revision(protocol: str) -> int:
    """The revision of *protocol* this build speaks.

    An unknown protocol has no revision: 0 means "I do not speak it",
    which is different from "I speak revision 1 of it".
    """
    try:
        return int(PROTOCOL_REVISIONS.get(protocol, 0))
    except (TypeError, ValueError):
        return 0


def protocol_token(protocol: str = None) -> str:
    """The token a client announces at login time.

    The token is ``<protocol>/<revision>`` -- for example ``rollback/1``.
    A bare protocol name (``rollback``) is also understood and means
    revision 1: that is what an old client sends, and it is the whole
    point of the revision being 1 for a freshly introduced protocol.
    """
    if protocol is None:
        protocol = DEFAULT_PROTOCOL
    revision = protocol_revision(protocol)
    if revision <= 0:
        # Unknown protocol: announce it as revision 1 so that the server
        # can at least parse it (and reject it as unknown).
        return "%s/1" % protocol
    return "%s/%d" % (protocol, revision)


def parse_protocol_token(token: str):
    """Parse a protocol token into ``(protocol, revision)``.

    Returns ``(protocol, revision)``.  A token without a revision is
    understood as revision 1, which is what an old client sends.

    Raises:
        ValueError: when the token is not a protocol name at all.
    """
    if token is None:
        raise ValueError("no protocol token")
    text = str(token).strip()
    if not text:
        raise ValueError("empty protocol token")
    protocol, sep, revision_part = text.partition("/")
    protocol = protocol.strip()
    if not protocol:
        raise ValueError("malformed protocol token: %r" % (token,))
    if not sep:
        # A bare protocol name: revision 1 (the original wire format).
        return protocol, 1
    try:
        revision = int(revision_part)
    except (TypeError, ValueError):
        raise ValueError("malformed protocol revision: %r" % (token,))
    return protocol, revision


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


def client_protocol_token() -> str:
    """The token this client announces at login time."""
    return protocol_token(client_protocol())


def protocols_compatible(protocol_a: str, revision_a: int,
                          protocol_b: str, revision_b: int) -> bool:
    """Can two peers play together with these protocols and revisions?

    They can when they speak the *same* protocol at the *same* revision.
    """
    if protocol_a != protocol_b:
        return False
    return int(revision_a) == int(revision_b)


def negotiate_protocol(client_protocols, client_revisions=None):
    """The protocol a game uses, given the protocols its clients speak.

    The rollback protocol only works when *every* player understands it:
    the clients have to agree on which inputs are authoritative, and that
    is only possible if they all speak the same protocol.

    So the answer is the rollback protocol only when everybody asked for
    it; otherwise the game falls back to lockstep, which every client
    understands.

    When the clients disagree on the *revision* of the rollback protocol,
    the game also falls back to lockstep: the revisions differ, which
    means the wire format or the frame semantics differ, and the match
    would corrupt silently.

    Args:
        client_protocols: the protocol each client announced.
        client_revisions: the revision each client announced, in the
            same order.  ``None`` means "revision 1 for everybody", which
            is what the pre-revision protocol did.
    """
    if not client_protocols:
        return DEFAULT_PROTOCOL
    if client_revisions is None:
        client_revisions = [1] * len(client_protocols)
    if len(client_revisions) != len(client_protocols):
        client_revisions = list(client_revisions) + [1] * (
            len(client_protocols) - len(client_revisions)
        )
    if all(p == ROLLBACK_PROTOCOL for p in client_protocols):
        revisions = {int(r) for r in client_revisions}
        if len(revisions) == 1:
            return ROLLBACK_PROTOCOL
        # Different revisions of the rollback protocol: the clients do not
        # agree on what a frame is.  Fall back to the protocol everybody
        # understands.
        warning_message = (
            "rollback protocol revision mismatch (%s), falling back to %s"
            % (sorted(revisions), LOCKSTEP_PROTOCOL)
        )
        _log_protocol_warning(warning_message)
        return LOCKSTEP_PROTOCOL
    return LOCKSTEP_PROTOCOL


def _log_protocol_warning(message: str) -> None:
    try:
        from .lib.log import warning

        warning(message)
    except Exception:  # pragma: no cover - logging must never break a match
        pass


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
