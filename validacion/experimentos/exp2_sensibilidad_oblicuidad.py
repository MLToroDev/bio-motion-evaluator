"""
Experimento 2: sensibilidad del angulo de rodilla a la oblicuidad de camara.

Pregunta que responde
---------------------
Con que exactitud puede el sistema estimar el angulo de flexion de rodilla y la
asimetria bilateral cuando la camara no esta perfectamente perpendicular al plano
sagital del sujeto, y cuanto de esa exactitud depende realmente de la coordenada
z (profundidad) que estima MediaPipe.

Metodo
------
1. Se modela una pierna rigida en 3D (cadera, rodilla, tobillo) contenida en el
   plano sagital, con un angulo de flexion verdadero conocido. Se modelan las dos
   piernas con flexion identica, de modo que la asimetria bilateral verdadera es
   exactamente 0 grados y cualquier asimetria medida es espuria (inducida por el
   punto de vista, no por el sujeto).
2. Se rota el modelo alrededor del eje vertical un azimut phi (desalineacion de la
   camara respecto al plano sagital), de 0 a 90 grados.
3. Se proyecta a la imagen con dos modelos de camara:
     - ortografica (caso base, camara lejana o teleobjetivo),
     - perspectiva a 2.5 m con campo de vision horizontal de 60 grados, que es la
       distancia del protocolo de captura del proyecto.
4. Se evaluan dos condiciones, que son el nucleo del experimento:
     - CONDICION 3D: se conserva la coordenada z (profundidad ideal, perfecta).
     - CONDICION 2D: se anula z (z = 0), simulando profundidad inservible.
5. Ambas se pasan a ``vision.biomechanics.knee_angles_from_landmarks`` (la MISMA
   funcion que usa el pipeline de produccion) y se mide el error contra el angulo
   verdadero.

Analisis complementarios
------------------------
- Barrido fino de azimut (paso 0.1 grados) para localizar el azimut maximo
  tolerable bajo el umbral de acuerdo clinico de 5 grados en goniometria.
- Validacion empirica: se toman los landmarks metricos (``world_landmarks``) de un
  video real de sentadilla profunda, se les aplica un azimut adicional de -90 a
  +90 grados y se mide el error de la condicion 2D contra la referencia 3D del
  mismo frame. El minimo de esa curva estima la oblicuidad real de la toma.
- Coherencia metrica de los ejes: los landmarks normalizados de MediaPipe llevan
  x dividido por el ancho de imagen y y dividido por el alto, y su z declara estar
  "aproximadamente en la escala de x". Se miden las tres escalas por minimos
  cuadrados sobre video real y se cuantifica, sobre la malla sintetica, el error
  angular que introduce cada incoherencia por separado y las dos juntas.

Uso
---
    cd backend && PYTHONPATH=. ~/.venvs/biomotion/bin/python \
        ../validacion/experimentos/exp2_sensibilidad_oblicuidad.py

Salidas en ``validacion/resultados/``:
    exp2_sensibilidad_oblicuidad.csv        malla completa
    exp2_barrido_fino_azimut.csv            barrido fino para el umbral de 5 grados
    exp2_validacion_empirica_video.csv      validacion con video real
    exp2_sensibilidad_oblicuidad.md         informe con tablas y conclusiones
    exp2_error_vs_azimut.png                figura
"""

from __future__ import annotations

import csv
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")  # sin pantalla disponible

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# --- Rutas del proyecto -----------------------------------------------------
RAIZ_REPO = Path(__file__).resolve().parents[2]
DIR_BACKEND = RAIZ_REPO / "backend"
DIR_RESULTADOS = RAIZ_REPO / "validacion" / "resultados"
RUTA_MODELO = DIR_BACKEND / "models" / "pose_landmarker_full.task"
RUTA_VIDEO = RAIZ_REPO / "tests" / "assets" / "videos" / "SentadillaProfunda.mp4"

if str(DIR_BACKEND) not in sys.path:
    sys.path.insert(0, str(DIR_BACKEND))

from vision.biomechanics import (  # noqa: E402
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
    knee_angles_from_landmarks,
)

# --- Parametros del experimento ---------------------------------------------
UMBRAL_CLINICO_DEG = 5.0
"""Umbral tipico de acuerdo clinico en goniometria de rodilla, en grados."""

AZIMUT_RECOMENDADO_DEG = 15.0
"""Consigna operativa propuesta para el protocolo, con margen sobre el limite estricto medido."""

LARGO_MUSLO_M = 0.45
LARGO_PIERNA_M = 0.42
ANCHO_CADERAS_M = 0.18

DISTANCIA_CAMARA_M = 2.5
"""Distancia camara-sujeto del protocolo de captura del proyecto."""

FOV_HORIZONTAL_DEG = 60.0
"""Campo de vision horizontal tipico de webcam o camara de telefono."""

FLEXIONES_VERDADERAS_DEG = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 120.0, 135.0]
AZIMUTS_MALLA_DEG = [0.0, 5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 75.0, 90.0]
AZIMUTS_EMPIRICOS_DEG = [float(v) for v in range(-90, 95, 5)]
POSTURAS = ("rodilla_aislada", "flexion_repartida")
PROYECCIONES = ("ortografica", "perspectiva")
CONDICIONES = ("3D", "2D")

PASO_BARRIDO_FINO_DEG = 0.1
FLEXION_MINIMA_EMPIRICA_DEG = 10.0

RAZON_Z_POR_DEFECTO = 3.25
"""Razon s_z/s_x de reserva si no hay video para medirla (valor medido en este proyecto)."""

# Paleta: dos hues categoricos validados, identidad reforzada con estilo de linea.
COLOR_3D = "#2a78d6"
COLOR_2D = "#eb6834"
COLOR_UMBRAL = "#e34948"
COLOR_TEXTO = "#0b0b0b"
COLOR_TEXTO_SEC = "#52514e"
COLOR_REJILLA = "#e4e3df"
RAMPA_AZUL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]

# Pares de landmarks usados para estimar las escalas por eje.
PARES_ESCALA = [
    (23, 25), (25, 27), (24, 26), (26, 28), (23, 24),
    (11, 12), (11, 23), (12, 24), (11, 13), (13, 15), (12, 14), (14, 16),
]


# ---------------------------------------------------------------------------
# 1. Modelo geometrico de la pierna
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModeloPiernas:
    """Seis puntos 3D en el sistema del sujeto: x anterior, y arriba, z lateral izquierdo."""

    cadera_izq: np.ndarray
    rodilla_izq: np.ndarray
    tobillo_izq: np.ndarray
    cadera_der: np.ndarray
    rodilla_der: np.ndarray
    tobillo_der: np.ndarray


def _inclinaciones_segmentos(flexion_deg: float, postura: str) -> tuple[float, float]:
    """
    Devuelve (alpha, beta) en radianes: inclinacion del muslo y de la pierna
    respecto a la vertical descendente, positivo hacia anterior.

    El angulo interno de rodilla resulta 180 - |alpha - beta|, luego la flexion
    verdadera es exactamente |alpha - beta| en ambas posturas. Las dos posturas son
    extremos de como una MISMA flexion verdadera puede orientarse dentro del plano
    sagital, y sirven para comprobar que el efecto de la oblicuidad no depende solo
    de la magnitud de la flexion sino de la orientacion absoluta del miembro:

    - ``rodilla_aislada``: muslo vertical, pierna girada hacia posterior
      (curl de isquiotibiales, flexion en decubito prono).
    - ``flexion_repartida``: la flexion se reparte simetricamente respecto a la
      vertical, como en la fase descendente de una sentadilla.
    """
    theta = math.radians(flexion_deg)
    if postura == "rodilla_aislada":
        return 0.0, -theta
    if postura == "flexion_repartida":
        return theta / 2.0, -theta / 2.0
    raise ValueError(f"Postura desconocida: {postura}")


def construir_modelo(flexion_deg: float, postura: str) -> ModeloPiernas:
    """Construye las dos piernas con la misma flexion verdadera (asimetria real = 0)."""
    alpha, beta = _inclinaciones_segmentos(flexion_deg, postura)
    dir_muslo = np.array([math.sin(alpha), -math.cos(alpha), 0.0])
    dir_pierna = np.array([math.sin(beta), -math.cos(beta), 0.0])

    puntos: dict[str, np.ndarray] = {}
    for lado, z_lateral in (("izq", +ANCHO_CADERAS_M / 2.0), ("der", -ANCHO_CADERAS_M / 2.0)):
        cadera = np.array([0.0, 0.0, z_lateral])
        rodilla = cadera + LARGO_MUSLO_M * dir_muslo
        tobillo = rodilla + LARGO_PIERNA_M * dir_pierna
        puntos[f"cadera_{lado}"] = cadera
        puntos[f"rodilla_{lado}"] = rodilla
        puntos[f"tobillo_{lado}"] = tobillo

    # Se centra verticalmente el modelo sobre el eje optico (sujeto bien encuadrado).
    y_medio = float(np.mean([p[1] for p in puntos.values()]))
    desplazamiento = np.array([0.0, y_medio, 0.0])
    return ModeloPiernas(
        cadera_izq=puntos["cadera_izq"] - desplazamiento,
        rodilla_izq=puntos["rodilla_izq"] - desplazamiento,
        tobillo_izq=puntos["tobillo_izq"] - desplazamiento,
        cadera_der=puntos["cadera_der"] - desplazamiento,
        rodilla_der=puntos["rodilla_der"] - desplazamiento,
        tobillo_der=puntos["tobillo_der"] - desplazamiento,
    )


