guía para hacer mapas
=====================

.. contents::

Introducción
------------

Probablemente la mejor manera de comenzar sea crear un mapa multijugador y probarlo en la computadora.

Mapas multijugador
------------------

Dónde almacenar un nuevo mapa multijugador
""""""""""""""""""""""""""""""""""""""""""

Si se le permite escribir en la carpeta donde está instalado SoundRTS (o prueba de SoundRTS),
luego podrás almacenar tu primer mapa multijugador en la carpeta "multi".

Si no se le permite escribir en la carpeta de archivos del programa porque trabaja en modo no administrador, puede almacenar su archivo de mapa de trabajo en el archivo "multi".
carpeta en "C:\\Documentos y configuraciones\\Su inicio de sesión\\Datos de programa\\SoundRTS". Esta carpeta se crea la primera vez que inicia SoundRTS, a menos que exista una carpeta de "usuario" cerca de soundrts.exe.
Otra solución es instalar SoundRTS en una carpeta donde puedas escribir y trabajar en la carpeta mencionada en el párrafo anterior.

Cómo editar un mapa
"""""""""""""""""""

Abra el archivo con un editor de texto.
Escriba en minúsculas, incluso si probablemente se ignorarán las mayúsculas y minúsculas de todos modos.

Cómo probar un mapa
"""""""""""""""""""

Para probar un mapa, inicie SoundRTS y vaya al menú de un jugador. Puedes jugar contra la computadora en mapas multijugador.
El mapa se recarga cada vez que inicias un juego, por lo que no necesitas reiniciar SoundRTS para probar las modificaciones.
Una combinación de teclas útil es Control Shift F2: si eres el único humano en el mapa, podrás examinar todo el mapa (sin niebla de guerra).

Cómo encontrar y eliminar un error
""""""""""""""""""""""""""""""""""

Si, cuando inicia el mapa, recibe un mensaje de "error de mapa" y regresa al menú, es posible que a veces encuentre información adicional (pero críptica) en "client.log" o en "server.log", generalmente en la carpeta "user/tmp".

Si aún no entiendes dónde está el error, no dudes en contactarme, directamente o en la lista de soundRTSChat.

Comentarios
"""""""""""

Las líneas que comienzan con punto y coma son comentarios. Los comentarios se ignoran en tiempo de ejecución.
Todo lo que va después de un punto y coma hasta el final de la línea también es un comentario.

Propiedades básicas
"""""""""""""""""""

Título
''''''

"título 4018 5000" significa: "el título del mapa es el sonido 4018 seguido del sonido 5000".

Objetivo
''''''''

"objetivo 145 88" significa: "el objetivo del mapa es el sonido 145 seguido del sonido 88".

Nb_players_min y nb_players_max
'''''''''''''''''''''''''''''''

"nb_players_min 2" significa: "Se necesitan 2 jugadores para comenzar el juego".
"nb_players_max 4" significa: "4 jugadores en este mapa es un máximo".

Límite_comida_global
''''''''''''''''''''

Nuevo en la versión beta 9e.

Actualización en la versión beta 10 o: este límite de comida ya no se divide entre los jugadores.

"global_food_limit 200" significa: "Cada jugador no puede tener más de 200 alimentos, incluso si construye más granjas".

