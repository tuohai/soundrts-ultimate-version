# Arco de la campaña del Norte (La leyenda de Raynor cap. 24-27)



Los capítulos 24-27 forman una historia continua de la alianza del norte: recluta a Garrek con la carta del rey → entrega la ficha de Garrek al Conde Roland y lucha en duelo → presenta el estandarte de guerra al general Vera → derrota a Marco Ironhand. Cada capítulo también requiere eliminar a los asesinos ``traitor_guard``. El progreso persiste a través de ``campaign_flag``.



Mapas:



| Cap. | Archivo | Tema |

| --- | --- | --- |

| 24 | [24.txt](../../../res/single/La leyenda de Raynor/24.txt) | Carta secreta; La ficha de Garrek tras la muerte de los traidores |

| 25 | [25.txt](../../../res/single/La leyenda de Raynor/25.txt) | Token para Roland; duelo de rendimiento; alianza opcional |

| 26 | [26.txt](../../../res/single/La leyenda de Raynor/26.txt) | Estandarte de guerra a Vera; ``transfer_units`` |

| 27 | [27.txt](../../../res/single/La leyenda de Raynor/27.txt) | duelo de marcos; control selectivo de los caballeros de escolta |



Definiciones: `rules.txt <../../../res/single/The Legend of Raynor/rules.txt>`_. TTS: ``ui/tts.txt``, ``ui-zh/tts.txt`` (7575–7718, 7720–7730, 7740–7745).




----




1. Banderas de campaña
----------------------




| Bandera | Ubicado en | Efecto |

| --- | --- | --- |

| ``ch24_garrek`` | 24 | Garrek reclutó; más tarde ``allied_control computer3`` |

| ``ch24_garrek_token`` | 24 | Token ganado; cap. 25 comienza con él en el inventario de Raynor |

| ``ch25_duel_started`` | 25 | Token entregado; duelo comenzado; matando a Roland/guardias antes de esta → derrota |

| ``ch25_roland_allied`` | 25 | Alianza aceptada; más tarde ``allied_assist computer4`` |

| ``ch25_roland_knights`` | 25 | Alianza rechazada; caballeros de compensación en capítulos posteriores |

| ``ch26_vera`` | 26 | Vera se une; Refuerzos de Vera en el cap. 27 |

| ``ch27_duel_started`` | 27 | En el mapa ``map_flag`` (no guardado en todos los capítulos): Raynor llegó al campamento de Marco; escena 7718 reproducida; matar a Marco antes de esta → derrota |

| ``ch27_marco`` | 27 | Marco reclutado |




----




2. Desencadenantes (nuevos y comunes)
-------------------------------------




| Nombre | Tipo | Resumen |

| --- | --- | --- |

| ``add_inventory_item`` | acción | Poner artículo en el inventario unitario: `(add_inventory_item <item> [<count>] [<unit_type>])` |

| ``set_ai_mode`` | acción | Establecer el modo AI en las unidades del propietario del disparador |

| ``set_yield_on_defeat`` | acción | Alternar rendimiento por unidad: `(set_yield_on_defeat <0\|1> [unit selector…])` |

| ``units_yielded`` | condición | Recuento de rendimiento enemigo (``yield_on_defeat``) |

| ``units_yielded_by`` | condición | Rendimiento por atacante específico: `(units_yielded_by <attacker> <count> <victim> [enemy\|ally])`; soporta ``is_a`` |

| ``has_entered`` | condición | Las unidades del propietario del activador ingresaron a un cuadrado (cuadrícula o alias de nombre de lugar) |

| ``stop_all_units`` | acción | Detener el combate; opcional ``computer1`` etc. |

| ``release_yielded_units`` | acción | Poner fin a la invulnerabilidad del rendimiento |

| ``npc_has_item`` | condición | NPC recibió el artículo |

| ``alliance`` | acción | Establecer alianza; objetivo múltiple: `(alliance 1 player1 computer1)` |

| ``alliance_request`` / ``alliance_with`` | acción/cond. | Alianza dinámica (Ctrl+F4 / Shift+F4 en campaña) |

