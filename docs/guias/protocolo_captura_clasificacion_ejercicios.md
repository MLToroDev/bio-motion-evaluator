# Protocolo de captura para clasificación de ejercicios (catálogo v1)

Este documento fija las condiciones mínimas para que las reglas heurísticas (Fase A) y el modelo ONNX entrenado sobre features 32D (Fase B) sean reproducibles y defendibles en el trabajo de grado.

## Ángulo de cámara y encuadre

- **Plano principal:** **sagital de cuerpo completo** (cámara de frente o ligeramente en tres cuartos, pero **consistente** dentro de una sesión).
- **Distancia:** aproximadamente **2,0–3,5 m** entre cámara y sujeto (ver catálogo en `backend/vision/data/exercise_catalog.json`).
- **Encuadre:** cabeza a pies dentro del fotograma; sin recortes fuertes que oculten rodillas o cadera.

## Catálogo inicial (etiquetas)

| `id`   | Nombre UI (ES)     | Notas |
|--------|--------------------|--------|
| `idle` | Reposo / en pie    | Sin ejercicio dinámico claro |
| `squat`| Sentadilla         | Contrato de reps: `SquatRepTracker` |
| `lunge`| Estocada (beta)    | Alta asimetría esperada; reps genéricas (`unknown` tracker) hasta módulo propio |

## Coherencia con el backend

- Features: `FeatureEngine` → vector **32** floats (`docs/planificacion/bio_motion_plan_v2.md`).
- Clasificador Fase A: `HeuristicExerciseClassifier` (sin ONNX).
- Clasificador Fase B: ONNX registrado en `vision/models/manifest.json` (ver script de entrenamiento).
- **Forzar ejercicio:** `forced_exercise_label` en la configuración WebSocket omite el clasificador y fija etiqueta (confianza 1,0) para pruebas y demostración.

## Exportación de datos (Fase B)

1. Grabar videos bajo `tests/assets/videos/`.
2. Para etiqueta uniforme por archivo: `scripts/export_features_from_video.py --video archivo.mp4 --label squat ...`
3. Para etiquetas por tramos temporales: `--segments segments.json` (lista de `{ "start_sec", "end_sec", "label" }`). Ver ejemplo en `backend/scripts/examples/segments_example.json`.
