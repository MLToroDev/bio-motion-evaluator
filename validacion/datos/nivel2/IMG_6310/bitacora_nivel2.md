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

## 2026-10-23 — Sesión 1, primera pasada (incompleta)

- Proyecto guardado por el operador: `~/Desktop/IMG_6310/sesion1.trz` a las
  2026-10-23T18:52:25-0500 (Tracker lo empaqueta como `.trz`: un `.trk` más las imágenes).
- Formato verificado de `framedata` del transportador en el `.trk`: por fotograma
  `{x_tobillo, y_tobillo, x_cadera, y_cadera, x_rodilla, y_rodilla}` en píxeles de imagen; el
  ángulo recalculado en el vértice (tercer par) coincide con la tabla **Datos** de Tracker
  (p. ej. −178,5° en 0, 101,2° en 4, 59,9° en 6, 170,4° en 8).
- Una entrada `null` significa que en ese fotograma **no se movió el transportador** y Tracker
  muestra el valor del fotograma anterior (comprobado: el fotograma 75 es `null` y Tracker
  muestra −178,9°, el valor del 74). Esos fotogramas no son mediciones propias.
- **19 de 76 fotogramas sin medición propia:** 1, 2, 9, 10, 11, 12, 26, 39, 46, 49, 52, 53,
  54, 55, 56, 62, 69, 72, 75. Se vuelven a medir antes de cerrar la sesión 1.
- El punto del tobillo se mantuvo en la misma posición en la mayoría de fotogramas: es
  coherente con el ejercicio (el pie no se desplaza en la sentadilla).
- `confianza_operador` aún sin registrar.

## 2026-10-23 — Cierre de la sesión 1

- El operador volvió a medir los fotogramas sin medición propia y guardó el proyecto a las
  **2026-10-23T19:05:47-05:00** (`~/Desktop/IMG_6310/sesion1 2.trz`). Queda **1 fotograma sin
  medición propia: ordinal 2** (`f01430`, de pie). El operador decidió no medirlo.
- Ningún fotograma repite exactamente las coordenadas del anterior.
- Evidencia en el repositorio: `sesion1.trk` (coordenadas de los tres puntos por fotograma,
  versionado) y `sesion1.trz` (proyecto con imágenes, excluido de git por Ley 1581).
- `nivel2_tracker_sesion1.csv` rellenado desde el `.trk`: `tracker_angulo_deg` = ángulo en el
  vértice con el signo y el redondeo a 0,1° que muestra Tracker (verificado contra la tabla
  **Datos** en los fotogramas 0, 4, 6, 7, 8 y 74). El ordinal 2 queda **vacío** con su
  observación: el valor que Tracker muestra ahí es el del fotograma anterior y no es una
  medición. Resultado: **75 de 76** mediciones; el análisis descarta y lista el ordinal 2.
- `fecha_medicion` = hora de cierre de la sesión (no hay hora por fotograma).

## 2026-10-23 — Sorteo de la sesión 2

- `sortear_sesion2.py`, semilla por defecto **20261023**, fracción 0,33: **26** fotogramas,
  en orden aleatorizado en `sesion2/s2_0000.png`… (`orden_sesion2.txt`). Copiados también a
  la copia de trabajo `~/Desktop/IMG_6310/sesion2/`.
- El sorteo **incluye el ordinal 2**, que no tiene valor en la sesión 1. No se repite el sorteo
  (estaba pre-especificado). Se mide igualmente en la sesión 2; el acuerdo intra-observador
  se calcula sobre los **25** pares completos.
- Fecha mínima de la sesión 2: **2026-10-25T19:06-05:00** (48 h después del cierre de la
  sesión 1).

## Pendiente

- [x] Convención del transportador observada en `m0000`: `interno`.
- [x] Cierre de la sesión 1 (75 de 76 mediciones).
- [x] Sorteo de la sesión 2.
- [x] `confianza_operador` de la sesión 1: **no anotada** por decisión del operador
  (2026-10-23). El análisis la reporta como "sin anotar" y no se estratifica el error por
  calidad de la medición; se declara como limitación.
- [ ] Sesión 2 (desde 2026-10-25T19:06-05:00). Durante la sesión 2 no se abren
  `sesion1 2.trz`, `sesion1.trk`, `nivel2_tracker_sesion1.csv` ni `serie_sistema.csv`.
