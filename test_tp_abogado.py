"""La tarjeta de abogado habilita las funciones avanzadas y se consume al generar."""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
sys.path.insert(0, BASE)

import app as flask_app  # noqa: E402
from test_paquete import _cliente, _payload, PAYLOAD_B  # noqa: E402

respuesta_ia = {}
flask_app._extract_with_claude = lambda *a, **k: dict(respuesta_ia)


def subir(client):
    return client.post("/api/extract/tp-abogado", content_type="multipart/form-data",
                       data={"file": (io.BytesIO(b"img"), "tp.jpg")})


client = _cliente()
payload = _payload("payload_b.json", PAYLOAD_B)
payload["disposiciones"] = [{"tema": "adicional", "texto": "prueba"}]

# Sin tarjeta: pedir disposiciones se rechaza
r = client.post("/api/generate", json=payload)
assert r.status_code == 403, r.status_code

# Documento que no es tarjeta de abogado
respuesta_ia.update(es_tarjeta_abogado=False, motivo="Es una cédula", numero_tarjeta="")
r = subir(client)
assert r.status_code == 422 and r.get_json()["valida"] is False
with client.session_transaction() as s:
    assert "tp_abogado" not in s

# Tarjeta válida
respuesta_ia.update(es_tarjeta_abogado=True, numero_tarjeta="123456",
                    nombre_completo="Persona Test", motivo="")
r = subir(client)
assert r.status_code == 200 and r.get_json()["numero_tarjeta"] == "123456"

# Con tarjeta genera, y la validación se consume
r = client.post("/api/generate", json=payload)
assert r.status_code == 200, r.get_data(as_text=True)[:300]
with client.session_transaction() as s:
    assert "tp_abogado" not in s, "la tarjeta vale para una sola constitución"
r = client.post("/api/generate", json=payload)
assert r.status_code == 403

# Sin disposiciones no se exige tarjeta (flujo actual intacto)
payload.pop("disposiciones")
assert client.post("/api/generate", json=payload).status_code == 200

print("OK test_tp_abogado")
