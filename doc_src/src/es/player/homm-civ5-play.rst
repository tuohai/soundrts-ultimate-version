Instrucciones de juego de Heroes and Civilization 5
===================================================


A partir de SoundRTS 1.4.3.4, Random Map (RMG) introduce objetivos de mapa, puntos de interés (POI) y varias condiciones de victoria inspiradas en "Heroes of Might and Magic" (HoMM) y "Civ5" (Civ5) en el esqueleto clásico de RTS. Este documento explica la comparación de diseño, las operaciones del jugador y los métodos de extensión de mod/desarrollador de estos juegos.

Consulta `Mapas aleatorios (jugador) <random-map-play.htm>`_ para obtener instrucciones generales sobre menús de mapas aleatorios, semillas y códigos para compartir.

----


1. Concepto de diseño: qué se puede jugar en RTS
------------------------------------------------


SoundRTS sigue siendo una estrategia en tiempo real: selecciona unidades, da órdenes, reúne, construye tropas y participa en la batalla. Los elementos de HoMM/Civ5 se reflejan principalmente en la generación de mapas y activan las condiciones de victoria, en lugar de un sistema completo por turnos o un árbol de tecnología.

.. list-table::
   :header-rows: 1

   * - fuente de inspiración
     - Correspondencia en SoundRTS
     - Ubicación del implemento
   * - Exploración de mapas HoMM, recompensas de ruinas.
     - Envía unidades a la plaza → Anuncia "Las ruinas han sido descubiertas" → Obtén monedas de oro/madera
     - ``ancient_ruin`` + ``has_entered`` disparador
   * - Guarida de criatura neutral HoMM / fortaleza capturable
     - Limpiar guardias → capturar los cuarteles con unidades ``can_capture 1`` (o atacar hasta el umbral)
     - ``captured_barracks`` + ``capture_hp_threshold`` + unidad ``can_capture``
   * - Defensa central HoMM, mapa simétrico
     - Coloca a los defensores enemigos escalados por fuerza en el centro del mapa (y puntos espejo)
     - ``MONSTER_PRESETS`` + ``\_append_creep``
   * - Civ5 múltiples formas de ganar
     - Conquista/Economía/Exploración/Supervivencia Cuatro modos de victoria RMG
     - `RandomMapConfig.victory_mode`
   * - Civ5 Explora todo el mapa y gana con recursos
     - Modo de exploración: descubre todas las ruinas de tu propio lado; Modo económico: Acumular recaudación para llegar a la meta
     - ``\_victory_mode_trigger_lines``
   * - Supervivencia de Civ5 y presión del tiempo
     - Modo de supervivencia: espera hasta la cuenta regresiva y mantén la base principal (``personal_victory``)
     - ``timer`` + `(personal_victory)`
   * - Cofre de mapas Civ5/Lujo
     - Opción "Cofre del tesoro": artículos de recogida colocados simétricamente o puntos minerales adicionales
     - ``\_append_treasure``
   * - Rama ciudad-estado de Civ5 (campaña)
     - Entregar artículos a NPC a cambio de recursos (no RMG, pertenece al guión de campaña)
     - Ejemplo: `res/single/The Legend of Raynor/`



Contenido que no ha sido implementado y es sólo para futura expansión (no incluido en el RMG actual):
- Mejoras de unidades de héroe, árboles de habilidades, sistema de maná (núcleo HoMM)
- Árbol de tecnología, cultura, puntos de diplomacia (núcleo de Civ5)
- Expansión urbana, producción de suelo, tarjetas de políticas.

----


2. Guía del jugador
-------------------


2.1 Cómo habilitar~~~~~~~~~~~~


