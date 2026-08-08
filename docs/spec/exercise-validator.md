# Spec: Validador / teacher de ejercicio (confirm | reject | changed)

## Meta

- **Estado:** Activo
- **Alcance:** Segunda etapa ligera sobre el vector 32D que valida la etiqueta del clasificador primario, ayuda a gatear `AUTO_COLLECT` y expone veredicto en el contrato WS v1.
- **Código:** `backend/vision/exercise_validator.py`, `backend/vision/exercise_validator_train.py`, `backend/scripts/train_exercise_validator.py`, `backend/vision/realtime_engine.py`, `backend/vision/feature_collector.py`, `appWeb/src/components/DetectedExerciseHero.tsx`
- **Última revisión:** 2026-08-07 (teacher `exercise_validator_fe345eab` cubre las 11 clases activas)

## Resumen

El clasificador primario (ONNX + histéresis, o heurística) propone `exercise_label`. El **validador** actúa como *teacher* ligero (sin Torch extra): compara con un teacher ONNX (RF pequeño), heurístico o margen de scores, y detecta cambios de ejercicio. Emite `exercise_validation` en cada frame cuando `EXERCISE_VALIDATOR_ENABLED=true`.

Ayuda al entrenamiento: con `EXERCISE_VALIDATOR_GATE_COLLECT=true`, solo se persisten muestras `AUTO_COLLECT` cuando el veredicto es `confirm` (`label_source=auto_validated`).

### Cómo dice sí / no / cambió

| `verdict` | Significado operativo |
|-----------|------------------------|
| `confirm` (sí) | Teacher y primario coinciden con confianza/margen suficientes → etiqueta usable para AUTO_COLLECT |
| `reject` (no) | Teacher discrepa con confianza suficiente (`validator_label` = lo que el teacher cree) |
| `changed` | La etiqueta estable del primario pasó de un ejercicio real a otro (hold corto) |
| `uncertain` | Ventana incompleta, `unknown`, margen/confianza bajos |

## Contrato WS (extensión compatible v1)

Campo opcional por frame:

```json
"exercise_validation": {
  "verdict": "confirm",
  "primary_label": "squat",
  "validator_label": "squat",
  "confidence": 0.88,
  "score_margin": 0.31,
  "reason": "teacher_agrees",
  "previous_label": "idle",
  "teacher_mode": "onnx"
}
```

## Configuración

| Env | Default | Notas |
|-----|---------|--------|
| `EXERCISE_VALIDATOR_ENABLED` | `false` (Compose: `true`) | Activa el módulo |
| `EXERCISE_VALIDATOR_MIN_CONFIDENCE` | `0.65` | Umbral teacher/primario |
| `EXERCISE_VALIDATOR_MIN_MARGIN` | `0.12` | `top1 - top2` de `raw_scores` |
| `EXERCISE_VALIDATOR_TEACHER` | `auto` (Compose: `onnx`) | `auto` \| `onnx` \| `heuristic` \| `margin` |
| `EXERCISE_VALIDATOR_CHANGE_HOLD_FRAMES` | `8` | Duración del veredicto `changed` |
| `EXERCISE_VALIDATOR_GATE_COLLECT` | `true` | Solo `confirm` → AUTO_COLLECT |
| `EXERCISE_VALIDATOR_ONNX_PATH` | vacío | Override; vacío → `vision/models/exercise_validator.onnx` |
| `EXERCISE_VALIDATOR_CLASSES` | vacío | Override CSV de clases; vacío → sidecar / `manifest.validator_active` |

### Teacher ONNX (artefacto)

- Ruta estable: `backend/vision/models/exercise_validator.onnx`
- Versionado: `exercise_validator_<hash8>.onnx` + entrada en `manifest.json` con `"role": "exercise_validator"` y clave `validator_active` (no altera `active` del clasificador primario).
- Sidecar de clases: `exercise_validator.classes.json` (o `<onnx>.classes.json`).
- Runtime: `onnxruntime` (misma pila que el RF primario). Si el archivo falta o no carga → **fallback a `heuristic`**.
- `TEACHER=auto`: ONNX si existe el artefacto; si no, heurística.

