# -*- coding: utf-8 -*-
"""
Procesador de PDFs con AcroForms para constitución S.A.S.

Llena los campos de formulario en los PDFs usando pypdf.
Todos los PDFs usan AcroForm nativo para alineación perfecta.
"""
import io
import os
import unicodedata
from datetime import date
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, TextStringObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# ════════════════════════════════════════════════════════════════
# UTILIDADES
# ════════════════════════════════════════════════════════════════

def _strip_tildes(text):
    """Elimina tildes/acentos para mejor renderizado en PDFs.
    Ej: 'Medellín' -> 'Medellin', 'María José' -> 'Maria Jose'
    """
    if not text:
        return text
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _get_on_state(annot):
    """Detecta el nombre del estado 'on' de un checkbox/radio.
    Busca en /AP/N la key que NO sea /Off."""
    ap = annot.get("/AP", {})
    if hasattr(ap, "get_object"):
        ap = ap.get_object()
    n_dict = ap.get("/N", {})
    if hasattr(n_dict, "get_object"):
        n_dict = n_dict.get_object()
    for key in n_dict:
        if str(key) != "/Off":
            return str(key)
    return "/Yes"  # fallback


def _fill_acroform(template_path, output_path, field_values, checkbox_fields=None,
                   radio_fields=None, font_size=None):
    """Llena un PDF AcroForm con los valores dados.

    Args:
        field_values: dict de nombre_campo -> valor (texto)
        checkbox_fields: dict de nombre_campo -> bool (marcar/desmarcar)
        radio_fields: dict de nombre_grupo -> valor_choice (ej: 'tipo_identificacion' -> '/Choice1')
        font_size: tamaño de fuente en pt para campos de texto (None = dejar el del template)
    """
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # Eliminar tildes de TODOS los valores de texto para mejor renderizado PDF
    clean_values = {k: _strip_tildes(v) if isinstance(v, str) else v
                    for k, v in field_values.items()}

    # Llenar campos de texto
    for page in writer.pages:
        writer.update_page_form_field_values(page, clean_values)

    # Forzar tamaño de fuente si se especificó (para formularios con font-size 0/auto)
    if font_size:
        # Detectar el nombre de fuente del template (puede ser /F0, /Helv, etc.)
        # para no sobrescribir con una fuente que no existe en el DR del PDF.
        template_font = "/Helv"  # fallback
        for page in writer.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            annots_list = annots.get_object() if hasattr(annots, "get_object") else annots
            for annot_ref in annots_list:
                annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                da = str(annot.get("/DA", ""))
                if "/F" in da:
                    # Extraer nombre de fuente (ej: "/F0" de "/F0 0 Tf")
                    import re as _re
                    m = _re.search(r"(/F\w+)", da)
                    if m:
                        template_font = m.group(1)
                        break
            if template_font != "/Helv":
                break

        da_str = f"0 0 0 rg {template_font} {font_size} Tf"
        for page in writer.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            annots_list = annots.get_object() if hasattr(annots, "get_object") else annots
            for annot_ref in annots_list:
                annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                ft = str(annot.get("/FT", ""))
                if ft == "/Tx":  # Solo campos de texto
                    annot[NameObject("/DA")] = TextStringObject(da_str)

    # Marcar checkboxes — detecta automáticamente el estado "on" correcto
    if checkbox_fields:
        for page in writer.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            annots_list = annots.get_object() if hasattr(annots, "get_object") else annots
            for annot_ref in annots_list:
                annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                field_name = str(annot.get("/T", ""))
                if field_name in checkbox_fields:
                    if checkbox_fields[field_name]:
                        on_state = _get_on_state(annot)
                        annot[NameObject("/V")] = NameObject(on_state)
                        annot[NameObject("/AS")] = NameObject(on_state)
                    else:
                        annot[NameObject("/V")] = NameObject("/Off")
                        annot[NameObject("/AS")] = NameObject("/Off")

    # Marcar radio buttons — busca por nombre del grupo padre
    if radio_fields:
        for page in writer.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            annots_list = annots.get_object() if hasattr(annots, "get_object") else annots
            for annot_ref in annots_list:
                annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                parent = annot.get("/Parent")
                if parent:
                    parent_obj = parent.get_object() if hasattr(parent, "get_object") else parent
                    group_name = str(parent_obj.get("/T", ""))
                    if group_name in radio_fields:
                        target_choice = radio_fields[group_name]
                        on_state = _get_on_state(annot)
                        if on_state == target_choice:
                            annot[NameObject("/AS")] = NameObject(on_state)
                            parent_obj[NameObject("/V")] = NameObject(target_choice)
                        else:
                            annot[NameObject("/AS")] = NameObject("/Off")

    # Activar NeedAppearances para que el visor PDF recalcule las apariencias
    # de los campos (necesario para campos numéricos con scripts AFNumber_Format)
    catalog = writer._root_object
    if "/AcroForm" in catalog:
        acro = catalog["/AcroForm"]
        if hasattr(acro, "get_object"):
            acro = acro.get_object()
        acro[NameObject("/NeedAppearances")] = BooleanObject(True)

    with open(output_path, "wb") as f:
        writer.write(f)


