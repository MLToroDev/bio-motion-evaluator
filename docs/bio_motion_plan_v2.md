**BIO-MOTION EVALUATOR**

Plan de Arquitectura e Implementación

_Versión 2.0 - Con mejoras para producto_

Mateo Londoño Toro · Ingeniería en Software · Tecnológico de Antioquia

# **0\. Resumen Ejecutivo**

Este documento define la arquitectura híbrida y evolutiva del Bio-Motion Evaluator, integrando las decisiones técnicas necesarias para pasar del prototipo de análisis de rodilla a un sistema multi-ejercicio en tiempo real con capacidad de escalar como producto comercial.

El plan está organizado en cuatro fases progresivas. Las Fases 1-3 corresponden al alcance del trabajo de grado. La sección de Post-Lanzamiento documenta las decisiones de arquitectura que deben tomarse en Fase 1 para no bloquear el crecimiento futuro, aunque su implementación completa sea posterior.

**Principios rectores del plan:**

- Robustez sin complejidad innecesaria: cada módulo tiene una sola responsabilidad.
- Trazabilidad: cada decisión arquitectónica tiene una referencia cruzada al código.
- Extensibilidad: agregar un ejercicio nuevo no modifica código existente.
- Orientación a producto: las decisiones de Fase 1 no bloquean monetización ni multi-usuario.

# **1\. Estado Actual - Base Útil**

El sistema cuenta con los siguientes componentes funcionales que se preservan y extienden:

| **Componente**                 | **Archivo**                                             | **Estado**                   |
| ------------------------------ | ------------------------------------------------------- | ---------------------------- |
| Canal WebSocket video          | backend/app/routers/video.py                            | Activo - se extiende         |
| Canal WebSocket pose stream    | backend/app/routers/live_pose.py                        | Activo - se extiende         |
| Extractor de pose              | backend/app/services/mediapipe_service.py               | Activo - se encapsula        |
| Cálculo biomecánico inicial    | backend/vision/biomechanics.py                          | Activo - se integra al motor |
| Parser de payload WS (Flutter) | app/lib/pose/pose_ws_payload.dart                       | Activo - se extiende         |
| Pantalla de análisis en vivo   | app/lib/screens/live_analysis/live_analysis_screen.dart | Activo - se adapta           |

# **2\. Arquitectura Target**

## **2.1 Capas del Motor de Análisis**

La arquitectura target sigue un modelo de cinco capas desacopladas en el backend, con un contrato de datos unificado hacia el cliente Flutter:

| **Capa**                             | **Responsabilidad**                                                             | **Módulo backend**     |
| ------------------------------------ | ------------------------------------------------------------------------------- | ---------------------- |
| 1 - Pose Extraction                  | Extracción de landmarks 2D/3D por frame con MediaPipe                           | pose_extractor.py      |
| 2 - Temporal Buffer + Feature Engine | Ventanas deslizantes (1.5-3 s), velocidad angular, simetría, periodicidad       | feature_engine.py      |
| 3 - Exercise Classifier              | Clasificación del ejercicio con score de confianza por ventana                  | exercise_classifier.py |
| 4 - Rep State & Biomechanics         | Fases concéntrica/excéntrica, ROM objetivo, asimetrías, errores técnicos        | rep_tracker.py         |
| 5 - Streaming Contract               | Payload unificado hacia Flutter: etiqueta, confianza, fase, repeticiones, flags | realtime_engine.py     |

## **2.2 Regla de Límite para realtime_engine.py**

_REGLA CRÍTICA: realtime_engine.py es un orquestador delgado. Si supera 80 líneas de código, alguna lógica está en el lugar equivocado. Solo debe contener cuatro llamadas en secuencia: extractor → feature_engine → classifier → rep_tracker → emit_payload._

## **2.3 Interfaz Base RepTracker**

Cada ejercicio implementa esta interfaz. Agregar un ejercicio nuevo es crear un archivo nuevo, nunca modificar código existente:

class RepTracker(ABC):

@abstractmethod

