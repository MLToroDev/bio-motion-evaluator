#!/usr/bin/env python3
"""
Genera el diagrama causa-efecto (Ishikawa) del problema como SVG.

Cada causa procede del planteamiento ya escrito en la memoria
(``docs/Formato_trabajo_de_grado.md``: Introducción, Definición del problema,
Justificación, Antecedentes §2.3.3 y Descripción del Negocio) y del texto equivalente de
``generar_informe_tecnico.py``. La tabla de trazabilidad causa → sección está en
``docs/diagramas/README.md``. No se añaden causas que no estén en ese texto.

Uso::

    python3 docs/diagramas/fuentes/ishikawa/generar_ishikawa.py <salida.svg>
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

EFECTO = (
    "La valoración del rango de movimiento de rodilla es costosa, depende de un "
    "profesional y su medición manual es variable: quien entrena suele quedarse "
    "sin una medida objetiva"
)

# (categoría, [causas]) — arriba las tres primeras, abajo las tres últimas.
CATEGORIAS: list[tuple[str, list[str]]] = [
    ("Método", [
        "Protocolos de valoración (p. ej. FMS) que exigen atención presencial",
        "Evaluación funcional por observación manual tradicional",
        "Preparación pre-entrenamiento genérica, sin información biomecánica",
    ]),
    ("Medición", [
        "Error típico de la goniometría manual ≈ 3,4° en flexión de rodilla",
        "Concordancia entre evaluadores limitada (límites de acuerdo > 18° con otros instrumentos)",
        "Sin una magnitud propia y repetible para el usuario",
    ]),
    ("Personas", [
        "Requiere la intervención y la presencia de un profesional",
        "Quien entrena depende del juicio cualitativo de un tercero o de ninguno",
        "Usuarios que cargan peso sin conocer sus restricciones de movilidad",
    ]),
    ("Herramientas y tecnología", [
        "Sin un instrumento accesible para producir la medida",
        "Herramientas manuales dependientes del operador (goniómetro; video con Kinovea)",
    ]),
    ("Entorno", [
        "Gimnasios donde se entrena con alta carga sin valoración funcional previa",
        "La valoración se presta en atención presencial",
    ]),
    ("Costos", [
        "Consulta profesional ≈ 46 000 a más de 100 000 COP en Medellín (referencia de mercado)",
        "La fase de valoración funcional se omite por su costo",
    ]),
]

W, H = 2400, 1320
ESPINA_Y = 660
ESPINA_X0, ESPINA_X1 = 90, 1880
CABEZA = (1900, 480, 440, 360)  # x, y, ancho, alto
RAICES_X = [600, 1140, 1680]  # punto de la espina donde nace cada espina secundaria
DESPLAZAMIENTO_X = 330  # avance horizontal de la espina secundaria hasta su extremo
EXTREMO_Y = {True: 150, False: H - 150}
FUENTE = "Helvetica, Arial, sans-serif"
TINTA = "#1f2328"
ACENTO = "#2563eb"


def _texto(x: float, y: float, lineas: list[str], tam: int, ancla: str = "end", peso: str = "normal",
           color: str = TINTA, interlinea: float = 1.25) -> str:
    out = [f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FUENTE}" font-size="{tam}" '
           f'font-weight="{peso}" fill="{color}" text-anchor="{ancla}">']
    for i, l in enumerate(lineas):
        dy = 0 if i == 0 else tam * interlinea
        out.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{escape(l)}</tspan>')
    out.append("</text>")
    return "".join(out)


def generar() -> str:
    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>',
        '<defs><marker id="punta" markerWidth="14" markerHeight="14" refX="12" refY="7" orient="auto">'
        f'<path d="M0,0 L14,7 L0,14 z" fill="{TINTA}"/></marker></defs>',
        # Espina principal
        f'<line x1="{ESPINA_X0}" y1="{ESPINA_Y}" x2="{CABEZA[0]}" y2="{ESPINA_Y}" stroke="{TINTA}" '
        'stroke-width="6" marker-end="url(#punta)"/>',
    ]
    # Cabeza (efecto)
    cx, cy, cw, ch = CABEZA
    p.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="18" fill="#eff4ff" '
             f'stroke="{ACENTO}" stroke-width="3"/>')
    p.append(_texto(cx + cw / 2, cy + 52, ["Efecto"], 20, "middle", "bold", ACENTO))
    lineas = textwrap.wrap(EFECTO, 30)
    p.append(_texto(cx + cw / 2, cy + 98, lineas, 24, "middle", "bold"))

    for k, (cat, causas) in enumerate(CATEGORIAS):
        arriba = k < 3
        rx = RAICES_X[k % 3]
        ex, ey = rx - DESPLAZAMIENTO_X, EXTREMO_Y[arriba]
        p.append(f'<line x1="{ex}" y1="{ey}" x2="{rx}" y2="{ESPINA_Y}" stroke="{TINTA}" stroke-width="3.5"/>')
        # Etiqueta de categoría en el extremo
        bw, bh = 360, 52
        by = ey - bh - 8 if arriba else ey + 8
        p.append(f'<rect x="{ex - bw / 2}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="#f3f4f6" '
                 f'stroke="{TINTA}" stroke-width="2"/>')
        p.append(_texto(ex, by + bh / 2 + 8, [cat], 24, "middle", "bold"))
        # Causas repartidas a lo largo de la espina secundaria
        n = len(causas)
        for i, causa in enumerate(causas):
            t = (i + 1) / (n + 1)
            # punto sobre la espina secundaria (desde el extremo hacia la raíz)
            px = ex + (rx - ex) * t
            py = ey + (ESPINA_Y - ey) * t
            largo = 250
            p.append(f'<line x1="{px - largo}" y1="{py}" x2="{px}" y2="{py}" stroke="{TINTA}" stroke-width="2"/>')
            p.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{TINTA}"/>')
            lin = textwrap.wrap(causa, 30)
            alto = 19 * 1.25 * (len(lin) - 1)
            if arriba:  # la espina sube hacia la izquierda: el texto va bajo la línea
                p.append(_texto(px - 14, py + 24, lin, 19, "end"))
            else:  # la espina baja hacia la izquierda: el texto va sobre la línea
                p.append(_texto(px - 14, py - 10 - alto, lin, 19, "end"))
    p.append("</svg>")
    return "\n".join(p) + "\n"


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("ishikawa_problema.svg")
    destino.write_text(generar(), encoding="utf-8")
    print(f"escrito {destino}")
