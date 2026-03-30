# Bio-Motion Evaluator — Patrones UI Aplicados por Pantalla

> **Fuente de patrones:** `ui_patterns.md` (ui-patterns.com)  
> **Basado en código:** vistas actuales entregadas en Sprint  
> **Versión:** 1.0.0

---

## Criterio de selección

Solo se incluyen patrones que resuelven un problema **real y observable** en las vistas actuales. Cada patrón tiene: problema detectado en el código → patrón aplicable → implementación concreta en Flutter.

---

## 1. `BioHomeScreen` — Pantalla de inicio

### 1.1 Problema: El usuario no sabe qué hacer si el backend está desconectado

**Código actual:**
```dart
// Muestra badge de texto, pero no orienta al usuario sobre qué hacer
child: Text(_backendOk ? 'Backend conectado' : 'Sin conexión al backend', ...)
```
El usuario ve "Sin conexión" pero no tiene guía sobre cómo resolverlo desde esta misma pantalla.

**Patrón: `Inline Help Box` + `Blank Slate`**

Cuando `_backendOk == false` y `_pingInFlight == false`, mostrar debajo del badge una ayuda contextual colapsable:

```dart
if (!_backendOk && !_pingInFlight)
  _InlineHelpTile(
    message: 'Verifica que el servidor esté corriendo en $_apiBase. '
             'Puedes cambiar la URL en "Estado del backend".',
    actionLabel: 'Ir al diagnóstico',
    onAction: () => Navigator.of(context).pushNamed(AppRoutes.backendStatus),
  ),
```

Esto cierra el loop: el problema se detecta → se explica → se ofrece la acción correcta, todo en la misma pantalla.

---

### 1.2 Problema: La sección "Última sesión" no motiva si está vacía

**Código actual:**
```dart
else
  Text('Sin datos guardados. Tras analizar en vivo o por vídeo, aquí verás el último resumen.',
       style: AppTypography.caption)
```
Texto pasivo. No hay tensión ni motivación para iniciar el primer análisis.

**Patrón: `Zeigarnik Effect` + `Blank Slate con CTA`**

El efecto Zeigarnik establece que las tareas incompletas generan mayor motivación para completarse que las no iniciadas. Mostrar el estado vacío como una tarea pendiente visible:

```dart
// Estado vacío como "tarea pendiente"
Container(
  padding: const EdgeInsets.all(AppSpacing.md),
  decoration: BoxDecoration(
    color: AppColors.surface,
    borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
    border: Border.all(color: AppColors.border),
  ),
  child: Row(
    children: [
      // Indicador de progreso visual: círculo vacío
      Icon(Icons.radio_button_unchecked, color: AppColors.textSecondary, size: 20),
      const SizedBox(width: AppSpacing.sm),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Primera sesión pendiente', style: AppTypography.labelLarge),
            Text('Realiza tu primer análisis para ver métricas aquí.',
                 style: AppTypography.caption),
          ],
        ),
      ),
    ],
  ),
),
```

Cuando hay datos, reemplazar el círculo vacío por `Icons.check_circle_outline` en `AppColors.accent`.

---

### 1.3 Patrón actualmente bien aplicado: `Good Defaults` ✅

La URL por defecto `http://localhost:8000` y el ping automático al iniciar (`_loadPrefs(alsoPing: true)`) son correctos. No requiere acción del usuario para ver el estado.

---

## 2. `LiveAnalysisScreen` — Análisis en vivo con cámara

### 2.1 Problema: El panel de métricas no comunica su estado cuando no hay transmisión

**Código actual (`MetricsBottomPanel`):**
```dart
if (transmitting && (leftDeg != null || rightDeg != null))
  Row(children: [MetricTile(...), MetricTile(...)])
```
Si `!transmitting`, los `MetricTile` desaparecen. El panel queda vacío o solo muestra el `AngleHistoryChart` vacío. El usuario no recibe orientación.

**Patrón: `Blank Slate` + `Inline Hints`**

