// Company Maker - Frontend Logic (Reestructurado según instructivo)
let currentStep = 1;
const totalSteps = 7;
let accionistaCount = 0;
// apoderado toggle managed via toggleApoderado()

document.addEventListener('DOMContentLoaded', () => {
    addAccionista();

    // Sidebar step navigation
    document.querySelectorAll('.step-item[data-step]').forEach(item => {
        item.addEventListener('click', () => {
            const targetStep = parseInt(item.dataset.step);
            if (targetStep < currentStep) {
                showStep(targetStep);
            } else if (targetStep === currentStep + 1) {
                nextStep(currentStep);
            }
        });
    });
});

// ─── STEP NAVIGATION ───
function showStep(n) {
    document.querySelectorAll('.step').forEach(s => s.classList.add('hidden'));
    document.getElementById('step' + n).classList.remove('hidden');
    document.querySelectorAll('.step-item[data-step]').forEach(s => {
        const step = parseInt(s.dataset.step);
        s.classList.remove('active', 'done');
        if (step === n) s.classList.add('active');
        else if (step < n) s.classList.add('done');
    });
    // Update mobile progress bar
    const progressFill = document.getElementById('progress-fill');
    if (progressFill) progressFill.style.width = ((n / totalSteps) * 100) + '%';

    currentStep = n;
    if (n === 3) populateRLSelects();
    if (n === 7) buildSummary();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function nextStep(from) {
    if (!validateStep(from)) return;
    showStep(from + 1);
}
function prevStep(from) { showStep(from - 1); }

function validateStep(step) {
    if (step === 1) {
        const nombre = document.getElementById('nombre_sas').value.trim();
        if (!nombre) { alert('Ingrese la razón social'); return false; }
        // Normalize S.A.S.
        const upper = nombre.toUpperCase();
        if (!upper.includes('S.A.S')) {
            if (!confirm('La razón social no incluye "S.A.S." — ¿desea continuar?')) return false;
        }
        const email = document.getElementById('email').value.trim();
        if (email) {
            if (email.length > 60) { alert('El correo no puede exceder 60 caracteres (regla DIAN)'); return false; }
            const atIdx = email.indexOf('@');
            if (atIdx > 0 && email[atIdx - 1] === '-') { alert('El correo no puede tener guión antes del @ (regla DIAN)'); return false; }
        }
    }
    if (step === 2) {
        const cards = document.querySelectorAll('.accionista-card');
        if (cards.length === 0) { alert('Agregue al menos un accionista'); return false; }
        let totalPct = 0;
        for (const card of cards) {
            const tipo = card.querySelector('[name$="_tipo_persona"]').value;
            let nombre, idNum, domicilio;
            if (tipo === 'juridica') {
                nombre = card.querySelector('[name$="_razon_social"]').value.trim();
                idNum = card.querySelector('[name$="_nit"]').value.trim();
                domicilio = card.querySelector('[name$="_domicilio_pj"]').value.trim();
            } else {
                nombre = card.querySelector('[name$="_nombre"]').value.trim();
                idNum = card.querySelector('[name$="_id_num"]').value.trim();
                domicilio = card.querySelector('[name$="_domicilio"]').value.trim();
            }
            const pct = parseFloat(card.querySelector('[name$="_porcentaje"]').value) || 0;
            if (!nombre) { alert('Complete el nombre/razón social de todos los accionistas'); return false; }
            if (!idNum) { alert('Complete la identificación/NIT de todos los accionistas'); return false; }
            if (!domicilio) { alert('Complete la ciudad de domicilio actual de todos los accionistas (campo obligatorio)'); return false; }
            totalPct += pct;
        }
        if (Math.abs(totalPct - 100) > 0.01) {
            alert('Los porcentajes deben sumar 100%. Actual: ' + totalPct.toFixed(2) + '%');
            return false;
        }
    }
    return true;
}

// ─── ACCIONISTAS ───
function addAccionista() {
    accionistaCount++;
    const n = accionistaCount;
    const container = document.getElementById('accionistas-container');
    const card = document.createElement('div');
    card.className = 'accionista-card';
    card.id = 'acc_' + n;
    card.innerHTML = `
        <div class="card-header">
            <h4>Accionista ${n}</h4>
            <button type="button" class="btn btn-danger" onclick="removeAccionista(${n})">Eliminar</button>
        </div>
        <div class="form-group">
            <label>Tipo de persona</label>
            <select name="acc${n}_tipo_persona" onchange="toggleAccType(${n}, this.value)">
                <option value="natural">Persona Natural</option>
                <option value="juridica">Persona Jurídica</option>
            </select>
        </div>

        <!-- Persona Natural fields -->
        <div id="acc${n}_natural_fields">
            <div class="upload-doc-section" id="acc${n}_upload_natural">
                <div class="upload-doc-info">
                    <strong>📷 Autocompletar desde cédula o pasaporte</strong>
                    <span class="upload-hint">Suba una foto o PDF y Sí S.A.S. extraerá los datos automáticamente. Opcional — también puede llenar manualmente.</span>
                </div>
                <label class="upload-doc-btn">
                    Cargar documento
                    <input type="file" accept="image/*,application/pdf" onchange="extractFromCedula(this, 'acc${n}', ${n})">
                </label>
                <span class="upload-status" id="acc${n}_upload_status"></span>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Nombres y apellidos completos</label>
                    <input type="text" name="acc${n}_nombre" placeholder="Ej: María López García">
                </div>
                <div class="form-group">
                    <label>Tipo de documento</label>
                    <select name="acc${n}_tipo_doc">
                        <option value="CC">Cédula de Ciudadanía</option>
                        <option value="CE">Cédula de Extranjería</option>
                        <option value="Pasaporte">Pasaporte</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Número de documento</label>
                    <input type="text" name="acc${n}_id_num" placeholder="Ej: 1.037.657.432">
                </div>
                <div class="form-group">
                    <label>Ciudad de expedición</label>
                    <input type="text" name="acc${n}_expedicion" placeholder="Ej: Envigado">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Ciudad de domicilio actual <span style="color:var(--danger)">*</span></label>
                    <input type="text" name="acc${n}_domicilio" placeholder="Ej: Medellín" required>
                    <span class="hint">Diligenciar manualmente (no se extrae del documento).</span>
                </div>
                <div class="form-group">
                    <label>Fecha de nacimiento</label>
                    <input type="date" name="acc${n}_nacimiento">
                    <span class="hint">Para determinar si aplica Ley 1780</span>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Género</label>
                    <select name="acc${n}_genero">
                        <option value="M">Masculino</option>
                        <option value="F">Femenino</option>
                    </select>
                    <span class="hint">Para conjugación en estatutos y % mujeres RUES</span>
                </div>
            </div>
        </div>

        <!-- Persona Jurídica fields (hidden by default) -->
        <div id="acc${n}_juridica_fields" class="hidden">
            <div class="upload-doc-section">
                <div class="upload-doc-info">
                    <strong>📄 Autocompletar desde Certificado de Cámara de Comercio</strong>
                    <span class="upload-hint">Suba el Certificado de Existencia y Representación Legal. Sí S.A.S. extraerá razón social, NIT, domicilio y datos del RL.</span>
                </div>
                <label class="upload-doc-btn">
                    Cargar certificado
                    <input type="file" accept="image/*,application/pdf" onchange="extractFromCertificado(this, 'acc${n}', ${n})">
                </label>
                <span class="upload-status" id="acc${n}_upload_status_jur"></span>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Razón social</label>
                    <input type="text" name="acc${n}_razon_social" placeholder="Ej: HOLDING ABC S.A.S.">
                </div>
                <div class="form-group">
                    <label>NIT (con dígito de verificación)</label>
                    <input type="text" name="acc${n}_nit" placeholder="Ej: 900.123.456-7">
                </div>
            </div>
            <div class="form-group">
                <label>Ciudad de domicilio de la persona jurídica</label>
                <input type="text" name="acc${n}_domicilio_pj" placeholder="Ej: Medellín">
            </div>
            <p class="hint" style="margin-top:8px"><strong>Representante Legal de esta persona jurídica:</strong></p>
            <div class="form-row">
                <div class="form-group">
                    <label>Nombre completo del RL</label>
                    <input type="text" name="acc${n}_rl_nombre" placeholder="Nombre del rep. legal">
                </div>
                <div class="form-group">
                    <label>Cédula del RL</label>
                    <input type="text" name="acc${n}_rl_cc" placeholder="Ej: 1.234.567.890">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Ciudad de expedición del RL</label>
                    <input type="text" name="acc${n}_rl_expedicion" placeholder="Ej: Medellín">
                </div>
                <div class="form-group">
                    <label>Género del RL</label>
                    <select name="acc${n}_rl_genero">
                        <option value="M">Masculino</option>
                        <option value="F">Femenino</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label>Porcentaje accionario (%)</label>
                <input type="number" name="acc${n}_porcentaje" min="0" max="100" step="0.01" placeholder="Ej: 50"
                       oninput="syncPorcentaje(this, ${n})">
            </div>
            <div class="form-group">
                <label>Capital pagado ($)</label>
                <input type="text" name="acc${n}_capital_pagado" placeholder="0"
                       oninput="formatMoney(this); recalcCapitalPagadoTotal()">
                <span class="hint">Monto pagado por este accionista. Deje en 0 si aún no ha pagado nada.</span>
            </div>
        </div>
    `;
    container.appendChild(card);
}

function toggleAccType(n, tipo) {
    const natFields = document.getElementById('acc' + n + '_natural_fields');
    const jurFields = document.getElementById('acc' + n + '_juridica_fields');
    if (tipo === 'juridica') {
        natFields.classList.add('hidden');
        jurFields.classList.remove('hidden');
    } else {
        natFields.classList.remove('hidden');
        jurFields.classList.add('hidden');
    }
}

function removeAccionista(n) {
    const card = document.getElementById('acc_' + n);
    if (card) card.remove();
}

// ─── RL SELECTS ───
function populateRLSelects() {
    const accionistas = getAccionistasData();
    ['principal', 'suplente'].forEach(tipo => {
        const sel = document.getElementById('rl_' + tipo + '_select');
        const currentVal = sel.value;
        sel.innerHTML = tipo === 'suplente'
            ? '<option value="">-- Ninguno --</option>'
            : '<option value="">-- Escribir manualmente --</option>';
        accionistas.forEach((acc, i) => {
            if (acc.tipo === 'natural') {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = acc.nombre;
                sel.appendChild(opt);
            }
        });
        sel.value = currentVal;
    });
}

function selectRL(tipo) {
    const sel = document.getElementById('rl_' + tipo + '_select');
    const idx = parseInt(sel.value);
    if (isNaN(idx)) {
        document.getElementById('rl_' + tipo + '_nombre').value = '';
        document.getElementById('rl_' + tipo + '_cedula').value = '';
        document.getElementById('rl_' + tipo + '_expedicion').value = '';
        return;
    }
    const accionistas = getAccionistasData();
    if (accionistas[idx]) {
        document.getElementById('rl_' + tipo + '_nombre').value = accionistas[idx].nombre;
        document.getElementById('rl_' + tipo + '_cedula').value = accionistas[idx].id_num;
        document.getElementById('rl_' + tipo + '_expedicion').value = accionistas[idx].expedicion || '';
        document.getElementById('rl_' + tipo + '_tipo_doc').value = accionistas[idx].tipo_doc || 'CC';
        document.getElementById('rl_' + tipo + '_genero').value = accionistas[idx].genero || 'M';
    }
}

// ─── CIIU SEARCH ───
let searchTimeout = null;
function searchCIIU(query, variant) {
    clearTimeout(searchTimeout);
    const suffix = variant === 'principal' ? '' : '_sec';
    const results = document.getElementById('ciiu_results' + suffix);
    if (query.length < 2) { results.classList.add('hidden'); return; }
    searchTimeout = setTimeout(async () => {
        try {
            const resp = await fetch('/api/ciiu/search?q=' + encodeURIComponent(query));
            const data = await resp.json();
            if (data.length === 0) {
                results.innerHTML = '<div class="result-item" style="color:#999">No se encontraron resultados</div>';
            } else {
                results.innerHTML = data.map(item =>
                    `<div class="result-item" onclick="selectCIIUVariant('${item.code}', '${item.description.replace(/'/g, "\\'")}', '${variant}')">
                        <span class="code">${item.code}</span> ${item.description}
                    </div>`
                ).join('');
            }
            results.classList.remove('hidden');
        } catch (e) { console.error('CIIU search error:', e); }
    }, 300);
}

function selectCIIUVariant(code, desc, variant) {
    const suffix = variant === 'principal' ? '' : '_sec';
    document.getElementById('ciiu_code' + suffix).value = code;
    document.getElementById('ciiu_description' + suffix).value = desc;
    const searchEl = document.getElementById(variant === 'principal' ? 'ciiu_search' : 'ciiu_search_sec');
    searchEl.value = code + ' - ' + desc;
    document.getElementById('ciiu_results' + suffix).classList.add('hidden');
    const tag = document.getElementById('ciiu_selected' + suffix);
    tag.textContent = code + ' - ' + desc;
    tag.classList.remove('hidden');
}

// ─── APODERADO (toggle) ───
function toggleApoderado(show) {
    const fields = document.getElementById('apoderado-fields');
    if (show) {
        fields.classList.remove('hidden');
    } else {
        fields.classList.add('hidden');
    }
    // Update radio card styling
    document.querySelectorAll('input[name="tiene_apoderado"]').forEach(radio => {
        radio.closest('.radio-card').classList.toggle('selected', radio.checked);
    });
}

// ─── EXTRACCIÓN AUTOMÁTICA DE DATOS (Claude Vision) ───

/**
 * Extrae datos de cédula/pasaporte y autocompleta los campos del accionista.
 * Funciona para tarjetas de accionista (prefix = "accN") y bloques de RL
 * (prefix = "rl_principal" o "rl_suplente").
 */
async function extractFromCedula(input, prefix, n) {
    const file = input.files[0];
    if (!file) return;

    const statusId = (prefix.startsWith('rl_'))
        ? `${prefix}_upload_status`
        : `${prefix}_upload_status`;
    const statusEl = document.getElementById(statusId);

    _setStatus(statusEl, 'processing', '<span class="spinner"></span> Procesando documento...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/extract/cedula', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();
        if (!resp.ok || data.error) {
            throw new Error(data.error || 'Error desconocido');
        }

        // Mapeo de campos según el contexto (accionista vs RL)
        const filled = [];

        if (prefix === 'apoderado') {
            // Apoderado — campos con id= fijo
            _fillIfPresent('apoderado_nombre', data.nombre_completo, filled, 'Nombre');
            _fillSelectIfPresent('apoderado_tipo_doc', _normTipoDoc(data.tipo_documento), filled, 'Tipo doc');
            _fillIfPresent('apoderado_id_num', data.numero_documento, filled, 'Documento');
        } else if (prefix.startsWith('rl_')) {
            // Representante legal (principal o suplente)
            _fillIfPresent(`${prefix}_nombre`, data.nombre_completo, filled, 'Nombre');
            _fillSelectIfPresent(`${prefix}_tipo_doc`, _normTipoDoc(data.tipo_documento), filled, 'Tipo doc');
            _fillIfPresent(`${prefix}_cedula`, data.numero_documento, filled, 'Cédula');
            _fillIfPresent(`${prefix}_expedicion`, data.ciudad_expedicion, filled, 'Ciudad expedición');
            _fillSelectIfPresent(`${prefix}_genero`, data.genero, filled, 'Género');
        } else {
            // Accionista persona natural — campos por name=
            _fillByNameIfPresent(`${prefix}_nombre`, data.nombre_completo, filled, 'Nombre');
            _fillByNameIfPresent(`${prefix}_tipo_doc`, _normTipoDoc(data.tipo_documento), filled, 'Tipo doc');
            _fillByNameIfPresent(`${prefix}_id_num`, data.numero_documento, filled, 'Documento');
            _fillByNameIfPresent(`${prefix}_expedicion`, data.ciudad_expedicion, filled, 'Ciudad expedición');
            _fillByNameIfPresent(`${prefix}_nacimiento`, data.fecha_nacimiento, filled, 'Fecha nacimiento');
            _fillByNameIfPresent(`${prefix}_genero`, data.genero, filled, 'Género');
        }

        if (filled.length === 0) {
            _setStatus(statusEl, 'error',
                '⚠ No se pudieron extraer datos. Verifique la calidad de la imagen o llene manualmente.');
        } else {
            _setStatus(statusEl, 'success',
                `✓ Datos extraídos: ${filled.join(', ')}. Verifique y complete los campos restantes (ej: domicilio actual).`);
        }
    } catch (e) {
        _setStatus(statusEl, 'error', `✗ Error al procesar: ${e.message}`);
        console.error('extractFromCedula error:', e);
    } finally {
        input.value = '';  // permitir resubir el mismo archivo
    }
}

/**
 * Extrae datos de Certificado de Existencia y Representación Legal
 * (Cámara de Comercio) y autocompleta los campos del accionista jurídico.
 */
async function extractFromCertificado(input, prefix, n) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById(`${prefix}_upload_status_jur`);
    _setStatus(statusEl, 'processing', '<span class="spinner"></span> Procesando certificado...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/extract/certificado', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();
        if (!resp.ok || data.error) {
            throw new Error(data.error || 'Error desconocido');
        }

        const filled = [];
        // Datos de la persona jurídica
        _fillByNameIfPresent(`${prefix}_razon_social`, data.razon_social, filled, 'Razón social');
        // NIT con dígito de verificación: combinar nit y nit_dv si están
        let nitCompleto = data.nit || '';
        if (data.nit_dv && nitCompleto) {
            nitCompleto = `${nitCompleto}-${data.nit_dv}`;
        }
        _fillByNameIfPresent(`${prefix}_nit`, nitCompleto, filled, 'NIT');
        _fillByNameIfPresent(`${prefix}_domicilio_pj`, data.ciudad_domicilio, filled, 'Domicilio PJ');
        // Datos del RL de la persona jurídica
        _fillByNameIfPresent(`${prefix}_rl_nombre`, data.representante_legal_nombre, filled, 'RL nombre');
        _fillByNameIfPresent(`${prefix}_rl_cc`, data.representante_legal_cc, filled, 'RL cédula');
        _fillByNameIfPresent(`${prefix}_rl_expedicion`, data.representante_legal_expedicion, filled, 'RL expedición');
        _fillByNameIfPresent(`${prefix}_rl_genero`, data.representante_legal_genero, filled, 'RL género');

        if (filled.length === 0) {
            _setStatus(statusEl, 'error',
                '⚠ No se pudieron extraer datos. Verifique la calidad del certificado o llene manualmente.');
        } else {
            _setStatus(statusEl, 'success', `✓ Datos extraídos: ${filled.join(', ')}.`);
        }
    } catch (e) {
        _setStatus(statusEl, 'error', `✗ Error al procesar: ${e.message}`);
        console.error('extractFromCertificado error:', e);
    } finally {
        input.value = '';
    }
}

