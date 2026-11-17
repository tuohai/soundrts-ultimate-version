# Miglioramenti campagna e campagna cooperativa (1.4.3.9)

Questa guida descrive le campagne in singolo e cooperative in stile Age of Empires Definitive Edition di SoundRTS: browser missioni, cinque livelli di difficoltà, cooperativo sulle missioni di trama, scalatura dei nemici e sincronizzazione sicura in lockstep. Per giocatori, autori di campagne e modder.

Versione cinese: `../../zh/player/战役与合作战役改进说明 <../../zh/player/战役与合作战役改进说明.htm>`_.


----


1. Panoramica
-------------


Prima
~~~~~


- Singolo giocatore: solo elenco capitoli; niente difficoltà, sinossi né riprova in caso di sconfitta.
- Cooperativo (dal 1.4.2.2): più umani sulla stessa mappa di campagna, ma più vicino a uno scontro che al cooperativo AoE DE (niente livelli di difficoltà, slot giocatore, partner IA alleati né semantica di trama condivisa).

Dopo (1.4.3.9)
~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Area
     - Singolo giocatore
     - Cooperativo
   * - Menu
     - Browser missioni: sinossi, difficoltà, completata/bloccata
     - Server: campagna → capitolo → difficoltà → velocità
   * - Difficoltà
     - Cinque livelli, salvati in ``user/campaigns.ini``
     - Stessi + scalatura extra in base al numero di giocatori umani
   * - Scalatura nemici
     - PF / danni in uscita dei nemici in %
     - Il server calcola una volta, trasmette a tutti i client / replay
   * - Trama
     - ``intro``, vittoria/sconfitta guidate dagli obiettivi
     - ``intro`` condiviso, cutscene, obiettivi F9; non “distruggi tutti i nemici”
   * - Slot
     - Un umano
     - Uno slot per umano; gli slot vuoti sono riempiti da IA alleate



Codice centrale: `soundrts/coop_difficulty.py <../../../soundrts/coop_difficulty.py>`_, ``soundrts/campaign.py <../../../soundrts/campaign.py>`_, ``soundrts/clientservermenu.py <../../../soundrts/clientservermenu.py>`_, ```soundrts/serverroom.py``.


----


2. Campagna in singolo
----------------------


2.1 Browser missioni
~~~~~~~~~~~~~~~~~~~~


Dopo aver scelto una campagna dal menu principale:

1. Sinossi della campagna (opzionale) — solo se ``campaign.txt`` definisce ``synopsis``; riproduce TTS poi torna all’elenco.
2. Difficoltà: … — livello corrente; sottomenu per scegliere Facile / Standard / Moderata / Difficile / Estrema.
3. Continua — scorciatoia all’ultimo capitolo sbloccato quando applicabile.
4. Elenco capitoli con stato:

   - Completato — riproducibile, titolo completo mostrato.
   - Corrente — giocabile, titolo completo.
   - Bloccato — solo numero + “bloccato”; non selezionabile (niente spoiler del titolo).

5. Indietro.

I progressi sono memorizzati in `user/campaigns.ini <../../../soundrts/paths.py>`_ (``chapter`` + ``difficulty`` per id campagna).

.. note:: **Che cosa indica il segnalibro (da 1.5.2.2)**

   Il ``chapter`` del segnalibro è l'**indice del prossimo capitolo giocabile
   nella lista dei capitoli**:

   - indice < segnalibro -> completato
   - indice == segnalibro -> attuale
   - indice > segnalibro -> bloccato

   I capitoli di cinempresa (``cut_scene_chapter``, come il prologo ``0.txt``)
   **non occupano una posizione giocabile**: non rubano mai lo slot "attuale" e
   possono essere scelti nel menu per essere riprodotti.

2.1.1 Crescita dell’eroe e trasferimento tra missioni (guidato dalle regole)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Configura qualsiasi eroe in :strong:```rules.txt`` con ``campaign_carryover 1`` (non specifico di Raynor).


.. list-table::
   :header-rows: 1

   * - Campo
     - Predefinito
     - Effetto
   * - ``campaign_carryover_id``
     - nome def
     - Chiavi di salvataggio `hero_<id>_xp`, ecc.
   * - ``campaign_carryover_stats``
     - ``1``
     - Livello + XP
   * - ``campaign_carryover_inventory``
     - ``1``
     - Zaino



- Salvato solo in caso di vittoria; il capitolo successivo ripristina. ``hero_min_level`` in ``campaign.txt`` è opzionale.
- Il cooperativo non persiste gli eroi.
- Separazione: ``campaign_carryover_inventory 0`` (solo statistiche) o ``campaign_carryover_stats 0`` (solo inventario).

Guida per autori: `../mod/campaign-hero-carryover <../mod/campaign-hero-carryover.htm>`_.

2.2 Sinossi in ``campaign.txt``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   title 7747
   synopsis 7751


``7751`` è un id voce in ``ui/tts.txt`` / ``ui-zh/tts.txt``. Ometti ``synopsis`` per nascondere la voce di menu.

