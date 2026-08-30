# ARCH-2: feature_engine.py — Capa 2, ventana temporal (ver docs/planificacion/bio_motion_plan_v2.md §2.1)
"""Buffer deslizante, vector fijo 32 floats, FeatureFrame para RepTracker (plan v2)."""

from __future__ import annotations

import math
import statistics
from collections import deque

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.biomechanics import (
    elbow_flex_angles_from_landmarks,
    angulos_rodilla,
    shoulder_width_proxy,
)
from vision.types import FeatureFrame, PoseFrame

# Dimensión fija de entrada ONNX / contrato documentado; sobrante relleno con ceros.
FEATURE_VECTOR_DIM = 32

_ANGLE_KEYS_VEL = (
    ("left_knee_flexion_angle_deg", "left_knee"),
    ("right_knee_flexion_angle_deg", "right_knee"),
    ("left_elbow_flexion_angle_deg", "left_elbow"),
    ("right_elbow_flexion_angle_deg", "right_elbow"),
)


def _knee_flex_pair(pose: PoseFrame) -> tuple[float, float]:
    if not pose.knees:
        return float("nan"), float("nan")
    lf = pose.knees.get("left_knee_flexion_angle_deg")
    rf = pose.knees.get("right_knee_flexion_angle_deg")
    try:
        l = float(lf) if lf is not None else float("nan")
    except (TypeError, ValueError):
        l = float("nan")
    try:
        r = float(rf) if rf is not None else float("nan")
    except (TypeError, ValueError):
        r = float("nan")
    return l, r


def _ensure_knees_on_pose(pose: PoseFrame) -> PoseFrame:
    if pose.knees or not pose.landmarks or not pose.ok:
        return pose
    k = angulos_rodilla(pose.landmarks, pose.world_landmarks)
    if not k:
        return pose
    return PoseFrame(
        ok=pose.ok,
        landmarks=pose.landmarks,
        note=pose.note,
        knees=k,
        world_landmarks=pose.world_landmarks,
    )


def _pose_joint_angles(pose: PoseFrame) -> dict[str, float]:
    p = _ensure_knees_on_pose(pose)
    out: dict[str, float] = {}
    if p.knees:
        for key in (
            "left_knee_flexion_angle_deg",
            "right_knee_flexion_angle_deg",
        ):
            v = p.knees.get(key)
            try:
                fv = float(v) if v is not None else float("nan")
            except (TypeError, ValueError):
                fv = float("nan")
            if not math.isnan(fv):
                out[key] = fv
    if p.landmarks:
        el = elbow_flex_angles_from_landmarks(p.landmarks)
        for key, v in el.items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isnan(fv):
                out[key] = fv
    return out


def _bilateral_knee_mean_series(poses: list[PoseFrame]) -> np.ndarray:
    vals: list[float] = []
    for p in poses:
        l, r = _knee_flex_pair(_ensure_knees_on_pose(p))
        pair = [x for x in (l, r) if not math.isnan(x)]
        if pair:
            vals.append(float(sum(pair) / len(pair)))
        else:
            vals.append(float("nan"))
    return np.array(vals, dtype=np.float64)


def _periodicity_score_from_series(series: np.ndarray) -> float:
    x = series[~np.isnan(series)]
    if x.size < 4:
        return 0.0
    xc = x - float(np.mean(x))
    if float(np.std(xc)) < 1e-6:
        return 0.0
    signs = np.sign(xc)
    crossings = int(np.sum(np.abs(np.diff(signs)) > 0))
    return float(min(1.0, crossings / max(x.size - 1, 1)))


