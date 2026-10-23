#!/usr/bin/env python3
"""
Sorteo de la submuestra de la sesión 2 (error intra-observador) del Nivel 2.

El protocolo (``docs/guias/protocolo_validacion_exactitud.md``, sección 2.6) exige
volver a medir, al menos 48 horas después de la sesión 1, una submuestra aleatoria del
**33 %** de los fotogramas, **en orden aleatorizado** y **sin consultar los valores de
la sesión 1**, y que la aleatorización la haga un script y no el operador "a ojo". Este
script es esa aleatorización.

Qué hace
--------
1. Lee la plantilla de la sesión 1 (vacía o ya rellenada: **no lee ni muestra los
   valores medidos**, solo las claves ``video``, ``frame_idx``, ``lado``,
   ``ordinal_muestra`` y ``archivo_png``).
2. Ordena las filas por ``(video, lado, frame_idx)``, para que el resultado no dependa
   del orden en que estén guardadas, y sortea ``ceil(fraccion * n)`` filas con
   ``random.Random(semilla).sample``, que ya devuelve la selección en orden aleatorio.
3. Escribe ``nivel2_tracker_sesion2.csv`` (``sesion = 2``, columnas de valor vacías)
   con las filas en el orden sorteado.
4. **Copia** (no enlaza) cada PNG de la sesión 1 a ``sesion2/`` con el nombre
   ``s2_<posicion:04d>.png``, de modo que Tracker abre ``s2_0000.png`` como secuencia y
   la recorre en el orden aleatorizado. Se copia en lugar de crear enlaces simbólicos
   porque un enlace muestra el nombre original en el explorador de archivos y se rompe
   si se mueve la carpeta. El índice original sigue rotulado en cada imagen.
5. Escribe ``sesion2/orden_sesion2.txt`` con la correspondencia ``s2_XXXX.png <-
   mXXXX.png``, la semilla y la fracción, para la auditoría.

Semilla
-------
La semilla por defecto es :data:`SEMILLA_POR_DEFECTO` (20261023, la fecha en que se
fijó este procedimiento). Se puede cambiar con ``--semilla``, pero debe decidirse y
anotarse en la bitácora **antes** de ejecutar el sorteo. El mismo fichero de entrada con
la misma semilla produce siempre la misma submuestra y el mismo orden.

Para evitar sorteos repetidos hasta "encontrar" una submuestra favorable, el script
**no sobrescribe** una sesión 2 existente salvo con ``--sobrescribir``, y nunca si la
plantilla de la sesión 2 ya contiene mediciones.

Ejemplo (desde la raíz del repositorio)::

    ~/.venvs/biomotion/bin/python validacion/analisis/sortear_sesion2.py \\
        --sesion1 validacion/datos/nivel2/<nombre_del_clip>/nivel2_tracker_sesion1.csv
"""

from __future__ import annotations

import argparse
import math
import random
import shutil
import sys
from pathlib import Path
from typing import Any

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from validacion.analisis.plantilla_tracker import (  # noqa: E402
    NOMBRE_PLANTILLA_SESION2,
    escribir_plantilla,
    leer_plantilla,
    nombre_fotograma_sesion1,
    nombre_fotograma_sesion2,
    plantilla_tiene_mediciones,
)

#: Semilla fija y documentada del sorteo (fecha de fijación del procedimiento).
SEMILLA_POR_DEFECTO = 20261023

#: Fracción de la sesión 1 que se vuelve a medir (protocolo, sección 2.6).
FRACCION_POR_DEFECTO = 0.33

NOMBRE_DIRECTORIO_SESION2 = "sesion2"
NOMBRE_ORDEN_SESION2 = "orden_sesion2.txt"


def tamano_submuestra(n: int, fraccion: float) -> int:
    """
    ``ceil(fraccion * n)``, protegido contra el error de coma flotante.

    Sin el redondeo previo, ``0.33 * 300`` vale ``99.00000000000001`` y el techo daría
    100 en lugar de 99. Se exige al menos una fila si ``n > 0``.
    """
    if n < 0:
        raise ValueError("n no puede ser negativo.")
    if not 0.0 < fraccion <= 1.0:
        raise ValueError("La fracción debe estar en (0, 1].")
    if n == 0:
        return 0
    return max(1, math.ceil(round(n * fraccion, 9)))


