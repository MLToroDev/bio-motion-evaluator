# Reporte tecnico: retraso de frames en captura de movimiento

## Objetivo

Identificar que archivos y etapas estan involucrados en el retraso observado en la vista de analisis de video (frames que llegan, pero con delay), para revisarlo con el equipo de ingenieria.

## Flujo end-to-end (resumen)

1. Flutter envia config por WebSocket a `/ws/pose-stream`.
2. Backend lee frame desde `VideoSource` (OpenCV).
3. Backend ejecuta extraccion de pose (MediaPipe) en hilo worker.
4. Backend opcionalmente codifica preview JPEG y lo incluye en el payload.
5. Backend envia JSON por WebSocket.
6. Flutter decodifica/aplica el frame recibido y renderiza overlay.

## Archivos que participan directamente

### Frontend (Flutter)

- `app/lib/views/analysis/video/video_analysis_screen.dart`
  - Construye payload inicial (`source`, `video_filename`, `target_fps`, `include_preview`, `capture_only`, `diagnostics`, `preview_fps`, `preview_jpeg_quality`).
  - Procesa stream con `asyncMap` y aplica estado en `_applyServerFrame(...)`.
  - Decodifica preview y renderiza imagen de fondo + landmarks.
  - Envia ajustes "en caliente" de preview (`preview_fps`, `preview_jpeg_quality`).

- `app/lib/pose/pose_ws_payload.dart`
  - Parsea `pipeline_ms`, `frame_index`, `knees`, etc. para consumo en UI.

- `app/lib/utils/ws_uri.dart`
  - Construye URI de WebSocket para `/ws/pose-stream`.

### Backend (API y stream)

- `backend/app/routers/live_pose.py`
  - Orquesta el loop principal de `/ws/pose-stream` (productor en hilo + cola + consumidor async).
  - Sleep compensado respecto al presupuesto por frame (`target_fps`).
  - Ejecuta motor (`engine.process_bgr`) en `to_thread`.
  - Codifica preview JPEG en `to_thread` cuando toca stride.
  - Si `diagnostics: true`, añade `consumer_timing_ms` al JSON por frame.
  - Envia payload por WS.

- `backend/app/models/schemas.py`
  - Define `PoseStreamConfig` (incluye `target_fps`, `include_preview`, `capture_only`, `diagnostics`, `preview_fps`, `preview_jpeg_quality`).

- `backend/scripts/profile_pose_stream.py`
  - Conecta al WS, acumula métricas e imprime tablas (mean / p50 / p95 / max) para localizar cuellos de botella.

### Backend (motor de vision)

- `backend/vision/realtime_engine.py`
  - Pipeline por frame: extract -> (feature/classify/track si aplica) -> payload.
  - `inference_stride` permite saltar inferencias para bajar carga.
  - `analysis_enabled=False` deja solo captura de movimiento (sin clasificador/rep tracker).

- `backend/vision/pose_extractor.py`
  - Wrapper de extraccion de pose y calculo de rodillas.

- `backend/app/services/mediapipe_service.py`
  - Llama MediaPipe Pose Landmarker.
  - Hace downscale a `max_dim=640` antes de inferencia.
  - Es una de las etapas de mayor costo CPU.

- `backend/vision/processor.py`
  - `VideoSource` basado en OpenCV (`cv2.VideoCapture`) para leer frames.

- `backend/vision/pipeline_timer.py`
  - Reporta tiempos por etapa (`extract`, `feature`, `classify`, `track`, `total`) en `pipeline_ms`.

## Donde se genera el retraso (puntos criticos)

1. **Throttling explicito por target FPS**
   - En `live_pose.py` se hace `await asyncio.sleep(interval)` en cada iteracion.
   - Si `target_fps` es bajo o hay jitter, el stream entrega mas tarde por diseno.

2. **Tiempo de inferencia MediaPipe**
   - `engine.process_bgr(...)` depende de CPU y del modelo.
   - Si `extract_ms` sube por encima del presupuesto por frame, se acumula delay.

3. **Costo de codificar preview**
   - Resize + `cv2.imencode` + base64 en `live_pose.py`.
   - Mayor `preview_jpeg_quality` y mayor resolucion incrementan latencia.

4. **Decodificacion/render en navegador**
   - Flutter web tiene costo en parse/render de imagen + repaint.
   - Aunque llegue el payload, la pintura visual puede ir atrasada respecto al frame index.

