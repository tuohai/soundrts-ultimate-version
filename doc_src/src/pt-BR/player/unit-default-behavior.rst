Configuração de comportamento padrão das unidades (``rules.txt``)
=====================================================


Autores de mapas e mods podem definir o comportamento inicial de cada tipo de unidade no início da partida em ``rules.txt``:

- Modo de IA padrão (``ai_mode``): offensive / defensive / guard / chase
- Coleta automática (``auto_gather``): trabalhadores começam coletando automaticamente
- Reparo automático (``auto_repair``): trabalhadores começam reparando automaticamente
- Exploração automática (``auto_explore``): unidades móveis começam explorando automaticamente

Jogadores ainda podem alterar isso no jogo após o spawn.


----


1. Visão geral
-------------



.. list-table::
   :header-rows: 1

   * - Campo
     - Valores
     - Padrão
     - Aplica-se a
     - Descrição
   * - ``ai_mode``
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
     - soldiers=``offensive``, workers=``defensive``
     - unidades de combate
     - modo de IA inicial
   * - ``auto_gather``
     - ``1`` / `0`
     - workers=`1`
     - trabalhadores
     - coleta automática no início
   * - ``auto_repair``
     - ``1`` / `0`
     - workers=`1`
     - trabalhadores
     - reparo automático no início
   * - ``auto_explore``
     - ``1`` / `0`
     - ``0``
     - unidades móveis
     - exploração automática no início
   * - ``can_auto_explore``
     - ``1`` / `0`
     - ``0``
     - unidades móveis
     - mostrar ativar/desativar exploração automática no menu de comandos




Escreva estes no bloco `def <name>` da unidade. Campos omitidos usam os padrões acima.

Exemplo de campanha (caps. 24–27): NPCs-chave usam ``escort`` ou ``ai_mode guard`` para não perseguir antes da entrega/duelo. Após aliança, gatilhos mudam modos:

- `(set_ai_mode offensive c2 1 npc_count_roland …)` — Roland fica ofensivo após o token (cap. 25)
- `(set_ai_mode offensive c2 1 npc_marco_ironhand)` + `(order … ((go c1)))` — cap. 27 (``raynor7``): apenas Marco fica ofensivo; escoltas vão para c1 para limpar a arena
- `(allied_assist computer1)` — todas as unidades de combate aliadas em guard → chase
- `(allied_assist computer1 c2 4 npc_archer_escort)` — apenas arqueiros de escolta → chase
- `(allied_control computer1 c2 4 npc_knight_escort)` — cavaleiros de escolta sob comando do jogador (permanecem em guard); outros auto → chase

Para duelos com rendição (``yield_on_defeat``), habilite em tempo de execução via `` (set_yield_on_defeat 1 …)`` em vez de em ``rules.txt`` no spawn, para NPCs serem mortíveis antes da entrega do token. Veja `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


``auto_explore`` vs ``can_auto_explore``:

``auto_explore`` — se a unidade começa com exploração automática ligada.

``can_auto_explore`` — se o menu de comandos oferece ativar/desativar exploração automática.

Independentes: ex. apenas cavaleiros recebem ``can_auto_explore 1``, ou ``auto_explore 1`` para batedores no início.


----


2. Modo de IA (``ai_mode``)
----------------------------


2.1 Modos
~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Valor
     - Nome
     - Comportamento
   * - ``offensive``
     - Ofensivo
     - ataca unidades hostis no quadrado atual (padrão comum)
   * - ``defensive``
     - Defensivo
     - recua de ameaças hostis quando desfavorável; engaja quando à frente
   * - ``guard``
     - Guarda
     - mantém posição; contra-ataca apenas se habilitado
   * - ``chase``
     - Perseguição
     - mantém um único ``AttackAction`` no inimigo travado e segue pelas saídas entre casas (sem ``go`` automático) até ficar no alcance


2.1.1 Ponto de hold (``position_to_hold``) e sair da casa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Unidades nascem com a casa atual como ``position_to_hold``. Dentro dessa área,
``_must_hold`` impede sair:


.. list-table::
   :header-rows: 1

   * - Modo IA
     - Limitado por ``position_to_hold``?
   * - ``offensive`` / ``guard``
     - Sim (não saem sozinhas sem ordem que faça ``stop()``)
   * - ``defensive``
     - Não (podem recuar)
   * - ``chase``
     - Não (o hold é limpo ao cruzar casas)


Ordens ``go`` / ``attack`` do jogador chamam ``stop()`` no primeiro update e limpam
``position_to_hold``.

Patrulha é um comando com rota, não um modo de IA. Você não pode escrever ``ai_mode patrol``. Use ``guard`` ou ``chase`` para efeitos similares.

2.2 Exemplos
~~~~~~~~~~~~~


.. code-block:: text

   def knight
   class soldier
   ...
   ai_mode guard
   
   def footman
   class soldier
   ...
   ai_mode defensive


2.3 Unidades neutras
~~~~~~~~~~~~~~~~~~


Unidades do jogador em modo ``offensive``, ``defensive`` ou ``chase``:

- não atacam automaticamente unidades neutras (`computer_only ... neutral` creeps / NPCs / vida selvagem);
- não fogem por causa de neutros (modo defensivo só pondera ameaças hostis reais);
- ``go`` padrão / normal em neutro (não imperativo) só move, sem AttackAction;
- a ordem padrão em ``is_huntable`` continua ``attack`` e causa dano;
- para a IA tratar creep / NPC neutro como alvo automático, emita ataque forçado
  (``imperative`` — ex. Ctrl+clique; o motor converte ``go`` imperativo em ``attack``).


Voz: animais de caça (``is_huntable`` / ``herdable``, ex. cervo, ovelha) são anunciados como

"deer , animal", não "neutral , NPC". NPCs de história (``quest_npc``, etc.) ainda dizem

"neutral , NPC". Veja `hunting.htm <hunting-system.htm>`_.


Modo ``guard`` inalterado: sem ataques proativos; contra-ataque apenas se habilitado e atingido.

Creeps neutros do computador ainda usam ``guard`` forçado + contra-ataque do lado deles.

2.4 Notas
~~~~~~~~~~


- Valores inválidos são ignorados (registrados) e voltam ao padrão.
- Creeps neutros (`computer_only ... neutral`) ainda são forçados a ``guard`` + contra-ataque independentemente de ``ai_mode``.


----


3. Coleta automática / reparo automático
------------------------------


Somente para trabalhadores:

- ``auto_gather 1`` — trabalhadores ociosos vão coletar quando há depósito e armazém por perto.
- ``auto_repair 1`` — trabalhadores ociosos reparam aliados danificados no mesmo quadrado (precisa ``can_repair 1``).

Ambos ligados por padrão. Defina ``0`` no def do trabalhador para desativar no início. Jogadores ainda podem alternar no jogo.

:strong:```can_repair`` — ``1`` ou ``0``. Padrão ``1`` em trabalhadores. Com ``0``, ordens de reparo e reparo automático ficam desabilitados.


