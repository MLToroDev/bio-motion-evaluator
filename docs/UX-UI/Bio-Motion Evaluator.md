# Bio-Motion Evaluator — Estándar de Diseño y Plan de Refactorización de Vistas

> **Proyecto:** Bio-Motion Evaluator · Trabajo de Grado · Mateo Londoño Toro  
> **Institución:** Tecnológico de Antioquia — Ingeniería en Software  
> **Versión:** 1.0.0  
> **Fecha:** 2025

---

## 1. Filosofía de Diseño

### 1.1 Principio Rector
**"Datos que se leen, no que se descifran."**

El sistema de diseño de Bio-Motion Evaluator sigue una filosofía **minimalista clínica con énfasis en datos en tiempo real**. Cada elemento visual existe para comunicar información biomecánica o guiar una acción del usuario — no como decoración. La elegancia surge de la precisión y la claridad, no de la ornamentación.

### 1.2 Valores de Diseño

| Valor | Descripción |
|---|---|
| **Claridad** | Los indicadores biomecánicos deben leerse de un vistazo. Ningún dato crítico debe estar a más de un elemento de profundidad visual. |
| **Confianza** | El sistema debe comunicar precisión y rigor científico. La UI refleja la seriedad del análisis clínico. |
| **Velocidad** | El feedback en tiempo real no puede sentirse lento. Animaciones < 200 ms. Actualizaciones de estado inmediatas. |
| **Accesibilidad** | Contraste mínimo WCAG AA. Tipografía legible en condiciones de gym (luz variable, distancia del dispositivo). |

---

## 2. Sistema de Tokens de Diseño

### 2.1 Paleta de Colores

Todos los colores se implementan como constantes `const Color(...)` en Flutter, agrupadas en una clase `AppColors`.

```dart
// lib/core/theme/app_colors.dart
abstract final class AppColors {

  // ── Fondo y superficies ──────────────────────────────────────────────────
  static const Color background      = Color(0xFF0D0F0E); // Negro orgánico (no puro)
  static const Color surface         = Color(0xFF161A18); // Superficie de card
  static const Color surfaceElevated = Color(0xFF1E2421); // Hover / elevación
  static const Color border          = Color(0xFF2A302D); // Bordes sutiles

  // ── Texto ────────────────────────────────────────────────────────────────
  static const Color textPrimary     = Color(0xFFF0F4F2); // Cuerpo / etiquetas
  static const Color textSecondary   = Color(0xFF8A9B93); // Metadatos / hints
  static const Color textDisabled    = Color(0xFF4A5550); // Controles desactivados

  // ── Acento principal: verde biomecánico ───────────────────────────────────
  static const Color accent          = Color(0xFF00E676); // Verde señal
  static const Color accentDim       = Color(0xFF00B25A); // Hover / pressed
  static const Color accentMuted     = Color(0xFF003D1E); // Background de badge activo

  // ── Semánticos de análisis ────────────────────────────────────────────────
  static const Color angleGood       = Color(0xFF00E676); // ROM dentro de rango
  static const Color angleWarn       = Color(0xFFFFB300); // ROM límite
  static const Color angleBad        = Color(0xFFFF5252); // Compensación detectada

  // ── Esqueleto de pose ────────────────────────────────────────────────────
  static const Color skeletonLine    = Color(0xFF00E676); // Huesos
  static const Color skeletonJoint   = Color(0xFFFFFFFF); // Articulaciones
  static const Color skeletonJointBorder = Color(0xFF00E676);
}
```

**Regla de uso:**
- `background` → Scaffold background
- `surface` → Cards, paneles de control
- `surfaceElevated` → Estado hover, modales
- `accent` → CTAs primarios, indicadores activos, esqueleto
- `angleGood / angleWarn / angleBad` → **Solo** para métricas de ángulo articular

### 2.2 Tipografía

