
Guida al modding
::::::::::::::::

.. contents::

mods
-----

Le regole del gioco e l’aspetto del gioco possono essere modificati dalle mod.

Una mod è una cartella che può contenere rules.txt, ai.txt, ui (e le relative versioni localizzate). La struttura dell’albero è la stessa della cartella "res".

Le mod sono memorizzate nella cartella "mods" della cartella principale o nella cartella "mods" della cartella utente. Per essere attivata, una mod deve essere referenziata nel parametro "mods =" in SoundRTS.ini.
Ad esempio: mods = soundpack,mymod,my_other_mod

Il file rules.txt applicherà una patch al file predefinito. Ad esempio, un rules.txt con queste 2 righe: "def peasant" e "decay 20" farà sparire ogni contadino dopo 20 secondi.

Localizzazione delle mod (ui-xx)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Le cartelle delle mod rispecchiano l’albero ``res``. Aggiungi cartelle localizzate accanto a ``ui/`` (``ui-zh``, ``ui-fr``, ``ui-de``, ``ui-it``, ecc.). Il gioco carica la lingua da ``cfg/language.txt`` (o dalla locale di sistema); le voci mancanti ripiegano su ``ui/tts.txt``.

Layout consigliato (``mods/mymod/``)::

    ui/style.txt          ; title 7000
    ui/tts.txt            ; 7000 Pig Farm
    ui-zh/tts.txt         ; 7000 猪圈
    ui-fr/tts.txt         ; 7000 Ferme à porcs
    ui-it/tts.txt         ; 7000 Fattoria di maiali
    mod.txt               ; opzionale: dipendenze e titolo nel menu (sotto)

Cosa puoi tradurre (una volta che la mod è attiva):

- Nomi di unità/edifici/fazioni: ``title \<ID\>`` in ``style.txt`` + lo stesso ID in ogni ``tts.txt``
- Introduzione delle unità: ``intro \<ID\>`` + ``tts.txt``
- Mappe/campagne dentro la mod: ID TTS ``title``/``intro`` della mappa; le cartelle campagna possono usare ``title`` in ``campaign.txt`` (come le campagne in ``res/single``)
- Frasi intere: in ``tts.txt``, ``english phrase = frase tradotta``

Nome visualizzato della mod nel menu (Opzioni → Mod, da 1.4.2.4):

Aggiungi una riga ``title`` in ``mod.txt``, stessa sintassi di ``campaign.txt`` — ID TTS o parole separate da spazio::

    title 7100

Definisci quell’ID in ``ui/tts.txt`` e in ogni ``ui-xx/tts.txt`` (es. ``7100 Orc Faction Mod`` / ``7100 Mod fazione orchi``). Senza ``title``, viene pronunciato il nome della cartella.

In alternativa, mappa i nomi delle cartelle tramite voci di frase nel ``res/ui-it/tts.txt`` globale o in una piccola mod di traduzione, es. ``crazyMod9beta10 = Mod pazza``.

Note: ``rules.txt`` / ``ai.txt`` non sono localizzati. Lo ``ui-xx/style.txt`` localizzato nelle sottocartelle di mappa/campagna potrebbe non caricarsi, ma ``ui-xx/tts.txt`` in quelle cartelle sì. Anche i soundpack (mod senza ``rules.txt``) supportano ``title`` in ``mod.txt`` e ``tts.txt`` localizzati in Opzioni → Soundpack.

Esempi in questo repository: ``mods/orc/``, ``mods/prismalab/ui-fr/``.

Maggiori dettagli: `Internazionalizzazione delle mod <mod-i18n.htm>`_.

clear
>>>>>

Per sostituire rules.txt o style.txt invece di fare patch, usa il comando "clear" in cima al file. Non funziona con ai.txt,
e comunque non serve, perché in ai.txt il comando def riscrive la definizione dell’IA.

is_a
>>>>

Mentre in style.txt "is_a" è un modo per ereditare tutte le proprietà di un’altra definizione,
in rules.txt "is_a" serve anche a garantire che un keep o un castle permettano ciò che permetterebbe un town hall.

Nota: gli alberi di ereditarietà in style.txt e in rules.txt non devono necessariamente coincidere.

le regole
----------

Da SoundRTS 1.1, le regole del gioco sono memorizzate in un file chiamato rules.txt.

faction
>>>>>>>

Ogni fazione è definita in rules.txt. Ad esempio::

	def orc_faction
	class faction

Nota: il nome "orc_faction" termina con "_faction" solo per evitare conflitti di nomi. Il suffisso "_faction" non è obbligatorio finché il nome è unico.

unit
>>>>

Nota: un’unità può essere anche un edificio.

count_limit
============

Novità in SoundRTS 1.2 alpha 10.

`count_limit <valore>`

Il valore predefinito è 0 (nessun limite).
Quando il limite è attivo, un tipo di unità che lo raggiunge non può essere addestrato,
costruito, evocato, rianimato, resuscitato o aggiunto da un trigger (add_unit).
La conversione però non è influenzata.

mdg_projectile / rdg_projectile
=================================

Novità in SoundRTS 1.3.8.2. Restrizione terreno basso vs alto aggiunta in 1.3.9.1.
Sostituisce il deprecato ``is_ballistic``.

``mdg_projectile 0|1``

``rdg_projectile 0|1``

Il valore predefinito è 0. Quando è impostato a 1, il tipo di attacco corrispondente è trattato come
proiettile:

- Su terreno alto, l’unità guadagna portata extra attaccando bersagli a quota inferiore
  (+1 casella per livello di altezza)
- Le unità non-proiettile non possono attaccare bersagli a terra su terreno alto dal basso,
  indipendentemente dalla portata

Migrazione: le mod che usavano ``is_ballistic 1`` dovrebbero usare ``rdg_projectile 1`` (a distanza) o
``mdg_projectile 1`` (proiettili in mischia come le catapulte); ogni tipo di attacco si configura
separatamente.

Esempio di proiettile a distanza::

    def archer
    rdg 3
    rdg_range 4
    rdg_projectile 1

is_teleportable
================

Novità in SoundRTS 1.2 alpha 9.

``is_teleportable 1``

L’unità (o edificio) è influenzata dall’effetto di teletrasporto o dall’effetto di richiamo.

hp_regen
=========

Novità in SoundRTS 1.2 alpha 11

`hp_regen <tasso di rigenerazione dei punti ferita>`

Ad esempio, con "hp_regen 0.15", l’unità recupera 0,15 punti ferita al secondo.

mana_start
===========

Novità in SoundRTS 1.2 alpha 10.

``mana_start 50``

Nell’esempio, l’unità inizierà con 50 mana invece di mana_max. Il valore predefinito di mana_start è 0. Se mana_start è 0 o negativo, viene usato mana_max.

provides_survival
==================

Novità in SoundRTS 1.2 alpha 9.

``provides_survival 1``

Avere almeno un’unità (o edificio) con "provides_survival" uguale a 1 impedisce a un giocatore di perdere in una partita multiplayer (non in una campagna single player). Il trigger interessato è "no_building_left". Per impostazione predefinita solo gli edifici hanno questa proprietà impostata a 1. I cantieri di costruzione hanno questa proprietà impostata a 0 e non può essere cambiata.

victory_time
=============

Novità in SoundRTS 1.4.5.8.

``victory_time <secondi>``

Il valore predefinito è 0 (nessun timer di vittoria). Se è maggiore di 0 su un edificio **completato**, il conto alla rovescia parte non appena l’edificio esiste. Se il timer arriva a zero e l’edificio è ancora in piedi, vince il proprietario (e il campo di vittoria alleata). Distruggere l’edificio annulla quel conto alla rovescia.

Si applica a qualsiasi tipo ``class building``, non solo alla Meraviglia vanilla. Esempio:

::

    def wonder
    class building
    cost 100 120
    time_cost 900
    hp_max 2500
    requirements imperial_age
    count_limit 1
    victory_time 300

Vanilla include ``wonder`` con ``victory_time 300`` (5 minuti dopo il completamento). Voci: TTS 5720 (avvio), 5721 (annullamento), 5722 (rimanente).

storage_bonus
==============

`storage_bonus <bonus per risorsa 0> <bonus per risorsa 1> ...`

Ad esempio, "storage_bonus 0 1" darà un bonus +1 per il legno (il secondo tipo di risorsa).

Il bonus va al proprietario dell’unità.
Il bonus non si accumula: per ogni tipo di risorsa si applica solo il bonus più alto.

damage_vs
==========

Nota: da SoundRTS 1.4 il sistema unico ``damage`` / ``armor`` è stato sostituito dal
sistema separato mischia/distanza (``mdg`` / ``rdg`` / ``mdf`` / ``rdf`` ...). Vedi `Sistema di combattimento
(da 1.4)`_ sotto. La documentazione legacy di ``damage_vs`` è mantenuta per le mod più vecchie.

(danno contro unità specifiche)

`damage_vs [<elenco di nomi di tipo> <danno>] ...`

Definisce un danno specifico contro alcuni tipi di unità.
Il valore predefinito è definito in unit.damage.

Esempio di un tipo di picchiere più efficiente contro un cavaliere
 e meno efficiente contro un fante o un contadino:

`damage 2 ; danno predefinito`

``damage_vs knight 7 footman peasant 1``

ability
>>>>>>>

Nota: da SoundRTS 1.4, le abilità sono unificate sotto ``class skill`` (vedi `Abilità (class
skill)`_ sotto). Le proprietà ``effect`` documentate qui si applicano ancora alle skill e alle
definizioni ``class effect``.

