# Experimento 2. Sensibilidad a la oblicuidad de cámara

Cuantifica el error del ángulo de flexión de rodilla cuando la cámara no está perpendicular al plano sagital del sujeto, y separa la contribución de la coordenada de profundidad `z`. Todas las medidas se obtienen pasando los landmarks por la función de producción `vision.biomechanics.knee_angles_from_landmarks`.

## Configuración

- Modelo geométrico: muslo 0.45 m, pierna 0.42 m, ancho de caderas 0.18 m.
- Las dos piernas se construyen con la misma flexión verdadera, de modo que la asimetría bilateral verdadera es exactamente 0.00 grados y cualquier asimetría medida es espuria.
- Flexión verdadera: 0, 15, 30, 45, 60, 75, 90, 105, 120, 135 grados.
- Azimut phi: 0, 5, 10, 15, 20, 30, 45, 60, 75, 90 grados. phi = 0 es la vista sagital perfecta; phi = 90 es la vista frontal, con el plano sagital de canto.
- Posturas: `rodilla_aislada` (muslo vertical, pierna hacia posterior) y `flexion_repartida` (la flexión se reparte simétricamente respecto a la vertical). Misma flexión verdadera, distinta orientación absoluta del miembro.
- Proyecciones: ortográfica (caso base) y perspectiva a 2.5 m con campo de visión horizontal de 60 grados.
- Condiciones: `3D` conserva z (profundidad perfecta); `2D` fuerza z = 0.
- Umbral de acuerdo clínico usado: 5 grados.
- Tiempo total de ejecución: 3.4 s.


## Tabla 1. Error absoluto (grados) frente al azimut

Agregado sobre las 10 flexiones verdaderas, las 2 posturas y las 2 piernas, con una muestra por pierna (el máximo es el peor caso de una pierna concreta, no el peor promedio de las dos).

| Azimut | ortogr. 3D medio | ortogr. 3D máx | ortogr. 2D medio | ortogr. 2D máx | perspe. 3D medio | perspe. 3D máx | perspe. 2D medio | perspe. 2D máx |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 5 | 0.00 | 0.00 | 0.11 | 0.22 | 0.28 | 0.69 | 0.22 | 0.50 |
| 10 | 0.00 | 0.00 | 0.43 | 0.88 | 0.54 | 1.41 | 0.38 | 1.09 |
| 15 | 0.00 | 0.00 | 0.98 | 1.99 | 0.79 | 2.11 | 0.62 | 1.95 |
| 20 | 0.00 | 0.00 | 1.76 | 3.56 | 1.02 | 2.77 | 1.15 | 3.05 |
| 30 | 0.00 | 0.00 | 4.06 | 8.21 | 1.35 | 3.78 | 3.17 | 6.01 |
| 45 | 0.00 | 0.00 | 9.69 | 19.68 | 1.54 | 4.26 | 8.46 | 15.62 |
| 60 | 0.00 | 0.00 | 18.78 | 38.82 | 1.47 | 3.88 | 17.47 | 34.67 |
| 75 | 0.00 | 0.00 | 33.00 | 71.71 | 1.35 | 4.54 | 32.36 | 70.65 |
| 90 | 0.00 | 0.00 | 56.84 | 135.00 | 1.08 | 4.55 | 53.51 | 123.10 |


## Tabla 2. Error absoluto por flexión verdadera, condición 2D ortográfica

Media de las dos posturas y las dos piernas.

