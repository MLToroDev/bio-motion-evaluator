Perfecto. Con eso ajusto el plan considerando tres cosas clave: hay miembros no técnicos, la única demo estable es live analysis, y el formato incluye diapositivas.

---

## Plan de presentación — 20 minutos
### Jurado mixto · Solo live analysis estable

---

### Bloque 1 — El problema (3 min)
**Diapositivas: 2**

Arrancar con algo que cualquier persona del jurado entienda, sin jerga técnica.

- **Diap 1 — La situación real:** "Cada vez que alguien hace una sentadilla con mala técnica, está acumulando daño articular sin saberlo. Una evaluación profesional cuesta [valor], requiere un fisioterapeuta certificado, y el 90% de los deportistas nunca la hace." Imagen de gimnasio + dato de lesiones músculo-esqueléticas.
- **Diap 2 — La pregunta:** ¿Qué pasaría si cualquier persona pudiera obtener ese diagnóstico desde su computador, sin sensores, sin costo, en tiempo real? Aquí introduces Bio-Motion Evaluator en una sola frase.

El objetivo de estas dos diapositivas es que el miembro no técnico del jurado entienda *para qué sirve* el sistema antes de ver cualquier código o arquitectura.

---

### Bloque 2 — La solución y cómo funciona (3 min)
**Diapositivas: 2**

- **Diap 3 — Qué hace el sistema:** Tres puntos visuales simples. (1) La cámara captura el movimiento. (2) La inteligencia artificial detecta las articulaciones. (3) El sistema calcula ángulos y entrega un diagnóstico con colores. Sin mencionar FastAPI, WebSocket ni landmarks todavía.
- **Diap 4 — Cómo está construido (para la parte técnica del jurado):** Diagrama de tres capas simple: navegador web → servidor Python → modelo MediaPipe. Una frase sobre cada capa. Aquí mencionas brevemente la decisión de migrar de Flutter Web a React y por qué, en máximo 30 segundos.

---

### Bloque 3 — Demo en vivo (10 min) ⭐
**Sistema en pantalla**

Con solo live analysis estable, toda la demo se concentra ahí. La clave es narrarla para que el jurado no técnico entienda lo que está viendo en cada momento.

**Paso 1 — Verificación del sistema (1 min):**
Mostrar el indicador de backend en verde. Decir: "Antes de analizar, el sistema confirma que el servidor de inteligencia artificial está activo. Esto garantiza que el análisis va a funcionar."

**Paso 2 — Configuración (30 seg):**
Mostrar `settings/connection` brevemente. Decir: "La URL del servidor es configurable, lo que permite usar el sistema en red local o en la nube sin cambiar el código."

**Paso 3 — Live analysis (8 min, el centro de todo):**

Aquí narras en capas, primero para el no técnico, luego para el técnico.

Enciendes la cámara e inicias la sesión. Mientras aparece el overlay decís:

"Lo que están viendo es el esqueleto digital superpuesto sobre la imagen en tiempo real. Cada punto es una articulación detectada por el modelo MediaPipe de Google, que identifica 33 puntos del cuerpo humano en cada fotograma."

Ejecutas una sentadilla lenta y señalás los números en pantalla:

"Estos son los ángulos de flexión de rodilla izquierda y derecha, calculados geométricamente en cada fotograma. El color verde indica que el rango de movimiento es adecuado. El amarillo indica zona límite. El rojo indica una compensación que podría derivar en lesión."

Luego hacés una sentadilla asimétrica deliberadamente o te inclinás para forzar un cambio de color:

"Noten cómo el sistema detecta la asimetría bilateral en tiempo real, algo que un evaluador humano difícilmente captaría fotograma a fotograma."

Para el técnico del jurado agregás: "La comunicación ocurre por WebSocket, lo que elimina el overhead de HTTP por cada fotograma y mantiene la latencia por debajo de los umbrales medidos en nuestras pruebas, documentados en el informe técnico."

---

### Bloque 4 — Desarrollo y metodología (2 min)
**Diapositivas: 2**

Breve, sin perder al jurado no técnico.

- **Diap 5 — El proceso de desarrollo:** Tabla compacta de los 6 sprints con íconos de estado (✓ completado, ⟳ en curso, ○ planificado). No leer cada sprint, solo decir: "Sprints 1 a 3 completados son lo que acaban de ver. Sprint 4 incluye autenticación y persistencia de sesiones, actualmente en desarrollo."
- **Diap 6 — Calidad del software:** Tres características ISO/IEC 25010 con evidencia visual concreta. Usabilidad: los colores semánticos que vieron en la demo. Mantenibilidad: arquitectura modular que permite agregar nuevos ejercicios sin tocar la interfaz. Portabilidad: el mismo servidor funciona para web y para dispositivos móviles.

---

### Bloque 5 — Impacto y cierre (2 min)
**Diapositivas: 2**

Cerrar pensando en el jurado no técnico.

- **Diap 7 — Impacto real:** Tres dimensiones. Para el deportista: diagnóstico preventivo accesible sin costo. Para el ecosistema académico: primera línea de investigación en visión artificial aplicada al deporte en el Tecnológico de Antioquia. Para la industria: diferenciador de valor para plataformas de fitness.
- **Diap 8 — Próximos pasos:** Tres puntos cortos. Validación comparativa con goniómetro manual. Extensión a más articulaciones (cadera, tobillo). Motor de prescripción automática de ejercicios correctivos.

---

## Resumen de tiempos

| Bloque | Contenido | Tiempo |
|--------|-----------|--------|
| 1 | Problema (lenguaje accesible) | 3 min |
| 2 | Solución y arquitectura | 3 min |
| 3 | **Demo live analysis** | 10 min |
| 4 | Metodología y calidad | 2 min |
| 5 | Impacto y cierre | 2 min |
| **Total** | | **20 min** |

---

## Tres ajustes críticos dado que solo live analysis está estable

**Primero**, no menciones video analysis ni gold standard en la demo. Si el jurado pregunta por esa funcionalidad, respondés desde las diapositivas que está implementada y puedes mostrar el código, pero no lo pongas en el guion principal porque un fallo en vivo cuesta más que no mostrarlo.

**Segundo**, prepara un video pregrabado de 60 segundos de la demo como respaldo. Si la cámara, la red o el backend fallan el día de la presentación, lo reproduces sin que parezca un plan B, sino material de referencia.

**Tercero**, para el jurado no técnico la demo tiene que tener un momento "wow" claro. Ese momento es cuando el color cambia de verde a rojo al hacer un movimiento incorrecto. Practica ese momento específico para que sea visible y deliberado.