Tutorial sulla creazione di IA
==============================

.. contents::

1. Introduzione
---------------

Questo tutorial spiega come scrivere IA per il computer.
Modifichi ``ai.txt`` (script) e, per le mod, ``rules.txt`` (mappature di
difficoltà per fazione). Questi file si trovano nella cartella ``res`` del
pacchetto SoundRTS; una mod, una campagna o una mappa possono fornire anche
le proprie copie.

Un’IA è un piccolo script: un elenco di comandi che il computer esegue
dall’alto verso il basso, in loop infinito. Non serve conoscenza di
programmazione.

2. ``ai.txt``: script IA
------------------------

In ``ai.txt``, ogni IA inizia con ``def \<name\>`` seguito dai suoi comandi::

    def tang_empire_easy
    research 1
    workers 12
    get 9 villager 5 footman
    attack
    goto -1

Note:

- I nomi possono essere qualsiasi identificatore, es. ``tang_empire_easy`` o
  ``my_mod_hard``. I nomi personalizzati non compaiono nel menu di invito; i
  giocatori vedono il livello di difficoltà mappato in ``rules.txt``
  (sezione successiva).
- Se l’``ai.txt`` di una mod contiene ``clear``, ogni script IA caricato finora
  (inclusi i cinque livelli base di ``res/ai.txt``) viene scartato. Ciò non
  cambia quanti pulsanti di invito appaiono; influisce solo su quali voci
  ``def`` restano caricate. La maggior parte delle mod non ha bisogno di
  ``clear``.
- Righe ``def`` con lo stesso nome in un livello successivo sovrascrivono
  quelle precedenti.
- Se a runtime non esiste uno script per il livello richiesto, ``get_ai``
  ricade sullo script definito più vicino (inclusa la catena di alias legacy
  ``easy`` / ``aggressive``).

3. Menu di invito e mappature in ``rules.txt``
----------------------------------------------

I menu di invito computer in singolo e multigiocatore sono guidati dalla
``rules.txt`` della mod corrente, non da un elenco fisso di cinque pulsanti.
Non servono righe segnaposto vuote come ``def beginner`` in ``ai.txt``.

Senza una mod
~~~~~~~~~~~~~

Il menu offre sempre i cinque livelli standard:

- ``beginner`` -- Principiante (初级)
- ``intermediate`` -- Intermedio (中级)
- ``advanced`` -- Avanzato (高级)
- ``expert`` -- Esperto (专家)
- ``nightmare`` -- Incubo (噩梦)

Con una mod caricata
~~~~~~~~~~~~~~~~~~~~

Il motore scansiona i blocchi di fazione in ``rules.txt`` alla ricerca delle
righe di mappatura difficoltà. Ogni livello compare nel menu quando almeno
una fazione mappa quel livello a un nome di script che esiste come ``def``
in ``ai.txt``.

Consigliato (nuove mod) -- nomi di livello standard dentro ogni blocco
fazione::

    def tang_empire
    class race
    townhall county_government
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

Questo produce Invita computer principiante / intermedio / avanzato (tanti
pulsanti quante le mappature). Se il giocatore sceglie "beginner" con la
fazione Tang, gira lo script ``tang_empire_easy``.

Mod legacy -- che usano ancora ``easy`` / ``aggressive``::

    def orc
    class race
    ...
    easy orc_defensive
    aggressive orc_aggressive

Il menu mostra Invita computer quieto / aggressivo (etichette difensivo /
aggressivo nell’UI cinese). L’host invita comunque il livello ``easy`` o
``aggressive``; ``rules.txt`` risolve lo script reale per fazione.

Riepilogo
~~~~~~~~~

- ``ai.txt`` contiene gli script; ``rules.txt`` mappa i livelli agli script
  per fazione.
- Fazioni diverse possono mappare lo stesso livello a script diversi; il menu
  elenca solo i nomi dei livelli, non i nomi degli script specifici di
  fazione.
- Se sono mappati sia ``beginner`` sia ``easy``, viene elencato solo
  ``beginner``.
- Script interni come ``timers`` non compaiono mai nel menu di invito.
- Gli host multigiocatore inviano ``invite_ai \<tier\>`` (es.
  ``invite_ai beginner``). I comandi legacy ``invite_beginner``, ecc.
  funzionano ancora.

4. Impostazioni (scritte una volta, vicino all’inizio di un "def")
------------------------------------------------------------------

