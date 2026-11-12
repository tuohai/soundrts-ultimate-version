"""Networking / netcode support for SoundRTS.

Currently holds the rollback-netcode building blocks:

- :mod:`soundrts.net.snapshot` — layered world snapshots (capture/restore)
  plus a strong digest used to verify a restored world.
- :mod:`soundrts.net.rollback` — a ring buffer of snapshots with rollback
  and replay.
- :mod:`soundrts.net.input_stream` — the authoritative input stream that
  replaces the lockstep "wait for everybody" barrier.

The legacy lockstep path still lives in ``serverroom.py`` / ``worldclient.py``
and is selected by the protocol version.
"""

__all__ = ["snapshot", "rollback", "input_stream"]