```dart
// lib/core/theme/app_typography.dart
// Importar en pubspec.yaml:
//   google_fonts: ^6.x  →  DM Sans (cuerpo) + DM Mono (datos)

import 'package:google_fonts/google_fonts.dart';

abstract final class AppTypography {
  // Números de métricas — monoespaciado, legible en tiempo real
  static final metricLarge = GoogleFonts.dmMono(
    fontSize: 36, fontWeight: FontWeight.w500, letterSpacing: -0.5,
  );
  static final metricMedium = GoogleFonts.dmMono(
    fontSize: 22, fontWeight: FontWeight.w400,
  );
  static final metricSmall = GoogleFonts.dmMono(
    fontSize: 14, fontWeight: FontWeight.w400,
  );

  // Etiquetas y cuerpo
  static final labelLarge = GoogleFonts.dmSans(
    fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.5,
  );
  static final labelMedium = GoogleFonts.dmSans(
    fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.textSecondary,
  );
  static final body = GoogleFonts.dmSans(fontSize: 14, fontWeight: FontWeight.w400);
  static final caption = GoogleFonts.dmSans(
    fontSize: 11, fontWeight: FontWeight.w400, color: AppColors.textSecondary,
  );

  // Títulos de pantalla
  static final screenTitle = GoogleFonts.dmSans(
    fontSize: 17, fontWeight: FontWeight.w600,
  );
  static final sectionTitle = GoogleFonts.dmSans(
    fontSize: 13, fontWeight: FontWeight.w700,
    letterSpacing: 1.2, color: AppColors.textSecondary,
  );
}
```

**Reglas:**
- `DM Mono` → **Exclusivamente** para valores numéricos: ángulos, frame index, FPS, timestamps.
- `DM Sans` → Todo el resto: labels, botones, títulos, descripciones.
- Nunca usar `fontStyle: italic` en métricas. Nunca usar tamaños menores a 11 sp.

### 2.3 Espaciado y Geometría

```dart
abstract final class AppSpacing {
  static const double xs  = 4.0;
  static const double sm  = 8.0;
  static const double md  = 16.0;
  static const double lg  = 24.0;
  static const double xl  = 32.0;
  static const double xxl = 48.0;

  // Radios de borde
  static const double radiusSm = 6.0;
  static const double radiusMd = 10.0;
  static const double radiusLg = 16.0;
}
```

**Grilla:** Múltiplos de 8 px. Padding estándar de pantalla: `16 px` horizontal.

### 2.4 Elevación y Bordes

No usar `BoxShadow` con color negro y alta opacidad. En tema oscuro, la elevación se comunica con **diferencia de color de superficie**:

```
background (0xFF0D0F0E)
  └── surface (0xFF161A18)        +1 nivel
        └── surfaceElevated (0xFF1E2421)  +2 niveles
```

Bordes: `Border.all(color: AppColors.border, width: 1)`. Sin bordes dobles ni sombras combinadas.

---

## 3. Componentes Reutilizables

### 3.1 `MetricTile` — Indicador de ángulo articular

Widget de uso universal para mostrar cualquier métrica numérica en tiempo real.

```dart
// lib/core/widgets/metric_tile.dart

enum MetricStatus { good, warn, bad, neutral }

class MetricTile extends StatelessWidget {
  const MetricTile({
    super.key,
    required this.label,      // ej. 'Rodilla Izq.'
    required this.value,      // ej. '127.4°'
    this.status = MetricStatus.neutral,
    this.sublabel,            // ej. 'Flexión'
  });

  final String label;
  final String value;
  final MetricStatus status;
  final String? sublabel;

  Color get _statusColor => switch (status) {
    MetricStatus.good    => AppColors.angleGood,
    MetricStatus.warn    => AppColors.angleWarn,
    MetricStatus.bad     => AppColors.angleBad,
    MetricStatus.neutral => AppColors.textSecondary,
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm + AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label.toUpperCase(), style: AppTypography.sectionTitle),
          const SizedBox(height: AppSpacing.xs),
          Text(value, style: AppTypography.metricLarge.copyWith(color: _statusColor)),
          if (sublabel != null)
            Text(sublabel!, style: AppTypography.caption),
        ],
      ),
    );
  }
}
```

**Regla de estado:**
- `good` → ángulo dentro de ROM esperado (definir rangos por movimiento)
- `warn` → ángulo en zona limítrofe ±10° del rango
- `bad` → compensación detectada o fuera de rango clínico
- `neutral` → sin datos suficientes o análisis no iniciado

### 3.2 `LiveIndicatorDot` — Estado de transmisión

```dart
// Punto animado que pulsa cuando hay streaming activo
class LiveIndicatorDot extends StatefulWidget {
  const LiveIndicatorDot({super.key, required this.active});
  final bool active;
  // ... implementar con AnimationController + ScaleTransition
  // Pulso: escala 0.8 → 1.0, duración 900ms, curva Curves.easeInOut, repeat
}
```