1. Menú principal → Iniciar juego → Mapa aleatorio
2. Presione el menú para configurar paso a paso, o pegue la configuración completa en Plantilla de mapa → Importar código compartido (admite pegar Ctrl+V)
3. Selecciona el modo de juego en el paso Modo Victoria (el valor predeterminado es Conquista)
4. Confirmar el tratado de alto el fuego y generar el mapa.
Modo de exploración Después de hacer clic en "Iniciar" para ingresar al juego, primero se reproducirá la sesión informativa de la misión inicial (información de la misión + oración variante aleatoria + objetivo de exploración) y luego comenzará la operación. El contenido del resumen está determinado por la semilla del mapa y se puede reproducir con el mismo código compartido.
En línea: se selecciona un mapa aleatorio de la lista de mapas al construir una casa, que el anfitrión genera a partir de la misma semilla al comienzo del juego; el cliente no transmitirá automáticamente el código compartido y el código compartido debe intercambiarse con anticipación.
2.2 Cuatro modos de victoria~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - modelo
     - Identificación de voz
     - Condiciones de victoria
     - Condiciones de falla (igual que otros modos)
   * - Conquistar
     - 5426
     - Destruye a todos los jugadores enemigos (no es necesario eliminar el monstruo central)
     - Pierde todos los edificios ``provides_survival``
   * - economía
     - 5427
     - La colección acumulada alcanza las monedas de oro objetivo (excluyendo las traídas al principio; el gasto seguirá contando)
     - Igual que arriba
   * - explorar
     - 5428
-Visita todas las ruinas antiguas en persona.
     - Igual que arriba
   * - Sobrevivir
     - 5429
     - Aguanta hasta el final de los tiempos y mantén tu base principal.
     - Igual que arriba



Vista previa de la configuración: el modo Económico también transmitirá un objetivo de oro específico (como "Economía...3000 de oro").
Modo económico objetivo monedas de oro (solo ``resource1``, es decir, monedas de oro):

.. list-table::
   :header-rows: 1

   * - plantilla de mapa
     - Objetivo
   * - rápido
     - 2000
   * - estándar
     - 3000
   * - Macro
     - 5000
   * - pasillo
     - 2500



Duración del modo de supervivencia:

.. list-table::
   :header-rows: 1

   * - plantilla de mapa
     - Duración
   * - rápido
     - 10 minutos
   * - Estándar / Macro / Canal
     - 15 minutos




Nota: En los modos de exploración, economía y supervivencia, la victoria automática no se logrará "aniquilando a todos los enemigos" (se ha eliminado `(no_enemy_player_left) (victory)`); sin embargo, aún puedes atacar y debilitar activamente a tus oponentes. Perder la base principal (centro de la ciudad, etc. edificios ``provides_survival 1``) seguirá fallando.
2.3 Puntos de interés del mapa (POI)~~~~~~~~~~~~~~~~~~~~~


