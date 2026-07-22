Note di rilascio
================

.. contents::


1.4.5.8
--------

**Novità: occupazione astratta della casella (``space``)**

- La proprietà ``space`` (precision; ammessi decimali) indica quanto occupa l’unità sul proprio strato aria/terra/acqua. La capacità è ``square_width`` della mappa nelle stesse unità (es. ``square_width 12`` + ``space 1`` → al massimo 12; ``space 0.5`` → al massimo 24).
- Predefinito ``space 0`` = illimitato (legacy). La capacità è condivisa da tutte le fazioni; se la casella è piena, nessuno di quello strato può entrare o addestrare lì. Voce: ``not_enough_space`` (TTS 5338); etichetta TTS 5733.
- Vanilla: molte unità di terra (es. peasant, footman) usano ``space 1``.
- **Codice**: ``definitions.py``, ``worldentity.py``, ``worldroom.py``, ``worldunit/world_movement.py``, ``worldorders/production.py``, ``worldplayercomputer_water.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui*/tts.txt``.
- **Documentazione**: ``mod/modding.rst``, ``mod/mapmaking.rst``, manuali (tutte le lingue).
- **Test**: ``test_unit_square_space.py``, ``test_train_square_space.py``.

**Novità: conto alla rovescia di vittoria edificio (``victory_time``) e Meraviglia**

- Qualsiasi edificio completato con ``victory_time N`` (secondi) avvia un conto alla rovescia. Se il timer scade e l’edificio è ancora in piedi, vince il proprietario (e il campo di vittoria alleata). Distruggere l’edificio annulla il conto alla rovescia e lo annuncia.
- ``wonder`` (Meraviglia) in vanilla (Età Imperiale): edificio tardivo costoso; ``victory_time 300`` (5 minuti). Scorciatoia ``o``.
- Voci 5720–5722 (avvio / annullamento / rimanente); avvisi a 120/60/30/10 s e 5…1.
- **Codice**: ``building_victory.py``, ``worldunit/worldcreature.py``, ``world/world_core.py``, ``world/world_game.py``, ``definitions.py``, ``msgparts.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Documentazione**: ``mod/modding.rst`` (``victory_time``), manuali giocatore.
- **Test**: ``test_building_victory.py``.

**Novità: requisiti ``any_buildings`` per gruppo**

- ``requirements`` può usare ``any_buildings <n> <group>_buildings``: il giocatore deve possedere almeno ``<n>`` edifici distinti del gruppo (AND con altri nomi semplici sulla stessa riga).
- Appartenenza: edifici il cui ``requirements`` semplice elenca ``<chiave>`` (dopo aver tolto il suffisso ``_buildings``). Esempio: ``requirements castle_age`` entra in ``castle_age_buildings``.
- Vanilla: ``imperial_age`` e ``castle`` (keep→castle) usano ``any_buildings 2 castle_age_buildings``.
- Voce: style ``parameters.any`` / ``parameters.buildings_of`` (TTS 5730–5731).
- **Codice**: ``worldrequirements.py``, ``worldplayerbase/base.py``, ``worldphase.py``, ``worldplayercomputer.py``, ``clientgameorder.py``, ``attributes/display_interface.py``, ``definitions.py``, ``worldunit/worldcreature.py``; ``res/rules.txt``, ``res/ui/style.txt``, ``res/ui/tts.txt``, ``res/ui-zh/tts.txt``.
- **Documentazione**: ``mod/modding.rst`` (tutte le lingue).
- **Test**: ``test_any_buildings_requirements.py``.


1.4.5.7
--------

**Correzione: unità bloccate ad attaccare edifici senza minaccia invece dei combattenti**

- **Sintomo**: mentre le unità demoliscono una fattoria, municipio o edificio simile, i combattenti nemici possono avvicinarsi e ucciderle; gli attaccanti continuano a colpire l’edificio invece di cambiare bersaglio.
- **Causa**: in 1.4 si saltava la riselezione del bersaglio durante l’ingaggio (prestazioni). Gli edifici contano come nemici vivi, quindi l’ingaggio restava sulle fattorie. 1.3.8.1 restava solo su bersagli con ``menace > 0`` e riselezionava se il bersaglio corrente non aveva minaccia.
- **Correzione**: ripristinato il comportamento 1.3.8.1—ingaggio sticky e cache decisioni solo con ``menace > 0``; edifici a minaccia 0 possono essere riselezionati, preferendo le unità da combattimento. Contro unità minacciose si esce ancora in anticipo (hot path invariato).
- **Codice**: ``worldunit/world_ai_decision.py``.
- **Test**: ``test_retarget_zero_menace.py``.

**Miglioramento: i bindings distinguono Shift sinistro/destro (``LSHIFT`` / ``RSHIFT``)**

- Oltre a ``SHIFT``, si possono usare ``LSHIFT`` e ``RSHIFT`` come modificatori (non mescolare con ``SHIFT`` sulla stessa riga).
- La ricerca preferisce il lato specifico, poi cade su ``SHIFT`` generico.
- Attivi di default: ``RSHIFT C`` / ``RSHIFT B`` (copia/aggiungi **secondaria**).
- ``LSHIFT C`` / ``LSHIFT B`` (primaria) sono **commentati** in ``res/ui/global_bindings.txt``; togliere il ``;`` iniziale per attivarli.
- **Consiglio:** usare uno screen reader come voce primaria per non impegnare ``F9``–``F12`` sulla primaria; i tasti sono densissimi. Vedi ``player/voice-libraries.rst``.
- **Codice**: ``lib/bindings.py``, ``res/ui/global_bindings.txt``, ``hotkey_editor.py``.
- **Test**: ``test_lshift_rshift_bindings.py``.

**Miglioramento: volume minimo per caselle lontane nel pan vocale**

- Le avvisaglie parlate con posizione non si attenuano senza limite: il volume resta vicino a quello di una casella adiacente (un po’ più basso consentito). I beep della minimappa usano ancora l’attenuazione completa.
- **Codice**: ``lib/sound.py``, ``clientgame/game_resources.py``, ``clientgame/game_unit_control.py``.
- **Test**: ``test_spatial_voice_alerts.py``.

**Miglioramento: moltiplicatore ``build_time`` in ``ai.txt``**

- Nuova direttiva ``build_time <pct>`` (a inizio partita, fuori dal loop): percentuale della durata normale di costruzione (``100`` = normale, ``50`` = il doppio di veloce).
- Esempi: advanced/expert ``build_time 50``; nightmare ``build_time 40``.
- **Test**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.

**Miglioramento: moltiplicatore ``gather_time`` in ``ai.txt``**

- Nuova direttiva ``gather_time <pct>``: percentuale della durata normale di raccolta (``100`` = normale, ``50`` = il doppio di veloce). Diversa dal campo ``gather_time`` dei lavoratori in ``rules.txt``.
- Esempi: advanced/expert ``gather_time 50``; nightmare ``gather_time 40``.
- **Test**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.6
--------

**Correzione: Alt+Z poteva mettere in coda un solo addestramento in più**

- **Sintomo**: dopo aver confermato l’addestramento di un contadino, Alt+Z (``do_again now``) aggiungeva solo un’altra voce in coda; le pressioni successive non allungavano la coda (sostituivano l’unico follow-up in coda).
- **Causa**: in 1.4, dietro una testa imperativa era consentito un solo ordine normale (per proteggere ``auto_explore``). Gli ordini di produzione (train/research) sono anch’essi ``is_imperative``, quindi venivano colpiti per errore. 1.3.8.1 non aveva questo limite.
- **Correzione**: gli ordini di produzione con ``never_forget_previous`` possono accumularsi; lo slot singolo resta per i follow-up normali dietro vere teste imperative.
- **Codice**: ``worldunit/world_order.py``.
- **Test**: ``test_train_queue_repeat.py``.

**Correzione: primo Alt+Z (e simili) blocco ~0.6–1s**

- **Sintomo**: all’inizio partita, il primo Alt+Z congela ~0.5–1s; 1.3.8.1 Alt+G non lo faceva.
- **Causa**: ``LALT`` → ``history_stop_primary`` → ``needs_sapi32`` avviava a freddo l’helper SAPI 32-bit (PowerShell) anche con Nuance.
- **Correzione**: le voci Nuance saltano il probe; cache di ``needs_sapi32``.
- **Codice**: ``lib/game_tts.py``.
- **Test**: ``test_nuance_skip_sapi32_probe.py``.


1.4.5.5
--------

**Miglioramento: avvisi di casella con pan stereo (segue la vista)**

- Linee passive legate a casella (nemico, perdite, scout, allarmi) panoramizzate rispetto alla casella di vista corrente.
- Il pan si aggiorna se cambi casella a metà frase.
- **Codice**: ``lib/voicechannel.py``, ``lib/message.py``, ``lib/game_tts.py``, ``lib/nuance_tts.py``, ``clientgame/game_unit_control.py``, ``clientgame/game_navigation.py``, ``tools/nuance_ve``, ``tools/sapi32``.
- **Documentazione**: ``player/voice-libraries.rst``.
- **Test**: ``test_spatial_voice_alerts.py``.

**Miglioramento: la secondaria si concentra sul campo di battaglia (economia/produzione → primaria)**

- Completamento unità/edificio, ricerca, avanzamento era, risorse e «menu cambiato» passano alla libreria **primaria**.
- **Documentazione**: ``player/voice-libraries.rst``.

**Miglioramento: Alt sinistro / Alt destro filtrano primaria vs secondaria**

- **Alt sinistro** salta/ferma la primaria; **Alt destro** salta/ferma la secondaria.
- **Con secondaria disattivata**: entrambi gli Alt saltano la riga corrente.
- **Documentazione**: ``player/voice-libraries.rst``.

**Miglioramento: buffer e frequenza mixer configurabili (meno stutter degli SFX in partita)**

- In ``SoundRTS.ini`` ``[audio]``: ``mixer_buffer`` (default ``2048``) e ``mixer_frequency`` (default ``44100``), applicati all'avvio con ``pygame.mixer.pre_init``.
- Buffer più grande = audio più stabile, latenza un po' più alta (``1024`` / ``2048`` / ``4096``). Valori non validi vanno al più vicino tra ``512/1024/2048/4096/8192``.
- Canali SFX: ``[general] num_channels`` (default ``16``; prova ``32`` se serve).
- Dopo la modifica **riavvia il gioco**.
- **Codice**: ``config.py``, ``lib/sound.py``, ``clientmedia.py``.
- **Documentazione**: ``mod/audio-management.rst``.


1.4.5.4
--------

**Miglioramento: librerie vocali primaria / secondaria e interruttore**

- In partita: le operazioni del giocatore usano la libreria **primaria**; gli eventi passivi (perdite, scoperte…) usano la **secondaria** (possono sovrapporsi; solo Alt interrompe la secondaria).
- Opzioni → Impostazioni libreria vocale: volume / tono / velocità / voce / dispositivo per libreria; attiva o disattiva la secondaria.
- **F3 nei menu** attiva/disattiva la secondaria (non in partita); disattivata, la primaria annuncia tutto.
- Installa voci SAPI o pacchetti ``voice.ini`` in ``user/voices``; uno screen reader rilevato può assumere la primaria.
- **Codice**: ``lib/voice.py``, ``lib/voicechannel.py``, ``lib/game_tts.py``, ``lib/voice_libs.py``, ``lib/voice_packs.py``, ``clientmenu.py``, ``clientmain.py``, ``config.py``.
- **Documentazione**: ``player/voice-libraries.rst``.
- **Test**: ``test_secondary_voice_toggle.py``, ``test_secondary_alt_interrupt.py``.

**Miglioramento: i rinforzi delle carte e ``starting_units`` dell’IA consumano popolazione**

