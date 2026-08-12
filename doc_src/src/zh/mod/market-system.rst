市场机制（规则驱动）
====================

.. epigraph:: 面向 **模组作者**：买卖、进贡、路线贸易均由 ``rules.txt`` 配置，引擎**不硬编码**资源名或「只赚黄金」。帝国时代 2 模组（``mods/aoe2``）只是其中一种接法。

----

概览
----

| 能力 | 命令 | 典型宿主 |
| --- | --- | --- |
| 买入 / 卖出一批商品 | ``market_buy`` / ``market_sell`` | ``is_market 1`` 的建筑 |
| 向盟友进贡 | ``tribute`` | 同上（需有盟友） |
| 在枢纽间跑商 | ``trade``（可多资源） | ``is_trade_unit 1`` 的单位 |

实现：``soundrts/worldmarket.py``、``soundrts/worldorders/market.py``。
权威规则字段亦见 ``modding.htm`` 本节交叉引用；aoe2 数值见 ``mods/aoe2/SOURCES.md``。

全局参数（``def parameters``）
------------------------------

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

   * - 键
     - 说明
   * - ``market_currency``
     - 买卖用的货币资源（``resourceN``）
   * - ``market_commodities``
     - 可买卖商品及底价：``resourceN <底价>`` 成对；价格为**显示单位**/批
   * - ``market_menu_labels``
     - 可选；菜单参数用别名（须 ``resourceN <别名>``，别名可对应 style 标题）
   * - ``market_batch`` / ``tribute_batch``
     - 每笔买卖 / 进贡数量
   * - ``market_tax_permille``
     - 默认税率（千分比，300 = 30%）
   * - ``market_tax_guilds_permille``
     - 玩家已有 ``market_tax_guilds``（如行会科技）时的税率
   * - ``tribute_fee_permille``
     - 默认进贡手续费；科技可用 ``tribute_fee_permille`` 覆盖玩家费率
   * - ``tribute_resources``
     - 可进贡的资源列表；省略则 = 货币 + 全部商品
   * - ``market_price_*``
     - 成交后底价升降与上下限
   * - ``trade_tile_scale`` / ``trade_shrink`` / ``trade_reward_cap``
     - 路程贸易收益公式（格距缩放、缩减、上限）

建筑 / 单位属性
---------------

市场建筑::

    def market
    class building
    is_market 1
    ; 可选覆盖：market_commodities / market_currency / market_batch / market_tax_permille

贸易单位::

    def trade_cart
    class soldier
    is_trade_unit 1
    trade_hubs market
    trade_rewards resource1

    def trade_cog
    class soldier
    is_trade_unit 1
    trade_hubs is_dock shipyard
    trade_rewards resource1

.. list-table::
   :header-rows: 1

   * - 属性
     - 说明
   * - ``is_market``
     - 开放买卖 / 进贡菜单
   * - ``is_dock``
     - 码头类枢纽（也可只写在 ``trade_hubs`` 里）
   * - ``is_trade_unit``
     - 可下 ``trade`` 命令
   * - ``trade_hubs``
     - 合法停靠点：类型名（如 ``market``）和/或标志（``is_market``、``is_dock``）
   * - ``trade_rewards``
     - 跑商可赚的资源；**多个**时菜单为 ``trade resourceN``（或 menu label）
   * - ``market_tax_guilds``（科技）
     - 设 ``1`` 后玩家改用行会税率
   * - ``tribute_fee_permille``（科技）
     - 写入玩家进贡费率（``0`` = 免费）

资源记号
--------

- 推荐一律用 ``resource1`` … ``resourceN``（与 ``nb_of_resource_types`` 一致）。
- 解析也接受别名 ``gold`` / ``wood`` / ``food`` / ``stone``（仅方便；其它模组勿依赖）。
- 菜单优先 ``market_menu_labels``，否则用 ``resourceN``；style 里为参数准备 ``title``（如 ``def wood``）。

路线贸易行为
------------

1. 选中贸易单位 → ``trade``（或 ``trade <资源>``）→ 指定**另一**合法枢纽（己方第二市场、盟友市场、码头等）。
2. 单位在「出发枢纽 ↔ 目标枢纽」间往返；到达目标时按**格距**结算 ``trade_rewards`` 中的资源（相邻过近可为 0，避免刷钱）。
3. 收益与货币无关：可设 ``trade_rewards resource2`` 只赚木材，或 ``resource1 resource3`` 让玩家选贸易类型。

未写 ``trade_hubs`` 时引擎有旧式回退（陆地贸易单位 ↔ 市场，水上 ↔ 码头）；新模组请显式配置。

非 aoe2 示例
------------

只卖气、用矿物当货币，马车赚食物::

    def parameters
    nb_of_resource_types 3
    market_currency resource2
    market_commodities resource3 80
    market_batch 50
    tribute_resources resource1 resource2 resource3

    def exchange
    class building
    is_market 1

    def caravan
    class soldier
    is_trade_unit 1
    trade_hubs exchange
    trade_rewards resource1

玩家向说明见 `市场与贸易（玩家） <../player/market-and-trade.htm>`_。
测试：``soundrts/tests/test_aoe2_market.py``、``test_aoe2_dock_economy.py``。
