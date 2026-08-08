# Spec: Aprendizaje continuo (admin / desarrollo)

## Meta

- **Estado:** Activo  
- **Alcance:** Rutas REST `/api/v1/dev/*`, tablas PostgreSQL, tarea Celery `train_exercise_classifier`, recolección automática de features en inferencia.  
- **Audiencia:** Administradores y desarrolladores del sistema (no usuarios finales).

## Resumen

El módulo permite **acumular vectores 32D** (`FeatureEngine.build_feature_vector`) etiquetados, **curarlos** vía API/UI y **entrenar** un clasificador RandomForest exportado a **ONNX**, actualizando `vision/models/manifest.json`. Opcionalmente se publica el artefacto en **Hugging Face Hub** (`HF_MODEL_REPO_ID`).

## Contrato REST

Todas las rutas bajo prefijo **`/api/v1/dev`**.

### Autenticación opcional

- Si `DEV_API_KEY` está definido en el servidor, las peticiones deben incluir cabecera **`X-Dev-API-Key`** con ese valor.
- Si no está definida, las rutas siguen protegidas por red/entorno (solo uso interno).

### Catálogo y estadísticas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/catalog` | Ejercicios desde `vision/data/exercise_catalog.json` + conteos de muestras + último `f1_per_class` del job completado más reciente. Requiere DB. |
| `GET` | `/samples/stats` | Conteos por etiqueta y `review_status`. |

### Muestras (`feature_samples`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/samples` | Query: `label`, `review_status`, `split`, `label_source`, `skip`, `limit`. |
| `GET` | `/samples/{id}` | Detalle incluye `feature_vector` completo. |
| `POST` | `/samples` | Body JSON: `{ "features": [32 floats], "label": "squat", "notes"?, "label_source"? }` |
| `PATCH` | `/samples/{id}` | `label`, `review_status` (`pending\|approved\|rejected`), `split` (`unset\|train\|val\|test`), `notes`. |
| `DELETE` | `/samples/{id}` | Elimina fila. |
| `POST` | `/samples/bulk-approve` | Body: `{ "ids": ["uuid", ...] }`. |

### Entrenamiento

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/training/jobs` | Body: `classes` (lista), `validation_fraction` (0.1–0.45), `set_active`, `push_hf`, `seed`, `n_estimators`. Encola Celery `train_exercise_classifier`. |
| `GET` | `/training/jobs` | Lista jobs. |
| `GET` | `/training/jobs/{id}` | Detalle + `metrics_json` (matriz de confusión, F1, etc.). |

### Modelos (manifest local)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/models` | Lista entradas de `manifest.json` y `active`. |
| `GET` | `/models/{key}` | Metadatos de una clave. |
| `POST` | `/models/{key}/activate` | Establece `active` en disco (`ModelRegistry.switch_version`). |

### Ingesta YouTube (`ingest_jobs`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/ingest/search` | Query: `q`, `limit`. Búsqueda con yt-dlp (metadatos, sin descarga). |
| `POST` | `/ingest/jobs` | Encola Celery `ingest_exercise_videos`. Body opcional: **`videos`**, lista de objetos con la misma forma que resultados de `/ingest/search` (`title`, `url`, `youtube_id`, etc.). Si `videos` no está vacía, se guarda en `ingest_jobs.videos_json` y el worker **no** vuelve a lanzar ytsearch, de modo que el lote coincide con la selección en la UI. Si se omite, el worker obtiene el lote con ytsearch como antes. |
| `GET` | `/ingest/jobs` | Lista jobs. Cada ítem incluye campos derivados de `metrics_json` agregado (`videos_processed`, `videos_failed`, `frames_read`, `features_extracted`, `samples_inserted`, etc.) para la UI. |
| `GET` | `/ingest/jobs/{id}` | Detalle + `videos_json` / `metrics_json`. |
| `GET` | `/ingest/video-usage` | Query: **`ids`** = lista de `youtube_id` separados por coma. Recorre los jobs más recientes (hasta `limit_jobs`, por defecto 150) y, para cada id solicitado, devuelve el **último** job en que ese vídeo apareció en `videos_json`, con campos `job_id`, `job_status`, `exercise_label`, `query`, fechas y métricas por vídeo si existen (`frames_read`, `features_extracted`, `samples_inserted`, `video_status`, `title`). Respuesta: `{ "items": { "<youtube_id>": { ... }, ... } }`. Pensado para marcar en la búsqueda si un resultado ya se ingestó. |
| `GET` | `/ingest/thumb` | Query: **`id`** = ID del vídeo YouTube. Proxy de `https://img.youtube.com/vi/{id}/mqdefault.jpg` con `Referer` adecuado; evita bloqueos del navegador al mostrar previews. Misma autenticación que el resto de `/dev`. La UI obtiene la imagen con `fetch` + cabecera `X-Dev-API-Key` (no con `<img src>` directo si hay clave). |

