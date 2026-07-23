Manual de criação de mapas
==========================

.. contents::

Introdução
----------

A melhor forma de começar provavelmente é criar um mapa multijogador e testá-lo contra o computador.

Mapas multijogador
------------------

Onde armazenar um novo mapa multijogador
"""""""""""""""""""""""""""""""""""""""""

Se você tiver permissão de escrita na pasta onde o SoundRTS (ou o SoundRTS test) está instalado,
então você pode guardar seu primeiro mapa multijogador na pasta "multi".

Se você não tiver permissão de escrita na pasta de arquivos de programa porque trabalha em modo não administrador, pode guardar o arquivo do mapa em que está trabalhando na pasta "multi"
em "C:\\Documents and Settings\\Seu Login\\Application Data\\SoundRTS". Essa pasta é criada na primeira vez que você inicia o SoundRTS, a menos que já exista uma pasta "user" próxima ao soundrts.exe.
Outra solução é instalar o SoundRTS em uma pasta onde você tenha permissão de escrita e trabalhar na pasta mencionada no parágrafo anterior.

Como editar um mapa
"""""""""""""""""""

Abra o arquivo com um editor de texto.
Escreva em minúsculas, mesmo que o uso de maiúsculas/minúsculas provavelmente seja ignorado de qualquer forma.

Como testar um mapa
"""""""""""""""""""

Para testar um mapa, inicie o SoundRTS e vá ao menu de um jogador. Você pode jogar contra o computador em mapas multijogador.
O mapa é recarregado toda vez que você inicia uma partida, então não é necessário reiniciar o SoundRTS para testar as modificações.
Uma combinação de teclas útil é Control Shift F2: se você for o único humano no mapa, poderá examinar o mapa inteiro (sem neblina de guerra).

Como localizar e corrigir um erro
"""""""""""""""""""""""""""""""""

Se, ao iniciar o mapa, você receber uma mensagem de "erro de mapa" e voltar ao menu, então às vezes é possível encontrar informações adicionais (mas enigmáticas) em "client.log" ou em "server.log", geralmente na pasta "user/tmp".

Se ainda assim você não entender onde está o erro, fique à vontade para entrar em contato comigo, diretamente ou pela lista soundRTSChat.

Comentários
"""""""""""

As linhas que começam com ponto e vírgula são comentários. Comentários são ignorados em tempo de execução.
Tudo o que vier depois de um ponto e vírgula até o final da linha também é um comentário.

Propriedades básicas
""""""""""""""""""""

Title
'''''

"title 4018 5000" significa: "o título do mapa é o som 4018 seguido do som 5000".

Objective
'''''''''

"objective 145 88" significa: "o objetivo do mapa é o som 145 seguido do som 88".

Nb_players_min e nb_players_max
'''''''''''''''''''''''''''''''

"nb_players_min 2" significa: "são necessários 2 jogadores para iniciar a partida."
"nb_players_max 4" significa: "4 jogadores neste mapa é o máximo."

Global_food_limit
'''''''''''''''''

Novo na versão beta 9e.

Atualizado na versão beta 10 o: este limite de comida não é mais dividido entre os jogadores.

"global_food_limit 200" significa: "nenhum jogador pode ter mais que 200 de comida, mesmo que construa mais fazendas."

Definindo o terreno
"""""""""""""""""""

Coordenadas (a partir de 1.4.1.8)
'''''''''''''''''''''''''''''''''

O sistema de coordenadas usa ``x,y`` (por exemplo, ``1,1`` em vez do antigo ``a1``). No modo zoom, as coordenadas
ainda são anunciadas com letras. A notação antiga é aceita e convertida::

    west_east_paths 1,3 2,3
    south_north_paths 1,1 2,1 3,1

Use a notação x,y para definir mais de 26 colunas.

Square_width
''''''''''''

"square_width 12" significa: "a largura do quadrado é 12 metros".
Você não deveria modificar esse parâmetro, pois objetos podem ficar inaudíveis se estiverem muito distantes.

Desde 1.4.5.8, ``square_width`` também é a capacidade **por aliança** de ``space`` das unidades em cada camada
ar/terra/água (mesmas unidades: ``space 1`` → no máximo 12 por lado se ``square_width`` for 12; contagem por aliança desde 1.4.5.9). Veja
``mod/modding.rst`` (Ocupação do quadrado).

Nb_lines e nb_columns
'''''''''''''''''''''

"nb_lines 7" significa: "a grade tem 7 linhas".
"nb_columns 7" significa: "a grade tem 7 colunas".
A notação por letras limita as colunas a 26 (``z``); use coordenadas x,y para mais colunas. Não há
um limite rígido para linhas, mas o desempenho define um limite prático.
Aviso: nb_rows está obsoleto e tem o mesmo significado de nb_columns.

West_east_paths e south_north_paths
'''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" significa: "adiciona um caminho de a1 a b1, de c1 a d1, de d1 a e1 e de f1 a g1".
Você só precisa informar o quadrado mais a oeste do caminho.
"south_north_paths a1 a3 a4 a6" significa: "adiciona um caminho de a1 a a2, de a3 a a4, de a4 a a5 e de a6 a a7".
Você só precisa informar o quadrado mais ao sul do caminho.

West_east_bridges e south_north_bridges
'''''''''''''''''''''''''''''''''''''''

Pontes funcionam exatamente como caminhos.

Caso geral: west_east e south_north
'''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" significa: "adiciona uma saída com o estilo 'road' de a1 a b1, de c1 a d1, de d1 a e1"

'road' deve estar definido em style.txt

Nota: "west_east_paths" é o mesmo que "west_east path"

Nota: "south_north_bridges" é o mesmo que "south_north bridge"

Minas de ouro, florestas e outros depósitos de recursos
'''''''''''''''''''''''''''''''''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" significa: "adiciona minas de ouro com 150 de ouro em a2, b7, g6 e f1".

"wood 150 a2 b7 g6 f1" significa: "adiciona florestas com 150 de madeira em a2, b7, g6 e f1".

"goldmine" e "wood" são definidos em rules.txt como depósitos de recursos ("class deposit").

As antigas palavras-chave no plural ("goldmines" e "woods") ainda funcionam.

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" significa: "preenche automaticamente o mapa com 2 prados em cada quadrado".

Additional_meadows
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" significa: "adiciona 1 prado nos quadrados a2, b7, g6 e f1".
"additional_meadows a2 a2 g6" significa: "adiciona 2 prados em a2 e 1 prado em g6".

Remove_meadows
''''''''''''''

remove_meadows faz o oposto de additional_meadows.

Building_land (tipo de slot de construção padrão)
'''''''''''''''''''''''''''''''''''''''''''''''''

Os mapas podem escolher qual tipo de objeto o ``nb_meadows_by_square`` preenche automaticamente::

    building_land build_site
    nb_meadows_by_square 2

- ``building_land meadow`` (padrão): preenche automaticamente slots de **meadow** (prado).
- ``building_land build_site``: preenche automaticamente slots de **build_site** (neutro quanto ao tema, por exemplo mods de espaço).

``additional_meadows`` e ``additional_build_sites`` ainda colocam esses tipos explicitamente;
``remove_meadows`` só remove objetos ``meadow``.

Nb_<type>_by_square (tipos de building_land das regras)
'''''''''''''''''''''''''''''''''''''''''''''''''''''''

Padrão de palavra-chave de mapa: ``nb_<type>_by_square <count>``, onde ``<type>`` é o nome ``def``
de qualquer objeto com ``class building_land`` em ``rules.txt``::

    nb_build_site_by_square 1
    nb_meadow_by_square 2
    nb_volcanic_rock_by_square 1

- Preenche **cada quadrado** com essa quantidade de objetos do tipo dado.
- Os tipos vêm das regras (mods podem adicionar ``def volcanic_rock`` + ``class building_land`` e usar
  ``nb_volcanic_rock_by_square``; nomes Unicode como ``nb_火山岩石_by_square`` funcionam se definidos nas regras).
- Independente da linha ``building_land`` do mapa.
- Pode coexistir com ``nb_meadows_by_square``; geralmente usa-se um ou outro.

O legado ``nb_meadows_by_square`` permanece: o nome é histórico; o tipo real é controlado
por ``building_land`` (padrão ``meadow``), e não pela análise de ``meadow`` na palavra-chave.

Se o mapa omite ``building_land`` e usa apenas uma palavra-chave ``nb_<type>_by_square``, esse tipo se torna ``world.building_land`` para a partida.

Quando a decolagem ou algumas melhorias restauram o terreno de construção no local, o motor usa **o tipo salvo quando o edifício foi colocado** primeiro; só se faltar, ele volta ao padrão do mapa acima.

Additional_build_sites
''''''''''''''''''''''

::

    additional_build_sites a2 b7

adiciona um **build_site** por quadrado listado (independente de ``building_land``).

Veja ``building-land-terrain.htm`` para terreno, terreno de construção e exemplos relacionados.

High_grounds
''''''''''''

Novo no SoundRTS 1.2 alpha 9.

"high_grounds a2 b7" significa: "a2 e b7 terão uma altitude maior"

Terreno de subcélula (a partir de 1.4.4.8)
'''''''''''''''''''''''''''''''''''''''''

O terreno também pode ser sobrescrito dentro de um quadrado. Adicione ``/x,y`` depois da coordenada do
quadrado, onde ``x`` e ``y`` são coordenadas baseadas em 1 dentro do quadrado::

    high_grounds a1/1,1 a1/1,2
    terrain mountain a1/2,2
    ground a1/2,2
    no_air a1/2,2

A grade de subcélulas é controlada por ``subcell_precision``. O padrão é ``3``,
portanto ``a1/1,1`` significa a subcélula noroeste de uma subdivisão 3x3. O intervalo aceito
é de 2 a 20::

    subcell_precision 20
    high_grounds a1/10,10 a1/10,11
    terrain mountain a1/1,1 a1/2,2 a1/3,3

Os seguintes comandos de terreno aceitam coordenadas de subcélula: ``terrain``,
``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` e ``no_air``.
Subcélulas não mencionadas herdam o terreno do quadrado pai.

No modo zoom, o navegador de mapa anuncia o terreno da subcélula atual. Se
``a1/1,1`` for terreno elevado e o restante de ``a1`` for terreno baixo, navegar por essa
subcélula anunciará planalto, enquanto as outras subcélulas não.

Square_name (a partir de 1.4.1.8)
'''''''''''''''''''''''''''''''''

Nomeie quadrados ou regiões::

    square_name normandy 2,2 verdun 20,23
    square_name normandy 2,2 2,3 3,3

A partir de 1.4.1.9, até três níveis hierárquicos são suportados (província, cidade, distrito). O TTS
anuncia os nomes ao entrar a partir de outra região; níveis internos são omitidos durante a navegação
dentro da mesma região. Traduza os nomes em ``tts.txt``::

    normandy = Normandy

Música e sons do mapa (a partir de 1.4.0.2)
'''''''''''''''''''''''''''''''''''''''''''

No arquivo do mapa::

    map_music <id>
    map_battle_music <id>
    map_victory_sound <id>
    map_defeat_sound <id>


Definindo os recursos iniciais dos jogadores
"""""""""""""""""""""""""""""""""""""""""""""