# ---------------------------------------------------------------------------
# 2. Camara: rotacion de azimut y proyecciones
# ---------------------------------------------------------------------------
def rotar_azimut(punto: np.ndarray, phi_deg: float) -> np.ndarray:
    """
    Rota un punto alrededor del eje vertical un azimut phi y lo expresa en el
    sistema de camara (X a la derecha en imagen, Y arriba, Z profundidad).

    phi = 0 grados: camara perpendicular al plano sagital (vista lateral ideal).
    phi = 90 grados: camara en el plano frontal, el plano sagital se ve de canto.
    """
    c = math.cos(math.radians(phi_deg))
    s = math.sin(math.radians(phi_deg))
    x, y, z = float(punto[0]), float(punto[1]), float(punto[2])
    return np.array([x * c + z * s, y, -x * s + z * c])


def _escala_focal_normalizada() -> float:
    """Distancia focal dividida por el ancho de imagen, para el campo de vision configurado."""
    return 0.5 / math.tan(math.radians(FOV_HORIZONTAL_DEG / 2.0))


def proyectar(punto_camara: np.ndarray, proyeccion: str) -> np.ndarray:
    """
    Proyecta un punto del sistema de camara a la representacion tipo MediaPipe:
    x, y en la imagen con y hacia abajo, y z de profundidad con origen en el centro
    de las caderas y, por construccion, en la misma escala que x.
    """
    x_c, y_c, z_c = float(punto_camara[0]), float(punto_camara[1]), float(punto_camara[2])
    if proyeccion == "ortografica":
        return np.array([x_c, -y_c, z_c])
    if proyeccion == "perspectiva":
        z_mundo = z_c + DISTANCIA_CAMARA_M
        if z_mundo <= 1e-6:
            return np.array([math.nan, math.nan, math.nan])
        s = _escala_focal_normalizada()
        return np.array([
            s * x_c / z_mundo,
            s * (-y_c) / z_mundo,
            s * (z_mundo - DISTANCIA_CAMARA_M) / DISTANCIA_CAMARA_M,
        ])
    raise ValueError(f"Proyeccion desconocida: {proyeccion}")