| Flexión verdadera | phi=0 | phi=5 | phi=10 | phi=15 | phi=20 | phi=30 | phi=45 | phi=60 | phi=75 | phi=90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 15 | 0.00 | 0.06 | 0.22 | 0.50 | 0.88 | 1.96 | 4.32 | 7.42 | 11.06 | 15.00 |
| 30 | 0.00 | 0.10 | 0.41 | 0.92 | 1.63 | 3.65 | 8.17 | 14.32 | 21.78 | 30.00 |
| 45 | 0.00 | 0.13 | 0.53 | 1.19 | 2.12 | 4.82 | 11.04 | 20.02 | 31.63 | 45.00 |
| 60 | 0.00 | 0.14 | 0.57 | 1.29 | 2.30 | 5.28 | 12.41 | 23.45 | 39.43 | 60.00 |
| 75 | 0.00 | 0.13 | 0.53 | 1.21 | 2.16 | 4.99 | 11.89 | 23.10 | 41.76 | 75.00 |
| 90 | 0.00 | 0.11 | 0.44 | 0.99 | 1.78 | 4.11 | 9.74 | 18.43 | 30.49 | 90.00 |
| 105 | 0.00 | 0.13 | 0.53 | 1.22 | 2.19 | 5.14 | 12.72 | 26.00 | 49.36 | 90.00 |
| 120 | 0.00 | 0.14 | 0.57 | 1.30 | 2.35 | 5.54 | 13.85 | 28.66 | 53.78 | 90.00 |
| 135 | 0.00 | 0.13 | 0.53 | 1.21 | 2.18 | 5.11 | 12.73 | 26.36 | 50.75 | 90.00 |


## Tabla 3. Asimetría bilateral espuria (grados)

Asimetría verdadera = 0.00 grados. Se muestra el máximo sobre flexión y postura.

| Azimut | Ortográfica 3D | Ortográfica 2D | Perspectiva 3D | Perspectiva 2D |
| --- | --- | --- | --- | --- |
| 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| 5 | 0.000 | 0.000 | 0.051 | 0.037 |
| 10 | 0.000 | 0.000 | 0.159 | 0.102 |
| 15 | 0.000 | 0.000 | 0.401 | 0.196 |
| 20 | 0.000 | 0.000 | 0.727 | 0.348 |
| 30 | 0.000 | 0.000 | 1.541 | 0.946 |
| 45 | 0.000 | 0.000 | 2.762 | 2.593 |
| 60 | 0.000 | 0.000 | 3.220 | 5.877 |
| 75 | 0.000 | 0.000 | 2.243 | 14.078 |
| 90 | 0.000 | 0.000 | 0.000 | 0.000 |


## Respuesta al umbral de 5 grados

Barrido fino de azimut con paso 0.1 grados. Se busca el mayor phi tal que el error se mantiene por debajo de 5 grados desde 0 hasta ese valor.

| Proyección | Condición | Error MEDIO < 5 grados hasta phi | Error MÁXIMO < 5 grados hasta phi |
| --- | --- | --- | --- |
| ortografica | 3D | sin límite (90) | sin límite (90) |
| ortografica | 2D | 33.1 grados | 23.6 grados |
| perspectiva | 3D | sin límite (90) | sin límite (90) |
| perspectiva | 2D | 36.2 grados | 26.9 grados |


**Respuesta directa.** Con profundidad perfecta (condición 3D) el azimut no impone ningún límite práctico: con proyección ortográfica la rotación es una transformación rígida y el ángulo entre segmentos es exactamente invariante (0.00 grados de error hasta phi = 90), y con perspectiva queda un residuo que nunca llega al umbral. El límite lo fija la condición 2D. Exigiendo que el error no supere los 5 grados en NINGÚN punto de la malla de flexión, el azimut máximo tolerable es **23.6 grados** con proyección ortográfica y **26.9 grados** con perspectiva a 2.5 m. Si sólo se exige que el error MEDIO se mantenga por debajo de 5 grados, el margen sube a 33.1 y 36.2 grados respectivamente.


## Validación empírica con vídeo real

Vídeo `SentadillaProfunda.mp4` (1920x1080, 25.07 fps, 183 frames leídos, 183 con pose válida; extracción 1.6 s, 8.9 ms/frame). Se toman los landmarks métricos (`world_landmarks`) de cada frame, se rotan alrededor del eje vertical un azimut adicional y se mide el error de la condición 2D contra la referencia 3D del mismo frame. Sólo se usan los 181 frames con flexión de referencia mayor o igual a 10 grados.


