Attribute VB_Name = "CorregirTablasPendientes"
'==============================================================================
' Bio-Motion — correcciones pendientes en Word (auditoría word.txt / cap. 6)
' Archivo: docs/guias/CorregirTablasPendientesTesis.bas
'
' USO:
'   1. Abra el .docx del trabajo de grado (guardar copia antes).
'   2. Alt+F11 → Archivo → Importar → este .bas
'      (puede convivir con ActualizarTesisBioMotion.bas; nombres de módulo distintos)
'   3. Ejecutar: CorregirTablasPendientesTesis
'   4. Actualice TOC / índice de tablas (clic derecho → Actualizar campos).
'
' Corrige:
'   • Pie Tabla 18 (Sprint 3) mal numerado como Tabla 19
'   • HU-06 / HU-07 sin prefijo «Tabla N» en Sprint 6
'   • Pie Tabla 25 (Sprint 5 IoT)
'   • BH-02: referencia § 6.10.1 (no § 6.8.1) en matriz de pruebas
'   • Tabla 29: título «Métricas de usabilidad» (no rendimiento)
'   • Índice: segunda «Tabla 26» y desfase 27–31 respecto al cuerpo
'==============================================================================

Option Explicit

Private Const SEP As String = vbCrLf
Private Const WD_FIND_MAX As Long = 255

Public Sub CorregirTablasPendientesTesis()
    Dim resp As VbMsgBoxResult
    resp = MsgBox( _
        "Se aplicarán las correcciones PENDIENTES al documento ACTIVO:" & SEP & _
        "• Tabla 18 entregables Sprint 3 (pie mal como Tabla 19)" & SEP & _
        "• HU-06 / HU-07 sin «Tabla 27/28»" & SEP & _
        "• Índice tablas 26–31 y título Tabla 29 usabilidad" & SEP & _
        "• BH-02 § 6.10.1 y pie Tabla 25 IoT" & SEP & SEP & _
        "¿Continuar? (recomendado: copia de seguridad antes)", _
        vbYesNo + vbQuestion, "Bio-Motion - Pendientes tablas")
    If resp <> vbYes Then Exit Sub

    Application.ScreenUpdating = False
    On Error GoTo ErrHandler

    CorregirPieTabla18Sprint3
    CorregirSprint6HistoriasSinTabla
    CorregirPieTabla25IoT
    CorregirReferenciaBH02Matriz
    CorregirTituloTabla29Usabilidad
    CorregirIndiceTablas26a31

    Application.ScreenUpdating = True
    MsgBox "Correcciones pendientes aplicadas." & SEP & SEP & _
           "Revise el índice de tablas (actualizar campos) y los números de página.", _
           vbInformation, "Bio-Motion - Pendientes listo"
    Exit Sub

ErrHandler:
    Application.ScreenUpdating = True
    MsgBox "Error " & Err.Number & ": " & Err.Description, vbCritical, "Bio-Motion - Pendientes"
End Sub

'--- Sprint 3: entregables deben ser Tabla 18, no Tabla 19 ------------------
Private Sub CorregirPieTabla18Sprint3()
    ReplaceAll "Tabla 19 Entregables del Sprint 2 — módulo web y documentación", _
               "Tabla 18 Entregables del Sprint 3"
    ReplaceAll "Tabla 19 Entregables del Sprint 2", _
               "Tabla 18 Entregables del Sprint 3"
End Sub

'--- Sprint 6: narrativa HU-06/07 sin pie de tabla numerado --------------------
Private Sub CorregirSprint6HistoriasSinTabla()
    ReplaceAll "Tabla 27 Historia de usuario HU-06:", "Historia de usuario HU-06:"
    ReplaceAll "Tabla 28 Historia de usuario HU-07:", "Historia de usuario HU-07:"
End Sub

'--- Sprint 5 IoT -------------------------------------------------------------
Private Sub CorregirPieTabla25IoT()
    ReplaceAll "Tabla 25 Entregables del Sprint — integración IoT y pruebas de streaming", _
               "Tabla 25 Entregables Sprint 5 (IoT)"