class FeatureEngine:
    """Mantiene una ventana de :class:`PoseFrame` y expone vector 32 + :class:`FeatureFrame`."""

    def __init__(self, cfg: ExerciseClassifierConfig) -> None:
        self._cfg = cfg
        self._window: deque[PoseFrame] = deque(maxlen=max(2, cfg.window_size_frames))
        self._default_dt_s = float(cfg.feature_default_dt_s)
        self._calib_min = int(cfg.feature_calibration_min_frames)
        self._shoulder_samples: list[float] = []
        self._calib_ref: float | None = None
        self._prev_angles: dict[str, float] | None = None
        self._last_angular_vel: dict[str, float] = {}

    def push(self, pose: PoseFrame, dt_s: float | None = None) -> None:
        dt = float(dt_s if dt_s is not None else self._default_dt_s)
        pose = _ensure_knees_on_pose(pose)
        self._update_calibration(pose)
        angles = _pose_joint_angles(pose)
        vels: dict[str, float] = {}
        if self._prev_angles and dt > 1e-9 and pose.ok:
            for angle_key, short in _ANGLE_KEYS_VEL:
                a0 = self._prev_angles.get(angle_key)
                a1 = angles.get(angle_key)
                if a0 is None or a1 is None:
                    continue
                if math.isnan(a0) or math.isnan(a1):
                    continue
                vels[f"{short}_deg_s"] = (a1 - a0) / dt
        self._last_angular_vel = vels
        if pose.ok and angles:
            self._prev_angles = angles
        elif not pose.ok:
            self._prev_angles = None

        self._window.append(pose)

    def reset(self) -> None:
        self._window.clear()
        self._shoulder_samples.clear()
        self._calib_ref = None
        self._prev_angles = None
        self._last_angular_vel.clear()

    def _update_calibration(self, pose: PoseFrame) -> None:
        if not pose.ok or not pose.landmarks:
            return
        w = shoulder_width_proxy(pose.landmarks)
        if w is None:
            return
        self._shoulder_samples.append(w)
        if self._calib_ref is None and len(self._shoulder_samples) >= self._calib_min:
            head = self._shoulder_samples[: self._calib_min]
            self._calib_ref = float(statistics.median(head))

    def _calibration_scale_value(self) -> float:
        if self._calib_ref is None or not self._window:
            return 1.0
        p = self._window[-1]
        if not p.ok or not p.landmarks:
            return 1.0
        w = shoulder_width_proxy(p.landmarks)
        if w is None or w < 1e-9:
            return 1.0
        s = self._calib_ref / w
        return float(max(0.5, min(2.0, s)))

    def _periodicity_score(self) -> float:
        if len(self._window) < 4:
            return 0.0
        series = _bilateral_knee_mean_series(list(self._window))
        return _periodicity_score_from_series(series)

    def build_feature_vector(self) -> np.ndarray:
        """Vector 1D float32 de longitud :data:`FEATURE_VECTOR_DIM` (relleno explícito al final)."""
        if not self._window:
            return np.zeros(FEATURE_VECTOR_DIM, dtype=np.float32)

        poses = [_ensure_knees_on_pose(p) for p in self._window]
        scale = self._calibration_scale_value()
        flex_l = np.array([_knee_flex_pair(p)[0] for p in poses], dtype=np.float64)
        flex_r = np.array([_knee_flex_pair(p)[1] for p in poses], dtype=np.float64)
        flex_l = np.nan_to_num(flex_l, nan=0.0) * scale
        flex_r = np.nan_to_num(flex_r, nan=0.0) * scale

        def _safe_stats(a: np.ndarray) -> tuple[float, float, float, float]:
            m = float(np.mean(a))
            s = float(np.std(a))
            mn = float(np.min(a))
            mx = float(np.max(a))
            return m, s, mn, mx

        ml, sl, min_l, max_l = _safe_stats(flex_l)
        mr, sr, min_r, max_r = _safe_stats(flex_r)
        pose_ok_ratio = float(sum(1 for p in poses if p.ok and p.landmarks) / len(poses))

        last_l, last_r = _knee_flex_pair(poses[-1])
        last_l = 0.0 if math.isnan(last_l) else float(last_l) * scale
        last_r = 0.0 if math.isnan(last_r) else float(last_r) * scale
        dl = 0.0 if math.isnan(ml) else float(last_l - ml)
        dr = 0.0 if math.isnan(mr) else float(last_r - mr)

        asym = 0.0
        raw_l = poses[-1].knees or {}
        try:
            l = float(raw_l.get("left_knee_flexion_angle_deg", float("nan")))
            r = float(raw_l.get("right_knee_flexion_angle_deg", float("nan")))
            if not math.isnan(l) and not math.isnan(r) and max(l, r, 1.0) > 0:
                asym = abs(l - r) / max(l, r, 1.0) * 100.0
        except (TypeError, ValueError):
            pass

        periodicity = self._periodicity_score()
        cal_scale = self._calibration_scale_value()

        ang_keys = ["left_knee_deg_s", "right_knee_deg_s", "left_elbow_deg_s", "right_elbow_deg_s"]
        ang = [float(self._last_angular_vel.get(k, 0.0)) for k in ang_keys]

        core = [
            ml,
            mr,
            sl,
            sr,
            min_l,
            max_l,
            min_r,
            max_r,
            dl,
            dr,
            float(len(poses)),
            pose_ok_ratio,
            asym,
            max_l - min_l,
            max_r - min_r,
            periodicity,
        ]
        vec = np.array(core + ang + [cal_scale], dtype=np.float32)
        if vec.size > FEATURE_VECTOR_DIM:
            vec = vec[:FEATURE_VECTOR_DIM]
        elif vec.size < FEATURE_VECTOR_DIM:
            pad = np.zeros(FEATURE_VECTOR_DIM - vec.size, dtype=np.float32)
            vec = np.concatenate([vec, pad])
        return vec

    def build_feature_frame(
        self,
        pose: PoseFrame,
        frame_index: int,
        exercise_label: str,
        exercise_confidence: float,
        dt_s: float | None = None,
    ) -> FeatureFrame:
        d = float(dt_s if dt_s is not None else self._default_dt_s)
        pose = _ensure_knees_on_pose(pose)
        return FeatureFrame(
            pose=pose,
            frame_index=frame_index,
            exercise_label=exercise_label,
            exercise_confidence=float(exercise_confidence),
            dt_s=d,
            angular_velocity_deg_s=dict(self._last_angular_vel),
            periodicity_score=float(self._periodicity_score()),
            calibration_scale=float(self._calibration_scale_value()),
        )

    def window_full(self) -> bool:
        return len(self._window) >= self._cfg.window_size_frames

