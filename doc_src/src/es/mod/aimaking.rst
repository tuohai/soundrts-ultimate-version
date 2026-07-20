Tutorial de creación de IA
==========================

.. contents::

1. Introducción
---------------

Este tutorial explica cómo escribir IAs del ordenador.
Editas ``ai.txt`` (scripts) y, para mods, ``rules.txt`` (asignaciones de dificultad
por facción). Estos archivos viven en la carpeta ``res`` del paquete SoundRTS; un mod,
una campaña o un mapa también pueden incluir sus propias copias.

Una IA es un script pequeño: una lista de comandos que el ordenador ejecuta de arriba
abajo, en bucle para siempre. No se requieren conocimientos de programación.

2. ``ai.txt``: scripts de IA
----------------------------

En ``ai.txt``, cada IA empieza con ``def \<name\>`` seguido de sus comandos::

    def tang_empire_easy
    research 1
    workers 12
    get 9 villager 5 footman
    attack
    goto -1


Notas:

- Los nombres pueden ser cualquier identificador, p.e. ``tang_empire_easy`` o ``my_mod_hard``.
  Los nombres personalizados no se muestran en el menú de invitación; Los jugadores ven la dificultad.
  nivel asignado en ``rules.txt`` (siguiente sección).
- Si el ``ai.txt`` de un mod contiene ``clear``, todos los scripts de IA cargados hasta el momento
  (incluidos los cinco niveles básicos de ``res/ai.txt``) se descarta. esto
  no cambia la cantidad de botones de invitación que aparecen; solo afecta cual
  Las entradas ``def`` permanecen cargadas. La mayoría de las modificaciones no necesitan ``clear``.
- Las líneas ``def`` con el mismo nombre en una capa posterior anulan las anteriores.
- Si no existe ningún script para un nivel solicitado en tiempo de ejecución, ``get_ai`` vuelve a
  el script definido más cercano (incluido el heredado ``easy`` / ``aggressive``
  cadena de alias).

3. Menú de invitación y asignaciones ``rules.txt``
--------------------------------------------------

Los menús de invitar ordenador (un jugador y multijugador) los controla el
``rules.txt`` del mod actual, no una lista fija de cinco botones. No hacen falta
líneas vacías de marcador de posición como ``def beginner`` en ``ai.txt``.

sin mod
~~~~~~~

El menú siempre ofrece los cinco niveles estándar:

- ``beginner`` -- Principiante (Junior)
- ``intermediate`` -- Intermedio (Intermedio)
- ``advanced`` -- Avanzado (Avanzado)
- ``expert`` -- Experto
- ``nightmare`` -- Pesadilla (Pesadilla)

Con un mod cargado
~~~~~~~~~~~~~~~~~~

El motor escanea los bloques de facciones en ``rules.txt`` en busca de dificultades para mapear líneas.
Cada nivel aparece en el menú cuando al menos una facción asigna ese nivel a un
nombre de script que existe como ``def`` en ``ai.txt``.

Recommended (new mods) -- standard tier names inside each faction block::

    def tang_empire
    class race
    townhall county_government
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard


Esto produce Invitar computadora principiante/intermedia/avanzada (tantas
botones mientras mapea). Si el jugador elige "principiante" de la facción Tang, el
Se ejecuta el script ``tang_empire_easy``.

Legacy mods -- still using ``easy`` / ``aggressive``::

    def orc
    class race
    ...
    easy orc_defensive
    aggressive orc_aggressive


El menú muestra Invitar a una computadora silenciosa/agresiva (defensiva/agresiva).
etiquetas en la interfaz de usuario china). El anfitrión aún invita al nivel ``easy`` o ``aggressive``;
``rules.txt`` resuelve el guión real por facción.

Resumen
~~~~~~~

- ``ai.txt`` contiene guiones; ``rules.txt`` asigna niveles a scripts por facción.
- Diferentes facciones pueden asignar el mismo nivel a diferentes scripts; las listas del menú
  Solo nombres de niveles, no nombres de scripts específicos de facciones.
- Si tanto ``beginner`` como ``easy`` están asignados, solo aparece ``beginner``.
- Los scripts internos como ``timers`` nunca aparecen en el menú de invitación.
- Los anfitriones multijugador envían ``invite_ai \<tier\>`` (por ejemplo, ``invite_ai beginner``).
  Los comandos heredados ``invite_beginner``, etc. aún funcionan.

4. Configuraciones (escritas una vez, cerca de la parte superior de "def")
--------------------------------------------------------------------------

Estos ajustan el comportamiento general de la IA. Colóquelos cerca de la parte superior de un ``def`` para que
corren antes del bucle. Una mayor dificultad normalmente significa una economía más grande,
Investigación activada, más bases y más voluntad de atacar.