Todos los mapas RMG (siempre que el tipo de unidad correspondiente esté definido en ``rules.txt``) generarán los siguientes puntos de interés, independientemente del modo de victoria:
Ruinas antiguas (``ancient_ruin``)^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Función: Se activa cuando tu unidad ingresa a esta casilla por primera vez (no es necesario atacar el edificio)
- Recompensa del Acto 1: Transmitir que se han descubierto las ruinas (5433) y obtener recursos
- Plantilla rápida: 300 de oro + 150 de madera
- Otras plantillas: 500 de oro + 250 de madera
- Acto 2 (cuadrados adyacentes): Después de descubrir las ruinas, se te pedirá que escuches un sonido metálico detrás del muro de piedra, revisa los cuadrados adyacentes (5490). Si hay una cuadrícula adyacente disponible al lado de las ruinas, enviar unidades a la cuadrícula adyacente puede obtener ganancias adicionales (5491) y recursos adicionales en las profundidades (aproximadamente el 50% del primer acto: rápido +150 oro / +75 madera, otros +250 oro / +125 madera). El acto 2 se omite cuando las celdas adyacentes no están disponibles (bordes, puntos de generación, etc.).
- Transmisión del progreso de la exploración (solo en el modo Exploración Victoria): transmisión después de descubrir ruinas. Ruinas no descubiertas: N o solo quedan las últimas ruinas (5492/5493).
- Victoria de exploración: debes enviar unidades personalmente a cada ruina (2 contra 2 incluye el recuento combinado de compañeros de equipo que han entrado en cada ruina). Las ruinas que el enemigo u oponente haya explorado primero no contarán para tu progreso, pero aun así podrás ingresar y completar el descubrimiento más tarde; La recompensa de recursos cuando ingresas a una ruina por primera vez en todo el mapa solo se otorga una vez (sin importar quién llegue primero).
- Cantidad (colocados en pares simétricos, el número real de puntos de activación es 2×pares):
- Miniatura: 1 par (modo exploración +1 par)
- Mediano/Grande: 2 pares (modo exploración +1 par)
Capaz de ocupar cuarteles (``captured_barracks``)^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Guardia: 2 infantería + 1 arquero en la plaza (ordenador hostil, no neutral)
- Ocupar: después de eliminar a los guardias, deja que la unidad ``can_capture 1`` haga clic derecho en el cuartel (o ataque hasta el umbral de captura); cuando el objetivo ``capture_hp_threshold`` sea 100, será ocupado una vez que esté en su lugar, sin causar daños. Las unidades configuradas en ``can_capture 0`` solo pueden atacar normalmente y no recibirán órdenes de captura de forma predeterminada.
- Después de la ocupación: Informe de ocupación del cuartel (5434); Se puede entrenar infantería (máximo 5) y arqueros (máximo 3).
- Cuando no esté ocupado: 2 infantería serán reforzadas en aproximadamente 5 a 10 minutos (hasta que esté ocupado)
- Cantidad: 1 par de cuadros pequeños; 2 pares de fotografías medianas/grandes; +1 par adicional en modo exploración
Guarnición central (fuerza de monstruos)^^^^^^^^^^^^^^^^^^^^


Menú Monster Strength Controla el tamaño de los defensores en el centro del mapa (estilo HoMM "zona de peligro en el centro del mapa"):

.. list-table::
   :header-rows: 1

   * - Fortaleza
     - guarnición
   * - débil
     - 2 infantería
   * - medio
     - 4 infantería + 2 arqueros
   * - poderoso
     - 6 Infantería + 4 Arqueros + 1 Caballero



Los defensores atacarán activamente a los jugadores que entren en el rango; plantillas como fast/passage ajustarán el número hasta ``creep_multiplier``.
Cofre del tesoro (opcional)^^^^^^^^^^^^


Los elementos del menú del Cofre del Tesoro son Ninguno/Menos/Más:
- Menos: Simétrica 1 mina de oro adicional (alrededor de 500)
- Múltiple: 2 plazas; alrededor del 45% de probabilidad de ser artículos recolectables (``class item``), alrededor del 35% de ellos son huertos y el resto son minas de oro (alrededor de 900)
La definición de elementos seleccionables para ``class item`` debe existir en el ``rules.txt`` actual.
2.4 Coordenadas y habilidades de exploración.~~~~~~~~~~~~~~~~~~


- Las coordenadas de la cuadrícula en el mapa y el menú se basan en 1 (la esquina inferior izquierda es `1,1`)
- Cuando explores ruinas, simplemente mueve la unidad a la cuadrícula donde se encuentran las ruinas; no hay necesidad de seleccionar las ruinas o atacar
- Las ruinas no desaparecerán después de ser "descubiertas", pero la recompensa solo se emitirá una vez.
- Presione F5 / F6 para escuchar mensajes de voz históricos como "Mapa generado, semillas, códigos compartidos", etc.
2.5 Campo de modo de victoria en código compartido~~~~~~~~~~~~~~~~~~~~~~~~~~


El código compartido completo tiene 12 segmentos (incluido el prefijo ``RMG1``) y el undécimo segmento es el modo de victoria:
.. code-block:: text

RMG1:Plantilla:Dimensiones:Número de personas:Monstruos:Recursos:Terreno:Equipo:Agua:Cofre del tesoro:Victoria:Semilla


