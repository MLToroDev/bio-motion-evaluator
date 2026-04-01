# Bio-Motion Evaluator — Patrones UI Aplicados por Pantalla

> **Fuente de patrones:** `ui_patterns.md` (ui-patterns.com)  
> **Basado en código:** vistas actuales entregadas en Sprint  
> **Versión:** 2.0.0  
> **Última actualización:** 2026-03-30  
>
> **Leyenda de estado:** ✅ Implementado · ⚠️ Parcial · ❌ Pendiente

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

### 2.1 ✅ Patrón: `Blank Slate` + estados diferenciados del panel

**Problema original:** `MetricsBottomPanel` dejaba el área de métricas vacía cuando no había transmisión activa.

**Implementado en:** `widgets/metrics_panel.dart` → clases `_IdleState` y `_DetectingPoseState`.

```dart
// Tres estados claramente diferenciados:
if (!transmitting)           → _IdleState()           // ícono + instrucción
else if (metrics.isEmpty)    → _DetectingPoseState()   // spinner + "Detectando pose…"
else                         → _MetricsList(metrics)   // tarjetas de métricas
```

`_IdleState` guía al usuario hacia la acción (patrón Blank Slate).  
`_DetectingPoseState` muestra un `CircularProgressIndicator` compacto para no dejar el área vacía mientras MediaPipe busca landmarks.

---

### 2.2 ✅ Patrón: `Feedback Loop` — indicador EN VIVO reactivo

**Problema original:** `LiveIndicatorDot(active: true)` hardcodeado ignoraba `serverStalled`.

**Implementado en:** `widgets/camera_hud.dart` — CameraHUD rediseñado como una sola línea compacta.

```dart
LiveIndicatorDot(
  active: !serverStalled,
  color: serverStalled ? AppColors.angleWarn : null,
),
Text(serverStalled ? 'EN VIVO (esperando…)' : 'EN VIVO', ...),
```

El color del indicador y el texto cambian según el estado real del servidor.  
**Nota adicional:** CameraHUD fue compactado de 2 contenedores apilados (~50 px) a una sola línea (~22 px) para reducir la presión de espacio en el panel inferior.

---

### 2.3 ✅ Patrón: `Undo` — SnackBar con acción "Reanudar"

**Problema original:** Botón "Detener" ejecutaba `_stopStreaming()` sin posibilidad de deshacer.

**Implementado en:** `live_analysis_screen.dart` → `_toggleTransmit()`.

```dart
ScaffoldMessenger.of(context).showSnackBar(
  SnackBar(
    content: const Text('Análisis detenido'),
    duration: const Duration(seconds: 4),
    action: SnackBarAction(
      label: 'Reanudar',
      textColor: AppColors.accent,
      onPressed: _toggleTransmit,
    ),
  ),
);
```

El análisis se detiene inmediatamente (no hay estado ambiguo) pero el usuario puede reanudar en 4 segundos si fue accidental.

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

### 2.5 ✅ Patrón: `Dashboard` + `Module Tabs` — panel inferior refactorizado

**Problema:** El panel inferior (`DraggableScrollableSheet`) mezclaba métricas, log y gráfica sin jerarquía clara. Al añadir contenido causaba overflow.

**Implementado en:** `widgets/live_dashboard_panel.dart` + `widgets/metrics_panel.dart`

#### Estructura visual implementada

```
┌──────────────────────────────────────┐
│  ── (handle)                         │
│  [MÉTRICAS]  [LOG]  [HISTÓRICO]      │  ← TabBar (Module Tabs)
├──────────────────────────────────────┤
│                                      │
│  Contenido del tab activo            │  ← TabBarView (Expanded)
│                                      │
├──────────────────────────────────────┤
│  [  Analizar en vivo  ▶  ]           │  ← CTA siempre visible
└──────────────────────────────────────┘
```

#### Por qué este patrón

- **Dashboard (operacional):** todos los datos giran en torno a una sola meta (calidad del movimiento). Métrica principal al frente, CTA siempre accesible.
- **Module Tabs:** cada categoría ocupa el 100% del ancho. Añadir un tab nuevo requiere únicamente un `Tab` y su widget hijo.

#### Archivos implicados

| Archivo | Responsabilidad |
|---------|----------------|
| `live_dashboard_panel.dart` | Orquestador con `TabController(length: 3)` |
| `metrics_panel.dart` | Tab MÉTRICAS (data-driven, sin conocimiento del ejercicio) |
| `log_panel.dart` | Tab LOG (eventos frontend/backend) |
| `history_panel.dart` | Tab HISTÓRICO (gráfica + leyenda + blank-slate) |

---

### 2.6 ✅ Patrón: `Data-Driven Cards` — panel de métricas extensible

**Problema:** `MetricsPanel` tenía hardcodeados `leftDeg`, `rightDeg`, `asymmetryPct` — imposible reutilizarlo para press banca, running u otros ejercicios sin modificar el widget.

**Implementado en:** `core/models/live_metric.dart` + `metrics_panel.dart` + `live_analysis_screen.dart`

#### Modelo `LiveMetric`

```dart
class LiveMetric {
  const LiveMetric({
    required this.label,   // "RODILLA IZQ.", "CADENCIA", "RANGO CODO"…
    required this.value,   // "127.3°", "168 spm", "5.2 km/h"
    required this.status,  // good / warn / bad / neutral
    this.sublabel,         // contexto opcional ("Objetivo: ≥ 130°")
    this.icon,             // IconData opcional
  });
}
```

