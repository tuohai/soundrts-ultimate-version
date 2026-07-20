Tutorial de criação de IAs
==========================

.. contents::

1. Introdução
-------------

Este tutorial explica como escrever IAs de computador.
Você edita ``ai.txt`` (scripts) e, para mods, ``rules.txt`` (mapeamentos de
dificuldade por facção). Esses arquivos ficam na pasta ``res`` do pacote
SoundRTS; um mod, campanha ou mapa também pode incluir suas próprias cópias.

Uma IA é um script pequeno: uma lista de comandos que o computador executa de
cima para baixo, em loop infinito. Não é necessário conhecimento de
programação.

2. ``ai.txt``: scripts de IA
----------------------------

Em ``ai.txt``, cada IA começa com ``def \<name\>`` seguido de seus comandos::

    def tang_empire_easy
    research 1
    workers 12
    get 9 villager 5 footman
    attack
    goto -1

Observações:

- Os nomes podem ser qualquer identificador, por exemplo ``tang_empire_easy``
  ou ``my_mod_hard``. Nomes personalizados não aparecem no menu de convite;
  os jogadores veem o nível de dificuldade mapeado em ``rules.txt`` (próxima
  seção).
- Se o ``ai.txt`` de um mod contiver ``clear``, todo script de IA carregado
  até então (incluindo os cinco níveis base de ``res/ai.txt``) é descartado.
  Isso não altera quantos botões de convite aparecem; afeta apenas quais
  entradas ``def`` permanecem carregadas. A maioria dos mods não precisa de
  ``clear``.
- Linhas ``def`` com o mesmo nome em uma camada posterior substituem as
  anteriores.
- Se não existir script para um nível solicitado em tempo de execução,
  ``get_ai`` recorre ao script definido mais próximo (incluindo a cadeia de
  aliases legados ``easy`` / ``aggressive``).

3. Menu de convite e mapeamentos em ``rules.txt``
-------------------------------------------------

Os menus de convite de computador no modo um jogador e multijogador são
controlados pelo ``rules.txt`` do mod atual, e não por uma lista fixa de cinco
botões. Não é necessário linhas vazias de placeholder como ``def beginner``
em ``ai.txt``.

Sem mod
~~~~~~~

O menu sempre oferece os cinco níveis padrão:

- ``beginner`` -- Beginner (初级)
- ``intermediate`` -- Intermediate (中级)
- ``advanced`` -- Advanced (高级)
- ``expert`` -- Expert (专家)
- ``nightmare`` -- Nightmare (噩梦)

Com um mod carregado
~~~~~~~~~~~~~~~~~~~~

O motor varre os blocos de facção em ``rules.txt`` em busca de linhas de
mapeamento de dificuldade. Cada nível aparece no menu quando pelo menos uma
facção mapeia esse nível para um nome de script que existe como ``def`` em
``ai.txt``.

Recomendado (mods novos) -- nomes de nível padrão dentro de cada bloco de
facção::

    def tang_empire
    class race
    townhall county_government
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

Isso produz Convite computador iniciante / intermediário / avançado (tantos
botões quantos você mapear). Se o jogador escolher "beginner" com a facção
Tang, o script ``tang_empire_easy`` é executado.

Mods legados -- ainda usando ``easy`` / ``aggressive``::

    def orc
    class race
    ...
    easy orc_defensive
    aggressive orc_aggressive

O menu mostra Convite computador quieto / agressivo (rótulos defensivo /
agressivo na interface em chinês). O anfitrião ainda convida o nível ``easy``
ou ``aggressive``; ``rules.txt`` resolve o script real por facção.

Resumo
~~~~~~

- ``ai.txt`` contém os scripts; ``rules.txt`` mapeia níveis para scripts por
  facção.
- Facções diferentes podem mapear o mesmo nível para scripts diferentes; o
  menu lista apenas nomes de nível, não nomes de script específicos da
  facção.
- Se tanto ``beginner`` quanto ``easy`` estiverem mapeados, apenas ``beginner``
  é listado.
- Scripts internos como ``timers`` nunca aparecem no menu de convite.
- Anfitriões multijogador enviam ``invite_ai \<tier\>`` (por exemplo
  ``invite_ai beginner``). Comandos legados ``invite_beginner`` etc. ainda
  funcionam.

4. Configurações (escritas uma vez, perto do topo de um "def")
---------------------------------------------------------------

Elas ajustam o comportamento geral da IA. Coloque-as perto do topo de um
``def`` para que rodem antes do loop. Uma dificuldade maior geralmente
significa economia maior, pesquisa ligada, mais bases e mais disposição para
atacar.

