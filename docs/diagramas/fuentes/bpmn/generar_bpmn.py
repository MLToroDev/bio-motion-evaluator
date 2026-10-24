#!/usr/bin/env python3
"""
Genera los procesos BPMN 2.0 de Bio-Motion Evaluator (XML semántico + BPMN DI).

Cada paso se basa en el código, en la memoria o en el protocolo de validación:

- AS-IS (proceso actual, sin el sistema): ``docs/Formato_trabajo_de_grado.md``
  (Definición del problema, Descripción del Negocio, Antecedentes §2.3.3).

- Evaluación en vivo: ``appWeb/src/pages/sustentacion/Demo.tsx`` (interfaz principal),
  ``appWeb/src/hooks/useLiveAnalysisSession.ts`` y
  ``backend/app/api/websocket/video.py`` (``/ws/video``).
- Análisis de video: ``appWeb/src/hooks/useVideoAnalysisSession.ts``,
  ``appWeb/src/pages/VideoAnalysis/hooks/useVideoAnalysis.ts`` y
  ``backend/app/api/websocket/live_pose.py`` (``/ws/pose-stream``).
- Validación Nivel 2: ``docs/guias/protocolo_validacion_exactitud.md`` §2,
  ``validacion/datos/README.md`` y ``validacion/analisis/*.py``.

Uso::

    python3 docs/diagramas/fuentes/bpmn/generar_bpmn.py

Escribe los ``.bpmn`` junto a este script y comprueba que el XML es bien formado.
"""

from __future__ import annotations

import sys
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bpmn_lib import Diagrama  # noqa: E402

AQUI = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# (a) Evaluación goniométrica en vivo
# ---------------------------------------------------------------------------

