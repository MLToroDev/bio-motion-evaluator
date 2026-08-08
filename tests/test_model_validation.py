"""Tests obligatorios del núcleo de validación (GroupSplit, frozen, herencia)."""

from __future__ import annotations

import numpy as np

from vision.model_validation import (
    compute_classification_metrics,
    inherit_group_splits,
    normalize_group_key,
    resolve_split_indices,
)


def test_normalize_group_key() -> None:
    assert normalize_group_key("  Video A  ") == "Video A"
    assert normalize_group_key("") is None
    assert normalize_group_key(None) is None
    assert normalize_group_key("   ") is None


def test_no_group_in_train_and_val_simultaneously() -> None:
    """1) Ningún grupo aparece simultáneamente en train y en val."""
    # 4 vídeos × 5 ventanas, 2 clases
    groups = np.array(
        ["v1"] * 5 + ["v2"] * 5 + ["v3"] * 5 + ["v4"] * 5,
        dtype=object,
    )
    y = np.array([0] * 10 + [1] * 10)
    split = resolve_split_indices(y, groups=groups, test_size=0.25, seed=42)
    assert split.strategy == "group_shuffle"
    g_train = {groups[i] for i in split.train_idx}
    g_val = {groups[i] for i in split.val_idx}
    assert g_train.isdisjoint(g_val), (g_train, g_val)
    assert len(g_val) >= 1 and len(g_train) >= 1


def test_frozen_split_respected() -> None:
    """2) frozen_split se respeta cuando hay sample_splits fijos."""
    groups = np.array(["va", "va", "vb", "vb", "vc", "vc"], dtype=object)
    y = np.array([0, 0, 1, 1, 0, 1])
    sample_splits = np.array(["train", "train", "train", "train", "val", "val"], dtype=object)
    split = resolve_split_indices(y, groups=groups, sample_splits=sample_splits, seed=0)
    assert split.strategy == "frozen_split"
    assert set(split.train_idx.tolist()) == {0, 1, 2, 3}
    assert set(split.val_idx.tolist()) == {4, 5}


def test_fallback_row_stratified_without_groups() -> None:
    """3) Fallback a train_test_split estratificado cuando no hay groups."""
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    split = resolve_split_indices(y, groups=None, test_size=0.25, seed=7)
    assert split.strategy in ("row_stratified", "row_unstratified")
    assert split.leakage_risk is True
    assert len(split.train_idx) + len(split.val_idx) == len(y)
    assert set(split.train_idx.tolist()).isdisjoint(set(split.val_idx.tolist()))


def test_new_row_inherits_group_split() -> None:
    """4) Una fila nueva de un grupo ya spliteado hereda el split correcto."""
    groups = np.array(["g1", "g1", "g2", "g2"], dtype=object)
    # g1 ya marcado train; nueva fila de g1 llega como unset
    sample_splits = np.array(["train", "unset", "val", "val"], dtype=object)
    inherited = inherit_group_splits(groups, sample_splits)
    assert inherited is not None
    assert inherited.tolist() == ["train", "train", "val", "val"]

    y = np.array([0, 0, 1, 1])
    split = resolve_split_indices(y, groups=groups, sample_splits=sample_splits, seed=1)
    assert split.strategy == "frozen_split"
    assert set(split.train_idx.tolist()) == {0, 1}
    assert set(split.val_idx.tolist()) == {2, 3}


def test_unreliable_classes_below_threshold() -> None:
    """Clases con <3 vídeos se marcan unreliable (y como índices + class_names)."""
    # clase idle: 2 vídeos; clase squat: 3 vídeos
    groups = np.array(
        ["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3 + ["e"] * 3,
        dtype=object,
    )
    y = np.array([0] * 6 + [1] * 9)  # 0→a,b ; 1→c,d,e
    split = resolve_split_indices(
        y,
        groups=groups,
        test_size=0.34,
        seed=3,
        min_videos_per_class=3,
        class_names=["idle", "squat"],
    )
    assert "idle" in split.unreliable_classes
    assert "squat" not in split.unreliable_classes
    # No marcar todas las clases por error de mapeo índice→nombre
    assert split.unreliable_classes == ["idle"]


def test_metrics_missing_class_no_crash() -> None:
    """AUC ausente en fold → null + undefined_metrics, sin excepción."""
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_pred = np.array([0, 0, 1, 1, 1, 0])
    # proba 3 clases pero y_true solo tiene 0 y 1
    y_proba = np.array(
        [
            [0.8, 0.1, 0.1],
            [0.7, 0.2, 0.1],
            [0.4, 0.5, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.8, 0.1],
            [0.3, 0.6, 0.1],
        ],
        dtype=np.float64,
    )
    m = compute_classification_metrics(
        y_true,
        y_pred,
        ["a", "b", "c"],
        y_proba=y_proba,
        oob_score=0.5,
    )
    assert m["oob_score"] == 0.5
    assert "leakage-free" in (m["oob_score_caveat"] or "")
    assert isinstance(m["undefined_metrics"], list)
    assert any("class_absent_in_val:c" in x for x in m["undefined_metrics"])
    assert m["macro_f1"] is not None
