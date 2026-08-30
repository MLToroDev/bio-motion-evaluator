# Experimento 1 - Verificación geométrica del cálculo angular

- **Fecha de ejecución:** 2026-08-29 18:12:23
- **Función bajo prueba:** `vision.biomechanics.knee_angles_from_landmarks`
- **Python:** 3.12.13 | **NumPy:** 2.5.2
- **Barrido:** 181 ángulos verdaderos, de 0 a 180 grados en pasos de 1 grado
- **Datos:** landmarks sintéticos; el ángulo verdadero se conoce por construcción, no por medición
- **Resultado global:** TODAS LAS VERIFICACIONES PASAN

## 1. Método

Para cada pierna se fija la rodilla `K` y se elige una base ortonormal `(e1, e2)` en 3D:

```
cadera  H = K + long_femur * e1
tobillo A = K + long_tibia * (cos(theta) * e1 + sin(theta) * e2)
```

El ángulo entre `(K->H)` y `(K->A)` es exactamente `theta` por construcción, luego el ángulo
interno verdadero es `theta` y la flexión verdadera es `180 - theta`.

Las dos piernas se someten deliberadamente a condiciones numéricas distintas:

| Pierna | Rodilla | Fémur | Tibia | Plano de rotación |
| --- | --- | --- | --- | --- |
| Izquierda | origen exacto `(0, 0, 0)` | 0.4 | 0.38 | vertical, casi frontal |
| Derecha | `(0.5237, 0.6114, -0.0473)` (coordenadas de imagen normalizada) | 0.31 | 0.55 | oblicuo en 3D |

La pierna derecha, al estar desplazada del origen, somete la resta `cadera - rodilla` a la
misma cancelación de punto flotante que un landmark alejado del origen. Conviene ser preciso
sobre el alcance de esa analogía: las coordenadas usadas son **isótropas** (misma unidad en
los tres ejes), mientras que los landmarks normalizados reales de MediaPipe **no lo son**
(`x` se divide por el ancho y `y` por el alto). Este experimento reproduce, por tanto, la
magnitud y el desplazamiento de un landmark real, pero **no** su anisotropía, que es un
efecto de orden muy superior y ajeno a la aritmética (ver sección 9.1).

## 2. Exactitud del ángulo interno (V1)

| Métrica | Pierna izquierda (grados) | Pierna derecha (grados) |
| --- | --- | --- |
| Error máximo | 2.647e-13 | 6.293e-13 |
| Error medio absoluto (MAE) | 1.326e-14 | 1.894e-14 |
| RMSE | 3.584e-14 | 6.446e-14 |
| Ángulo verdadero del peor caso | 1 | 1 |

El error máximo de la pierna derecha es 2.4 veces el de la izquierda. **Este cociente es descriptivo de las dos configuraciones elegidas, no la medida de un efecto aislado**: la pierna derecha difiere de la izquierda en tres factores a la vez (posición de la rodilla, longitudes de los segmentos y orientación del plano de rotación), de modo que el experimento no permite atribuir la diferencia a ninguno de ellos en particular. Una comprobación controlada, desplazando únicamente la rodilla de la configuración izquierda, deja el error máximo inalterado en 2.647e-13 grados, lo que indica que el desplazamiento respecto del origen no es por sí solo la causa.

Errores de la flexión (complemento), por completitud:

| Métrica | Flexión izquierda (grados) | Flexión derecha (grados) |
| --- | --- | --- |
| Error máximo | 2.558e-13 | 6.253e-13 |
| Error medio absoluto (MAE) | 1.186e-14 | 1.798e-14 |
| RMSE | 3.577e-14 | 6.414e-14 |

## 3. Identidad flexión = 180 - interno (V2)

- Comparaciones realizadas: 362
- Residuo máximo: 0 (exacto) grados
- Coincidencias bit a bit: 362 / 362
- Veredicto: CUMPLE de forma exacta

## 4. Acotamiento al rango [0, 180] (V3)

- Valores evaluados: 724
- Valores fuera de rango: 0
- Veredicto: CUMPLE

## 5. Independencia de escala (V4)

Se repite el barrido completo (181 ángulos) variando las longitudes
de fémur y tibia en casi tres órdenes de magnitud (de 0.001 a 0.999):

