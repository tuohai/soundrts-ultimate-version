
Notas de la versión
===================

.. contents::

1.4.9.4
--------

**Corrección: unirse después de que el anfitrión arrancara solo pitaba**

- **Problema**: abrir el menú de acciones de una sala en espera, esperar a que el anfitrión arranque y entonces elegir Unirse seguía enviando ``register`` con la instantánea antigua. El servidor respondía ``register_error``; el cliente solo pitaba.
- **Cambio**: si la partida ya está ``started``, el servidor envía ``game_already_started`` y el cliente anuncia que la partida ya ha empezado. Espectar no cambia.
- **Alcance**: ``serverclient.py`` ``cmd_register``; ``clientservermenu.py`` ``srv_game_already_started``; ``GAME_ALREADY_STARTED`` (5834).

**Corrección: la lista de salas avisaba maps / invitations**

- **Problema**: en la lista de salas (o su submenú), al arrancar el anfitrión se seguían enviando ``maps``, ``invitations`` y ``update_menu`` de vestíbulo. La lista no es ``ServerMenu``, así que las dos primeras daban WARNING; ``update_menu`` redibujaba el instantáneo viejo y seguía ofreciendo Unirse.
- **Cambio**: los menús anidados ignoran ``maps`` / ``invitations``; la lista pide ``list_rooms`` en ``update_menu``.
- **Alcance**: ``clientservermenu.py`` ``_ServerMenu`` ``srv_maps`` / ``srv_invitations``; ``RoomListMenu.srv_update_menu``.

**Cambio: velocidad de juego predeterminada en Opciones**

- **Problema**: solitario y campaña usaban ``speed`` de ``SoundRTS.ini``, pero Opciones no lo cambiaba y se quedaba en 1.
- **Cambio**: Opciones → **Velocidad de juego predeterminada**: 1, 1.5, 2, 2.5, 3, 3.5, 4, y **Personalizado** para escribir 0.1–10. Se guarda como ``speed``. El multijugador sigue eligiendo al crear la sala.
- **Alcance**: ``config.py`` ``game_speed_type``; ``clientmain.py`` ``default_game_speed_menu``; ``DEFAULT_GAME_SPEED`` (5835–5837).

**Cambio: voz de accesibilidad y visualización en Opciones**

- **Problema**: la voz de accesibilidad solo estaba en el menú de partida / F4, y la vista de mapa solo con Ctrl+F2.
- **Cambio**: Opciones tiene **Voz de accesibilidad** y **Visualización**; Intro las conmuta. Misma config (``speech_enabled``, ``display_enabled``). Ctrl+F2 y F4 del menú siguen.
- **Alcance**: ``clientmain.py`` ``options_menu``; ``DISPLAY_TOGGLE`` (5838).


1.4.9.3
--------

**Corrección: el espectador en multijugador robaba ids de entidad**

- **Problema**: crear el jugador espectador consumía ``world.get_next_id()``, así que las unidades entrenadas o construidas después tenían un id más alto que en la partida real. Las órdenes humanas eligen por id, así que el historial ``all_orders`` golpeaba el objetivo equivocado; el orden de ``active_objects`` por id también podía divergir.
- **Cambio**: tras crear el espectador se restaura la secuencia numérica de ids y se le marca ``pure_spectator``. Sigue sin consumir ``world.random`` ni ocupar un hueco de jugador.
- **Alcance**: ``game.py`` ``_create_spectator_player``; prueba headless ``test_multiplayer_spectate.py``.

**Corrección: el espectador repetía «está espectando» y luego se quedaba mudo**

- **Problema**: el retraso de puesta al día oscilaba en el umbral y volvía a anunciar ``YOU_ARE_SPECTATING``. Restaurar el audio solo con cola 1 dejaba el espectador en vivo mudo (la cola suele quedar en 2–3); flechas/Tab/F10 parecían muertas hasta volver al vestíbulo.
- **Cambio**: se anuncia una sola vez y se restaura el audio al estar dentro del umbral; ``spectate_success`` tardío se ignora en silencio. En partida, ``spectator_joined`` / ``spectator_left`` se anuncian en vez de un WARNING.
- **Alcance**: ``game_interface_base.py``, ``worldclient.py``.

**Corrección: al entrar no había casilla y las flechas no hacían nada**

- **Problema**: el espectador puro no tiene unidades, así que ``interface.place`` quedaba vacío hasta PageUp / PageDown.
- **Cambio**: la cámara abre en la casilla inicial de un jugador real.
- **Alcance**: ``game_navigation._initial_observer_place``.

**Cambio: una lista de salas en el vestíbulo, contraseña opcional para unirse y espectar**

- **Problema**: pública/privada era confuso, y espectar vivía en otro menú. «Pública» invitaba a todos; las privadas solo por invitación.
- **Cambio**: al crear ya no se elige pública/privada: después del mapa/velocidad/tregua se pone contraseña o se omite. El vestíbulo tiene una **lista de salas**: las que esperan se pueden unir o espectar (el espectador espera a que el anfitrión arranque), las empezadas se espectan. Las salas con contraseña siguen en la lista; unirse y espectar piden la clave. Los invitados no la necesitan al unirse. El anfitrión sigue pudiendo invitar.
- **Alcance**: ``serverroom.py``, ``serverclient.py``, ``clientservermenu.py``, ``room_password.py``; prueba ``test_open_rooms_lobby.py``.

**Corrección: la espera de espectador no tenía salir y Esc no hacía nada**

- **Problema**: el menú de espera no aplicaba ``make_menu()``, así que no había opciones. Esc solo confirma el último ítem.
- **Cambio**: al entrar se aplica «salir / dejar esta partida»; Esc lo confirma como en el menú de invitado.
- **Alcance**: ``clientservermenu.py`` ``WaitingToSpectateMenu``.

**Corrección: «está espectando» se cortaba con el anuncio de casilla**

- **Problema**: al terminar el catch-up, ``voice.info()`` encolaba ``YOU_ARE_SPECTATING`` y el siguiente ``voice.item()`` lo interrumpía.
- **Cambio**: se habla con ``voice.alert()`` para que termine antes de los ítems; sigue anunciándose una sola vez.
- **Alcance**: ``game_interface_base.py`` ``_update_catch_up_audio``.


1.4.9.2
--------

**Cambio: rebote por reglas (Glaive del Mutalisk)**

- **Problema**: el motor tenía splash circular y penetración en línea, pero no un salto a enemigos cercanos con daño decreciente; el Mutalisk era de un solo objetivo.
- **Cambio**: ``rdg_bounce`` / ``mdg_bounce`` (saltos extra), ``*_bounce_range`` (0 = alcance de ataque), ``*_bounce_decay`` (porcentaje que queda; 0 = 33, p. ej. 9→3→1). Solo tras el impacto principal; no hiere aliados; no se golpea dos veces en la misma cadena; filtros ``rdg_targets``.
- **Alcance**: ``combat/bounce.py`` y combate; Mutalisk StarCraft ``rdg_bounce 2``, alcance 3, decay 33.

**Cambio: Lurker y Coloso StarCraft con penetración en línea**

- **Problema**: existía ``rdg_pierce_line`` estilo escorpión AoE2, pero el mod no tenía Lurker ni Coloso.
- **Cambio**: Lurker Den + Lurker / Lurker enterrado (ancho 0.5); Robotics Facility / Robotics Bay + Coloso (ancho 0.6). El Hydralisk transforma y la larva puede mejorar; la IA expert / nightmare los construye.
- **Alcance**: ``mods/starcraft/rules.txt``, UI, IA.

**Cambio: extras del escorpión AoE2 al 50 % tras la armadura**

- **Problema**: los golpes extra de penetración usaban daño completo, no el original (objetivo apuntado lleno, el resto la mitad tras armadura, como flecha desviada).
- **Cambio**: ``rdg_pierce_decay`` / ``mdg_pierce_decay`` es el porcentaje que queda en extras tras la armadura; 0 = 100 %. Escorpión / Escorpión pesado usan 50. Lurker / Coloso lo omiten y siguen a pleno en la línea.
- **Alcance**: ``combat/pierce_line.py``, ``hit_scale`` de ``receive_hit``; ``mods/aoe2/rules.txt``.

**Cambio: la pantalla de atributos muestra penetración en línea, rebote y campos de pasto**

- **Problema**: penetración en línea, rebote y el pasto AoE2 solo existían en reglas; la pantalla de atributos no los listaba.
- **Cambio**: si las reglas están puestas, lista los campos (omite los vacíos):

  - Penetración: ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``, ``*_pierce_decay`` (0 muestra 100 %)
  - Rebote: ``rdg_bounce`` / ``mdg_bounce``, ``*_bounce_range``, ``*_bounce_decay`` (0 muestra 33 %)
  - Pasto / generación: ``spawns_unit``, ``larva_spawn_time``, ``larva_cap``, ``spawn_player_cap``, ``spawn_immediate``; almacenable ``storable_resource_types``; oveja ``claimable``; pastor ``can_herd``

- **Alcance**: pantalla de atributos, ``msgparts`` 5800–5821.

**Cambio: las mejoras de línea reescriben la cola de producción (AoE2 DE)**

- **Problema**: investigar Onager solo transformaba mangoneles en el campo; los que seguían en cola en el taller salían como mangoneles.
- **Cambio**: al completar, las órdenes ``train`` de la misma línea pasan a la forma nueva; al salir se resuelve el nivel más alto desbloqueado. Coste y tiempo restante ya pagados no cambian.
- **Alcance**: ``apply_unit_line_upgrade``, ``TrainOrder.complete``.

**Corrección: los exploradores águila aztecas no pasaban a guerreros águila**

- **Problema**: la línea de milicia tenía ``can_upgrade_to man_at_arms``; el explorador águila tenía ``can_upgrade_to`` vacío. Investigar guerrero águila no transformaba a ``aztec_eagle_scout``.
- **Cambio**: ``eagle_scout`` → ``eagle_warrior`` → ``elite_eagle_warrior``; jaguar → élite. El águila azteca de Edad Oscura ``is_a eagle_scout`` hereda la cadena.
- **Alcance**: ``mods/aoe2/rules.txt``.


1.4.9.1
--------

**Corrección: el PC de CrazyMod en pra1 se congelaba en el ayuntamiento**

- **Problema**: ``get chatelet 10 serf`` no terminaba: el ayuntamiento propio se trataba como soldado reservado para el cuartel, y los trabajadores que lo construyen contaban como cuartel ya poseído; el PC solo imprimía ``vermine_nm_loop``.
- **Cambio**: las líneas ``get`` de edificios propios se completan; un ayuntamiento de trabajador no es un cuartel. Las invocaciones por habilidad (``can_use_skill`` → ``termitiere``) cuentan como fabricantes.
- **Alcance**: plan del PC y fabricantes; la IA zerg de CrazyMod quita ``get larve`` extra (el criadero genera larvas).

**Corrección: habilidades sin objetivo (larva) no hacían nada**

- **Problema**: ``effect_target`` vacío dejaba ``UseOrder`` sin objetivo (``a_larve`` de CrazyMod).
- **Cambio**: sin objetivo / ``self`` se aplica al lanzador.
- **Alcance**: ``worldorders/skills.py``.

**Cambio: unidades a distancia de CrazyMod con velocidad de proyectil**

- **Problema**: faltaba ``rdg_projectile_speed``; los disparos impactaban al instante.
- **Cambio**: se añade ``rdg_projectile`` / ``rdg_projectile_speed`` según el alcance.
- **Alcance**: ``mods/crazyMod9beta10/rules.txt``.

**Cambio: la IA de StarCraft usa los nombres del mod**

- **Problema**: ``ai.txt`` pedía ``peasant`` / ``footman`` / ``townhall`` del paquete base.
- **Cambio**: scripts terran/protoss/zerg con SCV, sonda, zángano, marine, etc. ``addon_grants_train`` cuenta como fabricante (``get tank`` construye la fábrica).
- **Alcance**: ``mods/starcraft/ai.txt`` y búsqueda de fabricantes.

**Cambio: mapas StarCraft con minerales/vespeno; el peasant inicial aparece**

