#!/bin/sh
set -e

cd /workspace/backend

# Descarga Pose Landmarker si falta (full por defecto).
if [ ! -f models/pose_landmarker_full.task ] && [ ! -f models/pose_landmarker_lite.task ]; then
  echo "[entrypoint] Descargando modelo MediaPipe Pose Landmarker (full)..."
  python scripts/download_models.py full || {
    echo "[entrypoint] AVISO: no se pudo descargar el modelo; la API arrancara pero /ws fallara sin .task"
  }
fi

# Espera PostgreSQL si hay DATABASE_URL.
if [ -n "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] Esperando PostgreSQL..."
  python - <<'PY'
import os, time, sys
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "").strip()
if not url:
    sys.exit(0)

p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
host = p.hostname or "db"
port = p.port or 5432

import socket
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[entrypoint] PostgreSQL listo en {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"[entrypoint] TIMEOUT esperando {host}:{port}", file=sys.stderr)
sys.exit(1)
PY

  echo "[entrypoint] Aplicando migraciones Alembic..."
  alembic upgrade head || {
    echo "[entrypoint] AVISO: alembic upgrade fallo; revisa DATABASE_URL y el esquema"
  }
fi

exec "$@"
