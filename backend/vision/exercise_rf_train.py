"""
Entrenamiento RandomForest → ONNX para el clasificador de ejercicio (vector 32D).

Usado por el script CLI y por la tarea Celery de aprendizaje continuo.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

FEATURE_DIM = 32


def _export_constant_logit_gemm_onnx(
    out_path: Path,
    n_features: int,
    n_classes: int,
    positive_class_index: int,
) -> None:
    """
    Exporta un modelo ONNX trivial Y = X @ 0 + b (logits fijos por fila).
    Evita ``skl2onnx`` con RandomForest de una sola clase (TensorForest inválido).
    """
    import onnx
    from onnx import TensorProto, checker, helper, numpy_helper

    if not (0 <= positive_class_index < n_classes):
        raise ValueError(f"positive_class_index={positive_class_index} no válido para {n_classes} clases")
    bias = np.full((n_classes,), -25.0, dtype=np.float32)
    bias[positive_class_index] = 0.0
    w = np.zeros((n_features, n_classes), dtype=np.float32)

    input_info = helper.make_tensor_value_info("float_input", TensorProto.FLOAT, [None, n_features])
    output_info = helper.make_tensor_value_info("variable", TensorProto.FLOAT, [None, n_classes])

    graph = helper.make_graph(
        [
            helper.make_node("MatMul", ["float_input", "W"], ["Xm"]),
            helper.make_node("Add", ["Xm", "B"], ["variable"]),
        ],
        "single_class_logit_stub",
        [input_info],
        [output_info],
        initializer=[
            numpy_helper.from_array(w, name="W"),
            numpy_helper.from_array(bias, name="B"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    checker.check_model(model)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(out_path))


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

    classes_present_in_data = sorted({str(s) for s in y_str.tolist()})
    if len(class_list) > 1 and len(classes_present_in_data) < 2:
        raise ValueError(
            "Las muestras aprobadas solo cubren una clase "
            f"({classes_present_in_data[0]}). El job de entrenamiento pide "
            f"{len(class_list)} clases ({', '.join(class_list)}): hace falta al menos "
            "una muestra aprobada por cada etiqueta que quieras distinguir, y en la práctica "
            "al menos 2 clases distintas con datos. O bien reduce la lista de clases del entrenamiento "
            "a una sola etiqueta si solo tienes ejemplos de ese ejercicio."
        )

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

    clf: RandomForestClassifier | None = None
    n_unique_full = int(len(np.unique(y)))

    if n_unique_full == 1:
        # Todo el dataset es una clase: sin RandomForest.
        y_pred = np.full(y_val.shape, int(np.unique(y)[0]), dtype=np.int64)
    else:
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=seed,
            class_weight="balanced_subsample",
            n_jobs=-1,
        )
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_val)

    # Aunque ``y`` tenga varias clases, el split puede dejar ``y_train`` monoclas → bosque degenerado;
    # ``skl2onnx`` entonces genera TreeEnsembleClassifier inválido.
    rf_is_monoclass = clf is not None and len(getattr(clf, "classes_", [])) == 1
    use_stub_onnx = n_unique_full == 1 or rf_is_monoclass

    acc = float(accuracy_score(y_val, y_pred))
    # Per-class F1 (macro / per class)
    f1_each = f1_score(y_val, y_pred, average=None, labels=list(range(len(class_list))), zero_division=0)
    f1_per_class = {class_list[i]: float(f1_each[i]) for i in range(len(class_list))}
    cm = confusion_matrix(y_val, y_pred, labels=list(range(len(class_list))))
    cm_list = [[int(x) for x in row] for row in cm.tolist()]
    # Solo etiquetas que figuran en validación / predicción.
    eval_labels_arr = np.union1d(np.unique(y_val), np.unique(y_pred)).astype(int)
    eval_labels = [int(i) for i in sorted(eval_labels_arr.tolist())]
    eval_names = [class_list[i] for i in eval_labels]
    cls_rep = classification_report(
        y_val,
        y_pred,
        labels=eval_labels,
        target_names=eval_names,
        output_dict=True,
        zero_division=0,
    )

    if n_unique_full == 1:
        stub_class_idx = int(np.unique(y)[0])
    elif rf_is_monoclass and clf is not None:
        stub_class_idx = int(clf.classes_[0])
    else:
        stub_class_idx = int(np.argmax(np.bincount(y_train.astype(int))))

    out_path = Path(out_path)
    export_mode = "random_forest"
    if use_stub_onnx:
        _export_constant_logit_gemm_onnx(
            out_path,
            FEATURE_DIM,
            len(class_list),
            stub_class_idx,
        )
        if n_unique_full == 1:
            export_mode = "single_class_logit_stub"
        else:
            export_mode = "single_class_logit_stub_train_split_monoclass"
    else:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType

        assert clf is not None
        initial_types = [("float_input", FloatTensorType([None, FEATURE_DIM]))]
        try:
            onnx_model = convert_sklearn(
                clf,
                initial_types=initial_types,
                options={id(clf): {"zipmap": False}},
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("wb") as f:
                f.write(onnx_model.SerializeToString())
        except Exception as exc:
            log.warning(
                "skl2onnx falló (%s); se usa stub de logits. Considera más muestras o mejor reparto train/val.",
                exc,
            )
            _export_constant_logit_gemm_onnx(
                out_path,
                FEATURE_DIM,
                len(class_list),
                stub_class_idx,
            )
            export_mode = "single_class_logit_stub_onnx_convert_failed"

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
        "export_mode": export_mode,
    }
