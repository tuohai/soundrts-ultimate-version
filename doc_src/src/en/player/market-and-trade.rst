Market and trade (player)
=========================

Applies to mods that enable the market system (e.g. ``mods/aoe2`` Age of Empires II).
Which resources can be bought/sold and what trade earns is decided by the mod rules —
it does not have to be “gold”.


Buy / sell and tribute
----------------------

1. Select a **market**-type building.
2. **Buy / sell**: according to configured commodities (aoe2: wood, food, stone, batches of 100),
   pay or receive the configured currency (aoe2: gold). Default tax ~30%; researching a
   “Guilds”-style tech lowers it.
3. **Tribute**: with an ally, you can send configured resources to the first ally; there may
   be a fee (coinage / banking techs can reduce or remove it).

You can buy/sell without an ally (same as Age of Empires DE).

Route trade
-----------

1. Train **trade units** at a market (or dock) (e.g. trade cart, trade cog).
2. Select the unit → **Trade** → pick another valid hub:

   - Land cart: another market (your second market or an ally’s).
   - Trade ship: dock / shipyard-type buildings.

3. The unit runs back and forth; farther routes pay more; **too close may yield 0**
   (anti-abuse).
4. If the mod sets several ``trade_rewards`` for that unit, the menu asks first which
   resource to earn, then the destination.

Tip: build two markets far enough apart before trading; aoe2’s default trade reward is
gold; other mods may differ.

Related docs
------------

- Mod author setup: `Market system <../mod/market-system.htm>`_
- aoe2 data notes: ``mods/aoe2/SOURCES.md``, ``mods/aoe2/readme.txt``
- Release notes: `relnotes <../relnotes.htm>`_ (1.4.6.9)
