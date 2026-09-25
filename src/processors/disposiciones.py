"""
Disposiciones especiales redactadas con Claude Sonnet.

El abogado describe reglas propias (sobre junta directiva, revisoría fiscal u
otras materias). Sonnet no escribe el Word: propone operaciones sobre los
párrafos de los estatutos ya generados —insertar un parágrafo o un inciso,
reemplazar o eliminar un párrafo en conflicto— y una segunda llamada revisa
el documento resultante completo. El código aplica esas operaciones de forma
determinista clonando párrafos reales de la plantilla, de modo que
interlineado, sangría, espaciado, fuente y numeración quedan idénticos al
resto del documento.

Flujo:
  1. proponer_disposiciones(docx, disposiciones) → vista previa (operaciones,
     ajustes, hallazgos) que el usuario revisa y edita.
  2. aplicar(doc, operaciones, con_cambios) al generar: limpio o con control
     de cambios nativo de Word.
  3. generar_informe(...) → PDF con lo integrado, lo ajustado y por qué.
"""

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

MODELO = "claude-sonnet-5"
AUTOR_CAMBIOS = "Anuwa"

ORDINALES = ["primero", "segundo", "tercero", "cuarto", "quinto", "sexto",
             "séptimo", "octavo", "noveno", "décimo", "undécimo", "duodécimo"]
RE_PARAGRAFO = re.compile(r"^(Parágrafo)(?:\s+([A-Za-zÁÉÍÓÚáéíóú]+))?\s*([.:])", re.I)


class DisposicionError(Exception):
    """Las operaciones aprobadas ya no encajan en los estatutos generados."""


# ════════════════════════════════════════════════════════════════
# LECTURA DEL DOCUMENTO
# ════════════════════════════════════════════════════════════════

def _texto(p_elem):
    return "".join(t.text or "" for t in p_elem.iter(qn("w:t")))


def _norm(texto):
    return " ".join((texto or "").split())


def _num_id(p_elem):
    n = p_elem.find(".//" + qn("w:numId"))
    return n.get(qn("w:val")) if n is not None else None


def _es_negrilla(run):
    rpr = run.find(qn("w:rPr"))
    b = rpr.find(qn("w:b")) if rpr is not None else None
    return b is not None and b.get(qn("w:val")) not in ("0", "false")


def _runs(p_elem):
    return [r for r in p_elem.findall(qn("w:r")) if (r.findtext(qn("w:t")) or "")]


def indexar(doc):
    """
    Párrafos del cuerpo con su ubicación en el articulado.

    Los artículos se numeran con la numeración automática de Word, así que su
    número se reconstruye contando los párrafos de la lista de artículos (la
    del artículo de nombramiento del representante legal).
    """
    parrafos = doc.element.body.findall(qn("w:p"))
    num_articulos = None
    for p in parrafos:
        if _texto(p).strip().startswith("Nombramiento y período del representante legal."):
            num_articulos = _num_id(p)
            break

    entradas, n_art, art_actual = [], 0, None
    for i, p in enumerate(parrafos):
        texto = _norm(_texto(p))
        if re.match(r"CAPÍTULO [IVXL]+\b", texto):
            tipo, art_actual = "capitulo", None
        elif num_articulos and _num_id(p) == num_articulos:
            n_art += 1
            art_actual = f"Artículo {n_art}"
            tipo = "articulo"
        elif RE_PARAGRAFO.match(texto):
            tipo = "paragrafo"
        elif _num_id(p):
            tipo = "lista"
        else:
            tipo = "texto"
        entradas.append({"i": i, "elem": p, "texto": texto, "tipo": tipo,
                         "articulo": art_actual if tipo != "capitulo" else None})
    return entradas


def _fin_de_articulo(entradas, i):
    """Índice del último párrafo con texto del artículo al que pertenece `i`."""
    art = entradas[i]["articulo"]
    fin = i
    for e in entradas[i + 1:]:
        if e["tipo"] in ("capitulo", "articulo"):
            break
        if e["articulo"] == art and e["texto"]:
            fin = e["i"]
    return fin


# ════════════════════════════════════════════════════════════════
# SONNET: PROPUESTA Y VALIDACIÓN FINAL
# ════════════════════════════════════════════════════════════════

