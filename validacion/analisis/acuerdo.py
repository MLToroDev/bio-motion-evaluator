"""
Instrumento estadístico de acuerdo entre dos métodos de medición angular.

Este módulo implementa el análisis con el que se compara la estimación angular del
sistema Bio-Motion Evaluator (visión por computador, MediaPipe Pose en servidor)
contra un método de referencia (goniometría manual o video-goniometría con Kinovea).

Convenciones del módulo:

- Todos los ángulos se expresan en **grados**, rango esperado [0, 180].
- ``referencia`` es la serie del método de referencia (patrón de comparación) y
  ``estimado`` es la serie producida por el sistema bajo evaluación.
- La **diferencia** se define siempre como ``estimado - referencia``. Por tanto un
  sesgo positivo significa que el sistema **sobreestima** el ángulo respecto al
  método de referencia.
- Las funciones son puras: no leen ni escriben estado global, no mutan sus entradas
  y devuelven estructuras nuevas. La única función con efecto de disco es
  :func:`figura_bland_altman`, que escribe el archivo de imagen solicitado.
- Los pares en los que alguna de las dos series no es finita (NaN o infinito, p. ej.
  fotogramas sin detección de pose) se descartan antes de calcular. El número de
  pares efectivamente usados se reporta siempre en la clave ``n``.

Referencias metodológicas:

- Bland, J. M. y Altman, D. G. (1986). "Statistical methods for assessing agreement
  between two methods of clinical measurement". The Lancet, 327(8476), 307-310.
- Shrout, P. E. y Fleiss, J. L. (1979). "Intraclass correlations: uses in assessing
  rater reliability". Psychological Bulletin, 86(2), 420-428.
- McGraw, K. O. y Wong, S. P. (1996). "Forming inferences about some intraclass
  correlation coefficients". Psychological Methods, 1(1), 30-46. (Intervalos de
  confianza del ICC.)
- Koo, T. K. y Li, M. Y. (2016). "A guideline of selecting and reporting intraclass
  correlation coefficients for reliability research". Journal of Chiropractic
  Medicine, 15(2), 155-163. (Interpretación de los rangos del ICC.)
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

__all__ = [
    "BORDES_RANGO_POR_DEFECTO",
    "bland_altman",
    "coeficiente_correlacion_intraclase",
    "correlacion_pearson",
    "error_medio_absoluto",
    "error_por_rango",
    "figura_bland_altman",
    "formatear_resumen_markdown",
    "interpretar_icc",
    "raiz_error_cuadratico_medio",
    "resumen_acuerdo",
    "sesgo",
]

#: Tolerancia para considerar nula una varianza (evita divisiones 0/0).
_TOLERANCIA = 1e-12

#: Tramos angulares por defecto para el desglose de error (grados de flexión).
#: Separan extensión casi completa, flexión media y flexión profunda, que es donde
#: la estimación de pose monocular suele degradarse por autooclusión del miembro.
BORDES_RANGO_POR_DEFECTO: tuple[float, ...] = (0.0, 30.0, 60.0, 90.0, 120.0, 180.0)

#: Tipo de ICC implementado. Se declara como constante para dejar explícito que hoy
#: solo se soporta ICC(2,1) y que cualquier otro valor es un error de uso.
_TIPO_ICC_SOPORTADO = "dos_vias_acuerdo_absoluto"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _a_pares_validos(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Normaliza ambas series a vectores ``float64`` alineados y sin valores no finitos.

    Devuelve una copia; nunca modifica las entradas. Lanza ``ValueError`` si las
    series tienen distinta longitud, si están vacías o si no queda ningún par válido.
    """
    ref = np.asarray(referencia, dtype=np.float64).ravel()
    est = np.asarray(estimado, dtype=np.float64).ravel()

    if ref.size != est.size:
        raise ValueError(
            f"Las series deben tener la misma longitud (referencia={ref.size}, estimado={est.size})."
        )
    if ref.size == 0:
        raise ValueError("Las series están vacías; no hay nada que comparar.")

    finitos = np.isfinite(ref) & np.isfinite(est)
    ref_validos = ref[finitos]
    est_validos = est[finitos]
    if ref_validos.size == 0:
        raise ValueError("No queda ningún par válido tras descartar valores no finitos (NaN/inf).")
    return ref_validos, est_validos