5. **Ritmo de lectura de archivo**
   - `VideoSource.get_frame()` depende del codec del archivo y backend de OpenCV.
   - Videos pesados (bitrate alto, codecs complejos) pueden elevar tiempo de lectura.

## Metricas clave para diagnostico

- `pipeline_ms.total` (backend por frame): salud global del pipeline.
- `pipeline_ms.extract`: costo de MediaPipe.
- `server_wall_ms` (si se usa `/ws/video`): latencia real por frame del backend.
- `displayRxPerSec` en UI: ritmo real de mensajes procesados/renderizados.
- `consumer_timing_ms` (si `diagnostics: true` en el primer mensaje del WS): desglose en el consumidor del stream.

### Campos tipicos de `consumer_timing_ms`

| Campo | Significado |
|-------|-------------|
| `queue_wait_ms` | Tiempo esperando el siguiente frame en la cola (productor vs consumidor). |
| `process_bgr_ms` | Wall-clock del `to_thread(engine.process_bgr)` (MediaPipe + motor). |
| `jpeg_encode_ms` | Codificación preview JPEG en ese frame (0 si no toca stride o sin preview). |
| `wall_before_send_ms` | Tiempo desde inicio de iteración hasta justo antes de `send_json` (incluye cola + pose + jpeg + poll de control). |
| `residual_before_send_ms` | `wall_before_send` menos suma de queue + process + jpeg (overhead fino). |
| `scheduled_sleep_ms` | Tiempo que se va a dormir para respetar `target_fps` (throttle). |
| `frame_budget_ms` | `1000 / target_fps` (presupuesto nominal por frame). |

**Nota:** El coste real de `send_json` con un JPEG grande en base64 no va desgranado en un campo aparte; para aislarlo, comparar ejecuciones con `include_preview: false` vs `true` (el script lo permite con `--no-preview`).

## Script de agregacion

Desde `backend/` con el API levantado:

```bash
python scripts/profile_pose_stream.py --video RunningParcial.mp4 --fps 15 --max-frames 300
python scripts/profile_pose_stream.py --video RunningParcial.mp4 --no-preview --max-frames 300
```

En la app Flutter: activar **Diagnóstico servidor (timing)** antes de iniciar (envía `diagnostics: true`); puedes inspeccionar el JSON en el LOG o usar el script contra el mismo backend.

## Hipotesis principal para el caso reportado

Los frames "si llegan" pero "con retraso" suele indicar que no hay perdida de conectividad, sino **backpressure por costo de pipeline + render**, combinado con el control de ritmo (`target_fps`) y costo de preview JPEG.

## Recomendaciones de trabajo con el equipo

1. **Separar objetivos**
   - Mantener captura de movimiento en `capture_only=true`.
   - Dejar analitica avanzada para una fase posterior.

2. **Definir presupuesto por frame**
   - Ejemplo para 10 FPS: presupuesto total <= 100 ms.
   - Monitorear `pipeline_ms.total` y `extract`.

3. **Perf profile por combinacion**
   - Probar matriz:
     - `target_fps`: 8 / 10 / 12
     - `preview_fps`: 8 / 10 / 12
     - `preview_jpeg_quality`: 76 / 84 / 90
   - Registrar estabilidad visual y latencia percibida.

4. **Optimizar primero preview**
   - Si hay delay visual, bajar `preview_fps` antes que bajar `target_fps`.
   - Ajustar `preview_jpeg_quality` hasta balance nitidez/fluidez.

5. **Videos de prueba estandar**
   - Usar un set fijo de videos en `tests/assets/videos` para comparaciones consistentes.

## Lista corta de "archivos dueños" del problema

- UI/cliente: `app/lib/views/analysis/video/video_analysis_screen.dart`
- Router WS: `backend/app/routers/live_pose.py`
- Motor tiempo real: `backend/vision/realtime_engine.py`
- MediaPipe: `backend/app/services/mediapipe_service.py`
- Fuente de frames: `backend/vision/processor.py`
- Contrato WS: `backend/app/models/schemas.py`, `app/lib/pose/pose_ws_payload.dart`

## Proximo paso sugerido

Hacer una sesion de medicion de 10 minutos con el equipo usando este checklist:

- fijar 1 video de referencia;
- ejecutar `profile_pose_stream.py` con y sin `--no-preview`;
- correr 3 perfiles (8/10/12 preview FPS) si usas preview;
- documentar `pipeline_ms` y `consumer_timing_ms` (mean / p95) del script;
- anotar percepcion visual (sin negro, con negro leve, inestable);
- elegir preset base para desarrollo.
