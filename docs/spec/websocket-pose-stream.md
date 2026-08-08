# Spec: WebSocket `/ws/pose-stream`

## Meta

- **Estado:** Activo  
- **Alcance:** Primer mensaje de configuración y mensajes por frame desde el backend FastAPI hacia el cliente **`appWeb/`** (React).  
- **Código principal:** `backend/app/api/websocket/live_pose.py`, `backend/vision/realtime_engine.py`, `backend/app/models/schemas.py`

## Resumen

El cliente abre un WebSocket en **`/ws/pose-stream`**, envía **un único mensaje de texto JSON** con la configuración (`PoseStreamConfig`), y el servidor responde con **mensajes JSON por fotograma** según el **contrato unificado v1**: motor (`exercise_label`, `rep_phase`, `rep_count`, `pipeline_ms`, …) más compatibilidad con `knees` y landmarks (ver `UnifiedWsFrameV1` en `schemas.py`). Vista previa JPEG opcional sin cambios. Fuentes: archivo gold, cámara OpenCV del servidor, o **URL** (RTSP/HTTP o página YouTube resuelta a stream H.264 **sin descargar** el MP4).

Análisis **REST** de una sola imagen con el mismo motor: **`POST /api/v1/analyze/pose`** (ver [api-v1-rest.md](api-v1-rest.md)).

## Contrato: mensaje inicial (cliente → servidor)

Tipo: **texto** UTF-8, objeto JSON.

| Campo | Tipo | Obligatorio | Notas Mín. | Máximo |
|-------|------|-------------|------------|--------|
| `source` | string | no | `"file"` (defecto) | literal `camera` \| `file` \| `url` |
| `video_filename` | string \| null | si `source=file` | nombre bajo `tests/assets/videos/` | — |
| `device_index` | number | no | 0 (cámara) | — |
| `stream_url` | string \| null | si `source=url` | RTSP/HTTP(S) **o** página YouTube (`watch` / `shorts` / `youtu.be`) | YouTube: yt-dlp extrae URL de media (H.264/`avc1`) **sin descarga**; OpenCV lee el stream. RTSP/HTTP se pasan tal cual. |
| `target_fps` | number | no | 15 | 0.5–60 |
| `include_preview` | bool \| null | no | `true` | Coerción: ver abajo |
| `forced_exercise_label` | string \| null | no | `null` | Fija la etiqueta de ejercicio (omite clasificador; confianza 1.0) |
| `equipment_label` | string \| null | no | `null` | Metadato de equipamiento declarado (p. ej. `barbell`, `dumbbell`, `bodyweight`); normalizado a minúsculas; **no altera el motor**, se ecoa por frame |

### Coerción de `include_preview` (servidor)

Los clientes (p. ej. Flutter Web) pueden serializar **`null`** para flags booleanos.

- **Regla:** `null` se interpreta como **`true`** (alineado con el default del modelo Pydantic).
- **Implementación:** `field_validator` con `mode="before"` en `PoseStreamConfig.include_preview` (`backend/app/models/schemas.py`).

### Ejemplo mínimo (vídeo archivo)

```json
{
  "source": "file",
  "video_filename": "squat_test.mp4",
  "target_fps": 12,
  "include_preview": true
}
```

### Ejemplo YouTube (streaming, sin MP4 local)

```json
{
  "source": "url",
  "stream_url": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "target_fps": 12,
  "include_preview": true
}
```

## Contrato: mensajes por frame (servidor → cliente)

Tipo: **texto** JSON por mensaje.

