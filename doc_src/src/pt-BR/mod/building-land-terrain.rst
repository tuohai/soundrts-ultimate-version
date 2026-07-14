Terreno configurável por casa e terreno de construção
===================================================

.. epigraph:: Para **autores de mod**: ``class terrain``, ``class building_land``, ``square_terrain`` orientado a objetos e paleta do editor de mapas. Complementa ``mapmaking.htm`` e ``modding.htm``.


----

Visão geral
-----------


Todo terreno é declarado em ``rules.txt`` como ``class terrain``; ``style.txt``
usa os mesmos nomes ``def`` para voz, ``ground`` e cores. ``move_on_<key>`` /
``falling_on_<key>`` das unidades correspondem a nomes de tipo de terreno ou
categorias ``ground`` — veja ``modding.htm`` (Sistema de som de combate).

**O motor não atribui mais terreno padrão a toda casa.** O terreno de uma casa
vem apenas de:

1. Mapa ``terrain <name> <squares>``
2. Objeto ``square_terrain`` (mata, cidades, prados etc.)
3. ``high_grounds`` / ``is_high_ground`` — voz extra de "terreno elevado"
   apenas, não um nome de terreno


Definições e posicionamento
---------------------------


**rules.txt:**

.. code-block:: text

   def plain
   class terrain
   is_dynamic 1

   def lake
   class terrain
   is_water 1
   is_dynamic 0

**Mapa:**

.. code-block:: text

   terrain plain a1
   terrain lake d1
   terrain hill c1
   high_grounds e1

- ``terrain lake d1`` **não** precisa de uma linha ``water d1`` separada
- A palavra-chave legada ``water`` ainda funciona
- Casas sem ``terrain``: ``type_name`` vazio, sem voz de terreno


Terreno de construção (``class building_land``)
-----------------------------------------------


``meadow``, ``build_site`` e tipos personalizados não são mais fixos no código.
Declare-os com **`class building_land`** em ``rules.txt``.

.. code-block:: text

   def meadow
   class building_land
   square_terrain meadows 40

   def build_site
   class building_land
   square_terrain build_sites 50

.. list-table::
   :header-rows: 1

   * - Mecanismo
     - Função
   * - ``default_building_land``
     - Padrão de rules quando o mapa omite ``building_land``
   * - Mapa ``building_land <name>``
     - Tipo padrão de terreno de construção para o mapa inteiro
   * - ``nb_<type>_by_square <N>``
     - Preenche automaticamente toda casa com N objetos desse tipo
       ``class building_land``
   * - ``nb_meadows_by_square <N>``
     - Legado; tipo inferido de ``building_land`` / mapa
   * - ``additional_building_land <name> <squares…>``
     - Coloca qualquer tipo declarado de terreno de construção nas casas
       listadas

Quando decolagem ou algumas melhorias restauram terreno de construção no
lugar, o motor usa **primeiro o tipo salvo quando o edifício foi colocado**;
só se faltar, recorre ao ``building_land`` do mapa ou a uma única palavra-chave
``nb_<type>_by_square``.

Veja ``mapmaking.htm`` (*Building_land*, *Nb_<type>_by_square*).


Atributos de ``class terrain``
--------------------------------


.. list-table::
   :header-rows: 1

   * - Atributo
     - Significado
   * - ``is_dynamic``
     - ``0`` estático; ``1`` pode ser substituído por terreno de objeto
   * - ``is_ground`` / ``is_air`` / ``is_water``
     - Flags de passabilidade terrestre / aérea / aquática
   * - ``is_high_ground``
     - Terreno elevado + voz
   * - ``passable_units``
     - Lista branca (herança ``is_a`` se aplica)
   * - ``blocks_path``
     - Bloqueia saídas para vizinhos (por exemplo mata densa, montanha)
   * - ``speed``
     - Opcional. ``speed <ground> <air>`` (por exemplo ``speed .5 1`` → 50%
       de velocidade terrestre). Aplicado quando o mapa define ``terrain
       <name>``; linhas ``speed`` por casa do mapa substituem

Mapa ``terrain <name>`` grava essas flags na casa. **Velocidade de
movimento** em uma casa (diferente de ``speed_on_terrain`` da unidade) resolve
como:

1. Mapa ``speed <ground> <air> <squares>`` — autoritativo em tempo de execução
2. ``speed`` em ``class terrain`` em ``rules.txt`` — quando o mapa tem
   ``terrain`` mas sem ``speed`` para aquela célula
3. Padrão ``(100, 100)``

``editor_palette.txt`` é apenas do editor: entradas da paleta sem ``speed``
herdam de ``rules.txt`` quando a paleta é carregada; salvar o mapa grava
linhas ``speed``. O jogo **não** lê a paleta em tempo de execução.

Exemplo de vau (água rasa, metade da velocidade terrestre):

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1

Quando ``is_ground 1`` está definido em terreno aquático (``ford``,
``big_bridge``), o pathfinding trata o tile como parte da **mesma região
terrestre** que a terra adjacente, para unidades poderem rotear por vaus sem
ficar presas na margem.

**Vãos construídos pelo jogador** (``wooden_bridge``,
``is_buildable_on_water_only``, ``bridge_terrain bridge_deck``): veja
`Construção de pontes sobre a água <water-bridge-building.htm>`_ (`zh
<../../zh/mod/water-bridge-building.htm>`_). Mapa ``big_bridge`` é terreno de
travessia fixo; vãos terminados do jogador usam ``bridge_deck``.

