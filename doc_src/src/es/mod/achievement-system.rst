Sistema de logros
=================



Guía del jugador (menús, progreso, lo que cuenta): `../player/achievements.htm <../player/achievements.htm>`_

Referencia de implementación. Versión china: `../../zh/mod/achievement-system <../../zh/mod/achievement-system.htm>`_.

Estado
------



.. list-table::
   :header-rows: 1

   * - Fase
     - Estado
     - Resumen
   * - 1
     - Hecho
     - Definiciones, guardado por mod, desbloqueo posterior al juego, lista de logros
   * - 2
     - Hecho
     - Medallas, cartas, rangos y títulos de honor, armería.
   * - 3
     - Hecho
     - Equipamiento previo a la misión en TrainingGame, aplica efectos, consume cargas
   * - Esquema D
     - Hecho
     - Guardados por facción (``achievements_per_faction``), selector de facciones en los menús
   * - Metaprogreso
     - Hecho
     - Facciones cruzadas ``\_meta.json``, condiciones agregadas, ``scope meta``



código clave
------------



.. list-table::
   :header-rows: 1

   * - Archivo
     - Rol
   * - ``soundrts/achievements.py``
     - Cargar, evaluar, recompensar, persistir, anunciar
   * - ``soundrts/faction_progress.py``
     - Rutas por facción, coincidencia de facciones, selector de menú
   * - ``soundrts/meta_progress.py``
     - Metaguardado entre facciones (``\_meta.json``), agregación de instantáneas
   * - ``soundrts/cards.py``
     - Definiciones de tarjetas
   * - ``soundrts/titles.py``
     - Escala de rango + títulos de honor
   * - ``soundrts/achievements_menu.py``
     - Hub: selector de facciones, lista de logros, armería, metaprogreso
   * - ``soundrts/game.py``
     - `_say_achievements()` después de `say_score()` (omitido en la campaña)
   * - ``soundrts/lib/resource.py``
     - Carga logros + tarjetas + títulos con reglas
   * - ``res/achievements.txt``
     - Logros básicos
   * - ``mods/\<mod\>/achievements.txt``
     - Mod agregar/anular



Guardar rutas
-------------



.. list-table::
   :header-rows: 1

   * - Camino
     - cuando
   * - ``user/achievements/\<mod_key\>.json``
     - Predeterminado (guardado único por mod)
   * - ``user/achievements/\<mod_key\>/\<faction\>.json``
     - ``achievements_per_faction 1``
   * - ``user/achievements/\<mod_key\>/\_meta.json``
     - Meta entre facciones (``achievements_per_faction 1``)



Habilite el modo por facción en el mod ``rules.txt``:

.. code-block:: text

   def parameters
   achievements_enabled 1
   achievements_per_faction 1



- Las definiciones etiquetadas por facciones usan `faction <race_id>`; omita ``faction`` en tarjetas globales (compartidas entre sucursales).
- El menú principal Logros elige primero una facción (mods de múltiples facciones); regresar de la lista/armería regresa al selector de facciones.
- La entrada de progreso entre facciones abre la lista de meta logros + meta armería (ramas activas, hitos del mapa, meta honores).

Campaña: ``game.is_campaign_session()`` omite puntuación, logros, medallas, ascenso de rango y registro de estadísticas.

Multijugador: ``game_type_name == "multiplayer"`` omite logros, medallas, ascensos de rango y progreso de cartas; Las estadísticas de puntuación de voz y tiempo de reproducción aún se ejecutan (consulte `score-grading-system.htm <score-grading-system.htm>`_).

Fragmento de definición
-----------------------


.. code-block:: text

   def grade_s
   title 5300
   condition grade S
   once_per map_ai
   reward medal 50
   reward card card_mixed_army



Metalogro (``scope meta``)
~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def meta_three_branches
   scope meta
   title 79950
   condition factions_unlocked_at_least 3 1
   once
   reward title honor_meta_novice



Condiciones agregadas (lea todas las partidas guardadas de facción):