- ``constant_attacks 0/1`` -- cuando ``1`` la IA sigue atacando y explorando
  el mapa en lugar de tortugas en casa.
- ``research 0/1`` -- cuando ``1`` la IA investiga arma/armadura/habilidad
  actualizaciones siempre que se lo pueda permitir.
- ``workers \<n\>`` -- el número de trabajadores (campesinos) que la IA intenta retener.
  Más trabajadores significa una economía más fuerte. Predeterminado: ``10``.
- ``expand \<n\>`` -- el número total de ayuntamientos (bases) a mantener. el
  La base inicial cuenta, por lo que ``expand 2`` hace que la IA construya una base adicional.
  Predeterminado: ``0`` (sin expansión adicional).
- ``attack_ratio \<percent\>`` -- qué tan fuerte debe ser el ejército de la IA, en comparación con
  enemigo en el área objetivo, antes de atacar. ``180`` (el valor predeterminado) significa
  "atacar sólo con un 80% de ventaja" (cauteloso). Los valores más bajos hacen que la IA
  comprometerse antes; por debajo de ``100`` ataca incluso cuando está un poco más débil
  (presión implacable).
- ``counter_skill \<0-100\>`` -- qué tan bien las unidades de la IA usan ``mdg_vs`` /
  ``rdg_vs`` bonificaciones de contraataque al elegir objetivos y enviar ataques.
  ``0`` ignora los contadores (prioridad ``menace`` pura). ``100`` siempre elige el
  mejor coincidencia de contador, incluidos los tipos heredados a través de ``is_a`` (por ejemplo,
  ``mdg_vs cavalry`` también contrarresta un camello con ``is_a cavalry``). Valores en
  entre bonificación de contador de mezcla y ``menace``. Valor predeterminado si se omite: ``100``.

  Conjuntos vainilla ``res/ai.txt``: principiante ``25``, intermedio ``50``,
  avanzado ``75``, experto ``90``, pesadilla ``100``.
- ``starting_resources \<amounts...\>`` -- recursos adicionales agregados además de
  comienza el mapa (o facción). Mismo orden y mismas unidades que el mapa.
  ``starting_resources`` (por ejemplo, ``10 10`` = 10 de oro y 10 de madera; internamente
  almacenado como ``× 1000`` como se inicia el mapa). Omitido = sin bonificación.
- ``starting_units \<unit\>...`` -- unidades o edificios de bonificación generados en el
  Casilla de salida de la IA después de la salida normal. Utiliza la misma sintaxis plana que map.
  ``starting_units`` (ponga un recuento antes del nombre de un tipo para generar varios:
  ``5 footman 2 archer``). Respeta los nombres de las facciones ``equivalent``.
  **Consumen población** (igual que las unidades iniciales del mapa; sube el
  tope con ``starting_population`` si hace falta). Omitido = sin unidades de bonificación.
- ``starting_population \<n\>`` -- límite de población adicional agregado además de
  casas y otras unidades ``population_provided``. Entero simple (no ``× 1000``).
  ``available_population`` todavía está limitado por el ``global_population_limit`` del mapa.
- ``train_time \<pct\>`` -- porcentaje de la duración normal de entrenamiento
  (``100`` = normal, ``50`` = mitad de tiempo). Solo afecta a ``train`` y
  morph-as-train. Omitido = ``100``.
- ``research_time \<pct\>`` -- porcentaje de la duración normal de investigación /
  avance (``100`` = normal, ``80`` = 20% más rápido). Solo ``research`` /
  ``advance``. Omitido = ``100``.
- ``build_time \<pct\>`` -- porcentaje de la duración normal de construcción
  (``100`` = normal, ``50`` = el doble de rápido). Afecta el progreso en obra.
  Omitido = ``100``.
- ``gather_time \<pct\>`` -- porcentaje de la duración normal de recolección
  (``100`` = normal, ``50`` = el doble de rápido). Solo afecta al tiempo de
  cosecha de los trabajadores del ordenador (``Worker.get_gather_time``).
  **Nota:** es el multiplicador de dificultad de ``ai.txt``, no el campo
  ``gather_time`` de trabajadores en ``rules.txt``. Omitido = ``100``.
