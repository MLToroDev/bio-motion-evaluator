import sys

from celery import Celery

from app.config import settings

celery_app = Celery(
    "video_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Windows: el pool por defecto (prefork/billiard) suele fallar con WinError 5 al sincronizar workers.
if sys.platform == "win32":
    celery_app.conf.worker_pool = "solo"
