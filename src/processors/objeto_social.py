# -*- coding: utf-8 -*-
"""
Generador inteligente de objeto social para estatutos S.A.S.

Toma el codigo CIIU principal (y opcionalmente secundario), la descripcion
proporcionada por el usuario, y genera un objeto social profesional y completo
para los estatutos de constitucion.

Estrategia:
1. Si el usuario ya escribio un objeto social largo (>200 chars), se usa tal cual.
2. Si hay API de Claude disponible, se genera con IA un objeto social profesional.
3. Si Claude no esta disponible (sin key, error, timeout), se usa el generador
   deterministico como fallback.
"""
import os
import logging

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# CLAUDE API INTEGRATION
# ════════════════════════════════════════════════════════════════

_anthropic_client = None


def _get_client():
    """Lazy-init del cliente Anthropic. Retorna None si no hay API key."""
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxxx"):
        return None

    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
        return _anthropic_client
    except Exception as e:
        logger.warning(f"No se pudo inicializar cliente Anthropic: {e}")
        return None


SYSTEM_PROMPT_OBJETO = """Eres un abogado experto en derecho societario colombiano, especializado en la constitución de Sociedades por Acciones Simplificadas (S.A.S.) ante las Cámaras de Comercio de Colombia.

Tu tarea es redactar el OBJETO SOCIAL para los estatutos de constitución de una S.A.S. El objeto social debe:

1. **Iniciar** con "La sociedad tendrá como objeto social principal" seguido de la actividad económica principal del código CIIU.
2. **Incluir** actividades complementarias y conexas típicas del sector, redactadas en estilo jurídico societario colombiano.
3. **Si hay un CIIU secundario**, integrarlo de forma natural en el texto.
4. **Si el usuario proporcionó una descripción breve**, REESCRIBIRLA e integrarla profesionalmente (ver reglas abajo).
5. **Cerrar siempre** con la cláusula catch-all: "Asimismo, la sociedad podrá llevar a cabo, en general, todas las actividades lícitas de comercio que guarden relación directa o indirecta con el objeto social descrito, incluyendo aquellas actividades accesorias, complementarias o conexas que sean necesarias o convenientes para el cumplimiento de su objeto social principal."
6. **Incluir** las actividades universales: celebración de toda clase de actos y contratos civiles y comerciales; importación y exportación de bienes y servicios; participación como socia o accionista en otras sociedades; adquisición, enajenación, administración y gravamen de bienes muebles e inmuebles.

⚠️ INTEGRACIÓN DEL TEXTO DEL USUARIO (regla crítica):

NO insertes nunca el texto del usuario palabra por palabra con "incluyendo …". Debes REESCRIBIRLO:

- Conéctalo con la actividad principal del CIIU usando la fórmula:
    "[...descripción CIIU principal...], particularmente se dedicará a [texto reescrito en infinitivo]"
- Convierte verbos conjugados a infinitivos para que fluya:
    • "será un restaurante de X"   → "operar un restaurante de X"
    • "venderá productos X"        → "vender productos X"
    • "fabricará Y"                 → "fabricar Y"
    • "ofrecerá servicios Z"       → "ofrecer servicios Z"
    • "funcionará como W"          → "operar como W"
- Si el usuario es informal, reescríbelo en lenguaje jurídico formal manteniendo su intención.
- Corrige errores ortográficos del usuario (ej. "tematico" → "temático", "harry potter" → "Harry Potter").
- Si el negocio referencia una marca, saga, franquicia o IP (Harry Potter, Marvel, Disney, etc.), usa frases como "temático de la saga X", "inspirado en X", "con temática X" — NO afirmes propiedad o afiliación.

EJEMPLO CORRECTO:
- CIIU principal: 5611 Expendio a la mesa de comidas preparadas
- Usuario escribió: "será un restaurante temático de Harry Potter que venderá comidas y bebidas tributo a la saga de ficción"
- Apertura correcta: "La sociedad tendrá como objeto social principal el expendio a la mesa de comidas preparadas, particularmente se dedicará a operar un restaurante temático inspirado en la saga Harry Potter que venderá comidas y bebidas tributo a dicha saga de ficción."

EJEMPLO INCORRECTO (NO HACER):
- "...comidas preparadas, incluyendo la será un restaurante temático..."  ← rompe gramática
- "...comidas preparadas, incluyendo será un restaurante..."              ← cuelga el verbo
- "...comidas preparadas, incluyendo será restaurante de Harry Potter..."   ← repite verbo conjugado

Reglas de estilo:
- Usar lenguaje jurídico formal colombiano pero claro.
- Las actividades se separan con punto y coma (;).
- La última actividad antes del cierre se introduce con "; y".
- NO usar viñetas ni numerales. Es un solo párrafo continuo.
- NO incluir "Objeto social:" al inicio — solo el texto del párrafo.
- Extensión: entre 400 y 800 palabras.
- Usar lenguaje inclusivo donde sea posible sin forzar.
- Las actividades complementarias deben ser coherentes con el sector económico real.
"""


