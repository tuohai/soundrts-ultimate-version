# Schema di tasti rapidi a livelli

Questa guida descrive i tasti rapidi dell’interfaccia a livelli di SoundRTS: un livello globale di base più un livello per interfaccia, così lo stesso tasto fisico può significare cose diverse in modalità diverse. Pensata per giocatori e autori di mod che personalizzano le associazioni.


----


1. Panoramica e motivazione
---------------------------


Schema precedente
~~~~~~~~~~~~~~~~~


Tutti i tasti rapidi vivevano in un unico file ``res/ui/bindings.txt``. I tasti si saturavano; la stessa lettera entrava in conflitto tra selezione unità, ordini e navigazione mappa.

Nuovo schema
~~~~~~~~~~~~


- Livello globale: risorse, movimento, salti di casella, conferma comandi — disponibile in ogni modalità.
- Livello interfaccia: associazioni specifiche della modalità (unità, edificio, comando, abilità, mappa, ecc.).
- Cambio modalità: i tasti F commutano all’interno dei gruppi; aiuto / mappa / diplomazia sono modalità overlay che ripristinano la modalità precedente all’uscita.

Implementazione: ``soundrts/clientgame/interface_modes.py``.


----


2. Architettura e regole di caricamento
---------------------------------------


.. code-block:: text

   flowchart TD
       global[global_bindings.txt]
       mode[current mode txt]
       custom[cfg/bindings.txt]
       mod[mod bindings.txt]
       global --> merge[merged load]
       mode --> merge
       custom --> merge
       mod --> merge
       merge --> active[active hotkeys]


Ordine di caricamento
~~~~~~~~~~~~~~~~~~~~~