Campos habituales:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `schema_version` | int | Versión del contrato (v1 = **1**). Incrementar ante cambios breaking. |
| `frame_index` | number | Índice entero del frame |
| `pose_ok` | bool | Resultado de detección (ver `PoseResult` en servicio MediaPipe) |
| `note` | string \| null | Nota humana (p. ej. sin pose) |
| `landmarks` | array \| null | **Subconjunto** de puntos detectados con `visibility` suficiente: `{ index, x, y, z, visibility? }`. No se garantizan 33 entradas; el cliente debe usar `index` (p. ej. `PoseSkeletonCanvas` en `appWeb`). Umbral servidor: `pose_landmark_min_visibility_response` / env `POSE_LANDMARK_MIN_VISIBILITY_RESPONSE` (**defecto 0,25**; 0 = sin filtro). Overlay `appWeb` dibuja con `MIN_VIS=0.12`. |
| `world_landmarks` | array \| null | Misma política: solo índices presentes en `landmarks` filtrados. |
| `knees` | object \| null | Ángulos; p. ej. `left_knee_flexion_angle_deg`, `right_knee_flexion_angle_deg` (grados) |
| `exercise_label` | string | Clasificación actual (`unknown` en Fase 1 sin ONNX) |
| `exercise_confidence` | number | Confianza 0–1 (suavizada EMA en servidor) |
| `rep_phase` | string | `idle` \| `eccentric` \| `concentric` \| `hold` (según `RepTracker` activo) |
| `rep_count` | int | Repeticiones completas en la sesión del WebSocket |
| `quality_flags` | array[string] | Flags p. ej. `asymmetry_high`, `rom_low` |
| `pipeline_ms` | object \| null | Tiempos por etapa: `extract`, `feature`, `classify`, `track`, `total` |
| `total_frames` | number \| null | Total de fotogramas cuando la fuente es finita (`file` o VOD YouTube) y OpenCV reporta `CAP_PROP_FRAME_COUNT` fiable; `null` en cámara, RTSP/live o códec sin metadatos. |
| `server_ts_ms` | number | Marca de tiempo del servidor (epoch ms) al enviar el mensaje; útil para estimar latencia red + procesamiento. |
| `equipment_label` | string | **Presente** si el cliente declaró equipo o el detector de objetos infiere un slug: eco como metadato. |
| `detected_objects` | array | Opcional: objetos detectados `{label, label_es, confidence, bbox_norm:[x1,y1,x2,y2], equipment_slug?}`. Ver [equipment-object-detection.md](equipment-object-detection.md). |
| `exercise_validation` | object | Opcional: veredicto del teacher `{verdict, primary_label, validator_label, confidence, score_margin, reason, ...}`. Ver [exercise-validator.md](exercise-validator.md). |
| `preview_jpeg_base64` | string | Presente solo si `include_preview` era truthy en la config; JPEG en Base64 |

### Fin de stream (`source=file` o VOD YouTube)

Cuando la fuente es **finita** (`VideoSource.finite`: archivo gold o YouTube VOD resuelto), al agotarse los frames el servidor **deja de enviar fotogramas**, envía un último JSON con **`stream_done`: `true`** (junto a `frame_index`, `total_frames`, `server_ts_ms`) y **cierra el WebSocket** con código **1000**. El cliente debe dejar de tratar el canal como “en análisis”.

Cámaras OpenCV, RTSP/HTTP en vivo y YouTube **live** (`is_live`) no son finitos: un `None` de lectura se reporta como `error: sin_frame` y el canal sigue abierto.

**Nota:** En `vision/processor.py`, `VideoSource` para fuente finita **no rebobina** al inicio por defecto (`loop_file=False`). Si en el futuro se necesita bucle para regresión, instanciar `VideoSource(..., loop_file=True)` o exponer un flag en `PoseStreamConfig`.

### Mensaje de error operativo

Puede incluir **`error`** (string), p. ej. `sin_frame`, o cierre con código HTTP WS y cuerpo JSON según `live_pose.py`.

## Implementación

| Pieza | Ruta |
|-------|------|
| Filtro visibility → JSON | `backend/vision/landmark_filter.py`, `backend/vision/unified_payload.py` |
| Router WS | `backend/app/api/websocket/live_pose.py` |
| Motor tiempo real | `backend/vision/realtime_engine.py` — `RealtimeEngineSession` |
| Resolución YouTube → stream | `backend/app/services/video/downloader.py` — `resolve_playable_stream` (`download=False`) |
| Captura OpenCV | `backend/vision/processor.py` — `VideoSource` (`finite`, cabeceras HTTP) |
| Contrato documentado | `backend/app/models/schemas.py` — `UnifiedWsFrameV1`, `ExerciseClassifierConfig` |
| Modelo config | `backend/app/models/schemas.py` — clase `PoseStreamConfig` |
| URI cliente | `appWeb/src/lib/wsUri.ts` — `buildPoseStreamWebSocketUri` |
| Pantalla de análisis | `appWeb/src/pages/VideoAnalysis/` (`ConfigPanel` fuente YouTube → `source=url`) |

