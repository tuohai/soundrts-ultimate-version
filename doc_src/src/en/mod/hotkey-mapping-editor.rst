Hotkey Mapping Editor
======================



Player guide (layered/classic schemes): `../player/layered-hotkeys.md <../player/layered-hotkeys.htm>`_

中文版：`../../zh/mod/hotkey-mapping-editor.md <../../zh/mod/hotkey-mapping-editor.htm>`_

In-game Options → Key mapping — voice-driven remapping for blind-accessible play. Phases 1–5 are complete. This doc is for maintainers: architecture and data formats.

Source: ``soundrts/hotkey_editor.py``, ``soundrts/hotkey_catalogs.py``, ``soundrts/hotkey_remapping_menu.py``, ``soundrts/clientgame/interface_modes.py``.


----


1. Status
-----------



.. list-table::
   :header-rows: 1

   * - Phase
     - Status
     - Scope
   * - Phase 1
     - Done
     - Parser, JSON storage, load merge, global layer UI
   * - Phase 2
     - Done
     - unit/building/command/skill/rpg/help/map/diplomacy catalogs, layer submenus
   * - Phase 3
     - Done
     - Classic scheme (``classic`` layer / ``legacy_bindings.txt``); ~179 primary bindings
   * - Phase 4
     - Done
     - Search, advanced variants submenu, clipboard import/export
   * - Phase 5
     - Done
     - Independent alias-key remapping (LCTRL/RCTRL, RETURN/KP_ENTER, etc.)



Player flow (summary)
~~~~~~~~~~~~~~~~~~~~~~


- Options → Key mapping (sibling of Hotkey scheme)
- Layered scheme: pick a layer (global / unit / building / command / skill / first person / help / map / diplomacy)
- Classic scheme: Key mapping opens the full classic binding list directly (no extra “Classic hotkeys” layer); First person remains a submenu inside it
- Each layer: Search, Advanced variants (if any), Alias keys (if any), then primary catalog items
- Top level: Export / Import hotkey JSON via clipboard (merge or replace)
- Per-mod storage: `user/hotkey_overrides/{mod_key}.json`; takes effect at next game start


----


2. Why not append-only ``bindings.txt``
-------------------------------------------


Legacy: ``cfg/bindings.txt`` is key → command append; remapping via append leaves old keys working.

New model: store binding_id → key in JSON; at load time remove replaced default lines and add new ones. Hand-written ``cfg/bindings.txt`` still works (appended last).


----


3. Files
----------



.. list-table::
   :header-rows: 1

   * - Path
     - Role
   * - ``soundrts/hotkey_catalogs.py``
     - Per-layer catalogs, variant labels, alias catalog
   * - ``soundrts/hotkey_editor.py``
     - Parse, binding_id, JSON, ``apply_overrides_to_bindings_text``, capture
   * - ``soundrts/hotkey_remapping_menu.py``
     - Menu UI
   * - ``soundrts/clientgame/interface_modes.py``
     - Apply overrides before merge
   * - ``soundrts/msgparts.py``
     - TTS IDs 5280–5399, 5500–5684
   * - ``user/hotkey_overrides/{mod_key}.json``
     - Per-mod overrides + ``layered_hotkeys``
   * - ``user/hotkey_overrides.json``
     - Legacy single file (migrated to ``\_base.json``)



Tests: ``test_hotkey_editor.py`` through ``test_hotkey_editor_phase5.py``, ``test_hotkey_catalog_tts.py``


----


4. Data model
---------------


binding_id
~~~~~~~~~~~


``{layer}.{command}.{arg1}.{arg2}...``

Alias overrides use ``@`` + encoded default key: ``global.examine@RCTRL``, ``global.validate.imperative@CTRL+KP_ENTER`` (spaces → `` +``).

JSON example
~~~~~~~~~~~~~


.. code-block:: json

   {
     "version": 1,
     "layered_hotkeys": 1,
     "overrides": {
       "global": {
         "global.resource_status.resource1": "y",
         "global.examine@RCTRL": "F3"
       }
     }
   }



----


5. Load pipeline
------------------


.. code-block:: text

   global_bindings.txt → apply_overrides(global)
     → + mode layer → + mod → + cfg/bindings.txt → Bindings.load()


Classic: ``\_legacy_bindings_with_overrides()`` applies ``classic`` layer overrides.


----


6. Features (Phases 4–5)
--------------------------


- Search: filter by label or binding_id (EN/ZH)
- Advanced variants: bindings in `*_bindings.txt` not in primary catalog (e.g. Shift+Enter queue validate)
- Alias keys: remap secondary keys for the same binding_id (e.g. KP_ENTER vs RETURN)
- Import/export: clipboard JSON for current mod


----


7. Tests
----------


.. code-block:: bash

   pytest soundrts/tests/test_hotkey_editor.py -q
   pytest soundrts/tests/test_hotkey_editor_phase2.py -q
   pytest soundrts/tests/test_hotkey_editor_phase3.py -q
   pytest soundrts/tests/test_hotkey_editor_phase4.py -q
   pytest soundrts/tests/test_hotkey_editor_phase5.py -q
   pytest soundrts/tests/test_hotkey_catalog_tts.py -q
   pytest soundrts/tests/test_layered_bindings.py -q


The editor never edits shipped ``res/ui/*_bindings.txt``; only user JSON.

For full detail see the `Chinese developer doc <../../zh/mod/hotkey-mapping-editor.htm>`_.
