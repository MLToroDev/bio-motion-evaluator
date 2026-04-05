#!/usr/bin/env python3
"""
Entrena un clasificador de ejercicio ligero y exporta ONNX para el pipeline
``FeatureEngine`` → ``exercise_classifier.py`` (entrada float32 [1, 32]).

Requisitos adicionales::

    pip install -r requirements-train.txt

Datos
-----

**CSV** (cabecera obligatoria): columnas ``f0`` … ``f31`` y columna de etiqueta
(por defecto ``label``). Cada fila = una ventana ya agregada (mismo vector que
``FeatureEngine.build_feature_vector()`` en un instante).

Ejemplo mínimo de 2 filas (solo ilustración; números inventados)::

    f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31,label
    0.1,0.2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,squat
    0.05,0.05,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,unknown

**JSONL**: una línea JSON por muestra::

    {"features": [0.1, 0.2, ... 32 floats ...], "label": "squat"}

Cómo obtener filas reales
-------------------------

1. ``scripts/export_features_from_video.py`` — recorre un MP4 en
   ``tests/assets/videos/`` y escribe CSV (``--label`` fijo por vídeo).
2. Instrumentar el backend o exportar desde BD (futuro).

El runtime ONNX aplica ``softmax`` sobre la primera salida; los bosques
aleatorios en ONNX suelen emitir **probabilidades** ya normalizadas: el **argmax**
(categoría) suele coincidir; la confianza mostrada puede estar sesgada.

Uso (desde la carpeta ``backend``)::

    pip install -r requirements-train.txt
    python scripts/train_exercise_classifier_from_csv.py ^
      --csv scripts/examples/exercise_features_sample.csv ^
      --out models/mi_clf.onnx ^
      --classes unknown,squat

Multiclase + manifest (fusiona ``vision/models/manifest.json``; opcional ``--set-manifest-active``)::

    python scripts/train_exercise_classifier_from_csv.py ^
      --csv scripts/examples/exercise_features_multiclass.csv ^
      --out vision/models/exercise_rf_v1.onnx ^
      --classes idle,squat,lunge ^
      --write-manifest vision/models/manifest.json ^
      --manifest-model-key exercise_rf_v1

Sustituye ``--csv`` por la ruta a **tu** dataset real (no uses el nombre literal ``tu_dataset.csv`` del README si ese archivo no existe).

Con ``--write-manifest`` se actualiza ``path``/``classes``/``window_size``; sin ``--set-manifest-active``
la clave ``active`` del JSON no cambia (sigue el heurístico si ``active`` es null).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys
from pathlib import Path

import numpy as np

FEATURE_DIM = 32


def _merge_manifest(
    manifest_path: Path,
    backend_root: Path,
    model_key: str,
    onnx_rel_posix: str,
    class_list: list[str],
    window_size: int,
    *,
    set_active: bool,
) -> None:
    manifest_path = manifest_path.expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (backend_root / manifest_path).resolve()
    data: dict = {}
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as f:
            data = json.load(f)
    models = dict(data.get("models") or {})
    models[model_key] = {
        "path": onnx_rel_posix,
        "classes": class_list,
        "window_size": window_size,
        "feature_vector_dim": FEATURE_DIM,
        "created_at": _dt.date.today().isoformat(),
        "note": "RandomForest desde train_exercise_classifier_from_csv.py (--write-manifest)",
    }
    data["models"] = models
    if set_active:
        data["active"] = model_key
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _require_existing_file(path: Path, kind: str) -> Path:
    """Resuelve CSV/JSONL; si no existe, mensaje útil (evita confusión con nombres placeholder)."""
    path = path.expanduser()
    if path.is_file():
        return path.resolve()
    backend = Path(__file__).resolve().parent.parent
    alt = (backend / path).resolve()
    if alt.is_file():
        return alt
    sample = Path(__file__).resolve().parent / "examples" / "exercise_features_sample.csv"
    print(f"No se encontró el archivo {kind}: {path}", file=sys.stderr)
    if sample.is_file():
        try:
            csv_hint = sample.relative_to(backend)
        except ValueError:
            csv_hint = sample
        print(
            "\n«tu_dataset.csv» en la documentación era solo un ejemplo de nombre.\n"
            "Crea tu CSV con columnas f0…f31 y la columna de etiqueta, o prueba:\n",
            file=sys.stderr,
        )
        print(
            f"  python scripts/train_exercise_classifier_from_csv.py "
            f"--csv {csv_hint.as_posix()} --out models/mi_clf.onnx --classes unknown,squat\n",
            file=sys.stderr,
        )
    raise SystemExit(2)


def _feature_keys() -> list[str]:
    return [f"f{i}" for i in range(FEATURE_DIM)]


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
            raise ValueError(f"Faltan columnas: {missing[:5]}…")
        if label_column not in reader.fieldnames:
            raise ValueError(f"Columna etiqueta '{label_column}' no encontrada")
        for row in reader:
            try:
                vec = [float(row[k]) for k in keys]
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Fila inválida: {row}") from exc
            lab = (row.get(label_column) or "").strip()
            if not lab:
                continue
            xs.append(vec)
            ys.append(lab)
    if not xs:
        raise ValueError("No hay filas válidas en el CSV")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


def load_jsonl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[list[float]] = []
    ys: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL línea {line_no}") from exc
            feat = obj.get("features")
            lab = (obj.get("label") or "").strip()
            if not isinstance(feat, list) or len(feat) != FEATURE_DIM:
                raise ValueError(f"Línea {line_no}: 'features' debe ser lista de {FEATURE_DIM} floats")
            if not lab:
                continue
            xs.append([float(x) for x in feat])
            ys.append(lab)
    if not xs:
        raise ValueError("No hay muestras en el JSONL")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys)


def main() -> None:
    p = argparse.ArgumentParser(description="Entrena clasificador ejercicio → ONNX (32 features)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", type=Path, help="CSV con f0..f31 y columna de etiqueta")
    src.add_argument("--jsonl", type=Path, help="JSONL con {features: [32], label}")
    p.add_argument("--label-column", default="label", help="Nombre columna etiqueta en CSV")
    p.add_argument(
        "--classes",
        required=True,
        help="Orden de clases separado por comas (debe coincidir con manifest), ej. unknown,squat,lunge",
    )
    p.add_argument("--out", type=Path, required=True, help="Ruta salida .onnx (relativa a cwd o absoluta)")
    p.add_argument("--test-size", type=float, default=0.2, help="Fracción holdout estratificado")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument(
        "--write-manifest",
        type=Path,
        default=None,
        help="Escribir o fusionar vision/models/manifest.json (ruta típica desde backend: vision/models/manifest.json)",
    )
    p.add_argument(
        "--manifest-model-key",
        default="exercise_rf_active",
        help="Nombre del modelo dentro de manifest['models']",
    )
    p.add_argument(
        "--manifest-window-size",
        type=int,
        default=45,
        help="Ventana FeatureEngine (debe coincidir con la usada al exportar CSV)",
    )
    p.add_argument(
        "--set-manifest-active",
        action="store_true",
        help="Poner manifest['active'] = --manifest-model-key (si no, solo se registra el bloque en models)",
    )
    args = p.parse_args()

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:
        print(
            "Faltan dependencias. Instala:\n  pip install -r requirements-train.txt\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    class_list = [c.strip() for c in args.classes.split(",") if c.strip()]
    if len(set(class_list)) != len(class_list):
        raise SystemExit("--classes contiene duplicados")
    label_to_idx = {c: i for i, c in enumerate(class_list)}

    if args.csv is not None:
        csv_path = _require_existing_file(args.csv, "CSV")
        X, y_str = load_csv(csv_path, args.label_column)
    else:
        jsonl_path = _require_existing_file(args.jsonl, "JSONL")
        X, y_str = load_jsonl(jsonl_path)

    unknown_labels = sorted(set(y_str.tolist()) - set(label_to_idx))
    if unknown_labels:
        raise SystemExit(f"Etiquetas en datos no listadas en --classes: {unknown_labels}")

    y = np.array([label_to_idx[s] for s in y_str], dtype=np.int64)
    if X.shape[1] != FEATURE_DIM:
        raise SystemExit(f"Se esperaban {FEATURE_DIM} columnas, hay {X.shape[1]}")

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=args.test_size,
            random_state=args.seed,
            stratify=y,
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=args.test_size,
            random_state=args.seed,
        )

    clf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        random_state=args.seed,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=class_list))

    initial_types = [("float_input", FloatTensorType([None, FEATURE_DIM]))]
    onnx_model = convert_sklearn(
        clf,
        initial_types=initial_types,
        options={id(clf): {"zipmap": False}},
    )

    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        f.write(onnx_model.SerializeToString())

    print(f"\nONNX escrito: {out_path.resolve()}")

    backend_root = Path(__file__).resolve().parent.parent
    out_abs = out_path.resolve()
    try:
        onnx_rel = out_abs.relative_to(backend_root).as_posix()
    except ValueError:
        onnx_rel = out_abs.as_posix()

    if args.write_manifest is not None:
        mp = Path(args.write_manifest)
        _merge_manifest(
            mp,
            backend_root,
            args.manifest_model_key,
            onnx_rel,
            class_list,
            args.manifest_window_size,
            set_active=args.set_manifest_active,
        )
        dest = mp if mp.is_absolute() else (backend_root / mp).resolve()
        print(f"Manifest fusionado: {dest}")
        if not args.set_manifest_active:
            print("(active no modificado; usa --set-manifest-active para activar este modelo)")

    print("\n--- Fragmento manual vision/models/manifest.json (si no usas --write-manifest) ---")
    classes_json = ", ".join(json.dumps(c) for c in class_list)
    print(f'  "path": "{onnx_rel}",')
    print(f'  "classes": [{classes_json}],')
    print(f'  "window_size": {args.manifest_window_size},')
    print(f'  "feature_vector_dim": {FEATURE_DIM},')
    print("---")


if __name__ == "__main__":
    main()
