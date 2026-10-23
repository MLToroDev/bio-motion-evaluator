"""
Pruebas del flujo del Nivel 2 con Tracker (exportación, sorteo de la sesión 2 y análisis).

Todos los datos son **sintéticos** y se construyen dentro de ``tmp_path``: ninguna
prueba lee ni escribe en ``validacion/datos/``. Igual que ``test_acuerdo.py``, cada caso
fabrica datos de propiedades conocidas y comprueba que el código las recupera o que
falla de forma explícita.

Casos cubiertos:

- Convención de Tracker: ``abs()``, conversión interno -> flexión, rechazo de valores
  fuera de [0, 180] y de series en radianes.
- Validación y unión: claves duplicadas, sesión incoherente, filas sin fotograma en el
  sistema, filas de la sesión 2 ajenas a la sesión 1, descartes reportados.
- Criterio habilitante intra-observador: veredicto, orden del informe y remedio (a).
- Sorteo de la sesión 2: tamaño ``ceil(33 %)``, determinismo con semilla, independencia
  del orden de entrada, copia de PNG y protección contra un segundo sorteo.
- ``formatear_resumen_markdown(n_minimo_tramo=...)`` y rótulo de los PNG exportados.
"""

from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from validacion.analisis.acuerdo import formatear_resumen_markdown, resumen_acuerdo  # noqa: E402
from validacion.analisis.analizar_nivel2 import (  # noqa: E402
    ErrorDatosNivel2,
    analizar,
    cargar_sesion,
    cargar_sistema,
    comprobar_unidades_en_grados,
    convertir_a_flexion,
    escribir_resultados,
    evaluar_intraobservador,
)
from validacion.analisis.plantilla_tracker import (  # noqa: E402
    COLUMNAS_PLANTILLA_TRACKER,
    escribir_plantilla,
    leer_plantilla,
    nombre_fotograma_sesion1,
    nombre_fotograma_sesion2,
)
from validacion.analisis.sortear_sesion2 import (  # noqa: E402
    ejecutar_sorteo,
    sortear_submuestra,
    tamano_submuestra,
)

SEMILLA = 42
VIDEO = "clip_sintetico.mp4"
COLUMNAS_SISTEMA = (
    "frame_index",
    "timestamp_ms",
    "timestamp_s",
    "pose_ok",
    "left_knee_flexion_angle_deg",
    "right_knee_flexion_angle_deg",
    "left_knee_internal_angle_deg",
    "right_knee_internal_angle_deg",
    "asimetria_bilateral_deg",
    "angulo_manual_kinovea_deg",
    "lado_medido_kinovea",
    "observaciones",
)


# ---------------------------------------------------------------------------
# Generadores de datos sintéticos
# ---------------------------------------------------------------------------


def _flexion_sintetica(n: int) -> np.ndarray:
    """Flexión tipo sentadilla lenta: dos ciclos entre 5 y 125 grados."""
    t = np.linspace(0.0, 2.0 * 2.0 * math.pi, n)
    return 65.0 - 60.0 * np.cos(t)


def _escribir_sistema(ruta: Path, indices: list[int], flexion_derecha: list[float | None]) -> Path:
    with ruta.open("w", encoding="utf-8", newline="") as manejador:
        escritor = csv.DictWriter(manejador, fieldnames=list(COLUMNAS_SISTEMA), restval="", lineterminator="\n")
        escritor.writeheader()
        for indice, flexion in zip(indices, flexion_derecha, strict=True):
            escritor.writerow(
                {
                    "frame_index": indice,
                    "pose_ok": "0" if flexion is None else "1",
                    "left_knee_flexion_angle_deg": "" if flexion is None else f"{flexion + 3.0:.3f}",
                    "right_knee_flexion_angle_deg": "" if flexion is None else f"{flexion:.3f}",
                }
            )
    return ruta