SYSTEM_INTEGRAR = """Eres un abogado societario colombiano experto en Sociedades por Acciones Simplificadas (S.A.S.). Integras en unos estatutos ya redactados las disposiciones especiales que pide el abogado que constituye la sociedad.

Recibes los estatutos como párrafos numerados con su índice [i], el artículo al que pertenecen y su tipo (capitulo, articulo = título y primer párrafo del artículo, paragrafo, lista = literal de una enumeración, texto = inciso). Recibes también las disposiciones pedidas, cada una con su número y su materia (junta = junta directiva, revisor = revisoría fiscal, adicional = otra materia).

Cómo integrar:
1. No crees artículos nuevos. Cada disposición se incorpora dentro del artículo con el que guarda relación: como parágrafo (forma "paragrafo": va al final del artículo; el sistema escribe el rótulo "Parágrafo ...") o como inciso (forma "inciso": párrafo nuevo del artículo, inmediatamente después del párrafo que indiques). Las de junta van en los artículos del capítulo de junta directiva; las de revisoría, en el artículo de revisoría fiscal; las adicionales, en el artículo más relacionado. Puedes dividir una disposición en varias operaciones si toca materias de artículos distintos.
2. Valida cada disposición contra el resto de los estatutos y contra las normas imperativas colombianas (Ley 1258 de 2008, Código de Comercio, Ley 222 de 1995). Si la contraría, ajusta la redacción lo mínimo necesario para que sea válida y coherente, y explica el ajuste. Si no hay forma válida de incorporarla, no la integres y explícalo en ajustes.
3. Si una disposición nueva contradice un párrafo existente, propón reemplazarlo (tipo "reemplazar", con el cuerpo completo del párrafo ya corregido) o eliminarlo (tipo "eliminar"). Nunca reemplaces ni elimines títulos de capítulo ni el párrafo que abre un artículo (tipo articulo) salvo para corregir solo su cuerpo con "reemplazar"; nunca toques párrafos que no tengan relación con las disposiciones.
4. Redacción: igual estilo, registro y terminología que los estatutos ("asamblea general de accionistas", "junta directiva", "representante legal", "revisor fiscal"), concordancia de género y número, ortografía y puntuación correctas. Un solo párrafo por operación, sin rótulo "Parágrafo", sin numeración, sin comillas envolventes, sin markdown. En "reemplazar" sobre un párrafo tipo articulo, escribe solo el cuerpo, sin el título.
5. No cites normas, artículos ni sentencias salvo que estés seguro de su número y contenido; en la duda, no cites.
6. "parrafo" es siempre el índice [i] de un párrafo existente: el párrafo tras el cual va el inciso, cualquier párrafo del artículo donde va el parágrafo, o el párrafo que se reemplaza o elimina.
7. En "disposicion" indica el número de la disposición que origina la operación. En "motivo" explica en una frase por qué esa ubicación o ese cambio."""

SYSTEM_VALIDAR = """Eres un abogado societario colombiano revisor. Recibes el texto completo de unos estatutos de S.A.S. después de integrar disposiciones especiales. Los párrafos afectados están marcados: [NUEVO k], [MODIFICADO k] y [ELIMINADO k], donde k es el número de la operación. Los demás párrafos llevan su índice [i].

Revisa el documento completo en estructura, redacción, gramática, fondo y legalidad (Ley 1258 de 2008, Código de Comercio, Ley 222 de 1995): contradicciones entre artículos, regulaciones mal ubicadas, duplicidades, normas imperativas desconocidas, remisiones rotas.

Puedes:
- corregir el texto de una operación (accion "corregir", con el texto completo corregido) o anularla (accion "anular") si no debe integrarse;
- proponer operaciones adicionales ("reemplazar" o "eliminar") sobre párrafos existentes que contradigan las disposiciones nuevas, con las mismas reglas: no tocar títulos de capítulo, en párrafos que abren artículo solo reemplazar el cuerpo sin el título, un solo párrafo, sin rótulos ni markdown;
- reportar en "hallazgos" problemas del texto base que no se relacionen con las disposiciones: esos no se modifican, solo se informan.

Si todo está bien, devuelve listas vacías. No cites normas cuyo número y contenido no conozcas con certeza."""

