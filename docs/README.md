# Documentación — Bio-Motion Evaluator

Índice del material de soporte para el trabajo de grado y el desarrollo del monorepo.

## Estructura de carpetas

| Carpeta / archivo | Contenido |
|-------------------|-----------|
| [**Formato_trabajo_de_grado.md**](Formato_trabajo_de_grado.md) | Borrador principal de la tesis (Markdown); incluye la **bitácora** al final del cuerpo del documento. |
| [**arquitectura.md**](arquitectura.md) | Vista de capas y componentes del sistema. |
| [**diagramas/**](diagramas/README.md) | Figuras exportadas y notas para la memoria. |
| [**spec/**](spec/README.md) | Especificaciones técnicas (WebSocket, REST, contratos JSON, patrones UI). |
| [**UX-UI/**](UX-UI/) | Guías de interfaz y sistema de diseño. |
| [**guias/**](guias/) | Instalación, patrones de UI, estándares de diseño, reportes técnicos puntuales. |
| [**planificacion/**](planificacion/) | Plan del motor / roadmap y notas de apoyo al escrito. |
| [**literatura/**](literatura/apoyos/) | Resúmenes o notas de papers de referencia. |

**Código:** el frontend operativo de la tesis está en **`appWeb/`** (React). La carpeta **`app/`** (Flutter) es **legado** y no se mantiene como destino de nuevas funcionalidades salvo decisión explícita del equipo.

## Guías rápidas

| Recurso | Descripción |
|---------|-------------|
| [guias/SETUP.md](guias/SETUP.md) | Instalación (`gh`, Python, MediaPipe); Flutter solo si trabajas el legado en `app/` |
| [guias/ui_patterns.md](guias/ui_patterns.md) | Catálogo de patrones de UI de referencia |
| [guias/EstandarDiseño.md](guias/EstandarDiseño.md) | Estándar visual del proyecto |
| [guias/reporte_latencia_frames_ws_pose_stream.md](guias/reporte_latencia_frames_ws_pose_stream.md) | Notas de latencia en streaming |
| [guias/protocolo_captura_clasificacion_ejercicios.md](guias/protocolo_captura_clasificacion_ejercicios.md) | Protocolo de cámara y catálogo para clasificación de ejercicios |

Añade aquí el documento definitivo institucional (Word/LaTeX) o enlázalo según la política de la universidad.
