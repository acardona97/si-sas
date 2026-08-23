/**
 * Vista previa visual del paso de responsabilidades tributarias.
 *
 * No es una prueba: renderiza el paso 5 con el app.js real y los datos reales
 * de /api/responsabilidades (volcados a output/_preview/resp.json) y escribe
 * una página estática para revisarla en el navegador con el CSS de producción.
 *
 * Uso:  node preview_resp.mjs   →  src/static/_preview/responsabilidades.html
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

w.showStep(5);
await new Promise(r => setTimeout(r, 60));

// Estado que vale la pena ver: una sugerida marcada y el bloque de comercio
// exterior abierto con una calidad ya declarada.
w.toggleRespAdicional('16', true);
w.toggleRespAdicional('10', true);
w.togglePerfilCE('importador', true);
w.document.querySelectorAll('#resp-adicionales input[value="16"], #resp-adicionales input[value="10"]')
    .forEach(i => i.setAttribute('checked', 'checked'));
w.document.querySelectorAll('#resp-comercio-exterior input[value="importador"]')
    .forEach(i => i.setAttribute('checked', 'checked'));

const paso = w.document.getElementById('step5');
fs.writeFileSync(
    path.join(BASE, 'src/static/_preview/responsabilidades.html'),
    `<!doctype html><meta charset="utf-8"><title>Responsabilidades tributarias</title>
<style>${CSS}</style>
<div class="container"><div class="form-container">${paso.innerHTML}</div></div>`,
    'utf8');

console.log('vista previa ->', path.join(BASE, 'src/static/_preview/responsabilidades.html'));
