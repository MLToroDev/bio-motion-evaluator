# Spec: Vector de features 32D (`FeatureEngine`)

## Meta

- **Estado:** Activo
- **Alcance:** Layout del vector de entrada al clasificador de ejercicio (heurístico y ONNX) y a `feature_samples`.
- **Código principal:** `backend/vision/feature_engine.py` (`FeatureEngine.build_feature_vector`), `backend/vision/biomechanics.py`
- **Última revisión:** 2026-08-07 (F1-F5: postura y velocidad de ventana en índices 21-31)

## Resumen

`FeatureEngine` mantiene una ventana deslizante de `PoseFrame` (por defecto 45 frames, `classifier_window_size_frames`) y produce un vector fijo de **32 floats**. Hasta 2026-08 los índices 21-31 eran padding de ceros; ahora contienen features posturales (F1-F4) y de velocidad de ventana (F5). La dimensión total no cambia: la entrada ONNX sigue siendo `[1, 32]`.

**Compatibilidad:** los modelos entrenados con el layout anterior reciben valores no nulos en dimensiones que antes eran 0; deben reentrenarse (dataset re-exportado) antes de activarse en producción. Los datasets CSV/`feature_samples` exportados antes de este cambio quedan obsoletos para entrenamiento nuevo.

## Contrato: layout de índices

| Índice | Nombre | Tipo | Descripción |
|--------|--------|------|-------------|
| 0 | `knee_flex_mean_l` | ventana | Media de flexión de rodilla izq. (grados × escala de calibración) |
| 1 | `knee_flex_mean_r` | ventana | Ídem derecha |
| 2 | `knee_flex_std_l` | ventana | Desviación estándar izq. |
| 3 | `knee_flex_std_r` | ventana | Ídem derecha |
| 4 | `knee_flex_min_l` | ventana | Mínimo izq. |
| 5 | `knee_flex_max_l` | ventana | Máximo izq. |
| 6 | `knee_flex_min_r` | ventana | Mínimo der. |
| 7 | `knee_flex_max_r` | ventana | Máximo der. |
| 8 | `knee_flex_delta_l` | mixto | Último frame − media (izq.) |
| 9 | `knee_flex_delta_r` | mixto | Último frame − media (der.) |
| 10 | `window_len` | meta | Nº de frames en la ventana (sin normalizar) |
| 11 | `pose_ok_ratio` | ventana | Fracción de frames con pose válida |
| 12 | `knee_asymmetry_pct` | frame | Asimetría % de flexión de rodilla del último frame |
| 13 | `knee_rom_l` | ventana | `max_l − min_l` |
| 14 | `knee_rom_r` | ventana | `max_r − min_r` |
| 15 | `periodicity` | ventana | Zero-crossings de la serie media bilateral (0-1) |
| 16 | `knee_vel_l_deg_s` | frame | Velocidad angular instantánea rodilla izq. |
| 17 | `knee_vel_r_deg_s` | frame | Ídem derecha |
| 18 | `elbow_vel_l_deg_s` | frame | Velocidad angular instantánea codo izq. |
| 19 | `elbow_vel_r_deg_s` | frame | Ídem derecha |
| 20 | `calibration_scale` | frame | Ancho hombros ref./actual, acotado [0.5, 2.0] |
| 21 | `trunk_incl_mean_deg` | ventana | **F1** — media de inclinación de tronco vs vertical (`trunk_inclination_angle_deg`) |
| 22 | `trunk_incl_rom_deg` | ventana | **F1** — ROM de inclinación de tronco |
| 23 | `base_support_ratio_mean` | ventana | **F2** — media de distancia tobillos ÷ ancho caderas (`base_of_support_ratio`) |
| 24 | `hip_flex_mean_l_deg` | ventana | **F3** — media flexión de cadera izq. (`hip_flexion_angles_from_landmarks`) |
| 25 | `hip_flex_mean_r_deg` | ventana | **F3** — ídem derecha |
| 26 | `hip_flex_rom_bilateral_deg` | ventana | **F3** — media de ROM de cadera L/R |
| 27 | `wrist_rel_height_mean_l` | ventana | **F4** — media altura muñeca izq. relativa al torso (`wrist_relative_heights`; 0 = cadera, 1 = hombro) |
| 28 | `wrist_rel_height_mean_r` | ventana | **F4** — ídem derecha |
| 29 | `knee_speed_mean_abs_deg_s` | ventana | **F5** — media de \|velocidad angular\| de rodilla (ambos lados) |
| 30 | `knee_speed_max_abs_deg_s` | ventana | **F5** — máximo de \|velocidad angular\| de rodilla |
| 31 | `elbow_speed_max_abs_deg_s` | ventana | **F5** — máximo de \|velocidad angular\| de codo |