- ``constant_attacks 0/1`` -- quando ``1``, a IA continua atacando e
  explorando o mapa em vez de ficar na defesa em casa.
- ``research 0/1`` -- quando ``1``, a IA pesquisa melhorias de
  arma/armadura/habilidade sempre que puder pagar.
- ``workers \<n\>`` -- o número de trabalhadores (camponeses) que a IA tenta
  manter. Mais trabalhadores significa economia mais forte. Padrão: ``10``.
- ``expand \<n\>`` -- o número total de prefeituras (bases) a manter. A base
  inicial conta, então ``expand 2`` faz a IA construir uma base extra.
  Padrão: ``0`` (sem expansão extra).
- ``attack_ratio \<percent\>`` -- quão forte o exército da IA deve ser, em
  comparação com o inimigo na área alvo, antes de atacar. ``180`` (o padrão)
  significa "atacar apenas com 80% de vantagem" (cauteloso). Valores menores
  fazem a IA se comprometer mais cedo; abaixo de ``100`` ela ataca mesmo
  estando ligeiramente mais fraca (pressão implacável).
- ``counter_skill \<0-100\>`` -- quão bem as unidades da IA usam bônus de
  contador ``mdg_vs`` / ``rdg_vs`` ao escolher alvos e enviar ataques.
  ``0`` ignora contadores (prioridade pura de ``menace``). ``100`` sempre
  escolhe o melhor par de contador, incluindo tipos herdados via ``is_a`` (por
  exemplo, ``mdg_vs cavalry`` também conta camelos com ``is_a cavalry``).
  Valores intermediários misturam bônus de contador e ``menace``. Padrão se
  omitido: ``100``.

  O ``res/ai.txt`` vanilla define: beginner ``25``, intermediate ``50``,
  advanced ``75``, expert ``90``, nightmare ``100``.
- ``starting_resources \<amounts...\>`` -- recursos bônus adicionados além do
  início do mapa (ou da facção). Mesma ordem e mesmas unidades que
  ``starting_resources`` do mapa (por exemplo ``10 10`` = 10 ouro e 10 madeira;
  armazenado internamente como ``× 1000`` como inícios de mapa). Omitido = sem
  bônus.
- ``starting_units \<unit\>...`` -- unidades ou edifícios bônus gerados na
  casa inicial da IA após o início normal. Usa a mesma sintaxe plana de
  ``starting_units`` do mapa (coloque uma contagem antes do nome do tipo para
  gerar vários: ``5 footman 2 archer``). Respeita nomes ``equivalent`` da
  facção. **Consomem população** (igual às unidades iniciais do mapa; aumente
  o teto com ``starting_population`` se precisar). Omitido = sem unidades bônus.
- ``starting_population \<n\>`` -- limite de população bônus adicionado além
  de casas e outras unidades ``population_provided``. Inteiro simples (não
  ``× 1000``). ``available_population`` ainda é limitado pelo
  ``global_population_limit`` do mapa.
- ``train_time \<pct\>`` -- porcentagem da duração normal de treinamento
  (``100`` = normal, ``50`` = metade do tempo). Só ``train`` e morph-as-train.
  Omitido = ``100``.
- ``research_time \<pct\>`` -- porcentagem da duração normal de pesquisa /
  avanço (``100`` = normal, ``80`` = 20% mais rápido). Só ``research`` /
  ``advance``. Omitido = ``100``.
- ``build_time \<pct\>`` -- porcentagem da duração normal de construção
  (``100`` = normal, ``50`` = o dobro de rápido). Afeta o progresso no
  canteiro. Omitido = ``100``.
- ``gather_time \<pct\>`` -- porcentagem da duração normal de coleta
  (``100`` = normal, ``50`` = o dobro de rápido). Só o tempo de coleta dos
  trabalhadores do computador (``Worker.get_gather_time``). **Nota:** é o
  multiplicador de dificuldade em ``ai.txt``, não o campo ``gather_time`` de
  trabalhadores em ``rules.txt``. Omitido = ``100``.