1. `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_ (base globale)
2. File della modalità corrente (vedi tabella sotto)
3. Sovrascritture utente `cfg/bindings.txt <../../../soundrts/paths.py>`_ (``CUSTOM_BINDINGS_PATH``)
4. ``bindings.txt`` di mod non stub (append legacy)

I caricamenti successivi sovrascrivono i precedenti per lo stesso tasto.

Sotto-schermate e RPG
~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Contesto
     - Comportamento
   * - Inventario / equipaggiamento / attributi
     - Sostituisce temporaneamente ``\_bindings``; ``restore_active_bindings`` all’uscita
   * - Prima persona RPG
     - Aggiuntivo [``res/ui/rpg_bindings.txt``](../../../res/ui/rpg_bindings.txt)
   * - Editor di mappe
     - Indipendente [``res/ui/editor_bindings.txt``](../../../res/ui/editor_bindings.txt)



File delle modalità
~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modalità
     - File
   * - Globale
     - ``global_bindings.txt``
   * - Selezione unità
     - ``unit_bindings.txt``
   * - Selezione edifici
     - ``building_bindings.txt``
   * - Comandi
     - ``command_bindings.txt``
   * - Abilità
     - ``skill_bindings.txt``
   * - Prima persona (RPG)
     - ``rpg_bindings.txt``
   * - Aiuto e interrogazione
     - ``help_bindings.txt``
   * - Navigazione mappa
     - ``map_bindings.txt``
   * - Diplomazia
     - ``diplomacy_bindings.txt``




----


3. Cambio modalità (tasti F ed ESC)
-----------------------------------



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - F1
     - Selezione unità ↔ Selezione edifici
   * - F2
     - Comandi ↔ Abilità
   * - F3
     - Inventario ↔ Equipaggiamento (serve una sola unità amica; vedi [inventory-and-equipment.md](inventory-and-equipment.htm))
   * - F4
     - Entra in aiuto e interrogazione (premi di nuovo o Esc per uscire)
   * - F12
     - Entra in diplomazia (premi di nuovo o Esc per uscire)
   * - ESC
     - Annulla ordine / esci dalla sotto-schermata; altrimenti entra in navigazione mappa



Il passaggio a modalità non-mappa annuncia il nome della modalità (ad es. “selezione unità”, “modalità comandi”).

Comportamento speciale quando ESC entra in navigazione mappa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Azione
     - Voce
     - Stato interno
   * - ESC → mappa
     - Annuncia sempre “navigazione mappa” + panoramica della casella corrente
     - Se in precedenza era selezionato un deposito/prato/passaggio, ripristina silenziosamente `interface.target`
   * - ``f`` / ``g`` / ``m`` / ``p`` in mappa
     - Annuncia l’elemento come di consueto
     - Salva la selezione per ripristinarla dopo aver lasciato la mappa



Esempio: in modalità mappa, ``f`` seleziona una miniera d’oro → F1 in modalità unità, seleziona un contadino → ESC torna alla mappa → senti “navigazione mappa, 8, 13, 1 town hall…” (panoramica casella), non di nuovo la miniera; il focus resta sulla miniera, così puoi premere Invio per inviare subito l’ordine di raccolta.

Uscendo dalla modalità mappa si salva il focus corrente tramite ``save_map_browse_target``.


----


4. Tasti rapidi globali
-----------------------


Sempre attivi in ogni modalità (``global_bindings.txt``).

Risorse e popolazione
~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``z``
     - Stato risorsa 1
   * - ``x``
     - Stato risorsa 2
   * - ``SHIFT Z``
     - Stato risorsa 3
   * - ``c``
     - Stato popolazione



Accesso rapido (legacy)
~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``ALT V``
     - Schermata attributi
   * - ``SHIFT V``
     - Inventario
   * - ``CTRL V``
     - Equipaggiamento



Selezione del bersaglio
~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``TAB`` / ``SHIFT TAB``
     - Bersaglio successivo / precedente
   * - ``CTRL TAB`` / ``CTRL SHIFT TAB``
     - Bersaglio utile successivo / precedente



Movimento
~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - Tasti freccia
     - Muovi di 1 casella
   * - ``SHIFT`` + frecce
     - Muovi di 5 caselle
   * - ``CTRL`` + frecce
     - Muovi di 1 casella (senza collisione)
   * - ``CTRL SHIFT`` + frecce
     - Muovi di 5 caselle (senza collisione)



Salti di casella
~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``PAGE DOWN`` / ``PAGE UP``
     - Casella esplorata successiva / precedente
   * - ``CTRL PAGE DOWN`` / ``CTRL PAGE UP``
     - Caselle in conflitto
   * - ``ALT PAGE DOWN`` / ``ALT PAGE UP``
     - Caselle sconosciute
   * - ``SHIFT PAGE DOWN`` / ``SHIFT PAGE UP``
     - Caselle con risorse



Comando predefinito e conferma
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``BACKSPACE``
     - Comando predefinito
   * - ``SHIFT BACKSPACE``
     - Comando predefinito (coda)
   * - ``CTRL BACKSPACE``
     - Comando predefinito (imperativo)
   * - ``RETURN`` / tastierino ``ENTER``
     - Convalida ordine
   * - Con ``SHIFT`` / ``CTRL``
     - Varianti coda / imperativo



Osservazione e interrogazione
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``LCTRL`` / ``RCTRL``
     - Esamina
   * - ``SPACE``
     - Stato unità
   * - ``v``
     - Punti ferita
   * - ``F9`` / ``SHIFT F9``
     - Obiettivi
   * - ``F11``
     - Elenco giocatori



Sistema
~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``F5`` / ``F6``
     - Cronologia precedente / successiva
   * - ``F10`` / ``CTRL C`` / ``ALT F4``
     - Menu di gioco
   * - ``HOME`` / ``END`` ecc.
     - Volume
   * - ``ALT SPACE`` / ``CTRL SPACE``
     - Modalità prima persona
   * - ``CTRL F2``
     - Attiva/disattiva display
   * - ``CTRL F3``
     - Attiva/disattiva orologio parlante
   * - ``CTRL SHIFT F4``
     - Cambia vista giocatore
   * - ``ALT M`` ecc.
     - Volume musica




----


5. Tasti rapidi per interfaccia
-------------------------------


5.1 Selezione unità
~~~~~~~~~~~~~~~~~~~


File: ``unit_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Categoria
     - Tasti
     - Note
   * - Gruppo soldati
     - ``a``
     - Tutti locali; ``CTRL a`` su tutta la mappa
   * - Cicla unità
     - ``q`` / ``SHIFT q``
     - Locale; ``CTRL q`` su tutta la mappa
   * - Scorciatoia ordine
     - ``b``
     - Usa ``shortcut`` dagli ordini di style.txt
   * - Filtri
     - ``m`` / ``n``
     - Fazione / tipo nella scelta dei bersagli
   * - Lavoratori
     - ``s`` gruppo / ``w`` cicla
     - Ex tasti ``d``/``e``
   * - Soldati 1–7
     - `d/e` … `;/p`
     - Stessa zona tasti degli edifici
   * - Gruppi
     - ``1``–`5` imposta, `6`–`9` richiama
     - ``CTRL`` per gruppi su tutta la mappa



La modalità unità può sovrascrivere ``BACKSPACE`` localmente.

5.2 Selezione edifici
~~~~~~~~~~~~~~~~~~~~~


File: ``building_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Riga di tasti
     - Corrisponde a
   * - ``d f g h j k l ;``
     - building1 – building8
   * - ``e r t y u i o p``
     - building9 – building16



Per tasto: seleziona il tipo locale; ``SHIFT`` + tasto cicla uno; ``CTRL`` + tasto seleziona su tutta la mappa.

Configurazione mod: imposta ``keyboard building1`` … ``keyboard building16`` in ``style.txt`` (insieme al generico ``keyboard building``). Esempio campagna base: townhall→building1, house→building2.

5.3 Modalità comandi
~~~~~~~~~~~~~~~~~~~~


File: ``command_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Slot
     - Tasti
   * - Sfoglia
     - ``a`` / ``SHIFT a``
   * - 1–9
     - `s d f g h j k l ;`
   * - 10–18
     - ``w e r t y u i o p``
   * - 19–30
     - ``1``–`0` `-` `=`
   * - Ripeti
     - ``ALT x`` / ``ALT z``



Gli slot seguono l’ordine del menu dell’unità; i tasti in eccesso dicono “none” se esistono meno di 30 ordini.

5.4 Modalità abilità
~~~~~~~~~~~~~~~~~~~~


File: ``skill_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``a`` / ``SHIFT a``
     - Sfoglia il menu abilità (successiva / precedente)



5.5 Modalità prima persona (RPG)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Quando entri in modalità prima persona (globale ``ALT SPACE``), ``rpg_bindings.txt`` si sovrappone alle associazioni dell’interfaccia corrente.


.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - `1`–`9`
     - Abilità 1–9
   * - ``0``
     - Abilità 10
   * - `-` / `=`
     - Abilità 11 / 12
   * - ``ALT /``
     - Elenco abilità
   * - ``CTRL A``
     - Attacco automatico
   * - ``CTRL F8`` / ``SHIFT F8`` / ``ALT F8``
     - Precisione zoom su / giù / interroga



I tasti direzione e ``SHIFT`` + direzione muovono e girano in prima persona (vedi i commenti nel file).

5.6 Navigazione mappa
~~~~~~~~~~~~~~~~~~~~~


File: ``map_bindings.txt``

Movimento e salti di casella sono globali (sezione 4).

Questi tasti ciclano i bersagli sulla casella corrente (senza cambiare casella):


.. list-table::
   :header-rows: 1

   * - Tasto
     - Azione
   * - ``f`` / ``r``
     - deposito resource1 (ad es. oro)
   * - ``g`` / ``t``
     - deposito resource2 (ad es. legno)
   * - ``y`` / ``h``
     - deposito resource3 (ad es. cibo)
   * - ``m`` / ``SHIFT m``
     - Prato
   * - ``p`` / ``SHIFT p``
     - Passaggio / ponte
   * - ``F8`` series
     - Zoom



Dopo aver selezionato un deposito, usa il globale ``BACKSPACE`` / ``RETURN`` per dare l’ordine di raccolta; prato per costruire; passaggio per muovere/bloccare.

5.7 Aiuto e diplomazia
~~~~~~~~~~~~~~~~~~~~~~


Aiuto (`help_bindings.txt <../../../res/ui/help_bindings.txt>`_): ``1``/``2`` sfoglia aiuto, ``3`` dice l’ora, ``F7`` parla, ``CTRL SHIFT F3`` attiva/disattiva display del tick.

Diplomazia (`diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_): ``1`` seleziona candidato, ``q`` richiedi, ``w`` accetta, ``e`` rifiuta/annulla.