### 3.3 `AppPrimaryButton` — Botón de acción principal

```dart
// Reemplaza FilledButton nativo para control total del estilo
// Estado activo: fondo accent, texto negro (contraste máximo)
// Estado loading: CircularProgressIndicator en accent, fondo surface
// Estado disabled: fondo border, texto textDisabled
```

### 3.4 `SectionHeader` — Encabezado de sección

```dart
// Label en mayúsculas + línea divisora sutil
// Tipografía: AppTypography.sectionTitle
// Color línea: AppColors.border
```

### 3.5 `AppTextField` — Campo de texto

```dart
// InputDecoration estandarizado:
// - fillColor: AppColors.surface
// - focusedBorder: accent
// - enabledBorder: border color
// - labelStyle: textSecondary
// - contentPadding: 12 vertical, 16 horizontal
```

---

## 4. Estándar del Overlay de Pose (`PoseOverlay` / `PoseSkeletonPainter`)

### 4.1 Colores del Esqueleto

| Elemento | Color actual | Color estándar |
|---|---|---|
| Líneas (huesos) | `0xFF00C853` | `AppColors.skeletonLine` (`0xFF00E676`) |
| Relleno de articulación | `Colors.white` | `AppColors.skeletonJoint` |
| Borde de articulación | `0xFFFF1744` | `AppColors.skeletonJointBorder` = `accent` |

**Justificación:** Eliminar el rojo de las articulaciones. El rojo está reservado para `angleBad`. El esqueleto usa exclusivamente el verde de acento para coherencia visual.

### 4.2 Parámetros del Pintor

```dart
// Valores estándar para PoseSkeletonPainter:
lineStrokeWidth: 2.0       // Era 2.5 — más limpio en resoluciones altas
jointRadius: 3.5           // Era 4.0
minVisibility: 0.4         // Era 0.3 — reducir ruido en landmarks de baja confianza
```

### 4.3 Highlight de Articulaciones Analizadas

Cuando se detecta un ángulo activo (rodilla, cadera, hombro), las articulaciones involucradas deben dibujarse con un radio mayor y el color del `MetricStatus`:

```dart
// En PoseSkeletonPainter, recibir un Set<int> highlightedLandmarks
// y Map<int, Color> landmarkColors para articulaciones con estado semántico
```

---

## 5. Plan de Refactorización por Pantalla

### 5.1 `HomeScreen` → `BioHomeScreen`

**Problema actual:** Layout plano, tipografía genérica, sin jerarquía visual, sin contexto del estado del sistema.

**Cambios requeridos:**

1. **AppBar:** Eliminar `centerTitle`. Añadir `LiveIndicatorDot` en `leading` que muestre estado de conectividad con backend (ping a `/health` al iniciar).
2. **Header de bienvenida:** Reemplazar texto plano por una sección hero con:
   - Título: `BIO-MOTION` en `AppTypography.screenTitle` con peso 700
   - Subtítulo: `Evaluación biomecánica en tiempo real` en `textSecondary`
   - Estado del backend: badge pequeño con color semántico (verde = conectado, rojo = sin conexión)
3. **Cards de navegación:** Reemplazar los 3 botones apilados por cards con:
   - Icono grande (32×32) a la izquierda
   - Título + descripción de una línea
   - Chevron derecho en `textSecondary`
   - `onTap` con feedback háptico
4. **Añadir:** Sección de "Última sesión" (frame index, ángulos registrados) persistida con `SharedPreferences` — vacía en primera sesión.

**Estructura de layout propuesta:**
```
Scaffold(background: AppColors.background)
  ├── AppBar (transparente, sin elevación)
  ├── Column
  │   ├── HeroHeader (logo + estado backend)
  │   ├── SectionHeader('ANÁLISIS')
  │   ├── NavCard → CameraStreamScreen
  │   ├── NavCard → ServerTestVideoScreen
  │   ├── SectionHeader('DIAGNÓSTICO')
  │   └── NavCard → PosePlaceholderScreen
  └── SafeArea bottom: versión del app
```

---

### 5.2 `PosePlaceholderScreen` → `BackendStatusScreen`

**Problema actual:** Pantalla de diagnóstico técnico expuesta como "Demostración pose", nombre confuso para el usuario final.

