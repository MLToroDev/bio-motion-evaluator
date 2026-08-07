# Configuración del entorno (Windows)

## GitHub CLI (`gh`)

1. Instalación (elige uno):
   - **winget:** `winget install --id GitHub.cli -e --accept-package-agreements`
   - **Descarga:** [https://cli.github.com/](https://cli.github.com/)
2. Cierra y vuelve a abrir la terminal para refrescar el `PATH`.
3. Autenticación (interactiva):
   ```bash
   gh auth login
   ```

## Flutter

1. Descarga el SDK desde [Install Flutter on Windows](https://docs.flutter.dev/get-started/install/windows).
2. Extrae el SDK y añade `flutter\bin` al **PATH** del sistema (o de usuario).
3. Ejecuta:
   ```bash
   flutter doctor
   ```
4. En este monorepo, dentro de `app/`:
   ```bash
   cd app
   flutter create . --platforms=web,android,ios --project-name bio_motion_app
   flutter pub get
   ```

## Crear el repositorio remoto y subir código

Desde la raíz del monorepo (donde está `README.md`):

**PowerShell (Windows):** tras `gh auth login`, puedes ejecutar [`scripts/publish-github.ps1`](../../scripts/publish-github.ps1).

```bash
git add .
git commit -m "chore: estructura inicial monorepo bio-motion-evaluator"
gh repo create bio-motion-evaluator --public --source=. --remote=origin --push
```

Si el remoto ya existe:

```bash
git remote add origin https://github.com/TU_USUARIO/bio-motion-evaluator.git
git push -u origin main
```

**(Nota)** Si la rama por defecto es `master`, usa `git branch -M main` antes del push.

## MediaPipe (backend)

Tras `pip install -r requirements.txt`, descarga el modelo de pose:

```bash
cd backend
python scripts/download_models.py
```

Por defecto se descarga **pose_landmarker_full.task** (más preciso). Para **lite** (más FPS): `python scripts/download_models.py lite` y `MEDIAPIPE_POSE_MODEL_PATH=models/pose_landmarker_lite.task` en `.env`.

La ruta del modelo se puede configurar con `MEDIAPIPE_POSE_MODEL_PATH` en `.env` (ver `backend/.env.example`).

## Docker Compose (recomendado para demo / onboarding)

Requisitos: Docker Desktop (o Engine + Compose v2). Spec: [`docs/spec/docker-compose-stack.md`](../spec/docker-compose-stack.md).

Desde la **raíz del monorepo**:

```bash
# Opcional: variables (puertos, JWT, flags MVP)
cp .env.docker.example .env

docker compose up --build
```

| Servicio | URL |
|----------|-----|
| Cliente React (Vite) | http://localhost:5173 |
| API FastAPI | http://localhost:8000 — salud `/api/v1/health`, docs `/docs` |
| PostgreSQL | `localhost:5432` (user/db `biomotion`) |
| Redis | `localhost:6379` |

En **Configuración** del cliente usa `http://localhost:8000`. El entrypoint del backend descarga el modelo MediaPipe si falta en `backend/models/` y aplica migraciones Alembic.

Demo estática (nginx, build de producción):

```bash
docker compose --profile demo up --build web-demo backend db redis worker
# → http://localhost:8080
```

Solo infra (API y web en el host):

```bash
docker compose up db redis
```

## Desarrollo con recarga activa (sin Docker)

- **FastAPI:** usa siempre `uvicorn ... --reload`, que reinicia el servidor al guardar cambios en `.py`. Script: [`scripts/start-dev-backend.ps1`](../../scripts/start-dev-backend.ps1) desde la raíz.
- **appWeb:** `cd appWeb && npm run dev` (Vite).
- **Flutter (legado):** el comando `flutter run` se queda en ejecución; en la misma terminal **r** = hot reload, **R** = hot restart. Script: [`scripts/start-dev-flutter.ps1`](../../scripts/start-dev-flutter.ps1).
- Mantén **API + appWeb** en paralelo (dos terminales) si no usas Compose.

