# Auditoría y plan: fuente de video «cámara PTZ externa»

**Alcance:** solo lectura. Sin cambios de código.  
**Fecha:** 2026-07-10

---

## Parte 1 — Auditoría del estado actual

### 1.1 Selección de fuente en `/ws/pose-stream`

**Punto de entrada:** el router WebSocket `pose_stream` en `backend/app/api/websocket/live_pose.py`. Tras `accept`, valida el primer mensaje JSON como `PoseStreamConfig` y construye la fuente con `_build_video_source(cfg)`:

```77:91:backend/app/api/websocket/live_pose.py
def _build_video_source(cfg: PoseStreamConfig) -> VideoSource:
    if cfg.source == "camera":
        return VideoSource("camera", device_index=cfg.device_index)
    if cfg.source == "file":
        if not cfg.video_filename:
            raise ValueError("video_filename es obligatorio cuando source='file'")
        path = resolve_gold_standard_video(cfg.video_filename, settings.gold_standard_videos_dir())
        if not path.is_file():
            raise FileNotFoundError(f"No existe el vídeo: {path}")
        return VideoSource("file", file_path=str(path))
    if cfg.source == "url":
        if not cfg.stream_url:
            raise ValueError("stream_url es obligatorio cuando source='url'")
        return VideoSource("url", file_path=cfg.stream_url)
    raise ValueError(f"Fuente no soportada: {cfg.source}")
```

**Abstracción de captura:** `VideoSource` en `backend/vision/processor.py`. Las tres fuentes usan **`cv2.VideoCapture`**:

| `source_type` | Apertura | Notas |
|---------------|----------|-------|
| `camera` | `cv2.VideoCapture(device_index)` | `CAP_PROP_BUFFERSIZE = 1` (best-effort) |
| `file` | `cv2.VideoCapture(file_path)` | `total_frame_count` si OpenCV reporta `FRAME_COUNT` fiable |
| `url` | `cv2.VideoCapture(file_path)` donde `file_path` es la URL RTSP/HTTP | Sin `CAP_PROP_BUFFERSIZE` |

```36:61:backend/vision/processor.py
        if source_type == "camera":
            self._cap = cv2.VideoCapture(device_index)
            # Cola de captura mínima (donde el backend lo permite): evita acumular
            # fotogramas viejos cuando el procesamiento va más lento que la cámara.
            try:
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:  # noqa: BLE001 — propiedad opcional según driver
                pass
            log.info("VideoSource: cámara índice %s", device_index)
        elif source_type == "file":
            ...
            self._cap = cv2.VideoCapture(file_path)
        elif source_type == "url":
            ...
            self._cap = cv2.VideoCapture(file_path)
            log.info("VideoSource: URL/stream %s", file_path)
        ...
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente: {source_type} {file_path!r}")
```

**Arquitectura producer-consumer:** un hilo bloqueante (`_read_frames_blocking`) lee frames y los deposita en una `asyncio.Queue`; el consumer async procesa y envía por WS (`live_pose.py:120-149`, `249-398`).

**Lectura de frames:**

```86:103:backend/vision/processor.py
    def get_frame(self) -> np.ndarray | None:
        """Lee un frame BGR. Devuelve None si la fuente falla (excepto archivo en loop)."""
        ...
        ok, frame = self._cap.read()
        if ok and frame is not None:
            return frame

        if self.source_type == "file":
            if self._loop_file:
                ...
            return None

        log.warning("VideoSource: fallo al leer frame (%s)", self.source_type)
        return None
```

Para `url` (y `camera`), **un fallo de `read()` termina el productor** (no hay reintento ni rebobinado):

```137:144:backend/app/api/websocket/live_pose.py
        while not stop_event.is_set():
            frame = source.get_frame()
            ...
            if frame is None:
                break
```

---

### 1.2 Contrato `PoseStreamConfig` (Pydantic)

Definido en `backend/app/models/schemas.py`:

```112:187:backend/app/models/schemas.py
class PoseStreamConfig(BaseModel):
    """
  ...
    - ``url``: cadena RTSP/HTTP en ``stream_url``.
    """

    source: Literal["camera", "file", "url"] = "file"
    video_filename: str | None = Field(...)
    device_index: int = 0
    stream_url: str | None = None
    target_fps: float = Field(default=15.0, ge=0.5, le=60.0)
    max_throughput: bool = Field(default=False, ...)
    stream_tuning: StreamTuningMode = Field(default="auto", ...)
    include_preview: bool = Field(default=True, ...)
    preview_fps: Literal[8, 10, 12] = Field(default=10, ...)
    preview_jpeg_quality: int = Field(default=84, ge=70, le=90, ...)
    capture_only: bool = Field(default=False, ...)
    forced_exercise_label: str | None = Field(...)
    diagnostics: bool = Field(default=False, ...)
```

**Campos reutilizables para una cámara de red / PTZ (solo ingesta de video):**

| Campo | Reutilizable para PTZ | Evidencia |
|-------|----------------------|-----------|
| `stream_url` | Sí, si el dispositivo expone RTSP/HTTP | `schemas.py:128-129`, `processor.py:52-56` |
| `target_fps` | Sí | Ritmo del consumer en `live_pose.py:217` |
| `include_preview` / `preview_fps` / `preview_jpeg_quality` | Sí | Preview JPEG en consumer `live_pose.py:320-343` |
| `stream_tuning` | Sí | Geometría vía `source.stream_geometry()` → `build_stream_processing_plan` `live_pose.py:191-202` |
| `max_throughput`, `capture_only`, `forced_exercise_label`, `diagnostics` | Sí | Agnósticos a la fuente |
| `device_index` | No aplica a red | Solo `source=camera` |
| `video_filename` | No aplica | Solo `source=file` |

**Documentación spec alineada:** `docs/spec/websocket-pose-stream.md:21-24` lista `camera | file | url` y `stream_url` para RTSP/HTTP.

**Nota de trazabilidad:** el spec cita `backend/app/routers/live_pose.py` (`websocket-pose-stream.md:86`), pero el código real está en `backend/app/api/websocket/live_pose.py` (`main.py:8,47`).

---

### 1.3 Payload por frame: ¿depende del tipo de fuente?

**Motor de inferencia — agnóstico:** `RealtimeEngineSession.process_bgr` recibe un `np.ndarray` BGR y devuelve el dict unificado vía `build_frame_payload_v1` (`realtime_engine.py:52-60`, `unified_payload.py:16-47`). No recibe ni consulta `source_type`.

**Consumer WS — dependencias puntuales por fuente:**

| Comportamiento | Condición | Cita |
|----------------|-----------|------|
| `stream_done` + cierre WS 1000 | Solo `source=file` al terminar | `live_pose.py:400-411` |
| `break` al recibir `None` | Solo `source=file` | `live_pose.py:272-274` |
| `error: "sin_frame"` y **continúa** el loop | `source != file` y frame `None` | `live_pose.py:272-301` |
| `total_frames` en cada payload | Todas; valor de `VideoSource.total_frame_count` (null salvo file fiable) | `live_pose.py:190`, `processor.py:67-72` |
| `stream_profile` (primer mensaje) | Todas; geometría OpenCV | `live_pose.py:227-231` |

En la práctica, para `url`/`camera`, el productor **sale en el primer `None`**, así que el cliente recibe como máximo un `sin_frame` y luego el handler termina (sin `stream_done`).

---

### 1.4 Reconexión, timeout y pérdida de conexión (`source=url`)

**No hay reconexión automática** al stream RTSP/HTTP.

**Fallo al abrir (cámara apagada, IP incorrecta, URL inválida):**

1. `VideoSource.__init__` lanza `RuntimeError` si `not isOpened()` (`processor.py:60-61`).
2. `pose_stream` captura `Exception`, envía `{"error": "..."}` y cierra con código **1011** (`live_pose.py:425-433`).

**Fallo durante lectura (corte de red, stream interrumpido):**