- Le unità da carte ``spawn`` / ``train_bonus`` usano il normale ``population_cost`` (non sono più gratuite in popolazione).
- I bonus ``starting_units`` in ``ai.txt`` consumano anch’essi popolazione (come le unità iniziali di mappa); alza il tetto con ``starting_population`` se serve.
- **Codice**: ``card_loadout.py``, ``worldplayercomputer.py``.
- **Documentazione**: ``player/loadout-cards.rst``, ``mod/aimaking.rst``, ``mod/delayed-card-loadout.rst``, ``mod/achievement-system.rst``.
- **Test**: ``test_card_loadout.py``, ``test_ai_start_settings.py``.

**Miglioramento: moltiplicatori ``train_time``, ``research_time`` e ``unit_hp`` in ``ai.txt``**

- Nuove direttive one-shot (all’avvio partita, fuori dal loop dello script):
  - ``train_time <pct>`` — percentuale della durata normale di addestramento (``100`` = normale, ``50`` = metà tempo)
  - ``research_time <pct>`` — percentuale della durata normale di ricerca/avanzamento (``80`` = 20% più veloce)
  - ``unit_hp <pct>`` — percentuale dei PV normali delle unità di questo computer (``120`` = +20% PV)
- Esempi in ``res/ai.txt``: advanced ``train_time 50`` / ``research_time 80``; expert anche ``unit_hp 120``; nightmare ``train_time 40`` / ``research_time 60`` / ``unit_hp 140``.
- **Codice**: ``definitions.py``, ``worldplayercomputer.py``, ``worldorders/base.py``, ``worldorders/production.py``, ``worldunit/worldcreature.py``; ``res/ai.txt``.
- **Documentazione**: ``mod/aimaking.rst``.
- **Test**: ``test_ai_start_settings.py``, ``test_ai_train_research_hp.py``.


1.4.5.3
--------

**Correzione: soldati del computer intermedio bloccati su auto_explore (attacchi molto ritardati o instabili)**

- **Sintomo**: Su mappe melee piccole (es. ``jl1``), invitando un computer intermedio con umano idle, il primo attacco era molto instabile (~6 min a volte, 16–22 min altre). In 1.3.8.1 il computer aggressivo attaccava in modo stabile verso i 7–9 minuti nello stesso scenario.
- **Causa**: Dal 1.4, ``take_order`` protegge l’ordine imperativo in testa (``auto_explore`` è imperativo): un ``go`` normale viene solo messo in coda e non può sostituire l’esplorazione. ``_send_explorer`` richiamava ancora il vecchio esploratore con ``go``, falliva e assegnava nuovi esploratori finché quasi tutti i soldati erano in ``auto_explore``, quindi ``constant_attacks`` non aveva combattenti idle.
- **Correzione**: ``_send_explorer`` emette ``stop`` prima del richiamo e rimuove gli esploratori in eccesso, così di norma esplora una sola unità.
- **Codice**: ``worldplayercomputer.py`` (``_send_explorer``).
- **Verifica**: Confronto headless multi-seed vs 1.3.8.1; dopo la correzione, il primo danno dell’intermedio su jl1 è circa 5–7 minuti con span ~1,5 minuti.

**Correzione: il salto per iniziale nel menu mappe saltava la prima voce e ritardava al cambio lettera**

- **Sintomo**: In Giocatore singolo → Avvia una partita su (elenco mappe), una pressione di lettera finiva spesso sulla seconda corrispondenza (es. ``m`` → ``m2`` invece di ``m1``, ``p`` → ``pm2`` invece di ``pm1``); premendo un’altra lettera c’era una pausa di circa 0,7–1 secondo prima del salto.
- **Causa**: L’annuncio del titolo con ``keep_key`` rimetteva in coda tutti i ``KEYDOWN`` di auto-ripetizione, quindi una pressione fisica veniva gestita due volte; ricordare l’ultima mappa inseriva un duplicato in cima all’elenco, che vinceva se condivideva la lettera. ``_first_letter`` chiamava ``translate_sound_number`` → ``_global_lookup_text`` sui nomi file mappa, costando ~1 secondo su una lista di centinaia di voci.
- **Correzione**: Conservare solo il primo ``KEYDOWN`` all’interruzione della voce e cancellare le ripetizioni dopo il salto per lettera; con selezione fresca, cercare la prima corrispondenza dall’inizio dell’elenco; ricordare con ``default_choice_index`` invece di un duplicato; prendere il primo carattere del nome mappa e cercare gli id TTS numerici solo nel layer locale.
- **Codice**: ``clientmenu.py``, ``lib/voice.py``.
- **Test**: ``test_menu_first_letter_jump.py``.


1.4.5.2
--------


**Miglioramento: menace multidimensionale e override opzionali in rules**

- Il ``menace`` predefinito non è più solo il danno: include danno, cover/precisione, cooldown, wind-up (``*_ready``), HP, armatura, schivata, portata e velocità (scelta bersaglio e minaccia per casella).
- Campi opzionali: ``menace`` / ``menace_vs`` (assoluto), ``menace_mult`` / ``menace_mult_vs`` (peso sulla base auto). Parametri: ``menace_armor_weight``, ``menace_dodge_weight``, ``menace_range_weight``, ``menace_speed_weight``, ``menace_hp_ref``.
- **Documentazione**: ``mod/modding.rst``, ``mod/aimaking.rst`` (EN/ZH).

**Miglioramento: inseguimento continuo tra caselle (inseguimento reale)**

- **Prima**: In modalità ``chase``, quando il nemico lasciava la casella l’IA emetteva ``go`` automatici verso le caselle vicine e poi attaccava di nuovo — ancora guidato da ordini; l’unità poteva restare «in attacco» senza uscire.
- **Ora**: ``chase`` mantiene un solo ``AttackAction`` sul nemico bloccato e segue tramite uscite tra caselle, senza spam di ``go``.
- **Hold**: ``position_to_hold`` alla creazione blocca ancora l’uscita in offensiva / guardia. Difensiva / inseguimento sono esenti (l’inseguimento azzera l’hold quando attraversa). ``go`` / ``attack`` normali chiamano ancora ``stop()`` e azzerano l’hold.
- **Codice**: ``worldaction.py``, ``worldunit/world_ai_decision.py``, ``worldunit/world_movement.py``.
- **Documentazione**: ``player/unit-default-behavior.rst``.
- **Test**: ``test_chase_continuous_pursuit.py``.

**Miglioramento: schermata attributi con valori terreno in tempo reale**

