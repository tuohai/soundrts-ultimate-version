Terreno cuadrado configurable y terreno edificable.
===================================================

.. epigraph:: For **mod authors**: ``class terrain``, ``class building_land``, object-driven ``square_terrain``, and the map editor palette. Complements ``mapmaking.htm`` and ``modding.htm``.


----

Descripción general
-------------------


Todo el terreno se declara en ``rules.txt`` como ``class terrain``; ``style.txt`` usa los mismos nombres ``def`` para voz, ``ground`` y colores. La unidad ``move_on_<key>`` / ``falling_on_<key>`` coincide con los nombres de tipo de terreno o las categorías ``ground``; consulte ``modding.htm`` (Sistema de sonido de combate).

**El motor ya no asigna un terreno predeterminado a cada casilla.** El terreno de una casilla proviene únicamente de:

1. Mapa ``terrain <name> <squares>``
2. Objeto ``square_terrain`` (bosques, pueblos, prados, etc.)
3. ``high_grounds`` / ``is_high_ground``: solo voz adicional de "terreno elevado", no un nombre de terreno


Definiciones y ubicación
------------------------


**reglas.txt:**

.. code-block:: text

   def plain
   class terrain
   is_dynamic 1

   def lake
   class terrain
   is_water 1
   is_dynamic 0


**Mapa:**

.. code-block:: text

   terrain plain a1
   terrain lake d1
   terrain hill c1
   high_grounds e1


- ``terrain lake d1`` **no** necesita una línea ``water d1`` separada
- La palabra clave heredada ``water`` todavía funciona
- Cuadrados sin ``terrain``: ``type_name`` vacío, sin voz de terreno


Terreno edificable (``class building_land``)
--------------------------------------------


``meadow``, ``build_site`` y los tipos personalizados ya no están codificados. Declarelos con **`class building_land`** en ``rules.txt``.

.. code-block:: text

   def meadow
   class building_land
   square_terrain meadows 40

   def build_site
   class building_land
   square_terrain build_sites 50


.. list-table::
   :header-rows: 1

   * - Mecanismo
     - Rol
   * - ``default_building_land``
     - Reglas predeterminadas cuando el mapa omite ``building_land``
   * - Mapa ``building_land <name>``
     - Tipo de terreno edificable predeterminado en todo el mapa
   * - ``nb_<type>_by_square <N>``
     - Rellenar automáticamente cada cuadrado con N objetos de ese tipo ``class building_land``
   * - ``nb_meadows_by_square <N>``
     - Legado; escriba desde ``building_land`` / inferencia de mapa
   * - ``additional_building_land <name> <squares…>``
     - Colocar cualquier tipo de terreno edificable declarado en las plazas indicadas.

Cuando el despegue o algunas mejoras restablecen el terreno edificable en su lugar, el motor utiliza **el tipo guardado cuando se colocó el edificio** primero; solo si falta, vuelve a la palabra clave ``building_land`` del mapa o a una única palabra clave ``nb_<type>_by_square``.

Consulte ``mapmaking.htm`` (*Building_land*, *Nb_<type>_by_square*).


``class terrain`` atributos
---------------------------


.. list-table::
   :header-rows: 1

   * - Atributo
     - Significado
   * - ``is_dynamic``
     - ``0`` estático; ``1`` puede ser anulado por el terreno del objeto
   * - ``is_ground`` / ``is_air`` / ``is_water``
     - Banderas de transitabilidad terrestre/aire/agua
   * - ``is_high_ground``
     - Terreno elevado + voz
   * - ``passable_units``
     - Lista blanca (se aplica herencia ``is_a``)
   * - ``blocks_path``
     - Bloquea las salidas a los vecinos (por ejemplo, bosque denso, montaña)
   * - ``speed``
     - Opcional. ``speed <ground> <air>`` (por ejemplo, ``speed .5 1`` → 50% de velocidad de avance). Se aplica cuando el mapa establece ``terrain <name>``; mapa por cuadrado ``speed`` anulación de líneas

El mapa ``terrain <name>`` escribe estas banderas en el cuadrado. **Velocidad de movimiento** en un cuadrado (no es lo mismo que la unidad ``speed_on_terrain``) se resuelve como:

1. Mapa ``speed <ground> <air> <squares>``: autorizado en tiempo de ejecución
2. ``speed`` en el ``class terrain`` en ``rules.txt`` - cuando el mapa tiene ``terrain`` pero no ``speed`` para esa celda
3. Predeterminado ``(100, 100)``

``editor_palette.txt`` es solo para editor: las entradas de la paleta sin ``speed`` heredan de ``rules.txt`` cuando se carga la paleta; guardar el mapa escribe líneas ``speed``. El juego **no** lee la paleta en tiempo de ejecución.

Ejemplo de Ford (aguas poco profundas, velocidad media de avance):

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1


Cuando ``is_ground 1`` se establece en terreno acuático (``ford``, ``big_bridge``), la búsqueda de caminos trata la loseta como parte de la **misma región de terreno** que la tierra adyacente, de modo que las unidades puedan atravesar vados sin quedarse atrapadas en la orilla.

**Tramos construidos por jugadores** (``wooden_bridge``, ``is_buildable_on_water_only``, ``bridge_terrain bridge_deck``): consulte `Building bridges on water <water-bridge-building.htm>`_ (`zh <../../zh/mod/water-bridge-building.htm>`_). El mapa ``big_bridge`` es terreno de caballete fijo; Los tramos de reproductor terminados utilizan ``bridge_deck``.

