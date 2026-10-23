# Datos de la validación física

Aquí se depositan los **datos crudos** que produce la ejecución del protocolo
[`docs/guias/protocolo_validacion_exactitud.md`](../../docs/guias/protocolo_validacion_exactitud.md).

| Ruta | Contenido |
|------|-----------|
| `nivel1/` | Capturas y registros del patrón de referencia físico |
| `nivel1_patron.csv` | Tabla consolidada del Nivel 1: ángulo verdadero frente a ángulo medido |
| `nivel2/<clip>/` | Nivel 2 (video-goniometría manual con Tracker) de un clip propio; ver abajo |

Los ficheros están vacíos mientras el protocolo no se ejecute. **No se inventan datos:**
un archivo ausente significa que esa medición no se ha realizado.

## Nivel 2 con Tracker

Comparador manual: **Tracker** (Open Source Physics), en lugar de Kinovea (protocolo,
sección 2.1). Material: un **clip propio** de una sola toma, en plano sagital, midiendo
solo la pierna más cercana a la cámara; `SentadillaProfunda.mp4` no sirve para
exactitud (protocolo, sección 2.2). `<clip>` es el nombre del vídeo sin extensión.

```
nivel2/<clip>/
  serie_sistema.csv              serie del sistema (exportador)
  metadatos_exportacion.json     geometría, lado, paso y huellas SHA-256 (exportador)
  frames/m0000.png ...           fotogramas rotulados de la sesión 1 (exportador)
  nivel2_tracker_sesion1.csv     plantilla de la sesión 1 (exportador; la rellena el operador)
  sesion2/s2_0000.png ...        fotogramas de la sesión 2 en orden aleatorizado (sorteo)
  sesion2/orden_sesion2.txt      correspondencia s2_XXXX.png <- mXXXX.png, semilla y fracción
  nivel2_tracker_sesion2.csv     plantilla de la sesión 2 (sorteo; la rellena el operador)
  *.trk                          proyectos de Tracker, como evidencia
```

Los PNG se llaman `m<ordinal:04d>.png` y `s2_<posicion:04d>.png` (prefijo constante y
contador consecutivo) porque así es como Tracker reconoce una secuencia de imágenes. El
índice original del vídeo va rotulado en cada imagen y en la columna `frame_idx` de la
plantilla.

Todos los comandos, con el intérprete del proyecto:

**1. Exportar serie, fotogramas y plantilla** (desde `backend/`):

```bash
cd "/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio/backend" && \
  PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/analisis/exportar_para_kinovea.py \
  --video <ruta_del_clip.mp4> \
  --salida ../validacion/datos/nivel2/<clip>/serie_sistema.csv \
  --cada-n-frames 10 --lado <izquierda|derecha> --exportar-fotogramas
```

Sin argumento, `--exportar-fotogramas` escribe en `validacion/datos/nivel2/<clip>/frames/`.
El script no sobrescribe fotogramas existentes sin `--sobrescribir-fotogramas` y **nunca**
sobrescribe una plantilla que ya tenga mediciones.

**2. Sortear la sesión 2** (tras completar la sesión 1; desde la raíz del repositorio):

```bash
~/.venvs/biomotion/bin/python validacion/analisis/sortear_sesion2.py \
  --sesion1 validacion/datos/nivel2/<clip>/nivel2_tracker_sesion1.csv
```

Semilla por defecto `20261023`, fracción `0.33` (se sortean `ceil(0.33 x n)` filas). Si se
cambia la semilla, se anota en la bitácora antes de ejecutar. No repite un sorteo
existente sin `--sobrescribir`.

**3. Analizar** (tras la sesión 2, separada al menos 48 h; desde la raíz del repositorio):

```bash
~/.venvs/biomotion/bin/python validacion/analisis/analizar_nivel2.py \
  --sistema validacion/datos/nivel2/<clip>/serie_sistema.csv \
  --sesion1 validacion/datos/nivel2/<clip>/nivel2_tracker_sesion1.csv \
  --sesion2 validacion/datos/nivel2/<clip>/nivel2_tracker_sesion2.csv \
  --convencion-tracker <interno|flexion>
```

`--convencion-tracker` es la que se observó y anotó en el primer fotograma (protocolo,
sección 2.5, paso 7). Si el criterio habilitante intra-observador no se cumple y se aplica
el remedio (a), se añaden las mediciones repetidas con
`--sesiones-extra nivel2_tracker_sesion3.csv nivel2_tracker_sesion4.csv`. Las salidas van a
`validacion/resultados/` (`nivel2_acuerdo.md`, `nivel2_resumen.json`, `nivel2_pares.csv` y
las dos figuras de Bland-Altman).

## Datos personales

Los fotogramas del clip propio muestran a una persona identificable (el autor) y son dato
personal en el sentido de la Ley 1581 de 2012. Antes de versionar `frames/` y `sesion2/`
en el repositorio, decida si deben quedar fuera (por ejemplo, en `.gitignore`) y
publicarse solo las series numéricas y las plantillas.

Ver `validacion/analisis/acuerdo.py` para el detalle de los estadísticos disponibles.
