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

**2. Frames siguientes:** binarios JPEG (~cada 350 ms en `appWeb`).

**3. Respuesta:** JSON por frame (landmarks, `knees`, `exercise_label`, `rep_phase`, etc.). Ver `UnifiedWsFrameV1` en `backend/app/models/schemas.py`.

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
| Overlay 2D | `appWeb/src/components/PoseSkeletonCanvas.tsx` |
| WS backend | `backend/app/api/websocket/video.py` |
| Motor | `backend/vision/realtime_engine.py` |

## Pruebas manuales

1. `GET /api/v1/health` → 200.
2. `/live-analysis` → cámara frontal → iniciar transmisión.
3. **Horizontal:** brazo derecho levantado → landmark del hombro derecho sobre el hombro derecho en pantalla.
4. **Vertical:** hombros/cadera del esqueleto alineados con la silueta (sin bloque desplazado por recorte).
5. Ángulos de rodilla actualizándose en el panel.
