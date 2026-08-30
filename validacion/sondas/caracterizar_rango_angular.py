"""Caracteriza el rango angular real y la tasa de deteccion de los videos de referencia.

Sirve para dimensionar el Nivel 2 del protocolo de validacion (video-goniometria manual):
cuantas mediciones manuales implica muestrear cada N fotogramas y que tramos angulares
quedan efectivamente cubiertos.
"""
from pathlib import Path
import time

import cv2
import numpy as np

from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor
from vision.pose_extractor import extract_pose_bgr_video

RAIZ = Path("/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio")
MODELO = RAIZ / "backend" / "models" / "pose_landmarker_full.task"
VIDEOS = ["SentadillaProfunda.mp4", "Running.mp4"]
PASO_MUESTREO = 10

TRAMOS = [(0, 30), (30, 60), (60, 90), (90, 120), (120, 180)]


def procesar(nombre: str) -> None:
    ruta = RAIZ / "tests" / "assets" / "videos" / nombre
    cap = cv2.VideoCapture(str(ruta))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    reset_pose_video_timestamp_anchor()

    idx = 0
    ok_count = 0
    flex_izq: list[float] = []
    flex_der: list[float] = []
    idx_muestreados_ok = 0
    idx_muestreados_total = 0
    t0 = time.perf_counter()
    while True:
        leido, bgr = cap.read()
        if not leido:
            break
        ts_ms = int(round(idx * 1000.0 / fps)) if fps > 0 else idx * 40
        pf = extract_pose_bgr_video(bgr, MODELO, ts_ms)
        es_muestra = (idx % PASO_MUESTREO == 0)
        if es_muestra:
            idx_muestreados_total += 1
        if pf.ok and pf.knees:
            li = pf.knees.get("left_knee_flexion_angle_deg")
            de = pf.knees.get("right_knee_flexion_angle_deg")
            # Ambos lados deben ser validos: si uno falta, el par no sirve para
            # la asimetria y meter un NaN envenenaria todos los estadisticos.
            valido_izq = li is not None and not np.isnan(li)
            valido_der = de is not None and not np.isnan(de)
            if valido_izq and valido_der:
                ok_count += 1
                flex_izq.append(float(li))
                flex_der.append(float(de))
                if es_muestra:
                    idx_muestreados_ok += 1
        idx += 1
    cap.release()
    dt = time.perf_counter() - t0

    a_izq = np.array(flex_izq)
    a_der = np.array(flex_der)
    print(f"\n=== {nombre} ===")
    print(f"fotogramas leidos={idx} total_meta={total} fps={fps:.2f}")
    print(f"tiempo_proceso={dt:.1f}s  ms/frame={1000*dt/max(idx,1):.1f}  fps_efectivo={idx/dt:.2f}")
    print(f"deteccion_con_angulo={ok_count}/{idx} = {100.0*ok_count/max(idx,1):.1f}%")
    print(f"muestras cada {PASO_MUESTREO}: {idx_muestreados_total} previstas, {idx_muestreados_ok} con angulo valido")
    for etiqueta, arr in (("izquierda", a_izq), ("derecha", a_der)):
        if arr.size == 0:
            print(f"  flexion {etiqueta}: sin datos")
            continue
        print(f"  flexion {etiqueta} deg: min={arr.min():.1f} p05={np.percentile(arr,5):.1f} "
              f"mediana={np.median(arr):.1f} p95={np.percentile(arr,95):.1f} max={arr.max():.1f}")
    if a_izq.size:
        print("  cobertura por tramo (fotogramas, rodilla izquierda):")
        for lo, hi in TRAMOS:
            n = int(((a_izq >= lo) & (a_izq < hi)).sum())
            print(f"    [{lo:>3},{hi:>3}) deg: {n:>5}  ({100.0*n/a_izq.size:5.1f} %)")
    if a_izq.size and a_der.size:
        asim = np.abs(a_izq - a_der)
        print(f"  asimetria |izq-der| deg: media={asim.mean():.1f} mediana={np.median(asim):.1f} max={asim.max():.1f}")


for v in VIDEOS:
    procesar(v)