def _filas_tracker(
    indices: list[int],
    valores_internos: list[float | None],
    *,
    sesion: int,
    fecha: str,
    lado: str = "derecha",
) -> list[dict[str, object]]:
    return [
        {
            "video": VIDEO,
            "ordinal_muestra": ordinal,
            "frame_idx": indice,
            "lado": lado,
            "sesion": sesion,
            "fecha_medicion": fecha if valor is not None else "",
            "tracker_angulo_deg": "" if valor is None else f"{valor:.2f}",
            "confianza_operador": "1" if ordinal % 2 == 0 else "2",
            "observaciones": "" if valor is not None else "oclusion",
            "archivo_png": nombre_fotograma_sesion1(ordinal),
        }
        for ordinal, (indice, valor) in enumerate(zip(indices, valores_internos, strict=True))
    ]


def _escenario(
    tmp_path: Path,
    *,
    ruido_intra: float,
    ruido_sistema: float = 2.0,
    n: int = 30,
) -> tuple[Path, Path, Path]:
    """
    Sistema + sesiones 1 y 2 sintéticas.

    La sesión 1 mide el ángulo interno ``180 - flexion`` con ruido de 1 grado; la
    sesión 2 repite un tercio de los fotogramas con ruido ``ruido_intra``. Hay un
    fotograma sin pose en el sistema y uno sin valor en la sesión 1 (ambos deben
    descartarse y reportarse, no hacer fallar el análisis).
    """
    generador = np.random.default_rng(SEMILLA)
    indices = [10 * i for i in range(n)]
    verdad = _flexion_sintetica(n)
    sistema = list(verdad + generador.normal(0.0, ruido_sistema, n))
    sistema_con_hueco: list[float | None] = [float(v) for v in sistema]
    sistema_con_hueco[3] = None
    ruta_sistema = _escribir_sistema(tmp_path / "serie_sistema.csv", indices, sistema_con_hueco)

    interno_s1: list[float | None] = [float(v) for v in 180.0 - (verdad + generador.normal(0.0, 1.0, n))]
    interno_s1[5] = None
    ruta_s1 = escribir_plantilla(
        _filas_tracker(indices, interno_s1, sesion=1, fecha="2026-10-01T10:00:00"), tmp_path / "s1.csv"
    )

    elegidos = sorted(random.Random(SEMILLA).sample(range(n), math.ceil(n / 3)))
    filas_s2 = []
    for posicion, i in enumerate(elegidos):
        base = interno_s1[i]
        valor = None if base is None else base + float(generador.normal(0.0, ruido_intra))
        fila = _filas_tracker([indices[i]], [valor], sesion=2, fecha="2026-10-04T10:00:00")[0]
        fila["ordinal_muestra"] = i
        fila["archivo_png"] = nombre_fotograma_sesion2(posicion)
        filas_s2.append(fila)
    ruta_s2 = escribir_plantilla(filas_s2, tmp_path / "s2.csv")
    return ruta_sistema, ruta_s1, ruta_s2


# ---------------------------------------------------------------------------
# Convención de Tracker y rango
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bruto", "convencion", "esperado"),
    [
        (180.0, "interno", 0.0),
        (90.0, "interno", 90.0),
        (-150.0, "interno", 30.0),  # ángulo con signo: se toma el valor absoluto
        (0.0, "interno", 180.0),
        (45.0, "flexion", 45.0),
        (-45.0, "flexion", 45.0),
        (180.0, "flexion", 180.0),
    ],
)
def test_convertir_a_flexion_aplica_valor_absoluto_y_convencion(bruto: float, convencion: str, esperado: float) -> None:
    assert convertir_a_flexion(bruto, convencion) == pytest.approx(esperado)


@pytest.mark.parametrize("bruto", [180.01, -181.0, 270.0, float("nan"), float("inf")])
def test_convertir_a_flexion_rechaza_valores_fuera_de_rango(bruto: float) -> None:
    with pytest.raises(ErrorDatosNivel2):
        convertir_a_flexion(bruto, "interno")


def test_convertir_a_flexion_rechaza_convencion_desconocida() -> None:
    with pytest.raises(ValueError, match="Convención"):
        convertir_a_flexion(90.0, "reflejo")


def test_serie_en_radianes_se_rechaza() -> None:
    with pytest.raises(ErrorDatosNivel2, match="radianes"):
        comprobar_unidades_en_grados([3.10, 2.2, 1.6, 2.9])
    comprobar_unidades_en_grados([175.0, 120.0, 95.0])  # en grados: no falla


