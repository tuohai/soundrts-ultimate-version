Sistema de pontuação e notas
============================



Guia do jogador: `../player/score-and-grades.md <../player/score-and-grades.htm>`_

Este documento descreve a pontuação multidimensional pós-partida do SoundRTS,
notas por letra e anúncios por voz.

Versão em chinês: `../../zh/mod/score-grading-system.htm <../../zh/mod/score-grading-system.htm>`_

Para integração com conquistas, veja a seção 9 de `achievement-system <achievement-system.htm>`_. As conquistas leem ``score_breakdown()``; não reimplementam a pontuação.


----


1. Quando a pontuação é calculada
---------------------------------



.. list-table::
   :header-rows: 1

   * - Cenário
     - Anúncio de pontuação
     - Estatísticas no histórico
   * - Mapa personalizado / aleatório vs IA (TrainingGame)
     - ✅
     - ✅
   * - Multijogador
     - ✅
     - ✅
   * - Campanha / campanha cooperativa
     - ❌
     - ❌
   * - Espectador
     - ❌ (“spectating finished”)
     - ❌



Quando ``game.is_campaign_session()`` é verdadeiro, ``say_score()`` e ``\_record_stats()`` são ignorados.

Ordem ao fim da partida (``game.post_run()``): ``say_score()`` primeiro, depois ``\_say_achievements()``.


----


2. Estrutura da pontuação
-------------------------


.. code-block:: text

   total = base_total + ai_defeat



.. list-table::
   :header-rows: 1

   * - Campo
     - Significado
   * - ``base_total``
     - Soma das sete dimensões base, teto 800
   * - ``ai_defeat``
     - Bônus por computadores inimigos derrotados, não conta para 800
   * - ``total``
     - `base_total + ai_defeat`; pode exceder 800
   * - ``percent``
     - `base_total × 100 ÷ 800`, limitado a 100%
   * - ``max``
     - Sempre 800 (denominador do percentual; exclui ai_defeat)
   * - ``grade_total``
     - Pontuação usada para a nota por letra (teto na derrota; veja §5)



Sete dimensões base
~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Dimensão
     - Chave
     - Faixa
     - Observações
   * - Resultado
     - ``outcome``
     - 0 ou 200
     - Vitória 200, derrota 0
   * - Mineração
     - ``mining``
     - 0–100
     - vs capacidade de depósito do mapa ou referência
   * - Eficiência
     - ``efficiency``
     - 0–100
     - utilização ou frugal (veja §4)
   * - Sobrevivência
     - ``survival``
     - 0–100
     - taxa de perda de unidades aliadas
   * - Defesa de edifícios
     - ``building_defense``
     - 0–100
     - perdas de edifícios aliados
   * - Combate
     - ``combat``
     - 0–100
     - abates vs produção inimiga
   * - Demolição
     - ``demolition``
     - 0–100
     - edifícios inimigos destruídos



Linhas resumo (para anúncios)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Chave
     - Fórmula
   * - ``unit_line``
     - `survival + combat`
   * - ``building_line``
     - `building_defense + demolition`
   * - ``mining_by_resource[]``
     - pontuação de mineração por recurso




----


3. Fórmulas das dimensões
-------------------------


Todas as pontuações de dimensão usam ``\_clamp_score()`` para 0–100 (outcome é
0 ou 200). Valores internos usam inteiros de ponto fixo (``PRECISION``);
anúncios dividem por ``PRECISION`` para exibição.

3.1 Resultado
~~~~~~~~~~~~~


- Vitória: `200`
- Derrota: `0`

Peso dobrado em relação às outras dimensões individuais.

3.2 Mineração
~~~~~~~~~~~~~


Coleta efetiva = ``gathered[i] - starting_resources[i]`` (soma por recurso,
mínimo 0). Estoque inicial não conta.

Com capacidade do mapa (``sum(world.map_deposit_capacity) \> 0``):

.. code-block:: text

   mining = clamp(effective_gathered × 100 ÷ total_map_capacity)


A capacidade é acumulada de cada ``Deposit`` do mapa no carregamento
(``worldresource.py``).

Sem capacidade do mapa:

- Campanha: vitória → 100; derrota → 0
- Fora de campanha: se coleta efetiva ≤ 0 → 0; senão:

.. code-block:: text

     mining = clamp(effective_gathered × 100 ÷ 1000)

  (``MINING_REFERENCE_GATHER`` = 1000 em unidades de exibição)

Pontuações por recurso seguem as mesmas regras em ``mining_by_resource[i]``.

3.3 Eficiência
~~~~~~~~~~~~~~


.. code-block:: text

   utilization_percent = clamp(consumed ÷ gathered × 100)   // 0 se gathered for 0


- Padrão `efficiency_mode = "utilization"`: `efficiency = utilization_percent`
- Frugal `efficiency_mode = "frugal"` (apenas vitória, utilização < 50%):
  ``efficiency = clamp((1 - consumed/gathered) × 100)``  
  O anúncio usa “frugal efficiency” (TTS 5251) em vez de “resource utilization”
  (5227).

Na derrota, o modo frugal nunca se aplica.

3.4 Sobrevivência
~~~~~~~~~~~~~~~~~


.. code-block:: text

   if produced(unit) > 0:
       survival = clamp((produced - lost) × 100 ÷ produced)
   else:
       survival = 0


3.5 Defesa de edifícios
~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   building_defense = max(0, 100 - lost(building) × 5)


5 pontos perdidos por edifício aliado.

3.6 Combate
~~~~~~~~~~~


Soma ``produced(unit)`` sobre inimigos não aliados e não neutros como
``enemy_units``:

.. code-block:: text

   if enemy_units > 0:
       combat = clamp(killed(unit) × 100 ÷ enemy_units)
   else:
       combat = clamp(killed(unit) × 5)


3.7 Demolição
~~~~~~~~~~~~~


.. code-block:: text

   demolition = clamp(killed(building) × 5)


5 pontos por edifício inimigo (teto 100 com 20 edifícios).

3.8 Bônus por derrota de IA (``ai_defeat``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Para cada computador inimigo derrotado, adiciona ``defeat_score`` conforme a
dificuldade:


.. list-table::
   :header-rows: 1

   * - Nível integrado
     - defeat_score padrão
   * - beginner / easy
     - 10
   * - intermediate / aggressive
     - 20
   * - advanced
     - 40
   * - expert
     - 80
   * - nightmare
     - 200



De ``defeat_score \<n\>`` no bloco ``ai.txt`` da IA; nomes de IA personalizados
sem isso pontuam 0.

Excluídos: computadores aliados, não derrotados, tipos de IA ``timers`` /
``ai2`` / vazio, ``defeat_score 0``, jogadores não computador. Jogadores
derrotados em ``ex_players`` ainda contam.


----


4. Notas por letra
------------------


De ``grade_total`` (``score_grade_msg()`` / ``score_grade_letter()``):


.. list-table::
   :header-rows: 1

   * - Nota
     - grade_total mínimo
   * - S
     - 720
   * - A
     - 640
   * - B
     - 560
   * - C
     - 480
   * - D
     - 400
   * - E
     - 0



Teto de nota na derrota
~~~~~~~~~~~~~~~~~~~~~~~


Na derrota: ``grade_total = min(total, 479)`` (``DEFEAT_GRADE_MAX_TOTAL``). A
nota por letra não pode exceder D na derrota, mesmo que combate/demolição
inflacionem ``total``.


----


5. Eventos brutos de estatísticas
---------------------------------


``Stats.add(event, target, inc)`` durante a partida:


.. list-table::
   :header-rows: 1

   * - event
     - target
     - Gatilho típico
   * - ``gathered``
     - índice de recurso
     - mineração, recursos iniciais, concessões de cartas
   * - ``produced``
     - ``unit`` / ``building``
     - treinamento concluído
   * - ``lost``
     - ``unit`` / ``building``
     - aliado destruído
   * - ``killed``
     - ``unit`` / ``building``
     - inimigo destruído

O expirar de ``time_limit`` com ``on_disappear`` (incluindo invocações de ``lang_add_units``) não soma ``lost``; ``uncount_expired_unit_produced`` reverte ``produced``. Morte em combate continua a contar ``lost`` / ``killed``.



``consumed(i) = gathered(i) - player.resources[i]``.

``stats.freeze()`` ao fim da partida fixa ``game_duration`` para o anúncio de
tempo.


----


6. Anúncios por voz (``score_msgs``)
------------------------------------


Ordem:

1. Vitória/derrota + duração + pontos de resultado
2. Unidades: produzidas / perdidas / abates + ``unit_line``
3. Edifícios: produzidos / perdidos / abates + ``building_line``
4. Cada recurso: coletado / consumido + pontuação de mineração por recurso
5. Linha de eficiência (rótulo frugal ou utilização)
6. Cada nível de IA derrotada [× contagem] + bônus
7. Total / 800 / percent%
8. Nota por letra + explicação do histórico

IDs TTS: ``soundrts/msgparts.py`` (5225–5243, 5251) e ``res/ui/tts.txt``.


----


7. Integração com conquistas
----------------------------


``achievements.build_context()`` lê de ``score_breakdown()``:


.. list-table::
   :header-rows: 1

   * - Condição
     - Origem
   * - ``condition grade S`` etc.
     - `score_grade_letter(total)`
   * - ``condition victory``
     - `player.has_victory`
   * - ``condition utilization_below N``
     - ``utilization_percent`` (vitória necessária)
   * - ``condition survival_at_least N``
     - ``survival``
   * - ``condition building_defense_at_least N``
     - ``building_defense``
   * - ``condition defeated_ai expert`` etc.
     - ``ai_defeat_entries``




----


8. Personalização por mod
-------------------------


ai.txt — bônus por derrota
~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def my_custom_ai
   defeat_score 55


``defeat_score 0`` desativa o bônus para essa IA.


----


9. Arquivos relacionados
------------------------



.. list-table::
   :header-rows: 1

   * - Caminho
     - Função
   * - ``soundrts/worldplayerstats.py``
     - Pontuação, notas, mensagens
   * - ``soundrts/definitions.py``
     - ``DEFAULT_AI_DEFEAT_SCORE``, `get_ai_defeat_score()`
   * - ``soundrts/worldresource.py``
     - ``map_deposit_capacity``
   * - ``soundrts/game.py``
     - `say_score()`, `post_run()`
   * - ``soundrts/achievements.py``
     - Lê breakdown para desbloqueios




----


10. Testes
----------


.. code-block:: bash

   python -m pytest soundrts/tests/test_score_breakdown.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v



----


11. Constantes de design
------------------------



.. list-table::
   :header-rows: 1

   * - Constante
     - Valor
     - Função
   * - ``SCORE_BASE_MAX``
     - 800
     - Máximo base
   * - ``OUTCOME_MAX``
     - 200
     - Peso do resultado
   * - ``DEFEAT_GRADE_MAX_TOTAL``
     - 479
     - Teto de nota na derrota (D)
   * - ``MINING_REFERENCE_GATHER``
     - 1000
     - Referência quando não há depósitos



Não pontuados hoje: duração da partida, progresso tecnológico.
``game_duration`` é apenas para anúncio.

O percentual reflete apenas as sete dimensões base, não o bônus por derrota de
IA.
