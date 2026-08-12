# Mejoras en campañas y campañas cooperativas (1.4.3.9)

Esta guía describe las campañas cooperativas y para un jugador al estilo SoundRTS Age of Empires Definitive Edition: navegador de misiones, cinco niveles de dificultad, historia y misión cooperativa, escalamiento de enemigos y sincronización segura. Para jugadores, autores de campañas y modders.

Versión china: `../../zh/player/campaign-menu <../../zh/player/campaign-menu.htm>`_.


----


1. Descripción general
----------------------


antes
~~~~~


- Un jugador: solo lista de capítulos; sin dificultad, sinopsis o reintento en caso de derrota.
- Cooperativo (desde 1.4.2.2): varios humanos en un mapa de campaña, pero más cercano a una escaramuza que el cooperativo AoE DE (sin niveles de dificultad, espacios para jugadores, socios de IA aliados ni semántica de historia compartida).

Después (1.4.3.9)
~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Área
     - Un jugador
     - Cooperativa
   * - Menú
     - Explorador de misiones: sinopsis, dificultad, completado/bloqueado
     - Servidor: campaña → capítulo → dificultad → velocidad
   * - Dificultad
     - Cinco niveles, guardados en ``user/campaigns.ini``
     - Mismo + escala adicional por número de jugadores humanos
   * - Escalada del enemigo
     - HP enemigo/daño saliente en %
     - El servidor calcula una vez, transmite a todos los clientes/reproduce
   * - Historia
     - ``intro``, victoria/pérdida basada en objetivos
     - Compartido ``intro``, escenas, objetivos F9; no “destruir a todos los enemigos”
   * - Tragamonedas
     - Un humano
     - Un espacio por humano; espacios vacíos ocupados por IA aliada



Código principal: `soundrts/coop_difficulty.py <../../../soundrts/coop_difficulty.py>`_, ``soundrts/campaign.py <../../../soundrts/campaign.py>`_, ``soundrts/clientservermenu.py <../../../soundrts/clientservermenu.py>`_, ```soundrts/serverroom.py``.


----


2. Campaña para un jugador
--------------------------


2.1 Navegador de misión
~~~~~~~~~~~~~~~~~~~~~~~


Después de elegir una campaña del menú principal:

1. Sinopsis de la campaña (opcional): solo si ``campaign.txt`` define ``synopsis``; reproduce TTS y luego regresa a la lista.
2. Dificultad: … — nivel actual; submenú para elegir Fácil / Estándar / Moderado / Difícil / Extremo.
3. Continuar: acceso directo al último capítulo desbloqueado cuando corresponda.
4. Lista de capítulos con estado:

   - Completado: rejugable, se muestra el título completo.
   - Actual: jugable, título completo.
   - Bloqueado: número + “bloqueado” únicamente; no seleccionable (sin spoiler de título).

5. Atrás.

El progreso se almacena en `user/campaigns.ini <../../../soundrts/paths.py>`_ (``chapter`` + ``difficulty`` por identificación de campaña).

2.1.1 Crecimiento de héroes y transferencia entre misiones (basado en reglas)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Configure cualquier héroe en :strong:```rules.txt`` con ``campaign_carryover 1`` (no específico de Raynor).


.. list-table::
   :header-rows: 1

   * - Campo
     - Predeterminado
     - Efecto
   * - ``campaign_carryover_id``
     - nombre definido
     - Guardar claves `hero_<id>_xp`, etc.
   * - ``campaign_carryover_stats``
     - ``1``
     - Nivel + XP
   * - ``campaign_carryover_inventory``
     - ``1``
     - Mochila



- Guardado sólo en la victoria; Se restaura el siguiente capítulo. ``hero_min_level`` en ``campaign.txt`` opcional.
- La cooperativa no persiste héroes.
- Dividir: ``campaign_carryover_inventory 0`` (solo estadísticas) o ``campaign_carryover_stats 0`` (solo inventario).

Guía del autor: `../mod/campaign-hero-carryover <../mod/campaign-hero-carryover.htm>`_.

2.2 Sinopsis en ``campaign.txt``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   title 7747
   synopsis 7751



``7751`` es una identificación de voz en ``ui/tts.txt`` / ``ui-zh/tts.txt``. Omita ``synopsis`` para ocultar la entrada del menú.

Ejemplo: ``res/single/The Legend of Raynor/campaign.txt``.

2.3 Dificultad y escala del enemigo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- La dificultad persiste en ``campaigns.ini``; Estándar predeterminado.
- `MissionChapter.run` configura ``enemy_hp_factor`` / ``enemy_damage_factor`` en la sesión.
- Sólo unidades enemigas (no humanas, no neutrales): HP en el momento de aparición, daño causado al golpear.
- Estándar + solo = 100% / 100% (línea de base sin cambios).
- Solo nunca aplica el multiplicador de recuento de jugadores (siempre cuenta como 1 humano).

