"""Prueba del flujo completo del Sprint 1 (hito H5 del reparto de tareas)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.security.passwords import hash_password

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


def _solicitar(client, headers, **extra):
    cuerpo = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual", **extra}
    return client.post("/api/turnos", json=cuerpo, headers=headers)


def _otorgar(client, headers, turno_id, medico_id, fecha=None):
    return client.patch(
        f"/api/turnos/{turno_id}/otorgar",
        json={"medico_id": medico_id, "fecha_hora": fecha or _futuro(10)},
        headers=headers,
    )


# ---------- el flujo de punta a punta ----------

def test_flujo_completo_solicitar_otorgar_notificar_y_confirmar(client, h_paciente, h_admin, h_medico):
    # 1. el paciente pide el turno
    resp = _solicitar(client, h_paciente)
    assert resp.status_code == 201
    turno_id = resp.get_json()["id"]
    assert resp.get_json()["estado"] == "solicitado"

    # 2. el administrativo lo ve y lo otorga con médico, fecha y hora
    pendientes = client.get("/api/turnos?estado=solicitado", headers=h_admin).get_json()
    assert [t["id"] for t in pendientes] == [turno_id]
    resp = _otorgar(client, h_admin, turno_id, _id_de(client, h_medico), _futuro(10))
    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "otorgado"

    # 3. el paciente ve la notificación con la fecha y la hora, y confirma con el botón
    notifs = client.get("/api/notificaciones/mias", headers=h_paciente).get_json()
    assert len(notifs) == 1
    assert notifs[0]["turno_id"] == turno_id
    assert notifs[0]["tipo"] == "turno_otorgado"
    assert notifs[0]["leida"] is False
    assert "10:30 hs" in notifs[0]["mensaje"]
    resp = client.patch(f"/api/turnos/{turno_id}/respuesta", json={"accion": "aceptar"}, headers=h_paciente)
    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "confirmado"


def test_flujo_recetas_crear_plan_y_emitir(client, h_paciente, h_medico):
    paciente_id = _id_de(client, h_paciente)
    receta = client.post(
        "/api/recetas",
        json={"paciente_id": paciente_id, "medicamentos": [{"nombre": "Ibuprofeno", "dosis": "400 mg"}]},
        headers=h_medico,
    ).get_json()
    plan = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00"], "duracion_dias": 5}]}

    assert client.put(f"/api/recetas/{receta['id']}/plan", json=plan, headers=h_medico).status_code == 200
    assert client.post(f"/api/recetas/{receta['id']}/emitir", headers=h_medico).get_json()["estado"] == "emitida"

    # el paciente la recibe; en las rutas del médico recibe 403
    assert len(client.get("/api/recetas/mias", headers=h_paciente).get_json()) == 1
    assert client.post(f"/api/recetas/{receta['id']}/emitir", headers=h_paciente).status_code == 403


# ---------- solicitud por voz ----------

def test_el_turno_pedido_por_voz_queda_con_origen_voz(client, h_paciente):
    resp = _solicitar(client, h_paciente, origen="voz")

    assert resp.status_code == 201
    assert resp.get_json()["origen"] == "voz"
    assert resp.get_json()["creado_en"]


def test_el_origen_por_defecto_es_manual(client, h_paciente):
    assert _solicitar(client, h_paciente).get_json()["origen"] == "manual"


def test_origen_invalido_devuelve_400(client, h_paciente):
    assert _solicitar(client, h_paciente, origen="telepatia").status_code == 400


@pytest.mark.parametrize("rol", [MEDICO, ADMIN])
def test_medico_y_administrativo_no_solicitan_turnos(client, auth_headers, rol):
    assert _solicitar(client, auth_headers(*rol)).status_code == 403


# ---------- permisos de otorgar ----------

@pytest.mark.parametrize("rol", [PACIENTE, MEDICO])
def test_paciente_y_medico_no_otorgan_turnos(client, h_paciente, h_medico, auth_headers, rol):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]

    resp = _otorgar(client, auth_headers(*rol), turno_id, _id_de(client, h_medico))

    assert resp.status_code == 403


def test_no_se_otorga_un_turno_que_no_esta_solicitado(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    medico_id = _id_de(client, h_medico)
    _otorgar(client, h_admin, turno_id, medico_id)

    assert _otorgar(client, h_admin, turno_id, medico_id, _futuro(11)).status_code == 409


# ---------- el médico no puede tener dos turnos a la misma hora ----------

def test_el_medico_no_puede_tener_dos_turnos_a_la_misma_hora(client, h_paciente, h_admin, h_medico):
    medico_id = _id_de(client, h_medico)
    primero = _solicitar(client, h_paciente).get_json()["id"]
    segundo = _solicitar(client, h_paciente).get_json()["id"]
    hora = _futuro(10, 11)

    assert _otorgar(client, h_admin, primero, medico_id, hora).status_code == 200
    resp = _otorgar(client, h_admin, segundo, medico_id, hora)

    assert resp.status_code == 409
    # el segundo turno sigue pendiente y se puede otorgar en otro horario
    assert _otorgar(client, h_admin, segundo, medico_id, _futuro(10, 12)).status_code == 200


def test_un_turno_rechazado_libera_el_horario(client, h_paciente, h_admin, h_medico):
    medico_id = _id_de(client, h_medico)
    primero = _solicitar(client, h_paciente).get_json()["id"]
    segundo = _solicitar(client, h_paciente).get_json()["id"]
    hora = _futuro(10, 11)
    _otorgar(client, h_admin, primero, medico_id, hora)
    client.patch(f"/api/turnos/{primero}/respuesta", json={"accion": "rechazar"}, headers=h_paciente)

    assert _otorgar(client, h_admin, segundo, medico_id, hora).status_code == 200


# ---------- respuesta del paciente ----------

def test_accion_invalida_devuelve_400(client, h_paciente):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]

    resp = client.patch(f"/api/turnos/{turno_id}/respuesta", json={"accion": "quizas"}, headers=h_paciente)

    assert resp.status_code == 400


def test_no_se_responde_un_turno_que_no_esta_otorgado(client, h_paciente):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]

    resp = client.patch(f"/api/turnos/{turno_id}/respuesta", json={"accion": "aceptar"}, headers=h_paciente)

    assert resp.status_code == 409


def test_un_paciente_no_responde_el_turno_de_otro(app, client, h_paciente, h_admin, h_medico, auth_headers):
    app.db.usuarios.insert_one(
        {"nombre": "Pablo Paciente", "email": "paciente2@pamiapp.com", "telefono": "2610000010", "rol": "paciente",
         "dni": "28999888", "password_hash": hash_password("Paciente2222"), "intentos_fallidos": 0,
         "bloqueado_hasta": None}
    )
    otro = auth_headers("paciente2@pamiapp.com", "Paciente2222")
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))

    resp = client.patch(f"/api/turnos/{turno_id}/respuesta", json={"accion": "aceptar"}, headers=otro)

    assert resp.status_code == 404


def test_rechazar_deja_el_turno_rechazado(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))

    resp = client.patch(f"/api/turnos/{turno_id}/respuesta", json={"accion": "rechazar"}, headers=h_paciente)

    assert resp.get_json()["estado"] == "rechazado"


# ---------- notificaciones ----------

def test_cada_paciente_ve_solo_sus_notificaciones(app, client, h_paciente, h_admin, h_medico, auth_headers):
    app.db.usuarios.insert_one(
        {"nombre": "Pablo Paciente", "email": "paciente2@pamiapp.com", "telefono": "2610000010", "rol": "paciente",
         "dni": "28999888", "password_hash": hash_password("Paciente2222"), "intentos_fallidos": 0,
         "bloqueado_hasta": None}
    )
    otro = auth_headers("paciente2@pamiapp.com", "Paciente2222")
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))

    assert len(client.get("/api/notificaciones/mias", headers=h_paciente).get_json()) == 1
    assert client.get("/api/notificaciones/mias", headers=otro).get_json() == []


def test_marcar_una_notificacion_como_leida(client, h_paciente, h_admin, h_medico):
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))
    notif_id = client.get("/api/notificaciones/mias", headers=h_paciente).get_json()[0]["id"]

    resp = client.patch(f"/api/notificaciones/{notif_id}/leida", headers=h_paciente)

    assert resp.status_code == 200
    assert resp.get_json()["leida"] is True
    assert client.get("/api/notificaciones/mias", headers=h_paciente).get_json()[0]["leida"] is True


def test_no_se_puede_marcar_como_leida_la_notificacion_de_otro(app, client, h_paciente, h_admin, h_medico, auth_headers):
    app.db.usuarios.insert_one(
        {"nombre": "Pablo Paciente", "email": "paciente2@pamiapp.com", "telefono": "2610000010", "rol": "paciente",
         "dni": "28999888", "password_hash": hash_password("Paciente2222"), "intentos_fallidos": 0,
         "bloqueado_hasta": None}
    )
    otro = auth_headers("paciente2@pamiapp.com", "Paciente2222")
    turno_id = _solicitar(client, h_paciente).get_json()["id"]
    _otorgar(client, h_admin, turno_id, _id_de(client, h_medico))
    notif_id = client.get("/api/notificaciones/mias", headers=h_paciente).get_json()[0]["id"]

    assert client.patch(f"/api/notificaciones/{notif_id}/leida", headers=otro).status_code == 404
    assert client.patch("/api/notificaciones/no-es-un-id/leida", headers=h_paciente).status_code == 404


@pytest.mark.parametrize("rol", [MEDICO, ADMIN])
def test_solo_el_paciente_ve_notificaciones(client, auth_headers, rol):
    assert client.get("/api/notificaciones/mias", headers=auth_headers(*rol)).status_code == 403
    assert client.get("/api/notificaciones/mias").status_code == 401


# ---------- médicos y pacientes ----------

def test_listar_medicos_sin_datos_sensibles(client, h_paciente, h_admin):
    for headers in (h_paciente, h_admin):
        resp = client.get("/api/medicos", headers=headers)
        assert resp.status_code == 200
        assert [set(m) for m in resp.get_json()] == [{"id", "nombre", "especialidad"}]


def test_filtrar_medicos_por_especialidad(client, h_paciente):
    assert len(client.get("/api/medicos?especialidad=Clínica médica", headers=h_paciente).get_json()) == 1
    assert len(client.get("/api/medicos?especialidad=clínica MÉDICA", headers=h_paciente).get_json()) == 1
    assert client.get("/api/medicos?especialidad=Cardiología", headers=h_paciente).get_json() == []


def test_el_medico_no_lista_medicos(client, h_medico):
    assert client.get("/api/medicos", headers=h_medico).status_code == 403


def test_buscar_paciente_por_dni(client, h_medico, h_paciente):
    resp = client.get("/api/pacientes?dni=30111222", headers=h_medico)

    assert resp.status_code == 200
    assert resp.get_json() == [{"id": _id_de(client, h_paciente), "nombre": "Paula Paciente", "dni": "30111222"}]
    assert client.get("/api/pacientes?dni=11111111", headers=h_medico).get_json() == []


@pytest.mark.parametrize("dni", ["abc", "123", "123456789", ""])
def test_dni_invalido_devuelve_400(client, h_medico, dni):
    assert client.get(f"/api/pacientes?dni={dni}", headers=h_medico).status_code == 400


def test_el_paciente_no_busca_pacientes(client, h_paciente):
    assert client.get("/api/pacientes?dni=30111222", headers=h_paciente).status_code == 403


def test_swagger_documenta_los_endpoints_nuevos(client):
    spec = client.get("/apispec_1.json").get_json()
    for ruta in (
        "/api/turnos/{turno_id}/respuesta", "/api/medicos", "/api/pacientes",
        "/api/notificaciones/mias", "/api/notificaciones/{notificacion_id}/leida",
    ):
        assert ruta in spec["paths"]
