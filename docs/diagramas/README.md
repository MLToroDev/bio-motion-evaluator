# Diagramas

Figuras del Bio-Motion Evaluator para la memoria del trabajo de grado y sus anexos:
causa-efecto, procesos BPMN 2.0 (AS-IS y TO-BE), arquitectura, despliegue, clases UML y
modelo entidad-relación. Todas se generan a partir de fuentes versionadas en `fuentes/` y
se contrastaron con el código del MVP (`backend/`, `appWeb/src/`), con la memoria
(`docs/Formato_trabajo_de_grado.md`) y con el protocolo de validación
(`docs/guias/protocolo_validacion_exactitud.md`).

| Carpeta | Contenido |
|---------|-----------|
| `svg/` | Figuras vectoriales (preferidas para el documento y los anexos digitales) |
| `png/` | Figuras raster, fondo blanco, ≥ 2000 px de ancho |
| `fuentes/ishikawa/` | `generar_ishikawa.py` (causas y dibujo del diagrama causa-efecto) |
| `fuentes/bpmn/` | `generar_bpmn.py`, `bpmn_lib.py` y los `.bpmn` (BPMN 2.0 con BPMN DI) |
| `fuentes/arquitectura/` | `arquitectura_componentes.dot`, `despliegue_local.dot` (Graphviz) |
| `fuentes/clases/` | `generar_clases.py` (especificación) y los `.dot` de Graphviz que produce |
| `fuentes/er/` | `modelo_entidad_relacion.dot` (Graphviz, notación pata de gallo) |
| `fuentes/generado/` | Salida bruta de `pyreverse` (trazabilidad de la estructura real) |
| `fuentes/herramientas/` | `renderizar.sh` (regenera todo), `renderizar_bpmn.mjs` y `svg_a_png.mjs` |

La numeración sigue el orden de la plantilla (problema → negocio → arquitectura →
diseño → evaluación); ajústela al índice de figuras definitivo. Los BPMN AS-IS, en vivo y
de video están en orientación vertical (pools o carriles en columnas, flujo de arriba
abajo, proporción ≈ 1:2 a 1:2,7) para insertarse a página completa en vertical; el de
validación Nivel 2 sigue en horizontal (≈ 6:1) y conviene ponerlo en una página apaisada
o como anexo. Entregue también el SVG.

---

## Problema y negocio (plantilla §2.1 y §2.2)

### Figura 1. Diagrama causa-efecto del problema

> **Figura 1.** Diagrama causa-efecto (Ishikawa) del problema de la valoración del rango de movimiento de rodilla. *Nota.* Elaboración propia (2026).

El efecto es el problema tal como lo plantea la memoria: la valoración del rango de
movimiento de rodilla es costosa, depende de un profesional y su medición manual es
variable, de modo que quien entrena suele quedarse sin una medida objetiva. Las causas se
agrupan en seis categorías (método, medición, personas, herramientas y tecnología,
entorno y costos) y todas proceden del texto ya escrito de la memoria; no se añadió
ninguna causa nueva. La tabla siguiente indica de qué sección sale cada una.

