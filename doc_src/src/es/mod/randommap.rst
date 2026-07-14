.. raw:: html

   <script tipo="text/javascript" src="langdir.js"></script>

Guía de mapas aleatorios
========================

.. contents::

Introducción
------------

Desde SoundRTS 1.4.3.4, el generador de mapas aleatorios de procedimiento (RMG) crea mapas estándar ``.txt`` a partir de las opciones del menú. Los mapas generados utilizan el mismo canal de carga que los mapas hechos a mano y funcionan en escaramuzas locales o en la creación de salas en línea.

1. Dónde encontrarlo
--------------------

.. list-table::
   :header-rows: 1

   * - Modo
     - Camino
   * - Locales
     - Menú principal → Iniciar un juego → Mapa aleatorio (primer elemento)
   * - escaramuza
   * - Anfitrión en línea
     - Conéctese al servidor → Crear juego → elija Mapa aleatorio → velocidad →
   * - 
     - configurar

Después de la configuración, el juego local continúa invitando a IA/facción/inicio; el juego en línea envía un comando ``create_random`` y el anfitrión genera el mapa al inicio del juego.

2. Flujo de configuración
-------------------------

El submenú recorre (Esc retrocede un nivel):

1. Plantilla de mapa (o Importar código compartido – sección 4)
2. Tamaño: pequeño/mediano/grande
3. Jugadores: 2 / 3 / 4
4. Modo equipo (solo 4 jugadores): todos contra todos o 2v2 fijo
5. Fuerza del monstruo: débil / media / fuerte (guarnición central hostil; ataca a los jugadores - débil: 2 lacayos / media: 4 lacayos + 2 arqueros / fuerte: 6 lacayos + 4 arqueros + 1 caballero)
6. Diseño de recursos: equilibrado/agrupado
7. Terreno (no para plantilla de carriles): aleatorio/hierba, más cada terreno ``rmg_terrain 1`` en ``rules.txt``
8. Agua (no para carriles): ninguna / lago / río
9. Tesoro: ninguno / bajo / alto (requiere reglas de tipos seleccionables ``class item``)
10. Modo de victoria: conquista/económico/exploración/supervivencia (conquista por defecto; ver sección 7)
11. Semilla: número aleatorio o personalizado (0–99999)
12. Tratado: 0 / 5 / 10 / 15 / 20 minutos

Después de la selección de semillas, escuchará una vista previa de voz de la configuración; Después de la confirmación del tratado, se genera el mapa.

2.1 Plantillas
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Plantilla
     - Descripción
   * - Estándar
     - Cuadrícula clásica, inicios y puentes aleatorios.
   * - Rápido
     - Mayores recursos iniciales, juegos más rápidos.
   * - Macro
     - Mayor límite de población y más praderas, centrado en la economía.
   * - Carriles
     - Diseño de tres carriles (estilo TD2); sin terreno/escalones de agua

2.2 Equipos 2v2
^^^^^^^^^^^^^^^

Con 4 jugadores y 2v2, el mapa añade activadores de alianza: los jugadores 1+2 y 3+4 comienzan aliados.

3. Anuncio de generación y F5/F6
--------------------------------

En modo local, cuando el mapa está listo el juego anuncia:

- Mapa generado
- Semilla (número para reproducir el mismo diseño)
- Compartir código (cadena de configuración completa)
- Presione F5 para repetir (pista del historial)

El menú de invitación-AI que sigue no borra esto: F5 repite el mensaje anterior, F6 recorre el historial de voz para que puedas revisar las semillas y compartir el código en cualquier momento.

Los menús admiten las mismas teclas de historial F5/F6 que en el juego.

4. Compartir códigos
--------------------

4.1 Formato
^^^^^^^^^^^

Example::

 RMG1:f:m:2:med:b:r:f:v:hi:c:4242