``ESC`` nelle modalità overlay chiama ``exit_overlay_mode``.


----


6. Flussi di lavoro tipici
--------------------------


Raccolta
~~~~~~~~


1. Modalità unità: ``s`` seleziona contadino
2. ``F2`` modalità comandi, ``s`` scegli raccolta (o ``b`` + lettera scorciatoia)
3. ``ESC`` navigazione mappa
4. ``f`` seleziona miniera d’oro (annunciata)
5. ``RETURN`` per confermare

Se hai già selezionato una miniera e hai lasciato la mappa: ``ESC`` di ritorno annuncia la panoramica casella; il focus resta sulla miniera — premi ``RETURN`` direttamente.

Costruzione
~~~~~~~~~~~


1. ``ESC`` mappa → ``m`` seleziona prato
2. ``F2`` scegli lo slot di costruzione
3. ``RETURN`` conferma

Diplomazia
~~~~~~~~~~


1. ``F12`` diplomazia
2. `1` seleziona candidato
3. ``q`` richiesta di alleanza

.. code-block:: text

   sequenceDiagram
       participant U as UnitMode
       participant C as CommandMode
       participant M as MapMode
       U->>U: s select peasant
       U->>C: F2
       C->>C: s order slot 1
       C->>M: ESC
       M->>M: f select mine
       M->>C: RETURN validate



----


7. Personalizzazione per le mod
-------------------------------


Quale file modificare
~~~~~~~~~~~~~~~~~~~~~


- Comportamento globale: ``global_bindings.txt``
- Una interfaccia: il corrispondente `*_bindings.txt`
- Non modificare il corpo di ``bindings.txt`` (solo stub) a meno di conoscere il comportamento di append legacy delle mod

Modificatori
~~~~~~~~~~~~

