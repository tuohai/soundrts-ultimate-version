Sistema achievement
===================



Guida giocatore (menu, progresso, cosa conta): `../player/achievements.htm <../player/achievements.htm>`_

Riferimento di implementazione.


Stato
-----



.. list-table::
   :header-rows: 1

   * - Fase
     - Stato
     - Riepilogo
   * - 1
     - Completata
     - Definizioni, salvataggio per mod, sblocco a fine partita, elenco achievement
   * - 2
     - Completata
     - Medaglie, carte, ranghi e titoli d’onore, armeria
   * - 3
     - Completata
     - Loadout pre-missione in TrainingGame, applicazione effetti, consumo cariche
   * - Schema D
     - Completata
     - Salvataggi per fazione (``achievements_per_faction``), selettore fazione nei menu
   * - Progresso meta
     - Completata
     - ``\_meta.json`` inter-fazione, condizioni aggregate, ``scope meta``



Codice chiave
-------------



.. list-table::
   :header-rows: 1

   * - File
     - Ruolo
   * - ``soundrts/achievements.py``
     - Caricamento, valutazione, ricompense, persistenza, annuncio
   * - ``soundrts/faction_progress.py``
     - Percorsi per fazione, matching fazione, selettore menu
   * - ``soundrts/meta_progress.py``
     - Salvataggio meta inter-fazione (``\_meta.json``), aggregazione snapshot
   * - ``soundrts/cards.py``
     - Definizioni carte
   * - ``soundrts/titles.py``
     - Scala ranghi + titoli d’onore
   * - ``soundrts/achievements_menu.py``
     - Hub: selettore fazione, elenco achievement, armeria, progresso meta
   * - ``soundrts/game.py``
     - `_say_achievements()` dopo `say_score()` (saltato in campagna)
   * - ``soundrts/lib/resource.py``
     - Carica achievement + carte + titoli insieme alle regole
   * - ``res/achievements.txt``
     - Achievement di base
   * - ``mods/\<mod\>/achievements.txt``
     - Append / override della mod



Percorsi di salvataggio
-----------------------



.. list-table::
   :header-rows: 1

   * - Percorso
     - Quando
   * - ``user/achievements/\<mod_key\>.json``
     - Predefinito (un salvataggio per mod)
   * - ``user/achievements/\<mod_key\>/\<faction\>.json``
     - ``achievements_per_faction 1``
   * - ``user/achievements/\<mod_key\>/\_meta.json``
     - Meta inter-fazione (``achievements_per_faction 1``)



Abilita la modalità per fazione nella ``rules.txt`` della mod:

.. code-block:: text

   def parameters
   achievements_enabled 1
   achievements_per_faction 1


- Le definizioni con tag fazione usano `faction <race_id>`; ometti ``faction`` sulle carte globali (condivise tra i rami).
- Il menu principale Achievement sceglie prima una fazione (mod multi-fazione); indietro da elenco/armeria torna al selettore fazione.
- La voce di progresso inter-fazione apre l’elenco achievement meta + armeria meta (rami attivi, traguardi mappa, onori meta).

Campagna: ``game.is_campaign_session()`` salta punteggio, achievement, medaglie, promozione di rango e registrazione statistiche.

Multigiocatore: ``game_type_name == "multiplayer"`` salta achievement, medaglie, promozione di rango e progresso carte; la voce del punteggio e le statistiche di tempo di gioco restano attive (vedi `Sistema di valutazione punteggio <score-grading-system.htm>`_).

Estratto di definizione
-----------------------


.. code-block:: text

   def grade_s
   title 5300
   condition grade S
   once_per map_ai
   reward medal 50
   reward card card_mixed_army


