guía de modificación
::::::::::::::::::::


.. contents::

modificaciones
--------------

Las reglas del juego y el aspecto del juego se pueden cambiar mediante mods.

Un mod es una carpeta que potencialmente contiene reglas.txt, ai.txt, ui (y sus versiones localizadas). La estructura del árbol es la misma que la estructura de carpetas "res".

Los mods se almacenan en la carpeta "mods" de la carpeta principal o en la carpeta "mods" de la carpeta del usuario. Para ser activado, se debe hacer referencia a un mod en el parámetro "mods=" en SoundRTS.ini.
Por ejemplo: mods = paquete de sonido, mi mod, mi_otro_mod

El archivo reglas.txt parcheará el archivo predeterminado. Por ejemplo, un archivo reglas.txt que contenga estas 2 líneas: "def campesino" y "decay 20" hará que cualquier campesino desaparezca después de 20 segundos.

Localización de mods (ui-xx)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Las carpetas Mod reflejan el árbol ``res``. Agregue carpetas localizadas junto a ``ui/`` (``ui-zh``, ``ui-fr``, ``ui-de``, etc.). El juego carga el idioma desde ``cfg/language.txt`` (o la configuración regional del sistema); las entradas que faltan vuelven a ``ui/tts.txt``.

Recommended layout (``mods/mymod/``)::

    ui/style.txt          ; title 7000
    ui/tts.txt            ; 7000 Pig Farm
ui-zh/tts.txt; 7000 pocilga
    ui-fr/tts.txt         ; 7000 Ferme à porcs
    mod.txt               ; optional: dependencies and menu title (below)


Lo que puedes traducir (una vez que el mod esté activo):

- Nombres de unidad/edificio/facción: ``title \<ID\>`` en ``style.txt`` + el mismo ID en cada ``tts.txt``
- Introducciones de unidades: ``intro \<ID\>`` + ``tts.txt``
- Mapas/campañas dentro del mod: mapa ``title``/``intro`` ID TTS; Las carpetas de campaña pueden usar ``campaign.txt`` ``title`` (igual que las campañas ``res/single``)
- Frases completas: en ``tts.txt``, ``english phrase = translated phrase``

Nombre para mostrar del menú Mod (Opciones → Mods, desde 1.4.2.4):

Add a ``title`` line to ``mod.txt``, same syntax as ``campaign.txt`` — TTS ID or space-separated words::

    title 7100


Define esa ID en ``ui/tts.txt`` y cada ``ui-xx/tts.txt`` (por ejemplo, ``7100 Orc Faction Mod`` / ``7100 兽人模组``). Sin ``title``, se pronuncia el nombre de la alfombra.

Alternativamente, las alfombras están alfombradas, las alfombras están en el medio, las alfombras están en el aire, el entorno global es global.

Notas: ``rules.txt`` / ``ai.txt`` no están localizados. Es posible que el ``ui-xx/style.txt`` localizado dentro de las subcarpetas del mapa/campaña no se cargue, pero el ``ui-xx/tts.txt`` en esas carpetas sí. Los paquetes de sonido (mods sin ``rules.txt``) también admiten ``mod.txt`` ``title`` y ``tts.txt`` localizado en Opciones → Paquetes de sonido.

Ejemplos en este repositorio: ``mods/orc/``, ``mods/prismalab/ui-fr/``.

claro
>>>>>

Para reemplazar reglas.txt o style.txt en lugar de parchearlos, use el comando "borrar" en la parte superior de su archivo. Esto no funciona con ai.txt,
y no es necesario de todos modos, porque en ai.txt el comando def reescribe la definición de IA.

es_a
>>>>

Mientras que en style.txt "is_a" es una forma de heredar todas las propiedades de otra definición,
en reglas.txt, "is_a" también se usa para asegurarse de que una torre del homenaje o un castillo permitirá lo que permitiría un ayuntamiento.

Nota: no es necesario que los árboles de herencia en style.txt y en reglas.txt coincidan.

las reglas
----------

Desde SoundRTS 1.1, las reglas del juego se almacenan en un archivo llamado reglas.txt.

facción
>>>>>>>

Each faction is defined in rules.txt . For example::

	def orc_faction
	class faction


Nota: el nombre "orc_faction" termina con "_faction" sólo para evitar conflictos de nombres. Este sufijo "_faction" no es obligatorio siempre que el nombre sea único.

unidad
>>>>>>

Nota: una unidad también puede ser un edificio.

límite_conteo
=============

Nuevo en SoundRTS 1.2 alfa 10.

`count_limit <value>`

El valor predeterminado es 0 (sin límite).
Cuando el límite está activo, un tipo de unidad que alcance el límite no se puede entrenar,
construido, convocado, resucitado, resucitado o agregado mediante un disparador (add_unit).
Sin embargo, la conversión no se ve afectada.

mdg_projectile / rdg_projectile
===============================

Nuevo en SoundRTS 1.3.8.2. Se agregó restricción de terreno bajo versus terreno alto en 1.3.9.1.
Reemplaza el obsoleto ``is_ballistic``.

``mdg_projectile 0|1``

``rdg_projectile 0|1``

El valor predeterminado es 0. Cuando se establece en 1, el tipo de ataque correspondiente se trata como un
proyectil:

- En terreno elevado, la unidad gana alcance adicional al atacar objetivos a menor altitud.
  (+1 cuadrado por nivel de altura)
- Las unidades que no sean de proyectiles no pueden atacar objetivos terrestres en terreno elevado desde abajo.
  independientemente del rango

Migración: los mods que usaban ``is_ballistic 1`` deberían usar ``rdg_projectile 1`` (a distancia) o
``mdg_projectile 1`` (proyectiles cuerpo a cuerpo como catapultas); cada tipo de ataque está configurado
por separado.

Ranged projectile example::

    def archer
    rdg 3
    rdg_range 4
    rdg_projectile 1

es_teleportable
===============

Nuevo en SoundRTS 1.2 alfa 9.

``is_teleportable 1``

La unidad (o edificio) se ve afectada por el efecto de teletransportación o el efecto de recuperación.

hp_regen
========

Nuevo en SoundRTS 1.2 alfa 11

`hp_regen <hit points regeneration rate>`

Por ejemplo, con "hp_regen 0.15", la unidad recupera 0,15 puntos de vida por segundo.

inicio_maná
===========

Nuevo en SoundRTS 1.2 alfa 10.

``mana_start 50``

En el ejemplo, la unidad comenzará con 50 maná en lugar de mana_max. El valor predeterminado para mana_start es 0. Si mana_start es 0 o negativo, se usa mana_max en su lugar.

proporciona_supervivencia
=========================

Nuevo en SoundRTS 1.2 alfa 9.

``provides_survival 1``

Tener al menos una unidad (o edificio) con "provides_survival" igual a 1 evita que un jugador pierda en un juego multijugador (no en una campaña para un solo jugador). El activador afectado es "no_building_left". De forma predeterminada, solo los edificios tienen esta propiedad establecida en 1. Los sitios de construcción tienen esta propiedad establecida en 0 y no se puede cambiar.

victory_time
=============

Nuevo en SoundRTS 1.4.5.8.

``victory_time <segundos>``

El valor predeterminado es 0 (sin temporizador de victoria). Si es mayor que 0 en un edificio **terminado**, la cuenta atrás empieza en cuanto existe. Si el temporizador llega a cero y el edificio sigue en pie, gana su dueño (y el bando de victoria aliada). Destruir el edificio cancela esa cuenta atrás.

Aplica a cualquier tipo ``class building``, no solo a la Maravilla vanilla. Ejemplo:

::

    def wonder
    class building
    cost 100 120
    time_cost 900
    hp_max 2500
    requirements imperial_age
    count_limit 1
    victory_time 300

Vanilla incluye ``wonder`` con ``victory_time 300`` (5 minutos tras completarse). Voces: TTS 5720 (inicio), 5721 (cancelación), 5722 (restante).

bonificación_almacenamiento
===========================

`storage_bonus <bonus for resource 0> <bonus for resource 1> ...`

Por ejemplo, "storage_bonus 0 1" generará una bonificación de +1 para la madera (el segundo tipo de recurso).

El bono va al dueño de la unidad.
La bonificación no se acumula: solo se aplicará la bonificación más alta para cada tipo de recurso.

daño_vs
=======

Nota: desde SoundRTS 1.4 el sistema único ``damage`` / ``armor`` fue reemplazado por el
sistema dividido cuerpo a cuerpo/a distancia (``mdg`` / ``rdg`` / ``mdf`` / ``rdf`` ...). Ver `Sistema de combate
(desde 1.4)`_ a continuación. La documentación heredada ``damage_vs`` se conserva para modificaciones más antiguas.

(daño versus unidades específicas)

`damage_vs [<list of type names> <damage>] ...`

Define un daño específico contra algunos tipos de unidades.
El valor predeterminado se define en unit.damage.

Ejemplo de un tipo de piquero que sería más eficiente contra un caballero.
 y menos eficaz contra un lacayo o un campesino:

`damage 2 ; default damage`

``damage_vs knight 7 footman peasant 1``

habilidad
>>>>>>>>>

Nota: desde SoundRTS 1.4, las habilidades están unificadas en ``class skill`` (ver `Habilidades (habilidad de clase)`_ abajo). Las propiedades ``effect`` documentadas aquí todavía se aplican a las habilidades y a
``class effect`` definiciones.

efecto
======

`effect <effect type> [parameters]`

Valor predeterminado: (ninguno)