Nota (a partir de 1.4.1.8): unidades e recursos iniciais de facção também podem ser definidos em
``rules.txt``. Definições do mapa têm prioridade quando ambos são definidos.

Caso 1: mesmos recursos para todos
'''''''''''''''''''''''''''''''''

Use os comandos a seguir em combinação:

starting_resources
..................

"starting_resources 10 10" significa: "cada jogador começa com 10 de ouro e 10 de madeira."

starting_units
..............

"starting_units townhall farm peasant" significa: "cada jogador começa com 1 townhall, 1 farm e 1 peasant."

"starting_units townhall 2 farm peasant" significa: "cada jogador começa com 1 townhall, 2 farms e 1 peasant."

starting_population
...................

"starting_population 60" significa: "cada jogador recebe 60 de limite de população extra além do
que seus edifícios iniciais fornecem." Esse é um número inteiro simples (não multiplicado como os
recursos). Linhas ``player`` / ``computer_only`` por jogador também podem incluir
``population 60`` entre os tokens de unidade para aquele slot apenas. ``available_population``
continua limitado por ``global_population_limit``.

A partir do SoundRTS 1.1, starting_units também pode conter:

- melhorias e pesquisas: "starting_units u_teleportation" significa: "cada jogador já tem teletransporte pesquisado."
- unidades, edifícios, habilidades, melhorias/pesquisas proibidos (não aparecerão no menu):

  - "starting_units -u_teleportation" significa: "cada jogador não pode pesquisar teletransporte."
  - "starting_units -a_teleportation" significa: "cada jogador não pode usar teletransporte."

starting_squares
................

"starting_squares a2 b7 g6 f1" significa: "os quadrados iniciais dos jogadores são a2, b7, g6 e f1."

As unidades e edifícios iniciais serão criados nesses quadrados.

``starting_squares`` apenas fixa quais quadrados cada slot de spawn usa; por padrão não fixa qual humano que entra recebe qual slot (veja random_starts_ e player_start_).

.. _random_starts:

random_starts
.............

``random_starts 1`` (padrão): os slots de spawn são embaralhados entre os clientes humanos no início da partida. As posições das unidades dentro de cada slot permanecem as mesmas, mas a atribuição dos slots é aleatória.

``random_starts 0``: os slots são atribuídos em ordem aos clientes 0, 1, 2…; o primeiro a entrar sempre recebe o primeiro slot.

.. _player_start:

player_start (a partir de 1.4.2.8)
..................................

Fixa o jogador N (baseado em 1, igual a ``trigger playerN``) em um slot/quadrado. Jogadores fixos nunca participam do embaralhamento de ``random_starts``; os outros ainda seguem ``random_starts``.

Forma simples — altera apenas o quadrado, mantém os recursos e unidades existentes daquele slot::

    starting_squares a1 c1 e1
    starting_units townhall peasant
    player_start 1 b1

Forma completa — equivalente a fixar uma linha ``player`` completa no jogador N::

    player_start 1 5 10 a1 townhall peasant

Coordenadas e aliases também são suportados::

    player_start 1 2,3
    player_start 2 5,1

.. _spawn_semantics:

Semântica de spawn: player vs player_start
'''''''''''''''''''''''''''''''''''''''''

