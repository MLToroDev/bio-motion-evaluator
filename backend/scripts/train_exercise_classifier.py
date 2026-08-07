#!/usr/bin/env python3
# ARCH-T11 — Placeholder: entrenar/exportar ONNX para exercise_classifier (ver docs/planificacion/bio_motion_plan_v2.md).
"""
Punto de partida para el dataset propio y el entrenamiento en Hugging Face.

Pasos sugeridos (no automatizados aquí):
1. Grabar video por ejercicio bajo ``tests/assets/videos/`` con nombre consistente.
2. Extraer secuencias de landmarks (offline) y ventanas de N frames → matriz X, etiquetas y.
3. Entrenar modelo temporal (p. ej. scikit-learn / PyTorch) y exportar a ONNX: la entrada debe ser **32** floats por ventana (`FEATURE_VECTOR_DIM` en `vision/feature_engine.py`), alineado con :meth:`vision.feature_engine.FeatureEngine.build_feature_vector`.
4. Colocar el ``.onnx`` en ``backend/models/`` y actualizar ``vision/models/manifest.json``.

Este script solo documenta el flujo hasta que exista el dataset curado de tesis.
"""
from __future__ import annotations

print(__doc__)

