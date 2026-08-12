Mercato e commercio (giocatore)
===============================

Si applica ai mod che abilitano il sistema di mercato (es. ``mods/aoe2`` Age of Empires II). Quali risorse si possono comprare/vendere e cosa guadagna il commercio lo decide la regola del mod; non deve essere necessariamente «oro».


Compra/vendita e tributo
------------------------

1. Seleziona un edificio di tipo **mercato**.
2. **Compra / vendi**: secondo le merci configurate (aoe2: legno, cibo, pietra, lotti da 100), paga o incassa con la moneta configurata (aoe2: oro). Tassa predefinita ~30%; dopo una tech tipo «Gilde» scende.
3. **Tributo**: con un alleato, puoi inviare risorse configurate al primo alleato; può esserci una commissione (tech di conio / banca possono ridurla o azzerarla).

Puoi comprare/vendere senza alleato (come Age of Empires DE).

Commercio di tratta
-------------------

1. Addestra **unità commerciali** al mercato (o molo) (es. carretto commerciale, nave commerciale).
2. Seleziona l’unità → **Commercio** → indica un altro hub valido:

   - Carretto terrestre: un altro mercato (secondo mercato proprio o alleato).
   - Nave commerciale: edifici tipo molo / cantiere.

3. L’unità va e torna da sola; più è lontana, più guadagna; **se è troppo vicina può essere 0** (anti-abuso).
4. Se il mod configura più ``trade_rewards`` per quell’unità, il menu chiede prima il tipo di risorsa da guadagnare e poi la destinazione.

Consiglio: costruisci due mercati abbastanza distanti prima di commerciare; in aoe2 la ricompensa predefinita è oro; altri mod possono differire.

Documentazione correlata
------------------------

- Configurazione per autori di mod: `Sistema di mercato <../mod/market-system.htm>`_
- Dati aoe2: ``mods/aoe2/SOURCES.md``, ``mods/aoe2/readme.txt``
- Note di rilascio: `relnotes <../relnotes.htm>`_ (1.4.6.9)