## Incidencias y decisiones

1. **Pydantic rechazaba `include_preview: null`**  
   - **Causa:** tipo `bool` estricto sin aceptar JSON `null`.  
   - **Mitigación:** validador `before` que mapea `None → True` y demás valores con `bool(v)`.

2. **Flutter Web — `TypeError: null is not a subtype of bool`** (traza apuntando al payload o al estado del switch)  
   - **Contexto:** estado/`include_preview` en escenarios de hot reload o valores nulos en la frontera.  
   - **Mitigación cliente:** `_includePreview` como `bool?` y uso de **`?? true`** al construir JSON del primer mensaje y al enlazar `SwitchListTile.value` (ver spec Flutter).

3. **2026-08-07 — `equipment_label` manual (extensión compatible)**  
   - Se replica el patrón `forced_exercise_label`: campo opcional en `PoseStreamConfig` (y en el primer mensaje de `/ws/video`), pasa por `RealtimeEngineSession` y se incluye en `build_frame_payload_v1` solo si fue declarado. Cliente `appWeb`: selector «Equipamiento» en `ConfigPanel` (`appWeb/src/pages/VideoAnalysis/components/ConfigPanel.tsx`, tipo `EquipmentLabel`).  
   - Decisión: etiqueta **manual** (sin detector visual, YOLO descartado en Fase 1); sirve como ground truth para un futuro clasificador de equipamiento.

4. **2026-08-07 — YouTube en `/ws/pose-stream` sin descarga**  
   - **Decisión:** no bajar el MP4 a disco para análisis interactivo. `stream_url` con página YouTube se resuelve con yt-dlp (`extract_info`, `download=False`, preferencia `vcodec^=avc1`) y OpenCV lee el HTTP(S) resultante, mismo pipeline que cámara/archivo. VOD → `VideoSource.finite=True` + `stream_done`. Live/RTSP → no finitos.  
   - **Por qué no iframe en el navegador:** el iframe no entrega píxeles al motor; el análisis debe correr sobre frames BGR en el servidor.  
   - **Ingesta / entrenamiento** sigue usando `download_video` (archivo local) en Celery; es un flujo distinto (dataset, no demo en vivo).  
   - **Riesgo:** URLs firmadas de YouTube caducan; si OpenCV no abre el stream (AV1-only, geo-block, edad), el WS cierra con error. Preferir H.264. Si el stream falla, respaldo: descarga H.264 a `data/downloads`.

5. **2026-08-07 — Esqueleto a un brazo + curl unilateral que se “suelta”**  
   - **Causa overlay:** umbral de visibilidad 0,5 (servidor) + 0,4 (canvas) ocultaba el brazo ocluido/lejos en curl sentado.  
   - **Causa etiqueta/reps:** promedio bilateral de codo + histéresis corta: al extender un brazo la señal cae y el clasificador pasa a `unknown`/`idle`.  
   - **Mitigación:** `POSE_LANDMARK_MIN_VISIBILITY_RESPONSE=0.25`, `PoseSkeletonCanvas` `MIN_VIS=0.12`, `dominant_elbow_flexion` en `ElbowCurlRepTracker`, hold de `unknown` (~24 frames) y enter/hold de `curl_isolation_score` (0,55 / 0,38) con compuerta de tronco (no confundir push-up).

6. **2026-08-07 — `youtu.be?si=` no abre en OpenCV**  
   - **Causa:** el contenedor recargó código viejo (`VideoSource("url", file_path=página HTML)`). OpenCV no lee `youtu.be?si=…`.  
   - **Mitigación:** `normalize_youtube_url` → `watch?v=`; stream yt-dlp; si falla, descarga H.264 a `data/downloads`.

## Pruebas manuales sugeridas

1. Backend en `localhost:8000`, modelo descargado si aplica.  
2. `appWeb` → Análisis de vídeo → Tipo de fuente **YouTube** → pegar `https://www.youtube.com/watch?v=…` → Iniciar.  
3. Comprobar preview JPEG + `exercise_label` / rodillas en tiempo (semi-)real; al terminar el VOD, `stream_done` y cierre 1000.  
4. Con archivo gold: mismo panel, fuente «Vídeo en servidor». Con y sin “Vista previa desde servidor”, comprobar presencia/ausencia de `preview_jpeg_base64`.

