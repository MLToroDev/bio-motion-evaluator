"""Factory del detector de equipamiento según Settings."""

from __future__ import annotations

from vision.equipment_detector import EquipmentDetector, get_shared_equipment_detector


def build_optional_equipment_detector() -> EquipmentDetector | None:
    from app.config import settings

    return get_shared_equipment_detector(
        enabled=bool(settings.object_detect_enabled),
        classes=settings.object_detect_class_list(),
        conf_threshold=float(settings.object_detect_conf),
        model_id=str(settings.object_detect_model),
        imgsz=int(settings.object_detect_imgsz),
    )
