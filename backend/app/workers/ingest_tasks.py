"""Tarea Celery: ingesta automática de vídeos → feature_samples."""

from __future__ import annotations

import logging
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.db.models import FeatureSampleORM, IngestJobORM
from app.db.session import SessionLocal
from app.paths import backend_root
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

_BACKEND_ROOT = backend_root()

# ``from scripts.export_features_from_video`` exige que la raíz del backend esté en
# sys.path (no el directorio ``scripts/`` solo; eso rompe el paquete ``scripts``).
_br = str(_BACKEND_ROOT.resolve())
if _br not in sys.path:
    sys.path.insert(0, _br)


def _search_youtube(query: str, max_results: int) -> list[dict[str, Any]]:
    """Devuelve metadatos de vídeos sin descargarlos."""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
    }
    search_url = f"ytsearch{max_results}:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_url, download=False)
        entries = info.get("entries") or []
        results = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            vid_id = e.get("id") or e.get("display_id") or ""
            url = e.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")
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


def _download_video_temp(url: str, tmpdir: str) -> str | None:
    """Descarga en tmpdir; devuelve ruta al archivo o None si falla."""
    from app.services.video.downloader import download_video

    try:
        path = download_video(
            url=url,
            output_dir=tmpdir,
            filename_template="%(id)s.%(ext)s",
            quality="360p",
        )
        return path
    except Exception:
        log.exception("Error descargando %s", url)
        return None


def _extract_and_insert(
    video_path: Path,
    label: str,
    source_title: str,
    *,
    auto_approve: bool,
    only_window_full: bool,
    require_pose_ok: bool,
    emit_every: int,
    max_frames: int,
    ingest_job_id: uuid.UUID,
    segments: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Extrae features y las inserta en feature_samples. Devuelve métricas."""
    from scripts.export_features_from_video import extract_features_from_file  # type: ignore[import]

    model_path = settings.resolve_model_path(_BACKEND_ROOT)
    cfg = settings.exercise_classifier_config()

    try:
        vectors, frames_read = extract_features_from_file(
            video_path,
            label,
            cfg,
            model_path,
            only_window_full=only_window_full,
            require_pose_ok=require_pose_ok,
            emit_every=emit_every,
            max_frames=max_frames,
            segments=segments or None,
        )
    except Exception:
        log.exception("Error extrayendo features de %s", video_path)
        return {"frames_read": 0, "features_extracted": 0, "samples_inserted": 0}

    if not vectors:
        return {"frames_read": frames_read, "features_extracted": 0, "samples_inserted": 0}

    review = "approved" if auto_approve else "pending"
    inserted = 0
    try:
        db = SessionLocal()
        try:
            for vec in vectors:
                row = FeatureSampleORM(
                    label=label.strip().lower()[:64],
                    label_source="video_ingest",
                    review_status=review,
                    feature_vector=vec,
                    confidence_at_collection=None,
                    pose_ok=True,
                    session_id=None,
                    source_file=source_title[:512] if source_title else None,
                    split="unset",
                    notes=f"ingest_job={ingest_job_id}",
                )
                db.add(row)
                inserted += 1
            db.commit()
        except Exception:
            db.rollback()
            log.exception("Error insertando muestras en BD")
            inserted = 0
        finally:
            db.close()
    except RuntimeError:
        log.warning("BD no configurada; muestras no guardadas.")

    return {
        "frames_read": frames_read,
        "features_extracted": len(vectors),
        "samples_inserted": inserted,
    }


@celery_app.task(bind=True, name="ingest_exercise_videos")
def ingest_exercise_videos(self, job_id_str: str) -> dict[str, Any]:
    job_uuid = uuid.UUID(job_id_str)
    db = SessionLocal()

    def _reload_job() -> IngestJobORM | None:
        return db.query(IngestJobORM).filter(IngestJobORM.id == job_uuid).first()

    try:
        job = _reload_job()
        if not job:
            return {"status": "error", "error": "job not found"}

        job.celery_task_id = self.request.id
        job.status = "running"
        db.commit()

        params = dict(job.params_json or {})
        only_window_full = bool(params.get("only_window_full", True))
        require_pose_ok = bool(params.get("require_pose_ok", True))
        emit_every = max(1, int(params.get("emit_every", 3)))
        max_frames = max(0, int(params.get("max_frames_per_video", 0)))
        video_segments: dict[str, list[dict[str, Any]]] = params.get("video_segments") or {}

        label = (job.exercise_label or "").strip().lower()
        max_videos = max(1, int(job.max_videos or 5))

        # Búsqueda de vídeos
        try:
            video_list = _search_youtube(job.query, max_videos)
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Búsqueda YouTube falló: {e}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed", "error": str(e)}

        job.videos_json = video_list
        db.commit()

        metrics: dict[str, Any] = {
            "frames_read": 0,
            "features_extracted": 0,
            "samples_inserted": 0,
            "videos_processed": 0,
            "videos_failed": 0,
            "per_video": [],
        }

        with tempfile.TemporaryDirectory(prefix="bm_ingest_") as tmpdir:
            for video_info in video_list:
                vid_title = str(video_info.get("title") or "")
                vid_url = str(video_info.get("url") or "")
                if not vid_url:
                    continue

                log.info("Ingestando: %s", vid_title)
                filepath = _download_video_temp(vid_url, tmpdir)
                if not filepath or not Path(filepath).is_file():
                    log.warning("Descarga fallida: %s", vid_url)
                    metrics["videos_failed"] += 1
                    metrics["per_video"].append({"title": vid_title, "status": "download_failed"})
                    continue

                # Segmentos específicos para este vídeo (si los hay)
                vid_id = str(video_info.get("youtube_id") or "")
                vid_segs: list[dict[str, Any]] | None = video_segments.get(vid_id) or None

                vid_metrics = _extract_and_insert(
                    Path(filepath),
                    label,
                    vid_title,
                    auto_approve=bool(job.auto_approve),
                    only_window_full=only_window_full,
                    require_pose_ok=require_pose_ok,
                    emit_every=emit_every,
                    max_frames=max_frames,
                    ingest_job_id=job_uuid,
                    segments=vid_segs,
                )
                vid_metrics["title"] = vid_title
                vid_metrics["url"] = vid_url
                vid_metrics["status"] = "ok"
                metrics["per_video"].append(vid_metrics)
                metrics["frames_read"] += vid_metrics["frames_read"]
                metrics["features_extracted"] += vid_metrics["features_extracted"]
                metrics["samples_inserted"] += vid_metrics["samples_inserted"]
                metrics["videos_processed"] += 1

                # Borrar el archivo descargado inmediatamente
                try:
                    Path(filepath).unlink(missing_ok=True)
                except Exception:
                    pass

                # Actualizar métricas en BD de forma incremental
                j2 = _reload_job()
                if j2:
                    j2.metrics_json = metrics
                    db.commit()

        final_job = _reload_job()
        if final_job:
            final_job.status = "completed"
            final_job.metrics_json = metrics
            final_job.completed_at = datetime.now(timezone.utc)
            db.commit()

        return {"status": "completed", "metrics": metrics}

    except Exception as e:
        log.exception("ingest_exercise_videos %s", job_id_str)
        j = _reload_job()
        if j:
            j.status = "failed"
            j.error_message = str(e)
            j.completed_at = datetime.now(timezone.utc)
            db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
