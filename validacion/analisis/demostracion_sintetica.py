#!/usr/bin/env python3
"""
Demostración de punta a punta del instrumento de acuerdo con DATOS SINTÉTICOS.

Genera una serie angular de sentadilla con propiedades conocidas (sesgo, ruido
heterocedástico, valores atípicos y fotogramas perdidos), la analiza con
``validacion/analisis/acuerdo.py`` y escribe el informe de ejemplo y la figura de
Bland-Altman en ``validacion/resultados/``.

IMPORTANTE: la salida NO es evidencia de validación del sistema. Es la prueba de que
el instrumento estadístico recupera parámetros inyectados a propósito. El informe
generado lo advierte en su encabezado.

Ejecución (reproducible, semilla fija 42)::

    python validacion/analisis/demostracion_sintetica.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from validacion.analisis.acuerdo import (  # noqa: E402
    figura_bland_altman,
    formatear_resumen_markdown,
    resumen_acuerdo,
)

SEMILLA = 42
FRECUENCIA_MUESTREO_HZ = 25.0
NUMERO_REPETICIONES = 6
DURACION_REPETICION_S = 2.6
ANGULO_MINIMO_DEG = 8.0
ANGULO_MAXIMO_DEG = 132.0

#: Parámetros de error inyectados en la serie "estimada" (los que debe recuperar el análisis).
SESGO_INYECTADO_DEG = 2.5
RUIDO_BASE_DEG = 1.4
RUIDO_ADICIONAL_EN_FLEXION_PROFUNDA_DEG = 3.0
NUMERO_ATIPICOS = 6
DESPLAZAMIENTO_ATIPICO_DEG = 14.0
NUMERO_FOTOGRAMAS_PERDIDOS = 8
#: Umbral de flexion profunda donde se concentran las perdidas de seguimiento simuladas.
UMBRAL_FLEXION_PROFUNDA_DEG = 110.0

DIRECTORIO_RESULTADOS = _RAIZ_REPOSITORIO / "validacion" / "resultados"
RUTA_INFORME = DIRECTORIO_RESULTADOS / "ejemplo_acuerdo_sintetico.md"
RUTA_FIGURA = DIRECTORIO_RESULTADOS / "ejemplo_bland_altman_sintetico.png"


def generar_serie_referencia() -> np.ndarray:
    """
    Serie angular de referencia: flexión de rodilla en sentadillas consecutivas.

    Perfil coseno suavizado entre :data:`ANGULO_MINIMO_DEG` y :data:`ANGULO_MAXIMO_DEG`,
    muestreado a 25 Hz, que imita la forma de onda de una sentadilla profunda medida
    con goniometría de referencia.
    """
    n = int(round(NUMERO_REPETICIONES * DURACION_REPETICION_S * FRECUENCIA_MUESTREO_HZ))
    tiempo = np.arange(n) / FRECUENCIA_MUESTREO_HZ
    fase = 2.0 * math.pi * tiempo / DURACION_REPETICION_S
    amplitud = (ANGULO_MAXIMO_DEG - ANGULO_MINIMO_DEG) / 2.0
    return ANGULO_MINIMO_DEG + amplitud * (1.0 - np.cos(fase))


def generar_serie_estimada(referencia: np.ndarray, generador: np.random.Generator) -> np.ndarray:
    """
    Serie "estimada" con degradaciones realistas de una estimación de pose monocular.

    Se inyectan, en este orden: sesgo constante, ruido gaussiano cuya desviación crece
    con el ángulo (autooclusión y escorzo en flexión profunda), valores atípicos que
    simulan pérdidas puntuales de seguimiento y fotogramas sin detección (NaN).
    """
    proporcion_flexion = (referencia - ANGULO_MINIMO_DEG) / (ANGULO_MAXIMO_DEG - ANGULO_MINIMO_DEG)
    sigma = RUIDO_BASE_DEG + RUIDO_ADICIONAL_EN_FLEXION_PROFUNDA_DEG * proporcion_flexion
    estimado = referencia + SESGO_INYECTADO_DEG + generador.normal(0.0, 1.0, size=referencia.size) * sigma

    # Los atipicos se situan en flexion profunda a proposito: en la practica las
    # perdidas de seguimiento aparecen cuando el muslo ocluye la pierna al bajar.
    candidatos_atipicos = np.flatnonzero(referencia >= UMBRAL_FLEXION_PROFUNDA_DEG)
    indices_atipicos = generador.choice(candidatos_atipicos, size=NUMERO_ATIPICOS, replace=False)
    estimado[indices_atipicos] += DESPLAZAMIENTO_ATIPICO_DEG

    disponibles = np.setdiff1d(np.arange(referencia.size), indices_atipicos)
    indices_perdidos = generador.choice(disponibles, size=NUMERO_FOTOGRAMAS_PERDIDOS, replace=False)
    estimado[indices_perdidos] = np.nan
    return estimado


def _bloque_advertencia() -> str:
    """Encabezado de advertencia que impide confundir esta salida con validación real."""
    return (
        "# Ejemplo de salida del instrumento de acuerdo (DATOS SINTÉTICOS)\n\n"
        "> **AVISO. ESTOS NO SON RESULTADOS DE VALIDACIÓN REAL.**\n"
        ">\n"
        "> Las dos series comparadas en este documento fueron **generadas por computador**\n"
        "> con parámetros de error conocidos e inyectados a propósito. No proceden de\n"
        "> ningún goniómetro, de ninguna medición en Kinovea ni de ningún sujeto humano.\n"
        ">\n"
        "> El único objetivo de este archivo es demostrar que el módulo\n"
        "> `validacion/analisis/acuerdo.py` funciona de punta a punta y que recupera los\n"
        "> parámetros que se le inyectaron. **No debe citarse en la memoria como evidencia\n"
        "> de la exactitud del sistema Bio-Motion Evaluator.** Los resultados reales se\n"
        "> producirán con este mismo instrumento cuando se ejecute el protocolo de\n"
        "> validación física con el método de referencia.\n\n"
    )


def construir_informe(referencia: np.ndarray, estimado: np.ndarray, resumen: dict) -> str:
    """Compone el informe Markdown completo (advertencia, parámetros, resultados)."""
    ba = resumen["bland_altman"]
    sigma_media_esperada = RUIDO_BASE_DEG + RUIDO_ADICIONAL_EN_FLEXION_PROFUNDA_DEG * 0.5

    partes = [
        _bloque_advertencia(),
        "## 1. Qué se está demostrando\n\n"
        "Se comparan dos series angulares sintéticas de sentadilla: una que hace de\n"
        "**método de referencia** y otra que hace de **sistema estimado**, degradada con\n"
        "errores conocidos. Si el instrumento es correcto, debe devolver esos mismos\n"
        "errores. La comparación entre lo inyectado y lo recuperado es la verificación.\n\n"
        "## 2. Datos sintéticos generados\n\n"
        f"- Semilla de reproducibilidad: `numpy.random.default_rng({SEMILLA})`.\n"
        f"- Frecuencia de muestreo simulada: {FRECUENCIA_MUESTREO_HZ:.0f} Hz.\n"
        f"- {NUMERO_REPETICIONES} repeticiones de {DURACION_REPETICION_S:.1f} s "
        f"({referencia.size} muestras en total).\n"
        f"- Rango angular de referencia: {ANGULO_MINIMO_DEG:.0f} a {ANGULO_MAXIMO_DEG:.0f} grados de flexión.\n"
        f"- Sesgo inyectado: {SESGO_INYECTADO_DEG:+.1f} grados (el sistema sobreestima).\n"
        f"- Ruido gaussiano heterocedástico: sigma de {RUIDO_BASE_DEG:.1f} grados en extensión "
        f"hasta {RUIDO_BASE_DEG + RUIDO_ADICIONAL_EN_FLEXION_PROFUNDA_DEG:.1f} grados en flexión máxima.\n"
        f"- {NUMERO_ATIPICOS} valores atípicos de {DESPLAZAMIENTO_ATIPICO_DEG:+.0f} grados "
        "(pérdidas puntuales de seguimiento).\n"
        f"- {NUMERO_FOTOGRAMAS_PERDIDOS} fotogramas sin detección (NaN), que el módulo debe descartar.\n\n"
        "## 3. Verificación: parámetro inyectado frente a parámetro recuperado\n\n"
        "| Parámetro | Inyectado | Recuperado por el módulo |\n"
        "| --- | --- | --- |\n"
        f"| Sesgo (grados) | {SESGO_INYECTADO_DEG:+.2f} | {resumen['sesgo']:+.2f} |\n"
        f"| Desviación estándar de las diferencias (grados) | ~{sigma_media_esperada:.2f} (media del sigma variable) "
        f"| {ba['desviacion_estandar_diferencias']:.2f} |\n"
        f"| Fotogramas descartados | {NUMERO_FOTOGRAMAS_PERDIDOS} | {resumen['n_pares_descartados']} |\n"
        f"| Pares analizados | {referencia.size - NUMERO_FOTOGRAMAS_PERDIDOS} | {resumen['n']} |\n\n"
        "La desviación recuperada supera ligeramente la media del sigma inyectado porque los\n"
        "valores atípicos añaden dispersión; esa misma separación se observa entre MAE y RMSE.\n\n"
        "## 4. Resultado completo del análisis\n\n",
        formatear_resumen_markdown(resumen, titulo="Acuerdo entre serie de referencia y serie estimada (sintéticas)"),
        "\n## 5. Lectura del desglose por tramo\n\n"
        "El ruido se inyectó creciente con el ángulo y los valores atípicos se situaron en\n"
        "flexión profunda. El desglose lo detecta: la desviación típica de las diferencias\n"
        "crece de forma monótona desde el tramo de extensión hasta el de flexión máxima, y\n"
        "el RMSE hace lo mismo. El MAE muestra la tendencia de forma menos nítida porque\n"
        "está dominado por el sesgo constante, que actúa igual en todo el rango; por eso el\n"
        "instrumento reporta las tres métricas juntas y no solo el MAE.\n\n"
        "Este es exactamente el tipo de hallazgo que el instrumento debe hacer visible sobre\n"
        "los datos reales: el error de una estimación de pose monocular no tiene por qué ser\n"
        "uniforme a lo largo del recorrido articular.\n\n"
        "## 6. Figura de Bland-Altman\n\n"
        f"![Bland-Altman de datos sintéticos]({RUTA_FIGURA.name})\n\n"
        "La nube muestra el sesgo positivo constante, el abanico de dispersión que se abre\n"
        "hacia ángulos altos (heterocedasticidad) y los valores atípicos que sobrepasan el\n"
        "límite superior de acuerdo, concentrados en la zona de flexión profunda.\n\n"
        "## 7. Reproducción\n\n"
        "```bash\n"
        "cd \"<raiz del repositorio>\"\n"
        "python validacion/analisis/demostracion_sintetica.py\n"
        "```\n\n"
        "La semilla es fija, de modo que la ejecución reproduce exactamente estos números.\n",
    ]
    return "".join(partes)


def main() -> int:
    """Genera datos sintéticos, ejecuta el análisis y escribe informe y figura."""
    generador = np.random.default_rng(SEMILLA)
    referencia = generar_serie_referencia()
    estimado = generar_serie_estimada(referencia, generador)

    resumen = resumen_acuerdo(referencia, estimado)

    DIRECTORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    figura_bland_altman(
        referencia,
        estimado,
        RUTA_FIGURA,
        titulo="Bland-Altman (DATOS SINTETICOS DE DEMOSTRACION, no validacion real)",
    )
    RUTA_INFORME.write_text(construir_informe(referencia, estimado, resumen), encoding="utf-8")

    print("Demostracion con datos sinteticos completada.")
    print(f"  Pares analizados : {resumen['n']} (descartados: {resumen['n_pares_descartados']})")
    print(f"  MAE              : {resumen['mae']:.3f} grados")
    print(f"  RMSE             : {resumen['rmse']:.3f} grados")
    print(f"  Sesgo            : {resumen['sesgo']:+.3f} grados")
    print(
        f"  Limites acuerdo  : [{resumen['bland_altman']['limite_acuerdo_inferior']:+.3f}, "
        f"{resumen['bland_altman']['limite_acuerdo_superior']:+.3f}] grados"
    )
    print(
        f"  ICC(2,1)         : {resumen['icc']['icc']:.4f} "
        f"IC95 [{resumen['icc']['intervalo_confianza_95'][0]:.4f}, "
        f"{resumen['icc']['intervalo_confianza_95'][1]:.4f}] ({resumen['icc']['interpretacion']})"
    )
    print(f"  Pearson r        : {resumen['pearson']['r']:.4f} (p = {resumen['pearson']['p_valor']:.3e})")
    for fila in resumen["error_por_rango"]:
        print(
            f"  Tramo {fila['etiqueta']:>12} n={fila['n']:>3} "
            f"MAE={fila['mae']:.3f} RMSE={fila['rmse']:.3f} sesgo={fila['sesgo']:+.3f} "
            f"sd={fila['desviacion_estandar_diferencias']:.3f}"
            if fila["n"] > 0
            else f"  Tramo {fila['etiqueta']:>12} n=  0 (sin observaciones)"
        )
    print(f"  Informe          : {RUTA_INFORME}")
    print(f"  Figura           : {RUTA_FIGURA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
