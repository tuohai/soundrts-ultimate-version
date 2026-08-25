Costruire ponti sull’acqua (campate casella per casella)
=======================================================

.. epigraph:: Per **autori di mod** e creatori di mappe: i lavoratori possono posare **campate di ponte percorribili** una casella d’acqua alla volta su fiumi, laghi e oceani. Completa ``modding.htm`` (cantieri) e ``building-land-terrain.htm`` (``big_bridge``, ``ford``).


----

Progetto
--------

- **Una casella di mappa = una campata di ponte**, non un singolo oggetto “ponte intero” che copre un fiume largo.
- La **costruzione** usa un ``BuildingSite`` (impalcatura): le unità di terra possono camminare su quella casella per costruire, ma **le impalcature incomplete non concedono il passaggio** (nessuna scorciatoia solo-impalcatura attraverso l’acqua).
- **A completamento**, la casella riceve la def ``bridge_terrain`` (predefinita ``bridge_deck``), si collega alla terra adiacente / alle campate finite ed è **neutrale** — tutti i giocatori di terra possono usarla.

Esempio integrato: ``wooden_bridge`` (richiede ``lumbermill``, 5 oro / 10 legno).

Attributi delle regole
----------------------

Su un ``class building`` in ``rules.txt``:

.. list-table::
   :header-rows: 1

   * - Attributo
     - Significato
   * - ``is_buildable_on_water_only 1``
     - Solo su caselle di **acqua pura** (``is_water`` senza ``is_ground`` di mappa — fiumi, laghi, oceani; non ``ford`` / ``big_bridge`` di mappa)
   * - ``bridge_terrain <name>``
     - Quando l’edificio **finisce**, applica questo ``class terrain`` alla casella (es. ``bridge_deck``)

Esempio di terreno finito::

    def bridge_deck
    class terrain
    is_water 1
    is_ground 1
    is_dynamic 0

Esempio di campata costruibile::

    def wooden_bridge
    class building
    cost 5 10
    hp_max 400
    time_cost 60
    is_buildable_on_water_only 1
    bridge_terrain bridge_deck
    requirements lumbermill

Flusso in gioco
---------------

1. Seleziona un lavoratore; dalla **terra adiacente**, ordina ``wooden_bridge`` su una casella d’acqua.
2. Viene posizionato un ``BuildingSite``; la cella diventa temporaneamente ``is_ground`` così il lavoratore può pathare **sull’impalcatura** (le tessere oceaniche con velocità di terra 0 riprendono velocità normale mentre sono impalcate).
3. Il lavoratore costruisce su quella casella — stesso TTS di qualsiasi cantiere: **“campata di ponte, in costruzione”** (titolo del tipo edificio + titolo ``buildingsite``).
4. Al completamento l’edificio ``wooden_bridge`` resta e viene applicato ``bridge_terrain``; la tessera diventa percorribile e si collega alla riva / ad altre campate finite.

Restrizioni dell’impalcatura
----------------------------

- Una sola uscita temporanea verso la **casella di riva da cui è stato dato l’ordine**; **nessun** passo diretto impalcatura-impalcatura.
- La sincronizzazione dei passaggi gira solo per ``bridge_terrain`` **finito**, non per impalcature nude.
- Le unità ``BuildingSite`` sull’acqua **non** annegono (esenzione ``is_a_building``).
- I suoni del martello si definiscono sul **lavoratore** (``noise_when_building``); lo stereo suona sul **cantiere**. Un cantiere con costruttori non sovrappone il proprio loop di martello.

Voce e passi (``style.txt`` / ``tts.txt``)
------------------------------------------

Come per le altre costruzioni: **nessuna** def di stile “scaffold” separata; i cantieri usano ``buildingsite`` ``title 107 128`` (“in costruzione”).

| ID TTS | Testo (zh) | Uso |
|--------|------------|-----|
| 153 | bridge (generico) | Tipo di uscita ``bridge`` |
| 4348 | trestle | Terreno di mappa ``big_bridge`` |
| 5108 | wooden bridge span | Unità ``wooden_bridge``, nome cantiere |
| 5109 | bridge deck | Terreno finito ``bridge_deck`` |

**Passi:** Durante l’impalcatura e dopo il completamento, l’audio usa il ``ground`` di ``bridge_terrain`` (predefinito ``bridge_deck`` ``is_a big_bridge`` → ``ground wood``).

**Voce della casella:** Durante la costruzione, la cella riporta ancora l’acqua sottostante; **“bridge deck”** viene annunciato solo dopo il completamento.

UI: Tab e passaggi
------------------

- ``wooden_bridge`` **non** è un’uscita; **Tab** al centro di una casella di ponte può selezionare l’edificio della campata.
- Sulle caselle ponte/impalcatura, le mappe con ``select_target no_exit`` (es. td2) ciclano comunque le **uscite di passaggio** con Tab.
- Ciclo dedicato dei passaggi: ``select_passage`` quando è assegnato.

Campate personalizzate (es. ponte di ferro)
-------------------------------------------

Definisci solo l’**edificio** + il **terreno finito** — nessuno stile ``bridge_scaffold``:

**rules.txt** — ``iron_bridge`` con ``bridge_terrain iron_bridge_deck``; **style.txt** — titoli e ``iron_bridge_deck is_a big_bridge`` (o ``ground`` personalizzato). I passi dell’impalcatura seguono ``bridge_terrain``; il TTS del cantiere resta “campata di ponte di ferro, in costruzione”.

Confronto con ``big_bridge`` di mappa
-------------------------------------

Le campate costruite dal giocatore usano ``bridge_deck`` a fine lavori, lasciano un’entità ``wooden_bridge`` distruttibile e tornano acqua impassabile se distrutte. Il ``big_bridge`` di mappa è fisso al caricamento senza entità edificio.

Implementazione e test
----------------------

``soundrts/world_build_rules.py``, ``worldorders/movement.py``, ``clientgameentity/properties.py``, ``audio.py``; test in ``soundrts/tests/test_bridge_terrain.py``.

Vedi anche ``building-land-terrain.htm``, ``modding.htm``.