----


4. Ordem padrão de captura (``can_capture``)
----------------------------------------------


Para unidades com habilidades de ataque, controla a ordem padrão de clique direito em inimigos com
:strong:```capture_hp_threshold 100`` (captura por contato):


.. list-table::
   :header-rows: 1

   * - Valor
     - Comportamento
   * - `1` (padrão)
     - Ordem padrão de captura; IA usa captura por contato
   * - ``0``
     - Ataque/movimento padrão; IA ataca normalmente



Não bloqueia captura em limiares menores (ex. ``30``) via dano de combate — apenas o caminho de captura por contato no limiar 100 e a ordem padrão de clique direito.

.. code-block:: text

   def footman
   class soldier
   can_capture 1
   
   def archer
   class soldier
   can_capture 0


Veja também barracks capturáveis em mapas aleatórios em ``player/英雄无敌与文明5玩法说明.htm``.


----


5. Exploração automática
-----------------


Para qualquer unidade com velocidade > 0. Controlado por ``auto_explore`` (estado inicial) e ``can_auto_explore`` (opção no menu).

- ``can_auto_explore 1`` — menu de comandos mostra ativar/desativar exploração automática (apenas em unidades que têm).
- ``auto_explore 1`` — começa explorando quando ocioso; combate usa ``ai_mode`` quando inimigos aparecem.

Em tempo de execução: outras ordens pausam exploração; retoma quando ocioso de novo. Desativar exploração automática sempre disponível enquanto explora. Ativar apenas se ``can_auto_explore 1``. Exploração da IA do computador é separada.


----


6. Exemplo combinado
---------------------


.. code-block:: text

   def peasant
   class worker
   auto_gather 1
   auto_repair 0
   ai_mode defensive
   
   def knight
   class soldier
   auto_explore 1
   can_auto_explore 1
   ai_mode guard
   
   def footman
   class soldier
   ai_mode defensive



----


7. FAQ
--------


``Q: Por que ``ai_mode patrol`` não funciona?``  
R: Patrulha precisa de um caminho. Valores válidos: ``offensive``, ``defensive``, ``guard``, ``chase``.

``Q: ``auto_explore`` em um edifício?``  
R: Ignorado (velocidade 0).

``Q: ``auto_gather`` em um soldado?``  
R: Só faz sentido em trabalhadores.

P: Como chase difere do antigo salto com ``go`` automático?  
R: Agora mantém o ataque e segue entre casas; não é limitado por ``position_to_hold``.
Ofensivo / guarda ainda são, a menos que o jogador ordene mover.

P: Unidades ofensivas/chase atacam automaticamente NPCs neutros?  
R: Não. Modos ofensivo, defensivo e chase ignoram neutros para ataque automático e fuga;
use comando de ataque forçado para lutar contra eles.

P: Por que arqueiros atacam um barracks no clique direito mas footmen capturam?  
R: Verifique ``can_capture``. Padrão ``1`` → captura em alvos ``capture_hp_threshold 100``; ``0`` → ataque normal.


----


8. Referência de campos
--------------------



.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Valores válidos
   * - ``ai_mode``
     - string
     - ``offensive`` / ``defensive`` / ``guard`` / ``chase``
   * - ``auto_gather``
     - int
     - ``1`` / `0`
   * - ``auto_repair``
     - int
     - ``1`` / `0`
   * - ``auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_auto_explore``
     - int
     - ``1`` / `0`
   * - ``can_capture``
     - int
     - ``1`` / `0`
