Librerie vocali primaria e secondaria (giocatori)
=================================================


Il gioco usa due librerie vocali configurabili separatamente: primaria e secondaria. Puoi attivare o disattivare la secondaria; se è disattivata, la primaria annuncia tutto.

**Consiglio:** usare preferibilmente uno **screen reader** come voce primaria. Se il lettore è attivo, assume i compiti della libreria primaria e non serve impegnare ``F9``–``F12`` per «regolare la primaria». I tasti di questo gioco sono densissimi: **risparmiate scorciatoie quando potete**. La secondaria (campo di battaglia) si regola ancora con ``Shift+F9``–``F12``.


----


Compiti
-------


.. list-table::
   :header-rows: 1

   * - Libreria
     - Annuncia
   * - **Primaria**
     - Menu, operazioni del giocatore; tutto fuori partita; e in partita il **feedback economico/produzione** (unità/edificio pronto, ricerca, avanzamento era, risorse, menu cambiato…)
   * - **Secondaria**
     - Eventi passivi di **campo di battaglia** (nemici, perdite, scout, allarmi di combattimento, messaggi del mondo…)

Con secondaria **attiva**: primaria e secondaria possono sovrapporsi.

- **Alt sinistro**: salta/ferma la libreria **primaria**
- **Alt destro**: salta/ferma la libreria **secondaria**

Con secondaria **disattivata**: la primaria dice tutto; **Alt sinistro e Alt destro saltano la riga corrente** (non c’è una secondaria da filtrare).


----


Dove configurare
----------------


1. Menu principale → **Opzioni** → **Impostazioni libreria vocale**
2. Voci:
   - **Attiva o disattiva la voce secondaria** (oppure **F3** in qualsiasi menu; non in partita)
   - Editor **primaria** / **secondaria**: volume, tono, velocità, voce, scheda audio
   - **Apri cartella voci**: apre ``user/voices``


----


Parametri e tasti
-----------------


Nell’editor:

- Su/Giù: parametro (volume / tono / velocità / voce / dispositivo)
- Sinistra/Destra: regola
- Invio o Esc: indietro

In partita (e nei menu):

- **F9–F12**: libreria primaria
- **Shift+F9–F12**: libreria secondaria (qualsiasi Shift)
- **Shift destro+C**: copia ultima riga secondaria; **Shift destro+B**: aggiungi secondaria agli appunti
- **Shift sinistro+C / Shift sinistro+B** (primaria): **commentati** di default in ``res/ui/global_bindings.txt`` per ridurre i conflitti; togliere il ``;`` iniziale per attivarli
- **F3 nei menu**: attiva/disattiva secondaria (non in partita)


----


Aggiungere voci
---------------


Usa **Apri cartella voci** (di solito ``user/voices``).

Voci SAPI di Windows
~~~~~~~~~~~~~~~~~~~~

1. Installa e registra una voce SAPI5 in Windows.
2. In gioco, scorri il parametro **voce** in primaria o secondaria.
3. Alcune voci solo a 32 bit passano da ``tools/sapi32``.

Cartelle pacchetto (nomi amichevoli)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crea una sottocartella in ``user/voices`` con ``voice.ini``::

    [voice]
    title=Il mio nome
    sapi=Microsoft Huihui Desktop
    rate=0

- ``title``: nome nei menu
- ``sapi``: deve corrispondere a una voce SAPI registrata
- ``rate``: opzionale, circa -10…10

I pacchetti **non** installano un motore TTS; aliasano una voce SAPI esistente.

Nuance / voci Apple (opzionale)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Se i dati Nuance sono in ``user/voices/nuance``, compaiono nell’elenco. Vedi le note di quella cartella.

Primaria e secondaria possono usare **solo SAPI**; Nuance è opzionale e richiede l’helper Java a 32 bit in ``tools/nuance_ve``.


----


Avvisi direzionali in partita (pan stereo)
------------------------------------------


Alcune linee passive **legate a una casella** (nemico avvistato, perdite, scout, allarmi di combattimento) sono panoramizzate sinistra/destra rispetto alla casella di vista corrente (stessa logica dei SFX della minimappa).

Con cuffie: in vista dall’alto verso nord, est a destra e ovest a sinistra.

**Il pan si aggiorna se cambi casella a metà frase** (non serve attendere il messaggio successivo).


----


Screen reader
-------------


Se viene rilevato uno screen reader dedicato (es. NVDA), può assumere i compiti della **primaria**. La secondaria (se attiva) usa ancora il profilo secondario del gioco.


----


Vedi anche
----------


- `Note di rilascio <../../relnotes.htm>`_ — 1.4.5.4 (doppie librerie), 1.4.5.5 (pan, compiti, Alt sx/dx)
- `Manuale di gioco <manual.htm>`_
