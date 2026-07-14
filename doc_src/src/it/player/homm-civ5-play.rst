Guida al gioco in stile Heroes e Civ 5
======================================


A partire da SoundRTS 1.4.3.4, le mappe casuali (RMG) introducono sulla struttura RTS classica obiettivi di mappa, punti di interesse (POI) e diverse condizioni di vittoria ispirati a *Heroes of Might and Magic* (HoMM) e *Civilization 5* (Civ5). Questo documento spiega il confronto di design, le operazioni del giocatore e i metodi di estensione per mod/sviluppatori.


Per le istruzioni generali su menu mappe casuali, seed e codici di condivisione vedi `Guida alle mappe casuali <random-map-play.htm>`_.


----


1. Idea di design: cosa si può giocare in un RTS
-----------------------------------------------


SoundRTS resta strategia in tempo reale: selezioni unità, dai ordini, raccogli, produci truppe, combatti. Gli elementi HoMM / Civ5 si esprimono soprattutto nella generazione della mappa e nelle condizioni di vittoria a trigger, non in un sistema a turni completo o in un albero tecnologico.


.. list-table::
   :header-rows: 1

   * - Fonte di ispirazione
     - Corrispondenza in SoundRTS
     - Dove è implementato
   * - Esplorazione mappa HoMM, ricompense delle rovine
     - Invia unità in una casella → annuncio «rovina scoperta» → ottieni oro/legno
     - ``ancient_ruin`` + trigger ``has_entered``
   * - Tane di creature neutrali HoMM / avamposti catturabili
     - Elimina le guardie → occupa la caserma con un’unità ``can_capture 1`` (o attacca fino alla soglia)
     - ``captured_barracks`` + ``capture_hp_threshold`` + ``can_capture`` dell’unità
   * - Guardie centrali HoMM, mappe simmetriche
     - Al centro della mappa (e nei punti specchio) guardie ostili scalate per intensità
     - ``MONSTER_PRESETS`` + ``\_append_creep``
   * - Più modi di vincere Civ5
     - Quattro modalità di vittoria RMG: conquista / economia / esplorazione / sopravvivenza
     - `RandomMapConfig.victory_mode`
   * - Esplorazione completa e vittoria risorse Civ5
     - Modalità esplorazione: scopri tutte le rovine; modalità economia: raccolta cumulativa al traguardo
     - ``\_victory_mode_trigger_lines``
   * - Sopravvivenza e pressione temporale Civ5
     - Modalità sopravvivenza: resisti fino al conto alla rovescia e conserva la base principale (``personal_victory``)
     - ``timer`` + `(personal_victory)`
   * - Casse / beni di lusso Civ5
     - Opzione «tesoro»: oggetti raccoglibili o miniere extra posti in modo simmetrico
     - ``\_append_treasure``
   * - Missioni secondarie stile città-stato Civ5 (campagne)
     - Consegna oggetti a NPC in cambio di risorse (non RMG, script di campagna)
     - Es.: `res/single/The Legend of Raynor/`



Non implementato, solo direzione futura (l’RMG attuale non include):

- Upgrade eroi, alberi abilità, sistema mana (nucleo HoMM)
- Albero tecnologico, cultura, punti diplomazia (nucleo Civ5)
- Espansione città, resa delle caselle, carte politiche


----


2. Guida per i giocatori
------------------------


2.1 Come avviare
~~~~~~~~~~~~~~~~


1. Menu principale → Inizia partita → Mappa casuale
2. Configura passo passo dal menu, oppure in Modello mappa → Importa codice di condivisione incolla la configurazione completa (supporta Ctrl+V)
3. Nel passo Modalità di vittoria scegli lo stile di gioco (predefinito Conquista)
4. Conferma il Trattato di pace e genera la mappa

In modalità Esplorazione, dopo aver cliccato «Inizia» per entrare in partita, viene prima riprodotto il briefing della missione del seed (briefing + una frase variante casuale + obiettivo di esplorazione), poi inizia la gestione. Il contenuto del briefing dipende dal seed della mappa; lo stesso codice di condivisione è riproducibile.

Online: nella creazione stanza scegli Mappa casuale nell’elenco mappe; l’host genera all’avvio con lo stesso seed; i client non annunciano automaticamente il codice di condivisione, va scambiato in anticipo.

