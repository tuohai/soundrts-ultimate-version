Mod getting started
====================


Your first patch and first working unit — not maps or campaigns yet. Next: `Mod advanced guide <advanced.htm>`_.
----------------------------------------------------------------------------------------------------------------

What you change
----------------

A mod is a folder of text files. Save, reload the map or restart the game.

.. list-table::
   :header-rows: 1

   * - File
     - Role
   * - ``rules.txt``
     - Units, tech, skills (this guide)
   * - ``style.txt`` + ``ui/tts.txt``
     - Names and voice lines
   * - ``ai.txt``
     - Computer strategy (later)

Keyword reference: `Modding manual <modding.htm>`_.

----

Step 1: folder & activation
----------------------------

Put your mod in ``user/mods/mymod/``. Activate in ``user/SoundRTS.ini``:

.. code-block:: ini

   mods = mymod

Later mods in the list override earlier ones. Dev shortcut: ``python soundrts.py --mods=mymod``

----

Step 2: two-line proof
-----------------------

``user/mods/mymod/rules.txt``:

.. code-block:: text

   def peasant
   decay 20

Peasants vanish after ~20 seconds — your mod is loaded.

Sound-only mods: copy ``mods/soundpack/`` or use Options → soundpack.

----

Step 3: read rules.txt
-----------------------

.. code-block:: text

   def my_soldier
   class soldier
   is_a footman
   hp 120
   mdg 8

- ``def`` — start a definition
- ``class`` — soldier, building, skill, …
- ``is_a`` — inherit, then override fields
- ``clear`` at file top — replace defaults instead of patching

Factions: ``def orc_faction`` + ``class faction``.

----

Step 4: names players hear
---------------------------

.. code-block:: text

   ; ui/style.txt — title 7801
   ; ui/tts.txt — 7801 Heavy Infantry

See `Mod i18n <mod-i18n.htm>`_ (Chinese doc; pattern is universal).

----

Step 5: test
-------------

Single player vs computer; Ctrl+Shift+F2 reveals map (solo, sole human).  
Logs: ``user/tmp/client.log``

Player-side field meaning: `Inventory <../player/inventory.htm>`_ · `Default behaviors <../player/unit-default-behavior.htm>`_

----

What's next?
-------------

.. list-table::
   :header-rows: 1

   * - Goal
     - Read
   * - Full mod, skills, factions
     - `Mod advanced <advanced.htm>`_ · `Modding manual <modding.htm>`_
   * - First map
     - `Map guide <map-guide.htm>`_
   * - Campaign
     - `Campaign guide <campaign-guide.htm>`_
   * - Release notes
     - `Release notes <../relnotes.htm>`_

Back to `Mod docs index <index.htm>`_
