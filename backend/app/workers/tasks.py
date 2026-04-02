import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import VideoDownloadJobORM
from app.services.video.downloader import download_video
from app.workers.celery_app import celery_app
from app.config import settings

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="download_and_process_video")
def download_and_process_video(self, job_id_str: str, url: str, quality: str = "best") -> dict:
    """
    Celery task run in background.
    """
    job_id = uuid.UUID(job_id_str)
    
    with SessionLocal() as db:
        job: Optional[VideoDownloadJobORM] = db.query(VideoDownloadJobORM).filter(VideoDownloadJobORM.id == job_id).first()
        
        if not job:
            log.error("Job %s no encontrado", job_id)
            return {"status": "error", "error": "Job not found"}

        try:
            job.status = "processing"
            job.celery_task_id = self.request.id
            db.commit()

            # Descargar video
            output_dir = settings.downloads_dir
            filepath = download_video(
                url=url,
                output_dir=output_dir,
                filename_template=f"{job.id}.%(ext)s",
                quality=quality,
            )

            # Actualizar job db al terminar
            job.status = "completed"
            job.file_path = filepath
            db.commit()

            log.info("Job %s completado con éxito. Archivo: %s", job_id, filepath)
            return {"status": "completed", "file_path": filepath}

        except Exception as e:
            db.rollback()
            log.exception("Error procesando job %s", job_id)
            
            # Recargar y actualizar a fallido
            job = db.query(VideoDownloadJobORM).filter(VideoDownloadJobORM.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
            
            return {"status": "failed", "error": str(e)}