_OP_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": ["insertar", "reemplazar", "eliminar"]},
        "forma": {"type": "string", "enum": ["paragrafo", "inciso", "ninguna"]},
        "parrafo": {"type": "integer"},
        "texto": {"type": "string"},
        "disposicion": {"type": "integer"},
        "motivo": {"type": "string"},
    },
    "required": ["tipo", "forma", "parrafo", "texto", "disposicion", "motivo"],
    "additionalProperties": False,
}

SCHEMA_INTEGRAR = {
    "type": "object",
    "properties": {
        "operaciones": {"type": "array", "items": _OP_SCHEMA},
        "ajustes": {"type": "array", "items": {
            "type": "object",
            "properties": {"disposicion": {"type": "integer"}, "explicacion": {"type": "string"}},
            "required": ["disposicion", "explicacion"], "additionalProperties": False}},
    },
    "required": ["operaciones", "ajustes"],
    "additionalProperties": False,
}

SCHEMA_VALIDAR = {
    "type": "object",
    "properties": {
        "correcciones": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "operacion": {"type": "integer"},
                "accion": {"type": "string", "enum": ["corregir", "anular"]},
                "texto": {"type": "string"},
                "motivo": {"type": "string"},
            },
            "required": ["operacion", "accion", "texto", "motivo"], "additionalProperties": False}},
        "operaciones_extra": {"type": "array", "items": _OP_SCHEMA},
        "hallazgos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["correcciones", "operaciones_extra", "hallazgos"],
    "additionalProperties": False,
}


def _llamar_sonnet(system, contenido, schema):
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("API de Claude no configurada (ANTHROPIC_API_KEY).")
    client = anthropic.Anthropic(api_key=api_key)
    # Streaming: documento largo y respuesta con razonamiento
    with client.messages.stream(
        model=MODELO,
        max_tokens=32000,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": "high",
                       "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": contenido}],
    ) as stream:
        resp = stream.get_final_message()
    if resp.stop_reason == "refusal":
        raise RuntimeError("El modelo no pudo procesar las disposiciones.")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("La respuesta del modelo quedó incompleta. Divida las disposiciones.")
    texto = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(texto)


def _vista_indexada(entradas):
    lineas = []
    for e in entradas:
        if not e["texto"]:
            continue
        ubic = f"{e['articulo']} · {e['tipo']}" if e["articulo"] else e["tipo"]
        lineas.append(f"[{e['i']}] ({ubic}) {e['texto']}")
    return "\n".join(lineas)


def _validar_op(op, entradas):
    """Descarta lo que no se puede aplicar sin romper la estructura."""
    i = op.get("parrafo")
    if not isinstance(i, int) or not 0 <= i < len(entradas) or not entradas[i]["texto"]:
        return "índice de párrafo inexistente"
    e = entradas[i]
    if e["tipo"] == "capitulo" or not e["articulo"]:
        return "fuera del articulado (títulos y encabezados no se modifican)"
    if op["tipo"] == "eliminar" and e["tipo"] == "articulo":
        return "no se elimina el párrafo que abre un artículo"
    if op["tipo"] == "insertar" and op["forma"] not in ("paragrafo", "inciso"):
        return "inserción sin forma"
    if op["tipo"] != "eliminar" and not _norm(op.get("texto")):
        return "texto vacío"
    return None


def _completar(op, entradas):
    e = entradas[op["parrafo"]]
    op["texto"] = _limpiar_texto(op.get("texto", ""))
    op["ancla"] = e["texto"]
    op["articulo"] = e["articulo"] or ""
    op["texto_original"] = e["texto"] if op["tipo"] != "insertar" else ""
    return op


def _limpiar_texto(texto):
    t = _norm(texto).strip('"“”')
    t = RE_PARAGRAFO.sub("", t).strip() if RE_PARAGRAFO.match(t) else t
    if t and t[-1] not in ".;:":
        t += "."
    return t


