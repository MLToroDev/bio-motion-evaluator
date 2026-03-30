"""Cliente opcional para Hugging Face Inference API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)


async def run_optional_inference(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Si HF_INFERENCE_URL y HF_API_TOKEN están definidos, envía JSON al endpoint.
    De lo contrario devuelve None (sin error).
    """
    url = settings.hf_inference_url
    if not url:
        return None

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.hf_api_token:
        headers["Authorization"] = f"Bearer {settings.hf_api_token}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            if "application/json" in r.headers.get("content-type", ""):
                return r.json()
            return {"text": r.text}
    except Exception as exc:  # noqa: BLE001
        log.warning("Hugging Face inference falló: %s", exc)
        return {"error": str(exc)}
