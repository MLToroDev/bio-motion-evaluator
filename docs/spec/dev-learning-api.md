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

1. **2026-08-07 — Parseo incorrecto de salidas ONNX (etiqueta fija en clase 0)**  
   - **Causa:** el runtime (`_try_onnx_classifier` en `backend/vision/exercise_classifier.py`) tomaba `out[0]` como logits, pero los modelos RandomForest de `skl2onnx` (`zipmap=False`) emiten `[output_label int64, output_probability float]`; el argmax de un tensor de etiqueta de 1 elemento siempre es 0 → **cualquier entrada se clasificaba como la primera clase** con confianza 1.0.  
   - **Mitigación:** el clasificador ahora selecciona el tensor **float con tantas columnas como clases** (probabilidades o logits con softmax) y usa el tensor entero solo como fallback de índice. Verificado E2E: `Running.mp4` pasó de `squat` (bug) a `running`.
2. **2026-08-07 — Modelos ONNX IR v11 ilegibles por el runtime**  
   - **Causa:** `onnxruntime<1.22` (fijado en requirements) soporta IR ≤ 10; los artefactos generados con `onnx>=1.18` usan IR 11 → `InferenceSession` fallaba y el motor caía silenciosamente al heurístico.  
   - **Mitigación:** `onnxruntime>=1.22,<2` en `backend/requirements.txt`. Además se añadieron `scikit-learn`, `skl2onnx` y `onnx` al requirements principal para que la imagen Docker del worker pueda entrenar (antes solo existían en el venv de desarrollo).
3. **2026-08-07 — `vision/models/` compartido entre backend y worker en Docker**  
   - **Causa:** el worker Celery escribía el `.onnx` y el `manifest.json` en su propio filesystem de contenedor; el backend no veía el modelo recién activado y los artefactos se perdían al recrear el contenedor.  
   - **Mitigación:** bind mount `./backend/vision/models:/workspace/backend/vision/models` en los servicios `backend` y `worker` de `docker-compose.yml`.
4. **2026-08-07 — Primer modelo multi-clase real activado (`exercise_rf_14bc169b`, squat/running)**  
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
