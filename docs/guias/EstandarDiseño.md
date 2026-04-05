# Bio-Motion Evaluator — Plan de Estandarización de Diseño Frontend
> Versión 1.0.0 · Para ejecución por agente de código  
> Stack: React + TypeScript + CSS Variables  
> Filosofía: **"Datos que se leen, no que se descifran."**

---

## 0. Contexto del Proyecto

Bio-Motion Evaluator es una herramienta de análisis biomecánico en tiempo real. El usuario —un fisioterapeuta o deportista— la usa durante el ejercicio, con luz variable, a distancia del dispositivo. Cada decisión de diseño debe responder a esta realidad:

- Los datos de ángulo articular deben leerse en < 3 segundos sin conocimiento previo
- La UI compite contra el tiempo de reacción del usuario durante el movimiento
- Confianza y precisión clínica se comunican con sobriedad, no con ornamentación

---

## 1. Design Tokens — `src/design/tokens.css`

Crear o reemplazar este archivo con las variables CSS canónicas del sistema.

```css
/* ─── Bio-Motion Design Tokens v1.0 ─────────────────────────────── */
:root {
  /* Fondos y superficies */
  --bm-background:       #0D0F0E;   /* Scaffold */
  --bm-surface:          #161A18;   /* Cards, paneles */
  --bm-surface-elevated: #1E2421;   /* Hover, modales */
  --bm-border:           #2A302D;   /* Bordes sutiles — 1px */

  /* Texto */
  --bm-text-primary:     #F0F4F2;
  --bm-text-secondary:   #8A9B93;   /* Metadatos, hints */
  --bm-text-disabled:    #4A5550;

  /* Acento */
  --bm-accent:           #00E676;
  --bm-accent-dim:       #00B25A;   /* Hover/pressed en botón primary */
  --bm-accent-muted:     #003D1E;   /* Background de badge activo */

  /* Semánticos de análisis — SOLO para métricas articulares */
  --bm-angle-good:       #00E676;
  --bm-angle-warn:       #FFB300;
  --bm-angle-bad:        #FF5252;

  /* Espaciado (múltiplos de 8) */
  --bm-space-xs:   4px;
  --bm-space-sm:   8px;
  --bm-space-md:   16px;
  --bm-space-lg:   24px;
  --bm-space-xl:   32px;
  --bm-space-xxl:  48px;

  /* Radios */
  --bm-radius-sm: 6px;
  --bm-radius-md: 10px;
  --bm-radius-lg: 16px;

  /* Tipografía */
  --bm-font-body: 'DM Sans', system-ui, sans-serif;
  --bm-font-mono: 'DM Mono', 'Fira Mono', monospace;

  /* Transiciones */
  --bm-transition-fast:   120ms ease-in-out;
  --bm-transition-normal: 200ms ease-out;
}
```

**Importar en `main.tsx`** antes de cualquier otro CSS:
```tsx
import './design/tokens.css';
import './index.css';
```

---

## 2. Tipografía — `src/design/typography.css`

```css
/* Cargar fuentes (Google Fonts o local) */
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap');

/* ─── Clases tipográficas globales ─── */

/* Títulos de pantalla */
.bm-screen-title {
  font-family: var(--bm-font-body);
  font-size: 1.0625rem;  /* 17px */
  font-weight: 600;
  color: var(--bm-text-primary);
  margin: 0;
}

/* Hero / marca */
.bm-hero-title {
  font-family: var(--bm-font-body);
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--bm-text-primary);
}

/* Encabezado de sección (UPPERCASE + tracking) */
.bm-section-header {
  font-family: var(--bm-font-body);
  font-size: 0.8125rem;  /* 13px */
  font-weight: 700;
  letter-spacing: 0.075em;
  text-transform: uppercase;
  color: var(--bm-text-secondary);
}

/* Métricas numéricas — DM Mono EXCLUSIVO para números */
.bm-metric-lg {
  font-family: var(--bm-font-mono);
  font-size: 2.25rem;   /* 36px */
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1;
}
.bm-metric-md {
  font-family: var(--bm-font-mono);
  font-size: 1.375rem;  /* 22px */
  font-weight: 400;
  line-height: 1;
}
.bm-metric-sm {
  font-family: var(--bm-font-mono);
  font-size: 0.875rem;  /* 14px */
  font-weight: 400;
}

/* Texto de cuerpo */
.bm-body {
  font-family: var(--bm-font-body);
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--bm-text-primary);
  line-height: 1.5;
}

/* Caption / datos técnicos secundarios */
.bm-caption {
  font-family: var(--bm-font-body);
  font-size: 0.6875rem;  /* 11px */
  font-weight: 400;
  color: var(--bm-text-secondary);
  line-height: 1.4;
}

/* Caption monoespaciado (frame index, FPS, latencia) */
.bm-mono {
  font-family: var(--bm-font-mono);
  font-size: 0.6875rem;
  color: var(--bm-text-secondary);
}
```

