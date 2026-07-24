# Esquema de atalhos em camadas

Este guia descreve os atalhos da interface em camadas do SoundRTS: uma camada base global mais uma camada por interface, para a mesma tecla física significar coisas diferentes em modos distintos. Destinado a jogadores e autores de mods que personalizam bindings.


----


1. Visão geral e motivação
----------------------------


Esquema antigo
~~~~~~~~~~~


Todos os atalhos ficavam em um único arquivo ``res/ui/bindings.txt``. As teclas ficaram saturadas; a mesma letra conflitava entre seleção de unidades, ordens e navegação no mapa.

Novo esquema
~~~~~~~~~~~


- Camada global: recursos, movimento, saltos de quadrado, confirmação de comando — disponível em todo modo.
- Camada de interface: bindings específicos do modo (unidade, edifício, comando, habilidade, mapa, etc.).
- Troca de modo: teclas F alternam dentro de grupos; ajuda / mapa / diplomacia são modos sobrepostos que restauram o modo anterior ao sair.

Implementação: ``soundrts/clientgame/interface_modes.py``.


----


2. Arquitetura e regras de carregamento
-----------------------------------


.. code-block:: text

   flowchart TD
       global[global_bindings.txt]
       mode[current mode txt]
       custom[cfg/bindings.txt]
       mod[mod bindings.txt]
       global --> merge[merged load]
       mode --> merge
       custom --> merge
       mod --> merge
       merge --> active[active hotkeys]


Ordem de carregamento
~~~~~~~~~~~