Ambos podem colocar unidades/edifícios em quadrados específicos (por exemplo, ``a1``), mas não significam o mesmo tipo de "spawn fixo":

- ``player`` / ``starting_squares``: definem os slots de spawn e seus conteúdos. As coordenadas dos quadrados são fixas, mas com ``random_starts 1`` qual humano recebe qual slot é embaralhado.
- ``player_start``: fixa o jogador N ao slot N (e pode alterar o quadrado daquele slot), independentemente de ``random_starts``.

Padrões comuns:

Configurações diferentes por jogador, e o jogador 1 deve sempre começar no canto inferior esquerdo:

    random_starts 1
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant
    player_start 1 a1
    player_start 2 h1

Apenas linhas player, fixadas por ordem de entrada (sem necessidade de player_start):

    random_starts 0
    player 5 10 a1 townhall peasant
    player 5 10 h1 townhall peasant

Configuração inicial compartilhada, apenas alguns jogadores fixados:

    starting_squares a1 c1 e1 g1
    starting_units townhall peasant
    player_start 1 a1
    player_start 3 e1

Armadilhas comuns:

- Em ``player 5 10 …``, os dois primeiros números são quantidades de recursos (ouro/madeira), não um índice de jogador nem coordenadas.
- Para fixar "qual participante recebe qual canto", use ``player_start`` ou ``random_starts 0``; ``starting_squares`` / ``player`` sozinhos não são suficientes.

Caso 2: recursos diferentes dependendo do jogador
'''''''''''''''''''''''''''''''''''''''''''''''

player
......

O comando "player" define um ponto de partida que pode ser usado por um jogador humano ou por uma IA de computador (em partidas multijogador).

Esse comando pode ser repetido várias vezes em um mapa multijogador.

"player 5 10 -townhall a1 townhall peasant c1 footman"
significa: "um jogador começará com 5 de ouro, 10 de madeira, não poderá construir um town hall, terá um townhall e um peasant em A1, e um footman em C1."

Cada linha ``player`` acrescenta um slot de spawn na ordem do mapa; ``a1``, ``c1``, etc. são coordenadas de quadrado. Para fixar um slot ao jogador N, use player_start_ ou defina random_starts 0 (veja spawn_semantics_ acima).


Lista de tipos
'''''''''''''

Aqui estão alguns nomes corretos para os tipos usados em starting_units_, player_ e computer_only_.
Para uma lista completa, examine o arquivo rules.txt: o nome está logo após o comando "def".

- unidades: peasant footman archer knight catapult dragon mage priest necromancer
- edifícios: farm barracks lumbermill blacksmith townhall stables workshop dragonslair magestower
- habilidades: a_teleportation
- melhoria/pesquisa: u_teleportation melee_weapon


Adicionando monstros
""""""""""""""""""""

Adicionar um ponto de partida computer_only
'''''''''''''''''''''''''''''''''''''''''''

.. _computer_only:

O comando "computer_only" define um ponto de partida que sempre será controlado por uma IA de computador. Essa IA será hostil a qualquer outro jogador ou IA.

Esse comando pode ser repetido várias vezes, mas cuidado: muitas IAs podem tornar o jogo lento.
Então use uma IA se essas unidades não devem lutar entre si (vários dragões espalhados pelo mapa, por exemplo).

computer_only 0 0 a3 dragon b1 dragon
significa: "adiciona uma IA de computador com 0 de ouro, 0 de madeira, um dragão em A3 e um dragão em B1."

Computadores neutros (a partir de 1.4.2.8)
..........................................

Adicione a palavra-chave ``neutral`` para que a IA não ataque a menos que seja atacada primeiro::

    computer_only 0 0 neutral a3 peasant b1 footman

Sem ``neutral``, o computador é hostil a todos.

Unidades de jogador em modo ofensivo, defensivo ou de perseguição não atacarão automaticamente esses
neutros e não fugirão deles em modo defensivo; somente um ataque forçado (imperativo) inicia o combate.

Slots somente de vida selvagem (a partir de 1.4.3.7)
.....................................................

Se uma linha ``computer_only`` contiver apenas animais com ``is_huntable`` / ``herdable`` (por exemplo, ``deer``, ``sheep``, ``tiger`` personalizado), esse slot não entra na aliança padrão ``"ai"`` e não se alia com outros rebanhos, jogadores ou creep hostil. Cada linha ``computer_only`` é um ponto de caça independente.

Se a mesma linha misturar animais e footmen, o slot inteiro permanece uma IA normal. Veja ``../player/hunting.htm`` §3.1.


Adicionar gatilhos para fazer os monstros se moverem
'''''''''''''''''''''''''''''''''''''''''''''''''''

Importante: adicionar os gatilhos padrão de multijogador
........................................................

Se um mapa multijogador definir pelo menos um gatilho, os gatilhos padrão de multijogador são ignorados. O objetivo é permitir condições de vitória personalizadas.

Para manter as condições de vitória padrão, os gatilhos a seguir devem ser adicionados explicitamente ao mapa (ou a partida não terminará automaticamente)::

    trigger players (no_enemy_player_left) (victory)
    trigger players (no_building_left) (defeat)
    trigger computers (no_unit_left) (defeat)

Nota: o terceiro gatilho não é realmente necessário.

Condições de vitória e derrota (a partir de 1.4.0.1)
....................................................

Condições adicionais de gatilho::

    trigger all (unit_lost knight) (defeat)
    trigger player1 (unit_lost a1 3 footman) (defeat)
    trigger player1 (building_lost 1 townhall) (defeat)
    trigger player1 (key_unit_killed a1 3 footman) (defeat)
    trigger all (key_unit_killed hero) (defeat)
    trigger all (key_units_killed 5 knight) (defeat)
    trigger all (units_lost 3 knight) (defeat)
    trigger all (building_lost townhall) (defeat)
    trigger all (buildings_lost 1 townhall 2 barracks) (defeat)
    trigger players (killed_target dragon) (victory)
    trigger players (killed_target dragon enemy) (victory)
    trigger player1 (has_killed 5 footman enemy) (objective_complete 1)
    trigger player1 (has_killed 1 footman 3 knight enemy) (objective_complete 2)

``killed_target`` e ``has_killed`` aceitam ``enemy`` ou ``ally`` opcionais para contar apenas
aquelas unidades.

