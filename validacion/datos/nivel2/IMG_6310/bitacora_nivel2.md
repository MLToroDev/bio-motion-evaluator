# Bitácora de ejecución — Nivel 2 (clip `IMG_6310.mov`)

Registro fechado de las decisiones y verificaciones de la ejecución del Nivel 2 del
protocolo [`docs/guias/protocolo_validacion_exactitud.md`](../../../../docs/guias/protocolo_validacion_exactitud.md).
Cada entrada se escribe **en el momento** en que ocurre. Las decisiones de muestreo se
tomaron antes de cualquier medición manual.

---

## 2026-10-23 — Cambio de comparador

- El comparador manual pasa de **Kinovea** a **Tracker** (Open Source Physics). Kinovea solo
  funciona de forma nativa en Windows y el autor trabaja en macOS.
- Los criterios de aceptación pre-registrados del Nivel 2 **no cambian** (MAE intra-observador
  <= 3,0 grados como criterio habilitante; MAE sistema-Tracker <= 7,0 grados; ICC(2,1) >= 0,85).

## 2026-10-23 — Material de vídeo

`tests/assets/videos/SentadillaProfunda.mp4` se descarta para exactitud (montaje de varias
tomas, mayoritariamente en plano frontal; ver protocolo §2.2). Se graba un clip propio:

| Propiedad | Valor |
|-----------|-------|
| Archivo | `IMG_6310.mov` (fuera del repositorio; huella SHA-256 en `metadatos_exportacion.json`) |
| Códec | HEVC, HDR HLG (`arib-std-b67`), 10 bits |
| Geometría | 1920x1080 almacenado con rotación -90°; OpenCV lo decodifica derecho como **1080x1920** |
| Frecuencia | 30 fps nominales (media real 30,003 fps) |
| Duración | 118,19 s, 3546 fotogramas |
| Toma | Una sola toma continua, un solo sujeto, cámara fija |

El clip contiene tres orientaciones del sujeto respecto de la cámara, identificadas sobre una
hoja de contactos (un fotograma cada 90):

| Tramo aproximado (fotogramas) | Orientación | Uso en el Nivel 2 |
|-------------------------------|-------------|-------------------|
| ~360–1260 | De frente | No se usa |
| **~1350–2520** | **De perfil (plano sagital)** | **Material de medición** |
| ~2610–3330 | De espaldas | No se usa |

## 2026-10-23 — Pierna medida: izquierda

La pierna más cercana a la cámara es la **izquierda**. Criterio objetivo, sobre la salida de
MediaPipe Pose (modelo `pose_landmarker_full.task`) en cinco fotogramas del tramo sagital:

| Fotograma | Rodilla izq. z / visibility | Rodilla der. z / visibility |
|-----------|-----------------------------|-----------------------------|
| 1500 | -0,299 / 0,98 | 0,407 / 0,41 |
| 1620 | -0,261 / 0,95 | 0,456 / 0,14 |
| 1900 | -0,242 / 0,97 | 0,288 / 0,25 |
| 2270 | -0,229 / 0,99 | 0,493 / 0,29 |
| 2450 | -0,402 / 0,96 | 0,185 / 0,38 |

(z menor = más cerca de la cámara.)

## 2026-10-23 — Muestreo: tramo 1400–2530, paso 15 (desviación justificada del §2.3)

El §2.3 prevé paso 10 (o 5). Sobre el tramo sagital, con la flexión **estimada por el
sistema** (todavía sin ninguna medición manual), la cobertura por tramo angular de la rodilla
izquierda fue:

| Paso | n | `[0,30)` | `[30,60)` | `[60,90)` | `[90,120)` | `[120,180]` |
|------|---|----------|-----------|-----------|------------|-------------|
| 10 | 114 | 55 | 16 | 12 | 23 | 8 |
| 12 | 95 | 45 | 16 | 6 | 19 | 9 |
| 14 | 81 | 38 | 14 | 4 | 17 | 8 |
| **15** | **76** | **36** | **11** | **8** | **16** | **5** |
| 16 | 71 | 37 | 7 | 7 | 13 | 7 |
| 18 | 63 | 29 | 10 | 6 | 14 | 4 |
| 20 | 57 | 29 | 6 | 4 | 15 | 3 |