def _generar_con_claude(ciiu_code, ciiu_desc, ciiu_code_sec="", ciiu_desc_sec="", texto_usuario=""):
    """Genera objeto social usando Claude Sonnet. Retorna None si falla."""
    client = _get_client()
    if client is None:
        return None

    user_msg = f"Código CIIU principal: {ciiu_code} — {ciiu_desc}\n"
    if ciiu_code_sec and ciiu_desc_sec:
        user_msg += f"Código CIIU secundario: {ciiu_code_sec} — {ciiu_desc_sec}\n"
    if texto_usuario:
        user_msg += f"\nDescripción adicional del usuario: {texto_usuario}\n"
    user_msg += "\nRedacta el objeto social completo."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT_OBJETO,
            messages=[{"role": "user", "content": user_msg}],
        )
        texto = response.content[0].text.strip()

        # Validar que el resultado es razonable
        if len(texto) < 200:
            logger.warning("Respuesta de Claude demasiado corta, usando fallback")
            return None

        # Asegurar que empieza con el formato correcto
        if not texto.lower().startswith("la sociedad"):
            texto = "La sociedad tendrá como objeto social principal " + texto

        return texto

    except Exception as e:
        logger.warning(f"Error al generar objeto social con Claude: {e}")
        return None


# ════════════════════════════════════════════════════════════════
# GENERADOR DETERMINISTICO (FALLBACK)
# ════════════════════════════════════════════════════════════════