2.2 Quattro modalità di vittoria
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modalità
     - ID voce
     - Condizione di vittoria
     - Condizione di sconfitta (uguale alle altre modalità)
   * - Conquista
     - 5426
     - Elimina tutti i giocatori nemici (non serve ripulire i mostri centrali)
     - Perdi tutti gli edifici ``provides_survival``
   * - Economia
     - 5427
     - Raccolta cumulativa fino all’obiettivo di oro (escluso lo stock iniziale; anche se speso conta)
     - Come sopra
   * - Esplorazione
     - 5428
     - Visita di persona ogni antica rovina
     - Come sopra
   * - Sopravvivenza
     - 5429
     - Resisti fino alla fine del tempo e conserva la base principale
     - Come sopra



Anteprima configurazione: la modalità economia annuncia anche l’obiettivo oro concreto (ad es. «economia…3000 oro»).

Obiettivo oro modalità economia (solo ``resource1``, cioè oro):


.. list-table::
   :header-rows: 1

   * - Modello mappa
     - Obiettivo
   * - Veloce
     - 2000
   * - Standard
     - 3000
   * - Macro
     - 5000
   * - Corridoi
     - 2500


Durata modalità sopravvivenza:


.. list-table::
   :header-rows: 1

   * - Modello mappa
     - Durata
   * - Veloce
     - 10 minuti
   * - Standard / Macro / Corridoi
     - 15 minuti




Nota: in modalità esplorazione, economia e sopravvivenza non si vince automaticamente «eliminando tutti i nemici» (è stato rimosso `(no_enemy_player_left) (victory)`); puoi comunque attaccare per indebolire gli avversari. Perdere la base principale (municipio e altri edifici ``provides_survival 1``) fa comunque perdere.