## Recolección automática en inferencia

- Variables: `AUTO_COLLECT_ENABLED` (bool), `AUTO_COLLECT_MIN_CONFIDENCE` (float, p. ej. 0.85).
- Requiere `DATABASE_URL` y migraciones con tablas `feature_samples`, `training_jobs`.
- Cuando la ventana de features está llena, la confianza supera el umbral, la etiqueta no es `unknown` y **no** hay `forced_exercise_label`, se inserta una fila `label_source=auto_soft`, `review_status=pending`.
- Puntos de enganche: `RealtimeEngineSession` tras clasificar; instanciación en `/ws/video`, `/ws/pose-stream`, `POST /api/v1/analyze/pose` vía `build_optional_feature_collector()`.

## Implementación (trazabilidad)

| Componente | Ruta |
|------------|------|
| ORM / migración | `backend/app/db/models.py`, `backend/alembic/versions/20260404_0001_*.py` |
| Collector | `backend/vision/feature_collector.py`, `backend/app/services/feature_sample_persist.py` |
| Motor | `backend/vision/realtime_engine.py` |
| Entrenamiento núcleo | `backend/vision/exercise_rf_train.py` |
| Celery | `backend/app/workers/training_tasks.py`, `backend/app/workers/celery_app.py` |
| HF Hub | `backend/app/services/hf_hub.py` |
| Routers | `backend/app/api/v1/dev/*.py`, `backend/app/api/v1/dev_router.py` |
| Frontend | `appWeb/src/pages/dev/*.tsx`, `appWeb/src/lib/devLearningApi.ts` |
| Config | `backend/app/config.py`, `backend/.env.example` |

## Incidencias y decisiones

1. **2026-08-07 — Sistema de validación rigurosa (GroupSplit + manifest v2); no activación del candidato**
   - **Cambio de contrato de métricas:** `train_rf_export_onnx` usa `vision/model_validation.py` (`GroupShuffleSplit` por `source_file`, herencia de `split` por grupo, MetricsBundle con `balanced_accuracy`, OOB+`oob_score_caveat`, ROC/PR-AUC, Brier, `unreliable_classes`). `merge_manifest` escribe `manifest_version: 2` + `metrics` / `training_params` / `dataset_snapshot`. `_load_approved_arrays` propaga `source_file` y `split`.
   - **API/UI:** listado de jobs expone `split_strategy`, `leakage_risk`, `balanced_accuracy`, `oob_score`, `unreliable_classes`; Training.tsx muestra aviso si hay clases unreliable y OOB como tooltip/caveat.
   - **Cap. 6:** `scripts/evaluate_exercise_classifier.py --mode kfold` (default) → window macro-F1 **0.242 ± 0.066**, video **0.328 ± 0.126** (k=5, 120 vídeos, 43120 ventanas).
   - **Criterio F5 (escrito antes del retrain):** macro-F1 group-split ≥ 0.70 + integridad de split. Candidato `exercise_rf_1fba912f` obtuvo macro-F1 **0.216** → **DO_NOT_ACTIVATE**. Activos siguen siendo `exercise_rf_ad157f19` / `exercise_validator_fe345eab` (métricas leaky históricas; no citarlas como generalización).
   - **Trazabilidad:** `docs/spec/model-validation-methodology.md`, `backend/vision/models/reports/f5_acceptance_criteria.json`, `f5_activation_decision.json`.