// ─── Helpers de extracción ───
function _setStatus(el, klass, html) {
    if (!el) return;
    el.className = 'upload-status ' + klass;
    el.innerHTML = html;
}

function _fillIfPresent(id, value, filledArr, label) {
    if (!value) return;
    const el = document.getElementById(id);
    if (el) { el.value = value; filledArr.push(label); }
}

function _fillByNameIfPresent(name, value, filledArr, label) {
    if (!value) return;
    const el = document.querySelector(`[name="${name}"]`);
    if (el) {
        if (el.tagName === 'SELECT') {
            // Buscar opción que coincida (case-insensitive)
            const v = String(value).toUpperCase();
            for (const opt of el.options) {
                if (opt.value.toUpperCase() === v) {
                    el.value = opt.value;
                    filledArr.push(label);
                    return;
                }
            }
        } else {
            el.value = value;
            filledArr.push(label);
        }
    }
}

function _fillSelectIfPresent(id, value, filledArr, label) {
    if (!value) return;
    const el = document.getElementById(id);
    if (el && el.tagName === 'SELECT') {
        const v = String(value).toUpperCase();
        for (const opt of el.options) {
            if (opt.value.toUpperCase() === v) {
                el.value = opt.value;
                filledArr.push(label);
                return;
            }
        }
    }
}