Definiendo el terreno
"""""""""""""""""""""

Coordenadas (desde 1.4.1.8)
'''''''''''''''''''''''''''

El sistema de coordenadas utiliza ``x,y`` (por ejemplo, ``1,1`` para el antiguo ``a1``). En modo zoom, coordenadas
are still announced with letters. Legacy notation is accepted and converted::

    west_east_paths 1,3 2,3
    south_north_paths 1,1 2,1 3,1

Utilice la notación x,y para definir más de 26 columnas.

Ancho_cuadrado
''''''''''''''

"square_width 12" significa: "el ancho del cuadrado es de 12 metros".
No debes modificar este parámetro, ya que los objetos pueden ser inaudibles si están demasiado lejos.

Desde 1.4.5.8, ``square_width`` también es la capacidad **por alianza** de ``space`` de las unidades en cada capa
aire/tierra/agua (mismas unidades: ``space 1`` → máximo 12 por bando si ``square_width`` es 12; conteo por alianza desde 1.4.5.9). Véase
``mod/modding.rst`` (Ocupación de casilla).

Nb_lines y nb_columns
'''''''''''''''''''''

"nb_lines 7" significa: "la cuadrícula tiene 7 líneas".
"nb_columns 7" significa: "la cuadrícula tiene 7 columnas".
La notación de letras limita las columnas a 26 (``z``); use coordenadas x,y para más columnas. hay
No hay un límite estricto para las líneas, pero el rendimiento establece un límite práctico.
Advertencia: nb_rows está en desuso y tiene el mismo significado que nb_columns.

Rutas_este_oeste y rutas_norte_sur
''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" significa: "agregar una ruta de a1 a b1, de c1 a d1, de d1 a e1 y de f1 a g1".
Sólo necesitas dar el cuadrado más al oeste del camino.
"south_north_paths a1 a3 a4 a6" significa: "agregar una ruta de a1 a a2, de a3 a a4, de a4 a a5 y de a6 a a7".
Sólo necesitas dar el cuadrado más al sur del camino.

Puentes_este_oeste y puentes_sur_norte
''''''''''''''''''''''''''''''''''''''

Los puentes funcionan exactamente como los caminos.

Caso general: oeste_este y sur_norte
''''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" significa: "agregar una salida con el estilo 'carretera' de a1 a b1, de c1 a d1, de d1 a e1"

'camino' debe definirse en style.txt

Nota: "west_east_paths" es lo mismo que "west_east path"

Nota: "puentes_sur_norte" es lo mismo que "puente_sur_norte"

Minas de oro, bosques y otros depósitos de recursos
'''''''''''''''''''''''''''''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" significa: "agregar minas de oro con 150 de oro en a2, b7, g6 y f1".

"madera 150 a2 b7 g6 f1" significa: "añadir maderas con 150 maderas en a2, b7, g6 y f1".

"mina de oro" y "madera" se definen en reglas.txt como depósitos de recursos ("depósito de clase").

Las antiguas palabras clave en plural ("minas de oro" y "bosques") todavía funcionan.

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" significa: "rellenar automáticamente el mapa con 2 prados en cada cuadrado".

prados_adicionales
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" significa: "añade 1 prado en los cuadrados a2, b7, g6 y f1".
"additional_meadows a2 a2 g6" significa: "agregar 2 prados en a2 y 1 prado en g6".

Quitar_prados
'''''''''''''

remove_meadows hace lo contrario de adicional_meadows.

Building_land (tipo de espacio de construcción predeterminado)
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Maps can choose which object type ``nb_meadows_by_square`` auto-fills::

    building_land build_site
    nb_meadows_by_square 2

- ``building_land meadow`` (predeterminado): autocompletar espacios de **pradera**.
- ``building_land build_site``: espacios para **build_site** de autocompletar (tema neutral, por ejemplo, modificaciones espaciales).

``additional_meadows`` y ``additional_build_sites`` todavía colocan esos tipos explícitamente;
``remove_meadows`` solo elimina objetos ``meadow``.

Nb_<type>_by_square (tipos de terrenos de construcción de las reglas)
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Patrón de palabras clave del mapa: ``nb_<type>_by_square <count>``, donde ``<type>`` es el nombre ``def``
of any object with ``class building_land`` in ``rules.txt``::

    nb_build_site_by_square 1
    nb_meadow_by_square 2
    nb_volcanic_rock_by_square 1

- Rellena **cada cuadrado** con esa cantidad de objetos del tipo dado.
- Los tipos provienen de reglas (los mods pueden agregar ``def volcanic_rock`` + ``class building_land`` y usar
``nb_volcanic_rock_by_square``; Los nombres Unicode como ``nb_火山岩石_by_square`` funcionan si se definen en las reglas).
- Independiente de la línea ``building_land`` del mapa.
- Puede coexistir con ``nb_meadows_by_square``; Normalmente utilizamos uno u otro.

El legado ``nb_meadows_by_square`` permanece: el nombre es histórico; el tipo real está controlado
por ``building_land`` (predeterminado ``meadow``), no analizando ``meadow`` a partir de la palabra clave.

Si el mapa omite ``building_land`` y usa solo una palabra clave ``nb_<type>_by_square``, ese tipo se convierte en ``world.building_land`` para la coincidencia.

Cuando el despegue o algunas mejoras restablecen el terreno edificable en su lugar, el motor utiliza **el tipo guardado cuando se colocó el edificio** primero; solo si falta, vuelve al mapa predeterminado anterior.

Sitios_de_construcción_adicionales
''''''''''''''''''''''''''''''''''

::

    additional_build_sites a2 b7

agrega un **build_site** por cuadrado listado (independiente de ``building_land``).

Consulte ``building-land-terrain.htm`` para terreno, terrenos edificables y ejemplos relacionados.

Terrenos_altos
''''''''''''''

Nuevo en SoundRTS 1.2 alfa 9.

"high_grounds a2 b7" significa: "a2 y b7 tendrán una altitud mayor"

Terreno de subcelda (desde 1.4.4.8)
'''''''''''''''''''''''''''''''''''

El terreno también se puede anular dentro de un cuadrado. Agrega ``/x,y`` después del cuadrado
coordinate, where ``x`` and ``y`` are 1-based coordinates inside the square::

    high_grounds a1/1,1 a1/1,2
    terrain mountain a1/2,2
    ground a1/2,2
    no_air a1/2,2

La cuadrícula de subceldas está controlada por ``subcell_precision``. El valor predeterminado es ``3``,
entonces ``a1/1,1`` significa la subcelda noroeste de una subdivisión de 3x3. el aceptado
range is 2 to 20::

    subcell_precision 20
    high_grounds a1/10,10 a1/10,11
    terrain mountain a1/1,1 a1/2,2 a1/3,3

Los siguientes comandos de terreno aceptan coordenadas de subcelda: ``terrain``,
``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` y ``no_air``.
Las subceldas no mencionadas heredan el terreno de su casilla principal.

En el modo de zoom, el navegador de mapas anuncia el terreno de la subcelda actual. si
``a1/1,1`` es terreno elevado y el resto de ``a1`` es terreno bajo, explorando eso
La subcélula anunciará la meseta, mientras que las otras subcélulas no lo harán.

Nombre_cuadrado (desde 1.4.1.8)
'''''''''''''''''''''''''''''''

Name squares or regions::

    square_name normandy 2,2 verdun 20,23
    square_name normandy 2,2 2,3 3,3

Desde 1.4.1.9, se admiten hasta tres niveles jerárquicos (provincia, ciudad, distrito). tts
anuncia nombres al ingresar desde otra región; Los niveles internos se omiten durante la navegación.
inside the same region. Translate names in ``tts.txt``::

    normandy = Normandy

Mapa de música y sonidos (desde 1.4.0.2)
''''''''''''''''''''''''''''''''''''''''

In the map file::

    map_music <id>
    map_battle_music <id>
    map_victory_sound <id>
    map_defeat_sound <id>

Definir los recursos iniciales de los jugadores.
""""""""""""""""""""""""""""""""""""""""""""""""

Nota (desde 1.4.1.8): las unidades iniciales y los recursos de la facción también se pueden definir en
``rules.txt``. Las definiciones de mapas tienen prioridad cuando se establecen ambas.

Caso 1: mismos recursos para todos
''''''''''''''''''''''''''''''''''

Utilice los siguientes comandos en combinación:

recursos_iniciales
..................

"starting_resources 10 10" significa: "cada jugador comienza con 10 de oro y 10 de madera".

unidades_iniciales
..............

"starting_units townhall farm campesino" significa: "cada jugador comienza con 1 ayuntamiento, 1 granja y 1 campesino".

"starting_units townhall 2 farm campesino" significa: "cada jugador comienza con 1 ayuntamiento, 2 granjas y 1 campesino".

población_inicial
...................

"starting_population 60" significa: "cada jugador obtiene un límite de población adicional de 60 además de
lo que proporcionan sus edificios iniciales". Este es un número entero simple (no multiplicado como
recursos). Las líneas ``player`` / ``computer_only`` por jugador también pueden incluir
``population 60`` entre las fichas de unidad para ese espacio únicamente. ``available_population``
todavía está limitado por ``global_population_limit``.

Desde SoundRTS 1.1, las unidades_iniciales también pueden contener:

- actualizaciones e investigación: "starting_units u_teleportation" significa: "cada jugador ya tiene la teletransportación investigada".
- unidades, edificios, habilidades, mejoras/investigación prohibidos (no aparecerán en el menú):

  - "starting_units -u_teleportation" significa: "cada jugador no puede investigar la teletransportación".
  - "starting_units -a_teleportation" significa: "cada jugador no puede usar la teletransportación".

casillas_iniciales
................

"starting_squares a2 b7 g6 f1" significa: "las casillas iniciales de los jugadores son a2, b7, g6 y f1".

Las unidades y edificios iniciales se crearán en estos cuadrados.

``starting_squares`` solo corrige qué cuadrados usa cada ranura de generación; de forma predeterminada, no fija qué humano que se une obtiene qué espacio (consulte random_starts_ y player_start_).

.. _random_starts:

inicios_aleatorios
.............

``random_starts 1`` (predeterminado): los espacios de generación se barajan entre los clientes humanos al inicio del juego. Las posiciones de las unidades dentro de cada ranura siguen siendo las mismas, pero la asignación de ranuras es aleatoria.

``random_starts 0``: los slots se asignan en orden a los clientes 0, 1, 2…; el primer miembro que se une siempre obtiene el primer puesto.

.. _player_start:

player_start (desde 1.4.2.8)
............................

Fija al jugador N (basado en 1, igual que ``trigger playerN``) a una ranura/cuadrado. Los jugadores fijados nunca participan en la barajada ``random_starts``; otros todavía siguen ``random_starts``.

Simple form — change the square only, keep that slot's existing resources and units::

    starting_squares a1 c1 e1
    starting_units townhall peasant
    player_start 1 b1

Full form — equivalent to pinning a full ``player`` line to player N::

    player_start 1 5 10 a1 townhall peasant

Coordinates and aliases are also supported::

    player_start 1 2,3
    player_start 2 5,1

.. _spawn_semantics:

Semántica de generación: jugador vs jugador_start
'''''''''''''''''''''''''''''''''''''''''''''''''

Ambos pueden colocar unidades/edificios en casillas específicas (por ejemplo, ``a1``), pero no significan el mismo tipo de "generación fija":

- ``player`` / ``starting_squares``: define espacios de generación y su contenido. Las coordenadas cuadradas son fijas, pero con ``random_starts 1`` se baraja qué humano obtiene qué ranura.
- ``player_start``: fija al jugador N en la ranura N (y puede cambiar el cuadrado de esa ranura), independientemente de ``random_starts``.

Patrones comunes:

Diferentes configuraciones por jugador, y el jugador 1 siempre debe comenzar desde abajo a la izquierda:

    inicios_aleatorios 1
    jugador 5 10 a1 campesino del ayuntamiento
    jugador 5 10 h1 campesino del ayuntamiento
    jugador_inicio 1 a1
    jugador_inicio 2 h1

Solo líneas de jugador, fijadas por orden de unión (no se necesita player_start):

    inicios_aleatorios 0
    jugador 5 10 a1 campesino del ayuntamiento
    jugador 5 10 h1 campesino del ayuntamiento

Configuración inicial compartida, solo algunos jugadores fijados:

    casillas_iniciales a1 c1 e1 g1
    startup_units ayuntamiento campesino
    jugador_inicio 1 a1
    jugador_inicio 3 e1

Errores comunes:

- En ``player 5 10 …``, los dos primeros números son cantidades de recursos (oro/madera), no un índice o coordenadas de jugador.
- Para fijar "qué carpintero obtiene qué esquina", utilice ``player_start`` o ``random_starts 0``; ``starting_squares`` / ``player`` por sí solo no es suficiente.

Caso 2: diferentes recursos según el jugador
''''''''''''''''''''''''''''''''''''''''''''

jugador
......

El comando "jugador" define un punto de partida que puede ser utilizado por un jugador humano o por una IA por computadora (en juegos multijugador).

Este comando se puede repetir varias veces en un mapa multijugador.

"jugador 5 10 -ayuntamiento a1 campesino c1 lacayo"
significa: "un jugador comenzará con 5 de oro, 10 de madera, no se le permitirá construir un ayuntamiento, tendrá un ayuntamiento y un campesino en A1, un lacayo en C1.

Cada línea ``player`` agrega un espacio de generación en el orden del mapa; ``a1``, ``c1``, etc. son coordenadas cuadradas. Para fijar una ranura al jugador N, use player_start_ o establezca random_starts 0 (consulte spawn_semantics_ arriba).

Lista de tipos
''''''''''''''

A continuación se muestran algunos nombres correctos para los tipos utilizados en unidades_iniciales_, jugador_ y solo_computadora_.
Para obtener una lista completa, examine el archivo reglas.txt: el nombre está justo después de la declaración "def".

- unidades: campesino lacayo arquero caballero catapulta dragón mago sacerdote nigromante
- edificios: granja cuartel aserradero herrero ayuntamiento establos taller dragonslair magestower
- habilidades: a_teletransportación
- actualización/investigación: u_teleportation melee_weapon

Agregando monstruos
"""""""""""""""""""

Agregar un punto de partida solo para computadora
'''''''''''''''''''''''''''''''''''''''''''''''''

.. _computer_only:

El comando "computer_only" define un punto de partida que siempre será reproducido por una IA de computadora. Esta IA será hostil a cualquier otro jugador o IA.

Este comando se puede repetir varias veces, pero ten cuidado: demasiada IA puede ralentizar el juego.
Así que usa una IA si se supone que estas unidades no deben luchar entre sí (varios dragones por todo el mapa, por ejemplo).

solo_computadora 0 0 a3 dragón b1 dragón
significa: "agregue una IA de computadora con 0 oro, 0 madera, un dragón en A3 y un dragón en B1".

Computadoras neutrales (desde 1.4.2.8)
..................................

Add the ``neutral`` keyword so the AI does not attack unless attacked first::

    computer_only 0 0 neutral a3 peasant b1 footman

Sin ``neutral``, la computadora es hostil para todos.

Las unidades de jugador en modo ofensivo, defensivo o de persecución no atacarán automáticamente a estos neutrales y
no huirá de ellos en modo defensivo; sólo un ataque forzado (imperativo) inicia el combate.

Espacios solo para vida silvestre (desde 1.4.3.7)
.....................................

Si una línea ``computer_only`` contiene solo animales con ``is_huntable`` / ``herdable`` (por ejemplo, ``deer``, ``sheep``, ``tiger`` personalizado), esa ranura no se une a la alianza ``"ai"`` predeterminada y no se alia con otras manadas, jugadores o arrastramiento hostil. Cada línea ``computer_only`` es un lugar de caza independiente.

Si la misma línea mezcla animales y lacayos, toda la tragamonedas sigue siendo una IA normal. Véase ``../player/hunting.htm`` §3.1.

Añade disparadores para hacer que los monstruos se muevan.
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Importante: agregue los activadores multijugador predeterminados
...............................................

Si un mapa multijugador define al menos un activador, los activadores multijugador predeterminados se ignoran. El objetivo es permitir condiciones de victoria personalizadas.

To keep the default victory conditions, the following triggers must be explicitly added to the map (or the game won't stop automatically)::

    trigger players (no_enemy_player_left) (victory)
    trigger players (no_building_left) (defeat)
    trigger computers (no_unit_left) (defeat)

Nota: el tercer disparador no es realmente necesario.

Condiciones de victoria y derrota (desde 1.4.0.1)
.............................................

Additional trigger conditions::

    trigger all (unit_lost knight) (defeat)
    trigger player1 (unit_lost a1 3 footman) (defeat)
    trigger player1 (building_lost 1 townhall) (defeat)
    trigger player1 (key_unit_killed a1 3 footman) (defeat)
    trigger all (key_unit_killed hero) (defeat)
    trigger all (key_units_killed 5 knight) (defeat)
    trigger all (units_lost 3 knight) (defeat)
    trigger all (building_lost townhall) (defeat)
    trigger all (buildings_lost 1 townhall 2 barracks) (defeat)
    trigger players (killed_target dragon) (victory)
    trigger players (killed_target dragon enemy) (victory)
    trigger player1 (has_killed 5 footman enemy) (objective_complete 1)
    trigger player1 (has_killed 1 footman 3 knight enemy) (objective_complete 2)

``killed_target`` y ``has_killed`` aceptan ``enemy`` o ``ally`` opcionales para contar únicamente
esas unidades.

Selectores de índice de unidades (desde 1.4.3.1, demostración: The Legend of Raynor capítulo 28) - igual
``\<square\> \<index\> \<type\>`` sintaxis como ``transfer_units``; identifica la enésima unidad de
that type spawned at the square (stable after movement)::

    trigger player1 (killed_target c3 3 demo_marker_footman enemy) (objective_complete 1)
    trigger player1 (killed_target c3 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Índice ``killed_target``: `` (killed_target \<square\> \<index\> \<type\> [enemy|ally])``.
Índice ``npc_has_item``: `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``.
``unit_lost`` / ``building_lost`` / ``key_unit_killed`` índice: `` (\<square\> \<index\> \<type\>)``: solo esa unidad/edificio generado (por ejemplo, proteger el ayuntamiento inicial).
No es lo mismo que ``has_killed 3 footman`` (recuento total). El ``cut_scene`` de cada objetivo debe
describir ese objetivo únicamente. Ver ``campaign/unit-index.htm``; ejemplos
``res/single/The Legend of Raynor/28.txt``, ``1.txt``.

Activadores de misiones de objetos (desde 1.4.3.1)
.....................................

has_item — player picked up a quest item (checks all living units' inventories)::

    trigger player1 (has_item lost_amulet) (objective_complete 1)
    trigger player1 (has_item health_potion 2) (objective_complete 2)

El elemento debe ser ``class item`` con ``consume_on_pickup`` no establecido en 1 (0 predeterminado), por lo que
stays in inventory after pickup. Place items on the map like units::

    lost_amulet c3
    health_potion 2 a2

Diferencias entre condiciones relacionadas:

- ``has``: recuento de unidades de jugador (``self.units``)
- ``has_item``: elementos en los inventarios de las unidades de los jugadores (encontrados/recogidos en cualquier lugar)
- ``npc_has_item``: un NPC recibió un artículo (inventario o ``received_items``); formulario de índice ``\<square\> \<index\> \<type\> \<item\>`` (capítulo 28)
- ``find``: el objeto existe en el suelo en un cuadrado (cuadrado antes del tipo, por ejemplo, ``c3 mana_potion``); Por lo general, el artículo debe dejarse caer.
- ``has_brought_item``: la unidad de jugador que lleva un objeto llega a una casilla (el objeto permanece en el inventario)
- ``remove_item``: acción desencadenante que elimina un elemento de los inventarios de los jugadores (entrega de historia)
- ``remove_ground_item``: acción desencadenante que elimina elementos en el suelo en un cuadrado
- ``do``: acción desencadenante que ejecuta múltiples subacciones en orden
- ``and``: condición de activación que es verdadera solo cuando todas las subcondiciones son verdaderas

has_brought_item — carry a quest item to a square (inventory counts; no drop required)::

    trigger player1 (has_brought_item c3 mana_potion) (objective_complete 1)

Sintaxis: ``(has_brought_item \<square\> \<item_type_name\> [count])``

remove_item — remove and destroy items from player inventories (story delivery)::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintaxis: ``(remove_item \<item_type_name\> [square] [count])``

Caudal típico: ``has_brought_item`` → ``cut_scene`` → ``remove_item`` → ``objective_complete``.
Ejemplo: La leyenda de Raynor capítulo 18.

do — run multiple trigger actions in order::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintaxis: ``(do \<action1\> \<action2\> ...)``

``if`` tiene solo dos ramas (si/si no). Utilice ``do`` cuando necesite tres o más acciones
(cortar escena, eliminar elemento, completar objetivo, etc.).

remove_ground_item — delete items on the ground at a square::

    trigger player1 (find b2 mystery_treasure)
        (do (cut_scene 7546) (remove_ground_item b2 mystery_treasure)
            (add_units b2 10 gold_coin) (objective_complete 2))

Sintaxis: ``(remove_ground_item \<square\> \<item_type_name\> [count])``

``remove_item`` se elimina de los inventarios de los jugadores; ``remove_ground_item`` elimina de
el suelo en un cuadrado (por ejemplo, después de que el jugador suelta un objeto de misión para abrir un cofre).

and — all sub-conditions must be true::

    trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin)))
        (objective_complete 3)

Sintaxis: ``(and \<condition1\> \<condition2\> ...)``

Una línea de activación tiene una expresión de condición. Envuelva múltiples condiciones en ``and``; no
escriba ``(cond1) (cond2) (action)`` (la segunda expresión S se convierte en la acción).

Para ``find``, coloque siempre el cuadrado antes del tipo, incluso dentro de ``not``.
Incorrecto: ``(not (find gold_coin b2))`` (comprueba primero el cuadrado predeterminado, casi siempre es cierto).
Derecha: ``(not (find b2 gold_coin))``. Ejemplo de soltar para abrir: La leyenda de Raynor capítulo 22; uso del inventario: capítulo 20.

npc_has_item — an NPC received a specific item (inventory or ``received_items`` record)::

    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Sintaxis (cualquier forma):

- Clásico: ``(npc_has_item \<NPC_selector\> \<item_type_name\> [square])``
- Índice: ``(npc_has_item \<square\> \<index\> \<unit_type\> \<item_type_name\>)`` — igual que
  ``transfer_units``; la enésima unidad en esa casilla por orden de generación. Ejemplo: capítulo 28.

Forma clásica:

- ``\<NPC_selector\>``: unidad ``type_name`` o id de unidad.
- ``\<item_type_name\>``: p.ej. ``health_potion``.
- Opcional `````[square]```: límites a los NPC que se encuentran actualmente en esa casilla.

Coincidencias de formularios de índice por índice de generación; la unidad puede haberse alejado de esa casilla.

give in trigger orders (scripted delivery)::

    trigger player1 (timer 5) (order (a1 1 peasant) ((give c3 health_potion)))

Example find-item map (The Legend of Raynor chapter 17)::

    title Find the lost amulet
    lost_amulet c3
    starting_squares a1
    starting_units peasant
    trigger player1 (timer 0) (add_objective 1 "find the lost amulet")
    trigger player1 (has_item lost_amulet) (objective_complete 1)

Example give-to-NPC map (``res/multi/give_demo.txt``)::

    health_potion a1
    computer_only 0 0 neutral c3 quest_npc
    trigger player1 (timer 0) (add_objective 1 "deliver the potion to the quest npc")
    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)

Ejemplos de campañas (``The Legend of Raynor``): cap. 14 entregar ``pickaxe`` a un aliado ``npc_peasant``;
cap. 15 entregar ``knight_lance`` al punto muerto ``npc_knight``; cap. 16 entregar ``wand`` al enemigo
``npc_mage`` (relaciones ``ally``/``neutral``/``enemy``). Ver ``res/single/The Legend of Raynor/14.txt``,
``15.txt``, ``16.txt``. Demostración multijugador: ``res/multi/give_demo.txt``.

Alianza de campaña y transferencia de unidades (desde 1.4.3.1)
.....................................................

La diplomacia dinámica del F12 no funciona en campañas. Después de ``alliance_request``, el ser humano
acepta con Ctrl+F4 y rechaza con Shift+F4 (sin selección de destino F12). Ver
``../player/campaign-northern-arc.htm`` para todo el arco norte (cap. 24-27).

alliance_request — trigger action: one player requests alliance with another::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (cut_scene 7585) (alliance_request computer1) (objective_complete 1))

Sintaxis: ``(alliance_request \<from\> [to])``; si se omite ``to``, la solicitud va al
propietario del disparador.

alliance_with — condition: trigger owner is allied with the given player::

    trigger player1 (alliance_with computer1) (objective_complete 2)

alliance_declined_with — condition: declined alliance request from the given player (campaign Shift+F4)::

    trigger player1 (alliance_declined_with computer1)
        (do (cut_scene 7598) (add_units c3 3 knight) (objective_abandon 1))

add_secondary_objective — acción desencadenante: agrega un objetivo opcional (anunciado con el
"optional objective" prefix). Numbering is independent from primary objectives (both start at 1)::

    trigger player1 (timer 0) (add_objective 1 7583)
    trigger player1 (timer 0) (add_objective 2 7584)
    trigger player1 (timer 0) (add_secondary_objective 1 7599)

second_objective_complete — acción desencadenante: completar el objetivo opcional N (no
affect primary objective N)::

    trigger player1 (alliance_with computer1)
        (do (cut_scene 7586) (allied_assist computer1) (secondary_objective_complete 1))

Objective_abandon — acción desencadenante: abandonar el objetivo opcional N (por ejemplo, rechazar la alianza);
solo se aplica a ``add_secondary_objective``.

Alliance_request_pending — condición: una solicitud de alianza pendiente del jugador en cuestión.

transfer_units / convert_units / change_owner - acción desencadenante: cambiar unidad
ownership from one player to another (not ``add_units`` spawning)::

    trigger player1 (alliance_with computer1)
        (do (transfer_units computer1 player1) (add_objective 2 7584))

Sin selector de unidades, se transfieren todas las unidades habitacionales del reproductor fuente.
La sintaxis del selector coincide con ``order`` / ``add_units``: ``\<square\> \<count\> \<type\>``.

allied_assist — acción desencadenante: dejar que las unidades aliadas luchen solas (guardia→persecución); no
grant player command::

    trigger player1 (alliance_with computer1)
        (do (allied_assist computer1))

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (allied_assist computer1 c2 4 npc_archer_escort))

Sintaxis:

- Aliado completo: ``(allied_assist \<ally\>)``
- Solo unidades seleccionadas: ``(allied_assist \<ally\> \<square\> \<count\> \<type\> ...)``

La sintaxis del selector de unidades coincide con ``transfer_units`` / ``add_units``. Sin selector, todo combate.
las unidades en guardia cambian a persecución; con un selector, solo cambian las unidades coincidentes; el resto son
sin cambios.

allied_control — acción desencadenante: permite que un jugador comande directamente las unidades de un aliado
(select, move, attack)::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (alliance 1) (allied_control computer1 c2 4 npc_knight_escort))

Sintaxis:

- Aliado completo: ``(allied_control \<ally\> [controller])``
- Solo unidades seleccionadas: ``(allied_control \<ally\> [\<controller\>] \<square\> \<count\> \<type\> ...)``

Sin selector, todas las unidades vivas del aliado se otorgan y pasan a perseguir. Con un selector,
sólo se otorgan unidades iguales (permanecen en guardia hasta que el jugador lo ordene); combate inigualable
Las unidades en guardia cambian para perseguir automáticamente.

add_inventory_item — put an item into a unit's inventory (quest reward, cross-chapter re-grant)::

    trigger player1 (has_killed 3 traitor_guard)
        (do (cut_scene 7580) (add_inventory_item garrek_token 1 raynor) (set_campaign_flag ch24_garrek_token))

Sintaxis: ``(add_inventory_item \<item_type\> [\<count\>] [\<unit_type\>])``; si se omite la unidad, la primera unidad amiga con ``inventory_capacity`` (la campaña de Raynor por defecto es de tipo ``raynor``).

Progreso entre capítulos (tres mecanismos)
.........................................

.. list-table::
   :header-rows: 1

   * - Mecanismo
     - Configuración
     - lleva
   * - ``campaign_carryover``
     - ``rules.txt`` campos unitarios
     - Nivel+XP, inventario
   * - 
     - (dividido; ver modding.rst)
   * - ``campaign_flag`` /
     - disparadores de mapas
     - booleanos de historia
   * - ``set_campaign_flag``
   * - ``add_inventory_item``
     - disparadores de mapas
     - artículos específicos

``campaign_flag`` persiste en ``campaigns.ini`` ``flags``; ``map_flag`` es solo por mapa.

Re-grant at chapter start::

    trigger player1 (timer 0) (if (campaign_flag ch24_garrek_token) (do (add_inventory_item garrek_token 1 raynor)))

unset_campaign_flag borra los indicadores persistentes por error.

set_ai_mode — change AI mode on the trigger owner's units::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Sintaxis: ``(set_ai_mode \<offensive|defensive|guard|chase\> [\<square\> \<count\> \<type\> ...])``.

set_yield_on_defeat — toggle per-unit yield (zero HP → yield instead of die)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Sintaxis: ``(set_yield_on_defeat \<0|1\> [\<square\> \<count\> \<type\> ...])``. También puede configurar ``yield_on_defeat 1`` en ``rules.txt``.

units_yielded — count of yielded enemy units::

    trigger player1 (units_yielded 1 npc_marco_ironhand) (objective_complete 1)

units_yielded_by — yield forced by a specific attacker (supports ``is_a``)::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy) (objective_complete 1)

has_entered — trigger owner's units entered a square (grid or place-name alias; optional unit type)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

map_flag / set_map_flag — per-map session flags (not saved in campaign config)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

stop_all_units / release_yielded_units — cease fire and end yield invulnerability::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy)
        (do (cut_scene 7710) (alliance 1 player1 computer1) (stop_all_units) (release_yielded_units computer1))

Ejecute ``cut_scene`` en los activadores del jugador 1 para que el cliente humano escuche la voz. Los cambios de modo AI/rendimiento pueden ejecutarse en la computadora 1 (propietario de la unidad).

Arco norte de La leyenda de Raynor (capítulos 24-27): historia continua con objetivo ``traitor_guard`` compartido y remanente ``campaign_flag``. Ver ``../player/campaign-northern-arc.htm``:

- cap. 24 (carta a Garrek): ``allied_control``; ``add_inventory_item garrek_token`` después de que mueren los traidores
- cap. 25 (ficha para Roland): se puede matar antes de la entrega; luego ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``
- cap. 26 (estandarte a Vera): ``transfer_units``
- cap. 27 (duelo con Marco): ``has_entered c2 raynor7`` + escena 7718; Solo Marco ``set_ai_mode offensive``; escoltas ``order`` a ``c1`` para despejar la arena; ``units_yielded_by raynor7``; ``stop_all_units`` + selectivo ``allied_control`` (4 caballeros de escolta)

El Capítulo 25 debe registrar tres objetivos principales (entregar fichas, derrotar a Roland, matar a los traidores) más el objetivo opcional 1 (alianza) al inicio. Presione F9 para objetivos primarios y opcionales. Las computadoras con script se muestran como NPC (``Player.name`` + ``is_script_npc``).

Los NPC clave (``npc_count_roland``, ``npc_roland_guard``, etc.) deben comenzar en ``ai_mode guard``. Habilite ``yield_on_defeat`` en tiempo de ejecución a través de ``set_yield_on_defeat``, no en las reglas en el momento de la generación, por lo que se puede matar a Roland antes de que se entregue el token.

patrulla
......

To order up to 10 dragons from d1 to patrol between d1 and d9::

    trigger computer1 (timer 0) (order (d1 10 dragon) ((patrol d9)))

Atacar en un momento específico.
...........................

To order up to 10 dragons from e3 to attack b2 after 20 minutes (normal speed)::

    timer_coefficient 60
    trigger computer1 (timer 20) (order (e3 10 dragon) ((go b2)))

Cambiar a otra IA
....................

The default AI for computer_only is a trigger-only, do-nothing AI. To switch to "easy" (also known as "quiet computer")::

    trigger computer1 (timer 0) (ai easy)

Agregar unidades
.........

To add 10 dragons at A1::

    trigger computer1 (timer 0) (add_units a1 10 dragon)

#elección_aleatoria, #elección_final y #elección_aleatoria
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
(nuevo en beta 9g)
Esta directiva de preprocesador elige aleatoriamente entre 2 o más opciones delimitadas por #random_choice, #end_choice y por #end_random_choice para la última opción.
Cada opción consta de cero o más líneas.
Se pueden usar más de una directiva #random_choice en un archivo de mapa, pero no se pueden anidar.

This can be used for example to place random resources. For example::

 #random_choice
 goldmines 500 e2 c6 b3 f5
 #end_choice
 goldmines 500 d2 d6 b4 f4
 #end_choice
 goldmines 500 c2 e6 b5 f3
 #end_random_choice

Las líneas anteriores significan: "añadir una mina de oro en e2, c6, b3 y f5, o en d2, d6, b4 y f4, o en c2, e6, b5 y f3". De esta forma se equilibran los recursos (si no me equivoco, claro). Este es sólo un ejemplo.

El título del mapa y el número de jugadores no se pueden cambiar de esta manera porque el preprocesador se ejecuta cuando se carga el mapa (es decir: mucho después de que se carga el menú de un jugador).

Mapas multijugador avanzados: cómo cambiar las reglas y el aspecto del juego
----------------------------------------------------------------------------

Estructura del mapa
"""""""""""""""""""

El mapa avanzado es una carpeta que contiene un archivo llamado "map.txt" con el contenido de un mapa habitual, y la mayoría de archivos y carpetas que encuentras en la carpeta "res":
reglas.txt, ai.txt, las carpetas ui y su contenido.

Nota: por el momento, en un mapa o carpeta de campaña, la versión localizada de style.txt (por ejemplo: ui-fr/style.txt) no está cargada.
Sin embargo, los sonidos localizados están cargados.

Campañas para un jugador
------------------------

Dónde almacenar una nueva campaña para un jugador
"""""""""""""""""""""""""""""""""""""""""""""""""

Si se le permite escribir en la carpeta donde está instalado SoundRTS (o prueba de SoundRTS), puede almacenar su primera campaña en la carpeta "única".

Si no se le permite escribir en la carpeta de archivos del programa porque trabaja en modo no administrador, puede almacenar su archivo de mapa de trabajo en el archivo "único".
carpeta en "C:\\Documentos y configuraciones\\Su inicio de sesión\\Datos de programa\\SoundRTS". Esta carpeta se crea la primera vez que inicia SoundRTS.
Otra solución es instalar SoundRTS en una carpeta donde puedas escribir y trabajar en la carpeta mencionada en el párrafo anterior.

Estructura de la carpeta de campaña
"""""""""""""""""""""""""""""""""""

