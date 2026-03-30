# Spec: WebSocket `/ws/pose-stream`

## Meta

- **Estado:** Activo  
- **Alcance:** Primer mensaje de configuración y mensajes por frame desde el backend FastAPI hacia el cliente Flutter (u otros).  
- **Código principal:** `backend/app/routers/live_pose.py`, `backend/app/models/schemas.py`

## Resumen

El cliente abre un WebSocket en **`/ws/pose-stream`**, envía **un único mensaje de texto JSON** con la configuración (`PoseStreamConfig`), y el servidor responde con **mensajes JSON por fotograma** (ángulos de rodilla, landmarks opcionales, vista previa JPEG opcional).

## Contrato: mensaje inicial (cliente → servidor)

Tipo: **texto** UTF-8, objeto JSON.

| Campo | Tipo | Obligatorio | Notas Mín. | Máximo |
|-------|------|-------------|------------|--------|
| `source` | string | no | `"file"` (defecto) | literal `camera` \| `file` \| `url` |
| `video_filename` | string \| null | si `source=file` | nombre bajo `tests/assets/videos/` | — |
| `device_index` | number | no | 0 (cámara) | — |
| `stream_url` | string \| null | si `source=url` | RTSP/HTTP | — |
| `target_fps` | number | no | 15 | 0.5–60 |
| `include_preview` | bool \| null | no | `true` | Coerción: ver abajo |

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

## Contrato: mensajes por frame (servidor → cliente)

Tipo: **texto** JSON por mensaje.

Campos habituales:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `frame_index` | number | Índice entero del frame |
| `pose_ok` | bool | Resultado de detección (ver `PoseResult` en servicio MediaPipe) |
| `note` | string \| null | Nota humana (p. ej. sin pose) |
| `landmarks` | array \| null | Lista de puntos `{ index, x, y, z, visibility? }` |
| `knees` | object \| null | Ángulos; p. ej. `left_knee_flexion_angle_deg`, `right_knee_flexion_angle_deg` (grados) |
| `preview_jpeg_base64` | string | Presente solo si `include_preview` era truthy en la config; JPEG en Base64 |

### Mensaje de error operativo

Puede incluir **`error`** (string), p. ej. `sin_frame`, o cierre con código HTTP WS y cuerpo JSON según `live_pose.py`.

## Implementación

| Pieza | Ruta |
|-------|------|
| Router WS | `backend/app/routers/live_pose.py` |
| Modelo config | `backend/app/models/schemas.py` — clase `PoseStreamConfig` |
| URI cliente (Flutter) | `app/lib/utils/ws_uri.dart` — `buildPoseStreamWebSocketUri` |
| Pantalla de prueba | `app/lib/screens/server_test_video_screen.dart` |

## Incidencias y decisiones

1. **Pydantic rechazaba `include_preview: null`**  
   - **Causa:** tipo `bool` estricto sin aceptar JSON `null`.  
   - **Mitigación:** validador `before` que mapea `None → True` y demás valores con `bool(v)`.

2. **Flutter Web — `TypeError: null is not a subtype of bool`** (traza apuntando al payload o al estado del switch)  
   - **Contexto:** estado/`include_preview` en escenarios de hot reload o valores nulos en la frontera.  
   - **Mitigación cliente:** `_includePreview` como `bool?` y uso de **`?? true`** al construir JSON del primer mensaje y al enlazar `SwitchListTile.value` (ver spec Flutter).

## Pruebas manuales sugeridas

1. Backend en `localhost:8000`, modelo descargado si aplica.  
2. Flutter Web (`flutter run -d web-server`), pantalla “Vídeo de prueba (servidor)”.  
3. Conectar, enviar FPS y nombre de archivo existente en `tests/assets/videos/`.  
4. Con y sin “Vista previa desde servidor”, comprobar presencia/ausencia de `preview_jpeg_base64` en payloads.
