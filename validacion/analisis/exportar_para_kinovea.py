#!/usr/bin/env python3
"""
Exporta la serie angular estimada por el sistema y los fotogramas para medirlos a mano.

Nota sobre el nombre del archivo: se llama ``exportar_para_kinovea`` por razones
históricas (el protocolo se redactó para Kinovea y la memoria del trabajo de grado cita
este nombre). El comparador manual vigente del Nivel 2 es **Tracker** (Open Source
Physics), que funciona en macOS; el script es agnóstico de la herramienta y el nombre se
conserva para no romper las referencias.

Uso previsto en la validación: se procesa un vídeo con el mismo pipeline de producción
(MediaPipe Pose en servidor + ``vision.biomechanics``) y se vuelca a CSV el ángulo de
flexión de rodilla de los fotogramas **muestreados**, con su índice de frame y su
marca temporal. Ese CSV se pasa después a ``validacion/analisis/analizar_nivel2.py``
(que usa ``validacion/analisis/acuerdo.py``) para obtener MAE, RMSE, sesgo,
Bland-Altman e ICC(2,1).

Medir a mano todos los fotogramas de un clip es inviable, por eso existe
``--cada-n-frames``: con el valor por defecto (10) se obtiene una muestra manejable
que sigue cubriendo todo el rango articular del movimiento.

Nota sobre el muestreo: por defecto se ejecuta la inferencia sobre **todos** los
fotogramas en orden temporal (``RunningMode.VIDEO``), aunque solo se escriban al CSV
los muestreados. Así el seguimiento temporal de MediaPipe es idéntico al del análisis
real y el ángulo exportado es el que produciría el sistema en producción. Con
``--solo-muestreados`` se salta la inferencia de los fotogramas intermedios (más
rápido, pero sin continuidad de seguimiento; útil solo para pruebas exploratorias).

Exportación de fotogramas para Tracker
--------------------------------------
Con ``--exportar-fotogramas`` (y ``--lado``) el script escribe además:

- Cada fotograma muestreado como PNG en ``validacion/datos/nivel2/<video>/frames/``
  (o en el directorio indicado), con nombre ``m<ordinal:04d>.png`` y el **índice
  original del vídeo rotulado** en la esquina superior izquierda sobre un recuadro
  negro. El PNG se obtiene del **mismo arreglo** que recibe la inferencia durante la
  pasada secuencial, de modo que la imagen es exactamente el fotograma cuyo ángulo
  figura en el CSV (el protocolo, sección 2.4, verificó además que la lectura
  secuencial y el posicionamiento por ``CAP_PROP_POS_FRAMES`` son idénticos byte a
  byte). El nombre no lleva el índice del vídeo porque Tracker solo reconoce una
  secuencia con prefijo constante y contador consecutivo (ver
  ``validacion/analisis/plantilla_tracker.py``).
- La plantilla de medición ``nivel2_tracker_sesion1.csv`` junto al directorio de
  fotogramas (en su directorio padre), con una fila por PNG, ``sesion = 1`` y las
  columnas de valor vacías.
- ``metadatos_exportacion.json`` en ese mismo directorio: geometría del vídeo, lado,
  muestreo y huellas SHA-256 del vídeo y del CSV del sistema, para poder comprobar
  después que el análisis usa el CSV que corresponde a esos fotogramas.

Por seguridad, el script **nunca sobrescribe una plantilla que ya contenga
mediciones**, y no reemplaza fotogramas ni una plantilla vacía existentes sin
``--sobrescribir-fotogramas``.

Ejemplo (desde ``backend/``)::

    PYTHONPATH=. ~/.venvs/biomotion/bin/python ../validacion/analisis/exportar_para_kinovea.py \\
        --video <ruta_del_clip_propio.mp4> \\
        --salida ../validacion/datos/nivel2/<nombre_del_clip>/serie_sistema.csv \\
        --cada-n-frames 10 --lado derecha --exportar-fotogramas

ADVERTENCIA 1 - El CSV caduca con el pipeline
---------------------------------------------
Los angulos exportados son la salida del pipeline de vision **en el momento de la
exportacion**. Cualquier cambio en ``vision.biomechanics`` o en
``vision.pose_extractor`` (por ejemplo el paso de landmarks normalizados a
``world_landmarks``) invalida el CSV: las mediciones manuales (Tracker) quedarian
comparadas contra una estimacion que el sistema ya no produce. Antes de rellenar la
medicion manual, y de nuevo antes de calcular el acuerdo, hay que **regenerar el CSV**
con el codigo vigente y comprobar que los angulos no han cambiado.

ADVERTENCIA 2 - El video debe ser apto para goniometria
-------------------------------------------------------
Este script no comprueba la validez del material de entrada. Para que el CSV sirva
como base de una comparacion de exactitud angular, el clip debe cumplir:

1. **Una sola toma continua** y **un solo sujeto**. Un video de montaje (varias tomas
   pegadas) produce una serie que parece una trayectoria articular pero no lo es, y
   cualquier lectura biomecanica de ella (fases, asimetria por repeticion) es falsa.
2. **Plano sagital** respecto de la rodilla medida. Tracker, como Kinovea, mide angulos
   en 2D sobre el plano de la imagen: en plano frontal la flexion de rodilla aparece
   escorzada y ni la medicion manual ni la comparacion tienen sentido anatomico.
3. Ambas rodillas visibles y sin autooclusion si se va a reportar asimetria bilateral.

El clip ``tests/assets/videos/SentadillaProfunda.mp4`` **NO cumple 1 ni 2**: verificado
fotograma a fotograma, contiene al menos tres tomas distintas (sujeto de frente en
sentadilla hasta el frame ~55; sujeto distinto de frente y de pie hasta el frame ~85;
sujeto de perfil a partir del frame ~86). Los cortes no se detectan por diferencia de
pixeles porque el fondo es el mismo en todas las tomas. Sirve como banco de pruebas de
rendimiento y de robustez del exportador, pero **no como material de validacion de
exactitud**: para eso hay que grabar un clip propio de una sola toma en plano sagital.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
_RAIZ_BACKEND = _RAIZ_REPOSITORIO / "backend"
for _ruta in (_RAIZ_BACKEND, _RAIZ_REPOSITORIO):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

try:
    import cv2
    import numpy as np

    from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor
    from vision.pose_extractor import extract_pose_bgr_video
    from vision.processor import VideoSource
except ModuleNotFoundError as exc:  # pragma: no cover - diagnóstico de entorno
    nombre = getattr(exc, "name", None) or str(exc)
    print(
        f"Falta el módulo '{nombre}'. Intérprete actual: {sys.executable}\n"
        "Ejecute con el intérprete del proyecto y con el backend en PYTHONPATH.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from validacion.analisis.plantilla_tracker import (  # noqa: E402
    LADOS_VALIDOS,
    NOMBRE_PLANTILLA_SESION1,
    escribir_plantilla,
    nombre_fotograma_sesion1,
    plantilla_tiene_mediciones,
)

#: Directorio por defecto con los vídeos de referencia del repositorio.
DIRECTORIO_VIDEOS_POR_DEFECTO = _RAIZ_REPOSITORIO / "tests" / "assets" / "videos"

#: Modelo de pose por defecto (el mismo que sirve el backend en producción).
MODELO_POR_DEFECTO = _RAIZ_BACKEND / "models" / "pose_landmarker_full.task"

#: Raíz por defecto de los datos del Nivel 2: ``<raiz>/<nombre_del_video>/frames/``.
DIRECTORIO_NIVEL2_POR_DEFECTO = _RAIZ_REPOSITORIO / "validacion" / "datos" / "nivel2"

#: Nombre del archivo de metadatos que acompaña a los fotogramas exportados.
NOMBRE_METADATOS_EXPORTACION = "metadatos_exportacion.json"

#: Valor centinela de ``--exportar-fotogramas`` sin argumento (usar el directorio por defecto).
_DIRECTORIO_POR_DEFECTO = "__por_defecto__"

#: Columnas del CSV. ``angulo_manual_kinovea_deg`` se exporta vacía a propósito:
#: es la casilla histórica del flujo con Kinovea. Se conserva para no romper la
#: compatibilidad del formato; con Tracker la medición manual va en la plantilla
#: ``nivel2_tracker_sesion1.csv`` (ver ``plantilla_tracker.py``).
COLUMNAS_CSV = (
    "frame_index",
    "timestamp_ms",
    "timestamp_s",
    "pose_ok",
    "left_knee_flexion_angle_deg",
    "right_knee_flexion_angle_deg",
    "left_knee_internal_angle_deg",
    "right_knee_internal_angle_deg",
    "asimetria_bilateral_deg",
    "angulo_manual_kinovea_deg",
    "lado_medido_kinovea",
    "observaciones",
)


def resolver_video(referencia_video: str, directorio_videos: Path) -> Path:
    """
    Acepta una ruta directa a un archivo o el nombre de un vídeo del directorio dado.

    Se prioriza la ruta literal; si no existe, se busca por nombre dentro de
    ``directorio_videos``. Lanza ``FileNotFoundError`` si no aparece en ninguno.
    """
    candidato = Path(referencia_video).expanduser()
    if candidato.is_file():
        return candidato.resolve()
    alternativa = (directorio_videos / Path(referencia_video).name).resolve()
    if alternativa.is_file():
        return alternativa
    raise FileNotFoundError(
        f"No se encontró el vídeo {referencia_video!r} ni como ruta ni dentro de {directorio_videos}."
    )


def _redondear(valor: float | None, decimales: int = 3) -> str:
    """Formatea un ángulo para CSV; cadena vacía si no hay valor utilizable."""
    if valor is None:
        return ""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ""
    if numero != numero:  # NaN
        return ""
    return f"{numero:.{decimales}f}"


# ---------------------------------------------------------------------------
# Fotogramas rotulados
# ---------------------------------------------------------------------------


def texto_rotulo(indice: int) -> str:
    """Texto que se quema en el PNG: el índice original del vídeo (``f00030``)."""
    return f"f{indice:05d}"


def geometria_rotulo(alto: int) -> tuple[float, int, int, int]:
    """
    Escala de fuente, grosor, relleno y margen del rótulo, proporcionales al alto.

    Con ``FONT_HERSHEY_SIMPLEX`` la altura de las cifras es de unos 22 px por unidad de
    escala: a 360 px de alto (escala 0,67) el rótulo mide unos 15 px y a 1080 px
    (escala 2,0) unos 44 px. Ocupa menos del 6 % del ancho y del 10 % del alto de la
    imagen, siempre en la esquina superior izquierda, lejos de la pierna en un
    encuadre de cuerpo completo.
    """
    escala = max(0.6, alto / 540.0)
    grosor = max(2, int(round(escala * 2.0)))
    relleno = max(4, int(round(8 * escala)))
    margen = max(4, int(round(10 * escala)))
    return escala, grosor, relleno, margen


def rotular_indice_fotograma(fotograma: np.ndarray, indice: int) -> np.ndarray:
    """
    Devuelve una **copia** del fotograma con el índice rotulado arriba a la izquierda.

    Texto blanco sobre recuadro negro relleno (máximo contraste sobre cualquier fondo).
    No modifica el arreglo de entrada: el fotograma que recibe la inferencia sigue
    intacto.
    """
    if fotograma is None or fotograma.ndim != 3:
        raise ValueError("Se esperaba un fotograma BGR de tres canales.")
    rotulado = fotograma.copy()
    alto = int(rotulado.shape[0])
    escala, grosor, relleno, margen = geometria_rotulo(alto)
    texto = texto_rotulo(indice)
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    (ancho_texto, alto_texto), linea_base = cv2.getTextSize(texto, fuente, escala, grosor)
    x0, y0 = margen, margen
    x1 = x0 + ancho_texto + 2 * relleno
    y1 = y0 + alto_texto + linea_base + 2 * relleno
    cv2.rectangle(rotulado, (x0, y0), (x1, y1), (0, 0, 0), thickness=-1)
    cv2.putText(
        rotulado,
        texto,
        (x0 + relleno, y0 + relleno + alto_texto),
        fuente,
        escala,
        (255, 255, 255),
        grosor,
        cv2.LINE_AA,
    )
    return rotulado


def directorio_fotogramas_por_defecto(ruta_video: Path) -> Path:
    """``validacion/datos/nivel2/<nombre_del_video>/frames``."""
    return DIRECTORIO_NIVEL2_POR_DEFECTO / ruta_video.stem / "frames"


def preparar_directorio_fotogramas(directorio: Path, *, sobrescribir: bool) -> Path:
    """
    Comprueba que se puede exportar en ``directorio`` sin destruir datos y lo crea.

    Devuelve la ruta de la plantilla de la sesión 1 (en el directorio padre). Reglas:

    - Si la plantilla ya contiene alguna medición, **siempre** se aborta: son datos
      reales y no se regeneran por accidente.
    - Si ya hay fotogramas ``m*.png`` o una plantilla vacía, se aborta salvo
      ``sobrescribir``; en ese caso se borran los ``m*.png`` previos para que no se
      mezclen con la nueva exportación (otro paso de muestreo dejaría restos).
    """
    ruta_plantilla = directorio.parent / NOMBRE_PLANTILLA_SESION1
    if plantilla_tiene_mediciones(ruta_plantilla):
        raise RuntimeError(
            f"La plantilla {ruta_plantilla} ya contiene mediciones; no se sobrescribe. "
            "Mueva o renombre esa carpeta si de verdad quiere exportar de nuevo."
        )
    existentes = sorted(directorio.glob("m*.png")) if directorio.is_dir() else []
    if (existentes or ruta_plantilla.exists()) and not sobrescribir:
        raise RuntimeError(
            f"Ya existen fotogramas o plantilla en {directorio.parent}. "
            "Use --sobrescribir-fotogramas para reemplazarlos."
        )
    for ruta in existentes:
        ruta.unlink()
    directorio.mkdir(parents=True, exist_ok=True)
    return ruta_plantilla


def construir_filas_plantilla(
    filas_sistema: list[dict[str, Any]],
    *,
    nombre_video: str,
    lado: str,
) -> list[dict[str, Any]]:
    """
    Filas de la plantilla de la sesión 1: una por fotograma exportado, valores vacíos.

    El ordinal es la posición en la secuencia exportada (0, 1, 2...), que coincide con
    el contador del nombre del PNG y con el número de fotograma que muestra Tracker.
    """
    if lado not in LADOS_VALIDOS:
        raise ValueError(f"Lado no válido: {lado!r}. Use uno de {LADOS_VALIDOS}.")
    return [
        {
            "video": nombre_video,
            "ordinal_muestra": ordinal,
            "frame_idx": fila["frame_index"],
            "lado": lado,
            "sesion": 1,
            "fecha_medicion": "",
            "tracker_angulo_deg": "",
            "confianza_operador": "",
            "observaciones": "",
            "archivo_png": nombre_fotograma_sesion1(ordinal),
        }
        for ordinal, fila in enumerate(filas_sistema)
    ]


def huella_sha256(ruta: Path) -> str:
    """SHA-256 completo del archivo (lectura por bloques)."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


