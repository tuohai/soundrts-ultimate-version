Audio management (P0–P2 refactor)
==================================

SoundRTS 1.4.5.1 refactors the client audio engine in three phases. **P0 / P1 / P2 are refactor stages** (structure → UX → polish), **not** the three battle-shout layers, and **not** the numeric ``priority`` passed to ``psounds.play()`` for channel preemption.

Layered battle shouts (``shout_bg`` / ``shout_unit`` / ``shout_event``) are documented in :doc:`battle-shouts`.

.. contents::

Architecture
------------

::

  clientmain → clientmedia.init_media()
    ├─ sound.init()           pygame.mixer, channel 0 reserved for voice
    ├─ sounds.load_default()  index ui/ SFX, decode on demand
    └─ voice.init()           voice queue + TTS

  Runtime:
    channel 0      → UI voice / narration (VoiceChannel)
    channel 1..N   → game SFX (SoundManager / psounds)
    music stream   → background music (pygame.mixer.music)

Key modules:

+---------------------------+------------------------------------------+
| Module                    | Role                                     |
+===========================+==========================================+
| ``lib/sound.py``          | mixing, stereo pan, channels, BGM state  |
| ``lib/sound_cache.py``    | layered resource index, lazy load, preload |
| ``lib/music_resolver.py`` | menu/game/battle/victory/defeat lookup   |
| ``lib/battle_music.py``   | enter/stop battle music state machine    |
| ``lib/voice.py``          | spoken UI queue                          |
| ``clientmedia.py``        | volume adjustment entry points           |

P0 — structural refactor
------------------------

**Goals**: shrink the monolithic ``sound.py``, control memory when switching mods, fix class-level mutable state.

**Music resolver module (``music_resolver.py``)**

- Centralizes ``find_music_file()`` and map/campaign package lookup.
- Shared helpers: ``find_map_or_campaign_asset()``, ``get_active_context()``, ``clear_music_cache()``.
- ``play_game_music``, ``play_battle_music``, victory/defeat stingers share one lookup chain.

**Explicit SFX cache recycle (``sound_cache.clear_decoded()``)**

- On ``load_default()`` when switching mod/campaign/map: ``psounds.stop()``, clear rate-limit timestamps, rebuild layers.

**Instance state fixes**

- ``SoundSource``, ``LoopingSoundSource``, ``SoundManager`` move ``channel``, ``_sources``, ``_start_time`` into ``__init__``.

**Tests**: ``test_music_resolver.py``

P1 — UX and performance
-----------------------

**Separate game SFX volume (``sfx_volume``)**

- Config key ``audio/sfx_volume`` (default 0.5) in ``SoundRTS.ini``.
- **Voice/UI** uses ``main_volume``; **battle SFX** (footsteps, combat, ambience loops) uses ``sfx_volume``.
- In-game ``cmd_sfx_volume``; adjustable in menu and match.

**Non-blocking voice wait**

- ``voice._say_now()`` / ``flush()`` use ``pygame.event.pump()`` + ``Clock.tick(30)`` instead of ``time.sleep(0.1)``.

**Unified menu music fallback**

- ``_play_menu_music_with_fallback()`` merges duplicate fallback logic in campaign picker, game creation, and server lobby.

**Tests**: ``test_audio_settings.py``, ``test_voice_pump.py``

P2 — polish
-----------

**P2a — smooth ambience**

- ``ambient_volume()`` uses a slow position-based LFO (~8 s) instead of per-frame ``random.random()``.

**P2b — battle music controller (``battle_music.py``)**

- Centralizes enemy-in-vision checks and enter/stop battle BGM.
- Replaces scattered logic in ``combat.py``, ``game_display.py``, ``game_navigation.py``.

**P2c — ``music_resolver`` cleanup**

- Remove unreachable branches; add lookup tests.

**P2d — multi-format SFX and hot preload**

Game SFX under ``ui/`` support:

- ``.ogg`` (preferred)
- ``.wav``
- ``.mp3``

When multiple formats share a stem, ``.ogg`` wins. IDs may be written as ``footstep``, ``footstep.wav``, or ``1029.mp3``.

Hot preload: background thread reads bytes; main thread decodes via ``tick_preload()`` (pygame thread safety). Optional ``parameters.txt``::

  preload_sounds 4303,4304
  preload_decode_per_tick 6

**Tests**: ``test_ambient_stereo_volume.py``, ``test_battle_music.py``, ``test_sfx_formats.py``

Volumes and hotkeys
-------------------

+------------------+----------------------------+----------------------------------+
| Volume           | Config key                 | Typical adjustment               |
+==================+============================+==================================+
| Voice / UI       | ``audio/main_volume``      | optional (external screen readers) |
+------------------+----------------------------+----------------------------------+
| Game SFX         | ``audio/sfx_volume``       | Home up / End down               |
+------------------+----------------------------+----------------------------------+
| Music            | ``audio/music_volume``     | Alt+Home / Alt+End               |
+------------------+----------------------------+----------------------------------+

Mixer buffer and sample rate
----------------------------

``pygame.mixer.pre_init`` reads these from ``SoundRTS.ini`` at startup (``user/SoundRTS.ini`` or ``%APPDATA%/SoundRTS/SoundRTS.ini`` on Windows)::

  [audio]
  mixer_buffer = 2048
  mixer_frequency = 44100

  [general]
  num_channels = 16

+-------------------+---------+--------------------------------------------------+
| Key               | Default | Notes                                            |
+===================+=========+==================================================+
| ``mixer_buffer``  | 2048    | Samples per SDL buffer. Larger = stabler SFX     |
|                   |         | under load, slightly higher latency. Allowed:    |
|                   |         | ``512``, ``1024``, ``2048``, ``4096``, ``8192``  |
|                   |         | (other values snap to the nearest).              |
+-------------------+---------+--------------------------------------------------+
| ``mixer_frequency`` | 44100 | Output sample rate in Hz (``22050``–``48000``).  |
+-------------------+---------+--------------------------------------------------+
| ``num_channels``  | 16      | Concurrent SFX channels (try ``32`` if busy).    |
+-------------------+---------+--------------------------------------------------+

Rough latency for common buffers at 44100 Hz: ``1024``≈23ms (more underruns in
heavy matches), ``2048``≈46ms (default), ``4096``≈93ms (try if SFX still
stutter). **Restart the game** after editing these keys — the mixer cannot
re-init mid-session. Older ini files missing the keys get defaults on the next
launch.

For mod authors
---------------

- Place SFX in ``ui/`` or ``mods/<mod>/ui/``.
- ``.ogg`` is still recommended for size; ``.wav`` / ``.mp3`` work without conversion.
- If ``ui/tts.txt`` already defines the same ID as text, that ID is not loaded as audio.

**Not the same as battle-shout layers**

+----------------------+--------------------------------+---------------------------+
| Concept              | Meaning                        | Doc                       |
+======================+================================+===========================+
| P0–P2 refactor       | engine modules, volume, formats| this page                 |
+----------------------+--------------------------------+---------------------------+
| Shout layers         | ``shout_bg`` / unit / event    | :doc:`battle-shouts`      |
+----------------------+--------------------------------+---------------------------+
| Channel priority int | ``psounds.play`` preemption    | ``lib/sound.py``          |

Early 1.4.5.1 release-note drafts incorrectly described P0–P2 as ambient/combat/alert priority tiers; the release notes have been corrected.
