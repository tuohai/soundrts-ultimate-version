Sistema de puntuación y notas
=============================

Guía del jugador: `../player/score-and-grades.htm <../player/score-and-grades.htm>`_

Este documento describe la puntuación multidimensional al final de la partida en SoundRTS, las notas con letras y los anuncios de voz.

Para la integración con logros, consulta la sección 9 de `achievement-system <achievement-system.htm>`_. Los logros leen ``score_breakdown()``; no reimplementan la puntuación.

----

1. Cuándo se ejecuta la puntuación
----------------------------------

.. list-table::
   :header-rows: 1

   * - Escenario
     - Anuncio de puntuación
     - Estadísticas de historial
   * - Mapa personalizado / aleatorio contra IA (TrainingGame)
     - ✅
     - ✅
   * - Multijugador
     - ✅
     - ✅
   * - Campaña / campaña cooperativa
     - ❌
     - ❌
   * - Espectador
     - ❌ («espectando terminado»)
     - ❌

Cuando ``game.is_campaign_session()`` es verdadero, se omiten ``say_score()`` y ``\_record_stats()``.

Orden al final de la partida (``game.post_run()``): primero ``say_score()``, luego ``\_say_achievements()``.

----

2. Estructura de la puntuación
------------------------------

.. code-block:: text

   total = base_total + ai_defeat

.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``base_total``
     - Suma de siete dimensiones base, tope 800
   * - ``ai_defeat``
     - Bonificación por ordenadores enemigos derrotados, no cuenta hacia 800
   * - ``total``
     - `base_total + ai_defeat`; puede superar 800
   * - ``percent``
     - `base_total × 100 ÷ 800`, tope 100%
   * - ``max``
     - Siempre 800 (denominador del porcentaje; excluye ai_defeat)
   * - ``grade_total``
     - Puntuación usada para la nota (tope en derrota; ver §5)

Siete dimensiones base
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Dimensión
     - Clave
     - Rango
     - Notas
   * - Resultado
     - ``outcome``
     - 0 o 200
     - Victoria 200, derrota 0
   * - Minería
     - ``mining``
     - 0–100
     - frente a capacidad de depósitos del mapa o referencia
   * - Eficiencia
     - ``efficiency``
     - 0–100
     - utilización o frugal (ver §4)
   * - Supervivencia
     - ``survival``
     - 0–100
     - tasa de pérdida de unidades amigas
   * - Defensa de edificios
     - ``building_defense``
     - 0–100
     - pérdidas de edificios amigos
   * - Combate
     - ``combat``
     - 0–100
     - bajas frente a producción enemiga
   * - Demolición
     - ``demolition``
     - 0–100
     - edificios enemigos destruidos

Líneas de resumen (para anuncios)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Clave
     - Fórmula
   * - ``unit_line``
     - `survival + combat`
   * - ``building_line``
     - `building_defense + demolition`
   * - ``mining_by_resource[]``
     - puntuación de minería por recurso

----

3. Fórmulas de dimensiones
--------------------------

Todas las puntuaciones de dimensión usan ``\_clamp_score()`` a 0–100 (resultado es 0 o 200). Las cantidades internas usan enteros de punto fijo (``PRECISION``); los anuncios dividen por ``PRECISION`` para mostrar.

3.1 Resultado
~~~~~~~~~~~~~

- Victoria: `200`
- Derrota: `0`

Doble peso frente a otras dimensiones individuales.

3.2 Minería
~~~~~~~~~~~

Recogido efectivo = ``gathered[i] - starting_resources[i]`` (suma por recurso, mínimo 0). El stock inicial no cuenta.

Con capacidad de mapa (``sum(world.map_deposit_capacity) \> 0``):

.. code-block:: text

   mining = clamp(effective_gathered × 100 ÷ total_map_capacity)

La capacidad se acumula de cada ``Deposit`` del mapa al cargar (``worldresource.py``).

Sin capacidad de mapa:

- Campaña: victoria → 100; derrota → 0
- No campaña: si el recogido efectivo ≤ 0 → 0; si no:

.. code-block:: text

     mining = clamp(effective_gathered × 100 ÷ 1000)

  (``MINING_REFERENCE_GATHER`` = 1000 en unidades de visualización)

Las puntuaciones por recurso siguen las mismas reglas en ``mining_by_resource[i]``.

3.3 Eficiencia
~~~~~~~~~~~~~~

.. code-block:: text

   utilization_percent = clamp(consumed ÷ gathered × 100)   // 0 if gathered is 0

- Por defecto `efficiency_mode = "utilization"`: `efficiency = utilization_percent`
- Frugal `efficiency_mode = "frugal"` (solo victoria, utilización < 50%):
  ``efficiency = clamp((1 - consumed/gathered) × 100)``  
  El anuncio usa «eficiencia frugal» (TTS 5251) en lugar de «utilización de recursos» (5227).

En derrota, el modo frugal nunca se aplica.

3.4 Supervivencia
~~~~~~~~~~~~~~~~~

.. code-block:: text

   if produced(unit) > 0:
       survival = clamp((produced - lost) × 100 ÷ produced)
   else:
       survival = 0

3.5 Defensa de edificios
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   building_defense = max(0, 100 - lost(building) × 5)

5 puntos perdidos por edificio amigo.

3.6 Combate
~~~~~~~~~~~

Suma ``produced(unit)`` sobre enemigos no aliados, no neutrales como ``enemy_units``:

.. code-block:: text

   if enemy_units > 0:
       combat = clamp(killed(unit) × 100 ÷ enemy_units)
   else:
       combat = clamp(killed(unit) × 5)

