Sistema de caça
===============


O SoundRTS oferece caça no estilo Age of Empires: trabalhadores atacam animais selvagens, animais caçados deixam carcaças de comida coletáveis, e ovelhas podem ser conduzidas.


----


1. Fluxo do jogador
-------------------


1. Backspace / ordem padrão ou clique direito em um animal → ``attack`` em ``is_huntable`` (ataque normal causa dano; não precisa de imperativo)
2. Ao matar → surge ``food_carcass``; a ordem de ataque completa (**sem** bip falso ``order_impossible``)
3. Coleta automática → após matar, o trabalhador pode enfileirar coleta; com ``auto_gather`` também recolhe e entrega comida
4. Fuga ao ser atingido → cervos e ovelhas fogem; javalis contra-atacam
5. Condução (opcional) → trabalhadores com ``can_herd 1`` podem conduzir animais ``herdable`` (ex.: ovelhas)


Nota: a ordem padrão em creeps / NPCs neutros comuns é ``go`` (só mover); em animais caçáveis continua ``attack``.
Modos ofensivo / defensivo / chase **não** atacam automaticamente animais neutros sem ataque imperativo.


----


2. Voz: rótulo "animal" (não NPC)
------------------------------------


Animais de caça são colocados com ``computer_only ... neutral``, mas não são anunciados como "neutral NPC".


.. list-table::
   :header-rows: 1

   * - Situação
     - Exemplo de anúncio
   * - Selecionar um cervo
     - deer , animal
   * - Resumo do quadrado
     - , 2 deer , animal
   * - Ctrl+Shift+F4 para jogador só com vida selvagem
     - you are animal



Regras:

- Unidades com ``is_huntable 1`` ou ``herdable 1`` → vida selvagem → anunciadas como animal
- Uma vírgula separa o nome da unidade e animal (mesmo padrão dos rótulos inimigo/aliado)
- Ctrl+Shift+F4 diz you are animal somente quando todas as unidades vivas daquele jogador são vida selvagem; ``quest_npc`` misturado com cervo ainda diz you are neutral NPC

NPCs de história (``quest_npc``, etc.) mantêm neutral , NPC.


----


3. Colocação no mapa
------------------


.. code-block:: text

   computer_only 0 0 neutral b3 4 deer 2 sheep


Mapas aleatórios também geram pomares e vida selvagem perto das posições iniciais.

3.1 Diplomacia: vida selvagem não são aliados
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


A vida selvagem é gerada via ``computer_only``, mas não entra na aliança padrão ``"ai"`` do computador e não pode fazer aliança com jogadores ou outras facções.


.. list-table::
   :header-rows: 1

   * - Regra
     - Significado
   * - Detecção
     - O slot ``computer_only`` contém apenas unidades com ``is_huntable 1`` ou ``herdable 1`` (cervo, ovelha, um tigre personalizado, etc.)
   * - Motor
     - Esse computador recebe `alliance = None`; ``allied`` é apenas ele mesmo
   * - Vários rebanhos
     - Cada linha ``computer_only`` é um ponto de caça separado; rebanhos não se aliam entre si
   * - Slot misto
     - Se a mesma linha mistura animais e footmen, o slot inteiro permanece IA normal e entra em `"ai"`
   * - Diplomacia do jogador
     - Jogadores neutros não podem aliança F12; vida selvagem nunca é facção diplomática



Animal personalizado (isolado de ``"ai"``):

.. code-block:: text

   def tiger
   class soldier
   is_huntable 1
   ...
   
   computer_only 0 0 neutral 5,5 2 tiger


Para fazer vários grupos de vida selvagem agirem como uma "facção natureza", use o gatilho ``(alliance …)`` explicitamente; isso não é o comportamento padrão de caça.


----


4. rules.txt
--------------


Unidades integradas
~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tipo
     - Notas
   * - ``deer``
     - 35 comida, foge ao ser atingido
   * - ``sheep``
     - 25 comida, herdable, foge
   * - ``boar``
     - 50 comida, contra-ataca
   * - ``food_carcass``
     - carcaça coletável (``collision 0``)



Trabalhadores ``can_gather`` inclui ``food_carcass`` e ``orchard``.

Propriedades dos animais
~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Propriedade
     - Significado
   * - ``is_huntable 1``
     - caçável; clique direito padrão é atacar
   * - ``flee_on_hit 1``
     - foge do atacante
   * - ``herdable 1``
     - pode ser conduzido por trabalhadores ``can_herd``
   * - ``food_deposit``
     - tipo de depósito de carcaça na morte
   * - ``food_deposit_qty``
     - quantidade de comida na carcaça
   * - ``no_number 1``
     - omite número quando há apenas um daquele tipo



Trabalhador: ``can_herd 1`` habilita condução (padrão ``0``).

Exemplo de animal personalizado
~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def wolf
   class soldier
   is_huntable 1
   flee_on_hit 1
   food_deposit food_carcass
   food_deposit_qty 40
   no_number 1
   ai_mode guard


Tecnologia
~~~~~~~~~~~


``hunting_techniques``: coleta mais rápida de pomar/carcassa, maior rendimento, bônus de comida na carcaça dos animais. Pesquisada na prefeitura.


----


5. Vida selvagem vs NPCs de história
---------------------------



.. list-table::
   :header-rows: 1

   * - 
     - Vida selvagem
     - NPC de história
   * - Exemplos
     - ``deer``, ``sheep``, ``boar``
     - ``quest_npc``, ``npc_knight``
   * - Detecção
     - ``is_huntable`` / ``herdable``
     - (pode ter ``receive_items``)
   * - Voz
     - animal
     - neutral , NPC
   * - Ataque automático do jogador
     - não (ataque forçado necessário)
     - não



Veja `unit-default-behavior <unit-default-behavior.htm>`_.


----


6. Código e testes
-----------------



.. list-table::
   :header-rows: 1

   * - Função
     - Caminho
   * - Lógica de caça
     - ``soundrts/worldunit/worldcreature.py``, ``worldworker.py``
   * - Isolamento de aliança da vida selvagem
     - ``soundrts/worldplayerbase/base.py``, ``world/world_objects.py``
   * - Voz dos animais
     - ``soundrts/clientgameentity/properties.py``
   * - Voz de troca de jogador
     - ``soundrts/clientgame/game_resources.py``
   * - Geração em mapas aleatórios
     - ``soundrts/randommap.py``
   * - Testes
     - ``soundrts/tests/test_hunting.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``
