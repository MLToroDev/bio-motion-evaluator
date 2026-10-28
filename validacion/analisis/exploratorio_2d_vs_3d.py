#!/usr/bin/env python3
"""
Análisis EXPLORATORIO (no preregistrado) del Nivel 2: flexión 2D frente a 3D.

Hipótesis, formulada después de ver el error sistema-Tracker por tramo angular
(``validacion/resultados/nivel2_acuerdo.md``): el sistema calcula la flexión de rodilla en
3D sobre ``world_landmarks``, mientras que Tracker mide un ángulo 2D proyectado en el plano
de la imagen. Con la rodilla fuera del plano sagital durante la sentadilla, las dos
cantidades difieren aunque ninguna sea errónea.

El script repite la inferencia del sistema sobre el clip en el mismo modo que la exportación
(``RunningMode.VIDEO``, todos los fotogramas desde el 0 hasta el último muestreado) y, en
cada fotograma medido en la sesión 1 de Tracker, calcula:

- la flexión 3D a partir de ``world_landmarks`` (control: debe coincidir con
  ``serie_sistema.csv``), y
- la flexión 2D a partir de los landmarks normalizados escalados a píxeles.

Este análisis NO modifica el veredicto preregistrado del Nivel 2.

Uso (desde ``backend/``)::

    PYTHONPATH=. python ../validacion/analisis/exploratorio_2d_vs_3d.py \
        --video ../../IMG_6310.mov \
        --clip ../validacion/datos/nivel2/IMG_6310 \
        --salida ../validacion/resultados/nivel2_exploratorio_2d_vs_3d.md
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np

_RAIZ_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(_RAIZ_BACKEND))

from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor  # noqa: E402
from vision.pose_extractor import extract_pose_bgr_video  # noqa: E402
from vision.processor import VideoSource  # noqa: E402

#: Índices MediaPipe Pose de la pierna izquierda: cadera, rodilla, tobillo.
CADERA, RODILLA, TOBILLO = 23, 25, 27
TRAMOS = ((0, 30), (30, 60), (60, 90), (90, 120), (120, 181))
MODELO_POR_DEFECTO = _RAIZ_BACKEND / "models" / "pose_landmarker_full.task"


def flexion_deg(cadera: np.ndarray, rodilla: np.ndarray, tobillo: np.ndarray) -> float:
    """Flexión = 180 − ángulo interno en la rodilla (misma convención que el sistema)."""
    u, v = cadera - rodilla, tobillo - rodilla
    coseno = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))
    return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, coseno))))


def resumen(diferencias: np.ndarray) -> tuple[float, float, float]:
    return (float(np.mean(np.abs(diferencias))), float(np.mean(diferencias)),
            float(np.std(diferencias, ddof=1)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--video", required=True, help="Ruta al clip de validación.")
    parser.add_argument("--clip", required=True, help="Carpeta del clip en validacion/datos/nivel2/.")
    parser.add_argument("--salida", required=True, help="Informe Markdown de salida.")
    parser.add_argument("--modelo", default=str(MODELO_POR_DEFECTO), help="Modelo .task de MediaPipe Pose.")
    args = parser.parse_args()

    clip = Path(args.clip)
    sesion1 = {int(f["frame_idx"]): f for f in csv.DictReader(open(clip / "nivel2_tracker_sesion1.csv", encoding="utf-8"))}
    sistema = {int(f["frame_index"]): float(f["left_knee_flexion_angle_deg"])
               for f in csv.DictReader(open(clip / "serie_sistema.csv", encoding="utf-8"))}
    ultimo = max(sesion1)

    reset_pose_video_timestamp_anchor()
    pares: list[tuple[int, float, float, float, float]] = []
    with VideoSource(source_type="file", file_path=args.video) as fuente:
        ancho, alto, fps = fuente.stream_geometry()
        indice = 0
        while indice <= ultimo:
            fotograma = fuente.get_frame()
            if fotograma is None:
                break
            resultado = extract_pose_bgr_video(fotograma, Path(args.modelo), int(round(indice * 1000.0 / fps)))
            valor = sesion1.get(indice, {}).get("tracker_angulo_deg", "")
            if valor and resultado.ok and resultado.landmarks and resultado.world_landmarks:
                plano = lambda k: np.array([resultado.landmarks[k]["x"] * ancho, resultado.landmarks[k]["y"] * alto])
                mundo = lambda k: np.array([resultado.world_landmarks[k][e] for e in ("x", "y", "z")])
                pares.append((indice, 180.0 - abs(float(valor)), sistema[indice],
                              flexion_deg(mundo(CADERA), mundo(RODILLA), mundo(TOBILLO)),
                              flexion_deg(plano(CADERA), plano(RODILLA), plano(TOBILLO))))
            indice += 1

    datos = np.array([p[1:] for p in pares])
    tracker, sist, flex3d, flex2d = datos.T
    control = float(np.max(np.abs(sist - flex3d)))
    lineas = [
        "# Nivel 2 — Análisis exploratorio: flexión 2D frente a 3D",
        "",
        "> **No preregistrado.** Hipótesis formulada después de ver el error por tramo de "
        "`nivel2_acuerdo.md`. No modifica el veredicto del Nivel 2 (no concluyente).",
        "",
        f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}. Referencia: Tracker, sesión 1 (flexión = 180 − |θ|). "
        f"Pierna izquierda. n = {len(pares)}.",
        "",
        f"Control: la flexión 3D recalculada difiere de `serie_sistema.csv` en {control:.2f}° como máximo.",
        "",
        "| Ángulo del sistema | MAE (°) | Sesgo (°) | SD de las diferencias (°) |",
        "|---|---|---|---|",
    ]
    for nombre, estimado in (("3D, `world_landmarks` (el que reporta el sistema)", sist),
                             ("2D, plano de la imagen (exploratorio)", flex2d)):
        mae, sesgo, sd = resumen(estimado - tracker)
        lineas.append(f"| {nombre} | {mae:.2f} | {sesgo:+.2f} | {sd:.2f} |")
    lineas += ["", "| Tramo de referencia (°) | n | MAE 3D (°) | MAE 2D (°) | Sesgo 2D (°) |", "|---|---|---|---|---|"]
    for bajo, alto_t in TRAMOS:
        m = (tracker >= bajo) & (tracker < alto_t)
        lineas.append(f"| [{bajo}, {min(alto_t, 180)}{']' if alto_t > 180 else ')'} | {int(m.sum())} | "
                      f"{np.mean(np.abs(sist[m] - tracker[m])):.2f} | {np.mean(np.abs(flex2d[m] - tracker[m])):.2f} | "
                      f"{np.mean(flex2d[m] - tracker[m]):+.2f} |")
    lineas += ["", "**Lectura.** Si la flexión 2D concuerda mejor con Tracker que la 3D, la mayor parte de la "
               "diferencia sistema−Tracker se explica por la distinta dimensionalidad de las dos medidas "
               "y no por error de la estimación de pose.", ""]
    Path(args.salida).write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
