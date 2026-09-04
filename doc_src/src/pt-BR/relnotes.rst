
Notas de lançamento
==================

.. contents::

1.4.9.7
--------

**Mudança: camponeses voadores ainda contam como trabalhadores terrestres**

- **Problema**: as ``fee`` elementais do CrazyMod voam. O computador só punha camponeses terrestres em ``_workers``, tratava o primeiro aldeão terrestre das regras (``serf``) como trabalhador principal e o ``get`` recursava por ``keep`` / ``castle``, registando ``AI has trouble getting: 1 ['castle']``.
- **Mudança**: os trabalhadores da economia terrestre incluem camponeses de terra e voadores; barcos continuam excluídos. Sem camponeses vivos, prefere-se o tipo que um centro da cidade próprio pode treinar.
- **Alcance**: ``worldplayercomputer.py`` ``is_land_economy_worker`` / ``_primary_worker_type_name``; ``test_crazymod_pra1_ai.py``.

**Mudança: o computador ainda treina depois do edifício de produção atual estar pronto**

- **Problema**: com a torre de terra pronta, o computador travava ``get elemental_de_terre`` para sempre por um ``tour_du_feu`` numa linha posterior; a torre ficava ociosa e o stock acumulava.
- **Mudança**: a reserva total de ouro/madeira só vale se a linha ``get`` atual ainda precisa de um edifício de produção (cerco AoE2 na mesma linha). Edifícios de linhas posteriores só adiam um treino se essa unidade gastaria o stock.
- **Alcance**: ``worldplayercomputer.py`` ``_current_get_line_has_unpaid_production_building`` / ``_defer_plan_get_token``; ``test_crazymod_pra1_ai.py``.

**Mudança: o teleporte já não rebenta se aliados já estão no destino**

- **Problema**: ``a_passe_muraille`` (``effect teleportation``) chamava ``move_to(destino, None, None)`` nos aliados próximos. Quem já estava nessa casa fazia ``None - int`` no cálculo da carga e a habilidade inteira falhava.
- **Mudança**: mesmo quadrado com coordenadas ``None``: não calcula a carga. O teleporte ignora unidades já no destino.
- **Alcance**: ``worldunit/worldcreature.py`` ``move_to``; ``worldskill.py`` ``_execute_teleportation``; ``test_teleport_skill.py``.

**Mudança: uma derrota em solo já não regista um aviso falso de admin**

- **Problema**: após uma derrota a solo o jogador local sai de ``world.players`` (ou ``client.player`` é limpo). O ``is_admin`` seguinte falhava e registava ``couldn't be sure if this client is the admin of the game``.
- **Mudança**: se o jogador já não está ou a lista está vazia, trata-se como admin e não se avisa.
- **Alcance**: ``clientgame/game_interface_base.py`` ``is_admin``; ``test_is_admin_after_defeat.py``.

**Mudança: conversão de monges AoE2 usa dados por intervalo (regras)**

- **Problema**: no fim do canal a conversão acertava sempre; não havia aquecimento nem falhas por intervalo ao estilo Definitive Edition, nem sucesso garantido no máximo.
- **Mudança**: se a habilidade tem ``conversion_interval``, cada intervalo lança ``conversion_chance`` após ``conversion_min_intervals``. Uma falha continua o canto (``conversion_miss``). Em ``conversion_max_intervals`` o sucesso é garantido salvo ``conversion_fail_at_max 1`` (então ``conversion_fail``). O alvo pode mudar intervalos, probabilidade e resistência; Fé e o bónus de equipa teutão somam intervalos. Sem ``conversion_interval`` ainda acerta no fim do canal.
- **Alcance**: ``world_conversion.py`` ``conversion_roll_params`` / ``conversion_roll_after_interval``; ``worldorders/skills.py``; ``mods/aoe2/rules.txt``; ``test_conversion_interval_roll.py``.


1.4.9.6
--------

**Mudança: scripts da IA podem usar um cérebro adaptativo**

- **Problema**: o computador só executava linhas ``get`` de cima para baixo; ver cavaleiros não fazia treinar counters primeiro; autores não podiam ramificar o script conforme o reconhecimento.
- **Mudança**: ``brain plan|adaptive``. ``adaptive`` ainda completa todos os tokens da linha ``get`` atual, mas treina primeiro os melhores counters ``mdg_vs`` / ``rdg_vs`` contra inimigos reconhecidos. Novos saltos: ``if_enemy`` / ``if_not_enemy`` / ``if_attacked``. Expert e nightmare vanilla usam ``brain adaptive``. Beginner até advanced continuam em ``plan``.
- **Alcance**: ``soundrts/ai_brain.py``; ``worldplayercomputer.py`` ``_follow_plan``; ``res/ai.txt``; ``mod/aimaking.rst``.

**Mudança: o cérebro adaptativo injeta um contra treinável; expert ligado por padrão**

- **Problema**: ``adaptive`` só reordenava tipos já escritos na linha ``get``. O feudal expert de AoE2 é milícia + arqueiros, ver cavalaria não adicionava lanceiros; a maioria dos mods expert não define ``brain adaptive``.
- **Mudança**: Numa linha ``get`` militar, adiciona no máximo um tipo extra de ``can_train`` dos treinadores próprios que contra-ataca lutadores reconhecidos (não em aberturas só de aldeões). Expert e nightmare passam a ``adaptive`` em ``set_ai``; o script ainda pode ``brain plan``. Expert/nightmare vanilla de ``res/ai.txt`` saltam com ``if_attacked`` / ``if_enemy dragon|flyingmachine|knight`` após a primeira onda.
- **Alcance**: ``soundrts/ai_brain.py`` ``inject_counter_pairs``; ``worldplayercomputer.py`` ``set_ai`` / ``_follow_plan``; ``res/ai.txt``; ``mod/aimaking.rst``.

**Mudança: o cérebro adaptativo escolhe a mão por utilidade**

- **Problema**: Mesmo com ``adaptive``, cada tick ainda seguia o script, empurrava ataques e clicava a era ao mesmo tempo; um raid em casa ainda podia ``constant_attacks`` para fora, e com poucos aldeões treinava exército primeiro.
- **Mudança**: ``adaptive`` / ``utility`` pontua defender, era, eco, produzir e atacar a cada tick e usa só essa mão (a coleta não muda). Raids ou inimigos na casa do centro da cidade defendem; poupar para a era fica em casa e clica a era; poucos aldeões priorizam eco. ``brain plan`` ainda usa todas as mãos.
- **Alcance**: ``soundrts/ai_brain.py`` ``choose_utility_goal``; ``worldplayercomputer.py`` ``_play_body``; ``mod/aimaking.rst``.

**Mudança: o computador só divide ataques se a segunda frente ainda superar o ratio**

- **Problema**: O ataque mandava o grupo ocioso inteiro à primeira casa ordenada e voltava, então uma segunda ameaça ficava descoberta; dividir às cegas deixava as duas frentes abaixo de ``attack_ratio``.
- **Mudança**: ``assign_attack_groups`` abre uma frente só se a ameaça for estritamente maior que a inimiga × ``attack_ratio``. O que não cobre outra frente volta à primeira. No máximo duas frentes. Uma unidade não vai a dois sítios.
- **Alcance**: ``soundrts/ai_brain.py`` ``assign_attack_groups``; ``worldplayercomputer.py`` ``_eventually_attack``; ``test_ai_attack_split.py``.

**Mudança: o computador escolhe a mão do tick com uma árvore seletora**

- **Problema**: as pontuações de utilidade eram cinco números e um máximo, então a prioridade defender/eco inicial era difícil de ler e de estender com passos ordenados.
- **Mudança**: ``tick_behavior_tree`` é um seletor fixo: raid ou inimigo na casa do centro → defender; menos de 6 aldeões → eco; poupar para a era → era; abaixo da meta de aldeões → eco; ``constant_attacks`` com inimigos conhecidos → atacar; senão produzir. ``brain tree`` partilha a árvore com ``adaptive``. A coleta não muda.
- **Alcance**: ``soundrts/ai_brain.py`` ``BEHAVIOR_TREE``; ``worldplayercomputer.py`` ``brain``; ``mod/aimaking.rst``.

**Mudança: ataques deixam primeiro uma guarnição em casa**

- **Problema**: Depois de Atacar, os lutadores ociosos iam primeiro à casa inimiga com maior ameaça. Casa quieta (ameaça 0) ficava por último, o resto ia no raid e a base esvaziava. Defender só disparava depois de um raid já percebido.
- **Mudança**: ``peel_home_guard`` deixa um grupo em casa se houver centros. A guarda deve superar a ameaça inimiga em casa × ``attack_ratio`` (em casa quieta fica 1 unidade com ameaça > 0). Se o exército não cobre casa, todos ficam e não há raid. Com guarda, no máximo uma frente de raid (casa + raid = dois destinos); o resto do raid volta ao raid, não à guarda.
- **Alcance**: ``soundrts/ai_brain.py`` ``peel_home_guard`` / ``assign_attack_groups_with_home``; ``worldplayercomputer.py`` ``_home_base_places`` / ``_eventually_attack``; ``test_ai_attack_split.py``.

**Mudança: a sentinela de casa não é trocada por um recruta no tick seguinte**

- **Problema**: a guarnição voltava a partir os ociosos por id a cada tick. Um recruta novo com id menor virava sentinela e quem já estava no centro saía, deixando casa vazia até o recruta voltar.
- **Mudança**: ``_sticky_guard_order`` mantém primeiro quem já está em casa ou a caminho, depois os ``_home_guard_ids`` do tick anterior, depois os outros. Os extra em casa ainda podem sair quando casa já está coberta.
- **Alcance**: ``soundrts/ai_brain.py`` ``_sticky_guard_order`` / ``peel_home_guard``; ``worldplayercomputer.py`` ``_home_guard_ids``; ``test_ai_attack_split.py``.

**Mudança: o cérebro adaptativo reconhece antes de treinar exército**

- **Problema**: a árvore podia correr ``get`` militar antes de ver um lutador inimigo. Injetar counters e ``if_enemy`` precisam de scout; os exploradores já saíam a cada tick, mas a produção não esperava.
- **Mudança**: Depois de 6 aldeões, se não há inimigo de combate conhecido, o seletor usa ``scout``: continua o eco e envia o explorador, não executa o ``get`` do script e não ataca. Depois de avistar, ou ``SCOUT_THEN_PRODUCE_MS`` (60 s), volta a eco / atacar / produzir. Defender, eco inicial e era continuam primeiro.
- **Alcance**: ``soundrts/ai_brain.py`` ``_tree_scout`` / ``SCOUT_THEN_PRODUCE_MS``; ``worldplayercomputer.py`` ``_scout_sequence_started`` / ``_play_body``; ``mod/aimaking.rst``.

**Mudança: scripts expert/nightmare de AoE2 saltam conforme o reconhecimento**

- **Problema**: o motor já tinha ``if_enemy`` / ``if_attacked`` e o expert/nightmare vanilla de ``res/ai.txt`` usava; ``mods/aoe2/ai.txt`` continuava uma linha por idade, ver cavalaria ou arqueiros não mudava o feudal.
- **Mudança**: Em cada civ, expert e nightmare, após o primeiro ``attack`` feudal: ``if_attacked`` faz torres de vigia e lanceiros; ``if_enemy cavalry`` treina lanceiros; ``if_enemy archer_unit`` treina skirmishers. Depois voltam à linha de Castelo. Beginner até advanced continuam lineares.
- **Alcance**: ``mods/aoe2/ai.txt``; ``mod/aimaking.rst``.

1.4.9.5
--------

**Mudança: a exploração automática deixa de ser uma ordem imperativa**

- **Problema**: marcar a exploração como cabeça de fila imperativa fazia com que um movimento ou ataque normal ficasse na fila e nunca corresse; isso ia contra «retomar quando estiver ocioso».
- **Mudança**: ``AutoExploreOrder`` deixa de ser imperativa; as outras ordens assumem de imediato. O indicador ``auto_explore`` permanece ligado; ``decide()`` volta a emitir exploração quando ocioso. A IA continua a fazer stop antes de requisitar.
- **Alcance**: ``worldorders/computer.py``; comentários da fila.

**Mudança: Enter para exploração automática normal, Ctrl+Enter para imperativa**

- **Problema**: depois de a exploração deixar de ser imperativa, já não havia como manter um batedor a explorar até nova ordem.
- **Mudança**: Enter em ativar auto-exploração inicia exploração normal (substituída de imediato; retoma quando ocioso). Ctrl+Enter inicia exploração imperativa (ordens normais ficam atrás até parar, desativar ou outra ordem imperativa). A reemissão em idle mantém o modo (``auto_explore_imperative``).
- **Alcance**: ``enable_auto_explore`` / ``disable_auto_explore``; reemissão em ``decide()``; fila de ordens.

**Correção: Auto Scout do aoe2 nas linhas de batedor/águia, não no Mangudai**

- **Problema**: a linha da águia não tinha Auto Scout; o Mangudai tinha-o por engano.
- **Mudança**: linha ``eagle_scout`` (incluindo a águia asteca na Idade das Trevas) ``can_auto_explore 1``; ``mangudai`` ``can_auto_explore 0``. A linha de cavalaria de reconhecimento não muda. Este mod não tem Camel Scout; os camelos continuam sem.
- **Alcance**: ``mods/aoe2/rules.txt``.

**Correção: francos/bretões do aoe2 tinham melhorias de arqueiro no estábulo**

- **Problema**: besta, besta pesada, escaramuçador de elite (e um arqueiro a cavalo pesado a mais) apareciam no ``can_research`` do estábulo; a lista do campo de tiro estava vazia.
- **Mudança**: voltaram para o campo de tiro; o estábulo fica com pecuária e a linha de cavalaria. Francos/bretões continuam sem anel de polegar e sem CA pesada (DE). Identificadores: ``crossbowman`` ``arbalester``.
- **Alcance**: ``mods/aoe2/rules.txt`` campo de tiro e estábulo francos e bretões.


1.4.9.4
--------

**Correção: mudar a velocidade em Opções só valia após reiniciar**

- **Problema**: ``Game.run(speed=config.speed)`` congelava o valor na importação. Mudar de personalizado 6 para 1 em Opções gravava ``SoundRTS.ini``, mas solo/campanha ``run()`` ainda usava o 6 do arranque.
- **Mudança**: ler ``current_game_speed()`` ao iniciar a partida.
- **Alcance**: ``game.py`` ``run``; ``game_interface_base.py`` ``GameInterface``.

**Correção: entrar depois do anfitrião começar só emitia um bip**

- **Problema**: abrir o menu de ações de uma sala à espera, esperar o anfitrião começar e depois escolher Entrar ainda enviava ``register`` do instantâneo antigo. O servidor respondia ``register_error``; o cliente só emitia um bip.
- **Mudança**: se a partida já está ``started``, o servidor envia ``game_already_started`` e o cliente anuncia que a partida já começou. Observar não muda.
- **Alcance**: ``serverclient.py`` ``cmd_register``; ``clientservermenu.py`` ``srv_game_already_started``; ``GAME_ALREADY_STARTED`` (5834).

**Correção: a lista de salas avisava maps / invitations**

- **Problema**: na lista de salas (ou no submenu), ao o anfitrião começar ainda chegavam ``maps``, ``invitations`` e ``update_menu`` do átrio. A lista não é ``ServerMenu``, por isso as duas primeiras davam WARNING; ``update_menu`` redesenhava o instantâneo antigo e ainda oferecia Entrar.
- **Mudança**: menus aninhados ignoram ``maps`` / ``invitations``; a lista pede ``list_rooms`` em ``update_menu``.
- **Alcance**: ``clientservermenu.py`` ``_ServerMenu`` ``srv_maps`` / ``srv_invitations``; ``RoomListMenu.srv_update_menu``.

**Mudança: velocidade padrão do jogo em Opções**

- **Problema**: solo e campanha usavam ``speed`` de ``SoundRTS.ini``, mas Opções não mudava e ficava em 1.
- **Mudança**: Opções → **Velocidade padrão do jogo**: 1, 1.5, 2, 2.5, 3, 3.5, 4, e **Personalizado** para escrever 0.1–10. Gravado como ``speed``. O multiplayer ainda escolhe ao criar a sala.
- **Alcance**: ``config.py`` ``game_speed_type``; ``clientmain.py`` ``default_game_speed_menu``; ``DEFAULT_GAME_SPEED`` (5835–5837).

**Mudança: voz de acessibilidade e exibição em Opções**

- **Problema**: a voz de acessibilidade estava só no menu de jogo / F4, e o mapa só com Ctrl+F2.
- **Mudança**: Opções tem **Voz de acessibilidade** e **Exibição**; Enter alterna. Mesma config (``speech_enabled``, ``display_enabled``). Ctrl+F2 e F4 do menu continuam.
- **Alcance**: ``clientmain.py`` ``options_menu``; ``DISPLAY_TOGGLE`` (5838).


1.4.9.3
--------

**Correção: o espectador em multiplayer roubava ids de entidade**

- **Problema**: criar o jogador espectador consumia ``world.get_next_id()``, por isso unidades treinadas ou construídas depois tinham um id a mais do que na partida real. Ordens humanas escolhem por id, então o histórico ``all_orders`` acertava o alvo errado; a ordem de ``active_objects`` por id também podia divergir.
- **Mudança**: depois de criar o espectador restaura-se a sequência numérica de ids e marca-se ``pure_spectator``. Continua sem gastar ``world.random`` e sem ocupar um lugar de jogador.
- **Alcance**: ``game.py`` ``_create_spectator_player``; teste headless ``test_multiplayer_spectate.py``.

**Correção: o espectador repetia «está a observar» e depois ficava mudo**

- **Problema**: o atraso de catch-up oscilava no limiar e voltava a anunciar ``YOU_ARE_SPECTATING``. Restaurar o áudio só com fila 1 deixava o espectador ao vivo mudo (a fila fica muitas vezes em 2–3); setas/Tab/F10 pareciam mortas até voltar ao átrio.
- **Mudança**: anuncia-se uma só vez e restaura-se o áudio dentro do limiar; ``spectate_success`` tardio ignora-se em silêncio. Em jogo, ``spectator_joined`` / ``spectator_left`` passam a ser falados em vez de um WARNING.
- **Alcance**: ``game_interface_base.py``, ``worldclient.py``.

**Correção: ao entrar não havia casa e as setas não faziam nada**

- **Problema**: o espectador puro não tem unidades, por isso ``interface.place`` ficava vazio até PageUp / PageDown.
- **Mudança**: a câmara abre na casa inicial de um jogador real.
- **Alcance**: ``game_navigation._initial_observer_place``.

**Mudança: uma lista de salas no átrio, senha opcional para entrar e observar**

- **Problema**: pública/privada era confuso, e observar vivia noutro menu. «Pública» convidava toda a gente; privadas só por convite.
- **Mudança**: ao criar já não se escolhe pública/privada — depois do mapa/velocidade/trégua define-se senha ou salta-se. O átrio tem uma **lista de salas**: as que esperam podem-se juntar ou observar (o espectador espera o anfitrião começar), as já começadas observam-se. Salas com senha continuam na lista; juntar e observar pedem a senha. Convidados não precisam dela ao entrar. O anfitrião ainda pode convidar.
- **Alcance**: ``serverroom.py``, ``serverclient.py``, ``clientservermenu.py``, ``room_password.py``; teste ``test_open_rooms_lobby.py``.

**Correção: a espera de espectador não tinha sair e Esc não fazia nada**

- **Problema**: o menu de espera não aplicava ``make_menu()``, por isso as opções estavam vazias. Esc só confirma o último item.
- **Mudança**: ao entrar aplica-se «sair / deixar este jogo»; Esc confirma como no menu de convidado.
- **Alcance**: ``clientservermenu.py`` ``WaitingToSpectateMenu``.

**Correção: «está a observar» era cortado pelo anúncio da casa**

- **Problema**: no fim do catch-up, ``voice.info()`` punha ``YOU_ARE_SPECTATING`` na fila e o ``voice.item()`` seguinte interrompia.
- **Mudança**: fala-se com ``voice.alert()`` para terminar antes dos itens; continua a anunciar-se uma só vez.
- **Alcance**: ``game_interface_base.py`` ``_update_catch_up_audio``.


1.4.9.2
--------

**Mudança: ricochete por regras (glaive do Mutalisk)**

- **Problema**: o motor tinha splash circular e penetração em linha, mas não um salto para inimigos próximos com dano decrescente; o Mutalisk era de um alvo só.
- **Mudança**: ``rdg_bounce`` / ``mdg_bounce`` (saltos extra), ``*_bounce_range`` (0 = alcance de ataque), ``*_bounce_decay`` (percentagem conservada; 0 = 33, ex. 9→3→1). Só após o acerto primário; não fere aliados; não se acerta duas vezes na mesma cadeia; filtros ``rdg_targets``.
- **Alcance**: ``combat/bounce.py`` e combate; Mutalisk StarCraft ``rdg_bounce 2``, alcance 3, decay 33.

**Mudança: Lurker e Colossus StarCraft com penetração em linha**

- **Problema**: existia ``rdg_pierce_line`` estilo escorpião AoE2, mas o mod não tinha Lurker nem Colossus.
- **Mudança**: Lurker Den + Lurker / Lurker enterrado (largura 0.5); Robotics Facility / Robotics Bay + Colossus (largura 0.6). O Hydralisk transforma e a larva pode melhorar; a IA expert / nightmare constrói-os.
- **Alcance**: ``mods/starcraft/rules.txt``, UI, IA.

**Mudança: extras do escorpião AoE2 a 50 % após a armadura**

- **Problema**: os golpes extra de penetração usavam dano cheio, não o original (alvo apontado cheio, os outros metade após armadura, como flecha desviada).
- **Mudança**: ``rdg_pierce_decay`` / ``mdg_pierce_decay`` é a percentagem conservada nos extras após a armadura; 0 = 100 %. Escorpião / Escorpião pesado usam 50. Lurker / Colossus omitem e ficam cheios na linha.
- **Alcance**: ``combat/pierce_line.py``, ``hit_scale`` de ``receive_hit``; ``mods/aoe2/rules.txt``.

**Mudança: o ecrã de atributos mostra penetração em linha, ricochete e campos do pasto**

- **Problema**: penetração em linha, ricochete e o pasto AoE2 só existiam nas regras; o ecrã de atributos não os listava.
- **Mudança**: quando as regras estão definidas, lista os campos (omite os vazios):

  - Penetração: ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``, ``*_pierce_decay`` (0 mostra 100 %)
  - Ricochete: ``rdg_bounce`` / ``mdg_bounce``, ``*_bounce_range``, ``*_bounce_decay`` (0 mostra 33 %)
  - Pasto / geração: ``spawns_unit``, ``larva_spawn_time``, ``larva_cap``, ``spawn_player_cap``, ``spawn_immediate``; armazenável ``storable_resource_types``; ovelha ``claimable``; pastor ``can_herd``

- **Alcance**: ecrã de atributos, ``msgparts`` 5800–5821.

**Mudança: upgrades de linha reescrevem a fila de produção (AoE2 DE)**

- **Problema**: pesquisar Onagro só transformava mangonéis no campo; os que ainda estavam na fila da oficina saíam como mangonéis.
- **Mudança**: ao concluir, ordens ``train`` da mesma linha passam à forma nova; ao sair resolve-se o nível mais alto desbloqueado. Custo e tempo restante já pagos não mudam.
- **Alcance**: ``apply_unit_line_upgrade``, ``TrainOrder.complete``.

