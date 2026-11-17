# Melhorias de campanha e campanha cooperativa (1.4.3.9)

Este guia descreve campanhas single-player e cooperativas no estilo Age of Empires Definitive Edition do SoundRTS: navegador de missões, cinco níveis de dificuldade, co-op de missão narrativa, escalonamento de inimigos e sincronização segura em lockstep. Para jogadores, autores de campanha e modders.

Versão em chinês: `../../zh/player/战役与合作战役改进说明 <../../zh/player/战役与合作战役改进说明.htm>`_.


----


1. Visão geral
-------------


Antes
~~~~~~~


- Single-player: apenas lista de capítulos; sem dificuldade, sinopse ou tentar novamente na derrota.
- Co-op (desde 1.4.2.2): vários humanos em um mapa de campanha, mas mais próximo de escaramuça que co-op AoE DE (sem níveis de dificuldade, slots de jogador, parceiros de IA aliados ou semântica narrativa compartilhada).

Depois (1.4.3.9)
~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Área
     - Single-player
     - Co-op
   * - Menu
     - Navegador de missões: sinopse, dificuldade, concluído/bloqueado
     - Servidor: campanha → capítulo → dificuldade → velocidade
   * - Dificuldade
     - Cinco níveis, salvos em ``user/campaigns.ini``
     - Mesmo + escalonamento extra por contagem de jogadores humanos
   * - Escalonamento de inimigos
     - HP / dano de saída do inimigo por %
     - Servidor calcula uma vez, transmite a todos os clientes / replays
   * - História
     - ``intro``, vitória/derrota orientadas por objetivos
     - ``intro`` compartilhado, cutscenes, objetivos F9; não "destruir todos os inimigos"
   * - Slots
     - Um humano
     - Um slot por humano; slots vazios preenchidos por IA aliada



Código principal: `soundrts/coop_difficulty.py <../../../soundrts/coop_difficulty.py>`_, ``soundrts/campaign.py <../../../soundrts/campaign.py>`_, ``soundrts/clientservermenu.py <../../../soundrts/clientservermenu.py>`_, ```soundrts/serverroom.py``.


----


2. Campanha single-player
---------------------------


2.1 Navegador de missões
~~~~~~~~~~~~~~~~~~~~


Após escolher uma campanha no menu principal:

1. Sinopse da campanha (opcional) — apenas se ``campaign.txt`` define ``synopsis``; reproduz TTS e retorna à lista.
2. Dificuldade: … — nível atual; submenu para escolher Easy / Standard / Moderate / Hard / Extreme.
3. Continuar — atalho para o último capítulo desbloqueado quando aplicável.
4. Lista de capítulos com status:

   - Completed — rejogável, título completo exibido.
   - Current — jogável, título completo.
   - Locked — número + "locked" apenas; não selecionável (sem spoiler de título).

5. Voltar.

Progresso é armazenado em `user/campaigns.ini <../../../soundrts/paths.py>`_ (``chapter`` + ``difficulty`` por id de campanha).

.. note:: **O que significa o marcador (desde 1.5.2.2)**

   O ``chapter`` do marcador é o **índice do próximo capítulo jogável dentro da
   lista de capítulos**:

   - índice < marcador -> concluído
   - índice == marcador -> atual
   - índice > marcador -> bloqueado

   Capítulos de cinemateca (``cut_scene_chapter``, como o prólogo ``0.txt``)
   **não ocupam uma posição jogável**: nunca tomam o slot "atual" e podem ser
   escolhidos no menu para serem reproduzidos.

2.1.1 Crescimento do herói e carryover entre missões (orientado por regras)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Configure qualquer herói em :strong:```rules.txt`` com ``campaign_carryover 1`` (não específico de Raynor).


.. list-table::
   :header-rows: 1

   * - Campo
     - Padrão
     - Efeito
   * - ``campaign_carryover_id``
     - def name
     - Chaves de save `hero_<id>_xp`, etc.
   * - ``campaign_carryover_stats``
     - ``1``
     - Nível + XP
   * - ``campaign_carryover_inventory``
     - ``1``
     - Mochila



- Salvo apenas na vitória; próximo capítulo restaura. ``hero_min_level`` em ``campaign.txt`` opcional.
- Co-op não persiste heróis.
- Divisão: ``campaign_carryover_inventory 0`` (apenas stats) ou ``campaign_carryover_stats 0`` (apenas inventário).

Guia do autor: `../mod/campaign-hero-carryover <../mod/campaign-hero-carryover.htm>`_.

2.2 Sinopse em ``campaign.txt``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   title 7747
   synopsis 7751


``7751`` é um id de voz em ``ui/tts.txt`` / ``ui-zh/tts.txt``. Omita ``synopsis`` para ocultar a entrada do menu.

