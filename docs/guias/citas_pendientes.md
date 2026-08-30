# Control de afirmaciones y evidencia

Registro de la revisión bibliográfica de
[`docs/Formato_trabajo_de_grado.md`](../Formato_trabajo_de_grado.md).

Se abrió a raíz de detectarse una afirmación epidemiológica **sin fuente y factualmente
incorrecta** (la rodilla como articulación más lesionada en entrenamiento de fuerza).
Todas las entradas están cerradas.

## Regla de redacción adoptada

> Si una frase contiene **«causa», «reduce», «previene», «predice», «principal», «más
> frecuente», «incremento», «elevado»** o **una cifra**, hay que preguntarse: *¿qué estudio
> demuestra exactamente esto?*
>
> Si no existe, **no se busca una cita que salve la frase: se cambia la frase.**

Este principio es el que gobierna la separación, ya presente en el capítulo 7, entre lo que
está medido y lo que no.

## Vocabulario normalizado

El trabajo es de **Ingeniería de Software**, no una investigación clínica sobre predicción
de lesiones. El léxico se ajustó en consecuencia:

| Evitado | Adoptado |
|---------|----------|
| Diagnóstico | Evaluación / medición |
| Diagnóstico biomecánico | Valoración funcional automatizada |
| Predice lesiones | Caracteriza variables de movimiento |
| Previene / reduce lesiones | No evaluado en este trabajo |
| Limitación que causa lesión | Limitación funcional observada |
| Riesgo de lesión | Indicador funcional |

*Excepciones legítimas conservadas:* «diagnóstico de backend» (pantalla técnica de estado),
«diagnóstico INC-OVERLAY» (depuración) y el título del trabajo de Salazar et al. (2008).

## Entradas cerradas

| # | Afirmación | Resolución |
|---|-----------|------------|
| 1 | «La rodilla es la articulación con mayor incidencia lesional en entrenamiento de fuerza» | **Falsa.** Keogh y Winwood (2017): hombro 36 %, lumbar 24 %, codo 11 %, rodilla 9 %. Sustituida por una justificación de **tratabilidad metrológica** (articulación de tipo bisagra frente a enartrosis de 3 grados de libertad), con la elección declarada como limitación de alcance |
| 2 | «Resolución angular útil de un sistema de visión ~0,1°» | **Retirada y no reintroducida.** No es una propiedad universal de la visión artificial: depende de cámara, distancia, resolución, geometría, detector y criterio de aceptación |
| 3 | «Incremento en las lesiones **debido a** patrones disfuncionales» | **Reformulada.** Afirmaba tendencia epidemiológica y causalidad. Sustituida por asociación con evidencia heterogénea y nivel bajo (Bunn et al., 2019; Trinidad-Fernández et al., 2019; Moore et al., 2019) |
| 4 | «Falta de movilidad y asimetrías son los **principales precursores** de compensaciones lesivas» | **Reformulada.** Afirmación causal y jerárquica no sostenible. Ahora se tratan como **indicadores funcionales susceptibles de medición**, no predictores clínicos |
| 5 | «Costo **elevado** de la valoración profesional» | **Reformulada.** «Elevado» carecía de referente. Sustituida por tarifas publicadas en Medellín (desde ~46 000 COP) declaradas como **referencia de mercado, no evidencia científica**, y como barrera *potencial* de acceso |
| 6 | «No existen sistemas de diagnóstico preventivo basados en datos biométricos» | **Retirada.** Afirmación universal de estado del arte, además contradicha por el propio capítulo de antecedentes. Sustituida por el objetivo real: evaluar técnicamente una implementación concreta |
| 7 | «Reduciendo el riesgo de lesiones crónicas» (justificación) | **Retirada.** Exigiría demostrar la cadena medida → intervención → desenlace. Sustituida por viabilidad técnica y exactitud de la medición |
| 8 | «Las asimetrías son predictoras de lesión» + umbral «> 10–15 %» | **Reformulada.** Indicador funcional medible, acotado por el piso de ruido medido (~5°, § 7.2.4). El umbral porcentual sin fuente fue retirado |
| 9 | «Su terna anatómica es **la más estable** para la estimación de pose» | **Medida, no asumida.** Visibilidad mínima mediana: rodilla 0,828 (92,8 % ≥ 0,5), codo 0,519, hombro 0,540. Pero **empata con la terna de tobillo**, y los clips favorecen el tren inferior: ambos matices quedan declarados |
| 10 | Autores de Mehta et al. (2017) | **Verificados:** Mehta, Barker, Bowman, Galloway, Oliashirazi y Oliashirazi. *J Knee Surg*, 30(6), 577–584 |
| 11 | Umbral de acuerdo de 5° | **Declarado como regla práctica sin base estadística**, no como estándar normativo (§ 7.2.3) |

## Referencias incorporadas en esta revisión

- Keogh, J. W. L., & Winwood, P. W. (2017). *Sports Medicine*, 47(3), 479–501.
- Mehta, S. P., et al. (2017). *The Journal of Knee Surgery*, 30(6), 577–584.
- Bunn, P. dos S., et al. (2019). *Physical Therapy in Sport*, 35, 146–158.
- Moore, E., et al. (2019). *Sports Medicine*, 49(9), 1449–1463.
- Trinidad-Fernández, M., et al. (2019). *BMJ Open Sport & Exercise Medicine*, 5(1), e000501.
- Doctoralia (2026) — referencia de mercado local, no fuente académica.