Abreviatura del modo victoria:

.. list-table::
   :header-rows: 1

   * - abreviatura
     - modelo
   * - ``c``
     - conquistar conquista
   * - ``e``
     - económico
   * - ``x``
     - exploración
   * - ``s``
     - supervivencia



Ejemplo (pasaje, miniatura, 2 personas, exploración, cofre alto, semilla 6685):
.. code-block:: text

   RMG1:l:s:2:w:b:r:f:n:hi:x:6685


La versión anterior del código compartido de 10 segmentos (sin campo de victoria) tiene como valor predeterminado Conquest después de la importación.

----


3. Definición de reglas y datos (``res/rules.txt``)
---------------------------------------------------


Las unidades de puntos de interés se definen cerca del final de las reglas básicas (las notas indican inspiración HoMM/Civ5):
.. code-block:: text

   def ancient_ruin
   class building
   cost 0 0
   time_cost 0
   hp_max 200
   hp_regen 0
capture_hp_threshold 0; No se puede capturar, solo se usa como marcador de mapa.
   provides_survival 0
   is_buildable_anywhere 0
   sight_range 1
   
   def captured_barracks
   class building
   cost 0 0
   time_cost 0
   hp_max 500
   hp_regen 0.1
capture_hp_threshold 100; Se puede capturar cuando HP ≤100% (un ataque es suficiente)
   provides_survival 0
   is_buildable_anywhere 0
   can_train footman 5 archer 3
   population_provided 0


Descripción del campo clave~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - campo
     - Reliquias
     - Cuartel
   * - ``capture_hp_threshold``
     - ``0`` = Incapturable
     - `100` = Puede ser capturado (capturado al contacto)
   * - ``can_capture``
     - — (escrito en la unidad atacante)
     - Predeterminado `1`; `0` = Clic derecho/AI no ocupa esta unidad de forma predeterminada
   * - ``provides_survival``
     - ``0`` = La pérdida no afecta el juicio de "todavía hay edificios"
     - igual que a la izquierda
   * - ``can_train``
     - ninguno
     - Las unidades que se pueden producir después de la ocupación y el límite superior.
   * - ``sight_range 1``
     - Campo de visión bajo; el motor puede registrar INFORMACIÓN en ``sight_range 1``, que puede ignorarse
     - —



Si el módulo elimina o cambia el nombre de estos ``type_name``, RMG omitirá la generación de PDI correspondiente hasta ``\_rules_has_type()`` sin informar un error.

----


4. Generador de mapas aleatorios (desarrollador)
------------------------------------------------


Código fuente principal: ``soundrts/randommap.py``
Menú:``soundrts/randommap_menu.py``
Prueba:``soundrts/tests/test_randommap.py``
4.1 Descripción general del proceso de generación~~~~~~~~~~~~~~~~


.. code-block:: text

   RandomMapConfig
       → generate_definition() / _generate_grid_definition() / _generate_lanes_definition()
→ Terreno, recursos, aguas, cofres del tesoro.
→ _append_hunting (fauna silvestre)
→ Bloque de nacimiento del jugador
→ _append_creep (guarnición central)
→ _append_exploration_poi (reliquia + activador has_entered)
→ _append_capturable_dwelling (cuartel + refuerzo/activador de captura)
→ _append_skirmish_triggers (ganar/fallar)
→ Salida de cadena de mapa .txt → Mapa/Mundo se carga normalmente


La posición del PDI se selecciona aleatoria y simétricamente mediante ``\_symmetric_pairs()`` de las cuadrículas candidatas que evitan el punto de nacimiento y el punto de nacimiento espejo para garantizar la equidad.
4.2 Explorar plantillas de activación generadas por PDI~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


