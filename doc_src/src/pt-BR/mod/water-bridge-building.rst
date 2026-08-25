Construção de pontes sobre a água (vãos casa a casa)
======================================================

.. epigraph:: Para **autores de mod** e mapeadores: trabalhadores podem colocar **vãos de ponte transitáveis** uma casa aquática por vez em rios, lagos e oceanos. Complementa ``modding.htm`` (canteiros de obras) e ``building-land-terrain.htm`` (``big_bridge``, ``ford``).


----

Design
------

- **Uma casa do mapa = um vão de ponte**, não um único objeto "ponte inteira"
  cobrindo um rio largo.
- **A construção** usa um ``BuildingSite`` (andaime): unidades terrestres podem
  caminhar até aquela casa para construir, mas **andaimes incompletos não
  concedem passagem** (sem atalhos só de andaime atravessando a água).
- **Quando concluído**, a casa recebe o def ``bridge_terrain`` (padrão
  ``bridge_deck``), liga-se à terra adjacente / vãos concluídos e é
  **neutro** — todos os jogadores terrestres podem usar.

Exemplo integrado: ``wooden_bridge`` (requer ``lumbermill``, 5 ouro / 10
madeira).

Atributos de regra
------------------

Em um ``class building`` em ``rules.txt``:

.. list-table::
   :header-rows: 1

   * - Atributo
     - Significado
   * - ``is_buildable_on_water_only 1``
     - Apenas em casas de **água pura** (``is_water`` sem ``is_ground`` do
       mapa — rios, lagos, oceanos; não mapa ``ford`` / ``big_bridge``)
   * - ``bridge_terrain <name>``
     - Quando o edifício **termina**, aplica este ``class terrain`` à casa
       (por exemplo ``bridge_deck``)

Exemplo de terreno concluído::

    def bridge_deck
    class terrain
    is_water 1
    is_ground 1
    is_dynamic 0

Exemplo de vão construível::

    def wooden_bridge
    class building
    cost 5 10
    hp_max 400
    time_cost 60
    is_buildable_on_water_only 1
    bridge_terrain bridge_deck
    requirements lumbermill

Fluxo no jogo
-------------

1. Selecione um trabalhador; da **terra adjacente**, ordene ``wooden_bridge``
   em uma casa aquática.
2. Um ``BuildingSite`` é colocado; a célula torna-se temporariamente
   ``is_ground`` para o trabalhador poder path **até o andaime** (tiles de
   oceano com velocidade terrestre 0 recuperam velocidade normal enquanto
   andaime).
3. O trabalhador constrói naquela casa — mesmo TTS de qualquer canteiro:
   **"bridge span, under construction"** (título do tipo de edifício +
   título ``buildingsite``).
4. Na conclusão o edifício ``wooden_bridge`` permanece e ``bridge_terrain`` é
   aplicado; o tile torna-se transitável e conecta-se à margem / outros vãos
   concluídos.

Restrições de andaime
---------------------

- Apenas uma saída temporária para a **casa na margem onde a ordem foi dada**;
  **sem** passos diretos andaime-para-andaime.
- Sincronização de passagem roda apenas para **``bridge_terrain`` concluído**,
  não para andaimes vazios.
- Unidades ``BuildingSite`` aquáticas **não** afogam (``is_a_building``
  isento).
- Sons de martelo: defina ``noise_when_building`` no **trabalhador**; o estéreo toca no **canteiro**. Um canteiro com construtores não sobrepõe o próprio ciclo de martelo.

Voz e passos (``style.txt`` / ``tts.txt``)
------------------------------------------

Igual a outras construções: **sem** def de estilo "andaime" separado; canteiros
usam ``buildingsite`` ``title 107 128`` ("under construction").

| TTS ID | Texto (zh) | Uso |
|--------|-----------|-----|
| 153 | bridge (generic) | Tipo de saída ``bridge`` |
| 4348 | trestle | Terreno de mapa ``big_bridge`` |
| 5108 | wooden bridge span | Unidade ``wooden_bridge``, nome do canteiro |
| 5109 | bridge deck | Terreno concluído ``bridge_deck`` |

**Passos:** Durante andaime e após conclusão, o áudio usa o ``ground`` de
``bridge_terrain`` (padrão ``bridge_deck`` ``is_a big_bridge`` → ``ground
wood``).

**Voz da casa:** Enquanto constrói, a célula ainda reporta a água subjacente;
**"bridge deck"** só é anunciado após conclusão.

UI: Tab e passagens
-------------------

- ``wooden_bridge`` **não** é saída; **Tab** no centro de uma casa de deck
  pode selecionar o edifício do vão.
- Em casas de ponte/andaime, mapas com ``select_target no_exit`` (por exemplo
  td2) ainda alternam **saídas de passagem** via Tab.
- Alternância dedicada de passagem: ``select_passage`` quando mapeado.

Vãos personalizados (por exemplo ponte de ferro)
------------------------------------------------

Defina apenas o **edifício** + **terreno concluído** — sem estilo
``bridge_scaffold``:

**rules.txt** — ``iron_bridge`` com ``bridge_terrain iron_bridge_deck``;
**style.txt** — títulos e ``iron_bridge_deck is_a big_bridge`` (ou ``ground``
personalizado). Passos do andaime seguem ``bridge_terrain``; TTS do canteiro
permanece "iron bridge span, under construction".

vs. mapa ``big_bridge``
-----------------------

Vãos construídos pelo jogador usam ``bridge_deck`` quando prontos, deixam uma
entidade ``wooden_bridge`` destrutível e revertem para água intransitável ao
ser destruídos. ``big_bridge`` colocado no mapa é fixo no carregamento sem
entidade de edifício.

Implementação e testes
----------------------

``soundrts/world_build_rules.py``, ``worldorders/movement.py``,
``clientgameentity/properties.py``, ``audio.py``; testes em
``soundrts/tests/test_bridge_terrain.py``.

Veja também ``building-land-terrain.htm``, ``modding.htm``.
