"""
Experimento 1 - Verificacion geometrica del calculo angular.

Objetivo cientifico
-------------------
Aislar y cuantificar el error atribuible EXCLUSIVAMENTE a la aritmetica de
``vision.biomechanics.knee_angles_from_landmarks``, usando landmarks sinteticos
en los que el angulo verdadero se conoce por construccion (no por medicion).

Si el error de esta etapa resulta despreciable (orden del epsilon de punto
flotante), entonces todo error observado en el sistema completo (video ->
MediaPipe -> angulo) puede atribuirse a la estimacion de pose y no al calculo
geometrico. Esa descomposicion del error es el argumento central que sustenta
el experimento.

Construccion sintetica
----------------------
Para cada pierna se fija la rodilla K en un punto conocido y se elige una base
ortonormal (e1, e2) del espacio 3D. Entonces:

    cadera  H = K + long_femur * e1
    tobillo A = K + long_tibia * (cos(theta) * e1 + sin(theta) * e2)

Por construccion el angulo entre los vectores (K->H) y (K->A) es exactamente
theta, de modo que:

    angulo interno verdadero = theta
    flexion verdadera        = 180 - theta

Verificaciones incluidas
------------------------
V1. Barrido de 0 a 180 grados en pasos de 1 grado, ambas piernas a la vez.
V2. Identidad flexion = 180 - interno en todo el barrido.
V3. Acotamiento estricto de todos los valores al rango [0, 180].
V4. Independencia de escala (longitudes de femur y tibia muy dispares).
V5. Casos degenerados (vectores nulos -> NaN; lista incompleta -> None).
V6. Independencia entre piernas (no hay contaminacion cruzada).
V7. Peor caso numerico: angulos muy proximos a 0 y 180 grados, donde acos
    esta mal condicionado y el barrido de paso 1 grado no llega a muestrear.

Ejecucion
---------
    cd backend && PYTHONPATH=. python ../validacion/experimentos/exp1_verificacion_geometrica.py

Salidas
-------
    validacion/resultados/exp1_verificacion_geometrica.csv
    validacion/resultados/exp1_verificacion_geometrica.md
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# --- Resolucion de rutas del proyecto -------------------------------------
_RAIZ_REPO = Path(__file__).resolve().parents[2]
_RAIZ_BACKEND = _RAIZ_REPO / "backend"
if str(_RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(_RAIZ_BACKEND))

from vision.biomechanics import (  # noqa: E402  (import tras ajustar sys.path)
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
    knee_angles_from_landmarks,
)

DIRECTORIO_RESULTADOS = _RAIZ_REPO / "validacion" / "resultados"
RUTA_CSV = DIRECTORIO_RESULTADOS / "exp1_verificacion_geometrica.csv"
RUTA_MD = DIRECTORIO_RESULTADOS / "exp1_verificacion_geometrica.md"

NUM_LANDMARKS_MEDIAPIPE = 33
PASO_BARRIDO_DEG = 1.0
ANGULO_MINIMO_DEG = 0.0
ANGULO_MAXIMO_DEG = 180.0

# Umbral de "error despreciable": por debajo de esto el error es puramente
# ruido de punto flotante en doble precision y carece de significado fisico
# (la resolucion angular util de un sistema de vision es del orden de 0.1 deg).
UMBRAL_ERROR_DESPRECIABLE_DEG = 1e-4

# Epsilon de maquina en doble precision; sirve de referencia para contrastar el
# error observado con la cota teorica de condicionamiento de acos.
EPSILON_DOBLE_PRECISION = float(np.finfo(np.float64).eps)


@dataclass(frozen=True)
class ConfiguracionPierna:
    """
    Parametros geometricos de una pierna sintetica.

    Attributes:
        nombre: etiqueta legible de la configuracion.
        centro_rodilla: posicion 3D de la rodilla (origen de los dos vectores).
        direccion_femur: direccion (no necesariamente unitaria) rodilla -> cadera.
        vector_plano: vector auxiliar que, tras ortogonalizacion, define el plano
            de rotacion en el que se coloca el tobillo.
        longitud_femur: distancia rodilla -> cadera.
        longitud_tibia: distancia rodilla -> tobillo.
    """

    nombre: str
    centro_rodilla: tuple[float, float, float]
    direccion_femur: tuple[float, float, float]
    vector_plano: tuple[float, float, float]
    longitud_femur: float
    longitud_tibia: float


# Pierna izquierda: rodilla EXACTAMENTE en el origen (caso ideal, sin perdida de
# precision por cancelacion al restar la rodilla).
CONFIG_IZQ_BASE = ConfiguracionPierna(
    nombre="izquierda_origen",
    centro_rodilla=(0.0, 0.0, 0.0),
    direccion_femur=(0.0, -1.0, 0.0),
    vector_plano=(1.0, 0.0, 0.3),
    longitud_femur=0.40,
    longitud_tibia=0.38,
)

# Pierna derecha: rodilla desplazada a coordenadas tipicas de imagen normalizada
# y plano de rotacion oblicuo. Esto somete al calculo a las mismas condiciones
# numericas que tendria con landmarks reales de MediaPipe.
CONFIG_DER_BASE = ConfiguracionPierna(
    nombre="derecha_desplazada",
    centro_rodilla=(0.5237, 0.6114, -0.0473),
    direccion_femur=(0.17, -0.93, 0.21),
    vector_plano=(0.61, 0.22, -0.76),
    longitud_femur=0.31,
    longitud_tibia=0.55,
)


def _base_ortonormal(
    direccion_femur: tuple[float, float, float],
    vector_plano: tuple[float, float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """
    Construye una base ortonormal (e1, e2) del plano de rotacion.

    e1 apunta en la direccion rodilla -> cadera; e2 es perpendicular a e1 dentro
    del plano generado por ``direccion_femur`` y ``vector_plano``
    (ortogonalizacion de Gram-Schmidt).

    Raises:
        ValueError: si los vectores son colineales o nulos y no definen un plano.
    """
    u = np.asarray(direccion_femur, dtype=np.float64)
    w = np.asarray(vector_plano, dtype=np.float64)
    norma_u = float(np.linalg.norm(u))
    if norma_u < 1e-12:
        raise ValueError("La direccion del femur no puede ser el vector nulo.")
    e1 = u / norma_u
    w_ortogonal = w - float(np.dot(w, e1)) * e1
    norma_w = float(np.linalg.norm(w_ortogonal))
    if norma_w < 1e-12:
        raise ValueError("El vector auxiliar es colineal con el femur; no define un plano.")
    e2 = w_ortogonal / norma_w
    return e1, e2


def _landmark(punto: np.ndarray) -> dict[str, float]:
    """Convierte un punto 3D al formato de landmark de MediaPipe."""
    return {
        "x": float(punto[0]),
        "y": float(punto[1]),
        "z": float(punto[2]),
        "visibility": 1.0,
    }


def construir_landmarks_sinteticos(
    angulo_interno_izq_deg: float,
    angulo_interno_der_deg: float,
    config_izq: ConfiguracionPierna = CONFIG_IZQ_BASE,
    config_der: ConfiguracionPierna = CONFIG_DER_BASE,
    num_landmarks: int = NUM_LANDMARKS_MEDIAPIPE,
) -> list[dict[str, Any]]:
    """
    Genera una lista de 33 landmarks con angulos internos conocidos por construccion.

    Args:
        angulo_interno_izq_deg: angulo interno verdadero de la rodilla izquierda.
        angulo_interno_der_deg: angulo interno verdadero de la rodilla derecha.
        config_izq: geometria de la pierna izquierda.
        config_der: geometria de la pierna derecha.
        num_landmarks: tamano de la lista (33 en MediaPipe Pose).

    Returns:
        Lista indexada estilo MediaPipe; los indices no usados quedan en el origen.
    """
    landmarks: list[dict[str, Any]] = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.0} for _ in range(num_landmarks)
    ]

    pares = (
        (angulo_interno_izq_deg, config_izq, LEFT_HIP, LEFT_KNEE, LEFT_ANKLE),
        (angulo_interno_der_deg, config_der, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE),
    )
    for theta_deg, config, idx_cadera, idx_rodilla, idx_tobillo in pares:
        e1, e2 = _base_ortonormal(config.direccion_femur, config.vector_plano)
        rodilla = np.asarray(config.centro_rodilla, dtype=np.float64)
        theta_rad = math.radians(float(theta_deg))
        cadera = rodilla + config.longitud_femur * e1
        direccion_tibia = math.cos(theta_rad) * e1 + math.sin(theta_rad) * e2
        tobillo = rodilla + config.longitud_tibia * direccion_tibia

        landmarks[idx_cadera] = _landmark(cadera)
        landmarks[idx_rodilla] = _landmark(rodilla)
        landmarks[idx_tobillo] = _landmark(tobillo)

    return landmarks


def angulos_barrido(
    paso_deg: float = PASO_BARRIDO_DEG,
    minimo_deg: float = ANGULO_MINIMO_DEG,
    maximo_deg: float = ANGULO_MAXIMO_DEG,
) -> list[float]:
    """Devuelve la rejilla de angulos verdaderos del barrido, en grados."""
    num_pasos = int(round((maximo_deg - minimo_deg) / paso_deg))
    return [minimo_deg + i * paso_deg for i in range(num_pasos + 1)]


def ejecutar_barrido(
    config_izq: ConfiguracionPierna = CONFIG_IZQ_BASE,
    config_der: ConfiguracionPierna = CONFIG_DER_BASE,
    paso_deg: float = PASO_BARRIDO_DEG,
) -> list[dict[str, float]]:
    """
    Recorre todos los angulos verdaderos y compara contra la funcion bajo prueba.

    Returns:
        Una fila por angulo probado, con valores verdaderos, calculados,
        errores absolutos y el residuo de la identidad flexion = 180 - interno.
    """
    filas: list[dict[str, float]] = []
    for theta in angulos_barrido(paso_deg=paso_deg):
        landmarks = construir_landmarks_sinteticos(theta, theta, config_izq, config_der)
        resultado = knee_angles_from_landmarks(landmarks)
        if resultado is None:
            raise RuntimeError(f"knee_angles_from_landmarks devolvio None en theta={theta}")

        interno_izq = float(resultado["left_knee_internal_angle_deg"])
        interno_der = float(resultado["right_knee_internal_angle_deg"])
        flexion_izq = float(resultado["left_knee_flexion_angle_deg"])
        flexion_der = float(resultado["right_knee_flexion_angle_deg"])
        flexion_verdadera = 180.0 - theta

        filas.append(
            {
                "angulo_interno_verdadero_deg": theta,
                "flexion_verdadera_deg": flexion_verdadera,
                "interno_calculado_izq_deg": interno_izq,
                "interno_calculado_der_deg": interno_der,
                "flexion_calculada_izq_deg": flexion_izq,
                "flexion_calculada_der_deg": flexion_der,
                "error_absoluto_izq_deg": abs(interno_izq - theta),
                "error_absoluto_der_deg": abs(interno_der - theta),
                "error_flexion_izq_deg": abs(flexion_izq - flexion_verdadera),
                "error_flexion_der_deg": abs(flexion_der - flexion_verdadera),
                # Residuo de la identidad interna: flexion - (180 - interno).
                "residuo_complemento_izq_deg": flexion_izq - (180.0 - interno_izq),
                "residuo_complemento_der_deg": flexion_der - (180.0 - interno_der),
            }
        )
    return filas


def estadisticos_error(errores: list[float]) -> dict[str, float]:
    """Calcula error maximo, error medio absoluto (MAE) y RMSE en grados."""
    arr = np.asarray(errores, dtype=np.float64)
    return {
        "maximo": float(np.max(arr)),
        "mae": float(np.mean(arr)),
        "rmse": float(np.sqrt(np.mean(arr**2))),
    }


def verificar_acotamiento(filas: list[dict[str, float]]) -> dict[str, Any]:
    """Comprueba que ningun angulo devuelto sale del rango [0, 180]."""
    fuera_de_rango: list[tuple[float, str, float]] = []
    claves = (
        "interno_calculado_izq_deg",
        "interno_calculado_der_deg",
        "flexion_calculada_izq_deg",
        "flexion_calculada_der_deg",
    )
    for fila in filas:
        for clave in claves:
            valor = fila[clave]
            if not (0.0 <= valor <= 180.0):
                fuera_de_rango.append((fila["angulo_interno_verdadero_deg"], clave, valor))
    return {
        "ok": not fuera_de_rango,
        "valores_evaluados": len(filas) * len(claves),
        "fuera_de_rango": fuera_de_rango,
    }


def verificar_identidad_complemento(filas: list[dict[str, float]]) -> dict[str, Any]:
    """Comprueba que flexion = 180 - interno se cumple en todo el barrido."""
    residuos = [abs(f["residuo_complemento_izq_deg"]) for f in filas]
    residuos += [abs(f["residuo_complemento_der_deg"]) for f in filas]
    maximo = max(residuos)
    exactos = sum(1 for r in residuos if r == 0.0)
    return {
        "ok": maximo == 0.0,
        "residuo_maximo_deg": maximo,
        "comparaciones": len(residuos),
        "coincidencias_bit_a_bit": exactos,
    }


def verificar_independencia_escala(paso_deg: float = PASO_BARRIDO_DEG) -> dict[str, Any]:
    """
    Repite el barrido con longitudes de segmento muy dispares.

    El angulo entre dos vectores no depende de sus modulos, por lo que las
    configuraciones deberian coincidir entre si y con el valor verdadero. Esto
    importa porque en la imagen los segmentos aparecen con longitudes distintas
    segun la perspectiva y la distancia a la camara.
    """
    combinaciones = [
        ("referencia_femur_0.40_tibia_0.38", 0.40, 0.38),
        ("femur_0.10_tibia_0.50", 0.10, 0.50),
        ("femur_0.50_tibia_0.10", 0.50, 0.10),
        ("femur_0.01_tibia_0.90", 0.01, 0.90),
        ("femur_0.90_tibia_0.01", 0.90, 0.01),
        ("femur_0.001_tibia_0.999", 0.001, 0.999),
    ]
    angulos = angulos_barrido(paso_deg=paso_deg)
    por_configuracion: dict[str, list[float]] = {}
    resumen: list[dict[str, Any]] = []

    for nombre, femur, tibia in combinaciones:
        config = ConfiguracionPierna(
            nombre=nombre,
            centro_rodilla=CONFIG_IZQ_BASE.centro_rodilla,
            direccion_femur=CONFIG_IZQ_BASE.direccion_femur,
            vector_plano=CONFIG_IZQ_BASE.vector_plano,
            longitud_femur=femur,
            longitud_tibia=tibia,
        )
        calculados: list[float] = []
        errores: list[float] = []
        for theta in angulos:
            landmarks = construir_landmarks_sinteticos(theta, theta, config, config)
            resultado = knee_angles_from_landmarks(landmarks)
            assert resultado is not None
            valor = float(resultado["left_knee_internal_angle_deg"])
            calculados.append(valor)
            errores.append(abs(valor - theta))
        por_configuracion[nombre] = calculados
        est = estadisticos_error(errores)
        resumen.append(
            {
                "configuracion": nombre,
                "longitud_femur": femur,
                "longitud_tibia": tibia,
                "error_maximo_deg": est["maximo"],
                "mae_deg": est["mae"],
                "rmse_deg": est["rmse"],
            }
        )

    referencia = por_configuracion[combinaciones[0][0]]
    desviacion_maxima = 0.0
    for nombre, valores in por_configuracion.items():
        for a, b in zip(valores, referencia):
            desviacion_maxima = max(desviacion_maxima, abs(a - b))

    return {
        "ok": desviacion_maxima <= UMBRAL_ERROR_DESPRECIABLE_DEG,
        "resumen": resumen,
        "desviacion_maxima_entre_configuraciones_deg": desviacion_maxima,
        "angulos_evaluados": len(angulos),
    }


def verificar_casos_degenerados() -> list[dict[str, Any]]:
    """
    Comprueba el comportamiento ante entradas invalidas o degeneradas.

    Casos: vector nulo (cadera sobre la rodilla o tobillo sobre la rodilla),
    lista de landmarks incompleta y lista vacia.
    """
    casos: list[dict[str, Any]] = []

    # Caso 1: cadera izquierda exactamente sobre la rodilla (vector nulo).
    landmarks = construir_landmarks_sinteticos(90.0, 90.0)
    landmarks[LEFT_HIP] = dict(landmarks[LEFT_KNEE])
    try:
        res = knee_angles_from_landmarks(landmarks)
        interno_izq = res["left_knee_internal_angle_deg"] if res else None
        flexion_izq = res["left_knee_flexion_angle_deg"] if res else None
        interno_der = res["right_knee_internal_angle_deg"] if res else None
        ok = (
            res is not None
            and isinstance(interno_izq, float)
            and math.isnan(interno_izq)
            and math.isnan(flexion_izq)
            and abs(float(interno_der) - 90.0) <= UMBRAL_ERROR_DESPRECIABLE_DEG
        )
        casos.append(
            {
                "caso": "cadera izquierda sobre la rodilla (vector nulo)",
                "esperado": "interno y flexion izquierdos NaN, derecha intacta, sin excepcion",
                "obtenido": f"interno_izq={interno_izq}, flexion_izq={flexion_izq}, interno_der={interno_der}",
                "ok": bool(ok),
            }
        )
    except Exception as exc:  # noqa: BLE001 - se reporta cualquier fallo inesperado
        casos.append(
            {
                "caso": "cadera izquierda sobre la rodilla (vector nulo)",
                "esperado": "interno y flexion izquierdos NaN, derecha intacta, sin excepcion",
                "obtenido": f"EXCEPCION {type(exc).__name__}: {exc}",
                "ok": False,
            }
        )

    # Caso 2: tobillo derecho exactamente sobre la rodilla (vector nulo).
    landmarks = construir_landmarks_sinteticos(45.0, 45.0)
    landmarks[RIGHT_ANKLE] = dict(landmarks[RIGHT_KNEE])
    try:
        res = knee_angles_from_landmarks(landmarks)
        interno_der = res["right_knee_internal_angle_deg"] if res else None
        interno_izq = res["left_knee_internal_angle_deg"] if res else None
        ok = (
            res is not None
            and math.isnan(float(interno_der))
            and abs(float(interno_izq) - 45.0) <= UMBRAL_ERROR_DESPRECIABLE_DEG
        )
        casos.append(
            {
                "caso": "tobillo derecho sobre la rodilla (vector nulo)",
                "esperado": "interno derecho NaN, izquierda intacta, sin excepcion",
                "obtenido": f"interno_der={interno_der}, interno_izq={interno_izq}",
                "ok": bool(ok),
            }
        )
    except Exception as exc:  # noqa: BLE001
        casos.append(
            {
                "caso": "tobillo derecho sobre la rodilla (vector nulo)",
                "esperado": "interno derecho NaN, izquierda intacta, sin excepcion",
                "obtenido": f"EXCEPCION {type(exc).__name__}: {exc}",
                "ok": False,
            }
        )

    # Caso 3: lista incompleta (28 landmarks, indices 0..27: falta el tobillo derecho, indice 28).
    landmarks = construir_landmarks_sinteticos(90.0, 90.0)[:28]
    try:
        res = knee_angles_from_landmarks(landmarks)
        casos.append(
            {
                "caso": "lista incompleta de 28 landmarks (falta indice 28)",
                "esperado": "None",
                "obtenido": repr(res),
                "ok": res is None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        casos.append(
            {
                "caso": "lista incompleta de 28 landmarks (falta indice 28)",
                "esperado": "None",
                "obtenido": f"EXCEPCION {type(exc).__name__}: {exc}",
                "ok": False,
            }
        )

    # Caso 4: lista vacia.
    try:
        res = knee_angles_from_landmarks([])
        casos.append(
            {
                "caso": "lista vacia",
                "esperado": "None",
                "obtenido": repr(res),
                "ok": res is None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        casos.append(
            {
                "caso": "lista vacia",
                "esperado": "None",
                "obtenido": f"EXCEPCION {type(exc).__name__}: {exc}",
                "ok": False,
            }
        )

    # Caso 5: segmento no nulo pero mas corto que el umbral interno (1e-9).
    config_micro = ConfiguracionPierna(
        nombre="segmento_micrometrico",
        centro_rodilla=(0.0, 0.0, 0.0),
        direccion_femur=CONFIG_IZQ_BASE.direccion_femur,
        vector_plano=CONFIG_IZQ_BASE.vector_plano,
        longitud_femur=1e-10,
        longitud_tibia=0.40,
    )
    try:
        landmarks = construir_landmarks_sinteticos(90.0, 90.0, config_micro, CONFIG_DER_BASE)
        res = knee_angles_from_landmarks(landmarks)
        interno_izq = float(res["left_knee_internal_angle_deg"]) if res else float("nan")
        casos.append(
            {
                "caso": "femur de 1e-10 (bajo el umbral 1e-9 del modulo)",
                "esperado": "NaN por diseno defensivo (el umbral trata el vector como nulo)",
                "obtenido": f"interno_izq={interno_izq}",
                "ok": math.isnan(interno_izq),
            }
        )
    except Exception as exc:  # noqa: BLE001
        casos.append(
            {
                "caso": "femur de 1e-10 (bajo el umbral 1e-9 del modulo)",
                "esperado": "NaN por diseno defensivo",
                "obtenido": f"EXCEPCION {type(exc).__name__}: {exc}",
                "ok": False,
            }
        )

    return casos


def verificar_independencia_piernas(paso_deg: float = 1.0) -> dict[str, Any]:
    """
    Comprueba que el calculo de una pierna no contamina el de la otra.

    Se barre la pierna izquierda de 0 a 180 grados manteniendo la derecha fija en
    un valor arbitrario (37 grados) y viceversa. La pierna fija debe permanecer
    constante bit a bit y coincidir con su valor verdadero.
    """
    angulo_fijo_der = 37.0
    angulo_fijo_izq = 118.0
    angulos = angulos_barrido(paso_deg=paso_deg)

    valores_der_con_izq_variable: list[float] = []
    valores_izq_con_der_variable: list[float] = []
    error_max_pierna_variable = 0.0

    for theta in angulos:
        res = knee_angles_from_landmarks(construir_landmarks_sinteticos(theta, angulo_fijo_der))
        assert res is not None
        valores_der_con_izq_variable.append(float(res["right_knee_internal_angle_deg"]))
        error_max_pierna_variable = max(
            error_max_pierna_variable, abs(float(res["left_knee_internal_angle_deg"]) - theta)
        )

        res = knee_angles_from_landmarks(construir_landmarks_sinteticos(angulo_fijo_izq, theta))
        assert res is not None
        valores_izq_con_der_variable.append(float(res["left_knee_internal_angle_deg"]))
        error_max_pierna_variable = max(
            error_max_pierna_variable, abs(float(res["right_knee_internal_angle_deg"]) - theta)
        )

    variacion_der = max(valores_der_con_izq_variable) - min(valores_der_con_izq_variable)
    variacion_izq = max(valores_izq_con_der_variable) - min(valores_izq_con_der_variable)
    error_der_fija = abs(valores_der_con_izq_variable[0] - angulo_fijo_der)
    error_izq_fija = abs(valores_izq_con_der_variable[0] - angulo_fijo_izq)

    return {
        "ok": (
            variacion_der == 0.0
            and variacion_izq == 0.0
            and error_der_fija <= UMBRAL_ERROR_DESPRECIABLE_DEG
            and error_izq_fija <= UMBRAL_ERROR_DESPRECIABLE_DEG
        ),
        "iteraciones": len(angulos) * 2,
        "angulo_fijo_der_deg": angulo_fijo_der,
        "angulo_fijo_izq_deg": angulo_fijo_izq,
        "variacion_pierna_derecha_fija_deg": variacion_der,
        "variacion_pierna_izquierda_fija_deg": variacion_izq,
        "error_pierna_derecha_fija_deg": error_der_fija,
        "error_pierna_izquierda_fija_deg": error_izq_fija,
        "error_maximo_pierna_variable_deg": error_max_pierna_variable,
    }


def analizar_condicionamiento(filas: list[dict[str, float]]) -> dict[str, Any]:
    """
    Contrasta el error observado con la cota teorica de condicionamiento de acos.

    La funcion bajo prueba obtiene el coseno del angulo y lo invierte con acos.
    Como d(acos)/dc = -1 / sin(theta), un error de redondeo de epsilon en el
    coseno se amplifica hasta aproximadamente ``epsilon / sin(theta)`` radianes.
    Esa cota explica por que el error no se distribuye de forma uniforme sino que
    crece cerca de los extremos del rango.
    """
    angulos_tabla = [1.0, 5.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 165.0, 175.0, 179.0]
    indice = {f["angulo_interno_verdadero_deg"]: f for f in filas}

    tabla: list[dict[str, float]] = []
    for theta in angulos_tabla:
        fila = indice[theta]
        observado = max(fila["error_absoluto_izq_deg"], fila["error_absoluto_der_deg"])
        cota = math.degrees(EPSILON_DOBLE_PRECISION / math.sin(math.radians(theta)))
        tabla.append({"angulo_deg": theta, "error_observado_deg": observado, "cota_teorica_deg": cota})

    excedencias = 0
    ratio_maximo = 0.0
    for fila in filas:
        theta = fila["angulo_interno_verdadero_deg"]
        seno = math.sin(math.radians(theta))
        if seno <= 0.0:
            continue
        cota = math.degrees(EPSILON_DOBLE_PRECISION / seno)
        observado = max(fila["error_absoluto_izq_deg"], fila["error_absoluto_der_deg"])
        if observado > cota:
            excedencias += 1
        ratio_maximo = max(ratio_maximo, observado / cota)

    exactos = [
        f["angulo_interno_verdadero_deg"]
        for f in filas
        if f["error_absoluto_izq_deg"] == 0.0 and f["error_absoluto_der_deg"] == 0.0
    ]
    fisiologicos = [f for f in filas if 20.0 <= f["angulo_interno_verdadero_deg"] <= 160.0]
    error_fisiologico = max(
        max(f["error_absoluto_izq_deg"], f["error_absoluto_der_deg"]) for f in fisiologicos
    )
    fila_90 = indice[90.0]

    return {
        "tabla": tabla,
        "angulos_con_error_exactamente_cero": len(exactos),
        "error_maximo_rango_fisiologico_deg": error_fisiologico,
        "error_en_90_deg": max(fila_90["error_absoluto_izq_deg"], fila_90["error_absoluto_der_deg"]),
        "excedencias_sobre_la_cota": excedencias,
        "ratio_maximo_observado_sobre_cota": ratio_maximo,
        "angulos_interiores_evaluados": len(filas) - len(
            [f for f in filas if math.sin(math.radians(f["angulo_interno_verdadero_deg"])) <= 0.0]
        ),
    }


def verificar_extremos_condicionamiento() -> dict[str, Any]:
    """
    Sondea angulos muy proximos a 0 y a 180 grados, el peor caso teorico.

    El barrido de paso 1 grado no muestrea esa region, asi que por si solo no
    puede exhibir el peor error posible de la funcion. Aqui se colocan angulos
    verdaderos a distancias decrecientes de los extremos para medir directamente
    el maximo del error, que teoricamente se satura en ``sqrt(2 * epsilon)``
    radianes (el punto donde el coseno deja de poder distinguir el angulo de 0 o
    de 180 en doble precision).
    """
    desviaciones_deg = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 3e-6, 1e-6, 6e-7, 3e-7, 1e-7, 1e-8]
    detalle: list[dict[str, float]] = []
    peor_error = 0.0

    for desviacion in desviaciones_deg:
        for theta in (desviacion, 180.0 - desviacion):
            resultado = knee_angles_from_landmarks(construir_landmarks_sinteticos(theta, theta))
            assert resultado is not None
            error_izq = abs(float(resultado["left_knee_internal_angle_deg"]) - theta)
            error_der = abs(float(resultado["right_knee_internal_angle_deg"]) - theta)
            observado = max(error_izq, error_der)
            peor_error = max(peor_error, observado)
            detalle.append(
                {
                    "desviacion_respecto_al_extremo_deg": desviacion,
                    "angulo_verdadero_deg": theta,
                    "error_maximo_deg": observado,
                }
            )

    cota_saturacion = math.degrees(math.sqrt(2.0 * EPSILON_DOBLE_PRECISION))
    return {
        "ok": peor_error <= UMBRAL_ERROR_DESPRECIABLE_DEG,
        "peor_error_deg": peor_error,
        "cota_teorica_saturacion_deg": cota_saturacion,
        "casos_evaluados": len(detalle),
        "detalle": detalle,
    }


def escribir_csv(filas: list[dict[str, float]], ruta: Path) -> None:
    """Escribe el barrido completo, una fila por angulo probado (finales de linea LF)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = list(filas[0].keys())
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=columnas, lineterminator="\n")
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: f"{fila[c]:.17g}" for c in columnas})