3.7 Demolición
~~~~~~~~~~~~~~

.. code-block:: text

   demolition = clamp(killed(building) × 5)

5 puntos por edificio enemigo (tope 100 a 20 edificios).

3.8 Bonificación por derrota de IA (``ai_defeat``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Por cada ordenador enemigo derrotado, añade ``defeat_score`` según dificultad:

.. list-table::
   :header-rows: 1

   * - Nivel integrado
     - defeat_score por defecto
   * - beginner / easy
     - 10
   * - intermediate / aggressive
     - 20
   * - advanced
     - 40
   * - expert
     - 80
   * - nightmare
     - 200

Desde ``defeat_score \<n\>`` en el bloque ``ai.txt`` de la IA; nombres de IA personalizados sin él puntúan 0.

Excluidos: ordenadores aliados, no derrotados, tipos de IA ``timers`` / ``ai2`` / vacío, ``defeat_score 0``, jugadores no ordenador. Los jugadores derrotados en ``ex_players`` sí cuentan.

----

4. Notas con letras
-------------------

Desde ``grade_total`` (``score_grade_msg()`` / ``score_grade_letter()``):

.. list-table::
   :header-rows: 1

   * - Nota
     - grade_total mínimo
   * - S
     - 720
   * - A
     - 640
   * - B
     - 560
   * - C
     - 480
   * - D
     - 400
   * - E
     - 0

Tope de nota en derrota
~~~~~~~~~~~~~~~~~~~~~~~

En derrota: ``grade_total = min(total, 479)`` (``DEFEAT_GRADE_MAX_TOTAL``). La nota no puede superar D en derrota aunque combate/demolición inflen ``total``.

----

5. Eventos de estadísticas en bruto
-----------------------------------

``Stats.add(event, target, inc)`` durante la partida:

.. list-table::
   :header-rows: 1

   * - event
     - target
     - Disparador típico
   * - ``gathered``
     - índice de recurso
     - minería, recursos iniciales, concesiones de cartas
   * - ``produced``
     - ``unit`` / ``building``
     - entrenamiento completado
   * - ``lost``
     - ``unit`` / ``building``
     - amigo destruido
   * - ``killed``
     - ``unit`` / ``building``
     - enemigo destruido

El caducar de ``time_limit`` con ``on_disappear`` (incluidas invocaciones de ``lang_add_units``) no suma ``lost``; ``uncount_expired_unit_produced`` revierte ``produced``. Morir en combate sigue contando ``lost`` / ``killed``.

``consumed(i) = gathered(i) - player.resources[i]``.

``stats.freeze()`` al final de la partida fija ``game_duration`` para el anuncio de tiempo.

----

6. Anuncios de voz (``score_msgs``)
-----------------------------------

Orden:

1. Victoria/derrota + duración + puntos de resultado
2. Unidades: producidas / perdidas / matadas + ``unit_line``
3. Edificios: producidos / perdidos / matados + ``building_line``
4. Cada recurso: recogido / consumido + puntuación de minería por recurso
5. Línea de eficiencia (etiqueta frugal o utilización)
6. Cada nivel de IA derrotado [× cantidad] + bonificación
7. Total / 800 / percent%
8. Nota + explicación del historial

IDs TTS: ``soundrts/msgparts.py`` (5225–5243, 5251) y ``res/ui/tts.txt``.

----

7. Integración con logros
-------------------------

``achievements.build_context()`` lee de ``score_breakdown()``:

.. list-table::
   :header-rows: 1

   * - Condición
     - Fuente
   * - ``condition grade S`` etc.
     - `score_grade_letter(total)`
   * - ``condition victory``
     - `player.has_victory`
   * - ``condition utilization_below N``
     - ``utilization_percent`` (requiere victoria)
   * - ``condition survival_at_least N``
     - ``survival``
   * - ``condition building_defense_at_least N``
     - ``building_defense``
   * - ``condition defeated_ai expert`` etc.
     - ``ai_defeat_entries``

----

8. Personalización del mod
--------------------------

ai.txt — bonificación por derrota
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def my_custom_ai
   defeat_score 55

``defeat_score 0`` desactiva la bonificación para esa IA.

----

9. Archivos relacionados
------------------------

.. list-table::
   :header-rows: 1

   * - Ruta
     - Función
   * - ``soundrts/worldplayerstats.py``
     - Puntuación, notas, mensajes
   * - ``soundrts/definitions.py``
     - ``DEFAULT_AI_DEFEAT_SCORE``, `get_ai_defeat_score()`
   * - ``soundrts/worldresource.py``
     - ``map_deposit_capacity``
   * - ``soundrts/game.py``
     - `say_score()`, `post_run()`
   * - ``soundrts/achievements.py``
     - Lee el desglose para desbloqueos

----

10. Pruebas
-----------

.. code-block:: bash

   python -m pytest soundrts/tests/test_score_breakdown.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v

----

11. Constantes de diseño
------------------------

.. list-table::
   :header-rows: 1

   * - Constante
     - Valor
     - Función
   * - ``SCORE_BASE_MAX``
     - 800
     - Máximo base
   * - ``OUTCOME_MAX``
     - 200
     - Peso del resultado
   * - ``DEFEAT_GRADE_MAX_TOTAL``
     - 479
     - Tope de nota en derrota (D)
   * - ``MINING_REFERENCE_GATHER``
     - 1000
     - Referencia sin depósitos

No puntuados hoy: duración de la partida, progreso tecnológico. ``game_duration`` es solo anuncio.

El porcentaje refleja solo las siete dimensiones base, no la bonificación por derrota de IA.
