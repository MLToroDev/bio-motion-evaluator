# Arquitectura del sistema

## Visión general

El **Bio-Motion Evaluator** sigue un diseño **web-first**:

- El **frontend operativo** es **React (`appWeb/`)**: análisis en vivo, análisis por vídeo, configuración y métricas en el navegador.
- La carpeta **`app/`** (Flutter) permanece como **código legado** del enfoque cross-platform inicial; **no** es el destino del desarrollo actual de la tesis.
- El **backend** (FastAPI) centraliza la lógica, streaming por WebSocket y modelos de visión (MediaPipe, extensible con Hugging Face).
- Los **dispositivos IoT** (ESP32-CAM o Raspberry Pi Zero 2W) envían video comprimido (p. ej. JPEG) al backend.

## Diagrama

```mermaid
flowchart TD
    subgraph iotLayer [Capa IoT]
        ESP32["ESP32-CAM / RPi Zero 2W"]
    end
    subgraph frontendLayer [Frontend activo]
        ReactAppWeb["React appWeb (navegador)"]
    end
    subgraph backendLayer [Backend - FastAPI]
        WS["WebSocket /ws/video"]
        PoseAPI["POST /api/v1/analyze/pose"]
        MediaPipeService["MediaPipe Service"]
        HFService["Hugging Face Service"]
    end

    ESP32 -->|"WebSocket frames"| WS
    ReactAppWeb -->|"HTTP / WebSocket"| PoseAPI
    WS --> MediaPipeService
    PoseAPI --> MediaPipeService
    MediaPipeService --> HFService
```

## Flujo de datos (resumen)

1. **Captura**: IoT o cámara del cliente obtiene frames.
2. **Transporte**: WebSocket binario o HTTP multipart según el caso.
3. **Inferencia**: MediaPipe Pose Landmarker en el backend; modelos HF opcionales para tareas de clasificación.
4. **Presentación**: **`appWeb/`** (React) muestra resultados y métricas al usuario.

### Motor de análisis (visión)

