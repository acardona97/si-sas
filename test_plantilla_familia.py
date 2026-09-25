"""Motor de la plantilla de familia: condicionales, repeticiones y tabla."""
import itertools
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
from docx import Document  # noqa: E402
from processors.plantilla_familia import renderizar, PlantillaError  # noqa: E402

TMPL = os.path.join(BASE, "plantillas", "estatutos_familia_template.docx")
CAMPOS = [c["campo"] for c in json.load(
    open(os.path.join(BASE, "src", "data", "familia_placeholders.json"), encoding="utf8"))["campos"]]

# Variables de repetición → lista del contexto donde viven
LISTAS = {"clase": "clases", "constituyente": "constituyentes", "conversion": "conversiones",
          "decision": "decisiones_reservadas", "escenario": "dividendos.escenarios",
          "asignacion": "escenario.asignaciones", "causal": "exclusion.causales",
          "firmante": "firmantes", "nombramiento": "nombramientos", "suscripcion": "suscripciones"}


def poner(ctx, ruta, valor):
    partes = ruta.split(".")
    for p in partes[:-1]:
        ctx = ctx.setdefault(p, {})
    ctx.setdefault(partes[-1], valor)


def contexto(opciones):
    ctx = {}
    items = {v: [{}, {}] for v in LISTAS}
    for campo in CAMPOS:
        raiz, _, resto = campo.partition(".")
        if raiz == "opciones":
            continue
        if raiz in LISTAS and resto:
            for k, it in enumerate(items[raiz], 1):
                poner(it, resto, f"<{campo}#{k}>")
        else:
            poner(ctx, campo, f"<{campo}>")
    for var, lista in LISTAS.items():
        if var == "asignacion":
            continue
        destino = [dict(it) for it in items[var]]
        if var == "escenario":
            for e in destino:
                e["asignaciones"] = [dict(a) for a in items["asignacion"]]
        poner(ctx, lista, destino) if "." in lista else ctx.__setitem__(lista, destino)
    ctx["opciones"] = opciones
    return ctx


def render(opciones):
    out = os.path.join(tempfile.mkdtemp(), "f.docx")
    renderizar(TMPL, contexto(opciones), out)
    doc = Document(out)
    return doc, "\n".join(p.text for p in doc.paragraphs)


OPC = ["aportes_especie", "arbitraje", "autorizacion_transferencias", "consejo_familia",
       "conversion_por_transferencia", "dividendos_preferenciales_o_fijos", "junta_directiva",
       "objeto_amplio", "poder_tramites", "preferencia_suscripcion", "preferencia_transferencia",
       "prohibicion_temporal", "protocolo_familia", "revisor_fiscal_inicial",
       "opcion_compra", "exclusion"]

# Todas encendidas / todas apagadas: nunca quedan marcas ni campos sin llenar
for valor in (True, False):
    doc, txt = render({k: valor for k in OPC})
    assert "{{" not in txt and "[[" not in txt and "Retirar esta indicación" not in txt
    # Las alternativas A y B son excluyentes
    assert ("No se pacta opción estatutaria de compra" in txt) != valor, valor

# Repeticiones: dos constituyentes, dos firmantes, escenarios anidados
doc, txt = render({k: True for k in OPC})
assert txt.count("<constituyente.") >= 2 and "#2>" in txt
tabla = doc.tables[0]
filas = [[c.text for c in r.cells] for r in tabla.rows]
assert filas[0][0] == "Accionista" and filas[-1][0] == "Total"
assert len(filas) == 4, filas   # encabezado + 2 suscripciones + total

# Combinaciones al azar de opciones
for combo in itertools.islice(itertools.product([True, False], repeat=4), 16):
    ops = dict(zip(OPC[:4], combo), **{k: False for k in OPC[4:]})
    render(ops)

# Un dato faltante detiene la generación con el nombre del campo
ctx = contexto({k: False for k in OPC})
ctx["sociedad"].pop("nombre_completo", None)
try:
    renderizar(TMPL, ctx, os.path.join(tempfile.mkdtemp(), "x.docx"))
    raise AssertionError("debía fallar")
except PlantillaError as e:
    assert "sociedad.nombre_completo" in str(e), e

print("OK test_plantilla_familia")