COMPLEMENTARIAS_POR_DIVISION = {
    "01": [
        "la comercialización de productos agrícolas y pecuarios",
        "la importación y exportación de insumos agrícolas y productos del campo",
        "la prestación de servicios de asistencia técnica agropecuaria",
    ],
    "02": [
        "la explotación y comercialización de productos forestales y maderables",
        "la reforestación y conservación de recursos naturales",
    ],
    "03": [
        "la comercialización de productos pesqueros y acuícolas",
        "el procesamiento y conservación de pescado y mariscos",
    ],
    "05": ["la comercialización de minerales y materiales de construcción"],
    "06": ["la comercialización de hidrocarburos y sus derivados"],
    "07": ["la comercialización de minerales metálicos y no metálicos"],
    "08": ["la explotación y comercialización de materiales de construcción"],
    "09": ["la prestación de servicios de apoyo a la minería y extracción"],
    "10": [
        "la elaboración, transformación, distribución y comercialización de productos alimenticios",
        "la importación y exportación de materias primas e insumos para la industria alimentaria",
    ],
    "11": [
        "la elaboración y comercialización de bebidas",
        "la distribución y venta al por mayor y al detal de bebidas",
    ],
    "13": [
        "la fabricación y comercialización de productos textiles",
        "la importación y exportación de materias primas textiles y confecciones",
    ],
    "14": [
        "el diseño, confección y comercialización de prendas de vestir",
        "la importación y exportación de prendas de vestir y accesorios de moda",
    ],
    "15": [
        "la fabricación y comercialización de calzado y artículos de cuero",
        "la importación y exportación de materias primas y productos terminados del sector cuero",
    ],
    "20": [
        "la fabricación y comercialización de sustancias y productos químicos",
        "la importación y exportación de insumos químicos e industriales",
    ],
    "22": [
        "la fabricación y comercialización de productos de caucho y plástico",
        "la importación y exportación de materias primas plásticas y sus derivados",
    ],
    "23": [
        "la fabricación y comercialización de productos minerales no metálicos",
        "la producción y venta de materiales de construcción",
    ],
    "25": [
        "la fabricación, ensamble y comercialización de productos metálicos",
        "la prestación de servicios de metalmecánica y soldadura industrial",
    ],
    "26": [
        "la fabricación y comercialización de productos electrónicos y tecnológicos",
        "la importación y distribución de componentes electrónicos",
    ],
    "27": [
        "la fabricación y comercialización de aparatos y equipo eléctrico",
        "la importación y distribución de equipos eléctricos e industriales",
    ],
    "28": [
        "la fabricación y comercialización de maquinaria y equipo",
        "la prestación de servicios de mantenimiento y reparación de maquinaria industrial",
    ],
    "29": [
        "la fabricación, ensamble y comercialización de vehículos automotores y sus partes",
        "la importación y distribución de autopartes y accesorios vehiculares",
    ],
    "31": [
        "la fabricación y comercialización de muebles y accesorios para el hogar",
        "el diseño y producción de mobiliario para oficinas y espacios comerciales",
    ],
    "32": [
        "la fabricación y comercialización de artículos diversos",
        "la importación y exportación de productos manufacturados",
    ],
    "41": [
        "la construcción, remodelación y adecuación de edificaciones residenciales y no residenciales",
        "la promoción, gerencia y desarrollo de proyectos inmobiliarios",
        "la compraventa de bienes inmuebles",
    ],
    "42": [
        "la construcción de obras de ingeniería civil",
        "la interventoría y consultoría en proyectos de infraestructura",
    ],
    "43": [
        "la ejecución de actividades especializadas para la construcción",
        "la instalación de redes eléctricas, hidráulicas y sanitarias",
        "la demolición, preparación y acondicionamiento de terrenos",
    ],
    "45": [
        "la compraventa, importación, exportación y distribución de vehículos automotores, motocicletas, repuestos y accesorios",
        "la prestación de servicios de mantenimiento y reparación de vehículos",
    ],
    "46": [
        "la compraventa, importación, exportación y distribución al por mayor de toda clase de bienes, mercancías y productos",
        "la representación comercial de casas nacionales y extranjeras",
        "la intermediación y corretaje comercial",
    ],
    "47": [
        "la compraventa y comercialización al por menor de toda clase de bienes, mercancías y productos",
        "la operación de establecimientos de comercio",
        "la comercialización de productos a través de medios electrónicos y plataformas digitales",
    ],
    "49": [
        "la prestación de servicios de transporte terrestre de carga y pasajeros",
        "la operación logística, almacenamiento y distribución de mercancías",
    ],
    "50": [
        "la prestación de servicios de transporte acuático",
        "la operación logística y portuaria",
    ],
    "51": [
        "la prestación de servicios de transporte aéreo de pasajeros y carga",
    ],
    "52": [
        "el almacenamiento, depósito y operación logística de mercancías",
        "la prestación de servicios de agenciamiento aduanero y de carga",
    ],
    "53": [
        "la prestación de servicios postales y de mensajería",
        "la operación de servicios de courier nacional e internacional",
    ],
    "55": [
        "la prestación de servicios de alojamiento, hotelería y turismo",
        "la operación de establecimientos de hospedaje en todas sus modalidades",
    ],
    "56": [
        "la preparación, expendio y distribución de alimentos y bebidas",
        "la operación de restaurantes, cafeterías, bares y servicios de catering",
        "la prestación de servicios de alimentación institucional y eventos",
    ],
    "58": [
        "la edición, publicación y distribución de contenidos impresos y digitales",
        "el desarrollo y publicación de software y aplicaciones",
    ],
    "59": [
        "la producción, distribución y exhibición de contenidos audiovisuales y cinematográficos",
        "la producción musical y fonográfica",
    ],
    "60": [
        "la producción y emisión de contenidos de radio y televisión",
        "la operación de medios de comunicación digitales",
    ],
    "61": [
        "la prestación de servicios de telecomunicaciones",
        "la provisión de servicios de conectividad e infraestructura de redes",
    ],
    "62": [
        "el desarrollo, implementación y comercialización de software, aplicaciones y soluciones tecnológicas",
        "la consultoría en tecnologías de la información y transformación digital",
        "la prestación de servicios de soporte técnico, mantenimiento y administración de sistemas informáticos",
        "el diseño, desarrollo y operación de plataformas digitales y comercio electrónico",
    ],
    "63": [
        "la prestación de servicios de procesamiento de datos, alojamiento web y actividades conexas",
        "la operación de portales web y plataformas digitales de información",
        "la prestación de servicios de análisis de datos y business intelligence",
    ],
    "64": [
        "la intermediación financiera y la prestación de servicios monetarios",
        "la administración de fondos y vehículos de inversión",
    ],
    "65": [
        "la prestación de servicios de seguros, reaseguros y fondos de pensiones",
    ],
    "66": [
        "la prestación de servicios auxiliares a las actividades financieras y de seguros",
        "la asesoría y consultoría en inversiones y gestión de riesgos",
    ],
    "68": [
        "la compraventa, arrendamiento y administración de bienes inmuebles propios o de terceros",
        "la promoción, gerencia y desarrollo de proyectos inmobiliarios",
        "la intermediación y corretaje en negocios inmobiliarios",
        "la valoración y avalúo de bienes inmuebles",
    ],
    "69": [
        "la prestación de servicios jurídicos, de asesoría legal y representación judicial y extrajudicial",
        "la prestación de servicios de contabilidad, auditoría, revisoría fiscal y consultoría tributaria",
    ],
    "70": [
        "la consultoría empresarial, estratégica y de gestión",
        "la prestación de servicios de planeación, dirección y asesoría administrativa",
        "la administración y gestión de empresas y negocios",
    ],
    "71": [
        "la prestación de servicios de arquitectura e ingeniería y actividades conexas de consultoría técnica",
        "la realización de ensayos, análisis técnicos y certificaciones",
    ],
    "72": [
        "la investigación y el desarrollo experimental en ciencias naturales, sociales y humanidades",
        "la prestación de servicios de innovación y transferencia tecnológica",
    ],
    "73": [
        "la prestación de servicios de publicidad, mercadeo y comunicación estratégica",
        "la realización de estudios de mercado, encuestas y análisis de opinión pública",
    ],
    "74": [
        "la prestación de servicios de diseño especializado, fotografía y traducción",
        "la consultoría y asesoría empresarial en áreas especializadas",
    ],
    "75": [
        "la prestación de servicios veterinarios y de cuidado animal",
    ],
    "77": [
        "el alquiler y arrendamiento de maquinaria, equipo y bienes tangibles",
        "el leasing operativo y financiero de activos productivos",
    ],
    "78": [
        "la prestación de servicios de empleo temporal, selección y colocación de personal",
        "la administración y gestión del talento humano",
    ],
    "79": [
        "la operación de agencias de viajes y servicios de turismo",
        "la organización de eventos, convenciones y actividades turísticas",
    ],
    "80": [
        "la prestación de servicios de seguridad privada y vigilancia",
        "la consultoría en seguridad y gestión de riesgos",
    ],
    "81": [
        "la prestación de servicios de aseo, limpieza y mantenimiento de edificaciones e instalaciones",
        "la jardinería, paisajismo y mantenimiento de zonas verdes",
    ],
    "82": [
        "la prestación de servicios administrativos y de apoyo empresarial",
        "la organización de convenciones, ferias y eventos empresariales",
    ],
    "85": [
        "la prestación de servicios educativos formales y no formales en todos los niveles",
        "la capacitación, formación y entrenamiento empresarial y profesional",
        "el diseño y desarrollo de programas y contenidos educativos",
    ],
    "86": [
        "la prestación de servicios de salud humana, atención médica y hospitalaria",
        "la operación de consultorios, clínicas y centros de salud",
    ],
    "87": [
        "la prestación de servicios de atención residencial y cuidado especializado",
    ],
    "88": [
        "la prestación de servicios de asistencia social sin alojamiento",
    ],
    "90": [
        "la creación, producción y difusión de actividades artísticas y culturales",
        "la operación de espacios y equipamientos culturales",
    ],
    "91": [
        "la operación de bibliotecas, archivos, museos y otras actividades culturales",
    ],
    "92": [
        "la operación de juegos de azar y apuestas",
    ],
    "93": [
        "la prestación de servicios deportivos, recreativos y de esparcimiento",
        "la operación de instalaciones deportivas y centros de acondicionamiento físico",
    ],
    "94": [
        "la gestión y representación gremial, sindical y asociativa",
    ],
    "95": [
        "la reparación y mantenimiento de computadores, equipos de comunicación y enseres domésticos",
    ],
    "96": [
        "la prestación de servicios personales como peluquería, estética, spa y bienestar",
        "la prestación de servicios funerarios y actividades conexas",
    ],
}

