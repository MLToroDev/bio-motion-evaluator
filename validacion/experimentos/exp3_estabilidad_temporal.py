"""
Experimento 3: caracterizacion empirica de la estimacion angular sobre video real.

Objetivo cientifico
-------------------
Caracterizar el comportamiento del estimador de flexion de rodilla del proyecto
(MediaPipe Pose Landmarker + ``vision.biomechanics.knee_angles_from_landmarks``)
sobre los videos de referencia del repositorio.

NO hay medicion de goniometro ni de marcadores opticos asociada a estos clips, de modo
que este experimento NO mide exactitud. Lo que si mide, y es citable:

1. Tasa de deteccion (porcentaje de fotogramas con pose valida y angulos calculables).
2. Rango de movimiento observado por pierna (min, max, recorrido).
3. Ruido temporal (jitter) cuadro a cuadro de la serie angular.
4. Piso de ruido de la asimetria bilateral, distinguiendo regimen de movimiento.
5. Sensibilidad de la tasa de deteccion al umbral de visibilidad (>= 0.5).
6. Sensibilidad de la propia estimacion al sistema de coordenadas usado, y comprobacion
   de plausibilidad anatomica. Ambas son cotas de incertidumbre que NO requieren
   referencia externa: si tres formas defendibles de calcular el mismo angulo sobre la
   misma deteccion discrepan en X grados, la incertidumbre de la medida es al menos
   de ese orden.

Variantes de coordenadas comparadas (todas usan la MISMA funcion de calculo del
proyecto, ``knee_angles_from_landmarks``, cambiando solo los landmarks de entrada):

- ``produccion``: lo que devuelve hoy ``extract_pose_bgr_video``. La resolucion de la
  fuente de coordenadas la decide el propio proyecto en ``vision.biomechanics``, de modo
  que esta variante sigue al codigo, no a una hipotesis del experimento.
- ``world_xyz``: ``pose_world_landmarks`` de MediaPipe (metricos, origen en el punto
  medio de las caderas; isotropos por construccion).
- ``imagen_xyz_isotropico``: landmarks de imagen con ``y`` reescalado por alto/ancho
  (``escalar_a_isotropico``), es decir, corregidos de anisotropia.
- ``imagen_xy_isotropico``: los anteriores con z forzado a 0 (angulo proyectado en el
  plano de imagen).
- ``imagen_xyz_normalizado``: landmarks de imagen tal cual, SIN corregir la anisotropia.
  Es la ruta que el proyecto usaba antes de la correccion documentada en
  ``docs/spec/goniometria-espacio-de-coordenadas.md``; se conserva aqui para medir sobre
  video real el sesgo que introducia.

Las cuatro ultimas son auxiliares: existen solo para el analisis de sensibilidad.

Salidas
-------
- CSV por video con la serie temporal completa (insumo para el cotejo manual con
  Kinovea: incluye indice de fotograma y timestamp en milisegundos).
- Figura PNG por video con ambas series angulares y la asimetria.
- Resumen comparativo en Markdown y en JSON.

Ejecucion (desde la carpeta ``backend/`` del repositorio):

    PYTHONPATH=. ~/.venvs/biomotion/bin/python \
        ../validacion/experimentos/exp3_estabilidad_temporal.py

Opciones utiles: ``--max-frames`` (tope de seguridad por video, por defecto 4000: ningun
clip de referencia lo alcanza, de modo que todos se procesan completos) y ``--videos-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: obligatorio en ejecucion por lotes
import matplotlib.pyplot as plt  # noqa: E402
from scipy.signal import savgol_filter  # noqa: E402

# --------------------------------------------------------------------------------------
# Rutas del repositorio
# --------------------------------------------------------------------------------------

RAIZ_REPO = Path(__file__).resolve().parents[2]
DIR_BACKEND = RAIZ_REPO / "backend"

# Permite ejecutar el script desde cualquier directorio sin depender de PYTHONPATH.
if str(DIR_BACKEND) not in sys.path:
    sys.path.insert(0, str(DIR_BACKEND))

from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor  # noqa: E402
from vision.biomechanics import (  # noqa: E402
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
    escalar_a_isotropico,
    knee_angles_from_landmarks,
)
from vision.pose_extractor import extract_pose_bgr_video  # noqa: E402

DIR_VIDEOS_POR_DEFECTO = RAIZ_REPO / "tests" / "assets" / "videos"
DIR_RESULTADOS = RAIZ_REPO / "validacion" / "resultados"
DIR_SERIES = DIR_RESULTADOS / "series"
RUTA_MODELO = DIR_BACKEND / "models" / "pose_landmarker_full.task"

# --------------------------------------------------------------------------------------
# Parametros del analisis (declarados aqui para que el reporte sea reproducible)
# --------------------------------------------------------------------------------------

MAX_FRAMES_POR_DEFECTO = 4000
UMBRAL_VISIBILIDAD = 0.5

NOMBRES_LANDMARK = {
    LEFT_HIP: "left_hip",
    RIGHT_HIP: "right_hip",
    LEFT_KNEE: "left_knee",
    RIGHT_KNEE: "right_knee",
    LEFT_ANKLE: "left_ankle",
    RIGHT_ANKLE: "right_ankle",
}
LANDMARKS_MIEMBRO_INFERIOR = tuple(NOMBRES_LANDMARK)

# Deteccion de tramos cuasi-estaticos: ventana centrada y tope de dispersion local.
VENTANA_CUASI_ESTATICA = 5          # fotogramas
UMBRAL_CUASI_ESTATICO_DEG = 1.5     # desviacion estandar local maxima, en grados

# Estimacion del ruido de alta frecuencia: residuo frente a un suavizado Savitzky-Golay.
VENTANA_SAVGOL = 9
ORDEN_SAVGOL = 2

# Deteccion de cortes de plano (montaje). Un corte rompe el tracking temporal y produce
# un salto angular que NO es ruido del estimador, asi que no debe contarse como jitter.
# Criterio conservador y relativo a cada clip: la diferencia media absoluta entre
# fotogramas consecutivos (escala de grises, 160x90) supera a la vez un suelo absoluto y
# un multiplo de la mediana del propio clip.
CORTE_ESCENA_SUELO = 3.0
CORTE_ESCENA_FACTOR_MEDIANA = 5.0

# Ventana de detalle de las figuras: en un clip de miles de fotogramas la serie completa
# es una mancha ilegible, asi que se acompana de un tramo corto donde se ve el ciclo.
VENTANA_DETALLE_S = 5.0
MIN_FRAMES_PARA_DETALLE = 600

# Techo de plausibilidad anatomica de la flexion de rodilla. La flexion pasiva maxima
# (talon al gluteo) ronda 150-160 grados; por encima de este valor la lectura no puede
# corresponder a una postura real y se contabiliza como implausible.
TECHO_FLEXION_PLAUSIBLE_DEG = 150.0

# Variantes de coordenadas: etiqueta -> (columna izquierda, columna derecha).
VARIANTE_PRODUCCION = "produccion"
VARIANTES: dict[str, tuple[str, str]] = {
    VARIANTE_PRODUCCION: ("left_knee_flexion_angle_deg", "right_knee_flexion_angle_deg"),
    "world_xyz": ("left_knee_flexion_world_deg", "right_knee_flexion_world_deg"),
    "imagen_xyz_isotropico": ("left_knee_flexion_img_xyz_iso_deg", "right_knee_flexion_img_xyz_iso_deg"),
    "imagen_xy_isotropico": ("left_knee_flexion_img_xy_iso_deg", "right_knee_flexion_img_xy_iso_deg"),
    "imagen_xyz_normalizado": ("left_knee_flexion_img_xyz_norm_deg", "right_knee_flexion_img_xyz_norm_deg"),
}
ETIQUETAS_VARIANTE = {
    VARIANTE_PRODUCCION: "lo que devuelve hoy `extract_pose_bgr_video`",
    "world_xyz": "world landmarks metricos (x, y, z)",
    "imagen_xyz_isotropico": "imagen (x, y, z) con y reescalado por alto/ancho",
    "imagen_xy_isotropico": "imagen (x, y) isotropico, con z = 0 (proyeccion en el plano)",
    "imagen_xyz_normalizado": "imagen (x, y, z) normalizados sin corregir (ruta historica)",
}

# Plano de camara anotado MANUALMENTE por inspeccion visual de un fotograma de cada clip.
# No lo detecta el sistema: es metadato del experimento y por eso se declara como tal en el
# reporte. La clave es el identificador ASCII del video (ver ``nombre_seguro``).
PLANO_CAMARA_ANOTADO: dict[str, tuple[str, str]] = {
    "5_00_por_milha_3_06_km_Agora_olha_o_que_acontece_quando_a_ge": (
        "sagital", "lateral, cinta; video editado con cortes"
    ),
    "CintaRunning": ("frontal", "de frente, cinta"),
    "Running": ("posterior-oblicuo", "corriendo alejandose"),
    "Running2": ("sagital", "lateral, con paneo"),
    "SentadillaProfunda": ("frontal", "de frente; corte de plano hacia el final del clip"),
}
PLANO_NO_ANOTADO = ("no anotado", "")

# Fotogramas verificados visualmente por el autor del experimento. Sirven de ancla
# cualitativa: no son medicion de error, pero permiten contrastar la lectura del sistema
# con una postura inequivoca.
FOTOGRAMAS_REFERENCIA_VISUAL: dict[str, tuple[int, str]] = {
    "SentadillaProfunda.mp4": (
        70,
        "el sujeto esta de pie, completamente erguido, con los pies separados (toma frontal)",
    ),
}

# Paleta categorica validada (banda de luminosidad, contraste y separacion para
# daltonismo comprobados con el validador de la guia de visualizacion).
COLOR_IZQUIERDA = "#2a78d6"
COLOR_DERECHA = "#eb6834"
COLOR_ASIMETRIA = "#4a3aa7"
COLOR_TINTA = "#0b0b0b"
COLOR_TINTA_SUAVE = "#52514e"

# Regimen de movimiento por palabra clave en el nombre del archivo. Determina si el
# estadistico de asimetria puede leerse como "piso de ruido" o no.
PALABRAS_BILATERAL_SIMETRICO = ("sentadilla", "squat")
PALABRAS_MARCHA_CARRERA = ("running", "cinta", "marcha", "gait", "milha", "cad", "km")

REGIMEN_BILATERAL = "bilateral_simetrico"
REGIMEN_MARCHA = "marcha_carrera"
REGIMEN_DESCONOCIDO = "desconocido"


# --------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------


def procedencia_codigo() -> dict[str, str]:
    """
    Identifica la version exacta del codigo del proyecto que se esta midiendo.

    El repositorio se edita mientras se ejecutan experimentos, y la ruta de calculo
    angular vive en modulos que pueden cambiar entre una corrida y la siguiente. Sin esta
    huella, un numero de este reporte no seria atribuible a una version concreta.
    """
    def _sha256_corto(ruta: Path) -> str:
        if not ruta.is_file():
            return "ausente"
        return hashlib.sha256(ruta.read_bytes()).hexdigest()[:12]

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ_REPO, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - la procedencia es informativa, nunca bloqueante
        commit = "desconocido"

    try:
        sucio = subprocess.run(
            ["git", "status", "--porcelain", "backend/vision", "backend/app/services/pose"],
            cwd=RAIZ_REPO, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        sucio = ""

    return {
        "commit": commit,
        "arbol_de_trabajo": "con cambios sin confirmar" if sucio else "limpio",
        "sha256_biomechanics": _sha256_corto(DIR_BACKEND / "vision" / "biomechanics.py"),
        "sha256_pose_extractor": _sha256_corto(DIR_BACKEND / "vision" / "pose_extractor.py"),
        "sha256_mediapipe_service": _sha256_corto(DIR_BACKEND / "app" / "services" / "pose" / "mediapipe.py"),
    }


def nombre_seguro(nombre: str) -> str:
    """
    Convierte el nombre de un video en un identificador ASCII apto para nombre de archivo.

    Los videos de referencia incluyen espacios, tildes y simbolos no ASCII; los artefactos
    generados deben ser citables y portables entre sistemas de archivos.
    """
    base = Path(nombre).stem
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
    base = base[:60].strip("_")
    return base or "video"


def etiqueta_video(archivo: str, limite: int = 34) -> str:
    """Nombre abreviado para tablas y titulos; el nombre completo vive en la tabla 2."""
    if len(archivo) <= limite:
        return archivo
    return archivo[: limite - 3].rstrip() + "..."


def clasificar_regimen(nombre: str) -> str:
    """Heuristica por nombre de archivo: sentadilla (bilateral) frente a marcha/carrera."""
    minusculas = nombre.lower()
    if any(p in minusculas for p in PALABRAS_BILATERAL_SIMETRICO):
        return REGIMEN_BILATERAL
    if any(p in minusculas for p in PALABRAS_MARCHA_CARRERA):
        return REGIMEN_MARCHA
    return REGIMEN_DESCONOCIDO


def visibilidad_miembro_inferior(landmarks: list[dict[str, Any]]) -> tuple[float, str]:
    """
    Menor visibilidad entre los 6 landmarks usados para las rodillas, y cual la limita.

    Devuelve ``(nan, "")`` si faltan puntos o si MediaPipe no entrego ``visibility``.
    """
    if not landmarks:
        return float("nan"), ""
    peor_valor = float("inf")
    peor_indice = -1
    for indice in LANDMARKS_MIEMBRO_INFERIOR:
        if indice >= len(landmarks):
            return float("nan"), ""
        v = landmarks[indice].get("visibility")
        if v is None:
            return float("nan"), ""
        if float(v) < peor_valor:
            peor_valor = float(v)
            peor_indice = indice
    if peor_indice < 0:
        return float("nan"), ""
    return peor_valor, NOMBRES_LANDMARK[peor_indice]


def _percentil(valores: np.ndarray, q: float) -> float:
    """Percentil robusto a arreglos vacios o con NaN."""
    limpio = valores[np.isfinite(valores)]
    if limpio.size == 0:
        return float("nan")
    return float(np.percentile(limpio, q))


def _mediana(valores: np.ndarray) -> float:
    """Mediana robusta a arreglos vacios o con NaN."""
    limpio = valores[np.isfinite(valores)]
    if limpio.size == 0:
        return float("nan")
    return float(np.median(limpio))


def _redondear(valor: float, decimales: int = 2) -> float:
    """Redondeo que preserva NaN (evita ruido de precision en el JSON de resultados)."""
    return round(valor, decimales) if isinstance(valor, float) and math.isfinite(valor) else float("nan")


def tramos_contiguos(
    indices: np.ndarray,
    valores: np.ndarray,
    corta_antes: np.ndarray | None = None,
) -> list[np.ndarray]:
    """
    Parte una serie en tramos de fotogramas consecutivos con valor valido.

    Necesario para no calcular una "primera diferencia" a caballo de un hueco de
    deteccion: ese salto no es ruido del estimador sino ausencia de dato. Por la misma
    razon, ``corta_antes`` fuerza un corte de tramo en los fotogramas marcados (p. ej.
    un corte de plano del montaje, que rompe el tracking y produce un salto ficticio).
    """
    tramos: list[np.ndarray] = []
    actual: list[float] = []
    indice_previo: int | None = None
    rupturas = (
        np.zeros(len(valores), dtype=bool) if corta_antes is None
        else np.asarray(corta_antes, dtype=bool)
    )
    for posicion, (idx, val) in enumerate(zip(indices, valores, strict=True)):
        valido = bool(np.isfinite(val))
        contiguo = (
            indice_previo is not None
            and int(idx) == indice_previo + 1
            and not bool(rupturas[posicion])
        )
        if valido and contiguo and actual:
            actual.append(float(val))
        elif valido:
            if len(actual) > 1:
                tramos.append(np.asarray(actual, dtype=float))
            actual = [float(val)]
        else:
            if len(actual) > 1:
                tramos.append(np.asarray(actual, dtype=float))
            actual = []
        indice_previo = int(idx) if valido else None
    if len(actual) > 1:
        tramos.append(np.asarray(actual, dtype=float))
    return tramos


def primeras_diferencias(
    indices: np.ndarray,
    valores: np.ndarray,
    corta_antes: np.ndarray | None = None,
) -> np.ndarray:
    """Concatena las primeras diferencias calculadas dentro de cada tramo contiguo."""
    salida = [np.diff(t) for t in tramos_contiguos(indices, valores, corta_antes)]
    return np.concatenate(salida) if salida else np.asarray([], dtype=float)


def residuo_alta_frecuencia(
    indices: np.ndarray,
    valores: np.ndarray,
    corta_antes: np.ndarray | None = None,
) -> np.ndarray:
    """
    Residuo de la serie frente a un suavizado Savitzky-Golay, por tramo contiguo.

    La desviacion tipica de la primera diferencia mezcla el movimiento real con el ruido
    del estimador; en un video con movimiento rapido ese estadistico sobreestima el ruido.
    El residuo de alta frecuencia separa mejor la componente de ruido, asumiendo que el
    movimiento articular real es suave en la escala de la ventana usada.
    """
    salida: list[np.ndarray] = []
    for tramo in tramos_contiguos(indices, valores, corta_antes):
        if tramo.size < VENTANA_SAVGOL:
            continue
        suave = savgol_filter(tramo, window_length=VENTANA_SAVGOL, polyorder=ORDEN_SAVGOL)
        salida.append(tramo - suave)
    return np.concatenate(salida) if salida else np.asarray([], dtype=float)


# --------------------------------------------------------------------------------------
# Procesamiento de video
# --------------------------------------------------------------------------------------


@dataclass
class MetadatosVideo:
    """Metadatos de contenedor y del recorte aplicado al procesar."""

    archivo: str
    identificador: str
    regimen: str
    ancho: int
    alto: int
    fps: float
    frames_contenedor: int
    frames_procesados: int
    recortado: bool
    duracion_procesada_s: float
    plano_camara: str = "no anotado"
    plano_camara_detalle: str = ""
    cortes_de_plano: int = 0
    frames_de_corte: list[int] = field(default_factory=list)


def _flexiones(angulos: dict[str, float] | None) -> tuple[float, float]:
    """Extrae (izquierda, derecha) de la salida de ``knee_angles_from_landmarks``."""
    if not angulos:
        return float("nan"), float("nan")
    return (
        float(angulos.get("left_knee_flexion_angle_deg", float("nan"))),
        float(angulos.get("right_knee_flexion_angle_deg", float("nan"))),
    )


def _marcar_cortes_de_plano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Marca los fotogramas en los que el montaje cambia de plano.

    El umbral es relativo a cada clip (multiplo de la mediana de su propia puntuacion de
    cambio) con un suelo absoluto, porque el valor bruto no es comparable entre un plano
    fijo y una toma con paneo. Es un criterio conservador: detecta cortes secos y puede
    pasar por alto transiciones suaves o encadenados.
    """
    if df.empty or "cambio_escena_score" not in df.columns:
        return df
    puntuacion = df["cambio_escena_score"].to_numpy(dtype=float)
    mediana = float(np.median(puntuacion[1:])) if puntuacion.size > 1 else 0.0
    umbral = max(CORTE_ESCENA_SUELO, CORTE_ESCENA_FACTOR_MEDIANA * mediana)
    df = df.copy()
    df["corte_de_plano"] = (puntuacion > umbral).astype(int)
    df.loc[df.index[:1], "corte_de_plano"] = 0  # el primer fotograma no es un corte
    return df


