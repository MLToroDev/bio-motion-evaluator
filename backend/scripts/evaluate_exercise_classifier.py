#!/usr/bin/env python3
"""
Evaluación offline del clasificador (ventana + vídeo + GroupKFold).

Por defecto usa GroupKFold y reporta media ± desviación estándar entre folds
(número recomendado para citar en Cap. 6). Justificación: con pocos vídeos por
clase la varianza entre particiones es alta; un único holdout puede sesgar.

Uso::

    python scripts/evaluate_exercise_classifier.py --from-db \\
      --classes idle,squat,lunge,curl,running,pushup,plank,jumping_jack,overhead_press,deadlift,mountain_climber

    # Holdout único (secundario)
    python scripts/evaluate_exercise_classifier.py --from-db --classes squat,running --mode holdout
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from vision.exercise_rf_train import FEATURE_DIM  # noqa: E402
from vision.model_validation import (  # noqa: E402
    compute_classification_metrics,
    normalize_group_key,
    resolve_split_indices,
)


def _load_db(class_list: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from app.db.models import FeatureSampleORM
    from app.db.session import SessionLocal, engine_configured

    if not engine_configured():
        raise SystemExit("DATABASE_URL no configurada")
    xs: list[list[float]] = []
    ys: list[str] = []
    gs: list[str] = []
    with SessionLocal() as db:
        rows = (
            db.query(FeatureSampleORM)
            .filter(
                FeatureSampleORM.review_status == "approved",
                FeatureSampleORM.label.in_(class_list),
            )
            .all()
        )
        for row in rows:
            vec = row.feature_vector
            if not isinstance(vec, list) or len(vec) != FEATURE_DIM:
                continue
            lab = (row.label or "").strip().lower()
            if lab not in class_list:
                continue
            gk = normalize_group_key(row.source_file)
            if gk is None:
                continue
            xs.append([float(x) for x in vec])
            ys.append(lab)
            gs.append(gk)
    if len(xs) < 2:
        raise SystemExit("Insuficientes muestras con source_file")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys), np.asarray(gs, dtype=object)


def _fit_predict_rf(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    n_estimators: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray | None, float | None]:
    from sklearn.ensemble import RandomForestClassifier

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=seed,
        class_weight="balanced_subsample",
        n_jobs=-1,
        oob_score=True,
    )
    clf.fit(X_train, y_train)
    pred = clf.predict(X_val)
    proba = clf.predict_proba(X_val)
    oob = float(clf.oob_score_) if getattr(clf, "oob_score_", None) is not None else None
    return pred, proba, oob


def _align_proba(proba: np.ndarray, classes_present: np.ndarray, n_classes: int) -> np.ndarray:
    out = np.zeros((proba.shape[0], n_classes), dtype=np.float64)
    for local_i, cls_id in enumerate(classes_present.tolist()):
        out[:, int(cls_id)] = proba[:, local_i]
    return out


def _video_level_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
    class_list: list[str],
) -> dict[str, Any]:
    """Agrega por vídeo (voto mayoritario) y compara con etiqueta mayoritaria del vídeo."""
    by_g: dict[str, list[int]] = defaultdict(list)
    for i, g in enumerate(groups.tolist()):
        by_g[str(g)].append(i)
    yt: list[int] = []
    yp: list[int] = []
    for _g, idxs in by_g.items():
        true_lab = Counter(int(y_true[i]) for i in idxs).most_common(1)[0][0]
        pred_lab = Counter(int(y_pred[i]) for i in idxs).most_common(1)[0][0]
        yt.append(true_lab)
        yp.append(pred_lab)
    m = compute_classification_metrics(np.asarray(yt), np.asarray(yp), class_list)
    m["n_videos"] = len(by_g)
    return {
        "accuracy": m["accuracy"],
        "macro_f1": m["macro_f1"],
        "balanced_accuracy": m["balanced_accuracy"],
        "f1_per_class": m["f1_per_class"],
        "n_videos": m["n_videos"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluación group-aware del clasificador")
    p.add_argument("--from-db", action="store_true", required=True)
    p.add_argument("--classes", required=True, help="Clases separadas por coma")
    p.add_argument(
        "--mode",
        choices=("kfold", "holdout"),
        default="kfold",
        help="Default: kfold (recomendado Cap. 6). holdout = una sola partición.",
    )
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-estimators", type=int, default=50)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON de salida (default: vision/models/reports/eval_*.json)",
    )
    args = p.parse_args()

    class_list = [c.strip().lower() for c in args.classes.split(",") if c.strip()]
    if len(class_list) < 2:
        raise SystemExit("Se necesitan >=2 clases")

    X, y_str, groups = _load_db(class_list)
    label_to_idx = {c: i for i, c in enumerate(class_list)}
    y = np.asarray([label_to_idx[str(s)] for s in y_str.tolist()], dtype=np.int64)

    # Conteos de vídeos / clase
    from collections import defaultdict as dd

    vids: dict[str, set[str]] = dd(set)
    for lab, g in zip(y_str.tolist(), groups.tolist(), strict=True):
        vids[str(lab)].add(str(g))
    n_videos_per_class = {k: len(v) for k, v in sorted(vids.items())}
    min_vids = min(n_videos_per_class.values()) if n_videos_per_class else 0

    print("=== evaluate_exercise_classifier ===")
    print(f"mode={args.mode} n_samples={len(y)} n_videos={len(set(groups.tolist()))}")
    print("n_videos_per_class:", n_videos_per_class)
    print(
        "NOTA Cap. 6: GroupKFold reporta media±std porque con pocos grupos/clase "
        f"(mín={min_vids}) un único holdout tiene alta varianza.",
    )

    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "n_samples": int(len(y)),
        "n_videos": int(len(set(groups.tolist()))),
        "n_videos_per_class": n_videos_per_class,
        "classes": class_list,
        "justification": (
            "GroupKFold media±std es el número a citar en Cap. 6: con pocos "
            "vídeos por clase la varianza entre particiones es alta."
        ),
    }

    if args.mode == "holdout":
        split = resolve_split_indices(y, groups=groups, test_size=args.test_size, seed=args.seed, class_names=class_list)
        from sklearn.ensemble import RandomForestClassifier

        clf = RandomForestClassifier(
            n_estimators=args.n_estimators,
            random_state=args.seed,
            class_weight="balanced_subsample",
            n_jobs=-1,
            oob_score=True,
        )
        clf.fit(X[split.train_idx], y[split.train_idx])
        y_pred = clf.predict(X[split.val_idx])
        proba = _align_proba(clf.predict_proba(X[split.val_idx]), clf.classes_, len(class_list))
        m = compute_classification_metrics(
            y[split.val_idx],
            y_pred,
            class_list,
            y_proba=proba,
            y_train_true=y[split.train_idx],
            y_train_pred=clf.predict(X[split.train_idx]),
            oob_score=float(clf.oob_score_),
            split_meta=split,
        )
        m_vid = _video_level_metrics(y[split.val_idx], y_pred, groups[split.val_idx], class_list)
        report["holdout_window"] = {
            k: m[k]
            for k in (
                "accuracy",
                "macro_f1",
                "balanced_accuracy",
                "split_strategy",
                "leakage_risk",
                "unreliable_classes",
                "oob_score",
                "oob_score_caveat",
                "f1_per_class",
            )
        }
        report["holdout_video"] = m_vid
        print("holdout window macro_f1=", m["macro_f1"], "split=", m.get("split_strategy"))
        print("holdout video   macro_f1=", m_vid["macro_f1"], "n_videos=", m_vid["n_videos"])
    else:
        from sklearn.model_selection import GroupKFold

        n_splits = min(args.n_splits, min_vids) if min_vids >= 2 else 2
        if min_vids < args.n_splits:
            print(
                f"AVISO: min_videos_per_class={min_vids} < n_splits={args.n_splits}; "
                f"usando n_splits={n_splits}. No se inventan folds.",
            )
        if min_vids < 2:
            raise SystemExit("GroupKFold requiere al menos 2 vídeos en alguna clase; abortando")

        gkf = GroupKFold(n_splits=n_splits)
        fold_macro: list[float] = []
        fold_acc: list[float] = []
        fold_bal: list[float] = []
        fold_vid_macro: list[float] = []
        fold_details: list[dict[str, Any]] = []

        for fold_i, (tr, va) in enumerate(gkf.split(X, y, groups)):
            from sklearn.ensemble import RandomForestClassifier

            clf = RandomForestClassifier(
                n_estimators=args.n_estimators,
                random_state=args.seed + fold_i,
                class_weight="balanced_subsample",
                n_jobs=-1,
                oob_score=True,
            )
            clf.fit(X[tr], y[tr])
            y_pred = clf.predict(X[va])
            proba = _align_proba(clf.predict_proba(X[va]), clf.classes_, len(class_list))
            m = compute_classification_metrics(
                y[va],
                y_pred,
                class_list,
                y_proba=proba,
                oob_score=float(clf.oob_score_),
            )
            m_vid = _video_level_metrics(y[va], y_pred, groups[va], class_list)
            fold_macro.append(float(m["macro_f1"]))
            fold_acc.append(float(m["accuracy"]))
            fold_bal.append(float(m["balanced_accuracy"]))
            fold_vid_macro.append(float(m_vid["macro_f1"]))
            fold_details.append(
                {
                    "fold": fold_i,
                    "n_val": int(len(va)),
                    "n_val_videos": int(len(set(groups[va].tolist()))),
                    "macro_f1_window": m["macro_f1"],
                    "macro_f1_video": m_vid["macro_f1"],
                    "accuracy_window": m["accuracy"],
                },
            )
            print(
                f"fold {fold_i}: window_macro_f1={m['macro_f1']:.4f} "
                f"video_macro_f1={m_vid['macro_f1']:.4f} n_val_videos={len(set(groups[va].tolist()))}",
            )

        def _mean_std(xs: list[float]) -> dict[str, float]:
            arr = np.asarray(xs, dtype=np.float64)
            return {
                "mean": float(arr.mean()),
                "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
                "values": xs,
            }

        report["kfold"] = {
            "n_splits": n_splits,
            "window_macro_f1": _mean_std(fold_macro),
            "window_accuracy": _mean_std(fold_acc),
            "window_balanced_accuracy": _mean_std(fold_bal),
            "video_macro_f1": _mean_std(fold_vid_macro),
            "folds": fold_details,
        }
        wm = report["kfold"]["window_macro_f1"]
        vm = report["kfold"]["video_macro_f1"]
        print(
            f"\n>>> Cap. 6 (window macro-F1): {wm['mean']:.4f} ± {wm['std']:.4f} "
            f"(GroupKFold k={n_splits})",
        )
        print(
            f">>> Cap. 6 (video  macro-F1): {vm['mean']:.4f} ± {vm['std']:.4f}",
        )

    out = args.out
    if out is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = _BACKEND / "vision" / "models" / "reports" / f"eval_{args.mode}_{ts}.json"
    else:
        out = Path(out)
        if not out.is_absolute():
            out = (_BACKEND / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
