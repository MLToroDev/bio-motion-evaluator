#!/usr/bin/env python3
"""
Análisis del Nivel 2: acuerdo del sistema con video-goniometría manual en Tracker.

Implementa el análisis pre-registrado del Nivel 2 del protocolo
(``docs/guias/protocolo_validacion_exactitud.md``, secciones 2.6 y 2.7 y "Criterios
del Nivel 2"), **en el orden que fija el protocolo**:

1. **Criterio habilitante, primero:** acuerdo del operador consigo mismo (sesión 1
   frente a sesión 2 sobre los mismos fotogramas): MAE, desviación estándar de las
   diferencias, ICC(2,1) y Bland-Altman. Se exige MAE intra-observador <= 3,0 grados. El
   veredicto se imprime y se escribe **antes** de cualquier cifra sistema-Tracker.
2. **Acuerdo sistema frente a Tracker** (referencia = sesión 1, o la mediana de varias
   mediciones si se aplica el remedio (a), ver abajo), con
   ``acuerdo.resumen_acuerdo``, y comprobación de los umbrales del Nivel 2: MAE <= 7,0
   grados e ICC(2,1) >= 0,85. El MAE por tramo angular solo se publica donde ``n >= 5``
   (sección 2.3); en el resto se listan las diferencias individuales.

Si el criterio habilitante no se cumple, la parte 2 se calcula igualmente pero se
etiqueta el Nivel 2 como **no concluyente**. El protocolo preelige como salida (a)
medir tres veces cada punto y usar la mediana: si se pasan esas mediciones con
``--sesiones-extra``, la referencia de la parte 2 pasa a ser la mediana por fotograma
(exigiendo al menos tres mediciones válidas) y el resultado se etiqueta como
**condicionado al remedio (a)**. El MAE intra-observador original se reporta siempre.

Convención angular de Tracker
-----------------------------
El transportador de Tracker puede mostrar el **ángulo interno** entre los dos brazos
(cerca de 180 grados con la pierna extendida) o un ángulo con signo según la
orientación de los brazos. Hasta confirmarlo en la versión instalada, el análisis:

- toma el **valor absoluto** del valor anotado, tal cual lo muestra Tracker;
- exige que quede en ``[0, 180]`` y **falla** en caso contrario (un valor reflejo,
  mayor de 180, indica que se midió el ángulo exterior);
- con ``--convencion-tracker interno`` (por defecto) convierte ``flexion = 180 -
  interno``; con ``flexion`` usa el valor directamente;
- **falla** si todos los valores son menores de 2*pi, porque eso indica que Tracker
  estaba configurado en radianes.

Unión con el sistema
--------------------
Cada medición se une al CSV del sistema por ``(video, frame_idx, lado)``, tomando
``left_knee_flexion_angle_deg`` o ``right_knee_flexion_angle_deg`` según el lado. El
CSV del sistema no lleva el nombre del vídeo: se toma de ``--video``, o de
``metadatos_exportacion.json`` junto a la plantilla de la sesión 1, o del único vídeo
que figure en la sesión 1. Son **errores** (el script se detiene): claves duplicadas,
filas de Tracker sin fotograma correspondiente en el sistema, filas de la sesión 2 que
no están en la sesión 1, un número de sesión incoherente y valores fuera de rango. Se
**descartan y se reportan uno a uno**: filas sin valor de Tracker y fotogramas sin
estimación del sistema.

Ejemplo (desde la raíz del repositorio)::

    ~/.venvs/biomotion/bin/python validacion/analisis/analizar_nivel2.py \\
        --sistema validacion/datos/nivel2/<nombre_del_clip>/serie_sistema.csv \\
        --sesion1 validacion/datos/nivel2/<nombre_del_clip>/nivel2_tracker_sesion1.csv \\
        --sesion2 validacion/datos/nivel2/<nombre_del_clip>/nivel2_tracker_sesion2.csv \\
        --convencion-tracker interno

Salidas (en ``validacion/resultados/`` por defecto): ``nivel2_acuerdo.md``,
``nivel2_resumen.json``, ``nivel2_pares.csv``, ``nivel2_bland_altman.png`` y
``nivel2_bland_altman_intraobservador.png``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from validacion.analisis.acuerdo import (  # noqa: E402
    BORDES_RANGO_POR_DEFECTO,
    bland_altman,
    coeficiente_correlacion_intraclase,
    error_medio_absoluto,
    figura_bland_altman,
    formatear_resumen_markdown,
    resumen_acuerdo,
)
from validacion.analisis.plantilla_tracker import LADOS_VALIDOS, leer_plantilla  # noqa: E402

#: Convenciones admitidas para el valor que muestra el transportador de Tracker.
CONVENCIONES_TRACKER: tuple[str, ...] = ("interno", "flexion")

#: Criterio habilitante del pre-registro: MAE intra-observador máximo, en grados.
UMBRAL_MAE_INTRAOBSERVADOR_DEG = 3.0

#: Criterios del Nivel 2 frente al sistema (pre-registro, "Criterios del Nivel 2").
CRITERIOS_SISTEMA_TRACKER: tuple[dict[str, Any], ...] = (
    {"criterio": "MAE sistema vs. Tracker", "clave": "mae", "operador": "<=", "umbral": 7.0, "unidad": "grados"},
    {"criterio": "ICC(2,1)", "clave": "icc", "operador": ">=", "umbral": 0.85, "unidad": ""},
)

#: ``n`` mínimo para publicar el MAE de un tramo angular (protocolo, sección 2.3).
N_MINIMO_TRAMO = 5

#: Mediciones válidas mínimas por fotograma para la mediana del remedio (a).
MEDICIONES_MINIMAS_MEDIANA = 3

#: Separación mínima recomendada entre sesiones (protocolo, sección 2.6).
SEPARACION_MINIMA_HORAS = 48.0

#: Columna del CSV del sistema según el lado medido.
COLUMNA_SISTEMA_POR_LADO = {
    "izquierda": "left_knee_flexion_angle_deg",
    "derecha": "right_knee_flexion_angle_deg",
}

#: Nombre del archivo de metadatos que escribe el exportador junto a la plantilla.
NOMBRE_METADATOS_EXPORTACION = "metadatos_exportacion.json"

DIRECTORIO_RESULTADOS_POR_DEFECTO = _RAIZ_REPOSITORIO / "validacion" / "resultados"

Clave = tuple[str, int, str]


class ErrorDatosNivel2(ValueError):
    """Inconsistencia en los datos de entrada que impide un análisis fiable."""


@dataclass(frozen=True)
class Medicion:
    """Una fila de una plantilla de Tracker, ya validada y convertida a flexión."""

    video: str
    frame_idx: int
    lado: str
    sesion: int
    ordinal_muestra: str
    valor_bruto: str
    flexion_deg: float | None
    confianza_operador: str
    fecha_medicion: str
    observaciones: str

    @property
    def clave(self) -> Clave:
        return (self.video, self.frame_idx, self.lado)


# ---------------------------------------------------------------------------
# Convención angular
# ---------------------------------------------------------------------------


def convertir_a_flexion(valor_bruto: float, convencion: str) -> float:
    """
    Convierte el valor de Tracker a flexión de rodilla en grados.

    Se toma ``abs(valor_bruto)``, se exige que esté en ``[0, 180]`` y, con la
    convención ``interno``, se devuelve ``180 - interno``. Lanza ``ErrorDatosNivel2``
    si el valor no es finito o queda fuera de rango, y ``ValueError`` si la convención
    no es una de :data:`CONVENCIONES_TRACKER`.
    """
    if convencion not in CONVENCIONES_TRACKER:
        raise ValueError(f"Convención no soportada: {convencion!r}. Use una de {CONVENCIONES_TRACKER}.")
    valor = abs(float(valor_bruto))
    if not math.isfinite(valor):
        raise ErrorDatosNivel2(f"Valor de Tracker no finito: {valor_bruto!r}.")
    if valor > 180.0:
        raise ErrorDatosNivel2(
            f"Valor de Tracker fuera de [0, 180]: {valor_bruto!r}. Probablemente se midió el ángulo "
            "reflejo; invierta el sentido del transportador y vuelva a medir."
        )
    return 180.0 - valor if convencion == "interno" else valor


def _interpretar_numero(texto: str, contexto: str) -> float | None:
    """Número decimal de una celda; ``None`` si está vacía. Acepta coma decimal."""
    if texto == "":
        return None
    try:
        return float(texto.replace(",", "."))
    except ValueError as exc:
        raise ErrorDatosNivel2(f"Valor no numérico {texto!r} en {contexto}.") from exc


def comprobar_unidades_en_grados(valores_brutos: Sequence[float]) -> None:
    """
    Falla si todos los valores caben en ``[0, 2*pi]``: indicio de radianes.

    En una sentadilla el ángulo interno pasa por valores cercanos a 180 y la flexión
    supera con holgura los 7 grados, así que una serie entera por debajo de 6,3 no es
    plausible en grados. Solo se aplica con 3 valores o más.
    """
    absolutos = [abs(v) for v in valores_brutos]
    if len(absolutos) >= 3 and max(absolutos) <= 2.0 * math.pi:
        raise ErrorDatosNivel2(
            "Todos los valores de Tracker son menores de 2*pi: parece que el transportador "
            "estaba en radianes. Cambie la unidad de ángulo a grados en Tracker y vuelva a anotar."
        )


# ---------------------------------------------------------------------------
# Carga y validación
# ---------------------------------------------------------------------------


def cargar_sesion(
    ruta: Path,
    *,
    convencion: str,
    sesion_esperada: int | None = None,
) -> dict[Clave, Medicion]:
    """
    Lee una plantilla de Tracker y la valida.

    Devuelve un diccionario por clave ``(video, frame_idx, lado)``; las filas sin
    valor quedan con ``flexion_deg = None`` (el llamador las reporta como descartadas).
    Con ``sesion_esperada`` se exige que todas las filas tengan ese número de sesión;
    sin él, que todas compartan uno mismo.
    """
    filas = leer_plantilla(ruta)
    if not filas:
        raise ErrorDatosNivel2(f"La plantilla {ruta} no tiene filas.")

    mediciones: dict[Clave, Medicion] = {}
    sesiones_vistas: set[int] = set()
    for numero_linea, fila in enumerate(filas, start=2):
        contexto = f"{ruta.name}, línea {numero_linea}"
        lado = fila["lado"]
        if lado not in LADOS_VALIDOS:
            raise ErrorDatosNivel2(f"Lado no válido {lado!r} en {contexto}; use {LADOS_VALIDOS}.")
        try:
            frame_idx = int(fila["frame_idx"])
            sesion = int(fila["sesion"])
        except ValueError as exc:
            raise ErrorDatosNivel2(f"frame_idx o sesion no enteros en {contexto}.") from exc
        if sesion_esperada is not None and sesion != sesion_esperada:
            raise ErrorDatosNivel2(f"Se esperaba sesion = {sesion_esperada} y hay {sesion} en {contexto}.")
        sesiones_vistas.add(sesion)
        if not fila["video"]:
            raise ErrorDatosNivel2(f"Columna 'video' vacía en {contexto}.")

        bruto = _interpretar_numero(fila["tracker_angulo_deg"], contexto)
        try:
            flexion = None if bruto is None else convertir_a_flexion(bruto, convencion)
        except ErrorDatosNivel2 as exc:
            raise ErrorDatosNivel2(f"{exc} ({contexto})") from exc

        medicion = Medicion(
            video=fila["video"],
            frame_idx=frame_idx,
            lado=lado,
            sesion=sesion,
            ordinal_muestra=fila["ordinal_muestra"],
            valor_bruto=fila["tracker_angulo_deg"],
            flexion_deg=flexion,
            confianza_operador=fila["confianza_operador"],
            fecha_medicion=fila["fecha_medicion"],
            observaciones=fila["observaciones"],
        )
        if medicion.clave in mediciones:
            raise ErrorDatosNivel2(f"Clave duplicada {medicion.clave} en {contexto}.")
        mediciones[medicion.clave] = medicion

    if len(sesiones_vistas) != 1:
        raise ErrorDatosNivel2(f"La plantilla {ruta} mezcla sesiones: {sorted(sesiones_vistas)}.")
    comprobar_unidades_en_grados(
        [abs(float(m.valor_bruto.replace(",", "."))) for m in mediciones.values() if m.flexion_deg is not None]
    )
    return mediciones


def cargar_sistema(ruta: Path) -> dict[int, dict[str, float | None]]:
    """
    Lee el CSV del sistema (``exportar_para_kinovea.py``) indexado por ``frame_index``.

    Devuelve, por fotograma, la flexión de cada lado (``None`` si el sistema no dio
    estimación). Lanza ``ErrorDatosNivel2`` ante columnas ausentes o índices duplicados.
    """
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el CSV del sistema: {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as manejador:
        lector = csv.DictReader(manejador)
        necesarias = ("frame_index", *COLUMNA_SISTEMA_POR_LADO.values())
        faltan = [c for c in necesarias if c not in (lector.fieldnames or [])]
        if faltan:
            raise ErrorDatosNivel2(f"Al CSV del sistema le faltan columnas: {', '.join(faltan)}.")
        sistema: dict[int, dict[str, float | None]] = {}
        for numero_linea, fila in enumerate(lector, start=2):
            contexto = f"{ruta.name}, línea {numero_linea}"
            try:
                indice = int(fila["frame_index"])
            except ValueError as exc:
                raise ErrorDatosNivel2(f"frame_index no entero en {contexto}.") from exc
            if indice in sistema:
                raise ErrorDatosNivel2(f"frame_index duplicado {indice} en {contexto}.")
            sistema[indice] = {
                lado: _interpretar_numero((fila[columna] or "").strip(), contexto)
                for lado, columna in COLUMNA_SISTEMA_POR_LADO.items()
            }
    if not sistema:
        raise ErrorDatosNivel2(f"El CSV del sistema {ruta} no tiene filas.")
    return sistema


def resolver_video_sistema(
    video: str | None,
    sesion1: dict[Clave, Medicion],
    ruta_sesion1: Path,
) -> tuple[str, str]:
    """
    Nombre del vídeo al que corresponde el CSV del sistema y de dónde se obtuvo.

    Prioridad: ``--video``; ``metadatos_exportacion.json`` junto a la sesión 1; el
    único vídeo de la sesión 1. Si nada lo determina, error.
    """
    if video:
        return video, "argumento --video"
    ruta_metadatos = ruta_sesion1.parent / NOMBRE_METADATOS_EXPORTACION
    if ruta_metadatos.is_file():
        nombre = json.loads(ruta_metadatos.read_text(encoding="utf-8")).get("nombre_video")
        if nombre:
            return str(nombre), NOMBRE_METADATOS_EXPORTACION
    videos = sorted({clave[0] for clave in sesion1})
    if len(videos) == 1:
        return videos[0], "único vídeo de la sesión 1"
    raise ErrorDatosNivel2(f"La sesión 1 tiene varios vídeos {videos}; indique --video.")


def comprobar_correspondencia_sistema(
    mediciones: dict[Clave, Medicion],
    sistema: dict[int, dict[str, float | None]],
    video_sistema: str,
) -> None:
    """Falla si alguna medición no tiene fotograma correspondiente en el CSV del sistema."""
    sin_pareja = [
        clave for clave in mediciones if clave[0] != video_sistema or clave[1] not in sistema
    ]
    if sin_pareja:
        muestra = ", ".join(str(c) for c in sin_pareja[:5])
        raise ErrorDatosNivel2(
            f"{len(sin_pareja)} filas de Tracker sin correspondencia en el CSV del sistema "
            f"(vídeo {video_sistema!r}): {muestra}{' ...' if len(sin_pareja) > 5 else ''}"
        )


def comprobar_subconjunto(
    subconjunto: dict[Clave, Medicion],
    sesion1: dict[Clave, Medicion],
    nombre: str,
) -> None:
    """Falla si ``subconjunto`` contiene claves que no están en la sesión 1."""
    ajenas = [clave for clave in subconjunto if clave not in sesion1]
    if ajenas:
        raise ErrorDatosNivel2(
            f"{len(ajenas)} filas de {nombre} no existen en la sesión 1: "
            + ", ".join(str(c) for c in ajenas[:5])
        )


def huella_sha256(ruta: Path) -> str:
    """SHA-256 completo del archivo."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Parte 1: criterio habilitante intra-observador
