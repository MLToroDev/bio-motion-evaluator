"""Sesión stateful: extractor → features → clasificador → validador → rep tracker → payload unificado."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
from app.models.schemas import ExerciseClassifierConfig
from vision.equipment_detector import EquipmentDetector, majority_equipment_slug
from vision.exercise_classifier import build_classifier
from vision.exercise_validator import ExerciseValidator, build_exercise_validator
from vision.feature_collector import FeatureCollector
from vision.feature_engine import FeatureEngine
from vision.model_registry import ModelRegistry
from vision.pipeline_timer import StageTimer
from vision.pose_extractor import extract_pose_bgr, extract_pose_bgr_video, extract_pose_jpeg
from vision.rep_tracker import RepTrackerRouter
from vision.types import ClassificationResult, PoseFrame, RepState
from vision.unified_payload import build_frame_payload_v1


def _decode_jpeg_bgr(image_bytes: bytes) -> np.ndarray | None:
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return bgr


class RealtimeEngineSession:
    def __init__(
        self,
        backend_root: Path,
        model_path: Path,
        classifier_cfg: ExerciseClassifierConfig | None = None,
        *,
        inference_stride: int = 1,
        analysis_enabled: bool = True,
        forced_exercise_label: str | None = None,
        equipment_label: str | None = None,
        feature_collector: FeatureCollector | None = None,
        equipment_detector: EquipmentDetector | None = None,
        object_detect_stride: int = 4,
        exercise_validator: ExerciseValidator | None = None,
    ) -> None:
        self._model_path = model_path
        self._cfg = classifier_cfg or ExerciseClassifierConfig()
        self._inference_stride = max(1, int(inference_stride))
        self._analysis_enabled = bool(analysis_enabled)
        raw_forced = (forced_exercise_label or "").strip()
        self._forced_exercise_label: str | None = raw_forced.lower() if raw_forced else None
        raw_equipment = (equipment_label or "").strip()
        self._equipment_label: str | None = raw_equipment.lower() if raw_equipment else None
        self._feature_collector = feature_collector
        self._equipment_detector = equipment_detector
        self._object_detect_stride = max(1, int(object_detect_stride))
        self._last_pose: PoseFrame | None = None
        self._last_detections: list[dict[str, Any]] = []
        if self._analysis_enabled:
            self._features = FeatureEngine(self._cfg)
            self._classifier = build_classifier(self._cfg, ModelRegistry(backend_root))
            self._router = RepTrackerRouter(unknown_label=self._cfg.unknown_label)
            if exercise_validator is not None:
                self._validator = exercise_validator
            else:
                onnx_path: Path | None = None
                onnx_classes: list[str] | None = None
                raw_path = (settings.exercise_validator_onnx_path or "").strip()
                if raw_path:
                    p = Path(raw_path)
                    onnx_path = p if p.is_absolute() else (backend_root / p)
                raw_cls = (settings.exercise_validator_classes or "").strip()
                if raw_cls:
                    onnx_classes = [c.strip().lower() for c in raw_cls.split(",") if c.strip()]
                self._validator = build_exercise_validator(
                    enabled=bool(settings.exercise_validator_enabled),
                    unknown_label=self._cfg.unknown_label,
                    min_confidence=float(settings.exercise_validator_min_confidence),
                    min_margin=float(settings.exercise_validator_min_margin),
                    teacher_mode=str(settings.exercise_validator_teacher),
                    change_hold_frames=int(settings.exercise_validator_change_hold_frames),
                    classifier_cfg=self._cfg,
                    onnx_path=onnx_path,
                    onnx_classes=onnx_classes,
                )
        else:
            # Solo captura: no manifest/ONNX, ni ventana de features ni rep tracker.
            self._features = None
            self._classifier = None
            self._router = None
            self._validator = None

    def process_bgr(self, bgr: np.ndarray, frame_index: int, timestamp_ms: int | None = None) -> dict:
        st = StageTimer()
        pose = self._extract_pose(
            bgr=bgr,
            jpeg_bytes=None,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
        )
        detections = self._maybe_detect(bgr, frame_index)
        return self._after_extract(st, pose, frame_index, detections)

    def process_jpeg(self, image_bytes: bytes, frame_index: int) -> dict:
        st = StageTimer()
        bgr: np.ndarray | None = None
        if self._equipment_detector is not None:
            bgr = _decode_jpeg_bgr(image_bytes)
        if bgr is not None:
            pose = self._extract_pose(bgr=bgr, jpeg_bytes=None, frame_index=frame_index)
            detections = self._maybe_detect(bgr, frame_index)
        else:
            pose = self._extract_pose(bgr=None, jpeg_bytes=image_bytes, frame_index=frame_index)
            detections = list(self._last_detections)
        return self._after_extract(st, pose, frame_index, detections)

    def reset(self) -> None:
        self._last_pose = None
        self._last_detections = []
        if self._features is not None:
            self._features.reset()
        if self._classifier is not None:
            self._classifier.reset()
        if self._router is not None:
            self._router.reset_all()
        if self._validator is not None:
            self._validator.reset()

    def _maybe_detect(self, bgr: np.ndarray, frame_index: int) -> list[dict[str, Any]]:
        det = self._equipment_detector
        if det is None:
            return []
        if frame_index % self._object_detect_stride != 0 and self._last_detections:
            return list(self._last_detections)
        found = det.detect(bgr)
        self._last_detections = found
        return list(found)

    def _effective_equipment_label(self, detections: list[dict[str, Any]]) -> str | None:
        # Preferencia: etiqueta manual del usuario; si no, voto de detecciones.
        if self._equipment_label:
            return self._equipment_label
        return majority_equipment_slug(detections)

    def _extract_pose(
        self,
        frame_index: int,
        bgr: np.ndarray | None = None,
        jpeg_bytes: bytes | None = None,
        timestamp_ms: int | None = None,
    ) -> PoseFrame:
        s = self._inference_stride
        if s > 1 and (frame_index % s) != 0 and self._last_pose is not None:
            return self._last_pose
        if bgr is not None:
            if timestamp_ms is not None:
                pose = extract_pose_bgr_video(bgr, self._model_path, timestamp_ms)
            else:
                pose = extract_pose_bgr(bgr, self._model_path)
        else:
            assert jpeg_bytes is not None
            pose = extract_pose_jpeg(jpeg_bytes, self._model_path)
        if pose.ok and pose.landmarks:
            self._last_pose = pose
        return pose

    def _after_extract(
        self,
        st: StageTimer,
        pose: PoseFrame,
        frame_index: int,
        detections: list[dict[str, Any]],
    ) -> dict:
        st.mark_extract()
        equip = self._effective_equipment_label(detections)
        if not self._analysis_enabled:
            return build_frame_payload_v1(
                frame_index,
                pose,
                "unknown",
                0.0,
                RepState(),
                st.finish().as_dict(),
                equipment_label=equip,
                detected_objects=detections,
            )
        assert self._features is not None and self._classifier is not None and self._router is not None
        self._features.push(pose)
        vec = self._features.build_feature_vector()
        st.mark_feature()
        if self._forced_exercise_label:
            c = ClassificationResult(
                label=self._forced_exercise_label,
                confidence=1.0,
                raw_scores={"forced": 1.0},
            )
        else:
            c = self._classifier.classify(vec, self._features.window_full())
        st.mark_classify()
        validation_dict: dict[str, Any] | None = None
        validation_verdict: str | None = None
        if self._validator is not None and not self._forced_exercise_label:
            v = self._validator.validate(
                vec,
                window_full=self._features.window_full(),
                primary=c,
            )
            validation_dict = v.as_dict()
            validation_verdict = v.verdict
        ff = self._features.build_feature_frame(pose, frame_index, c.label, c.confidence)
        r = self._router.update(ff)
        st.mark_track()
        if self._feature_collector is not None:
            self._feature_collector.maybe_collect(
                vec,
                window_full=self._features.window_full(),
                label=c.label,
                confidence=float(c.confidence),
                pose_ok=bool(pose.ok),
                forced_label=bool(self._forced_exercise_label),
                validation_verdict=validation_verdict,
            )
        return build_frame_payload_v1(
            frame_index,
            pose,
            c.label,
            float(c.confidence),
            r,
            st.finish().as_dict(),
            equipment_label=equip,
            detected_objects=detections,
            exercise_validation=validation_dict,
        )
