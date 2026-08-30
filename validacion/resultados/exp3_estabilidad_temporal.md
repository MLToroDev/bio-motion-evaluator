# Experimento 3 - Caracterización empírica sobre vídeo real

Caracterización del estimador de flexión de rodilla del sistema (MediaPipe Pose Landmarker `pose_landmarker_full.task` + `vision.biomechanics.knee_angles_from_landmarks`) sobre los 5 vídeos de referencia del repositorio: 7877 fotogramas procesados en total.

> **Este experimento NO mide exactitud.** No existe medición de goniómetro ni de
> sistema optoelectrónico asociada a estos clips, de modo que ningún número de esta
> página puede citarse como error angular. Lo que se mide es *comportamiento*:
> disponibilidad de la medida, estabilidad temporal, rango observado, piso de ruido
> de la asimetría y **cotas de incertidumbre que no requieren referencia externa**
> (discrepancia entre variantes de cálculo y plausibilidad anatómica).

## 0. Hallazgos que condicionan la lectura del resto

1. **La detección casi nunca falla; el umbral de visibilidad descartaría casi la mitad de un clip, pero hoy no se aplica al ángulo.** Los ángulos son calculables en la práctica totalidad de los fotogramas de todos los clips. Exigir visibilidad >= 0.5 en los 6 landmarks dejaría un clip con la mitad de los fotogramas, pero eso es un **contrafactual**: el sistema emite hoy el bloque `knees` sin filtrar por visibilidad (sección 3).
2. **La estimación depende fuertemente del sistema de coordenadas.** Calcular el mismo ángulo, sobre la misma detección y con la misma función, cambiando solo el espacio de coordenadas de los landmarks, produce discrepancias de decenas de grados (sección 6). Esa discrepancia es una cota inferior de la incertidumbre de la medida y **no necesita goniómetro para citarse**.
3. **Aparecen lecturas anatómicamente imposibles** (flexión por encima de 150 grados) en la ruta de producción (sección 6).
4. **El plano de cámara condiciona la medida y el sistema no lo conoce.** En las tomas sagitales la proyección 2D y la estimación 3D convergen; en las frontales divergen ampliamente (sección 6). Hoy nada en el sistema distingue un encuadre del otro.
5. **Dos de los cinco clips tienen cortes de montaje** (tabla 2). Es un defecto del material de referencia, no del sistema: rompen el tracking temporal y obligan a excluir esos saltos del jitter.
6. **La asimetría bilateral solo es piso de ruido en régimen bilateral simétrico o en tramos cuasi-estáticos** (sección 7); en carrera es señal real de fase.

## 1. Método

- **Motor:** `vision.pose_extractor.extract_pose_bgr_video` (MediaPipe `RunningMode.VIDEO`, con tracking temporal). El ancla de timestamps se reinicia con `reset_pose_video_timestamp_anchor()` antes de cada clip.
- **Ángulo:** flexión = 180 - ángulo interno cadera-rodilla-tobillo, acotado a [0, 180] grados. Es la convención del proyecto. **La fuente de coordenadas la resuelve el propio proyecto** (`vision.biomechanics`), no este experimento; la sección 6 muestra cuál está usando de hecho en la versión medida.
- **Umbral de visibilidad evaluado:** 0.5 sobre la visibilidad mínima de los 6 landmarks usados (caderas, rodillas, tobillos).
- **Tope de fotogramas por vídeo:** 4000 como salvaguarda de cómputo; ningún clip lo alcanza, así que **todos los vídeos se procesaron completos**, sin recorte ni submuestreo.
- **Jitter:** desviación típica de la primera diferencia de la serie angular, en grados por fotograma, calculada **solo dentro de tramos de fotogramas consecutivos válidos** (un hueco de detección no se cuenta como salto).
- **Ruido de alta frecuencia:** RMS del residuo frente a un suavizado Savitzky-Golay (ventana 9, orden 2). Separa mejor el ruido del movimiento real que la primera diferencia bruta.
- **Tramos cuasi-estáticos:** fotogramas donde la desviación típica local (ventana centrada de 5 fotogramas) es menor que 1.5 grados **en ambas piernas**.
- **Techo de plausibilidad anatómica:** 150 grados de flexión de rodilla (la flexión pasiva máxima, talón al glúteo, ronda 150-160 grados). Por encima, la lectura no puede corresponder a una postura real.
- **Variantes de coordenadas comparadas.** Todas llaman a la misma función del proyecto (`knee_angles_from_landmarks`) y solo cambian los landmarks de entrada:
  - `produccion`: lo que devuelve hoy `extract_pose_bgr_video`. **(ruta de producción)**
  - `world_xyz`: world landmarks metricos (x, y, z). *(auxiliar, solo para este análisis)*
  - `imagen_xyz_isotropico`: imagen (x, y, z) con y reescalado por alto/ancho. *(auxiliar, solo para este análisis)*
  - `imagen_xy_isotropico`: imagen (x, y) isotropico, con z = 0 (proyeccion en el plano). *(auxiliar, solo para este análisis)*
  - `imagen_xyz_normalizado`: imagen (x, y, z) normalizados sin corregir (ruta historica). *(auxiliar, solo para este análisis)*