2.3 Punti di interesse della mappa (POI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Tutte le mappe RMG (purché ``rules.txt`` definisca i tipi di unità corrispondenti) generano i seguenti POI, indipendentemente dalla modalità di vittoria:

Antiche rovine (``ancient_ruin``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Effetto: si attiva la prima volta che una tua unità entra in quella casella (non serve attaccare l’edificio)
- Prima ricompensa: annuncio Rovine scoperte (5433) e risorse
- Modello veloce: 300 oro + 150 legno
- Altri modelli: 500 oro + 250 legno
- Secondo atto (casella adiacente): dopo la scoperta viene suggerito Un suono metallico dietro il muro di pietra, controlla le caselle adiacenti (5490). Se esiste una casella adiacente utilizzabile, inviando unità lì ottieni Un altro bottino nelle profondità (5491) e risorse extra (circa il 50% del primo atto: veloce +150 oro / +75 legno, altri +250 oro / +125 legno). Se la casella adiacente non è disponibile (bordo, punto di spawn, ecc.) il secondo atto viene saltato.
- Annuncio progresso esplorazione (solo modalità vittoria esplorazione): dopo la scoperta Rovine non ancora scoperte: N oppure Resta solo l’ultima rovina (5492 / 5493).
- Vittoria esplorazione: devi visitare di persona ogni rovina (in 2v2 conta l’unione di ciò che hanno visitato i compagni). Le rovine già esplorate da nemici o avversari non contano per il tuo progresso, ma puoi entrarci dopo e completare la scoperta; la ricompensa risorse della prima visita globale a una rovina viene data una sola volta (chiunque arrivi per primo)
- Quantità (poste a coppie simmetriche; i punti di attivazione reali sono 2× le coppie):
- Mappa piccola: 1 coppia (modalità esplorazione +1 coppia)
- Mappa media / grande: 2 coppie (modalità esplorazione +1 coppia)

Caserme catturabili (``captured_barracks``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Guardie: sulla casella 2 fanti + 1 arciere (computer ostile, non neutral)
- Occupazione: dopo aver eliminato le guardie, fai clic destro sulla caserma con un’unità ``can_capture 1`` (o attacca fino alla soglia di cattura); se il bersaglio ha ``capture_hp_threshold`` 100, l’occupazione avviene all’arrivo senza danni. Le unità con ``can_capture 0`` attaccano solo normalmente e non usano l’ordine di occupazione predefinito
- Dopo l’occupazione: annuncio Caserma occupata (5434); puoi addestrare fanti (limite 5) e arcieri (limite 3)
- Prima dell’occupazione: circa ogni 5–10 minuti arrivano 2 fanti di rinforzo (finché non è occupata)
- Quantità: mappa piccola 1 coppia; media / grande 2 coppie; modalità esplorazione +1 coppia extra

Guardie centrali (intensità mostri)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


La voce di menu Intensità mostri controlla la scala delle guardie al centro della mappa (zona pericolosa centrale in stile HoMM):


.. list-table::
   :header-rows: 1

   * - Intensità
     - Guardie
   * - Debole
     - 2 fanti
   * - Media
     - 4 fanti + 2 arcieri
   * - Forte
     - 6 fanti + 4 arcieri + 1 cavaliere



Le guardie attaccano attivamente i giocatori che entrano nel raggio; i modelli veloce / corridoi regolano leggermente i numeri tramite ``creep_multiplier``.

Tesoro (opzionale)
^^^^^^^^^^^^^^^^^^


La voce di menu Tesoro è Nessuno / Poco / Molto:

- Poco: 1 miniera d’oro extra simmetrica (circa 500)
- Molto: 2 punti; circa 45% probabilità di oggetto raccoglibile (``class item``), circa 35% frutteto, resto miniera d’oro (circa 900)

Serve che l’attuale ``rules.txt`` definisca oggetti raccoglibili ``class item``.

2.4 Coordinate e trucchi di esplorazione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


- Le coordinate delle caselle in mappa e menu sono a base 1 (angolo in basso a sinistra `1,1`)
- Per esplorare le rovine basta spostare l’unità nella casella della rovina; non serve selezionarla né attaccarla
- Dopo essere «scoperte» le rovine non scompaiono; la ricompensa viene data una sola volta
- Premi F5 / F6 per riascoltare messaggi storici come «mappa generata, seed, codice di condivisione»

2.5 Campo modalità di vittoria nel codice di condivisione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Il codice di condivisione completo ha 12 segmenti (incluso il prefisso ``RMG1``); l’11º è la modalità di vittoria:

.. code-block:: text

   RMG1:template:size:players:monsters:resources:terrain:teams:water:treasure:victory:seed


Abbreviazioni modalità di vittoria:


.. list-table::
   :header-rows: 1

   * - Abbreviazione
     - Modalità
   * - ``c``
     - conquista conquest
   * - ``e``
     - economia economic
   * - ``x``
     - esplorazione exploration
   * - ``s``
     - sopravvivenza survival



Esempio (corridoi, mappa piccola, 2 giocatori, esplorazione, tesoro alto, seed 6685):

.. code-block:: text

   RMG1:l:s:2:w:b:r:f:n:hi:x:6685


I vecchi codici a 10 segmenti (senza campo vittoria) importati usano Conquista per impostazione predefinita.


----


3. Definizioni di regole e dati (``res/rules.txt``)
--------------------------------------------------


Le definizioni delle unità POI sono verso la fine delle regole di base (commenti che indicano ispirazione HoMM / Civ5):

.. code-block:: text

   def ancient_ruin
   class building
   cost 0 0
   time_cost 0
   hp_max 200
   hp_regen 0
   capture_hp_threshold 0    ; 不可被占领，仅作地图标记
   provides_survival 0
   is_buildable_anywhere 0
   sight_range 1
   
   def captured_barracks
   class building
   cost 0 0
   time_cost 0
   hp_max 500
   hp_regen 0.1
   capture_hp_threshold 100  ; 血量 ≤100% 时可被夺取（一次攻击即可）
   provides_survival 0
   is_buildable_anywhere 0
   can_train footman 5 archer 3
   population_provided 0


Spiegazione dei campi chiave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Campo
     - Rovine
     - Caserma
   * - ``capture_hp_threshold``
     - ``0`` = non occupabile
     - `100` = catturabile (occupazione a contatto)
   * - ``can_capture``
     - — (scritto sull’unità attaccante)
     - Predefinito `1`; `0` = clic destro/IA di quell’unità non occupa per impostazione predefinita
   * - ``provides_survival``
     - ``0`` = la perdita non influisce sul giudizio «hai ancora edifici»
     - Come a sinistra
   * - ``can_train``
     - Nessuno
     - Unità producibili dopo l’occupazione e relativi limiti
   * - ``sight_range 1``
     - Vista bassa; il motore può registrare un INFO su ``sight_range 1``, ignorabile
     - —



Se una mod elimina o rinomina questi ``type_name``, l’RMG salta la generazione del POI corrispondente tramite ``\_rules_has_type()`` senza errori.


----


4. Generatore di mappe casuali (sviluppatori)
--------------------------------------------


Sorgente centrale: ``soundrts/randommap.py``  
Menu: ``soundrts/randommap_menu.py``  
Test: ``soundrts/tests/test_randommap.py``

4.1 Panoramica del flusso di generazione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   RandomMapConfig
       → generate_definition() / _generate_grid_definition() / _generate_lanes_definition()
           → 地形、资源、水域、宝箱
           → _append_hunting（野生动物）
           → 玩家出生块
           → _append_creep（中央守军）
           → _append_exploration_poi（遗迹 + has_entered 触发器）
           → _append_capturable_dwelling（兵营 + 增援/占领触发器）
           → _append_skirmish_triggers（胜利/失败）
       → 输出 .txt 地图字符串 → Map / World 正常加载


Le posizioni POI sono scelte a caso in modo simmetrico da ``\_symmetric_pairs()`` tra le caselle candidate che evitano spawn e spawn specchio, per garantire equità.

4.2 Modello di trigger per la generazione POI di esplorazione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


``\_append_exploration_poi()`` scrive per ogni rovina:

.. code-block:: text

   computer_only 0 0 neutral 8,2 1 ancient_ruin
   trigger players (has_entered 8,2) (if (not (rmg_ruin_discovered_by_self rmg_ruin_0)) (do (rmg_mark_ruin_discovered rmg_ruin_0) (if (not (map_flag rmg_ruin_0_reward)) (do (set_map_flag rmg_ruin_0_reward) (cut_scene 5433) (grant_resources 500 resource1 250 resource2))) (cut_scene 5490)))


- Le coordinate `8,2` sono a base 1; ``has_entered`` in ``triggers.py`` le converte in chiavi griglia a base 0
- Importante: su mappe strette come i corridoi, le coordinate a base 1 possono «collidere» con le chiavi griglia a base 0; il parsing dei trigger deve convertire prima a base 1, non cercare direttamente sulla griglia (altrimenti le rovine non si attivano)

4.3 Modello di trigger per caserme catturabili
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: text

   computer_only 0 0 8,3 1 captured_barracks 2 footman 1 archer
   trigger computerN (timer 5 5) (if (and (not (map_flag rmg_dwelling_8_3)) (unit_lost 8,3 1 captured_barracks)) (do (set_map_flag rmg_dwelling_8_3) (cut_scene 5434)))
   trigger computerN (timer 300 600) (if (and (not (map_flag rmg_dwelling_8_3)) (not (unit_lost 8,3 1 captured_barracks))) (add_units 8,3 2 footman))


- La caserma va su una casella ``computer_only`` ostile (con guardie), non ``neutral``, altrimenti le guardie non combattono attivamente
- Per l’occupazione usa `(unit_lost casella 1 captured_barracks)` (edificio catturato/sostituito); non usare la vecchia scrittura ``transfer_units player1``

4.4 Trigger delle modalità di vittoria
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modalità
     - Logica di generazione
   * - Economia
     - Ogni 60 secondi controlla ``(has_gathered obiettivo resource1)`` → `` (victory)`` (raccolta cumulativa, escluso lo stock iniziale)
   * - Sopravvivenza
     - ``(timer secondi) (if (not (no_building_left)) (personal_victory))`` (più giocatori possono vincere insieme)
   * - Esplorazione
     - Ogni 30 secondi controlla ``(rmg_all_ruins_discovered_by_allies rmg_ruin_0 …)`` → `` (victory)``
   * - Conquista
     - ``(no_enemy_player_left) (victory)`` (solo modalità conquista; conta solo i giocatori nemici)



Condizione di sconfitta comune (tutte le modalità):

.. code-block:: text

   trigger players (no_building_left) (defeat)
   trigger computers (no_unit_left) (defeat)


4.5 Passi consigliati per estendere i tipi di POI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Esempio: aggiungere un «santuario (shrine)»:

1. :strong:```rules.txt``: definisci ``def shrine`` (eredita ``building``, imposta ``capture_hp_threshold`` o puro marcatore)
2. :strong:```res/ui-zh/tts.txt`` / ``res/ui/tts.txt``: assegna nuovi ID voce (evita conflitti con il segmento RMG 5425–5441)
3. :strong:```msgparts.py``: aggiungi costanti `RMG_*`
4. :strong:```randommap.py``:

   - Aggiungi `_append_shrine_poi()`, sul modello di ``\_append_exploration_poi``
   - Chiamalo in `_generate_*_definition`
   - Se è legato alla vittoria esplorazione, restituisci l’elenco flag e passalo a ``\_victory_mode_trigger_lines``
5. :strong:```randommap_menu.py``: se serve una nuova voce di menu, estendi ``\_open_victory_menu`` o le opzioni del modello
6. ``\_SHARE_ABBR["victory_mode"]`` o nuovo campo`: aggiorna ``encode_share_code`` / ``decode_share_code``
7. Test: in ``test_randommap.py`` verifica che il testo generato contenga i trigger attesi

4.6 API trigger correlate
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Trigger
     - Uso
   * - ``(has_entered casella [tipo unità…])``
     - Unità del giocatore entra nella casella
   * - ``(has_gathered quantità resource1)``
     - Vittoria economia: raccolta cumulativa (escluso lo stock iniziale)
   * - ``(has_resources quantità resource1)``
     - Controlla lo stock risorse corrente (non vittoria economia RMG)
   * - ``(rmg_mark_ruin_discovered nome)``
     - Segna che il giocatore corrente ha scoperto quella rovina (progresso vittoria)
   * - ``(rmg_ruin_discovered_by_self nome)``
     - Condizione: il giocatore corrente ha già scoperto quella rovina?
   * - ``(rmg_all_ruins_discovered_by_allies nome…)``
     - Vittoria esplorazione: la fazione ha trovato tutte le rovine?
   * - ``(grant_resources 500 resource1 200 resource2)``
     - Ricompensa rovine
   * - `(set_map_flag nome)` / `(map_flag nome)`
     - Marcatore interno alla partita
   * - ``(cut_scene ID voce)``
     - Annuncia scoperta/occupazione
   * - ``(unit_lost casella indice tipo)``
     - Caserma occupata
   * - ``(add_units casella quantità tipo)``
     - Rinforzi delle guardie
   * - ``(timer intervallo [volte])``
     - Controllo periodico / conto alla rovescia sopravvivenza
   * - ``(personal_victory)``
     - Modalità sopravvivenza: vittoria personale senza eliminare gli altri sopravvissuti



Implementazione in ``soundrts/worldplayerbase/triggers.py``.


----


5. Voce e testi UI
------------------



.. list-table::
   :header-rows: 1

   * - ID
     - Cinese
     - Uso
   * - 5425
     - 胜利模式
     - Titolo menu
   * - 5426
     - 征服，歼灭所有敌方玩家
     - Nome modalità
   * - 5427
     - 经济，累计采集达到目标
     - Nome modalità (l’anteprima può aggiungere l’importo oro)
   * - 5428
     - 探索，亲访每一处遗迹
     - Nome modalità
   * - 5429
     - 生存，坚守到时间结束
     - Nome modalità
   * - 5430
     - 亲访每一处古代遗迹
     - Riga obiettivo modalità esplorazione
   * - 5431
     - 古代遗迹
     - Nome unità/concetto (riservato)
   * - 5432
     - 可占领兵营
     - Nome unità/concetto (riservato)
   * - 5433
     - 遗迹已发现
     - cut_scene ingresso rovine
   * - 5434
     - 兵营已占领
     - cut_scene occupazione
   * - 5435
     - 累计采集达到
     - Riga obiettivo modalità economia (seguita da quantità e «oro»)
   * - 5436
     - 坚守
     - Riga obiettivo modalità sopravvivenza
   * - 5437
     - 分钟
     - Riga obiettivo modalità sopravvivenza
   * - 5451
     - 歼灭所有敌方玩家
     - Riga obiettivo modalità conquista
   * - 5452
     - 并保留主基地
     - Suffisso riga obiettivo modalità sopravvivenza



Esempi di riga ``objective`` sulla mappa:

.. code-block:: text

   objective 5430                    ; 探索
   objective 5435 3000 131           ; 经济：累计采集 3000 黄金
   objective 5436 15 5437 5452       ; 生存 15 分钟并保留主基地
   objective 5451                    ; 征服



----


6. Test e regressione
---------------------


``soundrts/tests/test_randommap.py`` copre:

- Modalità esplorazione genera ``ancient_ruin``, ``rmg_mark_ruin_discovered``, ``rmg_all_ruins_discovered_by_allies``, e non ha la vittoria conquista `(no_enemy_player_left) (victory)`
- Modalità economia usa ``has_gathered``; obiettivo sopravvivenza include `5452`; obiettivo conquista è `5451`
- Anche economia / sopravvivenza senza vittoria automatica conquista
- Le caserme usano guardie ``computer_only``, non ``neutral``
- `captured_barracks.capture_hp_threshold == 100`
- Il codice di condivisione include il campo vittoria `:e:` / `:x:` ecc. con parsing andata e ritorno

Coordinate: in ``soundrts/tests/test_yield_on_defeat_and_campaign_flags.py``  
``test_has_entered_one_based_coords_not_confused_with_zero_based_grid_key`` previene la regressione del bug coordinate rovine sulle mappe a corridoi.


----


7. Limiti noti e avvertenze
---------------------------


1. IA modalità sopravvivenza: i computer invitati usano ancora lo ``res/ai.txt`` standard, senza script dedicato «assedia il giocatore in sopravvivenza»
2. Slot ``computerN``: con molti POI possono essere assegnati ID come ``computer11``; se i giocatori computer reali non bastano compare l’avviso «unknown player» (non influisce sui POI dei giocatori umani)
3. Esplorazione ≠ vittoria di guerra: eliminare tutti i nemici non fa vincere; la fazione deve trovare tutte le rovine (in FFA conta solo la propria scoperta)
4. Vittoria economia: quantità cumulativa raccolta di ``resource1`` (oro) (``has_gathered``, esclusi stock iniziale e ``grant_resources`` delle rovine), senza legno; dopo il traguardo la vittoria scatta entro circa 60 secondi
5. Vittoria esplorazione: dopo aver trovato tutte le rovine la vittoria scatta entro circa 30 secondi
6. Compatibilità mod: con nomi risorse non standard, aggiorna anche ``resource1`` / ``resource2`` in ``\_economic_goal`` e ``grant_resources``
7. Esplorazione + niente ``ancient_ruin``: se la mod non definisce il tipo rovina non si generano POI e la modalità esplorazione non può vincere
8. Elementi Civ5 in campagna: mercanti città-stato, missioni di consegna ecc. vedi mappe di campagna e `Portare oggetti e consegne di trama <brought-items.htm>`_, indipendenti dall’RMG


----


8. Indice file correlati
------------------------



.. list-table::
   :header-rows: 1

   * - Contenuto
     - Percorso
   * - Giocatore: menu mappe casuali
     - [Guida alle mappe casuali](random-map-play.htm)
   * - Regole: unità POI
     - ``res/rules.txt`` (``ancient_ruin``, ``captured_barracks``)
   * - Generatore
     - ``soundrts/randommap.py``
   * - Menu
     - ``soundrts/randommap_menu.py``
   * - Trigger
     - ``soundrts/worldplayerbase/triggers.py``
   * - Logica di cattura
     - ``soundrts/combat/damage_effects.py`` (``capture_hp_threshold``); ordine di occupazione predefinito ``can_capture`` → ``worldunit/world_order.py``
   * - Costanti voce
     - ``soundrts/msgparts.py``
   * - Documentazione HTML in gioco
     - ``doc/zh/mod/randommap.htm``
   * - Mappe casuali in inglese
     - [../../en/player/random-map.md](../../en/player/random-map.htm)




----


9. Confronto rapido: quale stile vuoi?
--------------------------------------



.. list-table::
   :header-rows: 1

   * - Voglio…
     - Impostazioni consigliate
   * - Esplorare e prendere ricompense in stile HoMM
     - Modalità vittoria Esplorazione, Tesoro Molto, Mostri Media
   * - Rubare caserme e ampliare l’esercito in stile HoMM
     - Qualsiasi modalità di vittoria; cerca prima le caserme catturabili
   * - Vincere accumulando economia in stile Civ5
     - Modalità vittoria Economia, modello Macro, risorse Concentrate
   * - Resistere fino alla fine in stile Civ5
     - Modalità vittoria Sopravvivenza, modello Veloce (10 minuti)
   * - Annientamento RTS classico
     - Modalità vittoria Conquista (predefinita)




----


*Versione documento: corrisponde all’implementazione mappe casuali SoundRTS 1.4.2.x; se i campi del codice di condivisione o le quantità POI cambiano, fanno fede ``soundrts/randommap.py`` e ``test_randommap.py``.*