def _clave_orden(fila: dict[str, str]) -> tuple[str, str, int]:
    try:
        indice = int(fila["frame_idx"])
    except ValueError as exc:
        raise ValueError(f"frame_idx no entero en la sesión 1: {fila['frame_idx']!r}.") from exc
    return (fila["video"], fila["lado"], indice)


def sortear_submuestra(
    filas_sesion1: list[dict[str, str]],
    *,
    semilla: int = SEMILLA_POR_DEFECTO,
    fraccion: float = FRACCION_POR_DEFECTO,
) -> list[dict[str, str]]:
    """
    Devuelve la submuestra sorteada, ya en el orden aleatorizado de medición.

    Función pura y determinista: no depende del orden de ``filas_sesion1`` (se ordenan
    antes por ``(video, lado, frame_idx)``) y usa un generador local, sin tocar el
    estado global de ``random``. Lanza ``ValueError`` si hay claves duplicadas.
    """
    ordenadas = sorted(filas_sesion1, key=_clave_orden)
    claves = [_clave_orden(f) for f in ordenadas]
    if len(set(claves)) != len(claves):
        raise ValueError("La sesión 1 contiene filas duplicadas para (video, lado, frame_idx).")
    k = tamano_submuestra(len(ordenadas), fraccion)
    return random.Random(semilla).sample(ordenadas, k)


def construir_filas_sesion2(seleccion: list[dict[str, str]]) -> list[dict[str, Any]]:
    """
    Filas de la plantilla de la sesión 2, en el orden sorteado.

    ``ordinal_muestra`` y ``frame_idx`` conservan los de la sesión 1 (identifican la
    muestra); ``archivo_png`` es el nombre del PNG copiado en ``sesion2/``, cuyo
    contador coincide con la posición en la secuencia que muestra Tracker. Los valores
    medidos en la sesión 1 **no se copian**.
    """
    return [
        {
            "video": fila["video"],
            "ordinal_muestra": fila["ordinal_muestra"],
            "frame_idx": fila["frame_idx"],
            "lado": fila["lado"],
            "sesion": 2,
            "fecha_medicion": "",
            "tracker_angulo_deg": "",
            "confianza_operador": "",
            "observaciones": "",
            "archivo_png": nombre_fotograma_sesion2(posicion),
        }
        for posicion, fila in enumerate(seleccion)
    ]


def _png_origen(fila: dict[str, str], directorio_fotogramas: Path) -> Path:
    """PNG de la sesión 1 de una fila; si falta ``archivo_png`` se deriva del ordinal."""
    nombre = fila.get("archivo_png") or nombre_fotograma_sesion1(int(fila["ordinal_muestra"]))
    return directorio_fotogramas / nombre


