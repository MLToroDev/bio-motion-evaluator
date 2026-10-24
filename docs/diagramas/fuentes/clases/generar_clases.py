#!/usr/bin/env python3
"""
Genera los diagramas de clases UML (Graphviz .dot) de Bio-Motion Evaluator.

Las especificaciones de cada diagrama están en este archivo como datos (clases,
relaciones, notas). Los nombres de clases, atributos y métodos se copian del código
fuente (``backend/``, ``appWeb/src/``) y se verificaron con ``rg``; la estructura bruta
extraída automáticamente con ``pyreverse`` está en ``../generado/``.

Uso (desde cualquier directorio)::

    python3 docs/diagramas/fuentes/clases/generar_clases.py

Escribe un ``.dot`` por diagrama junto a este script. El renderizado a SVG/PNG lo hace
``../herramientas/renderizar.sh``.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field, replace
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FUENTE = "Helvetica"

# Paleta sobria, apta para impresión en escala de grises.
COLOR = {
    "nucleo": "#E8F1FB",
    "datos": "#FFF6E0",
    "clasif": "#EAF6EC",
    "track": "#F3ECF8",
    "servicio": "#FDEDEC",
    "config": "#EEEEEE",
    "router": "#E8F1FB",
    "ws": "#E3F4F4",
    "schema": "#FFF6E0",
    "orm": "#EAF6EC",
    "infra": "#F3ECF8",
    "ref": "#FFFFFF",
    "hook": "#E8F1FB",
    "comp": "#EAF6EC",
    "tipo": "#FFF6E0",
    "lib": "#F3ECF8",
    "ext": "#FFFFFF",
}


@dataclass
class Clase:
    id: str
    nombre: str
    estereotipo: str | None = None
    atributos: list[str] = field(default_factory=list)
    operaciones: list[str] = field(default_factory=list)
    color: str = "nucleo"
    abstracta: bool = False
    subtitulo: str | None = None  # p. ej. módulo de origen
    compacta: bool = False  # solo nombre (referencia a otro diagrama)


@dataclass
class Relacion:
    origen: str
    destino: str
    tipo: str  # herencia | realizacion | composicion | agregacion | asociacion | dependencia | nota
    etiqueta: str | None = None
    mult_origen: str | None = None
    mult_destino: str | None = None
    extra: str = ""
    restringe: bool = True  # False -> constraint=false (no condiciona los rangos)


@dataclass
class Nota:
    id: str
    texto: list[str]


@dataclass
class Paquete:
    id: str
    titulo: str
    miembros: list[str]
    color: str = "#FAFAFA"


@dataclass
class Diagrama:
    archivo: str
    titulo: str
    clases: list[Clase]
    relaciones: list[Relacion]
    notas: list[Nota] = field(default_factory=list)
    paquetes: list[Paquete] = field(default_factory=list)
    rankdir: str = "TB"
    extra_grafo: str = ""
    # Ayudas de maquetación (no son relaciones UML): aristas invisibles y rangos comunes.
    invisibles: list[tuple[str, str]] = field(default_factory=list)
    mismo_rango: list[list[str]] = field(default_factory=list)


def _esc(texto: str) -> str:
    return html.escape(texto, quote=False)


def _miembro(texto: str) -> str:
    """Escapa un miembro y subraya los estáticos/constantes marcados con '_u_'."""
    if texto.startswith("_u_"):
        return f"<U>{_esc(texto[3:])}</U>"
    if texto.startswith("_i_"):
        return f"<I>{_esc(texto[3:])}</I>"
    return _esc(texto)


def _etiqueta_clase(c: Clase) -> str:
    filas = []
    cab = []
    if c.estereotipo:
        cab.append(f'<FONT POINT-SIZE="10">«{_esc(c.estereotipo)}»</FONT>')
    nombre = _esc(c.nombre)
    nombre = f"<I>{nombre}</I>" if c.abstracta else nombre
    cab.append(f'<B><FONT POINT-SIZE="13">{nombre}</FONT></B>')
    if c.subtitulo:
        cab.append(f'<FONT POINT-SIZE="9" COLOR="#555555">{_esc(c.subtitulo)}</FONT>')
    fondo = COLOR.get(c.color, c.color)
    filas.append(
        f'<TR><TD BGCOLOR="{fondo}" CELLPADDING="4">' + "<BR/>".join(cab) + "</TD></TR>"
    )
    if not c.compacta:
        attrs = "".join(f"{_miembro(a)}<BR ALIGN=\"LEFT\"/>" for a in c.atributos) or " "
        ops = "".join(f"{_miembro(o)}<BR ALIGN=\"LEFT\"/>" for o in c.operaciones) or " "
        filas.append(f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" CELLPADDING="4">{attrs}</TD></TR>')
        filas.append(f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" CELLPADDING="4">{ops}</TD></TR>')
    return (
        '<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" COLOR="#333333" BGCOLOR="white">'
        + "".join(filas)
        + "</TABLE>>"
    )


def _etiqueta_nota(n: Nota) -> str:
    return "<" + "".join(f"{_miembro(t)}<BR ALIGN=\"LEFT\"/>" for t in n.texto) + ">"


_ESTILO = {
    "herencia": 'arrowhead=empty, style=solid',
    "realizacion": 'arrowhead=empty, style=dashed',
    "composicion": 'dir=both, arrowtail=diamond, arrowhead=none, style=solid',
    "agregacion": 'dir=both, arrowtail=odiamond, arrowhead=none, style=solid',
    "asociacion": 'arrowhead=vee, style=solid',
    "dependencia": 'arrowhead=vee, style=dashed',
    "nota": 'arrowhead=none, style=dashed, color="#888888"',
}


def a_dot(d: Diagrama) -> str:
    out = [
        f'// {d.titulo}',
        "// Generado por generar_clases.py — no editar a mano.",
        f'digraph "{d.archivo}" {{',
        '  charset="utf-8";',
        f'  graph [rankdir={d.rankdir}, fontname="{FUENTE}", fontsize=12, bgcolor="white", '
        'nodesep=0.35, ranksep=0.55, pad=0.3, newrank=true' + (", " + d.extra_grafo if d.extra_grafo else "") + "];",
        f'  node [shape=plain, fontname="{FUENTE}", fontsize=11];',
        f'  edge [fontname="{FUENTE}", fontsize=10, color="#333333", arrowsize=0.9];',
    ]
    en_paquete = {m for p in d.paquetes for m in p.miembros}
    por_id = {c.id: c for c in d.clases}
    notas = {n.id: n for n in d.notas}

    def nodo(ident: str) -> str:
        if ident in por_id:
            return f'  "{ident}" [label={_etiqueta_clase(por_id[ident])}];'
        n = notas[ident]
        return (
            f'  "{ident}" [shape=note, style=filled, fillcolor="#FFFBE6", color="#999999", '
            f'fontsize=10, margin="0.12,0.08", label={_etiqueta_nota(n)}];'
        )

    for p in d.paquetes:
        out.append(f'  subgraph "cluster_{p.id}" {{')
        out.append(
            f'    label=<<B>{_esc(p.titulo)}</B>>; labeljust="l"; style="rounded,filled"; '
            f'fillcolor="{p.color}"; color="#9A9A9A"; fontsize=12; margin=12;'
        )
        for m in p.miembros:
            out.append("  " + nodo(m))
        out.append("  }")
    for c in d.clases:
        if c.id not in en_paquete:
            out.append(nodo(c.id))
    for n in d.notas:
        if n.id not in en_paquete:
            out.append(nodo(n.id))
    for r in d.relaciones:
        attrs = [_ESTILO[r.tipo]]
        if r.etiqueta:
            attrs.append("label=<" + _esc(r.etiqueta).replace("\n", "<BR/>") + ">")
        if r.mult_origen:
            attrs.append(f'taillabel="{r.mult_origen}"')
        if r.mult_destino:
            attrs.append(f'headlabel="{r.mult_destino}"')
        if r.mult_origen or r.mult_destino:
            attrs.append("labeldistance=1.6, labelangle=35")
        if not r.restringe:
            attrs.append("constraint=false")
        if r.extra:
            attrs.append(r.extra)
        out.append(f'  "{r.origen}" -> "{r.destino}" [{", ".join(attrs)}];')
    for a, b in d.invisibles:
        out.append(f'  "{a}" -> "{b}" [style=invis];')
    for grupo in d.mismo_rango:
        out.append("  { rank=same; " + " ".join(f'"{g}";' for g in grupo) + " }")
    out.append("}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# (a) Núcleo de visión y goniometría
# ---------------------------------------------------------------------------

def _catalogo_vision() -> dict[str, Clase]:
    """Clases del motor de visión, compartidas por los diagramas (a-1) y (a-2)."""
    C = Clase
    clases = [
        C("RealtimeEngineSession", "RealtimeEngineSession", None, [
            "- _model_path: Path",
            "- _cfg: ExerciseClassifierConfig",
            "- _inference_stride: int",
            "- _analysis_enabled: bool",
            "- _forced_exercise_label: str | None",
            "- _last_pose: PoseFrame | None",
        ], [
            "+ __init__(backend_root, model_path, classifier_cfg,",
            "      *, inference_stride, analysis_enabled, forced_exercise_label)",
            "+ process_bgr(bgr, frame_index, timestamp_ms): dict",
            "+ process_jpeg(image_bytes, frame_index): dict",
            "+ reset(): None",
            "- _extract_pose(frame_index, bgr, jpeg_bytes, timestamp_ms): PoseFrame",
            "- _after_extract(st, pose, frame_index): dict",
        ], color="nucleo", subtitulo="vision.realtime_engine"),
        C("pose_extractor", "pose_extractor", "utility", [], [
            "+ extract_pose_jpeg(image_bytes, model_path): PoseFrame",
            "+ extract_pose_bgr(bgr, model_path): PoseFrame",
            "+ extract_pose_bgr_video(bgr, model_path, timestamp_ms): PoseFrame",
            "- _relacion_aspecto(bgr): float | None",
        ], color="nucleo", subtitulo="vision.pose_extractor"),
        C("mediapipe", "mediapipe", "service", [
            "- _TARGET_MAX_DIM = 640",
            "- _VIDEO_LANDMARKER_LOCK: threading.Lock",
        ], [
            "+ analyze_image_bytes(image_bytes, model_path): PoseResult",
            "+ analyze_frame_bgr(bgr, model_path): PoseResult",
            "+ analyze_frame_bgr_video(bgr, model_path, timestamp_ms): PoseResult",
            "+ analyze_frame_rgb(rgb, model_path): PoseResult",
            "+ reset_pose_video_timestamp_anchor(): None",
        ], color="servicio", subtitulo="app.services.pose.mediapipe"),
        C("PoseResult", "PoseResult", "dataclass", [
            "+ ok: bool",
            "+ landmarks: list[dict[str, Any]]",
            "+ world_landmarks: list[dict[str, Any]]",
            "+ note: str | None",
        ], [], color="servicio", subtitulo="app.services.pose.mediapipe"),
        C("biomechanics", "biomechanics", "utility", [
            "_u_LEFT_HIP = 23, LEFT_KNEE = 25, LEFT_ANKLE = 27",
            "_u_RIGHT_HIP = 24, RIGHT_KNEE = 26, RIGHT_ANKLE = 28",
        ], [
            "+ angulos_rodilla(landmarks, world_landmarks, relacion_aspecto)",
            "      : KneeAnglesPayload | None",
            "+ knee_angles_from_landmarks(landmarks): KneeAnglesPayload | None",
            "+ escalar_a_isotropico(landmarks, relacion_aspecto): list[dict]",
            "+ elbow_flex_angles_from_landmarks(landmarks): dict[str, float]",
            "+ shoulder_width_proxy(landmarks): float | None",
        ], color="nucleo", subtitulo="vision.biomechanics"),
        C("KneeAnglesPayload", "KneeAnglesPayload", "TypedDict", [
            "+ left_knee_flexion_angle_deg: float",
            "+ right_knee_flexion_angle_deg: float",
            "+ left_knee_internal_angle_deg: float",
            "+ right_knee_internal_angle_deg: float",
        ], [], color="datos", subtitulo="vision.biomechanics"),
        C("PoseFrame", "PoseFrame", "dataclass", [
            "+ ok: bool",
            "+ landmarks: list[dict[str, Any]]",
            "+ note: str | None",
            "+ knees: dict[str, float] | None",
            "+ world_landmarks: list[dict[str, Any]] | None",
        ], [], color="datos", subtitulo="vision.types"),
        C("FeatureFrame", "FeatureFrame", "dataclass", [
            "+ pose: PoseFrame",
            "+ frame_index: int",
            "+ exercise_label: str",
            "+ exercise_confidence: float",
            "+ dt_s: float",
            "+ angular_velocity_deg_s: dict[str, float]",
            "+ periodicity_score: float",
            "+ calibration_scale: float",
        ], [], color="datos", subtitulo="vision.types"),
        C("ClassificationResult", "ClassificationResult", "dataclass", [
            "+ label: str",
            "+ confidence: float",
            "+ raw_scores: dict[str, float] | None",
        ], [], color="datos", subtitulo="vision.types"),
        C("RepState", "RepState", "dataclass", [
            "+ rep_phase: RepPhase = \"idle\"",
            "+ rep_count: int = 0",
            "+ quality_flags: list[str]",
        ], [], color="datos", subtitulo="vision.types"),
        C("FeatureEngine", "FeatureEngine", None, [
            "- _window: deque[PoseFrame]",
            "- _calib_ref: float | None",
            "- _last_angular_vel: dict[str, float]",
            "_u_FEATURE_VECTOR_DIM = 32",
        ], [
            "+ push(pose, dt_s): None",
            "+ build_feature_vector(): np.ndarray",
            "+ build_feature_frame(pose, frame_index, exercise_label,",
            "      exercise_confidence, dt_s): FeatureFrame",
            "+ window_full(): bool",
            "+ reset(): None",
        ], color="nucleo", subtitulo="vision.feature_engine"),
        C("ExerciseClassifier", "ExerciseClassifier", "Protocol", [], [
            "+ classify(features, window_full): ClassificationResult",
        ], color="clasif", abstracta=True, subtitulo="vision.exercise_classifier"),
        C("HysteresisClassifier", "HysteresisClassifier", None, [
            "- _inner: ExerciseClassifier",
            "- _stable_label: str",
            "- _candidate: str | None",
            "- _candidate_frames: int",
            "- _ema_confidence: float",
            "- _kalman: ScalarKalman1D",
        ], [
            "+ classify(features, window_full): ClassificationResult",
            "+ reset(): None",
        ], color="clasif", subtitulo="vision.exercise_classifier"),
        C("HeuristicExerciseClassifier", "HeuristicExerciseClassifier", None, [
            "- _classes: tuple[str, ...] = (\"idle\", \"squat\", \"lunge\")",
        ], [
            "+ classify(features, window_full): ClassificationResult",
        ], color="clasif", subtitulo="vision.heuristic_exercise_classifier"),
        C("NopExerciseClassifier", "NopExerciseClassifier", None, [], [
            "+ classify(features, window_full): ClassificationResult",
        ], color="clasif", subtitulo="vision.exercise_classifier"),
        C("_OnnxCls", "_OnnxCls", "local", [
            "- _session: ort.InferenceSession",
            "- _classes: list[str]",
        ], [
            "+ classify(features, window_full): ClassificationResult",
        ], color="clasif", subtitulo="definida en _try_onnx_classifier()"),
        C("exercise_classifier", "exercise_classifier", "utility", [], [
            "+ build_classifier(cfg, registry): HysteresisClassifier",
            "- _try_onnx_classifier(manifest, cfg): ExerciseClassifier | None",
        ], color="clasif", subtitulo="vision.exercise_classifier"),
        C("ScalarKalman1D", "ScalarKalman1D", None, [
            "- _q: float",
            "- _r: float",
            "- _x: float | None",
        ], [
            "+ update(measurement): float",
            "+ reset(): None",
        ], color="clasif", subtitulo="vision.scalar_kalman"),
        C("ModelRegistry", "ModelRegistry", "dataclass", [
            "+ backend_root: Path",
            "+ manifest_path: Path | None",
        ], [
            "+ load_active_manifest(): ExerciseModelManifest | None",
            "+ list_versions(): list[str]",
            "+ switch_version(name): None",
            "+ active_key(): str | None",
        ], color="clasif", subtitulo="vision.model_registry"),
        C("ExerciseModelManifest", "ExerciseModelManifest", "dataclass (frozen)", [
            "+ name: str",
            "+ path: Path",
            "+ classes: tuple[str, ...]",
            "+ window_size: int | None",
        ], [], color="clasif", subtitulo="vision.model_registry"),
        C("RepTracker", "RepTracker", "abstract", [], [
            "_i_+ update(frame: FeatureFrame): RepState",
            "_i_+ reset(): None",
        ], color="track", abstracta=True, subtitulo="vision.rep_tracker_abc (ABC)"),
        C("RepTrackerRouter", "RepTrackerRouter", None, [
            "- _unknown_label: str",
            "- _last_effective: str | None",
            "- _trackers: dict[str, RepTracker]",
        ], [
            "+ update(frame: FeatureFrame): RepState",
            "+ reset_all(): None",
        ], color="track", subtitulo="vision.rep_tracker"),
        C("SquatRepTracker", "SquatRepTracker", None, [
            "- _phase: Phase",
            "- _rep_count: int",
            "- _flex_peak: float",
            "- _flags: list[str]",
        ], [
            "+ update(frame: FeatureFrame): RepState",
            "+ reset(): None",
            "- _avg_flex(frame): float | None",
        ], color="track", subtitulo="vision.rep_trackers.squat"),
        C("UnknownRepTracker", "UnknownRepTracker", None, [
            "- _state: RepState",
        ], [
            "+ update(frame: FeatureFrame): RepState",
            "+ reset(): None",
        ], color="track", subtitulo="vision.rep_trackers.unknown"),
        C("StageTimer", "StageTimer", "dataclass", [
            "+ timing: PipelineTiming",
        ], [
            "+ mark_extract() / mark_feature()",
            "+ mark_classify() / mark_track()",
            "+ finish(): PipelineTiming",
        ], color="config", subtitulo="vision.pipeline_timer"),
        C("PipelineTiming", "PipelineTiming", "dataclass", [
            "+ extract_ms, feature_ms, classify_ms: float",
            "+ track_ms, total_ms: float",
        ], [
            "+ as_dict(): dict[str, float]",
        ], color="config", subtitulo="vision.pipeline_timer"),
        C("unified_payload", "unified_payload", "utility", [
            "_u_SCHEMA_VERSION = 1",
        ], [
            "+ build_frame_payload_v1(frame_index, pose, exercise_label,",
            "      exercise_confidence, rep, pipeline_ms): dict",
        ], color="nucleo", subtitulo="vision.unified_payload"),
        C("landmark_filter", "landmark_filter", "utility", [], [
            "+ landmarks_for_api_response(landmarks, world_landmarks,",
            "      min_visibility): tuple[list | None, list | None]",
        ], color="nucleo", subtitulo="vision.landmark_filter"),
        C("ExerciseClassifierConfig", "ExerciseClassifierConfig", "pydantic", [
            "+ min_confidence: float = 0.72",
            "+ window_size_frames: int = 45",
            "+ hysteresis_frames: int = 10",
            "+ unknown_label: str = \"unknown\"",
            "+ confidence_filter: \"ema\" | \"kalman\"",
            "+ confidence_ema_alpha: float = 0.25",
        ], [], color="config", subtitulo="app.models.schemas"),
    ]
    return {c.id: c for c in clases}


def _ref(c: Clase, donde: str) -> Clase:
    """Copia compacta (solo nombre) de una clase detallada en otro diagrama."""
    return replace(c, compacta=True, subtitulo=f"{c.subtitulo} · detalle en {donde}", color="ref")


def diagrama_vision_orquestacion() -> Diagrama:
    """(a-1) Orquestación por fotograma, estimación de pose y goniometría."""
    cat = _catalogo_vision()
    ids = [
        "RealtimeEngineSession", "pose_extractor", "mediapipe", "PoseResult", "biomechanics",
        "KneeAnglesPayload", "PoseFrame", "unified_payload", "landmark_filter", "StageTimer",
        "PipelineTiming", "ExerciseClassifierConfig",
    ]
    clases = [cat[i] for i in ids]
    clases[ids.index("ExerciseClassifierConfig")] = _ref(cat["ExerciseClassifierConfig"], "(a-2)")
    for i in ("FeatureEngine", "HysteresisClassifier", "RepTrackerRouter", "RepState"):
        clases.append(_ref(cat[i], "(a-2)"))
    R = Relacion
    rel = [
        R("RealtimeEngineSession", "pose_extractor", "dependencia", "«use»"),
        R("RealtimeEngineSession", "FeatureEngine", "composicion", "_features", "1", "0..1"),
        R("RealtimeEngineSession", "HysteresisClassifier", "composicion", "_classifier", "1", "0..1"),
        R("RealtimeEngineSession", "RepTrackerRouter", "composicion", "_router", "1", "0..1"),
        R("RealtimeEngineSession", "ExerciseClassifierConfig", "asociacion", "_cfg", None, "1"),
        R("RealtimeEngineSession", "StageTimer", "dependencia", "«create»"),
        R("RealtimeEngineSession", "unified_payload", "dependencia", "«use»"),
        R("RealtimeEngineSession", "PoseFrame", "asociacion", "_last_pose", None, "0..1", extra="weight=0"),
        R("pose_extractor", "mediapipe", "dependencia", "«use»"),
        R("pose_extractor", "biomechanics", "dependencia", "«use»\nangulos_rodilla"),
        R("pose_extractor", "PoseFrame", "dependencia", "«create»"),
        R("mediapipe", "PoseResult", "dependencia", "«create»"),
        R("biomechanics", "KneeAnglesPayload", "dependencia", "«create»"),
        R("PoseFrame", "KneeAnglesPayload", "asociacion", None, None, "knees 0..1", restringe=False),
        R("StageTimer", "PipelineTiming", "composicion", "timing", "1", "1"),
        R("unified_payload", "landmark_filter", "dependencia", "«use»"),
        R("unified_payload", "PoseFrame", "dependencia", "«use»"),
        R("unified_payload", "RepState", "dependencia", "«use»"),
    ]
    notas = [
        Nota("nota_convencion", [
            "Convención angular (biomechanics):",
            "interno = ∠(rodilla→cadera, rodilla→tobillo) ∈ [0°, 180°]",
            "flexión = min(180°, max(0°, 180° − interno))",
            "0° ≈ extensión completa; a mayor valor, más flexión.",
        ]),
        Nota("nota_espacio", [
            "Espacio de coordenadas de angulos_rodilla()",
            "(docs/spec/goniometria-espacio-de-coordenadas.md):",
            "1) world_landmarks: metros, origen en el punto medio",
            "    de las caderas, isótropo → fuente preferida;",
            "2) landmarks normalizados × (alto / ancho);",
            "3) normalizados sin corregir, solo como último recurso.",
            "La visibilidad se filtra sobre los normalizados.",
        ]),
        Nota("nota_pipeline", [
            "Pipeline por fotograma: extracción de pose → ventana de",
            "características → clasificación con histéresis →",
            "seguimiento de repeticiones → payload v1 (dict JSON).",
            "Con analysis_enabled = False solo se extrae la pose",
            "(_features, _classifier y _router quedan en None).",
        ]),
        Nota("nota_payload", [
            "Payload v1: schema_version, frame_index, pose_ok, note,",
            "landmarks (visibility ≥ umbral), world_landmarks, knees,",
            "exercise_label, exercise_confidence, rep_phase,",
            "rep_count, quality_flags, pipeline_ms.",
        ]),
    ]
    rel += [
        R("nota_convencion", "biomechanics", "nota"),
        R("nota_espacio", "biomechanics", "nota"),
        R("nota_pipeline", "RealtimeEngineSession", "nota"),
        R("nota_payload", "unified_payload", "nota"),
    ]
    return Diagrama(
        "clases_vision_orquestacion_goniometria",
        "Diagrama de clases — núcleo de visión: orquestación, pose y goniometría",
        clases, rel, notas,
        rankdir="LR",
    )


def diagrama_vision_clasificacion() -> Diagrama:
    """(a-2) Ventana de características, clasificación de ejercicio y repeticiones."""
    cat = _catalogo_vision()
    ids = [
        "FeatureEngine", "FeatureFrame", "ExerciseClassifierConfig", "HysteresisClassifier",
        "ScalarKalman1D", "ExerciseClassifier", "HeuristicExerciseClassifier",
        "NopExerciseClassifier", "_OnnxCls", "exercise_classifier", "ModelRegistry",
        "ExerciseModelManifest", "ClassificationResult", "RepTrackerRouter", "RepTracker",
        "SquatRepTracker", "UnknownRepTracker", "RepState",
    ]
    clases = [cat[i] for i in ids] + [_ref(cat["PoseFrame"], "(a-1)")]
    R = Relacion
    rel = [
        R("FeatureEngine", "PoseFrame", "agregacion", "_window\n(maxlen = window_size_frames)", "1", "0..*"),
        R("FeatureEngine", "FeatureFrame", "dependencia", "«create»"),
        R("FeatureEngine", "ExerciseClassifierConfig", "asociacion", "_cfg", None, "1"),
        R("FeatureFrame", "PoseFrame", "asociacion", "pose", None, "1"),
        R("exercise_classifier", "HysteresisClassifier", "dependencia", "«create»"),
        R("exercise_classifier", "ModelRegistry", "dependencia", "«use»"),
        R("ModelRegistry", "ExerciseModelManifest", "dependencia", "«create»"),
        R("exercise_classifier", "_OnnxCls", "dependencia", "«create»"),
        R("HysteresisClassifier", "ExerciseClassifier", "asociacion", "_inner", None, "1"),
        R("HysteresisClassifier", "ScalarKalman1D", "composicion", "_kalman", "1", "1"),
        R("HysteresisClassifier", "ExerciseClassifierConfig", "asociacion", "_cfg", None, "1", restringe=False),
        R("HeuristicExerciseClassifier", "ExerciseClassifier", "realizacion"),
        R("NopExerciseClassifier", "ExerciseClassifier", "realizacion"),
        R("_OnnxCls", "ExerciseClassifier", "realizacion"),
        R("ExerciseClassifier", "ClassificationResult", "dependencia", "«create»"),
        R("RepTrackerRouter", "RepTracker", "composicion", "_trackers", "1", "4"),
        R("SquatRepTracker", "RepTracker", "herencia"),
        R("UnknownRepTracker", "RepTracker", "herencia"),
        # Se declara invertida (FeatureFrame -> RepTracker con dir=back) solo para la maquetación;
        # se dibuja como RepTracker ..> FeatureFrame.
        R("FeatureFrame", "RepTracker", "dependencia", "«use»", extra="dir=back, arrowtail=vee, arrowhead=none"),
        R("RepTracker", "RepState", "dependencia", "«create»"),
    ]
    notas = [
        Nota("nota_vector", [
            "build_feature_vector(): vector float32 de",
            "FEATURE_VECTOR_DIM = 32 componentes (medias, ROM,",
            "asimetría y periodicidad de la flexión de rodilla en la",
            "ventana; relleno con ceros al final).",
        ]),
        Nota("nota_histeresis", [
            "Cambia de etiqueta solo si la confianza filtrada",
            "(EMA o Kalman) ≥ min_confidence durante",
            "hysteresis_frames fotogramas consecutivos;",
            "con ventana incompleta devuelve unknown_label.",
        ]),
        Nota("nota_build", [
            "build_classifier(): HeuristicExerciseClassifier por defecto;",
            "_OnnxCls si hay manifest activo y modelo ONNX válido;",
            "NopExerciseClassifier con el flag use_nop_classifier.",
            "El resultado siempre se envuelve en HysteresisClassifier.",
        ]),
        Nota("nota_squat", [
            "Fases: idle → eccentric (flexión ≥ 55°) → concentric",
            "(pico ≥ 80°) → idle (≤ 35°, +1 repetición).",
            "asymmetry_high si |L − R| / max(L, R) > 18 %;",
            "rom_low si en eccentric el pico queda < 72°.",
        ]),
        Nota("nota_router", [
            "_trackers: claves unknown, idle, squat, lunge",
            "(squat → SquatRepTracker; resto → UnknownRepTracker).",
            "Al cambiar de etiqueta se reinicia el tracker anterior.",
        ]),
    ]
    rel += [
        R("nota_vector", "FeatureEngine", "nota"),
        R("nota_histeresis", "HysteresisClassifier", "nota"),
        R("nota_build", "exercise_classifier", "nota"),
        R("nota_squat", "SquatRepTracker", "nota"),
        R("nota_router", "RepTrackerRouter", "nota"),
    ]
    return Diagrama(
        "clases_vision_clasificacion_repeticiones",
        "Diagrama de clases — núcleo de visión: características, clasificación y repeticiones",
        clases, rel, notas,
        paquetes=[
            Paquete("feat", "Ventana de características", ["nota_vector", "FeatureEngine", "FeatureFrame", "PoseFrame"], "#F7FAFE"),
            Paquete("clasif", "Clasificación de ejercicio", [
                "nota_build", "exercise_classifier", "ModelRegistry", "ExerciseModelManifest",
                "nota_histeresis", "HysteresisClassifier", "ScalarKalman1D", "ExerciseClassifier",
                "HeuristicExerciseClassifier", "NopExerciseClassifier", "_OnnxCls",
                "ClassificationResult", "ExerciseClassifierConfig"], "#F6FBF7"),
            Paquete("track", "Seguimiento de repeticiones", [
                "nota_router", "RepTrackerRouter", "RepTracker", "SquatRepTracker",
                "UnknownRepTracker", "nota_squat", "RepState"], "#FAF7FC"),
        ],
        invisibles=[("PoseFrame", "nota_router"), ("PoseFrame", "nota_squat")],
    )


# ---------------------------------------------------------------------------
# (b-1) API REST, WebSocket y servicios del backend
# ---------------------------------------------------------------------------

def diagrama_api_servicios() -> Diagrama:
    C = Clase
    cat = _catalogo_vision()
    clases = [
        C("main", "main", "module", ["+ app: FastAPI"], [
            "+ lifespan(app)  (invoca init_engine())",
            "+ GET / → root(): dict",
        ], color="config", subtitulo="app.main"),
        C("router", "router", "router", ["+ api_router: APIRouter  (prefijo /api/v1)"], [],
          color="router", subtitulo="app.api.v1.router"),
        C("health", "health", "router", [], [
            "+ GET /health → health(): HealthResponse",
        ], color="router", subtitulo="app.api.v1.health"),
        C("pose", "pose", "router", [], [
            "+ POST /analyze/pose → analyze_pose(file: UploadFile)",
            "      : PoseAnalysisResponse",
        ], color="router", subtitulo="app.api.v1.pose"),
        C("gold_standard_videos", "gold_standard_videos", "router", [], [
            "+ GET /analysis/gold-standard-videos",
            "      → get_gold_standard_videos(): dict[str, list[str]]",
        ], color="router", subtitulo="app.api.v1.gold_standard_videos"),
        C("auth", "auth", "router", [], [
            "+ POST /auth/token → login_stub(body: StubLogin, session)",
            "      : TokenResponse",
        ], color="router", subtitulo="app.api.v1.auth"),
        C("sessions", "sessions", "router", [], [
            "+ POST /sessions → create_session(body, session, user_sub): SessionOut",
            "+ GET /sessions → list_sessions(session, user_sub): list[SessionOut]",
            "+ POST /sessions/{session_id}/metrics → add_session_metric(...)",
            "+ POST /sessions/{session_id}/end → end_session(...): SessionOut",
        ], color="router", subtitulo="app.api.v1.sessions"),
        C("download", "download", "router", [], [
            "+ POST /download → request_download(payload, db): DownloadResponse",
            "+ GET /download/status/{job_id} → get_download_status(...)",
            "+ GET /download/file/{job_id} → get_download_file(...)",
            "+ DELETE /download/cleanup/{job_id} → cleanup_download(...)",
        ], color="router", subtitulo="app.api.v1.download"),
        C("live_pose", "live_pose", "websocket", [
            "- _POSE_STREAM_SLOT: asyncio.Lock",
            "- _QUEUE_MAXSIZE = 2",
        ], [
            "+ WS /ws/pose-stream → pose_stream(ws: WebSocket): None",
            "- _build_video_source(cfg: PoseStreamConfig): VideoSource",
            "- _read_frames_blocking(source, queue, loop, stop_event): None",
            "- _encode_preview_jpeg(frame, quality, *, max_long_side,",
            "      max_short_side): tuple[str | None, bool]",
        ], color="ws", subtitulo="app.api.websocket.live_pose"),
        C("_PreviewParams", "_PreviewParams", "NamedTuple", [
            "+ fps: float", "+ quality: int", "+ stride: int",
        ], [], color="ws", subtitulo="app.api.websocket.live_pose"),
        C("video", "video", "websocket", [], [
            "+ WS /ws/video → video_stream(ws: WebSocket): None",
            "- _process_jpeg_frame(engine, chunk, frame_idx): dict",
            "- _maybe_log_pose_timing(frame_idx, payload): None",
        ], color="ws", subtitulo="app.api.websocket.video"),
        C("deps", "deps", "utility", ["- _bearer: HTTPBearer"], [
            "+ optional_user_id(cred): str | None",
            "+ require_user_id(cred): str",
        ], color="infra", subtitulo="app.api.deps"),
        C("security", "security", "utility", [], [
            "+ create_access_token(subject, extra): str",
            "+ decode_token(token): dict[str, Any]",
            "+ decode_token_safe(token): dict[str, Any] | None",
        ], color="infra", subtitulo="app.core.security"),
        C("huggingface", "huggingface", "service", [], [
            "+ run_optional_inference(payload): dict | None",
        ], color="servicio", subtitulo="app.services.inference.huggingface"),
        C("downloader", "downloader", "service", [
            "_u_ALLOWED_QUALITY = {best, 1080p, 720p, 480p, 360p, worst}",
        ], [
            "+ download_video(url, output_dir, filename_template,",
            "      *, quality): str",
        ], color="servicio", subtitulo="app.services.video.downloader (yt-dlp)"),
        C("tasks", "tasks", "Celery task", [], [
            "+ download_and_process_video(self, job_id_str, url, quality): dict",
        ], color="infra", subtitulo="app.workers.tasks"),
        C("celery_app", "celery_app", "module", ["+ celery_app: Celery  (\"video_worker\", broker Redis)"], [],
          color="infra", subtitulo="app.workers.celery_app"),
        C("db_session", "session", "module", ["+ SessionLocal: _SyncSessionLocal"], [
            "+ init_engine(): None",
            "+ get_session(): AsyncGenerator[AsyncSession, None]",
            "+ get_db(): Generator[Session, None, None]",
        ], color="orm", subtitulo="app.db.session"),
        C("Settings", "Settings", "BaseSettings", [
            "+ mediapipe_pose_model_path: str",
            "+ pose_inference_stride: int",
            "+ pose_landmark_min_visibility_response: float",
            "+ access_token_expire_minutes: int",
            "+ celery_broker_url: str",
            "+ downloads_dir: str",
        ], [
            "+ resolve_model_path(backend_root): Path",
            "_u_+ gold_standard_videos_dir(): Path",
            "+ exercise_classifier_config(): ExerciseClassifierConfig",
            "+ feature_flags(): dict[str, Any]",
        ], color="config", subtitulo="app.config (instancia global settings)"),
        C("VideoSource", "VideoSource", None, [
            "+ source_type: SourceType  (\"camera\" | \"file\" | \"url\")",
            "+ total_frame_count: int | None",
        ], [
            "+ __init__(source_type, file_path, device_index, *, loop_file)",
            "+ stream_geometry(): tuple[int, int, float]",
            "+ get_frame(): np.ndarray | None",
            "+ release(): None",
        ], color="nucleo", subtitulo="vision.processor"),
        C("stream_processing_plan", "stream_processing_plan", "utility", [], [
            "+ build_stream_processing_plan(*, stream_tuning, requested_target_fps,",
            "      max_throughput, preview_jpeg_quality, base_inference_stride,",
            "      native_width, native_height, native_fps): StreamProcessingPlan",
            "+ classify_stream_tier(width, height, fps): \"light\" | \"medium\" | \"heavy\"",
            "+ downscale_bgr_max_side(bgr, max_side): np.ndarray",
        ], color="nucleo", subtitulo="vision.stream_processing_plan"),
        C("StreamProcessingPlan", "StreamProcessingPlan", "dataclass", [
            "+ tier: str",
            "+ tuning_mode: StreamTuningMode",
            "+ decode_max_side: int | None",
            "+ inference_stride: int",
            "+ effective_target_fps: float",
            "+ preview_jpeg_quality: int",
        ], ["+ to_public_dict(): dict[str, Any]"], color="nucleo",
          subtitulo="vision.stream_processing_plan"),
        _ref(cat["RealtimeEngineSession"], "(a-1)"),
        _ref(cat["mediapipe"], "(a-1)"),
        C("UserORM", "UserORM", "ORM", compacta=True, color="ref", subtitulo="app.db.models · detalle en (b-2)"),
        C("SessionORM", "SessionORM", "ORM", compacta=True, color="ref", subtitulo="app.db.models · detalle en (b-2)"),
        C("SessionMetricORM", "SessionMetricORM", "ORM", compacta=True, color="ref", subtitulo="app.db.models · detalle en (b-2)"),
        C("VideoDownloadJobORM", "VideoDownloadJobORM", "ORM", compacta=True, color="ref", subtitulo="app.db.models · detalle en (b-2)"),
    ]
    R = Relacion
    rel = [
        R("main", "router", "dependencia", "«include» /api/v1"),
        R("main", "live_pose", "dependencia", "«include»"),
        R("main", "video", "dependencia", "«include»"),
        *[R("router", r, "dependencia", "«include»") for r in
          ("health", "pose", "gold_standard_videos", "auth", "sessions", "download")],
        R("pose", "RealtimeEngineSession", "dependencia", "«create» 1 por petición"),
        R("pose", "huggingface", "dependencia"),
        R("gold_standard_videos", "Settings", "dependencia"),
        R("auth", "security", "dependencia"),
        R("auth", "UserORM", "dependencia"),
        R("auth", "db_session", "dependencia", "«use» get_session"),
        R("sessions", "deps", "dependencia", "«use» require_user_id"),
        R("sessions", "db_session", "dependencia", "«use» get_session"),
        R("sessions", "SessionORM", "dependencia"),
        R("sessions", "SessionMetricORM", "dependencia"),
        R("deps", "security", "dependencia"),
        R("download", "tasks", "dependencia", "«use» .delay()"),
        R("download", "VideoDownloadJobORM", "dependencia"),
        R("download", "db_session", "dependencia", "«use» get_db"),
        R("tasks", "celery_app", "dependencia", "«registered in»"),
        R("tasks", "downloader", "dependencia"),
        R("tasks", "VideoDownloadJobORM", "dependencia", "«update» status"),
        R("live_pose", "VideoSource", "dependencia", "«create»"),
        R("live_pose", "stream_processing_plan", "dependencia"),
        R("stream_processing_plan", "StreamProcessingPlan", "dependencia", "«create»"),
        R("live_pose", "_PreviewParams", "dependencia"),
        R("live_pose", "RealtimeEngineSession", "dependencia", "«create» 1 por conexión"),
        R("live_pose", "mediapipe", "dependencia", "«use» reset_pose_video_timestamp_anchor"),
        R("video", "RealtimeEngineSession", "dependencia", "«create» 0..1 por conexión"),
    ]
    notas = [
        Nota("nota_settings", [
            "settings = Settings() se importa en todos los módulos",
            "(ruta del modelo, stride, umbral de visibilidad, JWT,",
            "Celery). Sus dependencias no se dibujan para no saturar.",
        ]),
        Nota("nota_ws", [
            "/ws/pose-stream: el servidor lee el video (archivo del",
            "catálogo, cámara del servidor o URL). Una sola sesión",
            "activa (_POSE_STREAM_SLOT); hilo productor → cola de 2.",
            "Los tipos de entrada y salida (PoseStreamConfig, *Response)",
            "se detallan en el diagrama (b-2).",
            "/ws/video: el cliente envía JPEG binarios tras",
            "{\"analyze_pose\": true}; responde un payload v1 por JPEG.",
        ]),
    ]
    rel += [R("nota_settings", "Settings", "nota"), R("nota_ws", "live_pose", "nota")]
    paquetes = [
        Paquete("rest", "API REST — app.api.v1", ["router", "health", "pose", "gold_standard_videos", "auth", "sessions", "download"], "#F7FAFE"),
        Paquete("ws", "WebSocket — app.api.websocket", ["live_pose", "_PreviewParams", "video", "nota_ws"], "#F4FBFB"),
        Paquete("seg", "Seguridad", ["deps", "security"], "#FAF7FC"),
        Paquete("serv", "Servicios y tareas asíncronas", ["huggingface", "downloader", "tasks", "celery_app"], "#FEF9F8"),
        Paquete("vis", "Motor de visión (backend/vision)", ["RealtimeEngineSession", "mediapipe", "VideoSource", "stream_processing_plan", "StreamProcessingPlan"], "#F7FAFE"),
        Paquete("db", "Persistencia — app.db", ["db_session", "UserORM", "SessionORM", "SessionMetricORM", "VideoDownloadJobORM"], "#F6FBF7"),
    ]
    return Diagrama(
        "clases_api_servicios_backend",
        "Diagrama de clases — API y servicios del backend",
        clases, rel, notas, paquetes, rankdir="LR",
    )


# ---------------------------------------------------------------------------
# (b-2) Esquemas Pydantic y modelos ORM
# ---------------------------------------------------------------------------

def diagrama_esquemas_persistencia() -> Diagrama:
    C = Clase
    S = "app.models.schemas"
    clases = [
        C("PoseStreamConfig", "PoseStreamConfig", "pydantic", [
            "+ source: \"camera\" | \"file\" | \"url\" = \"file\"",
            "+ video_filename: str | None",
            "+ device_index: int = 0",
            "+ stream_url: str | None",
            "+ target_fps: float = 15.0  [0.5, 60]",
            "+ max_throughput: bool = False",
            "+ stream_tuning: \"auto\" | \"off\" = \"auto\"",
            "+ include_preview: bool = True",
            "+ preview_fps: 8 | 10 | 12 = 10",
            "+ preview_jpeg_quality: int = 84  [70, 90]",
            "+ capture_only: bool = False",
            "+ forced_exercise_label: str | None",
            "+ diagnostics: bool = False",
        ], [], color="schema", subtitulo=S),
        C("UnifiedWsFrameV1", "UnifiedWsFrameV1", "pydantic", [
            "+ schema_version: int = 1",
            "+ frame_index: int",
            "+ server_ts_ms: int",
            "+ pose_ok: bool",
            "+ note: str | None",
            "+ landmarks: list[dict] | None",
            "+ knees: dict[str, Any] | None",
            "+ exercise_label: str = \"unknown\"",
            "+ exercise_confidence: float  [0, 1]",
            "+ rep_phase: str = \"idle\"",
            "+ rep_count: int",
            "+ quality_flags: list[str]",
            "+ pipeline_ms: dict[str, float] | None",
            "+ preview_jpeg_base64: str | None",
            "+ total_frames: int | None",
            "+ error: str | None",
            "+ stream_done: bool | None",
        ], [], color="schema", subtitulo=S),
        C("PipelineTimingMs", "PipelineTimingMs", "pydantic", [
            "+ extract, feature, classify: float",
            "+ track, total: float",
        ], [], color="schema", subtitulo=S),
        C("PoseAnalysisResponse", "PoseAnalysisResponse", "pydantic", [
            "+ ok: bool",
            "+ landmarks: list[LandmarkPoint]",
            "+ world_landmarks: list[LandmarkPoint]",
            "+ note: str | None",
            "+ raw: dict[str, Any] | None",
            "+ exercise_label, rep_phase: str",
            "+ exercise_confidence: float",
            "+ rep_count: int",
            "+ quality_flags: list[str]",
            "+ pipeline_ms: dict[str, float] | None",
        ], [], color="schema", subtitulo=S),
        C("LandmarkPoint", "LandmarkPoint", "pydantic", [
            "+ index: int", "+ x: float", "+ y: float", "+ z: float",
            "+ visibility: float | None",
        ], [], color="schema", subtitulo=S),
        C("HealthResponse", "HealthResponse", "pydantic", [
            "+ status: str = \"ok\"", "+ version: str",
        ], [], color="schema", subtitulo=S),
        C("ExerciseClassifierConfig", "ExerciseClassifierConfig", "pydantic", compacta=True, color="ref",
          subtitulo=f"{S} · detalle en (a-2)"),
        C("StubLogin", "StubLogin", "pydantic", ["+ email: str"], [], color="schema", subtitulo="app.api.v1.auth"),
        C("TokenResponse", "TokenResponse", "pydantic", [
            "+ access_token: str", "+ token_type: str = \"bearer\"",
        ], [], color="schema", subtitulo="app.api.v1.auth"),
        C("CreateSessionBody", "CreateSessionBody", "pydantic", [
            "+ exercise_label: str = \"unknown\"", "+ device_info: dict[str, Any] | None",
        ], [], color="schema", subtitulo="app.api.v1.sessions"),
        C("SessionOut", "SessionOut", "pydantic", [
            "+ id: UUID", "+ user_id: UUID", "+ exercise_label: str",
            "+ started_at: datetime | None", "+ ended_at: datetime | None",
        ], [], color="schema", subtitulo="app.api.v1.sessions (from_attributes)"),
        C("SessionMetricBody", "SessionMetricBody", "pydantic", [
            "+ frame_index: int | None", "+ rep_count: int | None",
            "+ avg_confidence: float | None", "+ quality_score: float | None",
            "+ flags_json: dict[str, Any] | None",
        ], [], color="schema", subtitulo="app.api.v1.sessions"),
        C("DownloadRequest", "DownloadRequest", "pydantic", [
            "+ url: HttpUrl", "+ quality: DownloadQuality = \"best\"",
        ], [], color="schema", subtitulo="app.api.v1.download"),
        C("DownloadResponse", "DownloadResponse", "pydantic", [
            "+ job_id: UUID", "+ status: str", "+ message: str",
        ], [], color="schema", subtitulo="app.api.v1.download"),
        C("StatusResponse", "StatusResponse", "pydantic", [
            "+ job_id: UUID", "+ status: str", "+ file_path: str | None",
            "+ error_message: str | None",
        ], [], color="schema", subtitulo="app.api.v1.download"),
        C("Base", "Base", "DeclarativeBase", [], [], color="orm", subtitulo="app.db.base"),
        C("UserORM", "UserORM", "ORM · users", [
            "+ id: UUID  {PK}", "+ email: str  {unique}", "+ created_at: datetime",
        ], [], color="orm", subtitulo="app.db.models"),
        C("SessionORM", "SessionORM", "ORM · sessions", [
            "+ id: UUID  {PK}", "+ user_id: UUID  {FK users.id, CASCADE}",
            "+ exercise_label: str", "+ started_at: datetime",
            "+ ended_at: datetime | None", "+ device_info: JSONB | None",
        ], [], color="orm", subtitulo="app.db.models"),
        C("SessionMetricORM", "SessionMetricORM", "ORM · session_metrics", [
            "+ id: UUID  {PK}", "+ session_id: UUID  {FK sessions.id, CASCADE}",
            "+ frame_index: int | None", "+ rep_count: int | None",
            "+ avg_confidence: float | None", "+ quality_score: float | None",
            "+ flags_json: JSONB | None", "+ created_at: datetime",
        ], [], color="orm", subtitulo="app.db.models"),
        C("VideoDownloadJobORM", "VideoDownloadJobORM", "ORM · video_download_jobs", [
            "+ id: UUID  {PK}", "+ celery_task_id: str | None", "+ url: str",
            "+ status: str = \"pending\"", "+ file_path: str | None",
            "+ error_message: str | None", "+ created_at, updated_at: datetime",
        ], [], color="orm", subtitulo="app.db.models"),
    ]
    R = Relacion
    rel = [
        R("PoseAnalysisResponse", "LandmarkPoint", "composicion", "landmarks,\nworld_landmarks", "1", "0..*"),
        R("UserORM", "Base", "herencia"),
        R("SessionORM", "Base", "herencia"),
        R("SessionMetricORM", "Base", "herencia"),
        R("VideoDownloadJobORM", "Base", "herencia"),
        R("UserORM", "SessionORM", "asociacion", "sessions / user", "1", "0..*", extra="arrowhead=none"),
        R("SessionORM", "SessionMetricORM", "composicion", "metrics (delete-orphan)", "1", "0..*"),
        R("SessionOut", "SessionORM", "dependencia", "«from_attributes»"),
        R("CreateSessionBody", "SessionORM", "dependencia", "«create»"),
        R("SessionMetricBody", "SessionMetricORM", "dependencia", "«create»"),
        R("StubLogin", "UserORM", "dependencia", "«create» si no existe"),
        R("DownloadRequest", "VideoDownloadJobORM", "dependencia", "«create»"),
        R("StatusResponse", "VideoDownloadJobORM", "dependencia", "«read»"),
    ]
    notas = [
        Nota("nota_pydantic", [
            "Toda clase «pydantic» hereda de pydantic.BaseModel.",
            "PoseStreamConfig es el primer mensaje (texto JSON)",
            "del cliente en /ws/pose-stream.",
        ]),
        Nota("nota_unified", [
            "UnifiedWsFrameV1 documenta y valida (pruebas) el contrato",
            "servidor → cliente; en ejecución se envía el dict de",
            "build_frame_payload_v1() más total_frames, preview, etc.",
            "knees usa la convención flexión = 180° − interno;",
            "PipelineTimingMs documenta el campo pipeline_ms.",
        ]),
        Nota("nota_orm", [
            "PostgreSQL opcional (DATABASE_URL). Las rutas de sesión,",
            "autenticación y descarga lo requieren; el análisis de",
            "pose en vivo y por video no persiste datos.",
        ]),
    ]
    rel += [
        R("nota_pydantic", "PoseStreamConfig", "nota"),
        R("nota_unified", "UnifiedWsFrameV1", "nota"),
        R("nota_orm", "Base", "nota"),
    ]
    paquetes = [
        Paquete("ws", "Contratos WebSocket y REST — app.models.schemas", [
            "PoseStreamConfig", "UnifiedWsFrameV1", "PipelineTimingMs", "PoseAnalysisResponse",
            "LandmarkPoint", "HealthResponse", "ExerciseClassifierConfig", "nota_pydantic", "nota_unified"], "#FFFDF5"),
        Paquete("dto", "Cuerpos y respuestas definidos en los routers — app.api.v1", [
            "StubLogin", "TokenResponse", "CreateSessionBody", "SessionOut", "SessionMetricBody",
            "DownloadRequest", "DownloadResponse", "StatusResponse"], "#FFFDF5"),
        Paquete("orm", "Modelos ORM (SQLAlchemy 2) — app.db", [
            "Base", "UserORM", "SessionORM", "SessionMetricORM", "VideoDownloadJobORM", "nota_orm"], "#F6FBF7"),
    ]
    return Diagrama(
        "clases_esquemas_persistencia",
        "Diagrama de clases — esquemas de datos (Pydantic) y persistencia (ORM)",
        clases, rel, notas, paquetes,
        invisibles=[("LandmarkPoint", "TokenResponse"), ("UnifiedWsFrameV1", "UserORM"),
                    ("HealthResponse", "DownloadResponse")],
    )


# ---------------------------------------------------------------------------
# (c) Cliente web appWeb (React + TypeScript)
# ---------------------------------------------------------------------------

def diagrama_cliente_web() -> Diagrama:
    C = Clase
    clases = [
        C("router", "router", "module", [
            "+ / → <Navigate to=\"/sustentacion\" replace>",
            "+ /sustentacion → SustentacionLayout  (interfaz principal)",
            "+ (sin prefijo) → AppLayout  (interfaz completa)",
            "+ login, sessions, profile, video-download → MvpRouteGuard",
        ], ["+ App(): JSX.Element  (RouterProvider)"], color="config", subtitulo="router.tsx"),
        C("SustentacionLayout", "SustentacionLayout", "layout", [
            "- TOKENS_CLAROS: Record<string, string>",
            "- ENLACES: Inicio, Demostración, Resultados",
        ], ["+ SustentacionLayout(): JSX.Element  (tema claro, enlace «Interfaz completa →»)"],
          color="comp", subtitulo="pages/sustentacion/SustentacionLayout.tsx"),
        C("AppLayout", "AppLayout", "layout", [], ["+ AppLayout(): JSX.Element  (tema oscuro, barra lateral)"],
          color="comp", subtitulo="layouts/AppLayout.tsx"),
        C("Portada", "Portada", "page", compacta=True, color="ref", subtitulo="/sustentacion (índice)"),
        C("Resultados", "Resultados", "page", compacta=True, color="ref", subtitulo="/sustentacion/resultados"),
        C("Demo", "Demo", "page", [], [
            "+ Demo(): JSX.Element  (ruta /sustentacion/demo)",
            "- claseEstado(estado: MetricStatus): string",
            "- formatearGrados(deg): string",
        ], color="comp", subtitulo="pages/sustentacion/Demo.tsx"),
        C("Home", "Home", "page", compacta=True, color="ref", subtitulo="/inicio"),
        C("BackendStatus", "BackendStatus", "page", compacta=True, color="ref", subtitulo="/backend-status"),
        C("ConnectionConfig", "ConnectionConfig", "page", compacta=True, color="ref", subtitulo="/settings/connection"),
        C("LiveAnalysis", "LiveAnalysis", "page", [
            "- exerciseMode: LiveExerciseMode  ('auto' | 'idle' | 'squat' | 'lunge')",
        ], ["+ LiveAnalysis(): JSX.Element  (ruta /live-analysis)"], color="comp",
          subtitulo="pages/LiveAnalysis/LiveAnalysis.tsx"),
        C("VideoAnalysis", "VideoAnalysis", "page", [], [
            "+ VideoAnalysis(): JSX.Element  (ruta /video-analysis)",
        ], color="comp", subtitulo="pages/VideoAnalysis/VideoAnalysis.tsx"),
        C("useLiveAnalysisSession", "useLiveAnalysisSession", "hook", [
            "+ ui: LiveAnalysisUiState",
            "+ videoRef: RefObject<HTMLVideoElement>",
            "+ overlayLandmarksRef: RefObject<LandmarkMap[] | null>",
            "- wsRef: RefObject<WebSocket | null>",
            "_u_MAX_IN_FLIGHT = 3, CAPTURE_HZ = 30, JPEG_QUALITY = 0.6",
        ], [
            "+ useLiveAnalysisSession(apiBase, captureOnly, forcedExerciseLabel)",
            "+ startCamera(): Promise<void>",
            "+ stopCamera(): void",
            "+ startTransmit(): Promise<void>",
            "+ stopTransmit(): void",
            "+ statusForLeft(ex) / statusForRight(ex): MetricStatus",
            "- sendOneFrame(): void",
        ], color="hook", subtitulo="hooks/useLiveAnalysisSession.ts"),
        C("LiveAnalysisUiState", "LiveAnalysisUiState", "interface", [
            "+ cameraOn, transmitting: boolean",
            "+ error: string | null",
            "+ knees: Record<string, unknown> | null",
            "+ leftDeg, rightDeg: number | null",
            "+ leftSeries, rightSeries: number[]",
            "+ exerciseLabel, repPhase: string",
            "+ repCount: number",
            "+ qualityFlags: string[]",
            "+ serverRttMs, serverPipelineTotalMs: number | null",
        ], [], color="tipo", subtitulo="hooks/useLiveAnalysisSession.ts"),
        C("useVideoAnalysis", "useVideoAnalysis", "hook", [
            "+ config: ConfigValues",
            "+ videoList: string[]",
            "+ summaryOpen: AnalysisSummary | null",
        ], [
            "+ refreshVideos(): Promise<void>",
            "+ handleStart(): Promise<void>",
            "+ handleDownloadCsv(): void",
            "+ handleConfigChange(...): void",
        ], color="hook", subtitulo="pages/VideoAnalysis/hooks/useVideoAnalysis.ts"),
        C("useVideoAnalysisSession", "useVideoAnalysisSession", "hook", [
            "+ ui: VideoAnalysisUiState",
            "- accRef: RefObject<VideoAnalysisAccumulator>",
            "- activeTransportRef: 'pose' | 'browser' | null",
        ], [
            "+ useVideoAnalysisSession(opts?: UseVideoAnalysisSessionOptions)",
            "+ start(params: SessionStartParams): Promise<string | null>",
            "+ stop(naturalCompletion: boolean): void",
            "+ sendPreviewTuning(previewFps, previewJpegQuality): void",
            "+ resetCsv(): void",
            "- processEvent(data): Promise<void>",
        ], color="hook", subtitulo="hooks/useVideoAnalysisSession.ts"),
        C("VideoAnalysisUiState", "VideoAnalysisUiState", "interface", [
            "+ running: boolean",
            "+ statusError: string | null",
            "+ previewDataUrl: string | null",
            "+ landmarks, worldLandmarks: LandmarkMap[] | null",
            "+ frameIndex: number; totalFrames: number | null",
            "+ leftDeg, rightDeg: number | null",
            "+ exerciseLabel, repPhase: string; repCount: number",
            "+ csvText: string; framesProcessed: number",
        ], [], color="tipo", subtitulo="hooks/useVideoAnalysisSession.ts"),
        C("SessionStartParams", "SessionStartParams", "type (unión)", [
            "+ mode: 'file' | 'server_camera' | 'browser_camera'",
            "+ apiBaseUrl: string",
            "+ videoFilename (file) / deviceIndex (server_camera)",
            "+ targetFps, includePreview, captureOnly, ...",
        ], [], color="tipo", subtitulo="hooks/useVideoAnalysisSession.ts"),
        C("VideoAnalysisAccumulator", "VideoAnalysisAccumulator", "class", [], [
            "+ addFrame(params): void",
            "+ buildSummary(): AnalysisSummary",
            "+ reset(): void",
        ], color="lib", subtitulo="lib/videoAnalysisAccumulator.ts"),
        C("AnalysisSummary", "AnalysisSummary", "interface", [
            "+ framesProcessed, framesWithBothKnees: number",
            "+ pctGood: number",
            "+ meanLeftDeg, meanRightDeg: number | null",
            "+ minLeftDeg, maxLeftDeg: number | null",
            "+ minRightDeg, maxRightDeg: number | null",
            "+ lastExerciseLabel: string; lastRepCount: number",
        ], [], color="tipo", subtitulo="lib/videoAnalysisAccumulator.ts"),
        C("PoseSkeletonCanvas", "PoseSkeletonCanvas", "component", [
            "+ landmarks?: LandmarkMap[] | null",
            "+ landmarksRef?: RefObject<LandmarkMap[] | null>",
            "+ mirrorHorizontal?: boolean",
            "+ contentAspect?: number | null",
            "+ smoothMotion?: boolean",
        ], [], color="comp", subtitulo="components/PoseSkeletonCanvas.tsx"),
        C("PreviewCanvas", "PreviewCanvas", "component", [
            "+ previewDataUrl: string | null",
            "+ landmarks, skeletonOverlay?, ...",
        ], [], color="comp", subtitulo="pages/VideoAnalysis/components/PreviewCanvas.tsx"),
        C("PoseSkeleton3DPanel", "PoseSkeleton3DPanel", "component", [
            "+ landmarks: LandmarkMap[] | null",
            "+ worldLandmarks: LandmarkMap[] | null",
        ], [], color="comp", subtitulo="components/pose3d/PoseSkeleton3DPanel.tsx (Three.js)"),
        C("DashboardPanel", "DashboardPanel", "component", [
            "+ leftDeg, rightDeg: number | null",
            "+ leftStatus, rightStatus: MetricStatus",
            "+ leftSeries, rightSeries: number[]",
            "+ repCount: number; repPhase, exerciseLabel: string",
        ], [], color="comp", subtitulo="components/DashboardPanel.tsx"),
        C("AnalysisSummaryDialog", "AnalysisSummaryDialog", "component", [
            "+ summary: AnalysisSummary | null",
            "+ open: boolean",
            "+ onClose: () => void",
        ], [], color="comp", subtitulo="components/AnalysisSummaryDialog.tsx"),
        C("poseWsPayload", "poseWsPayload", "module", [], [
            "+ poseWsErrorMessage(map): string | null",
            "+ parseLandmarksJson(raw): LandmarkMap[] | null",
            "+ parseKneesMap(raw) / parseDeg(v) / parseFrameIndex(raw)",
            "+ parseQualityFlags(raw) / pipelineTotalMs(map)",
        ], color="lib", subtitulo="lib/poseWsPayload.ts"),
        C("angleFormatter", "angleFormatter / angleRanges", "module", [
            "_u_squatFlexGoodMinDeg = 80, squatFlexGoodMaxDeg = 100",
        ], [
            "+ statusForKneeFlexionInContext(deg, isLeftLeg, exerciseLabel,",
            "      otherLegDeg): MetricStatus",
            "+ kneeFlexionMetricSublabelInContext(...): string",
        ], color="lib", subtitulo="lib/angleFormatter.ts · lib/angleRanges.ts"),
        C("MetricStatus", "MetricStatus", "type", [
            "'good' | 'warn' | 'bad' | 'neutral'",
        ], [], color="tipo", subtitulo="lib/metricStatus.ts"),
        C("ws_video", "/ws/video", "WebSocket", [], [
            "→ {analyze_pose, capture_only, forced_exercise_label}",
            "→ JPEG binario · ← payload v1 (JSON)",
        ], color="ext", subtitulo="backend · app.api.websocket.video"),
        C("ws_pose", "/ws/pose-stream", "WebSocket", [], [
            "→ PoseStreamConfig · ← stream_profile,",
            "    payload v1 + preview_jpeg_base64, stream_done",
        ], color="ext", subtitulo="backend · app.api.websocket.live_pose"),
        C("rest_gold", "GET /api/v1/analysis/gold-standard-videos", "REST", [], [
            "← {filenames: string[]}",
        ], color="ext", subtitulo="backend · app.api.v1.gold_standard_videos"),
    ]
    R = Relacion
    rel = [
        R("router", "SustentacionLayout", "composicion", "/sustentacion", "1", "1"),
        R("router", "AppLayout", "composicion", "interfaz completa", "1", "1"),
        R("SustentacionLayout", "Portada", "dependencia", "«route» índice"),
        R("SustentacionLayout", "Demo", "dependencia", "«route» demo"),
        R("SustentacionLayout", "Resultados", "dependencia", "«route» resultados"),
        R("SustentacionLayout", "AppLayout", "dependencia", "«link» /inicio", restringe=False),
        R("AppLayout", "Home", "dependencia"),
        R("AppLayout", "LiveAnalysis", "dependencia", "«route» live-analysis"),
        R("AppLayout", "VideoAnalysis", "dependencia", "«route» video-analysis"),
        R("AppLayout", "BackendStatus", "dependencia"),
        R("AppLayout", "ConnectionConfig", "dependencia"),
        R("Demo", "useLiveAnalysisSession", "dependencia"),
        R("Demo", "PoseSkeletonCanvas", "dependencia", "«render»"),
        R("LiveAnalysis", "useLiveAnalysisSession", "dependencia"),
        R("LiveAnalysis", "PoseSkeletonCanvas", "dependencia", "«render»"),
        R("LiveAnalysis", "DashboardPanel", "dependencia", "«render»"),
        R("useLiveAnalysisSession", "LiveAnalysisUiState", "composicion", "ui", "1", "1"),
        R("useLiveAnalysisSession", "poseWsPayload", "dependencia"),
        R("useLiveAnalysisSession", "angleFormatter", "dependencia"),
        R("useLiveAnalysisSession", "ws_video", "dependencia", "«WebSocket»"),
        R("VideoAnalysis", "useVideoAnalysis", "dependencia"),
        R("VideoAnalysis", "PreviewCanvas", "dependencia", "«render»"),
        R("VideoAnalysis", "PoseSkeleton3DPanel", "dependencia", "«render» (lazy)"),
        R("VideoAnalysis", "DashboardPanel", "dependencia", "«render»"),
        R("VideoAnalysis", "AnalysisSummaryDialog", "dependencia", "«render»"),
        R("PreviewCanvas", "PoseSkeletonCanvas", "dependencia", "«render»"),
        R("useVideoAnalysis", "useVideoAnalysisSession", "dependencia"),
        R("useVideoAnalysis", "rest_gold", "dependencia", "«fetch»"),
        R("useVideoAnalysisSession", "VideoAnalysisUiState", "composicion", "ui", "1", "1"),
        R("useVideoAnalysisSession", "VideoAnalysisAccumulator", "composicion", "accRef", "1", "1"),
        R("useVideoAnalysisSession", "SessionStartParams", "dependencia"),
        R("useVideoAnalysisSession", "poseWsPayload", "dependencia"),
        R("useVideoAnalysisSession", "ws_pose", "dependencia", "«WebSocket» file / server_camera"),
        R("useVideoAnalysisSession", "ws_video", "dependencia", "«WebSocket» browser_camera"),
        R("VideoAnalysisAccumulator", "AnalysisSummary", "dependencia", "«create»"),
        R("AnalysisSummaryDialog", "AnalysisSummary", "asociacion", "summary", None, "0..1"),
        R("angleFormatter", "MetricStatus", "dependencia", "«create»"),
    ]
    notas = [
        Nota("nota_rutas", [
            "Interfaz principal: / redirige a /sustentacion (tema claro).",
            "Demo usa useLiveAnalysisSession(apiBase, false, null):",
            "rodilla izquierda/derecha y asimetría bilateral |L − R|,",
            "rotulada «no interpretable» por debajo de 5°.",
            "La interfaz completa (/inicio, tema oscuro) conserva el",
            "análisis de video, el diagnóstico y la configuración.",
            "Layout → página: ruta hija (la ruta va en el subtítulo).",
        ]),
        Nota("nota_live", [
            "Análisis en vivo: getUserMedia → captura JPEG a 30 Hz con",
            "contrapresión (máx. 3 fotogramas sin respuesta) → /ws/video.",
            "El video se muestra en espejo solo por CSS; el JPEG se",
            "envía sin espejar y el overlay usa mirrorHorizontal.",
        ]),
        Nota("nota_overlay", [
            "Con smoothMotion = true se lee landmarksRef de forma",
            "imperativa (sin setState) e interpola entre poses.",
            "Si llega un payload sin landmarks se conserva el último.",
        ]),
        Nota("nota_estado", [
            "Estado por pierna (MetricStatus): sentadilla 80–100° de",
            "flexión = good; zancada distingue pierna delantera y",
            "trasera comparando con otherLegDeg.",
        ]),
    ]
    rel += [
        R("nota_rutas", "router", "nota"),
        R("nota_live", "useLiveAnalysisSession", "nota"),
        R("nota_overlay", "PoseSkeletonCanvas", "nota"),
        R("nota_estado", "angleFormatter", "nota"),
    ]
    paquetes = [
        Paquete("pages", "Páginas (pages/)", ["LiveAnalysis", "VideoAnalysis"], "#F6FBF7"),
        Paquete("hooks", "Hooks de sesión (contenedores)", ["useLiveAnalysisSession", "useVideoAnalysis", "useVideoAnalysisSession", "nota_live"], "#F7FAFE"),
        Paquete("tipos", "Tipos de estado", ["LiveAnalysisUiState", "VideoAnalysisUiState", "SessionStartParams", "AnalysisSummary", "MetricStatus"], "#FFFDF5"),
        Paquete("comp", "Componentes de presentación (components/)", ["PoseSkeletonCanvas", "PreviewCanvas", "PoseSkeleton3DPanel", "DashboardPanel", "AnalysisSummaryDialog", "nota_overlay"], "#F6FBF7"),
        Paquete("lib", "Utilidades (lib/)", ["poseWsPayload", "angleFormatter", "VideoAnalysisAccumulator", "nota_estado"], "#FAF7FC"),
        Paquete("back", "Backend (contratos)", ["ws_video", "ws_pose", "rest_gold"], "#FFFFFF"),
    ]
    return Diagrama(
        "clases_cliente_web",
        "Diagrama de clases — cliente web appWeb (rutas, páginas, hooks, componentes y contratos)",
        clases, rel, notas,
    )


DIAGRAMAS = [
    diagrama_vision_orquestacion,
    diagrama_vision_clasificacion,
    diagrama_api_servicios,
    diagrama_esquemas_persistencia,
    diagrama_cliente_web,
]


if __name__ == "__main__":
    for fabrica in DIAGRAMAS:
        d = fabrica()
        destino = AQUI / f"{d.archivo}.dot"
        destino.write_text(a_dot(d), encoding="utf-8")
        print(f"escrito {destino.name}")
