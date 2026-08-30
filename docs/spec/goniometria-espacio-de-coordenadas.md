# Espacio de coordenadas para el cálculo goniométrico

## Meta

| Campo | Valor |
|-------|-------|
| **Estado** | Vigente |
| **Ámbito** | `backend/vision/biomechanics.py`, `backend/vision/pose_extractor.py`, `backend/vision/feature_engine.py` |
| **Tipo** | Incidencia crítica + decisión arquitectónica |
| **Fecha** | 2026-08-29 |
| **Trazabilidad** | `validacion/experimentos/exp2_sensibilidad_oblicuidad.py`, `validacion/resultados/exp2_sensibilidad_oblicuidad.md` |

---

## Resumen

El cálculo del ángulo de rodilla se realizaba sobre los **landmarks normalizados** de
MediaPipe. Esas coordenadas **no son isótropas**: `x` está dividido por el ancho de la
imagen y `y` por el alto. En vídeo 16:9 eso estira el eje vertical un factor
`W/H = 1,778` respecto del horizontal, de modo que **el ángulo medido queda deformado
aunque la cámara esté perfectamente alineada y la profundidad sea perfecta**.

Un ángulo solo es invariante en un espacio **métrico** (isótropo). Calcularlo sobre ejes
de escala distinta es un error geométrico, no una aproximación.

**Impacto medido:** error medio de **14,4°** y máximo de **31,5°** sobre
`SentadillaProfunda.mp4`; error medio de **15,5°** y máximo de **32,2°** sobre
`Running.mp4`. El error es **sistemático**, no ruido: se anula en 90° de flexión y crece
hacia los extremos del rango.

---

## Demostración

Se construye una pierna métrica con ángulo **conocido por construcción**, se proyecta a
una imagen de 1920×1080 y se calcula el ángulo en tres espacios de coordenadas:

| Flexión verdadera | Normalizado (código anterior) | Corregido por aspecto | Métrico (`world_landmarks`) |
|---|---|---|---|
| 150,0° | 162,01° (**+12,01**) | 150,00° (+0,00) | 150,00° (+0,00) |
| 120,0° | 135,75° (**+15,75**) | 120,00° (+0,00) | 120,00° (+0,00) |
| 90,0° | 90,00° (+0,00) | 90,00° (+0,00) | 90,00° (+0,00) |
| 60,0° | 44,25° (**−15,75**) | 60,00° (+0,00) | 60,00° (+0,00) |
| 30,0° | 17,99° (**−12,01**) | 30,00° (+0,00) | 30,00° (+0,00) |
| **Error absoluto medio** | **9,97°** | **0,0000°** | **0,0000°** |

El punto fijo en 90° es la firma característica del defecto: es el único ángulo en que la
deformación anisotrópica no altera la razón entre componentes.

---

## Por qué no basta con corregir la relación de aspecto

Corregir `y` por `H/W` deja las tres coordenadas en unidades homogéneas y **recupera el
ángulo verdadero de forma exacta en el caso sintético**. Sin embargo, sobre vídeo real esa
variante se aleja **28,05°** de media del ángulo calculado con `world_landmarks`, mientras
que la proyección puramente 2D (`z = 0`) se queda a **11,53°**.

La lectura es que la coordenada `z` de los **landmarks normalizados** es un estimador de
profundidad débil: MediaPipe la documenta como «de escala aproximadamente igual a la de
`x`», no como una medida métrica. Homogeneizar `x` e `y` sin poder homogeneizar una `z`
poco fiable traslada el error a la componente de profundidad.

`world_landmarks`, en cambio, es la salida **métrica** del modelo (metros, origen en el
punto medio de las caderas): es isótropa por construcción y constituye la estimación 3D
propiamente dicha.

---

## Decisión

**El cálculo goniométrico se realiza sobre `world_landmarks`.**

Razones:

1. **Corrección geométrica.** Son coordenadas métricas isótropas; el ángulo es invariante.
2. **Robustez a la oblicuidad de cámara.** El Experimento 2 muestra que, con profundidad
   correcta, la rotación de azimut es una transformación rígida y **no introduce error**;
   la condición 2D, en cambio, degrada hasta 56,8° de error medio a 90° de azimut.
3. **Disponibilidad.** Se verificó presencia de `world_landmarks` en el **100 %** de los
   fotogramas con pose detectada sobre el conjunto de referencia.

**Reparto de responsabilidades:** la **geometría** se calcula sobre `world_landmarks`; la
**calidad** (umbral de visibilidad) se sigue evaluando sobre los landmarks normalizados,
porque `world_landmarks` no expone `visibility`.

**Repliegue:** si `world_landmarks` no estuviera disponible, se calcula sobre los
landmarks normalizados **corregidos por relación de aspecto**, que es estrictamente mejor
que el comportamiento anterior. Nunca se calcula sobre coordenadas anisótropas.

---

## Consecuencias

- **Cambio de valores observables.** Los ángulos reportados cambian de forma apreciable
  (media de 74,6° a 62,4° en `SentadillaProfunda.mp4`). No es una regresión: los valores
  anteriores estaban sesgados.
- **Umbrales de la interfaz.** Los estados semánticos (bueno / advertencia / crítico) y el
  umbral de asimetría se calibraron sobre valores sesgados y **deben revisarse**.
- **Contrato WebSocket.** Cambia la semántica de `knees`, no su forma. Se documenta en
  `docs/spec/websocket-pose-stream.md`.
- **Validación pendiente.** Esta decisión corrige un error **demostrable**. No afirma que
  el resultado sea *exacto*: la exactitud de `world_landmarks` frente a un método de
  referencia externo sigue siendo objeto del Nivel 4 del protocolo de validación
  (`docs/guias/protocolo_validacion_exactitud.md`).

---

## Alcance del defecto

El mismo error afectaba a `elbow_flex_angles_from_landmarks` y a
`shoulder_width_proxy`, que operan sobre las mismas coordenadas normalizadas. Ambas se
corrigen con el mismo criterio.
