Sistema de conquistas
=====================



Guia do jogador (menus, progresso, o que conta): `../player/achievements.htm <../player/achievements.htm>`_

Referência de implementação. Versão em chinês: `../../zh/mod/achievement-system <../../zh/mod/achievement-system.htm>`_.

Status
------



.. list-table::
   :header-rows: 1

   * - Fase
     - Status
     - Resumo
   * - 1
     - Concluída
     - Definições, save por mod, desbloqueio pós-partida, lista de conquistas
   * - 2
     - Concluída
     - Medalhas, cartas, patentes e títulos de honra, arsenal
   * - 3
     - Concluída
     - Loadout pré-missão em TrainingGame, aplicar efeitos, consumir cargas
   * - Esquema D
     - Concluída
     - Saves por facção (``achievements_per_faction``), seletor de facção nos
       menus
   * - Progresso meta
     - Concluída
     - ``\_meta.json`` entre facções, condições agregadas, ``scope meta``



Código principal
----------------



.. list-table::
   :header-rows: 1

   * - Arquivo
     - Função
   * - ``soundrts/achievements.py``
     - Carregar, avaliar, recompensas, persistir, anunciar
   * - ``soundrts/faction_progress.py``
     - Caminhos por facção, correspondência de facção, seletor no menu
   * - ``soundrts/meta_progress.py``
     - Save meta entre facções (``\_meta.json``), agregação de snapshot
   * - ``soundrts/cards.py``
     - Definições de cartas
   * - ``soundrts/titles.py``
     - Escada de patentes + títulos de honra
   * - ``soundrts/achievements_menu.py``
     - Hub: seletor de facção, lista de conquistas, arsenal, progresso meta
   * - ``soundrts/game.py``
     - `_say_achievements()` após `say_score()` (ignorado em campanha)
   * - ``soundrts/lib/resource.py``
     - Carrega conquistas + cartas + títulos com rules
   * - ``res/achievements.txt``
     - Conquistas base
   * - ``mods/\<mod\>/achievements.txt``
     - Anexar / substituir do mod



Caminhos de save
----------------



.. list-table::
   :header-rows: 1

   * - Caminho
     - Quando
   * - ``user/achievements/\<mod_key\>.json``
     - Padrão (save único por mod)
   * - ``user/achievements/\<mod_key\>/\<faction\>.json``
     - ``achievements_per_faction 1``
   * - ``user/achievements/\<mod_key\>/\_meta.json``
     - Meta entre facções (``achievements_per_faction 1``)



Ative o modo por facção no ``rules.txt`` do mod:

.. code-block:: text

   def parameters
   achievements_enabled 1
   achievements_per_faction 1


- Defs com tag de facção usam `faction <race_id>`; omita ``faction`` em cartas
  globais (compartilhadas entre ramos).
- Conquistas no menu principal escolhem facção primeiro (mods multi-facção);
  voltar da lista/arsenal retorna ao seletor de facção.
- Entrada de progresso entre facções abre lista meta de conquistas + arsenal
  meta (ramos ativos, marcos de mapa, honras meta).

Campanha: ``game.is_campaign_session()`` ignora pontuação, conquistas,
medalhas, promoção de patente e gravação de estatísticas.

Multijogador: ``game_type_name == "multiplayer"`` ignora conquistas, medalhas,
promoção de patente e progresso de cartas; voz de pontuação e estatísticas de
tempo de jogo ainda rodam (veja `score-grading-system.htm
<score-grading-system.htm>`_).

Trecho de definição
-------------------


.. code-block:: text

   def grade_s
   title 5300
   condition grade S
   once_per map_ai
   reward medal 50
   reward card card_mixed_army


