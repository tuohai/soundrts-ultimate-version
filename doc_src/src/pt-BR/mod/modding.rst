Manual de modding
:::::::::::::::::

.. contents::

mods
----

As regras e a aparência do jogo podem ser alteradas por mods.

Um mod é uma pasta que pode conter rules.txt, ai.txt, ui (e suas versões localizadas). A estrutura da árvore é a mesma da pasta ``res``.

Os mods ficam na pasta ``mods`` da pasta principal ou na pasta ``mods`` da pasta do usuário. Para ser ativado, um mod deve ser referenciado no parâmetro ``mods =`` em SoundRTS.ini.
Por exemplo: mods = soundpack,mymod,my_other_mod

O arquivo rules.txt fará patch no arquivo padrão. Por exemplo, um rules.txt com estas 2 linhas: ``def peasant`` e ``decay 20`` fará com que qualquer camponês desapareça após 20 segundos.

Localização de mods (ui-xx)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Pastas de mod espelham a árvore ``res``. Adicione pastas localizadas ao lado de ``ui/`` (``ui-zh``, ``ui-fr``, ``ui-de``, etc.). O jogo carrega o idioma de ``language.txt`` do usuário / Opções → Idioma (com ``cfg/language.txt`` ou o locale do sistema como fallback); entradas ausentes recorrem a ``ui/tts.txt``.

Layout recomendado (``mods/mymod/``)::

    ui/style.txt          ; title 7000
    ui/tts.txt            ; 7000 Pig Farm
    ui-zh/tts.txt         ; 7000 猪圈
    ui-fr/tts.txt         ; 7000 Ferme à porcs
    mod.txt               ; opcional: dependências e título no menu (abaixo)

O que você pode traduzir (com o mod ativo):

- Nomes de unidade/edificação/facção: ``title \<ID\>`` em ``style.txt`` + o mesmo ID em cada ``tts.txt``
- Introduções de unidade: ``intro \<ID\>`` + ``tts.txt``
- Mapas/campanhas dentro do mod: IDs TTS de ``title``/``intro`` do mapa; pastas de campanha podem usar ``title`` em ``campaign.txt`` (igual às campanhas em ``res/single``)
- Frases completas: em ``tts.txt``, ``english phrase = translated phrase``

Nome exibido no menu de mods (Opções → Mods, desde 1.4.2.4):

Adicione uma linha ``title`` em ``mod.txt``, mesma sintaxe que ``campaign.txt`` — ID TTS ou palavras separadas por espaço::

    title 7100

Defina esse ID em ``ui/tts.txt`` e em cada ``ui-xx/tts.txt`` (ex.: ``7100 Orc Faction Mod`` / ``7100 兽人模组``). Sem ``title``, o nome da pasta é falado.

Alternativamente, mapeie nomes de pasta via entradas de frase em ``res/ui-zh/tts.txt`` global ou um mod de tradução pequeno, ex.: ``crazyMod9beta10 = 疯狂模组``.

Notas: ``rules.txt`` / ``ai.txt`` não são localizados. ``ui-xx/style.txt`` localizado em subpastas de mapa/campanha pode não carregar, mas ``ui-xx/tts.txt`` nessas pastas sim. Soundpacks (mods sem ``rules.txt``) também suportam ``title`` em ``mod.txt`` e ``tts.txt`` localizado em Opções → Soundpacks.

Exemplos neste repositório: ``mods/orc/``, ``mods/prismalab/ui-fr/``.

clear
>>>>>

Para substituir rules.txt ou style.txt em vez de fazer patch, use o comando ``clear`` no topo do arquivo. Isso não funciona com ai.txt,
e de qualquer forma não é necessário, porque em ai.txt o comando def reescreve a definição de IA.

is_a
>>>>

Enquanto em style.txt ``is_a`` é uma forma de herdar todas as propriedades de outra definição,
em rules.txt, ``is_a`` também é usado para garantir que um keep ou um castelo permitirá o que um town hall permitiria.

Nota: as árvores de herança em style.txt e em rules.txt não precisam coincidir.

as regras
---------

Desde o SoundRTS 1.1, as regras do jogo ficam em um arquivo chamado rules.txt.

faction
>>>>>>>

Cada facção é definida em rules.txt. Por exemplo::

	def orc_faction
	class faction

Nota: o nome ``orc_faction`` termina com ``_faction`` apenas para evitar conflitos de nome. Esse sufixo ``_faction`` não é obrigatório desde que o nome seja único.

No seletor de facção, as setas leem só ``title``. Com ``intro``, pressione **G** para um submenu frase a frase (desde 1.4.7.2).

unit
>>>>

Nota: uma unidade também pode ser uma edificação.

count_limit
===========

Novo no SoundRTS 1.2 alpha 10.

``count_limit <value>``

O valor padrão é 0 (sem limite).
Quando o limite está ativo, um tipo de unidade que atinge o limite não pode ser treinado,
construído, invocado, ressuscitado ou adicionado por um gatilho (add_unit).
Conversão não é afetada.

mdg_projectile / rdg_projectile
=================================

Novo no SoundRTS 1.3.8.2. Restrição terreno baixo vs alto adicionada em 1.3.9.1.
Substitui o obsoleto ``is_ballistic``.

``mdg_projectile 0|1``

``rdg_projectile 0|1``

O valor padrão é 0. Quando definido como 1, o tipo de ataque correspondente é tratado como
projétil:

- Em terreno elevado, a unidade ganha alcance extra ao atacar alvos em altitude menor
  (+1 casa por nível de altura)
- Unidades sem projétil não podem atacar alvos terrestres em terreno elevado de baixo,
  independentemente do alcance

Migração: mods que usavam ``is_ballistic 1`` devem usar ``rdg_projectile 1`` (à distância) ou
``mdg_projectile 1`` (projéteis corpo a corpo, como catapultas); cada tipo de ataque é configurado
separadamente.

Exemplo de projétil à distância::

    def archer
    rdg 3
    rdg_range 4
    rdg_projectile 1

projectile_lead
===============

Flag de unidade (0/1, ``int_properties``, padrão 0): se **projéteis à distância preveem / acertam alvos em movimento**.

- ``0``: o projétil mira o ponto no momento do disparo; se o alvo se afastou no impacto → erro
- ``1``: os projéteis podem prever alvos em movimento (estilo «Balística» de Age of Empires II)

**Requer velocidade de voo**: à distância precisa de ``rdg_projectile`` + ``rdg_projectile_speed`` (**casas/s**, >0). Caso contrário o acerto é instantâneo e a verificação de erro por movimento nunca importa.

Esses campos são **velocidade**, não «segundos de voo». Exemplo: ``7`` = sete casas por segundo. Não coloque um atraso de acerto desejado (ex.: 0.57) no campo.

**Não fixe o nome de uma tecnologia no motor.** Conceda o flag com um bônus de tecnologia, ex.::

    effect info 8510
    effect bonus projectile_lead 1
    effect_bonus_targets archer_unit -hand_cannoneer galley scouttower

As unidades ainda precisam da tecnologia em ``can_use_tech``. A UI de atributos não anuncia o ``+1`` deste flag; use ``effect info <tts_id>`` para um texto legível (veja *info* abaixo).

Distinto de ``rdg_projectile`` (regras de combate de projétil como alcance em terreno elevado). ``projectile_lead`` só controla o erro contra um alvo que se moveu.

projectile_speed / mdg_projectile_speed / rdg_projectile_speed
==============================================================

**Velocidade de voo** do projétil por tipo de ataque em casas/segundo (PRECISION), padrão 0.

- ``rdg_projectile_speed``: só para acertos **à distância** quando ``rdg_projectile 1``
- ``mdg_projectile_speed``: só para acertos de **projétil corpo a corpo** quando ``mdg_projectile 1``
- ``projectile_speed``: nome compartilhado obsoleto; no carregamento migra para a(s) via(s) correspondente(s)

**Não** coloque aqui «quantos segundos até o impacto» — é velocidade. O motor calcula a chegada como **distância ÷ velocidade** (mais longe = mais demora). Velocidade 0 ou ataque não-projétil → acerto instantâneo.

Uma unidade pode ter ``mdg`` e ``rdg`` ao mesmo tempo (mesmo com o mesmo alcance): só a via com ``*_projectile`` voa nessa velocidade.

aoe2 aproximado DE (todas **velocidades**): flechas/torres ``7``, mangonel ``3.5``, trabuco ``1.6``.

Exemplo::

    def aoe_archer
    rdg_projectile 1
    rdg_projectile_speed 7

    def mangonel
    mdg_projectile 1
    mdg_projectile_speed 3.5

Veja também: `Previsão de projéteis e velocidade de voo <projectile-lead.htm>`_.

is_teleportable
================

Novo no SoundRTS 1.2 alpha 9.

``is_teleportable 1``

A unidade (ou edificação) é afetada pelo efeito de teletransporte ou pelo efeito recall.

hp_regen
=========

Novo no SoundRTS 1.2 alpha 11

``hp_regen <taxa de regeneração de pontos de vida>``

Por exemplo, com ``hp_regen 0.15``, a unidade recupera 0,15 pontos de vida por segundo.

mana_start
===========

Novo no SoundRTS 1.2 alpha 10.

``mana_start 50``

No exemplo, a unidade começará com 50 de mana em vez de mana_max. O valor padrão de mana_start é 0. Se mana_start for 0 ou negativo, usa-se mana_max.

provides_survival
==================

Novo no SoundRTS 1.2 alpha 9.

``provides_survival 1``

Ter pelo menos uma unidade (ou edificação) com ``provides_survival`` igual a 1 impede que um jogador perca em partida multijogador (não em campanha single-player). O gatilho afetado é ``no_building_left``. Por padrão, apenas edificações têm essa propriedade definida como 1. Canteiros de obras têm essa propriedade em 0 e não pode ser alterada.

victory_time
=============

Novo no SoundRTS 1.4.5.8.

``victory_time <segundos>``

O valor padrão é 0 (sem temporizador de vitória). Quando maior que 0 em um prédio **concluído**, a contagem regressiva começa assim que o prédio existe. Se o temporizador chegar a zero e o prédio ainda existir, o dono (e o campo de vitória aliada) vence. Destruir o prédio cancela essa contagem.

Aplica-se a qualquer tipo ``class building``, não só à Maravilha vanilla. Exemplo:

::

    def wonder
    class building
    cost 100 120
    time_cost 900
    hp_max 2500
    requirements imperial_age
    count_limit 1
    victory_time 300

O vanilla inclui ``wonder`` com ``victory_time 300`` (5 minutos após a conclusão). Vozes: TTS 5720 (início), 5721 (cancelamento), 5722 (restante).

storage_bonus
==============

``storage_bonus <bônus para recurso 0> <bônus para recurso 1> ...``

Por exemplo, ``storage_bonus 0 1`` causará um bônus de +1 para madeira (o segundo tipo de recurso).

O bônus vai para o dono da unidade.
O bônus não acumula: apenas o maior bônus se aplica para cada tipo de recurso.

damage_vs
==========

Nota: desde o SoundRTS 1.4, o sistema único ``damage`` / ``armor`` foi substituído pelo
sistema separado corpo a corpo/à distância (``mdg`` / ``rdg`` / ``mdf`` / ``rdf`` ...). Veja `Sistema de combate
(desde 1.4)`_ abaixo. A documentação legada de ``damage_vs`` é mantida para mods antigos.