ACTIVIDADES_UNIVERSALES = [
    "la celebración de toda clase de actos y contratos, civiles y comerciales, relacionados directa o indirectamente con el objeto social",
    "la importación y exportación de bienes, productos, equipos, insumos y servicios relacionados con las actividades descritas",
    "la participación como socia o accionista en otras sociedades, consorcios, uniones temporales y cualquier forma asociativa permitida por la ley",
    "la adquisición, enajenación, administración y gravamen de bienes muebles e inmuebles",
]

CLAUSULA_CATCHALL = (
    "Asimismo, la sociedad podrá llevar a cabo, en general, todas las actividades "
    "lícitas de comercio que guarden relación directa o indirecta con el objeto social "
    "descrito, incluyendo aquellas actividades accesorias, complementarias o conexas que "
    "sean necesarias o convenientes para el cumplimiento de su objeto social principal."
)


def _format_ciiu_desc(desc):
    """
    Formatea una descripcion CIIU para uso en objeto social.
    Ej: 'Actividades de desarrollo...' -> 'las actividades de desarrollo...'
        'Expendio a la mesa...' -> 'el expendio a la mesa...'
        'Construccion de edificios...' -> 'la construccion de edificios...'
    """
    desc = desc.strip().rstrip(".")
    if not desc:
        return desc
    # Lowercase first letter (unless acronym)
    words = desc.split()
    if words and not all(c.isupper() for c in words[0]):
        desc = desc[0].lower() + desc[1:]
    # Skip if already has article
    if desc.startswith(("la ", "las ", "el ", "los ")):
        return desc
    # Determine article from first word
    first = words[0].lower() if words else ""
    if first.endswith("es") or (first.endswith("s") and not first.endswith("sis")):
        return "las " + desc
    elif first in ("expendio", "cultivo", "suministro", "alojamiento",
                    "transporte", "comercio", "mantenimiento", "desarrollo",
                    "procesamiento", "almacenamiento", "arrendamiento",
                    "diseno", "diseño"):
        return "el " + desc
    else:
        return "la " + desc