Modificadores de combate de unidades en el terreno (desde 1.4.5.0)
------------------------------------------------------------------

Además de por cuadrado ``terrain_speed``, las definiciones de unidad pueden anular las estadísticas de movimiento y combate **según el terreno en el que se encuentra la unidad**. Coincidencias de sintaxis ``speed_on_terrain``:

.. code-block:: text

   <terrain_name> <modifier> [<terrain_name> <modifier> ...]


**Qué mosaico cuenta:** el **cuadro actual del atacante/motor** ``type_name`` (o ``type_name_at`` para terreno de subcelda).

**Apilamiento:** los modificadores son **aditivos** (negativos = penalización), y se aplican después de ``mdg_vs`` / ``mdg_cd_vs``, etc. Los valores usan las mismas unidades que ``mdg`` / ``mdg_cd`` (decimales permitidos; almacenados ×1000 internamente).

.. list-table::
   :header-rows: 1

   * - Propiedad
     - Efecto
   * - ``speed_on_terrain``
     - Velocidad de movimiento en ese terreno (comportamiento existente)
   * - ``mdg_on_terrain`` / ``rdg_on_terrain``
     - Bonificación de daño cuerpo a cuerpo/a distancia (después de la base + ``*_vs``)
   * - ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``
     - Bonificación de enfriamiento de ataque (**positivo = ataques más lentos**)
   * - ``charge_mdg_terrain`` / ``charge_rdg_terrain``
     - Bonificación de daño por carga adicional (después de ``charge_mdg`` + ``charge_*_vs``)
   * - ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``
     - Bonificación de tiempo de reutilización de carga (positivo = tiempo de reutilización de carga más largo)

Golpea/esquiva en terreno **objetivo** (existente): ``mdg_cover_on_terrain``, ``rdg_cover_on_terrain``, ``mdg_dodge_on_terrain``, ``rdg_dodge_on_terrain``.

**Pantalla de atributos (Alt+V):** muestra las líneas ``*_on_terrain`` / carga de la unidad, y las lecturas en vivo de daño / enfriamiento / velocidad incluyen ``*_vs`` del terreno de la casilla actual más ``*_on_terrain`` (``*_vs`` de terreno = porcentaje decimal; ``speed_on_terrain`` sigue siendo absoluto).

**Ejemplo: caballero debilitado en un pantano:**

.. code-block:: text

   def knight
   speed 2.5
   mdg 6
   mdg_cd 1.5
   speed_on_terrain marsh 1.5 ford 1.5
   mdg_on_terrain marsh -2
   mdg_cd_on_terrain marsh 0.5


En ``marsh``: velocidad 1,5, daño cuerpo a cuerpo 4, tiempo de reutilización del ataque 2,0 s.

**Ejemplo: unidad con cargo:**

.. code-block:: text

   def raynor
   charge_mdg 4
   charge_mdg_cd 10
   charge_mdg_terrain marsh -1
   charge_mdg_cd_on_terrain marsh 2


En ``marsh``: bonificación de carga −1, tiempo de reutilización de carga +2 s.

Implementación: ``soundrts/combat/damage_calculation.py``, ``soundrts/combat/attack_action.py``; pruebas: ``test_combat_terrain_modifiers.py``.

Los tipos en ``res/rules.txt`` incluyen ``plain``, ``lake``, ``marsh``, ``mountain``, ``forest``, ``dense_forest``, ``meadows``, ``build_sites``, ``town``, ``ford``, etc.


``square_terrain``: terreno controlado por objetos
--------------------------------------------------


**Mapa ``terrain`` pinta la capa base; ``square_terrain`` permite que los objetos crezcan en la capa superior** que puede aparecer y desaparecer en tiempo de ejecución.

Sintaxis en cualquier ``def``:

.. code-block:: text

   square_terrain <terrain_name> [priority] [min_count]


- ``priority`` (predeterminado 50): mayores ganancias
- ``min_count`` (predeterminado 1): objetos mínimos de ese ``type_name`` en el cuadrado

Ejemplo: bosque versus bosque denso:

.. code-block:: text

   def wood
   class deposit
   square_terrain forest 80
   square_terrain dense_forest 90 7


Cada marca, ``update_terrain()`` elige la entrada elegible de mayor prioridad y establece el ``type_name`` del cuadrado. El terreno edificable tiene una capa de voz separada (``building_land_voice`` vs ``feature_voice``).

El ``terrain forest`` dinámico en el mapa genera objetos coincidentes a través de enlaces ``square_terrain`` inversos (consulte el documento chino para ver las tablas completas).


Capas de voz
~~~~~~~~~~~~


``resolve_square_layers()`` puede acumularse:

- ``feature_voice`` — terreno del objeto ganador (``forest``, ``town``,…)
- ``building_land_voice`` — ``meadows`` / ``build_sites`` cuando es diferente de la característica
- ``high_ground_voice`` — marcador de terreno elevado


Paleta del editor de mapas
--------------------------


Consola ``edit``; fijaciones en ``res/ui/editor_bindings.txt``. Lógica en ``soundrts/lib/editor_palette.py``.

- Terrenos estáticos (``lake``, ``mountain``,…): ``fixed_terrain``, guardados como ``terrain <name>``
- Terrenos dinámicos (``forest``, ``meadows``,…): generan objetos, no bloqueados
- Nombres de paleta alineados con ``res/ui/editor_palette.txt`` (``forest`` no heredado ``woods``)


Pruebas
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py -q


Cuadros completos y prosa china: ``../../zh/mod/building-land-terrain.htm``.