"""Cálculos biomecánicos a partir de landmarks MediaPipe Pose (índices estándar)."""

from __future__ import annotations

import math
from typing import Any, TypedDict

import numpy as np

# Índices MediaPipe Pose (33 puntos) — https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
LEFT_HIP = 23
LEFT_KNEE = 25
LEFT_ANKLE = 27
RIGHT_HIP = 24
RIGHT_KNEE = 26
RIGHT_ANKLE = 28
LEFT_SHOULDER = 11
LEFT_ELBOW = 13
LEFT_WRIST = 15
RIGHT_SHOULDER = 12
RIGHT_ELBOW = 14
RIGHT_WRIST = 16


class KneeAnglesPayload(TypedDict, total=False):
    """Ángulos de rodilla en grados, convención verbal en docstring de función pública."""

    left_knee_flexion_angle_deg: float
    right_knee_flexion_angle_deg: float
    left_knee_internal_angle_deg: float
    right_knee_internal_angle_deg: float


def _lm_xyz(landmarks: list[dict[str, Any]], index: int) -> np.ndarray | None:
    if index < 0 or index >= len(landmarks):
        return None
    p = landmarks[index]
    return np.array([float(p["x"]), float(p["y"]), float(p["z"])], dtype=np.float64)


def _angle_between_vectors_deg(u: np.ndarray, v: np.ndarray) -> float:
    """Ángulo entre dos vectores en grados, rango [0, 180]."""
    nu = np.linalg.norm(u)
    nv = np.linalg.norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return float("nan")
    c = float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))
    return float(math.degrees(math.acos(c)))


def knee_angles_from_landmarks(landmarks: list[dict[str, Any]]) -> KneeAnglesPayload | None:
    """
    Calcula ángulos de rodilla usando tres puntos por lado: cadera–rodilla–tobillo.

    - ``*_knee_internal_angle_deg``: ángulo en la rodilla entre los vectores
      (rodilla→cadera) y (rodilla→tobillo). En extensión aproximada del miembro suele
      acercarse a 180° en vista lateral ideal; al flexionar, el valor disminuye.

    - ``*_knee_flexion_angle_deg``: complemento respecto a 180° (0° ≈ extensión,
      valores mayores ≈ más flexión), acotado a [0, 180].
      Convención coherente con literatura CV en rehabilitación (p. ej. Wan Izzul &
      Kumaresan 2026, JIWE): sentadilla «buena» con ángulo interno 80–100° equivale
      aquí a flexión 80–100°.

    Landmarks esperados: lista indexada como salida estándar de MediaPipe (33 puntos).
    """
    lk = _lm_xyz(landmarks, LEFT_KNEE)
    lh = _lm_xyz(landmarks, LEFT_HIP)
    la = _lm_xyz(landmarks, LEFT_ANKLE)
    rk = _lm_xyz(landmarks, RIGHT_KNEE)
    rh = _lm_xyz(landmarks, RIGHT_HIP)
    ra = _lm_xyz(landmarks, RIGHT_ANKLE)

    if lk is None or lh is None or la is None or rk is None or rh is None or ra is None:
        return None

    # Vectores con origen en la rodilla
    u_left = lh - lk
    v_left = la - lk
    u_right = rh - rk
    v_right = ra - rk

    int_l = _angle_between_vectors_deg(u_left, v_left)
    int_r = _angle_between_vectors_deg(u_right, v_right)

    def flex(interior: float) -> float:
        if math.isnan(interior):
            return float("nan")
        return float(max(0.0, min(180.0, 180.0 - interior)))

    return {
        "left_knee_internal_angle_deg": int_l,
        "right_knee_internal_angle_deg": int_r,
        "left_knee_flexion_angle_deg": flex(int_l),
        "right_knee_flexion_angle_deg": flex(int_r),
    }


def _elbow_flex_for_side(
    landmarks: list[dict[str, Any]],
    shoulder_i: int,
    elbow_i: int,
    wrist_i: int,
) -> float:
    """Flexión de codo como 180° − ángulo interno hombro–codo–muñeca (0≈extensión)."""
    se = _lm_xyz(landmarks, shoulder_i)
    el = _lm_xyz(landmarks, elbow_i)
    wr = _lm_xyz(landmarks, wrist_i)
    if se is None or el is None or wr is None:
        return float("nan")
    u = se - el
    v = wr - el
    interior = _angle_between_vectors_deg(u, v)
    if math.isnan(interior):
        return float("nan")
    return float(max(0.0, min(180.0, 180.0 - interior)))


def elbow_flex_angles_from_landmarks(landmarks: list[dict[str, Any]]) -> dict[str, float]:
    """Flexión de codo izq./der. en grados (convención similar a rodilla)."""
    return {
        "left_elbow_flexion_angle_deg": _elbow_flex_for_side(landmarks, LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST),
        "right_elbow_flexion_angle_deg": _elbow_flex_for_side(landmarks, RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST),
    }


def shoulder_width_proxy(landmarks: list[dict[str, Any]]) -> float | None:
    """Distancia euclidiana 2D (x,y) hombros normalizada ~ ancho torso."""
    a = _lm_xyz(landmarks, LEFT_SHOULDER)
    b = _lm_xyz(landmarks, RIGHT_SHOULDER)
    if a is None or b is None:
        return None
    d = float(np.linalg.norm(a[:2] - b[:2]))
    return d if d > 1e-6 else None