**Correção: exploradores águia astecas não viravam guerreiros águia**

- **Problema**: a linha da milícia tinha ``can_upgrade_to man_at_arms``; o explorador águia tinha ``can_upgrade_to`` vazio. Pesquisar guerreiro águia não transformava ``aztec_eagle_scout``.
- **Mudança**: ``eagle_scout`` → ``eagle_warrior`` → ``elite_eagle_warrior``; jaguar → elite. A águia asteca da Idade das Trevas ``is_a eagle_scout`` herda a cadeia.
- **Alcance**: ``mods/aoe2/rules.txt``.


1.4.9.1
--------

**Correção: o PC do CrazyMod em pra1 travava no hall**

- **Problema**: ``get chatelet 10 serf`` não terminava: o hall já possuído era tratado como soldado guardado para o quartel, e trabalhadores que o constroem contavam como quartel já possuído; o PC só imprimia ``vermine_nm_loop``.
- **Mudança**: linhas ``get`` de edifícios próprios completam; hall de trabalhador não é quartel. Summons por habilidade (``can_use_skill`` → ``termitiere``) contam como makers.
- **Alcance**: plano do PC e makers; a IA zerg do CrazyMod tira ``get larve`` extra (o hatchery gera larvas).

**Correção: habilidades sem alvo (larva) não faziam nada**

- **Problema**: ``effect_target`` vazio deixava ``UseOrder`` sem alvo (``a_larve`` do CrazyMod).
- **Mudança**: sem alvo / ``self`` aplica-se ao lançador.
- **Alcance**: ``worldorders/skills.py``.

**Mudança: unidades à distância do CrazyMod com velocidade de projétil**

- **Problema**: faltava ``rdg_projectile_speed``; os tiros acertavam na hora.
- **Mudança**: ``rdg_projectile`` / ``rdg_projectile_speed`` conforme o alcance.
- **Alcance**: ``mods/crazyMod9beta10/rules.txt``.

**Mudança: a IA de StarCraft usa os nomes do mod**

- **Problema**: ``ai.txt`` pedia ``peasant`` / ``footman`` / ``townhall`` do pacote base.
- **Mudança**: scripts terran/protoss/zerg com SCV, sonda, drone, fuzileiro, etc. ``addon_grants_train`` conta como maker (``get tank`` constrói a fábrica).
- **Alcance**: ``mods/starcraft/ai.txt`` e busca de makers.

**Mudança: mapas StarCraft com minerais/vespeno; o peasant inicial aparece**

