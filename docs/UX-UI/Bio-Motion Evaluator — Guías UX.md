# Bio-Motion Evaluator — Guías UX

> **Complemento de:** `bio_motion_design_standard.md`  
> **Fuentes aplicadas:** Nielsen Norman Group (Eyetracking, 2000), Digital Studio (Principios UX), UI-Patterns.com  
> **Versión:** 1.0.0

---

## Propósito de este documento

Este documento traduce principios académicos y de industria en **decisiones de diseño concretas** para las pantallas de Bio-Motion Evaluator. No es teoría — cada principio tiene una aplicación directa al producto.

---

## 1. Comportamiento de Lectura y Zonas Calientes

### 1.1 Fundamento: Eyetracking y Patrones de Escaneo

La investigación de Nielsen Norman Group (Jakob Nielsen, 2000) y estudios posteriores del Poynter Institute establecen que:

- El **78% de las primeras fijaciones oculares** son sobre texto, no sobre gráficos.
- Los usuarios **no leen linealmente** — escanean en busca de puntos de interés.
- El patrón más frecuente en interfaces con jerarquía débil es el **patrón Z** (diagonal); con jerarquía fuerte se activa el **patrón F** (horizontal + descenso vertical izquierdo).
- El usuario promedio abandona una página en **menos de 15 segundos** si no encuentra relevancia.
- En lectura "completa", los usuarios leen aproximadamente el **75% del texto** — nunca el 100%.

**Conclusión para Bio-Motion:** La interfaz compite contra el tiempo de reacción del usuario durante el ejercicio. Los datos biomecánicos deben ubicarse en las zonas de mayor fijación ocular natural.

### 1.2 Mapa de Zonas Calientes por Pantalla

#### `LiveAnalysisScreen` (análisis en tiempo real)

```
┌─────────────────────────────────────┐
│  [ZONA A] AppBar / HUD superior     │  ← Primera fijación (F-horizontal)
│  Frame · FPS · Latencia · EN VIVO   │     Texto pequeño, mono, alta densidad
├─────────────────────────────────────┤
│                                     │
│                                     │
│      [ZONA B] Vista de cámara       │  ← Segunda fijación (centro visual)
│       + Esqueleto de pose           │     Zona más grande, sin texto
│                                     │
│                                     │
├─────────────────────────────────────┤
│  [ZONA C] Panel de métricas         │  ← Tercera fijación (F-descenso izq.)
│  Rodilla Izq. · Rodilla Der.        │     AQUÍ van los MetricTile principales
│  Asimetría · Estado general         │
├─────────────────────────────────────┤
│  [ZONA D] Botón de acción           │  ← CTA — posición fija, siempre visible
└─────────────────────────────────────┘
```

**Reglas derivadas:**
- Las métricas de ángulo (Zona C) deben ser **el texto más grande** de la pantalla después del video — el ojo llega ahí como tercer punto natural.
- La Zona A (HUD) usa tipografía mono pequeña — datos secundarios de monitoreo técnico, no clínicos.
- **Nunca colocar métricas críticas en el centro-derecha** de la pantalla: el patrón F deja esa zona como la de menor atención.
- El esqueleto de pose (Zona B) es el componente gráfico — según el eyetracking de Nielsen, los gráficos reciben atención **después** del texto. El esqueleto refuerza visualmente lo que los números ya comunican.

#### `VideoAnalysisScreen` (análisis de video servidor)

```
┌─────────────────────────────────────┐
│  [ZONA A] Título + estado           │  ← Patrón F: primera línea horizontal
│  Progreso del video (barra)         │
├───────────────┬─────────────────────┤
│               │  [ZONA C]           │
│  [ZONA B]     │  Rodilla Izq.       │  ← Columna izquierda: mayor atención
│  Preview JPEG │  Rodilla Der.       │     (patrón F baja por el lado izq.)
│  + Esqueleto  │  Asimetría          │
│               │                     │
├───────────────┴─────────────────────┤
│  [ZONA D] Log de frames             │  ← Zona de menor atención — datos técnicos
└─────────────────────────────────────┘
```

