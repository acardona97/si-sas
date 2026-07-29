# -*- coding: utf-8 -*-
"""
Validación de códigos CIIU para constitución de S.A.S.

El CIIU es un indicador inicial, no una prueba concluyente: un mismo código
puede comprender actividades reguladas y actividades ordinarias. Por eso las
reglas viven en una matriz versionada (data/reglas_ciiu.json) y no como
listas sueltas dentro del código, y varias decisiones dependen de la
modalidad que declare el usuario y del texto del objeto social.

Niveles de decisión:

  BLOCK_NOT_COMMERCIAL_ENTITY  la actividad no es de una sociedad mercantil
  BLOCK_NOT_SAS                exige otro vehículo jurídico
  REQUIRES_PRIOR_AUTHORIZATION compatible, pero hay que adjuntar el acto previo
  CONDITIONAL_REVIEW           el código es amplio: se decide con preguntas
  ALLOWED_WITH_OPERATING_WARNING  permitido, con habilitación antes de operar

Regla que no se puede romper: adjuntar un documento NUNCA convierte un
bloqueo por tipo societario en un permiso. La autorización solo aplica cuando
la S.A.S. es jurídicamente compatible con la actividad.
"""
import json
import os
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
RUTA_REGLAS = os.path.join(BASE_DIR, "data", "reglas_ciiu.json")

DECISIONES_BLOQUEO = ("BLOCK_NOT_COMMERCIAL_ENTITY", "BLOCK_NOT_SAS")

_cache = None


def cargar_matriz():
    """Carga la matriz regulatoria (una sola vez por proceso)."""
    global _cache
    if _cache is None:
        with open(RUTA_REGLAS, encoding="utf-8") as f:
            datos = json.load(f)
        datos["_por_codigo"] = {r["codigo"]: r for r in datos["reglas"]}
        _cache = datos
    return _cache


def version_matriz():
    m = cargar_matriz()
    return {"version": m["version"], "revisado_el": m["revisado_el"]}


def regla_de(codigo):
    """Regla aplicable a un código, o None si no tiene restricción."""
    if not codigo:
        return None
    return cargar_matriz()["_por_codigo"].get(str(codigo).strip())


def _sin_tildes(texto):
    nfkd = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _terminos_presentes(regla, objeto_social):
    """Términos disparadores que aparecen en el objeto social."""
    terminos = regla.get("terminos_disparadores") or []
    if not terminos:
        return []
    texto = _sin_tildes(objeto_social)
    return [t for t in terminos if _sin_tildes(t) in texto]