def _format_user_text(texto):
    """Formatea texto breve del usuario para incluirlo como actividad."""
    texto = texto.strip().rstrip(".")
    if not texto:
        return texto
    # Lowercase if starts with uppercase and isn't an acronym
    if texto[0].isupper():
        words = texto.split()
        if words and not all(c.isupper() for c in words[0]):
            texto = texto[0].lower() + texto[1:]
    # Add article if missing
    if not texto.startswith(("la ", "las ", "el ", "los ")):
        first = texto.split()[0] if texto.split() else ""
        if first in ("restaurante", "expendio", "cultivo", "suministro",
                      "alojamiento", "transporte", "comercio", "mantenimiento",
                      "desarrollo", "procesamiento", "almacenamiento",
                      "arrendamiento", "diseno", "diseño"):
            return "el " + texto
        return "la " + texto
    return texto


# Mapa de conjugaciones de verbos en futuro 3ra persona a infinitivos.
# Usado para reescribir descripciones del usuario que comienzan con verbos
# conjugados (ej. "será un restaurante") a infinitivos ("operar un restaurante")
# que conectan naturalmente con "se dedicará a ...".
_VERBOS_FUTURO_INFINITIVO = {
    "tendrá": "tener",
    "venderá": "vender",
    "fabricará": "fabricar",
    "ofrecerá": "ofrecer",
    "desarrollará": "desarrollar",
    "operará": "operar",
    "funcionará": "funcionar",
    "comercializará": "comercializar",
    "producirá": "producir",
    "realizará": "realizar",
    "prestará": "prestar",
    "brindará": "brindar",
    "distribuirá": "distribuir",
    "importará": "importar",
    "exportará": "exportar",
    "gestionará": "gestionar",
    "administrará": "administrar",
    "construirá": "construir",
    "creará": "crear",
    "diseñará": "diseñar",
    "elaborará": "elaborar",
    "proporcionará": "proporcionar",
    "suministrará": "suministrar",
    "hará": "hacer",
    "trabajará": "trabajar",
    "atenderá": "atender",
    "manejará": "manejar",
    "organizará": "organizar",
    "ejecutará": "ejecutar",
    "transportará": "transportar",
    "alquilará": "alquilar",
    "arrendará": "arrendar",
    "comprará": "comprar",
    "venderá": "vender",
    "prestará": "prestar",
    "instalará": "instalar",
    "repararará": "reparar",
    "reparará": "reparar",
    "asesorará": "asesorar",
    "capacitará": "capacitar",
    "enseñará": "enseñar",
    "publicará": "publicar",
    "editará": "editar",
    "publicitará": "publicitar",
    "promocionará": "promocionar",
}


def _convertir_a_descripcion_natural(texto):
    """
    Convierte la descripción del usuario en una frase fluida que se conecta
    naturalmente con "particularmente se dedicará a ...".

    Casos manejados:
    - "será un restaurante de X" → "operar un restaurante de X"
    - "venderá productos X"     → "vender productos X"
    - "fabricará Y"             → "fabricar Y"
    - "operar un X" / "la venta de X" → se usa tal cual (ya es infinitivo o sustantivo)
    - "se dedicará a X"         → "X" (eliminar repetición del verbo)
    - "la sociedad se dedicará a X" / "la empresa hará X" → strip prefijo redundante
    """
    import re
    texto = texto.strip().rstrip(".")
    if not texto:
        return texto

    # Normalizar primera letra a minúscula si no es acrónimo
    if texto[0].isupper():
        palabras_check = texto.split()
        if palabras_check and not all(c.isupper() for c in palabras_check[0]):
            texto = texto[0].lower() + texto[1:]

    # ── Strip de prefijo redundante "la sociedad / la empresa / la compañía / esta sociedad" ──
    # Ej: "la sociedad se dedicará a la venta..." → "se dedicará a la venta..."
    # Ej: "la empresa será un restaurante..."     → "será un restaurante..."
    # Esto previene la duplicación cuando el objeto generado ya dice
    # "La sociedad tendrá como objeto..." y el usuario repite el sujeto.
    sujetos_redundantes = (
        r"^(la|esta|nuestra)\s+(sociedad|empresa|compañ[ií]a|firma|entidad|organizaci[oó]n)\s+"
    )
    texto = re.sub(sujetos_redundantes, "", texto, flags=re.IGNORECASE).strip()

    # Si ya empieza con "se dedicará a", quitar esa parte (la pondremos nosotros)
    for prefijo in ("se dedicará a ", "se dedicara a ",
                    "se dedicará al ", "se dedicara al "):
        if texto.startswith(prefijo):
            # "al" se convierte en infinitivo/sustantivo directamente
            resto = texto[len(prefijo):]
            if prefijo.endswith("al "):
                return resto  # "expendio de comidas..." (ya viene como sustantivo)
            return resto

    palabras = texto.split()
    if not palabras:
        return texto

    primera = palabras[0].lower()
    resto = " ".join(palabras[1:])

    # Caso especial: "será un/una X" → "operar un/una X"
    # "será" antes de un artículo o sustantivo de negocio se traduce mejor
    # como "operar" (operar un restaurante, operar una empresa).
    if primera == "será":
        resto_palabras = resto.split()
        if resto_palabras and resto_palabras[0].lower() in (
            "un", "una", "el", "la", "unos", "unas", "los", "las"
        ):
            return "operar " + resto
        # Si lo que sigue no es artículo, mantener "ser"
        return "ser " + resto if resto else "ser"

    # Verbos conjugados futuro → infinitivo
    if primera in _VERBOS_FUTURO_INFINITIVO:
        infinitivo = _VERBOS_FUTURO_INFINITIVO[primera]
        return (infinitivo + " " + resto) if resto else infinitivo

    # Si ya empieza con infinitivo o sustantivo (con o sin artículo), usar tal cual
    return texto