Doce partes separadas por dos puntos: prefijo ``RMG1`` + 11 campos (los códigos antiguos de 10 campos omiten la victoria y el valor predeterminado es conquista):

.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
     - Ejemplos
   * - Plantilla
     - estándar / rápido / macro / carriles
     -s/f/m/l
   * - Tamaño
     - pequeño / mediano / grande
     - s/m/l
   * - Jugadores
     - 2–4
     - 2
   * - Monstruos
     - débil / medio / fuerte
     - con/med/s
   * - Recursos
     - equilibrado / agrupado
     - b/c
   * - Terreno
     - aleatorio / hierba / pantano / montaña
     -r/g/a/t
   * - Equipos
     -ffa/equipos_2v2
     -f/t
   * - Agua
     - ninguno / lago / río
     -n/l/v
   * - Tesoro
     - ninguno / bajo / alto
     - n / lo / hola
   * - Victoria
     - conquista / económica /
     -c/e/x/s
   * - 
     - exploración / supervivencia
   * - Semilla
     - 0 = aleatorio; >0 fijo
     - 4242

Abreviaturas de victoria: ``c`` conquista, ``e`` económica, ``x`` exploración, ``s`` supervivencia.

La importación acepta códigos con o sin el prefijo ``RMG1:``; ``/`` funciona como separador en lugar de ``:``.

4.2 Importar código compartido
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

En el submenú de plantilla de mapa, elija Importar código compartido, escriba o pegue el código, Ingrese para confirmar, Esc para cancelar.

El cuadro de entrada admite atajos de edición estándar (igual que otros campos de entrada de texto, como semilla o inicio de sesión):

.. list-table::
   :header-rows: 1

   * - Acceso directo
     - Acción
   *-Ctrl+A
     - Seleccionar todo
   *-Ctrl+C
     - Copiar (todo el texto si no hay nada seleccionado)
   *-Ctrl+X
     - Cortar
   *-Ctrl+V
     - Pegar (se filtran los caracteres no válidos)
   * - Retroceso / Eliminar
     - Eliminar selección o carácter antes/después del cursor

Longitud máxima 80; caracteres permitidos: letras, dígitos, ``:``, ``/``, ``.``, ``-``.

Si tiene éxito, escuchará una vista previa y irá directamente al Tratado (omitándose los pasos intermedios). Los códigos no válidos muestran Código compartido no válido y regresan al menú de plantilla.

5. Notas multijugador
---------------------

- El comando ``create_random …`` del anfitrión se aplica cuando comienza el juego; Todos los clientes obtienen el mismo mapa determinista de la configuración semilla +.
- Los clientes no escuchan el anuncio local "mapa generado + código compartido"; comparta el código antes de hospedar o haga que los invitados importen el mismo código al crear una habitación.
- Los juegos públicos y las actas de tratados siguen los submenús habituales de velocidad/visibilidad.

6. vs. ``#random_choice`` en archivos de mapas
----------------------------------------------

``#random_choice`` / ``#end_random_choice`` en un archivo de mapa son selecciones del preprocesador entre alternativas fijas (por ejemplo, colocación aleatoria de oro). Eso no es RMG.

RMG genera el mapa completo a partir de parámetros, con semillas y códigos compartidos para su reproducción.

7. Jugabilidad inspirada en HoMM/Civ5
-------------------------------------

Funciones de RMG inspiradas en Heroes of Might and Magic y Civilization V (objetivos del mapa y puntos de interés, no árboles tecnológicos o por turnos completos):

7.1 Modos de victoria
^^^^^^^^^^^^^^^^^^^^^

Conquista
    Elimina a todos los jugadores enemigos (predeterminado; eliminar los creeps del centro es opcional).

Económico
    El oro total recolectado alcanza la meta (excluye las existencias iniciales; el gasto aún cuenta; se verifica aproximadamente cada 60).
    Rápido 2000 / estándar 3000 / macro 5000 / carriles 2500.

