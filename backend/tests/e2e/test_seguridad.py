import base64
import json
import logging
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import mongomock
import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import TestConfig as ConfigDePruebas

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")
ID_FALSO = "0" * 24
NUEVO = {
    "nombre": "Juan Pérez", "email": "juan@pamiapp.com", "telefono": "2611234567",
    "dni": "12345678", "password": "Clave12345",
}

# (método, ruta, credenciales de un rol que NO tiene permiso)
NO_PERMITIDOS = [
    ("get", "/api/usuarios", PACIENTE),
    ("get", "/api/usuarios", MEDICO),
    ("get", "/api/pacientes?dni=30111222", PACIENTE),
    ("post", "/api/recetas", PACIENTE),
    ("post", "/api/recetas", ADMIN),
    ("get", "/api/recetas", PACIENTE),
    ("get", "/api/recetas", ADMIN),
    ("get", "/api/recetas/mias", MEDICO),
    ("get", "/api/recetas/mias", ADMIN),
    ("post", "/api/turnos", MEDICO),
    ("post", "/api/turnos", ADMIN),
    ("get", "/api/turnos/mios", MEDICO),
    ("get", "/api/turnos/mios", ADMIN),
    ("patch", f"/api/turnos/{ID_FALSO}/confirmar", ADMIN),
    ("patch", f"/api/turnos/{ID_FALSO}/confirmar", MEDICO),
    ("patch", f"/api/turnos/{ID_FALSO}/rechazar", MEDICO),
    ("patch", f"/api/turnos/{ID_FALSO}/reprogramar", PACIENTE),
    ("patch", f"/api/turnos/{ID_FALSO}/reprogramar", MEDICO),
    ("patch", f"/api/turnos/{ID_FALSO}/cancelar", PACIENTE),
    ("patch", f"/api/turnos/{ID_FALSO}/cancelar", MEDICO),
]
RUTAS_PROTEGIDAS = sorted({(metodo, ruta) for metodo, ruta, _ in NO_PERMITIDOS})


# ---------- permisos por rol ----------

@pytest.mark.parametrize("metodo,ruta,credenciales", NO_PERMITIDOS)
def test_cada_rol_recibe_403_en_lo_que_no_le_corresponde(client, auth_headers, metodo, ruta, credenciales):
    resp = getattr(client, metodo)(ruta, headers=auth_headers(*credenciales))
    assert resp.status_code == 403


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_sin_token_las_rutas_protegidas_dan_401(client, metodo, ruta):
    assert getattr(client, metodo)(ruta).status_code == 401


# ---------- tokens ----------

def _alterar_rol(token, rol):
    """Cambia el rol dentro del token sin volver a firmarlo (intento de subir de rol)."""
    cabecera, carga, firma = token.split(".")
    relleno = "=" * (-len(carga) % 4)
    datos = json.loads(base64.urlsafe_b64decode(carga + relleno))
    datos["rol"] = rol
    nueva = base64.urlsafe_b64encode(json.dumps(datos).encode()).decode().rstrip("=")
    return f"{cabecera}.{nueva}.{firma}"


def _con_token(token):
    return {"Authorization": f"Bearer {token}"}


def test_token_vencido_da_401(app, client):
    with app.app_context():
        token = create_access_token(
            identity="123", additional_claims={"rol": "administrativo"}, expires_delta=timedelta(seconds=-10)
        )
    assert client.get("/api/usuarios", headers=_con_token(token)).status_code == 401


def test_token_firmado_con_otra_clave_da_401(client):
    ahora = int(datetime.now(timezone.utc).timestamp())
    carga = {
        "sub": "123", "rol": "administrativo", "type": "access", "fresh": False,
        "jti": "prueba", "iat": ahora, "nbf": ahora, "exp": ahora + 600,
    }
    token = pyjwt.encode(carga, "otra-clave-que-no-es-la-del-servidor-1234567890", algorithm="HS256")
    assert client.get("/api/usuarios", headers=_con_token(token)).status_code == 401


