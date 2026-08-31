Upgrades de linha de unidade e treinamento de nível máximo (line_upgrade)
=========================================================================

Para **autores de mods**: configure em ``rules.txt`` “pesquisar uma forma → desbloquear o treinamento de nível máximo → transformar unidades no campo”, sem nomes de unidade fixos no motor. As linhas do quartel de Age of Empires II DE funcionam assim.

Visão geral
-----------

.. list-table::
   :header-rows: 1

   * - Recurso
     - Descrição
   * - Treinamento de nível máximo
     - O ``can_train`` do edifício lista a raiz (ex.: ``militia``); treina-se a forma mais alta desbloqueada
   * - Upgrade de linha pesquisável
     - Marque a forma com ``line_upgrade 1`` e coloque em ``can_research``; ao concluir, vai para ``player.upgrades``
   * - Transformação no campo
     - Ao concluir a pesquisa, unidades cujo ``can_upgrade_to`` inclui essa forma transformam-se na hora
   * - Fila de produção
     - Ordens ``train`` na fila ou em curso da mesma linha passam à forma nova (AoE2 DE: mangonéis na fila saem como onagros). Custo e tempo restante já pagos não mudam
   * - Custo de treinamento
     - Por padrão cobra-se ``cost`` / ``time_cost`` da **raiz** (substitua com ``train_cost`` / ``train_time``)

O motor **não** fixa civilizações nem ids de unidade — só campos de rules e cadeias ``can_upgrade_to``.

Sintaxe em rules
----------------

1. Linha de unidade (``can_upgrade_to``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def militia
    class soldier
    cost 20 0 50 0
    time_cost 21
    can_upgrade_to man_at_arms

    def man_at_arms
    is_a militia
    cost 40 0 100 0
    time_cost 40
    requirements feudal_age
    line_upgrade 1
    can_upgrade_to long_swordsman

- ``cost`` / ``time_cost`` de níveis médios/altos costumam ser o preço de **pesquisa** (como em DE).
- O treinamento ainda usa o custo da raiz, salvo ``train_cost`` / ``train_time``.

2. Edifício: slots de treino + pesquisa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    def barracks
    class building
    can_train militia spearman
    can_research tracking squires man_at_arms long_swordsman …

- Liste só raízes em ``can_train``; o menu mapeia para o nível mais alto desbloqueado.
- Após listar uma forma ``line_upgrade 1`` em ``can_research``, pesquisa-se como tecnologia.

3. Effect de tecnologia opcional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Com ``class upgrade``, pode escrever::

    effect unit_line_upgrade man_at_arms

Mesmo resultado de pesquisar a forma diretamente (upgrades + morph). Cada alvo vale uma vez por jogador.

Relação com morph automático por era
------------------------------------

.. list-table::
   :header-rows: 1

   * - Marca
     - Comportamento
   * - (nenhuma)
     - Se a phase tem ``units_auto_upgrade 1`` e o alvo inclui esse nome de era em ``requirements``, pode morphar com a era
   * - ``line_upgrade 1``
     - **Não** morpha com a era; precisa pesquisar; o treinamento também exige o nome em ``player.upgrades``
   * - ``no_auto_upgrade 1``
     - Pula morph por era; o treinamento ainda exige pesquisa (mesmo limiar que ``line_upgrade``)

Para linhas militares estilo AoE2 DE, use ``line_upgrade 1``, não só ``units_auto_upgrade``.

O menu da unidade ``upgrade_to`` **não** oferece mais formas ``line_upgrade`` (evita pagar a diferença por unidade, ao contrário de AoE2). Pesquise-as em ``can_research`` do edifício.

Linhas de edifícios (torres, muralhas) igual: ``can_build`` lista a raiz; após pesquisar, o menu mapeia para o nível máximo; o custo de construção usa a raiz (substitua com ``train_cost``). ``line_upgrade_also`` desbloqueia várias formas numa pesquisa.

Pontos de entrada do motor (referência)
---------------------------------------

.. list-table::
   :header-rows: 1

   * - Símbolo
     - Local
   * - ``resolve_trainable_unit_type``
     - ``soundrts/world_build_rules.py``
   * - ``effective_can_train`` / ``unit_train_cost`` / ``unit_train_time``
     - idem
   * - ``apply_unit_line_upgrade``
     - idem
   * - ``remap_queued_train_orders_for_line_upgrade`` / ``resolved_train_type_class``
     - idem
   * - ``ResearchOrder.complete``
     - ``soundrts/worldorders/production.py``
   * - ``effect_unit_line_upgrade``
     - ``soundrts/worldupgrade/attribute_effects.py``
   * - Skip de era
     - ``soundrts/worldphase.py`` → ``_auto_upgrade_units``
   * - Atributo padrão
     - ``Creature.line_upgrade`` (``worldcreature.py``)
   * - Atributo int de rules
     - ``definitions.py`` → ``line_upgrade``

Testes
------

``soundrts/tests/test_train_line_resolve.py``: a era sozinha não desbloqueia; após upgrades / ``apply_unit_line_upgrade``, treinamento de nível máximo e morph funcionam; concluir a pesquisa reatribui a fila da mesma linha.

Mod aoe2
--------

``mods/aoe2/rules.txt`` marca formas de espada, lança, arco, cavalaria e cerco com ``line_upgrade 1`` e liga-as ao ``can_research`` de quartel / arco / estábulo / oficina (e variantes de civ). Fontes: ``mods/aoe2/SOURCES.md``.

Veja também: `Manual de modding <modding.htm>`_.