```dart
if (!transmitting)
  Column(
    children: [
      Icon(Icons.accessibility_new, size: 40, color: AppColors.textDisabled),
      const SizedBox(height: AppSpacing.sm),
      Text(
        'Posiciónate a 2–3 m de la cámara,\nde cuerpo entero, y pulsa Iniciar.',
        style: AppTypography.body.copyWith(color: AppColors.textSecondary),
        textAlign: TextAlign.center,
      ),
    ],
  )
else if (leftDeg == null && rightDeg == null)
  Text('Detectando pose…', style: AppTypography.caption)
else
  Row(children: [MetricTile(...), MetricTile(...)]),
```

Tres estados diferenciados: idle → detectando → métricas activas.

---

### 2.2 Problema: El `CameraHUD` siempre muestra `LiveIndicatorDot(active: true)` hardcodeado

**Código actual (`camera_hud.dart` línea 77):**
```dart
child: LiveIndicatorDot(active: true),  // hardcodeado
```

Si hay `serverStalled`, el dot sigue mostrándose como activo. Incoherencia visual.

**Patrón: `Feedback Loop` + `Synchronization`**

```dart
// En CameraHUD, añadir parámetro:
const CameraHUD({
  ...
  required this.serverStalled,
});

// Y pasar al dot:
LiveIndicatorDot(active: !serverStalled),
```

El indicador "EN VIVO" pasa a naranja/pulsando lento cuando hay stall, y vuelve a verde cuando los datos llegan. El estado visual siempre refleja el estado real.

---

### 2.3 Problema: No hay confirmación antes de detener la transmisión si hay datos en curso

**Código actual:** Botón "Detener" ejecuta `_stopStreaming()` inmediatamente.

**Patrón: `Undo` adaptado → confirmación rápida tipo Snackbar**

En análisis clínico, detener accidentalmente pierde el contexto de la sesión. Aplicar el patrón Undo con un `SnackBar` de acción:

```dart
Future<void> _requestStop() async {
  _stopStreaming(); // detiene inmediatamente (datos ya están)
  if (!mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: const Text('Análisis detenido'),
      duration: const Duration(seconds: 4),
      action: SnackBarAction(
        label: 'Reanudar',
        textColor: AppColors.accent,
        onPressed: _toggleTransmit, // reinicia
      ),
    ),
  );
}
```

El dato ya se detuvo (no hay estado ambiguo) pero el usuario puede reanudar en 4 segundos si fue accidental.

---

### 2.4 Problema: La URL del API es configurable pero no hay feedback de si cambió

**Código actual:** `AppTextField` en un `ModalBottomSheet` (per estándar). No hay confirmación al guardar.

**Patrón: `Input Feedback` + `Forgiving Format`**

```dart
// Al cerrar el sheet de configuración:
void _saveConfig(String newUrl) {
  final normalized = normalizeApiBaseUrl(newUrl);
  persistApiBase(normalized);
  setState(() => _apiBase = normalized);
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('URL guardada: $normalized'),
      duration: const Duration(seconds: 2),
    ),
  );
}
```

El usuario ve exactamente qué URL quedó guardada (incluyendo la normalización automática).

---

### 2.5 Patrón actualmente bien aplicado: `Progressive Disclosure` ✅

El `DraggableScrollableSheet` del panel inferior con handle visible implementa correctamente la divulgación progresiva. El historial de 30 frames solo se ve al expandir. No requiere cambios.

---

### 2.6 Patrón actualmente bien aplicado: `Feedback Loop` en métricas ✅

`CameraHUD` con `serverStalled`, `rxPerSec`, `captureMs` y `serverRttMs` cubre el bucle de feedback técnico. `MetricTile` con `MetricStatus` cubre el bucle de feedback clínico.

---

## 3. `VideoAnalysisScreen` — Análisis de video desde servidor

### 3.1 Problema: No hay indicación de progreso del video

**Código actual:** El `_frameIndex` se muestra en un `Chip`. No hay indicación de cuánto falta.

**Patrón: `Progress Indicator` + `Zeigarnik Effect`**

Si el backend devuelve `total_frames` en el primer mensaje (o estimado), mostrar barra de progreso. Si no lo devuelve, mostrar al menos el frame index como contador progresivo:

```dart
// En VideoAnalysisScreen — añadir campo:
int? _totalFrames;  // del primer mensaje del backend si lo incluye

// En la UI, encima del preview:
if (_running && _frameIndex >= 0)
  Padding(
    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_totalFrames != null)
          LinearProgressIndicator(
            value: _frameIndex / _totalFrames!,
            color: AppColors.accent,
            backgroundColor: AppColors.border,
            borderRadius: BorderRadius.circular(2),
          )
        else
          // Sin total: contador de avance sin límite conocido
          Text('Procesando frame $_frameIndex…', style: AppTypography.caption),
      ],
    ),
  ),
```

El efecto Zeigarnik aplica: el usuario ve una tarea en progreso (barra incompleta) → motivación a esperar a que termine.

---

### 3.2 Problema: El `FrameLogTile` tiene el mini-spark con línea derecha `dashed: true` pero la función nunca pinta la línea derecha (el `if (dashed)` hace return)

**Código actual (`frame_log_tile.dart`):**
```dart
if (!dashed) {
  canvas.drawLine(Offset(x0, y0), Offset(x1, y1), paint);
}
// La línea derecha (dashed: true) nunca se pinta
```

**Bug funcional — corrección:**
```dart
void stroke(List<double> vals, Color c, {bool dashed = false}) {
  if (vals.length < 2) return;
  final paint = Paint()..color = c..strokeWidth = 1.2..style = PaintingStyle.stroke;
  for (var i = 0; i < vals.length - 1; i++) {
    final x0 = w * (i / (vals.length - 1));
    final x1 = w * ((i + 1) / (vals.length - 1));
    final y0 = h * (1 - vals[i].clamp(0.0, 180.0) / 180.0);
    final y1 = h * (1 - vals[i + 1].clamp(0.0, 180.0) / 180.0);
    if (dashed) {
      // Dash manual: alternar segmentos
      final dx = x1 - x0;
      final dy = y1 - y0;
      final len = (Offset(dx, dy)).distance;
      final dir = Offset(dx, dy) / len;
      const dashLen = 3.0, gapLen = 2.0;
      var t = 0.0;
      while (t < len) {
        final end = (t + dashLen).clamp(0.0, len);
        canvas.drawLine(
          Offset(x0, y0) + dir * t,
          Offset(x0, y0) + dir * end,
          paint,
        );
        t += dashLen + gapLen;
      }
    } else {
      canvas.drawLine(Offset(x0, y0), Offset(x1, y1), paint);
    }
  }
}
```

---

### 3.3 Problema: El `showAnalysisSummaryDialog` muestra datos en texto plano sin jerarquía

**Código actual (`analysis_summary_dialog.dart`):** Una lista de `Text(...)` sin diferenciación visual entre el dato principal (calidad %) y los datos de soporte (min/max frames).

**Patrón: `Visual Hierarchy` + `Peak-End Rule`**

Reestructurar el diálogo en tres zonas claras:

```
┌─────────────────────────────────────┐
│  RESUMEN DEL ANÁLISIS               │
├─────────────────────────────────────┤
│  [ZONA 1 — Peak] Gran número        │
│  Calidad ROM: 74.2%   ← MetricTile  │
│  (fondo verde/naranja/rojo)         │
├─────────────────────────────────────┤
│  [ZONA 2 — Medias]                  │
│  RODILLA IZQ.    RODILLA DER.       │
│  127.4° media    131.1° media       │
├─────────────────────────────────────┤
│  [ZONA 3 — Técnico, colapsable]     │
│  Min/max por frame (accordion)      │
├─────────────────────────────────────┤
│              [Cerrar]               │
└─────────────────────────────────────┘
```