# ---------------------------------------------------------------------------
# Extracción
# ---------------------------------------------------------------------------


def extraer_serie_angular(
    ruta_video: Path,
    ruta_modelo: Path,
    *,
    cada_n_frames: int = 10,
    max_frames: int = 0,
    solo_muestreados: bool = False,
    directorio_fotogramas: Path | None = None,
    desde_frame: int = 0,
    hasta_frame: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Procesa el vídeo y devuelve ``(filas_muestreadas, metadatos)``.

    ``filas_muestreadas`` contiene un diccionario por fotograma exportado, con las
    claves de :data:`COLUMNAS_CSV`. ``metadatos`` recoge geometría del vídeo, fotogramas
    leídos, tasa de detección de pose y tiempos de proceso, que son la evidencia de
    rendimiento que acompaña a la exactitud.

    Si se indica ``directorio_fotogramas`` (que debe existir), cada fotograma
    muestreado se escribe además como ``m<ordinal:04d>.png`` con su índice rotulado. El
    PNG sale del mismo arreglo que recibe la inferencia, en la misma iteración, así
    que no hay ninguna posibilidad de desalineación entre imagen y ángulo. Los nombres
    escritos se devuelven en ``metadatos["fotogramas_exportados"]``.

    ``desde_frame`` y ``hasta_frame`` (ambos inclusive) restringen la exportación a un
    tramo del clip, por ejemplo el segmento grabado en plano sagital de un vídeo que
    también contiene tomas de frente. El muestreo se cuenta desde ``desde_frame``. La
    inferencia sigue recorriendo los fotogramas previos al tramo para que el
    seguimiento temporal de MediaPipe sea el mismo que en producción.
    """
    if cada_n_frames < 1:
        raise ValueError("cada_n_frames debe ser >= 1.")
    if desde_frame < 0:
        raise ValueError("desde_frame debe ser >= 0.")
    if hasta_frame is not None and hasta_frame < desde_frame:
        raise ValueError("hasta_frame debe ser >= desde_frame.")
    if not ruta_modelo.is_file():
        raise FileNotFoundError(f"No se encontró el modelo de pose: {ruta_modelo}")

    # MediaPipe exige marcas de tiempo estrictamente crecientes por instancia:
    # al empezar un clip nuevo hay que reiniciar el ancla temporal.
    reset_pose_video_timestamp_anchor()

    filas: list[dict[str, Any]] = []
    fotogramas_exportados: list[dict[str, Any]] = []
    frames_leidos = 0
    frames_inferidos = 0
    frames_con_pose = 0
    inicio = time.perf_counter()

    with VideoSource(source_type="file", file_path=str(ruta_video)) as fuente:
        ancho, alto, fps = fuente.stream_geometry()
        total_declarado = fuente.total_frame_count

        while True:
            if max_frames and frames_leidos >= max_frames:
                break
            if hasta_frame is not None and frames_leidos > hasta_frame:
                break
            frame = fuente.get_frame()
            if frame is None:
                break

            indice = frames_leidos
            frames_leidos += 1
            es_muestreado = indice >= desde_frame and (indice - desde_frame) % cada_n_frames == 0
            if solo_muestreados and not es_muestreado:
                continue

            timestamp_ms = int(round(indice * 1000.0 / fps))
            resultado = extract_pose_bgr_video(frame, ruta_modelo, timestamp_ms)
            frames_inferidos += 1
            if resultado.ok and resultado.knees:
                frames_con_pose += 1

            if not es_muestreado:
                continue

            if directorio_fotogramas is not None:
                ordinal = len(filas)
                nombre_png = nombre_fotograma_sesion1(ordinal)
                ruta_png = directorio_fotogramas / nombre_png
                if not cv2.imwrite(str(ruta_png), rotular_indice_fotograma(frame, indice)):
                    raise RuntimeError(f"No se pudo escribir el fotograma {ruta_png}.")
                fotogramas_exportados.append(
                    {"ordinal_muestra": ordinal, "frame_idx": indice, "archivo_png": nombre_png}
                )

            rodillas = resultado.knees or {}
            flexion_izq = rodillas.get("left_knee_flexion_angle_deg")
            flexion_der = rodillas.get("right_knee_flexion_angle_deg")
            asimetria: float | None = None
            if flexion_izq is not None and flexion_der is not None:
                if flexion_izq == flexion_izq and flexion_der == flexion_der:  # descarta NaN
                    asimetria = abs(float(flexion_izq) - float(flexion_der))

            filas.append(
                {
                    "frame_index": indice,
                    "timestamp_ms": timestamp_ms,
                    "timestamp_s": f"{timestamp_ms / 1000.0:.3f}",
                    "pose_ok": "1" if (resultado.ok and rodillas) else "0",
                    "left_knee_flexion_angle_deg": _redondear(flexion_izq),
                    "right_knee_flexion_angle_deg": _redondear(flexion_der),
                    "left_knee_internal_angle_deg": _redondear(rodillas.get("left_knee_internal_angle_deg")),
                    "right_knee_internal_angle_deg": _redondear(rodillas.get("right_knee_internal_angle_deg")),
                    "asimetria_bilateral_deg": _redondear(asimetria),
                    "angulo_manual_kinovea_deg": "",
                    "lado_medido_kinovea": "",
                    "observaciones": "",
                }
            )

    transcurrido = time.perf_counter() - inicio
    metadatos = {
        "video": str(ruta_video),
        "modelo": str(ruta_modelo),
        "ancho": ancho,
        "alto": alto,
        "fps": fps,
        "frames_declarados_por_codec": total_declarado,
        "frames_leidos": frames_leidos,
        "frames_inferidos": frames_inferidos,
        "frames_con_pose": frames_con_pose,
        "tasa_deteccion": (frames_con_pose / frames_inferidos) if frames_inferidos else 0.0,
        "filas_exportadas": len(filas),
        "cada_n_frames": cada_n_frames,
        "desde_frame": desde_frame,
        "hasta_frame": hasta_frame,
        "solo_muestreados": solo_muestreados,
        "segundos_totales": transcurrido,
        "ms_por_frame_inferido": (transcurrido * 1000.0 / frames_inferidos) if frames_inferidos else 0.0,
        "fotogramas_exportados": fotogramas_exportados,
    }
    return filas, metadatos


def escribir_csv(filas: list[dict[str, Any]], ruta_salida: Path) -> Path:
    """Escribe las filas con las columnas de :data:`COLUMNAS_CSV` (UTF-8, LF)."""
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with ruta_salida.open("w", encoding="utf-8", newline="") as manejador:
        escritor = csv.DictWriter(manejador, fieldnames=list(COLUMNAS_CSV), lineterminator="\n")
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
    return ruta_salida


def escribir_metadatos_exportacion(
    metadatos: dict[str, Any],
    *,
    ruta_video: Path,
    ruta_csv: Path,
    ruta_plantilla: Path,
    directorio_fotogramas: Path,
    lado: str,
) -> Path:
    """
    Escribe ``metadatos_exportacion.json`` junto a la plantilla.

    Las huellas SHA-256 del vídeo y del CSV del sistema permiten a
    ``analizar_nivel2.py`` advertir si se analiza contra un CSV distinto del que se
    exportó con estos fotogramas (por ejemplo, regenerado tras cambiar el pipeline).
    """
    contenido = {
        **metadatos,
        "nombre_video": ruta_video.name,
        "sha256_video": huella_sha256(ruta_video),
        "lado": lado,
        "csv_sistema": str(ruta_csv),
        "sha256_csv_sistema": huella_sha256(ruta_csv),
        "plantilla_sesion1": str(ruta_plantilla),
        "directorio_fotogramas": str(directorio_fotogramas),
        "fecha_exportacion": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    ruta = ruta_plantilla.parent / NOMBRE_METADATOS_EXPORTACION
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ruta


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta la serie angular estimada por el sistema y, opcionalmente, los fotogramas "
            "rotulados y la plantilla de medición para Tracker."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--video", required=True, help="Ruta al vídeo o nombre dentro del directorio de vídeos.")
    parser.add_argument("--salida", required=True, help="Ruta del CSV de salida.")
    parser.add_argument("--cada-n-frames", type=int, default=10, help="Exportar 1 de cada N fotogramas.")
    parser.add_argument("--max-frames", type=int, default=0, help="Limitar fotogramas leídos (0 = todos).")
    parser.add_argument(
        "--desde-frame",
        type=int,
        default=0,
        help="Primer fotograma (inclusive) del tramo a exportar; el muestreo se cuenta desde aquí.",
    )
    parser.add_argument(
        "--hasta-frame",
        type=int,
        default=None,
        help="Último fotograma (inclusive) del tramo a exportar (por defecto, hasta el final).",
    )
    parser.add_argument("--modelo", default=str(MODELO_POR_DEFECTO), help="Ruta al modelo .task de MediaPipe Pose.")
    parser.add_argument(
        "--directorio-videos",
        default=str(DIRECTORIO_VIDEOS_POR_DEFECTO),
        help="Directorio donde buscar el vídeo si --video es solo un nombre.",
    )
    parser.add_argument(
        "--solo-muestreados",
        action="store_true",
        help="Inferir solo los fotogramas exportados (más rápido, sin seguimiento temporal continuo).",
    )
    parser.add_argument(
        "--exportar-fotogramas",
        nargs="?",
        const=_DIRECTORIO_POR_DEFECTO,
        default=None,
        metavar="DIR",
        help=(
            "Escribir los fotogramas muestreados como PNG rotulados en DIR y la plantilla "
            f"{NOMBRE_PLANTILLA_SESION1} en su directorio padre. Sin DIR se usa "
            "validacion/datos/nivel2/<nombre_del_video>/frames/. Requiere --lado."
        ),
    )
    parser.add_argument(
        "--lado",
        choices=LADOS_VALIDOS,
        default=None,
        help="Pierna que se medirá en Tracker (la más cercana a la cámara). Obligatorio con --exportar-fotogramas.",
    )
    parser.add_argument(
        "--sobrescribir-fotogramas",
        action="store_true",
        help="Reemplazar fotogramas y plantilla vacía existentes (nunca una plantilla con mediciones).",
    )
    return parser


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de línea de comandos. Devuelve el código de salida del proceso."""
    parser = _construir_parser()
    args = parser.parse_args(argumentos)
    if args.exportar_fotogramas is not None and args.lado is None:
        parser.error("--exportar-fotogramas requiere --lado {izquierda,derecha}.")

    directorio_fotogramas: Path | None = None
    ruta_plantilla: Path | None = None
    try:
        ruta_video = resolver_video(args.video, Path(args.directorio_videos))
        if args.exportar_fotogramas is not None:
            if args.exportar_fotogramas == _DIRECTORIO_POR_DEFECTO:
                directorio_fotogramas = directorio_fotogramas_por_defecto(ruta_video)
            else:
                directorio_fotogramas = Path(args.exportar_fotogramas).expanduser().resolve()
            # Se comprueba ANTES de la inferencia: si hay datos que proteger, se aborta sin coste.
            ruta_plantilla = preparar_directorio_fotogramas(
                directorio_fotogramas, sobrescribir=args.sobrescribir_fotogramas
            )
        filas, metadatos = extraer_serie_angular(
            ruta_video,
            Path(args.modelo).expanduser().resolve(),
            cada_n_frames=args.cada_n_frames,
            max_frames=args.max_frames,
            solo_muestreados=args.solo_muestreados,
            directorio_fotogramas=directorio_fotogramas,
            desde_frame=args.desde_frame,
            hasta_frame=args.hasta_frame,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ruta_csv = escribir_csv(filas, Path(args.salida).expanduser())

    ruta_metadatos: Path | None = None
    if directorio_fotogramas is not None and ruta_plantilla is not None:
        escribir_plantilla(
            construir_filas_plantilla(filas, nombre_video=ruta_video.name, lado=args.lado),
            ruta_plantilla,
        )
        ruta_metadatos = escribir_metadatos_exportacion(
            metadatos,
            ruta_video=ruta_video,
            ruta_csv=ruta_csv.resolve(),
            ruta_plantilla=ruta_plantilla,
            directorio_fotogramas=directorio_fotogramas,
            lado=args.lado,
        )

    print("Exportación completada.")
    print(f"  Vídeo               : {metadatos['video']}")
    print(f"  Geometria           : {metadatos['ancho']}x{metadatos['alto']} a {metadatos['fps']:.2f} fps")
    print(f"  Frames leidos       : {metadatos['frames_leidos']} (inferidos: {metadatos['frames_inferidos']})")
    print(f"  Frames con pose     : {metadatos['frames_con_pose']} ({metadatos['tasa_deteccion'] * 100:.1f} %)")
    print(f"  Muestreo            : 1 de cada {metadatos['cada_n_frames']} frames")
    tramo_fin = metadatos["hasta_frame"] if metadatos["hasta_frame"] is not None else "final"
    print(f"  Tramo exportado     : {metadatos['desde_frame']} a {tramo_fin}")
    print(f"  Filas exportadas    : {metadatos['filas_exportadas']}")
    print(
        f"  Tiempo de proceso   : {metadatos['segundos_totales']:.2f} s "
        f"({metadatos['ms_por_frame_inferido']:.1f} ms por frame inferido)"
    )
    print(f"  CSV                 : {ruta_csv}")
    if directorio_fotogramas is not None:
        print(f"  Fotogramas PNG      : {len(metadatos['fotogramas_exportados'])} en {directorio_fotogramas}")
        print(f"  Plantilla sesión 1  : {ruta_plantilla}")
        print(f"  Metadatos           : {ruta_metadatos}")
        print(f"  Lado a medir        : {args.lado}")
    print("")
    if directorio_fotogramas is not None:
        print("Siguiente paso: abrir en Tracker el primer PNG (m0000.png) como secuencia de imágenes,")
        print("medir cada fotograma con el transportador y anotar el valor tal cual en la columna")
        print("'tracker_angulo_deg' de la plantilla (ver protocolo, sección 2.5).")
    else:
        print("Siguiente paso: repetir con --exportar-fotogramas --lado <izquierda|derecha> para")
        print("obtener los PNG rotulados y la plantilla de medición de Tracker.")
    print("")
    print("AVISO: estos angulos corresponden al pipeline de vision vigente AHORA.")
    print("Si cambia vision/biomechanics.py o vision/pose_extractor.py, regenere el CSV")
    print("antes de comparar. Compruebe ademas que el clip es de una sola toma, un solo")
    print("sujeto y plano sagital; si no lo es, la comparacion angular no es valida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
