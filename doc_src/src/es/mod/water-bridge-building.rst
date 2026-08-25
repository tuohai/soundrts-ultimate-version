Construir puentes sobre el agua (tramos casilla a casilla)
==========================================================

.. epigraph:: Para **autores de mods** y cartógrafos: los trabajadores pueden colocar **tramos de puente transitables** una casilla de agua cada vez en ríos, lagos y océanos. Complementa ``modding.htm`` (obras de construcción) y ``building-land-terrain.htm`` (``big_bridge``, ``ford``).

----

Diseño
------

- **Una casilla del mapa = un tramo de puente**, no un solo objeto «puente entero» que cubra un río ancho.
- La **construcción** usa un ``BuildingSite`` (andamiaje): las unidades terrestres pueden caminar a esa casilla para construir, pero **los andamiajes sin terminar no conceden paso** (sin atajos solo-andamiaje a través del agua).
- **Al completarse**, la casilla recibe la def ``bridge_terrain`` (por defecto ``bridge_deck``), se enlaza con tierra adyacente / tramos terminados, y es **neutral** — todos los jugadores terrestres pueden usarla.

Ejemplo integrado: ``wooden_bridge`` (requiere ``lumbermill``, 5 oro / 10 madera).

Atributos de reglas
-------------------

En un ``class building`` de ``rules.txt``:

.. list-table::
   :header-rows: 1

   * - Atributo
     - Significado
   * - ``is_buildable_on_water_only 1``
     - Solo en casillas de **agua pura** (``is_water`` sin ``is_ground`` del mapa — ríos, lagos, océanos; no ``ford`` / ``big_bridge`` del mapa)
   * - ``bridge_terrain <name>``
     - Cuando el edificio **termina**, aplicar este ``class terrain`` a la casilla (p. ej. ``bridge_deck``)

Ejemplo de terreno terminado::

    def bridge_deck
    class terrain
    is_water 1
    is_ground 1
    is_dynamic 0

Ejemplo de tramo construible::

    def wooden_bridge
    class building
    cost 5 10
    hp_max 400
    time_cost 60
    is_buildable_on_water_only 1
    bridge_terrain bridge_deck
    requirements lumbermill

Flujo en el juego
-----------------

1. Selecciona un trabajador; desde **tierra adyacente**, ordena ``wooden_bridge`` en una casilla de agua.
2. Se coloca un ``BuildingSite``; la celda se vuelve temporalmente ``is_ground`` para que el trabajador pueda ir **al andamiaje** (las baldosas oceánicas con velocidad terrestre 0 recuperan velocidad normal mientras hay andamiaje).
3. El trabajador construye en esa casilla — mismo TTS que cualquier obra: **«tramo de puente, en construcción»** (título del tipo de edificio + título ``buildingsite``).
4. Al completarse permanece el edificio ``wooden_bridge`` y se aplica ``bridge_terrain``; la baldosa se vuelve transitable y conecta con la orilla / otros tramos terminados.

Restricciones del andamiaje
---------------------------

- Solo una salida temporal a la **casilla de orilla donde se dio la orden**; **sin** pasos directos andamiaje-a-andamiaje.
- La sincronización de paso solo corre para **``bridge_terrain`` terminado**, no para andamiajes desnudos.
- Las unidades ``BuildingSite`` de agua **no** se ahogan (exentas por ``is_a_building``).
- Los sonidos de martillo se definen en el **trabajador** (``noise_when_building``); el estéreo suena en la **obra**. Una obra con constructores no superpone su propio bucle de martillo.

Voz y pasos (``style.txt`` / ``tts.txt``)
-----------------------------------------

Igual que otras construcciones: **sin** def de estilo «andamiaje» separada; las obras usan ``buildingsite`` ``title 107 128`` («en construcción»).

| ID TTS | Texto (zh) | Uso |
|----

----

|----

----

---|----

-|
| 153 | puente (genérico) | Tipo de salida ``bridge`` |
| 4348 | caballete | Terreno de mapa ``big_bridge`` |
| 5108 | tramo de puente de madera | Unidad ``wooden_bridge``, nombre de obra |
| 5109 | tablero de puente | Terreno terminado ``bridge_deck`` |

**Pasos:** Durante el andamiaje y tras completarse, el audio usa el ``ground`` de ``bridge_terrain`` (por defecto ``bridge_deck`` ``is_a big_bridge`` → ``ground wood``).

**Voz de casilla:** Mientras se construye, la celda sigue informando el agua subyacente; **«tablero de puente»** solo se anuncia tras completarse.

IU: Tab y pasajes
-----------------

- ``wooden_bridge`` **no** es una salida; **Tab** en el centro de una casilla de tablero puede seleccionar el edificio del tramo.
- En casillas de puente/andamiaje, los mapas con ``select_target no_exit`` (p. ej. td2) siguen ciclando **salidas de pasaje** con Tab.
- Ciclo dedicado de pasajes: ``select_passage`` cuando esté enlazado.

Tramos personalizados (p. ej. puente de hierro)
-----------------------------------------------

Define solo el **edificio** + **terreno terminado** — sin estilo ``bridge_scaffold``:

**rules.txt** — ``iron_bridge`` con ``bridge_terrain iron_bridge_deck``; **style.txt** — títulos y ``iron_bridge_deck is_a big_bridge`` (o ``ground`` personalizado). Los pasos del andamiaje siguen ``bridge_terrain``; el TTS de la obra sigue siendo «tramo de puente de hierro, en construcción».

frente a ``big_bridge`` del mapa
--------------------------------

Los tramos construidos por el jugador usan ``bridge_deck`` al terminar, dejan una entidad ``wooden_bridge`` destructible, y vuelven a agua intransitable al destruirse. El ``big_bridge`` colocado en el mapa es fijo al cargar, sin entidad de edificio.

Implementación y pruebas
------------------------

``soundrts/world_build_rules.py``, ``worldorders/movement.py``, ``clientgameentity/properties.py``, ``audio.py``; pruebas en ``soundrts/tests/test_bridge_terrain.py``.

Véase también ``building-land-terrain.htm``, ``modding.htm``.
