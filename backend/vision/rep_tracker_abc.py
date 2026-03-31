"""Contrato ABC de seguimiento de repeticiones (sin dependencias a implementaciones)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vision.types import RepState, TrackingFrame


class RepTracker(ABC):
    """Contrato por ejercicio: ``update`` muta estado interno; ``reset`` limpia sesión."""

    @abstractmethod
    def update(self, frame: TrackingFrame) -> RepState:
        """Actualiza con un fotograma alineado al clasificador actual."""

    @abstractmethod
    def reset(self) -> None:
        """Reinicia repeticiones y fase (nueva sesión o cambio de ejercicio)."""
