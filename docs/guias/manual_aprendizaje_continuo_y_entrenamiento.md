# Manual: entrenamiento del clasificador de ejercicios y módulo de aprendizaje continuo

**Audiencia:** administradores y desarrolladores del Bio-Motion Evaluator.  
**Contrato técnico detallado:** [`docs/spec/dev-learning-api.md`](../spec/dev-learning-api.md).  
**Protocolo de captura (cámara, etiquetas):** [`protocolo_captura_clasificacion_ejercicios.md`](protocolo_captura_clasificacion_ejercicios.md).

---

## 1. Qué se entrena y qué no

- El pipeline usa un vector fijo de **32 números** por instante (`FeatureEngine.build_feature_vector`), alineado con MediaPipe y la ventana temporal del motor.
- El artefacto entrenado es un **RandomForest** exportado a **ONNX**; el runtime lo carga si está registrado y activo en `backend/vision/models/manifest.json`.
- **MediaPipe y la extracción de pose no se entrenan aquí**; solo el clasificador que mapea features → etiqueta (`idle`, `squat`, `lunge`, etc., según las clases que definas).

Hay **dos caminos** complementarios:

| Camino | Cuándo usarlo |
|--------|----------------|
| **A. Script offline (CSV/JSONL)** | Dataset desde vídeos ya etiquetados (`export_features_from_video.py`), control total sin base de datos obligatoria para entrenar. |
| **B. Módulo Dev (API + UI + Celery)** | Curación en base de datos, jobs desde la web, activación de modelos y push opcional a Hugging Face. |

---

## 2. Requisitos comunes

### 2.1 Entorno Python (backend)

Desde la carpeta `backend/`:

```bash
pip install -r requirements.txt
```

Para **entrenar** (script o worker Celery):

```bash
pip install -r requirements-train.txt
```

### 2.2 Modelo de pose

Debe existir el landmarker `.task` configurado en `MEDIAPIPE_POSE_MODEL_PATH` (ver `docs/guias/SETUP.md` o `scripts/download_models.py`).

### 2.3 Variables útiles en `.env`

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | Obligatorio para el **módulo Dev** (tablas `feature_samples`, `training_jobs`). |
| `AUTO_COLLECT_ENABLED` | `true` para guardar automáticamente ventanas 32D durante inferencia (ver §5). |
| `AUTO_COLLECT_MIN_CONFIDENCE` | Umbral (p. ej. `0.85`) por debajo del cual no se inserta muestra automática. |
| `DEV_API_KEY` | Si se define, todas las peticiones a `/api/v1/dev/*` deben llevar cabecera `X-Dev-API-Key`. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis u otro broker para **encolar jobs** desde la UI. |
| `HF_API_TOKEN` | Token con permiso de escritura si usarás **push** a Hub. |
| `HF_MODEL_REPO_ID` | Repositorio modelo Hub en forma `usuario/nombre-repo` (opcional). |

---

## 3. Camino A — Entrenamiento offline (CSV / JSONL)

### 3.1 Generar filas desde vídeo

1. Coloca o referencia vídeos bajo `tests/assets/videos/` (según el script).
2. Ejecuta (ejemplo desde `backend/`):

```text
python scripts/export_features_from_video.py --video mi_clip.mp4 --label squat --out data/features_squat.csv --append
```

- Puedes usar **`--segments`** para etiquetar tramos por tiempo (ver `backend/scripts/examples/segments_example.json`).
- Opciones útiles: `--only-window-full`, `--require-pose-ok`, `--max-frames`.

Para lotes gold: `scripts/export_features_gold_batch.py` (etiquetas por JSON o heurística de nombre).

### 3.2 Entrenar y registrar ONNX

```text
python scripts/train_exercise_classifier_from_csv.py ^
  --csv data/mi_dataset.csv ^
  --out vision/models/exercise_rf_v1.onnx ^
  --classes idle,squat,lunge ^
  --write-manifest vision/models/manifest.json ^
  --manifest-model-key exercise_rf_v1 ^
  --set-manifest-active
```

- **`--classes`** debe listar **exactamente** las etiquetas presentes en el CSV (sin sorpresas).
- Sin `--set-manifest-active`, el modelo se añade al manifest pero el runtime sigue usando el heurístico si `active` sigue en `null`.
- Ajusta `--test-size`, `--n-estimators`, `--manifest-window-size` según necesidad (ventana debe coincidir con la usada al exportar features).

### 3.3 Comprobar en runtime

Reinicia la API. Con `active` apuntando a tu clave y el archivo `.onnx` en la ruta del manifest, `build_classifier()` usará ONNX (si no está desactivado en `feature_flags_json`).

