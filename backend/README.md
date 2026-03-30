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
| GET | `/health` | Estado del servicio |
| POST | `/analyze/pose` | Imagen multipart → landmarks |
| WS | `/ws/video` | Frames binarios desde IoT / cliente |
| WS | `/ws/pose-stream` | Cámara, archivo (`tests/assets/videos`) o URL → MediaPipe + ángulos de rodilla en JSON |

Documentación: `http://localhost:8000/docs`

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

3. Recibirás por cada frame un JSON con `knees`: `left_knee_flexion_angle_deg`, `right_knee_flexion_angle_deg`, etc.

Coloca los vídeos en [`../tests/assets/videos`](../tests/assets/videos) (solo el nombre del archivo en la petición).
