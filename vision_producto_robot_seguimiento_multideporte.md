# Visión de Producto a Largo Plazo: Sistema de Captura Autónoma Multideporte

**Documento complementario a Bio-Motion Evaluator — Línea de continuidad investigativa**
**Estado: trabajo futuro (§10), fuera del alcance del trabajo de grado actual**

---

## 0. Propósito y advertencia de alcance

Este documento desarrolla una idea de producto surgida durante el desarrollo de Bio-Motion Evaluator: un sistema de captura de video **autónomo y móvil** que siga al deportista en distintos contextos (gimnasio, pista de atletismo, borde de piscina, ciclismo) para eliminar la dependencia de que el usuario posicione manualmente la cámara.

Se documenta deliberadamente **separado** de la memoria de tesis y como recomendación futura, por tres razones que conviene dejar explícitas y no diluir:

1. El motor de análisis biomecánico base (goniometría de rodilla) todavía no está cerrado ni validado contra goniometría manual (HU-06 pendiente). Comprometer esfuerzo de desarrollo en hardware robótico antes de cerrar el núcleo de visión es un riesgo de alcance que puede impedir la entrega del trabajo de grado.
2. Un sistema físico móvil autónomo introduce problemas de **robótica, mecánica, seguridad física y regulación** que no pertenecen al dominio de Ingeniería de Software puro y exceden el marco metodológico de un trabajo de grado individual con cronograma académico fijo.
3. No todos los deportes objetivo (gimnasio, natación, atletismo, ciclismo) comparten la misma solución óptima de captura — tratarlos como un solo problema de "cámara que sigue" es una simplificación que conviene corregir antes de invertir recursos.

Este documento existe para **capturar la idea con rigor**, identificar qué es realmente viable, en qué orden, y con qué riesgos — de forma que sirva como semilla de un trabajo de grado posterior, una línea de investigación del programa, o un desarrollo independiente del autor.

---

## 1. Problema a resolver

El valor de Bio-Motion Evaluator depende de que el sistema pueda observar al deportista con calidad suficiente para la estimación de pose (BlazePose exige que las articulaciones de interés estén dentro del encuadre, con buena resolución y sin oclusión severa). Hoy esto exige que el usuario:

- Coloque manualmente el dispositivo o trípode.
- Permanezca dentro de un encuadre relativamente fijo.
- Repita este proceso de posicionamiento para cada ejercicio o cambio de ángulo.

Esto es viable para una sentadilla frente a un trípode fijo. Deja de serlo en escenarios donde el deportista se desplaza en el espacio: recorrer una piscina, correr en pista, entrenar en distintas estaciones de un gimnasio, o pedalear en ruta.

**Pregunta de producto:** ¿cómo se captura video de calidad analítica de un deportista en movimiento, sin que la fricción de posicionar la cámara recaiga sobre el usuario en cada sesión?

---

## 2. Por qué "un robot que sigue con ruedas" no es la respuesta única

La idea original —un trípode con base motorizada que persigue físicamente al usuario— es intuitivamente atractiva pero resuelve el problema con la solución de mayor complejidad y riesgo posible. Antes de comprometerse con ella, vale la pena mapear el espacio de soluciones completo, porque **cada deporte objetivo tiene una geometría de movimiento distinta**, y la solución óptima no es la misma en los cuatro casos:

| Deporte | Patrón de movimiento del sujeto | Solución de captura más adecuada | Por qué |
|---|---|---|---|
| Gimnasio (fuerza) | Cuasi-estático, cambia de estación cada pocos minutos | Cámara fija por estación, o trípode manual (estado actual) | El sujeto no se desplaza durante el ejercicio; el problema no es de tracking sino de reposicionamiento entre estaciones |
| Atletismo / pista | Desplazamiento lineal en carril acotado (400 m típico) | Cámara fija gran angular + *tracking* digital (pan/zoom por software) | El espacio es predecible y acotado; no se requiere mover nada físicamente |
| Natación | Desplazamiento lineal en carril de piscina (25–50 m), con el sujeto parcialmente sumergido | Cámara fija gran angular en el borde, o riel lineal fijo (no robot móvil) + housing estanco | El movimiento es sobre un eje único; un riel es mecánicamente mucho más simple, robusto y seguro que un robot con ruedas cerca del agua |
| Ciclismo (ruta) | Desplazamiento de kilómetros, velocidad alta, entorno no controlado | Cámara embarcada en el propio sujeto o bicicleta (acción cam), no cámara externa que persigue | Ningún robot terrestre puede perseguir a un ciclista de forma segura y sostenida; la industria ya resolvió esto con cámaras a bordo |

**Conclusión clave:** el "robot con ruedas que sigue en todos lados" solo tendría sentido real para *uno* de los cuatro casos (quizá el gimnasio, para cambiar de estación automáticamente), y ahí compite en complejidad contra la alternativa trivial de que el usuario mueva el trípode. En pista y piscina, un **riel o cámara fija con seguimiento digital** logra el mismo resultado con una fracción del riesgo, costo y complejidad. En ciclismo, la cámara móvil externa **no es la solución que usa la industria** — se usa cámara a bordo.

Esto no descarta la idea de "cámara autónoma" como concepto: la reformula. El problema de fondo no es "cómo muevo un robot", es "cómo obtengo la vista correcta del sujeto sin fricción manual", y ese problema tiene varias soluciones más baratas y seguras que un robot antes de llegar a él.

---

## 3. Arquitecturas candidatas (de menor a mayor complejidad/riesgo)

### Nivel 0 — Cámara fija + tracking digital (recomendado como primer paso, si se retoma esta línea)
Una sola cámara de campo amplio (gran angular o 360°), fija, que cubre todo el espacio de movimiento (carril de pista, carril de piscina). El "seguimiento" ocurre en software: un modelo de detección/tracking (p. ej. YOLO + tracker tipo ByteTrack/DeepSORT, o el propio landmark de MediaPipe como ancla) recorta y sigue al sujeto dentro del frame ya capturado. No hay partes móviles.

- Precedente de industria: sistemas de cámara automática en deportes de equipo (cancha fija, panorámica digital) usan exactamente este patrón.
- Riesgo técnico: bajo-medio (visión por computador, ya es el dominio del proyecto).
- Riesgo físico/legal: nulo (no hay hardware móvil).
- Costo: bajo (una cámara de buena resolución/FOV).

### Nivel 1 — Riel lineal motorizado (para piscina o pista)
Un carril fijo instalado en el borde de la piscina o al lado de la pista, con un carro motorizado que se desplaza en un eje único siguiendo al nadador/corredor. Es un problema de control mucho más simple que un robot con ruedas: un solo grado de libertad, sin evasión de obstáculos, sin navegación.

- Riesgo técnico: medio (control de motor + tracking, pero en 1D).
- Riesgo físico/legal: medio (instalación fija, no autónoma deambulando entre personas).
- Costo: medio (requiere instalación de infraestructura, no es portátil).

### Nivel 2 — Base móvil terrestre con seguimiento (el "robot con ruedas" original)
Plataforma con ruedas, motores, tracking visual y navegación/evasión de obstáculos, operando en un espacio abierto compartido con personas (gimnasio).

- Riesgo técnico: alto (localización, navegación, tracking robusto en espacio no estructurado, batería, mantenimiento del encuadre mientras se mueve).
- Riesgo físico/legal: alto (objeto autónomo en movimiento cerca de personas y equipo de gimnasio; responsabilidad civil ante colisión o caída; necesidad de sensores de seguridad certificados).
- Costo: alto (chasis, motores, sensores de proximidad, batería, mantenimiento).
- Esto es, en la práctica, un **proyecto de robótica de servicio**, disciplina propia con su propio cuerpo de conocimiento (SLAM, control, path planning), no una extensión natural de un backend FastAPI + cliente React.

