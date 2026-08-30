"""
Cálculos biomecánicos a partir de landmarks MediaPipe Pose (índices estándar).

.. warning::
   **Espacio de coordenadas.** Un ángulo solo es invariante en un espacio *isótropo*
   (misma unidad en los tres ejes). Los *landmarks normalizados* de MediaPipe **no lo
   son**: ``x`` se divide por el ancho de la imagen y ``y`` por el alto, de modo que en
   vídeo 16:9 el eje vertical queda estirado un factor 1,778 respecto del horizontal.
   Calcular el ángulo sobre esas coordenadas introduce un error sistemático de hasta
   ~32 grados, incluso con la cámara perfectamente alineada.

   Por eso las funciones de este módulo **asumen coordenadas isótropas**. Para obtenerlas
   usa :func:`angulos_rodilla`, que resuelve la fuente correcta, en lugar de llamar
   directamente a :func:`knee_angles_from_landmarks` con landmarks normalizados.

   Ver ``docs/spec/goniometria-espacio-de-coordenadas.md``.
"""

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


def escalar_a_isotropico(
    landmarks: list[dict[str, Any]],
    relacion_aspecto: float,
) -> list[dict[str, Any]]:
    """
    Reescala ``y`` para dejar las tres coordenadas en unidades homogéneas.

    Los landmarks normalizados de MediaPipe traen ``x`` dividido por el ancho de la imagen
    y ``y`` por el alto; ``z`` usa aproximadamente la misma escala que ``x``. Multiplicar
    ``y`` por ``alto / ancho`` deja los tres ejes en unidades de *ancho de imagen*, que es
    condición necesaria para que el ángulo calculado sea el ángulo real.

    :param relacion_aspecto: cociente ``alto / ancho`` de la imagen de origen.
    """
    if relacion_aspecto <= 0.0:
        return landmarks
    return [{**p, "y": float(p["y"]) * relacion_aspecto} for p in landmarks]


def angulos_rodilla(
    landmarks: list[dict[str, Any]] | None,
    world_landmarks: list[dict[str, Any]] | None = None,
    relacion_aspecto: float | None = None,
) -> KneeAnglesPayload | None:
    """
    Ángulos de rodilla resolviendo la fuente de coordenadas **correcta**.

    Orden de preferencia:

    1. ``world_landmarks`` — salida métrica del modelo (metros, origen en el punto medio
       de las caderas). Es isótropa por construcción y constituye la estimación 3D
       propiamente dicha, por lo que además es invariante a la oblicuidad de la cámara.
    2. ``landmarks`` **corregidos** por ``relacion_aspecto``, cuando no hay
       ``world_landmarks`` pero sí se conoce la geometría de la imagen.
    3. ``landmarks`` tal cual, **solo** como último recurso. Esta rama es geométricamente
       incorrecta y se conserva únicamente para no dejar al sistema sin medida; su sesgo
       está documentado en ``docs/spec/goniometria-espacio-de-coordenadas.md``.

    Devuelve ``None`` si no hay ninguna fuente utilizable.
    """
    if world_landmarks:
        resultado = knee_angles_from_landmarks(world_landmarks)
        if resultado is not None:
            return resultado
    if not landmarks:
        return None
    if relacion_aspecto is not None:
        return knee_angles_from_landmarks(escalar_a_isotropico(landmarks, relacion_aspecto))
    return knee_angles_from_landmarks(landmarks)


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