Achievement meta (``scope meta``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   def meta_three_branches
   scope meta
   title 79950
   condition factions_unlocked_at_least 3 1
   once
   reward title honor_meta_novice


Condizioni aggregate (leggono tutti i salvataggi di fazione):


.. list-table::
   :header-rows: 1

   * - Condizione
     - Significato
   * - ``factions_unlocked_at_least N M``
     - Almeno N rami con ciascuno ≥M achievement sbloccati
   * - ``factions_medals_at_least N M``
     - Almeno N rami con ≥M medaglie
   * - ``factions_honors_at_least N M``
     - Almeno N rami con ciascuno ≥M titoli d’onore
   * - ``factions_achievement_id_contains_at_least N \<substr\>``
     - Almeno N rami hanno sbloccato un achievement il cui id contiene `<substr>` (es. ``\_map_``)



Le ricompense meta sono memorizzate in ``\_meta.json``. Le medaglie meta non contano per i ranghi per fazione. I titoli d’onore meta non hanno campo ``faction``.

Vedi l’elenco completo delle direttive (``condition``, ``reward``, ``repeat_medal``, ``cards.txt``, ``titles.txt``) nella documentazione di riferimento.

Completamento ripetuto: se la stessa chiave ``once`` è già stata assegnata, ``repeat_medal \<n\>`` concede solo medaglie (nessuna voce carta/onore/sblocco).

Normalizzazione difficoltà IA: i nomi degli script IA di fazioni personalizzate sono mappati a livelli canonici per i contatori cumulativi di sconfitta; le chiavi di salvataggio legacy migrano al caricamento.

Flusso runtime
--------------


.. code-block:: text

   Main menu → Achievements
     ├─ (multi-faction) pick faction → list / armory → back → pick faction again
     └─ (multi-faction) cross-faction progress → meta list / meta armory
   
   game.post_run()
     → say_score()              # skipped in campaign
     → _say_achievements()      # faction unlocks, then meta unlocks, rewards, rank-up
                                # skipped in campaign and multiplayer


Formato salvataggio (fazione o singola mod)
-------------------------------------------


.. code-block:: json

   {
     "unlocked": { "grade_s": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "grade_s|map:jl1|ai:beginner": true },
     "medals": 50,
     "honors": ["honor_nightmare_slayer"],
     "ai_defeats": { "beginner": 5 },
     "map_ai_defeats": { "pra1": { "beginner": 3 } },
     "cards": { "card_infantry": { "charges": 1, "total_earned": 1 } }
   }


Salvataggio meta (``\_meta.json``) — senza ``cards`` / ``ai_defeats`` / ``map_ai_defeats``:

.. code-block:: json

   {
     "unlocked": { "meta_three_branches": { "count": 1, "first_at": 0, "last_at": 0 } },
     "once_keys": { "meta_three_branches": true },
     "medals": 25,
     "honors": ["honor_meta_novice"]
   }


I salvataggi legacy senza campi vengono normalizzati al caricamento.

Fase 3 (completata)
-------------------


- Dopo Singolo giocatore → Avvia su mappa → Avvia, scegli fino a N carte (N = ``loadout_slots`` del rango)
- Gli effetti si applicano dopo il populate della mappa (immediati o dopo ``delay`` / ``delay_minutes``); una carica consumata per carta all’inizio partita
- Campi carta: ``spawn``, ``resource``, ``tech``; carte combo supportate; carte ritardate documentate in `Carte di loadout ritardate <delayed-card-loadout.htm>`_
- Gli spawn delle carte consumano popolazione
- Solo TrainingGame (skirmish contro IA); non campagna né multigiocatore
- Le carte possono richiedere ``min_rank`` in ``cards.txt``

Disattivazione nella mod
------------------------


.. code-block:: text

   def parameters
   achievements_enabled 0


Nasconde la voce Achievement del menu principale, salta sblocchi a fine partita, loadout e applicazione carte in partita; non carica ``achievements.txt`` / ``cards.txt`` / ``titles.txt``. I file di salvataggio restano se riattivi in seguito.

Esempio CrazyMod
----------------


``mods/crazyMod9beta10`` usa lo schema D + quattro livelli meta (``meta_three_branches`` … ``meta_ten_masters``) e traguardi mappa per fazione (``trad_map_pra1`` … ``delf_map_pra10``).

Test
----


.. code-block:: bash

   python -m pytest soundrts/tests/test_achievements.py -v
   python -m pytest soundrts/tests/test_faction_progress.py -v
   python -m pytest soundrts/tests/test_meta_progress.py -v
   python -m pytest soundrts/tests/test_achievements_menu_navigation.py -v
   python -m pytest soundrts/tests/test_campaign_no_score_or_achievements.py -v
   python -m pytest soundrts/tests/test_card_loadout.py -v