**Recomendación de secuencia:** si esta línea se retoma como trabajo de grado o proyecto futuro (por ejemplo de un estudiante de Mecatrónica o Robótica en codirección), el orden correcto es Nivel 0 → Nivel 1 → Nivel 2, validando en cada nivel si el nivel superior realmente aporta valor suficiente para justificar el salto de complejidad. Es muy posible que el Nivel 0 o 1 resuelva el 90% del valor de negocio sin necesitar nunca llegar al Nivel 2.

---

## 4. Estado del arte comercial y precios (julio 2026)

Antes de diseñar cualquiera de los niveles anteriores, vale la pena verificar qué ya existe en el mercado — porque, como suele pasar, alguien ya construyó una versión de esto. La buena noticia es que el mercado **ya validó que el camino correcto es cabezal motorizado (pan-tilt-zoom) sobre base fija, no un robot con ruedas**, lo que confirma la priorización de los Niveles 0–1 sobre el Nivel 2 de la sección anterior.

### 4.1. Panorama de productos existentes

| Producto | Mecanismo | Precio internacional (USD) | Disponibilidad en Colombia | Encaje con pista/piscina/ciclismo |
|---|---|---|---|---|
| Trípodes genéricos de seguimiento facial (KAMISAFE, YENDILI, Yeaki, etc.) | Cámara integrada, IA de rostro/cuerpo, sin tag | ~$30–60 | Sí, MercadoLibre/AliExpress | Solo gimnasio; rango útil de ~0.3–3 m. No sirve para pista ni piscina. |
| Pivo Pod (Lite / Classic) | Bluetooth + cámara del propio teléfono, tracking por app | ~$100–200 | **Sí, confirmado en MercadoLibre Colombia** | Diseñado explícitamente para entrenamiento atlético. Buena opción de entrada para gimnasio; rango limitado por el propio teléfono. |
| Obsbot Tail Air | Visión IA embarcada (sin tag), cabezal PTZ motorizado, salida NDI/HDMI/USB-C | ~$550–650 | **Sí, confirmado — Falabella Colombia (distribuidor Lumen Colombia): $2.599.900–3.639.900 COP** | Sólido para interiores (gimnasio); no tiene el alcance para pista o borde de piscina abierta. |
| SoloShot3+ (Optic25 / Optic65) | Tag GPS/RF resistente al agua, base motorizada, zoom óptico hasta 65x, hasta 600 m de alcance | ~$900–1,100+ | No hay distribuidor oficial local; solo compra directa a soloshot.com o Amazon US con envío internacional | Es el único que cubre pista + piscina + ciclismo con el alcance real necesario. |
| PIXEM / Move'N See | Tag + zoom automático, orientado a coaching profesional | Gama premium, precio no público | No | Fuera de rango para uso personal; producto B2B para clubes/academias. |

### 4.2. Costo real de traer un SoloShot a Colombia

El precio de lista (~$900–1,100 USD) no es el costo final. Importar un SoloShot3+ a Colombia por compra personal implica:

- IVA de importación (19% sobre el valor CIF).
- Posibles aranceles según partida arancelaria.
- Flete internacional y agenciamiento (Aeropost, Deprisa Cross Border u operador similar).
- Sin soporte técnico ni garantía local — cualquier reparación o reemplazo implica reenvío a EE. UU.

Estimación realista puesto en Medellín: **entre $4.5M y $6M COP** todo incluido, más el riesgo logístico de una compra internacional sin garantía en el país.

### 4.3. Ruta de validación recomendada (costo-riesgo creciente)

Dado que el motor de análisis biomecánico (no el hardware de captura) es el activo diferencial real del proyecto — ninguno de los productos anteriores hace goniometría ni detección de asimetrías, solo encuadran y graban —, la secuencia de menor riesgo es:

1. **Validar con Obsbot Tail Air** (disponible localmente, con garantía y tienda física en Colombia, ~$2.6–3.6M COP). Objetivo: confirmar que el backend de Bio-Motion Evaluator puede consumir el feed de video de una cámara PTZ real (vía NDI, HDMI o USB-C) y extraer pose de ahí, en el escenario más simple y controlado: gimnasio, interiores, distancia corta. Esto genera evidencia técnica real sobre una inversión moderada, antes de comprometer capital en una idea de producto aún no validada con usuarios.
2. **Alternativa aún más económica de entrada**: Pivo Pod (~$450.000–900.000 COP en Colombia), si se quiere una validación de concepto todavía más barata, aceptando la limitación de que la cámara es el propio teléfono.
3. **Solo si el prototipo con Obsbot (o Pivo) demuestra valor de uso real** — es decir, si de verdad se usa de forma recurrente y mejora la calidad del análisis frente a un trípode fijo — se justifica evaluar el salto a algo con mayor alcance: importar un SoloShot3+, o construir un cabezal pan-tilt propio con un servo de bajo costo sobre Raspberry Pi (reutilizando el conocimiento de IoT ya presente en el proyecto vía `iot/`), que probablemente resulte más económico que un SoloShot importado, aunque con más trabajo de ingeniería propio y menos pulido de producto.

Esta ruta evita comprometer $1,000+ USD en importación antes de tener evidencia de que el "acompañamiento autónomo" aporta valor real por encima de simplemente mover el trípode a mano.

---

## 5. Extensión del motor de análisis por deporte

Independiente de la solución de captura, cada deporte requiere un motor de análisis biomecánico distinto — esto es tan cierto para la cámara fija como para el robot, y es importante no subestimarlo:

- **Natación**: el análisis visual está condicionado por refracción y turbulencia del agua, oclusión parcial del cuerpo bajo la superficie, y necesidad frecuente de cámara subacuática o semi-sumergida para técnica de brazada. MediaPipe BlazePose no está entrenado ni validado para cuerpos parcialmente sumergidos con distorsión óptica del agua — esto requeriría investigación y posiblemente reentrenamiento o un modelo distinto, no solo "apuntar la cámara a la piscina".
- **Atletismo (running)**: métricas relevantes son distintas (cadencia, ángulo de contacto de pie, oscilación vertical, longitud de zancada) y requieren vista lateral estable con buena resolución temporal (FPS alto para capturar contacto de pie).
- **Ciclismo**: el análisis relevante suele ser de posición estática en el bikefitting (ángulo de rodilla en el punto muerto del pedaleo) más que de movimiento continuo en ruta — de hecho, gran parte del valor de "ciclismo" podría resolverse con el mismo enfoque actual del proyecto (cámara fija, rodillo/turbo estático), sin necesitar ningún sistema de seguimiento en absoluto.

Esto sugiere que **"multideporte" no debería traducirse en "un motor genérico que sirve para todo"**, sino en un roadmap de motores especializados, priorizados por dificultad y valor. El propio patrón *Data-Driven UI* que ya documentaste (LiveMetric agnóstico al tipo de ejercicio) es reutilizable en la capa de presentación, pero la capa de inferencia sí necesita trabajo específico por deporte.

---

## 6. Roadmap propuesto (si se retoma como proyecto independiente)

