"""Catálogo de ejercicios (público): etiquetas del clasificador + enriquecimiento UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.paths import backend_root

router = APIRouter(prefix="/exercises", tags=["exercises"])

_CDN_DEFAULT = "https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@main/"


def _catalog_path() -> Path:
    return backend_root() / "vision" / "data" / "exercise_catalog.json"


def load_exercise_catalog() -> dict[str, Any]:
    cp = _catalog_path()
    if not cp.is_file():
        return {"version": 0, "exercises": [], "external_dataset": {}}
    with cp.open(encoding="utf-8") as f:
        return json.load(f)


def enrich_exercise_entry(ex: dict[str, Any], cdn_base: str) -> dict[str, Any]:
    """Añade gif_url absoluto si hay gif_path relativo al dataset externo."""
    out = dict(ex)
    gif_path = (ex.get("gif_path") or "").strip()
    if gif_path:
        base = cdn_base if cdn_base.endswith("/") else cdn_base + "/"
        out["gif_url"] = base + gif_path.lstrip("/")
    return out


@router.get("/catalog")
def get_exercise_catalog() -> dict[str, Any]:
    """
    Catálogo activo del motor (ids = etiquetas del clasificador).

    Incluye metadatos de presentación (display_es, músculo, GIF vía CDN del
    dataset hasaneyldrm/exercises-dataset). No es un detector de pose.
    """
    raw = load_exercise_catalog()
    external = raw.get("external_dataset") or {}
    cdn = str(external.get("cdn_base") or _CDN_DEFAULT)
    exercises = [enrich_exercise_entry(e, cdn) for e in (raw.get("exercises") or []) if isinstance(e, dict)]
    return {
        "version": raw.get("version"),
        "source_note_es": raw.get("source_note_es"),
        "external_dataset": external,
        "camera_protocol": raw.get("camera_protocol"),
        "exercises": exercises,
        "by_id": {str(e.get("id")): e for e in exercises if e.get("id")},
    }