def proceso_en_vivo() -> Diagrama:
    # Interfaz principal: /sustentacion/demo (pages/sustentacion/Demo.tsx), que reutiliza
    # useLiveAnalysisSession(apiBase, captureOnly=false, forcedExerciseLabel=null).
    d = Diagrama("Def_EvaluacionEnVivo", "Proceso de evaluación goniométrica en vivo", columnas=24,
                 col_w=125, row_h=150, vertical=True)
    d.piscina("P_Sesion", "Sesión de medición en vivo — appWeb (/sustentacion/demo)", [
        ("L_Evaluador", "Evaluador", 1),
        ("L_Cliente", "Cliente web (appWeb /sustentacion/demo · useLiveAnalysisSession)", 4),
    ], "Medición en vivo")
    d.piscina("P_Servidor", "Servidor de inferencia — FastAPI, WebSocket /ws/video", [
        ("L_Servidor", "", 4),
    ], "Inferencia por fotograma")
    e_err = d.error("Err_Camara", "Cámara no disponible")
    e_con = d.error("Err_Conexion", "Servidor no disponible")
    e_cfg = d.error("Err_Config", "Primer mensaje inválido")

    N = d.nodo
    EV, CL, SV = "L_Evaluador", "L_Cliente", "L_Servidor"
    GW = dict(etiqueta_v="arriba-derecha")
    # Evaluador
    N("ev_inicio", "startEvent", "Medición de rodilla solicitada", EV, 0, etiqueta_v="abajo")
    N("ev_abrir", "userTask", "Abrir «Demostración» y pulsar «Conectar cámara»", EV, 1)
    N("ev_ubicar", "userTask", "Colocarse de cuerpo entero, a 2–3 m y de perfil; pulsar «Iniciar medición»", EV, 5)
    N("ev_mover", "userTask", "Ejecutar el movimiento (p. ej. sentadilla)", EV, 10)
    N("ev_observar", "userTask", "Leer rodilla izquierda, rodilla derecha y asimetría bilateral", EV, 11)
    N("ev_detener", "userTask", "Pulsar «Detener medición»", EV, 12)
    N("ev_apagar", "userTask", "Pulsar «Apagar cámara»", EV, 21)
    N("ev_fin", "endEvent", "Medición finalizada", EV, 22, etiqueta_v="abajo")
    # Cliente web
    N("cl_camara", "serviceTask", "Solicitar permiso de cámara (getUserMedia, 640×480)", CL, 2)
    N("cl_gw_permiso", "exclusiveGateway", "¿Permiso concedido?", CL, 3, **GW)
    N("cl_err_camara", "task", "Mostrar error de cámara (usar https o localhost)", CL, 3, 1)
    N("cl_fin_camara", "endEvent", "Cámara no disponible", CL, 3, 2, evento="error", error_ref=e_err, etiqueta_v="abajo")
    N("cl_vista", "task", "Mostrar la vista previa en espejo (CSS)", CL, 4)
    N("cl_ws", "serviceTask", "Abrir WebSocket /ws/video (espera máx. 8 s)", CL, 6)
    N("cl_gw_con", "exclusiveGateway", "¿Conexión establecida?", CL, 7, **GW)
    N("cl_err_con", "task", "Mostrar «No se pudo conectar»", CL, 7, 1)
    N("cl_fin_con", "endEvent", "Servidor no disponible", CL, 7, 2, evento="error", error_ref=e_con, etiqueta_v="abajo")
    N("cl_init", "sendTask", "Enviar configuración inicial {analyze_pose: true}", CL, 8)
    N("cl_fork", "parallelGateway", "", CL, 9)
    N("cl_enviar", "sendTask", "Capturar y enviar fotograma JPEG (30 Hz, máx. 3 sin respuesta)", CL, 13, 3, bucle=True)
    N("cl_gw_bucle", "exclusiveGateway", "", CL, 10)
    N("cl_recibir", "receiveTask", "Recibir payload JSON del fotograma", CL, 11)
    N("cl_gw_error", "exclusiveGateway", "¿Mensaje con error?", CL, 12, **GW)
    N("cl_err_ws", "task", "Mostrar el error y detener la medición", CL, 12, 2)
    N("cl_fin_ws", "endEvent", "Medición interrumpida", CL, 13, 2, evento="terminate", etiqueta_v="abajo")
    N("cl_gw_pose", "exclusiveGateway", "¿Llegaron landmarks y ángulos?", CL, 13, **GW)
    N("cl_actualizar", "task", "Actualizar esqueleto 2D y lecturas de rodilla izquierda y derecha", CL, 14)
    N("cl_asimetria", "task", "Calcular asimetría bilateral |izq. − der.| y contrastarla con 5°", CL, 15)
    N("cl_sin_datos", "task", "Conservar el último esqueleto; lecturas «—»", CL, 14, 1)
    N("cl_gw_merge", "exclusiveGateway", "", CL, 16)
    N("cl_gw_activa", "exclusiveGateway", "¿Medición activa?", CL, 17, **GW)
    N("cl_join", "parallelGateway", "", CL, 18)
    N("cl_cerrar", "task", "Cerrar el WebSocket y reiniciar las lecturas", CL, 20)
    # Servidor (fila 0: alternativas; fila 1: flujo principal; fila 2: desconexión)
    N("sv_inicio", "startEvent", "Conexión WebSocket aceptada", SV, 6, 1, evento="message")
    N("sv_cfg", "receiveTask", "Recibir el primer mensaje (texto JSON)", SV, 8, 1)
    N("sv_gw_json", "exclusiveGateway", "¿JSON válido?", SV, 9, 1, **GW)
    N("sv_err_cfg", "sendTask", "Enviar error y cerrar (código 4000)", SV, 10, 0)
    N("sv_fin_cfg", "endEvent", "Mensaje inicial rechazado", SV, 11, 0, evento="error", error_ref=e_cfg)
    N("sv_flags", "task", "Leer opciones: analizar pose, solo captura y ejercicio forzado", SV, 10, 1)
    N("sv_gw_bucle", "exclusiveGateway", "", SV, 11, 1)
    N("sv_gw_evento", "eventBasedGateway", "", SV, 12, 1)
    N("sv_jpeg", "intermediateCatchEvent", "Fotograma JPEG recibido", SV, 13, 1, evento="message")
    N("sv_pose", "serviceTask", "Estimar la pose con MediaPipe (el motor se crea con el 1.er fotograma)", SV, 14, 1)
    N("sv_gw_pose", "exclusiveGateway", "¿Pose detectada?", SV, 15, 1, **GW)
    N("sv_sin_pose", "task", "Payload sin landmarks: knees = null, note «No se detectó ninguna pose»", SV, 16, 0)
    N("sv_angulos", "serviceTask", "Calcular ángulos de rodilla sobre world_landmarks", SV, 16, 1)
    N("sv_clasificar", "serviceTask", "Clasificar ejercicio y seguir repeticiones", SV, 17, 1)
    N("sv_gw_merge", "exclusiveGateway", "", SV, 18, 1)
    N("sv_enviar", "sendTask", "Filtrar landmarks por visibilidad y enviar payload v1", SV, 19, 1)
    N("sv_desconexion", "intermediateCatchEvent", "Cliente cerró la conexión", SV, 20, 3, evento="message", etiqueta_v="abajo")
    N("sv_fin", "endEvent", "Sesión de inferencia cerrada", SV, 21, 3, etiqueta_v="abajo")

    F = d.flujo
    F("ev_inicio", "ev_abrir")
    F("ev_abrir", "cl_camara")
    F("cl_camara", "cl_gw_permiso")
    f_si = F("cl_gw_permiso", "cl_vista", "Sí")
    F("cl_gw_permiso", "cl_err_camara", "No", condicion="permiso denegado o error de getUserMedia")
    d.nodos["cl_gw_permiso"].default = f_si.id
    F("cl_err_camara", "cl_fin_camara")
    F("cl_vista", "ev_ubicar")
    F("ev_ubicar", "cl_ws")
    F("cl_ws", "cl_gw_con")
    f_si = F("cl_gw_con", "cl_init", "Sí")
    F("cl_gw_con", "cl_err_con", "No", condicion="onerror o timeout de 8 s")
    d.nodos["cl_gw_con"].default = f_si.id
    F("cl_err_con", "cl_fin_con")
    F("cl_init", "cl_fork")
    F("cl_fork", "ev_mover")
    F("cl_fork", "cl_gw_bucle")
    F("cl_fork", "cl_enviar", salida="abajo")
    F("ev_mover", "ev_observar")
    F("ev_observar", "ev_detener")
    F("ev_detener", "cl_join")
    F("cl_enviar", "cl_join")
    F("cl_gw_bucle", "cl_recibir")
    F("cl_recibir", "cl_gw_error")
    f_no = F("cl_gw_error", "cl_gw_pose", "No")
    F("cl_gw_error", "cl_err_ws", "Sí", condicion="el payload trae error (distinto de sin_frame)")
    d.nodos["cl_gw_error"].default = f_no.id
    F("cl_err_ws", "cl_fin_ws")
    f_si = F("cl_gw_pose", "cl_actualizar", "Sí")
    F("cl_gw_pose", "cl_sin_datos", "No", condicion="landmarks vacíos o knees = null")
    d.nodos["cl_gw_pose"].default = f_si.id
    F("cl_actualizar", "cl_asimetria")
    F("cl_asimetria", "cl_gw_merge")
    F("cl_sin_datos", "cl_gw_merge", entrada="abajo")
    F("cl_gw_merge", "cl_gw_activa")
    f_si = F("cl_gw_activa", "cl_gw_bucle", "Sí", ruta="abajo", canal=225, salida="abajo", entrada="abajo")
    F("cl_gw_activa", "cl_join", "No", condicion="se pulsó «Detener medición» o el servidor cerró")
    d.nodos["cl_gw_activa"].default = f_si.id
    F("cl_join", "cl_cerrar")
    F("cl_cerrar", "ev_apagar")
    F("ev_apagar", "ev_fin")

    F("sv_inicio", "sv_cfg")
    F("sv_cfg", "sv_gw_json")
    f_si = F("sv_gw_json", "sv_flags", "Sí")
    F("sv_gw_json", "sv_err_cfg", "No", condicion="JSONDecodeError")
    d.nodos["sv_gw_json"].default = f_si.id
    F("sv_err_cfg", "sv_fin_cfg")
    F("sv_flags", "sv_gw_bucle")
    F("sv_gw_bucle", "sv_gw_evento")
    F("sv_gw_evento", "sv_jpeg")
    F("sv_gw_evento", "sv_desconexion", salida="abajo")
    F("sv_jpeg", "sv_pose")
    F("sv_pose", "sv_gw_pose")
    f_si = F("sv_gw_pose", "sv_angulos", "Sí")
    F("sv_gw_pose", "sv_sin_pose", "No", condicion="pose_landmarks vacío")
    d.nodos["sv_gw_pose"].default = f_si.id
    F("sv_angulos", "sv_clasificar")
    F("sv_clasificar", "sv_gw_merge")
    F("sv_sin_pose", "sv_gw_merge", entrada="arriba")
    F("sv_gw_merge", "sv_enviar")
    F("sv_enviar", "sv_gw_bucle", ruta="abajo", canal=228)
    F("sv_desconexion", "sv_fin")

    M = d.mensaje
    M("cl_ws", "sv_inicio", "Apertura")
    M("cl_init", "sv_cfg", "Configuración")
    M("cl_enviar", "sv_jpeg", "JPEG binario")
    M("sv_enviar", "cl_recibir", "Payload v1", dx_destino=-15)
    M("sv_err_cfg", "cl_recibir", "{error}", dx_destino=15)
    M("cl_cerrar", "sv_desconexion", "Cierre")

    A = d.anotacion
    A("an_lecturas", "Lecturas en pantalla: rodilla izquierda y derecha (flexión; 0° = extensión) con color por estado, "
      "asimetría bilateral y telemetría (RX/s, RTT, motor, fotograma). Con asimetría < 5° (piso de ruido) se rotula «no interpretable».",
      CL, 14.3, 2.2, ancho=118, alto=300, dx=0, dy=0, asociada_a="cl_asimetria")
    A("an_envio", "Bucle hasta «Detener medición»: un JPEG (calidad 0,6) sin espejar cada 1/30 s, si hay menos de 3 en vuelo.",
      CL, 9.55, 2.1, ancho=128, alto=190, dx=0, dy=0, asociada_a="cl_enviar")
    A("an_completa", "Interfaz completa (/live-analysis, tema oscuro): mismo hook y mismo servidor; añade el selector de "
      "ejercicio (forced_exercise_label) y el panel con pestañas de métricas, registro e histórico, con conteo de repeticiones.",
      CL, 0.1, 1.55, ancho=420, alto=120, dx=0, dy=0)
    A("an_angulos", "Fuente preferida: world_landmarks (metros, isótropo). flexión = 180° − ángulo interno (cadera, rodilla, tobillo).",
      SV, 15.55, 2.0, ancho=113, alto=200, dx=20, dy=0, asociada_a="sv_angulos")
    A("an_clasif", "Ventana de 45 fotogramas, clasificación con histéresis y bandera asymmetry_high si |L − R| / máx(L, R) > 18 %.",
      SV, 17.4, 2.0, ancho=113, alto=200, dx=20, dy=0, asociada_a="sv_clasificar")
    return d


