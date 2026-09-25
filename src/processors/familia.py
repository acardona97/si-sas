"""
Contexto de los estatutos de la S.A.S. de familia a partir del cuestionario.

El usuario solo elige opciones y aporta datos; los textos jurídicos salen de
los textos aprobados (docs/FAMILIA_CATALOGO_TEXTOS.md y decisiones de
docs/PLAN_MEJORAS.md). Nada de lo que el usuario escribe entra como cláusula,
salvo la definición personalizada de grupo familiar, que revisa el abogado.

Reglas fijas del módulo:
  - CIIU principal 7010; objeto de tenencia y precautelación patrimonial.
  - Opción de compra (art. 66) y exclusión (art. 67) en su alternativa
    negativa hasta revisión jurídica.
  - Suplencias personales y opcionales.
"""

from datetime import date
from itertools import combinations

from processors.estatutos import _numero_a_letras, _fecha_literal, _label_tipo_doc

CIIU_PRINCIPAL = "7010"

OBJETO_PRINCIPAL = (
    "la tenencia, precautelación e inversión de activos como bienes muebles e "
    "inmuebles, acciones, bonos y cualquier otro título representativo de "
    "derechos; en mercados públicos o privados nacionales o internacionales"
)

OPERACIONES_CONEXAS = (
    "todas las operaciones, de cualquier naturaleza que ellas fueren, relacionadas "
    "con el objeto mencionado, así como cualquier actividad similar, conexa o "
    "complementaria o que permita facilitar o desarrollar el comercio o la "
    "industria de la sociedad, entre ellas, adquirir bienes muebles e inmuebles "
    "necesarios para sus actividades y enajenar unos y otros, tomar o dar dinero "
    "en préstamo a interés, gravar en cualquier forma sus bienes, celebrar "
    "contratos de sociedad o de asociación, y en general celebrar en su propio "
    "nombre o por cuenta de terceros toda clase de actos y contratos lícitos "
    "relacionados con su objeto"
)

GRUPO_FAMILIAR = {
    "amplio": "los accionistas fundadores, sus cónyuges o compañeros permanentes, "
              "y los descendientes y ascendientes en primer grado de consanguinidad "
              "de los fundadores",
    "descendencia": "los accionistas fundadores y sus descendientes",
    "segundo_grado": "los accionistas fundadores y sus parientes hasta el segundo "
                     "grado de consanguinidad o afinidad",
}

# Mayorías: umbral + operador + denominador explícitos (Guía §4)
MITAD_MAS_UNA = ("el voto favorable de accionistas que representen la mitad más una "
                 "de los votos que confieren las acciones suscritas")
SETENTA = ("el voto favorable de accionistas que representen al menos el setenta por "
           "ciento (70 %) de los votos que confieren las acciones suscritas")


class DatosFamiliaError(ValueError):
    """Datos del cuestionario incompletos o incoherentes."""


def _miles(n):
    return f"{int(n):,}".replace(",", ".")


def _pct(x):
    x = round(float(x), 2)
    return str(int(x)) if x == int(x) else str(x).replace(".", ",")


