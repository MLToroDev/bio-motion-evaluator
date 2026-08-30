"""Propagacion del desalineacion del transportador al angulo leido.

Modelo A (montaje pobre): cada brazo queda definido por el eje del transportador y un
unico anclaje distal. Si el eje esta desplazado 'e' perpendicular al segmento y el
anclaje distal esta a 'L' del centro articular, el brazo se desvia del eje longitudinal
del segmento un angulo atan(e/L). Ese error entra 1:1 en la lectura.

Modelo B (montaje recomendado): cada brazo se fija con DOS anclajes separados 's' sobre
el propio segmento; la direccion del brazo la impone el segmento y no el eje. El error
lo domina la incertidumbre de colocacion 'u' de cada anclaje: atan(2u/s) en el peor caso.
"""
import math

print("=== Modelo A: brazo definido por eje desplazado + un anclaje distal ===")
print("error angular por brazo = atan(e/L), en grados")
print(f"{'e (mm)':>8} | " + " | ".join(f"L={L} mm" for L in (250, 300, 350)))
for e in (5, 10, 15, 20, 30, 40):
    fila = [f"{math.degrees(math.atan(e / L)):6.2f}" for L in (250, 300, 350)]
    print(f"{e:>8} | " + " | ".join(f"{v:>9}" for v in fila))
print("Peor caso de lectura (los dos brazos se desvian en sentido opuesto): el doble.")

print("\n=== Modelo B: brazo fijado con dos anclajes separados s, incertidumbre u por anclaje ===")
print("error angular por brazo = atan(2u/s), en grados")
print(f"{'u (mm)':>8} | " + " | ".join(f"s={s} mm" for s in (150, 200, 250)))
for u in (1, 2, 3, 5):
    fila = [f"{math.degrees(math.atan(2 * u / s)):6.2f}" for s in (150, 200, 250)]
    print(f"{u:>8} | " + " | ".join(f"{v:>9}" for v in fila))

print("\n=== Tolerancia de colocacion para no gastar mas de X grados por brazo ===")
print("desplazamiento lateral maximo del extremo del brazo = L * tan(X)")
for X in (0.5, 1.0, 2.0):
    fila = [f"{L * math.tan(math.radians(X)):5.1f} mm" for L in (250, 300, 350)]
    print(f"  X={X:>4} deg -> " + " | ".join(f"L={L}: {v}" for L, v in zip((250, 300, 350), fila)))

print("\n=== Resolucion de lectura del transportador impreso ===")
print("un transportador de radio R con marcas cada 1 grado: separacion entre marcas")
for R in (60, 80, 100, 120):
    print(f"  R={R:>3} mm -> {math.radians(1.0) * R:.2f} mm entre marcas de 1 grado")