# ════════════════════════════════════════════════════════════════
# PULIDO JURÍDICO-FORMAL DEL TEXTO DEL USUARIO
# ════════════════════════════════════════════════════════════════

# Marcas, sagas, franquicias y propiedades intelectuales que requieren
# formulación cuidadosa para evitar implicar propiedad, afiliación o uso
# no autorizado. Se reemplaza la referencia plana ("Harry Potter") por
# una construcción descriptiva ("la saga Harry Potter") que es coherente
# con el lenguaje jurídico de objeto social.
_IPS_CONOCIDAS = {
    "harry potter": "la saga Harry Potter",
    "star wars": "la saga Star Wars",
    "el señor de los anillos": "la saga El Señor de los Anillos",
    "señor de los anillos": "la saga El Señor de los Anillos",
    "marvel": "el universo Marvel",
    "dc comics": "el universo DC Comics",
    "disney": "Disney",
    "pixar": "Pixar",
    "pokemon": "Pokémon",
    "pokémon": "Pokémon",
    "naruto": "el universo Naruto",
    "dragon ball": "Dragon Ball",
    "one piece": "One Piece",
    "game of thrones": "Game of Thrones",
    "juego de tronos": "Juego de Tronos",
    "stranger things": "Stranger Things",
    "el padrino": "El Padrino",
    "los simpsons": "Los Simpson",
    "los simpson": "Los Simpson",
    "rick y morty": "Rick y Morty",
    "breaking bad": "Breaking Bad",
}

# Correcciones ortográficas comunes (sin acento → con acento)
_CORRECCIONES_ORTOGRAFICAS = {
    # adjetivos -ático / -ática
    "tematico": "temático", "tematica": "temática",
    "tematicos": "temáticos", "tematicas": "temáticas",
    "automatico": "automático", "automatica": "automática",
    "automaticos": "automáticos", "automaticas": "automáticas",
    "dramatico": "dramático", "dramatica": "dramática",
    "informatico": "informático", "informatica": "informática",
    "informaticos": "informáticos", "informaticas": "informáticas",
    # adjetivos -ónico / -ónica
    "electronico": "electrónico", "electronica": "electrónica",
    "electronicos": "electrónicos", "electronicas": "electrónicas",
    # adjetivos -ógico / -ógica
    "tecnologico": "tecnológico", "tecnologica": "tecnológica",
    "tecnologicos": "tecnológicos", "tecnologicas": "tecnológicas",
    "logico": "lógico", "logica": "lógica",
    "biologico": "biológico", "biologica": "biológica",
    "ecologico": "ecológico", "ecologica": "ecológica",
    "psicologico": "psicológico", "psicologica": "psicológica",
    "geografico": "geográfico", "geografica": "geográfica",
    # adjetivos esdrújulos comunes
    "publico": "público", "publica": "pública",
    "publicos": "públicos", "publicas": "públicas",
    "tecnico": "técnico", "tecnica": "técnica",
    "tecnicos": "técnicos", "tecnicas": "técnicas",
    "fisico": "físico", "fisica": "física",
    "quimico": "químico", "quimica": "química",
    "basico": "básico", "basica": "básica",
    "basicos": "básicos", "basicas": "básicas",
    "clasico": "clásico", "clasica": "clásica",
    "clasicos": "clásicos", "clasicas": "clásicas",
    "magico": "mágico", "magica": "mágica",
    "magicos": "mágicos", "magicas": "mágicas",
    "tipico": "típico", "tipica": "típica",
    "tipicos": "típicos", "tipicas": "típicas",
    "academico": "académico", "academica": "académica",
    "academicos": "académicos", "academicas": "académicas",
    "domestico": "doméstico", "domestica": "doméstica",
    "domesticos": "domésticos", "domesticas": "domésticas",
    # palabras agudas / graves comunes en -ón / -ía
    "musica": "música", "trafico": "tráfico",
    "asi": "así", "ademas": "además", "tambien": "también",
    "tradicion": "tradición", "produccion": "producción",
    "operacion": "operación", "promocion": "promoción",
    "exportacion": "exportación", "importacion": "importación",
    "comunicacion": "comunicación", "educacion": "educación",
    "informacion": "información", "administracion": "administración",
    "construccion": "construcción", "investigacion": "investigación",
    "tributacion": "tributación", "facturacion": "facturación",
    "distribucion": "distribución", "atencion": "atención",
    "gestion": "gestión", "fabricacion": "fabricación",
    "ficcion": "ficción", "accion": "acción",
    "nacion": "nación", "creacion": "creación",
    "direccion": "dirección", "estacion": "estación",
    "decoracion": "decoración", "recreacion": "recreación",
    "generacion": "generación", "emocion": "emoción",
    "relacion": "relación", "innovacion": "innovación",
    "renovacion": "renovación", "transformacion": "transformación",
    "asesoria": "asesoría", "consultoria": "consultoría",
    "tecnologia": "tecnología", "tecnologias": "tecnologías",
    "categoria": "categoría", "categorias": "categorías",
    "energia": "energía", "energias": "energías",
    "estrategia": "estrategia",
    # nombres propios comunes mal escritos
    "colombia": "Colombia", "medellin": "Medellín",
    "bogota": "Bogotá", "antioquia": "Antioquia",
}