1. `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_ (base global)
2. Arquivo do modo atual (veja tabela abaixo)
3. Substituições do usuário `cfg/bindings.txt <../../../soundrts/paths.py>`_ (``CUSTOM_BINDINGS_PATH``)
4. ``bindings.txt`` de mod não-stub (acréscimo legado)

Carregamentos posteriores substituem anteriores para a mesma tecla.

Subtelas e RPG
~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Contexto
     - Comportamento
   * - Inventário / equipamento / atributos
     - Substitui temporariamente ``\_bindings``; ``restore_active_bindings`` ao sair
   * - RPG primeira pessoa
     - Adicional [``res/ui/rpg_bindings.txt``](../../../res/ui/rpg_bindings.txt)
   * - Editor de mapas
     - Independente [``res/ui/editor_bindings.txt``](../../../res/ui/editor_bindings.txt)



Arquivos de modo
~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Modo
     - Arquivo
   * - Global
     - ``global_bindings.txt``
   * - Seleção de unidades
     - ``unit_bindings.txt``
   * - Seleção de edifícios
     - ``building_bindings.txt``
   * - Comandos
     - ``command_bindings.txt``
   * - Habilidades
     - ``skill_bindings.txt``
   * - Primeira pessoa (RPG)
     - ``rpg_bindings.txt``
   * - Ajuda e consulta
     - ``help_bindings.txt``
   * - Navegação no mapa
     - ``map_bindings.txt``
   * - Diplomacia
     - ``diplomacy_bindings.txt``




----


3. Troca de modo (teclas F e ESC)
------------------------------------



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - F1
     - Seleção de unidades ↔ Seleção de edifícios
   * - F2
     - Comandos ↔ Habilidades
   * - F3
     - Inventário ↔ Equipamento (exige uma unidade aliada; veja [inventory-and-equipment.md](inventory-and-equipment.htm))
   * - F4
     - Entrar em ajuda e consulta (pressione de novo ou Esc para sair)
   * - F12
     - Entrar em diplomacia (pressione de novo ou Esc para sair)
   * - ESC
     - Cancelar ordem / sair de sub-tela; caso contrário entrar em navegação no mapa



Trocar para modos que não sejam mapa anuncia o nome do modo (ex. "unit selection", "command mode").

Comportamento especial quando ESC entra em navegação no mapa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Ação
     - Voz
     - Estado interno
   * - ESC → mapa
     - Sempre anuncia "map browse" + visão geral do quadrado atual
     - Se depósito/meadow/passagem foi selecionado antes, restaura silenciosamente `interface.target`
   * - ``f`` / ``g`` / ``m`` / ``p`` no mapa
     - Anuncia o elemento como de costume
     - Salva seleção para restaurar ao sair do mapa



Exemplo: No modo mapa, ``f`` seleciona uma mina de ouro → F1 para modo unidade, selecione um camponês → ESC de volta ao mapa → você ouve "map browse, 8, 13, 1 town hall…" (visão do quadrado), não a mina de novo; o foco permanece na mina, então pode pressionar Enter para enviar a ordem de coleta imediatamente.

Sair do modo mapa salva o foco atual do mapa via ``save_map_browse_target``.


----


4. Atalhos globais
-------------------


Sempre ativos em todo modo (``global_bindings.txt``).

Recursos e população
~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``z``
     - Status do recurso 1
   * - ``x``
     - Status do recurso 2
   * - ``SHIFT Z``
     - Status do recurso 3
   * - ``c``
     - Status da população



Entrada rápida (legado)
~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``ALT V``
     - Tela de atributos
   * - ``SHIFT V``
     - Inventário
   * - ``CTRL V``
     - Equipamento



Seleção de alvo
~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``TAB`` / ``SHIFT TAB``
     - Próximo / anterior alvo
   * - ``CTRL TAB`` / ``CTRL SHIFT TAB``
     - Próximo / anterior alvo útil



Movimento
~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - Setas
     - Mover 1 quadrado
   * - ``SHIFT`` + setas
     - Mover 5 quadrados
   * - ``CTRL`` + setas
     - Mover 1 quadrado (sem colisão)
   * - ``CTRL SHIFT`` + setas
     - Mover 5 quadrados (sem colisão)



Saltos de quadrado
~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``PAGE DOWN`` / ``PAGE UP``
     - Próximo / anterior quadrado explorado
   * - ``CTRL PAGE DOWN`` / ``CTRL PAGE UP``
     - Quadrados em conflito
   * - ``ALT PAGE DOWN`` / ``ALT PAGE UP``
     - Quadrados desconhecidos
   * - ``SHIFT PAGE DOWN`` / ``SHIFT PAGE UP``
     - Quadrados com recursos



Comando padrão e confirmação
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``BACKSPACE``
     - Comando padrão
   * - ``SHIFT BACKSPACE``
     - Comando padrão (fila)
   * - ``CTRL BACKSPACE``
     - Comando padrão (imperativo)
   * - ``RETURN`` / ``ENTER`` do teclado numérico
     - Validar ordem
   * - Com ``SHIFT`` / ``CTRL``
     - Variantes fila / imperativo



Observação e consulta
~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``LCTRL`` / ``RCTRL``
     - Examinar
   * - ``SPACE``
     - Status da unidade
   * - ``v``
     - Pontos de vida
   * - ``F9`` / ``SHIFT F9``
     - Objetivos
   * - ``F11``
     - Lista de jogadores



Sistema
~~~~~~~



.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``F5`` / ``F6``
     - Histórico anterior / próximo
   * - ``F10`` / ``CTRL C`` / ``ALT F4``
     - Menu do jogo
   * - ``HOME`` / ``END`` etc.
     - Volume
   * - ``ALT SPACE`` / ``CTRL SPACE``
     - Modo primeira pessoa
   * - ``CTRL F2``
     - Alternar tela + qualidade visual (persistente; ver manual)
   * - ``CTRL F3``
     - Alternar relógio falante
   * - ``CTRL SHIFT F4``
     - Mudar visão do jogador
   * - ``ALT M`` etc.
     - Volume da música




----


5. Atalhos por interface
--------------------------


5.1 Seleção de unidades
~~~~~~~~~~~~~~~~~~~


Arquivo: ``unit_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Categoria
     - Teclas
     - Notas
   * - Lote de soldados
     - ``a``
     - Todos locais; ``CTRL a`` em todo o mapa
   * - Ciclar unidade
     - ``q`` / ``SHIFT q``
     - Local; ``CTRL q`` em todo o mapa
   * - Atalho de ordem
     - ``b``
     - Usa ``shortcut`` das ordens em style.txt
   * - Filtros
     - ``m`` / ``n``
     - Lado / tipo ao escolher alvos
   * - Trabalhadores
     - ``s`` lote / ``w`` ciclar
     - Antigas teclas ``d``/``e``
   * - Soldados 1–7
     - `d/e` … `;/p`
     - Mesma região de teclas que edifícios
   * - Grupos
     - ``1``–`5` definir, `6`–`9` recolher
     - ``CTRL`` para grupos em todo o mapa



Modo unidade pode substituir ``BACKSPACE`` localmente.

5.2 Seleção de edifícios
~~~~~~~~~~~~~~~~~~~~~~~


Arquivo: ``building_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Linha de tecla
     - Mapeia para
   * - ``d f g h j k l ;``
     - building1 – building8
   * - ``e r t y u i o p``
     - building9 – building16



Por tecla: selecionar tipo local; ``SHIFT`` + tecla cicla um; ``CTRL`` + tecla seleciona em todo o mapa.

Config do mod: defina ``keyboard building1`` … ``keyboard building16`` em ``style.txt`` (junto com ``keyboard building`` genérico). Exemplo da campanha base: townhall→building1, house→building2.

5.3 Modo de comandos
~~~~~~~~~~~~~~~~~


Arquivo: ``command_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Slot
     - Teclas
   * - Navegar
     - ``a`` / ``SHIFT a``
   * - 1–9
     - `s d f g h j k l ;`
   * - 10–18
     - ``w e r t y u i o p``
   * - 19–30
     - ``1``–`0` `-` `=`
   * - Repetir
     - ``ALT x`` / ``ALT z``



Slots seguem a ordem do menu da unidade; teclas extras dizem "none" se houver menos de 30 ordens.

5.4 Modo de habilidades
~~~~~~~~~~~~~~~


Arquivo: ``skill_bindings.txt``


.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``a`` / ``SHIFT a``
     - Navegar menu de habilidades (próximo / anterior)



5.5 Modo primeira pessoa (RPG)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Ao entrar no modo primeira pessoa (``ALT SPACE`` global), ``rpg_bindings.txt`` é empilhado sobre os bindings da interface atual.


.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - `1`–`9`
     - Habilidades 1–9
   * - ``0``
     - Habilidade 10
   * - `-` / `=`
     - Habilidades 11 / 12
   * - ``ALT /``
     - Lista de habilidades
   * - ``CTRL A``
     - Ataque automático
   * - ``CTRL F8`` / ``SHIFT F8`` / ``ALT F8``
     - Precisão do zoom subir / descer / consultar



Teclas de direção e ``SHIFT`` +direção movem e giram em primeira pessoa (veja comentários no arquivo).

5.6 Navegação no mapa
~~~~~~~~~~~~~~~


Arquivo: ``map_bindings.txt``

Movimento e saltos de quadrado são globais (seção 4).

Estas teclas ciclam alvos no quadrado atual (sem mudar de quadrado):


.. list-table::
   :header-rows: 1

   * - Tecla
     - Ação
   * - ``f`` / ``r``
     - depósito resource1 (ex. ouro)
   * - ``g`` / ``t``
     - depósito resource2 (ex. madeira)
   * - ``y`` / ``h``
     - depósito resource3 (ex. comida)
   * - ``m`` / ``SHIFT m``
     - Meadow
   * - ``p`` / ``SHIFT p``
     - Passagem / ponte
   * - Série F8
     - Zoom



Após selecionar um depósito, use ``BACKSPACE`` / ``RETURN`` globais para emitir coleta; meadow para construir; passagem para mover/bloquear.

5.7 Ajuda e diplomacia
~~~~~~~~~~~~~~~~~~~~~~~


Ajuda (`help_bindings.txt <../../../res/ui/help_bindings.txt>`_): ``1``/``2`` navegar ajuda, ``3`` dizer hora, ``F7`` falar, ``CTRL SHIFT F3`` alternar exibição de tick.

Diplomacia (`diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_): ``1`` selecionar candidato, ``q`` solicitar, ``w`` aceitar, ``e`` recusar/cancelar.

