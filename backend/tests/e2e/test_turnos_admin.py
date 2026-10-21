from datetime import datetime, timedelta, timezone

import pytest

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")


def _futuro(dias: int = 7) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(tzinfo=None).isoformat(timespec="seconds")


def _id_de(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).get_json()["id"]


def _solicitar(client, headers) -> str:
    datos = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual"}
    return client.post("/api/turnos", json=datos, headers=headers).get_json()["id"]


def _otorgar(client, headers, turno_id, medico_id, fecha=None):
    cuerpo = {"medico_id": medico_id, "fecha_hora": fecha or _futuro(10)}
    return client.patch(f"/api/turnos/{turno_id}/otorgar", json=cuerpo, headers=headers)


@pytest.fixture
def h_paciente(auth_headers):
    return auth_headers(*PACIENTE)


@pytest.fixture
def h_admin(auth_headers):
    return auth_headers(*ADMIN)


@pytest.fixture
def h_medico(auth_headers):
    return auth_headers(*MEDICO)


# ---------- ver solicitudes ----------

def test_administrativo_ve_las_solicitudes_con_datos_del_paciente(client, h_paciente, h_admin):
    _solicitar(client, h_paciente)

    resp = client.get("/api/turnos?estado=solicitado", headers=h_admin)

    assert resp.status_code == 200
    turnos = resp.get_json()
    assert len(turnos) == 1
    assert turnos[0]["estado"] == "solicitado"
    assert turnos[0]["paciente"]["nombre"] == "Paula Paciente"
    assert turnos[0]["paciente"]["dni"] == "30111222"
    # solo datos de contacto: nada de historia clínica ni credenciales
    assert set(turnos[0]["paciente"]) == {"id", "nombre", "dni", "telefono"}


def test_filtro_por_estado(client, h_paciente, h_admin):
    _solicitar(client, h_paciente)
    assert len(client.get("/api/turnos", headers=h_admin).get_json()) == 1
    assert client.get("/api/turnos?estado=otorgado", headers=h_admin).get_json() == []


def test_estado_invalido_en_el_filtro(client, h_admin):
    resp = client.get("/api/turnos?estado=inventado", headers=h_admin)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Datos inválidos"


@pytest.mark.parametrize("credenciales", [PACIENTE, MEDICO])
def test_solo_el_administrativo_ve_los_turnos(client, auth_headers, credenciales):
    assert client.get("/api/turnos", headers=auth_headers(*credenciales)).status_code == 403
    assert client.get("/api/turnos").status_code == 401


def test_ver_detalle_de_un_turno(client, h_paciente, h_admin):
    turno_id = _solicitar(client, h_paciente)

    resp = client.get(f"/api/turnos/{turno_id}", headers=h_admin)

    assert resp.status_code == 200
    assert resp.get_json()["id"] == turno_id
    assert resp.get_json()["paciente"]["nombre"] == "Paula Paciente"


@pytest.mark.parametrize("turno_id", ["no-es-un-id", "0" * 24])
def test_detalle_de_turno_inexistente(client, h_admin, turno_id):
    assert client.get(f"/api/turnos/{turno_id}", headers=h_admin).status_code == 404


def test_paciente_no_puede_ver_el_detalle_administrativo(client, h_paciente):
    turno_id = _solicitar(client, h_paciente)
    assert client.get(f"/api/turnos/{turno_id}", headers=h_paciente).status_code == 403


# ---------- otorgar ----------

def test_otorgar_turno_ok(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente)
    medico_id = _id_de(client, h_medico)
    fecha = _futuro(10)

    resp = _otorgar(client, h_admin, turno_id, medico_id, fecha)

    assert resp.status_code == 200
    turno = resp.get_json()
    assert turno["estado"] == "otorgado"
    assert turno["medico_id"] == medico_id
    assert turno["administrativo_id"] == _id_de(client, h_admin)
    assert turno["fecha_hora"] == fecha


def test_flujo_completo_solicitar_otorgar_y_confirmar(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente)
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))

    # el paciente ve el turno otorgado en su lista
    mios = client.get("/api/turnos/mios", headers=h_paciente).get_json()
    assert mios[0]["estado"] == "otorgado"

    resp = client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h_paciente)
    assert resp.get_json()["estado"] == "confirmado"


def test_no_se_puede_otorgar_dos_veces(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente)
    medico_id = _id_de(client, h_medico)
    _otorgar(client, h_admin, turno_id, medico_id)

    resp = _otorgar(client, h_admin, turno_id, medico_id)

    assert resp.status_code == 409


def test_otorgar_con_medico_inexistente(client, h_paciente, h_admin):
    turno_id = _solicitar(client, h_paciente)
    resp = _otorgar(client, h_admin, turno_id, "0" * 24)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "El médico indicado no existe"


def test_otorgar_con_un_usuario_que_no_es_medico(client, h_paciente, h_admin):
    turno_id = _solicitar(client, h_paciente)
    resp = _otorgar(client, h_admin, turno_id, _id_de(client, h_paciente))
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"medico_id": "123", "fecha_hora": "2099-01-01T10:00:00"},
        {"medico_id": "a" * 24, "fecha_hora": "2020-01-01T10:00:00"},
        {"medico_id": "a" * 24, "fecha_hora": "2099-01-01T10:00:00", "estado": "confirmado"},
        {"fecha_hora": "2099-01-01T10:00:00"},
    ],
)
def test_otorgar_datos_invalidos(client, h_paciente, h_admin, cuerpo):
    turno_id = _solicitar(client, h_paciente)
    resp = client.patch(f"/api/turnos/{turno_id}/otorgar", json=cuerpo, headers=h_admin)
    assert resp.status_code == 400


def test_otorgar_turno_inexistente(client, h_admin, h_medico):
    resp = _otorgar(client, h_admin, "0" * 24, _id_de(client, h_medico))
    assert resp.status_code == 404


@pytest.mark.parametrize("credenciales", [PACIENTE, MEDICO])
def test_solo_el_administrativo_puede_otorgar(client, auth_headers, credenciales):
    resp = _otorgar(client, auth_headers(*credenciales), "0" * 24, "a" * 24)
    assert resp.status_code == 403


# ---------- documentación ----------

def test_swagger_documenta_los_endpoints_del_administrativo(client):
    paths = client.get("/apispec_1.json").get_json()["paths"]
    assert {"get", "post"} <= set(paths["/api/turnos"])
    assert "get" in paths["/api/turnos/{turno_id}"]
    assert "patch" in paths["/api/turnos/{turno_id}/otorgar"]