---

## 3. Componentes Base

### 3.1 `MetricTile` — Indicador de ángulo articular

**Archivo:** `src/components/MetricTile.tsx`

```tsx
import './MetricTile.css';

type MetricStatus = 'good' | 'warn' | 'bad' | 'neutral';

interface MetricTileProps {
  label: string;        // ≤ 12 caracteres, se muestra UPPERCASE
  value: string;        // Número + unidad: "127.4°", "42 ms"
  status?: MetricStatus;
  sublabel?: string;    // Contexto clínico: "Faltan 2.6° para objetivo"
}

const statusColorMap: Record<MetricStatus, string> = {
  good:    'var(--bm-angle-good)',
  warn:    'var(--bm-angle-warn)',
  bad:     'var(--bm-angle-bad)',
  neutral: 'var(--bm-text-secondary)',
};

export function MetricTile({ label, value, status = 'neutral', sublabel }: MetricTileProps) {
  return (
    <div className={`bm-metric-tile bm-metric-tile--${status}`}>
      <span className="bm-metric-tile__label">{label}</span>
      <span
        className="bm-metric-tile__value bm-metric-lg"
        style={{ color: statusColorMap[status] }}
      >
        {value}
      </span>
      {sublabel && (
        <span className="bm-metric-tile__sublabel bm-caption">{sublabel}</span>
      )}
    </div>
  );
}
```

**CSS:** `src/components/MetricTile.css`

```css
.bm-metric-tile {
  display: flex;
  flex-direction: column;
  gap: var(--bm-space-xs);
  padding: var(--bm-space-md) calc(var(--bm-space-sm) + var(--bm-space-xs));
  background: var(--bm-surface);
  border-radius: var(--bm-radius-md);
  border: 1px solid var(--bm-border);
  transition: border-color var(--bm-transition-fast), padding var(--bm-transition-fast);
}

/* Estado bad: padding reducido + border accent → señal visual de urgencia */
.bm-metric-tile--bad {
  padding: calc(var(--bm-space-sm) + var(--bm-space-xs)) var(--bm-space-md);
  border-color: var(--bm-angle-bad);
}

.bm-metric-tile__label {
  font-family: var(--bm-font-body);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.075em;
  text-transform: uppercase;
  color: var(--bm-text-secondary);
}

.bm-metric-tile__sublabel {
  margin-top: 2px;
}
```

---

### 3.2 `BmButton` — Botón estandarizado

**Archivo:** `src/components/BmButton.tsx`

```tsx
import './BmButton.css';

type ButtonVariant = 'primary' | 'outline' | 'ghost';

interface BmButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
}

export function BmButton({
  variant = 'outline',
  loading = false,
  disabled,
  children,
  className = '',
  ...rest
}: BmButtonProps) {
  return (
    <button
      className={`bm-btn bm-btn--${variant} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <span className="bm-btn__spinner" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
```

**CSS:** `src/components/BmButton.css`

```css
.bm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--bm-space-xs);
  font-family: var(--bm-font-body);
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.5rem 0.875rem;
  border-radius: var(--bm-radius-sm);
  border: 1px solid var(--bm-border);
  cursor: pointer;
  transition:
    background var(--bm-transition-fast),
    border-color var(--bm-transition-fast),
    opacity var(--bm-transition-fast),
    transform 80ms ease;
  white-space: nowrap;
}

.bm-btn:active:not(:disabled) {
  transform: scale(0.97);
}

