// Company Maker - Frontend Logic (Reestructurado según instructivo)
let currentStep = 1;
const totalSteps = 7;
let accionistaCount = 0;
// apoderado toggle managed via toggleApoderado()

document.addEventListener('DOMContentLoaded', () => {
    addAccionista();
    onRazonSocialInput();

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
    if (n === 5) syncCapital();
    if (n === 6) { refreshControlBlock(); renderNucleoFamiliar(); populateJuntaSelects(); }
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
        // Homonimia: se exige haber abierto la consulta Y declarar el resultado.
        // El resultado en sí nunca bloquea; solo el riesgo máximo pide un
        // reconocimiento expreso.
        const irAlBloque = () => document.getElementById('homonimia-block')
            ?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });

        const distintivo = nombreDistintivo(document.getElementById('nombre_sas').value);
        if (_distintivoConsultado !== distintivo) {
            alert('Antes de continuar debe consultar la razón social en el RUES.\n\n'
                  + 'Pulse "Consultar en el RUES", revise lo que aparece y vuelva a marcar '
                  + 'el resultado.');
            irAlBloque();
            return false;
        }
        const homonimia = getHomonimiaData();
        if (!homonimia) {
            alert('Ya abrió el RUES. Ahora marque cuál de los cuatro resultados le apareció.');
            irAlBloque();
            return false;
        }
        if (homonimia.resultado === 'identica_activa' && !homonimia.riesgo_aceptado) {
            alert('La razón social NO está disponible: ya existe una sociedad activa registrada '
                  + 'con ella.\n\nLo recomendable es cambiarla. Si aun así quiere seguir, marque '
                  + 'la casilla donde acepta el riesgo de que la Cámara devuelva el trámite.');
            irAlBloque();
            return false;
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
    if (step === 5) {
        const autorizado = _parseCop(document.getElementById('capital_autorizado').value);
        const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
        const nominal = _parseCop(document.getElementById('valor_nominal').value);
        if (nominal < 1) { alert('El valor nominal por acción debe ser al menos $1'); return false; }
        if (suscrito < nominal) { alert('El capital suscrito no puede ser inferior al valor nominal de una acción'); return false; }
        if (autorizado < suscrito) {
            alert('El capital autorizado no puede ser inferior al capital suscrito.');
            return false;
        }
        if (autorizado % nominal !== 0 || suscrito % nominal !== 0) {
            alert('El capital autorizado y el suscrito deben ser múltiplos exactos del valor nominal por acción ($'
                  + nominal.toLocaleString('es-CO') + ').');
            return false;
        }
    }
    if (step === 6) {
        if (document.querySelector('input[name="junta"]:checked')?.value === 'si') {
            const n = parseInt(document.getElementById('junta_num_principales').value);
            const principales = getJuntaPersonas('junta-principales-container');
            if (principales.length < n) {
                alert(`Complete el nombre y la identificación de los ${n} miembros principales de la junta directiva.`);
                return false;
            }
        }
        if (document.querySelector('input[name="revisor"]:checked')?.value === 'si') {
            if (!getRevisorData()) {
                alert('Complete todos los datos del revisor fiscal (incluida la tarjeta profesional del contador).');
                return false;
            }
        }
        if (document.querySelector('input[name="empresa_familiar"]:checked')?.value === 'si') {
            const nucleo = getNucleoFamiliarData();
            if (nucleo.length === 0) {
                alert('Marque al menos un accionista que integre el núcleo familiar.');
                return false;
            }
            if (nucleo.length > 5) {
                alert('El formato oficial admite máximo 5 integrantes del núcleo familiar.');
                return false;
            }
            if (nucleo.some(m => !m.parentesco)) {
                alert('Indique el parentesco de cada integrante del núcleo familiar.');
                return false;
            }
            if (_pctNucleoFamiliar() <= 50) {
                alert('Los integrantes del núcleo familiar deben representar más de la mitad del capital. Actual: '
                      + _pctNucleoFamiliar().toFixed(2) + '%');
                return false;
            }
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
                    <input type="text" name="acc${n}_id_num" placeholder="No. de identificación">
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
                    <input type="text" name="acc${n}_rl_cc" placeholder="No. de identificación">
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
        } else if (prefix === 'revisor' || prefix === 'revisor_contador') {
            // Revisor fiscal persona natural, o contador designado por la
            // persona jurídica. Estos campos van por id=, no por name=.
            _fillIfPresent(`${prefix}_nombre`, data.nombre_completo, filled, 'Nombre');
            _fillSelectIfPresent(`${prefix}_tipo_doc`, _normTipoDoc(data.tipo_documento), filled, 'Tipo doc');
            _fillIfPresent(`${prefix}_id_num`, data.numero_documento, filled, 'Documento');
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
 * Extrae el número de la tarjeta profesional de contador público.
 * `prefix` es 'revisor' (persona natural) o 'revisor_contador' (el contador
 * que designa la firma de revisoría).
 */
async function extractFromTarjeta(input, prefix) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById(`${prefix}_tarjeta_upload_status`);
    _setStatus(statusEl, 'processing', '<span class="spinner"></span> Leyendo la tarjeta profesional...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/extract/tarjeta', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!resp.ok || data.error) throw new Error(data.error || 'Error desconocido');

        const filled = [];
        _fillIfPresent(`${prefix}_tarjeta`, data.numero_tarjeta, filled, 'Tarjeta profesional');
        // El nombre y la cédula solo se completan si aún están vacíos, para no
        // pisar lo que ya se extrajo de la cédula.
        const elNombre = document.getElementById(`${prefix}_nombre`);
        if (elNombre && !elNombre.value.trim() && data.nombre_completo) {
            elNombre.value = data.nombre_completo;
            filled.push('Nombre');
        }
        const elDoc = document.getElementById(`${prefix}_id_num`);
        if (elDoc && !elDoc.value.trim() && data.numero_documento) {
            elDoc.value = data.numero_documento;
            filled.push('Documento');
        }

        if (filled.length === 0) {
            _setStatus(statusEl, 'error',
                '⚠ No se pudo leer el número de la tarjeta. Verifique la imagen o escríbalo a mano.');
        } else {
            _setStatus(statusEl, 'success', `✓ Datos extraídos: ${filled.join(', ')}.`);
        }
    } catch (e) {
        _setStatus(statusEl, 'error', `✗ Error al procesar: ${e.message}`);
        console.error('extractFromTarjeta error:', e);
    } finally {
        input.value = '';
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

// ═══════════════════════════════════════════════════════════
// HOMONIMIA — verificación contra el RUES
// ═══════════════════════════════════════════════════════════
// La Cámara devuelve el trámite si ya existe una sociedad con nombre
// idéntico. La comparación legal recae sobre el nombre distintivo, no sobre
// el tipo societario, así que se despoja el sufijo antes de buscar.
//
// El RUES no expone su API a terceros (responde 401 fuera del navegador), de
// modo que la consulta la hace el abogado en el sitio oficial mediante enlace
// profundo y aquí declara el resultado.

// Ordenados de más largo a más corto: "S EN C A" debe consumirse antes que
// "S EN C", y "S A S" antes que "S A".
const SUFIJOS_SOCIETARIOS = [
    'SOCIEDAD DE BENEFICIO E INTERES COLECTIVO',
    'SOCIEDAD POR ACCIONES SIMPLIFICADA',
    'EMPRESA DE SERVICIOS PUBLICOS',
    'SOCIEDAD EN COMANDITA POR ACCIONES',
    'SOCIEDAD EN COMANDITA SIMPLE',
    'EMPRESA UNIPERSONAL',
    'SOCIEDAD ANONIMA',
    'SOCIEDAD LIMITADA',
    'EN LIQUIDACION',
    'S EN C A', 'S EN C', 'SENC',
    'S C A', 'S C S', 'SCA', 'SCS',
    'S A S', 'SAS',
    'LTDA', 'LIMITADA',
    'S A', 'SA',
    'E U', 'EU',
    'E S P', 'ESP',
    'B I C', 'BIC',
    'Y CIA', 'CIA',
];

function _normalizarNombre(s) {
    return (s || '')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')   // tildes
        .toUpperCase()
        .replace(/[^A-Z0-9\s]/g, ' ')                       // puntuación, &, guiones
        .replace(/\s+/g, ' ')
        .trim();
}

/** "Café Montaña S.A.S. B.I.C." -> "CAFE MONTANA" */
function nombreDistintivo(razonSocial) {
    let n = _normalizarNombre(razonSocial);
    let cambio = true;
    while (cambio && n) {
        cambio = false;
        for (const suf of SUFIJOS_SOCIETARIOS) {
            if (n === suf) { n = ''; cambio = true; break; }
            if (n.endsWith(' ' + suf)) {
                n = n.slice(0, n.length - suf.length - 1).trim();
                cambio = true;
                break;
            }
        }
    }
    return n;
}

// Nombre distintivo sobre el que se declaró el último resultado. Si el usuario
// cambia la razón social, tanto la consulta como la declaración caducan.
let _distintivoDeclarado = null;
// Nombre distintivo que efectivamente se abrió en el RUES. Sin esto no se
// puede avanzar: la declaración sola no prueba que se haya consultado.
let _distintivoConsultado = null;

function onRazonSocialInput() {
    const razon = document.getElementById('nombre_sas').value.trim();
    const distintivo = nombreDistintivo(razon);
    const termino = document.getElementById('homonimia-termino');
    const link = document.getElementById('homonimia-link');
    if (!termino || !link) return;

    if (!distintivo) {
        termino.innerHTML = '<em>Escriba primero la razón social.</em>';
        link.href = 'https://www.rues.org.co/';
        link.classList.add('hidden');
    } else {
        termino.innerHTML = '<span class="homo-termino">' + distintivo + '</span>';
        link.href = 'https://www.rues.org.co/buscar/RM/' + encodeURIComponent(distintivo);
        link.classList.remove('hidden');
    }

    // Consulta y declaración corresponden a un nombre concreto: si el nombre
    // distintivo cambia, ambas dejan de valer y hay que repetir la consulta.
    if (_distintivoConsultado !== null && distintivo !== _distintivoConsultado) {
        resetHomonimia();
    }
}

function resetHomonimia() {
    _distintivoDeclarado = null;
    _distintivoConsultado = null;
    document.querySelectorAll('input[name="homonimia"]').forEach(r => {
        r.checked = false;
    });
    document.querySelectorAll('.rues-opcion').forEach(o => o.classList.remove('elegida'));
    const ack = document.getElementById('homonimia_ack');
    if (ack) ack.checked = false;
    document.getElementById('homonimia-declaracion').classList.add('hidden');
    document.getElementById('homonimia-resultado').classList.add('hidden');
    document.getElementById('homonimia-ack-wrap').classList.add('hidden');

    const btn = document.getElementById('homonimia-link');
    if (btn) btn.classList.remove('consultado');
    const estado = document.getElementById('homonimia-estado-consulta');
    if (estado) {
        estado.textContent = 'Se abre en una pestaña nueva con la búsqueda ya escrita. '
                           + 'No tiene que digitar nada.';
    }
    ['homo-paso-1', 'homo-paso-2', 'homo-paso-3'].forEach(id => {
        document.getElementById(id)?.classList.remove('done');
    });
}

function marcarConsultaRues() {
    // Solo se llega aquí al pulsar el enlace, así que registra que la consulta
    // se abrió de verdad para el nombre que hay escrito en este momento.
    const distintivo = nombreDistintivo(document.getElementById('nombre_sas').value);
    if (!distintivo) return;
    _distintivoConsultado = distintivo;

    document.getElementById('homonimia-declaracion').classList.remove('hidden');
    document.getElementById('homonimia-link').classList.add('consultado');
    document.getElementById('homo-paso-1')?.classList.add('done');
    document.getElementById('homo-paso-2')?.classList.add('done');
    const estado = document.getElementById('homonimia-estado-consulta');
    if (estado) {
        estado.innerHTML = 'Consulta abierta para <strong>' + distintivo + '</strong>. '
                         + 'Revise el RUES y marque abajo lo que vio.';
    }
}

const HOMONIMIA_RIESGO = {
    min: {
        nivel: 'mínimo', clase: 'ok', icono: '✓',
        titulo: 'RAZÓN SOCIAL DISPONIBLE',
        texto: 'El RUES no encontró ninguna sociedad registrada con esta razón social. '
             + 'Puede continuar con la constitución.',
    },
    similar: {
        nivel: 'medio', clase: 'aviso', icono: '!',
        titulo: 'ATENCIÓN — puede haber objeción',
        texto: 'Hay sociedades con razones sociales parecidas. Como ninguna coincide por '
             + 'completo, el trámite normalmente pasa, pero la Cámara puede objetarlo si '
             + 'considera que se presta a confusión. <strong>Si puede, agregue una palabra '
             + 'que la diferencie más.</strong>',
    },
    identica_cancelada: {
        nivel: 'medio', clase: 'aviso', icono: '!',
        titulo: 'ATENCIÓN — esta razón social ya existió',
        texto: 'La razón social exacta ya está registrada, pero esa sociedad no está activa. '
             + 'En general se admite, aunque la Cámara puede pedir aclaración. '
             + '<strong>Confirme en el RUES que el estado dice Cancelada o Liquidada</strong> '
             + 'y no Activa: si estuviera activa, el riesgo es máximo.',
    },
    identica_activa: {
        nivel: 'máximo', clase: 'alto', icono: '✕',
        titulo: 'RAZÓN SOCIAL NO DISPONIBLE',
        texto: 'Ya existe una sociedad activa con esta misma razón social. '
             + '<strong>La Cámara va a devolver el trámite por homonimia.</strong> '
             + 'Lo recomendable es volver arriba y cambiarla ahora, '
             + 'antes de llenar el resto del formulario.',
    },
};

function onHomonimiaChange() {
    const sel = document.querySelector('input[name="homonimia"]:checked');
    const caja = document.getElementById('homonimia-resultado');
    const ackWrap = document.getElementById('homonimia-ack-wrap');

    // Estas opciones no usan .radio-card, así que su resaltado no lo maneja
    // el listener genérico de radio-cards: se marca aquí.
    document.querySelectorAll('.rues-opcion').forEach(o => {
        o.classList.toggle('elegida', !!o.querySelector('input')?.checked);
    });

    if (!sel) { caja.classList.add('hidden'); ackWrap.classList.add('hidden'); return; }

    const r = HOMONIMIA_RIESGO[sel.value];
    _distintivoDeclarado = nombreDistintivo(document.getElementById('nombre_sas').value);
    document.getElementById('homo-paso-3')?.classList.add('done');

    caja.className = 'homo-veredicto ' + r.clase;
    caja.innerHTML =
        '<span class="homo-veredicto-icono">' + r.icono + '</span>' +
        '<span class="homo-veredicto-cuerpo">' +
        '<span class="homo-veredicto-titulo">' + r.titulo + '</span>' +
        '<div class="homo-veredicto-texto">' + r.texto +
        '<br><br>Riesgo de homonimia: <strong>' + r.nivel + '</strong>.</div>' +
        '</span>';
    caja.classList.remove('hidden');

    // Solo el riesgo máximo exige reconocimiento expreso; nunca bloquea.
    ackWrap.classList.toggle('hidden', sel.value !== 'identica_activa');
}

function getHomonimiaData() {
    const sel = document.querySelector('input[name="homonimia"]:checked');
    if (!sel) return null;
    return {
        resultado: sel.value,
        nivel_riesgo: HOMONIMIA_RIESGO[sel.value].nivel,
        nombre_distintivo: nombreDistintivo(document.getElementById('nombre_sas').value),
        consulta_realizada: _distintivoConsultado !== null
                            && _distintivoConsultado === _distintivoDeclarado,
        riesgo_aceptado: !!document.getElementById('homonimia_ack')?.checked,
    };
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
    updateAccionesResumen();
}

function updateAccionesResumen() {
    const box = document.getElementById('acciones_resumen');
    if (!box) return;
    const autorizado = _parseCop(document.getElementById('capital_autorizado').value);
    const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
    const nominal = _parseCop(document.getElementById('valor_nominal').value);

    if (nominal < 1) {
        box.innerHTML = '<strong>El valor nominal por acción debe ser al menos $1.</strong>';
        return;
    }
    if (autorizado < suscrito) {
        box.innerHTML = '<strong>El capital autorizado no puede ser inferior al capital suscrito.</strong>';
        return;
    }
    if (autorizado % nominal !== 0 || suscrito % nominal !== 0) {
        box.innerHTML = '<strong>El capital autorizado y el suscrito deben ser múltiplos exactos de $'
            + nominal.toLocaleString('es-CO') + '.</strong>';
        return;
    }
    box.innerHTML = (autorizado / nominal).toLocaleString('es-CO') + ' acciones autorizadas &middot; '
        + (suscrito / nominal).toLocaleString('es-CO') + ' acciones suscritas &middot; valor nominal $'
        + nominal.toLocaleString('es-CO') + ' c/u';
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
    // Si un accionista tiene el campo vacío, se asume que NO ha pagado (0).
    // Si NINGÚN accionista llenó el campo, se deja vacío → backend usa suscrito.
    const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
    const pagadoDisplay = document.getElementById('capital_pagado');
    if (!pagadoDisplay) return;
    const accionistas = getAccionistasData();
    if (accionistas.length === 0) return;

    let total = 0;
    let hayAlgunPorcentaje = false;
    let hayAlgunCapPagado = false;
    for (const acc of accionistas) {
        const pct = acc.porcentaje || 0;
        if (pct <= 0) continue;
        hayAlgunPorcentaje = true;
        const suscAcc = Math.round(suscrito * pct / 100);
        // Detectar si el accionista llenó el campo (incluye "0" explícito)
        if (acc.capital_pagado !== '') hayAlgunCapPagado = true;
        const pagAcc = (acc.capital_pagado !== '' && _parseCop(acc.capital_pagado) >= 0)
            ? Math.min(_parseCop(acc.capital_pagado), suscAcc)
            : 0;
        total += pagAcc;
    }
    if (hayAlgunPorcentaje) {
        if (hayAlgunCapPagado) {
            // Al menos un accionista especificó capital pagado → mostrar total exacto
            pagadoDisplay.value = total.toLocaleString('es-CO');
        } else {
            // Nadie llenó el campo → dejar vacío (backend usará suscrito como default)
            pagadoDisplay.value = '';
        }
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
    const fields = document.getElementById('junta-fields');
    fields.classList.toggle('hidden', !val);
    if (val && document.getElementById('junta-principales-container').children.length === 0) {
        renderJuntaPrincipales();
    }
}

// ═══════════════════════════════════════════════════════════
// JUNTA DIRECTIVA
// ═══════════════════════════════════════════════════════════

const TIPO_DOC_OPTIONS = `
    <option value="CC">Cédula de ciudadanía</option>
    <option value="CE">Cédula de extranjería</option>
    <option value="Pasaporte">Pasaporte</option>
    <option value="NIT">NIT</option>`;

function _juntaPersonaCard(prefix, idx, titulo, removable) {
    const id = prefix + idx;
    return `
        <div class="accionista-card" data-junta-row>
            <div class="card-header">
                <h4>${titulo}</h4>
                ${removable ? `<button type="button" class="btn btn-danger" onclick="this.closest('[data-junta-row]').remove()">Eliminar</button>` : ''}
            </div>
            <div class="upload-doc-section">
                <div class="upload-doc-info">
                    <strong>📷 Autocompletar desde cédula o pasaporte</strong>
                    <span class="upload-hint">Suba el documento del miembro y Sí S.A.S. completa nombre, tipo y número.</span>
                </div>
                <label class="upload-doc-btn">
                    Cargar documento
                    <input type="file" accept="image/*,application/pdf"
                           onchange="extractFromCedula(this, '${id}', 0)">
                </label>
                <span class="upload-status" id="${id}_upload_status"></span>
            </div>
            <div class="form-group">
                <label>Seleccionar de accionistas</label>
                <select data-junta-select onchange="selectJuntaAccionista(this, '${id}')">
                    <option value="">-- Escribir manualmente --</option>
                </select>
                <span class="hint">Si el miembro ya figura como accionista, escójalo y se llenan sus datos.</span>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Nombre completo</label>
                    <input type="text" name="${id}_nombre" placeholder="Nombres y apellidos">
                </div>
                <div class="form-group">
                    <label>Tipo de identificación</label>
                    <select name="${id}_tipo_doc">${TIPO_DOC_OPTIONS}</select>
                </div>
                <div class="form-group">
                    <label>Número de identificación</label>
                    <input type="text" name="${id}_id_num" placeholder="No. de identificación">
                </div>
            </div>
        </div>`;
}

/** Llena los selectores de accionistas de todas las tarjetas de junta. */
function populateJuntaSelects() {
    const accionistas = getAccionistasData();
    document.querySelectorAll('[data-junta-select]').forEach(sel => {
        const previo = sel.value;
        sel.innerHTML = '<option value="">-- Escribir manualmente --</option>';
        accionistas.forEach((acc, i) => {
            const opt = document.createElement('option');
            opt.value = i;
            // Una persona jurídica no puede ser miembro de junta directiva.
            opt.textContent = acc.tipo === 'juridica'
                ? `${acc.rl_nombre || acc.nombre} (RL de ${acc.nombre})`
                : acc.nombre;
            sel.appendChild(opt);
        });
        sel.value = previo;
    });
}

function selectJuntaAccionista(sel, id) {
    const idx = parseInt(sel.value);
    if (isNaN(idx)) return;
    const acc = getAccionistasData()[idx];
    if (!acc) return;
    // De una persona jurídica se toma su representante legal, que es quien
    // puede ocupar la silla en la junta.
    const esPJ = acc.tipo === 'juridica';
    _setByName(`${id}_nombre`, esPJ ? acc.rl_nombre : acc.nombre);
    _setByName(`${id}_id_num`, esPJ ? acc.rl_cc : acc.id_num);
    const tipoSel = document.querySelector(`[name="${id}_tipo_doc"]`);
    if (tipoSel) tipoSel.value = esPJ ? 'CC' : (acc.tipo_doc || 'CC');
}

function renderJuntaPrincipales() {
    const n = parseInt(document.getElementById('junta_num_principales').value) || 1;
    const container = document.getElementById('junta-principales-container');
    // Se conservan los valores ya digitados al cambiar el número de miembros.
    const previos = getJuntaPersonas('junta-principales-container', true);
    let html = '';
    for (let i = 1; i <= n; i++) {
        html += _juntaPersonaCard('jd_pri_', i, `Miembro principal ${i}`, false);
    }
    container.innerHTML = html;
    previos.slice(0, n).forEach((p, i) => {
        const idx = i + 1;
        _setByName(`jd_pri_${idx}_nombre`, p.nombre);
        _setByName(`jd_pri_${idx}_tipo_doc`, p.tipo_doc);
        _setByName(`jd_pri_${idx}_id_num`, p.id_num);
    });
    populateJuntaSelects();
}

let juntaSuplenteCount = 0;
function addJuntaSuplente() {
    juntaSuplenteCount++;
    const container = document.getElementById('junta-suplentes-container');
    const div = document.createElement('div');
    div.innerHTML = _juntaPersonaCard('jd_sup_', juntaSuplenteCount,
        `Miembro suplente ${container.children.length + 1}`, true);
    container.appendChild(div.firstElementChild);
    populateJuntaSelects();
}

function _setByName(name, value) {
    const el = document.querySelector(`[name="${name}"]`);
    if (el && value) el.value = value;
}

function getJuntaPersonas(containerId, incluirVacios) {
    const personas = [];
    document.querySelectorAll(`#${containerId} [data-junta-row]`).forEach(row => {
        const nombre = (row.querySelector('[name$="_nombre"]')?.value || '').trim();
        const idNum = (row.querySelector('[name$="_id_num"]')?.value || '').trim();
        const tipoDoc = row.querySelector('[name$="_tipo_doc"]')?.value || 'CC';
        if (incluirVacios || (nombre && idNum)) {
            personas.push({ nombre: nombre, tipo_doc: tipoDoc, id_num: idNum });
        }
    });
    return personas;
}

function getJuntaData() {
    if (document.querySelector('input[name="junta"]:checked')?.value !== 'si') return null;
    const principales = getJuntaPersonas('junta-principales-container');
    if (principales.length === 0) return null;
    return {
        principales: principales,
        suplentes: getJuntaPersonas('junta-suplentes-container'),
    };
}

// ═══════════════════════════════════════════════════════════
// REVISOR FISCAL
// ═══════════════════════════════════════════════════════════

function toggleRevisor(val) {
    document.querySelectorAll('input[name="revisor"]').forEach(r => {
        r.closest('.radio-card').classList.toggle('selected', r.checked);
    });
    document.getElementById('revisor-fields').classList.toggle('hidden', !val);
}

function toggleRevisorTipo(tipo) {
    document.getElementById('revisor_natural_fields').classList.toggle('hidden', tipo !== 'natural');
    document.getElementById('revisor_juridica_fields').classList.toggle('hidden', tipo !== 'juridica');
}

function getRevisorData() {
    if (document.querySelector('input[name="revisor"]:checked')?.value !== 'si') return null;
    const tipo = document.querySelector('input[name="revisor_tipo"]:checked')?.value || 'natural';
    const v = id => (document.getElementById(id)?.value || '').trim();

    if (tipo === 'juridica') {
        const d = {
            tipo: 'juridica',
            nombre: v('revisor_pj_nombre'),
            id_num: v('revisor_pj_nit'),
            contador_nombre: v('revisor_contador_nombre'),
            contador_tipo_doc: document.getElementById('revisor_contador_tipo_doc')?.value || 'CC',
            contador_id_num: v('revisor_contador_id_num'),
            contador_tarjeta_profesional: v('revisor_contador_tarjeta'),
        };
        // Una persona jurídica sin contador designado no puede ejercer el cargo.
        if (!d.nombre || !d.id_num || !d.contador_nombre || !d.contador_id_num
            || !d.contador_tarjeta_profesional) return null;
        return d;
    }

    const d = {
        tipo: 'natural',
        nombre: v('revisor_nombre'),
        tipo_doc: document.getElementById('revisor_tipo_doc')?.value || 'CC',
        id_num: v('revisor_id_num'),
        tarjeta_profesional: v('revisor_tarjeta'),
    };
    if (!d.nombre || !d.id_num || !d.tarjeta_profesional) return null;
    return d;
}

// ═══════════════════════════════════════════════════════════
// SITUACIÓN DE CONTROL
// ═══════════════════════════════════════════════════════════

function getControlante() {
    const accionistas = getAccionistasData();
    if (accionistas.length === 0) return null;
    if (accionistas.length === 1) return accionistas[0];
    return accionistas.find(a => a.porcentaje > 50) || null;
}

function refreshControlBlock() {
    const block = document.getElementById('control-block');
    const ctx = document.getElementById('control-context');
    const controlante = getControlante();
    if (!controlante) {
        block.classList.add('hidden');
        return;
    }
    const accionistas = getAccionistasData();
    ctx.innerHTML = accionistas.length === 1
        ? `La sociedad se constituye con un único accionista (<strong>${controlante.nombre}</strong>),
           lo que configura una situación de control.`
        : `<strong>${controlante.nombre}</strong> es titular del ${controlante.porcentaje}% del capital,
           lo que configura una situación de control.`;
    block.classList.remove('hidden');
}

// ═══════════════════════════════════════════════════════════
// EMPRESA FAMILIAR (Ley 2495 de 2025)
// ═══════════════════════════════════════════════════════════

function toggleEmpresaFamiliar(val) {
    document.querySelectorAll('input[name="empresa_familiar"]').forEach(r => {
        r.closest('.radio-card').classList.toggle('selected', r.checked);
    });
    document.getElementById('familiar-fields').classList.toggle('hidden', !val);
    if (val) renderNucleoFamiliar();
}

function _accionesDeAccionista(acc) {
    const suscrito = _parseCop(document.getElementById('capital_suscrito').value);
    const nominal = Math.max(1, _parseCop(document.getElementById('valor_nominal').value));
    return Math.floor(Math.round(suscrito * (acc.porcentaje || 0) / 100) / nominal);
}

function renderNucleoFamiliar() {
    const container = document.getElementById('familiar-container');
    if (!container) return;
    const accionistas = getAccionistasData();
    // Se conservan las marcas y parentescos ya digitados al re-renderizar.
    const previos = {};
    container.querySelectorAll('[data-fam-row]').forEach(row => {
        previos[row.dataset.famRow] = {
            checked: row.querySelector('[data-fam-check]').checked,
            parentesco: row.querySelector('[data-fam-parentesco]').value,
        };
    });

    if (accionistas.length === 0) {
        container.innerHTML = '<p class="hint">Agregue accionistas en el Paso 2 para poder conformar el núcleo familiar.</p>';
        return;
    }

    container.innerHTML = accionistas.map((acc, i) => {
        const prev = previos[i] || {};
        const id = acc.tipo === 'juridica' ? `NIT ${acc.id_num}` : `${acc.id_tipo} ${acc.id_num}`;
        return `
        <div class="accionista-card" data-fam-row="${i}">
            <div class="form-row" style="align-items:center">
                <div class="form-group" style="flex:0 0 auto">
                    <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer">
                        <input type="checkbox" data-fam-check ${prev.checked ? 'checked' : ''}
                               onchange="updateFamiliarBar()">
                        <span>Integra el núcleo familiar</span>
                    </label>
                </div>
                <div class="form-group">
                    <label>Accionista</label>
                    <input type="text" value="${acc.nombre} — ${id} (${acc.porcentaje}%)" disabled class="input-disabled">
                </div>
                <div class="form-group">
                    <label>Parentesco</label>
                    <input type="text" data-fam-parentesco value="${prev.parentesco || ''}"
                           placeholder="Ej: Padre, Hija, Cónyuge, Hermano">
                </div>
            </div>
        </div>`;
    }).join('');
    updateFamiliarBar();
}

function _pctNucleoFamiliar() {
    const accionistas = getAccionistasData();
    let pct = 0;
    document.querySelectorAll('#familiar-container [data-fam-row]').forEach(row => {
        if (row.querySelector('[data-fam-check]').checked) {
            const acc = accionistas[parseInt(row.dataset.famRow)];
            if (acc) pct += acc.porcentaje || 0;
        }
    });
    return pct;
}

function updateFamiliarBar() {
    const pct = _pctNucleoFamiliar();
    const fill = document.getElementById('familiar-bar-fill');
    const label = document.getElementById('familiar-bar-label');
    if (!fill || !label) return;
    fill.style.width = Math.min(100, pct) + '%';
    // Debe superar la mitad del capital para acceder a los beneficios de la ley.
    fill.style.background = pct > 50 ? 'var(--success, #2e7d32)' : 'var(--danger, #c62828)';
    label.textContent = pct.toFixed(2).replace(/\.00$/, '') + '% del capital';
}

function getNucleoFamiliarData() {
    const accionistas = getAccionistasData();
    const miembros = [];
    document.querySelectorAll('#familiar-container [data-fam-row]').forEach(row => {
        if (!row.querySelector('[data-fam-check]').checked) return;
        const acc = accionistas[parseInt(row.dataset.famRow)];
        if (!acc) return;
        miembros.push({
            tipo_doc: acc.tipo === 'juridica' ? 'NIT' : (acc.id_tipo || 'C.C.'),
            id_num: acc.id_num,
            nombre: acc.nombre,
            acciones: _accionesDeAccionista(acc).toLocaleString('es-CO'),
            parentesco: (row.querySelector('[data-fam-parentesco]').value || '').trim(),
        });
    });
    return miembros;
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
        // Una cámara cubre varios municipios (ej. Aburrá Sur), por eso no se
        // deriva del municipio: el usuario la elige.
        camara_ciudad: document.getElementById('camara_ciudad').value.trim(),
        homonimia: getHomonimiaData(),
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
        capital_autorizado: document.getElementById('capital_autorizado').value,
        valor_nominal: document.getElementById('valor_nominal').value,
        capital_suscrito: document.getElementById('capital_suscrito').value,
        // capital_pagado total se calcula en el backend a partir de los
        // pagados individuales de cada accionista. Se envía para display/fallback.
        capital_pagado: document.getElementById('capital_pagado').value,
        regimen: document.getElementById('regimen').value,
        ingresos_mensuales: document.getElementById('ingresos_mensuales').value,
        tiene_junta: document.querySelector('input[name="junta"]:checked')?.value === 'si',
        tiene_revisor: document.querySelector('input[name="revisor"]:checked')?.value === 'si',
        junta_directiva: getJuntaData(),
        revisor_fiscal: getRevisorData(),
        es_emprendimiento_social: document.querySelector('input[name="emprendimiento"]:checked')?.value === 'si',
        grupo_etnico: document.getElementById('grupo_etnico')?.value || '',
        // Solo se pregunta cuando existe controlante; si no, se deja en true
        // para no alterar el comportamiento histórico.
        declara_control: document.querySelector('input[name="declara_control"]:checked')?.value !== 'no',
        es_empresa_familiar: document.querySelector('input[name="empresa_familiar"]:checked')?.value === 'si',
        nucleo_familiar: getNucleoFamiliarData(),
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
    if (d.homonimia) {
        const r = HOMONIMIA_RIESGO[d.homonimia.resultado];
        h += f('Homonimia (RUES)',
               `<span style="color:${r.color};font-weight:600">Riesgo ${d.homonimia.nivel_riesgo}</span>`
               + ` — se consultó "${d.homonimia.nombre_distintivo}"`
               + (d.homonimia.riesgo_aceptado ? ' · riesgo aceptado por el usuario' : ''));
    }
    h += f('Dirección', d.direccion);
    h += f('Municipio', `${d.municipio}, ${d.departamento}`);
    h += f('Cámara de Comercio', d.camara_ciudad ? `Cámara de Comercio de ${d.camara_ciudad}` : '—');
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
    const _nominal = Math.max(1, _parseCop(d.valor_nominal));
    h += f('Capital Autorizado', '$' + d.capital_autorizado
           + ' (' + (_parseCop(d.capital_autorizado) / _nominal).toLocaleString('es-CO') + ' acciones)');
    h += f('Capital Suscrito', '$' + d.capital_suscrito
           + ' (' + (_parseCop(d.capital_suscrito) / _nominal).toLocaleString('es-CO') + ' acciones)');
    h += f('Capital Pagado', '$' + d.capital_pagado);
    h += f('Valor nominal por acción', '$' + _nominal.toLocaleString('es-CO'));
    h += f('Régimen', d.regimen === 'simple' ? 'Simple (SIMPLE)' : 'Ordinario');

    if (d.junta_directiva) {
        h += '<h3>Junta Directiva</h3>';
        d.junta_directiva.principales.forEach((m, i) => {
            h += f(`Principal ${i + 1}`, `${m.nombre} (${m.tipo_doc} ${m.id_num})`);
        });
        d.junta_directiva.suplentes.forEach((m, i) => {
            h += f(`Suplente ${i + 1}`, `${m.nombre} (${m.tipo_doc} ${m.id_num})`);
        });
    }

    if (d.revisor_fiscal) {
        h += '<h3>Revisor Fiscal</h3>';
        if (d.revisor_fiscal.tipo === 'juridica') {
            h += f('Firma', `${d.revisor_fiscal.nombre} (NIT ${d.revisor_fiscal.id_num})`);
            h += f('Contador designado',
                   `${d.revisor_fiscal.contador_nombre} (${d.revisor_fiscal.contador_tipo_doc} `
                   + `${d.revisor_fiscal.contador_id_num}) — T.P. ${d.revisor_fiscal.contador_tarjeta_profesional}`);
        } else {
            h += f('Nombre', `${d.revisor_fiscal.nombre} (${d.revisor_fiscal.tipo_doc} ${d.revisor_fiscal.id_num})`);
            h += f('Tarjeta profesional', d.revisor_fiscal.tarjeta_profesional);
        }
    }

    h += '<h3>Documentos a Generar</h3><div class="docs-list">';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Estatutos</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formulario RUES</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formulario Otras Entidades</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Anexo Responsabilidades Tributarias</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Manifestación Emprendimientos Sociales</div>';
    h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Grupo Étnico</div>';

    // Situación de control: accionista único o titular de más del 50%.
    // Si existe controlante pero el usuario decide no declararla, en su lugar
    // se emite la carta explicativa a la Cámara de Comercio.
    const hasControl = !!getControlante();
    if (!hasControl) {
        h += '<div class="doc-item doc-conditional">— Situación de Control (no aplica)</div>';
    } else if (d.declara_control) {
        h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Situación de Control</div>';
    } else {
        h += '<div class="doc-item"><span class="doc-check">&#10003;</span> Carta de no declaración de situación de control</div>';
    }

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

    // Empresa familiar (Ley 2495 de 2025)
    h += (d.es_empresa_familiar && d.nucleo_familiar.length)
        ? '<div class="doc-item"><span class="doc-check">&#10003;</span> Formato Empresa Familiar (Ley 2495 de 2025)</div>'
        : '<div class="doc-item doc-conditional">— Empresa Familiar (no aplica)</div>';

    h += '</div>';

    if (d.es_empresa_familiar && d.nucleo_familiar.length) {
        h += '<h3>Núcleo Familiar</h3>';
        d.nucleo_familiar.forEach(m => {
            h += f(m.parentesco || '—', `${m.nombre} (${m.tipo_doc} ${m.id_num}) — ${m.acciones} acciones`);
        });
    }

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