Seletores de índice de unidade (a partir de 1.4.3.1, demo: The Legend of Raynor capítulo 28) — mesma
sintaxe ``\<square\> \<index\> \<type\>`` de ``transfer_units``; identifica a N-ésima unidade daquele
tipo gerada no quadrado (estável após movimento)::

    trigger player1 (killed_target c3 3 demo_marker_footman enemy) (objective_complete 1)
    trigger player1 (killed_target c3 1 demo_marker_footman enemy) (do (cut_scene 7606) (defeat))
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Índice de ``killed_target``: `` (killed_target \<square\> \<index\> \<type\> [enemy|ally])``.
Índice de ``npc_has_item``: `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``.
Índice de ``unit_lost`` / ``building_lost`` / ``key_unit_killed``: `` (\<square\> \<index\> \<type\>)`` — apenas aquela unidade/edifício gerado (por exemplo, proteger o town hall inicial).
Não é o mesmo que ``has_killed 3 footman`` (contagem total). O ``cut_scene`` de cada objetivo deve
descrever apenas aquele objetivo. Veja ``campaign/unit-index.htm``; exemplos
``res/single/The Legend of Raynor/28.txt``, ``1.txt``.

Gatilhos de missão de item (a partir de 1.4.3.1)
...............................................

has_item — o jogador pegou um item de missão (verifica os inventários de todas as unidades vivas)::

    trigger player1 (has_item lost_amulet) (objective_complete 1)
    trigger player1 (has_item health_potion 2) (objective_complete 2)

O item deve ser ``class item`` com ``consume_on_pickup`` não definido como 1 (padrão 0), para que
permaneça no inventário após ser pego. Coloque itens no mapa como unidades::

    lost_amulet c3
    health_potion 2 a2

Diferenças entre condições relacionadas:

- ``has``: contagens de unidades do jogador (``self.units``)
- ``has_item``: itens nos inventários das unidades do jogador (encontrados/pegos em qualquer lugar)
- ``npc_has_item``: um NPC recebeu um item (inventário ou ``received_items``); forma de índice ``\<square\> \<index\> \<type\> \<item\>`` (capítulo 28)
- ``find``: o objeto existe no chão em um quadrado (quadrado antes do tipo, por exemplo, ``c3 mana_potion``); o item normalmente precisa ser largado
- ``has_brought_item``: uma unidade do jogador carregando um item chegou a um quadrado (o item permanece no inventário)
- ``remove_item``: ação de gatilho que exclui um item dos inventários do jogador (entrega de história)
- ``remove_ground_item``: ação de gatilho que exclui itens no chão em um quadrado
- ``do``: ação de gatilho que executa várias sub-ações em ordem
- ``and``: condição de gatilho que é verdadeira apenas quando todas as sub-condições são verdadeiras

has_brought_item — levar um item de missão a um quadrado (o inventário conta; não é necessário largar)::

    trigger player1 (has_brought_item c3 mana_potion) (objective_complete 1)

Sintaxe: ``(has_brought_item \<square\> \<item_type_name\> [count])``

remove_item — remover e destruir itens dos inventários do jogador (entrega de história)::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintaxe: ``(remove_item \<item_type_name\> [square] [count])``

Fluxo típico: ``has_brought_item`` → ``cut_scene`` → ``remove_item`` → ``objective_complete``.
Exemplo: The Legend of Raynor capítulo 18.

do — executar várias ações de gatilho em ordem::

    trigger player1 (has_brought_item c3 mana_potion)
        (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))

Sintaxe: ``(do \<action1\> \<action2\> ...)``

``if`` tem apenas dois ramos (if/else). Use ``do`` quando você precisa de três ou mais ações
(cutscene, remover item, concluir objetivo, etc.).

remove_ground_item — excluir itens no chão em um quadrado::

    trigger player1 (find b2 mystery_treasure)
        (do (cut_scene 7546) (remove_ground_item b2 mystery_treasure)
            (add_units b2 10 gold_coin) (objective_complete 2))

Sintaxe: ``(remove_ground_item \<square\> \<item_type_name\> [count])``

``remove_item`` remove dos inventários do jogador; ``remove_ground_item`` remove do
chão em um quadrado (por exemplo, depois que o jogador larga um item de missão para abrir um baú).

and — todas as sub-condições devem ser verdadeiras::

    trigger player1 (and (find b2 treasure_opened_mark) (not (find b2 gold_coin)))
        (objective_complete 3)

Sintaxe: ``(and \<condition1\> \<condition2\> ...)``

Uma linha de gatilho tem uma expressão de condição. Envolva várias condições em ``and``; não
escreva ``(cond1) (cond2) (action)`` (a segunda S-expression se torna a ação).

Para ``find``, sempre coloque o quadrado antes do tipo, inclusive dentro de ``not``.
Errado: ``(not (find gold_coin b2))`` (verifica o quadrado padrão primeiro, quase sempre verdadeiro).
Certo: ``(not (find b2 gold_coin))``. Exemplo de largar-para-abrir: The Legend of Raynor capítulo 22; uso de inventário: capítulo 20.

npc_has_item — um NPC recebeu um item específico (inventário ou registro ``received_items``)::

    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)
    trigger player1 (npc_has_item quest_npc health_potion c3) (objective_complete 1)
    trigger player1 (npc_has_item b2 3 quest_npc short_sword) (objective_complete 2)

Sintaxe (qualquer forma):

- Clássica: ``(npc_has_item \<NPC_selector\> \<item_type_name\> [square])``
- Por índice: ``(npc_has_item \<square\> \<index\> \<unit_type\> \<item_type_name\>)`` — igual a
  ``transfer_units``; a N-ésima unidade naquele quadrado por ordem de geração. Exemplo: capítulo 28.

Forma clássica:

- ``\<NPC_selector\>``: ``type_name`` da unidade ou id da unidade.
- ``\<item_type_name\>``: por exemplo, ``health_potion``.
- `````[square]`````` opcional: limita a NPCs atualmente naquele quadrado.

A forma por índice corresponde pelo índice de geração; a unidade pode ter saído daquele quadrado.

give em ordens de gatilho (entrega roteirizada)::

    trigger player1 (timer 5) (order (a1 1 peasant) ((give c3 health_potion)))

Exemplo de mapa de encontrar item (The Legend of Raynor capítulo 17)::

    title Find the lost amulet
    lost_amulet c3
    starting_squares a1
    starting_units peasant
    trigger player1 (timer 0) (add_objective 1 "find the lost amulet")
    trigger player1 (has_item lost_amulet) (objective_complete 1)

Exemplo de mapa de entregar a NPC (``res/multi/give_demo.txt``)::

    health_potion a1
    computer_only 0 0 neutral c3 quest_npc
    trigger player1 (timer 0) (add_objective 1 "deliver the potion to the quest npc")
    trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)

