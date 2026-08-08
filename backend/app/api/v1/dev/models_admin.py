"""Rutas /dev/models — lectura y activación del manifest local."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.paths import backend_root
from vision.model_registry import ModelRegistry

router = APIRouter()


@router.get("/models")
def list_models() -> dict[str, Any]:
    reg = ModelRegistry(backend_root())
    blob = reg.manifest_blob()
    active = blob.get("active")
    models = blob.get("models") or {}
    items = []
    for key, meta in models.items():
        if not isinstance(meta, dict):
            continue
        items.append(
            {
                "key": key,
                "path": meta.get("path"),
                "classes": meta.get("classes"),
                "window_size": meta.get("window_size"),
                "created_at": meta.get("created_at"),
                "note": meta.get("note"),
                "is_active": key == active,
                "metrics": meta.get("metrics"),
                "training_params": meta.get("training_params"),
                "dataset_snapshot": meta.get("dataset_snapshot"),
                "role": meta.get("role"),
            }
        )
    items.sort(key=lambda x: str(x.get("key")))
    return {
        "active": active,
        "validator_active": blob.get("validator_active"),
        "manifest_version": blob.get("manifest_version"),
        "items": items,
    }


@router.get("/models/{model_key}")
def get_model_detail(model_key: str) -> dict[str, Any]:
    reg = ModelRegistry(backend_root())
    blob = reg.manifest_blob()
    models = blob.get("models") or {}
    if model_key not in models:
        raise HTTPException(status_code=404, detail="Modelo no registrado")
    return {"key": model_key, "meta": models[model_key], "active": blob.get("active")}


@router.post("/models/{model_key}/activate")
def activate_model(model_key: str) -> dict[str, str]:
    reg = ModelRegistry(backend_root())
    try:
        reg.switch_version(model_key)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "ok", "active": model_key}
