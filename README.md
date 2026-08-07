# Bio-Motion Evaluator

Sistema de software para la **valoración automática de movilidad articular** y detección de asimetrías mediante **visión artificial** (MediaPipe BlazePose en servidor). Trabajo de grado — Ingeniería en Software, Tecnológico de Antioquia (2026).

**Autor:** Mateo Londoño Toro  
**Repositorio público:** https://github.com/MLToroDev/Repositorio

---

## Resumen

Bio-Motion Evaluator integra:

- **Cliente web operativo** ([`appWeb/`](appWeb/)) — React 19 + Vite + TypeScript: análisis en vivo desde cámara, análisis de vídeo *gold standard*, panel de métricas y herramientas de desarrollo (aprendizaje continuo).
- **Backend** ([`backend/`](backend/)) — FastAPI (Python): inferencia de pose, goniometría digital de rodilla, clasificación de ejercicio, WebSockets y API REST.
- **IoT opcional** ([`iot/`](iot/)) — ESP32-CAM / Raspberry Pi como fuente de vídeo.
- **Flutter legado** ([`app/`](app/)) — Prototipo inicial Android/iOS/web; **no** es el destino de nuevas funcionalidades (ver migración a React en la memoria).

La inferencia corre en el **servidor**; los clientes capturan fotogramas, envían por WebSocket y renderizan el esqueleto y las métricas en tiempo real. Evaluación de calidad alineada con **ISO/IEC 25010** (usabilidad, mantenibilidad, escalabilidad).

Documentación de tesis y specs: [`docs/`](docs/README.md) · Arquitectura: [`docs/arquitectura.md`](docs/arquitectura.md) · Borrador académico: [`docs/Formato_trabajo_de_grado.md`](docs/Formato_trabajo_de_grado.md)

---

## Arquitectura

| Capa | Tecnología | Carpeta | Rol |
|------|------------|---------|-----|
| **Frontend web (activo)** | React 19, Vite, TypeScript | [`appWeb/`](appWeb/) | HU-03 análisis en vivo, HU-04 vídeo, configuración, Dev Tools |
| **Backend** | Python 3.10+, FastAPI, MediaPipe | [`backend/`](backend/) | API REST, WebSockets, motor en tiempo real, Celery |
| **Persistencia** | PostgreSQL + Alembic (opcional) | `backend/app/db/` | Sesiones, dataset 32D, jobs de entrenamiento |
| **IoT** | ESP32-CAM / RPi | [`iot/`](iot/) | Captura remota de vídeo |
| **Flutter (legado)** | Dart / Flutter | [`app/`](app/) | Referencia histórica; no ampliar salvo decisión explícita |
| **Documentación** | Markdown | [`docs/`](docs/) | Specs, guías, bitácora, diagramas |
| **Pruebas** | pytest, vídeos locales | [`tests/`](tests/) | *Gold standard* (MP4 no versionados) |

```mermaid
flowchart LR
  subgraph clients [Clientes]
    Web["appWeb React"]
    IoT["ESP32 / RPi"]
  end
  subgraph api [Backend FastAPI]
    WSvideo["/ws/video"]
    WSpose["/ws/pose-stream"]
    REST["/api/v1"]
    MP["MediaPipe + motor"]
  end
  Web -->|JPEG / JSON| WSvideo
  Web --> REST
  Web --> WSpose
  IoT --> WSvideo
  WSvideo --> MP
  WSpose --> MP
```

---

## Funcionalidades principales (`appWeb`)

| Ruta | Descripción |
|------|-------------|
| `/live-analysis` | Cámara del navegador → `/ws/video` → overlay 2D + flexión bilateral de rodilla |
| `/video-analysis` | Vídeos en servidor (`tests/assets/videos`) → `/ws/pose-stream` |
| `/backend-status` | Diagnóstico de salud del API |
| `/settings/connection` | URL del backend y claves dev |
| `/dev/*` | Catálogo, dataset 32D, entrenamiento ONNX, modelos (requiere flags MVP) |
| `/login`, `/sessions`, … | Sprint 4 — auth y persistencia (opcional, según `VITE_MVP_*`) |

Detalle del cliente: [`appWeb/README.md`](appWeb/README.md). Contratos: [`docs/spec/`](docs/spec/README.md).

---

## Requisitos

| Componente | Versión |
|------------|---------|
| **Python** | 3.10+ (recomendado 3.11) |
| **Node.js** | 20+ (para `appWeb`) |
| **Git** | Cualquier versión reciente |
| **PostgreSQL** | Opcional (auth, sesiones, aprendizaje continuo) |
| **Redis** | Opcional (Celery para ingestión/entrenamiento) |
| **Flutter** | Solo si trabajas el legado en `app/` |

Instalación detallada: [`docs/guias/SETUP.md`](docs/guias/SETUP.md).

---

## Inicio rápido (evaluadores / desarrollo)

### Opción A — Docker Compose (recomendado)

