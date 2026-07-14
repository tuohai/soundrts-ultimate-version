Configuración del comportamiento por defecto de las unidades (``rules.txt``)
============================================================================

Los autores de mapas y mods pueden establecer el comportamiento inicial de cada tipo de unidad al inicio de la partida en ``rules.txt``:

- Modo de IA por defecto (``ai_mode``): offensive / defensive / guard / chase
- Recolección automática (``auto_gather``): los trabajadores empiezan a recolectar automáticamente
- Reparación automática (``auto_repair``): los trabajadores empiezan a reparar automáticamente
- Exploración automática (``auto_explore``): las unidades móviles empiezan a explorar automáticamente

Los jugadores aún pueden cambiarlos en el juego tras la aparición.

----

1. Resumen
----------

.. list-table::
   :header-rows: 1

   * - Campo
     - Valores
     - Por defecto
     - Se aplica a
     - Descripción
   * - ``ai_mode``
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
     - soldiers=``offensive``, workers=``defensive``
     - unidades de combate
     - modo de IA inicial
   * - ``auto_gather``
     - ``1`` / `0`
     - workers=`1`
     - trabajadores
     - recolección automática al inicio
   * - ``auto_repair``
     - ``1`` / `0`
     - workers=`1`
     - trabajadores
     - reparación automática al inicio
   * - ``auto_explore``
     - ``1`` / `0`
     - ``0``
     - unidades móviles
     - exploración automática al inicio
   * - ``can_auto_explore``
     - ``1`` / `0`
     - ``0``
     - unidades móviles
     - mostrar activar/desactivar exploración automática en el menú de comandos

Escribe estos en el bloque `def <name>` de la unidad. Los campos omitidos usan los valores por defecto de arriba.

Ejemplo de campaña (caps. 24–27): los PNJ clave usan ``escort`` o ``ai_mode guard`` para que no persigan antes de la entrega/duelo. Tras la alianza, los disparadores cambian de modo:

- `(set_ai_mode offensive c2 1 npc_count_roland …)` — Roland pasa a ofensivo tras la ficha (cap. 25)
- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((go c1)))` — cap. 27 (``raynor7``): Marco solo pasa a ofensivo; los escoltas van a c1 para despejar la arena
- `(allied_assist computer1)` — todas las unidades de combate aliadas en guard → chase
- `(allied_assist computer1 c2 4 npc_archer_escort)` — solo arqueros escolta → chase
- `(allied_control computer1 c2 4 npc_knight_escort)` — caballeros escolta bajo mando del jugador (siguen en guard); otros auto → chase

Para duelos de cesión (``yield_on_defeat``), actívalo en tiempo de ejecución vía `` (set_yield_on_defeat 1 …)`` en lugar de en ``rules.txt`` al aparecer, para que los PNJ sean matables antes de entregar la ficha. Consulta `campaign-northern-arc.htm <campaign-northern-arc.htm>`_.

``auto_explore`` frente a ``can_auto_explore``:

``auto_explore`` — si la unidad empieza con exploración automática activada.

``can_auto_explore`` — si el menú de comandos ofrece activar/desactivar exploración automática.

Independientes: p. ej. solo los caballeros obtienen ``can_auto_explore 1``, o ``auto_explore 1`` para exploradores al inicio.

----

2. Modo de IA (``ai_mode``)
---------------------------

2.1 Modos
~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Valor
     - Nombre
     - Comportamiento
   * - ``offensive``
     - Ofensivo
     - atacar unidades hostiles en la casilla actual (por defecto habitual)
   * - ``defensive``
     - Defensivo
     - retirarse de amenazas hostiles cuando es desfavorable; combatir cuando se va por delante
   * - ``guard``
     - Guardia
     - mantener posición; contraatacar solo si está habilitado
   * - ``chase``
     - Perseguir
     - mantener un solo ``AttackAction`` sobre el enemigo fijado y seguir por salidas entre casillas (sin ``go`` automático) hasta estar a alcance

2.1.1 Punto de retención (``position_to_hold``) y salir de casilla
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Las unidades nacen con la casilla actual como ``position_to_hold``. Dentro de esa zona,
``_must_hold`` impide salir:


.. list-table::
   :header-rows: 1

   * - Modo IA
     - ¿Limitado por ``position_to_hold``?
   * - ``offensive`` / ``guard``
     - Sí (no salen solas sin una orden que haga ``stop()``)
   * - ``defensive``
     - No (pueden retirarse)
   * - ``chase``
     - No (se limpia el hold al cruzar casillas)


Las órdenes ``go`` / ``attack`` del jugador llaman ``stop()`` al primer update y limpian
``position_to_hold``.

La patrulla es un comando con ruta, no un modo de IA. No puedes escribir ``ai_mode patrol``. Usa ``guard`` o ``chase`` para efectos similares.

2.2 Ejemplos
~~~~~~~~~~~~

.. code-block:: text

   def knight
   class soldier
   ...
   ai_mode guard
   
   def footman
   class soldier
   ...
   ai_mode defensive

2.3 Unidades neutrales
~~~~~~~~~~~~~~~~~~~~~~

Unidades del jugador en modo ``offensive``, ``defensive`` o ``chase``:

- no autoatacan unidades neutrales (bichos / PNJ / fauna `computer_only ... neutral`);
- no huyen por neutrales (el modo defensivo solo sopesa amenazas hostiles reales);
- ``go`` por defecto / normal sobre un neutral (no imperativo) solo mueve, sin AttackAction;
- el orden por defecto sobre ``is_huntable`` sigue siendo ``attack`` y hace daño;
- para que la IA trate un creep / PNJ neutral como objetivo automático, emite un ataque forzado
  (``imperative`` — p. ej. Ctrl+clic; el motor convierte el ``go`` imperativo en ``attack``).

Voz: los animales de caza (``is_huntable`` / ``herdable``, p. ej. ciervo, oveja) se anuncian como

"deer , animal", no "neutral , NPC". Los PNJ de historia (``quest_npc``, etc.) siguen diciendo

"neutral , NPC". Consulta `hunting.htm <hunting.htm>`_.

El modo ``guard`` no cambia: sin ataques proactivos; contraataque solo si está habilitado y te golpean.

Los bichos de ordenador neutrales siguen usando ``guard`` forzado + contraataque de su lado.

2.4 Notas
~~~~~~~~~

- Los valores inválidos se ignoran (registrados) y se vuelve al valor por defecto.
- Los bichos neutrales (`computer_only ... neutral`) siguen forzados a ``guard`` + contraataque independientemente de ``ai_mode``.

----

3. Recolección / reparación automática
--------------------------------------

Solo para trabajadores:

- ``auto_gather 1`` — los trabajadores inactivos van a recolectar cuando hay un depósito y un almacén cerca.
- ``auto_repair 1`` — los trabajadores inactivos reparan aliados dañados en la misma casilla (necesita ``can_repair 1``).

Ambos están activados por defecto. Establece ``0`` en la def del trabajador para desactivarlos al inicio. Los jugadores aún pueden alternarlos en el juego.

:strong:```can_repair`` — ``1`` o ``0``. Por defecto ``1`` en trabajadores. Cuando es ``0``, las órdenes de reparación y la reparación automática se desactivan.

