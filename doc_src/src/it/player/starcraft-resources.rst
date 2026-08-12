Mod StarCraft — minerali e vespene
===================================


Mod: ``mods/starcraft`` (``mods = starcraft`` in ``SoundRTS.ini``).

Risorse
--------


- Minerali (``resource1``): premi Z
- Vespene (``resource2``): premi X

Sintassi della mappa:

.. code-block:: text

   mineral_field 1500 a1
   geyser 1 e1


``geyser 1`` è un sito di costruzione; la riserva predefinita viene da ``deposit_volume`` (5000). Puoi anche scrivere ``geyser 5000 e1``.

Strutture del gas
------------------


Assimilator / Extractor / Refinery devono essere costruiti su un geyser (Tab sul geyser, poi costruisci). Costruire su terreno edificabile riproduce «non puoi costruire lì».

Dopo il completamento (stile StarCraft 1):

1. La struttura prende la riserva del geyser (``is_an_extractor``); i lavoratori raccolgono da essa (**niente** buffer ``auto_production``)
2. Ogni viaggio rende ``extraction_qty`` (predefinito **8**) e scala ``source_qty``
3. Quando la riserva arriva a 0, la resa scende a ``depleted_production_qty`` (predefinito **2**)
4. Il vespene viene depositato al Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Numero di lavoratori (``gather_slots``)
---------------------------------------


Predefinito ``gather_slots 3``:

- Al massimo **3** lavoratori estraggono insieme
- Gli altri aspettano finché non c’è posto
- Mandarne 8 produce ancora gas (a turno), ma il ritmo ≈ 3, non 8×

Consiglio: metti **3** lavoratori su ogni gas.

Note Protoss / Zerg
-------------------


- Assimilator: solo geyser (**senza** psi)
- Extractor: solo geyser (**senza** creep)
- I Pylon possono warp ovunque; i Photon Cannon richiedono psi e non attaccano senza energia

Schermata attributi
--------------------


Seleziona una struttura del gas e premi V per sentire requires deposit e la riserva rimanente.

Riferimento alle regole: ``mod/modding.rst`` (Economy and Deposits & gas).

Mappa di test: ``mods/starcraft/multi/sc_resources_test.txt``.