def _diferencias(referencia: np.ndarray, estimado: np.ndarray) -> np.ndarray:
    """Diferencias ``estimado - referencia`` (positivo = el sistema sobreestima)."""
    return estimado - referencia


# ---------------------------------------------------------------------------
# Métricas de error punto a punto
# ---------------------------------------------------------------------------


def error_medio_absoluto(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
) -> float:
    """
    Error medio absoluto (MAE) en grados.

    MAE = media(|estimado - referencia|). Es la magnitud típica del error sin
    importar su dirección; se reporta en las mismas unidades que el ángulo.
    """
    ref, est = _a_pares_validos(referencia, estimado)
    return float(np.mean(np.abs(_diferencias(ref, est))))


def raiz_error_cuadratico_medio(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
) -> float:
    """
    Raíz del error cuadrático medio (RMSE) en grados.

    RMSE = sqrt(media((estimado - referencia)^2)). Penaliza más los errores grandes
    que el MAE, por lo que la distancia RMSE - MAE informa sobre la presencia de
    fotogramas atípicos (p. ej. pérdidas puntuales de seguimiento).
    """
    ref, est = _a_pares_validos(referencia, estimado)
    return float(np.sqrt(np.mean(np.square(_diferencias(ref, est)))))


def sesgo(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
) -> float:
    """
    Sesgo (error sistemático medio, con signo) en grados.

    sesgo = media(estimado - referencia). Positivo: el sistema sobreestima el
    ángulo de flexión; negativo: lo subestima.
    """
    ref, est = _a_pares_validos(referencia, estimado)
    return float(np.mean(_diferencias(ref, est)))


# ---------------------------------------------------------------------------
# Bland-Altman
# ---------------------------------------------------------------------------


def bland_altman(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
    *,
    nivel_confianza: float = 0.95,
) -> dict[str, Any]:
    """
    Análisis de Bland-Altman (1986) del acuerdo entre los dos métodos.

    Devuelve un diccionario con:

    - ``sesgo``: media de las diferencias (``estimado - referencia``).
    - ``desviacion_estandar_diferencias``: desviación estándar muestral (ddof=1) de
      las diferencias.
    - ``limite_acuerdo_inferior`` / ``limite_acuerdo_superior``: sesgo -/+ 1.96 * sd.
      Entre ambos límites cabe esperar el 95 % de las diferencias futuras si estas
      se distribuyen aproximadamente normal.
    - ``intervalo_confianza_95_del_sesgo``: IC del sesgo, ``sesgo -/+ t * sd/sqrt(n)``
      con t de Student de n-1 grados de libertad. Si el IC contiene 0, no hay
      evidencia de error sistemático.
    - ``intervalo_confianza_95_limite_inferior`` / ``..._limite_superior``: IC de cada
      límite de acuerdo (error estándar aproximado sqrt(3) * sd / sqrt(n), Bland y
      Altman 1986).
    - ``n``: número de pares válidos utilizados.

    ``nivel_confianza`` solo afecta a los intervalos de confianza; los límites de
    acuerdo se mantienen en la convención clásica de 1.96 desviaciones estándar.
    """
    if not 0.0 < nivel_confianza < 1.0:
        raise ValueError("nivel_confianza debe estar en (0, 1).")

    ref, est = _a_pares_validos(referencia, estimado)
    dif = _diferencias(ref, est)
    n = int(dif.size)
    if n < 2:
        raise ValueError("Se requieren al menos 2 pares válidos para el análisis de Bland-Altman.")

    media_dif = float(np.mean(dif))
    sd_dif = float(np.std(dif, ddof=1))
    limite_inferior = media_dif - 1.96 * sd_dif
    limite_superior = media_dif + 1.96 * sd_dif

    t_critico = float(stats.t.ppf(0.5 + nivel_confianza / 2.0, df=n - 1))
    error_estandar_sesgo = sd_dif / np.sqrt(n)
    # Error estándar aproximado de un límite de acuerdo (Bland y Altman 1986):
    # var(limite) ~ (1/n + 1.96^2 / (2*(n-1))) * sd^2, que se aproxima por 3*sd^2/n.
    error_estandar_limite = float(np.sqrt(3.0) * sd_dif / np.sqrt(n))

    return {
        "sesgo": media_dif,
        "desviacion_estandar_diferencias": sd_dif,
        "limite_acuerdo_inferior": float(limite_inferior),
        "limite_acuerdo_superior": float(limite_superior),
        "intervalo_confianza_95_del_sesgo": (
            float(media_dif - t_critico * error_estandar_sesgo),
            float(media_dif + t_critico * error_estandar_sesgo),
        ),
        "intervalo_confianza_95_limite_inferior": (
            float(limite_inferior - t_critico * error_estandar_limite),
            float(limite_inferior + t_critico * error_estandar_limite),
        ),
        "intervalo_confianza_95_limite_superior": (
            float(limite_superior - t_critico * error_estandar_limite),
            float(limite_superior + t_critico * error_estandar_limite),
        ),
        "n": n,
    }


