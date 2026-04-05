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

## Guía operativa (manual)

Procedimiento paso a paso para desarrolladores: **[`docs/guias/manual_aprendizaje_continuo_y_entrenamiento.md`](../guias/manual_aprendizaje_continuo_y_entrenamiento.md)**.

## Pruebas manuales

1. Configurar `DATABASE_URL`, ejecutar `alembic upgrade head`.
2. `AUTO_COLLECT_ENABLED=true`, ejecutar análisis con vídeo hasta ventana llena; verificar filas en `feature_samples`.
3. Aprobar muestras vía `PATCH` o UI Dev · Dataset.
4. Encolar job con Redis + worker Celery y dependencias `requirements-train.txt`.
5. `GET /models` y `POST .../activate` para cambiar modelo activo.
