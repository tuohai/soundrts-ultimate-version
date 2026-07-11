
Notas de la versión
===================

.. contents::

1.4.5.1
-------

Corrección de errores y mejoras en la experiencia de usuario de voz/audio:

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

**Mejora: esquema de prioridad de audio P0–P2**

- **Ambiente P0** (de negativo a positivo bajo, por ejemplo, -20, -10): pasos, ambiente en bucle, gritos de fondo; pueden ser reemplazados por capas superiores.
- **Combate P1** (0–14, ``shout_combat_priority`` escala con el número de efectivos): golpes, heridas, gritos de unidad.
- **Alertas P2** (10–16): subir de nivel, transformarse, gritos de eventos; se mantiene cuando los canales son escasos.
- **Código**: ``lib/sound.py`` ``SoundManager.find_a_channel`` se adelanta a las fuentes de menor prioridad; ``audio.py`` pasos en ``priority=-10``; TTS permanece en el canal 0.

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
