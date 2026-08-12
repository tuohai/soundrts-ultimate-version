Predizione dei proiettili (projectile_lead) e velocità per corsia
=================================================================

Per **autori di mod**: ogni proiettile (corpo a corpo / a distanza) ha una **velocità di volo** (caselle/s); gli attacchi senza proiettile non sono interessati.

Importante: velocità, non durata
--------------------------------

``rdg_projectile_speed`` / ``mdg_projectile_speed`` (e il deprecato ``projectile_speed``) indicano **quanto veloce** viaggia il proiettile (caselle al secondo), **non** “quanti secondi fino all’impatto”.

- ``7`` → sette caselle al secondo (scala arciere AoE2)
- **Non** scrivere ``0.57`` perché si vuole un colpo in ~0.57 s — viene letto come 0.57 caselle/s e sembra lentissimo
- Il tempo di arrivo è **derivato**: distanza ÷ velocità (più lontano = più tempo)

Panoramica
----------

.. list-table::
   :header-rows: 1

   * - Campo
     - Descrizione
   * - ``rdg_projectile`` + ``rdg_projectile_speed``
     - Proiettile a distanza: **velocità** (caselle/s)
   * - ``mdg_projectile`` + ``mdg_projectile_speed``
     - Proiettile corpo a corpo: **velocità** (caselle/s, es. mangonel)
   * - ``projectile_lead``
     - Solo a distanza: dopo il volo a quella velocità, miss se il bersaglio ha lasciato il punto di mira
   * - ``projectile_speed``
     - Nome condiviso **deprecato**; migrato alla corsia corrispondente al caricamento

Velocità 0, o la corsia non è un proiettile → colpo istantaneo (nessun volo).

Unità con entrambi gli attacchi
-------------------------------

Se l’unità ha sia ``mdg`` sia ``rdg`` (es. entrambi con range 4):

- Solo ``rdg_projectile_speed`` → **solo a distanza** vola a quella velocità; corpo a corpo istantaneo (salvo ``mdg_projectile`` + velocità)
- Solo ``mdg_projectile_speed`` → **solo il proiettile corpo a corpo** vola a quella velocità
- Il corpo a corpo normale (senza ``mdg_projectile``) **non** vola mai

Esempi rules
------------

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

aoe2 (stile DE, tutte **velocità**): frecce/torri ``7``, mangonel ``3.5``, trabucco ``1.6``.

Deprecato
---------

``mdg_delay`` / ``rdg_delay`` (vecchia “durata in secondi”) e ``projectile_speed`` condiviso: il combattimento non li legge; convertiti/migrati a **velocità** per corsia al caricamento. Mod nuove: impostare ``*_projectile_speed`` direttamente.

Motore / sync
-------------

- ``attack_action._calc_projectile_flight_ms(target, is_melee=…)`` (deriva ms di arrivo dalla velocità)
- ``definitions._migrate_legacy_projectile_delay``
- Sync: ``tools/_sync_projectile_lead_fix8_fix14.py`` → 修复8 / 修复14 (senza mods/aoe2)

Vedi anche: `Manuale di modding <modding.htm>`_, `Note di rilascio <../relnotes.htm>`_ (1.4.6.9).