| ``allied_assist`` / ``allied_control`` | acción | Los aliados luchan solos/el jugador controla a los aliados |

| ``transfer_units`` | acción | Cambiar de propietario (cap. 26) |

| ``has_killed`` | condición | Recuento de muertes del equipo |

| ``key_unit_killed`` | condición | Unidad clave realmente murió (no entregada) |

| ``campaign_flag`` / ``set_campaign_flag`` | cond./acción | Progreso entre capítulos |




``cut_scene`` debe ejecutarse en los activadores ``player1`` para que el cliente humano reciba voz. Los cambios de modo AI/rendimiento pueden ejecutarse en ``computer1`` (propietario de la unidad).




La sintaxis del activador es `trigger <owner> <condition> <action>` (tres partes). Utilice `(and …) (defeat)`, no `(if (and …) (defeat))`.




La diplomacia F12 está desactivada en campaña. Utilice Ctrl+F4 para aceptar, Shift+F4 para rechazar.




----




3. Capítulo 24 - Garrek
-----------------------




1. Recoge ``secret_letter``, dáselo a Garrek en el campamento de Garrek (``c2``) → alianza, ``allied_control``, ``ch24_garrek``.

2. Mata a 3 ``traitor_guard`` → ``add_inventory_item garrek_token``, ``ch24_garrek_token``.




----




4. Capítulo 25 - Roland
-----------------------




Transferencia: Garrek en A2 si ``ch24_garrek``; token en inventario si ``ch24_garrek_token``.



Objetivos: (1) entregar la ficha a Roland, (2) derrotar a Roland + 2 caballeros guardianes (ceder), (3) matar a los traidores; alianza opcional.



Fluir:

1. Roland y ``npc_roland_guard`` comienzan en ``guard``, no ``yield_on_defeat`` (se puede matar antes del parto; error → derrota).

2. jugador1 en ``npc_has_item``: ``cut_scene 7701``, objetivo 1, ``ch25_duel_started``.

3. computadora1 en las mismas condiciones: ``set_ai_mode offensive`` + ``set_yield_on_defeat 1``.

4. Después de ceder: alto el fuego, ``alliance_request``; Rama Ctrl+F4 o Shift+F4.



Registre tres objetivos primarios + un objetivo opcional al inicio (numeración independiente).




----




5. Capítulo 26 - Vera
---------------------




Entregar ``war_banner`` a Vera → ``transfer_units computer1 player1``, ``ch26_vera``. Matar a Vera falla la misión.




----




6. Capítulo 27 - Marco
----------------------




Mapa: ``c2`` (campamento de Marco); Marco + escoltas (caballeros/guerreros/arqueros); asesinos en ``b3``/``c3``. Marco y todos los acompañantes comienzan en ``ai_mode guard`` (``rules.txt``).



Transferencia: cap. 24-26 unidades de recompensa por bandera. El jugador comienza como ``raynor7`` con su séquito (2 lacayos, 2 arqueros, 2 caballeros).



Flujo:



1. Raynor ``enters ``c2`` (Marco's camp / 3,2)`` → jugador1: ``cut_scene 7718``, ``set_map_flag ch27_duel_started`` (``raynor7`` debe entrar; los escoltas por sí solos no se activan).

2. computadora1 (conjunto de banderas): solo Marco `(set_ai_mode offensive c2 1 npc_marco_ironhand)`; escolta a `(order … ((go c1)))` a c1 para despejar la arena.

3. Raynor debe derrotar a Marco personalmente: `(units_yielded_by raynor7 1 npc_marco_ironhand enemy)` completa el objetivo principal. Si escoltas u otras unidades obligan a Marco a ceder → ``defeat``.

4. Después del rendimiento: ``cut_scene 7710`` → `(alliance 1 player1 computer1)`, ``stop_all_units``, ``release_yielded_units``.

5. `(allied_control computer1 c2 4 npc_knight_escort)` — cuatro caballeros de escolta bajo el mando del jugador; Se ordena a los escoltas en c1 `(go c2)` que se vuelvan a formar en el campamento de Marco.

6. Mata a 3 ``traitor_guard`` (objetivo secundario) → ``cut_scene 7719`` (línea de cierre de Marco, no el diálogo simbólico de Garrek del capítulo 24 `7580`).



Fallo: mata a Marco antes de que comience el duelo (``key_unit_killed``); Marco cedió por una unidad que no pertenece a Raynor; Raynor muere; limpiar.




----




7. Unidades y artículos
-----------------------




| Tipo | Rol |

| --- | --- |

| ``garrek_token`` | Sello de Garrek (capítulos 24-25) |

| ``npc_count_roland`` | el Conde Roldán; acepta ``garrek_token`` |

| ``npc_roland_guard`` | Caballeros de la guardia (Roland los llama "hermanos" en el diálogo) |

| ``npc_marco_ironhand`` | marco; ``yield_on_defeat`` |

| ``traitor_guard`` | Asesinos; ``guard``, no persigas los cuadrados |




----




8. ``yield_on_defeat``
----------------------




- Con cero HP, la unidad cede en lugar de morir; breve invulnerabilidad.

- ``release_yielded_units`` tras elección de alianza.

- Cap. 25: deshabilitado hasta que se entregue el token (mediante el disparador ``set_yield_on_defeat 1``).




----




9. Comparación (capítulos 24-27)
--------------------------------




| Aspecto | 24 Garrek | 25 Roldán | 26 Vera | 27 Marcos |

| --- | --- | --- | --- | --- |

| Duelo de rendimiento | — | Después del token | — | Desde el principio; Raynor debe asestar el golpe final |

| Inicio del duelo | A la entrega | Después del token | En transferencia de banner | Al entrar al campamento de Marco |

| Mata a NPC clave temprano | Garrek muere → fracasa | Antes del token → fallar | Vera muere → fracasar | Antes del duelo en el campamento → fallar |




----




10. Documentos relacionados
---------------------------




| Tema | Médico |

| --- | --- |

| Dar a NPC | [dar-a-npc.md](dar-a-npc.htm) |

| Modos de IA | [comportamiento-predeterminado-de-la unidad.md](comportamiento-predeterminado-de-la-unidad.htm) |

| Selectores de índice | [selectores-de-índice-de-unidad-de-mapa.md](selectores-de-índice-de-unidad-de-mapa.htm) |

| Sintaxis oficial | ``mod/mapmaking.rst`` |




----




11. Pruebas
-----------




.. code-block:: text

   
   python -m pytest soundrts/tests/test_campaign_alliance_transfer_triggers.py -q
   
   python -m pytest soundrts/tests/test_yield_on_defeat_and_campaign_flags.py -q
   
   python -m pytest soundrts/tests/test_give_item_to_npc.py -q
   






----




12. En toda la campaña (crecimiento de Raynor, séquito, nombres de lugares)
---------------------------------------------------------------------------




Etapas de Raynor (``rules.txt`` / por mapa ``starting_units``):



| Capítulos | Tipo de unidad | Séquito inicial (además de Raynor) |

| --- | --- | --- |

| 1–12 | ``raynor`` | valores predeterminados por capítulo |

| 13–15 | ``raynor2`` | 1 lacayo |

| 16–18 | ``raynor3`` | 2 lacayos |

| 19–21 | ``raynor4`` | 2 lacayos, 1 arquero |

| 22–24 | ``raynor5`` | 2 lacayos, 1 arquero, 1 caballero |

| 25–26 | ``raynor6`` | 2 lacayos, 2 arqueros, 2 caballeros |

| 27–28 | ``raynor7`` | 2 lacayos, 2 arqueros, 2 caballeros |

Escenas del escenario: final del cap. 12 (``7730``); cap. 13/16/19/22/25/27 aperturas (``7720``–``7729``, ``7737``–``7738``). Intros de pantalla de atributos: ``ui/style.txt`` ``intro 7740``–``7746``.



Nombres de lugares: cap. 1 a 28 mapas utilizan ``square_name`` (provincia/condado/sitio). TTS en ``ui-zh/tts.txt`` Sección de nombres de lugares. Los scripts aún pueden usar coordenadas de cuadrícula (``c2``) o alias de nombres de lugares.