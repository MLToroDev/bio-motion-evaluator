"""Sonda empirica: viabilidad del patron de referencia fisico del Nivel 1.

Prueba A: un patron de dos segmentos rigidos (proxy sintetico de carton pluma) sobre
fondo plano, sin cuerpo humano. Comprueba si BlazePose lo detecta.

Prueba B: fotogramas REALES de SentadillaProfunda.mp4 con un patron rigido opaco
superpuesto sobre muslo y pierna derechos (proxy de la ferula solidaria al segmento).
Compara los angulos de rodilla con y sin patron para acotar la perturbacion que el
propio instrumento introduce en la deteccion.
"""
from pathlib import Path

import cv2
import numpy as np

from vision.pose_extractor import extract_pose_bgr

RAIZ = Path("/Users/mateolondonotoro/.mounty/Disco C_C/Proyectos desarrollo/TRABAJO DE GRADO/Repositorio")
MODELO = RAIZ / "backend" / "models" / "pose_landmarker_full.task"
VIDEO = RAIZ / "tests" / "assets" / "videos" / "SentadillaProfunda.mp4"

RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE = 24, 26, 28


def prueba_a() -> None:
    """Patron de carton aislado, sin persona: se espera NO deteccion."""
    print("=== PRUEBA A: patron de dos segmentos sobre fondo plano (sin cuerpo) ===")
    for grados in (0, 45, 90, 135):
        img = np.full((1080, 1920, 3), 235, dtype=np.uint8)  # fondo claro uniforme
        eje = np.array([960, 700], dtype=np.float64)
        largo = 320.0
        # Brazo fijo hacia arriba (proximal) y brazo movil segun el angulo de flexion
        p_prox = eje + np.array([0.0, -largo])
        theta = np.deg2rad(180.0 - grados)  # angulo interno respecto al brazo proximal
        d = np.array([np.sin(theta), np.cos(theta)])
        p_dist = eje + d * largo
        for a, b in ((p_prox, eje), (eje, p_dist)):
            cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), (40, 40, 40), 34)
        cv2.circle(img, tuple(eje.astype(int)), 26, (0, 0, 0), -1)
        pf = extract_pose_bgr(img, MODELO)
        n_lm = len(pf.landmarks) if pf.landmarks else 0
        print(f"  angulo objetivo {grados:>3} deg -> ok={pf.ok}  landmarks={n_lm}  nota={pf.note!r}")


def _pixel(lm: dict, w: int, h: int) -> np.ndarray:
    return np.array([float(lm["x"]) * w, float(lm["y"]) * h], dtype=np.float64)


def _dibujar_patron(img: np.ndarray, cad: np.ndarray, rod: np.ndarray, tob: np.ndarray,
                    desplazamiento_lateral: float) -> np.ndarray:
    """Superpone una ferula rigida de dos brazos + disco de transportador en la rodilla."""
    out = img.copy()
    def perp(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        v = b - a
        n = np.linalg.norm(v)
        if n < 1e-6:
            return np.zeros(2)
        return np.array([-v[1], v[0]]) / n
    off_muslo = perp(cad, rod) * desplazamiento_lateral
    off_pierna = perp(rod, tob) * desplazamiento_lateral
    grosor = max(10, int(0.045 * np.linalg.norm(rod - cad)))
    cv2.line(out, tuple((cad + off_muslo).astype(int)), tuple((rod + off_muslo).astype(int)),
             (35, 35, 35), grosor)
    cv2.line(out, tuple((rod + off_pierna).astype(int)), tuple((tob + off_pierna).astype(int)),
             (35, 35, 35), grosor)
    radio = max(14, int(0.10 * np.linalg.norm(rod - cad)))
    centro = rod + (off_muslo + off_pierna) / 2.0
    cv2.circle(out, tuple(centro.astype(int)), radio, (250, 250, 250), -1)
    cv2.circle(out, tuple(centro.astype(int)), radio, (20, 20, 20), 3)
    cv2.circle(out, tuple(centro.astype(int)), 5, (20, 20, 20), -1)
    return out


def prueba_b() -> None:
    """Patron solidario a la pierna derecha sobre fotogramas reales."""
    print("\n=== PRUEBA B: patron rigido superpuesto sobre pierna derecha (fotogramas reales) ===")
    cap = cv2.VideoCapture(str(VIDEO))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = list(range(0, total, 10))
    resultados = {0.0: [], 1.0: []}  # desplazamiento lateral relativo -> lista de (base, con_patron)
    fallos = {0.0: 0, 1.0: 0}
    n_base_ok = 0
    for i in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        leido, bgr = cap.read()
        if not leido:
            continue
        h, w = bgr.shape[:2]
        base = extract_pose_bgr(bgr, MODELO)
        if not (base.ok and base.knees and base.landmarks):
            continue
        ang_base = base.knees.get("right_knee_flexion_angle_deg")
        if ang_base is None or np.isnan(ang_base):
            continue
        n_base_ok += 1
        cad = _pixel(base.landmarks[RIGHT_HIP], w, h)
        rod = _pixel(base.landmarks[RIGHT_KNEE], w, h)
        tob = _pixel(base.landmarks[RIGHT_ANKLE], w, h)
        largo_muslo = float(np.linalg.norm(rod - cad))
        for factor in (0.0, 1.0):
            img = _dibujar_patron(bgr, cad, rod, tob, desplazamiento_lateral=factor * 0.16 * largo_muslo)
            pf = extract_pose_bgr(img, MODELO)
            if pf.ok and pf.knees:
                a = pf.knees.get("right_knee_flexion_angle_deg")
                if a is not None and not np.isnan(a):
                    resultados[factor].append((float(ang_base), float(a)))
                    continue
            fallos[factor] += 1
    cap.release()

    print(f"  fotogramas muestreados={len(indices)}  con deteccion base valida={n_base_ok}")
    for factor, etiqueta in ((0.0, "patron centrado sobre el segmento (oclusion maxima)"),
                             (1.0, "patron desplazado 16% del muslo hacia lateral")):
        pares = resultados[factor]
        if not pares:
            print(f"  [{etiqueta}] sin detecciones validas (fallos={fallos[factor]})")
            continue
        base = np.array([p[0] for p in pares])
        con = np.array([p[1] for p in pares])
        d = con - base
        print(f"  [{etiqueta}]")
        print(f"    n={len(pares)}  perdidas_deteccion={fallos[factor]}")
        print(f"    MAE={np.abs(d).mean():.2f} deg  sesgo={d.mean():+.2f} deg  "
              f"RMSE={np.sqrt((d**2).mean()):.2f} deg  max|d|={np.abs(d).max():.2f} deg")


prueba_a()
prueba_b()
