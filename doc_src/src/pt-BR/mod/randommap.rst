.. raw:: html

   <script type="text/javascript" src="langdir.js"></script>

Guia de mapa aleatório
======================

.. contents::

Introdução
----------

Desde o SoundRTS 1.4.3.4, o gerador procedural de mapas aleatórios (RMG)
monta mapas ``.txt`` padrão a partir das opções do menu. Mapas gerados usam
o mesmo pipeline de carregamento que mapas feitos à mão e funcionam em
escaramuça local ou na criação de salas online.

1. Onde encontrar
-----------------

.. list-table::
   :header-rows: 1

   * - Modo
     - Caminho
   * - Local
     - Menu principal → Iniciar partida → Mapa aleatório (primeiro item)
   * - escaramuça
     - 
   * - Anfitrião online
     - Conectar ao servidor → Criar partida → escolher Mapa aleatório → velocidade →
   * - 
     - configurar


Após a configuração, o jogo local segue para convite de IA / facção / início;
online envia um comando ``create_random`` e o anfitrião gera o mapa no início
da partida.

2. Fluxo de configuração
------------------------

O submenu percorre (Esc volta um nível):

1. Modelo de mapa (ou Importar código de compartilhamento — seção 4)
2. Tamanho: pequeno / médio / grande
3. Jogadores: 2 / 3 / 4
4. Modo de equipe (apenas 4 jogadores): todos contra todos ou 2v2 fixo
5. Força dos monstros: fraca / média / forte (guarnição hostil central; ataca
   jogadores — fraca: 2 footman / média: 4 footman + 2 archer / forte: 6
   footman + 4 archer + 1 knight)
6. Layout de recursos: equilibrado / agrupado
7. Terreno (não para modelo lanes): aleatório / grass, mais todo terreno
   ``rmg_terrain 1`` em ``rules.txt``
8. Água (não para lanes): nenhuma / lago / rio
9. Tesouro: nenhum / baixo / alto (requer tipos ``class item`` coletáveis em
   rules)
10. Modo de vitória: conquest / economic / exploration / survival (padrão
    conquest; veja seção 7)
11. Semente: aleatória ou número personalizado (0–99999)
12. Trégua: 0 / 5 / 10 / 15 / 20 minutos

Após a seleção da semente você ouve uma prévia por voz das configurações; após
confirmar a trégua o mapa é gerado.

2.1 Modelos
^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Modelo
     - Descrição
   * - Standard
     - Grade clássica, inícios e pontes aleatórios
   * - Fast
     - Mais recursos iniciais, partidas mais rápidas
   * - Macro
     - Limite de população maior e mais prados, foco em economia
   * - Lanes
     - Layout de três rotas (estilo TD2); sem etapas de terreno/água


2.2 Equipes 2v2
^^^^^^^^^^^^^^^

Com 4 jogadores e 2v2, o mapa adiciona gatilhos de aliança: jogadores 1+2 e
3+4 começam aliados.

3. Anúncio de geração e F5/F6
-----------------------------

No modo local, quando o mapa estiver pronto o jogo anuncia:

- Mapa gerado
- Semente (número para reproduzir o mesmo layout)
- Código de compartilhamento (string completa de configurações)
- Pressione F5 para repetir (dica de histórico)

O menu de convite de IA que segue não apaga isso: F5 repete a mensagem
anterior, F6 percorre o histórico de voz para revisar semente e código de
compartilhamento a qualquer momento.

Menus suportam as mesmas teclas de histórico F5 / F6 do jogo.

4. Códigos de compartilhamento
------------------------------

4.1 Formato
^^^^^^^^^^^

Exemplo::

 RMG1:f:m:2:med:b:r:f:v:hi:c:4242

Doze partes separadas por dois-pontos: prefixo ``RMG1`` + 11 campos (códigos
legados de 10 campos omitem vitória e usam conquest como padrão):

.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
     - Exemplos
   * - Modelo
     - standard / fast / macro / lanes
     - s / f / m / l
   * - Tamanho
     - small / medium / large
     - s / m / l
   * - Jogadores
     - 2–4
     - 2
   * - Monstros
     - weak / medium / strong
     - w / med / s
   * - Recursos
     - balanced / clustered
     - b / c
   * - Terreno
     - random / grass / marsh / mountain
     - r / g / a / t
   * - Equipes
     - ffa / teams_2v2
     - f / t
   * - Água
     - none / lake / river
     - n / l / v
   * - Tesouro
     - none / low / high
     - n / lo / hi
   * - Vitória
     - conquest / economic /
     - c / e / x / s
   * - 
     - exploration / survival
     - 
   * - Semente
     - 0 = aleatória; >0 fixa
     - 4242


Abreviações de vitória: ``c`` conquest, ``e`` economic, ``x`` exploration,
``s`` survival.

Importação aceita códigos com ou sem o prefixo ``RMG1:``; ``/`` funciona como
separador em vez de ``:``.

4.2 Importar código de compartilhamento
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No submenu de modelo de mapa, escolha Importar código de compartilhamento,
digite ou cole o código, Enter para confirmar, Esc para cancelar.

A caixa de entrada suporta atalhos de edição padrão (iguais a outros campos
de texto como semente ou login):

.. list-table::
   :header-rows: 1

   * - Atalho
     - Ação
   * - Ctrl+A
     - Selecionar tudo
   * - Ctrl+C
     - Copiar (todo o texto se nada estiver selecionado)
   * - Ctrl+X
     - Recortar
   * - Ctrl+V
     - Colar (caracteres inválidos filtrados)
   * - Backspace / Delete
     - Excluir seleção ou caractere antes/depois do cursor


