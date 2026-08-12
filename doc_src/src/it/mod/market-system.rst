Sistema di mercato (guidato dalle regole)
=========================================

.. epigraph:: Per **autori di mod**: compra/vendita, tributo e commercio di tratta si configurano in ``rules.txt``. Il motore **non** hardcoda nomi di risorsa né commercio «solo oro». ``mods/aoe2`` è un cablaggio della stessa API.

----

Panoramica
----------

| Funzione | Ordine | Ospite tipico |
| --- | --- | --- |
| Compra / vendi un lotto | ``market_buy`` / ``market_sell`` | edificio con ``is_market 1`` |
| Tributo a un alleato | ``tribute`` | uguale (serve un alleato) |
| Navetta tra hub | ``trade`` (multi-ricompensa opzionale) | unità con ``is_trade_unit 1`` |

Codice: ``soundrts/worldmarket.py``, ``soundrts/worldorders/market.py``.
Numeri AoE2: ``mods/aoe2/SOURCES.md``.

Parametri globali (``def parameters``)
--------------------------------------

::

    def parameters
    market_currency resource1
    market_batch 100
    market_tax_permille 300
    market_tax_guilds_permille 150
    tribute_fee_permille 300
    tribute_batch 100
    market_price_min 20
    market_price_max 9999
    market_price_step 2
    market_commodities resource2 100 resource3 100 resource4 100
    market_menu_labels resource2 resource2 resource3 resource3 resource4 resource4
    tribute_resources resource1 resource2 resource3 resource4
    trade_tile_scale 6
    trade_shrink 5
    trade_reward_cap 517

.. list-table::
   :header-rows: 1

   * - Chiave
     - Significato
   * - ``market_currency``
     - Risorsa moneta per compra/vendita (``resourceN``)
   * - ``market_commodities``
     - Merci vendibili e prezzi base: coppie ``resourceN <price>`` (unità di display per lotto)
   * - ``market_menu_labels``
     - Alias opzionali di menu: ``resourceN <alias>`` (l’alias può coincidere con un titolo style)
   * - ``market_batch`` / ``tribute_batch``
     - Unità trasferite per compra/vendita o tributo
   * - ``market_tax_permille``
     - Tassa predefinita (per mille; 300 = 30%)
   * - ``market_tax_guilds_permille``
     - Tassa quando il giocatore ha ``market_tax_guilds`` (es. tech Gilde)
   * - ``tribute_fee_permille``
     - Commissione tributo predefinita; le tech possono impostare ``tribute_fee_permille`` sul giocatore
   * - ``tribute_resources``
     - Risorse tributabili; omettere → moneta + tutte le merci
   * - ``market_price_*``
     - Deriva prezzi dopo gli scambi e limiti
   * - ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``
     - Formula di payout del commercio di tratta (scala hop, shrink, tetto)

Attributi edificio / unità
---------------------------

Edificio mercato::

    def market
    class building
    is_market 1
    ; override opzionali: market_commodities / market_currency / market_batch / market_tax_permille

Unità commerciale::

    def trade_cart
    class soldier
    is_trade_unit 1
    trade_hubs market
    trade_rewards resource1

.. list-table::
   :header-rows: 1

   * - Attributo
     - Significato
   * - ``is_market``
     - Abilita il menu compra/vendita/tributo
   * - ``is_dock``
     - Hub stile molo (o elencarli sotto ``trade_hubs``)
   * - ``is_trade_unit``
     - Abilita ``trade``
   * - ``trade_hubs``
     - Hub validi: nomi di tipo e/o flag (``is_market``, ``is_dock``, …)
   * - ``trade_rewards``
     - Risorse guadagnate sulle tratte; **più** → voci di menu ``trade resourceN``
   * - ``market_tax_guilds`` (tech)
     - ``1`` passa il giocatore alla tassa delle gilde
   * - ``tribute_fee_permille`` (tech)
     - Imposta la commissione tributo del giocatore (``0`` = gratis)

Preferisci token ``resourceN``. Gli alias ``gold`` / ``wood`` / ``food`` / ``stone`` si analizzano solo per comodità.

Commercio di tratta
-------------------

1. Seleziona un’unità commerciale → ``trade`` (o ``trade <resource>``) → scegli un altro hub valido.
2. L’unità fa la spola casa ↔ destinazione; il payout usa **hop di casella** verso ``trade_rewards`` (tratte molto corte possono pagare 0).
3. Le ricompense non sono legate alla moneta — es. ``trade_rewards resource2`` guadagna solo legno.

Se ``trade_hubs`` è omesso, valgono i fallback legacy (commercio terrestre ↔ mercato, acqua ↔ molo). Le nuove mod dovrebbero impostare gli hub esplicitamente.

Bozza non-AoE2::

    def parameters
    market_currency resource2
    market_commodities resource3 80
    market_batch 50

    def caravan
    class soldier
    is_trade_unit 1
    trade_hubs exchange
    trade_rewards resource1

Note per giocatori: `Mercato e commercio <../player/market-and-trade.htm>`_.
Test: ``test_aoe2_market.py``, ``test_aoe2_dock_economy.py``.