def _pulir_texto_usuario(texto):
    """
    Pule el texto del usuario para producir prosa jurídico-formal impecable.

    Acciones:
    1. Convierte verbos conjugados en futuro a infinitivos
    2. Envuelve referencias a marcas/IPs con descriptores ("la saga X")
    3. Corrige errores ortográficos comunes (sin acento → con acento)
    4. Limpia espaciado y puntuación
    """
    import re

    # 1. Convertir a infinitivo / forma natural
    texto = _convertir_a_descripcion_natural(texto)

    # 2. Reemplazar IPs/marcas conocidas con frases protectoras
    # Ordenar por longitud descendente para que "el señor de los anillos" se
    # detecte antes que "señor de los anillos".
    for ip, reemplazo in sorted(_IPS_CONOCIDAS.items(), key=lambda x: -len(x[0])):

        def _smart_replace(match, _reemplazo=reemplazo):
            # No reemplazar si ya está envuelto por una frase protectora
            start = match.start()
            contexto_previo = texto[max(0, start - 20):start].lower()
            for prefijo in (
                "la saga ", "el universo ", "la franquicia ",
                "inspirado en ", "inspirada en ", "homenaje a ",
                "tributo a ",
            ):
                if contexto_previo.endswith(prefijo):
                    return match.group(0)
            return _reemplazo

        texto = re.sub(
            r"\b" + re.escape(ip) + r"\b",
            _smart_replace,
            texto,
            flags=re.IGNORECASE,
        )

    # 3. Correcciones ortográficas (palabras enteras, case-insensitive)
    for incorrecto, correcto in _CORRECCIONES_ORTOGRAFICAS.items():
        # Preservar capitalización si la palabra original empezaba con mayúscula
        def _corregir(m, _correcto=correcto):
            original = m.group(0)
            if original[0].isupper():
                return _correcto[0].upper() + _correcto[1:]
            return _correcto

        texto = re.sub(
            r"\b" + re.escape(incorrecto) + r"\b",
            _corregir,
            texto,
            flags=re.IGNORECASE,
        )

    # 4. Contracciones gramaticales: "de el" → "del", "a el" → "al"
    texto = re.sub(r"\bde el\b", "del", texto)
    texto = re.sub(r"\bDe el\b", "Del", texto)
    texto = re.sub(r"\ba el\b", "al", texto)
    texto = re.sub(r"\bA el\b", "Al", texto)

    # 5. Limpieza de espaciado y puntuación
    texto = re.sub(r"\s+", " ", texto).strip()
    # Quitar coma o punto y coma final si quedaron pegados
    texto = re.sub(r"[,;]+\s*$", "", texto)
    texto = texto.rstrip(".")  # Sin punto final (lo añadimos al armar la frase)

    return texto