**Cambios requeridos:**

1. **Renombrar:** `BackendStatusScreen` — comunica su propósito real.
2. **Status panel:** En lugar de texto monocromático, mostrar `MetricTile` style para cada campo del `/health`:
   - `status`: badge verde/rojo
   - `model`: texto mono
   - `version`: texto mono
3. **Ping indicator:** Mostrar latencia en ms con color semántico (< 100 ms verde, < 500 ms naranja, > 500 ms rojo).
4. **Auto-retry:** Timer de 10 s que re-intenta si el estado es error, con indicador de countdown.
5. **Añadir enlace:** "Abrir backend en navegador" con `url_launcher`.

---

### 5.3 `CameraStreamScreen` → `LiveAnalysisScreen`

**Es la pantalla más crítica del sistema. Requiere la refactorización más profunda.**

**Problema actual:**
- Métricas como `Chip` widgets — difíciles de leer en movimiento
- `TextField` para URL siempre visible — contamina la UI durante análisis
- Sin diferenciación visual entre estado idle / transmitiendo
- Sin indicadores de calidad de señal (FPS real, latencia WS)

**Arquitectura de layout propuesta:**

```
Scaffold
  ├── AppBar
  │   ├── leading: BackButton
  │   ├── title: 'Análisis en vivo'
  │   └── actions: [ConfigButton, RefreshButton]
  │
  ├── Stack (ocupa todo el espacio disponible)
  │   ├── CameraPreview + PoseOverlay   ← full-screen
  │   │
  │   ├── Positioned(top: 0)            ← HUD superior (solo en transmisión)
  │   │   └── Row: [LiveIndicatorDot + 'EN VIVO', FrameCounter, SignalQuality]
  │   │
  │   └── Positioned(bottom: 0)         ← Panel de métricas deslizable
  │       └── MetricsBottomSheet
  │           ├── Handle bar
  │           ├── Row: [MetricTile(rodillaIzq), MetricTile(rodillaDer)]
  │           ├── (expandido) → más métricas / historial de ángulos
  │           └── PrimaryButton: 'Iniciar / Detener'
  │
  └── ConditionalOverlay (si !transmitting && !initializing)
      └── IdlePrompt centrado con botón de inicio
```

**Cambios específicos:**

1. **URL del API:** Mover a un `ModalBottomSheet` o pantalla de configuración. En uso normal, la URL no debe ser editable desde la pantalla principal.
2. **Métricas de ángulo:** Usar `MetricTile` con `MetricStatus` calculado según rangos ROM esperados para sentadilla (referencia: < 90° = `bad`, 90–130° = `warn`, > 130° = `good` para flexión de rodilla en sentadilla profunda).
3. **HUD de frame:** Reemplazar `Chip(frame N)` por texto mono pequeño en esquina superior derecha de la preview.
4. **Añadir métrica de FPS real:** Calcular frames recibidos por segundo en el cliente y mostrarlo en el HUD.
5. **Historial de ángulos:** Gráfica de línea simple (usando `fl_chart` o `CustomPainter`) con los últimos 30 valores de cada ángulo — visible al expandir el panel inferior.

**Nueva firma de `_fmtDeg` → `AngleFormatter`:**
```dart
// lib/core/utils/angle_formatter.dart
class AngleFormatter {
  static String format(dynamic v) { ... }  // misma lógica
  
  static MetricStatus statusForKneeFlexion(double deg) {
    if (deg >= 130) return MetricStatus.good;
    if (deg >= 90)  return MetricStatus.warn;
    return MetricStatus.bad;
  }
  // Añadir: statusForHipFlexion, statusForAnkleDorsiflexion, etc.
}
```

---

### 5.4 `ServerTestVideoScreen` → `VideoAnalysisScreen`

**Problema actual:**
- Log de texto plano sin diferenciación visual
- Sin visualización del progreso del video
- Sin resumen estadístico al finalizar

**Cambios requeridos:**

1. **Configuración:** Misma estrategia que `LiveAnalysisScreen` — mover a modal de config.
2. **Barra de progreso:** Si el backend reporta `total_frames` y `frame_index`, mostrar `LinearProgressIndicator` con color `accent`.
3. **Log mejorado:** Reemplazar `ListTile` plano por filas con:
   - Número de frame en mono + color semántico según ángulos
   - Mini spark line con los últimos 5 valores
