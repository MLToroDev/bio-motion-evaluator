Attribute VB_Name = "ActualizarTesisBioMotion"
'==============================================================================
' Bio-Motion Evaluator — macro de corrección documental (Word)
' Archivo: docs/guias/ActualizarTesisBioMotion.bas
'
' USO:
'   1. Abre tu .docx del trabajo de grado.
'   2. Alt+F11 → si ya importó antes, elimine el módulo «ActualizarTesisBioMotion» viejo
'   3. Archivo → Importar archivo → selecciona este .bas
'      (error «too many continuations»: use esta versión; no mezcle con copia antigua)
'   4. Ejecuta: ActualizarTesisBioMotion
'   5. Guarda copia antes (Ctrl+Shift+S) — la macro modifica el documento activo.
'   6. Al finalizar: Actualizar tabla de contenido (clic derecho TOC → Actualizar).
'
' Requiere: Microsoft Word con macros habilitadas.
'==============================================================================

Option Explicit

Private Const SEP As String = vbCrLf
Private Const WD_FIND_MAX As Long = 255   ' Límite de Word para Find.Text / Replacement.Text

'--- Punto de entrada principal -------------------------------------------------
Public Sub ActualizarTesisBioMotion()
    Dim resp As VbMsgBoxResult
    resp = MsgBox( _
        "Se aplicarán correcciones al documento ACTIVO:" & SEP & _
        "• Sprint 2 / HU-03 (elimina texto copiado del Sprint 1)" & SEP & _
        "• Sprint 1 (HU-01, HU-02 + BH-01)" & SEP & _
        "• Resultados (7 HU, sin HU-12)" & SEP & _
        "• Backlog, referencias, títulos y criterios binarios" & SEP & SEP & _
        "¿Desea continuar? (recomendado: guardar copia antes)", _
        vbYesNo + vbQuestion, "Bio-Motion - Actualizar tesis")
    If resp <> vbYes Then Exit Sub

    Application.ScreenUpdating = False
    On Error GoTo ErrHandler

    AplicarReemplazosGlobales
    CorregirFilasTablaBacklog
    ReemplazarSprint1Historias
    ReemplazarSprint2Completo
    ReemplazarSprint3HU04
    RenombrarExtensionesSprint4a6
    ReemplazarSprint6Pruebas
    InsertarAntecedentesValidacion
    InsertarReferenciasAsesor
    NormalizarTitulosCapitulo6
    ActualizarIndiceDeTablas
    AgregarNotaDetalleHU

    Application.ScreenUpdating = True
    MsgBox "Correcciones automáticas aplicadas." & SEP & SEP & _
           "REVISE MANUALMENTE:" & SEP & _
           "1) Inserte § «Detalle de historias de usuario» desde docs/Formato_trabajo_de_grado.md si falta." & SEP & _
           "2) Actualice tabla de contenido y campos (clic derecho TOC)." & SEP & _
           "3) Compruebe números de página del índice de tablas." & SEP & _
           "4) Compruebe diagramas y figuras.", vbInformation, "Bio-Motion - Listo"
    Exit Sub

ErrHandler:
    Application.ScreenUpdating = True
    MsgBox "Error " & Err.Number & ": " & Err.Description & SEP & SEP & _
           "Sugerencia: ejecute SoloCorregirSprint2 o corrija la sección indicada manualmente.", _
           vbCritical, "Bio-Motion - Error"
End Sub

'--- Reemplazos de texto en todo el documento ---------------------------------
Private Sub AplicarReemplazosGlobales()
    Dim reps As Variant
    Dim i As Long

    reps = Array( _
        Array("12 historias de usuario definidas y trazadas (HU-01 a HU-12); 5 cerradas, 4 en curso y 3 planificadas.", _
              "7 historias de usuario en la Tabla 10 del product backlog (HU-01 a HU-07), más extensiones de producto (cliente React, sesiones, JWT, descarga, 2D/3D) alineadas sobre todo al Sprint 4."), _
        Array("pendiente profundizar contraste estadístico con goniometría manual en muestra amplia.", _
              "el contraste estadístico con goniómetro manual corresponde a la HU-06 y no consta ejecutado en el estado documentado a abril de 2026."), _
        Array("Historia de usuario: HU-3 — Análisis en vivo", _
              "Historia de usuario: HU-03 — Análisis en vivo"), _
        Array("Tabla 15 Historia de usuario HU-01: Análisis biomecánico en tiempo real", _
              "Tabla 15 Historia de usuario HU-03: Análisis biomecánico en tiempo real"), _
        Array("Como deportista quiero ver si el backend está disponible antes de analizar" & vbTab & "2" & vbTab, _
              "Como deportista quiero ver si el backend está disponible antes de analizar" & vbTab & "1" & vbTab) _
    )

    For i = LBound(reps) To UBound(reps)
        ReplaceAll CStr(reps(i)(0)), CStr(reps(i)(1))
    Next i

    ' Criterios genéricos HU-04 (reemplazo corto; detalle completo va en tabla vía ReplaceTablaHU)
    ReplaceAll "Espero:	que el sistema procese el archivo correctamente", _
               "Espero:	recibo stream_done y resumen con maxLeftDeg, maxRightDeg, pctGood (pasa/no pasa)"
    ReplaceAll "Espero:	recibir un resumen del desempeño", _
               "Espero:	rechazo si la extensión no es .mp4, .mov, .avi, .mkv o .webm"
