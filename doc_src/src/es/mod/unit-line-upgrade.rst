Mejoras de línea de unidad y entrenamiento de nivel máximo (line_upgrade)
=========================================================================

Para **autores de mods**: configure en ``rules.txt`` “investigar una forma → desbloquear el entrenamiento de nivel máximo → transformar unidades en el campo”, sin codificar nombres de unidad en el motor. Las líneas de cuartel de Age of Empires II DE funcionan así.

Resumen
-------

.. list-table::
   :header-rows: 1

   * - Capacidad
     - Descripción
   * - Entrenamiento de nivel máximo
     - El ``can_train`` del edificio lista la raíz (p. ej. ``militia``); se entrena la forma más alta desbloqueada
   * - Mejora de línea investigable
     - Marque la forma con ``line_upgrade 1`` y póngala en ``can_research``; al completar se guarda en ``player.upgrades``
   * - Transformación en el campo
     - Al completar la investigación, las unidades cuyo ``can_upgrade_to`` incluye esa forma se transforman al instante
   * - Cola de producción
     - Las órdenes ``train`` en cola o en curso de la misma línea pasan a la forma nueva (AoE2 DE: los mangoneles en cola salen como onagros). Coste y tiempo restante ya pagados no cambian
   * - Coste de entrenamiento
     - Por defecto se cobra el ``cost`` / ``time_cost`` de la **raíz** (anule con ``train_cost`` / ``train_time``)

El motor **no** codifica civilizaciones ni ids de unidad: solo campos de reglas y cadenas ``can_upgrade_to``.

Sintaxis en rules
-----------------

1. Línea de unidad (``can_upgrade_to``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def militia
    class soldier
    cost 20 0 50 0
    time_cost 21
    can_upgrade_to man_at_arms

    def man_at_arms
    is_a militia
    cost 40 0 100 0
    time_cost 40
    requirements feudal_age
    line_upgrade 1
    can_upgrade_to long_swordsman

- El ``cost`` / ``time_cost`` de niveles medios/altos suele ser el precio de **investigación** (como en DE).
- El entrenamiento sigue usando el coste de la raíz salvo ``train_cost`` / ``train_time``.

2. Edificio: ranuras de entrenamiento e investigación
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def barracks
    class building
    can_train militia spearman
    can_research tracking squires man_at_arms long_swordsman …

- Liste solo raíces en ``can_train``; el menú mapea al nivel más alto desbloqueado.
- Tras listar una forma ``line_upgrade 1`` en ``can_research``, se investiga como una tecnología.

3. Effect de tecnología opcional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Con ``class upgrade`` puede escribir::

    effect unit_line_upgrade man_at_arms

Mismo resultado que investigar esa forma (upgrades + morfosis). Cada objetivo aplica una vez por jugador.

Relación con la morfosis automática por edad
--------------------------------------------

.. list-table::
   :header-rows: 1

   * - Marca
     - Comportamiento
   * - (ninguna)
     - Si la fase tiene ``units_auto_upgrade 1`` y el objetivo incluye ese nombre de edad en ``requirements``, puede morfarse con la edad
   * - ``line_upgrade 1``
     - **No** se morfosea con la edad; hay que investigarla; el entrenamiento también exige el nombre en ``player.upgrades``
   * - ``no_auto_upgrade 1``
     - Omite la morfosis por edad; el entrenamiento sigue exigiendo investigación (mismo umbral que ``line_upgrade``)

Para líneas militares al estilo AoE2 DE, use ``line_upgrade 1``, no solo ``units_auto_upgrade``.

El menú de unidad ``upgrade_to`` ya **no** ofrece formas ``line_upgrade`` (evita pagar la diferencia por unidad, a diferencia de AoE2). Investíguelas en ``can_research`` del edificio.

Las líneas de edificios (torres, muros) igual: ``can_build`` lista la raíz; tras investigar, el menú mapea al nivel máximo; el coste de construcción usa la raíz (anule con ``train_cost``). ``line_upgrade_also`` desbloquea varias formas en una investigación.

Puntos de entrada del motor (referencia)
----------------------------------------

.. list-table::
   :header-rows: 1

   * - Símbolo
     - Ubicación
   * - ``resolve_trainable_unit_type``
     - ``soundrts/world_build_rules.py``
   * - ``effective_can_train`` / ``unit_train_cost`` / ``unit_train_time``
     - idem
   * - ``apply_unit_line_upgrade``
     - idem
   * - ``remap_queued_train_orders_for_line_upgrade`` / ``resolved_train_type_class``
     - idem
   * - ``ResearchOrder.complete``
     - ``soundrts/worldorders/production.py``
   * - ``effect_unit_line_upgrade``
     - ``soundrts/worldupgrade/attribute_effects.py``
   * - Omisión por edad
     - ``soundrts/worldphase.py`` → ``_auto_upgrade_units``
   * - Atributo por defecto
     - ``Creature.line_upgrade`` (``worldcreature.py``)
   * - Atributo int de rules
     - ``definitions.py`` → ``line_upgrade``

Pruebas
-------

``soundrts/tests/test_train_line_resolve.py``: la edad sola no desbloquea; tras upgrades / ``apply_unit_line_upgrade``, el entrenamiento de nivel máximo y la morfosis funcionan; completar la investigación reasigna la cola de la misma línea.

Mod aoe2
--------

``mods/aoe2/rules.txt`` marca formas de espada, lanza, arco, caballería y asedio con ``line_upgrade 1`` y las enlaza en ``can_research`` de cuarteles / arquería / establo / taller (y variantes de civ). Fuentes: ``mods/aoe2/SOURCES.md``.

Véase también: `Manual de modding <modding.htm>`_.