def update(self, features: FeatureFrame) -> RepState: ...

@abstractmethod

def reset(self) -> None: ...

## **2.4 ExerciseClassifierConfig**

Centraliza los parámetros de decisión del clasificador. Vive en schemas.py o en un archivo de configuración propio:

| **Parámetro**      | **Tipo** | **Valor por defecto** | **Descripción**                                     |
| ------------------ | -------- | --------------------- | --------------------------------------------------- |
| min_confidence     | float    | 0.72                  | Umbral mínimo para activar un ejercicio             |
| window_size_frames | int      | 45                    | Tamaño de la ventana temporal (~1.5 s a 30 fps)     |
| hysteresis_frames  | int      | 10                    | Frames estables antes de cambiar la etiqueta activa |
| unknown_label      | str      | "unknown"             | Etiqueta cuando ningún ejercicio supera el umbral   |

## **2.5 Flujo Objetivo**

El pipeline end-to-end por frame sigue este orden estricto:

- FrameInput → MediaPipePoseExtractor (landmarks 2D/3D)
- Landmarks → TemporalWindowBuffer (acumula N frames)
- Buffer → FeatureEngine (velocidad angular, simetría, ROM, periodicidad)
- Features → ExerciseClassifier (etiqueta + confidence; aplica hysteresis)
- Etiqueta → RepStateTracker específico del ejercicio (fase + conteo + quality flags)
- Estado → UnifiedWSPayload → Flutter LiveUI

# **3\. Contrato WebSocket Unificado**

## **3.1 Payload por Frame (Servidor → Cliente)**

El payload se extiende con los campos del motor de ejercicios. Se agrega schema_version desde el día uno para detectar incompatibilidades silenciosas:

| **Campo**           | **Tipo**       | **Descripción**                                              |
| ------------------- | -------------- | ------------------------------------------------------------ |
| schema_version      | int            | Versión del contrato. Incrementar al añadir campos breaking. |
| frame_index         | int            | Índice del frame procesado                                   |
| server_ts_ms        | float          | Timestamp servidor (epoch ms) para medir latencia            |
| pose_ok             | bool           | True si MediaPipe detectó pose en el frame                   |
| landmarks           | array \| null  | Lista de puntos {index, x, y, z, visibility}                 |
| knees               | object \| null | Ángulos de rodilla (compatibilidad con flujo actual)         |
| exercise_label      | str            | Ejercicio detectado o 'unknown'                              |
| exercise_confidence | float          | Score de confianza 0.0-1.0 del clasificador                  |
| rep_phase           | str            | Fase actual: 'concentric' \| 'eccentric' \| 'hold' \| 'idle' |
| rep_count           | int            | Repeticiones completas en la sesión actual                   |
| quality_flags       | array\[str\]   | Lista de flags activos: 'asymmetry_high', 'rom_low', etc.    |
| pipeline_ms         | object \| null | Tiempos por etapa: {extract, feature, classify, track}       |

## **3.2 Coerción de Campos Nulos**

Regla heredada del contrato actual, extendida a los nuevos campos booleanos:

- include_preview: null → true (validator before en Pydantic)
- exercise_confidence: null → 0.0
- rep_count: null → 0
- quality_flags: null → \[\] (lista vacía, nunca null en cliente)

_En Flutter: usar ?? en todo campo del mapa JSON. Nunca asumir non-null sin operador de coalescencia._

# **4\. Modelo de Datos - Decisión Fase 1**

Aunque el sistema de sesiones completo se implementa en Fase 2, el schema de base de datos debe definirse en Fase 1. Cambiar la estructura de tablas después de tener datos reales tiene un costo alto.

## **4.1 Stack de Persistencia**

- Motor: PostgreSQL (no SQLite - no escala a multi-usuario ni multi-tenant)
- Migraciones: Alembic desde la primera tabla
- ORM: SQLAlchemy async (compatible con FastAPI)
- Storage de video/frames: bucket S3-compatible (MinIO en desarrollo local)

