Mod StarCraft — minerales y vespeno
===================================

Mod: ``mods/starcraft`` (``mods = starcraft`` en ``SoundRTS.ini``).

Recursos
--------

- Minerales (``resource1``): pulsa Z
- Vespeno (``resource2``): pulsa X

Sintaxis de mapa:

.. code-block:: text

   mineral_field 1500 a1
   geyser 1 e1

``geyser 1`` es un sitio de construcción; la reserva por defecto viene de ``deposit_volume`` (5000). También puedes escribir ``geyser 5000 e1``.

Estructuras de gas
------------------

Assimilator / Extractor / Refinery deben construirse sobre un geyser (Tab en el geyser, luego construir). Construir en suelo edificable reproduce «no se puede construir ahí».

Tras completarse:

1. La estructura toma la reserva del geyser (``is_an_extractor``) y produce automáticamente (``auto_production``)
2. Cada ``production_time`` segundos añade ``production_qty`` de vespeno (por defecto 18 s / 8), descontando de la reserva
3. Los trabajadores recolectan del edificio y transportan ``extraction_qty`` por viaje (por defecto 8)
4. Cuando la reserva llega a 0, el rendimiento baja a ``depleted_production_qty`` (por defecto 2)
5. El vespeno se almacena en el Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Usa auto_production para el gas, no auto_cultivate al estilo de granjas.

Pantalla de atributos
---------------------

Selecciona una estructura de gas y pulsa V para oír que requiere depósito y la reserva restante.

Referencia de reglas: ``mod/modding.rst`` (Economy and Deposits & gas).

Mapa de prueba: ``mods/starcraft/multi/sc_resources_test.txt``.
