# Spec: API REST `/api/v1`

## Meta

- **Estado:** Activo (Fase 1 — stub auth + persistencia opcional)
- **Código:** `backend/app/api/v1/`, `backend/app/db/`, `backend/app/core/security.py`

## Resumen

Rutas versionadas para **identidad mínima** y **sesiones** cuando `DATABASE_URL` apunta a PostgreSQL. Sin base de datos, las dependencias FastAPI que usan `get_session` responden **503**.

## Contrato

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Estado y versión (`HealthResponse`) |
| POST | `/api/v1/analyze/pose` | No | Multipart imagen → landmarks + campos motor v1 (`PoseAnalysisResponse`) |
| POST | `/api/v1/auth/token` | No | Body JSON `{ "email": "..." }` → JWT |
| POST | `/api/v1/sessions` | Bearer | Crea fila en `sessions` |
| GET | `/api/v1/sessions` | Bearer | Lista últimas 50 sesiones del usuario |
| POST | `/api/v1/sessions/{id}/metrics` | Bearer | Inserta `session_metrics` (body puede incluir `frame_index` opcional) |
| POST | `/api/v1/sessions/{id}/end` | Bearer | Marca `ended_at` |

### `PoseAnalysisResponse` (alineado semánticamente al WS v1)

Campos opcionales además de pose clásica: `schema_version`, `exercise_label`, `exercise_confidence`, `rep_phase`, `rep_count`, `quality_flags`, `pipeline_ms`. El análisis usa la misma sesión de motor que el stream (`RealtimeEngineSession` por petición). **`landmarks` / `world_landmarks`** siguen la misma regla que el WebSocket: subconjunto filtrado por `visibility` (ver `POSE_LANDMARK_MIN_VISIBILITY_RESPONSE` en `docs/spec/websocket-pose-stream.md`).

### `session_metrics`

- `frame_index` (integer, nullable): índice de fotograma asociado a la muestra, si aplica.

## Implementación

- Migraciones: `backend/alembic/versions/20250331_0001_initial_schema.py`, `20250331_0002_session_metrics_frame_index.py`
- Modelos: `backend/app/db/models.py`

## Incidencias

1. **503 sin `DATABASE_URL`** — esperado en demos solo-vision; el motor WebSocket no requiere BD.

