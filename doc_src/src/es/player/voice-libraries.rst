Bibliotecas de voz principal y secundaria (jugadores)
=====================================================


El juego usa dos bibliotecas de voz configurables por separado: principal y secundaria. Puedes activar o desactivar la secundaria; si está desactivada, la principal anuncia todo.

**Consejo:** conviene usar un **lector de pantalla** como voz principal. Si el lector está activo, asume el rol de la biblioteca principal y no hace falta gastar ``F9``–``F12`` en «ajustar la principal». Las teclas de este juego están muy saturadas: **ahorre atajos siempre que pueda**. La secundaria (campo de batalla) sigue ajustándose con ``Shift+F9``–``F12``.


----


Funciones
---------


.. list-table::
   :header-rows: 1

   * - Biblioteca
     - Anuncia
   * - **Principal**
     - Menús, operaciones del jugador; todo fuera de partida; y en partida el **feedback económico/producción** (unidad/edificio listo, investigación, mejora de era, recursos, menú cambiado…)
   * - **Secundaria**
     - Eventos pasivos de **campo de batalla** (enemigos, bajas, scout, alertas de combate, mensajes del mundo…)

Con la secundaria **activada**: principal y secundaria pueden solaparse.

- **Alt izquierdo**: omite/para la biblioteca **principal**
- **Alt derecho**: omite/para la biblioteca **secundaria**

Con la secundaria **desactivada**: la principal lo dice todo; **Alt izquierdo y Alt derecho omiten la línea actual** (no hay secundaria que filtrar).


----


Dónde configurar
----------------


1. Menú principal → **Opciones** → **Ajustes de biblioteca de voz**
2. Opciones:
   - **Activar o desactivar la voz secundaria** (o **F3** en cualquier menú; no en partida)
   - Editores **principal** / **secundaria**: volumen, tono, velocidad, voz, tarjeta de sonido
   - **Abrir carpeta de voces**: abre ``user/voices``


----


Parámetros y teclas
-------------------


En el editor:

- Arriba/Abajo: parámetro (volumen / tono / velocidad / voz / dispositivo)
- Izquierda/Derecha: ajustar
- Intro o Esc: volver

En partida (y menús):

- **F9–F12**: biblioteca principal
- **Shift+F9–F12**: biblioteca secundaria (cualquier Shift)
- **Shift derecho+C**: copiar última línea secundaria; **Shift derecho+B**: añadir secundaria al portapapeles
- **Shift izquierdo+C / Shift izquierdo+B** (principal): **comentados** por defecto en ``res/ui/global_bindings.txt`` para reducir conflictos; quite el ``;`` inicial de esas líneas para activarlos
- **F3 en menús**: activar/desactivar secundaria (no en partida)


----


Añadir voces
------------


Usa **Abrir carpeta de voces** (normalmente ``user/voices``).

Voces SAPI de Windows
~~~~~~~~~~~~~~~~~~~~~

1. Instala y registra una voz SAPI5 en Windows.
2. En el juego, recorre el parámetro **voz** en principal o secundaria.
3. Algunas voces solo de 32 bits se usan vía ``tools/sapi32``.

Carpetas de paquete (nombres amigables)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crea una subcarpeta en ``user/voices`` con ``voice.ini``::

    [voice]
    title=Mi nombre
    sapi=Microsoft Huihui Desktop
    rate=0

- ``title``: nombre en menús
- ``sapi``: debe coincidir con una voz SAPI registrada
- ``rate``: opcional, aprox. -10…10

Los paquetes **no** instalan un motor TTS; solo ponen alias a una voz SAPI existente.

Nuance / voces Apple (opcional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Si hay datos Nuance en ``user/voices/nuance``, aparecen en la lista. Consulta las notas de esa carpeta.

Principal y secundaria pueden usar **solo SAPI**; Nuance es opcional y requiere el ayudante Java 32 bits en ``tools/nuance_ve``.


----


Alertas direccionales en partida (pan estéreo)
----------------------------------------------


Algunos anuncios pasivos **ligados a una casilla** (enemigo detectado, bajas, exploración, alertas de combate) se panoramizan izquierda/derecha respecto a tu casilla de vista actual (misma lógica que los SFX del minimapa).

Con auriculares: en vista cenital hacia el norte, el este suena más a la derecha y el oeste a la izquierda.

**El pan se actualiza si cambias de casilla a mitad del anuncio** (no hace falta esperar al siguiente mensaje).


----


Lectores de pantalla
--------------------


Si se detecta un lector dedicado (p. ej. NVDA), puede asumir la **principal** para no pelear con ella. La secundaria (si está activa) sigue usando el perfil secundario del juego.


----


Ver también
-----------


- `Notas de la versión <../../relnotes.htm>`_ — 1.4.5.4 (doble biblioteca), 1.4.5.5 (pan, deberes, Alt izq./der.)
- `Manual del juego <manual.htm>`_
