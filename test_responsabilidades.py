# -*- coding: utf-8 -*-
"""
Pruebas del anexo de responsabilidades tributarias.

Reglas de la guía de la Cámara de Comercio de Medellín (V.01 2024):
  - 05 y 47 son excluyentes entre sí
  - 48 y 49 son excluyentes entre sí
  - las sociedades no pueden llevar 04, 06 ni 49
  - 13, 15, 17, 23, 45 y 52 exigen resolución o habilitación previa de la DIAN
  - el Régimen Simple ya integra el impuesto nacional al consumo

Ejecutar:  python test_responsabilidades.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from processors.responsabilidades import (
    cargar, construir, disponibles, no_seleccionables, predeterminadas,
    exige_comercio_exterior, casillas_rues_comercio_exterior,
    config_comercio_exterior,
)

# Listado completo de la casilla 53 del RUT que debe quedar clasificado
LISTADO_DIAN = [
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "13", "14", "15", "16", "17", "18", "19", "20", "21", "22",
    "23", "24", "26", "32", "33", "36", "37", "38", "39", "41",
    "42", "45", "46", "47", "48", "49", "50", "51", "52", "53",
    "54", "55", "56", "58", "59", "60", "61", "62", "63", "64",
    "65", "66",
]


def codigos(lista):
    return [c for c, _ in lista]


def test_predeterminadas():
    ordinario = codigos(predeterminadas("ordinario"))
    assert ordinario == ["05", "07", "14", "42", "48", "55"], ordinario

    simple = codigos(predeterminadas("simple"))
    assert simple == ["07", "14", "42", "47", "48", "55"], simple

    # Nunca conviven 05 y 47
    assert not ({"05", "47"} <= set(ordinario))
    assert not ({"05", "47"} <= set(simple))

    # El INC entra por actividad, pero no en Régimen Simple: ya lo integra
    assert "33" in codigos(predeterminadas("ordinario", incluir_consumo=True))
    assert "33" not in codigos(predeterminadas("simple", incluir_consumo=True))
    print("OK  predeterminadas por régimen, sin mezclar 05 con 47")


def test_no_duplica_las_predeterminadas():
    for regimen in ("ordinario", "simple"):
        ya = {c for c, _ in predeterminadas(regimen)}
        ofrecidas = {r["codigo"] for r in disponibles(regimen)}
        assert not (ya & ofrecidas), (
            f"se están ofreciendo responsabilidades que ya vienen por defecto: "
            f"{ya & ofrecidas}"
        )
    print("OK  no se ofrece ninguna que ya venga preseleccionada")


def test_excluyentes_con_el_regimen():
    # El INC se ofrece en ordinario pero no en simple
    assert "33" in {r["codigo"] for r in disponibles("ordinario")}
    assert "33" not in {r["codigo"] for r in disponibles("simple")}, \
        "la 33 no debe ofrecerse en Régimen Simple: ya está integrada"

    # Y si el usuario la manda igual, se descarta con aviso
    resps, avisos = construir("simple", adicionales=["33"])
    assert "33" not in codigos(resps)
    assert any("33" in a for a in avisos), avisos
    print("OK  no se ofrece ni se acepta una excluyente con el régimen")


def test_usuario_puede_agregar():
    # El caso que pidió el usuario: la 10, usuario aduanero
    resps, avisos = construir("ordinario", adicionales=["10"])
    assert "10" in codigos(resps), codigos(resps)
    assert not avisos, avisos

    # Varias a la vez, y quedan ordenadas por código
    resps, avisos = construir("ordinario", adicionales=["19", "10", "18"])
    assert codigos(resps) == ["05", "07", "10", "14", "18", "19", "42", "48", "55"], codigos(resps)
    assert not avisos
    print("OK  el usuario agrega adicionales y quedan ordenadas")


def test_no_duplica_si_la_manda_repetida():
    resps, avisos = construir("ordinario", adicionales=["07", "42", "10", "10"])
    assert codigos(resps).count("07") == 1
    assert codigos(resps).count("42") == 1
    assert codigos(resps).count("10") == 1
    print("OK  no se duplica una responsabilidad ya incluida ni repetida")


def test_prohibidas_para_sociedad():
    vetadas = {r["codigo"] for r in no_seleccionables()}
    # Las que la guía prohíbe a las sociedades y las de resolución previa
    for codigo in ["04", "06", "49", "13", "15", "17", "23", "45", "52"]:
        assert codigo in vetadas, f"{codigo} debía estar entre las no seleccionables"
        # Nunca se ofrecen
        assert codigo not in {r["codigo"] for r in disponibles("ordinario")}
        # Y si llegan por el payload, se descartan con motivo
        resps, avisos = construir("ordinario", adicionales=[codigo])
        assert codigo not in codigos(resps), f"{codigo} no debía entrar al anexo"
        assert avisos and codigo in avisos[0], avisos
    print("OK  prohibidas para sociedad y las de resolución previa se descartan con motivo")


def test_48_y_49_excluyentes():
    # La 48 viene por defecto, así que la 49 choca
    resps, avisos = construir("ordinario", adicionales=["49"])
    assert "49" not in codigos(resps)
    assert avisos
    print("OK  48 y 49 no pueden convivir")


def test_tope_del_anexo():
    """El anexo impreso tiene diez filas: no se puede exceder ni truncar."""
    from processors.responsabilidades import cupo_adicionales, maximo_anexo
    assert maximo_anexo() == 10

    # Ordinario deja cuatro cupos (6 fijas); con consumo, tres (7 fijas)
    assert cupo_adicionales("ordinario") == 4
    assert cupo_adicionales("ordinario", incluir_consumo=True) == 3

    # Todas las adicionales del régimen ordinario caben justo
    todas = [r["codigo"] for r in disponibles("ordinario")]
    resps, avisos = construir("ordinario", adicionales=todas)
    assert len(resps) <= 10, len(resps)

    # Pero con el INC ya incluido, la última no cabe y se avisa
    todas_consumo = [r["codigo"] for r in disponibles("ordinario", incluir_consumo=True)]
    resps, avisos = construir("ordinario", incluir_consumo=True, adicionales=todas_consumo)
    assert len(resps) == 10, f"el anexo no puede pasar de 10: {len(resps)}"
    assert any("anexo solo admite" in a for a in avisos), avisos
    print("OK  el anexo nunca pasa de diez filas y avisa cuál quedó por fuera")


def test_cobertura_del_listado_dian():
    """Todo código de la casilla 53 debe estar clasificado en alguna parte."""
    datos = cargar()
    clasificados = set()
    clasificados.update(r["codigo"] for r in datos["por_regimen"].values())
    clasificados.update(r["codigo"] for r in datos["base_sociedad"])
    clasificados.update(r["codigo"] for r in datos["adicionales"])
    clasificados.update(r["codigo"] for r in datos["no_seleccionables"])

    faltan = [c for c in LISTADO_DIAN if c not in clasificados]
    assert not faltan, f"códigos DIAN sin clasificar: {faltan}"

    sobran = [c for c in clasificados if c not in LISTADO_DIAN]
    assert not sobran, f"códigos que no existen en la casilla 53: {sobran}"

    # Ningún código puede estar en dos listas a la vez
    for grupo in ("adicionales", "no_seleccionables"):
        codigos = [r["codigo"] for r in datos[grupo]]
        assert len(codigos) == len(set(codigos)), f"repetidos en {grupo}"
    vetadas = {r["codigo"] for r in datos["no_seleccionables"]}
    ofrecidas = {r["codigo"] for r in datos["adicionales"]}
    assert not (vetadas & ofrecidas), f"en dos listas: {vetadas & ofrecidas}"
    print(f"OK  los {len(LISTADO_DIAN)} códigos de la casilla 53 están clasificados")


def test_sugeridas_por_actividad():
    """Las que dependen de la actividad se destacan cuando el CIIU o el objeto la delatan."""
    # Restaurante: sugiere INC y no responsable de consumo
    ofrecidas = {r["codigo"]: r for r in
                 disponibles("ordinario", False, ["5611"], "Operar un restaurante")}
    assert ofrecidas["33"]["sugerida"], "un restaurante debe sugerir la 33"
    assert ofrecidas["50"]["sugerida"], "un restaurante debe sugerir la 50"
    assert not ofrecidas["18"]["sugerida"], "precios de transferencia no lo sugiere un restaurante"

    # Combustibles: gasolina y carbono, detectados por texto
    ofrecidas = {r["codigo"]: r for r in
                 disponibles("ordinario", False, [], "Venta de gasolina y ACPM")}
    assert ofrecidas["32"]["sugerida"]
    assert ofrecidas["56"]["sugerida"]

    # Plásticos de un solo uso, detectado sin tildes
    ofrecidas = {r["codigo"]: r for r in
                 disponibles("ordinario", False, [], "Fabricacion de envases plasticos")}
    assert ofrecidas["62"]["sugerida"], "debía detectar 'plastico' sin tilde"

    # Sin actividad relacionada no se sugiere nada de eso
    ofrecidas = {r["codigo"]: r for r in
                 disponibles("ordinario", False, ["6201"], "Desarrollo de software")}
    for codigo in ("32", "56", "62", "63", "64"):
        assert not ofrecidas[codigo]["sugerida"], f"{codigo} no aplica a software"
    print("OK  se sugieren las que la actividad declarada hace probables")


def test_reemplazo_53_por_48():
    """La 53 sustituye a la 48, no se suma: o se es responsable de IVA o no."""
    sin = [c for c, _ in predeterminadas("ordinario")]
    assert "48" in sin

    con = [c for c, _ in predeterminadas("ordinario", adicionales=["53"])]
    assert "48" not in con, "la 53 debe sacar a la 48 de las predeterminadas"

    resps, avisos = construir("ordinario", adicionales=["53"])
    codigos_finales = codigos(resps)
    assert "53" in codigos_finales and "48" not in codigos_finales, codigos_finales
    assert not avisos, avisos
    print("OK  la 53 reemplaza a la 48 en lugar de convivir con ella")


def test_dependencias():
    """La 24 y la 26 no van sin la 18."""
    for codigo in ("24", "26"):
        resps, avisos = construir("ordinario", adicionales=[codigo])
        assert codigo not in codigos(resps), f"{codigo} no debía entrar sin la 18"
        assert any("requiere" in a for a in avisos), avisos

        resps, avisos = construir("ordinario", adicionales=["18", codigo])
        assert codigo in codigos(resps), f"{codigo} debía entrar junto con la 18"
        assert not avisos, avisos
    print("OK  las declaraciones de precios de transferencia exigen la 18")


def test_excluyentes_nuevas():
    """33 vs 50, y 48 vs 53."""
    # No se puede ser responsable y no responsable del consumo a la vez
    resps, avisos = construir("ordinario", incluir_consumo=True, adicionales=["50"])
    assert "50" not in codigos(resps)
    assert any("excluyente" in a for a in avisos), avisos

    # Ni responsable y no responsable de IVA
    resps, avisos = construir("ordinario", adicionales=["53", "48"])
    finales = codigos(resps)
    assert not ("48" in finales and "53" in finales), finales
    # La interfaz necesita saberlo para soltar la contraria al marcar una
    ofrecidas = {r["codigo"]: r for r in disponibles("ordinario", ciiu_codes=["5611"])}
    assert "50" in ofrecidas["33"]["excluye"], ofrecidas["33"]
    assert "33" in ofrecidas["50"]["excluye"], ofrecidas["50"]
    # El código del régimen elegido nunca se lista ahí: no es una casilla que
    # el usuario pueda soltar desde el checklist.
    assert all("05" not in r["excluye"] for r in ofrecidas.values()), ofrecidas
    print("OK  33/50 y 48/53 no pueden convivir, y el cuestionario lo sabe")


def test_comercio_exterior():
    """Las de comercio exterior obligan a declarar la calidad ante la DIAN."""
    cfg = config_comercio_exterior()
    ids = {op["id"] for op in cfg["opciones"]}
    assert ids == {"importador", "exportador", "usuario_aduanero"}, ids

    # Las tres casillas del RUES están mapeadas y no se repiten
    casillas = [op["casilla_rues"] for op in cfg["opciones"]]
    assert casillas == ["Casilla 1_30", "Casilla 1_31", "Casilla 1_32"], casillas

    # 10, 19 y 21 disparan la pregunta
    for codigo in ("10", "19", "21"):
        resps, _ = construir("ordinario", adicionales=[codigo])
        assert exige_comercio_exterior(resps) == [codigo], codigo

    # Las que no son de comercio exterior no la disparan
    resps, _ = construir("ordinario", adicionales=["16", "18"])
    assert exige_comercio_exterior(resps) == []

    # El perfil declarado se traduce a casillas
    assert casillas_rues_comercio_exterior(["importador"]) == {"Casilla 1_30": True}
    assert casillas_rues_comercio_exterior(["exportador"]) == {"Casilla 1_31": True}
    assert casillas_rues_comercio_exterior(["usuario_aduanero"]) == {"Casilla 1_32": True}
    assert casillas_rues_comercio_exterior(["importador", "exportador"]) == {
        "Casilla 1_30": True, "Casilla 1_31": True}
    # Un perfil inválido no marca nada
    assert casillas_rues_comercio_exterior(["cualquier cosa"]) == {}
    assert casillas_rues_comercio_exterior([]) == {}
    print("OK  comercio exterior: dispara la pregunta y marca la casilla correcta del RUES")


def test_46_no_es_para_sociedad_colombiana():
    """La 46 es de prestadores SIN domicilio en Colombia."""
    vetadas = {r["codigo"]: r for r in no_seleccionables()}
    assert "46" in vetadas, "la 46 no puede ofrecerse a una S.A.S. colombiana"
    assert "09" in vetadas["46"]["motivo"], \
        "el motivo debe remitir a la 09, que es la que sí le corresponde"
    resps, avisos = construir("ordinario", adicionales=["46"])
    assert "46" not in codigos(resps)
    assert avisos
    print("OK  la 46 se bloquea y se explica cuál corresponde en su lugar")


def test_matriz_coherente():
    datos = cargar()
    assert datos["version"] and datos["revisado_el"]
    assert "Cámara de Comercio de Medellín" in datos["fuente"]
    # Ninguna adicional puede estar a la vez en la lista de vetadas
    vetadas = {r["codigo"] for r in datos["no_seleccionables"]}
    for r in datos["adicionales"]:
        assert r["codigo"] not in vetadas, f"{r['codigo']} está en las dos listas"
        assert r.get("descripcion"), f"{r['codigo']} sin descripción para el usuario"
    for r in datos["no_seleccionables"]:
        assert r.get("motivo"), f"{r['codigo']} sin motivo"
    print("OK  matriz versionada y coherente")


if __name__ == "__main__":
    test_matriz_coherente()
    test_predeterminadas()
    test_no_duplica_las_predeterminadas()
    test_excluyentes_con_el_regimen()
    test_usuario_puede_agregar()
    test_no_duplica_si_la_manda_repetida()
    test_prohibidas_para_sociedad()
    test_48_y_49_excluyentes()
    test_tope_del_anexo()
    test_cobertura_del_listado_dian()
    test_sugeridas_por_actividad()
    test_reemplazo_53_por_48()
    test_dependencias()
    test_excluyentes_nuevas()
    test_comercio_exterior()
    test_46_no_es_para_sociedad_colombiana()
    print("\nTodas las pruebas de responsabilidades pasaron.")