#### Punto de extensión en `live_analysis_screen.dart`

```dart
// Hoy: flexión de rodilla
final metrics = _buildLiveMetrics(leftDeg, rightDeg);

// Futuro: al agregar press banca, running, etc.
// → agregar nueva implementación aquí según ejercicio seleccionado
List<LiveMetric> _buildLiveMetrics(double? leftDeg, double? rightDeg) {
  // construye las LiveMetric del ejercicio activo
}
```

**`MetricsPanel` usa `ListView.separated` + `Expanded`** → overflow imposible, independientemente de cuántas métricas devuelva el ejercicio.

---

### 2.7 ✅ Fix: camera preview sin barras negras (`FittedBox.cover`)

**Problema:** `AspectRatio(ctrl.value.aspectRatio)` + `Align(topCenter)` dejaba una franja negra entre la cámara y el panel inferior.

**Implementado en:** `live_analysis_screen.dart` → `_buildPreview()`

```dart
return ClipRect(
  child: FittedBox(
    fit: BoxFit.cover,
    alignment: Alignment.topCenter,
    child: SizedBox(
      width: ps?.height ?? 1.0,  // ejes invertidos para portrait
      height: ps?.width ?? 1.0,
      child: PoseOverlay(..., child: CameraPreview(ctrl)),
    ),
  ),
);
```

`BoxFit.cover` garantiza que la cámara llene el área disponible recortando los bordes sobrantes, igual que `object-fit: cover` en CSS. `PoseOverlay` sigue mapeando landmarks correctamente porque opera sobre las dimensiones nativas del sensor antes del escalado.

---

### 2.8 ✅ Patrón: `Feedback Loop` en métricas

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

> Actualizado al 2026-03-30. ✅ = implementado en código · ⚠️ = parcial · ❌ = pendiente.

### 6.1 Patrones UI/UX

| Pantalla | Patrón | Prioridad | Estado | Archivo principal |
|---|---|---|---|---|
| `BioHomeScreen` | Inline Help Box + Blank Slate (backend offline) | Alta | ✅ | `home_screen.dart` |
| `BioHomeScreen` | Zeigarnik (última sesión vacía) | Media | ✅ | `home_screen.dart` |
| `LiveAnalysisScreen` | Blank Slate — idle / detectando pose | Alta | ✅ | `metrics_panel.dart` |
| `LiveAnalysisScreen` | Feedback Loop — LiveDot reactivo a stall | Alta | ✅ | `camera_hud.dart` |
| `LiveAnalysisScreen` | Undo — SnackBar "Reanudar" | Media | ✅ | `live_analysis_screen.dart` |
| `LiveAnalysisScreen` | Input Feedback — URL normalizada al guardar | Baja | ✅ | `connection_config_form.dart` |
| `LiveAnalysisScreen` | Dashboard + Module Tabs (panel inferior) | Alta | ✅ | `live_dashboard_panel.dart` |
| `LiveAnalysisScreen` | Data-Driven Cards (`LiveMetric`) | Alta | ✅ | `metrics_panel.dart` + `live_metric.dart` |
| `VideoAnalysisScreen` | Progress Indicator + Zeigarnik | Alta | ✅ | `video_analysis_screen.dart` |
| `VideoAnalysisScreen` | Visual Hierarchy (diálogo resumen) | Alta | ✅ | `analysis_summary_dialog.dart` |
| `VideoAnalysisScreen` | New Beginning Effect (SnackBar post-análisis) | Media | ✅ | `video_analysis_screen.dart` |
| `VideoAnalysisScreen` | Bug fix spark derecho (dashed) | Alta | ✅ | `frame_log_tile.dart` |
| `BackendStatusScreen` | Progress Indicator (retry countdown) | Baja | ✅ | `backend_status_screen.dart` |
| Todas | Forgiving Format (normalizar URLs) | Alta | ✅ | `ws_uri.dart` → `buildHealthHttpUri` |
| Todas | Appropriate Challenge (sublabels dinámicos) | Media | ✅ | `angle_formatter.dart` |
| Todas | Consistent Terminology | Media | ✅ | NavCards + AppBar titles |

### 6.2 Decisiones arquitectónicas de UI

| Decisión | Descripción | Archivo(s) |
|---|---|---|
| Camera preview sin barras negras | `FittedBox(fit: BoxFit.cover)` reemplaza `AspectRatio` | `live_analysis_screen.dart` |
| Panel inferior modular (tabs) | `LiveDashboardPanel` con `TabController(length: 3)` | `live_dashboard_panel.dart` |
| Métricas data-driven | Modelo `LiveMetric` agnóstico del ejercicio | `core/models/live_metric.dart` |
| Overflow imposible en métricas | `MetricsPanel` usa `ListView.separated` + `Expanded` | `metrics_panel.dart` |
| CameraHUD compacto | Reducido de ~50 px (2 contenedores) a ~22 px (1 línea) | `camera_hud.dart` |
| Detección de emulador Android | `defaultApiBaseUrl()` usa `DeviceInfoPlugin` | `default_api_base_url.dart` |
| Almacenamiento multi-plataforma | `SharedPreferences` / `localStorage` según plataforma | `storage/prefs.dart` |

---

*Prioridad Alta = afecta la experiencia principal del usuario en cada sesión.  
Prioridad Media = mejora la calidad percibida y reduce fricción.  
Prioridad Baja = refinamiento de detalle.*