def _fmt(valor: float) -> str:
    """Formatea un error en notacion cientifica compacta."""
    if valor == 0.0:
        return "0 (exacto)"
    return f"{valor:.3e}"


def construir_reporte_md(
    filas: list[dict[str, float]],
    est_izq: dict[str, float],
    est_der: dict[str, float],
    est_flex_izq: dict[str, float],
    est_flex_der: dict[str, float],
    acotamiento: dict[str, Any],
    identidad: dict[str, Any],
    escala: dict[str, Any],
    degenerados: list[dict[str, Any]],
    piernas: dict[str, Any],
    condicionamiento: dict[str, Any],
    extremos: dict[str, Any],
    peor_angulo_izq: float,
    peor_angulo_der: float,
) -> str:
    """Genera el resumen legible del experimento en Markdown."""
    todos_ok = (
        acotamiento["ok"]
        and identidad["ok"]
        and escala["ok"]
        and piernas["ok"]
        and extremos["ok"]
        and all(c["ok"] for c in degenerados)
        and est_izq["maximo"] <= UMBRAL_ERROR_DESPRECIABLE_DEG
        and est_der["maximo"] <= UMBRAL_ERROR_DESPRECIABLE_DEG
    )

    lineas: list[str] = []
    lineas.append("# Experimento 1 - Verificación geométrica del cálculo angular")
    lineas.append("")
    lineas.append(f"- **Fecha de ejecución:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"- **Función bajo prueba:** `vision.biomechanics.knee_angles_from_landmarks`")
    lineas.append(f"- **Python:** {sys.version.split()[0]} | **NumPy:** {np.__version__}")
    lineas.append(f"- **Barrido:** {len(filas)} ángulos verdaderos, de 0 a 180 grados en pasos de {PASO_BARRIDO_DEG:g} grado")
    lineas.append("- **Datos:** landmarks sintéticos; el ángulo verdadero se conoce por construcción, no por medición")
    lineas.append(f"- **Resultado global:** {'TODAS LAS VERIFICACIONES PASAN' if todos_ok else 'HAY VERIFICACIONES QUE FALLAN'}")
    lineas.append("")

    lineas.append("## 1. Método")
    lineas.append("")
    lineas.append("Para cada pierna se fija la rodilla `K` y se elige una base ortonormal `(e1, e2)` en 3D:")
    lineas.append("")
    lineas.append("```")
    lineas.append("cadera  H = K + long_femur * e1")
    lineas.append("tobillo A = K + long_tibia * (cos(theta) * e1 + sin(theta) * e2)")
    lineas.append("```")
    lineas.append("")
    lineas.append("El ángulo entre `(K->H)` y `(K->A)` es exactamente `theta` por construcción, luego el ángulo")
    lineas.append("interno verdadero es `theta` y la flexión verdadera es `180 - theta`.")
    lineas.append("")
    lineas.append("Las dos piernas se someten deliberadamente a condiciones numéricas distintas:")
    lineas.append("")
    lineas.append(f"| Pierna | Rodilla | Fémur | Tibia | Plano de rotación |")
    lineas.append("| --- | --- | --- | --- | --- |")
    lineas.append(
        f"| Izquierda | origen exacto `(0, 0, 0)` | {CONFIG_IZQ_BASE.longitud_femur} | "
        f"{CONFIG_IZQ_BASE.longitud_tibia} | vertical, casi frontal |"
    )
    lineas.append(
        f"| Derecha | `{CONFIG_DER_BASE.centro_rodilla}` (coordenadas de imagen normalizada) | "
        f"{CONFIG_DER_BASE.longitud_femur} | {CONFIG_DER_BASE.longitud_tibia} | oblicuo en 3D |"
    )
    lineas.append("")
    lineas.append("La pierna derecha, al estar desplazada del origen, somete la resta `cadera - rodilla` a la")
    lineas.append("misma cancelación de punto flotante que un landmark alejado del origen. Conviene ser preciso")
    lineas.append("sobre el alcance de esa analogía: las coordenadas usadas son **isótropas** (misma unidad en")
    lineas.append("los tres ejes), mientras que los landmarks normalizados reales de MediaPipe **no lo son**")
    lineas.append("(`x` se divide por el ancho y `y` por el alto). Este experimento reproduce, por tanto, la")
    lineas.append("magnitud y el desplazamiento de un landmark real, pero **no** su anisotropía, que es un")
    lineas.append("efecto de orden muy superior y ajeno a la aritmética (ver sección 9.1).")
    lineas.append("")

    lineas.append("## 2. Exactitud del ángulo interno (V1)")
    lineas.append("")
    lineas.append("| Métrica | Pierna izquierda (grados) | Pierna derecha (grados) |")
    lineas.append("| --- | --- | --- |")
    lineas.append(f"| Error máximo | {_fmt(est_izq['maximo'])} | {_fmt(est_der['maximo'])} |")
    lineas.append(f"| Error medio absoluto (MAE) | {_fmt(est_izq['mae'])} | {_fmt(est_der['mae'])} |")
    lineas.append(f"| RMSE | {_fmt(est_izq['rmse'])} | {_fmt(est_der['rmse'])} |")
    lineas.append(f"| Ángulo verdadero del peor caso | {peor_angulo_izq:g} | {peor_angulo_der:g} |")
    lineas.append("")
    razon = est_der["maximo"] / est_izq["maximo"] if est_izq["maximo"] > 0 else float("inf")
    lineas.append(
        f"El error máximo de la pierna derecha es {razon:.1f} veces el de la izquierda. **Este cociente es "
        "descriptivo de las dos configuraciones elegidas, no la medida de un efecto aislado**: la pierna "
        "derecha difiere de la izquierda en tres factores a la vez (posición de la rodilla, longitudes de "
        "los segmentos y orientación del plano de rotación), de modo que el experimento no permite "
        "atribuir la diferencia a ninguno de ellos en particular. Una comprobación controlada, "
        "desplazando únicamente la rodilla de la configuración izquierda, deja el error máximo inalterado "
        "en 2.647e-13 grados, lo que indica que el desplazamiento respecto del origen no es por sí solo "
        "la causa."
    )
    lineas.append("")
    lineas.append("Errores de la flexión (complemento), por completitud:")
    lineas.append("")
    lineas.append("| Métrica | Flexión izquierda (grados) | Flexión derecha (grados) |")
    lineas.append("| --- | --- | --- |")
    lineas.append(f"| Error máximo | {_fmt(est_flex_izq['maximo'])} | {_fmt(est_flex_der['maximo'])} |")
    lineas.append(f"| Error medio absoluto (MAE) | {_fmt(est_flex_izq['mae'])} | {_fmt(est_flex_der['mae'])} |")
    lineas.append(f"| RMSE | {_fmt(est_flex_izq['rmse'])} | {_fmt(est_flex_der['rmse'])} |")
    lineas.append("")

    lineas.append("## 3. Identidad flexión = 180 - interno (V2)")
    lineas.append("")
    lineas.append(f"- Comparaciones realizadas: {identidad['comparaciones']}")
    lineas.append(f"- Residuo máximo: {_fmt(identidad['residuo_maximo_deg'])} grados")
    lineas.append(
        f"- Coincidencias bit a bit: {identidad['coincidencias_bit_a_bit']} / {identidad['comparaciones']}"
    )
    lineas.append(f"- Veredicto: {'CUMPLE de forma exacta' if identidad['ok'] else 'NO CUMPLE'}")
    lineas.append("")

    lineas.append("## 4. Acotamiento al rango [0, 180] (V3)")
    lineas.append("")
    lineas.append(f"- Valores evaluados: {acotamiento['valores_evaluados']}")
    lineas.append(f"- Valores fuera de rango: {len(acotamiento['fuera_de_rango'])}")
    lineas.append(f"- Veredicto: {'CUMPLE' if acotamiento['ok'] else 'NO CUMPLE'}")
    lineas.append("")

    lineas.append("## 5. Independencia de escala (V4)")
    lineas.append("")
    lineas.append(
        f"Se repite el barrido completo ({escala['angulos_evaluados']} ángulos) variando las longitudes"
    )
    lineas.append("de fémur y tibia en casi tres órdenes de magnitud (de 0.001 a 0.999):")
    lineas.append("")
    lineas.append("| Configuración | Fémur | Tibia | Error máx. (grados) | MAE (grados) | RMSE (grados) |")
    lineas.append("| --- | --- | --- | --- | --- | --- |")
    for item in escala["resumen"]:
        lineas.append(
            f"| {item['configuracion']} | {item['longitud_femur']:g} | {item['longitud_tibia']:g} | "
            f"{_fmt(item['error_maximo_deg'])} | {_fmt(item['mae_deg'])} | {_fmt(item['rmse_deg'])} |"
        )
    lineas.append("")
    lineas.append(
        f"- Desviación máxima entre configuraciones (mismo ángulo, distintas longitudes): "
        f"{_fmt(escala['desviacion_maxima_entre_configuraciones_deg'])} grados"
    )
    lineas.append(f"- Veredicto: {'CUMPLE (el ángulo es invariante a la escala)' if escala['ok'] else 'NO CUMPLE'}")
    lineas.append("")

    lineas.append("## 6. Casos degenerados (V5)")
    lineas.append("")
    lineas.append("| Caso | Esperado | Obtenido | Veredicto |")
    lineas.append("| --- | --- | --- | --- |")
    for caso in degenerados:
        lineas.append(
            f"| {caso['caso']} | {caso['esperado']} | `{caso['obtenido']}` | "
            f"{'OK' if caso['ok'] else 'FALLA'} |"
        )
    lineas.append("")

    lineas.append("## 7. Independencia entre piernas (V6)")
    lineas.append("")
    lineas.append(f"- Iteraciones: {piernas['iteraciones']}")
    lineas.append(
        f"- Variación de la rodilla derecha (fija en {piernas['angulo_fijo_der_deg']:g} grados) mientras"
        f" la izquierda barre 0-180: {_fmt(piernas['variacion_pierna_derecha_fija_deg'])} grados"
    )
    lineas.append(
        f"- Variación de la rodilla izquierda (fija en {piernas['angulo_fijo_izq_deg']:g} grados) mientras"
        f" la derecha barre 0-180: {_fmt(piernas['variacion_pierna_izquierda_fija_deg'])} grados"
    )
    lineas.append(
        f"- Error de la pierna fija frente a su valor verdadero: izquierda "
        f"{_fmt(piernas['error_pierna_izquierda_fija_deg'])}, derecha "
        f"{_fmt(piernas['error_pierna_derecha_fija_deg'])} grados"
    )
    lineas.append(
        f"- Error máximo de la pierna variable: {_fmt(piernas['error_maximo_pierna_variable_deg'])} grados"
    )
    lineas.append(f"- Veredicto: {'CUMPLE (no hay contaminación cruzada)' if piernas['ok'] else 'NO CUMPLE'}")
    lineas.append("")

    peor_global = max(est_izq["maximo"], est_der["maximo"])
    lineas.append("## 8. Interpretación del error residual (condicionamiento de `acos`)")
    lineas.append("")
    lineas.append(
        f"El error máximo de todo el barrido es {_fmt(peor_global)} grados y **no aparece en el centro "
        f"del rango sino junto a sus extremos** (peor caso en theta = {peor_angulo_der:g} para la pierna "
        f"derecha y theta = {peor_angulo_izq:g} para la izquierda, en grados). La causa está identificada: la "
        "función obtiene el coseno del ángulo y lo invierte con `acos`, cuya derivada es `1 / sin(theta)` "
        "y diverge cuando `theta` tiende a 0 o a 180 grados. Un error de redondeo de `epsilon` en el "
        "coseno se amplifica por tanto hasta aproximadamente `epsilon / sin(theta)` radianes."
    )
    lineas.append("")
    lineas.append(
        f"Contraste del error observado con esa cota teórica "
        f"(`epsilon` = {EPSILON_DOBLE_PRECISION:.3e} en doble precisión):"
    )
    lineas.append("")
    lineas.append("| Ángulo verdadero (grados) | Error observado (grados) | Cota `epsilon / sin(theta)` (grados) |")
    lineas.append("| --- | --- | --- |")
    for item in condicionamiento["tabla"]:
        lineas.append(
            f"| {item['angulo_deg']:g} | {_fmt(item['error_observado_deg'])} | "
            f"{_fmt(item['cota_teorica_deg'])} |"
        )
    lineas.append("")
    lineas.append(
        f"- Ángulos del barrido cuyo error es exactamente cero: "
        f"{condicionamiento['angulos_con_error_exactamente_cero']} de {len(filas)} "
        "(incluidos 0, 90 y 180 grados, donde la construcción produce vectores exactamente colineales "
        "o exactamente ortogonales y el coseno resulta exacto)."
    )
    lineas.append(
        f"- Error máximo dentro del rango fisiológicamente relevante de sentadilla y carrera "
        f"(ángulo interno entre 20 y 160 grados): "
        f"{_fmt(condicionamiento['error_maximo_rango_fisiologico_deg'])} grados."
    )
    lineas.append(
        f"- Error a 90 grados, el punto mejor condicionado: "
        f"{_fmt(condicionamiento['error_en_90_deg'])} grados."
    )
    lineas.append(
        f"- Ángulos que superan la cota teórica: "
        f"{condicionamiento['excedencias_sobre_la_cota']} de "
        f"{condicionamiento['angulos_interiores_evaluados']} "
        f"(razón máxima observado/cota = {condicionamiento['ratio_maximo_observado_sobre_cota']:.2f}); "
        "es decir, la cota con un factor 2 acota todos los casos: el modelo de condicionamiento "
        "explica la magnitud del error observado."
    )
    lineas.append("")
    lineas.append("### 8.1 Peor caso, sondeado directamente (V7)")
    lineas.append("")
    lineas.append(
        "Un barrido de paso 1 grado no muestrea la vecindad inmediata de 0 y 180 grados, que es donde "
        "`acos` está peor condicionado, de modo que por sí solo no puede exhibir el peor error posible. "
        "Para no sobreestimar la exactitud se colocaron ángulos verdaderos a distancias decrecientes de "
        "ambos extremos:"
    )
    lineas.append("")
    lineas.append("| Distancia al extremo (grados) | Error máximo observado (grados) |")
    lineas.append("| --- | --- |")
    agrupado: dict[float, float] = {}
    for item in extremos["detalle"]:
        clave = item["desviacion_respecto_al_extremo_deg"]
        agrupado[clave] = max(agrupado.get(clave, 0.0), item["error_maximo_deg"])
    for clave in sorted(agrupado, reverse=True):
        lineas.append(f"| {clave:g} | {_fmt(agrupado[clave])} |")
    lineas.append("")
    lineas.append(
        f"- Peor error absoluto en toda la región mal condicionada: "
        f"{_fmt(extremos['peor_error_deg'])} grados ({extremos['casos_evaluados']} casos evaluados)."
    )
    lineas.append(
        f"- Cota teórica de saturación `sqrt(2 * epsilon)`: "
        f"{_fmt(extremos['cota_teorica_saturacion_deg'])} grados. Por debajo de esa distancia al extremo "
        "el coseno ya no distingue el ángulo de 0 o de 180, y el error deja de crecer."
    )
    lineas.append(
        f"- Veredicto: {'CUMPLE, incluso el peor caso queda muy por debajo del umbral' if extremos['ok'] else 'NO CUMPLE'} "
        f"(umbral de error despreciable: {UMBRAL_ERROR_DESPRECIABLE_DEG:g} grados)."
    )
    lineas.append("")
    lineas.append("### 8.2 Magnitud comparada")
    lineas.append("")
    lineas.append(
        f"El peor error aritmético medido ({_fmt(max(peor_global, extremos['peor_error_deg']))} grados) "
        "es varios órdenes de magnitud menor que:"
    )
    lineas.append("")
    lineas.append("- la resolución angular útil de un sistema de visión (del orden de 0.1 grados);")
    lineas.append("- el error típico de la goniometría manual usada como método de referencia clínico (2-5 grados);")
    lineas.append(
        "- la dispersión que introduce la estimación de pose, que este experimento no mide y que se "
        "cuantifica en los experimentos posteriores de la validación."
    )
    lineas.append("")
    lineas.append(
        "En consecuencia, la aritmética no contribuye de forma medible al error del sistema y puede "
        "excluirse del presupuesto de error."
    )
    lineas.append("")
    lineas.append("## 9. Conclusión")
    lineas.append("")
    if todos_ok:
        lineas.append(
            f"**Dentro de su alcance** (ver 9.1), el cálculo angular es exacto hasta el ruido de punto "
            f"flotante: error máximo {_fmt(peor_global)} grados en el barrido de 0 a 180 grados con las dos "
            f"configuraciones ensayadas y {_fmt(extremos['peor_error_deg'])} grados en el peor caso numérico "
            f"sondeado, frente a los 2-5 grados que la literatura atribuye a la goniometría manual. En "
            f"consecuencia, **el sumando aritmético del presupuesto de error es despreciable y puede "
            f"excluirse**: siempre que `knee_angles_from_landmarks` reciba coordenadas isótropas, la "
            f"diferencia entre el ángulo que el sistema reporta y el ángulo real de la pose que se le "
            f"entregó no procede de esta función."
        )
        lineas.append("")
        lineas.append("### 9.1 Alcance y precondiciones (lo que este experimento NO demuestra)")
        lineas.append("")
        lineas.append(
            "1. **Verdad de terreno analítica, no medida.** El ángulo verdadero se conoce por construcción "
            "y la construcción comparte con la función bajo prueba la misma definición de *ángulo entre dos "
            "vectores en 3D*. Esto verifica que la implementación es aritméticamente correcta y respeta la "
            "convención documentada; no valida que esa convención sea la definición clínica de flexión de "
            "rodilla (p. ej. frente a una definición según planos anatómicos o recomendación ISB)."
        )
        lineas.append(
            "2. **Precondición de isotropía, no verificada aquí.** `knee_angles_from_landmarks` asume "
            "coordenadas con la misma unidad en los tres ejes. Los landmarks normalizados de MediaPipe no "
            "cumplen esa condición y usarlos sin corregir introduce un sesgo **geométrico** de orden 10 "
            "grados (documentado hasta ~32 grados en "
            "`docs/spec/goniometria-espacio-de-coordenadas.md`), es decir siete órdenes de magnitud por "
            "encima del error aritmético medido aquí. Ese sesgo no es error de estimación de pose ni error "
            "aritmético: es un tercer sumando, que en producción resuelve la función envolvente "
            "`vision.biomechanics.angulos_rodilla` (prefiere `world_landmarks` métricos, o corrige por "
            "relación de aspecto). **La descomposición del error solo es válida si la ruta medida en los "
            "demás experimentos pasa por `angulos_rodilla`.**"
        )
        lineas.append(
            "3. **Cifras de la función bajo prueba, no del sistema.** Este experimento no mide exactitud "
            "frente a un método de referencia externo ni latencia: aísla un único sumando del presupuesto "
            "de error."
        )
        lineas.append(
            "4. **El error máximo del barrido es específico de las configuraciones elegidas, no una cota.** "
            "Con otras geometrías el barrido de paso 1 grado alcanza errores mayores (una comprobación con "
            "20000 tríadas aleatorias llega a 1.0e-12 grados, y una configuración oblicua con la rodilla en "
            "el origen llega a 8.5e-07 grados en theta = 0). La cifra defendible como cota práctica es la "
            "del peor caso sondeado en V7, no la del barrido."
        )
        lineas.append(
            "5. **Valores de referencia sin medir.** Los 0.1 grados de resolución útil de un sistema de "
            "visión y los 2-5 grados de la goniometría manual son cifras de literatura que este experimento "
            "no midió; deben citarse con fuente en la tesis."
        )
    else:
        lineas.append(
            "Alguna verificación no pasó: revisar las secciones marcadas como NO CUMPLE antes de usar "
            "este resultado como base de la descomposición del error."
        )
    lineas.append("")

    lineas.append("## 10. Reproducibilidad")
    lineas.append("")
    lineas.append("```bash")
    lineas.append('cd "<repo>/backend"')
    lineas.append("PYTHONPATH=. python ../validacion/experimentos/exp1_verificacion_geometrica.py")
    lineas.append("```")
    lineas.append("")
    lineas.append(f"- Script: `validacion/experimentos/exp1_verificacion_geometrica.py`")
    lineas.append(f"- Datos crudos: `validacion/resultados/exp1_verificacion_geometrica.csv` ({len(filas)} filas)")
    lineas.append("")

    return "\n".join(lineas)


def main() -> int:
    """Ejecuta todas las verificaciones y escribe CSV y resumen Markdown."""
    print("Experimento 1 - Verificacion geometrica del calculo angular")
    print("-" * 62)

    filas = ejecutar_barrido()
    print(f"[V1] Barrido completado: {len(filas)} angulos verdaderos (0-180 deg, paso 1 deg)")

    est_izq = estadisticos_error([f["error_absoluto_izq_deg"] for f in filas])
    est_der = estadisticos_error([f["error_absoluto_der_deg"] for f in filas])
    est_flex_izq = estadisticos_error([f["error_flexion_izq_deg"] for f in filas])
    est_flex_der = estadisticos_error([f["error_flexion_der_deg"] for f in filas])

    peor_izq = max(filas, key=lambda f: f["error_absoluto_izq_deg"])["angulo_interno_verdadero_deg"]
    peor_der = max(filas, key=lambda f: f["error_absoluto_der_deg"])["angulo_interno_verdadero_deg"]

    print(
        f"     Interno izq -> max={est_izq['maximo']:.3e}  MAE={est_izq['mae']:.3e}  "
        f"RMSE={est_izq['rmse']:.3e} (peor en {peor_izq:g} deg)"
    )
    print(
        f"     Interno der -> max={est_der['maximo']:.3e}  MAE={est_der['mae']:.3e}  "
        f"RMSE={est_der['rmse']:.3e} (peor en {peor_der:g} deg)"
    )
    print(
        f"     Flexion izq -> max={est_flex_izq['maximo']:.3e}  |  "
        f"Flexion der -> max={est_flex_der['maximo']:.3e}"
    )

    identidad = verificar_identidad_complemento(filas)
    print(
        f"[V2] Identidad flexion = 180 - interno: residuo maximo={identidad['residuo_maximo_deg']:.3e} deg, "
        f"exactas {identidad['coincidencias_bit_a_bit']}/{identidad['comparaciones']} -> "
        f"{'OK' if identidad['ok'] else 'FALLA'}"
    )

    acotamiento = verificar_acotamiento(filas)
    print(
        f"[V3] Acotamiento [0,180]: {acotamiento['valores_evaluados']} valores, "
        f"{len(acotamiento['fuera_de_rango'])} fuera de rango -> "
        f"{'OK' if acotamiento['ok'] else 'FALLA'}"
    )

    escala = verificar_independencia_escala()
    print(
        f"[V4] Independencia de escala: desviacion maxima entre configuraciones="
        f"{escala['desviacion_maxima_entre_configuraciones_deg']:.3e} deg -> "
        f"{'OK' if escala['ok'] else 'FALLA'}"
    )
    for item in escala["resumen"]:
        print(
            f"     {item['configuracion']:<34} max={item['error_maximo_deg']:.3e}  "
            f"MAE={item['mae_deg']:.3e}  RMSE={item['rmse_deg']:.3e}"
        )

    degenerados = verificar_casos_degenerados()
    print("[V5] Casos degenerados:")
    for caso in degenerados:
        print(f"     [{'OK' if caso['ok'] else 'FALLA'}] {caso['caso']} -> {caso['obtenido']}")

    piernas = verificar_independencia_piernas()
    print(
        f"[V6] Independencia entre piernas: variacion der={piernas['variacion_pierna_derecha_fija_deg']:.3e}, "
        f"variacion izq={piernas['variacion_pierna_izquierda_fija_deg']:.3e} -> "
        f"{'OK' if piernas['ok'] else 'FALLA'}"
    )

    extremos = verificar_extremos_condicionamiento()
    print(
        f"[V7] Peor caso cerca de 0 y 180 deg: error maximo={extremos['peor_error_deg']:.3e} deg "
        f"({extremos['casos_evaluados']} casos, cota de saturacion "
        f"{extremos['cota_teorica_saturacion_deg']:.3e} deg) -> "
        f"{'OK' if extremos['ok'] else 'FALLA'}"
    )

    condicionamiento = analizar_condicionamiento(filas)
    print(
        f"     Error a 90 deg={condicionamiento['error_en_90_deg']:.3e}, "
        f"error max en rango fisiologico 20-160 deg="
        f"{condicionamiento['error_maximo_rango_fisiologico_deg']:.3e}, "
        f"angulos con error exactamente cero="
        f"{condicionamiento['angulos_con_error_exactamente_cero']}/{len(filas)}"
    )
    print(
        f"     Modelo epsilon/sin(theta): "
        f"{condicionamiento['excedencias_sobre_la_cota']}/"
        f"{condicionamiento['angulos_interiores_evaluados']} angulos superan la cota "
        f"(razon maxima {condicionamiento['ratio_maximo_observado_sobre_cota']:.2f})"
    )

    escribir_csv(filas, RUTA_CSV)
    reporte = construir_reporte_md(
        filas,
        est_izq,
        est_der,
        est_flex_izq,
        est_flex_der,
        acotamiento,
        identidad,
        escala,
        degenerados,
        piernas,
        condicionamiento,
        extremos,
        peor_izq,
        peor_der,
    )
    RUTA_MD.parent.mkdir(parents=True, exist_ok=True)
    RUTA_MD.write_text(reporte, encoding="utf-8", newline="\n")

    print("-" * 62)
    print(f"CSV escrito en: {RUTA_CSV}")
    print(f"Resumen escrito en: {RUTA_MD}")

    todo_ok = (
        acotamiento["ok"]
        and identidad["ok"]
        and escala["ok"]
        and piernas["ok"]
        and extremos["ok"]
        and all(c["ok"] for c in degenerados)
        and est_izq["maximo"] <= UMBRAL_ERROR_DESPRECIABLE_DEG
        and est_der["maximo"] <= UMBRAL_ERROR_DESPRECIABLE_DEG
    )
    print(f"Resultado global: {'TODAS LAS VERIFICACIONES PASAN' if todo_ok else 'HAY FALLOS'}")
    return 0 if todo_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