function _normTipoDoc(tipo) {
    // Normaliza "CC" / "C.C." / "Cédula" → "CC" para los selects
    if (!tipo) return '';
    const t = tipo.toUpperCase().replace(/\./g, '').trim();
    if (t === 'CC' || t.startsWith('CEDULA') || t.startsWith('CÉDULA')) return 'CC';
    if (t === 'CE' || t.includes('EXTRANJ')) return 'CE';
    if (t.includes('PASAPORTE') || t === 'P') return 'Pasaporte';
    return tipo;
}

// ─── MONEY FORMAT ───
function formatMoney(input) {
    let val = input.value.replace(/\D/g, '');
    if (val === '') { input.value = ''; return; }
    input.value = parseInt(val).toLocaleString('es-CO');
}

function _parseCop(str) {
    return parseInt((str || '').replace(/\D/g, ''), 10) || 0;
}

function syncCapital() {
    // Al cambiar capital suscrito solo recalcula el total; el pagado lo maneja el usuario.
    recalcCapitalPagadoTotal();
}

function syncPorcentaje(input, n) {
    // Al ingresar porcentaje solo recalcula el total; el pagado lo maneja el usuario.
    recalcCapitalPagadoTotal();
}

function onCapitalPagadoTotalChange() {
    // El usuario está editando el total directamente (modo global).
    const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
    const pagadoEl = document.getElementById('capital_pagado');
    if (_parseCop(pagadoEl.value) > suscrito) {
        pagadoEl.value = suscrito.toLocaleString('es-CO');
    }
}

