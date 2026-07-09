Battle shouts (layered combat audio)
====================================

Skirmish-only build (no legion formations). Three layers: **battlefield background**, **unit voice**, **event highlights**. Staggered playback with cooldowns.

Code: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``. Tests: ``test_battle_shout_audio.py``.

Triggers: either side has ≥ **5** fighting units in the square. Cooldowns: 10s global, 6s per square; 4s for charge/crit event shouts.

``style.txt``::

  def walking_unit
  shouts 1854

Full reference (Chinese): ``zh/mod/battle-shouts.rst``.
