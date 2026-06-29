Mod advanced guide
====================


Skills, factions, meta progress, AI — after `Getting started <getting-started.htm>`_. Maps/campaigns have their own guides.
.. contents::

----

Mod folder layout
------------------

``rules.txt`` (core), optional ``ai.txt``, ``ui/tts.txt``, ``ui/bindings.txt``, ``ui-xx/``.  
Examples: ``mods/orc/``, ``mods/starcraft/``, ``mods/crazyMod9beta10/``.

----

Rules: units & combat
----------------------

Use ``is_a`` chains; attach skills via ``can_use_skill``.
Full keywords: `Modding manual <modding.htm>`_.  
Skills / heal / effects: `Skills guide (zh) <../../zh/mod/skills-and-effects.htm>`_ or `Modding manual <modding.htm>`_.

----

UI, hotkeys, i18n
------------------

- `Hotkey mapping editor <hotkey-mapping-editor.htm>`_
- Layered bindings: `Layered hotkeys <../player/layered-hotkeys.htm>`_
- i18n: `Mod i18n <mod-i18n.htm>`_ (Chinese doc; pattern is universal)

----

AI
---

`AI tutorial <aimaking.htm>`_

----

Meta: achievements, scoring, cards
-----------------------------------

.. list-table::
   :header-rows: 1

   * - System
     - Mod doc
     - Player doc
   * - Achievements
     - `Achievement system <achievement-system.htm>`_
     - `Achievements <../player/achievements.htm>`_
   * - Scoring
     - `Score grading <score-grading-system.htm>`_
     - `Score & grades <../player/score-and-grades.htm>`_
   * - Cards
     - `Delayed cards <delayed-card-loadout.htm>`_
     - `Loadout cards <../player/loadout-cards.htm>`_

----

Maps & campaigns (separate guides)
-----------------------------------

- `Map guide <map-guide.htm>`_ → `Mapmaking manual <mapmaking.htm>`_
- `Campaign guide <campaign-guide.htm>`_
- `Random maps <randommap.htm>`_

----

Index
------

- `Modding manual <modding.htm>`_
- `Release notes <../relnotes.htm>`_
- `Mod docs index <index.htm>`_

Back to `Getting started <getting-started.htm>`_