2. **2026-08-07 — Ronda de entrenamiento exhaustiva: 11 clases, ~43 120 muestras, 120 vídeos YouTube**
   - **Alcance:** simular "muchas rutinas grabadas" ampliando el catálogo de 5 a **11 clases** (`idle`, `squat`, `lunge`, `curl`, `running` + nuevas `pushup`, `plank`, `jumping_jack`, `overhead_press`, `deadlift`, `mountain_climber`) e ingerir bastantes más vídeos por clase que rondas previas.
   - **Ingesta:** `backend/scripts/batch_youtube_ingest_and_train.py` sobre Celery `ingest_exercise_videos`, `label_source=video_ingest`, `review_status=approved` (auto-aprobado). Se requirió antes corregir `backend/app/services/video/downloader.py` para forzar codec **H.264 (avc1)** en `yt-dlp` — varios vídeos servidos en AV1/VP9 daban `frames_read=0` con el build mínimo de ffmpeg de `opencv-python-headless`.
   - **Muestras aprobadas por clase (Postgres, `feature_samples`, tras limpieza de contaminación de smoke tests):**

     | Clase | Vídeos | Muestras |
     |-------|--------|----------|
     | `curl` | 9 | 2 965 |
     | `deadlift` | 17 | 6 911 |
     | `idle` | 7 | 1 739 |
     | `jumping_jack` | 12 | 4 034 |
     | `lunge` | 7 | 3 170 |
     | `mountain_climber` | 13 | 4 625 |
     | `overhead_press` | 14 | 5 515 |
     | `plank` | 11 | 4 047 |
     | `pushup` | 13 | 4 369 |
     | `running` | 8 | 2 708 |
     | `squat` | 9 | 3 037 |
     | **Total** | **120** | **43 120** |

   - **Clasificador activo (`exercise_rf_ad157f19`, RandomForest `n_estimators=50`):** holdout 20 % estratificado, `n_train=34 496`, `n_val=8 624` → **accuracy 0.9458**, **macro-F1 0.9520**. `f1_per_class`: idle 0.987, squat 0.971, lunge 0.984, curl 0.977, running 0.966, pushup 0.977, **plank 0.793** (el más bajo), jumping_jack 0.932, overhead_press 0.957, deadlift 0.974, mountain_climber 0.954. Se probaron también `n_estimators=250` (128 MB, excede el límite de 100 MB de GitHub LFS) y `n_estimators=100` (50 MB) con macro-F1 prácticamente idéntico; se activó la versión de 50 árboles (~25 MB) por ser la más liviana sin pérdida de desempeño.
   - **Validador ONNX (`exercise_validator_fe345eab`, `n_estimators=40`):** mismo dataset y split → accuracy 0.9455, macro-F1 0.9517 (ver `docs/spec/exercise-validator.md`). Artefacto de ~20 MB (se descartó una variante con `n_estimators=200`, ~60 MB, por tamaño sin ganancia relevante).
   - **⚠️ Limitaciones metodológicas (léase antes de citar estas métricas en la tesis):**
     1. **Split no agrupado por vídeo fuente.** Igual que en la ronda anterior (ver `docs/spec/model-validation-methodology.md`), el holdout 80/20 es aleatorio por ventana/fila, no por `source_file`. Con ventanas deslizantes de un mismo vídeo muy correlacionadas entre sí, el conjunto de validación probablemente contiene frames del mismo vídeo (misma persona, cámara, iluminación, ropa) que el de entrenamiento → las métricas reportadas son una **cota optimista**, no una medida de generalización a personas/cámaras nuevas.
     2. **Fuente única de datos (YouTube, tutoriales "forma perfecta").** No hay diversidad de errores de ejecución, biotipos ni ángulos de cámara reales de gimnasio; el modelo puede no generalizar a las condiciones de grabación reales de la tesis (cámara del portátil/celular del evaluador).
     3. **`plank` es la clase más débil (F1≈0.79 en ambos modelos)** por ser isométrica: se confunde parcialmente con `idle` (tronco erguido vs. horizontal, pero ambos sin ciclos) y con `overhead_press`/`pushup` en frames de transición. Es una limitación esperada del vector 32D actual, que captura postura y periodicidad de ventana pero no la ausencia total de movimiento de forma robusta.
     4. **Verificación E2E cualitativa, no cuantitativa.** Se corrieron 4 sesiones WS cortas (`/ws/pose-stream`, `capture_only=false`) contra vídeos gold (`SentadillaProfunda.mp4`, `Running.mp4`, `Running2.mp4`, `CintaRunning.mp4`, propios del repo, no usados en el entrenamiento): `Running.mp4`/`Running2.mp4` clasificaron `running` con confianza media ~0.92 y veredicto `confirm` en la mayoría de frames; `SentadillaProfunda.mp4` alternó `squat`/`unknown` (confianza media 0.665, `squat` solo en 32/183 frames tras llenarse la ventana de histéresis); `CintaRunning.mp4` quedó en `unknown` en el 100 % de los frames muestreados (confianza media 0.34) — posible **shift de dominio** entre el ángulo/iluminación de esta cinta y los vídeos de YouTube usados para entrenar `running`. Esto refuerza la limitación (1)-(2): el modelo generaliza mejor a vídeos similares a su fuente de entrenamiento que a grabaciones propias con condiciones distintas.
     5. **591 muestras `auto_validated/pending` contaminadas** por estas mismas sesiones de verificación E2E (con `AUTO_COLLECT_ENABLED=true`, cada frame confirmado por el validador se auto-persiste) se identificaron y **eliminaron** de `feature_samples` tras la verificación, para no ensuciar el dataset curado de cara a un futuro reentrenamiento.
   - **Trazabilidad:** `backend/vision/data/exercise_catalog.json`, `backend/vision/rep_trackers/{pushup,deadlift,overhead_press,jumping_jack}.py`, `backend/vision/rep_trackers/threshold_cycle.py`, `backend/vision/rep_tracker.py`, `backend/vision/equipment_detector.py`, `backend/app/services/video/downloader.py`, `backend/vision/models/manifest.json`, `backend/scripts/batch_youtube_ingest_and_train.py`, `backend/scripts/train_exercise_validator.py`, `docs/spec/exercise-catalog-external.md`, `docs/spec/exercise-validator.md`, `docs/spec/equipment-object-detection.md`.