def test_plantilla_en_radianes_hace_fallar_la_carga(tmp_path: Path) -> None:
    ruta = escribir_plantilla(
        _filas_tracker([0, 10, 20], [3.1, 2.0, 1.7], sesion=1, fecha="2026-10-01"), tmp_path / "s1.csv"
    )
    with pytest.raises(ErrorDatosNivel2, match="radianes"):
        cargar_sesion(ruta, convencion="interno", sesion_esperada=1)


# ---------------------------------------------------------------------------
# Validación de plantillas y unión con el sistema
# ---------------------------------------------------------------------------


def test_fila_vacia_queda_sin_valor_y_coma_decimal_se_acepta(tmp_path: Path) -> None:
    filas = _filas_tracker([0, 10, 20], [170.0, None, 100.0], sesion=1, fecha="2026-10-01")
    filas[2]["tracker_angulo_deg"] = "100,5"
    ruta = escribir_plantilla(filas, tmp_path / "s1.csv")
    mediciones = cargar_sesion(ruta, convencion="interno", sesion_esperada=1)
    assert mediciones[(VIDEO, 10, "derecha")].flexion_deg is None
    assert mediciones[(VIDEO, 20, "derecha")].flexion_deg == pytest.approx(79.5)


def test_clave_duplicada_falla(tmp_path: Path) -> None:
    filas = _filas_tracker([0, 10, 10], [170.0, 150.0, 151.0], sesion=1, fecha="2026-10-01")
    ruta = escribir_plantilla(filas, tmp_path / "s1.csv")
    with pytest.raises(ErrorDatosNivel2, match="duplicada"):
        cargar_sesion(ruta, convencion="interno", sesion_esperada=1)


def test_numero_de_sesion_incoherente_falla(tmp_path: Path) -> None:
    ruta = escribir_plantilla(_filas_tracker([0, 10, 20], [170.0, 150.0, 120.0], sesion=1, fecha=""), tmp_path / "s.csv")
    with pytest.raises(ErrorDatosNivel2, match="sesion = 2"):
        cargar_sesion(ruta, convencion="interno", sesion_esperada=2)


def test_lado_invalido_falla(tmp_path: Path) -> None:
    filas = _filas_tracker([0, 10, 20], [170.0, 150.0, 120.0], sesion=1, fecha="", lado="izq")
    ruta = escribir_plantilla(filas, tmp_path / "s1.csv")
    with pytest.raises(ErrorDatosNivel2, match="Lado"):
        cargar_sesion(ruta, convencion="interno", sesion_esperada=1)


def test_csv_del_sistema_con_indice_duplicado_falla(tmp_path: Path) -> None:
    ruta = _escribir_sistema(tmp_path / "sis.csv", [0, 10, 10], [5.0, 20.0, 21.0])
    with pytest.raises(ErrorDatosNivel2, match="duplicado"):
        cargar_sistema(ruta)


def test_fila_de_tracker_sin_fotograma_en_el_sistema_falla(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=1.0)
    filas = leer_plantilla(ruta_s1)
    filas[-1]["frame_idx"] = "99999"
    escribir_plantilla(filas, ruta_s1)
    with pytest.raises(ErrorDatosNivel2, match="sin correspondencia"):
        analizar(ruta_sistema, ruta_s1, ruta_s2)


def test_video_distinto_al_del_sistema_falla(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=1.0)
    with pytest.raises(ErrorDatosNivel2, match="sin correspondencia"):
        analizar(ruta_sistema, ruta_s1, ruta_s2, video="otro_clip.mp4")


def test_fila_de_la_sesion2_ajena_a_la_sesion1_falla(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=1.0)
    filas = leer_plantilla(ruta_s1)
    escribir_plantilla(filas[1:], ruta_s1)  # se quita de la sesión 1 el fotograma 0...
    filas_s2 = leer_plantilla(ruta_s2)
    filas_s2[0]["frame_idx"] = "0"  # ...y se fuerza en la sesión 2
    escribir_plantilla(filas_s2, ruta_s2)
    with pytest.raises(ErrorDatosNivel2, match="no existen en la sesión 1"):
        analizar(ruta_sistema, ruta_s1, ruta_s2)


# ---------------------------------------------------------------------------
# Criterio habilitante y análisis completo
# ---------------------------------------------------------------------------