| Categoría | Causa | Sección de origen |
|-----------|-------|-------------------|
| Método | Protocolos de valoración (p. ej. FMS) que exigen atención presencial | Introducción; Definición del problema (barrera «Costo y accesibilidad») |
| Método | Evaluación funcional por observación manual tradicional | Antecedentes §2.3.3 Contexto institucional |
| Método | Preparación pre-entrenamiento genérica, sin información biomecánica | Descripción del Negocio |
| Medición | Error típico de la goniometría manual ≈ 3,4° en flexión de rodilla | Definición del problema (barrera «Variabilidad de la medición manual»; Mehta et al., 2017) |
| Medición | Concordancia entre evaluadores limitada (límites de acuerdo > 18° con otros instrumentos) | Definición del problema (barrera «Variabilidad de la medición manual») |
| Medición | Sin una magnitud propia y repetible para el usuario | Definición del problema (barrera «Ausencia de una medida objetiva a mano») |
| Personas | Requiere la intervención y la presencia de un profesional | Introducción; Descripción del Negocio |
| Personas | Quien entrena depende del juicio cualitativo de un tercero o de ninguno | Definición del problema (barrera «Ausencia de una medida objetiva a mano») |
| Personas | Usuarios que cargan peso sin conocer sus restricciones de movilidad | Descripción del Negocio |
| Herramientas y tecnología | Sin un instrumento accesible para producir la medida | Definición del problema (barrera «Ausencia de una medida objetiva a mano») |
| Herramientas y tecnología | Herramientas manuales dependientes del operador (goniómetro; video con Kinovea) | Definición del problema (goniómetro universal); Antecedentes §2.3.3 (Kinovea) |
| Entorno | Gimnasios donde se entrena con alta carga sin valoración funcional previa | Descripción del Negocio |
| Entorno | La valoración se presta en atención presencial | Definición del problema (barrera «Costo y accesibilidad») |
| Costos | Consulta profesional ≈ 46 000 a más de 100 000 COP en Medellín (referencia de mercado) | Definición del problema (barrera «Costo y accesibilidad»; Doctoralia, 2026) |
| Costos | La fase de valoración funcional se omite por su costo | Descripción del Negocio |

Las mismas afirmaciones aparecen en `generar_informe_tecnico.py`, en los bloques
«Descripción contextualizada del problema» y «Descripción del negocio».

- Fuente: `fuentes/ishikawa/generar_ishikawa.py`
- Figuras: `svg/ishikawa_problema.svg`, `png/ishikawa_problema.png`

### Figura 2. Proceso AS-IS de valoración manual del rango de movimiento de rodilla

> **Figura 2.** Proceso AS-IS de valoración manual del rango de movimiento de rodilla, sin el sistema (BPMN 2.0). *Nota.* Elaboración propia (2026).

Es el proceso actual sobre el que interviene el sistema, con tres carriles: evaluado
(deportista), evaluador (profesional) y herramienta manual. Si el deportista no accede a
una valoración profesional, por costo o por falta de un profesional, la omite y calienta
con una rutina genérica; si accede, paga y asiste a la consulta presencial, y el evaluador
mide con goniómetro universal o con video-goniometría manual en Kinovea (marcado a mano
de cadera, rodilla y tobillo). Después interpreta la medida con su juicio cualitativo y
comunica los hallazgos; las anotaciones recogen el error típico del goniómetro, la
concordancia limitada entre evaluadores y el uso de Kinovea en la institución.

Fuentes del modelo: Descripción del Negocio (fases valoración → preparación → ejecución y
omisión de la valoración), Definición del problema (costo, goniometría manual y su
variabilidad, juicio cualitativo), Antecedentes §2.3.3 (Kinovea) y protocolo de
validación §2.1 (procedimiento de video-goniometría manual: tres referencias marcadas y
ángulo plano). El nivel de detalle de los pasos de medición es una interpretación de esos
textos, que no describen el procedimiento clínico paso a paso.

- Fuente: `fuentes/bpmn/proceso_asis_valoracion_manual.bpmn`
- Figuras: `svg/proceso_asis_valoracion_manual.svg`, `png/proceso_asis_valoracion_manual.png`

### Figura 3. Proceso TO-BE de evaluación goniométrica en vivo

> **Figura 3.** Proceso TO-BE de evaluación goniométrica en vivo con el sistema, en la interfaz de demostración (BPMN 2.0). *Nota.* Elaboración propia (2026).

En la interfaz principal (`/sustentacion/demo`), el evaluador pulsa «Conectar cámara»,
se coloca de cuerpo entero, a 2–3 m y de perfil, y pulsa «Iniciar medición»; el cliente
abre el WebSocket `/ws/video`, y los fallos de permiso y de conexión (8 s) terminan en
eventos de error. Mientras el cliente envía fotogramas JPEG con contrapresión, el
servidor estima la pose, calcula los ángulos sobre `world_landmarks`, clasifica el
ejercicio y devuelve el payload v1; el cliente actualiza el esqueleto, las lecturas de
rodilla izquierda y derecha y la asimetría bilateral, que rotula «no interpretable» por
debajo de 5°. Si no se detecta pose, conserva el último esqueleto con lecturas «—»; la
sesión termina con «Detener medición» y «Apagar cámara». Una anotación recoge lo que
añade la interfaz completa (`/live-analysis`): selector de ejercicio y panel de métricas.

