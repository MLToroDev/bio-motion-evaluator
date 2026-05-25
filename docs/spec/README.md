# Especificaciones (`docs/spec/`)

Documentación técnica en **formato spec**: contratos de API/WebSocket, decisiones de implementación y registro de incidencias resueltas. Sirve para tesis (trazabilidad Cap. 6), onboarding y para que asistentes de código alineen cambios con el comportamiento acordado.

## Convención del formato spec

Cada archivo `.md` bajo `docs/spec/` debe incluir, cuando aplique:

| Sección | Contenido |
|--------|-----------|
| **Meta** | Estado del documento (`Activo`, `Borrador`), alcance, última revisión relevante |
| **Resumen** | Qué define este spec en 2–4 frases |
| **Contrato** | Mensajes, campos, tipos, valores por defecto, ejemplos JSON |
| **Implementación** | Rutas a código (backend / Flutter / IoT) |
| **Incidencias y decisiones** | Bugs conocidos, mitigaciones, por qué se eligió X |
| **Pruebas manuales** | Pasos mínimos para validar |

Al cambiar protocolos o comportamiento visible, **actualizar el spec correspondiente** en el mismo PR o commit lógico.

## Índice

| Documento | Descripción |
|-----------|-------------|
| [websocket-pose-stream.md](websocket-pose-stream.md) | `/ws/pose-stream`: config inicial, frames JSON, contrato unificado v1, `include_preview` |
| [live-camera-analysis.md](live-camera-analysis.md) | `/live-analysis` + `/ws/video`: cámara navegador, espejo selfie, overlay 2D (HU-03) |
| [live-overlay-inestabilidad-diagnostico.md](live-overlay-inestabilidad-diagnostico.md) | Diagnóstico overlay/motor: doble rAF, `setState`, blend, guía Performance |
| [flutter-client-websocket.md](flutter-client-websocket.md) | Patrones Flutter/Web (null-safety, hot reload, WS) |
| [api-v1-rest.md](api-v1-rest.md) | `/api/v1`: salud, `analyze/pose`, JWT stub, sesiones, métricas (PostgreSQL opcional) |
| [dev-learning-api.md](dev-learning-api.md) | `/api/v1/dev/*`: dataset 32D, jobs de entrenamiento, manifest ONNX, auto-colección (manual operativo: [`../guias/manual_aprendizaje_continuo_y_entrenamiento.md`](../guias/manual_aprendizaje_continuo_y_entrenamiento.md)) |

Referencias de arquitectura general: [../arquitectura.md](../arquitectura.md).

