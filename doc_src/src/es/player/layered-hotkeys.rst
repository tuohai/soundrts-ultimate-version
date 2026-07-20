# Esquema de teclas de acceso rápido en capas

Esta guía describe las teclas de acceso rápido de la interfaz en capas de SoundRTS: una capa base global más una capa por interfaz, por lo que la misma tecla física puede significar diferentes cosas en diferentes modos. Destinado a jugadores y autores de mods que personalizan enlaces.


----


1. Descripción general y motivación
-----------------------------------


viejo esquema
~~~~~~~~~~~~~


Todas las teclas de acceso rápido vivían en un solo archivo ``res/ui/bindings.txt``. Las claves se saturaron; la misma carta entraba en conflicto entre la selección de unidades, los pedidos y la exploración de mapas.

Nuevo esquema
~~~~~~~~~~~~~


- Capa global: recursos, movimiento, saltos cuadrados, confirmación de comandos, disponible en todos los modos.
- Capa de interfaz: enlaces específicos del modo (unidad, edificio, comando, habilidad, mapa, etc.).
- Cambio de modo: las teclas F alternan dentro de los grupos; ayuda/mapa/diplomacia son modos superpuestos que restauran el modo anterior al salir.

Implementación: ``soundrts/clientgame/interface_modes.py``.


----


2. Arquitectura y reglas de carga.
----------------------------------


.. code-block:: text

   flowchart TD
       global[global_bindings.txt]
       mode[current mode txt]
       custom[cfg/bindings.txt]
       mod[mod bindings.txt]
       global --> merge[merged load]
       mode --> merge
       custom --> merge
       mod --> merge
       merge --> active[active hotkeys]



Orden de carga
~~~~~~~~~~~~~~