function recalcCapitalPagadoTotal() {
    // Suma los capital_pagado individuales de los accionistas y muestra el total.
    // Si un accionista tiene el campo vacío, se asume que pagó su porción completa.
    const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
    const pagadoDisplay = document.getElementById('capital_pagado');
    if (!pagadoDisplay) return;
    const accionistas = getAccionistasData();
    if (accionistas.length === 0) return;

    let total = 0;
    let hayAlgunPorcentaje = false;
    for (const acc of accionistas) {
        const pct = acc.porcentaje || 0;
        if (pct <= 0) continue;
        hayAlgunPorcentaje = true;
        const suscAcc = Math.round(suscrito * pct / 100);
        const pagAcc = (acc.capital_pagado && _parseCop(acc.capital_pagado) > 0)
            ? Math.min(_parseCop(acc.capital_pagado), suscAcc)
            : 0;  // vacío o cero = no ha pagado
        total += pagAcc;
    }
    if (hayAlgunPorcentaje) {
        pagadoDisplay.value = total > 0 ? total.toLocaleString('es-CO') : '';
    }
}

function selectRegimen(valor) {
    document.getElementById('regimen').value = valor;
    document.querySelectorAll('#step5 .radio-card').forEach(c => c.classList.remove('selected'));
    const radio = document.getElementById('regimen_' + valor);
    if (radio) {
        radio.checked = true;
        radio.closest('.radio-card').classList.add('selected');
    }
}