Exemplos de campanha (``The Legend of Raynor``): cap. 14 entregar ``pickaxe`` ao ``npc_peasant`` aliado;
cap. 15 entregar ``knight_lance`` ao ``npc_knight`` neutro; cap. 16 entregar ``wand`` ao
``npc_mage`` inimigo (relações ``ally``/``neutral``/``enemy``). Veja ``res/single/The Legend of Raynor/14.txt``,
``15.txt``, ``16.txt``. Demo multijogador: ``res/multi/give_demo.txt``.

Aliança e transferência de unidades em campanha (a partir de 1.4.3.1)
.....................................................................

A diplomacia dinâmica F12 não funciona em campanhas. Após ``alliance_request``, o humano
aceita com Ctrl+F4 e recusa com Shift+F4 (sem seleção de alvo F12). Veja
``../player/campaign-northern-arc.htm`` para o arco do norte completo (cap. 24–27).

alliance_request — ação de gatilho: um jogador solicita aliança com outro::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (cut_scene 7585) (alliance_request computer1) (objective_complete 1))

Sintaxe: ``(alliance_request \<from\> [to])``; se ``to`` for omitido, o pedido vai ao
dono do gatilho.

alliance_with — condição: o dono do gatilho está aliado ao jogador dado::

    trigger player1 (alliance_with computer1) (objective_complete 2)

alliance_declined_with — condição: pedido de aliança recusado do jogador dado (campanha Shift+F4)::

    trigger player1 (alliance_declined_with computer1)
        (do (cut_scene 7598) (add_units c3 3 knight) (objective_abandon 1))

add_secondary_objective — ação de gatilho: adiciona um objetivo opcional (anunciado com o
prefixo "objetivo opcional"). A numeração é independente dos objetivos primários (ambos começam em 1)::

    trigger player1 (timer 0) (add_objective 1 7583)
    trigger player1 (timer 0) (add_objective 2 7584)
    trigger player1 (timer 0) (add_secondary_objective 1 7599)

secondary_objective_complete — ação de gatilho: conclui o objetivo opcional N (não afeta
o objetivo primário N)::

    trigger player1 (alliance_with computer1)
        (do (cut_scene 7586) (allied_assist computer1) (secondary_objective_complete 1))

objective_abandon — ação de gatilho: abandona o objetivo opcional N (por exemplo, recusar aliança);
aplica-se apenas a ``add_secondary_objective``.

alliance_request_pending — condição: há um pedido de aliança pendente do jogador dado.

transfer_units / convert_units / change_owner — ação de gatilho: muda a posse de unidades
de um jogador para outro (não é geração via ``add_units``)::

    trigger player1 (alliance_with computer1)
        (do (transfer_units computer1 player1) (add_objective 2 7584))

Sem seletor de unidade, todas as unidades vivas do jogador de origem são transferidas.
A sintaxe do seletor corresponde a ``order`` / ``add_units``: ``\<square\> \<count\> \<type\>``.

allied_assist — ação de gatilho: deixa unidades aliadas lutarem por conta própria (guarda→perseguição); não
concede comando ao jogador::

    trigger player1 (alliance_with computer1)
        (do (allied_assist computer1))

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (allied_assist computer1 c2 4 npc_archer_escort))

Sintaxe:

- Aliado inteiro: ``(allied_assist \<ally\>)``
- Apenas unidades selecionadas: ``(allied_assist \<ally\> \<square\> \<count\> \<type\> ...)``

A sintaxe do seletor de unidade corresponde a ``transfer_units`` / ``add_units``. Sem seletor, todas as unidades
de combate em guarda mudam para perseguição; com seletor, apenas as unidades correspondentes mudam; o restante fica
inalterado.

allied_control — ação de gatilho: permite que um jogador comande diretamente as unidades de um aliado
(selecionar, mover, atacar)::

    trigger player1 (npc_has_item npc_knight_leader secret_letter c2)
        (do (alliance 1) (allied_control computer1 c2 4 npc_knight_escort))

Sintaxe:

- Aliado inteiro: ``(allied_control \<ally\> [controller])``
- Apenas unidades selecionadas: ``(allied_control \<ally\> [\<controller\>] \<square\> \<count\> \<type\> ...)``

Sem seletor, todas as unidades vivas do aliado são concedidas e mudam para perseguição. Com seletor,
apenas as unidades correspondentes são concedidas (elas permanecem em guarda até o jogador dar ordens); unidades de combate
não correspondentes em guarda mudam para perseguição automaticamente.

add_inventory_item — coloca um item no inventário de uma unidade (recompensa de missão, re-concessão entre capítulos)::

    trigger player1 (has_killed 3 traitor_guard)
        (do (cut_scene 7580) (add_inventory_item garrek_token 1 raynor) (set_campaign_flag ch24_garrek_token))

Sintaxe: ``(add_inventory_item \<item_type\> [\<count\>] [\<unit_type\>])``; se a unidade for omitida, a primeira unidade amigável com ``inventory_capacity`` (a campanha do Raynor usa por padrão os tipos ``raynor``).

Progresso entre capítulos (três mecanismos)
..........................................

.. list-table::
   :header-rows: 1

   * - Mecanismo
     - Configuração
     - Transporta
   * - ``campaign_carryover``
     - campos de unidade em ``rules.txt``
     - Nível+XP, inventário
   * - 
     - 
     - (divisão; veja modding.rst)
   * - ``campaign_flag`` /
     - gatilhos do mapa
     - booleanos de história
   * - ``set_campaign_flag``
     - 
     - 
   * - ``add_inventory_item``
     - gatilhos do mapa
     - itens específicos


``campaign_flag`` persiste em ``campaigns.ini`` ``flags``; ``map_flag`` é apenas por mapa.

Re-conceder no início do capítulo::

    trigger player1 (timer 0) (if (campaign_flag ch24_garrek_token) (do (add_inventory_item garrek_token 1 raynor)))

unset_campaign_flag limpa flags persistidas por engano.

set_ai_mode — altera o modo de IA nas unidades do dono do gatilho::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (do (set_ai_mode offensive c2 1 npc_count_roland c2 2 npc_roland_guard) (set_yield_on_defeat 1 ...))

Sintaxe: ``(set_ai_mode \<offensive|defensive|guard|chase\> [\<square\> \<count\> \<type\> ...])``.

set_yield_on_defeat — alterna rendição por unidade (HP zero → rende-se em vez de morrer)::

    trigger computer1 (npc_has_item npc_count_roland garrek_token c2)
        (set_yield_on_defeat 1 c2 1 npc_count_roland c2 2 npc_roland_guard)

Sintaxe: ``(set_yield_on_defeat \<0|1\> [\<square\> \<count\> \<type\> ...])``. Também é possível definir ``yield_on_defeat 1`` em ``rules.txt``.

units_yielded — contagem de unidades inimigas rendidas::

    trigger player1 (units_yielded 1 npc_marco_ironhand) (objective_complete 1)

