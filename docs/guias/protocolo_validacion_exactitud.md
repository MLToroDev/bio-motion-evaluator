# Protocolo de validación de exactitud angular

## Meta

| Campo | Valor |
|-------|-------|
| **Estado** | Activo (documento operativo, listo para ejecutar) |
| **Alcance** | Validación de exactitud de la estimación de flexión de rodilla y asimetría bilateral del motor `vision/` frente a métodos de referencia de medición angular. No cubre latencia extremo a extremo (ver reporte de latencia y Experimento de rendimiento). |
| **Restricción de partida** | El autor **no dispone de goniómetro clínico ni de sujetos de estudio ni de aval de comité de ética**. Todo lo descrito aquí es ejecutable por **una sola persona**, con materiales de papelería y ferretería, sobre sí misma. |
| **Naturaleza** | Este documento describe **cómo se medirá**. No contiene resultados de medición. Los resultados irán en `validacion/reportes/`. |
| **Última revisión** | 2026-08-29 |

## Resumen

Este protocolo responde a la mitad de exactitud de la pregunta de investigación: *¿con qué exactitud, frente a métodos de referencia de medición angular, estima el sistema el ángulo de flexión de rodilla y la asimetría bilateral?*

Se define una validación en tres niveles de coste creciente. El **Nivel 1** construye un patrón físico de ángulo conocido (una férula articulada con transportador impreso) y lo compara contra la salida del sistema: da error absoluto contra verdad conocida. El **Nivel 2** usa video-goniometría manual en Kinovea sobre los vídeos reales del repositorio: da acuerdo contra el método que la propia institución ya emplea. El **Nivel 3** queda descrito pero no se ejecuta ahora: es la ruta de integración si más adelante se consiguen goniómetro clínico y sujetos.

