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

Tras completarse (estilo StarCraft 1):

1. La estructura toma la reserva del geyser (``is_an_extractor``); los trabajadores recolectan de ella (**no** hay búfer ``auto_production``)
2. Cada viaje rinde ``extraction_qty`` (por defecto **8**) y descuenta ``source_qty``
3. Cuando la reserva llega a 0, el rendimiento baja a ``depleted_production_qty`` (por defecto **2**)
4. El vespeno se almacena en el Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Número de trabajadores (``gather_slots``)
-----------------------------------------

Por defecto ``gather_slots 3``:

- Como máximo **3** trabajadores extraen a la vez
- Los demás esperan hasta que haya hueco
- Enviar 8 sigue produciendo gas (rotan), pero el ritmo ≈ 3, no 8×

Consejo: pon **3** trabajadores en cada gas.

Notas Protoss / Zerg
--------------------

- Assimilator: solo geyser (**sin** psi)
- Extractor: solo geyser (**sin** creep)
- Los Pylon pueden warpear en cualquier sitio; los Photon Cannon necesitan psi y no atacan sin energía

Pantalla de atributos
---------------------

Selecciona una estructura de gas y pulsa V para oír que requiere depósito y la reserva restante.

Referencia de reglas: ``mod/modding.rst`` (Economy and Deposits & gas).

Mapa de prueba: ``mods/starcraft/multi/sc_resources_test.txt``.
