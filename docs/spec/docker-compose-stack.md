# Despliegue local con Docker Compose

| Campo | Valor |
|-------|--------|
| **Estado** | Activo |
| **Alcance** | Stack local: `appWeb` + FastAPI + PostgreSQL + Redis + Celery |
| **Última revisión** | 2026-08-07 |

## Resumen

Define el arranque reproducible del monorepo con **Docker Compose** en la raíz. El frontend operativo (`appWeb`) y el backend (MediaPipe / FastAPI) se exponen en el host; la persistencia opcional (PostgreSQL) y la cola (Redis/Celery) quedan cableadas con variables de entorno. No cambia contratos REST/WebSocket: solo empaquetado y orquestación.

## Contrato (puertos y URLs)

| Servicio | Contenedor | Host (default) | Notas |
|----------|------------|----------------|-------|
| Vite (`web`) | 5173 | http://localhost:5173 | Hot reload; monta `appWeb/src` |
| API (`backend`) | 8000 | http://localhost:8000 (o `BACKEND_PORT` en `.env`) | `/api/v1/health`, `/docs`, WS |
| Demo nginx (`web-demo`) | 80 | http://localhost:8080 | Perfil Compose `demo` |
| PostgreSQL (`db`) | 5432 | localhost:5432 | user/db `biomotion` |
| Redis (`redis`) | 6379 | localhost:6379 | broker Celery |

En el navegador, la URL del API sigue siendo **`http://localhost:8000`** (prefs de `appWeb`), porque el cliente habla al host, no al DNS interno de Compose.

Variables relevantes del backend en Compose:

- `DATABASE_URL=postgresql://biomotion:biomotion@db:5432/bio_motion`
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` → `redis://redis:6379/0`
- `CORS_ORIGINS` incluye `5173` y `8080`
- Modelo: `MEDIAPIPE_POSE_MODEL_PATH=models/pose_landmarker_full.task` (volumen `./backend/models`; si falta, `docker/entrypoint.sh` descarga)
- Aprendizaje continuo: `AUTO_COLLECT_ENABLED` / `AUTO_COLLECT_MIN_CONFIDENCE` se propagan a `backend` y `worker` (default `false` / `0.85` vía `.env` raíz)
- Validador de ejercicio: `EXERCISE_VALIDATOR_ENABLED` / `EXERCISE_VALIDATOR_TEACHER` / `EXERCISE_VALIDATOR_GATE_COLLECT` (Compose default `true` / `onnx` / `true`; si falta el ONNX, runtime cae a heuristic)
- Detección de objetos: `OBJECT_DETECT_*` + `YOLO_CONFIG_DIR=/tmp/Ultralytics` (evita PermissionError de Ultralytics en contenedor)
- Modelos ONNX del clasificador: bind mount **`./backend/vision/models`** compartido por `backend` y `worker` — el worker entrena/activa y el backend ve el `manifest.json` actualizado; los artefactos persisten en el host

## Implementación

| Pieza | Ruta |
|-------|------|
| Compose raíz | `docker-compose.yml` |
| Env de ejemplo | `.env.docker.example` |
| Dockerfile API | `backend/Dockerfile` |
| Entrypoint (modelo + Alembic) | `backend/docker/entrypoint.sh` |
| Dockerfile Vite dev | `appWeb/Dockerfile.dev` |
| Dockerfile demo nginx | `appWeb/Dockerfile` + `appWeb/docker/nginx.conf` |
| Redis solo (legado) | `backend/docker-compose.yml` |

Comandos:

```bash
# Stack completo (web + API + db + redis + worker)
docker compose up --build

# Solo infra (si corres API/web en el host)
docker compose up db redis

# Build estático para demo jurado
docker compose --profile demo up --build web-demo backend db redis worker
```

## Incidencias y decisiones

- **NTFS solo lectura en macOS:** si el monorepo vive en un volumen NTFS montado RO, hay que trabajar desde una copia en APFS (o remount RW con Mounty/ntfs-3g) para poder escribir Dockerfiles.
- **Contexto de build:** raíz del monorepo (no solo `backend/`) para copiar `tests/` y respetar `Settings.repo_root()`.
- **Flutter (`app/`) excluido** del stack Docker: legado, fuera del rumbo UI actual.
- El compose de `backend/docker-compose.yml` (solo Redis) se mantiene como atajo legado; el canónico es el de la raíz.
- **2026-08-07 — `vision/models/` sin compartir:** el worker escribía modelo y manifest en su propio contenedor y el backend no los veía; se añadió el bind mount compartido (ver arriba). En la misma fecha se incorporaron a la imagen las dependencias de entrenamiento (`scikit-learn`, `skl2onnx`, `onnx`) y se subió `onnxruntime>=1.22` (IR v11); detalles en [dev-learning-api.md](dev-learning-api.md).

## Pruebas manuales

1. `docker compose up --build` hasta que `backend` esté healthy.
2. `curl -fsS http://localhost:8000/api/v1/health` → 200.
3. Abrir http://localhost:5173 → Configuración / Backend status con `http://localhost:8000`.
4. Análisis en vivo: cámara → overlay + ángulos.
5. (Opcional) `docker compose --profile demo up --build web-demo` → http://localhost:8080.
