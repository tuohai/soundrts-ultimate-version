# Northern campaign arc (The Legend of Raynor ch. 24–27)



Chapters 24–27 form a continuous northern alliance storyline: recruit Garrek with the King's letter → deliver Garrek's token to Count Roland and duel → present the war banner to General Vera → defeat Marco Ironhand. Each chapter also requires eliminating ``traitor_guard`` assassins. Progress persists via ``campaign_flag``.



Maps:



| Ch. | File | Theme |

| --- | --- | --- |

| 24 | [24.txt](../../../res/single/The Legend of Raynor/24.txt) | Secret letter; Garrek's token after traitors die |

| 25 | [25.txt](../../../res/single/The Legend of Raynor/25.txt) | Token to Roland; yield duel; optional alliance |

| 26 | [26.txt](../../../res/single/The Legend of Raynor/26.txt) | War banner to Vera; ``transfer_units`` |

| 27 | [27.txt](../../../res/single/The Legend of Raynor/27.txt) | Marco duel; selective escort-knight control |



Definitions: `rules.txt <../../../res/single/The Legend of Raynor/rules.txt>`_. TTS: ``ui/tts.txt``, ``ui-zh/tts.txt`` (7575–7718, 7720–7730, 7740–7745).




----




1. Campaign flags
-------------------




| Flag | Set in | Effect |

| --- | --- | --- |

| ``ch24_garrek`` | 24 | Garrek recruited; later ``allied_control computer3`` |

| ``ch24_garrek_token`` | 24 | Token earned; ch. 25 starts with it in Raynor's inventory |

| ``ch25_duel_started`` | 25 | Token delivered; duel begun; killing Roland/guards before this → defeat |

| ``ch25_roland_allied`` | 25 | Accepted alliance; later ``allied_assist computer4`` |

| ``ch25_roland_knights`` | 25 | Declined alliance; compensation knights in later chapters |

| ``ch26_vera`` | 26 | Vera joins; Vera reinforcements in ch. 27 |

| ``ch27_duel_started`` | 27 | In-map ``map_flag`` (not saved across chapters): Raynor reached Marco's camp; cutscene 7718 played; killing Marco before this → defeat |

| ``ch27_marco`` | 27 | Marco recruited |




----




2. Triggers (new & common)
----------------------------




| Name | Type | Summary |

| --- | --- | --- |

| ``add_inventory_item`` | action | Put item in unit inventory: `(add_inventory_item <item> [<count>] [<unit_type>])` |

| ``set_ai_mode`` | action | Set AI mode on trigger owner's units |

| ``set_yield_on_defeat`` | action | Toggle per-unit yield: `(set_yield_on_defeat <0\|1> [unit selector…])` |

| ``units_yielded`` | condition | Enemy yield count (``yield_on_defeat``) |

| ``units_yielded_by`` | condition | Yield by specific attacker: `(units_yielded_by <attacker> <count> <victim> [enemy\|ally])`; supports ``is_a`` |

| ``has_entered`` | condition | Trigger owner's units entered a square (grid or place-name alias) |

| ``stop_all_units`` | action | Halt combat; optional ``computer1`` etc. |

| ``release_yielded_units`` | action | End yield invulnerability |

| ``npc_has_item`` | condition | NPC received item |

| ``alliance`` | action | Set alliance; multi-target: `(alliance 1 player1 computer1)` |

| ``alliance_request`` / ``alliance_with`` | action/cond. | Dynamic alliance (Ctrl+F4 / Shift+F4 in campaign) |

| ``allied_assist`` / ``allied_control`` | action | Allies fight alone / player commands allies |

| ``transfer_units`` | action | Change ownership (ch. 26) |

| ``has_killed`` | condition | Team kill count |

| ``key_unit_killed`` | condition | Key unit actually died (not yielded) |

| ``campaign_flag`` / ``set_campaign_flag`` | cond./action | Cross-chapter progress |




``cut_scene`` must run on ``player1`` triggers so the human client receives voice. AI mode / yield toggles may run on ``computer1`` (unit owner).




Trigger syntax is `trigger <owner> <condition> <action>` (three parts). Use `(and …) (defeat)`, not `(if (and …) (defeat))`.




F12 diplomacy is disabled in campaign. Use Ctrl+F4 to accept, Shift+F4 to decline.




----




3. Chapter 24 — Garrek
------------------------




1. Pick up ``secret_letter``, give to Garrek at Garrek's camp (``c2``) → alliance, ``allied_control``, ``ch24_garrek``.

2. Kill 3 ``traitor_guard`` → ``add_inventory_item garrek_token``, ``ch24_garrek_token``.




----




4. Chapter 25 — Roland
------------------------




Carryover: Garrek at A2 if ``ch24_garrek``; token in inventory if ``ch24_garrek_token``.



Objectives: (1) deliver token to Roland, (2) defeat Roland + 2 guard knights (yield), (3) kill traitors; optional alliance.



Flow:



1. Roland and ``npc_roland_guard`` start on ``guard``, no ``yield_on_defeat`` (killable before delivery; mistake → defeat).

2. player1 on ``npc_has_item``: ``cut_scene 7701``, objective 1, ``ch25_duel_started``.