# ---------------------------------------------------------------------------


def _horas_entre(fecha_a: str, fecha_b: str) -> float | None:
    try:
        a = datetime.fromisoformat(fecha_a)
        b = datetime.fromisoformat(fecha_b)
    except ValueError:
        return None
    if (a.tzinfo is None) != (b.tzinfo is None):
        return None
    return abs((b - a).total_seconds()) / 3600.0


def evaluar_intraobservador(
    sesion1: dict[Clave, Medicion],
    sesion2: dict[Clave, Medicion],
    *,
    umbral_mae: float = UMBRAL_MAE_INTRAOBSERVADOR_DEG,
) -> dict[str, Any]:
    """
    Acuerdo del operador consigo mismo sobre los fotogramas medidos en ambas sesiones.

    Diferencia = ``sesion2 - sesion1``. Devuelve ``n``, ``mae``,
    ``desviacion_estandar_diferencias``, ``icc``, ``bland_altman``, ``cumple`` (MAE <=
    umbral), los pares usados, los descartados y la separación mínima entre sesiones en
    horas (si las fechas se pueden interpretar). Lanza ``ErrorDatosNivel2`` con menos
    de 2 pares válidos.
    """
    comprobar_subconjunto(sesion2, sesion1, "la sesión 2")
    pares: list[dict[str, Any]] = []
    descartados: list[dict[str, Any]] = []
    separaciones: list[float] = []
    for clave in sorted(sesion2):
        m2 = sesion2[clave]
        m1 = sesion1[clave]
        if m1.flexion_deg is None or m2.flexion_deg is None:
            sesiones_vacias = [s for s, m in ((1, m1), (2, m2)) if m.flexion_deg is None]
            descartados.append(
                {
                    "video": clave[0],
                    "frame_idx": clave[1],
                    "lado": clave[2],
                    "motivo": "sin valor de Tracker en la sesión " + " y ".join(map(str, sesiones_vacias)),
                    "observaciones": " | ".join(o for o in (m1.observaciones, m2.observaciones) if o),
                }
            )
            continue
        pares.append(
            {
                "video": clave[0],
                "frame_idx": clave[1],
                "lado": clave[2],
                "sesion1_flexion_deg": m1.flexion_deg,
                "sesion2_flexion_deg": m2.flexion_deg,
                "diferencia_deg": m2.flexion_deg - m1.flexion_deg,
            }
        )
        horas = _horas_entre(m1.fecha_medicion, m2.fecha_medicion)
        if horas is not None:
            separaciones.append(horas)

    if len(pares) < 2:
        raise ErrorDatosNivel2(
            f"Solo hay {len(pares)} pares válidos sesión 1 - sesión 2; se necesitan al menos 2."
        )
    s1 = np.array([p["sesion1_flexion_deg"] for p in pares])
    s2 = np.array([p["sesion2_flexion_deg"] for p in pares])
    ba = bland_altman(s1, s2)
    mae = error_medio_absoluto(s1, s2)
    return {
        "n": len(pares),
        "n_sesion2": len(sesion2),
        "mae": mae,
        "desviacion_estandar_diferencias": ba["desviacion_estandar_diferencias"],
        "bland_altman": ba,
        "icc": coeficiente_correlacion_intraclase(s1, s2),
        "umbral_mae": umbral_mae,
        "cumple": bool(mae <= umbral_mae),
        "separacion_minima_horas": min(separaciones) if separaciones else None,
        "pares": pares,
        "descartados": descartados,
    }


