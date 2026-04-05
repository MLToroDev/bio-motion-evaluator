"""Publicación opcional de artefactos ONNX en Hugging Face Hub."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def push_exercise_model(
    *,
    onnx_path: Path,
    manifest_entry: dict[str, Any],
    repo_id: str,
    token: str | None,
    path_in_repo: str = "artifacts/exercise_classifier.onnx",
) -> str | None:
    """
    Sube el ONNX y un JSON de metadatos. Devuelve el commit SHA o None si falla.

    Requiere ``pip install huggingface_hub`` y token con permiso de escritura en ``repo_id``.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        log.warning("huggingface_hub no instalado; omitiendo push")
        return None
    if not token or not str(token).strip():
        log.warning("HF_API_TOKEN vacío; omitiendo push a %s", repo_id)
        return None
    api = HfApi(token=token.strip())
    try:
        api.upload_file(
            path_or_fileobj=str(onnx_path),
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="model",
            commit_message=f"bio-motion exercise_classifier {manifest_entry.get('created_at', '')}",
        )
        meta_path = path_in_repo.replace(".onnx", "_manifest_entry.json")
        manifest_entry_json = json.dumps(manifest_entry, indent=2).encode("utf-8")
        api.upload_file(
            path_or_fileobj=io.BytesIO(manifest_entry_json),
            path_in_repo=meta_path,
            repo_id=repo_id,
            repo_type="model",
            commit_message="manifest entry JSON",
        )
        info = api.repo_info(repo_id=repo_id, repo_type="model")
        sha = getattr(info, "sha", None)
        return str(sha) if sha else "ok"
    except Exception:
        log.exception("Fallo push_exercise_model a %s", repo_id)
        return None


def list_hub_repo_commits(repo_id: str, token: str | None, *, limit: int = 10) -> list[dict[str, Any]]:
    """Lista commits recientes del repo modelo (mejor esfuerzo)."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return []
    if not token or not str(token).strip():
        return []
    try:
        api = HfApi(token=token.strip())
        commits = api.list_repo_commits(repo_id=repo_id, repo_type="model")
        out: list[dict[str, Any]] = []
        for c in commits[:limit]:
            out.append(
                {
                    "commit_sha": getattr(c, "commit_id", None) or getattr(c, "oid", None),
                    "title": getattr(c, "title", None),
                    "date": getattr(c, "created_at", None),
                }
            )
        return out
    except Exception:
        log.exception("list_hub_repo_commits")
        return []