End Sub

' Find/Reemplazar solo admite 255 caracteres; textos largos usan Range.
Private Sub ReplaceAll(ByVal findText As String, ByVal replaceText As String)
    If Len(findText) = 0 Then Exit Sub
    If Len(findText) > WD_FIND_MAX Or Len(replaceText) > WD_FIND_MAX Then
        ReplaceAllPorRango findText, replaceText
        Exit Sub
    End If
    With ActiveDocument.Content.Find
        .ClearFormatting
        .Replacement.ClearFormatting
        .Text = findText
        .Replacement.Text = replaceText
        .Forward = True
        .Wrap = wdFindContinue
        .Format = False
        .MatchCase = False
        .MatchWholeWord = False
        .MatchWildcards = False
        .Execute Replace:=wdReplaceAll
    End With
End Sub

Private Sub ReplaceAllPorRango(ByVal findText As String, ByVal replaceText As String)
    Dim rng As Range
    Dim n As Long
    n = 0
    Do
        Set rng = BuscarTexto(findText)
        If rng Is Nothing Then Exit Do
        EstablecerTextoRango rng, replaceText
        n = n + 1
        If n > 300 Then Exit Do
    Loop
End Sub

' Escribe en un Range sin límite de 255 (por trozos).
Private Sub EstablecerTextoRango(ByVal rng As Range, ByVal texto As String)
    Dim i As Long
    Dim parte As String
    If rng Is Nothing Then Exit Sub
    rng.Text = ""
    If Len(texto) = 0 Then Exit Sub
    For i = 1 To Len(texto) Step WD_FIND_MAX
        parte = Mid$(texto, i, WD_FIND_MAX)
        rng.InsertAfter parte
    Next i
End Sub

Private Sub EstablecerTextoCelda(ByVal celda As Cell, ByVal texto As String)
    EstablecerTextoRango celda.Range, texto
End Sub

'--- Corrige Sprint de HU-01 y observaciones HU-04/HU-05 en Tabla 10 -----------
Private Sub CorregirFilasTablaBacklog()
    Dim t As Table
    Dim r As Long, c As Long
    Dim cellText As String

    For Each t In ActiveDocument.Tables
        If InStr(1, TablaTexto(t), "Product Backlog", vbTextCompare) > 0 _
           Or InStr(1, TablaTexto(t), "Id HU", vbTextCompare) > 0 Then
            For r = 1 To t.Rows.Count
                cellText = Normalizar(t.Cell(r, 1).Range.Text)
                If cellText Like "HU-01*" Then
                    BuscarCeldaSprint t, r, "1"
                ElseIf cellText Like "HU-04*" Then
                    PonerObservacionFila t, r, _
                        "VideoAnalysisPage; API gold_standard_videos; mensaje stream_done; acumulador VideoAnalysisAccumulator (appWeb)"
                ElseIf cellText Like "HU-05*" Then
                    PonerObservacionFila t, r, "iot/esp32-cam, iot/raspberry-pi/stream.py"
                End If
            Next r
        End If
    Next t
End Sub