| Configuración | Fémur | Tibia | Error máx. (grados) | MAE (grados) | RMSE (grados) |
| --- | --- | --- | --- | --- | --- |
| referencia_femur_0.40_tibia_0.38 | 0.4 | 0.38 | 2.647e-13 | 1.326e-14 | 3.584e-14 |
| femur_0.10_tibia_0.50 | 0.1 | 0.5 | 1.417e-13 | 1.048e-14 | 2.341e-14 |
| femur_0.50_tibia_0.10 | 0.5 | 0.1 | 1.137e-13 | 7.804e-15 | 1.893e-14 |
| femur_0.01_tibia_0.90 | 0.01 | 0.9 | 4.643e-13 | 1.881e-14 | 5.726e-14 |
| femur_0.90_tibia_0.01 | 0.9 | 0.01 | 2.647e-13 | 1.474e-14 | 3.917e-14 |
| femur_0.001_tibia_0.999 | 0.001 | 0.999 | 2.647e-13 | 1.498e-14 | 4.254e-14 |

- Desviación máxima entre configuraciones (mismo ángulo, distintas longitudes): 7.290e-13 grados
- Veredicto: CUMPLE (el ángulo es invariante a la escala)

## 6. Casos degenerados (V5)

| Caso | Esperado | Obtenido | Veredicto |
| --- | --- | --- | --- |
| cadera izquierda sobre la rodilla (vector nulo) | interno y flexion izquierdos NaN, derecha intacta, sin excepcion | `interno_izq=nan, flexion_izq=nan, interno_der=90.0` | OK |
| tobillo derecho sobre la rodilla (vector nulo) | interno derecho NaN, izquierda intacta, sin excepcion | `interno_der=nan, interno_izq=45.0` | OK |
| lista incompleta de 28 landmarks (falta indice 28) | None | `None` | OK |
| lista vacia | None | `None` | OK |
| femur de 1e-10 (bajo el umbral 1e-9 del modulo) | NaN por diseno defensivo (el umbral trata el vector como nulo) | `interno_izq=nan` | OK |

## 7. Independencia entre piernas (V6)

- Iteraciones: 362
- Variación de la rodilla derecha (fija en 37 grados) mientras la izquierda barre 0-180: 0 (exacto) grados
- Variación de la rodilla izquierda (fija en 118 grados) mientras la derecha barre 0-180: 0 (exacto) grados
- Error de la pierna fija frente a su valor verdadero: izquierda 1.421e-14, derecha 0 (exacto) grados
- Error máximo de la pierna variable: 6.293e-13 grados
- Veredicto: CUMPLE (no hay contaminación cruzada)

## 8. Interpretación del error residual (condicionamiento de `acos`)

El error máximo de todo el barrido es 6.293e-13 grados y **no aparece en el centro del rango sino junto a sus extremos** (peor caso en theta = 1 para la pierna derecha y theta = 1 para la izquierda, en grados). La causa está identificada: la función obtiene el coseno del ángulo y lo invierte con `acos`, cuya derivada es `1 / sin(theta)` y diverge cuando `theta` tiende a 0 o a 180 grados. Un error de redondeo de `epsilon` en el coseno se amplifica por tanto hasta aproximadamente `epsilon / sin(theta)` radianes.

Contraste del error observado con esa cota teórica (`epsilon` = 2.220e-16 en doble precisión):

| Ángulo verdadero (grados) | Error observado (grados) | Cota `epsilon / sin(theta)` (grados) |
| --- | --- | --- |
| 1 | 6.293e-13 | 7.290e-13 |
| 5 | 1.545e-13 | 1.460e-13 |
| 15 | 3.020e-14 | 4.915e-14 |
| 30 | 2.132e-14 | 2.544e-14 |
| 60 | 7.105e-15 | 1.469e-14 |
| 90 | 0 (exacto) | 1.272e-14 |
| 120 | 1.421e-14 | 1.469e-14 |
| 150 | 0 (exacto) | 2.544e-14 |
| 165 | 2.842e-14 | 4.915e-14 |
| 175 | 1.705e-13 | 1.460e-13 |
| 179 | 2.558e-13 | 7.290e-13 |

- Ángulos del barrido cuyo error es exactamente cero: 75 de 181 (incluidos 0, 90 y 180 grados, donde la construcción produce vectores exactamente colineales o exactamente ortogonales y el coseno resulta exacto).
- Error máximo dentro del rango fisiológicamente relevante de sentadilla y carrera (ángulo interno entre 20 y 160 grados): 2.842e-14 grados.
- Error a 90 grados, el punto mejor condicionado: 0 (exacto) grados.
- Ángulos que superan la cota teórica: 30 de 180 (razón máxima observado/cota = 1.81); es decir, la cota con un factor 2 acota todos los casos: el modelo de condicionamiento explica la magnitud del error observado.

### 8.1 Peor caso, sondeado directamente (V7)

Un barrido de paso 1 grado no muestrea la vecindad inmediata de 0 y 180 grados, que es donde `acos` está peor condicionado, de modo que por sí solo no puede exhibir el peor error posible. Para no sobreestimar la exactitud se colocaron ángulos verdaderos a distancias decrecientes de ambos extremos:

| Distancia al extremo (grados) | Error máximo observado (grados) |
| --- | --- |
| 0.1 | 1.995e-13 |
| 0.01 | 1.910e-11 |
| 0.001 | 7.660e-10 |
| 0.0001 | 6.375e-09 |
| 1e-05 | 4.337e-08 |
| 3e-06 | 7.832e-08 |
| 1e-06 | 2.074e-07 |
| 6e-07 | 6.000e-07 |
| 3e-07 | 3.000e-07 |
| 1e-07 | 1.000e-07 |
| 1e-08 | 1.000e-08 |

- Peor error absoluto en toda la región mal condicionada: 6.000e-07 grados (22 casos evaluados).
- Cota teórica de saturación `sqrt(2 * epsilon)`: 1.207e-06 grados. Por debajo de esa distancia al extremo el coseno ya no distingue el ángulo de 0 o de 180, y el error deja de crecer.
- Veredicto: CUMPLE, incluso el peor caso queda muy por debajo del umbral (umbral de error despreciable: 0.0001 grados).

### 8.2 Magnitud comparada

El peor error aritmético medido (6.000e-07 grados) es varios órdenes de magnitud menor que:

- la resolución angular útil de un sistema de visión (del orden de 0.1 grados);
- el error típico de la goniometría manual usada como método de referencia clínico (2-5 grados);
- la dispersión que introduce la estimación de pose, que este experimento no mide y que se cuantifica en los experimentos posteriores de la validación.

En consecuencia, la aritmética no contribuye de forma medible al error del sistema y puede excluirse del presupuesto de error.

## 9. Conclusión

**Dentro de su alcance** (ver 9.1), el cálculo angular es exacto hasta el ruido de punto flotante: error máximo 6.293e-13 grados en el barrido de 0 a 180 grados con las dos configuraciones ensayadas y 6.000e-07 grados en el peor caso numérico sondeado, frente a los 2-5 grados que la literatura atribuye a la goniometría manual. En consecuencia, **el sumando aritmético del presupuesto de error es despreciable y puede excluirse**: siempre que `knee_angles_from_landmarks` reciba coordenadas isótropas, la diferencia entre el ángulo que el sistema reporta y el ángulo real de la pose que se le entregó no procede de esta función.

### 9.1 Alcance y precondiciones (lo que este experimento NO demuestra)

1. **Verdad de terreno analítica, no medida.** El ángulo verdadero se conoce por construcción y la construcción comparte con la función bajo prueba la misma definición de *ángulo entre dos vectores en 3D*. Esto verifica que la implementación es aritméticamente correcta y respeta la convención documentada; no valida que esa convención sea la definición clínica de flexión de rodilla (p. ej. frente a una definición según planos anatómicos o recomendación ISB).
2. **Precondición de isotropía, no verificada aquí.** `knee_angles_from_landmarks` asume coordenadas con la misma unidad en los tres ejes. Los landmarks normalizados de MediaPipe no cumplen esa condición y usarlos sin corregir introduce un sesgo **geométrico** de orden 10 grados (documentado hasta ~32 grados en `docs/spec/goniometria-espacio-de-coordenadas.md`), es decir siete órdenes de magnitud por encima del error aritmético medido aquí. Ese sesgo no es error de estimación de pose ni error aritmético: es un tercer sumando, que en producción resuelve la función envolvente `vision.biomechanics.angulos_rodilla` (prefiere `world_landmarks` métricos, o corrige por relación de aspecto). **La descomposición del error solo es válida si la ruta medida en los demás experimentos pasa por `angulos_rodilla`.**
3. **Cifras de la función bajo prueba, no del sistema.** Este experimento no mide exactitud frente a un método de referencia externo ni latencia: aísla un único sumando del presupuesto de error.
4. **El error máximo del barrido es específico de las configuraciones elegidas, no una cota.** Con otras geometrías el barrido de paso 1 grado alcanza errores mayores (una comprobación con 20000 tríadas aleatorias llega a 1.0e-12 grados, y una configuración oblicua con la rodilla en el origen llega a 8.5e-07 grados en theta = 0). La cifra defendible como cota práctica es la del peor caso sondeado en V7, no la del barrido.
5. **Valores de referencia sin medir.** Los 0.1 grados de resolución útil de un sistema de visión y los 2-5 grados de la goniometría manual son cifras de literatura que este experimento no midió; deben citarse con fuente en la tesis.

## 10. Reproducibilidad

```bash
cd "<repo>/backend"
PYTHONPATH=. python ../validacion/experimentos/exp1_verificacion_geometrica.py
```

- Script: `validacion/experimentos/exp1_verificacion_geometrica.py`
- Datos crudos: `validacion/resultados/exp1_verificacion_geometrica.csv` (181 filas)