## **4.2 Schema Mínimo Fase 1**

Todas las tablas incluyen user_id desde el inicio, aunque auth sea un token fijo por ahora:

\-- Usuarios (stub en Fase 1, completo en Fase 2)

CREATE TABLE users (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

email TEXT UNIQUE NOT NULL,

created_at TIMESTAMPTZ DEFAULT NOW()

);

\-- Sesiones de análisis

CREATE TABLE sessions (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

user_id UUID REFERENCES users(id) ON DELETE CASCADE,

exercise_label TEXT NOT NULL,

started_at TIMESTAMPTZ DEFAULT NOW(),

ended_at TIMESTAMPTZ,

device_info JSONB

);

\-- Métricas resumidas por sesión

CREATE TABLE session_metrics (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,

rep_count INT,

avg_confidence FLOAT,

quality_score FLOAT,

flags_json JSONB,

created_at TIMESTAMPTZ DEFAULT NOW()

);

_Regla: nunca guardar landmarks crudos por frame en base de datos. Son voluminosos y su lugar es S3 (video original) o análisis offline. En DB solo van métricas resumidas._

# **5\. Estructura de Archivos Backend**

## **5.1 Módulos Nuevos en backend/vision/**

| **Archivo**            | **Responsabilidad**                                                                   | **Depende de**         |
| ---------------------- | ------------------------------------------------------------------------------------- | ---------------------- |
| pose_extractor.py      | Wrapper de mediapipe_service.py. Normaliza salida a FeatureFrame.                     | mediapipe_service.py   |
| feature_engine.py      | Normalización corporal + features temporales sobre ventana deslizante.                | pose_extractor.py      |
| exercise_classifier.py | Interfaz abstracta + implementación local ONNX/Torch + hysteresis.                    | feature_engine.py      |
| rep_tracker.py         | Clase base RepTracker (ABC) + implementaciones por ejercicio.                         | exercise_classifier.py |
| realtime_engine.py     | Orquestador < 80 líneas. Llama las 4 capas en orden.                                  | Todas las anteriores   |
| model_registry.py      | Carga dinámica de modelos ML por nombre y versión desde manifest JSON.                | exercise_classifier.py |
| pipeline_timer.py      | Mide latencia por etapa desde Fase 1. Emite dict {extract, feature, classify, track}. | Independiente          |

## **5.2 Extensiones en Módulos Existentes**

| **Archivo existente**            | **Cambio**                                                                  |
| -------------------------------- | --------------------------------------------------------------------------- |
| backend/app/routers/video.py     | Conectar realtime_engine en lugar de llamar mediapipe_service directamente. |
| backend/app/routers/live_pose.py | Ídem. Los routers quedan como thin wrappers de WebSocket.                   |
| backend/app/models/schemas.py    | Agregar UnifiedWSPayload, ExerciseClassifierConfig, PipelineTiming.         |

# **6\. Estructura Flutter - Cambios Relevantes**

## **6.1 Archivos Afectados**

| **Archivo**                                             | **Cambio**                                                                                              |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| app/lib/pose/pose_ws_payload.dart                       | Parsear campos nuevos: exercise_label, confidence, rep_phase, rep_count, quality_flags, schema_version. |
| app/lib/screens/live_analysis/live_analysis_screen.dart | Consumir exercise_label para construir List&lt;LiveMetric&gt; dinámicamente según ejercicio.            |
| app/lib/core/models/live_metric.dart                    | Sin cambios - modelo ya es agnóstico al ejercicio.                                                      |
| app/lib/pose/pose_overlay.dart                          | Colorear landmarks según quality_flags activos (p. ej. rojo en asimetría alta).                         |

## **6.2 Regla de Null-Safety en Flutter**

Todo campo nuevo del payload JSON debe parsearse con operador de coalescencia:

final label = map\['exercise_label'\] as String? ?? 'unknown';

final conf = (map\['exercise_confidence'\] as num?)?.toDouble() ?? 0.0;

final reps = (map\['rep_count'\] as int?) ?? 0;

