# Spec: Cliente Flutter — WebSockets y robustez (Web)

## Meta

- **Estado:** Activo  
- **Alcance:** Patrones aplicables a pantallas que usan `web_socket_channel` contra el backend (*pose stream*, video binario, etc.).  
- **Referencia principal:** `app/lib/screens/video_analysis/video_analysis_screen.dart`, `app/lib/screens/live_analysis/live_analysis_screen.dart`, `app/lib/utils/ws_uri.dart`, `app/lib/pose/pose_ws_payload.dart` (parseo compartido de respuestas pose JSON)

## Resumen

En **Flutter Web**, JSON decodificado y el estado de widgets pueden interactuar mal con **hot reload** o con valores **`null`** que en otros lenguajes se envían explícitamente. Este spec documenta decisiones para evitar fallos en runtime (`Null is not a subtype of bool`, etc.) y mantener contrato con el backend descrito en [websocket-pose-stream.md](websocket-pose-stream.md).

## Parseo compartido de respuestas JSON (pose)

Los mensajes de texto con `landmarks`, `knees`, `frame_index` (y opcionalmente `total_frames`, `error`, **`schema_version`**, **`exercise_label`**, **`exercise_confidence`**, **`rep_phase`**, **`rep_count`**, **`quality_flags`**, **`pipeline_ms`**) se interpretan en **`app/lib/pose/pose_ws_payload.dart`** (y `landmarks` en **`app/lib/pose/landmarks_json.dart`**): `PoseWsServerFrame.fromJsonMap`, `poseWsErrorMessage`, `parsePoseFrameIndex`, `parsePoseTotalFrames`, highlights `kPoseKneeHighlightIndices` y texto de resumen de sesión (`poseSessionSummaryFromKneesMap`). Cualquier cambio de contrato del backend en esos campos debe actualizarse **una sola vez** ahí; las pantallas en vivo y vídeo solo orquestan WebSocket y UI. Campos nuevos deben usar **null-safety** (`??`) — ver plan v2 §6.2.

## Persistencia en Web (`home_prefs`)

La URL del API y el resumen de sesión pasan por **`app/lib/storage/prefs.dart`**: en **IO** (Android, iOS, desktop) se usa `shared_preferences`; en **Web** (`dart.library.html` o `dart.library.js_interop`) se usa **`localStorage`** vía `package:web`, sin el canal `plugins.flutter.io/shared_preferences`. Así se evita **`MissingPluginException(No implementation found for method getAll…)`** en algunos arranques con DDC o Wasm cuando el registrador de plugins no enlaza el plugin.

## Navegación y DDC (Flutter Web)

La pantalla de inicio **no importa** `LiveAnalysisScreen` / `VideoAnalysisScreen` / `BackendStatusScreen`: usa rutas con nombre (`AppRoutes` en `app/lib/app_routes.dart`, tabla `routes` en `main.dart`). Así se evita un grafo denso `home → análisis → …` que en modo **desarrollo con DDC** a veces disparaba *«Library … was previously defined»* tras hot reload. Si reaparece: **hot restart** (`R`) o `flutter clean` + `flutter run`.

## Contrato hacia el servidor

- **`/ws/pose-stream`:** un solo `jsonEncode` con al menos `source`, `video_filename` (si aplica), `target_fps`, `include_preview`.
- **Recomendación:** no enviar `null` para `include_preview`; si el estado UI puede ser ambiguo, usar **`include_preview: _includePreview ?? true`** para materializar siempre un booleano JSON legítimo.

## Implementación: bandera `include_preview` (pantalla servidor)

Archivo: `app/lib/screens/video_analysis/video_analysis_screen.dart`.

| Elemento | Decisión |
|----------|----------|
| Estado | `bool? _includePreview = true` |
| Motivo | Documentado en código: en web el estado puede quedar incoherente tras hot reload; el `?? true` unifica comportamiento con el default del backend. |
| `SwitchListTile.value` | `_includePreview ?? true` |
| Payload WS | `'include_preview': _includePreview ?? true` |
| Layout / textos | Condiciones que dependían de `_includePreview` usan `(_includePreview ?? true)` donde hace falta un bool concreto |

## Otros clientes WS

- **`/ws/video`** (`live_analysis_screen.dart`): primer mensaje texto `{"analyze_pose": true}`; luego JPEG binarios. El HUD muestra **dos tiempos** (no confundir con “ping” HTTP): **Cap** = `takePicture()` + lectura de bytes en el cliente (en Web puede ser **mucho mayor** que el servidor); **Srv** = desde `sink.add(JPEG)` hasta el JSON de respuesta (red local despreciable + `imdecode` + **MediaPipe** + serialización). Un valor **Srv** de decenas a ~200 ms en local solo con CPU es habitual según resolución del JPEG y carga del PC. **resp/s** cuenta mensajes recibidos por segundo (no es el FPS de captura). Si se añaden flags booleanos al JSON, aplicar la misma regla: **nunca asumir no-null sin `??` o helper** al leer `Map<String, dynamic>` desde `jsonDecode`.

## Incidencias registradas

| Síntoma | Causa probable | Mitigación |
|---------|----------------|------------|
| `DartError: ... null is not a subtype of bool` en traza cerca de `_start` / JSON del WS | Booleano de UI o mapa con `null` forzado a `bool` | `bool?` + `?? true` o helper `_coerceJsonBool` si se parsean campos del servidor |

## Pruebas manuales

1. Tras cambios en la pantalla, hacer **hot restart** (`R`) en `flutter run`, no solo hot reload, antes de descartar errores en Web.  
2. Probar toggle “Vista previa desde servidor” apagado y encendido; verificar tráfico o UI (imagen vs solo log).  
3. Validar contra backend con spec [websocket-pose-stream.md](websocket-pose-stream.md).

## Referencias de código

- `app/lib/pose/pose_overlay.dart` — `parseLandmarksJson`  
- `backend/app/models/schemas.py` — `PoseStreamConfig.include_preview`