def _fmt_money(n):
    """Formatea número como moneda colombiana: 1000000 -> '1.000.000'."""
    if not n:
        return "0"
    return f"{int(n):,}".replace(",", ".")


def _overlay_text(template_path, output_path, text_items):
    """
    Coloca texto en coordenadas específicas sobre un PDF existente.
    text_items: lista de dicts con keys: page, x, y, text, size (opcional), font (opcional)
    """
    reader = PdfReader(template_path)
    writer = PdfWriter()

    # Agrupar items por página
    by_page = {}
    for item in text_items:
        pg = item.get("page", 0)
        by_page.setdefault(pg, []).append(item)

    for i, page in enumerate(reader.pages):
        if i in by_page:
            # Crear overlay
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            for item in by_page[i]:
                font = item.get("font", "Helvetica")
                size = item.get("size", 9)
                c.setFont(font, size)
                c.drawString(item["x"], item["y"], str(item["text"]))
            c.save()
            buf.seek(0)
            overlay_reader = PdfReader(buf)
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


# ════════════════════════════════════════════════════════════════
# 1. EMPRENDIMIENTOS SOCIALES (4 campos AcroForm)
# ════════════════════════════════════════════════════════════════

def generar_emprendimientos(data, template_path, output_path):
    """Llena el formulario de Manifestación de Emprendimientos Sociales."""
    es_emprendimiento = data.get("es_emprendimiento_social", False)

    fields = {
        "razon_social": data["nombre_sas"],
        # NIT queda vacío en constitución
    }

    # Los checkboxes son campos de texto pequeño con X
    if es_emprendimiento:
        fields["es_emprendimiento_social_si"] = "X"
        fields["es_emprendimiento_social_no"] = ""
    else:
        fields["es_emprendimiento_social_si"] = ""
        fields["es_emprendimiento_social_no"] = "X"

    _fill_acroform(template_path, output_path, fields)


# ════════════════════════════════════════════════════════════════
# 2. SITUACIÓN DE CONTROL (19 campos AcroForm)
# ════════════════════════════════════════════════════════════════