### Entrenar / (re)generar el modelo

Desde `backend/` (o contenedor `backend` tras rebuild/copia de scripts):

```bash
# Smoke / demo con CSV de ejemplo
python scripts/train_exercise_validator.py \
  --csv scripts/examples/exercise_features_multiclass.csv \
  --classes idle,squat,lunge

# Producción: muestras approved en PostgreSQL (11 clases, ronda 2026-08-07)
python scripts/train_exercise_validator.py \
  --from-db \
  --classes idle,squat,lunge,curl,running,pushup,plank,jumping_jack,overhead_press,deadlift,mountain_climber \
  --n-estimators 40
```

Reutiliza `vision/exercise_rf_train.train_rf_export_onnx` (RandomForest → skl2onnx). No hace falta descargar Torch/HF: el “modelo pequeño que se baja al servidor” es este ONNX generado y desplegado bajo `vision/models/` (bind mount en Compose).

Activación típica:

```bash
EXERCISE_VALIDATOR_ENABLED=true
EXERCISE_VALIDATOR_TEACHER=onnx
EXERCISE_VALIDATOR_GATE_COLLECT=true
```

## Implementación

| Pieza | Ruta |
|-------|------|
| Validador runtime | `backend/vision/exercise_validator.py` |
| Train / resolve path | `backend/vision/exercise_validator_train.py` |
| CLI | `backend/scripts/train_exercise_validator.py` |
| Orquestación | `backend/vision/realtime_engine.py` |
| Payload | `backend/vision/unified_payload.py` → `exercise_validation` |
| Gate collect | `backend/vision/feature_collector.py`, `backend/app/services/feature_sample_persist.py` |
| Chip UI | `appWeb/src/components/DetectedExerciseHero.tsx` |
| Parse cliente | `appWeb/src/lib/poseWsPayload.ts` → `parseExerciseValidation` |

## Incidencias / decisiones

1. **No se añadió un modelo HF/Torch** para el teacher: YOLO ya aporta peso; el teacher 32D es RF→ONNX entrenable desde `feature_samples` approved (ISO 25010: mantenibilidad y rendimiento).
2. **Prioridad de veredicto:** `changed` > `confirm` > `reject` > `uncertain` durante el hold de transición.
3. Con etiqueta forzada (`forced_exercise_label`) no se emite validación ni se recolecta.
4. El teacher ONNX es **independiente** del clasificador primario (`exercise_rf_*`): mismo layout 32D, distinto artefacto y `validator_active`.
5. **2026-08-07 — Reentrenado a 11 clases, artefacto reducido por tamaño.** Con ~43 120 muestras approved (120 vídeos YouTube, 11 clases), un primer entrenamiento con `n_estimators=200` generó un ONNX de ~60 MB; se redujo a `n_estimators=40` (`exercise_validator_fe345eab.onnx`, ~20 MB) sin pérdida relevante de macro-F1 (0.9517 vs 0.9524 con 200 árboles), priorizando tamaño de artefacto versionable en Git. `f1_per_class` más bajo: `plank` (0.79) — se confunde parcialmente con `idle`/`overhead_press` por su naturaleza isométrica (ver limitaciones en `docs/spec/dev-learning-api.md`).

## Pruebas

- Unitarias: `tests/test_exercise_validator.py` (incl. fallback `auto` y smoke ONNX si existe el artefacto).
- Smoke CLI: entrenar con CSV multiclass → verificar `teacher_mode=onnx` y `exercise_validation.verdict` en `as_dict()`.
- Manual: `EXERCISE_VALIDATOR_ENABLED=true`, `TEACHER=onnx`, análisis en vivo → chip Confirmado / Rechazado / Cambio; con AUTO_COLLECT, muestras `auto_validated` solo en confirm.