3. computer1 on same condition: ``set_ai_mode offensive`` + ``set_yield_on_defeat 1``.

4. After yield: ceasefire, ``alliance_request``; Ctrl+F4 or Shift+F4 branch.



Register three primary + one optional objective at start (independent numbering).




----




5. Chapter 26 — Vera
----------------------




Deliver ``war_banner`` to Vera → ``transfer_units computer1 player1``, ``ch26_vera``. Killing Vera fails the mission.




----




6. Chapter 27 — Marco
-----------------------




Map: ``c2`` (Marco's camp); Marco + escorts (knights/warriors/archers); assassins at ``b3``/``c3``. Marco and all escorts start on ``ai_mode guard`` (``rules.txt``).



Carryover: ch. 24–26 reward units by flag. Player starts as ``raynor7`` with retinue (2 footmen, 2 archers, 2 knights).



Flow:



1. Raynor ``enters ``c2`` (Marco's camp / 3,2)`` → player1: ``cut_scene 7718``, ``set_map_flag ch27_duel_started`` (``raynor7`` must enter; escorts alone do not trigger).

2. computer1 (flag set): Marco only `(set_ai_mode offensive c2 1 npc_marco_ironhand)`; escorts `(order … ((go c1)))` to c1 to clear the arena.

3. Raynor must defeat Marco personally: `(units_yielded_by raynor7 1 npc_marco_ironhand enemy)` completes the primary objective. If escorts or other units force Marco to yield → ``defeat``.

4. After yield: ``cut_scene 7710`` → `(alliance 1 player1 computer1)`, ``stop_all_units``, ``release_yielded_units``.

5. `(allied_control computer1 c2 4 npc_knight_escort)` — four escort knights under player command; escorts at c1 are ordered `(go c2)` to re-form at Marco's camp.

6. Kill 3 ``traitor_guard`` (secondary objective) → ``cut_scene 7719`` (Marco's closing line — not ch. 24 Garrek token dialogue `7580`).



Failure: kill Marco before the duel starts (``key_unit_killed``); Marco yielded by a non-Raynor unit; Raynor dies; wipe.




----




7. Units & items
------------------




| Type | Role |

| --- | --- |

| ``garrek_token`` | Garrek's signet (ch. 24–25) |

| ``npc_count_roland`` | Count Roland; accepts ``garrek_token`` |

| ``npc_roland_guard`` | Guard knights (Roland calls them "brothers" in dialogue) |

| ``npc_marco_ironhand`` | Marco; ``yield_on_defeat`` |

| ``traitor_guard`` | Assassins; ``guard``, do not chase across squares |




----




8. ``yield_on_defeat``
--------------------------




- On zero HP, unit yields instead of dying; brief invulnerability.

- ``release_yielded_units`` after alliance choice.

- Ch. 25: disabled until token delivered (via ``set_yield_on_defeat 1`` trigger).




----




9. Comparison (ch. 24–27)
---------------------------




| Aspect | 24 Garrek | 25 Roland | 26 Vera | 27 Marco |

| --- | --- | --- | --- | --- |

| Yield duel | — | After token | — | From start; Raynor must land final blow |

| Duel start | On delivery | After token | On banner transfer | On entering Marco's camp |

| Kill key NPC early | Garrek dies → fail | Before token → fail | Vera dies → fail | Before camp duel → fail |




----




10. Related docs
------------------




| Topic | Doc |

| --- | --- |

| Give to NPC | [give-to-npc.md](give-to-npc.htm) |

| AI modes | [unit-default-behavior.md](unit-default-behavior.htm) |

| Index selectors | [map-unit-index-selectors.md](map-unit-index-selectors.htm) |

| Official syntax | ``mod/mapmaking.rst`` |




----




11. Tests
-----------




.. code-block:: text

   
   python -m pytest soundrts/tests/test_campaign_alliance_transfer_triggers.py -q
   
   python -m pytest soundrts/tests/test_yield_on_defeat_and_campaign_flags.py -q
   
   python -m pytest soundrts/tests/test_give_item_to_npc.py -q
   





----




12. Campaign-wide (Raynor growth, retinue, place names)
---------------------------------------------------------




Raynor stages (``rules.txt`` / per-map ``starting_units``):



| Chapters | Unit type | Starting retinue (besides Raynor) |

| --- | --- | --- |

| 1–12 | ``raynor`` | per-chapter defaults |

| 13–15 | ``raynor2`` | 1 footman |

| 16–18 | ``raynor3`` | 2 footmen |

| 19–21 | ``raynor4`` | 2 footmen, 1 archer |

| 22–24 | ``raynor5`` | 2 footmen, 1 archer, 1 knight |

| 25–26 | ``raynor6`` | 2 footmen, 2 archers, 2 knights |

| 27–28 | ``raynor7`` | 2 footmen, 2 archers, 2 knights |



Stage cutscenes: end of ch. 12 (``7730``); ch. 13/16/19/22/25/27 openings (``7720``–``7729``, ``7737``–``7738``). Attribute-screen intros: ``ui/style.txt`` ``intro 7740``–``7746``.



Place names: ch. 1–28 maps use ``square_name`` (province/county/site). TTS in ``ui-zh/tts.txt`` Place names section. Scripts may still use grid coords (``c2``) or place-name aliases.