``\_append_exploration_poi()`` Para cada reliquia escribe:
.. code-block:: text

   computer_only 0 0 neutral 8,2 1 ancient_ruin
   trigger players (has_entered 8,2) (if (not (rmg_ruin_discovered_by_self rmg_ruin_0)) (do (rmg_mark_ruin_discovered rmg_ruin_0) (if (not (map_flag rmg_ruin_0_reward)) (do (set_map_flag rmg_ruin_0_reward) (cut_scene 5433) (grant_resources 500 resource1 250 resource2))) (cut_scene 5490)))


- Las coordenadas `8,2` son base 1; ``has_entered`` se convertirá a base 0 en ``triggers.py`` Clave de cuadrícula
- Importante: en mapas estrechos, como pasajes, las coordenadas de base 1 pueden "chocar" con la clave de la cuadrícula de base 0; El análisis de activación debe realizarse primero mediante la conversión de 1 base y la cuadrícula no se puede verificar directamente (de lo contrario, las ruinas no se pueden activar)
4.3 Plantilla de activación de cuarteles capturables~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   computer_only 0 0 8,3 1 captured_barracks 2 footman 1 archer
   trigger computerN (timer 5 5) (if (and (not (map_flag rmg_dwelling_8_3)) (unit_lost 8,3 1 captured_barracks)) (do (set_map_flag rmg_dwelling_8_3) (cut_scene 5434)))
   trigger computerN (timer 300 600) (if (and (not (map_flag rmg_dwelling_8_3)) (not (unit_lost 8,3 1 captured_barracks))) (add_units 8,3 2 footman))


- Lo mejor es usar ordenadores en casillas ``computer_only`` hostiles (con guardias).
- Para determinar la ocupación, usa `(unit_lost casilla 1 captured_barracks)` (edificio capturado/reemplazado), no el método obsoleto ``transfer_units player1``.

4.4 Activador del modo victoria
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - modelo
     - Generar lógica
   * - economía
     - Verifique ``(has_gathered objetivo resource1)`` → `` (victory)`` cada 60 segundos (colección acumulada, excluyendo el inicio)
   * - Sobrevivir
     - ``(timer <segundos>) (if (not (no_building_left)) (personal_victory))`` (varias personas pueden ganar a la vez)
   * - explorar
     - Verifique ``(rmg_all_ruins_discovered_by_allies rmg_ruin_0 …)`` → `` (victory)`` cada 30 segundos
   * - Conquistar
     - ``(no_enemy_player_left) (victory)`` (solo modo Conquista; solo se cuentan los jugadores enemigos)



Condiciones de falla comunes (todos los modos):
.. code-block:: text

   trigger players (no_building_left) (defeat)
   trigger computers (no_unit_left) (defeat)


4.5 Pasos recomendados para ampliar los tipos de puntos de interés
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Tomemos como ejemplo añadir un «santuario»:

1. **rules.txt**: define el tipo (hereda terreno, deja marca o marcado puro)
2. **``res/ui/tts.txt``** (y ``ui-xx``): asigna una nueva ID de voz (evita conflictos con 5425–5441 RMG)
3. **Añade** constantes ``RMG_*``
4. **``randommap.py``**:
   - Añade ``_append_shrine_poi()``, modelado a partir de ``_append_exploration_poi``
   - Llámalo en ``_generate_*_definition``
   - Si está vinculado a la victoria de exploración, devuelve la lista de banderas y pásala a ``_victory_mode_trigger_lines``
5. Si necesitas nuevos elementos de menú, amplía las opciones de plantilla
6. Actualiza ``encode_share_code`` / ``decode_share_code`` si hay un campo nuevo
7. Prueba: afirma el texto generado con los activadores esperados en ``test_randommap.py``