1. `get_frame()` devuelve `None` y loguea warning (`processor.py:102-103`).
2. Productor deposita `None`, rompe el bucle y envía `_STREAM_DONE` (`live_pose.py:137-149`).
3. Consumer: si no es `file`, emite payload con `error: "sin_frame"` (`live_pose.py:279-300`) y luego sale al recibir `_STREAM_DONE`.
4. **No** se reabre `VideoCapture`; **no** hay backoff ni reintentos.

**Timeouts explícitos:** solo en cleanup del productor al cerrar WS (`wait_for(..., timeout=15.0)`, `live_pose.py:445-447`). OpenCV no tiene timeout de lectura configurado en este código.

**Buffering RTSP:** no hay `CAP_PROP_BUFFERSIZE` para `url` (solo `camera`, `processor.py:42-45`). Comportamiento de latencia/acumulación depende del backend FFmpeg/GStreamer de OpenCV en el SO del servidor — **no documentado ni controlado en el repo**.

**Comparación con otras fuentes:**

| Escenario | `file` | `camera` | `url` |
|-----------|--------|----------|-------|
| Fin natural | `stream_done` + close 1000 | N/A (infinito hasta fallo/desconexión) | Igual que camera |
| Frame `None` en consumer | `break` inmediato | `sin_frame` + continúa (pero productor ya paró) | Igual que camera |
| Reconexión | No | No | No |
| Tests automatizados de `url` | — | — | **No encontrados** en `tests/` |

**IoT existente:** el monorepo prioriza WebSocket JPEG hacia `/ws/video`, no RTSP hacia pose-stream (`iot/README.md:31-33`). La Pi reintenta lectura en bucle solo para frames fallidos locales (`iot/raspberry-pi/stream.py:39-42`), patrón distinto al de `VideoSource`.

---

### 1.5 Cliente `appWeb`: cambio de fuente y supuestos hardcodeados

#### Análisis en vivo (`useLiveAnalysisSession.ts`)

**No usa `/ws/pose-stream`.** Usa cámara del navegador + `/ws/video`:

```208:237:appWeb/src/hooks/useLiveAnalysisSession.ts
    const url = buildVideoWebSocketUri(normalizeApiBaseUrl(apiBase));
    const ws = new WebSocket(url);
    ...
    const init: Record<string, unknown> = { analyze_pose: true, capture_only: captureOnly };
    ...
    ws.send(JSON.stringify(init));
```

Coherente con `docs/spec/live-camera-analysis.md:7` («No usar `/ws/pose-stream` para este flujo»).

#### Análisis por vídeo (`useVideoAnalysisSession.ts` + `ConfigPanel`)

**Tipos de fuente en UI** — solo tres, sin red/RTSP:

```11:11:appWeb/src/pages/VideoAnalysis/components/ConfigPanel.tsx
export type AnalysisInputSource = 'file' | 'server_camera' | 'browser_camera';
```

**Payload a pose-stream** — bifurcación `file` vs `server_camera`; no existe rama `url`:

```701:728:appWeb/src/hooks/useVideoAnalysisSession.ts
      const posePayload =
        params.mode === 'file'
          ? { source: 'file' as const, video_filename: params.videoFilename, ... }
          : {
              source: 'camera' as const,
              device_index: params.deviceIndex,
              ...
            };
```

**`browser_camera`** usa `/ws/video` (JPEG del navegador), no pose-stream (`useVideoAnalysisSession.ts:183-184`, `523+`).

**Manejo de `sin_frame`:** el cliente **no lo trata como error fatal**:

```3:7:appWeb/src/lib/poseWsPayload.ts
export function poseWsErrorMessage(map: Record<string, unknown>): string | null {
  if (!('error' in map)) return null;
  const e = String(map.error);
  if (e === 'sin_frame') return null;
  return e;
}
```

**Flutter legado:** solo envía `source: 'file'` (`video_analysis_session_controller.dart:455-468`). Sin `stream_url` en todo `app/`.

**Conclusión cliente:** el backend soporta `source=url`, pero **ningún cliente activo lo expone**. La UI asume webcam local (servidor o navegador) o archivo gold standard.

