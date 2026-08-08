# Spec: Detección de equipamiento (objetos) + overlay de cajas

## Meta

- **Estado:** Activo
- **Alcance:** Detección open-vocabulary de objetos de gimnasio en el frame, envío en el contrato WS v1 y dibujo de bounding boxes en `appWeb`.
- **Código:** `backend/vision/equipment_detector.py`, `backend/vision/realtime_engine.py`, `appWeb/src/components/DetectedObjectsCanvas.tsx`
- **Última revisión:** 2026-08-07 (añadida clase `yoga mat`)

## Resumen

Complementa el clasificador de **ejercicio** (pose → 32D → ONNX) con un detector de **objetos** (YOLO-World vía Ultralytics) que localiza mancuernas, barras, kettlebells, bancos, máquinas, etc. Las cajas se normalizan a `[0,1]` y se dibujan en el overlay del análisis en vivo.

Si Ultralytics/torch no están instalados o el modelo falla al cargar, el motor de pose **sigue funcionando** y `detected_objects` queda vacío.

## Contrato WS (extensión compatible v1)

Campo opcional por frame:

```json
"detected_objects": [
  {
    "label": "dumbbell",
    "label_es": "Mancuerna",
    "confidence": 0.81,
    "bbox_norm": [0.12, 0.40, 0.28, 0.72],
    "equipment_slug": "dumbbell"
  }
]
```

- `bbox_norm`: `[x1, y1, x2, y2]` relativos al frame (mismo sistema que landmarks MediaPipe).
- `equipment_label` del payload: si el usuario no forzó equipo manual, se rellena con el slug mayoritario de las detecciones (`majority_equipment_slug`).

## Configuración

| Env | Default | Notas |
|-----|---------|--------|
| `OBJECT_DETECT_ENABLED` | `false` (Compose demo: `true`) | Activa el detector |
| `OBJECT_DETECT_STRIDE` | `4` | Inferir 1 de cada N frames (reusa última detección) |
| `OBJECT_DETECT_CONF` | `0.28` | Umbral de confianza |
| `OBJECT_DETECT_MODEL` | `yolov8s-world.pt` | Se descarga a la caché de Ultralytics la 1.ª vez |
| `OBJECT_DETECT_IMGSZ` | `320` | Resolución de inferencia |
| `OBJECT_DETECT_CLASSES` | (vacío = defaults) | Lista CSV de prompts EN |

## Implementación

| Pieza | Ruta |
|-------|------|
| Detector | `backend/vision/equipment_detector.py` |
| Factory | `backend/app/services/equipment_detect_factory.py` |
| Orquestación | `backend/vision/realtime_engine.py` |
| Overlay UI | `appWeb/src/components/DetectedObjectsCanvas.tsx` (vivo + análisis de vídeo) |
| Parse cliente | `appWeb/src/lib/poseWsPayload.ts` → `parseDetectedObjects` |

## Incidencias / decisiones

1. **2026-08-07 — Clase `yoga mat` añadida.** Con la ampliación del catálogo de ejercicios a `plank`/`mountain_climber` (isométricos/suelo), se agregó `"yoga mat"` a `DEFAULT_EQUIPMENT_CLASSES` (`label_es="Colchoneta"`, `equipment_slug="mat"`). Como YOLO-World es open-vocabulary, no requiere reentrenar ni descargar pesos nuevos: solo se amplía la lista de prompts EN pasada al modelo. El resto de clases nuevas de ejercicio (`deadlift`, `overhead_press`, `pushup`, `jumping_jack`) ya quedaban cubiertas por `barbell`/`dumbbell`/`weight plate` existentes.
2. **Open-vocab (YOLO-World)** en lugar de COCO clásico: COCO no tiene clases fiables de mancuerna/barra.
3. **Stride** por defecto 4 para no hundir el FPS junto a MediaPipe.
4. Dependencia pesada (`ultralytics` + `torch`): la imagen Docker crece; desactivar con `OBJECT_DETECT_ENABLED=false` si solo se necesita pose.
5. Precisión variable con tomas lejanas, oclusiones y prompts; no sustituye curación humana para tesis cuantitativa.
6. **`YOLO_CONFIG_DIR=/tmp/Ultralytics`** en Compose: Ultralytics intenta escribir `settings.yaml` bajo el home del proceso; en contenedor provoca `PermissionError` sin este env.
7. **CLIP + `git` en imagen:** YOLO-World importa el paquete `clip` de Ultralytics; el `Dockerfile` del backend instala `git` y `git+https://github.com/ultralytics/CLIP.git` en build para no fallar en runtime.

## Pruebas manuales

1. `OBJECT_DETECT_ENABLED=true` y reiniciar backend.
2. Análisis en vivo **o** de vídeo con mancuernas a la vista → cajas + etiqueta ES sobre el preview (capa «Objetos» en vídeo).
3. `curl`/WS: payload incluye `detected_objects` no vacío cuando hay detección.