Dentro del rango operativo la curva empírica reproduce la forma en V que predice el modelo sintético: el error mediano vale 6.90 grados en phi = -45, baja a 3.16 en phi = 0, alcanza su mínimo de 2.45 grados en phi = +10 y vuelve a subir hasta 6.86 en phi = +45. Ese mínimo es una estimación de cuánto le falta a la toma real para ser perfectamente sagital, y coincide en magnitud con un segundo estimador geométrico: la orientación del eje de caderas en el sistema métrico sitúa la oblicuidad de esta grabación en 12 grados (mediana sobre frames). Ese acuerdo **no es una validación cruzada**: los dos estimadores se calculan sobre la coordenada `z` de los mismos `world_landmarks` y de los mismos frames, de modo que comparten la fuente de error y pueden equivocarse juntos. Además el estimador del eje de caderas usa `atan2(|dz|, |dx|)`, que es ciego al signo: corrobora la magnitud de la oblicuidad, nunca su sentido.


Fuera de +/- 45 grados la curva deja de ser informativa y se vuelve no monótona (5.15 grados en phi = -90 y 5.15 en phi = +90, por debajo de valores intermedios). El motivo es que la referencia usada aquí, la profundidad de los `world_landmarks`, no es una verdad de terreno: en este vídeo el segmento cadera-rodilla presenta una extensión en profundidad comparable a la horizontal, algo que no encaja con una toma casi lateral. Con oblicuidades grandes ese ruido de profundidad domina el resultado. Por eso se reporta la mediana además de la media, y por eso este bloque debe leerse como una comprobación de consistencia sobre datos reales, no como una validación contra un patrón de referencia externo.

| Azimut adicional | Error mediano | Error medio | Percentil 95 | Error máximo |
| --- | --- | --- | --- | --- |
| -90 | 5.15 | 18.08 | 61.88 | 72.66 |
| -75 | 8.12 | 17.56 | 64.91 | 93.76 |
| -60 | 8.25 | 10.53 | 28.12 | 41.65 |
| -45 | 6.90 | 9.74 | 29.75 | 63.49 |
| -30 | 5.09 | 13.73 | 62.72 | 89.91 |
| -15 | 5.12 | 8.95 | 31.21 | 51.70 |
| +0 | 3.16 | 7.41 | 23.52 | 40.50 |
| +15 | 3.76 | 9.75 | 44.92 | 68.08 |
| +30 | 5.04 | 10.59 | 39.78 | 80.96 |
| +45 | 6.86 | 8.80 | 21.16 | 43.97 |
| +60 | 5.43 | 9.88 | 32.38 | 36.18 |
| +75 | 4.39 | 13.64 | 54.84 | 62.04 |
| +90 | 5.15 | 18.08 | 61.88 | 72.66 |


El error residual de 2.45 grados (mediana) en el mínimo NO es oblicuidad: es el coste de anular la profundidad en una toma que ya está razonablemente alineada, más el ruido propio de MediaPipe en una sentadilla profunda con oclusión de la pierna lejana. Marca el suelo de error del sistema en la condición 2D.


## Coherencia métrica de los ejes en los landmarks normalizados

Hallazgo colateral, pero con consecuencias directas sobre la exactitud del sistema. Se cuantifica aquí el error que se comete al calcular el ángulo sobre los landmarks NORMALIZADOS de MediaPipe en lugar de sobre los `world_landmarks`. En esos landmarks `x` está dividido por el ancho de imagen, `y` por el alto, y la documentación de MediaPipe afirma que `z` usa aproximadamente la misma escala que `x`. El cálculo del ángulo en 3D exige que los tres ejes compartan escala; si no la comparten, el ángulo se deforma aunque la cámara esté perfectamente alineada y la profundidad sea perfecta.


Escalas estimadas por mínimos cuadrados sobre 183 frames del vídeo real (unidades normalizadas por metro, usando diferencias entre pares de landmarks):