/* Primary — CTA principal (solo 1 visible por pantalla) */
.bm-btn--primary {
  background: var(--bm-accent);
  border-color: var(--bm-accent-dim);
  color: #000000;
  font-weight: 700;
}
.bm-btn--primary:hover:not(:disabled) {
  background: var(--bm-accent-dim);
  border-color: var(--bm-accent-dim);
}

/* Outline — acción secundaria */
.bm-btn--outline {
  background: var(--bm-surface-elevated);
  color: var(--bm-text-primary);
}
.bm-btn--outline:hover:not(:disabled) {
  background: #243044;
  border-color: #4a6080;
}

/* Ghost — acción terciaria / destructiva suave */
.bm-btn--ghost {
  background: transparent;
  border-color: transparent;
  color: var(--bm-text-secondary);
}
.bm-btn--ghost:hover:not(:disabled) {
  background: var(--bm-surface-elevated);
  color: var(--bm-text-primary);
}

/* Disabled */
.bm-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
  transform: none;
}

/* Spinner */
.bm-btn__spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: bm-spin 0.7s linear infinite;
}

@keyframes bm-spin {
  to { transform: rotate(360deg); }
}
```

**Regla de oro:** Nunca renderizar dos `BmButton variant="primary"` simultáneamente. Si se necesita una acción secundaria, usar `variant="outline"` o `variant="ghost"`.

---

### 3.3 `BmInput` — Campo de texto estandarizado

**Archivo:** `src/components/BmInput.tsx`

```tsx
import './BmInput.css';

interface BmInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function BmInput({ label, error, hint, id, ...rest }: BmInputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="bm-field">
      <label className="bm-field__label" htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        className={`bm-field__input ${error ? 'bm-field__input--error' : ''}`}
        {...rest}
      />
      {error && <span className="bm-field__error" role="alert">{error}</span>}
      {!error && hint && <span className="bm-field__hint">{hint}</span>}
    </div>
  );
}
```

**CSS:** `src/components/BmInput.css`

```css
.bm-field {
  display: flex;
  flex-direction: column;
  gap: var(--bm-space-xs);
}

.bm-field__label {
  font-family: var(--bm-font-body);
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--bm-text-secondary);
}

.bm-field__input {
  font-family: var(--bm-font-body);
  font-size: 0.875rem;
  color: var(--bm-text-primary);
  background: var(--bm-surface);
  border: 1px solid var(--bm-border);
  border-radius: var(--bm-radius-md);
  padding: 0.5rem 0.75rem;
  width: 100%;
  outline: none;
  transition:
    border-color var(--bm-transition-fast),
    box-shadow var(--bm-transition-fast);
}

.bm-field__input::placeholder {
  color: var(--bm-text-disabled);
}

.bm-field__input:focus {
  border-color: var(--bm-accent);
  box-shadow: 0 0 0 2px var(--bm-accent-muted);
}

.bm-field__input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.bm-field__input--error {
  border-color: var(--bm-angle-bad);
}

.bm-field__input--error:focus {
  box-shadow: 0 0 0 2px rgba(255, 82, 82, 0.15);
}

.bm-field__error {
  font-size: 0.75rem;
  color: var(--bm-angle-warn);
  font-family: var(--bm-font-body);
}

.bm-field__hint {
  font-size: 0.75rem;
  color: var(--bm-text-disabled);
  font-family: var(--bm-font-body);
}

/* Select — mismos estilos que input */
.bm-select {
  font-family: var(--bm-font-body);
  font-size: 0.875rem;
  color: var(--bm-text-primary);
  background: var(--bm-surface);
  border: 1px solid var(--bm-border);
  border-radius: var(--bm-radius-md);
  padding: 0.5rem 0.75rem;
  width: 100%;
  outline: none;
  cursor: pointer;
  transition: border-color var(--bm-transition-fast);
}

.bm-select:focus {
  border-color: var(--bm-accent);
  box-shadow: 0 0 0 2px var(--bm-accent-muted);
}
```

---

### 3.4 `NavCard` — Tarjeta de navegación

**Archivo:** `src/components/NavCard.tsx`

```tsx
import './NavCard.css';

interface NavCardProps {
  title: string;
  subtitle: string;
  icon?: string;
  primary?: boolean;    // Primera card de la lista = más importante
  onClick?: () => void;
}