- **Coste de ejecución:** 57.7 s de reloj para el lote completo.
- **Determinismo comprobado:** dos ejecuciones consecutivas del lote, con el mismo código, producen series angulares idénticas (0 celdas distintas al comparar los CSV de `SentadillaProfunda.mp4` y `Running.mp4`, 183 y 1029 fotogramas). Lo único que varía entre corridas es el tiempo de inferencia por fotograma.

**Procedencia del código medido.** El repositorio se edita mientras corren los experimentos y la ruta de cálculo angular vive en módulos que pueden cambiar entre corridas, así que cada ejecución deja su huella:

| Elemento | Valor |
|---|---|
| Commit | `3c84893` |
| Árbol de trabajo (`backend/vision`, `backend/app/services/pose`) | con cambios sin confirmar |
| `vision/biomechanics.py` | sha256 `9a5ee3cab546` |
| `vision/pose_extractor.py` | sha256 `5411bf06bb65` |
| `app/services/pose/mediapipe.py` | sha256 `a812ba09a084` |

Si el árbol figura *con cambios sin confirmar*, los números corresponden al código del árbol de trabajo en ese momento, no al del commit.

## 2. Vídeos procesados

| Vídeo | Identificador de artefactos | Régimen | Plano de cámara | Resolución | fps | Fotogramas del clip | Procesados | Recortado | Cortes de plano |
|---|---|---|---|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora olha o que acontece quando a gente mexe só em UMA variável- A CAD.mp4` | `5_00_por_milha_3_06_km_Agora_olha_o_que_acontece_quando_a_ge` | marcha / carrera | sagital (lateral, cinta; video editado con cortes) | 720x1280 | 30.00 | 921 | 921 | no | 3 (fotogramas 34, 670, 768) |
| `CintaRunning.mp4` | `CintaRunning` | marcha / carrera | frontal (de frente, cinta) | 640x360 | 29.98 | 2449 | 2449 | no | 0 |
| `Running.mp4` | `Running` | marcha / carrera | posterior-oblicuo (corriendo alejandose) | 640x360 | 29.99 | 1029 | 1029 | no | 0 |
| `Running2.mp4` | `Running2` | marcha / carrera | sagital (lateral, con paneo) | 640x360 | 29.98 | 3295 | 3295 | no | 0 |
| `SentadillaProfunda.mp4` | `SentadillaProfunda` | bilateral simetrico | frontal (de frente; corte de plano hacia el final del clip) | 1920x1080 | 25.07 | 183 | 183 | no | 1 (fotogramas 86) |

En las tablas siguientes el nombre del vídeo aparece abreviado; el nombre completo y su identificador de artefactos están en esta tabla.

Los **cortes de plano** se detectan automáticamente comparando fotogramas consecutivos (diferencia media absoluta en escala de grises reducida) con un umbral relativo a cada clip. Importan por dos motivos: rompen el tracking temporal de MediaPipe, y el salto angular que producen **no es ruido del estimador**, por lo que se excluye del cálculo de jitter (la serie se parte en el corte, igual que en un hueco de detección). El criterio es conservador: detecta cortes secos y puede pasar por alto encadenados suaves.

El **plano de cámara** es una anotación manual del autor del experimento, hecha por inspección visual de un fotograma de cada clip. El sistema **no** detecta el plano de la toma; se anota aquí porque, como muestra la sección 6, es la variable que más condiciona la lectura angular.

Nota: MediaPipe reescala internamente el fotograma a un lado máximo de 640 px antes de inferir (`_TARGET_MAX_DIM` en `app/services/pose/mediapipe.py`), así que la resolución nativa del clip no se traduce en resolución efectiva de inferencia.

## 3. Tasa de detección y sensibilidad al umbral de visibilidad

| Vídeo | Pose detectada (%) | Ángulos calculables (%) | Ángulos con visibilidad >= 0.5 (%) | Caída por el umbral (p.p.) | Visibilidad mín. mediana | Visibilidad mín. p05 | Landmark limitante dominante |
|---|---|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | 97.07 | 97.07 | 94.90 | 2.17 | 0.717 | 0.597 | `right_knee` (94.63 %) |
| `CintaRunning.mp4` | 100.00 | 100.00 | 100.00 | 0.00 | 0.816 | 0.741 | `right_ankle` (57.74 %) |
| `Running.mp4` | 100.00 | 100.00 | 99.90 | 0.10 | 0.794 | 0.671 | `left_knee` (72.98 %) |
| `Running2.mp4` | 99.70 | 99.70 | 99.70 | 0.00 | 0.832 | 0.757 | `left_knee` (92.79 %) |
| `SentadillaProfunda.mp4` | 100.00 | 100.00 | 53.01 | 46.99 | 0.667 | 0.318 | `left_knee` (54.10 %) |

Lectura: la detección de pose no es el cuello de botella. **La columna del umbral describe un escenario contrafactual, no el comportamiento actual del sistema.** Hoy `pose_landmark_min_visibility_response` (0.5 por defecto) solo recorta la lista de landmarks que viaja al cliente para dibujar el esqueleto (`vision.landmark_filter.landmarks_for_api_response`); el bloque `knees` sale sin filtrar en `vision.unified_payload.build_frame_payload_v1`, de modo que **ningún ángulo se descarta hoy por visibilidad**. Lo que la columna muestra es qué ocurriría si se condicionase la medida a ese umbral: el efecto **no es uniforme entre clips** y vaciaría casi la mitad de la sentadilla. Como el landmark limitante tiende a ser el mismo dentro de cada clip, si alguna vez se decide condicionar el ángulo a la visibilidad convendría un umbral por articulación antes que un valor global.

## 4. Rango de movimiento observado (ruta de producción)

Flexión de rodilla en grados. Es el rango que el estimador *reporta*, no el rango real del sujeto: sin referencia externa no puede afirmarse cuál de los dos es. Compárese con el techo de plausibilidad de la sección 6.

| Vídeo | Pierna | Mín. | Máx. | Recorrido | Mediana |
|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | izquierda | 16.20 | 137.57 | 121.36 | 63.94 |
| `5-00 por milha → 3-06-km.Agora...` | derecha | 0.29 | 122.86 | 122.57 | 29.77 |
| `CintaRunning.mp4` | izquierda | 9.85 | 97.37 | 87.52 | 34.13 |
| `CintaRunning.mp4` | derecha | 10.28 | 88.78 | 78.50 | 29.45 |
| `Running.mp4` | izquierda | 2.81 | 133.80 | 130.99 | 46.35 |
| `Running.mp4` | derecha | 10.07 | 159.27 | 149.20 | 55.10 |
| `Running2.mp4` | izquierda | 0.57 | 147.30 | 146.72 | 55.46 |
| `Running2.mp4` | derecha | 0.39 | 161.29 | 160.91 | 52.45 |
| `SentadillaProfunda.mp4` | izquierda | 5.61 | 135.31 | 129.70 | 88.86 |
| `SentadillaProfunda.mp4` | derecha | 2.99 | 133.83 | 130.84 | 92.83 |

## 5. Ruido temporal (jitter) de la ruta de producción

| Vídeo | Pierna | Jitter (grados/fotograma) | Jitter (grados/s) | Salto mediano abs. | Salto p95 abs. | Ruido alta frec. RMS |
|---|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | izquierda | 18.953 | 568.60 | 11.392 | 40.570 | 11.406 |
| `5-00 por milha → 3-06-km.Agora...` | derecha | 15.948 | 478.44 | 8.493 | 31.280 | 9.746 |
| `CintaRunning.mp4` | izquierda | 9.315 | 279.27 | 4.369 | 20.629 | 4.072 |
| `CintaRunning.mp4` | derecha | 9.236 | 276.89 | 3.796 | 21.360 | 5.268 |
| `Running.mp4` | izquierda | 29.488 | 884.23 | 12.610 | 73.132 | 18.267 |
| `Running.mp4` | derecha | 32.194 | 965.36 | 13.384 | 78.240 | 18.335 |
| `Running2.mp4` | izquierda | 31.407 | 941.41 | 14.822 | 76.622 | 19.264 |
| `Running2.mp4` | derecha | 32.495 | 974.03 | 15.289 | 81.345 | 19.702 |
| `SentadillaProfunda.mp4` | izquierda | 2.643 | 66.25 | 1.148 | 5.497 | 0.770 |
| `SentadillaProfunda.mp4` | derecha | 2.649 | 66.41 | 1.086 | 5.819 | 0.739 |

Lectura: la columna *jitter* mezcla movimiento real y ruido del estimador, y por eso es alta en carrera aunque el estimador fuese estable. La columna *ruido de alta frecuencia* aísla mejor la componente de ruido; es la que debe citarse como piso de ruido cuadro a cuadro. Sigue siendo una cota superior: parte del residuo de alta frecuencia en carrera es movimiento real rápido.

Referencia cuasi-estática (el estimador midiendo algo que apenas se mueve; es el caso más limpio disponible sin referencia externa):

| Vídeo | Fotogramas cuasi-estáticos | Jitter izq. (grados/fotograma) | Jitter der. (grados/fotograma) |
|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | 30 | 0.159 | 0.124 |
| `CintaRunning.mp4` | 0 | n/d | n/d |
| `Running.mp4` | 0 | n/d | n/d |
| `Running2.mp4` | 0 | n/d | n/d |
| `SentadillaProfunda.mp4` | 53 | 0.550 | 0.417 |

## 6. Sensibilidad al sistema de coordenadas y plausibilidad anatómica

Todas las variantes parten de **la misma detección de pose y la misma función de cálculo** (`knee_angles_from_landmarks`): solo cambian los landmarks de entrada. La diferencia entre ellas no es error de detección, sino ambigüedad del propio método de medida. **La discrepancia entre variantes es una cota inferior de la incertidumbre angular del sistema y no necesita goniómetro para ser citada.**

Variantes:

- `produccion`: lo que devuelve hoy `extract_pose_bgr_video`. **(referencia de comparación)**
- `world_xyz`: world landmarks metricos (x, y, z).
- `imagen_xyz_isotropico`: imagen (x, y, z) con y reescalado por alto/ancho.
- `imagen_xy_isotropico`: imagen (x, y) isotropico, con z = 0 (proyeccion en el plano).
- `imagen_xyz_normalizado`: imagen (x, y, z) normalizados sin corregir (ruta historica).

La variante `imagen_xyz_normalizado` reproduce la ruta que el proyecto usaba antes de la corrección de espacio de coordenadas (`docs/spec/goniometria-espacio-de-coordenadas.md`); su columna de discrepancia es, por tanto, **la medida sobre vídeo real del sesgo que esa ruta introducía**.

| Vídeo | Variante | Mediana flexión | p95 flexión | Máx. flexión | % lecturas > 150 grados | Ruido alta frec. RMS | Discrepancia mediana vs. producción | Discrepancia p95 | Discrepancia máx. |
|---|---|---|---|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | `produccion` | 43.41 | 102.64 | 137.57 | 0.00 | 10.576 | - | - | - |
| `5-00 por milha → 3-06-km.Agora...` | `world_xyz` | 43.41 | 102.64 | 137.57 | 0.00 | 10.576 | 0.00 | 0.00 | 0.00 |
| `5-00 por milha → 3-06-km.Agora...` | `imagen_xyz_isotropico` | 47.56 | 101.67 | 174.18 | 0.06 | 11.936 | 5.95 | 21.23 | 102.90 |
| `5-00 por milha → 3-06-km.Agora...` | `imagen_xy_isotropico` | 45.05 | 105.69 | 174.91 | 0.22 | 13.899 | 6.78 | 23.39 | 133.34 |
| `5-00 por milha → 3-06-km.Agora...` | `imagen_xyz_normalizado` | 56.76 | 115.94 | 174.33 | 0.06 | 13.438 | 13.23 | 41.40 | 103.04 |
| `CintaRunning.mp4` | `produccion` | 31.98 | 78.16 | 97.37 | 0.00 | 4.670 | - | - | - |
| `CintaRunning.mp4` | `world_xyz` | 31.98 | 78.16 | 97.37 | 0.00 | 4.670 | 0.00 | 0.00 | 0.00 |
| `CintaRunning.mp4` | `imagen_xyz_isotropico` | 81.00 | 132.78 | 154.74 | 0.29 | 10.822 | 48.17 | 65.68 | 78.97 |
| `CintaRunning.mp4` | `imagen_xy_isotropico` | 4.38 | 17.53 | 53.63 | 0.00 | 2.261 | 28.20 | 65.86 | 87.84 |
| `CintaRunning.mp4` | `imagen_xyz_normalizado` | 60.33 | 110.77 | 137.43 | 0.00 | 8.049 | 26.75 | 39.42 | 50.84 |
| `Running.mp4` | `produccion` | 51.45 | 125.65 | 159.27 | 0.05 | 18.301 | - | - | - |
| `Running.mp4` | `world_xyz` | 51.45 | 125.65 | 159.27 | 0.05 | 18.301 | 0.00 | 0.00 | 0.00 |
| `Running.mp4` | `imagen_xyz_isotropico` | 75.28 | 135.81 | 165.30 | 0.68 | 14.688 | 27.76 | 62.34 | 86.61 |
| `Running.mp4` | `imagen_xy_isotropico` | 46.40 | 138.25 | 173.92 | 0.92 | 21.444 | 9.10 | 27.43 | 74.65 |
| `Running.mp4` | `imagen_xyz_normalizado` | 62.68 | 126.94 | 154.85 | 0.24 | 15.973 | 15.60 | 35.04 | 55.97 |
| `Running2.mp4` | `produccion` | 53.75 | 124.47 | 161.29 | 0.17 | 19.483 | - | - | - |
| `Running2.mp4` | `world_xyz` | 53.75 | 124.47 | 161.29 | 0.17 | 19.483 | 0.00 | 0.00 | 0.00 |
| `Running2.mp4` | `imagen_xyz_isotropico` | 65.46 | 133.03 | 167.58 | 0.46 | 18.355 | 15.64 | 46.48 | 84.30 |
| `Running2.mp4` | `imagen_xy_isotropico` | 53.95 | 132.50 | 179.93 | 0.47 | 20.127 | 8.83 | 25.67 | 91.53 |
| `Running2.mp4` | `imagen_xyz_normalizado` | 54.52 | 130.34 | 171.30 | 0.23 | 19.745 | 10.46 | 30.67 | 96.72 |
| `SentadillaProfunda.mp4` | `produccion` | 90.40 | 132.04 | 135.31 | 0.00 | 0.754 | - | - | - |
| `SentadillaProfunda.mp4` | `world_xyz` | 90.40 | 132.04 | 135.31 | 0.00 | 0.754 | 0.00 | 0.00 | 0.00 |
| `SentadillaProfunda.mp4` | `imagen_xyz_isotropico` | 108.11 | 141.46 | 148.54 | 0.00 | 1.403 | 13.86 | 55.31 | 76.24 |
| `SentadillaProfunda.mp4` | `imagen_xy_isotropico` | 88.27 | 139.26 | 144.63 | 0.00 | 0.442 | 10.18 | 19.65 | 27.16 |
| `SentadillaProfunda.mp4` | `imagen_xyz_normalizado` | 96.88 | 137.44 | 144.37 | 0.00 | 1.098 | 8.84 | 32.32 | 46.63 |

**Aviso de lectura: `world_xyz` no es una variante independiente.** Su discrepancia sale 0.00 en los cinco clips y en todos los fotogramas porque coincide *exactamente* con la ruta de producción: `vision.biomechanics.angulos_rodilla` prefiere los `world_landmarks` siempre que existen, y existen en todos los fotogramas detectados. En la versión medida, producción **es** esa variante. Esa fila de ceros **no es una corroboración entre dos métodos**, sino una comprobación de procedencia que identifica qué espacio de coordenadas usa el sistema hoy. Las únicas comparaciones informativas de esta tabla son las de las variantes de imagen.


**Ancla cualitativa.** En `SentadillaProfunda.mp4`, fotograma 70, verificado visualmente: el sujeto esta de pie, completamente erguido, con los pies separados (toma frontal). Una rodilla erguida debería leerse cerca de 0 grados de flexión. Lecturas de cada variante en ese fotograma:

| Variante | Rodilla izquierda | Rodilla derecha |
|---|---|---|
| `produccion` | 17.25 | 13.84 |
| `world_xyz` | 17.25 | 13.84 |
| `imagen_xyz_isotropico` | 59.10 | 54.98 |
| `imagen_xy_isotropico` | 0.98 | 0.99 |
| `imagen_xyz_normalizado` | 37.49 | 35.19 |

Sobre una postura erguida, la ruta de producción reporta 17.25 / 13.84 grados; la ruta histórica sin corregir, 37.49 / 35.19; la proyección 2D isotrópica, 0.98 / 0.99.

Tres advertencias antes de leer la diferencia como error del estimador:

- El ángulo de tres puntos cadera-rodilla-tobillo **no es flexión sagital pura**: con los pies separados, como en este fotograma, el muslo queda oblicuo en el plano frontal y el ángulo en la rodilla recoge esa oblicuidad real. Parte de la lectura es geometría verdadera del sujeto, no error.
- Que la proyección 2D dé casi 0 **no la convierte en la variante correcta**: en una toma frontal esa proyección es prácticamente ciega a la flexión, y daría un valor bajo tanto con el sujeto erguido como flexionando hacia la cámara. En este mismo clip subestima la sentadilla profunda.
- Las variantes que usan `z` dependen por completo de la calidad de esa coordenada, que es la peor estimada de las tres.

La conclusión defendible no es «el sistema se equivoca en X grados», sino que **la magnitud reportada como «flexión de rodilla» no está definida sin fijar un plano de proyección**, y el sistema hoy no lo fija ni lo detecta. Un fotograma de postura conocida como este es, además, el tipo de ancla que debería multiplicarse en un protocolo con goniómetro para convertir estas cotas en una medida de exactitud.

**Concordancia entre la proyección 2D y la estimación 3D, por plano de cámara.** Si la cámara mira el plano en el que ocurre la flexión, ambas formas de calcular deberían converger; si no, deben divergir. Es una prueba de consistencia interna que tampoco requiere referencia externa:

| Plano de cámara (anotado) | Vídeos | Discrepancia mediana 2D vs. producción: media (grados) | Rango entre clips |
|---|---|---|---|
| frontal | 2 | 19.19 | 10.18 - 28.20 |
| posterior-oblicuo | 1 | 9.10 | clip único |
| sagital | 2 | 7.80 | 6.78 - 8.83 |

Con cinco clips y un solo sujeto por clip esto es una **señal, no una prueba**, y el reparto es desigual dentro del grupo frontal. Aun así apunta en la dirección que predice la geometría y sugiere una línea de trabajo concreta: **la concordancia 2D/3D podría servir de indicador automático de si el encuadre sirve para medir**, sin pedir al usuario que declare el plano. Verificarlo exige un diseño con varios sujetos y planos controlados.

## 7. Asimetría bilateral: qué es piso de ruido y qué no

**Advertencia de interpretación (crítica).** En marcha o carrera las piernas están en fases opuestas del ciclo, así que `|izquierda - derecha|` es grande y **es señal real, no ruido**. Solo puede leerse como piso de ruido del estimador en movimientos bilaterales simétricos (sentadilla) o en tramos cuasi-estáticos. Las columnas de clip completo y las cuasi-estáticas **no deben mezclarse** en la memoria.

| Vídeo | Régimen | Asimetría mediana (todo el clip) | Asimetría p95 (todo el clip) | Fotogramas cuasi-estáticos | % del clip | Asimetría mediana cuasi-estática | Asimetría p95 cuasi-estática | ¿Piso de ruido válido? |
|---|---|---|---|---|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | marcha / carrera | 34.50 | 82.80 | 30 | 3.26 | 2.11 | 3.04 | solo la columna cuasi-estática |
| `CintaRunning.mp4` | marcha / carrera | 26.26 | 56.16 | 0 | 0.00 | n/d | n/d | no (señal de fase, no ruido) |
| `Running.mp4` | marcha / carrera | 57.91 | 109.99 | 0 | 0.00 | n/d | n/d | no (señal de fase, no ruido) |
| `Running2.mp4` | marcha / carrera | 62.33 | 113.84 | 0 | 0.00 | n/d | n/d | no (señal de fase, no ruido) |
| `SentadillaProfunda.mp4` | bilateral simetrico | 4.92 | 13.38 | 53 | 28.96 | 3.67 | 14.48 | sí (movimiento bilateral simétrico) |

## 8. Coste de inferencia observado

Tiempo de `extract_pose_bgr_video` por fotograma (incluye conversión de color y reescalado a 640 px; excluye decodificación del contenedor y todo transporte de red). Es el componente de inferencia del presupuesto de latencia extremo a extremo, no la latencia extremo a extremo.

| Vídeo | Media (ms) | Mediana (ms) | p95 (ms) |
|---|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | 7.04 | 6.77 | 7.18 |
| `CintaRunning.mp4` | 6.64 | 6.60 | 6.85 |
| `Running.mp4` | 6.94 | 6.70 | 7.61 |
| `Running2.mp4` | 6.79 | 6.63 | 7.55 |
| `SentadillaProfunda.mp4` | 8.00 | 7.60 | 8.46 |

## 9. Artefactos generados

Cada figura tiene tres paneles en los clips largos: la serie completa (panorámica; en miles de fotogramas solo sirve para ver la envolvente y los huecos de detección), una **ventana de detalle de 5 s** tomada del centro del clip y sombreada en la panorámica, y la asimetría bilateral. En la ventana de detalle de los clips de carrera se aprecia con claridad que ambas piernas oscilan en oposición de fase, que es justo lo que hace inservible la asimetría como piso de ruido en ese régimen.

| Vídeo | Serie temporal (CSV) | Figura (PNG) |
|---|---|---|
| `5-00 por milha → 3-06-km.Agora...` | `validacion/resultados/series/5_00_por_milha_3_06_km_Agora_olha_o_que_acontece_quando_a_ge.csv` | `validacion/resultados/exp3_series_5_00_por_milha_3_06_km_Agora_olha_o_que_acontece_quando_a_ge.png` |
| `CintaRunning.mp4` | `validacion/resultados/series/CintaRunning.csv` | `validacion/resultados/exp3_series_CintaRunning.png` |
| `Running.mp4` | `validacion/resultados/series/Running.csv` | `validacion/resultados/exp3_series_Running.png` |
| `Running2.mp4` | `validacion/resultados/series/Running2.csv` | `validacion/resultados/exp3_series_Running2.png` |
| `SentadillaProfunda.mp4` | `validacion/resultados/series/SentadillaProfunda.csv` | `validacion/resultados/exp3_series_SentadillaProfunda.png` |

Columnas del CSV: `frame_index`, `timestamp_ms`, `pose_detectada`, `angulos_validos`, `left_knee_flexion_angle_deg`, `right_knee_flexion_angle_deg`, `left_knee_internal_angle_deg`, `right_knee_internal_angle_deg`, `bilateral_asymmetry_abs_deg`, las columnas de cada variante de coordenadas (`*_knee_flexion_world_deg`, `*_knee_flexion_img_xyz_iso_deg`, `*_knee_flexion_img_xy_iso_deg`, `*_knee_flexion_img_xyz_norm_deg`), `bilateral_asymmetry_world_abs_deg`, `cambio_escena_score`, `corte_de_plano`, `min_visibility_lower_limb`, `landmark_limitante`, `visible_ge_0_5`, `inferencia_ms`.

Al preparar el cotejo con Kinovea, revisar antes la columna `corte_de_plano`: un clip con cortes cambia de encuadre a mitad de la serie y los fotogramas de cada tramo no son comparables entre sí.

`frame_index` y `timestamp_ms` están pensados para el cotejo manual fotograma a fotograma con Kinovea: `timestamp_ms` es nominal (`frame_index * 1000 / fps` del contenedor), no el sello de tiempo de presentación real del contenedor. Para el cotejo conviene medir en Kinovea el ángulo interno cadera-rodilla-tobillo y convertirlo con `flexión = 180 - interno`, que es la convención del sistema.

## 10. Limitaciones

1. **Sin referencia externa.** No hay goniometría ni marcadores; nada aquí es exactitud. Las cotas de la sección 6 son de incertidumbre, no de error.
2. **Plano de cámara anotado a mano, no detectado.** La anotación de la tabla 2 la hizo el autor del experimento mirando un fotograma por clip: es suficiente para agrupar resultados, no para corregirlos. El sistema no detecta el plano y no compensa la oblicuidad de la toma.
3. **El ángulo de tres puntos no es flexión sagital pura.** Recoge también la oblicuidad del miembro en el plano frontal (p. ej. una postura con los pies separados), de modo que una lectura distinta de cero en bipedestación no implica necesariamente error del estimador.
4. **Componente `z` de los landmarks de imagen.** Su escala no es comparable a la de x/y y su incertidumbre es mayor; la sección 6 cuantifica el efecto, no lo corrige.
5. **Régimen por heurística de nombre de archivo**, no por anotación del autor.
6. **Muestra no probabilística:** un sujeto por clip y clips tomados del material de regresión del repositorio, no de un diseño muestral. Ninguna cifra generaliza a población.
7. **El techo de plausibilidad (150 grados) es un criterio conservador:** detecta lecturas imposibles, no las meramente erróneas. Un valor plausible puede seguir estando equivocado.
8. **Los tramos cuasi-estáticos se detectan sobre la propia serie estimada**, así que un tramo en el que el estimador se quedara congelado se clasificaría como cuasi-estático y rebajaría artificialmente el piso de ruido.
9. **El material de referencia no se grabó para medir.** Son vídeos editados o descargados, con cortes, rótulos y encuadres variables; sirven para caracterizar el comportamiento del sistema, no como protocolo de medición.
10. **El coste de inferencia depende de la máquina** (aquí, portátil Apple Silicon) y del reescalado interno a 640 px; no es extrapolable a otro hardware.

_Generado por `validacion/experimentos/exp3_estabilidad_temporal.py`._
