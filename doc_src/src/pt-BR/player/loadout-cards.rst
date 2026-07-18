Loadout de cartas pré-missão (jogadores)
========================================


Quando e como levar cartas antes do início — e quando você não ouvirá os prompts de cartas.

Formato de arquivo: `cartas atrasadas (mod) <../mod/delayed-card-loadout.htm>`_.


----


Requisitos
----------


Todos os seguintes:

1. Um jogador → Iniciar no mapa → convidar computador → Iniciar (mapa personalizado ou aleatório)
2. O mod tem conquistas ativas (``achievements_enabled`` não é 0)
3. Sua patente concede slots de loadout (ex.: Tenente = 1, Capitão = 2, …)
4. O arsenal tem cartas com cargas restantes e você atende o ``min_rank`` de cada carta

Sem loadout em campanha ou multijogador.


----


Fluxo
-----


1. Configure o mapa e a IA, pressione Iniciar.
2. Facção aleatória (mods multifacção): a voz pede a facção desta partida.
3. Sem slots ou sem cartas usáveis: a partida começa na hora — sem voz de “selecionar carta de loadout”.
4. Caso contrário: escolha uma carta por slot, pule o slot ou comece agora.
5. Efeitos aplicam no jogo (instantâneos ou atrasados); uma carga por carta usada.


----


Efeitos típicos
---------------


- Cartas de recurso — bônus no início
- Cartas de reforço — unidades perto do seu início (consomem população)
- Cartas atrasadas — carga gasta no início; unidades ou tech chegam após tempo de jogo

O arsenal fala o efeito de cada carta quando você a percorre.


----


Confusões comuns
----------------



.. list-table::
   :header-rows: 1

   * - Situação
     - O que acontece
   * - Jogador novo, ainda sem cartas
     - Vai direto à partida — sem menu de cartas
   * - Facção aleatória
     - Pode ouvir só a seleção de facção, não as cartas
   * - Patente baixa demais
     - Cartas ficam no arsenal mas não podem ser selecionadas




----


Ver também
----------


- `conquistas <achievements.htm>`_
- `Notas de versão <../../relnotes.htm>`_
