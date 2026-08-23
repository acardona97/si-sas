# -*- coding: utf-8 -*-
"""
Sí S.A.S. — Company Maker
Flask backend para generar el paquete completo de constitución S.A.S.

Quarta Acompañamiento Legal S.A.S. — Medellín, Colombia.
"""
import os
import json
import zipfile
import tempfile
import re
import uuid
import functools
from datetime import date, datetime
from dotenv import load_dotenv
from flask import (
    Flask, request, jsonify, send_file, render_template,
    session, redirect, url_for, flash, get_flashed_messages
)

# Cargar variables de entorno desde .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from auth import (
    init_db, seed_admin, seed_staff_user, get_user_by_id, verify_password,
    create_user, get_all_users, update_user_plan, set_user_active,
    check_puede_generar, decrement_generacion, set_generaciones, PLAN_LABELS
)
from processors.ciiu_reglas import (
    evaluar as evaluar_ciiu,
    resumen_para_listado,
    validar_seleccion as validar_ciiu,
    version_matriz as version_matriz_ciiu,
)
from processors.responsabilidades import (
    construir as construir_resps,
    disponibles as resps_disponibles,
    no_seleccionables as resps_no_seleccionables,
    exige_comercio_exterior,
    casillas_rues_comercio_exterior,
    config_comercio_exterior,
)
from processors.objeto_social import generar_objeto_social
from processors.estatutos import generar_estatutos
from processors.pdf_filler import (
    generar_emprendimientos,
    generar_situacion_control,
    generar_ley_1780,
    generar_responsabilidades,
    generar_grupo_etnico,
    generar_rues,
    generar_otras_entidades,
    generar_empresa_familiar,
    generar_carta_no_control,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quarta-si-sas-dev-secret-2026")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)  # si_sas_proyecto/
PLANTILLAS_DIR = os.path.join(PROJECT_DIR, "plantillas")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
# Datos estáticos dentro de src/ — no se ven afectados por el Volume de Railway
STATIC_DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
# Actos administrativos que habilitan una actividad restringida. Se adjuntan
# al paquete generado.
AUTORIZACIONES_DIR = os.path.join(OUTPUT_DIR, "_autorizaciones")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════

CAPITAL_AUTORIZADO = 1_000_000_000
VALOR_NOMINAL_ACCION = 1

CIIU_CONSUMO = [
    "5611", "5612", "5613", "5619", "5621", "5629", "5630",
    "6120", "6110", "9200", "0128",
]


# ═══════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════

def parse_date(s):
    if isinstance(s, date):
        return s
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_money(s):
    if isinstance(s, (int, float)):
        return int(s)
    try:
        return int(str(s).replace(".", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def determinar_incluir_consumo(ciiu_codes, objeto_social=""):
    codigos = ciiu_codes if isinstance(ciiu_codes, list) else [ciiu_codes]
    for ciiu in codigos:
        if str(ciiu)[:4] in CIIU_CONSUMO:
            return True
    keywords = ["restaurante", "bar ", "café", "expendio de bebida",
                "telefonía móvil", "internet", "cannabis"]
    obj_lower = objeto_social.lower()
    return any(kw in obj_lower for kw in keywords)


def construir_responsabilidades(regimen, incluir_consumo, adicionales=None,
                                ciiu_codes=None, objeto_social=""):
    """Anexo de responsabilidades: las del régimen más las que marcó el usuario."""
    return construir_resps(regimen, incluir_consumo, adicionales,
                           ciiu_codes, objeto_social)


def determinar_ley_1780(accionistas):
    hoy = date.today()
    pct_jovenes = 0.0
    for acc in accionistas:
        if acc.get("tipo") != "natural":
            continue
        nac = acc.get("nacimiento") or acc.get("fecha_nacimiento")
        if not nac:
            continue
        try:
            nac = parse_date(nac) if isinstance(nac, str) else nac
            edad = (hoy - nac).days / 365.25
            if edad <= 35:
                pct_jovenes += float(acc.get("porcentaje", 0))
        except Exception:
            continue
    return pct_jovenes > 50


def determinar_situacion_control(accionistas):
    """Devuelve el accionista controlante, o None si no hay ninguno.

    Es controlante quien supere el 50% del capital y, en todo caso, el
    accionista único (que controla por definición aunque el porcentaje
    venga mal diligenciado).
    """
    if len(accionistas) == 1:
        return accionistas[0]
    for acc in accionistas:
        if float(acc.get("porcentaje", 0)) > 50:
            return acc
    return None


# ═══════════════════════════════════════════════════════════
# INICIALIZACIÓN DB + ADMIN
# ═══════════════════════════════════════════════════════════

def _sembrar(descripcion, email, password, sembrador, *args):
    """Siembra una cuenta interna y avisa cuando no puede hacerlo.

    Los sembradores no hacen nada si falta la contraseña. Sin este aviso el
    arranque no deja rastro alguno: la cuenta simplemente no queda creada y
    el problema aparece mucho después, cuando esa persona intenta generar y
    recibe "Sin generaciones disponibles" sin explicación.
    """
    if not email or not password:
        app.logger.warning(
            "Cuenta %s (%s) NO sembrada: falta su contraseña en las variables "
            "de entorno. No tendrá plan admin ni generaciones ilimitadas; "
            "habrá que asignárselas desde /admin.",
            descripcion, email or "correo sin definir",
        )
        return
    sembrador(email, password, *args)


with app.app_context():
    init_db()
    _sembrar(
        "administrador",
        os.environ.get("ADMIN_EMAIL", ""),
        os.environ.get("ADMIN_PASSWORD", ""),
        seed_admin,
    )
    _sembrar(
        "staff 1",
        os.environ.get("STAFF_EMAIL_1", "acardona@quarta.co"),
        os.environ.get("STAFF_PASSWORD_1", ""),
        seed_staff_user,
        "Andrés Cardona",
    )
    _sembrar(
        "staff 2",
        os.environ.get("STAFF_EMAIL_2", "info.2@quarta.co"),
        os.environ.get("STAFF_PASSWORD_2", ""),
        seed_staff_user,
        "Quarta Info",
    )


# ═══════════════════════════════════════════════════════════
# DECORADORES AUTH
# ═══════════════════════════════════════════════════════════

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Sesión requerida. Por favor inicie sesión."}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if session.get("plan") != "admin":
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════
# RUTAS PÚBLICAS
# ═══════════════════════════════════════════════════════════

@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("app_main"))
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("app_main"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = verify_password(email, password)
        if user:
            session["user_id"]     = user["id"]
            session["user_email"]  = user["email"]
            session["user_nombre"] = user["nombre"]
            session["plan"]        = user["plan"]
            return redirect(url_for("app_main"))
        error = "Correo o contraseña incorrectos."
    return render_template("auth.html", mode="login", error=error)


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("app_main"))
    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        nombre   = request.form.get("nombre", "").strip()
        if not email or not password:
            error = "Correo y contraseña son obligatorios."
        elif len(password) < 8:
            error = "La contraseña debe tener mínimo 8 caracteres."
        elif password != confirm:
            error = "Las contraseñas no coinciden."
        else:
            user = create_user(email, password, nombre)
            if user:
                session["user_id"]     = user["id"]
                session["user_email"]  = user["email"]
                session["user_nombre"] = user["nombre"]
                session["plan"]        = user["plan"]
                return redirect(url_for("app_main"))
            error = "Ese correo ya está registrado."
    return render_template("auth.html", mode="register", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ═══════════════════════════════════════════════════════════
# RUTAS PROTEGIDAS
# ═══════════════════════════════════════════════════════════

@app.route("/app")
@login_required
def app_main():
    user = get_user_by_id(session["user_id"])
    return render_template("index.html", user=user)


# ═══════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════

@app.route("/admin")
@admin_required
def admin_panel():
    users = get_all_users()
    return render_template("admin.html", users=users, plan_labels=PLAN_LABELS)


@app.route("/admin/update-plan", methods=["POST"])
@admin_required
def admin_update_plan():
    user_id = request.form.get("user_id")
    plan    = request.form.get("plan")
    if user_id and plan in PLAN_LABELS:
        update_user_plan(user_id, plan)
    return redirect(url_for("admin_panel"))


@app.route("/admin/toggle-active", methods=["POST"])
@admin_required
def admin_toggle_active():
    user_id = request.form.get("user_id")
    active  = request.form.get("active")
    if user_id:
        set_user_active(user_id, 0 if active == "1" else 1)
    return redirect(url_for("admin_panel"))


@app.route("/admin/set-generaciones", methods=["POST"])
@admin_required
def admin_set_generaciones():
    user_id = request.form.get("user_id")
    valor   = request.form.get("generaciones", "").strip()
    if user_id:
        n = None if valor == "" else int(valor)
        set_generaciones(user_id, n)
        flash(f"Generaciones actualizadas.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/add-user", methods=["POST"])
@admin_required
def admin_add_user():
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    nombre   = request.form.get("nombre", "").strip()
    plan     = request.form.get("plan", "basic")

    if not email or not password:
        flash("Correo y contraseña son obligatorios.", "error")
    elif len(password) < 8:
        flash("La contraseña debe tener mínimo 8 caracteres.", "error")
    elif plan not in PLAN_LABELS:
        flash("Plan inválido.", "error")
    else:
        user = create_user(email, password, nombre, plan)
        if user:
            flash(f"Usuario {email} creado exitosamente.", "success")
        else:
            flash(f"El correo {email} ya está registrado.", "error")

    return redirect(url_for("admin_panel"))


@app.route("/api/ciiu/search")
def ciiu_search():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])

    results = []
    ciiu_path = os.path.join(STATIC_DATA_DIR, "listado_ciiu.json")
    try:
        with open(ciiu_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        codigos = data.get("codigos", {})
        for code, desc in codigos.items():
            if q in code.lower() or q in desc.lower():
                # Los códigos restringidos siguen apareciendo en la lista: se
                # marcan, no se ocultan. La restricción se explica al elegirlos.
                item = {"code": code, "description": desc}
                marca = resumen_para_listado(code)
                if marca:
                    item["restriccion"] = marca
                results.append(item)
                if len(results) >= 20:
                    break
    except Exception:
        pass
    return jsonify(results)


@app.route("/api/responsabilidades")
@login_required
def api_responsabilidades():
    """
    Responsabilidades tributarias según el régimen elegido.

    Devuelve las que van por defecto (no se pueden quitar), las que el
    usuario puede agregar y las que nunca se ofrecen, con el motivo.
    """
    from processors.responsabilidades import (
        predeterminadas, cupo_adicionales, maximo_anexo,
    )
    regimen = request.args.get("regimen", "ordinario")
    incluir_consumo = request.args.get("consumo") == "1"
    objeto_social = request.args.get("objeto_social", "")
    ciiu_codes = [c for c in request.args.getlist("ciiu") if c]
    # Las ya marcadas importan: la 53 reemplaza a la 48, así que cambian
    # tanto las predeterminadas como el cupo disponible.
    marcadas = [c for c in request.args.getlist("marcada") if c]

    return jsonify({
        "predeterminadas": [
            {"codigo": c, "nombre": n}
            for c, n in predeterminadas(regimen, incluir_consumo, marcadas)
        ],
        "adicionales": resps_disponibles(regimen, incluir_consumo, ciiu_codes,
                                         objeto_social, marcadas),
        "no_seleccionables": resps_no_seleccionables(),
        # El anexo impreso tiene un número fijo de filas
        "maximo_anexo": maximo_anexo(),
        "cupo_adicionales": cupo_adicionales(regimen, incluir_consumo, marcadas),
        "comercio_exterior": config_comercio_exterior(),
    })


@app.route("/api/ciiu/regla/<codigo>")
@login_required
def ciiu_regla(codigo):
    """Evalúa un código con lo que el usuario lleva declarado hasta ahora."""
    respuestas = {}
    for clave, valor in request.args.items():
        if clave.startswith("r_"):
            respuestas[clave[2:]] = valor
    objeto_social = request.args.get("objeto_social", "")
    resultado = evaluar_ciiu(codigo, respuestas, objeto_social)
    resultado["matriz"] = version_matriz_ciiu()
    return jsonify(resultado)


@app.route("/api/ciiu/autorizacion", methods=["POST"])
@login_required
def ciiu_autorizacion():
    """
    Recibe el acto administrativo que habilita una actividad.

    Solo tiene sentido cuando la S.A.S. es jurídicamente compatible con el
    código: si la actividad exige otro vehículo, el bloqueo no se subsana
    adjuntando nada y aquí se rechaza.
    """
    codigo = (request.form.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"error": "Falta el código CIIU"}), 400
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No se recibió archivo"}), 400

    respuestas = {}
    for clave, valor in request.form.items():
        if clave.startswith("r_"):
            respuestas[clave[2:]] = valor

    evaluacion = evaluar_ciiu(codigo, respuestas, request.form.get("objeto_social", ""))
    if evaluacion["bloquea"] or not evaluacion.get("requiere_autorizacion"):
        return jsonify({
            "error": "Esta actividad no se habilita adjuntando un documento. "
                     + (evaluacion.get("mensaje") or "")
        }), 400

    archivo = request.files["file"]
    datos = archivo.read()
    if len(datos) > 15 * 1024 * 1024:
        return jsonify({"error": "Archivo muy grande (máx 15MB)"}), 400

    os.makedirs(AUTORIZACIONES_DIR, exist_ok=True)
    nombre_seguro = re.sub(r"[^\w.\-]", "_", archivo.filename)[-80:]
    documento_id = f"{uuid.uuid4().hex}_{nombre_seguro}"
    with open(os.path.join(AUTORIZACIONES_DIR, documento_id), "wb") as f:
        f.write(datos)

    return jsonify({
        "documento_id": documento_id,
        "nombre": archivo.filename,
        "codigo": codigo,
        "autoridad": evaluacion.get("autoridad"),
    })


@app.route("/api/generate", methods=["POST"])
@login_required
def generate():
    """Genera el paquete completo de constitución S.A.S."""
    if not check_puede_generar(session["user_id"]):
        return jsonify({
            "error": "Sin generaciones disponibles. Adquiera un plan para generar sus documentos."
        }), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    tmp_dir = tempfile.mkdtemp(prefix="si_sas_")
    errors = []

    try:
        # ─── EXTRAER Y NORMALIZAR ───
        nombre_sas = data["nombre_sas"].upper().strip()
        if not nombre_sas.endswith("S.A.S."):
            # Se admiten las variantes de escritura del indicativo y se llevan
            # todas a la forma canónica "S.A.S.".
            nombre_sas = re.sub(
                r"\s*(SOCIEDAD\s+POR\s+ACCIONES\s+SIMPLIFICADA|SAS|S\s*A\s*S|S\.A\.S)"
                r"\s*\.?\s*$",
                " S.A.S.", nombre_sas
            ).strip()

        # El indicativo del tipo societario es obligatorio y va al final
        # (artículo 5 de la Ley 1258 de 2008). El cuestionario ya lo exige;
        # esto cubre el caso de que se llame al endpoint por fuera.
        if not nombre_sas.endswith("S.A.S."):
            return jsonify({
                "error": 'La razón social debe terminar en "S.A.S." '
                         "(artículo 5 de la Ley 1258 de 2008)."
            }), 400
        if not nombre_sas[:-len("S.A.S.")].strip(" .,-"):
            return jsonify({
                "error": 'La razón social no puede ser solo el indicativo "S.A.S.": '
                         "falta el nombre que identifica a la sociedad."
            }), 400

        fecha = date.today()
        municipio = data.get("municipio", "Medellín")
        departamento = data.get("departamento", "Antioquia")
        direccion = data.get("direccion", "")
        barrio = data.get("barrio", "")
        email = data.get("email", "")
        telefono1 = data.get("telefono1", "")
        telefono2 = data.get("telefono2", "")
        telefono3 = data.get("telefono3", "")
        zona = data.get("zona", "urbana")
        tipo_local = data.get("tipo_local", "oficina")
        tenencia = data.get("tenencia", "arriendo")

        accionistas = data.get("accionistas", [])
        # Puede haber varios representantes legales; el primero de cada lista
        # es el que figura en los formularios y firma ante las entidades.
        _principales = [r for r in (data.get("rl_principales") or []) if r and r.get("nombre")]
        _suplentes = [r for r in (data.get("rl_suplentes") or []) if r and r.get("nombre")]
        rl_principal = _principales[0] if _principales else data.get("rl_principal", {})
        rl_suplente = _suplentes[0] if _suplentes else data.get("rl_suplente", None)

        objeto_social = data.get("objeto_social", "")
        ciiu_code = data.get("ciiu_code", "")
        ciiu_desc = data.get("ciiu_description", "")
        ciiu_code_sec = data.get("ciiu_code_sec", "")
        ciiu_desc_sec = data.get("ciiu_description_sec", "")

        regimen = data.get("regimen", "ordinario")
        capital_suscrito = parse_money(data.get("capital_suscrito", 1_000_000))

        # ─── Capital autorizado y valor nominal por acción ───
        # Ambos son editables desde el cuestionario; si vienen vacíos o
        # inválidos se cae a los valores por defecto históricos.
        capital_autorizado = parse_money(
            data.get("capital_autorizado") or CAPITAL_AUTORIZADO
        ) or CAPITAL_AUTORIZADO
        valor_nominal = parse_money(
            data.get("valor_nominal") or VALOR_NOMINAL_ACCION
        ) or VALOR_NOMINAL_ACCION
        if capital_autorizado < capital_suscrito:
            return jsonify({
                "error": "El capital autorizado no puede ser inferior al capital suscrito."
            }), 400
        if capital_autorizado % valor_nominal or capital_suscrito % valor_nominal:
            return jsonify({
                "error": (
                    f"El capital autorizado y el suscrito deben ser múltiplos exactos "
                    f"del valor nominal por acción (${valor_nominal:,}).".replace(",", ".")
                )
            }), 400

        # ─── Capital pagado: dos modos posibles ───
        # MODO A: el usuario llenó el campo individual de al menos un accionista.
        #         → suma los individuales (vacío = 100% del suscrito de ese acc).
        # MODO B: ninguno llenó individual → usar el TOTAL global tecleado por el
        #         usuario y distribuir proporcionalmente al porcentaje accionario.
        # En ambos casos el total nunca puede superar el capital suscrito.

        any_individual = any(
            str(acc.get("capital_pagado", "")).strip() for acc in accionistas
        )

        if any_individual:
            # MODO A: suma de individuales. Vacío = 0 (no ha pagado).
            capital_pagado_total = 0
            for acc in accionistas:
                pct = float(acc.get("porcentaje", 0))
                susc_acc = int(capital_suscrito * pct / 100)
                cp_raw = str(acc.get("capital_pagado", "")).strip()
                cp_acc = min(parse_money(cp_raw), susc_acc) if cp_raw else 0
                acc["capital_pagado_num"] = cp_acc
                capital_pagado_total += cp_acc
            capital_pagado = capital_pagado_total  # se respeta aunque sea 0
        else:
            # MODO B: total global. Vacío → default suscrito; explícito → respetar.
            cp_raw_global = str(data.get("capital_pagado", "")).strip()
            if cp_raw_global:
                capital_pagado_global = min(parse_money(cp_raw_global), capital_suscrito)
            else:
                capital_pagado_global = capital_suscrito  # no ingresó nada → 100%
            acumulado = 0
            n = len(accionistas)
            for i, acc in enumerate(accionistas):
                pct = float(acc.get("porcentaje", 0))
                if i == n - 1:
                    cp_acc = capital_pagado_global - acumulado
                else:
                    cp_acc = int(capital_pagado_global * pct / 100)
                    acumulado += cp_acc
                acc["capital_pagado_num"] = max(0, cp_acc)
            capital_pagado = capital_pagado_global

        ingresos = data.get("ingresos_mensuales", "100.000")
        es_emprendimiento = data.get("es_emprendimiento_social", False)
        tiene_junta = data.get("tiene_junta", False)
        tiene_revisor = data.get("tiene_revisor", False)

        # ─── Junta directiva y revisor fiscal (nombramientos) ───
        junta_directiva = data.get("junta_directiva") if tiene_junta else None
        if junta_directiva and not junta_directiva.get("principales"):
            junta_directiva = None
        revisor_fiscal = data.get("revisor_fiscal") if tiene_revisor else None
        if revisor_fiscal and not revisor_fiscal.get("nombre"):
            revisor_fiscal = None

        # ─── Empresa familiar (Ley 2495 de 2025) ───
        es_empresa_familiar = data.get("es_empresa_familiar", False)
        nucleo_familiar = data.get("nucleo_familiar", []) if es_empresa_familiar else []
        camara_ciudad = data.get("camara_ciudad") or municipio

        # ─── Declaración de situación de control ───
        # Por defecto se declara (comportamiento histórico); el cuestionario
        # solo ofrece la opción cuando existe un accionista controlante.
        declara_control = data.get("declara_control", True)

        # Apoderado (opcional)
        apoderado_raw = data.get("apoderado", None)
        apoderado = None
        if apoderado_raw and apoderado_raw.get("nombre"):
            apoderado = {
                "nombre": apoderado_raw["nombre"].strip(),
                "id_tipo": apoderado_raw.get("id_tipo", "C.C."),
                "id_num": apoderado_raw.get("id_num", ""),
                "domicilio_ciudad": apoderado_raw.get("domicilio_ciudad", municipio),
                "domicilio_departamento": apoderado_raw.get("domicilio_departamento", departamento),
            }

        # Normalizar RL keys
        if "cedula" in rl_principal and "cc" not in rl_principal:
            rl_principal["cc"] = rl_principal["cedula"]
        if not rl_principal.get("expedicion"):
            rl_principal["expedicion"] = municipio
        if rl_suplente:
            if "cedula" in rl_suplente and "cc" not in rl_suplente:
                rl_suplente["cc"] = rl_suplente["cedula"]

        # ─── Revalidación regulatoria de los CIIU ───
        # El formulario ya la hizo, pero se puede saltar. Se vuelve a evaluar
        # aquí con el objeto social definitivo y antes de generar nada: una
        # aprobación anterior no vale si cambiaron el código, las respuestas o
        # el objeto social.
        ciiu_codes = [c for c in [ciiu_code, ciiu_code_sec] if c]
        ciiu_respuestas = data.get("ciiu_respuestas") or {}
        ciiu_autorizaciones = data.get("ciiu_autorizaciones") or {}
        ok_ciiu, errores_ciiu, detalle_ciiu = validar_ciiu(
            ciiu_codes, ciiu_respuestas, objeto_social, ciiu_autorizaciones
        )
        if not ok_ciiu:
            return jsonify({
                "error": "La actividad económica seleccionada no permite continuar:\n\n"
                         + "\n\n".join(errores_ciiu),
                "ciiu": detalle_ciiu,
            }), 400

        # Derivaciones automáticas
        incluir_consumo = determinar_incluir_consumo(ciiu_codes, objeto_social)
        responsabilidades, avisos_resp = construir_responsabilidades(
            regimen, incluir_consumo, data.get("responsabilidades_adicionales"),
            ciiu_codes, objeto_social,
        )

        # Primero el cupo del anexo: si la selección no cabe, hay que
        # corregirla antes de preguntar nada más sobre ella.
        if any("anexo solo admite" in a for a in avisos_resp):
            return jsonify({
                "error": "No caben todas las responsabilidades tributarias "
                         "seleccionadas:\n\n" + "\n".join(avisos_resp)
                         + "\n\nQuite alguna para continuar."
            }), 400

        # ─── Calidad ante la DIAN cuando hay comercio exterior ───
        # El formulario ya la exige, pero se puede saltar: sin ella el RUES
        # saldría con las tres casillas vacías.
        exigen = exige_comercio_exterior(responsabilidades)
        perfil_ce = [p for p in (data.get("perfil_comercio_exterior") or []) if p]
        casillas_ce = {}
        if exigen:
            if not perfil_ce:
                return jsonify({
                    "error": "Seleccionó "
                             + ", ".join(f"la responsabilidad {c}" for c in exigen)
                             + ". Debe indicar si la sociedad actuará como importador, "
                               "exportador o usuario aduanero: de eso depende la casilla "
                               "que se marca en el formulario RUES."
                }), 400
            casillas_ce = casillas_rues_comercio_exterior(perfil_ce)
            if not casillas_ce:
                return jsonify({
                    "error": "La calidad declarada ante la DIAN no es válida. "
                             "Debe ser importador, exportador o usuario aduanero."
                }), 400
        if avisos_resp:
            errors.extend(avisos_resp)
        controlante = determinar_situacion_control(accionistas)
        aplica_1780 = determinar_ley_1780(accionistas)

        # Objeto social inteligente
        objeto_social_final = generar_objeto_social(
            ciiu_code=ciiu_code, ciiu_desc=ciiu_desc,
            ciiu_code_sec=ciiu_code_sec, ciiu_desc_sec=ciiu_desc_sec,
            texto_usuario=objeto_social,
        )

        fecha_pfx = fecha.strftime("%Y-%m-%d")
        nombre_limpio = nombre_sas.replace(".", "").replace(" ", "_")
        generated = []

        # ─── 1. ESTATUTOS (.docx) ───
        try:
            est_data = {
                "nombre_sas": nombre_sas,
                "fecha": fecha,
                "municipio": municipio,
                "ciudad": municipio,
                "departamento": departamento,
                "accionistas": accionistas,
                "objeto_social": objeto_social_final,
                "capital_autorizado": capital_autorizado,
                "capital_suscrito": capital_suscrito,
                "capital_pagado": capital_pagado,
                "valor_nominal": valor_nominal,
                "rl_principal": rl_principal,
                "rl_suplente": rl_suplente,
                "rl_principales": data.get("rl_principales"),
                "rl_suplentes": data.get("rl_suplentes"),
                "limitaciones_rl": data.get("limitaciones_rl"),
                "tiene_junta": tiene_junta,
                "tiene_revisor": tiene_revisor,
                "junta_directiva": junta_directiva,
                "revisor_fiscal": revisor_fiscal,
                "apoderado": apoderado,
            }
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Estatutos.docx")
            tmpl = os.path.join(PLANTILLAS_DIR, "estatutos_template.docx")
            generar_estatutos(est_data, tmpl, out)
            generated.append(out)
        except Exception as e:
            errors.append(f"Estatutos: {e}")

        # ─── 2. RUES (.pdf) ───
        try:
            rues_data = {
                "nombre_sas": nombre_sas, "fecha": fecha,
                "municipio": municipio, "departamento": departamento,
                "direccion": direccion, "barrio": barrio,
                "email": email, "telefono1": telefono1,
                "telefono2": telefono2, "telefono3": telefono3,
                "ciiu_code": ciiu_code, "ciiu_code_sec": ciiu_code_sec,
                "capital_suscrito": capital_suscrito,
                "rl_principal": rl_principal,
                "rl_suplente": rl_suplente,
                "accionistas": accionistas,
                "zona": zona, "tipo_local": tipo_local,
                "tenencia": tenencia, "aplica_1780": aplica_1780,
                "es_empresa_familiar": es_empresa_familiar,
                "casillas_comercio_exterior": casillas_ce,
            }
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formulario_RUES.pdf")
            generar_rues(rues_data, os.path.join(PLANTILLAS_DIR, "rues_form.pdf"), out)
            generated.append(out)
        except Exception as e:
            errors.append(f"RUES: {e}")

        # ─── 3. OTRAS ENTIDADES (.pdf) ───
        try:
            otras_data = {
                "nombre_sas": nombre_sas,
                "ciiu_code": ciiu_code, "ciiu_description": ciiu_desc,
                "ingresos_mensuales": str(ingresos),
                "nombre_rl": rl_principal.get("nombre", ""),
                "tipo_doc_rl": rl_principal.get("tipo_doc", "C.C."),
                "cc_rl": rl_principal.get("cc", ""),
            }
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formulario_Otras_Entidades.pdf")
            generar_otras_entidades(otras_data, os.path.join(PLANTILLAS_DIR, "otras_entidades_form.pdf"), out)
            generated.append(out)
        except Exception as e:
            errors.append(f"Otras Entidades: {e}")

        # ─── 4. RESPONSABILIDADES TRIBUTARIAS (.pdf) ───
        try:
            resp_data = {
                "nombre_sas": nombre_sas,
                "nombre_rl": rl_principal.get("nombre", ""),
                "cc_rl": rl_principal.get("cc", ""),
                "fecha": fecha,
                "responsabilidades": responsabilidades,
            }
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Anexo_Responsabilidades_Tributarias.pdf")
            generar_responsabilidades(resp_data, os.path.join(PLANTILLAS_DIR, "responsabilidades_tributarias_form.pdf"), out)
            generated.append(out)
        except Exception as e:
            errors.append(f"Responsabilidades: {e}")

        # ─── 5. EMPRENDIMIENTOS SOCIALES (.pdf) ───
        try:
            emp_data = {
                "nombre_sas": nombre_sas,
                "es_emprendimiento_social": es_emprendimiento,
            }
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Manifestacion_Emprendimiento_Social.pdf")
            generar_emprendimientos(emp_data, os.path.join(PLANTILLAS_DIR, "emprendimientos_sociales_form.pdf"), out)
            generated.append(out)
        except Exception as e:
            errors.append(f"Emprendimientos: {e}")

        # ─── 6. GRUPO ÉTNICO (.pdf) ───
        try:
            ge_data = {"nombre_sas": nombre_sas}
            out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formato_Grupo_Etnico.pdf")
            generar_grupo_etnico(ge_data, os.path.join(PLANTILLAS_DIR, "grupo_etnico_form.pdf"), out)
            generated.append(out)
        except Exception as e:
            errors.append(f"Grupo Étnico: {e}")

        # ─── 7. SITUACIÓN DE CONTROL (condicional) ───
        # Si hay controlante, el usuario decide en el cuestionario si la
        # declara. Cuando opta por no declararla se emite en su lugar la carta
        # explicativa dirigida a la Cámara de Comercio.
        if controlante and declara_control:
            try:
                ctrl_data = {
                    "nombre_sas": nombre_sas,
                    "fecha": fecha,
                    "ciudad": municipio,
                    "domicilio_sas": f"{municipio}, {departamento}",
                    "actividad_ciiu": f"{ciiu_code} - {ciiu_desc}",
                    "controlante_nombre": controlante.get("nombre", ""),
                    "controlante_domicilio": controlante.get("domicilio", municipio),
                    "controlante_nacionalidad": "Colombiana",
                    "controlante_actividad": ciiu_desc or "Actividades empresariales",
                }
                out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formato_Situacion_Control.pdf")
                generar_situacion_control(ctrl_data, os.path.join(PLANTILLAS_DIR, "situacion_de_control_form.pdf"), out)
                generated.append(out)
            except Exception as e:
                errors.append(f"Situación Control: {e}")
        elif controlante and not declara_control:
            try:
                carta_data = {
                    "nombre_sas": nombre_sas,
                    "fecha": fecha,
                    "ciudad": municipio,
                    "camara_ciudad": camara_ciudad,
                    "nombre_rl": rl_principal.get("nombre", ""),
                    "tipo_doc_rl": rl_principal.get("tipo_doc", "C.C."),
                    "cc_rl": rl_principal.get("cc", ""),
                    "controlante_nombre": controlante.get("nombre", ""),
                    "controlante_porcentaje": controlante.get("porcentaje"),
                    "es_unico_accionista": len(accionistas) == 1,
                }
                out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Carta_No_Situacion_Control.pdf")
                generar_carta_no_control(carta_data, out)
                generated.append(out)
            except Exception as e:
                errors.append(f"Carta No Situación Control: {e}")

        # ─── 8. LEY 1780 (condicional) ───
        if aplica_1780:
            try:
                hoy = date.today()
                jovenes = []
                for acc in accionistas:
                    if acc.get("tipo") != "natural":
                        continue
                    nac = acc.get("nacimiento") or acc.get("fecha_nacimiento")
                    if nac:
                        nac_d = parse_date(nac) if isinstance(nac, str) else nac
                        if (hoy - nac_d).days / 365.25 <= 35:
                            jovenes.append(acc)

                ley_data = {
                    "nombre_sas": nombre_sas,
                    "nombre_rl": rl_principal.get("nombre", ""),
                    "cc_rl": rl_principal.get("cc", ""),
                    "fecha": fecha,
                    "ciudad": municipio,
                    "accionistas_jovenes": jovenes,
                }
                out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formato_Ley_1780.pdf")
                generar_ley_1780(ley_data, os.path.join(PLANTILLAS_DIR, "ley_1780_form.pdf"), out)
                generated.append(out)
            except Exception as e:
                errors.append(f"Ley 1780: {e}")

        # ─── 9. EMPRESA FAMILIAR — Ley 2495 de 2025 (condicional) ───
        if es_empresa_familiar and nucleo_familiar:
            try:
                fam_data = {
                    "nombre_sas": nombre_sas,
                    "fecha": fecha,
                    "ciudad": municipio,
                    "camara_ciudad": camara_ciudad,
                    "nombre_rl": rl_principal.get("nombre", ""),
                    "tipo_doc_rl": rl_principal.get("tipo_doc", "C.C."),
                    "cc_rl": rl_principal.get("cc", ""),
                    "nucleo_familiar": nucleo_familiar,
                }
                out = os.path.join(tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Formato_Empresa_Familiar.pdf")
                generar_empresa_familiar(fam_data, os.path.join(PLANTILLAS_DIR, "empresa_familiar_form.pdf"), out)
                generated.append(out)
            except Exception as e:
                errors.append(f"Empresa Familiar: {e}")

        # ─── 10. AUTORIZACIONES PREVIAS ADJUNTADAS ───
        # Van dentro del paquete: son parte de lo que se radica.
        anexos = []
        for codigo, aut in ciiu_autorizaciones.items():
            doc_id = (aut or {}).get("documento_id")
            if not doc_id:
                continue
            origen = os.path.join(AUTORIZACIONES_DIR, os.path.basename(doc_id))
            if not os.path.exists(origen):
                errors.append(f"Autorización de CIIU {codigo}: archivo no encontrado")
                continue
            ext = os.path.splitext(doc_id)[1] or ".pdf"
            destino = os.path.join(
                tmp_dir, f"{fecha_pfx}_{nombre_limpio}_Autorizacion_CIIU_{codigo}{ext}"
            )
            with open(origen, "rb") as f_in, open(destino, "wb") as f_out:
                f_out.write(f_in.read())
            anexos.append(destino)
        generated.extend(anexos)

        # ─── ZIP ───
        zip_name = f"{fecha_pfx}_{nombre_limpio}.zip"
        zip_path = os.path.join(tmp_dir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in generated:
                zf.write(fpath, os.path.basename(fpath))

        if errors:
            app.logger.warning(f"Errores parciales: {errors}")

        decrement_generacion(session["user_id"])

        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_name,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "errores_detalle": errors}), 500


# ═══════════════════════════════════════════════════════════
# EXTRACCIÓN AUTOMÁTICA DE DATOS (Claude Vision)
# ═══════════════════════════════════════════════════════════

EXTRACT_CEDULA_SYSTEM = """Eres un extractor especializado de datos de documentos de identidad colombianos (cédulas de ciudadanía, cédulas de extranjería y pasaportes).

Tu tarea es leer la imagen/PDF del documento y extraer los datos del titular.

Devuelve EXCLUSIVAMENTE un objeto JSON válido con estos campos (usa cadena vacía "" si no puedes leer alguno con certeza):

{
  "nombre_completo": "string (Nombres + Apellidos en orden natural: 'MARIA CAMILA TORRES GARCIA')",
  "tipo_documento": "CC | CE | Pasaporte",
  "numero_documento": "string (solo dígitos, sin puntos ni separadores)",
  "fecha_expedicion": "YYYY-MM-DD o ''",
  "ciudad_expedicion": "string (ciudad de expedición sin tildes especiales si es necesario, ej: 'Medellín')",
  "fecha_nacimiento": "YYYY-MM-DD o ''",
  "genero": "M | F | '' (basado en el campo SEXO si está visible)"
}

Reglas estrictas:
1. NO inventes datos. Si un campo no se puede leer con certeza, usa "".
2. Para el nombre, usa el orden natural (nombres primero, apellidos al final). Mantén tildes (María, José).
3. Para fechas, convierte siempre a formato ISO YYYY-MM-DD.
4. El número de documento debe ser solo dígitos (quita puntos, espacios, guiones).
5. Si es cédula colombiana, tipo_documento = "CC". Si es extranjería, "CE". Si es pasaporte, "Pasaporte".
6. Responde SOLO con el JSON, sin marcadores de código, sin texto adicional."""


EXTRACT_CERTIFICADO_SYSTEM = """Eres un extractor especializado de Certificados de Existencia y Representación Legal expedidos por Cámaras de Comercio de Colombia.

Tu tarea es leer el documento y extraer los datos principales de la sociedad y de su representante legal principal.

Devuelve EXCLUSIVAMENTE un objeto JSON válido con estos campos (usa "" si no puedes leer alguno con certeza):

{
  "razon_social": "string (nombre completo, incluye sufijo S.A.S./LTDA./S.A.)",
  "nit": "string (solo dígitos del NIT, sin DV ni puntos)",
  "nit_dv": "string (dígito de verificación, un solo carácter)",
  "ciudad_domicilio": "string (ciudad principal del domicilio social)",
  "departamento_domicilio": "string (departamento, ej: 'Antioquia')",
  "representante_legal_nombre": "string (Nombres + Apellidos del RL principal)",
  "representante_legal_cc": "string (solo dígitos)",
  "representante_legal_expedicion": "string (ciudad de expedición de la CC del RL)",
  "representante_legal_genero": "M | F | ''"
}

Reglas estrictas:
1. NO inventes datos. Usa "" si no puedes leer un campo.
2. Si hay varios representantes legales (principal y suplente), extrae solo el PRINCIPAL.
3. NIT: solo dígitos, sin DV. El DV va en campo separado.
4. Responde SOLO con el JSON, sin marcadores de código, sin texto adicional."""


EXTRACT_TARJETA_SYSTEM = """Eres un extractor especializado de Tarjetas Profesionales de Contador Público expedidas por la Junta Central de Contadores de Colombia.

Tu tarea es leer la imagen/PDF del documento y extraer los datos del contador.

Devuelve EXCLUSIVAMENTE un objeto JSON válido con estos campos (usa cadena vacía "" si no puedes leer alguno con certeza):

{
  "nombre_completo": "string (Nombres + Apellidos en orden natural: 'CARLOS MESA URIBE')",
  "numero_tarjeta": "string (número de la tarjeta profesional tal como aparece, incluyendo el sufijo con guion si lo tiene, ej: '12345-T')",
  "numero_documento": "string (cédula del contador, solo dígitos, sin puntos)"
}

Reglas estrictas:
1. NO inventes datos. Si un campo no se puede leer con certeza, usa "".
2. El número de tarjeta profesional colombiano suele terminar en '-T'. Consérvalo si aparece.
3. El número de documento debe ser solo dígitos (quita puntos, espacios, guiones).
4. Para el nombre, usa el orden natural y mantén tildes.
5. Responde SOLO con el JSON, sin marcadores de código, sin texto adicional."""


def _extract_with_claude(file_data, mime_type, system_prompt, user_msg):
    """Envía el documento a Claude Vision y parsea el JSON de respuesta.

    Devuelve un dict con los campos extraídos, o lanza una excepción.
    """
    import base64
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxxx"):
        raise RuntimeError("API de Claude no configurada (ANTHROPIC_API_KEY).")

    client = anthropic.Anthropic(api_key=api_key)
    file_b64 = base64.standard_b64encode(file_data).decode("utf-8")

    # Detectar bloque según mime type
    if mime_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": file_b64},
        }
    else:
        # Forzar a image/jpeg si el tipo no es estándar
        valid_image_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if mime_type not in valid_image_types:
            mime_type = "image/jpeg"
        content_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": mime_type, "data": file_b64},
        }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": [content_block, {"type": "text", "text": user_msg}],
        }],
    )

    text = response.content[0].text.strip()

    # Limpiar posibles marcadores de código
    if text.startswith("```"):
        # Cortar primera línea (```json o ```)
        text = text.split("\n", 1)[-1] if "\n" in text else text
        # Quitar último ```
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()

    return json.loads(text)


