// Renderiza diagramas BPMN 2.0 a SVG y PNG con bpmn-js en Chrome sin interfaz.
//
// Uso:
//   NODE_PATH=<dir>/node_modules node renderizar_bpmn.mjs <chrome> <salida_svg> <salida_png> <a.bpmn> [<b.bpmn> ...]
//
// Dependencias (versiones fijadas, instaladas fuera del repositorio):
//   bpmn-js@18.30.1  puppeteer-core@25.13.0
// Falla (código 1) si bpmn-js informa advertencias o errores de importación.

import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';

const require = createRequire(join(process.env.NODE_PATH ?? '.', 'x.js'));
const puppeteer = require('puppeteer-core');
const bpmnDir = join(require.resolve('bpmn-js/package.json'), '..');

const [chrome, dirSvg, dirPng, ...archivos] = process.argv.slice(2);
if (!chrome || !dirSvg || !dirPng || archivos.length === 0) {
  console.error('uso: renderizar_bpmn.mjs <chrome> <dir_svg> <dir_png> <archivo.bpmn>...');
  process.exit(2);
}

const ANCHO_MIN_PNG = 2400;
const css = ['diagram-js.css', 'bpmn-js.css', 'bpmn-font/css/bpmn-embedded.css']
  .map((f) => readFileSync(join(bpmnDir, 'dist/assets', f), 'utf8'))
  .join('\n');

const navegador = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] });
let fallos = 0;
try {
  for (const archivo of archivos) {
    const nombre = basename(archivo, '.bpmn');
    const xml = readFileSync(archivo, 'utf8');
    const pagina = await navegador.newPage();
    await pagina.setContent(
      `<!doctype html><html><head><meta charset="utf-8"><style>${css}
       html,body{margin:0;background:#fff;font-family:Arial,Helvetica,sans-serif}
       #lienzo{width:4000px;height:3000px}</style></head><body><div id="lienzo"></div></body></html>`,
    );
    await pagina.addScriptTag({ path: join(bpmnDir, 'dist/bpmn-navigated-viewer.production.min.js') });
    const r = await pagina.evaluate(async (xml) => {
      const visor = new window.BpmnJS({ container: '#lienzo' });
      try {
        const { warnings } = await visor.importXML(xml);
        const { svg } = await visor.saveSVG();
        return { ok: true, warnings: warnings.map((w) => w.message), svg };
      } catch (e) {
        return { ok: false, warnings: (e.warnings || []).map((w) => w.message), error: String(e) };
      }
    }, xml);
    if (!r.ok || r.warnings.length) {
      fallos++;
      console.error(`✗ ${nombre}: ${r.error ?? ''}`);
      r.warnings.forEach((w) => console.error(`   advertencia: ${w}`));
      await pagina.close();
      continue;
    }
    // Fondo blanco explícito en el SVG exportado.
    const vb = /viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/.exec(r.svg);
    const [vx, vy, vw, vh] = vb.slice(1).map(Number);
    const fondo = `<rect x="${vx}" y="${vy}" width="${vw}" height="${vh}" fill="#ffffff"/>`;
    const svgFinal = r.svg.replace(/(<svg[^>]*>)/, `$1${fondo}`);
    writeFileSync(join(dirSvg, `${nombre}.svg`), svgFinal, 'utf8');

    const escala = Math.max(2, Math.ceil(ANCHO_MIN_PNG / vw));
    await pagina.setViewport({ width: Math.ceil(vw), height: Math.ceil(vh), deviceScaleFactor: escala });
    await pagina.setContent(
      `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}</style></head>
       <body>${svgFinal.replace(/<\?xml[^>]*\?>/, '').replace(/<svg /, `<svg style="display:block;width:${vw}px;height:${vh}px" `)}</body></html>`,
    );
    await pagina.screenshot({ path: join(dirPng, `${nombre}.png`), clip: { x: 0, y: 0, width: vw, height: vh }, omitBackground: false });
    console.log(`✓ ${nombre}: sin advertencias de importación; SVG ${Math.round(vw)}×${Math.round(vh)}, PNG ×${escala}`);
    await pagina.close();
  }
} finally {
  await navegador.close();
}
process.exit(fallos ? 1 : 0);