Convenciones:

- Frames sin landmarks suficientes aportan `nan` a las series posturales; los agregados usan solo valores válidos y devuelven **0.0** si no hay ninguno (neutro documentado).
- Índices 0-1 y 4-9 están multiplicados por `calibration_scale` (comportamiento heredado, sin cambio).
- **Aceleración angular (F6):** no incluida — no quedan slots libres tras F1-F5. Requeriría ampliar `FEATURE_VECTOR_DIM` (breaking change de modelo).

## Implementación

| Pieza | Ruta |
|-------|------|
| Construcción del vector | `backend/vision/feature_engine.py` — `build_feature_vector`, `_posture_series` |
| Funciones biomecánicas F1-F4 | `backend/vision/biomechanics.py` — `trunk_inclination_angle_deg`, `base_of_support_ratio`, `hip_flexion_angles_from_landmarks`, `wrist_relative_heights` |
| Consumo heurístico | `backend/vision/heuristic_exercise_classifier.py` — `IDX_TRUNK_MEAN`, `IDX_BASE_RATIO`, `curl_isolation_score`, `idle_still_score` (F4/F5) |
| Export a CSV | `backend/scripts/export_features_from_video.py` |
| Persistencia DB | `backend/app/services/feature_sample_persist.py` (`feature_samples.feature_vector`) |

## Incidencias y decisiones

- **2026-08-07 — F1-F5 en slots de padding:** se eligió rellenar los índices 21-31 en lugar de ampliar la dimensión para no romper la forma de entrada `[1, 32]` del runtime ONNX (`backend/vision/exercise_classifier.py`). El modelo activo previo (`exercise_rf_a0eac3d7`, 1 clase) era degenerado, por lo que el impacto de valores no nulos en sus pesos es irrelevante; aun así, el flujo correcto es re-exportar dataset y reentrenar.
- La heurística usa F1/F2 con pesos bajos (0.08-0.12) y valor neutro 0.5 cuando la feature llega en 0.0 (datasets legados), para no desestabilizar el comportamiento previo.
- **2026-08-07 — Curl sentado vs squat:** el vector 0–20 está dominado por rodilla. Un curl sentado deja flexión ~90° **fija** (ROM y velocidad de rodilla bajos) y codo rápido (índice 31). `curl_isolation_score` + rescate en el wrapper ONNX (`_OnnxWithPostureRescue`, enter 0,55 / hold 0,38) evitan etiquetar squat/idle. Curl **unilateral**: muñeca y codo del lado activo (max L/R), no promedio. El RF activo no se reentrena aquí (F5).
- **2026-08-07 — Idle vs deadlift:** de pie quieto (rodillas extendidas, ROM/velocidad bajas, tronco erguido) se etiqueta `idle` si `idle_still_score` ≥ 0,62 y no hay curl. El RF leaky suele devolver `deadlift` en esa postura.

## Pruebas manuales

1. Desde `backend/`: exportar un vídeo gold y verificar que las columnas `f21`-`f31` tienen valores no nulos cuando hay pose válida:
   `python scripts/export_features_from_video.py --video SentadillaProfunda.mp4 --label squat --out data/squat_rows.csv --only-window-full --require-pose-ok`
2. En `/ws/video` o `/ws/pose-stream`, confirmar que la clasificación heurística sigue estable para squat/idle.