# ---------------------------------------------------------------------------
# Parte 2: sistema frente a Tracker
# ---------------------------------------------------------------------------


def construir_referencia(
    sesion1: dict[Clave, Medicion],
    sesiones_extra: Sequence[dict[Clave, Medicion]] = (),
) -> tuple[dict[Clave, dict[str, Any]], list[dict[str, Any]]]:
    """
    Valor de referencia de Tracker por fotograma.

    Sin sesiones extra, la referencia es la sesión 1. Con ellas (remedio (a) del
    protocolo), es la **mediana** de las mediciones válidas de la sesión 1 y las
    extra, y se exige un mínimo de :data:`MEDICIONES_MINIMAS_MEDIANA`; los fotogramas
    que no lo alcanzan se descartan con su motivo.
    """
    for indice, extra in enumerate(sesiones_extra, start=1):
        comprobar_subconjunto(extra, sesion1, f"la sesión extra {indice}")

    referencia: dict[Clave, dict[str, Any]] = {}
    descartados: list[dict[str, Any]] = []
    for clave in sorted(sesion1):
        m1 = sesion1[clave]
        valores = [m.flexion_deg for m in (m1, *(e[clave] for e in sesiones_extra if clave in e))]
        validos = [v for v in valores if v is not None]
        if not sesiones_extra:
            if m1.flexion_deg is None:
                descartados.append(_descarte(m1, "sin valor de Tracker en la sesión 1"))
                continue
            referencia[clave] = {"valor": m1.flexion_deg, "n_mediciones": 1, "medicion": m1}
            continue
        if len(validos) < MEDICIONES_MINIMAS_MEDIANA:
            descartados.append(
                _descarte(m1, f"solo {len(validos)} mediciones válidas (< {MEDICIONES_MINIMAS_MEDIANA}) para la mediana")
            )
            continue
        referencia[clave] = {"valor": float(statistics.median(validos)), "n_mediciones": len(validos), "medicion": m1}
    return referencia, descartados


