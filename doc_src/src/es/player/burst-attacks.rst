Ataques en ráfaga (``damage_seq``) y ballesta de repetición
===========================================================

Desde SoundRTS 1.3.8.2 (mejorado en 1.4.3.6), las unidades pueden realizar ataques en ráfaga / secuencia: un ciclo de ataque dispara varios golpes en rápida sucesión, similar al Chu Ko Nu (ballesta de repetición) de *Age of Empires*. Cada disparo tira impacto, crítico y debilitamiento por separado.

Referencia oficial: ``mod/modding.rst`` (Combat system → ``damage_seq``).

.. note::

   **No es lo mismo que ``effect burst`` de habilidad:** Esta página cubre **ataques normales de unidad** vía ``damage_seq`` (p. ej. ballesta de repetición). Los golpes de combo de habilidad usan ``effect burst mdg|rdg …`` en ``class skill``, lanzados manualmente o autoactivados, con sintaxis y ubicación distintas. Consulta la guía de habilidades (`../mod/skills-and-effects.htm`_).

----

1. Resumen
----------

.. list-table::
   :header-rows: 1

   * - Aspecto
     - Comportamiento
   * - Daño total por ciclo
     - Reparto igual/manual: sigue igualando ``mdg`` / ``rdg``; modo ``secondary``: primera viva + flechas fijas posteriores (puede superar la base)
   * - Disparos por ciclo
     - Hasta 6 (`damage_seq … <times>`)
   * - Tiradas de impacto
     - Independientes por disparo; las flechas secundarias aciertan al 100%
   * - Tiempo de reutilización
     - ``mdg_cd`` / ``rdg_cd`` empieza tras terminar la ráfaga completa
   * - Sonidos de lanzamiento
     - Un ``launch_mdg`` / ``launch_rdg`` por disparo

----

2. Configuración en rules.txt
-----------------------------

2.1 Sintaxis
~~~~~~~~~~~~

.. code-block:: text

   damage_seq mdg|rdg <times> [(damage d1 d2 ...)] [(secondary pierce melee)] [(interval seconds)]

Define el ``mdg`` o ``rdg`` base antes de ``damage_seq``.

2.2 División automática (desde 1.4.3.6)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Omite ``(damage …)`` para dividir el daño base por igual:

.. code-block:: text

   rdg 6
   damage_seq rdg 3 (interval 0.25)

→ tres disparos de 2 de daño cada uno. Funciona con daño base fraccionario (p. ej. ``rdg 7.5`` con 3 disparos → 2.5 cada uno).

2.3 División manual
~~~~~~~~~~~~~~~~~~~

Los valores enteros de segmento deben sumar el daño base (mismas unidades que en rules):

.. code-block:: text

   mdg 12
   damage_seq mdg 3 (damage 6 3 3) (interval 0.2)

El ``(damage …)`` manual solo usa valores enteros; el daño base fraccionario (p. ej. ``rdg 2.5``) no se puede expresar así — usa la división automática.

2.3b Flechas secundarias AoE2 (``secondary``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Alineado con el Chu Ko Nu de Age of Empires II DE: primer disparo = ataque vivo de la unidad (aplican mejoras) + melee fijo; disparos posteriores = pierce + melee fijos (**no** mejorados por herrería/química). El melee puede ser ``0`` (aún daña armadura melee negativa como arietes).

.. code-block:: text

   rdg 8
   rdg_cd 2.77
   rdg_ready 0.23
   damage_seq rdg 3 (secondary 3 0) (interval 0.23)

El Chu Ko Nu de élite usa ``rdg 5 (secondary 3 0)`` (5 flechas). Este modo **no** exige que la suma iguale ``rdg``.

2.4 Intervalo
~~~~~~~~~~~~~

- `(interval 0.25)` — segundos entre disparos
- Si `times > 1` y el intervalo se omite o es `0`, por defecto 0.25 s

2.5 Consejos de ráfaga a distancia
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Establece ``rdg_projectile 1`` para comportamiento de proyectil (reglas de terreno elevado, etc.)
- Usa un ``rdg_cd`` más largo que un arquero de un solo disparo: el DPS de ráfaga es mayor pero cada ciclo sigue respetando el ``rdg`` total

Ejemplo (unidad integrada):

.. code-block:: text

   def repeating_crossbowman
   class soldier
   rdg 6
   rdg_cd 2.5
   rdg_range 4
   rdg_projectile 1
   damage_seq rdg 3 (interval 0.25)

----

3. Sonidos (``style.txt``)
--------------------------

Cada disparo dispara ``launch_rdg`` o ``launch_mdg``. Lista varios IDs de sonido para que los disparos puedan variar:

.. code-block:: text

   def repeating_crossbowman
   is_a archer
   launch_rdg 1042 1042 1042

Los sonidos de impacto / fallo (``rdg_hit``, ``rdg_missed``, …) siguen reproduciéndose por cada tirada de impacto exitosa como de costumbre.

----

4. Ejemplo integrado: ``repeating_crossbowman``
-----------------------------------------------

.. list-table::
   :header-rows: 1

   * - Elemento
     - Valor
   * - Ubicación
     - ``res/rules.txt``
   * - Mejora
     - ``archer`` → ``repeating_crossbowman`` (``can_upgrade_to``)
   * - Voz (ZH)
     - Zhuge Ballestero (``tts.txt`` id 5082)
   * - Estadísticas
     - 3×2 daño a distancia por ciclo, 2.5 s de recarga, alcance 4

----

5. Errores habituales
---------------------

.. list-table::
   :header-rows: 1

   * - Problema
     - Causa / solución
   * - ``damage_seq`` ignorado
     - ``mdg`` / ``rdg`` base no definido, o suma de segmentos ≠ base (división manual)
   * - Intervalo incorrecto
     - Antes de 1.4.3.6, el intervalo se ignoraba (corregido); comprueba la versión del juego
   * - Daño fraccionario + `(damage …)` manual
     - Usa la división automática
   * - Más de 6 disparos
     - El motor limita a 6 por ataque
   * - Solo un sonido de lanzamiento
     - Esperado en unidades sin ráfaga; las de ráfaga necesitan manejo por disparo (1.4.3.6+)

----

6. Archivos y pruebas relacionados
----------------------------------

.. list-table::
   :header-rows: 1

   * - Archivo
     - Función
   * - ``soundrts/definitions.py``
     - Analiza ``damage_seq`` en rules
   * - ``soundrts/combat/damage_effects.py``
     - Programa golpes de ráfaga y sonidos de lanzamiento
   * - ``soundrts/combat/attack_action.py``
     - Preparación de ataque / tiempo de reutilización
   * - ``soundrts/tests/test_damage_seq_burst.py``
     - Pruebas de análisis y regresión

Ejecutar pruebas:

.. code-block:: bash

   python -m pytest soundrts/tests/test_damage_seq_burst.py -q
