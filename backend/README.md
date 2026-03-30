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

Documentación: `http://localhost:8000/docs`