- ``unit_hp \<pct\>`` -- porcentaje de PV normales de todas las unidades de este
  ordenador (``100`` = normal, ``120`` = +20% PV). Tras el ``enemy_hp_factor``
  de coop. Omitido = ``100``.

  Estas líneas se aplican una vez al inicio del juego; no son parte del
  bucle de secuencia de comandos (a diferencia de ``get`` / ``attack``).

  Bonificaciones de vainilla ``res/ai.txt`` (además de cada inicio de mapa):

  - intermedio: ``starting_resources 50 50``, ``starting_population 10``
  - avanzado: ``100 100`` + ``2 footman 2 archer``, ``starting_population 20``,
    ``train_time 50``, ``research_time 80``, ``build_time 50``, ``gather_time 50``
  - experto: ``200 200`` + ``5 footman 4 archer 2 knight``, ``starting_population 40``,
    ``train_time 50``, ``research_time 70``, ``build_time 50``, ``gather_time 50``,
    ``unit_hp 120``
  - pesadilla: ``400 400`` + ``8 footman 6 archer 4 knight``, ``starting_population 60``,
    ``train_time 40``, ``research_time 60``, ``build_time 40``, ``gather_time 40``,
    ``unit_hp 140``
- ``watchdog \<seconds\>`` -- una red de seguridad: si la IA está atrapada en la misma línea
  durante este tiempo, pasa a la siguiente línea. ``0`` lo desactiva.

Contraobjetivo (``counter_skill``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cuando ``counter_skill`` está por encima de ``0``, las unidades informáticas prefieren enemigos a los que
contador según ``rules.txt`` bonificaciones de daño:

- Un caballero con ``mdg_vs archer 12`` enfoca a los arqueros sobre unidades superiores de ``menace``.
- Un arquero con ``rdg_vs footman 7`` enfoca a los lacayos.
- Escriba los nombres en ``mdg_vs`` / ``rdg_vs`` que coincidan con el ``type_name`` del objetivo o cualquier
  nombre en su cadena de herencia ``is_a``.

Con un ``counter_skill`` bajo, los objetivos con un ``menace`` alto aún pueden ganar; en ``100``,
la mejor contrapartida gana a menos que solo haya un enemigo dentro del alcance.

Desde 1.4.5.2, el ``menace`` por defecto es una **puntuación de combate multidimensional**
(daño, cover/acierto, enfriamiento, preparación/ready, HP, armadura, esquiva, alcance, velocidad),
opcionalmente anulable con ``menace_mult`` / ``menace_vs`` — ver ``modding.rst``
*Amenaza automática / prioridad de objetivo*.

Esto afecta tanto al micro (a qué enemigo ataca cada unidad) como al macro.
(qué área empujar y qué unidades enviar primero), siempre y cuando el ejército todavía
cumple con ``attack_ratio``.

5. Comandos de acción
---------------------

- ``get \<n\> \<unit\>...``: recluta o construye hasta que la IA posea ``\<n\>`` de cada uno
  unidad/edificio listado. Puede enumerar varios pares a la vez. Ver ``rules.txt``
  para conocer los nombres exactos de los tipos de unidades.
  Ejemplo: ``get 10 footman 20 archer 10 knight``
- ``attack`` -- a partir de este momento, ataca siempre que sea lo suficientemente fuerte (también
  enciende ``constant_attacks``).
- ``wait \<seconds\>``: permanezca en esta línea durante ``\<seconds\>`` antes de continuar.
  Útil para marcar el ritmo (una IA sencilla puede ``wait`` entre oleadas). Nota: un distinto de cero
  ``watchdog`` todavía puede sacar a la IA de la línea antes de tiempo.

6. control de flujo
-------------------

- ``label \<name\>``: marca una posición a la que puedes saltar.
- ``goto \<name\>`` -- salta a una etiqueta. ``goto`` también acepta una línea relativa
  desplazamiento como ``goto -1`` (retrocede una línea).
- ``goto_random \<name1\> \<name2\> ...`` -- salta a una de las etiquetas enumeradas,
  elegido al azar. Genial para hacer que la IA sea impredecible.

7. Ejemplo de modificación (tres niveles, scripts por facción)
--------------------------------------------------------------

``ai.txt`` excerpt::

    def tang_empire_easy
    constant_attacks 0
    get 9 villager 5 footman
    attack
    goto -1

    def tang_empire_hard
    constant_attacks 1
    get 9 villager 10 footman
    attack
    goto -1


``rules.txt`` excerpt for the Tang faction::

    def tang_empire
    class race
    peasant villagers
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard


El menú muestra tres niveles; Ejecuciones Tang + "intermedias" ``tang_empire_hard``.

8. Ejemplo completo (un nivel básico)
-------------------------------------

::

    def advanced

    counter_skill 75
    watchdog 480
    constant_attacks 1
    research 1
    workers 18
    expand 2          ; second base for a stronger economy
    attack_ratio 150  ; pushes with a smaller advantage

    label open
    get 9 peasant 6 footman 4 archer
    attack
    goto_random knights mixed

    label knights
    get 9 peasant 16 knight 10 archer 3 catapult
    attack
    goto open

    label mixed
    get 9 peasant 20 archer 12 knight 5 priest 4 catapult
    attack
    goto open


Todo lo que sigue a ``;`` en una línea es un comentario y se ignora.