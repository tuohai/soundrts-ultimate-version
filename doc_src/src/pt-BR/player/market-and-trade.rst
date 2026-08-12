Mercado e comércio (jogador)
============================

Aplica-se a mods que ativam o sistema de mercado (ex.: ``mods/aoe2`` Age of Empires II). Quais recursos se pode comprar/vender e o que o comércio rende é definido pela regra do mod; não precisa ser «ouro».


Compra/venda e tributo
----------------------

1. Selecione uma edificação do tipo **mercado**.
2. **Comprar / vender**: conforme as mercadorias configuradas (aoe2: madeira, comida, pedra, lotes de 100), pague ou receba com a moeda configurada (aoe2: ouro). Imposto padrão ~30%; após uma tech tipo «Guildas» baixa.
3. **Tributo**: com um aliado, pode enviar recursos configurados ao primeiro aliado; pode haver taxa (techs de cunhagem / banco podem reduzir ou zerar).

Pode comprar/vender sem aliado (como Age of Empires DE).

Comércio de rota
----------------

1. Treine **unidades de comércio** no mercado (ou cais) (ex.: carroça comercial, navio comercial).
2. Selecione a unidade → **Comércio** → indique outro hub válido:

   - Carroça terrestre: outro mercado (segundo mercado próprio ou de aliado).
   - Navio comercial: edificações tipo cais / estaleiro.

3. A unidade vai e volta sozinha; quanto mais longe, mais rende; **se estiver perto demais pode ser 0** (anti-abuso).
4. Se o mod configurar vários ``trade_rewards`` para essa unidade, o menu pede primeiro o tipo de recurso a ganhar e depois o destino.

Dica: construa dois mercados suficientemente distantes antes de comerciar; em aoe2 a recompensa padrão é ouro; outros mods podem diferir.

Documentação relacionada
------------------------

- Configuração para autores de mods: `Sistema de mercado <../mod/market-system.htm>`_
- Dados aoe2: ``mods/aoe2/SOURCES.md``, ``mods/aoe2/readme.txt``
- Notas de lançamento: `relnotes <../relnotes.htm>`_ (1.4.6.9)