**Reglas derivadas:**
- Layout de **dos columnas** en orientación landscape, **una columna** en portrait.
- Las métricas (Zona C) van a la **izquierda o en la parte superior** — nunca solo abajo o a la derecha.
- El log de frames (Zona D) es información de soporte, no primaria — fuente pequeña, contraste reducido.

#### `BioHomeScreen` (navegación inicial)

```
┌─────────────────────────────────────┐
│  [ZONA A] Header + estado backend   │  ← Patrón Z: esquina sup. izquierda
│  BIO-MOTION · Estado: Conectado     │
├─────────────────────────────────────┤
│  [ZONA B] NavCard principal         │  ← Centro del patrón Z (mayor peso)
│  → Análisis en vivo                 │     La acción más importante arriba
├─────────────────────────────────────┤
│  [ZONA C] NavCards secundarias      │  ← Descenso del patrón Z
│  → Análisis de video                │
│  → Estado del backend               │
└─────────────────────────────────────┘
```

**Regla derivada:** La tarjeta de acción más importante (análisis en vivo) siempre en **primera posición** — el patrón Z deposita la mayor atención en el recorrido diagonal de la esquina superior izquierda a la inferior derecha.

---

## 2. Principios de Escaneabilidad Aplicados

### 2.1 Jerarquía Visual en Métricas

Basado en los factores de jerarquía visual (tamaño, color, contraste, proximidad, alineación, espacio negativo, repetición):

**Escala de importancia visual → escala tipográfica:**

| Nivel | Dato | Estilo | Tamaño |
|---|---|---|---|
| 1 — Crítico | Ángulo articular activo | `DM Mono Bold` + color semántico | 36 sp |
| 2 — Importante | Etiqueta del ángulo ("Rodilla Izq.") | `DM Sans SemiBold` uppercase | 12 sp |
| 3 — Contextual | Frame index, FPS | `DM Mono Regular` | 11 sp |
| 4 — Técnico | URL del backend, log de frames | `DM Mono Regular` dimmed | 10 sp |

**Regla de contraste:** El número del ángulo (`36sp`, color semántico) debe tener al menos **4.5:1 de contraste** contra el fondo del `MetricTile` (`AppColors.surface`). Los valores `angleGood`, `angleWarn` y `angleBad` ya cumplen esto contra `#161A18`.

### 2.2 Espacio Negativo como Señal Clínica

El espacio negativo no es solo estética — en una interfaz de análisis biomecánico, **la densidad visual comunica urgencia**:

- **Panel colapsado (estado normal):** Mucho espacio negativo → calma, sesión fluye bien.
- **Panel expandido con métricas en rojo:** Densidad aumenta → el usuario nota que algo requiere atención.

**Reglas de padding por contexto:**

```
MetricTile normal:        padding: 16h × 12v
MetricTile en estado bad: padding: 12h × 10v  + border accent angleBad
HUD superior (en vivo):   padding: 8h × 6v    (compacto, no interfiere con video)
Cards de navegación:      padding: 20h × 16v  (espacioso, invita a la acción)
```

### 2.3 Subtítulos y Labels como Guías de Escaneo

Los usuarios escanean encabezados y etiquetas para decidir si el contenido es relevante. En Bio-Motion esto se traduce en:

**Labels en `SectionHeader`:** Siempre en MAYÚSCULAS + tracking amplio (`letterSpacing: 1.2`) — señal visual inmediata de cambio de sección, igual que un subtítulo editorial.

**Formato de etiquetas en `MetricTile`:**
- ✅ `RODILLA IZQ.` — concreto, scannable, sin ambigüedad
- ❌ `Ángulo de flexión de rodilla izquierda` — demasiado largo para escaneo rápido
- ❌ `L_KNEE` — críptico, requiere aprendizaje previo

**Regla de los 3 segundos:** Cualquier métrica activa debe poder leerse e interpretarse en ≤ 3 segundos sin conocimiento previo de la UI. Si requiere más tiempo, el label o el formato debe simplificarse.

### 2.4 CTAs — Botones de Acción Principal

Basado en las mejores prácticas de UI: el CTA debe ser claramente visible incluso en escala de grises.