function toggleJunta(val) {
    // Update radio-card styling
    document.querySelectorAll('input[name="junta"]').forEach(r => {
        r.closest('.radio-card').classList.toggle('selected', r.checked);
    });
}

// Radio-card click handler — update selected styling for all radio groups
document.addEventListener('change', function(e) {
    if (e.target.type === 'radio' && e.target.closest('.radio-cards')) {
        const group = e.target.closest('.radio-cards');
        group.querySelectorAll('.radio-card').forEach(c => c.classList.remove('selected'));
        e.target.closest('.radio-card').classList.add('selected');
    }
});

// ─── DATA COLLECTION ───
function getAccionistasData() {
    const accionistas = [];
    document.querySelectorAll('.accionista-card').forEach(card => {
        const inputs = card.querySelectorAll('input, select');
        const raw = {};
        inputs.forEach(inp => {
            const key = inp.name.replace(/^acc\d+_/, '');
            raw[key] = inp.value.trim();
        });
        const tipo = raw.tipo_persona || 'natural';
        const acc = { tipo: tipo, porcentaje: parseFloat(raw.porcentaje) || 0 };

        if (tipo === 'juridica') {
            acc.nombre = raw.razon_social || '';
            acc.id_tipo = 'NIT';
            acc.id_num = raw.nit || '';
            acc.domicilio = raw.domicilio_pj || '';
            acc.rl_nombre = raw.rl_nombre || '';
            acc.rl_cc = raw.rl_cc || '';
            acc.rl_expedicion = raw.rl_expedicion || '';
            acc.rl_genero = raw.rl_genero || 'M';
        } else {
            acc.nombre = raw.nombre || '';
            acc.tipo_doc = raw.tipo_doc || 'CC';
            acc.id_tipo = raw.tipo_doc === 'NIT' ? 'NIT' : (raw.tipo_doc === 'CE' ? 'C.E.' : (raw.tipo_doc === 'Pasaporte' ? 'Pasaporte' : 'C.C.'));
            acc.id_num = raw.id_num || '';
            acc.expedicion = raw.expedicion || '';
            acc.domicilio = raw.domicilio || '';
            acc.nacimiento = raw.nacimiento || '';
            acc.genero = raw.genero || 'M';
        }
        // Capital pagado individual (vacío = 100% del suscrito de este accionista)
        acc.capital_pagado = raw.capital_pagado || '';
        if (acc.nombre) accionistas.push(acc);
    });
    return accionistas;
}