effect
=======

`effect <tipo di effetto> [parametri]`

Valore predefinito: (nessuno)

Un effetto è una proprietà di un’abilità. Quando un’abilità è usata da un’unità, l’effetto avrà luogo a meno che non sia stato indicato alcun tipo di effetto.

Proprietà aggiuntive possono modificare un effetto: effect_target_ e effect_range_.

apply_bonus
^^^^^^^^^^^^

`effect apply_bonus <nome proprietà>`

Aumenta la proprietà delle unità interessate. Il valore è definito nella proprietà dell’unità chiamata "<nome proprietà>_bonus".
Ad esempio, "effect apply_bonus damage" cercherà una proprietà chiamata "damage_bonus" nella definizione di ogni unità interessata.
In questo modo, unità che beneficiano dello stesso upgrade possono avere valori di bonus diversi.

bonus
^^^^^^

`effect bonus <nome proprietà> <valore>`

Aumenta del valore indicato la proprietà delle unità interessate.

Almeno le seguenti proprietà dovrebbero funzionare: damage, armor, range, heal_level, speed, hp_max (le unità già esistenti però non avranno i loro hp aggiornati a hp_max).
food_cost e food_provided probabilmente non funzionano correttamente.

conversion
^^^^^^^^^^^

``effect conversion`` (nessun parametro)

Sposta il bersaglio nell’esercito del lanciatore.

Se il bersaglio non è un nemico del lanciatore, non succederà nulla.

Valori ammessi per le proprietà correlate:

* effect_target: ask
* effect_range: square, nearby, anywhere

TODO: aggiungere un <limite> così che le unità in una casella bersaglio siano scelte (invece di dover bersagliare un’unità)

raise_dead
^^^^^^^^^^^

`effect raise_dead <durata (in secondi)> <tipi di unità e numeri>`

Crea le unità richieste nella casella bersaglio a partire dai cadaveri nella casella, nell’ordine dell’elenco delle unità. Se non ci sono abbastanza cadaveri, la fine dell’elenco non sarà creata. Le unità spariranno dopo <durata> secondi, a meno che <durata> non sia impostata a 0.

Se non c’è alcun cadavere nella casella bersaglio, l’ordine non sarà eseguito.

Valori ammessi per le proprietà correlate:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

recall
^^^^^^^

``effect recall`` (nessun parametro)

Simile al teletrasporto. Teletrasporta le unità del giocatore dalla casella bersaglio alla casella del lanciatore. Gli edifici non sono influenzati. Anche le unità alleate non lo sono.

Se non c’è alcuna unità nella casella bersaglio, l’ordine non sarà eseguito.

Valori ammessi per le proprietà correlate:

* effect_target: ask, random
* effect_range: nearby, anywhere

resurrection
^^^^^^^^^^^^^

`effect resurrection <limite>`

Resuscita i cadaveri dell’esercito del lanciatore che giacciono nella casella bersaglio, con un massimo di <limite> unità resuscitabili. I cadaveri più vecchi sono resuscitati per primi. I punti ferita sono ripristinati a un terzo del massimo.

Se non c’è alcun cadavere di un’unità dello stesso esercito nella casella bersaglio, l’ordine non sarà eseguito.

Valori ammessi per le proprietà correlate:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

summon
^^^^^^^

`effect summon <durata (in secondi)> <tipi di unità e numeri>`

Crea le unità richieste nella casella bersaglio e le aggiunge all’esercito del lanciatore. Le unità evocate spariranno dopo <durata> secondi, a meno che <durata> non sia impostata a 0.

Attributi opzionali della skill per i controlli di piazzamento (esempio tumore creep di StarCraft)::

    summon_requires_build_field creep
    summon_requires_marked_field 1

``summon_requires_marked_field 1`` richiede una casella di build-field marcata (non solo live). Omettilo quando basta il campo live (Queen spawn tumor).

deploy
^^^^^^^

``effect deploy \<durata (secondi)\> [\<conteggio\>] \<tipo di effetto\>``

Piazza un’entità ``class effect`` sulla casella bersaglio (danno ad area, zona di cura, detector, ecc.). Scompare dopo la durata indicata. A differenza di ``effect summon``, serve solo per definizioni ``class effect``; la UI degli attributi mostra le statistiche harm/heal invece di "summon".

Esempi::

    effect deploy 5 sc_nuclear_blast
    effect deploy 3 sc_psi_storm_fx

Conteggio opzionale (più entità effetto sulla stessa casella)::

    effect deploy 5 2 greek_fire

Supporta anche ``summon_requires_build_field`` / ``summon_requires_marked_field``.

Valori ammessi per le proprietà correlate:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

