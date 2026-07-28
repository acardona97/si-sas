/**
 * Prueba del cuestionario: carga index.html + app.js en un DOM headless,
 * simula la interacción del usuario y verifica el JSON que se enviaría a
 * /api/generate.
 *
 * Requiere jsdom:  npm install jsdom --no-save
 * Ejecutar:        node test_cuestionario.mjs
 *
 * Deja los payloads en output/_test_cuestionario/ para que test_paquete.py
 * genere el ZIP con el JSON real del cuestionario.
 */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const BASE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'));
const HTML = fs.readFileSync(path.join(BASE, 'src/templates/index.html'), 'utf8');
const JS = fs.readFileSync(path.join(BASE, 'src/static/js/app.js'), 'utf8');

// Los payloads se vuelcan a disco para que test_paquete.py genere el ZIP con
// exactamente el JSON que produce el cuestionario, y no con uno escrito a mano.
const PAYLOAD_DIR = path.join(BASE, 'output', '_test_cuestionario');
fs.mkdirSync(PAYLOAD_DIR, { recursive: true });
const guardarPayload = (nombre, d) =>
    fs.writeFileSync(path.join(PAYLOAD_DIR, nombre), JSON.stringify(d, null, 2), 'utf8');

// La plantilla trae Jinja; se retiran los bloques para que jsdom la parsee.
const htmlLimpio = HTML
    .replace(/\{%[\s\S]*?%\}/g, '')
    .replace(/\{\{[\s\S]*?\}\}/g, '');

function nuevaApp() {
    const dom = new JSDOM(htmlLimpio, { runScripts: 'outside-only', url: 'http://localhost:5000/app' });
    const { window } = dom;
    window.alert = (m) => { window.__alerts.push(m); };
    window.confirm = () => true;
    window.scrollTo = () => {};
    window.__alerts = [];
    window.fetch = async () => ({ ok: true, json: async () => ([]) });
    window.eval(JS);
    window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
    return window;
}

const set = (w, id, v) => { w.document.getElementById(id).value = v; };
const setName = (w, name, v) => { w.document.querySelector(`[name="${name}"]`).value = v; };

function marcarRadio(w, name, value) {
    const el = w.document.querySelector(`input[name="${name}"][value="${value}"]`);
    assert.ok(el, `no existe el radio ${name}=${value}`);
    el.checked = true;
    w.document.querySelectorAll(`input[name="${name}"]`).forEach(r => {
        if (r !== el) r.checked = false;
    });
    el.dispatchEvent(new w.Event('change', { bubbles: true }));
    // Los handlers inline no corren solos en jsdom: se invocan a mano.
    const onchange = el.getAttribute('onchange');
    if (onchange) w.eval(onchange.replace(/\bthis\b/g, `document.querySelector('input[name="${name}"][value="${value}"]')`));
}

function llenarPaso1(w, homonimia = 'min') {
    set(w, 'nombre_sas', 'FAMILIA ANDINA S.A.S.');
    set(w, 'direccion', 'Carrera 43A #1-50, Oficina 805');
    set(w, 'barrio', 'El Poblado');
    set(w, 'email', 'contacto@familiaandina.co');
    set(w, 'telefono1', '3001234567');
    w.onRazonSocialInput();
    w.marcarConsultaRues();
    marcarRadio(w, 'homonimia', homonimia);
}

// La cámara no se deriva del municipio: Envigado se radica en Aburrá Sur.
function llenarAburraSur(w) {
    set(w, 'municipio', 'Envigado');
    set(w, 'camara_ciudad', 'Aburrá Sur');
}