def generar_situacion_control(data, template_path, output_path):
    """Llena el Formato 1 - Situación de Control (Decreto 667/2018)."""
    fecha = data["fecha"]
    if isinstance(fecha, str):
        from datetime import datetime
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    fields = {
        "fecha_dia": str(fecha.day).zfill(2),
        "fecha_mes": str(fecha.month).zfill(2),
        "fecha_anio": str(fecha.year),
        "camara_comercio_ciudad_1": data.get("ciudad", "Medellín"),
        "camara_comercio_ciudad_2": data.get("ciudad", "Medellín"),
        # Sociedad subordinada (la que se constituye)
        "sociedad_subordinada_nombre": data["nombre_sas"],
        "sociedad_subordinada_nombre_1": data["nombre_sas"],
        "sociedad_subordinada_domicilio": data.get("domicilio_sas", "Medellín, Antioquia"),
        "sociedad_subordinada_domicilio_1": data.get("domicilio_sas", "Medellín, Antioquia"),
        "sociedad_subordinada_actividad": data.get("actividad_ciiu", ""),
        "sociedad_subordinada_actividad_1": data.get("actividad_ciiu", ""),
        # Controlante
        "controlante_nombre": data.get("controlante_nombre", ""),
        "controlante_nombre_1": data.get("controlante_nombre", ""),
        "controlante_domicilio": data.get("controlante_domicilio", ""),
        "controlante_domicilio_1": data.get("controlante_domicilio", ""),
        "controlante_nacionalidad": data.get("controlante_nacionalidad", "Colombiana"),
        "controlante_nacionalidad_1": data.get("controlante_nacionalidad", "Colombiana"),
        "controlante_actividad": data.get("controlante_actividad", ""),
        "controlante_actividad_1": data.get("controlante_actividad", ""),
    }

    _fill_acroform(template_path, output_path, fields, font_size=8)


# ════════════════════════════════════════════════════════════════
# 3. LEY 1780 (58 campos AcroForm)
# ════════════════════════════════════════════════════════════════

def generar_ley_1780(data, template_path, output_path):
    """Llena el Formato de Ley 1780 de 2016 (jóvenes emprendedores)."""
    fecha = data["fecha"]
    if isinstance(fecha, str):
        from datetime import datetime
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]

    fields = {
        "municipio": data.get("ciudad", "Medellín"),
        "fecha_dia": str(fecha.day),
        "fecha_mes": meses[fecha.month],
        "fecha_anio": str(fecha.year),
        "rl_nombre_inline": data.get("nombre_rl", ""),
        "rl_nombre_inline_2": data.get("nombre_rl", ""),
        "razon_social_inline": data["nombre_sas"],
        "razon_social_inline_2": data["nombre_sas"],
        # Pie de página
        "rl_nombre_pie": data.get("nombre_rl", ""),
        "rl_nombre_pie_2": data.get("nombre_rl", ""),
        "rl_id_pie": data.get("cc_rl", ""),
        "rl_id_pie_2": data.get("cc_rl", ""),
    }

    # Accionistas jóvenes (≤35 años) - cuadro superior
    jovenes = data.get("accionistas_jovenes", [])
    for i, joven in enumerate(jovenes[:5], 1):
        nombre = joven.get("nombre", "")
        id_num = joven.get("id_num", "")
        fields[f"acc{i}_nombre"] = nombre
        fields[f"acc{i}_nombre_orig"] = nombre
        fields[f"acc{i}_id"] = id_num
        fields[f"acc{i}_id_orig"] = id_num

    _fill_acroform(template_path, output_path, fields)


# ════════════════════════════════════════════════════════════════
# 4. RESPONSABILIDADES TRIBUTARIAS (28 campos AcroForm)
# ════════════════════════════════════════════════════════════════

