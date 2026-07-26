Internacionalización de mods
============================

Ajuste de idioma
----------------

Los jugadores pueden cambiar el idioma en menú principal → **Opciones** → **Idioma** (se guarda en ``language.txt`` del usuario). También se puede editar ese archivo, o usar ``cfg/language.txt`` de la instalación como respaldo si el archivo de usuario no existe (p. ej. ``zh``, ``fr``, ``es``). El juego escanea las carpetas ``ui-xx`` de los recursos cargados y elige la mejor coincidencia.

Estructura de directorios
-------------------------

Los mods tienen la misma estructura que el directorio ``res``; diseño habitual:

.. code-block:: text

   mods/mymod/
     rules.txt
     mod.txt                 # opcional
     ui/style.txt
     ui/tts.txt
     ui-zh/tts.txt
     ui-fr/tts.txt
     ui-es/tts.txt
     single/                 # opcional: campaña dentro del mod
       my campaign/
         campaign.txt
         ui/tts.txt
         ui-zh/tts.txt
         ui-es/tts.txt

Traducir texto del juego
------------------------

1. En ``ui/style.txt`` establece `title <ID numérico>` para unidades/edificios, etc.
2. En ``ui/tts.txt`` escribe ``7000 Pig Farm``.
3. En ``ui-es/tts.txt`` escribe ``7000 Granja de cerdos`` (el ID debe coincidir).

Las frases completas pueden usar el formato con igual: ``English phrase = Traducción española``.

Codificación de tts.txt (importante)
------------------------------------

Guarda siempre en UTF-8. Si no hay ``; coding:``, el motor lee por defecto como UTF-8; la primera línea puede llevar ``; coding: utf-8`` (opcional, para que algunos editores lo reconozcan).

Los archivos GBK heredados deben llevar ``; coding: gbk`` en la primera línea; si no, la decodificación fallará.

Causa habitual de caracteres corruptos: abrir ``tts.txt`` con la codificación incorrecta en VS Code/Cursor y guardarlo; el chino (u otros) se convierte en `` y se pierde para siempre. Al cargar, el motor detecta ``U+FFFD`` y avisa; si la decodificación falla, da error en lugar de sustituir en silencio.

Nombre mostrado del mod en el menú
----------------------------------

Opciones → Mods: la lista lee por defecto el nombre de la carpeta. Desde 1.4.2.4 puedes establecer en ``mod.txt``:

.. code-block:: text

   title 7100

y definir la traducción de ``7100`` en cada ``tts.txt`` de idioma. El mecanismo es el mismo que el ``title`` de ``campaign.txt`` de las campañas.

Si no quieres modificar el mod en sí, puedes añadir en ``res/ui-es/tts.txt`` o en un mod de traducción:

.. code-block:: text

   nombre_carpeta = Nombre mostrado en español

Limitaciones
------------

- ``rules.txt`` y ``ai.txt`` son un solo archivo; no se dividen por idioma.
- ``ui-xx/style.txt`` en subdirectorios de mapa/campaña puede no cargarse; ``ui-xx/tts.txt`` sí.
- El menú de paquetes de sonido sigue usando el nombre de la carpeta.

Ejemplos
--------

- `mods/orc/`: ``ui-xx/tts.txt`` en siete idiomas
- `mods/prismalab/ui-fr/`: interfaz y teclas rápidas en francés

Más detalles en la sección de internacionalización de mods de ``mod/modding.rst``.
