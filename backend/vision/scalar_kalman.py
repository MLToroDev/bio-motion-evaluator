"""Filtro de Kalman escalar 1D para suavizar confianza (o cualquier escalar en [0,1])."""

from __future__ import annotations


class ScalarKalman1D:
    """
    Modelo: x_k = x_{k-1} + w, z_k = x_k + v (estado = valor suavizado).
    """

    def __init__(self, process_noise: float, measurement_noise: float) -> None:
        self._q = float(process_noise)
        self._r = float(measurement_noise)
        self._x: float | None = None
        self._p: float | None = None

    def reset(self) -> None:
        self._x = None
        self._p = None

    def update(self, measurement: float) -> float:
        z = float(measurement)
        if self._x is None:
            self._x = z
            self._p = 1.0
            return self._x
        assert self._p is not None
        p_pred = self._p + self._q
        k = p_pred / (p_pred + self._r)
        self._x = self._x + k * (z - self._x)
        self._p = (1.0 - k) * p_pred
        return float(self._x)

