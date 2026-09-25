"""
Soportes del paquete: cédulas, certificados de existencia y tarjetas
profesionales de las personas que intervienen en la constitución.

Cada documento cargado en el cuestionario se incluye en la carpeta
`Soportes/` del ZIP. Si alguno falta se incluye en su lugar un PDF de una
página que dice qué documento está pendiente, para que el paquete muestre de
un vistazo qué falta por reunir antes de radicar.

Los archivos llegan del navegador identificados por una llave
"<tipo>:<prefijo>" —ej. "cedula:acc1", "certificado:acc2",
"tarjeta:revisor"—, donde el prefijo es el mismo de los campos del
formulario. Cada persona trae ese prefijo en su `doc_key`.
"""

import os
import re
import unicodedata

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CARPETA = "Soportes"

TITULOS = {
    "cedula": "cédula",
    "certificado": "certificado de existencia y representación legal",
    "tarjeta": "tarjeta profesional",
}


def _digitos(num):
    return re.sub(r"\D", "", str(num or ""))


def _ordinal(lista, i, base):
    """'representante legal principal' o 'representante legal principal 2'
    cuando hay más de uno, para que cada pendiente sea identificable."""
    return f"{base} {i + 1}" if len(lista) > 1 else base


def requerimientos(data):
    """
    Lista de documentos que exige el paquete, en el orden en que aparecen las
    personas en el cuestionario.

    Cada elemento: {tipo, llave, rol, nombre, num}. `llave` es la del archivo
    que envía el navegador; `num` sirve para no pedir dos veces la cédula de
    quien tiene varios roles.
    """
    reqs = []

    def add(tipo, llave, rol, nombre, num=""):
        reqs.append({
            "tipo": tipo, "llave": f"{tipo}:{llave}" if llave else "",
            "rol": rol, "nombre": (nombre or "").strip(), "num": _digitos(num),
        })

    for i, acc in enumerate(data.get("accionistas") or []):
        key = acc.get("doc_key") or ""
        n = i + 1
        if acc.get("tipo") == "juridica":
            add("certificado", key, f"accionista {n}", acc.get("nombre"), acc.get("id_num"))
            add("cedula", f"{key}_rl" if key else "",
                f"representante legal de accionista {n}"
                + (f" ({acc['nombre'].strip()})" if acc.get("nombre") else ""),
                acc.get("rl_nombre"), acc.get("rl_cc"))
        else:
            add("cedula", key, f"accionista {n}", acc.get("nombre"), acc.get("id_num"))

    for clave, base in (("rl_principales", "representante legal principal"),
                        ("rl_suplentes", "representante legal suplente")):
        lista = [r for r in (data.get(clave) or []) if r and r.get("nombre")]
        for i, rl in enumerate(lista):
            add("cedula", rl.get("doc_key"), _ordinal(lista, i, base),
                rl.get("nombre"), rl.get("cc") or rl.get("cedula"))

    junta = data.get("junta_directiva") if data.get("tiene_junta") else None
    for clave, base in (("principales", "miembro principal"), ("suplentes", "miembro suplente")):
        lista = (junta or {}).get(clave) or []
        for i, m in enumerate(lista):
            add("cedula", m.get("doc_key"), f"{base} {i + 1} de junta directiva",
                m.get("nombre"), m.get("id_num"))

    rf = data.get("revisor_fiscal") if data.get("tiene_revisor") else None
    if rf:
        if (rf.get("tipo") or "natural") == "juridica":
            add("cedula", "revisor_contador", "contador designado por la revisoría fiscal",
                rf.get("contador_nombre"), rf.get("contador_id_num"))
            add("tarjeta", "revisor_contador", "contador designado por la revisoría fiscal",
                rf.get("contador_nombre"))
        else:
            add("cedula", "revisor", "revisor fiscal designado", rf.get("nombre"), rf.get("id_num"))
            add("tarjeta", "revisor", "revisor fiscal designado", rf.get("nombre"))

    ap = data.get("apoderado")
    if ap and ap.get("nombre"):
        add("cedula", "apoderado", "apoderado", ap.get("nombre"), ap.get("id_num"))

    return reqs


def agrupar(reqs):
    """
    Une las cédulas de una misma persona (mismo número de documento) en un
    solo soporte con todos sus roles. Certificados y tarjetas no se unen.
    """
    grupos, por_num = [], {}
    for r in reqs:
        clave = (r["tipo"], r["num"]) if r["tipo"] == "cedula" and r["num"] else None
        if clave and clave in por_num:
            g = por_num[clave]
            g["roles"].append(r["rol"])
            g["llaves"].append(r["llave"])
            continue
        g = {"tipo": r["tipo"], "roles": [r["rol"]], "llaves": [r["llave"]],
             "nombre": r["nombre"]}
        grupos.append(g)
        if clave:
            por_num[clave] = g
    return grupos


def _unir_roles(roles):
    return roles[0] if len(roles) == 1 else ", ".join(roles[:-1]) + " y " + roles[-1]


def _nombre_archivo(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return t[:150]


def _pdf_pendiente(path, titulo, nombre):
    c = canvas.Canvas(path, pagesize=letter)
    ancho, alto = letter
    c.setFont("Helvetica-Bold", 16)
    # Partir el título en líneas que quepan en la página
    palabras, lineas, actual = titulo.split(), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if c.stringWidth(prueba, "Helvetica-Bold", 16) > ancho - 144:
            lineas.append(actual)
            actual = p
        else:
            actual = prueba
    lineas.append(actual)
    y = alto / 2 + 12 * len(lineas)
    for ln in lineas:
        c.drawCentredString(ancho / 2, y, ln)
        y -= 24
    if nombre:
        c.setFont("Helvetica", 13)
        c.drawCentredString(ancho / 2, y - 12, nombre.upper())
    c.showPage()
    c.save()


def armar_soportes(data, archivos, destino_dir):
    """
    Escribe en `destino_dir` un archivo por soporte: el cargado por el usuario
    o el PDF de pendiente. `archivos` mapea llave → (bytes, nombre_original).

    Devuelve la lista de (ruta_local, ruta_en_zip).
    """
    os.makedirs(destino_dir, exist_ok=True)
    salida, usados = [], set()
    for g in agrupar(requerimientos(data)):
        doc = TITULOS[g["tipo"]]
        roles = _unir_roles(g["roles"])
        archivo = next((archivos[k] for k in g["llaves"] if k and k in archivos), None)

        base = f"{doc.split()[0].capitalize()} - {roles}"
        if g["nombre"]:
            base += f" - {g['nombre']}"
        if archivo:
            ext = os.path.splitext(archivo[1] or "")[1].lower() or ".pdf"
            nombre = _nombre_archivo(base) + ext
        else:
            nombre = "PENDIENTE_" + _nombre_archivo(base) + ".pdf"
        # Dos soportes no pueden quedar con el mismo nombre dentro del ZIP
        raiz, ext = os.path.splitext(nombre)
        k = 2
        while nombre in usados:
            nombre = f"{raiz}_{k}{ext}"
            k += 1
        usados.add(nombre)

        ruta = os.path.join(destino_dir, nombre)
        if archivo:
            with open(ruta, "wb") as f:
                f.write(archivo[0])
        else:
            _pdf_pendiente(ruta, f"PENDIENTE DE CARGAR {doc} de {roles}".upper(), g["nombre"])
        salida.append((ruta, f"{CARPETA}/{nombre}"))
    return salida
