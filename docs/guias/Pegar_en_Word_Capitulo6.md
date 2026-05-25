# Contenido listo para Word (Capítulo 6 — observaciones asesor)

Copiar cada bloque en el `.docx` sustituyendo la sección indicada. Fuente alineada: `docs/Formato_trabajo_de_grado.md`.

**Importar macros:** `Alt+F11` → borrar módulos viejos si ya existían → Importar:

1. `docs/guias/ActualizarTesisBioMotion.bas` — corrección amplia del cap. 6.
2. `docs/guias/CorregirTablasPendientesTesis.bas` — **solo pendientes** detectados en la auditoría del `.docx` (pies Tabla 18/25/29, HU-06/07, índice 26–31, BH-02 § 6.10.1).

Si Word dice *too many continuations*, no pegue el código a mano; use los `.bas` del repo.

**Orden recomendado:** `ActualizarTesisBioMotion` → `CorregirTablasPendientesTesis` → actualizar campos del índice de tablas.

---

## A. Índice de tablas (sustituir listado viejo)

**Automático:** `SoloActualizarIndiceDeTablas` o `ActualizarTesisBioMotion`; luego `CorregirTablasPendientesTesis` si el índice aún muestra dos «Tabla 26» o Tabla 28–30 desfasadas respecto al cuerpo.

**Manual (solo si la macro no encuentra el texto):** pegar este bloque en «ÍNDICE DE TABLAS»:

```
Tabla 10 Product Backlog: historias de usuario, estimaciones y ejecución
Tabla 11 Backlog técnico (BH-01, BH-02)
Tabla 12 Historia de usuario HU-01: Disponibilidad del backend
Tabla 13 Historia de usuario HU-02: Configuración de URL del servidor
Tabla 14 Entregables del Sprint 1
Tabla 15 Historia de usuario HU-03: Análisis en vivo con retroalimentación de rodillas
Tabla 16 Entregables del Sprint 2
Tabla 17 Historia de usuario HU-04: Análisis por video gold standard
Tabla 18 Entregables del Sprint 3
Tabla 19 Extensión de producto: cliente web React (Sprint 3–4)
Tabla 20–23 Extensiones Sprint 4 (auth, sesiones, descarga, 2D/3D) — ver texto narrativo
Tabla 24 Historia de usuario HU-05: Cámara IoT
Tabla 25 Entregables Sprint 5 (IoT)
Tabla 26 Backlog técnico BH-02: Matriz de pruebas funcionales
Tabla 27 Comparativa técnica: Flutter Web vs. React + Vite
Tabla 28 Casos de prueba funcional del sistema
Tabla 29 Métricas de usabilidad: objetivos y resultados observados
Tabla 30 Evaluación de características de calidad del sistema (ISO/IEEE)
Tabla 31 Matriz de trazabilidad: funcionalidades, módulos y especificaciones
```

---

## B. Tras Tabla 10/11 — sección «Detalle de historias de usuario»

Pegar el apartado completo desde `docs/Formato_trabajo_de_grado.md`, líneas «## Detalle de historias de usuario» hasta antes de «# Planificación del sprint 1».

---

## C. Tabla 12 — HU-01

| Campo | Texto |
|-------|--------|
| NOMBRE | Disponibilidad del backend antes de analizar |
| ID | HU-01 |
| Como | deportista |
| Quiero | saber si el servidor está disponible antes de iniciar un análisis |
| Para | no perder tiempo configurando un análisis que no podrá ejecutarse |
| Criterios | Cuando: el backend está activo y la URL es correcta → Espero: GET /api/v1/health responde 200 y la pantalla muestra estado OK (**Pasa/No pasa**). Cuando: el backend está caído o la URL es incorrecta → Espero: pantalla de fallo sin confundir «sin respuesta» con «análisis completado» (**Pasa/No pasa**). |

---

## D. Tabla 13 — HU-02

| Campo | Texto |
|-------|--------|
| NOMBRE | Configuración de la URL base del servidor |
| ID | HU-02 |
| Como | usuario |
| Quiero | configurar la URL base del servidor |
| Para | que REST y WebSocket apunten al mismo host |
| Criterios | Cuando: guardo URL válida → Espero: peticiones REST y WS usan ese host (**Pasa/No pasa**). Cuando: URL vacía o mal formada → Espero: no se guarda o error explícito (**Pasa/No pasa**). |

**Nota:** Monorepo y SETUP = **BH-01** (Tabla 11), no HU.

---

## E. Tabla 15 — HU-03 (Sprint 2 — crítico)

| Campo | Texto |
|-------|--------|
| NOMBRE | Análisis en vivo con retroalimentación de rodillas |
| ID | HU-03 |
| Como | deportista |
| Quiero | analizar mi movimiento en vivo con retroalimentación de rodillas |
| Para | adaptar mi calentamiento con datos objetivos |
| Regla overlay | Esqueleto solo con landmarks con visibility ≥ 0,5; ver docs/spec/websocket-pose-stream.md |
| Criterios | (1) pose_ok true → knees.left/right_knee_flexion_angle_deg cuando computables; null → «sin dato» (**Pasa/No pasa**). (2) pose_ok false → UI «sin pose» (**Pasa/No pasa**). (3) asymmetry_high en quality_flags → alerta visible (**Pasa/No pasa**). (4) WS cortado → desconectado; reconexión reinicia análisis (**Pasa/No pasa**). (5) Sin permisos cámara / mala luz → no inicia o pose_ok false con mensaje (**Pasa/No pasa**). |

**Párrafo antes de 6.4.2:** Objetivo del sprint (HU-03): primer flujo biomecánico en tiempo real; no replica Sprint 1 ni HU-04 ni React.

---

## F. Tabla 17 — HU-04

| Campo | Texto |
|-------|--------|
| ID | HU-04 |
| Como | investigador |
| Criterios | Video .mp4/.mov/.avi/.mkv/.webm → stream_done y resumen con framesProcessed, maxLeftDeg, maxRightDeg, minLeftDeg, minRightDeg, pctGood, lastRepCount, lastExerciseLabel, lastQualityFlags (**Pasa/No pasa**). Extensión .wmv → rechazo con lista de válidas (**Pasa/No pasa**). Corte de red → interrumpido; framesProcessed parcial (**Pasa/No pasa**). |

---

## G. Sprint 4 — no usar HU-06…09 de Tabla 10

Título: **Extensiones de producto (Sprint 4)** — Autenticación JWT, sesiones PostgreSQL, descarga Celery, vistas 2D/3D. IDs sugeridos: EXT-Auth, EXT-Sesiones, etc.

## H. Sprint 5 — HU-05 Tabla 10 (IoT)

Historia **HU-05** — Cámara IoT (no HU-10).

## I. Sprint 6 — BH-02

Sustituir HU-11 por **BH-02** — Matriz § 6.10.1, resultado Pasa/No pasa por caso.

## J. Títulos APA (buscar y reemplazar en Word)

- PLANIFICACIÓN DEL SPRINT → Planificación del sprint
- DISEÑO DEL SISTEMA → Diseño del sistema
- PLAN DE PRUEBAS → Plan de pruebas
- DESPLIEGUE DEL SISTEMA → Despliegue del sistema
- Diagrama de clases. → Diagrama de clases
- Diagrama entidad relación. → Diagrama entidad-relación

Eliminar párrafos duplicados del «Objetivo del sprint» en el índice (artefacto de macro).