Comprimento máximo 80; caracteres permitidos: letras, dígitos, ``:``, ``/``,
``.``, ``-``.

Em caso de sucesso você ouve uma prévia e vai direto para Trégua (pulando
etapas intermediárias). Códigos inválidos mostram Invalid share code e voltam
ao menu de modelos.

5. Observações multijogador
---------------------------

- O comando ``create_random …`` do anfitrião é aplicado quando a partida
  inicia; todos os clientes recebem o mesmo mapa determinístico a partir de
  semente + configurações.
- Clientes não ouvem o anúncio local "map generated + share code"; compartilhe
  o código antes de hospedar ou peça aos convidados que importem o mesmo código
  ao criar uma sala.
- Partidas públicas e minutos de trégua seguem os submenus habituais de
  velocidade / visibilidade.

6. vs. ``#random_choice`` em arquivos de mapa
---------------------------------------------

``#random_choice`` / ``#end_random_choice`` em um arquivo de mapa são escolhas
do pré-processador entre alternativas fixas (por exemplo posicionamento
aleatório de ouro). Isso não é RMG.

O RMG gera o mapa inteiro a partir de parâmetros, com sementes e códigos de
compartilhamento para reprodução.

7. Jogabilidade inspirada em HoMM / Civ5
----------------------------------------

Recursos do RMG inspirados em Heroes of Might and Magic e Civilization V
(objetivos de mapa e POI, não turnos completos nem árvores tecnológicas):

7.1 Modos de vitória
^^^^^^^^^^^^^^^^^^^^

Conquest
    Eliminar todos os jogadores inimigos (padrão; limpar criaturas centrais é
    opcional).

Economic
    Ouro total coletado atinge a meta (exclui estoque inicial; gastos ainda
    contam; verificado a cada ~60s).
    Fast 2000 / standard 3000 / macro 5000 / lanes 2500.

Exploration
    Seu acampamento descobre todas as ruínas antigas (FFA: só suas descobertas
    contam; 2v2: descobertas de aliados contam).

Survival
    Resista até o temporizador terminar com sua prefeitura intacta (10 min
    fast / 15 min nos demais).

Perder todos os edifícios ``provides_survival`` ainda significa derrota. Nos
modos exploration/economic/survival, eliminar todos os inimigos não garante
vitória automática; você ainda pode atacar. Verificações de vitória rodam a
cada ~30s (exploration) ou 60s (economic) após as condições serem atendidas.

7.2 POI do mapa
^^^^^^^^^^^^^^^

Todo mapa RMG (quando os tipos existem em ``rules.txt``) pode incluir:

- Ruínas antigas (``ancient_ruin``): sua unidade entra na casa por recursos
  (fast: 300 ouro + 150 madeira; outros: 500 + 250); exploration exige que seu
  acampamento encontre toda ruína; recompensa apenas ao primeiro visitante;
  edifício permanece após descoberta
- Quartéis capturáveis (``captured_barracks``): guardas 2 footman + 1 archer;
  elimine guardas, ataque para capturar, depois treine footman/archer;
  quartéis sem reforço geram footman extras a cada ~5–10 minutos
- Guarnição central: menu Força dos monstros (fraca 2 footman / média 4+2 /
  forte 6+4+1 knight)

7.3 Leitura adicional
^^^^^^^^^^^^^^^^^^^^^

Comparação completa, IDs de voz e extensão por mod:
``player/英雄无敌与文明5玩法说明.htm`` (chinês; detalhes RMG em inglês em
``player/random-map.htm``).

8. Modelos personalizados de mapa aleatório
-------------------------------------------

Jogadores e autores de mod podem adicionar arquivos de texto
``random_map_template`` para estender modelos RMG e alinhar escolhas de terreno
com ``rules.txt``.

8.1 Onde colocar arquivos
^^^^^^^^^^^^^^^^^^^^^^^^^

- ``cfg/randommap/*.txt`` — modelos locais do jogador (recomendado)
- ``mods/<modname>/randommap/*.txt`` — incluídos com um mod
- Referência de sintaxe: ``res/randommap/example.txt``

8.2 Formato do arquivo
^^^^^^^^^^^^^^^^^^^^^^

::

 random_map_template
 name my_macro
 extends macro
 title My macro map
 terrain_modes random grass marsh rocky_plain
 water_terrain lake
 monster_medium 4 footman 2 archer

- ``extends`` herda de ``standard``, ``fast``, ``macro``, ``lanes`` ou outro
  modelo personalizado
- Modelos integrados omitem ``terrain_modes`` para listar automaticamente
  ``random``, ``grass`` e todos os terrenos ``rmg_terrain 1`` de rules
- ``terrain_modes`` opcionalmente restringe o menu (cada nome deve ser
  ``class terrain`` em ``rules.txt``)
- Códigos de compartilhamento: modelos integrados ainda usam abreviações
  ``RMG1:``; modelos personalizados ou nomes de terreno personalizados usam
  ``RMG2:`` (nomes completos, sem abreviações)

8.3 Flags de terreno em rules.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Flags opcionais em ``class terrain``:

- ``rmg_terrain 1`` — terreno terrestre que o RMG pode colocar
- ``rmg_border 1`` — colocar ao longo das bordas do mapa (por exemplo
  montanhas)
- ``rmg_water 1`` — nome de terreno usado para casas de água de lago/rio
- ``rmg_ford 1`` — nome de terreno usado para vaus em mapas de rotas

Quando o RMG coloca terreno, lê ``speed``, ``is_water``, ``blocks_path`` e
propriedades relacionadas de rules em vez de valores fixos de ``marsh`` /
``mountain``.
