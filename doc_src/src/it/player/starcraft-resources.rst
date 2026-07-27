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

Dopo il completamento:

1. La struttura prende la riserva del geyser (``is_an_extractor``) e produce automaticamente (``auto_production``)
2. Ogni ``production_time`` secondi aggiunge ``production_qty`` di vespene (predefinito 18 s / 8), scalando dalla riserva
3. I lavoratori raccolgono dall'edificio e trasportano ``extraction_qty`` per viaggio (predefinito 8)
4. Quando la riserva arriva a 0, la resa scende a ``depleted_production_qty`` (predefinito 2)
5. Il vespene viene depositato al Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Usa auto_production per il gas, non auto_cultivate in stile fattoria.

Schermata attributi
--------------------


Seleziona una struttura del gas e premi V per sentire requires deposit e la riserva rimanente.

Riferimento alle regole: ``mod/modding.rst`` (Economy and Deposits & gas).

Mappa di test: ``mods/starcraft/multi/sc_resources_test.txt``.