Exemplo: ``res/single/The Legend of Raynor/campaign.txt``.

2.3 Dificuldade e escalonamento de inimigos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Dificuldade persiste em ``campaigns.ini``; padrão Standard.
- `MissionChapter.run` define ``enemy_hp_factor`` / ``enemy_damage_factor`` na sessão.
- Apenas unidades inimigas (não humanas, não neutras): HP no spawn, dano de saída no acerto.
- Standard + solo = 100% / 100% (linha de base inalterada).
- Solo nunca aplica o multiplicador por contagem de jogadores (sempre conta como 1 humano).

Níveis base (HP / dano):


.. list-table::
   :header-rows: 1

   * - Nível
     - HP inimigo
     - Dano inimigo
   * - Easy
     - 70%
     - 70%
   * - Standard
     - 100%
     - 100%
   * - Moderate
     - 120%
     - 115%
   * - Hard
     - 145%
     - 135%
   * - Extreme
     - 180%
     - 165%



2.4 Vitória e derrota
~~~~~~~~~~~~~~~~~~~~~~~


- Vitória: voz Next mission unlocked; menu Continue (próximo capítulo) ou Quit; marcador avança.
- Derrota: menu Retry this mission ou Quit.


----


3. Campanha cooperativa
-------------------------


3.1 Fluxo do jogador
~~~~~~~~~~~~~~~~


1. Lobby do servidor → Co-op campaign → campanha (apenas se ``coop_campaign 1`` em ``campaign.txt``) → capítulo → dificuldade → velocidade → criar sala.
2. Sem etapa de tratado (``treaty`` fixo em 0).
3. Outros entram; host inicia.
4. Todos recebem a intro do capítulo, depois gatilhos do mapa dirigem vitória/derrota.
5. Qualquer humano completando objetivos primários vence para a equipe; marcador do host avança quando o host vence e o marcador é igual ao capítulo atual.

3.2 Tabela de campanha e mapas de missão
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Menu co-op: dirigido por ``coop_campaign`` / ``coop_intro`` / ``coop_missions`` em cada ``campaign.txt`` (sem nomes de campanha fixos no motor).
- Carregamento de mapa: co-op e single-player compartilham ``N.txt``; o servidor carrega via ``ensure_chapter_map`` — sem ``N.coop.txt``.
- Autoria: `coop-campaign.md <../mod/coop-campaign.htm>`_ e §4 abaixo.

3.3 Missão narrativa, não escaramuça
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Vitória/derrota de ``add_objective``, ``objective_complete``, ``defeat``, etc. — não eliminar todos os jogadores de IA.
- `world.is_campaign = True`: música de campanha, computadores de gatilho anunciados como "NPC", sem "player defeated/quit" para IAs de script.
- ``cut_scene`` e objetivos transmitidos ao dono do gatilho e todos os aliados.
- `MultiplayerGame.pre_run` reproduz `world.intro` para co-op.

3.4 Slots de jogador e parceiros de IA aliados
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Exemplo de mapa: ``res/single/The Legend of Raynor/1.txt``.

.. code-block:: text

   nb_players_min 1
   nb_players_max 2
   player_start 1 a1 raynor footman footman
   player_start 2 h8 raynor2 footman archer
   computer_only e5 ...



.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``nb_players_max``
     - Contagem de slots co-op
   * - ``nb_players_min 1``
     - Solo + parceiros de IA permitidos
   * - ``player_start N …``
     - Quadrado de spawn e unidades do slot N
   * - ``computer_only``
     - Inimigos da missão (aliança `"ai"` vs humanos na aliança 1)



``Game._fill_coop_ai_partners`` preenche slots vazios com IA aliada agressiva; todos os humanos + parceiros começam na aliança 1.  
``player1``, ``player2``, … em gatilhos mapeiam para humanos na ordem de entrada; slots só de IA geralmente não são alvo de gatilhos narrativos.

3.5 Dificuldade e contagem de jogadores
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Além do nível base:

.. code-block:: text

   count multiplier = 100 + (humans - 1) × 20   (solo = 100%)
   final hp%        = base hp% × multiplier // 100
   final damage%    = base damage% × multiplier // 100


Exemplo: Hard + 3 humanos → base 145/135, multiplicador 140 → ~203% HP / 189% dano.

Servidor envia ``coop_difficulty`` antes de ``start_game``; apenas matemática inteira. Linha de seed do replay pode acrescentar ``hp% damage%`` (replays antigos padrão 100).