# ---------------------------------------------------------------------------
# Coeficiente de correlación intraclase ICC(2,1)
# ---------------------------------------------------------------------------


def _cuadrados_medios(datos: np.ndarray) -> tuple[int, int, float, float, float]:
    """
    Cuadrados medios del ANOVA de dos vías sin réplica sobre una matriz n x k.

    Filas = sujetos (observaciones apareadas), columnas = métodos de medición.
    Devuelve ``(n, k, msr, msc, mse)``:

    - ``msr``: cuadrado medio entre sujetos (filas), gl = n-1.
    - ``msc``: cuadrado medio entre métodos (columnas), gl = k-1.
    - ``mse``: cuadrado medio residual, gl = (n-1)(k-1).
    """
    n, k = datos.shape
    media_general = float(datos.mean())
    medias_sujeto = datos.mean(axis=1)
    medias_metodo = datos.mean(axis=0)

    ss_sujetos = float(k * np.sum(np.square(medias_sujeto - media_general)))
    ss_metodos = float(n * np.sum(np.square(medias_metodo - media_general)))
    ss_total = float(np.sum(np.square(datos - media_general)))
    ss_residual = max(0.0, ss_total - ss_sujetos - ss_metodos)

    msr = ss_sujetos / (n - 1)
    msc = ss_metodos / (k - 1)
    mse = ss_residual / ((n - 1) * (k - 1))
    return n, k, msr, msc, mse


def interpretar_icc(valor_icc: float) -> str:
    """
    Interpretación cualitativa del ICC según Koo y Li (2016).

    < 0.50 pobre; 0.50-0.75 moderada; 0.75-0.90 buena; > 0.90 excelente.
    """
    if not np.isfinite(valor_icc):
        return "indeterminada"
    if valor_icc < 0.50:
        return "pobre"
    if valor_icc < 0.75:
        return "moderada"
    if valor_icc <= 0.90:
        return "buena"
    return "excelente"


