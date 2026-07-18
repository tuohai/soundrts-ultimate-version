Primary and secondary voice libraries (players)
================================================


The game uses two independently configurable voice libraries: primary and secondary. You can enable or disable the secondary library; when disabled, the primary library speaks everything.


----


Duties
------


.. list-table::
   :header-rows: 1

   * - Library
     - Speaks
   * - **Primary**
     - Menus, player ops (select, move, mode changes, …), all out-of-match speech
   * - **Secondary**
     - In-match passive events only (casualties, discoveries, world messages, …)

With secondary **enabled**: ops use primary, passive events use secondary; they can overlap. Only **Alt** interrupts secondary.

With secondary **disabled**: primary speaks everything (single-channel style); ops interrupt passive lines.


----


Where to configure
------------------


1. Main menu → **Options** → **Voice library settings**
2. Choices:
   - **Enable or disable secondary voice** (or press **F3** in any menu; not available in-match)
   - **Primary** / **Secondary** library editors: volume, pitch, rate, voice, sound card
   - **Open voices folder**: opens ``user/voices`` for installing packs


----


Parameters and hotkeys
----------------------


In a library editor:

- Up/Down: select parameter (volume / pitch / rate / voice / device)
- Left/Right: adjust
- Enter or Esc: back

In-match (and menus):

- **F9–F12**: adjust primary (device / param type / decrease / increase)
- **Shift+F9–F12**: adjust secondary
- **Left Shift+C**: copy last primary line; **Right Shift+C**: last secondary line
- **Shift+A**: append to clipboard
- **F3 in menus**: toggle secondary on/off (not bound in-match)


----


Adding voices
-------------


Use **Open voices folder** (usually ``user/voices``).

Windows SAPI voices
~~~~~~~~~~~~~~~~~~~

1. Install and register a SAPI5 voice in Windows (Settings → Speech).
2. In-game, cycle the **voice** parameter in primary or secondary settings.
3. Some 32-bit-only voices are reached via ``tools/sapi32``.

Voice pack folders (friendly titles)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a subfolder under ``user/voices`` with ``voice.ini``::

    [voice]
    title=My display name
    sapi=Microsoft Huihui Desktop
    rate=0

- ``title``: name shown in menus
- ``sapi``: must match a registered SAPI voice (substring OK)
- ``rate``: optional, about -10…10

Packs do **not** install a TTS engine; they alias an existing SAPI voice.

Nuance / Apple voices (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If Nuance data is under ``user/voices/nuance``, those voices appear in the list. See that folder’s notes or the release tools for import steps.


----


Screen readers
--------------


If a dedicated screen reader (e.g. NVDA, 争渡) is detected, it may take over **primary** duties so it does not fight the primary library. Secondary (when enabled) still uses the in-game secondary profile.


----


See also
--------


- `Release notes <../../relnotes.htm>`_ — 1.4.5.4
- `Game manual <manual.htm>`_
