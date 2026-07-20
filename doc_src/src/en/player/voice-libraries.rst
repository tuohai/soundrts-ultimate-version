Primary and secondary voice libraries (players)
================================================


The game uses two independently configurable voice libraries: primary and secondary. You can enable or disable the secondary library; when disabled, the primary library speaks everything.

**Tip:** Prefer a **screen reader** (NVDA, JAWS, Contending Reader / 争渡, etc.) as the primary voice. When a reader is active it takes over primary duties, so you need not spend ``F9``–``F12`` on “adjust primary.” Hotkeys in this game are extremely dense and nearly saturated—**save a key whenever you can**. You can still tune the secondary (battlefield) library with ``Shift+F9``–``F12``.


----


Duties
------


.. list-table::
   :header-rows: 1

   * - Library
     - Speaks
   * - **Primary**
     - Menus, player ops (select, move, mode changes, …); all out-of-match speech; and in-match **own economy / production feedback** (unit/building complete, research complete, age upgrade complete, resource stock changes, menu changed, …)
   * - **Secondary**
     - In-match **battlefield passive** events (enemies spotted, casualties, scout reports, combat-square alerts, world messages, …)

With secondary **enabled**: primary and secondary can overlap.

Skip / stop the current line:

- **Left Alt**: filter (skip / stop) the **primary** library
- **Right Alt**: filter (skip / stop) the **secondary** library

With secondary **disabled**: primary speaks everything (single-channel style); **both Left Alt and Right Alt skip the current line** (there is no secondary to filter).


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
- **Shift+F9–F12**: adjust secondary (either Shift)
- **Right Shift+C**: copy last secondary line; **Right Shift+B**: append secondary to clipboard
- **Left Shift+C / Left Shift+B** (copy/append primary): **commented out** by default in ``res/ui/global_bindings.txt`` to reduce hotkey clashes; uncomment the lines (remove the leading ``;``) to enable
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

Primary and secondary can both use **SAPI only**; Nuance is optional. Nuance needs the 32-bit Java helper shipped in ``tools/nuance_ve``; the SAPI path does not use Java.


----


Directional in-match alerts (stereo pan)
----------------------------------------


Some **square-linked** passive lines in a match (enemy spotted, casualties, scout reports, combat-square alerts) are panned left/right (with front/back attenuation) relative to your **current view square**, using the same positioning math as minimap alert SFX.

Headphones recommended. In the default overhead view facing north: squares to the east are louder on the right; west on the left.

**Volume floor:** Spoken directional cues do not keep getting quieter with distance—far squares stay about as loud as an adjacent square (slightly quieter allowed) so you can hear them while playing. Left/right and rear attenuation still apply. Minimap alert beeps still use full distance falloff.

**Pan follows mid-utterance moves:** if you hear “enemy at a1” from the left while on b1, then switch to a1 before the line ends, the voice moves to center (in front)—you do not wait for the next message.

Notes:

- Direction applies to the secondary library when enabled, otherwise to primary. It works with SAPI or Nuance.
- Menu and selection speech stay centered.
- When a screen reader owns primary, primary pan is unavailable; secondary can still pan as above.


----


Screen readers
--------------


If a dedicated screen reader (e.g. NVDA, 争渡) is detected, it may take over **primary** duties so it does not fight the primary library. Secondary (when enabled) still uses the in-game secondary profile.


----


See also
--------


- `Release notes <../../relnotes.htm>`_ — 1.4.5.4 (dual libraries), 1.4.5.5 (directional alerts, duties, Left/Right Alt)
- `Game manual <manual.htm>`_
