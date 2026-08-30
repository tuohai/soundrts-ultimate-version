Documentazione per autori di mod
================================


Per rules, mappe e script di campagna — non il codice del motore. Giocatori: `Documentazione giocatori <../player/index.htm>`_.
-------------------------------------------------------------------------------------------------------------------------------

Percorso di lettura
-------------------

Regole mod

1. `Primi passi <getting-started.htm>`_ — prima patch e test
2. `Guida avanzata <advanced.htm>`_ — abilità, fazioni, meta, IA
3. `Manuale di modding <modding.htm>`_ — riferimento completo delle parole chiave; penetrazione in linea ``rdg_pierce_line`` nel sistema di combattimento
4. `Abilità / cura / effetti <skills-and-effects.htm>`_
5. `Sistema di mercato <market-system.htm>`_ — compra/vendita, tributo, commercio di tratta
6. `Upgrade di linea e addestramento di livello massimo <unit-line-upgrade.htm>`_ — ``line_upgrade``, risoluzione addestramento
7. `Predizione proiettili e velocità di volo <projectile-lead.htm>`_ — ``projectile_lead``, ``*_projectile_speed``
8. `Urla di battaglia <battle-shouts.htm>`_ — urla a livelli, configurazione ``shouts``
9. `Gestione audio <audio-management.htm>`_ — refactor P0–P2, SFX multiformato, volumi

Mappe

4. `Guida alle mappe <map-guide.htm>`_ → `Manuale di creazione mappe <mapmaking.htm>`_
5. `Terreno a caselle e terreno edificabile <building-land-terrain.htm>`_ — ``class terrain`` / ``building_land`` / ``square_terrain``
6. `Costruire ponti sull'acqua <water-bridge-building.htm>`_ — tratti di ponte a casella, ``is_buildable_on_water_only`` / ``bridge_terrain``
7. `Mappe casuali <randommap.htm>`_ — parametri RMG e codici di condivisione

Campagne

7. `Guida alle campagne <campaign-guide.htm>`_ — struttura a capitoli, obiettivi, oggetti, PNG, coop, trasporto inter-capitolo
8. `Obiettivi progressivi <campaign/progressive-objectives.htm>`_
9. `Trovare oggetti (has_item) <campaign/find-item.htm>`_
10. `Dare a un PNG <campaign/give-to-npc.htm>`_
11. `Selettori indice unità <campaign/unit-index.htm>`_
12. `Trasporto eroi <campaign/hero-carryover.htm>`_
13. `Campagne cooperative <campaign/coop.htm>`_

Altro

14. `Tutorial IA <aimaking.htm>`_ · `Server <server.htm>`_ · `Note di rilascio <../relnotes.htm>`_

Progressi meta e interfaccia
----------------------------

- `Sistema obiettivi <achievement-system.htm>`_ · `Punteggio e voti <score-grading-system.htm>`_ · `Carte ritardate <delayed-card-loadout.htm>`_
- `Mod multilingue <mod-i18n.htm>`_ · `Editor mappatura tasti <hotkey-mapping-editor.htm>`_
- Tasti a livelli (per i giocatori): `Tasti rapidi a livelli <../player/layered-hotkeys.htm>`_

Mod di esempio
--------------

``mods/orc/``, ``mods/starcraft/``, ``mods/crazyMod9beta10/`` — conviene copiarli in ``user/mods/`` prima di modificarli.
