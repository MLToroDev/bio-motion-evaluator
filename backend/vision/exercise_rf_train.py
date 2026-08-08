"""
Entrenamiento RandomForest → ONNX para el clasificador de ejercicio (vector 32D).

Usado por el script CLI y por la tarea Celery de aprendizaje continuo.
Validación: ``vision.model_validation`` (GroupSplit / métricas honestas).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from vision.model_validation import compute_classification_metrics, resolve_split_indices

log = logging.getLogger(__name__)

FEATURE_DIM = 32
MANIFEST_VERSION = 2


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
    metrics: dict[str, Any] | None = None,
    training_params: dict[str, Any] | None = None,
    dataset_snapshot: dict[str, Any] | None = None,
) -> None:
    """Fusiona o crea entrada en ``manifest.json`` (manifest_version=2)."""
    manifest_path = manifest_path.expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (backend_root / manifest_path).resolve()
    data: dict[str, Any] = {}
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as f:
            data = json.load(f)
    data["manifest_version"] = MANIFEST_VERSION
    models = dict(data.get("models") or {})
    entry: dict[str, Any] = {
        "path": onnx_rel_posix,
        "classes": class_list,
        "window_size": window_size,
        "feature_vector_dim": FEATURE_DIM,
        "created_at": _dt.date.today().isoformat(),
        "note": note or "RandomForest (vision/exercise_rf_train.py)",
    }
    if metrics is not None:
        # Evitar classification_report enorme en manifest; conservar claves clave
        slim = {
            k: metrics[k]
            for k in (
                "accuracy",
                "macro_f1",
                "balanced_accuracy",
                "f1_per_class",
                "confusion_matrix",
                "oob_score",
                "oob_score_caveat",
                "roc_auc_ovr",
                "pr_auc_ovr",
                "brier_score_multiclass",
                "split_strategy",
                "leakage_risk",
                "unreliable_classes",
                "high_variance_classes",
                "n_train",
                "n_val",
                "n_groups_train",
                "n_groups_val",
                "train_macro_f1",
                "overfit_gap_macro_f1",
                "undefined_metrics",
            )
            if k in metrics
        }
        entry["metrics"] = slim
    if training_params is not None:
        entry["training_params"] = training_params
    if dataset_snapshot is not None:
        entry["dataset_snapshot"] = dataset_snapshot
    models[model_key] = entry
    data["models"] = models
    if set_active:
        data["active"] = model_key
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _dataset_snapshot(y_str: np.ndarray) -> dict[str, int]:
    counts: dict[str, int] = {}
    for lab in y_str.tolist():
        k = str(lab).strip().lower()
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items()))


def train_rf_export_onnx(
    X: np.ndarray,
    y_str: np.ndarray,
    class_list: list[str],
    out_path: Path,
    *,
    groups: np.ndarray | None = None,
    sample_splits: np.ndarray | None = None,
    test_size: float = 0.2,
    seed: int = 42,
    n_estimators: int = 200,
) -> dict[str, Any]:
    """
    Entrena con holdout (GroupSplit / frozen / row), exporta ONNX y devuelve métricas.

    Raises:
        ValueError: etiquetas fuera de ``class_list`` o pocas muestras.
    """
    from sklearn.ensemble import RandomForestClassifier

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

    X_f = X.astype(np.float32)
    split = resolve_split_indices(
        y,
        groups=groups,
        sample_splits=sample_splits,
        test_size=test_size,
        seed=seed,
        class_names=class_list,
    )
    for note in split.notes:
        log.warning("split note: %s", note)
    if split.strategy in ("row_stratified", "row_unstratified"):
        log.warning(
            "Split %s (leakage_risk=%s). Preferir groups=source_file o sample_splits congelados.",
            split.strategy,
            split.leakage_risk,
        )
    if not split.stratified:
        log.warning("Split sin estratificación (stratified=False)")

    X_train, X_val = X_f[split.train_idx], X_f[split.val_idx]
    y_train, y_val = y[split.train_idx], y[split.val_idx]

    clf: RandomForestClassifier | None = None
    n_unique_full = int(len(np.unique(y)))
    oob_score: float | None = None
    y_proba: np.ndarray | None = None

    if n_unique_full == 1:
        y_pred = np.full(y_val.shape, int(np.unique(y)[0]), dtype=np.int64)
        y_train_pred = np.full(y_train.shape, int(np.unique(y)[0]), dtype=np.int64)
    else:
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=seed,
            class_weight="balanced_subsample",
            n_jobs=-1,
            oob_score=True,
        )
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_val)
        y_train_pred = clf.predict(X_train)
        oob_score = float(getattr(clf, "oob_score_", None) or 0.0) if getattr(clf, "oob_score_", None) is not None else None
        try:
            # Alinear columnas de proba al orden de class_list
            proba_raw = clf.predict_proba(X_val)
            proba_full = np.zeros((X_val.shape[0], len(class_list)), dtype=np.float64)
            for local_i, cls_id in enumerate(clf.classes_):
                proba_full[:, int(cls_id)] = proba_raw[:, local_i]
            y_proba = proba_full
        except Exception as exc:
            log.warning("predict_proba no disponible: %s", exc)
            y_proba = None

    rf_is_monoclass = clf is not None and len(getattr(clf, "classes_", [])) == 1
    use_stub_onnx = n_unique_full == 1 or rf_is_monoclass

    metrics = compute_classification_metrics(
        y_val,
        y_pred,
        class_list,
        y_proba=y_proba,
        y_train_true=y_train,
        y_train_pred=y_train_pred,
        oob_score=oob_score,
        split_meta=split,
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

    snap = _dataset_snapshot(y_str)
    training_params = {
        "seed": int(seed),
        "n_estimators": int(n_estimators),
        "test_size": float(test_size),
        "class_weight": "balanced_subsample",
        "split_strategy": split.strategy,
    }
    metrics["export_mode"] = export_mode
    metrics["dataset_snapshot"] = snap
    metrics["training_params"] = training_params
    return metrics