def _midpoint_2d(landmarks: list[dict[str, Any]], idx_a: int, idx_b: int) -> np.ndarray | None:
    a = _lm_xyz(landmarks, idx_a)
    b = _lm_xyz(landmarks, idx_b)
    if a is None or b is None:
        return None
    return (a[:2] + b[:2]) / 2.0


def trunk_inclination_angle_deg(landmarks: list[dict[str, Any]]) -> float:
    """
    Inclinación del tronco respecto a la vertical de imagen, en grados [0, 180].

    Segmento: cadera-media (23/24) → hombro-medio (11/12), en coordenadas
    normalizadas 2D (x, y). 0° ≈ tronco erguido; valores mayores ≈ más inclinado
    (flexión de tronco anterior/lateral indistinta en 2D). ``nan`` si faltan puntos.
    """
    mid_sh = _midpoint_2d(landmarks, LEFT_SHOULDER, RIGHT_SHOULDER)
    mid_hip = _midpoint_2d(landmarks, LEFT_HIP, RIGHT_HIP)
    if mid_sh is None or mid_hip is None:
        return float("nan")
    v = mid_sh - mid_hip
    # En imagen, y crece hacia abajo: la vertical "arriba" es (0, -1).
    up = np.array([0.0, -1.0], dtype=np.float64)
    return _angle_between_vectors_deg(v, up)


def base_of_support_ratio(landmarks: list[dict[str, Any]]) -> float:
    """
    Ancho de base de apoyo: distancia 2D entre tobillos (27/28) dividida por el
    ancho de caderas (23/24). ~1–2 en bipedestación estándar; crece con stance
    ancho o zancada (lunge). ``nan`` si faltan puntos o el ancho de cadera es ~0.
    """
    la = _lm_xyz(landmarks, LEFT_ANKLE)
    ra = _lm_xyz(landmarks, RIGHT_ANKLE)
    lh = _lm_xyz(landmarks, LEFT_HIP)
    rh = _lm_xyz(landmarks, RIGHT_HIP)
    if la is None or ra is None or lh is None or rh is None:
        return float("nan")
    hip_w = float(np.linalg.norm(lh[:2] - rh[:2]))
    if hip_w < 1e-6:
        return float("nan")
    ankle_d = float(np.linalg.norm(la[:2] - ra[:2]))
    return ankle_d / hip_w


def _hip_flex_for_side(
    landmarks: list[dict[str, Any]],
    shoulder_i: int,
    hip_i: int,
    knee_i: int,
) -> float:
    """Flexión de cadera como 180° − ángulo interno hombro–cadera–rodilla (0 ≈ erguido)."""
    sh = _lm_xyz(landmarks, shoulder_i)
    hp = _lm_xyz(landmarks, hip_i)
    kn = _lm_xyz(landmarks, knee_i)
    if sh is None or hp is None or kn is None:
        return float("nan")
    interior = _angle_between_vectors_deg(sh - hp, kn - hp)
    if math.isnan(interior):
        return float("nan")
    return float(max(0.0, min(180.0, 180.0 - interior)))


def hip_flexion_angles_from_landmarks(landmarks: list[dict[str, Any]]) -> dict[str, float]:
    """Flexión de cadera izq./der. en grados (convención análoga a rodilla/codo)."""
    return {
        "left_hip_flexion_angle_deg": _hip_flex_for_side(landmarks, LEFT_SHOULDER, LEFT_HIP, LEFT_KNEE),
        "right_hip_flexion_angle_deg": _hip_flex_for_side(landmarks, RIGHT_SHOULDER, RIGHT_HIP, RIGHT_KNEE),
    }


def wrist_relative_heights(landmarks: list[dict[str, Any]]) -> dict[str, float]:
    """
    Altura de muñecas relativa al torso, adimensional por lado.

    0 ≈ muñeca a la altura de cadera-media; 1 ≈ a la altura de hombro-medio;
    >1 por encima de hombros (press/overhead); <0 por debajo de cadera (colgado,
    peso muerto). Normalizada por la longitud de torso 2D. ``nan`` si faltan puntos.
    """
    mid_sh = _midpoint_2d(landmarks, LEFT_SHOULDER, RIGHT_SHOULDER)
    mid_hip = _midpoint_2d(landmarks, LEFT_HIP, RIGHT_HIP)
    out = {
        "left_wrist_relative_height": float("nan"),
        "right_wrist_relative_height": float("nan"),
    }
    if mid_sh is None or mid_hip is None:
        return out
    torso_len = float(np.linalg.norm(mid_sh - mid_hip))
    if torso_len < 1e-6:
        return out
    for key, idx in (("left_wrist_relative_height", LEFT_WRIST), ("right_wrist_relative_height", RIGHT_WRIST)):
        wr = _lm_xyz(landmarks, idx)
        if wr is None:
            continue
        # y crece hacia abajo: (hip_y − wrist_y) positivo cuando la muñeca está por encima de la cadera.
        out[key] = float((mid_hip[1] - wr[1]) / torso_len)
    return out

