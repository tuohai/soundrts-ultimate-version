Guida del giocatore SoundRTS — Inizia da qui
=============================================



Un percorso di lettura progressivo: basi → RTS di base → funzioni moderne → multigiocatore → mod.

Autori di mod: `Guida per sviluppatori <../mod/getting-started.htm>`_.


----


Cos'è SoundRTS?
----------------


Un gioco di strategia in tempo reale audio ispirato a Warcraft e StarCraft, pensato per giocatori non vedenti e per chiunque ami comandare a orecchio. Due modalità di visuale:


.. list-table::
   :header-rows: 1

   * - Modalità
     - Come entrare
     - Ideale per
   * - Modalità mappa (predefinita)
     - all'avvio
     - Macro: selezionare unità, dare ordini, controllare risorse
   * - Modalità in prima persona (RPG)
     - Alt+Space / Ctrl+Space
     - Micro: camminare, mirare le abilità




----


Livello 1 — Partenza in dieci minuti
-------------------------------------


Obiettivo: selezionare un contadino, estrarre oro, costruire una fattoria e una casa.


.. list-table::
   :header-rows: 1

   * - Azione
     - Tasto
   * - Unità amica successiva
     - Q
   * - Edificio successivo
     - W
   * - Comando successivo / precedente
     - A / Shift+A
   * - Bersaglio successivo / precedente
     - Tab / Shift+Tab
   * - Conferma
     - Enter
   * - Comando predefinito sul bersaglio
     - Backspace



Risorse: Z oro · X legno · Shift+Z cibo · C popolazione.

Movimento: frecce, Page Up/Down tra le caselle interessanti, Space per seguire la selezione.

Elenco completo dei comandi: `manual.rst <../../../player/manual.rst>`_ §3, oppure menu F10 in partita.


----


Livello 2 — Ciclo RTS di base
------------------------------


- Economia: contadini → case (limite di popolazione) e fattorie (cibo) → edifici → esercito
- Punto di raduno: seleziona il municipio → Tab sulla miniera d'oro → Backspace
- Gruppi: Shift+6–9 per salvare, 6–9 per richiamare
- Esplorazione: la modalità difesa fugge dai nemici più forti
- Movimento/attacco forzato: Ctrl+Backspace
- Zoom: F8 (sotto-caselle per un posizionamento preciso)

Consigli: `unit-default-behavior <unit-default-behavior.htm>`_


----


Livello 3 — Funzioni moderne (1.4+)
------------------------------------



.. list-table::
   :header-rows: 1

   * - Argomento
     - Documentazione
   * - Attributi / inventario / equipaggiamento
     - [inventory-and-equipment.md](inventory-and-equipment.htm)
   * - Traguardi, gradi, arsenale
     - [achievements.htm](achievements.htm)
   * - Punteggio a fine partita (S–E)
     - [score-and-grades.md](score-and-grades.htm)
   * - Carte pre-missione
     - [loadout-cards.md](loadout-cards.htm)
   * - Campagne e cooperativo
     - [campaign-and-co-op-improvements.md](campaign-and-co-op-improvements.htm)
   * - Mappe casuali (seed / codice di condivisione)
     - [random-map.md](random-map.htm)
   * - Scorciatoie a livelli
     - [layered-hotkeys.md](layered-hotkeys.htm)
   * - Portare oggetti a una casella
     - [brought-item-delivery.md](brought-item-delivery.htm)



----


Livello 4 — Multigiocatore
---------------------------


Menu principale → multigiocatore → scegli il server → crea/unisciti a una stanza → chat F7. Squadre fisse prima dell'inizio; alleanze dinamiche F12 / F4 / Ctrl+F4 quando consentito. Porta predefinita 2500.


----


Livello 5 — Mod e documentazione tematica
------------------------------------------


Attiva in ``user/SoundRTS.ini``: ``mods = soundpack,starcraft`` oppure ``--mods=...``


.. list-table::
   :header-rows: 1

   * - Argomento
     - Documentazione
   * - Caccia / pastorizia
     - [hunting.htm](hunting-system.htm)
   * - Attacchi a raffica
     - [burst-attack-damage-seq.md](burst-attack-damage-seq.htm)
   * - Risorse StarCraft
     - [starcraft-resources.htm](starcraft-resources-vespene.htm)
   * - Addon Terran
     - [starcraft-terran.htm](starcraft-terran-addons.htm)
   * - Creep Zerg
     - [starcraft-zerg-creep.md](starcraft-zerg-creep.htm)



Aggiornamenti automatici
~~~~~~~~~~~~~~~~~~~~~~~~

All’avvio il gioco controlla di default se c’è un Release più recente su GitHub. Invio aggiorna, Esc annulla.
Attiva/disattiva in Opzioni → **Controlla aggiornamenti all’avvio del gioco**. La build Windows può scaricare e installare; dal codice sorgente si apre solo la pagina di download. Vedi il manuale e le `Note di rilascio <../../relnotes.htm>`_ (1.4.6.3).


Note di rilascio: `Note di rilascio <../../relnotes.htm>`_ — cronologia completa delle versioni.


----


Prossimi passi
---------------


- Completa il tutorial → documentazione del Livello 3 quando serve
- Modding: `Guida per sviluppatori <../mod/getting-started.htm>`_
- Indice: `README.md <README.htm>`_
