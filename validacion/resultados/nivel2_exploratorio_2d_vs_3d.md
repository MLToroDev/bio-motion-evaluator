# Nivel 2 — Análisis exploratorio: flexión 2D frente a 3D

> **No preregistrado.** Hipótesis formulada después de ver el error por tramo de `nivel2_acuerdo.md`. No modifica el veredicto del Nivel 2 (no concluyente).

Fecha: 2026-10-27 22:16. Referencia: Tracker, sesión 1 (flexión = 180 − |θ|). Pierna izquierda. n = 75.

Control: la flexión 3D recalculada difiere de `serie_sistema.csv` en 0.00° como máximo.

| Ángulo del sistema | MAE (°) | Sesgo (°) | SD de las diferencias (°) |
|---|---|---|---|
| 3D, `world_landmarks` (el que reporta el sistema) | 8.13 | -2.43 | 9.17 |
| 2D, plano de la imagen (exploratorio) | 4.21 | -2.62 | 4.59 |

| Tramo de referencia (°) | n | MAE 3D (°) | MAE 2D (°) | Sesgo 2D (°) |
|---|---|---|---|---|
| [0, 30) | 34 | 6.78 | 4.59 | -2.90 |
| [30, 60) | 9 | 9.97 | 3.99 | -3.52 |
| [60, 90) | 9 | 14.18 | 6.13 | -6.04 |
| [90, 120) | 12 | 6.52 | 3.62 | -0.11 |
| [120, 180] | 11 | 7.61 | 2.26 | -0.98 |

**Lectura.** Si la flexión 2D concuerda mejor con Tracker que la 3D, la mayor parte de la diferencia sistema−Tracker se explica por la distinta dimensionalidad de las dos medidas y no por error de la estimación de pose.
