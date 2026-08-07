"""Pruebas del módulo de ángulos articulares (regresión numérica)."""

from __future__ import annotations

import math

from vision.biomechanics import knee_angles_from_landmarks


def _fake_landmarks() -> list[dict]:
    """33 landmarks mínimos: solo índices usados por rodillas."""
    lm: list[dict] = [{"index": i, "x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for i in range(33)]
    # Vista simplificada: cadera arriba, rodilla origen, tobillo abajo — extensión ~180° entre vectores.
    # Rodilla izq en (0.5,0.5); cadera (0.5,0.3); tobillo (0.5,0.7) → vectores opuestos en Y.
    lh, lk, la = 23, 25, 27
    lm[lh] = {"index": lh, "x": 0.5, "y": 0.3, "z": 0.0, "visibility": 1.0}
    lm[lk] = {"index": lk, "x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}
    lm[la] = {"index": la, "x": 0.5, "y": 0.7, "z": 0.0, "visibility": 1.0}
    rh, rk, ra = 24, 26, 28
    lm[rh] = {"index": rh, "x": 0.5, "y": 0.3, "z": 0.0, "visibility": 1.0}
    lm[rk] = {"index": rk, "x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}
    lm[ra] = {"index": ra, "x": 0.5, "y": 0.7, "z": 0.0, "visibility": 1.0}
    return lm


def test_knee_straight_line_flexion_near_zero() -> None:
    out = knee_angles_from_landmarks(_fake_landmarks())
    assert out is not None
    assert not math.isnan(out["left_knee_flexion_angle_deg"])
    assert out["left_knee_flexion_angle_deg"] < 5.0
    assert out["right_knee_flexion_angle_deg"] < 5.0


def test_knee_flexed_has_higher_flexion() -> None:
    lm = _fake_landmarks()
    # Acercar tobillo hacia la cadera en X (flexión artificial en 3D/2D)
    lm[27] = {**lm[27], "x": 0.45, "y": 0.52}
    lm[28] = {**lm[28], "x": 0.55, "y": 0.52}
    straight = knee_angles_from_landmarks(_fake_landmarks())
    flexed = knee_angles_from_landmarks(lm)
    assert straight and flexed
    assert flexed["left_knee_flexion_angle_deg"] > straight["left_knee_flexion_angle_deg"]


def test_resolve_path_rejects_traversal() -> None:
    from pathlib import Path

    from vision.paths import resolve_gold_standard_video

    base = Path(__file__).resolve().parent / "assets" / "videos"
    try:
        resolve_gold_standard_video("../evil.mp4", base)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