- **Vector de features 32D** (`vision/feature_engine.py`): rodilla (0-20), postura de ventana F1-F4 — tronco, base de apoyo, cadera, muñecas — (21-28) y velocidad angular de ventana F5 (29-31). Layout: [`docs/spec/feature-vector-32d.md`](spec/feature-vector-32d.md).
- **Clasificador** (`vision/exercise_classifier.py`): ONNX activo según `vision/models/manifest.json` (multi-clase: squat / lunge / idle / running) con fallback heurístico; envoltura de histéresis + EMA.
- **Validador / teacher** (`vision/exercise_validator.py`, opcional): segunda etapa sobre el mismo 32D (`confirm` / `reject` / `changed` / `uncertain`); teacher preferido **ONNX RF** (`vision/models/exercise_validator.onnx`, entrenable con `scripts/train_exercise_validator.py` desde muestras approved); fallback heurístico/margen. Campo WS `exercise_validation`; puede gatear `AUTO_COLLECT` (`auto_validated`). Spec: [`docs/spec/exercise-validator.md`](spec/exercise-validator.md).
- **Catálogo UI** (`GET /api/v1/exercises/catalog`): enriquecimiento con [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (nombre ES, equipo, GIF CDN). No detecta pose; solo presenta la etiqueta del motor.
- **Detección de objetos** (`vision/equipment_detector.py`, opcional): YOLO-World localiza mancuernas/barra/máquinas; cajas en `detected_objects` del WS y overlay `DetectedObjectsCanvas` en vivo y en análisis de vídeo (`appWeb`).
- **Rep tracking** (`vision/rep_tracker.py`): FSM genérica `ThresholdCycleTracker` parametrizable por señal/umbrales/fases; trackers concretos (`SquatRepTracker`, `ElbowCurlRepTracker`) registrados en `DEFAULT_TRACKER_FACTORIES`, fallback `UnknownRepTracker`.

### Aprendizaje continuo (administración)

- **PostgreSQL** almacena `feature_samples` (vectores 32D curados) y `training_jobs` (métricas de entrenamiento).
- Recolección opcional durante inferencia WebSocket/REST cuando `AUTO_COLLECT_ENABLED` y umbral de confianza.
- **Celery** ejecuta `train_exercise_classifier`: RandomForest → ONNX, fusiona `vision/models/manifest.json`, opcional **push** a Hugging Face Hub. En Docker, `vision/models/` es un bind mount compartido backend/worker.
- **React** expone rutas **`/dev/*`** (catálogo, dataset, entrenamiento, modelos) para desarrolladores; contrato en `docs/spec/dev-learning-api.md`.

### Despliegue local (Docker Compose)

El monorepo incluye un **`docker-compose.yml` en la raíz** que orquesta:

| Contenedor | Rol |
|------------|-----|
| `web` | Vite (`appWeb`) en desarrollo |
| `web-demo` | nginx con build de producción (perfil `demo`) |
| `backend` | FastAPI + MediaPipe |
| `worker` | Celery |
| `db` | PostgreSQL 16 |
| `redis` | Broker / backend de resultados Celery |

El navegador sigue apuntando a `http://localhost:8000` (puerto publicado). Spec: [`docs/spec/docker-compose-stack.md`](spec/docker-compose-stack.md).

---

## Arquitectura del panel de análisis en vivo

> **Nota:** esta subsección describe el panel **legado en Flutter** (`app/lib/.../live_analysis_screen.dart`). El desarrollo y la evolución de la UX de análisis en vivo deben hacerse en **`appWeb/`** (p. ej. `LiveAnalysisPage`, hooks de sesión WebSocket).

El panel inferior de `LiveAnalysisScreen` sigue un modelo **data-driven** para permitir múltiples tipos de ejercicio sin modificar los widgets de UI.

```
LiveAnalysisScreen (StatefulWidget)
│
│  _buildLiveMetrics(leftDeg, rightDeg) → List<LiveMetric>
│  ← punto de extensión por tipo de ejercicio
│
└─ LiveDashboardPanel (Dashboard + Module Tabs)
      ├─ TabBar: [MÉTRICAS] [LOG] [HISTÓRICO]
      ├─ MetricsPanel      ← recibe List<LiveMetric>, usa ListView
      ├─ LogPanel          ← recibe List<String>
      └─ HistoryPanel      ← recibe leftSeries / rightSeries
```

### Modelo `LiveMetric` (`core/models/live_metric.dart`)

Representa una métrica de movimiento de forma agnóstica al ejercicio:

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `label` | `String` | `"RODILLA IZQ."`, `"CADENCIA"` |
| `value` | `String` | `"127.3°"`, `"168 spm"` |
| `status` | `MetricStatus` | `good`, `warn`, `bad`, `neutral` |
| `sublabel` | `String?` | `"Objetivo: ≥ 130°"` |
| `icon` | `IconData?` | `Icons.fitness_center` |

### Extensibilidad

Para agregar un nuevo ejercicio (press banca, running, mancuerna…):
1. Implementar la lógica de cómputo de métricas en `live_analysis_screen.dart` dentro de `_buildLiveMetrics`.
2. Retornar una `List<LiveMetric>` con los datos del ejercicio.
3. Ningún widget de UI necesita modificarse.

---

## Convenciones de nomenclatura de widgets (live analysis)

| Widget | Responsabilidad |
|--------|----------------|
| `LiveAnalysisScreen` | Estado, cámara, WebSocket, construcción de `List<LiveMetric>` |
| `LiveDashboardPanel` | Orquestador del panel inferior (TabBar + TabBarView + CTA) |
| `MetricsPanel` | Tab MÉTRICAS: renderiza `List<LiveMetric>` con `ListView` |
| `LogPanel` | Tab LOG: muestra eventos frontend/backend |
| `HistoryPanel` | Tab HISTÓRICO: gráfica de series temporales |
| `CameraHUD` | Línea compacta de estado del servidor (frame, FPS, latencia) |
| `PoseOverlay` | `CustomPaint` de landmarks sobre `CameraPreview` |