export function NavCard({ title, subtitle, icon, primary = false, onClick }: NavCardProps) {
  return (
    <button
      type="button"
      className={`bm-nav-card ${primary ? 'bm-nav-card--primary' : ''}`}
      onClick={onClick}
    >
      {icon && <span className="bm-nav-card__icon" aria-hidden="true">{icon}</span>}
      <div className="bm-nav-card__content">
        <span className="bm-nav-card__title">{title}</span>
        <span className="bm-nav-card__subtitle bm-caption">{subtitle}</span>
      </div>
      <span className="bm-nav-card__arrow" aria-hidden="true">›</span>
    </button>
  );
}
```

**CSS:** `src/components/NavCard.css`

```css
.bm-nav-card {
  display: flex;
  align-items: center;
  gap: var(--bm-space-md);
  width: 100%;
  padding: var(--bm-space-md) calc(var(--bm-space-md) + var(--bm-space-xs));
  background: var(--bm-surface);
  border: 1px solid var(--bm-border);
  border-radius: var(--bm-radius-md);
  cursor: pointer;
  text-align: left;
  transition:
    background var(--bm-transition-fast),
    border-color var(--bm-transition-fast),
    transform 80ms ease;
}

.bm-nav-card:hover {
  background: var(--bm-surface-elevated);
  border-color: #3d5244;
}

.bm-nav-card:active {
  transform: scale(0.99);
}

/* Primera card = acción principal → border accent sutil */
.bm-nav-card--primary {
  border-color: rgba(0, 230, 118, 0.25);
}

.bm-nav-card--primary:hover {
  border-color: rgba(0, 230, 118, 0.45);
  background: rgba(0, 230, 118, 0.04);
}

.bm-nav-card__icon {
  font-size: 1.25rem;
  min-width: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bm-nav-card__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bm-nav-card__title {
  font-family: var(--bm-font-body);
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--bm-text-primary);
}

.bm-nav-card__arrow {
  font-size: 1.25rem;
  color: var(--bm-text-secondary);
  line-height: 1;
}
```

---

### 3.5 `SectionHeader` — Encabezado de sección

**Archivo:** `src/components/SectionHeader.tsx`

```tsx
import './SectionHeader.css';

interface SectionHeaderProps {
  children: React.ReactNode;
}

export function SectionHeader({ children }: SectionHeaderProps) {
  return (
    <div className="bm-section-header">
      <h2 className="bm-section-header__text">{children}</h2>
      <div className="bm-section-header__rule" />
    </div>
  );
}
```

**CSS:** `src/components/SectionHeader.css`

```css
.bm-section-header {
  display: flex;
  align-items: center;
  gap: var(--bm-space-md);
  margin: var(--bm-space-lg) 0 var(--bm-space-sm);
}

.bm-section-header__text {
  font-family: var(--bm-font-body);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.075em;
  text-transform: uppercase;
  color: var(--bm-text-secondary);
  margin: 0;
  white-space: nowrap;
}

.bm-section-header__rule {
  flex: 1;
  height: 1px;
  background: var(--bm-border);
}
```

---

### 3.6 `LiveIndicatorDot` — Indicador de sesión activa

**Archivo:** `src/components/LiveIndicatorDot.tsx`

```tsx
import './LiveIndicatorDot.css';

interface LiveIndicatorDotProps {
  active: boolean;
}

export function LiveIndicatorDot({ active }: LiveIndicatorDotProps) {
  return (
    <span
      className={`bm-live-dot ${active ? 'bm-live-dot--active' : ''}`}
      aria-label={active ? 'Sesión activa' : 'Inactivo'}
      role="status"
    />
  );
}
```

**CSS:** `src/components/LiveIndicatorDot.css`

```css
.bm-live-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--bm-text-disabled);
  transition: background var(--bm-transition-normal);
}

.bm-live-dot--active {
  background: var(--bm-accent);
  animation: bm-pulse 900ms ease-in-out infinite;
}

@keyframes bm-pulse {
  0%, 100% { transform: scale(1);    opacity: 1; }
  50%       { transform: scale(0.75); opacity: 0.7; }
}
```

---

### 3.7 `StatusBadge` — Badge de estado de conexión

**Archivo:** `src/components/StatusBadge.tsx`

```tsx
import './StatusBadge.css';

