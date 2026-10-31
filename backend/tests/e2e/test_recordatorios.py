"""Sprint 2 (JAVI123-7): recordatorios de turnos confirmados, con acceso permitido y denegado por rol."""

from datetime import timedelta

import pytest

from app.services.recordatorio_service import ahora_local

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")


def _en(horas: int) -> str:
    """Fecha local dentro de `horas` horas (los turnos se guardan en hora local)."""
    return (ahora_local() + timedelta(hours=horas)).replace(microsecond=0).isoformat(timespec="seconds")


def _id_de(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).get_json()["id"]


@pytest.fixture
def h_paciente(auth_headers):
    return auth_headers(*PACIENTE)


@pytest.fixture
def h_admin(auth_headers):
    return auth_headers(*ADMIN)


@pytest.fixture
def h_medico(auth_headers):
    return auth_headers(*MEDICO)


@pytest.fixture
def crear_turno(client, h_paciente, h_admin, h_medico):
    """Devuelve una función que deja un turno otorgado (y confirmado si se pide) dentro de `horas` horas."""

    def _crear(horas: int, confirmar: bool = True) -> str:
        cuerpo = {"especialidad": "Cardiología", "fecha_hora": _en(horas), "motivo": "Control anual"}
        turno_id = client.post("/api/turnos", json=cuerpo, headers=h_paciente).get_json()["id"]
        otorgar = {"medico_id": _id_de(client, h_medico), "fecha_hora": _en(horas)}
        client.patch(f"/api/turnos/{turno_id}/otorgar", json=otorgar, headers=h_admin)
        if confirmar:
            client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h_paciente)
        return turno_id

    return _crear


def _ejecutar(client, headers):
    return client.post("/api/recordatorios/ejecutar", headers=headers)


def _recordatorios(client, headers):
    notifs = client.get("/api/notificaciones/mias", headers=headers).get_json()
    return [n for n in notifs if n["tipo"] == "recordatorio"]


def test_el_administrativo_genera_el_recordatorio_de_un_turno_de_manana(client, h_paciente, h_admin, crear_turno):
    turno_id = crear_turno(20)

    resp = _ejecutar(client, h_admin)

    assert resp.status_code == 200
    assert resp.get_json() == {"enviados": 1, "tomas": 0}
    recordatorio = _recordatorios(client, h_paciente)[0]
    assert recordatorio["turno_id"] == turno_id
    assert recordatorio["mensaje"].startswith("Recordatorio: tenés un turno de Cardiología")
    assert recordatorio["leida"] is False


def test_ejecutarlo_de_nuevo_no_duplica_el_recordatorio(client, h_paciente, h_admin, crear_turno):
    crear_turno(20)

    assert _ejecutar(client, h_admin).get_json()["enviados"] == 1
    assert _ejecutar(client, h_admin).get_json()["enviados"] == 0
    assert len(_recordatorios(client, h_paciente)) == 1


def test_no_recuerda_turnos_lejanos(client, h_paciente, h_admin, crear_turno):
    crear_turno(100)

    assert _ejecutar(client, h_admin).get_json()["enviados"] == 0
    assert _recordatorios(client, h_paciente) == []


def test_no_recuerda_un_turno_que_el_paciente_todavia_no_confirmo(client, h_paciente, h_admin, crear_turno):
    crear_turno(20, confirmar=False)

    assert _ejecutar(client, h_admin).get_json()["enviados"] == 0
    assert _recordatorios(client, h_paciente) == []


def test_si_se_reprograma_el_turno_el_recordatorio_vuelve_a_generarse(client, h_paciente, h_admin, crear_turno):
    turno_id = crear_turno(20)
    _ejecutar(client, h_admin)

    client.patch(f"/api/turnos/{turno_id}/reprogramar", json={"fecha_hora": _en(22)}, headers=h_admin)
    client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h_paciente)

    assert _ejecutar(client, h_admin).get_json()["enviados"] == 1
    assert len(_recordatorios(client, h_paciente)) == 2


def test_el_campo_interno_no_se_muestra_en_la_api(client, h_paciente, h_admin, crear_turno):
    crear_turno(20)
    _ejecutar(client, h_admin)

    turno = client.get("/api/turnos/mios", headers=h_paciente).get_json()[0]
    assert "recordatorios_enviados" not in turno
    assert "_id" not in turno


def test_el_administrativo_no_recibe_el_recordatorio_del_paciente(client, h_admin, crear_turno):
    crear_turno(20)
    _ejecutar(client, h_admin)

    # el administrativo no recibe el recordatorio del paciente
    notifs_admin = client.get("/api/notificaciones/mias", headers=h_admin).get_json()
    assert [n for n in notifs_admin if n["tipo"] == "recordatorio"] == []


# ---------- permisos: acceso denegado ----------

@pytest.mark.parametrize("quien", ["h_paciente", "h_medico"])
def test_solo_el_administrativo_ejecuta_los_recordatorios(client, request, crear_turno, quien):
    crear_turno(20)

    assert _ejecutar(client, request.getfixturevalue(quien)).status_code == 403
    # y no se creó nada por intentarlo
    h_paciente = request.getfixturevalue("h_paciente")
    assert _recordatorios(client, h_paciente) == []


def test_sin_token_no_se_ejecutan_los_recordatorios(client):
    assert client.post("/api/recordatorios/ejecutar").status_code == 401


def test_swagger_documenta_el_endpoint(client):
    assert "/api/recordatorios/ejecutar" in client.get("/apispec_1.json").get_json()["paths"]


# ---------- script programable ----------

def test_el_script_crea_los_recordatorios_e_informa_cuantos(app, crear_turno, monkeypatch, capsys):
    from scripts import enviar_recordatorios

    crear_turno(20)
    monkeypatch.setattr(enviar_recordatorios, "create_app", lambda: app)

    enviar_recordatorios.main()
    salida = capsys.readouterr().out
    assert "Recordatorios creados: 1" in salida
    assert "toma" not in salida  # la receta del paciente la genera el administrativo, no el script

    enviar_recordatorios.main()
    assert "Recordatorios creados: 0" in capsys.readouterr().out
