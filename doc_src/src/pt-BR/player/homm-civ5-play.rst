Guia de jogo estilo Heroes of Might and Magic e Civilization 5
================================================================


Desde o SoundRTS 1.4.3.4, mapas aleatórios (RMG) incorporam, sobre a estrutura clássica de RTS, objetivos de mapa, pontos de interesse (POI) e várias condições de vitória inspiradas em *Heroes of Might and Magic* (HoMM) e *Civilization 5* (Civ5). Este documento explica o paralelo de design, ações do jogador e como mods/desenvolvedores podem estender o sistema.


Instruções gerais sobre menu de mapa aleatório, semente e código de compartilhamento: `Mapas aleatórios (jogador) <random-map-play.htm>`_.


----


1. Filosofia de design: o que dá para jogar num RTS
--------------------------------------------------


O SoundRTS continua sendo estratégia em tempo real: selecionar unidades, dar ordens, coletar, treinar tropas e lutar. Os elementos HoMM / Civ5 aparecem sobretudo na **geração de mapa** e em **gatilhos de vitória**, não como turnos completos nem árvore de tecnologia.


.. list-table::
   :header-rows: 1

   * - Inspiração
     - Equivalente no SoundRTS
     - Onde está implementado
   * - Exploração e recompensas em ruínas (HoMM)
     - Enviar unidade à casa → anúncio «ruína descoberta» → ouro/madeira
     - ``ancient_ruin`` + gatilho ``has_entered``
   * - Ninhos neutros / postos capturáveis (HoMM)
     - Eliminar guardas → unidade com ``can_capture 1`` ocupa o quartel (ou ataca até o limiar)
     - ``captured_barracks`` + ``capture_hp_threshold`` + ``can_capture`` na unidade
   * - Guardiões centrais, mapa simétrico (HoMM)
     - Forças hostis escaladas no centro (e pontos espelhados)
     - ``MONSTER_PRESETS`` + ``\_append_creep``
   * - Várias formas de vitória (Civ5)
     - Conquista / Economia / Exploração / Sobrevivência no RMG
     - `RandomMapConfig.victory_mode`
   * - Explorar o mapa, vitória por recursos (Civ5)
     - Exploração: descobrir todas as ruínas; Economia: coleta acumulada atinge a meta
     - ``\_victory_mode_trigger_lines``
   * - Sobrevivência e pressão de tempo (Civ5)
     - Sobrevivência: resistir até o fim do cronômetro mantendo a base principal (``personal_victory``)
     - ``timer`` + `(personal_victory)`
   * - Baús / luxos no mapa (Civ5)
     - Opção «baús»: itens coletáveis ou minas extras em posição simétrica
     - ``\_append_treasure``
   * - Missões secundárias estilo city-state (campanha)
     - Entregar itens a NPC por recursos (não é RMG; script de campanha)
     - Ex.: `res/single/The Legend of Raynor/`



Não implementado — apenas direção futura (RMG atual não inclui):

- Herói com level, árvore de habilidades, sistema de mana (núcleo HoMM)
- Árvore de tecnologia, cultura, pontos diplomáticos (núcleo Civ5)
- Expansão de cidades, produção por tile, cartas de política


----


2. Guia do jogador
------------------


2.1 Como iniciar
~~~~~~~~~~~~~~~~


1. Menu principal → Iniciar jogo → Mapa aleatório
2. Configure passo a passo no menu, ou em Modelo de mapa → Importar código de compartilhamento cole a configuração completa (Ctrl+V suportado)
3. Na etapa Modo de vitória, escolha o estilo de jogo (padrão: Conquista)
4. Confirme o tratado de cessar-fogo e gere o mapa

No modo Exploração, após clicar «Iniciar» e entrar na partida, toca primeiro o briefing da semente (missão + variante aleatória + objetivo de exploração) e só então começa a operação. O briefing depende da semente do mapa; o mesmo código de compartilhamento reproduz o mesmo resultado.

Multijogador: ao criar sala, escolha Mapa aleatório na lista; o host gera com a mesma semente no início; o cliente não anuncia automaticamente o código — troquem-no antes.

