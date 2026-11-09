# Evaluación de calidad del producto según ISO/IEC 25010:2023 — Bio-Motion Evaluator (MVP)

- **Fecha de la evaluación:** 2026-10-23 (estado del repositorio en esa fecha, con cambios locales sin commit). **Actualizada el 2026-10-27** con el resultado del Nivel 2 de la validación de exactitud (fila «Corrección funcional: exactitud frente a referencia», §3, §4 y §5); el resto de la evaluación no cambió.
- **Tipo:** autoevaluación técnica basada en evidencia. Los comandos se ejecutaron con apoyo de una herramienta de IA (Claude Code); cada resultado está respaldado por una salida guardada en `docs/calidad/evidencias/` o por un archivo del repositorio.
- **Plataforma donde se ejecutaron los comandos:** macOS sobre Apple Silicon (arm64), Python 3.12.13 (`~/.venvs/biomotion`), Node.js 26.6.0, TypeScript 5.9.3.

---

## 1. Alcance, modelo y método

### 1.1 Objeto evaluado

El MVP entregado: backend FastAPI (`backend/app`), núcleo de visión y goniometría (`backend/vision`, MediaPipe Pose Landmarker) y cliente web React (`appWeb/`). La interfaz principal es el **«Modo sustentación»** (tema claro; rutas `/sustentacion`, `/sustentacion/demo`, `/sustentacion/resultados`). La **«Interfaz completa»** (tema oscuro; `/inicio`, `/live-analysis`, `/video-analysis`, `/backend-status`, `/settings/connection`) es secundaria.

**Fuera del objeto:** el cliente Flutter, la captura IoT (HU-05, trasladada a trabajo futuro) y el módulo Dev Tools o de aprendizaje continuo, que ya se retiraron del código. Las herramientas de `validacion/` no son producto: sirven como instrumento de medición. Su cobertura de pruebas se reporta aparte para no inflar la del producto.

### 1.2 Alcance respecto del OE5

El objetivo específico de caracterización del rendimiento y la calidad (OE5) quedó redefinido así: *«…evaluar la calidad técnica del producto conforme a la norma ISO/IEC 25010 en las características verificables mediante evidencia técnica (adecuación funcional, eficiencia de desempeño, fiabilidad y mantenibilidad)»*.

- **Dentro del OE5 (sección 2.1, evaluación en profundidad):** adecuación funcional, eficiencia de desempeño, fiabilidad y mantenibilidad.
- **Fuera del alcance del OE5 (sección 2.2, solo inventario de la evidencia existente):** compatibilidad, capacidad de interacción, seguridad, flexibilidad y protección. **No se harán pruebas de usabilidad con usuarios reales.**

> Nota de numeración: en `docs/Formato_trabajo_de_grado.md` la lista de objetivos específicos está escrita en el fuente como 1, 2, 3, 5 y 6 (no hay 4). Markdown la renumera al mostrarla (1 a 5), y el texto que la sigue habla de «objetivos 4 y 5». Aquí, «OE5» es el objetivo que en el fuente aparece como `6.`: *Caracterización del rendimiento y calidad*.

### 1.3 Versión del modelo

Se usa la **ISO/IEC 25010:2023** (segunda edición, 2023-11), *Systems and software engineering — SQuaRE — Product quality model*. Esta edición anula y reemplaza la ISO/IEC 25010:2011.

**Cómo se verificó.** Se consultaron las páginas preliminares oficiales de la norma: portada, prólogo y cláusula 1 (vista previa IEC en VDE Verlag, `https://www.vde-verlag.de/iec-normen/preview-pdf/info_isoiec25010{ed2.0}en.pdf`). La ficha del catálogo ISO (`https://www.iso.org/standard/78176.html`) rechazó el acceso automatizado con HTTP 403. El extracto literal está en `evidencias/13_fuente_iso25010_2023.txt` y confirma lo siguiente:

- El modelo tiene nueve características.
- Se añade *safety*, con las subcaracterísticas *operational constraint, risk identification, fail safe, hazard warning, safe integration*.
- *Usability* pasa a llamarse *interaction capability*, y *portability* pasa a *flexibility*.
- Se añaden *inclusivity* y *self-descriptiveness* (en *interaction capability*), *resistance* (en *security*) y *scalability* (en *flexibility*).
- *User engagement* reemplaza a *user interface aesthetics*, y *faultlessness* reemplaza a *maturity*.
- *Accessibility* se divide en *inclusivity* y *user assistance*.

**Limitación declarada.** La vista previa no incluye la cláusula 4, donde se enumeran todas las subcaracterísticas. Las que la norma no modificó se toman de la edición 2011 y se ajustan con los cambios que declara el prólogo. El prólogo advierte también que «varias características y subcaracterísticas recibieron nombres y definiciones más precisos»; por eso, para citar definiciones literales, hay que consultar el texto completo. Las traducciones al español son del evaluador; no se verificó una versión oficial en español.