- Alt+V mostra ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` e modificatori di carica per terreno.
- Il terreno della casella attuale (``mdg_vs`` / ``rdg_vs`` / ecc.) e ``*_on_terrain`` alimentano danno, cooldown e velocità in UI (``*_vs`` terreno = percentuale decimale; ``speed_on_terrain`` resta velocità assoluta).
- **Codice**: ``attributes/terrain_effective.py``, ``attributes/combat_attributes.py``, ``attributes/basic_attributes.py``, ``attributes/bonus_handler.py``.
- **Test**: ``test_terrain_attributes_ui.py``, ``test_terrain_effective_attributes.py``.

**Correzione: Tab non trova più uscite su caselle mai esplorate**

- **Sintomo**: Su caselle mai visitate, Tab poteva annunciare uscite dall’altro lato.
- **Causa**: La nebbia memorizzava le uscite opposte prima dell’ingresso reale.
- **Correzione**: Senza ``scouted_squares`` né ``scouted_before_squares``, riepilogo / visibilità vuoti; la nebbia statica dopo una visita permette ancora Tab.
- **Codice**: ``clientgame/game_unit_control.py``.
- **Test**: ``test_unknown_square_tab_blank.py``.

**Correzione: beep ``order_impossible`` dopo aver ucciso un animale con Backspace**

- **Sintomo**: Dopo l’attacco predefinito a un animale cacciabile, suonava ``order_impossible``.
- **Causa**: ``AttackOrder`` trattava la scomparsa del bersaglio come fallimento.
- **Correzione**: Completare l’ordine se il bersaglio sparisce o ``hp <= 0``.
- **Codice**: ``worldorders/movement.py``.
- **Test**: ``test_hunting.py``.

**Correzione: ordine predefinito sui neutrali e danno di caccia**

- ``go`` normale / predefinito sui neutrali (non imperativo) si limita a muovere, senza AttackAction a danno zero.
- ``attack`` normale su ``is_huntable`` (inclusa caccia predefinita con Backspace) infligge danno; solo l’attacco imperativo fa trattare i neutrali come bersagli auto all’IA.
- **Codice**: ``worldunit/world_ai_decision.py``, ``worldunit/worldcreature.py``.
- **Documentazione**: ``player/hunting.rst``, ``player/unit-default-behavior.rst``.
- **Test**: ``test_neutral_no_auto_attack.py``, ``test_neutral_go_and_hunt_attack.py``.

**Correzione: crash nell'aggiornamento della percezione del giocatore Computer (manca ``_buckets``)**

- **Sintomo**: A partita in corso (specie con IA ``computer_only`` della mappa, alleati IA o dopo un caricamento) poteva crashare nella fase di percezione del loop principale con ``AttributeError: 'Computer' object has no attribute '_buckets'``.
- **Causa**: L'indice spaziale del giocatore ``_buckets`` era inizializzato solo nel wrapper ``Player.__init__``; salvataggio/caricamento rimuove quel campo di cache; i controlli di visibilità alleata in blocco (``bulk_visibility_check``) chiamano ``_potential_neighbors`` degli alleati e sollevavano l'eccezione se un ``Computer`` non aveva ancora ``_buckets``.
- **Correzione**: Pre-inizializzare ``_buckets`` in ``BasePlayer.__init__`` insieme alle altre cache di percezione; ``_potential_neighbors`` usa un dizionario vuoto se manca; ``update_alliance`` azzera la cache di istanza ``allied_vision`` per evitare liste di alleati obsolete dopo un cambio di alleanza.
- **Codice**: ``worldplayerbase/base.py``, ``worldplayerbase/perception.py``, ``worldplayerbase/__init__.py``.
- **Test**: ``test_meteors_computer_only.py``, ``test_phase3_parity.py``, ``test_neutral_passive_creep.py``.


1.4.5.1
--------

**Miglioramento: copertura terreno, modificatori per unità e notazione percentuale**

- ``class terrain`` in ``rules.txt`` supporta ``cover <terra> <aria>``, come ``speed``: ``terrain marsh h8`` sulla mappa eredita la copertura predefinita; le righe ``cover`` della mappa sovrascrivono ancora le caselle singole.
- Il terreno può modificare **tipi di unità** con ``speed_vs``, ``cover_vs``, ``dodge_vs``, ``mdg_vs``, ``rdg_vs``, ``mdg_cd_vs``, ``rdg_cd_vs`` (es. ``speed_vs knight .25 archer .5``). Si possono usare solo ``*_vs`` senza ``speed``/``cover`` globali.
- Quei ``*_vs`` e ``mdg_on_terrain`` / ``rdg_on_terrain`` / ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain`` (e ``charge_*_terrain``) usano **percentuali decimali 0–1** (``.5`` = ±50%%, ``.1`` = ±10%%) rispetto al danno o cooldown base attuale dell'unità.
- ``speed_on_terrain`` resta una **velocità assoluta** (diversa da ``speed_vs`` in percentuale).
- ``speed`` / ``cover`` sulla mappa valgono per **tutte** le unità sulla casella; le differenze per unità vanno nelle def terreno o unità in ``rules.txt``.
- **Codice**: ``worldterrain.py``, ``lib/square_terrain_rules.py``, ``world/world_map.py``, ``combat/hit_miss.py``, ``combat/damage_calculation.py``, ``combat/attack_action.py``, ``worldunit/world_movement.py``; mappe casuali emettono righe ``cover`` (``rmg_templates.terrain_cover_line``).
- **Documentazione**: ``mod/building-land-terrain.rst``; commenti in ``res/ui/editor_palette.txt``.
- **Test**: ``test_terrain_cover_defaults.py``, ``test_terrain_unit_vs.py``, ``test_unit_on_terrain_percent.py``; ``test_combat_terrain_modifiers.py`` aggiornato a casi percentuali.

Correzioni di bug e miglioramenti UX voce/audio:

**Correzione: cooldown attacco corpo a corpo/a distanza (``mdg_cd`` / ``rdg_cd``) più lento delle rules**

- **Sintomo**: Con 1 secondo di cooldown nelle rules (es. contadino ``mdg_cd 1``), l'intervallo reale era sensibilmente maggiore che in 1.3.8.1 (~1,5 s vs ~1,2 s; quest'ultimo è solo quantizzazione del tick da 300 ms).
- **Causa**: (1) Con ``mdg_ready`` / ``rdg_ready`` a 0, il ramo di preparazione consumava un tick extra prima di colpire; (2) i colpi istantanei (``mdg_delay`` / ``rdg_delay`` 0) passavano da un minimo di 100 ms in ``_schedule_ballistic_hit``; (3) ``attack_action.aim()`` e ``damage_effects._schedule_ballistic_hit`` impostavano entrambi il cooldown, con una seconda scrittura dopo il ritardo che allungava ``next_attack_time``.
- **Correzione**: saltare la preparazione quando ``ready=0`` e attaccare subito; nessun minimo di 100 ms per colpi istantanei; il cooldown si imposta una sola volta in ``attack_action.aim()`` all'avvio dell'attacco.
- **Nota**: ``charge_mdg_cd`` / ``charge_rdg_cd`` usano un percorso separato (``receive_hit`` immediato, senza preparazione/schedulazione balistica) e non erano interessati; il ritmo misto carica + attacco normale migliora indirettamente con la correzione del CD normale.
- **Codice**: ``combat/attack_action.py``, ``combat/damage_effects.py``.
- **Test**: ``test_attack_cooldown_timing.py``.

**Miglioramento: rifiuto ordini go e feedback vocale su terreno non transitabile**

- Unità di terra con ``go`` / ``patrol`` verso caselle ``is_ground 0``, o aeree verso ``is_air 0``: ordine rifiutato in coda con ``ground_impassable`` / ``air_impassable``.
- Terreno con ``passable_units``: unità fuori lista → «\<tipo unità\>, cannot pass» (titolo unità + messaggio 5701); tipi in lista (anche via ``is_a``) possono ancora ``go``.
- **Codice**: ``worldorders/base.py``, ``lib/square_terrain_rules.py``, ``clientgameentity/events.py``. **Test**: ``test_water_impassable_order.py``.

**Correzione: fantasma di nebbia senza nome dopo il suicidio di un'unità**

- **Sintomo**: Dopo il suicidio di un'unità, ciclare i bersagli con Tab nella stessa casella poteva ancora selezionare un oggetto senza nome leggibile.
- **Causa**: Dopo la morte ``place is None``, la memoria della nebbia di guerra non veniva cancellata in tempo; gli oggetti in memoria potevano avere un ``title`` (suffisso nebbia) ma un ``short_title`` vuoto, e Tab li trattava comunque come selezionabili.
- **Correzione**: ``perception.py`` dimentica la memoria quando ``initial_model.place is None``; le unità che lasciano la percezione non vengono memorizzate quando ``place is None`` o quando sono unità morte del giocatore; ``game_unit_control.py`` ``is_visible`` richiede un ``short_title`` non vuoto.
- **Test**: ``test_suicide_fog_ghost.py`` (percorsi memoria nebbia cadavere e audio ambientale preservati).

**Correzione: HP del muro che oscillano su e giù durante l'attacco**

- **Sintomo**: Attaccare ``wall`` e altri edifici ``is_repairable`` poteva far salire e scendere intermittentemente HP o suoni di variazione vita.
- **Causa**: I muri ereditano ``is_repairable=True`` dagli edifici, quindi attacco / riparazione / soglia di cattura potevano interagire; la sync HP nebbia (``_sync_memory_hp_from_live``) senza portare ``previous_hp`` tra scambi percezione/memoria causava falsi feedback di variazione vita.
- **Correzione**: ``world_order.py`` / ``worldcreature.py`` / ``worldworker.py`` — edifici riparabili nemici di default ``go``, imperativo di default ``attack``; percorsi riparazione protetti con ``not is_an_enemy(target)``; ``game_navigation.py`` preserva il tracking HP sugli aggiornamenti nebbia (``_take_hp_tracking`` / ``_apply_hp_tracking``).
- **Test**: ``test_imperative_attack.py`` (attacco imperativo sui muri).

**Correzione: ordine go normale interrompeva erroneamente l'attacco imperativo**

- **Sintomo**: Con un'unità in attacco forzato (es. municipio), un ``go`` normale interrompeva l'attacco ma la selezione gruppo (es. F) annunciava ancora «attacca il municipio, vai a \<casella\>» — comportamento e voce incoerenti.
- **Causa**: ``take_order`` con ``forget_previous=True`` chiamava ``cancel_all_orders()``, rimuovendo l'attacco imperativo e accodando ``go``, mentre ``AttackAction`` poteva restare sull'unità.
- **Correzione**: Con ordine imperativo attivo, i comandi normali (eccetto ``stop``) vengono accodati automaticamente (``forget_previous=False``) senza sostituire la testa imperativa; l'unità completa l'attacco forzato prima del comando in coda. Dopo un imperativo è consentito **un solo** comando in coda; un nuovo comando normale **sostituisce** quello già accodato (come in 1.3.8.1).
- **Codice**: ``worldunit/world_order.py`` ``take_order``.
- **Test**: ``test_imperative_attack.py`` (``test_normal_go_queues_behind_imperative_attack``, ``test_only_one_queued_order_behind_imperative_attack``, ecc.).

**Miglioramento: descrizioni vocali del comportamento delle unità**

- Dopo aver selezionato un bersaglio con Tab, Ctrl+Backspace o go + Ctrl+Enter conferma «attacca \<bersaglio\>» invece di «vai» per unità/edifici nemici.
- Selezione gruppo da tasto rapido (es. F per i fanti): «Controlli N fanti che attaccano il municipio»; se si muovono mentre combattono, aggiunge «vai a c6».
- **Codice**: ``clientgameentity/base.py`` ``_attack_action_title_msg``; ``properties.py`` ``orders_txt``; ``game_orders.py`` ``_say_validate_confirmation`` / ``_say_default_confirmation``; ``game_unit_control.py`` ``say_group``.
- **Test**: ``test_attack_orders_txt.py``, ``test_imperative_attack.py``.

**Miglioramento: urla di battaglia a livelli**

- Tre livelli: ``shout_bg`` (sfondo campo di battaglia), ``shout_unit`` (voce unità), ``shout_event`` (primo scontro / carica / crit in evidenza); cooldown globali e per casella; ``formation_sound_queue`` sfasa i burst così le urla non si sovrappongono ai suoni di colpo nello stesso frame.
- **Codice**: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``.
- **Documentazione**: ``mod/battle-shouts.rst``.
- **Test**: ``test_battle_shout_audio.py``.

**Miglioramento: refactor motore audio P0–P2**

- **Correzione**: bozze precedenti descrivevano P0–P2 come livelli di *priorità* ambientale/combattimento/avvisi; sono in realtà **tre fasi di refactor** del motore audio, distinte dalle urla a livelli sopra e da ``psounds.play(..., priority=…)``. Vedi ``mod/audio-management.rst``.
- **P0 struttura**: ``lib/music_resolver.py``; ``sound_cache.clear_decoded()`` al cambio mod/mappa; fix stato mutabile in ``SoundSource`` / ``SoundManager``.
- **P1 UX**: ``audio/sfx_volume`` separato da ``main_volume``; attesa voce con event pump; fallback musica menu unificato.
- **P2 polish**: LFO ambiente; ``lib/battle_music.py``; pulizia ``music_resolver``; SFX in ``ui/`` con ``.ogg`` / ``.wav`` / ``.mp3`` (``.ogg`` preferito) e precaricamento (``preload_sounds`` / ``tick_preload``).
- **Tasti**: Home/End per SFX; Alt+Home/Alt+End per musica.
- **Test**: ``test_music_resolver.py``, ``test_audio_settings.py``, ``test_voice_pump.py``, ``test_ambient_stereo_volume.py``, ``test_battle_music.py``, ``test_sfx_formats.py``.

1.4.5.0
--------

Terreno configurabile, contenitori di trasporto, ``attack_inside_chance`` e mappe casuali:

**Terreno a caselle configurabile**

- Il terreno è ``class terrain`` in ``rules.txt`` più le def corrispondenti in ``style.txt``; nessun terreno di default del motore su ogni cella.
- La mappa ``terrain <name>`` applica transitabilità, acqua, velocità e terreno elevato dalle rules; ``class building_land`` estende prati e siti edificabili.
- Editor mappe e sintassi sotto-cella ``square/x,y``: ``mod/building-land-terrain.rst``.

**Contenitori di trasporto**

- ``passenger_attack_types``: tipi di unità che possono attaccare bersagli esterni mentre sono nel contenitore.
- ``load_bonus``: per ogni unità caricata, aggiunge stats al contenitore.
- ``passenger_bonus``: stats aggiunte al passeggero mentre è dentro; rimosse allo scarico. Stessa sintassi di ``load_bonus``; combinabile con ``load_bonus``.

**``attack_inside_chance``**

- Proprietà contenitore aperto: gli attacchi esterni colpiscono i passeggeri dentro a questa percentuale (es. muro ``attack_inside_chance 40``).

**Generatore di mappe casuali**

- I template integrati elencano ogni terreno ``rmg_terrain 1`` dalle rules; il piazzamento usa le proprietà delle rules.
- File ``random_map_template`` personalizzati in ``cfg/randommap/`` o ``mods/.../randommap/``.
- Codici di condivisione: ``RMG1`` (abbreviazioni integrate) / ``RMG2`` (nomi personalizzati completi).

Vedi ``mod/building-land-terrain.rst``, ``mod/randommap.rst``, ``mod/modding.rst`` (Transport containers); test ``test_transport_bonus.py``, ``test_attack_inside_chance.py``, ``test_randommap.py``.

**Costruire ponti sull'acqua**

- I lavoratori possono posare tratti di ``wooden_bridge`` casella per casella su fiumi, laghi e oceani (``is_buildable_on_water_only`` + ``bridge_terrain bridge_deck``).
- Fase ponteggio: costruzione camminabile, nessun passaggio fino al completamento; i tratti finiti si collegano alla riva / ad altri ponti; neutrali per tutti i giocatori.
- TTS del sito come le altre voci ``buildingsite``; i passi usano ``bridge_deck`` / ``big_bridge`` ``ground wood``.
- Documentazione: ``mod/water-bridge-building.rst``; test: ``test_bridge_terrain.py``.

**Modificatori di combattimento unità sul terreno**

- ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``: bonus di attacco, cooldown e carica per terreno per la **casella corrente dell'attaccante** (stessa sintassi elenco ``terrain value …`` di ``speed_on_terrain``).
- I modificatori di danno negativi indeboliscono gli attacchi; ``*_cd_on_terrain`` positivi allungano il cooldown.
- Documentazione: ``mod/building-land-terrain.rst``; test: ``test_combat_terrain_modifiers.py``.

**Passi e suoni di caduta sul terreno**

- ``move_on_<key>`` / ``falling_on_<key>`` accettano ora **nomi di tipo terreno** (es. ``ocean``) e categorie ``ground`` di ``style.txt`` (es. ``water``, ``grass``); il nome tipo è provato per primo.
- Correzione: su terreni senza ``ground`` (es. ``ocean``), ``falling_on_ocean`` non corrispondeva mai e suonava solo il generico ``falling``.
- Documentazione: ``mod/modding.rst`` (Combat sound system); test: ``test_falling_terrain_sound.py``.

**Urla di battaglia (riproduzione a livelli)**

- Tre livelli in combattimento: sfondo campo di battaglia, voce unità, evidenziazioni evento; cooldown globali/per casella.
- ``ui/style.txt``: ``shouts`` su ``def walking_unit``; si attiva quando almeno un lato ha ≥5 unità in combattimento nella casella.
- Codice: ``battle_shout_audio.py``, ``combat.py``, ``formation_sound_queue.py``; test: ``test_battle_shout_audio.py``.
- Documentazione: ``mod/battle-shouts.rst``.

1.4.4.9
--------

Corretto un bug per cui la distanza minima effettiva di carica non funzionava.

Documentazione aggiornata.

1.4.4.8
--------

Terreno sotto-cella per autori di mappe e editor mappe:

Terreno sotto-cella dentro una casella

- I comandi terreno possono mirare a un'area dentro una casella con sintassi ``square/x,y``, ad esempio ``high_grounds a1/1,1 a1/1,2``.
- ``subcell_precision N`` controlla la suddivisione. Default ``3``, valori da ``2`` a ``20``.
- Comandi supportati: ``terrain``, ``high_grounds``, ``speed``, ``cover``, ``water``, ``ground`` e ``no_air``.
- Combattimento, movimento, velocità terreno, cover e controlli terreno elevato possono usare la sotto-cella effettiva dell'unità.

Navigazione zoom e comportamento editor

- La navigazione mappa in modalità zoom annuncia il terreno sotto-cella corrente, incluso terreno elevato parziale.
- Nell'editor mappe sperimentale, Invio applica il terreno selezionato alla sotto-cella corrente mentre lo zoom è attivo.
- Le mappe salvate scrivono le override sotto-cella con sintassi ``square/x,y``.

1.4.4.7
--------

Formule soglia XP eroe (``xp_threshold_growth``) e reset XP dopo salita di livello (``level_up_reset_xp``):

``Formule soglia XP eroe (``xp_threshold_growth``)``

- Le def eroe possono impostare ``max_level`` + ``xp_threshold_growth``; il caricamento di ``rules.txt`` riempie automaticamente ``xp_thresholds`` così i modder non devono elencare a mano decine o centinaia di valori XP cumulativi.
- Tipi di curva: ``linear``, ``quadratic``, ``polynomial``, ``geometric`` (vedi Heroes in ``modding.rst``).
- Retrocompatibile con ``xp_thresholds`` esplicito (l'elenco esplicito vince). Le def figlie possono ereditare ``xp_threshold_growth`` via ``is_a`` e sovrascrivere solo ``max_level``.
- Implementazione: ``soundrts/xp_threshold_growth.py``, ``soundrts/definitions.py``; test: ``test_xp_threshold_growth.py``.

``Reset XP dopo salita di livello (``level_up_reset_xp``)``

- Opzionale ``level_up_reset_xp 1`` sulle def eroe: l'XP corrente diventa 0 dopo ogni salita di livello in combattimento; default ``0`` mantiene l'XP cumulativa.
- Quando ``1``, preferire ``xp_thresholds`` per livello, non totali cumulativi.
- Implementazione: ``soundrts/worldunit/world_status_update.py``; test: ``test_level_up_combat_stats.py``.

1.4.4.6
--------

Pulizia nomi suoni mod, sistema abilità unificato, effetti abilità generici, filtri bersaglio abilità ed esclusioni -tag, scaling stats a salita di livello, sblocco abilità per livello, trasporto eroi di campagna, suoni uso oggetti zaino, suoni ready/prep personalizzati, toggle tasto zaino/equipaggiamento, livello iniziale eroe e display XP livello 0:

Rinomina chiavi suoni di attacco

- I suoni di attacco in ``ui/style.txt`` preferiscono ora le chiavi ``mdg`` / ``rdg``:
  ``launch_mdg`` / ``launch_rdg``, ``mdg_hit`` / ``rdg_hit``,
  ``mdg_hit_vs`` / ``rdg_hit_vs``, ``mdg_missed`` / ``rdg_missed``,
  e ``mdg_dodge`` / ``rdg_dodge``.
- I suoni di carica usano ``launch_charge_mdg`` / ``launch_charge_rdg`` e
  ``charge_mdg_hit`` / ``charge_rdg_hit``.
- I file ``style.txt`` in bundle sono stati migrati; le vecchie chiavi ``matk`` / ``ratk`` restano compatibili come fallback.

Suoni ready personalizzati

- Le abilità con ``ready \<seconds\>`` possono definire ``ready \<sound\>`` sullo style dell'abilità; trigger manuali e automatici lo riproducono all'inizio della prep.
- La prep di attacco normale può riprodurre i suoni ``mdg_ready`` / ``rdg_ready`` dello style unità.

Sistema abilità unificato

- Una ``class skill`` può essere sia usata manualmente sia auto-triggerata; non servono liste gemelle separate.
- Campi abilità: ``auto_trigger 1``, ``manual_use 1`` (default 1), ``trigger_timing``.
- ``trigger_timing``: ``on_hit`` | ``on_attack`` | ``on_attack_replace`` | ``on_damaged``.
- Le abilità apprese vivono in ``can_use_skill``; il menu comandi mostra solo le abilità ``manual_use 1``.
- Le liste legacy funzionano ancora: ``active_trigger_skills``, ``attack_trigger_skills``,
  ``attack_replace_skills``,   ``passive_trigger_skills`` restano compatibili insieme ai nuovi campi.

Effetti abilità generici

- Danno fisso ``harm_target N`` / ``harm_area N R``; danno di combattimento ``harm_target mdg`` / ``harm_area mdg R`` (pipeline completa).
- Combo ``burst mdg N (interval X)`` o `` (delays …)``; knockback ``push``; ``buffs`` / ``debuffs``; ``deploy``; ``summon``.
- Legacy ``teleportation`` / ``recall`` / ``conversion`` / ``raise_dead`` / ``resurrection`` funzionano ancora.
- Tassi di trigger, condizioni HP, liste buff/debuff a inizio attacco restano compatibili; vedi ``mod/skills-and-effects.htm``.

``Filtri tipo bersaglio ed esclusioni (``-tag``)``

- ``class skill`` supporta ``harm_target_type`` su ``burst`` / ``harm_target`` / ``harm_area`` / ``push``; di default solo nemici se non impostato.
- Il prefisso ``-`` esclude un tag (es. ``-building``). Si applica a ``harm_target_type``, ``heal_target_type``, ``mdg_targets`` / ``rdg_targets``, ``target_type`` di buff/debuff.
- Esclusioni diplomatiche: ``-enemy``, ``-allied``, ``-neutral``.
- Esempi: ``harm_target_type enemy unit -building``; ``heal_target_type unit -undead``; ``mdg_targets -building``.

**Bonus stats a salita di livello (``*_per_level``)**

- Le unità possono impostare ``\<stat\>\_per_level`` in ``rules.txt`` per la maggior parte delle stats di combattimento, vita, mana, heal/harm e regen; ogni salita di livello aggiunge un passo.
- Esempi: ``hp_max_per_level``, ``mdg_per_level``, ``charge_mdg_per_level``, ``mdg_crit_rate_per_level``, ``mana_max_per_level``, ``heal_cd_per_level``, ecc.
- Il ripristino eroe di campagna riapplica i bonus cumulativi fino al livello salvato.

Livello iniziale eroe e display stato

- ``level`` / ``xp`` sulle def eroe in ``rules.txt`` (richiede ``xp_thresholds``); ``level \> 1`` applica i ``*_per_level`` cumulativi allo spawn.
- ``level 0``: inizia sotto il livello 1; lo stato Tab mostra livello 0 e XP verso ``xp_thresholds[0]``.
- Gli eroi con ``xp_thresholds`` annunciano sempre il livello nello stato Tab (incluso 0 e 1).

``Guarigione completa a salita di livello (``level_up_heal_full``)``

- Opzionale ``level_up_heal_full 1`` sulle def eroe: ripristina HP e mana completi a ogni salita di livello; default ``0`` mantiene solo il guadagno incrementale HP/mana.

Sblocco abilità per livello e libri abilità

- Unità ``level_skills \<level\> \<skill\> …``: aggiunta automatica a ``can_use_skill`` al raggiungimento di quel livello (con notifica vocale).
- Unità ``learn_level_skills``: gate aggiuntivo di apprendimento da libro (il più restrittivo con ``learn_level`` dell'oggetto).
- Libri abilità: apprendimento permanente via ``use_item`` nello zaino; il pickup non concede se gated.
- Non duplicare la stessa abilità su ``level_skills`` e su un libro.

Trasporto eroi di campagna

- Def eroe: ``campaign_carryover 1`` (opzionali ``campaign_carryover_stats``, ``campaign_carryover_inventory``, ``campaign_carryover_id``).
- In vittoria, livello/XP e zaino salvati in ``user/campaigns.ini``; il capitolo successivo ripristina; la coop non persiste.
- Opzionale ``hero_min_level 13:2 …`` in ``campaign.txt`` per pavimenti di livello per capitolo.

Suoni uso oggetti zaino (style.txt)

- Stessa ricerca a tre livelli di pickup/drop: oggetto ``use`` / ``on_use`` → unità ``use_\<item type\>`` → globale ``item_used`` (``def thing``).
- I suoni suonano solo dopo successo confermato dal server; nessuna voce ottimistica «usato» su Invio.
- Libri abilità: suono uso + titolo abilità + ``skill_learned``; altri consumabili: titolo oggetto + «usato».
- I consumabili sono rimossi dall'inventario al successo; ``unequip`` del libro abilità non toglie più le abilità apprese permanentemente.

Tasti rapidi zaino / equipaggiamento

- Shift+V cicla tra zaino ed equipaggiamento (classico e a livelli); Ctrl+V rimosso; F3 a livelli funziona ancora.

Documentazione: ``mod/modding.rst``, ``mod/modding.rst``, ``mod/skills-and-effects.htm``, ``mod/campaign-hero-carryover.htm``
Test: ``test_level_skills.py``, ``test_level_up_combat_stats.py``, ``test_campaign_hero.py``, ``test_wuxia_skills.py``, ``test_worldskill_deploy.py``, ``test_target_type_exclusions.py``, ``test_hit_vs_buff_sounds.py``, ``test_damage_seq_burst.py``,
``test_changelog_138x.py``, ``test_skill_trigger_sounds.py``, ``test_inventory_backpack.py``


1.4.4.5
--------

Gameplay mappe casuali stile HoMM/Civ5, ordine cattura predefinito, operazioni anfibie IA, correzione scoring Ctrl+Shift+F4, editor mappatura tasti:

Mappe casuali: ispirazione HoMM / Civ5

- menu modalità vittoria: conquest / economic / exploration / survival (TTS 5425–5430)
- POI mappa: rovine antiche, caserme catturabili, creep centrali, tesoro opzionale
- codici di condivisione: 11° campo vittoria; ``res/rules.txt``: ``ancient_ruin``, ``captured_barracks``
- documentazione: ``player/英雄无敌与文明5玩法说明.htm``; ``randommap.rst``
- test: ``test_randommap.py``

Ordine cattura predefinito (can_capture)

- ``capture_hp_threshold 100``: ``can_capture 1`` → occupazione predefinita; ``can_capture 0`` → solo attacco/movimento
- soglie sotto 100 richiedono ancora combattimento fino alla soglia di cattura
- documentazione: ``mod/modding.rst``; giocatori ``player/unit-default-behavior.htm`` §4
- test: ``test_capture_default_order.py``

Operazioni IA oltre l'acqua

- raccolta anfibia, assalti con trasporto, mantenimento navale su mappe d'acqua
- test: ``test_worldplayercomputer_water.py``, ``test_ai_naval_m3.py``

Addestramento: scala il batch alla popolazione rimanente

- spazio popolazione insufficiente in addestramento a batch → addestra quanti ne entrano (es. 5 richiesti, 3 pop → 3 addestrati); zero spazio fallisce ancora
- ``worldorders/production.py`` (``TrainOrder._max_train_count_for_population``)
- test: ``test_train_population.py``

Correzione: cambio vista Ctrl+Shift+F4 vs scoring

- fissa l'umano di scoring; nessun premio vittoria IA/passivo dopo il cambio; baseline dei nemici di scoring sconfitti al primo cambio
- test: ``test_change_player_scoring.py``

Editor mappatura tasti

- Opzioni → Key mapping (accanto a Hotkey scheme); ``hotkey_remapping_menu.py``, ``hotkey_editor.py``, ``hotkey_catalogs.py``
- 8 livelli a livelli + ~179 binding classici; per mod ``user/hotkey_overrides/{mod_key}.json``; effettivo al prossimo avvio partita
- ricerca, varianti avanzate, chiavi alias (``binding_id@default_key``), import/export clipboard
- catalogo TTS 5500–5684; varianti avanzate classiche complete; correzioni etichette gruppi di controllo
- etichette: Alt+Space → modalità prima persona; Ctrl+F2 → toggle display
- documentazione: ``mod/hotkey-mapping-editor.htm``, ``player/layered-hotkeys.htm``
- test: ``test_hotkey_editor*.py``, ``test_hotkey_catalog_tts.py``, ``test_hotkey_editor_mod_isolation.py``

1.4.4.4
--------

Carte di carico ritardate, punteggio e voti, obiettivi per fazione, progressi meta, CrazyMod, correzioni UX:

Carte pre-missione ritardate

- ``cards.txt``: ``delay \<seconds\>``, ``delay_minutes \<n\>`` — programma effetti dopo tempo di gioco (``world.schedule_after``, rispetta ``timer_coefficient``)
- ``tech \<upgrade_id\>`` sulle carte; combinabile con ``spawn`` / ``resource`` sotto un delay condiviso
- voce all'applicazione: effetti dopo N minuti/secondi; allo scatto: effetto carta di carico attivato (TTS 5387–5393)
- vanilla: ``card_reinforcements_delayed`` (3 footman dopo 10 min), ``card_delayed_melee_weapon`` (``melee_weapon`` dopo 8 min)
- obiettivi: ``reinforcement_contract`` → rinforzi ritardati; ``defeat_expert`` → carta arma da mischia ritardata
- documentazione: ``mod/delayed-card-loadout.htm`` (giocatori: ``player/loadout-cards.htm``)
- test: ``test_cards.py``, ``test_card_loadout.py`` (``-k delay`` / ``-k delayed``)

Punteggio post-partita e voti a lettera

- documentazione: ``mod/score-grading-system.htm`` (giocatori: ``player/score-and-grades.htm``)
- le sette dimensioni base sono limitate a 800; il bonus sconfitta IA è extra ed escluso dal denominatore percentuale
- voto sconfitta limitato a D (``grade_total`` max 479)
- vittoria + utilizzo < 50%: dimensione efficienza frugale (TTS 5251)
- estrazione su mappe senza capacità deposito: proporzionale alla raccolta di riferimento (1000 = 100 pts); mappe campagna senza deposito invariate
- sopravvivenza 0 se nessuna unità prodotta; perdita/demolizione edifici 5 pts per edificio (era 10)
- rimossi helper score legacy inutilizzati da ``worldplayerbase/resources.py``
- test: ``test_score_breakdown.py``

Dati obiettivi e gradi

- Tenente (``rank_lieutenant``): 200 medaglie, 1 slot di carico
- ``defeat_beginner`` medaglia ripetuta 8; ``perfect_survival`` richiede sopravvivenza ≥90 e difesa edifici ≥90

Correzioni

- lavoratore ``can_gather all``: l'UI attributi non duplica più «all» quando le liste deposito ed edificio sono entrambe ``all``
- test: ``conftest`` ripristina ``res.mods`` dopo i test di cambio mod
- UX carico / fazione casuale; broadcast sconfitta PNG gated da ``broadcasts_defeat_and_quit``

Progressi per fazione e meta

- ``achievements_per_faction 1``, ``\_meta.json``, ``scope meta``; campagna esclusa

CrazyMod 9

- milestone per fazione, tier meta, ritocchi di bilanciamento

Documentazione (giocatore / sviluppatore)

- Indice: ``help-index.htm``, ``player/README.htm``, ``mod/README.htm``

Trasporto eroi di campagna (guidato dalle rules)

- ``rules.txt``: ``campaign_carryover 1`` (opzionali ``campaign_carryover_id``, ``campaign_carryover_stats``, ``campaign_carryover_inventory``)
- ``campaign.txt``: ``hero_min_level 13:2 …`` per livelli pavimento per capitolo
- salvato in vittoria in ``user/campaigns.ini`` (``hero_\<id\>\_xp`` / ``\_level`` / ``\_inventory``); ripristinato al capitolo successivo; la coop non persiste
- indipendente da ``campaign_flag`` / ``add_inventory_item``; vedi ``modding.rst``, ``mapmaking.rst``, ``mod/campaign-hero-carryover.htm``
- implementazione: ``soundrts/campaign_hero.py``; test: ``test_campaign_hero.py``

Correzioni e voce

- mappe lanes: ``has_entered`` con coordinate 1-based (es. ``8,2``) non collide più con chiavi griglia 0-based; i trigger rovine funzionano
- input di testo (codice condivisione, seed, ecc.): Ctrl+V incolla via API clipboard pygame-ce
- TTS HoMM/Civ5 e missioni secondarie campagna spostati da 5107–5123 a 5425–5441 per evitare conflitti ID

1.4.4.3
--------

Obiettivi e armeria (fasi 2–3: medaglie, gradi, carte, carico pre-missione):

- nuova voce menu principale Achievements: elenco obiettivi + armeria (grado, onori, totale medaglie, cariche carte)
- dopo scaramuccia / mappa casuale vs computer, gli sblocchi ``achievements.txt`` sono valutati; voce per sblocchi, medaglie, carte, promozione grado e slot di carico extra
- i progressi sono salvati per mod: ``user/achievements/\<mod\>.json``
- carico carte pre-missione: Single player → Start on map → Start, poi scegli fino a N carte per grado (Tenente = 1 slot, Capitano = 2, … in ``titles.txt``); solo TrainingGame (mappa personalizzata o casuale vs IA — non campagna o multigiocatore)
- gli effetti si applicano all'avvio partita: risorse bonus e/o unità vicino al tuo start; una carica spesa per carta usata
- gli spawn delle carte non usano popolazione; gli spawn fazione casuale usano equivalenti di fazione
- correzione: le carte di carico non venivano applicate perché il giocatore locale era rilevato solo dopo ``GameInterface``; ora applicate dopo il caricamento mappa, prima dell'apertura interfaccia
- armeria: sfogliare una carta ne annuncia l'effetto (bonus iniziale, spawn, grado richiesto se bloccata)
- completamento ripetuto: soddisfare di nuovo un obiettivo già sbloccato concede solo ``repeat_medal \<n\>`` medaglie (niente carta, onore o voce sblocco); le medaglie fanno avanzare comunque il grado
- opt-out mod: ``achievements_enabled 0`` in ``rules.txt`` nasconde la voce menu e salta carico / elaborazione post-partita
- ``I bonus ``starting_units`` IA in ``ai.txt`` non consumano popolazione`` (gli start mappa sì); ``starting_population`` è invariato
- dati: ``res/achievements.txt``, ``res/cards.txt``, ``res/titles.txt``; id TTS 5244–5367, ecc.
- documentazione: ``achievement-system.htm`` (``achievement-system.htm``)
- test: ``test_achievements.py``, ``test_cards.py``, ``test_titles.py``, ``test_card_loadout.py``

1.4.4.2
--------

Miratura counter IA (``counter_skill`` in ``ai.txt``):

- le unità computer usano ``mdg_vs`` / ``rdg_vs`` (e ereditarietà ``is_a``) nella scelta dei bersagli e nell'invio degli attacchi
- nuovo comando script ``counter_skill \<0-100\>``: ``0`` = ignora i counter (solo ``menace``), ``100`` = sceglie sempre il miglior counter; i valori intermedi mescolano entrambi
- tier vanilla in ``res/ai.txt``: beginner ``25``, intermediate ``50``, advanced ``75``, expert ``90``, nightmare ``100``; omesso in uno script mod default ``100``
- nuovi ``starting_resources`` / ``starting_units`` in ``ai.txt``: risorse e unità bonus aggiunte sopra lo start mappa per i computer invitati (stessa sintassi dei comandi mappa; applicati una volta all'avvio, non nel loop script)
- nuovo ``starting_population`` in ``ai.txt`` e mappe: tetto popolazione bonus (intero semplice, non ×1000) aggiunto sopra case/unità; ancora limitato da ``global_population_limit``
- start bonus vanilla: intermediate +50/+50 risorse; advanced +100/+100 e 2 footman 2 archer; expert +200/+200 e esercito 5/4/2; nightmare +400/+400 e esercito 8/6/4
- documentazione: ``doc_src/src/en/aimaking.rst``, ``doc_src/src/zh/aimaking.rst``
- test: ``test_ai_counter_targeting.py``, ``test_ai_loader_and_menu.py``, ``test_ai_start_settings.py``

1.4.3.9
--------

Tasti rapidi interfaccia a livelli (base globale + livello per modalità):

- un solo ``bindings.txt`` suddiviso in ``global_bindings.txt`` e sette file modalità (unit/building/command/skill/help/map/diplomacy); ordine di caricamento: globale → modalità corrente → ``cfg/bindings.txt`` → append mod
- cambio con tasti F: F1 unit↔building, F2 command↔skill, F3 inventory↔equipment, F4 help & query, F12 diplomacy, ESC entra/esci navigazione mappa; nome modalità annunciato al cambio
- il livello globale mantiene risorse (z/x/SHIFT z/c), movimento, salti casella, conferma comando, F9/F11, ecc.; i precedenti F1/F4 help e F12 diplomacy diretto entrano ora in modalità overlay dedicate
- modalità unità: lavoratori ``s``/``w`` (era ``d``/``e``); soldati 1–7 su ``d/e``…``;``/``p``; slot modalità edifici ``building1``–``building16`` (``d/f/g/h/j/k/l/;`` + ``e/r/t/y/u/i/o/p``)
- modalità comando 30 slot indice tasti; modalità mappa ``f/g/m/p`` cicla depositi/prati/passaggi sulla casella corrente (senza salti casella); ESC verso mappa annuncia il riepilogo casella e ripristina silenziosamente l'ultimo bersaglio mappa
- mod ``style.txt``: ``keyboard worker``, ``keyboard soldier1``–``7``, ``keyboard building1``–``16``; il corpo di ``bindings.txt`` è ora uno stub di compatibilità
- i sotto-schermi inventario/equipaggiamento/attributi chiamano ``restore_active_bindings`` all'uscita; i binding editor invariati
- tasti classici a file singolo: `````[general] layered_hotkeys = 0``` in ``user/SoundRTS.ini`` (default ``1`` = a livelli); oppure menu principale Options → Hotkey scheme — Layered hotkeys / Classic hotkeys (effettivo alla prossima partita); classico carica ``legacy_bindings.txt``, nessun livello modalità F, ESC non entra in navigazione mappa
- le mod possono personalizzare ogni schema: a livelli via ``ui/*_bindings.txt`` o append ``ui/bindings.txt``; classico via ``ui/legacy_bindings.txt`` o append ``ui/bindings.txt``
- documentazione: ``../player/layered-hotkeys.htm``, ``../player/layered-hotkeys.htm``
- test: ``test_layered_bindings.py``, ``test_map_browse_target_persist.py``

Campagne stile Age of Empires DE (single-player + coop):

- single-player: browser missioni (``synopsis``, cinque tier di difficoltà persistiti, capitoli completati/bloccati, riprova); HP/danno nemici scalano per tier (Standard + solo = 100%)
- coop: multigiocatore missione narrativa (slot giocatore + partner IA alleati, intro/cutscene/obiettivi condivisi, nessun trattato); difficoltà e numero umani scalano i nemici; TTS campagna caricato automaticamente per nomi luoghi localizzati
- vedi ``../player/campaign-menu.htm`` (``../player/campaign-menu.htm``)
- test: ``test_changelog_1429_coop_campaign_difficulty.py``, ``test_changelog_1429b_campaign_browser_difficulty.py``, ``test_changelog_1429c_coop_story_mission.py``, ``test_changelog_1429d_coop_player_slots.py``, ``test_coop_campaign_place_names.py``

1.4.3.8
--------

Campi di costruzione, obiettivi progressivi e tumori creep Zerg:

- ``build_field_radius`` (BFS a caselle) vs ``build_field_radius_m`` (metri da `` (x,y)``); i provider a metri dipingono marche quando ``build_field_persists`` / ``build_field_spreads`` — corregge i controlli costruzione creep a metri solo Hatchery
- Trigger ``register_objective`` registra i numeri primari per la vittoria senza F9/voce; la vittoria usa ``\_required_objective_numbers`` vs ``\_completed_objective_numbers`` (niente vittoria prematura quando gli obiettivi sono rivelati uno per uno)
- F9 / ``add_objective``: «Primary objective N:» con più obiettivi; due punti dopo il numero; un solo obiettivo omette il numero
- Mod StarCraft: Queen Spawn creep tumor / tumor Extend creep tumor; attr abilità ``summon_requires_build_field``, ``summon_requires_marked_field``
- documentazione: ``campaign/progressive-objectives.htm``, ``../player/starcraft-zerg-creep.htm``; ``modding.rst``, ``mapmaking.rst``
- test: ``test_build_rules.py`` (creep tumor), ``test_campaign_alliance_transfer_triggers.py`` (register_objective), ``test_objective_announce.py``

1.4.3.7
--------

Sistema di caccia ed etichette vocali fauna:

- Caccia stile Age of Empires: animali ``is_huntable`` lasciano depositi ``food_carcass``; i lavoratori li raccolgono; cervi/pecore fuggono; le pecore possono essere guidate (``can_herd`` / ``herdable``)
- Fauna annunciata come «animal» (es. «deer , animal»), non «neutral , NPC»; i riepiloghi casella usano un bucket animali separato
- Gli slot ``computer_only`` solo-fauna non entrano nell'alleanza ``"ai"`` (non con giocatori, creep ostili o altri branchi; slot misti invariati)
- Ctrl+Shift+F4 verso un giocatore solo-fauna dice «you are animal»; giocatori misti PNG + fauna dicono ancora «you are neutral NPC»
- Le mappe casuali spawnano fauna e frutteti vicino agli start; ``hunting_techniques`` migliora la raccolta carcasse
- documentazione: ``../player/hunting.htm``; sezione hunting di ``modding.rst``
- test: ``soundrts/tests/test_hunting.py``, ``test_hunting_herd.py``, ``test_wildlife_identification.py``, ``test_wildlife_alliance.py``

1.4.3.6
--------

Attacchi a raffica / sequenza (``damage_seq``):

- intervallo burst fisso: rules ``(interval …)`` ora rispettato (era hard-coded a 0,4 s)
- omettere ``(damage …)`` per suddividere automaticamente ``mdg`` / ``rdg`` base in parti uguali (supporta danno frazionario)
- ogni colpo in un burst attiva ``launch_mdg`` / ``launch_rdg``; elenca più ID suono in ``style.txt``
- rules base: nuovo ``repeating_crossbowman`` (upgrade da archer; stile Chu Ko Nu Age of Empires)
- test: ``soundrts/tests/test_damage_seq_burst.py``
- documentazione: ``../player/burst-attacks.htm``; sezione Combat system di ``modding.rst``

1.4.3.5
--------

IA di combattimento vs unità neutrali:

- le unità del giocatore in modalità ``offensive``, ``defensive`` o ``chase`` non attaccano automaticamente le unità
  neutrali (``computer_only ... neutral``)
- la modalità defensive non fugge quando sono presenti solo neutrali
- l'attacco forzato (``imperative`` go/attack, es. Ctrl+click sull'unità) funziona ancora
- i creep neutrali restano guard + contrattacco dal loro lato; vedi ``../player/unit-default-behavior.htm``

1.4.3.4
--------

Generatore procedurale di mappe casuali (RMG):

- Ingresso: menu principale Start a game → Random map; oppure Random map nell'elenco mappe crea-partita online
- Opzioni: template (standard/fast/macro/lanes), dimensione, numero giocatori, squadre 2v2, mostri, risorse, terreno, acqua, tesoro, seed, trattato
- Dopo la generazione, seed e codice di condivisione sono annunciati; F5/F6 li riproducono dalla cronologia vocale (ancora disponibili nel menu invita-IA)
- Importare il codice di condivisione salta i menu passo-passo; formato ``RMG1:…`` — vedi `Guida mappe casuali <randommap.htm>`_
- Gli input di testo nei menu (codice condivisione, seed, login, ecc.) supportano Ctrl+A/C/V/X seleziona tutto, copia, incolla, taglia
- Codice: ``soundrts/randommap.py``, ``soundrts/randommap_menu.py``; test ``soundrts/tests/test_randommap.py``

1.4.3.3
--------

Condizioni indicizzate (``killed_target`` / ``npc_has_item`` / ``unit_lost`` / ``building_lost`` / ``key_unit_killed``):

- Indice spawn globale (qualsiasi casella): ``(killed_target \<index\> \<type\> [enemy|ally])``, `` (npc_has_item \<index\> \<type\> \<item\>)``, `` (unit_lost \<index\> \<type\>)``, `` (building_lost \<index\> \<type\>)``, `` (key_unit_killed \<index\> \<type\>)``
- Indice casella: ``(killed_target \<square\> \<index\> \<type\>)``, `` (npc_has_item \<square\> \<index\> \<type\> \<item\>)``, ecc.
- Stesse regole di indice di ``killed_target`` / ``npc_has_item``; solo la N-esima unità/edificio spawnato in quella casella
- Esempio: ``(building_lost 1 townhall) (defeat)`` fallisce solo se il 1° municipio spawnato è distrutto (qualsiasi casella); `` (building_lost a1 1 townhall)`` è specifico di casella; `` (unit_lost 3 footman) (defeat)`` fallisce solo se muore il fante #3
- Demo: The Legend of Raynor capitolo 1; vedi ``campaign/unit-index.htm``
- Test: ``soundrts/tests/test_map_select_loss_triggers.py``

1.4.3.2
--------

Unità senza numero (rules.txt, ``no_number 1``):

- Si applica solo ai tipi unità con ``no_number 1``; le unità default (es. contadini) tengono sempre i numeri seriali («peasant 1 at a1»)
- Con ``no_number 1`` e una sola unità viva di quel tipo: nessun numero seriale («Guan Yu at a1», «knight leader at a1»)
- Con ``no_number 1`` e due o più di quel tipo: numeri seriali («Guan Yu 1», «Guan Yu 2»)
- I riepiloghi di gruppo, casella e battaglia seguono la stessa regola (es. «you control Guan Yu and 2 escort knights»)
- Vedi ``modding.rst``; esempi campagna ``raynor``, ``npc_knight_leader`` in ``The Legend of Raynor/rules.txt``

1.4.3.1
--------

Inventario ed equipaggiamento:

- Shift+V: zaino (tutti gli oggetti in inventario); Ctrl+V: equipaggiamento (armi e armature)
- mutuamente esclusivo con lo schermo proprietà Alt+V; richiede esattamente un'unità amica selezionata
- tasti in-schermo: frecce navigano, Invio equipaggia/usa, Shift+Invio diseqipaggia, Delete/Shift+Delete lascia, g legge l'intro
- modello oggetti unificato: ``class item`` con ``equippable_as_weapon 1`` / ``equippable_as_armor 1``; le stats si applicano all'equip
- ``weapons`` / ``armor`` iniziali che sono oggetti equipaggiabili entrano automaticamente in inventario; equipaggiati silenziosamente quando non c'è gear built-in di quel tipo e ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` è 1 (default; serve ``inventory_capacity`` > 0)
- legacy ``class weapon`` / ``class armor`` restano built-in (sola lettura nello schermo equipaggiamento)
- gear misto built-in + oggetto: built-in equipaggiato allo spawn; con ``spawn_weapons_equipped 1``, le armi oggetto restano nello zaino e non possono essere equipaggiate; lo switch built-in solo con built-in, oggetto solo con oggetto, niente cross-switch (stesso per armature)