def _vista_con_marcas(entradas, ops):
    """Texto de los estatutos con las operaciones aplicadas, para la revisión."""
    por_parrafo, inserciones = {}, {}
    for k, op in enumerate(ops):
        if op["tipo"] == "insertar":
            destino = (_fin_de_articulo(entradas, op["parrafo"])
                       if op["forma"] == "paragrafo" else op["parrafo"])
            inserciones.setdefault(destino, []).append((k, op))
        else:
            por_parrafo[op["parrafo"]] = (k, op)
    lineas = []
    for e in entradas:
        if not e["texto"]:
            continue
        if e["i"] in por_parrafo:
            k, op = por_parrafo[e["i"]]
            lineas.append(f"[ELIMINADO {k}] {e['texto']}" if op["tipo"] == "eliminar"
                          else f"[MODIFICADO {k}] {op['texto']}")
        else:
            lineas.append(f"[{e['i']}] {e['texto']}")
        for k, op in inserciones.get(e["i"], []):
            rotulo = "Parágrafo. " if op["forma"] == "paragrafo" else ""
            lineas.append(f"[NUEVO {k}] {rotulo}{op['texto']}")
    return "\n".join(lineas)


def proponer_disposiciones(docx_path, disposiciones):
    """
    Vista previa: integra las disposiciones y valida el documento resultante.

    `disposiciones` → [{"tema": "junta"|"revisor"|"adicional", "texto": str}]
    Devuelve {"operaciones": [...], "ajustes": [...], "hallazgos": [...]}.
    """
    doc = Document(docx_path)
    entradas = indexar(doc)
    pedidas = "\n".join(
        f"{n}. ({d.get('tema', 'adicional')}) {_norm(d.get('texto'))}"
        for n, d in enumerate(disposiciones, 1) if _norm(d.get("texto"))
    )
    if not pedidas:
        return {"operaciones": [], "ajustes": [], "hallazgos": []}

    r1 = _llamar_sonnet(
        SYSTEM_INTEGRAR,
        f"ESTATUTOS:\n{_vista_indexada(entradas)}\n\nDISPOSICIONES PEDIDAS:\n{pedidas}",
        SCHEMA_INTEGRAR,
    )
    ops, descartes = [], []
    for op in r1.get("operaciones", []):
        motivo = _validar_op(op, entradas)
        if motivo:
            descartes.append(f"Operación de la disposición {op.get('disposicion')} descartada: {motivo}.")
        else:
            ops.append(_completar(op, entradas))

    # Validación final sobre el documento completo ya integrado
    r2 = _llamar_sonnet(
        SYSTEM_VALIDAR,
        f"DISPOSICIONES PEDIDAS:\n{pedidas}\n\nESTATUTOS INTEGRADOS:\n{_vista_con_marcas(entradas, ops)}",
        SCHEMA_VALIDAR,
    )
    ajustes = [{"disposicion": a["disposicion"], "explicacion": a["explicacion"]}
               for a in r1.get("ajustes", [])]
    for c in r2.get("correcciones", []):
        k = c.get("operacion")
        if not isinstance(k, int) or not 0 <= k < len(ops):
            continue
        if c["accion"] == "anular":
            ops[k]["anulada"] = True
        elif _norm(c.get("texto")):
            ops[k]["texto"] = _limpiar_texto(c["texto"])
        ajustes.append({"disposicion": ops[k]["disposicion"],
                        "explicacion": f"Revisión final: {c.get('motivo', '')}"})
    ops = [op for op in ops if not op.pop("anulada", False)]
    for op in r2.get("operaciones_extra", []):
        if op["tipo"] == "insertar":
            continue
        motivo = _validar_op(op, entradas)
        if motivo:
            descartes.append(f"Ajuste de la revisión final descartado: {motivo}.")
        else:
            ops.append(_completar(op, entradas))

    return {"operaciones": ops, "ajustes": ajustes,
            "hallazgos": list(r2.get("hallazgos", [])) + descartes,
            "textos_usuario": disposiciones}


# ════════════════════════════════════════════════════════════════
# APLICACIÓN SOBRE EL WORD
# ════════════════════════════════════════════════════════════════

