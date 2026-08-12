Sistema de mercado (orientado por regras)
=========================================

.. epigraph:: Para **autores de mods**: compra/venda, tributo e comércio de rota são configurados em ``rules.txt``. O motor **não** fixa nomes de recurso nem comércio «só ouro». ``mods/aoe2`` é uma ligação da mesma API.

----

Visão geral
-----------

| Recurso | Ordem | Hospedeiro típico |
| --- | --- | --- |
| Comprar / vender um lote | ``market_buy`` / ``market_sell`` | edificação com ``is_market 1`` |
| Tributo a um aliado | ``tribute`` | igual (exige um aliado) |
| Vai-e-vem entre hubs | ``trade`` (multi-recompensa opcional) | unidade com ``is_trade_unit 1`` |

Código: ``soundrts/worldmarket.py``, ``soundrts/worldorders/market.py``.
Números AoE2: ``mods/aoe2/SOURCES.md``.

Parâmetros globais (``def parameters``)
---------------------------------------

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

   * - Chave
     - Significado
   * - ``market_currency``
     - Recurso moeda para compra/venda (``resourceN``)
   * - ``market_commodities``
     - Mercadorias vendáveis e preços base: pares ``resourceN <price>`` (unidades de tela por lote)
   * - ``market_menu_labels``
     - Aliases opcionais de menu: ``resourceN <alias>`` (o alias pode coincidir com um título style)
   * - ``market_batch`` / ``tribute_batch``
     - Unidades transferidas por compra/venda ou tributo
   * - ``market_tax_permille``
     - Imposto padrão (por mil; 300 = 30%)
   * - ``market_tax_guilds_permille``
     - Imposto quando o jogador tem ``market_tax_guilds`` (ex.: tech Guildas)
   * - ``tribute_fee_permille``
     - Taxa de tributo padrão; techs podem definir ``tribute_fee_permille`` no jogador
   * - ``tribute_resources``
     - Recursos tributáveis; omitir → moeda + todas as mercadorias
   * - ``market_price_*``
     - Deriva de preços após operações e limites
   * - ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``
     - Fórmula de pagamento do comércio de rota (escala de saltos, shrink, teto)

Atributos de edificação / unidade
---------------------------------

Edificação de mercado::

    def market
    class building
    is_market 1
    ; sobrescritas opcionais: market_commodities / market_currency / market_batch / market_tax_permille

Unidade de comércio::

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
     - Ativa o menu compra/venda/tributo
   * - ``is_dock``
     - Hub estilo cais (ou liste em ``trade_hubs``)
   * - ``is_trade_unit``
     - Ativa ``trade``
   * - ``trade_hubs``
     - Hubs válidos: nomes de tipo e/ou flags (``is_market``, ``is_dock``, …)
   * - ``trade_rewards``
     - Recursos ganhos nas rotas; **vários** → linhas de menu ``trade resourceN``
   * - ``market_tax_guilds`` (tech)
     - ``1`` muda o jogador para o imposto de guildas
   * - ``tribute_fee_permille`` (tech)
     - Define a taxa de tributo do jogador (``0`` = grátis)

Prefira tokens ``resourceN``. Aliases ``gold`` / ``wood`` / ``food`` / ``stone`` são analisados só por conveniência.

Comércio de rota
----------------

1. Selecione uma unidade de comércio → ``trade`` (ou ``trade <resource>``) → escolha outro hub válido.
2. A unidade faz o vai-e-vem casa ↔ destino; o pagamento usa **saltos de casa** em ``trade_rewards`` (rotas muito curtas podem pagar 0).
3. As recompensas não estão atadas à moeda — ex.: ``trade_rewards resource2`` ganha só madeira.

Se ``trade_hubs`` for omitido, valem fallbacks legados (comércio terrestre ↔ mercado, água ↔ cais). Mods novos devem definir os hubs explicitamente.

Esboço não-AoE2::

    def parameters
    market_currency resource2
    market_commodities resource3 80
    market_batch 50

    def caravan
    class soldier
    is_trade_unit 1
    trade_hubs exchange
    trade_rewards resource1

Notas para jogadores: `Mercado e comércio <../player/market-and-trade.htm>`_.
Testes: ``test_aoe2_market.py``, ``test_aoe2_dock_economy.py``.
