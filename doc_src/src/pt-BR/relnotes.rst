
Notas de lançamento
==================

.. contents::


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