# ---------------------------------------------------------------------------
# (b) Análisis de video (archivo del catálogo de referencia)
# ---------------------------------------------------------------------------

def proceso_video() -> Diagrama:
    d = Diagrama("Def_AnalisisVideo", "Proceso de análisis de video", columnas=23,
                 col_w=125, row_h=150, vertical=True)
    d.piscina("P_Cliente", "Análisis de video — appWeb (/video-analysis)", [
        ("L_Evaluador", "Evaluador", 1),
        ("L_Cliente", "Cliente web (useVideoAnalysis · useVideoAnalysisSession)", 4),
    ], "Análisis de video en el cliente")
    d.piscina("P_Servidor", "Servidor de inferencia — FastAPI", [
        ("L_Rest", "API REST /api/v1", 1),
        ("L_Ws", "WebSocket /ws/pose-stream", 3),
    ], "Procesamiento de video en el servidor")
    e_cat = d.error("Err_Catalogo", "Catálogo no disponible")
    e_con = d.error("Err_Conexion", "Servidor no disponible")
    e_cfg = d.error("Err_Config", "Configuración inválida")
    e_fue = d.error("Err_Fuente", "Video no disponible")
    e_pro = d.error("Err_Proceso", "Error de procesamiento")

    N = d.nodo
    EV, CL, RS, WS = "L_Evaluador", "L_Cliente", "L_Rest", "L_Ws"
    # Evaluador
    N("ev_inicio", "startEvent", "Análisis de video solicitado", EV, 0)
    N("ev_abrir", "userTask", "Abrir «Análisis de video»", EV, 1)
    N("ev_config", "userTask", "Elegir el video y configurar FPS, vista previa y ejercicio; pulsar «Iniciar»", EV, 5)
    N("ev_revisar", "userTask", "Revisar el resumen y descargar el CSV (opcional)", EV, 17)
    N("ev_fin", "endEvent", "Análisis completado", EV, 18)
    # Cliente web
    N("cl_cat", "serviceTask", "Solicitar el catálogo de videos (GET gold-standard-videos)", CL, 2, 1)
    N("cl_gw_cat", "exclusiveGateway", "¿Catálogo obtenido?", CL, 3, 1, etiqueta="arriba")
    N("cl_err_cat", "task", "Mostrar error de lista (HTTP o red)", CL, 4, 2)
    N("cl_fin_cat", "endEvent", "Catálogo no disponible", CL, 5, 2, evento="error", error_ref=e_cat)
    N("cl_lista", "task", "Mostrar la lista y preseleccionar el primer video", CL, 4, 1)
    N("cl_ws", "serviceTask", "Abrir WebSocket /ws/pose-stream", CL, 6, 1)
    N("cl_gw_con", "exclusiveGateway", "¿Conexión abierta?", CL, 7, 1, etiqueta="arriba")
    N("cl_err_con", "task", "Mostrar «No se pudo conectar (WebSocket)»", CL, 7, 2)
    N("cl_fin_con", "endEvent", "Servidor no disponible", CL, 7, 3, evento="error", error_ref=e_con, etiqueta="derecha")
    N("cl_cfg", "sendTask", "Enviar PoseStreamConfig (source = file, video_filename, target_fps…)", CL, 8, 1)
    N("cl_gw_bucle", "exclusiveGateway", "", CL, 9, 1)
    N("cl_gw_evento", "eventBasedGateway", "", CL, 10, 1)
    N("cl_msg", "intermediateCatchEvent", "Mensaje JSON recibido", CL, 11, 1, evento="message", etiqueta="abajo-izquierda", etiqueta_v="abajo-derecha")
    N("cl_cierre", "intermediateCatchEvent", "WebSocket cerrado", CL, 11.6, 0, evento="message", etiqueta="derecha", etiqueta_v="izquierda")
    N("cl_gw_tipo", "exclusiveGateway", "¿Tipo de mensaje?", CL, 12, 1, etiqueta="arriba-derecha")
    N("cl_frame", "task", "Acumular fotograma, CSV y series; actualizar vista previa, overlay y métricas", CL, 13, 1)
    N("cl_perfil", "task", "Registrar el perfil de procesamiento (stream_profile)", CL, 13, 2)
    N("cl_error", "task", "Detener y mostrar el error (statusError)", CL, 13, 3)
    N("cl_fin_error", "endEvent", "Análisis interrumpido", CL, 14, 3, evento="terminate", etiqueta_v="abajo")
    N("cl_gw_merge", "exclusiveGateway", "", CL, 14, 1)
    N("cl_resumen", "task", "Construir el resumen del análisis (AnalysisSummary)", CL, 15, 0)
    N("cl_dialogo", "task", "Mostrar el resumen en un diálogo y el aviso de fin", CL, 16, 0)
    # Servidor — REST
    N("rs_inicio", "startEvent", "Petición GET recibida", RS, 2, evento="message")
    N("rs_listar", "serviceTask", "Listar archivos de tests/assets/videos", RS, 3)
    N("rs_fin", "endEvent", "Lista enviada", RS, 4, evento="message")
    # Servidor — WebSocket
    N("ws_inicio", "startEvent", "Conexión aceptada", WS, 6, 1, evento="message")
    N("ws_cfg", "receiveTask", "Recibir PoseStreamConfig (primer mensaje)", WS, 8, 1)
    N("ws_gw_json", "exclusiveGateway", "¿JSON válido?", WS, 9, 1, etiqueta="abajo")
    N("ws_err_json", "task", "Cerrar la conexión (código 4000)", WS, 10, 0)
    N("ws_fin_json", "endEvent", "Configuración inválida", WS, 10.75, 0, evento="error", error_ref=e_cfg, etiqueta="derecha", etiqueta_v="abajo")
    N("ws_turno", "task", "Esperar turno (una sola sesión de pose-stream activa)", WS, 10, 1)
    N("ws_fuente", "serviceTask", "Abrir el video del catálogo (VideoSource)", WS, 11, 1)
    N("ws_gw_fuente", "exclusiveGateway", "¿Archivo y configuración válidos?", WS, 12, 1, etiqueta="abajo")
    N("ws_err_fuente", "sendTask", "Enviar {error} y cerrar (código 4000)", WS, 13, 0)
    N("ws_fin_fuente", "endEvent", "Video no disponible", WS, 13.75, 0, evento="error", error_ref=e_fue, etiqueta="derecha", etiqueta_v="abajo")
    N("ws_plan", "serviceTask", "Construir el perfil de procesamiento y crear el motor de análisis", WS, 13, 1)
    N("ws_perfil", "sendTask", "Enviar stream_profile", WS, 14, 1)
    N("ws_productor", "task", "Iniciar el hilo productor de fotogramas (cola de 2)", WS, 15, 1)
    N("ws_gw_bucle", "exclusiveGateway", "", WS, 16, 1)
    N("ws_tomar", "task", "Tomar el siguiente fotograma de la cola", WS, 17, 1)
    N("ws_gw_fin", "exclusiveGateway", "¿Fin del video?", WS, 18, 1, etiqueta="abajo")
    N("ws_done", "sendTask", "Enviar stream_done y cerrar (código 1000)", WS, 19, 0)
    N("ws_fin", "endEvent", "Video procesado", WS, 19.75, 0, etiqueta_v="abajo")
    N("ws_proceso", "serviceTask", "Reducir resolución, estimar pose y calcular ángulos (modo VIDEO)", WS, 19, 1)
    N("ws_borde", "boundaryEvent", "Error inesperado", WS, 19, 1, evento="error", adjunto_a="ws_proceso", etiqueta="abajo-izquierda", etiqueta_v="abajo")
    N("ws_enviar", "sendTask", "Codificar vista previa, enviar payload v1 y esperar al ritmo objetivo", WS, 20, 1)
    N("ws_err_proc", "sendTask", "Enviar {error} y cerrar (código 1011)", WS, 21, 2)
    N("ws_fin_proc", "endEvent", "Error de procesamiento", WS, 22, 2, evento="error", error_ref=e_pro, etiqueta_v="abajo")

    F = d.flujo
    F("ev_inicio", "ev_abrir")
    F("ev_abrir", "cl_cat", entrada="izquierda")
    F("cl_cat", "cl_gw_cat")
    f = F("cl_gw_cat", "cl_lista", "Sí")
    F("cl_gw_cat", "cl_err_cat", "No", condicion="respuesta HTTP no válida o error de red")
    d.nodos["cl_gw_cat"].default = f.id
    F("cl_err_cat", "cl_fin_cat")
    F("cl_lista", "ev_config")
    F("ev_config", "cl_ws")
    F("cl_ws", "cl_gw_con")
    f = F("cl_gw_con", "cl_cfg", "Sí")
    F("cl_gw_con", "cl_err_con", "No", condicion="onerror antes de abrir")
    d.nodos["cl_gw_con"].default = f.id
    F("cl_err_con", "cl_fin_con")
    F("cl_cfg", "cl_gw_bucle")
    F("cl_gw_bucle", "cl_gw_evento")
    F("cl_gw_evento", "cl_msg")
    F("cl_gw_evento", "cl_cierre", salida="arriba")
    F("cl_msg", "cl_gw_tipo")
    f = F("cl_gw_tipo", "cl_frame", "Fotograma")
    F("cl_gw_tipo", "cl_perfil", "stream_profile", condicion="el mensaje trae stream_profile", etiqueta_en="fin")
    F("cl_gw_tipo", "cl_error", "Error", condicion="el mensaje trae error (distinto de sin_frame)", etiqueta_en="fin")
    d.nodos["cl_gw_tipo"].default = f.id
    F("cl_frame", "cl_gw_merge")
    F("cl_perfil", "cl_gw_merge", entrada="abajo")
    F("cl_error", "cl_fin_error")
    F("cl_gw_merge", "cl_gw_bucle", ruta="arriba", canal=-75, salida="arriba", entrada="arriba")
    F("cl_cierre", "cl_resumen")
    F("cl_resumen", "cl_dialogo")
    F("cl_dialogo", "ev_revisar")
    F("ev_revisar", "ev_fin")

    F("rs_inicio", "rs_listar")
    F("rs_listar", "rs_fin")

    F("ws_inicio", "ws_cfg")
    F("ws_cfg", "ws_gw_json")
    f = F("ws_gw_json", "ws_turno", "Sí")
    F("ws_gw_json", "ws_err_json", "No", condicion="JSONDecodeError")
    d.nodos["ws_gw_json"].default = f.id
    F("ws_err_json", "ws_fin_json")
    F("ws_turno", "ws_fuente")
    F("ws_fuente", "ws_gw_fuente")
    f = F("ws_gw_fuente", "ws_plan", "Sí")
    F("ws_gw_fuente", "ws_err_fuente", "No", condicion="ValueError o FileNotFoundError")
    d.nodos["ws_gw_fuente"].default = f.id
    F("ws_err_fuente", "ws_fin_fuente")
    F("ws_plan", "ws_perfil")
    F("ws_perfil", "ws_productor")
    F("ws_productor", "ws_gw_bucle")
    F("ws_gw_bucle", "ws_tomar")
    F("ws_tomar", "ws_gw_fin")
    f = F("ws_gw_fin", "ws_proceso", "No")
    F("ws_gw_fin", "ws_done", "Sí", condicion="la cola entrega el fin de stream")
    d.nodos["ws_gw_fin"].default = f.id
    F("ws_done", "ws_fin")
    F("ws_proceso", "ws_enviar")
    F("ws_enviar", "ws_gw_bucle", ruta="arriba", canal=-75, salida="arriba", entrada="arriba")
    F("ws_borde", "ws_err_proc")
    F("ws_err_proc", "ws_fin_proc")

    M = d.mensaje
    M("cl_cat", "rs_inicio", "GET", dx_origen=-20, dx_destino=-20)
    M("rs_fin", "cl_cat", "{filenames}", dx_destino=20, etiqueta_lado="origen")
    M("cl_ws", "ws_inicio", "Apertura")
    M("cl_cfg", "ws_cfg", "Configuración inicial")
    M("ws_perfil", "cl_msg", "stream_profile", dx_origen=30, dx_destino=-16, etiqueta_lado="origen-abajo")
    M("ws_enviar", "cl_msg", "Payload v1", dx_origen=30, dx_destino=-11, etiqueta_lado="origen-abajo")
    M("ws_err_fuente", "cl_msg", "{error}", dx_destino=-6, etiqueta_lado="origen")
    M("ws_err_proc", "cl_msg", "{error}", dx_destino=-1, etiqueta_lado="origen")
    M("ws_err_json", "cl_cierre", "Cierre 4000", dx_destino=-10, etiqueta_lado="origen")
    M("ws_done", "cl_cierre", "stream_done y cierre 1000", dx_destino=10, etiqueta_lado="origen")

    A = d.anotacion
    A("an_catalogo", "El cliente no sube archivos: analiza un video del catálogo de referencia del servidor. "
      "La descarga por URL (/api/v1/download, Celery) es un flujo aparte que no alimenta este catálogo.",
      CL, 0.15, 2.05, ancho=270, alto=150, dx=0, dy=0)
    A("an_cierre", "stream_done se ignora; el fin se detecta al cerrarse el WebSocket. "
      "«DETENER» del evaluador cierra la conexión y también muestra el resumen si hubo fotogramas.",
      EV, 6.2, 0.05, ancho=130, alto=430, dx=0, dy=0, asociada_a="cl_cierre")
    A("an_plan", "Perfil según resolución × FPS nativos: reducción a 720/960 px, stride de inferencia y techo de FPS.",
      WS, 13.3, 2.0, ancho=115, alto=210, dx=22, dy=0, asociada_a="ws_plan")
    A("an_proceso", "flexión = 180° − interno sobre world_landmarks; payload con landmarks filtrados por visibilidad.",
      WS, 15.3, 0.05, ancho=115, alto=290, dx=0, dy=0, asociada_a="ws_proceso")
    for n in d.nodos.values():  # rótulos de compuertas: arriba a la derecha
        if n.tipo.endswith("Gateway"):
            n.etiqueta_v = "arriba-derecha"
    return d


