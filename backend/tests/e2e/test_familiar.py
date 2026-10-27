"""Sprint 3 (JAVI123-8): familiar autorizado, con consentimiento y permisos por rol."""

import logging

import pytest

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")

FAMILIAR = {
    "nombre": "Marta Gómez",
    "parentesco": "Hija",
    "canal": "sms",
    "contacto": "+54 9 261 555-1234",
    "consentimiento": True,
}


@pytest.fixture
def h_paciente(auth_headers):
    return auth_headers(*PACIENTE)


@pytest.fixture
def h_medico(auth_headers):
    return auth_headers(*MEDICO)


@pytest.fixture
def h_admin(auth_headers):
    return auth_headers(*ADMIN)


@pytest.fixture
def h_otro_paciente(client, auth_headers):
    cuerpo = {"nombre": "Otro Paciente", "email": "otro@pamiapp.com", "telefono": "2615550000", "dni": "29888777", "password": "Clave12345"}
    assert client.post("/api/auth/registro", json=cuerpo).status_code == 201
    return auth_headers("otro@pamiapp.com", "Clave12345")


def _guardar(client, headers, **cambios):
    return client.put("/api/familiar", json={**FAMILIAR, **cambios}, headers=headers)


# ---------- el paciente administra a su familiar ----------

def test_al_principio_no_hay_familiar(client, h_paciente):
    resp = client.get("/api/familiar", headers=h_paciente)

    assert resp.status_code == 200
    assert resp.get_json() == {"familiar": None}


def test_el_paciente_autoriza_a_un_familiar(client, h_paciente):
    resp = _guardar(client, h_paciente)

    assert resp.status_code == 200
    familiar = resp.get_json()["familiar"]
    assert familiar["nombre"] == "Marta Gómez"
    assert familiar["parentesco"] == "Hija"
    assert familiar["canal"] == "sms"
    assert familiar["contacto"] == "+5492615551234"  # el teléfono queda normalizado
    assert familiar["autorizado_en"]
    assert "consentimiento" not in familiar
    assert client.get("/api/familiar", headers=h_paciente).get_json()["familiar"]["nombre"] == "Marta Gómez"


def test_autorizar_de_nuevo_cambia_los_datos(client, h_paciente):
    _guardar(client, h_paciente)

    resp = _guardar(client, h_paciente, nombre="Luis Pérez", canal="email", contacto="luis@mail.com")

    assert resp.get_json()["familiar"]["nombre"] == "Luis Pérez"
    assert client.get("/api/familiar", headers=h_paciente).get_json()["familiar"]["contacto"] == "luis@mail.com"


def test_el_paciente_quita_la_autorizacion(client, h_paciente):
    _guardar(client, h_paciente)

    resp = client.delete("/api/familiar", headers=h_paciente)

    assert resp.status_code == 200
    assert resp.get_json() == {"familiar": None}
    assert client.get("/api/familiar", headers=h_paciente).get_json() == {"familiar": None}


def test_quitar_la_autorizacion_sin_familiar_responde_igual(client, h_paciente):
    assert client.delete("/api/familiar", headers=h_paciente).status_code == 200


def test_los_avisos_enviados_arrancan_vacios(client, h_paciente):
    resp = client.get("/api/familiar/avisos", headers=h_paciente)

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_la_ruta_funciona_con_y_sin_barra_final(client, h_paciente):
    assert client.get("/api/familiar/", headers=h_paciente).status_code == 200
    assert client.get("/api/familiar", headers=h_paciente).status_code == 200


# ---------- validaciones: datos inválidos ----------

def test_sin_consentimiento_no_se_guarda_nada(client, h_paciente):
    resp = _guardar(client, h_paciente, consentimiento=False)

    assert resp.status_code == 400
    assert client.get("/api/familiar", headers=h_paciente).get_json() == {"familiar": None}