- **Problema**: mapas con ``goldmines`` / ``woods``; ``peasant`` inicial no existe (``couldn't create an initial unit``).
- **Cambio**: mapas multijugador con ``mineral_field`` / ``geyser``; la tabla de facción mapea ``peasant`` a SCV / sonda / zángano.
- **Alcance**: mapas multi, ``equivalent_type``, parseo inicial.

**Cambio: tiempos y recolección StarCraft alineados con SC2 Faster**

- **Problema**: tiempos y recolección seguían más cerca de SC1.
- **Cambio**: SC2 Faster (5 minerales, 4 gas / 2 agotado, géiser 2250); proyectiles a distancia.
- **Alcance**: ``mods/starcraft/rules.txt``.

**Corrección: el PC principiante en jl1 alternaba oro y madera**

- **Problema**: el feudal pedía oro y madera; cada turno robaba a los mismos campesinos, los viajes no acababan.
- **Cambio**: no se roba a un trabajador de otro recurso que aún falta y no supera su tope.
- **Alcance**: ``_send_workers_toward_resources``.

**Corrección: ``time_cost -5`` feudal saltaba 2 y 8 en la barra**

- **Problema**: el bonus se aplicaba dos veces (jugador + ``_phase_bonus_pool``); el peón de 12s pasaba a 2s y la barra ``0 1 3 4 5 6 7 9 10``.
- **Cambio**: el pozo solo guarda stats de combate; se rellenan los ``completeness`` 0–10 saltados.
- **Alcance**: pozo de era y ``ProductionOrder``.

**Corrección: el primer desbloqueo de logro anunciaba también repetición**

- **Problema**: ``evaluate_new_unlocks`` escribía ``once_keys`` antes de ``evaluate_repeat_completions``.
- **Cambio**: primero repeticiones, luego desbloqueos. El soldado raso sigue con 0 huecos de cartas (el teniente tiene 1).
- **Alcance**: ``process_game_end_achievements``.

**Corrección: pintar con la paleta de terreno de la consola**

- **Problema**: el bosque no tenía ``is_dynamic 1`` y al pintar se bloqueaba el terreno. El pincel de mina soltaba la madera. Pintar bosque tras un lago buscaba espacio como agua.
- **Cambio**: bosque dinámico; la paleta cambia tierra/agua antes de colocar recursos; minas y árboles sin colisión.
- **Alcance**: aplicación de paleta, ``ensure_resources``; ``forest`` en base / AoE2 / StarCraft / CrazyMod.


1.4.9.0
--------

**Cambio: ``*_vs`` de splash se aplica a la unidad alcanzada**

- **Problema**: ``mdg_splash_vs`` / ``mdg_splash_decay_min_vs`` usaban el objetivo apuntado para cambiar todo el pozo.
- **Cambio**: ``mdg_splash`` / ``rdg_splash`` sigue repartido al azar; ``*_splash_vs`` y ``*_splash_decay_min_vs`` aplican a **cada unidad salpicada**. Igual en splash de carga.
- **Alcance**: ``combat/splash.py`` y splash de carga.

**Equilibrio: restaurar el daño DE de la línea mangonel**

- **Problema**: 1.4.8.7 recortó ~25% asumiendo splash completo por objetivo; el splash es un pozo compartido.
- **Cambio**: Mangonel / Onager / Siege Onager vuelven a 40 / 50 / 75; ``mdg_splash`` igual al cuerpo a cuerpo.
- **Alcance**: línea mangonel en ``mods/aoe2/rules.txt``.

**Equilibrio: el splash de AoE2 iguala el ataque principal**

- **Problema**: mangonel ya usaba ``mdg_splash`` = cuerpo a cuerpo; cañón de asedio, galeones de cañón, dromon, barcos tortuga, Warwolf, elefantes/arietes y torres de bombardas tenían splash ``1`` (bandera).
- **Cambio**: el pozo de splash iguala ``mdg`` / ``rdg``; Logistica 9/12; torre de bombardas 120 y radio 0.5. Petardos y barcos de demolición ya estaban bien.
- **Alcance**: ``mods/aoe2/rules.txt``.

1.4.8.9
-------

**Corrección: crash del PC al requisar barcos de pesca para andamios terrestres (``KeyError: deep_fish()``)**

- **Problema**: la reparación de obras olvidadas requisaba cualquier ``Worker``, incluidos barcos en ``deep_fish``. ``_gathered_deposits`` solo cuenta campesinos; al restar petaba.
- **Cambio**: los trabajadores de agua no van a andamios de tierra; el recuento de recolección solo baja si la orden se acepta y el yacimiento estaba registrado.
- **Alcance**: ``order()`` de reparación del PC.

**Corrección: las reglas de perforación del escorpión se perdían al cargar**

- **Problema**: ``rdg_pierce_line`` / ``rdg_pierce_width`` estaban en reglas y tablas, pero ``Soldier``/``Creature`` no tenían el atributo; se advertía y se borraban.
- **Cambio**: campos de perforación en ``Creature`` y en instancias; escorpión / escorpión pesado aoe2 conservan los flags.
- **Alcance**: atributos de unidad y escorpiones aoe2.

**Corrección: recolectar pez de costa en memoria de niebla avisaba al mover el objeto real**

- **Problema**: sin visión del agua, el gather usaba una copia de ``shore_fish``; al vaciarla ``delete()`` de la copia y el aviso ``Will move the real object instead of its memorized version``.
- **Cambio**: ``extract_resource`` sobre memoria descuenta el yacimiento real.
- **Alcance**: recolección de yacimientos (pez de costa, etc.).

**Corrección: el menú de unidades (mago, etc.) petaba si ``player`` era None**

- **Problema**: ``EnableAutoExplore.is_allowed`` leía ``unit.player.is_human``; memoria de niebla, cadáveres y unidades sin dueño tienen ``player is None`` y lanzaban ``AttributeError``. ``_menu`` abortaba el bucle y se perdían órdenes posteriores.
- **Cambio**: si falta ``player``, se trata como no humano y se devuelve False; misma guarda al desactivar auto-exploración y en la del PC.
- **Alcance**: menú de órdenes de unidad.

**Corrección: crash del menú de órdenes en EnableAutoExplore cuando ``player`` es None (mago)**

- **Problema**: ``EnableAutoExplore.is_allowed`` leía ``unit.player.is_human``; memoria de niebla, cadáveres y unidades sin dueño tienen ``player is None`` y lanzaban ``AttributeError``. ``_menu`` capturaba todo el bucle y se perdían órdenes posteriores.
- **Cambio**: devolver False si ``player`` es None o no es humano; misma guarda al desactivar auto-exploración y en auto-exploración del PC.
- **Alcance**: menú de órdenes (conmutador de auto-exploración).


1.4.8.8
-------

**Cambio: revertir «ataque cuerpo a cuerpo 0 vs armadura negativa»**

- **Problema**: permitir ``mdg 0`` contra ``mdf`` negativo hacía raro el «ataque 0».
- **Cambio**: ``mdg == 0`` (sin explode) ya no inicia melee; se mantiene ``max(1, ataque−armadura)``. Los arqueros aoe2 sin ``mdg_range`` melee gratis.
- **Alcance**: puertas de ataque / caché AI / arqueros aoe2. Perforación de escorpión y nerf de mangonel de 1.4.8.7 se conservan.

**Mejora: atributos «tecnologías usables» filtradas a las investigables de la civ**

- **Problema**: ``can_use_tech`` a menudo incluye tecnologías únicas ajenas para efectos, y los atributos las leían.
- **Cambio**: la lista solo muestra lo que esta civ puede investigar (más ``team_share_research`` aliado y ya investigado). La aplicación real y el compartir aliado no cambian. Techs de arquería del aserradero compartido (base / crazyMod) siguen listándose.
- **Alcance**: lista de atributos e índices de navegación.


1.4.8.7
-------

**Mejora: perforación en línea de proyectiles (escorpión), por reglas**

- **Problema**: el escorpión de AoE2 debe atravesar unidades en la línea de tiro; solo había splash circular.
- **Cambio**: ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``. Golpes extra a lo largo del segmento (sin el objetivo principal). aoe2 scorpion / heavy scorpion con ``rdg_pierce_line 1``.
- **Alcance**: combate y escorpiones aoe2; el splash sigue sin aliados.

**Equilibrio: menos daño de mangonel (sin fuego amigo)**

- **Problema**: el splash ya no hiere aliados; el daño base DE dejaba la línea demasiado fuerte.
- **Cambio**: mangonel / onager / siege onager ~−25% (40→30, 50→38, 75→56).
- **Alcance**: ``mods/aoe2/rules.txt``.

**Mejora: ataque cuerpo a cuerpo 0 puede golpear armadura negativa (arietes)**

- **Problema**: ``mdg 0`` se bloqueaba antes de la armadura; arietes con ``mdf -3`` no recibían 3.
- **Cambio**: con ``mdg_range`` (o explode) se permite melee si el daño tras armadura > 0. Monjes sin rango melee no. Arqueros / skirmishers / arqueros a caballo con ``mdg_range 1``. 0 vs 0 armadura sigue en mínimo 1.
- **Alcance**: puertas de ataque / aoe2 arqueros y arietes.


1.4.8.6
-------

**Corrección: aoe2 Hand Cannoneer entrenable en el Campo de tiro**

- **Problema**: los Hand Cannoneer no salían en la lista de entrenamiento; algunas civs los ponían en ``can_research`` y solo pedían Edad Imperial (sin Química).
- **Cambio**: ``hand_cannoneer`` exige ``imperial_age chemistry``; el Campo genérico y las civs que lo tienen lo listan en ``can_train`` (bizantinos, japoneses, francos, teutones, portugueses, malíes, …). Britanos, chinos, mongoles, vikingos, vietnamitas, aztecas y celtas siguen sin ellos (árbol DE).
- **Alcance**: ``mods/aoe2/rules.txt`` Campo de tiro y Hand Cannoneer.

**Corrección: el detalle de «puede construir» resuelve el edificio de la civ**

- **Problema**: el menú guarda nombres genéricos (p. ej. ``aoe_castle``). Al abrir el detalle se leía el cascarón genérico: el castillo britano solo mostraba el Trebuchet hasta construirlo (Longbowman).
- **Cambio**: ``_show_unit_detail`` usa ``resolve_buildable_type`` (``aoe_castle`` → ``briton_castle``, etc.) para que entrenar/investigar coincidan con el edificio real.
- **Alcance**: detalles de tipo desde puede construir / puede entrenar.

**Corrección: el detalle de tipo aplica bonos de edad / civ**

- **Problema**: al mirar milicia, arquero, etc. desde puede entrenar solo se veían stats base, sin armadura de proyectil malí, alcance britano u otros bonos ``on_phase``.
- **Cambio**: el proxy de detalle reutiliza ``Player._phase_bonus_pool`` con ``Phase.apply_pool_*`` como al crear unidades.
- **Alcance**: detalles de tipo (no tech/habilidad).


1.4.8.5
-------

**Mejora: el recuadro prioriza militares; los sprites apiñados se reducen**

- **Problema**: el arrastre seleccionaba aldeanos, soldados y edificios a la vez, a diferencia de Age of Empires II DE. Los PNG de ``ui/map`` son mayores que el punto de colisión y se tapan.
- **Cambio**: si el recuadro tiene militares (``class soldier``), solo militares; si no, trabajadores (``class worker``); si no, edificios. El clic no cambia. Los sprites se encogen si hay muchos en la misma casilla, con un punto de color de equipo.
- **Alcance**: recuadro con ratón Ctrl+F2 / F8 y dibujo del mapa. Teclado y TTS igual.

**Mejora: animaciones spritesheet de unidades (Spine opcional)**

- **Problema**: ``ui/anims/`` solo tenía documentación; Ctrl+F2 seguía con PNG estáticos de ``ui/map``; ``go`` no activaba ``walk``.
- **Cambio**: ``python tools/gen_unit_anims.py`` genera hojas 4 direcciones (idle/walk/attack/gather) para tipos móviles base y aoe2. ``go``/``use`` → ``walk``; ``dirs: 4`` en meta; ``backend: spine`` vuelve al spritesheet de la misma carpeta sin runtime.
- **Alcance**: ``game_unit_anim.py``, ``res/ui/anims/``, ``mods/aoe2/ui/anims/``. TTS / juego a ciegas sin cambios.

**Corrección: granja en auto-cultivo ya no muestra «empezar auto-cultivo» de más**

- **Problema**: con la granja ya en modo auto-cultivo (incluso entre replantíos), la carta mostraba «empezar auto-cultivo» y «parar cultivo» a la vez.
- **Cambio**: si ``current_production_mode`` ya es ``auto``, ocultar el comando de inicio y dejar solo parar. Igual para ``auto_produce`` / ``manual_produce``.
- **Alcance**: menús ``AutoCultivateOrder`` / ``StopCultivateOrder`` y producción equivalente.

**Corrección: el comando por defecto del aldeano sobre granja es gather, no go**

- **Problema**: con un aldeano seleccionado, clic derecho en granja emitía ``go`` en lugar de ``gather``.
- **Cambio**: ``Worker.get_default_order`` comprueba depósitos/edificios recolectables (granjas con ``can_gather_building``) antes del ``go`` genérico para unidades vivas.
- **Alcance**: clic derecho por defecto del aldeano; objetivos vacíos o prohibidos siguen con ``go``.

**Corrección: alias gratuitos de granja francos aoe2 no cumplían el requisito padre**

- **Problema**: tras investigar ``frank_horse_collar`` (``is_a horse_collar``, gratis), Arado pesado / Rotación seguían pidiendo ``horse_collar`` / ``heavy_plow``. Otras civs con el nombre padre iban bien.
- **Cambio**: ``player.has()`` cuenta ``is_a`` / ``expanded_is_a`` de mejoras investigadas. Techs de granja gratis (bono franco) sin cambio.
- **Alcance**: requisitos de investigación (alias de civ).


1.4.8.4
-------

**Rendimiento: vista de mapa Ctrl+F2 y simulación del mundo**

- **Problema**: con Ctrl+F2 y muchos ordenadores, pintar el mapa y actualizar el mundo no llegaban a tiempo real. La ruta caliente usaba ``__getattr__`` de EntityView, reconstruía la niebla cada tick y reclasificaba cada objeto y sprite. ``decide`` y el espacio de casilla corrían demasiado.
- **Cambio**: la vista lee tipo y coordenadas del modelo (``stamp_map_view_cache``, ``_map_kind``). ``display_objects`` pinta por capas; los recursos omiten animación de unidad y barras de vida. La niebla salta objetos sin cambio y guarda ``is_memory``, sprites y etiquetas. ``memory_for_display`` se guarda por tick. Unidades ociosas retrasan ``decide`` (``_next_decide_time``). Las casillas guardan ``used_square_space``. Los estados sin combate van por una vía barata. El recorte por celda (``visible_cell_range``) se probó; el bucle de objetos fue más lento y no se conservó.
- **Alcance**: vista Ctrl+F2, niebla del cliente, actualizaciones del ordenador. TTS y reglas de juego sin cambios.


1.4.8.3
-------

**aoe2: arte HUD / mapa y conjuntos de arquitectura DE**

- **Problema**: el mod Age of Empires II DE no tenía PNG propios de carta de órdenes ni de mapa; Ctrl+F2 caía en el arte base. Las civilizaciones comparten tipos como ``militia``; un miliciano distinto por civ no coincide con DE (conjuntos regionales, no IDs por civ).
- **Cambio**: las capas de recursos posteriores cubren PNG del mismo nombre. aoe2 incluye ``mods/aoe2/ui/icons`` y ``ui/map``. Geometría inicial: ``python tools/gen_aoe2_hud_icons.py``; PNG propias no necesitan el script. ``ui/architecture.txt`` agrupa civs (p. ej. ``western_european``); se busca ``ui/map/<conjunto>/<tipo>.png``. Civs del mismo conjunto comparten arte. Depósitos y fauna neutrales quedan en la raíz. Los RGB (``rim``, etc.) solo afectan al generador. Mods estilo StarCraft con tipos distintos por raza (``marine`` / ``zergling`` / ``zealot``) no necesitan subcarpetas de arquitectura.
- **Alcance**: carga de PNG HUD/mapa; arte aoe2 y ``architecture.txt``. TTS / juego a ciegas sin cambios.


1.4.8.2
-------

**aoe2: pesca según rules (peces de orilla / mar profundo)**

- **Problema**: el mod DE solo tenía viveros de barco pesquero. No había yacimientos de orilla ni de mar profundo; los aldeanos no pescaban desde tierra. El muelle y el vivero eran feudales, así que no había pesca en Edad Oscura.
- **Cambio**: un yacimiento con ``gather_from_shore 1`` lo recolectan trabajadores de tierra en una casilla terrestre adyacente. aoe2: ``shore_fish`` (200 comida) y ``deep_fish`` (225, solo barcos). Redes de enmalle y el ritmo japonés cubren las tres fuentes. Muelle y vivero en Edad Oscura (transporte / galera / nao mercantil siguen feudales).
- **Alcance**: recolección/IA/mapas aleatorios; rules aoe2 y mapas de agua.

**Corrección: recolectar / construir / reparar / depositar suenan en el objetivo**

- **Problema**: los bucles iban en el aldeano, así que el estéreo sonaba en el trabajador. La pesca de orilla sonaba en tierra.
- **Cambio**: ``noise_when_exploiting_*`` / ``noise_when_building`` (opcional ``noise_when_repairing``) en el trabajador; coordenadas en el yacimiento o edificio. ``store_resource1`` … en aldeano/barco **o** almacén; si hay ambas, gana el trabajador. Estéreo en el almacén. ``store_resource_0`` está obsoleto.
- **Alcance**: todos los mods.

**Corrección: los mapas con solo starting_squares siempre usaban un nacimiento fijo**

- **Problema**: los mapas multijugador de AoE2 DE listan ``starting_squares`` y omiten ``starting_units`` (valores de la raza). Los huecos vacíos perdían la casilla, así que el centro urbano / aldeanos de la facción usaban siempre ``starting_squares[índice_de_jugador]``. ``random_starts 1`` no barajaba.
- **Cambio**: cada ranura de nacimiento recuerda su casilla. Con inicios aleatorios por defecto se barajan esas casillas y los valores de la raza caen en la sorteada. ``random_starts 0`` sigue el orden de la lista.
- **Alcance**: todos los mapas que usan ``starting_squares`` sin unidades por ranura (incluido aoe2).


1.4.8.1
-------

**Mejora: el alcance al reclamar ovejas coincide con AoE2 DE (4 m + radios de colisión)**

- **Problema**: las ovejas usaban ``claim_range 12000`` (un cuadrado entero de 12 m), mucho más que el radio de búsqueda de DE (~4 casillas). El cuadrado de 12 m es una celda de navegación para juego sin ver; las coordenadas siguen continuas, unos 1 m por casilla. El reclamo comparaba solo centros, sin radios de colisión.
- **Cambio**: las ovejas usan ``claim_range 4000`` (~4 m). Reclamar/robar es borde a borde: distancia entre centros ≤ ``claim_range`` + ambos ``radius`` (175 mm cada uno si hay colisión).
- **Alcance**: rules base y ovejas aoe2; todo ganado ``claimable`` con ``claim_range``.

**Corrección: los nombres numéricos de partidas/replays se leían como IDs de tts.txt**

- **Problema**: al renombrar una partida a ``1`` se decía «estás» / «you are» (id 1 de tts.txt) en lugar del número 1. Lo mismo en los replays.
- **Cambio**: los nombres elegidos por el jugador (partidas y replays, incluida la confirmación al borrar) usan ``literal_text_msg``. Los nombres automáticos ``replayN_timestamp`` y los archivos antiguos solo con marca de tiempo larga siguen leyendo la hora y el índice.
- **Alcance**: menús de cargar partida y de replay.


1.4.8.0
-------

**Corrección: la TTS de un buff al recogerlo leía milipuntos de vida**

- **Problema**: en td2, recoger una espada decía daño cuerpo a cuerpo +7000000. Las rules ``stat mdg`` / ``v 7000`` guardan 7_000_000 milipuntos; el anuncio tomaba ese valor interno como el de pantalla.
- **Cambio**: los buffs temporales dividen las stats de precisión (hp, mdg, etc.) por ``PRECISION`` antes de la TTS. Los acumuladores de producción siguen en unidades de pantalla.
- **Alcance**: TTS al ganar un buff en todos los mods.

**Ordenador: atraer presas que contraatacan al depósito de comida antes de matarlas**

- **Problema**: los aldeanos ociosos atacaban animales ``is_huntable`` in situ. Los jabalíes con ``pursue_attacker`` pelean en el campo. No había «golpear una vez y arrastrar a casa».
- **Cambio**: un cazable que no es ``herdable`` / ``claimable`` y tiene ``pursue_attacker`` (jabalíes aoe2) recibe un golpe; el aldeano corre a un edificio que guarda el recurso 3 (centro urbano, molino, etc.) y lo mata allí. Los cazables que no contraatacan (ciervos) se siguen matando in situ. Las ovejas se siguen llevando al depósito. Sin nombres de tipo fijos. El corredor no se gira a pelear de camino.
- **Alcance**: jugadores ordenador; mods con esos flags (incluido aoe2).

**Asignación de teclas: estado del recurso 4**

- **Problema**: aoe2 ya asignaba la piedra a Mayús+X, pero el catálogo de reasignación solo listaba los recursos 1–3.
- **Cambio**: los catálogos global y clásico incluyen el estado del recurso 4. En aoe2 el valor por defecto sigue siendo Mayús+X.
- **Alcance**: reasignación de teclas; id TTS 5508.

**Teclas clásicas: Mayús derecho+C / B copian la voz secundaria**

- **Problema**: las teclas por capas podían copiar la voz secundaria al portapapeles; el ``legacy_bindings.txt`` clásico no tenía esas teclas.
- **Cambio**: ``res/ui`` y ``mods/aoe2/ui`` ``legacy_bindings.txt`` añaden Mayús derecho+C copiar y Mayús derecho+B añadir al portapapeles la voz secundaria.
- **Alcance**: esquema de teclas clásico.


1.4.7.9
-------

**Mejora: al reclamar/robar ovejas se anuncia la civilización y si es enemigo**

- **Problema**: reclamar o robar una oveja siempre decía «oveja , reclamado», sin saber qué civilización se la llevaba.
- **Cambio**: la reclamación propia sigue corta. Si un enemigo se la lleva (y ves al que reclama) se dice «oveja reclamada bizantinos , enemigo»; un aliado nombra la civ y «aliado». Mods de una sola facción omiten el nombre de civ pero siguen diciendo enemigo/aliado. En la niebla, si no ves al que reclama, no hay anuncio.
- **Alcance**: TTS del cliente; todos los mods con ganado ``claimable`` (incluidas las ovejas aoe2).

**Mejora: al capturar edificios se anuncia el nombre y la cantidad (igual que las muertes)**

- **Problema**: la captura solo reproducía un sonido, sin decir qué edificio se había tomado.
- **Cambio**: si pierdes el tuyo: «1 ayuntamiento ocupado». Si tomas uno enemigo: «1 centro urbano capturado». Varios del mismo tipo en el mismo momento: «2 cuarteles ocupados / capturados». La cantidad sigue las muertes: los tipos con número la incluyen; los ``no_number`` únicos omiten el «1». Ver a otros capturar sigue siendo solo el sonido.
- **Alcance**: TTS del cliente; todos los edificios capturables (incluidos muros, puertas y centros urbanos aoe2).


1.4.7.8
-------

**Corrección: el servidor seguía mostrando la partida en curso después de terminar**

- **Problema**: al acabar una partida multijugador, el cliente a veces no enviaba ``quit_game`` (error al leer la puntuación, fallo al cargar el mapa, o el comando iba después del recuento). Si alguien seguía en el vestíbulo, la sala permanecía en la lista de partidas en curso / espectar.
- **Cambio**: se da de baja la sala antes de la TTS de puntuación; al salir de la UI de partida se envía ``quit_game`` otra vez si no se había enviado. Los comandos del vestíbulo y una limpieza del servidor cierran salas sin nadie jugando. Un ``quit_game`` duplicado desde el vestíbulo se ignora (sin aviso).
- **Alcance**: servidor y cliente multijugador.

**Empaquetado: la instalación de Windows ya no duplica Tcl/Tk**

- **Problema**: ``tcl8`` / ``tcl8.6`` / ``tk8.6`` estaban en la raíz de la instalación y también en ``share/``, copias idénticas, unos 5 MB de más.
- **Cambio**: solo se conserva la copia de cx_Freeze en ``share/``; la ventana de actualización prefiere ``share/``.
- **Alcance**: paquete de Windows.


1.4.7.7
-------

**Motor: andanada de guarnición del edificio (por reglas, sin tipo de arma)**

- **Problema**: los centros urbanos aoe2 vacíos seguían disparando (daño a distancia del edificio), a diferencia de DE. Las +5 disparos teutones con el centro vacío y Tigui maliense +8 no se podían expresar en rules. Un campo llamado arrows no valdría para un edificio de cañón.
- **Cambio**: con ``garrison_shots 1``, disparos = ``base_shots`` + unidades de guarnición que disparan, tope ``max_garrison_shots`` (por defecto 10). Un edificio vacío con ``base_shots 0`` no dispara; teutones ``base_shots 5``; Tigui usa el ``effect bonus base_shots 8`` existente. El tipo de daño sigue siendo el ``rdg`` del edificio (flecha, cañón u otro a distancia). La andanada es del edificio, no disparos de pasajeros. El motor no comprueba nombres de civilización.
- **Alcance**: todos los mods; los centros urbanos aoe2 lo activan. Castillos y torres siguen disparando vacíos.

**aoe2: malienses**

- **Problema**: el mod no tenía la civilización maliense.
- **Cambio**: decimotercera civ. Edificios −15 % de madera salvo granjas; milicia/lanceros del cuartel +1/+2/+3 de armadura perforante Feudal/Castillo/Imperial (no Gbeto); aldeanos entregan +10 % de oro; investigación universitaria de equipo 80 % más rápida (``team_on_phase`` + ``time_cost -44%``). Unidad única Gbeto; tecnología de castillo Tigui (200 comida 300 madera, ``base_shots`` +8 en el centro); tecnología imperial Farimba (cuerpo a cuerpo de caballería +5). Introducción ``8532``.
- **Alcance**: mod aoe2.

**aoe2: las cáscaras de edificios de civ no tenían título de estilo**

- **Problema**: cáscaras como ``malian_barracks`` no heredaban título, así que el edificio terminado no tenía nombre. Granjas/centros teutones y el monasterio bizantino tampoco tenían ``is_a`` en ``style.txt``.
- **Cambio**: esas cáscaras apuntan con ``is_a`` al edificio genérico; una prueba exige títulos en cáscaras posteriores.
- **Alcance**: estilo UI aoe2.


1.4.7.6
-------

**aoe2: bonos de las doce civilizaciones alineados con Definitive Edition actual**

- **Problema**: los bonos aún seguían una instantánea ~2022 (p. ej. chinos 10/15/20 % en tecnologías, centros urbanos 10 de población), no la DE actual. El motor tampoco podía expresar investigación compartida de equipo, robo de rebaño vigilado ni descuentos de coste por edad.
- **Cambio**: las doce civs (britanos, francos, chinos, mongoles, bizantinos, japoneses, teutones, vikingos, vietnamitas, portugueses, aztecas, celtas) usan bonos y bonos de equipo DE actuales. Donde las rules no bastaban, el motor añade campos sin nombres de civ: ``team_on_phase``, ``grant_tech_on_phase``, ``team_share_research`` (tecnología y edificios anfitrión opcionales, p. ej. hondero imperial vietnamita para aliados), ``team_farm_food_pct``, ``reveal_enemy_town_centers``, ``research_cost_zero_slot`` / ``research_time_percent``, ``gather_byproduct``, resistencia de equipo a la conversión, etc.
- **Alcance**: mod aoe2; los campos nuevos sirven a otros mods.

**Motor: reclamar / robar rebaños (por reglas)**

- **Problema**: la pertenencia por proximidad ``claimable`` no estaba en el bucle de unidad. El «no se puede robar un rebaño vigilado / sí se puede si no está protegido» de AoE2 no tenía flags.
- **Cambio**: los animales ``claimable`` neutrales pasan a un jugador no neutral cercano. El rebaño con dueño se puede robar: cualquiera si no hay guarda; bloqueado si hay una unidad viva del dueño; raza ``herdable_steal_ignore_guards 1`` ignora esa guarda; ``herdable_steal_protected 1`` (por defecto 0) impide ese bono sobre tus propios animales. El motor no comprueba nombres de civilización.
- **Alcance**: todos los mods; los celtas aoe2 activan ambos flags.

**aoe2: inicio en Edad Oscura como AoE2 (incluidos chinos)**

- **Problema**: el inicio era 1 aldeano, una casa y sin explorador. Los chinos tenían 4 aldeanos (+3 sobre una base de 1), no los 6 + explorador de DE.
- **Cambio**: civs estándar: centro urbano + 3 aldeanos + caballería de exploración. Chinos: 6 aldeanos + explorador (−50 madera, −200 comida, centro 15 de población). Aztecas: 3 aldeanos + explorador águila, +50 oro. Sin casa inicial (población del centro urbano). Los guiones de campaña y aldeanos extra de dificultad de la IA no cambian.
- **Alcance**: ``starting_units`` / ``starting_resources`` por defecto de las razas aoe2.

**aoe2: textos del selector de facción en todos los idiomas del mod**

- **Problema**: las fichas G de civilización solo estaban en inglés y chino.
- **Cambio**: ids ``8520``–``8531`` en todos los paquetes UI de aoe2 (en, zh, de, fr, es, it, ru, be, pl, cs, sk, pt-BR, vi).


1.4.7.5
-------

**Corrección: la orden por defecto del aldeano sobre un edificio dañado no era reparar**

- **Problema**: el cambio de caza hacía que cualquier objetivo vivo con dueño fuera ``go``. Los edificios aliados dañados (y las obras) caían ahí, así que el aldeano caminaba en vez de reparar.
- **Cambio**: resolver primero la reparación por defecto en obras y objetivos ``is_repairable`` con ``hp < hp_max`` (sigue exigiendo ``can_repair`` / ``can_build``; se excluyen enemigos). Edificios intactos, fauna y enemigos siguen en ``go``.
- **Alcance**: orden por defecto de los trabajadores en todos los mods.


1.4.7.4
-------

**Rendimiento: velocidad de la tecla F al inicio (bucle del cliente)**

- **Problema**: Al inicio, muchos pasos/ambientes decodificando OGG por primera vez podían bloquear el cliente un fotograma largo, retrasar la siguiente petición al mundo y bajar la velocidad relativa de F.
- **Cambio**: Vaciar avisos del servidor con un presupuesto corto (dejar ``voila`` para el fotograma siguiente); repartir la animación de unidades; decodificar pasos/ambiente (prioridad ≤ −10) en segundo plano y no robar canales del mezclador.
- **Alcance**: cliente local en todos los mods.

**Límite de SFX: disparo/impacto, confirmación, pasos, noise en bucle**

- **Problema**: En combates densos el hilo principal seguía ejecutando notify / animación de sonidos que el mezclador no puede superponer.
- **Cambio**: Disparo/impacto como máximo 16 por tick (8 por casilla); ``order_ok`` / ``order_impossible`` 2 por tick; pasos 8 por oleada de animación (4 por casilla); noise en bucle como máximo 3 por tipo de unidad/edificio (los tipos no comparten tope; sin techo global de tipos). Muerte, caída, proporción de HP y alerta de unidad propia atacada no se limitan.
- **Alcance**: cliente local en todos los mods.

**Corrección: a veces no sonaban impacto, proporción de HP ni muerte**

- **Problema**: Evitar decodificar OGG en el hilo principal callaba el SFX de combate si aún no estaba en caché.
- **Cambio**: La reproducción no decodifica en el bucle. Se precargan estilos de combate (impacto / ``proportion_*`` / muerte, etc.) en segundo plano; si falta, se reintenta desde una cola breve. Se mantiene el vaciado de eventos.

**Corrección: tras el objetivo no se anunciaban coordenadas ni resumen de la casilla inicial**

- **Problema**: El primer refresco de cámara omitía el habla para no trabar la animación, guardaba la frase y nunca la decía.
- **Cambio**: Tras vaciar eventos del servidor, anunciar una vez la casilla inicial (coordenadas, terreno, aldeanos / casas / centro urbano / mina de oro, etc.).

**Corrección: el cuartel del res base entrenaba arqueros oscuros en vez de arqueros**

- **Problema**: La resolución de línea de entrenamiento al estilo AoE2 trataba cualquier ``can_upgrade_to`` como la forma que el edificio debía entrenar. El morph archer→darkarcher (torre de magos) se aplicaba al cuartel.
- **Cambio**: Solo las formas con ``line_upgrade`` / ``no_auto_upgrade`` sustituyen la ranura de entrenamiento (milicia→hombre de armas vive en las rules del mod aoe2). El cuartel base sigue entrenando arqueros; el arquero oscuro sigue siendo una mejora de arqueros existentes. Las ideas de un mod no deben reescribir el juego base ni los menús de otros mods.

**Corrección: Opciones → biblioteca de voz secundaria leía 5762 y 5778**

- **Problema**: al abrir el editor de voz secundaria desde Opciones se leían los ids ``5762`` / ``5778`` como dígitos, no como «biblioteca de voz secundaria» y la pista de teclas.
- **Cambio**: resolver msgparts antes de hablar. El editor es una lista de submenú normal; la voz del menú da el feedback para que un canal secundario silenciado no parezca una pantalla vacía.


1.4.7.3
-------

**Rendimiento: conteos y memo del turno de la IA**

- **Problema**: con muchos ordenadores, ``Computer.play`` recorría una y otra vez ``nb`` / ``future_nb`` y recalculaba edificios/reserva de madera de la línea get varias veces por turno.
- **Cambio**: índice de tipos por turno de IA; ``check_type`` más barato; memo de las consultas del plan (makers pendientes, madera, etc.), invalidado tras entrenar/construir. Sin cambiar combate ni percepción.
- **Alcance**: ordenadores en todos los mods.

**aoe2: IA por edades — entrena y ataca**

- **Problema**: ``mods/aoe2/ai.txt`` mezclaba edades en una sola get; el ahorro de comida aplazaba el ejército y el watchdog saltaba gets incompletos.
- **Cambio**: oleadas Dark / Feudal / Castle; el watchdog no corta la eco de la Edad Oscura; el ejército feudal de la línea actual no queda retenido por el castillo siguiente; tras el castillo, reserva madera para el taller de asedio sin congelar granjas. Scripts y dificultades actualizados.
- **Nota**: el avance de edad puede compartir el motor, pero el ahorro/oleadas de aoe2 siguen sus propias rules — otros mods con edades no tienen que comportarse igual.

**Corrección: el res base construía cuartel y no entrenaba**

- **Problema**: la lógica de «maker sin pagar» de aoe2 trataba makers unidad→unidad (``darkarcher``) y astilleros en mapas terrestres como edificios a ahorrar, aplazando peones/arqueros.
- **Cambio**: solo edificios reales; en mapas sin agua, ignora unidades/muelles acuáticos. El res base entrena y ataca con el cuartel listo; la reserva de madera del taller en aoe2 se mantiene.

**Corrección: ordenadores atrapados en la get feudal — no llegan a castillo / arietes**

- **Problema**: el plan mantiene a propósito el ejército feudal actual sin pulsar Edad de los Castillos. Si las tropas mueren en la base enemiga, el get nunca se completa. A la vez ``_watchdog_should_wait`` trataba la madera del taller posterior y la comida/madera de entrenamiento como «aún progresando», reiniciando el temporizador, de modo que el watchdog no saltaba la get feudal y no arrancaba la oleada de castillo (herrería, Edad de los Castillos, taller, arietes).
- **Cambio**: si la get actual ya no necesita una edad pero una oleada posterior sí necesita castillo, el temporizador solo espera edificios de producción de la línea actual sin pagar (cuartel / campo de tiro, etc.), no la madera del taller ni el entrenamiento. Las gets de asedio siguen pausando correctamente con el taller listo y madera de ariete pendiente.
- **Alcance**: ordenadores en todos los mods. Cualquier script aoe2 «ejército feudal → tropas/asedio de castillo» se beneficia.

**Corrección: los ordenadores no llevan las ovejas propias al centro urbano antes de matarlas**

- **Problema**: muchos mods (incluido aoe2) dejan ``can_herd 0`` y usan ``claimable``. La IA no enviaba ovejas propias como unidades controlables al depósito de comida, y las metía en ``auto_explore`` / oleadas de ataque, así que vagaban o morían en el campo en lugar de dejar ``food_livestock`` en el centro urbano.
- **Cambio**: el ganado propio (``herdable`` / ``claimable``) hace ``go`` solo al edificio que guarda comida; los aldeanos solo matan allí y luego recolectan. Ovejas neutrales claimable: primero ``go`` para reclamar. Quedan fuera de exploradores y luchadores idle. No exige ``can_herd``; el pastoreo por seguimiento sigue disponible.
- **Alcance**: ordenadores en todos los mods; ovejas aoe2 y pastos mongoles se benefician.


1.4.7.2
-------

**aoe2 / motor: empacar / desempacar el trabuquete (por reglas) + progreso proportion**

- **Problema**: las unidades asedio «packable» solo retrasaban el primer disparo tras moverse; no había estado real empacado/desempacado ni barra ``proportion_*``.
- **Cambio**: reglas ``packable``, ``unpack_time`` / ``pack_time``, opcionales ``packed_mdf`` / ``packed_rdf``, ``spawn_packed``. Empacado = solo mover; desempacado = solo atacar. Progreso ``completeness`` → ``proportion_*``. UI: empacar / desempacar.
- **Docs**: ``mod/modding.htm``.

**aoe2: corrección de Collar de caballo / Arado pesado / Rotación de cultivos duplicados en aldeanos**

- **Problema**: el ``can_use_tech`` del campesino incluía las mejoras de molino genéricas y los alias francos a coste 0 (``frank_horse_collar``, etc.). Los alias comparten título, así que la pantalla de atributos leía cada nombre dos veces.
- **Cambio**: los aldeanos no francos conservan solo ``horse_collar`` / ``heavy_plow`` / ``crop_rotation``. Los francos usan ``frank_villager``, con las alias gratuitas.

**Corrección: ``gather_byproduct`` (p. ej. Papel moneda) no aparecía en atributos**

- **Problema**: el efecto es un triple (depósito, ritmo). La UI lo leía como par, tomaba el depósito como valor, perdía el ritmo y ocultaba la fila.
- **Cambio**: se muestran depósito, recurso secundario y ritmo por segundo (Papel moneda: depósito de madera, oro, +0.014/s). Las reglas siguen usando el tipo de depósito (p. ej. ``wood``).

**Novedad: oír las bonificaciones de civilización al elegir facción**

- Las flechas solo leen el nombre. Con ``intro``, pulse **G** para un submenú y suba/baje frase a frase (Enter repite; Esc vuelve). Sin ``intro``, sin cambios.
- aoe2: las doce civs tienen texto en inglés y chino.

**aoe2: pastores y cazadores usan depósitos de cadáver distintos (por reglas)**

- **Problema**: ovejas y ciervos/jabalíes compartían ``food_carcass``, así que el bonus de pastores britanos y el de cazadores mongoles aceleraban ambos trabajos.
- **Cambio**: los ``herdable`` dejan ``food_livestock``; la caza sigue con ``food_carcass``. Britanos: ``gather_time_food_livestock -20%``. Mongoles: ``gather_time_food_carcass -29%``. El motor empareja ``gather_time_<depósito>`` y la caza de la IA desde las rules (``food_deposit`` / ``is_huntable``), sin hardcodear civs.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novedad: ``pursue_attacker`` — jabalíes persiguen entre casillas (estilo AoE2)**

- **Problema**: los jabalíes contraatacaban en ``guard``, pero ``AttackAction`` solo perseguía entre casillas en modo ``chase``, así que al salir el aldeano se cortaba la persecución y no se podía atraer al centro urbano.
- **Cambio**: el flag de rules ``pursue_attacker 1`` mantiene el ataque siguiendo entre casillas (sin exigir enemistad diplomática). Jabalíes en rules base y aoe2 lo activan; ciervos/ovejas siguen con ``flee_on_hit``.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novedad: ``pursue_leash_range`` — soltar agresión al abrir distancia**

- **Problema**: solo con ``pursue_attacker``, ``last_attacker`` mantenía la persecución aunque abrieras un gran hueco (no es el deaggro por LOS de AoE2).
- **Cambio**: entero de rules ``pursue_leash_range`` (mm; ``0`` = ilimitado). Más allá, olvida al atacante, detiene el ataque y vuelve a casa. Jabalíes usan ``48000`` (~4 casillas).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novedad: ``claimable`` + pastizal (reclamo AoE2 / pastizal AoE4, por reglas)**

- **Problema**: el pastoreo solo seguía sin cambiar de dueño; no había reclamo al acercarse ni pastizales que críen ganado.
- **Cambio**: animales ``claimable`` neutrales pasan a cualquier unidad no neutral cercana (``claim_range``; ``can_herd`` sigue aparte). Edificios: ``spawns_unit`` + ``spawn_player_cap`` / ``spawn_immediate`` (aoe2: oveja ``claimable``; ``pasture`` mongol).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.


1.4.7.1
-------

- **Problema**: el solar (``BuildingSite``) mostraba el menú de entrenamiento/investigación del edificio objetivo, así que un cuartel podía entrenar antes de terminarse.
- **Cambio**: los solares inacabados no listan entrenamiento/investigación y no pueden producir.
- **Alcance**: todos los mods (incluido aoe2).
- **Código / pruebas**: ``world_build_rules.py`` (``is_unfinished_building``, ``effective_can_train`` / ``effective_can_research`` / ``building_can_operate``); ``test_can_train_upgrade.py``.

**Corrección: al terminar, el edificio nace con el HP de bonificación, no a medio reparar**

- **Problema**: al completar se escribía el HP actual con el ``hp_max`` de la clase (p. ej. cuartel 1200), mientras el ``hp_max`` de instancia ya incluía bonificaciones (bizantinos Edad Oscura +10% → 1320). Los aldeanos reparaban el «hueco».
- **Cambio**: al completar se usa el ``hp_max`` de instancia (menos el daño durante la obra). Como en AoE2: termina a HP lleno con bonus, no se repara después.
- **Alcance**: todos los mods.
- **Código / pruebas**: ``worldcreature.py`` (``BuildingSite._complete_construction``); ``test_z5_byzantine_barracks_hp.py``.

**aoe2: civilización Celtas; campaña de William Wallace como celtas**

- Celtas: UU merodeador con tinte; UT Fortaleza / Furor celta; bonus de infantería, leñadores y asedio.
- Campaña Wallace: jugador ``default_faction celts``; PCs ingleses ``faction britons``.
- Mapas: ``computer_only … faction <nombre> …`` asigna civilización por PC. Ver ``mod/mapmaking``.


1.4.7.0
-------

**Mejora: el sonido de paso/bloqueo se solapa con las coordenadas al recorrer el mapa**

- **Problema**: al navegar con las flechas, el sonido de paso (p. ej. puente) o de bloqueo iba en la cola de voz y terminaba antes de las coordenadas / nombres, con sensación de retraso.
- **Cambio**: esos efectos se reproducen al instante en el mezclador de SFX; coordenadas y nombres siguen en la cola de voz, de modo que empiezan a la vez.
- **Alcance**: recorrido normal, cruce de casilla en zoom, bloqueo en primera persona.
- **Código**: ``clientgame/game_navigation.py`` (``_play_movement_sfx``), ``clientgamefocus.py``, ``clientgame/game_audio.py``.


**Novedad: recompensa de recurso al matar ``kill_resource_vs`` (sin oro hardcodeado)**

- **Uso**: al matar un tipo coincidente, el asesino gana un **recurso elegido** (p. ej. Caudillos: oro al matar aldeanos); el motor **no** fija «oro» ni ``resource1``.
- **Sintaxis**: ``effect bonus kill_resource_vs <tipo> <recurso> <cantidad>``, p. ej. ``kill_resource_vs peasant resource1 5``. El recurso puede ser ``resourceN`` o alias ``gold`` / ``wood`` / ``food`` / ``stone``. Coincidencia por ``type_name`` / ``is_a``.
- **Almacenamiento**: ``tipo_víctima → { resourceN: cantidad }``; al matar, ``store`` y evento ``resourceN_reward``.
- **aoe2**: Caudillos usa ``kill_resource_vs … resource1 5`` (aldeano / carreta / barco / monje).
- **TTS / UI**: «bonificación de recurso al matar vs» (sin clave cruda ``kill_gold``).
- **Docs**: ``mod/modding``. Código / pruebas alineados con la versión inglesa.


1.4.6.9
-------

**Novedad: predicción de proyectiles por reglas y velocidad de vuelo por vía**

- **Vuelo**: ``rdg_projectile_speed`` / ``mdg_projectile_speed`` son **velocidades** (casillas/s), no «segundos de vuelo»; solo con el flag ``*_projectile`` correspondiente. Tiempo hasta impacto = distancia ÷ velocidad. ``projectile_speed`` compartido y ``*_delay`` legado están obsoletos (migrados al cargar).
- **Predicción**: ``projectile_lead 0|1`` (solo proyectiles a distancia). Sin ``ballistics`` hardcodeado.
- **Tech / UI**: ``effect bonus projectile_lead 1``; ``effect info``.
- **Docs**: `Predicción de proyectiles <mod/projectile-lead.htm>`_; ``mod/modding``.

**Novedad: mercado configurable por reglas (compra/venta, tributo, rutas)**


- Mods eligen mercancías, moneda, impuestos, tributos y qué recursos/hubs usan las unidades de comercio — sin nombres fijos en el motor ni oro obligatorio.
- Parámetros ``market_*`` / ``tribute_*`` / ``trade_*``; atributos ``is_market``, ``trade_hubs``, ``trade_rewards``; órdenes ``market_buy`` / ``market_sell`` / ``tribute`` / ``trade``.
- Docs: ``mod/market-system``, ``player/market-and-trade``; aoe2 en ``SOURCES.md``.

**Mejora: renombrar filtros de bonus a ``phase_bonus_targets`` / ``effect_bonus_targets``**

- Nombres principales emparejados con ``phase bonus`` / ``effect bonus``.
- Alias aún válidos: ``phase_targets``, ``tech_effect_targets``, ``effect_targets``.

**Novedad: modos duales de recolección ``gather_mode trip|continuous``**

- Predeterminado ``trip``: un pulso ``gather_qty`` y entrega (comportamiento anterior).
- ``continuous``: llena ``carry_capacity`` a un ritmo por segundo, luego entrega (estilo AoE II/IV).
- Reglas: ``gather_mode``, ``carry_capacity``, ``carry_capacity_<type>``, ``gather_rate`` — ver docs de modding.
- ``mods/aoe2`` activa continuous (carga 10, carroña de caza 35).



**Mejora: anunciar la facción resuelta tras civ aleatoria**

- Solo si en el lobby se eligió Aleatoria **y** el mod tiene más de una facción: tras el objetivo inicial se dice “eres” + civ; elección manual o un solo bando (p. ej. ``res`` base) no anuncia. ``Alt+C`` (``faction_status``) usa la misma regla.
- Código: ``faction_announce.py``, ``worldplayerbase/base.py`` (``faction_was_random``), ``game_resources.py``, ``game_interface_base.py``; tests ``test_faction_status_announce.py``.

**Mejora: oír la civ enemiga en mods multi-civ**

- Con más de una facción, el título de unidades enemigas/aliadas incluye la civ; ``F11`` y la selección diplomática también dicen la civ tras el nombre.
- Código: ``faction_announce.py``, ``properties.py``, ``game_audio.py``.

**Novedad: ``on_phase`` y ``research_cost_discount`` / ``advance_cost_discount``**

- Recompensas por civ en ``class race``/``faction`` sin nombres hardcodeados en el motor.
- ``on_phase`` / ``research_cost_discount`` / ``advance_cost_discount``; ``phase bonus clear``; ``no_auto_upgrade 1``.
- Código: ``worldphase.py``, órdenes, ``definitions.py``; tests ``test_faction_age_cost_discounts.py``.

**Novedad: plantillas de facción ``abstract`` e herencia ``is_a`` de inicio**

- **Uso**: defaults de ``starting_resources`` / ``starting_units`` en un padre abstracto (p. ej. ``Civilization``); cada civ ``is_a`` ese padre. Lo que escriba el hijo prevalece; lo omitido se hereda. Mapas sin unidades iniciales siguen usando el default de raza.
- **``abstract 1``**: solo plantilla — **no aparece en el selector**; ``abstract`` no se hereda.
- **Herencia**: ``class race`` = ``class faction``; cadenas ``is_a``. El mapa explícito sigue ganando.
- **Código / pruebas**: ``definitions.py``, ``test_faction_starting_inheritance.py``.

**Mejora: aislar mapas y campañas con un mod activo (sin fallback a ``res``)**

- **Problema**: si un mod no tenía ``multi/`` o ``single/`` propios, los menús seguían listando el contenido base de ``res``.
- **Cambio**: con cualquier mod activo solo se listan ``mods/<mod>/multi`` y ``mods/<mod>/single``; si no hay, las listas quedan vacías — **sin** volver a ``res`` ni descargas. Sin mod, igual que antes.
- **Código / pruebas**: ``lib/resource.py``, ``game.py``, ``test_mod_map_campaign_isolation.py``.

**Corrección: se ignoraba ``starting_resources`` de la raza si el mapa no lo definía (inicio en 0)**

- **Problema**: las razas tenían ``starting_resources`` en rules, pero mapas sin esa línea empezaban en 0.
- **Causa**: ``_parse_map`` rellenaba ``[0, 0, …]``; ``populate_map`` solo usa el valor de raza si la lista está vacía.
- **Corrección**: lista vacía ``[]`` hasta que el mapa defina ``starting_resources``; una línea explícita del mapa (incluso ``0``) sigue ganando.
- **Código / pruebas**: ``world_map.py``, ``test_race_starting_resources.py``.

**Corrección: comentar ``LSHIFT C`` / ``LSHIFT B`` seguía copiando voz en partida**

- **Problema**: ``global_bindings.txt`` comenta por defecto Left Shift+C/B (copiar / añadir de la biblioteca de voz primaria), pero en partida seguían funcionando.
- **Causa**: ``game_input_handler`` llamaba a ``voice_libs.handle_hotkey`` antes de bindings y saltaba la tabla de teclas.
- **Corrección**: en partida Shift+C/B solo siguen **bindings**; un ``;`` al inicio las desactiva. Los menús conservan Left/Right Shift+C/B hardcodeados. Right Shift+C/B (biblioteca secundaria) siguen activos por defecto.
- **Código / pruebas**: ``game_input_handler.py``, ``clientmenu.py``, ``voice_libs.handle_hotkey``, ``test_lshift_rshift_bindings.py``.


1.4.6.8
-------

**Novedad: habilidades automáticas al morir/destruir (``trigger_timing on_death``)**

- **Uso**: unidades o edificios pueden lanzar efectos al morir — p. ej. un depósito de munición que explota con daño en área; también invocaciones, ``effect deploy``, etc.
- **Configuración**: en ``class skill``, ``auto_trigger 1``, ``manual_use 0``, ``trigger_timing on_death``, y enlazar con ``can_use_skill`` (o el legado ``death_trigger_skills``). Ejemplo: ``effect harm_area 40 6`` (daño fijo 40, radio 6); también sirven ``deploy`` / ``summon`` / ``buffs``.
- **Comportamiento**: se dispara en ``die()`` antes de borrar la entidad; permite HP ya en 0; **no usa maná ni enfriamiento**; centra en sí misma (para AoE, ``effect_target self``); las muertes en cadena pueden encadenar más ``on_death``. Distinto de ``mdg_explode`` / ``rdg_explode`` (solo al atacar). El mismo skill puede ser ``manual_use 1`` + ``on_death`` (p. ej. depósito que se detona): un lanzamiento manual exitoso se registra para que la autodestrucción **no vuelva a explotar**; destruido por el enemigo sí dispara una vez.
- **Código / pruebas**: ``world_attributes.py``, ``worldcreature.py``, ``worldskill.py``; ``GENERIC_SKILL_SYSTEM.md``; ``test_death_skills.py``.


1.4.6.7
-------

**Corrección: atacar un NPC neutral de historia no lo volvía hostil**

- En la campaña de Raynor (cap. 25), los guardias devolvían el golpe pero seguían ``neutral``, así que el ejército no los atacaba solo.
- Causa: el duelo solo hacía ``set_ai_mode offensive`` sin quitar ``Player.neutral``.
- Nuevo ``(set_neutral 0|1 [player])``; la neutralidad va con guardia — pasar a ofensivo/defensivo/persecución (UI o ``set_ai_mode``) la quita; también al ser golpeado por un bando no neutral (no fauna); cap. 25 usa ``set_neutral 0`` al duelo y ``set_neutral 1 computer1`` al rechazar la alianza.
- **Código / pruebas**: ``worldplayerbase/base.py``, ``triggers.py``, ``25.txt``, ``test_campaign_alliance_transfer_triggers.py``, ``test_neutral_no_auto_attack.py``.

**Corrección: los escoltas de Marco atacaban a Raynor en el duelo (cap. 27)**

- Debían salir de la arena; ``_notify_guard_units`` los metía en el contraataque y la orden solo movía 8 de 12.
- Nuevo ``(set_counterattack 0|1 …)``; al empezar el duelo se desactiva el contraataque de los 12 escoltas y salen con ``imperative go``.
- **Código / pruebas**: ``triggers.py``, ``27.txt``, ``test_campaign_alliance_transfer_triggers.py``.

**Corrección: con trucos activos, una flecha saltaba varias casillas**

- En mapas grandes (p. ej. cap. 28) con cheatmode, Right una vez hacía a1→b1→c1→d1.
- Causa: ``select_square`` lento + key-repeat de pygame; el bucle de juego no limpiaba KEYDOWN repetidos (el menú sí).
- Ahora se conserva el primer KEYDOWN por tecla del lote y se hace ``clear([KEYDOWN])`` tras manejarlo.
- **Código / pruebas**: ``game_input_handler.py``, ``test_game_keydown_repeat_collapse.py``.


1.4.6.6
-------

**Corrección: la comprobación al iniciar a veces no detectaba una versión nueva**

- Con la comprobación al inicio activa, a veces no había aviso tras arrancar, pero Opciones → Comprobar ahora sí encontraba la versión.
- Causa: la petición a GitHub puede tardar ~20 s y el hilo principal solo esperaba ~8 s; el tiempo agotado se trataba como «ya actualizado».
- Ahora la comprobación arranca antes, espera a terminar (~30 s) y, si sigue pendiente, usa la misma comprobación síncrona que el menú.
- **Código / pruebas**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``test_auto_update.py``.

**Mejora: avisos de actualización visibles en pantalla**

- Los avisos ya no son solo por voz: texto en pantalla, botones Yes/No (clic), notas del changelog visibles, e intento de traer la ventana al frente.
- **Código**: ``pygame_ui.py``, ``clientmenu.py``, ``clientversion.py``.

**Corrección: al elegir leer las notas de actualización no se oían**

- Tras confirmar una actualización nueva, aceptar «leer las notas» no reproducía el cuerpo del Release de GitHub (o se cortaba al instante por el aviso de continuar).
- Causa: lista de ``literal_text_msg`` anidada de más, y ``voice.item`` no bloqueante interrumpido por el siguiente aviso.
- Ahora se usan ``voice.menu(literal_text_msg(...))`` (bloqueo hasta terminar o saltar) y luego la confirmación de continuar.
- **Código / pruebas**: ``clientversion.py``, ``test_auto_update.py``.

**Corrección: desplazamiento de traducción en TTS (clave ``5750``)**

- En de / es / fr / it / pt-BR, la clave ``5750`` (idioma) decía erróneamente texto de «uno contra muchos» por un desfase de líneas.
- Corregido en ``res/ui-de``, ``ui-es``, ``ui-fr``, ``ui-it``, ``ui-pt-BR`` ``tts.txt`` → Sprache / idioma / langue / lingua / linguagem.

**Corrección: auditoría TTS multilingüe (ids faltantes y errores claros)**

- Varios idiomas iban detrás del ``tts.txt`` inglés (unas 27 claves nuevas: terreno/aire intransitables, amenaza, cuenta regresiva de victoria, voz de accesibilidad, idioma predeterminado del sistema, etc.), con errores o confusiones (p. ej. italiano: soldado raso como peón, sigilo = invisible, reunión = reorganizar; es/pt: sigilo como «robado»; alemán: reunión como «usted comanda»; población vs comida; velocidad del habla = velocidad de unidad; ayuda larga de bibliotecas de voz aún en inglés).
- Se completaron las claves faltantes en ``ui-it``, ``ui-fr``, ``ui-es``, ``ui-de``, ``ui-pt-BR``, ``ui-ru``, ``ui-pl``, ``ui-cs``, ``ui-sk``, ``ui-be``, ``ui-vi`` (el chino ya estaba completo); se corrigieron errores claros; se tradujo la ayuda de voz/actualización que seguía en inglés.
- **Alineación i18n**: se ejecutó ``python tools/i18n/extract_pot.py`` para que ``i18n/tts.pot`` y cada ``i18n/tts-*.po`` coincidan con ``res/ui-*/tts.txt``; volver a ejecutar ``build_tts.py`` no borrará estas actualizaciones.
- **Archivos**: ``res/ui-*/tts.txt``, ``i18n/tts.pot``, ``i18n/tts-*.po``.


1.4.6.5
-------

**Corrección / novedad: el gas del mod StarCraft se agota (extractores genéricos)**

- **Problema**: Assimilator / Extractor / Refinery producían vespeno ilimitado a ``production_qty`` (8 por defecto) — a diferencia de StarCraft.
- **Reglas**: el geyser tiene reserva (por defecto ``deposit_volume 5000``; ``geyser 1`` en el mapa es marcador y usa ese valor, o ``geyser 5000``); cada ciclo descuenta de la reserva; al vaciarse, el rendimiento baja a ``depleted_production_qty`` (2).
- **Palabras clave**: ``is_an_extractor``, ``deposit_volume``, ``depleted_production_qty`` (reutilizables en otros mods).
- **Código / pruebas / docs**: ver notas en inglés/chino; ``mods/starcraft/readme.txt``.

**Mejora: generación larva/hatchery genérica con ``spawns_unit``**

- Ya no se usan nombres fijos ``hatchery``/``larva``; cualquier edificio puede usar ``spawns_unit`` + ``larva_cap`` + ``larva_spawn_time``.


1.4.6.4
-------

**Novedad: Opciones → Comprobar actualizaciones ahora**

- Si desactivas la comprobación al iniciar, aún puedes comprobar GitHub manualmente desde Opciones; si hay versión nueva, el flujo de confirmación es el mismo.
- Anuncia si ya tienes la última versión o si falla la comprobación.

**Mejora / corrección: paquete Windows usa una ventana de actualización aparte (con progreso)**

- Tras confirmar, el juego sale y ``soundrts.exe --soundrts-update`` abre **SoundRTS Update** para descargar/descomprimir con barra de progreso (evita «No responde» y cuelgues al cargar el módulo de actualización). La instalación usa ``tasklist`` sin ``find`` (conflicto con Git), omite ``user``, y reinicia. Temporal en ``user/tmp/`` (o ``%APPDATA%\\SoundRTS\\tmp/``).
- **Código**: ``update_window.py``, ``update_core.py``, ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``soundrts.py``, ``msgparts.py``, ``tts.txt`` (``5794``–``5798``).
- **Pruebas**: ``test_auto_update.py``.

**Corrección: lentitud al recorrer el menú de bibliotecas de voz con las flechas**

- En Opciones → bibliotecas de voz, subir/bajar se notaba lento aunque la fila activa fuera corta, porque el texto de ayuda largo seguía visible.
- Cada redibujado truncaba líneas largas con un bucle lineal de ``font.size``.
- Ahora el ajuste de texto del menú usa búsqueda binaria y caché.
- **Código**: ``lib/pygame_ui.py`` (``_fit_menu_text``).
- **Pruebas**: ``test_voice_libs_menu_arrow_profile.py``.

**Mejora: textos de bibliotecas de voz / comprobar actualizaciones pasan a ids TTS multilingües**

- Algunos textos estaban solo en chino en ``msgparts.py`` y no seguían el idioma de la interfaz vía ``tts.txt``.
- Ahora son ids numéricos (aprox. ``5760``–``5793``) en ``res/ui`` y cada ``ui-*`` ``tts.txt`` (zh/en completos; otras lenguas traducen etiquetas cortas, con inglés de reserva en textos largos).
- **Código**: ``msgparts.py``, ``tts.txt`` por idioma.


1.4.6.3
-------

**Novedad: comprobar actualizaciones de GitHub al iniciar e instalar con un clic (paquete Windows)**

- Al iniciar, consulta el Release de GitHub ``tuohai/soundrts-ultimate-version``. Si hay versión más nueva: **Intro** para actualizar, **Esc** para cancelar.
- Opcionalmente se puede oír el changelog del Release antes de descargar.
- **Paquete Windows**: descarga y descomprime en ``tmp`` de la configuración (portable ``user/tmp/``, instalado ``%APPDATA%\\SoundRTS\\tmp/``); al salir un script corto sobrescribe la carpeta e inicia de nuevo. Se **omite** la carpeta ``user`` (partidas/ajustes locales). Tras aplicar, se borran esos temporales.
- **Ejecución desde el código fuente**: solo abre la página de descarga (no sobrescribe el proyecto).
- Menú de opciones: **Comprobar actualizaciones al iniciar el juego** (activado por defecto; Intro alterna). Opción ``check_updates_on_start`` en ``SoundRTS.ini``.
- **Código**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``config.py``.
- **Pruebas**: ``test_auto_update.py``.

**Mejora: scroll por bordes y zoom con rueda en mapas grandes Ctrl+F2 (estilo Age of Empires)**

- En mapas grandes, pasar el ratón por las casillas ya **no salta la cámara**.
- La vista solo se desplaza con el puntero en el **borde del mapa**; rueda arriba/abajo para acercar/alejar.
- Clic en el minimapa y saltos con teclado siguen centrando la vista.
- **Código**: ``clientgamegridview.py``, ``game_input_handler.py``, ``game_navigation.py``.
- **Pruebas**: ``test_gridview_viewport.py``, ``test_zoom_mouse.py``.


1.4.6.2
-------

**Novedad: cambiar el idioma de la interfaz desde el menú de opciones**

- Menú principal → **Opciones** → **Idioma**: elige un idioma o **Predeterminado del sistema** sin editar archivos de la carpeta de instalación.
- La preferencia se guarda en ``language.txt`` del usuario (``user/language.txt`` o ``%APPDATA%\\SoundRTS\\language.txt``). ``cfg/language.txt`` sigue siendo un respaldo de solo lectura.
- El archivo de usuario tiene prioridad sobre ``cfg/language.txt``.
- **Código**: ``clientmain.py``, ``lib/resource.py``, ``paths.py``.

**Mejora: panel de atributos / mochila y equipo / viewport de mapas grandes**

- Panel de atributos al seleccionar; mochila/equipo con ratón; mapas grandes estilo Age of Empires (sin encoger).

**Corrección: fallo al guardar la partida para continuar en mapas grandes**

- Al salir a mitad de partida en mapas grandes (p. ej. ``cw1-mm`` 100×100), el autoguardado de «continuar partida» fallaba y el registro decía erróneamente «mundo demasiado grande».
- **Causa**: se serializaba ``local_client.interface`` (fuentes/bloqueos de pygame).
- **Corrección**: no se guarda ``interface`` (se reconstruye al cargar); solo ``RecursionError`` / ``MemoryError`` se informan como mapa demasiado grande.
- **Código**: ``worldclient.py``, ``game.py``, ``clientgame/game_resources.py``.


1.4.6.1
-------

**Corrección / mejora: unidades en mapa Ctrl+F2 y capas de arte**

- **Corrección**: unidades/edificios del mapa principal casi pegados al borde superior por conversión mundo→pantalla incorrecta; el eje Y ahora coincide con las casillas.
- **Ratón / HUD / F8**: selección, rejilla de comandos 5×3, cola; ``ui/icons`` (HUD) vs ``ui/map`` (mapa) vs ``ui/anims``.
- **Código**: ``clientgamegridview.py``, ``game_hud.py``, ``game_unit_anim.py``, etc.


1.4.6.0
-------

**Nuevo / mejora: calidad visual Ctrl+F2 (vista cenital)**

Respecto al mapa de depuración antiguo (bloques planos, muros negros, puntos), esta versión mejora legibilidad e información:

- **Terreno y ambiente**: colores por defecto legibles sin ``color`` en style; terreno alto más claro y ligeramente cálido; niebla oscurecida pero con tono; mapa centrado con márgenes.
- **Estructura**: rejilla; muros vs salidas/pasos diferenciados.
- **Unidades y recursos**: formas distintas; colores de equipo; selección; barras de vida; marcadores aéreos.
- **Etiquetas y panel**: coordenadas base 1 (p. ej. 2,7), nombres y recursos; panel izquierdo al pasar el ratón.
- **Minimapa y botón de objetivos**: como en el manual.
- **Código**: ``clientgamegridview.py``, ``game_visual_fx.py``, etc.

**Nuevo: F4 conmuta la voz de accesibilidad en menús**

- En **cualquier menú** (incluido el menú de pausa), **F4** o el ítem «conmutar voz de accesibilidad» apaga/enciende todo el TTS.
- **Apagado**: sin voz; SFX y música siguen; útil con Ctrl+F2.
- **Por defecto activado**; se guarda en ``SoundRTS.ini`` (``speech_enabled``).
- **F4 en partida sin cambios** (teclas por capas: sigue siendo Ayuda); solo en menús.
- **Código**: ``config.py``, ``lib/voice.py``, etc.; TTS 5740–5743.
- **Docs**: ``player/voice-libraries.rst``, manuales.

**Nuevo: menús visuales pygame y ratón (sin wxPython)**

- Menús principal/sub/pausa dibujan una lista en la ventana SDL (~960×640).
- **Ratón**: resalta al pasar; clic selecciona y anuncia; otro clic o doble clic confirma. Teclado sin cambios.
- Juego a ciegas: TTS + teclado; el texto en pantalla es de píxeles y **suele no llegar a lectores/braille**.
- **Código**: ``lib/pygame_ui.py``, ``clientmenu.py``, ``lib/screen.py``.

**Nuevo: escenas / sinopsis / objetivos en pantalla**

- ``synopsis`` de campaña, ``sequence`` de corte, ``intro`` de mapa, objetivo inicial y F9 en partida muestran texto.
- **Objetivo inicial**: siempre scroll; en partida se puede volver a ver.
- **Escenas / sinopsis / intro**: local / entrenamiento / solo vs PCs: Enter / Esc; en línea (dos o más humanos): scroll.
- **Código**: ``lib/voice.py`` (play_cutscene_line / play_scrolling_line / play_narrative_line), ``clientmedia.py``, ``campaign.py``, etc.

**Mejora: Ctrl+F2 persistente**

- Se guarda ``display_enabled`` en ``SoundRTS.ini``; se restaura al reiniciar.
- **Código**: ``config.py``, ``clientmedia.py``.

**Corrección: retraso al saltar mapas por letra**

- Listas largas ~0,8 s por escaneo TTS global; ahora etiquetas locales + caché.
- **Código**: ``lib/pygame_ui.py``, ``clientmenu.py``.


1.4.5.9
-------

**Mejora: ``space`` de casilla contado por alianza**

- **Antes**: La capacidad era compartida; la artillería enemiga llenando una casilla impedía entrar a melé/caballería.
- **Ahora**: Cada alianza tiene su propio cupo hasta ``square_width``; la ocupación enemiga no usa el tuyo. P. ej. con ``square_width 12``, cada bando puede tener doce ``space 1``. Los aliados comparten un cupo.
- **Código**: ``worldroom.py``; entrenamiento/aparición pasan el jugador.
- **Pruebas**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Corrección: recursos recolectados se almacenaban sin almacén**

- **Síntoma**: Tras recolectar, los trabajadores podían añadir recursos al almacén aunque no hubiera ayuntamiento / aserradero u otro edificio de almacenamiento.
- **Causa**: En tierra, ``bring_back`` seguía llamando a ``_store_cargo()`` si ``nearest_warehouse`` devolvía ninguno. En 1.3.8.1 se vaciaba la carga y fallaba la orden; una reescritura posterior almacenaba por error.
- **Corrección**: Sin almacén no se guarda; se conserva la carga, se avisa una vez ``order_impossible`` y se detiene. La entrega continúa cuando haya almacén.
- **Código**: ``worldorders/gathering.py``.
- **Pruebas**: ``test_gather_requires_warehouse.py``.


1.4.5.8
-------

**Novedad: ocupación abstracta de casilla (``space``)**

- La propiedad ``space`` (precisión; admite decimales) usa las **mismas unidades que ``square_width``**. ``square_width 12`` = cada casilla (p. ej. a1) mide 12; ``space 1`` ocupa 1 de esos 12 (máx. 12); ``space 0.5`` → máx. 24.
- Por defecto ``space 0`` = ilimitado (legado). La capacidad es por alianza (véase 1.4.5.9); si tu bando está lleno, no puedes entrar ni entrenar allí. Voz: ``not_enough_space`` (TTS 5338); etiqueta TTS 5733.
- Vanilla: peasant/footman ``space 0.25``; catapult ``space 1``.
- **Código**: ``definitions.py``, ``worldentity.py``, ``worldroom.py``, ``worldunit/world_movement.py``, ``worldorders/production.py``, ``worldplayercomputer_water.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui*/tts.txt``.
- **Docs**: ``mod/modding.rst``, ``mod/mapmaking.rst``, manuales (todos los idiomas).
- **Pruebas**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Novedad: cuenta atrás de victoria de edificio (``victory_time``) y Maravilla**

- Cualquier edificio terminado con ``victory_time N`` (segundos) inicia una cuenta atrás. Si el temporizador termina y el edificio sigue en pie, gana su dueño (y el bando de victoria aliada). Destruir el edificio cancela la cuenta atrás y lo anuncia.
- ``wonder`` (Maravilla) en vanilla (Edad Imperial): edificio tardío costoso; ``victory_time 300`` (5 minutos). Atajo ``o``.
- Voces 5720–5722 (inicio / cancelación / restante); avisos a 120/60/30/10 s y 5…1.
- **Código**: ``building_victory.py``, ``worldunit/worldcreature.py``, ``world/world_core.py``, ``world/world_game.py``, ``definitions.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (``victory_time``), manuales de jugador.
- **Pruebas**: ``test_building_victory.py``.

**Novedad: requisitos ``any_buildings`` por grupo**

- ``requirements`` admite ``any_buildings <n> <group>_buildings``: el jugador debe poseer cualesquiera ``<n>`` edificios distintos del grupo (AND con otros nombres simples en la misma línea).
- Pertenencia: edificios cuyo ``requirements`` simple incluye ``<clave>`` (tras quitar el sufijo ``_buildings``). Ejemplo: ``requirements castle_age`` entra en ``castle_age_buildings``.
- Vanilla: ``imperial_age`` y ``castle`` (keep→castle) usan ``any_buildings 2 castle_age_buildings``.
- Voz: style ``parameters.any`` / ``parameters.buildings_of`` (TTS 5730–5731).
- **Código**: ``worldrequirements.py``, ``worldplayerbase/base.py``, ``worldphase.py``, ``worldplayercomputer.py``, ``clientgameorder.py``, ``attributes/display_interface.py``, ``definitions.py``, ``worldunit/worldcreature.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (todos los idiomas).
- **Pruebas**: ``test_any_buildings_requirements.py``.


1.4.5.7
-------

**Corrección: unidades atrapadas atacando edificios sin amenaza en vez de combatientes**

- **Síntoma**: al destruir una granja, ayuntamiento u otro edificio similar, los combatientes enemigos pueden acercarse y matar a tus unidades; estas siguen golpeando el edificio en lugar de cambiar de objetivo.
- **Causa**: en 1.4 se omitía el reescaneo de objetivos mientras ya había combate (rendimiento). Los edificios cuentan como enemigos vivos, así que el combate se pegaba a granjas. 1.3.8.1 solo se pegaba a objetivos con ``menace > 0`` y reelegía si el objetivo actual no tenía amenaza.
- **Corrección**: se restaura el comportamiento de 1.3.8.1—enganche sticky y caché de decisión solo con ``menace > 0``; edificios con amenaza 0 pueden reescanearse y se prefieren unidades de combate. Atacar unidades amenazantes sigue devolviendo pronto (ruta caliente intacta).
- **Código**: ``worldunit/world_ai_decision.py``.
- **Pruebas**: ``test_retarget_zero_menace.py``.

**Mejora: bindings distinguen Shift izquierdo/derecho (``LSHIFT`` / ``RSHIFT``)**

- Además de ``SHIFT``, se pueden usar ``LSHIFT`` y ``RSHIFT`` como modificadores (no mezclar con ``SHIFT`` en la misma línea).
- La búsqueda prioriza el lado concreto y luego cae a ``SHIFT`` genérico.
- Activos por defecto: ``RSHIFT C`` / ``RSHIFT B`` (copiar/añadir **secundaria**).
- ``LSHIFT C`` / ``LSHIFT B`` (principal) están **comentados** en ``res/ui/global_bindings.txt``; quite el ``;`` inicial para activarlos.
- **Consejo:** use un lector de pantalla como voz principal para no gastar ``F9``–``F12`` en la principal; las teclas están muy saturadas. Véase ``player/voice-libraries.rst``.
- **Código**: ``lib/bindings.py``, ``res/ui/global_bindings.txt``, ``hotkey_editor.py``.
- **Pruebas**: ``test_lshift_rshift_bindings.py``.

**Mejora: suelo de volumen para casillas lejanas en pan de voz**

- Las alertas habladas con posición no se atenúan sin límite: el volumen se mantiene cerca del de una casilla adyacente (un poco más bajo permitido). Los pitidos del minimapa siguen atenuándose por distancia completa.
- **Código**: ``lib/sound.py``, ``clientgame/game_resources.py``, ``clientgame/game_unit_control.py``.
- **Pruebas**: ``test_spatial_voice_alerts.py``.

**Mejora: ``ai.txt`` multiplicador ``build_time``**

- Nueva directiva ``build_time <pct>`` (al inicio, fuera del bucle): porcentaje de la duración normal de construcción (``100`` = normal, ``50`` = el doble de rápido).
- Ejemplos: advanced/expert ``build_time 50``; nightmare ``build_time 40``.
- **Pruebas**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.

**Mejora: ``ai.txt`` multiplicador ``gather_time``**

- Nueva directiva ``gather_time <pct>``: porcentaje de la duración normal de recolección (``100`` = normal, ``50`` = el doble de rápido). Distinto del campo ``gather_time`` de trabajadores en ``rules.txt``.
- Ejemplos: advanced/expert ``gather_time 50``; nightmare ``gather_time 40``.
- **Pruebas**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.6
-------

**Corrección: Alt+Z solo podía encolar un entrenamiento más**

- **Síntoma**: tras confirmar entrenar campesino en el ayuntamiento, Alt+Z (``do_again now``) solo añadía una unidad más a la cola; pulsaciones siguientes no alargaban la cola (reemplazaban el único seguimiento encolado).
- **Causa**: en 1.4 se limitó a «un solo orden normal tras una cabeza imperativa» para proteger ``auto_explore``. Los órdenes de producción (train/research) también son ``is_imperative``, así que se vieron afectados por error. 1.3.8.1 no tenía ese límite.
- **Corrección**: los órdenes de producción con ``never_forget_previous`` pueden apilarse; el hueco único sigue aplicando a seguimientos normales tras cabezas imperativas reales.
- **Código**: ``worldunit/world_order.py``.
- **Pruebas**: ``test_train_queue_repeat.py``.

**Corrección: primer Alt+Z (y similares) tirón ~0.6–1s**

- **Síntoma**: al empezar, el primer Alt+Z congela ~0.5–1s; 1.3.8.1 Alt+G no lo hacía.
- **Causa**: ``LALT`` → ``history_stop_primary`` → ``needs_sapi32`` arrancaba en frío el helper SAPI 32-bit (PowerShell) incluso con Nuance.
- **Corrección**: voces Nuance omiten el sondeo; caché de ``needs_sapi32``.
- **Código**: ``lib/game_tts.py``.
- **Pruebas**: ``test_nuance_skip_sapi32_probe.py``.


1.4.5.5
-------

**Mejora: alertas de casilla con pan estéreo (sigue la vista)**

- Anuncios pasivos ligados a casilla (enemigo, bajas, scout, alertas de combate) se panoramizan respecto a la casilla de vista actual.
- El pan se actualiza si cambias de casilla a mitad del anuncio.
- **Código**: ``lib/voicechannel.py``, ``lib/message.py``, ``lib/game_tts.py``, ``lib/nuance_tts.py``, ``clientgame/game_unit_control.py``, ``clientgame/game_navigation.py``, ``tools/nuance_ve``, ``tools/sapi32``.
- **Documentos**: ``player/voice-libraries.rst``.
- **Pruebas**: ``test_spatial_voice_alerts.py``.

**Mejora: la secundaria se centra en el campo de batalla (economía/producción → principal)**

- Completar unidad/edificio, investigación, avance de era, cambios de recursos y «menú cambiado» pasan a la biblioteca **principal**.
- **Documentos**: ``player/voice-libraries.rst``.

**Mejora: Alt izquierdo / Alt derecho filtran principal vs secundaria**

- **Alt izquierdo** omite/para la principal; **Alt derecho** omite/para la secundaria.
- **Con secundaria desactivada**: ambos Alt omiten la línea actual.
- **Documentos**: ``player/voice-libraries.rst``.

**Mejora: búfer y frecuencia del mixer configurables (menos cortes de SFX en partida)**

- En ``SoundRTS.ini`` ``[audio]``: ``mixer_buffer`` (por defecto ``2048``) y ``mixer_frequency`` (por defecto ``44100``), aplicados al iniciar con ``pygame.mixer.pre_init``.
- Más búfer = audio más estable y un poco más de latencia (``1024`` / ``2048`` / ``4096``). Valores inválidos se ajustan al más cercano de ``512/1024/2048/4096/8192``.
- Canales SFX: ``[general] num_channels`` (por defecto ``16``; prueba ``32`` si hace falta).
- Tras cambiar, **reinicia el juego**.
- **Código**: ``config.py``, ``lib/sound.py``, ``clientmedia.py``.
- **Documentos**: ``mod/audio-management.rst``.


1.4.5.4
-------

**Mejora: bibliotecas de voz principal / secundaria y interruptor**

- En partida: las operaciones del jugador usan la biblioteca **principal**; los eventos pasivos (bajas, descubrimientos…) usan la **secundaria** (pueden solaparse; solo Alt interrumpe la secundaria).
- Opciones → Ajustes de biblioteca de voz: volumen / tono / velocidad / voz / dispositivo por biblioteca; activar o desactivar la secundaria.
- **F3 en menús** activa/desactiva la secundaria (no en partida); desactivada, la principal anuncia todo.
- Instala voces SAPI o paquetes ``voice.ini`` en ``user/voices``; un lector de pantalla detectado puede asumir la principal.
- **Código**: ``lib/voice.py``, ``lib/voicechannel.py``, ``lib/game_tts.py``, ``lib/voice_libs.py``, ``lib/voice_packs.py``, ``clientmenu.py``, ``clientmain.py``, ``config.py``.
- **Documentos**: ``player/voice-libraries.rst``.
- **Pruebas**: ``test_secondary_voice_toggle.py``, ``test_secondary_alt_interrupt.py``.

**Mejora: los refuerzos de cartas y ``starting_units`` de la IA consumen población**

- Las unidades de cartas ``spawn`` / ``train_bonus`` usan el ``population_cost`` normal (ya no son gratis en población).
- Los bonus ``starting_units`` de ``ai.txt`` también consumen población (igual que el inicio del mapa); sube el tope con ``starting_population`` si hace falta.
- **Código**: ``card_loadout.py``, ``worldplayercomputer.py``.
- **Documentos**: ``player/loadout-cards.rst``, ``mod/aimaking.rst``, ``mod/delayed-card-loadout.rst``, ``mod/achievement-system.rst``.
- **Pruebas**: ``test_card_loadout.py``, ``test_ai_start_settings.py``.

**Mejora: multiplicadores ``train_time``, ``research_time`` y ``unit_hp`` en ``ai.txt``**

- Nuevas directivas de una sola vez (al inicio de la partida, fuera del bucle del script):
  - ``train_time <pct>`` — porcentaje de la duración normal de entrenamiento (``100`` = normal, ``50`` = mitad de tiempo)
  - ``research_time <pct>`` — porcentaje de la duración normal de investigación/avance (``80`` = 20% más rápido)
  - ``unit_hp <pct>`` — porcentaje de PV normales de las unidades de este ordenador (``120`` = +20% PV)
- Ejemplos en ``res/ai.txt``: avanzado ``train_time 50`` / ``research_time 80``; experto también ``unit_hp 120``; pesadilla ``train_time 40`` / ``research_time 60`` / ``unit_hp 140``.
- **Código**: ``definitions.py``, ``worldplayercomputer.py``, ``worldorders/base.py``, ``worldorders/production.py``, ``worldunit/worldcreature.py``; ``res/ai.txt``.
- **Documentos**: ``mod/aimaking.rst``.
- **Pruebas**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.3
-------

**Corrección: soldados de la IA intermedia atrapados en autoexploración (ataques muy tardíos o inestables)**

- **Síntoma**: En mapas pequeños (p. ej. ``jl1``), al invitar un ordenador intermedio con el humano inactivo, el primer ataque era muy inestable (~6 min a veces, 16–22 min otras). En 1.3.8.1 el ordenador agresivo atacaba de forma estable hacia 7–9 min en el mismo escenario.
- **Causa**: Desde 1.4, ``take_order`` protege el orden imperativo en cabeza (``auto_explore`` es imperativo): un ``go`` normal solo se encola y no puede sustituir la exploración. ``_send_explorer`` seguía recordando al explorador antiguo con ``go``, fallaba y asignaba nuevos exploradores hasta que casi todos los soldados estaban en ``auto_explore``, de modo que ``constant_attacks`` no tenía combatientes libres.
- **Corrección**: ``_send_explorer`` hace ``stop`` antes de recordar y limpia exploradores sobrantes para que normalmente explore solo una unidad.
- **Código**: ``worldplayercomputer.py`` (``_send_explorer``).
- **Verificación**: Comparación sin interfaz con varios seeds frente a 1.3.8.1; tras el arreglo, el primer daño de la IA intermedia en jl1 ronda 5–7 min con ~1,5 min de dispersión.

**Corrección: el salto por letra inicial en el menú de mapas saltaba el primer mapa y se retrasaba al cambiar de letra**

- **Síntoma**: En Un jugador → Iniciar una partida en (lista de mapas), una pulsación de letra a menudo caía en la segunda coincidencia (p. ej. ``m`` → ``m2`` en lugar de ``m1``, ``p`` → ``pm2`` en lugar de ``pm1``); al pulsar otra letra había una pausa de unos 0,7–1 s antes de saltar.
- **Causa**: El anuncio del título con ``keep_key`` devolvía a la cola todos los ``KEYDOWN`` de autocorrección, así que una pulsación se procesaba dos veces; recordar el último mapa insertaba un duplicado al frente de la lista, que ganaba si compartía la letra. ``_first_letter`` llamaba a ``translate_sound_number`` → ``_global_lookup_text`` sobre los nombres de mapa, costando ~1 s al recorrer una lista de cientos de entradas.
- **Corrección**: Conservar solo el primer ``KEYDOWN`` al interrumpir el habla y limpiar repeticiones tras el salto por letra; con selección fresca, buscar la primera coincidencia desde el inicio de la lista; recordar con ``default_choice_index`` en lugar de un duplicado; tomar el primer carácter del nombre del mapa y consultar los id TTS numéricos solo en la capa local.
- **Código**: ``clientmenu.py``, ``lib/voice.py``.
- **Pruebas**: ``test_menu_first_letter_jump.py``.


1.4.5.2
-------


**Mejora: amenaza (menace) multidimensional y overrides opcionales en rules**

- El ``menace`` por defecto ya no es solo el daño: combina daño, cobertura/acierto, enfriamiento, preparación (``*_ready``), HP, armadura, esquiva, alcance y velocidad (selección de objetivo y amenaza por casilla).
- Campos opcionales: ``menace`` / ``menace_vs`` (absoluto), ``menace_mult`` / ``menace_mult_vs`` (peso sobre la base auto). Parámetros: ``menace_armor_weight``, ``menace_dodge_weight``, ``menace_range_weight``, ``menace_speed_weight``, ``menace_hp_ref``.
- **Docs**: ``mod/modding.rst``, ``mod/aimaking.rst`` (EN/ZH).

**Mejora: persecución continua entre casillas (persecución real)**

- **Antes**: En modo ``chase``, al salir el enemigo de la casilla la IA emitía ``go`` automáticos a casillas vecinas y volvía a atacar — seguía siendo por órdenes, y la unidad podía quedarse «atacando» sin cruzar.
- **Ahora**: ``chase`` mantiene un solo ``AttackAction`` sobre el enemigo bloqueado y sigue por salidas entre casillas, sin spam de ``go``.
- **Hold**: ``position_to_hold`` al nacer sigue bloqueando salir en ofensivo / guardia. Defensivo / persecución están exentos (la persecución limpia el hold al cruzar). ``go`` / ``attack`` normales siguen llamando ``stop()`` y limpian el hold.
- **Código**: ``worldaction.py``, ``worldunit/world_ai_decision.py``, ``worldunit/world_movement.py``.
- **Docs**: ``player/unit-default-behavior.rst``.
- **Pruebas**: ``test_chase_continuous_pursuit.py``.

**Mejora: la pantalla de atributos muestra estadísticas con terreno en vivo**

- Alt+V muestra ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` y modificadores de carga por terreno.
- El terreno de la casilla actual (``mdg_vs`` / ``rdg_vs`` / etc.) y ``*_on_terrain`` alimentan daño, enfriamiento y velocidad en la UI (``*_vs`` de terreno = porcentaje decimal; ``speed_on_terrain`` sigue siendo velocidad absoluta).
- **Código**: ``attributes/terrain_effective.py``, ``attributes/combat_attributes.py``, ``attributes/basic_attributes.py``, ``attributes/bonus_handler.py``.
- **Pruebas**: ``test_terrain_attributes_ui.py``, ``test_terrain_effective_attributes.py``.

**Corrección: Tab ya no encuentra salidas en casillas nunca exploradas**

- **Síntoma**: En casillas nunca visitadas, Tab podía anunciar salidas del otro lado.
- **Causa**: La niebla recordaba salidas opuestas antes de entrar realmente.
- **Corrección**: Sin ``scouted_squares`` ni ``scouted_before_squares``, resumen / visibilidad en blanco; la niebla estática tras visitar sigue permitiendo Tab.
- **Código**: ``clientgame/game_unit_control.py``.
- **Pruebas**: ``test_unknown_square_tab_blank.py``.

**Corrección: pitido ``order_impossible`` tras matar un animal con Retroceso**

- **Síntoma**: Tras el ataque por defecto a un animal cazable, sonaba ``order_impossible``.
- **Causa**: ``AttackOrder`` trataba la desaparición del objetivo como fallo.
- **Corrección**: Completar la orden si el objetivo desaparece o ``hp <= 0``.
- **Código**: ``worldorders/movement.py``.
- **Pruebas**: ``test_hunting.py``.

**Corrección: orden por defecto sobre neutrales y daño de caza**

- ``go`` normal / por defecto sobre neutrales (no imperativo) solo mueve, sin AttackAction sin daño.
- ``attack`` normal sobre ``is_huntable`` (incluida caza por defecto con Retroceso) hace daño; solo el ataque imperativo hace que la IA trate neutrales como objetivos automáticos.
- **Código**: ``worldunit/world_ai_decision.py``, ``worldunit/worldcreature.py``.
- **Docs**: ``player/hunting.rst``, ``player/unit-default-behavior.rst``.
- **Pruebas**: ``test_neutral_no_auto_attack.py``, ``test_neutral_go_and_hunt_attack.py``.

**Solución: fallo al actualizar la percepción del jugador Computer (falta ``_buckets``)**

- **Síntoma**: Durante la partida (sobre todo con IA ``computer_only`` del mapa, aliados IA o tras cargar una partida) podía fallar en la fase de percepción del bucle principal con ``AttributeError: 'Computer' object has no attribute '_buckets'``.
- **Causa**: El índice espacial del jugador ``_buckets`` solo se inicializaba en el envoltorio ``Player.__init__``; guardar/cargar elimina ese campo de caché; las comprobaciones de visibilidad aliada en bloque (``bulk_visibility_check``) llaman a ``_potential_neighbors`` de los aliados y fallaban si un ``Computer`` aún no tenía ``_buckets``.
- **Solución**: Preinicializar ``_buckets`` en ``BasePlayer.__init__`` junto con las demás cachés de percepción; ``_potential_neighbors`` usa un diccionario vacío si falta; ``update_alliance`` borra la caché de instancia ``allied_vision`` para que un cambio de alianza no siga usando listas de aliados obsoletas.
- **Código**: ``worldplayerbase/base.py``, ``worldplayerbase/perception.py``, ``worldplayerbase/__init__.py``.
- **Pruebas**: ``test_meteors_computer_only.py``, ``test_phase3_parity.py``, ``test_neutral_passive_creep.py``.


1.4.5.1
-------

**Mejora: cobertura de terreno, modificadores por unidad y notación porcentual**

- ``class terrain`` en ``rules.txt`` admite ``cover <suelo> <aire>``, igual que ``speed``: ``terrain marsh h8`` en el mapa hereda cobertura por defecto; las líneas ``cover`` del mapa siguen anulando casillas concretas.
- El terreno puede modificar **tipos de unidad** con ``speed_vs``, ``cover_vs``, ``dodge_vs``, ``mdg_vs``, ``rdg_vs``, ``mdg_cd_vs``, ``rdg_cd_vs`` (p. ej. ``speed_vs knight .25 archer .5``). Basta con ``*_vs`` sin ``speed``/``cover`` global.
- Esos ``*_vs`` y ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` (y ``charge_*_terrain``) usan **porcentajes decimales 0–1** (``.5`` = ±50%%, ``.1`` = ±10%%) respecto al daño o enfriamiento base actual de la unidad.
- ``speed_on_terrain`` sigue siendo **velocidad absoluta** (distinto de ``speed_vs`` en porcentaje).
- ``speed`` / ``cover`` del mapa afectan a **todas** las unidades de la casilla; las diferencias por unidad van en el terreno o en el def de la unidad en ``rules.txt``.
- **Código**: ``worldterrain.py``, ``lib/square_terrain_rules.py``, ``world/world_map.py``, ``combat/hit_miss.py``, ``combat/damage_calculation.py``, ``combat/attack_action.py``, ``worldunit/world_movement.py``; mapas aleatorios emiten líneas ``cover`` (``rmg_templates.terrain_cover_line``).
- **Documentación**: ``mod/building-land-terrain.rst``; comentarios en ``res/ui/editor_palette.txt``.
- **Pruebas**: ``test_terrain_cover_defaults.py``, ``test_terrain_unit_vs.py``, ``test_unit_on_terrain_percent.py``; ``test_combat_terrain_modifiers.py`` actualizado a casos porcentuales.

Corrección de errores y mejoras en la experiencia de usuario de voz/audio:

**Corrección: enfriamiento de ataque cuerpo a cuerpo/a distancia (``mdg_cd`` / ``rdg_cd``) más lento que en rules**

- **Síntoma**: Con 1 s de enfriamiento en rules (p. ej. campesino ``mdg_cd 1``), el intervalo real era notablemente mayor que en 1.3.8.1 (~1,5 s frente a ~1,2 s; lo segundo es solo cuantización del tick de 300 ms).
- **Causa**: (1) Con ``mdg_ready`` / ``rdg_ready`` en 0, la rama de preparación consumía un tick extra antes de golpear; (2) los impactos instantáneos (``mdg_delay`` / ``rdg_delay`` 0) pasaban por un mínimo de 100 ms en ``_schedule_ballistic_hit``; (3) ``attack_action.aim()`` y ``damage_effects._schedule_ballistic_hit`` establecían ambos el enfriamiento, con una segunda escritura tras el retraso que alargaba ``next_attack_time``.
- **Corrección**: omitir preparación cuando ``ready=0`` y atacar al instante; sin suelo de 100 ms para impactos instantáneos; el enfriamiento se establece una sola vez en ``attack_action.aim()`` al iniciar el ataque.
- **Nota**: ``charge_mdg_cd`` / ``charge_rdg_cd`` usan otra ruta (``receive_hit`` inmediato, sin preparación/programación balística) y no se vieron afectados; el ritmo mixto carga + ataque normal mejora indirectamente con la corrección del CD normal.
- **Código**: ``combat/attack_action.py``, ``combat/damage_effects.py``.
- **Pruebas**: ``test_attack_cooldown_timing.py``.

**Mejora: rechazo de órdenes go y aviso de voz en terreno intransitable**

- Las unidades terrestres que ordenan ``go`` / ``patrol`` a casillas con ``is_ground 0``, o las aéreas a ``is_air 0``, reciben rechazo al encolar con ``ground_impassable`` / ``air_impassable``.
- Terreno con ``passable_units``: unidades fuera de la lista escuchan el título del tipo de unidad más «no puede pasar» (p. ej. footman, knight); los tipos en la lista (incl. ``is_a``) siguen pudiendo ``go``.
- **Código**: ``worldorders/base.py``, ``lib/square_terrain_rules.py``, ``clientgameentity/events.py``. **Voz**: ``messages`` 4979, 5700, 5701. **Pruebas**: ``test_water_impassable_order.py``.

**Solución: fantasma de niebla sin nombre después del suicidio de la unidad**

- **Síntoma**: Después de que una unidad se suicida, los objetivos que se mueven con tabulaciones en el mismo cuadrado aún podrían seleccionar un objeto sin un nombre legible.
- **Causa**: Después de la muerte ``place is None``, la memoria de la niebla de guerra no se borró a tiempo; Los objetos de memoria podían tener un ``title`` (sufijo de niebla) pero un ``short_title`` vacío, pero Tab aún los trataba como seleccionables.
- **Solución**: ``perception.py`` olvida la memoria cuando ``initial_model.place is None``; las unidades que salen de la percepción no se memorizan cuando ``place is None`` o cuando son las unidades muertas del propio jugador; ``game_unit_control.py`` ``is_visible`` requiere un ``short_title`` que no esté vacío.
- **Pruebas**: ``test_suicide_fog_ghost.py`` (se conservan la memoria de niebla del cadáver y las rutas de audio ambiental).

**Solución: el HP de la pared parpadeaba hacia arriba y hacia abajo mientras se ataca**

- **Síntoma**: Atacar ``wall`` y otros edificios ``is_repairable`` podría hacer que los HP o los sonidos que cambian la vida suban y bajen de forma intermitente.
- **Causa**: Los muros heredan ``is_repairable=True`` de los edificios, por lo que la lógica de ataque/reparación/umbral de captura podría interactuar; La sincronización de HP de niebla (``_sync_memory_hp_from_live``) sin llevar ``previous_hp`` a través de los intercambios de vista de percepción/memoria causó comentarios falsos sobre el cambio de vida.
- **Solución**: ``world_order.py`` / ``worldcreature.py`` / ``worldworker.py``: los edificios enemigos reparables por defecto son ``go``, los imperativo por defecto son ``attack``; reparar caminos vigilados con ``not is_an_enemy(target)``; ``game_navigation.py`` conserva el seguimiento de HP en las actualizaciones de niebla (``_take_hp_tracking`` / ``_apply_hp_tracking``).
- **Pruebas**: ``test_imperative_attack.py`` (ataque imperativo a paredes).

**Solución: la orden go normal interrumpía incorrectamente el ataque imperativo**

- **Síntoma**: Con una unidad en ataque forzado (p. ej. ayuntamiento), un ``go`` normal detenía el ataque, pero la selección de grupo (p. ej. F) seguía anunciando «atacar el ayuntamiento, ir a \<casilla\>» — comportamiento y voz incoherentes.
- **Causa**: ``take_order`` con ``forget_previous=True`` llamaba a ``cancel_all_orders()``, eliminando el ataque imperativo y encolando ``go``, mientras ``AttackAction`` podía permanecer en la unidad.
- **Solución**: Con una orden imperativa activa, los comandos normales (excepto ``stop``) se encolan automáticamente (``forget_previous=False``) sin reemplazar la cabeza imperativa; la unidad termina el ataque forzado antes del comando en cola. Tras un imperativo solo se permite **un** comando en cola; un nuevo comando normal **reemplaza** el ya encolado (igual que en 1.3.8.1).
- **Código**: ``worldunit/world_order.py`` ``take_order``.
- **Pruebas**: ``test_imperative_attack.py`` (``test_normal_go_queues_behind_imperative_attack``, ``test_only_one_queued_order_behind_imperative_attack``, etc.).

**Mejora: descripciones de voz del comportamiento de la unidad**

- Después de seleccionar un objetivo con la tecla Tab, Ctrl+Retroceso o ir + Ctrl+Entrar confirma "atacar \<objetivo\>" en lugar de "ir" para las unidades/edificios enemigos.
- Selección de grupo de teclas de acceso rápido (por ejemplo, F para lacayos): "Tú controlas N lacayos que atacan el ayuntamiento"; si se mueve mientras pelea, agrega "ir a c6".
- **Código**: ``clientgameentity/base.py`` ``_attack_action_title_msg``; ``properties.py`` ``orders_txt``; ``game_orders.py`` ``_say_validate_confirmation`` / ``_say_default_confirmation``; ``game_unit_control.py`` ``say_group``.
- **Pruebas**: ``test_attack_orders_txt.py``, ``test_imperative_attack.py``.

**Mejora: gritos de batalla en capas**

- Tres capas: ``shout_bg`` (fondo del campo de batalla), ``shout_unit`` (voz de la unidad), ``shout_event`` (primer choque/carga/críticos destacados); tiempos de reutilización globales y por cuadrado; ``formation_sound_queue`` escalona las ráfagas para que los gritos no se acumulen con los sonidos de los golpes en el mismo cuadro.
- **Código**: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``.
- **Documentos**: ``mod/battle-shouts.rst``.
- **Pruebas**: ``test_battle_shout_audio.py``.

**Mejora: refactorización del motor de audio P0–P2**

- **Corrección**: borradores anteriores describían P0–P2 como capas de *prioridad* ambiental/combate/alertas; en realidad son **tres fases de refactorización** del motor de audio, distintas de los gritos en capas anteriores y de ``psounds.play(..., priority=…)``. Ver ``mod/audio-management.rst``.
- **P0 estructura**: ``lib/music_resolver.py``; ``sound_cache.clear_decoded()`` al cambiar mod/mapa; corrección de estado mutable en ``SoundSource`` / ``SoundManager``.
- **P1 UX**: ``audio/sfx_volume`` separado de ``main_volume``; espera de voz por event pump; fallback de música de menú unificado.
- **P2 pulido**: LFO de ambiente; ``lib/battle_music.py``; limpieza de ``music_resolver``; SFX en ``ui/`` con ``.ogg`` / ``.wav`` / ``.mp3`` (``.ogg`` preferido) y precarga en caliente (``preload_sounds`` / ``tick_preload``).
- **Atajos**: Home/End para SFX; Alt+Home/Alt+End para música.
- **Pruebas**: ``test_music_resolver.py``, ``test_audio_settings.py``, ``test_voice_pump.py``, ``test_ambient_stereo_volume.py``, ``test_battle_music.py``, ``test_sfx_formats.py``.

1.4.5.0
-------

Terreno configurable, contenedores de transporte, ``attack_inside_chance`` y mapas aleatorios:

**Terreno cuadrado configurable**

- El terreno es ``class terrain`` en ``rules.txt`` más las definiciones coincidentes de ``style.txt``; no hay terreno predeterminado en todo el motor en cada celda.
- El mapa ``terrain <name>`` aplica la transitabilidad, el agua, la velocidad y el terreno elevado según las reglas; ``class building_land`` amplía prados y zonas de construcción.
- Editor de mapas y subcelda ``square/x,y`` sintaxis: ``mod/building-land-terrain.rst``.

**Contenedores de transporte**

- ``passenger_attack_types``: tipos de unidades que pueden atacar objetivos externos mientras están dentro del contenedor.
- ``load_bonus``: por unidad cargada, agrega estadísticas al contenedor.
- ``passenger_bonus``: estadísticas agregadas al pasajero mientras está dentro; eliminado durante la descarga. Misma sintaxis que ``load_bonus``; Se puede combinar con ``load_bonus``.

**``attack_inside_chance``**

- Propiedad de contenedores abiertos: los ataques externos afectan a los pasajeros que se encuentran dentro en este porcentaje (por ejemplo, la pared ``attack_inside_chance 40``).

**Generador de mapas aleatorios**

- Las plantillas integradas enumeran cada terreno ``rmg_terrain 1`` según las reglas; La ubicación utiliza propiedades de reglas.
- Archivos ``random_map_template`` personalizados en ``cfg/randommap/`` o ``mods/.../randommap/``.
- Códigos compartidos: ``RMG1`` (abreviaturas integradas) / ``RMG2`` (nombres personalizados completos).

Véase ``mod/building-land-terrain.rst``, ``mod/randommap.rst``, ``mod/modding.rst`` (Contenedores de transporte); pruebas ``test_transport_bonus.py``, ``test_attack_inside_chance.py``, ``test_randommap.py``.

**Construyendo puentes sobre el agua**

- Los trabajadores pueden colocar tramos de ``wooden_bridge`` losa por losa en ríos, lagos y océanos (``is_buildable_on_water_only`` + ``bridge_terrain bridge_deck``).
- Fase de andamio: construcción transitable, sin paso hasta que esté completo; los tramos terminados se conectan con la costa o con otras cubiertas; neutral para todos los jugadores.
- El TTS del sitio coincide con otras entradas ``buildingsite``; pasos use ``bridge_deck`` / ``big_bridge`` ``ground wood``.
- Documentos: ``mod/water-bridge-building.rst``; pruebas: ``test_bridge_terrain.py``.

**Modificadores de combate de unidades en el terreno**

- ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``: ataque por terreno, enfriamiento y bonificaciones de carga para el **cuadro actual del atacante** (igual ``terrain value …`` enumera la sintaxis como ``speed_on_terrain``).
- Los modificadores de daño negativos debilitan los ataques; positivo ``*_cd_on_terrain`` alarga el tiempo de reutilización.
- Documentos: ``mod/building-land-terrain.rst``; pruebas: ``test_combat_terrain_modifiers.py``.

**Pasos del terreno y sonidos de caídas**

- ``move_on_<key>`` / ``falling_on_<key>`` ahora aceptan **nombres de tipo de terreno** (por ejemplo, ``ocean``) y categorías ``style.txt`` ``ground`` (por ejemplo, ``water``, ``grass``); Primero se prueba el nombre del tipo.
- Solución: en terrenos sin ``ground`` (por ejemplo, ``ocean``), ``falling_on_ocean`` nunca había coincidido anteriormente y solo se jugaba el ``falling`` genérico.
- Documentos: ``mod/modding.rst`` (Sistema de sonido de combate); pruebas: ``test_falling_terrain_sound.py``.

**Gritos de batalla (reproducción en capas)**

- Tres capas de combate: fondo del campo de batalla, voz de la unidad, momentos destacados del evento; tiempos de reutilización globales/por cuadrado.
- ``ui/style.txt``: ``shouts`` en ``def walking_unit``; Se activa cuando cualquiera de los bandos tiene ≥5 unidades de combate en el cuadrado.
- Código: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``; pruebas: ``test_battle_shout_audio.py``.
- Documentos: ``mod/battle-shouts.rst``.

1.4.4.9
-------

Se corrigió un error por el cual la distancia mínima de carga efectiva no funcionaba.

Se actualizó la documentación.

1.4.4.8
-------

Terreno de subceldas para autores de mapas y el editor de mapas:

Terreno de subcelda dentro de un cuadrado.

- Los comandos de terreno pueden apuntar a un área dentro de un cuadrado con sintaxis ``square/x,y``, por ejemplo ``high_grounds a1/1,1 a1/1,2``.
- ``subcell_precision N`` controla la subdivisión. El valor predeterminado es ``3`` y acepta valores de ``2`` a ``20``.
- Comandos admitidos: ``terrain``, ``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` y ``no_air``.
- El combate, el movimiento, la velocidad del terreno, la cobertura y las comprobaciones en terreno elevado pueden utilizar la subcélula real de la unidad.

Comportamiento del editor y navegación de Zoom

- La exploración del mapa en modo zoom anuncia el terreno actual de la subcelda, incluido el terreno elevado parcial.
- En el editor de mapas experimental, Enter aplica el terreno seleccionado a la subcelda actual mientras el modo de zoom está habilitado.
- Los mapas guardados escriben anulaciones de subceldas con la sintaxis ``square/x,y``.

1.4.4.7
-------

Fórmulas de umbral de XP de héroe (``xp_threshold_growth``) y restablecimiento de XP posterior al nivel (``level_up_reset_xp``):

``Hero XP threshold formulas (``xp_threshold_growth``)``

- Las definiciones de héroe se pueden configurar ``max_level`` + ``xp_threshold_growth``; ``rules.txt`` carga los autocompletados ``xp_thresholds`` para que los modders no tengan que enumerar a mano docenas o cientos de valores de XP acumulativos.
- Tipos de curvas: ``linear``, ``quadratic``, ``polynomial``, ``geometric`` (ver Héroes en ``modding.rst``).
- Compatible con versiones anteriores con ``xp_thresholds`` explícito (la lista explícita gana). Las definiciones secundarias pueden ``is_a`` heredar ``xp_threshold_growth`` y anular solo ``max_level``.
- Implementación: ``soundrts/xp_threshold_growth.py``, ``soundrts/definitions.py``; pruebas: ``test_xp_threshold_growth.py``.

``Post-level-up XP reset (``level_up_reset_xp``)``

- Opcional ``level_up_reset_xp 1`` en definiciones de héroe: la XP actual se vuelve 0 después de cada nivel de combate; El valor predeterminado ``0`` mantiene XP acumulativo.
- Cuando ``1``, prefiera ``xp_thresholds`` por nivel, no totales acumulativos.
- Implementación: ``soundrts/worldunit/world_status_update.py``; pruebas: ``test_level_up_combat_stats.py``.

1.4.4.6
-------

Limpieza de nombres de sonido de mod, sistema de habilidades unificado, efectos de habilidades genéricas, filtros de objetivos de habilidades y exclusiones de etiquetas, escalamiento de estadísticas de nivel, desbloqueo de habilidades de nivel, transferencia de héroe de campaña, sonidos de uso de elementos de mochila, sonidos de preparación/listo personalizados, alternancia de teclas de acceso rápido de mochila/equipo, nivel inicial de héroe y visualización de XP de nivel 0:

Cambio de nombre de clave de sonido de ataque

- Los sonidos de ataque ``ui/style.txt`` ahora prefieren las teclas ``mdg`` / ``rdg``:
  ``launch_mdg`` / ``launch_rdg``, ``mdg_hit`` / ``rdg_hit``,
  ``mdg_hit_vs`` / ``rdg_hit_vs``, ``mdg_missed`` / ``rdg_missed``,
  y ``mdg_dodge`` / ``rdg_dodge``.
- Los sonidos de carga usan ``launch_charge_mdg`` / ``launch_charge_rdg`` y
  ``charge_mdg_hit`` / ``charge_rdg_hit``.
- Se han migrado los archivos empaquetados ``style.txt``; Las antiguas claves ``matk`` / ``ratk`` siguen siendo compatibles como alternativa.

Sonidos listos para personalizar

- Las habilidades con ``ready \<seconds\>`` pueden definir ``ready \<sound\>`` en el estilo de habilidad; Los disparadores manuales y automáticos lo reproducen cuando comienza la preparación.
- La preparación de ataque normal puede reproducir sonidos del estilo de unidad ``mdg_ready`` / ``rdg_ready``.

Sistema de habilidades unificado

- Un ``class skill`` puede usarse tanto manualmente como activarse automáticamente; no se requieren listas de gemelos separadas.
- Campos de habilidad: ``auto_trigger 1``, ``manual_use 1`` (predeterminado 1), ``trigger_timing``.
- ``trigger_timing``: ``on_hit`` | ``on_attack`` | ``on_attack_replace`` | ``on_damaged``.
- Las habilidades aprendidas se encuentran en ``can_use_skill``; el menú de comandos muestra solo las habilidades ``manual_use 1``.
- Las listas heredadas aún funcionan: ``active_trigger_skills``, ``attack_trigger_skills``,
  ``attack_replace_skills``, ``passive_trigger_skills`` siguen siendo compatibles junto con los nuevos campos.

Efectos de habilidades genéricas

- Se corrigió el daño ``harm_target N`` / ``harm_area N R``; daño de combate ``harm_target mdg`` / ``harm_area mdg R`` (tubería completa).
- Combinaciones ``burst mdg N (interval X)`` o `` (delays …)``; retroceso ``push``; ``buffs`` / ``debuffs``; ``deploy``; ``summon``.
- Legacy ``teleportation`` / ``recall`` / ``conversion`` / ``raise_dead`` / ``resurrection`` todavía funciona.
- Las tasas de activación, las condiciones de HP y las listas de ventajas/desventajas de inicio de ataque siguen siendo compatibles; ver ``mod/skills-and-effects.htm``.

``Target type filters and exclusions (``-etiqueta``)``

- ``class skill`` admite ``harm_target_type`` en ``burst`` / ``harm_target`` / ``harm_area`` / ``push``; enemigos predeterminados solo cuando no están configurados.
- El prefijo ``-`` excluye una etiqueta (por ejemplo, ``-building``). Se aplica a ``harm_target_type``, ``heal_target_type``, ``mdg_targets`` / ``rdg_targets``, mejora/desventaja ``target_type``.
- Exclusiones de diplomacia: ``-enemy``, ``-allied``, ``-neutral``.
- Ejemplos: ``harm_target_type enemy unit -building``; ``heal_target_type unit -undead``; ``mdg_targets -building``.

**Bonificaciones de estadísticas por subir de nivel (``*_per_level``)**

- Las unidades pueden configurar ``\<stat\>\_per_level`` en ``rules.txt`` para la mayoría de las estadísticas de combate, vida, maná, curación/daño y regeneración; cada nivel sube agrega un paso.
- Ejemplos: ``hp_max_per_level``, ``mdg_per_level``, ``charge_mdg_per_level``, ``mdg_crit_rate_per_level``, ``mana_max_per_level``, ``heal_cd_per_level``, etc.
- La restauración del héroe de campaña vuelve a aplicar bonificaciones acumulativas hasta el nivel guardado.

Nivel inicial del héroe y visualización de estado.

- ``level`` / ``xp`` en definiciones de héroe en ``rules.txt`` (requiere ``xp_thresholds``); ``level \> 1`` aplica ``*_per_level`` acumulativo al generar.
- ``level 0``: empezar por debajo del nivel 1; El estado de la pestaña muestra el nivel 0 y XP hacia ``xp_thresholds[0]``.
- Los héroes con ``xp_thresholds`` siempre anuncian el nivel en el estado de pestaña (incluidos 0 y 1).

``Full heal on level up (``level_up_heal_full``)``

- Opcional ``level_up_heal_full 1`` en definiciones de héroe: restaura HP y maná completos en cada nivel superior; El valor predeterminado ``0`` mantiene solo la ganancia incremental de HP/maná.

Desbloqueos de habilidades de nivel y libros de habilidades.

- Unidad ``level_skills \<level\> \<skill\> …``: se agrega automáticamente a ``can_use_skill`` cuando se alcanza ese nivel (con notificación de voz).
- Unidad ``learn_level_skills``: puerta de nivel de aprendizaje de libros adicional (más estricta con el elemento ``learn_level``).
- Libros de habilidades: aprendizaje permanente mediante mochila ``use_item``; la recogida no se concede cuando está cerrada.
- No dupliques la misma habilidad en ``level_skills`` y un libro.

Transferencia de héroe de campaña

- Definiciones de héroe: ``campaign_carryover 1`` (opcional ``campaign_carryover_stats``, ``campaign_carryover_inventory``, ``campaign_carryover_id``).
- Al ganar, el nivel/XP y la mochila se guardan en ``user/campaigns.ini``; el próximo capítulo se restaura; La cooperativa no persiste.
- Opcional ``hero_min_level 13:2 …`` en ``campaign.txt`` para pisos nivelados por capítulo.

Sonidos de uso de elementos de mochila (style.txt)

- Misma búsqueda de tres niveles que recoger/entregar: artículo ``use`` / ``on_use`` → unidad ``use_\<item type\>`` → global ``item_used`` (``def thing``).
- Los sonidos se reproducen sólo después de que el servidor haya confirmado el éxito; no hay voz optimista "usada" en Enter.
- Libros de habilidades: usar sonido + título de habilidad + ``skill_learned``; otros consumibles: título del artículo + "usado".
- Los consumibles se eliminan del inventario en caso de éxito; El libro de habilidades ``unequip`` ya no elimina las habilidades aprendidas permanentemente.

Teclas de acceso rápido para mochila/equipo

- Shift+V alterna entre mochila y equipo (clásico y en capas); Ctrl+V eliminado; F3 en capas todavía funciona.

Documentos: ``mod/modding.rst``, ``mod/modding.rst``, ``mod/skills-and-effects.htm``, ``mod/campaign-hero-carryover.htm``
Pruebas: ``test_level_skills.py``, ``test_level_up_combat_stats.py``, ``test_campaign_hero.py``, ``test_wuxia_skills.py``, ``test_worldskill_deploy.py``, ``test_target_type_exclusions.py``, ``test_hit_vs_buff_sounds.py``, ``test_damage_seq_burst.py``,
``test_changelog_138x.py``, ``test_skill_trigger_sounds.py``, ``test_inventory_backpack.py``

1.4.4.5
-------

Mapa aleatorio estilo HoMM/Civ5, orden de captura predeterminado, operaciones anfibias de IA, corrección de puntuación Ctrl+Shift+F4, editor de mapas de teclas de acceso rápido:

Mapa aleatorio: inspirado en HoMM/Civ5

- menú del modo victoria: conquista / económico / exploración / supervivencia (TTS 5425–5430)
- PDI del mapa: ruinas antiguas, cuarteles capturables, creeps centrales, tesoro opcional
- compartir códigos: 11º campo de victoria; ``res/rules.txt``: ``ancient_ruin``, ``captured_barracks``
- documentos: ``player/homm-civ5-play.htm``; ``randommap.rst``
- pruebas: ``test_randommap.py``

Orden de captura predeterminado (can_capture)

- ``capture_hp_threshold 100``: ``can_capture 1`` → ocupación predeterminada; ``can_capture 0`` → atacar/mover solo
- los umbrales por debajo de 100 aún requieren combate para capturar el umbral
- documentos: ``mod/modding.rst``; jugadores ``player/unit-default-behavior.htm`` §4
- pruebas: ``test_capture_default_order.py``

Operaciones de IA entre aguas

- reunión anfibia, asaltos de transporte, mantenimiento naval en mapas acuáticos
- pruebas: ``test_worldplayercomputer_water.py``, ``test_ai_naval_m3.py``

Tren: escalar lote a la población restante

- espacio insuficiente para el pop cuando se entrena por lotes → entrenar tantos como sea posible (por ejemplo, 5 solicitados, 3 pop → 3 entrenados); El margen cero sigue fallando
- ``worldorders/production.py`` (``TrainOrder._max_train_count_for_population``)
- pruebas: ``test_train_population.py``

Solución: Ctrl+Shift+F4 cambio de vista frente a puntuación

- puntuación humana; sin recompensas de victoria pasivas o de IA después del cambio; Línea de base de enemigos derrotados que puntúan en el primer cambio.
- pruebas: ``test_change_player_scoring.py``

Editor de mapeo de teclas de acceso rápido

- Opciones → Mapeo de teclas (hermano del esquema de teclas de acceso rápido); ``hotkey_remapping_menu.py``, ``hotkey_editor.py``, ``hotkey_catalogs.py``
- 8 capas en capas + ~179 fijaciones clásicas; por mod ``user/hotkey_overrides/{mod_key}.json``; inicio efectivo del próximo juego
- búsqueda, variantes avanzadas, claves de alias (``binding_id@default_key``), importación/exportación del portapapeles
- catálogo TTS 5500–5684; variantes avanzadas clásicas completas; correcciones de etiquetas de grupo de control
- etiquetas: Alt+Espacio → modo en primera persona; Ctrl+F2 → alternar pantalla
- documentos: ``mod/hotkey-mapping-editor.htm``, ``player/layered-hotkeys.htm``
- pruebas: ``test_hotkey_editor*.py``, ``test_hotkey_catalog_tts.py``, ``test_hotkey_editor_mod_isolation.py``

1.4.4.4
-------

Tarjetas de carga retrasadas, puntuación y calificaciones, logros por facción, metaprogreso, CrazyMod, correcciones de UX:

Tarjetas previas a la misión retrasadas

- ``cards.txt``: ``delay \<seconds\>``, ``delay_minutes \<n\>`` — efectos del programa después del tiempo de juego (``world.schedule_after``, respeta ``timer_coefficient``)
- ``tech \<upgrade_id\>`` en tarjetas; combinable con ``spawn`` / ``resource`` bajo un retardo compartido
- voz al aplicar: efectos después de N minutos/segundos; en llamas: efecto de tarjeta de equipamiento activado (TTS 5387–5393)
- vainilla: ``card_reinforcements_delayed`` (3 lacayos después de 10 min), ``card_delayed_melee_weapon`` (``melee_weapon`` después de 8 min)
- logros: ``reinforcement_contract`` → refuerzos retrasados; ``defeat_expert`` → tarjeta de arma cuerpo a cuerpo retrasada
- documentos: ``mod/delayed-card-loadout.htm`` (jugadores: ``player/loadout-cards.htm``)
- pruebas: ``test_cards.py``, ``test_card_loadout.py`` (``-k delay`` / ``-k delayed``)

Puntuación y calificaciones con letras después del juego

- documentos: ``mod/score-grading-system.htm`` (jugadores: ``player/score-and-grades.htm``)
- base de siete dimensiones con límite de 800; La bonificación por derrota de la IA es adicional y está excluida del denominador porcentual.
- grado de derrota limitado a D (``grade_total`` máx. 479)
- ganar + utilización < 50%: dimensión de eficiencia frugal (TTS 5251)
- minería en mapas sin capacidad de depósito: proporcional a la recopilación de referencia (1000 = 100 pts); mapas de campaña sin depósito sin cambios
- supervivencia 0 si no se producen unidades; pérdida/demolición de edificios 5 puntos por edificio (en lugar de 10)
- Se eliminaron los ayudantes de puntuación heredados no utilizados de ``worldplayerbase/resources.py``.
- pruebas: ``test_score_breakdown.py``

Logros y datos de clasificación

- Teniente (``rank_lieutenant``): 200 medallas, 1 espacio de equipamiento
- ``defeat_beginner`` repetir medalla 8; ``perfect_survival`` requiere supervivencia ≥90 y construcción de defensa ≥90

Correcciones

- trabajador ``can_gather all``: la interfaz de usuario del atributo ya no duplica "todos" cuando las listas de depósito y construcción son ambas ``all``
- pruebas: ``conftest`` restaura ``res.mods`` después de las pruebas de cambio de mod
- equipamiento/UX de facción aleatoria; Transmisión de derrota de NPC bloqueada por ``broadcasts_defeat_and_quit``

Progreso por facción y meta

- ``achievements_per_faction 1``, ``\_meta.json``, ``scope meta``; campaña excluida

LocoMod 9

- hitos por facción, metaniveles, ajustes de equilibrio

Documentación (reproductor/desarrollador)

- Índice: ``help-index.htm``, ``player/README.htm``, ``mod/README.htm``

Transferencia de héroe de campaña (según reglas)

- ``rules.txt``: ``campaign_carryover 1`` (opcional ``campaign_carryover_id``, ``campaign_carryover_stats``, ``campaign_carryover_inventory``)
- ``campaign.txt``: ``hero_min_level 13:2 …`` para niveles de piso de capítulos
- salvado en victoria a ``user/campaigns.ini`` (``hero_\<id\>\_xp`` / ``\_level`` / ``\_inventory``); restaurado el siguiente capítulo; la cooperativa no persiste
- independiente de ``campaign_flag`` / ``add_inventory_item``; ver ``modding.rst``, ``mapmaking.rst``, ``mod/campaign-hero-carryover.htm``
- implementación: ``soundrts/campaign_hero.py``; pruebas: ``test_campaign_hero.py``

Correcciones y voz

- mapas de carriles: ``has_entered`` con coordenadas basadas en 1 (por ejemplo, ``8,2``) ya no choca con las claves de cuadrícula basadas en 0; la ruina desencadena el trabajo
- entradas de texto (compartir código, semilla, etc.): Ctrl+V pegar a través de la API del portapapeles pygame-ce
- HoMM/Civ5 y TTS de misiones secundarias de campaña se movieron de 5107–5123 a 5425–5441 para evitar conflictos de identificación.

1.4.4.3
-------

Logros y arsenal (fases 2 y 3: medallas, rangos, cartas, equipamiento previo a la misión):

- nueva entrada de Logros del menú principal: lista de logros + armería (rango, honores, total de medallas, cargos de tarjeta)
- después de una escaramuza/mapa aleatorio contra computadora, se evalúan los desbloqueos de ``achievements.txt``; voz para desbloqueos, medallas, tarjetas, ascensos de rango y espacios de equipamiento adicionales
- el progreso se guarda por mod: ``user/achievements/\<mod\>.json``
- Carga de cartas previa a la misión: Un jugador → Iniciar en el mapa → Iniciar, luego recoger hasta N cartas por rango (Teniente = 1 espacio, Capitán = 2,… en ``titles.txt``); Solo TrainingGame (mapa personalizado o aleatorio versus IA, no campaña ni multijugador)
- los efectos se aplican al inicio del juego: recursos adicionales y/o unidades cerca de tu inicio; un cargo gastado por tarjeta utilizada
- la generación de cartas no utiliza población; los engendros aleatorios de facciones usan equivalentes de facciones
- solución: las tarjetas de equipamiento no se aplicaron porque el jugador local solo se detectó después de que existiera ``GameInterface``; ahora se aplica después de cargar el mapa, antes de que se abra la interfaz
- Armería: al explorar una carta se habla de su efecto (bonificación inicial, aparición, rango requerido si está bloqueado)
- Repetir finalización: volver a alcanzar un logro ya desbloqueado otorga solo medallas ``repeat_medal \<n\>`` (sin tarjeta, honor ni voz de desbloqueo); las medallas aún avanzan en el rango
- exclusión voluntaria del mod: ``achievements_enabled 0`` en ``rules.txt`` oculta la entrada del menú y omite el procesamiento de carga/post-juego
- ``AI ``starting_units`` bonuses in ``ai.txt`` do not consume population`` (los inicios del mapa todavía funcionan); ``starting_population`` no ha cambiado
- datos: ``res/achievements.txt``, ``res/cards.txt``, ``res/titles.txt``; Identificadores TTS 5244–5367, etc.
- documentos: ``achievement-system.htm`` (``achievement-system.htm``)
- pruebas: ``test_achievements.py``, ``test_cards.py``, ``test_titles.py``, ``test_card_loadout.py``

1.4.4.2
-------

Contraobjetivo de IA (``counter_skill`` en ``ai.txt``):

- las unidades informáticas utilizan ``mdg_vs`` / ``rdg_vs`` (y herencia ``is_a``) al seleccionar objetivos y enviar ataques
- nuevo comando de script ``counter_skill \<0-100\>``: ``0`` = ignorar contadores (solo ``menace``), ``100`` = elegir siempre el mejor contador; Los valores intermedios combinan ambos.
- niveles básicos en ``res/ai.txt``: principiante ``25``, intermedio ``50``, avanzado ``75``, experto ``90``, pesadilla ``100``; omitido en un script mod por defecto es ``100``
- nuevo ``starting_resources`` / ``starting_units`` en ``ai.txt``: recursos y unidades adicionales agregados en la parte superior del inicio del mapa para las computadoras invitadas (la misma sintaxis que los comandos del mapa; se aplica una vez al inicio del juego, no en el bucle del script)
- nuevo ``starting_population`` en ``ai.txt`` y mapas: límite de población adicional (entero simple, no ×1000) agregado encima de las casas/unidades; todavía limitado por ``global_population_limit``
- inicios de bonificación básica: recursos intermedios +50/+50; avanzado +100/+100 y 2 lacayos 2 arqueros; experto +200/+200 y ejército 5/4/2; pesadilla +400/+400 y 8/6/4 ejército
- documentos: ``doc_src/src/en/aimaking.rst``, ``doc_src/src/zh/aimaking.rst``
- pruebas: ``test_ai_counter_targeting.py``, ``test_ai_loader_and_menu.py``, ``test_ai_start_settings.py``

1.4.3.9
-------

Teclas de acceso rápido de interfaz en capas (base global + capa por modo):

- ``bindings.txt`` único dividido en ``global_bindings.txt`` y siete archivos de modo (unidad/edificio/comando/skill/help/map/diplomacy); orden de carga: global → modo actual → ``cfg/bindings.txt`` → mod anexar
- Cambio de tecla F: unidad F1↔edificio, comando F2↔habilidad, inventario F3↔equipo, ayuda y consulta F4, diplomacia F12, exploración de mapa de entrada/salida ESC; nombre del modo anunciado en el interruptor
- la capa global mantiene recursos (z/x/SHIFT z/c), movimiento, saltos cuadrados, confirmación de comando, F9/F11, etc.; La antigua ayuda F1/F4 y la diplomacia directa F12 ahora ingresan a modos de superposición dedicados.
- modo de unidad: trabajadores ``s``/``w`` (antes ``d``/``e``); soldados 1 a 7 en ``d/e``…``;``/``p``; ranuras de modo de construcción ``building1``–``building16`` (``d/f/g/h/j/k/l/;`` + ``e/r/t/y/u/i/o/p``)
- modo comando teclas de acceso rápido de índice de 30 ranuras; modo de mapa ``f/g/m/p`` realiza un ciclo de depósitos/prados/pasajes en el cuadrado actual (sin saltos de cuadrado); ESC al mapa anuncia el resumen del cuadrado y restaura silenciosamente el último objetivo del mapa
- mod ``style.txt``: ``keyboard worker``, ``keyboard soldier1``–``7``, ``keyboard building1``–``16``; ``bindings.txt`` el cuerpo ahora es un código auxiliar de compatibilidad
- las subpantallas de inventario/equipo/atributos llaman a ``restore_active_bindings`` al salir; enlaces del editor sin cambios
- teclas de acceso rápido clásicas de un solo archivo: `````[general] layered_hotkeys = 0``` en ``user/SoundRTS.ini`` (predeterminado ``1`` = en capas); o menú principal Opciones → Esquema de teclas de acceso rápido: teclas de acceso rápido en capas/teclas de acceso rápido clásicas (efectivo en el próximo juego); cargas clásicas ``legacy_bindings.txt``, sin capas de modo de tecla F, ESC no ingresa a la exploración del mapa
- Los mods pueden personalizar cada esquema: en capas a través de ``ui/*_bindings.txt`` o agregar ``ui/bindings.txt``; clásico a través de ``ui/legacy_bindings.txt`` o agregar ``ui/bindings.txt``
- documentos: ``../player/layered-hotkeys.htm``, ``../player/layered-hotkeys.htm``
- pruebas: ``test_layered_bindings.py``, ``test_map_browse_target_persist.py``

Campañas estilo Age of Empires DE (un jugador + cooperativo):

- un jugador: navegador de misiones (``synopsis``, cinco niveles de dificultad persistentes, capítulos completados/bloqueados, reintento); HP enemigo/escala de daño por nivel (Estándar + solo = 100%)
- cooperativo: multijugador de historia y misión (espacios para jugadores + socios aliados de IA, introducción/escenas/objetivos compartidos, sin tratado); la dificultad y el número de enemigos escalan enemigos; TTS de campaña cargado automáticamente para nombres de lugares localizados
- ver ``../player/campaign-menu.htm`` (``../player/campaign-menu.htm``)
- pruebas: ``test_changelog_1429_coop_campaign_difficulty.py``, ``test_changelog_1429b_campaign_browser_difficulty.py``, ``test_changelog_1429c_coop_story_mission.py``, ``test_changelog_1429d_coop_player_slots.py``, ``test_coop_campaign_place_names.py``

1.4.3.8
-------

Campos de construcción, objetivos progresivos y tumores de fluencia Zerg:

- ``build_field_radius`` (mosaico BFS) vs ``build_field_radius_m`` (metros de `` (x,y)``); Los proveedores de medidores pintan marcas cuando ``build_field_persists`` / ``build_field_spreads``: corrige las comprobaciones de construcción de fluencia de medidores exclusivas de Hatchery.
- El disparador ``register_objective`` registra números primarios para la victoria sin F9/voz; la victoria usa ``\_required_objective_numbers`` vs ``\_completed_objective_numbers`` (no hay victoria prematura cuando los goles se revelan uno por uno)
- F9 / ``add_objective``: "Objetivo principal N:" cuando hay múltiples objetivos; dos puntos después del número; objetivo único omite número
- Mod de StarCraft: tumor de fluencia / tumor de Queen Spawn Extender tumor de fluencia; atributos de habilidad ``summon_requires_build_field``, ``summon_requires_marked_field``
- documentos: ``campaign/progressive-objectives.htm``, ``../player/starcraft-zerg-creep.htm``; ``modding.rst``, ``mapmaking.rst``
- pruebas: ``test_build_rules.py`` (tumor arrastrado), ``test_campaign_alliance_transfer_triggers.py`` (register_objective), ``test_objective_announce.py``

1.4.3.7
-------

Etiquetas de voz del sistema de caza y vida silvestre:

- Caza al estilo Age of Empires: ``is_huntable`` los animales dejan ``food_carcass`` depósitos; los trabajadores los recogen; los ciervos/ovejas huyen; las ovejas pueden ser pastoreadas (``can_herd`` / ``herdable``)
- Vida silvestre anunciada como "animal" (por ejemplo, "ciervo, animal"), no como "neutral, NPC"; los resúmenes cuadrados utilizan un cubo de animales separado
- Las máquinas tragamonedas ``computer_only`` exclusivas para vida silvestre no se unen a la alianza ``"ai"`` (no con jugadores, criaturas hostiles u otras manadas; las máquinas tragamonedas mixtas no cambian)
- Ctrl+Shift+F4 para un jugador solo de vida silvestre dice "eres un animal"; Los jugadores mixtos de NPC + vida silvestre todavía dicen "eres NPC neutral"
- Los mapas aleatorios generan vida silvestre y huertos cerca de los inicios; ``hunting_techniques`` mejora la recolección de cadáveres
- documentos: ``../player/hunting.htm``; ``modding.rst`` sección de caza
- pruebas: ``soundrts/tests/test_hunting.py``, ``test_hunting_herd.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``

1.4.3.6
-------

Ataques de ráfaga/secuencia (``damage_seq``):

- intervalo de ráfaga fijo: ahora se respetan las reglas ``(interval …)`` (se codificaron en 0,4 s)
- omitir ``(damage …)`` para dividir automáticamente la base ``mdg`` / ``rdg`` de manera uniforme (admite daño fraccional)
- cada disparo en ráfaga activa ``launch_mdg`` / ``launch_rdg``; enumerar múltiples ID de sonido en ``style.txt``
- reglas básicas: nuevo ``repeating_crossbowman`` (actualización de arquero; estilo Age of Empires Chu Ko Nu)
- pruebas: ``soundrts/tests/test_damage_seq_burst.py``
- documentos: ``../player/burst-attacks.htm``; ``modding.rst`` Sección del sistema de combate

1.4.3.5
-------

Combate AI contra unidades neutrales:

- Las unidades de jugador en modo ``offensive``, ``defensive`` o ``chase`` no atacan automáticamente a neutrales.
  unidades (``computer_only ... neutral``)
- el modo defensivo no huye cuando solo hay neutrales presentes
- El ataque forzado (``imperative`` ir/atacar, por ejemplo, Ctrl+hacer clic en la unidad) todavía funciona
- los creeps neutrales permanecen en guardia + contraataque de su lado; ver ``../player/unit-default-behavior.htm``

1.4.3.4
-------

Generador de mapas aleatorios de procedimientos (RMG):

- Entrada: menú principal Iniciar un juego → Mapa aleatorio; o Mapa aleatorio en la lista de mapas de creación de juegos en línea
- Opciones: plantilla (estándar/rápida/macro/carriles), tamaño, número de jugadores, equipos 2 contra 2, monstruos, recursos, terreno, agua, tesoro, semillas, tratado.
- Después de la generación, se anuncian el código semilla y compartido; F5/F6 reproducirlos desde el historial de voz (aún disponible en el menú de invitación AI)
- Importar código compartido salta los menús paso a paso; formato ``RMG1:…`` — consulte `Random map guide <randommap.htm>`_
- Las entradas de texto del menú (compartir código, semilla, inicio de sesión, etc.) admiten Ctrl+A/C/V/X seleccionar todo, copiar, pegar, cortar
- Código: ``soundrts/randommap.py``, ``soundrts/randommap_menu.py``; pruebas ``soundrts/tests/test_randommap.py``

1.4.3.3
-------

Condiciones indexadas (``killed_target`` / ``npc_has_item`` / ``unit_lost`` / ``building_lost`` / ``key_unit_killed``):

- Índice de generación global (cualquier cuadrado): ``(killed_target \<index\> \<type\> [enemy|ally])``, `` (npc_has_item \<index\> \<type\> \<item\>)``, `` (unit_lost \<index\> \<type\>)``, `` (building_lost \<index\> \<type\>)``, `` (key_unit_killed \<index\> \<type\>)``
- Índice cuadrado: ``(killed_target \<square\> \<index\> \<type\>)``, `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``, etc.
- Mismas reglas de índice que ``killed_target`` / ``npc_has_item``; solo la enésima unidad/edificio generado en esa casilla
- Ejemplo: ``(building_lost 1 townhall) (defeat)`` falla sólo si el primer ayuntamiento generado es destruido (cualquier casilla); `` (building_lost a1 1 townhall)`` es específico de un cuadrado; `` (unit_lost 3 footman) (defeat)`` falla sólo si el lacayo n.º 3 muere
- Demostración: La leyenda de Raynor capítulo 1; ver ``campaign/unit-index.htm``
- Pruebas: ``soundrts/tests/test_map_select_loss_triggers.py``

1.4.3.2
-------

Unidades sin numerar (rules.txt, ``no_number 1``):

- Se aplica sólo a tipos de unidades con ``no_number 1``; las unidades predeterminadas (por ejemplo, campesinos) siempre mantienen números de serie ("campesino 1 en a1")
- Con ``no_number 1`` y sólo una unidad de vivienda de ese tipo: sin número de serie ("Guan Yu en a1", "caballero líder en a1")
- Con ``no_number 1`` y dos o más de ese tipo: números de serie ("Guan Yu 1", "Guan Yu 2")
- Los resúmenes de grupo, cuadro y batalla siguen la misma regla (por ejemplo, "tú controlas a Guan Yu y 2 caballeros de escolta")
- Véase ``modding.rst``; ejemplos de campaña ``raynor``, ``npc_knight_leader`` en ``The Legend of Raynor/rules.txt``

1.4.3.1
-------

Inventario y equipo:

- Shift+V: mochila (todos los artículos en el inventario); Ctrl+V: equipamiento (armas y armaduras)
- mutuamente excluyentes con la pantalla de propiedades Alt+V; requiere exactamente una unidad amiga seleccionada
- Teclas en pantalla: flechas para explorar, Ingresar equipar/usar, Mayús+Ingresar desequipar, Eliminar/Mayús+Eliminar soltar, g lee la introducción
- modelo de artículo unificado: ``class item`` con ``equippable_as_weapon 1`` / ``equippable_as_armor 1``; las estadísticas se aplican al equipar
- a partir de ``weapons`` / ``armor`` que son elementos equipables que ingresan automáticamente al inventario; equipado silenciosamente cuando no hay equipo incorporado de ese tipo y ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` es 1 (predeterminado; necesita ``inventory_capacity`` > 0)
- ``class weapon`` / ``class armor`` heredados permanecen integrados (solo lectura en la pantalla del equipo)
- equipo mixto incorporado + elemento: incorporado equipado en el momento del desove; con ``spawn_weapons_equipped 1``, las armas de los objetos permanecen en la mochila y no se pueden equipar; interruptores incorporados solo con elemento incorporado, solo con elemento, sin conmutación cruzada (lo mismo para armadura)

Comportamiento predeterminado de la unidad (rules.txt):

- ``ai_mode``: inicio del modo AI — ``offensive``, ``defensive``, ``guard`` o ``chase`` (no ``patrol``)
- ``auto_gather`` / ``auto_repair``: trabajador que se reúne y repara automáticamente al inicio del juego (predeterminado 1)
- ``auto_explore``: las unidades móviles comienzan con la exploración automática activada (predeterminado 0)
- ``can_auto_explore 1``: el menú de la unidad ofrece habilitar/deshabilitar comandos de exploración automática

Dar artículos a los NPC:

- Orden ``give``: haga clic derecho en una unidad no hostil, menú de comando o acceso directo ``g``
- necesidades objetivo ``receive_items 1``; Lista blanca ``accepted_items`` opcional y filtro de relación ``accept_from``
- condición de activación ``npc_has_item``; demostración multijugador ``res/multi/give_demo.txt``; campaña cap. 14–16 (``The Legend of Raynor/14.txt``\ –``16.txt``) para entrega aliada/neutral/enemiga
- ``npc_has_item`` / ``killed_target`` sintaxis de índice de unidad (``\<square\> \<index\> \<type\>``); demostración La leyenda de Raynor capítulo 28; ver ``campaign/unit-index.htm``

Victoria por encontrar objetos:

- la condición de activación ``has_item`` verifica el inventario del jugador para un tipo de artículo determinado (recuento opcional)
- el artículo debe permanecer en el inventario (``consume_on_pickup`` no debe ser 1)
- ejemplo: La leyenda de Raynor capítulo 17 (``lost_amulet``)

Transporte a plaza y entrega de historia:

- condición de activación ``has_brought_item``: la unidad del jugador llega a un cuadrado mientras lleva un objeto (sin caída)
- acción desencadenante ``remove_item``: eliminar y destruir elementos de los inventarios de los jugadores; utilizar con ``cut_scene`` para entrega narrativa
- acción desencadenante ``do``: ejecuta múltiples subacciones en orden (``if`` no puede reemplazar esto)
- ejemplo: La leyenda de Raynor capítulo 18 (``mana_potion`` en el santuario c3)

Elementos del terreno y condiciones compuestas:

- acción desencadenante ``remove_ground_item``: eliminar elementos en el suelo en un cuadrado (por ejemplo, eliminar el tesoro después de abrirlo)
- condición de activación ``and``: verdadera solo cuando todas las subcondiciones son verdaderas
- Sintaxis ``find``: cuadrado antes del tipo, incluso dentro de ``not``; El orden incorrecto hace que las condiciones casi siempre sean verdaderas.
- ejemplo: La Leyenda de Raynor capítulo 20 (solta el tesoro, luego recoge todas las monedas de oro)

Desencadenantes de la diplomacia de campaña y la transferencia de unidades:

- acción desencadenante ``alliance_request``: un jugador solicita alianza; en campañas el humano acepta con Ctrl+F4 (sin selección de objetivo F12)
- condiciones de activación ``alliance_with`` / ``alliance_request_pending``
- acción desencadenante ``transfer_units`` (alias ``convert_units``, ``change_owner``): cambiar la propiedad de la unidad entre jugadores
- acción desencadenante ``allied_assist``: las unidades aliadas luchan solas (guardia→persecución); selector de unidad opcional para interruptor parcial
- acción desencadenante ``allied_control``: otorga mando directo sobre el ejército de un aliado (todo el aliado o unidades seleccionadas); unidades incomparables cambian a persecución
- acción desencadenante ``add_inventory_item``: poner elementos en el inventario de la unidad (transporte entre capítulos, recompensas de misiones)
- acciones de activación ``set_ai_mode`` / ``set_yield_on_defeat``: modo AI en tiempo de ejecución y alternancia de duelo de rendimiento
- condiciones ``units_yielded`` / ``units_yielded_by``, ``has_entered``; acciones ``stop_all_units`` / ``release_yielded_units``: recuentos de rendimiento (filtrar por atacante), entrada en casilla, alto el fuego, restaurar el combate
- La Leyenda de Raynor capítulos 24-27 (arco de la alianza del norte); ver ``../player/campaign-northern-arc.htm``

``phase_targets`` sintaxis de exclusión:

- un ``-`` inicial excluye una coincidencia (por ejemplo, ``phase_targets -building`` = todas las unidades excepto los edificios)
- incluye y excluye se pueden mezclar (por ejemplo, ``phase_targets soldier -footman``)

``is_a`` herencia de exclusión ``-`` prefijo:

- p.ej. ``is_a footman(-hp_max)`` es equivalente a ``is_a footman(apart hp_max)``
- múltiples exclusiones: ``is_a footman(-hp_max -mdg)``

Errores solucionados:

- Se corrigió la pérdida de la selección de unidad después de una actualización ``can_upgrade_to`` o una transformación ``can_change_to``: por ejemplo, un arquero seleccionado con g permanece seleccionado después de actualizar a un arquero oscuro, sin volver a seleccionar

1.4.3.0
-------

Errores solucionados:

- Se corrigió un error grave en la victoria de la campaña: cuando un mapa de campaña tenía dos o más computadoras enemigas, completar los objetivos no terminaba el juego; la causa principal fue mutar la lista de jugadores mientras se iteraba durante la liquidación de la victoria.
- Se corrigieron unidades y objetos que desaparecían de un cuadrado durante 4 a 5 segundos después de que una unidad se marchaba.
- en campañas, F12 (alianza dinámica) ya no selecciona ningún objetivo; Las computadoras con script de activación no son jugadores oponentes reales.
- los equipos desencadenantes promovidos por ``(ai easy)`` y desencadenantes similares se anuncian como "NPC" en lugar del nombre interno ``ai_timers``; su derrota ya no se anuncia en las campañas
- Ctrl+Shift+F4 ahora anuncia las computadoras activadoras como "NPC"

1.4.2.9
-------

- los mapas descargados de un servidor mantienen su nombre original
- los mapas con el mismo contenido que un mapa local no se vuelven a descargar
- las repeticiones multijugador se almacenan como ``replay1``, ``replay2``, ``replay3``, etc.

1.4.2.8
-------

- pequeño aumento de rendimiento gracias a las optimizaciones de Cython
- computadoras neutrales: agregue la palabra clave ``neutral`` a una línea ``computer_only``; Las IA neutrales no atacan a menos que sean atacadas primero.
- ``player_start \<N\> \<square\>`` arregla el cuadrado de generación para el jugador N (consulte la guía de creación de mapas)

1.4.2.7
-------

- Se puede cambiar el nombre de las partidas guardadas y reproducidas (cualquier idioma/caracteres): edite archivos en ``user/saves`` o ``user/replays``, o presione Shift+Enter en un archivo en el menú de restauración/reproducción
- Eliminar pide confirmación; Mayús+Suprimir elimina inmediatamente

1.4.2.6
-------

- hasta 10 espacios para guardar por mod; Cada mod tiene sus propios guardados, puntos de memoria y repeticiones.
- cancelar un juego crea un punto de memoria; "Continuar juego sin terminar" aparece en el menú principal.
- Los archivos de reproducción también son específicos del mod.

1.4.2.5
-------

- ``can_advance`` para actualizaciones de fase (distintas de ``can_research``); se muestra en la interfaz de propiedades
- La fase inicial predeterminada se muestra al inicio del juego cuando un edificio tiene ``can_advance``
- ``hide_locked_commands`` en ``def parameters`` oculta comandos cuyos requisitos no se cumplen

1.4.2.4
-------

- nuevo ``class phase`` (progresión de estilo de edad): ``phase_targets``, ``phase bonus``, ``units_auto_upgrade``
- alianza dinámica: cada solicitud de alianza ahora tiene su propio tiempo de reutilización

1.4.2.3
-------

- alianza dinámica durante un juego (F12 / Shift+F12 seleccionar objetivo; F4 solicitar; Ctrl+F4 aceptar; Shift+F4 cancelar/rechazar/dejar); Las alianzas previas al juego no se pueden cambiar en el juego.
- correcciones de errores de campaña cooperativa

1.4.2.2
-------

- modo tratado: paz por una duración determinada (hasta 20 minutos), luego guerra
- campaña cooperativa en servidores: cualquier jugador que complete objetivos contribuye al equipo

1.4.2.1
-------

Errores solucionados:

- Los sonidos de los pasajes ya no retrasan los anuncios de nombres de lugares y coordenadas.
- Las unidades ya no obtienen bonificación de velocidad con cada resurrección.
- Los cambios de actualización en costo, costo_tiempo y costo_población ahora persisten después de la investigación.
- Las mejoras de curación y daño ya no se aplican a todos los tipos de unidades.
- altitud de la unidad aérea restaurada al comportamiento 1.3.8.1

1.4.2.0
-------

Errores solucionados:

- las unidades revividas pueden recibir órdenes nuevamente
- Los autoataques ya no provocan daño de carga.
- Las actualizaciones con descuento ya no afectan a las unidades sin la tecnología de descuento.
- La salpicadura de carga terrestre ya no golpea a las unidades aéreas.
- los transportes con capacidad ≥ 99 ya no se cargan solos

1.4.1.9
-------

- ``square_name`` jerarquía hasta 3 niveles (provincia/ciudad/distrito); TTS anuncia nombres al ingresar desde otra región
- más optimizaciones de rendimiento

1.4.1.8
-------

- las coordenadas del mapa utilizan ``x,y`` (por ejemplo, ``1,1``) en lugar de letra+número; La notación heredada todavía se acepta.
- ``square_name`` para nombrar cuadrados; traducciones en ``tts.txt``
- Las unidades iniciales y los recursos de la facción se pueden definir en ``rules.txt`` (las definiciones del mapa tienen prioridad)

1.4.1.7
-------

- sistema de habilidades unificado (``class skill``) con ``effect_target`` y ``effect_range``
- mejoras de estadísticas múltiples, mejoras de aura (``buff_radius``), parámetros ampliados de daño/curación/regeneración

1.4.1.6
-------

- Las desventajas se pueden definir en las armas.
- Se corrigió el error de carga del juego guardado.

1.4.1.5
-------

- Palabra clave ``intro`` en ``style.txt`` para descripciones de unidades
- percepción diagonal restaurada
- UI de producción fija en edificios no productivos

1.4.1.4
-------

- 1.3.5.2 activadores migrados; Mapas td1-td3 jugables

1.4.1.3
-------

- sistema de armas y armaduras; cambio manual de arma (A / Shift+A / B+X); ``auto_weapon_switch``
- sistema de elementos migrado desde 1.3.5.2
- muros y puertas reconstruibles

1.4.1.2
-------

- ``can_repair`` sobre los trabajadores; Búsqueda mejorada de rutas de unidades de agua y minería costera.
- más atributos en la interfaz de propiedades

1.4.1.1
-------

- interfaz de propiedades mejorada con navegación interactiva (can_train, skills, research, can_build)
- ``can_repair_ships`` para trabajadores y edificios; reparación de barcos en tierra (distancia 6) y reparación de automóviles de edificios (distancia 8)

1.4.1
-----

- La vista RPG en primera persona es de 360°; precisión de movimiento mejorada

1.4.0.9
-------

- guía del modo RPG en primera persona; Zoom dinámico F8 de 3×3 a 15×15; navegación con reconocimiento de ruta

1.4.0.8
-------

- ``minimal_mdg`` / ``minimal_rdg`` renombrado nuevamente a ``minimal_damage``
- Teclas de acceso rápido para habilidades RPG (1–0) en modo primera persona

1.4.0.7
-------

- tasas de aciertos críticos fijadas; Mod loco jugable

1.4.0.6
-------

- modo espectador en servidores; Sonidos de victoria/derrota en multijugador arreglados.

1.4.0.5
-------

- Palabras clave ``food`` reemplazadas por ``population`` (por ejemplo, ``population_cost``)
- economía más rica: construcción de recursos, cultivo y producción automáticos/manuales
- ``rpg_bindings.txt`` reservado para futuras personalizaciones de teclas de acceso rápido de RPG

1.4.0.4
-------

- ``auto_production`` / ``manual_production``; ``is_gather`` / ``is_create``; ``class resource`` separado de ``class deposit``

1.4.0.3
-------

- Fondo de facción y música de batalla (``\<faction\>\_music``, ``\<faction\>\_battle_music``)

1.4.0.2
-------

- sonidos de selección/confirmación/retorno de menú; Música de fondo por menú y música de batalla.

1.4.0.1
-------

- mecánica de carga y contracarga; tasas de activación de mejoras ampliadas
- nuevas condiciones de derrota: ``unit_lost``, ``key_unit_killed``, ``key_units_killed``, ``units_lost``, ``buildings_lost``, ``has_killed``; ``killed_target`` y ``has_killed`` admiten ``enemy`` / ``ally``

1.4

- reelaboración del combate: ``mdg`` + ``mdg_vs`` (aditivo), crítico, perforador, explotar
- sistema hero y XP desde 1.3.5.2 integrado
- Los parámetros ``title``/campaña/mapa aceptan cadenas entrecomilladas; ``tts.txt`` formato de traducción
- Se admiten mapas avanzados desempaquetados en ``multi/``
- Se corrigieron los sonidos que se reproducían al escribir nombres coincidentes en los cuadros de entrada.

1.3.9.8
-------

- sistema de mejora/desventaja de 1.3.5.2 integrado
- Los enemigos aparecen inmediatamente al entrar en su casilla.

1.3.9.7
-------

- ``can_train`` con cantidades; ``can_change_to``; Corrección del menú ``can_use_tech`` / ``can_use_skill``

1.3.9.6
-------

- costo porcentual/coste_tiempo/coste_población en las actualizaciones; visualización de recursos decimales

1.3.9.5
-------

- filtros de objetos (teclas M / N); ``cfg/language.txt`` selección de idioma

1.3.9.3
-------

- correcciones de cobertura/esquiva del terreno; la investigación se aplica a unidades futuras; sonidos de salpicaduras eliminados temporalmente

1.3.9.2
-------

- efectos de la mejora en coste/tiempo/población; sonidos de salpicaduras; atributos flotantes en la interfaz de usuario de propiedades

1.3.9.1
-------

- propiedades de salpicadura ``\_vs``; sonido retrasado ``falling``; regla de ataque de altura del proyectil

1.3.9.0
-------

- ``extraction_time`` / ``extraction_qty`` restaurado; Interfaz de propiedades Alt+V con ``attributes_bindings.txt``

1.3.8.8
-------

- ``can_gather`` / ``gather_time`` / ``gather_qty`` sobre los trabajadores; ``is_rewards`` / ``rewards_resource``

1.3.8.7
-------

- matar/destruir recompensas de recursos; reembolso por autodemolición

1.3.8.5
-------

- mapas específicos de mod a través de ``mods/\<mod\>/multi/``

1.3.8.4
-------

- producción de recursos de construcción (``is_production``, ``production_type``, etc.)

1.3.8.3
-------

- herencia flexible ``is_a`` (selectiva, de exclusión, multiparental)

1.3.8.2
-------

- capturar la propiedad; ``mdg_projectile`` / cobertura del terreno/esquivar; contenedores de salida mejorados
- importantes modificaciones de combate: sistema ``mdg``/``rdg``/``mdf``/``rdf``; secuencias de daño; ``class skill``; modos de guardia/persecución; refactorización del sistema de sonido

1.3.8.1
-------

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.8 o posterior
- servidor: 1.2-c12 o posterior

Principales cambios desde 1.3.8:

Errores solucionados:

- en un juego restaurado, la tecla R seleccionaría a cualquier soldado (gracias a Marco Oros por informar del error)
- cuando crear un menú lleva demasiado tiempo, se acumularían teclas repetidas
- con suerte evitar cualquier problema de volumen cuando se crea una fuente de sonido
- Los mapas personalizados aparecerán después de los mapas oficiales.
- ejecutar server.py no requiere ningún paquete

1.3.8
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.8 o posterior
- servidor: 1.2-c12 o posterior

Principales cambios desde 1.3.7:

- agregado tts_digit_coficient en cfg/parameters.toml

Errores solucionados:

- Los caminos entre el suelo y el agua se mantendrán si ambos cuadrados son de tierra.
- las unidades huirán a la casilla anterior con más frecuencia
- Manejar adecuadamente archivos de reproducción que no son marcas de tiempo (gracias a dnl-nash).
- enviar informes de errores sólo si el cliente es un ejecutable

Traducciones:

- se agregó traducción al bielorruso (gracias a Uladzimir)
- traducción al eslovaco actualizada (gracias a Marco Oros)

1.3.7
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.7 o posterior
- servidor: 1.2-c12 o posterior

Cambios desde 1.3.6:

Ahora las unidades pueden atacar desde el interior de vehículos o edificios:

- las unidades a distancia pueden atacar como de costumbre
- Las unidades cuerpo a cuerpo sólo pueden atacar desde el suelo y sin ningún alcance adicional.
- las unidades cuerpo a cuerpo no pueden atacar desde vehículos aéreos
- en el juego predeterminado: las unidades pueden entrar por muros, puertas y torres

Se solucionaron problemas con los contraataques a una plaza cercana:

- Las unidades que no puedan contraatacar permanecerán en silencio.
- las unidades defensivas no contraatacarán

Otro:

- restauró el "¡ataque!" notificación
- corrección de error: una unidad no entraría a un edificio si la orden se daba desde otra casilla
- arreglado: restaurar el juego
- los ataques entre cuadros podrían funcionar mejor

Modificación:

- añadido Armor_vs
- ahora "damage_vs" funciona con "is_a" (incluidos varios niveles de "herencia" y "herencia" múltiple)

Elaboración de mapas:

- mapas oficiales "multi" movidos a res/multi
- Los "mapas de carpetas" multijugador deben estar comprimidos para poder jugar en línea
- Se eliminó el archivo "maperror.txt" (la información ya está en el mensaje de error del juego).

Cambios en el formato de la campaña:

- mods.txt reemplazado con la palabra clave "mods" en Campaign.txt
- Palabra clave "título" en campaña.txt
- nueva restricción: un mapa de misión complejo debe almacenarse como un archivo zip

1.3.6
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.6 o posterior
- servidor: 1.2-c12 o posterior

Cambios desde 1.3.5:

Comportamiento de la unidad:

- error solucionado: las unidades ofensivas cercanas contraatacarán automáticamente nuevamente (se moverán a la casilla del atacante y luego regresarán a sus posiciones iniciales)
- error solucionado: las unidades defensivas huirán nuevamente

Interfaz:

- la descripción de las unidades controladas será menos confusa
- seguimiento de grupo mejorado (tecla de espacio): la interfaz generalmente seguirá al frente del grupo
- error solucionado: en style.txt, noise_if_very_damged nunca se reproduciría
- error solucionado: SAPI no funcionaba

Agua:

- de ahora en adelante, el juego no creará caminos anfibios (resuelve el siguiente problema: si el camino más corto al destino incluyera un cuadrado de agua, las unidades terrestres caminarían hacia el agua y morirían)
- Problema solucionado: un mago podía retirar unidades de agua a casillas que no fueran de agua (ahora un mago retirará unidades de agua a la casilla de agua adyacente más cercana).

Multijugador:

- iniciar un servidor no privado configurará automáticamente el enrutador (funciona solo si UPnP está activado en el enrutador; el enrutador elimina automáticamente la configuración después de 20 minutos de inactividad)
- configuración más sencilla del servidor independiente
- descubrimiento automático del servidor local mediante transmisión UDP (el servidor local aparecerá en el menú "elegir un servidor en una lista").
- error solucionado: en juegos multijugador, un jugador que no sea administrador podría establecer una velocidad más lenta

Traducciones:

- Traducciones actualizadas al portugués brasileño, chino, checo, italiano y eslovaco.

Elaboración de mapas:

- cuando sea posible, emitir una advertencia en lugar de un error de mapa
- error solucionado: en algunos casos, un disparador seleccionaba más unidades de las especificadas. Por ejemplo, si hay 3 dragones y muchos lacayos en a1, (a1 10 lacayos dragón) seleccionaría 3 dragones y 7 lacayos.

1.3.5
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.5 o posterior
- servidor: 1.2-c12 o posterior

Cambios desde 1.3.4:

- error solucionado: no se podía guardar un juego con terreno
- Corregido: el sonido del golpe no se emitía si mataba al objetivo.
- arreglado: el juego se congelaría si no había suficiente espacio en un cuadrado para crear una unidad

Internacionalización:

- convirtió todos los archivos tts.txt a UTF-8 con firma BOM. La codificación todavía está definida explícitamente en la primera línea como UTF-8. La firma BOM puede ayudar a algunos editores de texto a seleccionar UTF-8 automáticamente.
- siempre usará UTF-8 (o ASCII) para archivos de texto distintos de tts.txt (rules.txt, style.txt, etc.)
- traducción al español actualizada (gracias a Oscar Corona)

1.3.4
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.4 o posterior
- servidor: 1.2-c12 o posterior

Cambios desde 1.3.3:

- probablemente se corrigió el habla en algunos casos más (infórmenos si aún no puede iniciar el cliente)
- guardado y restaurado restaurado (parece estar funcionando, pero tenga cuidado)
- recursos y tecnología infinitos restaurados para "computadora agresiva 2" (más interesante)

Multijugador:

- el cliente recordará la lista de servidores descargada previamente y la usará si el metaservidor está temporalmente inactivo
- en "ingrese la dirección IP del servidor", al ingresar una dirección IP vacía se seleccionará su computadora (no es necesario escribir: "localhost")
- servidor independiente: se eliminó la dependencia de pygame

Interfaz:

- comando de consola: "a u_recall" agregará la actualización de recuperación al jugador actual
- error menor solucionado: la interfaz no seguía a una unidad dentro de un transporte (si la unidad estaba en modo de seguimiento antes de ser transportada)

Internacionalización:

- traducción italiana actualizada (gracias a Luigi Russo)

Campaña principal:

- se agregó el capítulo 12, un pequeño mapa para mostrar cómo funcionan los bosques densos (la regla es: "cualquier camino entre dos bosques densos está bloqueado")

Consejo: para comprobar rápidamente si hay mejoras en un capítulo específico de una campaña que ya has jugado:

- presione la tecla "consola" debajo de Escape y presione "v" y Enter para una victoria instantánea
- o editar user/campaigns.ini: en [single_campaign] "chapter = 12", por ejemplo

1.3.3
-----

Para juegos multijugador, esta versión requiere:

- cliente: 1.3.3 o posterior (si es compatible)
- servidor: 1.2-c12, 1.3.0, 1.3.1, 1.3.2, 1.3.3 o posterior (si es compatible)

Cambios desde 1.3.2:

- error solucionado: una unidad no se detenía después de usar una habilidad que requería acercarse (niebla mortal, exorcismo...) y se movía hacia el enemigo...
- error solucionado: el juego requeriría un objetivo para una habilidad centrada en el lanzador (por ejemplo: resucitar a los muertos)
- error solucionado: no se podía ver el agua desde terreno bajo (por ejemplo en el mapa jl7)

La interfaz del mapa debería parecer más natural:

- Moverse en el mapa no causará colisiones si controlas una unidad voladora.
- Moverse en el mapa no causará colisiones si estás definiendo el objetivo de una orden de retirada (por ejemplo)
- Se eliminaron las colisiones entre el agua y el terreno bajo.

Bosques densos:

- error solucionado: los bosques densos crearían caminos cuando se despejaran (incluso si no había caminos antes)
- ahora los bosques son densos si tienen al menos 7 bosques (en lugar de 3)
- mapa multijugador 8: actualizado (7 bosques) y mejorado (economía más rápida)
- editor: paleta de terreno actualizada (bosque denso si hay al menos 7 bosques)

Internacionalización:

- error solucionado: los mapas con caracteres que no sean US-ASCII no se podían leer en plataformas que usan GBK o UTF-8 de forma predeterminada (ahora los mapas siempre se leen como UTF-8 y los errores se reemplazan con "?")
- convirtió los siguientes mapas a UTF-8: bs2, can1, qc1, qc2 y qc3
- traducción polaca actualizada (gracias a Patryk Mojsiewicz)

Pequeños cambios en la campaña principal:

- Capítulo 9: con el error de "niebla mortal" solucionado, los nigromantes deberían ser más fáciles de manejar
- capítulos 5 y 10 ligeramente mejorados

Consejo: para comprobar rápidamente si hay mejoras en un capítulo específico de una campaña que ya has jugado:

- presione la tecla "consola" debajo de Escape y presione "v" y Enter para una victoria instantánea
- o editar usuario/campañas.ini: en [single_campaign] "chapter = 11", por ejemplo

1.3.2
-----

Cambios desde 1.3.1:

Principales cambios:

- el menú "elegir un servidor" incluirá cualquier servidor con una versión de servidor compatible (no solo la misma versión), por lo que los servidores no tendrán que actualizarse con tanta frecuencia
- Los clientes compatibles con diferentes versiones podrán jugar juntos.
- los servidores "más cercanos" aparecerán primero en el menú "elegir un servidor" (servidores con el menor retraso de respuesta)
- el tiempo necesario para comprobar si un servidor está disponible se mencionará (expresado en milisegundos) en el menú "elegir un servidor" para comparar
- Los servidores no disponibles no aparecerán en el menú "elegir un servidor".

Cambios menores:

- disminuyó ligeramente la detalle de server.log
- Se mejoró la guía del servidor independiente (aunque todavía no es perfecta)
- Se agregaron "notas de la versión" a la documentación.

1.3.1
-----

Cambios desde 1.3.0:

- probablemente solucionado: el juego no se iniciaba en Windows 7 (ImportError: falló la carga de DLL al importar _socket)
- solucionado: a veces el juego no iniciaba hasta que se elimina la carpeta "gen_py" en "appdata\local\Temp" (AttributeError: el módulo 'win32com.gen_py...' no tiene el atributo 'CLSIDToClassMap')
- solucionado: podría faltar vcruntime140.dll
- arreglado: no se pudo obtener la lista de servidores
- arreglado: presionar A se comportará como antes y presionar Control+A solo seleccionará órdenes inactivas

1.3.0
-----

Cambios desde 1.2-c12:

Principales cambios:

- sólo se pueden construir muros y puertas en las salidas (o cualquier edificio "construible sólo en las salidas")
- ahora sólo se puede construir una torre en el centro de un subcuadrado y sólo una torre por subcuadrado. La ubicación de una torre se puede seleccionar de varias formas:

  - en modo zoom: selecciona el subcuadrado actual (debe estar libre)
  - en modo cuadrado: selecciona cualquier subcuadrado libre, comenzando por el central
  - si se selecciona algún objeto: selecciona el subcuadrado circundante (debe estar libre)

- ahora el lector de pantalla es el TTS predeterminado

Cambios técnicos:

- migró a Python 3
- reemplazó todos los TTS con access_output2 (parcheado para soportar Linux)

Errores solucionados:

- no podía controlar una unidad resucitada que estaba en un grupo
- un trabajador que pospusiera la construcción o reunión para eliminar a un intruso no regresaría a su tarea y la completaría en el lugar
- una unidad podría ver una meseta desde abajo
- una unidad no podía ver en diagonal
- No se pudo seleccionar un cuadrado como objetivo para construir una puerta (se seleccionará una salida libre)

Mejoras en la interfaz:

- modo zoom: validar una orden de construcción de un muro (o una puerta) sin seleccionar un objetivo específico seleccionará automáticamente la salida local (si no está bloqueada)
- La pestaña seleccionará cualquier enemigo primero.
- Al presionar Escape cuando se selecciona un objetivo, se seleccionará el cuadrado actual.
- error solucionado: ahora al entrar o salir del modo zoom se seleccionará el minicuadrado o cuadrado como objetivo (en lugar de mantener el objetivo seleccionado)
- se agregaron comas en algunos mensajes (para mayor claridad)
- resumen enemigo más corto
- error solucionado: diría "sitio de construcción" y no el tipo de edificio
- error solucionado: en el modo zoom, un orden predeterminado para un edificio no establecía el punto de reunión en la subcuadrada sino en la plaza
- error solucionado: un juego pausado no se cerraba
- error solucionado: presionar Espacio indicará las órdenes exactas incluso cuando algunas unidades tienen órdenes diferentes (Esto es muy útil para verificar cuántos trabajadores están recolectando oro, madera, etc. (presionando D). Esto podría ser útil para saber cuántas unidades en un grupo se están moviendo y cuántas han llegado. Presionando Control + Shift + S obtendrá un resumen completo de las órdenes de los soldados y trabajadores).
- en el modo de construcción, la pestaña seleccionará prados antes de las salidas
- la descripción de una orden de patrulla recapitulará todos los puntos de ruta
- error solucionado: al presionar Tab se seleccionarían salidas bloqueadas
- error solucionado: ya no es posible construir otro muro en la misma salida
- modo zoom: si no se encuentra ningún terreno edificable mientras se ha validado una orden de construcción en una subcuadra, se generará un error (en lugar de buscar un terreno edificable en la plaza circundante)
