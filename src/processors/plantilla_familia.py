"""
Motor de la plantilla de estatutos de la S.A.S. de familia.

La plantilla (02_Plantilla_ajustada_alternativas) usa tres convenciones:
  {{campo.sub}}                      valor que se sustituye
  [[SI opciones.x]] ... [[FIN_SI]]   bloque que se incluye si la opción es verdadera
  [[REPETIR lista COMO e]] ... [[FIN_REPETIR]]
                                     bloque que se repite por cada elemento; dentro
                                     se usa {{e.campo}}. En una tabla solo se repite
                                     la fila que usa {{e.*}}: encabezado y totales
                                     quedan una vez.

Los marcadores van solos en su párrafo y se retiran, igual que las indicaciones
editoriales "(ALTERNATIVA ... Retirar esta indicación ...)". Todo párrafo o fila
que se agrega es copia de uno de la plantilla: el formato no cambia.

Las opciones "sin_x" son siempre el complemento de "x"; no se preguntan.
"""

import re
from copy import deepcopy

from docx import Document
from docx.oxml.ns import qn

RE_SI = re.compile(r"^\[\[SI\s+([\w.]+)\s*\]\]$")
RE_REPETIR = re.compile(r"^\[\[REPETIR\s+([\w.]+)\s+COMO\s+(\w+)\b.*\]\]$", re.S)
RE_CAMPO = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
RE_EDITORIAL = re.compile(r"^\(ALTERNATIVA\b.*Retirar esta indicación.*\)$", re.S)


class PlantillaError(Exception):
    """Datos insuficientes o plantilla mal formada."""


def _texto(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()


def _buscar(ctx, ruta):
    valor = ctx
    for parte in ruta.split("."):
        if isinstance(valor, dict) and parte in valor:
            valor = valor[parte]
        else:
            return None
    return valor


def completar_opciones(opciones):
    """Agrega los complementos "sin_x" de cada opción "x"."""
    op = dict(opciones or {})
    for k in list(op):
        if not k.startswith("sin_"):
            op[f"sin_{k}"] = not bool(op[k])
    return op


def _sustituir(el, ctx, faltantes):
    """Reemplaza {{campo}} dentro de cada w:t (los campos no se parten entre runs)."""
    for t in el.iter(qn("w:t")):
        if not t.text or "{{" not in t.text:
            continue

        def valor(m):
            v = _buscar(ctx, m.group(1))
            if v is None or v == "":
                faltantes.add(m.group(1))
                return m.group(0)
            return str(v)

        t.text = RE_CAMPO.sub(valor, t.text)
        t.set(qn("xml:space"), "preserve")


def _bloques(elementos):
    """Agrupa la lista plana de elementos en un árbol de bloques SI/REPETIR."""
    raiz, pila = [], []
    actual = raiz
    for el in elementos:
        texto = _texto(el) if el.tag == qn("w:p") else ""
        m_si, m_rep = RE_SI.match(texto), RE_REPETIR.match(texto)
        if m_si or m_rep:
            nodo = {"tipo": "si" if m_si else "repetir",
                    "expr": (m_si or m_rep).group(1),
                    "como": m_rep.group(2) if m_rep else None,
                    "hijos": [], "marcas": [el]}
            actual.append(nodo)
            pila.append((nodo, actual))
            actual = nodo["hijos"]
        elif texto in ("[[FIN_SI]]", "[[FIN_REPETIR]]"):
            if not pila:
                raise PlantillaError(f"{texto} sin apertura")
            nodo, actual = pila.pop()
            esperado = "si" if texto == "[[FIN_SI]]" else "repetir"
            if nodo["tipo"] != esperado:
                raise PlantillaError(f"{texto} cierra un bloque {nodo['tipo'].upper()}")
            nodo["marcas"].append(el)
        else:
            actual.append(el)
    if pila:
        raise PlantillaError("Bloque sin cerrar: " + pila[-1][0]["expr"])
    return raiz


def _expandir(nodos, ctx, faltantes):
    """Devuelve la lista de elementos resultante para `ctx`."""
    salida = []
    for n in nodos:
        if not isinstance(n, dict):
            el = deepcopy(n)
            if el.tag == qn("w:p") and RE_EDITORIAL.match(_texto(el)):
                continue
            _sustituir(el, ctx, faltantes)
            salida.append(el)
        elif n["tipo"] == "si":
            if _buscar(ctx, n["expr"]):
                salida += _expandir(n["hijos"], ctx, faltantes)
        else:
            lista = _buscar(ctx, n["expr"]) or []
            if not isinstance(lista, list):
                raise PlantillaError(f"{n['expr']} debe ser una lista")
            salida += _expandir_repeticion(n, lista, ctx, faltantes)
    return salida


def _expandir_repeticion(n, lista, ctx, faltantes):
    """Repite el bloque por elemento; en las tablas solo la fila del elemento."""
    como = n["como"]
    salida, tablas_hechas = [], set()
    for item in lista:
        sub = dict(ctx, **{como: item})
        for hijo in n["hijos"]:
            if not isinstance(hijo, dict) and hijo.tag == qn("w:tbl"):
                if id(hijo) in tablas_hechas:
                    continue
                tablas_hechas.add(id(hijo))
                salida.append(_tabla_repetida(hijo, como, lista, ctx, faltantes))
                continue
            salida += _expandir([hijo], sub, faltantes)
    return salida


def _tabla_repetida(tbl, como, lista, ctx, faltantes):
    tabla = deepcopy(tbl)
    patron = "{{" + como + "."
    filas = tabla.findall(qn("w:tr"))
    modelo = next((f for f in filas if patron in "".join(t.text or "" for t in f.iter(qn("w:t")))), None)
    if modelo is not None:
        ancla = modelo
        for item in lista:
            fila = deepcopy(modelo)
            _sustituir(fila, dict(ctx, **{como: item}), faltantes)
            ancla.addnext(fila)
            ancla = fila
        tabla.remove(modelo)
    for f in tabla.findall(qn("w:tr")):
        _sustituir(f, ctx, faltantes)
    return tabla


def _sin_blancos_dobles(body):
    anterior_vacio = False
    for el in list(body):
        if el.tag != qn("w:p"):
            anterior_vacio = False
            continue
        vacio = not _texto(el) and el.find(".//" + qn("w:drawing")) is None
        if vacio and anterior_vacio:
            body.remove(el)
        anterior_vacio = vacio


def renderizar(plantilla, contexto, salida):
    """Genera los estatutos de familia. Falla si queda algún campo sin dato."""
    doc = Document(plantilla)
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))
    elementos = [el for el in body if el is not sect]

    ctx = dict(contexto)
    ctx["opciones"] = completar_opciones(ctx.get("opciones"))
    faltantes = set()
    resultado = _expandir(_bloques(elementos), ctx, faltantes)
    if faltantes:
        raise PlantillaError("Faltan datos para: " + ", ".join(sorted(faltantes)))

    for el in elementos:
        body.remove(el)
    for el in resultado:
        (sect.addprevious(el) if sect is not None else body.append(el))
    _sin_blancos_dobles(body)

    # Encabezados y pies también pueden llevar campos
    for s in doc.sections:
        for parte in (s.header, s.footer):
            for p in parte.paragraphs:
                _sustituir(p._p, ctx, faltantes)
    if faltantes:
        raise PlantillaError("Faltan datos para: " + ", ".join(sorted(faltantes)))

    restos = [t for t in (_texto(e) for e in body) if "{{" in t or "[[" in t]
    if restos:
        raise PlantillaError("Quedaron marcas sin resolver: " + restos[0][:80])
    doc.save(salida)
