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


Assimilator / Extractor / Refinery must be built on a **geyser** (Tab the geyser, then build). Building on building land plays “cannot build there”.

After completion (SC1 Brood War–style numbers):

1. The structure takes over the geyser reserve (``is_an_extractor``); workers gather from it (**not** building ``auto_production`` filling a buffer)
2. Each worker trip yields ``extraction_qty`` (default **8**) and debits ``source_qty``
3. When the reserve hits 0, yield drops to ``depleted_production_qty`` (default **2**), like a depleted geyser
4. Vespene is stored at the Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Worker count (``gather_slots``)
--------------------------------


Gas buildings default to ``gather_slots 3``:

- At most **3** workers extract at once (StarCraft gas saturation)
- Extra workers wait nearby until a slot frees
- Sending 8 workers still produces gas (they rotate), but throughput ≈ 3 workers, not 8×

Practical tip: put **3** workers on each gas structure.

Protoss / Zerg notes
--------------------


- Assimilator: geyser only (**no** psi required)
- Extractor: geyser only (**no** creep required)
- Pylons may warp **anywhere** (they create psi); Photon Cannons need psi and do not attack while unpowered

Attributes screen
------------------


Select a gas structure and press V to hear requires deposit and remaining reserve.

See ``mod/modding.rst`` (Economy and Deposits & gas). Test map: ``mods/starcraft/multi/sc_resources_test.txt``.