- `s_x` = 0.2588
- `s_y` = 0.4477, de donde `s_y/s_x` = **1.7297** frente al valor esperado si sólo actuase la relación de aspecto, ancho/alto = 1.7778. La anisotropía por relación de aspecto queda confirmada con un desajuste del 2.7 %.
- `s_z` = 0.8401, de donde `s_z/s_x` = **3.2458**, frente al valor 1.0 que cabría esperar según la documentación. La profundidad normalizada está sobredimensionada un factor 3.2 respecto al eje horizontal.


Efecto de cada incoherencia sobre la malla sintética, con profundidad perfecta (condición 3D ortográfica, cuyo error sin distorsión es 0.00 grados en toda la malla). Factor de aspecto 1.7778, razón de profundidad 3.25. Se muestra el error absoluto medio, y entre paréntesis el máximo, agregando sobre flexión, postura y piernas:

| Incoherencia aplicada | phi=0 | phi=10 | phi=20 | phi=30 | phi=45 | phi=60 | phi=90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| solo relacion de aspecto | 15.78 (32.51) | 15.78 (32.51) | 15.78 (32.51) | 15.78 (32.51) | 15.78 (32.51) | 15.78 (32.51) | 15.78 (32.51) |
| solo escala de profundidad | 0.00 (0.00) | 3.58 (7.22) | 10.55 (21.28) | 16.95 (34.37) | 23.82 (48.40) | 28.00 (57.51) | 30.93 (63.83) |
| ambas (normalizados tal cual) | 15.78 (32.51) | 12.46 (25.49) | 5.65 (11.43) | 0.97 (1.96) | 8.50 (17.06) | 13.29 (26.88) | 16.75 (33.96) |


Las dos incoherencias no se comportan igual. La de **relación de aspecto** actúa ya con la cámara perfectamente alineada: 15.78 grados de error medio y 32.51 de máximo en phi = 0, es decir, un orden de magnitud por encima de lo que cuesta una desalineación de 20 grados. Su valor además no depende del azimut, y no es casualidad: los dos segmentos del miembro viven en el mismo plano, luego sus componentes horizontales apuntan siempre en la misma dirección de la imagen y el problema se reduce a uno bidimensional en el que sólo interviene el estiramiento vertical. La de **escala de profundidad** vale exactamente 0.00 grados en phi = 0, porque con la cámara alineada el miembro no tiene componente de profundidad, y sólo aparece al desalinear: 10.55 grados de media en phi = 20 y 23.82 en phi = 45. Es decir, la `z` mal escalada convierte la oblicuidad en error incluso cuando la profundidad estimada es geométricamente correcta.


Además, las dos distorsiones se compensan parcialmente entre sí: aplicadas juntas, el error medio en phi = 20 es 5.65 grados, menor que los 10.55 de la distorsión de profundidad sola. Esa compensación es un accidente numérico, no una propiedad: depende de la distancia de captura, del encuadre y de la relación de aspecto, y no debe tomarse como excusa para no corregir las escalas.

Conviene precisar qué se está midiendo. `s_z/s_x` = 3.25 dice que la profundidad normalizada y la profundidad métrica de MediaPipe **no concuerdan entre sí** por un factor de aproximadamente 3.2. Puede ser que la `z` normalizada esté sobredimensionada, que la `z` métrica esté subdimensionada, o ambas cosas. Lo que sí es seguro es que las dos salidas del mismo modelo se contradicen entre sí, y que calcular un ángulo en 3D mezclando `x`, `y` y `z` normalizados asume una coherencia de escala que aquí no se cumple.


Comprobación sobre el vídeo real. Se compara el ángulo obtenido con cada representación de los landmarks normalizados contra el ángulo obtenido con los `world_landmarks` del mismo frame, que es la mejor referencia métrica disponible.