@app.route("/api/extract/cedula", methods=["POST"])
@login_required
def extract_cedula():
    """Extrae datos de cédula/pasaporte mediante Claude Vision."""
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Archivo vacío"}), 400

    # Límite 10MB
    file_data = file.read()
    if len(file_data) > 10 * 1024 * 1024:
        return jsonify({"error": "Archivo muy grande (máx 10MB)"}), 400

    mime_type = file.mimetype or "image/jpeg"

    try:
        result = _extract_with_claude(
            file_data, mime_type, EXTRACT_CEDULA_SYSTEM,
            "Extrae los datos del documento de identidad. Responde solo con el JSON.",
        )
        return jsonify(result)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Respuesta no es JSON válido: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Error en extract_cedula: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract/tarjeta", methods=["POST"])
@login_required
def extract_tarjeta():
    """Extrae los datos de una tarjeta profesional de contador público."""
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Archivo vacío"}), 400

    file_data = file.read()
    if len(file_data) > 10 * 1024 * 1024:
        return jsonify({"error": "Archivo muy grande (máx 10MB)"}), 400

    mime_type = file.mimetype or "image/jpeg"

    try:
        result = _extract_with_claude(
            file_data, mime_type, EXTRACT_TARJETA_SYSTEM,
            "Extrae los datos de esta tarjeta profesional de contador. Responde solo con el JSON.",
        )
        return jsonify(result)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Respuesta no es JSON válido: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Error en extract_tarjeta: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract/certificado", methods=["POST"])
