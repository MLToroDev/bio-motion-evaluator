"""Persistencia síncrona de feature samples (invocable desde hilo de inferencia o Celery)."""

from __future__ import annotations

import logging
import uuid

from app.config import settings
from app.db.models import FeatureSampleORM
from app.db.session import SessionLocal, engine_configured
from vision.feature_collector import FeatureCollector

log = logging.getLogger(__name__)


def save_auto_collected_sample(
    feature_vector: list[float],
    label: str,
    confidence: float,
    pose_ok: bool,
    session_id: uuid.UUID | None,
    label_source: str = "auto_soft",
) -> None:
    """Inserta una fila en estado ``pending`` (``auto_soft`` o ``auto_validated``)."""
    if not engine_configured():
        return
    if len(feature_vector) != 32:
        log.warning("feature_vector debe tener 32 elementos, hay %s", len(feature_vector))
        return
    try:
        db = SessionLocal()
    except RuntimeError:
        return
    try:
        src = (label_source or "auto_soft").strip().lower()[:32] or "auto_soft"
        row = FeatureSampleORM(
            label=label.strip().lower()[:64],
            label_source=src,
            review_status="pending",
            feature_vector=feature_vector,
            confidence_at_collection=float(confidence),
            pose_ok=bool(pose_ok),
            session_id=session_id,
            source_file=None,
            split="unset",
            notes=None,
        )
        db.add(row)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("No se pudo guardar feature_sample")
    finally:
        db.close()


def build_optional_feature_collector(
    *,
    session_id: uuid.UUID | None = None,
) -> FeatureCollector | None:
    """Hook para ``RealtimeEngineSession`` cuando ``AUTO_COLLECT_ENABLED`` y DB estan configurados."""
    if not settings.auto_collect_enabled:
        return None
    if not engine_configured():
        return None

    gate = bool(settings.exercise_validator_enabled and settings.exercise_validator_gate_collect)
    return FeatureCollector(
        unknown_label=settings.classifier_unknown_label,
        min_confidence=float(settings.auto_collect_min_confidence),
        on_save=save_auto_collected_sample,
        session_id=session_id,
        require_validation_confirm=gate,
    )
