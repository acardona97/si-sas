/**
 * Vista previa visual del cuestionario.
 *
 * No es una prueba: monta index.html con el app.js real, avanza hasta el paso
 * pedido y escribe una página estática para revisarla en el navegador con el
 * CSS de producción. Sirve para mirar el diseño sin abrir sesión.
 *
 * Uso:  node preview_paso.mjs [paso]   →  src/static/_preview/paso<n>.html
 *       node preview_paso.mjs 5        (por defecto, el de responsabilidades)
 */
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const BASE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'));
const HTML = fs.readFileSync(path.join(BASE, 'src/templates/index.html'), 'utf8');
const JS = fs.readFileSync(path.join(BASE, 'src/static/js/app.js'), 'utf8');
const CSS = fs.readFileSync(path.join(BASE, 'src/static/css/style.css'), 'utf8');
const DATA = JSON.parse(fs.readFileSync(path.join(BASE, 'output/_preview/resp.json'), 'utf8'));

const htmlLimpio = HTML.replace(/\{%[\s\S]*?%\}/g, '').replace(/\{\{[\s\S]*?\}\}/g, '');
const dom = new JSDOM(htmlLimpio, { runScripts: 'outside-only', url: 'http://localhost:5000/app' });
const w = dom.window;
w.alert = () => {};
w.scrollTo = () => {};
w.fetch = async () => ({ ok: true, json: async () => DATA });
w.eval(JS);
w.document.dispatchEvent(new w.Event('DOMContentLoaded'));

const PASO = Number(process.argv[2]) || 5;
w.showStep(PASO);
await new Promise(r => setTimeout(r, 60));

// Estado que vale la pena ver en el paso 5: una sugerida marcada y el bloque
// de comercio exterior abierto con una calidad ya declarada.
if (PASO === 5) {
w.toggleRespAdicional('16', true);
w.toggleRespAdicional('10', true);
w.togglePerfilCE('importador', true);
w.document.querySelectorAll('#resp-adicionales input[value="16"], #resp-adicionales input[value="10"]')
    .forEach(i => i.setAttribute('checked', 'checked'));
w.document.querySelectorAll('#resp-comercio-exterior input[value="importador"]')
    .forEach(i => i.setAttribute('checked', 'checked'));
}

// Se conserva el armazón entero —barra lateral, cabecera, paginador— para
// poder juzgar la composición y no solo el formulario.
const salida = path.join(BASE, `src/static/_preview/paso${PASO}.html`);
fs.mkdirSync(path.dirname(salida), { recursive: true });
fs.writeFileSync(salida,
    `<!doctype html><meta charset="utf-8"><title>Paso ${PASO}</title>
<link rel="stylesheet" href="/static/css/style.css">
${w.document.body.innerHTML}`,
    'utf8');

console.log('vista previa ->', salida);