2.2 Quatro modos de vitória
~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modo
     - ID de voz
     - Condição de vitória
     - Condição de derrota (igual nos outros modos)
   * - Conquista
     - 5426
     - Eliminar todos os jogadores inimigos (não precisa limpar criaturas centrais)
     - Perder todos os edifícios ``provides_survival``
   * - Economia
     - 5427
     - Coleta acumulada atinge ouro-alvo (não conta o inicial; gastar ainda conta)
     - Idem
   * - Exploração
     - 5428
     - Visitar pessoalmente cada ruína antiga
     - Idem
   * - Sobrevivência
     - 5429
     - Resistir até o fim do tempo mantendo a base principal
     - Idem



Prévia da configuração: no modo Economia, anuncia também o ouro-alvo (ex.: «Economia… 3000 ouro»).

Ouro-alvo no modo Economia (apenas ``resource1``, ou seja, ouro):


.. list-table::
   :header-rows: 1

   * - Modelo de mapa
     - Meta
   * - Rápido
     - 2000
   * - Padrão
     - 3000
   * - Macro
     - 5000
   * - Corredor
     - 2500



Duração do modo Sobrevivência:


.. list-table::
   :header-rows: 1

   * - Modelo de mapa
     - Duração
   * - Rápido
     - 10 minutos
   * - Padrão / Macro / Corredor
     - 15 minutos




Atenção: em Exploração, Economia e Sobrevivência, eliminar todos os inimigos **não** concede vitória automática (removido `(no_enemy_player_left) (victory)`); ainda é possível atacar para enfraquecer oponentes. Perder a base principal (centro da cidade etc. com ``provides_survival 1``) ainda causa derrota.