units_yielded_by — rendição forçada por um atacante específico (suporta ``is_a``)::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy) (objective_complete 1)

has_entered — unidades do dono do gatilho entraram em um quadrado (grade ou alias de nome de local; tipo de unidade opcional)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

map_flag / set_map_flag — flags de sessão por mapa (não salvos na configuração da campanha)::

    trigger player1 (has_entered c2 raynor7) (do (cut_scene 7718) (set_map_flag ch27_duel_started))

stop_all_units / release_yielded_units — cessar-fogo e encerrar invulnerabilidade de rendição::

    trigger player1 (units_yielded_by raynor7 1 npc_marco_ironhand enemy)
        (do (cut_scene 7710) (alliance 1 player1 computer1) (stop_all_units) (release_yielded_units computer1))

Execute ``cut_scene`` em gatilhos do player1 para que o cliente humano ouça a voz. Modos de IA / alternadores de rendição podem rodar em computer1 (dono das unidades).

O arco do norte de The Legend of Raynor (cap. 24–27): história contínua com objetivo compartilhado de ``traitor_guard`` e transporte de ``campaign_flag``. Veja ``../player/campaign-northern-arc.htm``:

- cap. 24 (carta para Garrek): ``allied_control``; ``add_inventory_item garrek_token`` após os traidores morrerem
- cap. 25 (token para Roland): matável antes da entrega; depois ``set_ai_mode`` + ``set_yield_on_defeat``; ``alliance_request``
- cap. 26 (estandarte para Vera): ``transfer_units``
- cap. 27 (duelo com Marco): ``has_entered c2 raynor7`` + cutscene 7718; ``set_ai_mode offensive`` só do Marco; escoltas recebem ``order`` para ``c1`` para limpar a arena; ``units_yielded_by raynor7``; ``stop_all_units`` + ``allied_control`` seletivo (4 cavaleiros de escolta)

O capítulo 25 deve registrar três objetivos primários (entregar token, derrotar Roland, matar traidores) mais o objetivo opcional 1 (aliança) no início. Pressione F9 para objetivos primários e opcionais. Computadores roteirizados aparecem como NPC (``Player.name`` + ``is_script_npc``).

NPCs principais (``npc_count_roland``, ``npc_roland_guard``, etc.) devem começar em ``ai_mode guard``. Ative ``yield_on_defeat`` em tempo de execução via ``set_yield_on_defeat``, e não nas regras no spawn, para que Roland seja matável antes que o token seja entregue.


Patrulha
........

Para ordenar até 10 dragões de d1 a patrulhar entre d1 e d9::

    trigger computer1 (timer 0) (order (d1 10 dragon) ((patrol d9)))


Atacar em um momento específico
...............................

Para ordenar até 10 dragões de e3 a atacar b2 após 20 minutos (velocidade normal)::

    timer_coefficient 60
    trigger computer1 (timer 20) (order (e3 10 dragon) ((go b2)))


Trocar para outra IA
....................

A IA padrão para computer_only é uma IA apenas de gatilho, que não faz nada. Para trocar para "easy" (também conhecida como "computador silencioso")::

    trigger computer1 (timer 0) (ai easy)


Adicionar unidades
..................

Para adicionar 10 dragões em A1::

    trigger computer1 (timer 0) (add_units a1 10 dragon)


#random_choice, #end_choice e #end_random_choice
"""""""""""""""""""""""""""""""""""""""""""""""
(novo em beta 9g)
Esta diretiva de pré-processador escolhe aleatoriamente entre 2 ou mais opções delimitadas por #random_choice, #end_choice e por #end_random_choice para a última opção.
Cada opção consiste em zero ou mais linhas.
Mais de uma diretiva #random_choice pode ser usada em um arquivo de mapa, mas elas não podem ser aninhadas.

Isso pode ser usado, por exemplo, para colocar recursos aleatórios. Por exemplo::

 #random_choice
 goldmines 500 e2 c6 b3 f5
 #end_choice
 goldmines 500 d2 d6 b4 f4
 #end_choice
 goldmines 500 c2 e6 b5 f3
 #end_random_choice

As linhas anteriores significam: "adiciona uma mina de ouro em e2, c6, b3 e f5, ou em d2, d6, b4 e f4, ou em c2, e6, b5 e f3". Dessa forma, os recursos ficam equilibrados (se eu não cometi um erro, claro). Isto é apenas um exemplo.

O título do mapa e o número de jogadores não podem ser alterados dessa forma porque o pré-processador é executado quando o mapa é carregado (ou seja: muito depois de o menu de um jogador ser carregado).

Mapas multijogador avançados: como alterar as regras e a aparência do jogo
--------------------------------------------------------------------------

Estrutura do mapa
"""""""""""""""""

O mapa avançado é uma pasta contendo um arquivo chamado "map.txt" com o conteúdo de um mapa comum, e a maioria dos arquivos e pastas que você encontra na pasta "res":
rules.txt, ai.txt, as pastas ui e seu conteúdo.

Nota: no momento, em uma pasta de mapa ou campanha, a versão localizada de style.txt (por exemplo: ui-fr/style.txt) não é carregada.
Sons localizados são carregados, no entanto.

Campanhas de um jogador
-----------------------

Onde armazenar uma nova campanha de um jogador
"""""""""""""""""""""""""""""""""""""""""""""

Se você tiver permissão de escrita na pasta onde o SoundRTS (ou o SoundRTS test) está instalado, pode guardar sua primeira campanha na pasta "single".

Se você não tiver permissão de escrita na pasta de arquivos de programa porque trabalha em modo não administrador, pode guardar o arquivo do mapa em que está trabalhando na pasta "single"
em "C:\\Documents and Settings\\Seu Login\\Application Data\\SoundRTS". Essa pasta é criada na primeira vez que você inicia o SoundRTS.
Outra solução é instalar o SoundRTS em uma pasta onde você tenha permissão de escrita e trabalhar na pasta mencionada no parágrafo anterior.

Estrutura da pasta da campanha
"""""""""""""""""""""""""""""""

O nome da pasta da campanha será usado pelo menu de um jogador. Campanhas oficiais terão seu próprio título na pasta "ui".
A pasta contém arquivos de capítulo. Ela também contém arquivos e pastas que imitam a estrutura da pasta "res": rules.txt, ai.txt, ui...

Arquivo de mods necessários
'''''''''''''''''''''''''''

Novo no SoundRTS 1.2 alpha 10.

Uma campanha pode definir quais mods ela requer. Os mods necessários serão carregados automaticamente.

Os mods necessários são definidos em um arquivo chamado "mods.txt", na pasta da campanha:

- o arquivo é uma lista separada por vírgulas de nomes de mods;
- se o arquivo não existir, os mods atuais serão mantidos;
- se o arquivo estiver vazio, o jogo "vanilla" será carregado.

Arquivos de capítulo
'''''''''''''''''''

Arquivos de capítulo são arquivos de texto chamados "0.txt", "1.txt", "2.txt", etc. Quando uma campanha é iniciada pela primeira vez, apenas o capítulo 0 está disponível. Quando um capítulo termina, o próximo capítulo pode ser executado. O número do capítulo mais alto disponível é armazenado automaticamente no arquivo de configuração do jogador chamado campaigns.ini.

Um arquivo de capítulo descreve um capítulo de missão ou um capítulo de cutscene.

Deve haver pelo menos um arquivo de capítulo, chamado "0.txt".

Sintaxe de um arquivo de capítulo
"""""""""""""""""""""""""""""""""

