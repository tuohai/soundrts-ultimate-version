Mercado y comercio (jugador)
============================

Aplicable a mods que activan el sistema de mercado (p. ej. ``mods/aoe2`` Age of Empires II). Qué recursos se pueden comprar/vender y qué gana el comercio lo decide la regla del mod; no tiene por qué ser «oro».


Compra/venta y tributo
----------------------

1. Seleccione un edificio de tipo **mercado**.
2. **Comprar / vender**: según las mercancías configuradas (aoe2: madera, comida, piedra, lotes de 100), pague o cobre con la moneda configurada (aoe2: oro). Impuesto por defecto ~30%; tras estudiar una tecnología tipo «Gremios» baja.
3. **Tributo**: con un aliado, puede enviar recursos configurados al primer aliado; puede haber comisión (tecnologías de acuñación / banca pueden reducirla o anularla).

Puede comprar/vender sin aliado (igual que Age of Empires DE).

Comercio de rutas
-----------------

1. Entrene **unidades de comercio** en un mercado (o muelle) (p. ej. carreta comercial, barco comercial).
2. Seleccione la unidad → **Comercio** → indique otro hub válido:

   - Carreta terrestre: otro mercado (segundo mercado propio o de aliado).
   - Barco comercial: edificios tipo muelle / astillero.

3. La unidad va y viene sola; cuanto más lejos, más gana; **si está demasiado cerca puede ser 0** (anti-abuso).
4. Si el mod configura varios ``trade_rewards`` para esa unidad, el menú pide primero el tipo de recurso a ganar y luego el destino.

Consejo: construya dos mercados suficientemente alejados antes de comerciar; en aoe2 la recompensa por defecto es oro; otros mods pueden diferir.

Documentación relacionada
-------------------------

- Configuración para autores de mods: `Sistema de mercado <../mod/market-system.htm>`_
- Datos aoe2: ``mods/aoe2/SOURCES.md``, ``mods/aoe2/readme.txt``
- Notas de versión: `relnotes <../relnotes.htm>`_ (1.4.6.9)
