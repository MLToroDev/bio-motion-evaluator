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


def list_gold_standard_video_filenames(base_dir: Path) -> list[str]:
    """
    Nombres de archivo (solo base) de vídeos con extensión permitida en ``base_dir``.
    Orden lexicográfico insensible a mayúsculas. Si el directorio no existe, lista vacía.
    """
    base = base_dir.resolve()
    if not base.is_dir():
        return []
    out: list[str] = []
    for p in base.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() not in _ALLOWED_SUFFIX:
            continue
        out.append(p.name)
    return sorted(out, key=str.lower)

