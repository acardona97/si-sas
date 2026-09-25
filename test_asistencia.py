# -*- coding: utf-8 -*-
"""Pruebas del envío del paquete a Quarta para asistencia en la radicación.

Ejecutar: python test_asistencia.py
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import app as flask_app
from test_paquete import _cliente


def _zip(contenido=b"documento"):
    archivo = io.BytesIO()
    with zipfile.ZipFile(archivo, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("documento.txt", contenido)
    return archivo.getvalue()


class RespuestaMake:
    status = 200

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _post(client, datos, nombre="constitucion.zip"):
    return client.post("/api/enviar-asistencia", content_type="multipart/form-data", data={
        "zip": (io.BytesIO(datos), nombre),
        "nombre_sas": "PRUEBA S.A.S.",
        "telefono": "3001234567",
        "mensaje": "Necesito asistencia.",
    })


def test_adjunto(client):
    capturada = {}

    def urlopen(solicitud, timeout):
        capturada["cuerpo"] = solicitud.data
        capturada["timeout"] = timeout
        return RespuestaMake()

    original = flask_app.urllib.request.urlopen
    flask_app.urllib.request.urlopen = urlopen
    os.environ["MAKE_WEBHOOK_URL"] = "https://make.test/webhook"
    try:
        respuesta = _post(client, _zip())
    finally:
        flask_app.urllib.request.urlopen = original

    assert respuesta.status_code == 200, respuesta.get_data(as_text=True)
    assert b'name="destinatario"' in capturada["cuerpo"]
    assert b"acardona@quarta.co" in capturada["cuerpo"]
    assert b'name="zip"; filename="constitucion.zip"' in capturada["cuerpo"]
    assert capturada["timeout"] == 30
    print("  OK  envía destinatario y ZIP adjunto")


def test_enlace_descarga(client):
    capturada = {}

    def urlopen(solicitud, timeout):
        capturada["cuerpo"] = solicitud.data
        return RespuestaMake()

    original = flask_app.urllib.request.urlopen
    flask_app.urllib.request.urlopen = urlopen
    os.environ["MAKE_WEBHOOK_URL"] = "https://make.test/webhook"
    os.environ["MAKE_MAX_ADJUNTO_BYTES"] = "1"
    try:
        respuesta = _post(client, _zip(b"contenido grande"))
    finally:
        flask_app.urllib.request.urlopen = original
        os.environ.pop("MAKE_MAX_ADJUNTO_BYTES", None)

    assert respuesta.status_code == 200, respuesta.get_data(as_text=True)
    assert b'name="enlace_descarga"' in capturada["cuerpo"]
    assert b'name="zip"' not in capturada["cuerpo"]
    token = capturada["cuerpo"].decode().split("/descargas/asistencia/", 1)[1].split("\r", 1)[0]
    descarga = client.get("/descargas/asistencia/" + token)
    assert descarga.status_code == 200 and zipfile.is_zipfile(io.BytesIO(descarga.data))
    assert client.get("/descargas/asistencia/..%2Fx").status_code == 404
    assert client.get("/descargas/asistencia/" + "a" * 32).status_code == 404
    print("  OK  usa enlace temporal para ZIP grande")


def test_validaciones(client):
    os.environ.pop("MAKE_WEBHOOK_URL", None)
    respuesta = _post(client, _zip())
    assert respuesta.status_code == 503

    os.environ["MAKE_WEBHOOK_URL"] = "https://make.test/webhook"
    respuesta = _post(client, b"no es zip", "documento.zip")
    assert respuesta.status_code == 400
    print("  OK  valida configuración y ZIP")


if __name__ == "__main__":
    cliente = _cliente()
    test_adjunto(cliente)
    test_enlace_descarga(cliente)
    test_validaciones(cliente)
    print("\nTodas las pruebas de asistencia pasaron.")