| Característica (EN, 2023) | Característica (ES) | Subcaracterísticas usadas en esta evaluación |
|---|---|---|
| Functional suitability | Adecuación funcional | Completitud, corrección y pertinencia funcional |
| Performance efficiency | Eficiencia de desempeño | Comportamiento temporal, utilización de recursos y capacidad |
| Compatibility | Compatibilidad | Coexistencia e interoperabilidad |
| Interaction capability | Capacidad de interacción | Reconocibilidad de la adecuación, aprendizaje, operabilidad, protección contra errores del usuario, compromiso del usuario, inclusividad, asistencia al usuario y autodescriptividad |
| Reliability | Fiabilidad | Ausencia de fallos (*faultlessness*), disponibilidad, tolerancia a fallos y capacidad de recuperación |
| Security | Seguridad | Confidencialidad, integridad, no repudio, responsabilidad (*accountability*), autenticidad y resistencia |
| Maintainability | Mantenibilidad | Modularidad, reusabilidad, analizabilidad, capacidad de modificación y capacidad de prueba |
| Flexibility | Flexibilidad | Adaptabilidad, escalabilidad, instalabilidad y reemplazabilidad |
| Safety | Protección (*safety*) | Restricción operativa, identificación de riesgos, fallo seguro, advertencia de peligro e integración segura |

### 1.4 Método y escala

Cada subcaracterística se evalúa con uno o más criterios verificables. Cada criterio apunta a una evidencia que es una de dos cosas: un archivo del repositorio, o un comando que se puede volver a ejecutar y cuya salida real quedó guardada en `docs/calidad/evidencias/`. No se usan cifras estimadas ni opiniones de usuarios.

| Valoración | Criterio de asignación |
|---|---|
| **Cumple** | La evidencia reproducible satisface el criterio definido, sin defectos abiertos que lo contradigan. |
| **Cumple parcialmente** | La evidencia cubre solo una parte del criterio, o cubre el criterio pero muestra defectos acotados y documentados. |
| **Sin evidencia — pendiente** | No existe evidencia que permita juzgar el criterio. Nunca se interpreta como cumplimiento. Se indica qué la produciría. |
| **No aplica** | El criterio no corresponde al alcance del MVP entregado; se justifica en cada caso. |

**Regla de agregación.** Una característica recibe «Cumple» solo si todas sus subcaracterísticas cumplen. Si alguna queda «Sin evidencia — pendiente», la característica no puede pasar de «Cumple parcialmente». Un resultado **no concluyente** según un criterio preregistrado (la medición se hizo, pero el protocolo no permite juzgar el criterio) se agrega como «Sin evidencia — pendiente»: nunca cuenta como cumplimiento.

### 1.5 Evidencias generadas en esta evaluación

| Archivo | Comando / contenido |
|---|---|
| `evidencias/01_pytest.txt` | `~/.venvs/biomotion/bin/python -m pytest -q` → **92 passed** (antes de la corrección de `/ws/pose-stream`; ver `evidencias/14`) |
| `evidencias/02_pytest_coleccion.txt` | `pytest --co -q`: lista de las 92 pruebas (antes de la corrección de `/ws/pose-stream`) |
| `evidencias/03_verificacion_angular_independiente.txt` | Barrido sintético independiente de `knee_angles_from_landmarks` (7220 casos; el script va copiado dentro del archivo) |
| `evidencias/04_tsc.txt` | `cd appWeb && npx tsc -b --force` → `exit=0` |
| `evidencias/05_eslint.txt` | `cd appWeb && npm run lint` → **11 problemas (10 errores, 1 advertencia)** |
| `evidencias/06_sonda_onnx_respaldo.txt` | Carga del clasificador ONNX y respaldo al heurístico |
| `evidencias/07_sondas_api_websocket.txt` | Sondas en proceso con `fastapi.testclient`: salud, CORS, autenticación y rutas de error de los WebSocket |
| `evidencias/08_radon.txt` | `radon cc` / `radon mi` (complejidad ciclomática e índice de mantenibilidad) |
| `evidencias/09_ruff.txt` | `ruff check` con reglas por defecto |
| `evidencias/10_cobertura.txt` | `coverage run -m pytest` con cobertura por módulo |
| `evidencias/11_acoplamiento_vision_app.txt` | Dependencias entre `backend/vision` y `backend/app` |
| `evidencias/12_estado_nivel2.txt` | Conteo de mediciones del Nivel 2 al 2026-10-23 (sin calcular estadísticos, para no romper el cegamiento). El resultado final del Nivel 2 (2026-10-27) está en `validacion/resultados/nivel2_acuerdo.md` y `nivel2_resumen.json`, generados por `validacion/analisis/analizar_nivel2.py` |
| `evidencias/13_fuente_iso25010_2023.txt` | Extracto literal de la fuente de la versión del modelo |
| `evidencias/14_pytest_tras_correccion_pose_stream.txt` | `~/.venvs/biomotion/bin/python -m pytest -q` tras corregir `/ws/pose-stream` → **95 passed**; y la prueba de regresión `tests/test_pose_stream_config_invalida.py` → 3 passed |