def generar_responsabilidades(data, template_path, output_path):
    """Llena el Anexo de Responsabilidades Tributarias."""
    fecha = data["fecha"]
    if isinstance(fecha, str):
        from datetime import datetime
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    fields = {
        "fecha_dia": str(fecha.day).zfill(2),
        "fecha_mes": str(fecha.month).zfill(2),
        "fecha_anio": str(fecha.year),
        "rl_nombre": data.get("nombre_rl", ""),
        "razon_social": data["nombre_sas"],
        "nombre_legible_rl": data.get("nombre_rl", ""),
        "num_identificacion": data.get("cc_rl", ""),
    }

    # Llenar tabla de responsabilidades (hasta 10 filas)
    responsabilidades = data.get("responsabilidades", [])
    for i, (num, nombre) in enumerate(responsabilidades[:10], 1):
        fields[f"resp{i}_num"] = num
        fields[f"resp{i}_nombre"] = nombre

    # Marcar tipo de identificación: CC (Cédula de Ciudadanía) = Choice1
    tipo_id = data.get("tipo_identificacion", "CC")
    TIPO_ID_MAP = {
        "CC": "/Choice1",
        "CE": "/Choice2",
        "TI": "/Choice3",
        "PASAPORTE": "/Choice4",
    }
    radio_choice = TIPO_ID_MAP.get(tipo_id.upper(), "/Choice1")

    _fill_acroform(template_path, output_path, fields,
                   radio_fields={"tipo_identificacion": radio_choice})


# ════════════════════════════════════════════════════════════════
# 5. GRUPO ÉTNICO (29 campos AcroForm)
# ════════════════════════════════════════════════════════════════

def generar_grupo_etnico(data, template_path, output_path):
    """Llena el Formato de Grupo Étnico."""
    fields = {
        "razon_social": data["nombre_sas"],
        # NIT vacío en constitución
    }

    # Por defecto: No en las 3 secciones (sociedad recién constituida)
    checkboxes = {
        "p1_no": True,
        "p1_si": False,
        "p2_no": True,
        "p2_si": False,
        "p3_no": True,
        "p3_si": False,
    }

    _fill_acroform(template_path, output_path, fields, checkbox_fields=checkboxes)


# ════════════════════════════════════════════════════════════════
# 6. RUES (338 campos - overlay por coordenadas)
# ════════════════════════════════════════════════════════════════