Esempio: ``res/single/The Legend of Raynor/campaign.txt``.

2.3 Difficoltà e scalatura dei nemici
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- La difficoltà persiste in ``campaigns.ini``; predefinito Standard.
- `MissionChapter.run` imposta ``enemy_hp_factor`` / ``enemy_damage_factor`` sulla sessione.
- Solo unità nemiche (non umane, non neutrali): PF alla creazione, danni in uscita al colpo.
- Standard + solo = 100% / 100% (baseline invariata).
- Il singolo non applica mai il moltiplicatore per numero di giocatori (conta sempre come 1 umano).

Livelli base (PF / danni):


.. list-table::
   :header-rows: 1

   * - Livello
     - PF nemici
     - Danni nemici
   * - Facile
     - 70%
     - 70%
   * - Standard
     - 100%
     - 100%
   * - Moderata
     - 120%
     - 115%
   * - Difficile
     - 145%
     - 135%
   * - Estrema
     - 180%
     - 165%



2.4 Vittoria e sconfitta
~~~~~~~~~~~~~~~~~~~~~~~~


- Vittoria: voce Missione successiva sbloccata; menu Continua (capitolo successivo) o Esci; il segnalibro avanza.
- Sconfitta: menu Riprova questa missione o Esci.


----


3. Campagna cooperativa
-----------------------


3.1 Flusso del giocatore
~~~~~~~~~~~~~~~~~~~~~~~~


1. Lobby server → Campagna cooperativa → campagna (solo se ``coop_campaign 1`` in ``campaign.txt``) → capitolo → difficoltà → velocità → crea stanza.
2. Nessun passo trattato (``treaty`` fisso a 0).
3. Gli altri si uniscono; l’host avvia.
4. Tutti ricevono l’intro del capitolo, poi i trigger della mappa guidano vittoria/sconfitta.
5. Qualsiasi umano che completa gli obiettivi primari vince per la squadra; il segnalibro dell’host avanza quando l’host vince e il segnalibro è uguale al capitolo corrente.

3.2 Tabella campagna e mappe missione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Menu cooperativo: guidato da ``coop_campaign`` / ``coop_intro`` / ``coop_missions`` in ciascun ``campaign.txt`` (nessun nome campagna hardcoded nel motore).
- Caricamento mappa: cooperativo e singolo condividono ``N.txt``; il server carica tramite ``ensure_chapter_map`` — niente ``N.coop.txt``.
- Autorialità: `coop-campaign.md <../mod/coop-campaign.htm>`_ e §4 sotto.

3.3 Missione di trama, non scontro
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Vittoria/sconfitta da ``add_objective``, ``objective_complete``, ``defeat``, ecc. — non dallo sterminio di tutti i giocatori IA.
- `world.is_campaign = True`: musica di campagna, computer trigger annunciati come “NPC”, niente “giocatore sconfitto/uscito” per le IA di script.
- ``cut_scene`` e obiettivi trasmessi al proprietario del trigger e a tutti gli alleati.
- `MultiplayerGame.pre_run` riproduce `world.intro` per il cooperativo.

3.4 Slot giocatore e partner IA alleati
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Mappa di esempio: ``res/single/The Legend of Raynor/1.txt``.

.. code-block:: text

   nb_players_min 1
   nb_players_max 2
   player_start 1 a1 raynor footman footman
   player_start 2 h8 raynor2 footman archer
   computer_only e5 ...



.. list-table::
   :header-rows: 1

   * - Campo
     - Significato
   * - ``nb_players_max``
     - Numero di slot cooperativi
   * - ``nb_players_min 1``
     - Solo + partner IA consentiti
   * - ``player_start N …``
     - Casella di spawn e unità per lo slot N
   * - ``computer_only``
     - Nemici della missione (alleanza `"ai"` contro umani sull’alleanza 1)



``Game._fill_coop_ai_partners`` riempie gli slot vuoti con IA alleate aggressive; tutti gli umani + partner partono sull’alleanza 1.  
``player1``, ``player2``, … nei trigger corrispondono agli umani in ordine di ingresso; gli slot solo IA di solito non sono bersaglio dei trigger di trama.

3.5 Difficoltà e numero di giocatori
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Oltre al livello base:

.. code-block:: text

   count multiplier = 100 + (humans - 1) × 20   (solo = 100%)
   final hp%        = base hp% × multiplier // 100
   final damage%    = base damage% × multiplier // 100


Esempio: Difficile + 3 umani → base 145/135, moltiplicatore 140 → ~203% PF / 189% danni.

Il server invia ``coop_difficulty`` prima di ``start_game``; solo aritmetica intera. La riga seed del replay può aggiungere ``hp% damage%`` (i vecchi replay usano 100 per impostazione predefinita).

