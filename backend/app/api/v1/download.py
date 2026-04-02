import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import VideoDownloadJobORM
from app.workers.tasks import download_and_process_video

router = APIRouter(prefix="/download", tags=["Descargas de Video"])


class DownloadRequest(BaseModel):
    url: HttpUrl


class DownloadResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: UUID
    status: str
    file_path: str | None = None
    error_message: str | None = None


@router.post("", response_model=DownloadResponse, status_code=status.HTTP_202_ACCEPTED)
def request_download(payload: DownloadRequest, db: Session = Depends(get_db)):
    """
    Inicia un trabajo en segundo plano para descargar un video.
    """
    job = VideoDownloadJobORM(url=str(payload.url))
    db.add(job)
    db.commit()
    db.refresh(job)

    # Disparar tarea a celery
    download_and_process_video.delay(str(job.id), str(payload.url))

    return DownloadResponse(
        job_id=job.id,
        status=job.status,
        message="Tarea enviada a la cola"
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
def get_download_status(job_id: UUID, db: Session = Depends(get_db)):
    """
    Consulta el estado de una descarga.
    """
    job = db.query(VideoDownloadJobORM).filter(VideoDownloadJobORM.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")

    return StatusResponse(
        job_id=job.id,
        status=job.status,
        file_path=job.file_path,
        error_message=job.error_message
    )


@router.get("/file/{job_id}")
def get_download_file(job_id: UUID, db: Session = Depends(get_db)):
    """
    Descarga o sirve el video final generado.
    """
    job = db.query(VideoDownloadJobORM).filter(VideoDownloadJobORM.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")

    if job.status != "completed" or not job.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archivo no está listo o falló la descarga")

    if not os.path.exists(job.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado en el servidor")

    filename = os.path.basename(job.file_path)
    return FileResponse(path=job.file_path, filename=filename, media_type="video/mp4")


@router.delete("/cleanup/{job_id}")
def cleanup_download(job_id: UUID, db: Session = Depends(get_db)):
    """
    Elimina los archivos generados y el registro de la base de datos.
    """
    job = db.query(VideoDownloadJobORM).filter(VideoDownloadJobORM.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")

    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except Exception as e:
            # Continuar de todas formas con la eliminación en db.
            pass

    db.delete(job)
    db.commit()

    return {"message": "Job limpiado correctamente"}