- Fuente: `fuentes/bpmn/proceso_evaluacion_en_vivo.bpmn`
- Figuras: `svg/proceso_evaluacion_en_vivo.svg`, `png/proceso_evaluacion_en_vivo.png`

### Figura 4. Proceso TO-BE de análisis de video

> **Figura 4.** Proceso TO-BE de análisis de video pregrabado con el sistema (BPMN 2.0). *Nota.* Elaboración propia (2026).

El análisis de video está en la interfaz completa (`/video-analysis`, enlazada desde
`/inicio`). El cliente consulta el catálogo de videos de referencia del servidor, el
evaluador elige un video y configura el análisis, y el cliente envía `PoseStreamConfig`
por `/ws/pose-stream`. El servidor valida la configuración, abre el video, construye el
perfil de procesamiento y recorre los fotogramas con un hilo productor; por cada uno
estima la pose, calcula ángulos y envía el payload v1 con vista previa, hasta enviar
`stream_done` y cerrar. El cliente acumula los fotogramas y, al cerrarse el WebSocket,
construye y muestra el resumen del análisis, con descarga opcional del CSV.

- Fuente: `fuentes/bpmn/proceso_analisis_video.bpmn`
- Figuras: `svg/proceso_analisis_video.svg`, `png/proceso_analisis_video.png`

---

## Arquitectura y despliegue

### Figura 5. Diagrama de arquitectura del sistema

> **Figura 5.** Diagrama de arquitectura de componentes de Bio-Motion Evaluator. *Nota.* Elaboración propia (2026).

El cliente es la SPA `appWeb` en el navegador, con el Modo sustentación como interfaz
principal y la Interfaz completa como secundaria; ambas capturan la cámara y hablan con el
servidor a través de los hooks de sesión. El servidor FastAPI (uvicorn, puerto 8000)
expone la API REST `/api/v1` y los WebSocket `/ws/video` y `/ws/pose-stream`, que delegan
en el núcleo de visión: MediaPipe Pose Landmarker (BlazePose), goniometría sobre
`world_landmarks` y clasificación con seguimiento de repeticiones, con el modelo de pose y
el clasificador ONNX en disco. PostgreSQL (autenticación, sesiones, trabajos de descarga),
Redis y el worker Celery (solo descarga de video por URL) y la inferencia de Hugging Face
son opcionales y se dibujan con borde discontinuo.

- Fuente: `fuentes/arquitectura/arquitectura_componentes.dot`
- Figuras: `svg/arquitectura_componentes.svg`, `png/arquitectura_componentes.png`

### Figura 6. Diagrama de despliegue

> **Figura 6.** Diagrama de despliegue del sistema en un portátil de desarrollo o de demostración (UML). *Nota.* Elaboración propia (2026).

Es el despliegue que realmente se usa: todo en un portátil, con el navegador, el
servidor de desarrollo de Vite (puerto 5173) o, como alternativa, `appWeb/dist/` servido
con `vite preview` (puerto 4173), y uvicorn con FastAPI en el entorno virtual de Python
(puerto 8000), que lee el modelo de pose, el clasificador ONNX y el catálogo de videos. El
navegador carga la SPA por HTTP y se comunica con el backend por HTTP (REST) y WebSocket.
Redis en Docker (`backend/docker-compose.yml`, puerto 6379), el worker Celery y PostgreSQL
(`DATABASE_URL`) son opcionales. No existe infraestructura de producción en el
repositorio y no se representa ninguna.

- Fuente: `fuentes/arquitectura/despliegue_local.dot`
- Figuras: `svg/despliegue_local.svg`, `png/despliegue_local.png`

---

## Diagramas de clases (UML)