Las herramientas auxiliares (radon 6.0.1, ruff 0.6.9 y coverage 7.6.1) se instalaron en un entorno virtual desechable fuera del repositorio. No se modificó ningún archivo de código ni se escribió caché en el repositorio.

---

## 2. Resultados

### 2.1 Características dentro del alcance del OE5

| Característica | Subcaracterística | Métrica o criterio | Evidencia (ruta / comando) | Resultado | Valoración |
|---|---|---|---|---|---|
| Adecuación funcional | Completitud funcional | Las HU del alcance del MVP (HU-01 salud del backend, HU-02 URL base, HU-03 análisis en vivo, HU-04 análisis de vídeo, HU-06 exactitud y latencia) tienen funcionalidad implementada y accesible | `appWeb/src/router.tsx`; `backend/app/api/v1/health.py`; `backend/app/api/websocket/{video,live_pose}.py`; `docs/manuales/img/04_demo_midiendo.png`, `07_analisis_video.png`, `12_analisis_vivo_medicion.png`; `evidencias/07` (`GET /api/v1/health` → 200) | Las cinco HU tienen ruta y endpoint. Las capturas del manual muestran la medición bilateral y la asimetría en funcionamiento. HU-05 se trasladó a trabajo futuro y no cuenta. Los flujos de interfaz HU-03 y HU-04 se verifican por inspección y capturas, no con pruebas automatizadas de extremo a extremo. | **Cumple** |
| Adecuación funcional | Corrección funcional: aritmética del ángulo | Error del cálculo angular frente a ángulos de verdad conocida ≤ 1e-4° (umbral de exp1) | `validacion/resultados/exp1_verificacion_geometrica.md`; `evidencias/03` | exp1: error máximo 6,293e-13° en el barrido 0–180° y peor caso sondeado 6,000e-07°. La verificación independiente con 7220 casos y geometrías aleatorias da un máximo de 1,207e-06° en θ = 0 (flexión 180°, zona mal condicionada de `acos`) y un p99 de 2,8e-13°. La cota práctica es del orden de 1e-6°, despreciable frente a los 2–5° de la goniometría manual. | **Cumple** |
| Adecuación funcional | Corrección funcional: espacio de coordenadas | La flexión se calcula en coordenadas isótropas (sin el sesgo de anisotropía de hasta ~32°) | `tests/test_goniometria_espacio_coordenadas.py` (18 pruebas, en `evidencias/01`); `docs/spec/goniometria-espacio-de-coordenadas.md`; `backend/vision/biomechanics.py::angulos_rodilla` | Las 18 pruebas pasan. La ruta de producción prefiere `world_landmarks` o corrige por relación de aspecto. El defecto lo detectó exp2 y está cubierto por una prueba de regresión (PF-10). | **Cumple** |
| Adecuación funcional | Corrección funcional: tolerancia a la oblicuidad de la cámara | Margen de azimut en el que el error se mantiene < 5° | `validacion/resultados/exp2_sensibilidad_oblicuidad.md` | Peor caso 2D: 23,6° (ortográfica) y 26,9° (perspectiva). La consigna operativa de ±15° deja el error medio en 0,98° y el máximo en 1,99°. Es una cota sintética conservadora, no calibrada sobre el sistema real (el propio informe lo declara). El sistema no detecta el plano de cámara, y exp3 registra lecturas por encima de 150° (anatómicamente imposibles) en tomas no sagitales. | **Cumple parcialmente** |
| Adecuación funcional | Corrección funcional: exactitud frente a referencia (Nivel 2) | MAE sistema-Tracker ≤ 7,0°, ICC(2,1) ≥ 0,85; criterio habilitante: MAE intraobservador ≤ 3,0° | `validacion/resultados/nivel2_acuerdo.md`, `nivel2_resumen.json`; `validacion/datos/nivel2/IMG_6310/bitacora_nivel2.md` (2026-10-27) | Protocolo preregistrado ejecutado: sesión 1 con 75 de 76 mediciones y sesión 2 con 26 de 26 (98,9 h después). Criterio habilitante: MAE intraobservador 3,07° (n = 25) frente a ≤ 3,0° → **no cumple**, por lo que el Nivel 2 es **no concluyente** según el criterio preregistrado. El remedio (a) no se aplicó (salida (b), protocolo §2.6). Cifras sistema-Tracker, **solo descriptivas** (n = 75): ICC(2,1) 0,978, MAE 8,13°, sesgo −2,43°, con sesgo sistemático dependiente del rango. Un análisis exploratorio no preregistrado (`nivel2_exploratorio_2d_vs_3d.md`) da MAE 4,21° para el ángulo 2D del plano de la imagen; no cambia el veredicto. | **No concluyente** (se agrega como «Sin evidencia — pendiente») |
| Adecuación funcional | Pertinencia funcional | El sistema entrega la magnitud objeto de estudio (flexión bilateral e índice de asimetría) sin mostrar valores no interpretables | `appWeb/src/pages/sustentacion/Demo.tsx` (asimetría interpretable solo si ≥ 5°); `validacion/resultados/exp3_estabilidad_temporal.md` §7; `exp2` (asimetría espuria hasta 14,08° fuera del margen) | La interfaz principal muestra la flexión de cada rodilla y marca la asimetría por debajo del piso de ruido de 5°. No existe evidencia con usuarios de que estas funciones faciliten la tarea; eso queda fuera del OE5 por decisión de alcance. | **Cumple parcialmente** |
| Eficiencia de desempeño | Comportamiento temporal | (a) El ritmo entregado sostiene el ritmo solicitado sin acumular retraso; (b) existe una cifra única de latencia de extremo a extremo | `validacion/resultados/exp4_latencia.md` §B.2 y «Advertencia…»; reproducción: `exp4a_latencia_etapas.py`, `exp4b_latencia_e2e.py` | (a) Con 10 FPS solicitados y vista previa: 9,7 FPS efectivos, intervalo p95 de 126,94 ms y entrega p95 de 5,37 ms en bucle local. (b) **No se obtuvo**: la suma 28,02 + 5,37 = 33,4 ms p95 no es defendible (percentiles sumados, sesiones distintas y doble conteo del JPEG). No hay red real y el render del cliente no está instrumentado. | **Cumple parcialmente** |
| Eficiencia de desempeño | Utilización de recursos | Reparto del tiempo de CPU por etapa y coste de la carga útil | `exp4_latencia.md` §A.1, §A.5 y §B.2 | La inferencia de pose consume el 93,4 % del tiempo por fotograma (1080p a 640 px) y el cálculo biomecánico el 0,3 % (0,026 ms). La vista previa JPEG eleva la carga útil de 7,3 a 40,9 KiB por mensaje. No se midió memoria ni porcentaje de CPU del proceso, solo tiempos. | **Cumple parcialmente** |
| Eficiencia de desempeño | Capacidad | Rendimiento máximo del pipeline ≥ ritmo solicitado (10 FPS) | `exp4_latencia.md` §A.2 y «Presupuesto de fotograma…»; `backend/app/api/websocket/live_pose.py:66` | 125,9 FPS sostenibles (p95 de 8,32 ms por fotograma) frente a los 10 FPS solicitados, en un Apple M5 con una sola máquina y una sesión por configuración. `/ws/pose-stream` admite **un solo flujo a la vez** (`_POSE_STREAM_SLOT = asyncio.Lock()`). No se midió la capacidad con varios clientes simultáneos. | **Cumple** (un flujo, un equipo) |
| Fiabilidad | Ausencia de fallos | Pruebas automatizadas en verde y resultados deterministas | `evidencias/14` (95 passed); `evidencias/01` (92 passed antes de la corrección); `exp3_estabilidad_temporal.md` §1 (dos corridas con series idénticas, 0 celdas distintas) | Las 95 pruebas pasan y el pipeline es determinista. Las sondas encontraron dos defectos: el de `/ws/pose-stream` ya está corregido y protegido por una prueba de regresión (ver tolerancia a fallos); sigue abierta la falta de reconexión automática del cliente (ver capacidad de recuperación), y la cobertura del código de aplicación es baja (ver capacidad de prueba). | **Cumple parcialmente** |
| Fiabilidad | Disponibilidad | (a) Existe un mecanismo para comprobar el estado; (b) disponibilidad medida en operación | `backend/app/api/v1/health.py`; `evidencias/07` (`[health] 200 {'status': 'ok', 'version': '0.1.0'}`); `appWeb/src/hooks/useBackendHealth.ts` (tiempo de espera de 5 s) | (a) Sí. (b) No hay despliegue, así que no hay tiempo de servicio que medir. | **Cumple parcialmente** ((b) sin evidencia) |
| Fiabilidad | Tolerancia a fallos | Ante entradas o componentes defectuosos el servicio sigue funcionando o falla de forma controlada | `evidencias/06`; `evidencias/07`; `backend/vision/exercise_classifier.py:112-121` | **Controlados:** (1) el modelo ONNX `exercise_rf_a0eac3d7.onnx` no carga con onnxruntime 1.21.1 (*IR version 11, max supported 10*) y el sistema cae al `HeuristicExerciseClassifier` con una advertencia en el registro; (2) un JPEG corrupto en `/ws/video` produce `pose_ok:false`, `knees:null` y la conexión sigue abierta; (3) un archivo inexistente o un *path traversal* en `/ws/pose-stream` producen un cierre 4000 con mensaje. **Defecto encontrado y corregido (2026-10-23):** un primer mensaje con JSON inválido, con `target_fps` fuera de rango o con un `source` desconocido en `/ws/pose-stream` lanzaba un `ValidationError` de Pydantic no capturado y el cliente recibía un cierre anómalo, no el código 4000 documentado. La causa: con Pydantic v2, `model_validate_json` lanza `ValidationError` también ante JSON mal formado, así que el bloque `except json.JSONDecodeError` era código muerto. `live_pose.py` captura ahora `(ValidationError, json.JSONDecodeError)` y cierra con 4000. La prueba de regresión `tests/test_pose_stream_config_invalida.py` (3 casos) fallaba 3/3 antes de la corrección y pasa 3/3 después (`evidencias/14`); con el servidor real, `target_fps: 1000` cierra con 4000. Todos los casos sondeados quedan controlados. | **Cumple** |
| Fiabilidad | Capacidad de recuperación | Tras un corte, se liberan los recursos y el usuario puede reanudar | `live_pose.py` (bloque `finally`: detiene el productor); `appWeb/src/hooks/useLiveAnalysisSession.ts:335-345` (`onclose`) | El servidor libera el productor y el turno del flujo. El cliente reinicia su estado al cerrarse el WebSocket, pero **no reconecta solo** y no distingue un cierre normal de uno por error (no lee `event.code`). El usuario debe volver a iniciar la medición. | **Cumple parcialmente** |
| Mantenibilidad | Modularidad | El núcleo de goniometría no depende de la capa web; las dependencias van de `app` hacia `vision` | `evidencias/11` | `vision/biomechanics.py` y `vision/landmark_filter.py` solo dependen de `math`, `numpy` y `typing`. Pero **6 de los 21 módulos de `backend/vision`** importan de `backend/app` (`app.config`, `app.models.schemas`, `app.services.pose.mediapipe`), así que la dependencia entre paquetes es bidireccional. El núcleo de visión no está completamente desacoplado. | **Cumple parcialmente** |
| Mantenibilidad | Reusabilidad | La misma función de producción se reutiliza en la validación | `rg -l "from vision" validacion` (exp1, exp2, exp3, exp4a, `exportar_para_kinovea.py` y dos sondas) | Los experimentos miden directamente las funciones de producción (`knee_angles_from_landmarks`, `angulos_rodilla`, `extract_pose_bgr_video`), sin reimplementarlas. | **Cumple** |
| Mantenibilidad | Analizabilidad | Complejidad ciclomática media ≤ B; índice de mantenibilidad A; documentación técnica vigente | `evidencias/08`; `evidencias/09`; `docs/spec/`, `docs/guias/SETUP.md`, `docs/manuales/`, `docs/diagramas/` | CC media **A (3,61)** en 199 bloques (167 A, 25 B, 6 C y 1 F). Punto crítico: `pose_stream` en `live_pose.py`, con **CC 48 (rango F)**, que es justamente donde está el defecto de tolerancia a fallos. Los 54 módulos tienen MI de rango A. ruff reporta 8 hallazgos (6 E741, 1 F401, 1 F841). Hay especificaciones, manuales, guía de instalación y diagramas, pero el repositorio **no conserva los ADR como archivos propios**: se registran en el informe técnico (§ Registro de decisiones técnicas). `docs/arquitectura.md` conserva secciones del cliente Flutter retirado (`live_metric.dart`), y 23 de los 54 archivos `.py` empiezan con BOM UTF-8, lo que rompe algunas herramientas de análisis. | **Cumple parcialmente** |
| Mantenibilidad | Capacidad de modificación | El cliente compila en modo estricto; el análisis estático no reporta errores | `evidencias/04`; `evidencias/05` | `tsc -b` (`strict: true`) termina sin errores (`exit=0`). ESLint reporta **11 problemas (10 errores y 1 advertencia)**: 2 `react-hooks/set-state-in-effect`, 2 `react-hooks/refs`, 1 `react-hooks/purity`, 2 `react-refresh/only-export-components`, 3 `prefer-const` y 1 `react-hooks/exhaustive-deps`. Están en 5 archivos (`PoseSkeletonCanvas.tsx`, `VideoPreviewOverlays.tsx`, `useVideoAnalysisSession.ts`, `useConnectionConfig.ts` y `useHome.ts`); ninguno de ellos tiene cambios sin commit. | **Cumple parcialmente** |
| Mantenibilidad | Capacidad de prueba | Suite automatizada rápida y cobertura del código del producto | `evidencias/14`, `02`, `10` | 95 pruebas en ~4 s. Reparto: 30 sobre código de producto (`test_biomechanics` 3, `test_goniometria_espacio_coordenadas` 18, `test_paths_suffix` 3, `test_unified_payload_landmarks` 3, `test_pose_stream_config_invalida` 3) y 65 sobre el instrumento de validación (`test_acuerdo` 20, `test_nivel2` 45). Cobertura de sentencias (medida antes de añadir `test_pose_stream_config_invalida`; no se repitió): `backend/app` **2,7 %**, `backend/vision` **16,4 %** (`biomechanics.py` 74 %; `live_pose.py`, `video.py`, `realtime_engine.py` y `exercise_classifier.py` 0 %) y `validacion/analisis` 67,4 %. El cliente web no tiene pruebas automatizadas. | **Cumple parcialmente** |