**Decisión:** paso **15** desde el fotograma **1400** hasta el **2530**: **76 muestras**, con
n >= 5 en los cinco tramos (permite reportar MAE por tramo en todo el rango). Paso 10
añadiría 38 mediciones, casi todas de pie (`[0,30)`), sin ganar potencia en los tramos
intermedios, y el esfuerzo total (76 + 26 de la sesión 2 = 102) queda en el orden del plan
original del protocolo (97).

Sesión 2: `ceil(0,33 x 76)` = **26** mediciones.

## 2026-10-23 — Exportación

Se añadieron al exportador las opciones `--desde-frame` y `--hasta-frame`. La inferencia
recorre todos los fotogramas desde el 0 para conservar el seguimiento temporal de producción;
solo se exportan las muestras del tramo.

```bash
cd backend && PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/analisis/exportar_para_kinovea.py \
  --video "../../IMG_6310.mov" --salida ../validacion/datos/nivel2/IMG_6310/serie_sistema.csv \
  --cada-n-frames 15 --desde-frame 1400 --hasta-frame 2530 --lado izquierda --exportar-fotogramas
```

| Resultado | Valor |
|-----------|-------|
| Fotogramas leídos e inferidos | 2531 |
| Fotogramas con pose (0–2530) | 2413 (95,3 %) |
| Muestras exportadas | 76, todas con pose (`pose_ok = 1`) |
| Rango de flexión estimada (izquierda) | 10° a 126,9° (máximo en el fotograma 1625) |
| Consistencia | Diferencia máxima 0,0° frente a la serie completa del clip procesada de principio a fin |

Verificación visual: `m0015.png` está derecho y lleva el rótulo `f01625`, que coincide con su
fila de la plantilla.

Protección de datos: los PNG muestran a una persona identificable (Ley 1581 de 2012) y quedan
excluidos del control de versiones (`.gitignore`: `validacion/datos/nivel2/**/*.png`). Se
versionan los CSV, los metadatos y esta bitácora.

## 2026-10-23 — Tracker: instalación y apertura de la secuencia

- Versión: **Tracker 6.3.5** según el instalador (`Tracker-6.3.5-osx-installer.app`).
  *Confirmar en `Ayuda > Acerca de Tracker` y corregir aquí si difiere.*
- Interfaz en **español**. Los nombres de menú verificados están en el protocolo §2.5.
- El operador mide sobre una copia de trabajo de la carpeta del clip en el escritorio
  (`~/Desktop/IMG_6310/`), con los mismos 76 PNG. La plantilla que se rellene allí se copia
  de vuelta al repositorio al terminar la sesión; solo se rellena una plantilla.
- Abrir la **carpeta** desde Tracker falla ("No se pudo cargar el archivo"). Abrir el
  **archivo** `frames/m0000.png` carga la secuencia completa.
- **Alineación verificada:** con el contador de Tracker en **047**, la imagen muestra el rótulo
  **`f02105`** = 1400 + 47 x 15. El número de fotograma de Tracker es el `ordinal_muestra`
  de la plantilla.
- Cegamiento: la copia de trabajo contiene `serie_sistema.csv`; el operador tiene la
  instrucción de no abrirlo durante las sesiones.

## 2026-10-23 — Convención del transportador

- En `m0000` (`f01400`, pierna casi extendida) el transportador muestra **−177,8°**: Tracker
  reporta el **ángulo interno con signo** según la orientación de los brazos. Convención para
  el análisis: **`--convencion-tracker interno`** (se toma el valor absoluto; flexión =
  180 − |θ|).
- En `m0000` se usaron: vértice en la rodilla, brazo 1 hacia la cadera y brazo 2 hacia el
  tobillo. Se usa el mismo orden en todos los fotogramas.
- La casilla **Regla** se desmarca (el círculo graduado tapa la pierna). El **Autorastreador**
  no se usa: la medición es manual.
- Cada fila de la tabla **Datos** de Tracker es un fotograma de la secuencia (`t` = ordinal x
  0,1 s; la escala temporal es arbitraria y se ignora).

## Pendiente

- [x] Convención del transportador observada en `m0000`: `interno`.
- [ ] Fecha y hora de inicio y fin de la sesión 1.
- [ ] Sorteo de la sesión 2 (semilla 20261023) y fecha de la sesión 2 (>= 48 h después).
