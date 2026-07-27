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

Após a conclusão:

1. A estrutura assume a reserva do geyser (``is_an_extractor``) e produz automaticamente (``auto_production``)
2. A cada ``production_time`` segundos adiciona ``production_qty`` de vespene (padrão 18 s / 8), debitando da reserva
3. Trabalhadores coletam do edifício e carregam ``extraction_qty`` por viagem (padrão 8)
4. Quando a reserva chega a 0, o rendimento cai para ``depleted_production_qty`` (padrão 2)
5. Vespene é armazenado no Nexus / Hatchery / Command Center (``storable_resource_types resource1 resource2``)

Use auto_production para gás, não auto_cultivate estilo fazenda.

Tela de atributos
-----------------


Selecione uma estrutura de gás e pressione V para ouvir requires deposit e a reserva restante.

Referência de regras: ``mod/modding.rst`` (Economy e Deposits & gas).

Mapa de teste: ``mods/starcraft/multi/sc_resources_test.txt``.
