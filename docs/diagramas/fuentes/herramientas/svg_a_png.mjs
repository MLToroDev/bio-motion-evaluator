// Convierte un SVG a PNG con Chrome sin interfaz (fondo blanco, escala ×2 o mayor).
//
// Uso:
//   NODE_PATH=<dir>/node_modules node svg_a_png.mjs <chrome> <entrada.svg> <salida.png> [ancho_min=2400]

import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const require = createRequire(join(process.env.NODE_PATH ?? '.', 'x.js'));
const puppeteer = require('puppeteer-core');

const [chrome, entrada, salida, anchoMin = '2400'] = process.argv.slice(2);
const svg = readFileSync(entrada, 'utf8').replace(/<\?xml[^>]*\?>/, '');
const m = /viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/.exec(svg) ?? /width="([\d.]+)(?:pt|px)?" height="([\d.]+)(?:pt|px)?"/.exec(svg);
const [w, h] = m.length === 5 ? [Number(m[3]), Number(m[4])] : [Number(m[1]), Number(m[2])];
const escala = Math.max(2, Math.ceil(Number(anchoMin) / w));

const navegador = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] });
try {
  const pagina = await navegador.newPage();
  await pagina.setViewport({ width: Math.ceil(w), height: Math.ceil(h), deviceScaleFactor: escala });
  await pagina.setContent(
    `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}
     svg{display:block;width:${w}px;height:${h}px}</style></head><body>${svg}</body></html>`,
  );
  await pagina.screenshot({ path: salida, clip: { x: 0, y: 0, width: w, height: h } });
  console.log(`✓ ${salida} (${Math.round(w)}×${Math.round(h)} ×${escala})`);
} finally {
  await navegador.close();
}