type StatusType = 'connected' | 'disconnected' | 'checking';

interface StatusBadgeProps {
  status: StatusType;
}

const labels: Record<StatusType, string> = {
  connected:    'Backend conectado',
  disconnected: 'Sin conexión',
  checking:     'Comprobando…',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`bm-status-badge bm-status-badge--${status}`}>
      {labels[status]}
    </span>
  );
}
```

**CSS:** `src/components/StatusBadge.css`

```css
.bm-status-badge {
  display: inline-block;
  font-family: var(--bm-font-body);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.625rem;
  border-radius: var(--bm-radius-sm);
  border: 1px solid var(--bm-border);
}

.bm-status-badge--connected {
  background: var(--bm-accent-muted);
  color: var(--bm-accent);
  border-color: rgba(0, 230, 118, 0.2);
}

.bm-status-badge--disconnected {
  background: rgba(255, 82, 82, 0.08);
  color: var(--bm-angle-bad);
  border-color: rgba(255, 82, 82, 0.2);
}

.bm-status-badge--checking {
  background: var(--bm-surface-elevated);
  color: var(--bm-text-secondary);
}
```

---

## 4. Estructura de Archivos Objetivo

```
src/
├── design/
│   ├── tokens.css          ← CSS variables canónicas (ÚNICA fuente de verdad)
│   └── typography.css      ← Clases tipográficas globales
│
├── components/
│   ├── MetricTile.tsx + .css
│   ├── BmButton.tsx + .css
│   ├── BmInput.tsx + .css
│   ├── NavCard.tsx + .css
│   ├── SectionHeader.tsx + .css
│   ├── LiveIndicatorDot.tsx + .css
│   ├── StatusBadge.tsx + .css
│   ├── DashboardPanel.tsx   ← ya existe, actualizar colores
│   └── PoseSkeletonCanvas.tsx ← ya existe, actualizar colores
│
└── pages/
    ├── HomePage.tsx
    ├── LiveAnalysisPage.tsx
    ├── VideoAnalysisPage.tsx
    ├── BackendStatusPage.tsx
    ├── LoginPage.tsx
    ├── ProfilePage.tsx
    ├── SessionsHistoryPage.tsx
    ├── VideoDownloadPage.tsx
    └── ConnectionConfigPage.tsx
```

---

## 5. Instrucciones por Página

### 5.1 HomePage — Patrón Z

Orden de prioridad visual (de mayor a menor atención):
1. Header con LiveIndicatorDot + StatusBadge → Zona A del patrón Z
2. NavCard `primary={true}` → Análisis en vivo → Zona B (mayor peso)
3. NavCards secundarias → Zona C

```tsx
// Implementación correcta del patrón Z en HomePage:
<SectionHeader>Análisis</SectionHeader>
<div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
  <NavCard
    primary={true}               // ← PRIMERA, borde accent sutil
    title="Análisis en vivo"
    subtitle="Cámara: pose y ángulos en tiempo real."
    icon="📹"
    onClick={() => navigate('/live-analysis')}
  />
  <NavCard
    title="Análisis de video"
    subtitle="Gold standard en servidor."
    icon="🎬"
    onClick={() => navigate('/video-analysis')}
  />
</div>
```

**Estado del backend:** Usar `StatusBadge` en lugar de estilos inline.

---

### 5.2 LiveAnalysisPage — Patrón F

Zonas de atención (de primera a última fijación):

- **Zona A (HUD):** Frame index, FPS, RTT → `bm-mono bm-caption` → datos técnicos, no clínicos
- **Zona B (Video):** Cámara + esqueleto de pose → mayor área, sin texto superpuesto
- **Zona C (Métricas):** MetricTile izquierda-abajo → DM Mono 36px + color semántico
- **Zona D (CTA):** Un solo BmButton primary visible → nunca desaparece por scroll

```tsx
// Regla: métricas NUNCA en el centro-derecha (patrón F = menor atención ahí)
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
  <MetricTile
    label="Rodilla Izq."
    value={ui.leftDeg != null ? `${ui.leftDeg.toFixed(1)}°` : '—'}
    status={statusForLeft(ex)}
    sublabel={leftSublabel}
  />
  <MetricTile
    label="Rodilla Der."
    value={ui.rightDeg != null ? `${ui.rightDeg.toFixed(1)}°` : '—'}
    status={statusForRight(ex)}
    sublabel={rightSublabel}
  />
