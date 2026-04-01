# Vídeos gold standard (inyección / regresión)

Coloca aquí vídeos **pre-grabados** para probar MediaPipe y el cálculo de ángulos **sin cámara en vivo**.

## Convención

- Solo el **nombre del archivo** se expone al API (seguridad: sin path traversal).
- Ejemplo esperado: `squat_test.mp4` — referencia desde el WebSocket ``/ws/pose-stream``::

```json
{"source": "file", "video_filename": "squat_test.mp4", "target_fps": 15}
```

## Sugerencias para la tesis (Cap. 7)

- Sentadilla de referencia (técnica consistente).
- Sentadilla con **valgo** u otro error reproducible.
- Toma lateral para **dorsiflexión** de tobillo si amplías el análisis.

> Los archivos `.mp4` pueden ser grandes: valora Git LFS o almacenamiento externo según normas de tu programa.

## Export masivo de features (entrenamiento clasificador)

Para generar un único CSV con **todos** los clips de esta carpeta (mismo formato que
``backend/scripts/export_features_from_video.py``), desde ``backend/`` con el venv activo::

    .venv\Scripts\python scripts/export_features_gold_batch.py --out data/gold_all.csv --only-window-full

Etiquetas: copia ``video_labels.example.json`` como ``video_labels.json`` y ajusta el mapeo
``nombre_archivo.mp4`` → clase; si falta una entrada, se usa una heurística por nombre y
luego la etiqueta por defecto ``unknown``.