### 2.2 Características fuera del alcance del OE5 (inventario de evidencia)

Estas características **no deciden el OE5**. Se registra la evidencia que existe para no darla por cumplida ni por ausente sin fundamento.

| Característica | Subcaracterística | Métrica o criterio | Evidencia (ruta / comando) | Resultado | Valoración |
|---|---|---|---|---|---|
| Compatibilidad | Interoperabilidad | Contratos versionados y documentados | `docs/spec/websocket-pose-stream.md` (`schema_version` = 1), `docs/spec/api-v1-rest.md`; `evidencias/07` (la carga útil real incluye `"schema_version":1`) | El contrato existe, está versionado y la respuesta real lo cumple en el campo observado. No hay pruebas de contrato automatizadas. | **Cumple parcialmente** |
| Compatibilidad | Coexistencia | Funciona junto a otros productos en un entorno compartido | — | No evaluado. | **Sin evidencia — pendiente** |
| Capacidad de interacción | Las ocho subcaracterísticas | Prueba con usuarios (SUS, tasa de éxito y tiempo por tarea) | `docs/Formato_trabajo_de_grado.md` § «Evaluación heurística interna (realizada)» | Solo existe una **inspección heurística interna hecha por el propio autor**, que **no es una prueba con usuarios** y no se reporta como tal. Además es anterior al «Modo sustentación» (sus mejoras citan accesos a Dev Tools, hoy retirados). Por decisión de alcance no habrá pruebas con usuarios reales. La afirmación de «contraste WCAG AA» de la memoria no se verificó en esta evaluación. | **Sin evidencia — pendiente** |
| Seguridad | Confidencialidad | CORS restringido; secretos fuera del control de versiones; datos personales protegidos | `evidencias/07`; `git ls-files` (solo `appWeb/.env.example` y `backend/.env.example`); `git check-ignore -v backend/.env appWeb/.env` (ignorados por `.gitignore:7`); `bitacora_nivel2.md` (PNG excluidos por la Ley 1581) | Los archivos `.env` no se versionan, y los fotogramas con personas identificables están excluidos de git. Con la configuración local actual, CORS responde `allow-origin: *` también a un origen ajeno. Un mensaje de error de `/ws/pose-stream` revela la ruta absoluta del servidor. | **Cumple parcialmente** (solo entorno de desarrollo) |
| Seguridad | Autenticidad | Autenticación robusta de usuarios | `backend/app/api/v1/auth.py`, `backend/app/core/security.py`, `backend/app/config.py` | El inicio de sesión es un *stub* de desarrollo: emite un JWT a partir de un correo, **sin contraseña**. La clave JWT tiene un valor por defecto inseguro de desarrollo. La autenticación es opcional y los flujos de medición no la exigen. Sin base de datos, `/api/v1/sessions` responde 503 antes de evaluar el token (`evidencias/07`). | **Sin evidencia — pendiente** |
| Seguridad | Integridad y resistencia | Validación de entradas; superficie de ataque | `tests/test_paths_suffix.py::test_resolve_path_rejects_traversal`; `evidencias/07`; `backend/app/models/schemas.py` (`PoseStreamConfig.source = "url"`) | Se bloquea el *path traversal* y hay una prueba que lo cubre. `source="url"` permite que el cliente ordene al servidor abrir una URL RTSP/HTTP arbitraria, lo que sería un riesgo de SSRF si se desplegara. No hubo pruebas de penetración. | **Sin evidencia — pendiente** |
| Seguridad | No repudio y responsabilidad | Trazabilidad de acciones por usuario | — | Fuera del alcance del MVP académico. | **Sin evidencia — pendiente** |
| Flexibilidad | Instalabilidad | Instalación verificada por plataforma | `docs/manuales/manual_instalacion.md` (l. 47: verificado en macOS Apple Silicon; tabla l. 422: `92 passed`, cifra anterior a la corrección); `evidencias/14` | macOS: verificado (95 pruebas en verde, reproducido el 2026-10-23). **Windows y Linux: no verificados**; solo están documentados en `docs/guias/SETUP.md`. Los navegadores de la tabla de requisitos (Chrome, Edge, Firefox y Safari) son declarativos: no hay registro de en cuáles se probó. | **Cumple parcialmente** |
| Flexibilidad | Adaptabilidad y escalabilidad | Comportamiento en otro hardware o con más clientes | `exp4_latencia.md` (una máquina); `live_pose.py:66` (un flujo a la vez) | Solo se midió en un equipo. La concurrencia de `/ws/pose-stream` está limitada a un flujo por diseño. | **Sin evidencia — pendiente** |
| Flexibilidad | Reemplazabilidad | Sustitución de otro producto | — | El MVP no reemplaza un producto existente. | **No aplica** |
| Protección (*safety*) | Las cinco subcaracterísticas | Análisis de riesgos para el usuario que ejecuta el gesto | `docs/Formato_trabajo_de_grado.md` (el trabajo «no evalúa efectos clínicos»); `Demo.tsx` (instrucciones de colocación; asimetría solo por encima de 5°) | Hay advertencias de uso y una limitación clínica declarada, pero no un análisis de riesgos formal. El sistema no es un dispositivo médico y no orienta sobre cargas. | **Sin evidencia — pendiente** |

