# Detector de equipamiento de gimnasio (open-vocabulary) sobre el frame BGR.
"""
Usa Ultralytics YOLO-World cuando está disponible. Si el paquete o el modelo fallan,
devuelve lista vacía (el motor de pose sigue operando).

Las cajas se normalizan a [0, 1] respecto al ancho/alto del frame para que el cliente
las dibuje alineadas con el vídeo (mismo sistema que landmarks MediaPipe).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Clases pedidas al modelo open-vocab (inglés; YOLO-World espera prompts en EN).
DEFAULT_EQUIPMENT_CLASSES: tuple[str, ...] = (
    "dumbbell",
    "barbell",
    "kettlebell",
    "weight plate",
    "weight bench",
    "cable machine",
    "smith machine",
    "treadmill",
    "exercise bike",
    "resistance band",
)

LABEL_ES: dict[str, str] = {
    "dumbbell": "Mancuerna",
    "barbell": "Barra",
    "kettlebell": "Kettlebell",
    "weight plate": "Disco",
    "weight bench": "Banco",
    "cable machine": "Máquina de cable",
    "smith machine": "Máquina Smith",
    "treadmill": "Cinta",
    "exercise bike": "Bicicleta",
    "resistance band": "Banda",
}

# Mapeo a la etiqueta corta de `equipment_label` del contrato WS.
LABEL_TO_EQUIPMENT: dict[str, str] = {
    "dumbbell": "dumbbell",
    "barbell": "barbell",
    "kettlebell": "kettlebell",
    "weight plate": "barbell",
    "weight bench": "machine",
    "cable machine": "machine",
    "smith machine": "machine",
    "treadmill": "machine",
    "exercise bike": "machine",
    "resistance band": "band",
}


def label_es(label: str) -> str:
    key = (label or "").strip().lower()
    return LABEL_ES.get(key, label.replace("_", " ").title() if label else "Objeto")


def equipment_slug(label: str) -> str | None:
    return LABEL_TO_EQUIPMENT.get((label or "").strip().lower())


class EquipmentDetector:
    """
    Detector stateful (modelo compartido). Thread-safe en ``detect`` vía lock.

    ``model_id`` tipico: ``yolov8s-world.pt`` (se descarga la 1.ª vez a la caché de Ultralytics).
    """

    def __init__(
        self,
        *,
        classes: list[str] | None = None,
        conf_threshold: float = 0.25,
        model_id: str = "yolov8s-world.pt",
        imgsz: int = 320,
    ) -> None:
        self._classes = [c.strip().lower() for c in (classes or list(DEFAULT_EQUIPMENT_CLASSES)) if c.strip()]
        self._conf = float(conf_threshold)
        self._model_id = model_id
        self._imgsz = int(imgsz)
        self._model: Any = None
        self._load_error: str | None = None
        self._lock = threading.Lock()
        self._unavailable = False

    @property
    def available(self) -> bool:
        return not self._unavailable

    def _ensure_model(self) -> bool:
        if self._unavailable:
            return False
        if self._model is not None:
            return True
        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]

            # YOLO-World (open vocabulary). Fallback: YOLO clásico no entiende prompts de gym.
            model = YOLO(self._model_id)
            if hasattr(model, "set_classes"):
                model.set_classes(self._classes)
            self._model = model
            log.info(
                "EquipmentDetector listo model=%s classes=%s conf=%.2f",
                self._model_id,
                self._classes,
                self._conf,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._unavailable = True
            self._load_error = str(exc)
            log.warning("EquipmentDetector no disponible (%s); se omite detección de objetos", exc)
            return False

    def detect(self, bgr: np.ndarray) -> list[dict[str, Any]]:
        """
        Devuelve lista de dicts:
        ``{label, label_es, confidence, bbox_norm: [x1,y1,x2,y2]}`` con coords en [0,1].
        """
        if bgr is None or not isinstance(bgr, np.ndarray) or bgr.size == 0:
            return []
        with self._lock:
            if not self._ensure_model():
                return []
            assert self._model is not None
            try:
                h, w = int(bgr.shape[0]), int(bgr.shape[1])
                if h < 8 or w < 8:
                    return []
                results = self._model.predict(
                    source=bgr,
                    conf=self._conf,
                    imgsz=self._imgsz,
                    verbose=False,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("EquipmentDetector.predict falló: %s", exc)
                return []

        out: list[dict[str, Any]] = []
        if not results:
            return out
        r0 = results[0]
        boxes = getattr(r0, "boxes", None)
        names = getattr(r0, "names", None) or {}
        if boxes is None:
            return out
        try:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)
        except Exception:  # noqa: BLE001
            return out

        for i in range(int(xyxy.shape[0])):
            conf = float(confs[i])
            if conf < self._conf:
                continue
            cls_i = int(clss[i])
            raw_name = names.get(cls_i, self._classes[cls_i] if cls_i < len(self._classes) else f"class_{cls_i}")
            label = str(raw_name).strip().lower()
            x1, y1, x2, y2 = (float(v) for v in xyxy[i].tolist())
            # Normalizar y clamp
            nx1 = max(0.0, min(1.0, x1 / w))
            ny1 = max(0.0, min(1.0, y1 / h))
            nx2 = max(0.0, min(1.0, x2 / w))
            ny2 = max(0.0, min(1.0, y2 / h))
            if nx2 <= nx1 or ny2 <= ny1:
                continue
            out.append(
                {
                    "label": label,
                    "label_es": label_es(label),
                    "confidence": round(conf, 4),
                    "bbox_norm": [round(nx1, 5), round(ny1, 5), round(nx2, 5), round(ny2, 5)],
                    "equipment_slug": equipment_slug(label),
                }
            )
        # Ordenar por confianza desc; limitar ruido en UI
        out.sort(key=lambda d: float(d["confidence"]), reverse=True)
        return out[:12]


_detector_singleton: EquipmentDetector | None = None
_singleton_lock = threading.Lock()


def get_shared_equipment_detector(
    *,
    enabled: bool,
    classes: list[str] | None = None,
    conf_threshold: float = 0.25,
    model_id: str = "yolov8s-world.pt",
    imgsz: int = 320,
) -> EquipmentDetector | None:
    """Singleton perezoso; ``None`` si ``enabled`` es False."""
    global _detector_singleton
    if not enabled:
        return None
    with _singleton_lock:
        if _detector_singleton is None:
            _detector_singleton = EquipmentDetector(
                classes=classes,
                conf_threshold=conf_threshold,
                model_id=model_id,
                imgsz=imgsz,
            )
        return _detector_singleton


def majority_equipment_slug(detections: list[dict[str, Any]]) -> str | None:
    """Slug de equipo más frecuente entre detecciones con confianza >= 0.35."""
    votes: dict[str, float] = {}
    for d in detections:
        slug = d.get("equipment_slug")
        conf = float(d.get("confidence") or 0.0)
        if not slug or conf < 0.35:
            continue
        votes[str(slug)] = votes.get(str(slug), 0.0) + conf
    if not votes:
        return None
    return max(votes.items(), key=lambda kv: kv[1])[0]
