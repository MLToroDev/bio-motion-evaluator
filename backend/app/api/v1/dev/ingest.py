"""Rutas /dev/ingest — búsqueda YouTube e ingesta automática de vídeos para feature_samples."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import IngestJobORM
from app.workers.ingest_tasks import ingest_exercise_videos

from .deps import get_dev_db

log = logging.getLogger(__name__)

router = APIRouter()

_YT_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


@router.get("/ingest/thumb")
async def proxy_youtube_thumbnail(
    video_id: str = Query(..., alias="id", description="Identificador del vídeo en YouTube (sin URL)."),
) -> Response:
    """
    Proxy de miniatura ``mqdefault.jpg`` desde ``img.youtube.com``.

    Evita bloqueos del navegador (CORS / Referer) al cargar previews en la UI de desarrollo.
    Requiere las mismas reglas de autenticación que el resto de ``/dev`` (cabecera ``X-Dev-API-Key`` si está configurada).
    Para usar en ``<img src>`` sin cabeceras, el cliente debe obtener el binario vía ``fetch`` con la clave y un blob URL.
    """
    vid = (video_id or "").strip()
    if not _YT_VIDEO_ID_RE.match(vid):
        raise HTTPException(status_code=400, detail="id de YouTube inválido")
    url = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BioMotionEvaluator/1.0; +https://github.com/)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.youtube.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
    except httpx.RequestError as e:
        log.warning("YouTube thumbnail fetch failed: %s", e)
        raise HTTPException(status_code=502, detail="No se pudo contactar el servidor de miniaturas") from e

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Miniatura no disponible (HTTP {r.status_code})")

    ct = r.headers.get("content-type", "").split(";")[0].strip() or "image/jpeg"
    if not ct.startswith("image/"):
        ct = "image/jpeg"

    return Response(
        content=r.content,
        media_type=ct,
        headers={
            "Cache-Control": "public, max-age=86400",
        },
    )


def _yt_search(q: str, limit: int) -> list[dict[str, Any]]:
    """Búsqueda en YouTube sin descargar. Devuelve lista de metadatos."""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
    }
    search_url = f"ytsearch{limit}:{q}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_url, download=False)
        entries = info.get("entries") or []
        results = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            vid_id = str(e.get("id") or e.get("display_id") or "")
            url = str(e.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""))
            results.append(
                {
                    "title": str(e.get("title") or ""),
                    "url": url,
                    "youtube_id": vid_id,
                    "duration_s": int(e.get("duration") or 0),
                    "channel": str(e.get("channel") or e.get("uploader") or ""),
                    "thumbnail_url": str(e.get("thumbnail") or ""),
                    "view_count": int(e.get("view_count") or 0),
                }
            )
        return results


@router.get("/ingest/search")
async def search_youtube(q: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Busca en YouTube usando yt-dlp (sin descargar).
    Devuelve hasta ``limit`` resultados con metadatos del vídeo.
    """
    if not q.strip():
        return []
    limit = min(15, max(1, limit))
    try:
        results = await asyncio.to_thread(_yt_search, q.strip(), limit)
        return results
    except Exception as e:
        log.exception("YouTube search failed: %s", q)
        raise HTTPException(status_code=502, detail=f"Búsqueda YouTube falló: {e}") from e


class IngestParams(BaseModel):
    only_window_full: bool = True
    require_pose_ok: bool = True
    emit_every: int = Field(3, ge=1, le=30)
    max_frames_per_video: int = Field(0, ge=0)
    video_segments: dict[str, list[dict[str, float]]] = Field(
        default_factory=dict,
        description=(
            "Mapa youtube_id → lista de tramos {start_sec, end_sec}. "
            "Si el id no aparece o la lista está vacía, se procesa el vídeo completo."
        ),
    )


class IngestJobCreate(BaseModel):
    label: str
    query: str
    source_type: str = "youtube_search"
    max_videos: int = Field(5, ge=1, le=20)
    auto_approve: bool = False
    params: IngestParams = Field(default_factory=IngestParams)


@router.post("/ingest/jobs")
def create_ingest_job(
    body: IngestJobCreate,
    db: Session = Depends(get_dev_db),
) -> dict[str, Any]:
    label = body.label.strip().lower()[:64]
    if not label:
        raise HTTPException(status_code=400, detail="label vacío")
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query vacío")

    job = IngestJobORM(
        status="pending",
        exercise_label=label,
        source_type=body.source_type[:32],
        query=body.query.strip(),
        max_videos=int(body.max_videos),
        auto_approve=bool(body.auto_approve),
        params_json=body.params.model_dump(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        async_result = ingest_exercise_videos.delay(str(job.id))
        job.celery_task_id = async_result.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"No se pudo encolar Celery: {e}"
        db.commit()
        raise HTTPException(status_code=503, detail=str(e)) from e

    return {"id": str(job.id), "celery_task_id": job.celery_task_id}


@router.get("/ingest/jobs")
def list_ingest_jobs(
    db: Session = Depends(get_dev_db),
    skip: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    limit = min(100, max(1, limit))
    q = db.query(IngestJobORM).order_by(IngestJobORM.created_at.desc())
    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    items = []
    for r in rows:
        m = r.metrics_json or {}
        items.append(
            {
                "id": str(r.id),
                "status": r.status,
                "exercise_label": r.exercise_label,
                "query": r.query,
                "source_type": r.source_type,
                "max_videos": r.max_videos,
                "auto_approve": r.auto_approve,
                "videos_processed": m.get("videos_processed"),
                "samples_inserted": m.get("samples_inserted"),
                "features_extracted": m.get("features_extracted"),
                "videos_failed": m.get("videos_failed"),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
            }
        )
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: uuid.UUID, db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    r = db.query(IngestJobORM).filter(IngestJobORM.id == job_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return {
        "id": str(r.id),
        "status": r.status,
        "celery_task_id": r.celery_task_id,
        "exercise_label": r.exercise_label,
        "query": r.query,
        "source_type": r.source_type,
        "max_videos": r.max_videos,
        "auto_approve": r.auto_approve,
        "params_json": r.params_json,
        "videos_json": r.videos_json,
        "metrics_json": r.metrics_json,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