El nombre de la carpeta de campaña se utilizará en el menú para un jugador. Las campañas oficiales tendrán su propio título en la carpeta "ui".
La carpeta contiene archivos de capítulos. También contiene archivos y carpetas que imitan la estructura de la carpeta "res": reglas.txt, ai.txt, ui...

Archivo de modificaciones requerido
'''''''''''''''''''''''''''''''''''

Nuevo en SoundRTS 1.2 alfa 10.

Una campaña puede definir qué modificaciones requiere. Las modificaciones requeridas se cargarán automáticamente.

Los mods necesarios se definen en un archivo llamado "mods.txt", en la carpeta de la campaña:

- el archivo es una lista de nombres de mods separados por comas;
- si el archivo no existe, se conservarán las modificaciones actuales;
- si el archivo está vacío, se cargará el juego "vainilla".

Archivos de capítulos
'''''''''''''''''''''

Los archivos de capítulos son archivos de texto llamados "0.txt", "1.txt", "2.txt", etc. Cuando se inicia una campaña por primera vez, solo está disponible el capítulo 0. Cuando finaliza un capítulo, se puede ejecutar el siguiente capítulo. El número del capítulo superior disponible se almacena automáticamente en el archivo de configuración del reproductor llamado campañas.ini.

Un archivo de capítulo describe un capítulo de misión o un capítulo de escena de corte.