3.6 Nomes de lugares e recursos de campanha
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Nome lógico do mapa ``CampaignName/chapter`` dispara `apply_campaign_from_map_name <../../../soundrts/lib/resource.py>``_ para ``rules.txt`` e ``tts.txt`` da campanha carregarem nos clientes; nomes de quadrados como ``loc_ch02_*`` resolvem via TTS em vez de ler chaves brutas.

3.7 ``campaign_flag`` entre capítulos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Co-op não define ``world.campaign``, então ``campaign_flag`` sem objeto de campanha local retorna False (no-op determinístico). ``set_map_flag`` / ``map_flag`` na missão ainda funcionam no estado sincronizado do mundo.


----


4. Autoria de mapas
------------------


4.1 Tabela de campanha (``campaign.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Declare co-op como Age of Empires em :strong:```campaign.txt``. Não envie arquivos paralelos ``N.coop.txt``
; single-player e co-op carregam o mesmo mapa de missão ``N.txt``.

.. code-block:: text

   title 7747
   synopsis 7751
   coop_campaign 1
   coop_intro 0
   coop_missions 1-29



.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``coop_campaign``
     - ``1`` — mostrar no menu Co-op campaign do servidor
   * - ``coop_intro``
     - Números de capítulo de cutscene no fluxo co-op (ex. prólogo `0`)
   * - ``coop_missions``
     - Capítulos de missão jogáveis em co-op (`1-29`, listas com espaço, etc.)



4.2 Campos de mapa co-op (``N.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. ``nb_players_min 1`` / ``nb_players_max 2`` e vários blocos ``player`` (ou ``player_start``).
2. Duplique gatilhos-chave por jogador co-op quando necessário (``add_objective``, ``objective_complete``), ou dirija globalmente via ``player1`` se compartilhado.
3. `(alliance 1)` opcional para humanos co-op; inimigos via ``computer_only``.
4. ``intro`` / ``cut_scene`` opcionais; balanceamento via dificuldade do motor — sem hacks manuais de stats.

Single-player ainda registra um humano e usa apenas o primeiro spawn; slots co-op vazios não são preenchidos por IA no solo.

4.3 Correções relacionadas (1.4.3.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Mapas multi-computador: completar objetivos vence sem ter que matar toda IA de script (`Player.victory` itera um snapshot).
- F12 não seleciona alvo em campanhas; computadores de gatilho anunciados como "NPC".


----


5. Resumo da migração
----------------------



.. list-table::
   :header-rows: 1

   * - Antigo
     - Novo
   * - Apenas lista de capítulos
     - Sinopse + dificuldade + concluído/bloqueado + tentar novamente
   * - Co-op sem dificuldade / etapa de tratado
     - Cinco níveis + escalonamento por contagem; sem tratado
   * - Co-op como escaramuça
     - Intro/cutscenes/objetivos compartilhados; parceiros de IA
   * - ``N.coop.txt`` ou detecção de co-op por arquivo
     - Flags em ``campaign.txt`` + ``N.txt`` compartilhado
   * - Chaves brutas `loc_*` em co-op
     - Camada TTS de campanha, nomes localizados
   * - Standard = linha de base
     - Ainda 100%/100%; outros níveis conforme tabela




----


6. Testes
----------


.. code-block:: bash

   python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429b_campaign_browser_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
   python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
   python -m pytest soundrts/tests/test_coop_campaign_place_names.py -q
   python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
   python -m pytest soundrts/tests/test_changelog_1428_campaign_victory_f12.py -q



----


7. Veja também
-------------



.. list-table::
   :header-rows: 1

   * - Doc
     - Tópico
   * - [progressive-campaign-objectives.md](progressive-campaign-objectives.htm)
     - ``register_objective``
   * - [campaign-northern-arc.htm](campaign-secret-letter-alliance.htm)
     - The Legend of Raynor caps. 24–27
   * - [coop-campaign.md](coop-campaign.htm)
     - Referência curta de co-op
   * - ``mod/mapmaking.rst``
     - Sintaxe de missão




.. list-table::
   :header-rows: 1

   * - Fonte
     - Função
   * - ``soundrts/campaign.py``
     - Navegador SP, metadados co-op (`coop_*`), marcadores, dificuldade
   * - ``soundrts/coop_difficulty.py``
     - Tabela de níveis e multiplicador por contagem
   * - ``soundrts/clientservermenu.py``
     - Menu co-op, ``srv_coop_difficulty``
   * - ``soundrts/serverroom.py``
     - Parceiros de IA, transmissão de dificuldade
   * - ``soundrts/game.py``
     - ``is_coop_campaign``, intro, atualização de marcador
   * - ``soundrts/worldunit/worldcreature.py``
     - Escala de HP inimigo
   * - ``soundrts/combat/damage_effects.py``
     - Escala de dano inimigo
   * - ``soundrts/lib/resource.py``
     - Pilha de recursos de campanha, TTS de lugares