1. `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_ (base global)
2. Archivo de modo actual (consulte la tabla a continuación)
3. El usuario anula `cfg/bindings.txt <../../../soundrts/paths.py>`_ (``CUSTOM_BINDINGS_PATH``)
4. Mod sin código auxiliar ``bindings.txt`` (anexo heredado)

Las cargas posteriores anulan las anteriores para la misma clave.

Subpantallas y RPG
~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Contexto
     - Comportamiento
   * - Inventario/equipo/atributos
     - Reemplaza temporalmente a ``\_bindings``; ``restore_active_bindings`` al salir
   * - RPG en primera persona
     - Adicional [``res/ui/rpg_bindings.txt``](../../../res/ui/rpg_bindings.txt)
   * - Editor de mapas
     - Independiente [``res/ui/editor_bindings.txt``](../../../res/ui/editor_bindings.txt)



Archivos de modo
~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modo
     - Archivo
   * - Mundial
     - ``global_bindings.txt``
   * - Selección de unidad
     - ``unit_bindings.txt``
   * - Selección de edificio
     - ``building_bindings.txt``
   * - Comandos
     - ``command_bindings.txt``
   * - Habilidades
     - ``skill_bindings.txt``
   * - Primera persona (RPG)
     - ``rpg_bindings.txt``
   * - Ayuda y consulta
     - ``help_bindings.txt``
   * - Exploración del mapa
     - ``map_bindings.txt``
   * - Diplomacia
     - ``diplomacy_bindings.txt``




----


3. Cambio de modo (teclas F y ESC)
----------------------------------



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   *-F1
     - Selección de unidad ↔ Selección de edificio
   *-F2
     - Comandos ↔ Habilidades
   *-F3
     - Inventario ↔ Equipo (se requiere una única unidad amiga; consulte [inventory-and-equipment.md](inventory-and-equipment.htm))
   *-F4
     - Ingrese ayuda y consulta (presione nuevamente o Esc para salir)
   *-F12
     - Ingrese a diplomacia (presione nuevamente o Esc para salir)
   *-ESC
     - Cancelar orden / salir de la subpantalla; De lo contrario, ingrese al mapa y explore



Al cambiar a modos sin mapa se anuncia el nombre del modo (por ejemplo, “selección de unidad”, “modo de comando”).

Comportamiento especial cuando ESC ingresa a la exploración del mapa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Acción
     - Voz
     - Estado interno
   * - ESC → mapa
     - Siempre anuncia "exploración de mapa" + descripción general del cuadrado actual
     - Si se seleccionó anteriormente un depósito/prado/pasaje, se restaura silenciosamente `interface.target`
   * - ``f`` / ``g`` / ``m`` / ``p`` en el mapa
     - Anuncia el elemento como de costumbre.
     - Guarda la selección para restaurar después de abandonar el mapa.



Ejemplo: en el modo mapa, ``f`` selecciona una mina de oro → F1 al modo unidad, selecciona un campesino → ESC regresa al mapa → escuchas “explorar mapa, 8, 13, 1 ayuntamiento…” (descripción general del cuadrado), no la mina nuevamente; El foco permanece en la mina, por lo que puedes presionar Enter para enviar la orden de recolección inmediatamente.

Al salir del modo de mapa se guarda el foco del mapa actual mediante ``save_map_browse_target``.


----


4. Teclas de acceso rápido globales
-----------------------------------


Siempre activo en todos los modos (``global_bindings.txt``).

Recursos y población
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``z``
     - Estado del recurso 1
   * - ``x``
     - Estado del recurso 2
   * - ``SHIFT Z``
     - Estado del recurso 3
   * - ``c``
     - Estado de la población



Entrada rápida (heredada)
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``ALT V``
     - Pantalla de atributos
   * - ``SHIFT V``
     - Inventario
   * - ``CTRL V``
     - Equipo



Selección de objetivos
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``TAB`` / ``SHIFT TAB``
     - Objetivo siguiente/anterior
   * - ``CTRL TAB`` / ``CTRL SHIFT TAB``
     - Objetivo útil siguiente/anterior



movimiento
~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - Teclas de flecha
     - Mover 1 casilla
   * - ``SHIFT`` + flechas
     - Mover 5 casillas
   * - ``CTRL`` + flechas
     - Mover 1 casilla (sin colisión)
   * - ``CTRL SHIFT`` + flechas
     - Mover 5 casillas (sin colisión)



Saltos cuadrados
~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``PAGE DOWN`` / ``PAGE UP``
     - Cuadrado explorado siguiente/anterior
   * - ``CTRL PAGE DOWN`` / ``CTRL PAGE UP``
     - Cuadrados de conflicto
   * - ``ALT PAGE DOWN`` / ``ALT PAGE UP``
     - Cuadrados desconocidos
   * - ``SHIFT PAGE DOWN`` / ``SHIFT PAGE UP``
     - Cuadrados de recursos



Comando predeterminado y confirmación
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``BACKSPACE``
     - Comando predeterminado
   * - ``SHIFT BACKSPACE``
     - Comando predeterminado (cola)
   * - ``CTRL BACKSPACE``
     - Comando predeterminado (imperativo)
   * - ``RETURN`` / teclado ``ENTER``
     - Validar pedido
   * - Con ``SHIFT`` / ``CTRL``
     - Cola / variantes imperativas



Observación y consulta
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``LCTRL`` / ``RCTRL``
     - Examinar
   * - ``SPACE``
     - Estado de la unidad
   * - ``v``
     - Puntos de vida
   * - ``F9`` / ``SHIFT F9``
     - Objetivos
   * - ``F11``
     - Lista de jugadores



Sistema
~~~~~~~



.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``F5`` / ``F6``
     - Historia anterior/siguiente
   * - ``F10`` / ``CTRL C`` / ``ALT F4``
     - Menú de juego
   * - ``HOME`` / ``END`` etc.
     - Volumen
   * - ``ALT SPACE`` / ``CTRL SPACE``
     - Modo en primera persona
   * - ``CTRL F2``
     - Alternar pantalla
   * - ``CTRL F3``
     - Alternar reloj parlante
   * - ``CTRL SHIFT F4``
     - Cambiar la vista del jugador
   * - ``ALT M``etc.
     - Volumen de la música




----


5. Teclas de acceso rápido por interfaz
---------------------------------------


5.1 Selección de unidad
~~~~~~~~~~~~~~~~~~~~~~~


Archivo: ``unit_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Categoría
     - llaves
     - Notas
   * - Lote de soldados
     - ``a``
     - Todos los locales; ``CTRL a`` en todo el mapa
   * - Unidad de ciclo
     - ``q`` / ``SHIFT q``
     - Locales; ``CTRL q`` en todo el mapa
   * - Acceso directo a pedidos
     - ``b``
     - Utiliza ``shortcut`` de pedidos de style.txt
   * - Filtros
     - ``m`` / ``n``
     - Lado/tipo al elegir objetivos
   * - Trabajadores
     - ``s`` lote / ``w`` ciclo
     - Antiguas llaves ``d``/``e``
   * - Soldados 1 a 7
     - `d/e` … `;/p`
     - Misma región clave que los edificios.
   * - Grupos
     - ``1``–`5` configurado, `6`–`9` recuperar
     - ``CTRL`` para grupos de todo el mapa



El modo de unidad puede anular ``BACKSPACE`` localmente.

5.2 Selección de edificio
~~~~~~~~~~~~~~~~~~~~~~~~~


Archivo: ``building_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Fila de claves
     - Mapas para
   * - ``d f g h j k l ;``
     - edificio1 – edificio8
   * - ``e r t y u i o p``
     - edificio9 – edificio16



Por clave: seleccione el tipo local; ``SHIFT`` + ciclos de tecla uno; ``CTRL`` La tecla + selecciona todo el mapa.

Configuración de mod: establezca ``keyboard building1``… ``keyboard building16`` en ``style.txt`` (junto con el genérico ``keyboard building``). Ejemplo de campaña base: ayuntamiento→edificio1, casa→edificio2.

5.3 Modo de comando
~~~~~~~~~~~~~~~~~~~


Archivo: ``command_bindings.txt``

.. list-table::
   :header-rows: 1

   * - Ranura
     - llaves
   * - Navegar
     - ``a`` / ``SHIFT a``
   * - 1–9
     - `s d f g h j k l ;`
   * - 10–18
     - ``w e r t y u i o p``
   * - 19–30
     - ``1``–`0` `-` `=`
   * - Repetir
     - ``ALT x`` / ``ALT z``



Las ranuras siguen el orden del menú de la unidad; Las claves adicionales dicen "ninguno" si existen menos de 30 pedidos.

5.4 Modo de habilidad
~~~~~~~~~~~~~~~~~~~~~


Archivo: ``skill_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``a`` / ``SHIFT a``
     - Explorar el menú de habilidades (siguiente / anterior)



5.5 Modo primera persona (RPG)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Cuando ingresa al modo de primera persona (global ``ALT SPACE``), ``rpg_bindings.txt`` se superpone a los enlaces de interfaz actuales.


.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - `1`–`9`
     - Habilidades 1 a 9
   * - ``0``
     - Habilidad 10
   * - `-` / `=`
     - Habilidades 11 / 12
   * - ``ALT /``
     - Lista de habilidades
   * - ``CTRL A``
     - Ataque automático
   * - ``CTRL F8`` / ``SHIFT F8`` / ``ALT F8``
     - Zoom de precisión hacia arriba / abajo / consulta



Las teclas de dirección y ``SHIFT`` + teclas de dirección se mueven y giran en primera persona (ver comentarios del archivo).

5.6 Exploración del mapa
~~~~~~~~~~~~~~~~~~~~~~~~


Archivo: ``map_bindings.txt``

El movimiento y los saltos cuadrados son globales (sección 4).

Estas teclas ciclan objetivos en el cuadrado actual (sin cambio de cuadrado):


.. list-table::
   :header-rows: 1

   * - Clave
     - Acción
   * - ``f`` / ``r``
     - depósito de recurso1 (por ejemplo, oro)
   * - ``g`` / ``t``
     - depósito de recursos2 (por ejemplo, madera)
   * - ``y`` / ``h``
     - depósito de recursos3 (por ejemplo, alimentos)
   * - ``m`` / ``SHIFT m``
     - pradera
   * - ``p`` / ``SHIFT p``
     - Pasaje / puente
   * - Serie ``F8``
     - Ampliar



Después de seleccionar un depósito, use global ``BACKSPACE`` / ``RETURN`` para emitir el cobro; prado para construir; pasaje para mover/bloquear.

5.7 Ayuda y diplomacia
~~~~~~~~~~~~~~~~~~~~~~


Ayuda (`help_bindings.txt <../../../res/ui/help_bindings.txt>`_): ``1``/``2`` buscar ayuda, ``3`` decir la hora, ``F7`` decir, ``CTRL SHIFT F3`` alternar la visualización de marcas.

Diplomacia (`diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_): ``1`` seleccionar candidato, ``q`` solicitar, ``w`` aceptar, ``e`` rechazar/cancelar.

