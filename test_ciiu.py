# -*- coding: utf-8 -*-
"""
Pruebas del validador de CIIU para S.A.S.

Cubre las cinco categorías de decisión y, una por una, las comprobaciones
concretas que exige el informe de validación.

Ejecutar:  python test_ciiu.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from processors.ciiu_reglas import (
    evaluar, regla_de, resumen_para_listado, validar_seleccion, cargar_matriz,
)

SI = "si"
NO = "no"


def _todas(regla, valor):
    """Responde todas las preguntas de una regla con el mismo valor."""
    return {p["id"]: valor for p in regla.get("preguntas", [])}


# ════════════════════════════════════════════════════════════════
# 1. La matriz está completa y es coherente
# ════════════════════════════════════════════════════════════════
def test_matriz():
    m = cargar_matriz()
    assert m["version"] and m["revisado_el"], "la matriz debe estar versionada y fechada"
    assert m["aplica_a"] == "SAS"

    # Toda regla condicional necesita preguntas y sus dos ramas
    for r in m["reglas"]:
        if r["decision"] == "CONDITIONAL_REVIEW":
            assert r.get("preguntas"), f"{r['codigo']} condicional sin preguntas"
            assert r.get("escalamiento") and r.get("sin_escalamiento"), \
                f"{r['codigo']} condicional sin ramas de decisión"
            assert r.get("modo_escalamiento") in ("alguna", "todas"), r["codigo"]
        # Todo bloqueo explica por qué
        if r["decision"].startswith("BLOCK"):
            assert r.get("mensaje"), f"{r['codigo']} bloquea sin explicar"
            assert r.get("fundamento"), f"{r['codigo']} bloquea sin fundamento normativo"

    # Un código sin regla no restringe nada
    libre = evaluar("6201")            # desarrollo de software
    assert libre["decision"] == "ALLOWED"
    assert not libre["bloquea"]
    assert resumen_para_listado("6201") is None
    print("OK  matriz versionada, coherente y sin restringir lo no regulado")


# ════════════════════════════════════════════════════════════════
# 2. Bloqueo porque no es una sociedad mercantil
# ════════════════════════════════════════════════════════════════
def test_bloqueo_no_mercantil():
    for codigo in ["8411", "8430", "9700", "9810", "9900", "0010", "0082"]:
        r = evaluar(codigo)
        assert r["decision"] == "BLOCK_NOT_COMMERCIAL_ENTITY", (codigo, r["decision"])
        assert r["bloquea"], codigo

    # 9499 y las demás de ESAL: el informe insiste en no limitarse a 9499
    for codigo in ["9411", "9412", "9420", "9491", "9492", "9499"]:
        r = evaluar(codigo)
        assert r["bloquea"], f"{codigo} debía bloquearse en el formulario S.A.S."
        assert "sin ánimo de lucro" in r["mensaje"].lower() or \
               "sin ánimo de lucro" in (r.get("tipo_entidad_requerido") or "").lower()
    print("OK  bloqueo por naturaleza no mercantil (incluye las seis de ESAL, no solo 9499)")


# ════════════════════════════════════════════════════════════════
# 3. Bloqueo porque exige otro vehículo jurídico
# ════════════════════════════════════════════════════════════════
def test_bloqueo_no_sas():
    # Sector solidario
    for codigo, esperado in [("6424", "cooperativa"), ("6492", "fondo de empleados")]:
        r = evaluar(codigo)
        assert r["decision"] == "BLOCK_NOT_SAS", codigo
        assert r["bloquea"]
        assert esperado in r["tipo_entidad_requerido"].lower(), r["tipo_entidad_requerido"]

    # Financieras y aseguradoras vigiladas
    for codigo in ["6411", "6412", "6421", "6422", "6423", "6432", "6496",
                   "6511", "6512", "6513", "6515", "6532",
                   "6611", "6612", "6613", "6614"]:
        r = evaluar(codigo)
        assert r["decision"] == "BLOCK_NOT_SAS", (codigo, r["decision"])

    # Vigilancia privada y material de guerra
    assert evaluar("8010")["decision"] == "BLOCK_NOT_SAS"
    assert "vigilancia" in evaluar("8010")["autoridad"].lower()
    assert evaluar("2520")["decision"] == "BLOCK_NOT_SAS"
    print("OK  bloqueo por incompatibilidad de tipo societario")


# ════════════════════════════════════════════════════════════════
# 4. Un PDF nunca supera una incompatibilidad de tipo societario
# ════════════════════════════════════════════════════════════════
def test_autorizacion_no_subsana_bloqueo():
    autorizacion = {
        "regulador": "SFC", "acto": "Resolución 1234", "documento_id": "abc",
        "estado": "APPROVED",
    }
    for codigo in ["6412", "6424", "6492", "8010", "2520", "9499"]:
        r = evaluar(codigo, autorizacion=autorizacion)
        assert r["bloquea"], f"{codigo} debía seguir bloqueado pese a la autorización"
        assert not r["requiere_autorizacion"], (
            f"{codigo} no debe ofrecer carga de autorización: el bloqueo es de "
            f"tipo societario, no de trámite"
        )

    # Y la revalidación de servidor tampoco lo deja pasar
    ok, errores, _ = validar_seleccion(["6412"], autorizaciones={"6412": autorizacion})
    assert not ok
    assert any("6412" in e for e in errores)
    print("OK  cargar un PDF no habilita 6412, 6424, 6492, 8010, 2520 ni 9499")


# ════════════════════════════════════════════════════════════════
# 5. Revisión condicional: financieras
# ════════════════════════════════════════════════════════════════
def test_financieras_condicionales():
    # 6499 no puede bloquearse sin analizar la actividad
    r = evaluar("6499")
    assert r["decision"] == "CONDITIONAL_REVIEW"
    assert not r["bloquea"], "6499 no debe bloquearse automáticamente"
    assert r.get("pendiente"), "debe pedir respuestas antes de decidir"
    assert len(r["preguntas"]) == 8

    regla = regla_de("6499")

    # Préstamo con recursos propios NO es captación
    solo_propios = _todas(regla, NO)
    solo_propios["presta_recursos_propios"] = SI
    solo_propios["cartera_recursos_propios"] = SI
    r = evaluar("6499", solo_propios)
    assert r["decision"] == "ALLOWED_WITH_OPERATING_WARNING", r["decision"]
    assert not r["bloquea"], "prestar con recursos propios no es captación financiera"

    # Captar del público sí bloquea
    capta = _todas(regla, NO)
    capta["capta_publico"] = SI
    r = evaluar("6499", capta)
    assert r["decision"] == "BLOCK_NOT_SAS"
    assert "Superintendencia Financiera" in r["autoridad"]

    # No todo 66xx está prohibido
    for codigo in ["6615", "6619", "6621", "6629", "6630"]:
        assert evaluar(codigo)["decision"] == "CONDITIONAL_REVIEW", codigo
        assert not evaluar(codigo, _todas(regla_de(codigo), NO))["bloquea"], codigo
    print("OK  6499 no se bloquea sin analizar; recursos propios ≠ captación; 66xx no es prohibición en bloque")


# ════════════════════════════════════════════════════════════════
# 6. Revisión condicional: seguridad privada
# ════════════════════════════════════════════════════════════════
def test_seguridad_condicional():
    regla = regla_de("8020")

    # Cerrajería e instalación: permitido
    cerrajeria = _todas(regla, NO)
    r_cerrajeria = evaluar("8020", cerrajeria)
    assert r_cerrajeria["decision"] == "ALLOWED_WITH_OPERATING_WARNING"
    assert not r_cerrajeria["bloquea"]

    # Central de monitoreo: es vigilancia privada
    central = _todas(regla, NO)
    central["central_monitoreo"] = SI
    r_central = evaluar("8020", central)
    assert r_central["decision"] == "BLOCK_NOT_SAS"

    assert r_cerrajeria["decision"] != r_central["decision"], \
        "la cerrajería no puede tratarse igual que una central de monitoreo"

    # 8030 también es condicional, no bloqueo automático
    assert evaluar("8030")["decision"] == "CONDITIONAL_REVIEW"
    consultoria = _todas(regla_de("8030"), NO)
    assert not evaluar("8030", consultoria)["bloquea"], \
        "la auditoría y la debida diligencia no son vigilancia privada"
    print("OK  8020 de cerrajería ≠ central de monitoreo; 8030 no bloquea la consultoría")


# ════════════════════════════════════════════════════════════════
# 7. Puertos
# ════════════════════════════════════════════════════════════════
def test_puertos():
    regla = regla_de("5222")

    auxiliares = _todas(regla, NO)
    r_aux = evaluar("5222", auxiliares)
    assert r_aux["decision"] == "ALLOWED_WITH_OPERATING_WARNING"

    portuaria = _todas(regla, NO)
    portuaria["sociedad_portuaria"] = SI
    r_port = evaluar("5222", portuaria)
    assert r_port["decision"] == "BLOCK_NOT_SAS"
    assert r_port["tipo_entidad_requerido"] == "Sociedad anónima"

    assert r_aux["decision"] != r_port["decision"], \
        "los servicios auxiliares no pueden tratarse igual que una sociedad portuaria"
    print("OK  5222 auxiliar ≠ sociedad portuaria (que exige S.A.)")


# ════════════════════════════════════════════════════════════════
# 8. Transporte: nada de bloqueo en bloque
# ════════════════════════════════════════════════════════════════
def test_transporte():
    codigos = [r["codigo"] for r in cargar_matriz()["reglas"]
               if r["codigo"][:2] in ("49", "50", "51")]
    assert len(codigos) >= 10, "faltan códigos de transporte en la matriz"

    for codigo in codigos:
        assert evaluar(codigo)["decision"] == "CONDITIONAL_REVIEW", codigo
        assert not evaluar(codigo)["bloquea"], f"{codigo} no debe bloquearse en bloque"

    regla = regla_de("4921")
    # Transporte de carga propia: permitido
    carga = _todas(regla, NO)
    assert evaluar("4921", carga)["decision"] == "ALLOWED_WITH_OPERATING_WARNING"

    # Público CON rutas y horarios: exige habilitación previa (modo "todas")
    publico = {"transporte_publico": SI, "rutas_horarios": SI}
    r = evaluar("4921", publico)
    assert r["decision"] == "REQUIRES_PRIOR_AUTHORIZATION"
    assert r["requiere_autorizacion"]
    assert not r["bloquea"], "el transporte público no bloquea la S.A.S., pide autorización"

    # Público SIN rutas asignadas: no escala, porque el modo es "todas"
    parcial = {"transporte_publico": SI, "rutas_horarios": NO}
    assert evaluar("4921", parcial)["decision"] == "ALLOWED_WITH_OPERATING_WARNING"
    print("OK  transporte condicional por modalidad, sin bloqueo en bloque")


# ════════════════════════════════════════════════════════════════
# 9. Autorización previa: aquí sí sirve adjuntar
# ════════════════════════════════════════════════════════════════
def test_autorizacion_previa():
    publico = {"transporte_publico": SI, "rutas_horarios": SI}

    ok, errores, _ = validar_seleccion(["4921"], respuestas=publico)
    assert not ok, "sin adjuntar la habilitación no debía dejar generar"
    assert any("autorización previa" in e for e in errores), errores

    ok, errores, _ = validar_seleccion(
        ["4921"], respuestas=publico,
        autorizaciones={"4921": {"acto": "Resolución 100", "documento_id": "x"}},
    )
    assert ok, errores
    print("OK  la autorización sí habilita cuando la S.A.S. es compatible")


# ════════════════════════════════════════════════════════════════
# 10. Servicios públicos domiciliarios: no se bloquean por ser S.A.S.
# ════════════════════════════════════════════════════════════════
def test_servicios_publicos():
    for codigo in ["3511", "3520", "3600", "3700", "3811", "6110", "6120"]:
        r = evaluar(codigo)
        assert r["decision"] == "ALLOWED_WITH_OPERATING_WARNING", (codigo, r["decision"])
        assert not r["bloquea"], f"{codigo} no puede bloquearse solo por ser S.A.S."
        assert "E.S.P." in r["mensaje"], codigo
    print("OK  servicios públicos permitidos con régimen E.S.P., sin bloqueo automático")


# ════════════════════════════════════════════════════════════════
# 11. Términos disparadores en el objeto social
# ════════════════════════════════════════════════════════════════
def test_terminos_disparadores():
    # Sin mención de armas, 4774 pasa sin preguntas
    r = evaluar("4774", objeto_social="Comercio al por menor de artículos de segunda mano.")
    assert r["decision"] == "ALLOWED_WITH_OPERATING_WARNING"
    assert not r.get("pendiente")

    # Mencionando armas, se eleva a revisión
    r = evaluar("4774", objeto_social="Compraventa de armas y municiones usadas.")
    assert r["decision"] == "CONDITIONAL_REVIEW"
    assert r.get("pendiente"), "debía pedir confirmación"
    assert "armas" in r["terminos_detectados"]

    # Y si confirma, bloquea
    r = evaluar("4774", {"armas_explosivos": SI},
                objeto_social="Compraventa de armas y municiones usadas.")
    assert r["decision"] == "BLOCK_NOT_SAS"

    # Detecta con y sin tilde
    r = evaluar("2029", objeto_social="Fabricación de POLVORA y explosivos.")
    assert r.get("pendiente"), "debía detectar 'pólvora' escrito sin tilde"
    print("OK  términos disparadores detectados en el objeto social (con y sin tildes)")


# ════════════════════════════════════════════════════════════════
# 12. Etiquetas para la lista desplegable
# ════════════════════════════════════════════════════════════════
def test_etiquetas():
    assert resumen_para_listado("9499")["nivel"] == "bloqueado"
    assert resumen_para_listado("6412")["nivel"] == "bloqueado"
    assert resumen_para_listado("8020")["nivel"] == "preguntas"
    assert resumen_para_listado("3511")["nivel"] == "aviso"
    assert resumen_para_listado("6201") is None, "lo no regulado no se marca"
    print("OK  etiquetas para marcar los códigos en el desplegable")


if __name__ == "__main__":
    test_matriz()
    test_bloqueo_no_mercantil()
    test_bloqueo_no_sas()
    test_autorizacion_no_subsana_bloqueo()
    test_financieras_condicionales()
    test_seguridad_condicional()
    test_puertos()
    test_transporte()
    test_autorizacion_previa()
    test_servicios_publicos()
    test_terminos_disparadores()
    test_etiquetas()
    print("\nTodas las pruebas del validador CIIU pasaron.")
