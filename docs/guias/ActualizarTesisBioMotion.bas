Attribute VB_Name = "ActualizarTesisBioMotion"
'==============================================================================
' Bio-Motion Evaluator — macro de corrección documental (Word)
' Archivo: docs/guias/ActualizarTesisBioMotion.bas
'
' USO:
'   1. Abre tu .docx del trabajo de grado.
'   2. Alt+F11 → Archivo → Importar archivo → selecciona este .bas
'   3. Ejecuta: ActualizarTesisBioMotion
'   4. Guarda copia antes (Ctrl+Shift+S) — la macro modifica el documento activo.
'   5. Al finalizar: Actualizar tabla de contenido (clic derecho TOC → Actualizar).
'
' Requiere: Microsoft Word con macros habilitadas.
'==============================================================================

Option Explicit

Private Const SEP As String = vbCrLf

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
        vbYesNo + vbQuestion, "Bio-Motion — Actualizar tesis")
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
    AgregarNotaDetalleHU

    Application.ScreenUpdating = True
    MsgBox "Correcciones automáticas aplicadas." & SEP & SEP & _
           "REVISE MANUALMENTE:" & SEP & _
           "1) Tablas con numeración vieja en índice de tablas (Tabla 11–26)." & SEP & _
           "2) Inserte § «Detalle de historias de usuario» desde docs/Formato_trabajo_de_grado.md si falta." & SEP & _
           "3) Actualice tabla de contenido y campos." & SEP & _
           "4) Compruebe diagramas y figuras.", vbInformation, "Bio-Motion — Listo"
    Exit Sub

ErrHandler:
    Application.ScreenUpdating = True
    MsgBox "Error " & Err.Number & ": " & Err.Description, vbCritical, "Bio-Motion — Error"
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

    ' Criterios genéricos HU-04 (si aún existen)
    ReplaceAll "Cuando: 	selecciono un video" & vbTab & "Espero:	que el sistema procese el archivo correctamente", _
               "Cuando:	selecciono un video .mp4, .mov, .avi, .mkv o .webm válido" & vbTab & _
               "Espero:	recibir frames con stream_done y resumen con maxLeftDeg, maxRightDeg, minLeftDeg, minRightDeg, pctGood, lastRepCount, lastExerciseLabel y lastQualityFlags"
    ReplaceAll "Cuando:	finaliza el análisis" & vbTab & "Espero:	recibir un resumen del desempeño", _
               "Cuando:	el archivo tiene extensión no permitida (p. ej. .wmv)" & vbTab & _
               "Espero:	rechazo con mensaje que enumere .mp4, .mov, .avi, .mkv, .webm"
End Sub

Private Sub ReplaceAll(ByVal findText As String, ByVal replaceText As String)
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
    t.Cell(1, 2).Range.Text = nombre
    t.Cell(2, 2).Range.Text = idHu
    If t.Rows.Count >= 5 Then
        t.Cell(4, 2).Range.Text = como
        t.Cell(5, 2).Range.Text = quiero
    End If
    If t.Rows.Count >= 6 Then t.Cell(6, 2).Range.Text = para
    Dim r As Long
    For r = 1 To t.Rows.Count
        If InStr(1, Normalizar(t.Cell(r, 1).Range.Text), "CRITERIOS", vbTextCompare) > 0 Then
            If r < t.Rows.Count And t.Rows(r + 1).Cells.Count >= 1 Then
                t.Cell(r + 1, 1).Range.Text = criterios
            ElseIf t.Rows(r).Cells.Count >= 2 Then
                t.Cell(r, 2).Range.Text = criterios
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
    If BuscarTexto("Örücü") Is Nothing Then
        InsertarAntesDe "11.	BITÁCORA", _
            "Örücü, S., Erdağı, K., Işık, B., Özbay, E., & Osmanoğlu, U. Ö. (2025). Azure Kinect for joint range of motion analysis: A validity and reliability evaluation in elite female weightlifters. PLOS ONE, 20(11), e0334890. https://doi.org/10.1371/journal.pone.0334890" & SEP & SEP & _
            "Sabo, A., Mittal, N., Deshpande, A., Clarke, H., & Taati, B. (2023). Automated, vision-based goniometry and range of motion calculation in individuals with suspected Ehlers-Danlos syndromes/generalized hypermobility spectrum disorders: A comparison of pose-estimation libraries to goniometric measurements. IEEE Journal of Translational Engineering in Health and Medicine, 12, 140–150. https://doi.org/10.1109/JTEHM.2023.3327691" & SEP & SEP
    End If
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
    rngReplace.Text = newText & SEP
End Sub

Private Sub InsertarAntesDe(ByVal anchor As String, ByVal texto As String)
    Dim rng As Range
    Set rng = BuscarTexto(anchor)
    If rng Is Nothing Then Exit Sub
    rng.InsertBefore texto & SEP
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