Exploración
    Tu campamento descubre cada ruina antigua (FFA: solo cuentan tus hallazgos; 2v2: los hallazgos de tus aliados cuentan).

Supervivencia
    Mantén presionado hasta que el cronómetro termine con tu ayuntamiento intacto (10 min rápido / 15 min en caso contrario).

Perder todos los edificios ``provides_survival`` sigue significando la derrota. En los modos de exploración, economía y supervivencia, eliminar a todos los enemigos no significa ganar automáticamente; todavía puedes atacar. Los controles de victoria se realizan cada 30 segundos (exploración) o 60 segundos (económico) después de que se cumplan las condiciones.

7.2 PDI del mapa
^^^^^^^^^^^^^^^^

Cada mapa RMG (cuando existen tipos en ``rules.txt``) puede incluir:

- Ruinas antiguas (``ancient_ruin``): tu unidad entra al cuadrado en busca de recursos (rápido: 300 de oro + 150 de madera; otros: 500 + 250); la exploración requiere que tu campamento encuentre todas las ruinas; recompensa únicamente al primer visitante; El edificio permanece después del descubrimiento.
- Cuartel capturable (``captured_barracks``): 2 lacayos + 1 arquero guardia; despejar guardias, atacar para capturar, luego entrenar a lacayos/arqueros; Los cuarteles no reforzados generan lacayos adicionales cada ~5 a 10 minutos.
- Guarnición central: menú de fuerza de monstruos (2 lacayos débiles / medio 4+2 / fuerte 6+4+1 caballero)

7.3 Lectura adicional
^^^^^^^^^^^^^^^^^^^^^

Finalización, ID y extensión del mod: ``player/homm-civ5-play.htm`` (chino; detalles de RMG e inglés en ``player/random-map.htm``).

8. Plantillas de mapas aleatorias personalizadas
------------------------------------------------

Los jugadores y autores de mods pueden agregar archivos de texto ``random_map_template`` para ampliar las plantillas RMG y alinear las opciones de terreno con ``rules.txt``.

8.1 Dónde colocar archivos
^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``cfg/randommap/*.txt`` — plantillas de reproductor local (recomendado)
- ``mods/<modname>/randommap/*.txt`` — enviado con un mod
- Referencia de sintaxis: ``res/randommap/example.txt``

8.2 Formato de archivo
^^^^^^^^^^^^^^^^^^^^^^

::

 random_map_template
 name my_macro
 extends macro
 title My macro map
 terrain_modes random grass marsh rocky_plain
 water_terrain lake
 monster_medium 4 footman 2 archer

- ``extends`` hereda de ``standard``, ``fast``, ``macro``, ``lanes`` u otra plantilla personalizada
- Las plantillas integradas omiten ``terrain_modes`` para enumerar automáticamente ``random``, ``grass`` y todos los terrenos ``rmg_terrain 1`` de las reglas
- ``terrain_modes`` restringe opcionalmente el menú (cada nombre debe estar ``class terrain`` en ``rules.txt``)
- Compartir códigos: las plantillas integradas todavía usan abreviaturas ``RMG1:``; plantillas personalizadas o nombres de terreno personalizados utilizan ``RMG2:`` (nombres completos, sin abreviaturas)

8.3 Banderas de terreno en reglas.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Banderas opcionales en ``class terrain``:

- ``rmg_terrain 1`` — terreno terrestre que RMG puede colocar
- ``rmg_border 1`` — colocar a lo largo de los bordes del mapa (por ejemplo, montañas)
- ``rmg_water 1`` — nombre del terreno usado para cuadrados de agua de lago/río
- ``rmg_ford 1`` — nombre del terreno utilizado para los cruces de vado en el mapa de carriles

Cuando RMG coloca terreno, lee ``speed``, ``is_water``, ``blocks_path`` y las propiedades relacionadas de las reglas en lugar de los valores ``marsh`` / ``mountain`` codificados.