---

## Parte 2 — Plan de extensión: «cámara PTZ externa en red»

### 2.1 ¿Reutilizar `source=url` o ruta de ingesta distinta?

```mermaid
flowchart LR
    subgraph devices [Dispositivo PTZ Obsbot u otro]
        RTSP[Salida RTSP / HTTP]
        NDI[Salida NDI]
        HDMI[HDMI → adaptador IP]
    end
    subgraph backend [Backend FastAPI]
        VS[VideoSource cv2.VideoCapture]
        PS[pose_stream consumer]
        RE[RealtimeEngineSession]
    end
  subgraph clients [Clientes]
        AW[appWeb VideoAnalysis]
    end

    RTSP --> VS
    HDMI -->|típicamente RTSP| VS
    NDI -.->|requiere librería NDI| X[Ingesta NO existente]
    VS --> PS --> RE
    AW -->|PoseStreamConfig| PS
```

| Vía de ingesta | ¿Cubre el código actual? | Dependencia nueva |
|----------------|--------------------------|-------------------|
| **RTSP / HTTP** (URL en `stream_url`) | **Sí** — `source=url` + `cv2.VideoCapture` | Ninguna en backend |
| **NDI** (Obsbot Tail Air) | **No** — no es URL RTSP estándar para OpenCV | SDK NDI o `ffmpeg` con filtro NDI; ruta distinta a `VideoSource` actual |
| **WebSocket JPEG** (patrón IoT) | Parcial — existe `/ws/video`, no pose-stream con fuente remota | Reutilizar patrón `iot/`, no `VideoSource` |

**Recomendación de plan (sin decidir por ti):** la fase mínima de **solo ingesta** encaja en reutilizar el mecanismo `url` **si** confirmas que el Obsbot (o un adaptador) entrega RTSP estable. NDI implica un PR separado con ingesta propia.

**Fuera de alcance explícito (backlog):** control PTZ pan/tilt/zoom desde backend.

---

### 2.2 Cambios mínimos de contrato y compatibilidad

**Opción A — Sin cambio de contrato (mínimo absoluto):**

```json
{ "source": "url", "stream_url": "rtsp://...", "target_fps": 15, "include_preview": true }
```

- Compatible con Pydantic actual (`schemas.py:122-128`).
- Clientes que no envían `url` no se rompen.
- Flutter legado: no usa `url` hoy; seguiría igual si no se actualiza.

**Opción B — Nuevo literal `source` (p. ej. `"network_camera"` o `"ptz"`):**

- Requiere ampliar `Literal[...]` en `PoseStreamConfig` (`schemas.py:122`) — **cambio de contrato aditivo**.
- Clientes antiguos que solo conocen `camera|file|url` ignoran el nuevo valor hasta actualizarse.
- Pydantic rechazaría `source=ptz` hoy → **breaking para quien ya envíe ese string** (nadie en el repo hoy).
- Ventaja semántica: distinguir «URL genérica» de «cámara PTZ de laboratorio» y validar campos distintos en el futuro (sin acoplar al fabricante).

**Campos adicionales posibles (todos requieren tu decisión):**

| Campo hipotético | Propósito | ¿Rompe compatibilidad? |
|------------------|-----------|------------------------|
| `stream_url` (existente) | URL RTSP | No |
| `stream_transport` | `rtsp` / `http` / `ndi` | Aditivo si opcional |
| Credenciales fuera de URL | Usuario/contraseña RTSP | Aditivo; implica ensamblado seguro de URL en servidor |
| Preset en `.env` del backend | URL por defecto del laboratorio | Sin cambio WS; config servidor |

---

### 2.3 Estrategia de fallos para cámara física en red

**Comportamiento actual (documentar, no idealizar):**

