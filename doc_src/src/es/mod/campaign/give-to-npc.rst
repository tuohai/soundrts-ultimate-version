Dar objetos a PNJ (``give`` + ``npc_has_item``)
===============================================

Permite a los jugadores entregar objetos transportados a otra unidad (PNJ neutral, aliado, enemigo) y comprobar la entrega con :strong:```npc_has_item``.

----

1. Resumen
----------

.. list-table::
   :header-rows: 1

   * - Parte
     - Nombre
     - Función
   * - Orden
     - ``give``
     - transferir objeto del portador al objetivo
   * - Campo
     - ``receive_items``
     - interruptor maestro (por defecto 0)
   * - Campo
     - ``accepted_items``
     - lista blanca de objetos; vacía = cualquiera
   * - Campo
     - ``accept_from``
     - relación del dador: ``self``/``ally``/``neutral``/``enemy``; vacía = cualquiera
   * - Campo
     - ``accept_givers``
     - tipos de unidad dadora; vacía = cualquiera
   * - Condición
     - ``npc_has_item``
     - el objetivo recibió / tiene el objeto
   * - Condición
     - ``npc_has_items``
     - el objetivo recibió / tiene una *cantidad* de objetos (objetivos de colección)

Al éxito: el objeto pasa al inventario del objetivo; ``received_items`` registra el tipo; retroalimentación de audio/IU.

Los objetivos necesitan ``receive_items 1`` en ``rules.txt`` o la entrega se rechaza.

----

2. Uso del jugador
------------------

El portador necesita ``inventory_capacity \> 0`` y el objeto (vía ``pickup``).

1. Clic derecho en unidad no enemiga mientras llevas → dar por defecto (primer objeto aceptable).
2. Menú de comandos: «Dar».
3. Tecla rápida: ``g`` (``style.txt``).

Dar con clic derecho solo cuando llevas + el objetivo no es enemigo ni edificio.

----

3. Script: ``give`` en disparadores
-----------------------------------

.. code-block:: text

   give <target_unit_id>
   give <target_unit_id> <item>    ; type_name or item id

----

4. ``npc_has_item``
-------------------

.. code-block:: text

   (npc_has_item <NPC_selector> <item_type> [square])
   (npc_has_item <index> <unit_type> <item_type>)
   (npc_has_item <square> <index> <unit_type> <item_type>)

- Clásico: selector = ``type_name`` o id de unidad; casilla opcional = PNJ actualmente en esa casilla.
- Índice global: `(npc_has_item 3 quest_npc short_sword)` — 3.ª ``<unit_type>`` generada para ese propietario (cualquier casilla).
- Índice de casilla: N-ésima en `<square>` (estable tras moverse). Consulta `unit-index.htm <unit-index.htm>`_. El capítulo 28 usa la forma global.

Verdadero si ``received_items`` contiene el tipo o el inventario aún lo tiene.

Compara con `find-item.htm <find-item.htm>`_. Para llegar-y-desaparecer sin PNJ, usa `brought-items.htm <../player/brought-items.htm>`_.

----

4b. ``npc_has_items`` (variante con contador)
-----------------------------------------------

.. code-block:: text

   (npc_has_items <NPC_selector> <item_type> <count> [square])
   (npc_has_items <index> <unit_type> <item_type> <count>)
   (npc_has_items <square> <index> <unit_type> <item_type> <count>)


Los mismos selectores que ``npc_has_item``, más un ``<count>`` obligatorio: la
condición sólo es verdadera cuando la unidad tiene **al menos esa cantidad** de
objetos de ese tipo.

``npc_has_item`` sólo pregunta si la unidad tiene el *tipo* de objeto
(``received_items`` es un conjunto), por lo que entregar un solo objeto ya la
cumple. Usa ``npc_has_items`` para objetivos de colección que exigen varias
copias — p. ej. el capítulo 4 de Joan of Arc requiere las tres reliquias en la
catedral de Reims:

.. code-block:: text

   trigger player1 (npc_has_items npc_reims_cathedral relic 3 c5) (do (objective_complete 1) (cut_scene 8837))


La cuenta es el mayor entre (a) cuántos objetos se entregaron con ``give`` y
(b) cuántos hay ahora en el inventario de la unidad — así sobrevive a que el
objeto vuelva a salir del inventario, y también cuenta los objetos con los que
el PNJ empieza. El mismo objeto nunca se cuenta dos veces.

``<count>`` debe ser un entero positivo; ``0``, un número negativo o un token no
numérico hacen que la condición sea falsa.

----

5. Reglas de recepción
----------------------

Todas deben cumplirse:

.. list-table::
   :header-rows: 1

   * - Campo
     - Valores
   * - ``receive_items``
     - ``1`` / `0`
     - por defecto 0
   * - ``accepted_items``
     - lista de tipos
     - vacía = cualquiera; ``is_a`` funciona
   * - ``accept_from``
     - relaciones
     - vacía = cualquiera
   * - ``accept_givers``
     - tipos de unidad
     - vacía = cualquiera

Relaciones (receptor frente a dador): ``self`` > ``ally`` > ``neutral`` > ``enemy``.

Con ``accept_from enemy``, el clic derecho en ese enemigo con el objeto correcto se convierte en dar en lugar de atacar (solo para ese objeto + tipo de unidad).

Ejemplos
~~~~~~~~

Caballero aliado acepta solo lanza:

.. code-block:: text

   def knight
   receive_items 1
   accepted_items knight_lance
   accept_from ally

Líder enemigo acepta carta solo de campesino:

.. code-block:: text

   def npc_knight_leader
   receive_items 1
   accepted_items secret_letter
   accept_from enemy
   accept_givers peasant
   ai_mode guard

Campaña caps. 24–27: `campaign-northern-arc.htm <../player/campaign-northern-arc.htm>`_.

----

6. Mapa de demostración
-----------------------

``res/multi/give_demo.txt``:

.. code-block:: text

   health_potion a1
   computer_only 0 0 neutral c3 quest_npc
   trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)

Ejemplos de campaña (``The Legend of Raynor``): cap. 14 entregar ``pickaxe`` al ``npc_peasant`` aliado; cap. 15
entregar ``knight_lance`` al ``npc_knight`` neutral; cap. 16 entregar ``wand`` al ``npc_mage`` enemigo.
Consulta ``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``. Multijugador: ``res/multi/give_demo.txt``.

----

7. Archivos de implementación
-----------------------------

.. list-table::
   :header-rows: 1

   * - Función
     - Ruta
   * - ``GiveOrder``
     - ``soundrts/worldorders/skills.py``
   * - Transferencia
     - ``soundrts/worldunit/world_order.py``
   * - ``accepts_item``
     - ``soundrts/worldunit/worldcreature.py``
   * - Disparador
     - ``soundrts/worldplayerbase/triggers.py``
   * - Pruebas
     - ``soundrts/tests/test_give_item_to_npc.py``

----

8. Casos límite
---------------

- Triple comprobación: ``receive_items``, ``accepted_items``, ``accept_from`` (+ ``accept_givers`` si está).
- El objetivo debe ser una unidad con ``player``.
- El objeto debe estar en el inventario del dador.
- La entrega ``ignora`` el ``inventory_capacity`` del objetivo (transferencia narrativa); el exceso cae al suelo.
- ``equip`` se ejecuta en el receptor como ``pickup`` (se aplican buffs/habilidades).

----

9. Pruebas
----------

.. code-block:: text

   python -m pytest soundrts/tests/test_give_item_to_npc.py -q

También: ``test_campaign_alliance_transfer_triggers.py`` para disparadores de alianza / transferencia.

----

10. Campaña caps. 24–27
-----------------------

.. list-table::
   :header-rows: 1

   * - Cap.
     - Objeto
     - Receptor
   * - 24
     - ``secret_letter``
     - ``npc_knight_leader`` (Garrek)
   * - 25
     - ``garrek_token``
     - ``npc_count_roland`` (Roland)
   * - 26
     - ``war_banner``
     - ``npc_general_vera`` (Vera)
   * - 27
     - —
     - duelo con ``npc_marco_ironhand``

Tras la muerte de los traidores del cap. 24, ``(add_inventory_item garrek_token 1 raynor)`` pone la ficha en el inventario de Raynor para el cap. 25. Ejecuta ``cut_scene`` en disparadores de player1 tras ``npc_has_item`` para que el humano oiga la voz. Guía completa: `campaign-northern-arc.htm <../player/campaign-northern-arc.htm>`_.

----

11. Campaña cap. 28 (entrega indexada)
--------------------------------------

.. code-block:: text

   trigger player1 (npc_has_item 3 quest_npc short_sword) (objective_complete 2)

Solo cuenta el 3.er ``quest_npc`` en B2. El mismo capítulo demuestra ``killed_target`` indexado y derrota por muerte incorrecta: `unit-index.htm <unit-index.htm>`_.