Private Sub BuscarCeldaSprint(ByRef t As Table, ByVal rowIdx As Long, ByVal sprintVal As String)
    Dim c As Long
    For c = 1 To t.Rows(rowIdx).Cells.Count
        If InStr(1, Normalizar(t.Cell(rowIdx, c).Range.Text), "HU-0", vbTextCompare) = 0 Then
            If IsNumeric(Left$(Trim$(t.Cell(rowIdx, c).Range.Text), 1)) _
               Or Trim$(t.Cell(rowIdx, c).Range.Text) Like "[1-6]" Then
                t.Cell(rowIdx, c).Range.Text = sprintVal
                Exit Sub
            End If
        End If
    Next c
    ' Fallback: columna 3 típica de plantilla
    If t.Rows(rowIdx).Cells.Count >= 3 Then t.Cell(rowIdx, 3).Range.Text = sprintVal
End Sub

Private Sub PonerObservacionFila(ByRef t As Table, ByVal rowIdx As Long, ByVal texto As String)
    If t.Rows(rowIdx).Cells.Count > 0 Then
        t.Cell(rowIdx, t.Rows(rowIdx).Cells.Count).Range.Text = texto
    End If
End Sub

Private Function TablaTexto(ByRef t As Table) As String
    TablaTexto = Normalizar(t.Range.Text)
End Function

Private Function Normalizar(ByVal s As String) As String
    Normalizar = Replace(Replace(Trim$(s), Chr$(7), ""), Chr$(13), " ")
End Function

'--- Sprint 1: HU-01, HU-02 (usuario) — no «configurar entorno» como HU ----------
Private Sub ReemplazarSprint1Historias()
    ReplaceBetweenAnchors _
        "Historia de usuario: HU-01 — Configuración del entorno.", _
        "Historia de usuario: HU-02 — Verificación cliente-servidor", _
        "Historia de usuario: HU-01 — Disponibilidad del backend." & SEP & _
        "Ítem de backlog técnico: BH-01 — Configuración del monorepo (Tabla 11)." & SEP & SEP & _
        "Ver criterios binarios en la sección «Detalle de historias de usuario» (HU-01)."

    ReplaceTablaHU _
        "Tabla 12 Historia de usuario HU-01: Configuración del entorno de desarrollo", _
        "HU-01", "Disponibilidad del backend antes de analizar", _
        "deportista", _
        "saber si el servidor está disponible antes de iniciar un análisis", _
        "evitar errores de conexión", _
        "Cuando:	el backend está activo y la URL es correcta" & vbTab & _
        "Espero:	GET /api/v1/health responde 200 y la pantalla muestra estado OK (binario: pasa / no pasa)" & vbCr & _
        "Cuando:	el backend está caído o la URL es incorrecta" & vbTab & _
        "Espero:	la pantalla muestra fallo y no confunde «sin respuesta» con «análisis completado»"

    ReplaceTablaHU _
        "Tabla 13 Entregables del Sprint 1", _
        "HU-02", "Configuración de la URL base del servidor", _
        "usuario", _
        "configurar la URL base del servidor", _
        "que REST y WebSocket usen el mismo host", _
        "Cuando:	guardo una URL válida" & vbTab & _
        "Espero:	las peticiones REST y el WebSocket usan ese host (pasa / no pasa)" & vbCr & _
        "Cuando:	la URL está vacía o mal formada" & vbTab & _
        "Espero:	validación que impide guardar o muestra error explícito"
End Sub

'--- Sprint 2: reemplazo completo (corrige copia del Sprint 1) ------------------
Private Sub ReemplazarSprint2Completo()
    Dim bloque As String
    bloque = "Objetivo del sprint: implementar el primer flujo de valor biomecánico en tiempo real (HU-03): captura de video, inferencia MediaPipe BlazePose en FastAPI, flexión bilateral de rodilla, WebSocket /ws/pose-stream y presentación en Flutter con overlay (visibility ≥ 0,5), métricas y manejo de errores." & SEP & _
             "Este sprint no replica Sprint 1 (salud/URL), no incluye análisis por archivo (Sprint 3 / HU-04) ni cliente React (extensión Sprint 3–4)." & SEP & SEP

    InsertarAntesDe "6.4.2.", bloque

    ReplaceTablaHU _
        "Tabla 15 Historia de usuario HU-03: Análisis biomecánico en tiempo real", _
        "HU-03", "Análisis en vivo con retroalimentación de rodillas", _
        "deportista", _
        "analizar mi movimiento en vivo con retroalimentación de rodillas", _
        "adaptar mi calentamiento con datos objetivos", _
        "Cuando:	hay conexión estable y pose_ok es true" & vbTab & _
        "Espero:	cada fotograma incluye knees.left_knee_flexion_angle_deg y knees.right_knee_flexion_angle_deg cuando son computables (pasa / no pasa)" & vbCr & _
        "Cuando:	pose_ok es false" & vbTab & _
        "Espero:	UI muestra «sin pose» y no presenta ángulos como válidos" & vbCr & _
        "Cuando:	quality_flags contiene asymmetry_high" & vbTab & _
        "Espero:	panel muestra alerta de asimetría no ambigua" & vbCr & _
        "Cuando:	se pierde el WebSocket a mitad del ejercicio" & vbTab & _
        "Espero:	estado desconectado; al reconectar se reinicia análisis y PoseStreamConfig" & vbCr & _
        "Cuando:	permisos de cámara denegados o iluminación insuficiente" & vbTab & _
        "Espero:	análisis no inicia o pose_ok false con mensaje accionable" & vbCr & _
        "Regla overlay:	esqueleto solo con landmarks recibidos (visibility ≥ 0,5); ver docs/spec/websocket-pose-stream.md"
