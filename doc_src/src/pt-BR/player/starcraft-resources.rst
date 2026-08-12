Mod StarCraft — minerais e vespene
==================================


Mod: ``mods/starcraft`` (``mods = starcraft`` em ``SoundRTS.ini``).

Recursos
--------


- Minerais (``resource1``): pressione Z
- Vespene (``resource2``): pressione X

Sintaxe de mapa:

.. code-block:: text

   mineral_field 1500 a1
   geyser 1 e1


``geyser 1`` é um local de construção; a reserva padrão vem de ``deposit_volume`` (5000). Também pode escrever ``geyser 5000 e1``.

Estruturas de gás
-----------------


Assimilator / Extractor / Refinery devem ser construídos sobre um geyser (Tab no geyser, depois construir). Construir em terreno edificável toca “não é possível construir ali”.

Após a conclusão (estilo StarCraft 1):

1. A estrutura assume a reserva do geyser (``is_an_extractor``); trabalhadores coletam dela (**sem** buffer ``auto_production``)
2. Cada viagem rende ``extraction_qty`` (padrão **8**) e debita ``source_qty``
3. Quando a reserva chega a 0, o rendimento cai para ``depleted_production_qty`` (padrão **2**)
4. Vespene é armazenado no Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Número de trabalhadores (``gather_slots``)
------------------------------------------


Padrão ``gather_slots 3``:

- No máximo **3** trabalhadores extraem ao mesmo tempo
- Os demais esperam até haver vaga
- Enviar 8 ainda produz gás (rodízio), mas o ritmo ≈ 3, não 8×

Dica: coloque **3** trabalhadores em cada gás.

Notas Protoss / Zerg
--------------------


- Assimilator: só geyser (**sem** psi)
- Extractor: só geyser (**sem** creep)
- Pylons podem warp em qualquer lugar; Photon Cannons precisam de psi e não atacam sem energia

Tela de atributos
-----------------


Selecione uma estrutura de gás e pressione V para ouvir requires deposit e a reserva restante.

Referência de regras: ``mod/modding.rst`` (Economy e Deposits & gas).

Mapa de teste: ``mods/starcraft/multi/sc_resources_test.txt``.
