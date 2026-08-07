from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import FeatureSampleORM, TrainingJobORM
from app.paths import backend_root

from .deps import get_dev_db

router = APIRouter()


def _catalog_path() -> Path:
    return backend_root() / "vision" / "data" / "exercise_catalog.json"


class FeatureSampleCreate(BaseModel):
    features: list[float] = Field(..., min_length=32, max_length=32)
    label: str
    notes: str | None = None
    label_source: str = "manual"


class FeatureSamplePatch(BaseModel):
    label: str | None = None
    review_status: str | None = None
    split: str | None = None
    notes: str | None = None


class BulkApproveBody(BaseModel):
    ids: list[uuid.UUID]


def _compute_stats(db: Session) -> dict[str, Any]:
    rows = (
        db.query(
            FeatureSampleORM.label,
            FeatureSampleORM.review_status,
            func.count(FeatureSampleORM.id),
        )
        .group_by(FeatureSampleORM.label, FeatureSampleORM.review_status)
        .all()
    )
    by_label: dict[str, dict[str, int]] = {}
    totals = {"pending": 0, "approved": 0, "rejected": 0, "all": 0}
    for lab, st, cnt in rows:
        lab_k = (lab or "").strip().lower()
        st_k = (st or "").strip().lower()
        by_label.setdefault(lab_k, {"pending": 0, "approved": 0, "rejected": 0})
        if st_k in by_label[lab_k]:
            by_label[lab_k][st_k] += int(cnt)
        if st_k in totals:
            totals[st_k] += int(cnt)
        totals["all"] += int(cnt)
    return {"by_label": by_label, "totals": totals}


@router.get("/catalog")
def get_catalog_summary(db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    """Catálogo de ejercicios + conteos de muestras y último F1 por clase."""
    cp = _catalog_path()
    exercises: list[dict[str, Any]] = []
    if cp.is_file():
        with cp.open(encoding="utf-8") as f:
            data = json.load(f)
            exercises = list(data.get("exercises") or [])
    stats = _compute_stats(db)
    last_f1: dict[str, float] = {}
    last_job = (
        db.query(TrainingJobORM)
        .filter(TrainingJobORM.status == "completed")
        .order_by(TrainingJobORM.completed_at.desc())
        .first()
    )
    if last_job and isinstance(last_job.metrics_json, dict):
        raw = last_job.metrics_json.get("f1_per_class")
        if isinstance(raw, dict):
            last_f1 = {str(k): float(v) for k, v in raw.items()}
    return {"exercises": exercises, "stats": stats, "last_f1_per_class": last_f1}


@router.get("/samples/stats")
def samples_stats(db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    return _compute_stats(db)


@router.get("/samples")
def list_samples(
    db: Session = Depends(get_dev_db),
    label: str | None = None,
    review_status: str | None = None,
    split: str | None = None,
    label_source: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    limit = min(500, max(1, limit))
    skip = max(0, skip)
    q = db.query(FeatureSampleORM)
    if label:
        q = q.filter(FeatureSampleORM.label == label.strip().lower())
    if review_status:
        q = q.filter(FeatureSampleORM.review_status == review_status.strip().lower())
    if split:
        q = q.filter(FeatureSampleORM.split == split.strip().lower())
    if label_source:
        q = q.filter(FeatureSampleORM.label_source == label_source.strip().lower())
    total = q.count()
    rows = q.order_by(FeatureSampleORM.recorded_at.desc()).offset(skip).limit(limit).all()
    items = []
    for r in rows:
        items.append(
            {
                "id": str(r.id),
                "label": r.label,
                "label_source": r.label_source,
                "review_status": r.review_status,
                "confidence_at_collection": r.confidence_at_collection,
                "pose_ok": r.pose_ok,
                "split": r.split,
                "notes": r.notes,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
                "feature_vector_preview": (r.feature_vector[:4] if isinstance(r.feature_vector, list) else []),
            }
        )
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/samples/{sample_id}")
def get_sample(sample_id: uuid.UUID, db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    r = db.query(FeatureSampleORM).filter(FeatureSampleORM.id == sample_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")
    return {
        "id": str(r.id),
        "label": r.label,
        "label_source": r.label_source,
        "review_status": r.review_status,
        "feature_vector": r.feature_vector,
        "confidence_at_collection": r.confidence_at_collection,
        "pose_ok": r.pose_ok,
        "split": r.split,
        "notes": r.notes,
        "session_id": str(r.session_id) if r.session_id else None,
        "source_file": r.source_file,
        "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
    }


@router.post("/samples")
def create_sample(body: FeatureSampleCreate, db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    row = FeatureSampleORM(
        label=body.label.strip().lower()[:64],
        label_source=(body.label_source or "manual")[:32],
        review_status="pending",
        feature_vector=[float(x) for x in body.features],
        confidence_at_collection=None,
        pose_ok=True,
        session_id=None,
        source_file=None,
        split="unset",
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id)}


@router.patch("/samples/{sample_id}")
def patch_sample(
    sample_id: uuid.UUID,
    body: FeatureSamplePatch,
    db: Session = Depends(get_dev_db),
) -> dict[str, str]:
    r = db.query(FeatureSampleORM).filter(FeatureSampleORM.id == sample_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")
    if body.label is not None:
        r.label = body.label.strip().lower()[:64]
    if body.review_status is not None:
        rs = body.review_status.strip().lower()
        if rs not in ("pending", "approved", "rejected"):
            raise HTTPException(status_code=400, detail="review_status inválido")
        r.review_status = rs
    if body.split is not None:
        sp = body.split.strip().lower()
        if sp not in ("unset", "train", "val", "test"):
            raise HTTPException(status_code=400, detail="split inválido")
        r.split = sp
    if body.notes is not None:
        r.notes = body.notes
    db.commit()
    return {"status": "ok"}


@router.delete("/samples/{sample_id}")
def delete_sample(sample_id: uuid.UUID, db: Session = Depends(get_dev_db)) -> dict[str, str]:
    r = db.query(FeatureSampleORM).filter(FeatureSampleORM.id == sample_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")
    db.delete(r)
    db.commit()
    return {"status": "ok"}


@router.post("/samples/bulk-approve")
def bulk_approve(body: BulkApproveBody, db: Session = Depends(get_dev_db)) -> dict[str, Any]:
    n = 0
    for sid in body.ids:
        r = db.query(FeatureSampleORM).filter(FeatureSampleORM.id == sid).first()
        if r:
            r.review_status = "approved"
            n += 1
    db.commit()
    return {"approved": n}
