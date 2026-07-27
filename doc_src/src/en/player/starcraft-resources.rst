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


``geyser 1`` is a build site; the default reserve comes from ``deposit_volume`` in rules (5000). You can also write ``geyser 5000 e1``.

Gas structures
---------------


Assimilator / Extractor / Refinery must be built on a geyser (Tab the geyser, then build). Building on building land plays “cannot build there”.

After completion:

1. The structure takes over the geyser reserve (``is_an_extractor``) and auto-produces (``auto_production``)
2. Every ``production_time`` seconds it adds ``production_qty`` vespene into the building (default 18 s / 8), deducted from the reserve
3. Workers gather from the gas building and carry ``extraction_qty`` per trip (default 8)
4. When the reserve hits 0, yield drops to ``depleted_production_qty`` (default 2), like a depleted geyser in StarCraft
5. Vespene is stored at the Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Use auto_production for gas, not farm-style auto_cultivate (farms only restart when storage is empty).

Attributes screen
------------------


Select a gas structure and press V to hear requires deposit and remaining reserve. Production time and quantity use the existing production attribute entries.

See ``mod/modding.rst`` (Economy and Deposits & gas). Test map: ``mods/starcraft/multi/sc_resources_test.txt``.