(dano versus tipos específicos de unidade)

``damage_vs [<lista de nomes de tipo> <dano>] ...``

Define um dano específico contra alguns tipos de unidade.
O valor padrão é definido em unit.damage.

Exemplo de um tipo de piqueiro que seria mais eficiente contra um cavaleiro
 e menos eficiente contra um footman ou um camponês:

``damage 2 ; dano padrão``

``damage_vs knight 7 footman peasant 1``

ability
>>>>>>>

Nota: desde o SoundRTS 1.4, habilidades foram unificadas em ``class skill`` (veja `Habilidades (class
skill)`_ abaixo). As propriedades ``effect`` documentadas aqui ainda se aplicam a habilidades e a
definições ``class effect``.

effect
=======

``effect <tipo de efeito> [parâmetros]``

Valor padrão: (nenhum)

Um efeito é uma propriedade de uma habilidade. Quando uma habilidade é usada por uma unidade, o efeito ocorre, a menos que nenhum tipo de efeito tenha sido mencionado.

Propriedades adicionais podem modificar um efeito: effect_target_ e effect_range_.

apply_bonus
^^^^^^^^^^^^

``effect apply_bonus <nome da propriedade>``

Aumenta a propriedade das unidades afetadas. O valor é definido na propriedade da unidade chamada ``<nome da propriedade>_bonus``.
Por exemplo, ``effect apply_bonus damage`` procurará uma propriedade chamada ``damage_bonus`` na definição de cada unidade afetada.
Assim, unidades que se beneficiam do mesmo upgrade podem ter valores de bônus diferentes.

bonus
^^^^^^

``effect bonus <nome da propriedade> <valor>``

Aumenta em valor indicado a propriedade das unidades afetadas.

Coloque os filtros de unidade na linha seguinte como `effect_bonus_targets` (não na mesma linha que `effect bonus`)::

    effect bonus mdg_range 1
    effect_bonus_targets mangonel onager
    effect bonus rdg_range 1
    effect_bonus_targets scorpion trebuchet -petard

`effect_bonus_targets` aplica-se ao `effect bonus` precedente (as unidades ainda precisam de `can_use_tech`). Um `-` inicial exclui uma correspondência (igual a `phase_bonus_targets`), ex.: `effect_bonus_targets soldier -building`. O alias `effect_targets` é aceito.

Pelo menos as seguintes propriedades devem funcionar: damage, armor, range, heal_level, speed, hp_max, hp.

- ``effect bonus hp_max N`` / ``hp_max N%``: só aumenta o máximo; o HP atual não muda.
- ``effect bonus hp N`` / ``hp N%``: aumenta o HP atual e o ``hp_max`` pela mesma quantidade. Use ``hp`` se a pesquisa também deve curar unidades vivas.
food_cost e food_provided provavelmente não funcionam corretamente.

`projectile_lead` é um flag de combate 0/1; conceda-o com `effect bonus projectile_lead 1` (veja *projectile_lead* acima). A UI de atributos omite o `+1` numérico deste flag.

info
^^^^^

`effect info <tts_id>…`

Texto apenas de exibição na tela de atributos de tecnologia/habilidade (sem mudança de stats em tempo de execução). Pode ser combinado com outros efeitos, ex.: Balística: `effect info` mais `effect bonus projectile_lead 1`.

conversion
^^^^^^^^^^^

``effect conversion`` (sem parâmetro)

Move o alvo para o exército do conjurador.

Se o alvo não for inimigo do conjurador, nada acontecerá.

Valores permitidos para as propriedades relacionadas:

* effect_target: ask
* effect_range: square, nearby, anywhere

TODO: adicionar um <limit> para que unidades em uma casa alvo sejam escolhidas (em vez de ter que mirar em uma unidade)

raise_dead
^^^^^^^^^^^

``effect raise_dead <tempo de vida (em segundos)> <tipos e quantidades de unidade>``

Cria as unidades necessárias na casa alvo a partir dos cadáveres na casa, na ordem da lista de unidades. Se não houver cadáveres suficientes, o final da lista não será criado. As unidades desaparecerão após <tempo de vida> segundos, a menos que <tempo de vida> seja 0.

Se não houver cadáver na casa alvo, a ordem não será executada.

Valores permitidos para as propriedades relacionadas:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

recall
^^^^^^^

``effect recall`` (sem parâmetro)

Similar à teletransportação. Teletransporta as unidades do jogador da casa alvo de volta à casa do conjurador. Edificações não são afetadas. Unidades aliadas também não.

Se não houver unidade na casa alvo, a ordem não será executada.

Valores permitidos para as propriedades relacionadas:

* effect_target: ask, random
* effect_range: nearby, anywhere

resurrection
^^^^^^^^^^^^^

``effect resurrection <limite>``

Ressuscita os cadáveres do exército do conjurador na casa alvo, com no máximo <limite> unidades ressuscitadas. Os cadáveres mais antigos são ressuscitados primeiro. Os pontos de vida são restaurados a um terço do máximo.

Se não houver cadáver de unidade do mesmo exército na casa alvo, a ordem não será executada.

Valores permitidos para as propriedades relacionadas:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

summon
^^^^^^^

``effect summon <tempo de vida (em segundos)> <tipos e quantidades de unidade>``

Cria as unidades necessárias na casa alvo e as adiciona ao exército do conjurador. As unidades invocadas desaparecerão após <tempo de vida> segundos, a menos que <tempo de vida> seja 0.

Atributos opcionais de habilidade para verificação de posicionamento (exemplo tumor de creep do StarCraft)::

    summon_requires_build_field creep
    summon_requires_marked_field 1

``summon_requires_marked_field 1`` exige uma casa de build-field marcada (não só live). Omita quando o campo live for suficiente (Queen spawn tumor).

deploy
^^^^^^^

``effect deploy \<tempo de vida (segundos)\> [\<contagem\>] \<tipo de efeito\>``

Coloca uma entidade ``class effect`` na casa alvo (dano em área, zona de cura, detector, etc.). Desaparece após a duração indicada. Diferente de ``effect summon``, serve apenas para definições ``class effect``; a tela de atributos mostra estatísticas de dano/cura em vez de "summon".

Exemplos::

    effect deploy 5 sc_nuclear_blast
    effect deploy 3 sc_psi_storm_fx

Contagem opcional (várias entidades de efeito na mesma casa)::

    effect deploy 5 2 greek_fire

Também suporta ``summon_requires_build_field`` / ``summon_requires_marked_field``.

Valores permitidos para as propriedades relacionadas:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