</div>
```

**Empty state (cámara off):** Mostrar instrucciones de posicionamiento, no vacío.

```tsx
{!ui.cameraOn && (
  <div className="bm-empty-state">
    <p className="bm-body" style={{ textAlign: 'center', color: 'var(--bm-text-secondary)' }}>
      Posiciónate a 2–3 metros de la cámara,<br/>
      de cuerpo entero, y pulsa Iniciar.
    </p>
    <BmButton variant="primary" onClick={() => void startCamera()}>
      Conectar cámara
    </BmButton>
  </div>
)}
```

---

### 5.3 VideoAnalysisPage — Layout 2 columnas

- Columna izquierda (panel de config): `BmInput` + `BmButton` + selects con clase `bm-select`
- Columna derecha (main): métricas en Zona C (izquierda visual), preview, log técnico al fondo
- El log de frames usa `bm-caption bm-mono` con contraste reducido — datos secundarios
- Al completar análisis: `AnalysisSummaryDialog` con peak-end rule (mejor ángulo logrado)

**Reemplazar todos los inputs inline por `BmInput`:**

```tsx
// Antes (estilo inline inconsistente):
<input value={apiBase} style={{ width: '100%', padding: 8, ... }} />

// Después (estandarizado):
<BmInput
  label="URL base del API"
  value={apiBase}
  onChange={(e) => setApiBase(e.target.value)}
  onBlur={persistApi}
  disabled={ui.running}
/>
```

---

### 5.4 BackendStatusPage

```tsx
// Latencia con color semántico usando MetricTile:
<MetricTile
  label="Latencia"
  value={latencyMs != null ? `${latencyMs} ms` : '—'}
  status={latencyStatus(latencyMs)}  // good/warn/bad según ms
/>

// Botón estandarizado:
<BmButton
  variant="outline"
  onClick={() => void check()}
  loading={loading}
>
  Comprobar /api/v1/health
</BmButton>
```

---

### 5.5 LoginPage y ProfilePage

```tsx
// Ambas páginas: reemplazar inputs inline por BmInput, botones por BmButton
<BmInput
  label="Email"
  type="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>
<BmButton variant="primary" disabled={busy} onClick={() => void signIn()}>
  {busy ? 'Solicitando…' : 'Solicitar token'}
</BmButton>
```

---

### 5.6 ConnectionConfigPage

```tsx
<BmInput
  label="URL base del API"
  value={base}
  onChange={(e) => setBase(e.target.value)}
/>
<BmInput
  label="Objetivo de repeticiones"
  hint="Vacío = sin barra de progreso"
  value={goal}
  onChange={(e) => setGoal(e.target.value)}
  inputMode="numeric"
/>
<BmButton variant="primary" onClick={save}>
  Guardar
</BmButton>
```

---

## 6. Patrones de UI a Implementar

### 6.1 Validación Inline (Inline Validation)

Mostrar error en el campo donde ocurre, inmediatamente, sin esperar submit:

```tsx
// En VideoAnalysisPage — campo FPS:
<BmInput
  label="Target FPS"
  value={fpsText}
  onChange={(e) => setFpsText(e.target.value)}
  error={fpsParsed.error}   // "Entre 0.5 y 60 FPS"
  disabled={ui.running}
/>
```

### 6.2 Peak-End Rule — Resumen post-sesión

Al terminar análisis, el `AnalysisSummaryDialog` debe mostrar:
- El mejor ángulo logrado (peak positivo, en DM Mono, color `good`)
- Estado general como color de fondo del resumen
- Mensaje motivador: "Buena movilidad de rodilla derecha. Trabaja el rango izquierdo."

### 6.3 Appropriate Challenge — Sublabel en MetricTile

```tsx
// Cuando status === 'warn', mostrar el gap al objetivo:
sublabel={status === 'warn' ? `Faltan ${(130 - deg).toFixed(1)}° para el objetivo` : undefined}
```

### 6.4 Self-Monitoring — Última sesión en Home

```tsx
// Ya implementado en HomePage — asegurar que el resumen sea legible:
<div style={{
  padding: 16,
  background: 'var(--bm-surface)',
  borderRadius: 'var(--bm-radius-md)',
  border: '1px solid var(--bm-border)',
}}>
  <p className="bm-caption">
    {lastSession ?? 'Aún no hay resumen de sesión guardado.'}
  </p>