def _descarte(medicion: Medicion, motivo: str) -> dict[str, Any]:
    return {
        "video": medicion.video,
        "frame_idx": medicion.frame_idx,
        "lado": medicion.lado,
        "motivo": motivo,
        "observaciones": medicion.observaciones,
    }


def emparejar_con_sistema(
    referencia: dict[Clave, dict[str, Any]],
    sistema: dict[int, dict[str, float | None]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pares referencia-sistema; descarta (y reporta) los fotogramas sin estimación."""
    pares: list[dict[str, Any]] = []
    descartados: list[dict[str, Any]] = []
    for clave, dato in referencia.items():
        medicion: Medicion = dato["medicion"]
        estimado = sistema[clave[1]][clave[2]]
        if estimado is None or not math.isfinite(estimado):
            descartados.append(_descarte(medicion, "sin estimación del sistema (pose no detectada)"))
            continue
        pares.append(
            {
                "video": clave[0],
                "frame_idx": clave[1],
                "lado": clave[2],
                "ordinal_muestra": medicion.ordinal_muestra,
                "tracker_bruto_sesion1": medicion.valor_bruto,
                "tracker_flexion_deg": dato["valor"],
                "n_mediciones_referencia": dato["n_mediciones"],
                "sistema_flexion_deg": float(estimado),
                "diferencia_deg": float(estimado) - dato["valor"],
                "confianza_operador": medicion.confianza_operador,
                "observaciones": medicion.observaciones,
            }
        )
    return pares, descartados


def evaluar_criterios(resumen: dict[str, Any]) -> list[dict[str, Any]]:
    """Compara MAE e ICC(2,1) con los umbrales pre-registrados del Nivel 2."""
    valores = {"mae": resumen["mae"], "icc": resumen["icc"]["icc"]}
    filas = []
    for criterio in CRITERIOS_SISTEMA_TRACKER:
        valor = float(valores[criterio["clave"]])
        if not math.isfinite(valor):
            cumple = False
        elif criterio["operador"] == "<=":
            cumple = valor <= criterio["umbral"]
        else:
            cumple = valor >= criterio["umbral"]
        filas.append({**criterio, "valor": valor, "cumple": bool(cumple)})
    return filas


def diferencias_en_tramos_sin_potencia(
    pares: list[dict[str, Any]],
    resumen: dict[str, Any],
    *,
    n_minimo: int = N_MINIMO_TRAMO,
) -> list[dict[str, Any]]:
    """
    Diferencias individuales de los tramos con ``0 < n < n_minimo``.

    Usa los mismos bordes y la misma regla de cierre que ``acuerdo.error_por_rango``
    (semiabiertos salvo el último), aplicados sobre el valor de referencia.
    """
    salida = []
    tramos = resumen["error_por_rango"]
    for posicion, tramo in enumerate(tramos):
        if not 0 < tramo["n"] < n_minimo:
            continue
        es_ultimo = posicion == len(tramos) - 1
        inferior, superior = tramo["limite_inferior_deg"], tramo["limite_superior_deg"]
        for par in pares:
            ref = par["tracker_flexion_deg"]
            dentro = inferior <= ref <= superior if es_ultimo else inferior <= ref < superior
            if dentro:
                salida.append({"tramo": tramo["etiqueta"], **par})
    return salida


def estratificar_por_confianza(pares: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """MAE y sesgo por valor de ``confianza_operador`` (vacío = "sin anotar")."""
    grupos: dict[str, list[float]] = {}
    for par in pares:
        grupos.setdefault(par["confianza_operador"] or "sin anotar", []).append(par["diferencia_deg"])
    filas = []
    for nivel in sorted(grupos):
        dif = np.array(grupos[nivel])
        filas.append(
            {
                "confianza_operador": nivel,
                "n": int(dif.size),
                "mae": float(np.mean(np.abs(dif))),
                "sesgo": float(np.mean(dif)),
            }
        )
    return filas


def veredicto_nivel2(intra: dict[str, Any], criterios: list[dict[str, Any]], *, remedio_aplicado: bool) -> str:
    """Etiqueta final del Nivel 2 según el orden de decisión pre-registrado."""
    cumple_todo = all(c["cumple"] for c in criterios)
    resultado = "cumple los criterios" if cumple_todo else "no cumple los criterios"
    if intra["cumple"]:
        return f"concluyente: {resultado}"
    if remedio_aplicado:
        return f"condicionado al remedio (a), mediana de mediciones repetidas: {resultado}"
    return "no concluyente (criterio habilitante intra-observador no cumplido)"


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------


def analizar(
    ruta_sistema: Path,
    ruta_sesion1: Path,
    ruta_sesion2: Path,
    *,
    convencion: str = "interno",
    video: str | None = None,
    rutas_extra: Sequence[Path] = (),
    bordes_rango: Sequence[float] = BORDES_RANGO_POR_DEFECTO,
) -> dict[str, Any]:
    """
    Ejecuta el análisis completo del Nivel 2 y devuelve un diccionario con todo.

    No escribe nada en disco. Lanza ``ErrorDatosNivel2`` ante datos inconsistentes.
    """
    if convencion not in CONVENCIONES_TRACKER:
        raise ValueError(f"Convención no soportada: {convencion!r}.")
    sesion1 = cargar_sesion(ruta_sesion1, convencion=convencion, sesion_esperada=1)
    sesion2 = cargar_sesion(ruta_sesion2, convencion=convencion, sesion_esperada=2)
    extras = [cargar_sesion(r, convencion=convencion) for r in rutas_extra]
    for ruta, extra in zip(rutas_extra, extras, strict=True):
        numero = next(iter(extra.values())).sesion
        if numero in (1, 2):
            raise ErrorDatosNivel2(f"La sesión extra {ruta.name} usa sesion = {numero}; use 3 o más.")
    sistema = cargar_sistema(ruta_sistema)
    video_sistema, origen_video = resolver_video_sistema(video, sesion1, ruta_sesion1)

    for mediciones in (sesion1, sesion2, *extras):
        comprobar_correspondencia_sistema(mediciones, sistema, video_sistema)

    advertencias: list[str] = []
    ruta_metadatos = ruta_sesion1.parent / NOMBRE_METADATOS_EXPORTACION
    if ruta_metadatos.is_file():
        huella_esperada = json.loads(ruta_metadatos.read_text(encoding="utf-8")).get("sha256_csv_sistema")
        if huella_esperada and huella_esperada != huella_sha256(ruta_sistema):
            advertencias.append(
                "El CSV del sistema no coincide (SHA-256) con el que se exportó junto a los fotogramas. "
                "Si se regeneró con el pipeline vigente, compruebe que los ángulos no cambiaron."
            )

    # Parte 1, primero y por separado.
    intra = evaluar_intraobservador(sesion1, sesion2)
    if intra["separacion_minima_horas"] is not None and intra["separacion_minima_horas"] < SEPARACION_MINIMA_HORAS:
        advertencias.append(
            f"La separación mínima entre sesiones es de {intra['separacion_minima_horas']:.1f} h, "
            f"inferior a las {SEPARACION_MINIMA_HORAS:.0f} h del protocolo."
        )
    if intra["separacion_minima_horas"] is None:
        advertencias.append("No se pudo comprobar la separación entre sesiones (fecha_medicion vacía o no ISO 8601).")

    # Parte 2.
    referencia, descartados_referencia = construir_referencia(sesion1, extras)
    pares, descartados_sistema = emparejar_con_sistema(referencia, sistema)
    if len(pares) < 3:
        raise ErrorDatosNivel2(f"Solo hay {len(pares)} pares sistema-Tracker válidos; se necesitan al menos 3.")
    ref = np.array([p["tracker_flexion_deg"] for p in pares])
    est = np.array([p["sistema_flexion_deg"] for p in pares])
    resumen = resumen_acuerdo(ref, est, bordes_rango=bordes_rango)
    criterios = evaluar_criterios(resumen)
    remedio = bool(extras)

    return {
        "fecha_ejecucion": time.strftime("%Y-%m-%d %H:%M:%S"),
        "entradas": {
            "sistema": _describir_entrada(ruta_sistema, len(sistema)),
            "sesion1": _describir_entrada(ruta_sesion1, len(sesion1)),
            "sesion2": _describir_entrada(ruta_sesion2, len(sesion2)),
            "sesiones_extra": [_describir_entrada(r, len(e)) for r, e in zip(rutas_extra, extras, strict=True)],
        },
        "parametros": {
            "convencion_tracker": convencion,
            "video_sistema": video_sistema,
            "origen_nombre_video": origen_video,
            "umbral_mae_intraobservador_deg": UMBRAL_MAE_INTRAOBSERVADOR_DEG,
            "n_minimo_tramo": N_MINIMO_TRAMO,
            "bordes_rango_deg": list(bordes_rango),
            "remedio_mediana_aplicado": remedio,
            "lados": sorted({clave[2] for clave in sesion1}),
        },
        "advertencias": advertencias,
        "intraobservador": intra,
        "sistema_vs_tracker": {
            "resumen": resumen,
            "criterios": criterios,
            "pares": pares,
            "descartados": descartados_referencia + descartados_sistema,
            "diferencias_tramos_sin_potencia": diferencias_en_tramos_sin_potencia(pares, resumen),
            "por_confianza": estratificar_por_confianza(pares),
        },
        "veredicto": veredicto_nivel2(intra, criterios, remedio_aplicado=remedio),
    }


def _describir_entrada(ruta: Path, filas: int) -> dict[str, Any]:
    try:
        relativa = str(ruta.resolve().relative_to(_RAIZ_REPOSITORIO))
    except ValueError:
        relativa = ruta.name
    return {"ruta": relativa, "sha256": huella_sha256(ruta), "filas": filas}


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------


def _si_no(valor: bool) -> str:
    return "**cumple**" if valor else "**no cumple**"


def _tabla_descartados(descartados: list[dict[str, Any]]) -> list[str]:
    if not descartados:
        return ["Ninguno.", ""]
    lineas = ["| Vídeo | frame_idx | Lado | Motivo | Observaciones |", "| --- | --- | --- | --- | --- |"]
    for d in descartados:
        lineas.append(f"| {d['video']} | {d['frame_idx']} | {d['lado']} | {d['motivo']} | {d['observaciones'] or '-'} |")
    lineas.append("")
    return lineas


def formatear_informe(resultado: dict[str, Any], *, nombre_figura: str, nombre_figura_intra: str) -> str:
    """Informe Markdown del Nivel 2. Función pura: no recalcula nada."""
    intra = resultado["intraobservador"]
    parte2 = resultado["sistema_vs_tracker"]
    resumen = parte2["resumen"]
    param = resultado["parametros"]
    ba_i = intra["bland_altman"]
    icc_i = intra["icc"]
    ic_icc_i = icc_i["intervalo_confianza_95"]

    lineas = [
        "# Nivel 2 - Acuerdo del sistema con video-goniometría manual (Tracker)",
        "",
        "**Protocolo:** `docs/guias/protocolo_validacion_exactitud.md`, Nivel 2.",
        f"Fecha de ejecución: {resultado['fecha_ejecucion']}.",
        "",
        "Generado por `validacion/analisis/analizar_nivel2.py` a partir de los CSV listados abajo. "
        "Ningún valor de este informe se edita a mano: para corregirlo, se corrigen los CSV y se "
        "vuelve a ejecutar el script.",
        "",
        "## Entradas",
        "",
        "| Archivo | Filas | SHA-256 (12) |",
        "| --- | --- | --- |",
    ]
    entradas = resultado["entradas"]
    for etiqueta, entrada in (
        ("Sistema", entradas["sistema"]),
        ("Tracker, sesión 1", entradas["sesion1"]),
        ("Tracker, sesión 2", entradas["sesion2"]),
        *((f"Tracker, sesión extra {i}", e) for i, e in enumerate(entradas["sesiones_extra"], start=1)),
    ):
        lineas.append(f"| {etiqueta}: `{entrada['ruta']}` | {entrada['filas']} | `{entrada['sha256'][:12]}` |")
    lineas += [
        "",
        "## Parámetros",
        "",
        "| Parámetro | Valor |",
        "| --- | --- |",
        f"| Vídeo del CSV del sistema | `{param['video_sistema']}` ({param['origen_nombre_video']}) |",
        f"| Lado(s) medido(s) | {', '.join(param['lados'])} |",
        f"| Convención de Tracker | `{param['convencion_tracker']}` "
        + ("(flexión = 180 - abs(valor))" if param["convencion_tracker"] == "interno" else "(flexión = abs(valor))")
        + " |",
        f"| Criterio habilitante | MAE intra-observador <= {param['umbral_mae_intraobservador_deg']:.1f} grados |",
        f"| n mínimo para MAE por tramo | {param['n_minimo_tramo']} |",
        f"| Remedio (a), mediana de mediciones repetidas | {'aplicado' if param['remedio_mediana_aplicado'] else 'no aplicado'} |",
        "",
    ]
    if resultado["advertencias"]:
        lineas += ["## Advertencias", ""] + [f"- {a}" for a in resultado["advertencias"]] + [""]

    lineas += [
        "## 1. Criterio habilitante: error intra-observador (se evalúa primero)",
        "",
        "Diferencia = sesión 2 - sesión 1, sobre los mismos fotogramas.",
        "",
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| Fotogramas en la sesión 2 | {intra['n_sesion2']} |",
        f"| Pares analizados (n) | {intra['n']} |",
        f"| MAE (grados) | {intra['mae']:.2f} |",
        f"| Desviación estándar de las diferencias (grados) | {intra['desviacion_estandar_diferencias']:.2f} |",
        f"| Sesgo (grados) | {ba_i['sesgo']:+.2f} |",
        f"| Límites de acuerdo 95 % (grados) | [{ba_i['limite_acuerdo_inferior']:+.2f}, {ba_i['limite_acuerdo_superior']:+.2f}] |",
        f"| ICC(2,1) | {icc_i['icc']:.3f} (IC 95 % [{ic_icc_i[0]:.3f}, {ic_icc_i[1]:.3f}]) |",
        "| Separación mínima entre sesiones | "
        + (f"{intra['separacion_minima_horas']:.1f} h" if intra["separacion_minima_horas"] is not None else "no disponible")
        + " |",
        "",
        f"**Veredicto del criterio habilitante: MAE = {intra['mae']:.2f} grados frente a <= "
        f"{intra['umbral_mae']:.1f} grados -> {'CUMPLE' if intra['cumple'] else 'NO CUMPLE'}.**",
        "",
    ]
    if not intra["cumple"]:
        lineas += [
            "El comparador no alcanza la resolución exigida. Según el pre-registro (sección 2.6), "
            "la salida preelegida es (a) medir tres veces cada punto y usar la mediana "
            "(`--sesiones-extra`); si no se aplica, el Nivel 2 se declara **no concluyente** y la "
            "validación se apoya en el Nivel 1. Las cifras de la sección 2 se publican solo como "
            "descripción.",
            "",
        ]
    lineas += [f"Figura: `{nombre_figura_intra}`.", "", "Pares descartados de la parte 1:", ""]
    lineas += _tabla_descartados(intra["descartados"])

    titulo_parte2 = "## 2. Acuerdo sistema frente a Tracker"
    if not intra["cumple"] and not param["remedio_mediana_aplicado"]:
        titulo_parte2 += " (solo descriptivo: Nivel 2 no concluyente)"
    referencia_texto = (
        "mediana por fotograma de la sesión 1 y las sesiones extra (remedio (a))"
        if param["remedio_mediana_aplicado"]
        else "sesión 1 de Tracker"
    )
    lineas += [
        titulo_parte2,
        "",
        f"Referencia: {referencia_texto}. Diferencia = sistema - Tracker (positivo: el sistema "
        "sobreestima la flexión).",
        "",
        formatear_resumen_markdown(
            resumen, titulo="Resumen de acuerdo sistema-Tracker", n_minimo_tramo=N_MINIMO_TRAMO
        ),
    ]
    sin_potencia = parte2["diferencias_tramos_sin_potencia"]
    if sin_potencia:
        lineas += [
            f"#### Diferencias individuales en tramos con n < {N_MINIMO_TRAMO}",
            "",
            "| Tramo | frame_idx | Tracker (grados) | Sistema (grados) | Diferencia (grados) |",
            "| --- | --- | --- | --- | --- |",
        ]
        for fila in sin_potencia:
            lineas.append(
                f"| {fila['tramo']} | {fila['frame_idx']} | {fila['tracker_flexion_deg']:.2f} | "
                f"{fila['sistema_flexion_deg']:.2f} | {fila['diferencia_deg']:+.2f} |"
            )
        lineas.append("")

    lineas += [
        "#### Criterios de aceptación del Nivel 2 (pre-registro)",
        "",
        "| Criterio | Umbral | Valor | Resultado |",
        "| --- | --- | --- | --- |",
        f"| Habilitante: MAE intra-observador | <= {intra['umbral_mae']:.1f} grados | {intra['mae']:.2f} | {_si_no(intra['cumple'])} |",
    ]
    for c in parte2["criterios"]:
        es_mae = c["clave"] == "mae"
        umbral = f"{c['operador']} {c['umbral']:{'.1f' if es_mae else '.2f'}} {c['unidad']}".strip()
        lineas.append(
            f"| {c['criterio']} | {umbral} | {c['valor']:{'.2f' if es_mae else '.3f'}} | {_si_no(c['cumple'])} |"
        )
    lineas += [
        "",
        f"El error intra-observador (MAE {intra['mae']:.2f} grados) es la cota inferior del error "
        "detectable con este comparador: un MAE sistema-Tracker de ese orden es indistinguible de "
        "un acuerdo perfecto.",
        "",
        "#### Estratificación por confianza del operador",
        "",
        "1 = referencias óseas claras, 2 = dudosas, 3 = estimadas por oclusión.",
        "",
        "| Confianza | n | MAE (grados) | Sesgo (grados) |",
        "| --- | --- | --- | --- |",
    ]
    for fila in parte2["por_confianza"]:
        lineas.append(f"| {fila['confianza_operador']} | {fila['n']} | {fila['mae']:.2f} | {fila['sesgo']:+.2f} |")
    lineas += ["", f"Figura: `{nombre_figura}`.", "", "Pares descartados de la parte 2:", ""]
    lineas += _tabla_descartados(parte2["descartados"])
    lineas += [
        "## 3. Veredicto del Nivel 2",
        "",
        f"**{resultado['veredicto']}.**",
        "",
        "Notas de alcance: Tracker, como Kinovea, es un segundo estimador con error propio; lo que "
        "se mide es acuerdo entre métodos, no exactitud. Se mide una sola pierna (la más cercana a "
        "la cámara) y solo flexión: la asimetría bilateral no se evalúa en este nivel. El CSV del "
        "sistema no incluye la `visibility` de los landmarks, por lo que no se condiciona el "
        "análisis a ella.",
        "",
    ]
    return "\n".join(lineas)


def _a_json(valor: Any) -> Any:
    """Convierte a tipos serializables; NaN e infinito pasan a ``None``."""
    if isinstance(valor, dict):
        return {str(k): _a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_a_json(v) for v in valor]
    if isinstance(valor, Medicion):
        return None
    if isinstance(valor, (np.floating, float)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    return valor


def escribir_resultados(resultado: dict[str, Any], directorio: Path, *, prefijo: str = "nivel2") -> dict[str, Path]:
    """Escribe informe, JSON, CSV de pares y las dos figuras de Bland-Altman."""
    directorio.mkdir(parents=True, exist_ok=True)
    rutas = {
        "informe": directorio / f"{prefijo}_acuerdo.md",
        "resumen": directorio / f"{prefijo}_resumen.json",
        "pares": directorio / f"{prefijo}_pares.csv",
        "figura": directorio / f"{prefijo}_bland_altman.png",
        "figura_intra": directorio / f"{prefijo}_bland_altman_intraobservador.png",
    }
    intra = resultado["intraobservador"]
    pares = resultado["sistema_vs_tracker"]["pares"]

    figura_bland_altman(
        [p["sesion1_flexion_deg"] for p in intra["pares"]],
        [p["sesion2_flexion_deg"] for p in intra["pares"]],
        rutas["figura_intra"],
        titulo="Bland-Altman intra-observador: Tracker sesion 2 frente a sesion 1",
    )
    figura_bland_altman(
        [p["tracker_flexion_deg"] for p in pares],
        [p["sistema_flexion_deg"] for p in pares],
        rutas["figura"],
        titulo="Bland-Altman: sistema frente a Tracker (flexion de rodilla)",
    )
    rutas["informe"].write_text(
        formatear_informe(resultado, nombre_figura=rutas["figura"].name, nombre_figura_intra=rutas["figura_intra"].name),
        encoding="utf-8",
    )
    rutas["resumen"].write_text(
        json.dumps(_a_json(resultado), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    columnas = list(pares[0].keys())
    with rutas["pares"].open("w", encoding="utf-8", newline="") as manejador:
        escritor = csv.DictWriter(manejador, fieldnames=columnas, lineterminator="\n")
        escritor.writeheader()
        for par in pares:
            escritor.writerow(par)
    return rutas


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analiza el Nivel 2: intra-observador de Tracker y acuerdo sistema-Tracker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--sistema", required=True, help="CSV del sistema (exportar_para_kinovea.py).")
    parser.add_argument("--sesion1", required=True, help="Plantilla de Tracker rellenada, sesión 1.")
    parser.add_argument("--sesion2", required=True, help="Plantilla de Tracker rellenada, sesión 2.")
    parser.add_argument(
        "--convencion-tracker",
        choices=CONVENCIONES_TRACKER,
        default="interno",
        help="Qué muestra el transportador de Tracker: ángulo interno (180 = pierna recta) o flexión.",
    )
    parser.add_argument(
        "--sesiones-extra",
        nargs="*",
        default=[],
        metavar="CSV",
        help="Mediciones repetidas (sesion >= 3) para el remedio (a): referencia = mediana por fotograma.",
    )
    parser.add_argument("--video", default=None, help="Nombre del vídeo del CSV del sistema (si no se puede inferir).")
    parser.add_argument(
        "--directorio-salida", default=str(DIRECTORIO_RESULTADOS_POR_DEFECTO), help="Dónde escribir los resultados."
    )
    parser.add_argument("--prefijo", default="nivel2", help="Prefijo de los archivos de salida.")
    return parser


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de línea de comandos. Devuelve el código de salida del proceso."""
    args = _construir_parser().parse_args(argumentos)
    try:
        resultado = analizar(
            Path(args.sistema).expanduser(),
            Path(args.sesion1).expanduser(),
            Path(args.sesion2).expanduser(),
            convencion=args.convencion_tracker,
            video=args.video,
            rutas_extra=[Path(r).expanduser() for r in args.sesiones_extra],
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    intra = resultado["intraobservador"]
    print("1. Criterio habilitante (intra-observador, se evalúa primero)")
    print(f"   n = {intra['n']}  MAE = {intra['mae']:.2f} grados  SD = {intra['desviacion_estandar_diferencias']:.2f}")
    print(f"   Umbral <= {intra['umbral_mae']:.1f} grados -> {'CUMPLE' if intra['cumple'] else 'NO CUMPLE'}")
    print("")
    parte2 = resultado["sistema_vs_tracker"]
    print("2. Sistema frente a Tracker")
    print(f"   n = {parte2['resumen']['n']}  descartados = {len(parte2['descartados'])}")
    for c in parte2["criterios"]:
        print(f"   {c['criterio']}: {c['valor']:.3f} ({c['operador']} {c['umbral']}) -> {'cumple' if c['cumple'] else 'no cumple'}")
    print("")
    print(f"Veredicto del Nivel 2: {resultado['veredicto']}")
    for aviso in resultado["advertencias"]:
        print(f"AVISO: {aviso}")

    rutas = escribir_resultados(resultado, Path(args.directorio_salida).expanduser(), prefijo=args.prefijo)
    print("")
    for etiqueta, ruta in rutas.items():
        print(f"  {etiqueta:<13}: {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
