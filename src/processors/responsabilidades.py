# -*- coding: utf-8 -*-
"""
Armado del anexo de responsabilidades tributarias de una S.A.S.

Unas van siempre —las del régimen elegido y las comunes a toda sociedad— y
el usuario puede agregar otras. Nunca se ofrece una que ya esté incluida, ni
una excluyente con lo ya seleccionado, ni una que las sociedades no puedan
llevar o que exija resolución previa de la DIAN.

Algunas dependen de la actividad: si el CIIU o el objeto social las delatan
—combustibles, plásticos de un solo uso, bebidas azucaradas, restaurantes—
se marcan como sugeridas para que el usuario las vea primero.

Las de comercio exterior (obligado aduanero, exportador de exentos, ingreso o
salida de divisas) obligan a declarar en qué calidad actuará la sociedad, y
esa respuesta marca la casilla correspondiente del formulario RUES.

Fuente de las reglas: casilla 53 del RUT contrastada con la guía de la Cámara
de Comercio de Medellín (ver data/responsabilidades_tributarias.json).
"""
import json
import os
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
RUTA = os.path.join(BASE_DIR, "data", "responsabilidades_tributarias.json")

_cache = None


def cargar():
    global _cache
    if _cache is None:
        with open(RUTA, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def maximo_anexo():
    """Filas que tiene el anexo impreso de la Cámara."""
    return cargar().get("maximo_anexo", 10)


def _sin_tildes(texto):
    nfkd = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _catalogo():
    """Índice código -> definición de todas las adicionales."""
    return {r["codigo"]: r for r in cargar()["adicionales"]}


def predeterminadas(regimen, incluir_consumo=False, adicionales=None):
    """Responsabilidades que van siempre, según el régimen elegido.

    `incluir_consumo` viene de la actividad económica: si el CIIU o el objeto
    social indican un hecho generador del INC se agrega la 33 — salvo en
    Régimen Simple, que ya lo integra.

    `adicionales` se mira solo para aplicar reemplazos: la 53 (persona
    jurídica no responsable de IVA) sustituye a la 48, no se suma a ella.
    """
    datos = cargar()
    reg = datos["por_regimen"].get(regimen) or datos["por_regimen"]["ordinario"]
    lista = [(reg["codigo"], reg["nombre"])]
    lista += [(r["codigo"], r["nombre"]) for r in datos["base_sociedad"]]

    if incluir_consumo and regimen != "simple":
        consumo = _catalogo()["33"]
        lista.append((consumo["codigo"], consumo["nombre"]))

    # Reemplazos: una adicional puede sustituir a una de base
    catalogo = _catalogo()
    sustituidos = set()
    for codigo in (adicionales or []):
        regla = catalogo.get(str(codigo).strip().zfill(2))
        if regla:
            sustituidos.update(regla.get("reemplaza") or [])
    if sustituidos:
        lista = [(c, n) for c, n in lista if c not in sustituidos]

    return sorted(lista, key=lambda x: int(x[0]))


def cupo_adicionales(regimen, incluir_consumo=False, adicionales=None):
    """Cuántas adicionales caben todavía en el anexo."""
    fijas = len(predeterminadas(regimen, incluir_consumo, adicionales))
    return max(0, maximo_anexo() - fijas)


def _sugerida(regla, ciiu_codes, objeto_social):
    """¿La actividad declarada delata esta responsabilidad?"""
    cond = regla.get("sugerida_si")
    if not cond:
        return False
    codigos = [str(c)[:4] for c in (ciiu_codes or []) if c]
    if any(c in (cond.get("ciiu") or []) for c in codigos):
        return True
    texto = _sin_tildes(objeto_social)
    return any(_sin_tildes(t) in texto for t in (cond.get("terminos") or []))


def disponibles(regimen, incluir_consumo=False, ciiu_codes=None, objeto_social="",
                adicionales=None):
    """
    Adicionales que el usuario puede marcar, ya descontadas las que van por
    defecto y las incompatibles con el régimen.

    Cada una viene con `sugerida` para que la interfaz destaque las que la
    actividad declarada hace probables.
    """
    datos = cargar()
    ya_incluidas = {c for c, _ in predeterminadas(regimen, incluir_consumo, adicionales)}
    reg_codigo = datos["por_regimen"].get(
        regimen, datos["por_regimen"]["ordinario"])["codigo"]

    salida = []
    for r in datos["adicionales"]:
        if r["codigo"] in ya_incluidas:
            continue                      # no se ofrece lo que ya está
        if reg_codigo in (r.get("incompatible_con") or []):
            continue                      # excluyente con el régimen elegido
        salida.append({
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "descripcion": r.get("descripcion", ""),
            "sugerida": _sugerida(r, ciiu_codes, objeto_social),
            "requiere": r.get("requiere") or [],
            "reemplaza": r.get("reemplaza") or [],
            "comercio_exterior": bool(r.get("comercio_exterior")),
            # Para que la interfaz suelte la contraria al marcar una, en vez
            # de dejar al usuario chocar contra el error al final.
            "excluye": [
                c for c in (datos["excluyentes"].get(r["codigo"]) or [])
                if c != reg_codigo
            ],
            "fundamento": r.get("fundamento") or [],
        })
    # Primero las que la actividad sugiere
    salida.sort(key=lambda r: (not r["sugerida"], int(r["codigo"])))
    return salida


def no_seleccionables():
    """Las que no se ofrecen nunca, con el motivo, para poder explicarlo."""
    return cargar()["no_seleccionables"]


def config_comercio_exterior():
    """Pregunta y casillas del RUES para la calidad ante la DIAN."""
    return cargar()["comercio_exterior"]


def exige_comercio_exterior(responsabilidades):
    """
    ¿Alguna de las responsabilidades elegidas obliga a declarar la calidad de
    importador, exportador o usuario aduanero?

    Recibe la lista final (código, nombre) o una lista de códigos.
    """
    catalogo = _catalogo()
    codigos = [r[0] if isinstance(r, (list, tuple)) else str(r)
               for r in (responsabilidades or [])]
    return [c for c in codigos
            if (catalogo.get(c) or {}).get("comercio_exterior")]


def casillas_rues_comercio_exterior(perfil):
    """
    Traduce el perfil declarado a las casillas del formulario RUES.

    `perfil` es una lista de ids ('importador', 'exportador', 'usuario_aduanero').
    Devuelve {nombre_de_casilla: True}.
    """
    cfg = config_comercio_exterior()
    elegidas = {str(p).strip().lower() for p in (perfil or [])}
    return {
        op["casilla_rues"]: True
        for op in cfg["opciones"] if op["id"] in elegidas
    }


def construir(regimen, incluir_consumo=False, adicionales=None,
              ciiu_codes=None, objeto_social=""):
    """
    Lista final para el anexo: predeterminadas más las que marcó el usuario.

    Devuelve (responsabilidades, avisos). Las adicionales que no sean válidas
    se descartan y se informan, en lugar de colarse al documento.
    """
    datos = cargar()
    avisos = []
    marcadas = [str(c).strip().zfill(2) for c in (adicionales or [])]

    base = predeterminadas(regimen, incluir_consumo, marcadas)
    codigos = {c for c, _ in base}
    tope = maximo_anexo()

    permitidas = {r["codigo"]: r for r in
                  disponibles(regimen, incluir_consumo, ciiu_codes, objeto_social, marcadas)}
    vetadas = {r["codigo"]: r for r in datos["no_seleccionables"]}
    excluyentes = datos["excluyentes"]
    catalogo = _catalogo()

    for codigo in marcadas:
        if codigo in codigos:
            continue                      # ya estaba: no se duplica
        if codigo in vetadas:
            avisos.append(f"Responsabilidad {codigo} descartada: {vetadas[codigo]['motivo']}")
            continue
        choque = [c for c in excluyentes.get(codigo, []) if c in codigos]
        if choque:
            avisos.append(
                f"Responsabilidad {codigo} descartada: es excluyente con la "
                f"{', '.join(choque)}, que ya está incluida."
            )
            continue
        if codigo not in permitidas:
            avisos.append(f"Responsabilidad {codigo} descartada: no aplica al régimen elegido.")
            continue
        # Dependencias: la 24 y la 26 no van sin la 18
        faltan = [d for d in (catalogo[codigo].get("requiere") or [])
                  if d not in codigos and d not in marcadas]
        if faltan:
            avisos.append(
                f"Responsabilidad {codigo} descartada: requiere que también se "
                f"seleccione la {', '.join(faltan)}."
            )
            continue
        if len(base) >= tope:
            # El anexo tiene un número fijo de filas. Antes que truncar en
            # silencio un formulario tributario, se avisa cuál quedó por fuera.
            avisos.append(
                f"Responsabilidad {codigo} descartada: el anexo solo admite "
                f"{tope} responsabilidades y ya están completas."
            )
            continue
        base.append((codigo, permitidas[codigo]["nombre"]))
        codigos.add(codigo)

    return sorted(base, key=lambda x: int(x[0])), avisos