``ESC`` em modos sobrepostos chama ``exit_overlay_mode``.


----


6. Fluxos típicos
----------------------


Coleta
~~~~~~~~~~


1. Modo unidade: ``s`` selecionar camponês
2. ``F2`` modo comando, ``s`` escolher coleta (ou ``b`` + atalho de letra)
3. ``ESC`` navegação no mapa
4. ``f`` selecionar mina de ouro (anunciada)
5. ``RETURN`` para confirmar

Se você já selecionou uma mina e saiu do mapa: ``ESC`` de volta anuncia visão do quadrado; foco permanece na mina — pressione ``RETURN`` diretamente.

Construção
~~~~~~~~~


1. ``ESC`` mapa → ``m`` selecionar meadow
2. ``F2`` escolher slot de construção
3. ``RETURN`` confirmar

Diplomacia
~~~~~~~~~~


1. ``F12`` diplomacia
2. `1` selecionar candidato
3. ``q`` solicitação de aliança

.. code-block:: text

   sequenceDiagram
       participant U as UnitMode
       participant C as CommandMode
       participant M as MapMode
       U->>U: s select peasant
       U->>C: F2
       C->>C: s order slot 1
       C->>M: ESC
       M->>M: f select mine
       M->>C: RETURN validate



----


7. Personalização para mods
---------------------------


Qual arquivo editar
~~~~~~~~~~~~~~~~~~~


- Comportamento global: ``global_bindings.txt``
- Uma interface: o `*_bindings.txt` correspondente
- Não edite o corpo de ``bindings.txt`` (apenas stub) a menos que entenda o comportamento legado de acréscimo de mod

Modificadores
~~~~~~~~~~~~~

