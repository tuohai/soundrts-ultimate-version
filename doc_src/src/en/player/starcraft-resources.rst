StarCraft mod — minerals and vespene
=====================================


Mod: ``mods/starcraft`` (``mods = starcraft`` in ``SoundRTS.ini``).

Resources
----------


- Minerals (``resource1``): press Z
- Vespene (``resource2``): press X

Map syntax:

.. code-block:: text

   mineral_field 1500 a1
   geyser 1 e1


Gas structures
---------------


Assimilator / Extractor / Refinery must be built on a geyser (Tab the geyser, then build). Building on building land plays “cannot build there”.

After completion:

1. The structure auto-produces (``auto_production``): every ``production_time`` seconds it adds ``production_qty`` vespene into the building (default 18 s / 8 units)
2. Workers gather from the gas building (``can_gather assimilator``, etc.) and carry ``extraction_qty`` per trip (default 8)
3. Vespene is stored at the Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Use auto_production for gas, not farm-style auto_cultivate (farms only restart when storage is empty).

Attributes screen
------------------


Select a gas structure and press V to hear requires deposit (deposit type name, e.g. geyser). Production time and quantity use the existing production attribute entries.

Rule reference: ``mod/modding.rst`` (Economy and Deposits & gas).

Test map: ``mods/starcraft/multi/sc_resources_test.txt``.