def _generar_deterministico(ciiu_code, ciiu_desc, ciiu_code_sec="", ciiu_desc_sec="", texto_usuario=""):
    """
    Genera objeto social de forma determinística con estructura profesional.

    Estructura:
    1. Apertura con actividad principal
    2. Descripción del usuario (si la hay)
    3. Actividad secundaria CIIU
    4. Bloque de actividades complementarias del sector
    5. Bloque de actividades universales
    6. Cláusula catch-all de cierre
    """
    texto = texto_usuario.strip()
    div = ciiu_code[:2] if ciiu_code else ""
    div_sec = ciiu_code_sec[:2] if ciiu_code_sec else ""

    # ─── 1. Construir actividad principal ───
    act_principal = ""
    if ciiu_desc:
        act_principal = _format_ciiu_desc(ciiu_desc)
    elif texto:
        act_principal = _format_user_text(texto)
        texto = ""  # Ya se usó

    if not act_principal:
        act_principal = "actividades comerciales lícitas"

    # ─── 2. Descripción específica del usuario y actividades secundarias ───
    descripcion_usuario = None  # Texto del usuario pulido y reformulado
    actividades_especificas = []  # Solo para CIIU secundario

    # Texto del usuario: pulir orto, IPs, verbos, etc.
    if texto and len(texto) <= 500:
        descripcion_usuario = _pulir_texto_usuario(texto)

    # Actividad secundaria CIIU
    if ciiu_desc_sec and ciiu_desc_sec != ciiu_desc:
        desc_sec = _format_ciiu_desc(ciiu_desc_sec)
        if desc_sec != act_principal:
            actividades_especificas.append(desc_sec)

    # ─── 3. Complementarias del sector ───
    complementarias = []
    for comp in COMPLEMENTARIAS_POR_DIVISION.get(div, []):
        if comp != act_principal and comp not in actividades_especificas:
            complementarias.append(comp)

    # Complementarias del sector secundario
    if div_sec and div_sec != div:
        for comp in COMPLEMENTARIAS_POR_DIVISION.get(div_sec, []):
            if comp not in complementarias and comp != act_principal and comp not in actividades_especificas:
                complementarias.append(comp)

    # ─── 4. Redacción final con estructura natural ───
    parrafos = []

    # Apertura
    apertura = f"La sociedad tendrá como objeto social principal {act_principal}"

    # Descripción específica del usuario.
    # El conector se elige según el tipo de descripción para mantener
    # coherencia gramatical y prosa fluida:
    #   - Si empieza con artículo o sustantivo: "que comprende, en particular, ..."
    #   - Si empieza con infinitivo (acción): "particularmente se dedicará a ..."
    if descripcion_usuario:
        primera = descripcion_usuario.split()[0].lower() if descripcion_usuario.split() else ""
        empieza_con_articulo = primera in ("la", "las", "el", "los", "un", "una", "unos", "unas")
        if empieza_con_articulo:
            apertura += f", que comprende, en particular, {descripcion_usuario}"
        else:
            apertura += f", particularmente se dedicará a {descripcion_usuario}"

    # Actividades secundarias (CIIU secundario)
    if actividades_especificas:
        conector = "; asimismo, " if descripcion_usuario else ", incluyendo "
        apertura += conector + actividades_especificas[0]
        for act in actividades_especificas[1:]:
            apertura += ", " + act

    apertura += "."

    parrafos.append(apertura)

    # Bloque complementario (con mejor redacción)
    if complementarias:
        intro_comp = "En desarrollo de su objeto, la sociedad podrá igualmente dedicarse "
        # Contraer "a el" → "al" para gramática correcta
        first_comp = complementarias[0]
        if first_comp.startswith("el "):
            intro_comp += "al " + first_comp[3:]
        else:
            intro_comp += "a " + first_comp
        if len(complementarias) == 1:
            intro_comp += "."
        else:
            for comp in complementarias[1:-1]:
                intro_comp += "; " + comp
            intro_comp += "; y " + complementarias[-1] + "."
        parrafos.append(intro_comp)

    # Bloque universal
    intro_univ = "De manera general, la sociedad podrá realizar "
    intro_univ += "; ".join(ACTIVIDADES_UNIVERSALES[:-1])
    intro_univ += "; y " + ACTIVIDADES_UNIVERSALES[-1] + "."
    parrafos.append(intro_univ)

    # Cláusula catch-all
    parrafos.append(CLAUSULA_CATCHALL)

    return " ".join(parrafos)


# ════════════════════════════════════════════════════════════════
# FUNCION PRINCIPAL (API PUBLICA)
# ════════════════════════════════════════════════════════════════

def generar_objeto_social(ciiu_code, ciiu_desc, ciiu_code_sec="", ciiu_desc_sec="", texto_usuario=""):
    """
    Genera un objeto social profesional para estatutos S.A.S.

    Estrategia:
    1. Si el usuario proporciono un texto extenso (>200 chars), lo respeta.
    2. Intenta generar con Claude Sonnet (si la API key esta configurada).
    3. Si Claude no esta disponible o falla, usa el generador deterministico.
    """
    texto = texto_usuario.strip()

    # Si el usuario ya redacto un objeto social largo y detallado, respetarlo
    if len(texto) > 200:
        if ("actividades lícitas" not in texto.lower()
                and "actividades licitas" not in texto.lower()
                and "objeto social" not in texto[-100:].lower()):
            texto = texto.rstrip(". ") + ". " + CLAUSULA_CATCHALL
        return texto

    # Intentar con Claude API
    resultado_claude = _generar_con_claude(
        ciiu_code, ciiu_desc, ciiu_code_sec, ciiu_desc_sec, texto_usuario
    )
    if resultado_claude:
        logger.info("Objeto social generado con Claude API")
        return resultado_claude

    # Fallback: generador deterministico
    logger.info("Objeto social generado con fallback deterministico")
    return _generar_deterministico(
        ciiu_code, ciiu_desc, ciiu_code_sec, ciiu_desc_sec, texto_usuario
    )