Niveles básicos (HP / daño):


.. list-table::
   :header-rows: 1

   * - Nivel
     - HP enemigo
     - Daño enemigo
   * - Fácil
     - 70%
     - 70%
   * - Estándar
     - 100%
     - 100%
   * - Moderado
     - 120%
     - 115%
   * - Difícil
     - 145%
     - 135%
   * - Extremo
     - 180%
     - 165%



2.4 Victoria y derrota
~~~~~~~~~~~~~~~~~~~~~~

- Ganar: voz Próxima misión desbloqueada; menú Continuar (capítulo siguiente) o Salir; avance del marcador.
- Pérdida: menú Reintentar esta misión o Salir.


----


3. Campaña cooperativa
----------------------


3.1 Flujo de jugadores
~~~~~~~~~~~~~~~~~~~~~~


1. Lobby del servidor → campaña cooperativa → campaña (solo si ``coop_campaign 1`` en ``campaign.txt``) → capítulo → dificultad → velocidad → crear espacio.
2. Sin paso de tratado (``treaty`` fijado en 0).
3. Otros se unen; Se inicia el host.
4. Todos reciben la introducción del capítulo, luego los activadores del mapa impulsan la victoria/pérdida.
5. Cualquier humano que complete los objetivos principales gana para el equipo; El marcador del anfitrión avanza cuando el anfitrión gana y el marcador es igual al capítulo actual.

3.2 Tabla de campaña y mapas de misión
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Menú cooperativo: controlado por ``coop_campaign`` / ``coop_intro`` / ``coop_missions`` en el ``campaign.txt`` de cada campaña (no hay nombres de campaña codificados en el motor).
- Carga de mapas: cooperativo y compartido para un jugador ``N.txt``; el servidor se carga a través de ``ensure_chapter_map`` - no ``N.coop.txt``.
- Autoría: `coop-campaign.md <../mod/coop-campaign.htm>`_ y §4 siguientes.

3.3 Misión de historia, no escaramuza
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Victoria/derrota de ``add_objective``, ``objective_complete``, ``defeat``, etc., sin borrar a todos los jugadores de IA.
- `world.is_campaign = True`: música de campaña, computadoras de activación anunciadas como "NPC", no "jugador derrotado/abandonado" para las IA de script.
- ``cut_scene`` y los objetivos se transmiten al propietario del disparador y a todos los aliados.
- `MultiplayerGame.pre_run` juega `world.intro` en modo cooperativo.

3.4 Espacios para jugadores y socios aliados de IA
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Mapa de ejemplo: ``res/single/The Legend of Raynor/1.txt``.

.. code-block:: text

   nb_players_min 1
   nb_players_max 2
   player_start 1 a1 raynor footman footman
   player_start 2 h8 raynor2 footman archer
   computer_only e5 ...




.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``nb_players_max``
     - Recuento de espacios cooperativos
   * - ``nb_players_min 1``
     - Se permiten socios Solo + AI
   * - ``player_start N …``
     - Cuadrados de generación y unidades para la ranura N.
   * - ``computer_only``
     - Enemigos de la misión (`"ai"` alianza vs humanos en la alianza 1)



``Game._fill_coop_ai_partners`` llena los espacios vacíos con una IA aliada agresiva; Todos los humanos + socios comienzan en la alianza 1.  
``player1``, ``player2``,… en los activadores se asignan a humanos en orden de unión; Las tragamonedas exclusivas de IA generalmente no son el objetivo de los desencadenantes de la historia.

3.5 Dificultad y recuento de jugadores.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Encima del nivel base:

.. code-block:: text

   count multiplier = 100 + (humans - 1) × 20   (solo = 100%)
   final hp%        = base hp% × multiplier // 100
   final damage%    = base damage% × multiplier // 100



Ejemplo: Difícil + 3 humanos → base 145/135, multiplicador 140 → ~203% HP / 189% daño.

El servidor envía ``coop_difficulty`` antes de ``start_game``; Sólo matemáticas de números enteros. La línea inicial de repetición puede agregar ``hp% damage%`` (las repeticiones antiguas tienen por defecto 100).

3.6 Nombres de lugares y recursos de campaña
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


