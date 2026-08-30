#!/usr/bin/env python3
"""
Exporta la serie angular estimada por el sistema para compararla con Kinovea.

Uso previsto en la validación: se procesa un vídeo con el mismo pipeline de producción
(MediaPipe Pose en servidor + ``vision.biomechanics``) y se vuelca a CSV el ángulo de
flexión de rodilla de los fotogramas **muestreados**, con su índice de frame y su
marca temporal. El autor abre ese mismo vídeo en Kinovea, mide a mano exactamente esos
fotogramas y rellena la columna vacía ``angulo_manual_kinovea_deg``. El CSV resultante
se pasa después a ``validacion/analisis/acuerdo.py`` para obtener MAE, RMSE, sesgo,
Bland-Altman e ICC(2,1).

Medir a mano los 183 fotogramas de un clip es inviable, por eso existe
``--cada-n-frames``: con el valor por defecto (10) se obtiene una muestra manejable
(unos 19 fotogramas) que sigue cubriendo todo el rango articular del movimiento.

Nota sobre el muestreo: por defecto se ejecuta la inferencia sobre **todos** los
fotogramas en orden temporal (``RunningMode.VIDEO``), aunque solo se escriban al CSV
los muestreados. Así el seguimiento temporal de MediaPipe es idéntico al del análisis
real y el ángulo exportado es el que produciría el sistema en producción. Con
``--solo-muestreados`` se salta la inferencia de los fotogramas intermedios (más
rápido, pero sin continuidad de seguimiento; útil solo para pruebas exploratorias).

Ejemplo (desde ``backend/``)::

    PYTHONPATH=. python ../validacion/analisis/exportar_para_kinovea.py \
        --video SentadillaProfunda.mp4 \
        --salida ../validacion/resultados/serie_angular_SentadillaProfunda.csv \
        --cada-n-frames 10

ADVERTENCIA 1 - El CSV caduca con el pipeline
---------------------------------------------
Los angulos exportados son la salida del pipeline de vision **en el momento de la
exportacion**. Cualquier cambio en ``vision.biomechanics`` o en
``vision.pose_extractor`` (por ejemplo el paso de landmarks normalizados a
``world_landmarks``) invalida el CSV: las mediciones manuales de Kinovea quedarian
comparadas contra una estimacion que el sistema ya no produce. Antes de rellenar la
columna manual, y de nuevo antes de calcular el acuerdo, hay que **regenerar el CSV**
con el codigo vigente y comprobar que los angulos no han cambiado.

ADVERTENCIA 2 - El video debe ser apto para goniometria
-------------------------------------------------------
Este script no comprueba la validez del material de entrada. Para que el CSV sirva
como base de una comparacion de exactitud angular, el clip debe cumplir:

1. **Una sola toma continua** y **un solo sujeto**. Un video de montaje (varias tomas
   pegadas) produce una serie que parece una trayectoria articular pero no lo es, y
   cualquier lectura biomecanica de ella (fases, asimetria por repeticion) es falsa.
2. **Plano sagital** respecto de la rodilla medida. Kinovea mide angulos en 2D sobre el
   plano de la imagen: en plano frontal la flexion de rodilla aparece escorzada y ni la
   medicion manual ni la comparacion tienen sentido anatomico.
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
import sys
import time
from pathlib import Path
from typing import Any

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
_RAIZ_BACKEND = _RAIZ_REPOSITORIO / "backend"
if str(_RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(_RAIZ_BACKEND))

try:
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

#: Directorio por defecto con los vídeos de referencia del repositorio.
DIRECTORIO_VIDEOS_POR_DEFECTO = _RAIZ_REPOSITORIO / "tests" / "assets" / "videos"

#: Modelo de pose por defecto (el mismo que sirve el backend en producción).
MODELO_POR_DEFECTO = _RAIZ_BACKEND / "models" / "pose_landmarker_full.task"

#: Columnas del CSV. ``angulo_manual_kinovea_deg`` se exporta vacía a propósito:
#: es la casilla que el evaluador rellena tras medir en Kinovea.
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


def extraer_serie_angular(
    ruta_video: Path,
    ruta_modelo: Path,
    *,
    cada_n_frames: int = 10,
    max_frames: int = 0,
    solo_muestreados: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Procesa el vídeo y devuelve ``(filas_muestreadas, metadatos)``.

    ``filas_muestreadas`` contiene un diccionario por fotograma exportado, con las
    claves de :data:`COLUMNAS_CSV`. ``metadatos`` recoge geometría del vídeo, fotogramas
    leídos, tasa de detección de pose y tiempos de proceso, que son la evidencia de
    rendimiento que acompaña a la exactitud.
    """
    if cada_n_frames < 1:
        raise ValueError("cada_n_frames debe ser >= 1.")
    if not ruta_modelo.is_file():
        raise FileNotFoundError(f"No se encontró el modelo de pose: {ruta_modelo}")

    # MediaPipe exige marcas de tiempo estrictamente crecientes por instancia:
    # al empezar un clip nuevo hay que reiniciar el ancla temporal.
    reset_pose_video_timestamp_anchor()

    filas: list[dict[str, Any]] = []
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
            frame = fuente.get_frame()
            if frame is None:
                break

            indice = frames_leidos
            frames_leidos += 1
            es_muestreado = indice % cada_n_frames == 0
            if solo_muestreados and not es_muestreado:
                continue

            timestamp_ms = int(round(indice * 1000.0 / fps))
            resultado = extract_pose_bgr_video(frame, ruta_modelo, timestamp_ms)
            frames_inferidos += 1
            if resultado.ok and resultado.knees:
                frames_con_pose += 1

            if not es_muestreado:
                continue

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
        "solo_muestreados": solo_muestreados,
        "segundos_totales": transcurrido,
        "ms_por_frame_inferido": (transcurrido * 1000.0 / frames_inferidos) if frames_inferidos else 0.0,
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


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta la serie angular estimada por el sistema para medirla en Kinovea.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--video", required=True, help="Ruta al vídeo o nombre dentro del directorio de vídeos.")
    parser.add_argument("--salida", required=True, help="Ruta del CSV de salida.")
    parser.add_argument("--cada-n-frames", type=int, default=10, help="Exportar 1 de cada N fotogramas.")
    parser.add_argument("--max-frames", type=int, default=0, help="Limitar fotogramas leídos (0 = todos).")
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
    return parser


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de línea de comandos. Devuelve el código de salida del proceso."""
    parser = _construir_parser()
    args = parser.parse_args(argumentos)

    try:
        ruta_video = resolver_video(args.video, Path(args.directorio_videos))
        filas, metadatos = extraer_serie_angular(
            ruta_video,
            Path(args.modelo).expanduser().resolve(),
            cada_n_frames=args.cada_n_frames,
            max_frames=args.max_frames,
            solo_muestreados=args.solo_muestreados,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ruta_csv = escribir_csv(filas, Path(args.salida).expanduser())

    print("Exportación completada.")
    print(f"  Vídeo               : {metadatos['video']}")
    print(f"  Geometria           : {metadatos['ancho']}x{metadatos['alto']} a {metadatos['fps']:.2f} fps")
    print(f"  Frames leidos       : {metadatos['frames_leidos']} (inferidos: {metadatos['frames_inferidos']})")
    print(f"  Frames con pose     : {metadatos['frames_con_pose']} ({metadatos['tasa_deteccion'] * 100:.1f} %)")
    print(f"  Muestreo            : 1 de cada {metadatos['cada_n_frames']} frames")
    print(f"  Filas exportadas    : {metadatos['filas_exportadas']}")
    print(
        f"  Tiempo de proceso   : {metadatos['segundos_totales']:.2f} s "
        f"({metadatos['ms_por_frame_inferido']:.1f} ms por frame inferido)"
    )
    print(f"  CSV                 : {ruta_csv}")
    print("")
    print("Siguiente paso: abrir el mismo video en Kinovea, medir los fotogramas listados")
    print("en 'frame_index' y rellenar la columna 'angulo_manual_kinovea_deg'.")
    print("")
    print("AVISO: estos angulos corresponden al pipeline de vision vigente AHORA.")
    print("Si cambia vision/biomechanics.py o vision/pose_extractor.py, regenere el CSV")
    print("antes de comparar. Compruebe ademas que el clip es de una sola toma, un solo")
    print("sujeto y plano sagital; si no lo es, la comparacion angular no es valida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