def generar_rues(data, template_path, output_path):
    """
    Llena el Formulario RUES usando AcroForm (285 campos nativos).
    Cada campo del PDF tiene nombre y posición fija — llenado perfecto.
    """
    fecha = data["fecha"]
    if isinstance(fecha, str):
        from datetime import datetime
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    nombre_sas = data["nombre_sas"]
    municipio = data.get("municipio", "Medellín")
    departamento = data.get("departamento", "Antioquia")
    direccion = data.get("direccion", "")
    barrio = data.get("barrio", "")
    email = data.get("email", "")
    telefono1 = data.get("telefono1", "")
    telefono2 = data.get("telefono2", "")
    telefono3 = data.get("telefono3", "")
    ciiu_code = data.get("ciiu_code", "")
    ciiu_code_sec = data.get("ciiu_code_sec", "")
    capital_suscrito = data.get("capital_suscrito", 1_000_000)
    rl = data.get("rl_principal", {})
    zona = data.get("zona", "urbana")
    tipo_local = data.get("tipo_local", "oficina")
    tenencia = data.get("tenencia", "arriendo")

    fields = {}
    checkboxes = {}

    # ═══════════════════════════════════════════════════════════
    # HOJA 1 — Sección 1: Información del Registro
    # ═══════════════════════════════════════════════════════════

    # Matrícula / Inscripción (Registro Mercantil)
    checkboxes["Casilla 1_8"] = True

    # Tipo General de Organización: 02 (Sociedad)
    fields["Cuadro de texto 2_26"] = "0"
    fields["Cuadro de texto 2_27"] = "2"

    # Tipo Específico de Organización: 16 (S.A.S.)
    fields["Cuadro de texto 2_24"] = "1"
    fields["Cuadro de texto 2_25"] = "6"

    # ─── Sección 2: Identificación ───

    # Razón Social (Persona Jurídica)
    fields["Cuadro de texto 2_42"] = nombre_sas

    # ─── Sección 3: Ubicación y Datos Generales ───

    # Dirección de Domicilio Principal
    fields["Cuadro de texto 2_76"] = direccion

    # Zona: Urbana/Rural
    if zona == "urbana":
        checkboxes["Casilla 1_20"] = True
    else:
        checkboxes["Casilla 1_21"] = True

    # Ubicación tipo local — campos de texto donde se pone "X"
    UBICACION_FIELDS = {
        "local": "Cuadro de texto 2_78",
        "oficina": "Cuadro de texto 2_79",
        "local_oficina": "Cuadro de texto 2_80",
        "fabrica": "Cuadro de texto 2_81",
        "vivienda": "Cuadro de texto 2_82",
        "finca": "Cuadro de texto 2_83",
    }
    if tipo_local in UBICACION_FIELDS:
        fields[UBICACION_FIELDS[tipo_local]] = "X"

    # Municipio / Departamento / Barrio / País
    fields["Cuadro de texto 2_84"] = municipio
    fields["Cuadro de texto 2_85"] = departamento
    fields["Cuadro de texto 2_86"] = barrio
    fields["Cuadro de texto 2_87"] = "Colombia"

    # Teléfono 1 — un dígito por casilla (10 casillas)
    tel_digits = telefono1.replace(" ", "").replace("-", "")
    TEL1_FIELDS = [
        "Cuadro de texto 2_93", "Cuadro de texto 2_94", "Cuadro de texto 2_95",
        "Cuadro de texto 2_96", "Cuadro de texto 2_97", "Cuadro de texto 2_98",
        "Cuadro de texto 2_99", "Cuadro de texto 2_100", "Cuadro de texto 2_101",
        "Cuadro de texto 2_102",
    ]
    for j, digit in enumerate(tel_digits[:10]):
        fields[TEL1_FIELDS[j]] = digit

    # Teléfono 2
    if telefono2:
        tel2_digits = telefono2.replace(" ", "").replace("-", "")
        TEL2_FIELDS = [
            "Cuadro de texto 2_103", "Cuadro de texto 2_104", "Cuadro de texto 2_105",
            "Cuadro de texto 2_106", "Cuadro de texto 2_107", "Cuadro de texto 2_108",
            "Cuadro de texto 2_109", "Cuadro de texto 2_110", "Cuadro de texto 2_111",
            "Cuadro de texto 2_112",
        ]
        for j, digit in enumerate(tel2_digits[:10]):
            fields[TEL2_FIELDS[j]] = digit

    # Teléfono 3
    if telefono3:
        tel3_digits = telefono3.replace(" ", "").replace("-", "")
        TEL3_FIELDS = [
            "Cuadro de texto 2_113", "Cuadro de texto 2_114", "Cuadro de texto 2_115",
            "Cuadro de texto 2_116", "Cuadro de texto 2_117", "Cuadro de texto 2_118",
            "Cuadro de texto 2_119", "Cuadro de texto 2_120", "Cuadro de texto 2_121",
            "Cuadro de texto 2_122",
        ]
        for j, digit in enumerate(tel3_digits[:10]):
            fields[TEL3_FIELDS[j]] = digit

    # Correo Electrónico
    fields["Cuadro de texto 2_206"] = email

    # ─── Notificación Judicial (mismos datos) ───

    # Dirección Notificación
    fields["Cuadro de texto 2_123"] = direccion

    # Zona Notificación
    if zona == "urbana":
        checkboxes["Casilla 1_22"] = True

    # Municipio / Departamento / Barrio / País Notificación
    fields["Cuadro de texto 2_125"] = municipio
    fields["Cuadro de texto 2_126"] = departamento
    fields["Cuadro de texto 2_127"] = barrio
    fields["Cuadro de texto 2_128"] = "Colombia"

    # Teléfono 1 Notificación
    NTEL1_FIELDS = [
        "Cuadro de texto 2_134", "Cuadro de texto 2_135", "Cuadro de texto 2_136",
        "Cuadro de texto 2_137", "Cuadro de texto 2_138", "Cuadro de texto 2_139",
        "Cuadro de texto 2_140", "Cuadro de texto 2_141", "Cuadro de texto 2_142",
        "Cuadro de texto 2_143",
    ]
    for j, digit in enumerate(tel_digits[:10]):
        fields[NTEL1_FIELDS[j]] = digit

    # Teléfono 2 Notificación
    if telefono2:
        NTEL2_FIELDS = [
            "Cuadro de texto 2_144", "Cuadro de texto 2_145", "Cuadro de texto 2_146",
            "Cuadro de texto 2_147", "Cuadro de texto 2_148", "Cuadro de texto 2_149",
            "Cuadro de texto 2_150", "Cuadro de texto 2_151", "Cuadro de texto 2_152",
            "Cuadro de texto 2_153",
        ]
        for j, digit in enumerate(tel2_digits[:10]):
            fields[NTEL2_FIELDS[j]] = digit

    # Teléfono 3 Notificación
    if telefono3:
        NTEL3_FIELDS = [
            "Cuadro de texto 2_154", "Cuadro de texto 2_155", "Cuadro de texto 2_156",
            "Cuadro de texto 2_157", "Cuadro de texto 2_158", "Cuadro de texto 2_159",
            "Cuadro de texto 2_160", "Cuadro de texto 2_161", "Cuadro de texto 2_162",
            "Cuadro de texto 2_163",
        ]
        for j, digit in enumerate(tel3_digits[:10]):
            fields[NTEL3_FIELDS[j]] = digit

    # Correo Notificación
    fields["Cuadro de texto 2_207"] = email

    # Sede administrativa
    TENENCIA_CHECKBOXES = {
        "propia": "Casilla 1_24",
        "arriendo": "Casilla 1_25",
        "comodato": "Casilla 1_26",
        "prestamo": "Casilla 1_27",
    }
    if tenencia in TENENCIA_CHECKBOXES:
        checkboxes[TENENCIA_CHECKBOXES[tenencia]] = True

    # Sí autoriza notificación por correo electrónico
    checkboxes["Casilla 1_28"] = True

    # ─── Sección 4: Actividades Económicas ───

    # CIIU 1 (4 dígitos)
    if ciiu_code and len(ciiu_code) >= 4:
        CIIU1_FIELDS = [
            "Cuadro de texto 2_164", "Cuadro de texto 2_165",
            "Cuadro de texto 2_166", "Cuadro de texto 2_167",
        ]
        for j, digit in enumerate(ciiu_code[:4]):
            fields[CIIU1_FIELDS[j]] = digit

    # CIIU 2 (4 dígitos)
    if ciiu_code_sec and len(ciiu_code_sec) >= 4:
        CIIU2_FIELDS = [
            "Cuadro de texto 2_169", "Cuadro de texto 2_170",
            "Cuadro de texto 2_171", "Cuadro de texto 2_172",
        ]
        for j, digit in enumerate(ciiu_code_sec[:4]):
            fields[CIIU2_FIELDS[j]] = digit

    # Fecha inicio actividad primaria (AAAAMMDD)
    fecha_str = fecha.strftime("%Y%m%d")
    FECHA_PRI_FIELDS = [
        "Cuadro de texto 2_184", "Cuadro de texto 2_185", "Cuadro de texto 2_186",
        "Cuadro de texto 2_187", "Cuadro de texto 2_188", "Cuadro de texto 2_189",
        "Cuadro de texto 2_190", "Cuadro de texto 2_191",
    ]
    for j, digit in enumerate(fecha_str[:8]):
        fields[FECHA_PRI_FIELDS[j]] = digit

    # Fecha inicio actividad secundaria
    if ciiu_code_sec:
        FECHA_SEC_FIELDS = [
            "Cuadro de texto 2_192", "Cuadro de texto 2_193", "Cuadro de texto 2_194",
            "Cuadro de texto 2_195", "Cuadro de texto 2_196", "Cuadro de texto 2_197",
            "Cuadro de texto 2_198", "Cuadro de texto 2_199",
        ]
        for j, digit in enumerate(fecha_str[:8]):
            fields[FECHA_SEC_FIELDS[j]] = digit

    # CIIU de mayores ingresos por actividad ordinaria (= actividad principal)
    if ciiu_code and len(ciiu_code) >= 4:
        CIIU_INGRESOS_FIELDS = [
            "Cuadro de texto 2_201", "Cuadro de texto 2_202",
            "Cuadro de texto 2_203", "Cuadro de texto 2_204",
        ]
        for j, digit in enumerate(ciiu_code[:4]):
            fields[CIIU_INGRESOS_FIELDS[j]] = digit

    # ═══════════════════════════════════════════════════════════
    # HOJA 2 — Información Financiera y Estado de la PJ
    # ═══════════════════════════════════════════════════════════
    # Los campos "Campo numérico" son campos numéricos del PDF.
    # Deben recibir el número plano (sin puntos); el PDF aplica su propio formato.
    cap_plain = str(int(capital_suscrito))

    # Estado de Situación Financiera
    # Nota: 'é' en nombres de campo PDF está codificado como #C3#A9
    _cn = "Campo num#C3#A9rico"
    fields[f"{_cn} 1"] = cap_plain              # Activo Corriente
    fields[f"{_cn} 1_2"] = "0"                  # Activo No Corriente
    fields[f"{_cn} 2"] = cap_plain              # Activo Total
    fields[f"{_cn} 1_3"] = "0"                  # Pasivo Corriente
    fields[f"{_cn} 1_4"] = "0"                  # Pasivo No Corriente
    fields[f"{_cn} 1_5"] = "0"                  # Pasivo Total
    fields[f"{_cn} 1_6"] = cap_plain            # Patrimonio Neto
    fields[f"{_cn} 1_7"] = cap_plain            # Pasivo + Patrimonio

    # Estado de Resultados — todo en 0
    fields[f"{_cn} 1_9"] = "0"                  # Ingresos Actividad Ordinaria
    fields[f"{_cn} 1_10"] = "0"                 # Otros Ingresos
    fields[f"{_cn} 1_11"] = "0"                 # Costo de Ventas
    fields[f"{_cn} 1_12"] = "0"                 # Gastos Operacionales
    fields[f"{_cn} 1_13"] = "0"                 # Otros Gastos
    fields[f"{_cn} 1_14"] = "0"                 # Gastos por Impuestos
    fields[f"{_cn} 1_15"] = "0"                 # Utilidad/Pérdida Operacional
    fields[f"{_cn} 1_16"] = "0"                 # Resultado del Período

    # GRUPO NIIF: 3 (microempresas)
    fields["Cuadro de texto 1_2"] = "3"

    # Composición del capital: 1.2 PRIVADO = 100%
    fields[f"{_cn} 1_18"] = "100"

    # Porcentaje de participación de mujeres en el capital social
    accionistas = data.get("accionistas", [])
    pct_mujeres = 0.0
    for acc in accionistas:
        if acc.get("tipo") == "natural" and acc.get("genero") == "F":
            pct_mujeres += float(acc.get("porcentaje", 0))
    pct_mujeres_str = str(int(pct_mujeres)) if pct_mujeres == int(pct_mujeres) else f"{pct_mujeres:.1f}"
    fields[f"{_cn} 1_21"] = pct_mujeres_str

    # Sección 8: Estado actual PJ — código "02" (activa)
    fields["Cuadro de texto 1_3"] = "0"
    fields["Cuadro de texto 1_4"] = "2"

    # Número de empleados: 0 (5 dígitos)
    fields["Cuadro de texto 1_5"] = "0"

    # Número total de mujeres que ocupan cargos directivos
    rl_suplente = data.get("rl_suplente")
    num_mujeres_dir = 0
    if rl.get("genero") == "F":
        num_mujeres_dir += 1
    if rl_suplente and rl_suplente.get("genero") == "F":
        num_mujeres_dir += 1
    fields["Cuadro de texto 1_10"] = str(num_mujeres_dir)

    # Número de empleadas mujeres (0 en constitución)
    fields["Cuadro de texto 1_15"] = "0"

    # Establecimientos: NO
    checkboxes["Casilla 1_34"] = True
    # Proceso de innovación: NO
    checkboxes["Casilla 1_36"] = True
    # Empresa familiar: NO
    checkboxes["Casilla 1_38"] = True
    # Porcentaje empleados temporales: 0
    fields[f"{_cn} 3"] = "0"

    # Sección 10: Ley 1780
    aplica_1780 = data.get("aplica_1780", False)
    if aplica_1780:
        checkboxes["Casilla 1_39"] = True
    else:
        checkboxes["Casilla 1_40"] = True

    # Sección 11: Protección social — SÍ
    checkboxes["Casilla 1_43"] = True
    # Tipo aportante: Independiente
    checkboxes["Casilla 1_48"] = True

    # Firma: RL nombre y documento
    fields["Cuadro de texto 3"] = rl.get("nombre", "")
    fields["Cuadro de texto 3_4"] = rl.get("cc", "")
    # CC checkbox
    checkboxes["Casilla 1_49"] = True
    # País
    fields["Cuadro de texto 3_2"] = "Colombia"

    # ═══════════════════════════════════════════════════════════
    # Escribir AcroForm
    # ═══════════════════════════════════════════════════════════
    _fill_acroform(template_path, output_path, fields, checkbox_fields=checkboxes)


