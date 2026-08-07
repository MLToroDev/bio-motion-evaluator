# Filtro de landmarks para respuestas API (sin dependencias de app.config).
"""Excluye del JSON puntos con ``visibility`` por debajo de un umbral."""

from __future__ import annotations

from typing import Any


def landmarks_for_api_response(
    landmarks: list[dict[str, Any]] | None,
    world_landmarks: list[dict[str, Any]] | None,
    min_visibility: float,
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
    """
    Lista filtrada para el cliente: excluye puntos cuya ``visibility`` numérica sea
    estrictamente menor que ``min_visibility``. Si ``visibility`` es ``None``, se conserva
    el punto (compatibilidad con salidas sin el campo).

    ``world_landmarks`` se recorta a los mismos ``index`` que sobreviven en la lista
    normalizada. Con ``min_visibility <= 0`` no se filtra.
    """
    if not landmarks or min_visibility <= 0.0:
        return landmarks, world_landmarks

    kept: list[dict[str, Any]] = []
    kept_idx: set[int] = set()
    for p in landmarks:
        vis = p.get("visibility")
        if vis is not None:
            try:
                if float(vis) < float(min_visibility):
                    continue
            except (TypeError, ValueError):
                continue
        kept.append(p)
        idx = p.get("index")
        if isinstance(idx, int):
            kept_idx.add(idx)

    world_out: list[dict[str, Any]] | None = None
    if world_landmarks:
        world_out = [
            q
            for q in world_landmarks
            if isinstance(q.get("index"), int) and q["index"] in kept_idx
        ]

    return kept, world_out
