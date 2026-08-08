"""
Validación rigurosa del clasificador RF→ONNX (split por vídeo, métricas honestas).

Núcleo reutilizable por entrenamiento Celery, teacher/validador y scripts offline.
No depende de FastAPI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any  # noqa: TC003 — usado en firmas públicas serializables

import numpy as np

log = logging.getLogger(__name__)

# Confirmado Gate F0 (2026-08-07): <3 vídeos/clase ⇒ unreliable_class.
DEFAULT_MIN_VIDEOS_PER_CLASS = 3

OOB_SCORE_CAVEAT = (
    "row-level estimate, not leakage-free for grouped/correlated data"
)

FIXED_SPLITS = frozenset({"train", "val", "test"})


def normalize_group_key(source_file: str | None) -> str | None:
    """Normaliza ``source_file`` a una clave de grupo estable, o None si ausente."""
    if source_file is None:
        return None
    key = str(source_file).strip()
    return key or None


@dataclass
class SplitResult:
    """Índices train/val y metadatos de la política de partición."""

    train_idx: np.ndarray
    val_idx: np.ndarray
    strategy: str
    leakage_risk: bool
    n_groups_train: int
    n_groups_val: int
    unreliable_classes: list[str] = field(default_factory=list)
    high_variance_classes: list[str] = field(default_factory=list)
    stratified: bool = True
    notes: list[str] = field(default_factory=list)
    effective_splits: np.ndarray | None = None  # etiquetas efectivas por fila tras herencia


def _label_to_name(label: Any, class_names: list[str] | None) -> str:
    """Mapea etiqueta int (índice) o str al nombre de clase canónico."""
    if class_names is not None and isinstance(label, (int, np.integer)):
        idx = int(label)
        if 0 <= idx < len(class_names):
            return str(class_names[idx])
    return str(label)


def _count_groups_per_class(
    y: np.ndarray,
    groups: np.ndarray,
    class_names: list[str] | None = None,
) -> dict[str, int]:
    counts: dict[str, set[str]] = {}
    for label, g in zip(y.tolist(), groups.tolist(), strict=True):
        lab = _label_to_name(label, class_names)
        gk = normalize_group_key(None if g is None else str(g))
        if gk is None:
            continue
        counts.setdefault(lab, set()).add(gk)
    out = {k: len(v) for k, v in counts.items()}
    if class_names:
        for c in class_names:
            out.setdefault(str(c), 0)
    return out


def inherit_group_splits(
    groups: np.ndarray | None,
    sample_splits: np.ndarray | None,
) -> np.ndarray | None:
    """
    Si un grupo tiene alguna fila con split fijo (train/val/test), todas las filas
    de ese grupo heredan ese split (prioridad: test > val > train si hay conflicto).
    """
    if groups is None or sample_splits is None:
        return sample_splits
    n = len(groups)
    if len(sample_splits) != n:
        raise ValueError("groups y sample_splits deben tener la misma longitud")

    priority = {"test": 3, "val": 2, "train": 1}
    group_fixed: dict[str, str] = {}
    for i in range(n):
        gk = normalize_group_key(None if groups[i] is None else str(groups[i]))
        sp = str(sample_splits[i] or "unset").strip().lower()
        if gk is None or sp not in FIXED_SPLITS:
            continue
        prev = group_fixed.get(gk)
        if prev is None or priority[sp] > priority[prev]:
            group_fixed[gk] = sp

    if not group_fixed:
        return np.asarray([str(s or "unset").strip().lower() for s in sample_splits.tolist()])

    inherited: list[str] = []
    for i in range(n):
        gk = normalize_group_key(None if groups[i] is None else str(groups[i]))
        sp = str(sample_splits[i] or "unset").strip().lower()
        if gk is not None and gk in group_fixed:
            inherited.append(group_fixed[gk])
        else:
            inherited.append(sp if sp else "unset")
    return np.asarray(inherited, dtype=object)


def resolve_split_indices(
    y: np.ndarray,
    *,
    groups: np.ndarray | None = None,
    sample_splits: np.ndarray | None = None,
    test_size: float = 0.2,
    seed: int = 42,
    min_videos_per_class: int = DEFAULT_MIN_VIDEOS_PER_CLASS,
    class_names: list[str] | None = None,
) -> SplitResult:
    """
    Resuelve índices train/val.

    Prioridad:
    1. Holdout congelado (tras herencia de split por grupo) si hay filas train y val/test.
    2. GroupShuffleSplit si hay grupos válidos suficientes.
    3. train_test_split estratificado (fallback CSV / sin source_file).
    """
    from sklearn.model_selection import GroupShuffleSplit, train_test_split

    y = np.asarray(y)
    n = int(y.shape[0])
    if n < 2:
        raise ValueError("Se necesitan al menos 2 muestras para particionar")

    notes: list[str] = []
    effective = inherit_group_splits(groups, sample_splits)

    # --- unreliable / high-variance por conteo de grupos ---
    unreliable: list[str] = []
    high_var: list[str] = []
    if groups is not None:
        g_norm = np.asarray(
            [normalize_group_key(None if g is None else str(g)) or "" for g in groups.tolist()],
            dtype=object,
        )
        per_class = _count_groups_per_class(y, g_norm, class_names=class_names)
        for lab, n_vid in sorted(per_class.items()):
            if n_vid < min_videos_per_class:
                unreliable.append(str(lab))
            elif n_vid < 5:
                high_var.append(str(lab))
    else:
        g_norm = None

    # --- 1) Frozen split ---
    if effective is not None:
        train_mask = np.array([str(s) == "train" for s in effective.tolist()])
        # val y test se usan como holdout de evaluación
        val_mask = np.array([str(s) in ("val", "test") for s in effective.tolist()])
        if int(train_mask.sum()) >= 1 and int(val_mask.sum()) >= 1:
            train_idx = np.flatnonzero(train_mask)
            val_idx = np.flatnonzero(val_mask)
            n_gt = n_gv = 0
            if g_norm is not None:
                g_train = {g for g in g_norm[train_idx].tolist() if g}
                g_val = {g for g in g_norm[val_idx].tolist() if g}
                n_gt, n_gv = len(g_train), len(g_val)
                overlap = g_train & g_val
                leakage = bool(overlap)
                if leakage:
                    notes.append(f"frozen_split leakage: groups in both sides={sorted(overlap)[:5]}")
            else:
                leakage = False
            return SplitResult(
                train_idx=train_idx,
                val_idx=val_idx,
                strategy="frozen_split",
                leakage_risk=leakage,
                n_groups_train=n_gt,
                n_groups_val=n_gv,
                unreliable_classes=unreliable,
                high_variance_classes=high_var,
                stratified=True,
                notes=notes,
                effective_splits=effective,
            )
        if int(train_mask.sum()) + int(val_mask.sum()) > 0:
            notes.append(
                "sample_splits parciales insuficientes (hace falta train y val/test); "
                "se continúa con GroupShuffle o row split",
            )

    # --- 2) GroupShuffleSplit ---
    if g_norm is not None:
        valid_group_mask = np.array([bool(g) for g in g_norm.tolist()])
        n_valid = int(valid_group_mask.sum())
        frac_missing = 1.0 - (n_valid / max(n, 1))
        unique_groups = {g for g in g_norm.tolist() if g}
        if len(unique_groups) >= 2 and n_valid >= 2:
            # Solo filas con grupo; si hay huérfanas, van a train con leakage_risk
            idx_with_g = np.flatnonzero(valid_group_mask)
            y_g = y[idx_with_g]
            groups_g = g_norm[idx_with_g]
            try:
                gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
                tr_rel, va_rel = next(gss.split(np.zeros(len(idx_with_g)), y_g, groups_g))
                train_idx = idx_with_g[tr_rel]
                val_idx = idx_with_g[va_rel]
                orphan = np.flatnonzero(~valid_group_mask)
                if orphan.size:
                    train_idx = np.concatenate([train_idx, orphan])
                    notes.append(f"{orphan.size} filas sin source_file asignadas a train")
                g_train = {g for g in g_norm[train_idx].tolist() if g}
                g_val = {g for g in g_norm[val_idx].tolist() if g}
                leakage = frac_missing > 0.30 or bool(g_train & g_val)
                if frac_missing > 0.30:
                    notes.append(f"leakage_risk: {frac_missing:.0%} muestras sin grupo")
                return SplitResult(
                    train_idx=np.sort(train_idx),
                    val_idx=np.sort(val_idx),
                    strategy="group_shuffle",
                    leakage_risk=leakage,
                    n_groups_train=len(g_train),
                    n_groups_val=len(g_val),
                    unreliable_classes=unreliable,
                    high_variance_classes=high_var,
                    stratified=True,
                    notes=notes,
                    effective_splits=effective,
                )
            except ValueError as exc:
                notes.append(f"GroupShuffleSplit falló ({exc}); fallback row split")
        else:
            notes.append("grupos insuficientes para GroupShuffleSplit; fallback row split")

    # --- 3) Row-level stratified ---
    indices = np.arange(n)
    stratified = True
    try:
        train_idx, val_idx = train_test_split(
            indices,
            test_size=test_size,
            random_state=seed,
            stratify=y,
        )
    except ValueError:
        stratified = False
        log.warning(
            "train_test_split sin estratificación (clases demasiado minoritarias o n pequeño)",
        )
        notes.append("stratify falló; split no estratificado")
        train_idx, val_idx = train_test_split(
            indices,
            test_size=test_size,
            random_state=seed,
        )
    return SplitResult(
        train_idx=np.sort(np.asarray(train_idx, dtype=int)),
        val_idx=np.sort(np.asarray(val_idx, dtype=int)),
        strategy="row_stratified" if stratified else "row_unstratified",
        leakage_risk=True,  # row-level siempre tiene riesgo de leakage con ventanas correlacionadas
        n_groups_train=0,
        n_groups_val=0,
        unreliable_classes=unreliable,
        high_variance_classes=high_var,
        stratified=stratified,
        notes=notes,
        effective_splits=effective,
    )


def _safe_roc_pr_auc(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    class_list: list[str],
) -> tuple[float | None, float | None, list[str]]:
    """ROC-AUC / PR-AUC one-vs-rest; null + undefined_metrics si no aplicable."""
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.preprocessing import label_binarize

    undefined: list[str] = []
    n_classes = len(class_list)
    if y_proba.ndim != 2 or y_proba.shape[1] != n_classes:
        undefined.append("roc_auc_ovr:proba_shape_mismatch")
        undefined.append("pr_auc_ovr:proba_shape_mismatch")
        return None, None, undefined

    present = sorted(set(int(x) for x in np.unique(y_true).tolist()))
    if len(present) < 2:
        undefined.append("roc_auc_ovr:fewer_than_2_classes_in_y_true")
        undefined.append("pr_auc_ovr:fewer_than_2_classes_in_y_true")
        return None, None, undefined

    # Clases ausentes en y_true → no se puede calcular OvR completo de forma fiable
    missing = [class_list[i] for i in range(n_classes) if i not in present]
    if missing:
        for m in missing:
            undefined.append(f"roc_auc_ovr:class_absent_in_val:{m}")
            undefined.append(f"pr_auc_ovr:class_absent_in_val:{m}")

    try:
        y_bin = label_binarize(y_true, classes=list(range(n_classes)))
        if y_bin.ndim == 1:
            y_bin = y_bin.reshape(-1, 1)
        # Solo columnas presentes
        cols = present
        roc = float(
            roc_auc_score(y_bin[:, cols], y_proba[:, cols], average="macro", multi_class="ovr"),
        )
    except ValueError as exc:
        undefined.append(f"roc_auc_ovr:error:{exc}")
        roc = None

    try:
        y_bin = label_binarize(y_true, classes=list(range(n_classes)))
        if n_classes == 2 and y_bin.ndim == 1:
            # label_binarize binary edge-case
            ap = float(average_precision_score(y_true == present[-1], y_proba[:, present[-1]]))
        else:
            aps = []
            for i in present:
                aps.append(average_precision_score((y_true == i).astype(int), y_proba[:, i]))
            ap = float(np.mean(aps)) if aps else None
    except ValueError as exc:
        undefined.append(f"pr_auc_ovr:error:{exc}")
        ap = None

    return roc, ap, undefined


def _multiclass_brier(y_true: np.ndarray, y_proba: np.ndarray, n_classes: int) -> float | None:
    try:
        from sklearn.metrics import brier_score_loss
        from sklearn.preprocessing import label_binarize

        y_bin = label_binarize(y_true, classes=list(range(n_classes)))
        if y_bin.ndim == 1:
            y_bin = np.column_stack([1 - y_bin, y_bin]) if n_classes == 2 else y_bin.reshape(-1, 1)
        if y_bin.shape[1] != y_proba.shape[1]:
            return None
        # Media de Brier one-vs-rest
        scores = []
        for i in range(n_classes):
            if y_bin[:, i].sum() == 0 and (1 - y_bin[:, i]).sum() == 0:
                continue
            scores.append(brier_score_loss(y_bin[:, i], y_proba[:, i]))
        return float(np.mean(scores)) if scores else None
    except Exception:
        return None


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_list: list[str],
    *,
    y_proba: np.ndarray | None = None,
    y_train_true: np.ndarray | None = None,
    y_train_pred: np.ndarray | None = None,
    oob_score: float | None = None,
    split_meta: SplitResult | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Bundle de métricas serializable a JSON.

    AUC/PR ausentes o no calculables → null + ``undefined_metrics`` (sin excepción).
    """
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    labels = list(range(len(class_list)))

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    f1_each = f1_score(y_true, y_pred, average=None, labels=labels, zero_division=0)
    f1_per_class = {class_list[i]: float(f1_each[i]) for i in range(len(class_list))}
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_list = [[int(x) for x in row] for row in cm.tolist()]

    eval_labels_arr = np.union1d(np.unique(y_true), np.unique(y_pred)).astype(int)
    eval_labels = [int(i) for i in sorted(eval_labels_arr.tolist()) if 0 <= int(i) < len(class_list)]
    eval_names = [class_list[i] for i in eval_labels]
    cls_rep = classification_report(
        y_true,
        y_pred,
        labels=eval_labels,
        target_names=eval_names,
        output_dict=True,
        zero_division=0,
    )

    train_acc = train_macro_f1 = overfit_gap = None
    if y_train_true is not None and y_train_pred is not None:
        train_acc = float(accuracy_score(y_train_true, y_train_pred))
        train_macro_f1 = float(f1_score(y_train_true, y_train_pred, average="macro", zero_division=0))
        overfit_gap = float(train_macro_f1 - macro_f1)

    undefined: list[str] = []
    roc_auc = pr_auc = brier = None
    if y_proba is not None:
        roc_auc, pr_auc, undef_auc = _safe_roc_pr_auc(y_true, np.asarray(y_proba), class_list)
        undefined.extend(undef_auc)
        brier = _multiclass_brier(y_true, np.asarray(y_proba), len(class_list))
        if brier is None:
            undefined.append("brier_score_multiclass:undefined")
    else:
        undefined.append("roc_auc_ovr:no_proba")
        undefined.append("pr_auc_ovr:no_proba")
        undefined.append("brier_score_multiclass:no_proba")

    metrics: dict[str, Any] = {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "balanced_accuracy": bal_acc,
        "f1_per_class": f1_per_class,
        "confusion_matrix": cm_list,
        "classification_report": cls_rep,
        "class_names": list(class_list),
        "train_accuracy": train_acc,
        "train_macro_f1": train_macro_f1,
        "overfit_gap_macro_f1": overfit_gap,
        "oob_score": float(oob_score) if oob_score is not None else None,
        "oob_score_caveat": OOB_SCORE_CAVEAT if oob_score is not None else None,
        "roc_auc_ovr": roc_auc,
        "pr_auc_ovr": pr_auc,
        "brier_score_multiclass": brier,
        "undefined_metrics": undefined,
    }

    if split_meta is not None:
        if isinstance(split_meta, SplitResult):
            metrics["split_strategy"] = split_meta.strategy
            metrics["leakage_risk"] = bool(split_meta.leakage_risk)
            metrics["n_groups_train"] = int(split_meta.n_groups_train)
            metrics["n_groups_val"] = int(split_meta.n_groups_val)
            metrics["unreliable_classes"] = list(split_meta.unreliable_classes)
            metrics["high_variance_classes"] = list(split_meta.high_variance_classes)
            metrics["stratified"] = bool(split_meta.stratified)
            metrics["split_notes"] = list(split_meta.notes)
            metrics["n_train"] = int(len(split_meta.train_idx))
            metrics["n_val"] = int(len(split_meta.val_idx))
        else:
            metrics.update({k: v for k, v in split_meta.items() if k not in metrics})

    return metrics
