"""
Entrenamiento RandomForest → ONNX para el clasificador de ejercicio (vector 32D).

Usado por el script CLI y por la tarea Celery de aprendizaje continuo.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

import numpy as np

FEATURE_DIM = 32


def merge_manifest(
    manifest_path: Path,
    backend_root: Path,
    model_key: str,
    onnx_rel_posix: str,
    class_list: list[str],
    window_size: int,
    *,
    set_active: bool,
    note: str | None = None,
) -> None:
    """Fusiona o crea entrada en ``manifest.json``."""
    manifest_path = manifest_path.expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (backend_root / manifest_path).resolve()
    data: dict[str, Any] = {}
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as f:
            data = json.load(f)
    models = dict(data.get("models") or {})
    entry: dict[str, Any] = {
        "path": onnx_rel_posix,
        "classes": class_list,
        "window_size": window_size,
        "feature_vector_dim": FEATURE_DIM,
        "created_at": _dt.date.today().isoformat(),
        "note": note or "RandomForest (vision/exercise_rf_train.py)",
    }
    models[model_key] = entry
    data["models"] = models
    if set_active:
        data["active"] = model_key
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def train_rf_export_onnx(
    X: np.ndarray,
    y_str: np.ndarray,
    class_list: list[str],
    out_path: Path,
    *,
    test_size: float = 0.2,
    seed: int = 42,
    n_estimators: int = 200,
) -> dict[str, Any]:
    """
    Entrena con holdout estratificado, exporta ONNX y devuelve métricas serializables.

    Raises:
        ValueError: etiquetas fuera de ``class_list`` o pocas muestras.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    if X.shape[1] != FEATURE_DIM:
        raise ValueError(f"Se esperaban {FEATURE_DIM} columnas, hay {X.shape[1]}")
    labels_set = set(y_str.tolist())
    unknown_labels = sorted(labels_set - set(class_list))
    if unknown_labels:
        raise ValueError(f"Etiquetas no listadas en class_list: {unknown_labels}")
    label_to_idx = {c: i for i, c in enumerate(class_list)}
    y = np.array([label_to_idx[str(s)] for s in y_str], dtype=np.int64)
    if X.shape[0] < 2:
        raise ValueError("Se necesitan al menos 2 muestras")

    try:
        X_train, X_val, y_train, y_val = train_test_split(
            X.astype(np.float32),
            y,
            test_size=test_size,
            random_state=seed,
            stratify=y,
        )
    except ValueError:
        X_train, X_val, y_train, y_val = train_test_split(
            X.astype(np.float32),
            y,
            test_size=test_size,
            random_state=seed,
        )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=seed,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_val)

    acc = float(accuracy_score(y_val, y_pred))
    # Per-class F1 (macro / per class)
    f1_each = f1_score(y_val, y_pred, average=None, labels=list(range(len(class_list))), zero_division=0)
    f1_per_class = {class_list[i]: float(f1_each[i]) for i in range(len(class_list))}
    cm = confusion_matrix(y_val, y_pred, labels=list(range(len(class_list))))
    cm_list = [[int(x) for x in row] for row in cm.tolist()]
    cls_rep = classification_report(
        y_val,
        y_pred,
        target_names=class_list,
        output_dict=True,
        zero_division=0,
    )

    initial_types = [("float_input", FloatTensorType([None, FEATURE_DIM]))]
    onnx_model = convert_sklearn(
        clf,
        initial_types=initial_types,
        options={id(clf): {"zipmap": False}},
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        f.write(onnx_model.SerializeToString())

    macro_f1 = float(f1_score(y_val, y_pred, average="macro", zero_division=0))

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "f1_per_class": f1_per_class,
        "confusion_matrix": cm_list,
        "classification_report": cls_rep,
        "class_names": list(class_list),
        "n_train": int(X_train.shape[0]),
        "n_val": int(X_val.shape[0]),
    }
