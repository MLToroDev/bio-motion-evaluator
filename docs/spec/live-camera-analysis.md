# Spec: Análisis de cámara en vivo (HU-03)

## Meta

- **Estado:** Activo
- **Alcance:** Cliente web `appWeb` — ruta `/live-analysis`, WebSocket `/ws/video`, cámara del navegador.
- **Relacionado:** Payload JSON por frame compartido con [`websocket-pose-stream.md`](websocket-pose-stream.md) (contrato unificado v1). **No** usar `/ws/pose-stream` para este flujo (ese canal lee video en el servidor).

## Resumen

El deportista conecta la cámara frontal del navegador, envía JPEG al backend por `WebSocket /ws/video` y recibe landmarks y ángulos de rodilla. La inferencia MediaPipe corre en el servidor; el cliente captura, espeja el frame para coherencia con la vista selfie y dibuja el esqueleto 2D sin volver a invertir coordenadas.

## Parte descriptiva

| Elemento | Detalle |
|----------|---------|
| Historia | HU-03 — Análisis en vivo con retroalimentación de rodillas |
| Actor | Deportista / evaluador |
| Cliente | `appWeb/src/pages/LiveAnalysis/` |
| Métrica principal | Flexión bilateral de rodilla + estados semánticos (verde / amarillo / rojo) |

### Flujo de usuario

1. Comprobar backend (Inicio / Diagnóstico).
2. Opcional: Configuración → URL del API.
3. Análisis en vivo → Conectar cámara → Iniciar transmisión.
4. Interpretar overlay y panel de rodillas; Detener o Apagar cámara.

### Alcance MVP (cámara)

Flujo validado con **`facingMode: 'user'`** (cámara frontal). Cámara trasera u otros dispositivos pueden romper la convención de espejo; no es objetivo de la demo de sustentación.

## Parte técnica

### Endpoint

| Parámetro | Valor |
|-----------|--------|
| URL | `ws://{host}/ws/video` (o `wss://`) |
| Cliente | `buildVideoWebSocketUri()` — `appWeb/src/lib/wsUri.ts` |
| Backend | `backend/app/api/websocket/video.py` |

### Protocolo

**1. Primer mensaje (texto JSON):**

```json
{
  "analyze_pose": true,
  "capture_only": false,
  "forced_exercise_label": null
}
```

Con `capture_only: true` el motor no infiere pose (`analysis_enabled=false`).

**2. Frames siguientes:** binarios JPEG enviados en paralelo hasta el techo de backpressure del cliente (ver § Rendimiento captura).

**3. Respuesta:** JSON por frame (landmarks, `knees`, `exercise_label`, `rep_phase`, etc.). Ver `UnifiedWsFrameV1` en `backend/app/models/schemas.py`.

### Rendimiento captura (cliente)

El hook separa dos caminos en el cliente:

| Camino | Responsabilidad | Ritmo |
|--------|-----------------|-------|
| **Captura → WS** | JPEG al backend (`sendOneFrame`, backpressure) | `setInterval` **30 Hz** (`CAPTURE_HZ`) + `MAX_IN_FLIGHT` |
| **Motor (servidor)** | MediaPipe, ángulos, clasificador, reps | Respuesta JSON asíncrona (~8–20 RX/s) |
| **Overlay (cámara)** | `overlayLandmarksRef` + `PoseSkeletonCanvas` `smoothMotion` | **~60 FPS** (rAF estable + blend adaptativo) |

Las métricas del panel (`ui`: rodillas, ejercicio, reps) se actualizan en `onmessage` vía `setUi`. El esqueleto lee **`overlayLandmarksRef`** sin `setState` y pinta en un bucle rAF que **no se reinicia** por cada pose del servidor.

| Parámetro | Valor | Rol |
|-----------|-------|-----|
| Bucle de captura | `setInterval(1000/CAPTURE_HZ)` con `CAPTURE_HZ=30` | Desacoplado del rAF del overlay; menos contención en el hilo principal |
| `MAX_IN_FLIGHT` | `3` | Backpressure: no envía si `rttQueueRef.length >= 3` |
| `blobPendingRef` | boolean | Si `toBlob` tarda, ticks del intervalo retornan sin enviar (no encolan) |
| `JPEG_QUALITY` | `0.6` | Payload JPEG en `/ws/video` |
| Overlay `landmarksRef` | `useRef` en hook | Escritura en `onmessage`; sin re-render de `LiveAnalysis` por landmarks |
| Blend overlay | `adaptiveBlendMs ≈ 0.9 × intervalo` entre poses (mín. 80 ms) | Completa antes de la siguiente muestra WS típica |
| Estilos esqueleto | Cache al montar (`--bm-skeleton-*`) | Sin `getComputedStyle` en el hot path de pintura |
| HUD `displayRxPerSec` | contador 1 s | Respuestas JSON/s (RX/s), no FPS de captura ni de overlay |

