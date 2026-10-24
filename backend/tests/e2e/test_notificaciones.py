"""Sprint 2 (JAVI123-4): avisos por cambio de turno, con acceso permitido y denegado por rol."""

from datetime import datetime, timedelta, timezone

import pytest

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")


def _futuro(dias: int = 7, hora: int = 10) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(hour=hora, minute=30, second=0, microsecond=0, tzinfo=None).isoformat(timespec="seconds")


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
def turno_otorgado(client, h_paciente, h_admin, h_medico):
    """Turno ya otorgado por el administrativo (devuelve su id)."""
    cuerpo = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual"}
    turno_id = client.post("/api/turnos", json=cuerpo, headers=h_paciente).get_json()["id"]
    medico_id = _id_de(client, h_medico)
    client.patch(
        f"/api/turnos/{turno_id}/otorgar", json={"medico_id": medico_id, "fecha_hora": _futuro(10)}, headers=h_admin
    )
    return turno_id


def _notifs(client, headers):
    return client.get("/api/notificaciones/mias", headers=headers).get_json()


def _reprogramar(client, headers, turno_id, fecha=None):
    return client.patch(f"/api/turnos/{turno_id}/reprogramar", json={"fecha_hora": fecha or _futuro(20, 15)}, headers=headers)


# ---------- reprogramar ----------

def test_reprogramar_avisa_al_paciente_con_la_nueva_fecha(client, h_paciente, h_admin, turno_otorgado):
    resp = _reprogramar(client, h_admin, turno_otorgado, _futuro(20, 15))

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "reprogramado"
    notif = _notifs(client, h_paciente)[0]  # la más nueva primero
    assert notif["tipo"] == "turno_reprogramado"
    assert notif["turno_id"] == turno_otorgado
    assert "15:30 hs" in notif["mensaje"]
    assert notif["leida"] is False


def test_el_paciente_acepta_el_turno_reprogramado_y_el_administrativo_se_entera(client, h_paciente, h_admin, turno_otorgado):
    _reprogramar(client, h_admin, turno_otorgado)

    resp = client.patch(f"/api/turnos/{turno_otorgado}/confirmar", headers=h_paciente)

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "confirmado"
    aviso = _notifs(client, h_admin)[0]
    assert aviso["tipo"] == "turno_confirmado"
    assert aviso["mensaje"].startswith("Paula Paciente confirmó")


def test_el_paciente_rechaza_el_turno_otorgado_y_el_administrativo_se_entera(client, h_paciente, h_admin, turno_otorgado):
    client.patch(f"/api/turnos/{turno_otorgado}/rechazar", headers=h_paciente)

    aviso = _notifs(client, h_admin)[0]
    assert aviso["tipo"] == "turno_rechazado"
    assert aviso["mensaje"].startswith("Paula Paciente rechazó")


def test_reprogramar_a_una_fecha_pasada_devuelve_400(client, h_admin, turno_otorgado):
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None).isoformat(timespec="seconds")
    assert _reprogramar(client, h_admin, turno_otorgado, ayer).status_code == 400


@pytest.mark.parametrize("cuerpo", [{}, {"fecha_hora": "no-es-fecha"}, {"fecha_hora": {"$ne": ""}}, {"estado": "confirmado"}])
def test_reprogramar_valida_el_cuerpo(client, h_admin, turno_otorgado, cuerpo):
    resp = client.patch(f"/api/turnos/{turno_otorgado}/reprogramar", json=cuerpo, headers=h_admin)
    assert resp.status_code == 400


def test_reprogramar_un_turno_que_no_esta_otorgado_devuelve_409(client, h_paciente, h_admin):
    cuerpo = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual"}
    solicitado = client.post("/api/turnos", json=cuerpo, headers=h_paciente).get_json()["id"]

    assert _reprogramar(client, h_admin, solicitado).status_code == 409


