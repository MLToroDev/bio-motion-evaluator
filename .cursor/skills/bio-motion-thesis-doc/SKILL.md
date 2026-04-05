---
name: bio-motion-thesis-doc
description: Mantiene alineados el borrador de tesis (`docs/Formato_trabajo_de_grado.md`), la bitácora de decisiones, `docs/spec/` y `docs/arquitectura.md` tras cambios importantes en Bio-Motion Evaluator. Usar cuando el usuario pida documentar, cerrar un sprint, registrar una decisión, o al finalizar una feature que afecte contratos o arquitectura.
---

# Documentación de tesis y trazabilidad (Bio-Motion)

## Objetivo

Dejar constancia en el repo de lo que la memoria debe reflejar (Capítulo 6 y decisiones), sin duplicar ensayos largos: priorizar **hechos**, **decisiones** y **rutas de código**.

## Checklist tras implementación relevante

1. **Inventario:** listar archivos tocados y si el cambio afecta REST, WebSocket, modelos Pydantic, contrato TS en **`appWeb/`** (frontend operativo), o flujo de usuario. No usar **`app/`** (Flutter) como superficie de cambio salvo que el usuario lo pida.
2. **Spec:** si aplica, editar o crear el archivo en `docs/spec/` (ver `docs/spec/README.md`).
3. **Arquitectura:** si cambia el mapa mental del sistema, actualizar `docs/arquitectura.md`.
4. **Bitácora:** en `docs/Formato_trabajo_de_grado.md`, sección **BITÁCORA DE DESARROLLO Y DECISIONES**, añadir una entrada **nueva encima** de las existentes con fecha (AAAA-MM-DD), ámbito, tipo, descripción breve y trazabilidad (paths, spec).
5. **Capítulo 6 narrativo:** solo si el usuario lo pide explícitamente, ampliar subsecciones 6.x (p. ej. diseño, despliegue) además de la bitácora.

## Texto de bitácora (plantilla mental)

- Una decisión = una entrada; si hay varios archivos, agrupar bajo un solo hilo si comparten la misma motivación.
- **Trazabilidad:** incluir al menos un path real (`backend/...`, `appWeb/...`, `docs/spec/...`).
- Mantener **español** académico claro; evitar jerga sin definir.

## Errores a evitar

- No mover ni renombrar `Formato_trabajo_de_grado.md` sin acuerdo (es la fuente que el usuario exporta o compila).
- No sustituir la bitácora por comentarios solo en código: el documento de grado es el archivo designado por el usuario.