# ---------------------------------------------------------------------------
# (c) Validación de exactitud — Nivel 2 (Tracker)
# ---------------------------------------------------------------------------

def proceso_validacion_nivel2() -> Diagrama:
    d = Diagrama("Def_ValidacionNivel2", "Proceso de validación de exactitud — Nivel 2", columnas=21,
                 col_w=190, row_h=150, tarea=(165, 105))
    d.piscina("P_Nivel2", "Validación de exactitud angular — Nivel 2 (video-goniometría manual con Tracker)", [
        ("L_Operador", "Investigador (operador de Tracker)", 2),
        ("L_Scripts", "Scripts de validación (validacion/analisis)", 2),
    ], "Validación Nivel 2")
    N = d.nodo
    OP, SC = "L_Operador", "L_Scripts"
    N("op_inicio", "startEvent", "Criterios del Nivel 2 pre-registrados en la bitácora", OP, 0)
    N("op_grabar", "userTask", "Grabar clip propio: una toma, plano sagital, 1920×1080, sentadillas lentas", OP, 1)
    N("sc_gw_exp", "exclusiveGateway", "", SC, 2)
    N("sc_exportar", "scriptTask", "Exportar la serie del sistema, los PNG rotulados y la plantilla de la sesión 1 (exportar_para_kinovea.py)", SC, 3)
    N("op_revisar", "userTask", "Revisar la flexión estimada por tramo en serie_sistema.csv", OP, 4)
    N("op_gw_paso", "exclusiveGateway", "¿n ≥ 5 en los tramos de interés?", OP, 5, etiqueta="arriba")
    N("op_paso", "userTask", "Fijar un paso menor (p. ej. 5) y anotarlo en la bitácora", OP, 5, 1)
    N("op_s1_abrir", "userTask", "Sesión 1: abrir frames/m0000.png como secuencia y verificar fotogramas y rótulos", OP, 6)
    N("op_s1_medir", "userTask", "Fijar la convención (interno o flexión) y medir cada fotograma con el transportador", OP, 7)
    N("sc_sortear", "scriptTask", "Sortear la sesión 2: ceil(0,33 · n) filas, semilla 20261023 (sortear_sesion2.py)", SC, 8)
    N("op_espera", "intermediateCatchEvent", "Han pasado al menos 48 h desde la sesión 1", OP, 9, evento="timer", duracion="PT48H")
    N("op_s2", "userTask", "Sesión 2: medir sesion2/s2_*.png sin consultar la sesión 1", OP, 10)
    N("sc_analizar", "scriptTask", "Analizar el Nivel 2: acuerdo intra-observador primero (analizar_nivel2.py)", SC, 11)
    N("sc_gw_intra", "exclusiveGateway", "¿MAE intra-observador ≤ 3,0°?", SC, 12, etiqueta="abajo")
    N("op_gw_rem", "exclusiveGateway", "¿Remedio elegido?", OP, 13, 1, etiqueta="izquierda")
    N("op_remedio", "userTask", "Remedio (a): medir tres veces cada punto y usar la mediana (sesiones 3 y 4)", OP, 14, 1)
    N("sc_reanalizar", "scriptTask", "Reanalizar con las sesiones 3 y 4: la referencia pasa a ser la mediana por fotograma (≥ 3 mediciones)", SC, 15, 1)
    N("sc_gw_merge", "exclusiveGateway", "", SC, 16)
    N("sc_acuerdo", "scriptTask", "Acuerdo sistema–Tracker: MAE ≤ 7,0°, ICC(2,1) ≥ 0,85; MAE por tramo solo con n ≥ 5", SC, 17)
    N("sc_informe", "scriptTask", "Escribir el informe y el veredicto (nivel2_acuerdo.md y figuras)", SC, 18)
    N("op_reportar", "userTask", "Reportar en la memoria el MAE intra-observador junto al acuerdo y el veredicto", OP, 19)
    N("op_fin", "endEvent", "Veredicto del Nivel 2 emitido", OP, 20)
    # Objetos de datos
    N("do_serie", "dataObjectReference", "Serie del sistema y metadatos", SC, 3, 1)
    N("do_frames", "dataObjectReference", "PNG y plantilla de la sesión 1", SC, 4.2, 1)
    N("do_s1", "dataObjectReference", "Mediciones de la sesión 1 y proyecto de Tracker", OP, 7.4, 1)
    N("do_s2", "dataObjectReference", "PNG y plantilla de la sesión 2", SC, 8, 1)
    N("do_res", "dataObjectReference", "Informe, resumen, pares y Bland-Altman", SC, 18, 1)
    d.nodos["sc_exportar"].datos_salida += ["do_serie", "do_frames"]
    d.nodos["op_s1_medir"].datos_salida += ["do_s1"]
    d.nodos["sc_sortear"].datos_salida += ["do_s2"]
    d.nodos["sc_informe"].datos_salida += ["do_res"]

    F = d.flujo
    F("op_inicio", "op_grabar")
    F("op_grabar", "sc_gw_exp")
    F("sc_gw_exp", "sc_exportar")
    F("sc_exportar", "op_revisar")
    F("op_revisar", "op_gw_paso")
    f = F("op_gw_paso", "op_s1_abrir", "Sí")
    F("op_gw_paso", "op_paso", "No", condicion="algún tramo de interés con n < 5")
    d.nodos["op_gw_paso"].default = f.id
    F("op_paso", "sc_gw_exp", ruta="abajo", canal=250, entrada="abajo")
    F("op_s1_abrir", "op_s1_medir")
    F("op_s1_medir", "sc_sortear")
    F("sc_sortear", "op_espera")
    F("op_espera", "op_s2")
    F("op_s2", "sc_analizar")
    F("sc_analizar", "sc_gw_intra")
    f = F("sc_gw_intra", "sc_gw_merge", "Sí")
    F("sc_gw_intra", "op_gw_rem", "No", condicion="MAE intra-observador > 3,0°", salida="arriba", entrada="abajo")
    d.nodos["sc_gw_intra"].default = f.id
    f = F("op_gw_rem", "op_remedio", "(a)")
    F("op_gw_rem", "sc_gw_merge", "(b) no concluyente", condicion="se eligió la salida (b)", salida="arriba", entrada="arriba", pasillo=-80, etiqueta_en="fin")
    d.nodos["op_gw_rem"].default = f.id
    F("op_remedio", "sc_reanalizar")
    F("sc_reanalizar", "sc_gw_merge", entrada="abajo")
    F("sc_gw_merge", "sc_acuerdo")
    F("sc_acuerdo", "sc_informe")
    F("sc_informe", "op_reportar")
    F("op_reportar", "op_fin")

    A = d.anotacion
    A("an_alinear", "Alinear siempre por índice de fotograma (frame_idx), nunca por marca de tiempo; el exportador no sobrescribe una plantilla con mediciones.",
      SC, 0.1, 1, ancho=330, alto=72, dy=20, asociada_a="sc_exportar")
    A("an_remedio", "La salida se elige antes de ver los datos y se prefiere (a), que se pasa al análisis con --sesiones-extra. Con (b), el Nivel 2 se declara no concluyente y la validación se apoya en el Nivel 1.",
      OP, 11.15, 0, ancho=560, alto=58, dy=8, asociada_a="op_gw_rem")
    A("an_veredicto", "Veredicto: «concluyente: cumple / no cumple los criterios», «condicionado al remedio (a)» o «no concluyente».",
      SC, 19.15, 1, ancho=300, alto=72, dy=15, asociada_a="sc_informe")
    return d