def test_reprogramar_turno_inexistente_devuelve_404(client, h_admin):
    assert _reprogramar(client, h_admin, "0" * 24).status_code == 404
    assert _reprogramar(client, h_admin, "no-es-un-id").status_code == 404


# ---------- cancelar ----------

def test_cancelar_avisa_al_paciente(client, h_paciente, h_admin, turno_otorgado):
    resp = client.patch(f"/api/turnos/{turno_otorgado}/cancelar", headers=h_admin)

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "cancelado"
    assert _notifs(client, h_paciente)[0]["tipo"] == "turno_cancelado"


def test_no_se_cancela_dos_veces(client, h_admin, turno_otorgado):
    client.patch(f"/api/turnos/{turno_otorgado}/cancelar", headers=h_admin)
    assert client.patch(f"/api/turnos/{turno_otorgado}/cancelar", headers=h_admin).status_code == 409


def test_un_turno_cancelado_ya_no_se_puede_aceptar(client, h_paciente, h_admin, turno_otorgado):
    client.patch(f"/api/turnos/{turno_otorgado}/cancelar", headers=h_admin)
    assert client.patch(f"/api/turnos/{turno_otorgado}/confirmar", headers=h_paciente).status_code == 409


# ---------- permisos: acceso denegado ----------

@pytest.mark.parametrize("accion", ["reprogramar", "cancelar"])
def test_solo_el_administrativo_reprograma_y_cancela(client, h_paciente, h_medico, turno_otorgado, accion):
    ruta = f"/api/turnos/{turno_otorgado}/{accion}"
    cuerpo = {"fecha_hora": _futuro(20)}

    assert client.patch(ruta, json=cuerpo, headers=h_paciente).status_code == 403
    assert client.patch(ruta, json=cuerpo, headers=h_medico).status_code == 403
    assert client.patch(ruta, json=cuerpo).status_code == 401


def test_el_turno_sigue_igual_si_un_paciente_intenta_cancelarlo(client, h_paciente, h_admin, turno_otorgado):
    client.patch(f"/api/turnos/{turno_otorgado}/cancelar", headers=h_paciente)

    turnos = client.get("/api/turnos/mios", headers=h_paciente).get_json()
    assert turnos[0]["estado"] == "otorgado"


def test_cada_uno_ve_solo_sus_notificaciones(client, h_paciente, h_admin, turno_otorgado):
    _reprogramar(client, h_admin, turno_otorgado)
    client.patch(f"/api/turnos/{turno_otorgado}/confirmar", headers=h_paciente)

    tipos_paciente = {n["tipo"] for n in _notifs(client, h_paciente)}
    tipos_admin = {n["tipo"] for n in _notifs(client, h_admin)}
    assert tipos_paciente == {"turno_otorgado", "turno_reprogramado"}
    assert tipos_admin == {"turno_confirmado"}


def test_el_medico_no_ve_notificaciones(client, h_medico):
    assert client.get("/api/notificaciones/mias", headers=h_medico).status_code == 403


def test_el_administrativo_marca_como_leida_la_suya_pero_no_la_del_paciente(client, h_paciente, h_admin, turno_otorgado):
    client.patch(f"/api/turnos/{turno_otorgado}/rechazar", headers=h_paciente)
    suya = _notifs(client, h_admin)[0]["id"]
    del_paciente = _notifs(client, h_paciente)[0]["id"]

    assert client.patch(f"/api/notificaciones/{suya}/leida", headers=h_admin).get_json()["leida"] is True
    assert client.patch(f"/api/notificaciones/{del_paciente}/leida", headers=h_admin).status_code == 404
    assert _notifs(client, h_paciente)[0]["leida"] is False


def test_swagger_documenta_reprogramar_y_cancelar(client):
    paths = client.get("/apispec_1.json").get_json()["paths"]
    assert "/api/turnos/{turno_id}/reprogramar" in paths
    assert "/api/turnos/{turno_id}/cancelar" in paths