harm_target (da 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^

Danno su bersaglio singolo. Due forme:

* **Danno vero fisso** (ignora l’armatura): ``effect harm_target <valore>``
* **Pipeline di combattimento** (armatura, critico, splash, ecc.): ``effect harm_target mdg`` o ``effect harm_target rdg``

Le statistiche di combattimento non nulle sulla skill sovrascrivono il lanciatore. Vedi ``skill_lipi`` / ``skill_lipi_mdg`` in ``mods/wuxia/rules.txt``.

Usa ``harm_target_type`` per filtrare i bersagli (solo nemici per impostazione predefinita). Vedi `Guida alle abilità <skills-and-effects.htm>`_.

harm_area (da 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^

Danno ad area:

* **Danno vero fisso**: ``effect harm_area <danno> <raggio>``
* **Pipeline di combattimento**: ``effect harm_area mdg <raggio>`` o ``effect harm_area rdg <raggio>``

Il raggio può essere omesso (usa ``effect_radius`` della skill). Esempi: ``skill_heng_sao``, ``skill_heng_sao_mdg`` (mod wuxia).

burst (da 1.4.4.6)
^^^^^^^^^^^^^^^^^^

Colpi combo di skill (**non** uguali alle raffiche ``damage_seq`` delle unità; vedi `burst-attacks.htm <../player/burst-attacks.htm>`_)::

    effect burst mdg <conteggio> (interval <sec>) (window <sec>)
    effect burst rdg <conteggio> (delays <t1> <t2> …)

Il danno usa ``mdg`` / ``rdg`` della skill o del lanciatore. Esempio: ``skill_jifengci`` (mod wuxia).

push (da 1.4.4.6)
^^^^^^^^^^^^^^^^^

``effect push <distanza>`` — respinge un nemico e trova una casella percorribile. Esempio: ``skill_moli_dan`` (mod wuxia).

buffs / debuffs (tramite skill)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``effect buffs <buff> …`` / ``effect debuffs <debuff> …``

Applica buff o debuff al bersaglio (``debuffs`` solo sui nemici). Non esiste ``effect reflect``; usa ``reflect_percent`` sul buff e applica con ``effect buffs`` (wuxia ``b_douzhuan``).

Riferimento completo: `Guida alle abilità <skills-and-effects.htm>`_.

teleportation
^^^^^^^^^^^^^^

``effect teleportation`` (nessun parametro)

Sposta le unità del giocatore nella casella del lanciatore sulla casella bersaglio. Gli edifici non sono influenzati. Anche le unità alleate non lo sono.
   
Se la destinazione è la stessa della casella del lanciatore, non verrà fatto nulla.

Valori ammessi per le proprietà correlate:

* effect_target: ask, random
* effect_range: nearby, anywhere

effect_target
==============

`effect_target <metodo di selezione>`

Determina come sarà selezionato il bersaglio.

Valore predefinito: self

Valori possibili:

* self: il bersaglio sarà il lanciatore (o la posizione del lanciatore se il bersaglio deve essere un luogo)
* ask: l’interfaccia utente chiederà un bersaglio
* random: il gioco sceglierà una casella casuale come bersaglio

effect_range
=============

`effect_range <distanza>`

Determina la distanza tra il lanciatore e il bersaglio.

Valore predefinito: 6

Valore speciale: inf (infinito)

Se la distanza attuale è maggiore di quella richiesta, il lanciatore cercherà di spostarsi in un luogo più vicino e usare l’abilità da lì.

effect_radius
==============

`effect_radius <distanza>`

Determina il raggio dell’area di effetto. Il centro dell’area è il bersaglio.

Valore predefinito: 6

Valore speciale: inf (infinito)

Sistema di combattimento (da 1.4)
---------------------------------

Da 1.4, il danno finale è additivo: ``final_mdg = mdg + mdg_vs`` (e lo stesso per
``rdg``, ``mdf``, ``rdf``). Quando il danno base è 0 e ``minimal_damage`` è 0 in
``def parameters``, l’unità non attaccherà.

Proprietà principali mischia/distanza:

- ``mdg`` / ``rdg``: danno base
- ``mdg_vs`` / ``rdg_vs``: bonus contro tipi di unità specifici
- ``mdf`` / ``rdf``: difesa
- ``mdg_range`` / ``rdg_range``, ``mdg_cd`` / ``rdg_cd``, ``mdg_ready`` / ``rdg_ready``
- ``mdg_projectile`` / ``rdg_projectile``: flag proiettile (bonus portata da terreno alto, regole basso vs alto)
- ``mdg_splash`` / ``rdg_splash``, ``mdg_radius`` / ``rdg_radius``, ``mdg_splash_decay``
- ``mdg_targets`` / ``rdg_targets``: ``ground``, ``air``, ``unit``, ``building``, o un nome di tipo
- ``mdg_crit`` / ``rdg_crit``, ``mdg_crit_rate`` / ``rdg_crit_rate``, ``crit_vs``
- ``mdg_piercing`` / ``rdg_piercing`` (percentuale di armatura ignorata), ``piercing_vs``
- ``mdg_explode`` / ``rdg_explode``, ``exp_dgf``, ``exp_hp_cost``, ``mdg_explode_vs``
- Modificatori per **terreno dell’attaccante** (da 1.4.5.0): ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``; stessa sintassi di ``speed_on_terrain`` — vedi ``building-land-terrain.rst`` *Modificatori di combattimento delle unità sul terreno*

Menace automatica / priorità di bersaglio (da 1.4.5.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Il ``menace`` di un’unità non è più solo il danno. Se rules non imposta un valore
assoluto, il motore usa un **punteggio di combattimento multidimensionale** per:

- Scelta automatica del bersaglio (minaccia più alta prima; giocatori computer
  non ``timers`` possono anche mescolare ``mdg_vs``/``rdg_vs`` con
  ``counter_skill`` — vedi ``aimaking.rst``)
- Somme di minaccia nemica per casella e decisioni IA correlate

**Dimensioni** (arma primaria = il maggiore tra ``mdg`` / ``rdg``):

- Danno, precisione (``mdg_cover``/``rdg_cover``, 0 = 100%%), cooldown
  (``*_cd``), wind-up (``mdg_ready``/``rdg_ready`` — non il ``*_delay`` balistico)
- HP (``hp`` corrente, altrimenti ``hp_max``), armatura (``max(mdf, rdf)``),
  schivata (``max(mdg_dodge, rdg_dodge)``)
- Portata d’attacco, velocità di movimento

In sintesi: DPS effettivo (danno × hit / (cd + ready)), poi sopravvivenza e
fattori di portata/velocità.

**Override opzionali in rules** (def unità):

======= ================= ============================================================
Campo     Tipo              Significato
======= ================= ============================================================
``menace`` assoluto         Minaccia fissa; **non** segue gli upgrade; sostituisce l’auto
``menace_mult`` peso (1)    Moltiplica la base multi-dim (scala ancora con le stat)
``menace_vs`` assoluto vs   Minaccia fissa verso quel tipo di osservatore / ``is_a``
``menace_mult_vs`` peso vs  Base multi-dim × peso verso quell’osservatore
======= ================= ============================================================

Ordine di lookup (``menace_versus``): ``menace_vs`` → ``menace_mult_vs`` →
``menace`` / ``menace_mult`` / punteggio automatico globale.

Esempio::

    def knight
    mdg 6
    menace_mult 1.5

    def archer
    rdg 5
    menace_vs knight 3
    menace_mult_vs mage 1.2

**Pesi regolabili** in ``def parameters`` (importanza armatura/schivata/portata/velocità
e normalizzazione HP; danno+cd+ready+cover alimentano sempre il nucleo DPS)::

    def parameters
    menace_armor_weight 1
    menace_dodge_weight 1
    menace_range_weight 0.15
    menace_speed_weight 0.2
    menace_hp_ref 50

Preferire ``menace_mult`` / ``menace_mult_vs`` per unità che ricercano upgrade;
usare ``menace`` / ``menace_vs`` assoluti solo per una priorità fissa.

Carica e controcarica (da 1.4.0.1)

Carica: le unità con statistiche di carica possono eseguire un attacco di carica ad alto danno quando impegnano un
nemico entro portata. Dopo la carica entrano in cooldown e infliggono solo ``mdg`` / ``rdg`` normali
fino alla fine del cooldown. Per caricare di nuovo lo stesso bersaglio, allontana l’unità oltre
``charge_mdg_dist`` / ``charge_rdg_dist`` dopo la scadenza del cooldown.

Danno di carica (additivo, non un moltiplicatore)::

    charge_damage = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)

Esempio: ``mdg 6, charge_mdg 2`` → base ``6 + 2 = 8``, poi scalato dalla distanza entro
``charge_mdg_dist`` (circa 50% a contatto, fino a ~100% alla portata massima). A distanza usa ``rdg`` /
``charge_rdg`` allo stesso modo.

Proprietà di carica (coppie mischia / distanza; scambia ``mdg`` ↔ ``rdg`` per la distanza):

- ``charge_mdg`` / ``charge_rdg`` — danno di carica extra (aggiunto)
- ``charge_mdg_vs`` / ``charge_rdg_vs`` — bonus contro tipi di unità specifici
- ``charge_mdg_cd`` / ``charge_rdg_cd`` — cooldown (ms)
- ``charge_mdg_dist`` / ``charge_rdg_dist`` — portata massima di carica
- ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` — portata minima per attivarsi (0 = nessun limite)
- ``charge_mdg_splash`` / ``charge_rdg_splash`` — danno splash
- ``charge_mdg_radius`` / ``charge_rdg_radius`` — raggio splash
- ``charge_mdg_splash_decay_min`` / ``charge_rdg_splash_decay_min`` — attenuazione splash minima (0.0–1.0)

Esempio (cavaliere di campagna)::

    def knight
    mdg 3
    charge_mdg 2
    charge_mdg_cd 10
    charge_mdg_dist 15
    charge_mdg_min_dist 3
    charge_mdg_splash 1
    charge_mdg_radius 1
    charge_mdg_splash_decay_min 0.5

Controcarica: contrasta una carica in arrivo. Quando un’unità di controcarica blocca un attaccante in carica
entro portata, la carica dell’attaccante è interrotta (quel colpo si risolve come un attacco
normale) e l’attaccante subisce danno di controcarica.

Danno di controcarica (additivo)::

    counter = attacker (mdg/rdg + mdg_vs/rdg_vs) + attacker (charge_mdg/charge_rdg + charge_mdg_vs/charge_rdg_vs)
            + self (op_charge_mdg/op_charge_rdg + op_charge_mdg_vs/op_charge_rdg_vs)

Proprietà di controcarica:

- ``op_charge_mdg`` / ``op_charge_rdg`` — danno di controcarica extra (aggiunto)
- ``op_charge_mdg_vs`` / ``op_charge_rdg_vs`` — bonus contro tipi di attaccante
- ``op_charge_mdg_cd`` / ``op_charge_rdg_cd`` — cooldown
- ``op_charge_mdg_dist`` / ``op_charge_rdg_dist`` — portata effettiva (0 = illimitata)

``Suoni (``style.txt``)``: ``charge_success``, ``charge_failed``, ``op_charge``. Anche
``critical_hit``, ``piercing_triggered`` per il feedback di combattimento.

Note: gli auto-attacchi non attivano la carica; lo splash di carica a terra non colpisce le unità aeree.

Raffiche / attacchi in sequenza (``damage_seq``, da 1.3.8.2, potenziato in 1.4.3.6)
-------------------------------------------------------------------------------------

Un ciclo di attacco può sparare più colpi in rapida successione (stile Chu Ko Nu di
Age of Empires). Definisci prima ``mdg`` / ``rdg`` base, poi ``damage_seq``:

``damage_seq mdg|rdg \<volte\> [(damage d1 d2 ...)] [(interval secondi)]``

- Suddivisione esplicita: ``(damage 6 3 3)`` — i valori interi dei segmenti devono sommare al danno
  base (stesse unità di ``mdg`` / ``rdg`` in rules.txt)
- Suddivisione automatica (da 1.4.3.6): ometti ``(damage ...)`` per dividere il danno base in modo uniforme su
  ``volte`` (funziona con danno frazionario, es. ``rdg 7.5`` con ``volte 3`` → 2,5 per colpo)
- Intervallo: ``(interval 0.25)`` secondi tra i colpi; se omesso o 0 con ``volte \> 1``,
  predefinito 0,25 s
- Limite: al massimo 6 colpi per attacco
- Tiraggi di colpo: ogni segmento tira indipendentemente colpo, critico e debuff
- Cooldown: ``mdg_cd`` / ``rdg_cd`` inizia dopo che l’intera raffica è finita
- Suoni: ogni colpo attiva ``launch_mdg`` / ``launch_rdg``; elenca più ID suono
  in ``style.txt`` (es. ``launch_rdg 1042 1042 1042``)

Esempio di raffica a distanza (``repeating_crossbowman`` integrato)::

    def repeating_crossbowman
    rdg 6
    rdg_cd 2.5
    rdg_range 4
    rdg_projectile 1
    damage_seq rdg 3 (interval 0.25)

Esempio in mischia con suddivisione esplicita del danno::

    def footman
    mdg 12
    mdg_cd 1.5
    mdg_range 6
    damage_seq mdg 3 (damage 6 3 3) (interval 0.2)

Vedi anche ``../player/burst-attacks.htm``.

Armi e armature (da 1.4.1.3)
-----------------------------

Le armi (``class weapon``) e le armature (``class armor``) contengono le statistiche di combattimento. Le unità le referenziano::

    def footman
    class soldier
    weapons sword bow     ; la prima arma è quella predefinita / principale
    auto_weapon_switch 1  ; 1 = cambio automatico per portata in combattimento
    armor light_armor

I giocatori cambiano arma con A / Shift+A o B poi X. Il cambio manuale ha priorità sul cambio automatico.
Le statistiche sull’unità e sull’equipaggiamento si sommano. Le armi supportano l’ereditarietà come
le unità.

Buff e debuff (da 1.3.9.8, esteso in 1.4.1.7)
----------------------------------------------

Collega agli attacchi con ``buffs`` / ``debuffs``, o tramite skill con ``effect buffs`` /
``effect debuffs``.

``reflect_percent`` (percentuale intera) su un buff abilita la riflessione del danno; applica con
``effect buffs``. Non esiste ``effect reflect``. Esempio: ``b_douzhuan`` in ``mods/wuxia/rules.txt``.

Esempio di buff multi-statistica::

    def HealEnhancementBuff
    class buff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1

Modalità di trigger:

1. Predefinito — al colpo
2. :strong:```is_active 1`` — all’inizio di un attacco (attivo)
3. :strong:```is_passive 1`` — quando si subisce danno (passivo), con ``trigger_condition`` (es.
   ``hp \< 20``) e ``passive_trigger_rate``

Tassi di trigger (percentuale; il predefinito ripiega sui tassi di attacco normale):

- ``mdg_trigger_rate`` / ``rdg_trigger_rate`` — danno normale
- ``charge_mdg_trigger_rate`` / ``charge_rdg_trigger_rate`` — danno di carica
- ``op_charge_mdg_trigger_rate`` / ``op_charge_rdg_trigger_rate`` — controcarica

Abilità (class skill)
----------------------

Definisci le abilità con ``class skill`` invece di ``class ability``::

    def fireball
    class skill
    mana_cost 50
    cost 10 0
    time_cost 30
    effect harm_target 60
    effect_target ask
    effect_range 12
    cooldown 10

``can_use_tech`` si applica agli upgrade; ``can_use_skill`` si applica alle abilità.

Da 1.4.4.6: ``harm_target``, ``harm_area``, ``burst``, ``push``, ``effect buffs`` / ``debuffs``, ecc. Mod demo: ``mods/wuxia/rules.txt``. Vedi `Guida alle abilità <skills-and-effects.htm>`_.

**Trigger delle abilità (da 1.4.4.6)**

Le abilità apprese vanno in ``can_use_skill``. Manuale e automatico possono coesistere (``manual_use 1`` + ``auto_trigger 1``).

+--------------------+------------------------------------------------+
| ``manual_use 1``   | Mostra nel menu comandi (predefinito 1)        |
+--------------------+------------------------------------------------+
| ``auto_trigger 1`` | Si attiva automaticamente in combattimento     |
+--------------------+------------------------------------------------+
| ``trigger_timing`` | Quando attivarsi automaticamente (vedi tabella)|
+--------------------+------------------------------------------------+

+-------------------------+----------------------------------------------+---------------------------+
| ``trigger_timing``      | Quando                                       | Elenco legacy             |
+=========================+==============================================+===========================+
| ``on_hit`` (predefinito)| Dopo aver colpito un nemico                  | ``active_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack``           | All’inizio dell’attacco; l’attacco normale continua | ``attack_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack_replace``   | All’inizio dell’attacco; sostituisce questo attacco | ``attack_replace_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_damaged``          | Quando si viene colpiti da un nemico (passivo)| ``passive_trigger_skills``|
+-------------------------+----------------------------------------------+---------------------------+

Tassi: ``active_trigger_rate`` / ``passive_trigger_rate`` (1–100); opzionali ``mdg_trigger_rate`` / ``rdg_trigger_rate`` sovrascrivono il tasso attivo per mischia/distanza.

Condizioni: ``trigger_condition hp < 30`` (``hp``/``mana`` confrontati come percentuale) o ``hp_threshold 30``. Verificate solo per ``on_hit`` e ``on_damaged``, non per ``on_attack`` / ``on_attack_replace``.

I trigger automatici consumano mana e rispettano il cooldown; la preparazione ``ready`` si applica come nei lanci manuali.

Esempio (passivo quando si viene colpiti)::

    def skill_thorns
    class skill
    auto_trigger 1
    manual_use 0
    trigger_timing on_damaged
    passive_trigger_rate 30
    effect harm_target 10
    effect_target ask

Riferimento completo: `Guida alle abilità <skills-and-effects.htm>`_ (sezione sulle modalità di trigger).
Effetti (class effect, da 1.4.1.7)
-----------------------------------

Danno e cura sono suddivisi in parametri dettagliati::

    def exorcism
    class effect
    harm_level 2
    harm_cd 7.5
    harm_radius 6
    harm_target_type undead
    debuffs b_slow

Analogamente: ``heal_level``, ``heal_cd``, ``heal_radius``, ``heal_target_type``;
``hp_regen_cd``, ``mana_regen_ready``, ecc.

Sistema delle fasi (da 1.4.2.4)
--------------------------------

``class phase`` fa avanzare le ere di gioco senza potenziare la base::

    def dark_age
    class phase
    cost 0 0
    time_cost 0

    def feudal_age
    class phase
    cost 10 15
    time_cost 130
    phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
    units_auto_upgrade 0
    phase_targets soldier

``phase_targets`` opzionale limita quali unità ricevono le voci non-costo di ``phase bonus`` (i bonus di tipo costo si applicano sempre a livello giocatore). Lascia vuoto per tutte le unità. Usa nomi di categoria (``soldier``, ``worker``, ``building``, ``unit``, ecc.), nomi di unità specifici (``footman knight``), o qualsiasi nome nella catena ``is_a``; qualsiasi corrispondenza positiva conta. Un ``-`` iniziale esclude una corrispondenza — es. ``phase_targets -building`` significa ogni unità tranne gli edifici; puoi mescolare inclusioni ed esclusioni, es. ``phase_targets soldier -footman``.

Su un edificio::

    can_advance feudal_age

Usa ``can_advance`` (non ``can_research``) per le fasi. Premi V sull’edificio per vedere la
fase attuale.

``hide_locked_commands 1`` in ``def parameters`` nasconde i comandi i cui requisiti non sono
ancora soddisfatti.

Oltre ai nomi di tipo semplici (tutti devono essere posseduti — AND), ``requirements`` può
chiedere almeno N edifici di un gruppo nominato (da 1.4.5.8)::

    def stables
    class building
    requirements castle_age

    def imperial_age
    class phase
    requirements castle_age any_buildings 2 castle_age_buildings

    def castle
    class building
    requirements any_buildings 2 castle_age_buildings

``any_buildings <n> <group>_buildings`` toglie ``_buildings`` e raccoglie gli edifici il cui
``requirements`` semplice elenca quella chiave. Usare ``castle_age_buildings``, non il nome
nudo della fase. Il token di gruppo non attiva ``units_auto_upgrade``.

Economia (da 1.4.0.x)
---------------------

``population_cost`` ha sostituito ``food_cost``. Gli edifici possono produrre o contenere risorse::

    auto_production 1       ; produzione automatica (gas, ecc.); riparte finché non è pieno
    manual_production 1     ; produzione avviata dal giocatore
    auto_cultivate 1        ; fattorie; riparte solo quando il deposito è vuoto
    is_gather 1             ; l’output va nel deposito dell’edificio; i lavoratori lo trasportano alla base
    resource_volume_max 8
    resource_volume_start 0
    production_type resource2
    production_time 18      ; secondi per riempire un lotto
    production_qty 8        ; quantità per ciclo di produzione (nel deposito dell’edificio)
    extraction_time 2       ; tempo di raccolta del lavoratore dall’edificio (secondi)
    extraction_qty 8        ; quantità trasportata per viaggio

Senza ``is_gather``, sia la produzione automatica sia quella manuale accreditano l’output di ``production_type`` direttamente nelle scorte del giocatore (es. ``gold_house``)::

    auto_production 1
    manual_production 1
    production_type resource1
    production_time 100
    production_qty 200

Per bottino raccoglibile, usa invece ``production_item`` (al posto di ``production_type``)::

    production_item gold_pile
    production_qty 1

| Attributo | Ruolo |
| --- | --- |
| ``production_type`` | Risorsa prodotta (con ``production_time`` e ``production_qty`` definisce la capacità di produzione) |
| ``production_time`` | Secondi per ciclo di produzione |
| ``production_qty`` | Output per ciclo; senza ``is_gather``, aggiunto alle risorse del giocatore; con ``is_gather``, a ``resource_qty`` dell’edificio |
| ``auto_production`` | Quando ``1``, mostra produzione automatica; ripete dopo ogni ciclo; usa per il gas (non ``auto_cultivate``) |
| ``manual_production`` | Quando ``1``, mostra produzione manuale; un ciclo per clic; indipendente da ``auto_production`` |
| ``auto_cultivate`` | Coltivazione automatica su edifici ``is_gather`` (es. fattorie); parallelo a ``auto_production`` |
| ``manual_cultivate`` | Coltivazione manuale; parallelo a ``manual_production``; imposta ``1`` esplicitamente quando serve |
| ``production_item`` | Nome del tipo di oggetto; genera oggetti raccoglibili accanto all’edificio al completamento |
| ``is_gather`` | L’output resta nell’edificio finché un lavoratore con ``can_gather_building`` non lo trasporta a un magazzino |
| ``resource_volume_max`` | Massimo memorizzato nell’edificio (es. 8 vespene) |
| ``resource_volume_start`` | Quantità iniziale memorizzata alla costruzione (``0`` = vuoto) |
| ``extraction_time`` / ``extraction_qty`` | Tempo di raccolta del lavoratore e quantità per viaggio da edificio o deposito |

.. note::

   ``auto_production`` e ``manual_production`` sono flag separati e possono essere entrambi ``1`` (es. ``gold_house``). ``auto_production`` assente o ``0`` non implica la modalità manuale; imposta ``manual_production 1`` per il comando manuale. Stesso discorso per ``auto_cultivate`` / ``manual_cultivate`` sulle fattorie.

.. note::

   ``is_create`` è deprecato: i cumuli a terra ``class resource`` non vengono più generati. Usa ``production_type`` (scorte dirette), ``is_gather`` (deposito edificio) o ``production_item`` (genera oggetti).

``class resource`` è separato da ``class deposit``. Depositi sulla mappa::

    mineral_field 1500 a1
    geyser 1 e1

Le strutture del gas devono stare sul deposito corrispondente::

    requires_deposit geyser
    is_buildable_anywhere 0

Vedi ``sc_gas_building`` / ``assimilator`` in ``mods/starcraft/rules.txt``. Guida del giocatore:
``../player/starcraft-resources.htm``. La schermata attributi (V) aggiunge requires deposit;
tempo/qty di produzione usano le voci attributo di produzione esistenti.

Eroi (da 1.4)
--------------

Definisci unità eroe in qualsiasi ``rules.txt`` (regole base, mod, pacchetti campagna, pacchetti mappe multiplayer). Funzionano in schermaglia, mappe casuali, multiplayer e campagne: XP da uccisione, livellamento ``xp_thresholds``, revival ``is_revivable``, inventario, ecc. Il salvataggio tra capitoli (``campaign_carryover`` nella sezione successiva) è una funzione extra solo per le campagne single-player.

Esempio multiplayer: ``hero`` / ``hero_knight`` in ``res/multi/td2/rules.txt``.

::

    def hero
    class soldier
    global_count_limit 1
    is_revivable 1
    revival_time 10
    xp_thresholds 200 500 900
    hp_max_per_level 1000
    mdg_per_level 100
    resource_rewards 300
    xp_reward 100

``Livello e XP (``level`` / ``xp`` / ``xp_thresholds`` / ``xp_threshold_growth``)``

| Campo | Predefinito | Significato |
| --- | --- | --- |
| ``xp_thresholds`` | (vuoto) | Soglie XP cumulative. Il primo valore è l’XP totale per il livello 2 (o livello 1 se si parte dal livello 0); ogni valore successivo è il livello successivo. |
| ``max_level`` | (nessuno) | Cap di livello dell’eroe. Con ``xp_threshold_growth``, il caricamento delle regole genera automaticamente ``max_level - 1`` soglie |
| ``xp_threshold_growth`` | (nessuno) | Genera automaticamente ``xp_thresholds`` da una formula (tabella sotto). Richiede ``max_level``; usa questo o un elenco esplicito ``xp_thresholds`` (l’elenco esplicito ha priorità) |
| ``level`` | ``1`` | Livello iniziale. Quando ``\> 1`` con ``xp_thresholds``, i bonus cumulativi ``*_per_level`` e ``level_skills`` sono applicati allo spawn. |
| ``xp`` | ``0`` | XP cumulativa iniziale opzionale. |
| ``level_up_heal_full`` | ``0`` | ``1`` = ripristina HP e mana completi a ogni salita di livello; ``0`` = aggiunge solo l’incremento ``hp_max_per_level`` / ``mana_max_per_level`` ai valori attuali (predefinito). |
| ``level_up_reset_xp`` | ``0`` | ``1`` = azzera l’XP corrente dopo ogni salita di livello; ``0`` = mantieni l’XP cumulativa (predefinito). Quando ``1``, preferisci ``xp_thresholds`` per livello (XP dall’ultimo level-up), non totali cumulativi. |

- Livello massimo = ``len(xp_thresholds) + 1`` (es. nove soglie → cap livello 10).
- Stato unità (Tab): gli eroi con ``xp_thresholds`` annunciano sempre il livello (inclusi 0 e 1). L’XP è mostrata come ``corrente / prossima soglia`` (al livello 0 la prossima soglia è ``xp_thresholds[0]``).
- Solo ``xp_thresholds`` (o ``xp_threshold_growth`` dopo l’espansione) → livello predefinito 1 all’inizio della partita; ``level 0`` inizia sotto il livello 1.

:strong:```Tipi di curva ``xp_threshold_growth``` (l’indice di soglia ``i`` inizia a 0 per il livello 2, 3, …)

| Tipo | Sintassi | Formula |
| --- | --- | --- |
| linear | ``linear BASE STEP`` | ``BASE + STEP × i`` |
| quadratic | ``quadratic BASE A B`` | ``BASE + A×i + B×i²`` |
| polynomial | ``polynomial c0 c1 c2 …`` | ``c0 + c1×i + c2×i² + …`` |
| geometric | ``geometric FIRST RATIO`` | ``FIRST × RATIO^i`` (``RATIO`` può essere frazionario, es. ``1.08``) |

Esempio (eroe a 100 livelli, XP cumulativa lineare)::

    def long_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50
    hp_max_per_level 30
    mdg_per_level 2

Esempio (curva quadratica stile Raynor, uguale a ``40 90 160 250 …``)::

    def raynor_curve
    class soldier
    max_level 10
    xp_threshold_growth quadratic 40 40 10
    hp_max_per_level 30

Esempio (def figlia sovrascrive solo il cap di livello; eredita ``xp_threshold_growth`` del genitore)::

    def base_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50

    def short_campaign_hero
    is_a base_hero
    max_level 20

Esempio (inizio a livello 0, elenco soglie esplicito)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160 250 360 490 640 810 1000
    hp_max_per_level 30
    mdg_per_level 2
    level 0

Esempio (cura completa al level up)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160
    hp_max_per_level 30
    level_up_heal_full 1

Esempio (inizio a livello 3 con XP iniziale)::

    def veteran_hero
    is_a knight
    xp_thresholds 200 500 900
    hp_max_per_level 20
    level 3
    xp 500

Carryover eroe di campagna (guidato dalle regole)
--------------------------------------------------

Aggiungi ``campaign_carryover 1`` su una def eroe della sezione precedente. Solo campagne single-player: alla vittoria, i progressi sono salvati in ``user/campaigns.ini`` e ripristinati nel capitolo successivo (il ritentativo dopo una sconfitta non sovrascrive). Il co-op non persiste gli eroi.

::

    def my_hero
    is_a knight
    campaign_carryover 1
    campaign_carryover_stats 1
    campaign_carryover_inventory 1
    inventory_capacity 8

| Campo | Predefinito | Significato |
| --- | --- | --- |
| ``campaign_carryover`` | ``0`` | ``1`` = abilita salvataggio tra capitoli |
| ``campaign_carryover_id`` | nome def | Chiavi ``hero_\<id\>\_xp``, ``\_level``, ``\_inventory`` |
| ``campaign_carryover_stats`` | ``1`` | Livello + XP |
| ``campaign_carryover_inventory`` | ``1`` | Oggetti nello zaino |

Solo statistiche: ``campaign_carryover_inventory 0``. Solo inventario: ``campaign_carryover_stats 0``. Nessun carryover: ometti ``campaign_carryover 1``.

Opzionale in ``campaign.txt``: ``hero_min_level 13:2 16:3 …`` per livelli minimi di capitolo.

Separato da ``campaign_flag`` / ``add_inventory_item`` (token di storia, alleanze). Vedi ``mod/campaign-hero-carryover.htm``.

Contenitori di trasporto (rinomina campi da 1.4.4.9; i nomi legacy sono ancora accettati)
------------------------------------------------------------------------------------------

Unità o edifici con ``transport_capacity`` agiscono come contenitori di trasporto. Proprietà correlate:

| Proprietà | Effetto | Esempio |
| --- | --- | --- |
| ``passenger_attack_types`` | Tipi di unità che possono attaccare all’esterno mentre sono dentro | ``passenger_attack_types archer knight`` o ``all`` |
| ``load_bonus`` | Per unità caricata → statistiche aggiunte al **contenitore** | ``load_bonus speed 0.5 mdg 2`` |
| ``passenger_bonus`` | Statistiche aggiunte al **passeggero** mentre è dentro (annullate allo scarico) | ``passenger_bonus rdg_range 1 mdg 2`` |

Esempio::

    def flyingmachine
    class soldier
    transport_capacity 8
    passenger_attack_types knight archer
    load_bonus speed 0.5
    passenger_bonus rdg_range 1

    def wall
    class building
    transport_capacity 4
    passenger_attack_types archer catapult
    passenger_bonus mdg 2

- Senza ``passenger_attack_types``, i passeggeri non possono attaccare bersagli esterni per impostazione predefinita.
- ``load_bonus`` e ``passenger_bonus`` possono essere combinati sullo stesso contenitore.

Occupazione della casella (``space``, da 1.4.5.8)
-------------------------------------------------

``space`` è una proprietà precision (decimali ammessi). Indica quanto l’unità occupa
sul proprio strato aria/terra/acqua. La capacità è ``square_width`` della mappa nelle stesse unità.

| Impostazione | Effetto |
| --- | --- |
| ``space 0`` (predefinito) | Non consuma capacità (illimitato, legacy) |
| ``space 1`` con ``square_width 12`` | Al massimo 12 unità su quello strato |
| ``space 0.5`` con ``square_width 12`` | Al massimo 24 |
| ``space`` > ``square_width`` | L’unità non può entrare in quella casella |

La capacità è condivisa da tutte le fazioni. Se la casella è piena, movimento e
addestramento che spawnerebbe lì vengono rifiutati (voce ``not_enough_space``).
Gli strati sono separati: l’occupazione a terra non blocca le unità aeree.

Esempio::

    def peasant
    class worker
    space 1

    def siege_engine
    class soldier
    space 4

Vedi anche ``square_width`` in ``mod/mapmaking.rst``.

Oggetti (da 1.4.1.3)
---------------------

::

    def magic_sword
    class item
    consume_on_pickup 0
    buffs power_buff
    resource_rewards resource1 50

``is_loot 1`` fa cadere l’oggetto quando il portatore muore.

``Suoni degli oggetti (``style.txt``; suoni di uso da 1.4.4.6)``

| Quando | ``style.txt`` dell’oggetto | ``style.txt`` dell’unità | Predefinito globale (``def thing``) |
| Raccolta | ``on_pickup`` | ``pickup_\<tipo oggetto\>`` | ``pickup`` |
| Rilascio | ``on_drop`` | ``drop_\<tipo oggetto\>`` | ``drop`` |
| Uso | ``use`` / ``on_use`` | ``use_\<tipo oggetto\>`` | ``item_used`` |

Sull’oggetto (``use`` e ``on_use`` sono equivalenti; più ID sono scelti a caso)::

    def zhuiri_jianfa_book
    title 7754
    pickup 1506
    use 1506

Sull’unità::

    def raynor
    use_zhuiri_jianfa_book 1506

Fallback globale::

    def thing
    item_used 1194 1195 1196

L’ereditarietà (``is_a``) funziona come ``on_pickup`` / ``on_drop``: i tipi derivati sovrascrivono i genitori.

Inventario e oggetti equipaggiabili (da 1.4.3.1)
-------------------------------------------------

Le unità necessitano di ``inventory_capacity`` > 0 per tenere oggetti. Ogni oggetto usa uno slot (``transport_volume``
è definito ma la capacità attualmente conta gli oggetti, non il volume).

Equipaggiamento integrato (tradizionale)::

    def footman
    weapons sword          ; class weapon — integrato, non nello zaino
    armor footman_armor    ; class armor — integrato

Oggetti equipaggiabili (modello unificato): lo stesso nome di tipo può essere ``class item``::

    def sword
    class item
    equippable_as_weapon 1
    mdg 3.5
    mdg_range 1
    transport_volume 1

    def footman_armor
    class item
    equippable_as_armor 1
    mdf 0.5

Quando ``weapons`` / ``armor`` su un’unità puntano a oggetti equipaggiabili, il motore crea istanze
di oggetto allo spawn e le mette nell’inventario. Se l’unità non ha equipaggiamento integrato di quel
tipo e ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` è ``1`` (predefinito), sono
equipaggiati in silenzio::

    def footman
    inventory_capacity 2
    weapons sword
    armor footman_armor

Regole di cambio equipaggiamento quando un’unità ha sia equipaggiamento integrato sia a oggetti (es.
``weapons bow sword`` con ``bow`` come ``class weapon`` e ``sword`` come oggetto equipaggiabile):

- L’equipaggiamento integrato è sempre equipaggiato allo spawn; l’equipaggiamento a oggetti va nello zaino.
- Con ``spawn_weapons_equipped 1`` (predefinito), le armi-oggetto restano nello zaino e non possono
  essere equipaggiate; con ``spawn_weapons_equipped 0``, il giocatore può equipaggiarle manualmente.
- L’equipaggiamento integrato può cambiare solo con equipaggiamento integrato; quello a oggetti solo con oggetti;
  nessun cambio incrociato tra i due tipi. Stesse regole per l’armatura
  (``spawn_armor_equipped``).

Esempio arciere misto::

    def archer
    weapons bow sword
    spawn_weapons_equipped 1   ; arco equipaggiato, spada nello zaino, spada non equipaggiabile
    inventory_capacity 3

    def archer
    weapons bow sword
    spawn_weapons_equipped 0   ; arco equipaggiato, spada nello zaino, il giocatore può equipaggiare la spada
    inventory_capacity 3

I consumabili (solo ``buffs``, senza ``equippable_as_*``) si usano dallo zaino con Invio,
non dalla schermata equipaggiamento. In caso di successo, suonano ``use`` / ``on_use``; i consumabili normali
annunciano il titolo dell’oggetto più "usato".

Libri di abilità (imparano permanentemente una skill; consumati all’uso riuscito)::

    def zhuiri_jianfa_book
    class item
    skills skill_zhuiri_jianfa
    learn_level 10
    transport_volume 1

- ``learn_level`` / ``learn_level_skills``: livello minimo per imparare dal libro (il più severo tra
  ``learn_level_skills`` dell’unità e le regole dell’oggetto).
- ``level_skills`` dell’unità: sblocco automatico al level up (separato dai libri; non duplicare la stessa
  skill o l’uso restituisce ``skill_already_known`` e tiene il libro).
- Con ``learn_level`` / ``learn_level_skills`` sull’oggetto, la raccolta non concede la skill;
  il giocatore deve usare il libro dallo zaino.
- Successo: suono di uso + titolo TTS della skill + messaggio ``skill_learned``; fallimento: ``order_impossible``
  con ``skill_level_too_low`` / ``skill_already_known`` ecc.

``Tesoro con ``use_square`` (ricompense solo quando usato nello zaino su una casella nominata)::

    def mystery_treasure
    class item
    use_square b2
    resource_rewards resource1 150

Ordini server (utilizzabili anche nelle azioni trigger ``order``): ``equip_weapon``, ``unequip_weapon``,
``equip_armor``, ``unequip_armor``, ``use_item``, ``drop``.

Comportamento predefinito delle unità (da 1.4.3.1)
---------------------------------------------------

Comportamento iniziale per unità in ``rules.txt``:

- ``ai_mode``: ``offensive``, ``defensive``, ``guard``, o ``chase``. Predefinito: ``offensive``
  per i soldati, ``defensive`` per i lavoratori. Si applica alle unità di combattimento.
  ``chase`` mantiene un ``AttackAction`` e segue tra caselle (senza ``go`` automatico);
  ``offensive`` / ``guard`` rispettano ancora ``position_to_hold`` alla creazione finché un ordine non fa ``stop()``;
  ``defensive`` / ``chase`` no.
- ``auto_gather``: ``1`` o ``0``. Predefinito ``1``. Solo lavoratori.
- ``auto_repair``: ``1`` o ``0``. Predefinito ``1``. Solo lavoratori.
- ``auto_explore``: ``1`` o ``0``. Predefinito ``0``. Unità mobili (speed > 0).
- ``can_auto_explore``: ``1`` o ``0``. Predefinito ``0``. Aggiunge abilita/disabilita auto-esplorazione al
  menu comandi dell’unità.
- ``no_number`` (da 1.4.3.2): ``1`` o ``0``. Predefinito ``0`` (pronuncia sempre i numeri seriali,
  es. "peasant 1 at a1"). Quando ``1``: omette il numero mentre esiste una sola unità viva di quel
  tipo ("Guan Yu at a1"); con due o più, usa i numeri ("Guan Yu 1", "Guan Yu 2").
  I riepiloghi di gruppo seguono la stessa regola. Per eroi o leader unici.

``ai_mode patrol`` non è valido — la pattuglia richiede un comando di percorso. Le unità computer neutrali sono
ancora forzate a guard + contrattacco indipendentemente da ``ai_mode``.

Le unità del giocatore in modalità ``offensive``, ``defensive`` o ``chase`` non attaccano automaticamente le unità
neutrali (``computer_only ... neutral``) e la modalità difensiva non fugge dai soli neutrali.
Il ``go`` normale su un neutrale si limita a muovere; l’``attack`` normale su ``is_huntable`` infligge danno.
Usa un attacco imperativo (es. Ctrl+clic) perché l’IA tratti un creep/NPC neutrale come bersaglio automatico.

Esempio::

    def knight
    class soldier
    ai_mode guard
    auto_explore 1
    can_auto_explore 1

    def peasant
    class worker
    auto_gather 1
    auto_repair 0
    ai_mode defensive

Cattura / ordine di occupazione predefinito
--------------------------------------------

Bersaglio — ``capture_hp_threshold`` (su edifici/unità catturabili):

| Valore | Significato |
| --- | --- |
| ``0`` (predefinito) | Non catturabile tramite soglia HP |
| ``100`` | Cattura a contatto: converte il proprietario all’arrivo, senza danno; l’ordine predefinito del clic destro è cattura (vedi ``can_capture``) |
| ``30`` ecc. | Catturabile quando HP ≤ quella percentuale durante il combattimento normale |

Attaccante — ``can_capture`` (su soldati/lavoratori con attacco):

| Valore | Significato |
| --- | --- |
| ``1`` (predefinito) | Clic destro su nemico con ``capture_hp_threshold 100`` → cattura predefinita; l’IA usa la cattura a contatto |
| ``0`` | Stesso bersaglio → attacco/movimento predefinito; l’IA attacca normalmente |

Richiede ``attack`` nelle skill dell’unità; il bersaglio deve essere un nemico vivo e vulnerabile.

Esempio — solo i fanti catturano le caserme; gli arcieri attaccano::

    def captured_barracks
    class building
    capture_hp_threshold 100
    ...

    def footman
    class soldier
    can_capture 1
    ...

    def archer
    class soldier
    can_capture 0
    ...

POI di mappa casuale ``captured_barracks`` e gioco stile HoMM: ``player/英雄无敌与文明5玩法说明.htm``.

Riparazione navi (da 1.4.1.1)
-----------------------------

ordine give — trasferisci un oggetto dell’inventario a un’altra unità::

    give <id unità bersaglio>
    give <id unità bersaglio> <tipo o id oggetto>

Campi del bersaglio (tutti devono passare):

- ``receive_items 1`` (predefinito 0 — gli NPC devono aderire)
- ``accepted_items`` — whitelist opzionale di tipi di oggetto (ereditarietà ``is_a`` supportata); vuoto = qualsiasi
- ``accept_from`` — elenco opzionale: ``self``, ``ally``, ``neutral``, ``enemy``; vuoto = qualsiasi

Esempio di NPC che accetta qualsiasi oggetto da chiunque::

    def quest_npc
    receive_items 1
    inventory_capacity 5

Esempio: i cavalieri alleati accettano solo ``knight_lance`` dagli alleati::

    def knight
    receive_items 1
    accepted_items knight_lance
    accept_from ally

La consegna registra ``received_items`` sul bersaglio per i controlli trigger. Gli oggetti applicano ``skills`` /
``buffs`` alla ricezione come ``pickup``. La consegna da script ignora ``inventory_capacity`` del bersaglio.
Demo multiplayer: ``res/multi/give_demo.txt``. Demo di relazione in campagna: ``The Legend of Raynor`` cap. 14–16
(``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``).

Campi di costruzione, addon e decollo (stile StarCraft, ``mods/starcraft``)
----------------------------------------------------------------------------

Il motore supporta campi di costruzione, modalità di costruzione dei lavoratori, addon Terran e
ricombinazione al decollo. Implementazione di riferimento: ``mods/starcraft/rules.txt``. Guide del giocatore:

- Addon Terran: ``../player/starcraft-terran.htm``
- Creep Zerg e tumori della Regina: ``../player/starcraft-zerg-creep.htm``

Campi di costruzione (psi Protoss / creep Zerg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Attributo | Ruolo |
| --- | --- |
| ``provides_build_field \<nome\>`` | Marca le caselle vicine (es. ``psi``, ``creep``) |
| ``requires_build_field \<nome\>`` | Richiede quel campo per piazzare/costruire; ``0`` esenta il tipo (Nexus, Photon Cannon) |
| ``build_field_radius \<caselle\>`` | Raggio del provider (passi BFS dalla casella principale; usa questo o ``build_field_radius_m``) |
| ``build_field_radius_m \<metri\>`` | Raggio del provider in metri (stessa scala di ``rdg_range``); distanza euclidea dal ``(x,y)`` del provider |
| ``build_field_persists 1`` | I segni restano dopo la distruzione del provider (creep Zerg) |
| ``build_field_spreads 1`` | Diffonde i segni alle caselle adiacenti ogni secondo |
| ``build_field_spread_squares N`` | Livelli per tick (predefinito 1 quando ``build_field_spreads``) |
| ``requires_build_field_on_square 1`` | L’intera casella deve essere marcata (Zerg); altrimenti basta il campo live ovunque sulla casella (Protoss) |
| ``loses_power_without_field 1`` | Senza campo live: interrompe costruzione/addestramento/potenza (Protoss) |

:strong:```build_field_radius`` vs ``build_field_radius_m``

Usa una sola proprietà di raggio per provider; lascia l’altra a 0 (predefinito).

| Proprietà | Come si misura la portata | Uso tipico |
| --- | --- | --- |
| ``build_field_radius`` | Passi BFS dalla casella principale del provider (caselle discrete) | Creep legacy basato su caselle |
| ``build_field_radius_m`` | Distanza euclidea dal (x, y) del provider in metri | Catene psi Protoss (stile SC2); Hatchery / tumore creep Zerg in ``mods/starcraft`` |

Una casella di mappa è larga circa 12 m (``square_width 12``). Esempi nella mod StarCraft:
Nexus 18 m, Pylon 12 m, Hatchery 12 m, tumore creep 4 m.

Campo live vs marcato

- Campo live — attualmente fornito da edifici/unità in piedi (metri: punto-in-cerchio; caselle: BFS da ``place``).
- Campo marcato — segni persistenti sulle caselle dipinti alla registrazione e/o diffusi ogni secondo.

``has_build_field_on_square`` accetta live O marcato. Lo Zerg ``requires_build_field_on_square 1`` controlla solo le caselle marcate (non puoi costruire su creep live che non si è ancora diffuso/marcato).

Quando ``build_field_persists 1`` o ``build_field_spreads 1`` è impostato, anche i provider a raggio metrico dipingono segni in portata (necessario perché Hatchery-only ``build_field_radius_m`` permetta ancora la costruzione Zerg).

Tumore creep della Regina (``mods/starcraft``): le skill di summon piazzano edifici ``creep_tumor`` sulle caselle bersaglio. Attributi della skill:

| Attributo | Ruolo |
| --- | --- |
| ``summon_requires_build_field \<nome\>`` | La casella bersaglio deve avere quel campo (live o marcato) |
| ``summon_requires_marked_field 1`` | Il bersaglio deve essere marcato (tumor Extend; Queen Spawn omette questo) |

Guida del giocatore: ``../player/starcraft-zerg-creep.htm``. Readme della mod: ``mods/starcraft/readme.txt``.

Protoss (``protoss_building``)::

    requires_build_field psi
    is_buildable_anywhere 1
    self_constructs 1
    loses_power_without_field 1

Zerg (``zerg_building``)::

    requires_build_field creep
    requires_build_field_on_square 1
    is_buildable_anywhere 1
    self_constructs 1

Hatchery: ``provides_build_field creep`` + ``build_field_radius_m 12`` + ``build_field_persists 1`` +
``build_field_spreads 1``. Queen Spawn creep tumor / tumor Extend — vedi ``../player/starcraft-zerg-creep.htm``.

UI: ``def build_field_\<nome\>`` + ``title \<tts_id\>`` in ``ui/style.txt``; ``noise`` ambientale opzionale.

Depositi e gas (``requires_deposit``)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Attributo | Ruolo |
| --- | --- |
| ``requires_deposit \<tipo\>`` | Deve costruire su un deposito della mappa (es. ``geyser``); il deposito è rimosso al completamento |
| ``is_buildable_anywhere 0`` | Con ``requires_deposit``, blocca la costruzione su building land |

Il template gas ``sc_gas_building`` usa ``auto_production`` + ``is_gather`` + ``production_time`` / ``production_qty``.
I lavoratori necessitano di ``can_gather assimilator`` (tipo edificio), non ``geyser`` (deposito).

Modalità di costruzione dei lavoratori
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| ``build_mode`` | Comportamento |
| --- | --- |
| ``assisted`` | Il lavoratore resta fino alla fine (SCV Terran, predefinito) |
| ``place_and_leave`` | Il lavoratore piazza il cantiere e se ne va; ``self_constructs 1`` completa l’edificio (Probe) |
| ``sacrifice`` | Il lavoratore è consumato (Drone) |

Anche: ``self_constructs 1``, ``build_sacrifices_worker 1``, ``is_buildable_anywhere 1`` (nessuno slot ``class building_land`` separato su Protoss/Zerg/Terran volanti).

Addon Terran
>>>>>>>>>>>>

| Attributo | Ruolo |
| --- | --- |
| ``can_have_addon \<tipi\>`` | Tipi host (Barracks / Factory / Starport) |
| ``addon_max N`` | Addon allegati massimi (predefinito 1) |
| ``is_addon 1`` | Edificio addon (Tech Lab, Reactor) |
| ``addon_host_types \<host\>`` | Quali host accettano questo addon |
| ``addon_grants_train_\<host\> \<unità\>`` | Opzione di addestramento extra quando allegato |
| ``addon_grants_research \<tech\>`` | Ricerca extra quando allegato |
| ``addon_train_multiplier N`` | Doppia produzione del Reactor |
| ``addon_offset_x \<valore\>`` | Offset dello slot laterale a est dell’host (predefinito 3,5 caselle) |

Costruisci l’addon su un host esistente, non a terra nuda.

Decollo e ricombinazione
>>>>>>>>>>>>>>>>>>>>>>>>

| Attributo | Ruolo |
| --- | --- |
| ``can_change_to \<volante\>`` | L’host a terra può decollare |
| ``ground_form \<terra\>`` | La forma volante atterra come questo tipo |
| ``change_time \<sec\>`` | Tempo di morph per ``change_to`` (nessun costo risorse/pop) |

Decollo: gli addon si staccano a terra; il building land è ripristinato sotto l’host (**stesso tipo che l’edificio ha consumato alla costruzione**; le mappe StarCraft usano ``build_site``). Se l’unità non ha un riferimento salvato, si usa ``building_land`` della mappa o l’unica parola chiave ``nb_<tipo>_by_square``.

Atterraggio: consuma l’oggetto ``class building_land`` più vicino sulla casella (nomi API come ``find_meadow_near_xy`` sono storici).

Ricombinazione: Tab Tech Lab → Backspace go (vola allo slot di atterraggio a ovest del lab) → ``change_to`` a terra.

Building land vs slot: building land = permesso di terra; il riattacco richiede allineamento dello slot
(``tech_lab.x ≈ factory.x + addon_offset_x``, entro ~2,5 caselle Manhattan).

Atterrare sulla propria patch di decollo non riattacca. Atterraggio sbagliato con addon orfano → TTS ``addon_reattach_failed`` (7350).

Mappe di test: ``terran_addon_test``, ``terran_recombine_test``; campagna ``sc_build_tests`` cap. 3–4.

Riparazione navi (da 1.4.1.1)
-----------------------------

``can_repair_ships 1`` su lavoratori o edifici. I lavoratori riparano le navi sulla riva adiacente (6
caselle); gli edifici riparano automaticamente le navi nell’acqua vicina (8 caselle).

Costruire ponti sull’acqua (campate a caselle)
----------------------------------------------

I lavoratori possono costruire campate ``is_buildable_on_water_only 1`` su acqua pura; al completamento
viene applicato ``bridge_terrain`` (es. ``bridge_deck``). I cantieri ponte usano il TTS normale
``buildingsite``; i passi usano il ``ground`` del terreno finito. Vedi
`water-bridge-building.htm <water-bridge-building.htm>`_.

Pastorizia (lavoratori)
-----------------------

``can_herd 1`` permette a un lavoratore di pascolare animali con ``herdable 1`` (ad esempio pecore). Il
predefinito è ``0``; abilita la pastorizia esplicitamente per tipo di lavoratore in ``rules.txt``.

:strong:```can_capture`` — ``1`` o ``0``. Predefinito ``1``. Su unità con skill ``attack``: quando
``0``, il clic destro su nemici con ``capture_hp_threshold 100`` usa attacco/movimento normale invece
dell’ordine di cattura predefinito; anche la cattura a contatto dell’IA è disabilitata. Vedi Cattura / ordine di
occupazione predefinito sopra.

Sistema di caccia (stile Age of Empires)

Vedi ``../player/hunting.htm``. Riepilogo:

- I lavoratori Backspace/clic destro su ``is_huntable`` attaccano (l’attacco normale infligge danno); le uccisioni generano ``food_deposit`` (es. ``food_carcass``) e completano l’ordine senza beep falso ``order_impossible``.
- Attr animali: ``is_huntable``, ``flee_on_hit``, ``herdable``, ``food_deposit``, ``food_deposit_qty``, ``no_number``.
- Spawn sulla mappa: ``computer_only 0 0 neutral \<casella\> \<conteggio\> deer``; le mappe casuali aggiungono fauna vicino agli inizi.
- Voce: le unità con ``is_huntable`` / ``herdable`` sono annunciate come "deer , animal", non "neutral , NPC". Ctrl+Shift+F4 su un giocatore solo fauna dice "you are animal". Gli NPC di storia (``quest_npc``, ecc.) dicono ancora "neutral , NPC".
- Diplomazia: uno slot ``computer_only`` con sola fauna (``deer`` / ``sheep`` / ``tiger`` personalizzato, ecc.) non entra nell’alleanza ``"ai"`` e non si allea con giocatori, creep ostili o altri branchi di fauna; gli slot misti restano invariati. Vedi ``../player/hunting.htm`` §3.1.
- Tech ``hunting_techniques``: raccolta più veloce da frutteti/carcasse.

Esempio animale::

    def deer
    class soldier
    is_huntable 1
    flee_on_hit 1
    food_deposit food_carcass
    food_deposit_qty 35
    no_number 1
    ai_mode guard

Ereditarietà (da 1.3.8.3)
--------------------------

::

    is_a footman                    ; tutti gli attributi
    is_a footman(hp_max mdg)        ; selettiva
    is_a footman(apart hp_max)      ; ereditarietà per esclusione (forma apart)
    is_a footman(-hp_max)           ; ereditarietà per esclusione (prefisso -, uguale ad apart)
    is_a footman(-hp_max -mdg)      ; escludi più attributi
    is_a footman(mdg) knight(hp_max) ; più genitori

style
------

Lo stile è definito in "ui/style.txt" e nella versione localizzata di "style.txt".

shortcut
>>>>>>>>

Ordini semplici, ordini di costruzione, ordini di addestramento, ordini che usano un’abilità possono essere dati con una scorciatoia, se una scorciatoia è definita.

Per definire una scorciatoia, definisci una proprietà "shortcut" seguita dalla lettera corrispondente. La lettera deve essere in minuscolo.

Se l’ordine è un ordine semplice, la scorciatoia deve essere definita dall’ordine (es: patrol).
Se l’ordine è un ordine complesso (train, build, use an ability), la scorciatoia deve essere definita dalla seconda parte dell’ordine.
Ad esempio, definisci una scorciatoia "m" per l’abilità meteor così che il mago avrà la scorciatoia "m" per lanciare meteore.

intro (da 1.4.1.5)
>>>>>>>>>>>>>>>>>>

Aggiungi una descrizione dell’unità sotto ``title``::

    def footman
    title 87
    intro 1001

Il testo deve esistere in ``tts.txt``.

Sistema sonoro di combattimento (da 1.3.8.2; 1.4.4.6 ha rinominato matk/ratk in mdg/rdg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Sostituisce i vecchi suoni di attacco::

    launch_mdg / launch_rdg
    mdg_hit / rdg_hit / mdg_hit_vs / rdg_hit_vs
    mdg_missed / rdg_missed
    mdg_dodge / rdg_dodge
    launch_charge_mdg / launch_charge_rdg
    charge_mdg_hit / charge_rdg_hit
    casting
    disappear
    weapon_switched
    death / falling / falling_delay / falling_on_<terrain>
    move / move_on_<terrain>

**Urla di battaglia (riproduzione a livelli da 1.4.5.0; vedi :doc:`battle-shouts`)**

- ``shouts`` — pool di urla di combattimento; definisci su ``def walking_unit`` così che fanteria e arcieri ereditino

**Passi sul terreno e suoni di caduta (da 1.3.9.1; nomi di tipo terreno da 1.4.5.0)**

In ``def unit`` (o un’unità specifica) in ``style.txt``:

- ``move`` — suoni di passo predefiniti
- ``move_on_<key>`` — passi che dipendono dal terreno
- ``falling`` — suono generico di caduta del corpo dopo la morte
- ``falling_delay <secondi>`` — attendi dopo ``death`` prima di ``falling``; ometti o ``0`` per riproduzione immediata
- ``falling_on_<key>`` — suono di caduta specifico del terreno

Risoluzione di ``<key>`` (uguale per ``move_on_`` e ``falling_on_``):

1. **Nome del tipo di terreno** — la def ``rules.txt`` / ``style.txt`` sulla casella dell’unità (es. ``ocean``, ``plain``, ``mountain``). Con terreno a sottocella, si usa il tipo alle coordinate dell’unità.
2. **Categoria ``ground``** — il valore ``ground`` sulla def ``style.txt`` di quel terreno (es. ``creek`` con ``ground water`` corrisponde a ``move_on_water`` / ``falling_on_water``).

Il nome del tipo di terreno è provato prima di ``ground``. ``falling_on_ocean`` funziona su ``ocean`` anche quando quella def non ha una riga ``ground``; su ``creek``, ``falling_on_creek`` ha priorità su ``falling_on_water`` quando esistono entrambi.

Esempio::

    def unit
    move 1052 1053
    move_on_ocean 1088 1348
    move_on_water 1088 1348
    move_on_grass 1053 1054
    falling 80051
    falling_delay 1
    falling_on_ocean fallwater
    falling_on_water splash

Solo le unità **a terra** usano il terreno della casella per ``move_on_``; altrimenti si usa ``move``. Anche oggetti immobili vicini (edifici, alberi, ecc.) possono fornire ``move_on_<tipo oggetto>`` o ``move_on_<ground>`` quando sono più vicini.

Le unità a raffica sparano ``launch_mdg`` / ``launch_rdg`` una volta per colpo in una raffica
``damage_seq``. Puoi elencare più ID suono sulla stessa riga così ogni colpo sceglie tra di essi.

``mdg_hit_vs`` / ``rdg_hit_vs`` possono riprodurre suoni di colpo diversi per tipo di bersaglio. L’insieme di
corrispondenza del bersaglio include il tipo di unità, i tipi di unità ereditati e i tipi di buff/debuff attualmente
attivi sul bersaglio. Esempio::

    def swordsman
    mdg_hit_vs b_absolute_defense iron_clang

Quando ``swordsman`` colpisce un bersaglio che ha attualmente ``b_absolute_defense``, viene riprodotto ``iron_clang``.

Da 1.4.4.6, documentazione e risorse in bundle usano i nomi ``mdg`` / ``rdg``. Le vecchie
chiavi ``matk`` / ``ratk`` restano disponibili come fallback di compatibilità per le mod esistenti.

Anche skill, buff e debuff possono definire suoni di trigger::

    def skill_counter
    alert counter_alert
    ready counter_ready
    triggered counter_proc

    def b_absolute_defense
    triggered shield_on
    noise loop shield_hum

Le skill usate manualmente riproducono ``alert``. Se una regola di skill ha ``ready \<secondi\>``, lo stile della skill
può definire ``ready \<suono\>``; i trigger manuali e automatici lo riproducono all’inizio della preparazione.
Le skill attivate da ``active_trigger_skills``,
``passive_trigger_skills``, ``attack_trigger_skills`` o ``attack_replace_skills`` preferiscono
``triggered`` e ripiegano su ``alert`` quando ``triggered`` non è configurato. Buff e
debuff applicati tramite campi trigger riproducono il proprio suono ``triggered`` quando configurato.
I suoni di stato persistenti di buff/debuff devono essere scritti esplicitamente come ``noise loop \<suono\>`` o
``noise repeat \<intervallo\> \<suono...\>``; ``noise \<suono\>`` mantiene il comportamento di parsing esistente
e non è trattato automaticamente come loop.

Musica di menu e di gioco (da 1.4.0.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

In ``def parameters``::

    menu_music <id>
    campaign_music <id>
    game_creation_music <id>
    server_lobby_music <id>
    game_music <id>
    battle_music <id>
    victory_sound <id>
    defeat_sound <id>
    main_menu_select_sound <id>
    main_menu_confirm_sound <id>

Musica di fazione (da 1.4.0.3)::

    china_music china
    china_battle_music china_battle

Override di mappa: ``map_music``, ``map_battle_music``, ``map_victory_sound``, ``map_defeat_sound``.
File musicali: ``ui/music/\<id\>.mp3`` o ``mods/\<mod\>/ui/music/\<id\>.mp3``.