Un efecto es una propiedad de una habilidad. Cuando una unidad usa una habilidad, el efecto se producirá a menos que no se haya mencionado ningún tipo de efecto.

Propiedades adicionales pueden modificar un efecto: objetivo_efecto_ y rango_efecto_.

aplicar_bonus
^^^^^^^^^^^^^

`effect apply_bonus <property name>`

Aumenta la propiedad de las unidades afectadas. El valor se define en la propiedad de la unidad llamada "<nombre de propiedad>_bonus".
Por ejemplo, "efecto aplicar_bonus daño" buscará una propiedad llamada "daño_bonus" en la definición de cada unidad afectada.
De esta manera, las unidades que se benefician de la misma mejora pueden tener diferentes valores de bonificación.

bonificación
^^^^^^^^^^^^

`effect bonus <property name> <value>`

Incrementa en el valor indicado la propiedad de las unidades afectadas.

Al menos las siguientes propiedades deberían funcionar: daño, armadura, alcance, nivel de curación, velocidad, hp_max (aunque las unidades antiguas no tendrán su hp actualizado a hp_max).
food_cost y food_provided probablemente no funcionen correctamente.

conversión
^^^^^^^^^^

``effect conversion`` (sin parámetro)

Mueve el objetivo al ejército del lanzador.

Si el objetivo no es enemigo del lanzador, no pasará nada.

Valores permitidos para las propiedades relacionadas:

* effect_target: preguntar
* effect_range: cuadrado, cerca, en cualquier lugar

TODO: agregue un <límite> para que se elijan las unidades en un cuadrado objetivo (en lugar de tener que apuntar a una unidad)

levantar_muerto
^^^^^^^^^^^^^^^

`effect raise_dead <life span (in seconds)> <unit types and numbers>`

Crea las unidades requeridas en el cuadrado objetivo a partir de los cadáveres en el cuadrado, en el orden de la lista de unidades. Si no hay suficientes cadáveres, no se creará el final de la lista. Las unidades desaparecerán después de <vida útil> segundos, a menos que <vida útil> esté establecido en 0.

Si no hay ningún cadáver en la casilla objetivo, la orden no se ejecutará.

Valores permitidos para las propiedades relacionadas:

* effect_target: self, preguntar, aleatorio
* effect_range: cuadrado, cerca, en cualquier lugar

recordar
^^^^^^^^

``effect recall`` (sin parámetro)

Similar a la teletransportación. Teletransporta las unidades del jugador desde la casilla objetivo de regreso a la casilla del lanzador. Los edificios no se ven afectados. Las unidades aliadas tampoco se ven afectadas.

Si no hay ninguna unidad en la casilla objetivo, la orden no se ejecutará.

Valores permitidos para las propiedades relacionadas:

* effect_target: preguntar, aleatorio
* effect_range: cerca, en cualquier lugar

resurrección
^^^^^^^^^^^^

`effect resurrection <limit>`

Resucita los cadáveres del ejército del lanzador que yacen en la casilla objetivo, con un máximo de <límite> unidades resucitadas. Los cadáveres más antiguos son los primeros en resucitar. Los puntos de vida se restablecen a un tercio de su máximo.

Si no hay ningún cadáver de una unidad del mismo ejército en la casilla objetivo, la orden no se ejecutará.

Valores permitidos para las propiedades relacionadas:

* effect_target: self, preguntar, aleatorio
* effect_range: cuadrado, cerca, en cualquier lugar

convocar
^^^^^^^^

`effect summon <life span (in seconds)> <unit types and numbers>`

Crea las unidades necesarias en la casilla objetivo y las agrega al ejército del lanzador. Las unidades convocadas desaparecerán después de <vida útil> segundos, a menos que <vida útil> esté establecido en 0.

Optional skill attributes for placement checks (StarCraft creep tumor example)::

    summon_requires_build_field creep
    summon_requires_marked_field 1


``summon_requires_marked_field 1`` requiere un cuadrado de campo de construcción marcado (no solo en vivo). Omitirlo cuando el campo vivo sea suficiente (tumor de desove de reina).

implementar
^^^^^^^^^^^

``effect deploy \<life span (seconds)\> [\<count\>] \<effect type\>``

Coloca una entidad ``class effect`` en el cuadro objetivo (área dañada, zona de curación, detector, etc.). Desaparece después de la duración dada. A diferencia de ``effect summon``, esto es sólo para las definiciones de ``class effect``; la interfaz de usuario de atributos muestra estadísticas de daño/curación en lugar de "invocar".

Examples::

    effect deploy 5 sc_nuclear_blast
    effect deploy 3 sc_psi_storm_fx


Optional count (multiple effect entities on the same square)::

    effect deploy 5 2 greek_fire


También es compatible con ``summon_requires_build_field`` / ``summon_requires_marked_field``.

Valores permitidos para las propiedades relacionadas:

* effect_target: self, preguntar, aleatorio
* effect_range: cuadrado, cerca, en cualquier lugar