- ``unit_hp \<pct\>`` -- porcentagem do HP normal de todas as unidades deste
  computador (``100`` = normal, ``120`` = +20% HP). Depois do
  ``enemy_hp_factor`` coop. Omitido = ``100``.

  Essas linhas são aplicadas uma vez no início da partida; não fazem parte do
  loop do script (diferente de ``get`` / ``attack``).

  Bônus do ``res/ai.txt`` vanilla (além de todo início de mapa):

  - intermediate: ``starting_resources 50 50``, ``starting_population 10``
  - advanced: ``100 100`` + ``2 footman 2 archer``, ``starting_population 20``,
    ``train_time 50``, ``research_time 80``, ``build_time 50``, ``gather_time 50``
  - expert: ``200 200`` + ``5 footman 4 archer 2 knight``, ``starting_population 40``,
    ``train_time 50``, ``research_time 70``, ``build_time 50``, ``gather_time 50``,
    ``unit_hp 120``
  - nightmare: ``400 400`` + ``8 footman 6 archer 4 knight``, ``starting_population 60``,
    ``train_time 40``, ``research_time 60``, ``build_time 40``, ``gather_time 40``,
    ``unit_hp 140``
- ``watchdog \<seconds\>`` -- rede de segurança: se a IA ficar presa na mesma
  linha por esse tempo, avança para a próxima linha. ``0`` desativa.

Seleção por contador (``counter_skill``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quando ``counter_skill`` está acima de ``0``, unidades do computador preferem
inimigos que elas counteram de acordo com bônus de dano em ``rules.txt``:

- Um cavaleiro com ``mdg_vs archer 12`` foca arqueiros em vez de unidades com
  ``menace`` maior.
- Um arqueiro com ``rdg_vs footman 7`` foca soldados.
- Nomes de tipo em ``mdg_vs`` / ``rdg_vs`` correspondem ao ``type_name`` do
  alvo ou a qualquer nome em sua cadeia de herança ``is_a``.

Com ``counter_skill`` baixo, alvos com ``menace`` alto ainda podem vencer; em
``100``, o melhor par de contador vence, a menos que haja apenas um inimigo ao
alcance.

Desde 1.4.5.2, o ``menace`` padrão é uma **pontuação de combate multidimensional**
(dano, cover/acerto, cooldown, ready/wind-up, HP, armadura, esquiva, alcance, velocidade),
opcionalmente sobrescrito com ``menace_mult`` / ``menace_vs`` — veja ``modding.rst``
*Menace automática / prioridade de alvo*.

Isso afeta micro (qual inimigo cada unidade ataca) e macro (qual área
empurrar e quais unidades enviar primeiro), desde que o exército ainda atenda
``attack_ratio``.

5. Comandos de ação
-------------------

- ``get \<n\> \<unit\>...`` -- recruta ou constrói até a IA possuir ``\<n\>`` de
  cada unidade/edifício listado. Você pode listar vários pares de uma vez. Veja
  ``rules.txt`` para os nomes exatos dos tipos de unidade.
  Exemplo: ``get 10 footman 20 archer 10 knight``
- ``attack`` -- a partir daqui, ataca sempre que estiver forte o suficiente
  (também liga ``constant_attacks``).
- ``wait \<seconds\>`` -- permanece nesta linha por ``\<seconds\>`` antes de
  continuar. Útil para ritmo (uma IA fácil pode ``wait`` entre ondas).
  Observação: um ``watchdog`` diferente de zero ainda pode tirar a IA da linha
  mais cedo.

6. Controle de fluxo
--------------------

- ``label \<name\>`` -- marca uma posição para a qual você pode pular.
- ``goto \<name\>`` -- pula para um rótulo. ``goto`` também aceita um
  deslocamento relativo de linha como ``goto -1`` (volta uma linha).
- ``goto_random \<name1\> \<name2\> ...`` -- pula para um dos rótulos
  listados, escolhido aleatoriamente. Ótimo para tornar a IA imprevisível.

7. Exemplo de mod (três níveis, scripts por facção)
----------------------------------------------------

Trecho de ``ai.txt``::

    def tang_empire_easy
    constant_attacks 0
    get 9 villager 5 footman
    attack
    goto -1

    def tang_empire_hard
    constant_attacks 1
    get 9 villager 10 footman
    attack
    goto -1

Trecho de ``rules.txt`` para a facção Tang::

    def tang_empire
    class race
    peasant villagers
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

O menu mostra três níveis; Tang + "intermediate" executa ``tang_empire_hard``.

8. Exemplo completo (um nível vanilla)
--------------------------------------

::

    def advanced

    counter_skill 75
    watchdog 480
    constant_attacks 1
    research 1
    workers 18
    expand 2          ; segunda base para economia mais forte
    attack_ratio 150  ; avança com vantagem menor

    label open
    get 9 peasant 6 footman 4 archer
    attack
    goto_random knights mixed

    label knights
    get 9 peasant 16 knight 10 archer 3 catapult
    attack
    goto open

    label mixed
    get 9 peasant 20 archer 12 knight 5 priest 4 catapult
    attack
    goto open

Tudo após um ``;`` na linha é comentário e é ignorado.