Um capítulo é uma missão ou uma cutscene.

Sintaxe de um arquivo de capítulo de missão
'''''''''''''''''''''''''''''''''''''''''''
Um arquivo de missão não é muito diferente de um mapa multijogador.
A estrutura de mapa avançado também é permitida: nesse caso, o nome da pasta é o número do capítulo.

Campanha cooperativa (a partir de 1.4.2.2; estilo AoE DE desde 1.4.4.4+): declare
``coop_campaign`` / ``coop_intro`` / ``coop_missions`` em ``campaign.txt``;
``hero_min_level 13:2 16:3 …`` opcional (níis de herói entre capítulos; veja ``modding.rst``);
um jogador e cooperativo carregam o mesmo mapa de missão ``N.txt`` (não inclua
``N.coop.txt``). Veja ``mod/coop-campaign.htm`` e
``player/campaign-and-co-op-improvements.htm``.

Missões cooperativas definem ``nb_players_min`` / ``nb_players_max`` e vários blocos ``player``
em ``N.txt``; em um servidor, qualquer jogador que conclua objetivos contribui
para a equipe. O modo um jogador ainda registra um humano e usa apenas o primeiro spawn.

Em campanhas, F12 (aliança dinâmica) não seleciona nenhum alvo. Computadores roteirizados por gatilho são
anunciados como "NPC" em vez de nomes internos como ``ai_timers``.

Intro
.....

Nota: um número pode representar uma mensagem de texto definida em tts.txt (novo no SoundRTS 1.2 alpha 9).

Exemplo: "intro 7500 7501 7502" significa: "antes de a partida começar, reproduz 7500.ogg, 7501.ogg e 7502.ogg (ou texto se definido em tts.txt)".
O comando intro define uma sequência de sons e textos que serão reproduzidos antes de a partida começar. Quando o jogador pressiona uma tecla, o próximo elemento da sequência é reproduzido. Um intro pode ser, por exemplo, um título com música, depois uma cena com uma conversa entre personagens, depois um briefing. Após o intro, o jogo anunciará os objetivos da missão.

Add_objective
.............

"add_objective player1 1 7000" significa: "adiciona o objetivo primário número 1 com o som 7000.ogg"

"add_secondary_objective player1 1 7599" significa: "adiciona o objetivo opcional número 1" (a missão
pode ser vencida sem concluí-lo). Objetivos primários e opcionais usam numeração independente
(ambos podem começar em 1; primário 1 e opcional 1 podem coexistir).

Todos os objetivos primários devem ser concluídos para vencer. Use ``secondary_objective_complete`` para
marcar um objetivo opcional como concluído, ou ``objective_abandon`` para abandoná-lo. Se um objetivo primário
falhar (por exemplo, um personagem importante morre), a missão é perdida.

Register_objective (ação em um gatilho)
.......................................

``register_objective`` registra números de objetivos primários necessários para a vitória sem
mostrá-los na lista F9 nem reproduzir a voz de "novo objetivo".

Sintaxe (dentro de uma ação de gatilho)::

    register_objective 1 2 3

Por que usar: se você encadear ``add_objective`` em vários gatilhos (revelar o objetivo 2 apenas
depois que o objetivo 1 for concluído), cada ``add_objective`` também adiciona aquele número ao conjunto de vitória.
Concluir o objetivo 1 poderia, de outra forma, desencadear uma vitória prematura quando os objetivos 2–N ainda não
tiverem sido adicionados.

Padrão de revelação progressiva — em ``timer 0``, registre todos os números, depois mostre apenas o primeiro
objetivo; a cada conclusão, ``objective_complete`` + ``add_objective`` para o próximo::

    trigger player1 (timer 0) (do (register_objective 1 2) (add_objective 1 7510))
    trigger player1 (has 4 pylon) (do (objective_complete 1) (add_objective 2 7511))
    trigger player1 (has_entered f1 gateway) (objective_complete 2)

Lógica de vitória: o motor mantém ``\_required_objective_numbers`` (de ``register_objective``
e ``add_objective``) e ``\_completed_objective_numbers`` (de ``objective_complete``).
A vitória da missão ocorre quando todos os números necessários estão concluídos — independentemente de um objetivo
ainda estar visível no F9.

Numeração F9 / voz: quando existem vários objetivos primários (registrados ou já mostrados),
F9 e ``add_objective`` anunciam "Objetivo primário N:" antes da descrição; com um
único objetivo primário o número é omitido. Veja ``soundrts/objective_announce.py``.

Exemplos: ``mods/starcraft/single/sc_build_tests/1.txt`` (2 objetivos); ``sc_late_game/1.txt`` (6
objetivos encadeados). Guia: ``campaign/progressive-objectives.htm``.

Objective_complete (ação em um gatilho)
.......................................

Esta ação só pode ser incluída na parte de ação de um gatilho.

"objective_complete 1" significa: "o objetivo primário 1 agora está concluído".

Secondary_objective_complete (ação em um gatilho)
.................................................

``objective_complete 1`` afeta apenas objetivos primários. Para concluir um objetivo opcional, use::

    secondary_objective_complete 1

que significa: "o objetivo opcional 1 agora está concluído".

Exemplo de gatilho:

"trigger player1 (has barracks) (objective_complete 2)" significa: "adiciona o seguinte gatilho para o player1: se ele tiver pelo menos 1 barracks então o objetivo 2 é concluído"

Coeficiente de temporizador
...........................

Um coeficiente de temporizador pode ser usado para medir o tempo de gatilhos em um determinado bloco.

Por exemplo, se você souber que quer que todos os seus gatilhos ocorram em blocos de meio minuto, pode definir seu coeficiente de temporizador como 30, assim:

"timer_coefficient 30"

Sempre que essa quantidade de tempo passar, o contador do temporizador será incrementado (aumentará em 1). Você pode então vincular gatilhos ao temporizador alcançar um determinado número. Por exemplo, se você quisesse fazer reforços aparecerem no mapa após 90 segundos (3 incrementos de 30 segundos), faria o seguinte:

"trigger player1 (timer 3) (add_units a1 10 footman)" ; após três ticks do temporizador, dá ao jogador 10 footman em a1

Cut_scene (ação em um gatilho)
..............................

Nota: a distinção entre sons em streaming e sons pré-carregados foi removida no SoundRTS 1.2. Todos os sons são carregados antecipadamente.

