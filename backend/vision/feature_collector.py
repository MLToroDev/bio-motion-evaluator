"""Hook opcional para persistir vectores de características durante inferencia."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

import numpy as np

log = logging.getLogger(__name__)

# vector 32D (list[float]), label, confidence, pose_ok, session_id opcional
FeatureSaveFn = Callable[[list[float], str, float, bool, uuid.UUID | None], None]


class FeatureCollector:
    """
    Tras cada frame con ventana llena, si la confianza supera el umbral y la etiqueta
    no es ``unknown``, invoca ``on_save`` (normalmente escritura DB en hilo worker).
    """

    def __init__(
        self,
        *,
        unknown_label: str = "unknown",
        min_confidence: float = 0.85,
        on_save: FeatureSaveFn,
        session_id: uuid.UUID | None = None,
    ) -> None:
        self._unknown = (unknown_label or "unknown").strip().lower()
        self._min_confidence = float(min_confidence)
        self._on_save = on_save
        self._session_id = session_id

    def maybe_collect(
        self,
        feature_vec: np.ndarray,
        *,
        window_full: bool,
        label: str,
        confidence: float,
        pose_ok: bool,
        forced_label: bool,
    ) -> None:
        if forced_label:
            return
        if not window_full:
            return
        if feature_vec.size < 32:
            return
        conf = float(confidence)
        if conf < self._min_confidence:
            return
        lab = (label or "").strip().lower()
        if not lab or lab == self._unknown:
            return
        try:
            vec_list = [float(feature_vec[i]) for i in range(32)]
        except (TypeError, ValueError, IndexError):
            return
        try:
            self._on_save(vec_list, lab, conf, bool(pose_ok), self._session_id)
        except Exception:  # noqa: BLE001
            log.exception("feature_collector: fallo al persistir muestra")
