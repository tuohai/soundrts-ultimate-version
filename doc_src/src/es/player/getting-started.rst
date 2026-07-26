Guía del jugador de SoundRTS — Empieza aquí
===========================================

Una ruta de lectura progresiva: lo básico → RTS central → funciones modernas → multijugador → mods.

Autores de mods: `Primeros pasos para desarrolladores <../mod/getting-started.htm>`_.

----

¿Qué es SoundRTS?
-----------------

Un juego de estrategia en tiempo real por audio inspirado en Warcraft y StarCraft, pensado para jugadores ciegos y para cualquiera a quien le guste comandar de oído. Dos vistas:

.. list-table::
   :header-rows: 1

   * - Modo
     - Entrada
     - Ideal para
   * - Modo mapa (por defecto)
     - al iniciar
     - Macro: seleccionar unidades, dar órdenes, consultar recursos
   * - Modo primera persona (RPG)
     - Alt+Espacio / Ctrl+Espacio
     - Micro: caminar, apuntar habilidades

----

Nivel 1 — Arranque en diez minutos
----------------------------------

Objetivo: seleccionar un campesino, minar oro, construir una granja y una casa.

.. list-table::
   :header-rows: 1

   * - Acción
     - Tecla
   * - Siguiente unidad amiga
     - Q
   * - Siguiente edificio
     - W
   * - Siguiente / anterior comando
     - A / Shift+A
   * - Siguiente / anterior objetivo
     - Tab / Shift+Tab
   * - Confirmar
     - Intro
   * - Comando por defecto sobre el objetivo
     - Retroceso

Recursos: Z oro · X madera · Shift+Z comida · C población.

Movimiento: flechas, RePág/AvPág entre casillas interesantes, Espacio para seguir la selección.

Lista completa de comandos: `manual.rst <../../../player/manual.rst>`_ §3, o menú F10 en el juego.

----

Nivel 2 — Bucle RTS central
---------------------------

- Economía: campesinos → casas (límite de población) y granjas (comida) → edificios → ejército
- Punto de reunión: selecciona el ayuntamiento → Tab a la mina de oro → Retroceso
- Grupos: Shift+6–9 para guardar, 6–9 para recuperar
- Exploración: el modo defensa huye de enemigos más fuertes
- Movimiento/ataque forzado: Ctrl+Retroceso
- Zoom: F8 (subcasillas para colocación precisa)

Consejos: `unit-default-behavior <unit-default-behavior.htm>`_

----

Nivel 3 — Funciones modernas (1.4+)
-----------------------------------

.. list-table::
   :header-rows: 1

   * - Tema
     - Doc
   * - Atributos / inventario / equipo
     - [inventory.htm](inventory.htm)
   * - Logros, rangos, arsenal
     - [achievements.htm](achievements.htm)
   * - Puntuación al final (S–E)
     - [score-and-grades.htm](score-and-grades.htm)
   * - Cartas previas a la misión
     - [loadout-cards.htm](loadout-cards.htm)
   * - Campañas y cooperativo
     - [campaign-menu.htm](campaign-menu.htm)
   * - Mapas aleatorios (semilla / código para compartir)
     - [random-map-play.htm](random-map-play.htm)
   * - Teclas rápidas por capas
     - [layered-hotkeys.htm](layered-hotkeys.htm)
   * - Llevar objetos a una casilla
     - [brought-items.htm](brought-items.htm)

----

Nivel 4 — Multijugador
----------------------

Menú principal → multijugador → elige servidor → crea/únete a sala → F7 chat. Equipos fijos antes de empezar; alianzas dinámicas F12 / F4 / Ctrl+F4 cuando se permita. Puerto por defecto 2500.

----

Nivel 5 — Mods y docs temáticos
-------------------------------

Activa en ``user/SoundRTS.ini``: ``mods = soundpack,starcraft`` o ``--mods=...``

.. list-table::
   :header-rows: 1

   * - Tema
     - Doc
   * - Caza / pastoreo
     - [hunting.htm](hunting.htm)
   * - Ataques en ráfaga
     - [burst-attacks.htm](burst-attacks.htm)
   * - Recursos StarCraft
     - [starcraft-resources.htm](starcraft-resources.htm)
   * - Complementos Terran
     - [starcraft-terran.htm](starcraft-terran.htm)
   * - Creep Zerg
     - [starcraft-zerg-creep.htm](starcraft-zerg-creep.htm)
   * - Mapas estilo Héroes / Civ 5
     - [homm-civ5-play.htm](homm-civ5-play.htm)

Actualizaciones automáticas
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Al iniciar, el juego comprueba por defecto si hay un Release más nuevo en GitHub. Intro actualiza, Esc cancela.
Active o desactive en Opciones → **Comprobar actualizaciones al iniciar el juego**. El paquete Windows puede descargar e instalar; desde el código fuente solo se abre la página de descarga. Véase el manual y las `Notas de la versión <../../relnotes.htm>`_ (1.4.6.3).

Notas de la versión: `Notas de la versión <../../relnotes.htm>`_ — historial completo de versiones.

----

Siguientes pasos
----------------

- Completa el tutorial → docs del Nivel 3 según necesites
- Modding: `Primeros pasos para desarrolladores <../mod/getting-started.htm>`_
- Índice: `help-index.htm <../help-index.htm>`_