3. **2026-08-07 — Parseo incorrecto de salidas ONNX (etiqueta fija en clase 0)**  
   - **Causa:** el runtime (`_try_onnx_classifier` en `backend/vision/exercise_classifier.py`) tomaba `out[0]` como logits, pero los modelos RandomForest de `skl2onnx` (`zipmap=False`) emiten `[output_label int64, output_probability float]`; el argmax de un tensor de etiqueta de 1 elemento siempre es 0 → **cualquier entrada se clasificaba como la primera clase** con confianza 1.0.  
   - **Mitigación:** el clasificador ahora selecciona el tensor **float con tantas columnas como clases** (probabilidades o logits con softmax) y usa el tensor entero solo como fallback de índice. Verificado E2E: `Running.mp4` pasó de `squat` (bug) a `running`.
4. **2026-08-07 — Modelos ONNX IR v11 ilegibles por el runtime**  
   - **Causa:** `onnxruntime<1.22` (fijado en requirements) soporta IR ≤ 10; los artefactos generados con `onnx>=1.18` usan IR 11 → `InferenceSession` fallaba y el motor caía silenciosamente al heurístico.  
   - **Mitigación:** `onnxruntime>=1.22,<2` en `backend/requirements.txt`. Además se añadieron `scikit-learn`, `skl2onnx` y `onnx` al requirements principal para que la imagen Docker del worker pueda entrenar (antes solo existían en el venv de desarrollo).
4. **2026-08-07 — `vision/models/` compartido entre backend y worker en Docker**  
   - **Causa:** el worker Celery escribía el `.onnx` y el `manifest.json` en su propio filesystem de contenedor; el backend no veía el modelo recién activado y los artefactos se perdían al recrear el contenedor.  
   - **Mitigación:** bind mount `./backend/vision/models:/workspace/backend/vision/models` en los servicios `backend` y `worker` de `docker-compose.yml`.
5. **2026-08-07 — Primer modelo multi-clase real activado (`exercise_rf_14bc169b`, squat/running)**  
   - Dataset: 139 muestras `squat` (`SentadillaProfunda.mp4`) + 1098 `running` (`Running.mp4`, `Running2.mp4`, `CintaRunning.mp4`), ingeridas con `_extract_and_insert` (ruta oficial de `ingest_tasks`), `label_source=video_ingest`, `review_status=approved`, con el **vector 32D nuevo** (F1-F5, ver [feature-vector-32d.md](feature-vector-32d.md)).  
   - Métricas holdout (20 %): accuracy 1.0, macro-F1 1.0, matriz de confusión `[[28,0],[0,220]]`. `set_active=true`. Los modelos previos de 1 clase quedan obsoletos (vector y parseo antiguos).

## Guía operativa (manual)

Procedimiento paso a paso para desarrolladores: **[`docs/guias/manual_aprendizaje_continuo_y_entrenamiento.md`](../guias/manual_aprendizaje_continuo_y_entrenamiento.md)**.

## Pruebas manuales

1. Configurar `DATABASE_URL`, ejecutar `alembic upgrade head`.
2. `AUTO_COLLECT_ENABLED=true`, ejecutar análisis con vídeo hasta ventana llena; verificar filas en `feature_samples`.
3. Aprobar muestras vía `PATCH` o UI Dev · Dataset.
4. Encolar job con Redis + worker Celery (las dependencias de entrenamiento ya están en `requirements.txt` / imagen Docker).
5. `GET /models` y `POST .../activate` para cambiar modelo activo.
