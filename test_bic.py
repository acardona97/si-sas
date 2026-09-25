"""Sociedad BIC: la palabra BIC en la razón social marca la casilla del RUES."""
import io
import os
import sys
import tempfile
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
sys.path.insert(0, BASE)
from test_paquete import _cliente, _payload, _campos_pdf, PAYLOAD_B  # noqa: E402

client = _cliente()
casos = {
    "GRUPO I'Q HOLDING S.A.S. BIC": True,
    "TOLEDALES BIC S.A.S.": True,
    "BICICLETAS DEL VALLE S.A.S.": False,
}
for nombre, bic in casos.items():
    payload = _payload("payload_b.json", PAYLOAD_B)
    payload["nombre_sas"] = nombre
    r = client.post("/api/generate", json=payload)
    assert r.status_code == 200, (nombre, r.get_data(as_text=True)[:300])
    with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
        rues = next(n for n in zf.namelist() if "Formulario_RUES" in n)
        ruta = os.path.join(tempfile.mkdtemp(), "rues.pdf")
        open(ruta, "wb").write(zf.read(rues))
    campos = _campos_pdf(ruta)
    marcada = str(campos.get("Casilla 2")) not in ("", "None", "/Off")
    assert marcada == bic, (nombre, campos.get("Casilla 2"))
    assert campos.get("Cuadro de texto 2_42") == nombre, campos.get("Cuadro de texto 2_42")
    print(f"  OK  {nombre} -> BIC {'marcada' if bic else 'sin marcar'}")

print("OK test_bic")