</div>
```

---

## 7. Animaciones y Transiciones

| Contexto | Duración | Curva | Propiedad animada |
|---|---|---|---|
| Cambio de estado MetricTile | 120ms | ease-in-out | border-color, color |
| Hover en NavCard / BmButton | 120ms | ease-in-out | background, border-color |
| Pulso LiveIndicatorDot | 900ms, infinite | ease-in-out | transform, opacity |
| Spinner de loading | 700ms, linear | — | rotate |
| Transición entre rutas | 200ms | ease-out | opacity |

**Regla absoluta:** Los valores numéricos de métricas en tiempo real (ángulos de rodilla, FPS, latencia) **NO se animan**. El cambio debe ser inmediato — transmite precisión clínica. Ninguna animación supera los 300ms.

---

## 8. Accesibilidad (WCAG AA)

- Contraste mínimo 4.5:1 en texto sobre `--bm-surface` (#161A18)
- `good` (#00E676): ratio ≈ 9.8:1 ✓
- `warn` (#FFB300): ratio ≈ 7.2:1 ✓
- `bad` (#FF5252): ratio ≈ 5.1:1 ✓
- Todos los inputs deben tener `label` asociado (via `htmlFor` + `id`)
- Estados de error con `role="alert"` para lectores de pantalla
- `LiveIndicatorDot` con `aria-label` y `role="status"`
- Botones disabled deben tener texto legible en grises (test: screenshot en B&W)

---

## 9. Checklist de Verificación por Pantalla

Ejecutar antes de marcar una pantalla como lista.

### Todas las pantallas
- [ ] No hay colores hardcodeados — todo usa `var(--bm-...)`
- [ ] No hay `font-family` inline — todo usa variables tipográficas
- [ ] Números en DM Mono, texto en DM Sans
- [ ] Grilla de 8px (padding/gap son múltiplos de 4 o 8px)
- [ ] Un solo `BmButton variant="primary"` visible

### HomePage
- [ ] NavCard de Análisis en vivo es `primary={true}` y está primera
- [ ] StatusBadge visible sin interacción
- [ ] No hay texto de más de 2 líneas en zona visible inicial

### LiveAnalysisPage
- [ ] MetricTile en zona inferior-izquierda
- [ ] HUD superior solo datos técnicos (DM Mono caption)
- [ ] Empty state muestra instrucciones de posicionamiento
- [ ] URL del backend NO visible en pantalla principal

### VideoAnalysisPage
- [ ] BmInput en todos los campos de configuración
- [ ] Log de frames usa contraste reducido (bm-caption bm-mono)
- [ ] AnalysisSummaryDialog aparece al completar

### BackendStatusPage
- [ ] MetricTile para latencia con color semántico
- [ ] BmButton con estado loading

---

## 10. Migraciones de Estilo Inline

Reemplazar estos patrones en todas las páginas:

| ❌ Antes | ✓ Después |
|---|---|
| `color: '#ff6b6b'` | `color: var(--bm-angle-bad)` |
| `color: 'var(--bm-angle-warn)'` | Ya correcto |
| `background: '#1a2332'` | `background: var(--bm-surface)` |
| `border: '1px solid #2d3a4d'` | `border: 1px solid var(--bm-border)` |
| `background: '#243044'` | `background: var(--bm-surface-elevated)` |
| `font-size: 0.9rem` inline | Clase `.bm-body` |
| `font-size: 0.8rem` inline | Clase `.bm-caption` |
| `borderRadius: 8` inline | `var(--bm-radius-md)` |
| `padding: 8` inline | `var(--bm-space-sm)` |

---

*Este documento es la fuente de verdad para la estandarización frontend de Bio-Motion Evaluator.*  
*Cualquier desviación debe justificarse con una razón clínica o de UX específica.*