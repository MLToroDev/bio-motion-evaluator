# Spec: API REST `/api/v1`

## Meta

- **Estado:** Activo (Fase 1 — stub auth + persistencia opcional)
- **Código:** `backend/app/api/v1/`, `backend/app/db/`, `backend/app/core/security.py`

## Resumen

Rutas versionadas para **identidad mínima** y **sesiones** cuando `DATABASE_URL` apunta a PostgreSQL. Sin base de datos, las dependencias FastAPI que usan `get_session` responden **503**.

## Contrato

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | No | Body JSON `{ "email": "..." }` → JWT |
| POST | `/api/v1/sessions` | Bearer | Crea fila en `sessions` |
| GET | `/api/v1/sessions` | Bearer | Lista últimas 50 sesiones del usuario |
| POST | `/api/v1/sessions/{id}/metrics` | Bearer | Inserta `session_metrics` |
| POST | `/api/v1/sessions/{id}/end` | Bearer | Marca `ended_at` |

## Implementación

- Migraciones: `backend/alembic/versions/20250331_0001_initial_schema.py`
- Modelos: `backend/app/db/models.py`

## Incidencias

1. **503 sin `DATABASE_URL`** — esperado en demos solo-vision; el motor WebSocket no requiere BD.