3.6 Nomi dei luoghi e risorse di campagna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Il nome logico della mappa ``CampaignName/chapter`` attiva `apply_campaign_from_map_name <../../../soundrts/lib/resource.py>``_ così ``rules.txt`` e il ``tts.txt`` di campagna si caricano sui client; nomi di casella come ``loc_ch02_*`` si risolvono tramite TTS invece di leggere le chiavi grezze.

3.7 ``campaign_flag`` tra capitoli
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Il cooperativo non imposta ``world.campaign``, quindi ``campaign_flag`` senza oggetto campagna locale restituisce False (no-op deterministico). ``set_map_flag`` / ``map_flag`` in missione funzionano ancora sullo stato mondo sincronizzato.


----


4. Autorialità delle mappe
--------------------------


4.1 Tabella campagna (``campaign.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Dichiara il cooperativo come in Age of Empires in :strong:```campaign.txt``. Non distribuire file paralleli ``N.coop.txt``;
singolo e cooperativo caricano la stessa mappa missione ``N.txt``.

.. code-block:: text

   title 7747
   synopsis 7751
   coop_campaign 1
   coop_intro 0
   coop_missions 1-29



.. list-table::
   :header-rows: 1

   * - Campo
     - Significato
   * - ``coop_campaign``
     - ``1`` — mostra nel menu Campagna cooperativa del server
   * - ``coop_intro``
     - Numeri di capitolo cutscene nel flusso cooperativo (ad es. prologo `0`)
   * - ``coop_missions``
     - Capitoli missione giocabili in cooperativo (`1-29`, elenchi separati da spazio, ecc.)



4.2 Campi mappa cooperativa (``N.txt``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


1. ``nb_players_min 1`` / ``nb_players_max 2`` e più blocchi ``player`` (o ``player_start``).
2. Duplica i trigger chiave per ogni giocatore cooperativo dove serve (``add_objective``, ``objective_complete``), oppure guidali globalmente via ``player1`` se condivisi.
3. Opzionale `(alliance 1)` per gli umani cooperativi; nemici via ``computer_only``.
4. Opzionale ``intro`` / ``cut_scene``; bilanciamento via difficoltà del motore — niente hack manuali alle statistiche.

Il singolo registra ancora un umano e usa solo il primo spawn; gli slot cooperativi vuoti non sono riempiti dall’IA in solo.

4.3 Correzioni correlate (1.4.3.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Mappe multi-computer: completare gli obiettivi fa vincere senza dover uccidere ogni IA di script (`Player.victory` itera uno snapshot).
- F12 non seleziona bersagli in campagna; i computer trigger sono annunciati come “NPC”.


----


5. Riepilogo della migrazione
-----------------------------



.. list-table::
   :header-rows: 1

   * - Vecchio
     - Nuovo
   * - Solo elenco capitoli
     - Sinossi + difficoltà + completata/bloccata + riprova
   * - Cooperativo senza difficoltà / passo trattato
     - Cinque livelli + scalatura per conteggio; niente trattato
   * - Cooperativo come scontro
     - Intro/cutscene/obiettivi condivisi; partner IA
   * - ``N.coop.txt`` o rilevamento cooperativo basato su file
     - Flag ``campaign.txt`` + ``N.txt`` condiviso
   * - Chiavi `loc_*` grezze in cooperativo
     - Livello TTS di campagna, nomi localizzati
   * - Standard = baseline
     - Ancora 100%/100%; altri livelli secondo tabella




----


6. Test
-------


.. code-block:: bash

   python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429b_campaign_browser_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
   python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
   python -m pytest soundrts/tests/test_coop_campaign_place_names.py -q
   python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
   python -m pytest soundrts/tests/test_changelog_1428_campaign_victory_f12.py -q



----


7. Vedi anche
-------------



.. list-table::
   :header-rows: 1

   * - Doc
     - Argomento
   * - [progressive-campaign-objectives.md](progressive-campaign-objectives.htm)
     - ``register_objective``
   * - [campaign-northern-arc.htm](campaign-secret-letter-alliance.htm)
     - The Legend of Raynor cap. 24–27
   * - [coop-campaign.md](coop-campaign.htm)
     - Riferimento cooperativo breve
   * - ``mod/mapmaking.rst``
     - Sintassi missione




.. list-table::
   :header-rows: 1

   * - Sorgente
     - Ruolo
   * - ``soundrts/campaign.py``
     - Browser SP, metadati cooperativi (`coop_*`), segnalibri, difficoltà
   * - ``soundrts/coop_difficulty.py``
     - Tabella livelli e moltiplicatore per conteggio
   * - ``soundrts/clientservermenu.py``
     - Menu cooperativo, ``srv_coop_difficulty``
   * - ``soundrts/serverroom.py``
     - Partner IA, trasmissione difficoltà
   * - ``soundrts/game.py``
     - ``is_coop_campaign``, intro, aggiornamento segnalibro
   * - ``soundrts/worldunit/worldcreature.py``
     - Scalatura PF nemici
   * - ``soundrts/combat/damage_effects.py``
     - Scalatura danni nemici
   * - ``soundrts/lib/resource.py``
     - Stack risorse campagna, TTS luoghi