End Sub

'--- Sprint 3: criterios HU-04 ------------------------------------------------
Private Sub ReemplazarSprint3HU04()
    ReplaceTablaHU _
        "Tabla 17 Historia de usuario HU-04: Análisis de movimiento desde archivo", _
        "HU-04", "Análisis de video gold standard con resumen por sesión", _
        "investigador", _
        "analizar un video de referencia en el servidor", _
        "obtener un resumen cuantitativo comparable al análisis en vivo", _
        "Cuando:	selecciono un video .mp4, .mov, .avi, .mkv o .webm válido" & vbTab & _
        "Espero:	recibo stream_done true y resumen con framesProcessed, maxLeftDeg, maxRightDeg, minLeftDeg, minRightDeg, pctGood, lastRepCount, lastExerciseLabel, lastQualityFlags (pasa / no pasa)" & vbCr & _
        "Cuando:	la extensión no está permitida (p. ej. .wmv)" & vbTab & _
        "Espero:	rechazo con mensaje que enumere extensiones válidas" & vbCr & _
        "Cuando:	se corta la red antes de stream_done" & vbTab & _
        "Espero:	estado interrumpido y framesProcessed coherente con lo acumulado"
End Sub

'--- Sprints 4–5: las HU-06…HU-10 del Word son extensiones, no Tabla 10 -------
Private Sub RenombrarExtensionesSprint4a6()
    ReplaceAll "Historia de usuario: HU-06 — Autenticación", "Extensión de producto (Sprint 4): Autenticación JWT — no es HU-06 de la Tabla 10"
    ReplaceAll "Historia de usuario: HU-07 — Gestión de sesiones", "Extensión de producto (Sprint 4): Sesiones PostgreSQL"
    ReplaceAll "Historia de usuario: HU-08 — Descarga de videos", "Extensión de producto (Sprint 4): Descarga de videos (Celery)"
    ReplaceAll "Historia de usuario: HU-09 — Visualización avanzada", "Extensión de producto (Sprint 4): Visualización 2D/3D de la pose"
    ReplaceAll "Historia de usuario: HU-10 — Integración IoT", "Historia de usuario: HU-05 — Cámara IoT (Tabla 10)"
    ReplaceAll "ID HISTORIA" & vbTab & "HU-06" & vbCr, "ID (extensión)" & vbTab & "EXT-Auth" & vbCr
    ReplaceAll "ID HISTORIA" & vbTab & "HU-07" & vbCr, "ID (extensión)" & vbTab & "EXT-Sesiones" & vbCr
    ReplaceAll "ID HISTORIA" & vbTab & "HU-08" & vbCr, "ID (extensión)" & vbTab & "EXT-Descarga" & vbCr
    ReplaceAll "ID HISTORIA" & vbTab & "HU-09" & vbCr, "ID (extensión)" & vbTab & "EXT-2D3D" & vbCr
    ReplaceAll "ID HISTORIA" & vbTab & "HU-10" & vbCr, "ID HISTORIA" & vbTab & "HU-05" & vbCr
End Sub