**Test de escala de grises para `AppPrimaryButton`:**
- Fondo: `#00E676` (acento) → en grises: `~220/255` — muy claro, contrasta con fondo oscuro ✅
- Texto: `#000000` → en grises: `0/255` — máximo contraste ✅
- Estado disabled: `#2A302D` → en grises: `~45/255` — claramente opaco, distinguible del activo ✅

**Posicionamiento de CTAs:**
- `LiveAnalysisScreen`: CTA ("Iniciar / Detener") fijo en Zona D — **nunca se desplaza** fuera de la pantalla.
- `VideoAnalysisScreen`: CTA visible sin scroll en configuración inicial.
- `BioHomeScreen`: cada NavCard es su propio CTA — sin botón separado adicional.

**Regla de un solo CTA por pantalla:** Nunca dos `AppPrimaryButton` visibles simultáneamente. Si se necesita una acción secundaria, usar `OutlinedButton` o un `TextButton`.

---

## 3. Patrones de UI Aplicados

### 3.1 Navegación

**Patrón aplicado: `Fat Footer` adaptado → `NavCard`**

En lugar de un menú de navegación inferior (tabbar), Bio-Motion usa **cards de navegación explícitas** en la home. Justificación: la app tiene 3 flujos principales muy diferenciados — cámara, video, diagnóstico. Un tabbar implicaría que todos son accesibles en todo momento, pero durante un análisis activo no se debe navegar libremente.

**Patrón: `Breadcrumbs` implícitos vía AppBar**

Cada pantalla muestra su nombre en el AppBar + botón de regreso. No se necesita breadcrumb explícito dado que la profundidad máxima de navegación es 2 niveles (Home → Pantalla de análisis).

**Patrón: `Modal` para configuración**

La URL del backend y parámetros técnicos van en un `ModalBottomSheet` (o `Dialog`) — no en la pantalla principal. Esto aplica el principio de **Progressive Disclosure**: mostrar solo lo necesario para la tarea actual.

```
Implementación:
  IconButton(Settings) en AppBar → showModalBottomSheet(
    context,
    builder: (_) => ConnectionConfigSheet(),
  )
```

### 3.2 Feedback en Tiempo Real

**Patrón: `Feedback Loop` + `Synchronization`**

El análisis biomecánico en tiempo real es por definición un bucle de feedback: el usuario realiza el movimiento → el sistema mide → el usuario ajusta. La UI debe hacer este bucle **perceptible y sin fricción**.

**Implementación por capa:**

| Capa | Feedback | Implementación |
|---|---|---|
| Esqueleto de pose | Inmediato, visual | `CustomPainter` repinta en cada frame recibido |
| Valores numéricos | Inmediato, numérico | `setState` sin animación de transición |
| Color semántico | Inmediato, cromático | `MetricStatus` recalculado en cada update |
| `LiveIndicatorDot` | Continuo, periférico | Pulso cada 900ms — confirmación pasiva de conexión activa |
| Error WS | Inmediato, contextual | `SnackBar` con color `angleBad` y descripción accionable |

**Regla de latencia percibida:** Si el servidor no envía datos por más de **2 segundos** durante transmisión activa, mostrar un indicador de "Esperando datos…" en el HUD — no silencio. El silencio en una UI de tiempo real se interpreta como error.

```dart
// Implementar con Timer en _CameraStreamScreenState:
Timer? _stalledTimer;

// Al recibir cada frame:
_stalledTimer?.cancel();
_stalledTimer = Timer(const Duration(seconds: 2), () {
  if (mounted) setState(() => _isStalled = true);
});

// En el HUD: if (_isStalled) → mostrar 'Esperando servidor…' en textSecondary
```

**Patrón: `Input Feedback` → Validación de ángulos**

Cuando un ángulo entra en zona `bad`, no basta con cambiar el color — agregar una **micro-vibración háptica** (solo móvil nativo):

```dart
import 'package:flutter/services.dart';

// En AngleFormatter, al detectar cambio a MetricStatus.bad:
HapticFeedback.mediumImpact();
```

Esto cierra el bucle sensorial: visual (color) + táctil (vibración) → el usuario recibe confirmación sin mirar la pantalla.

### 3.3 Formularios y Configuración

**Patrón: `Good Defaults` (Buenas opciones predeterminadas)**

