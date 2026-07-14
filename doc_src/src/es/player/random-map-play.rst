Generador de mapas aleatorios
=============================

Desde SoundRTS 1.4.3.4, el generador procedural de mapas aleatorios (RMG) construye mapas ``.txt`` estándar a partir de opciones del menú. Los mapas generados usan la misma canalización de carga que los mapas hechos a mano y funcionan en escaramuza local o al crear salas en línea.

----

1. Dónde encontrarlo
--------------------

.. list-table::
   :header-rows: 1

   * - Modo
     - Ruta
   * - Escaramuza local
     - Menú principal → Empezar una partida → Mapa aleatorio (primer elemento)
   * - Anfitrión en línea
     - Conectar al servidor → Crear partida → elige Mapa aleatorio → velocidad → configurar

Tras la configuración, el juego local continúa a invitar-IA / facción / empezar; el juego en línea envía un comando ``create_random`` y el anfitrión genera el mapa al inicio de la partida.

----

2. Flujo de configuración
-------------------------

El submenú recorre ( Esc vuelve un nivel ):

1. Plantilla de mapa (o Importar código para compartir — sección 4)
2. Tamaño: pequeño / mediano / grande
3. Jugadores: 2 / 3 / 4
4. Modo de equipo (solo 4 jugadores): todos contra todos o 2v2 fijo
5. Fuerza de monstruos: débil / media / fuerte (guarnición hostil del centro; ataca a los jugadores — débil: 2 footmen / media: 4 footmen + 2 archers / fuerte: 6 footmen + 4 archers + 1 knight)
6. Distribución de recursos: equilibrada / agrupada
7. Terreno (no para plantilla lanes): aleatorio / hierba / pantano / montaña
8. Agua (no para lanes): ninguna / lago / río
9. Tesoro: ninguno / bajo / alto (requiere tipos ``class item`` recogibles en rules)
10. Modo de victoria: conquista / económica / exploración / supervivencia
11. Semilla: aleatoria o número personalizado (0–99999)
12. Tratado: 0 / 5 / 10 / 15 / 20 minutos

Tras elegir la semilla oyes una vista previa por voz de los ajustes; tras confirmar el tratado se genera el mapa.

2.1 Plantillas
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Plantilla
     - Descripción
   * - Standard
     - Cuadrícula clásica, inicios y puentes aleatorios
   * - Fast
     - Más recursos iniciales, partidas más rápidas
   * - Macro
     - Mayor tope de población y más prados, centrado en economía
   * - Lanes
     - Diseño de tres carriles (estilo TD2); sin pasos de terreno/agua

2.2 Equipos 2v2
~~~~~~~~~~~~~~~

Con 4 jugadores y 2v2, el mapa añade disparadores de alianza: los jugadores 1+2 y 3+4 empiezan aliados.

2.3 Modos de victoria
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Modo
     - Condición de victoria
     - Objetivo inicial (voz)
     - Notas
   * - Conquista
     - Eliminar a todos los jugadores enemigos
     - Eliminar a todos los jugadores enemigos
     - Por defecto; no hace falta limpiar bichos del centro ni guardias de cuarteles
   * - Económica
     - El oro total recogido alcanza la meta (excluye stock inicial)
     - Recoger N oro en total
     - Gastar el oro recogido sigue contando; la vista previa anuncia N; se comprueba cada ~60 s
   * - Exploración
     - Tu campamento descubre todas las ruinas antiguas
     - Descubrir todas las ruinas con tus fuerzas
     - En 2v2 cuentan los hallazgos del aliado; en FFA los del enemigo no; la recompensa sigue yendo al primer visitante
   * - Supervivencia
     - Aguantar hasta el temporizador con el ayuntamiento intacto
     - Aguantar N minutos manteniendo el ayuntamiento
     - 10 min fast, 15 min en caso contrario; perder la base primero = derrota; se permiten varios ganadores

Metas de oro económicas (solo ``resource1``):

.. list-table::
   :header-rows: 1

   * - Plantilla
     - Meta
   * - Fast
     - 2000
   * - Standard
     - 3000
   * - Macro
     - 5000
   * - Lanes
     - 2500

Perder todos los edificios ``provides_survival`` sigue significando derrota. En modos exploración/económica/supervivencia, eliminar a todos los enemigos no gana automáticamente; aún puedes atacar.