Los criterios de aceptación se fijan **antes** de medir (sección [Criterios de aceptación](#criterios-de-aceptación-pre-registro)) y no se modifican después de ver los resultados.

---

## 0. Qué se mide y contra qué

| Magnitud del sistema | Clave en el payload | Referencia del Nivel 1 | Referencia del Nivel 2 |
|----------------------|---------------------|------------------------|------------------------|
| Flexión de rodilla izquierda | `left_knee_flexion_angle_deg` | Ángulo bloqueado en la férula | Ángulo medido en Kinovea |
| Flexión de rodilla derecha | `right_knee_flexion_angle_deg` | Ángulo bloqueado en la férula | Ángulo medido en Kinovea |
| Asimetría bilateral | `abs(izq - der)` | Derivada de las dos anteriores | Derivada de las dos anteriores |

**Convención, idéntica a la del código** (`vision/biomechanics.py::knee_angles_from_landmarks`):

- *Ángulo interno* = ángulo en la rodilla entre el vector (rodilla -> cadera) y el vector (rodilla -> tobillo).
- *Flexión* = `180 - interno`, acotado a `[0, 180]`. Pierna recta ~ 0 grados de flexión.
- El cálculo del sistema usa las tres coordenadas `x, y, z`; el transportador y Kinovea miden **en el plano de la imagen (2D)**. Esta diferencia de dimensionalidad es una fuente de discrepancia sistemática y se declara como tal en [Amenazas a la validez](#amenazas-a-la-validez).

**Cuidado con la asimetría en marcha.** En el vídeo `Running.mp4`, la asimetría instantánea `|izq - der|` medida por el propio sistema tiene una media de **58,0 grados** y un máximo de **138,1 grados**. Eso **no** es un defecto del sistema ni una patología del sujeto: en carrera las dos piernas están en fases opuestas del ciclo, de modo que la diferencia instantánea mide fase, no asimetría. La asimetría solo es interpretable en ejercicios **bilaterales simultáneos** (sentadilla). En `SentadillaProfunda.mp4` la asimetría media es de 5,5 grados y la mediana de 4,9 grados, valores ya en el orden del error que queremos medir. **La validación de asimetría se hace únicamente sobre sentadilla.**

---

## Criterios de aceptación (pre-registro)

Se fijan **antes** de tomar ningún dato. Registrar la fecha de fijación de estos umbrales en la bitácora del trabajo de grado, para que sea verificable que no se ajustaron a posteriori.

**Referencia de la literatura.** La goniometría clínica manual de rodilla tolera habitualmente diferencias del orden de **5 grados**: es el umbral por debajo del cual la diferencia entre dos mediciones se considera atribuible al error del propio instrumento y no a un cambio real en la articulación (literatura clásica de fiabilidad goniométrica: Gajdosik y Bohannon; Norkin y White, *Measurement of Joint Motion*). *Verificar la cita exacta contra la bibliografía final de la memoria antes de la entrega; el umbral de 5 grados es el valor a usar, la referencia bibliográfica concreta debe cerrarse.*

Para la interpretación del ICC se usan los cortes de Koo y Li (2016): `< 0,50` pobre, `0,50–0,75` moderado, `0,75–0,90` bueno, `> 0,90` excelente.

### Criterios del Nivel 1 (contra patrón físico)

| Criterio | Umbral | Justificación |
|----------|--------|---------------|
| **Principal** — MAE global | **<= 5,0 grados** | Equipara el sistema al margen de error aceptado en goniometría clínica manual. |
| Sesgo (media de las diferencias) | **<= 3,0 grados en valor absoluto** | Un sesgo pequeño es corregible por calibración; separa error sistemático de error aleatorio. |
| Límites de acuerdo Bland-Altman | **amplitud <= +/- 10 grados** | Aproximadamente `2 x SD`; equivale a exigir `SD <= 5 grados`. |
| ICC(2,1) | **>= 0,90** | Corte de "excelente" de Koo y Li. |
| MAE por tramo `[0, 90)` grados | **<= 5,0 grados** | Rango de trabajo funcional habitual. |
| MAE por tramo `[90, 135]` grados | **<= 8,0 grados**, declarándolo | En flexión alta la pierna se autoocluye en vista sagital y el error crece; se acepta un umbral relajado siempre que se reporte por separado y no se promedie con el resto. |

### Criterios del Nivel 2 (contra Kinovea)

| Criterio | Umbral | Justificación |
|----------|--------|---------------|
| **Habilitante** — MAE intra-observador del propio comparador | **<= 3,0 grados** | Si el operador no se repite a sí mismo dentro de 3 grados, el comparador no tiene resolución para juzgar al sistema y el Nivel 2 se declara no concluyente. **Este criterio se evalúa primero.** |
| MAE sistema vs. Kinovea | **<= 7,0 grados** | Umbral más laxo que el Nivel 1 porque la diferencia observada arrastra el error del comparador manual además del error del sistema. |
| ICC(2,1) | **>= 0,85** | Corte "bueno"; se relaja respecto al Nivel 1 por la misma razón. |

### Qué pasa si no se cumplen

Se declara explícitamente en la memoria y **no se retocan los umbrales**. El análisis obligatorio pasa a ser de caracterización: en qué tramo angular falla, si el fallo es sesgo (corregible) o dispersión (no corregible sin cambiar el modelo), y si se concentra en fotogramas con baja `visibility` de los landmarks. Un resultado negativo bien caracterizado es un resultado válido de trabajo de grado; un umbral movido a posteriori invalida el experimento entero.

---

## Nivel 1 — Patrón de referencia físico

### 1.1 El problema científico, de frente: BlazePose no ve el cartón

La idea intuitiva es construir un goniómetro de cartón (dos brazos y un transportador), fijarlo en ángulos conocidos, filmarlo y comparar. **Esa idea, en su forma directa, no funciona**, y conviene decir por qué antes de gastar la mañana del sábado.

El modelo de pose del sistema es BlazePose (`pose_landmarker_full.task`), entrenado para detectar **cuerpos humanos**. No es un detector de segmentos ni de esquinas: su primera etapa localiza una persona y sólo entonces regresa los 33 landmarks. Una figura articulada de cartón no activa esa primera etapa.

**Comprobación ejecutada** (sonda `prueba_a`, ver [Anexo](#anexo-sondas-ejecutadas-para-fundamentar-este-protocolo)): se sintetizó un patrón de dos segmentos rígidos unidos por un eje, sobre fondo claro uniforme, en cuatro ángulos objetivo, y se pasó por `extract_pose_bgr`:

| Ángulo objetivo del patrón | `ok` | Landmarks devueltos | Nota del motor |
|---------------------------|------|---------------------|----------------|
| 0 grados | `True` | **0** | "No se detectó ninguna pose" |
| 45 grados | `True` | **0** | "No se detectó ninguna pose" |
| 90 grados | `True` | **0** | "No se detectó ninguna pose" |
| 135 grados | `True` | **0** | "No se detectó ninguna pose" |

Cero landmarks en los cuatro casos. Un patrón aislado no produce ninguna medición que comparar.

> **Detalle de implementación que hay que respetar al escribir los scripts de validación:** `PoseFrame.ok` vale `True` incluso cuando no se detectó ninguna pose (significa "el frame se procesó sin excepción", no "hay persona"). La comprobación correcta de validez es `pf.landmarks and pf.knees`, **nunca** `pf.ok` a secas. Ver `backend/app/services/pose/mediapipe.py` línea 115.

### 1.2 El diseño que sí funciona: férula solidaria al segmento

**La persona aporta la detección; el patrón aporta la verdad.**

Se construye una **férula articulada de dos brazos con transportador y bloqueo**, y se **fija a la propia pierna del autor**, lateralmente, con el eje sobre la rodilla. MediaPipe detecta a la persona (que sí es un cuerpo humano completo) y produce su estimación; la férula, rígida y solidaria a los segmentos, sostiene la pierna en un ángulo conocido y lo exhibe en el transportador. Se obtiene así, en la misma captura, la estimación del sistema y la verdad de referencia.

La férula cumple además una función mecánica decisiva para un operador solo: **al bloquear el eje con una tuerca de mariposa, la propia férula sostiene la pierna en el ángulo objetivo**, sin que el autor tenga que mantener la posición con esfuerzo muscular ni necesite un ayudante.

**¿Estorba la férula a la detección?** Segunda comprobación ejecutada (sonda `prueba_b`): sobre los **19 fotogramas muestreados** de `SentadillaProfunda.mp4`, se superpuso digitalmente una férula opaca sobre muslo y pierna derechos y se comparó el ángulo estimado con y sin ella.

| Montaje simulado | Fotogramas con detección | Pérdidas de detección | MAE vs. línea base | Sesgo | RMSE | Máx. diferencia |
|------------------|--------------------------|-----------------------|--------------------|-------|------|-----------------|
| Férula **centrada sobre el segmento** (oclusión máxima) | 19 / 19 | 0 | **3,42 grados** | +0,57 | 4,67 | 13,77 |
| Férula **desplazada lateralmente** un 16 % de la longitud del muslo | 19 / 19 | 0 | **1,95 grados** | +0,18 | 2,78 | 7,03 |

Dos conclusiones operativas, y ambas se traducen en instrucciones de montaje:

1. **La detección no se pierde.** En ningún caso MediaPipe dejó de encontrar a la persona. La férula es viable.
2. **Montar la férula al lado del segmento, no encima.** Desplazarla lateralmente reduce casi a la mitad la perturbación que el propio instrumento introduce (de 3,4 a 2,0 grados de MAE), y reduce el caso peor de 13,8 a 7,0 grados. **Regla práctica: el borde interior de la férula va a unos 6 cm del eje longitudinal de la pierna** (16 % de un muslo de 40 cm), lo bastante lejos para no tapar el contorno de la extremidad y lo bastante cerca para seguirla rígidamente.

> Honestidad sobre esta sonda, punto 2: la férula sintética se dibuja **a lo largo de los landmarks que > MediaPipe ya había estimado en ese mismo fotograma**. Es decir, el instrumento simulado se apoya sobre > el eje que el modelo cree ver, no sobre el eje anatómico real, que es donde se apoyaría una férula > física. Eso puede **reforzar** la estimación en vez de perturbarla y, por tanto, la sonda mide una > **cota inferior optimista** de la perturbación instrumental. La cifra buena saldrá del paso 1 del > guion de captura, con la férula construida.
>
> Honestidad sobre esta sonda, punto 1: se trata de una **superposición sintética** sobre fotogramas reales, no de una fotografía de cartón real sobre una pierna real. La textura, el brillo y la sombra proyectada de un objeto físico difieren. La sonda establece que la oclusión geométrica no rompe la detección y que el desplazamiento lateral ayuda; **no** sustituye a una comprobación con la férula construida. **Por eso el paso 1 del guion de captura es exactamente esa comprobación** (sección 1.8).

### 1.3 La limitación geométrica: el eje del transportador no es el centro articular

Es la objeción seria y hay que acotarla con números, no con adjetivos.

El centro de rotación de la rodilla no es un punto fijo (hay rodadura y deslizamiento femorotibial) y, en todo caso, está **dentro** de la articulación, mientras que el eje de la férula queda por fuera, sobre la piel, a la altura aproximada del epicóndilo femoral lateral. La distancia entre ambos, `e`, es de 1 a 3 cm.

**El punto clave, que suele pasarse por alto: si cada brazo de la férula queda paralelo a su segmento, el ángulo leído es correcto aunque el eje esté descentrado.** El ángulo entre dos rectas no depende de dónde se corten. El descentrado sólo hace daño cuando la **dirección** de un brazo la impone el eje descentrado en lugar del segmento. De ahí salen dos modelos de montaje con errores muy distintos:

**Modelo A — montaje pobre: el brazo se ancla en el eje y en un único punto distal.** Su dirección va del eje descentrado al anclaje distal, y se desvía del segmento en `atan(e / L)`:

| Descentrado `e` | Brazo `L` = 250 mm | `L` = 300 mm | `L` = 350 mm |
|-----------------|--------------------|--------------|--------------|
| 5 mm | 1,15 grados | 0,95 | 0,82 |
| 10 mm | 2,29 | 1,91 | 1,64 |
| 15 mm | 3,43 | 2,86 | 2,45 |
| 20 mm | 4,57 | 3,81 | 3,27 |
| 30 mm | 6,84 | 5,71 | 4,90 |
| 40 mm | 9,09 | 7,59 | 6,52 |

*Y en el peor caso los dos brazos se desvían en sentidos opuestos: el error de lectura es el doble.* Un descentrado de 2 cm, perfectamente normal si no se cuida, puede costar **9 grados**. Eso arruinaría el experimento: el instrumento de referencia tendría más error que el sistema que pretende auditar.

**Modelo B — montaje recomendado: cada brazo se fija con DOS anclajes sobre el propio segmento, separados `s`, y el eje queda libre de flotar.** La dirección del brazo la impone entonces el segmento. El error lo domina la incertidumbre `u` de colocación de cada anclaje, como `atan(2u / s)`:

| Incertidumbre `u` por anclaje | `s` = 150 mm | `s` = 200 mm | `s` = 250 mm |
|-------------------------------|--------------|--------------|--------------|
| 1 mm | 0,76 grados | 0,57 | 0,46 |
| 2 mm | 1,53 | 1,15 | 0,92 |
| 3 mm | 2,29 | 1,72 | 1,37 |
| 5 mm | 3,81 | 2,86 | 2,29 |

**Decisión de diseño, en consecuencia:** brazos de **300 mm o más**, **dos correas por brazo separadas al menos 200 mm**, y el eje montado en una **ranura o pletina que permita al eje flotar unos milímetros** en lugar de forzar la geometría. Con `u <= 2 mm` y `s = 200 mm`, el error de referencia queda **por debajo de 1,2 grados por brazo**, es decir, cerca de un quinto del umbral de aceptación de 5 grados. Eso es lo que hace que el patrón sea un patrón y no una segunda fuente de ruido.

**Tolerancia de colocación equivalente**, por si es más cómodo verificarla con una regla en la mano — desplazamiento lateral máximo del extremo del brazo:

| Error angular admitido por brazo | `L` = 250 mm | `L` = 300 mm | `L` = 350 mm |
|----------------------------------|--------------|--------------|--------------|
| 0,5 grados | 2,2 mm | 2,6 mm | 3,1 mm |
| 1,0 grados | 4,4 mm | 5,2 mm | 6,1 mm |
| 2,0 grados | 8,7 mm | 10,5 mm | 12,2 mm |

**Residuo que no se elimina y se declara:** la rodilla no es una bisagra pura. Aunque los brazos estén perfectos, el "ángulo entre segmentos" es un modelo, no una verdad física. Es exactamente **el mismo modelo que asume el sistema** al usar cadera-rodilla-tobillo, de modo que la comparación es interna al modelo y justa; lo que no puede afirmarse es que se está midiendo el ángulo femorotibial anatómico verdadero. Se declara así en la memoria.

### 1.4 El transportador NO se lee desde el vídeo de validación

Presupuesto óptico, calculado para 1920x1080 y un campo horizontal de 65 grados (cámara de teléfono típica):

| Distancia | Ancho de escena | Resolución | Persona de 1,75 m |
|-----------|-----------------|------------|-------------------|
| 2,0 m | 2,55 m | 1,33 mm/px | 1319 px |
| 2,5 m | 3,19 m | 1,66 mm/px | 1055 px |
| 3,0 m | 3,82 m | 1,99 mm/px | 879 px |
| 3,5 m | 4,46 m | 2,32 mm/px | 753 px |

En un transportador de radio 100 mm las marcas de 1 grado distan 1,75 mm: **menos de un píxel a 3 m**. Ni agrandándolo a radio 200 mm se llega a ser legible (1,8 px a 3 m, cuando hacen falta 3 px para distinguir marcas). El paso angular mínimo realmente legible a 3 m es de unos **1,7 a 3,4 grados** según el radio: del mismo orden que el error que queremos medir. **Leer el ángulo de referencia desde el plano general es imposible.**

**Consecuencia operativa, y es importante:** el valor de referencia se obtiene **leyendo el transportador en persona, con la férula ya bloqueada**, antes de filmar; y se documenta con una **foto de detalle en primer plano** del transportador (a 30–40 cm, con el teléfono, inmediatamente antes y después de cada toma). Esa foto de detalle es la evidencia auditable del valor de referencia. El plano general sólo sirve para alimentar al sistema.

La sensibilidad del sistema, en el mismo presupuesto óptico, para un segmento de 0,40 m:

| Distancia | Segmento en px | 1 grado equivale a | 1 px equivale a |
|-----------|----------------|--------------------|-----------------|
| 2,0 m | 301 px | 5,26 px | 0,19 grados |
| 2,5 m | 241 px | 4,21 px | 0,24 grados |
| 3,0 m | 201 px | 3,51 px | 0,29 grados |
| 3,5 m | 172 px | 3,01 px | 0,33 grados |

Es decir: **a 3,5 m, un temblor de 3 px en la posición del tobillo ya vale 1 grado**. Esto justifica preferir el extremo cercano del rango de distancias y explica por qué el ruido de landmark se traduce directamente en ruido angular.

### 1.5 Materiales

| Elemento | Especificación | Dónde | Coste aproximado |
|----------|----------------|-------|------------------|
| Brazos de la férula (x2) | Listón de madera o PVC de **35 x 10 mm, 350 mm de largo**. Alternativa: cartón pluma de 5 mm **doblado en dos capas encoladas** (una sola capa flexa y arruina la rigidez) | Ferretería / papelería | Bajo |
| Eje | Tornillo M6 de 40 mm + arandelas grandes (x2) + **tuerca de mariposa** | Ferretería | Bajo |
| Ranura de flote del eje | Taladro alargado de 6 x 12 mm en uno de los brazos, para que el eje flote (ver Modelo B, sección 1.3) | Se hace en casa | — |
| Transportador | Impreso en papel, **radio 150 mm**, semicírculo 0–180 grados, marcas gruesas cada 5 grados y numeración cada 15 | Impresora doméstica | Bajo |
| Refuerzo del transportador | Pegado sobre cartón pluma o cartulina rígida; **plastificar o cubrir con cinta transparente** | Papelería | Bajo |
| Índice / aguja | Tira de cartulina de color contrastado con punta en bisel, atornillada al brazo móvil | Papelería | Bajo |
| Correas de fijación | **4 correas de velcro** de 40–50 cm (tipo sujeción de cables o cinchas de equipaje). Alternativa: vendas elásticas | Ferretería / farmacia | Bajo |
| Marcadores anatómicos | **Círculos adhesivos de 15–20 mm**, color muy contrastado con la piel (negro sobre piel clara, blanco/amarillo sobre piel oscura). Alternativa: gomets de papelería | Papelería | Muy bajo |
| Soporte de cámara | Trípode, o cualquier superficie estable a la altura de la rodilla. **La cámara no puede ir en la mano** | — | — |
| Cinta métrica | 5 m, para fijar y verificar la distancia cámara-sujeto | Ferretería | Bajo |
| Cinta de enmascarar | Para marcar en el suelo la posición del trípode y la del sujeto | Papelería | Bajo |
| Plomada o nivel de burbuja | Incluido el de cualquier teléfono; para verificar que el trípode está a plomo | — | — |

### 1.6 Construcción

1. **Imprimir el transportador al 100 % de escala.** En el diálogo de impresión, desactivar "ajustar a la página" / "fit to page". **Verificación obligatoria:** el diseño debe incluir una línea de referencia de 100,0 mm; medirla con la regla sobre el papel impreso. Si no mide 100 mm, la impresión salió escalada y **todos los ángulos saldrían mal**. Reimprimir hasta que coincida.
2. Pegar el transportador sobre cartón rígido y recortarlo. Plastificar o cubrir con cinta transparente (va a sufrir).
3. Taladrar el eje: agujero redondo de 6 mm en el brazo proximal (el del muslo); **ranura alargada de 6 x 12 mm** en el brazo distal (el de la pierna), orientada a lo largo del brazo. Esa ranura es la que permite al eje flotar y evita el error del Modelo A.
4. Fijar el transportador al **brazo proximal**, con su centro exactamente en el eje del tornillo. Fijar la aguja al **brazo distal**.
5. Montar tornillo, arandelas y tuerca de mariposa. Comprobar que apretando la mariposa la articulación queda **rígida**: sujetando un brazo, el otro no debe ceder bajo el peso de una pierna.
6. **Verificación de cero.** Alinear los dos brazos rectos, uno sobre otro, y comprobar que la aguja marca 180 grados de ángulo interno (= 0 de flexión). Si no, corregir la posición de la aguja, **no compensar mentalmente después**.
7. **Verificación cruzada de la escala.** Fijar la férula en 90 grados de flexión y comprobar con una escuadra que los brazos forman ángulo recto. Repetir en 45 grados contra una plantilla de papel doblada en diagonal. Anotar cualquier desviación en la hoja de registro.
8. Coser o pegar las 4 correas: **dos por brazo, separadas al menos 200 mm** entre sí.

### 1.7 Marcadores anatómicos: para qué son y para qué no

**Los marcadores adhesivos NO son para MediaPipe.** MediaPipe no los usa: infiere los landmarks del cuerpo completo, y pegarle puntos no cambia su salida. Ponerlos "para que el modelo los vea" es un malentendido que hay que evitar.

Los marcadores sirven para (a) **colocar la férula de forma repetible** y (b) **darle al Nivel 2 los puntos que el observador humano pinchará en Kinovea**. Son el nexo entre los dos niveles.

Tres marcadores en el **lado lateral** de la pierna medida:

| Punto | Referencia anatómica | Cómo localizarlo |
|-------|----------------------|------------------|
| Cadera | **Trocánter mayor del fémur** | De pie, palpar la prominencia ósea lateral de la cadera; rotar levemente la pierna: es el punto que gira bajo el dedo |
| Rodilla | **Epicóndilo femoral lateral** | Con la rodilla a 90 grados, la prominencia ósea lateral por encima de la interlínea articular |
| Tobillo | **Maléolo lateral** | La prominencia ósea externa del tobillo |

Fotografiar los tres marcadores colocados al inicio de la sesión. **Si se despegan, se vuelven a colocar y se anota en el registro**, porque eso rompe la comparabilidad entre repeticiones.

Ropa: **pantalón corto ajustado**, piernas descubiertas, color contrastado con el fondo. Fondo liso, sin patrones. Pies descalzos o con calzado ajustado sin plataforma.

### 1.8 Cámara y encuadre

| Parámetro | Valor | Motivo |
|-----------|-------|--------|
| Distancia cámara-sujeto | **2,7 a 3,5 m** en encuadre apaisado, medida con cinta métrica y **marcada en el suelo con cinta**. Preferir **2,7–3,0 m** | Corrige la recomendación anterior de 2,0–2,5 m, que era **incompatible con el encuadre de cuerpo completo** exigido dos filas más abajo: con FOV horizontal de 65 grados y sensor 16:9, la escena mide 0,717 x d de alto, de modo que un sujeto de 1,75 m **no cabe** por debajo de 2,44 m y no deja margen por debajo de 2,7 m (sección 1.4). A 2,7 m la resolución sigue siendo 0,26 grados/px, holgada frente al umbral de 5 grados. **Si el FOV real de la cámara resulta distinto, recalcular esta fila antes de la sesión.** |
| Altura de la cámara | **A la altura de la rodilla del sujeto** | Minimiza el escorzo perspectivo en la articulación medida |
| Plano | **Sagital**: eje óptico perpendicular al plano de movimiento de la pierna | Es el plano en el que se define la flexión |
| Azimut máximo tolerable | **≤ 20°** (límite operativo recomendado) | Determinado por el **Experimento 2**. Con proyección puramente 2D, el error máximo se mantiene bajo 5° hasta **23,6°** de azimut y el error medio hasta **33,1°**. Se adopta **20°** para dejar margen. Con profundidad correcta la oblicuidad no introduce error, pero mientras la exactitud de la profundidad no esté validada (Nivel 4) se aplica la cota conservadora del caso 2D. **Documentar el azimut real de cada sesión.** |
| Resolución y tasa | **1920x1080 a 30 fps** como mínimo | Coherente con `SentadillaProfunda.mp4` (1920x1080) |
| Estabilización de imagen (EIS/OIS) | **DESACTIVADA** | La estabilización electrónica deforma geométricamente el fotograma (recorte y warping variables) y sesga los ángulos de forma no modelable |
| Enfoque, exposición, balance de blancos | **BLOQUEADOS** antes de empezar | Evita cambios de nitidez y de color a mitad de sesión que alteren la detección |
| Encuadre | **Cuerpo completo, de la cabeza a los pies**, sin recortes | El detector de personas de BlazePose es más fiable con el cuerpo completo |
| Iluminación | Difusa y uniforme. **Nada de contraluz**: ni ventana ni lámpara detrás del sujeto | El contraluz convierte al sujeto en silueta y degrada la detección |

**Verificación del azimut sobre el terreno:** marcar en el suelo con cinta la línea del plano sagital del sujeto y la línea cámara-sujeto; deben formar 90 grados. Comprobar con una escuadra grande o con el método 3-4-5 (3 m sobre una línea, 4 m sobre la otra, la diagonal debe medir 5 m).

### 1.9 Ángulos objetivo y repeticiones

**Ángulos objetivo de flexión (10 niveles):** `0, 15, 30, 45, 60, 75, 90, 105, 120, 135` grados.

Este rango está justificado por los datos reales del repositorio: en `SentadillaProfunda.mp4` la flexión estimada recorre de 5,6 a 135,3 grados en la pierna izquierda y de 3,0 a 133,8 en la derecha; en `Running.mp4`, de 2,8 a 133,8. El barrido `0–135` cubre el rango de trabajo observado.

**Postura de captura:** de pie, apoyado sobre la pierna contraria, **una mano en el respaldo de una silla para el equilibrio**, cadera neutra, rodilla medida flexionada hacia atrás. Es la posición clínica clásica para flexión de rodilla, permite el rango completo `0–135` y mantiene el cuerpo entero visible en plano sagital. La férula bloqueada sostiene el ángulo; el autor no hace fuerza para mantenerlo.

> *Variante para 105–135 grados si el equilibrio de pie resulta inestable:* decúbito prono sobre una colchoneta, con la cámara al nivel del suelo. Anotar el cambio de postura en el registro, porque cambia las condiciones y no debe mezclarse silenciosamente con el resto.

**Repeticiones: mínimo 3 por ángulo, recomendado 5.** Y —esto es lo que le da valor— **una repetición no es volver a grabar: es desbloquear la mariposa, mover la articulación fuera del ángulo objetivo, volver a fijarla en el objetivo y volver a filmar.** Repetir sin desmontar sólo mide el ruido del sensor y sobreestima la precisión.

Por qué 3 como mínimo:

- Con `n = 3` la mediana descarta un error grosero aislado (una lectura mal anotada, una correa suelta); con `n = 2` es imposible saber cuál de las dos está mal.
- Permite estimar la desviación típica dentro de cada condición y separar así **error sistemático** (sesgo, corregible) de **error aleatorio** (dispersión, no corregible).
- El error típico de la media escala como `SD/sqrt(n)`: `0,58 x SD` con `n = 3`, `0,45 x SD` con `n = 5`. Subir a 5 repeticiones cuesta poco tiempo y mejora la estimación un 22 %.

**Además: al menos una vez por sesión, desmontar la férula por completo de la pierna y volver a montarla** (repetición de montaje). Ese es el único modo de capturar la variabilidad de colocación, que es la fuente de error dominante según el análisis de la sección 1.3.

**Duración de cada toma:** mantener el ángulo **3 segundos** filmando. A 30 fps son unos 90 fotogramas; la estimación del sistema para esa condición será la **mediana** de los fotogramas válidos, lo que la hace robusta al temblor de landmark.

**Volumen total:** 10 ángulos x 3 repeticiones = **30 tomas** de 3 segundos = 90 segundos de vídeo útil. Con reposicionamiento, la captura ocupa **45–60 minutos**.

### 1.10 Guion de captura (la mañana del sábado)

**Paso 0 — Preparación (20 min).** Montar el trípode, marcar el suelo con cinta, medir y anotar la distancia, verificar la perpendicularidad, bloquear enfoque/exposición/balance, **desactivar la estabilización**, colocar los tres marcadores adhesivos y fotografiarlos.

**Paso 1 — Comprobación de viabilidad, ANTES de gastar la mañana (5 min).** Montar la férula en la pierna, ponerse en el encuadre, grabar 3 segundos, y **pasar ese clip por el sistema inmediatamente**:

```bash
cd "/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio/backend" && \
  PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/analisis/exportar_para_kinovea.py \
  --video <ruta_del_clip_de_prueba.mp4> --paso 10
```

Criterio de paso: **detección válida (landmarks no vacíos y `knees` no nulo) en al menos el 90 % de los fotogramas**. Si no se alcanza, **detenerse y corregir antes de seguir**: alejar la férula lateralmente del contorno de la pierna, mejorar la iluminación, cambiar el fondo, verificar que el cuerpo entero está en cuadro. En los vídeos existentes la tasa de detección es del **100 %** (183/183 y 1029/1029 fotogramas), así que hay margen: si sale muy por debajo, algo del montaje está mal, no es un límite del sistema.

**Paso 2 — Barrido (45–60 min).** Para cada uno de los 10 ángulos, y para cada una de las 3 repeticiones:

1. Desbloquear la mariposa y sacar la articulación del ángulo objetivo.
2. Fijar el ángulo objetivo en el transportador y **apretar la mariposa a fondo**.
3. **Fotografía de detalle del transportador** a 30–40 cm. Es la evidencia del valor de referencia.
4. Ajustar la férula sobre la pierna con las cuatro correas, verificando que **el borde interior queda a unos 6 cm del eje de la pierna** (sección 1.2).
5. Colocarse sobre la marca del suelo, adoptar la postura, **decir en voz alta el identificador de la toma** ("ángulo 45, repetición 2") — queda en el audio y desambigua los archivos.
6. Grabar **3 segundos** quieto.
7. **Segunda fotografía de detalle** del transportador, para detectar si la férula cedió durante la toma. Si las dos lecturas difieren en más de 1 grado, **descartar la toma y repetirla**.
8. Anotar la fila en la hoja de registro (sección 1.11) antes de pasar a la siguiente.

**Paso 3 — Cierre (5 min).** Repetir la verificación de cero de la férula (sección 1.6, punto 6) para comprobar que no se desajustó durante la sesión. Anotar el resultado. Volcar los vídeos y las fotos a `validacion/datos/nivel1/`.

### 1.11 Plantilla de registro — Nivel 1

Hoja de papel o de cálculo, rellenada **durante** la captura, no después de memoria.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `captura_id` | texto | `N1_<angulo>_<repeticion>`, p. ej. `N1_045_02` |
| `fecha_hora` | ISO 8601 | Momento de la toma |
| `angulo_objetivo_deg` | entero | Uno de `0,15,...,135` |
| `repeticion` | entero | 1, 2, 3 (…5) |
| `referencia_deg` | decimal | **Lectura real del transportador**, no el objetivo. Si se apuntaba a 45 y quedó en 46,5, se anota 46,5 |
| `referencia_deg_post` | decimal | Segunda lectura, tras la toma |
| `lado` | texto | `izquierda` / `derecha` |
| `postura` | texto | `de_pie` / `prono` |
| `remontaje_ferula` | booleano | `si` si se desmontó y remontó la férula antes de esta toma |
| `distancia_camara_m` | decimal | Medida, no estimada |
| `azimut_deg` | decimal | Desviación respecto al plano sagital perfecto |
| `archivo_video` | ruta | Nombre del clip |
| `foto_transportador_pre` | ruta | Foto de detalle previa |
| `foto_transportador_post` | ruta | Foto de detalle posterior |
| `incidencias` | texto libre | Correa suelta, marcador despegado, cambio de luz, toma descartada… |

Tras el procesamiento se añaden, por script y no a mano:

| Columna | Descripción |
|---------|-------------|
| `sistema_deg` | Mediana de la flexión estimada en los fotogramas válidos de la toma |
| `sistema_sd_deg` | Desviación típica dentro de la toma (mide el temblor del sistema en estático) |
| `n_frames_validos` | Fotogramas con `landmarks` y `knees` no nulos |
| `n_frames_total` | Fotogramas leídos |
| `visibility_media_rodilla` | `visibility` media del landmark de rodilla (índice 25 o 26) |

Fichero resultante: **`validacion/datos/nivel1_patron.csv`**.

---

## Nivel 2 — Video-goniometría manual con Kinovea

### 2.1 Por qué Kinovea y no otra cosa

Kinovea es el comparador **con validez institucional** para este trabajo: la Facultad de Educación Física del Tecnológico de Antioquia ya lo emplea en evaluación funcional manual, según se recoge en el apartado **2.3.3 (Contexto Institucional)** de la memoria. Comparar contra Kinovea no es comparar contra una herramienta arbitraria: es comparar contra **el método que la institución considera práctica válida hoy**. Ese es precisamente el argumento del trabajo — cerrar la brecha entre la observación manual y la automatización — y por tanto el comparador correcto para sostenerlo.

Ventaja añadida frente al Nivel 1: se mide sobre **movimiento real y no posado**, con oclusiones, velocidad y ropa reales, y sobre los vídeos que ya están en el repositorio como activos de regresión.

Limitación que compensa esa ventaja, y que hay que tener presente: **Kinovea no es un patrón de oro, es un segundo estimador con su propio error.** Lo que se calcula aquí es *acuerdo entre métodos*, no *exactitud*. De ahí que el Nivel 1 sea necesario y no redundante.

### 2.2 Material disponible (inventario real, medido)

| Archivo | Resolución | fps | Fotogramas | Duración | Muestras cada 10 |
|---------|-----------|-----|------------|----------|------------------|
| `SentadillaProfunda.mp4` | 1920x1080 | 25,07 | 183 | 7,30 s | **19** |
| `Running.mp4` | 640x360 | 29,99 | 1029 | 34,32 s | 103 |
| `CintaRunning.mp4` | 640x360 | 29,98 | 2449 | 81,69 s | 245 |
| `Running2.mp4` | 640x360 | 29,98 | 3295 | 109,92 s | 330 |
| `5-00 por milha…mp4` | 720x1280 | 30,00 | 921 | 30,70 s | 93 |

Rangos angulares reales estimados por el sistema (tasa de detección **100 %** en ambos):

> **Procedencia de estas cifras.** Todas las tablas empíricas de este documento se han
> regenerado con `vision.biomechanics.angulos_rodilla`, que resuelve los ángulos sobre
> `world_landmarks` métricos. Una versión anterior de este protocolo publicó cifras
> calculadas sobre los landmarks normalizados sin corregir la relación de aspecto, rama
> que introduce un sesgo sistemático documentado en
> `docs/spec/goniometria-espacio-de-coordenadas.md` (la mediana de la rodilla derecha en
> `SentadillaProfunda` cambiaba en 13 grados). **Cualquier cifra angular de este documento
> caduca si cambia el cálculo de ángulos: hay que reejecutar las sondas antes de citarla
> en la memoria.**

| Vídeo | Lado | mín | p05 | mediana | p95 | máx |
|-------|------|-----|-----|---------|-----|-----|
| `SentadillaProfunda` | izquierda | 5,6 | 16,2 | 88,9 | 130,2 | 135,3 |
| `SentadillaProfunda` | derecha | 3,0 | 3,8 | 92,8 | 132,2 | 133,8 |
| `Running` | izquierda | 2,8 | 13,2 | 46,4 | 104,1 | 133,8 |
| `Running` | derecha | 10,1 | 20,7 | 55,1 | 131,1 | 159,3 |

Cobertura por tramo angular (rodilla izquierda, porcentaje de fotogramas):

| Tramo | `SentadillaProfunda` | `Running` |
|-------|----------------------|-----------|
| `[0, 30)` | 27,9 % | 35,9 % |
| `[30, 60)` | 8,7 % | 21,6 % |
| `[60, 90)` | 14,8 % | 26,2 % |
| `[90, 120)` | 30,1 % | 15,8 % |
| `[120, 180)` | 18,6 % | 0,5 % |

**Conclusión de selección:** `SentadillaProfunda.mp4` es el vídeo primario del Nivel 2 — es el único con **1080p** (mejor resolución para pinchar puntos a mano), el único **bilateral simultáneo** (única condición en que la asimetría es interpretable) y el que mejor cubre la flexión alta. `Running.mp4` entra como vídeo secundario, para probar el sistema en movimiento rápido, **sólo con la pierna más cercana a la cámara y sólo para flexión**, no para asimetría.

### 2.3 Muestreo: cada 10 fotogramas

Muestrear cada 10 fotogramas es una decisión de **viabilidad de la medición manual**, y conviene justificarla con números en lugar de presentarla como una elección de estilo.

Cada medición en Kinovea (colocar tres puntos, leer, anotar) toma **30–60 segundos** con el flujo ya rodado. Medir los 183 fotogramas de `SentadillaProfunda` en las dos piernas serían 366 mediciones, entre **3 y 6 horas** — y en una segunda pasada para el error intra-observador, el doble. Inviable, y una fatiga así degrada la calidad de las mediciones finales, que es lo peor que puede pasar en el comparador de referencia.

Cada 10 fotogramas, a 25,07 fps, equivale a **una muestra cada 399 ms**. En una sentadilla completa de 7,3 s es resolución de sobra para caracterizar el error a lo largo del recorrido. No se busca reconstruir la curva temporal: se busca una **muestra representativa del rango angular**.

**Cuántas muestras caen realmente en cada tramo** (medido, no supuesto; rodilla izquierda):

| Tramo | `SentadillaProfunda` paso 10 (n=19) | `Running` paso 30 (n=35) |
|-------|-------------------------------------|--------------------------|
| `[0, 30)` | 5 | 13 |
| `[30, 60)` | **2** | 10 |
| `[60, 90)` | **2** | 6 |
| `[90, 120)` | 7 | 6 |
| `[120, 180)` | 3 | **0** |

> **Consecuencia que hay que aceptar por escrito.** Los cinco tramos están cubiertos, pero dos de > ellos con **n = 2**. Un MAE por tramo sobre 2 puntos no es un estadístico: es una anécdota. Por > tanto, en el Nivel 2 **el MAE por tramo sólo se reporta donde `n >= 5`**; en los demás se publica > la lista de diferencias individuales y se dice que no hay potencia. Si se quiere MAE por tramo en > todo el rango, hay que bajar el paso a 5 en `SentadillaProfunda` (38 mediciones en vez de 19) y > asumir el coste. `Running` con paso 30 **no aporta ninguna muestra por encima de 120 grados** en la > pierna izquierda: la flexión alta la cubre únicamente la sentadilla.

**Plan de medición concreto:**

| Conjunto | Vídeo | Paso | Lado | Mediciones |
|----------|-------|------|------|-----------|
| Principal A | `SentadillaProfunda.mp4` | 10 | izquierda | 19 |
| Principal B | `SentadillaProfunda.mp4` | 10 | derecha | 19 |
| Secundario | `Running.mp4` | **30** | la pierna más cercana a la cámara | 35 |
| **Total sesión 1** | | | | **73** |
| Intra-observador (sesión 2) | submuestra aleatoria del 33 % de las anteriores | | | **24** |
| **Total** | | | | **97** |

A 30–60 s cada una: **50–100 minutos**, repartidos en dos sesiones separadas al menos 48 horas. Eso sí es ejecutable.

En `Running.mp4` se sube el paso a 30 (una muestra por segundo) porque 103 mediciones desequilibrarían el esfuerzo hacia el vídeo secundario, que además es de 640x360 y admite peor la medición manual precisa.

### 2.4 Alineación de fotogramas: sin ambigüedad posible

Es donde este tipo de estudio se rompe en silencio: si la fila 7 del CSV no corresponde al fotograma que se midió en Kinovea, el MAE resultante es basura y nada lo delata.

**Hallazgo relevante, comprobado sobre `SentadillaProfunda.mp4`:**

| Índice | `idx / fps` (ms) | `CAP_PROP_POS_MSEC` real (ms) | Desfase |
|--------|------------------|-------------------------------|---------|
| 0 | 0,00 | 0,00 | 0,00 |
| 10 | 398,96 | 381,00 | **17,96** |
| 50 | 1994,81 | 1981,00 | 13,81 |
| 100 | 3989,62 | 3981,00 | 8,62 |
| 180 | 7181,31 | 7181,00 | 0,31 |

Los fps declarados (25,0651) **no describen exactamente** el espaciado real de los fotogramas: el desfase entre el tiempo teórico y el real llega a **18 ms**, casi medio fotograma, y varía a lo largo del vídeo.

**Regla que se deriva: alinear SIEMPRE por índice de fotograma, NUNCA por marca de tiempo.** Un desfase de medio fotograma en una sentadilla rápida ya introduce varios grados de error espurio que se atribuirían falsamente al sistema.

En cambio, el **posicionamiento directo por índice sí es fiable** en estos archivos: se verificó que `cap.set(CAP_PROP_POS_FRAMES, i)` seguido de `read()` devuelve un fotograma **byte a byte idéntico** al obtenido por lectura secuencial, en los índices 0, 10, 50, 100 y 180 (hashes MD5 coincidentes). Se puede exportar por índice con confianza.

**Procedimiento de alineación, con triple seguro:**

1. `exportar_para_kinovea.py` escribe el CSV del sistema **y además** vuelca los fotogramas muestreados como PNG en `validacion/datos/nivel2/<video>/frames/`, con nombre `m<ordinal:04d>_f<indice:05d>.png` (p. ej. `m0003_f00030.png`).
2. Cada PNG lleva el **índice original rotulado en una esquina**, quemado en el píxel. Así el operador ve el número en pantalla mientras mide y no depende de ninguna convención de numeración.
3. En Kinovea se abre la **secuencia de imágenes** (Archivo > Abrir, seleccionar el primer PNG; Kinovea detecta la serie). La posición N de la secuencia corresponde al ordinal N, y el rótulo confirma el índice original. **Kinovea no vuelve a tocar el vídeo, así que no hay forma de que su numeración interna se desincronice.**
4. **Verificación explícita antes de medir nada:** comprobar que el primer PNG rotulado `f00000` y el último coinciden visualmente con el primer y último fotograma del vídeo abierto aparte. Anotarlo como hecho en la hoja de registro.

> El nombre exacto de los ficheros debe coincidir con lo que produzca `validacion/analisis/exportar_para_kinovea.py`. Si ese script usa otra convención, **manda el script** y se corrige este documento, no al revés.

### 2.5 Procedimiento en Kinovea

1. Abrir la secuencia de PNG exportada.
2. **Configurar la lectura de posición como número de fotograma**, no como código de tiempo (clic derecho sobre el indicador de tiempo -> seleccionar número de fotogramas).
3. Seleccionar la herramienta de **ángulo** (medición de tres puntos).
4. Colocar los tres puntos **en este orden fijo**: **cadera (trocánter mayor) -> rodilla (epicóndilo lateral) -> tobillo (maléolo lateral)**, con el vértice en la rodilla. Los marcadores adhesivos de la sección 1.7 son la guía; en los vídeos existentes, que no los tienen, se estiman las referencias óseas por inspección — y esa estimación es justamente la principal fuente de error intra-observador.
5. **Kinovea devuelve el ángulo interno.** Anotar ese valor en la columna `kinovea_interno_deg`. La conversión a flexión, `flexion = 180 - interno`, la hace el script de análisis, **no el operador a mano** (restar 97 veces mentalmente es una fuente de errores de transcripción gratuita).
6. **Verificar el sentido en el primer fotograma:** si la herramienta reportara el ángulo reflejo (mayor de 180), invertir el orden de los puntos y anotarlo. Comprobarlo una vez al principio de cada sesión y dejar constancia.
7. Ampliar (zoom) para colocar los puntos. Trabajar sin zoom sobre 640x360 es la receta segura para un error intra-observador alto.
8. Avanzar a la siguiente imagen y repetir. Anotar cada valor **inmediatamente**, no al final.

### 2.6 Error intra-observador: acotar el propio comparador

Sin esto, el Nivel 2 no es defendible: no se puede juzgar al sistema con una regla cuya precisión se desconoce.

**Procedimiento:**

1. **Sesión 1:** medir los 73 puntos del plan.
2. **Esperar 48 horas como mínimo** (idealmente una semana). Es el intervalo que rompe la memoria visual de dónde se pincharon los puntos.
3. **Sesión 2:** volver a medir una submuestra aleatoria del **33 %** (24 puntos), **en orden aleatorizado** y **sin consultar los valores de la sesión 1**. Aleatorizar el orden con el script, no "a ojo".
4. Calcular el acuerdo del observador consigo mismo con el mismo módulo de análisis: MAE, SD de las diferencias, ICC(2,1) y Bland-Altman.

**Criterio habilitante (ya fijado en el pre-registro): MAE intra-observador <= 3,0 grados.** Se evalúa **antes** de mirar el acuerdo sistema-Kinovea, para no contaminar el juicio.

- Si se cumple, el comparador es utilizable y **el error intra-observador se reporta explícitamente junto al MAE sistema-Kinovea**, como cota inferior del error alcanzable: si el observador se repite con 2,5 grados de error, un MAE de 3 grados frente al sistema es indistinguible de un acuerdo perfecto.
- Si no se cumple, hay dos salidas, y se elige **antes** de ver los datos: (a) medir tres veces cada punto y usar la mediana, o (b) declarar el Nivel 2 no concluyente y apoyar la validación en el Nivel 1. Se prefiere (a).

### 2.7 Plantilla de registro — Nivel 2

Fichero: **`validacion/datos/nivel2_kinovea.csv`**.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `video` | texto | Nombre del archivo de vídeo |
| `ordinal_muestra` | entero | Posición en la secuencia exportada (0, 1, 2…) |
| `frame_idx` | entero | **Índice original en el vídeo** — la clave de unión con el CSV del sistema |
| `lado` | texto | `izquierda` / `derecha` |
| `sesion` | entero | 1 o 2 (2 = repetición intra-observador) |
| `fecha_medicion` | ISO 8601 | Para documentar la separación temporal entre sesiones |
| `kinovea_interno_deg` | decimal | **Valor tal cual lo muestra Kinovea**, sin convertir |
| `confianza_operador` | entero 1–3 | 1 = referencias óseas claras, 2 = dudosas, 3 = estimadas por oclusión. Permite analizar el error condicionado a la calidad de la medición |
| `observaciones` | texto libre | Oclusión, desenfoque de movimiento, punto fuera de cuadro |

El script de análisis añade, por unión sobre `(video, frame_idx, lado)`:

| Columna | Descripción |
|---------|-------------|
| `kinovea_flexion_deg` | `180 - kinovea_interno_deg` |
| `sistema_flexion_deg` | Del CSV exportado por el sistema |
| `visibility_rodilla` | `visibility` del landmark de rodilla en ese fotograma |

---

## Nivel 3 — Opcional: goniómetro clínico y sujetos

No se ejecuta ahora (sin instrumental clínico, sin sujetos, sin aval de comité). Se documenta para que la integración futura no obligue a rehacer nada.

**Qué cambiaría, y qué no.** No cambia nada del pipeline: el goniómetro clínico ocupa exactamente el lugar de la férula del Nivel 1 como fuente de la columna `referencia_deg`. El formato de datos, el módulo de análisis, los criterios de aceptación y las plantillas son los mismos. **Por eso las plantillas de esta guía no tienen ninguna columna específica de "férula": la columna se llama `referencia_deg` y es agnóstica del instrumento.** Basta con añadir una columna `instrumento_referencia` con valores `ferula_casera` / `goniometro_clinico` y el análisis se puede correr conjunto o estratificado.

**Requisitos previos que sí habría que resolver:**

1. **Aval del comité de ética** de la institución y **consentimiento informado** por escrito de cada participante. Los datos personales de los sujetos quedan sujetos a la Ley 1581 de 2012; los vídeos de personas identificables son dato personal y **no se versionan en el repositorio**: sólo se versionan las series numéricas anonimizadas, con los vídeos en almacenamiento aparte con acceso restringido.
2. **Dos evaluadores** en lugar de uno, midiendo con el goniómetro sobre el mismo sujeto y la misma repetición. Eso habilita el error **inter**-observador, que hoy no puede calcularse, y permite pasar de ICC(2,1) individual a un análisis con evaluador como factor.
3. **Tamaño muestral:** para estimar un ICC de 0,90 con un intervalo de confianza de amplitud razonable, la referencia habitual está en el orden de **25–30 sujetos**. Con menos, el ICC se reporta con su intervalo de confianza y se describe como exploratorio.
4. **Sincronización:** la lectura del goniómetro debe corresponder al instante filmado. Se resuelve manteniendo la posición estática, igual que en el Nivel 1.

**Qué aportaría que hoy no se tiene:** variabilidad entre sujetos (distinta antropometría, distinto tejido blando sobre las referencias óseas), que es la limitación de fondo del diseño actual y la que no puede resolverse por más repeticiones que haga un solo autor sobre sí mismo.

---

## Análisis estadístico

**Todo el análisis se ejecuta con `validacion/analisis/acuerdo.py`.** No se calculan estadísticos a mano ni en una hoja de cálculo: el módulo es la única fuente de resultados, para que sean reproducibles desde el CSV crudo.

```bash
cd "/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio/backend" && \
  PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/analisis/acuerdo.py \
  --entrada ../validacion/datos/nivel1_patron.csv \
  --columna-referencia referencia_deg \
  --columna-sistema sistema_deg \
  --salida ../validacion/reportes/nivel1_acuerdo
```

> El nombre exacto de los argumentos debe verificarse contra la interfaz real de `acuerdo.py`, que se está desarrollando en paralelo. **El contrato de nombres de columna lo fija `acuerdo.py`**; si difiere del propuesto aquí, se renombra en este documento y en las plantillas.

Estadísticos a reportar, en todos los niveles:

| Estadístico | Qué responde | Cómo se reporta |
|-------------|--------------|-----------------|
| **MAE** | Magnitud típica del error, en grados | Valor + `n`. Es el estadístico principal, comparable directamente con el umbral de 5 grados |
| **RMSE** | Error penalizando los valores extremos | Junto al MAE. `RMSE >> MAE` indica que hay pocos errores muy grandes en vez de un error uniforme, y obliga a inspeccionarlos |
| **Sesgo** | Media de `sistema - referencia` | Con signo e intervalo de confianza. Un sesgo consistente es corregible por calibración; hay que decirlo |
| **Bland-Altman** | Acuerdo a lo largo del rango | Gráfico diferencia vs. media, con sesgo y límites de acuerdo (`sesgo +/- 1,96 x SD`). **Inspeccionar si la diferencia crece con el ángulo**: eso indicaría error proporcional, no constante |
| **ICC(2,1)** | Acuerdo absoluto, adimensional | Con su intervalo de confianza al 95 % e interpretación según Koo y Li. **Nunca sin el intervalo**: con `n` pequeño el ICC puntual es muy inestable |
| **Error por tramo angular** | Dónde falla | MAE, sesgo y `n` en los tramos `[0,30) [30,60) [60,90) [90,120) [120,180)`. Es lo que permite afirmar en qué rango el sistema es utilizable |
| **Error de asimetría** | Sólo en sentadilla | MAE sobre `abs(izq - der)`, referencia vs. sistema. Se reporta aparte, porque su error se compone del de las dos piernas |

**Reglas de reporte no negociables:**

- Reportar siempre `n` junto a cada estadístico. Un MAE sobre 4 puntos no es lo mismo que sobre 73.
- Reportar los estadísticos **por tramo angular además del global**. Un MAE global de 4 grados puede esconder 2 grados en flexión baja y 12 en flexión alta, y esa distinción es el resultado útil.
- **Los fotogramas descartados se cuentan y se justifican**, uno a uno, en el reporte. Descartar en silencio los casos difíciles es la forma más común de inflar la exactitud.
- **Ningún estadístico se calcula antes de haber cerrado la recogida de datos** de ese nivel. Mirar resultados parciales e ir ajustando el montaje es la vía directa a un resultado no reproducible.

---

## Amenazas a la validez

Se declaran en la memoria, en el capítulo de resultados, **antes** de presentar los números. Un tribunal valora que las limitaciones estén identificadas y acotadas; penaliza que aparezcan sólo en la defensa oral.

| # | Amenaza | Alcance real | Cómo se declara y qué la acota |
|---|---------|--------------|-------------------------------|
| 1 | **Un solo sujeto** (el autor) | La más grave. No hay variabilidad antropométrica: ni distinta proporción de segmentos, ni distinto tejido blando sobre las referencias óseas, ni distinto tono de piel frente al detector | Se declara que los resultados **caracterizan el sistema sobre un sujeto**, no que estimen su exactitud poblacional. **No se extrapola a población.** Se identifica como el primer objetivo del Nivel 3 |
| 2 | **Tamaño muestral pequeño** | 30 tomas (Nivel 1), 73 mediciones (Nivel 2) | Todo estadístico va con `n` e intervalo de confianza. El ICC se presenta como exploratorio. No se usan pruebas de hipótesis que exijan supuestos que `n = 30` no sostiene |
| 3 | **Un solo dispositivo de captura** | Un modelo de cámara, un sensor, un pipeline de compresión | Se documentan modelo, resolución, fps y ajustes. Se declara que el rendimiento puede variar con otro hardware. Los vídeos del Nivel 2 provienen de fuentes distintas, lo que **mitiga parcialmente** esta amenaza |
| 4 | **Iluminación no controlada** | Sin laboratorio; luz doméstica variable | Se fotografía la escena y se anota la condición lumínica de cada sesión. Se bloquean exposición y balance de blancos. Se reporta la tasa de detección por sesión como indicador indirecto |
| 5 | **Desfase entre eje del transportador y centro articular** | Cuantificada en la sección 1.3: hasta 9 grados con montaje pobre, por debajo de 1,2 grados por brazo con el montaje de dos anclajes | Se declara el diseño de dos anclajes y la tolerancia de colocación. Se reporta el **residuo estimado del instrumento junto al error del sistema**, para que el lector distinga uno de otro |
| 6 | **Ausencia de patrón de oro clínico** | Ni goniómetro clínico ni sistema optoelectrónico (Vicon, OptiTrack) | Se declara sin rodeos que la referencia es un **patrón construido ad hoc** con incertidumbre propia estimada, y que Kinovea es **un segundo estimador, no un patrón de oro**. Se evita la palabra "exactitud" sin cualificar: se habla de *error frente al patrón construido* y de *acuerdo con video-goniometría manual* |
| 7 | **La férula altera lo que se mide** | Cuantificada: MAE de 2,0 a 3,4 grados de perturbación sobre la propia estimación, con un caso peor de 13,8 grados (sección 1.2) | Se declara y se reporta como cota de la perturbación instrumental. El montaje lateral la minimiza. **Es la razón de que el Nivel 2, sin férula, sea complementario y no redundante** |
| 8 | **Comparación 3D contra referencia 2D** | El sistema calcula en `x, y, z`; transportador y Kinovea miden en el plano de imagen | Se declara como diferencia de definición, no como error del sistema. Se mitiga con alineación sagital estricta y se acota con el azimut del Experimento 2. El límite adoptado, **20° de azimut**, fija cuánta desalineación invalida la comparación fija cuánto azimut invalida la comparación |
| 9 | **Error intra-observador del comparador manual** | Desconocido a priori | Se mide explícitamente (sección 2.6) y se reporta junto al resultado, como cota inferior del error detectable. Criterio habilitante fijado a priori en 3 grados |
| 10 | **Sesgo del propio autor midiendo su propio sistema** | El autor construye el patrón, monta la férula, mide en Kinovea y analiza | Se mitiga con: criterios de aceptación **pre-registrados** antes de medir, separación temporal y aleatorización de orden en la sesión 2, y publicación de los CSV crudos junto al reporte para que un tercero pueda recalcular. Se declara abiertamente en la memoria |
| 11 | **Autooclusión en flexión alta** | En vista sagital, por encima de ~110 grados la pierna se oculta tras el muslo | Anticipada en los criterios: tramo `[90,135]` con umbral relajado y **reportado por separado**. Se registra la `visibility` de cada landmark para poder condicionar el análisis a la calidad de detección |
| 12 | **Condiciones estáticas en el Nivel 1** | El Nivel 1 mide poses mantenidas; el uso real es dinámico | Por eso existe el Nivel 2, que mide sobre movimiento real. Se declara que el error dinámico puede ser mayor que el estático, y se reporta el error de ambos niveles **por separado, sin promediarlos** |

---

## Anexo: sondas ejecutadas para fundamentar este protocolo

Los números empíricos de este documento no son estimaciones: provienen de código ejecutado sobre el repositorio real el 2026-08-29, con el intérprete `~/.venvs/biomotion/bin/python` y el modelo `backend/models/pose_landmarker_full.task`.

Los scripts están versionados en **`validacion/sondas/`** y son reejecutables tal cual:

```bash
cd "/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio/backend" && \
  PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/sondas/<sonda>.py
```

| Script | Sonda |
|--------|-------|
| `inventario_videos.py` | Inventario de vídeos |
| `caracterizar_rango_angular.py` | Rango angular, cobertura por tramo y tasa de detección |
| `viabilidad_patron_fisico.py` | Detectabilidad del patrón aislado + perturbación de la férula |
| `geometria_desalineacion.py` | Propagación del error de desalineación |
| `presupuesto_optico.py` | Resolución, legibilidad del transportador y grados por píxel |

MediaPipe escribe líneas `I0000`/`W0000` en stderr al inicializar; no son errores. Filtrar con `2>&1 | grep -v "^I0000\|^W0000"`.

| Sonda | Qué estableció | Sección donde se usa |
|-------|----------------|----------------------|
| Inventario de vídeos (OpenCV) | Resolución, fps, fotogramas y muestras por vídeo | 2.2 |
| Caracterización angular | Rango, mediana y cobertura por tramo; **tasa de detección del 100 %** en `SentadillaProfunda` (183/183) y `Running` (1029/1029); asimetría media de 58,0 grados en carrera | 0, 1.9, 2.2 |
| Detectabilidad del patrón aislado | **0 landmarks** en los 4 ángulos probados sobre patrón sin cuerpo humano | 1.1 |
| Perturbación de la férula | 19/19 detecciones conservadas; MAE de 3,42 grados (centrada) frente a 1,95 (desplazada un 16 %) | 1.2 |
| Geometría de desalineación | Tablas de propagación `atan(e/L)` y `atan(2u/s)` | 1.3 |
| Presupuesto óptico | mm/px por distancia; transportador **no legible** desde el plano general; 1 px = 0,19–0,33 grados | 1.4 |
| Alineación de fotogramas | Posicionamiento por índice **byte-exacto**; desfase de hasta **18 ms** entre `idx/fps` y el tiempo real | 2.4 |

**Rendimiento medido durante estas sondas** (Apple M5, arm64, modo VIDEO con seguimiento temporal): **12,9 ms/fotograma** sobre `SentadillaProfunda.mp4` (1920x1080) y **7,2 ms/fotograma** sobre `Running.mp4` (640x360). Procesar los 183 fotogramas del vídeo de sentadilla tarda **2,4 segundos**. Esto es relevante para planificar la jornada: **reprocesar todo el material del Nivel 1 cuesta segundos, no minutos**, así que la comprobación de viabilidad del Paso 1 puede hacerse sin coste. *(Estos valores son sensiblemente mejores que los ~52 ms/fotograma registrados en notas previas del proyecto; la discrepancia debe reconciliarse antes de citar cualquier cifra de rendimiento en la memoria — probablemente difieren las condiciones de medición, y las cifras de latencia oficiales deben salir del experimento de rendimiento dedicado, no de este anexo.)*

## Referencias cruzadas

- `docs/guias/protocolo_captura_clasificacion_ejercicios.md` — condiciones de captura (distancia, plano sagital, encuadre) de las que este protocolo hereda.
- `docs/spec/README.md` — convención del formato de documentación técnica.
- `backend/vision/biomechanics.py` — definición canónica de la convención angular.
- `validacion/analisis/exportar_para_kinovea.py` — exportación de la serie del sistema y de los fotogramas muestreados.
- `validacion/analisis/acuerdo.py` — MAE, RMSE, sesgo, Bland-Altman, ICC(2,1) y error por tramo.
- `docs/Formato_trabajo_de_grado.md` — apartado 2.3.3 (contexto institucional, uso de Kinovea en la Facultad de Educación Física) y bitácora de decisiones.