2.3 Pontos de interesse do mapa (POI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Todo mapa RMG (desde que ``rules.txt`` defina os tipos de unidade correspondentes) gera estes POI, independentemente do modo de vitória:

Ruínas antigas (``ancient_ruin``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Função: dispara na primeira vez que **sua** unidade entra na casa (não exige atacar o edifício)
- Recompensa do ato 1: anúncio de ruína descoberta (5433) e recursos
- Modelo rápido: 300 ouro + 150 madeira
- Outros modelos: 500 ouro + 250 madeira
- Ato 2 (casa adjacente): após descobrir a ruína, avisa que há «som metálico atrás da parede de pedra» — verifique a casa vizinha (5490). Se houver casa adjacente válida, enviar unidade a ela dá «recompensa extra nas profundezas» (5491) e recursos extras (~50% do ato 1: rápido +150 ouro / +75 madeira; outros +250 ouro / +125 madeira). Se a adjacência não for válida (borda, spawn etc.), o ato 2 é ignorado.
- Progresso de exploração (só vitória por Exploração): após descobrir, anuncia «ruínas ainda não descobertas: N» ou «só resta a última ruína» (5492 / 5493).
- Vitória por exploração: você deve enviar unidades a **cada** ruína (em 2v2, conta a união do que você e aliados visitaram). Ruínas já vistas pelo inimigo não contam no seu progresso, mas você ainda pode entrar depois e completar a descoberta; a recompensa do primeiro a entrar em cada ruína no mapa só é paga uma vez (quem chegar primeiro).
- Quantidade (pares simétricos; pontos de gatilho = 2× pares):
- Mapa pequeno: 1 par (+1 par no modo Exploração)
- Médio / grande: 2 pares (+1 par no modo Exploração)

Quartéis capturáveis (``captured_barracks``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Guardas: 2 infantaria + 1 arqueiro na casa (IA hostil, não neutral)
- Captura: elimine os guardas; unidade com ``can_capture 1`` clique com botão direito no quartel (ou ataque até o limiar de captura). Com ``capture_hp_threshold`` 100, basta chegar — sem dano. Unidade com ``can_capture 0`` só ataca normalmente, sem ordem de captura padrão
- Após captura: anúncio quartel ocupado (5434); pode treinar infantaria (máx. 5) e arqueiro (máx. 3)
- Antes da captura: reforço de ~2 infantaria a cada 5–10 minutos (até ser capturado)
- Quantidade: mapa pequeno 1 par; médio/grande 2 pares; Exploração +1 par extra

Guardiões centrais (intensidade de criaturas)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


O menu Intensidade de criaturas controla a escala no centro do mapa (zona perigosa estilo HoMM):


.. list-table::
   :header-rows: 1

   * - Intensidade
     - Tropas
   * - Fraca
     - 2 infantaria
   * - Média
     - 4 infantaria + 2 arqueiros
   * - Forte
     - 6 infantaria + 4 arqueiros + 1 cavaleiro



Os guardiões atacam jogadores que entram no alcance; modelos Rápido / Corredor ajustam quantidade via ``creep_multiplier``.

Baús (opcional)
^^^^^^^^^^^^^^^


Opção Baús no menu: Nenhum / Poucos / Muitos:

- Poucos: 1 mina de ouro extra simétrica (~500)
- Muitos: 2 locais; ~45% item coletável (``class item``), ~35% pomar, resto mina de ouro (~900)

Requer definições de itens coletáveis ``class item`` no ``rules.txt`` atual.

2.4 Coordenadas e dicas de exploração
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Coordenadas no mapa e no menu são base 1 (canto inferior esquerdo = `1,1`)
- Para explorar ruínas, mova a unidade até a casa da ruína; não precisa selecionar a ruína nem atacar
- Ruínas «descobertas» não somem; a recompensa só é paga uma vez
- F5 / F6 repetem falas anteriores («mapa gerado», semente, código de compartilhamento etc.)

2.5 Campo de modo de vitória no código de compartilhamento
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


O código completo tem 12 segmentos (prefixo ``RMG1``); o 11º é o modo de vitória:

.. code-block:: text

   RMG1:modelo:tamanho:jogadores:criaturas:recursos:terreno:equipe:água:baús:vitória:semente


Abreviações do modo de vitória:


.. list-table::
   :header-rows: 1

   * - Abrev.
     - Modo
   * - ``c``
     - Conquista (conquest)
   * - ``e``
     - Economia (economic)
   * - ``x``
     - Exploração (exploration)
   * - ``s``
     - Sobrevivência (survival)



Exemplo (Corredor, mapa pequeno, 2 jogadores, Exploração, baús altos, semente 6685):

.. code-block:: text

   RMG1:l:s:2:w:b:r:f:n:hi:x:6685


Códigos antigos de 10 segmentos (sem campo de vitória) importam como Conquista por padrão.


----


3. Regras e definições de dados (``res/rules.txt``)
---------------------------------------------------


Definições de unidades POI ficam perto do fim das regras base (comentário indica inspiração HoMM / Civ5):

.. code-block:: text

   def ancient_ruin
   class building
   cost 0 0
   time_cost 0
   hp_max 200
   hp_regen 0
   capture_hp_threshold 0    ; não capturável, só marcador no mapa
   provides_survival 0
   is_buildable_anywhere 0
   sight_range 1
   
   def captured_barracks
   class building
   cost 0 0
   time_cost 0
   hp_max 500
   hp_regen 0.1
   capture_hp_threshold 100  ; capturável com HP ≤100% (um ataque basta)
   provides_survival 0
   is_buildable_anywhere 0
   can_train footman 5 archer 3
   population_provided 0


Campos principais
~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Campo
     - Ruína
     - Quartel
   * - ``capture_hp_threshold``
     - ``0`` = não capturável
     - `100` = capturável (ocupa ao contato)
   * - ``can_capture``
     - — (na unidade atacante)
     - Padrão `1`; `0` = unidade não usa captura por padrão no clique direito/IA
   * - ``provides_survival``
     - ``0`` = perder não afeta «ainda há edifício»
     - Idem
   * - ``can_train``
     - Nenhum
     - Unidades e limites após captura
   * - ``sight_range 1``
     - Visão baixa; motor pode logar INFO para ``sight_range 1`` — pode ignorar
     - —



Se o mod remover ou renomear esses ``type_name``, o RMG usa ``\_rules_has_type()`` e pula a geração do POI correspondente, sem erro.


----


4. Gerador de mapa aleatório (desenvolvedor)
--------------------------------------------


Código principal: ``soundrts/randommap.py``  
Menu: ``soundrts/randommap_menu.py``  
Testes: ``soundrts/tests/test_randommap.py``

4.1 Visão geral do fluxo de geração
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   RandomMapConfig
       → generate_definition() / _generate_grid_definition() / _generate_lanes_definition()
           → terreno, recursos, água, baús
           → _append_hunting (animais selvagens)
           → blocos de spawn dos jogadores
           → _append_creep (guardiões centrais)
           → _append_exploration_poi (ruínas + gatilhos has_entered)
           → _append_capturable_dwelling (quartéis + gatilhos de reforço/captura)
           → _append_skirmish_triggers (vitória/derrota)
       → saída string .txt do mapa → Map / World carrega normalmente


Posição dos POI: ``\_symmetric_pairs()`` escolhe casas simétricas evitando spawns e espelhos, para equidade.

4.2 Modelo de gatilho na geração de POI de exploração
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


``\_append_exploration_poi()`` grava por ruína:

.. code-block:: text

   computer_only 0 0 neutral 8,2 1 ancient_ruin
   trigger players (has_entered 8,2) (if (not (rmg_ruin_discovered_by_self rmg_ruin_0)) (do (rmg_mark_ruin_discovered rmg_ruin_0) (if (not (map_flag rmg_ruin_0_reward)) (do (set_map_flag rmg_ruin_0_reward) (cut_scene 5433) (grant_resources 500 resource1 250 resource2))) (cut_scene 5490)))


- Coordenada `8,2` é base 1; ``has_entered`` em ``triggers.py`` converte para chave de grade base 0
- Importante: em mapas estreitos como Corredor, coordenada base 1 pode «colidir» com chave base 0; o parser de gatilhos deve converter de base 1 primeiro, não consultar a grade diretamente (senão a ruína não dispara)

4.3 Modelo de gatilho de quartel capturável
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   computer_only 0 0 8,3 1 captured_barracks 2 footman 1 archer
   trigger computerN (timer 5 5) (if (and (not (map_flag rmg_dwelling_8_3)) (unit_lost 8,3 1 captured_barracks)) (do (set_map_flag rmg_dwelling_8_3) (cut_scene 5434)))
   trigger computerN (timer 300 600) (if (and (not (map_flag rmg_dwelling_8_3)) (not (unit_lost 8,3 1 captured_barracks))) (add_units 8,3 2 footman))


- Quartel em casa ``computer_only`` hostil (com guardas), não ``neutral``, senão guardas não engajam
- Captura via `(unit_lost casa 1 captured_barracks)` (edifício tomado/substituído); não use o obsoleto ``transfer_units player1``

4.4 Gatilhos de modo de vitória
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modo
     - Lógica gerada
   * - Economia
     - A cada 60 s verifica ``(has_gathered meta resource1)`` → `` (victory)`` (coleta acumulada, sem inicial)
   * - Sobrevivência
     - ``(timer segundos) (if (not (no_building_left)) (personal_victory))`` (vários podem vencer)
   * - Exploração
     - A cada 30 s verifica ``(rmg_all_ruins_discovered_by_allies rmg_ruin_0 …)`` → `` (victory)``
   * - Conquista
     - ``(no_enemy_player_left) (victory)`` (só modo Conquista; só jogadores inimigos)



Condição de derrota comum (todos os modos):

.. code-block:: text

   trigger players (no_building_left) (defeat)
   trigger computers (no_unit_left) (defeat)


4.5 Passos recomendados para estender tipos de POI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Exemplo: adicionar «santuário (shrine)»:

1. **``rules.txt``**: defina ``def shrine`` (herda ``building``, ``capture_hp_threshold`` ou marcador puro)
2. **``res/ui-zh/tts.txt`` / ``res/ui/tts.txt``**: atribua novo ID de voz (evite conflito com faixa RMG 5425–5441)
3. **``msgparts.py``**: adicione constantes `RMG_*`
4. **``randommap.py``**:

   - Nova `_append_shrine_poi()`, espelhando ``\_append_exploration_poi``
   - Chame em `_generate_*_definition`
   - Se ligado à vitória por exploração, retorne lista de flags para ``\_victory_mode_trigger_lines``
5. **``randommap_menu.py``**: se precisar de item de menu, estenda ``\_open_victory_menu`` ou opções de modelo
6. **``\_SHARE_ABBR["victory_mode"]`` ou novo campo**: atualize ``encode_share_code`` / ``decode_share_code``
7. Testes: em ``test_randommap.py``, assert que o texto gerado contém os gatilhos esperados

4.6 API de gatilhos relacionada
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Gatilho
     - Uso
   * - ``(has_entered casa [tipo_unidade…])``
     - Unidade do jogador entra na casa
   * - ``(has_gathered quantidade resource1)``
     - Vitória Economia: coleta acumulada (sem inicial)
   * - ``(has_resources quantidade resource1)``
     - Verifica estoque atual (não é vitória RMG por economia)
   * - ``(rmg_mark_ruin_discovered nome)``
     - Marca que o jogador atual descobriu a ruína (progresso de vitória)
   * - ``(rmg_ruin_discovered_by_self nome)``
     - Condição: jogador atual já descobriu a ruína
   * - ``(rmg_all_ruins_discovered_by_allies nome…)``
     - Vitória Exploração: facção aliada encontrou todas as ruínas
   * - ``(grant_resources 500 resource1 200 resource2)``
     - Recompensa de ruína
   * - `(set_map_flag nome)` / `(map_flag nome)`
     - Flag interna do mapa
   * - ``(cut_scene ID_voz)``
     - Anúncio de descoberta/captura
   * - ``(unit_lost casa índice tipo)``
     - Quartel capturado
   * - ``(add_units casa quantidade tipo)``
     - Reforço de guardas
   * - ``(timer intervalo [vezes])``
     - Verificação periódica / contagem regressiva de sobrevivência
   * - ``(personal_victory)``
     - Modo Sobrevivência: vitória individual sem eliminar outros sobreviventes



Implementação em ``soundrts/worldplayerbase/triggers.py``.


----


5. Voz e textos de UI
---------------------



.. list-table::
   :header-rows: 1

   * - ID
     - Chinês (original)
     - Uso
   * - 5425
     - Modo de vitória
     - Título do menu
   * - 5426
     - Conquista, eliminar todos os inimigos
     - Nome do modo
   * - 5427
     - Economia, coleta acumulada atinge meta
     - Nome do modo (prévia pode incluir ouro)
   * - 5428
     - Exploração, visitar cada ruína
     - Nome do modo
   * - 5429
     - Sobrevivência, resistir até o fim
     - Nome do modo
   * - 5430
     - Visitar cada ruína antiga
     - Linha de objetivo Exploração
   * - 5431
     - Ruína antiga
     - Nome de unidade/conceito (reservado)
   * - 5432
     - Quartel capturável
     - Nome de unidade/conceito (reservado)
   * - 5433
     - Ruína descoberta
     - cut_scene ao entrar na ruína
   * - 5434
     - Quartel ocupado
     - cut_scene de captura
   * - 5435
     - Coleta acumulada atinge
     - Linha de objetivo Economia (seguida de quantidade e «ouro»)
   * - 5436
     - Resistir
     - Linha de objetivo Sobrevivência
   * - 5437
     - Minutos
     - Linha de objetivo Sobrevivência
   * - 5451
     - Eliminar todos os inimigos
     - Linha de objetivo Conquista
   * - 5452
     - E manter a base principal
     - Sufixo da linha de objetivo Sobrevivência



Exemplo de linhas ``objective`` no mapa:

.. code-block:: text

   objective 5430                    ; Exploração
   objective 5435 3000 131           ; Economia: coletar 3000 ouro
   objective 5436 15 5437 5452       ; Sobrevivência 15 min e manter base
   objective 5451                    ; Conquista



----


6. Testes e regressão
---------------------


``soundrts/tests/test_randommap.py`` cobre:

- Modo Exploração gera ``ancient_ruin``, ``rmg_mark_ruin_discovered``, ``rmg_all_ruins_discovered_by_allies``, sem `(no_enemy_player_left) (victory)` de Conquista
- Modo Economia usa ``has_gathered``; objetivo Sobrevivência inclui `5452`; Conquista usa `5451`
- Economia / Sobrevivência também sem vitória automática por Conquista
- Quartel com guardas ``computer_only``, não ``neutral``
- `captured_barracks.capture_hp_threshold == 100`
- Código de compartilhamento com campo de vitória `:e:` / `:x:` etc. — ida e volta

Coordenadas: em ``soundrts/tests/test_yield_on_defeat_and_campaign_flags.py``,  
``test_has_entered_one_based_coords_not_confused_with_zero_based_grid_key`` evita regressão do bug de coordenadas de ruína em mapas Corredor.


----


7. Limitações e observações conhecidas
--------------------------------------


1. IA no modo Sobrevivência: computadores convidados ainda usam ``res/ai.txt`` padrão, sem script dedicado de «cercar sobrevivente»
2. Slot ``computerN``: com muitos POI pode alocar ``computer11`` etc.; se houver menos jogadores IA que slots, aviso «unknown player» (não afeta POI de humanos)
3. Exploração ≠ vitória militar: eliminar inimigos não vence; a facção aliada deve encontrar todas as ruínas (FFA conta só descobertas por você)
4. Vitória Economia: coleta acumulada de ``resource1`` (ouro) via ``has_gathered`` (sem inicial nem ``grant_resources`` de ruínas); madeira não conta; após atingir meta, vitória em até ~60 s
5. Vitória Exploração: após encontrar todas as ruínas, vitória em até ~30 s
6. Compatibilidade de mod: com nomes de recurso não padrão, ajuste ``\_economic_goal`` e ``grant_resources`` em ``resource1`` / ``resource2``
7. Exploração sem ``ancient_ruin``: se o mod não define ruínas, POI não é gerado e Exploração não pode vencer
8. Elementos Civ5 em campanha: comerciantes city-state, entrega de missões etc. — veja mapas de campanha e `携带物品与剧情交付说明.md <携带物品与剧情交付说明.htm>`_; independente do RMG


----


8. Índice de arquivos relacionados
-----------------------------------



.. list-table::
   :header-rows: 1

   * - Conteúdo
     - Caminho
   * - Jogador: menu de mapa aleatório
     - [随机地图功能说明.md](随机地图功能说明.htm)
   * - Regras: unidades POI
     - ``res/rules.txt`` (``ancient_ruin``, ``captured_barracks``)
   * - Gerador
     - ``soundrts/randommap.py``
   * - Menu
     - ``soundrts/randommap_menu.py``
   * - Gatilhos
     - ``soundrts/worldplayerbase/triggers.py``
   * - Lógica de captura
     - ``soundrts/combat/damage_effects.py`` (``capture_hp_threshold``); ordem padrão de captura ``can_capture`` → ``worldunit/world_order.py``
   * - Constantes de voz
     - ``soundrts/msgparts.py``
   * - Documentação HTML no jogo
     - ``doc/zh/mod/randommap.htm``
   * - Mapa aleatório em inglês
     - [../../en/player/random-map.md](../../en/player/random-map.htm)




----


9. Referência rápida: qual estilo jogar?
----------------------------------------



.. list-table::
   :header-rows: 1

   * - Quero experimentar…
     - Configuração sugerida
   * - Exploração e recompensas estilo HoMM
     - Vitória Exploração, Baús Muitos, Criaturas Média
   * - Disputar quartéis estilo HoMM
     - Qualquer modo de vitória; priorize Quartéis capturáveis
   * - Vitória por economia estilo Civ5
     - Vitória Economia, modelo Macro, recursos Concentrados
   * - Resistir até o fim estilo Civ5
     - Vitória Sobrevivência, modelo Rápido (10 min)
   * - RTS clássico de eliminação
     - Vitória Conquista (padrão)




----


*Versão do documento: corresponde ao RMG do SoundRTS 1.4.2.x; se campos do código de compartilhamento ou quantidades de POI mudarem, prevalecem ``soundrts/randommap.py`` e ``test_randommap.py``.*
