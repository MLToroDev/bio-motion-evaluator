"""
Entrenamiento del teacher/validador de ejercicio (RF → ONNX, vector 32D).

Produce un artefacto distinto del clasificador primario (`exercise_rf_*`):
`vision/models/exercise_validator*.onnx`, pensado para confirmar / rechazar
la etiqueta primaria o senalar cambio de ejercicio en runtime.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from vision.exercise_rf_train import FEATURE_DIM, train_rf_export_onnx

log = logging.getLogger(__name__)

VALIDATOR_STABLE_NAME = "exercise_validator.onnx"
VALIDATOR_CLASSES_SIDECAR = "exercise_validator.classes.json"
MANIFEST_VALIDATOR_ACTIVE_KEY = "validator_active"


def default_validator_models_dir(backend_root: Path) -> Path:
    return backend_root / "vision" / "models"


def resolve_validator_onnx_path(
    backend_root: Path,
    *,
    explicit: str | Path | None = None,
) -> Path:
    """
    Resuelve la ruta del teacher ONNX.

    Orden: ruta explicita (abs o relativa a backend) → ``exercise_validator.onnx``
    estable → primera coincidencia ``exercise_validator_*.onnx`` por mtime.
    """
    if explicit:
        p = Path(str(explicit).strip())
        if not p.is_absolute():
            p = backend_root / p
        return p.resolve()

    models = default_validator_models_dir(backend_root)
    stable = models / VALIDATOR_STABLE_NAME
    if stable.is_file():
        return stable.resolve()

    candidates = sorted(
        models.glob("exercise_validator_*.onnx"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0].resolve()
    return stable.resolve()


def load_validator_classes(
    backend_root: Path,
    *,
    onnx_path: Path | None = None,
    classes_csv: str | None = None,
    manifest_path: Path | None = None,
) -> list[str] | None:
    """Carga lista de clases: env CSV → sidecar JSON → entrada active del manifest."""
    if classes_csv and classes_csv.strip():
        return [c.strip().lower() for c in classes_csv.split(",") if c.strip()]

    path = onnx_path or resolve_validator_onnx_path(backend_root)
    sidecar = path.with_suffix(".classes.json")
    if not sidecar.is_file():
        sidecar = path.parent / VALIDATOR_CLASSES_SIDECAR
    if sidecar.is_file():
        with sidecar.open(encoding="utf-8") as f:
            data = json.load(f)
        classes = data.get("classes") or data.get("class_names") or []
        out = [str(c).strip().lower() for c in classes if str(c).strip()]
        if out:
            return out

    mp = manifest_path or (backend_root / "vision" / "models" / "manifest.json")
    if mp.is_file():
        with mp.open(encoding="utf-8") as f:
            data = json.load(f)
        active = data.get(MANIFEST_VALIDATOR_ACTIVE_KEY)
        models = data.get("models") or {}
        if active and active in models:
            classes = models[active].get("classes") or []
            out = [str(c).strip().lower() for c in classes if str(c).strip()]
            if out:
                return out
    return None


def write_classes_sidecar(path: Path, class_list: list[str]) -> Path:
    """Escribe JSON de clases junto al ONNX (y copia estable si aplica)."""
    path = Path(path)
    payload = {
        "classes": list(class_list),
        "feature_vector_dim": FEATURE_DIM,
        "role": "exercise_validator",
        "updated_at": _dt.date.today().isoformat(),
    }
    targets = [path.with_suffix(".classes.json")]
    stable_dir = path.parent
    stable_side = stable_dir / VALIDATOR_CLASSES_SIDECAR
    if path.name != VALIDATOR_STABLE_NAME:
        targets.append(stable_side)
    else:
        targets = [stable_side, path.with_suffix(".classes.json")]

    written = targets[0]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        with t.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        written = t
    return written


def merge_validator_manifest(
    manifest_path: Path,
    backend_root: Path,
    model_key: str,
    onnx_rel_posix: str,
    class_list: list[str],
    window_size: int,
    *,
    set_active: bool,
    note: str | None = None,
) -> None:
    """Registra el teacher en ``manifest.json`` sin tocar ``active`` del clasificador primario."""
    manifest_path = manifest_path.expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (backend_root / manifest_path).resolve()
    data: dict[str, Any] = {}
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as f:
            data = json.load(f)
    models = dict(data.get("models") or {})
    models[model_key] = {
        "path": onnx_rel_posix,
        "classes": class_list,
        "window_size": window_size,
        "feature_vector_dim": FEATURE_DIM,
        "role": "exercise_validator",
        "created_at": _dt.date.today().isoformat(),
        "note": note or "RandomForest teacher (vision/exercise_validator_train.py)",
    }
    data["models"] = models
    if set_active:
        data[MANIFEST_VALIDATOR_ACTIVE_KEY] = model_key
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _model_key_from_bytes(payload: bytes) -> str:
    digest = hashlib.sha1(payload).hexdigest()[:8]
    return f"exercise_validator_{digest}"


def train_validator_export_onnx(
    X: np.ndarray,
    y_str: np.ndarray,
    class_list: list[str],
    backend_root: Path,
    *,
    out_dir: Path | None = None,
    test_size: float = 0.2,
    seed: int = 42,
    n_estimators: int = 120,
    window_size: int = 45,
    set_manifest_active: bool = True,
    write_stable_copy: bool = True,
) -> dict[str, Any]:
    """
    Entrena RF teacher, escribe ONNX versionado + copia estable ``exercise_validator.onnx``.

    Returns:
        Metricas de entrenamiento + rutas absolutas del artefacto.
    """
    models_dir = out_dir or default_validator_models_dir(backend_root)
    models_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = models_dir / f"_tmp_validator_{seed}.onnx"
    metrics = train_rf_export_onnx(
        X,
        y_str,
        class_list,
        tmp_path,
        test_size=test_size,
        seed=seed,
        n_estimators=n_estimators,
    )
    raw = tmp_path.read_bytes()
    model_key = _model_key_from_bytes(raw)
    versioned = models_dir / f"{model_key}.onnx"
    versioned.write_bytes(raw)
    tmp_path.unlink(missing_ok=True)

    stable = models_dir / VALIDATOR_STABLE_NAME
    if write_stable_copy:
        shutil.copy2(versioned, stable)

    write_classes_sidecar(versioned if not write_stable_copy else stable, class_list)

    try:
        onnx_rel = versioned.resolve().relative_to(backend_root.resolve()).as_posix()
    except ValueError:
        onnx_rel = versioned.resolve().as_posix()

    manifest_path = models_dir / "manifest.json"
    merge_validator_manifest(
        manifest_path,
        backend_root,
        model_key,
        onnx_rel,
        class_list,
        window_size,
        set_active=set_manifest_active,
        note="RandomForest teacher (train_validator_export_onnx)",
    )

    metrics = dict(metrics)
    metrics["model_key"] = model_key
    metrics["onnx_path"] = str(versioned.resolve())
    metrics["stable_onnx_path"] = str(stable.resolve()) if write_stable_copy else None
    metrics["role"] = "exercise_validator"
    return metrics
