Predicción de proyectiles (projectile_lead) y velocidad por vía
===============================================================

Para **autores de mods**: cada proyectil (cuerpo a cuerpo / a distancia) tiene una **velocidad de vuelo** (casillas/s); los ataques sin proyectil no se ven afectados.

Importante: velocidad, no duración
----------------------------------

``rdg_projectile_speed`` / ``mdg_projectile_speed`` (y el obsoleto ``projectile_speed``) indican **qué tan rápido** viaja el proyectil (casillas por segundo), **no** “cuántos segundos hasta el impacto”.

- ``7`` → siete casillas por segundo (escala de arquero AoE2)
- **No** escriba ``0.57`` porque desea un impacto en ~0.57 s — se interpreta como 0.57 casillas/s y se siente extremadamente lento
- El tiempo hasta el impacto se **deriva**: distancia ÷ velocidad (más lejos = más tiempo)

Resumen
-------

.. list-table::
   :header-rows: 1

   * - Campo
     - Descripción
   * - ``rdg_projectile`` + ``rdg_projectile_speed``
     - Proyectil a distancia: **velocidad** (casillas/s)
   * - ``mdg_projectile`` + ``mdg_projectile_speed``
     - Proyectil cuerpo a cuerpo: **velocidad** (casillas/s, p. ej. mangonel)
   * - ``projectile_lead``
     - Solo a distancia: tras viajar a esa velocidad, fallo si el objetivo dejó el punto de mira
   * - ``projectile_speed``
     - Nombre compartido **obsoleto**; se migra a la vía correspondiente al cargar

Velocidad 0, o esa vía no es proyectil → impacto instantáneo (sin vuelo).

Unidades con ambos ataques
--------------------------

Si la unidad tiene ``mdg`` y ``rdg`` (p. ej. ambos con range 4):

- Solo ``rdg_projectile_speed`` → **solo a distancia** vuela a esa velocidad; cuerpo a cuerpo instantáneo (salvo ``mdg_projectile`` + velocidad)
- Solo ``mdg_projectile_speed`` → **solo el proyectil cuerpo a cuerpo** vuela a esa velocidad
- El cuerpo a cuerpo normal (sin ``mdg_projectile``) **nunca** vuela

Ejemplos en rules
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

aoe2 (estilo DE, todas **velocidades**): flechas/torres ``7``, mangonel ``3.5``, trabuquete ``1.6``.

Obsoleto
--------

``mdg_delay`` / ``rdg_delay`` (antigua “duración en segundos”) y ``projectile_speed`` compartido: el combate no los lee; se convierten/migran a **velocidades** por vía al cargar. Mods nuevos: use ``*_projectile_speed`` directamente.

Motor
----------------------

- ``attack_action._calc_projectile_flight_ms(target, is_melee=…)`` (deriva ms de llegada desde la velocidad)
- ``definitions._migrate_legacy_projectile_delay``

Véase también: `Manual de modding <modding.htm>`_, `Notas de la versión <../relnotes.htm>`_ (1.4.6.9).
