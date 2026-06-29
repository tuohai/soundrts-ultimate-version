# Age-of-Empires-style co-op campaigns


Full guide (1.4.3.9): `../player/campaign-and-co-op-improvements.md <../player/campaign-and-co-op-improvements.htm>`_ — mission browser, difficulty tiers, AI partners, determinism, map authoring.

中文：`../../zh/player/战役与合作战役改进说明.md <../../zh/player/战役与合作战役改进说明.htm>`_

This engine plays campaign chapters cooperatively the way Age of Empires II/III
Definitive Edition does: several players join the same story mission, each
commands their own slot (base/army) on one team, share the mission's
objectives and cutscenes, and face enemies that scale with difficulty and the
number of players. Empty slots are taken over by an allied AI partner, so
one person can also play a co-op mission solo.

How co-op works (player view)
------------------------------


1. Server lobby -> `Co-op campaign` -> pick campaign -> pick chapter ->
   pick difficulty (Easy / Standard / Moderate / Hard / Extreme) -> pick speed.
   (No treaty step: co-op campaigns never offer a treaty.)
2. Other players join the lobby; the host starts.
3. The mission's intro cutscene plays for everyone, then the mission runs
   with its own objectives driving shared victory/defeat (not "destroy all
   enemies"). Cutscenes and objective updates are voiced to all players.
4. Completing the chapter unlocks the next one (host's campaign bookmark).

How a campaign declares co-op (campaign author)
------------------------------------------------


Like Age of Empires campaign tables, co-op is declared in :strong:```campaign.txt``
alongside ``title`` / ``synopsis``. Do not ship parallel ``N.coop.txt`` files;
single-player and co-op load the same ``N.txt`` mission map.

.. code-block:: text

   title 7747
   synopsis 7751
   coop_campaign 1
   coop_intro 0
   coop_missions 1-29



.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``coop_campaign``
     - ``1`` — campaign appears in the server Co-op campaign menu
   * - ``coop_intro``
     - Cutscene chapter numbers shown in the co-op flow (e.g. prologue `0`)
   * - ``coop_missions``
     - Mission chapter numbers playable in co-op (`1-29`, `1 2 3`, etc.)



The engine parses these in `soundrts/campaign.py <../../../soundrts/campaign.py>`_
(``supports_coop``, ``coop_menu_chapters``, ``coop_mission_chapters``). Co-op games
load the chapter's normal map via ``ensure_chapter_map``. No campaign name is
hard-coded — any mod can opt in via its own ``campaign.txt``.

How a chapter declares co-op slots (map author)
------------------------------------------------


A chapter is just a campaign map. To make it co-op-capable, author it with
more than one human player slot, all meant for the same team:

.. code-block:: text

   nb_players_min 1            ; allow solo + AI partners
   nb_players_max 2            ; two co-op slots (Player A / Player B)
   ; one starting square per slot, in different places:
   player_start 1 a1 raynor footman footman
   player_start 2 h8 raynor2 footman archer
   ; enemies are computer_only as usual (they form their own "ai" team):
   computer_only e5 ...


Key points:

- ``nb_players_max`` = number of co-op player slots. The engine assigns each
  human (and each AI partner) a distinct starting position from the map's
  player starts, so everyone gets their own base/army.
- ``nb_players_min 1`` lets a single human start the mission; the engine fills the
  remaining slots with allied AI partners
  (``Game._fill_coop_ai_partners`` in `soundrts/serverroom.py <../../../soundrts/serverroom.py>`_).
- All human + AI-partner slots are forced onto one team (alliance 1) at
  start. Enemies declared with ``computer_only`` form a separate team
  (``populate_map`` puts them on the ``"ai"`` alliance), so they remain hostile.
- Mission triggers that address ``player1``, ``player2``, ... map to the human
  players in order. AI-partner-only slots are simply not addressed by those
  story triggers (they just fight with their slot's forces).

Single-player ``MissionGame`` still registers one human and uses only the first spawn.

Optional maintenance tool (Raynor only)
----------------------------------------


`tools/generate_raynor_coop_maps.py <../../../tools/generate_raynor_coop_maps.py>`_ applies co-op layout transforms (wider map, mirrored second player, etc.) into :strong:```N.txt`` for *The Legend of Raynor* only. Other campaigns should author ``campaign.txt`` + ``N.txt`` directly.

What scales with difficulty / player count
-------------------------------------------


Enemy unit HP and outgoing damage are scaled deterministically (integer math,
identical on every client) by the chosen difficulty, further increased by the
number of human players. See
`soundrts/coop_difficulty.py <../../../soundrts/coop_difficulty.py>`_.

Determinism notes
------------------


- Difficulty factors are computed once on the server and broadcast, so all
  clients / spectators / replays rebuild an identical world.
- Cross-chapter ``campaign_flag`` carry-over is intentionally a no-op in co-op
  (the world has no local campaign object), avoiding per-client save divergence.
  In-mission ``set_map_flag`` / ``map_flag`` use synced world state and work
  normally.

Tests
------


.. code-block:: bash

   python -m pytest soundrts/tests/test_coop_chapter_maps.py -q
   python -m pytest soundrts/tests/test_changelog_1429_coop_campaign_difficulty.py -q
   python -m pytest soundrts/tests/test_changelog_1429c_coop_story_mission.py -q
   python -m pytest soundrts/tests/test_changelog_1429d_coop_player_slots.py -q
