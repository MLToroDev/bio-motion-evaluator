# ARCH-5: realtime_engine.py — Orquestador < 80 líneas (ver docs/bio_motion_plan_v2.md §2.2)
"""Sesión stateful: extractor → features → clasificador → rep tracker → payload unificado."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.exercise_classifier import build_classifier
from vision.feature_engine import FeatureEngine
from vision.model_registry import ModelRegistry
from vision.pipeline_timer import StageTimer
from vision.pose_extractor import extract_pose_bgr, extract_pose_jpeg
from vision.rep_tracker import RepTrackerRouter
from vision.types import PoseFrame
from vision.unified_payload import build_frame_payload_v1


class RealtimeEngineSession:
    def __init__(
        self,
        backend_root: Path,
        model_path: Path,
        classifier_cfg: ExerciseClassifierConfig | None = None,
        *,
        inference_stride: int = 1,
    ) -> None:
        self._model_path = model_path
        self._cfg = classifier_cfg or ExerciseClassifierConfig()
        self._inference_stride = max(1, int(inference_stride))
        self._last_pose: PoseFrame | None = None
        self._features = FeatureEngine(self._cfg)
        self._classifier = build_classifier(self._cfg, ModelRegistry(backend_root))
        self._router = RepTrackerRouter(unknown_label=self._cfg.unknown_label)

    def process_bgr(self, bgr: np.ndarray, frame_index: int) -> dict:
        st = StageTimer()
        pose = self._extract_pose(bgr=bgr, jpeg_bytes=None, frame_index=frame_index)
        return self._after_extract(st, pose, frame_index)

    def process_jpeg(self, image_bytes: bytes, frame_index: int) -> dict:
        st = StageTimer()
        pose = self._extract_pose(bgr=None, jpeg_bytes=image_bytes, frame_index=frame_index)
        return self._after_extract(st, pose, frame_index)

    def reset(self) -> None:
        self._last_pose = None
        self._features.reset()
        self._classifier.reset()
        self._router.reset_all()

    def _extract_pose(
        self,
        frame_index: int,
        bgr: np.ndarray | None = None,
        jpeg_bytes: bytes | None = None,
    ) -> PoseFrame:
        s = self._inference_stride
        if s > 1 and (frame_index % s) != 0 and self._last_pose is not None:
            return self._last_pose
        if bgr is not None:
            pose = extract_pose_bgr(bgr, self._model_path)
        else:
            assert jpeg_bytes is not None
            pose = extract_pose_jpeg(jpeg_bytes, self._model_path)
        if pose.ok and pose.landmarks:
            self._last_pose = pose
        return pose

    def _after_extract(self, st: StageTimer, pose: PoseFrame, frame_index: int) -> dict:
        st.mark_extract()
        self._features.push(pose)
        vec = self._features.build_feature_vector()
        st.mark_feature()
        c = self._classifier.classify(vec, self._features.window_full())
        st.mark_classify()
        ff = self._features.build_feature_frame(pose, frame_index, c.label, c.confidence)
        r = self._router.update(ff)
        st.mark_track()
        return build_frame_payload_v1(
            frame_index, pose, c.label, float(c.confidence), r, st.finish().as_dict()
        )

