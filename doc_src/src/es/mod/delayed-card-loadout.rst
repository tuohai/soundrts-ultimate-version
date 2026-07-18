Cartas de carga diferidas
=========================

Guía del jugador: `../player/loadout-cards.htm <../player/loadout-cards.htm>`_

Las cartas previas a la misión pueden aplicarse tras :strong:```delay`` / ``delay_minutes`` en lugar de al inicio de la partida.

Véase también: `achievement-system <achievement-system.htm>`_, `score-grading-system.htm <score-grading-system.htm>`_.

----

1. Alcance
----------

- Solo TrainingGame (mapa personalizado / aleatorio contra la IA), igual que las cartas instantáneas; no campaña ni multijugador.
- La selección de carta y el descuento de carga ocurren al inicio de la partida; los efectos se disparan tras el tiempo de juego.
- Las cartas diferidas usan ranuras de carga y cuestan una carga como las instantáneas; ``min_rank`` / ``faction`` sin cambios.

----

2. Sintaxis de cards.txt
------------------------

.. list-table::
   :header-rows: 1

   * - Directiva
     - Significado
   * - ``delay \<seconds\>``
     - Esperar segundos de tiempo de juego
   * - ``delay_minutes \<n\>``
     - Igual que `delay (n×60)`
   * - ``tech \<upgrade_id\> [...]``
     - Conceder mejora(s) cuando expire el retraso

Combínalo con ``spawn`` y ``resource`` en una misma carta; un solo retraso compartido, todos los efectos se aplican juntos.

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

- Omite ``delay`` o usa `0` para efecto inmediato (comportamiento heredado).

----

3. Tiempo de ejecución
----------------------

En el momento de aplicar la carga, ``delay \> 0`` registra ``world.schedule_after(delay_ms, callback)``.  
``delay_ms = delay_seconds × 1000 × world.timer_coefficient``.

Cuando el temporizador se dispara: aplica recursos → apariciones cerca del inicio (consumen población) → tecnologías; el humano local recibe la voz LOADOUT_CARD_TRIGGERED.

La carga se consume cuando la carta se programa con éxito al inicio de la partida, no cuando se disparan los efectos.

----

4. Voz (TTS)
------------

.. list-table::
   :header-rows: 1

   * - ID
     - Inglés
     - Uso
   * - 5387
     - (effects in)
     - Aplicado / arsenal
   * - 5392
     - (after delay)
     - sufijo
   * - 5388
     - loadout card effect triggered
     - Al dispararse
   * - 5389–5393
     - spawn / resource / tech hints
     - Arsenal

Los minutos enteros se anuncian como “N minutos”; en caso contrario, segundos.

----

5. Ejemplos vanilla
-------------------

.. list-table::
   :header-rows: 1

   * - Carta
     - Efecto
     - Logro
   * - ``card_reinforcements_delayed``
     - 3 footman tras 10 min
     - ``reinforcement_contract``
   * - ``card_delayed_melee_weapon``
     - ``melee_weapon`` tras 8 min
     - ``defeat_expert``

----

6. Pruebas
----------

.. code-block:: bash

   python -m pytest soundrts/tests/test_cards.py -k delay -v
   python -m pytest soundrts/tests/test_card_loadout.py -k delayed -v
