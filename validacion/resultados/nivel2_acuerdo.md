# Nivel 2 - Acuerdo del sistema con video-goniometría manual (Tracker)

**Protocolo:** `docs/guias/protocolo_validacion_exactitud.md`, Nivel 2.
Fecha de ejecución: 2026-10-27 22:05:25.

Generado por `validacion/analisis/analizar_nivel2.py` a partir de los CSV listados abajo. Ningún valor de este informe se edita a mano: para corregirlo, se corrigen los CSV y se vuelve a ejecutar el script.

## Entradas

| Archivo | Filas | SHA-256 (12) |
| --- | --- | --- |
| Sistema: `validacion/datos/nivel2/IMG_6310/serie_sistema.csv` | 76 | `a53994b8f014` |
| Tracker, sesión 1: `validacion/datos/nivel2/IMG_6310/nivel2_tracker_sesion1.csv` | 76 | `6f3f33d57961` |
| Tracker, sesión 2: `validacion/datos/nivel2/IMG_6310/nivel2_tracker_sesion2.csv` | 26 | `b8f7ec776ddc` |

## Parámetros

| Parámetro | Valor |
| --- | --- |
| Vídeo del CSV del sistema | `IMG_6310.mov` (metadatos_exportacion.json) |
| Lado(s) medido(s) | izquierda |
| Convención de Tracker | `interno` (flexión = 180 - abs(valor)) |
| Criterio habilitante | MAE intra-observador <= 3.0 grados |
| n mínimo para MAE por tramo | 5 |
| Remedio (a), mediana de mediciones repetidas | no aplicado |

## 1. Criterio habilitante: error intra-observador (se evalúa primero)

Diferencia = sesión 2 - sesión 1, sobre los mismos fotogramas.

| Métrica | Valor |
| --- | --- |
| Fotogramas en la sesión 2 | 26 |
| Pares analizados (n) | 25 |
| MAE (grados) | 3.07 |
| Desviación estándar de las diferencias (grados) | 3.95 |
| Sesgo (grados) | +0.46 |
| Límites de acuerdo 95 % (grados) | [-7.29, +8.21] |
| ICC(2,1) | 0.997 (IC 95 % [0.993, 0.999]) |
| Separación mínima entre sesiones | 98.9 h |

**Veredicto del criterio habilitante: MAE = 3.07 grados frente a <= 3.0 grados -> NO CUMPLE.**

El comparador no alcanza la resolución exigida. Según el pre-registro (sección 2.6), la salida preelegida es (a) medir tres veces cada punto y usar la mediana (`--sesiones-extra`); si no se aplica, el Nivel 2 se declara **no concluyente** y la validación se apoya en el Nivel 1. Las cifras de la sección 2 se publican solo como descripción.

Figura: `nivel2_bland_altman_intraobservador.png`.

Pares descartados de la parte 1:

| Vídeo | frame_idx | Lado | Motivo | Observaciones |
| --- | --- | --- | --- | --- |
| IMG_6310.mov | 1430 | izquierda | sin valor de Tracker en la sesión 1 | Sin medicion propia en Tracker: no se recoloco el transportador (Tracker muestra el valor del fotograma anterior). Se deja vacio. |

## 2. Acuerdo sistema frente a Tracker (solo descriptivo: Nivel 2 no concluyente)

Referencia: sesión 1 de Tracker. Diferencia = sistema - Tracker (positivo: el sistema sobreestima la flexión).

### Resumen de acuerdo sistema-Tracker

| Métrica | Valor |
| --- | --- |
| Pares analizados (n) | 75 |
| Pares descartados (sin dato) | 0 |
| MAE (grados) | 8.13 |
| RMSE (grados) | 9.43 |
| Sesgo (grados) | -2.43 |
| IC 95 % del sesgo (grados) | [-4.54, -0.33] |
| Desviación estándar de las diferencias (grados) | 9.17 |
| Límites de acuerdo 95 % (grados) | [-20.41, +15.54] |
| ICC(2,1) | 0.978 (IC 95 % [0.965, 0.987]) |
| Interpretación ICC (Koo y Li 2016) | excelente |
| r de Pearson | 0.988 (p = 1.94e-60) |

#### Error por tramo angular de referencia

| Tramo (grados) | n | MAE | RMSE | Sesgo | Desv. tipica de las diferencias |
| --- | --- | --- | --- | --- | --- |
| [0, 30) | 34 | 6.78 | 7.92 | +5.71 | 5.57 |
| [30, 60) | 9 | 9.97 | 10.77 | -9.78 | 4.80 |
| [60, 90) | 9 | 14.18 | 14.77 | -14.18 | 4.37 |
| [90, 120) | 12 | 6.52 | 7.99 | -6.46 | 4.92 |
| [120, 180] | 11 | 7.61 | 8.30 | -7.61 | 3.49 |

#### Criterios de aceptación del Nivel 2 (pre-registro)

| Criterio | Umbral | Valor | Resultado |
| --- | --- | --- | --- |
| Habilitante: MAE intra-observador | <= 3.0 grados | 3.07 | **no cumple** |
| MAE sistema vs. Tracker | <= 7.0 grados | 8.13 | **no cumple** |
| ICC(2,1) | >= 0.85 | 0.978 | **cumple** |

El error intra-observador (MAE 3.07 grados) es la cota inferior del error detectable con este comparador: un MAE sistema-Tracker de ese orden es indistinguible de un acuerdo perfecto.

#### Estratificación por confianza del operador

1 = referencias óseas claras, 2 = dudosas, 3 = estimadas por oclusión.

| Confianza | n | MAE (grados) | Sesgo (grados) |
| --- | --- | --- | --- |
| sin anotar | 75 | 8.13 | -2.43 |

Figura: `nivel2_bland_altman.png`.

Pares descartados de la parte 2:

| Vídeo | frame_idx | Lado | Motivo | Observaciones |
| --- | --- | --- | --- | --- |
| IMG_6310.mov | 1430 | izquierda | sin valor de Tracker en la sesión 1 | Sin medicion propia en Tracker: no se recoloco el transportador (Tracker muestra el valor del fotograma anterior). Se deja vacio. |

## 3. Veredicto del Nivel 2

**no concluyente (criterio habilitante intra-observador no cumplido).**

Notas de alcance: Tracker, como Kinovea, es un segundo estimador con error propio; lo que se mide es acuerdo entre métodos, no exactitud. Se mide una sola pierna (la más cercana a la cámara) y solo flexión: la asimetría bilateral no se evalúa en este nivel. El CSV del sistema no incluye la `visibility` de los landmarks, por lo que no se condiciona el análisis a ella.
