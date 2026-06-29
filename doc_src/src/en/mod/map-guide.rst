Map authoring guide (intro & advanced)
========================================


Build a playable map first. Full syntax: `Mapmaking manual <mapmaking.htm>`_.
.. contents::

----

Getting started
----------------

.. list-table::
   :header-rows: 1

   * - Location
     - Notes
   * - ``user/multi/``
     - Private maps
   * - ``user/single/…/N.txt``
     - Campaign chapters — `Campaign guide <campaign-guide.htm>`_

Test from single-player vs computer. Errors: ``user/tmp/client.log``.

----

Minimal map
------------

.. code-block:: text

   title 4018 5000
   objective 145 88
   nb_players_min 2
   nb_players_max 2
   squares 3 3
   goldmines 1 1 5000
   woods 2 2 5000
   players 1 1 1

----

Advanced
---------

Triggers and full syntax → `Mapmaking manual <mapmaking.htm>`_  
Campaign actions → `Campaign guide <campaign-guide.htm>`_  
RMG → `Random maps <randommap.htm>`_ · Player UI → `Random maps (player) <../player/random-map-play.htm>`_