Nota: um número pode representar uma mensagem de texto definida em tts.txt (novo no SoundRTS 1.2 alpha 9).

Uma cutscene pode ser disparada no meio de uma partida: quando algo é descoberto, quando reforços chegam, etc.

"cut_scene 7500 7501" significa: reproduz a cutscene composta pelos sons 7500 e 7501.

Exemplo de gatilho:

"trigger player1 (has_entered d5) (cut_scene 7500)" significa: "adiciona o seguinte gatilho para o player1: se ele entrou no quadrado d5, então reproduz a cutscene composta pelo som 7500.ogg"

Temporizador e timer_coefficient (condição em um gatilho)

"timer_coefficient 60"

"trigger player1 (timer 2) (cut_scene 7500)" significa: "após 2 minutos (2 x 60 segundos) reproduz o arquivo de som 7500.ogg."

Ordens de IA
............

É possível controlar as ações do computador em uma missão, para aumentar o desafio. Você terá que fazer isso fazendo suas unidades receberem ordens em gatilhos específicos.

Por exemplo, podemos fazer as forças da IA em A1 moverem-se para a localização conhecida do jogador em A3, que enfrentará as forças do jogador conforme as encontrar. Aqui, lançaremos um ataque com 10 footman contra o jogador.

"timer_coefficient 60"

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1)))"

A posição dos colchetes é importante aqui, para encapsular os comandos corretos nas partes corretas deste gatilho. Se por algum motivo seu gatilho não parecer funcionar, tente verificar novamente os colchetes.

Também é possível enfileirar ordens para as unidades dadas seguirem. Neste próximo cenário, vamos imaginar que o jogador tem sua base espalhada por a1 e b1. Precisaríamos então dizer aos footmen para irem a b1 assim que terminarem com a1. Faríamos isso assim:

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1)))"

Finalmente, se você quiser que as unidades da IA entrem em modo "auto_attack", onde elas caçarão quaisquer unidades sobreviventes do jogador após limpar a base, você também pode fazer isso:

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1) (auto_attack)))"

Você pode usar ordens para fazer o computador treinar suas próprias unidades também, que você pode então tornar alvo de ordens posteriores. Aqui, diremos ao barracks do computador para treinar imediatamente mais 10 footmen para substituir os que estamos prestes a enviar para atacar o jogador.

trigger computer1 (timer 0) (order (a1 barracks) ((train footman) (train footman) (train footman))) ; e assim por diante até você ter 10 ordens de train footman

Note que cada ordem de treinamento deve ser separada; você não pode fazer o seguinte: (train 10 footman)

Esta não é a única forma de aumentar a quantidade de unidades que o jogador computador tem à sua disposição; você também poderia usar a ordem add_units como mostrado aqui.

trigger computer1 (timer 0) (add_units a1 10 footman)

No entanto, isso é imediato e não oferece ao jogador nenhuma forma de influenciar esse evento. No outro cenário, o jogador pode impedir o computador de ter seu próximo lote de footmen destruindo o barracks usado para treiná-los. Dessa forma, esses footmen aparecerão independentemente.

Sintaxe de um arquivo de capítulo de cutscene
'''''''''''''''''''''''''''''''''''''''''''''

Nota: a distinção entre sons em streaming e sons pré-carregados foi removida no SoundRTS 1.2. Todos os sons são carregados antecipadamente.

Nota: um número pode representar uma mensagem de texto definida em tts.txt (novo no SoundRTS 1.2 alpha 9).

Um capítulo de cutscene é uma sequência interrompível de sons. Quando o capítulo de cutscene é reproduzido, o próximo capítulo é desbloqueado.
Não confunda com cutscenes mais curtas executadas por um gatilho durante uma missão quando uma condição é atendida (descoberta de um quadrado, por exemplo), ou com a introdução (ou briefing) da missão.

Os capítulos de cutscene têm apenas 3 linhas. Por exemplo:
cut_scene_chapter
title 7000
sequence 7500 7501 7502

A primeira linha é uma palavra-chave usada para dizer ao jogo que este capítulo é uma cutscene e não uma missão.
A linha do título é usada no menu da campanha.
A linha de sequência significa: "reproduz o som 7500.ogg seguido por 7501 e 7502; se o jogador pressionar uma tecla, pula o som atual e reproduz o próximo."

Editor de mapas (experimental)
------------------------------

O cliente inclui um editor de mapas experimental para mapas multijogador. Ele só funciona para o terreno, então você ainda precisa editar manualmente o mapa para as unidades.

Iniciar o editor
""""""""""""""""

Inicie uma partida em um mapa. Esse mapa será o ponto de partida. Entre no console (pressione a tecla sob o escape) e digite o comando: "edit". Pressione Enter. As teclas de atalho do editor serão carregadas de res/ui/editor_bindings.txt.

Selecionar um terreno da paleta
"""""""""""""""""""""""""""""""

Pressione PageUp ou PageDown para selecionar um terreno. O significado de cada terreno está armazenado em ``res/ui/editor_palette.txt``.

O ``style`` de cada entrada da paleta deve corresponder a um nome de ``class terrain`` em ``rules.txt`` (por exemplo, ``forest``, ``dense_forest``, ``meadows``, ``lake``). Quando aplicado:

- **Terreno estático** (``is_dynamic 0``, por exemplo, lake, mountain): bloqueia ``type_name`` no quadrado; salvo como ``terrain <name>``.
- **Terreno dinâmico** (``is_dynamic 1``, por exemplo, forest, dense forest, meadows): coloca depósitos de ``wood`` / ``meadow`` no quadrado; a voz do terreno vem de ``square_terrain`` e pode mudar quando os objetos são removidos.

Aplicar um terreno a um quadrado
"""""""""""""""""""""""""""""""

Pressione Enter para aplicar o terreno ao quadrado atual. Quadrados vizinhos com as mesmas características (terreno e mesma altura) serão vinculados automaticamente por um caminho. Quadrados diferentes terão seu caminho removido.

Se o modo zoom estiver ativado, Enter aplica o terreno selecionado apenas à subcélula
atual. O mapa salvo usará a sintaxe ``square/x,y`` descrita em
`Terreno de subcélula (a partir de 1.4.4.8)`_.

Alternar caminho para um vizinho
"""""""""""""""""""""""""""""""

Pressione Control + Shift + seta para adicionar ou remover o caminho na direção correspondente.

Salvar mapa
"""""""""""

Pressione Control + s para salvar o mapa. O arquivo nunca sobrescreverá outro arquivo. O nome do arquivo será user/multi/editor0.txt, editor1.txt, editor2.txt, etc.

Sair do editor
"""""""""""""

Pressione F10 e saia da partida para sair do editor. Um salvamento automático do mapa será feito para o caso (mas não confie demais nele). Seu nome é user/multi/editor_autosave.txt

Adicionar unidades
"""""""""""""""""

Abra o arquivo em um editor de texto. Use os comandos mencionados em ``Definindo os recursos iniciais dos jogadores``.