Todos los modos también generan ruinas antiguas (recompensa de recursos de una sola vez en la primera visita) y cuarteles capturables (limpiar guardias, capturar, luego entrenar unidades).

----

3. Anuncio de generación y F5/F6
--------------------------------

En modo local, cuando el mapa está listo el juego anuncia:

- Mapa generado
- Semilla (número para reproducir el mismo diseño)
- Código para compartir (cadena completa de ajustes)
- Pulsa F5 para repetir (pista de historial)

El menú de invitar-IA que sigue no borra esto: F5 repite el mensaje anterior, F6 recorre el historial de voz para que puedas revisar semilla y código en cualquier momento.

Los menús admiten las mismas teclas de historial F5 / F6 que en el juego.

----

4. Códigos para compartir
-------------------------

4.1 Formato
~~~~~~~~~~~

Ejemplo:

.. code-block:: text

   RMG1:f:m:2:med:b:r:f:v:hi:4242

Once partes separadas por dos puntos: prefijo ``RMG1`` + 10 campos:

.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
     - Ejemplos
   * - Plantilla
     - standard / fast / macro / lanes
     - ``s`` / ``f`` / ``m`` / ``l``
   * - Tamaño
     - small / medium / large
     - ``s`` / ``m`` / ``l``
   * - Jugadores
     - 2–4
     - `2`
   * - Monstruos
     - weak / medium / strong
     - ``w`` / ``med`` / ``s``
   * - Recursos
     - balanced / clustered
     - ``b`` / ``c``
   * - Terreno
     - random / grass / marsh / mountain
     - ``r`` / ``g`` / ``a`` / ``t``
   * - Equipos
     - ffa / teams_2v2
     - ``f`` / ``t``
   * - Agua
     - none / lake / river
     - ``n`` / ``l`` / ``v``
   * - Tesoro
     - none / low / high
     - ``n`` / ``lo`` / ``hi``
   * - Semilla
     - 0 = aleatoria; >0 fija
     - `4242`

La importación acepta códigos con o sin el prefijo ``RMG1:``; ``/`` funciona como separador en lugar de ``:``.

4.2 Importar código para compartir
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

En el submenú de plantilla de mapa, elige Importar código para compartir, escribe o pega el código, Intro para confirmar, Esc para cancelar.

El cuadro de entrada admite atajos de edición estándar (igual que otros campos ``input_string`` como semilla o login):

.. list-table::
   :header-rows: 1

   * - Atajo
     - Acción
   * - Ctrl+A
     - Seleccionar todo
   * - Ctrl+C
     - Copiar (todo el texto si no hay selección)
   * - Ctrl+X
     - Cortar
   * - Ctrl+V
     - Pegar (caracteres inválidos filtrados)
   * - Retroceso / Supr
     - Borrar selección o carácter antes/después del cursor

Longitud máxima 80; caracteres permitidos: letras, dígitos, ``:``, ``/``, ``.``, ``-``.

Al éxito oyes una vista previa y vas directo a Tratado (saltando pasos intermedios). Los códigos inválidos muestran Código para compartir inválido y vuelven al menú de plantilla.

----

5. Notas de multijugador
------------------------

- El comando `create_random …` del anfitrión se aplica cuando empieza la partida; todos los clientes obtienen el mismo mapa determinista a partir de semilla + ajustes.
- Los clientes no oyen el anuncio local «mapa generado + código para compartir»; comparte el código antes de alojar o haz que los invitados importen el mismo código al crear una sala.
- Las partidas públicas y los minutos de tratado siguen los submenús habituales de velocidad / visibilidad.

----

6. frente a `#random_choice` en archivos de mapa
------------------------------------------------

``#random_choice`` / ``#end_random_choice`` en un archivo de mapa son elecciones del preprocesador entre alternativas fijas (p. ej. colocación aleatoria de oro). Eso no es RMG.

RMG genera el mapa entero a partir de parámetros, con semillas y códigos para compartir para la reproducción.

----

7. Fuente
---------

.. list-table::
   :header-rows: 1

   * - Elemento
     - Ruta
   * - Docs en el juego
     - ``doc/es/randommap.htm`` (menú principal → Documentación → Guía de mapas aleatorios)
   * - Generador
     - ``soundrts/randommap.py``
   * - Menús
     - ``soundrts/randommap_menu.py``
   * - Pruebas
     - ``soundrts/tests/test_randommap.py``