- **Problema**: mapas com ``goldmines`` / ``woods``; ``peasant`` inicial não existe (``couldn't create an initial unit``).
- **Mudança**: mapas multi com ``mineral_field`` / ``geyser``; a tabela de facção mapeia ``peasant`` para SCV / sonda / drone.
- **Alcance**: mapas multi, ``equivalent_type``, parse inicial.

**Mudança: tempos e coleta StarCraft alinhados ao SC2 Faster**

- **Problema**: tempos e coleta ainda perto de SC1.
- **Mudança**: SC2 Faster (5 minerais, 4 gás / 2 esgotado, geyser 2250); projéteis à distância.
- **Alcance**: ``mods/starcraft/rules.txt``.

**Correção: o PC iniciante em jl1 alternava ouro e madeira**

- **Problema**: o feudal pedia ouro e madeira; cada turno roubava os mesmos camponeses, as viagens não acabavam.
- **Mudança**: não se rouba um trabalhador de outro recurso que ainda falta e está no teto ou abaixo.
- **Alcance**: ``_send_workers_toward_resources``.

**Correção: ``time_cost -5`` feudal saltava 2 e 8 na barra**

- **Problema**: o bónus aplicava-se duas vezes (jogador + ``_phase_bonus_pool``); o peão de 12s virava 2s e a barra ``0 1 3 4 5 6 7 9 10``.
- **Mudança**: o poço só guarda stats de combate; preenchem-se os ``completeness`` 0–10 saltados.
- **Alcance**: poço da era e ``ProductionOrder``.

**Correção: o primeiro desbloqueio de conquista anunciava também repetição**

- **Problema**: ``evaluate_new_unlocks`` escrevia ``once_keys`` antes de ``evaluate_repeat_completions``.
- **Mudança**: primeiro as repetições, depois os desbloqueios. O soldado raso continua com 0 slots de cartas (o tenente tem 1).
- **Alcance**: ``process_game_end_achievements``.

**Correção: pintar com a paleta de terreno da consola**

- **Problema**: a floresta sem ``is_dynamic 1`` ficava bloqueada. O pincel de mina largava a madeira. Pintar floresta depois de um lago procurava espaço como água.
- **Mudança**: floresta dinâmica; a paleta muda terra/água antes dos recursos; minas e árvores sem colisão.
- **Alcance**: aplicação da paleta, ``ensure_resources``; ``forest`` em base / AoE2 / StarCraft / CrazyMod.


1.4.9.0
--------

**Mudança: ``*_vs`` de splash aplica-se à unidade atingida**

- **Problema**: ``mdg_splash_vs`` / ``mdg_splash_decay_min_vs`` usavam o alvo apontado para mudar o poço inteiro.
- **Mudança**: ``mdg_splash`` / ``rdg_splash`` continua repartido ao acaso; ``*_splash_vs`` e ``*_splash_decay_min_vs`` aplicam-se a **cada unidade atingida pelo splash**. O splash de carga igual.
- **Alcance**: ``combat/splash.py`` e splash de carga.

**Equilíbrio: restaurar o dano DE da linha mangonel**

- **Problema**: 1.4.8.7 cortou ~25% como se o splash fosse cheio por alvo; o splash é um poço partilhado.
- **Mudança**: Mangonel / Onager / Siege Onager voltam a 40 / 50 / 75; ``mdg_splash`` igual ao corpo a corpo.
- **Alcance**: linha mangonel em ``mods/aoe2/rules.txt``.

**Equilíbrio: splash AoE2 igual ao ataque principal**

- **Problema**: mangonel já usava ``mdg_splash`` = corpo a corpo; canhão de bombardeio, galeões, dromon, navios tartaruga, Warwolf, elefantes/arietes e torres de bombardas tinham splash ``1`` (bandeira).
- **Mudança**: o poço de splash iguala ``mdg`` / ``rdg``; Logistica 9/12; torre de bombardas 120 e raio 0.5. Petardos e navios de demolição já estavam certos.
- **Alcance**: ``mods/aoe2/rules.txt``.

1.4.8.9
-------

**Correção: crash do PC ao requisitar barcos de pesca para andaimes em terra (``KeyError: deep_fish()``)**

- **Problema**: reparo de obras esquecidas requisitava qualquer ``Worker``, inclusive barcos em ``deep_fish``. ``_gathered_deposits`` só conta camponeses; o decremento crashava.
- **Mudança**: trabalhadores de água não vão a andaimes terrestres; a contagem de coleta só cai se a ordem for aceite e o depósito estava registado.
- **Alcance**: ``order()`` de reparo do PC.

**Correção: regras de perfuração do escorpião eram descartadas no load**

- **Problema**: ``rdg_pierce_line`` / ``rdg_pierce_width`` estavam nas regras e tabelas, mas ``Soldier``/``Creature`` não tinham o atributo; aviso e remoção.
- **Mudança**: campos de perfuração em ``Creature`` e nas instâncias; escorpião / escorpião pesado aoe2 mantêm os flags.
- **Alcance**: atributos de unidade e escorpiões aoe2.

**Correção: coletar peixe costeiro da memória de névoa avisava ao mover o objeto real**

- **Problema**: sem visão da água, o gather usava uma cópia de ``shore_fish``; ao esvaziar, ``delete()`` na cópia e o aviso ``Will move the real object instead of its memorized version``.
- **Mudança**: ``extract_resource`` na memória debita o depósito real.
- **Alcance**: coleta de depósitos (peixe costeiro, etc.).

**Correção: o menu de unidades (mago, etc.) crashava se ``player`` fosse None**

- **Problema**: ``EnableAutoExplore.is_allowed`` lia ``unit.player.is_human``; memória de névoa, cadáveres e unidades sem dono têm ``player is None`` e levantavam ``AttributeError``. ``_menu`` abortava o ciclo e perdiam-se ordens seguintes.
- **Mudança**: ``player`` em falta tratado como não humano, devolve False; mesma guarda em desativar auto-exploração e na do PC.
- **Alcance**: menu de ordens da unidade.

**Correção: crash do menu de ordens em EnableAutoExplore quando ``player`` é None (mago)**

- **Problema**: ``EnableAutoExplore.is_allowed`` lia ``unit.player.is_human``; memória de névoa, cadáveres e unidades sem dono têm ``player is None`` e lançavam ``AttributeError``. ``_menu`` capturava o loop inteiro e as ordens seguintes eram perdidas.
- **Mudança**: devolve False se ``player`` é None ou não é humano; mesma guarda ao desativar auto-exploração e na auto-exploração do PC.
- **Alcance**: menu de ordens (interruptor de auto-exploração).


1.4.8.8
-------

**Mudança: reverter «ataque corpo a corpo 0 vs armadura negativa»**

- **Problema**: permitir ``mdg 0`` contra ``mdf`` negativo tornava estranho o «ataque 0».
- **Mudança**: ``mdg == 0`` (sem explode) deixa de iniciar melee; mantém-se ``max(1, ataque−armadura)``. Arqueiros aoe2 sem ``mdg_range`` melee grátis.
- **Alcance**: portas de ataque / cache AI / arqueiros aoe2. Perfuração de escorpião e nerf de mangonel de 1.4.8.7 mantêm-se.

**Melhoria: atributos «tecnologias usáveis» filtradas às pesquisáveis da civ**

- **Problema**: ``can_use_tech`` muitas vezes inclui tecnologias únicas estrangeiras para efeitos, e os atributos as liam.
- **Mudança**: a lista mostra só o que esta civ pode pesquisar (mais ``team_share_research`` aliado e já pesquisado). Aplicação real e partilha aliada não mudam. Techs de arqueiro na serraria partilhada (base / crazyMod) continuam listadas.
- **Alcance**: lista de atributos e índices de navegação.


1.4.8.7
-------

**Melhoria: perfuração em linha de projéteis (escorpião), por regras**

- **Problema**: o escorpião AoE2 deve atravessar unidades na linha de tiro; só havia splash circular.
- **Mudança**: ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``. Golpes extra ao longo do segmento (sem o alvo principal). aoe2 scorpion / heavy scorpion com ``rdg_pierce_line 1``.
- **Alcance**: combate e escorpiões aoe2; splash continua só inimigos.

**Equilíbrio: menos dano de mangonel (sem fogo amigo)**

- **Problema**: o splash já não fere aliados; o dano base DE deixava a linha forte demais.
- **Mudança**: mangonel / onager / siege onager ~−25% (40→30, 50→38, 75→56).
- **Alcance**: ``mods/aoe2/rules.txt``.

**Melhoria: ataque corpo a corpo 0 pode acertar armadura negativa (arietes)**

- **Problema**: ``mdg 0`` era bloqueado antes da armadura; arietes com ``mdf -3`` não recebiam 3.
- **Mudança**: com ``mdg_range`` (ou explode) o melee é permitido se o dano pós-armadura > 0. Monges sem alcance melee não. Arqueiros / skirmishers / arqueiros a cavalo com ``mdg_range 1``. 0 vs 0 armadura continua mínimo 1.
- **Alcance**: portas de ataque / aoe2 arqueiros e arietes.


1.4.8.6
-------

**Correção: aoe2 Hand Cannoneer treinável no Campo de Arqueiros**

- **Problema**: Hand Cannoneers não apareciam na lista de treino; algumas civs os punham em ``can_research`` e só pediam Idade Imperial (sem Química).
- **Mudança**: ``hand_cannoneer`` exige ``imperial_age chemistry``; Campo genérico e shells das civs com a unidade listam em ``can_train`` (bizantinos, japoneses, francos, teutões, portugueses, malineses, …). Bretões, chineses, mongóis, vikings, vietnamitas, astecas e celtas continuam sem (árvore DE).
- **Alcance**: ``mods/aoe2/rules.txt`` Campo de Arqueiros e Hand Cannoneer.

**Correção: detalhe de «pode construir» resolve o shell da civ**

- **Problema**: o menu guarda nomes semânticos (ex. ``aoe_castle``). Abrir o detalhe lia o shell genérico: castelo bretão só Trebuchet até construir (Longbowman).
- **Mudança**: ``_show_unit_detail`` usa ``resolve_buildable_type`` (``aoe_castle`` → ``briton_castle``, etc.) para treino/pesquisa coincidirem com o edifício real.
- **Alcance**: detalhes de tipo a partir de pode construir / pode treinar.

**Correção: detalhe de tipo aplica bónus de idade / civ**

- **Problema**: milícia, arqueiro, etc. a partir de pode treinar mostravam só stats base, sem armadura de perfuração malinesa, alcance bretão e outros ``on_phase``.
- **Mudança**: o proxy reutiliza ``Player._phase_bonus_pool`` com ``Phase.apply_pool_*`` como em ``Player.add``.
- **Alcance**: detalhes de tipo (não tech/habilidade).


1.4.8.5
-------

**Melhoria: a caixa prefere militares; sprites amontoados encolhem**

- **Problema**: arrastar selecionava aldeões, soldados e edifícios juntos, ao contrário de Age of Empires II DE. Os PNG de ``ui/map`` são maiores que o ponto de colisão e tapam-se.
- **Mudança**: se a caixa tiver militares (``class soldier``), só militares; senão trabalhadores (``class worker``); senão edifícios. O clique não muda. Sprites encolhem quando muitos partilham a casa, com um ponto da cor da equipa.
- **Alcance**: caixa do rato Ctrl+F2 / F8 e desenho do mapa. Teclado e TTS iguais.

**Melhoria: animações spritesheet de unidades (Spine opcional)**

- **Problema**: ``ui/anims/`` só tinha documentação; Ctrl+F2 ficava em PNG estáticos ``ui/map``; ``go`` não mudava para ``walk``.
- **Mudança**: ``python tools/gen_unit_anims.py`` gera folhas 4 direções (idle/walk/attack/gather) para tipos móveis base e aoe2. ``go``/``use`` → ``walk``; ``dirs: 4`` no meta; ``backend: spine`` volta ao spritesheet na mesma pasta sem runtime.
- **Alcance**: ``game_unit_anim.py``, ``res/ui/anims/``, ``mods/aoe2/ui/anims/``. TTS / jogo às cegas inalterados.

**Correção: fazenda em auto-cultivo não mostra «iniciar auto-cultivo» a mais**

- **Problema**: com a fazenda já em modo auto-cultivo (inclusive entre replantios), a carta mostrava «iniciar auto-cultivo» e «parar cultivo» ao mesmo tempo.
- **Mudança**: se ``current_production_mode`` já é ``auto``, ocultar o início e manter só parar. Idem para ``auto_produce`` / ``manual_produce``.
- **Alcance**: menus ``AutoCultivateOrder`` / ``StopCultivateOrder`` e produção equivalente.

**Correção: ordem padrão do aldeão sobre fazenda é gather, não go**

- **Problema**: com aldeão selecionado, clique direito na fazenda emitia ``go`` em vez de ``gather``.
- **Mudança**: ``Worker.get_default_order`` verifica depósitos/edifícios coletáveis (fazendas com ``can_gather_building``) antes do ``go`` genérico para unidades vivas.
- **Alcance**: clique direito padrão do aldeão; alvos esgotados ou proibidos continuam com ``go``.

**Correção: aliases gratuitos de fazenda francos aoe2 não satisfaziam o requisito pai**

- **Problema**: após ``frank_horse_collar`` (``is_a horse_collar``, grátis), Arado pesado / Rotação ainda pediam ``horse_collar`` / ``heavy_plow``. Outras civs com o nome pai ok.
- **Mudança**: ``player.has()`` considera ``is_a`` / ``expanded_is_a`` das techs pesquisadas. Techs de fazenda grátis (bónus franco) iguais.
- **Alcance**: requisitos de pesquisa (aliases de civ).


1.4.8.4
-------

**Desempenho: vista de mapa Ctrl+F2 e simulação do mundo**

- **Problema**: com Ctrl+F2 e muitos computadores, pintar o mapa e atualizar o mundo não acompanhavam o tempo real. O caminho quente usava ``__getattr__`` de EntityView, reconstruía o nevoeiro a cada tick e reclassificava cada objeto e sprite. ``decide`` e o espaço das casas corriam demais.
- **Mudança**: a vista lê tipo e coordenadas do modelo (``stamp_map_view_cache``, ``_map_kind``). ``display_objects`` pinta por camadas; recursos saltam animação de unidade e barras de vida. O nevoeiro ignora objetos inalterados e guarda ``is_memory``, sprites e rótulos. ``memory_for_display`` é cacheado por tick. Unidades ociosas atrasam ``decide`` (``_next_decide_time``). Casas guardam ``used_square_space``. Atualizações de estado sem combate usam um caminho barato. O recorte por célula (``visible_cell_range``) foi testado; o ciclo de objetos ficou mais lento e não foi mantido.
- **Alcance**: vista Ctrl+F2, nevoeiro do cliente, atualizações do computador. TTS e regras de jogo inalterados.


1.4.8.3
-------

**aoe2: arte HUD / mapa e conjuntos de arquitetura DE**

- **Problema**: o mod Age of Empires II DE não tinha PNG próprios de carta de comandos nem de mapa; Ctrl+F2 caía na arte base. Civilizações compartilham tipos como ``militia``; um miliciano distinto por civ não bate com DE (conjuntos regionais, não IDs por civ).
- **Mudança**: camadas de recursos posteriores cobrem PNG de mesmo nome. aoe2 traz ``mods/aoe2/ui/icons`` e ``ui/map``. Geometria inicial: ``python tools/gen_aoe2_hud_icons.py``; PNG próprias não precisam do script. ``ui/architecture.txt`` agrupa civs (ex. ``western_european``); a busca é ``ui/map/<conjunto>/<tipo>.png``. Civs do mesmo conjunto compartilham arte. Depósitos e fauna neutros ficam no nível superior. RGB (``rim``, etc.) só afetam o gerador. Mods estilo StarCraft com tipos distintos por raça (``marine`` / ``zergling`` / ``zealot``) não precisam de subpastas de arquitetura.
- **Alcance**: carga de PNG HUD/mapa; arte aoe2 e ``architecture.txt``. TTS / jogo às cegas inalterados.


1.4.8.2
-------

**aoe2: pesca guiada pelas rules (peixe de costa / mar fundo)**

- **Problema**: o mod DE só tinha viveiros do barco de pesca. Não havia depósitos de costa nem de mar fundo; os aldeões não pescavam de terra. Cais e viveiro eram feudais, por isso não havia pesca na Idade das Trevas.
- **Mudança**: um depósito com ``gather_from_shore 1`` é recolhido por trabalhadores de terra numa casa terrestre adjacente. aoe2: ``shore_fish`` (200 comida) e ``deep_fish`` (225, só barcos). Redes de emalhar e o ritmo japonês cobrem as três fontes. Cais e viveiro na Idade das Trevas (transporte / galé / nau mercante ficam feudais).
- **Alcance**: recolha/IA/mapas aleatórios; rules aoe2 e mapas de água.

**Correção: recolher / construir / reparar / depositar soam no alvo**

- **Problema**: os ciclos estavam no aldeão, por isso o estéreo soava no trabalhador. A pesca de costa soava em terra.
- **Mudança**: ``noise_when_exploiting_*`` / ``noise_when_building`` (opcional ``noise_when_repairing``) no trabalhador; coordenadas no depósito ou edifício. ``store_resource1`` … no aldeão/barco **ou** armazém; se ambos existirem, ganha o trabalhador. Estéreo no armazém. ``store_resource_0`` está obsoleto.
- **Alcance**: todos os mods.

**Correção: mapas só com starting_squares usavam sempre um spawn fixo**

- **Problema**: os mapas multiplayer AoE2 DE listam ``starting_squares`` e omitem ``starting_units`` (predefinições da raça). Slots vazios perdiam a casa, por isso o centro da cidade / aldeões da facção usavam sempre ``starting_squares[índice_do_jogador]``. ``random_starts 1`` não baralhava.
- **Mudança**: cada slot de spawn guarda a sua casa. Com inícios aleatórios por omissão essas casas são baralhadas e as predefinições da raça caem na sorteada. ``random_starts 0`` continua a ordem da lista.
- **Alcance**: todos os mapas que usam ``starting_squares`` sem unidades por slot (incluindo aoe2).


1.4.8.1
-------

**Melhoria: alcance ao reivindicar ovelhas alinhado ao AoE2 DE (4 m + raios de colisão)**

- **Problema**: as ovelhas usavam ``claim_range 12000`` (um quadrado inteiro de 12 m), muito além do raio de busca do DE (~4 casas). O quadrado de 12 m é uma célula de navegação para jogo sem visão; as coordenadas continuam contínuas, cerca de 1 m por casa. A reivindicação comparava só os centros, sem raios de colisão.
- **Mudança**: as ovelhas usam ``claim_range 4000`` (~4 m). Reivindicar/roubar é bordo a bordo: distância entre centros ≤ ``claim_range`` + ambos os ``radius`` (175 mm cada se houver colisão).
- **Alcance**: rules de base e ovelhas aoe2; todo o gado ``claimable`` com ``claim_range``.

**Correção: nomes numéricos de gravações/replays eram lidos como IDs do tts.txt**

- **Problema**: ao renomear uma gravação para ``1`` dizia «estás» / «you are» (id 1 do tts.txt) em vez do número 1. O mesmo nos replays.
- **Mudança**: nomes escolhidos pelo jogador (gravações e replays, incluindo a confirmação ao apagar) usam ``literal_text_msg``. Nomes automáticos ``replayN_timestamp`` e ficheiros antigos só com carimbo de data longo continuam a ler a hora e o índice.
- **Alcance**: menus de carregar jogo e de replay.


1.4.8.0
-------

**Correção: a TTS do buff ao apanhar lia milipontos de vida**

- **Problema**: no td2, apanhar uma espada dizia dano corpo a corpo +7000000. As rules ``stat mdg`` / ``v 7000`` guardam 7_000_000 milipontos; o anúncio tratava esse valor interno como o de ecrã.
- **Mudança**: os buffs temporários dividem as stats de precisão (hp, mdg, etc.) por ``PRECISION`` antes da TTS. Os acumuladores de produção ficam em unidades de ecrã.
- **Alcance**: TTS ao ganhar um buff em todos os mods.

**Computador: atrair presas que contra-atacam ao depósito de comida antes de as matar**

- **Problema**: aldeões ociosos atacavam animais ``is_huntable`` no sítio. Javalis com ``pursue_attacker`` lutam no campo. Não havia «bater uma vez e arrastar para casa».
- **Mudança**: um caçável que não é ``herdable`` / ``claimable`` e tem ``pursue_attacker`` (javalis aoe2) leva um golpe; o aldeão corre para um edifício que guarda o recurso 3 (centro da cidade, moinho, etc.) e mata-o lá. Caçáveis que não contra-atacam (veados) continuam a ser mortos no sítio. As ovelhas continuam a ser levadas ao depósito. Sem nomes de tipo fixos. O corredor não se vira a lutar a caminho.
- **Alcance**: jogadores computador; mods com esses flags (incluindo aoe2).

**Mapeamento de teclas: estado do recurso 4**

- **Problema**: o aoe2 já ligava a pedra a Shift+X, mas o catálogo de reatribuição só listava os recursos 1–3.
- **Mudança**: os catálogos global e clássico incluem o estado do recurso 4. No aoe2 o predefinido continua Shift+X.
- **Alcance**: reatribuição de teclas; id TTS 5508.

**Teclas clássicas: Shift direito+C / B copiam a voz secundária**

- **Problema**: as teclas em camadas podiam copiar a voz secundária para a área de transferência; o ``legacy_bindings.txt`` clássico não tinha essas teclas.
- **Mudança**: ``res/ui`` e ``mods/aoe2/ui`` ``legacy_bindings.txt`` acrescentam Shift direito+C copiar e Shift direito+B acrescentar a voz secundária.
- **Alcance**: esquema de teclas clássico.


1.4.7.9
-------

**Melhoria: reivindicar/roubar ovelhas anuncia a civilização e se é inimigo**

- **Problema**: reivindicar ou roubar uma ovelha dizia sempre «ovelha , reivindicado», sem saber que civilização a levava.
- **Mudança**: a reivindicação própria continua curta. Se um inimigo a leva (e vês quem reivindica) diz-se «ovelha reivindicada bizantinos , inimigo»; um aliado nomeia a civ e «aliado». Mods de uma só facção omitem o nome da civ mas ainda dizem inimigo/aliado. No nevoeiro, se não vires quem reivindica, não há anúncio.
- **Alcance**: TTS do cliente; todos os mods com gado ``claimable`` (incluindo ovelhas aoe2).

**Melhoria: capturar edifícios anuncia o nome e a quantidade (igual às mortes)**

- **Problema**: a captura só tocava um som, sem dizer que edifício tinha sido tomado.
- **Mudança**: se perdes o teu: «1 câmara municipal ocupado». Se tomas um inimigo: «1 centro da cidade capturado». Vários do mesmo tipo no mesmo momento: «2 quartéis ocupados / capturados». A quantidade segue as mortes: tipos com número incluem a contagem; ``no_number`` únicos omitem o «1». Ver outros capturar continua a ser só o som.
- **Alcance**: TTS do cliente; todos os edifícios capturáveis (incluindo muros, portões e centros da cidade aoe2).


1.4.7.8
-------

**Correção: o servidor ainda listava a partida em curso depois de terminar**

- **Problema**: no fim de uma partida multijogador, o cliente por vezes não enviava ``quit_game`` (erro na TTS da pontuação, falha ao carregar o mapa, ou o comando só ia depois do resumo). Se alguém ficasse no lobby, a sala permanecia na lista em curso / espetar.
- **Mudança**: a sala é cancelada antes da TTS da pontuação; ao sair da UI da partida envia-se ``quit_game`` outra vez se ainda não tiver sido enviado. Comandos do lobby e uma limpeza do servidor fecham salas sem ninguém a jogar. Um ``quit_game`` duplicado no lobby é ignorado (sem aviso).
- **Alcance**: servidor e cliente multijogador.

**Empacotamento: a instalação Windows já não duplica Tcl/Tk**

- **Problema**: ``tcl8`` / ``tcl8.6`` / ``tk8.6`` existiam na raiz da instalação e também em ``share/``, cópias idênticas, cerca de 5 MB a mais.
- **Mudança**: fica só a cópia do cx_Freeze em ``share/``; a janela de atualização prefere ``share/``.
- **Alcance**: pacote Windows.


1.4.7.7
-------

**Motor: salva de guarnição do edifício (por regras, independente da arma)**

- **Problema**: centros da cidade aoe2 vazios ainda disparavam (dano à distância do edifício), ao contrário da DE. As +5 salvas teutónicas com o centro vazio e Tigui maliano +8 não se exprimiam nas rules. Um campo chamado arrows não serviria a um edifício de canhão.
- **Mudança**: com ``garrison_shots 1``, tiros = ``base_shots`` + unidades de guarnição que disparam, teto ``max_garrison_shots`` (predefinição 10). Um edifício vazio com ``base_shots 0`` não dispara; teutões ``base_shots 5``; Tigui usa o ``effect bonus base_shots 8`` já existente. O tipo de dano continua a ser o ``rdg`` do edifício (flecha, canhão ou outro à distância). A salva é do edifício, não tiros de passageiros. O motor não testa nomes de civilização.
- **Alcance**: todos os mods; os centros da cidade aoe2 ativam-no. Castelos e torres continuam a disparar vazios.

**aoe2: malianos**

- **Problema**: o mod não tinha a civilização maliana.
- **Mudança**: décima terceira civ. Edifícios −15 % de madeira excepto quintas; milícia/lanceiros do quartel +1/+2/+3 de armadura perfurante Feudal/Castelo/Imperial (não Gbeto); aldeões entregam +10 % de ouro; pesquisa universitária de equipa 80 % mais rápida (``team_on_phase`` + ``time_cost -44%``). Unidade única Gbeto; tecnologia de castelo Tigui (200 comida 300 madeira, ``base_shots`` +8 no centro); tecnologia imperial Farimba (corpo a corpo de cavalaria +5). Introdução ``8532``.
- **Alcance**: mod aoe2.

**aoe2: cascas de edifícios de civ sem título de estilo**

- **Problema**: cascas como ``malian_barracks`` não herdavam título, por isso o edifício acabado não tinha nome. Quintas/centros teutónicos e o mosteiro bizantino também não tinham ``is_a`` em ``style.txt``.
- **Mudança**: essas cascas apontam com ``is_a`` para o edifício genérico; um teste exige títulos nas cascas seguintes.
- **Alcance**: estilo UI aoe2.


1.4.7.6
-------

**aoe2: bónus das doze civilizações alinhados com a Definitive Edition atual**

- **Problema**: os bónus civ ainda seguiam um snapshot ~2022 (p.ex. chineses 10/15/20 % nas tecnologias, centros da cidade 10 de população), não a DE atual. O motor também não exprimia pesquisa partilhada de equipa, roubo de rebanho vigiado nem descontos de custo por idade.
- **Mudança**: as doze civs (bretões, francos, chineses, mongóis, bizantinos, japoneses, teutões, vikings, vietnamitas, portugueses, astecas, celtas) usam bónus e bónus de equipa DE atuais. Onde as rules não chegavam, o motor ganhou campos sem nomes de civ: ``team_on_phase``, ``grant_tech_on_phase``, ``team_share_research`` (tecnologia e edifícios anfitrião opcionais, p.ex. escaramuçador imperial vietnamita para aliados), ``team_farm_food_pct``, ``reveal_enemy_town_centers``, ``research_cost_zero_slot`` / ``research_time_percent``, ``gather_byproduct``, resistência de equipa à conversão, etc.
- **Alcance**: mod aoe2; os novos campos de raça servem outros mods.

**Motor: reclamar / roubar rebanhos (por regras)**

- **Problema**: a posse por proximidade ``claimable`` não estava no ciclo da unidade. O «não se rouba rebanho vigiado / rouba-se se não estiver protegido» do AoE2 não tinha flags.
- **Mudança**: animais ``claimable`` neutros passam a um jogador não neutro próximo. O rebanho com dono pode ser roubado: qualquer um se não houver guarda; bloqueado se houver uma unidade viva do dono; raça ``herdable_steal_ignore_guards 1`` ignora essa guarda; ``herdable_steal_protected 1`` (predefinição 0) bloqueia esse bónus nos teus próprios animais. O motor não testa nomes de civilização.
- **Alcance**: todos os mods; os celtas aoe2 ativam ambos os flags.

**aoe2: início na Idade das Trevas como AoE2 (incluindo chineses)**

- **Problema**: o início era 1 aldeão, uma casa e sem batedor. Os chineses tinham 4 aldeões (+3 sobre uma base de 1), não os 6 + batedor da DE.
- **Mudança**: civs padrão: centro da cidade + 3 aldeões + cavalaria de exploração. Chineses: 6 aldeões + batedor (−50 madeira, −200 comida, centro 15 de população). Astecas: 3 aldeões + batedor águia, +50 ouro. Sem casa inicial (população do centro). Os scripts de campanha e aldeões extra da dificuldade da IA não mudam.
- **Alcance**: ``starting_units`` / ``starting_resources`` predefinidos das raças aoe2.

**aoe2: textos do seletor de facção em todos os idiomas do mod**

- **Problema**: as fichas G das civilizações só existiam em inglês e chinês.
- **Mudança**: ids ``8520``–``8531`` em todos os pacotes UI aoe2 (en, zh, de, fr, es, it, ru, be, pl, cs, sk, pt-BR, vi).


1.4.7.5
-------

**Correção: a ordem padrão do trabalhador num edifício danificado não era reparar**

- **Problema**: a alteração da caça fazia ``go`` em qualquer alvo vivo com dono. Edifícios aliados danificados (e estaleiros) caiam nesse ramo, por isso o aldeão andava em vez de reparar.
- **Mudança**: resolver primeiro a reparação padrão em estaleiros e alvos ``is_repairable`` com ``hp < hp_max`` (continua a exigir ``can_repair`` / ``can_build``; inimigos excluídos). Edifícios intactos, fauna e inimigos continuam ``go``.
- **Alcance**: ordem padrão dos trabalhadores em todos os mods.


1.4.7.4
-------

**Desempenho: velocidade F no início (loop do cliente)**

- **Problema**: com muitas unidades locais, o primeiro decode OGG de passos/ambiente podia travar um quadro e perder o tick seguinte, baixando a velocidade relativa de F.
- **Mudança**: esvaziar notifies do servidor com orçamento de ~8 ms (deixar ``voila`` para o quadro seguinte); repartir a animação; decodificar passos/ambiente (prioridade ≤ −10) em segundo plano e não roubar canais do mixer para esses sons.
- **Alcance**: cliente local, todos os mods.

**Limite de SFX: tiro/acerto, confirmação de ordem, passos, noise em loop**

- **Problema**: em combates densos o fio principal ainda processava sons que o mixer não consegue empilhar.
- **Mudança**: tiro/acerto no máximo 16 por tick (8 por quadrado); ``order_ok`` / ``order_impossible`` 2 por tick; passos 8 por onda de animação (4 por quadrado); noise em loop no máximo 3 por tipo de unidade/edifício (sem teto global de tipos). Morte, queda, proporção de PV e alerta de unidade própria atacada não são limitados.
- **Alcance**: cliente local, todos os mods.

**Correção: por vezes não tocavam acerto, proporção de PV nem morte**

- **Problema**: proibir decode OGG de combate no fio principal evitava engasgos, mas silenciava o primeiro acerto se o som ainda não estava em cache.
- **Mudança**: não descodificar no caminho de reprodução; pré-carregar acerto / ``proportion_*`` / morte quando o tipo aparece; fila curta de repetição se o decode ainda corre. O esvaziamento em rajada mantém-se.

**Correção: após o objetivo não se anunciava o quadrado inicial**

- **Problema**: a primeira atualização da câmara saltava a fala para não travar, guardava o anúncio e nunca o reproduzia.
- **Mudança**: anunciá-lo uma vez depois de esvaziar eventos (coordenadas, terreno e resumo de camponeses/casas/centro da cidade/mina).

**Correção: o quartel base treinava arqueiro negro em vez de arqueiro**

- **Problema**: a linha de treino ao estilo AoE2 tratava qualquer ``can_upgrade_to`` como a forma que o prédio devia treinar. Arqueiro→arqueiro negro (morph com torre de magos) não é linha de quartel.
- **Mudança**: só formas ``line_upgrade`` / ``no_auto_upgrade`` alteram o menu de treino (milícia→homem de armas fica nas rules do aoe2). O quartel base continua a treinar arqueiro; o arqueiro negro continua a ser uma melhoria de arqueiros existentes. Um mod não deve reescrever os menus do jogo base nem de outros mods.

**Correção: Opções → biblioteca de voz secundária lia 5762 e 5778**

- **Problema**: ao abrir o editor da voz secundária em Opções, os ids ``5762`` / ``5778`` eram lidos como dígitos, não como «biblioteca de voz secundária» e a dica das teclas.
- **Mudança**: resolver msgparts antes de falar. O editor é uma lista de submenu normal; o feedback usa a voz do menu para um canal secundário mudo não parecer um ecrã vazio.


1.4.7.3
-------

**Desempenho: contagens e memo do turno da IA**

- **Problema**: com muitos computadores, ``Computer.play`` varría ``nb`` / ``future_nb`` e recalculava prédios/reserva de madeira da linha get várias vezes por turno.
- **Mudança**: índice de tipos por turno da IA; ``check_type`` mais barato; memo das consultas do plano (makers pendentes, madeira, etc.), invalidado após treino/construção. Sem mudar o combate/percepção.
- **Alcance**: computadores em todos os mods.

**aoe2: IA por idade — treina e ataca**

- **Problema**: ``mods/aoe2/ai.txt`` misturava eras numa só linha get; a poupança de comida adiava o exército e o watchdog saltava gets incompletos.
- **Mudança**: ondas Dark / Feudal / Castle; watchdog não corta a eco da Idade das Trevas; exército feudal da linha atual não fica preso pelo castelo seguinte; após o castelo, reserva madeira para a oficina de cerco sem congelar fazendas. Scripts e dificuldades atualizados.
- **Nota**: a subida de idade pode partilhar o motor, mas a poupança/ondas do aoe2 seguem as próprias rules — outros mods com eras não precisam do mesmo comportamento.

**Correção: res padrão construía quartel e não treinava**

- **Problema**: a lógica de «maker não pago» do aoe2 tratava makers unidade→unidade (``darkarcher``) e estaleiros em mapa terrestre como prédios a poupar, adiando infantaria/arqueiros.
- **Mudança**: só prédios reais; em mapas sem água, ignora unidades/docas aquáticas. O res padrão treina e ataca com o quartel pronto; a reserva de madeira da oficina no aoe2 mantém-se.

**Correção: computadores presos na get feudal — não chegam a castelo / aríetes**

- **Problema**: o plano mantém de propósito o exército feudal atual sem clicar Idade dos Castelos. Se as tropas morrem na base inimiga, o get nunca completa. Ao mesmo tempo ``_watchdog_should_wait`` tratava a madeira da oficina seguinte e comida/madeira de treino como «ainda a progredir», reiniciando o temporizador, pelo que o watchdog nunca saltava a get feudal e a onda de castelo (ferreiro, Idade dos Castelos, oficina, aríetes) não começava.
- **Mudança**: quando a get atual já não precisa de uma idade mas uma onda posterior ainda precisa de castelo, o temporizador só espera prédios de produção da linha atual por pagar (quartel / campo de tiro, etc.) — não a madeira da oficina nem o treino. Gets de cerco continuam a pausar corretamente com oficina pronta e madeira de aríete em falta.
- **Alcance**: computadores em todos os mods. Qualquer script aoe2 «exército feudal → tropas/cerco de castelo» beneficia.

**Correção: computadores não levam ovelhas próprias ao centro da cidade antes de abater**

- **Problema**: muitos mods (incluindo aoe2) deixam ``can_herd 0`` e usam ``claimable``. A IA não enviava ovelhas próprias como unidades controláveis ao depósito de comida e metia-as em ``auto_explore`` / ondas de ataque, pelo que vagueavam ou morriam no campo em vez de deixar ``food_livestock`` no centro da cidade.
- **Mudança**: gado próprio (``herdable`` / ``claimable``) faz ``go`` sozinho para um prédio que guarda comida; aldeões só abatem lá e depois recolhem. Ovelhas claimable neutras: primeiro ``go`` para reivindicar. Ficam de fora de exploradores e lutadores idle. Não exige ``can_herd``; o caminho de pastoreio mantém-se.
- **Alcance**: computadores em todos os mods; ovelhas aoe2 e pastagens mongóis beneficiam.


1.4.7.2
-------

**aoe2 / motor: empacotar / desempacotar o trabuco (por regras) + progresso proportion**

- **Problema**: unidades de cerco «packable» só atrasavam o primeiro tiro após mover; não havia estado real nem ``proportion_*``.
- **Mudança**: regras ``packable``, ``unpack_time`` / ``pack_time``, opcionais ``packed_mdf`` / ``packed_rdf``, ``spawn_packed``. Empacotado = só mover; desempacotado = só atacar. Progresso ``completeness`` → ``proportion_*``. UI: empacotar / desempacotar.
- **Docs**: ``mod/modding.htm``.

**aoe2: correção de Coleira / Arado pesado / Rotação de culturas duplicados em aldeões**

- **Problema**: o ``can_use_tech`` do camponês listava as techs genéricas do moinho e os aliases francos de custo 0 (``frank_horse_collar`` etc.). Os aliases compartilham o título, então a tela de atributos lia cada nome duas vezes.
- **Mudança**: aldeões não francos ficam só com ``horse_collar`` / ``heavy_plow`` / ``crop_rotation``. Francos usam ``frank_villager``, só com os aliases grátis.

**Correção: ``gather_byproduct`` (ex. Papel-moeda) não aparecia nos atributos**

- **Problema**: o efeito é um terno (depósito, ritmo). A UI lia como par, usava o depósito como valor, perdia o ritmo e escondia a linha.
- **Mudança**: mostram-se depósito, recurso secundário e ritmo por segundo (Papel-moeda: depósito de madeira, ouro, +0.014/s). As rules continuam com o tipo de depósito (ex. ``wood``).

**Novidade: ouvir os bônus de civilização ao escolher a facção**

- As setas leem só o nome. Com ``intro``, pressione **G** para um submenu e use cima/baixo frase a frase (Enter repete; Esc volta). Sem ``intro``, sem mudanças.
- aoe2: as doze civs têm texto em inglês e chinês.

**aoe2: pastores e caçadores usam depósitos de carcaça separados (orientado a rules)**

- **Problema**: ovelhas e cervos/javalis compartilhavam ``food_carcass``, então o bônus de pastores britânicos e o de caçadores mongóis aceleravam os dois trabalhos.
- **Mudança**: ``herdable`` deixam ``food_livestock``; a caça continua com ``food_carcass``. Britânicos: ``gather_time_food_livestock -20%``. Mongóis: ``gather_time_food_carcass -29%``. O motor casa ``gather_time_<depósito>`` e a caça da IA a partir das rules (``food_deposit`` / ``is_huntable``), sem hardcode de civ.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novidade: ``pursue_attacker`` — javalis perseguem entre casas (estilo AoE2)**

- **Problema**: javalis contra-atacavam em ``guard``, mas ``AttackAction`` só perseguia entre casas no modo ``chase``, então ao sair o aldeão a perseguição parava e não dava para atrair ao centro da cidade.
- **Mudança**: o flag de rules ``pursue_attacker 1`` mantém o ataque seguindo entre casas (sem exigir inimizade diplomática). Javalis nas rules base e aoe2 ativam; cervos/ovelhas continuam com ``flee_on_hit``.
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novidade: ``pursue_leash_range`` — soltar agressão ao abrir distância**

- **Problema**: só com ``pursue_attacker``, ``last_attacker`` mantinha a perseguição mesmo com grande distância (não o deaggro por LOS do AoE2).
- **Mudança**: inteiro de rules ``pursue_leash_range`` (mm; ``0`` = sem limite). Além disso, esquece o atacante, para o ataque e volta para casa. Javalis usam ``48000`` (~4 casas).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.

**Novidade: ``claimable`` + pasto (reivindicação AoE2 / pasto AoE4, por rules)**

- **Problema**: a condução só seguia sem mudar dono; não havia reivindicação por proximidade nem pastos que geram gado.
- **Mudança**: animais ``claimable`` neutros passam a qualquer unidade não neutra próxima (``claim_range``; ``can_herd`` continua separado). Edifícios: ``spawns_unit`` + ``spawn_player_cap`` / ``spawn_immediate`` (aoe2: ovelha ``claimable``; ``pasture`` mongol).
- **Docs**: ``player/hunting.htm``, ``mod/modding.htm``.


1.4.7.1
-------

- **Problema**: o canteiro (``BuildingSite``) expunha o menu de treino/pesquisa do prédio-alvo, então um quartel podia treinar antes de ficar pronto.
- **Mudança**: canteiros inacabados não listam treino/pesquisa e não podem produzir.
- **Alcance**: todos os mods (incluindo aoe2).
- **Código / testes**: ``world_build_rules.py`` (``is_unfinished_building``, ``effective_can_train`` / ``effective_can_research`` / ``building_can_operate``); ``test_can_train_upgrade.py``.

**Correção: ao concluir, o prédio nasce com o HP de bônus, não para ser consertado**

- **Problema**: na conclusão o HP atual usava o ``hp_max`` da classe (ex. quartel 1200), enquanto o ``hp_max`` da instância já incluía bônus (bizantinos Idade das Trevas +10% → 1320). Aldeões consertavam a «falta».
- **Mudança**: na conclusão usa-se o ``hp_max`` da instância (menos dano durante a obra). Como no AoE2: termina com HP cheio com bônus, não se repara depois.
- **Alcance**: todos os mods.
- **Código / testes**: ``worldcreature.py`` (``BuildingSite._complete_construction``); ``test_z5_byzantine_barracks_hp.py``.

**aoe2: civilização Celtas; campanha de William Wallace como celtas**

- Celtas: UU Saqueador woad; UT Fortaleza / Furor Céltica; bônus de infantaria, lenhadores e cerco.
- Campanha Wallace: jogador ``default_faction celts``; PCs ingleses ``faction britons``.
- Mapas: ``computer_only … faction <nome> …`` atribui civilização por PC. Ver ``mod/mapmaking``.


1.4.7.0
-------

**Melhoria: SFX de passagem/bloqueio sobrepõe as coordenadas na navegação do mapa**

- **Problema**: com as setas, o som de passagem (ex. ponte) ou de bloqueio ia na fila de voz e terminava antes das coordenadas / nomes, com atraso perceptível.
- **Mudança**: esses efeitos tocam de imediato no mixer de SFX; coordenadas e nomes continuam na fila de voz, começando juntos.
- **Alcance**: navegação normal, troca de casa no zoom, bloqueio em primeira pessoa.
- **Código**: ``clientgame/game_navigation.py`` (``_play_movement_sfx``), ``clientgamefocus.py``, ``clientgame/game_audio.py``.


**Novidade: recompensa de recurso ao matar ``kill_resource_vs`` (sem ouro fixo)**

- **Uso**: ao matar um tipo correspondente, o matador ganha um **recurso escolhido** (ex. Chefes: ouro em aldeões); o motor **não** fixa «ouro» nem ``resource1``.
- **Sintaxe**: ``effect bonus kill_resource_vs <tipo> <recurso> <quantidade>``, ex. ``kill_resource_vs peasant resource1 5``. Recurso ``resourceN`` ou alias ``gold`` / ``wood`` / ``food`` / ``stone``. Match via ``type_name`` / ``is_a``.
- **Armazenamento**: ``tipo_vítima → { resourceN: quantidade }``; ao matar, ``store`` e evento ``resourceN_reward``.
- **aoe2**: Chefes usa ``kill_resource_vs … resource1 5`` (aldeão / carroça / navio / monge).
- **TTS / UI**: «bônus de recurso ao matar vs» (sem chave crua ``kill_gold``).
- **Docs**: ``mod/modding``. Código / testes como na versão inglesa.


1.4.6.9
-------

**Novidade: previsão de projéteis por regras e velocidade de voo por via**

- **Voo**: ``rdg_projectile_speed`` / ``mdg_projectile_speed`` são **velocidades** (casas/s), não «segundos de voo»; só com o flag ``*_projectile`` correspondente. Tempo até o impacto = distância ÷ velocidade. ``projectile_speed`` compartilhado e ``*_delay`` legado estão obsoletos (migrados no carregamento).
- **Previsão**: ``projectile_lead 0|1`` (só projéteis à distância). Sem ``ballistics`` fixo.
- **Tech / UI**: ``effect bonus projectile_lead 1``; ``effect info``.
- **Docs**: `Previsão de projéteis <mod/projectile-lead.htm>`_; ``mod/modding``.

**Novidade: mercado configurável (compra/venda, tributo, comércio de rota)**


- Parâmetros ``market_currency``, ``market_commodities``, ``trade_hubs``, ``trade_rewards``, etc. — sem recursos fixos no motor.
- Ordens ``market_buy`` / ``market_sell`` / ``tribute`` / ``trade``. Docs: ``mod/market-system``, ``player/market-and-trade``; ``mods/aoe2/SOURCES.md``.

**Melhoria: renomear filtros de bônus para ``phase_bonus_targets`` / ``effect_bonus_targets``**

- Nomes principais emparelhados com ``phase bonus`` / ``effect bonus``.
- Aliases ainda válidos: ``phase_targets``, ``tech_effect_targets``, ``effect_targets``.

**Novidade: modos duais de coleta ``gather_mode trip|continuous``**

- Padrão ``trip``: um pulso ``gather_qty`` depois entrega (comportamento anterior).
- ``continuous``: preenche ``carry_capacity`` a uma taxa por segundo, depois entrega (estilo AoE II/IV).
- Rules: ``gather_mode``, ``carry_capacity``, ``carry_capacity_<type>``, ``gather_rate`` — veja docs de modding.
- ``mods/aoe2`` ativa continuous (carga 10, carcaça de caça 35).



**Melhoria: anunciar a facção após civ aleatória**

- Só se no lobby foi escolhido Aleatório **e** o mod tem mais de uma facção: após o objetivo inicial “você é” + civ; escolha manual ou uma só facção (ex. ``res`` base) fica em silêncio. ``Alt+C`` (``faction_status``) usa a mesma regra.
- Código: ``faction_announce.py``, ``worldplayerbase/base.py`` (``faction_was_random``), ``game_resources.py``, ``game_interface_base.py``; testes ``test_faction_status_announce.py``.

**Melhoria: ouvir a civ inimiga em mods multi-civ**

- Com mais de uma facção, o título de unidades inimigas/aliadas inclui a civ; ``F11`` e a seleção diplomática também dizem a civ após o nome.
- Código: ``faction_announce.py``, ``properties.py``, ``game_audio.py``.

**Novidade: ``on_phase`` e ``research_cost_discount`` / ``advance_cost_discount``**

- Recompensas por civ em ``class race``/``faction`` sem nomes fixos no motor.
- ``on_phase`` / ``research_cost_discount`` / ``advance_cost_discount``; ``phase bonus clear``; ``no_auto_upgrade 1``.
- Código: ``worldphase.py``, ordens, ``definitions.py``; testes ``test_faction_age_cost_discounts.py``.

**Novidade: templates de facção ``abstract`` e herança ``is_a`` no início**

- **Uso**: defaults de ``starting_resources`` / ``starting_units`` num pai abstrato (ex. ``Civilization``); cada civ ``is_a`` esse pai. O que o filho define prevalece; o omitido herda. Mapas sem unidades iniciais ainda usam o default da raça.
- **``abstract 1``**: só template — **oculto no seletor**; ``abstract`` não é herdado.
- **Herança**: ``class race`` = ``class faction``; cadeias ``is_a``. Linha explícita do mapa ainda vence.
- **Código / testes**: ``definitions.py``, ``test_faction_starting_inheritance.py``.

**Melhoria: isolar mapas e campanhas com um mod ativo (sem fallback para ``res``)**

- **Problema**: se um mod não tinha ``multi/`` ou ``single/`` próprios, os menus ainda listavam o conteúdo base de ``res``.
- **Mudança**: com qualquer mod ativo só se listam ``mods/<mod>/multi`` e ``mods/<mod>/single``; se não houver, as listas ficam vazias — **sem** voltar a ``res`` nem downloads. Sem mod, igual.
- **Código / testes**: ``lib/resource.py``, ``game.py``, ``test_mod_map_campaign_isolation.py``.

**Correção: ``starting_resources`` da raça ignorados se o mapa os omitir (início em 0)**

- **Problema**: as raças tinham ``starting_resources`` nas rules, mas mapas sem essa linha começavam em 0.
- **Causa**: ``_parse_map`` preenchia ``[0, 0, …]``; ``populate_map`` só usa o padrão da raça se a lista estiver vazia.
- **Correção**: lista vazia ``[]`` até o mapa definir ``starting_resources``; uma linha explícita do mapa (mesmo ``0``) continua a prevalecer.
- **Código / testes**: ``world_map.py``, ``test_race_starting_resources.py``.

**Correção: comentar ``LSHIFT C`` / ``LSHIFT B`` ainda copiava voz na partida**

- **Problema**: ``global_bindings.txt`` comenta por padrão Left Shift+C/B (copiar / anexar da biblioteca de voz primária), mas na partida ainda funcionavam.
- **Causa**: ``game_input_handler`` chamava ``voice_libs.handle_hotkey`` antes dos bindings, contornando a tabela de teclas.
- **Correção**: na partida Shift+C/B seguem **só os bindings**; um ``;`` no início desativa. Os menus mantêm Left/Right Shift+C/B em código. Right Shift+C/B (biblioteca secundária) continuam ativos por padrão.
- **Código / testes**: ``game_input_handler.py``, ``clientmenu.py``, ``voice_libs.handle_hotkey``, ``test_lshift_rshift_bindings.py``.


1.4.6.8
-------

**Novidade: habilidades automáticas na morte/destruição (``trigger_timing on_death``)**

- **Uso**: unidades ou edifícios podem disparar efeitos ao morrer — p.ex. um depósito de munição que explode com dano em área; também invocações, ``effect deploy``, etc.
- **Configuração**: em ``class skill``, ``auto_trigger 1``, ``manual_use 0``, ``trigger_timing on_death``, e ligar com ``can_use_skill`` (ou o legado ``death_trigger_skills``). Exemplo: ``effect harm_area 40 6`` (dano fixo 40, raio 6); também ``deploy`` / ``summon`` / ``buffs``.
- **Comportamento**: dispara em ``die()`` antes de apagar a entidade; permite HP já em 0; **ignora mana e cooldown**; centra em si (para AoE use ``effect_target self``); mortes em cadeia podem encadear mais ``on_death``. Diferente de ``mdg_explode`` / ``rdg_explode`` (só ao atacar). O mesmo skill pode ser ``manual_use 1`` + ``on_death`` (ex. depósito que se detona): um cast manual bem-sucedido é registado para a autodestruição **não explodir de novo**; destruído pelo inimigo ainda dispara uma vez.
- **Código / testes**: ``world_attributes.py``, ``worldcreature.py``, ``worldskill.py``; ``GENERIC_SKILL_SYSTEM.md``; ``test_death_skills.py``.


1.4.6.7
-------

**Correção: atacar um NPC neutro da história não o tornava hostil**

- Na campanha de Raynor (cap. 25), os guardas revidavam, mas continuavam ``neutral``, então o exército não os atacava sozinho.
- Causa: o duelo só fazia ``set_ai_mode offensive`` sem limpar ``Player.neutral``.
- Novo ``(set_neutral 0|1 [player])``; a neutralidade fica com guard — mudar para ofensivo/defensivo/perseguição (UI ou ``set_ai_mode``) remove; também ao ser atingido por um lado não neutro (não fauna); cap. 25 usa ``set_neutral 0`` no duelo e ``set_neutral 1 computer1`` ao recusar a aliança.
- **Código / testes**: ``worldplayerbase/base.py``, ``triggers.py``, ``25.txt``, ``test_campaign_alliance_transfer_triggers.py``, ``test_neutral_no_auto_attack.py``.

**Correção: a escolta de Marco atacava Raynor no duelo (cap. 27)**

- Deviam sair da arena; ``_notify_guard_units`` puxava o contra-ataque e a ordem só movia 8 de 12.
- Novo ``(set_counterattack 0|1 …)``; no início do duelo desativa o contra-ataque das 12 escoltas e elas saem com ``imperative go``.
- **Código / testes**: ``triggers.py``, ``27.txt``, ``test_campaign_alliance_transfer_triggers.py``.

**Correção: com cheats ativos, uma seta saltava várias casas**

- Em mapas grandes (ex. cap. 28) com cheatmode, Right uma vez ia a1→b1→c1→d1.
- Causa: ``select_square`` lento + key-repeat do pygame; o loop do jogo não limpava KEYDOWNs repetidos (o menu sim).
- Agora mantém só o primeiro KEYDOWN por tecla no lote e faz ``clear([KEYDOWN])`` depois de tratar.
- **Código / testes**: ``game_input_handler.py``, ``test_game_keydown_repeat_collapse.py``.


1.4.6.6
-------

**Correção: a verificação na inicialização às vezes não detectava versão nova**

- Com a verificação ao iniciar ligada, às vezes não havia aviso após abrir o jogo, mas Opções → Verificar agora encontrava a versão.
- Causa: o pedido ao GitHub pode levar ~20 s e a thread principal só esperava ~8 s; o tempo esgotado era tratado como «já atualizado».
- Agora a verificação começa mais cedo, espera terminar (~30 s) e, se ainda estiver pendente, usa a mesma verificação síncrona do menu.
- **Código / testes**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``test_auto_update.py``.

**Melhoria: avisos de atualização visíveis na tela**

- Não só por voz: texto na janela, botões Yes/No (clicáveis), notas do changelog visíveis, e tentativa de trazer a janela para a frente.
- **Código**: ``pygame_ui.py``, ``clientmenu.py``, ``clientversion.py``.

**Correção: ao escolher ouvir as notas de atualização nada era lido**

- Depois de confirmar uma atualização nova, aceitar ouvir as notas não reproduzia o body do Release no GitHub (ou era cortado na hora pelo aviso de continuar).
- Causa: lista de ``literal_text_msg`` aninhada a mais, e ``voice.item`` não bloqueante interrompido pelo próximo aviso.
- Agora usa ``voice.menu(literal_text_msg(...))`` (bloqueia até terminar ou pular) e só então pede para continuar.
- **Código / testes**: ``clientversion.py``, ``test_auto_update.py``.

**Correção: deslocamento de tradução no TTS (chave ``5750``)**

- Em de / es / fr / it / pt-BR, a chave ``5750`` (idioma) estava errada com texto de «um contra muitos» por deslocamento de linhas.
- Corrigido em ``res/ui-de``, ``ui-es``, ``ui-fr``, ``ui-it``, ``ui-pt-BR`` ``tts.txt`` → Sprache / idioma / langue / lingua / linguagem.

**Correção: auditoria TTS multilíngue (ids faltantes e erros claros)**

- Vários idiomas estavam atrás do ``tts.txt`` inglês (cerca de 27 ids mais novos: solo/ar intransitáveis, ameaça, contagem regressiva de vitória, voz de acessibilidade, idioma padrão do sistema, etc.), com erros ou confusões (ex.: italiano: soldado como peão, furtivo = invisível, reunião = reorganizar; es/pt: furtivo como «roubado»; alemão: reunião como «você comanda»; população vs comida; velocidade da fala = velocidade de unidade; textos longos das bibliotecas de voz ainda em inglês).
- Completados os ids faltantes em ``ui-it``, ``ui-fr``, ``ui-es``, ``ui-de``, ``ui-pt-BR``, ``ui-ru``, ``ui-pl``, ``ui-cs``, ``ui-sk``, ``ui-be``, ``ui-vi`` (o chinês já estava completo); corrigidos erros claros; traduzidos os textos de voz/atualização que ainda estavam em inglês.
- **Alinhamento i18n**: executado ``python tools/i18n/extract_pot.py`` para que ``i18n/tts.pot`` e cada ``i18n/tts-*.po`` coincidam com ``res/ui-*/tts.txt``; rodar ``build_tts.py`` depois não apagará estas atualizações.
- **Arquivos**: ``res/ui-*/tts.txt``, ``i18n/tts.pot``, ``i18n/tts-*.po``.


1.4.6.5
-------

**Correção / novidade: gás do mod StarCraft esgota (extratores genéricos)**

- **Problema**: Assimilator / Extractor / Refinery produziam vespene ilimitado em ``production_qty`` (padrão 8) — diferente de StarCraft.
- **Regras**: o geyser tem reserva (padrão ``deposit_volume 5000``; ``geyser 1`` no mapa é marcador e usa esse valor, ou ``geyser 5000``); cada ciclo debita da reserva; ao zerar, o rendimento cai para ``depleted_production_qty`` (2).
- **Palavras-chave**: ``is_an_extractor``, ``deposit_volume``, ``depleted_production_qty`` (reutilizáveis em outros mods).
- **Código / testes / docs**: ver notas em inglês/chinês; ``mods/starcraft/readme.txt``.

**Melhoria: spawn larva/hatchery genérico com ``spawns_unit``**

- Sem nomes fixos ``hatchery``/``larva``; qualquer edifício pode usar ``spawns_unit`` + ``larva_cap`` + ``larva_spawn_time``.


1.4.6.4
-------

**Novo: Opções → Verificar atualizações agora**

- Se desligar a verificação ao iniciar, ainda pode checar o GitHub manualmente em Opções; se houver versão nova, o fluxo de confirmação é o mesmo.
- Anuncia se você já tem a versão mais recente ou se a verificação falhar.

**Melhoria / correção: pacote Windows com janela de atualização separada (com progresso)**

- Após confirmar, o jogo sai e ``soundrts.exe --soundrts-update`` abre **SoundRTS Update** para baixar/extrair com barra de progresso (evita “Não está respondendo” e travamentos ao carregar o módulo). A instalação usa ``tasklist`` sem ``find`` (conflito com Git), ignora ``user`` e reinicia. Temporários em ``user/tmp/`` (ou ``%APPDATA%\\SoundRTS\\tmp/``).
- **Código**: ``update_window.py``, ``update_core.py``, ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``soundrts.py``, ``msgparts.py``, ``tts.txt`` (``5794``–``5798``).
- **Testes**: ``test_auto_update.py``.

**Correção: lentidão ao percorrer o menu de bibliotecas de voz com as setas**

- Em Opções → bibliotecas de voz, subir/descer ficava lento mesmo com uma linha curta selecionada, enquanto o texto longo de ajuda permanecia visível.
- Cada redesenho truncava linhas longas com um loop linear de ``font.size``.
- Agora o ajuste de texto do menu usa busca binária e cache.
- **Código**: ``lib/pygame_ui.py`` (``_fit_menu_text``).
- **Testes**: ``test_voice_libs_menu_arrow_profile.py``.

**Melhoria: textos de bibliotecas de voz / verificar atualizações passam a ids TTS multilíngues**

- Alguns textos existiam só como literais em chinês em ``msgparts.py`` e não seguiam o idioma da interface via ``tts.txt``.
- Agora são ids numéricos (cerca de ``5760``–``5793``) em ``res/ui`` e em cada ``ui-*`` ``tts.txt`` (zh/en completos; outros idiomas traduzem rótulos curtos, com inglês de reserva nos textos longos).
- **Código**: ``msgparts.py``, ``tts.txt`` por idioma.


1.4.6.3
-------

**Novo: verificar atualizações do GitHub ao iniciar e instalar com um clique (pacote Windows)**

- Na abertura, consulta o Release do GitHub ``tuohai/soundrts-ultimate-version``. Se houver versão mais nova: **Enter** para atualizar, **Esc** para cancelar.
- Opcionalmente, ouvir as notas do Release antes do download.
- **Pacote Windows**: baixa e extrai em ``tmp`` da configuração (portátil ``user/tmp/``, instalado ``%APPDATA%\\SoundRTS\\tmp/``); ao sair, um script curto sobrescreve a pasta e reinicia. A pasta ``user`` é **ignorada** (saves/ajustes locais). Após aplicar, esses temporários são apagados.
- **Execução a partir do código-fonte**: só abre a página de download (não sobrescreve o projeto).
- Menu de opções: **Verificar atualizações ao iniciar o jogo** (ligado por padrão; Enter alterna). Opção ``check_updates_on_start`` em ``SoundRTS.ini``.
- **Código**: ``auto_update.py``, ``clientversion.py``, ``clientmain.py``, ``config.py``.
- **Testes**: ``test_auto_update.py``.

**Melhoria: scroll pelas bordas e zoom com a roda em mapas grandes Ctrl+F2 (estilo Age of Empires)**

- Em mapas grandes, passar o mouse pelas casas **não salta mais a câmera**.
- A vista só se move com o ponteiro na **borda do mapa**; roda para cima/baixo aproxima/afasta.
- Clique no minimapa e saltos pelo teclado ainda centralizam a vista.
- **Código**: ``clientgamegridview.py``, ``game_input_handler.py``, ``game_navigation.py``.
- **Testes**: ``test_gridview_viewport.py``, ``test_zoom_mouse.py``.


1.4.6.2
-------

**Novo: trocar o idioma da interface pelo menu de opções**

- Menu principal → **Opções** → **Idioma**: escolha um idioma ou **Padrão do sistema** sem editar arquivos da pasta de instalação.
- A preferência é salva em ``language.txt`` do usuário (``user/language.txt`` ou ``%APPDATA%\\SoundRTS\\language.txt``). ``cfg/language.txt`` continua como fallback somente leitura.
- O arquivo do usuário tem prioridade sobre ``cfg/language.txt``.
- **Código**: ``clientmain.py``, ``lib/resource.py``, ``paths.py``.

**Melhoria: painel de atributos / mochila e equipamento / viewport de mapas grandes**

- Painel de atributos na seleção; mochila/equipamento com mouse; mapas grandes estilo Age of Empires (sem encolher).

**Correção: falha ao salvar retomada automática em mapas grandes**

- Ao sair no meio da partida em mapas grandes (ex.: ``cw1-mm`` 100×100), o autosalvamento de «continuar jogo» falhava e o log dizia incorretamente «mundo grande demais».
- **Causa**: ``local_client.interface`` era serializado (fontes/locks do pygame).
- **Correção**: ``interface`` não é salva (reconstruída ao carregar); só ``RecursionError`` / ``MemoryError`` são reportados como mapa grande demais.
- **Código**: ``worldclient.py``, ``game.py``, ``clientgame/game_resources.py``.


1.4.6.1
-------

**Correção / melhoria: unidades no mapa Ctrl+F2 e camadas de arte**

- **Correção**: unidades/edifícios do mapa principal quase grudados no topo por conversão mundo→tela errada; o eixo Y agora alinha com as casas.
- **Mouse / HUD / F8**: seleção, grade 5×3, fila; ``ui/icons`` (HUD) vs ``ui/map`` (mapa) vs ``ui/anims``.
- **Código**: ``clientgamegridview.py``, ``game_hud.py``, ``game_unit_anim.py``, etc.


1.4.6.0
-------

**Novo / melhoria: qualidade visual Ctrl+F2 (vista de cima)**

Em relação ao mapa de depuração antigo (blocos planos, muros pretos, pontinhos), esta versão melhora legibilidade e densidade de informação:

- **Terreno e atmosfera**: cores padrão legíveis sem ``color`` no style; terreno alto mais claro e levemente quente; névoa escurecida mas com matiz; mapa centralizado com margens.
- **Estrutura**: grade; muros vs saídas/passagens diferenciados.
- **Unidades e recursos**: formas distintas; cores de time; seleção; barras de vida; marcadores aéreos.
- **Rótulos e painel**: coordenadas base 1 (ex. 2,7), nomes e recursos; painel esquerdo ao passar o mouse.
- **Minimapa e botão de objetivos**: como no manual.
- **Código**: ``clientgamegridview.py``, ``game_visual_fx.py``, etc.

**Novo: F4 liga/desliga a voz de acessibilidade nos menus**

- Em **qualquer menu** (incluindo o menu de pausa), **F4** ou o item «alternar voz de acessibilidade» desliga/liga todo o TTS.
- **Desligado**: sem fala; SFX e música continuam; útil com Ctrl+F2.
- **Padrão ligado**; salvo em ``SoundRTS.ini`` (``speech_enabled``).
- **F4 na partida inalterado** (teclas em camadas: ainda Ajuda); só nos menus.
- **Código**: ``config.py``, ``lib/voice.py``, etc.; TTS 5740–5743.
- **Docs**: ``player/voice-libraries.rst``, manuais.

**Novo: menus visuais pygame e mouse (sem wxPython)**

- Menus principal/sub/pausa desenham uma lista na janela SDL (~960×640).
- **Mouse**: destaca ao passar; clique seleciona e anuncia; outro clique ou duplo clique confirma. Teclado inalterado.
- Jogo sem visão: TTS + teclado; o texto na tela é pixel e **em geral não chega a leitores/braille**.
- **Código**: ``lib/pygame_ui.py``, ``clientmenu.py``, ``lib/screen.py``.

**Novo: cut-scenes / sinopse / objetivos na tela**

- ``synopsis`` da campanha, ``sequence``, ``intro`` do mapa, objetivo inicial e F9 na partida mostram texto.
- **Objetivo inicial**: sempre rola; na partida dá para rever.
- **Cut-scenes / sinopse / intro**: local / treino / só vs PCs: Enter / Esc; online (dois ou mais humanos): rola.
- **Código**: ``lib/voice.py`` (play_cutscene_line / play_scrolling_line / play_narrative_line), ``clientmedia.py``, ``campaign.py``, etc.

**Melhoria: Ctrl+F2 persistente**

- Salvo como ``display_enabled`` em ``SoundRTS.ini``; restaurado na próxima abertura.
- **Código**: ``config.py``, ``clientmedia.py``.

**Correção: atraso ao saltar mapas por letra**

- Listas longas ~0,8 s por varredura TTS global; agora rótulos locais + cache.
- **Código**: ``lib/pygame_ui.py``, ``clientmenu.py``.


1.4.5.9
-------

**Melhoria: ``space`` do quadrado contado por aliança**

- **Antes**: Capacidade compartilhada; artilharia inimiga enchendo um quadrado bloqueava melee/cavalaria.
- **Agora**: Cada aliança tem o próprio orçamento até ``square_width``; ocupação inimiga não usa o seu. Ex.: com ``square_width 12``, cada lado pode ter doze ``space 1``. Aliados compartilham um orçamento.
- **Código**: ``worldroom.py``; treino/spawn passam o jogador.
- **Testes**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Correção: recursos coletados entravam no estoque sem armazém**

- **Sintoma**: Após coletar, os trabalhadores podiam adicionar recursos ao estoque mesmo sem prefeitura / serraria ou outro prédio de armazenamento.
- **Causa**: Em terra, ``bring_back`` ainda chamava ``_store_cargo()`` quando ``nearest_warehouse`` não achava nada. Em 1.3.8.1 a carga era limpa e a ordem falhava; uma reescrita posterior depositava por engano.
- **Correção**: Sem armazém não deposita; mantém a carga, avisa uma vez ``order_impossible`` e para. A entrega continua depois de um armazém ser construído.
- **Código**: ``worldorders/gathering.py``.
- **Testes**: ``test_gather_requires_warehouse.py``.


1.4.5.8
-------

**Novo: ocupação abstrata do quadrado (``space``)**

- A propriedade ``space`` (precision; decimais permitidos) usa as **mesmas unidades que ``square_width``**. ``square_width 12`` = cada quadrado (ex.: a1) tem tamanho 12; ``space 1`` ocupa 1 desses 12 (no máximo 12); ``space 0.5`` → no máximo 24.
- Padrão ``space 0`` = ilimitado (legado). A capacidade é por aliança (veja 1.4.5.9); se o seu lado estiver cheio, você não pode entrar nem treinar ali. Voz: ``not_enough_space`` (TTS 5338); rótulo TTS 5733.
- Vanilla: peasant/footman ``space 0.25``; catapult ``space 1``.
- **Código**: ``definitions.py``, ``worldentity.py``, ``worldroom.py``, ``worldunit/world_movement.py``, ``worldorders/production.py``, ``worldplayercomputer_water.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui*/tts.txt``.
- **Docs**: ``mod/modding.rst``, ``mod/mapmaking.rst``, manuais (todos os idiomas).
- **Testes**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Novo: contagem regressiva de vitória de prédio (``victory_time``) e Maravilha**

- Qualquer prédio concluído com ``victory_time N`` (segundos) inicia uma contagem regressiva. Se o temporizador terminar e o prédio ainda existir, o dono (e o campo de vitória aliada) vence. Destruir o prédio cancela a contagem e anuncia.
- ``wonder`` (Maravilha) no vanilla (Idade Imperial): prédio tardio caro; ``victory_time 300`` (5 minutos). Atalho ``o``.
- Vozes 5720–5722 (início / cancelamento / restante); avisos em 120/60/30/10 s e 5…1.
- **Código**: ``building_victory.py``, ``worldunit/worldcreature.py``, ``world/world_core.py``, ``world/world_game.py``, ``definitions.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (``victory_time``), manuais do jogador.
- **Testes**: ``test_building_victory.py``.

**Novo: requisitos ``any_buildings`` por grupo**

- ``requirements`` pode usar ``any_buildings <n> <group>_buildings``: o jogador deve possuir quaisquer ``<n>`` prédios distintos do grupo (AND com outros nomes simples na mesma linha).
- Pertencimento: prédios cujo ``requirements`` simples lista ``<chave>`` (após remover o sufixo ``_buildings``). Exemplo: ``requirements castle_age`` entra em ``castle_age_buildings``.
- Vanilla: ``imperial_age`` e ``castle`` (keep→castle) usam ``any_buildings 2 castle_age_buildings``.
- Voz: style ``parameters.any`` / ``parameters.buildings_of`` (TTS 5730–5731).
- **Código**: ``worldrequirements.py``, ``worldplayerbase/base.py``, ``worldphase.py``, ``worldplayercomputer.py``, ``clientgameorder.py``, ``attributes/display_interface.py``, ``definitions.py``, ``worldunit/worldcreature.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Docs**: ``mod/modding.rst`` (todos os idiomas).
- **Testes**: ``test_any_buildings_requirements.py``.


1.4.5.7
-------

**Correção: unidades presas atacando prédios sem ameaça em vez de combatentes**

- **Sintoma**: enquanto unidades destroem uma fazenda, prefeitura ou prédio semelhante, combatentes inimigos podem se aproximar e matá-las; os atacantes continuam batendo no prédio em vez de trocar de alvo.
- **Causa**: na 1.4, a resseleção de alvo era pulada durante o engajamento (desempenho). Prédios contam como inimigos vivos, então o combate grudava em fazendas. 1.3.8.1 só grudava em alvos com ``menace > 0`` e reescolhia quando o alvo atual não tinha ameaça.
- **Correção**: restaurado o comportamento 1.3.8.1—engajamento sticky e cache de decisão só com ``menace > 0``; prédios com ameaça 0 podem ser reescaneados, preferindo unidades de combate. Contra unidades ameaçadoras ainda retorna cedo (caminho quente intacto).
- **Código**: ``worldunit/world_ai_decision.py``.
- **Testes**: ``test_retarget_zero_menace.py``.

**Melhoria: bindings distinguem Shift esquerdo/direito (``LSHIFT`` / ``RSHIFT``)**

- Além de ``SHIFT``, pode-se usar ``LSHIFT`` e ``RSHIFT`` como modificadores (não misturar com ``SHIFT`` na mesma linha).
- A busca prefere o lado específico e depois cai no ``SHIFT`` genérico.
- Ativos por padrão: ``RSHIFT C`` / ``RSHIFT B`` (copiar/acrescentar **secundária**).
- ``LSHIFT C`` / ``LSHIFT B`` (principal) estão **comentados** em ``res/ui/global_bindings.txt``; remova o ``;`` inicial para ativar.
- **Dica:** use um leitor de tela como voz principal para não gastar ``F9``–``F12`` na principal; os atalhos estão quase saturados. Veja ``player/voice-libraries.rst``.
- **Código**: ``lib/bindings.py``, ``res/ui/global_bindings.txt``, ``hotkey_editor.py``.
- **Testes**: ``test_lshift_rshift_bindings.py``.

**Melhoria: piso de volume para casas distantes no pan de voz**

- Alertas faladas com posição não atenuam sem limite: o volume fica perto do de uma casa adjacente (um pouco mais baixo permitido). Os beeps do minimapa ainda usam atenuação completa por distância.
- **Código**: ``lib/sound.py``, ``clientgame/game_resources.py``, ``clientgame/game_unit_control.py``.
- **Testes**: ``test_spatial_voice_alerts.py``.

**Melhoria: multiplicador ``build_time`` em ``ai.txt``**

- Nova diretiva ``build_time <pct>`` (no início, fora do loop): porcentagem da duração normal de construção (``100`` = normal, ``50`` = o dobro de rápido).
- Exemplos: advanced/expert ``build_time 50``; nightmare ``build_time 40``.
- **Testes**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.

**Melhoria: multiplicador ``gather_time`` em ``ai.txt``**

- Nova diretiva ``gather_time <pct>``: porcentagem da duração normal de coleta (``100`` = normal, ``50`` = o dobro de rápido). Diferente do campo ``gather_time`` de trabalhadores em ``rules.txt``.
- Exemplos: advanced/expert ``gather_time 50``; nightmare ``gather_time 40``.
- **Testes**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.6
-------

**Correção: Alt+Z só podia enfileirar mais um treino**

- **Sintoma**: após confirmar treinar camponês no hall, Alt+Z (``do_again now``) só adicionava mais um à fila; novas pressões não alongavam a fila (substituíam o único follow-up enfileirado).
- **Causa**: na 1.4, só um pedido normal podia ficar atrás de uma cabeça imperativa (para proteger ``auto_explore``). Pedidos de produção (train/research) também são ``is_imperative``, e foram atingidos por engano. 1.3.8.1 não tinha esse limite.
- **Correção**: pedidos de produção com ``never_forget_previous`` podem empilhar; o slot único continua para follow-ups normais atrás de cabeças imperativas de verdade.
- **Código**: ``worldunit/world_order.py``.
- **Testes**: ``test_train_queue_repeat.py``.

**Correção: primeiro Alt+Z (e semelhantes) trava ~0.6–1s**

- **Sintoma**: ao começar, o primeiro Alt+Z congela ~0.5–1s; 1.3.8.1 Alt+G não fazia isso.
- **Causa**: ``LALT`` → ``history_stop_primary`` → ``needs_sapi32`` iniciava a frio o helper SAPI 32-bit (PowerShell) mesmo com Nuance.
- **Correção**: vozes Nuance saltam o probe; cache de ``needs_sapi32``.
- **Código**: ``lib/game_tts.py``.
- **Testes**: ``test_nuance_skip_sapi32_probe.py``.


1.4.5.5
-------

**Melhoria: alertas de casa com pan estéreo (acompanha a vista)**

- Falas passivas ligadas a casa (inimigo, baixas, scout, alertas) panoramizadas em relação à casa de vista atual.
- O pan atualiza se você mudar de casa no meio da fala.
- **Código**: ``lib/voicechannel.py``, ``lib/message.py``, ``lib/game_tts.py``, ``lib/nuance_tts.py``, ``clientgame/game_unit_control.py``, ``clientgame/game_navigation.py``, ``tools/nuance_ve``, ``tools/sapi32``.
- **Documentação**: ``player/voice-libraries.rst``.
- **Testes**: ``test_spatial_voice_alerts.py``.

**Melhoria: a secundária foca no campo de batalha (economia/produção → principal)**

- Conclusão de unidade/prédio, pesquisa, avanço de era, recursos e «menu alterado» passam à biblioteca **principal**.
- **Documentação**: ``player/voice-libraries.rst``.

**Melhoria: Alt esquerdo / Alt direito filtram principal vs secundária**

- **Alt esquerdo** pula/para a principal; **Alt direito** pula/para a secundária.
- **Com secundária desativada**: ambos os Alt pulam a fala atual.
- **Documentação**: ``player/voice-libraries.rst``.

**Melhoria: buffer e frequência do mixer configuráveis (menos engasgos de SFX na partida)**

- Em ``SoundRTS.ini`` ``[audio]``: ``mixer_buffer`` (padrão ``2048``) e ``mixer_frequency`` (padrão ``44100``), aplicados na inicialização via ``pygame.mixer.pre_init``.
- Buffer maior = áudio mais estável, latência um pouco maior (``1024`` / ``2048`` / ``4096``). Valores inválidos vão para o mais próximo de ``512/1024/2048/4096/8192``.
- Canais de SFX: ``[general] num_channels`` (padrão ``16``; tente ``32`` se precisar).
- Depois de alterar, **reinicie o jogo**.
- **Código**: ``config.py``, ``lib/sound.py``, ``clientmedia.py``.
- **Documentação**: ``mod/audio-management.rst``.


1.4.5.4
-------

**Melhoria: bibliotecas de voz principal / secundária e interruptor**

- Na partida: operações do jogador usam a biblioteca **principal**; eventos passivos (baixas, descobertas…) usam a **secundária** (podem sobrepor-se; só Alt interrompe a secundária).
- Opções → Configurações da biblioteca de voz: volume / tom / velocidade / voz / dispositivo por biblioteca; ativar ou desativar a secundária.
- **F3 nos menus** ativa/desativa a secundária (não na partida); desativada, a principal anuncia tudo.
- Instale vozes SAPI ou pacotes ``voice.ini`` em ``user/voices``; um leitor de tela detectado pode assumir a principal.
- **Código**: ``lib/voice.py``, ``lib/voicechannel.py``, ``lib/game_tts.py``, ``lib/voice_libs.py``, ``lib/voice_packs.py``, ``clientmenu.py``, ``clientmain.py``, ``config.py``.
- **Documentação**: ``player/voice-libraries.rst``.
- **Testes**: ``test_secondary_voice_toggle.py``, ``test_secondary_alt_interrupt.py``.

**Melhoria: reforços de cartas e ``starting_units`` da IA consomem população**

- Unidades de cartas ``spawn`` / ``train_bonus`` usam o ``population_cost`` normal (não são mais grátis em população).
- Bônus ``starting_units`` em ``ai.txt`` também consomem população (igual ao início do mapa); aumente o teto com ``starting_population`` se precisar.
- **Código**: ``card_loadout.py``, ``worldplayercomputer.py``.
- **Documentação**: ``player/loadout-cards.rst``, ``mod/aimaking.rst``, ``mod/delayed-card-loadout.rst``, ``mod/achievement-system.rst``.
- **Testes**: ``test_card_loadout.py``, ``test_ai_start_settings.py``.

**Melhoria: multiplicadores ``train_time``, ``research_time`` e ``unit_hp`` em ``ai.txt``**

- Novas diretivas one-shot (no início da partida, fora do loop do script):
  - ``train_time <pct>`` — porcentagem da duração normal de treinamento (``100`` = normal, ``50`` = metade do tempo)
  - ``research_time <pct>`` — porcentagem da duração normal de pesquisa/avanço (``80`` = 20% mais rápido)
  - ``unit_hp <pct>`` — porcentagem do HP normal das unidades deste computador (``120`` = +20% HP)
- Exemplos em ``res/ai.txt``: advanced ``train_time 50`` / ``research_time 80``; expert também ``unit_hp 120``; nightmare ``train_time 40`` / ``research_time 60`` / ``unit_hp 140``.
- **Código**: ``definitions.py``, ``worldplayercomputer.py``, ``worldorders/base.py``, ``worldorders/production.py``, ``worldunit/worldcreature.py``; ``res/ai.txt``.
- **Documentação**: ``mod/aimaking.rst``.
- **Testes**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.3
-------

**Correção: soldados do computador intermediário presos em autoexploração (ataques muito atrasados ou instáveis)**

- **Sintoma**: Em mapas pequenos (ex.: ``jl1``), convidar um computador intermediário com humano ocioso gerava momento do primeiro ataque muito instável — às vezes ~6 min, às vezes 16–22 min. No 1.3.8.1 o computador agressivo atacava de forma estável por volta de 7–9 min no mesmo cenário.
- **Causa**: Desde o 1.4, ``take_order`` protege a ordem imperativa no topo (``auto_explore`` é imperativa): um ``go`` comum só entra na fila e não consegue substituir a exploração. ``_send_explorer`` ainda recallava o explorador antigo com ``go``, falhava e ia designando novos exploradores até quase todos os soldados ficarem em ``auto_explore``, de modo que ``constant_attacks`` não tinha combatentes ociosos.
- **Correção**: ``_send_explorer`` emite ``stop`` antes do recall e limpa exploradores extras para que normalmente só uma unidade explore.
- **Código**: ``worldplayercomputer.py`` (``_send_explorer``).
- **Verificação**: Comparação headless com vários seeds vs 1.3.8.1; após o conserto, o primeiro dano do intermediário em jl1 fica cerca de 5–7 min com dispersão ~1,5 min.

**Correção: salto por letra inicial no menu de mapas pulava o primeiro mapa e atrasava ao trocar de letra**

- **Sintoma**: Em Um jogador → Iniciar um jogo em (lista de mapas), uma tecla de letra muitas vezes caía na segunda correspondência (ex.: ``m`` → ``m2`` em vez de ``m1``, ``p`` → ``pm2`` em vez de ``pm1``); ao apertar outra letra havia uma pausa de cerca de 0,7–1 s antes do salto.
- **Causa**: O anúncio do título com ``keep_key`` recolocava na fila todos os ``KEYDOWN`` de auto-repetição, assim um toque era processado duas vezes; lembrar o último mapa inseria um duplicado no início da lista, que ganhava se compartilhasse a letra. ``_first_letter`` chamava ``translate_sound_number`` → ``_global_lookup_text`` nos nomes de mapa, custando ~1 s ao varrer uma lista de centenas de entradas.
- **Correção**: Manter só o primeiro ``KEYDOWN`` ao interromper a fala e limpar repetições após o salto por letra; com seleção nova, achar a primeira correspondência desde o início da lista; lembrar via ``default_choice_index`` em vez de duplicado; pegar o primeiro caractere do nome do mapa e consultar ids TTS numéricos só na camada local.
- **Código**: ``clientmenu.py``, ``lib/voice.py``.
- **Testes**: ``test_menu_first_letter_jump.py``.


1.4.5.2
-------


**Melhoria: menace multidimensional e overrides opcionais em rules**

- O ``menace`` padrão não é mais só dano: combina dano, cover/acerto, cooldown, wind-up (``*_ready``), HP, armadura, esquiva, alcance e velocidade (escolha de alvo e ameaça por casa).
- Campos opcionais: ``menace`` / ``menace_vs`` (absoluto), ``menace_mult`` / ``menace_mult_vs`` (peso sobre a base automática). Parâmetros: ``menace_armor_weight``, ``menace_dodge_weight``, ``menace_range_weight``, ``menace_speed_weight``, ``menace_hp_ref``.
- **Docs**: ``mod/modding.rst``, ``mod/aimaking.rst`` (EN/ZH).

**Melhoria: perseguição contínua entre casas (perseguição de verdade)**

- **Antes**: No modo ``chase``, quando o inimigo saía da casa a IA emitia ``go`` automático para casas vizinhas e atacava de novo — ainda por ordens; a unidade podia ficar “atacando” sem cruzar.
- **Agora**: ``chase`` mantém um único ``AttackAction`` no inimigo travado e segue pelas saídas entre casas, sem spam de ``go``.
- **Hold**: ``position_to_hold`` no spawn ainda impede sair em ofensivo / guarda. Defensivo / perseguição ficam isentos (a perseguição limpa o hold ao cruzar). ``go`` / ``attack`` normais ainda chamam ``stop()`` e limpam o hold.
- **Código**: ``worldaction.py``, ``worldunit/world_ai_decision.py``, ``worldunit/world_movement.py``.
- **Docs**: ``player/unit-default-behavior.rst``.
- **Testes**: ``test_chase_continuous_pursuit.py``.

**Melhoria: tela de atributos mostra stats com terreno em tempo real**

- Alt+V mostra ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` e modificadores de carga por terreno.
- O terreno da casa atual (``mdg_vs`` / ``rdg_vs`` / etc.) e ``*_on_terrain`` alimentam dano, cooldown e velocidade na UI (``*_vs`` de terreno = percentual decimal; ``speed_on_terrain`` continua velocidade absoluta).
- **Código**: ``attributes/terrain_effective.py``, ``attributes/combat_attributes.py``, ``attributes/basic_attributes.py``, ``attributes/bonus_handler.py``.
- **Testes**: ``test_terrain_attributes_ui.py``, ``test_terrain_effective_attributes.py``.

**Correção: Tab não encontra mais saídas em casas nunca exploradas**

- **Sintoma**: Em casas nunca visitadas, Tab ainda podia anunciar saídas do outro lado.
- **Causa**: A névoa lembrava saídas opostas antes da entrada real.
- **Correção**: Sem ``scouted_squares`` nem ``scouted_before_squares``, resumo / visibilidade em branco; névoa estática após visitar ainda permite Tab.
- **Código**: ``clientgame/game_unit_control.py``.
- **Testes**: ``test_unknown_square_tab_blank.py``.

**Correção: bip ``order_impossible`` após matar animal com Backspace**

- **Sintoma**: Após o ataque padrão a um animal caçável, tocava ``order_impossible``.
- **Causa**: ``AttackOrder`` tratava o alvo desaparecido como falha.
- **Correção**: Completar a ordem se o alvo sumir ou ``hp <= 0``.
- **Código**: ``worldorders/movement.py``.
- **Testes**: ``test_hunting.py``.

**Correção: ordem padrão em neutros e dano de caça**

- ``go`` normal / padrão em neutros (não imperativo) só move — sem AttackAction com dano zero.
- ``attack`` normal em ``is_huntable`` (incluindo caça padrão com Backspace) causa dano; só ataque imperativo faz a IA tratar neutros como alvos automáticos.
- **Código**: ``worldunit/world_ai_decision.py``, ``worldunit/worldcreature.py``.
- **Docs**: ``player/hunting.rst``, ``player/unit-default-behavior.rst``.
- **Testes**: ``test_neutral_no_auto_attack.py``, ``test_neutral_go_and_hunt_attack.py``.

**Correção: crash na atualização de percepção do jogador Computer (``_buckets`` ausente)**

- **Sintoma**: Durante a partida (especialmente com IA ``computer_only`` do mapa, aliados de IA ou após carregar um save) podia travar na etapa de percepção do loop principal com ``AttributeError: 'Computer' object has no attribute '_buckets'``.
- **Causa**: O índice espacial do jogador ``_buckets`` era inicializado apenas no wrapper ``Player.__init__``; salvar/carregar remove esse campo de cache; checagens em lote de visão aliada (``bulk_visibility_check``) chamam ``_potential_neighbors`` dos aliados e falhavam se um ``Computer`` ainda não tivesse ``_buckets``.
- **Correção**: Pré-inicializar ``_buckets`` em ``BasePlayer.__init__`` junto com os outros caches de percepção; ``_potential_neighbors`` usa um dicionário vazio quando estiver ausente; ``update_alliance`` limpa o cache de instância ``allied_vision`` para que mudanças de aliança não mantenham listas de aliados obsoletas.
- **Código**: ``worldplayerbase/base.py``, ``worldplayerbase/perception.py``, ``worldplayerbase/__init__.py``.
- **Testes**: ``test_meteors_computer_only.py``, ``test_phase3_parity.py``, ``test_neutral_passive_creep.py``.


1.4.5.1
-------

**Melhoria: cobertura de terreno, modificadores por unidade e notação percentual**

- ``class terrain`` em ``rules.txt`` agora suporta ``cover <solo> <ar>``, como ``speed``: ``terrain marsh h8`` no mapa herda cobertura padrão; linhas ``cover`` do mapa ainda sobrescrevem casas individuais.
- O terreno pode modificar **tipos de unidade** com ``speed_vs``, ``cover_vs``, ``dodge_vs``, ``mdg_vs``, ``rdg_vs``, ``mdg_cd_vs``, ``rdg_cd_vs`` (ex. ``speed_vs knight .25 archer .5``). Basta usar ``*_vs`` sem ``speed``/``cover`` global.
- Esses ``*_vs`` e ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` (e ``charge_*_terrain``) usam **percentuais decimais 0–1** (``.5`` = ±50%%, ``.1`` = ±10%%) em relação ao dano ou cooldown base atual da unidade.
- ``speed_on_terrain`` continua sendo **velocidade absoluta** (diferente de ``speed_vs`` em percentual).
- ``speed`` / ``cover`` do mapa afetam **todas** as unidades na casa; diferenças por unidade ficam nas defs de terreno ou unidade em ``rules.txt``.
- **Código**: ``worldterrain.py``, ``lib/square_terrain_rules.py``, ``world/world_map.py``, ``combat/hit_miss.py``, ``combat/damage_calculation.py``, ``combat/attack_action.py``, ``worldunit/world_movement.py``; mapas aleatórios emitem linhas ``cover`` (``rmg_templates.terrain_cover_line``).
- **Documentação**: ``mod/building-land-terrain.rst``; comentários em ``res/ui/editor_palette.txt``.
- **Testes**: ``test_terrain_cover_defaults.py``, ``test_terrain_unit_vs.py``, ``test_unit_on_terrain_percent.py``; ``test_combat_terrain_modifiers.py`` atualizado para casos percentuais.

Correções de bugs e melhorias de UX de voz/áudio:

**Correção: cooldown de ataque corpo a corpo / à distância (``mdg_cd`` / ``rdg_cd``) mais lento que nas rules**

- **Sintoma**: Com 1 s de cooldown nas rules (ex. camponês ``mdg_cd 1``), o intervalo real era visivelmente maior que em 1.3.8.1 (~1,5 s vs ~1,2 s; o segundo é apenas quantização do tick de 300 ms).
- **Causa**: (1) Com ``mdg_ready`` / ``rdg_ready`` em 0, o ramo de preparação ainda consumia um tick extra antes de atacar; (2) acertos instantâneos (``mdg_delay`` / ``rdg_delay`` 0) eram forçados a um mínimo de 100 ms em ``_schedule_ballistic_hit``; (3) ``attack_action.aim()`` e ``damage_effects._schedule_ballistic_hit`` definiam ambos o cooldown, com uma segunda gravação após o atraso que estendia ``next_attack_time``.
- **Correção**: pular preparação quando ``ready=0`` e atacar imediatamente; sem piso de 100 ms para acertos instantâneos; cooldown definido apenas uma vez em ``attack_action.aim()`` ao iniciar o ataque.
- **Nota**: ``charge_mdg_cd`` / ``charge_rdg_cd`` usam caminho separado (``receive_hit`` imediato, sem preparação/agendamento balístico) e não foram afetados; o ritmo misto carga + ataque normal melhora indiretamente com a correção do CD normal.
- **Código**: ``combat/attack_action.py``, ``combat/damage_effects.py``.
- **Testes**: ``test_attack_cooldown_timing.py``.

**Melhoria: rejeição de ordens go e aviso de voz em terreno intransitável**

- Unidades terrestres com ``go`` / ``patrol`` para casas ``is_ground 0``, ou aéreas para ``is_air 0``: ordem rejeitada na fila com ``ground_impassable`` / ``air_impassable``.
- Terreno com ``passable_units``: unidades fora da lista ouvem o título do tipo + ``passable_units_denied`` (5701); tipos na lista (incl. ``is_a``) ainda podem ``go``.
- **Código**: ``worldorders/base.py``, ``lib/square_terrain_rules.py``, ``clientgameentity/events.py``. **Testes**: ``test_water_impassable_order.py``.

**Correção: fantasma de neblina sem nome após suicídio de unidade**

- **Sintoma**: Após uma unidade se suicidar, percorrer alvos com Tab na mesma casa ainda podia selecionar um objeto sem nome legível.
- **Causa**: Após a morte ``place is None``, a memória da neblina de guerra não era limpa a tempo; objetos em memória podiam ter um ``title`` (sufixo de neblina) mas um ``short_title`` vazio, e Tab ainda os tratava como selecionáveis.
- **Correção**: ``perception.py`` esquece a memória quando ``initial_model.place is None``; unidades que saem da percepção não são memorizadas quando ``place is None`` ou quando são as próprias unidades mortas do jogador; ``game_unit_control.py`` ``is_visible`` exige um ``short_title`` não vazio.
- **Testes**: ``test_suicide_fog_ghost.py`` (caminhos de memória de neblina de cadáver e áudio ambiental preservados).

**Correção: HP de parede oscilando para cima e para baixo durante o ataque**

- **Sintoma**: Atacar ``wall`` e outras construções ``is_repairable`` podia fazer os sons de HP ou de mudança de vida subir e descer intermitentemente.
- **Causa**: Paredes herdam ``is_repairable=True`` das construções, então a lógica de ataque / reparo / limiar de captura podia interagir; a sincronização de HP na neblina (``_sync_memory_hp_from_live``) sem carregar o ``previous_hp`` entre trocas de visão de percepção/memória causava feedback falso de mudança de vida.
- **Correção**: ``world_order.py`` / ``worldcreature.py`` / ``worldworker.py`` — construções reparáveis inimigas usam por padrão ``go``, imperativo usa por padrão ``attack``; caminhos de reparo protegidos com ``not is_an_enemy(target)``; ``game_navigation.py`` preserva o rastreamento de HP em atualizações de neblina (``_take_hp_tracking`` / ``_apply_hp_tracking``).
- **Testes**: ``test_imperative_attack.py`` (ataque imperativo em paredes).

**Correção: ordem go normal interrompia incorretamente o ataque imperativo**

- **Sintoma**: Com uma unidade em ataque forçado (ex. prefeitura), um ``go`` normal interrompia o ataque, mas a seleção de grupo (ex. F) ainda anunciava «atacar a prefeitura, ir para \<casa\>» — comportamento e voz inconsistentes.
- **Causa**: ``take_order`` com ``forget_previous=True`` chamava ``cancel_all_orders()``, removendo o ataque imperativo e enfileirando ``go``, enquanto ``AttackAction`` podia permanecer na unidade.
- **Correção**: Com ordem imperativa ativa, comandos normais (exceto ``stop``) são enfileirados automaticamente (``forget_previous=False``) sem substituir a cabeça imperativa; a unidade conclui o ataque forçado antes do comando na fila. Após um imperativo só é permitido **um** comando enfileirado; um novo comando normal **substitui** o já enfileirado (como em 1.3.8.1).
- **Código**: ``worldunit/world_order.py`` ``take_order``.
- **Testes**: ``test_imperative_attack.py`` (``test_normal_go_queues_behind_imperative_attack``, ``test_only_one_queued_order_behind_imperative_attack``, etc.).

**Melhoria: descrições de voz do comportamento das unidades**

- Após selecionar um alvo com Tab, Ctrl+Backspace ou go + Ctrl+Enter confirma "atacar \<alvo\>" em vez de "ir" para unidades/construções inimigas.
- Seleção de grupo por atalho (ex. F para soldados de infantaria): "Você controla N soldados de infantaria atacando a prefeitura"; se movendo enquanto combate, acrescenta "ir para c6".
- **Código**: ``clientgameentity/base.py`` ``_attack_action_title_msg``; ``properties.py`` ``orders_txt``; ``game_orders.py`` ``_say_validate_confirmation`` / ``_say_default_confirmation``; ``game_unit_control.py`` ``say_group``.
- **Testes**: ``test_attack_orders_txt.py``, ``test_imperative_attack.py``.

**Melhoria: gritos de batalha em camadas**

- Três camadas: ``shout_bg`` (fundo do campo de batalha), ``shout_unit`` (voz da unidade), ``shout_event`` (destaques de primeiro choque / carga / crítico); tempos de recarga globais e por casa; ``formation_sound_queue`` espaça as rajadas para que os gritos não se acumulem com os sons de acerto no mesmo quadro.
- **Código**: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``.
- **Documentação**: ``mod/battle-shouts.rst``.
- **Testes**: ``test_battle_shout_audio.py``.

**Melhoria: refatoração do motor de áudio P0–P2**

- **Correção**: rascunhos anteriores descreviam P0–P2 como camadas de *prioridade* ambiental/combate/alerta; na verdade são **três fases de refatoração** do motor de áudio, distintas das urlas em camadas acima e de ``psounds.play(..., priority=…)``. Ver ``mod/audio-management.rst``.
- **P0 estrutura**: ``lib/music_resolver.py``; ``sound_cache.clear_decoded()`` ao trocar mod/mapa; correção de estado mutável em ``SoundSource`` / ``SoundManager``.
- **P1 UX**: ``audio/sfx_volume`` separado de ``main_volume``; espera de voz por event pump; fallback de música de menu unificado.
- **P2 polish**: LFO de ambiente; ``lib/battle_music.py``; limpeza do ``music_resolver``; SFX em ``ui/`` com ``.ogg`` / ``.wav`` / ``.mp3`` (``.ogg`` preferido) e pré-carregamento (``preload_sounds`` / ``tick_preload``).
- **Atalhos**: Home/End para SFX; Alt+Home/Alt+End para música.
- **Testes**: ``test_music_resolver.py``, ``test_audio_settings.py``, ``test_voice_pump.py``, ``test_ambient_stereo_volume.py``, ``test_battle_music.py``, ``test_sfx_formats.py``.

1.4.5.0
-------

Terreno configurável, contêineres de transporte, ``attack_inside_chance`` e mapas aleatórios:

**Terreno de casa configurável**

- O terreno é ``class terrain`` em ``rules.txt`` mais as definições correspondentes em ``style.txt``; sem terreno padrão do motor em todas as células.
- O mapa ``terrain <name>`` aplica passabilidade, água, velocidade e terreno elevado a partir das regras; ``class building_land`` estende prados e locais de construção.
- Editor de mapas e sintaxe de subcélula ``square/x,y``: ``mod/building-land-terrain.rst``.

**Contêineres de transporte**

- ``passenger_attack_types``: tipos de unidade que podem atacar alvos externos enquanto estão dentro do contêiner.
- ``load_bonus``: para cada unidade carregada, adiciona atributos ao contêiner.
- ``passenger_bonus``: atributos adicionados ao passageiro enquanto está dentro; removidos ao descarregar. Mesma sintaxe de ``load_bonus``; pode ser combinado com ``load_bonus``.

**``attack_inside_chance``**

- Propriedade de contêiner aberto: ataques externos atingem passageiros dentro nesta porcentagem (ex. parede ``attack_inside_chance 40``).

**Gerador de mapas aleatórios**

- Os modelos embutidos listam todos os terrenos ``rmg_terrain 1`` das regras; o posicionamento usa propriedades das regras.
- Arquivos ``random_map_template`` personalizados em ``cfg/randommap/`` ou ``mods/.../randommap/``.
- Códigos de compartilhamento: ``RMG1`` (abreviações embutidas) / ``RMG2`` (nomes personalizados completos).

Ver ``mod/building-land-terrain.rst``, ``mod/randommap.rst``, ``mod/modding.rst`` (Transport containers); testes ``test_transport_bonus.py``, ``test_attack_inside_chance.py``, ``test_randommap.py``.

**Construção de pontes sobre a água**

- Trabalhadores podem colocar trechos de ``wooden_bridge`` casa a casa sobre rios, lagos e oceanos (``is_buildable_on_water_only`` + ``bridge_terrain bridge_deck``).
- Fase de andaime: construção caminhável, sem passagem até a conclusão; trechos concluídos se ligam à margem / a outros decks; neutros para todos os jogadores.
- TTS do local corresponde às demais entradas ``buildingsite``; passos usam ``bridge_deck`` / ``big_bridge`` ``ground wood``.
- Documentação: ``mod/water-bridge-building.rst``; testes: ``test_bridge_terrain.py``.

**Modificadores de combate de unidades em terreno**

- ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``: bônus de ataque, tempo de recarga e carga por terreno para a **casa atual do atacante** (mesma sintaxe de lista ``terrain value …`` de ``speed_on_terrain``).
- Modificadores de dano negativos enfraquecem ataques; ``*_cd_on_terrain`` positivos alongam o tempo de recarga.
- Documentação: ``mod/building-land-terrain.rst``; testes: ``test_combat_terrain_modifiers.py``.

**Passos e sons de queda em terreno**

- ``move_on_<key>`` / ``falling_on_<key>`` agora aceitam **nomes de tipo de terreno** (ex. ``ocean``) e categorias ``ground`` de ``style.txt`` (ex. ``water``, ``grass``); o nome do tipo é tentado primeiro.
- Correção: em terrenos sem ``ground`` (ex. ``ocean``), ``falling_on_ocean`` nunca correspondia antes e apenas o ``falling`` genérico era reproduzido.
- Documentação: ``mod/modding.rst`` (Combat sound system); testes: ``test_falling_terrain_sound.py``.

**Gritos de batalha (reprodução em camadas)**

- Três camadas no combate: fundo do campo de batalha, voz da unidade, destaques de evento; tempos de recarga globais/por casa.
- ``ui/style.txt``: ``shouts`` em ``def walking_unit``; dispara quando qualquer lado tem ≥5 unidades combatendo na casa.
- Código: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``; testes: ``test_battle_shout_audio.py``.
- Documentação: ``mod/battle-shouts.rst``.

1.4.4.9
-------

Corrigido um bug em que a distância mínima efetiva de carga não funcionava.

Documentação atualizada.

1.4.4.8
-------

Terreno de subcélula para autores de mapas e editor de mapas:

Terreno de subcélula dentro de uma casa

- Comandos de terreno podem mirar em uma área dentro de uma casa com a sintaxe ``square/x,y``, por exemplo ``high_grounds a1/1,1 a1/1,2``.
- ``subcell_precision N`` controla a subdivisão. O padrão é ``3`` e aceita valores de ``2`` a ``20``.
- Comandos suportados: ``terrain``, ``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` e ``no_air``.
- Combate, movimento, velocidade de terreno, cobertura e checagens de terreno elevado podem usar a subcélula real da unidade.

Navegação em zoom e comportamento do editor

- A navegação de mapa no modo zoom anuncia o terreno da subcélula atual, incluindo terreno elevado parcial.
- No editor de mapas experimental, Enter aplica o terreno selecionado à subcélula atual enquanto o modo zoom está ativo.
- Mapas salvos gravam substituições de subcélula com a sintaxe ``square/x,y``.

1.4.4.7
-------

Fórmulas de limiar de XP de herói (``xp_threshold_growth``) e reset de XP após subida de nível (``level_up_reset_xp``):

``Fórmulas de limiar de XP de herói (``xp_threshold_growth``)``

- Definições de herói podem definir ``max_level`` + ``xp_threshold_growth``; o carregamento de ``rules.txt`` preenche automaticamente ``xp_thresholds`` para que os modders não precisem listar dezenas ou centenas de valores de XP cumulativos à mão.
- Tipos de curva: ``linear``, ``quadratic``, ``polynomial``, ``geometric`` (ver Heroes em ``modding.rst``).
- Compatível com ``xp_thresholds`` explícito (a lista explícita vence). Definições filhas podem herdar ``xp_threshold_growth`` via ``is_a`` e substituir apenas ``max_level``.
- Implementação: ``soundrts/xp_threshold_growth.py``, ``soundrts/definitions.py``; testes: ``test_xp_threshold_growth.py``.

``Reset de XP após subida de nível (``level_up_reset_xp``)``

- Opcional ``level_up_reset_xp 1`` em definições de herói: o XP atual se torna 0 após cada subida de nível em combate; o padrão ``0`` mantém o XP cumulativo.
- Quando ``1``, prefira ``xp_thresholds`` por nível, não totais cumulativos.
- Implementação: ``soundrts/worldunit/world_status_update.py``; testes: ``test_level_up_combat_stats.py``.

1.4.4.6
-------

Limpeza de nomenclatura de sons de mod, sistema de habilidades unificado, efeitos de habilidades genéricos, filtros de alvo de habilidade e exclusões -tag, escala de atributos em subida de nível, desbloqueio de habilidades por nível, transferência de herói de campanha, sons de uso de itens da mochila, sons de ready/prep personalizados, alternância de atalho de mochila/equipamento, nível inicial de herói e exibição de XP de nível 0:

Renomeação de chaves de som de ataque

- Os sons de ataque em ``ui/style.txt`` agora preferem as chaves ``mdg`` / ``rdg``:
  ``launch_mdg`` / ``launch_rdg``, ``mdg_hit`` / ``rdg_hit``,
  ``mdg_hit_vs`` / ``rdg_hit_vs``, ``mdg_missed`` / ``rdg_missed``,
  e ``mdg_dodge`` / ``rdg_dodge``.
- Sons de carga usam ``launch_charge_mdg`` / ``launch_charge_rdg`` e
  ``charge_mdg_hit`` / ``charge_rdg_hit``.
- Os arquivos ``style.txt`` empacotados foram migrados; as chaves antigas ``matk`` / ``ratk`` permanecem compatíveis como fallback.

Sons de ready personalizados

- Habilidades com ``ready \<seconds\>`` podem definir ``ready \<sound\>`` no estilo da habilidade; gatilhos manuais e automáticos o reproduzem quando a preparação começa.
- A preparação de ataque normal pode reproduzir sons ``mdg_ready`` / ``rdg_ready`` do estilo da unidade.

Sistema de habilidades unificado

- Uma ``class skill`` pode ser tanto usada manualmente quanto disparada automaticamente; não requer listas gêmeas separadas.
- Campos de habilidade: ``auto_trigger 1``, ``manual_use 1`` (padrão 1), ``trigger_timing``.
- ``trigger_timing``: ``on_hit`` | ``on_attack`` | ``on_attack_replace`` | ``on_damaged``.
- Habilidades aprendidas vivem em ``can_use_skill``; o menu de comandos mostra apenas habilidades ``manual_use 1``.
- Listas legadas ainda funcionam: ``active_trigger_skills``, ``attack_trigger_skills``,
  ``attack_replace_skills``,   ``passive_trigger_skills`` permanecem compatíveis junto aos novos campos.

Efeitos de habilidades genéricos

- Dano fixo ``harm_target N`` / ``harm_area N R``; dano de combate ``harm_target mdg`` / ``harm_area mdg R`` (pipeline completo).
- Combos ``burst mdg N (interval X)`` ou `` (delays …)``; knockback ``push``; ``buffs`` / ``debuffs``; ``deploy``; ``summon``.
- Legados ``teleportation`` / ``recall`` / ``conversion`` / ``raise_dead`` / ``resurrection`` ainda funcionam.
- Taxas de gatilho, condições de HP, listas de buff/debuff no início do ataque permanecem compatíveis; ver ``mod/skills-and-effects.htm``.

``Filtros de tipo de alvo e exclusões (``-tag``)``

- ``class skill`` suporta ``harm_target_type`` em ``burst`` / ``harm_target`` / ``harm_area`` / ``push``; padrão apenas inimigos quando não definido.
- O prefixo ``-`` exclui uma tag (ex. ``-building``). Aplica-se a ``harm_target_type``, ``heal_target_type``, ``mdg_targets`` / ``rdg_targets``, ``target_type`` de buff/debuff.
- Exclusões de diplomacia: ``-enemy``, ``-allied``, ``-neutral``.
- Exemplos: ``harm_target_type enemy unit -building``; ``heal_target_type unit -undead``; ``mdg_targets -building``.

**Bônus de atributos em subida de nível (``*_per_level``)**

- Unidades podem definir ``\<stat\>\_per_level`` em ``rules.txt`` para a maioria dos atributos de combate, vida, mana, heal/harm e regen; cada subida de nível adiciona um passo.
- Exemplos: ``hp_max_per_level``, ``mdg_per_level``, ``charge_mdg_per_level``, ``mdg_crit_rate_per_level``, ``mana_max_per_level``, ``heal_cd_per_level``, etc.
- A restauração de herói de campanha reaplica bônus cumulativos até o nível salvo.

Nível inicial de herói e exibição de status

- ``level`` / ``xp`` em definições de herói em ``rules.txt`` (requer ``xp_thresholds``); ``level \> 1`` aplica ``*_per_level`` cumulativos no spawn.
- ``level 0``: começa abaixo do nível 1; o status de Tab mostra nível 0 e XP em direção a ``xp_thresholds[0]``.
- Heróis com ``xp_thresholds`` sempre anunciam o nível no status de Tab (incluindo 0 e 1).

``Cura completa ao subir de nível (``level_up_heal_full``)``

- Opcional ``level_up_heal_full 1`` em definições de herói: restaura HP e mana completos a cada subida de nível; o padrão ``0`` mantém apenas o ganho incremental de HP/mana.

Desbloqueio de habilidades por nível e livros de habilidades

- Unidade ``level_skills \<level\> \<skill\> …``: adiciona automaticamente a ``can_use_skill`` quando esse nível é atingido (com notificação por voz).
- Unidade ``learn_level_skills``: portão extra de aprendizado por livro (o mais restritivo com ``learn_level`` do item).
- Livros de habilidades: aprendizado permanente via ``use_item`` da mochila; a coleta não concede quando há portão.
- Não duplicar a mesma habilidade em ``level_skills`` e em um livro.

Transferência de herói de campanha

- Definições de herói: ``campaign_carryover 1`` (opcionais ``campaign_carryover_stats``, ``campaign_carryover_inventory``, ``campaign_carryover_id``).
- Na vitória, nível/XP e mochila são salvos em ``user/campaigns.ini``; o próximo capítulo restaura; cooperativo não persiste.
- Opcional ``hero_min_level 13:2 …`` em ``campaign.txt`` para pisos de nível por capítulo.

Sons de uso de itens da mochila (style.txt)

- Mesma busca de três níveis que coleta/drop: item ``use`` / ``on_use`` → unidade ``use_\<item type\>`` → global ``item_used`` (``def thing``).
- Sons tocam apenas após sucesso confirmado pelo servidor; sem voz otimista de "usado" em Enter.
- Livros de habilidades: som de uso + título da habilidade + ``skill_learned``; outros consumíveis: título do item + "usado".
- Consumíveis são removidos do inventário em caso de sucesso; ``unequip`` de livro de habilidades não retira mais habilidades aprendidas permanentemente.

Atalhos de mochila / equipamento

- Shift+V alterna entre mochila e equipamento (clássico e em camadas); Ctrl+V removido; F3 em camadas ainda funciona.

Documentação: ``mod/modding.rst``, ``mod/modding.rst``, ``mod/skills-and-effects.htm``, ``mod/campaign-hero-carryover.htm``
Testes: ``test_level_skills.py``, ``test_level_up_combat_stats.py``, ``test_campaign_hero.py``, ``test_wuxia_skills.py``, ``test_worldskill_deploy.py``, ``test_target_type_exclusions.py``, ``test_hit_vs_buff_sounds.py``, ``test_damage_seq_burst.py``,
``test_changelog_138x.py``, ``test_skill_trigger_sounds.py``, ``test_inventory_backpack.py``


1.4.4.5
-------

Jogabilidade de mapa aleatório estilo HoMM/Civ5, ordem de captura padrão, operações anfíbias da IA, correção de pontuação Ctrl+Shift+F4, editor de mapeamento de atalhos:

Mapa aleatório: inspiração HoMM / Civ5

- menu de modo de vitória: conquest / economic / exploration / survival (TTS 5425–5430)
- POIs do mapa: ruínas antigas, casernas capturáveis, creeps centrais, tesouro opcional
- códigos de compartilhamento: 11º campo de vitória; ``res/rules.txt``: ``ancient_ruin``, ``captured_barracks``
- documentação: ``player/英雄无敌与文明5玩法说明.htm``; ``randommap.rst``
- testes: ``test_randommap.py``

Ordem de captura padrão (can_capture)

- ``capture_hp_threshold 100``: ``can_capture 1`` → ocupação padrão; ``can_capture 0`` → apenas ataque/movimento
- limiares abaixo de 100 ainda exigem combate até o limiar de captura
- documentação: ``mod/modding.rst``; jogadores ``player/unit-default-behavior.htm`` §4
- testes: ``test_capture_default_order.py``

Operações de IA através da água

- reunião anfíbia, assaltos com transporte, manutenção naval em mapas de água
- testes: ``test_worldplayercomputer_water.py``, ``test_ai_naval_m3.py``

Treinar: escalar o lote à população restante

- espaço de população insuficiente ao treinar em lote → treina quantos couberem (ex. 5 solicitados, 3 pop → 3 treinados); zero espaço ainda falha
- ``worldorders/production.py`` (``TrainOrder._max_train_count_for_population``)
- testes: ``test_train_population.py``

Correção: troca de vista Ctrl+Shift+F4 vs pontuação

- fixa o humano de pontuação; sem recompensas de vitória de IA/passivo após a troca; linha de base dos inimigos de pontuação derrotados na primeira troca
- testes: ``test_change_player_scoring.py``

Editor de mapeamento de atalhos

- Opções → Key mapping (irmão do Hotkey scheme); ``hotkey_remapping_menu.py``, ``hotkey_editor.py``, ``hotkey_catalogs.py``
- 8 camadas em camadas + ~179 ligações clássicas; por mod ``user/hotkey_overrides/{mod_key}.json``; eficaz no próximo início de partida
- busca, variantes avançadas, teclas de alias (``binding_id@default_key``), importar/exportar via área de transferência
- catálogo TTS 5500–5684; variantes avançadas clássicas completas; correções de rótulos de grupos de controle
- rótulos: Alt+Space → modo primeira pessoa; Ctrl+F2 → alternar exibição
- documentação: ``mod/hotkey-mapping-editor.htm``, ``player/layered-hotkeys.htm``
- testes: ``test_hotkey_editor*.py``, ``test_hotkey_catalog_tts.py``, ``test_hotkey_editor_mod_isolation.py``

1.4.4.4
-------

Cartas de carregamento atrasadas, pontuação e notas, conquistas por facção, progresso meta, CrazyMod, correções de UX:

Cartas pré-missão atrasadas

- ``cards.txt``: ``delay \<seconds\>``, ``delay_minutes \<n\>`` — agenda efeitos após o tempo do jogo (``world.schedule_after``, respeita ``timer_coefficient``)
- ``tech \<upgrade_id\>`` nas cartas; combinável com ``spawn`` / ``resource`` sob um atraso compartilhado
- voz ao aplicar: efeitos após N minutos/segundos; ao disparar: efeito de carta de carregamento ativado (TTS 5387–5393)
- vanilla: ``card_reinforcements_delayed`` (3 footman após 10 min), ``card_delayed_melee_weapon`` (``melee_weapon`` após 8 min)
- conquistas: ``reinforcement_contract`` → reforços atrasados; ``defeat_expert`` → carta de arma corpo a corpo atrasada
- documentação: ``mod/delayed-card-loadout.htm`` (jogadores: ``player/loadout-cards.htm``)
- testes: ``test_cards.py``, ``test_card_loadout.py`` (``-k delay`` / ``-k delayed``)

Pontuação pós-partida e notas por letra

- documentação: ``mod/score-grading-system.htm`` (jogadores: ``player/score-and-grades.htm``)
- as sete dimensões base limitam-se a 800; o bônus de derrota de IA é extra e excluído do denominador percentual
- nota de derrota limitada a D (``grade_total`` máx 479)
- vitória + utilização < 50%: dimensão de eficiência frugal (TTS 5251)
- mineração em mapas sem capacidade de depósito: proporcional à coleta de referência (1000 = 100 pts); mapas de campanha sem depósito inalterados
- sobrevivência 0 se nenhuma unidade produzida; perda/demolição de construção 5 pts por construção (era 10)
- removidos helpers de pontuação legados não usados de ``worldplayerbase/resources.py``
- testes: ``test_score_breakdown.py``

Dados de conquistas e patentes

- Tenente (``rank_lieutenant``): 200 medalhas, 1 slot de carregamento
- ``defeat_beginner`` medalha de repetição 8; ``perfect_survival`` exige sobrevivência ≥90 e defesa de construções ≥90

Correções

- trabalhador ``can_gather all``: a UI de atributos não duplica mais "all" quando as listas de depósito e de construção são ambas ``all``
- testes: ``conftest`` restaura ``res.mods`` após testes de troca de mod
- UX de carregamento / facção aleatória; transmissão de derrota de NPC controlada por ``broadcasts_defeat_and_quit``

Progresso por facção e meta

- ``achievements_per_faction 1``, ``\_meta.json``, ``scope meta``; campanha excluída

CrazyMod 9

- marcos por facção, tiers meta, ajustes de equilíbrio

Documentação (jogador / desenvolvedor)

- Índice: ``help-index.htm``, ``player/README.htm``, ``mod/README.htm``

Transferência de herói de campanha (guiada por regras)

- ``rules.txt``: ``campaign_carryover 1`` (opcionais ``campaign_carryover_id``, ``campaign_carryover_stats``, ``campaign_carryover_inventory``)
- ``campaign.txt``: ``hero_min_level 13:2 …`` para pisos de nível por capítulo
- salvo na vitória em ``user/campaigns.ini`` (``hero_\<id\>\_xp`` / ``\_level`` / ``\_inventory``); restaurado no próximo capítulo; cooperativo não persiste
- independente de ``campaign_flag`` / ``add_inventory_item``; ver ``modding.rst``, ``mapmaking.rst``, ``mod/campaign-hero-carryover.htm``
- implementação: ``soundrts/campaign_hero.py``; testes: ``test_campaign_hero.py``

Correções e voz

- mapas lanes: ``has_entered`` com coordenadas 1-based (ex. ``8,2``) não colide mais com chaves de grade 0-based; gatilhos de ruínas funcionam
- entradas de texto (código de compartilhamento, seed, etc.): Ctrl+V cola via API de área de transferência do pygame-ce
- TTS de HoMM/Civ5 e missões secundárias de campanha movidos de 5107–5123 para 5425–5441 para evitar conflitos de ID

1.4.4.3
-------

Conquistas e arsenal (fases 2–3: medalhas, patentes, cartas, carregamento pré-missão):

- nova entrada Conquistas no menu principal: lista de conquistas + arsenal (patente, honras, total de medalhas, cargas de cartas)
- após escaramuça / mapa aleatório vs computador, os desbloqueios de ``achievements.txt`` são avaliados; voz para desbloqueios, medalhas, cartas, promoção de patente e slots extras de carregamento
- o progresso é salvo por mod: ``user/achievements/\<mod\>.json``
- carregamento de cartas pré-missão: Single player → Start on map → Start, depois escolha até N cartas por patente (Tenente = 1 slot, Capitão = 2, … em ``titles.txt``); apenas TrainingGame (mapa personalizado ou aleatório vs IA — não campanha ou multijogador)
- efeitos aplicam-se no início da partida: recursos bônus e/ou unidades perto do seu início; uma carga gasta por carta usada
- spawns de cartas não usam população; spawns de facção aleatória usam equivalentes de facção
- correção: cartas de carregamento não eram aplicadas porque o jogador local era detectado apenas após ``GameInterface`` existir; agora aplicadas após o carregamento do mapa, antes de a interface abrir
- arsenal: navegar por uma carta anuncia seu efeito (bônus inicial, spawns, patente exigida se bloqueada)
- conclusão repetida: satisfazer novamente uma conquista já desbloqueada concede apenas medalhas ``repeat_medal \<n\>`` (sem carta, honra ou voz de desbloqueio); medalhas ainda fazem a patente avançar
- opt-out de mod: ``achievements_enabled 0`` em ``rules.txt`` oculta a entrada de menu e pula carregamento / processamento pós-partida
- ``Os bônus ``starting_units`` da IA em ``ai.txt`` não consomem população`` (inícios de mapa ainda consomem); ``starting_population`` é inalterado
- dados: ``res/achievements.txt``, ``res/cards.txt``, ``res/titles.txt``; IDs TTS 5244–5367, etc.
- documentação: ``achievement-system.htm`` (``achievement-system.htm``)
- testes: ``test_achievements.py``, ``test_cards.py``, ``test_titles.py``, ``test_card_loadout.py``

1.4.4.2
-------

Miragem de counter da IA (``counter_skill`` em ``ai.txt``):

- unidades do computador usam ``mdg_vs`` / ``rdg_vs`` (e herança ``is_a``) ao escolher alvos e enviar ataques
- novo comando de script ``counter_skill \<0-100\>``: ``0`` = ignora counters (apenas ``menace``), ``100`` = sempre escolhe o melhor counter; valores intermediários mesclam ambos
- níveis vanilla em ``res/ai.txt``: beginner ``25``, intermediate ``50``, advanced ``75``, expert ``90``, nightmare ``100``; omitido em um script de mod, padrão ``100``
- novos ``starting_resources`` / ``starting_units`` em ``ai.txt``: recursos e unidades bônus adicionados sobre o início do mapa para computadores convidados (mesma sintaxe dos comandos de mapa; aplicados uma vez no início da partida, não no loop do script)
- novo ``starting_population`` em ``ai.txt`` e mapas: teto de população bônus (inteiro simples, não ×1000) adicionado sobre casas/unidades; ainda limitado por ``global_population_limit``
- inícios bônus vanilla: intermediate +50/+50 recursos; advanced +100/+100 e 2 footman 2 archer; expert +200/+200 e exército 5/4/2; nightmare +400/+400 e exército 8/6/4
- documentação: ``doc_src/src/en/aimaking.rst``, ``doc_src/src/zh/aimaking.rst``
- testes: ``test_ai_counter_targeting.py``, ``test_ai_loader_and_menu.py``, ``test_ai_start_settings.py``

1.4.3.9
-------

Atalhos de interface em camadas (base global + camada por modo):

- ``bindings.txt`` único dividido em ``global_bindings.txt`` e sete arquivos de modo (unit/building/command/skill/help/map/diplomacy); ordem de carregamento: global → modo atual → ``cfg/bindings.txt`` → acréscimo de mod
- alternância por tecla F: F1 unit↔building, F2 command↔skill, F3 inventory↔equipment, F4 help & query, F12 diplomacy, ESC entra/sai da navegação de mapa; nome do modo anunciado ao alternar
- camada global mantém recursos (z/x/SHIFT z/c), movimento, saltos de casa, confirmação de comando, F9/F11, etc.; antigos F1/F4 help e F12 diplomacy direto agora entram em modos dedicados de sobreposição
- modo unit: trabalhadores ``s``/``w`` (era ``d``/``e``); soldados 1–7 em ``d/e``…``;``/``p``; modo building slots ``building1``–``building16`` (``d/f/g/h/j/k/l/;`` + ``e/r/t/y/u/i/o/p``)
- modo command atalhos de índice de 30 slots; modo map ``f/g/m/p`` percorre depósitos/prados/passagens na casa atual (sem saltos de casa); ESC para o mapa anuncia o resumo da casa e restaura silenciosamente o último alvo do mapa
- mod ``style.txt``: ``keyboard worker``, ``keyboard soldier1``–``7``, ``keyboard building1``–``16``; o corpo de ``bindings.txt`` agora é um stub de compatibilidade
- subtelas de inventário/equipamento/atributos chamam ``restore_active_bindings`` ao sair; atalhos do editor inalterados
- atalhos clássicos de arquivo único: `````[general] layered_hotkeys = 0``` em ``user/SoundRTS.ini`` (padrão ``1`` = em camadas); ou menu principal Opções → Hotkey scheme — Layered hotkeys / Classic hotkeys (efetivo na próxima partida); clássico carrega ``legacy_bindings.txt``, sem camadas de modo F, ESC não entra na navegação de mapa
- mods podem personalizar cada esquema: em camadas via ``ui/*_bindings.txt`` ou acréscimo em ``ui/bindings.txt``; clássico via ``ui/legacy_bindings.txt`` ou acréscimo em ``ui/bindings.txt``
- documentação: ``../player/layered-hotkeys.htm``, ``../player/layered-hotkeys.htm``
- testes: ``test_layered_bindings.py``, ``test_map_browse_target_persist.py``

Campanhas estilo Age of Empires DE (single-player + cooperativo):

- single-player: navegador de missões (``synopsis``, cinco níveis de dificuldade persistidos, capítulos concluídos/bloqueados, repetir); HP/dano do inimigo escalam por nível (Standard + solo = 100%)
- cooperativo: missão de história multijogador (slots de jogador + aliados de IA, introdução/cutscenes/objetivos compartilhados, sem trégua); dificuldade e contagem de humanos escalam inimigos; TTS de campanha carregado automaticamente para nomes de locais localizados
- ver ``../player/campaign-menu.htm`` (``../player/campaign-menu.htm``)
- testes: ``test_changelog_1429_coop_campaign_difficulty.py``, ``test_changelog_1429b_campaign_browser_difficulty.py``, ``test_changelog_1429c_coop_story_mission.py``, ``test_changelog_1429d_coop_player_slots.py``, ``test_coop_campaign_place_names.py``

1.4.3.8
-------

Campos de construção, objetivos progressivos e tumores de creep Zerg:

- ``build_field_radius`` (BFS em casas) vs ``build_field_radius_m`` (metros a partir de `` (x,y)``); provedores de metro pintam marcas quando ``build_field_persists`` / ``build_field_spreads`` — corrige checagens de construção de creep por metro só no Hatchery
- Gatilho ``register_objective`` registra números primários para vitória sem F9/voz; a vitória usa ``\_required_objective_numbers`` vs ``\_completed_objective_numbers`` (sem vitória prematura quando objetivos são revelados um a um)
- F9 / ``add_objective``: "Primary objective N:" quando há múltiplos objetivos; dois-pontos após o número; objetivo único omite o número
- mod StarCraft: Queen Spawn creep tumor / tumor Extend creep tumor; attrs de habilidade ``summon_requires_build_field``, ``summon_requires_marked_field``
- documentação: ``campaign/progressive-objectives.htm``, ``../player/starcraft-zerg-creep.htm``; ``modding.rst``, ``mapmaking.rst``
- testes: ``test_build_rules.py`` (creep tumor), ``test_campaign_alliance_transfer_triggers.py`` (register_objective), ``test_objective_announce.py``

1.4.3.7
-------

Sistema de caça e rótulos de voz de vida selvagem:

- caça estilo Age of Empires: animais ``is_huntable`` deixam depósitos de ``food_carcass``; trabalhadores os coletam; veados/ovelhas fogem; ovelhas podem ser conduzidas (``can_herd`` / ``herdable``)
- vida selvagem anunciada como "animal" (ex. "veado , animal"), não "neutro , NPC"; resumos de casa usam um balde de animais separado
- slots de vida selvagem apenas ``computer_only`` não entram na aliança ``"ai"`` (não com jogadores, creep hostil ou outros rebanhos; slots mistos inalterados)
- Ctrl+Shift+F4 para um jogador só de vida selvagem diz "you are animal"; jogadores mistos de NPC + vida selvagem ainda dizem "you are neutral NPC"
- mapas aleatórios geram vida selvagem e pomares perto dos inícios; ``hunting_techniques`` melhora a coleta de carcaças
- documentação: ``../player/hunting.htm``; seção de caça em ``modding.rst``
- testes: ``soundrts/tests/test_hunting.py``, ``test_hunting_herd.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``

1.4.3.6
-------

Ataques em rajada / sequência (``damage_seq``):

- intervalo de rajada fixo: as regras ``(interval …)`` agora são respeitadas (era hardcoded em 0,4 s)
- omitir ``(damage …)`` para dividir automaticamente o ``mdg`` / ``rdg`` base de forma uniforme (suporta dano fracionário)
- cada disparo numa rajada dispara ``launch_mdg`` / ``launch_rdg``; liste múltiplos IDs de som em ``style.txt``
- regras base: novo ``repeating_crossbowman`` (upgrade a partir de archer; estilo Chu Ko Nu de Age of Empires)
- testes: ``soundrts/tests/test_damage_seq_burst.py``
- documentação: ``../player/burst-attacks.htm``; seção Combat system em ``modding.rst``

1.4.3.5
-------

IA de combate vs unidades neutrais:

- unidades do jogador em modo ``offensive``, ``defensive`` ou ``chase`` não atacam
  automaticamente unidades neutrais (``computer_only ... neutral``)
- modo defensivo não foge quando apenas neutrais estão presentes
- ataque forçado (``imperative`` go/attack, ex. Ctrl+clique na unidade) ainda funciona
- creeps neutrais mantêm guarda + contra-ataque do seu lado; ver ``../player/unit-default-behavior.htm``

1.4.3.4
-------

Gerador procedural de mapas aleatórios (RMG):

- Entrada: menu principal Start a game → Random map; ou Random map na lista de mapas de criação de partida online
- Opções: modelo (standard/fast/macro/lanes), tamanho, contagem de jogadores, times 2v2, monstros, recursos, terreno, água, tesouro, seed, trégua
- Após a geração, seed e código de compartilhamento são anunciados; F5/F6 os repetem do histórico de voz (ainda disponíveis no menu de convidar IA)
- Importar código de compartilhamento pula os menus passo a passo; formato ``RMG1:…`` — ver `Guia de mapa aleatório <randommap.htm>`_
- Entradas de texto de menu (código de compartilhamento, seed, login, etc.) suportam Ctrl+A/C/V/X selecionar tudo, copiar, colar, recortar
- Código: ``soundrts/randommap.py``, ``soundrts/randommap_menu.py``; testes ``soundrts/tests/test_randommap.py``

1.4.3.3
-------

Condições indexadas (``killed_target`` / ``npc_has_item`` / ``unit_lost`` / ``building_lost`` / ``key_unit_killed``):

- Índice global de spawn (qualquer casa): ``(killed_target \<index\> \<type\> [enemy|ally])``, `` (npc_has_item \<index\> \<type\> \<item\>)``, `` (unit_lost \<index\> \<type\>)``, `` (building_lost \<index\> \<type\>)``, `` (key_unit_killed \<index\> \<type\>)``
- Índice por casa: ``(killed_target \<square\> \<index\> \<type\>)``, `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``, etc.
- Mesmas regras de índice de ``killed_target`` / ``npc_has_item``; apenas a N-ésima unidade/construção gerada naquela casa
- Exemplo: ``(building_lost 1 townhall) (defeat)`` falha apenas se a 1ª prefeitura gerada for destruída (qualquer casa); `` (building_lost a1 1 townhall)`` é específica por casa; `` (unit_lost 3 footman) (defeat)`` falha apenas se o footman nº 3 morrer
- Demo: The Legend of Raynor capítulo 1; ver ``campaign/unit-index.htm``
- Testes: ``soundrts/tests/test_map_select_loss_triggers.py``

1.4.3.2
-------

Unidades sem numeração (rules.txt, ``no_number 1``):

- Aplica-se apenas a tipos de unidade com ``no_number 1``; unidades padrão (ex. camponeses) sempre mantêm números de série ("peasant 1 at a1")
- Com ``no_number 1`` e apenas uma unidade viva daquele tipo: sem número de série ("Guan Yu at a1", "knight leader at a1")
- Com ``no_number 1`` e dois ou mais daquele tipo: números de série ("Guan Yu 1", "Guan Yu 2")
- Resumos de grupo, casa e batalha seguem a mesma regra (ex. "you control Guan Yu and 2 escort knights")
- Ver ``modding.rst``; exemplos de campanha ``raynor``, ``npc_knight_leader`` em ``The Legend of Raynor/rules.txt``

1.4.3.1
-------

Inventário e equipamento:

- Shift+V: mochila (todos os itens no inventário); Ctrl+V: equipamento (armas e armaduras)
- mutuamente exclusivo com a tela de propriedades Alt+V; exige exatamente uma unidade aliada selecionada
- teclas na tela: setas navegam, Enter equipar/usar, Shift+Enter desequipar, Delete/Shift+Delete descartar, g lê a introdução
- modelo de item unificado: ``class item`` com ``equippable_as_weapon 1`` / ``equippable_as_armor 1``; atributos aplicam-se ao equipar
- ``weapons`` / ``armor`` iniciais que são itens equipáveis entram automaticamente no inventário; equipados silenciosamente quando não há equipamento embutido daquele tipo e ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` é 1 (padrão; requer ``inventory_capacity`` > 0)
- legado ``class weapon`` / ``class armor`` permanece embutido (somente leitura na tela de equipamento)
- equipamento embutido + item misto: embutido equipado no spawn; com ``spawn_weapons_equipped 1``, itens de arma ficam na mochila e não podem ser equipados; embutido troca apenas com embutido, item apenas com item, sem troca cruzada (o mesmo vale para armadura)

Comportamento padrão de unidade (rules.txt):

- ``ai_mode``: modo de IA inicial — ``offensive``, ``defensive``, ``guard`` ou ``chase`` (não ``patrol``)
- ``auto_gather`` / ``auto_repair``: coleta e reparo automáticos do trabalhador no início da partida (padrão 1)
- ``auto_explore``: unidades móveis começam com auto-exploração ativada (padrão 0)
- ``can_auto_explore 1``: o menu da unidade oferece comandos para ativar/desativar a auto-exploração

Dar itens a NPCs:

- ordem ``give``: botão direito em uma unidade não hostil, menu de comandos ou atalho ``g``
- o alvo precisa de ``receive_items 1``; opcional lista de permissão ``accepted_items`` e filtro de relação ``accept_from``
- condição de gatilho ``npc_has_item``; demo multijogador ``res/multi/give_demo.txt``; campanha cap. 14–16 (``The Legend of Raynor/14.txt``\ –``16.txt``) para entrega a aliado/neutro/inimigo
- sintaxe de índice de unidade em ``npc_has_item`` / ``killed_target`` (``\<square\> \<index\> \<type\>``); demo The Legend of Raynor capítulo 28; ver ``campaign/unit-index.htm``

Vitória de encontrar item:

- condição de gatilho ``has_item`` checa o inventário do jogador por um tipo de item dado (contagem opcional)
- o item deve permanecer no inventário (``consume_on_pickup`` não deve ser 1)
- exemplo: The Legend of Raynor capítulo 17 (``lost_amulet``)

Levar-à-casa e entrega narrativa:

- condição de gatilho ``has_brought_item``: uma unidade do jogador chega a uma casa carregando um item (sem drop)
- ação de gatilho ``remove_item``: remove e destrói itens dos inventários do jogador; use com ``cut_scene`` para entrega narrativa
- ação de gatilho ``do``: executa várias subações em ordem (``if`` não pode substituir isso)
- exemplo: The Legend of Raynor capítulo 18 (``mana_potion`` no santuário c3)

Itens no chão e condições compostas:

- ação de gatilho ``remove_ground_item``: exclui itens no chão numa casa (ex. remover tesouro após abrir)
- condição de gatilho ``and``: verdadeira apenas quando todas as subcondições são verdadeiras
- sintaxe ``find``: casa antes do tipo, inclusive dentro de ``not``; ordem errada torna as condições quase sempre verdadeiras
- exemplo: The Legend of Raynor capítulo 20 (descartar tesouro, depois coletar todas as moedas de ouro)

Diplomacia de campanha e gatilhos de transferência de unidade:

- ação de gatilho ``alliance_request``: um jogador pede aliança; em campanhas o humano aceita com Ctrl+F4 (sem seleção de alvo em F12)
- condições de gatilho ``alliance_with`` / ``alliance_request_pending``
- ação de gatilho ``transfer_units`` (aliases ``convert_units``, ``change_owner``): muda a posse de unidades entre jogadores
- ação de gatilho ``allied_assist``: unidades aliadas lutam por conta própria (guarda→perseguição); seletor de unidade opcional para troca parcial
- ação de gatilho ``allied_control``: concede comando direto sobre o exército de um aliado (aliado inteiro ou unidades selecionadas); unidades não correspondentes mudam para perseguição
- ação de gatilho ``add_inventory_item``: coloca itens no inventário da unidade (carregamento entre capítulos, recompensas de missão)
- ações de gatilho ``set_ai_mode`` / ``set_yield_on_defeat``: modo de IA em tempo de execução e alternâncias de rendição-duelo
- condições ``units_yielded`` / ``units_yielded_by``, ``has_entered``; ações ``stop_all_units`` / ``release_yielded_units``: contagens de rendição (filtrar por atacante), entrada em casa, cessar-fogo, restaurar combate
- The Legend of Raynor capítulos 24–27 (arco da aliança do norte); ver ``../player/campaign-northern-arc.htm``

``Sintaxe de exclusão ``phase_targets``:

- um ``-`` inicial exclui uma correspondência (ex. ``phase_targets -building`` = todas as unidades exceto construções)
- inclusões e exclusões podem ser misturadas (ex. ``phase_targets soldier -footman``)

``Herança de exclusão ``is_a`` com prefixo ``-``:

- ex. ``is_a footman(-hp_max)`` equivale a ``is_a footman(apart hp_max)``
- múltiplas exclusões: ``is_a footman(-hp_max -mdg)``

Bugs corrigidos:

- corrigida a perda de seleção de unidade após um upgrade ``can_upgrade_to`` ou morph ``can_change_to``: por exemplo, um archer selecionado com g permanece selecionado após o upgrade para dark archer, sem precisar reselecionar


1.4.3.0
-------

Bugs corrigidos:

- corrigido um bug sério de vitória em campanha: quando um mapa de campanha tinha dois ou mais computadores inimigos, completar os objetivos não encerrava a partida; a causa raiz era mutar a lista de jogadores durante a iteração no assentamento de vitória
- corrigidas unidades e objetos desaparecendo de uma casa por 4–5 segundos após uma unidade sair
- em campanhas, F12 (aliança dinâmica) não seleciona mais nenhum alvo; computadores de script de gatilho não são jogadores oponentes reais
- computadores de gatilho promovidos por ``(ai easy)`` e gatilhos similares são anunciados como "NPC" em vez do nome interno ``ai_timers``; sua derrota não é mais anunciada em campanhas
- Ctrl+Shift+F4 agora anuncia computadores de gatilho como "NPC"


1.4.2.9
-------

- mapas baixados de um servidor mantêm seu nome original
- mapas com o mesmo conteúdo de um mapa local não são baixados novamente
- replays multijogador são armazenados como ``replay1``, ``replay2``, ``replay3``, etc.


1.4.2.8
-------

- pequeno ganho de desempenho por otimizações Cython
- computadores neutros: adicione a palavra-chave ``neutral`` a uma linha ``computer_only``; IAs neutras não atacam a menos que sejam atacadas primeiro
- ``player_start \<N\> \<square\>`` fixa a casa de spawn do jogador N (ver o guia de criação de mapas)


1.4.2.7
-------

- saves e replays podem ser renomeados (qualquer idioma/caracteres): edite arquivos em ``user/saves`` ou ``user/replays``, ou pressione Shift+Enter num arquivo no menu de restaurar/replay
- Delete pede confirmação; Shift+Delete exclui imediatamente


1.4.2.6
-------

- até 10 slots de save por mod; cada mod tem seus próprios saves, pontos de memória e replays
- cancelar uma partida cria um ponto de memória; "continue unfinished game" aparece no menu principal
- arquivos de replay também são específicos por mod


1.4.2.5
-------

- ``can_advance`` para upgrades de fase (distinto de ``can_research``); mostrado na interface de propriedades
- a fase inicial padrão é exibida no início da partida quando uma construção tem ``can_advance``
- ``hide_locked_commands`` em ``def parameters`` oculta comandos cujos requisitos não foram atendidos


1.4.2.4
-------

- novo ``class phase`` (progressão estilo idades): ``phase_targets``, ``phase bonus``, ``units_auto_upgrade``
- aliança dinâmica: cada pedido de aliança agora tem seu próprio tempo de recarga


1.4.2.3
-------

- aliança dinâmica durante uma partida (F12 / Shift+F12 seleciona alvo; F4 pede; Ctrl+F4 aceita; Shift+F4 cancela/rejeita/sai); alianças pré-partida não podem ser alteradas em partida
- correções de bugs em campanha cooperativa


1.4.2.2
-------

- modo trégua: paz por uma duração escolhida (até 20 minutos), depois guerra
- campanha cooperativa em servidores: qualquer jogador que complete objetivos contribui para a equipe


1.4.2.1
-------

Bugs corrigidos:

- sons de passagem não atrasam mais os anúncios de nome de local e coordenadas
- unidades não ganham mais bônus de velocidade a cada revivescimento
- mudanças de upgrade em cost, time_cost e population_cost agora persistem após a pesquisa
- upgrades de heal e harm não se aplicam mais a todos os tipos de unidade
- altitude de unidade aérea restaurada ao comportamento de 1.3.8.1


1.4.2.0
-------

Bugs corrigidos:

- unidades revividas podem receber ordens novamente
- auto-ataques não disparam mais dano de carga
- upgrades de desconto não afetam mais unidades sem a tecnologia de desconto
- splash de carga no solo não atinge mais unidades aéreas
- transportes com capacidade ≥ 99 não carregam mais a si mesmos


1.4.1.9
-------

- hierarquia ``square_name`` de até 3 níveis (província / cidade / distrito); TTS anuncia nomes ao entrar a partir de outra região
- mais otimizações de desempenho


1.4.1.8
-------

- coordenadas de mapa usam ``x,y`` (ex. ``1,1``) em vez de letra+número; notação legada ainda aceita
- ``square_name`` para nomear casas; traduções em ``tts.txt``
- unidades e recursos iniciais de facção podem ser definidos em ``rules.txt`` (definições de mapa têm prioridade)


1.4.1.7
-------

- sistema de habilidades unificado (``class skill``) com ``effect_target`` e ``effect_range``
- buffs multi-atributo, buffs de aura (``buff_radius``), parâmetros expandidos de harm/heal/regen


1.4.1.6
-------

- debuffs podem ser definidos em armas
- corrigida falha no carregamento de save


1.4.1.5
-------

- palavra-chave ``intro`` em ``style.txt`` para descrições de unidades
- percepção diagonal restaurada
- corrigida a UI de produção em construções não produtoras


1.4.1.4
-------

- gatilhos de 1.3.5.2 migrados; mapas td1–td3 jogáveis


1.4.1.3
-------

- sistema de armas e armaduras; troca manual de arma (A / Shift+A / B+X); ``auto_weapon_switch``
- sistema de itens migrado de 1.3.5.2
- paredes e portões construíveis novamente


1.4.1.2
-------

- ``can_repair`` em trabalhadores; pathfinding de unidades aquáticas e mineração costeira aprimorados
- mais atributos na interface de propriedades


1.4.1.1
-------

- interface de propriedades aprimorada com navegação interativa (can_train, skills, research, can_build)
- ``can_repair_ships`` para trabalhadores e construções; reparo de navios na costa (distância 6) e auto-reparo de construções (distância 8)


1.4.1
-----

- vista RPG em primeira pessoa é 360°; precisão de movimento aprimorada


1.4.0.9
-------

- guia do modo RPG em primeira pessoa; F8 zoom dinâmico 3×3 a 15×15; navegação ciente do caminho


1.4.0.8
-------

- ``minimal_mdg`` / ``minimal_rdg`` renomeados de volta para ``minimal_damage``
- atalhos de habilidade RPG (1–0) no modo primeira pessoa


1.4.0.7
-------

- taxas de acerto crítico corrigidas; Crazy-Mod jogável


1.4.0.6
-------

- modo espectador em servidores; sons de vitória/derrota em multijogador corrigidos


1.4.0.5
-------

- palavras-chave ``food`` substituídas por ``population`` (ex. ``population_cost``)
- economia mais rica: construções de recursos, cultivo e produção automáticos/manuais
- ``rpg_bindings.txt`` reservado para futura personalização de atalhos RPG


1.4.0.4
-------

- ``auto_production`` / ``manual_production``; ``is_gather`` / ``is_create``; ``class resource`` separado de ``class deposit``


1.4.0.3
-------

- música de fundo e de batalha por facção (``\<faction\>\_music``, ``\<faction\>\_battle_music``)


1.4.0.2
-------

- sons de seleção/confirmação/retorno de menu; música de fundo e de batalha por menu


1.4.0.1
-------

- mecânicas de carga e contra-carga; taxas de gatilho de buff expandidas
- novas condições de derrota: ``unit_lost``, ``key_unit_killed``, ``key_units_killed``, ``units_lost``, ``buildings_lost``, ``has_killed``; ``killed_target`` e ``has_killed`` suportam ``enemy`` / ``ally``


1.4
----

- retrabalho de combate: ``mdg`` + ``mdg_vs`` (aditivo), crítico, perfuração, explosão
- sistema de herói e XP de 1.3.5.2 integrado
- ``title`` / parâmetros de campanha / mapa aceitam strings entre aspas; formato de tradução ``tts.txt``
- mapas avançados descompactados em ``multi/`` suportados
- corrigidos sons tocando ao digitar nomes correspondentes em caixas de entrada


1.3.9.8
-------

- sistema de buff/debuff de 1.3.5.2 integrado
- inimigos aparecem imediatamente ao entrar na casa deles


1.3.9.7
-------

- ``can_train`` com quantidades; ``can_change_to``; correção de menu ``can_use_tech`` / ``can_use_skill``


1.3.9.6
-------

- custo/tempo_cost/population_cost percentuais em upgrades; exibição decimal de recursos


1.3.9.5
-------

- filtros de objeto (teclas M / N); seleção de idioma em ``cfg/language.txt``


1.3.9.3
-------

- correções de cobertura/esquiva de terreno; pesquisa aplica-se a unidades futuras; sons de splash hit temporariamente removidos


1.3.9.2
-------

- efeitos de upgrade em custo/tempo/população; sons de splash hit; atributos float na UI de propriedades


1.3.9.1
-------

- propriedades splash ``\_vs``; som ``falling`` atrasado; regra de ataque por altura de projétil


1.3.9.0
-------

- ``extraction_time`` / ``extraction_qty`` restaurados; interface de propriedades Alt+V com ``attributes_bindings.txt``


1.3.8.8
-------

- ``can_gather`` / ``gather_time`` / ``gather_qty`` em trabalhadores; ``is_rewards`` / ``rewards_resource``


1.3.8.7
-------

- recompensas de recursos por matar/destruir; reembolso ao demolir


1.3.8.5
-------

- mapas específicos por mod via ``mods/\<mod\>/multi/``


1.3.8.4
-------

- produção de recursos por construção (``is_production``, ``production_type``, etc.)


1.3.8.3
-------

- herança ``is_a`` flexível (seletiva, com exclusão, multiparent)


1.3.8.2
-------

- captura de posse; ``mdg_projectile`` / cobertura e esquiva de terreno; saída de contêineres aprimorada
- grande retrabalho de combate: sistema ``mdg``/``rdg``/``mdf``/``rdf``; sequências de dano; ``class skill``; modos guarda/perseguição; refatoração do sistema de som


1.3.8.1
-------

Para partidas multijogador, esta versão exige:

- cliente: 1.3.8 ou posterior
- servidor: 1.2-c12 ou posterior

Principais mudanças em relação à 1.3.8:

Bugs corrigidos:

- num jogo restaurado, a tecla R selecionaria qualquer soldado (obrigado a Marco Oros por relatar o bug)
- quando construir um menu leva muito tempo, teclas repetidas se acumulavam
- evita-se, espera-se, qualquer glitch de volume quando uma fonte de som é criada
- mapas personalizados aparecerão após mapas oficiais
- rodar server.py não exige nenhum pacote


1.3.8
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.8 ou posterior
- servidor: 1.2-c12 ou posterior

Principais mudanças em relação à 1.3.7:

- adicionado tts_digit_coefficient em cfg/parameters.toml

Bugs corrigidos:

- caminhos entre solo e água serão mantidos se ambas as casas forem solo
- unidades fugirão para a casa anterior com mais frequência
- manipula adequadamente arquivos de replay que não são timestamps (obrigado a dnl-nash)
- envia relatórios de bug apenas se o cliente for um executável

Traduções:

- adicionada tradução para bielorrusso (obrigado a Uladzimir)
- atualizada tradução para eslovaco (obrigado a Marco Oros)


1.3.7
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.7 ou posterior
- servidor: 1.2-c12 ou posterior

Mudanças em relação à 1.3.6:

Agora unidades podem atacar de dentro de veículos ou construções:

- unidades de longo alcance podem atacar como de costume
- unidades corpo a corpo só podem atacar do solo e sem alcance adicional
- unidades corpo a corpo não podem atacar de veículos aéreos
- no jogo padrão: unidades podem entrar em paredes, portões e torres

Corrigidos problemas com contra-ataques para uma casa próxima:

- unidades que não podem contra-atacar ficarão em silêncio
- unidades defensivas não contra-atacarão

Outros:

- restaurada a notificação "attack!"
- correção: uma unidade não entraria numa construção se a ordem fosse dada de outra casa
- corrigido: restaurar jogo
- ataques entre casas podem funcionar melhor

Modding:

- adicionado armor_vs
- agora "damage_vs" funciona com "is_a" (incluindo vários níveis de "herança" e "herança" múltipla)

Criação de mapas:

- mapas "multi" oficiais movidos para res/multi
- "mapas de pasta" multijogador devem ser compactados em zip para serem jogados online
- removido o arquivo "maperror.txt" (a informação já está na mensagem de erro no jogo)

Mudanças no formato de campanha:

- mods.txt substituído pela palavra-chave "mods" em campaign.txt
- palavra-chave "title" em campaign.txt
- nova restrição: um mapa de missão complexo deve ser armazenado como arquivo zip


1.3.6
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.6 ou posterior
- servidor: 1.2-c12 ou posterior

Mudanças em relação à 1.3.5:

Comportamento de unidades:

- bug corrigido: unidades ofensivas próximas voltarão a contra-atacar automaticamente (moverão para a casa do atacante e depois voltarão às posições iniciais)
- bug corrigido: unidades defensivas voltarão a fugir

Interface:

- a descrição de unidades controladas será menos confusa
- seguimento de grupo aprimorado (tecla espaço): a interface geralmente seguirá a frente do grupo
- bug corrigido: em style.txt, noise_if_very_damaged nunca tocaria
- bug corrigido: SAPI não funcionava

Água:

- a partir de agora, o jogo não criará caminhos anfíbios (resolve o problema: se o caminho mais curto até o destino incluía uma casa de água, unidades terrestres caminhavam para a água e morriam)
- problema corrigido: um mago podia invocar unidades aquáticas para casas não aquáticas (Agora um mago invocará unidades aquáticas para a casa de água adjacente mais próxima.)

Multijogador:

- iniciar um servidor não privado autoconfigurará o roteador (funciona apenas se UPnP estiver ativado no roteador; a configuração é removida automaticamente pelo roteador após 20 minutos de inatividade)
- configuração mais fácil do servidor autônomo
- descoberta automática de servidor local por broadcast UDP (O servidor local aparecerá no menu "choose a server in a list".)
- bug corrigido: em partidas multijogador, um jogador não administrador podia definir uma velocidade mais lenta

Traduções:

- atualizadas traduções para português brasileiro, chinês, tcheco, italiano e eslovaco

Criação de mapas:

- quando possível, emite um aviso em vez de um erro de mapa
- bug corrigido: em alguns casos, um gatilho selecionava mais unidades do que o especificado. Por exemplo, se há 3 dragões e muitos soldados de infantaria em a1, (a1 10 dragon footman) selecionaria 3 dragões e 7 soldados de infantaria.


1.3.5
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.5 ou posterior
- servidor: 1.2-c12 ou posterior

Mudanças em relação à 1.3.4:

- bug corrigido: não era possível salvar um jogo com terreno
- corrigido: o som de acerto não era emitido se matasse o alvo
- corrigido: o jogo congelaria se não houvesse espaço suficiente numa casa para criar uma unidade

Internacionalização:

- convertidos todos os arquivos tts.txt para UTF-8 com assinatura BOM. A codificação ainda é definida explicitamente na primeira linha como UTF-8. A assinatura BOM pode ajudar alguns editores de texto a selecionar UTF-8 automaticamente.
- sempre usará UTF-8 (ou ASCII) para arquivos de texto que não sejam tts.txt (rules.txt, style.txt, etc)
- atualizada tradução para espanhol (obrigado a Oscar Corona)


1.3.4
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.4 ou posterior
- servidor: 1.2-c12 ou posterior

Mudanças em relação à 1.3.3:

- provavelmente corrigida a fala em mais alguns casos (por favor, relate se ainda não conseguir iniciar o cliente)
- restaurados salvar e restaurar (parece estar funcionando, mas tenha cuidado)
- restaurados recursos e tecnologia infinitos para "aggressive computer 2" (mais interessante)

Multijogador:

- o cliente lembrará da lista de servidores baixada anteriormente e a usará se o metaservidor estiver temporariamente indisponível
- em "enter the IP address of the server", digitar um endereço IP vazio selecionará seu computador (sem precisar digitar: "localhost")
- servidor autônomo: removida dependência do pygame

Interface:

- comando de console: "a u_recall" adicionará o upgrade de recall ao jogador atual
- bug menor corrigido: a interface não seguiria uma unidade dentro de um transporte (se a unidade estivesse em modo de seguir antes de ser transportada)

Internacionalização:

- atualizada tradução para italiano (obrigado a Luigi Russo)

Campanha principal:

- adicionado capítulo 12, um mapa pequeno para mostrar como florestas densas funcionam (a regra é: "qualquer caminho entre duas florestas densas está bloqueado")

Dica: para verificar rapidamente melhorias num capítulo específico de uma campanha que você já jogou:

- pressione a tecla "console" abaixo de Escape e pressione "v" e Enter para uma vitória instantânea
- ou edite user/campaigns.ini: em [single_campaign] "chapter = 12" por exemplo


1.3.3
-----

Para partidas multijogador, esta versão exige:

- cliente: 1.3.3 ou posterior (se compatível)
- servidor: 1.2-c12, 1.3.0, 1.3.1, 1.3.2, 1.3.3 ou posterior (se compatível)

Mudanças em relação à 1.3.2:

- bug corrigido: uma unidade não pararia após usar uma habilidade que exige se aproximar (deadly fog, exorcism...) e se moveria em direção ao inimigo...
- bug corrigido: o jogo exigiria um alvo para uma habilidade centrada no conjurador (por exemplo: raise dead)
- bug corrigido: água não podia ser vista de terreno baixo (por exemplo no mapa jl7)

A interface de mapa deve parecer mais natural:

- mover no mapa não causará colisões se você controlar uma unidade voadora
- mover no mapa não causará colisões se você estiver definindo o alvo de uma ordem de recall (por exemplo)
- removidas colisões entre água e terreno baixo

Florestas densas:

- bug corrigido: florestas densas criariam caminhos quando desmatadas (mesmo se não houvesse nenhum caminho antes)
- agora florestas são densas se tiverem pelo menos 7 madeiras (em vez de 3)
- mapa multijogador 8: atualizado (7 madeiras) e melhorado (economia mais rápida)
- editor: paleta de terreno atualizada (floresta densa se pelo menos 7 madeiras)

Internacionalização:

- bug corrigido: mapas com caracteres não US-ASCII não podiam ser lidos em plataformas que usam GBK ou UTF-8 por padrão (agora mapas são sempre lidos como UTF-8 e erros são substituídos por "?")
- convertidos os seguintes mapas para UTF-8: bs2, can1, qc1, qc2 e qc3
- atualizada tradução para polonês (obrigado a Patryk Mojsiewicz)

Pequenas mudanças na campanha principal:

- capítulo 9: com o bug "deadly fog" corrigido, necromantes devem ser mais fáceis de gerenciar
- capítulos 5 e 10 levemente melhorados

Dica: para verificar rapidamente melhorias num capítulo específico de uma campanha que você já jogou:

- pressione a tecla "console" abaixo de Escape e pressione "v" e Enter para uma vitória instantânea
- ou edite user/campaigns.ini: em [single_campaign] "chapter = 11" por exemplo


1.3.2
-----

Mudanças em relação à 1.3.1:

Mudanças principais:

- o menu "choose a server" incluirá qualquer servidor com uma versão de servidor compatível (não apenas a mesma versão) para que os servidores não precisem ser atualizados com tanta frequência
- clientes compatíveis com versões diferentes poderão jogar juntos
- os servidores "mais próximos" aparecerão primeiro no menu "choose a server" (servidores com o menor atraso de resposta)
- o tempo gasto para verificar se um servidor está disponível será mencionado (expresso em milissegundos) no menu "choose a server" para comparação
- os servidores indisponíveis não aparecerão no menu "choose a server"

Mudanças menores:

- levemente reduzida a verbosidade de server.log
- melhorado o guia do servidor autônomo (ainda não está perfeito, porém)
- adicionadas "notas de lançamento" à documentação

1.3.1
-----

Mudanças em relação à 1.3.0:

- provavelmente corrigido: o jogo não iniciava no Windows 7 (ImportError: DLL load failed while importing _socket)
- corrigido: às vezes o jogo não iniciava até que a pasta "gen_py" em "appdata\local\Temp" fosse excluída (AttributeError: module 'win32com.gen_py...' has no attribute 'CLSIDToClassMap')
- corrigido: vcruntime140.dll podia estar faltando
- corrigido: não era possível obter a lista de servidores
- corrigido: pressionar A se comportará como antes e pressionar Control+A selecionará apenas ordens inativas

1.3.0
-----

Mudanças em relação à 1.2-c12:

Mudanças principais:

- apenas paredes e portões podem ser construídos em saídas (ou qualquer construção "buildable on exits only")
- agora uma torre pode ser construída apenas no centro de uma subcasa, e apenas uma torre por subcasa. A localização de uma torre pode ser selecionada de várias maneiras:

  - no modo zoom: seleciona a subcasa atual (deve estar livre)
  - no modo casa: seleciona qualquer subcasa livre, começando pela central
  - se algum objeto estiver selecionado: seleciona a subcasa envolvente (deve estar livre)

- agora o leitor de tela é o TTS padrão

Mudanças técnicas:

- migrado para Python 3
- substituídos todos os TTS por accessible_output2 (corrigido para suportar Linux)

Bugs corrigidos:

- não era possível controlar uma unidade ressuscitada que estava num grupo
- um trabalhador que adiasse construir ou coletar para eliminar um intruso não voltaria à sua tarefa e a concluiria no lugar
- uma unidade podia ver um planalto de baixo
- uma unidade não podia ver diagonalmente
- não era possível selecionar uma casa como alvo para construir um portão (uma saída livre será selecionada)

Melhorias de interface:

- modo zoom: validar uma ordem de construção de uma parede (ou portão) sem selecionar um alvo específico selecionará automaticamente a saída local (se não estiver bloqueada)
- tab selecionará qualquer inimigo primeiro
- pressionar escape quando um alvo está selecionado selecionará a casa atual
- bug corrigido: agora entrar ou sair do modo zoom selecionará a minicasa ou casa como alvo (em vez de manter o alvo selecionado)
- adicionadas vírgulas em algumas mensagens (para clareza)
- resumo de inimigo mais curto
- bug corrigido: diria "building site" e não o tipo de construção
- bug corrigido: no modo zoom, uma ordem padrão para uma construção não definia o ponto de reunião para a subcasa, mas sim para a casa
- bug corrigido: um jogo pausado não sairia
- bug corrigido: pressionar Space dirá as ordens exatas mesmo quando algumas unidades têm ordens diferentes (Isso é muito útil para checar quantos trabalhadores estão coletando ouro, madeira, etc (pressionando D). Isso pode ser útil para saber quantas unidades num grupo estão se movendo e quantas já chegaram. Pressionar Control + Shift + S dará um resumo completo das ordens de soldados e trabalhadores.)
- no modo construção, tab selecionará prados antes de saídas
- a descrição de uma ordem de patrulha recapitulará todos os pontos de passagem
- bug corrigido: pressionar Tab selecionaria saídas bloqueadas
- bug corrigido: não é mais possível construir outra parede na mesma saída
- modo zoom: se nenhum terreno de construção for encontrado enquanto uma ordem de construção foi validada numa subcasa, um erro será gerado (em vez de procurar um terreno de construção na casa envolvente
