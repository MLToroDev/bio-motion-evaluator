// Copia los manuales en PDF desde docs/manuales/ (fuente única) a public/manuales/
// para que el cliente los sirva como descarga. Se ejecuta antes de `dev` y `build`.
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const raizAppWeb = join(dirname(fileURLToPath(import.meta.url)), '..');
const origen = join(raizAppWeb, '..', 'docs', 'manuales');
const destino = join(raizAppWeb, 'public', 'manuales');
const manuales = ['manual_usuario.pdf', 'manual_instalacion.pdf'];

mkdirSync(destino, { recursive: true });
for (const nombre of manuales) {
  const ruta = join(origen, nombre);
  if (!existsSync(ruta)) {
    console.warn(`[manuales] No se encontró ${ruta}; la descarga de ${nombre} no estará disponible.`);
    continue;
  }
  copyFileSync(ruta, join(destino, nombre));
  console.log(`[manuales] ${nombre} copiado a public/manuales/`);
}