function getApoderadoData() {
    const tieneApoderado = document.querySelector('input[name="tiene_apoderado"]:checked')?.value === 'si';
    if (!tieneApoderado) return null;
    const nombre = (document.getElementById('apoderado_nombre')?.value || '').trim();
    if (!nombre) return null;
    return {
        nombre: nombre,
        id_tipo: document.getElementById('apoderado_tipo_doc')?.value || 'CC',
        id_num: (document.getElementById('apoderado_id_num')?.value || '').trim(),
        domicilio_ciudad: (document.getElementById('apoderado_ciudad')?.value || 'Medellín').trim(),
        domicilio_departamento: (document.getElementById('apoderado_departamento')?.value || 'Antioquia').trim(),
    };
}

function collectAllData() {
    const accionistas = getAccionistasData();
    const apoderado = getApoderadoData();

    const rlSuplNombre = document.getElementById('rl_suplente_nombre').value.trim();

    return {
        nombre_sas: document.getElementById('nombre_sas').value.trim().toUpperCase(),
        municipio: document.getElementById('municipio').value.trim(),
        departamento: document.getElementById('departamento').value.trim(),
        direccion: document.getElementById('direccion').value.trim(),
        barrio: document.getElementById('barrio').value.trim(),
        email: document.getElementById('email').value.trim(),
        telefono1: document.getElementById('telefono1').value.trim(),
        telefono2: document.getElementById('telefono2').value.trim(),
        telefono3: document.getElementById('telefono3').value.trim(),
        zona: document.getElementById('zona').value,
        tipo_local: document.getElementById('tipo_local').value,
        tenencia: document.getElementById('tenencia').value,
        accionistas: accionistas,
        rl_principal: {
            nombre: document.getElementById('rl_principal_nombre').value.trim(),
            cc: document.getElementById('rl_principal_cedula').value.trim(),
            tipo_doc: document.getElementById('rl_principal_tipo_doc').value,
            expedicion: document.getElementById('rl_principal_expedicion').value.trim(),
            genero: document.getElementById('rl_principal_genero').value,
        },
        rl_suplente: rlSuplNombre ? {
            nombre: rlSuplNombre,
            cc: document.getElementById('rl_suplente_cedula').value.trim(),
            tipo_doc: document.getElementById('rl_suplente_tipo_doc').value,
            expedicion: document.getElementById('rl_suplente_expedicion').value.trim(),
            genero: document.getElementById('rl_suplente_genero').value,
        } : null,
        ciiu_code: document.getElementById('ciiu_code').value,
        ciiu_description: document.getElementById('ciiu_description').value,
        ciiu_code_sec: document.getElementById('ciiu_code_sec').value,
        ciiu_description_sec: document.getElementById('ciiu_description_sec').value,
        objeto_social: document.getElementById('objeto_social').value.trim(),
        capital_suscrito: document.getElementById('capital_suscrito').value,
        // capital_pagado total se calcula en el backend a partir de los
        // pagados individuales de cada accionista. Se envía para display/fallback.
        capital_pagado: document.getElementById('capital_pagado').value,
        regimen: document.getElementById('regimen').value,
        ingresos_mensuales: document.getElementById('ingresos_mensuales').value,
        tiene_junta: document.querySelector('input[name="junta"]:checked')?.value === 'si',
        tiene_revisor: document.querySelector('input[name="revisor"]:checked')?.value === 'si',
        es_emprendimiento_social: document.querySelector('input[name="emprendimiento"]:checked')?.value === 'si',
        grupo_etnico: document.getElementById('grupo_etnico')?.value || '',
        apoderado: apoderado,
    };
}