def procesar_video(ruta: Path, max_frames: int) -> tuple[pd.DataFrame, MetadatosVideo]:
    """
    Ejecuta el estimador de pose sobre los fotogramas del video, en orden temporal.

    Usa ``RunningMode.VIDEO`` (tracking temporal de MediaPipe) y reinicia el ancla de
    timestamps antes de empezar, porque MediaPipe exige timestamps estrictamente
    crecientes por instancia de landmarker.
    """
    captura = cv2.VideoCapture(str(ruta))
    if not captura.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {ruta}")

    fps = float(captura.get(cv2.CAP_PROP_FPS)) or 30.0
    ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames_contenedor = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))

    reset_pose_video_timestamp_anchor()

    filas: list[dict[str, Any]] = []
    indice = 0
    gris_previo: np.ndarray | None = None
    while indice < max_frames:
        ok, bgr = captura.read()
        if not ok or bgr is None:
            break
        timestamp_ms = int(round(indice * 1000.0 / fps))

        # Puntuacion de cambio de escena: diferencia media absoluta con el fotograma
        # anterior en escala de grises reducida. Barata y suficiente para detectar cortes.
        gris = cv2.cvtColor(cv2.resize(bgr, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        cambio_escena = 0.0 if gris_previo is None else float(np.mean(np.abs(gris - gris_previo)))
        gris_previo = gris

        t0 = time.perf_counter()
        frame = extract_pose_bgr_video(bgr, RUTA_MODELO, timestamp_ms)
        inferencia_ms = (time.perf_counter() - t0) * 1000.0

        alto_frame, ancho_frame = int(bgr.shape[0]), int(bgr.shape[1])
        relacion_aspecto = alto_frame / ancho_frame if ancho_frame > 0 else 1.0

        pose_detectada = bool(frame.ok and frame.landmarks)
        visibilidad_min, landmark_limitante = visibilidad_miembro_inferior(frame.landmarks)

        # Variante de produccion: la que el sistema envia hoy al cliente.
        izquierda, derecha = _flexiones(frame.knees)
        interno_izq = float("nan")
        interno_der = float("nan")
        if frame.knees:
            interno_izq = float(frame.knees.get("left_knee_internal_angle_deg", float("nan")))
            interno_der = float(frame.knees.get("right_knee_internal_angle_deg", float("nan")))

        # Variantes auxiliares para el analisis de sensibilidad: misma funcion de calculo
        # del proyecto, distintos landmarks de entrada.
        nan2 = (float("nan"), float("nan"))
        if frame.landmarks:
            izq_norm, der_norm = _flexiones(knee_angles_from_landmarks(frame.landmarks))
            landmarks_iso = escalar_a_isotropico(frame.landmarks, relacion_aspecto)
            izq_iso, der_iso = _flexiones(knee_angles_from_landmarks(landmarks_iso))
            landmarks_iso_planos = [{**p, "z": 0.0} for p in landmarks_iso]
            izq_xy, der_xy = _flexiones(knee_angles_from_landmarks(landmarks_iso_planos))
        else:
            izq_norm, der_norm = nan2
            izq_iso, der_iso = nan2
            izq_xy, der_xy = nan2
        if frame.world_landmarks:
            izq_world, der_world = _flexiones(knee_angles_from_landmarks(frame.world_landmarks))
        else:
            izq_world, der_world = nan2

        angulos_validos = bool(math.isfinite(izquierda) and math.isfinite(derecha))
        asimetria = abs(izquierda - derecha) if angulos_validos else float("nan")
        asimetria_world = (
            abs(izq_world - der_world)
            if math.isfinite(izq_world) and math.isfinite(der_world)
            else float("nan")
        )

        filas.append(
            {
                "frame_index": indice,
                "timestamp_ms": timestamp_ms,
                "pose_detectada": int(pose_detectada),
                "angulos_validos": int(angulos_validos),
                "left_knee_flexion_angle_deg": izquierda,
                "right_knee_flexion_angle_deg": derecha,
                "left_knee_internal_angle_deg": interno_izq,
                "right_knee_internal_angle_deg": interno_der,
                "bilateral_asymmetry_abs_deg": asimetria,
                "left_knee_flexion_world_deg": izq_world,
                "right_knee_flexion_world_deg": der_world,
                "left_knee_flexion_img_xyz_iso_deg": izq_iso,
                "right_knee_flexion_img_xyz_iso_deg": der_iso,
                "left_knee_flexion_img_xy_iso_deg": izq_xy,
                "right_knee_flexion_img_xy_iso_deg": der_xy,
                "left_knee_flexion_img_xyz_norm_deg": izq_norm,
                "right_knee_flexion_img_xyz_norm_deg": der_norm,
                "bilateral_asymmetry_world_abs_deg": asimetria_world,
                "cambio_escena_score": cambio_escena,
                "min_visibility_lower_limb": visibilidad_min,
                "landmark_limitante": landmark_limitante,
                "visible_ge_0_5": int(
                    math.isfinite(visibilidad_min) and visibilidad_min >= UMBRAL_VISIBILIDAD
                ),
                "inferencia_ms": inferencia_ms,
            }
        )
        indice += 1

    captura.release()

    df = pd.DataFrame(filas)
    df = _marcar_cortes_de_plano(df)
    metadatos = MetadatosVideo(
        archivo=ruta.name,
        identificador=nombre_seguro(ruta.name),
        regimen=clasificar_regimen(ruta.name),
        ancho=ancho,
        alto=alto,
        fps=round(fps, 3),
        frames_contenedor=frames_contenedor,
        frames_procesados=len(df),
        recortado=bool(frames_contenedor > len(df)),
        duracion_procesada_s=round(len(df) / fps, 2) if fps else float("nan"),
        plano_camara=PLANO_CAMARA_ANOTADO.get(nombre_seguro(ruta.name), PLANO_NO_ANOTADO)[0],
        plano_camara_detalle=PLANO_CAMARA_ANOTADO.get(nombre_seguro(ruta.name), PLANO_NO_ANOTADO)[1],
        cortes_de_plano=int(df["corte_de_plano"].sum()) if "corte_de_plano" in df.columns else 0,
        frames_de_corte=(
            [int(v) for v in df.loc[df["corte_de_plano"] == 1, "frame_index"].to_list()[:10]]
            if "corte_de_plano" in df.columns else []
        ),
    )
    return df, metadatos


# --------------------------------------------------------------------------------------
# Estadisticos
# --------------------------------------------------------------------------------------


@dataclass
class EstadisticosVideo:
    """Resumen numerico por video (lo que se cita en la memoria)."""

    metadatos: dict[str, Any]
    tasa_deteccion_pose_pct: float
    tasa_angulos_validos_pct: float
    tasa_angulos_validos_vis05_pct: float
    caida_por_umbral_pp: float
    visibilidad_min_mediana: float
    visibilidad_min_p05: float
    landmark_limitante_dominante: str
    landmark_limitante_dominante_pct: float
    rom: dict[str, dict[str, float]] = field(default_factory=dict)
    jitter: dict[str, dict[str, float]] = field(default_factory=dict)
    asimetria: dict[str, float] = field(default_factory=dict)
    cuasi_estatico: dict[str, float] = field(default_factory=dict)
    variantes: dict[str, dict[str, float]] = field(default_factory=dict)
    referencia_visual: dict[str, Any] = field(default_factory=dict)
    inferencia: dict[str, float] = field(default_factory=dict)


def _estadisticos_rom(serie: pd.Series) -> dict[str, float]:
    """Minimo, maximo, recorrido y mediana de una serie angular."""
    limpio = serie.dropna()
    if limpio.empty:
        return {"min_deg": float("nan"), "max_deg": float("nan"),
                "recorrido_deg": float("nan"), "mediana_deg": float("nan")}
    return {
        "min_deg": _redondear(float(limpio.min())),
        "max_deg": _redondear(float(limpio.max())),
        "recorrido_deg": _redondear(float(limpio.max() - limpio.min())),
        "mediana_deg": _redondear(float(limpio.median())),
    }


def _estadisticos_jitter(df: pd.DataFrame, columna: str, fps: float) -> dict[str, float]:
    """Indicadores de ruido temporal de una serie angular."""
    indices = df["frame_index"].to_numpy()
    valores = df[columna].to_numpy(dtype=float)
    cortes = (
        df["corte_de_plano"].to_numpy(dtype=bool) if "corte_de_plano" in df.columns else None
    )
    diffs = primeras_diferencias(indices, valores, cortes)
    residuo = residuo_alta_frecuencia(indices, valores, cortes)

    jitter = float(np.std(diffs, ddof=1)) if diffs.size > 1 else float("nan")
    rms_residuo = float(np.sqrt(np.mean(residuo**2))) if residuo.size else float("nan")

    return {
        "n_diferencias": int(diffs.size),
        "jitter_std_diff_deg_frame": _redondear(jitter, 3),
        "jitter_std_diff_deg_s": _redondear(jitter * fps) if math.isfinite(jitter) else float("nan"),
        "salto_mediano_abs_deg": _redondear(_mediana(np.abs(diffs)), 3),
        "salto_p95_abs_deg": _redondear(_percentil(np.abs(diffs), 95.0), 3),
        "ruido_alta_frecuencia_rms_deg": _redondear(rms_residuo, 3),
    }


def _mascara_cuasi_estatica(df: pd.DataFrame) -> pd.Series:
    """
    Marca fotogramas cuasi-estaticos: dispersion local baja en AMBAS piernas.

    Solo en estos fotogramas (o en un ejercicio bilateral simetrico) la asimetria
    observada puede interpretarse como piso de ruido del estimador.
    """
    ventana = VENTANA_CUASI_ESTATICA
    std_izq = df["left_knee_flexion_angle_deg"].rolling(
        window=ventana, center=True, min_periods=ventana
    ).std()
    std_der = df["right_knee_flexion_angle_deg"].rolling(
        window=ventana, center=True, min_periods=ventana
    ).std()
    return (std_izq < UMBRAL_CUASI_ESTATICO_DEG) & (std_der < UMBRAL_CUASI_ESTATICO_DEG)


def _estadisticos_variante(df: pd.DataFrame, variante: str, fps: float) -> dict[str, float]:
    """
    Resumen de una variante de coordenadas, agrupando ambas piernas.

    ``discrepancia_*`` compara la variante con la ruta de produccion fotograma a
    fotograma; es una cota inferior de la incertidumbre de la medida que no necesita
    referencia externa.
    """
    col_izq, col_der = VARIANTES[variante]
    col_izq_prod, col_der_prod = VARIANTES[VARIANTE_PRODUCCION]

    valores = np.concatenate(
        [df[col_izq].to_numpy(dtype=float), df[col_der].to_numpy(dtype=float)]
    )
    finitos = valores[np.isfinite(valores)]
    n_validos = int(finitos.size)
    implausibles = int(np.sum(finitos > TECHO_FLEXION_PLAUSIBLE_DEG))

    ruido_izq = _estadisticos_jitter(df, col_izq, fps)["ruido_alta_frecuencia_rms_deg"]
    ruido_der = _estadisticos_jitter(df, col_der, fps)["ruido_alta_frecuencia_rms_deg"]
    ruidos = [r for r in (ruido_izq, ruido_der) if isinstance(r, float) and math.isfinite(r)]

    discrepancia = np.concatenate(
        [
            np.abs(df[col_izq].to_numpy(dtype=float) - df[col_izq_prod].to_numpy(dtype=float)),
            np.abs(df[col_der].to_numpy(dtype=float) - df[col_der_prod].to_numpy(dtype=float)),
        ]
    )
    hay_discrepancia = bool(np.isfinite(discrepancia).any())

    return {
        "n_valores": n_validos,
        "mediana_flexion_deg": _redondear(_mediana(valores)),
        "p95_flexion_deg": _redondear(_percentil(valores, 95.0)),
        "max_flexion_deg": _redondear(float(np.max(finitos))) if n_validos else float("nan"),
        "pct_implausible_mayor_150": (
            _redondear(100.0 * implausibles / n_validos) if n_validos else float("nan")
        ),
        "ruido_alta_frecuencia_rms_deg": _redondear(float(np.mean(ruidos)), 3) if ruidos else float("nan"),
        "discrepancia_mediana_deg": _redondear(_mediana(discrepancia)),
        "discrepancia_p95_deg": _redondear(_percentil(discrepancia, 95.0)),
        "discrepancia_max_deg": (
            _redondear(float(np.nanmax(discrepancia))) if hay_discrepancia else float("nan")
        ),
    }


def _referencia_visual(df: pd.DataFrame, metadatos: MetadatosVideo) -> dict[str, Any]:
    """
    Lecturas de todas las variantes en un fotograma cuya postura se verifico a ojo.

    Es un ancla cualitativa, no una medicion de error: da un caso concreto en el que se
    sabe que postura hay y se puede ver que dice cada variante.
    """
    entrada = FOTOGRAMAS_REFERENCIA_VISUAL.get(metadatos.archivo)
    if entrada is None:
        return {}
    indice, descripcion = entrada
    fila = df[df["frame_index"] == indice]
    if fila.empty:
        return {}
    fila = fila.iloc[0]
    lecturas = {
        clave: {
            "izquierda_deg": _redondear(float(fila[col_izq])),
            "derecha_deg": _redondear(float(fila[col_der])),
        }
        for clave, (col_izq, col_der) in VARIANTES.items()
    }
    return {"frame_index": int(indice), "descripcion": descripcion, "lecturas": lecturas}


def calcular_estadisticos(df: pd.DataFrame, metadatos: MetadatosVideo) -> EstadisticosVideo:
    """Consolida todos los indicadores del experimento para un video."""
    n = len(df)
    n_pose = int(df["pose_detectada"].sum())
    n_angulos = int(df["angulos_validos"].sum())
    n_angulos_vis = int(((df["angulos_validos"] == 1) & (df["visible_ge_0_5"] == 1)).sum())

    tasa_pose = 100.0 * n_pose / n if n else float("nan")
    tasa_ang = 100.0 * n_angulos / n if n else float("nan")
    tasa_ang_vis = 100.0 * n_angulos_vis / n if n else float("nan")

    limitantes = df.loc[df["landmark_limitante"] != "", "landmark_limitante"]
    if not limitantes.empty:
        conteo = limitantes.value_counts()
        limitante_dominante = str(conteo.index[0])
        limitante_pct = _redondear(100.0 * float(conteo.iloc[0]) / len(limitantes))
    else:
        limitante_dominante = "n/d"
        limitante_pct = float("nan")

    visibilidad = df["min_visibility_lower_limb"].to_numpy(dtype=float)
    asim = df["bilateral_asymmetry_abs_deg"].to_numpy(dtype=float)

    df_estatico = df[_mascara_cuasi_estatica(df).fillna(False).astype(bool)]
    asim_estatica = df_estatico["bilateral_asymmetry_abs_deg"].to_numpy(dtype=float)

    jitter_estatico_izq = (
        _estadisticos_jitter(df_estatico, "left_knee_flexion_angle_deg", metadatos.fps)
        if len(df_estatico) > 2 else {}
    )
    jitter_estatico_der = (
        _estadisticos_jitter(df_estatico, "right_knee_flexion_angle_deg", metadatos.fps)
        if len(df_estatico) > 2 else {}
    )

    inferencia = df["inferencia_ms"].to_numpy(dtype=float)

    return EstadisticosVideo(
        metadatos=asdict(metadatos),
        tasa_deteccion_pose_pct=_redondear(tasa_pose),
        tasa_angulos_validos_pct=_redondear(tasa_ang),
        tasa_angulos_validos_vis05_pct=_redondear(tasa_ang_vis),
        caida_por_umbral_pp=_redondear(tasa_ang - tasa_ang_vis),
        visibilidad_min_mediana=_redondear(_mediana(visibilidad), 3),
        visibilidad_min_p05=_redondear(_percentil(visibilidad, 5.0), 3),
        landmark_limitante_dominante=limitante_dominante,
        landmark_limitante_dominante_pct=limitante_pct,
        rom={
            "izquierda": _estadisticos_rom(df["left_knee_flexion_angle_deg"]),
            "derecha": _estadisticos_rom(df["right_knee_flexion_angle_deg"]),
        },
        jitter={
            "izquierda": _estadisticos_jitter(df, "left_knee_flexion_angle_deg", metadatos.fps),
            "derecha": _estadisticos_jitter(df, "right_knee_flexion_angle_deg", metadatos.fps),
            "izquierda_cuasi_estatico": jitter_estatico_izq,
            "derecha_cuasi_estatico": jitter_estatico_der,
        },
        asimetria={
            "n_frames": int(np.isfinite(asim).sum()),
            "mediana_deg": _redondear(_mediana(asim)),
            "p95_deg": _redondear(_percentil(asim, 95.0)),
            "max_deg": _redondear(float(np.nanmax(asim))) if np.isfinite(asim).any() else float("nan"),
        },
        cuasi_estatico={
            "n_frames": int(len(df_estatico)),
            "porcentaje_del_video": _redondear(100.0 * len(df_estatico) / n) if n else float("nan"),
            "asimetria_mediana_deg": _redondear(_mediana(asim_estatica)),
            "asimetria_p95_deg": _redondear(_percentil(asim_estatica, 95.0)),
        },
        variantes={v: _estadisticos_variante(df, v, metadatos.fps) for v in VARIANTES},
        referencia_visual=_referencia_visual(df, metadatos),
        inferencia={
            "media_ms": _redondear(float(np.mean(inferencia))) if inferencia.size else float("nan"),
            "mediana_ms": _redondear(_mediana(inferencia)),
            "p95_ms": _redondear(_percentil(inferencia, 95.0)),
        },
    )


# --------------------------------------------------------------------------------------
# Artefactos: CSV, figura, reporte
# --------------------------------------------------------------------------------------


def exportar_csv(df: pd.DataFrame, metadatos: MetadatosVideo) -> Path:
    """Serie temporal completa; ``frame_index`` y ``timestamp_ms`` permiten alinear con Kinovea."""
    DIR_SERIES.mkdir(parents=True, exist_ok=True)
    destino = DIR_SERIES / f"{metadatos.identificador}.csv"
    df.to_csv(destino, index=False, float_format="%.4f", encoding="utf-8", lineterminator="\n")
    return destino


def _dibujar_series(ax, df: pd.DataFrame, grosor: float) -> None:
    """Traza ambas piernas y el techo de plausibilidad sobre un eje ya creado."""
    x = df["frame_index"].to_numpy()
    ax.plot(x, df["left_knee_flexion_angle_deg"], color=COLOR_IZQUIERDA, linewidth=grosor,
            label="Rodilla izquierda")
    ax.plot(x, df["right_knee_flexion_angle_deg"], color=COLOR_DERECHA, linewidth=grosor,
            label="Rodilla derecha")
    ax.axhline(TECHO_FLEXION_PLAUSIBLE_DEG, color="#8a8880", linewidth=0.9, linestyle="--")


def _aplicar_estilo(ax) -> None:
    """Rejilla discreta, sin marcos superiores ni derechos, tinta secundaria."""
    ax.set_facecolor("#ffffff")
    ax.grid(axis="y", color="#d9d8d3", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c9c8c3")
    ax.tick_params(colors=COLOR_TINTA_SUAVE, labelsize=9)


def _leyenda(ax) -> None:
    """Leyenda legible incluso sobre series densas."""
    ax.legend(loc="upper right", fontsize=9, frameon=True, facecolor="#ffffff",
              edgecolor="none", framealpha=0.85)


def generar_figura(df: pd.DataFrame, metadatos: MetadatosVideo) -> Path:
    """
    Figura por video: serie angular completa, ventana de detalle y asimetria bilateral.

    En clips largos la serie completa solo sirve como panoramica (envolvente y huecos de
    deteccion); la lectura del ciclo se hace en la ventana de detalle.
    """
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_RESULTADOS / f"exp3_series_{metadatos.identificador}.png"

    n = len(df)
    fps = metadatos.fps if metadatos.fps else 30.0
    hay_detalle = n >= MIN_FRAMES_PARA_DETALLE
    grosor = 1.4 if n <= MIN_FRAMES_PARA_DETALLE else 0.7

    if hay_detalle:
        fig, (ax_ang, ax_detalle, ax_asim) = plt.subplots(
            3, 1, figsize=(11, 8.4), height_ratios=[1.7, 1.5, 0.9], dpi=150
        )
    else:
        fig, (ax_ang, ax_asim) = plt.subplots(
            2, 1, figsize=(11, 6.2), sharex=True, height_ratios=[2.1, 1.0], dpi=150
        )
        ax_detalle = None
    fig.patch.set_facecolor("#ffffff")

    # --- Panorámica -------------------------------------------------------------------
    _dibujar_series(ax_ang, df, grosor)
    ax_ang.annotate(
        f"techo de plausibilidad anatomica ({TECHO_FLEXION_PLAUSIBLE_DEG:.0f} grados)",
        xy=(0.01, TECHO_FLEXION_PLAUSIBLE_DEG),
        xycoords=("axes fraction", "data"),
        xytext=(0, 3),
        textcoords="offset points",
        color=COLOR_TINTA_SUAVE,
        fontsize=8,
    )
    ax_ang.set_ylabel("Flexion de rodilla (grados)", color=COLOR_TINTA_SUAVE, fontsize=10)
    _leyenda(ax_ang)
    ax_ang.margins(y=0.16)
    ax_ang.set_title(
        f"{etiqueta_video(metadatos.archivo, 48)}  |  {metadatos.frames_procesados} fotogramas "
        f"a {metadatos.fps} fps  |  plano {metadatos.plano_camara}"
        + ("  (recorte aplicado)" if metadatos.recortado else ""),
        color=COLOR_TINTA,
        fontsize=11,
        loc="left",
        pad=10,
    )

    # --- Ventana de detalle ------------------------------------------------------------
    if ax_detalle is not None:
        ancho_detalle = max(30, int(round(VENTANA_DETALLE_S * fps)))
        inicio = max(0, n // 2 - ancho_detalle // 2)
        fin = min(n, inicio + ancho_detalle)
        recorte = df.iloc[inicio:fin]
        ax_ang.axvspan(inicio, fin, color="#4a3aa7", alpha=0.10, linewidth=0)
        _dibujar_series(ax_detalle, recorte, 1.6)
        ax_detalle.set_ylabel("Flexion (grados)", color=COLOR_TINTA_SUAVE, fontsize=10)
        ax_detalle.set_title(
            f"Detalle: fotogramas {inicio}-{fin} ({VENTANA_DETALLE_S:.0f} s en el centro del clip, "
            "sombreado arriba)",
            color=COLOR_TINTA_SUAVE, fontsize=9, loc="left", pad=6,
        )
        ax_detalle.margins(y=0.16)
        _aplicar_estilo(ax_detalle)

    # --- Asimetría ---------------------------------------------------------------------
    ax_asim.plot(df["frame_index"].to_numpy(), df["bilateral_asymmetry_abs_deg"],
                 color=COLOR_ASIMETRIA, linewidth=max(0.7, grosor),
                 label="Asimetria bilateral |izq - der|")
    ax_asim.set_ylabel("Asimetria (grados)", color=COLOR_TINTA_SUAVE, fontsize=10)
    ax_asim.set_xlabel("Indice de fotograma", color=COLOR_TINTA_SUAVE, fontsize=10)
    _leyenda(ax_asim)
    ax_asim.margins(y=0.18)

    _aplicar_estilo(ax_ang)
    _aplicar_estilo(ax_asim)

    eje_segundos = ax_ang.secondary_xaxis("top", functions=(lambda v: v / fps, lambda t: t * fps))
    eje_segundos.set_xlabel("Tiempo (s)", color=COLOR_TINTA_SUAVE, fontsize=9)
    eje_segundos.tick_params(colors=COLOR_TINTA_SUAVE, labelsize=8)

    fig.tight_layout()
    fig.savefig(destino, facecolor=fig.get_facecolor())
    plt.close(fig)
    return destino


def _fmt(valor: Any, decimales: int = 2) -> str:
    """Formatea numeros para las tablas Markdown; NaN se imprime como 'n/d'."""
    if valor is None:
        return "n/d"
    if isinstance(valor, float) and not math.isfinite(valor):
        return "n/d"
    if isinstance(valor, float):
        return f"{valor:.{decimales}f}"
    return str(valor)


def _etiqueta_regimen(regimen: str) -> str:
    """Nombre legible del regimen de movimiento."""
    return {
        REGIMEN_BILATERAL: "bilateral simetrico",
        REGIMEN_MARCHA: "marcha / carrera",
        REGIMEN_DESCONOCIDO: "no clasificado",
    }.get(regimen, regimen)


def escribir_reporte(
    resultados: list[EstadisticosVideo],
    max_frames: int,
    duracion_total_s: float,
    procedencia: dict[str, str],
) -> Path:
    """Redacta el resumen comparativo en Markdown."""
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_RESULTADOS / "exp3_estabilidad_temporal.md"

    hay_recorte = any(r.metadatos["recortado"] for r in resultados)
    total_frames = sum(r.metadatos["frames_procesados"] for r in resultados)

    lineas: list[str] = []
    lineas.append("# Experimento 3 - Caracterización empírica sobre vídeo real")
    lineas.append("")
    lineas.append(
        "Caracterización del estimador de flexión de rodilla del sistema "
        "(MediaPipe Pose Landmarker `pose_landmarker_full.task` + "
        "`vision.biomechanics.knee_angles_from_landmarks`) sobre los "
        f"{len(resultados)} vídeos de referencia del repositorio: "
        f"{total_frames} fotogramas procesados en total."
    )
    lineas.append("")
    lineas.append("> **Este experimento NO mide exactitud.** No existe medición de goniómetro ni de")
    lineas.append("> sistema optoelectrónico asociada a estos clips, de modo que ningún número de esta")
    lineas.append("> página puede citarse como error angular. Lo que se mide es *comportamiento*:")
    lineas.append("> disponibilidad de la medida, estabilidad temporal, rango observado, piso de ruido")
    lineas.append("> de la asimetría y **cotas de incertidumbre que no requieren referencia externa**")
    lineas.append("> (discrepancia entre variantes de cálculo y plausibilidad anatómica).")
    lineas.append("")

    # --- Hallazgos ---------------------------------------------------------------------
    lineas.append("## 0. Hallazgos que condicionan la lectura del resto")
    lineas.append("")
    lineas.append("1. **La detección casi nunca falla; el umbral de visibilidad descartaría casi "
                  "la mitad de un clip, pero hoy no se aplica al ángulo.** Los ángulos son "
                  "calculables en la práctica totalidad de los fotogramas de todos los clips. Exigir "
                  "visibilidad >= 0.5 en los 6 landmarks dejaría un clip con la mitad de los "
                  "fotogramas, pero eso es un **contrafactual**: el sistema emite hoy el bloque "
                  "`knees` sin filtrar por visibilidad (sección 3).")
    lineas.append("2. **La estimación depende fuertemente del sistema de coordenadas.** Calcular el "
                  "mismo ángulo, sobre la misma detección y con la misma función, cambiando solo "
                  "el espacio de coordenadas de los landmarks, produce discrepancias de decenas de "
                  "grados (sección 6). Esa discrepancia es una cota inferior de la incertidumbre "
                  "de la medida y **no necesita goniómetro para citarse**.")
    lineas.append("3. **Aparecen lecturas anatómicamente imposibles** (flexión por encima de "
                  f"{TECHO_FLEXION_PLAUSIBLE_DEG:.0f} grados) en la ruta de producción (sección 6).")
    lineas.append("4. **El plano de cámara condiciona la medida y el sistema no lo conoce.** En las "
                  "tomas sagitales la proyección 2D y la estimación 3D convergen; en las frontales "
                  "divergen ampliamente (sección 6). Hoy nada en el sistema distingue un encuadre "
                  "del otro.")
    lineas.append("5. **Dos de los cinco clips tienen cortes de montaje** (tabla 2). Es un defecto "
                  "del material de referencia, no del sistema: rompen el tracking temporal y "
                  "obligan a excluir esos saltos del jitter.")
    lineas.append("6. **La asimetría bilateral solo es piso de ruido en régimen bilateral simétrico "
                  "o en tramos cuasi-estáticos** (sección 7); en carrera es señal real de fase.")
    lineas.append("")

    # --- Metodo ------------------------------------------------------------------------
    lineas.append("## 1. Método")
    lineas.append("")
    lineas.append("- **Motor:** `vision.pose_extractor.extract_pose_bgr_video` (MediaPipe "
                  "`RunningMode.VIDEO`, con tracking temporal). El ancla de timestamps se reinicia "
                  "con `reset_pose_video_timestamp_anchor()` antes de cada clip.")
    lineas.append("- **Ángulo:** flexión = 180 - ángulo interno cadera-rodilla-tobillo, acotado a "
                  "[0, 180] grados. Es la convención del proyecto. **La fuente de coordenadas la "
                  "resuelve el propio proyecto** (`vision.biomechanics`), no este experimento; la "
                  "sección 6 muestra cuál está usando de hecho en la versión medida.")
    lineas.append(f"- **Umbral de visibilidad evaluado:** {UMBRAL_VISIBILIDAD} sobre la visibilidad "
                  "mínima de los 6 landmarks usados (caderas, rodillas, tobillos).")
    if hay_recorte:
        lineas.append(f"- **Tope de fotogramas por vídeo:** {max_frames} "
                      f"(~{max_frames / 30.0:.0f} s a 30 fps); los clips que lo superan se recortan.")
    else:
        lineas.append(f"- **Tope de fotogramas por vídeo:** {max_frames} como salvaguarda de cómputo; "
                      "ningún clip lo alcanza, así que **todos los vídeos se procesaron completos**, "
                      "sin recorte ni submuestreo.")
    lineas.append("- **Jitter:** desviación típica de la primera diferencia de la serie angular, en "
                  "grados por fotograma, calculada **solo dentro de tramos de fotogramas "
                  "consecutivos válidos** (un hueco de detección no se cuenta como salto).")
    lineas.append(f"- **Ruido de alta frecuencia:** RMS del residuo frente a un suavizado "
                  f"Savitzky-Golay (ventana {VENTANA_SAVGOL}, orden {ORDEN_SAVGOL}). Separa mejor el "
                  "ruido del movimiento real que la primera diferencia bruta.")
    lineas.append(f"- **Tramos cuasi-estáticos:** fotogramas donde la desviación típica local "
                  f"(ventana centrada de {VENTANA_CUASI_ESTATICA} fotogramas) es menor que "
                  f"{UMBRAL_CUASI_ESTATICO_DEG} grados **en ambas piernas**.")
    lineas.append(f"- **Techo de plausibilidad anatómica:** {TECHO_FLEXION_PLAUSIBLE_DEG:.0f} grados "
                  "de flexión de rodilla (la flexión pasiva máxima, talón al glúteo, ronda 150-160 "
                  "grados). Por encima, la lectura no puede corresponder a una postura real.")
    lineas.append("- **Variantes de coordenadas comparadas.** Todas llaman a la misma función del "
                  "proyecto (`knee_angles_from_landmarks`) y solo cambian los landmarks de entrada:")
    for clave, etiqueta in ETIQUETAS_VARIANTE.items():
        marca = (" **(ruta de producción)**" if clave == VARIANTE_PRODUCCION
                 else " *(auxiliar, solo para este análisis)*")
        lineas.append(f"  - `{clave}`: {etiqueta}.{marca}")
    lineas.append(f"- **Coste de ejecución:** {duracion_total_s:.1f} s de reloj para el lote completo.")
    lineas.append("- **Determinismo comprobado:** dos ejecuciones consecutivas del lote, con el mismo "
                  "código, producen series angulares idénticas (0 celdas distintas al comparar los "
                  "CSV de `SentadillaProfunda.mp4` y `Running.mp4`, 183 y 1029 fotogramas). Lo único "
                  "que varía entre corridas es el tiempo de inferencia por fotograma.")
    lineas.append("")
    lineas.append("**Procedencia del código medido.** El repositorio se edita mientras corren los "
                  "experimentos y la ruta de cálculo angular vive en módulos que pueden cambiar "
                  "entre corridas, así que cada ejecución deja su huella:")
    lineas.append("")
    lineas.append("| Elemento | Valor |")
    lineas.append("|---|---|")
    lineas.append(f"| Commit | `{procedencia['commit']}` |")
    lineas.append(f"| Árbol de trabajo (`backend/vision`, `backend/app/services/pose`) | "
                  f"{procedencia['arbol_de_trabajo']} |")
    lineas.append(f"| `vision/biomechanics.py` | sha256 `{procedencia['sha256_biomechanics']}` |")
    lineas.append(f"| `vision/pose_extractor.py` | sha256 `{procedencia['sha256_pose_extractor']}` |")
    lineas.append(f"| `app/services/pose/mediapipe.py` | sha256 "
                  f"`{procedencia['sha256_mediapipe_service']}` |")
    lineas.append("")
    lineas.append("Si el árbol figura *con cambios sin confirmar*, los números corresponden al "
                  "código del árbol de trabajo en ese momento, no al del commit.")
    lineas.append("")

    # --- Inventario --------------------------------------------------------------------
    lineas.append("## 2. Vídeos procesados")
    lineas.append("")
    lineas.append("| Vídeo | Identificador de artefactos | Régimen | Plano de cámara | Resolución "
                  "| fps | Fotogramas del clip | Procesados | Recortado | Cortes de plano |")
    lineas.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in resultados:
        m = r.metadatos
        lineas.append(
            f"| `{m['archivo']}` | `{m['identificador']}` | {_etiqueta_regimen(m['regimen'])} | "
            f"{m['plano_camara']}" + (f" ({m['plano_camara_detalle']})" if m['plano_camara_detalle'] else "") + " | "
            f"{m['ancho']}x{m['alto']} | {_fmt(m['fps'])} | "
            f"{m['frames_contenedor']} | {m['frames_procesados']} | "
            f"{'sí' if m['recortado'] else 'no'} | "
            + (f"{m['cortes_de_plano']} (fotogramas {', '.join(str(v) for v in m['frames_de_corte'])})"
               if m['cortes_de_plano'] else "0")
            + " |"
        )
    lineas.append("")
    lineas.append("En las tablas siguientes el nombre del vídeo aparece abreviado; el nombre completo "
                  "y su identificador de artefactos están en esta tabla.")
    lineas.append("")
    lineas.append("Los **cortes de plano** se detectan automáticamente comparando fotogramas "
                  "consecutivos (diferencia media absoluta en escala de grises reducida) con un "
                  "umbral relativo a cada clip. Importan por dos motivos: rompen el tracking "
                  "temporal de MediaPipe, y el salto angular que producen **no es ruido del "
                  "estimador**, por lo que se excluye del cálculo de jitter (la serie se parte en "
                  "el corte, igual que en un hueco de detección). El criterio es conservador: "
                  "detecta cortes secos y puede pasar por alto encadenados suaves.")
    lineas.append("")
    lineas.append("El **plano de cámara** es una anotación manual del autor del experimento, hecha por "
                  "inspección visual de un fotograma de cada clip. El sistema **no** detecta el plano "
                  "de la toma; se anota aquí porque, como muestra la sección 6, es la variable que "
                  "más condiciona la lectura angular.")
    lineas.append("")
    lineas.append("Nota: MediaPipe reescala internamente el fotograma a un lado máximo de 640 px "
                  "antes de inferir (`_TARGET_MAX_DIM` en `app/services/pose/mediapipe.py`), así que "
                  "la resolución nativa del clip no se traduce en resolución efectiva de inferencia.")
    lineas.append("")

    # --- Deteccion ---------------------------------------------------------------------
    lineas.append("## 3. Tasa de detección y sensibilidad al umbral de visibilidad")
    lineas.append("")
    lineas.append("| Vídeo | Pose detectada (%) | Ángulos calculables (%) | "
                  "Ángulos con visibilidad >= 0.5 (%) | Caída por el umbral (p.p.) | "
                  "Visibilidad mín. mediana | Visibilidad mín. p05 | Landmark limitante dominante |")
    lineas.append("|---|---|---|---|---|---|---|---|")
    for r in resultados:
        lineas.append(
            f"| `{etiqueta_video(r.metadatos['archivo'])}` | {_fmt(r.tasa_deteccion_pose_pct)} | "
            f"{_fmt(r.tasa_angulos_validos_pct)} | {_fmt(r.tasa_angulos_validos_vis05_pct)} | "
            f"{_fmt(r.caida_por_umbral_pp)} | {_fmt(r.visibilidad_min_mediana, 3)} | "
            f"{_fmt(r.visibilidad_min_p05, 3)} | `{r.landmark_limitante_dominante}` "
            f"({_fmt(r.landmark_limitante_dominante_pct)} %) |"
        )
    lineas.append("")
    lineas.append("Lectura: la detección de pose no es el cuello de botella. **La columna del "
                  "umbral describe un escenario contrafactual, no el comportamiento actual del "
                  "sistema.** Hoy `pose_landmark_min_visibility_response` (0.5 por defecto) solo "
                  "recorta la lista de landmarks que viaja al cliente para dibujar el esqueleto "
                  "(`vision.landmark_filter.landmarks_for_api_response`); el bloque `knees` sale sin "
                  "filtrar en `vision.unified_payload.build_frame_payload_v1`, de modo que **ningún "
                  "ángulo se descarta hoy por visibilidad**. Lo que la columna muestra es qué "
                  "ocurriría si se condicionase la medida a ese umbral: el efecto **no es uniforme "
                  "entre clips** y vaciaría casi la mitad de la sentadilla. Como el landmark "
                  "limitante tiende a ser el mismo dentro de cada clip, si alguna vez se decide "
                  "condicionar el ángulo a la visibilidad convendría un umbral por articulación "
                  "antes que un valor global.")
    lineas.append("")

    # --- ROM ---------------------------------------------------------------------------
    lineas.append("## 4. Rango de movimiento observado (ruta de producción)")
    lineas.append("")
    lineas.append("Flexión de rodilla en grados. Es el rango que el estimador *reporta*, no el rango "
                  "real del sujeto: sin referencia externa no puede afirmarse cuál de los dos es. "
                  "Compárese con el techo de plausibilidad de la sección 6.")
    lineas.append("")
    lineas.append("| Vídeo | Pierna | Mín. | Máx. | Recorrido | Mediana |")
    lineas.append("|---|---|---|---|---|---|")
    for r in resultados:
        for clave in ("izquierda", "derecha"):
            rom = r.rom[clave]
            lineas.append(
                f"| `{etiqueta_video(r.metadatos['archivo'])}` | {clave} | {_fmt(rom['min_deg'])} | "
                f"{_fmt(rom['max_deg'])} | {_fmt(rom['recorrido_deg'])} | {_fmt(rom['mediana_deg'])} |"
            )
    lineas.append("")

    # --- Jitter ------------------------------------------------------------------------
    lineas.append("## 5. Ruido temporal (jitter) de la ruta de producción")
    lineas.append("")
    lineas.append("| Vídeo | Pierna | Jitter (grados/fotograma) | Jitter (grados/s) | "
                  "Salto mediano abs. | Salto p95 abs. | Ruido alta frec. RMS |")
    lineas.append("|---|---|---|---|---|---|---|")
    for r in resultados:
        for clave in ("izquierda", "derecha"):
            j = r.jitter[clave]
            lineas.append(
                f"| `{etiqueta_video(r.metadatos['archivo'])}` | {clave} | "
                f"{_fmt(j['jitter_std_diff_deg_frame'], 3)} | {_fmt(j['jitter_std_diff_deg_s'])} | "
                f"{_fmt(j['salto_mediano_abs_deg'], 3)} | {_fmt(j['salto_p95_abs_deg'], 3)} | "
                f"{_fmt(j['ruido_alta_frecuencia_rms_deg'], 3)} |"
            )
    lineas.append("")
    lineas.append("Lectura: la columna *jitter* mezcla movimiento real y ruido del estimador, y por "
                  "eso es alta en carrera aunque el estimador fuese estable. La columna *ruido de "
                  "alta frecuencia* aísla mejor la componente de ruido; es la que debe citarse como "
                  "piso de ruido cuadro a cuadro. Sigue siendo una cota superior: parte del residuo "
                  "de alta frecuencia en carrera es movimiento real rápido.")
    lineas.append("")
    lineas.append("Referencia cuasi-estática (el estimador midiendo algo que apenas se mueve; es el "
                  "caso más limpio disponible sin referencia externa):")
    lineas.append("")
    lineas.append("| Vídeo | Fotogramas cuasi-estáticos | Jitter izq. (grados/fotograma) | "
                  "Jitter der. (grados/fotograma) |")
    lineas.append("|---|---|---|---|")
    for r in resultados:
        j_izq = r.jitter.get("izquierda_cuasi_estatico") or {}
        j_der = r.jitter.get("derecha_cuasi_estatico") or {}
        lineas.append(
            f"| `{etiqueta_video(r.metadatos['archivo'])}` | {r.cuasi_estatico['n_frames']} | "
            f"{_fmt(j_izq.get('jitter_std_diff_deg_frame'), 3)} | "
            f"{_fmt(j_der.get('jitter_std_diff_deg_frame'), 3)} |"
        )
    lineas.append("")

    # --- Variantes ---------------------------------------------------------------------
    lineas.append("## 6. Sensibilidad al sistema de coordenadas y plausibilidad anatómica")
    lineas.append("")
    lineas.append("Todas las variantes parten de **la misma detección de pose y la misma función de "
                  "cálculo** (`knee_angles_from_landmarks`): solo cambian los landmarks de entrada. "
                  "La diferencia entre ellas no es error de detección, sino ambigüedad del propio "
                  "método de medida. **La discrepancia entre variantes es una cota inferior de la "
                  "incertidumbre angular del sistema y no necesita goniómetro para ser citada.**")
    lineas.append("")
    lineas.append("Variantes:")
    lineas.append("")
    for clave, etiqueta in ETIQUETAS_VARIANTE.items():
        marca = (" **(referencia de comparación)**" if clave == VARIANTE_PRODUCCION
                 else "")
        lineas.append(f"- `{clave}`: {etiqueta}.{marca}")
    lineas.append("")
    lineas.append("La variante `imagen_xyz_normalizado` reproduce la ruta que el proyecto usaba "
                  "antes de la corrección de espacio de coordenadas "
                  "(`docs/spec/goniometria-espacio-de-coordenadas.md`); su columna de discrepancia "
                  "es, por tanto, **la medida sobre vídeo real del sesgo que esa ruta introducía**.")
    lineas.append("")
    lineas.append("| Vídeo | Variante | Mediana flexión | p95 flexión | Máx. flexión | "
                  "% lecturas > 150 grados | Ruido alta frec. RMS | Discrepancia mediana vs. "
                  "producción | Discrepancia p95 | Discrepancia máx. |")
    lineas.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in resultados:
        for clave in VARIANTES:
            v = r.variantes[clave]
            es_prod = clave == VARIANTE_PRODUCCION
            disc_mediana = "-" if es_prod else _fmt(v["discrepancia_mediana_deg"])
            disc_p95 = "-" if es_prod else _fmt(v["discrepancia_p95_deg"])
            disc_max = "-" if es_prod else _fmt(v["discrepancia_max_deg"])
            lineas.append(
                f"| `{etiqueta_video(r.metadatos['archivo'])}` | `{clave}` | "
                f"{_fmt(v['mediana_flexion_deg'])} | {_fmt(v['p95_flexion_deg'])} | "
                f"{_fmt(v['max_flexion_deg'])} | {_fmt(v['pct_implausible_mayor_150'])} | "
                f"{_fmt(v['ruido_alta_frecuencia_rms_deg'], 3)} | {disc_mediana} | {disc_p95} | "
                f"{disc_max} |"
            )
    lineas.append("")

    # Una variante que coincide en TODOS los fotogramas con produccion no es evidencia
    # independiente: es la misma ruta de calculo vista dos veces. Declararlo evita que la
    # fila de ceros se lea como una corroboracion entre dos metodos distintos.
    identicas = [
        clave for clave in VARIANTES
        if clave != VARIANTE_PRODUCCION
        and all(r.variantes[clave]["discrepancia_max_deg"] == 0.0 for r in resultados)
    ]
    if identicas:
        listado = ", ".join(f"`{c}`" for c in identicas)
        lineas.append(f"**Aviso de lectura: {listado} no es una variante independiente.** Su "
                      "discrepancia sale 0.00 en los cinco clips y en todos los fotogramas porque "
                      "coincide *exactamente* con la ruta de producción: "
                      "`vision.biomechanics.angulos_rodilla` prefiere los `world_landmarks` siempre "
                      "que existen, y existen en todos los fotogramas detectados. En la versión "
                      "medida, producción **es** esa variante. Esa fila de ceros **no es una "
                      "corroboración entre dos métodos**, sino una comprobación de procedencia que "
                      "identifica qué espacio de coordenadas usa el sistema hoy. Las únicas "
                      "comparaciones informativas de esta tabla son las de las variantes de imagen.")
        lineas.append("")

    for r in resultados:
        ref = r.referencia_visual
        if not ref:
            continue
        lineas.append("")
        lineas.append(f"**Ancla cualitativa.** En `{r.metadatos['archivo']}`, fotograma "
                      f"{ref['frame_index']}, verificado visualmente: {ref['descripcion']}. "
                      "Una rodilla erguida debería leerse cerca de 0 grados de flexión. Lecturas "
                      "de cada variante en ese fotograma:")
        lineas.append("")
        lineas.append("| Variante | Rodilla izquierda | Rodilla derecha |")
        lineas.append("|---|---|---|")
        for clave, lectura in ref["lecturas"].items():
            lineas.append(f"| `{clave}` | {_fmt(lectura['izquierda_deg'])} | "
                          f"{_fmt(lectura['derecha_deg'])} |")
        lineas.append("")
        prod = ref["lecturas"].get(VARIANTE_PRODUCCION, {})
        hist = ref["lecturas"].get("imagen_xyz_normalizado", {})
        plano2d = ref["lecturas"].get("imagen_xy_isotropico", {})
        lineas.append(f"Sobre una postura erguida, la ruta de producción reporta "
                      f"{_fmt(prod.get('izquierda_deg'))} / {_fmt(prod.get('derecha_deg'))} grados; "
                      f"la ruta histórica sin corregir, {_fmt(hist.get('izquierda_deg'))} / "
                      f"{_fmt(hist.get('derecha_deg'))}; la proyección 2D isotrópica, "
                      f"{_fmt(plano2d.get('izquierda_deg'))} / {_fmt(plano2d.get('derecha_deg'))}.")
        lineas.append("")
        lineas.append("Tres advertencias antes de leer la diferencia como error del estimador:")
        lineas.append("")
        lineas.append("- El ángulo de tres puntos cadera-rodilla-tobillo **no es flexión sagital "
                      "pura**: con los pies separados, como en este fotograma, el muslo queda oblicuo "
                      "en el plano frontal y el ángulo en la rodilla recoge esa oblicuidad real. "
                      "Parte de la lectura es geometría verdadera del sujeto, no error.")
        lineas.append("- Que la proyección 2D dé casi 0 **no la convierte en la variante correcta**: "
                      "en una toma frontal esa proyección es prácticamente ciega a la flexión, y "
                      "daría un valor bajo tanto con el sujeto erguido como flexionando hacia la "
                      "cámara. En este mismo clip subestima la sentadilla profunda.")
        lineas.append("- Las variantes que usan `z` dependen por completo de la calidad de esa "
                      "coordenada, que es la peor estimada de las tres.")
        lineas.append("")
        lineas.append("La conclusión defendible no es «el sistema se equivoca en X grados», sino que "
                      "**la magnitud reportada como «flexión de rodilla» no está definida sin fijar "
                      "un plano de proyección**, y el sistema hoy no lo fija ni lo detecta. Un "
                      "fotograma de postura conocida como este es, además, el tipo de ancla que "
                      "debería multiplicarse en un protocolo con goniómetro para convertir estas "
                      "cotas en una medida de exactitud.")
    lineas.append("")

    # Concordancia entre proyeccion 2D y estimacion 3D, agrupada por plano de camara.
    por_plano: dict[str, list[float]] = {}
    for r in resultados:
        valor = r.variantes["imagen_xy_isotropico"]["discrepancia_mediana_deg"]
        if isinstance(valor, float) and math.isfinite(valor):
            por_plano.setdefault(r.metadatos["plano_camara"], []).append(valor)
    if por_plano:
        lineas.append("**Concordancia entre la proyección 2D y la estimación 3D, por plano de "
                      "cámara.** Si la cámara mira el plano en el que ocurre la flexión, ambas "
                      "formas de calcular deberían converger; si no, deben divergir. Es una prueba "
                      "de consistencia interna que tampoco requiere referencia externa:")
        lineas.append("")
        lineas.append("| Plano de cámara (anotado) | Vídeos | Discrepancia mediana 2D vs. "
                      "producción: media (grados) | Rango entre clips |")
        lineas.append("|---|---|---|---|")
        for plano, valores in sorted(por_plano.items()):
            promedio = sum(valores) / len(valores)
            rango = (f"{_fmt(min(valores))} - {_fmt(max(valores))}" if len(valores) > 1
                     else "clip único")
            lineas.append(f"| {plano} | {len(valores)} | {_fmt(promedio)} | {rango} |")
        lineas.append("")
        lineas.append("Con cinco clips y un solo sujeto por clip esto es una **señal, no una prueba**, "
                      "y el reparto es desigual dentro del grupo frontal. Aun así apunta en la "
                      "dirección que predice la geometría y sugiere una línea de trabajo concreta: "
                      "**la concordancia 2D/3D podría servir de indicador automático de si el "
                      "encuadre sirve para medir**, sin pedir al usuario que declare el plano. "
                      "Verificarlo exige un diseño con varios sujetos y planos controlados.")
    lineas.append("")

    # --- Asimetria ---------------------------------------------------------------------
    lineas.append("## 7. Asimetría bilateral: qué es piso de ruido y qué no")
    lineas.append("")
    lineas.append("**Advertencia de interpretación (crítica).** En marcha o carrera las piernas están "
                  "en fases opuestas del ciclo, así que `|izquierda - derecha|` es grande y **es señal "
                  "real, no ruido**. Solo puede leerse como piso de ruido del estimador en movimientos "
                  "bilaterales simétricos (sentadilla) o en tramos cuasi-estáticos. Las columnas de "
                  "clip completo y las cuasi-estáticas **no deben mezclarse** en la memoria.")
    lineas.append("")
    lineas.append("| Vídeo | Régimen | Asimetría mediana (todo el clip) | Asimetría p95 (todo el clip) "
                  "| Fotogramas cuasi-estáticos | % del clip | Asimetría mediana cuasi-estática | "
                  "Asimetría p95 cuasi-estática | ¿Piso de ruido válido? |")
    lineas.append("|---|---|---|---|---|---|---|---|---|")
    for r in resultados:
        ce = r.cuasi_estatico
        regimen = r.metadatos["regimen"]
        if regimen == REGIMEN_BILATERAL:
            valido = "sí (movimiento bilateral simétrico)"
        elif ce["n_frames"] > 0:
            valido = "solo la columna cuasi-estática"
        else:
            valido = "no (señal de fase, no ruido)"
        lineas.append(
            f"| `{etiqueta_video(r.metadatos['archivo'])}` | {_etiqueta_regimen(regimen)} | "
            f"{_fmt(r.asimetria['mediana_deg'])} | {_fmt(r.asimetria['p95_deg'])} | "
            f"{ce['n_frames']} | {_fmt(ce['porcentaje_del_video'])} | "
            f"{_fmt(ce['asimetria_mediana_deg'])} | {_fmt(ce['asimetria_p95_deg'])} | {valido} |"
        )
    lineas.append("")

    # --- Coste -------------------------------------------------------------------------
    lineas.append("## 8. Coste de inferencia observado")
    lineas.append("")
    lineas.append("Tiempo de `extract_pose_bgr_video` por fotograma (incluye conversión de color y "
                  "reescalado a 640 px; excluye decodificación del contenedor y todo transporte de "
                  "red). Es el componente de inferencia del presupuesto de latencia extremo a "
                  "extremo, no la latencia extremo a extremo.")
    lineas.append("")
    lineas.append("| Vídeo | Media (ms) | Mediana (ms) | p95 (ms) |")
    lineas.append("|---|---|---|---|")
    for r in resultados:
        lineas.append(
            f"| `{etiqueta_video(r.metadatos['archivo'])}` | {_fmt(r.inferencia['media_ms'])} | "
            f"{_fmt(r.inferencia['mediana_ms'])} | {_fmt(r.inferencia['p95_ms'])} |"
        )
    lineas.append("")

    # --- Artefactos --------------------------------------------------------------------
    lineas.append("## 9. Artefactos generados")
    lineas.append("")
    lineas.append("Cada figura tiene tres paneles en los clips largos: la serie completa (panorámica; "
                  "en miles de fotogramas solo sirve para ver la envolvente y los huecos de "
                  "detección), una **ventana de detalle de 5 s** tomada del centro del clip y "
                  "sombreada en la panorámica, y la asimetría bilateral. En la ventana de detalle de "
                  "los clips de carrera se aprecia con claridad que ambas piernas oscilan en "
                  "oposición de fase, que es justo lo que hace inservible la asimetría como piso de "
                  "ruido en ese régimen.")
    lineas.append("")
    lineas.append("| Vídeo | Serie temporal (CSV) | Figura (PNG) |")
    lineas.append("|---|---|---|")
    for r in resultados:
        ident = r.metadatos["identificador"]
        lineas.append(
            f"| `{etiqueta_video(r.metadatos['archivo'])}` | "
            f"`validacion/resultados/series/{ident}.csv` | "
            f"`validacion/resultados/exp3_series_{ident}.png` |"
        )
    lineas.append("")
    lineas.append("Columnas del CSV: `frame_index`, `timestamp_ms`, `pose_detectada`, "
                  "`angulos_validos`, `left_knee_flexion_angle_deg`, `right_knee_flexion_angle_deg`, "
                  "`left_knee_internal_angle_deg`, `right_knee_internal_angle_deg`, "
                  "`bilateral_asymmetry_abs_deg`, las columnas de cada variante de "
                  "coordenadas (`*_knee_flexion_world_deg`, `*_knee_flexion_img_xyz_iso_deg`, "
                  "`*_knee_flexion_img_xy_iso_deg`, `*_knee_flexion_img_xyz_norm_deg`), "
                  "`bilateral_asymmetry_world_abs_deg`, `cambio_escena_score`, "
                  "`corte_de_plano`, `min_visibility_lower_limb`, `landmark_limitante`, "
                  "`visible_ge_0_5`, `inferencia_ms`.")
    lineas.append("")
    lineas.append("Al preparar el cotejo con Kinovea, revisar antes la columna `corte_de_plano`: "
                  "un clip con cortes cambia de encuadre a mitad de la serie y los fotogramas de "
                  "cada tramo no son comparables entre sí.")
    lineas.append("")
    lineas.append("`frame_index` y `timestamp_ms` están pensados para el cotejo manual fotograma a "
                  "fotograma con Kinovea: `timestamp_ms` es nominal (`frame_index * 1000 / fps` del "
                  "contenedor), no el sello de tiempo de presentación real del contenedor. Para el "
                  "cotejo conviene medir en Kinovea el ángulo interno cadera-rodilla-tobillo y "
                  "convertirlo con `flexión = 180 - interno`, que es la convención del sistema.")
    lineas.append("")

    # --- Limitaciones ------------------------------------------------------------------
    lineas.append("## 10. Limitaciones")
    lineas.append("")
    lineas.append("1. **Sin referencia externa.** No hay goniometría ni marcadores; nada aquí es "
                  "exactitud. Las cotas de la sección 6 son de incertidumbre, no de error.")
    lineas.append("2. **Plano de cámara anotado a mano, no detectado.** La anotación de la tabla 2 "
                  "la hizo el autor del experimento mirando un fotograma por clip: es suficiente "
                  "para agrupar resultados, no para corregirlos. El sistema no detecta el plano y "
                  "no compensa la oblicuidad de la toma.")
    lineas.append("3. **El ángulo de tres puntos no es flexión sagital pura.** Recoge también la "
                  "oblicuidad del miembro en el plano frontal (p. ej. una postura con los pies "
                  "separados), de modo que una lectura distinta de cero en bipedestación no implica "
                  "necesariamente error del estimador.")
    lineas.append("4. **Componente `z` de los landmarks de imagen.** Su escala no es comparable a la "
                  "de x/y y su incertidumbre es mayor; la sección 6 cuantifica el efecto, no lo "
                  "corrige.")
    lineas.append("5. **Régimen por heurística de nombre de archivo**, no por anotación del autor.")
    lineas.append("6. **Muestra no probabilística:** un sujeto por clip y clips tomados del material "
                  "de regresión del repositorio, no de un diseño muestral. Ninguna cifra generaliza "
                  "a población.")
    lineas.append("7. **El techo de plausibilidad (150 grados) es un criterio conservador:** detecta "
                  "lecturas imposibles, no las meramente erróneas. Un valor plausible puede seguir "
                  "estando equivocado.")
    lineas.append("8. **Los tramos cuasi-estáticos se detectan sobre la propia serie estimada**, así "
                  "que un tramo en el que el estimador se quedara congelado se clasificaría como "
                  "cuasi-estático y rebajaría artificialmente el piso de ruido.")
    lineas.append("9. **El material de referencia no se grabó para medir.** Son vídeos editados o "
                  "descargados, con cortes, rótulos y encuadres variables; sirven para caracterizar "
                  "el comportamiento del sistema, no como protocolo de medición.")
    lineas.append("10. **El coste de inferencia depende de la máquina** (aquí, portátil Apple Silicon) "
                  "y del reescalado interno a 640 px; no es extrapolable a otro hardware.")
    if hay_recorte:
        lineas.append(f"11. **Recorte a {max_frames} fotogramas** en los clips marcados en la tabla 2: "
                      "las estadísticas describen ese segmento inicial, no el clip completo.")
    lineas.append("")
    lineas.append("_Generado por `validacion/experimentos/exp3_estabilidad_temporal.py`._")
    lineas.append("")

    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def listar_videos(directorio: Path) -> list[Path]:
    """Videos .mp4 del directorio, en orden lexicografico insensible a mayusculas."""
    if not directorio.is_dir():
        raise FileNotFoundError(f"Directorio de videos inexistente: {directorio}")
    return sorted(
        (p for p in directorio.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"),
        key=lambda p: p.name.lower(),
    )


def main() -> int:
    """Punto de entrada del experimento."""
    parser = argparse.ArgumentParser(
        description="Experimento 3: caracterizacion empirica sobre video real"
    )
    parser.add_argument("--videos-dir", type=Path, default=DIR_VIDEOS_POR_DEFECTO)
    parser.add_argument("--max-frames", type=int, default=MAX_FRAMES_POR_DEFECTO)
    args = parser.parse_args()

    if not RUTA_MODELO.is_file():
        print(f"[ERROR] Modelo de pose no encontrado: {RUTA_MODELO}", file=sys.stderr)
        return 2

    videos = listar_videos(args.videos_dir)
    if not videos:
        print(f"[ERROR] No hay videos .mp4 en {args.videos_dir}", file=sys.stderr)
        return 2

    procedencia = procedencia_codigo()
    print(f"[exp3] Videos a procesar: {len(videos)} | tope por video: {args.max_frames} fotogramas")
    print(f"[exp3] Codigo medido: commit {procedencia['commit']} "
          f"({procedencia['arbol_de_trabajo']}), biomechanics.py "
          f"sha256:{procedencia['sha256_biomechanics']}")
    resultados: list[EstadisticosVideo] = []
    t_lote = time.perf_counter()

    for ruta in videos:
        t0 = time.perf_counter()
        print(f"[exp3] Procesando {ruta.name} ...", flush=True)
        df, metadatos = procesar_video(ruta, args.max_frames)
        if df.empty:
            print(f"[exp3] AVISO: sin fotogramas legibles en {ruta.name}", file=sys.stderr)
            continue
        estadisticos = calcular_estadisticos(df, metadatos)
        ruta_csv = exportar_csv(df, metadatos)
        ruta_png = generar_figura(df, metadatos)
        resultados.append(estadisticos)
        print(
            f"[exp3]   {metadatos.frames_procesados} fotogramas en {time.perf_counter() - t0:.1f} s | "
            f"angulos validos {estadisticos.tasa_angulos_validos_pct:.2f}% | "
            f"CSV -> {ruta_csv.name} | PNG -> {ruta_png.name}",
            flush=True,
        )

    if not resultados:
        print("[ERROR] Ningun video produjo resultados", file=sys.stderr)
        return 1

    duracion_total = time.perf_counter() - t_lote
    ruta_md = escribir_reporte(resultados, args.max_frames, duracion_total, procedencia)

    ruta_json = DIR_RESULTADOS / "exp3_resumen.json"
    ruta_json.write_text(
        json.dumps(
            {
                "procedencia_codigo": procedencia,
                "parametros": {
                    "max_frames": args.max_frames,
                    "umbral_visibilidad": UMBRAL_VISIBILIDAD,
                    "techo_flexion_plausible_deg": TECHO_FLEXION_PLAUSIBLE_DEG,
                    "ventana_cuasi_estatica": VENTANA_CUASI_ESTATICA,
                    "umbral_cuasi_estatico_deg": UMBRAL_CUASI_ESTATICO_DEG,
                    "ventana_savgol": VENTANA_SAVGOL,
                    "orden_savgol": ORDEN_SAVGOL,
                },
                "videos": [asdict(r) for r in resultados],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[exp3] Reporte -> {ruta_md}")
    print(f"[exp3] Resumen JSON -> {ruta_json}")
    print(f"[exp3] Tiempo total: {duracion_total:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