> **Advertencia de seguridad (SGSI de la entidad).** El MVP no tiene ningún despliegue en producción. Antes de exponerlo fuera del equipo local, el Oficial de Seguridad de la Información debe revisar y validar la configuración (CORS, clave JWT, autenticación real, deshabilitar `source="url"`/`camera` en el servidor, TLS/WSS y mensajes de error sin rutas internas), conforme al MSPI de MinTIC y a la ISO/IEC 27001. Esta evaluación no contiene configuraciones listas para producción.

---

## 3. Síntesis por característica

**Adecuación funcional — Cumple parcialmente.** Las funciones del alcance del MVP están implementadas. La aritmética del ángulo es exacta hasta el ruido de punto flotante (cota práctica ~1e-6°), y el defecto de anisotropía está corregido y protegido por pruebas. La exactitud frente a la referencia se contrastó en el Nivel 2, pero el resultado es no concluyente según el criterio preregistrado: el comparador manual no alcanzó la resolución exigida (MAE intraobservador 3,07° frente a ≤ 3,0°), y las cifras sistema-Tracker (ICC(2,1) 0,978; MAE 8,13°) son solo descriptivas. Por eso, y porque el sistema no detecta el plano de cámara, la característica no puede llegar a «Cumple».

**Eficiencia de desempeño — Cumple parcialmente.** La capacidad está medida, no estimada: 126 FPS sostenibles frente a 10 solicitados, y la inferencia ocupa el 93,4 % del tiempo por fotograma. El ritmo de 10 FPS se sostiene sin acumular retraso. Falta una cifra única y defendible de latencia de extremo a extremo, y no se midió memoria ni concurrencia.