**Cadencia efectiva de captura:** con hardware lento, si `toBlob` supera ~33 ms, la tasa real de envío puede bajar a **~15–20/s** (mismo backpressure que antes; no es regresión frente al intervalo fijo histórico ~2,8/s).

**Expectativa en demo:** RX/s típico **8–20**; overlay percibido fluido a 60 FPS entre muestras del servidor.

**Límites y cleanup:**

- Pestaña oculta: el rAF del overlay se pausa; el intervalo de captura sigue (aceptable en demo; pestaña activa en sustentación).
- Al detener: `clearInterval` captura, cierre WS, `overlayLandmarksRef.current = null`; el canvas limpia refs si lee `null` antes del desmontaje.
- `resetStreamState` vacía `rttQueueRef` y `blobPendingRef = false`.

Sin cambios en `backend/app/api/websocket/video.py`: acepta varios JPEG en el mismo WebSocket.

### Alineación espejo (cámara frontal)

Cadena coherente para vista selfie (patrón vigente en `appWeb`):

| Capa | Implementación |
|------|----------------|
| Vista `<video>` | `transform: scaleX(-1)` + `object-fit: contain` (misma lógica de encuadre que el canvas) |
| Captura WS | `drawImage` **sin** espejar (JPEG = frame crudo del stream) |
| Overlay | `PoseSkeletonCanvas` con **`mirrorHorizontal={true}`** (`1 - x` alinea coords del JPEG con el vídeo espejado por CSS) |
| Proporción | `contentAspect={videoWidth/videoHeight}` cuando `videoWidth > 0` (listener `loadedmetadata`) |

**Incidencia:** espejar el JPEG en captura **y** usar `mirrorHorizontal={false}` en el overlay desfasaba izq/der en algunos navegadores (doble convención de espejo). **No** espejar en captura si el overlay aplica el espejo horizontal.

**Desplazamiento vertical:** `object-fit: cover` en el `<video>` recortaba distinto que el rectángulo `contain` del canvas; se unificó a `contain` + `contentAspect`.

### Alineación vertical (`object-fit: cover`)

El contenedor del preview puede tener relación de aspecto distinta al stream. `PoseSkeletonCanvas` usa `videoContentRect()` con `contentAspect` del stream para mapear landmarks al rectángulo visible (misma idea que `PreviewCanvas` en análisis por archivo).

## Implementación

| Pieza | Ruta |
|-------|------|
| UI | `appWeb/src/pages/LiveAnalysis/LiveAnalysis.tsx` |
| Sesión WS + captura | `appWeb/src/hooks/useLiveAnalysisSession.ts` |
| Overlay 2D | `appWeb/src/components/PoseSkeletonCanvas.tsx` (`smoothMotion`, `landmarkInterpolation.ts`) |
| WS backend | `backend/app/api/websocket/video.py` |
| Motor | `backend/vision/realtime_engine.py` |

## Incidencias overlay (mitigadas 2026-05-25)

| ID | Síntoma | Mitigación |
|----|---------|------------|
| INC-OVERLAY-001 | Doble rAF captura + pintura | Captura a 30 Hz (`CAPTURE_HZ`); overlay en rAF único `[smoothMotion]` |
| INC-OVERLAY-002 | Reinicio rAF por cada RX | `landmarks` fuera de deps del bucle; detección en `tick` vía `landmarksRef` |
| INC-OVERLAY-003 | Doble `setState` por landmarks | `overlayLandmarksRef` sin `setOverlayLandmarks` |
| INC-OVERLAY-004 | Blend 100 ms vs RX/s | `adaptiveBlendMsRef` según intervalo entre poses |

Diagnóstico previo y verificación post-fix: [`live-overlay-inestabilidad-diagnostico.md`](live-overlay-inestabilidad-diagnostico.md).

## Pruebas manuales

1. `GET /api/v1/health` → 200.
2. `/live-analysis` → cámara frontal → iniciar transmisión.
3. **Horizontal:** brazo derecho levantado → landmark del hombro derecho sobre el hombro derecho en pantalla.
4. **Vertical:** hombros/cadera del esqueleto alineados con la silueta (sin bloque desplazado por recorte).
5. Ángulos de rodilla actualizándose en el panel.
6. **Reconexión:** DETENER → Iniciar transmisión de nuevo: sin esqueleto residual; colores del esqueleto visibles (verde/blanco).