// ─── SUMMARY ───
function buildSummary() {
    const d = collectAllData();
    const container = document.getElementById('summary-content');
    const f = (label, value) =>
        `<div class="summary-field"><span class="summary-label">${label}</span><span class="summary-value">${value || '—'}</span></div>`;

    let h = '<h3>Sociedad</h3>';
    h += f('Razón Social', d.nombre_sas);
    h += f('Dirección', d.direccion);
    h += f('Municipio', `${d.municipio}, ${d.departamento}`);
    h += f('Barrio', d.barrio);
    h += f('Correo', d.email);
    h += f('Teléfono(s)', [d.telefono1, d.telefono2, d.telefono3].filter(Boolean).join(', '));

    h += '<h3>Accionistas</h3>';
    d.accionistas.forEach((acc, i) => {
        const id = acc.tipo === 'juridica' ? `NIT ${acc.id_num}` : `${acc.id_tipo} ${acc.id_num}`;
        h += f(`Accionista ${i+1} (${acc.tipo})`, `${acc.nombre} (${id}) — ${acc.porcentaje}%`);
    });

    h += '<h3>Representante Legal</h3>';
    h += f('Principal', `${d.rl_principal.nombre} (${d.rl_principal.tipo_doc} ${d.rl_principal.cc})`);
    if (d.rl_suplente) {
        h += f('Suplente', `${d.rl_suplente.nombre} (${d.rl_suplente.tipo_doc} ${d.rl_suplente.cc})`);
    } else {
        h += f('Suplente', 'Vacante');
    }

    h += '<h3>Actividad</h3>';
    h += f('CIIU Principal', `${d.ciiu_code} — ${d.ciiu_description}`);
    if (d.ciiu_code_sec) h += f('CIIU Secundario', `${d.ciiu_code_sec} — ${d.ciiu_description_sec}`);
    h += f('Objeto Social', d.objeto_social ? d.objeto_social.substring(0, 150) + '...' : '—');

    h += '<h3>Capital y Régimen</h3>';
    h += f('Capital Autorizado', '$1.000.000.000 (fijo)');
    h += f('Capital Suscrito', '$' + d.capital_suscrito);
    h += f('Capital Pagado', '$' + d.capital_pagado);
    h += f('Régimen', d.regimen === 'simple' ? 'Simple (SIMPLE)' : 'Ordinario');

    h += '<h3>Documentos a Generar</h3><div class="docs-list">';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Estatutos</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formulario RUES</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formulario Otras Entidades</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Anexo Responsabilidades Tributarias</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Manifestación Emprendimientos Sociales</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Grupo Étnico</div>';

    // Situación de control: >50% estricto
    const hasControl = d.accionistas.some(a => a.porcentaje > 50);
    h += hasControl
        ? '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Situación de Control</div>'
        : '<div class="doc-item doc-conditional">— Situación de Control (no aplica)</div>';

    // Ley 1780: naturales ≤35 con >50% del CAPITAL
    const today = new Date();
    let pctJovenes = 0;
    d.accionistas.forEach(a => {
        if (a.tipo === 'natural' && a.nacimiento) {
            const birth = new Date(a.nacimiento);
            const age = (today - birth) / (365.25 * 24 * 60 * 60 * 1000);
            if (age <= 35) pctJovenes += a.porcentaje;
        }
    });
    const aplica1780 = pctJovenes > 50;
    h += aplica1780
        ? '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Ley 1780</div>'
        : '<div class="doc-item doc-conditional">— Ley 1780 (no aplica)</div>';

    h += '</div>';

    // Apoderado
    if (d.apoderado) {
        h += '<h3>Apoderado</h3>';
        h += f('Nombre', d.apoderado.nombre);
        h += f('Documento', `${d.apoderado.id_tipo} ${d.apoderado.id_num}`);
        h += f('Domicilio', `${d.apoderado.domicilio_ciudad}, ${d.apoderado.domicilio_departamento}`);
    }

    container.innerHTML = h;
}