def test_intraobservador_con_ruido_pequeno_cumple_y_el_nivel_es_concluyente(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=0.8)
    resultado = analizar(ruta_sistema, ruta_s1, ruta_s2)

    intra = resultado["intraobservador"]
    assert intra["cumple"] is True
    assert intra["mae"] <= 3.0
    assert resultado["veredicto"].startswith("concluyente")
    # Los descartes se reportan, no se ocultan: el fotograma 50 no tiene valor de Tracker
    # y el 30 no tiene estimación del sistema.
    descartes = {d["frame_idx"]: d["motivo"] for d in resultado["sistema_vs_tracker"]["descartados"]}
    assert "Tracker" in descartes[50]
    assert "sistema" in descartes[30]
    assert resultado["sistema_vs_tracker"]["resumen"]["n"] == 28
    assert resultado["parametros"]["origen_nombre_video"] == "único vídeo de la sesión 1"


def test_intraobservador_con_ruido_grande_no_cumple_y_el_nivel_no_es_concluyente(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=8.0)
    resultado = analizar(ruta_sistema, ruta_s1, ruta_s2)
    assert resultado["intraobservador"]["cumple"] is False
    assert resultado["veredicto"].startswith("no concluyente")
    # La parte 2 se calcula igualmente.
    assert resultado["sistema_vs_tracker"]["resumen"]["n"] > 0


def test_criterio_habilitante_exacto_en_el_umbral(tmp_path: Path) -> None:
    """Diferencias de exactamente 3 grados cumplen (<=); 3,01 grados no."""
    indices = [0, 10, 20, 30]
    s1 = escribir_plantilla(_filas_tracker(indices, [170.0, 140.0, 100.0, 60.0], sesion=1, fecha=""), tmp_path / "a.csv")
    for desfase, esperado in ((3.0, True), (3.01, False)):
        s2 = escribir_plantilla(
            _filas_tracker(indices, [170.0 + desfase, 140.0 - desfase, 100.0 + desfase, 60.0 - desfase], sesion=2, fecha=""),
            tmp_path / f"b_{desfase}.csv",
        )
        intra = evaluar_intraobservador(
            cargar_sesion(s1, convencion="interno", sesion_esperada=1),
            cargar_sesion(s2, convencion="interno", sesion_esperada=2),
        )
        assert intra["mae"] == pytest.approx(desfase)
        assert intra["cumple"] is esperado


def test_remedio_mediana_etiqueta_el_veredicto_como_condicionado(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=8.0)
    extras = []
    for numero in (3, 4):
        filas = leer_plantilla(ruta_s1)
        for fila in filas:
            fila["sesion"] = str(numero)
        extras.append(escribir_plantilla(filas, tmp_path / f"s{numero}.csv"))
    resultado = analizar(ruta_sistema, ruta_s1, ruta_s2, rutas_extra=extras)
    assert resultado["parametros"]["remedio_mediana_aplicado"] is True
    assert resultado["veredicto"].startswith("condicionado al remedio (a)")
    assert all(p["n_mediciones_referencia"] == 3 for p in resultado["sistema_vs_tracker"]["pares"])


def test_sesion_extra_con_numero_1_o_2_falla(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=1.0)
    with pytest.raises(ErrorDatosNivel2, match="3 o más"):
        analizar(ruta_sistema, ruta_s1, ruta_s2, rutas_extra=[ruta_s1])


def test_informe_presenta_el_intraobservador_antes_que_el_sistema(tmp_path: Path) -> None:
    ruta_sistema, ruta_s1, ruta_s2 = _escenario(tmp_path, ruido_intra=0.8)
    resultado = analizar(ruta_sistema, ruta_s1, ruta_s2)
    rutas = escribir_resultados(resultado, tmp_path / "resultados")

    for ruta in rutas.values():
        assert ruta.is_file() and ruta.stat().st_size > 0
    informe = rutas["informe"].read_text(encoding="utf-8")
    posicion_intra = informe.index("## 1. Criterio habilitante")
    posicion_sistema = informe.index("## 2. Acuerdo sistema frente a Tracker")
    assert posicion_intra < posicion_sistema
    assert "CUMPLE" in informe[posicion_intra:posicion_sistema]
    assert "MAE sistema vs. Tracker" in informe
    assert "ICC(2,1)" in informe