**Fiabilidad — Cumple parcialmente.** Las pruebas pasan, los resultados son deterministas y hay degradación controlada ante un modelo ONNX incompatible, imágenes corruptas y rutas inválidas. Las sondas encontraron una excepción no controlada en la validación del primer mensaje de `/ws/pose-stream`, que ya está corregida y cubierta por una prueba de regresión (tolerancia a fallos pasa a «Cumple»). La característica sigue en «Cumple parcialmente» porque el cliente no reconecta automáticamente tras un corte (capacidad de recuperación), la disponibilidad no se midió en operación y la cobertura del código de aplicación es baja.

**Mantenibilidad — Cumple parcialmente.** La complejidad media es baja (A, 3,61), el MI es A en todos los módulos y el cliente compila en modo estricto. En contra pesan cuatro cosas: el punto crítico `pose_stream` (CC 48), el acoplamiento bidireccional `vision`↔`app`, los 11 problemas de ESLint y una cobertura muy baja del código de aplicación (2,7 %) y del cliente (0 pruebas).

**Fuera del OE5.** Seguridad y capacidad de interacción quedan mayoritariamente «Sin evidencia — pendiente». La flexibilidad solo está verificada en macOS.

### Limitaciones de la evaluación

1. Es una autoevaluación: no la hizo un evaluador independiente. Los criterios y umbrales los fijó el propio equipo; los de exp1, exp2 y el Nivel 2 se registraron antes de medir. El análisis 2D frente a 3D del Nivel 2 es post hoc y se reporta solo como exploratorio.
2. Todas las mediciones se hicieron en un solo equipo (Apple M5, macOS) y sin red real.
3. Las sondas de la API usan `fastapi.testclient` en proceso. Reproducen la lógica del servidor, pero no el comportamiento exacto de uvicorn ante una excepción no controlada.
4. La cobertura se midió por sentencias, no por ramas.
5. Inconsistencias detectadas en `docs/Formato_trabajo_de_grado.md`. Son las siguientes y conviene corregirlas antes de citar esta evaluación:
   - La tabla «Resumen técnico del software» aún menciona IoT, el cliente Flutter, `huggingface_service` y la convención `Screen → Panel → Widget`, que es de Flutter.
   - El glosario usa los nombres de la versión 2011, y la referencia bibliográfica cita la ISO/IEC 25010:2011.
   - La matriz de pruebas da «PF-01 a PF-08: Pasa, con 47 pruebas automatizadas», pero hoy hay 95. PF-06 se refiere al módulo Dev retirado, y PF-04/PF-05 requieren `DATABASE_URL`, por lo que no se reprodujeron aquí.
   - PF-03 promete «eventos de reconexión» que el cliente no implementa.