function llenarAccionista(w, n, datos) {
    setName(w, `acc${n}_nombre`, datos.nombre);
    setName(w, `acc${n}_id_num`, datos.id);
    setName(w, `acc${n}_expedicion`, datos.exp || 'Medellín');
    setName(w, `acc${n}_domicilio`, datos.dom || 'Medellín');
    setName(w, `acc${n}_genero`, datos.genero || 'M');
    setName(w, `acc${n}_porcentaje`, String(datos.pct));
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Escenario A: 2 accionistas, junta, revisor PJ, familiar, no declara control');
{
    const w = nuevaApp();
    llenarPaso1(w);
    llenarAburraSur(w);
    assert.ok(w.validateStep(1), 'paso 1 debía validar: ' + w.__alerts);

    // Paso 2 — dos accionistas
    llenarAccionista(w, 1, { nombre: 'Juan Pablo García', id: '71111111', pct: 60, genero: 'M' });
    w.addAccionista();
    llenarAccionista(w, 2, { nombre: 'María Camila Torres', id: '43222222', pct: 40, genero: 'F', exp: 'Envigado', dom: 'Envigado' });
    assert.ok(w.validateStep(2), 'paso 2 debía validar: ' + w.__alerts);

    // Paso 3 — representante legal
    set(w, 'rl_principal_nombre', 'Juan Pablo García');
    set(w, 'rl_principal_cedula', '71111111');
    set(w, 'rl_principal_expedicion', 'Medellín');

    // Paso 4 — CIIU
    set(w, 'ciiu_code', '6201');
    set(w, 'ciiu_description', 'Actividades de desarrollo de sistemas informáticos');
    set(w, 'objeto_social', 'Desarrollo de software a la medida.');

    // Paso 5 — capital autorizado y valor nominal personalizados
    set(w, 'capital_autorizado', '500.000.000');
    set(w, 'valor_nominal', '100');
    set(w, 'capital_suscrito', '2.000.000');
    w.syncCapital();
    const resumen = w.document.getElementById('acciones_resumen').textContent;
    assert.match(resumen, /5\.000\.000 acciones autorizadas/, 'resumen de acciones: ' + resumen);
    assert.match(resumen, /20\.000 acciones suscritas/, 'resumen de acciones: ' + resumen);
    assert.ok(w.validateStep(5), 'paso 5 debía validar: ' + w.__alerts);

    // Paso 6 — junta directiva
    w.showStep(6);
    marcarRadio(w, 'junta', 'si');
    assert.ok(!w.document.getElementById('junta-fields').classList.contains('hidden'),
        'el bloque de junta debía mostrarse');
    set(w, 'junta_num_principales', '3');
    w.renderJuntaPrincipales();
    setName(w, 'jd_pri_1_nombre', 'Juan Pablo García');
    setName(w, 'jd_pri_1_id_num', '71111111');
    setName(w, 'jd_pri_2_nombre', 'María Camila Torres');
    setName(w, 'jd_pri_2_id_num', '43222222');
    setName(w, 'jd_pri_3_nombre', 'Peter Schmidt');
    setName(w, 'jd_pri_3_tipo_doc', 'Pasaporte');
    setName(w, 'jd_pri_3_id_num', 'X8899221');
    w.addJuntaSuplente();
    setName(w, 'jd_sup_1_nombre', 'Laura Gil Peña');
    setName(w, 'jd_sup_1_id_num', '43555444');

    // Paso 6 — revisor fiscal persona jurídica
    marcarRadio(w, 'revisor', 'si');
    assert.ok(!w.document.getElementById('revisor-fields').classList.contains('hidden'));
    marcarRadio(w, 'revisor_tipo', 'juridica');
    assert.ok(!w.document.getElementById('revisor_juridica_fields').classList.contains('hidden'));
    set(w, 'revisor_pj_nombre', 'Auditores Asociados S.A.S.');
    set(w, 'revisor_pj_nit', '900.111.222-3');
    set(w, 'revisor_contador_nombre', 'Carlos Mesa Uribe');
    set(w, 'revisor_contador_id_num', '71999888');
    set(w, 'revisor_contador_tarjeta', '12345-T');

    // Paso 6 — situación de control: debe aparecer (hay controlante al 60%)
    w.refreshControlBlock();
    assert.ok(!w.document.getElementById('control-block').classList.contains('hidden'),
        'la pregunta de situación de control debía mostrarse');
    assert.match(w.document.getElementById('control-context').textContent, /60%/);
    marcarRadio(w, 'declara_control', 'no');

    // Paso 6 — empresa familiar
    marcarRadio(w, 'empresa_familiar', 'si');
    w.renderNucleoFamiliar();
    const filas = w.document.querySelectorAll('#familiar-container [data-fam-row]');
    assert.equal(filas.length, 2, 'debía listar los 2 accionistas');
    filas.forEach((fila, i) => {
        fila.querySelector('[data-fam-check]').checked = true;
        fila.querySelector('[data-fam-parentesco]').value = i === 0 ? 'Padre' : 'Hija';
    });
    w.updateFamiliarBar();
    assert.match(w.document.getElementById('familiar-bar-label').textContent, /100%/);
    assert.ok(w.validateStep(6), 'paso 6 debía validar: ' + w.__alerts);

    // ── Payload final ──
    const d = w.collectAllData();
    assert.equal(d.municipio, 'Envigado');
    assert.equal(d.camara_ciudad, 'Aburrá Sur', 'la cámara no debe derivarse del municipio');
    assert.equal(d.capital_autorizado, '500.000.000');
    assert.equal(d.valor_nominal, '100');
    assert.equal(d.declara_control, false, 'no debía declarar situación de control');
    assert.equal(d.es_empresa_familiar, true);

    assert.equal(d.junta_directiva.principales.length, 3);
    // Los objetos vienen del realm de jsdom: se comparan campo por campo.
    assert.equal(d.junta_directiva.principales[2].nombre, 'Peter Schmidt');
    assert.equal(d.junta_directiva.principales[2].tipo_doc, 'Pasaporte');
    assert.equal(d.junta_directiva.principales[2].id_num, 'X8899221');
    assert.equal(d.junta_directiva.suplentes.length, 1);
    assert.equal(d.junta_directiva.suplentes[0].nombre, 'Laura Gil Peña');

    assert.equal(d.revisor_fiscal.tipo, 'juridica');
    assert.equal(d.revisor_fiscal.id_num, '900.111.222-3');
    assert.equal(d.revisor_fiscal.contador_tarjeta_profesional, '12345-T');

    assert.equal(d.nucleo_familiar.length, 2);
    // 2.000.000 * 60% / 100 = 12.000 acciones
    assert.equal(d.nucleo_familiar[0].acciones, '12.000', 'acciones del núcleo: ' + d.nucleo_familiar[0].acciones);
    assert.equal(d.nucleo_familiar[1].acciones, '8.000');
    assert.equal(d.nucleo_familiar[0].parentesco, 'Padre');

    // Resumen del paso 7
    w.buildSummary();
    const html = w.document.getElementById('summary-content').innerHTML;
    assert.match(html, /Carta de no declaración de situación de control/);
    assert.match(html, /Formato Empresa Familiar/);
    assert.match(html, /Junta Directiva/);
    assert.match(html, /Revisor Fiscal/);
    assert.match(html, /Valor nominal por acción/);
    assert.ok(!/Formato Situación de Control/.test(html), 'no debía ofrecer el formato de control');

    guardarPayload('payload_a.json', d);
    console.log('  OK  payload y resumen del escenario A');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Escenario B: accionista único que sí declara control, por defecto');
{
    const w = nuevaApp();
    llenarPaso1(w);
    set(w, 'nombre_sas', 'SOLO UNO S.A.S.');
    llenarAccionista(w, 1, { nombre: 'Ana Restrepo Gómez', id: '43000111', pct: 100, genero: 'F' });
    assert.ok(w.validateStep(2), 'paso 2 debía validar: ' + w.__alerts);

    set(w, 'rl_principal_nombre', 'Ana Restrepo Gómez');
    set(w, 'rl_principal_cedula', '43000111');
    set(w, 'ciiu_code', '7020');
    assert.ok(w.validateStep(5), 'paso 5 por defecto debía validar: ' + w.__alerts);

    w.showStep(6);
    assert.ok(!w.document.getElementById('control-block').classList.contains('hidden'),
        'con accionista único la pregunta de control debía mostrarse');
    assert.match(w.document.getElementById('control-context').textContent, /único accionista/);
    assert.ok(w.validateStep(6), 'paso 6 debía validar: ' + w.__alerts);

    const d = w.collectAllData();
    assert.equal(d.declara_control, true, 'por defecto debe declarar');
    assert.equal(d.junta_directiva, null);
    assert.equal(d.revisor_fiscal, null);
    assert.equal(d.es_empresa_familiar, false);
    assert.equal(d.nucleo_familiar.length, 0);
    assert.equal(d.capital_autorizado, '1.000.000.000');
    assert.equal(d.valor_nominal, '1');

    w.buildSummary();
    const html = w.document.getElementById('summary-content').innerHTML;
    assert.match(html, /Formato Situación de Control/);
    assert.match(html, /Empresa Familiar \(no aplica\)/);

    guardarPayload('payload_b.json', d);
    console.log('  OK  payload y resumen del escenario B');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Validaciones que deben bloquear el avance');
{
    const w = nuevaApp();
    llenarPaso1(w);
    llenarAccionista(w, 1, { nombre: 'Ana Restrepo', id: '43000111', pct: 100 });

    // Capital autorizado inferior al suscrito
    set(w, 'capital_autorizado', '500.000');
    set(w, 'capital_suscrito', '1.000.000');
    w.__alerts = [];
    assert.equal(w.validateStep(5), false, 'debía rechazar autorizado < suscrito');
    assert.match(w.__alerts[0], /autorizado no puede ser inferior/);

    // Capital no múltiplo del valor nominal
    set(w, 'capital_autorizado', '1.000.000.000');
    set(w, 'valor_nominal', '300');
    w.__alerts = [];
    assert.equal(w.validateStep(5), false, 'debía rechazar capital no múltiplo del nominal');
    assert.match(w.__alerts[0], /múltiplos exactos/);
    set(w, 'valor_nominal', '1');

    // Junta con miembros incompletos
    w.showStep(6);
    marcarRadio(w, 'junta', 'si');
    set(w, 'junta_num_principales', '3');
    w.renderJuntaPrincipales();
    setName(w, 'jd_pri_1_nombre', 'Solo Uno');
    setName(w, 'jd_pri_1_id_num', '111');
    w.__alerts = [];
    assert.equal(w.validateStep(6), false, 'debía exigir los 3 miembros');
    assert.match(w.__alerts[0], /3 miembros principales/);
    marcarRadio(w, 'junta', 'no');

    // Revisor fiscal PJ sin contador designado
    marcarRadio(w, 'revisor', 'si');
    marcarRadio(w, 'revisor_tipo', 'juridica');
    set(w, 'revisor_pj_nombre', 'Auditores S.A.S.');
    set(w, 'revisor_pj_nit', '900.111.222-3');
    w.__alerts = [];
    assert.equal(w.validateStep(6), false, 'debía exigir el contador designado');
    assert.match(w.__alerts[0], /revisor fiscal/i);
    marcarRadio(w, 'revisor', 'no');

    // Núcleo familiar que no supera la mitad del capital
    w.addAccionista();
    llenarAccionista(w, 2, { nombre: 'Otro Socio', id: '999', pct: 70 });
    setName(w, 'acc1_porcentaje', '30');
    marcarRadio(w, 'empresa_familiar', 'si');
    w.renderNucleoFamiliar();
    const fila0 = w.document.querySelector('#familiar-container [data-fam-row="0"]');
    fila0.querySelector('[data-fam-check]').checked = true;
    fila0.querySelector('[data-fam-parentesco]').value = 'Padre';
    w.__alerts = [];
    assert.equal(w.validateStep(6), false, 'debía exigir más de la mitad del capital');
    assert.match(w.__alerts[0], /más de la mitad del capital/);

    // Marcado sin parentesco
    const fila1 = w.document.querySelector('#familiar-container [data-fam-row="1"]');
    fila1.querySelector('[data-fam-check]').checked = true;
    w.__alerts = [];
    assert.equal(w.validateStep(6), false, 'debía exigir el parentesco');
    assert.match(w.__alerts[0], /parentesco/);

    console.log('  OK  todas las validaciones bloquean correctamente');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Homonimia: nombre distintivo, enlace al RUES y niveles de riesgo');
{
    const w = nuevaApp();

    // El nombre distintivo ignora tipo societario, tildes y puntuación.
    assert.equal(w.nombreDistintivo('DONATELO S.A.S.'), 'DONATELO');
    assert.equal(w.nombreDistintivo('Donatelo s.a.s.'), 'DONATELO');
    assert.equal(w.nombreDistintivo('Café Montaña S.A.S. B.I.C.'), 'CAFE MONTANA');
    assert.equal(w.nombreDistintivo('ACME LTDA'), 'ACME');
    assert.equal(w.nombreDistintivo('ACME Sociedad Anónima'), 'ACME');
    assert.equal(w.nombreDistintivo('Inversiones J&M S. en C.'), 'INVERSIONES J M');
    assert.equal(w.nombreDistintivo('AGUAS DEL SUR S.A.S. E.S.P.'), 'AGUAS DEL SUR');
    // No debe comerse palabras que solo parecen sufijo en medio del nombre
    assert.equal(w.nombreDistintivo('CASA SAS'), 'CASA');
    assert.equal(w.nombreDistintivo('SA MARIA S.A.S.'), 'SA MARIA');
    console.log('  OK  normalización del nombre distintivo');

    // El enlace apunta al RUES con la búsqueda ya cargada
    set(w, 'nombre_sas', 'Café Montaña S.A.S.');
    w.onRazonSocialInput();
    const href = w.document.getElementById('homonimia-link').href;
    assert.equal(href, 'https://www.rues.org.co/buscar/RM/CAFE%20MONTANA', 'href: ' + href);
    assert.match(w.document.getElementById('homonimia-termino').textContent, /CAFE MONTANA/);
    console.log('  OK  enlace profundo al RUES');

    // Sin declarar, el paso 1 no deja avanzar
    llenarPaso1(w);
    set(w, 'nombre_sas', 'FAMILIA ANDINA S.A.S.');
    w.onRazonSocialInput();
    w.resetHomonimia();
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'debía exigir la declaración');
    assert.match(w.__alerts[0], /declare qué encontró/);

    // Riesgo mínimo deja pasar
    w.marcarConsultaRues();
    marcarRadio(w, 'homonimia', 'min');
    w.__alerts = [];
    assert.ok(w.validateStep(1), 'riesgo mínimo debía pasar: ' + w.__alerts);
    assert.match(w.document.getElementById('homonimia-resultado').textContent, /Riesgo de homonimia mínimo/);

    // Riesgo medio también deja pasar (solo advierte)
    marcarRadio(w, 'homonimia', 'similar');
    assert.ok(w.validateStep(1), 'riesgo medio debía pasar');
    marcarRadio(w, 'homonimia', 'identica_cancelada');
    assert.ok(w.validateStep(1), 'idéntica cancelada debía pasar (riesgo medio)');
    assert.match(w.document.getElementById('homonimia-resultado').textContent, /medio/);

    // Riesgo máximo exige reconocer el riesgo, pero no bloquea
    marcarRadio(w, 'homonimia', 'identica_activa');
    assert.ok(!w.document.getElementById('homonimia-ack-wrap').classList.contains('hidden'),
        'debía pedir el reconocimiento expreso');
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'sin reconocer el riesgo no debía pasar');
    assert.match(w.__alerts[0], /riesgo de devolución por homonimia/);
    w.document.getElementById('homonimia_ack').checked = true;
    w.onHomonimiaChange();
    assert.ok(w.validateStep(1), 'con el riesgo aceptado debía pasar (solo advertencia)');
    assert.equal(w.getHomonimiaData().nivel_riesgo, 'máximo');
    assert.equal(w.getHomonimiaData().riesgo_aceptado, true);
    console.log('  OK  niveles de riesgo: mínimo y medio pasan, máximo advierte sin bloquear');

    // Cambiar la razón social invalida la declaración anterior
    set(w, 'nombre_sas', 'OTRA COSA S.A.S.');
    w.onRazonSocialInput();
    assert.equal(w.getHomonimiaData(), null,
        'al cambiar el nombre, la declaración anterior debe reiniciarse');
    assert.ok(w.document.getElementById('homonimia-declaracion').classList.contains('hidden'));
    console.log('  OK  la declaración se reinicia al cambiar la razón social');

    // Cambio que no altera el nombre distintivo NO reinicia
    w.marcarConsultaRues();
    marcarRadio(w, 'homonimia', 'min');
    set(w, 'nombre_sas', 'Otra Cosa Ltda');   // mismo distintivo: OTRA COSA
    w.onRazonSocialInput();
    assert.ok(w.getHomonimiaData(), 'mismo nombre distintivo: no debía reiniciarse');
    console.log('  OK  no se reinicia si el nombre distintivo no cambió');
}

console.log('\nCuestionario verificado.\n');