@login_required
def extract_certificado():
    """Extrae datos de Certificado de Existencia y Representación Legal."""
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Archivo vacío"}), 400

    file_data = file.read()
    if len(file_data) > 15 * 1024 * 1024:
        return jsonify({"error": "Archivo muy grande (máx 15MB)"}), 400

    mime_type = file.mimetype or "application/pdf"

    try:
        result = _extract_with_claude(
            file_data, mime_type, EXTRACT_CERTIFICADO_SYSTEM,
            "Extrae los datos de este Certificado de Existencia y Representación Legal. Responde solo con JSON.",
        )
        return jsonify(result)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Respuesta no es JSON válido: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Error en extract_certificado: {e}")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════
# CHAT ASISTENTE LEGAL (Claude Sonnet)
# ═══════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """Eres un asistente legal experto en derecho societario colombiano, especializado en la constitución de Sociedades por Acciones Simplificadas (S.A.S.) ante las Cámaras de Comercio.

Estás integrado en "Sí S.A.S.", una herramienta de Quarta Acompañamiento Legal S.A.S. (Medellín) que automatiza la generación del paquete de documentos de constitución de S.A.S.

Tu rol es ayudar al usuario mientras llena el formulario de constitución, respondiendo preguntas sobre:
- Requisitos legales para constituir una S.A.S. en Colombia (Ley 1258 de 2008)
- Significado y selección de códigos CIIU
- Redacción del objeto social
- Capital autorizado, suscrito y pagado
- Régimen tributario (ordinario vs. SIMPLE)
- Responsabilidades tributarias ante la DIAN
- Representación legal (principal y suplente)
- Ley 1780 (jóvenes emprendedores, beneficios tributarios)
- Situación de control y grupos empresariales
- Junta directiva y revisor fiscal
- Trámites ante la Cámara de Comercio de Medellín
- Formulario RUES y Otras Entidades
- Emprendimientos sociales (Ley 2234 de 2022)
- Costos de registro y derechos de inscripción