---

## 4. Pendientes para completar la evaluación

| # | Pendiente | Qué lo produce | Archivo / procedimiento | Afecta a |
|---|---|---|---|---|
| 1 | ~~Nivel 2, sesión 2~~ **Ejecutada (2026-10-27): Nivel 2 no concluyente.** Queda pendiente una evidencia concluyente de exactitud | Remedio (a) del protocolo (dos sesiones adicionales en días distintos y mediana por fotograma) o Nivel 1 con patrón físico; además, contrastar un ángulo 2D sagital proyectado del sistema con la goniometría 2D | `analizar_nivel2.py --sesiones-extra` según `docs/guias/protocolo_validacion_exactitud.md` (§2.6); registrarlo en `bitacora_nivel2.md` | Corrección funcional (exactitud), dentro del OE5 |
| 2 | Latencia única de extremo a extremo | Instrumentar el trayecto completo en una sola sesión, con marcas de tiempo coherentes, incluido el render del cliente | Nueva ejecución de `validacion/experimentos/exp4b_latencia_e2e.py`, con resultado en `validacion/resultados/exp4_latencia.md` | Comportamiento temporal, dentro del OE5 |
| 3 | ~~Defecto de `/ws/pose-stream` con `ValidationError`~~ **Resuelto (2026-10-23)** | Se captura `pydantic.ValidationError` junto a `json.JSONDecodeError`; prueba de regresión `tests/test_pose_stream_config_invalida.py` | `backend/app/api/websocket/live_pose.py`; `evidencias/14` | Tolerancia a fallos, dentro del OE5 |
| 4 | Cobertura del código de aplicación | Pruebas de los WebSocket y del motor con `TestClient` y un vídeo corto de `tests/assets/videos/` | `tests/`; repetir `evidencias/10` | Capacidad de prueba, dentro del OE5 |
| 5 | Errores de ESLint (11) | Corrección de las reglas `react-hooks/*` y `prefer-const` | `appWeb/src/...` (5 archivos); repetir `evidencias/05` | Capacidad de modificación, dentro del OE5 |
| 6 | Verificación en Windows y Linux | Instalación limpia siguiendo `docs/manuales/manual_instalacion.md` y `pytest -q` en cada sistema, registrando la versión del sistema y del navegador usado | Añadir los resultados al manual de instalación y a `docs/calidad/evidencias/` | Flexibilidad, fuera del OE5 |
| 7 | Prueba con usuarios (SUS con ≥ 5 participantes) | **Descartada por decisión de alcance.** Si se retomara, se aplicaría el protocolo ya definido en `docs/Formato_trabajo_de_grado.md` § «Protocolo de pruebas de usuario» | — | Capacidad de interacción, fuera del OE5 |
| 8 | Revisión de seguridad previa a cualquier despliegue | Revisión del Oficial de Seguridad de la Información (MSPI / ISO 27001) | Fuera del repositorio | Seguridad, fuera del OE5 |

