# Hallazgos: fuga de datos y métricas honestas (2026-08-07)

## Meta

- **Estado:** Activo
- **Alcance:** Interpretación del gap entre métricas row-level (~0.95) y GroupSplit/GroupKFold (~0.24), implicaciones para la tesis y plan de remediación de datos.
- **Última revisión:** 2026-08-07

## Resumen ejecutivo

No se estaba **midiendo** la generalización correctamente. El RandomForest sí aprendía patrones, pero el holdout aleatorio por ventana dejaba ventanas del mismo vídeo en train y validación → **fuga de datos**. La cifra a citar en Cap. 6 es GroupKFold, no el 0.95 histórico.

## Evidencia cuantitativa

| Fuente | Métrica | Valor | Interpretación |
|--------|---------|-------|----------------|
| Job `exercise_rf_ad157f19` (activo) | macro-F1 holdout **row-level** | 0.952 | Cota optimista (leakage) |
| Job `exercise_rf_1fba912f` | macro-F1 **group_shuffle** | 0.216 | Generalización a vídeo nuevo |
| Mismo job | OOB score | 0.946 | Row-level; **no** leakage-free (`oob_score_caveat`) |
| GroupKFold k=5 | window macro-F1 | **0.242 ± 0.066** | Número Cap. 6 (ventana) |
| GroupKFold k=5 | video macro-F1 | **0.328 ± 0.126** | Número Cap. 6 (voto por vídeo) |

Snapshot F0: `backend/vision/models/reports/f0_snapshot_2026-08-07.json`  
Criterio y decisión F5: `f5_acceptance_criteria.json`, `f5_activation_decision.json`  
Eval KFold: `eval_kfold_20260807T235335Z.json`

## Qué implica / qué no

- **Sí:** el protocolo de validación anterior sobreestimaba el desempeño; hay que enriquecer diversidad (personas, ángulos, forma imperfecta, grabaciones propias).
- **No:** el vector 32D, MediaPipe o el export ONNX están “rotos”. El modelo activo en producción se mantiene con salvedad metodológica explícita.
- **Decisión F5:** no activar el candidato GroupSplit (macro-F1 0.22 ≪ umbral 0.70). Activos: `exercise_rf_ad157f19` / `exercise_validator_fe345eab`.

## Remediación de datos (ronda diversidad)

1. **Grabaciones propias** (dominio real, forma imperfecta aceptable): inventariar y etiquetar; ingerir con `label_source=own_recording`.
2. **YouTube diverso:** queries con front/side/gym/beginner/imperfect form (no solo “perfect form”).
3. Reevaluar solo con **GroupKFold**; no reactivar modelos por métricas row-level.

### Resultado ronda 2026-08-07/08 (post-propias + YouTube diverso)

| Métrica | Antes (F5) | Después diversidad |
|---------|------------|--------------------|
| n_vídeos totales | 120 | **172** |
| min vídeos/clase | 7 | **12** |
| n_ventanas approved | 43120 | **56326** |
| GroupKFold window macro-F1 | 0.242 ± 0.066 | **0.295 ± 0.046** |
| GroupKFold video macro-F1 | 0.328 ± 0.126 | **0.393 ± 0.060** |
| Propias (`own_recording`) | 0 | running 1748 + squat 46 |

Interpretación: mejora real y menor varianza entre folds, pero **sigue por debajo** del umbral F5 (macro-F1 ≥ 0.70). No activar candidato nuevo. Siguiente: etiquetar más clips de `Media/` (guía `docs/guias/etiquetar_grabaciones_propias.md`) y más sujetos/ángulos por clase.

Reportes: `eval_kfold_20260808T000930Z.json`, `own_recordings_manifest.ingest_report.json`.

## Mitigaciones operativas (sin reentrenar el RF)

Mientras F5 no se cumple, el wrapper `_OnnxWithPostureRescue` corrige fallos visibles del modelo leaky **sin activar un ONNX nuevo**:

| Postura observada | Etiqueta leaky típica | Rescate |
|-------------------|----------------------|---------|
| De pie quieto | `deadlift` | `idle_still_score` ≥ 0,62 y mayor que curl |
| Curl sentado / unilateral | `squat` / `idle` / `unknown` | `curl_isolation_score` enter 0,55 / hold 0,38 |
| Push-up (tronco alto + codo rápido) | riesgo `curl` | compuerta de tronco en `curl_isolation_score` |

Esto es **heurística de producto**, no evidencia de generalización. Cap. 6 debe citar GroupKFold, no estas reglas.

## Trazabilidad código

- `backend/vision/model_validation.py`
- `backend/vision/exercise_rf_train.py`
- `docs/spec/model-validation-methodology.md`
- `docs/spec/dev-learning-api.md`