**Notación común.** Rombo relleno = composición; rombo vacío = agregación; triángulo
vacío con línea continua = herencia; triángulo vacío con línea discontinua = realización
de un `Protocol`; flecha continua = asociación navegable (con multiplicidad); flecha
discontinua = dependencia (sin rótulo = uso). `+` público, `-` privado (prefijo `_` en
Python), subrayado = constante de módulo o miembro de clase, cursiva = abstracto. Los
módulos de funciones se modelan como clases con estereotipo («utility», «router»,
«websocket», «service», «module», «hook»). Las cajas blancas que solo muestran el nombre
son referencias a una clase detallada en otro diagrama.

### Figura 7. Diagrama de clases del núcleo de visión: orquestación, estimación de pose y goniometría

> **Figura 7.** Diagrama de clases del núcleo de visión: orquestación, estimación de pose y goniometría. *Nota.* Elaboración propia (2026).

`RealtimeEngineSession` orquesta, por fotograma, la estimación de pose con MediaPipe
(`pose_extractor` → `app.services.pose.mediapipe`), el cálculo goniométrico
(`biomechanics.angulos_rodilla`) y la construcción del payload WebSocket v1
(`unified_payload`), y compone de forma opcional el motor de características, el
clasificador y el seguimiento de repeticiones. Las notas fijan las dos invariantes de la
medición: flexión = 180° − ángulo interno cadera–rodilla–tobillo, y cálculo sobre
`world_landmarks` (métricos e isótropos), con repliegue a landmarks normalizados
corregidos por relación de aspecto (`docs/spec/goniometria-espacio-de-coordenadas.md`).

- Fuente: `fuentes/clases/clases_vision_orquestacion_goniometria.dot` (generada por `generar_clases.py`)
- Figuras: `svg/clases_vision_orquestacion_goniometria.svg`, `png/clases_vision_orquestacion_goniometria.png`

### Figura 8. Diagrama de clases del núcleo de visión: características, clasificación y repeticiones

> **Figura 8.** Diagrama de clases del núcleo de visión: características, clasificación de ejercicio y seguimiento de repeticiones. *Nota.* Elaboración propia (2026).

`FeatureEngine` mantiene una ventana deslizante de `PoseFrame` (45 fotogramas por
defecto) y produce un vector de 32 componentes y un `FeatureFrame`. La clasificación se
resuelve con el patrón decorador: `HysteresisClassifier` envuelve cualquier realización
del protocolo `ExerciseClassifier` (heurística, ONNX o nula) y aplica umbral, filtro EMA o
Kalman e histéresis. `RepTrackerRouter` delega en implementaciones de la clase abstracta
`RepTracker`; `SquatRepTracker` cuenta repeticiones por fases y marca `asymmetry_high`
cuando |L − R| / máx(L, R) supera el 18 %.

- Fuente: `fuentes/clases/clases_vision_clasificacion_repeticiones.dot`
- Figuras: `svg/clases_vision_clasificacion_repeticiones.svg`, `png/clases_vision_clasificacion_repeticiones.png`

### Figura 9. Diagrama de clases de la API y los servicios del backend

> **Figura 9.** Diagrama de clases de la API REST, los WebSocket y los servicios del backend FastAPI. *Nota.* Elaboración propia (2026).

`app.main` registra el router REST versionado (`/api/v1`: salud, análisis de pose,
catálogo de videos, autenticación, sesiones y descargas) y los dos WebSocket:
`/ws/video`, que recibe JPEG del navegador, y `/ws/pose-stream`, que lee el video en el
servidor (`VideoSource`) con un perfil adaptativo (`StreamProcessingPlan`). Ambos crean un
`RealtimeEngineSession` por conexión. La descarga por URL se delega a una tarea Celery que
usa yt-dlp y actualiza `VideoDownloadJobORM`; la seguridad se limita a un JWT de
desarrollo (`deps`, `security`).

- Fuente: `fuentes/clases/clases_api_servicios_backend.dot`
- Figuras: `svg/clases_api_servicios_backend.svg`, `png/clases_api_servicios_backend.png`

### Figura 10. Diagrama de clases de los esquemas de datos y la persistencia

