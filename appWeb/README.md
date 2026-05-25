# Bio-Motion Evaluator — cliente web (`appWeb`)

Cliente React 19 + Vite + TypeScript para análisis biomecánico en navegador (HU-03, HU-04). Consume el backend FastAPI vía REST y WebSocket.

## Desarrollo local

```bash
npm install
npm run dev
```

Por defecto el dev server usa la URL del API en `localStorage` o `http://localhost:8000` (ver pantalla **Configuración**).

## Build para entrega MVP (demo jurado)

Copia las variables de [`.env.example`](.env.example) a `.env.local` (o exporta en el entorno de build):

```env
VITE_MVP_DEMO_MODE=true
VITE_MVP_SHOW_DEV=false
VITE_MVP_SHOW_SPRINT4=false
VITE_MVP_SHOW_3D=false
VITE_MVP_SHOW_ADV_VIDEO=false
VITE_MVP_SHOW_LIVE_EXERCISE=false
VITE_MVP_SHOW_REP_GOAL=false
```

Luego:

```bash
npm run build
npm run preview
```

En modo demo se muestran **Inicio**, **Análisis en vivo**, **Análisis de video** (solo gold standard), **Diagnóstico** y **Configuración**. Las rutas `/dev/*`, login, sesiones y descarga remota permanecen en el código pero no aparecen en el menú; el acceso directo por URL redirige a `/`.

Si PostgreSQL y auth están operativos el día de la sustentación, puedes activar Sprint 4 en la demo:

```env
VITE_MVP_SHOW_SPRINT4=true
```

El cliente comprobará `POST /api/v1/auth/token` antes de mostrar cuenta y descarga.

## Build con UI completa (desarrollo)

```env
VITE_MVP_DEMO_MODE=false
```

(o omite las variables; sin `VITE_MVP_DEMO_MODE=true` se asume UI completa).

## Flags (`src/config/featureFlags.ts`)

| Variable | Efecto |
|----------|--------|
| `VITE_MVP_DEMO_MODE` | Activa perfil demo y defaults HU-04 (`captureOnly: false`, fuente `file`). |
| `VITE_MVP_SHOW_DEV` | Menú y rutas `/dev/*`. |
| `VITE_MVP_SHOW_SPRINT4` | Login, perfil, historial, descarga de video. |
| `VITE_MVP_SHOW_3D` | Panel Three.js en análisis por archivo. |
| `VITE_MVP_SHOW_ADV_VIDEO` | Fuentes alternativas y toggles de ingeniería en video. |
| `VITE_MVP_SHOW_LIVE_EXERCISE` | Selector manual de ejercicio en vivo. |
| `VITE_MVP_SHOW_REP_GOAL` | Objetivo de repeticiones en configuración. |

## Stack

Ver [Tabla 4 del trabajo de grado](../docs/Formato_trabajo_de_grado.md) y contratos en [`docs/spec/`](../docs/spec/).
