Gerador de mapas aleatórios
=====================


Desde o SoundRTS 1.4.3.4, o gerador procedural de mapas aleatórios (RMG) constrói mapas ``.txt`` padrão a partir de opções do menu. Mapas gerados usam o mesmo pipeline de carregamento dos feitos à mão e funcionam em escaramuça local ou criação de sala online.


----


1. Onde encontrar
---------------------



.. list-table::
   :header-rows: 1

   * - Modo
     - Caminho
   * - Escaramuça local
     - Menu principal → Iniciar partida → Mapa aleatório (primeiro item)
   * - Host online
     - Conectar ao servidor → Criar partida → escolher Mapa aleatório → velocidade → configurar



Após a configuração, jogo local segue para convidar IA / facção / iniciar; jogo online envia comando ``create_random`` e o host gera o mapa ao iniciar a partida.


----


2. Fluxo de configuração
-----------------------


O submenu percorre (Esc volta um nível):

1. Modelo de mapa (ou Importar código de compartilhamento — seção 4)
2. Tamanho: pequeno / médio / grande
3. Jogadores: 2 / 3 / 4
4. Modo de equipe (apenas 4 jogadores): todos contra todos ou 2v2 fixo
5. Força dos monstros: fraco / médio / forte (guarnição hostil no centro; ataca jogadores — fraco: 2 footmen / médio: 4 footmen + 2 archers / forte: 6 footmen + 4 archers + 1 knight)
6. Layout de recursos: equilibrado / agrupado
7. Terreno (não para modelo lanes): aleatório / grama / pântano / montanha
8. Água (não para lanes): nenhuma / lago / rio
9. Tesouro: nenhum / baixo / alto (exige tipos ``class item`` coletáveis nas regras)
10. Modo de vitória: conquista / econômico / exploração / sobrevivência
11. Seed: aleatório ou número personalizado (0–99999)
12. Tratado: 0 / 5 / 10 / 15 / 20 minutos

Após selecionar a seed você ouve uma prévia por voz das configurações; após confirmar o tratado o mapa é gerado.

2.1 Modelos
~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modelo
     - Descrição
   * - Standard
     - Grade clássica, starts e pontes aleatórios
   * - Fast
     - Mais recursos iniciais, partidas mais rápidas
   * - Macro
     - Limite de pop maior e mais meadows, foco na economia
   * - Lanes
     - Layout de três rotas (estilo TD2); sem etapas de terreno/água



2.2 Equipes 2v2
~~~~~~~~~~~~~~


Com 4 jogadores e 2v2, o mapa adiciona gatilhos de aliança: jogadores 1+2 e 3+4 começam aliados.

2.3 Modos de vitória
~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modo
     - Condição de vitória
     - Objetivo inicial (voz)
     - Notas
   * - Conquest
     - Eliminar todos os jogadores inimigos
     - Eliminar todos os jogadores inimigos
     - Padrão; não precisa limpar creeps centrais ou guardas de barracks
   * - Economic
     - Ouro total coletado atinge a meta (exclui estoque inicial)
     - Coletar N ouro no total
     - Gastar ouro coletado ainda conta; prévia anuncia N; verificado a cada ~60s
   * - Exploration
     - Seu acampamento descobre todas as ruínas antigas
     - Descobrir todas as ruínas com suas forças
     - Em 2v2 descoberta do aliado conta; em FFA descobertas inimigas não; recompensa ainda vai ao primeiro visitante
   * - Survival
     - Resistir até o timer com prefeitura intacta
     - Resistir N minutos mantendo a prefeitura
     - 10 min fast, 15 min caso contrário; perder base primeiro = derrota; vários vencedores permitidos



Metas de ouro no modo econômico (somente ``resource1``):


.. list-table::
   :header-rows: 1

   * - Modelo
     - Meta
   * - Fast
     - 2000
   * - Standard
     - 3000
   * - Macro
     - 5000
   * - Lanes
     - 2500



Perder todos os edifícios ``provides_survival`` ainda significa derrota. Nos modos exploração/econômico/sobrevivência, eliminar todos os inimigos não vence automaticamente; você ainda pode atacar.

Todos os modos também geram ruínas antigas (recompensa de recurso única na primeira visita) e barracks capturáveis (limpar guardas, capturar, depois treinar unidades).


----


3. Anúncio de geração e F5/F6
--------------------------------------


