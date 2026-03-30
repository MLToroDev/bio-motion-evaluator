"""Resolución segura de rutas a vídeos gold standard (anti path traversal)."""

from __future__ import annotations

from pathlib import Path

_ALLOWED_SUFFIX = (".mp4", ".mov", ".avi", ".mkv", ".webm")


def resolve_gold_standard_video(filename: str, base_dir: Path) -> Path:
    """
    Devuelve la ruta absoluta a un vídeo dentro de ``base_dir``.

    Solo se permite el nombre base del archivo (sin componentes de ruta).
    """
    base = base_dir.resolve()
    filename = filename.strip()
    name = Path(filename).name
    if not name or Path(filename) != Path(name):
        raise ValueError("Use solo el nombre del archivo (sin rutas relativas).")
    if not name.lower().endswith(_ALLOWED_SUFFIX):
        raise ValueError(f"Extensión no permitida; use una de: {_ALLOWED_SUFFIX}")
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("Ruta fuera del directorio de vídeos de referencia.") from exc
    return target
