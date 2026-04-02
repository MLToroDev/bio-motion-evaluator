"""Rutas ancla del backend (independientes de la profundidad del módulo que las importa)."""

from pathlib import Path


def backend_root() -> Path:
    """Directorio que contiene `app/`, `vision/` y `models/` (carpeta `backend/` del repo)."""
    return Path(__file__).resolve().parent.parent