# ---------------------------------------------------------------------------
# Sorteo de la sesión 2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("n", "esperado"), [(73, 25), (300, 99), (100, 33), (3, 1), (1, 1), (0, 0)])
def test_tamano_submuestra_es_el_techo_del_33_por_ciento(n: int, esperado: int) -> None:
    assert tamano_submuestra(n, 0.33) == esperado


def _filas_sesion1_vacias(n: int) -> list[dict[str, str]]:
    return [
        {
            "video": VIDEO,
            "ordinal_muestra": str(i),
            "frame_idx": str(10 * i),
            "lado": "derecha",
            "archivo_png": nombre_fotograma_sesion1(i),
        }
        for i in range(n)
    ]


def test_sorteo_es_determinista_e_independiente_del_orden_de_entrada() -> None:
    filas = _filas_sesion1_vacias(73)
    primero = sortear_submuestra(filas, semilla=7)
    barajadas = filas[:]
    random.Random(1).shuffle(barajadas)
    segundo = sortear_submuestra(barajadas, semilla=7)
    assert [f["frame_idx"] for f in primero] == [f["frame_idx"] for f in segundo]
    assert len(primero) == 25
    assert len({f["frame_idx"] for f in primero}) == 25
    # El orden de medición no es el temporal (aleatorizado).
    assert [int(f["frame_idx"]) for f in primero] != sorted(int(f["frame_idx"]) for f in primero)
    # Otra semilla da otra submuestra.
    assert [f["frame_idx"] for f in sortear_submuestra(filas, semilla=8)] != [f["frame_idx"] for f in primero]


def test_sorteo_rechaza_claves_duplicadas() -> None:
    filas = _filas_sesion1_vacias(5)
    filas.append(dict(filas[0]))
    with pytest.raises(ValueError, match="duplicadas"):
        sortear_submuestra(filas)


def test_ejecutar_sorteo_copia_los_png_en_orden_y_no_filtra_valores(tmp_path: Path) -> None:
    n = 12
    directorio_fotogramas = tmp_path / "frames"
    directorio_fotogramas.mkdir()
    for i in range(n):
        (directorio_fotogramas / nombre_fotograma_sesion1(i)).write_bytes(f"png sintetico {i}".encode())
    filas = _filas_tracker([10 * i for i in range(n)], [170.0 - i for i in range(n)], sesion=1, fecha="2026-10-01")
    ruta_s1 = escribir_plantilla(filas, tmp_path / "nivel2_tracker_sesion1.csv")

    resumen = ejecutar_sorteo(ruta_s1, semilla=123)

    assert resumen["k"] == 4
    filas_s2 = leer_plantilla(resumen["plantilla_sesion2"])
    assert list(filas_s2[0].keys()) == list(COLUMNAS_PLANTILLA_TRACKER)
    assert [f["archivo_png"] for f in filas_s2] == [nombre_fotograma_sesion2(i) for i in range(4)]
    assert all(f["sesion"] == "2" and f["tracker_angulo_deg"] == "" for f in filas_s2)
    for fila in filas_s2:
        copia = resumen["directorio_sesion2"] / fila["archivo_png"]
        origen = directorio_fotogramas / nombre_fotograma_sesion1(int(fila["ordinal_muestra"]))
        assert copia.read_bytes() == origen.read_bytes()
        assert not copia.is_symlink()
    assert "Semilla: 123" in resumen["orden"].read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="Ya existe un sorteo"):
        ejecutar_sorteo(ruta_s1, semilla=123)
    # Con --sobrescribir y la misma semilla se reproduce exactamente.
    repetido = ejecutar_sorteo(ruta_s1, semilla=123, sobrescribir=True)
    assert repetido["pares"] == resumen["pares"]


def test_ejecutar_sorteo_no_sobrescribe_una_sesion2_con_mediciones(tmp_path: Path) -> None:
    filas = _filas_tracker([0, 10, 20], [170.0, 150.0, 120.0], sesion=1, fecha="")
    ruta_s1 = escribir_plantilla(filas, tmp_path / "nivel2_tracker_sesion1.csv")
    escribir_plantilla(
        _filas_tracker([10], [149.0], sesion=2, fecha=""), tmp_path / "nivel2_tracker_sesion2.csv"
    )
    with pytest.raises(RuntimeError, match="ya contiene mediciones"):
        ejecutar_sorteo(ruta_s1, sobrescribir=True)


