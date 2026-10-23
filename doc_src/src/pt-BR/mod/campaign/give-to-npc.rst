Dar itens a NPCs (``give`` + ``npc_has_item``)
===============================================


Permite que jogadores entreguem itens carregados a outra unidade (NPC neutro,
aliado, inimigo) e testem a entrega com :strong:```npc_has_item``.


----


1. Visão geral
--------------



.. list-table::
   :header-rows: 1

   * - Parte
     - Nome
     - Função
   * - Ordem
     - ``give``
     - transferir item do portador para o alvo
   * - Campo
     - ``receive_items``
     - interruptor mestre (padrão 0)
   * - Campo
     - ``accepted_items``
     - lista branca de itens; vazio = qualquer
   * - Campo
     - ``accept_from``
     - relação do doador: ``self``/``ally``/``neutral``/``enemy``; vazio =
       qualquer
   * - Campo
     - ``accept_givers``
     - tipos de unidade doador; vazio = qualquer
   * - Condição
     - ``npc_has_item``
     - alvo recebeu / possui item
   * - Condição
     - ``npc_has_items``
     - alvo recebeu / possui uma *quantidade* de itens (objetivos de coleção)



Em caso de sucesso: item vai para o inventário do alvo; ``received_items``
registra o tipo; feedback de áudio/UI.


Alvos precisam de ``receive_items 1`` em ``rules.txt`` ou a entrega é
rejeitada.


----


2. Uso pelo jogador
-------------------


O portador precisa de ``inventory_capacity \> 0`` e o item (via ``pickup``).

1. Clique direito em unidade não inimiga enquanto carrega → give padrão
   (primeiro item aceitável).
2. Menu de comandos: "Give".
3. Atalho: ``g`` (``style.txt``).

Give por clique direito apenas quando carregando + alvo não inimigo e não
edifício.


----


3. Script: ``give`` em gatilhos
-------------------------------


.. code-block:: text

   give <target_unit_id>
   give <target_unit_id> <item>    ; type_name ou id do item



----


4. ``npc_has_item``
-------------------


.. code-block:: text

   (npc_has_item <NPC_selector> <item_type> [square])
   (npc_has_item <index> <unit_type> <item_type>)
   (npc_has_item <square> <index> <unit_type> <item_type>)


- Clássico: seletor = ``type_name`` ou id da unidade; casa opcional = NPC
  atualmente naquela casa.
- Índice global: `(npc_has_item 3 quest_npc short_sword)` — 3º `<unit_type>`
  spawnado daquele dono (qualquer casa).
- Índice por casa: N-ésimo em `<square>` (estável após mover). Veja
  `map-unit-index-selectors.md <unit-index.htm>`_. Capítulo 28 usa forma
  global.

Verdadeiro se ``received_items`` contém o tipo ou o inventário ainda o possui.

Compare com `find-item-objective <find-item-objective.htm>`_. Para chegar e
sumir sem NPC, use `brought-item-delivery <brought-item-delivery.htm>`_.


----


4b. ``npc_has_items`` (variante com contador)
-----------------------------------------------

.. code-block:: text

   (npc_has_items <NPC_selector> <item_type> <count> [square])
   (npc_has_items <index> <unit_type> <item_type> <count>)
   (npc_has_items <square> <index> <unit_type> <item_type> <count>)


Os mesmos seletores de ``npc_has_item``, mais um ``<count>`` obrigatório: a
condição só é verdadeira quando a unidade tem **pelo menos essa quantidade**
de itens desse tipo.

``npc_has_item`` pergunta apenas se a unidade tem o *tipo* de item
(``received_items`` é um conjunto), então entregar um único item já a satisfaz.
Use ``npc_has_items`` para objetivos de coleta que exigem várias cópias — por
exemplo o capítulo 4 de Joan of Arc exige as três relíquias na catedral de
Reims:

.. code-block:: text

   trigger player1 (npc_has_items npc_reims_cathedral relic 3 c5) (do (objective_complete 1) (cut_scene 8837))


A contagem é o maior entre (a) quantos itens foram entregues via ``give`` e
(b) quantos estão agora no inventário da unidade — assim sobrevive ao item
sair do inventário de novo, e também conta os itens com que o NPC começa. O
mesmo item nunca é contado duas vezes.

``<count>`` deve ser um inteiro positivo; ``0``, um número negativo ou um token
não numérico tornam a condição falsa.

----


5. Regras de recebimento
------------------------


Tudo deve passar:


.. list-table::
   :header-rows: 1

   * - Campo
     - Valores
     - 
   * - ``receive_items``
     - ``1`` / `0`
     - padrão 0
   * - ``accepted_items``
     - lista de tipos
     - vazio = qualquer; ``is_a`` funciona
   * - ``accept_from``
     - relações
     - vazio = qualquer
   * - ``accept_givers``
     - tipos de unidade
     - vazio = qualquer



Relações (receptor vs doador): ``self`` > ``ally`` > ``neutral`` > ``enemy``.

Com ``accept_from enemy``, clique direito naquele inimigo com o item certo
vira give em vez de ataque (apenas para aquele item + tipo de unidade).

Exemplos
~~~~~~~~


Cavaleiro aliado aceita apenas lança:

.. code-block:: text

   def knight
   receive_items 1
   accepted_items knight_lance
   accept_from ally


Líder inimigo aceita carta apenas de peasant:

.. code-block:: text

   def npc_knight_leader
   receive_items 1
   accepted_items secret_letter
   accept_from enemy
   accept_givers peasant
   ai_mode guard


Campanha caps. 24–27: `campaign-northern-arc.htm <campaign-secret-letter-alliance.htm>`_.


----


6. Mapa demo
------------


``res/multi/give_demo.txt``:

.. code-block:: text

   health_potion a1
   computer_only 0 0 neutral c3 quest_npc
   trigger player1 (npc_has_item quest_npc health_potion) (objective_complete 1)


Exemplos de campanha (``The Legend of Raynor``): cap. 14 entregar ``pickaxe``
a ``npc_peasant`` aliado; cap. 15 entregar ``knight_lance`` a ``npc_knight``
neutro; cap. 16 entregar ``wand`` a ``npc_mage`` inimigo.
Veja ``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``.
Multijogador: ``res/multi/give_demo.txt``.


----


7. Arquivos de implementação
----------------------------



.. list-table::
   :header-rows: 1

   * - Função
     - Caminho
   * - ``GiveOrder``
     - ``soundrts/worldorders/skills.py``
   * - Transferência
     - ``soundrts/worldunit/world_order.py``
   * - ``accepts_item``
     - ``soundrts/worldunit/worldcreature.py``
   * - Gatilho
     - ``soundrts/worldplayerbase/triggers.py``
   * - Testes
     - ``soundrts/tests/test_give_item_to_npc.py``




----


8. Casos extremos
-----------------


- Verificação tripla: ``receive_items``, ``accepted_items``, ``accept_from`` (+
  ``accept_givers`` se definido).
- Alvo deve ser unidade com ``player``.
- Item deve estar no inventário do doador.
- Entrega **ignora** ``inventory_capacity`` do alvo (transferência de história);
  excesso cai no chão.
- ``equip`` roda no receptor como ``pickup`` (buffs/habilidades aplicam).


----


9. Testes
---------


.. code-block:: text

   python -m pytest soundrts/tests/test_give_item_to_npc.py -q


Também: ``test_campaign_alliance_transfer_triggers.py`` para gatilhos de
aliança / transferência.


----


10. Campanha caps. 24–27
------------------------



.. list-table::
   :header-rows: 1

   * - Cap.
     - Item
     - Receptor
   * - 24
     - ``secret_letter``
     - ``npc_knight_leader`` (Garrek)
   * - 25
     - ``garrek_token``
     - ``npc_count_roland`` (Roland)
   * - 26
     - ``war_banner``
     - ``npc_general_vera`` (Vera)
   * - 27
     - —
     - duelo com ``npc_marco_ironhand``



Após traidores morrerem no cap. 24, ``(add_inventory_item garrek_token 1
raynor)`` coloca o token no inventário de Raynor para o cap. 25. Execute
``cut_scene`` em gatilhos player1 após ``npc_has_item`` para o humano ouvir
voz. Walkthrough completo: `campaign-northern-arc.htm
<campaign-secret-letter-alliance.htm>`_.


----


11. Campanha cap. 28 (entrega indexada)
---------------------------------------


.. code-block:: text

   trigger player1 (npc_has_item 3 quest_npc short_sword) (objective_complete 2)


Apenas o 3º ``quest_npc`` em B2 conta. O mesmo capítulo demonstra
``killed_target`` indexado e derrota por abate errado: `map-unit-index-selectors
<unit-index.htm>`_.