Los valores por defecto deben ser correctos para el caso de uso más común, de modo que el usuario nunca tenga que configurar nada para empezar:

| Campo | Default actual | Default recomendado | Justificación |
|---|---|---|---|
| URL del API | `http://localhost:8000` | `http://localhost:8000` | Correcto para desarrollo ✅ |
| FPS de análisis | `12` | `10` | Reduce carga en red móvil sin perder fluidez |
| Vista previa desde servidor | `true` | `true` | El usuario necesita ver el frame para confiar en el análisis ✅ |
| Archivo de video | `SentadillaProfunda.mp4` | Campo vacío con hint | Evitar asumir que el archivo existe en el servidor del usuario |

**Patrón: `Forgiving Format` (Formato de Perdón)**

El campo de URL del API debe aceptar entradas con y sin `http://`, con y sin `/` final, y normalizar automáticamente:

```dart
// En ws_uri.dart — extender buildBackendWebSocketUri:
static String normalizeBaseUrl(String input) {
  var url = input.trim();
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'http://$url';         // asumir http si no se especifica
  }
  if (url.endsWith('/')) {
    url = url.substring(0, url.length - 1);  // quitar slash final
  }
  return url;
}
```

**Patrón: `Inline Validation` → Feedback inmediato en campo FPS**

```dart
// En VideoAnalysisScreen — validar FPS al perder foco, no al enviar:
TextField(
  controller: _fps,
  onChanged: (v) {
    final n = double.tryParse(v);
    setState(() => _fpsError = (n == null || n < 0.5 || n > 60)
        ? 'Entre 0.5 y 60 FPS'
        : null);
  },
  decoration: InputDecoration(
    errorText: _fpsError,
    // errorStyle usa AppColors.angleBad automáticamente via ThemeData
  ),
)
```

### 3.4 Onboarding y Orientación

**Patrón: `Empty State` (Hoja en blanco)**

Las pantallas de análisis antes de iniciar deben comunicar claramente qué hacer — no estar vacías ni mostrar solo un botón:

**`LiveAnalysisScreen` — estado idle:**
```
┌─────────────────────────────────────┐
│  [Vista de cámara o placeholder]    │
│                                     │
│       Icono: videocam_outlined      │
│                                     │
│    "Posiciónate a 2–3 metros        │
│     de la cámara, de cuerpo         │
│     entero, y pulsa Iniciar."       │
│                                     │
│       [Iniciar análisis]            │
└─────────────────────────────────────┘
```

**`VideoAnalysisScreen` — estado idle:**
```
"Introduce el nombre del archivo de video
 disponible en el servidor y pulsa Iniciar.
 El análisis procesará cada frame con
 MediaPipe BlazePose."
```

**Patrón: `Inline Hints` (Pistas en línea)**

En lugar de un tutorial separado, incorporar pistas contextuales como `subtitle` en los `MetricTile`:

```dart
MetricTile(
  label: 'RODILLA IZQ.',
  value: '127.4°',
  sublabel: 'Rango objetivo: >130° en sentadilla profunda',
  status: MetricStatus.warn,
)
```

Esto elimina la necesidad de que el usuario sepa de antemano qué es un buen ángulo de rodilla — la UI lo comunica en contexto.

**Patrón: `Progressive Disclosure` en el panel de métricas**

El panel inferior en `LiveAnalysisScreen` tiene dos estados:

- **Colapsado (default):** Muestra solo los 2–3 `MetricTile` principales. Requiere el mínimo espacio visual, maximizando la vista de la cámara.
- **Expandido (usuario arrastra hacia arriba):** Muestra historial gráfico de ángulos, asimetría bilateral, estado general de la sesión.

```
Estado colapsado → handle visible + métricas principales
Estado expandido → historial + métricas secundarias + botón "Exportar sesión"
```

---

## 4. Patrones de Diseño Persuasivo Aplicados con Ética

Los patrones persuasivos son válidos en una herramienta de salud **solo si alinean el objetivo del sistema con el beneficio real del usuario**. En Bio-Motion, esto significa:

### 4.1 `Self-Monitoring` (Auto-monitoreo)

Mostrar el historial de sesiones anteriores en `BioHomeScreen` — no para crear dependencia, sino para que el usuario pueda **observar su progreso real** en movilidad articular a lo largo del tiempo.