----

4. Orden de captura por defecto (``can_capture``)
-------------------------------------------------

Para unidades con habilidades de ataque, controla la orden por defecto de clic derecho sobre enemigos con
:strong:```capture_hp_threshold 100`` (captura por contacto):

.. list-table::
   :header-rows: 1

   * - Valor
     - Comportamiento
   * - `1` (por defecto)
     - Orden de captura por defecto; la IA usa captura por contacto
   * - ``0``
     - Ataque/movimiento por defecto; la IA ataca con normalidad

No bloquea la captura a umbrales más bajos (p. ej. ``30``) vía daño de combate — solo la
ruta de captura por contacto con umbral 100 y la orden por defecto de clic derecho.

.. code-block:: text

   def footman
   class soldier
   can_capture 1
   
   def archer
   class soldier
   can_capture 0

Véase también los cuarteles capturables de mapas aleatorios en ``player/homm-civ5-play.htm``.

----

5. Exploración automática
-------------------------

Para cualquier unidad con velocidad > 0. Controlado por ``auto_explore`` (estado inicial) y ``can_auto_explore`` (opción de menú).

- ``can_auto_explore 1`` — el menú de comandos muestra activar/desactivar exploración automática (solo en unidades que lo tienen).
- ``auto_explore 1`` — empieza a explorar cuando está inactiva; el combate usa ``ai_mode`` cuando aparecen enemigos.

En tiempo de ejecución: otras órdenes pausan la exploración; se reanuda al volver a estar inactiva. Desactivar exploración automática siempre disponible mientras se explora. Activar solo si ``can_auto_explore 1``. La exploración de la IA del ordenador es independiente.

----

6. Ejemplo combinado
--------------------

.. code-block:: text

   def peasant
   class worker
   auto_gather 1
   auto_repair 0
   ai_mode defensive
   
   def knight
   class soldier
   auto_explore 1
   can_auto_explore 1
   ai_mode guard
   
   def footman
   class soldier
   ai_mode defensive

----

7. Preguntas frecuentes
-----------------------

``Q: ¿Por qué no funciona ``ai_mode patrol``?``  
A: La patrulla necesita una ruta. Valores válidos: ``offensive``, ``defensive``, ``guard``, ``chase``.

``Q: ¿``auto_explore`` en un edificio?``  
A: Se ignora (velocidad 0).

``Q: ¿``auto_gather`` en un soldado?``  
A: Solo tiene sentido en trabajadores.

P: ¿En qué se diferencia chase del antiguo salto con ``go`` automático?  
A: Ahora mantiene el ataque y sigue entre casillas; no está limitado por ``position_to_hold``.
Ofensivo / guardia sí lo están, salvo que el jugador ordene moverse.

P: ¿Las unidades ofensivas/persecución autoatacarán PNJ neutrales?  
A: No. Los modos ofensivo, defensivo y persecución ignoran a los neutrales para autoataque y huida;
usa un comando de ataque forzado para luchar contra ellos.

P: ¿Por qué los arqueros atacan un cuartel con clic derecho pero los footmen lo capturan?  
A: Comprueba ``can_capture``. Por defecto ``1`` → captura en objetivos ``capture_hp_threshold 100``; ``0`` → ataque normal.

----

8. Referencia de campos
-----------------------

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Valores válidos
   * - ``ai_mode``
     - string
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
   * - ``auto_gather``
     - int
     - ``1`` / `0`
   * - ``auto_repair``
     - int
     - ``1`` / `0`
   * - ``auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_capture``
     - int
     - ``1`` / `0`
