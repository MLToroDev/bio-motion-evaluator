# Spec: Catálogo de ejercicios + dataset externo (exercises-dataset)

## Meta

- **Estado:** Activo
- **Alcance:** Catálogo del motor (`exercise_catalog.json`), API pública de enriquecimiento UI, y vínculo con [hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset).
- **Código:** `backend/vision/data/exercise_catalog.json`, `backend/app/api/v1/exercises.py`, `appWeb/src/lib/exerciseCatalog.ts`, `appWeb/src/components/DetectedExerciseHero.tsx`
- **Última revisión:** 2026-08-07

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

`idle`, `squat`, `lunge`, `curl`, `running` (alineadas con trackers / clases entrenables).

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

## Pruebas manuales

1. `curl -fsS http://localhost:8000/api/v1/exercises/catalog | jq '.by_id.squat'`
2. Análisis en vivo → al detectar squat/running debe aparecer el hero con nombre ES + GIF.
3. (Opcional) `python scripts/batch_youtube_ingest_and_train.py --labels squat,curl,lunge --max-videos 3 --set-active`