```dart
// Zona 1 — dato más importante primero (Peak-End Rule)
MetricTile(
  label: 'CALIDAD ROM BILATERAL',
  value: '${s.pctGood.toStringAsFixed(1)} %',
  sublabel: s.pctGood >= 70
      ? 'Excelente movilidad en este movimiento'
      : s.pctGood >= 40
          ? 'Movilidad en zona de mejora'
          : 'Requiere trabajo de movilidad específico',
  status: s.qualityStatus,
),

// Zona 2 — medias lado a lado
Row(children: [
  Expanded(child: MetricTile(label: 'MEDIA IZQ.', value: '${s.meanLeftDeg!.toStringAsFixed(1)}°', ...)),
  SizedBox(width: AppSpacing.sm),
  Expanded(child: MetricTile(label: 'MEDIA DER.', value: '${s.meanRightDeg!.toStringAsFixed(1)}°', ...)),
]),

// Zona 3 — técnico colapsable (ExpansionTile con AppColors)
ExpansionTile(
  title: Text('Detalles por frame', style: AppTypography.labelMedium),
  iconColor: AppColors.textSecondary,
  children: [/* min/max/frames */],
),
```

---

### 3.4 Problema: No hay forma de reiniciar el análisis sin reconfigurar todo

**Código actual:** Al terminar, el botón vuelve a "Iniciar análisis". Los campos del formulario quedan con los valores anteriores. Correcto, pero no hay mensaje que invite a reiniciar.

**Patrón: `New Beginning Effect`**

Al terminar el análisis (evento `onDone`), mostrar un mensaje positivo que invite a repetir:

```dart
// En onDone del WebSocket:
_appendLog('(análisis completado)');
if (mounted) {
  setState(() => _running = false);
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: const Text('Análisis completado — puedes iniciar otro'),
      duration: const Duration(seconds: 3),
      backgroundColor: AppColors.accentMuted,
    ),
  );
}
```

---

## 4. `BackendStatusScreen` — Estado del backend

### 4.1 Patrón actualmente bien aplicado: `Feedback Loops` + `Good Defaults` ✅

- Auto-ping al iniciar (`initState` → `_checkHealth`)
- Retry automático con countdown (`_retrySecondsLeft`)
- `MetricTile` con `MetricStatus` para latencia
- `TextButton` para abrir en navegador

Implementación correcta. No requiere cambios estructurales.

---

### 4.2 Problema menor: El countdown de retry se muestra como texto simple

**Código actual:**
```dart
Text('Reintento automático en $_retrySecondsLeft s', style: AppTypography.caption)
```

**Patrón: `Progress Indicator` visual**

```dart
Row(
  children: [
    SizedBox(
      width: 16, height: 16,
      child: CircularProgressIndicator(
        value: _retrySecondsLeft / 10.0,  // 10 = duración total
        strokeWidth: 2,
        color: AppColors.angleWarn,
        backgroundColor: AppColors.border,
      ),
    ),
    const SizedBox(width: AppSpacing.sm),
    Text('Reintento en $_retrySecondsLeft s', style: AppTypography.caption),
  ],
),
```

El `CircularProgressIndicator` determinado comunica el tiempo restante de forma visual sin texto adicional.

---

## 5. Patrones transversales — aplican a todas las pantallas

### 5.1 `Forgiving Format` — URLs del API

Actualmente `ws_uri.dart` tiene `normalizeApiBaseUrl` pero no está siendo llamado en todos los puntos de entrada. Verificar que se llama en:

- [ ] `BackendStatusScreen._checkHealth()` — al construir el `Uri`
- [ ] `LiveAnalysisScreen._toggleTransmit()` — antes de `buildVideoWebSocketUri`
- [ ] `VideoAnalysisScreen._start()` — antes de `buildPoseStreamWebSocketUri`

```dart
// Patrón unificado — en cada punto de uso:
final base = normalizeApiBaseUrl(_apiBase.text.trim());
final wsUri = buildVideoWebSocketUri(base);
```

---

### 5.2 `Input Feedback` — Validación de campos numéricos

Solo `VideoAnalysisScreen` valida el campo FPS, y lo hace al pulsar "Iniciar" (feedback tardío).

**Mejorar a validación `onChange`:**

```dart
String? _fpsError;

TextField(
  controller: _fps,
  onChanged: (v) {
    final n = double.tryParse(v);
    setState(() => _fpsError =
        (n == null || n < 0.5 || n > 60) ? 'Entre 0.5 y 60 FPS' : null);
  },
  decoration: InputDecoration(
    labelText: 'FPS',
    errorText: _fpsError,
    border: const OutlineInputBorder(),
  ),
),
```