Reglas:
1. Responde en español colombiano, de forma clara y concisa.
2. Sé profesional pero accesible — el usuario puede no ser abogado.
3. Si no estás seguro de algo, dilo con honestidad.
4. No inventes normas o artículos. Cita la norma correcta cuando sea relevante.
5. Mantén las respuestas breves (2-4 párrafos máximo) a menos que el usuario pida más detalle.
6. Si la pregunta no es sobre derecho societario colombiano o constitución de S.A.S., redirige amablemente."""


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint para el chat asistente legal con Claude Sonnet."""
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "No se recibió mensaje"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxxx"):
        return jsonify({
            "error": "API key no configurada",
            "reply": "El asistente legal requiere una API key de Anthropic. "
                     "Configure ANTHROPIC_API_KEY en el archivo .env para activar esta función."
        }), 503

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Construir historial de mensajes
        messages = data.get("history", [])
        messages.append({"role": "user", "content": data["message"]})

        # Limitar historial a últimos 20 mensajes para no exceder contexto
        if len(messages) > 20:
            messages = messages[-20:]

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=CHAT_SYSTEM_PROMPT,
            messages=messages,
        )

        reply = response.content[0].text
        return jsonify({"reply": reply})

    except Exception as e:
        app.logger.error(f"Error en chat: {e}")
        return jsonify({
            "error": str(e),
            "reply": "Lo siento, hubo un error al procesar su consulta. Por favor intente de nuevo."
        }), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