Conquista meta (``scope meta``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def meta_three_branches
   scope meta
   title 79950
   condition factions_unlocked_at_least 3 1
   once
   reward title honor_meta_novice


Condições agregadas (lê todos os saves de facção):


.. list-table::
   :header-rows: 1

   * - Condição
     - Significado
   * - ``factions_unlocked_at_least N M``
     - Pelo menos N ramos com ≥M conquistas desbloqueadas cada
   * - ``factions_medals_at_least N M``
     - Pelo menos N ramos com ≥M medalhas
   * - ``factions_honors_at_least N M``
     - Pelo menos N ramos com ≥M títulos de honra cada
   * - ``factions_achievement_id_contains_at_least N \<substr\>``
     - Pelo menos N ramos desbloquearam conquista cujo id contém `<substr>`
       (por exemplo ``\_map_``)



Recompensas meta ficam em ``\_meta.json``. Medalhas meta não contam para
patentes por facção. Títulos de honra meta não têm campo ``faction``.

Veja o doc em zh para a lista completa de diretivas (``condition``, ``reward``,
``repeat_medal``, ``cards.txt``, ``titles.txt``).

Repetição de conclusão: se a mesma chave ``once`` já foi concedida,
``repeat_medal \<n\>`` concede apenas medalhas (sem carta/honra/voz de
desbloqueio).

Normalização de dificuldade de IA: nomes de script de IA personalizados por
facção mapeiam para níveis canônicos para contadores cumulativos de derrota;
chaves legadas de save migram no carregamento.

Fluxo em tempo de execução
--------------------------


.. code-block:: text

   Main menu → Achievements
     ├─ (multi-faction) pick faction → list / armory → back → pick faction again
     └─ (multi-faction) cross-faction progress → meta list / meta armory
   
   game.post_run()
     → say_score()              # skipped in campaign
     → _say_achievements()      # faction unlocks, then meta unlocks, rewards, rank-up
                                # skipped in campaign and multiplayer


Formato de save (facção ou mod único)
-------------------------------------


.. code-block:: json

   {
     "unlocked": { "grade_s": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "grade_s|map:jl1|ai:beginner": true },
     "medals": 50,
     "honors": ["honor_nightmare_slayer"],
     "ai_defeats": { "beginner": 5 },
     "map_ai_defeats": { "pra1": { "beginner": 3 } },
     "cards": { "card_infantry": { "charges": 1, "total_earned": 1 } }
   }


Save meta (``\_meta.json``) — sem ``cards`` / ``ai_defeats`` /
``map_ai_defeats``:

.. code-block:: json

   {
     "unlocked": { "meta_three_branches": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "meta_three_branches": true },
     "medals": 25,
     "honors": ["honor_meta_novice"]
   }


Saves legados sem campos são normalizados no carregamento.

Fase 3 (concluída)
------------------


- Após Um jogador → Iniciar no mapa → Iniciar, escolha até N cartas (N =
  ``loadout_slots`` da patente)
- Efeitos aplicam após popular o mapa (imediato ou após ``delay`` /
  ``delay_minutes``); uma carga consumida por carta no início da partida
- Campos de carta: ``spawn``, ``resource``, ``tech``; cartas combo suportadas;
  cartas com atraso documentadas em `delayed-card-loadout.htm
  <delayed-card-loadout.htm>`_
- Spawns de carta consomem população
- Apenas TrainingGame (escaramuça vs IA); não campanha nem multijogador
- Cartas podem exigir ``min_rank`` em ``cards.txt``

Opt-out por mod
---------------


.. code-block:: text

   def parameters
   achievements_enabled 0


Oculta a entrada Conquistas no menu principal, ignora desbloqueios pós-partida,
loadout e aplicação de cartas no jogo; não carrega ``achievements.txt`` /
``cards.txt`` / ``titles.txt``. Arquivos de save são mantidos se você
reativar depois.

Exemplo CrazyMod
----------------


``mods/crazyMod9beta10`` usa esquema D + quatro níveis meta
(``meta_three_branches`` … ``meta_ten_masters``) e marcos de mapa por facção
(``trad_map_pra1`` … ``delf_map_pra10``).

Testes
------


.. code-block:: bash

   python -m pytest soundrts/tests/test_achievements.py -v
   python -m pytest soundrts/tests/test_faction_progress.py -v
   python -m pytest soundrts/tests/test_meta_progress.py -v
   python -m pytest soundrts/tests/test_achievements_menu_navigation.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
   python -m pytest soundrts/tests/test_card_loadout.py -v
