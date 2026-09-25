"""Soportes del paquete: cédulas cargadas o PDF de pendiente, sin duplicados."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from processors.soportes import armar_soportes  # noqa: E402

data = {
    "accionistas": [
        {"tipo": "natural", "doc_key": "acc1", "nombre": "Persona Test Uno", "id_num": "99.999.991"},
        {"tipo": "natural", "doc_key": "acc2", "nombre": "Persona Test Dos", "id_num": "99999992"},
        {"tipo": "juridica", "doc_key": "acc3", "nombre": "PRUEBA HOLDING S.A.S.",
         "id_num": "900111222", "rl_nombre": "Persona Test Tres", "rl_cc": "99999993"},
    ],
    # El RL principal es el accionista 1: su cédula no se pide dos veces
    "rl_principales": [{"nombre": "Persona Test Uno", "cc": "99999991", "doc_key": "rl_principal"}],
    "rl_suplentes": [],
    "tiene_junta": True,
    "junta_directiva": {
        "principales": [{"nombre": "Persona Test Cuatro", "id_num": "99999994", "doc_key": "jd_pri_1"}],
        "suplentes": [],
    },
    "tiene_revisor": True,
    "revisor_fiscal": {"tipo": "natural", "nombre": "Persona Test Cinco", "id_num": "99999995"},
}
archivos = {
    "cedula:acc1": (b"%PDF-cedula1", "cedula1.pdf"),
    "certificado:acc3": (b"jpgdata", "cert.JPG"),
}

with tempfile.TemporaryDirectory() as d:
    zipnames = sorted(z for _, z in armar_soportes(data, archivos, d))
    for z in zipnames:
        print(z)

    esperados = [
        "Soportes/Cedula_accionista_1_y_representante_legal_principal_Persona_Test_Uno.pdf",
        "Soportes/Certificado_accionista_3_PRUEBA_HOLDING_S_A_S.jpg",
        "Soportes/PENDIENTE_Cedula_accionista_2_Persona_Test_Dos.pdf",
        "Soportes/PENDIENTE_Cedula_miembro_principal_1_de_junta_directiva_Persona_Test_Cuatro.pdf",
        "Soportes/PENDIENTE_Cedula_representante_legal_de_accionista_3_PRUEBA_HOLDING_S_A_S_Persona_Test_Tres.pdf",
        "Soportes/PENDIENTE_Cedula_revisor_fiscal_designado_Persona_Test_Cinco.pdf",
        "Soportes/PENDIENTE_Tarjeta_revisor_fiscal_designado_Persona_Test_Cinco.pdf",
    ]
    assert zipnames == sorted(esperados), zipnames
    # El cargado se copia tal cual; el pendiente es un PDF válido
    with open(os.path.join(d, esperados[0].split("/")[1]), "rb") as f:
        assert f.read() == b"%PDF-cedula1"
    with open(os.path.join(d, esperados[2].split("/")[1]), "rb") as f:
        assert f.read(5) == b"%PDF-"

print("OK test_soportes")
