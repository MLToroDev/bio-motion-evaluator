"""Descarga pose_landmarker_full.task para MediaPipe Tasks."""

from __future__ import annotations

import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/"
    "pose_landmarker_full.task"
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    dest = root / "models" / "pose_landmarker_full.task"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        print(f"Ya existe: {dest}")
        return
    print(f"Descargando {MODEL_URL} ...")
    urllib.request.urlretrieve(MODEL_URL, dest)
    print(f"Guardado en {dest}")


if __name__ == "__main__":
    main()