Modificadores de combate de unidades por terreno (desde 1.4.5.0)
----------------------------------------------------------------

Além de ``terrain_speed`` por casa, defs de unidade podem substituir
estatísticas de movimento e combate **pelo terreno em que a unidade está**. A
sintaxe corresponde a ``speed_on_terrain``:

.. code-block:: text

   <terrain_name> <modifier> [<terrain_name> <modifier> ...]

**Qual tile conta:** a casa atual ``type_name`` do **atacante/movedor** (ou
``type_name_at`` para terreno sub-célula).

**Empilhamento:** modificadores são **aditivos** (negativo = penalidade),
aplicados após ``mdg_vs`` / ``mdg_cd_vs`` etc. Valores usam as mesmas unidades
de ``mdg`` / ``mdg_cd`` (decimais permitidos; armazenados ×1000 internamente).

.. list-table::
   :header-rows: 1

   * - Propriedade
     - Efeito
   * - ``speed_on_terrain``
     - Velocidade de movimento nesse terreno (comportamento existente)
   * - ``mdg_on_terrain`` / ``rdg_on_terrain``
     - Bônus de dano corpo a corpo / à distância (após base + ``*_vs``)
   * - ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``
     - Bônus de cooldown de ataque (**positivo = ataques mais lentos**)
   * - ``charge_mdg_terrain`` / ``charge_rdg_terrain``
     - Bônus extra de dano de investida (após ``charge_mdg`` + ``charge_*_vs``)
   * - ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``
     - Bônus de cooldown de investida (positivo = cooldown de investida maior)

Acerto/esquiva no terreno do **alvo** (existente): ``mdg_cover_on_terrain``,
``rdg_cover_on_terrain``, ``mdg_dodge_on_terrain``, ``rdg_dodge_on_terrain``.

**Tela de atributos (Alt+V):** lista as linhas ``*_on_terrain`` / carga da unidade; as leituras ao vivo de dano / cooldown / velocidade incluem ``*_vs`` do terreno da casa atual mais ``*_on_terrain`` (``*_vs`` de terreno = percentual decimal; ``speed_on_terrain`` continua absoluto).

**Exemplo — cavaleiro enfraquecido em pântano:**

.. code-block:: text

   def knight
   speed 2.5
   mdg 6
   mdg_cd 1.5
   speed_on_terrain marsh 1.5 ford 1.5
   mdg_on_terrain marsh -2
   mdg_cd_on_terrain marsh 0.5

Em ``marsh``: velocidade 1.5, dano corpo a corpo 4, cooldown de ataque 2.0 s.

**Exemplo — unidade com investida:**

.. code-block:: text

   def raynor
   charge_mdg 4
   charge_mdg_cd 10
   charge_mdg_terrain marsh -1
   charge_mdg_cd_on_terrain marsh 2

Em ``marsh``: bônus de investida −1, cooldown de investida +2 s.

Implementação: ``soundrts/combat/damage_calculation.py``,
``soundrts/combat/attack_action.py``; testes:
``test_combat_terrain_modifiers.py``.

Tipos em ``res/rules.txt`` incluem ``plain``, ``lake``, ``marsh``,
``mountain``, ``forest``, ``dense_forest``, ``meadows``, ``build_sites``,
``town``, ``ford`` etc.


``square_terrain``: terreno orientado a objetos
-----------------------------------------------


**Mapa ``terrain`` pinta a camada base; ``square_terrain`` deixa objetos
crescer a camada superior** que pode aparecer e desaparecer em tempo de
execução.

Sintaxe em qualquer ``def``:

.. code-block:: text

   square_terrain <terrain_name> [priority] [min_count]

- ``priority`` (padrão 50): maior vence
- ``min_count`` (padrão 1): mínimo de objetos desse ``type_name`` na casa

Exemplo — floresta vs floresta densa:

.. code-block:: text

   def wood
   class deposit
   square_terrain forest 80
   square_terrain dense_forest 90 7

A cada tick, ``update_terrain()`` escolhe a entrada elegível de maior
prioridade e define o ``type_name`` da casa. Terreno de construção tem camada
de voz separada (``building_land_voice`` vs ``feature_voice``).

``terrain forest`` dinâmico no mapa gera objetos correspondentes via links
inversos ``square_terrain`` (veja doc em chinês para tabelas completas).


Camadas de voz
~~~~~~~~~~~~~~


``resolve_square_layers()`` pode empilhar:

- ``feature_voice`` — terreno vencedor de objeto (``forest``, ``town``, …)
- ``building_land_voice`` — ``meadows`` / ``build_sites`` quando diferente da
  feature
- ``high_ground_voice`` — marcador de terreno elevado


Paleta do editor de mapas
-------------------------


Console ``edit``; bindings em ``res/ui/editor_bindings.txt``. Lógica em
``soundrts/lib/editor_palette.py``.

- Terrenos estáticos (``lake``, ``mountain``, …): ``fixed_terrain``, salvos
  como ``terrain <name>``
- Terrenos dinâmicos (``forest``, ``meadows``, …): geram objetos, não
  bloqueados
- Nomes da paleta alinhados com ``res/ui/editor_palette.txt`` (``forest``, não
  legado ``woods``)


Testes
------


.. code-block:: bash

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py -q

Tabelas completas e texto em chinês: ``../../zh/mod/building-land-terrain.htm``.