``ESC`` en modos de superposición llama a ``exit_overlay_mode``.


----


6. Flujos de trabajo típicos
----------------------------


reunión
~~~~~~~


1. Modo unidad: ``s`` seleccionar campesino
2. ``F2`` modo de comando, ``s`` seleccionar recopilación (o ``b`` + método abreviado de letra)
3. ``ESC`` exploración de mapas
4. ``f`` seleccionar mina de oro (anunciada)
5. ``RETURN`` para confirmar

Si ya seleccionó una mina y dejó el mapa: ``ESC`` atrás anuncia una descripción general del cuadrado; el foco permanece en la mina: presione ``RETURN`` directamente.

edificio
~~~~~~~~


1. ``ESC`` mapa → ``m`` seleccionar prado
2. ``F2`` elige la ranura de construcción
3. ``RETURN`` confirmar

Diplomacia
~~~~~~~~~~


1. ``F12`` diplomacia
2. `1` seleccionar candidato
3. ``q`` solicitud de alianza

.. code-block:: text

   sequenceDiagram
       participant U as UnitMode
       participant C as CommandMode
       participant M as MapMode
       U->>U: s select peasant
       U->>C: F2
       C->>C: s order slot 1
       C->>M: ESC
       M->>M: f select mine
       M->>C: RETURN validate