'--- Sprint 6: HU-11 pruebas → BH-02; HU-06/07 según Tabla 10 -----------------
Private Sub ReemplazarSprint6Pruebas()
    ReplaceAll "Historia de usuario: HU-11 — Pruebas del sistema", "Ítem de backlog técnico: BH-02 — Ejecución de matriz de pruebas (§ 6.10.1)"
    ReplaceAll "Tabla 26 Historia de usuario HU-11: Ejecución de pruebas del sistema", "Tabla 26 Backlog técnico BH-02: Ejecución de pruebas del sistema"
    ReplaceAll "ID HISTORIA" & vbTab & "HU-11", "ID BH" & vbTab & "BH-02"
    ReplaceAll "NOMBRE DE LA HISTORIA" & vbTab & "Ejecución de pruebas del sistema", "NOMBRE DEL ÍTEM" & vbTab & "Ejecución de matriz de pruebas funcionales"
    ReplaceAll "Como:	evaluador" & vbCr & "Quiero:	ejecutar pruebas del sistema", "Como:	equipo de desarrollo" & vbCr & "Quiero:	ejecutar la matriz de pruebas § 6.10.1"
    ReplaceAll "Cuando: 	se ejecutan pruebas" & vbTab & "Espero:	obtener resultados documentados", _
               "Cuando:	se ejecuta la matriz PF-01 a PF-08" & vbTab & "Espero:	cada caso con resultado Pasa o No pasa y evidencia trazable"
End Sub

'--- Rellena tabla institucional de HU por título de tabla --------------------
Private Sub ReplaceTablaHU(ByVal tituloTabla As String, ByVal idHu As String, _
    ByVal nombre As String, ByVal como As String, ByVal quiero As String, _
    ByVal para As String, ByVal criterios As String)

    Dim rng As Range
    Dim t As Table

    Set rng = BuscarTexto(tituloTabla)
    If rng Is Nothing Then Exit Sub

    Set rng = rng.Next(wdTable, wdForward)
    If rng Is Nothing Then Exit Sub
    If rng.Tables.Count = 0 Then Exit Sub

    Set t = rng.Tables(1)
    On Error Resume Next
    ' Plantilla institucional: fila 1 = nombre, 2 = ID, 4 = Como, 5 = Quiero, 6 = Para
    EstablecerTextoCelda t.Cell(1, 2), nombre
    EstablecerTextoCelda t.Cell(2, 2), idHu
    If t.Rows.Count >= 5 Then
        EstablecerTextoCelda t.Cell(4, 2), como
        EstablecerTextoCelda t.Cell(5, 2), quiero
    End If
    If t.Rows.Count >= 6 Then EstablecerTextoCelda t.Cell(6, 2), para
    Dim r As Long
    For r = 1 To t.Rows.Count
        If InStr(1, Normalizar(t.Cell(r, 1).Range.Text), "CRITERIOS", vbTextCompare) > 0 Then
            If r < t.Rows.Count And t.Rows(r + 1).Cells.Count >= 1 Then
                EstablecerTextoCelda t.Cell(r + 1, 1), criterios
            ElseIf t.Rows(r).Cells.Count >= 2 Then
                EstablecerTextoCelda t.Cell(r, 2), criterios
            End If
            Exit For
        End If
    Next r
    On Error GoTo 0
End Sub

'--- Antecedentes + referencias ------------------------------------------------
Private Sub InsertarAntecedentesValidacion()
    Dim buscar As String
    Dim insertar As String
    buscar = "permitiendo ahora una goniometría digital precisa en dispositivos móviles."
    insertar = buscar & " Estudios recientes comparan estimación de ángulos por visión frente al goniómetro manual con correlaciones altas (Örücü et al., 2025; Sabo et al., 2023, con MediaPipe entre las bibliotecas evaluadas), lo que fundamenta la HU-06 de validación metrológica de este proyecto."
    ReplaceAll buscar, insertar
End Sub

Private Sub InsertarReferenciasAsesor()
    Dim ref1 As String, ref2 As String
    If Not BuscarTexto("Orucu") Is Nothing Then Exit Sub
    If Not BuscarTexto("Örücü") Is Nothing Then Exit Sub
    ref1 = "Orucu, S., Erdagi, K., Isik, B., Ozbay, E., & Osmanoglu, U. O. (2025). Azure Kinect for joint range of motion analysis. PLOS ONE, 20(11), e0334890. https://doi.org/10.1371/journal.pone.0334890"
    ref2 = "Sabo, A., Mittal, N., Deshpande, A., Clarke, H., & Taati, B. (2023). Automated, vision-based goniometry (MediaPipe vs goniometer). IEEE J Transl Eng Health Med, 12, 140-150. https://doi.org/10.1109/JTEHM.2023.3327691"
    InsertarAntesDe "11.	BITÁCORA", ref1 & SEP & SEP & ref2 & SEP & SEP
    InsertarAntesDe "REFERENCIAS", ref1 & SEP & SEP & ref2 & SEP & SEP
