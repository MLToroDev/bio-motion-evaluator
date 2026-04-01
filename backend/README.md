# Bio-Motion Evaluator — Backend

API **FastAPI** con WebSockets para streaming y análisis de pose (**MediaPipe**).

## Configuración

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts\download_models.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Estado del servicio |
| POST | `/api/v1/analyze/pose` | Imagen multipart → pose + motor v1 (`PoseAnalysisResponse`) |
| POST | `/api/v1/auth/token` | JWT stub (requiere `DATABASE_URL`; crea usuario por email) |
| POST | `/api/v1/sessions` | Crear sesión de análisis (Bearer JWT) |
| GET | `/api/v1/sessions` | Listar sesiones del usuario |
| WS | `/ws/video` | Primer mensaje JSON `{"analyze_pose":true}` luego JPEG → JSON **contrato unificado v1** (`schema_version`, `knees`, `exercise_label`, `pipeline_ms`, …) |
| WS | `/ws/pose-stream` | Cámara, archivo (`tests/assets/videos`) o URL → motor tiempo real (`RealtimeEngineSession`) + payload unificado |

Documentación: `http://localhost:8000/docs`

### Base de datos (PostgreSQL + Alembic)

1. Define `DATABASE_URL` en `.env` (p. ej. `postgresql://user:pass@localhost:5432/bio_motion`).
2. Migraciones (desde `backend/`, con la misma variable en el entorno):

```bash
alembic upgrade head
```

Sin `DATABASE_URL`, la API sigue funcionando para WebSockets y `/api/v1/analyze/pose`; rutas `/api/v1/auth` y `/api/v1/sessions` responderán 503.

### WebSocket `/ws/pose-stream`

1. Conectar a `ws://localhost:8000/ws/pose-stream`.
2. Enviar un solo mensaje de texto JSON, por ejemplo:

```json
{"source": "file", "video_filename": "squat_test.mp4", "target_fps": 15}
```

o cámara local:

```json
{"source": "camera", "device_index": 0, "target_fps": 10}
```

3. Recibirás por cada frame un JSON **v1** con `schema_version`, `knees` (compatibilidad), `exercise_label`, `rep_phase`, `rep_count`, `quality_flags`, `pipeline_ms`, etc. (ver `docs/spec/websocket-pose-stream.md`).

Coloca los vídeos en [`../tests/assets/videos`](../tests/assets/videos) (solo el nombre del archivo en la petición).