Comportamento predefinito unità (rules.txt):

- ``ai_mode``: modalità IA iniziale — ``offensive``, ``defensive``, ``guard`` o ``chase`` (non ``patrol``)
- ``auto_gather`` / ``auto_repair``: auto-raccolta e auto-riparazione lavoratori all'avvio partita (default 1)
- ``auto_explore``: le unità mobili partono con auto-explore attivo (default 0)
- ``can_auto_explore 1``: il menu unità offre comandi abilita/disabilita auto-explore

Dare oggetti ai PNG:

- ordine ``give``: clic destro su unità non ostile, menu comandi, o scorciatoia ``g``
- il bersaglio serve ``receive_items 1``; whitelist opzionale ``accepted_items`` e filtro relazione ``accept_from``
- condizione trigger ``npc_has_item``; demo multigiocatore ``res/multi/give_demo.txt``; campagna cap. 14–16 (``The Legend of Raynor/14.txt``\ –``16.txt``) per consegna alleato/neutrale/nemico
- sintassi indice unità ``npc_has_item`` / ``killed_target`` (``\<square\> \<index\> \<type\>``); demo The Legend of Raynor capitolo 28; vedi ``campaign/unit-index.htm``

Vittoria per oggetto trovato:

- condizione trigger ``has_item`` controlla l'inventario del giocatore per un dato tipo oggetto (conteggio opzionale)
- l'oggetto deve restare in inventario (``consume_on_pickup`` non deve essere 1)
- esempio: The Legend of Raynor capitolo 17 (``lost_amulet``)

