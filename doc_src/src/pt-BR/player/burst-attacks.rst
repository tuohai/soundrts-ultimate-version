Ataques em rajada (``damage_seq``) e besta de repetição
=======================================================


Desde o SoundRTS 1.3.8.2 (aprimorado em 1.4.3.6), unidades podem fazer ataques em rajada / sequência: um ciclo de ataque dispara vários acertos em rápida sucessão, semelhante ao Chu Ko Nu (besta de repetição) em *Age of Empires*. Cada tiro rola acerto, crítico e debuff separadamente.

Referência oficial: ``mod/modding.rst`` (Combat system → ``damage_seq``).

.. note::

   **Não é o mesmo que skill ``effect burst``:** Esta página cobre **ataques normais de unidade** via ``damage_seq`` (ex.: besta de repetição). Combos de habilidade usam ``effect burst mdg|rdg …`` em ``class skill``, lançados manualmente ou por auto-gatilho, com sintaxe e colocação diferentes. Veja o guia de habilidades (`../mod/skills-and-effects.htm`_).


----


1. Visão geral
--------------



.. list-table::
   :header-rows: 1

   * - Aspecto
     - Comportamento
   * - Dano total por ciclo
     - Divisão igual/manual: continua igual a ``mdg`` / ``rdg``; modo ``secondary``: primeiro ao vivo + flechas fixas seguintes (pode superar a base)
   * - Tiros por ciclo
     - Até 6 (`damage_seq … <times>`)
   * - Rolagens de acerto
     - Independentes por tiro; flechas secundárias acertam 100%
   * - Cooldown
     - ``mdg_cd`` / ``rdg_cd`` começa após o fim da rajada completa
   * - Sons de lançamento
     - Um ``launch_mdg`` / ``launch_rdg`` por tiro




----


2. Configuração em rules.txt
----------------------------


2.1 Sintaxe
~~~~~~~~~~~


.. code-block:: text

   damage_seq mdg|rdg <times> [(damage d1 d2 ...)] [(secondary pierce melee)] [(interval seconds)]


Defina o ``mdg`` ou ``rdg`` base antes de ``damage_seq``.

2.2 Divisão automática (desde 1.4.3.6)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Omita ``(damage …)`` para dividir o dano base igualmente:

.. code-block:: text

   rdg 6
   damage_seq rdg 3 (interval 0.25)


→ três tiros de 2 de dano cada. Funciona com dano base fracionário (ex.: ``rdg 7.5`` com 3 tiros → 2.5 cada).

2.3 Divisão manual
~~~~~~~~~~~~~~~~~~


Valores inteiros dos segmentos devem somar o dano base (mesmas unidades das rules):

.. code-block:: text

   mdg 12
   damage_seq mdg 3 (damage 6 3 3) (interval 0.2)


``(damage …)`` manual usa apenas valores inteiros; dano base fracionário (ex.: ``rdg 2.5``) não pode ser expresso assim — use divisão automática.


2.3b Flechas secundárias AoE2 (``secondary``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Alinhado ao Chu Ko Nu de Age of Empires II DE: primeiro tiro = ataque ao vivo da unidade (upgrades aplicam) + melee fixo; tiros seguintes = pierce + melee fixos (**não** aprimorados por ferreiro/química). O melee pode ser ``0`` (ainda causa dano a armadura melee negativa como aríetes).

.. code-block:: text

   rdg 8
   rdg_cd 2.77
   rdg_ready 0.23
   damage_seq rdg 3 (secondary 3 0) (interval 0.23)

O Chu Ko Nu de elite usa ``rdg 5 (secondary 3 0)`` (5 flechas). Este modo **não** exige que a soma iguale ``rdg``.

2.4 Intervalo
~~~~~~~~~~~~~


- `(interval 0.25)` — segundos entre tiros
- Se `times > 1` e o intervalo for omitido ou `0`, padrão 0.25 s

2.5 Dicas de rajada à distância
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Defina ``rdg_projectile 1`` para comportamento de projétil (regras de terreno alto etc.)
- Use um ``rdg_cd`` mais longo que um arqueiro de tiro único: o DPS da rajada é maior, mas cada ciclo ainda respeita o ``rdg`` total

Exemplo (unidade embutida):

.. code-block:: text

   def repeating_crossbowman
   class soldier
   rdg 6
   rdg_cd 2.5
   rdg_range 4
   rdg_projectile 1
   damage_seq rdg 3 (interval 0.25)



----


3. Sons (``style.txt``)
-----------------------


Cada tiro dispara ``launch_rdg`` ou ``launch_mdg``. Liste vários IDs de som para variar os tiros:

.. code-block:: text

   def repeating_crossbowman
   is_a archer
   launch_rdg 1042 1042 1042


Sons de acerto / erro (``rdg_hit``, ``rdg_missed``, …) ainda tocam por rolagem de acerto bem-sucedida, como de costume.


----


4. Exemplo embutido: ``repeating_crossbowman``
----------------------------------------------



.. list-table::
   :header-rows: 1

   * - Item
     - Valor
   * - Local
     - ``res/rules.txt``
   * - Upgrade
     - ``archer`` → ``repeating_crossbowman`` (``can_upgrade_to``)
   * - Voz (ZH)
     - 诸葛弩手 (``tts.txt`` id 5082)
   * - Stats
     - 3×2 de dano à distância por ciclo, recarga 2.5 s, alcance 4




----


5. Erros comuns
---------------



.. list-table::
   :header-rows: 1

   * - Problema
     - Causa / correção
   * - ``damage_seq`` ignorado
     - ``mdg`` / ``rdg`` base não definido, ou soma dos segmentos ≠ base (divisão manual)
   * - Intervalo errado
     - Antes de 1.4.3.6, o intervalo era ignorado (corrigido); confira a versão do jogo
   * - Dano fracionário + `(damage …)` manual
     - Use divisão automática
   * - Mais de 6 tiros
     - O motor limita a 6 por ataque
   * - Só um som de lançamento
     - Esperado em unidades sem rajada; unidades com rajada precisam de tratamento por tiro (1.4.3.6+)




----


6. Arquivos e testes relacionados
---------------------------------



.. list-table::
   :header-rows: 1

   * - Arquivo
     - Função
   * - ``soundrts/definitions.py``
     - Faz o parse de ``damage_seq`` nas rules
   * - ``soundrts/combat/damage_effects.py``
     - Agenda acertos da rajada e sons de lançamento
   * - ``soundrts/combat/attack_action.py``
     - Preparação de ataque / cooldown
   * - ``soundrts/tests/test_damage_seq_burst.py``
     - Testes de parse e regressão



Execute os testes:

.. code-block:: bash

   python -m pytest soundrts/tests/test_damage_seq_burst.py -q