Debe haber al menos un archivo de capítulo, llamado "0.txt".

Sintaxis de un archivo de capítulo
""""""""""""""""""""""""""""""""""

Un capítulo es una misión o una escena de corte.

Sintaxis de un archivo de capítulo de misión
''''''''''''''''''''''''''''''''''''''''''''
Un archivo de misión no es muy diferente de un mapa multijugador.
También se permite la estructura de mapas avanzada: en ese caso, el nombre de la carpeta es el número del capítulo.

Campaña cooperativa (desde 1.4.2.2; estilo AoE DE desde 1.4.4.4+): declarar
``coop_campaign`` / ``coop_intro`` / ``coop_missions`` en ``campaign.txt``;
opcional ``hero_min_level 13:2 16:3 …`` (niveles de piso de héroes entre capítulos; ver ``modding.rst``);
El modo para un jugador y el modo cooperativo cargan el mismo mapa de misión ``N.txt`` (no se envía
``N.coop.txt``). Consulte ``mod/coop-campaign.htm`` y
``player/campaign-and-co-op-improvements.htm``.

Misiones cooperativas establecidas ``nb_players_min`` / ``nb_players_max`` y múltiples ``player``
bloques en ``N.txt``; en un servidor, cualquier jugador que complete objetivos contribuye
al equipo. El modo para un jugador todavía registra a un humano y usa solo el primer engendro.

En campañas, F12 (alianza dinámica) no selecciona ningún target. Las computadoras con script de activación son
anunciado como "NPC" en lugar de nombres internos como ``ai_timers``.

Introducción
.....

Nota: un número puede representar un mensaje de texto definido en tts.txt (nuevo en SoundRTS 1.2 alpha 9).

Ejemplo: "introducción 7500 7501 7502" significa: "antes de que comience el juego, juega 7500.ogg, 7501.ogg y 7502.ogg (o texto si está definido en tts.txt)".
El comando de introducción define una secuencia de sonidos y textos que se reproducirán antes de que comience el juego. Cuando el jugador presiona una tecla, se reproduce el siguiente elemento de la secuencia. Una introducción puede ser, por ejemplo, un título con música, luego una escena con una discusión entre personajes y luego una sesión informativa. Después de la introducción, el juego contará los objetivos de la misión.

Agregar_objetivo
.............

"add_objective player1 1 7000" significa: "agregar el objetivo principal número 1 con el sonido 7000.ogg"

"add_secondary_objective player1 1 7599" significa: "añadir objetivo opcional número 1" (misión
se puede ganar sin completarlo). Los objetivos primarios y opcionales utilizan numeración independiente.
(Ambos pueden comenzar en 1; el 1 primario y el 1 opcional pueden coexistir).

Todos los objetivos principales deben completarse para ganar. Utilice ``secondary_objective_complete`` para
marcar un objetivo opcional como completado, o ``objective_abandon`` para eliminarlo. Si un objetivo primario
falla (por ejemplo, un personaje importante muere), la misión se pierde.

Register_objective (acción en un disparador)
........................................

``register_objective`` registra los números de objetivos primarios necesarios para la victoria sin
mostrándolos en la lista F9 o reproduciendo la voz de "nuevo objetivo".

Syntax (inside a trigger action)::

    register_objective 1 2 3

Por qué usarlo: si encadenas ``add_objective`` en varios activadores (revelar solo el objetivo 2)
después de completar el objetivo 1), cada ``add_objective`` también suma ese número al conjunto de victorias.
De lo contrario, completar el objetivo 1 podría desencadenar una victoria prematura cuando los objetivos 2-N no se cumplan.
añadido todavía.

Patrón de revelación progresiva: en ``timer 0``, registre todos los números y luego muestre solo el primero
objective; on each completion, ``objective_complete`` + ``add_objective`` for the next::

    trigger player1 (timer 0) (do (register_objective 1 2) (add_objective 1 7510))
    trigger player1 (has 4 pylon) (do (objective_complete 1) (add_objective 2 7511))
    trigger player1 (has_entered f1 gateway) (objective_complete 2)

Lógica de victoria: el motor mantiene ``\_required_objective_numbers`` (de ``register_objective``
y ``add_objective``) y ``\_completed_objective_numbers`` (de ``objective_complete``).
La victoria de la misión se ejecuta cuando se completan todos los números requeridos, independientemente de si se ha cumplido un objetivo.
todavía es visible en F9.

F9 / numeración por voz: cuando existen varios objetivos primarios (registrados o ya mostrados),
F9 y ``add_objective`` anuncian "Objetivo principal N:" antes de la descripción; con un
objetivo principal único, se omite el número. Consulte ``soundrts/objective_announce.py``.

Ejemplos: ``mods/starcraft/single/sc_build_tests/1.txt`` (2 goles); ``sc_late_game/1.txt`` (6
goles encadenados). Guía: ``campaign/progressive-objectives.htm``.

Objective_complete (acción en un disparador)
........................................

Esta acción solo puede incluirse en la parte de acción de un disparador.

"objective_complete 1" significa: "el objetivo principal 1 ya está completo".

Secondary_objective_complete (acción en un disparador)
..................................................

``objective_complete 1`` only affects primary objectives. To complete an optional objective, use::

    secondary_objective_complete 1

lo que significa: "el objetivo opcional 1 ya está completo".

Ejemplo de disparador:

"activar jugador1 (tiene cuartel) (objetivo_completo 2)" significa: "agregue el siguiente activador para jugador1: si tiene al menos 1 cuartel, entonces el objetivo 2 está completo"

Coeficiencia del temporizador
..................

Se puede utilizar un coeficiente de temporizador para medir el tiempo de los activadores en un bloque determinado. 

Por ejemplo, si sabe que desea que todos los factores desencadenantes se produzcan en bloques determinados de medio minuto, puede configurar el coeficiente del temporizador en 30 de esta manera.

"coeficiente_temporizador 30"

Cada vez que transcurra esta cantidad de tiempo, el contador del temporizador aumentará (aumentará en 1). Luego puede vincular activadores al temporizador que alcanza un número determinado. Por ejemplo, si quisieras que los refuerzos aparecieran en el mapa después de 90 segundos (3 incrementos de 30 segundos), harías lo siguiente. 

"activar jugador1 (temporizador 3) (add_units a1 10 lacayo)"; Después de tres tics del cronómetro, dale al jugador 10 lacayos en a1.

Cut_scene (acción en un disparador)
...............................

Nota: la distinción entre transmisión de sonidos y sonidos precargados se eliminó en SoundRTS 1.2. Todos los sonidos se cargan de antemano.

Nota: un número puede representar un mensaje de texto definido en tts.txt (nuevo en SoundRTS 1.2 alpha 9).

Se puede activar una escena en mitad de una partida: cuando se descubre algo, cuando llegan refuerzos, etc.

"cut_scene 7500 7501" significa: reproducir la escena de corte formada por los sonidos 7500 y 7501.

Ejemplo de disparador:

"trigger player1 (has_entered d5) (cut_scene 7500)" significa: "agregue el siguiente disparador para player1: si ha entrado en el cuadrado d5, reproduzca la escena de corte compuesta por el sonido 7500.ogg"

Temporizador y timer_coficient (condición en un disparador)

"coeficiente_temporizador 60"

'trigger player1 (temporizador 2) (cut_scene 7500)" significa: "después de 2 minutos (2 x 60 segundos), reproduce el archivo de sonido 7500.ogg".

Órdenes de IA
..........

Es posible controlar las acciones de la computadora en una misión, para agregar algún desafío. Tendrás que hacer esto haciendo que sus unidades reciban órdenes directamente en determinados factores desencadenantes. 

Por ejemplo, podemos hacer que las fuerzas de la IA en A1 se muevan a la ubicación conocida del jugador en A3, quien se enfrentará a las fuerzas de los jugadores cuando las encuentren. Aquí, lanzaremos un ataque con 10 lacayos contra el jugador.

"coeficiente_temporizador 60"

"activar computadora1 (temporizador 1) (orden (a3 10 lacayo) ((ir a1)))"

La ubicación de los corchetes es importante aquí, para encapsular los comandos correctos en las partes correctas de este disparador. Si por alguna razón su disparador no parece funcionar, intente verificar sus corchetes.

También es posible poner en cola órdenes para que las sigan las unidades dadas. En el siguiente escenario, imaginemos que el jugador tiene su base repartida entre a1 y b1. Entonces tendríamos que decirle a los lacayos que vayan a b1 una vez que hayan terminado con a1. Lo haríamos así. 

"activar computadora1 (temporizador 1) (orden (a3 10 lacayo) ((ir a1) (ir a b1)))"

Finalmente, si quieres que las unidades de IA entren en modo "auto_attack", donde cazarán a las unidades de jugadores supervivientes después de limpiar su base, también puedes hacerlo. 

"activar computadora1 (temporizador 1) (orden (a3 10 lacayo) ((ir a1) (ir a b1) (auto_attack)))"

Puedes usar órdenes para hacer que la computadora también entrene sus propias unidades, que luego puedes convertir en tema de órdenes posteriores. Aquí, le diremos al cuartel de la computadora que entrene inmediatamente a otros 10 lacayos para reemplazar a los que estamos a punto de enviar para atacar al jugador. 

activar computadora1 (temporizador 0) (orden (cuartel a1) ((lacayo del tren) (lacayo del tren) (lacayo del tren))); y así sucesivamente hasta que tengas 10 pedidos de lacayos del tren.

Tenga en cuenta que cada orden de entrenamiento tiene que ser separada, no puede hacer lo siguiente: (entrenar a 10 lacayos)

Esta no es la única forma de aumentar la cantidad de unidades que el jugador de la computadora tiene a su disposición; también puedes usar el orden add_units como se muestra aquí.

activar computadora1 (temporizador 0) (add_units a1 10 lacayo)

Sin embargo, esto es inmediato y no ofrece al jugador ninguna forma de influir en este evento. En el otro escenario, el jugador puede evitar que la computadora tenga su próximo grupo de lacayos destruyendo los cuarteles utilizados para entrenarlos. De esta manera, estos lacayos aparecerán independientemente.

Sintaxis de un archivo de capítulo de escena cortada
''''''''''''''''''''''''''''''''''''''''''''''''''''

Nota: la distinción entre transmisión de sonidos y sonidos precargados se eliminó en SoundRTS 1.2. Todos los sonidos se cargan de antemano.

Nota: un número puede representar un mensaje de texto definido en tts.txt (nuevo en SoundRTS 1.2 alpha 9).

Un capítulo de escena de corte es una secuencia interrumpible de sonidos. Cuando se ha reproducido el capítulo de la escena de corte, se desbloquea el siguiente capítulo.
No lo confunda con escenas más cortas ejecutadas por un disparador durante una misión cuando se cumple una condición (descubrimiento de un cuadrado, por ejemplo), o con la introducción (o sesión informativa) de la misión.

Los capítulos de las escenas de corte tienen solo 3 líneas. Por ejemplo:
corte_escena_capítulo
título 7000
secuencia 7500 7501 7502

La primera línea es una palabra clave que se utiliza para indicarle al juego que este capítulo es una escena y no una misión.
La línea de título se utiliza en el menú de la campaña.
La línea de secuencia significa: "reproduce el sonido 7500.ogg seguido de 7501 y 7502; si el jugador presiona una tecla, omite el sonido actual y reproduce el siguiente". 

Editor de mapas (experimental)
------------------------------

El cliente incluye un editor de mapas experimental para mapas multijugador. Sólo funciona para el terreno, por lo que aún tendrás que editar manualmente el mapa de las unidades.

Inicie el editor
""""""""""""""""

