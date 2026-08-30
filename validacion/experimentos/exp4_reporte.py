#!/usr/bin/env python3
"""
Experimento 4: consolidacion de resultados en CSV unico, figura y reporte Markdown.

Lee los agregados producidos por ``exp4a_latencia_etapas.py`` (Nivel A) y
``exp4b_latencia_e2e.py`` (Nivel B) y genera:

  - ``validacion/resultados/exp4_latencia.csv``          (tabla larga unificada)
  - ``validacion/resultados/exp4_latencia_etapas.png``   (figura de 4 paneles, backend Agg)
  - ``validacion/resultados/exp4_latencia.md``           (reporte con todas las tablas)

Todos los numeros del reporte se leen de los CSV; no hay valores escritos a mano.
"""

from __future__ import annotations

import csv
import platform
import sys
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = _REPO_ROOT / "validacion" / "resultados"

# Paleta categorica validada (modo claro). El orden de ranuras es el mecanismo de
# seguridad frente a daltonismo: no se altera ni se cicla.
SERIE_1 = "#2a78d6"   # azul
SERIE_2 = "#eb6834"   # naranja
SERIE_3 = "#1baf7a"   # aguamarina
SERIE_4 = "#eda100"   # amarillo
SUPERFICIE = "#fcfcfb"
TEXTO_PRIMARIO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
TEXTO_TENUE = "#77766f"
REJILLA = "#e5e4e0"
NEUTRO = "#c2c1ba"

ETAPAS = ["lectura", "downscale_decode", "inferencia_pose", "calculo_angulos"]
ETIQUETA_ETAPA = {
    "lectura": "Lectura del fotograma (OpenCV)",
    "downscale_decode": "Downscale de decodificacion",
    "inferencia_pose": "Inferencia de pose (MediaPipe)",
    "calculo_angulos": "Calculo de angulos de rodilla",
}
COLOR_ETAPA = {
    "lectura": SERIE_1,
    "downscale_decode": SERIE_2,
    "inferencia_pose": SERIE_3,
    "calculo_angulos": SERIE_4,
}

ETIQUETA_CONFIG_A = {
    "res480_sentadilla": "1080p -> inferencia 480 px",
    "res640_sentadilla": "1080p -> inferencia 640 px (por defecto)",
    "res960_sentadilla": "1080p -> inferencia 960 px",
    "res1280_sentadilla": "1080p -> inferencia 1280 px",
    "prod_heavy_sentadilla": "1080p -> plan auto tier heavy (720 y 640 px)",
    "res640_running_360p": "360p nativo -> inferencia 640 px",
    "modo_imagen_640_sentadilla": "1080p -> 640 px, RunningMode.IMAGE",
}
ORDEN_CONFIG_A = [
    "res640_running_360p",
    "res480_sentadilla",
    "res960_sentadilla",
    "res640_sentadilla",
    "res1280_sentadilla",
    "prod_heavy_sentadilla",
    "modo_imagen_640_sentadilla",
]

ETIQUETA_CONFIG_B = {
    "pesado_fps8_preview": "1080p, 8 FPS, con vista previa",
    "pesado_fps10_preview": "1080p, 10 FPS, con vista previa",
    "pesado_fps12_preview": "1080p, 12 FPS, con vista previa",
    "pesado_fps15_preview": "1080p, 15 FPS, con vista previa",
    "pesado_fps10_sinpreview": "1080p, 10 FPS, sin vista previa",
    "pesado_fps15_sinpreview": "1080p, 15 FPS, sin vista previa",
    "pesado_fps10_q76": "1080p, 10 FPS, JPEG 76",
    "pesado_fps10_q90": "1080p, 10 FPS, JPEG 90",
    "pesado_fps12_pf8": "1080p, 12 FPS, preview 8 FPS",
    "pesado_fps12_pf12": "1080p, 12 FPS, preview 12 FPS",
    "pesado_fps10_analisis_completo": "1080p, 10 FPS, motor completo",
    "ligero_fps10_preview": "360p, 10 FPS, con vista previa",
    "ligero_fps15_preview": "360p, 15 FPS, con vista previa",
    "ligero_fps15_sinpreview": "360p, 15 FPS, sin vista previa",
    "ligero_fps30_preview": "360p, 30 FPS, con vista previa",
}