4. **Panel de resumen post-análisis:** Al recibir `onDone`, mostrar:
   - Rango promedio de cada ángulo
   - Frame con ángulo máximo y mínimo
   - Badge de calidad general (basado en % de frames en zona `good`)
5. **Exportar log:** Botón para compartir log como CSV usando `share_plus`.

---

### 5.5 `PoseOverlay` y `PoseSkeletonPainter`

**Cambios requeridos:**

1. Actualizar colores según sección 4.1.
2. Añadir soporte para `highlightedLandmarks` y `landmarkColors`.
3. Extraer `minVisibility` como parámetro configurable desde el tema.
4. Añadir `shouldRepaint` más granular (comparar lista item por item con umbral de movimiento mínimo para evitar repaints innecesarios).

---

## 6. Estructura de Archivos Objetivo

```
lib/
├── core/
│   ├── theme/
│   │   ├── app_colors.dart
│   │   ├── app_typography.dart
│   │   ├── app_spacing.dart
│   │   └── app_theme.dart          ← ThemeData unificado
│   ├── widgets/
│   │   ├── metric_tile.dart
│   │   ├── live_indicator_dot.dart
│   │   ├── app_primary_button.dart
│   │   ├── app_text_field.dart
│   │   ├── nav_card.dart
│   │   └── section_header.dart
│   └── utils/
│       ├── angle_formatter.dart
│       └── ws_uri.dart             ← sin cambios
│
├── pose/
│   ├── pose_overlay.dart           ← actualizar colores y parámetros
│   ├── pose_topology.dart          ← sin cambios
│   └── angle_ranges.dart           ← NUEVO: rangos ROM por movimiento
│
└── screens/
    ├── home/
    │   └── bio_home_screen.dart
    ├── live_analysis/
    │   ├── live_analysis_screen.dart
    │   └── widgets/
    │       ├── metrics_bottom_panel.dart
    │       ├── camera_hud.dart
    │       └── angle_history_chart.dart
    ├── video_analysis/
    │   ├── video_analysis_screen.dart
    │   └── widgets/
    │       ├── analysis_summary_panel.dart
    │       └── frame_log_tile.dart
    ├── backend_status/
    │   └── backend_status_screen.dart
    └── config/
        └── connection_config_screen.dart   ← NUEVO: URL del API aislada
```

---

## 7. `AppTheme` — Configuración de ThemeData

```dart
// lib/core/theme/app_theme.dart
import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_typography.dart';

abstract final class AppTheme {
  static ThemeData get dark => ThemeData(
    colorScheme: const ColorScheme.dark(
      surface: AppColors.background,
      primary: AppColors.accent,
      onPrimary: Color(0xFF000000),
      secondary: AppColors.accentDim,
      error: AppColors.angleBad,
      outline: AppColors.border,
    ),
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(
        color: AppColors.textPrimary,
        fontSize: 17,
        fontWeight: FontWeight.w600,
      ),
      iconTheme: IconThemeData(color: AppColors.textPrimary),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.border,
      thickness: 1,
      space: 1,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
      ),
      labelStyle: const TextStyle(color: AppColors.textSecondary),
      hintStyle: const TextStyle(color: AppColors.textDisabled),
    ),
    useMaterial3: true,
  );
}
```

Actualizar `main.dart`:
```dart
theme: AppTheme.dark,        // aplicación siempre en dark
darkTheme: AppTheme.dark,
themeMode: ThemeMode.dark,
```

---

## 8. Nuevas Métricas e Indicadores para la UI

### 8.1 Métricas Prioritarias (Sprint siguiente)

| Métrica | Fuente | Widget | Posición |
|---|---|---|---|
| Ángulo rodilla izquierda (°) | Backend `/ws/video` | `MetricTile` | Panel inferior |
| Ángulo rodilla derecha (°) | Backend `/ws/video` | `MetricTile` | Panel inferior |
| Asimetría bilateral (%) | Calculada en cliente | `MetricTile` warn/bad | Panel inferior |
| FPS real del cliente | Timer en cliente | HUD superior | Esquina sup. derecha |
| Frame index | Backend | HUD superior | Esquina sup. izquierda |
| Latencia WebSocket (ms) | `DateTime.now()` - timestamp frame | HUD superior | Centro |