final flags = (map\['quality_flags'\] as List&lt;dynamic&gt;?)?.cast&lt;String&gt;() ?? \[\];

# **7\. Telemetría de Latencia - Desde Fase 1**

La telemetría empieza en Fase 1 aunque solo loguee en consola. Sin medición temprana, es imposible saber dónde se perdió rendimiento durante el desarrollo.

## **7.1 PipelineTimer**

Un dataclass simple que se llena en cada etapa del pipeline:

@dataclass

class PipelineTiming:

extract_ms: float = 0.0 # tiempo de MediaPipe

feature_ms: float = 0.0 # tiempo del FeatureEngine

classify_ms: float = 0.0 # tiempo del Classifier

track_ms: float = 0.0 # tiempo del RepTracker

total_ms: float = 0.0 # suma total

## **7.2 Métricas de Éxito (Criterios de Aceptación)**

| **Métrica**                      | **Umbral objetivo**                             | **Cómo medirla**                                   |
| -------------------------------- | ----------------------------------------------- | -------------------------------------------------- |
| Latencia p95 end-to-end          | < 300 ms                                        | server_ts_ms vs timestamp recepción en Flutter     |
| Estabilidad de clase             | < 2 cambios espurios por minuto                 | Contar cambios de label en sesión de prueba        |
| Precisión F1 macro por ejercicio | \> 0.85 en dataset propio                       | Evaluación offline con videos tests/assets/videos/ |
| Tiempo de extracción MediaPipe   | < 50 ms por frame                               | pipeline_ms.extract en logs                        |
| Robustez ante oclusión parcial   | Clasificación estable con 30% landmarks ocultos | Test con oclusión artificial                       |

# **8\. Versionado de Modelos ML - ModelRegistry**

El clasificador no vive como un archivo hardcodeado. ModelRegistry permite actualizar el modelo sin redeploy:

## **8.1 Estructura del Manifest**

// backend/vision/models/manifest.json

{

"active": "exercise_classifier_v1",

"models": {

"exercise_classifier_v1": {

"path": "models/exercise_classifier_v1.onnx",

"classes": \["unknown", "squat", "shoulder_press", "bench_press"\],

"window_size": 45,

"created_at": "2025-01-01"

}

}

}

## **8.2 Interfaz de ModelRegistry**

class ModelRegistry:

def load_active(self) -> ExerciseClassifier: ...

def list_versions(self) -> list\[str\]: ...

def switch_version(self, name: str) -> None: ...

_Hugging Face se usa para entrenamiento, versionado de artefactos e inferencia offline. No es la ruta crítica en vivo - el modelo se descarga una vez y corre localmente._

# **9\. Plan de Implementación por Fases**

**FASE 1 - Fundamentos sin romper nada (Tesis - Sprint actual)**

**Motor de análisis (backend):**

- Crear pipeline_timer.py - logging de latencia por etapa desde el día uno
- Crear pose_extractor.py - wrapper de mediapipe_service.py
- Crear feature_engine.py - normalización y features temporales básicas
- Crear interfaz base RepTracker (ABC) con métodos update() y reset()
- Crear exercise_classifier.py - emite exercise_label='unknown' + confidence=0.0
- Crear realtime_engine.py - orquestador delgado (< 80 líneas)
- Crear model_registry.py - carga por manifest.json
- Conectar realtime_engine desde video.py y live_pose.py

**Contrato y datos (backend):**

- Extender schemas.py con UnifiedWSPayload (incluye schema_version=1)
- Agregar ExerciseClassifierConfig como dataclass en schemas.py
- Configurar PostgreSQL + Alembic - crear tablas users, sessions, session_metrics
- Configurar MinIO local como S3-compatible para storage de video
- Agregar user_id en todos los modelos de datos (stub auth: token fijo)

**Flutter (cliente):**

- Extender pose_ws_payload.dart para parsear todos los campos del UnifiedWSPayload
- Aplicar null-safety con ?? en todos los campos nuevos
- Adaptar live_analysis_screen.dart para construir métricas según exercise_label
- Mantener métricas de rodilla existentes como ejercicio 'squat' base

