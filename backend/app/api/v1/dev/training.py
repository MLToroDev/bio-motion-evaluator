from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import TrainingJobORM
from app.workers.training_tasks import train_exercise_classifier_job

from .deps import get_dev_db

router = APIRouter()


class TrainingJobCreate(BaseModel):
    classes: list[str] = Field(..., min_length=1)
    validation_fraction: float = Field(0.2, ge=0.1, le=0.45)
    set_active: bool = False
    push_hf: bool = False
    seed: int = 42
    n_estimators: int = Field(200, ge=10, le=500)


@router.post("/training/jobs")
def enqueue_training_job(
    body: TrainingJobCreate,
    db: Session = Depends(get_dev_db),
) -> dict[str, Any]:
    class_list = sorted({str(c).strip().lower() for c in body.classes if str(c).strip()})
    if not class_list:
        raise HTTPException(status_code=400, detail="classes vacío")
    job = TrainingJobORM(
        status="pending",
        classes_json=class_list,
        params_json={
            "validation_fraction": float(body.validation_fraction),
            "set_active": bool(body.set_active),
            "push_hf": bool(body.push_hf),
            "seed": int(body.seed),
            "n_estimators": int(body.n_estimators),
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        async_result = train_exercise_classifier_job.delay(str(job.id))
        job.celery_task_id = async_result.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"No se pudo encolar Celery: {e}"
        db.commit()
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"id": str(job.id), "celery_task_id": job.celery_task_id}


@router.get("/training/jobs")
def list_training_jobs(
    db: Session = Depends(get_dev_db),
    skip: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    limit = min(100, max(1, limit))
    skip = max(0, skip)
    q = db.query(TrainingJobORM).order_by(TrainingJobORM.created_at.desc())
    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    items = []
    for r in rows:
        mj = r.metrics_json if isinstance(r.metrics_json, dict) else {}
        items.append(
            {
                "id": str(r.id),
                "status": r.status,
                "sample_count": r.sample_count,
                "model_key": r.model_key,
                "accuracy": mj.get("accuracy"),
                "macro_f1": mj.get("macro_f1"),
                "balanced_accuracy": mj.get("balanced_accuracy"),
                "oob_score": mj.get("oob_score"),
                "oob_score_caveat": mj.get("oob_score_caveat"),
                "split_strategy": mj.get("split_strategy"),
                "leakage_risk": mj.get("leakage_risk"),
                "unreliable_classes": mj.get("unreliable_classes") or [],
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
            }
        )
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/training/jobs/{job_id}")
def get_training_job(job_id: uuid.UUID, db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    r = db.query(TrainingJobORM).filter(TrainingJobORM.id == job_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return {
        "id": str(r.id),
        "status": r.status,
        "celery_task_id": r.celery_task_id,
        "classes_json": r.classes_json,
        "params_json": r.params_json,
        "sample_count": r.sample_count,
        "metrics_json": r.metrics_json,
        "model_key": r.model_key,
        "hf_commit": r.hf_commit,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
