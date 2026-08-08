"""Curl unilateral: señal de codo dominante (no promedio bilateral)."""

from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    bilateral_elbow_flexion,
    dominant_elbow_flexion,
)
from vision.types import FeatureFrame, PoseFrame


def _pose_unilateral_curl() -> FeatureFrame:
    lm = [{"index": i, "x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for i in range(17)]
    lm[11] = {"index": 11, "x": 0.4, "y": 0.2, "z": 0.0, "visibility": 1.0}
    lm[12] = {"index": 12, "x": 0.6, "y": 0.2, "z": 0.0, "visibility": 1.0}
    lm[13] = {"index": 13, "x": 0.35, "y": 0.45, "z": 0.0, "visibility": 1.0}
    lm[15] = {"index": 15, "x": 0.40, "y": 0.22, "z": 0.0, "visibility": 1.0}
    lm[14] = {"index": 14, "x": 0.65, "y": 0.45, "z": 0.0, "visibility": 1.0}
    lm[16] = {"index": 16, "x": 0.65, "y": 0.70, "z": 0.0, "visibility": 1.0}
    pose = PoseFrame(ok=True, landmarks=lm, note=None)
    return FeatureFrame(
        pose=pose,
        frame_index=0,
        exercise_label="curl",
        exercise_confidence=1.0,
        dt_s=0.066,
    )


def test_dominant_elbow_tracks_working_arm() -> None:
    frame = _pose_unilateral_curl()
    bilateral = bilateral_elbow_flexion(frame)
    dominant = dominant_elbow_flexion(frame)
    assert bilateral is not None and dominant is not None
    assert dominant > bilateral + 20.0
    assert dominant >= 70.0
