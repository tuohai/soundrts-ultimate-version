星际 mod — 矿物与高能瓦斯
=========================


模组：``mods/starcraft`` （在 ``SoundRTS.ini`` 中 ``mods = starcraft``）。

资源
---


- 矿物（``resource1``）：按 Z 查询库存
- 高能瓦斯（``resource2``）：按 X 查询库存

地图放置：

.. code-block:: text

   mineral_field 1500 a1
   geyser 1 e1


``geyser 1`` 表示建造位点；气泉默认储量来自规则里的 ``deposit_volume``（默认 5000）。也可写成 ``geyser 5000 e1`` 指定储量。

气矿建筑
--------


同化炉 / 萃取器 / 精炼厂必须建在 瓦斯气泉 上（Tab 气泉再建造）。建在建造用地上会提示「不能建在那里」。

建成后的流程：

1. 建筑吞并气泉储量（``is_an_extractor``），自动生产（``auto_production``）
2. 每 ``production_time`` 秒向建筑内积攒 ``production_qty`` 瓦斯（默认 18 秒 / 8 单位），并从气泉储量中扣除
3. 工人对气矿建筑采集，每次运回 ``extraction_qty`` （默认 8）
4. 储量降为 0 后，产量降为 ``depleted_production_qty``（默认 2），类似原版星际的枯竭气泉
5. 瓦斯存入主基地等带 ``storable_resource_types resource1 resource2`` 的建筑

气矿用 自动生产，不用农田的 ``auto_cultivate`` （农田要储量抽空才再种）。

查看属性
--------


选中气矿建筑，按 V 打开属性界面，可听到 需要矿床、当前矿脉储量等。生产时间、生产数量等沿用游戏原有的生产属性条目。

规则关键字详见 ``mod/modding.rst`` （Economy 与「矿床与气矿」两节）。

测试图：``mods/starcraft/multi/sc_resources_test.txt``。