End Sub

'--- Títulos capítulo 6: estilo oración, sin punto final en encabezados -------
Private Sub NormalizarTitulosCapitulo6()
    Dim reps As Variant
    Dim i As Long
    reps = Array( _
        Array("PLANIFICACIÓN DEL SPRINT", "Planificación del sprint"), _
        Array("DISEÑO DEL SISTEMA", "Diseño del sistema"), _
        Array("PLAN DE PRUEBAS", "Plan de pruebas"), _
        Array("DESPLIEGUE DEL SISTEMA", "Despliegue del sistema"), _
        Array("PROPUESTA DE SOLUCIÓN", "Propuesta de solución"), _
        Array("Diagrama de clases.", "Diagrama de clases"), _
        Array("Diagrama entidad relación.", "Diagrama entidad-relación"), _
        Array("Tareas asociadas y ejecutadas.", "Tareas asociadas y ejecutadas"), _
        Array("Manual de Usuario", "Manual de usuario"), _
        Array("Manual de Instalación", "Manual de instalación") _
    )
    For i = LBound(reps) To UBound(reps)
        ReplaceAll CStr(reps(i)(0)), CStr(reps(i)(1))
    Next i
End Sub

'--- Índice de tablas y pies «Tabla N …» (cap. 6) ------------------------------
' Sin Array() gigante: VBA limita a 25 continuaciones (_) por procedimiento al importar.
Private Sub ActualizarIndiceDeTablas()
    ReplaceAll "Tabla 27 Historia de usuario HU-06:", "Historia de usuario HU-06:"
    ReplaceAll "Tabla 28 Historia de usuario HU-07:", "Historia de usuario HU-07:"
    IndiceTablasReemplazos10a19
    IndiceTablasReemplazos20a26
    CorregirNumeracionTablas27a31
End Sub

Private Sub IndiceTablasReemplazos10a19()
    ReplaceAll "Tabla 11 Backlog técnico (BH): tareas de ingeniería sin formato de historia de usuario.", "Tabla 11 Backlog técnico (BH-01, BH-02)"
    ReplaceAll "Tabla 12 Historia de usuario HU-01: Configuración del entorno de desarrollo", "Tabla 12 Historia de usuario HU-01: Disponibilidad del backend"
    ReplaceAll "Tabla 12 Historia de usuario HU-01: Configuración del entorno", "Tabla 12 Historia de usuario HU-01: Disponibilidad del backend"
    ReplaceAll "Tabla 13 Entregables del Sprint 1", "Tabla 13 Historia de usuario HU-02: Configuración de URL del servidor"
    ReplaceAll "Tabla 13 Historia de usuario HU-02: Configuración de la URL base del servidor", "Tabla 13 Historia de usuario HU-02: Configuración de URL del servidor"
    ReplaceAll "Tabla 14 Historia de usuario HU-02: Configuración de URL del servidor", "Tabla 14 Entregables del Sprint 1"
    ReplaceAll "Tabla 15 Historia de usuario HU-01: Análisis biomecánico en tiempo real", "Tabla 15 Historia de usuario HU-03: Análisis en vivo con retroalimentación de rodillas"
    ReplaceAll "Tabla 15 Historia de usuario HU-03: Análisis biomecánico en tiempo real", "Tabla 15 Historia de usuario HU-03: Análisis en vivo con retroalimentación de rodillas"
    ReplaceAll "Tabla 16 Historia de usuario HU-03: Análisis en vivo con retroalimentación de rodillas", "Tabla 16 Entregables del Sprint 2"
    ReplaceAll "Tabla 17 Historia de usuario HU-04: Análisis de movimiento desde archivo", "Tabla 17 Historia de usuario HU-04: Análisis por video gold standard"
    ReplaceAll "Tabla 17 Historia de usuario HU-03: Análisis en vivo con retroalimentación de rodillas", "Tabla 17 Historia de usuario HU-04: Análisis por video gold standard"
    ReplaceAll "Tabla 18 Historia de usuario HU-04: Análisis por video gold standard", "Tabla 18 Entregables del Sprint 3"
    ReplaceAll "Tabla 19 Entregables del Sprint 2 — módulo web y documentación", "Tabla 18 Entregables del Sprint 3"
    ReplaceAll "Tabla 19 Entregables del Sprint 2", "Tabla 18 Entregables del Sprint 3"
    ReplaceAll "Tabla 19 Extensión de producto: cliente web React", "Tabla 19 Extensión de producto: cliente web React (Sprint 3–4)"
