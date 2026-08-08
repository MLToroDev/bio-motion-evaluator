# Spec: Catálogo de ejercicios + dataset externo (exercises-dataset)

## Meta

- **Estado:** Activo
- **Alcance:** Catálogo del motor (`exercise_catalog.json`), API pública de enriquecimiento UI, y vínculo con [hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset).
- **Código:** `backend/vision/data/exercise_catalog.json`, `backend/app/api/v1/exercises.py`, `appWeb/src/lib/exerciseCatalog.ts`, `appWeb/src/components/DetectedExerciseHero.tsx`
- **Última revisión:** 2026-08-07 (ronda de entrenamiento exhaustiva: 11 clases)

## Resumen

`exercises-dataset` **no es un clasificador de pose**. Es un catálogo estático (1 324 ejercicios: nombre, músculo, equipo, instrucciones multilenguaje, GIF/miniatura). Bio-Motion lo usa solo para **enriquecer la etiqueta que ya produce el motor** (MediaPipe → vector 32D → ONNX/heurística): nombre en español, equipo, músculo y GIF de referencia vía CDN.

La detección del ejercicio en vivo sigue dependiendo del modelo entrenado con vídeos (gold / YouTube → `feature_samples`).

## Contrato

### `GET /api/v1/exercises/catalog`

Respuesta JSON:

| Campo | Tipo | Notas |
|-------|------|--------|
| `exercises` | array | Entradas del catálogo activo del motor (`id` = etiqueta del clasificador) |
| `by_id` | object | Mapa `id` → entrada |
| `external_dataset.cdn_base` | string | Base CDN (jsDelivr) para GIFs |
| `external_dataset.attribution` | string | © Gym visual |

Cada ejercicio puede incluir `gif_url` absoluto, `display_es`, `equipment`, `target_muscle`, `instructions_es`, `youtube_search_queries`.

### Etiquetas actuales del motor

11 clases activas, alineadas con trackers / clases entrenables:

| Clase | Señal biomecánica dominante (vector 32D) | Rep tracker |
|-------|--------------------------------------------|-------------|
| `idle` | Postura neutra, baja periodicidad de ventana (índice 15) | `unknown` |
| `squat` | Flexión bilateral de rodilla (0-20) con ciclos | `squat` |
| `lunge` | Flexión de rodilla con asimetría marcada entre lados | `unknown` |
| `curl` | Flexión cíclica de codo, tronco erguido; **incluye sentado** (rodillas fijas ~90°, no squat) | `curl` |
| `running` | Locomoción cíclica de alta cadencia, sin fase de fuerza | `unknown` |
| `pushup` | Flexión cíclica de codo **con tronco casi horizontal** (F1, índice 21) — se distingue de `curl` por inclinación de tronco y de `squat`/`lunge` por flexión de codo dominante | `pushup` |
| `plank` | Tronco horizontal sostenido **sin ciclos** (periodicidad de ventana baja pese a F1 alto) — contrasta con `idle` (tronco erguido) y con `pushup`/`mountain_climber` (mismo tronco pero con ciclos) | `unknown` |
| `jumping_jack` | Patrón simétrico y rápido: muñecas muy por encima de hombros (F4, índices 27-28) + apertura de base de apoyo (F2) + alta velocidad angular (F5) | `jumping_jack` |
| `overhead_press` | Muñecas muy por encima de hombros en el punto alto (F4 fuerte), movimiento lento y controlado (velocidad angular F5 baja) a diferencia de `jumping_jack`; tronco erguido | `overhead_press` |
| `deadlift` | Flexión de cadera dominante (F3, índices 24-26) con flexión de rodilla moderada — a diferencia de `squat`, donde domina la rodilla; tronco se inclina (F1) en la bajada | `deadlift` |
| `mountain_climber` | Flexión de rodilla alterna y rápida con tronco casi horizontal (plancha alta) — similar a `running` pero con F1 alto en vez de bipedestación | `unknown` |

Las 6 clases nuevas (`pushup`, `plank`, `jumping_jack`, `overhead_press`, `deadlift`, `mountain_climber`) se añadieron en la ronda de entrenamiento exhaustiva de 2026-08-07 (ver `docs/spec/dev-learning-api.md` § Incidencias y decisiones y bitácora de tesis). Todas usan señales ya presentes en `vision/biomechanics.py`/`vision/feature_engine.py` (F1-F5), sin ampliar la dimensión del vector.

## Implementación

| Pieza | Ruta |
|-------|------|
| Catálogo | `backend/vision/data/exercise_catalog.json` |
| Subconjunto curado del dataset externo | `backend/vision/data/external/exercises_curated.json` |
| API | `backend/app/api/v1/exercises.py` |
| Cliente live | `appWeb/src/pages/LiveAnalysis/LiveAnalysis.tsx` + `DetectedExerciseHero` |
| Ingesta masiva YouTube | `backend/scripts/batch_youtube_ingest_and_train.py` |

## Incidencias / decisiones

1. **No entrenar 1 324 clases** con el vector 32D: el espacio de features no discrimina ese vocabulario; se curan pocas clases biomecánicamente distintas.
2. El JSON completo (~17 MB) no se versiona (`.gitignore`); se puede re-descargar desde GitHub si hace falta ampliar el subconjunto.
3. GIFs se sirven desde CDN jsDelivr del repo upstream (atribución obligatoria en UI).
4. **2026-08-07 — Curl sentado (`96O5mvyblQM`):** el ONNX leaky no generaliza a curl sentado (rodillas altas fijas → squat/idle) ni a curl **unilateral** (promedio L/R). Mitigación: `curl_isolation_score` + codo/muñeca dominantes, tracker `dominant_elbow_flexion`, umbral de overlay más permisivo. No se activa un RF nuevo (criterio F5).

## Pruebas manuales

1. `curl -fsS http://localhost:8000/api/v1/exercises/catalog | jq '.by_id.squat'`
2. Análisis en vivo → al detectar squat/running debe aparecer el hero con nombre ES + GIF.
3. (Opcional) `python scripts/batch_youtube_ingest_and_train.py --labels squat,curl,lunge --max-videos 3 --set-active`