**Resultado de Fase 1:**

_El sistema emite exercise_label='unknown' con confianza 0.0. Las métricas de rodilla existentes siguen funcionando. La telemetría ya mide latencia. La base de datos ya existe con user_id en todos los registros._

**FASE 2 - MVP Multi-ejercicio (Tesis - Sprint siguiente)**

**Clasificador y ejercicios:**

- Grabar dataset propio: 3-5 ejercicios base en condiciones reales
  - Ejercicios mínimos: squat, shoulder_press, bench_press, triceps_extension, deadlift
  - Mínimo 50 repeticiones por ejercicio, 3 sujetos distintos
- Entrenar clasificador temporal (ONNX/Torch) en Hugging Face
- Integrar clasificador en exercise_classifier.py via ModelRegistry
- Implementar RepTracker concreto para cada ejercicio (state machine)
- Activar quality_flags por ejercicio: asimetría, ROM, velocidad, compensación

**Producto (infraestructura):**

- Auth real: JWT + OAuth2, desacoplado del resto del backend
- Historial de sesiones: endpoint GET /sessions con métricas por usuario
- Modelo de planes: definir límites por plan (sesiones/mes, ejercicios disponibles)
- API pública v1: versionar todos los endpoints bajo /api/v1/
- Multi-tenant base: row-level security en PostgreSQL por user_id

**Flutter:**

- Pantalla de historial de sesiones con métricas por ejercicio
- Pantalla de perfil de usuario (nombre, plan activo, estadísticas)
- Feedback post-sesión: resumen visual con peak-end rule (mejor ángulo + estado general)

**Resultado de Fase 2:**

_El sistema clasifica 3-5 ejercicios con F1 > 0.85 en dataset propio. Los usuarios tienen cuenta, historial y feedback post-sesión. La API está versionada para integraciones externas._

**FASE 3 - Robustez para Producción**

**Rendimiento y estabilidad:**

- Calibración por usuario/cámara: normalización de landmarks relativa al frame del usuario
- Smoothing temporal: filtro de Kalman o EMA sobre confidence para eliminar saltos
- Backpressure adaptativo: drop de frames cuando la cola supera umbral de latencia
- Validación continua: pipeline de evaluación offline con videos de tests/assets/videos/

**Privacidad y compliance:**

- GDPR mínimo: endpoint de exportación de datos del usuario + endpoint de borrado
- Retención de datos: política configurable (p. ej. sesiones > 12 meses se archivan)
- HIPAA base: si el sistema procesa datos clínicos, revisar con director de tesis

**Reentrenamiento continuo:**

- Pipeline de datos: anonimizar y agregar sesiones de usuarios al dataset de entrenamiento
- Consentimiento explícito: flag opt-in en perfil de usuario
- Versionado de modelos: cada reentrenamiento genera nueva versión en manifest.json

**Resultado de Fase 3:**

_El sistema es estable en condiciones reales: variaciones de iluminación, cámaras distintas, oclusiones parciales. La latencia p95 es < 300 ms. El modelo mejora con el uso real._

**POST-LANZAMIENTO - Decisiones que no bloquean si las tomas en Fase 1**

- SDK cliente: biblioteca para que terceros embeds el análisis en sus apps
- Dashboard para clínicas: vista multi-paciente con histórico y comparativas
- Análisis diferido: procesar videos subidos offline (no en tiempo real)
- Integración con wearables: complementar landmarks con datos de acelerómetro
- Exportación de reportes PDF por sesión para fisioterapeutas
- App móvil nativa: separar código IoT del código web en Flutter

# **10\. Trazabilidad Arquitectónica**

Para mantener trazabilidad entre decisiones y código (requerida para la defensa de tesis), cada archivo que implementa una decisión arquitectónica debe incluir un comentario en el encabezado:

\# ARCH-1: pose_extractor.py - Capa 1 del motor de análisis (ver plan sección 2.1)