# ---------------------------------------------------------------------------
# (AS-IS) Valoración manual del rango de movimiento de rodilla, sin el sistema
# ---------------------------------------------------------------------------

def proceso_asis() -> Diagrama:
    """
    Proceso actual descrito en la memoria: Descripción del Negocio (fases valoración →
    preparación → ejecución; la valoración se omite por costo y por requerir un
    profesional), Definición del problema (costo, goniometría manual y su variabilidad,
    juicio cualitativo de un tercero) y Antecedentes §2.3.3 (evaluación funcional manual
    con Kinovea). El procedimiento de video-goniometría manual (tres referencias marcadas
    a mano, ángulo plano) es el descrito en el protocolo de validación, §2.1.
    """
    d = Diagrama("Def_AsIsValoracionManual", "Proceso AS-IS de valoración manual del rango de movimiento de rodilla",
                 columnas=20, col_w=125, row_h=150, vertical=True)
    d.piscina("P_AsIs", "Valoración funcional de rodilla sin el sistema (proceso actual)", [
        ("L_Evaluado", "Evaluado (deportista)", 2),
        ("L_Evaluador", "Evaluador (profesional)", 2),
        ("L_Herramienta", "Herramienta manual (goniómetro / video y Kinovea)", 2),
    ], "Valoración manual de rodilla")
    N = d.nodo
    EO, ER, HM = "L_Evaluado", "L_Evaluador", "L_Herramienta"
    GW = dict(etiqueta_v="arriba-derecha")
    N("eo_inicio", "startEvent", "Necesidad de entrenar: fase de valoración funcional", EO, 0)
    N("eo_gw_acceso", "exclusiveGateway", "¿Accede a una valoración profesional?", EO, 1, **GW)
    N("eo_omitir", "task", "Omitir la valoración funcional", EO, 2, 1)
    N("eo_generica", "task", "Calentar con una rutina de movilidad genérica, «a ciegas»", EO, 3, 1)
    N("eo_pagar", "task", "Solicitar y pagar la consulta profesional", EO, 2)
    N("eo_asistir", "task", "Asistir a la consulta presencial", EO, 3)
    N("er_gw_instr", "exclusiveGateway", "¿Instrumento de medición?", ER, 4, **GW)
    N("eo_posicion", "task", "Adoptar y mantener la posición de medición", EO, 5)
    N("er_alinear", "userTask", "Alinear el goniómetro con cadera, rodilla y tobillo", ER, 6)
    N("hm_gonio", "manualTask", "Goniómetro universal: el ángulo se lee en la escala", HM, 7)
    N("er_leer", "userTask", "Leer y anotar el ángulo", ER, 8)
    N("er_grabar", "userTask", "Grabar en video al evaluado mientras ejecuta el movimiento", ER, 9, 1)
    N("hm_kinovea", "task", "Kinovea: abrir el video y avanzar al fotograma de interés", HM, 10, 1)
    N("er_marcar", "userTask", "Marcar a mano las tres referencias (cadera, rodilla, tobillo)", ER, 11, 1)
    N("hm_angulo", "task", "Kinovea: calcular el ángulo plano entre los dos brazos", HM, 12, 1)
    N("er_gw_merge", "exclusiveGateway", "", ER, 13)
    N("er_interpretar", "userTask", "Interpretar la medida (juicio cualitativo del profesional)", ER, 14)
    N("er_comunicar", "userTask", "Comunicar los hallazgos al evaluado", ER, 15)
    N("eo_adaptar", "task", "Adaptar el calentamiento según las indicaciones", EO, 16)
    N("eo_gw_merge", "exclusiveGateway", "", EO, 17)
    N("eo_entrenar", "task", "Ejecutar el entrenamiento (ejercicios de alta carga)", EO, 18)
    N("eo_fin", "endEvent", "Entrenamiento realizado", EO, 19, etiqueta_v="abajo")

    F = d.flujo
    F("eo_inicio", "eo_gw_acceso")
    f = F("eo_gw_acceso", "eo_pagar", "Sí")
    F("eo_gw_acceso", "eo_omitir", "No", condicion="costo o falta de un profesional disponible")
    d.nodos["eo_gw_acceso"].default = f.id
    F("eo_omitir", "eo_generica")
    F("eo_generica", "eo_gw_merge", entrada="abajo")
    F("eo_pagar", "eo_asistir")
    F("eo_asistir", "er_gw_instr")
    f = F("er_gw_instr", "eo_posicion", "Goniómetro")
    F("er_gw_instr", "er_grabar", "Video", condicion="video-goniometría manual (Kinovea)")
    d.nodos["er_gw_instr"].default = f.id
    F("eo_posicion", "er_alinear")
    F("er_alinear", "hm_gonio")
    F("hm_gonio", "er_leer")
    F("er_leer", "er_gw_merge")
    F("er_grabar", "hm_kinovea")
    F("hm_kinovea", "er_marcar")
    F("er_marcar", "hm_angulo")
    F("hm_angulo", "er_gw_merge", entrada="abajo")
    F("er_gw_merge", "er_interpretar")
    F("er_interpretar", "er_comunicar")
    F("er_comunicar", "eo_adaptar")
    F("eo_adaptar", "eo_gw_merge")
    F("eo_gw_merge", "eo_entrenar")
    F("eo_entrenar", "eo_fin")

    A = d.anotacion
    A("an_acceso", "Barrera de costo y de atención presencial: la valoración funcional suele omitirse.",
      ER, 0.3, 0.1, ancho=260, alto=80, asociada_a="eo_gw_acceso")
    A("an_gonio", "Goniometría manual: error típico ≈ 3,4° en flexión de rodilla (Mehta et al., 2017).",
      HM, 5.4, 1.08, ancho=135, alto=150, asociada_a="hm_gonio")
    A("an_kinovea", "Video-goniometría manual 2D, la que usa la Facultad de Educación Física (§ 2.3.3).",
      HM, 8.0, 0.08, ancho=135, alto=135, asociada_a="hm_kinovea")
    A("an_variab", "Concordancia entre evaluadores limitada: límites de acuerdo > 18° con otros instrumentos.",
      ER, 14.3, 1.08, ancho=135, alto=150, asociada_a="er_interpretar")
    return d


DIAGRAMAS = {
    "proceso_asis_valoracion_manual": proceso_asis,
    "proceso_evaluacion_en_vivo": proceso_en_vivo,
    "proceso_analisis_video": proceso_video,
    "proceso_validacion_nivel2": proceso_validacion_nivel2,
}


def main() -> int:
    for nombre, fabrica in DIAGRAMAS.items():
        texto = fabrica().xml()
        xml.dom.minidom.parseString(texto.encode("utf-8"))  # bien formado o excepción
        (AQUI / f"{nombre}.bpmn").write_text(texto, encoding="utf-8")
        print(f"escrito {nombre}.bpmn (XML bien formado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