def test_el_consentimiento_tiene_que_estar_en_el_pedido(client, h_paciente):
    cuerpo = {k: v for k, v in FAMILIAR.items() if k != "consentimiento"}

    assert client.put("/api/familiar", json=cuerpo, headers=h_paciente).status_code == 400


@pytest.mark.parametrize(
    "cambios",
    [
        {"contacto": "no-es-un-telefono"},
        {"canal": "email", "contacto": "marta@"},
        {"canal": "whatsapp"},
        {"nombre": "M"},
        {"contacto": {"$ne": ""}},  # intento de inyección de consulta
        {"paciente_id": "000000000000000000000000"},  # no se puede elegir a qué paciente pertenece
        {"rol": "administrativo"},
    ],
)
def test_datos_invalidos_devuelven_400(client, h_paciente, cambios):
    assert _guardar(client, h_paciente, **cambios).status_code == 400


def test_un_cuerpo_vacio_devuelve_400(client, h_paciente):
    assert client.put("/api/familiar", headers=h_paciente).status_code == 400


# ---------- permisos: acceso denegado ----------

@pytest.mark.parametrize("quien", ["h_medico", "h_admin"])
@pytest.mark.parametrize(
    "metodo, ruta",
    [("get", "/api/familiar"), ("put", "/api/familiar"), ("delete", "/api/familiar"), ("get", "/api/familiar/avisos")],
)
def test_solo_el_paciente_administra_a_su_familiar(client, request, quien, metodo, ruta):
    resp = getattr(client, metodo)(ruta, json=FAMILIAR, headers=request.getfixturevalue(quien))

    assert resp.status_code == 403


@pytest.mark.parametrize(
    "metodo, ruta",
    [("get", "/api/familiar"), ("put", "/api/familiar"), ("delete", "/api/familiar"), ("get", "/api/familiar/avisos")],
)
def test_sin_token_no_se_accede(client, metodo, ruta):
    assert getattr(client, metodo)(ruta, json=FAMILIAR).status_code == 401


def test_un_rol_denegado_no_alcanza_a_modificar_nada(client, h_paciente, h_admin):
    _guardar(client, h_paciente)

    client.delete("/api/familiar", headers=h_admin)
    client.put("/api/familiar", json={**FAMILIAR, "nombre": "Intruso"}, headers=h_admin)

    assert client.get("/api/familiar", headers=h_paciente).get_json()["familiar"]["nombre"] == "Marta Gómez"


def test_cada_paciente_ve_solo_a_su_familiar(client, h_paciente, h_otro_paciente):
    _guardar(client, h_paciente)

    assert client.get("/api/familiar", headers=h_otro_paciente).get_json() == {"familiar": None}
    _guardar(client, h_otro_paciente, nombre="Luis Pérez")
    assert client.get("/api/familiar", headers=h_paciente).get_json()["familiar"]["nombre"] == "Marta Gómez"
    # quitar el de uno no afecta al del otro
    client.delete("/api/familiar", headers=h_otro_paciente)
    assert client.get("/api/familiar", headers=h_paciente).get_json()["familiar"]["nombre"] == "Marta Gómez"


# ---------- datos del familiar: no se loguean ----------

def test_el_log_no_contiene_los_datos_del_familiar(client, h_paciente, caplog):
    caplog.set_level(logging.INFO)

    _guardar(client, h_paciente)
    client.get("/api/familiar", headers=h_paciente)
    client.get("/api/familiar/avisos", headers=h_paciente)

    registro = caplog.text
    assert "familiar_autorizado" in registro  # el acceso sí queda registrado
    for dato in ("Marta", "Gómez", "5492615551234", "555-1234"):
        assert dato not in registro


def test_swagger_documenta_los_endpoints_del_familiar(client):
    paths = client.get("/apispec_1.json").get_json()["paths"]

    assert set(paths["/api/familiar"]) >= {"get", "put", "delete"}
    assert "/api/familiar/avisos" in paths
