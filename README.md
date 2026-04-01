# Bio-Motion Evaluator

Monorepo para el sistema de evaluación de movimiento (web-first, cross-platform, comunicación IoT). Incluye frontend Flutter, backend FastAPI con visión por computador e integración con dispositivos de captura.

## Arquitectura (resumen)

| Capa | Tecnología | Carpeta |
|------|------------|---------|
| Frontend (Web / Android / iOS) | Flutter | [`app/`](app/) |
| Backend (API, WebSockets, IA) | Python + FastAPI | [`backend/`](backend/) |
| IoT (cámara externa) | ESP32-CAM / Raspberry Pi | [`iot/`](iot/) |
| Documentación / tesis | Markdown, diagramas | [`docs/`](docs/) |
| Pruebas y vídeos gold standard | pytest, activos MP4 | [`tests/`](tests/) |

Diagrama detallado: [`docs/arquitectura.md`](docs/arquitectura.md).

Contexto para asistentes de código en Cursor: [`.cursorrules`](.cursorrules) (stack, biomecánica, trazabilidad para el Cap. 6). Especificaciones técnicas: [`docs/spec/`](docs/spec/README.md).

## Requisitos

- **Flutter** SDK (stable), con soporte Web, Android e iOS según tu objetivo.
- **Python** 3.10+ (recomendado 3.11).
- **Git** y, para publicar en GitHub, **GitHub CLI** (`gh`) autenticado.

Instrucciones de instalación: [`docs/SETUP.md`](docs/SETUP.md).

## Inicio rápido

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Opcional: descargar modelo MediaPipe Pose
python scripts/download_models.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Recarga automática del backend:** la flag `--reload` hace que **Uvicorn reinicie el proceso** cuando guardas cambios en `.py` bajo la carpeta desde la que arrancaste (normalmente `backend/`). No hace falta parar y volver a ejecutar el comando.

Atajos desde la raíz del repo (Windows):

- `.\scripts\start-dev-backend.ps1`
- `.\scripts\start-dev-flutter.ps1` (por defecto `web-server`; opcional: `.\scripts\start-dev-flutter.ps1 edge`)

- Salud: `GET http://localhost:8000/api/v1/health`
- Documentación interactiva: `http://localhost:8000/docs`
- Streaming de pose (cámara / vídeo en `tests/assets/videos` / URL): WebSocket `ws://localhost:8000/ws/pose-stream` (primer mensaje JSON; ver [`backend/README.md`](backend/README.md)).

### App Flutter

Si aún no generaste las carpetas de plataforma:

```bash
cd app
flutter create . --platforms=web,android,ios --project-name bio_motion_app
flutter pub get
flutter run -d edge
# Si aparece "Failed to launch browser", usa solo el servidor y abre la URL manualmente:
flutter run -d web-server --web-port 8080 --web-hostname localhost
```

**Hot reload en Flutter:** deja **`flutter run`** abierto en una terminal. Tras cambiar código Dart:

- Pulsa **`r`** en esa terminal → *hot reload* (rápido, mantiene estado).
- Pulsa **`R`** → *hot restart* (reinicia el estado de la app).
- En **Cursor / VS Code**, con la extensión **Flutter**, suele existir la opción *Hot reload on save* o el botón del rayo en la barra de depuración.

Abre **dos terminales**: una con el backend (`--reload`) y otra con `flutter run` para no detener nada al editar.

### IoT

Ver [`iot/README.md`](iot/README.md).

## Licencia

Define la licencia de tu trabajo de grado en esta sección cuando corresponda.

