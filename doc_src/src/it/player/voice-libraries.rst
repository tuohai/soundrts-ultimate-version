Librerie vocali primaria e secondaria (giocatori)
=================================================


Il gioco usa due librerie vocali configurabili separatamente: primaria e secondaria. Puoi attivare o disattivare la secondaria; se è disattivata, la primaria annuncia tutto.


----


Compiti
-------


.. list-table::
   :header-rows: 1

   * - Libreria
     - Annuncia
   * - **Primaria**
     - Menu, operazioni del giocatore (selezione, movimento, modalità…), tutto fuori partita
   * - **Secondaria**
     - Solo eventi passivi in partita (perdite, scoperte, messaggi del mondo…)

Con secondaria **attiva**: le operazioni usano la primaria, gli eventi passivi la secondaria; possono sovrapporsi. Solo **Alt** interrompe la secondaria.

Con secondaria **disattivata**: la primaria dice tutto (stile a canale unico); le operazioni interrompono le linee passive.


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
- **Shift+F9–F12**: libreria secondaria
- **Shift sinistro+C** / **Shift destro+C**: copia ultima riga primaria / secondaria
- **Shift+A**: aggiungi agli appunti
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


----


Screen reader
-------------


Se viene rilevato uno screen reader dedicato (es. NVDA), può assumere i compiti della **primaria**. La secondaria (se attiva) usa ancora il profilo secondario del gioco.


----


Vedi anche
----------


- `Note di rilascio <../../relnotes.htm>`_ — 1.4.5.4
- `Manuale di gioco <manual.htm>`_