> **Figura 10.** Diagrama de clases de los esquemas de datos (Pydantic) y de los modelos de persistencia (SQLAlchemy). *Nota.* Elaboración propia (2026).

Los esquemas de `app.models.schemas` definen los contratos de intercambio:
`PoseStreamConfig` (primer mensaje de `/ws/pose-stream`), `UnifiedWsFrameV1` (payload por
fotograma) y `PoseAnalysisResponse` (REST), además de los cuerpos y respuestas definidos
en los propios routers. Los modelos ORM heredan de `Base`: un usuario tiene cero o más
sesiones y cada sesión compone sus métricas (borrado en cascada); `VideoDownloadJobORM`
registra los trabajos de descarga. La base de datos es opcional y el análisis en vivo y
por video no persiste datos.

- Fuente: `fuentes/clases/clases_esquemas_persistencia.dot`
- Figuras: `svg/clases_esquemas_persistencia.svg`, `png/clases_esquemas_persistencia.png`

### Figura 11. Diagrama de clases del cliente web

> **Figura 11.** Diagrama de clases del cliente web appWeb: rutas, páginas, hooks de sesión, componentes y contratos con el backend. *Nota.* Elaboración propia (2026).

La ruta `/` redirige a `/sustentacion`, cuyo `SustentacionLayout` (tema claro) es la
interfaz principal con `Portada`, `Demo` y `Resultados`. `AppLayout` (tema oscuro) aloja
la interfaz completa: `Home` en `/inicio`, `LiveAnalysis`, `VideoAnalysis`,
`BackendStatus` y `ConnectionConfig`. El cliente sigue el patrón
contenedor-presentacional: las páginas delegan estado y comunicación en hooks
(`useLiveAnalysisSession`, compartido por `Demo` y `LiveAnalysis`; `useVideoAnalysis` y
`useVideoAnalysisSession`) y renderizan componentes sin lógica de red
(`PoseSkeletonCanvas`, `DashboardPanel`, `AnalysisSummaryDialog`, `PoseSkeleton3DPanel`).

- Fuente: `fuentes/clases/clases_cliente_web.dot`
- Figuras: `svg/clases_cliente_web.svg`, `png/clases_cliente_web.png`

---

## Modelo de datos

### Figura 12. Diagrama entidad-relación

> **Figura 12.** Diagrama entidad-relación del modelo de datos vigente (PostgreSQL). *Nota.* Elaboración propia (2026).

El modelo tiene cuatro tablas: un usuario (`users`) tiene cero o más sesiones
(`sessions`) y cada sesión registra cero o más métricas (`session_metrics`), con borrado en
cascada en ambas claves foráneas. `video_download_jobs` no se relaciona con las demás:
guarda el estado de los trabajos Celery de descarga por URL. Toda la base de datos es
opcional; sin `DATABASE_URL`, el análisis en vivo y por video funciona igual.

**Diferencia con las migraciones.** El diagrama sigue `backend/app/db/models.py`. Las
migraciones de `backend/alembic/versions/` todavía crean tres tablas sin modelo ORM, del
módulo de aprendizaje continuo retirado: `feature_samples` y `training_jobs`
(`20260404_0001`, con una clave foránea de `feature_samples.session_id` a `sessions.id`)
e `ingest_jobs` (`20260404_0002`). Un `alembic upgrade head` las crea igualmente; no se
dibujan porque el código vigente no las usa. Además, la migración `2cf2f413c376` sustituye
el índice único `ix_users_email` por una restricción de unicidad, que es lo que el
diagrama marca como «UQ».

- Fuente: `fuentes/er/modelo_entidad_relacion.dot`
- Figuras: `svg/modelo_entidad_relacion.svg`, `png/modelo_entidad_relacion.png`

---

## Evaluación

### Figura 13. Proceso de validación de exactitud — Nivel 2

> **Figura 13.** Proceso de validación de exactitud angular, Nivel 2: video-goniometría manual con Tracker (BPMN 2.0). *Nota.* Elaboración propia (2026).

