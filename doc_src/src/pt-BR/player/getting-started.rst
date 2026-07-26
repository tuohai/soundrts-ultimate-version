Guia do jogador SoundRTS — Comece aqui
======================================



Um caminho de leitura progressivo: básicos → núcleo RTS → recursos modernos → multijogador → mods.

Autores de mods: `Primeiros passos para desenvolvedores <../mod/getting-started.htm>`_.


----


O que é o SoundRTS?
-------------------


Um jogo de estratégia em tempo real em áudio, inspirado em Warcraft e StarCraft, feito para jogadores cegos e para quem gosta de comandar pelo ouvido. Duas visões:


.. list-table::
   :header-rows: 1

   * - Modo
     - Entrada
     - Melhor para
   * - Modo mapa (padrão)
     - ao iniciar
     - Macro: selecionar unidades, dar ordens, checar recursos
   * - Modo primeira pessoa (RPG)
     - Alt+Espaço / Ctrl+Espaço
     - Micro: andar, mirar habilidades




----


Nível 1 — Começo em dez minutos
-------------------------------


Objetivo: selecionar um camponês, minerar ouro, construir uma fazenda e uma casa.


.. list-table::
   :header-rows: 1

   * - Ação
     - Tecla
   * - Próxima unidade aliada
     - Q
   * - Próximo edifício
     - W
   * - Próximo / anterior comando
     - A / Shift+A
   * - Próximo / anterior alvo
     - Tab / Shift+Tab
   * - Confirmar
     - Enter
   * - Comando padrão no alvo
     - Backspace



Recursos: Z ouro · X madeira · Shift+Z comida · C população.

Movimento: setas, Page Up/Down entre quadrados interessantes, Espaço para seguir a seleção.

Lista completa de comandos: `manual.rst <../../../player/manual.rst>`_ §3, ou menu F10 no jogo.


----


Nível 2 — Ciclo central de RTS
------------------------------


- Economia: camponeses → casas (limite de população) e fazendas (comida) → edifícios → exército
- Ponto de reunião: selecione a prefeitura → Tab até a mina de ouro → Backspace
- Grupos: Shift+6–9 para salvar, 6–9 para recuperar
- Reconhecimento: o modo defesa foge de inimigos mais fortes
- Movimento/ataque forçado: Ctrl+Backspace
- Zoom: F8 (subquadrados para posicionamento preciso)

Dicas: `comportamento padrão das unidades <unit-default-behavior.htm>`_


----


Nível 3 — Recursos modernos (1.4+)
----------------------------------



.. list-table::
   :header-rows: 1

   * - Tópico
     - Doc
   * - Atributos / inventário / equipamento
     - `Inventário <inventory.htm>`_
   * - Conquistas, patentes, arsenal
     - `Conquistas <achievements.htm>`_
   * - Pontuação pós-partida (S–E)
     - `Pontuação e notas <score-and-grades.htm>`_
   * - Cartas pré-missão
     - `Cartas de loadout <loadout-cards.htm>`_
   * - Campanhas e cooperativo
     - `Menu de campanha <campaign-menu.htm>`_
   * - Mapas aleatórios (semente / código de compartilhamento)
     - `Mapas aleatórios <random-map-play.htm>`_
   * - Atalhos em camadas
     - `Atalhos em camadas <layered-hotkeys.htm>`_
   * - Levar itens a um quadrado
     - `Levar itens <brought-items.htm>`_



----


Nível 4 — Multijogador
----------------------


Menu principal → multijogador → escolher servidor → criar/entrar na sala → F7 chat. Equipes fixas antes do início; alianças dinâmicas F12 / F4 / Ctrl+F4 quando permitido. Porta padrão 2500.


----


Nível 5 — Mods e docs temáticos
-------------------------------


Ative em ``user/SoundRTS.ini``: ``mods = soundpack,starcraft`` ou ``--mods=...``


.. list-table::
   :header-rows: 1

   * - Tópico
     - Doc
   * - Caça / pastoreio
     - `Caça <hunting.htm>`_
   * - Ataques em rajada
     - `Ataques em rajada <burst-attacks.htm>`_
   * - Recursos StarCraft
     - `Recursos StarCraft <starcraft-resources.htm>`_
   * - Add-ons Terran
     - `Terran <starcraft-terran.htm>`_
   * - Creep Zerg
     - `Creep Zerg <starcraft-zerg-creep.htm>`_



Atualizações automáticas
~~~~~~~~~~~~~~~~~~~~~~~~

Na abertura o jogo verifica por padrão se há um Release mais novo no GitHub. Enter atualiza, Esc cancela.
Ligue/desligue em Opções → **Verificar atualizações ao iniciar o jogo**. Use Opções → **Verificar atualizações agora** para checagem manual. O pacote Windows baixa em ``user/tmp/`` (ou ``%APPDATA%\\SoundRTS\\tmp/`` se instalado); a partir do código-fonte só abre a página de download. Veja o manual e as `Notas de versão <../../relnotes.htm>`_ (1.4.6.4).


Notas de versão: `Notas de versão <../../relnotes.htm>`_ — histórico completo.


----


Próximos passos
---------------


- Jogue o tutorial → docs do Nível 3 conforme precisar
- Modding: `Primeiros passos para desenvolvedores <../mod/getting-started.htm>`_
- Índice: `Documentação do jogador <index.htm>`_