// ─── GENERATE ───
async function generateDocuments() {
    const data = collectAllData();
    const btn = document.getElementById('btn-generate');
    const status = document.getElementById('generation-status');

    btn.disabled = true;
    btn.textContent = 'Generando...';
    status.classList.remove('hidden');

    try {
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || 'Error generando documentos');
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Constitucion ${data.nombre_sas}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        status.innerHTML = '<p style="color: var(--success); font-size: 1.1rem; font-weight: 600;">&#10003; Documentos generados exitosamente</p>';
    } catch (e) {
        status.innerHTML = `<p style="color: var(--error);">Error: ${e.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generar Documentos';
    }
}

// ═══════════════════════════════════════════════════════════
// CHAT ASISTENTE LEGAL
// ═══════════════════════════════════════════════════════════

let chatHistory = [];
let chatOpen = false;

function toggleChat() {
    const panel = document.getElementById('chat-panel');
    const toggle = document.getElementById('chat-toggle');
    chatOpen = !chatOpen;
    panel.classList.toggle('open', chatOpen);
    toggle.classList.toggle('active', chatOpen);
    if (chatOpen) {
        document.getElementById('chat-input').focus();
        scrollChatToBottom();
    }
}

function chatKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
    }
    // Auto-resize textarea
    const ta = e.target;
    setTimeout(() => {
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }, 0);
}

function scrollChatToBottom() {
    const container = document.getElementById('chat-messages');
    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
}

function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;

    // Simple markdown-like formatting
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';

    div.innerHTML = `<div class="chat-bubble">${html}</div>`;
    container.appendChild(div);
    scrollChatToBottom();
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';
    div.id = 'chat-typing';
    div.innerHTML = `<div class="chat-bubble chat-typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>`;
    container.appendChild(div);
    scrollChatToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('chat-typing');
    if (el) el.remove();
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');
    const message = input.value.trim();
    if (!message) return;

    // Add user message
    addChatMessage('user', message);
    chatHistory.push({ role: 'user', content: message });

    // Clear input
    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;

    // Show typing indicator
    showTypingIndicator();

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: chatHistory.slice(0, -1), // Don't send the message we just added
            }),
        });

        removeTypingIndicator();

        const data = await resp.json();

        if (data.reply) {
            addChatMessage('assistant', data.reply);
            chatHistory.push({ role: 'assistant', content: data.reply });
        } else if (data.error) {
            addChatMessage('assistant', data.error);
        }
    } catch (e) {
        removeTypingIndicator();
        addChatMessage('assistant', 'Error de conexión. Verifique que el servidor está activo.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }

    // Keep history manageable
    if (chatHistory.length > 30) {
        chatHistory = chatHistory.slice(-20);
    }
}