def ejecutar_sorteo(
    ruta_sesion1: Path,
    *,
    directorio_fotogramas: Path | None = None,
    directorio_salida: Path | None = None,
    semilla: int = SEMILLA_POR_DEFECTO,
    fraccion: float = FRACCION_POR_DEFECTO,
    sobrescribir: bool = False,
) -> dict[str, Any]:
    """
    Ejecuta el sorteo completo y escribe plantilla, copias de PNG y orden.

    Por defecto los fotogramas se buscan en ``<dir de la sesión 1>/frames`` y la salida
    va al directorio de la sesión 1. Devuelve un resumen con rutas, ``n``, ``k`` y la
    lista ordenada de pares ``(png_sesion2, png_sesion1)``.
    """
    base = ruta_sesion1.parent
    directorio_fotogramas = directorio_fotogramas or (base / "frames")
    directorio_salida = directorio_salida or base
    ruta_sesion2 = directorio_salida / NOMBRE_PLANTILLA_SESION2
    directorio_sesion2 = directorio_salida / NOMBRE_DIRECTORIO_SESION2

    if plantilla_tiene_mediciones(ruta_sesion2):
        raise RuntimeError(f"La plantilla {ruta_sesion2} ya contiene mediciones; no se vuelve a sortear.")
    if (ruta_sesion2.exists() or directorio_sesion2.exists()) and not sobrescribir:
        raise RuntimeError(
            f"Ya existe un sorteo en {directorio_salida}. Repetir el sorteo invalida la "
            "aleatorización; use --sobrescribir solo si el anterior fue un error documentado."
        )

    filas_sesion1 = leer_plantilla(ruta_sesion1)
    if not filas_sesion1:
        raise ValueError(f"La plantilla {ruta_sesion1} no tiene filas.")
    seleccion = sortear_submuestra(filas_sesion1, semilla=semilla, fraccion=fraccion)

    origenes = [_png_origen(fila, directorio_fotogramas) for fila in seleccion]
    faltan = [str(r) for r in origenes if not r.is_file()]
    if faltan:
        raise FileNotFoundError("No se encuentran estos PNG de la sesión 1: " + ", ".join(faltan))

    if directorio_sesion2.exists():
        shutil.rmtree(directorio_sesion2)
    directorio_sesion2.mkdir(parents=True)

    filas_sesion2 = construir_filas_sesion2(seleccion)
    pares: list[tuple[str, str]] = []
    for fila, origen in zip(filas_sesion2, origenes, strict=True):
        shutil.copy2(origen, directorio_sesion2 / fila["archivo_png"])
        pares.append((fila["archivo_png"], origen.name))
    escribir_plantilla(filas_sesion2, ruta_sesion2)

    ruta_orden = directorio_sesion2 / NOMBRE_ORDEN_SESION2
    lineas = [
        "# Orden de medición de la sesión 2 (Nivel 2, error intra-observador).",
        f"# Plantilla de la sesión 1: {ruta_sesion1.name}",
        f"# Semilla: {semilla}  Fracción: {fraccion}  n sesión 1: {len(filas_sesion1)}  "
        f"k sesión 2: {len(seleccion)}",
        "# png_sesion2 <- png_sesion1",
        *(f"{destino} <- {origen}" for destino, origen in pares),
    ]
    ruta_orden.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    return {
        "plantilla_sesion2": ruta_sesion2,
        "directorio_sesion2": directorio_sesion2,
        "orden": ruta_orden,
        "n": len(filas_sesion1),
        "k": len(seleccion),
        "semilla": semilla,
        "fraccion": fraccion,
        "pares": pares,
    }


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sortea la submuestra aleatorizada de la sesión 2 (intra-observador) del Nivel 2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--sesion1", required=True, help="Plantilla de la sesión 1 (nivel2_tracker_sesion1.csv).")
    parser.add_argument(
        "--directorio-fotogramas",
        default=None,
        help="Directorio con los PNG de la sesión 1 (por defecto, <dir de la sesión 1>/frames).",
    )
    parser.add_argument(
        "--directorio-salida",
        default=None,
        help="Dónde escribir la plantilla de la sesión 2 y la carpeta sesion2/ (por defecto, junto a la sesión 1).",
    )
    parser.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO, help="Semilla del sorteo.")
    parser.add_argument("--fraccion", type=float, default=FRACCION_POR_DEFECTO, help="Fracción a volver a medir.")
    parser.add_argument(
        "--sobrescribir",
        action="store_true",
        help="Reemplazar un sorteo previo sin mediciones (anótelo en la bitácora).",
    )
    return parser


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de línea de comandos. Devuelve el código de salida del proceso."""
    args = _construir_parser().parse_args(argumentos)
    try:
        resumen = ejecutar_sorteo(
            Path(args.sesion1).expanduser().resolve(),
            directorio_fotogramas=Path(args.directorio_fotogramas).expanduser().resolve()
            if args.directorio_fotogramas
            else None,
            directorio_salida=Path(args.directorio_salida).expanduser().resolve() if args.directorio_salida else None,
            semilla=args.semilla,
            fraccion=args.fraccion,
            sobrescribir=args.sobrescribir,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Sorteo de la sesión 2 completado.")
    print(f"  Semilla / fracción  : {resumen['semilla']} / {resumen['fraccion']}")
    print(f"  Filas sesión 1 (n)  : {resumen['n']}")
    print(f"  Sorteadas (k)       : {resumen['k']}")
    print(f"  Plantilla sesión 2  : {resumen['plantilla_sesion2']}")
    print(f"  PNG en orden        : {resumen['directorio_sesion2']} (abrir s2_0000.png en Tracker)")
    print(f"  Correspondencia     : {resumen['orden']}")
    print("")
    print("Recuerde: medir al menos 48 horas después de la sesión 1 y sin consultar sus valores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
