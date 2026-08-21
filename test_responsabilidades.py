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
)


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
    print("\nTodas las pruebas de responsabilidades pasaron.")
