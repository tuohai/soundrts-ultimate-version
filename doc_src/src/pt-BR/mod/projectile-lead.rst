Previsão de projéteis (projectile_lead) e velocidade por via
============================================================

Para **autores de mods**: cada projétil (corpo a corpo / à distância) tem uma **velocidade de voo** (tiles/s); ataques sem projétil não são afetados.

Importante: velocidade, não duração
-----------------------------------

``rdg_projectile_speed`` / ``mdg_projectile_speed`` (e o obsoleto ``projectile_speed``) significam **quão rápido** o projétil viaja (tiles por segundo), **não** “quantos segundos até o impacto”.

- ``7`` → sete tiles por segundo (escala de arqueiro AoE2)
- **Não** escreva ``0.57`` porque quer um acerto em ~0.57 s — isso é lido como 0.57 tiles/s e fica extremamente lento
- O tempo até o acerto é **derivado**: distância ÷ velocidade (mais longe = mais tempo)

Visão geral
-----------

.. list-table::
   :header-rows: 1

   * - Campo
     - Descrição
   * - ``rdg_projectile`` + ``rdg_projectile_speed``
     - Projétil à distância: **velocidade** (tiles/s)
   * - ``mdg_projectile`` + ``mdg_projectile_speed``
     - Projétil corpo a corpo: **velocidade** (tiles/s, ex.: mangonel)
   * - ``projectile_lead``
     - Só à distância: após voar nessa velocidade, erra se o alvo saiu do ponto de mira
   * - ``projectile_speed``
     - Nome compartilhado **obsoleto**; migrado para a via correspondente no carregamento

Velocidade 0, ou a via não é projétil → acerto instantâneo (sem voo).

Unidades com ambos os ataques
-----------------------------

Se a unidade tem ``mdg`` e ``rdg`` (ex.: ambos com range 4):

- Só ``rdg_projectile_speed`` → **só à distância** voa nessa velocidade; corpo a corpo é instantâneo (salvo ``mdg_projectile`` + velocidade)
- Só ``mdg_projectile_speed`` → **só o projétil corpo a corpo** voa nessa velocidade
- Corpo a corpo normal (sem ``mdg_projectile``) **nunca** voa

Exemplos em rules
-----------------

::

    def aoe_archer
    rdg_projectile 1
    rdg_projectile_speed 7

    def mangonel
    mdg_projectile 1
    mdg_projectile_speed 3.5

    def ballistics
    class upgrade
    effect info 8510
    effect bonus projectile_lead 1
    effect_bonus_targets archer_unit -hand_cannoneer galley scouttower aoe_castle town_center townhall

aoe2 (estilo DE, todas **velocidades**): flechas/torres ``7``, mangonel ``3.5``, trabuco ``1.6``.

Obsoleto
--------

``mdg_delay`` / ``rdg_delay`` (antiga “duração em segundos”) e ``projectile_speed`` compartilhado: o combate não lê; convertidos/migrados para **velocidades** por via no carregamento. Mods novos: use ``*_projectile_speed`` diretamente.

Motor
------------

- ``attack_action._calc_projectile_flight_ms(target, is_melee=…)`` (deriva ms de chegada a partir da velocidade)
- ``definitions._migrate_legacy_projectile_delay``

Veja também: `Manual de modding <modding.htm>`_, `Notas de versão <../relnotes.htm>`_ (1.4.6.9).