---

### 5.3 `Appropriate Challenge` — Sublabels de `MetricTile`

En `MetricsBottomPanel` ya se usa `AngleFormatter.kneeFlexionMetricSublabel`. Verificar que esta función devuelve mensajes de progreso, no solo el estado:

```dart
// En angle_formatter.dart — patrón Appropriate Challenge:
static String kneeFlexionMetricSublabel(double? deg) {
  if (deg == null) return 'Sin datos';
  if (deg >= AngleRanges.kneeFlexionGoodMinDeg) return 'En objetivo ✓';
  final diff = AngleRanges.kneeFlexionGoodMinDeg - deg;
  if (diff <= 10) return 'Faltan ${diff.toStringAsFixed(1)}° — casi allí';
  return 'Objetivo: >${AngleRanges.kneeFlexionGoodMinDeg.toStringAsFixed(0)}°';
}
```

La diferencia semántica: "Objetivo: >130°" es informativo; "Faltan 3.2° — casi allí" es motivador.

---

### 5.4 `Consistent Terminology` — Nombres de pantallas

Actualmente en la UI conviven dos vocabularios:

| Lugar | Texto actual | Problema |
|---|---|---|
| `NavCard` home | `'Análisis en vivo'` | ✅ Claro |
| `AppBar` de la pantalla | `'Análisis en vivo'` | ✅ Consistente |
| `NavCard` home | `'Vídeo en servidor'` | ⚠️ Técnico |
| `AppBar` de la pantalla | `'Vídeo de prueba (servidor)'` | ❌ Inconsistente |
| `NavCard` home | `'Estado del backend'` | ⚠️ Técnico para usuario final |

**Propuesta de vocabulario unificado:**

| Pantalla | Label en NavCard | AppBar title |
|---|---|---|
| LiveAnalysisScreen | `Análisis en vivo` | `Análisis en vivo` |
| VideoAnalysisScreen | `Análisis de video` | `Análisis de video` |
| BackendStatusScreen | `Conexión al servidor` | `Conexión al servidor` |

---

## 6. Resumen ejecutivo de patrones por pantalla

| Pantalla | Patrón | Prioridad | Estado |
|---|---|---|---|
| `BioHomeScreen` | Blank Slate + Inline Help (backend offline) | Alta | ❌ Pendiente |
| `BioHomeScreen` | Zeigarnik (última sesión vacía) | Media | ❌ Pendiente |
| `LiveAnalysisScreen` | Blank Slate (panel idle) | Alta | ❌ Pendiente |
| `LiveAnalysisScreen` | Feedback Loop (LiveDot ↔ stall) | Alta | ⚠️ Bug (`active: true` hardcoded) |
| `LiveAnalysisScreen` | Undo (detener accidental) | Media | ❌ Pendiente |
| `LiveAnalysisScreen` | Input Feedback (URL config) | Baja | ❌ Pendiente |
| `LiveAnalysisScreen` | Progressive Disclosure (panel) | Alta | ✅ Implementado |
| `VideoAnalysisScreen` | Progress Indicator + Zeigarnik | Alta | ❌ Pendiente |
| `VideoAnalysisScreen` | Visual Hierarchy (diálogo resumen) | Alta | ❌ Pendiente |
| `VideoAnalysisScreen` | New Beginning Effect (post-análisis) | Media | ❌ Pendiente |
| `VideoAnalysisScreen` | Bug fix spark derecho (dashed) | Alta | ❌ Bug activo |
| `BackendStatusScreen` | Progress Indicator (retry countdown) | Baja | ⚠️ Solo texto |
| Todas | Forgiving Format (normalizar URLs) | Alta | ⚠️ Parcial |
| Todas | Input Feedback onChange (FPS) | Media | ⚠️ Solo al submit |
| Todas | Appropriate Challenge (sublabels) | Media | ⚠️ Parcial |
| Todas | Consistent Terminology | Media | ⚠️ Inconsistente |

---

*Prioridad Alta = afecta la experiencia principal del usuario en cada sesión.  
Prioridad Media = mejora la calidad percibida y reduce fricción.  
Prioridad Baja = refinamiento de detalle.*