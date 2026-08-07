import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import FeatureSampleORM, TrainingJobORM
from app.db.session import SessionLocal
from app.paths import backend_root
from app.services.hf_hub import push_exercise_model
from app.workers.celery_app import celery_app
from vision.exercise_rf_train import merge_manifest, train_rf_export_onnx

log = logging.getLogger(__name__)

_BACKEND_ROOT = backend_root()


def _load_approved_arrays(
    db: Session,
    class_list: list[str],
) -> tuple[np.ndarray, np.ndarray] | None:
    q = (
        db.query(FeatureSampleORM)
        .filter(
            FeatureSampleORM.review_status == "approved",
            FeatureSampleORM.label.in_(class_list),
        )
        .all()
    )
    if not q:
        return None
    xs: list[list[float]] = []
    ys: list[str] = []
    for row in q:
        vec = row.feature_vector
        if not isinstance(vec, list) or len(vec) != 32:
            continue
        lab = (row.label or "").strip().lower()
        if lab not in class_list:
            continue
        xs.append([float(x) for x in vec])
        ys.append(lab)
    if len(xs) < 2:
        return None
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


@celery_app.task(bind=True, name="train_exercise_classifier")
def train_exercise_classifier_job(self, job_id_str: str) -> dict[str, Any]:
    job_uuid = uuid.UUID(job_id_str)
    with SessionLocal() as db:
        job = db.query(TrainingJobORM).filter(TrainingJobORM.id == job_uuid).first()
        if not job:
            log.error("Training job %s no encontrado", job_id_str)
            return {"status": "error", "error": "job not found"}
        job.status = "running"
        job.celery_task_id = self.request.id
        db.commit()
        classes_raw = job.classes_json or []
        class_list = [str(c).strip().lower() for c in classes_raw if str(c).strip()]
        params = dict(job.params_json or {})
        test_size = float(params.get("validation_fraction", 0.2))
        test_size = min(0.49, max(0.1, test_size))
        set_active = bool(params.get("set_active", False))
        push_hf = bool(params.get("push_hf", False))
        seed = int(params.get("seed", 42))
        n_estimators = int(params.get("n_estimators", 200))

        try:
            arr = _load_approved_arrays(db, class_list)
            if arr is None:
                raise ValueError(
                    "No hay muestras aprobadas suficientes para las clases indicadas (mín. 2 filas válidas).",
                )
            X, y_str = arr
            job.sample_count = int(X.shape[0])
            db.commit()

            model_key = f"exercise_rf_{job_uuid.hex[:8]}"
            out_path = _BACKEND_ROOT / "vision" / "models" / f"{model_key}.onnx"
            metrics = train_rf_export_onnx(
                X,
                y_str,
                class_list,
                out_path,
                test_size=test_size,
                seed=seed,
                n_estimators=n_estimators,
            )

            out_abs = out_path.resolve()
            try:
                onnx_rel = out_abs.relative_to(_BACKEND_ROOT).as_posix()
            except ValueError:
                onnx_rel = out_abs.as_posix()

            manifest_path = _BACKEND_ROOT / "vision" / "models" / "manifest.json"
            merge_manifest(
                manifest_path,
                _BACKEND_ROOT,
                model_key,
                onnx_rel,
                class_list,
                settings.classifier_window_size_frames,
                set_active=set_active,
                note=f"Celery train_exercise_classifier job={job_uuid}",
            )

            hf_sha: str | None = None
            if push_hf and settings.hf_model_repo_id:
                entry = {
                    "path": onnx_rel,
                    "classes": class_list,
                    "window_size": settings.classifier_window_size_frames,
                    "feature_vector_dim": 32,
                    "model_key": model_key,
                }
                hf_sha = push_exercise_model(
                    onnx_path=out_abs,
                    manifest_entry=entry,
                    repo_id=settings.hf_model_repo_id,
                    token=settings.hf_api_token,
                    path_in_repo=f"artifacts/{model_key}.onnx",
                )

            job_reload = db.query(TrainingJobORM).filter(TrainingJobORM.id == job_uuid).first()
            if job_reload:
                job_reload.status = "completed"
                job_reload.metrics_json = metrics
                job_reload.model_key = model_key
                job_reload.hf_commit = hf_sha
                job_reload.completed_at = datetime.now(timezone.utc)
                db.commit()

            return {"status": "completed", "model_key": model_key, "metrics": metrics}
        except Exception as e:
            log.exception("train_exercise_classifier_job %s", job_id_str)
            job_fail = db.query(TrainingJobORM).filter(TrainingJobORM.id == job_uuid).first()
            if job_fail:
                job_fail.status = "failed"
                job_fail.error_message = str(e)
                job_fail.completed_at = datetime.now(timezone.utc)
                db.commit()
            return {"status": "failed", "error": str(e)}
