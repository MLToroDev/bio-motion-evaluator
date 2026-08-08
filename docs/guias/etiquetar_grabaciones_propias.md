# Plantilla: etiquetar grabaciones propias en Disco C_C/Media

Hay ~**5461** vídeos bajo `/Volumes/Disco C_C/Media` sin etiqueta de ejercicio.
Solo se pueden ingerir de forma segura los que mapees aquí.

## Cómo usar

1. Copia las filas que quieras etiquetar a `backend/vision/data/own_recordings_manifest.json` → `items`.
2. O añade entradas a este archivo y luego:

```bash
# desde el host: copiar el clip a tests/assets/videos/own/ y referenciarlo en el manifiesto
cp "/Volumes/Disco C_C/Media/.../tu_clip.mp4" tests/assets/videos/own/
```

3. Ejecutar:

```bash
docker compose exec backend python scripts/ingest_local_videos.py \
  --manifest vision/data/own_recordings_manifest.json --auto-approve --max-frames 900
```

## Clases válidas

`idle`, `squat`, `lunge`, `curl`, `running`, `pushup`, `plank`, `jumping_jack`, `overhead_press`, `deadlift`, `mountain_climber`

## Sesiones mixtas (recomendado: segmentos)

Para `Entrenamiento.mp4` / `Entrenamiento con cristian.mp4` no uses una sola etiqueta:
anota tramos `start_sec`–`end_sec` por ejercicio (el export local ya soporta `--segments` JSON;
próximo paso: extender `ingest_local_videos.py` con segmentos por item).

## Ya ingeridos (2026-08-07)

| Origen | Label | Muestras approx |
|--------|-------|-----------------|
| SentadillaProfunda + runnings gold/long/jeff/natación | squat / running | 46 + 1748 |

## Pendientes sugeridos (rellenar label)

| Path | Label propuesto | Notas |
|------|-----------------|-------|
| Media/.../Entrenamiento.mp4 | _(segmentos)_ | sesión mixta |
| Media/.../Entrenamiento con cristian.mp4 | _(segmentos)_ | otra persona |
| Media/.../Entreno de resistencia 09-06-2026.mp4 | ¿running? | confirmar |
| (añade más filas) | | forma imperfecta OK |