| Representación | Sesgo | Diferencia absoluta media | Percentil 95 | Máximo |
| --- | --- | --- | --- | --- |
| 3D con landmarks normalizados tal cual | +6.02 | 11.48 | 32.32 | 46.63 |
| 3D con y corregido por aspecto | +17.93 | 20.78 | 55.31 | 76.24 |
| 3D con y y z corregidos | +6.04 | 7.29 | 15.29 | 18.14 |
| 2D (z anulada) tal cual | -4.09 | 14.07 | 33.66 | 45.83 |
| 2D (z anulada) con y corregido | +0.98 | 10.63 | 19.65 | 27.16 |


Corregir sólo la relación de aspecto EMPEORA el resultado, porque al encoger el eje vertical se agrava el peso relativo de una `z` ya sobredimensionada. Corregir los dos ejes a la vez sí mejora de forma clara. La conclusión práctica es que las dos correcciones sólo tienen sentido juntas.


## Conclusiones

1. **Con profundidad perfecta, la oblicuidad de cámara no introduce ningún error.** En la condición 3D con proyección ortográfica la rotación de azimut es una transformación rígida y el ángulo entre segmentos es invariante: el error es 0.00 grados en toda la malla, hasta phi = 90. Con perspectiva a 2.5 m aparece un residuo pequeño (máximo 4.55 grados) por la distorsión proyectiva.
2. **Todo el error frente a la oblicuidad procede de la parte de la medida que vive en el plano de imagen.** Cuanto peor sea la estimación de `z`, más se parece el sistema real a la condición 2D, que es la que fija el límite operativo. La coordenada z no es un adorno: es exactamente lo que compra tolerancia a la desalineación de la cámara.
3. **Límite operativo.** En la condición 2D el error crece de forma acelerada con el azimut: 0.43 grados a phi = 10, 1.76 a phi = 20, 4.06 a phi = 30 y 9.69 a phi = 45 (error medio, proyección ortográfica). El peor caso de la malla supera los 5 grados a partir de phi = 23.6 grados.
4. **La asimetría bilateral es el indicador más frágil, y depende críticamente de que se respete el margen de azimut.** Con proyección ortográfica es exactamente 0.000 grados por simetría del modelo, pero la perspectiva la contamina porque las dos piernas están a distinta profundidad. Dentro del margen recomendado (phi hasta 15 grados) la asimetría espuria máxima es de sólo 0.40 grados, despreciable. Fuera de él crece deprisa: hasta 14.08 grados en un sujeto perfectamente simétrico. Es decir, la asimetría no es un indicador intrínsecamente malo, pero sí el primero que se rompe cuando la cámara se desalinea.
5. **Calcular el ángulo sobre landmarks normalizados, sin escala común entre ejes, introduce un error sistemático** independiente de la oblicuidad y mayor que ella en el rango de trabajo. Es la corrección con mejor relación coste/beneficio del sistema. En el estado actual del repositorio esta corrección **ya está aplicada**: `vision/pose_extractor.py` y `vision/feature_engine.py` llaman a `vision.biomechanics.angulos_rodilla`, que resuelve la fuente de coordenadas y da prioridad a los `world_landmarks` métricos. Las cifras de esta sección miden, por tanto, el error que esa corrección evita, no un defecto vigente.


## Limitaciones