El nombre del mapa lógico ``CampaignName/chapter`` activa `apply_campaign_from_map_name <../../../soundrts/lib/resource.py>``_ so ``rules.txt`` and campaign ``tts.txt`` load on clients; square names like ``loc_ch02_*`` se resuelve a través de TTS en lugar de leer claves sin formato.

3.7 Capítulo transversal ``campaign_flag``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


La cooperativa no establece ``world.campaign``, por lo que ``campaign_flag`` sin ningún objeto de campaña local devuelve False (no operativa determinista). En la misión ``set_map_flag`` / ``map_flag`` todavía funcionan en el estado mundial sincronizado.


----


4. Creación de mapas
--------------------


4.1 Tabla de campaña (``campaign.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Declara cooperativo como Age of Empires en :strong:```campaign.txt``. No envíe paralelo ``N.coop.txt``
archivos; El modo para un jugador y el modo cooperativo cargan el mismo mapa de misión ``N.txt``.

.. code-block:: text

   title 7747
   synopsis 7751
   coop_campaign 1
   coop_intro 0
   coop_missions 1-29




.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``coop_campaign``
     - ``1`` — mostrar en el menú de campaña cooperativa del servidor
   * - ``coop_intro``
     - Números de capítulos de escenas en el flujo cooperativo (por ejemplo, prólogo `0`)
   * - ``coop_missions``
     - Capítulos de misión jugables en modo cooperativo (`1-29`, listas de espacios, etc.)



4.2 Campos del mapa cooperativo (``N.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. ``nb_players_min 1`` / ``nb_players_max 2`` y múltiples bloques ``player`` (o ``player_start``).
2. Duplique los activadores clave por jugador cooperativo cuando sea necesario (``add_objective``, ``objective_complete``), o conduzca globalmente a través de ``player1`` si se comparte.
3. Opcional `(alliance 1)` para humanos cooperativos; enemigos a través de ``computer_only``.
4. Opcional ``intro`` / ``cut_scene``; equilibrio a través de la dificultad del motor: no se requieren trucos manuales de estadísticas.

El modo para un jugador todavía registra a un humano y usa solo el primer engendro; Los espacios cooperativos vacíos no los llena la IA en solitario.

4.3 Correcciones relacionadas (1.4.3.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Mapas multicomputadora: al completar los objetivos se gana sin tener que eliminar todas las IA del script (`Player.victory` itera una instantánea).
- F12 no selecciona ningún objetivo en las campañas; Activar computadoras anunciadas como "NPC".


----


5. Resumen de migración
-----------------------



.. list-table::
   :header-rows: 1

   * - viejo
     - Nuevo
   * - Sólo lista de capítulos
     - Sinopsis + dificultad + completado/bloqueado + reintento
   * - Cooperativa sin dificultad / paso de tratado
     - Cinco niveles + escala de recuento; ningún tratado
   * - Cooperativo como escaramuza
     - Introducción/escenas/objetivos compartidos; Socios de IA
   * - ``N.coop.txt`` o detección cooperativa basada en archivos
     - ``campaign.txt`` banderas + compartido ``N.txt``
   * - Claves sin procesar `loc_*` en modo cooperativo
     - Capa TTS de campaña, nombres localizados
   * - Estándar = línea de base
     - Todavía 100%/100%; otros niveles por mesa




----


6. Pruebas
----------


.. code-block:: bash

   python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429b_campaign_browser_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
   python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
   python -m pytest soundrts/tests/test_coop_campaign_place_names.py -q
   python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
   python -m pytest soundrts/tests/test_changelog_1428_campaign_victory_f12.py -q




----


7. Ver también
--------------



.. list-table::
   :header-rows: 1

   *-Doctor
     - Tema
   * - [objetivos-de-campaña-progresiva.md](objetivos-de-campaña-progresiva.htm)
     - ``register_objective``
   * - [campaña-arco-norte.htm](campaña-carta-secreta-alianza.htm)
     - La leyenda de Raynor cap. 24–27
   * - [campaña-coop.md](campaña-coop.htm)
     - Breve referencia cooperativa.
   * - ``mod/mapmaking.rst``
     - Sintaxis de la misión




.. list-table::
   :header-rows: 1

   * - Fuente
     - Rol
   * - ``soundrts/campaign.py``
     - Navegador SP, metadatos cooperativos (`coop_*`), marcadores, dificultad
   * - ``soundrts/coop_difficulty.py``
     - Tabla de niveles y multiplicador de recuento.
   * - ``soundrts/clientservermenu.py``
     - Menú cooperativo, ``srv_coop_difficulty``
   * - ``soundrts/serverroom.py``
     - Socios de IA, transmisión de dificultad.
   * - ``soundrts/game.py``
     - ``is_coop_campaign``, introducción, actualización de marcadores
   * - ``soundrts/worldunit/worldcreature.py``
     - Escala de HP del enemigo
   * - ``soundrts/combat/damage_effects.py``
     - Escala de daño enemigo
   * - ``soundrts/lib/resource.py``
     - Pila de recursos de campaña, colocar TTS