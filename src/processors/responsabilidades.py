# -*- coding: utf-8 -*-
"""
Armado del anexo de responsabilidades tributarias de una S.A.S.

Unas van siempre —las del régimen elegido y las comunes a toda sociedad— y
el usuario puede agregar otras de una lista corta. Nunca se ofrece una que
ya esté incluida, ni una que sea excluyente con el régimen, ni una que las
sociedades no puedan llevar o que exija resolución previa de la DIAN.

Fuente de las reglas: guía de la Cámara de Comercio de Medellín para
Antioquia, V.01 2024 (ver data/responsabilidades_tributarias.json).
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
RUTA = os.path.join(BASE_DIR, "data", "responsabilidades_tributarias.json")

_cache = None


def cargar():
    global _cache
    if _cache is None:
        with open(RUTA, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def predeterminadas(regimen, incluir_consumo=False):
    """Responsabilidades que van siempre, según el régimen elegido.

    `incluir_consumo` viene de la actividad económica: si el CIIU o el objeto
    social indican expendio de comidas y bebidas u otro hecho generador del
    INC, se agrega la 33 — salvo en Régimen Simple, que ya lo integra.
    """
    datos = cargar()
    reg = datos["por_regimen"].get(regimen) or datos["por_regimen"]["ordinario"]
    lista = [(reg["codigo"], reg["nombre"])]
    lista += [(r["codigo"], r["nombre"]) for r in datos["base_sociedad"]]

    if incluir_consumo and regimen != "simple":
        consumo = next(r for r in datos["adicionales"] if r["codigo"] == "33")
        lista.append((consumo["codigo"], consumo["nombre"]))

    return sorted(lista, key=lambda x: int(x[0]))


def disponibles(regimen, incluir_consumo=False):
    """
    Adicionales que el usuario puede marcar, ya descontadas las que van por
    defecto y las incompatibles con el régimen.
    """
    datos = cargar()
    ya_incluidas = {c for c, _ in predeterminadas(regimen, incluir_consumo)}
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
        })
    return salida


def no_seleccionables():
    """Las que no se ofrecen nunca, con el motivo, para poder explicarlo."""
    return cargar()["no_seleccionables"]


def maximo_anexo():
    """Filas que tiene el anexo impreso de la Cámara."""
    return cargar().get("maximo_anexo", 10)


def cupo_adicionales(regimen, incluir_consumo=False):
    """Cuántas adicionales caben todavía en el anexo."""
    return max(0, maximo_anexo() - len(predeterminadas(regimen, incluir_consumo)))


def construir(regimen, incluir_consumo=False, adicionales=None):
    """
    Lista final para el anexo: predeterminadas más las que marcó el usuario.

    Devuelve (responsabilidades, avisos). Las adicionales que no sean válidas
    se descartan y se informan, en lugar de colarse al documento.
    """
    datos = cargar()
    avisos = []
    base = predeterminadas(regimen, incluir_consumo)
    codigos = {c for c, _ in base}
    tope = maximo_anexo()

    permitidas = {r["codigo"]: r for r in disponibles(regimen, incluir_consumo)}
    vetadas = {r["codigo"]: r for r in datos["no_seleccionables"]}
    excluyentes = datos["excluyentes"]

    for codigo in (adicionales or []):
        codigo = str(codigo).strip().zfill(2)
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