---

## 4. Camino B — Módulo de aprendizaje continuo (dev)

### 4.0 Dónde está en la interfaz (importante)

**El entrenamiento no está dentro de «Análisis de video» ni «Análisis en vivo».** Esas pantallas solo consumen el modelo que ya tenga el servidor. El flujo de datos y entrenamiento vive aparte:

1. Abre el **menú lateral** (si está plegado, pulsa la flecha para mostrarlo).
2. Baja hasta la etiqueta pequeña **«Dev Tools»** (debajo de «Configuración»).
3. Ahí verás estos enlaces:
   - **Dev · Catálogo** → panorama por ejercicio.
   - **Dev · Dataset** → tabla de muestras (aprobar / rechazar).
   - **Dev · Fuentes de datos** → búsqueda YouTube, ingesta masiva a `feature_samples` (worker Celery + yt-dlp).
   - **Dev · Entrenamiento** → formulario **«Encolar entrenamiento»** (esto es el entrenamiento desde la web).
   - **Dev · Modelos** → activar qué ONNX usa el API.

También puedes ir desde **Inicio**: sección **«Desarrollo — aprendizaje del clasificador»**.

Las **miniaturas** de los resultados de búsqueda se cargan vía **`GET /api/v1/dev/ingest/thumb?id=<youtube_id>`** (el backend hace de proxy frente a `img.youtube.com`). La app usa `fetch` con tu **X-Dev-API-Key** y un blob local, porque un `<img src="...">` directo no puede enviar esa cabecera.

**URL directa:** `http://localhost:PUERTO/dev/training` (sustituye `PUERTO` por el de Vite, p. ej. 5173).

### 4.0.1 Flujo recomendado (orden de clics)

```text
Configuración → URL del API (+ X-Dev-API-Key si aplica)
       ↓
[Opcional] Análisis de video o en vivo con AUTO_COLLECT → genera muestras «pending» en DB
       ↓
Dev · Dataset → filtrar, corregir etiquetas, Aprobar (o carga manual vía API)
       ↓
Dev · Entrenamiento → clases = las que tienes aprobadas → Encolar entrenamiento
       (en otra terminal: Redis + `celery -A app.workers.celery_app worker ...` + `pip install -r requirements-train.txt`)
       ↓
Dev · Entrenamiento → Historial → comprobar estado completed / métricas
       ↓
Dev · Modelos → Activar el nuevo `exercise_rf_…` (si no marcaste «Activar al terminar» en el job)
       ↓
Reiniciar sesión de análisis o el servidor → ver «squat» / etiquetas nuevas en el HUD
```

Si abres **Dev · Entrenamiento** y al encolar aparece error, casi siempre falta **worker Celery**, **Redis**, o **`requirements-train.txt`** en el mismo Python del worker.

### 4.1 Puesta en marcha una sola vez

1. **PostgreSQL:** define `DATABASE_URL` en `.env`.
2. Migraciones:

```text
cd backend
alembic upgrade head
```

3. **Redis + Celery worker** (para botón “Entrenar” en la web):

```text
celery -A app.workers.celery_app worker --loglevel=info
```

(Ejecutar desde el entorno donde esté instalado `backend` con `requirements.txt` y **`requirements-train.txt`** en el mismo worker.)

4. **Frontend (`appWeb`):** en **Configuración** guarda la URL del API y, si el servidor tiene `DEV_API_KEY`, la misma clave en “X-Dev-API-Key”.

### 4.2 Navegación en la app (Dev Tools)

En el menú lateral:

| Ruta | Función |
|------|---------|
| **Dev · Catálogo** (`/dev/catalog`) | Vista por ejercicio del catálogo JSON + conteos de muestras y último F1 del último job completado (si existe). |
| **Dev · Dataset** (`/dev/dataset`) | Listar, filtrar, aprobar/rechazar muestras; aprobación masiva. |
| **Dev · Fuentes de datos** (`/dev/sources`) | Buscar en YouTube, elegir vídeos, encolar ingesta (descarga + extracción de features → DB). Historial y métricas por job. |
| **Dev · Entrenamiento** (`/dev/training`) | Encolar job Celery: clases, fracción de validación, activar modelo al terminar, push HF. |
| **Dev · Modelos** (`/dev/models`) | Listar entradas del `manifest.json` local y **activar** una versión. |

### 4.3 Flujo típico de trabajo

