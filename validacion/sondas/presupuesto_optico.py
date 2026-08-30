"""Presupuesto optico de la captura: que se puede y que no se puede leer a 2-3.5 m en 1080p.

Determina (a) si el transportador impreso es legible desde el video y (b) cuanto angulo
vale un pixel de temblor de landmark, para saber a que error es sensible el sistema.
"""
import math

ANCHO_PX = 1920
ALTO_PX = 1080
FOV_H_DEG = 65.0  # tipico de camara trasera de telefono / webcam gran angular

print(f"Camara asumida: {ANCHO_PX}x{ALTO_PX}, FOV horizontal {FOV_H_DEG} deg")
print(f"\n{'d (m)':>7} {'ancho escena (m)':>17} {'mm por px':>11} {'alto escena (m)':>16} {'persona 1.75 m (px)':>21}")
for d in (2.0, 2.5, 3.0, 3.5):
    ancho = 2 * d * math.tan(math.radians(FOV_H_DEG / 2))
    mm_px = ancho * 1000 / ANCHO_PX
    alto = ancho * ALTO_PX / ANCHO_PX
    persona_px = 1.75 / alto * ALTO_PX
    print(f"{d:>7.1f} {ancho:>17.2f} {mm_px:>11.2f} {alto:>16.2f} {persona_px:>21.0f}")

print("\n=== Legibilidad del transportador impreso desde el video ===")
print("separacion entre marcas de 1 grado = R * 1 grado en radianes; se necesitan >= 3 px para distinguirlas")
for R_mm in (100, 150, 200):
    sep_mm = math.radians(1.0) * R_mm
    print(f"\n  Transportador R={R_mm} mm -> marcas de 1 deg separadas {sep_mm:.2f} mm")
    for d in (2.0, 3.0, 3.5):
        ancho = 2 * d * math.tan(math.radians(FOV_H_DEG / 2))
        mm_px = ancho * 1000 / ANCHO_PX
        px = sep_mm / mm_px
        # paso angular minimo que si alcanza 3 px
        paso_min = 3 * mm_px / R_mm
        paso_min_deg = math.degrees(paso_min)
        veredicto = "LEGIBLE" if px >= 3 else "NO LEGIBLE"
        print(f"    d={d:.1f} m: {px:.1f} px por marca -> {veredicto}; "
              f"paso minimo legible ~{paso_min_deg:.1f} deg")

print("\n=== Sensibilidad angular: cuanto vale 1 px de error de landmark ===")
print("segmento (muslo o pierna) de 0.40 m visto a distancia d; 1 grado en la rodilla")
print("desplaza el tobillo L*tan(1 deg) = 7.0 mm")
L_m = 0.40
desp_mm = L_m * 1000 * math.tan(math.radians(1.0))
print(f"{'d (m)':>7} {'segmento (px)':>15} {'1 grado = ? px':>16} {'1 px = ? grados':>17}")
for d in (2.0, 2.5, 3.0, 3.5):
    ancho = 2 * d * math.tan(math.radians(FOV_H_DEG / 2))
    mm_px = ancho * 1000 / ANCHO_PX
    seg_px = L_m * 1000 / mm_px
    px_por_grado = desp_mm / mm_px
    print(f"{d:>7.1f} {seg_px:>15.0f} {px_por_grado:>16.2f} {1/px_por_grado:>17.2f}")