def coeficiente_correlacion_intraclase(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
    tipo: str = _TIPO_ICC_SOPORTADO,
    *,
    nivel_confianza: float = 0.95,
) -> dict[str, Any]:
    """
    Coeficiente de correlación intraclase ICC(2,1) con intervalo de confianza al 95 %.

    Modelo de dos vías de efectos aleatorios, medida única, **acuerdo absoluto**
    (Shrout y Fleiss 1979, caso 2,1). Es el ICC adecuado para comparar dos métodos
    de medición distintos sobre los mismos objetos, porque penaliza tanto la falta
    de correlación como la diferencia sistemática de nivel entre métodos (a
    diferencia del ICC de consistencia, que ignora el sesgo constante).

    Fórmula (con k = 2 métodos y n observaciones apareadas)::

        ICC(2,1) = (MSR - MSE) / (MSR + (k-1)*MSE + k*(MSC - MSE)/n)

    donde MSR es el cuadrado medio entre sujetos, MSC el cuadrado medio entre
    métodos y MSE el cuadrado medio residual del ANOVA de dos vías sin réplica.

    El intervalo de confianza sigue McGraw y Wong (1996), tabla 7 (mismo desarrollo
    que implementan los paquetes ``irr`` de R y ``pingouin`` de Python).

    Advertencia sobre el intervalo con k = 2: la componente de varianza entre métodos
    se estima con un solo grado de libertad, por lo que el intervalo es ancho y no se
    estrecha indefinidamente al aumentar n (comprobado por simulación: con métodos
    fijos y desfase constante, la cobertura empírica del IC 95 % resulta conservadora,
    entre el 98 % y el 100 %, con anchura media que se estanca alrededor de 0.28 a
    partir de n = 200). Se debe reportar siempre junto al análisis de Bland-Altman,
    que sí describe la magnitud del error en las unidades del ángulo.

    Parámetros
    ----------
    tipo:
        Solo se admite ``"dos_vias_acuerdo_absoluto"`` (ICC(2,1)). Se mantiene el
        parámetro para que la llamada quede autoexplicativa en la memoria y para
        poder ampliar el módulo sin romper la firma.

    Devuelve un diccionario con ``icc``, ``intervalo_confianza_95``,
    ``interpretacion``, ``interpretacion_limite_inferior``, ``n``, ``k``, ``tipo``
    y los cuadrados medios usados (``cuadrado_medio_*``), útiles para auditar el
    cálculo en el anexo estadístico.
    """
    if tipo != _TIPO_ICC_SOPORTADO:
        raise ValueError(
            f"Tipo de ICC no soportado: {tipo!r}. Use {_TIPO_ICC_SOPORTADO!r} (ICC(2,1))."
        )
    if not 0.0 < nivel_confianza < 1.0:
        raise ValueError("nivel_confianza debe estar en (0, 1).")

    ref, est = _a_pares_validos(referencia, estimado)
    if ref.size < 2:
        raise ValueError("Se requieren al menos 2 pares válidos para calcular el ICC.")

    datos = np.column_stack((ref, est))
    n, k, msr, msc, mse = _cuadrados_medios(datos)

    alfa = 1.0 - nivel_confianza
    sin_variabilidad_entre_sujetos = msr <= _TOLERANCIA

    if sin_variabilidad_entre_sujetos:
        # Todas las observaciones comparten el mismo nivel: el ICC no está definido
        # (no hay varianza entre sujetos que explicar).
        icc = float("nan")
        limite_inferior = float("nan")
        limite_superior = float("nan")
    elif mse <= _TOLERANCIA and msc <= _TOLERANCIA:
        # Acuerdo perfecto: residual y efecto de método nulos.
        icc = 1.0
        limite_inferior = 1.0
        limite_superior = 1.0
    else:
        denominador = msr + (k - 1) * mse + k * (msc - mse) / n
        icc = float((msr - mse) / denominador) if abs(denominador) > _TOLERANCIA else float("nan")

        if not np.isfinite(icc) or mse <= _TOLERANCIA:
            limite_inferior = float("nan")
            limite_superior = float("nan")
        else:
            gl_sujetos = n - 1
            gl_residual = (n - 1) * (k - 1)
            razon_metodos = msc / mse
            numerador_v = gl_residual * (
                (k * icc * razon_metodos + n * (1 + (k - 1) * icc) - k * icc) ** 2
            )
            denominador_v = gl_sujetos * (k**2) * (icc**2) * (razon_metodos**2) + (
                n * (1 + (k - 1) * icc) - k * icc
            ) ** 2
            grados_libertad_v = numerador_v / denominador_v if denominador_v > _TOLERANCIA else float("nan")

            if not np.isfinite(grados_libertad_v) or grados_libertad_v <= 0:
                limite_inferior = float("nan")
                limite_superior = float("nan")
            else:
                f_superior = float(stats.f.ppf(1.0 - alfa / 2.0, gl_sujetos, grados_libertad_v))
                f_inferior = float(stats.f.ppf(1.0 - alfa / 2.0, grados_libertad_v, gl_sujetos))
                limite_inferior = float(
                    n * (msr - f_superior * mse)
                    / (f_superior * (k * msc + (k * n - k - n) * mse) + n * msr)
                )
                limite_superior = float(
                    n * (f_inferior * msr - mse)
                    / (k * msc + (k * n - k - n) * mse + n * f_inferior * msr)
                )

    return {
        "icc": float(icc),
        "intervalo_confianza_95": (float(limite_inferior), float(limite_superior)),
        "interpretacion": interpretar_icc(icc),
        "interpretacion_limite_inferior": interpretar_icc(limite_inferior),
        "n": int(n),
        "k": int(k),
        "tipo": tipo,
        "cuadrado_medio_entre_sujetos": float(msr),
        "cuadrado_medio_entre_metodos": float(msc),
        "cuadrado_medio_residual": float(mse),
    }