def test_token_con_el_rol_alterado_da_401(client, auth_headers):
    token = auth_headers(*PACIENTE)["Authorization"].split()[1]
    falso = _alterar_rol(token, "administrativo")
    assert client.get("/api/usuarios", headers=_con_token(falso)).status_code == 401
    # el token original sigue siendo de paciente: puede entrar al sistema, pero no a lo del administrativo
    assert client.get("/api/usuarios", headers=_con_token(token)).status_code == 403


@pytest.mark.parametrize("encabezado", ["Bearer token.falso.alterado", "Basic abc123", "esto-no-es-un-token"])
def test_token_mal_formado_da_401(client, encabezado):
    resp = client.get("/api/auth/me", headers={"Authorization": encabezado})
    assert resp.status_code == 401


# ---------- registro ----------

def test_registro_exige_contrasena_segura(client):
    for clave in ("clave12345", "CLAVE12345", "ClaveSinNumero"):
        resp = client.post("/api/auth/registro", json={**NUEVO, "password": clave})
        assert resp.status_code == 400
    assert client.post("/api/auth/registro", json=NUEVO).status_code == 201


def test_rate_limit_en_registro(client):
    codigos = [client.post("/api/auth/registro", json=NUEVO).status_code for _ in range(11)]
    assert 429 not in codigos[:10]
    assert codigos[10] == 429


# ---------- encabezados y configuración ----------

def test_encabezados_de_seguridad_en_todas_las_respuestas(client, login):
    respuestas = [
        client.get("/apispec_1.json"),
        client.get("/api/auth/me"),
        login(*PACIENTE),
    ]
    for resp in respuestas:
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Cache-Control"] == "no-store"


def test_cors_solo_permite_los_origenes_configurados(client):
    pedido = {"Access-Control-Request-Method": "POST"}
    permitido = client.options("/api/auth/login", headers={"Origin": "http://localhost:5173", **pedido})
    assert permitido.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    ajeno = client.options("/api/auth/login", headers={"Origin": "http://sitio-malicioso.example", **pedido})
    assert "Access-Control-Allow-Origin" not in ajeno.headers


def test_la_app_no_arranca_sin_claves_secretas():
    class SinSecretKey(ConfigDePruebas):
        SECRET_KEY = None

    class SinJwtSecretKey(ConfigDePruebas):
        JWT_SECRET_KEY = None

    db = mongomock.MongoClient()["pami_test"]
    for config in (SinSecretKey, SinJwtSecretKey):
        with pytest.raises(RuntimeError):
            create_app(config, db=db)


# ---------- registro de accesos y logs ----------

def test_se_registra_quien_consulta_pacientes(client, auth_headers, caplog):
    h = auth_headers(*MEDICO)
    usuario_id = client.get("/api/auth/me", headers=h).get_json()["id"]
    with caplog.at_level(logging.INFO, logger="pami.acceso"):
        resp = client.get("/api/pacientes?dni=30111222", headers=h)
    assert resp.status_code == 200
    registros = [r.getMessage() for r in caplog.records if r.name == "pami.acceso"]
    assert len(registros) == 1
    assert "lectura de paciente_por_dni" in registros[0]
    assert f"usuario_id={usuario_id}" in registros[0]
    assert "rol=medico" in registros[0]
    assert "30111222" not in caplog.text
    assert h["Authorization"].split()[1] not in caplog.text


def test_se_registra_el_acceso_a_las_recetas(client, auth_headers, caplog):
    with caplog.at_level(logging.INFO, logger="pami.acceso"):
        client.get("/api/recetas", headers=auth_headers(*MEDICO))
        client.get("/api/recetas/mias", headers=auth_headers(*PACIENTE))
    registros = [r.getMessage() for r in caplog.records if r.name == "pami.acceso"]
    assert any("recetas_del_medico" in r and "rol=medico" in r for r in registros)
    assert any("recetas_del_paciente" in r and "rol=paciente" in r for r in registros)


def test_los_logs_no_guardan_contrasenas_ni_tokens(client, login, caplog):
    with caplog.at_level(logging.INFO):
        login(PACIENTE[0], "ClaveIncorrecta99")
        ok = login(*PACIENTE)
    token = ok.get_json()["access_token"]
    assert "ClaveIncorrecta99" not in caplog.text
    assert PACIENTE[1] not in caplog.text
    assert token not in caplog.text