def evaluar(codigo, respuestas=None, objeto_social="", autorizacion=None):
    """
    Evalúa un código CIIU y devuelve la decisión final.

    respuestas   dict {id_pregunta: "si"|"no"} con lo que declaró el usuario
    objeto_social texto libre, para los códigos con términos disparadores
    autorizacion dict con los datos del acto administrativo adjunto, o None

    El resultado siempre trae:
      decision, bloquea, requiere_autorizacion, preguntas (las que faltan o
      las que hay que hacer), titulo, mensaje y el fundamento normativo.
    """
    respuestas = respuestas or {}
    regla = regla_de(codigo)

    if regla is None:
        return {
            "codigo": codigo,
            "decision": "ALLOWED",
            "bloquea": False,
            "requiere_autorizacion": False,
            "preguntas": [],
            "titulo": "",
            "mensaje": "",
            "fundamento": [],
        }

    base = {
        "codigo": codigo,
        "titulo": regla.get("titulo", ""),
        "mensaje": regla.get("mensaje", ""),
        "fundamento": regla.get("fundamento", []),
        "tipo_entidad_requerido": regla.get("tipo_entidad_requerido"),
        "autoridad": regla.get("autoridad"),
        "preguntas": [],
        "requiere_autorizacion": False,
    }

    decision = regla["decision"]

    # ── Bloqueos duros: no se negocian ni se subsanan con un archivo ──
    if decision in DECISIONES_BLOQUEO:
        return dict(base, decision=decision, bloquea=True)

    # ── Códigos permitidos que solo se elevan si el objeto social los delata ──
    disparados = _terminos_presentes(regla, objeto_social)
    hay_preguntas = bool(regla.get("preguntas"))
    debe_preguntar = decision == "CONDITIONAL_REVIEW" or (disparados and hay_preguntas)

    if debe_preguntar and hay_preguntas:
        preguntas = regla["preguntas"]
        faltantes = [p for p in preguntas if respuestas.get(p["id"]) not in ("si", "no")]
        if faltantes:
            return dict(
                base,
                decision="CONDITIONAL_REVIEW",
                bloquea=False,
                preguntas=preguntas,
                pendiente=True,
                terminos_detectados=disparados,
                mensaje=(regla.get("mensaje", "") if not disparados else
                         "El objeto social menciona "
                         + ", ".join(disparados)
                         + ". Confirme el alcance de la actividad."),
            )

        # Todas respondidas: se aplica el modo de escalamiento
        marcadas = [p["id"] for p in preguntas
                    if p.get("escala") and respuestas.get(p["id"]) == "si"]
        con_escala = [p for p in preguntas if p.get("escala")]
        if regla.get("modo_escalamiento") == "todas":
            escala = len(marcadas) == len(con_escala) and bool(con_escala)
        else:
            escala = bool(marcadas)

        rama = regla["escalamiento"] if escala else regla["sin_escalamiento"]
        resultado = dict(
            base,
            decision=rama["decision"],
            mensaje=rama.get("mensaje", base["mensaje"]),
            preguntas=preguntas,
            respondidas=True,
            disparadores=marcadas,
        )
        if rama.get("tipo_entidad_requerido"):
            resultado["tipo_entidad_requerido"] = rama["tipo_entidad_requerido"]
        if rama.get("autoridad"):
            resultado["autoridad"] = rama["autoridad"]
        decision = rama["decision"]
    else:
        resultado = dict(base, decision=decision)

    resultado["bloquea"] = decision in DECISIONES_BLOQUEO

    # ── Autorización previa: solo cuando la S.A.S. sí es compatible ──
    if decision == "REQUIRES_PRIOR_AUTHORIZATION":
        resultado["requiere_autorizacion"] = True
        resultado["autorizacion_adjunta"] = bool(autorizacion)
    return resultado


def resumen_para_listado(codigo):
    """Etiqueta corta para marcar el código en la lista desplegable."""
    regla = regla_de(codigo)
    if regla is None:
        return None
    decision = regla["decision"]
    etiquetas = {
        "BLOCK_NOT_COMMERCIAL_ENTITY": ("bloqueado", "No corresponde a una sociedad"),
        "BLOCK_NOT_SAS": ("bloqueado", "No disponible para S.A.S."),
        "REQUIRES_PRIOR_AUTHORIZATION": ("autorizacion", "Requiere autorización previa"),
        "CONDITIONAL_REVIEW": ("preguntas", "Requiere responder preguntas"),
        "ALLOWED_WITH_OPERATING_WARNING": ("aviso", "Requiere habilitación para operar"),
    }
    nivel, texto = etiquetas[decision]
    return {"decision": decision, "nivel": nivel, "etiqueta": texto}


def validar_seleccion(codigos, respuestas=None, objeto_social="", autorizaciones=None):
    """
    Revalida todos los códigos escogidos. Es la comprobación de servidor que
    se corre antes de generar los documentos: la del formulario no basta,
    porque se puede saltar.

    Devuelve (ok, errores, detalle_por_codigo).
    """
    autorizaciones = autorizaciones or {}
    errores = []
    detalle = {}

    for codigo in [c for c in (codigos or []) if c]:
        res = evaluar(codigo, respuestas, objeto_social, autorizaciones.get(codigo))
        detalle[codigo] = res

        if res["bloquea"]:
            texto = f"CIIU {codigo}: {res['titulo']}. {res['mensaje']}"
            if res.get("tipo_entidad_requerido"):
                texto += f" Vehículo requerido: {res['tipo_entidad_requerido']}."
            errores.append(texto)
        elif res.get("pendiente"):
            errores.append(
                f"CIIU {codigo}: falta responder las preguntas que determinan si la "
                f"actividad puede desarrollarse mediante una S.A.S."
            )
        elif res.get("requiere_autorizacion") and not res.get("autorizacion_adjunta"):
            autoridad = res.get("autoridad") or "la autoridad competente"
            errores.append(
                f"CIIU {codigo}: debe adjuntar la autorización previa expedida por "
                f"{autoridad} antes de generar los documentos."
            )

    return (not errores), errores, detalle