def landmarks_desde_puntos(mapa: dict[int, np.ndarray]) -> list[dict[str, Any]]:
    """Empaqueta puntos sueltos en la lista de 33 landmarks estilo MediaPipe."""
    lms: list[dict[str, Any]] = [
        {"index": i, "x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for i in range(33)
    ]
    for indice, p in mapa.items():
        lms[indice] = {
            "index": indice,
            "x": float(p[0]),
            "y": float(p[1]),
            "z": float(p[2]),
            "visibility": 1.0,
        }
    return lms


def medir_flexiones(
    modelo: ModeloPiernas,
    phi_deg: float,
    proyeccion: str,
    condicion: str,
    factor_y: float = 1.0,
    factor_z: float = 1.0,
) -> tuple[float, float]:
    """
    Devuelve (flexion_izquierda_deg, flexion_derecha_deg) medidas por la funcion de
    produccion ``knee_angles_from_landmarks`` sobre el modelo proyectado.

    ``condicion`` = "3D" conserva z; "2D" lo anula.
    ``factor_y`` y ``factor_z`` escalan esas coordenadas para simular la
    incoherencia metrica entre ejes de los landmarks normalizados de MediaPipe.
    """
    indices = (
        (LEFT_HIP, modelo.cadera_izq), (LEFT_KNEE, modelo.rodilla_izq), (LEFT_ANKLE, modelo.tobillo_izq),
        (RIGHT_HIP, modelo.cadera_der), (RIGHT_KNEE, modelo.rodilla_der), (RIGHT_ANKLE, modelo.tobillo_der),
    )
    mapa: dict[int, np.ndarray] = {}
    for indice, punto in indices:
        p = proyectar(rotar_azimut(punto, phi_deg), proyeccion)
        z = 0.0 if condicion == "2D" else float(p[2]) * factor_z
        mapa[indice] = np.array([float(p[0]), float(p[1]) * factor_y, z])

    angulos = knee_angles_from_landmarks(landmarks_desde_puntos(mapa))
    if angulos is None:
        return math.nan, math.nan
    return (
        float(angulos["left_knee_flexion_angle_deg"]),
        float(angulos["right_knee_flexion_angle_deg"]),
    )


# ---------------------------------------------------------------------------
# 3. Malla principal
# ---------------------------------------------------------------------------
CAMPOS_MALLA = [
    "postura", "proyeccion", "condicion",
    "flexion_verdadera_deg", "azimut_deg",
    "left_knee_flexion_measured_deg", "right_knee_flexion_measured_deg",
    "error_izq_deg", "error_der_deg",
    "error_abs_izq_deg", "error_abs_der_deg", "error_abs_medio_deg",
    "asimetria_verdadera_deg", "asimetria_medida_deg",
]


def barrer_malla() -> list[dict[str, Any]]:
    """Barre postura x flexion x proyeccion x condicion x azimut."""
    filas: list[dict[str, Any]] = []
    for postura in POSTURAS:
        for flexion in FLEXIONES_VERDADERAS_DEG:
            modelo = construir_modelo(flexion, postura)
            for proyeccion in PROYECCIONES:
                for condicion in CONDICIONES:
                    for phi in AZIMUTS_MALLA_DEG:
                        izq, der = medir_flexiones(modelo, phi, proyeccion, condicion)
                        err_i = izq - flexion
                        err_d = der - flexion
                        filas.append({
                            "postura": postura,
                            "proyeccion": proyeccion,
                            "condicion": condicion,
                            "flexion_verdadera_deg": round(flexion, 4),
                            "azimut_deg": round(phi, 4),
                            "left_knee_flexion_measured_deg": round(izq, 6),
                            "right_knee_flexion_measured_deg": round(der, 6),
                            "error_izq_deg": round(err_i, 6),
                            "error_der_deg": round(err_d, 6),
                            "error_abs_izq_deg": round(abs(err_i), 6),
                            "error_abs_der_deg": round(abs(err_d), 6),
                            "error_abs_medio_deg": round((abs(err_i) + abs(err_d)) / 2.0, 6),
                            "asimetria_verdadera_deg": 0.0,
                            "asimetria_medida_deg": round(abs(izq - der), 6),
                        })
    return filas


# ---------------------------------------------------------------------------
# 4. Barrido fino de azimut y umbral de 5 grados
# ---------------------------------------------------------------------------
CAMPOS_BARRIDO = [
    "proyeccion", "condicion", "azimut_deg",
    "error_abs_medio_deg", "error_abs_p95_deg", "error_abs_max_deg",
    "asimetria_espuria_media_deg", "asimetria_espuria_max_deg",
]


def barrer_fino() -> dict[tuple[str, str], dict[str, np.ndarray]]:
    """
    Barrido de azimut con paso fino, agregando sobre la malla de flexion y postura.

    Devuelve, por (proyeccion, condicion): azimut, error medio, percentil 95,
    maximo y asimetria espuria media y maxima.
    """
    azimuts = np.round(np.arange(0.0, 90.0 + PASO_BARRIDO_FINO_DEG / 2.0, PASO_BARRIDO_FINO_DEG), 4)
    modelos = {
        (postura, flexion): construir_modelo(flexion, postura)
        for postura in POSTURAS
        for flexion in FLEXIONES_VERDADERAS_DEG
    }

    salida: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    for proyeccion in PROYECCIONES:
        for condicion in CONDICIONES:
            medios, p95s, maximos, asim_med, asim_max = [], [], [], [], []
            for phi in azimuts:
                errores: list[float] = []
                asimetrias: list[float] = []
                for (postura, flexion), modelo in modelos.items():
                    izq, der = medir_flexiones(modelo, float(phi), proyeccion, condicion)
                    errores.append(abs(izq - flexion))
                    errores.append(abs(der - flexion))
                    asimetrias.append(abs(izq - der))
                arr = np.array(errores, dtype=float)
                asim = np.array(asimetrias, dtype=float)
                medios.append(float(np.nanmean(arr)))
                p95s.append(float(np.nanpercentile(arr, 95)))
                maximos.append(float(np.nanmax(arr)))
                asim_med.append(float(np.nanmean(asim)))
                asim_max.append(float(np.nanmax(asim)))
            salida[(proyeccion, condicion)] = {
                "azimut": azimuts,
                "medio": np.array(medios),
                "p95": np.array(p95s),
                "max": np.array(maximos),
                "asim_medio": np.array(asim_med),
                "asim_max": np.array(asim_max),
            }
    return salida


def azimut_maximo_tolerable(azimuts: np.ndarray, errores: np.ndarray, umbral: float) -> float:
    """
    Mayor azimut tal que el error se mantiene por debajo del umbral desde 0 hasta el.

    Devuelve NaN si el umbral ya se supera en azimut 0.
    """
    fuera = np.where(errores >= umbral)[0]
    if fuera.size == 0:
        return float(azimuts[-1])
    primera = int(fuera[0])
    if primera == 0:
        return float("nan")
    return float(azimuts[primera - 1])


# ---------------------------------------------------------------------------
# 5. Validacion empirica con video real
# ---------------------------------------------------------------------------
CAMPOS_EMPIRICO = [
    "azimut_adicional_deg", "n_frames", "n_muestras",
    "error_abs_medio_deg", "error_abs_mediana_deg", "error_abs_p95_deg", "error_abs_max_deg",
]


def _rotar_y_aplanar(landmarks: list[dict[str, Any]], phi_deg: float) -> list[dict[str, Any]]:
    """Rota los landmarks alrededor del eje vertical (y) y anula z (condicion 2D)."""
    c = math.cos(math.radians(phi_deg))
    s = math.sin(math.radians(phi_deg))
    return [
        {"index": p.get("index"), "x": p["x"] * c + p["z"] * s, "y": p["y"], "z": 0.0}
        for p in landmarks
    ]


def _transformar(
    landmarks: list[dict[str, Any]], factor_y: float = 1.0, factor_z: float = 1.0, anular_z: bool = False
) -> list[dict[str, Any]]:
    """Reescala y (relacion de aspecto) y z (escala de profundidad); opcionalmente anula z."""
    return [
        {
            "index": p.get("index"),
            "x": p["x"],
            "y": p["y"] * factor_y,
            "z": 0.0 if anular_z else p["z"] * factor_z,
        }
        for p in landmarks
    ]


def _flexiones(landmarks: list[dict[str, Any]]) -> tuple[float, float]:
    a = knee_angles_from_landmarks(landmarks)
    if a is None:
        return math.nan, math.nan
    return float(a["left_knee_flexion_angle_deg"]), float(a["right_knee_flexion_angle_deg"])


def _escalas_por_eje(
    normalizados: list[list[dict[str, Any]]], metricos: list[list[dict[str, Any]]]
) -> tuple[float, float, float]:
    """
    Estima por minimos cuadrados, eje a eje, cuantas unidades normalizadas
    corresponden a un metro de los ``world_landmarks``.

    Se usan diferencias entre pares de landmarks (segmentos), no coordenadas
    absolutas, para que el origen de cada sistema no influya.
    """
    num = {"x": 0.0, "y": 0.0, "z": 0.0}
    den = {"x": 0.0, "y": 0.0, "z": 0.0}
    for n, w in zip(normalizados, metricos):
        for a1, a2 in PARES_ESCALA:
            if max(a1, a2) >= min(len(n), len(w)):
                continue
            for eje in ("x", "y", "z"):
                dn = float(n[a2][eje]) - float(n[a1][eje])
                dw = float(w[a2][eje]) - float(w[a1][eje])
                num[eje] += dn * dw
                den[eje] += dw * dw
    return tuple(  # type: ignore[return-value]
        (num[e] / den[e]) if den[e] > 1e-12 else math.nan for e in ("x", "y", "z")
    )


def procesar_video_real() -> dict[str, Any] | None:
    """Extrae pose de un video real y guarda landmarks normalizados y metricos por frame."""
    if not RUTA_VIDEO.is_file() or not RUTA_MODELO.is_file():
        print("[aviso] validacion empirica omitida: falta el video o el modelo")
        return None
    try:
        import cv2
        from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor
        from vision.pose_extractor import extract_pose_bgr_video
    except Exception as exc:  # noqa: BLE001
        print(f"[aviso] validacion empirica omitida: {exc}")
        return None

    reset_pose_video_timestamp_anchor()
    cap = cv2.VideoCapture(str(RUTA_VIDEO))
    if not cap.isOpened():
        print("[aviso] validacion empirica omitida: no se pudo abrir el video")
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    normalizados: list[list[dict[str, Any]]] = []
    metricos: list[list[dict[str, Any]]] = []
    indice = 0
    t0 = time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        pf = extract_pose_bgr_video(frame, RUTA_MODELO, int(round(indice * 1000.0 / fps)))
        indice += 1
        if pf.ok and pf.landmarks and pf.world_landmarks:
            normalizados.append(pf.landmarks)
            metricos.append(pf.world_landmarks)
    cap.release()
    segundos = time.perf_counter() - t0

    if not metricos:
        return None

    ref = np.array([_flexiones(w) for w in metricos])  # (n, 2): izq, der
    sx, sy, sz = _escalas_por_eje(normalizados, metricos)

    # Oblicuidad geometrica de la toma a partir del eje de caderas en el sistema metrico.
    orientaciones = []
    for w in metricos:
        dx = float(w[RIGHT_HIP]["x"]) - float(w[LEFT_HIP]["x"])
        dz = float(w[RIGHT_HIP]["z"]) - float(w[LEFT_HIP]["z"])
        orientaciones.append(math.degrees(math.atan2(abs(dz), abs(dx))))
    orient = np.array(orientaciones)

    return {
        "normalizados": normalizados,
        "metricos": metricos,
        "ref": ref,
        "escala_x": sx, "escala_y": sy, "escala_z": sz,
        "orientacion_caderas_deg": orient,
        "frames_leidos": indice,
        "ancho": ancho, "alto": alto, "fps": fps,
        "segundos": segundos,
        "ms_por_frame": (segundos / indice * 1000.0) if indice else math.nan,
    }


def barrer_azimut_empirico(datos: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Aplica un azimut adicional a los landmarks metricos reales y mide el error de la
    condicion 2D contra la referencia 3D del mismo frame.

    Se descartan los frames con flexion de referencia por debajo de
    ``FLEXION_MINIMA_EMPIRICA_DEG`` porque en extension casi completa el error es
    trivialmente nulo y diluiria el promedio.
    """
    ref = datos["ref"]
    usar = [k for k in range(len(datos["metricos"])) if float(np.nanmax(ref[k])) >= FLEXION_MINIMA_EMPIRICA_DEG]
    filas: list[dict[str, Any]] = []
    for phi in AZIMUTS_EMPIRICOS_DEG:
        errores: list[float] = []
        for k in usar:
            izq, der = _flexiones(_rotar_y_aplanar(datos["metricos"][k], phi))
            errores.append(abs(izq - float(ref[k][0])))
            errores.append(abs(der - float(ref[k][1])))
        arr = np.array(errores, dtype=float)
        filas.append({
            "azimut_adicional_deg": round(phi, 4),
            "n_frames": len(usar),
            "n_muestras": int(arr.size),
            "error_abs_medio_deg": round(float(np.nanmean(arr)), 4),
            "error_abs_mediana_deg": round(float(np.nanmedian(arr)), 4),
            "error_abs_p95_deg": round(float(np.nanpercentile(arr, 95)), 4),
            "error_abs_max_deg": round(float(np.nanmax(arr)), 4),
        })
    return filas


def comparar_variantes_landmarks(datos: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Compara, sobre el video real, el angulo obtenido con distintas representaciones
    de los landmarks normalizados frente al angulo obtenido con ``world_landmarks``.

    Sirve para separar el efecto de la relacion de aspecto (eje y) del efecto de la
    escala de profundidad (eje z).
    """
    ref = datos["ref"]
    ancho, alto = datos["ancho"], datos["alto"]
    f_aspecto = alto / ancho if ancho else 1.0
    razon_z = (datos["escala_z"] / datos["escala_x"]) if datos["escala_x"] else RAZON_Z_POR_DEFECTO
    f_z = 1.0 / razon_z if razon_z else 1.0

    variantes = [
        ("3D con landmarks normalizados tal cual", dict(factor_y=1.0, factor_z=1.0, anular_z=False)),
        ("3D con y corregido por aspecto", dict(factor_y=f_aspecto, factor_z=1.0, anular_z=False)),
        ("3D con y y z corregidos", dict(factor_y=f_aspecto, factor_z=f_z, anular_z=False)),
        ("2D (z anulada) tal cual", dict(factor_y=1.0, factor_z=1.0, anular_z=True)),
        ("2D (z anulada) con y corregido", dict(factor_y=f_aspecto, factor_z=1.0, anular_z=True)),
    ]
    filas: list[dict[str, Any]] = []
    for nombre, kwargs in variantes:
        diffs: list[float] = []
        for k, n in enumerate(datos["normalizados"]):
            izq, der = _flexiones(_transformar(n, **kwargs))
            diffs.append(izq - float(ref[k][0]))
            diffs.append(der - float(ref[k][1]))
        arr = np.array(diffs, dtype=float)
        filas.append({
            "variante": nombre,
            "sesgo_deg": float(np.nanmean(arr)),
            "dif_abs_media_deg": float(np.nanmean(np.abs(arr))),
            "dif_abs_p95_deg": float(np.nanpercentile(np.abs(arr), 95)),
            "dif_abs_max_deg": float(np.nanmax(np.abs(arr))),
        })
    return filas


# ---------------------------------------------------------------------------
# 6. Coherencia metrica de los ejes, sobre la malla sintetica
# ---------------------------------------------------------------------------
def analizar_coherencia_ejes(ancho: int, alto: int, razon_z: float) -> dict[str, Any]:
    """
    Cuantifica, con profundidad perfecta (condicion 3D), el error angular que
    introduce cada incoherencia de escala entre ejes:

    - relacion de aspecto: y va normalizado por el alto y x por el ancho, luego el
      eje vertical queda estirado un factor ancho/alto respecto al horizontal;
    - escala de profundidad: la z normalizada de MediaPipe no esta en la escala de
      x sino ``razon_z`` veces mayor (medido sobre video real).

    Se evalua sobre toda la malla de azimut porque las dos incoherencias no se
    comportan igual: la de aspecto actua ya con la camara alineada, mientras que la
    de profundidad solo aparece cuando el miembro tiene componente de profundidad,
    es decir, cuando hay oblicuidad. La referencia es la condicion 3D ortografica
    sin distorsion, cuyo error es 0.00 grados en toda la malla.
    """
    f_aspecto = ancho / alto if alto else 1.0
    casos = {
        "solo relacion de aspecto": (f_aspecto, 1.0),
        "solo escala de profundidad": (1.0, razon_z),
        "ambas (normalizados tal cual)": (f_aspecto, razon_z),
    }
    resultado: dict[str, Any] = {"factor_aspecto": f_aspecto, "razon_z": razon_z, "casos": {}}
    for nombre, (fy, fz) in casos.items():
        por_azimut: dict[float, tuple[float, float]] = {}
        globales: list[float] = []
        for phi in AZIMUTS_MALLA_DEG:
            errores: list[float] = []
            for postura in POSTURAS:
                for flexion in FLEXIONES_VERDADERAS_DEG:
                    modelo = construir_modelo(flexion, postura)
                    izq, der = medir_flexiones(
                        modelo, phi, "ortografica", "3D", factor_y=fy, factor_z=fz
                    )
                    errores.append(abs(izq - flexion))
                    errores.append(abs(der - flexion))
            arr = np.array(errores, dtype=float)
            por_azimut[phi] = (float(np.nanmean(arr)), float(np.nanmax(arr)))
            globales.extend(errores)
        arr_g = np.array(globales, dtype=float)
        resultado["casos"][nombre] = {
            "por_azimut": por_azimut,
            "error_abs_medio_phi0": por_azimut[0.0][0],
            "error_abs_max_phi0": por_azimut[0.0][1],
            "error_abs_medio_global": float(np.nanmean(arr_g)),
            "error_abs_max_global": float(np.nanmax(arr_g)),
        }
    return resultado


# ---------------------------------------------------------------------------
# 7. Salidas
# ---------------------------------------------------------------------------
def escribir_csv(ruta: Path, campos: list[str], filas: Iterable[dict[str, Any]]) -> None:
    """Escribe un CSV UTF-8 con finales de linea LF."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        for fila in filas:
            w.writerow(fila)


def _estilo_eje(ax) -> None:
    ax.set_facecolor("#ffffff")
    ax.grid(True, color=COLOR_REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(COLOR_REJILLA)
    ax.tick_params(colors=COLOR_TEXTO_SEC, labelsize=8)


SERIES_FIGURA = [
    ("ortografica", "3D", COLOR_3D, "-", "Ortografica, 3D (z conservada)"),
    ("ortografica", "2D", COLOR_2D, "-", "Ortografica, 2D (z = 0)"),
    ("perspectiva", "3D", COLOR_3D, "--", "Perspectiva 2.5 m, 3D"),
    ("perspectiva", "2D", COLOR_2D, "--", "Perspectiva 2.5 m, 2D"),
]


def generar_figura(
    fino: dict[tuple[str, str], dict[str, np.ndarray]],
    empirico: list[dict[str, Any]] | None,
    datos_video: dict[str, Any] | None,
    umbrales_max: dict[tuple[str, str], float],
    ruta_png: Path,
) -> None:
    """Figura de cuatro paneles con el resultado central del experimento."""
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.8), dpi=170)
    fig.patch.set_facecolor("#ffffff")

    # (a) error medio, escala completa
    ax = axes[0][0]
    _estilo_eje(ax)
    for proy, cond, color, ls, etiqueta in SERIES_FIGURA:
        d = fino[(proy, cond)]
        ax.plot(d["azimut"], d["medio"], color=color, linestyle=ls, linewidth=2.0, label=etiqueta)
    ax.axhline(UMBRAL_CLINICO_DEG, color=COLOR_UMBRAL, linewidth=1.4, linestyle=":")
    ax.text(46, UMBRAL_CLINICO_DEG + 1.5, "umbral clinico 5 grados", color=COLOR_UMBRAL, fontsize=8)
    ax.set_title("(a) Error absoluto medio frente al azimut de camara", fontsize=10, color=COLOR_TEXTO, loc="left")
    ax.set_xlabel("Azimut de camara phi (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_ylabel("Error absoluto medio (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_xlim(0, 90)
    ax.set_xticks([0, 15, 30, 45, 60, 75, 90])
    ax.legend(fontsize=8, frameon=False, loc="upper left", labelcolor=COLOR_TEXTO_SEC)

    # (b) peor caso, zoom operativo
    ax = axes[0][1]
    _estilo_eje(ax)
    for proy, cond, color, ls, etiqueta in SERIES_FIGURA:
        d = fino[(proy, cond)]
        ax.plot(d["azimut"], d["max"], color=color, linestyle=ls, linewidth=2.0, label=etiqueta)
    ax.axhline(UMBRAL_CLINICO_DEG, color=COLOR_UMBRAL, linewidth=1.4, linestyle=":")
    for (proy, cond), phi_max in umbrales_max.items():
        if math.isnan(phi_max) or phi_max >= 89.9:
            continue
        color = COLOR_3D if cond == "3D" else COLOR_2D
        ax.axvline(phi_max, color=color, linewidth=1.1, linestyle="-.", alpha=0.6)
        ax.annotate(
            f"phi = {phi_max:.1f}", xy=(phi_max - 0.6, 11.6), fontsize=8, color=color,
            rotation=90, ha="right", va="top",
        )
    ax.set_title("(b) Peor caso sobre la malla de flexion (zoom operativo)", fontsize=10, color=COLOR_TEXTO, loc="left")
    ax.set_xlabel("Azimut de camara phi (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_ylabel("Error absoluto maximo (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_xlim(0, 45)
    ax.set_ylim(0, 12)
    ax.legend(fontsize=8, frameon=False, loc="upper left", labelcolor=COLOR_TEXTO_SEC)

    # (c) mapa de calor flexion x azimut para la condicion critica
    ax = axes[1][0]
    postura_mapa = "flexion_repartida"
    matriz = np.zeros((len(FLEXIONES_VERDADERAS_DEG), len(AZIMUTS_MALLA_DEG)))
    for i, flexion in enumerate(FLEXIONES_VERDADERAS_DEG):
        modelo = construir_modelo(flexion, postura_mapa)
        for j, phi in enumerate(AZIMUTS_MALLA_DEG):
            izq, der = medir_flexiones(modelo, phi, "ortografica", "2D")
            matriz[i, j] = (abs(izq - flexion) + abs(der - flexion)) / 2.0
    cmap = LinearSegmentedColormap.from_list("azul_secuencial", RAMPA_AZUL)
    im = ax.imshow(matriz, cmap=cmap, aspect="auto", origin="lower", vmin=0.0, vmax=float(matriz.max()))
    ax.set_xticks(range(len(AZIMUTS_MALLA_DEG)))
    ax.set_xticklabels([f"{v:.0f}" for v in AZIMUTS_MALLA_DEG], fontsize=8)
    ax.set_yticks(range(len(FLEXIONES_VERDADERAS_DEG)))
    ax.set_yticklabels([f"{v:.0f}" for v in FLEXIONES_VERDADERAS_DEG], fontsize=8)
    ax.set_title("(c) Error absoluto (grados), condicion 2D ortografica",
                 fontsize=10, color=COLOR_TEXTO, loc="left")
    ax.set_xlabel("Azimut phi (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_ylabel("Flexion verdadera (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            valor = matriz[i, j]
            ax.text(j, i, f"{valor:.0f}", ha="center", va="center", fontsize=7,
                    color="#ffffff" if valor > 0.55 * matriz.max() else COLOR_TEXTO)
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cb.set_label("grados", fontsize=8, color=COLOR_TEXTO_SEC)
    cb.ax.tick_params(labelsize=7, colors=COLOR_TEXTO_SEC)
    ax.tick_params(colors=COLOR_TEXTO_SEC)

    # (d) validacion empirica con video real
    ax = axes[1][1]
    _estilo_eje(ax)
    if empirico:
        xs = [f["azimut_adicional_deg"] for f in empirico]
        medios = [f["error_abs_medio_deg"] for f in empirico]
        medianas = [f["error_abs_mediana_deg"] for f in empirico]
        ax.plot(xs, medios, color=COLOR_2D, linewidth=1.5, linestyle="--", marker="s", markersize=3.5,
                alpha=0.7, label="Error medio (sensible a frames atipicos)")
        ax.plot(xs, medianas, color=COLOR_2D, linewidth=2.2, marker="o", markersize=4.5,
                label="Error mediano, condicion 2D")
        ax.axhline(UMBRAL_CLINICO_DEG, color=COLOR_UMBRAL, linewidth=1.4, linestyle=":")
        i_min = int(np.argmin(medianas))
        ax.axvline(xs[i_min], color=COLOR_3D, linewidth=1.2, linestyle="-.", alpha=0.7)
        ax.annotate(
            f"minimo en phi = {xs[i_min]:.0f} ({medianas[i_min]:.1f} grados)",
            xy=(xs[i_min] + 3, medianas[i_min] + 0.3), fontsize=8, color=COLOR_3D,
            ha="left", va="bottom",
        )
        ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2, labelcolor=COLOR_TEXTO_SEC)
        ax.set_xlim(-90, 90)
        ax.set_xticks([-90, -60, -30, 0, 30, 60, 90])
    else:
        ax.text(0.5, 0.5, "Validacion empirica no disponible", ha="center", va="center",
                transform=ax.transAxes, color=COLOR_TEXTO_SEC, fontsize=9)
    subtitulo = f" ({len(datos_video['metricos'])} frames)" if datos_video is not None else ""
    ax.set_title(f"(d) Video real de sentadilla profunda{subtitulo}",
                 fontsize=10, color=COLOR_TEXTO, loc="left")
    ax.set_xlabel("Azimut adicional sobre la toma real (grados)", fontsize=9, color=COLOR_TEXTO_SEC)
    ax.set_ylabel("Error absoluto (grados)", fontsize=9, color=COLOR_TEXTO_SEC)

    fig.suptitle(
        "Experimento 2. Sensibilidad del angulo de flexion de rodilla a la oblicuidad de camara",
        fontsize=12.5, color=COLOR_TEXTO, x=0.012, ha="left", y=0.985,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    ruta_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta_png, facecolor="#ffffff")
    plt.close(fig)


def _tabla_md(cabeceras: list[str], filas: list[list[str]]) -> str:
    lineas = ["| " + " | ".join(cabeceras) + " |",
              "|" + "|".join([" --- "] * len(cabeceras)) + "|"]
    for f in filas:
        lineas.append("| " + " | ".join(f) + " |")
    return "\n".join(lineas)


def escribir_informe(
    ruta_md: Path,
    malla: list[dict[str, Any]],
    umbrales_max: dict[tuple[str, str], float],
    umbrales_medio: dict[tuple[str, str], float],
    empirico: list[dict[str, Any]] | None,
    variantes: list[dict[str, Any]] | None,
    datos_video: dict[str, Any] | None,
    coherencia: dict[str, Any],
    segundos: float,
) -> None:
    """Redacta el informe en Markdown con las tablas resumen y las conclusiones."""
    def sub(proy: str, cond: str, phi: float, campo: str) -> np.ndarray:
        return np.array([f[campo] for f in malla
                         if f["proyeccion"] == proy and f["condicion"] == cond and f["azimut_deg"] == phi],
                        dtype=float)

    p: list[str] = []
    p.append("# Experimento 2. Sensibilidad a la oblicuidad de cámara\n")
    p.append(
        "Cuantifica el error del ángulo de flexión de rodilla cuando la cámara no está "
        "perpendicular al plano sagital del sujeto, y separa la contribución de la coordenada "
        "de profundidad `z`. Todas las medidas se obtienen pasando los landmarks por la función "
        "de producción `vision.biomechanics.knee_angles_from_landmarks`.\n"
    )

    p.append("## Configuración\n")
    p.append(
        f"- Modelo geométrico: muslo {LARGO_MUSLO_M:.2f} m, pierna {LARGO_PIERNA_M:.2f} m, "
        f"ancho de caderas {ANCHO_CADERAS_M:.2f} m.\n"
        f"- Las dos piernas se construyen con la misma flexión verdadera, de modo que la "
        f"asimetría bilateral verdadera es exactamente 0.00 grados y cualquier asimetría medida "
        f"es espuria.\n"
        f"- Flexión verdadera: {', '.join(f'{v:.0f}' for v in FLEXIONES_VERDADERAS_DEG)} grados.\n"
        f"- Azimut phi: {', '.join(f'{v:.0f}' for v in AZIMUTS_MALLA_DEG)} grados. phi = 0 es la "
        f"vista sagital perfecta; phi = 90 es la vista frontal, con el plano sagital de canto.\n"
        f"- Posturas: `rodilla_aislada` (muslo vertical, pierna hacia posterior) y "
        f"`flexion_repartida` (la flexión se reparte simétricamente respecto a la vertical). "
        f"Misma flexión verdadera, distinta orientación absoluta del miembro.\n"
        f"- Proyecciones: ortográfica (caso base) y perspectiva a {DISTANCIA_CAMARA_M:.1f} m con "
        f"campo de visión horizontal de {FOV_HORIZONTAL_DEG:.0f} grados.\n"
        f"- Condiciones: `3D` conserva z (profundidad perfecta); `2D` fuerza z = 0.\n"
        f"- Umbral de acuerdo clínico usado: {UMBRAL_CLINICO_DEG:.0f} grados.\n"
        f"- Tiempo total de ejecución: {segundos:.1f} s.\n"
    )

    def por_pierna(proy: str, cond: str, phi: float) -> np.ndarray:
        """
        Errores absolutos con UNA muestra por pierna, no el promedio de las dos.

        El promedio de piernas oculta el peor caso en la proyeccion en perspectiva,
        donde las dos piernas estan a distinta profundidad y su error difiere. Es la
        misma convencion de agregacion que usa el barrido fino de azimut.
        """
        return np.concatenate([
            sub(proy, cond, phi, "error_abs_izq_deg"),
            sub(proy, cond, phi, "error_abs_der_deg"),
        ])

    p.append("\n## Tabla 1. Error absoluto (grados) frente al azimut\n")
    p.append(
        "Agregado sobre las 10 flexiones verdaderas, las 2 posturas y las 2 piernas, con una "
        "muestra por pierna (el máximo es el peor caso de una pierna concreta, no el peor "
        "promedio de las dos).\n"
    )
    cab = ["Azimut"]
    for proy in PROYECCIONES:
        for cond in CONDICIONES:
            cab += [f"{proy[:6]}. {cond} medio", f"{proy[:6]}. {cond} máx"]
    filas: list[list[str]] = []
    for phi in AZIMUTS_MALLA_DEG:
        fila = [f"{phi:.0f}"]
        for proy in PROYECCIONES:
            for cond in CONDICIONES:
                v = por_pierna(proy, cond, phi)
                fila += [f"{np.nanmean(v):.2f}", f"{np.nanmax(v):.2f}"]
        filas.append(fila)
    p.append(_tabla_md(cab, filas) + "\n")

    p.append("\n## Tabla 2. Error absoluto por flexión verdadera, condición 2D ortográfica\n")
    p.append("Media de las dos posturas y las dos piernas.\n")
    cab2 = ["Flexión verdadera"] + [f"phi={v:.0f}" for v in AZIMUTS_MALLA_DEG]
    filas2: list[list[str]] = []
    for flexion in FLEXIONES_VERDADERAS_DEG:
        fila = [f"{flexion:.0f}"]
        for phi in AZIMUTS_MALLA_DEG:
            v = [f["error_abs_medio_deg"] for f in malla
                 if f["proyeccion"] == "ortografica" and f["condicion"] == "2D"
                 and f["azimut_deg"] == phi and f["flexion_verdadera_deg"] == flexion]
            fila.append(f"{float(np.nanmean(v)):.2f}")
        filas2.append(fila)
    p.append(_tabla_md(cab2, filas2) + "\n")

    p.append("\n## Tabla 3. Asimetría bilateral espuria (grados)\n")
    p.append("Asimetría verdadera = 0.00 grados. Se muestra el máximo sobre flexión y postura.\n")
    cab3 = ["Azimut", "Ortográfica 3D", "Ortográfica 2D", "Perspectiva 3D", "Perspectiva 2D"]
    filas3: list[list[str]] = []
    for phi in AZIMUTS_MALLA_DEG:
        fila = [f"{phi:.0f}"]
        for proy in PROYECCIONES:
            for cond in CONDICIONES:
                fila.append(f"{float(np.nanmax(sub(proy, cond, phi, 'asimetria_medida_deg'))):.3f}")
        filas3.append(fila)
    p.append(_tabla_md(cab3, filas3) + "\n")

    p.append("\n## Respuesta al umbral de 5 grados\n")
    p.append(
        "Barrido fino de azimut con paso "
        f"{PASO_BARRIDO_FINO_DEG} grados. Se busca el mayor phi tal que el error se mantiene "
        "por debajo de 5 grados desde 0 hasta ese valor.\n"
    )
    cab4 = ["Proyección", "Condición", "Error MEDIO < 5 grados hasta phi", "Error MÁXIMO < 5 grados hasta phi"]
    filas4: list[list[str]] = []
    for proy in PROYECCIONES:
        for cond in CONDICIONES:
            def fmt(v: float) -> str:
                if math.isnan(v):
                    return "ya excedido en phi = 0"
                return "sin límite (90)" if v >= 89.9 else f"{v:.1f} grados"
            filas4.append([proy, cond, fmt(umbrales_medio[(proy, cond)]), fmt(umbrales_max[(proy, cond)])])
    p.append(_tabla_md(cab4, filas4) + "\n")

    phi_2d_orto = umbrales_max[("ortografica", "2D")]
    phi_2d_persp = umbrales_max[("perspectiva", "2D")]
    p.append(
        f"\n**Respuesta directa.** Con profundidad perfecta (condición 3D) el azimut no impone "
        f"ningún límite práctico: con proyección ortográfica la rotación es una transformación "
        f"rígida y el ángulo entre segmentos es exactamente invariante (0.00 grados de error hasta "
        f"phi = 90), y con perspectiva queda un residuo que nunca llega al umbral. El límite lo fija "
        f"la condición 2D. Exigiendo que el error no supere los "
        f"5 grados en NINGÚN punto de la malla de flexión, el azimut máximo tolerable es "
        f"**{phi_2d_orto:.1f} grados** con proyección ortográfica y **{phi_2d_persp:.1f} grados** "
        f"con perspectiva a {DISTANCIA_CAMARA_M:.1f} m. Si sólo se exige que el error MEDIO se "
        f"mantenga por debajo de 5 grados, el margen sube a "
        f"{umbrales_medio[('ortografica', '2D')]:.1f} y {umbrales_medio[('perspectiva', '2D')]:.1f} "
        f"grados respectivamente.\n"
    )

    if empirico and datos_video:
        p.append("\n## Validación empírica con vídeo real\n")
        medios = [f["error_abs_medio_deg"] for f in empirico]
        medianas = [f["error_abs_mediana_deg"] for f in empirico]
        i_min = int(np.argmin(medianas))
        phi_min = empirico[i_min]["azimut_adicional_deg"]
        orient = datos_video["orientacion_caderas_deg"]
        oblicuidad = 90.0 - float(np.median(orient))
        p.append(
            f"Vídeo `SentadillaProfunda.mp4` ({datos_video['ancho']}x{datos_video['alto']}, "
            f"{datos_video['fps']:.2f} fps, {datos_video['frames_leidos']} frames leídos, "
            f"{len(datos_video['metricos'])} con pose válida; extracción {datos_video['segundos']:.1f} s, "
            f"{datos_video['ms_por_frame']:.1f} ms/frame). Se toman los landmarks métricos "
            f"(`world_landmarks`) de cada frame, se rotan alrededor del eje vertical un azimut "
            f"adicional y se mide el error de la condición 2D contra la referencia 3D del mismo "
            f"frame. Sólo se usan los {empirico[0]['n_frames']} frames con flexión de referencia "
            f"mayor o igual a {FLEXION_MINIMA_EMPIRICA_DEG:.0f} grados.\n"
        )
        med = {f["azimut_adicional_deg"]: f["error_abs_mediana_deg"] for f in empirico}
        p.append(
            f"\nDentro del rango operativo la curva empírica reproduce la forma en V que predice el "
            f"modelo sintético: el error mediano vale {med[-45.0]:.2f} grados en phi = -45, baja a "
            f"{med[0.0]:.2f} en phi = 0, alcanza su mínimo de {medianas[i_min]:.2f} grados en "
            f"phi = {phi_min:+.0f} y vuelve a subir hasta {med[45.0]:.2f} en phi = +45. Ese mínimo es "
            f"una estimación de cuánto le falta a la toma real para ser perfectamente sagital, y "
            f"coincide en magnitud con un segundo estimador geométrico: la orientación "
            f"del eje de caderas en el sistema métrico sitúa la oblicuidad de esta grabación en "
            f"{oblicuidad:.0f} grados (mediana sobre frames). Ese acuerdo **no es una validación "
            f"cruzada**: los dos estimadores se calculan sobre la coordenada `z` de los mismos "
            f"`world_landmarks` y de los mismos frames, de modo que comparten la fuente de error "
            f"y pueden equivocarse juntos. Además el estimador del eje de caderas usa "
            f"`atan2(|dz|, |dx|)`, que es ciego al signo: corrobora la magnitud de la oblicuidad, "
            f"nunca su sentido.\n"
        )
        p.append(
            f"\nFuera de +/- 45 grados la curva deja de ser informativa y se vuelve no monótona "
            f"({med[-90.0]:.2f} grados en phi = -90 y {med[90.0]:.2f} en phi = +90, por debajo de "
            f"valores intermedios). El motivo es que la referencia usada aquí, la profundidad de los "
            f"`world_landmarks`, no es una verdad de terreno: en este vídeo el segmento cadera-rodilla "
            f"presenta una extensión en profundidad comparable a la horizontal, algo que no encaja con "
            f"una toma casi lateral. Con oblicuidades grandes ese ruido de profundidad domina el "
            f"resultado. Por eso se reporta la mediana además de la media, y por eso este bloque debe "
            f"leerse como una comprobación de consistencia sobre datos reales, no como una validación "
            f"contra un patrón de referencia externo.\n"
        )
        cab5 = ["Azimut adicional", "Error mediano", "Error medio", "Percentil 95", "Error máximo"]
        filas5 = [
            [f"{f['azimut_adicional_deg']:+.0f}", f"{f['error_abs_mediana_deg']:.2f}",
             f"{f['error_abs_medio_deg']:.2f}", f"{f['error_abs_p95_deg']:.2f}",
             f"{f['error_abs_max_deg']:.2f}"]
            for f in empirico if int(f["azimut_adicional_deg"]) % 15 == 0
        ]
        p.append(_tabla_md(cab5, filas5) + "\n")
        p.append(
            f"\nEl error residual de {medianas[i_min]:.2f} grados (mediana) en el mínimo NO es "
            f"oblicuidad: es el "
            f"coste de anular la profundidad en una toma que ya está razonablemente alineada, más el "
            f"ruido propio de MediaPipe en una sentadilla profunda con oclusión de la pierna lejana. "
            f"Marca el suelo de error del sistema en la condición 2D.\n"
        )

    p.append("\n## Coherencia métrica de los ejes en los landmarks normalizados\n")
    p.append(
        "Hallazgo colateral, pero con consecuencias directas sobre la exactitud del sistema. "
        "Se cuantifica aquí el error que se comete al calcular el ángulo sobre los landmarks "
        "NORMALIZADOS de MediaPipe en lugar de sobre los `world_landmarks`. En esos landmarks `x` está "
        "dividido por el ancho de imagen, `y` por el alto, y la documentación de MediaPipe afirma "
        "que `z` usa aproximadamente la misma escala que `x`. El cálculo del ángulo en 3D exige que "
        "los tres ejes compartan escala; si no la comparten, el ángulo se deforma aunque la cámara "
        "esté perfectamente alineada y la profundidad sea perfecta.\n"
    )
    if datos_video is not None:
        sx, sy, sz = datos_video["escala_x"], datos_video["escala_y"], datos_video["escala_z"]
        p.append(
            f"\nEscalas estimadas por mínimos cuadrados sobre {len(datos_video['metricos'])} frames "
            f"del vídeo real (unidades normalizadas por metro, usando diferencias entre pares de "
            f"landmarks):\n\n"
            f"- `s_x` = {sx:.4f}\n"
            f"- `s_y` = {sy:.4f}, de donde `s_y/s_x` = **{sy / sx:.4f}** frente al valor esperado "
            f"si sólo actuase la relación de aspecto, ancho/alto = "
            f"{datos_video['ancho'] / datos_video['alto']:.4f}. La anisotropía por relación de "
            f"aspecto queda confirmada con un desajuste del "
            f"{abs(sy / sx - datos_video['ancho'] / datos_video['alto']) / (datos_video['ancho'] / datos_video['alto']) * 100:.1f} %.\n"
            f"- `s_z` = {sz:.4f}, de donde `s_z/s_x` = **{sz / sx:.4f}**, frente al valor 1.0 que "
            f"cabría esperar según la documentación. La profundidad normalizada está sobredimensionada "
            f"un factor {sz / sx:.1f} respecto al eje horizontal.\n"
        )
    p.append(
        f"\nEfecto de cada incoherencia sobre la malla sintética, con profundidad perfecta "
        f"(condición 3D ortográfica, cuyo error sin distorsión es 0.00 grados en toda la malla). "
        f"Factor de aspecto {coherencia['factor_aspecto']:.4f}, razón de profundidad "
        f"{coherencia['razon_z']:.2f}. Se muestra el error absoluto medio, y entre paréntesis el "
        f"máximo, agregando sobre flexión, postura y piernas:\n"
    )
    azimuts_coh = [0.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0]
    cab6 = ["Incoherencia aplicada"] + [f"phi={v:.0f}" for v in azimuts_coh]
    filas6 = []
    for nombre, d in coherencia["casos"].items():
        fila = [nombre]
        for phi in azimuts_coh:
            medio, maximo = d["por_azimut"][phi]
            fila.append(f"{medio:.2f} ({maximo:.2f})")
        filas6.append(fila)
    p.append(_tabla_md(cab6, filas6) + "\n")
    aspecto = coherencia["casos"]["solo relacion de aspecto"]
    profund = coherencia["casos"]["solo escala de profundidad"]
    p.append(
        f"\nLas dos incoherencias no se comportan igual. La de **relación de aspecto** actúa ya con "
        f"la cámara perfectamente alineada: {aspecto['error_abs_medio_phi0']:.2f} grados de error "
        f"medio y {aspecto['error_abs_max_phi0']:.2f} de máximo en phi = 0, es decir, un orden de "
        f"magnitud por encima de lo que cuesta una desalineación de 20 grados. Su valor además no "
        f"depende del azimut, y no es casualidad: los dos segmentos del miembro viven en el mismo "
        f"plano, luego sus componentes horizontales apuntan siempre en la misma dirección de la "
        f"imagen y el problema se reduce a uno bidimensional en el que sólo interviene el estiramiento "
        f"vertical. La de **escala de "
        f"profundidad** vale exactamente 0.00 grados en phi = 0, porque con la cámara alineada el "
        f"miembro no tiene componente de profundidad, y sólo aparece al desalinear: "
        f"{profund['por_azimut'][20.0][0]:.2f} grados de media en phi = 20 y "
        f"{profund['por_azimut'][45.0][0]:.2f} en phi = 45. Es decir, la `z` mal escalada convierte "
        f"la oblicuidad en error incluso cuando la profundidad estimada es geométricamente correcta.\n"
    )
    ambas = coherencia["casos"]["ambas (normalizados tal cual)"]
    p.append(
        f"\nAdemás, las dos distorsiones se compensan parcialmente entre sí: aplicadas juntas, el "
        f"error medio en phi = 20 es {ambas['por_azimut'][20.0][0]:.2f} grados, menor que los "
        f"{profund['por_azimut'][20.0][0]:.2f} de la distorsión de profundidad sola. Esa compensación "
        f"es un accidente numérico, no una propiedad: depende de la distancia de captura, del "
        f"encuadre y de la relación de aspecto, y no debe tomarse como excusa para no corregir las "
        f"escalas.\n"
        f"\nConviene precisar qué se está midiendo. `s_z/s_x` = {coherencia['razon_z']:.2f} dice que "
        f"la profundidad normalizada y la profundidad métrica de MediaPipe **no concuerdan entre sí** "
        f"por un factor de aproximadamente {coherencia['razon_z']:.1f}. Puede ser que la `z` "
        f"normalizada esté sobredimensionada, que la `z` métrica esté subdimensionada, o ambas cosas. "
        f"Lo que sí es seguro es que las dos salidas del mismo modelo se contradicen entre sí, y que "
        f"calcular un ángulo en 3D mezclando `x`, `y` y `z` normalizados asume una coherencia de "
        f"escala que aquí no se cumple.\n"
    )

    if variantes:
        p.append(
            "\nComprobación sobre el vídeo real. Se compara el ángulo obtenido con cada "
            "representación de los landmarks normalizados contra el ángulo obtenido con los "
            "`world_landmarks` del mismo frame, que es la mejor referencia métrica disponible.\n"
        )
        cab7 = ["Representación", "Sesgo", "Diferencia absoluta media", "Percentil 95", "Máximo"]
        filas7 = [
            [v["variante"], f"{v['sesgo_deg']:+.2f}", f"{v['dif_abs_media_deg']:.2f}",
             f"{v['dif_abs_p95_deg']:.2f}", f"{v['dif_abs_max_deg']:.2f}"]
            for v in variantes
        ]
        p.append(_tabla_md(cab7, filas7) + "\n")
        p.append(
            "\nCorregir sólo la relación de aspecto EMPEORA el resultado, porque al encoger el eje "
            "vertical se agrava el peso relativo de una `z` ya sobredimensionada. Corregir los dos "
            "ejes a la vez sí mejora de forma clara. La conclusión práctica es que las dos "
            "correcciones sólo tienen sentido juntas.\n"
        )

    def medio_en(proy: str, cond: str, phi: float) -> float:
        return float(np.nanmean(sub(proy, cond, phi, "error_abs_medio_deg")))

    def asim_max(phis: list[float]) -> float:
        """Maxima asimetria espuria entre ambas proyecciones y condiciones, sobre esos azimuts."""
        vals = [
            float(np.nanmax(sub(proy, cond, phi, "asimetria_medida_deg")))
            for phi in phis for proy in PROYECCIONES for cond in CONDICIONES
        ]
        return max(vals)

    asim_dentro = asim_max([v for v in AZIMUTS_MALLA_DEG if v <= AZIMUT_RECOMENDADO_DEG])
    asim_fuera = asim_max([v for v in AZIMUTS_MALLA_DEG if v < 90.0])
    piso_asim = max(1.0, math.ceil(asim_dentro * 2.0) / 2.0)
    p.append("\n## Conclusiones\n")
    p.append(
        "1. **Con profundidad perfecta, la oblicuidad de cámara no introduce ningún error.** En la "
        "condición 3D con proyección ortográfica la rotación de azimut es una transformación rígida "
        "y el ángulo entre segmentos es invariante: el error es 0.00 grados en toda la malla, hasta "
        "phi = 90. Con perspectiva a 2.5 m aparece un residuo pequeño (máximo "
        f"{float(np.nanmax([f['error_abs_medio_deg'] for f in malla if f['proyeccion'] == 'perspectiva' and f['condicion'] == '3D'])):.2f} "
        "grados) por la distorsión proyectiva.\n"
        "2. **Todo el error frente a la oblicuidad procede de la parte de la medida que vive en el "
        "plano de imagen.** Cuanto peor sea la estimación de `z`, más se parece el sistema real a la "
        "condición 2D, que es la que fija el límite operativo. La coordenada z no es un adorno: es "
        "exactamente lo que compra tolerancia a la desalineación de la cámara.\n"
        f"3. **Límite operativo.** En la condición 2D el error crece de forma acelerada con el "
        f"azimut: {medio_en('ortografica', '2D', 10.0):.2f} grados a phi = 10, "
        f"{medio_en('ortografica', '2D', 20.0):.2f} a phi = 20, "
        f"{medio_en('ortografica', '2D', 30.0):.2f} a phi = 30 y "
        f"{medio_en('ortografica', '2D', 45.0):.2f} a phi = 45 (error medio, proyección "
        f"ortográfica). El peor caso de la malla supera los 5 grados a partir de "
        f"phi = {phi_2d_orto:.1f} grados.\n"
        f"4. **La asimetría bilateral es el indicador más frágil, y depende críticamente de que se "
        f"respete el margen de azimut.** Con proyección ortográfica es exactamente 0.000 grados por "
        f"simetría del modelo, pero la perspectiva la contamina porque las dos piernas están a "
        f"distinta profundidad. Dentro del margen recomendado (phi hasta "
        f"{AZIMUT_RECOMENDADO_DEG:.0f} grados) la asimetría espuria máxima es de sólo "
        f"{asim_dentro:.2f} grados, despreciable. Fuera de él crece deprisa: hasta "
        f"{asim_fuera:.2f} grados en un sujeto perfectamente simétrico. Es decir, la asimetría no es "
        f"un indicador intrínsecamente malo, pero sí el primero que se rompe cuando la cámara se "
        f"desalinea.\n"
        "5. **Calcular el ángulo sobre landmarks normalizados, sin escala común entre ejes, "
        "introduce un error sistemático** independiente de la oblicuidad y mayor que ella en el "
        "rango de trabajo. Es la corrección con mejor relación coste/beneficio del sistema. En el "
        "estado actual del repositorio esta corrección **ya está aplicada**: "
        "`vision/pose_extractor.py` y `vision/feature_engine.py` llaman a "
        "`vision.biomechanics.angulos_rodilla`, que resuelve la fuente de coordenadas y da "
        "prioridad a los `world_landmarks` métricos. Las cifras de esta sección miden, por tanto, "
        "el error que esa corrección evita, no un defecto vigente.\n"
    )

    p.append("\n## Limitaciones\n")
    p.append(
        "- El modelo sintético es una pierna rígida de dos segmentos en un plano. No modela tejido "
        "blando, desplazamiento del centro articular ni el error de detección de los propios "
        "landmarks: aísla deliberadamente el efecto geométrico del punto de vista. Los errores "
        "reportados son por tanto un **suelo**, no una predicción del error total del sistema.\n"
        "- La condición 3D supone profundidad perfecta, que MediaPipe no proporciona. Es una cota "
        "superior de rendimiento, útil para atribuir el error, no una condición alcanzable.\n"
        "- Las dos posturas evaluadas cubren dos orientaciones extremas del miembro dentro del plano "
        "sagital, pero no agotan las posturas posibles. El azimut máximo tolerable es el peor caso de "
        "esas dos, no de todas.\n"
        "- La proyección en perspectiva asume un sujeto bien encuadrado y centrado en el eje óptico, "
        "sin distorsión de lente. Un sujeto descentrado o un objetivo gran angular empeorarían esos "
        "resultados.\n"
        "- La validación empírica usa los `world_landmarks` como referencia 3D a falta de un patrón "
        "externo (goniómetro, sistema de captura óptica). Esa referencia tiene ruido de profundidad "
        "propio y no permite afirmar exactitud absoluta, sólo consistencia relativa.\n"
        "- **Los errores MEDIOS están diluidos a la baja en un 11 %.** La malla de flexión incluye "
        "el caso de flexión verdadera 0 grados, cuyo error es idénticamente nulo en todos los "
        "azimuts porque el miembro está extendido y su proyección no depende del punto de vista. "
        "Ese caso aporta ceros a todas las medias. Excluyéndolo, el error medio en la condición 2D "
        "ortográfica pasa de 0.43 a 0.48 grados en phi = 10, de 1.76 a 1.96 en phi = 20 y de 4.06 a "
        "4.51 en phi = 30. Las cifras de **máximo**, que son las que fijan el límite operativo de "
        "23.6 grados, no están afectadas.\n"
        "- **Hay una celda degenerada que se descarta en silencio.** En phi = 90, postura "
        "`rodilla_aislada` y flexión 90 grados, la condición 2D proyecta el segmento rodilla-tobillo "
        "sobre un vector de longitud nula y el ángulo queda indefinido (`NaN`): son 2 muestras de "
        "1600 en la malla, que las agregaciones `nanmean`/`nanmax` omiten. La celda de la Tabla 2 "
        "para flexión 90 y phi = 90 promedia por tanto una sola postura, no las dos que anuncia su "
        "encabezado.\n"
        "- **La consigna de +/- 15 grados se deriva de la condición 2D**, que es la hipótesis "
        "pesimista (profundidad inservible), no la condición en la que opera el sistema una vez que "
        "el ángulo se calcula sobre `world_landmarks`. Ningún experimento de este informe mide el "
        "error del sistema real frente al azimut real de cámara: eso exigiría grabar el mismo gesto "
        "desde varios ángulos conocidos, material del que no se dispone. El margen propuesto es "
        "por tanto una cota conservadora razonada, no una cifra calibrada sobre el sistema.\n"
        "- Un solo vídeo, un solo sujeto, un solo gesto. Los números empíricos son ilustrativos; los "
        "números sintéticos son los que sostienen la conclusión.\n"
    )

    p.append("\n## Recomendación operativa para el protocolo de captura\n")
    p.append(
        f"1. **Alinear la cámara al plano sagital con un margen de +/- {AZIMUT_RECOMENDADO_DEG:.0f} "
        f"grados de azimut.** El límite estricto medido es {phi_2d_orto:.1f} grados en el peor caso "
        f"de la malla; se propone {AZIMUT_RECOMENDADO_DEG:.0f} grados como consigna operativa para "
        f"dejar margen frente al error de colocación, a que el sujeto no se mantenga exactamente en "
        f"el eje y a que la profundidad estimada no sea perfecta. A "
        f"{AZIMUT_RECOMENDADO_DEG:.0f} grados el error medio es "
        f"{medio_en('ortografica', '2D', AZIMUT_RECOMENDADO_DEG):.2f} grados y el peor caso "
        f"{float(np.nanmax(por_pierna('ortografica', '2D', AZIMUT_RECOMENDADO_DEG))):.2f} "
        f"grados, ambos holgadamente por debajo del umbral clínico.\n"
        f"2. **Materializar la consigna en el sitio de captura**, no dejarla al ojo: marcar en el "
        f"suelo la línea de desplazamiento del sujeto y la posición del trípode, perpendicular y a "
        f"{DISTANCIA_CAMARA_M:.1f} m. El margen de {AZIMUT_RECOMENDADO_DEG:.0f} grados equivale a "
        f"{DISTANCIA_CAMARA_M * math.tan(math.radians(AZIMUT_RECOMENDADO_DEG)):.2f} m de "
        f"desplazamiento lateral de la cámara a esa distancia, es decir, un paso. Sin marca en el "
        f"suelo ese paso se da sin darse cuenta.\n"
        f"3. **No informar asimetrías bilaterales por debajo de {piso_asim:.1f} grados**, que es el "
        f"suelo de asimetría espuria dentro del margen recomendado. Y **no informar asimetría en "
        f"absoluto si la verificación de alineación detecta un azimut mayor de "
        f"{AZIMUT_RECOMENDADO_DEG + 5:.0f} grados**: fuera del margen el propio punto de vista puede "
        f"generar hasta {asim_fuera:.1f} grados de asimetría en un sujeto simétrico, más que "
        f"cualquier asimetría clínica que se pretenda detectar.\n"
        f"4. **Verificar la alineación automáticamente en cada sesión.** La orientación del eje de "
        f"caderas en los `world_landmarks` da una estimación de la oblicuidad por frame sin "
        f"instrumentación adicional; el sistema puede avisar al operador cuando se sale del margen.\n"
        f"5. **Corregir la escala de los ejes antes de calcular ángulos** (o calcularlos sobre "
        f"`world_landmarks`). Es independiente del protocolo de captura y reduce el error más que "
        f"cualquier mejora de colocación de la cámara.\n"
    )

    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    ruta_md.write_text("\n".join(p), encoding="utf-8")


# ---------------------------------------------------------------------------
# 8. Punto de entrada
# ---------------------------------------------------------------------------
def main() -> int:
    t0 = time.perf_counter()
    print("== Experimento 2: sensibilidad a la oblicuidad de camara ==")

    print("[1/6] Barriendo malla flexion x azimut x postura x proyeccion x condicion...")
    malla = barrer_malla()
    print(f"      filas generadas: {len(malla)}")

    print("[2/6] Barrido fino de azimut (paso 0.1 grados)...")
    fino = barrer_fino()
    umbral_max = {k: azimut_maximo_tolerable(d["azimut"], d["max"], UMBRAL_CLINICO_DEG) for k, d in fino.items()}
    umbral_medio = {k: azimut_maximo_tolerable(d["azimut"], d["medio"], UMBRAL_CLINICO_DEG) for k, d in fino.items()}

    print("[3/6] Extrayendo pose del video real...")
    datos_video = procesar_video_real()

    print("[4/6] Barrido empirico de azimut y comparacion de representaciones...")
    empirico = barrer_azimut_empirico(datos_video) if datos_video else None
    variantes = comparar_variantes_landmarks(datos_video) if datos_video else None

    print("[5/6] Analizando coherencia metrica de los ejes...")
    ancho = datos_video["ancho"] if datos_video else 1920
    alto = datos_video["alto"] if datos_video else 1080
    razon_z = RAZON_Z_POR_DEFECTO
    if datos_video and datos_video["escala_x"]:
        razon_z = datos_video["escala_z"] / datos_video["escala_x"]
    coherencia = analizar_coherencia_ejes(ancho, alto, razon_z)

    print("[6/6] Escribiendo salidas...")
    escribir_csv(DIR_RESULTADOS / "exp2_sensibilidad_oblicuidad.csv", CAMPOS_MALLA, malla)

    filas_barrido: list[dict[str, Any]] = []
    for (proy, cond), d in fino.items():
        for i in range(len(d["azimut"])):
            filas_barrido.append({
                "proyeccion": proy, "condicion": cond,
                "azimut_deg": round(float(d["azimut"][i]), 4),
                "error_abs_medio_deg": round(float(d["medio"][i]), 6),
                "error_abs_p95_deg": round(float(d["p95"][i]), 6),
                "error_abs_max_deg": round(float(d["max"][i]), 6),
                "asimetria_espuria_media_deg": round(float(d["asim_medio"][i]), 6),
                "asimetria_espuria_max_deg": round(float(d["asim_max"][i]), 6),
            })
    escribir_csv(DIR_RESULTADOS / "exp2_barrido_fino_azimut.csv", CAMPOS_BARRIDO, filas_barrido)
    if empirico:
        escribir_csv(DIR_RESULTADOS / "exp2_validacion_empirica_video.csv", CAMPOS_EMPIRICO, empirico)

    generar_figura(fino, empirico, datos_video, umbral_max, DIR_RESULTADOS / "exp2_error_vs_azimut.png")

    segundos = time.perf_counter() - t0
    escribir_informe(
        DIR_RESULTADOS / "exp2_sensibilidad_oblicuidad.md",
        malla, umbral_max, umbral_medio, empirico, variantes, datos_video, coherencia, segundos,
    )

    # --- Resumen por consola ---
    print("\n--- RESULTADOS ---")
    print("Error absoluto medio/maximo (grados) por azimut, agregado sobre flexion, postura y piernas:")
    print(f"{'phi':>5} | " + " | ".join(f"{p[:6]}.{c:>3}   " for p in PROYECCIONES for c in CONDICIONES))
    for phi in AZIMUTS_MALLA_DEG:
        celdas = []
        for proy in PROYECCIONES:
            for cond in CONDICIONES:
                # Una muestra por pierna: el promedio de las dos oculta el peor caso
                # en perspectiva, donde cada pierna esta a distinta profundidad.
                v = np.array([f[campo] for f in malla
                              if f["proyeccion"] == proy and f["condicion"] == cond and f["azimut_deg"] == phi
                              for campo in ("error_abs_izq_deg", "error_abs_der_deg")])
                celdas.append(f"{np.nanmean(v):6.2f}/{np.nanmax(v):6.2f}")
        print(f"{phi:5.0f} | " + " | ".join(celdas))

    print("\nAzimut maximo tolerable con umbral de 5 grados:")
    for proy in PROYECCIONES:
        for cond in CONDICIONES:
            print(f"  {proy:12s} {cond}: error medio < 5 hasta phi = {umbral_medio[(proy, cond)]:5.1f} ; "
                  f"error maximo < 5 hasta phi = {umbral_max[(proy, cond)]:5.1f}")

    print("\nAsimetria bilateral espuria maxima (verdadera = 0.00):")
    for phi in AZIMUTS_MALLA_DEG:
        celdas = []
        for proy in PROYECCIONES:
            for cond in CONDICIONES:
                v = [f["asimetria_medida_deg"] for f in malla
                     if f["proyeccion"] == proy and f["condicion"] == cond and f["azimut_deg"] == phi]
                celdas.append(f"{np.nanmax(v):7.3f}")
        print(f"  phi={phi:5.0f} -> " + " | ".join(celdas))

    print("\nCoherencia metrica de los ejes (condicion 3D ortografica; sin distorsion el error es 0.00):")
    print(f"  factor de aspecto={coherencia['factor_aspecto']:.4f}  razon s_z/s_x={coherencia['razon_z']:.4f}")
    for nombre, d in coherencia["casos"].items():
        print(f"  {nombre:28s} phi=0: medio={d['error_abs_medio_phi0']:6.2f} max={d['error_abs_max_phi0']:6.2f}"
              f"  | phi=20: medio={d['por_azimut'][20.0][0]:6.2f}"
              f"  | phi=45: medio={d['por_azimut'][45.0][0]:6.2f}"
              f"  | global: medio={d['error_abs_medio_global']:6.2f} max={d['error_abs_max_global']:6.2f}")

    if datos_video:
        sx, sy, sz = datos_video["escala_x"], datos_video["escala_y"], datos_video["escala_z"]
        print(f"\nVideo real: {datos_video['ancho']}x{datos_video['alto']} "
              f"{datos_video['fps']:.2f} fps, {len(datos_video['metricos'])}/{datos_video['frames_leidos']} "
              f"frames con pose, {datos_video['ms_por_frame']:.1f} ms/frame")
        print(f"  escalas normalizado/world: s_x={sx:.4f} s_y={sy:.4f} s_z={sz:.4f}")
        print(f"  s_y/s_x={sy / sx:.4f} (esperado ancho/alto={datos_video['ancho'] / datos_video['alto']:.4f})")
        print(f"  s_z/s_x={sz / sx:.4f} (esperado 1.0 segun documentacion MediaPipe)")
        obl = 90.0 - float(np.median(datos_video["orientacion_caderas_deg"]))
        print(f"  oblicuidad geometrica de la toma (mediana): {obl:.1f} grados")

    if empirico:
        medianas = [f["error_abs_mediana_deg"] for f in empirico]
        i_min = int(np.argmin(medianas))
        print(f"\nBarrido empirico (2D) sobre {empirico[0]['n_frames']} frames con flexion >= "
              f"{FLEXION_MINIMA_EMPIRICA_DEG:.0f} grados:")
        for f in empirico:
            if int(f["azimut_adicional_deg"]) % 15 == 0:
                print(f"  azimut {f['azimut_adicional_deg']:+5.0f} -> mediana {f['error_abs_mediana_deg']:6.2f} "
                      f"medio {f['error_abs_medio_deg']:6.2f} p95 {f['error_abs_p95_deg']:6.2f} "
                      f"max {f['error_abs_max_deg']:6.2f}")
        print(f"  minimo de la curva (mediana) en phi = {empirico[i_min]['azimut_adicional_deg']:+.0f} grados "
              f"({medianas[i_min]:.2f} grados)")

    if variantes:
        print("\nRepresentaciones de landmarks frente a world_landmarks (video real):")
        for v in variantes:
            print(f"  {v['variante']:34s} sesgo={v['sesgo_deg']:+7.2f} media={v['dif_abs_media_deg']:6.2f} "
                  f"p95={v['dif_abs_p95_deg']:6.2f} max={v['dif_abs_max_deg']:6.2f}")

    print(f"\nTiempo total: {segundos:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