.. list-table::
   :header-rows: 1

   * - Condición
     - Significado
   * - ``factions_unlocked_at_least N M``
     - Al menos N ramas, cada una desbloqueada ≥M logros
   * - ``factions_medals_at_least N M``
     - Al menos N sucursales con ≥M medallas
   * - ``factions_honors_at_least N M``
     - Al menos N sucursales cada una con ≥M títulos de honor
   * - ``factions_achievement_id_contains_at_least N \<substr\>``
     - Al menos N ramas desbloquearon un logro cuya identificación contiene `<substr>` (por ejemplo, ``\_map_``)



Las meta recompensas se almacenan en ``\_meta.json``. Las metamedallas no cuentan para los rangos por facción. Los títulos de meta honor no tienen el campo ``faction``.

Consulte el documento zh para obtener la lista completa de directivas (``condition``, ``reward``, ``repeat_medal``, ``cards.txt``, ``titles.txt``).

Repetición de finalización: si ya se otorgó la misma clave ``once``, ``repeat_medal \<n\>`` otorga solo medallas (sin tarjeta/honor/desbloqueo de voz).

Normalización de la dificultad de la IA: los nombres de los scripts de IA de las facciones personalizadas se asignan a niveles canónicos para contadores de derrotas acumulativas; Las claves de guardado heredadas migran al cargar.

Flujo de tiempo de ejecución
----------------------------


.. code-block:: text

   Main menu → Achievements
     ├─ (multi-faction) pick faction → list / armory → back → pick faction again
     └─ (multi-faction) cross-faction progress → meta list / meta armory
   
   game.post_run()
     → say_score()              # skipped in campaign
     → _say_achievements()      # faction unlocks, then meta unlocks, rewards, rank-up
                                # skipped in campaign and multiplayer



Formato de guardado (facción o mod único)
-----------------------------------------


.. code-block:: json

   {
     "unlocked": { "grade_s": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "grade_s|map:jl1|ai:beginner": true },
     "medals": 50,
     "honors": ["honor_nightmare_slayer"],
     "ai_defeats": { "beginner": 5 },
     "map_ai_defeats": { "pra1": { "beginner": 3 } },
     "cards": { "card_infantry": { "charges": 1, "total_earned": 1 } }
   }



Metaguardado (``\_meta.json``) - no ``cards`` / ``ai_defeats`` / ``map_ai_defeats``:

.. code-block:: json

   {
     "unlocked": { "meta_three_branches": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "meta_three_branches": true },
     "medals": 25,
     "honors": ["honor_meta_novice"]
   }



Los campos que faltan en los guardados heredados se normalizan al cargar.

Fase 3 (terminada)
------------------

- Después de Un jugador → Iniciar en el mapa → Iniciar, recoge hasta N cartas (N = rango ``loadout_slots``)
- Los efectos se aplican después de completar el mapa (inmediatamente o después de ``delay`` / ``delay_minutes``); un cargo consumido por tarjeta al inicio del juego
- Campos de la tarjeta: ``spawn``, ``resource``, ``tech``; tarjetas combinadas compatibles; tarjetas retrasadas documentadas en `delayed-card-loadout.htm <delayed-card-loadout.htm>`_
- La aparición de cartas consume población.
- Solo juego de entrenamiento (escaramuza contra IA); no campaña ni multijugador
- Las tarjetas pueden requerir ``min_rank`` en ``cards.txt``

Optar por no participar en modificaciones
-----------------------------------------


.. code-block:: text

   def parameters
   achievements_enabled 0



Oculta la entrada de Logros del menú principal, omite los desbloqueos posteriores al juego, el equipamiento y la aplicación de tarjetas en el juego; no carga ``achievements.txt`` / ``cards.txt`` / ``titles.txt``. Los archivos guardados se conservan si los vuelve a habilitar más tarde.

Ejemplo de CrazyMod
-------------------


``mods/crazyMod9beta10`` usa el esquema D + cuatro metaniveles (``meta_three_branches``… ``meta_ten_masters``) e hitos de mapa por facción (``trad_map_pra1``… ``delf_map_pra10``).

Pruebas
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_achievements.py -v
   python -m pytest soundrts/tests/test_faction_progress.py -v
   python -m pytest soundrts/tests/test_meta_progress.py -v
   python -m pytest soundrts/tests/test_achievements_menu_navigation.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
   python -m pytest soundrts/tests/test_card_loadout.py -v
