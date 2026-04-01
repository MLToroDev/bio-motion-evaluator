"""Descarga el bundle .task de Pose Landmarker (full por defecto; lite opcional para más FPS)."""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

MODELS = {
    "lite": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
        "float16/latest/pose_landmarker_lite.task",
        "pose_landmarker_lite.task",
    ),
    "full": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/"
        "float16/latest/pose_landmarker_full.task",
        "pose_landmarker_full.task",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga Pose Landmarker .task")
    parser.add_argument(
        "variant",
        nargs="?",
        default="full",
        choices=list(MODELS.keys()),
        help="full (más preciso, default) o lite (más rápido)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    url, filename = MODELS[args.variant]
    dest = root / "models" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        print(f"Ya existe: {dest}")
        return
    print(f"Descargando {url} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"Guardado en {dest}")


if __name__ == "__main__":
    main()