def _lista(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def escenarios_por_defecto(codigos):
    """Todos los subconjuntos no vacíos de clases; reparto igual por defecto."""
    esc = {}
    for n in range(1, len(codigos) + 1):
        for combo in combinations(codigos, n):
            base = round(100 / n, 2)
            reparto = {c: base for c in combo}
            reparto[combo[-1]] = round(100 - base * (n - 1), 2)
            esc["+".join(combo)] = reparto
    return esc


def _validar_escenarios(codigos, escenarios):
    esperados = set(escenarios_por_defecto(codigos))
    if set(escenarios) != esperados:
        raise DatosFamiliaError(
            "La matriz de dividendos debe tener exactamente los escenarios "
            + ", ".join(sorted(esperados)) + ".")
    for nombre, reparto in escenarios.items():
        clases = nombre.split("+")
        if set(reparto) - set(clases):
            raise DatosFamiliaError(f"El escenario {nombre} asigna a clases que no concurren.")
        if abs(sum(float(v) for v in reparto.values()) - 100) > 0.01:
            raise DatosFamiliaError(f"El escenario {nombre} debe sumar 100 %.")


def _persona_doc(p, clave_num="id_num", clave_tipo="tipo_doc"):
    return _label_tipo_doc(p.get(clave_tipo)), str(p.get(clave_num) or "").strip()


def construir_contexto(data, hoy=None):
    """Contexto completo para processors.plantilla_familia.renderizar."""
    hoy = hoy or date.today()
    municipio = data.get("municipio") or "Medellín"
    departamento = data.get("departamento") or "Antioquia"
    elecciones = data.get("elecciones") or {}
    opciones_usuario = data.get("opciones") or {}

    # ── Clases ──
    clases = data.get("clases") or [
        {"codigo": "A", "denominacion": "Acciones de fundadores",
         "naturaleza": "acciones privilegiadas con voto múltiple", "votos_por_accion": 10},
        {"codigo": "B", "denominacion": "Acciones ordinarias",
         "naturaleza": "acciones ordinarias", "votos_por_accion": 1},
    ]
    if not 1 <= len(clases) <= 3:
        raise DatosFamiliaError("La sociedad debe tener entre una y tres clases de acciones.")
    codigos = [c["codigo"] for c in clases]
    if len(set(codigos)) != len(codigos):
        raise DatosFamiliaError("Los códigos de clase no pueden repetirse.")

    # ── Capital y suscripciones ──
    nominal = int(data.get("valor_nominal") or 1000)
    autorizado = int(data.get("capital_autorizado") or 1_000_000_000)
    suscrito = int(data.get("capital_suscrito") or 0)
    accionistas = data.get("accionistas") or []
    if not accionistas:
        raise DatosFamiliaError("Debe haber al menos un accionista.")
    if suscrito <= 0 or suscrito % nominal or autorizado % nominal or autorizado < suscrito:
        raise DatosFamiliaError("Revise el capital: autorizado ≥ suscrito > 0, múltiplos del valor nominal.")
    if abs(sum(float(a.get("porcentaje") or 0) for a in accionistas) - 100) > 0.01:
        raise DatosFamiliaError("Los porcentajes de los accionistas deben sumar 100 %.")

    suscripciones, pagado_total, acciones_total = [], 0, 0
    for a in accionistas:
        clase = a.get("clase") or codigos[0]
        if clase not in codigos:
            raise DatosFamiliaError(f"{a.get('nombre')}: la clase {clase} no existe.")
        capital_acc = round(suscrito * float(a["porcentaje"]) / 100 / nominal) * nominal
        pagado_acc = min(int(a.get("capital_pagado_num", capital_acc) or 0), capital_acc)
        acciones = capital_acc // nominal
        pagado_total += pagado_acc
        acciones_total += acciones
        tipo, num = (("NIT", a.get("id_num")) if a.get("tipo") == "juridica"
                     else _persona_doc(a))
        saldo = capital_acc - pagado_acc
        suscripciones.append({
            "accionista_nombre": a["nombre"].upper(),
            "accionista_documento": f"{tipo} {num}",
            "clase": clase,
            "numero_acciones": _miles(acciones),
            "capital_suscrito": _miles(capital_acc),
            "capital_pagado": _miles(pagado_acc),
            "saldo": _miles(saldo),
            "porcentaje_capital": _pct(a["porcentaje"]),
            "prima_detalle": "no hay prima de emisión",
            "aporte_detalle": "aporte en dinero",
            "calendario_pago": ("dentro de los dos (2) años siguientes a la fecha de "
                                "suscripción, en dinero" if saldo else
                                "no aplica, el aporte se paga en su totalidad"),
        })
    if acciones_total * nominal != suscrito:
        raise DatosFamiliaError("La distribución de acciones no cuadra con el capital suscrito; "
                                "ajuste los porcentajes para que den acciones enteras.")
    clases_iniciales = [c for c in codigos if any(s["clase"] == c for s in suscripciones)]

    # ── Dividendos por escenarios ──
    escenarios = data.get("escenarios") or escenarios_por_defecto(codigos)
    _validar_escenarios(codigos, escenarios)

    # ── Constituyentes y firmantes ──
    constituyentes, firmantes = [], []
    for a in accionistas:
        if a.get("tipo") == "juridica":
            constituyentes.append({
                "nombre": a["nombre"].upper(), "tipo_persona": "persona jurídica",
                "nacionalidad": a.get("nacionalidad") or "colombiana",
                "tipo_documento": "NIT", "numero_documento": a.get("id_num", ""),
                "domicilio": a.get("domicilio") or municipio,
                "calidad_actuacion": "por intermedio de su representante legal",
                "representacion_soporte": (
                    f"{(a.get('rl_nombre') or '').upper()}, identificado(a) con C.C. "
                    f"{a.get('rl_cc', '')}, según el certificado de existencia y "
                    f"representación legal"),
            })
            firmantes.append({"nombre": (a.get("rl_nombre") or "").upper(), "tipo_documento": "C.C.",
                              "numero_documento": a.get("rl_cc", ""),
                              "calidad": "representante legal de accionista constituyente",
                              "representado": a["nombre"].upper()})
        else:
            tipo, num = _persona_doc(a)
            constituyentes.append({
                "nombre": a["nombre"].upper(), "tipo_persona": "persona natural",
                "nacionalidad": a.get("nacionalidad") or "colombiana",
                "tipo_documento": tipo, "numero_documento": num,
                "domicilio": a.get("domicilio") or municipio,
                "calidad_actuacion": "en nombre propio",
                "representacion_soporte": "no aplica",
            })
            firmantes.append({"nombre": a["nombre"].upper(), "tipo_documento": tipo,
                              "numero_documento": num, "calidad": "accionista constituyente",
                              "representado": "no aplica"})

    # ── Nombramientos ──
    nombramientos, ya_firman = [], {f["numero_documento"] for f in firmantes}

    def nombrar(cargo, p, num_key, tipo_key="tipo_doc", tarjeta="no aplica"):
        tipo, num = _persona_doc(p, num_key, tipo_key)
        nombramientos.append({
            "cargo": cargo, "nombre": (p.get("nombre") or "").upper(),
            "tipo_documento": tipo, "numero_documento": num,
            "domicilio": p.get("domicilio") or p.get("expedicion") or municipio,
            "tarjeta_profesional": tarjeta,
            "aceptacion_soporte": "mediante la firma del presente documento",
        })
        if num not in ya_firman:
            ya_firman.add(num)
            firmantes.append({"nombre": (p.get("nombre") or "").upper(), "tipo_documento": tipo,
                              "numero_documento": num, "calidad": f"acepta el cargo de {cargo}",
                              "representado": "no aplica"})

    principales = [r for r in (data.get("rl_principales") or []) if r and r.get("nombre")]
    suplentes = [r for r in (data.get("rl_suplentes") or []) if r and r.get("nombre")]
    if not principales:
        raise DatosFamiliaError("Debe designarse el representante legal principal.")
    for r in principales:
        nombrar("representante legal principal", r, "cc")
    for r in suplentes:
        nombrar("representante legal suplente", r, "cc")
    junta = data.get("junta_directiva") if opciones_usuario.get("junta_directiva") else None
    for m in (junta or {}).get("principales") or []:
        nombrar("miembro principal de junta directiva", m, "id_num")
    for m in (junta or {}).get("suplentes") or []:
        nombrar("miembro suplente de junta directiva", m, "id_num")
    rf = data.get("revisor_fiscal")
    if rf:
        if rf.get("tipo") == "juridica":
            nombrar("revisor fiscal", {"nombre": rf.get("contador_nombre"),
                                       "tipo_doc": rf.get("contador_tipo_doc"),
                                       "id_num": rf.get("contador_id_num")},
                    "id_num", tarjeta=rf.get("contador_tarjeta_profesional", ""))
        else:
            nombrar("revisor fiscal", rf, "id_num", tarjeta=rf.get("tarjeta_profesional", ""))
    situacion = _lista([
        "representante legal suplente: " + ("designado" if suplentes else "vacante"),
        "revisor fiscal: " + ("designado" if rf else "no se designa al constituirse"),
    ])

    # ── Opciones ──
    opciones = {
        "objeto_amplio": bool(opciones_usuario.get("objeto_amplio")),
        "aportes_especie": False,
        "dividendos_preferenciales_o_fijos": False,
        "prohibicion_temporal": bool(opciones_usuario.get("prohibicion_temporal")),
        "autorizacion_transferencias": bool(opciones_usuario.get("autorizacion_transferencias")),
        "conversion_por_transferencia": bool(opciones_usuario.get("conversion_por_transferencia")) and len(codigos) > 1,
        "preferencia_suscripcion": opciones_usuario.get("preferencia_suscripcion", True),
        "preferencia_transferencia": opciones_usuario.get("preferencia_transferencia", True),
        "junta_directiva": bool(junta and junta.get("principales")),
        "consejo_familia": bool(opciones_usuario.get("consejo_familia")),
        "arbitraje": bool(opciones_usuario.get("arbitraje")),
        "protocolo_familia": bool(opciones_usuario.get("protocolo_familia")),
        "revisor_fiscal_inicial": bool(rf),
        "poder_tramites": bool(data.get("apoderado")),
        # Diferidos hasta revisión jurídica
        "opcion_compra": False,
        "exclusion": False,
    }

    grupo = elecciones.get("grupo_familiar") or "amplio"
    if grupo == "personalizado":
        definicion_grupo = (elecciones.get("grupo_personalizado") or "").strip().rstrip(".")
        if not definicion_grupo:
            raise DatosFamiliaError("Escriba la definición personalizada de grupo familiar.")
    else:
        definicion_grupo = GRUPO_FAMILIAR.get(grupo, GRUPO_FAMILIAR["amplio"])

    escalonado = elecciones.get("preferencia") == "escalonado" and len(codigos) > 1
    orden_suscripcion = (
        "por turnos sucesivos según la clase: " + _lista(
            [f"primero los titulares de la clase {codigos[0]}"]
            + [f"luego los de la clase {c}" for c in codigos[1:]])
        + ", a prorrata dentro de cada turno"
        if escalonado else
        "un único turno, proporcional entre todos los accionistas según su "
        "participación en el capital suscrito")
    orden_transferencia = (
        "1) la sociedad; 2) " + _lista([f"los titulares de la clase {c}" for c in codigos])
        + ", en ese orden y a prorrata dentro de cada clase"
        if escalonado else
        "1) la sociedad; 2) los demás accionistas, a prorrata de su participación")

    limite_rl = elecciones.get("limite_rl_pct", 20)
    prestamos_prohibidos = elecciones.get("prestamos", "prohibidos") == "prohibidos"
    clase_fundadores = codigos[0]

    def clase_ctx(c):
        solo_familia = c.get("solo_grupo_familiar", c["codigo"] == clase_fundadores and len(codigos) > 1)
        return {
            "codigo": c["codigo"],
            "denominacion": c.get("denominacion") or f"Acciones clase {c['codigo']}",
            "naturaleza": c.get("naturaleza") or "acciones ordinarias",
            "votos_por_accion": str(int(c.get("votos_por_accion") or 1)),
            "regimen_voto_especial": "no existen asuntos sometidos a reglas especiales de voto "
                                     "ni eventos de adquisición o recuperación del voto distintos "
                                     "de los generales de estos estatutos",
            "derechos_economicos_adicionales": "ninguno distinto del régimen de dividendos por "
                                               "escenarios de este artículo",
            "derechos_liquidacion": "proporcional al capital nominal pagado de sus acciones, sin "
                                    "preferencia adicional sobre otras clases",
            "requisitos_titularidad": (
                "ser integrante del grupo familiar definido en estos estatutos" if solo_familia else
                "los generales para ser accionista, sin requisitos especiales"),
            "derechos_especiales": "Esta clase no tiene derechos particulares adicionales",
            "aprobacion_modificacion_derechos": "el voto favorable de la totalidad de los "
                                                "titulares de la clase afectada",
        }

    ctx = {
        "sociedad": {
            "nombre_completo": data["nombre_sas"].upper(),
            "municipio": municipio, "departamento": departamento,
            "duracion_texto": data.get("duracion_texto") or "indefinida",
            "objeto_principal": OBJETO_PRINCIPAL,
            "operaciones_conexas": OPERACIONES_CONEXAS,
            "organo_sucursales": "la asamblea general de accionistas",
        },
        "constitucion": {
            "lugar": f"{municipio}, {departamento}",
            "fecha": _fecha_literal(hoy),
            "instrumento": "documento privado",
        },
        "constituyentes": constituyentes,
        "capital": {
            "autorizado": _miles(autorizado),
            "autorizado_letras": _numero_a_letras(autorizado),
            "acciones_autorizadas": _miles(autorizado // nominal),
            "valor_nominal": _miles(nominal),
            "suscrito": _miles(suscrito),
            "acciones_suscritas": _miles(acciones_total),
            "pagado": _miles(pagado_total),
            "saldo": _miles(suscrito - pagado_total),
            "clases_iniciales": _lista([f"la clase {c}" for c in clases_iniciales]),
        },
        "clases": [clase_ctx(c) for c in clases],
        "dividendos": {
            "regimen": "reparto por escenarios de concurrencia de clases, conforme a la matriz "
                       "explícita de este artículo",
            "escenarios": [
                {"codigo": nombre, "clases_concurrentes": _lista(nombre.split("+")),
                 "asignaciones": [{"clase": c, "porcentaje": _pct(p)} for c, p in reparto.items()]}
                for nombre, reparto in escenarios.items()
            ],
            "regla_redondeo": "la asignación del residuo a la clase o accionista con mayor "
                              "participación en el escenario respectivo, dejando constancia en el acta",
            "destino_renuncias": ("su distribución entre los demás accionistas de la misma clase, "
                                  "a prorrata de su participación, en el mismo ejercicio"
                                  if elecciones.get("destino_renuncias", "clase") == "clase" else
                                  "una reserva ocasional de la sociedad"),
            "forma_plazo_pago": "en dinero efectivo, en proporción a la parte pagada de cada acción, "
                                "dentro del plazo que fije la asamblea al decretarlos",
            "no_reclamados": "su permanencia en la caja social, en depósito disponible a la orden "
                             "de sus titulares, sin generar intereses",
        },
        "transferencias": {
            "clases_restringidas": _lista(codigos),
            "prohibicion_anios": str(min(int(elecciones.get("prohibicion_anios") or 10), 10)),
            "clases_autorizacion": _lista(codigos),
            "criterios_admision": ("que el adquirente acredite su pertenencia al grupo familiar "
                                   "o, en su defecto, la aprobación expresa de la asamblea"),
        },
        "conversion": {
            "clase_origen": clase_fundadores,
            "titulares_habilitados": "sus titulares originales integrantes del grupo familiar",
            "evento": "la transferencia de dichas acciones a cualquier título, incluida la "
                      "adjudicación por causa de muerte",
            "clase_destino": codigos[-1],
            "relacion_canje": "una (1) acción por cada acción, con igual valor nominal",
            "momento_efectos": "el perfeccionamiento de la transferencia o de la adjudicación",
            "excepciones": "la mera constitución de un gravamen o embargo, que no produce "
                           "conversión por sí sola",
        },
        "emision": {
            "dias_comunicacion": "quince (15)",
            "plazo_oferta_texto": "no menor de quince (15) días hábiles ni superior a tres (3) "
                                  "meses calendario",
        },
        "preferencia_suscripcion": {
            "orden": orden_suscripcion,
            "procedimiento": "cada accionista aceptará dentro del plazo de la oferta; el remanente "
                             "se ofrecerá nuevamente, a prorrata, a quienes hayan aceptado",
            "negociabilidad": "el derecho será negociable únicamente entre accionistas, a prorrata "
                              "de su participación",
        },
        "preferencia_transferencia": {
            "orden": orden_transferencia,
            "eventos": "la venta, la permuta, la donación, el aporte en especie a sociedades y la "
                       "constitución de usufructo",
            "excepciones": ("la escisión o fusión, la transferencia a una sociedad matriz, filial o "
                            "subsidiaria, y la adjudicación en la liquidación de un accionista persona "
                            "jurídica a sus propios socios, siempre que en todos esos casos el "
                            "beneficiario final continúe perteneciendo al grupo familiar"),
            "equivalencia_actos_no_dinerarios": "se tomará el valor comercial del bien o derecho "
                                                "ofrecido en pago o, a falta de acuerdo, el que "
                                                "determine un perito",
            "dias_traslado": "cinco (5)", "dias_aceptacion": "quince (15)",
            "dias_acrecimiento": "diez (10)", "dias_venta_tercero": "sesenta (60)",
        },
        "mayorias": {
            "creacion_conversion_clases": SETENTA + ", sin perjuicio de las aprobaciones de clase "
                                                    "que correspondan",
            "autorizacion_transferencias": SETENTA,
            "gravamenes": SETENTA,
            "usufructo": SETENTA,
            "emision": MITAD_MAS_UNA,
            "exclusion_preferencia_suscripcion": SETENTA,
            "dispensa_preferencia_transferencia": SETENTA,
            "readquisicion": MITAD_MAS_UNA,
            "reformas": MITAD_MAS_UNA,
            "fusion_escision": MITAD_MAS_UNA,
            "enajenacion_global": MITAD_MAS_UNA,
            "reservas": "el voto favorable de la mitad más una de las acciones representadas en la reunión",
            "dividendos": "la mayoría ordinaria prevista en estos estatutos",
            "disolucion": MITAD_MAS_UNA,
        },
        "asamblea": {
            "quorum_porcentaje": "cincuenta y uno (51)",
            "operador_mayoria": "superen el",
            "mayoria_porcentaje": "cincuenta (50)",
            "dias_convocatoria": "cinco (5)", "dias_inspeccion": "cinco (5)",
            "porcentaje_solicitud_convocatoria": "diez (10)",
            "medios_convocatoria": "comunicación escrita física o electrónica",
            "medios_inspeccion_adicionales": "medios electrónicos seguros",
            "plazo_reunion_ordinaria": "los tres (3) primeros meses de cada año",
            "regla_fraccionamiento": "la prohibición de fraccionar el voto, salvo norma imperativa",
        },
        "junta": {
            "numero_principales": str(len((junta or {}).get("principales") or [])) or "0",
            "regimen_suplencias": ("sus respectivos suplentes personales"
                                   if (junta or {}).get("suplentes") else "sin suplentes"),
            "sistema_eleccion": "la asamblea general de accionistas mediante el sistema de "
                                "cuociente electoral",
            "periodo": "un (1) año, con posibilidad de reelección indefinida",
            "funciones": "las que le asigne la asamblea, sin asumir las funciones indelegables de esta",
            "convocante": "el representante legal o cualquiera de sus miembros",
            "dias_convocatoria": "cinco (5)",
            "medio_convocatoria": "comunicación escrita física o electrónica",
            "quorum": "la mayoría de sus miembros",
            "mayoria": "la mayoría de los miembros presentes",
            "reglas_funcionamiento": "reuniones ordinarias al menos una vez cada tres (3) meses, "
                                     "actas firmadas por presidente y secretario y, en caso de "
                                     "empate, voto dirimente del presidente de la junta",
        },
        "familia": {
            "definicion_grupo": definicion_grupo,
            "integracion_consejo": "los accionistas mayores de edad integrantes del grupo familiar",
            "periodo_consejo": "dos (2) años",
            "funcionamiento_consejo": "las que el propio consejo adopte en su reglamento",
            "funciones_consejo": "recomendar sobre la política de dividendos, el ingreso de nuevas "
                                 "generaciones y el protocolo de familia",
            "materias_protocolo": "gobierno corporativo familiar, ingreso y salida de familiares "
                                  "como accionistas o empleados, política de dividendos y educación "
                                  "patrimonial de las siguientes generaciones",
        },
        "decisiones_reservadas": [] if len(codigos) == 1 else [{
            "materia": "reformas estatutarias que modifiquen los derechos de la clase, fusión, "
                       "escisión y emisiones que diluyan su participación",
            "clases": clase_fundadores,
            "aprobacion": "el voto favorable de la totalidad de los titulares de la clase protegida",
            "regla_sin_clase": "la mayoría general aplicable, sin aprobación adicional",
        }],
        "representacion": {
            "denominacion_cargo": "un representante legal",
            "organo_designacion": "la asamblea general de accionistas",
            "periodo": "un (1) año",
            "regimen_suplencias": "suplencias personales y opcionales: cada suplente reemplaza al "
                                  "principal en sus faltas absolutas, temporales o accidentales",
            "facultades_suplentes": "las mismas del principal cuando actúen en su reemplazo",
            "organo_autorizacion": "la asamblea general de accionistas",
            "operaciones_reservadas": (
                f"adquirir, enajenar o gravar activos por un valor superior al "
                f"{_numero_a_letras(int(limite_rl))} por ciento ({int(limite_rl)} %) del patrimonio "
                f"líquido de la sociedad y otorgar garantías a favor de terceros"
                if limite_rl else
                "la fusión, la escisión y la enajenación global de activos"),
            "limite_cuantia": ("la acumulación de las operaciones relacionadas celebradas dentro de "
                               "un mismo ejercicio" if limite_rl else "sin límite de cuantía"),
            "politica_prestamos_garantias": (
                "se prohíbe a la sociedad otorgar préstamos a accionistas o administradores y "
                "avalar, afianzar o garantizar sus obligaciones personales" if prestamos_prohibidos else
                "se permiten previa autorización de la asamblea con " + MITAD_MAS_UNA),
        },
        "revisoria": {"periodo": "un (1) año, pudiendo ser reelegido",
                      "suplencia": "el suplente, cuando se designe, reemplazará al principal en sus "
                                   "faltas absolutas, temporales o accidentales"},
        "reservas": {"regimen": "no será obligatoria la apropiación de reserva legal, sin perjuicio "
                                "de las reservas de normas especiales aplicables",
                     "parametros": "no aplica"},
        "liquidacion": {"causales_adicionales": "ninguna distinta de las legales"},
        "controversias": {
            "dias_arreglo": "treinta (30)", "numero_arbitros": "un (1)",
            "centro_arbitraje": f"el Centro de Conciliación y Arbitraje de la Cámara de Comercio de "
                                f"{data.get('camara_ciudad') or municipio}",
            "sede": municipio, "dias_designacion": "cinco (5)",
        },
        "nombramientos": nombramientos,
        "nombramientos_situacion_inicial": situacion,
        "suscripciones": suscripciones,
        "firmantes": firmantes,
        "opciones": opciones,
    }

    # El bloque de conversión repite cada regla; en esta versión hay una sola
    ctx["conversiones"] = [ctx.pop("conversion")] if opciones["conversion_por_transferencia"] else []

    ap = data.get("apoderado")
    if ap and ap.get("nombre"):
        ctx["poder"] = {
            "poderdantes": "Los constituyentes",
            "apoderado_nombre": ap["nombre"].upper(),
            "apoderado_documento": f"{_label_tipo_doc(ap.get('id_tipo'))} {ap.get('id_num', '')}",
            "facultades": "adelantar los trámites de constitución e inscripción ante la cámara de "
                          "comercio, la obtención del RUT ante la DIAN, la inscripción de libros y la "
                          "declaración de situación de control",
            "vencimiento": "doce (12) meses contados desde la fecha de este documento",
            "sustitucion": "el apoderado podrá sustituir y reasumir el poder",
        }
    return ctx