----


7. Personalización para modificaciones.
---------------------------------------


Que archivo editar
~~~~~~~~~~~~~~~~~~


- Comportamiento global: ``global_bindings.txt``
- Una interfaz: la correspondiente `*_bindings.txt`
- No edite el cuerpo de ``bindings.txt`` (solo fragmento) a menos que comprenda el comportamiento de adición del mod heredado

Modificadores
~~~~~~~~~~~~~

- Permitidos: ``CTRL``, ``ALT``, ``SHIFT`` (cualquier lado), ``LSHIFT``, ``RSHIFT`` (más teclas standalone como ``LALT`` / ``RALT``).
- No ponga ``LSHIFT``/``RSHIFT`` y ``SHIFT`` en la misma línea; la búsqueda prefiere el lado concreto y luego el ``SHIFT`` genérico.

Anulaciones de usuario
~~~~~~~~~~~~~~~~~~~~~~


Mapeo en el juego (recomendado): Menú principal → Opciones → Mapeo de teclas (hermano del esquema de teclas de acceso rápido). Admite esquemas clásicos y en capas, todas las capas, búsqueda, variantes, claves de alias e importación/exportación del portapapeles. Las configuraciones se almacenan por mod en ``user/hotkey_overrides/{mod_key}.json`` y se aplican en el siguiente juego. Consulte `developer: hotkey mapping editor <../../mod/hotkey-mapping-editor.htm>`_.

