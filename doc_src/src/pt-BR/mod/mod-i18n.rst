Internacionalização de mods
===========================


Configuração de idioma
----------------------


Os jogadores podem trocar o idioma em menu principal → **Opções** → **Idioma** (salvo em ``language.txt`` do usuário). Também é possível editar esse arquivo, ou usar ``cfg/language.txt`` da instalação como fallback se o arquivo do usuário não existir (ex.: ``zh``, ``fr``, ``pt-BR``). O jogo varre pastas ``ui-xx`` nos recursos carregados e escolhe a melhor correspondência.

Estrutura de diretórios
-----------------------


Mods e o diretório ``res`` usam a mesma estrutura; layout comum:

.. code-block:: text

   mods/mymod/
     rules.txt
     mod.txt                 # opcional
     ui/style.txt
     ui/tts.txt
     ui-zh/tts.txt
     ui-fr/tts.txt
     single/                 # opcional: campanha dentro do mod
       my campaign/
         campaign.txt
         ui/tts.txt
         ui-zh/tts.txt


Traduzir textos do jogo
-----------------------


1. Em ``ui/style.txt``, defina `title <ID numérico>` para unidades/edifícios etc.
2. Em ``ui/tts.txt``, escreva ``7000 Pig Farm``.
3. Em ``ui-zh/tts.txt``, escreva ``7000 猪圈`` (o ID deve ser o mesmo).

Frases inteiras podem usar o formato com igual: ``English phrase = tradução``.

Codificação de tts.txt (importante)
-----------------------------------


Salve sempre em UTF-8. Sem ``; coding:`` o motor lê como UTF-8 por padrão; a primeira linha pode ter ``; coding: utf-8`` (opcional, ajuda alguns editores).

Arquivos legados em GBK devem ter ``; coding: gbk`` na primeira linha, senão a decodificação falha.

Causa comum de caracteres corrompidos: abrir ``tts.txt`` no VS Code/Cursor com a codificação errada e salvar de novo — o texto pode virar `` e se perder permanentemente. Na carga, o motor detecta ``U+FFFD`` e avisa; falha de decodificação gera erro em vez de substituição silenciosa.

Nome do mod no menu
-------------------


Opções → Mods lê por padrão o nome da pasta. Desde 1.4.2.4 você pode definir em ``mod.txt``:

.. code-block:: text

   title 7100


e definir a tradução de ``7100`` em cada ``tts.txt`` de idioma. O mecanismo é o mesmo do ``title`` em ``campaign.txt`` das campanhas.

Se não quiser alterar o mod em si, adicione em ``res/ui-zh/tts.txt`` ou num mod de tradução:

.. code-block:: text

   nome_da_pasta = Nome de exibição


Limitações
----------


- ``rules.txt`` e ``ai.txt`` existem em uma única cópia; não há arquivos por idioma.
- ``ui-xx/style.txt`` em subpastas de mapa/campanha pode não carregar; ``ui-xx/tts.txt`` carrega.
- O menu de pacotes de som ainda usa o nome da pasta.

Exemplos
--------


- `mods/orc/`: ``ui-xx/tts.txt`` em sete idiomas
- `mods/prismalab/ui-fr/`: interface e atalhos em francês

Mais detalhes na seção de multilíngue de mods em ``mod/modding.rst``.
