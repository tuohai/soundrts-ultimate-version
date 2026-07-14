Terreno di casella configurabile e building land
================================================

.. epigraph:: Per **autori di mod**: ``class terrain``, ``class building_land``, ``square_terrain`` guidato dagli oggetti e la palette dell’editor di mappe. Completa ``mapmaking.htm`` e ``modding.htm``.


----

Panoramica
----------


Tutto il terreno è dichiarato in ``rules.txt`` come ``class terrain``; ``style.txt`` usa gli stessi nomi ``def`` per voce, ``ground`` e colori. Le unità ``move_on_<key>`` / ``falling_on_<key>`` corrispondono ai nomi dei tipi di terreno o alle categorie ``ground`` — vedi ``modding.htm`` (sistema audio di combattimento).

**Il motore non assegna più un terreno predefinito a ogni casella.** Il terreno di una casella proviene solo da:

1. ``terrain <name> <squares>`` della mappa
2. ``square_terrain`` degli oggetti (boschi, città, prati, ecc.)
3. ``high_grounds`` / ``is_high_ground`` — solo voce extra “altura”, non un nome di terreno


Definizioni e posizionamento
----------------------------


**rules.txt:**

.. code-block:: text

   def plain
   class terrain
   is_dynamic 1

   def lake
   class terrain
   is_water 1
   is_dynamic 0

**Mappa:**

.. code-block:: text

   terrain plain a1
   terrain lake d1
   terrain hill c1
   high_grounds e1

- ``terrain lake d1`` **non** richiede una riga ``water d1`` separata
- La parola chiave legacy ``water`` funziona ancora
- Caselle senza ``terrain``: ``type_name`` vuoto, nessuna voce di terreno


Building land (``class building_land``)
---------------------------------------


``meadow``, ``build_site`` e i tipi personalizzati non sono più cablati. Dichiarali con **`class building_land`** in ``rules.txt``.

.. code-block:: text

   def meadow
   class building_land
   square_terrain meadows 40

   def build_site
   class building_land
   square_terrain build_sites 50

.. list-table::
   :header-rows: 1

   * - Meccanismo
     - Ruolo
   * - ``default_building_land``
     - Predefinito delle regole quando la mappa omette ``building_land``
   * - ``building_land <name>`` di mappa
     - Tipo building-land predefinito per tutta la mappa
   * - ``nb_<type>_by_square <N>``
     - Riempie automaticamente ogni casella con N oggetti di quel tipo ``class building_land``
   * - ``nb_meadows_by_square <N>``
     - Legacy; tipo da ``building_land`` / inferenza della mappa
   * - ``additional_building_land <name> <squares…>``
     - Posiziona qualsiasi tipo building-land dichiarato sulle caselle elencate

Quando il decollo o alcuni upgrade ripristinano il building land sul posto, il motore usa **prima il tipo salvato quando l’edificio è stato posizionato**; solo se manca, ricade sul ``building_land`` della mappa o su un’unica parola chiave ``nb_<type>_by_square``.

Vedi ``mapmaking.htm`` (*Building_land*, *Nb_<type>_by_square*).


Attributi ``class terrain``
---------------------------


.. list-table::
   :header-rows: 1

   * - Attributo
     - Significato
   * - ``is_dynamic``
     - ``0`` statico; ``1`` può essere sovrascritto dal terreno degli oggetti
   * - ``is_ground`` / ``is_air`` / ``is_water``
     - Flag di percorribilità terra / aria / acqua
   * - ``is_high_ground``
     - Altura + voce
   * - ``passable_units``
     - Whitelist (si applica l’eredità ``is_a``)
   * - ``blocks_path``
     - Blocca le uscite verso i vicini (es. foresta densa, montagna)
   * - ``speed``
     - Opzionale. ``speed <ground> <air>`` (es. ``speed .5 1`` → 50% velocità di terra). Applicato quando la mappa imposta ``terrain <name>``; le righe ``speed`` per casella della mappa hanno priorità

``terrain <name>`` della mappa scrive questi flag sulla casella. La **velocità di movimento** su una casella (non è la stessa di ``speed_on_terrain`` dell’unità) si risolve così:

1. ``speed <ground> <air> <squares>`` della mappa — autorevole a runtime
2. ``speed`` sul ``class terrain`` in ``rules.txt`` — quando la mappa ha ``terrain`` ma non ``speed`` per quella cella
3. Predefinito ``(100, 100)``

``editor_palette.txt`` è solo per l’editor: le voci di palette senza ``speed`` ereditano da ``rules.txt`` al caricamento della palette; il salvataggio della mappa scrive le righe ``speed``. Il gioco **non** legge la palette a runtime.

Esempio ford (acqua bassa, metà velocità di terra):

.. code-block:: text

   def ford
   class terrain
   is_water 1
   is_ground 1
   speed .5 1

Quando ``is_ground 1`` è impostato su terreno d’acqua (``ford``, ``big_bridge``), il pathfinding tratta la tessera come parte della **stessa regione di terra** della terra adiacente, così le unità possono attraversare i guadi senza bloccarsi sulla riva.

**Campate costruite dal giocatore** (``wooden_bridge``, ``is_buildable_on_water_only``, ``bridge_terrain bridge_deck``): vedi `Costruire ponti sull’acqua <water-bridge-building.htm>`_. Il ``big_bridge`` di mappa è terreno a traliccio fisso; le campate finite del giocatore usano ``bridge_deck``.