Implementación: persistir en `SharedPreferences` el resumen de la última sesión (fecha, ángulo promedio por articulación, % de frames en zona good).

### 4.2 `Feedback Loops` + `Peak-End Rule`

La regla del extremo-pico (Kahneman) establece que las personas recuerdan una experiencia por su **momento de mayor intensidad** y su **final**. 

Aplicación: al terminar un análisis (botón Detener / video completado), mostrar un **resumen visual breve** con:
- El mejor ángulo logrado en la sesión (peak positivo)
- El estado general (good/warn/bad) como color de fondo del resumen
- Un mensaje corto contextual: "Buena movilidad de rodilla derecha. Trabaja el rango izquierdo."

Esto hace que el usuario recuerde la sesión como útil y con dirección clara.

### 4.3 `Appropriate Challenge` (Desafío apropiado)

Los rangos ROM objetivo deben mostrarse como metas alcanzables, no como estándares inalcanzables:

- ❌ "Ángulo insuficiente" → frustrante, sin dirección
- ✅ "127° / objetivo 130° — casi allí" → gap pequeño, motivador

Implementar en el `sublabel` de `MetricTile` cuando el estado es `warn`: mostrar la diferencia en grados al objetivo.

```dart
// En AngleFormatter:
static String progressLabel(double current, double target) {
  final diff = (target - current).abs();
  if (diff < 0.5) return 'En objetivo ✓';
  if (current < target) return 'Faltan ${diff.toStringAsFixed(1)}° para el objetivo';
  return 'Sobre objetivo +${diff.toStringAsFixed(1)}°';
}
```

---

## 5. Checklist UX por Pantalla

Usar antes de marcar una pantalla como "lista para revisión" en el sprint.

### `BioHomeScreen`
- [ ] El estado del backend es visible sin interacción
- [ ] La acción más importante (análisis en vivo) está en primera posición
- [ ] Las cards tienen label + descripción de una línea, sin ambigüedad
- [ ] El CTA de cada card es legible en escala de grises
- [ ] Sin texto de más de 2 líneas en la zona visible inicial

### `LiveAnalysisScreen`
- [ ] Las métricas de ángulo están en la Zona C (panel inferior, izquierda visual)
- [ ] El HUD superior contiene solo datos técnicos secundarios (frame, FPS, latencia)
- [ ] El botón Iniciar/Detener es el único CTA primario visible
- [ ] El estado idle muestra instrucciones de posicionamiento
- [ ] Al perder datos del servidor por >2s, se muestra indicador de espera
- [ ] El cambio a `MetricStatus.bad` activa vibración háptica en móvil nativo
- [ ] La URL del backend NO es visible en la pantalla principal
- [ ] Labels de `MetricTile` en ≤ 12 caracteres

### `VideoAnalysisScreen`
- [ ] La barra de progreso del video es visible durante el análisis
- [ ] Las métricas van a la izquierda del layout en landscape
- [ ] El log de frames usa contraste reducido (datos técnicos, no clínicos)
- [ ] El resumen post-sesión aparece al completar el video
- [ ] El campo FPS tiene validación inline con mensaje claro

### `BackendStatusScreen`
- [ ] La latencia se muestra en ms con color semántico
- [ ] El auto-retry de 10s tiene contador visual
- [ ] El estado de conexión usa la misma paleta semántica que `MetricTile`

---

## 6. Referencias

- Nielsen, J. (2000). *Eyetracking Study of Web Readers*. Nielsen Norman Group.
- Pernice, K. (NN/g). *The Layer-Cake Pattern of Scanning Content on the Web*.
- Digital Studio PE. *Principios de diseño UX para webs exitosas*.
- UI-Patterns.com. *UI Design Patterns — Feedback, Navigation, Onboarding*.
- AprenderUXUI. *Artifacts y deliverables del diseño UX/UI*.
- Cook, G. et al. (2006). *Functional Movement Screen (FMS)* — referencia de rangos ROM.

---

*Este documento debe leerse junto con `bio_motion_design_standard.md`. Los tokens de color, tipografía y componentes están definidos allí; este documento define **dónde y por qué** se usan.*