Con los criterios pre-registrados, el investigador graba un clip propio en plano sagital
y `exportar_para_kinovea.py` exporta la serie del sistema, los PNG rotulados y la
plantilla de la sesión 1; si algún tramo de interés queda con n < 5, se fija un paso
menor antes de medir. Tras la sesión 1 en Tracker, `sortear_sesion2.py` sortea el 33 % de
los fotogramas y, pasadas al menos 48 h, se mide la sesión 2. `analizar_nivel2.py` evalúa
primero el criterio habilitante (MAE intra-observador ≤ 3,0°); si no se cumple, se aplica
el remedio (a), medir tres veces y usar la mediana, o se declara el nivel no concluyente,
y en todos los casos se calcula el acuerdo sistema–Tracker y se emite el veredicto.

- Fuente: `fuentes/bpmn/proceso_validacion_nivel2.bpmn`
- Figuras: `svg/proceso_validacion_nivel2.svg`, `png/proceso_validacion_nivel2.png`

---

## Regenerar

```bash
CHROME="/ruta/a/Google Chrome for Testing" \
PYREVERSE=/ruta/a/venv/bin/pyreverse \
docs/diagramas/fuentes/herramientas/renderizar.sh
```

El script: (1) regenera `fuentes/generado/` con `pyreverse` si se define `PYREVERSE`;
(2) escribe los `.dot` de clases y renderiza con Graphviz todos los `.dot` (clases,
arquitectura, despliegue y entidad-relación); (3) escribe los `.bpmn` y comprueba que son
XML bien formado; (4) instala, fuera del repositorio (`DIAGRAMAS_NODE_DIR`),
`bpmn-js@18.30.1`, `puppeteer-core@25.13.0` y `bpmnlint@11.14.0`, y pasa `bpmnlint` con
las reglas recomendadas; (5) importa cada BPMN en bpmn-js dentro de Chrome sin interfaz,
falla si hay advertencias de importación, y genera el diagrama causa-efecto (SVG con
Python, PNG con Chrome). `pyreverse` se instala con `pip install pylint` en un entorno
virtual aparte.

Para cambiar un diagrama se edita su especificación (`generar_ishikawa.py`,
`generar_bpmn.py`, `generar_clases.py` o el `.dot` de `arquitectura/` y `er/`), no los
archivos generados.

## Verificación realizada (2026-10-23)

- **Clases frente a `pyreverse`.** `backend/app`: 24 clases detectadas, 23 representadas
  (`_SyncSessionLocal` aparece solo como tipo de `SessionLocal`). `backend/vision`: 24
  clases (incluida `ExerciseClassifierConfig`), 24 representadas. Las funciones de módulo,
  los routers y el cliente TypeScript, que `pyreverse` no cubre, se modelaron a mano.
- **Identificadores.** Los 369 nombres de clase, atributo y método de los diagramas de
  clases se buscaron en `backend/app`, `backend/vision` y `appWeb/src`: ninguno ausente.
- **Arquitectura, despliegue y entidad-relación.** Cada elemento se contrastó con el
  código o la configuración: `appWeb/src/router.tsx`, `backend/app/main.py`,
  `backend/app/api/**`, `backend/app/config.py` (modelo `models/pose_landmarker_full.task`,
  broker Redis), `backend/app/workers/**`, `backend/docker-compose.yml` (`redis:7-alpine`,
  6379), `appWeb/package.json` (`vite`, `vite preview`), `docs/guias/SETUP.md`
  (uvicorn en 8000, Vite en 5173), `backend/README.md` (`DATABASE_URL` en 5432),
  `backend/app/db/models.py` y `backend/alembic/versions/`.
- **BPMN.** Los cuatro archivos son XML bien formado, `bpmnlint` (reglas recomendadas) no
  informa problemas y bpmn-js 18.30.1 los importa sin advertencias (también los tres
  verticales, con `isHorizontal="false"` en el BPMN DI).
- **Herramientas.** Graphviz 16.1.0; pylint/pyreverse 4.1.3 (astroid 4.3.4, Python
  3.12.13); Node.js 26.6.0; Chrome for Testing 151.0.7922.34.