4.6 API de activación relacionada
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - desencadenar
     - Objetivo
   * - ``(has_entered casilla [tipo_unidad…])``
     - Las unidades del jugador entran en la casilla.
   * - ``(has_gathered cantidad resource1)``
     - Victoria económica: recaudación acumulada (excluyendo las que vienen con el inicio)
   * - ``(has_resources cantidad resource1)``
     - Verificar el stock de recursos actual (victoria económica no RMG)
   * - ``(rmg_mark_ruin_discovered nombre)``
     - Marcar que el jugador actual ha descubierto las ruinas (progreso de victoria)
   * - ``(rmg_ruin_discovered_by_self nombre)``
     - Condición: Si el jugador actual ha descubierto las ruinas.
   * - ``(rmg_all_ruins_discovered_by_allies nombre…)``
     - Victoria de exploración: si tu campamento ha encontrado todas las reliquias.
   * - ``(grant_resources 500 resource1 200 resource2)``
     - Recompensas de reliquias
   * - `(set_map_flag nombre)` / `(map_flag nombre)`
     - Marcadores del juego en el mapa.
   * - ``(cut_scene id_voz)``
     - Informe de descubrimiento/ocupación
   * - ``(unit_lost casilla índice tipo)``
     - Cuarteles ocupados
   * - ``(add_units casilla cantidad tipo)``
     - Refuerzos de los defensores.
   * - ``(timer intervalo [veces])``
     - Control periódico/cuenta atrás de supervivencia
   * - ``(personal_victory)``
     - Modo supervivencia: ganas sin eliminar a otros supervivientes.



Consulte ``soundrts/worldplayerbase/triggers.py`` para la implementación.

----


5. Redacción de voz y UI
------------------------



.. list-table::
   :header-rows: 1

   * - ID
     - Chino
     - Objetivo
   * - 5425
     - Modo victoria
     - Título del menú
   * - 5426
     - Conquista y aniquila a todos los jugadores enemigos.
     - nombre del patrón
   * - 5427
     - La recaudación económica y acumulativa alcanza el objetivo.
     - Nombre del modo (la vista previa se puede conectar a la cantidad específica de monedas de oro)
   * - 5428
     - Explora y visita todas las ruinas en persona.
     - nombre del patrón
   * - 5429
     - Sobrevive y aguanta hasta el fin de los tiempos.
     - nombre del patrón
   * - 5430
-Visita todas las ruinas antiguas en persona.
     - Fila objetivo del modo Explorar
   * - 5431
     - ruinas antiguas
     - Nombre de la unidad/concepto (reservado)
   * - 5432
     - Capaz de ocupar cuarteles.
     - Nombre de la unidad/concepto (reservado)
   * - 5433
     - Reliquias descubiertas
     - Entra en las ruinas cut_scene
   * - 5434
     - El cuartel ha sido capturado.
     - Ocupar cut_scene
   * - 5435
     - La recaudación acumulada alcanza
     - Línea objetivo del modelo económico (seguida de cantidad y "oro")
   * - 5436
     - Agárrate fuerte
     - Línea objetivo del modo de supervivencia.
   * - 5437
     - minuto
     - Línea objetivo del modo de supervivencia.
   * - 5451
     - Destruye a todos los jugadores enemigos.
     - Fila objetivo del modo Conquista
   * - 5452
     - y mantener la base principal
     - Sufijo de línea objetivo del modo de supervivencia



``objective`` Ejemplo de fila de mapa:
.. code-block:: text

objetivo 5430; explorar
objetivo 5435 3000 131; Economía: Recoge 3000 de oro en total.
objetivo 5436 15 5437 5452 ; Sobrevive 15 minutos y mantén la base principal.
objetivo 5451; conquistar



----


6. Pruebas y regresión
----------------------


``soundrts/tests/test_randommap.py`` Cubre:
- El modo de exploración genera ``ancient_ruin``, ``rmg_mark_ruin_discovered``, ``rmg_all_ruins_discovered_by_allies`` y ninguna conquista `(no_enemy_player_left) (victory)`
- El modo económico utiliza ``has_gathered``; el objetivo de supervivencia incluye `5452`; el objetivo de la conquista es `5451`
- El modo Economía/supervivencia también tiene victoria automática sin conquista.
- Los cuarteles usan guardias ``computer_only``, no ``neutral``
- `captured_barracks.capture_hp_threshold == 100`
- El código compartido contiene el campo de victoria `:e:` / `:x:` y otros análisis de ida y vuelta
Coordenada relacionada: ``soundrts/tests/test_yield_on_defeat_and_campaign_flags.py`` Mediana
``test_has_entered_one_based_coords_not_confused_with_zero_based_grid_key`` Evitar la regresión del error de coordenadas de ruinas del mapa de canales.