# ---------------------------------------------------------------------------
# Correlación de Pearson
# ---------------------------------------------------------------------------


def correlacion_pearson(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
) -> tuple[float, float]:
    """
    Coeficiente de correlación de Pearson y su p-valor bilateral (scipy).

    Advertencia metodológica: la correlación mide asociación lineal, no acuerdo.
    Dos métodos con un sesgo constante de 10 grados pueden correlacionar r = 1.0.
    Se reporta como complemento de Bland-Altman e ICC, nunca como sustituto.
    """
    ref, est = _a_pares_validos(referencia, estimado)
    if ref.size < 3:
        raise ValueError("Se requieren al menos 3 pares válidos para la correlación de Pearson.")
    resultado = stats.pearsonr(ref, est)
    return float(resultado[0]), float(resultado[1])


# ---------------------------------------------------------------------------
# Desglose de error por tramo angular
# ---------------------------------------------------------------------------


def error_por_rango(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
    bordes_rango: Sequence[float] = BORDES_RANGO_POR_DEFECTO,
) -> list[dict[str, Any]]:
    """
    Desglosa MAE, RMSE y sesgo por tramos del ángulo de **referencia**.

    El error de la estimación de pose monocular no es uniforme a lo largo del rango
    articular: cerca de la extensión los segmentos están bien visibles, mientras que
    en flexión profunda aparecen autooclusión y escorzo. Separar el error por tramos
    es, por tanto, un hallazgo con valor clínico y no un simple detalle de reporte.

    Los tramos se definen semiabiertos ``[borde_i, borde_i+1)``, salvo el último que
    es cerrado ``[borde_n-1, borde_n]`` para no perder el valor máximo. La asignación
    usa el valor de la serie de referencia, que es el patrón de comparación.

    Devuelve una lista de diccionarios (una fila por tramo) con las claves
    ``limite_inferior_deg``, ``limite_superior_deg``, ``etiqueta``, ``n``, ``mae``,
    ``rmse``, ``sesgo`` y ``desviacion_estandar_diferencias``. Los tramos sin
    observaciones devuelven ``n = 0`` y métricas ``nan``.

    Advertencia: una observación cuyo ángulo de referencia caiga **fuera** de
    ``[bordes[0], bordes[-1]]`` no pertenece a ningún tramo y no aparece en esta tabla,
    aunque sí cuenta en las métricas globales. Por eso :func:`resumen_acuerdo` expone la
    clave ``n_fuera_de_los_tramos``: si no es cero, la suma de los ``n`` por tramo no
    coincide con el ``n`` global y hay que revisar los bordes o los datos de referencia.
    """
    bordes = np.asarray(bordes_rango, dtype=np.float64).ravel()
    if bordes.size < 2:
        raise ValueError("bordes_rango debe contener al menos 2 valores.")
    if not np.all(np.diff(bordes) > 0):
        raise ValueError("bordes_rango debe ser estrictamente creciente.")

    ref, est = _a_pares_validos(referencia, estimado)
    dif = _diferencias(ref, est)

    filas: list[dict[str, Any]] = []
    for indice in range(bordes.size - 1):
        inferior = float(bordes[indice])
        superior = float(bordes[indice + 1])
        es_ultimo = indice == bordes.size - 2
        if es_ultimo:
            seleccion = (ref >= inferior) & (ref <= superior)
        else:
            seleccion = (ref >= inferior) & (ref < superior)

        dif_tramo = dif[seleccion]
        n_tramo = int(dif_tramo.size)
        if n_tramo == 0:
            mae = rmse = sesgo_tramo = sd_tramo = float("nan")
        else:
            mae = float(np.mean(np.abs(dif_tramo)))
            rmse = float(np.sqrt(np.mean(np.square(dif_tramo))))
            sesgo_tramo = float(np.mean(dif_tramo))
            sd_tramo = float(np.std(dif_tramo, ddof=1)) if n_tramo > 1 else float("nan")

        cierre = "]" if es_ultimo else ")"
        filas.append(
            {
                "limite_inferior_deg": inferior,
                "limite_superior_deg": superior,
                "etiqueta": f"[{inferior:.0f}, {superior:.0f}{cierre}",
                "n": n_tramo,
                "mae": mae,
                "rmse": rmse,
                "sesgo": sesgo_tramo,
                "desviacion_estandar_diferencias": sd_tramo,
            }
        )
    return filas


