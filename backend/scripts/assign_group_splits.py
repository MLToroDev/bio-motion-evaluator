#!/usr/bin/env python3
"""
Asigna split train/val/test por vídeo (GroupShuffleSplit) a feature_samples.

Respeta herencia: si un source_file ya tiene filas con split fijo, todas las
filas de ese vídeo heredan ese split (no se reasignan).

Uso (desde backend/ o contenedor)::

    python scripts/assign_group_splits.py --dry-run
    python scripts/assign_group_splits.py --apply --test-size 0.2 --seed 42
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from vision.model_validation import FIXED_SPLITS, inherit_group_splits, normalize_group_key  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Asigna split por vídeo a feature_samples")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true", help="Solo reportar (default si no --apply)")
    p.add_argument("--apply", action="store_true", help="Escribir en DB")
    p.add_argument(
        "--review-status",
        default="approved",
        help="Filtrar por review_status (default approved; 'all' = sin filtro)",
    )
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True

    from app.db.models import FeatureSampleORM
    from app.db.session import SessionLocal, engine_configured
    from sklearn.model_selection import GroupShuffleSplit

    if not engine_configured():
        raise SystemExit("DATABASE_URL no configurada")

    with SessionLocal() as db:
        q = db.query(FeatureSampleORM)
        if args.review_status.strip().lower() != "all":
            q = q.filter(FeatureSampleORM.review_status == args.review_status.strip().lower())
        rows = q.all()
        if not rows:
            raise SystemExit("No hay muestras")

        ids = [r.id for r in rows]
        labels = np.asarray([(r.label or "").strip().lower() for r in rows], dtype=object)
        groups = np.asarray([r.source_file for r in rows], dtype=object)
        splits = np.asarray([(r.split or "unset").strip().lower() for r in rows], dtype=object)

        inherited = inherit_group_splits(groups, splits)
        assert inherited is not None

        # Grupos ya congelados: no reasignar
        frozen_groups: set[str] = set()
        for gk, sp in zip(
            [normalize_group_key(None if g is None else str(g)) for g in groups.tolist()],
            inherited.tolist(),
            strict=True,
        ):
            if gk and str(sp) in FIXED_SPLITS:
                frozen_groups.add(gk)

        # Filas / grupos a asignar
        assignable_idx = []
        for i, g in enumerate(groups.tolist()):
            gk = normalize_group_key(None if g is None else str(g))
            if gk is None:
                continue
            if gk in frozen_groups:
                continue
            assignable_idx.append(i)

        new_splits = list(inherited.tolist())
        if len(assignable_idx) >= 2:
            idx = np.asarray(assignable_idx, dtype=int)
            # Un representante por grupo para GroupShuffleSplit
            group_to_indices: dict[str, list[int]] = defaultdict(list)
            for i in idx.tolist():
                gk = normalize_group_key(str(groups[i]))
                if gk:
                    group_to_indices[gk].append(i)
            group_keys = sorted(group_to_indices.keys())
            # Etiqueta mayoritaria del grupo para estratificar a nivel grupo (aprox)
            group_labels = []
            for gk in group_keys:
                labs = [str(labels[i]) for i in group_to_indices[gk]]
                # moda
                mode = max(set(labs), key=labs.count)
                group_labels.append(mode)
            g_arr = np.asarray(group_keys, dtype=object)
            y_g = np.asarray(group_labels, dtype=object)
            if len(group_keys) < 2:
                print("Pocos grupos asignables; solo se aplica herencia")
            else:
                try:
                    gss = GroupShuffleSplit(
                        n_splits=1,
                        test_size=args.test_size,
                        random_state=args.seed,
                    )
                    # X dummy
                    Xd = np.zeros((len(group_keys), 1))
                    tr, va = next(gss.split(Xd, y_g, g_arr))
                    val_groups = {group_keys[i] for i in va.tolist()}
                    train_groups = {group_keys[i] for i in tr.tolist()}
                    assert train_groups.isdisjoint(val_groups)
                    for gk, row_ids in group_to_indices.items():
                        sp = "val" if gk in val_groups else "train"
                        for i in row_ids:
                            new_splits[i] = sp
                except ValueError as exc:
                    print(f"GroupShuffleSplit falló: {exc}; solo herencia aplicada")

        # También propagar herencia a filas unset de grupos frozen
        for i, g in enumerate(groups.tolist()):
            gk = normalize_group_key(None if g is None else str(g))
            if gk and gk in frozen_groups:
                # ya en inherited
                new_splits[i] = str(inherited[i])

        # Resumen
        from collections import Counter

        before = Counter(str(s) for s in splits.tolist())
        after = Counter(str(s) for s in new_splits)
        print("splits before:", dict(before))
        print("splits after:", dict(after))
        print(f"frozen_groups={len(frozen_groups)} assignable_groups≈{len(set(normalize_group_key(str(groups[i])) for i in assignable_idx) - {None})}")

        n_change = sum(1 for a, b in zip(splits.tolist(), new_splits, strict=True) if str(a) != str(b))
        print(f"filas a actualizar: {n_change}")

        if args.dry_run:
            print("dry-run: no se escribió en DB (usa --apply)")
            return

        updated = 0
        for r, sp in zip(rows, new_splits, strict=True):
            sp_s = str(sp)
            if (r.split or "unset").strip().lower() != sp_s:
                r.split = sp_s
                updated += 1
        db.commit()
        print(f"OK: actualizadas {updated} filas")


if __name__ == "__main__":
    main()
