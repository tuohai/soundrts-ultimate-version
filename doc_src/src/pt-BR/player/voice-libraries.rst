Bibliotecas de voz principal e secundária (jogadores)
=====================================================


O jogo usa duas bibliotecas de voz configuráveis em separado: principal e secundária. Você pode ativar ou desativar a secundária; desativada, a principal anuncia tudo.


----


Funções
-------


.. list-table::
   :header-rows: 1

   * - Biblioteca
     - Anuncia
   * - **Principal**
     - Menus, operações do jogador; tudo fora da partida; e na partida o **feedback econômico/produção** (unidade/prédio pronto, pesquisa, avanço de era, recursos, menu alterado…)
   * - **Secundária**
     - Eventos passivos de **campo de batalha** (inimigos, baixas, scout, alertas de combate, mensagens do mundo…)

Com a secundária **ativada**: principal e secundária podem sobrepor-se.

- **Alt esquerdo**: pula/para a biblioteca **principal**
- **Alt direito**: pula/para a biblioteca **secundária**

Com a secundária **desativada**: a principal fala tudo; **Alt esquerdo e Alt direito pulam a fala atual** (não há secundária para filtrar).


----


Onde configurar
---------------


1. Menu principal → **Opções** → **Configurações da biblioteca de voz**
2. Opções:
   - **Ativar ou desativar a voz secundária** (ou **F3** em qualquer menu; não na partida)
   - Editores **principal** / **secundária**: volume, tom, velocidade, voz, placa de som
   - **Abrir pasta de vozes**: abre ``user/voices``


----


Parâmetros e atalhos
--------------------


No editor:

- Cima/Baixo: parâmetro (volume / tom / velocidade / voz / dispositivo)
- Esquerda/Direita: ajustar
- Enter ou Esc: voltar

Na partida (e menus):

- **F9–F12**: biblioteca principal
- **Shift+F9–F12**: biblioteca secundária
- **Shift esquerdo+C** / **Shift direito+C**: copiar última linha principal / secundária
- **Shift+A**: acrescentar à área de transferência
- **F3 nos menus**: ativar/desativar secundária (não na partida)


----


Adicionar vozes
---------------


Use **Abrir pasta de vozes** (em geral ``user/voices``).

Vozes SAPI do Windows
~~~~~~~~~~~~~~~~~~~~~

1. Instale e registre uma voz SAPI5 no Windows.
2. No jogo, percorra o parâmetro **voz** na principal ou secundária.
3. Algumas vozes só de 32 bits passam por ``tools/sapi32``.

Pastas de pacote (nomes amigáveis)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crie uma subpasta em ``user/voices`` com ``voice.ini``::

    [voice]
    title=Meu nome
    sapi=Microsoft Huihui Desktop
    rate=0

- ``title``: nome nos menus
- ``sapi``: deve corresponder a uma voz SAPI registrada
- ``rate``: opcional, cerca de -10…10

Os pacotes **não** instalam um motor TTS; só dão alias a uma voz SAPI existente.

Nuance / vozes Apple (opcional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Se houver dados Nuance em ``user/voices/nuance``, aparecem na lista. Veja as notas dessa pasta.

Principal e secundária podem usar **só SAPI**; Nuance é opcional e precisa do helper Java 32 bits em ``tools/nuance_ve``.


----


Alertas direcionais na partida (pan estéreo)
--------------------------------------------


Algumas falas passivas **ligadas a uma casa** (inimigo avistado, baixas, scout, alertas de combate) são panoramizadas esquerda/direita em relação à casa de vista atual (mesma lógica dos SFX do minimapa).

Com fones: na vista aérea olhando para o norte, leste à direita e oeste à esquerda.

**O pan atualiza se você mudar de casa no meio da fala** (não precisa esperar a próxima mensagem).


----


Leitores de tela
----------------


Se for detectado um leitor dedicado (ex.: NVDA), ele pode assumir a **principal**. A secundária (quando ativa) continua com o perfil secundário do jogo.


----


Ver também
----------


- `Notas de lançamento <../../relnotes.htm>`_ — 1.4.5.4 (duas bibliotecas), 1.4.5.5 (pan, funções, Alt esq./dir.)
- `Manual do jogo <manual.htm>`_