# ---------------------------------------------------------------------------
# Resumen integrado
# ---------------------------------------------------------------------------


def resumen_acuerdo(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
    *,
    bordes_rango: Sequence[float] = BORDES_RANGO_POR_DEFECTO,
) -> dict[str, Any]:
    """
    Ejecuta el análisis de acuerdo completo y devuelve todos los resultados juntos.

    Claves devueltas: ``n``, ``n_pares_descartados``, ``n_fuera_de_los_tramos``,
    ``rango_referencia_deg``,
    ``rango_estimado_deg``, ``mae``, ``rmse``, ``sesgo``, ``bland_altman``, ``icc``,
    ``pearson`` (con ``r`` y ``p_valor``) y ``error_por_rango``.

    Es la función que consumen los scripts de reporte; concentra el orden de
    llamada para que la memoria y los anexos usen exactamente el mismo cálculo.
    """
    ref_bruta = np.asarray(referencia, dtype=np.float64).ravel()
    ref, est = _a_pares_validos(referencia, estimado)
    n_descartados = int(ref_bruta.size - ref.size)

    r_pearson, p_pearson = correlacion_pearson(ref, est)

    tabla_rangos = error_por_rango(ref, est, bordes_rango)
    # Un valor de referencia fuera de [primer borde, ultimo borde] no cae en ningun
    # tramo y desapareceria del desglose sin dejar rastro, dejando la tabla por tramos
    # en desacuerdo con las metricas globales. Se contabiliza de forma explicita.
    n_fuera_de_los_tramos = int(ref.size) - int(sum(fila["n"] for fila in tabla_rangos))

    return {
        "n": int(ref.size),
        "n_pares_descartados": n_descartados,
        "n_fuera_de_los_tramos": n_fuera_de_los_tramos,
        "rango_referencia_deg": (float(np.min(ref)), float(np.max(ref))),
        "rango_estimado_deg": (float(np.min(est)), float(np.max(est))),
        "mae": error_medio_absoluto(ref, est),
        "rmse": raiz_error_cuadratico_medio(ref, est),
        "sesgo": sesgo(ref, est),
        "bland_altman": bland_altman(ref, est),
        "icc": coeficiente_correlacion_intraclase(ref, est),
        "pearson": {"r": r_pearson, "p_valor": p_pearson},
        "error_por_rango": tabla_rangos,
    }


def _formatear_p_valor(p_valor: float) -> str:
    """Formatea un p-valor evitando imprimir 0 cuando hay desbordamiento a la baja."""
    if not np.isfinite(p_valor):
        return "p indeterminado"
    if p_valor <= 0.0:
        return "p < 1e-300"
    if p_valor < 0.001:
        return f"p = {p_valor:.2e}"
    return f"p = {p_valor:.3f}"


