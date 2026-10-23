# Configuración del entorno de desarrollo

Guía de instalación del repositorio **Bio-Motion Evaluator** en **Windows**, **macOS** y **Linux**.

> El cliente web es [`appWeb/`](../../appWeb/) (React 19 + Vite) y el servidor de análisis
> es [`backend/`](../../backend/) (FastAPI + MediaPipe).

---

## 0. Requisitos previos

| Componente | Versión | Necesario para |
|------------|---------|----------------|
| **Python** | 3.10 – 3.12 | Backend, motor de visión, experimentos de validación |
| **Node.js** | 20+ | Cliente web `appWeb/` |
| **Git** | Reciente | Control de versiones |
| PostgreSQL | 15+ | *Opcional* — auth, sesiones, descarga de vídeo |
| Redis | 7.x | *Opcional* — Celery (descarga remota de vídeo) |

**Python 3.13 aún no está soportado** por las ruedas (*wheels*) de MediaPipe 0.10.x.
Usa 3.11 o 3.12.

---

## 1. Finales de línea (importante en equipos mixtos)

El repositorio almacena **LF** y define las reglas en [`.gitattributes`](../../.gitattributes).
Esto es obligatorio porque el proyecto se edita desde Windows y desde macOS: sin esa
normalización, un clon en cada sistema ve *el repositorio entero* como modificado y
resulta imposible distinguir los cambios reales.

Tras clonar, verifica que la copia de trabajo está limpia:

```bash
git status --short     # no debe listar cientos de archivos modificados
```

Si aparecen cientos de archivos modificados sin que hayas tocado nada:

```bash
git config core.autocrlf false
git config core.precomposeunicode true   # macOS: acentos en nombres de archivo (NFD/NFC)
git add --renormalize .
git status --short                        # ahora debe estar limpio
```

`core.precomposeunicode` evita que macOS duplique archivos con tildes o eñes en el
nombre (por ejemplo `EstandarDiseño.md`), que de otro modo aparecen como archivos
nuevos sin serlo.

---

## 2. Backend (FastAPI + MediaPipe)

### 2.1. Entorno virtual

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **macOS con el repositorio en un disco montado** (macFUSE, NTFS, unidad de red):
> crea el entorno virtual **fuera** del punto de montaje. Un `venv` son decenas de
> miles de archivos pequeños y los montajes síncronos lo hacen extremadamente lento:
>
> ```bash
> python3.12 -m venv ~/.venvs/biomotion
> ~/.venvs/biomotion/bin/pip install -r backend/requirements.txt
> ```
>
> Un entorno creado en Windows **no es reutilizable** en macOS: contiene
> `Scripts/` y `Lib/` en lugar de `bin/` y `lib/`. Hay que recrearlo.

### 2.2. Modelo de pose

```bash
cd backend
python scripts/download_models.py          # descarga pose_landmarker_full.task
```

Para priorizar FPS sobre precisión: `python scripts/download_models.py lite` y
`MEDIAPIPE_POSE_MODEL_PATH=models/pose_landmarker_lite.task` en `.env`
(ver [`backend/.env.example`](../../backend/.env.example)).

### 2.3. Levantar el API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Comprobación: `curl http://127.0.0.1:8000/api/v1/health` → `200`.
Documentación interactiva en `http://127.0.0.1:8000/docs`.

En Windows existe el atajo [`scripts/start-dev-backend.ps1`](../../scripts/start-dev-backend.ps1).

---

## 3. Cliente web `appWeb/` (React + Vite)

```bash
cd appWeb
npm install
cp .env.example .env.local     # Windows: copy .env.example .env.local
npm run dev
```

> **`node_modules` no es portable entre sistemas.** Igual que el entorno virtual de
> Python, contiene **binarios nativos** compilados para una plataforma concreta
> (`@rolldown/binding-win32-x64-msvc` frente a `binding-darwin-arm64`). Si el
> repositorio se comparte entre Windows y macOS a través de un disco montado, el
> `build` fallará con `MODULE_NOT_FOUND` en el sistema que no coincida. La solución
> es volver a ejecutar `npm install` al cambiar de sistema operativo.

Abre `http://localhost:5173`. La URL del backend se ajusta en
**Configuración → Conexión** o mediante las variables de
[`appWeb/.env.example`](../../appWeb/.env.example).

Las variables `VITE_MVP_*` controlan qué se muestra en la interfaz. Para desarrollo
con la UI completa: `VITE_MVP_DEMO_MODE=false`.

### Interfaz de sustentación

Ruta **`/sustentacion`** — interfaz de tema claro, mínima, pensada para proyectarse en
aula durante la defensa del trabajo de grado. Convive con la interfaz completa sin
sustituirla y no depende de las banderas `VITE_MVP_*`.

| Vista | Ruta | Contenido |
|-------|------|-----------|
| Inicio | `/sustentacion` | Identidad del trabajo y pregunta de investigación |
| Demostración | `/sustentacion/demo` | Medición angular en vivo desde la cámara |
| Resultados | `/sustentacion/resultados` | Cifras medidas y lo que queda pendiente |

Reutiliza el mismo `useLiveAnalysisSession` y el mismo `PoseSkeletonCanvas` que la
interfaz principal: no duplica la lógica de captura ni de WebSocket.

---

## 4. Pruebas

```bash
# Desde la raíz del repositorio, con el entorno virtual activo
pytest -q
```

`pytest.ini` fija `pythonpath=backend` y `testpaths=tests`, de modo que las pruebas
importan el motor de visión sin instalación adicional.

Si usas un entorno virtual fuera del repositorio:

```bash
~/.venvs/biomotion/bin/python -m pytest -q
```

---

## 5. Servicios opcionales

### PostgreSQL (sesiones y autenticación)

```bash
# Ajusta DATABASE_URL en backend/.env
cd backend
alembic upgrade head
```

Sin PostgreSQL el análisis en vivo y por vídeo funcionan igual; lo que se desactiva
es la persistencia de sesiones, la autenticación y la descarga remota de vídeo.

### Redis + Celery (descarga remota de vídeo)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 6. GitHub CLI (`gh`)

| Sistema | Instalación |
|---------|-------------|
| Windows | `winget install --id GitHub.cli -e` |
| macOS | `brew install gh` |
| Linux | Ver [cli.github.com](https://cli.github.com/) |

```bash
gh auth login
```

---

## 7. Verificación de extremo a extremo

Comprobación rápida de que el motor de visión funciona sobre un vídeo de referencia:

```bash
cd backend
PYTHONPATH=. python -c "
import cv2
from pathlib import Path
from vision.pose_extractor import extract_pose_bgr_video
cap = cv2.VideoCapture('../tests/assets/videos/SentadillaProfunda.mp4')
ret, frame = cap.read()
pf = extract_pose_bgr_video(frame, Path('models/pose_landmarker_full.task'), 0)
print('pose detectada:', pf.ok, '| rodillas:', pf.knees)
cap.release()
"
```

Debe imprimir `pose detectada: True` y los cuatro ángulos de rodilla en grados.

MediaPipe escribe líneas informativas en `stderr` al inicializar el contexto gráfico
(`I0000 ... gl_context.cc`). **No son errores.**
