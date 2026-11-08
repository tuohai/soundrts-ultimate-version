"""Per-world perception cache containers.

Why this module exists
----------------------
The perception / vision / neighbor caches used to be *class* attributes on
``Player``.  A live match and a spectator rebuild run side by side inside the
same Python process and hand out the **same** player ids ("86", "87", ...),
so any class-level cache bled from one world into the other: the spectator
read the live world's observed squares / enemy lists and the two simulations
forked.

The caches now live on the ``World`` instance (``World._perception_caches``).
This module provides:

* :func:`shared_perception_caches` — process-wide fallback container, used by
  stubs that have no ``world`` attribute at all.
* :class:`PerceptionCachesMixin` — the ``_pcaches`` property, mixed into both
  the player base class and the perception mixin so that code using either
  one on its own keeps working.
"""

_SHARED_PERCEPTION_CACHES = None


def shared_perception_caches():
    """Process-wide fallback cache container (used by world-less stubs)."""
    global _SHARED_PERCEPTION_CACHES
    if _SHARED_PERCEPTION_CACHES is None:
        from ..world.world_core import _PerceptionCaches

        _SHARED_PERCEPTION_CACHES = _PerceptionCaches()
    return _SHARED_PERCEPTION_CACHES


class PerceptionCachesMixin:
    """Gives a player-like object access to its world's perception caches."""

    @property
    def _pcaches(self):
        """The per-world perception cache container.

        Falls back to a process-wide shared container when the player has no
        world (unit-test stubs) so that the perception code never has to
        guard against a missing attribute.
        """
        caches = getattr(getattr(self, "world", None), "_perception_caches", None)
        if caches is None:
            caches = shared_perception_caches()
        return caches