End Sub

'--- Tabla 11 / backlog: matriz de pruebas en § 6.10.1, no § 6.8.1 ------------
Private Sub CorregirReferenciaBH02Matriz()
    ReplaceAll "Matriz § 6.8.1 con resultado Pasa/No pasa por caso; anexos B–C actualizados", _
               "Matriz § 6.10.1 con resultado Pasa/No pasa por caso; anexos B–C actualizados"
    ReplaceAll "Matriz § 6.8.1 con resultado Pasa/No pasa por caso", _
               "Matriz § 6.10.1 con resultado Pasa/No pasa por caso"
    ReplaceAll "Matriz § 6.8.1 con resultado", _
               "Matriz § 6.10.1 con resultado"
End Sub

'--- Tabla 29: métricas de usabilidad (ISO 25010 usabilidad) ------------------
Private Sub CorregirTituloTabla29Usabilidad()
    ReplaceAll "Tabla 29 Métricas de rendimiento: objetivos y resultados observados", _
               "Tabla 29 Métricas de usabilidad: objetivos y resultados observados"
    ReplaceAll "Tabla 28 Métricas de rendimiento: objetivos y resultados observados", _
               "Tabla 29 Métricas de usabilidad: objetivos y resultados observados"
End Sub

'--- Índice 26–31 alineado con pies del cuerpo (27 Comparativa … 31 Matriz) ---
Private Sub CorregirIndiceTablas26a31()
    ' Cascada de mayor a menor para no pisar números ya correctos en el cuerpo
    If Not BuscarTexto("Tabla 28 Casos de prueba funcional del sistema") Is Nothing Then
        If Not BuscarTexto("Tabla 27 Casos de prueba funcional del sistema") Is Nothing Then
            RenumerarIndiceTablas27a31EnCascada
        End If
    ElseIf Not BuscarTexto("Tabla 27 Comparativa técnica") Is Nothing Then
        RenumerarIndiceTablas27a31EnCascada
    End If

    ' Segunda «Tabla 26» en índice (Comparativa) cuando el cuerpo ya usa Tabla 27
    If Not BuscarTexto("Tabla 27 Comparativa técnica") Is Nothing Then
        If Not BuscarTexto("Tabla 26 Comparativa técnica") Is Nothing Then
            If Not BuscarTexto("Tabla 26 Backlog técnico BH-02") Is Nothing Then
                ReplaceAll "Tabla 26 Comparativa técnica: Flutter Web vs. React + Vite", _
                           "Tabla 27 Comparativa técnica: Flutter Web vs. React + Vite"
            End If
        End If
    Else
        ' Cuerpo aún con una sola numeración: renumerar Comparativa 26 → 27
        If Not BuscarTexto("Tabla 26 Comparativa técnica") Is Nothing Then
            If Not BuscarTexto("Tabla 26 Backlog técnico BH-02") Is Nothing Then
                ReplaceAll "Tabla 26 Comparativa técnica: Flutter Web vs. React + Vite", _
                           "Tabla 27 Comparativa técnica: Flutter Web vs. React + Vite"
            End If
        End If
    End If
End Sub

Private Sub RenumerarIndiceTablas27a31EnCascada()
    ReplaceAll "Tabla 30 Matriz de trazabilidad: funcionalidades, módulos y especificaciones", _
               "Tabla 31 Matriz de trazabilidad: funcionalidades, módulos y especificaciones"
    ReplaceAll "Tabla 30 Matriz de trazabilidad", _
               "Tabla 31 Matriz de trazabilidad"
    ReplaceAll "Tabla 29 Evaluación de características de calidad del sistema (ISO/IEEE)", _
               "Tabla 30 Evaluación de características de calidad del sistema (ISO/IEEE)"
    ReplaceAll "Tabla 27 Casos de prueba funcional del sistema", _
               "Tabla 28 Casos de prueba funcional del sistema"
End Sub

'--- Utilidades (mismo patrón que ActualizarTesisBioMotion.bas) ---------------
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