---

## 5. Texto para la memoria

### 5.1 Párrafo para la sección ISO/IEC 25010 (≤ 200 palabras)

> La calidad del producto se evaluó con el modelo ISO/IEC 25010:2023, limitada a las características verificables mediante evidencia técnica: adecuación funcional, eficiencia de desempeño, fiabilidad y mantenibilidad. Cada valoración se apoya en un archivo del repositorio o en un comando reproducible cuya salida se conserva en `docs/calidad/evidencias/`. El cálculo angular es exacto hasta el ruido numérico (error máximo inferior a 1,3 × 10⁻⁶ grados) y el pipeline sostiene 126 fotogramas por segundo frente a los 10 solicitados, con la inferencia de pose como etapa dominante (93,4 %). Las cuatro características resultan *cumple parcialmente*. Frente a Tracker (Nivel 2), el ángulo de flexión muestra un ICC de 0,978, favorecido por el amplio rango angular, y un error medio de 8,1° con límites de acuerdo del 95 % de −20,4° a +15,5°, pero el resultado es no concluyente según el criterio preregistrado, porque el comparador manual no alcanzó la resolución exigida (3,07° frente a ≤ 3,0°). No se obtuvo una cifra única de latencia de extremo a extremo. Se corrigió una excepción no controlada en `/ws/pose-stream`, con su prueba de regresión; el cliente no reconecta automáticamente. La cobertura del código de aplicación es baja (2,7 %). Compatibilidad, capacidad de interacción, seguridad, flexibilidad y protección quedan fuera del alcance y sin evidencia suficiente; no hubo pruebas de usabilidad con usuarios.

### 5.2 Estado del OE5

> **OE5 — cumplido parcialmente.** La evaluación ISO/IEC 25010 de las cuatro características del alcance está completa y respaldada por evidencia reproducible. Su resultado es *cumple parcialmente* en las cuatro. La caracterización de latencia por etapa está hecha, pero la cifra única de extremo a extremo no se obtuvo. La exactitud frente a la referencia se contrastó en el Nivel 2 con resultado no concluyente según el criterio preregistrado; sus cifras son descriptivas.
