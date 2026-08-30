"""
Pruebas del instrumento estadístico de acuerdo (``validacion/analisis/acuerdo.py``).

Estrategia: en lugar de comprobar salidas "congeladas", cada prueba construye datos
sintéticos de **propiedades matemáticas conocidas** y verifica que el módulo las
recupera. Así la prueba valida la corrección del estadístico, no un número copiado.

Casos cubiertos:

- Acuerdo perfecto: MAE = RMSE = sesgo = 0 e ICC(2,1) = 1.
- Sesgo constante conocido: el sesgo y el MAE deben coincidir con el desplazamiento,
  y los límites de acuerdo deben colapsar sobre ese valor.
- Ruido gaussiano de sigma conocida: la desviación de las diferencias converge a sigma.
- Series sin relación: ICC(2,1) cercano a cero.
- ``error_por_rango``: reparto exacto de las n observaciones entre tramos.
- Comprobación cruzada del ICC contra su forma analítica cerrada para k = 2.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# El módulo bajo prueba vive fuera de ``backend/`` (pythonpath de pytest.ini), así que
# se añade la raíz del repositorio calculada desde este archivo, sin rutas absolutas fijas.
_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from validacion.analisis.acuerdo import (  # noqa: E402
    bland_altman,
    coeficiente_correlacion_intraclase,
    correlacion_pearson,
    error_medio_absoluto,
    error_por_rango,
    figura_bland_altman,
    formatear_resumen_markdown,
    raiz_error_cuadratico_medio,
    resumen_acuerdo,
    sesgo,
)

SEMILLA = 42


def _serie_sentadilla(n: int = 400) -> np.ndarray:
    """Serie angular sintética tipo sentadilla: 4 ciclos entre 5 y 125 grados."""
    t = np.linspace(0.0, 4.0 * 2.0 * math.pi, n)
    return 65.0 - 60.0 * np.cos(t)


# ---------------------------------------------------------------------------
# Acuerdo perfecto
# ---------------------------------------------------------------------------


def test_acuerdo_perfecto_todas_las_metricas_en_cero_y_icc_uno() -> None:
    referencia = _serie_sentadilla()
    estimado = referencia.copy()

    assert error_medio_absoluto(referencia, estimado) == pytest.approx(0.0, abs=1e-12)
    assert raiz_error_cuadratico_medio(referencia, estimado) == pytest.approx(0.0, abs=1e-12)
    assert sesgo(referencia, estimado) == pytest.approx(0.0, abs=1e-12)

    ba = bland_altman(referencia, estimado)
    assert ba["desviacion_estandar_diferencias"] == pytest.approx(0.0, abs=1e-12)
    assert ba["limite_acuerdo_inferior"] == pytest.approx(0.0, abs=1e-12)
    assert ba["limite_acuerdo_superior"] == pytest.approx(0.0, abs=1e-12)
    assert ba["n"] == referencia.size

    icc = coeficiente_correlacion_intraclase(referencia, estimado)
    assert icc["icc"] == pytest.approx(1.0, abs=1e-12)
    assert icc["intervalo_confianza_95"] == (1.0, 1.0)
    assert icc["interpretacion"] == "excelente"


# ---------------------------------------------------------------------------
# Sesgo constante conocido
# ---------------------------------------------------------------------------


def test_sesgo_constante_de_tres_grados_se_recupera_exactamente() -> None:
    desplazamiento = 3.0
    referencia = _serie_sentadilla()
    estimado = referencia + desplazamiento

    assert sesgo(referencia, estimado) == pytest.approx(desplazamiento, abs=1e-10)
    assert error_medio_absoluto(referencia, estimado) == pytest.approx(desplazamiento, abs=1e-10)
    assert raiz_error_cuadratico_medio(referencia, estimado) == pytest.approx(desplazamiento, abs=1e-10)

    ba = bland_altman(referencia, estimado)
    assert ba["desviacion_estandar_diferencias"] == pytest.approx(0.0, abs=1e-10)
    assert ba["limite_acuerdo_inferior"] == pytest.approx(desplazamiento, abs=1e-8)
    assert ba["limite_acuerdo_superior"] == pytest.approx(desplazamiento, abs=1e-8)
    inferior, superior = ba["intervalo_confianza_95_del_sesgo"]
    assert inferior == pytest.approx(desplazamiento, abs=1e-8)
    assert superior == pytest.approx(desplazamiento, abs=1e-8)


def test_sesgo_constante_no_lo_detecta_pearson_pero_si_el_icc() -> None:
    """Pearson mide asociación lineal; solo el ICC de acuerdo absoluto penaliza el sesgo."""
    referencia = _serie_sentadilla()
    estimado = referencia + 10.0

    r, _p = correlacion_pearson(referencia, estimado)
    assert r == pytest.approx(1.0, abs=1e-10)

    icc = coeficiente_correlacion_intraclase(referencia, estimado)
    assert icc["icc"] < 0.99


# ---------------------------------------------------------------------------
# Ruido gaussiano de sigma conocida
# ---------------------------------------------------------------------------


def test_ruido_gaussiano_recupera_la_sigma_conocida() -> None:
    sigma = 2.5
    n = 4000
    generador = np.random.default_rng(SEMILLA)
    referencia = generador.uniform(0.0, 140.0, size=n)
    estimado = referencia + generador.normal(loc=0.0, scale=sigma, size=n)

    ba = bland_altman(referencia, estimado)
    assert ba["desviacion_estandar_diferencias"] == pytest.approx(sigma, abs=0.15)
    assert ba["sesgo"] == pytest.approx(0.0, abs=0.15)
    # Para ruido normal centrado: MAE esperado = sigma * sqrt(2/pi); RMSE esperado = sigma.
    assert error_medio_absoluto(referencia, estimado) == pytest.approx(sigma * math.sqrt(2.0 / math.pi), abs=0.15)
    assert raiz_error_cuadratico_medio(referencia, estimado) == pytest.approx(sigma, abs=0.15)
    assert ba["limite_acuerdo_superior"] == pytest.approx(1.96 * sigma, abs=0.35)
    assert ba["limite_acuerdo_inferior"] == pytest.approx(-1.96 * sigma, abs=0.35)
    # El IC del sesgo debe contener el cero (no hay error sistemático simulado).
    inferior, superior = ba["intervalo_confianza_95_del_sesgo"]
    assert inferior < 0.0 < superior


def test_ruido_pequeno_frente_al_rango_da_icc_excelente() -> None:
    generador = np.random.default_rng(SEMILLA)
    referencia = generador.uniform(0.0, 140.0, size=600)
    estimado = referencia + generador.normal(0.0, 2.5, size=600)

    icc = coeficiente_correlacion_intraclase(referencia, estimado)
    assert icc["icc"] > 0.95
    limite_inferior, limite_superior = icc["intervalo_confianza_95"]
    assert limite_inferior <= icc["icc"] <= limite_superior
    assert icc["interpretacion"] == "excelente"


# ---------------------------------------------------------------------------
# Series sin relación
# ---------------------------------------------------------------------------


def test_icc_bajo_cuando_las_series_no_guardan_relacion() -> None:
    generador = np.random.default_rng(SEMILLA)
    referencia = generador.uniform(0.0, 140.0, size=500)
    estimado = generador.uniform(0.0, 140.0, size=500)

    icc = coeficiente_correlacion_intraclase(referencia, estimado)
    assert icc["icc"] < 0.25
    assert icc["interpretacion"] == "pobre"

    r, p_valor = correlacion_pearson(referencia, estimado)
    assert abs(r) < 0.2
    assert p_valor > 0.01


def test_icc_indeterminado_si_no_hay_variabilidad_entre_observaciones() -> None:
    """Sin varianza entre sujetos el ICC no está definido; debe devolver NaN sin romper."""
    constante = np.full(50, 90.0)
    icc = coeficiente_correlacion_intraclase(constante, constante)
    assert math.isnan(icc["icc"])
    assert icc["interpretacion"] == "indeterminada"


# ---------------------------------------------------------------------------
# Verificación cruzada del ICC(2,1) con su forma analítica para k = 2
# ---------------------------------------------------------------------------


def _icc21_forma_analitica(referencia: np.ndarray, estimado: np.ndarray) -> float:
    """
    ICC(2,1) calculado por una vía independiente, válida solo para k = 2 métodos.

    Con m_i = (x_i + y_i)/2 y d_i = y_i - x_i se demuestra que el ANOVA de dos vías
    cumple: MSR = 2*Var(m), MSC = n*media(d)^2/2 y MSE = Var(d)/2 (varianzas con
    ddof = 1). Sustituyendo en la fórmula de Shrout y Fleiss (1979) se obtiene el
    ICC sin pasar por la descomposición de sumas de cuadrados del módulo, lo que
    convierte esta prueba en una verificación cruzada real de la implementación.
    """
    n = referencia.size
    medias = (referencia + estimado) / 2.0
    diferencias = estimado - referencia
    msr = 2.0 * float(np.var(medias, ddof=1))
    msc = n * float(np.mean(diferencias)) ** 2 / 2.0
    mse = float(np.var(diferencias, ddof=1)) / 2.0
    k = 2
    return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)


def test_icc_coincide_con_su_forma_analitica_cerrada() -> None:
    generador = np.random.default_rng(SEMILLA)
    referencia = _serie_sentadilla(300)
    estimado = referencia + 1.8 + generador.normal(0.0, 4.0, size=referencia.size)

    resultado = coeficiente_correlacion_intraclase(referencia, estimado)
    esperado = _icc21_forma_analitica(referencia, estimado)
    assert resultado["icc"] == pytest.approx(esperado, rel=1e-10)

    # Los cuadrados medios expuestos también deben coincidir con la vía analítica.
    assert resultado["cuadrado_medio_entre_sujetos"] == pytest.approx(
        2.0 * float(np.var((referencia + estimado) / 2.0, ddof=1)), rel=1e-10
    )
    assert resultado["cuadrado_medio_residual"] == pytest.approx(
        float(np.var(estimado - referencia, ddof=1)) / 2.0, rel=1e-10
    )


def test_icc_converge_al_valor_poblacional_de_un_modelo_conocido() -> None:
    """
    Con datos generados por un modelo de componentes de varianza conocido, el ICC(2,1)
    estimado debe converger al valor poblacional sigma_s^2 / (sigma_s^2 + sigma_m^2 + sigma_e^2).

    Es la verificación más exigente del estadístico: no compara contra otra fórmula,
    sino contra el parámetro que generó los datos.
    """
    generador = np.random.default_rng(SEMILLA)
    n = 50000
    varianza_sujeto, varianza_error, desfase_entre_metodos = 100.0, 9.0, 3.0
    varianza_metodo = 2.0 * (desfase_entre_metodos / 2.0) ** 2

    sujeto = generador.normal(0.0, math.sqrt(varianza_sujeto), size=n)
    referencia = sujeto - desfase_entre_metodos / 2.0 + generador.normal(0.0, math.sqrt(varianza_error), size=n)
    estimado = sujeto + desfase_entre_metodos / 2.0 + generador.normal(0.0, math.sqrt(varianza_error), size=n)

    poblacional = varianza_sujeto / (varianza_sujeto + varianza_metodo + varianza_error)
    resultado = coeficiente_correlacion_intraclase(referencia, estimado)
    assert resultado["icc"] == pytest.approx(poblacional, abs=0.005)
    limite_inferior, limite_superior = resultado["intervalo_confianza_95"]
    assert limite_inferior <= poblacional <= limite_superior


def test_icc_rechaza_un_tipo_no_soportado() -> None:
    referencia = _serie_sentadilla(50)
    with pytest.raises(ValueError):
        coeficiente_correlacion_intraclase(referencia, referencia, tipo="consistencia")


# ---------------------------------------------------------------------------
# Error por rango
# ---------------------------------------------------------------------------


def test_error_por_rango_reparte_todas_las_observaciones() -> None:
    bordes = [0.0, 30.0, 60.0, 90.0, 120.0, 180.0]
    referencia = np.array(
        [1.0, 5.0, 10.0, 20.0, 29.9]  # 5 en [0, 30)
        + [30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 59.0, 59.5, 31.0, 33.0]  # 10 en [30, 60)
        + [60.0, 75.0, 89.9]  # 3 en [60, 90)
        + [120.0, 150.0, 179.0, 180.0, 130.0, 140.0, 145.0]  # 7 en [120, 180]
    )
    estimado = referencia + 2.0
    tabla = error_por_rango(referencia, estimado, bordes)

    assert [fila["n"] for fila in tabla] == [5, 10, 3, 0, 7]
    assert sum(fila["n"] for fila in tabla) == referencia.size
    assert len(tabla) == len(bordes) - 1

    # El tramo vacío no debe romper el cálculo: n = 0 y métricas NaN.
    tramo_vacio = tabla[3]
    assert tramo_vacio["n"] == 0
    assert math.isnan(tramo_vacio["mae"])

    # En los tramos poblados, con desplazamiento constante, MAE = RMSE = 2 grados.
    for fila in tabla:
        if fila["n"] > 0:
            assert fila["mae"] == pytest.approx(2.0, abs=1e-9)
            assert fila["rmse"] == pytest.approx(2.0, abs=1e-9)
            assert fila["sesgo"] == pytest.approx(2.0, abs=1e-9)


def test_error_por_rango_detecta_error_creciente_con_la_flexion() -> None:
    """El desglose debe evidenciar heterocedasticidad: más error en flexión profunda."""
    generador = np.random.default_rng(SEMILLA)
    referencia = generador.uniform(0.0, 180.0, size=3000)
    # Error que crece linealmente con el ángulo (simula autooclusión en flexión).
    escala = 1.0 + referencia / 60.0
    estimado = referencia + generador.normal(0.0, 1.0, size=referencia.size) * escala

    tabla = error_por_rango(referencia, estimado, [0.0, 60.0, 120.0, 180.0])
    maes = [fila["mae"] for fila in tabla]
    assert maes[0] < maes[1] < maes[2]


def test_resumen_contabiliza_las_observaciones_fuera_de_los_tramos() -> None:
    """Un valor de referencia fuera de los bordes no debe desaparecer en silencio."""
    referencia = [-3.0, 10.0, 50.0, 95.0, 130.0, 181.5]
    estimado = [1.0, 12.0, 53.0, 92.0, 133.0, 178.0]

    resumen = resumen_acuerdo(referencia, estimado)
    suma_tramos = sum(fila["n"] for fila in resumen["error_por_rango"])
    assert resumen["n"] == 6
    assert suma_tramos == 4
    assert resumen["n_fuera_de_los_tramos"] == 2

    # La discrepancia tiene que ser visible en el informe, no solo en el diccionario.
    markdown = formatear_resumen_markdown(resumen, titulo="Prueba")
    assert "fuera de los tramos" in markdown


def test_resumen_sin_valores_fuera_de_rango_no_ensucia_el_informe() -> None:
    referencia = _serie_sentadilla(120)
    estimado = referencia + 1.5

    resumen = resumen_acuerdo(referencia, estimado)
    assert resumen["n_fuera_de_los_tramos"] == 0
    assert sum(fila["n"] for fila in resumen["error_por_rango"]) == resumen["n"]
    assert "fuera de los tramos" not in formatear_resumen_markdown(resumen)


def test_error_por_rango_valida_los_bordes() -> None:
    referencia = _serie_sentadilla(20)
    with pytest.raises(ValueError):
        error_por_rango(referencia, referencia, [0.0])
    with pytest.raises(ValueError):
        error_por_rango(referencia, referencia, [0.0, 60.0, 30.0])


# ---------------------------------------------------------------------------
# Validación de entradas y manejo de datos faltantes
# ---------------------------------------------------------------------------


def test_longitudes_distintas_lanzan_error() -> None:
    with pytest.raises(ValueError):
        error_medio_absoluto([1.0, 2.0, 3.0], [1.0, 2.0])


def test_series_vacias_lanzan_error() -> None:
    with pytest.raises(ValueError):
        error_medio_absoluto([], [])


def test_los_pares_no_finitos_se_descartan_y_se_contabilizan() -> None:
    referencia = [10.0, 20.0, 30.0, 40.0, 50.0]
    estimado = [11.0, float("nan"), 31.0, 41.0, 51.0]

    assert error_medio_absoluto(referencia, estimado) == pytest.approx(1.0)
    resumen = resumen_acuerdo(referencia, estimado, bordes_rango=[0.0, 30.0, 60.0])
    assert resumen["n"] == 4
    assert resumen["n_pares_descartados"] == 1
    assert sum(fila["n"] for fila in resumen["error_por_rango"]) == 4


# ---------------------------------------------------------------------------
# Resumen integrado y figura
# ---------------------------------------------------------------------------


def test_resumen_acuerdo_expone_todas_las_secciones() -> None:
    generador = np.random.default_rng(SEMILLA)
    referencia = _serie_sentadilla(200)
    estimado = referencia + 2.0 + generador.normal(0.0, 3.0, size=referencia.size)

    resumen = resumen_acuerdo(referencia, estimado)
    for clave in ("n", "mae", "rmse", "sesgo", "bland_altman", "icc", "pearson", "error_por_rango"):
        assert clave in resumen
    assert resumen["n"] == 200
    assert resumen["sesgo"] == pytest.approx(sesgo(referencia, estimado))
    assert resumen["bland_altman"]["n"] == 200
    assert resumen["pearson"]["r"] > 0.9

    markdown = formatear_resumen_markdown(resumen, titulo="Prueba")
    assert "MAE (grados)" in markdown
    assert "ICC(2,1)" in markdown


def test_figura_bland_altman_se_escribe_en_disco(tmp_path: Path) -> None:
    generador = np.random.default_rng(SEMILLA)
    referencia = _serie_sentadilla(150)
    estimado = referencia + generador.normal(1.0, 3.0, size=referencia.size)

    destino = tmp_path / "subcarpeta" / "bland_altman.png"
    ruta = figura_bland_altman(referencia, estimado, destino)

    assert ruta == destino
    assert destino.exists()
    assert destino.stat().st_size > 5000