Trasporto su casella e consegna narrativa:

- condizione trigger ``has_brought_item``: un'unità del giocatore arriva a una casella trasportando un oggetto (senza drop)
- azione trigger ``remove_item``: rimuove e distrugge oggetti dagli inventari del giocatore; usare con ``cut_scene`` per consegna narrativa
- azione trigger ``do``: esegue più sotto-azioni in ordine (``if`` non può sostituirlo)
- esempio: The Legend of Raynor capitolo 18 (``mana_potion`` al santuario c3)

Oggetti a terra e condizioni composte:

- azione trigger ``remove_ground_item``: elimina oggetti a terra su una casella (es. rimuovere il tesoro dopo l'apertura)
- condizione trigger ``and``: vera solo quando ogni sotto-condizione è vera
- sintassi ``find``: casella prima del tipo, anche dentro ``not``; ordine sbagliato rende le condizioni quasi sempre vere
- esempio: The Legend of Raynor capitolo 20 (lasciare tesoro, poi raccogliere tutte le monete d'oro)

Trigger diplomazia campagna e trasferimento unità:

- azione trigger ``alliance_request``: un giocatore richiede alleanza; in campagna l'umano accetta con Ctrl+F4 (nessuna selezione bersaglio F12)
- condizioni trigger ``alliance_with`` / ``alliance_request_pending``
- azione trigger ``transfer_units`` (alias ``convert_units``, ``change_owner``): cambia proprietà unità tra giocatori
- azione trigger ``allied_assist``: le unità alleate combattono da sole (guard→chase); selettore unità opzionale per switch parziale
- azione trigger ``allied_control``: concede comando diretto sull'esercito di un alleato (intero alleato o unità selezionate); le unità non abbinate passano a chase
- azione trigger ``add_inventory_item``: mette oggetti nell'inventario unità (trasporto inter-capitolo, ricompense missione)
- azioni trigger ``set_ai_mode`` / ``set_yield_on_defeat``: toggle modalità IA runtime e duello-resa
- condizioni ``units_yielded`` / ``units_yielded_by``, ``has_entered``; azioni ``stop_all_units`` / ``release_yielded_units``: conteggi resa (filtro per attaccante), ingresso casella, cessate il fuoco, ripristino combattimento
- The Legend of Raynor capitoli 24–27 (arco alleanza del nord); vedi ``../player/campaign-northern-arc.htm``

Sintassi esclusione ``phase_targets``:

- un ``-`` iniziale esclude una corrispondenza (es. ``phase_targets -building`` = tutte le unità tranne gli edifici)
- inclusioni ed esclusioni possono essere mescolate (es. ``phase_targets soldier -footman``)

Ereditarietà esclusione ``is_a`` prefisso ``-``:

- es. ``is_a footman(-hp_max)`` è equivalente a ``is_a footman(apart hp_max)``
- esclusioni multiple: ``is_a footman(-hp_max -mdg)``

Bug corretti:

- corretta la perdita di selezione unità dopo un upgrade ``can_upgrade_to`` o un morph ``can_change_to``: ad esempio, un archer selezionato con g resta selezionato dopo l'upgrade a dark archer, senza riselezionare


1.4.3.0
--------

Bug corretti:

- corretto un grave bug di vittoria campagna: quando una mappa campagna aveva due o più computer nemici, completare gli obiettivi non terminava la partita; la causa era la mutazione della lista giocatori durante l'iterazione nel settlement di vittoria
- corrette unità e oggetti che sparivano da una casella per 4–5 secondi dopo che un'unità se n'era andata
- in campagna, F12 (alleanza dinamica) non seleziona più alcun bersaglio; i computer da script trigger non sono veri giocatori avversari
- i computer trigger promossi da ``(ai easy)`` e trigger simili sono annunciati come «NPC» invece del nome interno ``ai_timers``; la loro sconfitta non è più annunciata in campagna
- Ctrl+Shift+F4 annuncia ora i computer trigger come «NPC»


1.4.2.9
--------

- le mappe scaricate da un server mantengono il nome originale
- le mappe con lo stesso contenuto di una mappa locale non vengono riscaricate
- i replay multigiocatore sono memorizzati come ``replay1``, ``replay2``, ``replay3``, ecc.


1.4.2.8
--------

- piccolo boost di prestazioni dalle ottimizzazioni Cython
- computer neutrali: aggiungere la parola chiave ``neutral`` a una riga ``computer_only``; le IA neutrali non attaccano a meno di essere attaccate per prime
- ``player_start \<N\> \<square\>`` fissa la casella di spawn per il giocatore N (vedi la guida alla creazione mappe)


1.4.2.7
--------

- salvataggi e replay possono essere rinominati (qualsiasi lingua/caratteri): modifica i file in ``user/saves`` o ``user/replays``, oppure premi Shift+Invio su un file nel menu ripristina/replay
- Delete chiede conferma; Shift+Delete elimina subito


1.4.2.6
--------

- fino a 10 slot di salvataggio per mod; ogni mod ha i propri salvataggi, punti memoria e replay
- annullare una partita crea un punto memoria; «continue unfinished game» compare nel menu principale
- anche i file replay sono specifici per mod


1.4.2.5
--------

- ``can_advance`` per upgrade di fase (distinto da ``can_research``); mostrato nell'interfaccia proprietà
- la fase iniziale predefinita è visualizzata all'avvio partita quando un edificio ha ``can_advance``
- ``hide_locked_commands`` in ``def parameters`` nasconde i comandi i cui requisiti non sono soddisfatti


1.4.2.4
--------

- nuova ``class phase`` (progressione stile età): ``phase_targets``, ``phase bonus``, ``units_auto_upgrade``
- alleanza dinamica: ogni richiesta di alleanza ha ora il proprio cooldown


1.4.2.3
--------

- alleanza dinamica durante una partita (F12 / Shift+F12 seleziona bersaglio; F4 richiede; Ctrl+F4 accetta; Shift+F4 annulla/rifiuta/lascia); le alleanze pre-partita non possono essere cambiate in-game
- correzioni bug campagne cooperative


1.4.2.2
--------

- modalità trattato: pace per una durata scelta (fino a 20 minuti), poi guerra
- campagna cooperativa sui server: qualsiasi giocatore che completa gli obiettivi contribuisce alla squadra


1.4.2.1
--------

Bug corretti:

- i suoni di passaggio non ritardano più gli annunci di nome luogo e coordinate
- le unità non guadagnano più bonus velocità a ogni revival
- le modifiche di upgrade a cost, time_cost e population_cost persistono ora dopo la ricerca
- gli upgrade heal e harm non si applicano più a ogni tipo di unità
- altitudine unità aeree ripristinata al comportamento 1.3.8.1


1.4.2.0
--------

Bug corretti:

- le unità rianimate possono di nuovo ricevere ordini
- gli auto-attacchi non attivano più il danno di carica
- gli upgrade sconto non influenzano più le unità senza la tech di sconto
- lo splash di carica a terra non colpisce più le unità aeree
- i trasporti con capacità ≥ 99 non si caricano più da soli


1.4.1.9
--------

- gerarchia ``square_name`` fino a 3 livelli (provincia / città / distretto); il TTS annuncia i nomi entrando da un'altra regione
- ulteriori ottimizzazioni di prestazioni


1.4.1.8
--------

- le coordinate mappa usano ``x,y`` (es. ``1,1``) invece di lettera+numero; la notazione legacy è ancora accettata
- ``square_name`` per nominare le caselle; traduzioni in ``tts.txt``
- unità e risorse iniziali di fazione possono essere definite in ``rules.txt`` (le definizioni mappa hanno priorità)


1.4.1.7
--------

- sistema abilità unificato (``class skill``) con ``effect_target`` e ``effect_range``
- buff multi-stat, buff aura (``buff_radius``), parametri harm/heal/regen ampliati


1.4.1.6
--------

- i debuff possono essere definiti sulle armi
- corretto fallimento caricamento salvataggio


1.4.1.5
--------

- parola chiave ``intro`` in ``style.txt`` per le descrizioni unità
- percezione diagonale ripristinata
- corretta UI produzione su edifici non produttori


1.4.1.4
--------

- trigger 1.3.5.2 migrati; mappe td1–td3 giocabili


1.4.1.3
--------

- sistema armi e armature; cambio arma manuale (A / Shift+A / B+X); ``auto_weapon_switch``
- sistema oggetti migrato da 1.3.5.2
- muri e cancelli di nuovo edificabili


1.4.1.2
--------

- ``can_repair`` sui lavoratori; pathfinding unità d'acqua e mining sulla riva migliorati
- più attributi nell'interfaccia proprietà


1.4.1.1
--------

- interfaccia proprietà potenziata con navigazione interattiva (can_train, skills, research, can_build)
- ``can_repair_ships`` per lavoratori ed edifici; riparazione navi sulla riva (distanza 6) e auto-riparazione edifici (distanza 8)


1.4.1
------

- la vista RPG in prima persona è a 360°; precisione di movimento migliorata


1.4.0.9
--------

- guida modalità RPG in prima persona; zoom dinamico F8 da 3×3 a 15×15; navigazione consapevole del percorso


1.4.0.8
--------

- ``minimal_mdg`` / ``minimal_rdg`` rinominati di nuovo in ``minimal_damage``
- tasti rapidi abilità RPG (1–0) in modalità prima persona


1.4.0.7
--------

- tassi di colpo critico corretti; crazy-Mod giocabile


1.4.0.6
--------

- modalità spettatore sui server; suoni vittoria/sconfitta in multigiocatore corretti


1.4.0.5
--------

- parole chiave ``food`` sostituite con ``population`` (es. ``population_cost``)
- economia più ricca: edifici risorsa, coltivazione e produzione auto/manuale
- ``rpg_bindings.txt`` riservato per futura personalizzazione tasti RPG


1.4.0.4
--------

- ``auto_production`` / ``manual_production``; ``is_gather`` / ``is_create``; ``class resource`` separato da ``class deposit``


1.4.0.3
--------

- musica di sfondo fazione e di battaglia (``\<faction\>\_music``, ``\<faction\>\_battle_music``)


1.4.0.2
--------

- suoni seleziona/conferma/indietro menu; musica di sfondo e di battaglia per menu


1.4.0.1
--------

- meccaniche di carica e contro-carica; tassi di trigger buff ampliati
- nuove condizioni di sconfitta: ``unit_lost``, ``key_unit_killed``, ``key_units_killed``, ``units_lost``, ``buildings_lost``, ``has_killed``; ``killed_target`` e ``has_killed`` supportano ``enemy`` / ``ally``


1.4
----

- rifacimento combattimento: ``mdg`` + ``mdg_vs`` (additivo), crit, piercing, explode
- sistema eroe e XP da 1.3.5.2 integrato
- ``title`` / campagna / parametri mappa accettano stringhe tra virgolette; formato traduzione ``tts.txt``
- mappe avanzate non impacchettate in ``multi/`` supportate
- corretti suoni riprodotti digitando nomi corrispondenti nelle caselle di input


1.3.9.8
--------

- sistema buff/debuff da 1.3.5.2 integrato
- i nemici appaiono subito entrando nella loro casella


1.3.9.7
--------

- ``can_train`` con quantità; ``can_change_to``; correzione menu ``can_use_tech`` / ``can_use_skill``


1.3.9.6
--------

- cost/time_cost/population_cost percentuali sugli upgrade; display risorse decimali


1.3.9.5
--------

- filtri oggetti (tasti M / N); selezione lingua ``cfg/language.txt``


1.3.9.3
--------

- correzioni cover/dodge terreno; la ricerca si applica alle unità future; suoni splash hit rimossi temporaneamente


1.3.9.2
--------

- effetti upgrade su cost/time/population; suoni splash hit; attributi float nell'UI proprietà


1.3.9.1
--------

- proprietà splash ``\_vs``; suono ``falling`` ritardato; regola attacco altezza proiettile


1.3.9.0
--------

- ``extraction_time`` / ``extraction_qty`` ripristinati; interfaccia proprietà Alt+V con ``attributes_bindings.txt``


1.3.8.8
--------

- ``can_gather`` / ``gather_time`` / ``gather_qty`` sui lavoratori; ``is_rewards`` / ``rewards_resource``


1.3.8.7
--------

- ricompense risorse per uccisione/distruzione; rimborso su auto-demolizione


1.3.8.5
--------

- mappe specifiche per mod via ``mods/\<mod\>/multi/``


1.3.8.4
--------

- produzione risorse edifici (``is_production``, ``production_type``, ecc.)


1.3.8.3
--------

- ereditarietà ``is_a`` flessibile (selettiva, esclusione, multi-genitore)


1.3.8.2
--------

- cattura proprietà; ``mdg_projectile`` / cover/dodge terreno; uscita contenitori migliorata
- grande rifacimento combattimento: sistema ``mdg``/``rdg``/``mdf``/``rdf``; sequenze danno; ``class skill``; modalità guard/chase; refactor sistema suoni


1.3.8.1
--------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.8 o successiva
- server: 1.2-c12 o successiva

Principali cambiamenti da 1.3.8:

Bug corretti:

- in una partita ripristinata, il tasto R selezionava qualsiasi soldato (grazie a Marco Oros per la segnalazione)
- quando costruire un menu richiede troppo tempo, i tasti ripetuti si accumulavano
- speriamo di evitare qualsiasi glitch di volume quando viene creata una sorgente sonora
- le mappe personalizzate appariranno dopo le mappe ufficiali
- eseguire server.py non richiede alcun pacchetto


1.3.8
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.8 o successiva
- server: 1.2-c12 o successiva

Principali cambiamenti da 1.3.7:

- aggiunto tts_digit_coefficient in cfg/parameters.toml

Bug corretti:

- i percorsi tra terra e acqua saranno mantenuti se entrambe le caselle sono terra
- le unità fuggiranno più spesso verso la casella precedente
- gestione corretta dei file replay che non sono timestamp (grazie a dnl-nash)
- invio segnalazioni bug solo se il client è un eseguibile

Traduzioni:

- aggiunta traduzione bielorussa (grazie a Uladzimir)
- aggiornata traduzione slovacca (grazie a Marco Oros)


1.3.7
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.7 o successiva
- server: 1.2-c12 o successiva

Cambiamenti da 1.3.6:

Ora le unità possono attaccare dall'interno di veicoli o edifici:

- le unità a distanza possono attaccare come al solito
- le unità da mischia possono attaccare solo da terra e senza portata aggiuntiva
- le unità da mischia non possono attaccare da veicoli aerei
- nel gioco predefinito: le unità possono entrare in muri, cancelli e torri

Problemi risolti con i contrattacchi verso una casella vicina:

- le unità che non possono contrattaccare resteranno silenziose
- le unità difensive non contrattaccheranno

Altro:

- ripristinata la notifica «attack!»
- correzione bug: un'unità non entrava in un edificio se l'ordine era dato da un'altra casella
- corretto: ripristino partita
- gli attacchi inter-casella potrebbero funzionare meglio

Modding:

- aggiunto armor_vs
- ora «damage_vs» funziona con «is_a» (inclusi diversi livelli di «inheritance» e «inheritance» multipla)

Creazione mappe:

- mappe ufficiali «multi» spostate in res/multi
- le «folder maps» multigiocatore devono essere zipate per essere giocate online
- rimosso il file «maperror.txt» (l'informazione è già nel messaggio di errore in-game).

Cambiamenti al formato campagna:

- mods.txt sostituito con la parola chiave «mods» in campaign.txt
- parola chiave «title» in campaign.txt
- nuovo vincolo: una mappa missione complessa deve essere memorizzata come file zip


1.3.6
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.6 o successiva
- server: 1.2-c12 o successiva

Cambiamenti da 1.3.5:

Comportamento unità:

- bug corretto: le unità offensive vicine contrattaccheranno di nuovo automaticamente (si sposteranno nella casella dell'attaccante e poi torneranno alle posizioni di partenza)
- bug corretto: le unità difensive fuggiranno di nuovo

Interfaccia:

- la descrizione delle unità controllate sarà meno confusa
- seguito di gruppo migliorato (tasto spazio): l'interfaccia di solito seguirà il fronte del gruppo
- bug corretto: in style.txt, noise_if_very_damaged non suonava mai
- bug corretto: SAPI non funzionava

Acqua:

- d'ora in poi, il gioco non creerà percorsi anfibi (risolve il seguente problema: se il percorso più breve verso la destinazione includeva una casella d'acqua, le unità di terra camminavano in acqua e morivano)
- problema risolto: un mago poteva richiamare unità d'acqua su caselle non-acqua (Ora un mago richiamerà le unità d'acqua sulla casella d'acqua adiacente più vicina.)

Multigiocatore:

- avviare un server non privato auto-configurerà il router (funziona solo se UPnP è attivato sul router; la configurazione è rimossa automaticamente dal router dopo 20 minuti di inattività)
- configurazione più facile del server standalone
- auto-discovery server locale via broadcast UDP (Il server locale apparirà nel menu «choose a server in a list».)
- bug corretto: nelle partite multigiocatore, un giocatore non-admin poteva impostare una velocità più lenta

Traduzioni:

- aggiornate le traduzioni brasiliano-portoghese, cinese, ceca, italiana e slovacca

Creazione mappe:

- quando possibile, emettere un avviso invece di un errore mappa
- bug corretto: in alcuni casi, un trigger selezionava più unità di quelle specificate. Ad esempio, se ci sono 3 draghi e molti fanti in a1, (a1 10 dragon footman) selezionava 3 draghi e 7 fanti.


1.3.5
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.5 o successiva
- server: 1.2-c12 o successiva

Cambiamenti da 1.3.4:

- bug corretto: non si poteva salvare una partita con terreno
- corretto: il suono di colpo non veniva emesso se uccideva il bersaglio
- corretto: il gioco si bloccava se non c'era abbastanza spazio in una casella per creare un'unità

Internazionalizzazione:

- convertiti tutti i file tts.txt in UTF-8 con firma BOM. La codifica è ancora definita esplicitamente nella prima riga come UTF-8. La firma BOM potrebbe aiutare alcuni editor di testo a selezionare UTF-8 automaticamente.
- userà sempre UTF-8 (o ASCII) per i file di testo diversi da tts.txt (rules.txt, style.txt, ecc.)
- aggiornata traduzione spagnola (grazie a Oscar Corona)


1.3.4
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.4 o successiva
- server: 1.2-c12 o successiva

Cambiamenti da 1.3.3:

- probabilmente corretta la sintesi vocale in alcuni altri casi (segnalate se ancora non riuscite ad avviare il client)
- ripristinati salvataggio e ripristino (sembra funzionare, ma fate attenzione)
- ripristinate risorse e tech infinite per «aggressive computer 2» (più interessante)

Multigiocatore:

- il client ricorderà l'elenco server scaricato in precedenza e lo userà se il metaserver è temporaneamente giù
- in «enter the IP address of the server», inserire un indirizzo IP vuoto selezionerà il vostro computer (non serve digitare: «localhost»)
- server standalone: rimossa la dipendenza da pygame

Interfaccia:

- comando console: «a u_recall» aggiungerà l'upgrade recall al giocatore corrente
- bug minore corretto: l'interfaccia non seguiva un'unità dentro un trasporto (se l'unità era in modalità follow prima di essere trasportata)

Internazionalizzazione:

- aggiornata traduzione italiana (grazie a Luigi Russo)

Campagna principale:

- aggiunto capitolo 12, una mappa piccola per mostrare come funzionano le foreste dense (la regola è: «qualsiasi percorso tra due foreste dense è bloccato»)

Suggerimento: per controllare rapidamente i miglioramenti in un capitolo specifico di una campagna già giocata:

- premete il tasto «console» sotto Escape e premete «v» e Invio per una vittoria istantanea
- oppure modificate user/campaigns.ini: in [single_campaign] «chapter = 12» ad esempio


1.3.3
------

Per le partite multigiocatore, questa versione richiede:

- client: 1.3.3 o successiva (se compatibile)
- server: 1.2-c12, 1.3.0, 1.3.1, 1.3.2, 1.3.3 o successiva (se compatibile)

Cambiamenti da 1.3.2:

- bug corretto: un'unità non si fermava dopo aver usato un'abilità che richiedeva di avvicinarsi (deadly fog, exorcism...) e si muoveva verso il nemico...
- bug corretto: il gioco richiedeva un bersaglio per un'abilità centrata sul caster (ad esempio: raise dead)
- bug corretto: l'acqua non poteva essere vista da terreno basso (ad esempio nella mappa jl7)

L'interfaccia mappa dovrebbe risultare più naturale:

- muoversi nella mappa non causerà collisioni se controllate un'unità volante
- muoversi nella mappa non causerà collisioni se state definendo il bersaglio di un ordine recall (ad esempio)
- rimosse le collisioni tra acqua e terreno basso

Foreste dense:

- bug corretto: le foreste dense creavano percorsi quando venivano sgomberate (anche se non c'erano percorsi prima)
- ora le foreste sono dense se hanno almeno 7 woods (invece di 3)
- mappa multigiocatore 8: aggiornata (7 woods) e migliorata (economia più veloce)
- editor: palette terreno aggiornata (foresta densa se almeno 7 woods)

Internazionalizzazione:

- bug corretto: le mappe con caratteri non US-ASCII non potevano essere lette su piattaforme che usano GBK o UTF-8 di default (ora le mappe sono sempre lette come UTF-8 e gli errori sono sostituiti con «?»)
- convertite le seguenti mappe in UTF-8: bs2, can1, qc1, qc2 e qc3
- aggiornata traduzione polacca (grazie a Patryk Mojsiewicz)

Piccoli cambiamenti nella campagna principale:

- capitolo 9: con il bug «deadly fog» corretto, i necromanti dovrebbero essere più facili da gestire
- capitoli 5 e 10 leggermente migliorati

Suggerimento: per controllare rapidamente i miglioramenti in un capitolo specifico di una campagna già giocata:

- premete il tasto «console» sotto Escape e premete «v» e Invio per una vittoria istantanea
- oppure modificate user/campaigns.ini: in [single_campaign] «chapter = 11» ad esempio


1.3.2
------

Cambiamenti da 1.3.1:

Cambiamenti principali:

- il menu «choose a server» includerà qualsiasi server con una versione server compatibile (non solo la stessa versione) così i server non dovranno essere aggiornati così spesso
- i client compatibili con versioni diverse potranno giocare insieme
- i server «nearest» appariranno per primi nel menu «choose a server» (server con il ritardo di risposta più piccolo)
- il tempo impiegato per verificare se un server è disponibile sarà indicato (espresso in millisecondi) nel menu «choose a server» per confronto
- i server non disponibili non appariranno nel menu «choose a server»

Cambiamenti minori:

- leggermente ridotta la verbosità di server.log
- migliorata la guida al server standalone (ancora non perfetta però)
- aggiunte «release notes» alla documentazione

1.3.1
------

Cambiamenti da 1.3.0:

- probabilmente corretto: il gioco non partiva su Windows 7 (ImportError: DLL load failed while importing _socket)
- corretto: a volte il gioco non partiva finché non si eliminava la cartella «gen_py» in «appdata\local\Temp» (AttributeError: module 'win32com.gen_py...' has no attribute 'CLSIDToClassMap')
- corretto: poteva mancare vcruntime140.dll
- corretto: non si riusciva a ottenere l'elenco dei server
- corretto: premere A si comporta come prima e premere Control+A selezionerà solo gli ordini inattivi

1.3.0
------

Cambiamenti da 1.2-c12:

Cambiamenti principali:

- solo muri e cancelli possono essere costruiti sulle uscite (o qualsiasi edificio «buildable on exits only»)
- ora una torre può essere costruita solo al centro di una sotto-casella, e solo una torre per sotto-casella. La posizione di una torre può essere selezionata in diversi modi:

  - in modalità zoom: seleziona la sotto-casella corrente (deve essere libera)
  - in modalità casella: seleziona qualsiasi sotto-casella libera, partendo da quella centrale
  - se è selezionato un oggetto: seleziona la sotto-casella che lo racchiude (deve essere libera)

- ora lo screen reader è il TTS predefinito

Cambiamenti tecnici:

- migrato a Python 3
- sostituiti tutti i TTS con accessible_output2 (patchato per supportare Linux)

Bug corretti:

- non si poteva controllare un'unità resuscitata che era in un gruppo
- un lavoratore che aveva rimandato costruzione o raccolta per eliminare un intruso non tornava al suo compito e lo completava sul posto
- un'unità poteva vedere un plateau dal basso
- un'unità non poteva vedere in diagonale
- non si poteva selezionare una casella come bersaglio per costruire un cancello (verrà selezionata un'uscita libera)

Miglioramenti interfaccia:

- modalità zoom: validare un ordine di costruzione di un muro (o un cancello) senza selezionare un bersaglio specifico selezionerà automaticamente l'uscita locale (se non è bloccata)
- tab selezionerà prima qualsiasi nemico
- premere escape quando è selezionato un bersaglio selezionerà la casella corrente
- bug corretto: ora entrare o uscire dalla modalità zoom selezionerà la mini-casella o casella come bersaglio (invece di mantenere il bersaglio selezionato)
- aggiunte virgole in alcuni messaggi (per chiarezza)
- riepilogo nemici più breve
- bug corretto: diceva «building site» e non il tipo di edificio
- bug corretto: in modalità zoom, un ordine predefinito per un edificio non impostava il punto di raduno sulla sotto-casella ma sulla casella
- bug corretto: una partita in pausa non usciva
- bug corretto: premere Space dirà gli ordini esatti anche quando alcune unità hanno ordini diversi (Molto utile per controllare quanti lavoratori stanno raccogliendo oro, legno, ecc. (premendo D). Potrebbe essere utile sapere quante unità in un gruppo si stanno muovendo e quante sono arrivate. Premere Control + Shift + S darà un riepilogo completo degli ordini di soldati e lavoratori.)
- in modalità costruzione, tab selezionerà i prati prima delle uscite
- la descrizione di un ordine di pattuglia riepilogherà tutti i waypoint
- bug corretto: premere Tab selezionava le uscite bloccate
- bug corretto: non è più possibile costruire un altro muro sulla stessa uscita
- modalità zoom: se non si trova terreno edificabile mentre un ordine di costruzione è stato validato su una sotto-casella, verrà sollevato un errore (invece di cercare terreno edificabile nella casella che la racchiude