### 8.2 Cálculo de Asimetría Bilateral (cliente)

```dart
// lib/core/utils/angle_formatter.dart
static double asymmetry(double leftDeg, double rightDeg) {
  if (leftDeg == 0 && rightDeg == 0) return 0;
  return ((leftDeg - rightDeg).abs() / ((leftDeg + rightDeg) / 2)) * 100;
}

static MetricStatus statusForAsymmetry(double pct) {
  if (pct < 10) return MetricStatus.good;
  if (pct < 15) return MetricStatus.warn;
  return MetricStatus.bad;
}
```

### 8.3 Historial Gráfico (fase 2)

Implementar `AngleHistoryChart` con `CustomPainter`:
- Fondo: `AppColors.surface`
- Línea izquierda: `AppColors.accent` (sólida)
- Línea derecha: `AppColors.accentDim` (punteada)
- Zona good/warn/bad: bandas horizontales translúcidas
- Eje X: últimos 30 frames (sin etiquetas, solo línea base)
- Eje Y: 0–180°, etiquetas en `DM Mono 10sp`

---

## 9. Guía de Animaciones

| Contexto | Tipo | Duración | Curva |
|---|---|---|---|
| Transición de pantalla | `FadeTransition` | 200 ms | `Curves.easeOut` |
| Aparición de `MetricTile` | `SlideTransition` (bottom-up) + `FadeTransition` | 180 ms | `Curves.easeOutCubic` |
| Cambio de valor en métrica | Animación de número (`AnimatedSwitcher`) | 120 ms | `Curves.easeInOut` |
| Pulso `LiveIndicatorDot` | `ScaleTransition` 0.75→1.0 | 900 ms, repeat | `Curves.easeInOut` |
| Apertura panel inferior | `DraggableScrollableSheet` nativo | - | Material default |
| Error / estado bad | Shake sutil (`TweenSequence`) | 300 ms, 3 ciclos | `Curves.elasticIn` |

**Regla general:** Ninguna animación supera los 300 ms. Las actualizaciones de métricas en tiempo real (ángulos) NO se animan — el cambio debe ser inmediato para transmitir precisión clínica.

---

## 10. Checklist de Implementación

### Fase 1 — Fundamentos (Sprint actual)
- [ ] Crear `app_colors.dart`, `app_typography.dart`, `app_spacing.dart`
- [ ] Crear `app_theme.dart` y actualizar `main.dart`
- [ ] Implementar `MetricTile` con estados semánticos
- [ ] Implementar `LiveIndicatorDot`
- [ ] Implementar `AppPrimaryButton`, `AppTextField`, `NavCard`
- [ ] Refactorizar `PoseSkeletonPainter` con nuevos colores y parámetros
- [ ] Refactorizar `HomeScreen` → `BioHomeScreen`

### Fase 2 — Pantallas de análisis
- [ ] Refactorizar `CameraStreamScreen` → `LiveAnalysisScreen` con layout Stack
- [ ] Implementar `MetricsBottomPanel` con `MetricTile` y panel expandible
- [ ] Implementar `CameraHUD` (frame, FPS, latencia)
- [ ] Crear `ConnectionConfigScreen` y mover URL del API
- [ ] Refactorizar `PosePlaceholderScreen` → `BackendStatusScreen`

### Fase 3 — Métricas avanzadas
- [ ] Implementar `AngleFormatter.asymmetry` y `statusForAsymmetry`
- [ ] Implementar `AngleHistoryChart` con `CustomPainter`
- [ ] Implementar `angle_ranges.dart` con rangos ROM por movimiento
- [ ] Refactorizar `ServerTestVideoScreen` → `VideoAnalysisScreen` con resumen estadístico
- [ ] Añadir `AsymmetryMetricTile` al panel de análisis en vivo

---

## 11. Dependencias a Añadir

```yaml
# pubspec.yaml — nuevas dependencias
dependencies:
  google_fonts: ^6.2.1        # DM Sans + DM Mono
  shared_preferences: ^2.3.0  # Persistir URL, última sesión
  share_plus: ^10.0.0         # Exportar log CSV
  url_launcher: ^6.3.0        # Abrir backend en navegador
```

---

*Este documento es la fuente de verdad para todas las decisiones de diseño del proyecto Bio-Motion Evaluator. Cualquier desviación debe documentarse y justificarse en el sprint correspondiente.*