Esquema de teclas de acceso rápido: Opciones → El esquema de teclas de acceso rápido cambia en capas/clásico; Al mover la selección se anuncia activo o inactivo para el esquema actual.

Archivo manual: agregue o anule claves en ``cfg/bindings.txt``; cargado por última vez (todavía agregado después de las anulaciones basadas en JSON).

Notas
~~~~~


- Las ranuras ``select_order_index`` dependen del orden del menú
- Las ranuras ``buildingN`` necesitan ``keyboard buildingN`` en ``style.txt``
- La unidad ``b`` (``order_shortcut``) utiliza el ``shortcut`` de cada orden con estilo


----

8. Teclas de acceso rápido clásicas de un solo archivo
------------------------------------------------------


Para restaurar el conjunto de enlaces anterior a 1.4.3 (solicitud de alianza F4, candidato de alianza F12, ESC sin modo de exploración de mapa, etc.):

Opción A (recomendada): Menú principal → Opciones → Esquema de teclas de acceso rápido, luego elija Teclas de acceso rápido en capas o Teclas de acceso rápido clásicas.

Opción B (editar ini manualmente):

1. Abra :strong:```user/SoundRTS.ini`` (often `%APPDATA%\SoundRTS\SoundRTS.ini` en Windows).
2. En `````[general]```, agregue o configure:

.. code-block:: ini

      layered_hotkeys = 0



3. Reinicia el juego (debe configurarse antes de que comience el partido).

Cuando está deshabilitado:

- Solo se carga `res/ui/legacy_bindings.txt <../../../res/ui/legacy_bindings.txt>`_, no ``global_bindings.txt`` ni capas por modo.
- Mod no stub ``bindings.txt`` y ``user/bindings.txt`` todavía están agregados (el usuario anula la victoria).
- Los comandos de cambio de modo F1/F2/F3/F4/F12/ESC emiten un pitido; ESC cancela órdenes/sale de las subpantallas/sale de la inmersión o el zoom y no ingresa al modo de exploración de mapas.
- Inventario (``i``), equipo (``u``), atributos (Alt+V), etc. siguen ``legacy_bindings.txt``.

Para volver a habilitar el modo en capas: configure ``layered_hotkeys = 1`` (o elimine la línea; el valor predeterminado es 1) y reinicie.


----


9. Diferencias con el antiguo esquema.
--------------------------------------



.. list-table::
   :header-rows: 1

   * - viejo
     - Nuevo
   * - Ayuda directa F1/F4
     - F4 ingresa al modo de ayuda; F9/F11 globalizado
   * - Diplomacia directa F12
     - F12 entra primero en modo diplomacia
   * - Trabajador ``d``/``e``
     - Modo unidad ``s``/``w``
   * - Llaves de soldado
     - Reasignado a `d/e`…`;`/p`
   * - Mapa ``f`` cuadrados saltados
     - ``f`` ciclos de depósitos en el cuadrado actual
   * - ESC para mapear el último objetivo anunciado
     - ESC anuncia descripción general de la plaza; enfoque restaurado silenciosamente



Los atributos y enlaces del editor no se modifican.


----


Archivos fuente relacionados
----------------------------


- `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_
- `res/ui/unit_bindings.txt <../../../res/ui/unit_bindings.txt>`_
- `res/ui/building_bindings.txt <../../../res/ui/building_bindings.txt>`_
- `res/ui/command_bindings.txt <../../../res/ui/command_bindings.txt>`_
- `res/ui/skill_bindings.txt <../../../res/ui/skill_bindings.txt>`_
- `res/ui/map_bindings.txt <../../../res/ui/map_bindings.txt>`_
- `res/ui/help_bindings.txt <../../../res/ui/help_bindings.txt>`_
- `res/ui/diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_
- `soundrts/clientgame/interface_modes.py <../../../soundrts/clientgame/interface_modes.py>`_