----


7. Limitaciones y precauciones conocidas
----------------------------------------


1. Modo de supervivencia AI: la computadora invitada todavía usa el estándar ``res/ai.txt`` y no hay un script dedicado para el "jugador de supervivencia en asedio".
2. ``computerN`` Ranura `: Cuando hay muchos PDI, se pueden asignar ID como . Si no hay suficientes jugadores de computadora reales, habrá una advertencia de "jugador desconocido" (no afecta los puntos de interés de los jugadores humanos)
3. Exploración ≠ Victoria de guerra: no ganarás si destruyes a todos los enemigos; tu propio campamento debe encontrar todas las reliquias (FFA solo cuenta si las descubres)
4. Victoria económica: acumulativo  (monedas de oro) recolectadashas_gatheredgrant_resources\_economic_goalgrant_resourcesresource1resource2Exploración + Ninguno : No se generarán puntos de interés cuando el módulo no define el tipo de ruina y no se puede ganar el modo de exploración.
8. Elementos de campaña Civ5: comerciantes de ciudades-estado, tareas de entrega, etc. Ver mapa de campaña y `Instrucciones para transportar artículos y entrega de tramas.md <Instrucciones para transportar artículos y entrega de tramas.htm>`_, independiente de RMG

----


8. Índice de documentos relacionados
------------------------------------



.. list-table::
   :header-rows: 1

   * - contenido
     - camino
   * - Jugador: menú de mapa aleatorio
     - [Descripción de función de mapa aleatorio.md](Descripción de función de mapa aleatorio.htm)
   * - Regla: unidad PDI
     - ``res/rules.txt`` （``ancient_ruin``、``captured_barracks``）
   * - generador
     - ``soundrts/randommap.py``
   * - menú
     - ``soundrts/randommap_menu.py``
   * - desencadenar
     - ``soundrts/worldplayerbase/triggers.py``
   * - lógica de captura
     - ``soundrts/combat/damage_effects.py`` (``capture_hp_threshold``); comando de captura predeterminado ``can_capture`` → ``worldunit/world_order.py``
   * - Constante del habla
     - ``soundrts/msgparts.py``
   * - Documentación HTML del juego
     - ``doc/zh/mod/randommap.htm``
   * - Mapa aleatorio en inglés
     - [../../en/player/random-map.md](../../en/player/random-map.htm)




----


9. Comparación rápida: ¿A cuál quiero jugar?
--------------------------------------------



.. list-table::
   :header-rows: 1

   * - Quiero experimentar…
     - Configuraciones recomendadas
   * - Exploración de mapas estilo HoMM para ganar premios
     - Modo victoria: exploración, muchos cofres del tesoro, monstruos medianos.
   * - Ampliación del campamento militar estilo HoMM
     - Cualquier modo de victoria está disponible; Encuéntralo primero y ocupa el cuartel.
   * - Victoria económica estilo Civ5
     - Economía en modo victoria, macro plantilla, concentración de recursos.
   * - Defensa al estilo Civ5 hasta el final.
     - Supervivencia en modo Victoria, plantilla rápida (10 minutos)
   * - Aniquilación clásica de estrategia en tiempo real
     - Conquista en modo victoria (predeterminado)




----


*Versión del documento: Corresponde a la implementación de mapas aleatorios SoundRTS 1.4.2.x; Si se cambia el campo del código compartido o el número de puntos de interés, prevalecerán ``soundrts/randommap.py`` y ``test_randommap.py``. *