Comienza un juego en un mapa. Este mapa será el punto de partida. Ingrese a la consola (presione la tecla debajo de escape) e ingrese el comando: "editar". Presione Entrar. Las combinaciones de teclado del editor se cargarán desde res/ui/editor_bindings.txt.

Seleccione un terreno de la paleta
""""""""""""""""""""""""""""""""""

Presione PageUp o PageDown para seleccionar un terreno. El significado de cada terreno se almacena en ``res/ui/editor_palette.txt``.

El ``style`` de cada entrada de paleta debe coincidir con un nombre de ``class terrain`` en ``rules.txt`` (por ejemplo, ``forest``, ``dense_forest``, ``meadows``, ``lake``). Cuando se aplica:

- **Terreno estático** (``is_dynamic 0``, por ejemplo, lago, montaña): esclusas ``type_name`` en la plaza; guardado como ``terrain <name>``.
- **Terreno dinámico** (``is_dynamic 1``, por ejemplo, bosque, bosque denso, prados): coloca depósitos ``wood`` / ``meadow`` en la plaza; La voz del terreno proviene de ``square_terrain`` y puede cambiar cuando se eliminan objetos.

Aplicar un terreno a un cuadrado.
"""""""""""""""""""""""""""""""""

Presione Enter para aplicar el terreno al cuadrado actual. Las plazas vecinas con las mismas características (suelo y misma altura) quedarán unidas automáticamente por un camino. Se eliminará el camino de diferentes cuadrados.

Si el modo de zoom está habilitado, Intro aplica el terreno seleccionado sólo al terreno actual.
subcélula. El mapa guardado utilizará la sintaxis ``square/x,y`` descrita en
`Sub-cell terrain (since 1.4.4.8)`_.

Alternar ruta a un vecino
"""""""""""""""""""""""""

Presione Control + Shift + flecha para agregar o eliminar la ruta en la dirección correspondiente.

Guardar mapa
""""""""""""

Presione Control + s para guardar el mapa. El archivo nunca sobrescribirá otro archivo. El nombre del archivo será usuario/multi/editor0.txt, editor1.txt, editor2.txt, etc.

Salir del editor
""""""""""""""""

Presiona F10 y sal del juego para salir del editor. Se realizará un guardado automático del mapa por si acaso (pero no cuentes demasiado con ello). Su nombre es usuario/multi/editor_autosave.txt

Agregar unidades
""""""""""""""""

Abra el archivo en un editor de texto. Utilice los comandos mencionados en ``Defining the starting resources of the players``.
