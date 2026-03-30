# Configuración del entorno (Windows)

## GitHub CLI (`gh`)

1. Instalación (elige uno):
   - **winget:** `winget install --id GitHub.cli -e --accept-package-agreements`
   - **Descarga:** [https://cli.github.com/](https://cli.github.com/)
2. Cierra y vuelve a abrir la terminal para refrescar el `PATH`.
3. Autenticación (interactiva):
   ```bash
   gh auth login
   ```

## Flutter

1. Descarga el SDK desde [Install Flutter on Windows](https://docs.flutter.dev/get-started/install/windows).
2. Extrae el SDK y añade `flutter\bin` al **PATH** del sistema (o de usuario).
3. Ejecuta:
   ```bash
   flutter doctor
   ```
4. En este monorepo, dentro de `app/`:
   ```bash
   cd app
   flutter create . --platforms=web,android,ios --project-name bio_motion_app
   flutter pub get
   ```

## Crear el repositorio remoto y subir código

Desde la raíz del monorepo (donde está `README.md`):

**PowerShell (Windows):** tras `gh auth login`, puedes ejecutar [`scripts/publish-github.ps1`](../scripts/publish-github.ps1).

```bash
git add .
git commit -m "chore: estructura inicial monorepo bio-motion-evaluator"
gh repo create bio-motion-evaluator --public --source=. --remote=origin --push
```

Si el remoto ya existe:

```bash
git remote add origin https://github.com/TU_USUARIO/bio-motion-evaluator.git
git push -u origin main
```

**(Nota)** Si la rama por defecto es `master`, usa `git branch -M main` antes del push.

## MediaPipe (backend)

Tras `pip install -r requirements.txt`, descarga el modelo de pose:

```bash
cd backend
python scripts/download_models.py
```

La ruta del modelo se puede configurar con `MEDIAPIPE_POSE_MODEL_PATH` en `.env` (ver `backend/.env.example`).
