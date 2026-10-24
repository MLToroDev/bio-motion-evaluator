#!/usr/bin/env bash
# Regenera todos los diagramas de docs/diagramas (fuentes -> svg/ y png/):
# clases, arquitectura, despliegue, entidad-relación, BPMN (AS-IS y TO-BE) e Ishikawa.
#
# Requisitos: python3, Graphviz (dot) y Node.js. Las dependencias de Node se instalan
# FUERA del repositorio, en $DIAGRAMAS_NODE_DIR (por defecto un directorio temporal),
# con versiones fijadas:
#   bpmn-js@18.30.1  puppeteer-core@25.13.0  bpmnlint@11.14.0
#
# Variables:
#   CHROME               ejecutable de Chrome/Chromium (obligatorio para BPMN)
#   DIAGRAMAS_NODE_DIR   directorio con node_modules (se crea si no existe)
#   PYREVERSE            ruta a pyreverse (opcional: regenera fuentes/generado/)
#
# Uso:  CHROME=/ruta/a/chrome docs/diagramas/fuentes/herramientas/renderizar.sh
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAG="$(cd "$AQUI/../.." && pwd)"
REPO="$(cd "$DIAG/../.." && pwd)"
NODE_DIR="${DIAGRAMAS_NODE_DIR:-${TMPDIR:-/tmp}/bio-motion-diagramas-node}"
mkdir -p "$DIAG/svg" "$DIAG/png"

echo "1/5 Estructura bruta con pyreverse"
if [[ -n "${PYREVERSE:-}" ]]; then
  (cd "$REPO/backend" && PYTHONPATH=. "$PYREVERSE" -o dot -p backend_app -d "$DIAG/fuentes/generado" -A -S --colorized app \
    && PYTHONPATH=. "$PYREVERSE" -o dot -p backend_vision -d "$DIAG/fuentes/generado" -A -S --colorized vision)
else
  echo "   (omitido: defina PYREVERSE para regenerar fuentes/generado/*.dot)"
fi
for f in "$DIAG"/fuentes/generado/*.dot; do
  dot -Tsvg "$f" -o "${f%.dot}.svg"
done

echo "2/5 Diagramas Graphviz (clases, arquitectura, despliegue, entidad-relación)"
python3 "$DIAG/fuentes/clases/generar_clases.py"
for f in "$DIAG"/fuentes/clases/*.dot "$DIAG"/fuentes/arquitectura/*.dot "$DIAG"/fuentes/er/*.dot; do
  n="$(basename "$f" .dot)"
  dot -Tsvg "$f" -o "$DIAG/svg/$n.svg"
  dot -Tpng -Gdpi=150 "$f" -o "$DIAG/png/$n.png"
done

echo "3/5 Procesos BPMN (XML)"
python3 "$DIAG/fuentes/bpmn/generar_bpmn.py"

echo "4/5 Dependencias de Node en $NODE_DIR"
if [[ ! -d "$NODE_DIR/node_modules/bpmn-js" ]]; then
  mkdir -p "$NODE_DIR"
  (cd "$NODE_DIR" && npm init -y >/dev/null && \
    npm install --save-exact bpmn-js@18.30.1 puppeteer-core@25.13.0 bpmnlint@11.14.0)
fi
echo '{"extends":"bpmnlint:recommended"}' > "$NODE_DIR/.bpmnlintrc"
(cd "$NODE_DIR" && npx bpmnlint "$DIAG"/fuentes/bpmn/*.bpmn) && echo "   bpmnlint: sin problemas"

echo "5/5 Renderizado BPMN con bpmn-js (Chrome sin interfaz)"
: "${CHROME:?Defina CHROME con la ruta al ejecutable de Chrome o Chromium}"
NODE_PATH="$NODE_DIR/node_modules" node "$AQUI/renderizar_bpmn.mjs" "$CHROME" "$DIAG/svg" "$DIAG/png" "$DIAG"/fuentes/bpmn/*.bpmn

echo "   Diagrama causa-efecto (SVG generado por Python, PNG con Chrome)"
python3 "$DIAG/fuentes/ishikawa/generar_ishikawa.py" "$DIAG/svg/ishikawa_problema.svg"
NODE_PATH="$NODE_DIR/node_modules" node "$AQUI/svg_a_png.mjs" "$CHROME" "$DIAG/svg/ishikawa_problema.svg" "$DIAG/png/ishikawa_problema.png"
echo "Listo: $DIAG/svg y $DIAG/png"