# ---------------------------------------------------------------------------
# Presentación por tramos (acuerdo.py)
# ---------------------------------------------------------------------------


def test_formatear_resumen_oculta_metricas_de_tramos_con_n_pequeno() -> None:
    referencia = np.array([5.0, 10.0, 15.0, 20.0, 25.0, 45.0, 50.0, 100.0, 110.0, 130.0])
    estimado = referencia + np.linspace(-2.0, 2.0, referencia.size)
    resumen = resumen_acuerdo(referencia, estimado)

    por_defecto = formatear_resumen_markdown(resumen)
    assert "sin potencia" not in por_defecto  # comportamiento previo intacto

    filtrado = formatear_resumen_markdown(resumen, n_minimo_tramo=5)
    assert "| [0, 30) | 5 | " in filtrado and "| [0, 30) | 5 | sin potencia" not in filtrado
    assert "| [30, 60) | 2 | sin potencia (n < 5) |" in filtrado


# ---------------------------------------------------------------------------
# Exportador: rótulo y plantilla (requiere el entorno de visión)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def exportador():
    pytest.importorskip("cv2")
    pytest.importorskip("mediapipe")
    from validacion.analisis import exportar_para_kinovea

    return exportar_para_kinovea


@pytest.mark.parametrize(("alto", "ancho"), [(360, 640), (1080, 1920)])
def test_rotulo_queda_arriba_a_la_izquierda_y_no_toca_la_entrada(exportador, alto: int, ancho: int) -> None:
    fotograma = np.full((alto, ancho, 3), 128, dtype=np.uint8)
    original = fotograma.copy()
    rotulado = exportador.rotular_indice_fotograma(fotograma, 30)

    assert np.array_equal(fotograma, original)
    cambiados = np.argwhere(np.any(rotulado != original, axis=2))
    assert cambiados.size > 0
    assert cambiados[:, 0].max() < 0.12 * alto  # franja superior
    assert cambiados[:, 1].max() < 0.25 * ancho  # esquina izquierda
    # Contraste: el recuadro es negro y el texto blanco.
    region = rotulado[: int(0.12 * alto), : int(0.25 * ancho)]
    assert region.min() == 0 and region.max() == 255


def test_plantilla_del_exportador_tiene_una_fila_por_fotograma(exportador) -> None:
    filas_sistema = [{"frame_index": 10 * i} for i in range(4)]
    filas = exportador.construir_filas_plantilla(filas_sistema, nombre_video=VIDEO, lado="izquierda")
    assert [f["frame_idx"] for f in filas] == [0, 10, 20, 30]
    assert [f["archivo_png"] for f in filas] == ["m0000.png", "m0001.png", "m0002.png", "m0003.png"]
    assert all(f["sesion"] == 1 and f["tracker_angulo_deg"] == "" for f in filas)
    with pytest.raises(ValueError):
        exportador.construir_filas_plantilla(filas_sistema, nombre_video=VIDEO, lado="ambas")


def test_exportador_nunca_sobrescribe_una_plantilla_con_mediciones(exportador, tmp_path: Path) -> None:
    directorio = tmp_path / "clip" / "frames"
    directorio.mkdir(parents=True)
    (directorio / "m0000.png").write_bytes(b"x")
    escribir_plantilla(
        _filas_tracker([0], [170.0], sesion=1, fecha=""), tmp_path / "clip" / "nivel2_tracker_sesion1.csv"
    )
    with pytest.raises(RuntimeError, match="ya contiene mediciones"):
        exportador.preparar_directorio_fotogramas(directorio, sobrescribir=True)


def test_exportador_exige_sobrescribir_para_reemplazar_fotogramas(exportador, tmp_path: Path) -> None:
    directorio = tmp_path / "clip" / "frames"
    directorio.mkdir(parents=True)
    (directorio / "m0000.png").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="sobrescribir"):
        exportador.preparar_directorio_fotogramas(directorio, sobrescribir=False)
    exportador.preparar_directorio_fotogramas(directorio, sobrescribir=True)
    assert not (directorio / "m0000.png").exists()
