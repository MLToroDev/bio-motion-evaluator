# ARCH-6: model_registry.py — Carga dinámica de modelos (ver docs/planificacion/bio_motion_plan_v2.md §8)
"""Lectura de ``manifest.json`` para versionar el clasificador de ejercicios."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_MANIFEST_REL = Path("vision") / "models" / "manifest.json"


@dataclass(frozen=True)
class ExerciseModelManifest:
    """Metadatos de un artefacto de clasificación (p. ej. ONNX)."""

    name: str
    path: Path
    classes: tuple[str, ...]
    window_size: int | None = None
    created_at: str | None = None


@dataclass
class ModelRegistry:
    """Registro simple basado en JSON en disco."""

    backend_root: Path
    manifest_path: Path | None = None

    def __post_init__(self) -> None:
        if self.manifest_path is None:
            self.manifest_path = self.backend_root / DEFAULT_MANIFEST_REL

    def _load_raw(self) -> dict[str, Any]:
        p = self.manifest_path
        if p is None or not p.is_file():
            log.info("Model manifest no encontrado: %s", p)
            return {}
        with p.open(encoding="utf-8") as f:
            return json.load(f)

    def load_active_manifest(self) -> ExerciseModelManifest | None:
        data = self._load_raw()
        active = data.get("active")
        models = data.get("models") or {}
        if not active or active not in models:
            return None
        m = models[active]
        rel = m.get("path")
        if not rel:
            return None
        path = Path(rel)
        if not path.is_absolute():
            path = self.backend_root / path
        classes = m.get("classes") or []
        return ExerciseModelManifest(
            name=str(active),
            path=path,
            classes=tuple(str(c) for c in classes),
            window_size=int(m["window_size"]) if m.get("window_size") is not None else None,
            created_at=m.get("created_at"),
        )

    def list_versions(self) -> list[str]:
        data = self._load_raw()
        models = data.get("models") or {}
        return sorted(models.keys())

    def switch_version(self, name: str) -> None:
        """Actualiza la clave ``active`` en el manifest (desarrollo / ops)."""
        p = self.manifest_path
        if p is None or not p.is_file():
            raise FileNotFoundError(f"Manifest no existe: {p}")
        data = self._load_raw()
        models = data.get("models") or {}
        if name not in models:
            raise KeyError(f"Modelo no registrado: {name}")
        data["active"] = name
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def active_key(self) -> str | None:
        data = self._load_raw()
        a = data.get("active")
        return str(a) if a else None

    def manifest_blob(self) -> dict[str, Any]:
        """Copia del JSON del manifest (``active`` + ``models``)."""
        return dict(self._load_raw())