class _Marcas:
    """Marcas de control de cambios de Word (w:ins / w:del)."""

    def __init__(self):
        self.n = 9000
        self.fecha = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _el(self, tag):
        self.n += 1
        el = OxmlElement(tag)
        el.set(qn("w:id"), str(self.n))
        el.set(qn("w:author"), AUTOR_CAMBIOS)
        el.set(qn("w:date"), self.fecha)
        return el

    def insertar_runs(self, p, runs):
        ins = self._el("w:ins")
        runs[0].addprevious(ins)
        for r in runs:
            ins.append(r)

    def borrar_runs(self, p, runs):
        if not runs:
            return
        dele = self._el("w:del")
        runs[0].addprevious(dele)
        for r in runs:
            for t in r.findall(qn("w:t")):
                t.tag = qn("w:delText")
            dele.append(r)

    def marca_parrafo(self, p, tag):
        """Marca el fin de párrafo como insertado o eliminado."""
        ppr = p.find(qn("w:pPr"))
        if ppr is None:
            ppr = OxmlElement("w:pPr")
            p.insert(0, ppr)
        rpr = ppr.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            ppr.append(rpr)
        rpr.insert(0, self._el(tag))


def _referencias(entradas):
    """Párrafos modelo de la plantilla: parágrafo, inciso y línea en blanco."""
    paragrafo = inciso = blanco = None
    for e in entradas:
        runs = _runs(e["elem"])
        if (paragrafo is None and e["tipo"] == "paragrafo" and len(runs) == 2
                and _es_negrilla(runs[0]) and not _es_negrilla(runs[1])
                and _norm(_texto(runs[0])) == "Parágrafo."):
            paragrafo = e
        if (inciso is None and e["tipo"] == "texto" and e["articulo"] and len(runs) == 1
                and not _es_negrilla(runs[0]) and len(e["texto"]) > 80):
            inciso = e
        if (blanco is None and not e["texto"] and paragrafo is not None
                and e["i"] == paragrafo["i"] + 1):
            blanco = e
    if not (paragrafo and inciso):
        raise DisposicionError("La plantilla no tiene párrafos de referencia para integrar disposiciones.")
    if blanco is None:
        blanco = next(e for e in entradas if not e["texto"] and e["i"] > inciso["i"])
    return paragrafo["elem"], inciso["elem"], blanco["elem"]


def _nuevo_parrafo(ref, textos):
    """Copia `ref` con un texto por run (rótulo en negrilla + cuerpo)."""
    p = deepcopy(ref)
    runs = p.findall(qn("w:r"))
    for i, r in enumerate(runs):
        if i >= len(textos):
            p.remove(r)
            continue
        ts = r.findall(qn("w:t"))
        for t in ts[1:]:
            r.remove(t)
        ts[0].text = textos[i]
        ts[0].set(qn("xml:space"), "preserve")
    ppr = p.find(qn("w:pPr"))
    if ppr is not None and ppr.find(qn("w:rPr")) is not None:
        for m in ppr.find(qn("w:rPr")).findall(qn("w:ins")) + ppr.find(qn("w:rPr")).findall(qn("w:del")):
            ppr.find(qn("w:rPr")).remove(m)
    return p


def _resolver(entradas, op):
    """Párrafo destino de una operación: por índice si el texto coincide; si
    no, por texto. Si los estatutos cambiaron desde la vista previa, falla."""
    ancla = _norm(op.get("ancla"))
    i = op.get("parrafo")
    if isinstance(i, int) and 0 <= i < len(entradas) and entradas[i]["texto"] == ancla:
        return i
    iguales = [e["i"] for e in entradas if e["texto"] == ancla]
    if len(iguales) == 1:
        return iguales[0]
    raise DisposicionError(
        "Los estatutos cambiaron desde la vista previa de las disposiciones especiales "
        f"({op.get('articulo') or 'párrafo'}). Vuelva a generar la vista previa antes de continuar.")


def _rotulo(ordinal_idx, capital, sep):
    if ordinal_idx is None:
        return f"Parágrafo{sep} "
    o = ORDINALES[ordinal_idx]
    return f"Parágrafo {o.capitalize() if capital else o}{sep} "


def _cambiar_rotulo(p_elem, nuevo, marcas):
    """Cambia 'Parágrafo.' por 'Parágrafo primero.' en el run del rótulo."""
    run = _runs(p_elem)[0]
    t = run.find(qn("w:t"))
    m = RE_PARAGRAFO.match(t.text or "")
    if not m:
        return
    resto = (t.text or "")[m.end():]
    if marcas is None:
        t.text = nuevo.rstrip() + resto
        return
    viejo = deepcopy(run)
    viejo.find(qn("w:t")).text = m.group(0)
    t.text = nuevo.rstrip() + resto
    t.set(qn("xml:space"), "preserve")
    run.addprevious(viejo)
    marcas.borrar_runs(p_elem, [viejo])
    nuevo_run = deepcopy(run)
    nuevo_run.find(qn("w:t")).text = nuevo.rstrip()
    t.text = resto
    run.addprevious(nuevo_run)
    marcas.insertar_runs(p_elem, [nuevo_run])


