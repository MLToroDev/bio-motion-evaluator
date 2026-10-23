"""
Contrato común de las plantillas de medición manual del Nivel 2 (Tracker).

Este módulo fija, en un solo lugar, el formato de los ficheros que se intercambian entre
los tres pasos del Nivel 2 del protocolo
(``docs/guias/protocolo_validacion_exactitud.md``):

1. ``exportar_para_kinovea.py`` escribe los fotogramas muestreados como PNG y la
   plantilla vacía de la sesión 1 (``nivel2_tracker_sesion1.csv``).
2. ``sortear_sesion2.py`` lee esa plantilla y escribe la de la sesión 2
   (``nivel2_tracker_sesion2.csv``) con una submuestra aleatoria.
3. ``analizar_nivel2.py`` lee ambas plantillas ya rellenadas y las une con el CSV del
   sistema.

No depende de MediaPipe ni de OpenCV, de modo que el sorteo y el análisis pueden
ejecutarse sin el pipeline de visión instalado.

Convención de nombres de los PNG
--------------------------------
Tracker (Open Source Physics) abre una secuencia de imágenes a partir del primer
archivo tomando los **dígitos finales** del nombre (como máximo cinco) como contador,
el resto del nombre como **prefijo fijo**, e incrementando el contador de uno en uno
hasta que falta un archivo (``org.opensourcephysics.media.core.ImageVideo``). Un nombre
del tipo ``m0003_f00030.png`` rompe esa detección: el prefijo ``m0003_f`` cambia en
cada archivo y el contador (el índice de vídeo) salta de diez en diez, de modo que
Tracker cargaría una sola imagen.

Por eso los PNG se nombran ``m<ordinal:04d>.png`` (sesión 1) y
``s2_<posicion:04d>.png`` (sesión 2): prefijo constante y contador consecutivo desde
cero. El índice original del vídeo **no se pierde**: va rotulado en el propio píxel de
cada PNG y figura en la columna ``frame_idx`` de la plantilla, junto a ``archivo_png``,
que es la tabla de correspondencia archivo -> fotograma.

Columnas de la plantilla
------------------------
Las nueve primeras son las del protocolo (sección 2.7); ``archivo_png`` se añade al
final como tabla de correspondencia y el análisis la ignora.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "COLUMNAS_PLANTILLA_TRACKER",
    "COLUMNAS_OBLIGATORIAS_TRACKER",
    "LADOS_VALIDOS",
    "NOMBRE_PLANTILLA_SESION1",
    "NOMBRE_PLANTILLA_SESION2",
    "ORDINAL_MAXIMO",
    "escribir_plantilla",
    "leer_plantilla",
    "nombre_fotograma_sesion1",
    "nombre_fotograma_sesion2",
    "plantilla_tiene_mediciones",
]

#: Columnas de la plantilla de medición, en el orden en que se escriben.
COLUMNAS_PLANTILLA_TRACKER: tuple[str, ...] = (
    "video",
    "ordinal_muestra",
    "frame_idx",
    "lado",
    "sesion",
    "fecha_medicion",
    "tracker_angulo_deg",
    "confianza_operador",
    "observaciones",
    "archivo_png",
)

#: Columnas sin las cuales una plantilla no es interpretable (``archivo_png`` es opcional).
COLUMNAS_OBLIGATORIAS_TRACKER: tuple[str, ...] = COLUMNAS_PLANTILLA_TRACKER[:-1]

#: Valores admitidos en la columna ``lado`` (mismo vocabulario que el protocolo).
LADOS_VALIDOS: tuple[str, ...] = ("izquierda", "derecha")

NOMBRE_PLANTILLA_SESION1 = "nivel2_tracker_sesion1.csv"
NOMBRE_PLANTILLA_SESION2 = "nivel2_tracker_sesion2.csv"

#: Tracker lee como máximo cinco dígitos finales; con cuatro caben 10 000 muestras.
ORDINAL_MAXIMO = 9999


def _comprobar_ordinal(valor: int) -> int:
    if not 0 <= valor <= ORDINAL_MAXIMO:
        raise ValueError(f"El ordinal {valor} está fuera de [0, {ORDINAL_MAXIMO}].")
    return valor


def nombre_fotograma_sesion1(ordinal: int) -> str:
    """Nombre del PNG de la sesión 1 para el ordinal dado (``m0003.png``)."""
    return f"m{_comprobar_ordinal(ordinal):04d}.png"


def nombre_fotograma_sesion2(posicion: int) -> str:
    """Nombre del PNG de la sesión 2 para la posición aleatorizada dada (``s2_0007.png``)."""
    return f"s2_{_comprobar_ordinal(posicion):04d}.png"


def escribir_plantilla(filas: Iterable[Mapping[str, Any]], ruta: Path) -> Path:
    """
    Escribe una plantilla con las columnas de :data:`COLUMNAS_PLANTILLA_TRACKER`.

    UTF-8 y fin de línea LF, igual que el CSV del sistema. Las claves ausentes en una
    fila se escriben vacías; una clave desconocida es un error de programación y lanza
    ``ValueError`` (comportamiento de ``csv.DictWriter``).
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as manejador:
        escritor = csv.DictWriter(
            manejador, fieldnames=list(COLUMNAS_PLANTILLA_TRACKER), restval="", lineterminator="\n"
        )
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(dict(fila))
    return ruta


def leer_plantilla(ruta: Path) -> list[dict[str, str]]:
    """
    Lee una plantilla y devuelve sus filas como diccionarios de texto (sin convertir).

    Acepta BOM UTF-8 (hojas de cálculo que exportan con BOM) y elimina espacios
    alrededor de cada valor. Lanza ``ValueError`` si falta alguna columna obligatoria.
    """
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe la plantilla: {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as manejador:
        lector = csv.DictReader(manejador)
        columnas = [c.strip() for c in (lector.fieldnames or [])]
        faltan = [c for c in COLUMNAS_OBLIGATORIAS_TRACKER if c not in columnas]
        if faltan:
            raise ValueError(f"A la plantilla {ruta} le faltan columnas obligatorias: {', '.join(faltan)}.")
        filas = []
        for fila in lector:
            filas.append({(clave or "").strip(): (valor or "").strip() for clave, valor in fila.items()})
    return filas


def plantilla_tiene_mediciones(ruta: Path) -> bool:
    """``True`` si la plantilla existe y alguna fila tiene ``tracker_angulo_deg`` no vacío."""
    if not ruta.is_file():
        return False
    return any(fila.get("tracker_angulo_deg", "") for fila in leer_plantilla(ruta))
