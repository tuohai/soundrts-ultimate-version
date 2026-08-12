Market system (rules-driven)
============================

.. epigraph:: For **mod authors**: buy/sell, tribute, and route trade are configured in ``rules.txt``. The engine does **not** hardcode resource names or “gold-only” trade. ``mods/aoe2`` is one wiring of the same API.

----

Overview
--------

| Feature | Order | Typical host |
| --- | --- | --- |
| Buy / sell a batch | ``market_buy`` / ``market_sell`` | building with ``is_market 1`` |
| Tribute to an ally | ``tribute`` | same (requires an ally) |
| Shuttle between hubs | ``trade`` (optional multi-reward) | unit with ``is_trade_unit 1`` |

Code: ``soundrts/worldmarket.py``, ``soundrts/worldorders/market.py``.
AoE2 numbers: ``mods/aoe2/SOURCES.md``.

Global parameters (``def parameters``)
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

   * - Key
     - Meaning
   * - ``market_currency``
     - Currency resource for buy/sell (``resourceN``)
   * - ``market_commodities``
     - Sellable goods and base prices: ``resourceN <price>`` pairs (display units per batch)
   * - ``market_menu_labels``
     - Optional menu aliases: ``resourceN <alias>`` (alias can match a style title)
   * - ``market_batch`` / ``tribute_batch``
     - Units transferred per buy/sell or tribute
   * - ``market_tax_permille``
     - Default tax (permille; 300 = 30%)
   * - ``market_tax_guilds_permille``
     - Tax when the player has ``market_tax_guilds`` (e.g. Guilds tech)
   * - ``tribute_fee_permille``
     - Default tribute fee; techs may set ``tribute_fee_permille`` on the player
   * - ``tribute_resources``
     - Tributable resources; omit → currency + all commodities
   * - ``market_price_*``
     - Price drift after trades and clamps
   * - ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``
     - Route-trade payout formula (hop scale, shrink, cap)

Building / unit attributes
--------------------------

Market building::

    def market
    class building
    is_market 1
    ; optional overrides: market_commodities / market_currency / market_batch / market_tax_permille

Trade unit::

    def trade_cart
    class soldier
    is_trade_unit 1
    trade_hubs market
    trade_rewards resource1

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``is_market``
     - Enables buy/sell/tribute menu
   * - ``is_dock``
     - Dock-style hub (or list it under ``trade_hubs``)
   * - ``is_trade_unit``
     - Enables ``trade``
   * - ``trade_hubs``
     - Valid hubs: type names and/or flags (``is_market``, ``is_dock``, …)
   * - ``trade_rewards``
     - Resources earned on routes; **several** → menu lines ``trade resourceN``
   * - ``market_tax_guilds`` (tech)
     - ``1`` switches the player to guild tax
   * - ``tribute_fee_permille`` (tech)
     - Sets player tribute fee (``0`` = free)

Prefer ``resourceN`` tokens. Aliases ``gold`` / ``wood`` / ``food`` / ``stone`` parse for convenience only.

Route trade
-----------

1. Select a trade unit → ``trade`` (or ``trade <resource>``) → pick another valid hub.
2. The unit shuttles home ↔ destination; payout uses **square hops** into ``trade_rewards`` (very short routes may pay 0).
3. Rewards are not tied to currency — e.g. ``trade_rewards resource2`` earns wood only.

If ``trade_hubs`` is omitted, legacy fallbacks apply (land trade ↔ market, water ↔ dock). New mods should set hubs explicitly.

Non-AoE2 sketch::

    def parameters
    market_currency resource2
    market_commodities resource3 80
    market_batch 50

    def caravan
    class soldier
    is_trade_unit 1
    trade_hubs exchange
    trade_rewards resource1

Player-facing notes: `Market and trade (player, zh) <../../zh/player/market-and-trade.htm>`_.
Tests: ``test_aoe2_market.py``, ``test_aoe2_dock_economy.py``.
