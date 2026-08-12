Attacchi a raffica (``damage_seq``) e balestra a ripetizione
=============================================================


Da SoundRTS 1.3.8.2 (migliorato in 1.4.3.6), le unità possono eseguire attacchi a raffica / in sequenza: un ciclo d'attacco spara diversi colpi in rapida successione, simile al Chu Ko Nu (balestra a ripetizione) di *Age of Empires*. Ogni colpo tira indipendentemente colpo, critico e debuff.

Riferimento ufficiale: ``mod/modding.rst`` (Combat system → ``damage_seq``).

.. note::

   **Non è la stessa cosa di ``effect burst`` sulle abilità:** Questa pagina tratta gli **attacchi normali delle unità** tramite ``damage_seq`` (es. balestra a ripetizione). I colpi combo delle abilità usano ``effect burst mdg|rdg …`` su ``class skill``, lanciati manualmente o auto-attivati, con sintassi e collocazione diverse. Vedi la guida alle abilità (`../mod/skills-and-effects.htm`_, sezione "进阶" / Advanced).


----


1. Panoramica
--------------



.. list-table::
   :header-rows: 1

   * - Aspetto
     - Comportamento
   * - Danno totale per ciclo
     - Suddivisione pari/manuale: resta uguale a ``mdg`` / ``rdg``; modalità ``secondary``: primo live + frecce fisse successive (può superare la base)
   * - Colpi per ciclo
     - Fino a 6 (`damage_seq … <times>`)
   * - Tiraggi di colpo
     - Indipendenti per ogni colpo; le frecce secondarie colpiscono al 100%
   * - Tempo di ricarica
     - ``mdg_cd`` / ``rdg_cd`` inizia dopo la fine dell'intera raffica
   * - Suoni di lancio
     - Un ``launch_mdg`` / ``launch_rdg`` per colpo




----


2. Configurazione in rules.txt
-------------------------------


2.1 Sintassi
~~~~~~~~~~~~~


.. code-block:: text

   damage_seq mdg|rdg <times> [(damage d1 d2 ...)] [(secondary pierce melee)] [(interval seconds)]


Definisci il ``mdg`` o ``rdg`` di base prima di ``damage_seq``.

2.2 Suddivisione automatica (da 1.4.3.6)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Ometti ``(damage …)`` per dividere il danno di base in parti uguali:

.. code-block:: text

   rdg 6
   damage_seq rdg 3 (interval 0.25)


→ tre colpi da 2 di danno ciascuno. Funziona con danno di base frazionario (es. ``rdg 7.5`` con 3 colpi → 2,5 ciascuno).

2.3 Suddivisione manuale
~~~~~~~~~~~~~~~~~~~~~~~~~


I valori interi dei segmenti devono sommare al danno di base (stesse unità delle regole):

.. code-block:: text

   mdg 12
   damage_seq mdg 3 (damage 6 3 3) (interval 0.2)


Il ``(damage …)`` manuale usa solo valori interi; il danno di base frazionario (es. ``rdg 2.5``) non si può esprimere così — usa invece la suddivisione automatica.


2.3b Frecce secondarie AoE2 (``secondary``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Allineato al Chu Ko Nu di Age of Empires II DE: primo colpo = attacco live dell’unità (applicano gli upgrade) + melee fisso; colpi successivi = pierce + melee fissi (**non** potenziati da fabbro/chimica). Il melee può essere ``0`` (danneggia ancora armature melee negative come gli arieti).

.. code-block:: text

   rdg 8
   rdg_cd 2.77
   rdg_ready 0.23
   damage_seq rdg 3 (secondary 3 0) (interval 0.23)

Il Chu Ko Nu elite usa ``rdg 5 (secondary 3 0)`` (5 frecce). Questa modalità **non** richiede che la somma eguagli ``rdg``.

2.4 Intervallo
~~~~~~~~~~~~~~~


- `(interval 0.25)` — secondi tra i colpi
- Se `times > 1` e l'intervallo è omesso o `0`, predefinito 0,25 s

2.5 Consigli per raffiche a distanza
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Imposta ``rdg_projectile 1`` per il comportamento a proiettile (regole del terreno elevato, ecc.)
- Usa un ``rdg_cd`` più lungo di un arciere a colpo singolo: il DPS della raffica è più alto ma ogni ciclo rispetta comunque il ``rdg`` totale

Esempio (unità integrata):

.. code-block:: text

   def repeating_crossbowman
   class soldier
   rdg 6
   rdg_cd 2.5
   rdg_range 4
   rdg_projectile 1
   damage_seq rdg 3 (interval 0.25)



----


3. Suoni (``style.txt``)
-----------------------------


Ogni colpo attiva ``launch_rdg`` o ``launch_mdg``. Elenca più ID sonori così i colpi possono variare:

.. code-block:: text

   def repeating_crossbowman
   is_a archer
   launch_rdg 1042 1042 1042


I suoni di colpo / mancato (``rdg_hit``, ``rdg_missed``, …) suonano ancora per ogni tiraggio di colpo riuscito come di consueto.


----


4. Esempio integrato: ``repeating_crossbowman``
----------------------------------------------------



.. list-table::
   :header-rows: 1

   * - Voce
     - Valore
   * - Posizione
     - ``res/rules.txt``
   * - Potenziamento
     - ``archer`` → ``repeating_crossbowman`` (``can_upgrade_to``)
   * - Voce (ZH)
     - 诸葛弩手 (``tts.txt`` id 5082)
   * - Statistiche
     - 3×2 danno a distanza per ciclo, ricarica 2,5 s, portata 4




----


5. Errori comuni
-----------------



.. list-table::
   :header-rows: 1

   * - Problema
     - Causa / correzione
   * - ``damage_seq`` ignorato
     - ``mdg`` / ``rdg`` di base non definito, oppure somma dei segmenti ≠ base (suddivisione manuale)
   * - Intervallo sbagliato
     - Prima di 1.4.3.6 l'intervallo era ignorato (corretto); controlla la versione del gioco
   * - Danno frazionario + `(damage …)` manuale
     - Usa invece la suddivisione automatica
   * - Più di 6 colpi
     - Il motore limita a 6 per attacco
   * - Un solo suono di lancio
     - Atteso per unità non a raffica; le unità a raffica richiedono gestione per colpo (1.4.3.6+)




----


6. File correlati e test
-------------------------



.. list-table::
   :header-rows: 1

   * - File
     - Ruolo
   * - ``soundrts/definitions.py``
     - Analizza ``damage_seq`` nelle regole
   * - ``soundrts/combat/damage_effects.py``
     - Pianifica i colpi della raffica e i suoni di lancio
   * - ``soundrts/combat/attack_action.py``
     - Preparazione dell'attacco / tempo di ricarica
   * - ``soundrts/tests/test_damage_seq_burst.py``
     - Test di parsing e regressione



Esegui i test:

.. code-block:: bash

   python -m pytest soundrts/tests/test_damage_seq_burst.py -q