# ════════════════════════════════════════════════════════════════
# 7. OTRAS ENTIDADES (102 AcroForm campos)
# ════════════════════════════════════════════════════════════════

def generar_otras_entidades(data, template_path, output_path):
    """
    Llena el Formulario de Otras Entidades usando AcroForm + overlay.
    Campos AcroForm mapeados desde plantilla (Button1-Button100, Text30-Text102).
    Firma del RL via overlay (sin campo AcroForm).
    """
    nombre_sas = data["nombre_sas"]
    ciiu_code = data.get("ciiu_code", "")
    ingresos = data.get("ingresos_mensuales", "100.000")
    nombre_rl = data.get("nombre_rl", "")
    cc_rl = data.get("cc_rl", "")

    # ─── AcroForm Fields ───
    fields = {}

    # Campo 3: Razón social (Text30)
    fields["Text30"] = nombre_sas

    # Campo 5: CIIU dígitos (Text32-Text35)
    if ciiu_code and len(ciiu_code) == 4:
        fields["Text32"] = ciiu_code[0]
        fields["Text33"] = ciiu_code[1]
        fields["Text34"] = ciiu_code[2]
        fields["Text35"] = ciiu_code[3]

    # Campo 7.2: Promedio mensual ingresos (Text101)
    fields["Text101"] = str(ingresos)

    # Firma: Número de identificación (Text102)
    fields["Text102"] = cc_rl

    # ─── Checkboxes ───
    checkbox_fields = {
        "Button1": True,     # Inscripción RUT Primera Vez = Sí
        "Button97": True,    # Sí industria y comercio
        "Button99": True,    # No avisos (por defecto)
    }

    # ─── Escribir AcroForm ───
    _fill_acroform(template_path, output_path, fields, checkbox_fields=checkbox_fields,
                   font_size=8)

    # ─── Overlay: Firma nombre RL (no hay campo AcroForm para esto) ───
    if nombre_rl:
        overlay_items = [
            {"page": 0, "x": 100, "y": 202, "text": _strip_tildes(nombre_rl), "size": 9},
        ]
        _overlay_text(output_path, output_path, overlay_items)