| Evento | Comportamiento hoy | Diferencia vs `file` |
|--------|-------------------|----------------------|
| URL inalcanzable al inicio | Error JSON + WS 1011 | `file` → 4000 / mensaje distinto |
| Corte WiFi/Ethernet mid-stream | 1× `sin_frame`, fin de sesión | `file` → `stream_done` ordenado |
| IP cambiada (DHCP) | Fallo de apertura o lectura; sin recuperación | N/A en file |
| Cámara apagada | Igual | N/A |

**Mejoras posibles (cada una = decisión tuya + posible PR):**

1. **Sin cambio:** documentar que el operador debe reiniciar análisis y reenviar `PoseStreamConfig` (alineado con tesis `Formato_trabajo_de_grado.md:607` para pérdida de WS).
2. **Señalización:** nuevos códigos `error` (p. ej. `stream_lost`, `stream_reconnecting`) — **cambio de contrato**.
3. **Reconexión en `VideoSource`:** reabrir `VideoCapture` con backoff — lógica nueva; `ponytail:` marcar límites (sin descubrimiento DHCP).
4. **Descubrimiento de IP:** fuera de alcance mínimo; requeriría servicio aparte.

**Diferenciación `url` vs `file` en cliente:** hoy `stream_done` solo en file; una cámara de red nunca enviará `stream_done`. La UI no debe mostrar barra de progreso finita (`useVideoAnalysis.ts:132-135` usa `totalFrames` — será `null` para URL, `websocket-pose-stream.md:67`).

---

### 2.4 Documentación `docs/spec/websocket-pose-stream.md`

**Necesario actualizar o extender** cuando implementes, como mínimo:

1. Sección **«Fuente de cámara en red / PTZ (solo video)»** con:
   - equivalencia `source=url` + `stream_url` (o nuevo literal si eliges Opción B);
   - requisitos OpenCV/FFmpeg en el host del backend;
   - ausencia de control PTZ;
   - semántica de fallos (`sin_frame`, sin `stream_done`);
   - ausencia de reconexión (o la política que definas).
2. Corregir ruta de código `backend/app/api/websocket/live_pose.py`.
3. Tabla de campos reutilizables (`target_fps`, `include_preview`, `stream_tuning`, etc.).
4. Ejemplo JSON para Obsbot vía RTSP (URL placeholder, sin asumir path del fabricante).

**También tocar (tras implementación):** `docs/arquitectura.md` (diagrama IoT hoy solo muestra `/ws/video`, no RTSP → pose-stream), bitácora en `docs/Formato_trabajo_de_grado.md`.

---

## Parte 3 — PRs sugeridos (un concern por PR)

| PR | Concern único | Alcance | Criterio de cierre binario |
|----|---------------|---------|----------------------------|
| **PR-1** | Especificación y decisiones | Actualizar `docs/spec/websocket-pose-stream.md` (+ corrección ruta); sección PTZ/red; registrar preguntas resueltas | Spec mergeable; tabla `source` y fallos reflejan código **o** gaps explícitos como «pendiente PR-N» |
| **PR-2** | Validación backend RTSP (sin UI) | Script manual tipo `profile_pose_stream.py` con `--rtsp-url`; o test de humo que mockée `VideoSource` | Con URL RTSP de prueba configurada por ti: script recibe ≥1 frame con `pose_ok` definido **o** falla con mensaje claro en &lt;30 s |
| **PR-3** | Contrato aditivo (solo si eliges nuevo `source`) | `PoseStreamConfig` + `_build_video_source` + spec | `source=<nuevo>` validado por Pydantic; `source=url` sigue funcionando; tests de schema pasan |
| **PR-4** | UI `appWeb` — selección fuente PTZ/red | `ConfigPanel`, `useVideoAnalysis`, `useVideoAnalysisSession`: modo `network_stream` → `source=url` + `stream_url` | Usuario elige fuente, ingresa URL, inicia sesión, recibe preview JPEG y landmarks ≥10 s sin error fatal |
| **PR-5** | Señalización de fallos de red (opcional) | Backend: distinguir apertura vs lectura; cliente: UX «stream perdido» (sin reconectar aún) | Simular corte RTSP: cliente muestra estado de error en &lt;5 s; no muestra métricas obsoletas como actuales |
| **PR-6** | Reconexión automática (opcional, deuda explícita) | `VideoSource` o wrapper para `url` con N reintentos | Tras corte &lt;X s, sesión recupera frames sin nuevo WS **o** documento `ponytail:` declara techo (p. ej. sin DHCP) y test demuestra N reintentos |
| **PR-7** | Ingesta NDI (solo si eliges NDI) | Módulo `vision/` + dependencia NDI + nuevo `source` o `stream_transport` | Frame NDI → mismo payload unificado v1; **no** incluye control PTZ |
| **PR-8** | Trazabilidad tesis | Bitácora + `docs/arquitectura.md` | Entrada bitácora con fecha, archivos y enlace a spec |