No modo local, quando o mapa está pronto o jogo anuncia:

- Mapa gerado
- Seed (número para reproduzir o mesmo layout)
- Código de compartilhamento (string completa de configurações)
- Pressione F5 para repetir (dica do histórico)

O menu de convidar IA que segue não apaga isso: F5 repete a mensagem anterior, F6 percorre o histórico de voz para revisar seed e código de compartilhamento a qualquer momento.

Menus suportam as mesmas teclas F5 / F6 de histórico do jogo.


----


4. Códigos de compartilhamento
----------------


4.1 Formato
~~~~~~~~~~~


Exemplo:

.. code-block:: text

   RMG1:f:m:2:med:b:r:f:v:hi:4242


Onze partes separadas por dois-pontos: prefixo ``RMG1`` + 10 campos:


.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
     - Exemplos
   * - Template
     - standard / fast / macro / lanes
     - ``s`` / ``f`` / ``m`` / ``l``
   * - Size
     - small / medium / large
     - ``s`` / ``m`` / ``l``
   * - Players
     - 2–4
     - `2`
   * - Monsters
     - weak / medium / strong
     - ``w`` / ``med`` / ``s``
   * - Resources
     - balanced / clustered
     - ``b`` / ``c``
   * - Terrain
     - random / grass / marsh / mountain
     - ``r`` / ``g`` / ``a`` / ``t``
   * - Teams
     - ffa / teams_2v2
     - ``f`` / ``t``
   * - Water
     - none / lake / river
     - ``n`` / ``l`` / ``v``
   * - Treasure
     - none / low / high
     - ``n`` / ``lo`` / ``hi``
   * - Seed
     - 0 = aleatório; >0 fixo
     - `4242`



Importação aceita códigos com ou sem o prefixo ``RMG1:``; ``/`` funciona como separador em vez de ``:``.

4.2 Importar código de compartilhamento
~~~~~~~~~~~~~~~~~~~~~~


No submenu de modelo de mapa, escolha Importar código de compartilhamento, digite ou cole o código, Enter para confirmar, Esc para cancelar.

A caixa de entrada suporta atalhos de edição padrão (mesmos de outros campos ``input_string`` como seed ou login):


.. list-table::
   :header-rows: 1

   * - Atalho
     - Ação
   * - Ctrl+A
     - Selecionar tudo
   * - Ctrl+C
     - Copiar (todo o texto se nada selecionado)
   * - Ctrl+X
     - Recortar
   * - Ctrl+V
     - Colar (caracteres inválidos filtrados)
   * - Backspace / Delete
     - Apagar seleção ou caractere antes/depois do cursor



Comprimento máximo 80; caracteres permitidos: letras, dígitos, ``:``, ``/``, ``.``, ``-``.

Em caso de sucesso você ouve uma prévia e vai direto para Tratado (pulando etapas intermediárias). Códigos inválidos mostram Invalid share code e retornam ao menu de modelo.


----


5. Notas de multijogador
----------------------


- O comando ``create_random …`` do host é aplicado quando a partida inicia; todos os clientes recebem o mesmo mapa determinístico a partir de seed + configurações.
- Clientes não ouvem o anúncio local "mapa gerado + código de compartilhamento"; compartilhe o código antes de hospedar ou peça aos convidados que importem o mesmo código ao criar uma sala.
- Partidas públicas e minutos de tratado seguem os submenus usuais de velocidade / visibilidade.


----


6. vs. ``#random_choice`` em arquivos de mapa
------------------------------------------


``#random_choice`` / ``#end_random_choice`` em um arquivo de mapa são escolhas de pré-processador entre alternativas fixas (ex. posição aleatória de ouro). Isso não é RMG.

RMG gera o mapa inteiro a partir de parâmetros, com seeds e códigos de compartilhamento para reprodução.


----


7. Fonte
-----------



.. list-table::
   :header-rows: 1

   * - Item
     - Caminho
   * - Documentação no jogo
     - ``doc/en/randommap.htm`` (menu principal → Documentação → Guia de mapa aleatório)
   * - Gerador
     - ``soundrts/randommap.py``
   * - Menus
     - ``soundrts/randommap_menu.py``
   * - Testes
     - ``soundrts/tests/test_randommap.py``
   * - Guia em chinês
     - [../../zh/player/随机地图功能说明.md](../../zh/player/随机地图功能说明.htm)