| Fase | Objetivo | Entregable | Riesgo principal a validar |
|---|---|---|---|
| 0 | Validar valor de uso con hardware comercial de bajo costo (Obsbot Tail Air o Pivo Pod) en gimnasio | Integración del feed de video con el backend existente + prueba de uso recurrente real | ¿El "seguimiento" aporta valor medible frente a simplemente mover el trípode a mano? |
| 1 | Validar Nivel 0 propio en un solo deporte adicional (recomendado: atletismo en pista, terreno más simple y controlado) | Cámara fija gran angular + tracking digital + integración con motor de rodilla existente | ¿El tracking digital mantiene suficiente resolución efectiva sobre el sujeto para goniometría útil a distancia? |
| 2 | Evaluar si el Nivel 0 es suficiente o si se justifica Nivel 1 (riel) para piscina | Prototipo de riel de bajo costo o descarte justificado | ¿La ganancia de calidad de imagen justifica el costo de instalación fija? |
| 3 | Explorar motor de visión específico para natación (agua) como problema de investigación aparte | Estado del arte + prueba de concepto de detección de pose subacuática | Este es en sí mismo un tema de tesis/investigación independiente |
| 4 | Ciclismo: evaluar si aporta valor diferencial frente a bikefitting estático ya cubierto por el enfoque actual | Documento de decisión (build vs. no-build) | Puede que no requiera ningún desarrollo nuevo de captura |
| 5 (largo plazo, opcional) | Solo si 0–4 demuestran valor de negocio claro: importar SoloShot3+ o construir cabezal pan-tilt propio; explorar Nivel 2 (base móvil) solo en codirección con Mecatrónica/Robótica | Propuesta de trabajo de grado interdisciplinar o adquisición justificada | Requiere equipo y competencias fuera del alcance de Ingeniería de Software en solitario (para Nivel 2); costo de importación (para SoloShot) |

---

## 7. Riesgos transversales a documentar desde ya

- **Seguridad física**: cualquier objeto motorizado autónomo cerca de personas requiere análisis de riesgo formal (paralelo conceptual a tu propia evaluación de riesgo ocupacional bajo Resolución 2646 — aquí el "riesgo" lo introduce el sistema, no el commute).
- **Privacidad**: cámaras autónomas grabando en espacios compartidos (gimnasio, piscina pública) tienen implicaciones de privacidad de terceros que no están presentes cuando el usuario controla manualmente su propio trípode.
- **Costo de hardware vs. valor percibido**: validar con usuarios reales si la fricción de mover un trípode manualmente es realmente el problema que impide adopción, antes de invertir en resolverla con robótica costosa.
- **Mantenimiento y confiabilidad**: un sistema de software puede iterarse con despliegues; un robot físico en campo tiene costos de mantenimiento, desgaste mecánico y soporte que no aplican al resto del proyecto.

---

## 8. Conclusión y recomendación

La intuición de fondo —que el sistema debería reducir la fricción de captura y "acompañar" al deportista— es válida y consistente con la visión de producto de Bio-Motion Evaluator. Pero la primera solución que viene a la mente (robot con ruedas) no es la de menor riesgo ni la de mejor relación esfuerzo/valor, no es una solución única para los cuatro deportes mencionados, y —como confirma el estado del arte comercial (§4)— el mercado ya demostró que ni siquiera hace falta inventarla desde cero.

**Recomendación concreta para la sección de Trabajo Futuro (§10) de la tesis actual:** registrar esta línea con el nivel de detalle de este documento, dejando explícito que el siguiente paso natural — si se retoma — no es diseñar hardware propio desde el Nivel 2, sino:

1. Validar con un producto comercial ya disponible en Colombia y de costo moderado (Obsbot Tail Air, o el aún más económico Pivo Pod) si el "acompañamiento autónomo" genera valor de uso real frente al trípode manual actual.
2. Solo si esa validación es positiva, avanzar a un prototipo propio de Nivel 0 (cámara fija + tracking digital) en un deporte adicional (atletismo recomendado como primer caso).
3. Reservar la importación de un SoloShot3+ o la exploración de un Nivel 2 con base móvil para una fase posterior, justificada por evidencia de uso y, en el caso del Nivel 2, en codirección con Mecatrónica/Robótica.

Esto preserva la ambición de la idea original sin comprometer el alcance ni el cronograma del trabajo de grado actual, evita una inversión de capital prematura en hardware de importación, y deja una ruta de continuidad clara y escalonada para un futuro trabajo de grado.
