"""Listado de vídeos gold standard bajo ``tests/assets/videos`` (análisis por archivo)."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from vision.paths import list_gold_standard_video_filenames

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/gold-standard-videos")
async def get_gold_standard_videos() -> dict[str, list[str]]:
    """Nombres de archivo listos para ``video_filename`` en ``/ws/pose-stream``."""
    base = settings.gold_standard_videos_dir()
    return {"filenames": list_gold_standard_video_filenames(base)}
