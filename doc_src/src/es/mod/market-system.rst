Sistema de mercado (impulsado por reglas)
=========================================

.. epigraph:: Para **autores de mods**: compra/venta, tributo y comercio de rutas se configuran en ``rules.txt``. El motor **no** hardcodea nombres de recurso ni comercio «solo oro». ``mods/aoe2`` es un cableado de la misma API.

----

Resumen
-------

| Función | Orden | Anfitrión típico |
| --- | --- | --- |
| Comprar / vender un lote | ``market_buy`` / ``market_sell`` | edificio con ``is_market 1`` |
| Tributo a un aliado | ``tribute`` | igual (requiere un aliado) |
| Ir y venir entre hubs | ``trade`` (multi-recompensa opcional) | unidad con ``is_trade_unit 1`` |

Código: ``soundrts/worldmarket.py``, ``soundrts/worldorders/market.py``.
Números AoE2: ``mods/aoe2/SOURCES.md``.

Parámetros globales (``def parameters``)
----------------------------------------

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

   * - Clave
     - Significado
   * - ``market_currency``
     - Recurso moneda para compra/venta (``resourceN``)
   * - ``market_commodities``
     - Bienes vendibles y precios base: pares ``resourceN <price>`` (unidades de pantalla por lote)
   * - ``market_menu_labels``
     - Alias opcionales de menú: ``resourceN <alias>`` (el alias puede coincidir con un título de style)
   * - ``market_batch`` / ``tribute_batch``
     - Unidades transferidas por compra/venta o tributo
   * - ``market_tax_permille``
     - Impuesto por defecto (por mil; 300 = 30%)
   * - ``market_tax_guilds_permille``
     - Impuesto cuando el jugador tiene ``market_tax_guilds`` (p. ej. tecnología Gremios)
   * - ``tribute_fee_permille``
     - Comisión de tributo por defecto; las tecnologías pueden fijar ``tribute_fee_permille`` en el jugador
   * - ``tribute_resources``
     - Recursos tributables; omitir → moneda + todas las mercancías
   * - ``market_price_*``
     - Deriva de precios tras operaciones y límites
   * - ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``
     - Fórmula de pago del comercio de rutas (escala de saltos, shrink, tope)

Atributos de edificio / unidad
------------------------------

Edificio de mercado::

    def market
    class building
    is_market 1
    ; anulaciones opcionales: market_commodities / market_currency / market_batch / market_tax_permille

Unidad de comercio::

    def trade_cart
    class soldier
    is_trade_unit 1
    trade_hubs market
    trade_rewards resource1

.. list-table::
   :header-rows: 1

   * - Atributo
     - Significado
   * - ``is_market``
     - Activa el menú compra/venta/tributo
   * - ``is_dock``
     - Hub estilo muelle (o listarlo bajo ``trade_hubs``)
   * - ``is_trade_unit``
     - Activa ``trade``
   * - ``trade_hubs``
     - Hubs válidos: nombres de tipo y/o flags (``is_market``, ``is_dock``, …)
   * - ``trade_rewards``
     - Recursos ganados en rutas; **varios** → líneas de menú ``trade resourceN``
   * - ``market_tax_guilds`` (tech)
     - ``1`` cambia al jugador al impuesto de gremios
   * - ``tribute_fee_permille`` (tech)
     - Fija la comisión de tributo del jugador (``0`` = gratis)

Prefiera tokens ``resourceN``. Los alias ``gold`` / ``wood`` / ``food`` / ``stone`` se analizan solo por comodidad.

Comercio de rutas
-----------------

1. Seleccione una unidad de comercio → ``trade`` (o ``trade <resource>``) → elija otro hub válido.
2. La unidad va y viene casa ↔ destino; el pago usa **saltos de casilla** hacia ``trade_rewards`` (rutas muy cortas pueden pagar 0).
3. Las recompensas no están ligadas a la moneda — p. ej. ``trade_rewards resource2`` gana solo madera.

Si se omite ``trade_hubs``, aplican respaldo legado (comercio terrestre ↔ mercado, agua ↔ muelle). Los mods nuevos deben fijar los hubs explícitamente.

Boceto no-AoE2::

    def parameters
    market_currency resource2
    market_commodities resource3 80
    market_batch 50

    def caravan
    class soldier
    is_trade_unit 1
    trade_hubs exchange
    trade_rewards resource1

Notas para jugadores: `Mercado y comercio <../player/market-and-trade.htm>`_.
Pruebas: ``test_aoe2_market.py``, ``test_aoe2_dock_economy.py``.