Queste regolano il comportamento complessivo dell’IA. Mettili vicino all’inizio
di un ``def`` così girano prima del loop. Una difficoltà più alta di solito
significa un’economia più grande, ricerca attiva, più basi e più voglia di
attaccare.

- ``constant_attacks 0/1`` -- quando ``1`` l’IA continua ad attaccare ed
  esplorare la mappa invece di barricarsi a casa.
- ``research 0/1`` -- quando ``1`` l’IA ricerca upgrade di armi/armature/
  abilità ogni volta che può permetterseli.
- ``workers \<n\>`` -- il numero di lavoratori (contadini) che l’IA cerca di
  mantenere. Più lavoratori significa un’economia più forte. Predefinito:
  ``10``.
- ``expand \<n\>`` -- il numero totale di municipi (basi) da mantenere. La
  base iniziale conta, quindi ``expand 2`` fa costruire all’IA una base
  extra. Predefinito: ``0`` (nessuna espansione extra).
- ``attack_ratio \<percent\>`` -- quanto deve essere forte l’esercito dell’IA,
  rispetto al nemico nell’area obiettivo, prima di attaccare. ``180`` (il
  predefinito) significa "attacca solo con un vantaggio dell’80%" (cauto).
  Valori più bassi fanno impegnare l’IA prima; sotto ``100`` attacca anche
  quando è leggermente più debole (pressione incessante).
- ``counter_skill \<0-100\>`` -- quanto bene le unità dell’IA usano i bonus
  di contro ``mdg_vs`` / ``rdg_vs`` nella scelta dei bersagli e nell’invio
  degli attacchi. ``0`` ignora i contro (priorità pura ``menace``). ``100``
  sceglie sempre il miglior match di contro, inclusi i tipi ereditati via
  ``is_a`` (ad esempio, ``mdg_vs cavalry`` contrasta anche un cammello con
  ``is_a cavalry``). I valori intermedi mescolano bonus di contro e
  ``menace``. Predefinito se omesso: ``100``.

  Il ``res/ai.txt`` vanilla imposta: beginner ``25``, intermediate ``50``,
  advanced ``75``, expert ``90``, nightmare ``100``.
- ``starting_resources \<amounts...\>`` -- risorse bonus aggiunte sopra
  l’inizio della mappa (o della fazione). Stesso ordine e stesse unità di
  ``starting_resources`` di mappa (es. ``10 10`` = 10 oro e 10 legno;
  memorizzate internamente come ``× 1000`` come gli inizi di mappa).
  Omesso = nessun bonus.
- ``starting_units \<unit\>...`` -- unità o edifici bonus generati sulla
  casella di partenza dell’IA dopo l’inizio normale. Usa la stessa sintassi
  piatta di ``starting_units`` di mappa (metti un conteggio prima di un nome
  tipo per generarne diversi: ``5 footman 2 archer``). Rispetta i nomi
  ``equivalent`` della fazione. **Consumano popolazione** (come le unità
  iniziali di mappa; alza il tetto con ``starting_population`` se serve).
  Omesso = nessuna unità bonus.
- ``starting_population \<n\>`` -- bonus al tetto di popolazione aggiunto
  sopra case e altre unità ``population_provided``. Intero semplice (non
  ``× 1000``). ``available_population`` resta comunque limitato dal
  ``global_population_limit`` della mappa.
- ``train_time \<pct\>`` -- percentuale della durata normale di addestramento
  (``100`` = normale, ``50`` = metà tempo). Solo ``train`` e morph-as-train.
  Omesso = ``100``.
- ``research_time \<pct\>`` -- percentuale della durata normale di ricerca /
  avanzamento (``100`` = normale, ``80`` = 20% più veloce). Solo
  ``research`` / ``advance``. Omesso = ``100``.
- ``unit_hp \<pct\>`` -- percentuale dei PV normali di tutte le unità di
  questo computer (``100`` = normale, ``120`` = +20% PV). Dopo
  ``enemy_hp_factor`` coop. Omesso = ``100``.

  Queste righe sono applicate una volta all’inizio della partita; non fanno
  parte del loop dello script (a differenza di ``get`` / ``attack``).

  Bonus del ``res/ai.txt`` vanilla (sopra ogni inizio di mappa):

  - intermediate: ``starting_resources 50 50``, ``starting_population 10``
  - advanced: ``100 100`` + ``2 footman 2 archer``, ``starting_population 20``,
    ``train_time 50``, ``research_time 80``
  - expert: ``200 200`` + ``5 footman 4 archer 2 knight``, ``starting_population 40``,
    ``train_time 50``, ``research_time 70``, ``unit_hp 120``
  - nightmare: ``400 400`` + ``8 footman 6 archer 4 knight``, ``starting_population 60``,
    ``train_time 40``, ``research_time 60``, ``unit_hp 140``
