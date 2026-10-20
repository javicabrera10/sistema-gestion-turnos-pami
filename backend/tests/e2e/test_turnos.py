from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")
OTRO_PACIENTE = {
    "nombre": "Otro Paciente", "email": "otro@pamiapp.com", "telefono": "2611111111",
    "dni": "40111222", "password": "Clave12345",
}


def _futuro(dias: int = 7) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(tzinfo=None).isoformat(timespec="seconds")


def _solicitud(**cambios) -> dict:
    datos = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual"}
    return {**datos, **cambios}


def _solicitar(client, headers, **cambios):
    return client.post("/api/turnos", json=_solicitud(**cambios), headers=headers)


def _otorgar(app, turno_id):
    # La US2 todavía no existe: se simula lo que va a hacer el administrativo
    app.db.turnos.update_one({"_id": ObjectId(turno_id)}, {"$set": {"estado": "otorgado"}})


def _headers_otro_paciente(client, auth_headers):
    client.post("/api/auth/registro", json=OTRO_PACIENTE)
    return auth_headers(OTRO_PACIENTE["email"], OTRO_PACIENTE["password"])


# ---------- solicitar ----------

def test_solicitar_turno_ok(client, auth_headers):
    h = auth_headers(*PACIENTE)
    resp = _solicitar(client, h)

    assert resp.status_code == 201
    turno = resp.get_json()
    assert turno["estado"] == "solicitado"
    assert turno["especialidad"] == "Cardiología"
    assert turno["medico_id"] is None
    # el paciente sale del token, no del body
    assert turno["paciente_id"] == client.get("/api/auth/me", headers=h).get_json()["id"]


def test_solicitar_sin_token(client):
    assert client.post("/api/turnos", json=_solicitud()).status_code == 401


@pytest.mark.parametrize("credenciales", [MEDICO, ADMIN])
def test_solicitar_solo_lo_puede_hacer_un_paciente(client, auth_headers, credenciales):
    resp = _solicitar(client, auth_headers(*credenciales))
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "cambios",
    [
        {"fecha_hora": "2020-01-01T10:00:00"},
        {"motivo": ""},
        {"especialidad": {"$ne": ""}},
        {"estado": "confirmado"},
        {"paciente_id": "000000000000000000000000"},
    ],
)
def test_solicitar_datos_invalidos(client, auth_headers, cambios):
    resp = _solicitar(client, auth_headers(*PACIENTE), **cambios)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Datos inválidos"


# ---------- mis turnos ----------

def test_mis_turnos_sin_turnos_devuelve_lista_vacia(client, auth_headers):
    resp = client.get("/api/turnos/mios", headers=auth_headers(*PACIENTE))
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_mis_turnos_devuelve_solo_los_propios(client, auth_headers):
    h1 = auth_headers(*PACIENTE)
    h2 = _headers_otro_paciente(client, auth_headers)
    _solicitar(client, h1)
    _solicitar(client, h2)
    _solicitar(client, h2, especialidad="Dermatología")

    assert len(client.get("/api/turnos/mios", headers=h1).get_json()) == 1
    assert len(client.get("/api/turnos/mios", headers=h2).get_json()) == 2


def test_mis_turnos_solo_para_pacientes(client, auth_headers):
    assert client.get("/api/turnos/mios", headers=auth_headers(*MEDICO)).status_code == 403
    assert client.get("/api/turnos/mios").status_code == 401


# ---------- confirmar / rechazar ----------

def test_confirmar_turno_otorgado(app, client, auth_headers):
    h = auth_headers(*PACIENTE)
    turno_id = _solicitar(client, h).get_json()["id"]
    _otorgar(app, turno_id)

    resp = client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h)

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "confirmado"
    assert client.get("/api/turnos/mios", headers=h).get_json()[0]["estado"] == "confirmado"


def test_rechazar_turno_otorgado(app, client, auth_headers):
    h = auth_headers(*PACIENTE)
    turno_id = _solicitar(client, h).get_json()["id"]
    _otorgar(app, turno_id)

    resp = client.patch(f"/api/turnos/{turno_id}/rechazar", headers=h)

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "rechazado"


def test_no_se_puede_confirmar_un_turno_que_no_fue_otorgado(client, auth_headers):
    h = auth_headers(*PACIENTE)
    turno_id = _solicitar(client, h).get_json()["id"]

    resp = client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h)

    assert resp.status_code == 409
    assert "solicitado" in resp.get_json()["error"]


def test_no_se_puede_responder_dos_veces(app, client, auth_headers):
    h = auth_headers(*PACIENTE)
    turno_id = _solicitar(client, h).get_json()["id"]
    _otorgar(app, turno_id)
    client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h)

    assert client.patch(f"/api/turnos/{turno_id}/rechazar", headers=h).status_code == 409


def test_otro_paciente_no_puede_responder_el_turno(app, client, auth_headers):
    h1 = auth_headers(*PACIENTE)
    h2 = _headers_otro_paciente(client, auth_headers)
    turno_id = _solicitar(client, h1).get_json()["id"]
    _otorgar(app, turno_id)

    resp = client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h2)

    assert resp.status_code == 404
    assert client.get("/api/turnos/mios", headers=h1).get_json()[0]["estado"] == "otorgado"


@pytest.mark.parametrize("turno_id", ["no-es-un-id", "0" * 24])
def test_responder_turno_inexistente(client, auth_headers, turno_id):
    h = auth_headers(*PACIENTE)
    assert client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h).status_code == 404


def test_responder_requiere_rol_paciente(client, auth_headers):
    ruta = "/api/turnos/" + "0" * 24 + "/confirmar"
    assert client.patch(ruta, headers=auth_headers(*ADMIN)).status_code == 403
    assert client.patch(ruta).status_code == 401


# ---------- documentación ----------

def test_swagger_documenta_los_endpoints_de_turnos(client):
    spec = client.get("/apispec_1.json").get_json()
    assert "/api/turnos" in spec["paths"]
    assert "/api/turnos/mios" in spec["paths"]
    assert "/api/turnos/{turno_id}/confirmar" in spec["paths"]
    assert "/api/turnos/{turno_id}/rechazar" in spec["paths"]
