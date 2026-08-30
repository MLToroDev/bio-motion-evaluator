"""Inventario real de los videos de referencia: resolucion, fps, fotogramas, duracion."""
from pathlib import Path
import cv2

CARPETA = Path("/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio/tests/assets/videos")

filas = []
for ruta in sorted(CARPETA.glob("*.mp4")):
    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        filas.append((ruta.name, "NO ABRE", "", "", "", ""))
        continue
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    dur = n / fps if fps > 0 else 0.0
    muestras = len(range(0, n, 10))
    filas.append((ruta.name, f"{w}x{h}", f"{fps:.2f}", str(n), f"{dur:.2f}", str(muestras)))

print(f"{'archivo':<60} {'res':<11} {'fps':<7} {'frames':<7} {'seg':<7} {'muestras@10'}")
for f in filas:
    print(f"{f[0][:59]:<60} {f[1]:<11} {f[2]:<7} {f[3]:<7} {f[4]:<7} {f[5]}")
