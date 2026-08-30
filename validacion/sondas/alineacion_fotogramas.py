"""Verifica la correspondencia fotograma <-> tiempo y la fiabilidad del posicionamiento.

Decide si el protocolo Nivel 2 puede alinear Kinovea y el CSV por numero de fotograma
o si debe exportar los fotogramas muestreados como imagenes con el indice grabado.
"""
import hashlib
from pathlib import Path

import cv2

RAIZ = Path("/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio")
VIDEO = RAIZ / "tests" / "assets" / "videos" / "SentadillaProfunda.mp4"

INDICES = [0, 10, 50, 100, 180]


def hash_frame(bgr) -> str:
    return hashlib.md5(bgr.tobytes()).hexdigest()[:12]


# Lectura secuencial: referencia
cap = cv2.VideoCapture(str(VIDEO))
fps = float(cap.get(cv2.CAP_PROP_FPS))
secuencial = {}
i = 0
while True:
    ok, bgr = cap.read()
    if not ok:
        break
    if i in INDICES:
        secuencial[i] = (hash_frame(bgr), float(cap.get(cv2.CAP_PROP_POS_MSEC)))
    i += 1
cap.release()
print(f"fps declarado = {fps:.4f}   fotogramas leidos secuencialmente = {i}")

# Lectura por posicionamiento directo
cap = cv2.VideoCapture(str(VIDEO))
print(f"\n{'idx':>5} {'t=idx/fps (ms)':>16} {'POS_MSEC seq':>14} {'hash seq':>14} {'hash seek':>14} {'coincide':>9}")
for idx in INDICES:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, bgr = cap.read()
    h_seek = hash_frame(bgr) if ok else "NO LEE"
    h_seq, ms_seq = secuencial.get(idx, ("-", float("nan")))
    t_calc = 1000.0 * idx / fps
    print(f"{idx:>5} {t_calc:>16.2f} {ms_seq:>14.2f} {h_seq:>14} {h_seek:>14} {str(h_seq == h_seek):>9}")
cap.release()