**Orden sugerido:** PR-1 → PR-2 → (PR-3 si aplica) → PR-4 → PR-5/6/7 según decisiones.

**Atajos / deuda explícita si se pospone:**

- `ponytail:` Reutilizar `source=url` sin UI: operador usa `wscat`/script; deuda = sin selector en appWeb.
- `ponytail:` Sin reconexión: operador reinicia sesión manualmente; deuda = PR-6.
- `ponytail:` Credenciales embebidas en URL: visible en logs del servidor (`processor.py:56` loguea URL completa); upgrade path = campos separados + redacción en logs.

---

## Puntos de decisión antes de implementar

Responde estas preguntas antes de que se genere código:

1. **Protocolo de video del Obsbot Tail Air en tu laboratorio:** ¿salida **RTSP** (¿URL y path conocidos?), **NDI**, u **otro** (HDMI→adaptador RTSP)? Esto determina si basta `source=url` o hace falta PR-7.

2. **¿Nuevo literal `source` (p. ej. `network_camera` / `ptz`) o reutilizar `url`?** Trade-off: semántica/validación vs. cero cambio de contrato.

3. **¿Dónde vive la URL de la cámara?** ¿Solo campo en UI, preset en `.env` del backend, ambos, o lista de presets nombrados (`lab_ptz_1`)?

4. **Credenciales RTSP:** ¿embebidas en `stream_url` (`rtsp://user:pass@host/...`) o campos separados en el contrato?

5. **Política de reconexión:** ¿aceptable reinicio manual de sesión (estado actual), o exiges reintentos automáticos mid-stream? Si sí: ¿cuántos intentos, intervalo, timeout total?

6. **¿En qué pantalla debe vivir la fuente PTZ?** ¿Solo `/video-analysis`, también flujo «en vivo» dedicado, o ambos?

7. **¿El backend corre en el mismo LAN que la cámara?** (OpenCV consume RTSP en el **servidor**, no en el navegador — implica que un API en la nube sin túnel RTSP no sirve.)

8. **Compatibilidad Flutter legado:** ¿ignorar (no actualizar `app/`), o exigir que el contrato nuevo no rompa clientes que solo conocen `camera|file`?

9. **Señalización al usuario ante `sin_frame`:** ¿mostrar aviso en UI, contador de gaps, o tratar como frame vacío silencioso (comportamiento actual en `poseWsPayload.ts:6`)?

10. **Resolución/FPS del Obsbot:** ¿hay objetivo fijo para validar `stream_tuning: auto` (p. ej. 1080p30) o se deja heurística actual?

11. **Alcance de pruebas de tesis:** ¿basta prueba manual con cámara real + entrada en bitácora, o quieres vídeo RTSP grabado en `tests/assets/` para regresión sin hardware?

---

### Resumen ejecutivo

El backend **ya ingiere streams de red** vía `source=url` + `cv2.VideoCapture` + el mismo pipeline de pose que cámara/archivo. **No hay clientes que lo usen**, **no hay reconexión**, y **NDI requeriría ingesta nueva**. El camino de menor código para «PTZ externa solo video» es, *si* confirmas RTSP, exponer `stream_url` en `appWeb` y documentar fallos; todo lo demás (nuevo `source`, reconexión, NDI, credenciales) depende de tus respuestas en la sección anterior.