def aplicar(doc, operaciones, con_cambios=False):
    """Aplica las operaciones aprobadas; con `con_cambios`, como revisiones de Word."""
    if not operaciones:
        return
    entradas = indexar(doc)
    ref_parag, ref_inciso, ref_blanco = _referencias(entradas)
    marcas = _Marcas() if con_cambios else None

    # Todos los destinos se resuelven antes de tocar el documento
    resueltas = [(op, _resolver(entradas, op)) for op in operaciones]

    # Parágrafos nuevos por artículo, para rotularlos en orden
    nuevos_por_art = {}
    for op, i in resueltas:
        if op["tipo"] == "insertar" and op["forma"] == "paragrafo":
            fin = _fin_de_articulo(entradas, i)
            nuevos_por_art.setdefault(fin, []).append(op)

    # Inserciones primero: su ancla puede ser un párrafo que luego se elimina
    for op, i in resueltas:
        if op["tipo"] != "insertar" or op["forma"] != "inciso":
            continue
        nuevo = _nuevo_parrafo(ref_inciso, [op["texto"]])
        _insertar_despues(entradas[i]["elem"], nuevo, ref_blanco, marcas)

    for fin, ops in nuevos_por_art.items():
        art = entradas[fin]["articulo"]
        existentes = [e for e in entradas
                      if e["articulo"] == art and e["tipo"] == "paragrafo" and e["i"] <= fin]
        total = len(existentes) + len(ops)
        m0 = RE_PARAGRAFO.match(existentes[0]["texto"]) if existentes else None
        sep = m0.group(3) if m0 else "."
        capital = bool(m0 and m0.group(2) and m0.group(2)[0].isupper())
        if total > 1 and len(existentes) == 1 and m0 and (m0.group(2) or "").lower() not in ORDINALES:
            _cambiar_rotulo(existentes[0]["elem"], _rotulo(0, capital, sep), marcas)
        ancla = entradas[fin]["elem"]
        for k, op in enumerate(ops):
            n = len(existentes) + k
            rotulo = _rotulo(n if total > 1 else None, capital, sep)
            nuevo = _nuevo_parrafo(ref_parag, [rotulo, op["texto"]])
            ancla = _insertar_despues(ancla, nuevo, ref_blanco, marcas)

    for op, i in resueltas:
        p = entradas[i]["elem"]
        if op["tipo"] == "eliminar":
            siguiente = p.getnext()
            if marcas:
                marcas.borrar_runs(p, _runs(p))
                marcas.marca_parrafo(p, "w:del")
            else:
                p.getparent().remove(p)
                # Sin su línea en blanco, para no dejar dos seguidas
                if siguiente is not None and siguiente.tag == qn("w:p") and not _texto(siguiente).strip():
                    siguiente.getparent().remove(siguiente)
        elif op["tipo"] == "reemplazar":
            runs = _runs(p)
            # El título en negrilla del artículo o rótulo del parágrafo se conserva
            cuerpo = [r for r in runs if not _es_negrilla(r)] if entradas[i]["tipo"] in ("articulo", "paragrafo") else runs
            if not cuerpo:
                continue
            # Conserva la puntuación y el espacio con que arrancaba el cuerpo
            # tras el título en negrilla (ej. "Quórum" + ". Salvo...")
            original = "".join(t.text or "" for r in cuerpo for t in r.findall(qn("w:t")))
            inicio = re.match(r"^[\s.:;,\-–]*", original).group(0) if entradas[i]["tipo"] != "texto" else ""
            if marcas:
                _reemplazo_con_cambios(p, cuerpo, original, inicio + op["texto"], marcas)
            else:
                nuevo = _run_con(cuerpo[0], inicio + op["texto"])
                cuerpo[-1].addnext(nuevo)
                for r in cuerpo:
                    p.remove(r)


