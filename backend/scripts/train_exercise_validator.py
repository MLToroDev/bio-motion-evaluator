#!/usr/bin/env python3
"""
Entrena el teacher/validador ONNX desde muestras approved (DB) o CSV/JSONL.

Uso (desde ``backend/``, o en el contenedor)::

    # Desde CSV de ejemplo (smoke)
    python scripts/train_exercise_validator.py \\
      --csv scripts/examples/exercise_features_multiclass.csv \\
      --classes idle,squat,lunge

    # Desde feature_samples approved en PostgreSQL
    python scripts/train_exercise_validator.py --from-db --classes squat,lunge,curl,idle,running

El artefacto estable queda en ``vision/models/exercise_validator.onnx`` (+ sidecar de clases).
Runtime: ``EXERCISE_VALIDATOR_ENABLED=true`` y ``EXERCISE_VALIDATOR_TEACHER=onnx`` (o ``auto``).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from vision.exercise_rf_train import FEATURE_DIM  # noqa: E402
from vision.exercise_validator_train import train_validator_export_onnx  # noqa: E402


def _feature_keys() -> list[str]:
    return [f"f{i}" for i in range(FEATURE_DIM)]


def _require_file(path: Path, kind: str) -> Path:
    path = path.expanduser()
    if path.is_file():
        return path.resolve()
    alt = (_BACKEND / path).resolve()
    if alt.is_file():
        return alt
    raise SystemExit(f"No se encontro {kind}: {path}")


def load_csv(path: Path, label_column: str) -> tuple[np.ndarray, np.ndarray]:
    keys = _feature_keys()
    xs: list[list[float]] = []
    ys: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV sin cabecera")
        missing = [k for k in keys if k not in reader.fieldnames]
        if missing:
            raise ValueError(f"Faltan columnas: {missing[:5]}...")
        if label_column not in reader.fieldnames:
            raise ValueError(f"Columna etiqueta '{label_column}' no encontrada")
        for row in reader:
            vec = [float(row[k]) for k in keys]
            lab = (row.get(label_column) or "").strip().lower()
            if not lab:
                continue
            xs.append(vec)
            ys.append(lab)
    if not xs:
        raise ValueError("No hay filas validas en el CSV")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


def load_jsonl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[list[float]] = []
    ys: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            feat = obj.get("features")
            lab = (obj.get("label") or "").strip().lower()
            if not isinstance(feat, list) or len(feat) != FEATURE_DIM or not lab:
                raise ValueError(f"JSONL invalido en linea {line_no}")
            xs.append([float(x) for x in feat])
            ys.append(lab)
    if not xs:
        raise ValueError("No hay muestras en el JSONL")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


def _load_from_db(class_list: list[str]) -> tuple[np.ndarray, np.ndarray]:
    from app.db.models import FeatureSampleORM
    from app.db.session import SessionLocal, engine_configured

    if not engine_configured():
        raise SystemExit("DATABASE_URL no configurada; no se puede usar --from-db")

    xs: list[list[float]] = []
    ys: list[str] = []
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
            xs.append([float(x) for x in vec])
            ys.append(lab)
    if len(xs) < 2:
        raise SystemExit(
            "No hay suficientes muestras approved (min. 2) para las clases indicadas.",
        )
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


def main() -> None:
    p = argparse.ArgumentParser(description="Entrena teacher exercise_validator → ONNX (32D)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", type=Path, help="CSV f0..f31 + label")
    src.add_argument("--jsonl", type=Path, help="JSONL {features:[32], label}")
    src.add_argument(
        "--from-db",
        action="store_true",
        help="Cargar feature_samples con review_status=approved",
    )
    p.add_argument("--label-column", default="label")
    p.add_argument(
        "--classes",
        default="",
        help="Orden de clases (coma). Si vacio con CSV, se infiere del dataset.",
    )
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-estimators", type=int, default=120)
    p.add_argument("--window-size", type=int, default=45)
    p.add_argument(
        "--no-set-manifest-active",
        action="store_true",
        help="No actualizar manifest['validator_active']",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directorio de salida (default: vision/models)",
    )
    args = p.parse_args()

    try:
        import sklearn  # noqa: F401
        import skl2onnx  # noqa: F401
    except ImportError as exc:
        print("Faltan sklearn/skl2onnx. pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.from_db:
        class_list = [c.strip().lower() for c in args.classes.split(",") if c.strip()]
        if len(class_list) < 2:
            raise SystemExit("--from-db requiere --classes con al menos 2 etiquetas")
        X, y_str = _load_from_db(class_list)
    elif args.csv is not None:
        csv_path = _require_file(args.csv, "CSV")
        X, y_str = load_csv(csv_path, args.label_column)
    else:
        jsonl_path = _require_file(args.jsonl, "JSONL")
        X, y_str = load_jsonl(jsonl_path)

    if args.classes.strip():
        class_list = [c.strip().lower() for c in args.classes.split(",") if c.strip()]
    else:
        counts: dict[str, int] = {}
        for lab in y_str.tolist():
            k = str(lab).strip().lower()
            counts[k] = counts.get(k, 0) + 1
        class_list = sorted(counts.keys(), key=lambda k: (-counts[k], k))

    if len(set(class_list)) != len(class_list):
        raise SystemExit("--classes contiene duplicados")
    if len(class_list) < 2:
        raise SystemExit("Se necesitan al menos 2 clases para el teacher")

    unknown = sorted(set(str(s).strip().lower() for s in y_str.tolist()) - set(class_list))
    if unknown:
        mask = np.array([str(s).strip().lower() in class_list for s in y_str.tolist()])
        X = X[mask]
        y_str = y_str[mask]
        print(f"Aviso: se omitieron etiquetas fuera de --classes: {unknown}", file=sys.stderr)

    if X.shape[0] < 2:
        raise SystemExit("Menos de 2 filas validas tras filtrar clases")

    out_dir = args.out_dir
    if out_dir is not None and not out_dir.is_absolute():
        out_dir = (_BACKEND / out_dir).resolve()

    metrics = train_validator_export_onnx(
        X,
        y_str,
        class_list,
        _BACKEND,
        out_dir=out_dir,
        test_size=args.test_size,
        seed=args.seed,
        n_estimators=args.n_estimators,
        window_size=args.window_size,
        set_manifest_active=not args.no_set_manifest_active,
        write_stable_copy=True,
    )
    printable = {
        k: v
        for k, v in metrics.items()
        if k not in ("classification_report", "confusion_matrix")
    }
    print(json.dumps(printable, indent=2))
    print("\nActiva en runtime:")
    print("  EXERCISE_VALIDATOR_ENABLED=true")
    print("  EXERCISE_VALIDATOR_TEACHER=onnx   # o auto")
    print(f"  # modelo: {metrics.get('stable_onnx_path') or metrics.get('onnx_path')}")


if __name__ == "__main__":
    main()
