Sistema de caza
===============

SoundRTS admite caza al estilo Age of Empires: los trabajadores atacan a la fauna, los animales cazados dejan cadáveres de comida recolectables, y las ovejas se pueden pastorear.

----

1. Flujo del jugador
--------------------

1. Retroceso / orden por defecto o clic derecho en un animal → ``attack`` sobre ``is_huntable`` (el ataque normal hace daño; no hace falta imperativo)
2. Al matar → aparece ``food_carcass``; la orden de ataque se completa (**sin** pitido falso ``order_impossible``)
3. Recolección automática → tras matar, el trabajador puede encolar recolección; con ``auto_gather`` también recoge y lleva comida
4. Huir al ser golpeado → ciervos y ovejas huyen; los jabalíes contraatacan
5. Pastoreo (opcional) → los trabajadores con ``can_herd 1`` pueden pastorear animales ``herdable`` (p. ej. ovejas)


Nota: la orden por defecto sobre creeps / PNJ neutrales comunes es ``go`` (solo mover); sobre animales cazables sigue siendo ``attack``.
Los modos ofensivo / defensivo / persecución **no** autoatacan animales neutrales sin un ataque imperativo.

----

2. Voz: etiqueta «animal» (no PNJ)
----------------------------------

Los animales de caza se colocan con ``computer_only ... neutral`` pero no se anuncian como «PNJ neutral».

.. list-table::
   :header-rows: 1

   * - Situación
     - Anuncio de ejemplo
   * - Seleccionar un ciervo
     - deer , animal
   * - Resumen de casilla
     - , 2 deer , animal
   * - Ctrl+Shift+F4 al jugador solo-fauna
     - you are animal

Reglas:

- Unidades con ``is_huntable 1`` o ``herdable 1`` → fauna → anunciadas como animal
- Una coma separa el nombre de la unidad y animal (mismo patrón que las etiquetas enemigo/aliado)
- Ctrl+Shift+F4 dice you are animal solo cuando toda unidad viva de ese jugador es fauna; ``quest_npc`` + ciervo mezclados sigue diciendo you are neutral NPC

Los PNJ de historia (``quest_npc``, etc.) mantienen neutral , NPC.

----

3. Colocación en el mapa
------------------------

.. code-block:: text

   computer_only 0 0 neutral b3 4 deer 2 sheep

Los mapas aleatorios también generan huertos y fauna cerca de las posiciones de inicio.

3.1 Diplomacia: la fauna no son aliados
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

La fauna se genera vía ``computer_only``, pero no se une a la alianza de ordenador ``"ai"`` por defecto y no puede aliarse con jugadores u otras facciones.

.. list-table::
   :header-rows: 1

   * - Regla
     - Significado
   * - Detección
     - La ranura ``computer_only`` contiene solo unidades con ``is_huntable 1`` o ``herdable 1`` (ciervo, oveja, un tigre personalizado, etc.)
   * - Motor
     - Ese ordenador obtiene `alliance = None`; ``allied`` es solo él mismo
   * - Varios rebaños
     - Cada línea ``computer_only`` es un punto de caza separado; los rebaños no se alianzan entre sí
   * - Ranura mixta
     - Si la misma línea mezcla animales y footmen, toda la ranura sigue siendo una IA normal y se une a `"ai"`
   * - Diplomacia del jugador
     - Los jugadores neutrales no pueden aliarse con F12; la fauna nunca es una facción diplomática

Animal personalizado (aislado de ``"ai"``):

.. code-block:: text

   def tiger
   class soldier
   is_huntable 1
   ...
   
   computer_only 0 0 neutral 5,5 2 tiger

Para que varios grupos de fauna actúen como una «facción naturaleza», usa el disparador ``(alliance …)`` explícitamente; eso no es el comportamiento de caza por defecto.

----

4. rules.txt
------------

Unidades integradas
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Tipo
     - Notas
   * - ``deer``
     - 35 comida, huye al ser golpeado
   * - ``sheep``
     - 25 comida, pastoreable, huye
   * - ``boar``
     - 50 comida, contraataca
   * - ``food_carcass``
     - cadáver recolectable (``collision 0``)

El ``can_gather`` de los trabajadores incluye ``food_carcass`` y ``orchard``.

Propiedades de animales
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Propiedad
     - Significado
   * - ``is_huntable 1``
     - cazable; el clic derecho por defecto es atacar
   * - ``flee_on_hit 1``
     - huir del atacante
   * - ``herdable 1``
     - puede ser pastoreado por trabajadores ``can_herd``
   * - ``food_deposit``
     - tipo de depósito de cadáver al morir
   * - ``food_deposit_qty``
     - cantidad de comida del cadáver
   * - ``no_number 1``
     - omitir número cuando solo hay uno de ese tipo

Trabajador: ``can_herd 1`` habilita el pastoreo (por defecto ``0``).

Ejemplo de animal personalizado
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def wolf
   class soldier
   is_huntable 1
   flee_on_hit 1
   food_deposit food_carcass
   food_deposit_qty 40
   no_number 1
   ai_mode guard

Tecnología
~~~~~~~~~~

``hunting_techniques``: recolección más rápida de huerto/cadáver, más rendimiento, comida de cadáver extra en animales. Se investiga en el ayuntamiento.

----

5. Fauna frente a PNJ de historia
---------------------------------

.. list-table::
   :header-rows: 1

   * - 
     - Fauna
     - PNJ de historia
   * - Ejemplos
     - ``deer``, ``sheep``, ``boar``
     - ``quest_npc``, ``npc_knight``
   * - Detección
     - ``is_huntable`` / ``herdable``
     - (puede tener ``receive_items``)
   * - Voz
     - animal
     - neutral , NPC
   * - Autoataque del jugador
     - no (se requiere ataque forzado)
     - no

Consulta `unit-default-behavior <unit-default-behavior.htm>`_.

----

6. Código y pruebas
-------------------

.. list-table::
   :header-rows: 1

   * - Función
     - Ruta
   * - Lógica de caza
     - ``soundrts/worldunit/worldcreature.py``, ``worldworker.py``
   * - Aislamiento de alianza de fauna
     - ``soundrts/worldplayerbase/base.py``, ``world/world_objects.py``
   * - Voz de animal
     - ``soundrts/clientgameentity/properties.py``
   * - Voz de cambio de jugador
     - ``soundrts/clientgame/game_resources.py``
   * - Apariciones RMG
     - ``soundrts/randommap.py``
   * - Pruebas
     - ``soundrts/tests/test_hunting.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``
