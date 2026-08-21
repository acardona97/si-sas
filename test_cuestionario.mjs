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

    // ── Sin abrir el RUES no se puede avanzar, aunque se marque un resultado ──
    llenarPaso1(w);
    set(w, 'nombre_sas', 'FAMILIA ANDINA S.A.S.');
    w.onRazonSocialInput();
    w.resetHomonimia();
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'sin consultar el RUES no debía pasar');
    assert.match(w.__alerts[0], /debe consultar la razón social en el RUES/);

    // El bloque de declaración ni siquiera está visible antes de consultar
    assert.ok(w.document.getElementById('homonimia-declaracion').classList.contains('hidden'));
    console.log('  OK  no deja avanzar si no se abrió la consulta en el RUES');

    // ── Tras consultar, falta declarar ──
    w.marcarConsultaRues();
    assert.ok(w.document.getElementById('homonimia-link').classList.contains('consultado'),
        'el botón debía quedar marcado como consultado');
    assert.ok(w.document.getElementById('homo-paso-1').classList.contains('done'));
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'consultó pero no declaró');
    assert.match(w.__alerts[0], /marque cuál de los cuatro resultados/);

    // ── Las cuatro opciones y su semáforo ──
    const opciones = [...w.document.querySelectorAll('.rues-opcion')];
    assert.equal(opciones.length, 4, 'deben seguir siendo cuatro opciones');
    assert.deepEqual(opciones.map(o => o.dataset.nivel),
        ['ok', 'aviso', 'aviso', 'alto'], 'semáforo de severidad');
    assert.deepEqual(opciones.map(o => o.querySelector('input').value),
        ['min', 'similar', 'identica_cancelada', 'identica_activa'],
        'los valores del cuestionario no pueden cambiar');
    // Cada opción muestra la réplica de la pantalla del RUES
    assert.equal(w.document.querySelectorAll('.rues-mock').length, 4);
    assert.match(opciones[0].textContent, /No se encontraron resultados/);
    assert.match(opciones[3].textContent, /Cerca de 1 resultados Exacto/);
    // El instructivo habla de razón social, no de "nombre"
    const bloque = w.document.getElementById('homonimia-declaracion').textContent;
    assert.ok(!/\bnombre\b/i.test(bloque),
        'el instructivo debe decir "razón social": ' +
        (bloque.match(/.{0,40}\bnombre\b.{0,40}/i) || [''])[0]);
    console.log('  OK  cuatro opciones con semáforo, réplica del RUES y lenguaje de razón social');

    // ── Veredictos ──
    marcarRadio(w, 'homonimia', 'min');
    // El resaltado de la opción elegida lo maneja onHomonimiaChange, no el
    // listener genérico de .radio-cards
    assert.ok(opciones[0].classList.contains('elegida'), 'la opción elegida debía resaltarse');
    assert.ok(!opciones[3].classList.contains('elegida'));
    const veredicto = w.document.getElementById('homonimia-resultado');
    assert.ok(veredicto.classList.contains('ok'), 'clase del veredicto: ' + veredicto.className);
    assert.match(veredicto.textContent, /RAZÓN SOCIAL DISPONIBLE/);
    assert.ok(w.validateStep(1), 'riesgo mínimo debía pasar: ' + w.__alerts);
    assert.equal(w.getHomonimiaData().consulta_realizada, true);

    marcarRadio(w, 'homonimia', 'similar');
    assert.ok(veredicto.classList.contains('aviso'));
    assert.match(veredicto.textContent, /ATENCIÓN/);
    assert.ok(w.validateStep(1), 'riesgo medio debía pasar');

    marcarRadio(w, 'homonimia', 'identica_cancelada');
    assert.ok(veredicto.classList.contains('aviso'));
    assert.match(veredicto.textContent, /Cancelada o Liquidada/);
    assert.ok(w.validateStep(1), 'idéntica cancelada debía pasar (riesgo medio)');

    marcarRadio(w, 'homonimia', 'identica_activa');
    assert.ok(veredicto.classList.contains('alto'), 'clase: ' + veredicto.className);
    assert.match(veredicto.textContent, /RAZÓN SOCIAL NO DISPONIBLE/);
    assert.match(veredicto.textContent, /devolver el trámite por homonimia/);
    assert.ok(!w.document.getElementById('homonimia-ack-wrap').classList.contains('hidden'),
        'debía pedir el reconocimiento expreso');
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'sin reconocer el riesgo no debía pasar');
    assert.match(w.__alerts[0], /razón social NO está disponible/);
    w.document.getElementById('homonimia_ack').checked = true;
    w.onHomonimiaChange();
    assert.ok(w.validateStep(1), 'con el riesgo aceptado debía pasar (solo advertencia)');
    assert.equal(w.getHomonimiaData().nivel_riesgo, 'máximo');
    assert.equal(w.getHomonimiaData().riesgo_aceptado, true);
    console.log('  OK  veredictos: disponible / atención / no disponible');

    // ── Cambiar la razón social obliga a consultar de nuevo ──
    set(w, 'nombre_sas', 'OTRA COSA S.A.S.');
    w.onRazonSocialInput();
    assert.equal(w.getHomonimiaData(), null,
        'al cambiar el nombre debe caducar la declaración');
    assert.ok(w.document.getElementById('homonimia-declaracion').classList.contains('hidden'));
    assert.ok(!w.document.getElementById('homonimia-link').classList.contains('consultado'),
        'el botón debía volver a su estado sin consultar');
    assert.ok(![...w.document.querySelectorAll('.rues-opcion')].some(o => o.classList.contains('elegida')),
        'al reiniciar no debe quedar ninguna opción resaltada');
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'con nombre nuevo hay que consultar otra vez');
    assert.match(w.__alerts[0], /debe consultar la razón social en el RUES/);
    console.log('  OK  cambiar la razón social obliga a consultar de nuevo');

    // Cambio que no altera el nombre distintivo NO obliga a repetir
    w.marcarConsultaRues();
    marcarRadio(w, 'homonimia', 'min');
    set(w, 'nombre_sas', 'otra cosa sas');   // mismo distintivo: OTRA COSA
    w.onRazonSocialInput();
    assert.ok(w.getHomonimiaData(), 'mismo nombre distintivo: no debía caducar');
    assert.ok(w.validateStep(1), 'mismo distintivo: debía seguir pasando');
    console.log('  OK  no caduca si el nombre distintivo no cambió');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Razón social: el indicativo S.A.S. es obligatorio');
{
    const w = nuevaApp();

    // Formas válidas del indicativo
    for (const valida of ['ACME S.A.S.', 'ACME SAS', 'Acme s.a.s', 'ACME S A S',
                          'ACME Sociedad por Acciones Simplificada',
                          'ACME S.A.S. B.I.C.', 'AGUAS DEL SUR S.A.S. E.S.P.']) {
        assert.ok(w.tieneIndicativoSAS(valida), `debía aceptar: ${valida}`);
    }
    // Formas que no llevan el indicativo, o lo llevan donde no va
    for (const invalida of ['ACME', 'ACME LTDA', 'ACME S.A.', 'Inversiones Acme',
                            'SAS ACME', 'ACME LIMITADA']) {
        assert.ok(!w.tieneIndicativoSAS(invalida), `no debía aceptar: ${invalida}`);
    }
    console.log('  OK  reconocimiento del indicativo en todas sus formas');

    // Sin indicativo, el paso 1 no deja avanzar
    llenarPaso1(w);
    set(w, 'nombre_sas', 'FAMILIA ANDINA');
    w.onRazonSocialInput();
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'sin S.A.S. no debía dejar continuar');
    assert.match(w.__alerts[0], /debe terminar en "S\.A\.S\."/);
    assert.match(w.__alerts[0], /Ley 1258 de 2008/);
    // Y sugiere exactamente qué escribir
    assert.match(w.__alerts[0], /FAMILIA ANDINA S\.A\.S\./);

    // Solo el indicativo tampoco sirve: falta el nombre distintivo
    set(w, 'nombre_sas', 'S.A.S.');
    w.onRazonSocialInput();
    w.__alerts = [];
    assert.equal(w.validateStep(1), false, 'solo el indicativo no debía pasar');
    assert.match(w.__alerts[0], /no puede ser solo el indicativo/);
    // Lo mismo con otro tipo societario suelto
    set(w, 'nombre_sas', 'LTDA');
    w.__alerts = [];
    assert.equal(w.validateStep(1), false);
    assert.match(w.__alerts[0], /no puede ser solo el indicativo/);

    // Con el indicativo sí avanza
    set(w, 'nombre_sas', 'FAMILIA ANDINA S.A.S.');
    w.onRazonSocialInput();
    w.marcarConsultaRues();
    marcarRadio(w, 'homonimia', 'min');
    w.__alerts = [];
    assert.ok(w.validateStep(1), 'con S.A.S. debía pasar: ' + w.__alerts);
    console.log('  OK  bloquea sin indicativo y deja pasar con él');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Junta directiva: selector de accionistas en cada miembro');
{
    const w = nuevaApp();
    llenarPaso1(w);
    llenarAccionista(w, 1, { nombre: 'Juan Pablo García', id: '71111111', pct: 60 });
    w.addAccionista();
    llenarAccionista(w, 2, { nombre: 'María Camila Torres', id: '43222222', pct: 40 });

    w.showStep(6);
    marcarRadio(w, 'junta', 'si');
    set(w, 'junta_num_principales', '3');
    w.renderJuntaPrincipales();

    // Cada tarjeta trae su selector poblado con los accionistas
    const selects = w.document.querySelectorAll('[data-junta-select]');
    assert.equal(selects.length, 3, 'debía haber un selector por miembro');
    const opciones = [...selects[0].options].map(o => o.textContent);
    assert.deepEqual(opciones,
        ['-- Escribir manualmente --', 'Juan Pablo García', 'María Camila Torres'], opciones);

    // Y cada tarjeta trae su carga de documento
    assert.equal(w.document.querySelectorAll('#junta-principales-container input[type="file"]').length, 3);
    assert.ok(w.document.getElementById('jd_pri_1_upload_status'), 'falta el estado de carga');

    // Escoger un accionista autocompleta el miembro
    selects[0].value = '1';
    w.selectJuntaAccionista(selects[0], 'jd_pri_1');
    assert.equal(w.document.querySelector('[name="jd_pri_1_nombre"]').value, 'María Camila Torres');
    assert.equal(w.document.querySelector('[name="jd_pri_1_id_num"]').value, '43222222');

    // Los suplentes también
    w.addJuntaSuplente();
    const selSup = w.document.querySelector('#junta-suplentes-container [data-junta-select]');
    assert.ok(selSup, 'el suplente debía traer selector');
    assert.equal([...selSup.options].length, 3);
    assert.ok(w.document.querySelector('#junta-suplentes-container input[type="file"]'),
        'el suplente debía traer carga de documento');
    console.log('  OK  selector y carga de cédula en principales y suplentes');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Revisor fiscal: cargas de cédula y tarjeta profesional');
{
    const w = nuevaApp();
    w.showStep(6);
    marcarRadio(w, 'revisor', 'si');

    // Persona natural: cédula + tarjeta profesional
    for (const id of ['revisor_upload_status', 'revisor_tarjeta_upload_status']) {
        assert.ok(w.document.getElementById(id), `falta ${id}`);
    }
    // Persona jurídica: cédula y tarjeta del contador designado
    marcarRadio(w, 'revisor_tipo', 'juridica');
    for (const id of ['revisor_contador_upload_status', 'revisor_contador_tarjeta_upload_status']) {
        assert.ok(w.document.getElementById(id), `falta ${id}`);
    }
    // Las cargas apuntan a los endpoints correctos
    const cargas = [...w.document.querySelectorAll('#revisor-fields input[type="file"]')]
        .map(i => i.getAttribute('onchange'));
    assert.equal(cargas.filter(c => c.includes('extractFromCedula')).length, 2, cargas.join(' | '));
    assert.equal(cargas.filter(c => c.includes('extractFromTarjeta')).length, 2, cargas.join(' | '));
    console.log('  OK  cuatro cargas: cédula y tarjeta, para natural y para el contador designado');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── CIIU: marcas en la lista y panel de restricciones');
{
    const w = nuevaApp();

    // La lista desplegable marca los códigos restringidos sin ocultarlos
    const resultados = w.document.getElementById('ciiu_results');
    w.fetch = async () => ({
        ok: true,
        json: async () => ([
            { code: '6201', description: 'Desarrollo de sistemas informáticos' },
            { code: '9499', description: 'Actividades de otras asociaciones n.c.p.',
              restriccion: { decision: 'BLOCK_NOT_COMMERCIAL_ENTITY', nivel: 'bloqueado',
                             etiqueta: 'No corresponde a una sociedad' } },
            { code: '8020', description: 'Servicios de sistemas de seguridad',
              restriccion: { decision: 'CONDITIONAL_REVIEW', nivel: 'preguntas',
                             etiqueta: 'Requiere responder preguntas' } },
        ]),
    });
    w.searchCIIU('seg', 'principal');
    await new Promise(r => setTimeout(r, 400));

    const items = [...resultados.querySelectorAll('.result-item')];
    assert.equal(items.length, 3, 'los códigos restringidos no se ocultan de la lista');
    assert.equal(items[0].querySelectorAll('.ciiu-marca').length, 0, '6201 no lleva marca');
    const marcaBloq = items[1].querySelector('.ciiu-marca');
    assert.ok(marcaBloq, '9499 debía llevar marca');
    assert.ok(marcaBloq.classList.contains('bloqueado'), marcaBloq.className);
    assert.match(marcaBloq.textContent, /No corresponde a una sociedad/);
    assert.ok(items[2].querySelector('.ciiu-marca').classList.contains('preguntas'));
    console.log('  OK  la lista marca los restringidos y no los oculta');

    // Se recorre el flujo real: elegir el código dispara la evaluación contra
    // el backend, que aquí se simula devolviendo lo que devolvería de verdad.
    const panel = w.document.getElementById('ciiu_panel');
    let evaluacionActual = null;
    let ultimaConsulta = null;
    w.fetch = async (url, opts) => {
        ultimaConsulta = url;
        if (String(url).includes('/api/ciiu/autorizacion')) {
            return { ok: true, json: async () => ({ documento_id: 'abc', nombre: 'resolucion.pdf' }) };
        }
        return { ok: true, json: async () => evaluacionActual };
    };
    const elegir = async (code, evaluacion) => {
        evaluacionActual = evaluacion;
        w.selectCIIUVariant(code, 'descripción', 'principal');
        await new Promise(r => setTimeout(r, 30));
    };

    // ── Código bloqueado ──
    await elegir('9499', {
        decision: 'BLOCK_NOT_COMMERCIAL_ENTITY', bloquea: true, preguntas: [],
        titulo: 'Actividad propia de una entidad sin ánimo de lucro',
        mensaje: 'El código describe la naturaleza institucional de una asociación.',
        tipo_entidad_requerido: 'Entidad sin ánimo de lucro',
        fundamento: ['Decreto 2150 de 1995'],
    });
    assert.ok(panel.classList.contains('bloqueado'), panel.className);
    assert.match(panel.textContent, /Entidad sin ánimo de lucro/);
    assert.match(panel.textContent, /Decreto 2150 de 1995/);
    w.__alerts = [];
    assert.equal(w.validateStep(4), false, 'un código bloqueado no debe dejar avanzar');
    assert.match(w.__alerts[0], /no puede usarse en una S\.A\.S\./);
    console.log('  OK  código bloqueado: panel rojo y no deja continuar');

    // ── Preguntas pendientes ──
    await elegir('8020', {
        decision: 'CONDITIONAL_REVIEW', bloquea: false, pendiente: true,
        titulo: 'Sistemas de seguridad', mensaje: 'Depende del servicio concreto',
        preguntas: [
            { id: 'central_monitoreo', texto: '¿Operará una central de monitoreo?' },
            { id: 'patrullaje', texto: '¿Hará patrullaje?' },
        ],
        fundamento: [],
    });
    assert.ok(panel.classList.contains('preguntas'), panel.className);
    assert.equal(panel.querySelectorAll('.ciiu-pregunta').length, 2);
    w.__alerts = [];
    assert.equal(w.validateStep(4), false, 'con preguntas sin responder no debe avanzar');
    assert.match(w.__alerts[0], /Responda las preguntas/);

    // Responder vuelve a consultar al backend con la respuesta
    evaluacionActual = {
        decision: 'ALLOWED_WITH_OPERATING_WARNING', bloquea: false, preguntas: [],
        titulo: 'Permitido', mensaje: 'La cerrajería no es vigilancia privada.',
        fundamento: [],
    };
    w.responderCIIU('principal', 'central_monitoreo', 'no');
    await new Promise(r => setTimeout(r, 30));
    assert.match(String(ultimaConsulta), /r_central_monitoreo=no/,
        'la respuesta debía viajar al backend: ' + ultimaConsulta);
    assert.ok(w.validateStep(4), 'ya resuelto, debía avanzar: ' + w.__alerts);
    console.log('  OK  preguntas condicionales bloquean y se resuelven contra el backend');

    // ── Autorización previa ──
    await elegir('4921', {
        decision: 'REQUIRES_PRIOR_AUTHORIZATION', bloquea: false,
        requiere_autorizacion: true, preguntas: [],
        titulo: 'Transporte público', mensaje: 'Exige habilitación previa',
        autoridad: 'Ministerio de Transporte', fundamento: [],
    });
    assert.ok(panel.querySelector('input[type="file"]'), 'debía ofrecer carga del acto');
    assert.match(panel.textContent, /Ministerio de Transporte/);
    w.__alerts = [];
    assert.equal(w.validateStep(4), false, 'sin adjuntar la autorización no avanza');
    assert.match(w.__alerts[0], /adjuntar la autorización previa/);

    // Se sube el acto administrativo
    const inputFalso = { files: [new w.File(['x'], 'resolucion.pdf')], value: '' };
    await w.subirAutorizacionCIIU(inputFalso, 'principal');
    await new Promise(r => setTimeout(r, 30));
    assert.match(panel.textContent, /resolucion\.pdf/);
    assert.ok(w.validateStep(4), 'con la autorización adjunta debía avanzar: ' + w.__alerts);

    const d = w.collectAllData();
    assert.equal(d.ciiu_autorizaciones['4921'].documento_id, 'abc');
    console.log('  OK  autorización previa: pide el archivo, lo adjunta y deja avanzar');

    // ── Cambiar de código invalida lo declarado antes ──
    await elegir('6201', { decision: 'ALLOWED', bloquea: false, preguntas: [] });
    assert.ok(panel.classList.contains('hidden'), 'sin restricción no se muestra panel');
    const d2 = w.collectAllData();
    assert.equal(Object.keys(d2.ciiu_autorizaciones).length, 0,
        'al cambiar el código debe invalidarse la autorización adjunta');
    assert.ok(w.validateStep(4), 'un código sin restricción debe pasar');
    console.log('  OK  cambiar el código invalida respuestas y autorización previas');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Varios representantes legales y limitaciones');
{
    const w = nuevaApp();
    llenarPaso1(w);
    llenarAccionista(w, 1, { nombre: 'Ana Restrepo', id: '43000111', pct: 100, genero: 'F' });
    w.showStep(3);

    // Primer principal y primer suplente: campos de siempre
    set(w, 'rl_principal_nombre', 'Ana Restrepo');
    set(w, 'rl_principal_cedula', '43000111');
    set(w, 'rl_suplente_nombre', 'Luisa Mora');
    set(w, 'rl_suplente_cedula', '43555666');

    // Adicionales
    w.addRepresentante('principal');
    set(w, 'rl_principal_2_nombre', 'Pedro Gómez');
    set(w, 'rl_principal_2_cedula', '71222333');
    w.addRepresentante('suplente');
    set(w, 'rl_suplente_2_nombre', 'Carlos Ruiz');
    set(w, 'rl_suplente_2_cedula', '71888999');

    const principales = w.getRepresentantes('principal');
    const suplentes = w.getRepresentantes('suplente');
    assert.equal(principales.length, 2, 'debía haber dos principales');
    assert.equal(suplentes.length, 2, 'debía haber dos suplentes');
    assert.equal(principales[1].nombre, 'Pedro Gómez');
    assert.equal(suplentes[1].cc, '71888999');

    // Cada tarjeta nueva trae su carga de documento y su selector
    assert.ok(w.document.getElementById('rl_principal_2_upload_status'));
    assert.equal(w.document.querySelectorAll('[data-rl-select]').length, 2);
    console.log('  OK  se agregan principales y suplentes adicionales');

    // ── Limitaciones ──
    marcarRadio(w, 'rl_limitaciones', 'si');
    assert.ok(!w.document.getElementById('limitaciones-fields').classList.contains('hidden'));
    w.__alerts = [];
    assert.equal(w.validateStep(3), false, 'sin escoger el tipo de limitación no avanza');
    assert.match(w.__alerts[0], /por cuantía, por naturaleza/);

    marcarRadio(w, 'lim_cuantia', 'si');
    w.__alerts = [];
    assert.equal(w.validateStep(3), false, 'falta la cuantía');
    assert.match(w.__alerts[0], /cuantía máxima/);
    set(w, 'lim_cuantia_smmlv', '500');
    set(w, 'lim_cuantia_organo', 'asamblea');

    marcarRadio(w, 'lim_naturaleza', 'si');
    w.__alerts = [];
    assert.equal(w.validateStep(3), false, 'falta describir la naturaleza');
    assert.match(w.__alerts[0], /naturaleza de los contratos/);
    set(w, 'lim_naturaleza_texto', 'la enajenación o gravamen de bienes inmuebles');
    set(w, 'lim_naturaleza_organo', 'junta');

    assert.ok(w.validateStep(3), 'completo debía avanzar: ' + w.__alerts);

    const d = w.collectAllData();
    assert.equal(d.rl_principales.length, 2);
    assert.equal(d.rl_suplentes.length, 2);
    assert.equal(d.limitaciones_rl.cuantia_smmlv, '500');
    assert.equal(d.limitaciones_rl.organo_cuantia, 'asamblea');
    assert.equal(d.limitaciones_rl.organo_naturaleza, 'junta');
    // El primero sigue viajando suelto: es el que usan los formularios
    assert.equal(d.rl_principal.nombre, 'Ana Restrepo');
    console.log('  OK  limitaciones: exige cuantía y naturaleza según lo marcado');
}

// ════════════════════════════════════════════════════════════════
console.log('\n─── Responsabilidades tributarias: checklist sin duplicar ni chocar');
{
    const w = nuevaApp();
    // Respuesta del backend para régimen ordinario
    w.fetch = async (url) => ({
        ok: true,
        json: async () => (String(url).includes('regimen=simple') ? {
            predeterminadas: [
                { codigo: '07', nombre: 'Retención en la Fuente a título de renta' },
                { codigo: '14', nombre: 'Informante de Exógena' },
                { codigo: '42', nombre: 'Obligado a llevar contabilidad' },
                { codigo: '47', nombre: 'Régimen Simple de Tributación' },
                { codigo: '48', nombre: 'Impuesto sobre las ventas' },
                { codigo: '55', nombre: 'Informante de Beneficiarios Finales' },
            ],
            // Sin la 33: el Régimen Simple ya la integra
            adicionales: [
                { codigo: '10', nombre: 'Usuario aduanero', descripcion: 'Comercio exterior.' },
                { codigo: '16', nombre: 'Obligación de facturar por excluidos', descripcion: '...' },
            ],
            no_seleccionables: [
                { codigo: '49', nombre: 'No responsable de IVA', motivo: 'Las sociedades no pueden incluirla.' },
            ],
            maximo_anexo: 10, cupo_adicionales: 4,
        } : {
            predeterminadas: [
                { codigo: '05', nombre: 'Impuesto sobre la Renta Régimen Ordinario' },
                { codigo: '07', nombre: 'Retención en la Fuente a título de renta' },
                { codigo: '14', nombre: 'Informante de Exógena' },
                { codigo: '42', nombre: 'Obligado a llevar contabilidad' },
                { codigo: '48', nombre: 'Impuesto sobre las ventas' },
                { codigo: '55', nombre: 'Informante de Beneficiarios Finales' },
            ],
            adicionales: [
                { codigo: '10', nombre: 'Usuario aduanero', descripcion: 'Comercio exterior.' },
                { codigo: '16', nombre: 'Obligación de facturar por excluidos', descripcion: '...' },
                { codigo: '33', nombre: 'Impuesto Nacional al Consumo', descripcion: '...' },
            ],
            no_seleccionables: [
                { codigo: '49', nombre: 'No responsable de IVA', motivo: 'Las sociedades no pueden incluirla.' },
            ],
            // Con el INC ya incluido solo quedan dos cupos en el anexo
            maximo_anexo: 10, cupo_adicionales: 2,
        }),
    });

    w.showStep(5);
    await new Promise(r => setTimeout(r, 40));

    const fijas = w.document.getElementById('resp-predeterminadas');
    const extras = w.document.getElementById('resp-adicionales');
    assert.match(fijas.textContent, /Van siempre con este régimen/);
    assert.match(fijas.textContent, /05/);

    // Ninguna de las fijas puede aparecer también como opción para agregar
    const codigosFijos = [...fijas.querySelectorAll('.resp-cod')].map(e => e.textContent.trim());
    const codigosExtra = [...extras.querySelectorAll('input[type="checkbox"]')].map(e => e.value);
    const repetidos = codigosFijos.filter(c => codigosExtra.includes(c));
    assert.equal(repetidos.length, 0, 'no se puede ofrecer lo que ya está: ' + repetidos);
    console.log('  OK  no ofrece las que ya vienen con el régimen');

    // Marcar la 10, que es el caso que pidió el usuario
    const casilla10 = extras.querySelector('input[value="10"]');
    assert.ok(casilla10, 'la 10 debía ofrecerse');
    casilla10.checked = true;
    w.toggleRespAdicional('10', true);
    assert.deepEqual([...w.collectAllData().responsabilidades_adicionales], ['10']);

    // Cambiar a Régimen Simple: la 33 deja de ofrecerse y se descarta si estaba
    w.toggleRespAdicional('33', true);
    w.selectRegimen('simple');
    await new Promise(r => setTimeout(r, 40));
    const codigosSimple = [...w.document.querySelectorAll('#resp-adicionales input[type="checkbox"]')]
        .map(e => e.value);
    assert.ok(!codigosSimple.includes('33'),
        'la 33 no debe ofrecerse en Régimen Simple: ya está integrada');
    assert.ok(!w.collectAllData().responsabilidades_adicionales.includes('33'),
        'al cambiar de régimen debe soltarse la que ya no aplica');
    assert.ok(w.collectAllData().responsabilidades_adicionales.includes('10'),
        'la 10 sigue siendo válida y debe conservarse');
    console.log('  OK  al cambiar de régimen suelta las excluyentes y conserva las válidas');

    // Se explica por qué no se ofrecen otras
    assert.match(w.document.getElementById('resp-vetadas').textContent,
        /No responsable de IVA .* no pueden incluirla/);
    console.log('  OK  explica por qué no se ofrecen las prohibidas');

    // ── El anexo tiene filas contadas: no se puede marcar de más ──
    const w2 = nuevaApp();
    w2.fetch = async () => ({
        ok: true,
        json: async () => ({
            predeterminadas: [{ codigo: '05', nombre: 'Renta' }],
            adicionales: [
                { codigo: '10', nombre: 'Usuario aduanero', descripcion: '' },
                { codigo: '16', nombre: 'Facturar excluidos', descripcion: '' },
                { codigo: '18', nombre: 'Precios de transferencia', descripcion: '' },
            ],
            no_seleccionables: [],
            maximo_anexo: 10,
            cupo_adicionales: 2,        // solo caben dos
        }),
    });
    w2.showStep(5);
    await new Promise(r => setTimeout(r, 40));

    const casillas = [...w2.document.querySelectorAll('#resp-adicionales input[type="checkbox"]')];
    assert.match(w2.document.getElementById('resp-cupo').textContent, /quedan 2 de 2/);

    casillas[0].checked = true; w2.toggleRespAdicional('10', true);
    casillas[1].checked = true; w2.toggleRespAdicional('16', true);

    assert.match(w2.document.getElementById('resp-cupo').textContent, /no cabe ninguna más/);
    assert.equal(casillas[2].disabled, true,
        'sin cupo, la tercera debe quedar deshabilitada en vez de fallar al generar');
    assert.equal(casillas[0].disabled, false, 'las ya marcadas se pueden desmarcar');

    // Al soltar una, vuelve a haber cupo
    casillas[0].checked = false; w2.toggleRespAdicional('10', false);
    assert.equal(casillas[2].disabled, false);
    console.log('  OK  respeta las diez filas del anexo: bloquea antes de desbordar');
}

console.log('\nCuestionario verificado.\n');