\# ARCH-2: feature_engine.py - Capa 2, ventana temporal (ver plan sección 2.1)

\# ARCH-3: exercise_classifier.py - Capa 3 + ExerciseClassifierConfig (ver 2.4)

\# ARCH-4: rep_tracker.py - Interfaz base RepTracker (ver plan sección 2.3)

\# ARCH-5: realtime_engine.py - Orquestador < 80 líneas (ver plan sección 2.2)

\# ARCH-6: model_registry.py - Carga dinámica de modelos (ver plan sección 8)

\# ARCH-7: pipeline_timer.py - Telemetría desde Fase 1 (ver plan sección 7.1)

## **10.1 Tabla de TODOs Técnicos**

| **ID**   | **Tarea**                                                              | **Fase** | **Estado** |
| -------- | ---------------------------------------------------------------------- | -------- | ---------- |
| ARCH-T1  | Documentar contrato actual WS y puntos de extensión                    | 1        | Pendiente  |
| ARCH-T2  | Crear pose_extractor.py con interfaz pose → features                   | 1        | Pendiente  |
| ARCH-T3  | Crear feature_engine.py con ventana deslizante                         | 1        | Pendiente  |
| ARCH-T4  | Crear interfaz base RepTracker (ABC)                                   | 1        | Pendiente  |
| ARCH-T5  | Crear exercise_classifier.py (emite 'unknown' en Fase 1)               | 1        | Pendiente  |
| ARCH-T6  | Crear realtime_engine.py (orquestador < 80 líneas)                     | 1        | Pendiente  |
| ARCH-T7  | Crear model_registry.py con manifest.json                              | 1        | Pendiente  |
| ARCH-T8  | Crear pipeline_timer.py con PipelineTiming dataclass                   | 1        | Pendiente  |
| ARCH-T9  | Definir UnifiedWSPayload con schema_version en schemas.py              | 1        | Pendiente  |
| ARCH-T10 | Configurar PostgreSQL + Alembic + tablas base                          | 1        | Pendiente  |
| ARCH-T11 | Extender pose_ws_payload.dart con campos nuevos + null-safety          | 1        | Pendiente  |
| ARCH-T12 | Entrenar clasificador MVP (3-5 ejercicios) con dataset propio          | 2        | Pendiente  |
| ARCH-T13 | Implementar RepTracker concreto por ejercicio                          | 2        | Pendiente  |
| ARCH-T14 | Integrar auth JWT + OAuth2 desacoplado                                 | 2        | Pendiente  |
| ARCH-T15 | Versionar API pública bajo /api/v1/                                    | 2        | Pendiente  |
| ARCH-T16 | Implementar smoothing temporal (Kalman / EMA sobre confidence)         | 3        | Pendiente  |
| ARCH-T17 | Pipeline de reentrenamiento con datos de usuarios (con consentimiento) | 3        | Pendiente  |
| ARCH-T18 | Compliance GDPR mínimo: exportar + borrar datos de usuario             | 3        | Pendiente  |

# **11\. Principios de Cierre**

Este plan tiene una regla de oro: cada fase debe dejar el sistema en un estado funcional y demostrable. Nunca hay código a medias que bloquee la siguiente demo.

**Garantías de no regresión:**

- Fase 1 no rompe el análisis de rodilla existente - sigue funcionando como ejercicio 'squat'.
- Fase 2 no rompe el contrato WS - schema_version permite detectar incompatibilidades.
- Fase 3 no rompe la inferencia local - el smoothing es una capa encima, no un reemplazo.

**Señales de alerta a vigilar:**

- Si realtime_engine.py supera 80 líneas → mover lógica al módulo correspondiente.
- Si exercise_classifier.py contiene lógica de UI → está en el lugar equivocado.
- Si un router de FastAPI supera 50 líneas de lógica → extraer a servicio.
- Si Flutter parsea campos del payload en más de un archivo → consolidar en pose_ws_payload.dart.

_Mateo Londoño Toro · Bio-Motion Evaluator · 2025_