1. **Obtener datos**
   - *Automático:* con `AUTO_COLLECT_ENABLED=true`, durante análisis en vivo o por `/ws/pose-stream` y `/ws/video`, se insertan filas `label_source=auto_soft`, `review_status=pending`, solo si la ventana está llena, confianza ≥ umbral, etiqueta ≠ `unknown` y **no** hay `forced_exercise_label`.
   - *YouTube (bulk):* en **Dev · Fuentes de datos**, búsqueda + ingesta encolada (`ingest_exercise_videos`): descarga temporal, extracción de features, inserción con la etiqueta elegida. Requiere worker Celery con `yt-dlp` (incluido en `requirements.txt`).
   - *Manual / API:* `POST /api/v1/dev/samples` con vector 32D y etiqueta.
   - *Offline import:* puedes cargar datos generados por scripts si los insertas vía API o herramientas SQL (el formato es JSONB de 32 floats).
2. **Curar:** en **Dataset**, revisa `pending`, corrige etiqueta si hace falta y marca **approved** (o usa rechazar).
3. **Entrenar:** en **Entrenamiento**, indica la lista de **clases** que quieres incluir (deben existir muestras **approved** para esas clases; el worker filtra por ellas). Opciones:
   - **Activar al terminar:** escribe `active` en `manifest.json` apuntando al nuevo `exercise_rf_<uuid>`.
   - **Push a HF Hub:** requiere `HF_MODEL_REPO_ID` y `HF_API_TOKEN`.
4. **Ver métricas:** en el historial de jobs, expande un job completado para ver matriz de confusión y F1 por clase.
5. **Cambiar modelo sin reentrenar:** en **Modelos**, **Activar** otra clave ya registrada en el manifest.

**Importante:** las sesiones WebSocket ya abiertas siguen con el clasificador que cargaron al conectarse; para asegurar el nuevo modelo, reinicia análisis o la API según tu despliegue.

---

## 5. Recolección automática (detalle)

- Condiciones: `DATABASE_URL` configurada, migraciones aplicadas, `AUTO_COLLECT_ENABLED=true`.
- No sustituye la **curación**: las muestras automáticas entran como `pending` para evitar entrenar con errores del heurístico u ONNX actual.
- Si quieres **más** muestras automáticas, baja ligeramente `AUTO_COLLECT_MIN_CONFIDENCE` (con precaución: más ruido).

---

## 6. Hugging Face Hub (opcional)

1. Crea un repo modelo en [huggingface.co](https://huggingface.co), p. ej. `tu_usuario/bio-motion-exercise-classifier`.
2. En `.env`: `HF_MODEL_REPO_ID=tu_usuario/bio-motion-exercise-classifier` y `HF_API_TOKEN=...` (escritura).
3. Al encolar un job con **Push a HF Hub**, se suben el `.onnx` y un JSON de metadatos bajo `artifacts/`. El entrenamiento y la activación local del manifest **no dependen** del Hub; el Hub es copia de respaldo y trazabilidad.

---

## 7. Problemas frecuentes

| Síntoma | Qué revisar |
|---------|-------------|
| UI Dev devuelve 503 “DATABASE_URL” | Variable vacía o motor no iniciado; `alembic upgrade head`. |
| 401 en `/api/v1/dev/*` | Coincidir `DEV_API_KEY` con cabecera `X-Dev-API-Key` en Configuración (o quitar la clave en servidor solo en desarrollo controlado). |
| Job se queda en `pending` / error al encolar | Worker Celery no arrancado, Redis incorrecto, o falta `requirements-train.txt` en el worker. |
| Job `failed`: pocas muestras | Necesitas al menos **2** filas válidas `approved` con las clases pedidas. |
| Sigue saliendo “unknown” o baja confianza | Umbrales `CLASSIFIER_MIN_CONFIDENCE` / histérisis; datos mal balanceados; o mismatch de clases entre manifest y heurístico. |
| Target FPS alto pero ~14 FPS en vídeo pesado | Perfil automático del stream (`stream_tuning: auto`) puede capar FPS; ver `docs/spec/websocket-pose-stream.md` y opciones “Máximo rendimiento” / `stream_tuning: off`. |

---

## 8. Referencias rápidas en código

| Elemento | Ubicación |
|----------|-----------|
| Entrenamiento núcleo (ONNX) | `backend/vision/exercise_rf_train.py` |
| Script CLI | `backend/scripts/train_exercise_classifier_from_csv.py` |
| Export CSV desde vídeo | `backend/scripts/export_features_from_video.py` |
| Tarea Celery | `backend/app/workers/training_tasks.py` |
| Manifest | `backend/vision/models/manifest.json` |
| API dev | `backend/app/api/v1/dev/` |
| Cliente web | `appWeb/src/lib/devLearningApi.ts`, `appWeb/src/pages/dev/` |

---

*Última alineación con el repo: documento del mismo conjunto lógico que el spec `dev-learning-api.md`.*