def _run_con(modelo, texto):
    """Run con el formato de `modelo` y el texto dado."""
    r = deepcopy(modelo)
    for t in r.findall(qn("w:t"))[1:]:
        r.remove(t)
    t = r.find(qn("w:t"))
    t.text = texto
    t.set(qn("xml:space"), "preserve")
    return r


def _reemplazo_con_cambios(p, cuerpo, viejo, nuevo, marcas):
    """Control de cambios palabra por palabra: solo se tacha lo que cambia."""
    from difflib import SequenceMatcher

    tok = lambda s: re.findall(r"\S+\s*|\s+", s)  # noqa: E731
    a, b = tok(viejo), tok(nuevo)
    modelo = cuerpo[0]
    ancla = cuerpo[-1]
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            r = _run_con(modelo, "".join(a[i1:i2]))
            ancla.addnext(r)
            ancla = r
            continue
        if i2 > i1:
            r = _run_con(modelo, "".join(a[i1:i2]))
            ancla.addnext(r)
            marcas.borrar_runs(p, [r])
            ancla = r.getparent()
        if j2 > j1:
            r = _run_con(modelo, "".join(b[j1:j2]))
            ancla.addnext(r)
            marcas.insertar_runs(p, [r])
            ancla = r.getparent()
    for r in cuerpo:
        p.remove(r)


def _insertar_despues(ancla, nuevo, ref_blanco, marcas):
    """Inserta línea en blanco + párrafo tras `ancla`; devuelve el párrafo."""
    blanco = _nuevo_parrafo(ref_blanco, [])
    ancla.addnext(blanco)
    blanco.addnext(nuevo)
    if marcas:
        marcas.insertar_runs(nuevo, nuevo.findall(qn("w:r")))
        marcas.marca_parrafo(nuevo, "w:ins")
        marcas.marca_parrafo(blanco, "w:ins")
    return nuevo


# ════════════════════════════════════════════════════════════════
# INFORME
# ════════════════════════════════════════════════════════════════

def generar_informe(disposiciones, nombre_sas, path):
    """PDF con las disposiciones pedidas, cómo se integraron y los ajustes."""
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    st = getSampleStyleSheet()
    h, n = st["Heading2"], st["BodyText"]
    e = lambda t: escape(str(t or ""))  # noqa: E731
    story = [Paragraph(f"Informe de disposiciones especiales — {e(nombre_sas)}", st["Title"]),
             Spacer(1, 8)]

    story.append(Paragraph("Disposiciones pedidas", h))
    for k, d in enumerate(disposiciones.get("textos_usuario") or [], 1):
        story.append(Paragraph(f"<b>{k}. ({e(d.get('tema'))})</b> {e(d.get('texto'))}", n))

    story.append(Paragraph("Cambios integrados en los estatutos", h))
    nombres = {"insertar": "Se incorpora", "reemplazar": "Se reemplaza", "eliminar": "Se elimina"}
    for op in disposiciones.get("operaciones") or []:
        forma = (" como parágrafo" if op["forma"] == "paragrafo" else " como inciso") \
            if op["tipo"] == "insertar" else ""
        story.append(Paragraph(
            f"<b>{e(op.get('articulo') or 'Estatutos')} — {nombres[op['tipo']]}{e(forma)}</b> "
            f"(disposición {e(op.get('disposicion'))})", n))
        if op.get("texto_original"):
            story.append(Paragraph(f"<strike>{e(op['texto_original'])}</strike>", n))
        if op["tipo"] != "eliminar":
            story.append(Paragraph(e(op.get("texto")), n))
        story.append(Paragraph(f"<i>Motivo: {e(op.get('motivo'))}</i>", n))
        story.append(Spacer(1, 6))

    if disposiciones.get("ajustes"):
        story.append(Paragraph("Ajustes por validez y coherencia", h))
        for a in disposiciones["ajustes"]:
            story.append(Paragraph(f"<b>Disposición {e(a.get('disposicion'))}:</b> {e(a.get('explicacion'))}", n))
    if disposiciones.get("hallazgos"):
        story.append(Paragraph("Observaciones de la revisión final (no modificadas)", h))
        for x in disposiciones["hallazgos"]:
            story.append(Paragraph(f"• {e(x)}", n))

    SimpleDocTemplate(path, pagesize=letter, title="Informe de disposiciones especiales").build(story)