harm_target (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dano em alvo único. Duas formas:

* **Dano verdadeiro fixo** (ignora armadura): ``effect harm_target <valor>``
* **Pipeline de combate** (armadura, crítico, splash, etc.): ``effect harm_target mdg`` ou ``effect harm_target rdg``

Estatísticas de combate não nulas na habilidade substituem as do conjurador. Veja ``skill_lipi`` / ``skill_lipi_mdg`` em ``mods/wuxia/rules.txt``.

Use ``harm_target_type`` para filtrar alvos (apenas inimigos por padrão). Veja `Guia de habilidades <skills-and-effects.htm>`_.

harm_area (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Dano em área:

* **Dano verdadeiro fixo**: ``effect harm_area <dano> <raio>``
* **Pipeline de combate**: ``effect harm_area mdg <raio>`` ou ``effect harm_area rdg <raio>``

O raio pode ser omitido (usa ``effect_radius`` da habilidade). Exemplos: ``skill_heng_sao``, ``skill_heng_sao_mdg`` (mod wuxia).

burst (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^^

Golpes combo de habilidade (**não** é o mesmo que rajadas burst de ``damage_seq`` de unidade; veja `burst-attacks.htm <../player/burst-attacks.htm>`_)::

    effect burst mdg <contagem> (interval <seg>) (window <seg>)
    effect burst rdg <contagem> (delays <t1> <t2> …)

O dano usa ``mdg`` / ``rdg`` da habilidade ou do conjurador. Exemplo: ``skill_jifengci`` (mod wuxia).

push (desde 1.4.4.6)
^^^^^^^^^^^^^^^^^^^^

``effect push <distância>`` — empurra um inimigo para trás e encontra uma casa transitável. Exemplo: ``skill_moli_dan`` (mod wuxia).

buffs / debuffs (via habilidades)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``effect buffs <buff> …`` / ``effect debuffs <debuff> …``

Aplica buffs ou debuffs ao alvo (``debuffs`` apenas em inimigos). Não existe ``effect reflect``; use ``reflect_percent`` no buff e aplique com ``effect buffs`` (wuxia ``b_douzhuan``).

Referência completa: `Guia de habilidades <skills-and-effects.htm>`_.

teleportation
^^^^^^^^^^^^^^

``effect teleportation`` (sem parâmetro)

Move as unidades do jogador na casa do conjurador para a casa alvo. Edificações não são afetadas. Unidades aliadas também não.
   
Se o destino for a mesma casa do conjurador, nada será feito.

Valores permitidos para as propriedades relacionadas:

* effect_target: ask, random
* effect_range: nearby, anywhere

effect_target
==============

``effect_target <método de seleção>``

Determina como o alvo será selecionado.

Valor padrão: self

Valores possíveis:

* self: o alvo será o conjurador (ou a localização do conjurador se o alvo deve ser um lugar)
* ask: a interface pedirá um alvo
* random: o jogo escolherá uma casa aleatória como alvo

effect_range
=============

``effect_range <distância>``

Determina a distância entre o conjurador e o alvo.

Valor padrão: 6

Valor especial: inf (infinito)

Se a distância atual for maior que a exigida, o conjurador tentará mover-se para um lugar mais próximo e usar a habilidade de lá.

effect_radius
==============

``effect_radius <distância>``

Determina o raio da área de efeito. O centro da área é o alvo.

Valor padrão: 6

Valor especial: inf (infinito)

Sistema de combate (desde 1.4)
------------------------------

Desde 1.4, o dano final é aditivo: ``final_mdg = mdg + mdg_vs`` (e o mesmo para
``rdg``, ``mdf``, ``rdf``). Quando o dano base é 0 e ``minimal_damage`` é 0 em
``def parameters``, a unidade não atacará.

Propriedades principais corpo a corpo/à distância:

- ``mdg`` / ``rdg``: dano base
- ``mdg_vs`` / ``rdg_vs``: bônus vs tipos específicos de unidade. Qualquer
  uma das formas serve (podem ser misturadas; **linhas repetidas são
  mescladas**, a posterior não sobrescreve)::

      mdg_vs building 150 siege_unit 40
      mdg_vs building 150
      mdg_vs siege_unit 40

  Outros atributos ``*_vs`` em pares (ex.: ``rdg_vs``, ``mdg_cover_vs``,
  ``menace_vs``) também aceitam vários pares numa linha e mesclam linhas
  repetidas.
- ``mdf`` / ``rdf``: defesa
- ``mdg_range`` / ``rdg_range``, ``mdg_cd`` / ``rdg_cd``, ``mdg_ready`` / ``rdg_ready``
- ``mdg_projectile`` / ``rdg_projectile``: flag de projétil (bônus de alcance em terreno elevado, regras terreno baixo vs alto)
- ``mdg_projectile_speed`` / ``rdg_projectile_speed``: velocidade de voo do projétil por via (casas/s; substitui delay / ``projectile_speed`` compartilhado)
- ``projectile_lead``: se projéteis à distância preveem alvos em movimento (0/1; costuma ser concedido por ``effect bonus`` de tecnologia)
- Ganchos do motor usados por tecnologias únicas estilo AoE2 (sem nomes de civ fixos): ``unpack_time`` / ``pack_time`` (veja *Empacotar / desempacotar* abaixo), ``gather_byproduct`` (ex.: Papel-moeda: ouro ao cortar madeira), ``kill_resource_vs`` (ex.: Chefes: o matador ganha um recurso escolhido se a vítima corresponder a um tipo; ``effect bonus kill_resource_vs peasant resource1 5``, via ``type_name`` / ``is_a``; recurso ``resourceN`` ou alias ``gold``/``wood``), ``reveal_map`` em upgrades (Circumnavegação explora o mapa inteiro)
- ``mdg_splash`` / ``rdg_splash``, ``mdg_radius`` / ``rdg_radius``, ``mdg_splash_decay``
- ``mdg_splash_vs`` / ``rdg_splash_vs``, ``mdg_splash_decay_min_vs`` / ``rdg_splash_decay_min_vs``: aplicam-se a **cada unidade atingida pelo splash** (não o alvo apontado nem o poço inteiro); ``mdg_splash`` base continua repartido ao acaso
- ``rdg_pierce_line`` / ``mdg_pierce_line``, ``*_pierce_width``, ``*_pierce_max``: penetração em linha (veja abaixo; estilo escorpião AoE2). Não é ``mdg_piercing``
- ``rdg_bounce`` / ``mdg_bounce``, ``*_bounce_range``, ``*_bounce_decay``: ricochete em inimigos próximos após um acerto (veja abaixo; estilo Mutalisk). Não é splash nem penetração em linha
- ``mdg_targets`` / ``rdg_targets``: ``ground``, ``air``, ``unit``, ``building``, ou um nome de tipo
- ``mdg_crit`` / ``rdg_crit``, ``mdg_crit_rate`` / ``rdg_crit_rate``, ``crit_vs``
- ``mdg_piercing`` / ``rdg_piercing`` (percentual de armadura ignorada; não é penetração em linha), ``piercing_vs``
- ``mdg_explode`` / ``rdg_explode``, ``exp_dgf``, ``exp_hp_cost``, ``mdg_explode_vs``
- Modificadores de **terreno do atacante** (desde 1.4.5.0): ``mdg_on_terrain`` / ``rdg_on_terrain``, ``mdg_cd_on_terrain`` / ``rdg_cd_on_terrain``, ``charge_mdg_terrain`` / ``charge_rdg_terrain``, ``charge_mdg_cd_on_terrain`` / ``charge_rdg_cd_on_terrain``; mesma sintaxe que ``speed_on_terrain`` — veja ``building-land-terrain.rst`` *Modificadores de combate de unidade em terreno*

Penetração em linha (por regras, estilo escorpião AoE2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Não é o mesmo que ``mdg_piercing`` / ``rdg_piercing`` (percentual de armadura ignorada): isto são **golpes extra na linha de tiro**.

O projétil percorre o segmento do atirador ao ponto de mira e aplica dano de novo a **inimigos** perto do segmento (sem o alvo principal). Se o primário falhar, a penetração continua. Não atinge aliados. Os golpes extra vão do mais perto ao mais longe; o dano é o ``rdg`` / ``mdg`` dessa vítima (com ``*_vs``).

- ``rdg_pierce_line`` / ``mdg_pierce_line``: 0/1, ativa penetração à distância / corpo a corpo com projétil
- ``rdg_pierce_width`` / ``mdg_pierce_width``: meia-largura (casas); omitido ou 0 = 0.5
- ``rdg_pierce_max`` / ``mdg_pierce_max``: teto de golpes extra; 0 = ilimitado
- ``rdg_pierce_decay`` / ``mdg_pierce_decay``: percentagem de dano extra após a armadura; 0 ou omitido = 100. Escorpião AoE2 usa 50

Exemplo (escorpião aoe2)::

    rdg_projectile 1
    rdg_pierce_line 1
    rdg_pierce_width 0.5
    rdg_pierce_decay 50

Ricochete (por regras, estilo Mutalisk de StarCraft)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Não é o mesmo que splash circular (``rdg_splash``) nem penetração em linha (``rdg_pierce_line``): depois do **acerto primário**, o tiro salta para outro inimigo próximo.

Cada salto escolhe o inimigo mais próximo ainda não atingido nesta cadeia e que corresponda a ``rdg_targets`` / ``mdg_targets``. Não fere aliados. Se o primário falhar, não há ricochete. O dano é o ``rdg`` / ``mdg`` dessa vítima (com ``*_vs``), reduzido a cada salto.

- ``rdg_bounce`` / ``mdg_bounce``: saltos extra; 0 ou omitido = desligado. Mutalisk usa 2 (três alvos no total)
- ``rdg_bounce_range`` / ``mdg_bounce_range``: distância máxima por salto (casas); omitido ou 0 usa ``rdg_range`` / ``mdg_range``
- ``rdg_bounce_decay`` / ``mdg_bounce_decay``: percentagem do salto anterior que permanece (arredondamento); omitido ou 0 = 33 (9→3→1)

Exemplo (mutalisk StarCraft)::

    rdg_projectile 1
    rdg_bounce 2
    rdg_bounce_range 3
    rdg_bounce_decay 33

Empacotar / desempacotar (modo cerco, por regras)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Estilo trabuco AoE2: qualquer unidade pode ativar em ``rules.txt`` (sem nomes de tipo fixos). Ordens da UI: ``pack`` / ``unpack``.

======= ================ ============================================================
Campo   Tipo             Significado
======= ================ ============================================================
``packable`` 0/1         Ativa o modo (precisa de um tempo positivo)
``unpack_time`` segundos Tempo para desempacotar (desdobrar e atirar); PRECISION ms
``pack_time`` segundos   Tempo para empacotar; se omitido, usa ``unpack_time``
``spawn_packed`` 0/1     Nasce empacotado (1, padrão) ou já desdobrado (0)
``packed_mdf`` / ``packed_rdf``  Armadura opcional enquanto empacotado
======= ================ ============================================================

Comportamento: empacotado = mover sem atacar; desempacotado = atacar sem mover.
Mover empacota sozinho; atacar desempacota sozinho. **Stop** cancela na hora.
Progresso: ``completeness,0..10`` → ``proportion_*`` (como o treinamento).

Menace automática / prioridade de alvo (desde 1.4.5.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

O ``menace`` de uma unidade não é mais só o dano. Quando rules não define um
valor absoluto, o motor usa uma **pontuação de combate multidimensional** para:

- Escolha automática de alvo (maior ameaça primeiro; jogadores computer que não
  são ``timers`` também podem misturar ``mdg_vs``/``rdg_vs`` com
  ``counter_skill`` — veja ``aimaking.rst``)
- Somas de ameaça inimiga por casa e decisões de IA relacionadas

**Dimensões** (arma principal = o maior de ``mdg`` / ``rdg``):

- Dano, acerto (``mdg_cover``/``rdg_cover``, 0 = 100%%), cooldown (``*_cd``),
  wind-up (``mdg_ready``/``rdg_ready`` — não o ``*_delay`` balístico)
- HP (``hp`` atual, senão ``hp_max``), armadura (``max(mdf, rdf)``), esquiva
  (``max(mdg_dodge, rdg_dodge)``)
- Alcance de ataque, velocidade de movimento

Em resumo: DPS efetivo (dano × acerto / (cd + ready)), depois sobrevivência e
fatores de alcance/velocidade.

**Overrides opcionais em rules** (defs de unidade):

======= ================= ============================================================
Campo     Tipo              Significado
======= ================= ============================================================
``menace`` absoluto         Ameaça fixa; **não** acompanha upgrades; substitui o auto
``menace_mult`` peso (1)    Multiplica a base multi-dim (ainda escala com stats)
``menace_vs`` absoluto vs   Ameaça fixa em relação a esse tipo de observador / ``is_a``
``menace_mult_vs`` peso vs  Base multi-dim × peso em relação a esse observador
======= ================= ============================================================

Ordem de busca (``menace_versus``): ``menace_vs`` → ``menace_mult_vs`` →
``menace`` / ``menace_mult`` / pontuação automática global.

Exemplo::

    def knight
    mdg 6
    menace_mult 1.5

    def archer
    rdg 5
    menace_vs knight 3
    menace_mult_vs mage 1.2

**Pesos ajustáveis** em ``def parameters`` (importância de armadura/esquiva/alcance/velocidade
e normalização de HP; dano+cd+ready+cover sempre alimentam o núcleo de DPS)::

    def parameters
    menace_armor_weight 1
    menace_dodge_weight 1
    menace_range_weight 0.15
    menace_speed_weight 0.2
    menace_hp_ref 50

Prefira ``menace_mult`` / ``menace_mult_vs`` para unidades que pesquisam upgrades;
use ``menace`` / ``menace_vs`` absolutos só quando quiser prioridade fixa.

Investida e contra-investida (desde 1.4.0.1)

Investida: unidades com estatísticas de investida podem executar um ataque de investida de alto dano ao engajar um
inimigo dentro do alcance. Após investir entram em cooldown e causam apenas ``mdg`` / ``rdg`` normais
até o cooldown terminar. Para investir o mesmo alvo de novo, afaste a unidade além de
``charge_mdg_dist`` / ``charge_rdg_dist`` após o cooldown expirar.

Dano de investida (aditivo, não multiplicador)::

    charge_damage = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)

Exemplo: ``mdg 6, charge_mdg 2`` → base ``6 + 2 = 8``, depois escalado pela distância dentro de
``charge_mdg_dist`` (cerca de 50% em corpo a corpo, até ~100% no alcance máximo). À distância usa ``rdg`` /
``charge_rdg`` da mesma forma.

Propriedades de investida (pares corpo a corpo / à distância; troque ``mdg`` ↔ ``rdg`` para à distância):

- ``charge_mdg`` / ``charge_rdg`` — dano extra de investida (somado)
- ``charge_mdg_vs`` / ``charge_rdg_vs`` — bônus vs tipos específicos de unidade
- ``charge_mdg_cd`` / ``charge_rdg_cd`` — cooldown (ms)
- ``charge_mdg_dist`` / ``charge_rdg_dist`` — alcance máximo de investida
- ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` — alcance mínimo para disparar (0 = sem limite)
- ``charge_mdg_splash`` / ``charge_rdg_splash`` — dano splash
- ``charge_mdg_radius`` / ``charge_rdg_radius`` — raio splash
- ``charge_mdg_splash_decay_min`` / ``charge_rdg_splash_decay_min`` — queda mínima de splash (0,0–1,0)

Exemplo (cavaleiro de campanha)::

    def knight
    mdg 3
    charge_mdg 2
    charge_mdg_cd 10
    charge_mdg_dist 15
    charge_mdg_min_dist 3
    charge_mdg_splash 1
    charge_mdg_radius 1
    charge_mdg_splash_decay_min 0.5

Contra-investida: contraria uma investida recebida. Quando uma unidade de contra-investida bloqueia um
atacante investindo dentro do alcance, a investida do atacante é interrompida (aquele golpe resolve como ataque
normal) e o atacante recebe dano de contra-investida.

Dano de contra-investida (aditivo)::

    counter = attacker (mdg/rdg + mdg_vs/rdg_vs) + attacker (charge_mdg/charge_rdg + charge_mdg_vs/charge_rdg_vs)
            + self (op_charge_mdg/op_charge_rdg + op_charge_mdg_vs/op_charge_rdg_vs)

Propriedades de contra-investida:

- ``op_charge_mdg`` / ``op_charge_rdg`` — dano extra de contra (somado)
- ``op_charge_mdg_vs`` / ``op_charge_rdg_vs`` — bônus vs tipos de atacante
- ``op_charge_mdg_cd`` / ``op_charge_rdg_cd`` — cooldown
- ``op_charge_mdg_dist`` / ``op_charge_rdg_dist`` — alcance efetivo (0 = ilimitado)

``Sons (``style.txt``)``: ``charge_success``, ``charge_failed``, ``op_charge``. Também
``critical_hit``, ``piercing_triggered`` para feedback de combate.

Notas: auto-ataques não disparam investida; splash de investida terrestre não atinge unidades aéreas.

Rajada / sequência de ataques (``damage_seq``, desde 1.3.8.2, aprimorado em 1.4.3.6)
-------------------------------------------------------------------------------------

Um ciclo de ataque pode disparar vários golpes em rápida sucessão (estilo Chu Ko Nu do Age of Empires).
Defina ``mdg`` / ``rdg`` base primeiro, depois ``damage_seq``:

``damage_seq mdg|rdg \<vezes\> [(damage d1 d2 ...)] [(secondary pierce melee)] [(interval segundos)]``

- Divisão explícita: ``(damage 6 3 3)`` — valores inteiros dos segmentos devem somar o dano
  base (mesmas unidades que ``mdg`` / ``rdg`` em rules.txt)
- Divisão automática (desde 1.4.3.6): omita ``(damage ...)`` para dividir o dano base igualmente entre
  ``vezes`` (funciona com dano fracionário, ex.: ``rdg 7.5`` com ``vezes 3`` → 2,5 por tiro)
- **Projéteis secundários (Chu Ko Nu de AoE2)**: ``(secondary 3 0)`` — o primeiro tiro = ataque
  ao vivo da unidade (upgrades aplicam) mais melee fixo; tiros seguintes = pierce + melee fixos
  (**não** aprimorados por ferreiro/química). O melee pode ser ``0`` (ainda causa dano a armadura
  melee negativa como aríetes). A soma **não** precisa igualar o dano base neste modo.
- Intervalo: ``(interval 0.25)`` segundos entre tiros; se omitido ou 0 com ``vezes \> 1``,
  padrão 0,25 s
- Limite: no máximo 6 tiros por ataque
- Rolagens de acerto: cada segmento rola acerto, crítico e debuff separadamente; tiros
  secundários acertam 100%
- Cooldown: ``mdg_cd`` / ``rdg_cd`` começa após a rajada completa terminar
  (próxima salva = ``(vezes-1)×interval + cd``, depois ``ready``)
- Sons: cada tiro dispara ``launch_mdg`` / ``launch_rdg``; liste vários IDs de som
  em ``style.txt`` (ex.: ``launch_rdg 1042 1042 1042``)

Exemplo de rajada à distância (``repeating_crossbowman`` embutido)::

    def repeating_crossbowman
    rdg 6
    rdg_cd 2.5
    rdg_range 4
    rdg_projectile 1
    damage_seq rdg 3 (interval 0.25)

Chu Ko Nu do AoE2 DE (``mods/aoe2``; o elite usa 5 flechas)::

    def chu_ko_nu
    rdg 8
    rdg_cd 2.77
    rdg_ready 0.23
    damage_seq rdg 3 (secondary 3 0) (interval 0.23)

Exemplo corpo a corpo com divisão explícita de dano::

    def footman
    mdg 12
    mdg_cd 1.5
    mdg_range 6
    damage_seq mdg 3 (damage 6 3 3) (interval 0.2)

Veja também ``../player/burst-attacks.htm``.

Armas e armadura (desde 1.4.1.3)
---------------------------------

Armas (``class weapon``) e armadura (``class armor``) guardam estatísticas de combate. Unidades referenciam
elas::

    def footman
    class soldier
    weapons sword bow     ; primeira arma é padrão / principal
    auto_weapon_switch 1  ; 1 = troca automática por alcance em combate
    armor light_armor

Jogadores trocam armas com A / Shift+A ou B depois X. Troca manual substitui a automática.
Estatísticas na unidade e no equipamento somam. Armas suportam herança como
unidades.

Buffs e debuffs (desde 1.3.9.8, estendido em 1.4.1.7)
------------------------------------------------------

Anexe a ataques com ``buffs`` / ``debuffs``, ou via habilidades com ``effect buffs`` /
``effect debuffs``.

``reflect_percent`` (percentual inteiro) em um buff habilita reflexão de dano; aplique com
``effect buffs``. Não existe ``effect reflect``. Exemplo: ``b_douzhuan`` em ``mods/wuxia/rules.txt``.

Exemplo de buff multi-atributo::

    def HealEnhancementBuff
    class buff
    stat heal_level heal_cd heal_radius
    v 1 1500 6
    duration 300
    temporary 1

Modos de gatilho:

1. Padrão — ao acertar
2. :strong:```is_active 1`` — ao iniciar um ataque (ativo)
3. :strong:```is_passive 1`` — ao receber dano (passivo), com ``trigger_condition`` (ex.
   ``hp \< 20``) e ``passive_trigger_rate``

Taxas de gatilho (percentual; padrão recorre às taxas normais de ataque):

- ``mdg_trigger_rate`` / ``rdg_trigger_rate`` — dano normal
- ``charge_mdg_trigger_rate`` / ``charge_rdg_trigger_rate`` — dano de investida
- ``op_charge_mdg_trigger_rate`` / ``op_charge_rdg_trigger_rate`` — contra-investida

Habilidades (class skill)
--------------------------

Defina habilidades com ``class skill`` em vez de ``class ability``::

    def fireball
    class skill
    mana_cost 50
    cost 10 0
    time_cost 30
    effect harm_target 60
    effect_target ask
    effect_range 12
    cooldown 10

``can_use_tech`` aplica-se a upgrades; ``can_use_skill`` aplica-se a habilidades.

Desde 1.4.4.6: ``harm_target``, ``harm_area``, ``burst``, ``push``, ``effect buffs`` / ``debuffs``, etc. Mod demo: ``mods/wuxia/rules.txt``. Veja `Guia de habilidades <skills-and-effects.htm>`_.

**Gatilhos de habilidade (desde 1.4.4.6)**

Habilidades aprendidas ficam em ``can_use_skill``. Manual e automático podem coexistir (``manual_use 1`` + ``auto_trigger 1``).

+--------------------+------------------------------------------------+
| ``manual_use 1``   | Mostrar no menu de comandos (padrão 1)          |
+--------------------+------------------------------------------------+
| ``auto_trigger 1`` | Disparar automaticamente em combate              |
+--------------------+------------------------------------------------+
| ``trigger_timing`` | Quando disparar automaticamente (veja tabela)    |
+--------------------+------------------------------------------------+

+-------------------------+----------------------------------------------+---------------------------+
| ``trigger_timing``      | Quando                                       | Lista legada              |
+=========================+==============================================+===========================+
| ``on_hit`` (padrão)     | Após acertar um inimigo                        | ``active_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack``           | No início do ataque; ataque normal continua  | ``attack_trigger_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_attack_replace``   | No início do ataque; substitui este ataque   | ``attack_replace_skills`` |
+-------------------------+----------------------------------------------+---------------------------+
| ``on_damaged``          | Ao ser atingido por inimigo (passivo)        | ``passive_trigger_skills``|
+-------------------------+----------------------------------------------+---------------------------+

Taxas: ``active_trigger_rate`` / ``passive_trigger_rate`` (1–100); opcional ``mdg_trigger_rate`` / ``rdg_trigger_rate`` substituem a taxa ativa para corpo a corpo/à distância.

Condições: ``trigger_condition hp < 30`` (``hp``/``mana`` comparados como percentual) ou ``hp_threshold 30``. Verificadas apenas para ``on_hit`` e ``on_damaged``, não para ``on_attack`` / ``on_attack_replace``.

Gatilhos automáticos consomem mana e respeitam cooldown; preparação ``ready`` aplica-se como em lançamentos manuais.

Exemplo (passivo ao receber golpe)::

    def skill_thorns
    class skill
    auto_trigger 1
    manual_use 0
    trigger_timing on_damaged
    passive_trigger_rate 30
    effect harm_target 10
    effect_target ask

Referência completa: `Guia de habilidades <skills-and-effects.htm>`_ (seção sobre modos de gatilho).

Efeitos (class effect, desde 1.4.1.7)
--------------------------------------

Dano e cura foram divididos em parâmetros detalhados::

    def exorcism
    class effect
    harm_level 2
    harm_cd 7.5
    harm_radius 6
    harm_target_type undead
    debuffs b_slow

Similarmente: ``heal_level``, ``heal_cd``, ``heal_radius``, ``heal_target_type``;
``hp_regen_cd``, ``mana_regen_ready``, etc.

Sistema de fases (desde 1.4.2.4)
---------------------------------

``class phase`` avança eras do jogo sem fazer upgrade da base::

    def dark_age
    class phase
    cost 0 0
    time_cost 0

    def feudal_age
    class phase
    cost 10 15
    time_cost 130
    phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
    units_auto_upgrade 0
    phase_targets soldier

``phase_targets`` opcional limita quais unidades recebem entradas não-custo de ``phase bonus`` (bônus de tipo cost sempre se aplicam no nível do jogador). Deixe vazio para todas as unidades. Use nomes de categoria (``soldier``, ``worker``, ``building``, ``unit``, etc.), nomes específicos de unidade (``footman knight``), ou qualquer nome na cadeia ``is_a``; qualquer correspondência positiva conta. Um ``-`` inicial exclui uma correspondência — ex.: ``phase_targets -building`` significa toda unidade exceto edificações; pode misturar inclusões e exclusões, ex.: ``phase_targets soldier -footman``.


Recompensas de era da facção (desde 1.4.6.9): `on_phase`, `research_cost_discount`, `advance_cost_discount` — sem nomes de civ no motor. Também `phase bonus clear`, `no_auto_upgrade 1`.

Em uma edificação::

    can_advance feudal_age

Use ``can_advance`` (não ``can_research``) para fases. Pressione V na edificação para ver a
fase atual.

``hide_locked_commands 1`` em ``def parameters`` oculta comandos cujos requisitos ainda não foram
atendidos.

Além de nomes de tipo simples (todos devem ser possuídos — AND), ``requirements`` pode pedir
quaisquer N prédios de um grupo nomeado (desde 1.4.5.8)::

    def stables
    class building
    requirements castle_age

    def imperial_age
    class phase
    requirements castle_age any_buildings 2 castle_age_buildings

    def castle
    class building
    requirements any_buildings 2 castle_age_buildings

``any_buildings <n> <group>_buildings`` remove ``_buildings`` e coleta prédios cujo
``requirements`` simples lista essa chave. Use ``castle_age_buildings``, não o nome nu
da fase. O token de grupo não dispara ``units_auto_upgrade``.

Economia (desde 1.4.0.x)
-------------------------

``population_cost`` substituiu ``food_cost``. Edificações podem produzir ou armazenar recursos::

    auto_production 1       ; produção automática (gás, etc.); reinicia enquanto não cheio
    manual_production 1     ; produção iniciada pelo jogador
    auto_cultivate 1        ; fazendas; reinicia só quando o armazém está vazio
    is_gather 1             ; saída vai para armazém da edificação; trabalhadores levam à base
    resource_volume_max 8
    resource_volume_start 0
    production_type resource2
    production_time 18      ; segundos para encher um lote
    production_qty 8        ; quantidade por ciclo de produção (no armazém da edificação)
    extraction_time 2       ; tempo de colheita do trabalhador na edificação (segundos)
    extraction_qty 8        ; quantidade por viagem do trabalhador

Sem ``is_gather``, produção automática e manual creditam a saída de ``production_type`` direto no estoque do jogador (ex.: ``gold_house``)::

    auto_production 1
    manual_production 1
    production_type resource1
    production_time 100
    production_qty 200

Para loot coletável, use ``production_item`` (em vez de ``production_type``)::

    production_item gold_pile
    production_qty 1

| Atributo | Função |
| --- | --- |
| ``production_type`` | Recurso produzido (com ``production_time`` e ``production_qty`` define capacidade de produção) |
| ``production_time`` | Segundos por ciclo de produção |
| ``production_qty`` | Saída por ciclo; sem ``is_gather``, adicionado aos recursos do jogador; com ``is_gather``, a ``resource_qty`` da edificação |
| ``auto_production`` | Quando ``1``, mostra produção automática; repete após cada ciclo; use para buffers (ex.: gold house). Gás SC usa viagens de trabalhadores (veja Depósitos e gás); não confundir com ``auto_cultivate`` de fazendas |
| ``manual_production`` | Quando ``1``, mostra produção manual; um ciclo por clique; independente de ``auto_production`` |
| ``auto_cultivate`` | Cultivo automático em edificações ``is_gather`` (ex.: fazendas); paralelo a ``auto_production`` |
| ``manual_cultivate`` | Cultivo manual; paralelo a ``manual_production``; defina ``1`` explicitamente quando necessário |
| ``production_item`` | Nome do tipo de item; gera itens coletáveis ao lado da edificação ao concluir |
| ``is_gather`` | Saída fica na edificação até um trabalhador com ``can_gather_building`` levar a um armazém |
| ``resource_volume_max`` | Máximo armazenado na edificação (ex.: 8 vespene) |
| ``resource_volume_start`` | Quantidade inicial ao construir (``0`` = vazio) |
| ``extraction_time`` / ``extraction_qty`` | Tempo de colheita e quantidade por viagem do trabalhador na edificação ou depósito |


Modos de coleta (desde 1.4.6.9)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Há dois mecanismos de coleta disponíveis para mods:

1. **``trip`` (padrão):** um pulso ``gather_qty`` (mais ``extraction_*``), depois entrega — viagens estilo StarCraft.
2. **``continuous``:** preenche ``carry_capacity`` a uma taxa por segundo, depois entrega — estilo Age of Empires II/IV.

::

    def parameters
    gather_mode continuous

    def peasant
    class worker
    gather_mode continuous
    carry_capacity 10
    carry_capacity_food_carcass 35
    gather_rate wood 0.39
    gather_rate goldmine 0.38

| Propriedade | Significado |
| --- | --- |
| ``gather_mode`` | ``trip`` (padrão) ou ``continuous``; em ``parameters`` e/ou no trabalhador |
| ``carry_capacity`` | limite de carga continuous; ``0`` volta a um ``gather_qty`` |
| ``carry_capacity_<type>`` | sobrescrita por depósito/edificação |
| ``gather_rate`` / ``gather_rate_<type>`` | continuous recursos/s; senão ``qty/time`` |

Use ``effect bonus carry_capacity N`` para upgrades estilo carrinho de mão. Bônus percentuais ``gather_time_*`` aumentam a taxa continuous efetiva. As chaves batem com o ``type_name`` do depósito (ex.: ``gather_time_food_livestock`` vs ``gather_time_food_carcass``), para separar bônus de pastores e caçadores sem hardcode de civ.

Sistema de mercado (desde 1.4.6.9)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compra/venda, tributo e comércio de rota são guiados por regras — **sem** nomes de recurso fixos nem payout só em ouro. Tabelas completas: `Sistema de mercado <market-system.htm>`_.

Destaques:

- ``def parameters``: ``market_currency``, ``market_commodities``, ``market_menu_labels``, chaves de imposto/tributo/distância de comércio.
- Edificações: ``is_market 1``. Unidades de comércio: ``is_trade_unit 1``, ``trade_hubs``, ``trade_rewards`` (um ou mais).
- Ordens: ``market_buy`` / ``market_sell`` / ``tribute`` / ``trade``.
- Exemplo: ``mods/aoe2/rules.txt``; notas para jogadores: `mercado e comércio <../player/market-and-trade.htm>`_.


.. note::

   ``auto_production`` e ``manual_production`` são flags separadas e ambas podem ser ``1`` (ex.: ``gold_house``). ``auto_production`` ausente ou ``0`` não implica modo manual; defina ``manual_production 1`` para o comando manual. O mesmo vale para ``auto_cultivate`` / ``manual_cultivate`` em fazendas.

.. note::

   ``is_create`` está obsoleto: pilhas terrestres ``class resource`` não são mais geradas. Use ``production_type`` (estoque direto), ``is_gather`` (armazém na edificação) ou ``production_item`` (gerar itens).

``class resource`` é separado de ``class deposit``. Depósitos no mapa::

    mineral_field 1500 a1
    geyser 1 e1

Estruturas de gás devem ficar no depósito correspondente::

    requires_deposit geyser
    is_buildable_anywhere 0

Veja ``sc_gas_building`` / ``assimilator`` em ``mods/starcraft/rules.txt``. Guia do jogador:
``../player/starcraft-resources.htm``. A tela de atributos (V) adiciona requires deposit;
production time/qty usam as entradas de atributo de produção existentes.

Heróis (desde 1.4)
-------------------

Defina unidades herói em qualquer ``rules.txt`` (regras base, mods, packs de campanha, packs de mapa multijogador). Funcionam em escaramuça, mapas aleatórios, multijogador e campanhas: XP por abates, nivelamento ``xp_thresholds``, revives ``is_revivable``, inventário, etc. Save entre capítulos (``campaign_carryover`` na próxima seção) é recurso extra apenas para campanhas single-player.

Exemplo multijogador: ``hero`` / ``hero_knight`` em ``res/multi/td2/rules.txt``.

::

    def hero
    class soldier
    global_count_limit 1
    is_revivable 1
    revival_time 10
    xp_thresholds 200 500 900
    hp_max_per_level 1000
    mdg_per_level 100
    resource_rewards 300
    xp_reward 100

``Nível e XP (``level`` / ``xp`` / ``xp_thresholds`` / ``xp_threshold_growth``)``

| Campo | Padrão | Significado |
| --- | --- | --- |
| ``xp_thresholds`` | (vazio) | Portões cumulativos de XP. O primeiro valor é o XP total para nível 2 (ou nível 1 ao começar no nível 0); cada valor seguinte é o próximo nível. |
| ``max_level`` | (nenhum) | Teto de nível do herói. Com ``xp_threshold_growth``, o carregamento de rules gera ``max_level - 1`` limiares automaticamente |
| ``xp_threshold_growth`` | (nenhum) | Gera ``xp_thresholds`` automaticamente por fórmula (tabela abaixo). Exige ``max_level``; use isto ou uma lista explícita ``xp_thresholds`` (lista explícita prevalece) |
| ``level`` | ``1`` | Nível inicial. Quando ``\> 1`` com ``xp_thresholds``, bônus cumulativos ``*_per_level`` e ``level_skills`` são aplicados ao spawn. |
| ``xp`` | ``0`` | XP cumulativo inicial opcional. |
| ``level_up_heal_full`` | ``0`` | ``1`` = restaura HP e mana completos a cada subida de nível; ``0`` = adiciona apenas o incremento ``hp_max_per_level`` / ``mana_max_per_level`` aos valores atuais (padrão). |
| ``level_up_reset_xp`` | ``0`` | ``1`` = zera XP atual após cada subida de nível; ``0`` = mantém XP cumulativo (padrão). Quando ``1``, prefira ``xp_thresholds`` por nível (XP desde a última subida), não totais cumulativos. |

- Nível máximo = ``len(xp_thresholds) + 1`` (ex.: nove limiares → teto nível 10).
- Status da unidade (Tab): heróis com ``xp_thresholds`` sempre anunciam nível (incluindo 0 e 1). XP é mostrado como ``atual / próximo portão`` (no nível 0 o próximo portão é ``xp_thresholds[0]``).
- ``xp_thresholds`` (ou ``xp_threshold_growth`` após expansão) sozinho → nível padrão 1 no início do jogo; ``level 0`` começa abaixo do nível 1.

:strong:```xp_threshold_growth`` tipos de curva`` (índice de limiar ``i`` começa em 0 para nível 2, 3, …)

| Tipo | Sintaxe | Fórmula |
| --- | --- | --- |
| linear | ``linear BASE STEP`` | ``BASE + STEP × i`` |
| quadratic | ``quadratic BASE A B`` | ``BASE + A×i + B×i²`` |
| polynomial | ``polynomial c0 c1 c2 …`` | ``c0 + c1×i + c2×i² + …`` |
| geometric | ``geometric FIRST RATIO`` | ``FIRST × RATIO^i`` (``RATIO`` pode ser fracionário, ex.: ``1.08``) |

Exemplo (herói 100 níveis, XP cumulativo linear)::

    def long_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50
    hp_max_per_level 30
    mdg_per_level 2

Exemplo (curva quadrática estilo Raynor, igual a ``40 90 160 250 …``)::

    def raynor_curve
    class soldier
    max_level 10
    xp_threshold_growth quadratic 40 40 10
    hp_max_per_level 30

Exemplo (def filha sobrescreve só o teto de nível; herda ``xp_threshold_growth`` do pai)::

    def base_hero
    class soldier
    max_level 100
    xp_threshold_growth linear 100 50

    def short_campaign_hero
    is_a base_hero
    max_level 20

Exemplo (início nível 0, lista explícita de limiares)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160 250 360 490 640 810 1000
    hp_max_per_level 30
    mdg_per_level 2
    level 0

Exemplo (cura completa ao subir de nível)::

    def raynor
    is_a footman
    xp_thresholds 40 90 160
    hp_max_per_level 30
    level_up_heal_full 1

Exemplo (início nível 3 com XP inicial)::

    def veteran_hero
    is_a knight
    xp_thresholds 200 500 900
    hp_max_per_level 20
    level 3
    xp 500

Carryover de herói de campanha (orientado por rules)
-----------------------------------------------------

Adicione ``campaign_carryover 1`` em uma def de herói da seção anterior. Apenas campanhas single-player: na vitória, o progresso é salvo em ``user/campaigns.ini`` e restaurado no próximo capítulo (tentativa após derrota não sobrescreve). Co-op não persiste heróis.

::

    def my_hero
    is_a knight
    campaign_carryover 1
    campaign_carryover_stats 1
    campaign_carryover_inventory 1
    inventory_capacity 8

| Campo | Padrão | Significado |
| --- | --- | --- |
| ``campaign_carryover`` | ``0`` | ``1`` = habilita save entre capítulos |
| ``campaign_carryover_id`` | nome da def | Chaves ``hero_\<id\>\_xp``, ``\_level``, ``\_inventory`` |
| ``campaign_carryover_stats`` | ``1`` | Nível + XP |
| ``campaign_carryover_inventory`` | ``1`` | Itens da mochila |

Só stats: ``campaign_carryover_inventory 0``. Só inventário: ``campaign_carryover_stats 0``. Sem carryover: omita ``campaign_carryover 1``.

Opcional em ``campaign.txt``: ``hero_min_level 13:2 16:3 …`` para níveis mínimos por capítulo.

Separado de ``campaign_flag`` / ``add_inventory_item`` (tokens de história, alianças). Veja `campaign/hero-carryover.htm <campaign/hero-carryover.htm>`_.

Contêineres de transporte (renomeação de campo desde 1.4.4.9; nomes legados ainda aceitos)
-----------------------------------------------------------------------------------------

Unidades ou edificações com ``transport_capacity`` funcionam como contêineres de transporte. Propriedades relacionadas:

| Propriedade | Efeito | Exemplo |
| --- | --- | --- |
| ``passenger_attack_types`` | Tipos de unidade que podem atacar de fora enquanto dentro | ``passenger_attack_types archer knight`` ou ``all`` |
| ``load_bonus`` | Por unidade carregada → stats somados ao **contêiner** | ``load_bonus speed 0.5 mdg 2`` |
| ``passenger_bonus`` | Stats somados ao **passageiro** enquanto dentro (revertidos ao descarregar) | ``passenger_bonus rdg_range 1 mdg 2`` |

Exemplo::

    def flyingmachine
    class soldier
    transport_capacity 8
    passenger_attack_types knight archer
    load_bonus speed 0.5
    passenger_bonus rdg_range 1

    def wall
    class building
    transport_capacity 4
    passenger_attack_types archer catapult
    passenger_bonus mdg 2

- Sem ``passenger_attack_types``, passageiros não podem atacar alvos externos por padrão.
- ``load_bonus`` e ``passenger_bonus`` podem ser combinados no mesmo contêiner.

Ocupação do quadrado (``space``, desde 1.4.5.8)
-----------------------------------------------

``space`` é uma propriedade precision (decimais permitidos). Indica quanto a unidade ocupa
na sua camada ar/terra/água. A capacidade é o ``square_width`` do mapa nas mesmas unidades.

| Ajuste | Efeito |
| --- | --- |
| ``space 0`` (padrão) | Não consome capacidade (ilimitado, legado) |
| ``space 1`` com ``square_width 12`` | Ocupa 1 do tamanho 12; no máximo 12 |
| ``space 0.5`` com ``square_width 12`` | No máximo 24 |
| ``space`` > ``square_width`` | A unidade não pode entrar nesse quadrado |

``square_width`` é o tamanho de cada quadrado (ex.: a1). ``space`` usa as mesmas unidades.
A capacidade é contada **por aliança** (cada lado até ``square_width``); ocupação inimiga
não usa o seu orçamento. Aliados compartilham um orçamento. Se o seu lado estiver cheio,
movimento e treinamento que spawnaria ali são recusados (voz ``not_enough_space``).
As camadas são independentes: ocupação terrestre não bloqueia unidades aéreas.

Exemplo::

    def peasant
    class worker
    space 1

    def siege_engine
    class soldier
    space 4

Veja também ``square_width`` em ``mod/mapmaking.rst``.

Itens (desde 1.4.1.3)
----------------------

::

    def magic_sword
    class item
    consume_on_pickup 0
    buffs power_buff
    resource_rewards resource1 50

``is_loot 1`` solta o item quando o portador morre.

``Sons de item (``style.txt``; use sounds desde 1.4.4.6)``

| Quando | ``style.txt`` do item | ``style.txt`` da unidade | Padrão global (``def thing``) |
| Coleta | ``on_pickup`` | ``pickup_\<tipo de item\>`` | ``pickup`` |
| Soltar | ``on_drop`` | ``drop_\<tipo de item\>`` | ``drop`` |
| Usar | ``use`` / ``on_use`` | ``use_\<tipo de item\>`` | ``item_used`` |

No item (``use`` e ``on_use`` são equivalentes; vários IDs são escolhidos aleatoriamente)::

    def zhuiri_jianfa_book
    title 7754
    pickup 1506
    use 1506

Na unidade::

    def raynor
    use_zhuiri_jianfa_book 1506

Fallback global::

    def thing
    item_used 1194 1195 1196

Herança (``is_a``) funciona como ``on_pickup`` / ``on_drop``: tipos derivados substituem pais.

Inventário e itens equipáveis (desde 1.4.3.1)
----------------------------------------------

Unidades precisam ``inventory_capacity`` > 0 para guardar itens. Cada item usa um slot (``transport_volume``
está definido, mas a capacidade atualmente conta itens, não volume).

Equipamento embutido (tradicional)::

    def footman
    weapons sword          ; class weapon — embutido, não na mochila
    armor footman_armor    ; class armor — embutido

Itens equipáveis (modelo unificado): o mesmo nome de tipo pode ser ``class item``::

    def sword
    class item
    equippable_as_weapon 1
    mdg 3.5
    mdg_range 1
    transport_volume 1

    def footman_armor
    class item
    equippable_as_armor 1
    mdf 0.5

Quando ``weapons`` / ``armor`` em uma unidade apontam para itens equipáveis, o motor cria instâncias
de item no spawn e as coloca no inventário. Se a unidade não tiver equipamento embutido daquele
tipo e ``spawn_weapons_equipped`` / ``spawn_armor_equipped`` for ``1`` (padrão), equipam-se silenciosamente::

    def footman
    inventory_capacity 2
    weapons sword
    armor footman_armor

Regras de troca de equipamento quando a unidade tem embutido e item (ex.:
``weapons bow sword`` com ``bow`` como ``class weapon`` e ``sword`` como item equipável):

- Equipamento embutido está sempre equipado no spawn; equipamento item vai para a mochila.
- Com ``spawn_weapons_equipped 1`` (padrão), armas item ficam na mochila e não podem
  ser equipadas; com ``spawn_weapons_equipped 0``, o jogador pode equipá-las manualmente.
- Equipamento embutido só troca com embutido; item só com item;
  sem troca cruzada entre os dois tipos. Mesmas regras para armadura
  (``spawn_armor_equipped``).

Exemplo arqueiro misto::

    def archer
    weapons bow sword
    spawn_weapons_equipped 1   ; arco equipado, espada na mochila, espada não equipável
    inventory_capacity 3

    def archer
    weapons bow sword
    spawn_weapons_equipped 0   ; arco equipado, espada na mochila, jogador pode equipar espada
    inventory_capacity 3

Consumíveis (só ``buffs``, sem ``equippable_as_*``) são usados da mochila com Enter,
não na tela de equipamento. Em sucesso, tocam sons ``use`` / ``on_use``; consumíveis normais
anunciam o título do item mais "used".

Livros de habilidade (aprendem permanentemente uma habilidade; consumidos no uso bem-sucedido)::

    def zhuiri_jianfa_book
    class item
    skills skill_zhuiri_jianfa
    learn_level 10
    transport_volume 1

- ``learn_level`` / ``learn_level_skills``: nível mínimo para aprender do livro (mais restritivo entre
  ``learn_level_skills`` da unidade e regras do item).
- ``level_skills`` da unidade: desbloqueio automático ao subir de nível (separado de livros; não duplique a mesma
  habilidade ou o uso retorna ``skill_already_known`` e mantém o livro).
- Com ``learn_level`` / ``learn_level_skills`` no item, coleta não concede a habilidade;
  o jogador deve usar o livro da mochila.
- Sucesso: som de uso + título TTS da habilidade + mensagem ``skill_learned``; falha: ``order_impossible``
  com ``skill_level_too_low`` / ``skill_already_known`` etc.

``Tesouro com ``use_square`` (recompensas só ao usar na mochila em uma casa nomeada)::

    def mystery_treasure
    class item
    use_square b2
    resource_rewards resource1 150

Ordens de servidor (também usáveis em ações ``order`` de gatilho): ``equip_weapon``, ``unequip_weapon``,
``equip_armor``, ``unequip_armor``, ``use_item``, ``drop``.

Comportamento padrão de unidade (desde 1.4.3.1)
------------------------------------------------

Comportamento inicial por unidade em ``rules.txt``:

- ``ai_mode``: ``offensive``, ``defensive``, ``guard`` ou ``chase``. Padrão: ``offensive``
  para soldados, ``defensive`` para trabalhadores. Aplica-se a unidades de combate.
  ``chase`` mantém um ``AttackAction`` e segue entre casas (sem ``go`` automático);
  ``offensive`` / ``guard`` ainda respeitam ``position_to_hold`` do spawn até uma ordem dar ``stop()``;
  ``defensive`` / ``chase`` não.
- ``auto_gather``: ``1`` ou ``0``. Padrão ``1``. Apenas trabalhadores.
- ``auto_repair``: ``1`` ou ``0``. Padrão ``1``. Apenas trabalhadores.
- ``auto_explore``: ``1`` ou ``0``. Padrão ``0``. Unidades móveis (speed > 0).
- ``can_auto_explore``: ``1`` ou ``0``. Padrão ``0``. Adiciona habilitar/desabilitar auto-exploração ao
  menu de comandos da unidade.
- ``no_number`` (desde 1.4.3.2): ``1`` ou ``0``. Padrão ``0`` (sempre fala números de série,
  ex.: "peasant 1 at a1"). Quando ``1``: omite o número enquanto existir apenas uma unidade viva daquele
  tipo ("Guan Yu at a1"); com duas ou mais, usa números ("Guan Yu 1", "Guan Yu 2").
  Resumos de grupo seguem a mesma regra. Para heróis ou líderes únicos.

``ai_mode patrol`` é inválido — patrulha exige comando de rota. Unidades neutras do computador ainda são
forçadas a guard + contra-ataque independentemente de ``ai_mode``.

Unidades do jogador em modo ``offensive``, ``defensive`` ou ``chase`` não atacam automaticamente unidades
neutras (``computer_only ... neutral``) e modo defensivo não foge só de neutros.
``go`` normal em neutro só move; ``attack`` normal em ``is_huntable`` causa dano.
Use ataque imperativo (ex.: Ctrl+clique) para a IA tratar creep/NPC neutro como alvo automático.

Exemplo::

    def knight
    class soldier
    ai_mode guard
    auto_explore 1
    can_auto_explore 1

    def peasant
    class worker
    auto_gather 1
    auto_repair 0
    ai_mode defensive

Captura / ordem padrão de ocupação
-----------------------------------

Alvo — ``capture_hp_threshold`` (em edificações/unidades capturáveis):

| Valor | Significado |
| --- | --- |
| ``0`` (padrão) | Não capturável via limiar de HP |
| ``100`` | Captura por contato: converte dono ao chegar, sem dano; ordem padrão de clique direito é captura (veja ``can_capture``) |
| ``30`` etc. | Capturável quando HP ≤ aquele percentual durante combate normal |

Atacante — ``can_capture`` (em soldados/trabalhadores com ataque):

| Valor | Significado |
| --- | --- |
| ``1`` (padrão) | Clique direito em inimigo com ``capture_hp_threshold 100`` → captura padrão; IA usa captura por contato |
| ``0`` | Mesmo alvo → ataque/movimento padrão; IA ataca normalmente |

Exige ``attack`` nas habilidades da unidade; alvo deve ser inimigo vivo e vulnerável.

Exemplo — só footmen capturam quartel; arqueiros atacam::

    def captured_barracks
    class building
    capture_hp_threshold 100
    ...

    def footman
    class soldier
    can_capture 1
    ...

    def archer
    class soldier
    can_capture 0
    ...

POI de mapa aleatório ``captured_barracks`` e jogo estilo HoMM: `../player/homm-civ5-play.htm <../player/homm-civ5-play.htm>`_.

Dar itens (give)
----------------

Ordem give — transferir um item do inventário para outra unidade::

    give <id da unidade alvo>
    give <id da unidade alvo> <tipo ou id do item>

Campos do alvo (todos devem passar):

- ``receive_items 1`` (padrão 0 — NPCs devem optar por participar)
- ``accepted_items`` — lista branca opcional de tipos de item (herança ``is_a`` suportada); vazio = qualquer
- ``accept_from`` — lista opcional: ``self``, ``ally``, ``neutral``, ``enemy``; vazio = qualquer

Exemplo NPC que aceita qualquer item de qualquer um::

    def quest_npc
    receive_items 1
    inventory_capacity 5

Exemplo: cavaleiros aliados aceitam só ``knight_lance`` de aliados::

    def knight
    receive_items 1
    accepted_items knight_lance
    accept_from ally

Entrega registra ``received_items`` no alvo para verificação de gatilho. Itens aplicam ``skills`` /
``buffs`` ao receber como ``pickup``. Entrega por script ignora ``inventory_capacity`` do alvo.
Demo multijogador: ``res/multi/give_demo.txt``. Demos de relação em campanha: ``The Legend of Raynor`` cap. 14–16
(``res/single/The Legend of Raynor/14.txt``, ``15.txt``, ``16.txt``).

Build fields, addons e decolagem (estilo StarCraft, ``mods/starcraft``)
-----------------------------------------------------------------------

O motor suporta build fields, modos de construção de trabalhador, addons Terran e
recombinação após decolagem. Implementação de referência: ``mods/starcraft/rules.txt``. Guias do jogador:

- Addons Terran: ``../player/starcraft-terran.htm``
- Creep Zerg e tumores da Queen: ``../player/starcraft-zerg-creep.htm``

Build fields (psi Protoss / creep Zerg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Função |
| --- | --- |
| ``provides_build_field \<name\>`` | Marca casas próximas (ex.: ``psi``, ``creep``) |
| ``requires_build_field \<name\>`` | Exige aquele field para posicionar/construir; ``0`` isenta o tipo (Nexus, Pylon, Assimilator; Photon Cannon **precisa** de psi) |
| ``build_field_radius \<tiles\>`` | Raio do provedor (passos BFS da casa principal; use isto ou ``build_field_radius_m``) |
| ``build_field_radius_m \<meters\>`` | Raio do provedor em metros (mesma escala que ``rdg_range``); distância euclidiana do provedor `` (x,y)`` |
| ``build_field_persists 1`` | Marcas permanecem após destruição do provedor (creep Zerg) |
| ``build_field_spreads 1`` | Espalha marcas para casas adjacentes a cada segundo |
| ``build_field_spread_squares N`` | Camadas por tick (padrão 1 quando ``build_field_spreads``) |
| ``requires_build_field_on_square 1`` | Casa inteira deve estar marcada (Zerg); senão field live em qualquer ponto da casa basta (Protoss) |
| ``loses_power_without_field 1`` | Desliga sem field live: parar build/train/power (Protoss) |

:strong:```build_field_radius`` vs ``build_field_radius_m``

Use uma propriedade de raio por provedor; deixe a outra em 0 (padrão).

| Propriedade | Como o alcance é medido | Uso típico |
| --- | --- | --- |
| ``build_field_radius`` | Passos BFS da casa principal do provedor (tiles discretos) | Creep legado baseado em tile |
| ``build_field_radius_m`` | Distância euclidiana do (x, y) do provedor em metros | Cadeias psi Protoss (estilo SC2); Hatchery / tumor de creep Zerg em ``mods/starcraft`` |

Uma casa do mapa tem cerca de 12 m de largura (``square_width 12``). Exemplos no mod StarCraft:
Nexus 18 m, Pylon 12 m, Hatchery 12 m, tumor de creep 4 m.

Field live vs marcado

- Field live — atualmente fornecido por edificações/unidades em pé (metros: ponto no círculo; tiles: BFS de ``place``).
- Field marcado — marcas persistentes de casa pintadas no registro e/ou espalhadas a cada segundo.

``has_build_field_on_square`` aceita live OU marcado. Zerg ``requires_build_field_on_square 1`` verifica só casas marcadas (não pode construir em creep live que ainda não espalhou/marcou).

Quando ``build_field_persists 1`` ou ``build_field_spreads 1`` está definido, provedores de raio em metros também pintam marcas no alcance (necessário para Hatchery só com ``build_field_radius_m`` ainda permitir construção Zerg).

Tumor de creep da Queen (``mods/starcraft``): habilidades summon colocam edificações ``creep_tumor`` em casas alvo. Atributos de habilidade:

| Atributo | Função |
| --- | --- |
| ``summon_requires_build_field \<name\>`` | Casa alvo deve ter aquele field (live ou marcado) |
| ``summon_requires_marked_field 1`` | Alvo deve estar marcado (Extend tumor; Queen Spawn omite isto) |

Guia do jogador: ``../player/starcraft-zerg-creep.htm``. Readme do mod: ``mods/starcraft/readme.txt``.

Protoss (``protoss_building``)::

    requires_build_field psi
    is_buildable_anywhere 1
    self_constructs 1
    loses_power_without_field 1

Zerg (``zerg_building``)::

    requires_build_field creep
    requires_build_field_on_square 1
    is_buildable_anywhere 1
    self_constructs 1

Hatchery: ``provides_build_field creep`` + ``build_field_radius_m 12`` + ``build_field_persists 1`` +
``build_field_spreads 1``. Queen Spawn tumor de creep / Extend tumor — veja ``../player/starcraft-zerg-creep.htm``.

UI: ``def build_field_\<name\>`` + ``title \<tts_id\>`` em ``ui/style.txt``; ``noise`` ambiente opcional.

Depósitos e gás (``requires_deposit`` / ``is_an_extractor``)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Função |
| --- | --- |
| ``requires_deposit \<type\>`` | Deve construir em depósito do mapa (ex.: ``geyser``); depósito é removido ao concluir |
| ``is_buildable_anywhere 0`` | Com ``requires_deposit``, bloqueia construção em building land |
| ``is_an_extractor 1`` | Ao concluir, copia a reserva do depósito para ``source_qty``; trabalhadores debitam ao coletar |
| ``deposit_volume N`` | Reserva padrão do depósito quando o mapa usa qty ``1`` |
| ``depleted_production_qty N`` | Rendimento por viagem após ``source_qty`` zerar (``0`` = parar; gás SC usa ``2``) |
| ``gather_slots N`` | Máximo de trabalhadores extraindo ao mesmo tempo; ``0`` = ilimitado. Gás SC usa ``3`` |

Template de gás ``sc_gas_building`` (estilo SC1) usa ``is_an_extractor`` + coleta por viagem (``auto_production 0``) + ``extraction_qty`` / ``depleted_production_qty`` + ``gather_slots 3``.
Trabalhadores precisam ``can_gather assimilator`` (tipo de edificação), não ``geyser`` (depósito). Dica: **3** trabalhadores por gás.

Modos de construção de trabalhador
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

| ``build_mode`` | Comportamento |
| --- | --- |
| ``assisted`` | Trabalhador fica até terminar (SCV Terran, padrão) |
| ``place_and_leave`` | Trabalhador coloca canteiro e sai; ``self_constructs 1`` termina a edificação (Probe) |
| ``sacrifice`` | Trabalhador é consumido (Drone) |

Também: ``self_constructs 1``, ``build_sacrifices_worker 1``, ``is_buildable_anywhere 1`` (sem slot ``class building_land`` separado em Protoss/Zerg/Terran voador).

Addons Terran
>>>>>>>>>>>>>

| Atributo | Função |
| --- | --- |
| ``can_have_addon \<types\>`` | Tipos hospedeiros (Barracks / Factory / Starport) |
| ``addon_max N`` | Máximo de addons anexados (padrão 1) |
| ``is_addon 1`` | Edificação addon (Tech Lab, Reactor) |
| ``addon_host_types \<hosts\>`` | Quais hospedeiros aceitam este addon |
| ``addon_grants_train_\<host\> \<unit\>`` | Opção extra de treino quando anexado |
| ``addon_grants_research \<tech\>`` | Pesquisa extra quando anexado |
| ``addon_train_multiplier N`` | Produção dupla do Reactor |
| ``addon_offset_x \<value\>`` | Deslocamento lateral a leste do hospedeiro (padrão 3,5 tiles) |

Construa addon em hospedeiro existente, não em terreno vazio.

Decolagem e recombinar
>>>>>>>>>>>>>>>>>>>>>>

| Atributo | Função |
| --- | --- |
| ``can_change_to \<flying\>`` | Hospedeiro terrestre pode decolar |
| ``ground_form \<ground\>`` | Forma voadora pousa como este tipo |
| ``change_time \<sec\>`` | Tempo de morph para ``change_to`` (sem custo de recurso/pop) |

Decolagem: addons se desprendem no chão; building land é restaurado sob o hospedeiro (**mesmo tipo que a edificação consumiu ao construir**; mapas StarCraft usam ``build_site``). Se a unidade não tiver referência salva, usa-se ``building_land`` do mapa ou única keyword ``nb_<type>_by_square``.

Pouso: consome o objeto ``class building_land`` mais próximo na casa (nomes de API como ``find_meadow_near_xy`` são históricos).

Recombinar: Tab Tech Lab → Backspace go (voa para slot de pouso a oeste do lab) → ``change_to`` terrestre.

Building land vs slot: building land = permissão de pouso; reanexar precisa alinhamento de slot
(``tech_lab.x ≈ factory.x + addon_offset_x``, dentro de ~2,5 tiles Manhattan).

Pousar no próprio patch de decolagem não reanexa. Pouso errado com addon órfão → TTS ``addon_reattach_failed`` (7350).

Mapas de teste: ``terran_addon_test``, ``terran_recombine_test``; campanha ``sc_build_tests`` cap. 3–4.

Reparo de navios (desde 1.4.1.1)
--------------------------------

``can_repair_ships 1`` em trabalhadores ou edificações. Trabalhadores reparam navios adjacentes na costa (6
casas); edificações reparam automaticamente navios na água vizinha (8 casas).

Construção de pontes na água (vãos por tile)
---------------------------------------------

Trabalhadores podem construir vãos ``is_buildable_on_water_only 1`` em água pura; ao concluir
aplica-se ``bridge_terrain`` (ex.: ``bridge_deck``). Canteiros usam TTS normal de
``buildingsite``; passos usam o ``ground`` do terreno final. Veja
`water-bridge-building.htm <water-bridge-building.htm>`_.

Pastoreio (trabalhadores)
-------------------------

``can_herd 1`` permite que um trabalhador pastoreie animais com ``herdable 1`` (por exemplo ovelhas). O
padrão é ``0``; habilite pastoreio explicitamente por tipo de trabalhador em ``rules.txt``.

:strong:```can_capture`` — ``1`` ou ``0``. Padrão ``1``. Em unidades com habilidades ``attack``: quando
``0``, clique direito em inimigos com ``capture_hp_threshold 100`` usa ataque/movimento normal em vez
da ordem de captura padrão; captura por contato da IA também é desabilitada. Veja Captura / ordem padrão de ocupação
acima.

Sistema de caça (estilo Age of Empires)

Veja ``../player/hunting.htm``. Resumo:

- Trabalhadores Backspace/clique direito em ``is_huntable`` atacam (ataque normal causa dano); abates geram ``food_deposit`` (ex.: ``food_carcass``, ou aoe2 ``food_livestock`` para ``herdable``) e completam a ordem sem bip falso ``order_impossible``.
- Atributos de animal: ``is_huntable``, ``flee_on_hit``, ``pursue_attacker``, ``herdable``, ``food_deposit``, ``food_deposit_qty``, ``no_number``.
- Spawn no mapa: ``computer_only 0 0 neutral \<square\> \<count\> deer``; mapas aleatórios adicionam fauna perto dos starts.
- Voz: unidades com ``is_huntable`` / ``herdable`` são anunciadas como "deer , animal", não "neutral , NPC". Ctrl+Shift+F4 para jogador só de fauna diz "you are animal". NPCs de história (``quest_npc``, etc.) ainda dizem "neutral , NPC".
- Diplomacia: slot ``computer_only`` só com fauna (``deer`` / ``sheep`` / ``tiger`` customizado, etc.) não entra na aliança ``"ai"`` nem se aliando a jogadores, creep hostil ou outros rebanhos; slots mistos inalterados. Veja ``../player/hunting.htm`` §3.1.
- Tech ``hunting_techniques``: colheita mais rápida de pomar/cadáver.
- Velocidade de pastores / caçadores separada: ``food_deposit`` distintos + ``gather_time_<depósito>`` (aoe2: britânicos ``food_livestock``, mongóis ``food_carcass``). Orientado a rules, sem hardcode de civ.
- ``pursue_attacker 1``: após contra-atacar, persegue entre casas (atrair javali ao centro no estilo AoE2). Cervos/ovelhas usam ``flee_on_hit``.
- ``pursue_leash_range N``: solta a agressão se a distância ao alvo passar de N mm (``0`` = sem limite). Javalis usam ``48000`` (~4 casas); depois esquecem e voltam à origem.
- ``claimable 1``: em neutro, qualquer unidade não neutra próxima o reivindica (ovelha AoE2). Independente de ``can_herd``.
- Pasto: ``spawns_unit``, ``larva_spawn_time``, ``larva_cap``, ``spawn_player_cap`` / ``spawn_immediate`` (aoe2 ``pasture`` mongol).

Exemplo de animal::

    def deer
    class soldier
    is_huntable 1
    flee_on_hit 1
    food_deposit food_carcass
    food_deposit_qty 35
    no_number 1
    ai_mode guard

Herança (desde 1.3.8.3)
-------------------------

::

    is_a footman                    ; todos os atributos
    is_a footman(hp_max mdg)        ; seletivo
    is_a footman(apart hp_max)      ; herança por exclusão (forma apart)
    is_a footman(-hp_max)           ; herança por exclusão (prefixo -, igual a apart)
    is_a footman(-hp_max -mdg)      ; excluir vários atributos
    is_a footman(mdg) knight(hp_max) ; vários pais

style
------

O estilo é definido em "ui/style.txt" e na versão localizada de "style.txt".

Sons de actividade e depósito (desde 1.4.8.1 / 1.4.8.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Os ciclos de recolher / construir / reparar ficam no **trabalhador**: ``noise_when_exploiting_*``, ``noise_when_building``, opcional ``noise_when_repairing``. O estéreo usa o depósito ou o edifício.

Depósito: ``store_resource1``, ``store_resource2``, … (alinhado com ``resource1``). **Não** use ``store_resource_0``. Pode ir no aldeão / barco de pesca **ou** no armazém; se ambos existirem, ganha o trabalhador. O estéreo toca no armazém.

Vista Ctrl+F2: ícones e animação (desde 1.4.6.1)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Com a tela ligada, mods podem fornecer arte opcional. Prioridade no mapa:
``ui/anims/<tipo>/`` → ``ui/map/<conjunto>/<tipo>.png`` → ``ui/map/<tipo>.png`` → formas geométricas.
Camadas posteriores cobrem PNG de mesmo nome. Formato: ``res/ui/anims/README.txt``.
Spine é opcional; se faltar, volta a spritesheet/ícones/formas. Código: ``game_unit_anim.py``.

Conjuntos de arquitetura (desde 1.4.8.3): ``ui/architecture.txt`` agrupa civs
(``def <conjunto>`` + ``factions …``). aoe2 usa conjuntos DE, não um miliciano por civ.
Depósitos e fauna neutros ficam no nível superior. RGB (``rim``, etc.) só para
``python tools/gen_aoe2_hud_icons.py``. Mods com tipos distintos por raça
(StarCraft: ``marine`` / ``zergling`` / ``zealot``) não precisam de subpastas.

shortcut
>>>>>>>>

Ordens simples, ordens de construção, ordens de treino, ordens que usam habilidade podem ser dadas com atalho, se um atalho estiver definido.

Para definir um atalho, defina a propriedade "shortcut" seguida da letra correspondente. A letra deve estar em minúsculas.

Se a ordem for simples, o atalho deve ser definido pela ordem (ex.: patrol).
Se a ordem for complexa (train, build, usar habilidade), o atalho deve ser definido pela segunda parte da ordem.
Por exemplo, defina atalho "m" para a habilidade meteor para que o mago tenha atalho "m" para lançar meteoros.

intro (desde 1.4.1.5)
>>>>>>>>>>>>>>>>>>>>>

Adicione descrição da unidade abaixo de ``title``::

    def footman
    title 87
    intro 1001

O texto deve existir em ``tts.txt``. Facções também podem definir ``intro``: no seletor pressione **G** para um submenu frase a frase (desde 1.4.7.2).

Sistema de som de combate (desde 1.3.8.2; 1.4.4.6 renomeou matk/ratk para mdg/rdg)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Substitui os sons de ataque antigos::

    launch_mdg / launch_rdg
    mdg_hit / rdg_hit / mdg_hit_vs / rdg_hit_vs
    mdg_missed / rdg_missed
    mdg_dodge / rdg_dodge
    launch_charge_mdg / launch_charge_rdg
    charge_mdg_hit / charge_rdg_hit
    casting
    disappear
    weapon_switched
    death / falling / falling_delay / falling_on_<terrain>
    move / move_on_<terrain>

**Gritos de batalha (reprodução em camadas desde 1.4.5.0; veja :doc:`battle-shouts`)**

- ``shouts`` — pool de gritos de combate; defina em ``def walking_unit`` para infantaria e arqueiros herdarem

**Passos em terreno e sons de queda (desde 1.3.9.1; nomes de tipo de terreno desde 1.4.5.0)**

Em ``def unit`` (ou unidade específica) em ``style.txt``:

- ``move`` — sons de passo padrão
- ``move_on_<key>`` — passos que dependem do terreno
- ``falling`` — som genérico de queda do corpo após morte
- ``falling_delay <segundos>`` — espera após ``death`` antes de ``falling``; omita ou ``0`` para tocar imediatamente
- ``falling_on_<key>`` — som de queda específico do terreno

Resolução de ``<key>`` (igual para ``move_on_`` e ``falling_on_``):

1. **Nome do tipo de terreno** — a def em ``rules.txt`` / ``style.txt`` na casa da unidade (ex.: ``ocean``, ``plain``, ``mountain``). Com terreno sub-célula, usa-se o tipo nas coordenadas da unidade.
2. **Categoria ``ground``** — o valor ``ground`` na def ``style.txt`` daquele terreno (ex.: ``creek`` com ``ground water`` corresponde a ``move_on_water`` / ``falling_on_water``).

O nome do tipo de terreno é tentado antes de ``ground``. ``falling_on_ocean`` funciona em ``ocean`` mesmo quando essa def não tem linha ``ground``; em ``creek``, ``falling_on_creek`` vence sobre ``falling_on_water`` quando ambos existem.

Exemplo::

    def unit
    move 1052 1053
    move_on_ocean 1088 1348
    move_on_water 1088 1348
    move_on_grass 1053 1054
    falling 80051
    falling_delay 1
    falling_on_ocean fallwater
    falling_on_water splash

Apenas unidades **terrestres** usam terreno da casa para ``move_on_``; senão usa-se ``move``. Objetos imóveis próximos (edificações, árvores, etc.) também podem fornecer ``move_on_<tipo de objeto>`` ou ``move_on_<ground>`` quando mais perto.

Unidades burst disparam ``launch_mdg`` / ``launch_rdg`` uma vez por tiro em rajada ``damage_seq``.
Pode listar vários IDs de som na mesma linha para cada tiro escolher entre eles.

``mdg_hit_vs`` / ``rdg_hit_vs`` podem tocar sons de acerto diferentes por tipo de alvo. O conjunto de correspondência do alvo inclui o tipo de unidade, tipos herdados e tipos de buff/debuff ativos no alvo. Exemplo::

    def swordsman
    mdg_hit_vs b_absolute_defense iron_clang

Quando ``swordsman`` acerta um alvo que tem ``b_absolute_defense`` ativo, toca-se
``iron_clang``.

Desde 1.4.4.6, docs e recursos embutidos usam os nomes ``mdg`` / ``rdg``. Chaves antigas
``matk`` / ``ratk`` permanecem como fallback de compatibilidade para mods existentes.

Habilidades, buffs e debuffs também podem definir sons de gatilho::

    def skill_counter
    alert counter_alert
    ready counter_ready
    triggered counter_proc

    def b_absolute_defense
    triggered shield_on
    noise loop shield_hum

Habilidades usadas manualmente tocam ``alert``. Se uma regra de habilidade tiver ``ready \<segundos\>``, o
style da habilidade pode definir ``ready \<som\>``; gatilhos manuais e automáticos tocam ao iniciar preparação.
Habilidades disparadas por ``active_trigger_skills``,
``passive_trigger_skills``, ``attack_trigger_skills`` ou ``attack_replace_skills`` preferem
``triggered`` e recorrem a ``alert`` quando ``triggered`` não está configurado. Buffs e
debuffs aplicados por campos de gatilho tocam seu próprio som ``triggered`` quando configurado.
Sons de status persistentes de buff/debuff devem ser escritos explicitamente como ``noise loop \<som\>`` ou
``noise repeat \<intervalo\> \<som...\>``; ``noise \<som\>`` mantém seu comportamento de parsing existente
e não é tratado como loop automaticamente.

Menu e música do jogo (desde 1.4.0.2)
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Em ``def parameters``::

    menu_music <id>
    campaign_music <id>
    game_creation_music <id>
    server_lobby_music <id>
    game_music <id>
    battle_music <id>
    victory_sound <id>
    defeat_sound <id>
    main_menu_select_sound <id>
    main_menu_confirm_sound <id>

Música de facção (desde 1.4.0.3)::

    china_music china
    china_battle_music china_battle

Substituições de mapa: ``map_music``, ``map_battle_music``, ``map_victory_sound``, ``map_defeat_sound``.
Arquivos de música: ``ui/music/\<id\>.mp3`` ou ``mods/\<mod\>/ui/music/\<id\>.mp3``.