- Consentiti: ``CTRL``, ``ALT``, ``SHIFT`` (qualsiasi lato), ``LSHIFT``, ``RSHIFT`` (più tasti standalone come ``LALT`` / ``RALT``).
- Non mettere ``LSHIFT``/``RSHIFT`` e ``SHIFT`` sulla stessa riga; la ricerca preferisce il lato specifico, poi ``SHIFT`` generico.

Sovrascritture utente
~~~~~~~~~~~~~~~~~~~~~


Mappatura in gioco (consigliata): Menu principale → Opzioni → Mappatura tasti (accanto a Schema tasti rapidi). Supporta schemi a livelli e classico, tutti i livelli, ricerca, varianti, tasti alias e import/export dagli appunti. Le impostazioni sono memorizzate per mod in ``user/hotkey_overrides/{mod_key}.json`` e si applicano alla partita successiva. Vedi `sviluppatore: editor mappatura tasti <../../mod/hotkey-mapping-editor.htm>`_.

Schema tasti rapidi: Opzioni → Schema tasti rapidi passa tra a livelli/classico; spostando la selezione si annuncia attivo o inattivo per lo schema corrente.

File manuale: aggiungi o sovrascrivi tasti in ``cfg/bindings.txt``; caricato per ultimo (ancora in append dopo le sovrascritture basate su JSON).

Note
~~~~


- Gli slot ``select_order_index`` dipendono dall’ordine del menu
- Gli slot ``buildingN`` richiedono ``keyboard buildingN`` in ``style.txt``
- L’unità ``b`` (``order_shortcut``) usa lo ``shortcut`` di ogni ordine in style


----


8. Tasti rapidi classici a file unico
-------------------------------------


Per ripristinare l’insieme di associazioni pre-1.4.3 (F4 richiesta alleanza, F12 candidato alleanza, ESC senza modalità navigazione mappa, ecc.):

Opzione A (consigliata): Menu principale → Opzioni → Schema tasti rapidi, poi scegli Tasti rapidi a livelli o Tasti rapidi classici.

Opzione B (modifica ini a mano):

1. Apri :strong:```user/SoundRTS.ini`` (spesso `%APPDATA%\SoundRTS\SoundRTS.ini` su Windows).
2. Sotto `````[general]```, aggiungi o imposta:

.. code-block:: ini

      layered_hotkeys = 0


3. Riavvia il gioco (deve essere impostato prima dell’inizio di una partita).

Quando è disabilitato:

- Viene caricato solo `res/ui/legacy_bindings.txt <../../../res/ui/legacy_bindings.txt>`_ — niente ``global_bindings.txt`` né livelli per modalità.
- Il ``bindings.txt`` non stub delle mod e ``user/bindings.txt`` vengono ancora aggiunti in append (le sovrascritture utente vincono).
- I comandi di cambio modalità F1/F2/F3/F4/F12/ESC emettono un beep; ESC annulla ordini / esce dalle sotto-schermate / esce da immersione o zoom, e non entra in modalità navigazione mappa.
- Inventario (``i``), equipaggiamento (``u``), attributi (Alt+V), ecc. seguono ``legacy_bindings.txt``.

Per riabilitare la modalità a livelli: imposta ``layered_hotkeys = 1`` (o rimuovi la riga; il predefinito è 1) e riavvia.


----


9. Differenze rispetto allo schema precedente
---------------------------------------------



.. list-table::
   :header-rows: 1

   * - Vecchio
     - Nuovo
   * - F1/F4 aiuto diretto
     - F4 entra in modalità aiuto; F9/F11 globalizzati
   * - F12 diplomazia diretta
     - F12 entra prima in modalità diplomazia
   * - Lavoratore ``d``/``e``
     - Modalità unità ``s``/``w``
   * - Tasti soldati
     - Rimappati su `d/e`…`;`/p`
   * - Mappa ``f`` saltava caselle
     - ``f`` cicla i depositi sulla casella corrente
   * - ESC verso mappa annunciava l’ultimo bersaglio
     - ESC annuncia la panoramica casella; il focus è ripristinato in silenzio



Le associazioni di attributi ed editor sono invariate.


----


File sorgente correlati
-----------------------


- `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_
- `res/ui/unit_bindings.txt <../../../res/ui/unit_bindings.txt>`_
- `res/ui/building_bindings.txt <../../../res/ui/building_bindings.txt>`_
- `res/ui/command_bindings.txt <../../../res/ui/command_bindings.txt>`_
- `res/ui/skill_bindings.txt <../../../res/ui/skill_bindings.txt>`_
- `res/ui/map_bindings.txt <../../../res/ui/map_bindings.txt>`_
- `res/ui/help_bindings.txt <../../../res/ui/help_bindings.txt>`_
- `res/ui/diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_
- `soundrts/clientgame/interface_modes.py <../../../soundrts/clientgame/interface_modes.py>`_