harm_target (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Daño a un solo objetivo. Dos formas:

* **Daño verdadero fijo** (evita la armadura): ``effect harm_target <value>``
* **Tubería de combate** (armadura, crítico, salpicadura, etc.): ``effect harm_target mdg`` o ``effect harm_target rdg``

Las estadísticas de combate distintas de cero en la habilidad anulan al lanzador. Consulte ``skill_lipi`` / ``skill_lipi_mdg`` en ``mods/wuxia/rules.txt``.

Utilice ``harm_target_type`` para filtrar objetivos (solo enemigos de forma predeterminada). Consulte `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

harm_area (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^

Daños en el área:

* **Daño verdadero arreglado**: ``effect harm_area <damage> <radius>``
* **Tubería de combate**: ``effect harm_area mdg <radius>`` o ``effect harm_area rdg <radius>``

Se puede omitir el radio (usa la habilidad ``effect_radius``). Ejemplos: ``skill_heng_sao``, ``skill_heng_sao_mdg`` (mod wuxia).

ráfaga (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^

Skill combo hits (**not** the same as unit ``damage_seq`` burst attacks; see `burst-attacks.htm <../player/burst-attacks.htm>`_)::

    effect burst mdg <count> (interval <sec>) (window <sec>)
    effect burst rdg <count> (delays <t1> <t2> …)


El daño usa la habilidad o lanzador ``mdg`` / ``rdg``. Ejemplo: ``skill_jifengci`` (mod wuxia).

empujar (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^

``effect push <distance>``: derriba a un enemigo y encuentra una casilla transitable. Ejemplo: ``skill_moli_dan`` (mod wuxia).

ventajas/desventajas (a través de habilidades)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``effect buffs <buff> …`` / ``effect debuffs <debuff> …``

Aplica ventajas o desventajas al objetivo (``debuffs`` solo en enemigos). No existe ``effect reflect``; use ``reflect_percent`` en el pulido y aplique con ``effect buffs`` (wuxia ``b_douzhuan``).

Referencia completa: `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

teletransportación
^^^^^^^^^^^^^^^^^^

``effect teleportation`` (sin parámetro)

Mueve las unidades del jugador en la casilla del lanzador a la casilla objetivo. Los edificios no se ven afectados. Las unidades aliadas tampoco se ven afectadas.
   
Si el destino es el mismo que el cuadrado del lanzador, no se hará nada.

Valores permitidos para las propiedades relacionadas:

* effect_target: preguntar, aleatorio
* effect_range: cerca, en cualquier lugar

objetivo_efecto
===============

`effect_target <selection method>`

Determina cómo se seleccionará el objetivo.

Valor predeterminado: uno mismo

Valores posibles:

* yo: el objetivo será el lanzador (o la ubicación del lanzador si el objetivo debe ser un lugar)
* preguntar: la interfaz de usuario solicitará un objetivo
* aleatorio: el juego elegirá un cuadrado aleatorio como objetivo

rango_efecto
============

`effect_range <distance>`

Determina la distancia entre el lanzador y el objetivo.

Valor predeterminado: 6

Valor especial: inf (infinito)

Si la distancia actual es mayor que la distancia requerida, el lanzador intentará moverse a un lugar más cercano y usar la habilidad desde allí

radio_efecto
============

`effect_radius <distance>`

Determina el radio del área de efecto. El centro del área es el objetivo.

Valor predeterminado: 6

Valor especial: inf (infinito)

Sistema de combate (desde 1.4)
------------------------------

Desde 1.4, el daño final es aditivo: ``final_mdg = mdg + mdg_vs`` (y lo mismo para
``rdg``, ``mdf``, ``rdf``). Cuando el daño base es 0 y ``minimal_damage`` es 0 en
``def parameters``, la unidad no atacará.

Principales propiedades cuerpo a cuerpo/a distancia:

- ``mdg`` / ``rdg``: daño base
- ``mdg_vs`` / ``rdg_vs``: bonificación frente a tipos de unidades específicas
- ``mdf`` / ``rdf``: defensa
- ``mdg_range`` / ``rdg_range``, ``mdg_cd`` / ``rdg_cd``, ``mdg_ready`` / ``rdg_ready``
- ``mdg_projectile`` / ``rdg_projectile``: bandera de proyectil (bonificación de alcance en terreno alto, reglas básicas bajas versus altas)
- ``mdg_splash`` / ``rdg_splash``, ``mdg_radius`` / ``rdg_radius``, ``mdg_splash_decay``
- ``mdg_targets`` / ``rdg_targets``: ``ground``, ``air``, ``unit``, ``building``, o un nombre de tipo
- ``mdg_crit`` / ``rdg_crit``, ``mdg_crit_rate`` / ``rdg_crit_rate``, ``crit_vs``
- ``mdg_piercing`` / ``rdg_piercing`` (porcentaje de armadura ignorado), ``piercing_vs``
- ``mdg_explode`` / ``rdg_explode``, ``exp_dgf``, ``exp_hp_cost``, ``mdg_explode_vs``
- Modificadores de terreno por **atacante** (desde 1.4.5.0): ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``; Misma sintaxis que ``speed_on_terrain`` — ver ``building-land-terrain.rst`` *Modificadores de combate de unidades en el terreno*

Amenaza automática / prioridad de objetivo (desde 1.4.5.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

El ``menace`` de una unidad ya no es solo el daño. Si rules no fija un valor
absoluto, el motor usa una **puntuación de combate multidimensional** para:

- Elegir objetivo automáticamente (mayor amenaza primero; jugadores PC que no
  son ``timers`` también pueden mezclar ``mdg_vs``/``rdg_vs`` con
  ``counter_skill`` — ver ``aimaking.rst``)
- Sumas de amenaza enemiga por casilla y decisiones de IA relacionadas

**Dimensiones** (arma principal = el mayor de ``mdg`` / ``rdg``):

- Daño, acierto (``mdg_cover``/``rdg_cover``, 0 = 100%%), enfriamiento
  (``*_cd``), preparación (``mdg_ready``/``rdg_ready`` — no el ``*_delay`` balístico)
- HP (``hp`` actual, si no ``hp_max``), armadura (``max(mdf, rdf)``), esquiva
  (``max(mdg_dodge, rdg_dodge)``)
- Alcance de ataque, velocidad de movimiento

Aproximadamente: DPS efectivo (daño × acierto / (cd + ready)), luego
supervivencia y factores de alcance/velocidad.

**Overrides opcionales en rules** (defs de unidad):

======= ================= ============================================================
Campo     Tipo              Significado
======= ================= ============================================================
``menace`` absoluto         Amenaza fija; **no** sigue mejoras; sustituye lo automático
``menace_mult`` peso (1)    Multiplica la base multi-dim (sigue cambiando con stats)
``menace_vs`` absoluto vs   Amenaza fija hacia ese tipo de observador / ``is_a``
``menace_mult_vs`` peso vs  Base multi-dim × peso hacia ese observador
======= ================= ============================================================

Orden de búsqueda (``menace_versus``): ``menace_vs`` → ``menace_mult_vs`` →
``menace`` / ``menace_mult`` / puntuación automática global.

Ejemplo::

    def knight
    mdg 6
    menace_mult 1.5

    def archer
    rdg 5
    menace_vs knight 3
    menace_mult_vs mage 1.2

**Pesos ajustables** en ``def parameters`` (importancia de armadura/esquiva/alcance/velocidad
y normalización de HP; daño+cd+ready+cover siempre alimentan el núcleo de DPS)::

    def parameters
    menace_armor_weight 1
    menace_dodge_weight 1
    menace_range_weight 0.15
    menace_speed_weight 0.2
    menace_hp_ref 50

Prefiera ``menace_mult`` / ``menace_mult_vs`` para unidades que investigan mejoras;
use ``menace`` / ``menace_vs`` absolutos solo si quiere una prioridad fija.

Carga y contracarga (desde 1.4.0.1)

Carga: las unidades con estadísticas de carga pueden realizar un ataque de carga de alto daño cuando se enfrentan a un
enemigo dentro del alcance. Después de cargar, entran en tiempo de reutilización y solo actúan normalmente ``mdg`` / ``rdg``.
hasta que finalice el tiempo de reutilización. Para cargar el mismo objetivo nuevamente, lleve la unidad más allá
``charge_mdg_dist`` / ``charge_rdg_dist`` después de que expire el tiempo de reutilización.

Charge damage (additive, not a multiplier)::

    charge_damage = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)


Ejemplo: ``mdg 6, charge_mdg 2`` → base ``6 + 2 = 8``, luego escalado por distancia dentro
``charge_mdg_dist`` (aproximadamente 50% a quemarropa, hasta ~100% en el rango máximo). Usos a distancia ``rdg`` /
``charge_rdg`` de la misma manera.

Propiedades de carga (pares cuerpo a cuerpo/a distancia; intercambiar ``mdg`` ↔ ``rdg`` por a distancia):

- ``charge_mdg`` / ``charge_rdg`` — daño por carga adicional (agregado)
- ``charge_mdg_vs`` / ``charge_rdg_vs`` — bonificación frente a tipos de unidades específicas
- ``charge_mdg_cd`` / ``charge_rdg_cd`` — tiempo de reutilización (ms)
- ``charge_mdg_dist`` / ``charge_rdg_dist`` — rango de carga máximo
- ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` — rango mínimo para activar (0 = sin límite)
- ``charge_mdg_splash`` / ``charge_rdg_splash`` — daño por salpicadura
- ``charge_mdg_radius`` / ``charge_rdg_radius`` — radio de salpicadura
- ``charge_mdg_splash_decay_min`` / ``charge_rdg_splash_decay_min`` — caída mínima de salpicadura (0,0–1,0)

Example (campaign knight)::

    def knight
    mdg 3
    charge_mdg 2
    charge_mdg_cd 10
    charge_mdg_dist 15
    charge_mdg_min_dist 3
    charge_mdg_splash 1
    charge_mdg_radius 1
    charge_mdg_splash_decay_min 0.5


Contracarga: contrarresta una carga entrante. Cuando una unidad de contracarga bloquea una carga
atacante dentro del alcance, la carga del atacante se interrumpe (ese golpe se resuelve como un ataque normal).
ataque) y el atacante sufre daño de contracarga.

Counter-charge damage (additive)::

    counter = attacker (mdg/rdg + mdg_vs/rdg_vs) + attacker (charge_mdg/charge_rdg + charge_mdg_vs/charge_rdg_vs)
            + self (op_charge_mdg/op_charge_rdg + op_charge_mdg_vs/op_charge_rdg_vs)


Propiedades de contracarga:

- ``op_charge_mdg`` / ``op_charge_rdg`` — contra daño adicional (agregado)
- ``op_charge_mdg_vs`` / ``op_charge_rdg_vs`` — bonificación frente a tipos de atacantes
- ``op_charge_mdg_cd`` / ``op_charge_rdg_cd`` — tiempo de reutilización
- ``op_charge_mdg_dist`` / ``op_charge_rdg_dist`` — alcance efectivo (0 = ilimitado)

``Sounds (``style.txt``)`: ``charge_success``, ``charge_failed``, ``op_charge``. también
``critical_hit``, ``piercing_triggered`` para comentarios de combate.

Notas: los autoataques no activan la carga; La salpicadura de carga terrestre no golpea a las unidades aéreas.

Ataques de ráfaga/secuencia (``damage_seq``, desde 1.3.8.2, mejorado en 1.4.3.6)
--------------------------------------------------------------------------------

Un ciclo de ataque puede disparar múltiples golpes en rápida sucesión (Age of Empires Chu Ko Nu
estilo). Defina la base ``mdg`` / ``rdg`` primero, luego ``damage_seq``:

``damage_seq mdg|rdg \<times\> [(damage d1 d2 ...)] [(interval seconds)]``

- División explícita: ``(damage 6 3 3)``: los valores del segmento entero deben sumar la base
  daño (las mismas unidades que ``mdg`` / ``rdg`` en reglas.txt)
- División automática (desde 1.4.3.6): omite ``(damage ...)`` para dividir el daño base uniformemente
  ``times`` (funciona con daño fraccional, por ejemplo, ``rdg 7.5`` con ``times 3`` → 2,5 por disparo)
- Intervalo: ``(interval 0.25)`` segundos entre disparos; si se omite o 0 con ``times \> 1``,
  predeterminado 0,25 s
- Límite: como máximo 6 disparos por ataque
- Tiradas de golpe: cada segmento tira golpe, crítico y desventaja por separado
- Enfriamiento: ``mdg_cd`` / ``rdg_cd`` comienza después de que termina la ráfaga completa
- Sonidos: cada disparo activa ``launch_mdg`` / ``launch_rdg``; enumerar múltiples ID de sonido
  en ``style.txt`` (por ejemplo, ``launch_rdg 1042 1042 1042``)

Ranged burst example (built-in ``repeating_crossbowman``)::

    def repeating_crossbowman
    rdg 6
    rdg_cd 2.5
    rdg_range 4
    rdg_projectile 1
    damage_seq rdg 3 (interval 0.25)


Melee example with explicit damage split::

    def footman
    mdg 12
    mdg_cd 1.5
    mdg_range 6
    damage_seq mdg 3 (damage 6 3 3) (interval 0.2)


Véase también ``../player/burst-attacks.htm``.

Armas y armaduras (desde 1.4.1.3)
---------------------------------

Las armas (``class weapon``) y las armaduras (``class armor``) tienen estadísticas de combate. Referencia de unidades
them::

    def footman
    class soldier
    weapons sword bow     ; first weapon is default / main weapon
    auto_weapon_switch 1  ; 1 = auto-switch by range in combat
    armor light_armor


Los jugadores cambian de arma con A / Shift+A o B y luego X. El cambio manual anula el cambio automático.
Las estadísticas de la unidad y del equipo equipado se suman. Las armas apoyan la herencia como
unidades.

Mejoras y desventajas (desde 1.3.9.8, ampliado en 1.4.1.7)
----------------------------------------------------------

Adjunte a ataques con ``buffs`` / ``debuffs``, o mediante habilidades con ``effect buffs`` /
``effect debuffs``.

``reflect_percent`` (porcentaje entero) en una mejora permite reflejar el daño; aplicar con
``effect buffs``. No existe ``effect reflect``. Ejemplo: ``b_douzhuan`` en ``mods/wuxia/rules.txt``.

Multi-stat buff example::

    def HealEnhancementBuff
    class buff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1


Modos de disparo:

1. Predeterminado: al golpear
2. :strong:```is_active 1`` — al iniciar un ataque (activo)
3. :strong:```is_passive 1`` — al recibir daño (pasivo), con ``trigger_condition`` (p. ej.
   ``hp \< 20``) y ``passive_trigger_rate``

Tasas de activación (porcentaje; el valor predeterminado vuelve a las tasas de ataque normales):

- ``mdg_trigger_rate`` / ``rdg_trigger_rate`` — daño normal
- ``charge_mdg_trigger_rate`` / ``charge_rdg_trigger_rate`` — daño por carga
- ``op_charge_mdg_trigger_rate`` / ``op_charge_rdg_trigger_rate`` — contracarga

Habilidades (habilidad de clase)
--------------------------------

Define skills with ``class skill`` instead of ``class ability``::

    def fireball
    class skill
    mana_cost 50
    cost 10 0
    time_cost 30
    effect harm_target 60
    effect_target ask
    effect_range 12
    cooldown 10


``can_use_tech`` se aplica a las actualizaciones; ``can_use_skill`` se aplica a las habilidades.

Desde 1.4.4.6: ``harm_target``, ``harm_area``, ``burst``, ``push``, ``effect buffs`` / ``debuffs``, etc. Mod de demostración: ``mods/wuxia/rules.txt``. Consulte `Skills guide <../../zh/mod/skills-and-effects.htm>`_.

**Activadores de habilidades (desde 1.4.4.6)**

Las habilidades aprendidas van en ``can_use_skill``. Manual y automático pueden coexistir (``manual_use 1`` + ``auto_trigger 1``).

+--------------------+---------------------------------------------------+
| ``manual_use 1``   | Mostrar en el menú de comandos (predeterminado 1) |
+--------------------+---------------------------------------------------+
| ``auto_trigger 1`` | Dispara automáticamente en combate                |
+--------------------+---------------------------------------------------+
| ``trigger_timing`` | Cuándo disparar automáticamente (ver tabla)       |
+--------------------+---------------------------------------------------+

+-----------------------------+-------------------------------------------------+----------------------------+
| ``trigger_timing``          | Cuando                                          | Lista heredada             |
+=============================+=================================================+============================+
| ``on_hit`` (predeterminado) | Después de golpear a un enemigo                 | ``active_trigger_skills``  |
+-----------------------------+-------------------------------------------------+----------------------------+
| ``on_attack``               | Al inicio del ataque; el ataque normal continúa | ``attack_trigger_skills``  |
+-----------------------------+-------------------------------------------------+----------------------------+
| ``on_attack_replace``       | Al inicio del ataque; reemplaza este ataque     | ``attack_replace_skills``  |
+-----------------------------+-------------------------------------------------+----------------------------+
| ``on_damaged``              | Cuando es golpeado por un enemigo (pasivo)      | ``passive_trigger_skills`` |
+-----------------------------+-------------------------------------------------+----------------------------+

Tarifas: ``active_trigger_rate`` / ``passive_trigger_rate`` (1–100); opcional ``mdg_trigger_rate`` / ``rdg_trigger_rate`` anula la velocidad activa para cuerpo a cuerpo/a distancia.

Condiciones: ``trigger_condition hp < 30`` (``hp``/``mana`` comparado como porcentaje) o ``hp_threshold 30``. Comprobado solo para ``on_hit`` y ``on_damaged``, no para ``on_attack``/``on_attack_replace``.

Los disparadores automáticos consumen maná y respetan el tiempo de reutilización; ``ready`` la cuerda se aplica como los yesos manuales.

Example (passive on hit taken)::

    def skill_thorns
    class skill
    auto_trigger 1
    manual_use 0
    trigger_timing on_damaged
    passive_trigger_rate 30
    effect harm_target 10
    effect_target ask


Referencia completa: `Skills guide <../../zh/mod/skills-and-effects.htm>`_ (sección sobre modos de disparo).

Efectos (efecto de clase, desde 1.4.1.7)
----------------------------------------

Harm and heal are split into detailed parameters::

    def exorcism
    class effect
    harm_level 2
    harm_cd 7.5
    harm_radius 6
    harm_target_type undead
    debuffs b_slow


De manera similar: ``heal_level``, ``heal_cd``, ``heal_radius``, ``heal_target_type``;
``hp_regen_cd``, ``mana_regen_ready``, etc.

Sistema de fases (desde 1.4.2.4)
--------------------------------

``class phase`` advances game eras without upgrading the base::

    def dark_age
    class phase
    cost 0 0
    time_cost 0

    def feudal_age
    class phase
    cost 10 15
    time_cost 130
    phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
    units_auto_upgrade 0
    phase_targets soldier


Opcional ``phase_targets`` limita qué unidades reciben entradas sin costo de ``phase bonus`` (las bonificaciones de tipo costo siempre se aplican a nivel de jugador). Dejar vacío para todas las unidades. Utilice nombres de categorías (``soldier``, ``worker``, ``building``, ``unit``, etc.), nombres de unidades específicas (``footman knight``) o cualquier nombre en la cadena ``is_a``; cualquier coincidencia positiva cuenta. Un ``-`` inicial excluye una coincidencia, p. ``phase_targets -building`` significa todas las unidades excepto los edificios; puede mezclar incluye y excluye, p. ``phase_targets soldier -footman``.

On a building::

    can_advance feudal_age


Utilice ``can_advance`` (no ``can_research``) para las fases. Presione V en el edificio para ver el
fase actual.

``hide_locked_commands 1`` en ``def parameters`` oculta comandos cuyos requisitos no son
aún conocido.

Además de nombres de tipo simples (todos deben cumplirse — AND), ``requirements`` puede
pedir cualesquiera N edificios de un grupo con nombre (desde 1.4.5.8)::

    def stables
    class building
    requirements castle_age

    def imperial_age
    class phase
    requirements castle_age any_buildings 2 castle_age_buildings

    def castle
    class building
    requirements any_buildings 2 castle_age_buildings

``any_buildings <n> <group>_buildings`` quita ``_buildings`` y recoge edificios cuyo
``requirements`` simple incluye esa clave. Use ``castle_age_buildings``, no el nombre
desnudo de la fase. El token de grupo no dispara ``units_auto_upgrade``.

Economía (desde 1.4.0.x)
------------------------

``population_cost`` replaced ``food_cost``. Buildings can produce or hold resources::

    auto_production 1       ; auto produce (gas, etc.); restarts while not full
    manual_production 1     ; player-started production
    auto_cultivate 1        ; farms; restarts only when storage is empty
    is_gather 1             ; output goes to building storage; workers haul to base
    resource_volume_max 8
    resource_volume_start 0
    production_type resource2
    production_time 18      ; seconds to fill one batch
    production_qty 8        ; amount per production cycle (into building storage)
    extraction_time 2       ; worker harvest time from building (seconds)
    extraction_qty 8        ; worker carry size per trip


Without ``is_gather``, both auto and manual production credit ``production_type`` output straight into the player's stockpile (e.g. ``gold_house``)::

    auto_production 1
    manual_production 1
    production_type resource1
    production_time 100
    production_qty 200


For pickable loot instead, use ``production_item`` (instead of ``production_type``)::

    production_item gold_pile
    production_qty 1


| Atributo | Rol |
| --- | --- |
| ``production_type`` | Recurso producido (con ``production_time`` y ``production_qty`` define la capacidad de producción) |
| ``production_time`` | Segundos por ciclo de producción |
| ``production_qty`` | Producción por ciclo; sin ``is_gather``, agregado a los recursos del jugador; con ``is_gather``, al edificio ``resource_qty`` |
| ``auto_production`` | Cuando ``1``, muestra producción automática; bucles después de cada ciclo; uso para gas (no ``auto_cultivate``) |
| ``manual_production`` | Cuando ``1``, muestra producción manual; un ciclo por clic; independiente de ``auto_production`` |
| ``auto_cultivate`` | Autocultivo en edificios ``is_gather`` (por ejemplo, granjas); paralelos ``auto_production`` |
| ``manual_cultivate`` | Cultivo manual; paralelos ``manual_production``; establezca ``1`` explícitamente cuando sea necesario |
| ``production_item`` | Nombre del tipo de artículo; genera elementos seleccionables al lado del edificio al finalizar |
| ``is_gather`` | La producción permanece en el edificio hasta que un trabajador con ``can_gather_building`` la transporta a un almacén |
| ``resource_volume_max`` | Máximo almacenado en el edificio (por ejemplo, 8 vespeno) |
| ``resource_volume_start`` | Cantidad inicial almacenada cuando se construye (``0`` = vacío) |
| ``extraction_time`` / ``extraction_qty`` | Tiempo de cosecha de los trabajadores y monto por viaje desde el edificio o depósito |

.. note::

   ``auto_production`` y ``manual_production`` son indicadores separados y ambos pueden ser ``1`` (por ejemplo, ``gold_house``). ``auto_production`` ausente o ``0`` no implica modo manual; configure ``manual_production 1`` para el comando manual. Lo mismo para ``auto_cultivate`` / ``manual_cultivate`` en granjas.

.. note::

   ``is_create`` está en desuso: las pilas de terreno ``class resource`` ya no se generan. Utilice ``production_type`` (almacenamiento directo), ``is_gather`` (almacenamiento de edificios) o ``production_item`` (elementos de generación).

``class resource`` is separate from ``class deposit``. Map deposits::

    mineral_field 1500 a1
    geyser 1 e1


Gas structures must sit on the matching deposit::

    requires_deposit geyser
    is_buildable_anywhere 0


Consulte ``sc_gas_building`` / ``assimilator`` en ``mods/starcraft/rules.txt``. Guía del jugador:
``../player/starcraft-resources.htm``. La pantalla de atributos (V) agrega requiere depósito;
El tiempo/cantidad de producción utiliza las entradas de atributos de producción existentes.

Héroes (desde 1.4)
------------------

Defina unidades de héroe en cualquier ``rules.txt`` (reglas básicas, modificaciones, paquetes de campaña, paquetes de mapas multijugador). Funcionan en escaramuzas, mapas aleatorios, multijugador y campañas: matar XP, subir de nivel ``xp_thresholds``, revivir ``is_revivable``, inventario, etc. El guardado entre capítulos (``campaign_carryover`` en la siguiente sección) es una característica adicional solo para campañas para un jugador.

Ejemplo multijugador: ``hero`` / ``hero_knight`` en ``res/multi/td2/rules.txt``.

::

    def hero
    class soldier
    global_count_limit 1
    is_revivable 1
    revival_time 10
    xp_thresholds 200 500 900
    hp_max_per_level 1000
    mdg_per_level 100
    resource_rewards 300
    xp_reward 100


``Level and XP (``nivel`` / ``xp`` / ``xp_umbrales`` / ``xp_umbral_crecimiento``)``

| Campo | Predeterminado | Significado |
| --- | --- | --- |
| ``xp_thresholds`` | (vacío) | Puertas de XP acumuladas. El primer valor es el XP total para el nivel 2 (o el nivel 1 cuando se comienza en el nivel 0); cada valor siguiente es el siguiente nivel. |
| ``max_level`` | (ninguno) | Límite de nivel de héroe. Con ``xp_threshold_growth``, la carga de reglas genera umbrales ``max_level - 1`` automáticamente |
| ``xp_threshold_growth`` | (ninguno) | Generar automáticamente ``xp_thresholds`` a partir de una fórmula (tabla a continuación). Requiere ``max_level``; use esta o una lista ``xp_thresholds`` explícita (la lista explícita gana) |
| ``level`` | ``1`` | Nivel inicial. Cuando ``\> 1`` con ``xp_thresholds``, las bonificaciones acumulativas de ``*_per_level`` y ``level_skills`` se aplican al generar. |
| ``xp`` | ``0`` | XP acumulativo inicial opcional. |
| ``level_up_heal_full`` | ``0`` | ``1`` = restaurar HP y maná completos en cada nivel superior; ``0`` = agrega solo el incremento ``hp_max_per_level`` / ``mana_max_per_level`` a los valores actuales (predeterminado). |
| ``level_up_reset_xp`` | ``0`` | ``1`` = restablecer la XP actual a 0 después de cada nivel superior; ``0`` = mantener XP acumulativo (predeterminado). Cuando ``1``, prefiera ``xp_thresholds`` por nivel (XP desde el último nivel), no totales acumulativos. |

- Nivel máximo = ``len(xp_thresholds) + 1`` (por ejemplo, nueve umbrales → límite de nivel 10).
- Estado de la unidad (pestaña): los héroes con ``xp_thresholds`` siempre anuncian el nivel (incluidos 0 y 1). XP se muestra como ``current / next gate`` (en el nivel 0, la siguiente puerta es ``xp_thresholds[0]``).
- ``xp_thresholds`` (o ``xp_threshold_growth`` después de la expansión) solo → nivel 1 predeterminado al inicio del juego; ``level 0`` comienza por debajo del nivel 1.

:strong:```xp_threshold_growth`` curve types`` (threshold index ``i`` comienza en 0 para el nivel 2, 3,…)

| Tipo | Sintaxis | Fórmula |
| --- | --- | --- |
| lineal | ``linear BASE STEP`` | ``BASE + STEP × i`` |
| cuadrático | ``quadratic BASE A B`` | ``BASE + A×i + B×i²`` |
| polinomio | ``polynomial c0 c1 c2 …`` | ``c0 + c1×i + c2×i² + …`` |
| geométrico | ``geometric FIRST RATIO`` | ``FIRST × RATIO^i`` (``RATIO`` puede ser fraccionario, por ejemplo, ``1.08``) |

Example (100-level hero, linear cumulative XP)::

    def long_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50
    hp_max_per_level 30
    mdg_per_level 2


Example (Raynor-style quadratic curve, same as ``40 90 160 250 …``)::

    def raynor_curve
    class soldier
    max_level 10
    xp_threshold_growth quadratic 40 40 10
    hp_max_per_level 30


Example (child def overrides only the level cap; inherits parent ``xp_threshold_growth``)::

    def base_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50

    def short_campaign_hero
    is_a base_hero
    max_level 20


Example (level 0 start, explicit threshold list)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160 250 360 490 640 810 1000
    hp_max_per_level 30
    mdg_per_level 2
    level 0


Example (full heal on level up)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160
    hp_max_per_level 30
    level_up_heal_full 1


Example (level 3 start with initial XP)::

    def veteran_hero
    is_a knight
    xp_thresholds 200 500 900
    hp_max_per_level 20
    level 3
    xp 500


Transferencia de héroe de campaña (según reglas)
------------------------------------------------

Agregue ``campaign_carryover 1`` a una definición de héroe de la sección anterior. Solo campañas para un jugador: al ganar, el progreso se guarda en ``user/campaigns.ini`` y se restaura en el siguiente capítulo (el reintento de derrota no se sobrescribe). La cooperativa no persiste héroes.

::

    def my_hero
    is_a knight
    campaign_carryover 1
    campaign_carryover_stats 1
    campaign_carryover_inventory 1
    inventory_capacity 8


| Campo | Predeterminado | Significado |
| --- | --- | --- |
| ``campaign_carryover`` | ``0`` | ``1`` = habilitar guardar entre capítulos |
| ``campaign_carryover_id`` | nombre definido | Teclas ``hero_\<id\>\_xp``, ``\_level``, ``\_inventory`` |
| ``campaign_carryover_stats`` | ``1`` | Nivel + XP |
| ``campaign_carryover_inventory`` | ``1`` | Artículos de mochila |

Solo estadísticas: ``campaign_carryover_inventory 0``. Solo inventario: ``campaign_carryover_stats 0``. Sin transferencia: omitir ``campaign_carryover 1``.

Opcional en ``campaign.txt``: ``hero_min_level 13:2 16:3 …`` para niveles de piso de capítulos.

Separado de ``campaign_flag`` / ``add_inventory_item`` (fichas de historia, alianzas). Consulte ``mod/campaign-hero-carryover.htm``.

Contenedores de transporte (cambio de nombre de campo desde 1.4.4.9; aún se aceptan nombres heredados)
------------------------------------------------------------------------------------------------------

Las unidades o edificios con ``transport_capacity`` actúan como contenedores de transporte. Propiedades relacionadas:

| Propiedad | Efecto | Ejemplo |
| --- | --- | --- |
| ``passenger_attack_types`` | Tipos de unidades que pueden atacar afuera mientras están adentro | ``passenger_attack_types archer knight`` o ``all`` |
| ``load_bonus`` | Por unidad cargada → estadísticas agregadas al **contenedor** | ``load_bonus speed 0.5 mdg 2`` |
| ``passenger_bonus`` | Estadísticas agregadas al **pasajero** mientras está dentro (revertidas al descargar) | ``passenger_bonus rdg_range 1 mdg 2`` |

Example::

    def flyingmachine
    class soldier
    transport_capacity 8
    passenger_attack_types knight archer
    load_bonus speed 0.5
    passenger_bonus rdg_range 1

    def wall
    class building
    transport_capacity 4
    passenger_attack_types archer catapult
    passenger_bonus mdg 2


- Sin ``passenger_attack_types``, los pasajeros no pueden atacar objetivos externos de forma predeterminada.
- ``load_bonus`` y ``passenger_bonus`` se pueden combinar en el mismo contenedor.

Ocupación de casilla (``space``, desde 1.4.5.8)
-----------------------------------------------

``space`` es una propiedad de precisión (admite decimales). Indica cuánto ocupa la unidad
en su capa aire/tierra/agua. La capacidad es el ``square_width`` del mapa en las mismas unidades.

| Ajuste | Efecto |
| --- | --- |
| ``space 0`` (predeterminado) | No consume capacidad (ilimitado, legado) |
| ``space 1`` con ``square_width 12`` | Como máximo 12 unidades en esa capa |
| ``space 0.5`` con ``square_width 12`` | Como máximo 24 |
| ``space`` > ``square_width`` | La unidad no puede entrar en esa casilla |

La capacidad es compartida por todos los bandos. Si la casilla está llena, se rechazan
el movimiento y el entrenamiento que spawnearía allí (voz ``not_enough_space``).
Las capas son independientes: la ocupación terrestre no bloquea a las unidades aéreas.

Ejemplo::

    def peasant
    class worker
    space 1

    def siege_engine
    class soldier
    space 4

Véase también ``square_width`` en ``mod/mapmaking.rst``.

Artículos (desde 1.4.1.3)
-------------------------

::

    def magic_sword
    class item
    consume_on_pickup 0
    buffs power_buff
    resource_rewards resource1 50


``is_loot 1`` deja caer el artículo cuando el portador muere.

``Item sounds (``estilo.txt``; use sounds since 1.4.4.6)``

| Cuando | Artículo ``style.txt`` | Unidad ``style.txt`` | Valor predeterminado global (``def thing``) |
| Recogida | ``on_pickup`` | ``pickup_\<item type\>`` | ``pickup`` |
| Gota | ``on_drop`` | ``drop_\<item type\>`` | ``drop`` |
| Uso | ``use`` / ``on_use`` | ``use_\<item type\>`` | ``item_used`` |

On the item (``use`` and ``on_use`` are equivalent; multiple IDs are chosen at random)::

    def zhuiri_jianfa_book
    title 7754
    pickup 1506
    use 1506


On the unit::

    def raynor
    use_zhuiri_jianfa_book 1506


Global fallback::

    def thing
    item_used 1194 1195 1196


La herencia (``is_a``) funciona como ``on_pickup`` / ``on_drop``: los tipos derivados anulan los padres.

Inventario y artículos equipables (desde 1.4.3.1)
-------------------------------------------------

Las unidades necesitan ``inventory_capacity`` > 0 para contener elementos. Cada artículo usa una ranura (``transport_volume``
está definido pero la capacidad actualmente cuenta los artículos, no el volumen).

Built-in gear (traditional)::

    def footman
    weapons sword          ; class weapon — built-in, not in backpack
    armor footman_armor    ; class armor — built-in


Equippable items (unified model): the same type name can be ``class item``::

    def sword
    class item
    equippable_as_weapon 1
    mdg 3.5
    mdg_range 1
    transport_volume 1

    def footman_armor
    class item
    equippable_as_armor 1
    mdf 0.5


Cuando ``weapons`` / ``armor`` en una unidad apunta a elementos equipables, el motor crea un elemento
instancias en el momento del desove y las coloca en el inventario. Si la unidad no tiene equipo incorporado de ese
tipo y ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` es ``1`` (predeterminado), son
silently equipped::

    def footman
    inventory_capacity 2
    weapons sword
    armor footman_armor


Reglas de cambio de equipo cuando una unidad tiene equipo incorporado y de objeto (p. ej.
``weapons bow sword`` con ``bow`` como ``class weapon`` y ``sword`` como artículo equipable):

- El equipo incorporado siempre está equipado en el momento del desove; El equipo del artículo va a la mochila.
- Con ``spawn_weapons_equipped 1`` (predeterminado), las armas de los objetos permanecen en la mochila y no pueden
  estar equipado; con ``spawn_weapons_equipped 0``, el jugador puede equiparlos manualmente.
- El equipo incorporado solo puede cambiar con el equipo incorporado; equipo de artículo solo con equipo de artículo;
  No hay conmutación cruzada entre los dos tipos. Las mismas reglas se aplican a la armadura.
  (``spawn_armor_equipped``).

Mixed archer example::

    def archer
    weapons bow sword
    spawn_weapons_equipped 1   ; bow equipped, sword in backpack, sword not equippable
    inventory_capacity 3

    def archer
    weapons bow sword
    spawn_weapons_equipped 0   ; bow equipped, sword in backpack, player may equip sword
    inventory_capacity 3


Los consumibles (``buffs`` solamente, no ``equippable_as_*``) se usan desde la mochila con Enter,
no desde la pantalla del equipo. En caso de éxito, se reproducen los sonidos ``use`` / ``on_use``; consumibles normales
anuncie el título del artículo más "usado".

Skill books (permanently learn a skill; consumed on successful use)::

    def zhuiri_jianfa_book
    class item
    skills skill_zhuiri_jianfa
    learn_level 10
    transport_volume 1


- ``learn_level`` / ``learn_level_skills``: nivel mínimo para aprender del libro (el más estricto de
  unidad ``learn_level_skills`` y reglas del artículo).
- Unidad ``level_skills``: desbloqueo automático al subir de nivel (separado de los libros; no duplique el mismo
  habilidad o uso regresa ``skill_already_known`` y se queda con el libro).
- Con ``learn_level`` / ``learn_level_skills`` en el objeto, recogerlo no otorga la habilidad;
  el jugador debe usar el libro de la mochila.
- Éxito: usar sonido + título de habilidad TTS + mensaje ``skill_learned``; fallo: ``order_impossible``
  con ``skill_level_too_low`` / ``skill_already_known`` etc.

``Treasure with ``use_square`` (rewards only when used in backpack at a named square)::

    def mystery_treasure
    class item
    use_square b2
    resource_rewards resource1 150


Órdenes del servidor (también utilizables en acciones desencadenantes ``order``): ``equip_weapon``, ``unequip_weapon``,
``equip_armor``, ``unequip_armor``, ``use_item``, ``drop``.

Comportamiento predeterminado de la unidad (desde 1.4.3.1)
----------------------------------------------------------

Comportamiento inicial por unidad en ``rules.txt``:

- ``ai_mode``: ``offensive``, ``defensive``, ``guard`` o ``chase``. Predeterminado: ``offensive``
  para soldados, ``defensive`` para trabajadores. Se aplica a unidades de combate.
  ``chase`` mantiene un ``AttackAction`` y sigue entre casillas (sin ``go`` automático);
  ``offensive`` / ``guard`` siguen respetando ``position_to_hold`` al nacer hasta que una orden haga ``stop()``;
  ``defensive`` / ``chase`` no.
- ``auto_gather``: ``1`` o ``0``. Predeterminado ``1``. Sólo trabajadores.
- ``auto_repair``: ``1`` o ``0``. Predeterminado ``1``. Sólo trabajadores.
- ``auto_explore``: ``1`` o ``0``. Predeterminado ``0``. Unidades móviles (velocidad > 0).
- ``can_auto_explore``: ``1`` o ``0``. Predeterminado ``0``. Agrega habilitar/deshabilitar la exploración automática a
  menú de comando de la unidad.
- ``no_number`` (desde 1.4.3.2): ``1`` o ``0``. Predeterminado ``0`` (siempre diga números de serie,
  por ej. "campesino 1 en a1"). Cuando ``1``: omitir el número mientras solo una unidad de vivienda de esa
  el tipo existe ("Guan Yu en a1"); con dos o más, utilice números ("Guan Yu 1", "Guan Yu 2").
  Los resúmenes grupales siguen la misma regla. Para héroes o líderes únicos.

``ai_mode patrol`` no es válido: la patrulla requiere un comando de ruta. Las unidades informáticas neutrales son
Todavía obligado a defender + contraatacar independientemente de ``ai_mode``.

Las unidades de jugador en modo ``offensive``, ``defensive`` o ``chase`` no atacan automáticamente a neutrales.
unidades (``computer_only ... neutral``) y el modo defensivo no huye solo de los neutrales.
``go`` normal sobre un neutral solo mueve; ``attack`` normal sobre ``is_huntable`` hace daño.
Usa un ataque imperativo (por ejemplo, Ctrl+clic) para que la IA trate un creep/PNJ neutral como objetivo automático.

Example::

    def knight
    class soldier
    ai_mode guard
    auto_explore 1
    can_auto_explore 1

    def peasant
    class worker
    auto_gather 1
    auto_repair 0
    ai_mode defensive


Orden de captura/ocupación predeterminada
-----------------------------------------

Objetivo — ``capture_hp_threshold`` (en edificios/unidades capturables):

| Valor | Significado |
| --- | --- |
| ``0`` (predeterminado) | No capturable a través del umbral de HP |
| ``100`` | Captura de contacto: convierta al propietario a su llegada, sin daños; el orden predeterminado al hacer clic con el botón derecho es capturar (consulte ``can_capture``) |
| ``30`` etc. | Capturable cuando HP ≤ ese porcentaje durante el combate normal |

Atacante — ``can_capture`` (a soldados/trabajadores con ataque):

| Valor | Significado |
| --- | --- |
| ``1`` (predeterminado) | Haga clic derecho en el enemigo con ``capture_hp_threshold 100`` → captura predeterminada; La IA utiliza la captura de contactos |
| ``0`` | Mismo objetivo → ataque/movimiento predeterminado; La IA ataca normalmente |

Requiere ``attack`` en las habilidades de la unidad; El objetivo debe ser un enemigo vivo y vulnerable.

Example — only footmen capture barracks; archers attack::

    def captured_barracks
    class building
    capture_hp_threshold 100
    ...

    def footman
    class soldier
    can_capture 1
    ...

    def archer
    class soldier
    can_capture 0
    ...


PDI de mapa aleatorio ``captured_barracks`` y juego estilo HoMM: ``player/homm-civ5-play.htm``.

Reparación de barcos (desde 1.4.1.1)
------------------------------------

give order — transfer an inventory item to another unit::

    give <target unit id>
    give <target unit id> <item type or id>


Campos de destino (todos deben pasar):

- ``receive_items 1`` (predeterminado 0: los NPC deben participar)
- ``accepted_items``: lista blanca opcional de tipos de elementos (se admite herencia ``is_a``); vacío = cualquiera
- ``accept_from`` — lista opcional: ``self``, ``ally``, ``neutral``, ``enemy``; vacío = cualquiera

Example NPC that accepts any item from anyone::

    def quest_npc
    receive_items 1
    inventory_capacity 5


Example: allied knights accept only ``knight_lance`` from allies::

    def knight
    receive_items 1
    accepted_items knight_lance
    accept_from ally


Registros de entrega ``received_items`` en el objetivo para verificaciones de activación. Se aplican artículos ``skills`` /
``buffs`` al recibirlo como ``pickup``. La entrega del script ignora el objetivo ``inventory_capacity``.
Demostración multijugador: ``res/multi/give_demo.txt``. Demostraciones de relación de campaña: ``The Legend of Raynor`` cap. 14-16
(``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``).

Campos de construcción, complementos y despegue (estilo StarCraft, ``mods/starcraft``)
--------------------------------------------------------------------------------------

El motor admite campos de construcción, modos de construcción de trabajadores, complementos Terran y
recombinación de despegue. Implementación de referencia: ``mods/starcraft/rules.txt``. Guías para jugadores:

- Complementos terrestres: ``../player/starcraft-terran.htm``
- Tumores de reina y fluencia zerg: ``../player/starcraft-zerg-creep.htm``

Campos de construcción (Protoss psi / Zerg creep)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Rol |
| --- | --- |
| ``provides_build_field \<name\>`` | Marca cuadrados cercanos (por ejemplo, ``psi``, ``creep``) |
| ``requires_build_field \<name\>`` | Requiere ese campo para colocar/construir; ``0`` exime el tipo (Nexus, Photon Cannon) |
| ``build_field_radius \<tiles\>`` | Radio del proveedor (pasos BFS de la plaza principal; use esto o ``build_field_radius_m``) |
| ``build_field_radius_m \<meters\>`` | Radio del proveedor en metros (misma escala que ``rdg_range``); Distancia euclidiana del proveedor `` (x,y)`` |
| ``build_field_persists 1`` | Las marcas permanecen después de que se destruye el proveedor (arrastre Zerg) |
| ``build_field_spreads 1`` | Distribuya marcas en cuadrados adyacentes cada segundo |
| ``build_field_spread_squares N`` | Capas por tick (predeterminado 1 cuando ``build_field_spreads``) |
| ``requires_build_field_on_square 1`` | Se debe marcar todo el cuadrado (Zerg); de lo contrario, el campo vivo en cualquier lugar del cuadrado es suficiente (Protoss) |
| ``loses_power_without_field 1`` | Apagado sin campo activo: detener la construcción/entrenamiento/energía (Protoss) |

:fuerte:```build_field_radius`` frente a ``build_field_radius_m``

Utilice una propiedad de radio por proveedor; deje el otro en 0 (predeterminado).

| Propiedad | Cómo se mide el alcance | Uso típico |
| --- | --- | --- |
| ``build_field_radius`` | BFS a pasos de la plaza principal del proveedor (mosaicos discretos) | Creep heredado basado en mosaicos |
| ``build_field_radius_m`` | Distancia euclidiana desde el proveedor (x, y) en metros | Cadenas psi protoss (tipo SC2); Criadero Zerg / tumor de fluencia en ``mods/starcraft`` |

Un cuadrado de mapa tiene unos 12 m de ancho (``square_width 12``). Ejemplos en el mod StarCraft:
Nexus 18 m, Pilón 12 m, Criadero 12 m, tumor de fluencia 4 m.

Campo en vivo vs marcado

- Campo vivo: actualmente proporcionado por edificios/unidades en pie (medidor: punto en círculo; mosaicos: BFS de ``place``).
- Campo marcado: marcas cuadradas persistentes pintadas en el registro y/o extendidas cada segundo.

``has_build_field_on_square`` acepta vivo O marcado. Zerg ``requires_build_field_on_square 1`` solo verifica los cuadrados marcados (no puedes construir sobre un creep vivo que aún no se ha extendido/marcado).

Cuando se configura ``build_field_persists 1`` o ``build_field_spreads 1``, los proveedores de radio de metros también pintan marcas en el rango (es necesario para que ``build_field_radius_m`` solo en Hatchery aún permita la construcción Zerg).

Tumor de fluencia de reina (``mods/starcraft``): las habilidades de invocación colocan edificios ``creep_tumor`` en las casillas seleccionadas. Atributos de habilidad:

| Atributo | Rol |
| --- | --- |
| ``summon_requires_build_field \<name\>`` | El cuadrado objetivo debe tener ese campo (vivo o marcado) |
| ``summon_requires_marked_field 1`` | El objetivo debe estar marcado (el tumor se extiende; Queen Spawn omite esto) |

Guía del jugador: ``../player/starcraft-zerg-creep.htm``. Léame del mod: ``mods/starcraft/readme.txt``.

Protoss (``protoss_building``)::

    requires_build_field psi
    is_buildable_anywhere 1
    self_constructs 1
    loses_power_without_field 1


Zerg (``zerg_building``)::

    requires_build_field creep
    requires_build_field_on_square 1
    is_buildable_anywhere 1
    self_constructs 1


Criadero: ``provides_build_field creep`` + ``build_field_radius_m 12`` + ``build_field_persists 1`` +
``build_field_spreads 1``. Tumor de arrastre de Queen Spawn / tumor Extender — ver ``../player/starcraft-zerg-creep.htm``.

Interfaz de usuario: ``def build_field_\<name\>`` + ``title \<tts_id\>`` en ``ui/style.txt``; ambiente opcional ``noise``.

Depósitos y gas (``requires_deposit``)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Rol |
| --- | --- |
| ``requires_deposit \<type\>`` | Debe basarse en un depósito de mapas (por ejemplo, ``geyser``); el depósito se elimina al finalizar |
| ``is_buildable_anywhere 0`` | Con ``requires_deposit``, bloques de construcción en terreno edificable |

La plantilla de gas ``sc_gas_building`` utiliza ``auto_production`` + ``is_gather`` + ``production_time`` / ``production_qty``.
Los trabajadores necesitan ``can_gather assimilator`` (tipo de edificio), no ``geyser`` (depósito).

Modos de construcción de trabajadores
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| ``build_mode`` | Comportamiento |
| --- | --- |
| ``assisted`` | El trabajador permanece hasta que termine (Terran SCV, predeterminado) |
| ``place_and_leave`` | El trabajador coloca el sitio y se va; ``self_constructs 1`` termina edificio (Sonda) |
| ``sacrifice`` | Trabajador se consume (Dron) |

Además: ``self_constructs 1``, ``build_sacrifices_worker 1``, ``is_buildable_anywhere 1`` (no hay una ranura ``class building_land`` separada en Protoss/Zerg/terran voladores).

Complementos terran
>>>>>>>>>>>>>>>>>>>

| Atributo | Rol |
| --- | --- |
| ``can_have_addon \<types\>`` | Tipos de host (Cuartel/Fábrica/Puerto estelar) |
| ``addon_max N`` | Máximo de complementos adjuntos (predeterminado 1) |
| ``is_addon 1`` | Construcción de complementos (laboratorio tecnológico, reactor) |
| ``addon_host_types \<hosts\>`` | ¿Qué hosts aceptan este complemento?
| ``addon_grants_train_\<host\> \<unit\>`` | Opción de tren adicional cuando se adjunta |
| ``addon_grants_research \<tech\>`` | Investigación adicional cuando se adjunta |
| ``addon_train_multiplier N`` | Doble producción del reactor |
| ``addon_offset_x \<value\>`` | Ranura lateral desplazada al este del host (3,5 mosaicos predeterminados) |

Cree un complemento en un host existente, no en un terreno desnudo.

Despegue y recombinación
>>>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Rol |
| --- | --- |
| ``can_change_to \<flying\>`` | anfitrión de tierra puede levantar |
| ``ground_form \<ground\>`` | La forma voladora aterriza como este tipo |
| ``change_time \<sec\>`` | Tiempo de transformación para ``change_to`` (sin costo de recurso/pop) |

Ascensor: los complementos se separan del suelo; El terreno edificable se restaura bajo el anfitrión (**el mismo tipo que el edificio consumió cuando se construyó**; los mapas de StarCraft usan ``build_site``). Si la unidad no tiene una referencia guardada, se utiliza la palabra clave ``building_land`` del mapa o una única palabra clave ``nb_<type>_by_square``.

Terreno: consume el objeto ``class building_land`` más cercano en el cuadrado (los nombres de API como ``find_meadow_near_xy`` son históricos).

Recombinar: Tab Tech Lab → Retroceso (vuela a la ranura de aterrizaje al oeste del laboratorio) → ``change_to`` suelo.

Terreno edificable versus espacio: terreno edificable = permiso de terreno; volver a colocar necesita alineación de ranura
(``tech_lab.x ≈ factory.x + addon_offset_x``, dentro de ~2,5 mosaicos de Manhattan).

El aterrizaje en su propia zona de despegue no se vuelve a conectar. Tierra equivocada con complemento huérfano → TTS ``addon_reattach_failed`` (7350).

Mapas de prueba: ``terran_addon_test``, ``terran_recombine_test``; campaña ``sc_build_tests`` cap. 3–4.

Reparación de barcos (desde 1.4.1.1)
------------------------------------

``can_repair_ships 1`` sobre trabajadores o edificios. Los trabajadores reparan barcos costeros adyacentes (6
cuadrados); edificios de barcos de reparación de automóviles en aguas vecinas (8 cuadrados).

Construcción de puentes sobre el agua (tramos de tejas)
-------------------------------------------------------

Los trabajadores pueden construir tramos ``is_buildable_on_water_only 1`` con agua pura; al finalizar
Se aplica ``bridge_terrain`` (por ejemplo, ``bridge_deck``). Los sitios de andamio usan normal
``buildingsite`` TTS; Los pasos utilizan el terreno terminado ``ground``. Ver
`water-bridge-building.htm <water-bridge-building.htm>`_ (`zh <../../zh/mod/water-bridge-building.htm>`_).

Pastoreo (trabajadores)
-----------------------

``can_herd 1`` permite a un trabajador pastorear animales con ``herdable 1`` (por ejemplo, ovejas). el
el valor predeterminado es ``0``; habilite el pastoreo explícitamente por tipo de trabajador en ``rules.txt``.

:fuerte:```can_capture`` — ``1`` o ``0``. Predeterminado ``1``. En unidades con habilidades ``attack``: cuando
``0``, haz clic derecho en los enemigos con ``capture_hp_threshold 100`` usa ataque/movimiento normal en su lugar
de la orden de captura predeterminada; La captura de contactos de IA también está deshabilitada. Ver Captura/ocupación predeterminada
orden arriba.

Sistema de caza (estilo Age of Empires)

Consulte ``../player/hunting.htm``. Resumen:

- Los trabajadores Retroceso/clic derecho sobre ``is_huntable`` atacan (el ataque normal hace daño); las muertes generan ``food_deposit`` (p. ej. ``food_carcass``) y completan la orden sin pitido falso ``order_impossible``.
- Atributos animales: ``is_huntable``, ``flee_on_hit``, ``herdable``, ``food_deposit``, ``food_deposit_qty``, ``no_number``.
- Generación de mapas: ``computer_only 0 0 neutral \<square\> \<count\> deer``; Los mapas aleatorios agregan vida silvestre cerca de los inicios.
- Voz: las unidades con ``is_huntable`` / ``herdable`` se anuncian como "ciervo, animal", no como "neutral, NPC". Ctrl+Shift+F4 a un jugador solo de vida silvestre dice "eres un animal". Los NPC de la historia (``quest_npc``, etc.) todavía dicen "neutral, NPC".
- Diplomacia: una ranura ``computer_only`` con solo vida silvestre (``deer`` / ``sheep`` / personalizada ``tiger``, etc.) no se une a la alianza ``"ai"`` y no se alia con jugadores, criaturas hostiles u otras manadas de vida silvestre; Las tragamonedas mixtas no cambian. Consulte ``../player/hunting.htm`` §3.1.
- Tecnología ``hunting_techniques``: recolección más rápida del huerto/carcasas.

Example animal::

    def deer
    class soldier
    is_huntable 1
    flee_on_hit 1
    food_deposit food_carcass
    food_deposit_qty 35
    no_number 1
    ai_mode guard


Herencia (desde 1.3.8.3)
------------------------

::

    is_a footman                    ; all attributes
    is_a footman(hp_max mdg)        ; selective
    is_a footman(apart hp_max)      ; exclusion inheritance (apart form)
    is_a footman(-hp_max)           ; exclusion inheritance (- prefix, same as apart)
    is_a footman(-hp_max -mdg)      ; exclude multiple attributes
    is_a footman(mdg) knight(hp_max) ; multiple parents


estilo
------

El estilo se define en "ui/style.txt" y en la versión localizada de "style.txt".

atajo
>>>>>>>

Órdenes simples, órdenes de construcción, órdenes de entrenamiento, órdenes usando una habilidad se pueden dar con un atajo, si se define un atajo.

Para definir un atajo, defina una propiedad de "atajo" seguida de la letra correspondiente. La letra debe estar en minúscula.

Si la orden es simple, el atajo debe estar definido por la orden (ej: patrulla).
Si la orden es compleja (entrenar, desarrollar, usar una habilidad), el atajo debe estar definido por la segunda parte de la orden.
Por ejemplo, define un atajo "m" para la habilidad de meteorito para que el mago tenga el atajo "m" para lanzar meteoritos.

introducción (desde 1.4.1.5)
>>>>>>>>>>>>>>>>>>>>>

Add a unit description below ``title``::

    def footman
    title 87
    intro 1001


El texto debe existir en ``tts.txt``.

Sistema de sonido de combate (desde 1.3.8.2; 1.4.4.6 renombrado matk/ratk a mdg/rdg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Replaces the old attack sounds::

    launch_mdg / launch_rdg
    mdg_hit / rdg_hit / mdg_hit_vs / rdg_hit_vs
    mdg_missed / rdg_missed
    mdg_dodge / rdg_dodge
    launch_charge_mdg / launch_charge_rdg
    charge_mdg_hit / charge_rdg_hit
    casting
    disappear
    weapon_switched
    death / falling / falling_delay / falling_on_<terrain>
    move / move_on_<terrain>


**Gritos de batalla (reproducción en capas desde 1.4.5.0; consulte :doc:`battle-shouts`)**

- ``shouts`` — conjunto de gritos de combate; definir en ``def walking_unit`` para que la infantería y los arqueros hereden

**Pasados del terreno y sonidos de caídas (desde 1.3.9.1; nombres de tipos de terreno desde 1.4.5.0)**

En ``def unit`` (o una unidad específica) en ``style.txt``:

- ``move`` — sonidos de pasos predeterminados
- ``move_on_<key>`` — pasos que dependen del terreno
- ``falling`` — sonido genérico de caída del cuerpo después de la muerte
- ``falling_delay <seconds>`` — espere después de ``death`` antes de ``falling``; omitir o ``0`` para reproducción inmediata
- ``falling_on_<key>`` — sonido de caída específico del terreno

Resolución de ``<key>`` (igual para ``move_on_`` y ``falling_on_``):

1. **Nombre del tipo de terreno**: la definición ``rules.txt`` / ``style.txt`` en el cuadrado de la unidad (por ejemplo, ``ocean``, ``plain``, ``mountain``). Con terreno de subcelda, se utiliza el tipo en las coordenadas de la unidad.
2. **``ground`` categoría**: el valor de ``ground`` en la definición de ``style.txt`` de ese terreno (por ejemplo, ``creek`` con ``ground water`` coincide con ``move_on_water`` / ``falling_on_water``).

El nombre del tipo de terreno se prueba antes de ``ground``. ``falling_on_ocean`` funciona en ``ocean`` incluso cuando esa definición no tiene línea ``ground``; en ``creek``, ``falling_on_creek`` gana a ``falling_on_water`` cuando ambos existen.

Example::

    def unit
    move 1052 1053
    move_on_ocean 1088 1348
    move_on_water 1088 1348
    move_on_grass 1053 1054
    falling 80051
    falling_delay 1
    falling_on_ocean fallwater
    falling_on_water splash


Solo las unidades **terrestres** usan terreno cuadrado para ``move_on_``; de lo contrario se utiliza ``move``. Los objetos inmóviles cercanos (edificios, árboles, etc.) también pueden suministrar ``move_on_<object type>`` o ``move_on_<ground>`` cuando están más cerca.

Las unidades de ráfaga disparan ``launch_mdg`` / ``launch_rdg`` una vez por disparo en un ``damage_seq``
estallar. Puede enumerar varios ID de sonido en la misma línea para que cada toma seleccione uno de ellos.

``mdg_hit_vs`` / ``rdg_hit_vs`` puede reproducir diferentes sonidos de golpe según el tipo de objetivo. el objetivo
El conjunto de coincidencias incluye el tipo de unidad, los tipos de unidad heredados y los tipos de ventajas/desventajas actuales.
active on the target. Example::

    def swordsman
    mdg_hit_vs b_absolute_defense iron_clang


Cuando ``swordsman`` alcanza un objetivo que actualmente tiene ``b_absolute_defense``, ``iron_clang``
se juega.

Desde 1.4.4.6, los documentos y los recursos incluidos utilizan los nombres ``mdg`` / ``rdg``. viejo
Las claves ``matk`` / ``ratk`` permanecen disponibles como respaldo de compatibilidad para modificaciones existentes.

Skills, buffs, and debuffs can also define trigger sounds::

    def skill_counter
    alert counter_alert
    ready counter_ready
    triggered counter_proc

    def b_absolute_defense
    triggered shield_on
    noise loop shield_hum


Juego de habilidades usado manualmente ``alert``. Si una regla de habilidad tiene ``ready \<seconds\>``, la habilidad
el estilo puede definir ``ready \<sound\>``; Los disparadores manuales y automáticos lo reproducen cuando comienza la preparación.
Habilidades activadas por ``active_trigger_skills``,
``passive_trigger_skills``, ``attack_trigger_skills`` o ``attack_replace_skills`` prefieren
``triggered`` y recurrir a ``alert`` cuando ``triggered`` no esté configurado. Mejoras y
las desventajas aplicadas a través de campos de activación reproducen su propio sonido ``triggered`` cuando se configuran.
Los sonidos de estado de mejora/desventaja persistentes deben escribirse explícitamente como ``noise loop \<sound\>`` o
``noise repeat \<interval\> \<sound...\>``; ``noise \<sound\>`` mantiene su comportamiento de análisis existente
y no se trata como un bucle automáticamente.

Menú y música del juego (desde 1.4.0.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

In ``def parameters``::

    menu_music <id>
    campaign_music <id>
    game_creation_music <id>
    server_lobby_music <id>
    game_music <id>
    battle_music <id>
    victory_sound <id>
    defeat_sound <id>
    main_menu_select_sound <id>
    main_menu_confirm_sound <id>


Faction music (since 1.4.0.3)::

    china_music china
    china_battle_music china_battle


Anulaciones de mapas: ``map_music``, ``map_battle_music``, ``map_victory_sound``, ``map_defeat_sound``.
Archivos de música: ``ui/music/\<id\>.mp3`` o ``mods/\<mod\>/ui/music/\<id\>.mp3``.
