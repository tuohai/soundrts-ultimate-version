Internazionalizzazione delle mod
================================


Impostazione della lingua
-------------------------


I giocatori possono cambiare lingua da menu principale → **Opzioni** → **Lingua** (salvata in ``language.txt`` dell’utente). Si può anche modificare quel file, oppure usare ``cfg/language.txt`` di installazione come ripiego se il file utente non esiste (es. ``zh``, ``fr``, ``it``). Il gioco scansiona le cartelle ``ui-xx`` tra le risorse caricate e sceglie la corrispondenza migliore.

Struttura delle directory
-------------------------


Le mod usano la stessa struttura della cartella ``res``; layout tipico:

.. code-block:: text

   mods/mymod/
     rules.txt
     mod.txt                 # opzionale
     ui/style.txt
     ui/tts.txt
     ui-zh/tts.txt
     ui-fr/tts.txt
     ui-it/tts.txt
     single/                 # opzionale: campagna dentro la mod
       my campaign/
         campaign.txt
         ui/tts.txt
         ui-zh/tts.txt
         ui-it/tts.txt


Tradurre i testi di gioco
-------------------------


1. In ``ui/style.txt`` imposta `title <ID numerico>` per unità/edifici ecc.
2. In ``ui/tts.txt`` scrivi ``7000 Pig Farm``.
3. In ``ui-it/tts.txt`` scrivi ``7000 Fattoria di maiali`` (l’ID deve coincidere).

Le frasi intere possono usare il formato con uguale: ``English phrase = Traduzione italiana``.

Codifica di tts.txt (importante)
--------------------------------


Salva sempre in UTF-8. Senza ``; coding:`` il motore legge per impostazione predefinita come UTF-8; la prima riga può avere ``; coding: utf-8`` (opzionale, aiuta alcuni editor).

I file legacy in GBK devono avere ``; coding: gbk`` sulla prima riga, altrimenti la decodifica fallisce.

Causa comune di caratteri corrotti: aprire ``tts.txt`` in VS Code/Cursor con la codifica sbagliata e risalvare — il testo può diventare `` e perdersi definitivamente. In caricamento il motore rileva ``U+FFFD`` e avvisa; se la decodifica fallisce genera un errore invece di sostituire in silenzio.

Nome della mod nel menu
-----------------------


Opzioni → Mod: l’elenco legge per impostazione predefinita il nome della cartella. Da 1.4.2.4 puoi impostare in ``mod.txt``:

.. code-block:: text

   title 7100


e definire la traduzione di ``7100`` in ogni ``tts.txt`` di lingua. Il meccanismo è lo stesso del ``title`` in ``campaign.txt`` delle campagne.

Se non vuoi modificare la mod stessa, aggiungi in ``res/ui-it/tts.txt`` o in una mod di traduzione:

.. code-block:: text

   nome_cartella = Nome visualizzato


Limitazioni
-----------


- ``rules.txt`` e ``ai.txt`` esistono in una sola copia; non ci sono file per lingua.
- ``ui-xx/style.txt`` nelle sottocartelle di mappa/campagna potrebbe non caricarsi; ``ui-xx/tts.txt`` sì.
- Il menu dei pacchetti audio usa ancora il nome della cartella.

Esempi
------


- `mods/orc/`: ``ui-xx/tts.txt`` in sette lingue
- `mods/prismalab/ui-fr/`: interfaccia e scorciatoie in francese

Maggiori dettagli nella sezione multilinguismo delle mod in ``mod/modding.rst``.