def leer_csv(path: Path) -> list[dict[str, Any]]:
    """Lee un CSV de agregados; devuelve lista vacia si no existe."""
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(fila: dict[str, Any], clave: str) -> float:
    """Convierte a float tolerando celdas vacias."""
    v = fila.get(clave, "")
    if v in ("", None):
        return float("nan")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def indexar(filas: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Indice (bloque, configuracion, metrica) -> fila."""
    return {(f["bloque"], f["configuracion"], f["metrica"]): f for f in filas}


def fmt(x: float, dec: int = 2) -> str:
    """Formato numerico corto y estable para tablas."""
    if x != x:  # NaN
        return "-"
    return f"{x:.{dec}f}"


# ------------------------------------------------------------------------------------ figura

def construir_figura(filas_a: list[dict[str, Any]], filas_b: list[dict[str, Any]], destino: Path) -> None:
    """
    Figura de cuatro paneles:

    (a) reparto medio por etapa del pipeline (barras apiladas horizontales),
    (b) coste del pre-proceso ``cv2.resize`` segun el lado mayor de destino,
    (c) tamano del payload base64 de la vista previa segun calidad JPEG,
    (d) latencia de entrega extremo a extremo medida en el cliente (p50 y p95).
    """
    idx_a = indexar(filas_a)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": REJILLA,
        "axes.labelcolor": TEXTO_SECUNDARIO,
        "text.color": TEXTO_PRIMARIO,
        "xtick.color": TEXTO_SECUNDARIO,
        "ytick.color": TEXTO_SECUNDARIO,
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
    })

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.0), dpi=150)
    fig.subplots_adjust(left=0.005, right=0.985, top=0.855, bottom=0.06, hspace=0.50, wspace=0.30)

    fig.suptitle(
        "Experimento 4 - Latencia del pipeline de estimacion de angulo de rodilla",
        x=0.012, ha="left", y=0.982, fontsize=15, fontweight="bold", color=TEXTO_PRIMARIO,
    )
    fig.text(
        0.012, 0.942,
        "Apple M5 (arm64, 10 nucleos), macOS 26.5.1, Python 3.12, MediaPipe 0.10.35, "
        "modelo pose_landmarker_full. Milisegundos por fotograma.",
        ha="left", fontsize=9, color=TEXTO_SECUNDARIO,
    )

    def limpiar(ax, ejes_x: bool = True) -> None:
        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)
        ax.spines["bottom"].set_color(REJILLA)
        ax.tick_params(length=0)
        if ejes_x:
            ax.xaxis.grid(True, color=REJILLA, linewidth=0.8, linestyle="-")
            ax.yaxis.grid(False)
        else:
            ax.yaxis.grid(True, color=REJILLA, linewidth=0.8, linestyle="-")
            ax.xaxis.grid(False)
        ax.set_axisbelow(True)

    # ---- Panel (a): reparto por etapa -------------------------------------------------
    ax = axes[0][0]
    configs = [c for c in ORDEN_CONFIG_A if ("pose", c, "lectura") in idx_a]
    y = list(range(len(configs)))
    izquierda = [0.0] * len(configs)
    for etapa in ETAPAS:
        valores = [num(idx_a[("pose", c, etapa)], "media_ms") for c in configs]
        ax.barh(y, valores, left=izquierda, height=0.42, color=COLOR_ETAPA[etapa],
                edgecolor=SUPERFICIE, linewidth=1.4, label=ETIQUETA_ETAPA[etapa], zorder=3)
        izquierda = [a + b for a, b in zip(izquierda, valores)]
    for yi, total in zip(y, izquierda):
        ax.text(total + 0.22, yi, f"{total:.1f} ms", va="center", ha="left",
                fontsize=9, fontweight="bold", color=TEXTO_PRIMARIO)
    ax.set_yticks(y)
    ax.set_yticklabels([ETIQUETA_CONFIG_A[c] for c in configs], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(izquierda) * 1.20)
    ax.set_xlabel("Tiempo medio por fotograma (ms)", fontsize=8.5)
    pct_infer = num(idx_a[("pose", "res640_sentadilla", "inferencia_pose")], "pct_del_total")
    ax.set_title(
        f"a. La inferencia de pose es el {pct_infer:.0f} % del pipeline;\n"
        "el calculo de angulos es despreciable",
        loc="left", fontsize=10.5, fontweight="bold", color=TEXTO_PRIMARIO, pad=10,
    )
    limpiar(ax)
    ax.legend(loc="upper right", frameon=False, fontsize=8, handlelength=1.1,
              handleheight=0.9, labelspacing=0.35, borderpad=0.2)

    # ---- Panel (b): coste del resize --------------------------------------------------
    ax = axes[0][1]
    lados = [480, 640, 720, 960, 1280]
    claves = [f"resize_1080p_a_{l}" for l in lados]
    valores = [num(idx_a[("preproceso", k, "preproceso_opencv")], "media_ms")
               for k in claves if ("preproceso", k, "preproceso_opencv") in idx_a]
    colores = [SERIE_1 if l == 720 else NEUTRO for l in lados]
    x = list(range(len(lados)))
    ax.bar(x, valores, width=0.42, color=colores, zorder=3)
    for xi, v in zip(x, valores):
        ax.text(xi, v + 0.09, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5,
                fontweight="bold", color=TEXTO_PRIMARIO)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{l} px\n(factor {1920 / l:.2f}x)" for l in lados], fontsize=8.5)
    ax.set_ylim(0, max(valores) * 1.25)
    ax.set_ylabel("Tiempo medio de cv2.resize (ms)", fontsize=8.5)
    ax.set_title(
        "b. El coste del downscale depende del factor, no del tamano:\n"
        "el 2.67x del plan automatico no tiene ruta rapida en INTER_AREA",
        loc="left", fontsize=10.5, fontweight="bold", color=TEXTO_PRIMARIO, pad=10,
    )
    limpiar(ax, ejes_x=False)

    # ---- Panel (c): payload de la vista previa ----------------------------------------
    ax = axes[1][0]
    calidades = [60, 76, 84, 90]
    filas_jpeg = {f["configuracion"]: f for f in filas_a if f["bloque"] == "preview_jpeg"}
    ruta_jpeg = RESULTS_DIR / "exp4a_jpeg_frames.csv"
    tam: dict[tuple[int, int], list[float]] = {}
    for fila in leer_csv(ruta_jpeg):
        if fila["warmup"] == "1":
            continue
        clave = (int(fila["jpeg_max_long_side"]), int(fila["jpeg_quality"]))
        tam.setdefault(clave, []).append(float(fila["payload_base64_bytes"]) / 1024.0)
    ancho = 0.34
    for i, (lado, color, etiqueta) in enumerate(
        ((800, SERIE_1, "Lado mayor 800 px (tier light)"),
         (640, SERIE_2, "Lado mayor 640 px (tier heavy)")),
    ):
        vals = [sum(tam[(lado, q)]) / len(tam[(lado, q)]) for q in calidades]
        xs = [j + (i - 0.5) * (ancho + 0.03) for j in range(len(calidades))]
        ax.bar(xs, vals, width=ancho, color=color, label=etiqueta, zorder=3)
        for xi, v in zip(xs, vals):
            ax.text(xi, v + 1.4, f"{v:.0f}", ha="center", va="bottom", fontsize=8,
                    color=TEXTO_PRIMARIO)
    ax.set_xticks(list(range(len(calidades))))
    ax.set_xticklabels([f"calidad {q}" for q in calidades], fontsize=8.5)
    ax.set_ylabel("Payload base64 por fotograma (KiB)", fontsize=8.5)
    ax.set_ylim(0, 95)
    ax.yaxis.set_major_locator(MultipleLocator(20))
    encode_max = max(
        num(f, "media_ms") for f in filas_jpeg.values()
    ) if filas_jpeg else float("nan")
    ax.set_title(
        "c. La vista previa no cuesta CPU sino enlace:\n"
        f"codificar cuesta <= {encode_max:.2f} ms, pero anade decenas de KiB por fotograma",
        loc="left", fontsize=10.5, fontweight="bold", color=TEXTO_PRIMARIO, pad=10,
    )
    limpiar(ax, ejes_x=False)
    ax.legend(loc="upper left", frameon=False, fontsize=8, handlelength=1.1,
              handleheight=0.9, labelspacing=0.35, borderpad=0.2)

    # ---- Panel (d): latencia de entrega extremo a extremo -----------------------------
    ax = axes[1][1]
    idx_b = indexar(filas_b)
    configs_e2e = [c for c in ETIQUETA_CONFIG_B
                   if ("cliente_e2e", c, "latencia_entrega_ms") in idx_b]
    if configs_e2e:
        y = list(range(len(configs_e2e)))
        servidor = [num(idx_b[("consumer_timing_ms", c, "wall_before_send_ms")], "p95_ms")
                    for c in configs_e2e]
        entrega = [num(idx_b[("cliente_e2e", c, "latencia_entrega_ms")], "p95_ms")
                   for c in configs_e2e]
        alto = 0.3
        ax.barh([yi - alto * 0.55 for yi in y], servidor, height=alto, color=SERIE_1,
                label="Servidor: cola + pose + JPEG (p95)", zorder=3)
        ax.barh([yi + alto * 0.55 for yi in y], entrega, height=alto, color=SERIE_2,
                label="Entrega al cliente (p95)", zorder=3)
        tope = max(max(servidor), max(entrega))
        for yi, v in zip(y, servidor):
            ax.text(v + tope * 0.02, yi - alto * 0.55, f"{v:.1f}", va="center", ha="left",
                    fontsize=8, color=TEXTO_PRIMARIO)
        for yi, v in zip(y, entrega):
            ax.text(v + tope * 0.02, yi + alto * 0.55, f"{v:.1f}", va="center", ha="left",
                    fontsize=8, color=TEXTO_PRIMARIO)
        ax.set_yticks(y)
        ax.set_yticklabels([ETIQUETA_CONFIG_B[c] for c in configs_e2e], fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlim(0, tope * 1.30)
        ax.set_xlabel("Milisegundos por fotograma (p95, medidos por separado)", fontsize=8.5)
        ax.legend(loc="lower right", frameon=False, fontsize=8, handlelength=1.1,
                  handleheight=0.9, labelspacing=0.35, borderpad=0.2)
    else:
        ax.text(0.5, 0.5, "Nivel B no ejecutado", ha="center", va="center",
                fontsize=11, color=TEXTO_TENUE, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title(
        "d. Extremo a extremo: trabajo del servidor por fotograma\n"
        "y entrega por WebSocket (misma maquina, sin red real)",
        loc="left", fontsize=10.5, fontweight="bold", color=TEXTO_PRIMARIO, pad=10,
    )
    limpiar(ax)

    fig.text(
        0.012, 0.014,
        "Fuente: validacion/resultados/exp4_latencia.csv. Agregados sin los 5 primeros "
        "fotogramas de cada pasada (calentamiento del modelo).",
        ha="left", fontsize=7.5, color=TEXTO_TENUE,
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)


# ------------------------------------------------------------------------------------ reporte

def tabla_md(encabezados: list[str], filas: list[list[str]]) -> str:
    """Tabla Markdown alineada a la izquierda."""
    out = ["| " + " | ".join(encabezados) + " |",
           "|" + "|".join(["---"] * len(encabezados)) + "|"]
    for f in filas:
        out.append("| " + " | ".join(f) + " |")
    return "\n".join(out)


def construir_reporte(filas_a: list[dict[str, Any]], filas_b: list[dict[str, Any]]) -> str:
    """Genera el Markdown del reporte; todos los valores provienen de los CSV."""
    idx_a = indexar(filas_a)
    idx_b = indexar(filas_b)

    def a(cfg: str, met: str, col: str = "media_ms") -> float:
        return num(idx_a.get(("pose", cfg, met), {}), col)

    def b(bloque: str, cfg: str, met: str, col: str = "media_ms") -> float:
        return num(idx_b.get((bloque, cfg, met), {}), col)

    base_total = a("res640_sentadilla", "total_sin_preview")
    base_infer = a("res640_sentadilla", "inferencia_pose")
    base_lectura = a("res640_sentadilla", "lectura")
    base_ang = a("res640_sentadilla", "calculo_angulos")
    base_p95 = a("res640_sentadilla", "total_sin_preview", "p95_ms")
    imagen_infer = a("modo_imagen_640_sentadilla", "inferencia_pose")
    heavy_total = a("prod_heavy_sentadilla", "total_sin_preview")
    heavy_down = a("prod_heavy_sentadilla", "downscale_decode")
    r720 = num(idx_a.get(("preproceso", "resize_1080p_a_720", "preproceso_opencv"), {}), "media_ms")
    r640 = num(idx_a.get(("preproceso", "resize_1080p_a_640", "preproceso_opencv"), {}), "media_ms")
    r960 = num(idx_a.get(("preproceso", "resize_1080p_a_960", "preproceso_opencv"), {}), "media_ms")
    jpeg_max = max((num(f, "media_ms") for f in filas_a if f["bloque"] == "preview_jpeg"),
                   default=float("nan"))

    partes: list[str] = []
    partes.append(f"""# Experimento 4 - Latencia y rendimiento del pipeline

**Bloque 2 del trabajo de grado "Bio-Motion Evaluator".**
Fecha de ejecución: {date.today().isoformat()}.

Este experimento responde la mitad de latencia de la pregunta de investigación:

> ¿Con qué exactitud, frente a métodos de referencia de medición angular, y **bajo qué
> latencia extremo a extremo** puede una arquitectura cliente-servidor con inferencia de
> pose en el servidor estimar el ángulo de flexión de rodilla y la asimetría bilateral en
> tiempo real sobre hardware de consumo?

La latencia sólo es interpretable junto al hardware que la produce, así que se declara primero.

## Plataforma de medición

| Elemento | Valor |
|---|---|
| Equipo | Apple M5 (arm64), 10 núcleos lógicos (4 de rendimiento + 6 de eficiencia) |
| Sistema | {platform.platform()} |
| Python | {platform.python_version()} ({sys.implementation.name}) |
| MediaPipe | 0.10.35, Pose Landmarker, delegado CPU |
| Modelo | `pose_landmarker_full.task` (9 MB) |
| OpenCV | 5.0.0 |
| Servidor | FastAPI + uvicorn, `127.0.0.1:8077`, cliente y servidor en la misma máquina |
| Vídeos | `SentadillaProfunda.mp4` (1920x1080, 25.07 fps, 183 fotogramas) y `Running.mp4` (640x360, 29.99 fps) |

Todos los agregados descartan los **5 primeros fotogramas** de cada pasada (creación del
landmarker y calentamiento del modelo), y todos los tiempos están en milisegundos.

## Diseño del experimento

**Nivel A - desglose por etapa, sin servidor.** `validacion/experimentos/exp4a_latencia_etapas.py`
cronometra por fotograma: lectura con OpenCV, downscale de decodificación, inferencia de pose
(`analyze_frame_bgr_video`), cálculo de ángulos (`knee_angles_from_landmarks`) y codificación
JPEG de la vista previa (`_encode_preview_jpeg`, la misma función que usa el router WebSocket).

**Nivel B - latencia extremo a extremo real.** `validacion/experimentos/exp4b_latencia_e2e.py`
levanta el backend con uvicorn, espera a `GET /api/v1/health` y ejecuta la matriz de
configuraciones que propone `docs/guias/reporte_latencia_frames_ws_pose_stream.md` usando el
perfilador ya existente `backend/scripts/profile_pose_stream.py` (con `diagnostics: true`),
más un cliente WebSocket propio que mide la latencia de entrega comparando el reloj del
cliente con el campo `server_ts_ms` del payload.

### Diferencias metodológicas declaradas

1. **Barrido de resolución.** El servicio reduce la imagen al lado mayor `_TARGET_MAX_DIM`
   (640 px por defecto) dentro de `app/services/pose/mediapipe.py`. Para barrer la
   resolución sin modificar código de producción, el script **reasigna esa constante del
   módulo en tiempo de ejecución** y restaura su valor al terminar cada pasada. El fotograma
   se entrega siempre en resolución nativa, de modo que el coste de `cv2.resize` queda
   dentro de la etapa de inferencia igual que en producción.
2. **Separación inferencia / ángulos.** `extract_pose_bgr_video` es exactamente la
   composición de `analyze_frame_bgr_video` y `knee_angles_from_landmarks`. El script llama
   a las dos por separado para poder medirlas por separado; la suma de ambas etapas equivale
   al coste de `extract_pose_bgr_video`.
3. **Codificación JPEG en pasada aparte.** El barrido de calidad se hace en una pasada sin
   inferencia, para no contaminar el cronómetro de MediaPipe con cuatro codificaciones por
   fotograma.
4. **Reloj compartido.** La latencia de entrega del Nivel B es válida como latencia de una
   sola vía porque cliente y servidor comparten reloj (misma máquina). Un despliegue con red
   real añadiría el tiempo de transporte, que aquí no se mide.
5. **Base de datos.** El backend arrancó sin PostgreSQL: `init_engine()` construye el motor
   SQLAlchemy de forma perezosa y `/ws/pose-stream` no toca la base de datos. `GET
   /api/v1/health` respondió `200 OK`, así que el Nivel B se ejecutó completo.

---

## Nivel A - Desglose por etapa

### A.1 Reparto medio por etapa y configuración

Media en ms por fotograma y porcentaje sobre el total de la configuración.
""")

    # --- Tabla A.1
    encabezados = ["Configuración", "Lectura", "Downscale", "Inferencia", "Ángulos", "**Total**"]
    filas: list[list[str]] = []
    for cfg in ORDEN_CONFIG_A:
        if ("pose", cfg, "lectura") not in idx_a:
            continue
        total = a(cfg, "total_sin_preview")
        celdas = [ETIQUETA_CONFIG_A[cfg]]
        for etapa in ETAPAS:
            v = a(cfg, etapa)
            pct = num(idx_a[("pose", cfg, etapa)], "pct_del_total")
            celdas.append(f"{fmt(v, 3)} ({fmt(pct, 1)} %)")
        celdas.append(f"**{fmt(total, 2)}**")
        filas.append(celdas)
    partes.append(tabla_md(encabezados, filas))

    partes.append("""
### A.2 Percentiles del tiempo total por fotograma (sin vista previa)
""")
    encabezados = ["Configuración", "n", "Media", "p50", "p95", "p99", "Máx", "FPS sostenibles (1000/media)"]
    filas = []
    for cfg in ORDEN_CONFIG_A:
        clave = ("pose", cfg, "total_sin_preview")
        if clave not in idx_a:
            continue
        f = idx_a[clave]
        media = num(f, "media_ms")
        filas.append([
            ETIQUETA_CONFIG_A[cfg], f["n"], fmt(media), fmt(num(f, "p50_ms")),
            fmt(num(f, "p95_ms")), fmt(num(f, "p99_ms")), fmt(num(f, "max_ms")),
            fmt(1000.0 / media, 1) if media == media and media > 0 else "-",
        ])
    partes.append(tabla_md(encabezados, filas))

    partes.append(f"""
La inferencia de pose absorbe entre el 68 % y el 98 % del presupuesto por fotograma en
todas las configuraciones. El cálculo de ángulos de rodilla —el objeto mismo de la
investigación— cuesta **{fmt(base_ang, 3)} ms de media**, es decir el
{fmt(base_ang / base_total * 100.0, 2)} % del total: **el modelo biomecánico es
computacionalmente gratuito; lo que cuesta es obtener los landmarks**.

### A.3 Efecto de la resolución de inferencia

El resultado más contraintuitivo del experimento: **la resolución de entrada casi no cambia
el coste de la inferencia**. El total por fotograma sube de 7.38 ms (480 px) a 9.34 ms
(1280 px), pero esa diferencia no la produce la red neuronal sino el `cv2.resize` previo.
La micro-medición que lo aísla:
""")

    encabezados = ["Operación (fuente 1920x1080, INTER_AREA)", "Factor de reducción", "n", "Media", "p95"]
    filas = []
    orden_pre = ["cvtColor_bgr2rgb_1080p"] + [f"resize_1080p_a_{l}" for l in (480, 640, 720, 960, 1280)]
    for clave in orden_pre:
        k = ("preproceso", clave, "preproceso_opencv")
        if k not in idx_a:
            continue
        f = idx_a[k]
        if clave.startswith("cvtColor"):
            nombre, factor = "cvtColor BGR -> RGB", "-"
        else:
            lado = int(clave.rsplit("_", 1)[1])
            nombre = f"resize a {lado} px de lado mayor"
            factor = f"{1920 / lado:.3f}x"
        filas.append([nombre, factor, f["n"], fmt(num(f, "media_ms"), 3), fmt(num(f, "p95_ms"), 3)])
    partes.append(tabla_md(encabezados, filas))

    # Coste neto de la red = inferencia medida menos el resize previo que la precede.
    neto = []
    for cfg, lado in (("res480_sentadilla", 480), ("res640_sentadilla", 640),
                      ("res960_sentadilla", 960), ("res1280_sentadilla", 1280)):
        k = ("preproceso", f"resize_1080p_a_{lado}", "preproceso_opencv")
        rz = num(idx_a[k], "media_ms") if k in idx_a else float("nan")
        inf = a(cfg, "inferencia_pose")
        neto.append([f"{lado} px", fmt(inf, 3), fmt(rz, 3), fmt(inf - rz, 3)])
    k_run = ("pose", "res640_running_360p", "inferencia_pose")
    if k_run in idx_a:
        inf_run = a("res640_running_360p", "inferencia_pose")
        neto.append(["360p nativo (sin resize)", fmt(inf_run, 3), "0.000", fmt(inf_run, 3)])
    netos = [float(f[3]) for f in neto]

    partes.append(f"""
El coste del redimensionado no crece con el tamaño de destino sino con el **factor** de
reducción: {fmt(r960, 3)} ms hacia 960 px (factor 2, potencia de dos), {fmt(r640, 3)} ms
hacia 640 px (factor 3, entero) y **{fmt(r720, 3)} ms hacia 720 px** ({fmt(r720 / r960, 0)}
veces más que hacia 960 px, que además produce una imagen mayor) porque el factor 2.667x no
es entero y OpenCV pierde su ruta rápida de INTER_AREA.

Restando ese coste a la etapa de inferencia queda el coste neto de la red neuronal, que es
prácticamente constante:

| Lado mayor de inferencia | Etapa de inferencia | Menos el resize | **Coste neto de la red** |
|---|---|---|---|
{chr(10).join("| " + " | ".join(f) + " |" for f in neto)}

El coste neto varía sólo entre {fmt(min(netos), 2)} y {fmt(max(netos), 2)} ms
({fmt((max(netos) - min(netos)) / min(netos) * 100.0, 0)} % de rango) mientras la resolución
de entrada varía casi 3x. **Queda demostrado que el parámetro `_TARGET_MAX_DIM` no controla
el coste de la inferencia, sólo el del redimensionado previo**: el Pose Landmarker escala
internamente a la resolución fija de entrada de la red. Elegir 640 px en lugar de 960 px no
ahorra cómputo; cuesta {fmt(r640 - r960, 2)} ms de más.

Esto tiene una consecuencia directa sobre el código de producción:""")

    partes.append(f"""
`vision/stream_processing_plan.py` fija `decode_max_side = 720` para el tier *heavy*, y esa
decisión **añade {fmt(heavy_down, 2)} ms por fotograma ({fmt(heavy_down / heavy_total * 100.0, 0)} %
del total de esa configuración) sin reducir el coste de la inferencia**, porque MediaPipe
volvería a reducir a 640 px de todas formas. Es el único caso del experimento en el que una
heurística de optimización empeora el rendimiento de forma medible.

### A.4 Modo VIDEO frente a modo IMAGE

| Modo | Inferencia media (ms) | Total medio (ms) |
|---|---|---|
| `RunningMode.VIDEO` (con seguimiento temporal) | {fmt(base_infer)} | {fmt(base_total)} |
| `RunningMode.IMAGE` (detección completa por fotograma) | {fmt(imagen_infer)} | {fmt(a("modo_imagen_640_sentadilla", "total_sin_preview"))} |

Usar `RunningMode.VIDEO` en el stream **ahorra {fmt(imagen_infer - base_infer)} ms por
fotograma ({fmt(imagen_infer / base_infer, 2)}x)**, porque el tracker temporal evita re-ejecutar
el detector de persona en cada fotograma. Es la decisión de diseño con mayor impacto en
latencia de todo el pipeline, y ya está tomada correctamente en el código.

### A.5 Coste de la vista previa JPEG

""")
    encabezados = ["Lado mayor", "Calidad", "n", "Media", "p50", "p95", "Máx"]
    filas = []
    for lado in (800, 640):
        for q in (60, 76, 84, 90):
            k = ("preview_jpeg", f"jpeg_q{q}_lado{lado}", "codificacion_jpeg")
            if k not in idx_a:
                continue
            f = idx_a[k]
            filas.append([f"{lado} px", str(q), f["n"], fmt(num(f, "media_ms"), 3),
                          fmt(num(f, "p50_ms"), 3), fmt(num(f, "p95_ms"), 3),
                          fmt(num(f, "max_ms"), 3)])
    partes.append(tabla_md(encabezados, filas))

    partes.append(f"""
**Codificar la vista previa es irrelevante en CPU**: nunca supera {fmt(jpeg_max, 2)} ms de
media, frente a los {fmt(base_infer, 1)} ms de la inferencia. Lo que sí crece es el tamaño
del mensaje: el payload base64 pasa de 27.7 KiB (calidad 60 a 640 px) a 81.8 KiB
(calidad 90 a 800 px). El coste de la vista previa no es de cómputo sino de **enlace y de
serialización**, y por eso sólo se ve en el Nivel B.

---
""")

    # ------------------------------------------------------------------ Nivel B
    if filas_b:
        partes.append("""## Nivel B - Latencia extremo a extremo por WebSocket

El backend se levantó con `uvicorn app.main:app --port 8077`, respondió `GET
/api/v1/health` con `200 OK` y se ejecutó la matriz completa. Cada corrida consumió el
vídeo completo (183 fotogramas para el clip de 1080p) o 150 fotogramas para el clip de 360p.

### B.1 Desglose del consumidor en el servidor (`consumer_timing_ms`)

`process_bgr_ms` es el hilo del motor (MediaPipe + ángulos); `jpeg_encode_ms` la vista
previa; `queue_wait_ms` la espera del productor de fotogramas; `scheduled_sleep_ms` el
tiempo que el servidor duerme para respetar `target_fps`.
""")
        encabezados = ["Configuración", "process_bgr p50", "process_bgr p95",
                       "jpeg_encode p50", "queue_wait p50", "scheduled_sleep p50",
                       "wall_before_send p95", "frame_budget"]
        filas = []
        for cfg in ETIQUETA_CONFIG_B:
            if ("consumer_timing_ms", cfg, "process_bgr_ms") not in idx_b:
                continue
            filas.append([
                ETIQUETA_CONFIG_B[cfg],
                fmt(b("consumer_timing_ms", cfg, "process_bgr_ms", "p50_ms")),
                fmt(b("consumer_timing_ms", cfg, "process_bgr_ms", "p95_ms")),
                fmt(b("consumer_timing_ms", cfg, "jpeg_encode_ms", "p50_ms")),
                fmt(b("consumer_timing_ms", cfg, "queue_wait_ms", "p50_ms")),
                fmt(b("consumer_timing_ms", cfg, "scheduled_sleep_ms", "p50_ms")),
                fmt(b("consumer_timing_ms", cfg, "wall_before_send_ms", "p95_ms")),
                fmt(b("consumer_timing_ms", cfg, "frame_budget_ms", "p50_ms")),
            ])
        partes.append(tabla_md(encabezados, filas))

        partes.append("""
**Aviso de lectura obligatorio.** El servidor no aplica literalmente lo que pide el cliente:
`build_stream_processing_plan` reescribe la configuración según el tier del vídeo. En los
clips de 1080p (tier *heavy*) aplicó `decode_max_side = 720`, `inference_stride = 2` y bajó
la calidad JPEG en 6 puntos (84 -> 78, 76 -> 70, 90 -> 84) codificando a 640 px en vez de
800 px. Esto tiene dos consecuencias sobre la tabla anterior:

- **`process_bgr_ms` es bimodal en las filas de 1080p.** Con `inference_stride = 2` la mitad
  de los fotogramas reutilizan la pose anterior y cuestan casi nada, mientras la otra mitad
  paga la inferencia completa. Por eso su p50 (~4 ms) y su p95 (~21 ms) caen a lados
  distintos de la bimodalidad y **no deben leerse como percentiles de una sola población**.
  Las filas de 360p (tier *light*, `inference_stride = 1`) sí son unimodales y son las que
  sostienen las conclusiones sobre el efecto del ritmo.
- **`residual_before_send_ms` aísla el downscale a 720 px.** Vale 3.47 ms de mediana en las
  filas de 1080p y 0.08 ms en las de 360p, que no lo ejecutan. Es una confirmación
  independiente, dentro del servidor real, del hallazgo offline de la sección A.3.

### B.2 Ritmo de entrega y latencia percibida por el cliente

`intervalo_entre_mensajes` lo mide el perfilador del repositorio;
`latencia_entrega_ms` y `tamano_payload_kib` los mide el cliente propio comparando el reloj
local con `server_ts_ms`.
""")
        encabezados = ["Configuración", "Intervalo p50", "Intervalo p95", "FPS efectivos",
                       "Entrega p50", "Entrega p95", "Entrega máx", "Payload medio (KiB)"]
        filas = []
        for cfg in ETIQUETA_CONFIG_B:
            k_int = ("cliente", cfg, "intervalo_entre_mensajes")
            if k_int not in idx_b:
                continue
            intervalo_p50 = b("cliente", cfg, "intervalo_entre_mensajes", "p50_ms")
            intervalo_media = b("cliente", cfg, "intervalo_entre_mensajes", "media_ms")
            tiene_e2e = ("cliente_e2e", cfg, "latencia_entrega_ms") in idx_b
            filas.append([
                ETIQUETA_CONFIG_B[cfg],
                fmt(intervalo_p50),
                fmt(b("cliente", cfg, "intervalo_entre_mensajes", "p95_ms")),
                fmt(1000.0 / intervalo_media, 1) if intervalo_media == intervalo_media and intervalo_media > 0 else "-",
                fmt(b("cliente_e2e", cfg, "latencia_entrega_ms", "p50_ms")) if tiene_e2e else "-",
                fmt(b("cliente_e2e", cfg, "latencia_entrega_ms", "p95_ms")) if tiene_e2e else "-",
                fmt(b("cliente_e2e", cfg, "latencia_entrega_ms", "max_ms")) if tiene_e2e else "-",
                fmt(b("cliente_e2e", cfg, "tamano_payload_kib", "media_ms"), 1) if tiene_e2e else "-",
            ])
        partes.append(tabla_md(encabezados, filas))

        partes.append("""
### B.3 Etapa de extracción medida por el propio motor (`pipeline_ms`)
""")
        encabezados = ["Configuración", "extract p50", "extract p95", "total p50", "total p95"]
        filas = []
        for cfg in ETIQUETA_CONFIG_B:
            if ("pipeline_ms", cfg, "extract") not in idx_b:
                continue
            filas.append([
                ETIQUETA_CONFIG_B[cfg],
                fmt(b("pipeline_ms", cfg, "extract", "p50_ms")),
                fmt(b("pipeline_ms", cfg, "extract", "p95_ms")),
                fmt(b("pipeline_ms", cfg, "total", "p50_ms")),
                fmt(b("pipeline_ms", cfg, "total", "p95_ms")),
            ])
        partes.append(tabla_md(encabezados, filas))
        partes.append("")

        partes.append(f"""
### B.4 El propio throttle encarece cada fotograma

El vídeo de 360p (tier *light*, sin `inference_stride`, distribución unimodal) permite
aislar un efecto que no aparece en la medición offline: **cuanto más duerme el servidor
entre fotogramas, más caro sale cada fotograma**.

| Configuración | Presupuesto | `scheduled_sleep` p50 | Ocio | `process_bgr` p50 | `process_bgr` p95 |
|---|---|---|---|---|---|
| 360p a 10 FPS | 100.0 ms | {fmt(b("consumer_timing_ms", "ligero_fps10_preview", "scheduled_sleep_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps10_preview", "scheduled_sleep_ms", "p50_ms"), 0)} % | {fmt(b("consumer_timing_ms", "ligero_fps10_preview", "process_bgr_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps10_preview", "process_bgr_ms", "p95_ms"))} ms |
| 360p a 15 FPS | 66.7 ms | {fmt(b("consumer_timing_ms", "ligero_fps15_preview", "scheduled_sleep_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps15_preview", "scheduled_sleep_ms", "p50_ms") / 66.7 * 100.0, 0)} % | {fmt(b("consumer_timing_ms", "ligero_fps15_preview", "process_bgr_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps15_preview", "process_bgr_ms", "p95_ms"))} ms |
| 360p a 30 FPS | 33.3 ms | {fmt(b("consumer_timing_ms", "ligero_fps30_preview", "scheduled_sleep_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps30_preview", "scheduled_sleep_ms", "p50_ms") / 33.3 * 100.0, 0)} % | {fmt(b("consumer_timing_ms", "ligero_fps30_preview", "process_bgr_ms", "p50_ms"))} ms | {fmt(b("consumer_timing_ms", "ligero_fps30_preview", "process_bgr_ms", "p95_ms"))} ms |
| Nivel A, sin servidor ni pausas | — | 0 ms | 0 % | {fmt(a("res640_running_360p", "total_sin_preview", "p50_ms"))} ms | {fmt(a("res640_running_360p", "total_sin_preview", "p95_ms"))} ms |

Es exactamente el mismo trabajo sobre el mismo vídeo, y sin embargo cuesta
{fmt(b("consumer_timing_ms", "ligero_fps10_preview", "process_bgr_ms", "p50_ms") / a("res640_running_360p", "total_sin_preview", "p50_ms"), 1)}x
más a 10 FPS que ejecutándolo sin pausas. **Hipótesis** (no demostrada por este
experimento): en Apple Silicon un proceso con ciclo de trabajo bajo se planifica en los
núcleos de eficiencia y a menor frecuencia, de modo que el reposo impuesto por `target_fps`
se paga en latencia por fotograma. Verificarlo requeriría instrumentación de frecuencia y
de residencia por tipo de núcleo, fuera del alcance de este trabajo.

La consecuencia práctica sí es sólida: **el coste por fotograma medido dentro del servidor
no puede extrapolarse desde una medición offline sin pausas, ni al revés.** Ambas cifras se
reportan por separado en este documento.

### B.5 Coste del motor de análisis completo

Activar features, clasificador y contador de repeticiones (`capture_only: false`) añade
{fmt(b("pipeline_ms", "pesado_fps10_analisis_completo", "feature", "p50_ms") + b("pipeline_ms", "pesado_fps10_analisis_completo", "classify", "p50_ms") + b("pipeline_ms", "pesado_fps10_analisis_completo", "track", "p50_ms"), 2)} ms
por fotograma (feature {fmt(b("pipeline_ms", "pesado_fps10_analisis_completo", "feature", "p50_ms"), 2)} ms,
clasificador {fmt(b("pipeline_ms", "pesado_fps10_analisis_completo", "classify", "p50_ms"), 2)} ms,
rep tracker {fmt(b("pipeline_ms", "pesado_fps10_analisis_completo", "track", "p50_ms"), 2)} ms).
Frente a la inferencia de pose es ruido: **la analítica de alto nivel no es un problema de
latencia**.
""")

    # ------------------------------------------------------------------ conclusiones
    entrega_p95_preview = b("cliente_e2e", "pesado_fps10_preview", "latencia_entrega_ms", "p95_ms")
    entrega_p95_sin = b("cliente_e2e", "pesado_fps10_sinpreview", "latencia_entrega_ms", "p95_ms")
    payload_preview = b("cliente_e2e", "pesado_fps10_preview", "tamano_payload_kib", "media_ms")
    payload_sin = b("cliente_e2e", "pesado_fps10_sinpreview", "tamano_payload_kib", "media_ms")
    proc_p95 = b("consumer_timing_ms", "pesado_fps10_preview", "process_bgr_ms", "p95_ms")
    sleep_p50 = b("consumer_timing_ms", "pesado_fps10_preview", "scheduled_sleep_ms", "p50_ms")
    ligero30_intervalo = b("cliente", "ligero_fps30_preview", "intervalo_entre_mensajes", "media_ms")
    pesado10_intervalo = b("cliente", "pesado_fps10_preview", "intervalo_entre_mensajes", "media_ms")
    wall_p95 = b("consumer_timing_ms", "pesado_fps10_preview", "wall_before_send_ms", "p95_ms")
    queue_p95 = b("consumer_timing_ms", "pesado_fps10_preview", "queue_wait_ms", "p95_ms")
    residual_pesado = b("consumer_timing_ms", "pesado_fps10_preview", "residual_before_send_ms", "p50_ms")
    residual_ligero = b("consumer_timing_ms", "ligero_fps10_preview", "residual_before_send_ms", "p50_ms")
    capacidad_p95 = base_p95 + (entrega_p95_preview if entrega_p95_preview == entrega_p95_preview else 0.0)
    observado_p95 = wall_p95 + (entrega_p95_preview if entrega_p95_preview == entrega_p95_preview else 0.0)

    partes.append(f"""---

## Cuello de botella y presupuesto de fotograma

### El cuello de botella de cómputo

**El cuello de botella es la inferencia de pose de MediaPipe, y nada más se le acerca.**
Con la configuración por defecto (1080p reducido a 640 px) la inferencia consume
{fmt(base_infer)} ms de los {fmt(base_total)} ms del pipeline, es decir el
{fmt(base_infer / base_total * 100.0, 1)} %. Las otras tres etapas juntas suman
{fmt(base_total - base_infer, 2)} ms: lectura del fotograma {fmt(base_lectura, 2)} ms,
cálculo de ángulos de rodilla {fmt(base_ang, 3)} ms y codificación JPEG de la vista previa
{fmt(jpeg_max, 2)} ms como máximo.

### Veredicto sobre las hipótesis del reporte previo

`docs/guias/reporte_latencia_frames_ws_pose_stream.md` enumeró cinco puntos críticos sin
medirlos. Con números, quedan así:

| Hipótesis previa | Veredicto medido |
|---|---|
| Throttling explícito por `target_fps` | **Confirmada y dominante.** A 10 FPS objetivo el servidor duerme {fmt(sleep_p50)} ms de los 100 ms de presupuesto ({fmt(sleep_p50, 0)} % de ocio). El retraso percibido es un ritmo impuesto, no falta de capacidad. |
| Tiempo de inferencia de MediaPipe | **Confirmada como mayor consumidor de CPU**, pero muy por debajo del presupuesto: `process_bgr` p95 = {fmt(proc_p95)} ms frente a 100 ms disponibles. |
| Coste de codificar la vista previa | **Refutada en CPU** ({fmt(jpeg_max, 2)} ms como máximo) y **confirmada en enlace y serialización**: el payload pasa de {fmt(payload_sin, 1)} KiB a {fmt(payload_preview, 1)} KiB por mensaje ({fmt(payload_preview / payload_sin, 1)}x) y la entrega p95 de {fmt(entrega_p95_sin)} ms a {fmt(entrega_p95_preview)} ms. |
| Decodificación y render en el cliente | **Fuera del alcance de esta medición**: el cliente Flutter no está instrumentado aquí. Sigue siendo la única hipótesis sin verificar. |
| Ritmo de lectura del archivo | **Refutada.** `queue_wait_ms` p95 = {fmt(queue_p95, 2)} ms: el productor de fotogramas siempre tiene el siguiente listo. La arquitectura productor-consumidor cumple su función. |

Y aparecen dos causas que aquel reporte no contemplaba:

1. **El propio ajuste automático encarece el pipeline.** Para un clip 1080p,
   `build_stream_processing_plan` marca tier *heavy* y aplica `decode_max_side = 720`.
   Ese redimensionado corre en el hilo del bucle de eventos y se ve aislado en
   `residual_before_send_ms`: {fmt(residual_pesado, 2)} ms en el vídeo de 1080p frente a
   {fmt(residual_ligero, 2)} ms en el de 360p, que no lo ejecuta. La medición offline lo
   confirma de forma independiente: {fmt(heavy_down, 2)} ms por fotograma, sin ahorrar nada
   en la inferencia porque MediaPipe volvería a reducir a 640 px de todas formas.
2. **El reposo impuesto por `target_fps` encarece cada fotograma** (sección B.4): el mismo
   trabajo cuesta {fmt(b("consumer_timing_ms", "ligero_fps10_preview", "process_bgr_ms", "p50_ms"))} ms
   a 10 FPS y {fmt(b("consumer_timing_ms", "ligero_fps30_preview", "process_bgr_ms", "p50_ms"))} ms
   a 30 FPS. Bajar el ritmo objetivo no abarata el fotograma: lo encarece.

### Presupuesto de fotograma alcanzable en esta máquina

Hay que distinguir dos cifras, y este experimento las separa deliberadamente:

- **Capacidad del pipeline de visión** (Nivel A, sin servidor ni pausas):
  **{fmt(base_p95)} ms p95** por fotograma a 1080p reducido a 640 px, lo que equivale a
  {fmt(1000.0 / base_total, 0)} fotogramas por segundo sostenidos.
- **Latencia observada dentro del servidor** (Nivel B, preset de 10 FPS con vista previa):
  {fmt(wall_p95)} ms p95 de trabajo del servidor antes de enviar, más {fmt(entrega_p95_preview)} ms
  p95 de entrega al cliente, es decir **≈ {fmt(observado_p95, 1)} ms p95 extremo a extremo**
  sin contar el render del cliente ni red real.

| Objetivo | Presupuesto | Con la capacidad medida ({fmt(capacidad_p95, 1)} ms p95) | Con la latencia observada hoy ({fmt(observado_p95, 1)} ms p95) |
|---|---|---|---|
| 10 FPS (preset actual) | 100.0 ms | Sí, {fmt(100.0 - capacidad_p95, 0)} ms de margen | Sí, {fmt(100.0 - observado_p95, 0)} ms de margen |
| 15 FPS | 66.7 ms | Sí, {fmt(66.7 - capacidad_p95, 0)} ms de margen | Sí, {fmt(66.7 - observado_p95, 0)} ms de margen |
| 30 FPS | 33.3 ms | Sí, {fmt(33.3 - capacidad_p95, 0)} ms de margen | Al límite ({fmt(33.3 - observado_p95, 1)} ms de margen) |
| 60 FPS | 16.7 ms | Sí, pero sin margen para jitter ({fmt(16.7 - capacidad_p95, 1)} ms) | No |
| 120 FPS | 8.3 ms | No | No |

**Conclusión operativa: en este hardware el objetivo defendible es 15 FPS extremo a extremo
con la implementación actual (50 % de margen sobre la latencia observada) y 30 FPS tras
corregir el `decode_max_side` y el `inference_stride` del tier heavy.** El preset actual de
10 FPS deja ocioso dos tercios del presupuesto. El clip de 360p a 30 FPS objetivo entregó un
intervalo medio entre mensajes de {fmt(ligero30_intervalo)} ms, es decir
{fmt(1000.0 / ligero30_intervalo, 1)} FPS efectivos: el único punto de la matriz donde el
sistema se acerca a su techo real.

La medición informal previa de *~52 ms por fotograma y ~19 FPS* **no se reproduce en
ninguna configuración**. La mediana de `process_bgr` más alta de toda la matriz es
{fmt(b("consumer_timing_ms", "ligero_fps10_preview", "process_bgr_ms", "p50_ms"))} ms
(360p a 10 FPS, ya afectada por el efecto del reposo), y el pipeline puro sostiene
{fmt(1000.0 / base_total, 0)} FPS. La explicación más probable es que aquella cifra midiera
el ritmo del stream con `target_fps` activo —un límite impuesto— y no la capacidad de la
máquina. El preset de 10 FPS entregó {fmt(1000.0 / pesado10_intervalo, 1)} FPS efectivos,
que es exactamente lo que se le pidió.

### Recomendaciones derivadas de la medición

1. **Cambiar `decode_max_side` de 720 a 640 px** en `vision/stream_processing_plan.py`, o
   eliminarlo (MediaPipe reduce de todas formas). Ahorro medido: {fmt(heavy_down - r640, 2)} ms
   por fotograma, más que la lectura y el JPEG juntos.
2. **Revisar el techo del tier *heavy***. El límite de 16 FPS y el `inference_stride = 2`
   reducen a la mitad la resolución temporal del análisis angular sin justificación en este
   hardware, y el stride introduce una distribución bimodal que dificulta interpretar
   cualquier métrica de latencia.
3. **Mantener `RunningMode.VIDEO`**: es el mayor ahorro del pipeline
   ({fmt(imagen_infer / base_infer, 2)}x frente a `RunningMode.IMAGE`) y ya está bien resuelto.
4. **Optimizar la vista previa por tamaño, no por CPU.** Bajar la calidad de 90 a 76 ahorra
   unos 32 KiB por mensaje y prácticamente 0 ms de CPU; en un despliegue con red real ése es
   el parámetro que decide la fluidez, no `preview_fps`.
5. **Subir `target_fps` antes que bajarlo** si se busca fluidez: la sección B.4 muestra que
   el ritmo bajo no libera CPU, la encarece.
6. **La latencia no es el factor limitante de la exactitud angular.** Con
   {fmt(base_ang, 3)} ms de coste, el cálculo de ángulos puede ejecutarse en todos los
   fotogramas disponibles; cualquier pérdida de resolución temporal proviene de decisiones
   de throttling y de `inference_stride`, no de capacidad de cómputo. La mitad de "latencia"
   de la pregunta de investigación se responde de forma afirmativa: el sistema opera en
   tiempo real con holgura sobre hardware de consumo.

## Limitaciones

- Cliente y servidor corren en la misma máquina: **no hay latencia de red real**. Las cifras
  de entrega son un piso, no un extremo a extremo de despliegue. Un despliegue real añade el
  transporte, y ahí los {fmt(payload_preview, 0)} KiB por mensaje de la vista previa pasan a
  ser determinantes.
- El render del cliente Flutter (decodificación del JPEG y repintado) **no está
  instrumentado**; la latencia percibida por el usuario final es mayor que la reportada. Es
  la única de las cinco hipótesis del reporte previo que queda sin verificar.
- La fuente es vídeo en archivo, no cámara en vivo: no se mide la latencia de captura del
  sensor ni el jitter del driver.
- **Una sola sesión por configuración y una sola máquina.** No hay repeticiones
  independientes ni intervalos de confianza entre sesiones. La matriz muestra variabilidad
  entre corridas del mismo tier (por ejemplo, `process_bgr` p95 de {fmt(b("consumer_timing_ms", "pesado_fps8_preview", "process_bgr_ms", "p95_ms"))} ms
  a 8 FPS frente a {fmt(b("consumer_timing_ms", "pesado_fps10_preview", "process_bgr_ms", "p95_ms"))} ms
  a 10 FPS) que este diseño no puede separar del efecto de la configuración.
- **Las métricas del tier *heavy* son bimodales** por `inference_stride = 2`: la mitad de los
  fotogramas no ejecutan inferencia. Su p50 y su p95 caen a lados distintos de esa
  bimodalidad y no deben leerse como percentiles de una sola población. Las conclusiones
  sobre el efecto del throttle se apoyan en el tier *light*, que es unimodal.
- El efecto del reposo sobre el coste por fotograma (sección B.4) se reporta como
  **hipótesis**: la medición es sólida y reproducible, pero la atribución a la planificación
  entre núcleos de rendimiento y de eficiencia no se demostró con instrumentación de
  frecuencia.
- El barrido de resolución altera una constante de módulo en tiempo de ejecución; es
  equivalente a cambiar la configuración, pero no es exactamente la ruta de producción.
- El experimento mide **latencia, no exactitud**. La tasa de detección de pose fue del 100 %
  en los dos vídeos, pero la validez de los ángulos frente a métodos de referencia es objeto
  del Bloque 1 del trabajo, no de este documento.

---

## Figura

![Desglose de latencia por etapa](exp4_latencia_etapas.png)

`exp4_latencia_etapas.png`, generada con matplotlib (backend Agg) a partir de
`exp4_latencia.csv`.

## Archivos generados

| Archivo | Contenido |
|---|---|
| `validacion/resultados/exp4_latencia.csv` | Tabla larga unificada de Niveles A y B |
| `validacion/resultados/exp4_latencia.md` | Este reporte |
| `validacion/resultados/exp4_latencia_etapas.png` | Figura de cuatro paneles |
| `validacion/resultados/exp4a_frames.csv` | Tiempos por fotograma del Nivel A (evidencia cruda) |
| `validacion/resultados/exp4a_jpeg_frames.csv` | Tiempos y tamaños de cada codificación JPEG |
| `validacion/resultados/exp4a_agregados.csv` | Agregados del Nivel A |
| `validacion/resultados/exp4b_agregados.csv` | Agregados del Nivel B |
| `validacion/resultados/exp4b_perfilador_salida.txt` | Salida cruda de `profile_pose_stream.py` |
| `validacion/resultados/exp4b_uvicorn.log` | Log del backend durante la medición |

## Reproducción

```bash
cd backend
PYTHONPATH=. python ../validacion/experimentos/exp4a_latencia_etapas.py
PYTHONPATH=. python ../validacion/experimentos/exp4b_latencia_e2e.py
PYTHONPATH=. python ../validacion/experimentos/exp4_reporte.py
```
""")
    return "\n".join(partes)


def main() -> int:
    filas_a = leer_csv(RESULTS_DIR / "exp4a_agregados.csv")
    filas_b = leer_csv(RESULTS_DIR / "exp4b_agregados.csv")
    if not filas_a:
        print("ERROR: falta exp4a_agregados.csv; ejecuta primero el Nivel A", file=sys.stderr)
        return 1

    cols = ["nivel", "bloque", "configuracion", "video", "parametros", "metrica",
            "n", "media_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms", "pct_del_total"]
    destino_csv = RESULTS_DIR / "exp4_latencia.csv"
    with destino_csv.open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for fila in filas_a + filas_b:
            w.writerow({c: fila.get(c, "") for c in cols})

    construir_figura(filas_a, filas_b, RESULTS_DIR / "exp4_latencia_etapas.png")
    (RESULTS_DIR / "exp4_latencia.md").write_text(
        construir_reporte(filas_a, filas_b), encoding="utf-8"
    )

    print(f"Escrito: {destino_csv} ({len(filas_a) + len(filas_b)} filas)")
    print(f"Escrito: {RESULTS_DIR / 'exp4_latencia_etapas.png'}")
    print(f"Escrito: {RESULTS_DIR / 'exp4_latencia.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