Modificatori di combattimento delle unità sul terreno (da 1.4.5.0)
------------------------------------------------------------------

Oltre a ``terrain_speed`` per casella, le def delle unità possono sovrascrivere movimento e statistiche di combattimento **in base al terreno su cui si trova l’unità**. La sintassi corrisponde a ``speed_on_terrain``:

.. code-block:: text

   <terrain_name> <modifier> [<terrain_name> <modifier> ...]

**Quale tessera conta:** la casella corrente dell’**attaccante/in movimento** ``type_name`` (o ``type_name_at`` per terreno a sottocella).

**Accumulo:** i modificatori sono **additivi** (negativo = penalità), applicati dopo ``mdg_vs`` / ``mdg_cd_vs`` ecc. I valori usano le stesse unità di ``mdg`` / ``mdg_cd`` (decimali ammessi; memorizzati ×1000 internamente).

.. list-table::
   :header-rows: 1

   * - Proprietà
     - Effetto
   * - ``speed_on_terrain``
     - Velocità di movimento su quel terreno (comportamento esistente)
   * - ``mdg_on_terrain`` / ``rdg_on_terrain``
     - Bonus danno mischia / a distanza (dopo base + ``*_vs``)
   * - ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``
     - Bonus cooldown di attacco (**positivo = attacchi più lenti**)
   * - ``charge_mdg_terrain`` / ``charge_rdg_terrain``
     - Bonus danno di carica extra (dopo ``charge_mdg`` + ``charge_*_vs``)
   * - ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``
     - Bonus cooldown di carica (positivo = cooldown di carica più lungo)

Colpo/schivata sul terreno del **bersaglio** (esistente): ``mdg_cover_on_terrain``, ``rdg_cover_on_terrain``, ``mdg_dodge_on_terrain``, ``rdg_dodge_on_terrain``.

**Schermata attributi (Alt+V):** elenca le righe ``*_on_terrain`` / carica dell’unità; i valori live di danno / cooldown / velocità includono ``*_vs`` del terreno della casella corrente più ``*_on_terrain`` (``*_vs`` terreno = percentuale decimale; ``speed_on_terrain`` resta assoluto).

**Esempio — cavaliere indebolito nella palude:**

.. code-block:: text

   def knight
   speed 2.5
   mdg 6
   mdg_cd 1.5
   speed_on_terrain marsh 1.5 ford 1.5
   mdg_on_terrain marsh -2
   mdg_cd_on_terrain marsh 0.5

Su ``marsh``: velocità 1.5, danno mischia 4, cooldown di attacco 2.0 s.

**Esempio — unità con carica:**

.. code-block:: text

   def raynor
   charge_mdg 4
   charge_mdg_cd 10
   charge_mdg_terrain marsh -1
   charge_mdg_cd_on_terrain marsh 2

Su ``marsh``: bonus carica −1, cooldown carica +2 s.

Implementazione: ``soundrts/combat/damage_calculation.py``, ``soundrts/combat/attack_action.py``; test: ``test_combat_terrain_modifiers.py``.

I tipi in ``res/rules.txt`` includono ``plain``, ``lake``, ``marsh``, ``mountain``, ``forest``, ``dense_forest``, ``meadows``, ``build_sites``, ``town``, ``ford``, ecc.


``square_terrain``: terreno guidato dagli oggetti
-------------------------------------------------


**``terrain`` di mappa dipinge lo strato base; ``square_terrain`` lascia che gli oggetti crescano lo strato superiore** che può apparire e sparire a runtime.

Sintassi su qualsiasi ``def``:

.. code-block:: text

   square_terrain <terrain_name> [priority] [min_count]

- ``priority`` (predefinito 50): vince il più alto
- ``min_count`` (predefinito 1): minimo di oggetti di quel ``type_name`` sulla casella

Esempio — foresta vs foresta densa:

.. code-block:: text

   def wood
   class deposit
   square_terrain forest 80
   square_terrain dense_forest 90 7

A ogni tick, ``update_terrain()`` sceglie la voce idonea a priorità più alta e imposta il ``type_name`` della casella. Il building land ha uno strato vocale separato (``building_land_voice`` vs ``feature_voice``).

Il ``terrain forest`` dinamico sulla mappa genera oggetti corrispondenti tramite i collegamenti inversi ``square_terrain``.


Strati vocali
~~~~~~~~~~~~~


``resolve_square_layers()`` può sovrapporre:

- ``feature_voice`` — terreno oggetto vincente (``forest``, ``town``, …)
- ``building_land_voice`` — ``meadows`` / ``build_sites`` quando diverso dalla feature
- ``high_ground_voice`` — marcatore di altura


Palette dell’editor di mappe
----------------------------


Console ``edit``; binding in ``res/ui/editor_bindings.txt``. Logica in ``soundrts/lib/editor_palette.py``.

- Terreni statici (``lake``, ``mountain``, …): ``fixed_terrain``, salvati come ``terrain <name>``
- Terreni dinamici (``forest``, ``meadows``, …): generano oggetti, non bloccati
- Nomi della palette allineati a ``res/ui/editor_palette.txt`` (``forest`` non il legacy ``woods``)


Test
----


.. code-block:: bash

   python -m pytest soundrts/tests/test_square_terrain_rules.py soundrts/tests/test_building_land.py soundrts/tests/test_subcell_terrain.py soundrts/tests/test_editor_palette.py soundrts/tests/test_terrain_speed_defaults.py soundrts/tests/test_ground_region_ford.py -q
