Bibliotecas de voz principal y secundaria (jugadores)
=====================================================


El juego usa dos bibliotecas de voz configurables por separado: principal y secundaria. Puedes activar o desactivar la secundaria; si está desactivada, la principal anuncia todo.


----


Funciones
---------


.. list-table::
   :header-rows: 1

   * - Biblioteca
     - Anuncia
   * - **Principal**
     - Menús, operaciones del jugador (selección, movimiento, modos…), todo fuera de partida
   * - **Secundaria**
     - Solo eventos pasivos en partida (bajas, descubrimientos, mensajes del mundo…)

Con la secundaria **activada**: las operaciones van por la principal y los eventos pasivos por la secundaria; pueden solaparse. Solo **Alt** interrumpe la secundaria.

Con la secundaria **desactivada**: la principal lo dice todo (modo de un solo canal); las operaciones interrumpen las líneas pasivas.


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
- **Shift+F9–F12**: biblioteca secundaria
- **Shift izquierdo+C** / **Shift derecho+C**: copiar última línea principal / secundaria
- **Shift+A**: añadir al portapapeles
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


----


Lectores de pantalla
--------------------


Si se detecta un lector dedicado (p. ej. NVDA), puede asumir la **principal** para no pelear con ella. La secundaria (si está activa) sigue usando el perfil secundario del juego.


----


Ver también
-----------


- `Notas de la versión <../../relnotes.htm>`_ — 1.4.5.4
- `Manual del juego <manual.htm>`_