def formatear_resumen_markdown(resumen: dict[str, Any], titulo: str = "Resumen de acuerdo") -> str:
    """
    Convierte la salida de :func:`resumen_acuerdo` en Markdown listo para el anexo.

    Función pura de presentación: no recalcula nada, solo formatea el diccionario.
    """
    ba = resumen["bland_altman"]
    icc = resumen["icc"]
    ic_sesgo = ba["intervalo_confianza_95_del_sesgo"]
    ic_icc = icc["intervalo_confianza_95"]

    lineas = [
        f"### {titulo}",
        "",
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| Pares analizados (n) | {resumen['n']} |",
        f"| Pares descartados (sin dato) | {resumen['n_pares_descartados']} |",
        *(
            [
                "| **Pares fuera de los tramos definidos** | "
                f"**{resumen['n_fuera_de_los_tramos']}** (revisar bordes_rango: el desglose "
                "por tramo no los incluye) |"
            ]
            if resumen.get("n_fuera_de_los_tramos", 0)
            else []
        ),
        f"| MAE (grados) | {resumen['mae']:.2f} |",
        f"| RMSE (grados) | {resumen['rmse']:.2f} |",
        f"| Sesgo (grados) | {resumen['sesgo']:+.2f} |",
        f"| IC 95 % del sesgo (grados) | [{ic_sesgo[0]:+.2f}, {ic_sesgo[1]:+.2f}] |",
        f"| Desviación estándar de las diferencias (grados) | {ba['desviacion_estandar_diferencias']:.2f} |",
        (
            "| Límites de acuerdo 95 % (grados) | "
            f"[{ba['limite_acuerdo_inferior']:+.2f}, {ba['limite_acuerdo_superior']:+.2f}] |"
        ),
        f"| ICC(2,1) | {icc['icc']:.3f} (IC 95 % [{ic_icc[0]:.3f}, {ic_icc[1]:.3f}]) |",
        f"| Interpretación ICC (Koo y Li 2016) | {icc['interpretacion']} |",
        f"| r de Pearson | {resumen['pearson']['r']:.3f} ({_formatear_p_valor(resumen['pearson']['p_valor'])}) |",
        "",
        "#### Error por tramo angular de referencia",
        "",
        "| Tramo (grados) | n | MAE | RMSE | Sesgo | Desv. tipica de las diferencias |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for fila in resumen["error_por_rango"]:
        if fila["n"] == 0:
            lineas.append(f"| {fila['etiqueta']} | 0 | - | - | - | - |")
        else:
            sd_tramo = fila["desviacion_estandar_diferencias"]
            sd_texto = f"{sd_tramo:.2f}" if sd_tramo == sd_tramo else "-"
            lineas.append(
                f"| {fila['etiqueta']} | {fila['n']} | {fila['mae']:.2f} | "
                f"{fila['rmse']:.2f} | {fila['sesgo']:+.2f} | {sd_texto} |"
            )
    lineas.append("")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Figura de Bland-Altman
# ---------------------------------------------------------------------------


def figura_bland_altman(
    referencia: Sequence[float] | np.ndarray,
    estimado: Sequence[float] | np.ndarray,
    ruta_salida: str | Path,
    *,
    titulo: str = "Bland-Altman: sistema frente a metodo de referencia",
    etiqueta_unidad: str = "grados",
    dpi: int = 150,
) -> Path:
    """
    Genera y guarda la figura de Bland-Altman (diferencias frente a medias).

    Dibuja el sesgo y los límites de acuerdo de 95 % (sesgo -/+ 1.96 sd) sobre la
    nube de puntos. Usa el backend Agg de forma explícita (``FigureCanvasAgg`` sobre
    un ``Figure`` propio) en lugar de ``pyplot``, de modo que no se toca ningún
    estado global de matplotlib y la función es segura en scripts y en pruebas.

    Devuelve la ruta del archivo escrito.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    ref, est = _a_pares_validos(referencia, estimado)
    resultado = bland_altman(ref, est)
    medias = (ref + est) / 2.0
    diferencias = _diferencias(ref, est)

    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    figura = Figure(figsize=(8.0, 5.0), dpi=dpi)
    FigureCanvasAgg(figura)
    ejes = figura.add_subplot(1, 1, 1)

    ejes.scatter(medias, diferencias, s=18, alpha=0.65, color="#1f77b4", edgecolors="none",
                 label="Diferencia por observacion")
    ejes.axhline(resultado["sesgo"], color="#d62728", linewidth=1.6,
                 label=f"Sesgo = {resultado['sesgo']:+.2f} {etiqueta_unidad}")
    ejes.axhline(resultado["limite_acuerdo_superior"], color="#7f7f7f", linestyle="--", linewidth=1.3,
                 label=f"LdA superior = {resultado['limite_acuerdo_superior']:+.2f}")
    ejes.axhline(resultado["limite_acuerdo_inferior"], color="#7f7f7f", linestyle="--", linewidth=1.3,
                 label=f"LdA inferior = {resultado['limite_acuerdo_inferior']:+.2f}")
    ejes.axhline(0.0, color="#000000", linewidth=0.8, alpha=0.35)

    ejes.set_xlabel(f"Media de ambos metodos ({etiqueta_unidad})")
    ejes.set_ylabel(f"Diferencia estimado - referencia ({etiqueta_unidad})")
    ejes.set_title(titulo)
    ejes.grid(True, alpha=0.25, linestyle=":")
    ejes.legend(loc="best", fontsize=8, framealpha=0.9)
    figura.tight_layout()
    figura.savefig(ruta)
    return ruta
