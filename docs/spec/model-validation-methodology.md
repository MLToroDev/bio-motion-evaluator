# Spec: Metodología de validación del clasificador de ejercicio y del validador (teacher)

## Meta

- **Estado:** Activo (implementado 2026-08-07).
- **Alcance:** Cómo se sustenta con evidencia cuantitativa que el `RandomForestClassifier` → ONNX del clasificador primario y del teacher/validador generalizan correctamente (split por vídeo, MetricsBundle, manifest v2, GroupKFold Cap. 6).
- **Código:** `backend/vision/model_validation.py`, `backend/vision/exercise_rf_train.py`, `backend/app/workers/training_tasks.py`, `backend/vision/exercise_validator_train.py`, `backend/scripts/assign_group_splits.py`, `backend/scripts/evaluate_exercise_classifier.py`, `tests/test_model_validation.py`.
- **Última revisión:** 2026-08-07.
- **No cubre:** métricas biomecánicas de ángulos articulares ni el conteo de repeticiones.

## Resumen

El entrenamiento usa **`GroupShuffleSplit` por `source_file`** (o holdout congelado vía columna `split` con herencia por grupo). Las métricas (macro-F1, balanced accuracy, OOB con caveat, ROC/PR-AUC, Brier, `unreliable_classes`) viajan en `TrainingJobORM.metrics_json` y en `manifest.json` (`manifest_version: 2`). El número a citar en Cap. 6 es el de **GroupKFold media ± std** (`evaluate_exercise_classifier.py --mode kfold`), no el holdout leaky histórico.

## Contrato — MetricsBundle (extracto)

Campos relevantes en `metrics_json` / `manifest.models[*].metrics`:

| Campo | Significado |
|-------|-------------|
| `split_strategy` | `group_shuffle` \| `frozen_split` \| `row_stratified` \| `row_unstratified` |
| `leakage_risk` | `true` si row-split o grupos solapados / >30% sin `source_file` |
| `unreliable_classes` | clases con `< min_videos_per_class` (default **3**, Gate F0) |
| `macro_f1`, `balanced_accuracy`, `f1_per_class`, `confusion_matrix` | métricas principales |
| `oob_score` | estimación bootstrap del RF |
| `oob_score_caveat` | `"row-level estimate, not leakage-free for grouped/correlated data"` — **no** equivalente a métricas group-split |
| `roc_auc_ovr` / `pr_auc_ovr` / `brier_score_multiclass` | pueden ser `null`; ver `undefined_metrics` |
| `train_macro_f1`, `overfit_gap_macro_f1` | diagnóstico overfitting |

Root del manifest: `"manifest_version": 2`.

## Metodología

1. **Split por vídeo** (`resolve_split_indices`): prioridad frozen (con herencia) → GroupShuffle → row fallback.
2. **Umbral unreliable:** `n_videos < 3` por clase (confirmado F0; dataset actual min=7 → `[]`).
3. **Cap. 6:** `evaluate_exercise_classifier.py` default `--mode kfold` → media±std ventana y por vídeo.
4. **OOB:** se reporta con caveat; no se usa como evidencia de generalización libre de leakage.

## Implementación (trazabilidad)

| Componente | Ruta |
|---|---|
| Núcleo | `backend/vision/model_validation.py` |
| Train RF + merge_manifest v2 | `backend/vision/exercise_rf_train.py` |
| Celery loader groups/splits | `backend/app/workers/training_tasks.py` |
| Teacher | `backend/vision/exercise_validator_train.py`, `scripts/train_exercise_validator.py` |
| Assign splits | `backend/scripts/assign_group_splits.py` |
| Eval Cap. 6 | `backend/scripts/evaluate_exercise_classifier.py` |
| Tests | `tests/test_model_validation.py` |
| UI | `appWeb/src/pages/dev/Training/Training.tsx` |
| Reportes F0/F5 | `backend/vision/models/reports/` |

## Pruebas manuales

```bash
# Tests núcleo
pytest tests/test_model_validation.py -v

# Cap. 6 (GroupKFold)
python scripts/evaluate_exercise_classifier.py --from-db \
  --classes idle,squat,lunge,curl,running,pushup,plank,jumping_jack,overhead_press,deadlift,mountain_climber

# Entrenamiento Celery (sin activar hasta cumplir criterio)
# POST /api/v1/dev/training/jobs con set_active=false
```

## Incidencias y decisiones

1. **2026-08-07 — Implementación + decisión F5 DO_NOT_ACTIVATE**
   - Criterio escrito **antes** de entrenar (`reports/f5_acceptance_criteria.json`): `split_strategy∈{group_shuffle,frozen_split}`, `leakage_risk=false`, `unreliable_classes=[]`, **macro-F1 group-split ≥ 0.70**, balanced accuracy ≥ 0.65, F1 por clase ≥ 0.40.
   - Candidato `exercise_rf_1fba912f`: split OK, unreliable=[], pero **macro-F1=0.216** (bal.acc=0.314). OOB≈0.946 (row-level) vs val group 0.22 → confirma que el ~0.95 histórico era leakage.
   - GroupKFold k=5: window macro-F1 **0.242 ± 0.066**, video macro-F1 **0.328 ± 0.126** (`eval_kfold_20260807T235335Z.json`).
   - **No se activó** el candidato; permanece `exercise_rf_ad157f19` / `exercise_validator_fe345eab` en producción, con salvedad metodológica.
   - Bug corregido: `unreliable_classes` mapeaba índices int como nombres (`model_validation._label_to_name`).

2. **2026-08-07 — Auditoría previa (F0):** 0 jobs `running`; min vídeos/clase=7; umbral unreliable=3; snapshot en `reports/f0_snapshot_2026-08-07.json`.