Requiere Docker Desktop. Desde la raíz del monorepo:

```bash
cp .env.docker.example .env   # opcional
docker compose up --build
```

| Servicio | URL |
|----------|-----|
| Cliente (`appWeb`, Vite) | http://localhost:5173 |
| API | http://localhost:8000/api/v1/health · http://localhost:8000/docs |
| Demo estática (perfil `demo`) | `docker compose --profile demo up --build web-demo` → http://localhost:8080 |

Detalle: [`docs/spec/docker-compose-stack.md`](docs/spec/docker-compose-stack.md) · [`docs/guias/SETUP.md`](docs/guias/SETUP.md).

### Opción B — Procesos locales

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # Windows — editar variables
# cp .env.example .env    # Linux/macOS

python scripts/download_models.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Atajo (Windows, desde la raíz):** `.\scripts\start-dev-backend.ps1`

| Recurso | URL |
|---------|-----|
| Salud | http://localhost:8000/api/v1/health |
| OpenAPI | http://localhost:8000/docs |
| WS cámara navegador | `ws://localhost:8000/ws/video` |
| WS vídeo en servidor | `ws://localhost:8000/ws/pose-stream` |

Más endpoints y PostgreSQL: [`backend/README.md`](backend/README.md).

**Celery** (opcional, ingestión/entrenamiento):

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### 2. Cliente web (`appWeb`)

En **otra terminal**, desde la raíz:

```bash
cd appWeb
npm install
npm run dev
```

Abre la URL que indique Vite (p. ej. http://localhost:5173). En **Configuración** define `http://localhost:8000` si no es el valor por defecto.

**Build de producción / demo jurado:**

```bash
npm run build
npm run preview
```

Variables MVP y menú reducido: [`appWeb/README.md`](appWeb/README.md) y [`appWeb/.env.example`](appWeb/.env.example).

### 3. Flujo mínimo de prueba (HU-03)

1. Backend en marcha (`GET /api/v1/health` → 200).
2. `appWeb` → **Análisis en vivo** → Conectar cámara → Iniciar transmisión.
3. Comprobar overlay de esqueleto y ángulos de rodilla en el panel (RX/s típico **8–20** según hardware).

Pruebas alineadas al spec: [`docs/spec/live-camera-analysis.md`](docs/spec/live-camera-analysis.md).

---

## Estructura del monorepo

```
Repositorio/
├── appWeb/          # Cliente React (frontend activo)
├── backend/         # FastAPI + visión + workers
├── app/             # Flutter (legado)
├── iot/             # Firmware / notas IoT
├── docs/            # Tesis, specs, guías, arquitectura
├── tests/           # Pruebas y assets de vídeo (MP4 en .gitignore)
└── scripts/         # Atajos PowerShell (backend, publish)
```

---

## Flutter (legado)

El primer cliente se desarrolló en Flutter; la capa web operativa migró a **React** por limitaciones de Flutter Web en vista previa y despliegue estable de MediaPipe en cliente. Para ejecutar el legado:

```bash
cd app
flutter pub get
flutter run -d chrome   # o android / ios
```

Atajo Windows: `.\scripts\start-dev-flutter.ps1`

---

## IoT

Ver [`iot/README.md`](iot/README.md).

---

## Documentación para evaluadores

| Documento | Contenido |
|-----------|-----------|
| [`docs/Formato_trabajo_de_grado.md`](docs/Formato_trabajo_de_grado.md) | Memoria: objetivos, sprints, diseño, pruebas, bitácora |
| [`docs/spec/live-camera-analysis.md`](docs/spec/live-camera-analysis.md) | Análisis en vivo (cámara + `/ws/video`) |
| [`docs/spec/websocket-pose-stream.md`](docs/spec/websocket-pose-stream.md) | Streaming pose por archivo/cámara servidor |
| [`docs/spec/api-v1-rest.md`](docs/spec/api-v1-rest.md) | API REST v1 |
| [`presentacion.md`](presentacion.md) | Guion de sustentación (si aplica) |

---

## Seguridad al clonar

- **No** subas `backend/.env` ni claves reales; usa [`backend/.env.example`](backend/.env.example).
- Los vídeos de prueba van en `tests/assets/videos/` (ignorados por Git).
- Si rotaste tokens tras hacer el repo público, revisa que no queden secretos en el historial de Git.

---

## Licencia

Pendiente de definición según política institucional del trabajo de grado. Contacto del autor vía el repositorio en GitHub.

---

## Referencia académica (extracto)

> *Bio-Motion Evaluator automatiza la valoración de movilidad articular y la detección de asimetrías en entrenamiento de fuerza, integrando visión artificial (MediaPipe), comunicación WebSocket en tiempo real y arquitectura cliente-servidor con separación entre captura, inferencia y visualización.*

Palabras clave: visión artificial, estimación de pose, goniometría digital, FastAPI, React, WebSocket, biomecánica, ISO/IEC 25010.