- ``watchdog \<seconds\>`` -- una rete di sicurezza: se l’IA è bloccata sulla
  stessa riga per così tanto tempo, passa alla riga successiva. ``0`` lo
  disabilita.

Mirare ai contro (``counter_skill``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quando ``counter_skill`` è sopra ``0``, le unità del computer preferiscono i
nemici che contrastano secondo i bonus di danno di ``rules.txt``:

- Un cavaliere con ``mdg_vs archer 12`` si concentra sugli arcieri rispetto a
  unità con ``menace`` più alto.
- Un arciere con ``rdg_vs footman 7`` si concentra sui fanti.
- I nomi di tipo in ``mdg_vs`` / ``rdg_vs`` corrispondono al ``type_name`` del
  bersaglio o a qualsiasi nome nella sua catena di eredità ``is_a``.

Con ``counter_skill`` basso, i bersagli ad alto ``menace`` possono ancora
vincere; a ``100``, vince il miglior match di contro a meno che non ci sia
un solo nemico a portata.

Da 1.4.5.2, il ``menace`` predefinito è un **punteggio di combattimento multidimensionale**
(danno, cover/precisione, cooldown, ready/wind-up, HP, armatura, schivata, portata, velocità),
opzionalmente sovrascrivibile con ``menace_mult`` / ``menace_vs`` — vedi ``modding.rst``
*Menace automatica / priorità di bersaglio*.

Questo influisce sia sul micro (quale nemico attacca ogni unità) sia sul
macro (quale area spingere e quali unità inviare per prime), purché
l’esercito soddisfi ancora ``attack_ratio``.

5. Comandi di azione
--------------------

- ``get \<n\> \<unit\>...`` -- recluta o costruisci finché l’IA possiede
  ``\<n\>`` di ciascuna unità/edificio elencata. Puoi elencare più coppie
  insieme. Vedi ``rules.txt`` per i nomi esatti dei tipi di unità.
  Esempio: ``get 10 footman 20 archer 10 knight``
- ``attack`` -- da questo punto in poi, attacca quando è abbastanza forte
  (attiva anche ``constant_attacks``).
- ``wait \<seconds\>`` -- resta su questa riga per ``\<seconds\>`` prima di
  continuare. Utile per il ritmo (un’IA facile può ``wait`` tra le ondate).
  Nota: un ``watchdog`` diverso da zero può comunque far uscire l’IA dalla
  riga in anticipo.

6. Controllo di flusso
----------------------

- ``label \<name\>`` -- marca una posizione a cui puoi saltare.
- ``goto \<name\>`` -- salta a un’etichetta. ``goto`` accetta anche un offset
  di riga relativo come ``goto -1`` (torna indietro di una riga).
- ``goto_random \<name1\> \<name2\> ...`` -- salta a una delle etichette
  elencate, scelta a caso. Ottimo per rendere l’IA imprevedibile.

7. Esempio di mod (tre livelli, script per fazione)
---------------------------------------------------

Estratto ``ai.txt``::

    def tang_empire_easy
    constant_attacks 0
    get 9 villager 5 footman
    attack
    goto -1

    def tang_empire_hard
    constant_attacks 1
    get 9 villager 10 footman
    attack
    goto -1

Estratto ``rules.txt`` per la fazione Tang::

    def tang_empire
    class race
    peasant villagers
    ...
    beginner tang_empire_easy
    intermediate tang_empire_hard
    advanced tang_empire_hard

Il menu mostra tre livelli; Tang + "intermediate" esegue ``tang_empire_hard``.

8. Esempio completo (un livello vanilla)
----------------------------------------

::

    def advanced

    counter_skill 75
    watchdog 480
    constant_attacks 1
    research 1
    workers 18
    expand 2          ; second base for a stronger economy
    attack_ratio 150  ; pushes with a smaller advantage

    label open
    get 9 peasant 6 footman 4 archer
    attack
    goto_random knights mixed

    label knights
    get 9 peasant 16 knight 10 archer 3 catapult
    attack
    goto open

    label mixed
    get 9 peasant 20 archer 12 knight 5 priest 4 catapult
    attack
    goto open

Tutto ciò che segue un ``;`` su una riga è un commento e viene ignorato.