End Sub

Private Sub IndiceTablasReemplazos20a26()
    ReplaceAll "Tabla 20 Historia de usuario HU-06", "Tabla 20 Extensión de producto: Autenticación de usuarios"
    ReplaceAll "Tabla 21 Historia de usuario HU-07", "Tabla 21 Extensión de producto: Registro de sesiones de análisis"
    ReplaceAll "Tabla 22 Historia de usuario HU-08", "Tabla 22 Extensión de producto: Descarga de videos de análisis"
    ReplaceAll "Tabla 23 Historia de usuario HU-09", "Tabla 23 Extensión de producto: Visualización 2D/3D de la pose"
    ReplaceAll "Tabla 24 Historia de usuario HU-10: Integración IoT", "Tabla 24 Historia de usuario HU-05: Cámara IoT"
    ReplaceAll "Tabla 24 Historia de usuario HU-10: Cámara IoT", "Tabla 24 Historia de usuario HU-05: Cámara IoT"
    ReplaceAll "Tabla 24 Historia de usuario HU-05: Cámara IoT frente al backend", "Tabla 24 Historia de usuario HU-05: Cámara IoT"
    ReplaceAll "Tabla 25 Entregables del Sprint — integración IoT y pruebas de streaming", "Tabla 25 Entregables Sprint 5 (IoT)"
    ReplaceAll "Tabla 26 Historia de usuario HU-11: Ejecución de pruebas del sistema", "Tabla 26 Backlog técnico BH-02: Matriz de pruebas funcionales"
    ReplaceAll "Tabla 26 Historia de usuario HU-11: Ejecución de pruebas", "Tabla 26 Backlog técnico BH-02: Matriz de pruebas funcionales"
    ReplaceAll "Tabla 26 Backlog técnico BH-02: Ejecución de matriz de pruebas funcionales", "Tabla 26 Backlog técnico BH-02: Matriz de pruebas funcionales"
End Sub

' Segunda «Tabla 26» en índice (Comparativa) → 27…31 en cascada, o apunta a Tabla 27 existente
Private Sub CorregirNumeracionTablas27a31()
    If BuscarTexto("Tabla 26 Comparativa técnica") Is Nothing Then Exit Sub
    If BuscarTexto("Tabla 26 Backlog técnico BH-02") Is Nothing Then Exit Sub

    If Not BuscarTexto("Tabla 27 Comparativa técnica") Is Nothing Then
        If Not BuscarTexto("Tabla 28 Casos de prueba funcional del sistema") Is Nothing Then
            ReplaceAll "Tabla 30 Matriz de trazabilidad: funcionalidades, módulos y especificaciones", "Tabla 31 Matriz de trazabilidad: funcionalidades, módulos y especificaciones"
            ReplaceAll "Tabla 29 Evaluación de características de calidad del sistema (ISO/IEEE)", "Tabla 30 Evaluación de características de calidad del sistema (ISO/IEEE)"
            ReplaceAll "Tabla 28 Métricas de rendimiento: objetivos y resultados observados", "Tabla 29 Métricas de usabilidad: objetivos y resultados observados"
            ReplaceAll "Tabla 27 Casos de prueba funcional del sistema", "Tabla 28 Casos de prueba funcional del sistema"
        End If
        ReplaceAll "Tabla 26 Comparativa técnica: Flutter Web vs. React + Vite", "Tabla 27 Comparativa técnica: Flutter Web vs. React + Vite"
        Exit Sub
    End If

    ReplaceAll "Tabla 30 Matriz de trazabilidad: funcionalidades, módulos y especificaciones", "Tabla 31 Matriz de trazabilidad: funcionalidades, módulos y especificaciones"
    ReplaceAll "Tabla 30 Matriz de trazabilidad", "Tabla 31 Matriz de trazabilidad"
    ReplaceAll "Tabla 29 Evaluación de características de calidad del sistema (ISO/IEEE)", "Tabla 30 Evaluación de características de calidad del sistema (ISO/IEEE)"
    ReplaceAll "Tabla 28 Métricas de rendimiento: objetivos y resultados observados", "Tabla 29 Métricas de rendimiento: objetivos y resultados observados"
    ReplaceAll "Tabla 27 Casos de prueba funcional del sistema", "Tabla 28 Casos de prueba funcional del sistema"
    ReplaceAll "Tabla 26 Comparativa técnica: Flutter Web vs. React + Vite", "Tabla 27 Comparativa técnica: Flutter Web vs. React + Vite"