- El modelo sintético es una pierna rígida de dos segmentos en un plano. No modela tejido blando, desplazamiento del centro articular ni el error de detección de los propios landmarks: aísla deliberadamente el efecto geométrico del punto de vista. Los errores reportados son por tanto un **suelo**, no una predicción del error total del sistema.
- La condición 3D supone profundidad perfecta, que MediaPipe no proporciona. Es una cota superior de rendimiento, útil para atribuir el error, no una condición alcanzable.
- Las dos posturas evaluadas cubren dos orientaciones extremas del miembro dentro del plano sagital, pero no agotan las posturas posibles. El azimut máximo tolerable es el peor caso de esas dos, no de todas.
- La proyección en perspectiva asume un sujeto bien encuadrado y centrado en el eje óptico, sin distorsión de lente. Un sujeto descentrado o un objetivo gran angular empeorarían esos resultados.
- La validación empírica usa los `world_landmarks` como referencia 3D a falta de un patrón externo (goniómetro, sistema de captura óptica). Esa referencia tiene ruido de profundidad propio y no permite afirmar exactitud absoluta, sólo consistencia relativa.
- **Los errores MEDIOS están diluidos a la baja en un 11 %.** La malla de flexión incluye el caso de flexión verdadera 0 grados, cuyo error es idénticamente nulo en todos los azimuts porque el miembro está extendido y su proyección no depende del punto de vista. Ese caso aporta ceros a todas las medias. Excluyéndolo, el error medio en la condición 2D ortográfica pasa de 0.43 a 0.48 grados en phi = 10, de 1.76 a 1.96 en phi = 20 y de 4.06 a 4.51 en phi = 30. Las cifras de **máximo**, que son las que fijan el límite operativo de 23.6 grados, no están afectadas.
- **Hay una celda degenerada que se descarta en silencio.** En phi = 90, postura `rodilla_aislada` y flexión 90 grados, la condición 2D proyecta el segmento rodilla-tobillo sobre un vector de longitud nula y el ángulo queda indefinido (`NaN`): son 2 muestras de 1600 en la malla, que las agregaciones `nanmean`/`nanmax` omiten. La celda de la Tabla 2 para flexión 90 y phi = 90 promedia por tanto una sola postura, no las dos que anuncia su encabezado.
- **La consigna de +/- 15 grados se deriva de la condición 2D**, que es la hipótesis pesimista (profundidad inservible), no la condición en la que opera el sistema una vez que el ángulo se calcula sobre `world_landmarks`. Ningún experimento de este informe mide el error del sistema real frente al azimut real de cámara: eso exigiría grabar el mismo gesto desde varios ángulos conocidos, material del que no se dispone. El margen propuesto es por tanto una cota conservadora razonada, no una cifra calibrada sobre el sistema.
- Un solo vídeo, un solo sujeto, un solo gesto. Los números empíricos son ilustrativos; los números sintéticos son los que sostienen la conclusión.


## Recomendación operativa para el protocolo de captura

1. **Alinear la cámara al plano sagital con un margen de +/- 15 grados de azimut.** El límite estricto medido es 23.6 grados en el peor caso de la malla; se propone 15 grados como consigna operativa para dejar margen frente al error de colocación, a que el sujeto no se mantenga exactamente en el eje y a que la profundidad estimada no sea perfecta. A 15 grados el error medio es 0.98 grados y el peor caso 1.99 grados, ambos holgadamente por debajo del umbral clínico.
2. **Materializar la consigna en el sitio de captura**, no dejarla al ojo: marcar en el suelo la línea de desplazamiento del sujeto y la posición del trípode, perpendicular y a 2.5 m. El margen de 15 grados equivale a 0.67 m de desplazamiento lateral de la cámara a esa distancia, es decir, un paso. Sin marca en el suelo ese paso se da sin darse cuenta.
3. **No informar asimetrías bilaterales por debajo de 1.0 grados**, que es el suelo de asimetría espuria dentro del margen recomendado. Y **no informar asimetría en absoluto si la verificación de alineación detecta un azimut mayor de 20 grados**: fuera del margen el propio punto de vista puede generar hasta 14.1 grados de asimetría en un sujeto simétrico, más que cualquier asimetría clínica que se pretenda detectar.
4. **Verificar la alineación automáticamente en cada sesión.** La orientación del eje de caderas en los `world_landmarks` da una estimación de la oblicuidad por frame sin instrumentación adicional; el sistema puede avisar al operador cuando se sale del margen.
5. **Corregir la escala de los ejes antes de calcular ángulos** (o calcularlos sobre `world_landmarks`). Es independiente del protocolo de captura y reduce el error más que cualquier mejora de colocación de la cámara.
