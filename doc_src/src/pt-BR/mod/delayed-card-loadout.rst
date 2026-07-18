Cartas de loadout atrasadas
===========================



Guia do jogador: `cartas de loadout <../player/loadout-cards.htm>`_

Cartas pré-missão podem fazer efeito após :strong:```delay`` / ``delay_minutes`` em vez de no início da partida.

Ver também: `sistema de conquistas <achievement-system.htm>`_, `sistema de notas <score-grading-system.htm>`_.


----


1. Escopo
---------


- Apenas TrainingGame (mapa personalizado / aleatório vs IA), igual às cartas instantâneas; não campanha nem multijogador.
- Seleção da carta e dedução da carga acontecem no início da partida; os efeitos disparam após o tempo de jogo decorrer.
- Cartas atrasadas usam slots de loadout e custam uma carga como as instantâneas; ``min_rank`` / ``faction`` inalterados.


----


2. Sintaxe de cards.txt
-----------------------



.. list-table::
   :header-rows: 1

   * - Diretiva
     - Significado
   * - ``delay \<seconds\>``
     - Esperar segundos de tempo de jogo
   * - ``delay_minutes \<n\>``
     - Igual a `delay (n×60)`
   * - ``tech \<upgrade_id\> [...]``
     - Conceder upgrade(s) quando o atraso expirar



Combine com ``spawn`` e ``resource`` na mesma carta; um atraso compartilhado, todos os efeitos aplicados juntos.

.. code-block:: text

   def card_reinforcements_delayed
   title 5333
   spawn footman 3
   delay_minutes 10
   grant_charges 1
   
   def card_delayed_melee_weapon
   title 5334
   tech melee_weapon
   delay_minutes 8
   grant_charges 1


- Omita ``delay`` ou use `0` para efeito imediato (comportamento legado).


----


3. Tempo de execução
--------------------


No momento de aplicar o loadout, ``delay \> 0`` registra ``world.schedule_after(delay_ms, callback)``.  
``delay_ms = delay_seconds × 1000 × world.timer_coefficient``.

Quando o timer dispara: aplica recursos → spawns perto do início (consomem população) → techs; o humano local recebe a voz LOADOUT_CARD_TRIGGERED.

A carga é consumida quando a carta é agendada com sucesso no início da partida, não quando os efeitos disparam.


----


4. Voz (TTS)
------------



.. list-table::
   :header-rows: 1

   * - ID
     - Inglês
     - Uso
   * - 5387
     - (effects in)
     - Aplicado / arsenal
   * - 5392
     - (after delay)
     - sufixo
   * - 5388
     - loadout card effect triggered
     - Ao disparar
   * - 5389–5393
     - dicas de spawn / resource / tech
     - Arsenal



Minutos inteiros anunciados como “N minutos”; caso contrário, segundos.


----


5. Exemplos vanilla
-------------------



.. list-table::
   :header-rows: 1

   * - Carta
     - Efeito
     - Conquista
   * - ``card_reinforcements_delayed``
     - 3 footman após 10 min
     - ``reinforcement_contract``
   * - ``card_delayed_melee_weapon``
     - ``melee_weapon`` após 8 min
     - ``defeat_expert``




----


6. Testes
---------


.. code-block:: bash

   python -m pytest soundrts/tests/test_cards.py -k delay -v
   python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