End Sub

'--- Nota para pegar detalle normativo desde el repo ---------------------------
Private Sub AgregarNotaDetalleHU()
    Dim nota As String
    nota = "[NOTA EDITORIAL — eliminar tras pegar contenido]" & SEP & _
           "Inserte aquí la sección «Detalle de historias de usuario: reglas de negocio del motor, criterios de aceptación verificables y flujos alternativos» desde docs/Formato_trabajo_de_grado.md (después de la Tabla 10 / BH)." & SEP
    If BuscarTexto("Detalle de historias de usuario: reglas de negocio") Is Nothing Then
        InsertarAntesDe "6.3.	PLANIFICACIÓN DEL SPRINT 1", nota
        InsertarAntesDe "6.3.	Planificación del sprint 1", nota
    End If
End Sub

'--- Utilidades de rango --------------------------------------------------------
Private Sub ReplaceBetweenAnchors(ByVal startAnchor As String, ByVal endAnchor As String, ByVal newText As String)
    Dim rngStart As Range, rngEnd As Range, rngReplace As Range
    Set rngStart = BuscarTexto(startAnchor)
    Set rngEnd = BuscarTexto(endAnchor)
    If rngStart Is Nothing Or rngEnd Is Nothing Then Exit Sub
    If rngEnd.Start <= rngStart.Start Then Exit Sub
    Set rngReplace = ActiveDocument.Range(rngStart.Start, rngEnd.Start)
    EstablecerTextoRango rngReplace, newText & SEP
End Sub

Private Sub InsertarAntesDe(ByVal anchor As String, ByVal texto As String)
    Dim rng As Range
    Dim insRng As Range
    Dim bloque As String
    Dim i As Long
    Dim parte As String

    Set rng = BuscarTexto(anchor)
    If rng Is Nothing Then Exit Sub

    bloque = texto & SEP
    Set insRng = ActiveDocument.Range(rng.Start, rng.Start)

    If Len(bloque) <= WD_FIND_MAX Then
        insRng.InsertBefore bloque
        Exit Sub
    End If

    ' InsertBefore también falla con cadenas muy largas: trocear de atrás hacia adelante
    For i = Len(bloque) To 1 Step -WD_FIND_MAX
        parte = Mid$(bloque, i, WD_FIND_MAX)
        insRng.InsertBefore parte
    Next i
End Sub

Private Function BuscarTexto(ByVal texto As String) As Range
    Dim rng As Range
    Set rng = ActiveDocument.Content
    With rng.Find
        .ClearFormatting
        .Text = texto
        .Forward = True
        .Wrap = wdFindStop
        .Format = False
        .MatchCase = False
        .Execute
    End With
    If rng.Find.Found Then
        Set BuscarTexto = rng
    Else
        Set BuscarTexto = Nothing
    End If
End Function

'--- Solo índice de tablas y pies Tabla 10–31 -----------------------------------
Public Sub SoloActualizarIndiceDeTablas()
    Application.ScreenUpdating = False
    ActualizarIndiceDeTablas
    Application.ScreenUpdating = True
    MsgBox "Títulos del índice de tablas y pies «Tabla N» actualizados (10–31)." & SEP & _
           "Actualice campos/TOC y revise números de página.", vbInformation
End Sub

'--- Solo reemplazos de títulos (ejecución parcial) ----------------------------
Public Sub SoloNormalizarTitulos()
    NormalizarTitulosCapitulo6
    MsgBox "Títulos del capítulo 6 normalizados.", vbInformation
End Sub

'--- Solo Sprint 2 (si el resto ya lo actualizó) ------------------------------
Public Sub SoloCorregirSprint2()
    Application.ScreenUpdating = False
    ReemplazarSprint2Completo
    ReplaceAll "Configurar el entorno base del proyecto con backend y estructura de repositorio", _
               "analizar mi movimiento en vivo con retroalimentación de rodillas"
    ReplaceAll "Que el proyecto pueda ejecutarse sin errores siguiendo la guía SETUP", _
               "cada fotograma con pose_ok true incluye ángulos de rodilla o UI muestra sin pose"
    Application.ScreenUpdating = True
    MsgBox "Sprint 2 / HU-03 corregido. Revise Tabla 15.", vbInformation
End Sub