- Permitidos: ``CTRL``, ``ALT``, ``SHIFT`` (qualquer lado), ``LSHIFT``, ``RSHIFT`` (mais teclas standalone como ``LALT`` / ``RALT``).
- Não coloque ``LSHIFT``/``RSHIFT`` e ``SHIFT`` na mesma linha; a busca prefere o lado específico e depois o ``SHIFT`` genérico.

Substituições do usuário
~~~~~~~~~~~~~~~


Mapeamento no jogo (recomendado): Menu principal → Opções → Mapeamento de teclas (irmão de Esquema de atalhos). Suporta esquemas em camadas e clássico, todas as camadas, busca, variantes, teclas alias e importação/exportação da área de transferência. Configurações ficam por mod em ``user/hotkey_overrides/{mod_key}.json`` e aplicam na próxima partida. Veja `developer: hotkey mapping editor <../../mod/hotkey-mapping-editor.htm>`_.

Esquema de atalhos: Opções → Esquema de atalhos alterna em camadas/clássico; mover a seleção anuncia ativo ou inativo para o esquema atual.

Arquivo manual: Acrescente ou substitua teclas em ``cfg/bindings.txt``; carregado por último (ainda acrescentado após substituições baseadas em JSON).

Notas
~~~~~~


- Slots ``select_order_index`` dependem da ordem do menu
- Slots ``buildingN`` precisam ``keyboard buildingN`` em ``style.txt``
- ``b`` de unidade (``order_shortcut``) usa ``shortcut`` de cada ordem no style


----


8. Atalhos clássicos em arquivo único
--------------------------------


Para restaurar o conjunto de bindings pré-1.4.3 (F4 solicitação de aliança, F12 candidato de aliança, ESC sem modo de navegação no mapa, etc.):

Opção A (recomendada): Menu principal → Opções → Esquema de atalhos, depois escolha Atalhos em camadas ou Atalhos clássicos.

Opção B (editar ini manualmente):

1. Abra :strong:```user/SoundRTS.ini`` (muitas vezes `%APPDATA%\SoundRTS\SoundRTS.ini` no Windows).
2. Em `````[general]```, adicione ou defina:

.. code-block:: ini

      layered_hotkeys = 0


3. Reinicie o jogo (deve estar definido antes de uma partida começar).

Quando desabilitado:

- Apenas `res/ui/legacy_bindings.txt <../../../res/ui/legacy_bindings.txt>`_ é carregado — sem ``global_bindings.txt`` ou camadas por modo.
- ``bindings.txt`` de mod não-stub e ``user/bindings.txt`` ainda são acrescentados (substituições do usuário vencem).
- Comandos de troca de modo F1/F2/F3/F4/F12/ESC emitem beep; ESC cancela ordens / sai de sub-telas / sai de imersão ou zoom, e não entra em modo de navegação no mapa.
- Inventário (``i``), equipamento (``u``), atributos (Alt+V), etc. seguem ``legacy_bindings.txt``.

Para reativar modo em camadas: defina ``layered_hotkeys = 1`` (ou remova a linha; padrão é 1) e reinicie.


----


9. Diferenças do esquema antigo
------------------------------------



.. list-table::
   :header-rows: 1

   * - Antigo
     - Novo
   * - F1/F4 ajuda direta
     - F4 entra em modo ajuda; F9/F11 globalizados
   * - F12 diplomacia direta
     - F12 entra primeiro em modo diplomacia
   * - Trabalhador ``d``/``e``
     - Modo unidade ``s``/``w``
   * - Teclas de soldado
     - Remapeadas para `d/e`…`;`/p`
   * - Mapa ``f`` saltou quadrados
     - ``f`` cicla depósitos no quadrado atual
   * - ESC para mapa anunciava último alvo
     - ESC anuncia visão do quadrado; foco restaurado silenciosamente



Bindings de atributos e editor inalterados.


----


Arquivos fonte relacionados
---------------------


- `res/ui/global_bindings.txt <../../../res/ui/global_bindings.txt>`_
- `res/ui/unit_bindings.txt <../../../res/ui/unit_bindings.txt>`_
- `res/ui/building_bindings.txt <../../../res/ui/building_bindings.txt>`_
- `res/ui/command_bindings.txt <../../../res/ui/command_bindings.txt>`_
- `res/ui/skill_bindings.txt <../../../res/ui/skill_bindings.txt>`_
- `res/ui/map_bindings.txt <../../../res/ui/map_bindings.txt>`_
- `res/ui/help_bindings.txt <../../../res/ui/help_bindings.txt>`_
- `res/ui/diplomacy_bindings.txt <../../../res/ui/diplomacy_bindings.txt>`_
- `soundrts/clientgame/interface_modes.py <../../../soundrts/clientgame/interface_modes.py>`_
